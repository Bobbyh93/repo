# Harrity Lesson Builder QA Checklist

## Blockers

Do not export as final when any blocker exists.

- Required runtime variable is missing for the selected build mode.
- The output is a new skill instead of an update to `harrity-lesson-builder-pipeline` when the user requested skill consolidation.
- Lesson topic, source family, patient, chapter, package ID, or filename is hardcoded without user/source/runtime support.
- A final PPTX, ZIP, manifest, QA log, audio package, binding file, or video plan is claimed without an actual created file.
- Unsafe clinical instruction is presented without source support or a `needs-verification` flag.
- Unsupported factual claim is labeled as `source-grounded`.
- Duplicate `slide_id` values exist.
- Production slide contract is missing stable `slide_id`, CJM functions, source status, or channel fields.
- Clinical judgment mapping omits required CJMM functions without documented short-package rationale.
- Quiz remediation is based only on topic labels and does not identify the failed thinking operation.

## Major defects

Fix before final release.

- No high-level map or organizing clinical question.
- Map does not connect to bedside nursing action.
- Source status is omitted from manifest.
- Glossary or taxonomy drift occurs after lock.
- Notes are outlines instead of verbatim reviewer scripts.
- TTS text is collapsed with learner-facing slide text.
- Layout archetype or visual density budget is missing.
- Assessment map lacks concept lane, CJM function, learner task, or remediation target.
- Filename does not follow the resolved pattern.
- Rebuild scope is too broad or too narrow for a revision request.
- Existing slide IDs are silently renumbered during revision.

## Minor defects

Acceptable for draft or polish pass.

- Non-blocking title length or visual alignment issue.
- Optional media field is omitted when media output was not requested.
- Low-risk pronunciation note is missing.
- Activity answer key could be more concise.
- One concept lane label could be clearer, but map logic remains intact.

## Release status decision

- `release-ready`: no blockers or major defects.
- `review-needed`: no blockers, but clinical/source review remains.
- `draft-only`: source, taxonomy, or verification gaps remain.
- `blocked`: unsafe issue, export failure, source insufficiency, schema failure, or missing required files.
