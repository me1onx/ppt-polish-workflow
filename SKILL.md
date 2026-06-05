---
name: ppt-polish-workflow
description: "Orchestrate a personal PPT production workflow from a ChatGPT-generated presentation outline: use codex-ppt for the first image-based visual draft, use ppt-master live preview and annotations for review and polish, and only when the user explicitly selects pages, use image-to-editable-ppt to convert those pages into editable PPTX pages."
---

# PPT Polish Workflow

## Overview

Use this skill as the coordinator for a staged PPT workflow. It does not replace `codex-ppt`, `ppt-master`, or `image-to-editable-ppt`; it decides when to invoke each one and keeps the handoff between draft, review, and editable reconstruction explicit.

Default outcome: a polished visual PPT deck, with only user-selected pages converted to object-level editable PPTX when needed.

## Mandatory Stop Gates

This skill is an interactive production workflow, not a one-shot PPT generator. Do not deliver the first generated PPTX as the final answer unless the user explicitly asked to skip review and editable-page decisions.

Stop and wait for user input at these gates:

1. `outline-confirmed`: after normalizing the ChatGPT outline, before any slide image generation.
2. `draft-review`: immediately after the first `codex-ppt` PPTX is assembled and the preview surface has been started or explicitly reported as unavailable.
3. `review-changes`: after the user has previewed or described requested edits.
4. `editable-page-selection`: after review changes are handled, before any `image-to-editable-ppt` work.
5. `final-delivery`: only after the user says no more preview edits and either chooses editable pages or explicitly declines editable conversion.

If the user asks "make/generate the PPT" without mentioning preview or editable pages, still stop at `draft-review`. The correct response is to provide the draft PPTX path, start `ppt-master` live preview when `svg_output/` or `origin_image/` is available, explain the preview/review status, and ask what to do next.

## Required Inputs

Before starting, identify:

- The ChatGPT-generated PPT outline or slide list.
- The intended audience, purpose, and delivery context if stated.
- Any hard constraints: page count, language, brand/style, source images, deadline, or required editable pages.
- The output directory and deck name, if the user specified them.

If the user only gives a rough topic instead of an outline, ask for the outline or use the appropriate upstream content-to-outline workflow before entering this skill.

## Workflow

### 1. Normalize And Confirm The Outline

Convert the user's ChatGPT outline into a deck-ready structure:

- Slide number and title.
- 3-5 concise points per slide.
- Intended visual role such as cover, agenda, section divider, comparison, process, timeline, data evidence, case study, summary, or Q&A.
- Required source assets, if any.
- Speaker-note intent, if the user expects narration.

Before generating the deck, show the normalized outline and ask for confirmation unless the user explicitly asked to skip approvals.

### 2. Generate The Visual Draft With `codex-ppt`

Use `codex-ppt` for the first complete draft. Follow its own phase gates, backend selection rules, sample-slide approval, subagent dispatch rules, QA, notes, and final PPTX assembly.

Do not ask `codex-ppt` to produce object-level editable PowerPoint layouts. Its role here is visual-first draft generation.

Expected draft artifacts include:

- `outline.md`
- generated slide images under the deck project
- `speech.md` or speaker notes when applicable
- the initial `.pptx`

Mandatory handoff after draft generation:

- Verify the PPTX exists and the expected slide images exist.
- Classify the draft for `ppt-master` handoff as `compatible-ppt-master-project`, `image-readonly-preview`, `review-reference-only`, or `rebuild-in-ppt-master`.
- If the deck project has `svg_output/*.svg` or `origin_image/slide_*.png`, start `ppt-master` live preview immediately before stopping for user review.
- Stop and tell the user: draft path, live preview URL if started, bridge classification, whether the preview is SVG direct-edit or image readonly, and that editable conversion has not started.
- Ask the user for the next action: add preview annotations, request edits in chat, select pages for editable conversion, or accept the current draft as final.

Do not continue from the first draft directly to final delivery.

### 3. Review And Polish With `ppt-master`

Use `ppt-master` for live preview and annotation-driven polish. It now supports both native SVG projects and read-only preview of `codex-ppt` image drafts that contain `origin_image/slide_*.png`.

Before using live preview, read:

```text
/Users/liuchengxi/.codex/skills/ppt-master/SKILL.md
/Users/liuchengxi/.codex/skills/ppt-master/workflows/live-preview.md
```

For bridge details, read `references/ppt-master-bridge.md`.

In the review loop:

- Direct, deterministic edits such as wording, color, spacing, or simple coordinates can be applied directly in the preview workflow.
- Annotation edits that require judgment should be collected, classified, and applied through the `ppt-master` annotation path.
- Larger design changes should be routed back to a slide-level regeneration or reconstruction step instead of patched superficially.

If the draft is `review-reference-only`, do not skip the review gate. Show the user the draft path and explain that live editing is not direct because the draft is image-based. Offer review by screenshots/PPTX reference, chat-described edits, slide regeneration, or rebuilding in `ppt-master`.

If the draft is `image-readonly-preview`, do not describe preview as unavailable. Start the live preview server against the `codex-ppt` deck project directory and tell the user that annotations apply to whole-slide raster previews.

### 4. Classify Requested Changes

After each review pass, classify every requested change:

- `direct-edit`: wording, color, alignment, spacing, or other deterministic local change.
- `annotation-edit`: a localized change requiring AI judgment or layout adjustment.
- `regenerate-slide`: a page whose visual concept, composition, or generated text is wrong enough to remake.
- `editable-page`: a page the user explicitly wants as object-level editable PPTX.

Do not silently convert a page to editable PPTX only because it has many edits. Ask the user to confirm the page numbers for `editable-page` work.

### 5. Convert Selected Pages With `image-to-editable-ppt`

Use `image-to-editable-ppt` only after the user names one or more pages to convert.

Before conversion, provide the selected page list and the source artifact for each page, then follow `image-to-editable-ppt` exactly. Its role is object-level reconstruction, not visual draft generation.

Do not convert the whole deck by default. Whole-deck conversion requires an explicit user request.

If the user has not named pages, ask a direct decision question before final delivery: whether to keep the deck image-based, convert specific pages, or convert the whole deck. If the user declines conversion, record that decision in the final response.

### 6. Final Delivery

At the end, report:

- Final visual draft PPTX path.
- Any `ppt-master` export path or annotation status.
- Any pages converted through `image-to-editable-ppt` and their output PPTX paths.
- Which pages remain image-based and which pages are object-level editable.
- Known limits such as generated-image text drift, pages not yet reviewed, or pages intentionally left image-based.

## Rules

- Keep the three underlying skills separate; do not copy their detailed internal instructions into this skill.
- Treat `codex-ppt` output as image-based unless proven otherwise.
- Treat `ppt-master` live preview as mandatory after draft generation whenever `svg_output/*.svg` or `origin_image/slide_*.png` exists.
- Treat `image-to-editable-ppt` as an opt-in page reconstruction stage.
- Preserve user approval gates: outline approval, draft approval, review changes, and editable page selection.
- Never skip the draft-review gate merely because a PPTX exists.
- Never skip the editable-page-selection gate merely because the user did not mention editability.
- If a handoff is not technically compatible, state the blocker and choose the closest review-safe alternative rather than pretending the tools interoperate.
