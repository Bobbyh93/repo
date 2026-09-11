# Silent-pass audit of the lesson gate — 2026-09-11

Addendum to `HARDENING_2026-09-07.md`. That review covered the code that touches
credentials and external systems, and closed with:

> **Not reviewed.** The renderer and the gate itself … touch no credentials and
> no external system, and are covered by the merge tests.

That exclusion used blast radius as its criterion and measured it in the wrong
units. The gate handles no secrets, but its PASS is what certifies a nursing
lesson for faculty sign-off and, downstream, becomes accreditation evidence
against CA BRN Article 3. A wrong PASS there is not a leaked token; it is a
lesson entering a curriculum, and an evidence record asserting it was reviewed.
This audit covers what that section deferred.

## Scope and what was audited

| | |
|---|---|
| **Subject** | `validate_and_gate.py`, `validate_unified_package.py`, `record_gate.py`, `verify_sources.py`, `compliance_sync.py`, `qa_visual.py`, `export_lms.py` |
| **Claim under test** | "No check may report PASS because its input was absent" |
| **Downstream of a PASS** | `release-ready` in the manifest → faculty sign-off → `compliance_sync` writes an Attachment to the BRN Evidence Registry |
| **Suite at start** | 33 passed, 0 failed |
| **Suite at end** | 54 passed, 0 failed (20 new cases plus one amended; every reproduction case shown to fail on the pre-fix code) |

**Assumption logged:** that `qa.gates_passed` is intended to be load-bearing
rather than advisory. The field is written by `record_gate.py gate-pass`, is
carried into the manifest, and is named in the skill's four-phase procedure as
the record that QA occurred — so it is treated here as a requirement, not a note.
If the intent was advisory, D1's control is wrong and should be reverted rather
than adjusted.

## Register

Severity is by consequence: **Critical** = the tool certifies what it should
have blocked. **High** = blocks compliant work, or verifies materially less than
its name claims. **Medium** = unreliable in a reachable condition.

| ID | Sev | Defect | Failure mode in production | Control |
|---|---|---|---|---|
| **D1** | Critical | `validate_governance` computed `release-ready` from the seven approvals and the taxonomy lock. `qa.gates_passed` was written, carried into the manifest, and **never read by any condition**. | Seven human sign-offs are attestations of intent; none of them is evidence anyone looked at the rendered deck. A package no one had opened certified as `release-ready`, the manifest listed the QA gates as passed, and `compliance_sync` filed it as accreditation evidence. Reproduced: a fully-approved demo spec with **no** `gates_passed` at all returned `status: release-ready`. | `release-ready` now requires every gate in `qa.required_gates`, defaulting to `["visual_qa"]`. Absent gates are a `major` defect naming what is missing. |
| **D2** | Critical | In `validate_unified_package.py`, the deck/manifest comparison sat under `if slides:`, and the artifact-existence loop iterated `manifest["files"]`. Both collections come from the manifest under inspection. | A truncated or half-written build leaves a manifest describing nothing. The validator then had nothing to compare and reported success. The tool's own output convicted it: <br>`=== H1: manifest claims zero slides, deck has 20 ===`<br>`[PASS] No validation errors found.`<br>A 20-slide deck certified against a manifest asserting it had none. | A manifest listing zero slides is now an error ("nothing can be checked against the deck"); an empty `files[]` is an error ("the package claims to contain nothing"). The count comparison no longer sits behind a truthiness guard. |
| **D3** | High | `record_gate.py gate-pass` accepted any string. `KNOWN_GATES` did not exist. | The operator runs `gate-pass visaul_qa`, sees `recorded R08: gate-pass by …`, and believes the visual QA is on file. It is on file — as a string no check will ever match. Combined with D1 this is the realistic path to a false release, because the operator did the work and the record silently does not count it. Reproduced: <br>`manifest release_status: release-ready`<br>`manifest gates_passed  : ['visaul_qa', 'totally_made_up_gate', 'deck_render', 'package_manifest']` | 15-name `KNOWN_GATES`; `gate-pass` exits non-zero on an unknown name and writes nothing, with `--new-gate` as the deliberate escape hatch. The gate also raises a `minor` for unknown names already in a spec. |
| **D4** | High | The CJM coverage check excused **every** missing function whenever `qa.cjm_coverage_rationale` was non-empty, regardless of what the rationale said. | CJM mapping is the lesson's link to the NCSBN clinical judgment model and the reason the package is accreditation evidence at all. One sentence — "Short package; coverage addressed in the unit exam" — cleared all six functions. A lesson mapped to the model in no way passed the check named for that mapping. | Zero mapped functions is now a `blocker` that no rationale can clear ("a coverage rationale cannot stand in for the mapping itself"). A partial gap is excused only for the functions the rationale **names**; unnamed gaps stay blockers. |
| **D5** | Medium | `record_gate.py status` with no package directory omitted `release_status_computed` entirely and printed the declared status. | A key that is absent reads as agreement. The operator saw `release_status_declared: release-ready` with nothing contradicting it, on a run that computed nothing. | The key is always present, set to `"not recomputed (no package directory)"`, with a `[note]` on stderr saying how to get a real recomputation. |
| **D6** | High | `verify_sources.py` recorded a partial fetch ("fetched 3/12 urls") **only in the string returned by that run**. The cache it wrote carried no provenance. | The egress proxy blocks most Pressbooks URLs, so partial fetches are this repo's normal condition, not an edge case. On the next run the cache was read and reported as `cache <path>` — a verification against a quarter of the chapter was indistinguishable from one against all of it. Worse, `--fetch` short-circuited on the cache and never retried the missing sections. | Every cache is written with a `<SRC>.provenance.json` sidecar recording urls attempted, succeeded, failed, and a `complete` flag. A cache with no sidecar reads as **unknown, therefore incomplete**. `--fetch` over a partial cache re-attempts the missing URLs. `how` carries `[PARTIAL: n/m sections]`. |
| **D6b** | High | (The same defect, pointing the other way.) A low-overlap result against a partially-loaded source was reported as `flag: low overlap`. | Against a half-loaded chapter, "this claim is not in the source" and "the section holding it never downloaded" are the same number. The report accused the lesson of unsupported claims on the strength of a network failure — and a faculty reviewer acting on it would rewrite correct material. | A sub-threshold result against an incomplete source now returns `cannot verify: source text incomplete`. High-overlap results are still reported, because those terms were positively found in text that did load. |

## Why the existing suite could not see any of this

The suite varied one axis: **the lesson**. Every case built a spec, injected a
defect into it, and asserted the gate fired. Thirty-three cases, one dimension.

Nothing varied the operator's inputs or the record of QA. No case passed a
mistyped gate name, a manifest that described nothing, a rationale that excused
the wrong thing, or a source cache that had loaded half a chapter. Each of those
defects was invisible **by construction**: the suite could not distinguish a
check that examined a correct lesson from a check that examined nothing, because
it never supplied nothing.

Three of the six (D1, D3, D5) are specifically about the *record of review*
rather than the lesson — `gates_passed`, the gate-name vocabulary, the computed
status. That subsystem had no test of any kind. It is the subsystem a faculty
reviewer's trust actually rests on, because it is what they read instead of
re-opening the deck.

The twelve new cases are labelled by defect ID and were placed on the axis the
suite was missing, not added as more lesson-shaped cases. Each was run against
the pre-fix code first and confirmed to fail:

```
tests/test_merge.py          d1 ×2, d2 ×2, d4 ×2                        6 failed
tests/test_release_tools.py  d3 ×2, d6 ×4, + the amended release-ready   7 failed
```

`test_release_ready_requires_all_approvals_and_lock` was amended rather than
added: it asserted `release-ready` after the seven approvals and the lock, which
is precisely the certification D1 allows. It now asserts that state is refused,
then records `visual_qa` and asserts release-ready follows. Its failure against
the fixed code was the first evidence the D1 control works end to end through
`record_gate.py`, not only inside the gate.

## What this changes for the outstanding manual steps

The six steps awaiting the user are unchanged in substance, with one addition
that D1 makes explicit rather than optional:

- Recording the seven approvals and the taxonomy lock **no longer produces
  `release-ready` on its own.** `visual_qa` must also be recorded, by someone who
  opened the PPTX. That is the intended order and was always the documented
  procedure; it is now enforced.
- `verify_sources.py --fetch` will report `[PARTIAL: n/m sections]` while the
  egress proxy blocks Pressbooks. Slides scoring below threshold against a
  partial chapter now read `cannot verify` rather than `flag`, and must not be
  treated as content findings.

## Second pass — the filing path (D7–D9)

The first pass scoped itself to the gate and left out `compliance_sync.py` on
the grounds that the 2026-09-07 review had covered it. That review covered its
*credential and API* behaviour. Nobody had asked whether its checks could pass
on an absent input — and it is the script that writes the accreditation record,
so it is the last place that omission should have stood.

| ID | Sev | Defect | Failure mode in production | Control |
|---|---|---|---|---|
| **D7** | Critical | The attachment loop iterates `manifest["files"]`, and nothing asserted it was non-empty. | A run that filed **nothing** reported a clean dry run and exit 0, and `--apply` would have accepted it, because the refusal is gated on `problems` being empty. The operator sees a successful filing and a BRN Evidence Registry that gained no evidence. Reproduced: <br>`"attachment_records": 0,`<br>`"problems": [],`<br>`exit: 0` | An empty `files[]` is a problem: "there is no artifact to file as evidence". `--apply` refuses. |
| **D8** | Critical | `compliance_sync.py` contained no `exists()` call anywhere. `p = package_dir / f` was used only for `p.suffix`, and `missing_file_flag` was computed from whether a `--drive-url` was supplied. | An Attachments record naming a path that is not on disk reads, in the accreditation record, as evidence on file. The field's own name convicts it — with the reference deck deleted and a drive URL supplied: <br>`"file": "…/20260906_NHP_Family_Dynamics_Part_1.pptx",`<br>`"ingest_status": "Linked",`<br>`"missing_file_flag": false` <br>The one field named for whether the artifact is missing was the one field that never looked. | Each listed file is checked on disk. A file that is not there is a problem naming it, so `--apply` refuses before any Airtable write. `missing_file_flag` is now `(not on_disk) or (not drive_url)`, and `ingest_status` requires both. |
| **D9** | High | `visual_gate_ready` was `bool(render.ran)`, and `ran` meant only that the rasteriser produced **at least one** image. Thumbnails were never counted against slides. | This is the partial-read shape (D6's sibling) on the flag that matters most after D1: `visual_gate_ready` is what tells the operator the one remaining gate can be recorded, and recording it is now the last thing between a package and `release-ready`. One thumbnail from a twenty-slide deck read as ready. Reproduced end to end on a deck with **no slides** — LibreOffice emits one blank page — which reported `visual_gate_ready: True`. | `thumbnails_cover_deck` requires a non-zero slide count and one thumbnail per slide; `visual_gate_ready` requires both that and `ran`. A short render records why. The verdict logic moved into `finalize()` so it can be tested without a rasteriser. |

### `export_lms` and `qa_visual`'s structural checks: probed, nothing found

Both were scanned and then read at every verdict-bearing site. Two shapes looked
like leads and are not:

- `validate_cartridge` compares `len(qitems) != expected_items` whenever a quiz
  resource exists, so a zero-item QTI against ten expected items is caught. The
  `expected_items is not None` guard closed on 2026-09-07 is the only thing that
  could have made it vacuous.
- `qa_visual`'s `slide_count_matches_manifest` compares unconditionally, unlike
  `validate_unified_package` before D2 — an empty manifest against a full deck
  fails correctly. Its one vacuous case, zero slides against zero slides, is
  caught by `structural_pass`, which now also fails because the D2 fix makes the
  package validator exit 1 on a slide-less manifest. That is D2's control
  reaching a second consumer, which is what a boundary fix is supposed to do.

The remaining scanner hits in both files are `.get()` calls on presentation
content — a slide's optional `activity_prompt` or `learning_objective`. They
feed rendering, not verdicts, and an absent one means the slide genuinely has no
such field.

## Not fixed, and why

- **The renderer** (`generate_lesson_package.py`) produces the artifact rather
  than certifying it. A renderer bug shows up as a visibly wrong slide, which is
  the loud failure mode, not the silent one.
- **`spec_adapter.py`** was not audited. It translates between schemas and makes
  no pass/fail claim, so it has no verdict to be vacuously true. Its pass-through
  keys are already reported as `minor` defects by the gate.

## Honest note on the D9 regression cases

Three of the four D9 cases exercise `finalize()` directly and fail on the
pre-fix code with `AttributeError`, because that function did not exist — a
structural failure, not proof of the behaviour. The fourth
(`test_d9_end_to_end_empty_deck_does_not_open_the_visual_gate`) runs the CLI on
a slide-less package and fails on the old code with `assert True is False`
against `visual_gate_ready`. That one is the decisive case; the other three
guard the logic once the boundary exists.
