# Migration Run Findings — 2026-09-05

**Work set:** legacy package `20260610_NCC_RN2019_NCOC_Unit_1_full_production`, chapter 1 (Family-Centered Nursing Care, 18 slides) → `lesson_spec.json` v1.0 → `generate_lesson_package.py`.
**Result:** migration completes; generator renders 18/18 slides; PPTX validates; release status `blocked` (1 blocker, 2 major, 14 minor carried from legacy QA).

## Findings

| # | Finding | Class | Disposition |
|---|---|---|---|
| F1 | Legacy package was built without source text attached (its own source inventory says so). All 16 clinical slides migrate as `needs-verification`. `source-aligned_transformed` in the legacy manifest overstated evidence. | evidence | Register as gap. Do not relabel until source pages are attached and audited. |
| F2 | Legacy package has no organizing clinical question and no concept lanes. Both are required by the current pipeline and are the Stage 3 blueprint's core outputs. | schema gap | Blocker on migration. Requires one authoring pass per chapter — cannot be derived. |
| F3 | Lane and CJM assignments were inferred from `layout_archetype` by fixed table. CJM coverage after inference: all six covered (recognize S05; analyze S02,S03; prioritize S06,S12,S17; solutions S07,S11,S12; action S04,S07–S10,S14; evaluate S13,S15,S16). | inferred | Acceptable for draft. Faculty must confirm. `migration.lane_inferred: true` on every slide. |
| F4 | Legacy `activity_statement` is a slide directive ("Set the chapter lens."), not a learner task. Only the case slide carries a true prompt, and it has no answer key. | contract mismatch | One major. Answer keys must be authored; the legacy schema never held them. |
| F5 | Legacy visuals ("native shape visuals each slide") do not survive migration: the blueprint CSV holds no structured visual data, so 15/18 slides render as plain bullets with empty body space. | visual loss | The old visual layer lived only in the generator, not the data. New schema's `card_data` is the fix, but it must be authored. Register as the largest rework cost. |
| F6 | Speaker scripts (103–120 words/slide) migrate cleanly from notes; speaking-rate estimates land in the 140 wpm window. | pass | No action. |
| F7 | Legacy source is the ATI RN 2019 review module — `restricted` license, `coverage: absent`. Content cannot be labelled `source-grounded` against it. | license | Consistent with the OpenStax audit finding: the pipeline currently has no CC BY backbone source in the Drive corpus. |
| F8 | Legacy slide IDs (`NCOC_RN2019_CH001_S001`, with a gap at S018–S019) renumber to `S01–S18`. Original preserved as `legacy_slide_id`. | ID policy | Acceptable; Stage 13 lock applies from this run forward. |

## Baseline metrics for the VSM

| Measure | Value |
|---|---|
| Migration passes (build → run clean) | 2 (one fix: unit-level `ALL` rows in legacy QA CSV) |
| Generator passes | 1 |
| Slides rendered / total | 18 / 18 |
| Fields surviving migration without inference | 9 of 26 contract fields |
| Fields inferred | 4 (`concept_lane`, `cjm_functions`, `nursing_action_category`, `remediation_target`) |
| Fields empty, must be authored | 5 (`organizing_clinical_question`, `source_refs`, `answer_key`, `card_data`, `tts_text`) |

## Decision required

The migration proves the schema and generator on real data. It also shows the legacy Unit 1 package is roughly one authoring pass per chapter away from `faculty-review-needed` status (F2, F4, F5) and cannot reach `release-ready` at all without a source it can cite (F1, F7). The cheapest path to a release-ready reference lesson is therefore **not** further migration — it is one chapter authored fresh against a CC BY 4.0 source with the question, lanes, answer keys and card data written in.
