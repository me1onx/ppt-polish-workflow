# PPT Master Bridge

Use this reference when moving from a `codex-ppt` visual draft into a `ppt-master` review loop.

## Role Boundary

`codex-ppt` produces a visual-first deck where each final slide is an image assembled into PPTX. `ppt-master` is an SVG-first production workflow with live preview, direct edits, annotations, SVG post-processing, and PPTX export.

Because the formats are different, check the current artifacts first. `ppt-master` live preview now supports two surfaces:

- SVG project preview: full element selection, direct edits, annotations, save back to `svg_output/`.
- Image readonly preview: `codex-ppt` `origin_image/slide_*.png` pages are wrapped as read-only SVG image pages, so the user can preview and add whole-slide annotations without pretending the slide is object-editable.

## Live Preview Entry

Before starting or re-entering preview, read:

```text
/Users/liuchengxi/.codex/skills/ppt-master/workflows/live-preview.md
```

The normal live preview command is:

```bash
python3 /Users/liuchengxi/.codex/skills/ppt-master/scripts/svg_editor/run_server.py <project_path>
```

Use this when `<project_path>` is either:

- a `ppt-master` project with `svg_output/*.svg`, or
- a `codex-ppt` deck project with `origin_image/slide_*.png`.

If a preview server is already running for the project, report its URL instead of restarting it.

## Bridge Decision

After the `codex-ppt` draft is generated, choose one of these paths:

- `compatible-ppt-master-project`: the deck is already represented as a `ppt-master` project with `svg_output/`; use live preview directly.
- `image-readonly-preview`: the deck project has `origin_image/slide_*.png`; start `ppt-master` live preview directly, preview raster slides, and collect whole-slide annotations.
- `review-reference-only`: the deck is an image-based PPTX but no `origin_image/` project folder is available; use screenshots, exported slide images, or the PPTX itself as review references, then apply changes through `codex-ppt` regeneration or `image-to-editable-ppt` when selected.
- `rebuild-in-ppt-master`: the user wants a native `ppt-master` deck rather than an image-based deck; start a `ppt-master` project using the approved outline and visual direction as source guidance.

Do not fabricate `svg_output/` from screenshot slides just to make live preview appear available.

## Annotation Classification

Classify preview annotations before applying them:

- `direct-edit`: deterministic text, color, position, size, or attribute change that can be applied to a selected SVG element.
- `annotation-edit`: localized instruction requiring AI judgment, such as "make this section less crowded" or "replace this visual metaphor."
- `regenerate-slide`: composition, generated text, map, chart, or visual identity is wrong enough that patching would be brittle.
- `editable-page`: user explicitly asks for a page to become object-level editable in PowerPoint.

Apply `direct-edit` and `annotation-edit` through `ppt-master` when the project is compatible. Route `regenerate-slide` back to the generation skill or `ppt-master` rebuild path, depending on which artifact is authoritative. Route `editable-page` to `image-to-editable-ppt` only after user confirmation.

## Compatibility Limits

- A `codex-ppt` slide image is not an editable SVG page, even when it appears in `ppt-master` live preview.
- Image readonly preview supports viewing and whole-slide annotations, not object-level direct editing.
- A PPTX containing full-slide images is not automatically compatible with SVG direct editing unless the source `origin_image/` project folder is available for image readonly preview.
- `ppt-master` preview changes update SVG/project artifacts; re-export is still a separate chat-driven step.
- If review feedback targets text embedded in a generated slide image, prefer slide regeneration unless the user selects that page for editable reconstruction.
- If the user needs only a few editable pages, convert only those pages with `image-to-editable-ppt` and keep the rest image-based.

## Reporting

When leaving the review loop, report:

- Whether live preview was SVG direct-edit, image readonly, or reference-only.
- Which annotations were applied.
- Which changes required regeneration.
- Which pages were selected for editable reconstruction.
- Any unresolved compatibility limits.
