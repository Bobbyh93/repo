# Migration log — chapter 1: Family-Centered Nursing Care

- Deck `20260610_NCC_Unit_1_Foundations_of_Nursing_Care_of_Children_Family_Centered_Nursing_Care_Part_1.pptx`: 18 slides; blueprint rows for chapter: 18. Counts match.
- Legacy source_status `source-aligned_transformed` with inventory assumption: "Exact source text was not attached to this chat; chapter identity and unit structure were taken from available manifest …". Mapped to `evidence_status: needs-verification` on every clinical slide because no source text was attached at build. `source-aligned` would require resolvable source_refs, which do not exist.
- Lane and CJM assignments derived from legacy `layout_archetype` via a fixed table (ARCH_MAP). These are **inferred**, not sourced; every migrated slide carries `migration.lane_inferred: true`.
- `activity_statement` is a slide directive in the legacy schema (e.g. 'Set the chapter lens.'), not a learner task. Mapped to `activity_prompt` only for `case` archetype; elsewhere preserved in `visual_notes`. No legacy slide has an answer key; expect a `major` on the case slide.
- Legacy IDs `NCOC_RN2019_CH001_S0NN` renumbered to `SNN` by slide_number (legacy S020 → S18). Original kept in `legacy_slide_id`.
- `organizing_clinical_question` is empty: the legacy package has no organizing question or concept lanes. Lanes set to the safety/triage default from SKILL.md. Expect a **blocker** from the generator on the empty question.
- Legacy source registered as `SRC01`, license `restricted`, coverage `absent`. Legacy QA rows (14) carried into `qa.defects` with a `[legacy …]` prefix.
