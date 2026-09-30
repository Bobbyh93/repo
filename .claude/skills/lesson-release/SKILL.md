---
name: lesson-release
description: Drive a gated Harrity lesson package from faculty-review-needed to release-ready. Use this whenever the user wants to QA a lesson deck or package, check slides visually, validate or import the Common Cartridge (.imscc) into Canvas or another LMS, verify slides against their cited source, promote evidence status (source-aligned to source-grounded), record faculty or release approvals, lock the taxonomy, file a released lesson as accreditation evidence in the BRN Airtable base (Evidence Registry), or asks "is this lesson ready", "sign off", "approve", "release", "check the deck", "verify against Open RN" — even if they don't name the skill. Also use it after any change to a lesson_spec.json so the package is regenerated and the status recomputed.
---

# Lesson release

Four phases, each a script in `skills/harrity-lesson-builder-pipeline/scripts/`. The scripts do the mechanical work and write reports; you read the reports and the artifacts and make the judgment calls; the human signs the decisions. That split is deliberate: the gate can only lower a release status, and nothing in this skill can raise one without a named reviewer.

Paths below assume the repository root. A lesson lives at `lessons/<name>/lesson_spec.json` with its package in `lessons/<name>/package/`. Every command block below is runnable as written once `$S` is set:

```bash
S=skills/harrity-lesson-builder-pipeline/scripts
```

## 1. QA the package (`qa`)

```bash
python $S/qa_visual.py lessons/<name>/package [--canvas-course-id ID]
```

Produces `package/qa_visual/report.json`, `slide-NN.png` thumbnails and `contact_sheet.png` when LibreOffice and pdftoppm are present. Then:

1. Read `report.json`. `structural_pass` false means fix the spec first; do not look at pixels on a broken package.
2. If `visual_gate_ready` is true, Read `contact_sheet.png` and look for: text running past its box or off the slide, empty body regions, cards with only a title, footers overlapping content, the wrong slide count. Open individual `slide-NN.png` for anything suspicious. `possible_text_overflow` is a heuristic hint, not a verdict — check those slides first.
3. Fix layout problems in the lesson's `build_spec.py` (or `lesson_spec.json` if the lesson is past its authoring stage), rebuild, re-run the gate, re-run qa. Shorten bullets or split a slide rather than loosening the density budget.
4. If `visual_gate_ready` is false, say so plainly: the visual gate is still open and the deck has to be opened in PowerPoint by a person. Two causes read differently. `render.ran` false means the rasteriser produced nothing. `render.ran` true with `thumbnails_cover_deck` false means it produced fewer images than the deck has slides — `render.reason` says how many — so the contact sheet does not show the whole deck and is not reviewable; re-render rather than signing off on the part that came out.
5. Canvas import runs only when `CANVAS_BASE_URL` and `CANVAS_TOKEN` are set and a sandbox course id is given. Read `canvas_import` in the report: `completed` plus a non-zero quiz count is a pass. Never point this at a live course.

Record what passed with a reviewer name (the person who looked, not you):

```bash
python $S/record_gate.py lessons/<name>/lesson_spec.json gate-pass visual_qa --by "Name" --note "contact sheet reviewed, no overflow"
python $S/record_gate.py lessons/<name>/lesson_spec.json gate-pass lms_import --by "Name" --note "Canvas sandbox course 123: migration completed, 1 quiz, 10 items"
```

`gate-pass` rejects a gate name it does not know and writes nothing, so a typo
fails at the prompt instead of recording QA that no check will ever match. For a
gate genuinely new to the pipeline, pass `--new-gate` deliberately. **`visual_qa`
recorded here is a precondition for §3**: the gate will not compute
`release-ready` without it, however many approvals are on file.

## 2. Verify slides against the source (`verify`)

```bash
python $S/verify_sources.py lessons/<name>/lesson_spec.json --out lessons/<name>/verification --fetch
# or, when the network is blocked, with a saved chapter page:
python $S/verify_sources.py lessons/<name>/lesson_spec.json --out lessons/<name>/verification --html SRC01=/path/chapter.html
```

The script measures term overlap between each sourced slide or item and the source text, names the best-matching section, and suggests `keep-as-is`, `promote`, `review`, or `flag`. Overlap is not faithfulness: a slide can reuse every noun and still misstate the claim. So for every `promote` and `review` row:

1. Open `verification/sources/<SRC>.txt`, go to the best-matching section, and read the slide's bullets and card text against it.
2. Check the tables the index flagged as unretrievable (`sources/<SRC>.tables.json`): if the slide was written from section-body facts and the table now says something different, the slide changes, not the status.
3. Promote only when every clinical claim on the slide is stated or directly implied in the source. Cite the section in `--evidence`.

```bash
python $S/record_gate.py lessons/<name>/lesson_spec.json promote S05 --to source-grounded --by "Name" --evidence "4.2 Family Structures: five functions listed verbatim; Table 4.2 checked"
```

`flag` rows with "source text unavailable" mean the fetch failed; report that and stop, do not guess. A `flag: low overlap` on a `source-aligned` slide is a real finding: either the slide drifted from the source or it cites the wrong section.

`cannot verify: source text incomplete` is not a finding against the lesson. It
means the source on hand is less than the source the spec cites, so low overlap is
unattributable — the claim may be absent, or the section holding it may simply not
have downloaded. Check the source's `complete` and `how` fields in
`verification.json`; `how` carries `[PARTIAL: n/m sections]` when the fetch was
short. Re-run with `--fetch`, which on a partial cache re-fetches the whole source
(every URL, not only the failed ones — a section that did download during a
partly-blocked run may itself be truncated), before reading any row against the
lesson. A cache with no `<SRC>.provenance.json`
sidecar beside it is of unknown completeness and is treated as incomplete.

## 3. Record approvals and release (`approve`)

The master-lesson envelope has seven approvals in sequence: `source_approved`, `taxonomy_approved`, `objectives_approved`, `outline_approved`, `script_approved`, `faculty_approved`, `release_approved`, plus the taxonomy lock. Record each one only when the named person has actually signed off on it in the conversation; never infer an approval from silence or from a passing test.

```bash
python $S/record_gate.py lessons/<name>/lesson_spec.json approve source_approved --by "Name" --note "SRC01 CC BY 4.0 verified 2026-09-05"
python $S/record_gate.py lessons/<name>/lesson_spec.json lock-taxonomy --by "Name"
python $S/record_gate.py lessons/<name>/lesson_spec.json set-state release_ready --by "Name"
python $S/record_gate.py lessons/<name>/lesson_spec.json set-release release-ready --by "Name"
python $S/record_gate.py lessons/<name>/lesson_spec.json status
```

Every command re-runs the gate and prints `release_status_computed`. The computed status is the truth: if it says `faculty-review-needed` after you set `release-ready`, the gate refused, and the QA log says why. There are three causes, and the first is the one that looks like nothing is wrong:

1. **A required QA gate is not recorded.** Approvals are sign-offs; they are not evidence anyone opened the deck. `qa.required_gates` (default `["visual_qa"]`) must all appear in `qa.gates_passed`. This is the confusing case, because `approvals_missing` will be `[]` — every human box is ticked and the status still will not rise. Go back to §1 and record the gate. Set `qa.required_gates` on the spec if this lesson needs more than the default (say `lms_import` too).
2. **An approval is missing** — `approvals_missing` names it, or the taxonomy lock is still `unlocked`.
3. **A blocker or major defect** — the QA log names the slide and the rule.

Fix the cause; do not re-issue the command.

`status` on a lesson with no `package/` directory beside it prints
`release_status_computed: "not recomputed (no package directory)"`. That is not
agreement with the declared status — nothing was computed. Run the gate, or pass
`--outdir`, to get a real answer.

`status` with no write is the right first move when the user asks "where is this lesson at".

## 4. File the evidence (`compliance`)

Once the computed status is `release-ready`, the package is evidence for the CA BRN requirements named in `lesson.standards_refs`. The BRN base models this its own way, and the script follows it: the `Evidence Registry` holds one stable pack per requirement (`EV-BRN-14`), and package files become `Attachments` records linked to those packs. **The script never creates a pack**; if one is missing it names it and refuses, because inventing a requirement record pollutes an accreditation registry.

```bash
python $S/compliance_sync.py lessons/<name>/lesson_spec.json --drive-url "<package folder>"   # dry run, always first
AIRTABLE_TOKEN=… python $S/compliance_sync.py lessons/<name>/lesson_spec.json --drive-url "…" --apply
```

Read `package/compliance_payload.json` from the dry run and show the reviewer which packs will be touched and what the attachment notes say, before `--apply`. Re-running updates in place rather than duplicating.

The dry run refuses — `problems` non-empty, exit 1, and `--apply` blocked — if the
manifest lists a file that is not on disk, or lists none at all. Both mean the
package is not what the manifest claims, and an Attachments record naming a
missing artifact reads in the registry as evidence on file. Regenerate the package
rather than filing it. `missing_file_flag` on each record reflects the artifact
itself, not just whether a `--drive-url` was given.

Adding a `standards_ref` is not checked by anything. The gate validates that the
ref exists in the framework snapshot, and cannot judge whether the lesson
evidences the requirement — so an over-claim passes silently all the way into the
registry. That judgement is the reviewer's; `docs/DECISION_BRN16.md` is a worked
example of making it.

`--mark-received` also flips those packs from Missing to Received. Only pass it when the reviewer has said this lesson is sufficient evidence for the requirement, not merely relevant to it; that is their judgement, not yours. Details and the live-base verification in `docs/WP5_COMPLIANCE_LOOP.md`.

## Reporting back

Lead with the computed release status and what changed it. Then, in one short list: gates recorded, promotions made (slide, from, to, evidence), approvals recorded (key, by), evidence filed (evidence_ids, or dry-run only), and anything still open with who has to act. Point to `package/qa_log.md` and `verification/verification_report.md` rather than restating them.

## Why the spec is edited in place

`build_spec.py` authors the first version. Once review starts, `lesson_spec.json` is the record: `record_gate.py` appends to `revision_log` with stable IDs and reruns the gate, which is the Stage 13 lock the pipeline expects. Re-running `build_spec.py` after review would erase recorded approvals, so do not, unless the user asks to restart authoring.
