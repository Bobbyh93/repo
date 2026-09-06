# WP-3 — LMS-neutral export

Date: 2026-09-06 · Status: **exit criterion met** (cartridge passes structural validation; manifest lists `.imscc` in `files[]`). Live LMS import remains a manual step.

## Decision record

| Question | Decision | Why |
|---|---|---|
| Reuse the repo's `nclex-rn-2026` exporter? | No. Ported the pattern only. | It emits QTI 2.1, its QTI file is not registered in the cartridge manifest, and its input is a hard-coded TypeScript array. Nothing there could consume a `lesson_spec` or run inside the Python gate. |
| QTI version | **QTI 1.2, Common Cartridge 1.1 assessment profile** (`cc.exam.v0p1`; item profiles `cc.multiple_choice.v0p1`, `cc.multiple_response.v0p1`, `cc.essay.v0p1`) | This is what Canvas, Moodle and Blackboard import natively from a cartridge. QTI 2.1 is not part of the CC 1.1 profile. |
| Where does the export run? | Inside `validate_and_gate.py`, after the package writers, before the manifest | The `.imscc` name must carry the same `_DRAFT` stamp as the deck and appear in `files[]`. |
| What goes in the cartridge? | `web/index.html`, `web/learner_handout.html`, `quiz/assessment.xml` | Learner-facing only. Speaker scripts, answer keys, and the facilitator guide stay in the package directory. QTI items carry their key and rationale because the LMS grades and reveals them under its own policy. |
| PDF | Best-effort via LibreOffice; logged as a minor defect when unavailable | LibreOffice cannot load files in the build container; the code path is present and exercised on a machine with a working `soffice`. |
| OpenStax license contradiction | Not blocking; OpenStax remains excluded from every package | The reference lesson uses Open RN (CC BY 4.0, verified in SRC01). Recorded in `docs/WP0_REPO_INVENTORY.md`. |
| Non-Canvas targets | Satisfied by CC 1.1 + QTI 1.2 + plain HTML | No Canvas-specific extensions are emitted. |

## Item-type mapping

| `assessment_items[].item_type` | QTI 1.2 rendering | Auto-graded |
|---|---|---|
| `mcq` | `response_lid` Single, `varequal` on the correct letter | yes |
| `sata` | `response_lid` Multiple, `<and>` of `varequal` / `<not>` | yes |
| `matching`, `ordering`, `short-answer`, `retrieval` | `cc.essay.v0p1` with the expected answer in feedback | no (instructor grades) |

Option letters are taken from a leading `A.`/`A)` in the option text when present, else assigned in order.

## Structural validation (`export_lms.validate_cartridge`)

Checks zip integrity, well-formed `imsmanifest.xml`, CC 1.1 root namespace and `schemaversion 1.1.0`, every `resource/file@href` present in the zip, every organization `item@identifierref` resolving to a resource, and, when items exist, one resource typed `imsqti_xmlv1p2/imscc_xmlv1p1/assessment` whose XML parses as `questestinterop` with one `item` per assessment item, each carrying `presentation` and `resprocessing`. XSD validation is not performed (no schema files offline); `tests/test_export.py` includes a negative test.

## Outputs added to the package

| File | Content |
|---|---|
| `web/index.html` | lesson page: question, lanes, per-slide text and card content, activities without keys, attribution |
| `web/learner_handout.html` | HTML twin of `learner_handout.md` |
| `<deck stem>.imscc` | CC 1.1 cartridge |
| `<deck stem>.pdf` | only when LibreOffice succeeds |
| `lesson_manifest.json › exports` | cartridge/assessment versions, resource ids, item count, validation result, pdf name or null |

## Manual step still open

Import `lessons/openrn_hp_ch4/package/20260906_NHP_Family_Dynamics_Part_1.imscc` into a Canvas or Moodle sandbox and confirm the quiz appears with 10 items (8 auto-graded, 2 essay). Record the result in the lesson's `qa.gates_passed` as `lms_import`.
