# Failure Modes

Use this list to prevent the most common bugs in lesson-generation workflows.

## 1. Input ambiguity
**Symptom:** The source text, files, and tables point in different directions.
**Prevention:** Run preflight first. Record assumptions and conflict decisions before building slides.

## 2. Taxonomy drift
**Symptom:** The outline uses one tag set and the scripts use a different tag set.
**Prevention:** Lock concept tags and outcome tags in the glossary stage. Allow new tags only in `proposed_new_tags`.

## 3. Definition drift
**Symptom:** The same term receives multiple definitions across slides.
**Prevention:** Maintain a single approved glossary and reuse those definitions exactly.

## 4. Slide overload
**Symptom:** One slide carries multiple teaching objectives and becomes impossible to narrate clearly.
**Prevention:** Enforce one core teaching objective per slide. Split slides instead of adding more bullets.

## 5. Outline-to-script drift
**Symptom:** The script introduces material that is not present in the approved outline.
**Prevention:** Require one script block per `slide_id` and flag `net_new_items` explicitly.

## 6. Duration bloat
**Symptom:** The lesson becomes much longer than intended during scripting.
**Prevention:** Track duration in both the outline and the script stages. Warn early when pacing is off.

## 7. Unsupported claims
**Symptom:** The lesson states inferred content as fact.
**Prevention:** Use the `evidence_status` field. Mark uncertain content as `inferred` or `unresolved` instead of blending it into source-grounded material.

## 8. Revision regressions
**Symptom:** Fixing one slide accidentally rewrites other approved slides.
**Prevention:** Treat revisions as targeted changes, keep stable slide ids, and maintain a revision log.

## 9. Non-slide-worthy material in the core flow
**Symptom:** Administrative details, exceptions, or appendices clutter the main teaching sequence.
**Prevention:** Classify material during outline creation as main flow, verbal aside, appendix, or exclude.

## 10. Audio-stage mutation
**Symptom:** The audio-ready package changes meaning or adds new teaching content.
**Prevention:** Treat audio export as a formatting stage, not a content-creation stage.

## 11. Machine-readable instability
**Symptom:** Downstream tools break because field names or structures shift between runs.
**Prevention:** Reuse the canonical field names in `references/schemas.md` and validate saved JSON with `scripts/validate_lesson_json.py`.

## 12. Visual dependence
**Symptom:** The script says things like "as you can see here" in an audio-only context.
**Prevention:** Remove visual-only phrasing or rewrite it as explicit narration.
