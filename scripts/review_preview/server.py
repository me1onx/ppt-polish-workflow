#!/usr/bin/env python3
"""Image-only pre-review server for ppt-polish-workflow.

The server previews `codex-ppt` raster slide drafts from `origin_image/` and
persists whole-slide or region annotations for the agent to classify later.
It deliberately avoids SVG/PPT object editing.
"""

from __future__ import annotations

import argparse
import atexit
import json
import logging
import os
import signal
import sys
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from flask import Flask, jsonify, request, send_from_directory

LOGGER = logging.getLogger("ppt_polish_review")
LOCK_FILE_NAME = ".ppt_polish_preview.lock"
ANNOTATION_FILE_NAME = ".ppt_polish_annotations.json"
IMAGE_PATTERNS = ("slide_*.png", "slide_*.jpg", "slide_*.jpeg", "slide_*.webp")
VALID_TARGET_TYPES = {"slide", "region"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _iter_slide_images(image_dir: Path) -> list[Path]:
    files: list[Path] = []
    for pattern in IMAGE_PATTERNS:
        files.extend(image_dir.glob(pattern))
    return sorted(files)


def _find_image_dir(project_path: Path) -> Optional[Path]:
    image_dir = project_path / "origin_image"
    if image_dir.exists() and any(_iter_slide_images(image_dir)):
        return image_dir
    return None


def _process_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def _read_lock(lock_file: Path) -> Optional[dict[str, Any]]:
    try:
        data = json.loads(lock_file.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except (OSError, json.JSONDecodeError):
        return None


def _claim_lock(lock_file: Path, port: int) -> Optional[dict[str, Any]]:
    existing = _read_lock(lock_file)
    if existing and _process_alive(int(existing.get("pid", 0))):
        return existing
    lock_file.write_text(
        json.dumps({"pid": os.getpid(), "port": port}, ensure_ascii=False),
        encoding="utf-8",
    )
    return None


def _release_lock(lock_file: Path) -> None:
    try:
        current = _read_lock(lock_file)
        if current and int(current.get("pid", 0)) == os.getpid():
            lock_file.unlink(missing_ok=True)
    except OSError:
        pass


def _safe_slide_path(image_dir: Path, name: str) -> Optional[Path]:
    if "/" in name or "\\" in name or ".." in name:
        return None
    slide_path = (image_dir / name).resolve()
    try:
        slide_path.relative_to(image_dir.resolve())
    except ValueError:
        return None
    if slide_path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
        return None
    return slide_path


def _normalize_target(raw_target: Any) -> dict[str, Any]:
    if not isinstance(raw_target, dict):
        return {"type": "slide"}

    target_type = raw_target.get("type")
    if target_type not in VALID_TARGET_TYPES:
        target_type = "slide"

    target: dict[str, Any] = {"type": target_type}
    if target_type == "region":
        region = {}
        for key in ("x", "y", "width", "height"):
            value = raw_target.get(key)
            if not isinstance(value, (int, float)):
                return {"type": "slide"}
            value = float(value)
            if value < 0:
                value = 0.0
            if value > 1:
                value = 1.0
            region[key] = round(value, 6)
        if region["width"] <= 0 or region["height"] <= 0:
            return {"type": "slide"}
        target.update(region)
    return target


def _load_annotations(project_path: Path) -> dict[str, list[dict[str, Any]]]:
    annotation_path = project_path / ANNOTATION_FILE_NAME
    if not annotation_path.exists():
        return {}
    try:
        data = json.loads(annotation_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        LOGGER.warning("failed to load annotation file: %s", exc)
        return {}
    slides = data.get("slides") if isinstance(data, dict) else None
    if not isinstance(slides, dict):
        return {}
    clean: dict[str, list[dict[str, Any]]] = {}
    for name, records in slides.items():
        if not isinstance(name, str) or not isinstance(records, list):
            continue
        clean[name] = [r for r in records if isinstance(r, dict)]
    return clean


def _annotation_payload(
    project_path: Path,
    annotations: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    return {
        "version": 1,
        "preview_mode": "image-review",
        "project_path": str(project_path),
        "saved_at": _utc_now(),
        "slides": annotations,
    }


def create_app(
    project_dir: str,
    idle_timeout: int = 900,
    lock_file: Optional[Path] = None,
) -> Flask:
    project_path = Path(project_dir).resolve()
    image_dir = _find_image_dir(project_path)

    app = Flask(__name__, static_folder="static", static_url_path="/static")
    app.config["PROJECT_PATH"] = project_path
    app.config["IMAGE_DIR"] = image_dir
    app.config["LOCK_FILE"] = lock_file
    app.config["ANNOTATIONS"] = _load_annotations(project_path)
    app.config["LAST_REQUEST_TIME"] = time.time()

    @app.before_request
    def _update_activity() -> None:
        app.config["LAST_REQUEST_TIME"] = time.time()

    def _exit_with_lock_release(code: int = 0) -> None:
        lf = app.config.get("LOCK_FILE")
        if lf is not None:
            _release_lock(lf)
        os._exit(code)

    def _idle_watchdog() -> None:
        if idle_timeout <= 0:
            return
        while True:
            time.sleep(10)
            elapsed = time.time() - app.config["LAST_REQUEST_TIME"]
            if elapsed > idle_timeout:
                LOGGER.info("idle for %ds, shutting down", idle_timeout)
                _exit_with_lock_release(0)

    threading.Thread(target=_idle_watchdog, daemon=True).start()

    @app.route("/")
    def index():
        return send_from_directory(app.static_folder, "index.html")

    @app.route("/api/config")
    def config():
        return jsonify({"preview_mode": "image-review", "live": True})

    @app.route("/api/slides")
    def slides():
        image_dir = app.config.get("IMAGE_DIR")
        if image_dir is None:
            return jsonify({"slides": [], "error": "origin_image slide images not found"}), 404
        annotations = app.config["ANNOTATIONS"]
        payload = []
        for slide_file in _iter_slide_images(image_dir):
            try:
                mtime = slide_file.stat().st_mtime
            except OSError as exc:
                LOGGER.warning("stat failed: %s: %s", slide_file, exc)
                continue
            count = len(annotations.get(slide_file.name, []))
            payload.append(
                {
                    "name": slide_file.name,
                    "mtime": mtime,
                    "annotation_count": count,
                    "annotated": count > 0,
                    "preview_mode": "image-review",
                }
            )
        return jsonify({"slides": payload})

    @app.route("/preview-images/<path:name>")
    def preview_image(name: str):
        image_dir = app.config.get("IMAGE_DIR")
        if image_dir is None:
            return jsonify({"error": "origin_image slide images not found"}), 404
        slide_path = _safe_slide_path(image_dir, name)
        if slide_path is None or not slide_path.exists() or not slide_path.is_file():
            return jsonify({"error": "slide not found"}), 404
        return send_from_directory(str(image_dir), name)

    @app.route("/api/slide/<name>")
    def slide(name: str):
        image_dir = app.config.get("IMAGE_DIR")
        if image_dir is None:
            return jsonify({"error": "origin_image slide images not found"}), 404
        slide_path = _safe_slide_path(image_dir, name)
        if slide_path is None or not slide_path.exists() or not slide_path.is_file():
            return jsonify({"error": "slide not found"}), 404
        try:
            mtime = slide_path.stat().st_mtime
        except OSError as exc:
            return jsonify({"error": f"failed to stat slide: {exc}"}), 500
        return jsonify(
            {
                "name": name,
                "image_url": f"/preview-images/{name}",
                "annotations": app.config["ANNOTATIONS"].get(name, []),
                "mtime": mtime,
                "preview_mode": "image-review",
                "warnings": [
                    {
                        "kind": "image-preview-readonly",
                        "reason": "Raster slide preview is read-only; save annotations for AI follow-up.",
                    }
                ],
            }
        )

    @app.route("/api/slide/<name>/annotate", methods=["POST"])
    def annotate(name: str):
        image_dir = app.config.get("IMAGE_DIR")
        if image_dir is None:
            return jsonify({"error": "origin_image slide images not found"}), 404
        slide_path = _safe_slide_path(image_dir, name)
        if slide_path is None or not slide_path.exists() or not slide_path.is_file():
            return jsonify({"error": "slide not found"}), 404

        data = request.get_json(silent=True) or {}
        text = data.get("annotation")
        if not isinstance(text, str) or not text.strip():
            return jsonify({"error": "annotation is required"}), 400
        if len(text) > 10000:
            return jsonify({"error": "annotation too long (max 10000 chars)"}), 400

        record = {
            "id": f"ann_{uuid.uuid4().hex[:12]}",
            "annotation": text.strip(),
            "target": _normalize_target(data.get("target")),
            "created_at": _utc_now(),
        }
        app.config["ANNOTATIONS"].setdefault(name, []).append(record)
        return jsonify(
            {
                "status": "ok",
                "annotation": record,
                "annotations_count": len(app.config["ANNOTATIONS"][name]),
            }
        )

    @app.route("/api/slide/<name>/annotate/<annotation_id>", methods=["DELETE"])
    def delete_annotation(name: str, annotation_id: str):
        annotations = app.config["ANNOTATIONS"].setdefault(name, [])
        before = len(annotations)
        app.config["ANNOTATIONS"][name] = [
            ann for ann in annotations if ann.get("id") != annotation_id
        ]
        return jsonify(
            {
                "status": "ok",
                "deleted": len(app.config["ANNOTATIONS"][name]) != before,
                "annotations_count": len(app.config["ANNOTATIONS"][name]),
            }
        )

    @app.route("/api/save-all", methods=["POST"])
    def save_all():
        project_path = app.config["PROJECT_PATH"]
        annotation_path = project_path / ANNOTATION_FILE_NAME
        payload = _annotation_payload(project_path, app.config["ANNOTATIONS"])
        annotation_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        total = sum(len(v) for v in app.config["ANNOTATIONS"].values())
        return jsonify(
            {
                "status": "ok",
                "path": str(annotation_path),
                "annotations_count": total,
            }
        )

    @app.route("/api/shutdown", methods=["POST"])
    def shutdown():
        data = request.get_json(silent=True) or {}
        reason = data.get("reason") or "shutdown"

        def _stop() -> None:
            time.sleep(0.5)
            LOGGER.info("shutting down (%s)", reason)
            _exit_with_lock_release(0)

        threading.Thread(target=_stop, daemon=True).start()
        return jsonify({"status": "ok"})

    return app


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="PPT Polish image review preview server")
    parser.add_argument("project_dir", help="codex-ppt deck project directory")
    parser.add_argument("--port", type=int, default=5055, help="Port to serve on")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind")
    parser.add_argument(
        "--idle-timeout",
        type=int,
        default=900,
        help="Seconds without requests before auto-shutdown; 0 disables",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    project_path = Path(args.project_dir).resolve()
    if not project_path.exists() or not project_path.is_dir():
        LOGGER.error("project directory does not exist: %s", project_path)
        return 1

    image_dir = _find_image_dir(project_path)
    if image_dir is None:
        LOGGER.error("no origin_image/slide_*.png images found in %s", project_path)
        return 1

    lock_file = project_path / LOCK_FILE_NAME
    existing = _claim_lock(lock_file, args.port)
    if existing:
        LOGGER.error(
            "review preview is already running for this project at http://127.0.0.1:%s "
            "(pid %s)",
            existing.get("port"),
            existing.get("pid"),
        )
        return 2

    atexit.register(_release_lock, lock_file)

    def _signal_handler(signum, _frame) -> None:
        LOGGER.info("signal %s received, releasing lock", signum)
        _release_lock(lock_file)
        raise SystemExit(0)

    signal.signal(signal.SIGTERM, _signal_handler)
    signal.signal(signal.SIGINT, _signal_handler)

    app = create_app(
        str(project_path),
        idle_timeout=args.idle_timeout,
        lock_file=lock_file,
    )
    slide_count = len(_iter_slide_images(image_dir))
    LOGGER.info("project: %s", project_path)
    LOGGER.info("image preview: %s (%d slides)", image_dir, slide_count)
    LOGGER.info("review preview URL: http://%s:%s", args.host, args.port)
    app.run(host=args.host, port=args.port, debug=False, threaded=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
