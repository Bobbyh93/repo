---
name: lesson-release
description: Drive a Harrity lesson package from review-needed to release-ready. Use this whenever the user wants to QA a lesson deck or package, check slides visually, validate or import the Common Cartridge (.imscc) into Canvas or another LMS, verify slides against their cited source, promote evidence status (source-aligned to source-grounded), release a lesson, file a released lesson as accreditation evidence in the BRN Airtable base (Evidence Registry), or asks "is this lesson ready", "ship it", "release", "check the deck", "verify against Open RN" — even if they don't name the skill. Also use it after any change to a lesson_spec.json so the package is regenerated and the status recomputed. There is no approval workflow: defects alone decide status.
---

# Lesson release

Four phases, each a script in `skills/harrity-lesson-builder-pipeline/scripts/`. The scripts do the mechanical work and write reports; you read the reports and the artifacts and make the judgment calls; the human signs the decisions. That split is deliberate: the gate can only lower a release status, and nothing in this skill can raise one without a named reviewer.

Paths below assume the repository root. A lesson lives at `lessons/<name>/lesson_spec.json` with its package in `lessons/<name>/package/`.

## 1. QA the package (`qa`)

```bash
python skills/harrity-lesson-builder-pipeline/scripts/qa_visual.py lessons/<name>/package [--canvas-course-id ID]
```

Produces `package/qa_visual/report.json`, `slide-NN.png` thumbnails and `contact_sheet.png` when LibreOffice and pdftoppm are present. Then:

1. Read `report.json`. `structural_pass` false means fix the spec first; do not look at pixels on a broken package.
2. If `render.ran` is true, Read `contact_sheet.png` and look for: text running past its box or off the slide, empty body regions, cards with only a title, footers overlapping content, the wrong slide count. Open individual `slide-NN.png` for anything suspicious. `possible_text_overflow` is a heuristic hint, not a verdict — check those slides first.
3. Fix layout problems in the lesson's `build_spec.py` (or `lesson_spec.json` if the lesson is past its authoring stage), rebuild, re-run the gate, re-run qa. Shorten bullets or split a slide rather than loosening the density budget.
4. If `render.ran` is false, say so plainly: the visual gate is still open and the deck has to be opened in PowerPoint by a person.
5. Canvas import runs only when `CANVAS_BASE_URL` and `CANVAS_TOKEN` are set and a sandbox course id is given. Read `canvas_import` in the report: `completed` plus a non-zero quiz count is a pass. Never point this at a live course.

Record what passed with a reviewer name (the person who looked, not you):

```bash
python .../record_gate.py lessons/<name>/lesson_spec.json gate-pass visual_qa --by "Name" --note "contact sheet reviewed, no overflow"
python .../record_gate.py lessons/<name>/lesson_spec.json gate-pass lms_import --by "Name" --note "Canvas sandbox course 123: migration completed, 1 quiz, 10 items"
```

## 2. Verify slides against the source (`verify`)

```bash
python skills/harrity-lesson-builder-pipeline/scripts/verify_sources.py lessons/<name>/lesson_spec.json --out lessons/<name>/verification --fetch
# or, when the network is blocked, with a saved chapter page:
python .../verify_sources.py lessons/<name>/lesson_spec.json --out lessons/<name>/verification --html SRC01=/path/chapter.html
```

The script measures term overlap between each sourced slide or item and the source text, names the best-matching section, and suggests `keep-as-is`, `promote`, `review`, or `flag`. Overlap is not faithfulness: a slide can reuse every noun and still misstate the claim. So for every `promote` and `review` row:

1. Open `verification/sources/<SRC>.txt`, go to the best-matching section, and read the slide's bullets and card text against it.
2. Check the tables the index flagged as unretrievable (`sources/<SRC>.tables.json`): if the slide was written from section-body facts and the table now says something different, the slide changes, not the status.
3. Promote only when every clinical claim on the slide is stated or directly implied in the source. Cite the section in `--evidence`.

```bash
python .../record_gate.py lessons/<name>/lesson_spec.json promote S05 --to source-grounded --by "Name" --evidence "4.2 Family Structures: five functions listed verbatim; Table 4.2 checked"
```

`flag` rows with "source text unavailable" mean the fetch failed; report that and stop, do not guess. A `flag: low overlap` on a `source-aligned` slide is a real finding: either the slide drifted from the source or it cites the wrong section.

## 3. Release (`set-release`)

There is no sign-off workflow: no approval keys, no taxonomy lock, no signature. If the package is clean, declaring it release-ready is enough.

```bash
python .../record_gate.py lessons/<name>/lesson_spec.json set-state release_ready
python .../record_gate.py lessons/<name>/lesson_spec.json set-release release-ready
python .../record_gate.py lessons/<name>/lesson_spec.json status
```

Every command re-runs the gate and prints `release_status_computed`. The computed status is the truth: if it says `review-needed` after you set `release-ready`, the gate found a **major defect** — that is the only thing that can hold a package back now — and the QA log says which. Fix the cause; do not re-issue the command.

`status` with no write is the right first move when the user asks "where is this lesson at".

## 4. File the evidence (`compliance`)

Once the computed status is `release-ready`, the package is accreditation evidence for the CA BRN requirements named in `lesson.standards_refs` (framework `CA-BRN-ART3`, `req_id` values from the base). The builder proposes those refs; confirm with the reviewer which apply before filing, because an Evidence Registry record is a claim to an auditor.

```bash
python skills/harrity-lesson-builder-pipeline/scripts/compliance_sync.py lessons/<name>/lesson_spec.json            # dry run, always first
AIRTABLE_TOKEN=… python skills/harrity-lesson-builder-pipeline/scripts/compliance_sync.py lessons/<name>/lesson_spec.json --apply
```

Read `package/compliance_payload.json` from the dry run and show the reviewer the evidence descriptions before `--apply`. Apply refuses unreleased packages and missing tokens; it updates existing records on re-release rather than duplicating them. Details in `docs/WP5_COMPLIANCE_LOOP.md`.

## Reporting back

Lead with the computed release status and what changed it. Then, in one short list: gates recorded, promotions made (slide, from, to, evidence), evidence filed (evidence_ids, or dry-run only), and anything still open with who has to act. Point to `package/qa_log.md` and `verification/verification_report.md` rather than restating them.

## Why the spec is edited in place

`build_spec.py` authors the first version. Once review starts, `lesson_spec.json` is the record: `record_gate.py` appends to `revision_log` with stable IDs and reruns the gate, which is the Stage 13 lock the pipeline expects. Re-running `build_spec.py` after review would erase the revision log and any recorded evidence promotions, so do not, unless the user asks to restart authoring.
