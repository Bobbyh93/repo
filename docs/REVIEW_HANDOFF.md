# Review handoff — Family Dynamics at the Bedside (HP-CH4 R1)

Date: 2026-09-06 · Status: `faculty-review-needed` · Revision R01 (AI visual review recorded)

## Where things are

| What | Where |
|---|---|
| Package of record | `lessons/openrn_hp_ch4/package/` (PPTX, PDF, thumbnails, cartridge, guides, manifest) |
| Spec of record | `lessons/openrn_hp_ch4/lesson_spec.json` (do not re-run `build_spec.py` once approvals are recorded) |
| Drive review folder | https://drive.google.com/drive/folders/1nlWNVHgl3E7a_ai6DvR3fqNYkewK2ZCi — REVIEW CHECKLIST (Google Doc), README, facilitator guide, QA log, `.imscc` |
| Drive `sources/` | https://drive.google.com/drive/folders/1hFywSA2NleioUVUY25Ll9B4bQ3lVvzKP — `source_registry.json` (SRC01 registered; OpenStax blocked with the license contradiction and the 30+ Drive copies inventoried, nothing trashed) |
| Review tooling | `.claude/skills/lesson-release/SKILL.md` |

## What was executed in the build container

- Visual QA: LibreOffice Impress installed, PyMuPDF fallback added, all 20 slides rendered, six layout defects fixed, re-rendered clean. Gate `visual_qa_ai` recorded; human `visual_qa` still open.
- Cartridge structurally validated; Canvas import not run (no token).
- Compliance sync dry run produces two Evidence Registry records (BRN-14, BRN-17); apply refused until `release-ready`.

## What is blocked in the build container and why

Every source host is refused by the egress proxy: wtcs.pressbooks.pub, ncbi.nlm.nih.gov, ftp.ncbi.nlm.nih.gov, med.libretexts.org, openstax.org, web.archive.org. So: no source verification, no table retrieval, no OpenStax license check. All four are one command each from a machine with normal network access (see the REVIEW CHECKLIST).

## Remaining human steps, in order

1. Open the PPTX; record `visual_qa`.
2. `verify_sources.py --fetch`; promote slides that hold.
3. Confirm BRN-14 / BRN-17, decide BRN-16.
4. Canvas sandbox import; record `lms_import`.
5. Seven approvals + taxonomy lock + set-state/set-release.
6. `compliance_sync.py --apply` with `AIRTABLE_TOKEN`.
