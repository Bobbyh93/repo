# Harrity Lesson Builder Dynamic Prompt Templates

## Runtime resolver prompt
Resolve `runtime_config` from the current user request and source inputs.

Return JSON only with these top-level objects:
- `runtime`
- `lesson`
- `sources`
- `taxonomy`
- `outputs`
- `layout`
- `media`
- `qa`
- `revision`
- `unresolved_variables`

Rules:
1. Do not invent lesson topic, chapter, source family, patient, case, or official source support.
2. Derive IDs and filenames after lesson identity is resolved.
3. Mark unsupported clinical details as `needs-verification`.
4. If source is sufficient for a useful draft but not final, proceed with `faculty-review-needed` or `draft-only` package status.

## Full production command template
Using the frozen `runtime_config`, run stages 0-12. Generate only the target outputs named in `outputs.target_outputs`. Preserve the five channels: slide, narration, speech, layout, media.

## Revision command template
Using `revision.change_request`, `revision.target_slide_ids`, and `runtime.rebuild_scope`, update only affected packages unless the change alters source base, taxonomy, slide order, lesson scope, or global output controls.
