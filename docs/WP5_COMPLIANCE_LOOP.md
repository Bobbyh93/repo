# WP-5 — Compliance loop: lesson package → BRN Evidence Registry

Date: 2026-09-07 (corrected from the 2026-09-06 first draft) · Status: built and tested against a simulated base; **no live write has been made**. First live run waits on the reference lesson reaching `release-ready`.

## The correction that matters

The first draft created a **new** Evidence Registry record per lesson per requirement (`EV-LESSON-<package>-<req_id>`). Reading the live base on 2026-09-07 showed that was wrong and would have polluted an accreditation registry.

The base already has its own model, in use since December 2025:

| Table | Real convention |
|---|---|
| `Evidence Registry` | **one stable evidence pack per requirement**, keyed `EV-<req_id>` — `EV-BRN-14`, `EV-BRN-17`, and so on. 37 records exist (26 requirement packs plus 11 EDP-P-16 process packs). `Evidence Status` is Missing or Received *for the requirement*. |
| `Attachments` | **one record per artifact**, linked to the pack(s) it serves via `evidence_link`, with provenance in `notes` as `key: value` lines and routing written as `route to EV-BRN-07, EV-BRN-12`. |

Filing a lesson is therefore an *Attachments* operation, not an Evidence Registry one. Had the original run gone ahead, BRN-14 would have had two competing records: the program's own pack and a lesson-specific one. An auditor reading the registry would see a duplicated requirement.

## What the script does now

1. Resolves each `lesson.standards_refs` ref to the existing pack `EV-<req_id>`. **It never creates a pack.** If one is missing it refuses with the name, before writing anything.
2. Upserts one Attachments record per package file, matched by `attachment_name` (`<package_id>/<filename>`), linked to those packs, carrying release status, source and licence, slide and item counts, clinical-judgment coverage, and the routing line.
3. Only with `--mark-received` does it flip a pack from Missing to Received. That is a claim that the requirement now has evidence, which is a sufficiency judgement, so it stays off by default and reports what it left unchanged.

## Verified against the live base (read-only, 2026-09-07)

- `req_id` is a singleSelect already containing BRN-01…BRN-25; BRN-14 and BRN-17 are existing choices, so no new option is invented.
- `Evidence Status` accepts exactly `Missing` and `Received`.
- `ingest_status` accepts `: New`, `Linked`, `Needs Review`; the script writes `Linked` when a Drive URL is supplied and `Needs Review` otherwise, with `missing_file_flag` set to match.
- Packs `EV-BRN-14` and `EV-BRN-17` both exist and are currently `Missing`.

## Safety properties

- Dry run by default, writing `package/compliance_payload.json`; nothing leaves the machine.
- `--apply` needs `AIRTABLE_TOKEN` and a `release-ready` manifest (exit 3 otherwise; `--allow-unreleased` is for a sandbox base).
- Matching is done by listing records and comparing in Python, not with `filterByFormula`. Airtable has no documented escape for quotes or braces inside a formula string, and a formula that silently fails to match would create a duplicate instead of updating. Listing removes that failure class.
- Every Airtable error is caught and translated (401 bad token, 403 no write scope, 404 schema drift, 422 rejected values, 429 rate limit), the partial payload is written, and the exit code is 5. Re-running recovers because attachments match by name.
- Requests are paced at 4/second against Airtable's 5/second limit.
- The token is read from the environment, never written to the payload or printed. A test asserts this.
- Nothing is ever deleted, and packs for requirements this lesson does not claim are untouched (also tested).

## Run

```bash
S=skills/harrity-lesson-builder-pipeline/scripts
python $S/compliance_sync.py lessons/openrn_hp_ch4/lesson_spec.json \
    --drive-url "https://drive.google.com/drive/folders/1nlWNVHgl3E7a_ai6DvR3fqNYkewK2ZCi"
AIRTABLE_TOKEN=pat… python $S/compliance_sync.py lessons/openrn_hp_ch4/lesson_spec.json \
    --drive-url "…" --apply [--mark-received]
```

## Not done

- Live apply. Waits on release-ready and a personal access token with write scope.
- Uploading files into Airtable's `file_attachment` field, which needs a publicly reachable URL. The `source_url` Drive link is the interim answer.
- CCNE hub base and BVNPT: same pattern, different snapshot file.
- EDP-P-16 `curriculum_narrative` generation from released packages.

## Open question for the reviewer

The base's existing packs are per requirement, so a second released lesson also claiming BRN-14 will add its attachments to the same pack. That is correct, but it means a pack's `Evidence Status` says nothing about *which* lessons contributed. If you want per-lesson evidence visible in the registry itself rather than only in Attachments, say so and the model can carry a lesson roll-up field instead.
