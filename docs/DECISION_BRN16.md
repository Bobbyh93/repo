# Decision memo — should the Family Dynamics lesson claim BRN-16?

Prepared 2026-09-11 for step 3 of the review handoff ("Confirm BRN-14 / BRN-17,
decide BRN-16"). This memo does the analysis so the step is a yes/no rather than
a research task. **The decision is yours**; the recommendation is mine and the
reasoning is below so you can overrule it on facts I could not reach.

## The three refs, side by side

| ref | CCR | Requirement (base's label) | Currently claimed | Artifact the claim rests on |
|---|---|---|---|---|
| BRN-14 | 1426(b) | Curriculum unifying theme & nursing process | **yes** | S14 process map + the CJM coverage matrix |
| BRN-17 | 1426(f) | Tools to evaluate student progress | **yes** | 10 assessment items + `traceability_matrix.csv` |
| BRN-16 | 1426(d) | Concurrent theory and clinical practice; core nursing areas and content | **no** | — |

BRN-14 and BRN-17 are sound: each names a specific artifact in the package that a
reviewer can open, and each `basis` string in `lesson_spec.json` points at it.
That is the standard the third claim has to meet.

## Recommendation: **no — do not add BRN-16 to this lesson**

1426(d) has two limbs, and the lesson package can only speak to one of them.

**Limb 1, concurrency, is not a lesson fact.** "Concurrent theory and clinical
practice" is a statement about how the *program schedules* students — whether
theory and clinical run together. No slide, handout, cartridge or manifest this
pipeline emits can evidence it. The evidence lives in a course schedule or
syllabus showing co-enrollment, at program level. Filing a lesson package against
this limb would put an artifact in the Evidence Registry that a BRN reviewer
would open and find silent on the thing the requirement asks about.

**Limb 2, core areas and content, needs a curriculum map this lesson does not
carry.** The content half could in principle be evidenced by lesson material, but
only against a map naming which core nursing area the lesson serves. The spec
records `course_code: NHP` and `chapter_title: Family Dynamics` and asserts no
core-area mapping. Health-promotion and family content sits under community
health or fundamentals depending on the program — that is a curriculum-map fact
held by the program, not something this lesson declares or I can infer.

So on the evidence in the package, BRN-16 would be an over-claim: a record in the
accreditation registry asserting more than the artifact supports. That is the
exact failure mode the 2026-09-11 audit spent two passes closing, arriving from
the other direction — not a tool certifying something false, but a human claim
the tools cannot check.

## The tooling will not stop you, and that is worth knowing

I tested it. Adding BRN-16 to `lesson.standards_refs` produces **no defect at any
severity**: `status: faculty-review-needed, blocked: False, defects mentioning
BRN-16: NONE`. The gate validates that a ref exists in the framework snapshot —
`BRN-16` does, as `recKMNZXZfJRZQacZ` / 1426(d) — and it has no way to judge
whether the lesson evidences the requirement. Nothing downstream catches it
either: `compliance_sync` would look up `EV-BRN-16`, find the pack, and link
eleven attachments to it.

This is not a gap to fix. A checker cannot read a regulation and decide whether a
deck satisfies it; that judgment is what the seven approvals are for. It is worth
stating plainly because every *other* over-claim in this pipeline now gets caught,
which makes it easy to assume this one would be too.

## What would change the answer

Two facts I could not reach. Either would make BRN-16 defensible:

1. **The program's `EV-BRN-16` pack is an aggregate** in which concurrency
   evidence is supplied separately at program level, and lesson artifacts are
   filed only against the content limb. If the pack is scoped that way, a lesson
   contribution is appropriate. I could not check: this session's Airtable tools
   do not include record listing, so I never read the pack.
2. **The curriculum map names Family Dynamics under a core area** covered by
   1426(d). If it does, the content limb has a basis and the `basis` string should
   cite the map, not the lesson.

If you confirm either, the change is one line:

```json
{"framework_id": "CA-BRN-ART3", "ref": "BRN-16",
 "basis": "1426(d): <name the artifact or the curriculum map that carries it>"}
```

then re-run the gate so the manifest and payload pick it up.

## Assumptions logged

- That `ca_brn_article3_requirements.json` (snapshot 2026-09-06) still matches the
  live base. The snapshot's `text_policy` is `public-domain`, so quoting the
  section label here is within policy; no AACN/QSEN text appears in this memo.
- That the lesson's scope is unchanged since the spec was authored — one chapter
  of Open RN Health Promotion, no clinical component.
- I did **not** read the CCR text itself. Every source host remains blocked by the
  egress proxy (`403` at CONNECT, re-confirmed 2026-09-11), so the analysis rests
  on the requirement labels in the snapshot and the lesson's own content. If the
  precise wording of 1426(d) matters to your decision, read it before deciding —
  my reading of "concurrent" as a scheduling fact is the load-bearing inference
  and it comes from the label, not the regulation.
