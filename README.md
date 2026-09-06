# Harrity Lesson Builder — merged pipeline

One data model, one renderer, one gate. Source-grounded, map-first nursing lesson packages (PPTX + facilitator guide + learner handout + assessment map + traceability matrix + manifest + QA log) from a single `lesson_spec.json`.

```
lesson_spec.json (schema 1.2)
   │  skills/harrity-lesson-builder-pipeline/scripts/validate_and_gate.py
   ├─ validate: 26-field slide contract, evidence/source enforcement, CJM coverage,
   │            traceability, governance envelope (master-lesson 1.0.0)
   ├─ adapt:    spec_adapter.py  → renderer slide dict
   ├─ render:   generate_lesson_package.py (canonical renderer, 26 archetypes)
   └─ write:    guides, assessment_map.csv, traceability_matrix.csv,
                lesson_manifest.json, qa_log.md   (_DRAFT stamped on any blocker)
```

## Run

```bash
pip install -r requirements.txt
python skills/harrity-lesson-builder-pipeline/scripts/validate_and_gate.py --demo --outdir out/demo
python skills/harrity-lesson-builder-pipeline/scripts/validate_and_gate.py --spec fixtures/ch1_migrated_lesson_spec.json --outdir out/ch1
python skills/harrity-lesson-builder-pipeline/scripts/validate_unified_package.py out/demo
pytest -q tests/
```

Exit codes: `0` clean, `1` rendered with blockers (deck is `_DRAFT`), `2` spec unreadable.

## Layout

| Path | What |
|---|---|
| `skills/harrity-lesson-builder-pipeline/` | the skill: `SKILL.md`, `scripts/`, `references/`, `templates/`, `assets/` |
| `skills/…/references/package-schema.md` | `lesson_spec.json` contract, v1.2 |
| `skills/…/references/renderer-spec.md` | renderer's native format (adapter target; legacy migration source) |
| `skills/…/references/master_lesson/` | master-lesson 1.0.0 schema + template (governance envelope source) |
| `fixtures/` | migrated legacy Ch.1 spec; renderer's own demo in legacy format |
| `tests/test_merge.py` | WP-1 exit criteria as tests |
| `docs/` | WP-0 inventory, WP-1 merge log, WP-4 web-app review |
| `handoff/` | 2026-09-05 handoff materials (read-only history) |

## Constraints carried in the gate

No learner identifiers in any artifact. No CC BY-NC content in packages. Identifier-only for AACN/QSEN text (`text_policy`). Human approval is the terminal gate: the generator can lower a release status, never raise it. Outputs are never Canvas-only.

## Work packages

| WP | Status |
|---|---|
| WP-0 inventory | done — `docs/WP0_REPO_INVENTORY.md` |
| WP-1 merge | done, awaiting review — `docs/WP1_MERGE_LOG.md` |
| WP-4 web app review | done — `docs/WP4_WEB_APP_REVIEW.md` |
| WP-2 reference lesson (Open RN Health Promotion Ch.4) | queued |
| WP-3 LMS-neutral export (`.imscc` + QTI) | queued; scope note in WP-0 (existing exporter is QTI 2.1) |
