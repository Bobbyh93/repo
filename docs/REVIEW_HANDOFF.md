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
3. Confirm BRN-14 / BRN-17, decide BRN-16 — see `DECISION_BRN16.md` (recommendation: no).
4. Canvas sandbox import; record `lms_import`.
5. Seven approvals + taxonomy lock + set-state/set-release.
6. `compliance_sync.py --apply` with `AIRTABLE_TOKEN`.

Step 1 is no longer optional in practice. After the 2026-09-11 silent-pass audit
(`SILENT_PASS_AUDIT_2026-09-11.md`), the gate refuses `release-ready` until
`visual_qa` is recorded — step 5 alone will leave the lesson at
`faculty-review-needed`, and step 6 will keep refusing to apply. Four other
behaviours changed and will be visible at the prompt:

- `record_gate.py gate-pass` now rejects a gate name it does not know, rather
  than recording the typo. Pass `--new-gate` if you genuinely mean a new one.
- `qa_visual.py` now reports `visual_gate_ready: false` unless it rendered one
  thumbnail per slide. If it comes back short, the contact sheet does not cover
  the deck and the visual QA is not yet reviewable — re-run the render rather
  than recording the gate off a partial sheet.
- `compliance_sync.py` refuses `--apply` if the manifest lists a file that is
  not on disk, or lists none at all. Both used to produce a clean dry run.
- `verify_sources.py --fetch` reports `[PARTIAL: n/m sections]` whenever some
  source URLs fail. Slides scoring low against a partial chapter now read
  `cannot verify: source text incomplete` — do **not** treat those as content
  findings against the lesson. Re-run once the fetch is complete.
