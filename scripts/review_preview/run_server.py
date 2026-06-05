#!/usr/bin/env python3
"""Python-version-safe launcher for PPT Polish image pre-review."""

from __future__ import annotations

import os
import sys
from pathlib import Path

BUNDLED_PYTHON = (
    "/Users/liuchengxi/.cache/codex-runtimes/codex-primary-runtime/"
    "dependencies/python/bin/python3"
)


def main() -> int:
    script_path = Path(__file__).resolve()
    skill_root = script_path.parents[2]
    venv_python = skill_root / ".venv" / "bin" / "python"
    server_py = script_path.with_name("server.py")

    if not venv_python.exists():
        print(
            "ppt-polish-workflow review preview runtime is missing: "
            f"{venv_python}\n"
            "Create it with:\n"
            f"  {BUNDLED_PYTHON} -m venv {skill_root / '.venv'}\n"
            f"  {skill_root / '.venv' / 'bin' / 'python'} -m pip install 'flask>=3.0.0'",
            file=sys.stderr,
        )
        return 1

    cmd = [str(venv_python), str(server_py)] + sys.argv[1:]
    os.execv(str(venv_python), cmd)


if __name__ == "__main__":
    raise SystemExit(main())
