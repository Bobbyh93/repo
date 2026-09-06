# Handoff — Build Session 2026-09-05 (evening)

## 1. Deployed / prior work inventory

| Asset | Where | State | Access from this chat |
|---|---|---|---|
| **nursestudy-lesson-builder** web app | Render `srv-d925n4p9rddc7384d0cg`, Node, free plan, Oregon, auto-deploy on `main`, health `/health` | Live at https://nursestudy-lesson-builder.onrender.com ; last deploy 2026-08-27 | Service metadata only |
| Source repo | GitHub `Bobbyh93/Codex_Repo_2026`, branch `main`, `npm ci && npm run build` / `npm run start` | Private (API 403) | **Not readable here.** Needs a surface with your GitHub auth. |
| Replit apps | NursesBrain, NurseStudy, Nurse Remediation Hub, SyllabusMapper (all last touched Jul 3–15); NursesBrain (1), Nursing Insight, Ai Secretary Assistant (May) | Prototypes, none updated since July | Readable via Replit connector |
| `nclex-rn-2026/` | Drive `1rpoKEi0mhf2j_V9tjI5I1WNPs3BwXQXm` | CC + QTI export path, validated | Readable |
| `harrity_master_lesson_template/` | Drive `1jlTAVy_Hwcn_ZMgJPNvt3M77ReNsrHvh` | Schema 1.0.0 + validator | Readable |
| Skill `harrity-lesson-builder-pipeline` — **complete** | `uploads/skill.zip` (977 KB, ChatGPT-built) | All 10 "missing" reference files present, plus `generate_lesson_package.py` (1,284 lines, 20 render archetypes, runs `--demo` clean, PPTX validates), `lesson_spec.template.json`, `reference_montage.png`, `agents/openai.yaml`. Its SKILL.md differs from the project copy. | In hand |
| Skill v2 (2026-05-09) | `uploads/harrity_lesson_builder_pipeline_skill_v2_20260509.zip` | Older, **different** design: `slide_grammar.md`, `student_reception_review`, `package_manifest.schema.json`, CSV templates. A fourth lesson data model. | Migration source only |
| **Airtable** (8 bases) | `BRN_Prelicensure_Compliance` (favorite, `appGEIYBWBAZHFEXR`), `CA RN Compliance MVP (Title 16)`, `CCNE BSN Accreditation Compliance Hub`, `Pearson Concept Framework Loader (Nursing Process)` ×2, `NCLEX 2026 Content Library`, `NCLEX 2026 Roadmap Resource Catalog`, `Content Operations` | Built Nov 2025–Jan 2026. BRN base schema read: Programs · Clinical_Areas · Faculty (compliance_status formula) · Courses (content_areas) · Attachments · EDP-P-02/03/05a/06/10/16 · Checklists · Tasks · **Evidence Registry** · **Requirements (Article 3)** with `ccr_section`, `authority`, `source_url` | Readable |
| **Jotform** (25+ forms) | BRN faculty compliance intake: EDP-P-10 Report on Faculty (v2 API, v3 PDF template), Faculty Intake (BRN), Faculty CE logs, Compliance Automation Event Log, Compliance Dashboard Snapshot, Verification of Faculty Qualifications, BRN File Upload Intake, Clinical Faculty Observation; plus Student Advisement, RN Fundamentals, reference-request forms | Feeds the Airtable BRN base | Readable |
| This session's outputs | `outputs/stage9`, `outputs/migration_ch1`, `outputs/source` | package-schema v1.1, generator, migration, SRC01 index, inventories | — |

Open question the repo review must answer: is the Render app the *same* codebase as any Replit app, or a separate build? Render deploys from GitHub, not Replit, so the Replit apps may be dead branches. Do not invest in them until confirmed.

## 1a. Compliance-first integration (from Airtable/Jotform review)

The Airtable + Jotform work is a second product line — **program and faculty regulatory compliance** (BRN Article 3 requirements → evidence registry → EDP forms) — not lesson content. It already has the two things the lesson builder's standards layer needs, so do not rebuild them:

1. **`Requirements (Article 3)`** (`req_id`, `ccr_section`, `authority`, `source_url`) is the regulatory spine. `taxonomy.frameworks[]` should register `CA-BRN-ART3` with `text_policy: public-domain` and `standards_refs[].ref` = `req_id`. Same pattern for the CCNE hub base and, later, BVNPT.
2. **`Evidence Registry`** (`evidence_id`, `req_id`, type, status, attachments) is where a released lesson package becomes accreditation evidence. A `release-ready` package + its `traceability_matrix.csv` = one Evidence Registry record linked to the `req_id`s it satisfies (curriculum evidence for EDP-P-05a/06 and the EDP-P-16 `curriculum_narrative`). This closes the compliance loop without new infrastructure.
3. **`Courses.content_areas`** / `EDP-P-06 content_area` give `lesson.course_objectives` a place to map upward to BRN-required content. That is the missing top of the traceability chain.
4. **Pearson Concept Framework Loader** is the conceptual-curriculum spine (concept × nursing process). Not read tonight — WP-1 should pull its table list and decide whether `concept_lanes` key to it.

MVP scope: register the framework IDs and leave `standards_refs` empty. Do **not** wire Airtable writes into the generator tonight; manifest → Evidence Registry is a v1 feature. Schema slots only.

## 2. Tonight — objectives, in order

| WP | Objective | Inputs | Exit criterion | Est. |
|---|---|---|---|---|
| **WP-1 Merge (revised)** | One data model, one renderer, one gate. **Renderer = original `skill.zip` generator** (20 archetypes incl. control_room, process_map, exchange_model, triad, safety_chain, compare, risk_engine, teaching_point — visually far ahead of tonight's rebuild). **Gate + contract = tonight's `stage9/generate_lesson_package.py` v1.1** (26-field slide contract, evidence/source enforcement, defect severities, `_DRAFT` stamping, traceability matrix, outcomes/improvement_log — the original has zero evidence_status/source_refs checks). **Envelope = master-lesson 1.0.0** (promotion states, approvals, taxonomy_lock). Build an adapter: v1.1 `lesson_spec` → original renderer's slide dict (`type, title, subtitle, module_label, concept_lane, cjm_steps, speaker_notes, content`); map `card_data` onto its content structures. Keep both files; the original's name stays canonical in the skill, tonight's becomes `validate_and_gate.py` or is folded in. | `skill.zip`, `stage9/`, master-lesson schema | Demo, migrated Ch.1, and the original's own demo all run through gate → render; PPTX validates; no archetype lost; evidence gate still stamps `_DRAFT` on blockers | 90–120 min |
| **WP-2 Reference lesson** | First lesson grounded on a CC BY source. | SRC01 index; Pressbooks tables 4.2/4.3/4.5a/4.5b/4.7 | `lesson_spec` for Open RN HP Ch.4: organizing question, 5 lanes, card_data on ≥6 slides, 8–10 **original** assessment items (CC BY-NC items excluded), `source_refs` on every clinical slide, CJM from §4.7. Status `faculty-review-needed`; you approve → `release-ready` | 90–120 min |
| **WP-3 LMS-neutral export** | Generator emits `.imscc` (Common Cartridge + QTI 1.2) and an HTML/PDF/PPTX bundle. | `nclex-rn-2026` export code, if in repo; else its output files as reference | Cartridge passes structural validation; manifest lists `.imscc` in `files[]`. Live LMS import test is a separate manual step. | 60 min if reusable; 3 h if not |
| **WP-4 Web app review** | Decide rebuild vs redesign. | repo checkout | Screen/route inventory; API surface; which schema the app actually uses; gap list vs the 3-screen flow (source in → review/approve → download); estimate | 45 min read-only |

Sequence: WP-1 → WP-2 → WP-4 → WP-3. WP-3 last because its cost is unknown until WP-4 says whether the July export code lives in the repo.

Hard constraints carried forward: no learner identifiers in any artifact; no CC BY-NC content in packages; identifier-only for AACN/QSEN text; human approval is the terminal gate; outputs never Canvas-only.

## 3. Which surface

| Surface | Use for | Why |
|---|---|---|
| **Claude Code (desktop app or terminal)** | WP-1, WP-2, WP-3, WP-4 | Needs the private repo, local Python/Node, file iteration, git commits, and a longer working budget than chat. This is the build surface tonight. |
| Cowork | Drive housekeeping (dedupe OpenStax copies, create `sources/` + `source_registry.json`), later faculty-review packaging | Multi-connector knowledge work without a repo |
| This chat | Planning, review, decisions | What we've been doing; not for a 4-hour build |

Recommendation: **Claude Code**, opened on a clone of `Codex_Repo_2026`, with this handoff zip unpacked into a `handoff/` folder. Start WP-1.

## 4. Starting prompt for Claude Code

> Read `handoff/HANDOFF.md`. Work packages WP-1 through WP-4 in that order. Before writing code, inventory the repo and report which schema the app uses and whether the `nclex-rn-2026` Common Cartridge/QTI exporter exists here. Then begin WP-1. Log every assumption and every field that changes meaning in the merge. Do not claim a file exists unless you created it. Stop at each exit criterion for my review. Unpack `uploads/skill.zip` first — it is the canonical skill; the project copy was incomplete. Replace `/home/oai/skills/...` paths and drop `agents/openai.yaml` from the Claude-side package.
