# Review Preview

Use this reference when moving from a `codex-ppt` visual draft into the `ppt-polish-workflow` pre-review loop.

## Role Boundary

`codex-ppt` produces a visual-first deck where each final slide is an image assembled into PPTX. The built-in `ppt-polish-workflow` review preview is a lightweight image review layer for those draft slides.

It previews `origin_image/slide_*.png` and collects whole-slide or region annotations. It does not expose object-level SVG or PowerPoint editing.

`ppt-master` may be used as source-code inspiration for this preview layer, but it is not the runtime for `ppt-polish-workflow` pre-review.

## Live Preview Entry

Start preview with:

```bash
python3 /Users/liuchengxi/.codex/skills/ppt-polish-workflow/scripts/review_preview/run_server.py <deck_project_path>
```

Use this only when `<deck_project_path>/origin_image/slide_*.png` exists.

If a preview server is already running for the project, report its URL instead of restarting it. The lock file is:

```text
<deck_project_path>/.ppt_polish_preview.lock
```

## Annotation Output

When the user clicks "Save annotations", the server writes:

```text
<deck_project_path>/.ppt_polish_annotations.json
```

The file records:

- project path and save timestamp
- slide names
- annotation IDs
- annotation text
- target type: `slide` or `region`
- region coordinates when applicable

Coordinates are normalized to slide-relative fractions where `x`, `y`, `width`, and `height` are between `0` and `1`.

## Review Decision

After reading the saved annotation file, classify feedback as:

- `direct-chat-edit`: deterministic wording, color, spacing, or local instruction to include in the next generation/edit pass.
- `regenerate-slide`: composition, generated text, chart, visual identity, or structure is wrong enough that the slide should be remade.
- `editable-page`: user explicitly asks for a page to become object-level editable in PowerPoint.

Do not route a page to `image-to-editable-ppt` only because the annotation is complex. Editable reconstruction remains opt-in by page number.

## Compatibility Limits

- A `codex-ppt` slide image is not editable SVG or editable PPT content.
- Region annotations identify visual areas for AI follow-up; they do not create editable objects.
- If feedback targets text embedded in a generated slide image, prefer slide regeneration unless the user selects that page for editable reconstruction.
- If the user needs only a few editable pages, convert only those pages with `image-to-editable-ppt` and keep the rest image-based.

## Reporting

When leaving the pre-review loop, report:

- preview URL/status
- annotation JSON path
- which annotations were saved
- which pages need regeneration
- which pages were selected for editable reconstruction
- unresolved image-only limitations
