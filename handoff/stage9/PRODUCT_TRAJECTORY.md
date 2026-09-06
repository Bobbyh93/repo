# Product trajectory — from lesson generator to improvement system

Date: 2026-09-05 · Status: design note, not a roadmap commitment

## Principle
Lesson generation is stage one. The product is the loop: deliver → measure → analyze by failed CJM operation → act → re-deliver → show effect. Accreditors (CCNE Standard IV, ACEN Standard 6 — verify current numbering) and boards audit that loop, not the slides.

## Data model now carries the loop (schema v1.1)
- Traceability chain: program outcome → course objective → slide objective → assessment item → outcome data → improvement action. All identifier-linked.
- `standards_refs` on every slide, identifier-only for licensed frameworks, text allowed for public-domain regulation.
- `outcomes` (aggregate only, no learner identifiers) and `improvement_log` (trigger → finding → action → evidence).
- Generator emits `traceability_matrix.csv` and `unmapped_counts`; checks are `minor` in MVP so nothing blocks until a program activates the layer.

## Phases
| Phase | Scope | Exit criterion |
|---|---|---|
| MVP (now) | One release-ready lesson from a CC BY source; slots present, empty | `release-ready` status achieved once |
| v1 — Traceability | Program/course objectives authored; frameworks registered; matrix reviewed by faculty | `unmapped_counts` = 0 for one course |
| v2 — Outcomes in | Aggregate item results entered per delivery; Stage 10 classifies misses by failed operation | First `improvement_log` entry with `evidence_of_effect` filled |
| v3 — Analysis | Cross-lesson roll-up: CJM function × concept lane × cohort trend; curriculum-level gap report | One systematic evaluation cycle documented end to end |

## Constraints carried forward
- No learner-level data in any package artifact (FERPA). Aggregate at cohort.
- No RAG/embedding over restricted or NC-licensed sources; source index is identifier-based.
- Framework descriptor text policy enforced by `text_policy`, not by trust.
- Human approval remains the terminal step for any curriculum change.
