# Review handoff — Family Dynamics at the Bedside (HP-CH4 R1)

Date: 2026-09-06 · Status: `review-needed` · Revision R01 (AI visual review recorded)

## Where things are

| What | Where |
|---|---|
| Package of record | `lessons/openrn_hp_ch4/package/` (PPTX, PDF, thumbnails, cartridge, guides, manifest) |
| Spec of record | `lessons/openrn_hp_ch4/lesson_spec.json` (do not re-run `build_spec.py` once the revision log has entries) |
| Drive review folder | https://drive.google.com/drive/folders/1nlWNVHgl3E7a_ai6DvR3fqNYkewK2ZCi — REVIEW CHECKLIST (Google Doc), README, facilitator guide, QA log, `.imscc` |
| Drive `sources/` | https://drive.google.com/drive/folders/1hFywSA2NleioUVUY25Ll9B4bQ3lVvzKP — `source_registry.json` (SRC01 registered; OpenStax blocked with the license contradiction and the 30+ Drive copies inventoried, nothing trashed) |
| Review tooling | `.claude/skills/lesson-release/SKILL.md` |

## What was executed in the build container

- Visual QA: LibreOffice Impress installed, PyMuPDF fallback added, all 20 slides rendered, six layout defects fixed, re-rendered clean. Gate `visual_qa_ai` recorded; human `visual_qa` still open.
- Cartridge structurally validated; Canvas import not run (no token).
- Compliance sync dry run produces two Evidence Registry records (BRN-14, BRN-17); apply refused until `release-ready`.

## What is blocked in the build container and why

Every source host is refused by the egress proxy: wtcs.pressbooks.pub, ncbi.nlm.nih.gov, ftp.ncbi.nlm.nih.gov, med.libretexts.org, openstax.org, web.archive.org. So: no source verification, no table retrieval, no OpenStax license check. All four are one command each from a machine with normal network access (see the REVIEW CHECKLIST).

## Remaining steps, in order

The sign-off workflow was removed on 2026-09-11: there are no approval keys, no
taxonomy lock, and no signature needed to release. Only defects hold a package back.
Steps 1-4 below are optional quality work, not gates — do the ones you want.

1. Open the PPTX; record `visual_qa` if you want it logged.
2. `verify_sources.py --fetch`; `promote` slides that hold up against the source.
   (`promote` still takes `--by` and `--evidence`: calling a slide `source-grounded`
   is a claim someone checked it, and the spec records who.)
3. Confirm BRN-14 / BRN-17, decide BRN-16 — needed only for the compliance filing.
4. Canvas sandbox import; record `lms_import` if you want it logged.
5. `set-release release-ready` — one command, no signatures.
6. `compliance_sync.py --apply` with `AIRTABLE_TOKEN`.
