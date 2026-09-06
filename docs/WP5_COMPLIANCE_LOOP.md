# WP-5 — Compliance loop v1: lesson package → BRN Evidence Registry

Date: 2026-09-06 · Status: built and tested against a fake Airtable; **no live write has been made**. First live run waits on the reference lesson reaching `release-ready`.

## What it closes

The handoff's §1a: a released lesson package plus its traceability matrix becomes one Evidence Registry record per requirement it satisfies, linked to the `req_id`, with the package files registered as Attachments. That makes the lesson builder and the BRN compliance base one system without new infrastructure.

## Mapping (read from the live base `BRN_Prelicensure_Compliance`, appGEIYBWBAZHFEXR)

| Package | Airtable | Rule |
|---|---|---|
| `lesson.standards_refs[]` with `framework_id: CA-BRN-ART3` | `Evidence Registry` — one record per `ref` | `evidence_id = EV-LESSON-<package_id>-<req_id>`; `req_id` select; `requirements_link` → the Requirements record; `Evidence Status` = `Received` only when the manifest is `release-ready`, else `Missing` |
| `lesson_manifest.json › files[]` | `Attachments` — one record per file | `attachment_name = <package_id>/<file>`; `file` = absolute path (the base's `file` is a text field; `file_attachment` needs a public URL and is left for the Cowork Drive step); `ingest_status = Linked`; `evidence_link` → all evidence records |
| manifest: status, governance, CJM coverage, unmapped counts, sources with licenses | `Evidence Description` | one paragraph an auditor can read without opening the package |

`req_id` → record id and `ccr_section` come from `references/frameworks/ca_brn_article3_requirements.json`, a snapshot of the base's 25 `BRN-nn` rows plus the two process rows, so the gate can validate refs offline. Refresh it when the base changes.

## Who decides what a lesson evidences

The builder proposes; faculty confirms. `build_spec.py` sets BRN-14 (1426(b), nursing process and clinical judgment integrated) and BRN-17 (1426(f), evaluation tools linked to objectives) for the reference lesson, with a `basis` string each, and logs a QA note asking whether BRN-16 (1426(d) integrated content, cultural diversity) also applies. The gate checks each ref exists in the snapshot (minor) and applies the identifier-only length rule.

## Safety rules

- Dry run by default; `--apply` needs `AIRTABLE_TOKEN` and a `release-ready` manifest (exit 3 otherwise; `--allow-unreleased` exists for a sandbox base only).
- Upsert by `evidence_id` / `attachment_name`, so re-releasing updates rather than duplicates (tested: second apply makes zero creates).
- Nothing is deleted; existing evidence packs in the base are untouched.
- No learner data can reach the base: the payload is built from the spec and manifest, which carry none.

## Run

```bash
python skills/harrity-lesson-builder-pipeline/scripts/compliance_sync.py lessons/openrn_hp_ch4/lesson_spec.json            # dry run → package/compliance_payload.json
AIRTABLE_TOKEN=pat… python skills/harrity-lesson-builder-pipeline/scripts/compliance_sync.py lessons/openrn_hp_ch4/lesson_spec.json --apply
```

## Not done

- Live apply (waits on release-ready and a personal access token with write scope on the base).
- File upload to `file_attachment` (needs a reachable URL; pair with the Drive `sources/` housekeeping in Cowork).
- CCNE hub base and BVNPT: same pattern, different snapshot file; not started.
- EDP-P-16 `curriculum_narrative` generation from released packages: v2.
