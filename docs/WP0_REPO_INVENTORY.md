# WP-0 — Repository inventory (pre-build report)

Date: 2026-09-06 · Read-only · Answers the two questions the handoff required before code was written.

## Which repository is which

| Repo | State at session start | Role now |
|---|---|---|
| `Bobbyh93/repo` (this session's push target) | empty, zero commits | **build repo** — merged skill, tests, docs, fixtures |
| `Bobbyh93/codex_repo_2026` | public; 571 files; last commit "Do not block startup on pgvector setup (#6)" | inventoried read-only; not modified; not pushable from this session |

## Q1 — Which schema does the web app use?

**Its own Drizzle/Postgres model, not any of the three lesson schemas in the handoff.** Nothing in the app reads or writes `lesson_spec.json`, `package-schema`, `master-lesson`, or `runtime_config` (0 hits for each). The app's lesson tables are `lesson_packages`, `lesson_slides`, `lesson_items`, `lesson_citations` (`shared/schema.ts:1054–1285`) plus an ad-hoc "harrity" export profile that is a list of required filenames and QA gate keys in code (`server/routes/lesson-builder-routes.ts`).

Concept-by-concept against the v1.x slide contract:

| v1.x concept | In the app? | Nearest thing |
|---|---|---|
| `slide_id` (stable authored id) | no | FK column only |
| `slide_archetype` | no | `slideType` free string |
| `concept_lane` | no | — |
| `evidence_status` | no | `approvalStatus` / `ingestionStatus` on sources |
| `source_refs` | no | `sourceIds[]`, `lesson_citations` rows |
| `cjm_functions` | partial | single `cjmStep` per slide |
| `speaker_script` | partial | `speakerNotes` |
| `layout_spec` / `card_data` | no | `visibleContent` jsonb, `deckModel` jsonb |
| release / promotion state | yes | `releaseStage` (draft, clinical_review, approved, export_ready) + audit table + promote endpoint |
| traceability | name only | QA gate names `source_traceability`, `practice_item_traceability`; no matrix |

Consequence for WP-1: the merge could proceed on the file-based pipeline without touching the app. Consequence for WP-4: the app would need an adapter (DB rows ⇄ `lesson_spec`) before it could call the gate.

## Q2 — Does the `nclex-rn-2026` Common Cartridge / QTI exporter exist in the repo?

**Yes, and it is a library, not a script.** `server/nclex-curriculum-service.ts` (194 lines) exports six zero-argument pure functions: `curriculumManifest()`, `validateCurriculum()`, `canvasOutcomesCsv()`, `qtiAssessmentXml()`, `pathwayRulesManifest()`, `commonCartridgeArchive()` (JSZip → `.imscc`), `executionStatus()`. `scripts/build-nclex-curriculum-exports.mjs` is a 29-line driver. Outputs are committed under `curriculum_exports/nclex-rn-2026/`.

Three facts that change WP-3's plan:

1. **It emits QTI 2.1, not QTI 1.2.** `qtiAssessmentXml()` uses `imsqti_v2p1` with `assessmentItem`/`choiceInteraction`. There is no QTI 1.2 path. The handoff's "QTI 1.2" target is therefore new work, or WP-3 accepts 2.1.
2. **The QTI file is not registered as a resource in `imsmanifest.xml`.** It sits loose in the zip, so Canvas will not import the bank as a quiz.
3. **Its input is a hard-coded TypeScript array** (`EXEMPLAR_TOPICS` in `shared/nclex-rn-2026.ts`), not a DB package and not a `lesson_spec`. Reuse means porting the manifest/zip pattern, not calling the functions.

License note found in passing: `curriculum-manifest.json` asserts `CC BY 4.0` for all eight OpenStax sources, while `OPENSTAX_NURSING_SOURCE_AUDIT.md` in the same repo says CC BY-NC-SA 4.0 with an AI-ingestion restriction. Not verified independently; one of the two is wrong and it matters for WP-3's `no CC BY-NC content` constraint.

## Q3 (open question from the handoff) — Is the Render app the same codebase as a Replit app?

**Yes.** `.replit` (modules, autoscale deployment, object storage bucket), `pyproject.toml` name `repl-nix-workspace`, and `replit.md` naming the app "NursePrep Analytics" are all present. `PRODUCT_CONSOLIDATION_LOG.md` states the Render/GitHub app is canonical and Replit reconciliation is a separate follow-up. No file mentions NursesBrain, Nurse Remediation Hub, or SyllabusMapper, so those Replit apps cannot be tied to this codebase from the repo alone; treat them as dead branches until the Replit connector says otherwise.

## Handoff assets present and used

| Asset | Used in WP-1 as |
|---|---|
| `skill.zip` (ChatGPT, complete) | canonical renderer + skill references → `skills/harrity-lesson-builder-pipeline/` |
| `stage9/generate_lesson_package.py` v1.1 | gate + package writers → `scripts/validate_and_gate.py` |
| `stage9/package-schema.md` v1.1 | → `references/package-schema.md` v1.2 |
| `migration_ch1/lesson_spec.json` | test fixture `fixtures/ch1_migrated_lesson_spec.json` |
| Drive `harrity_master_lesson_template/` (schema, template, validator, README) | governance envelope source → `references/master_lesson/` |
| `source/SRC01_openrn_healthpromo_ch4_index.json` | not yet used (WP-2 input) |
| `skill_v2` (2026-05-09) | not merged; kept under `handoff/skills_in_hand/` |

Not read: Drive `nclex-rn-2026/` folder (the repo copy under `curriculum_exports/` is the same export), Airtable bases, Jotform forms, Replit apps.
