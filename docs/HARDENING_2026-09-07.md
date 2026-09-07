# Hardening pass — 2026-09-07

An adversarial review of the three scripts that touch live systems, before a
non-engineer runs them against a production accreditation base and a Canvas
course. Findings and fixes below; all 33 tests pass.

## The design defect (found by reading the live base, not the code)

`compliance_sync.py` created a **new** Evidence Registry record per lesson per
requirement (`EV-LESSON-<package>-BRN-14`). The base has used a different model
since December 2025: **one stable evidence pack per requirement** (`EV-BRN-14`),
with artifacts held in `Attachments` and linked to that pack.

Filing the reference lesson would therefore have put a second, competing record
against BRN-14 and BRN-17 in a registry an auditor reads. Rewritten to look the
packs up and refuse if one is absent; the script can no longer create a pack.
See `docs/WP5_COMPLIANCE_LOOP.md`.

## Defects fixed

| # | Where | Defect | Consequence if unfixed |
|---|---|---|---|
| 1 | `compliance_sync` | Airtable **replaces** a link field on PATCH; the update sent the full field set | A link or source URL a coordinator added by hand vanished on the next run. Now links are unioned and a human-entered URL is never blanked. |
| 2 | `compliance_sync` | `typecast: true` on every write | Airtable silently adds a new `singleSelect` option, and treats an unknown string on a link field as a **new record to create** — a record named `recXXXX` could appear in the Requirements table. Typecast is now off and select values are validated against the snapshot. |
| 3 | `compliance_sync` | No error handling on `urlopen` | A non-engineer saw a raw traceback; Airtable's own message, which names the offending field, was discarded. Now every status is translated (401 token, 403 scope, 404 schema drift, 422 values, 429 rate limit), the partial payload is written, exit 5. |
| 4 | `compliance_sync` | No pacing; 26 back-to-back requests against a 5/second limit | Near-certain 429 partway through, leaving the base half-written **and no payload file**, because it was written after the API calls. Now paced at 4/second and the payload is written on the error path. |
| 5 | `compliance_sync` | `filterByFormula` with hand-rolled quote escaping | Airtable has no documented escape for quotes or braces; a formula that silently matched nothing would **create a duplicate** instead of updating. Matching is now done client-side, removing the failure class. |
| 6 | `qa_visual` | The Canvas pre-upload response was written into `report.json` on the failure path | That body carries **signed upload credentials**, written to a file that gets committed. Now only the response's key names are recorded. Regression test asserts the secret never appears. |
| 7 | `qa_visual` | `render.ran` was set true even when the rasteriser produced zero images | `visual_gate_ready` passed with **no thumbnails at all** — a visual gate that never saw a slide. Now a render with no images reports `ran: false`. |
| 8 | `qa_visual` | Exit code ignored the Canvas result; `stderr` of the package validator was discarded; no `.pptx` raised `IndexError` | A failed import reported success to any caller checking the exit code. All three fixed. |
| 9 | `export_lms` | QTI `mattext texttype="text/html"` was escaped once, but it is HTML inside XML | The XML parser decodes once, handing raw `<` to the HTML renderer. **"SpO2 < 90%" truncates the question at the `<`**, and markup would go live. Not triggerable by the current ten items, but nursing text hits it immediately. Now double-escaped, with a regression test. |
| 10 | `export_lms` | `_ident` collapsed all punctuation, so `Q-1` and `Q.1` produced one identifier | A duplicate QTI ident silently drops a question in some LMSs while still validating. Identifiers now carry a short digest. |
| 11 | `export_lms` | `validate_cartridge` skipped the whole QTI check when `expected_items` was 0 | A malformed quiz resource passed validation. Now `is not None`. |

## Known and accepted

- **Changing `runtime_config.runtime.package_id` between runs** produces a second
  set of Attachments records, because the record key embeds it. That is correct
  behaviour for a genuinely new package, but it is worth knowing before renaming.
- **Canvas cartridge import does not de-duplicate.** Re-importing the same
  cartridge adds a second copy of every page and quiz. The report now says so.
  The import is not gated on release status on purpose: importing a draft to a
  sandbox is the point of the `lms_import` gate.
- The `file` field holds a repository-relative path, matching the base's own
  convention; putting the bytes into Airtable's attachment field needs a public
  URL and is not done.

## Not reviewed

The renderer and the gate itself (`generate_lesson_package.py`,
`validate_and_gate.py`, `spec_adapter.py`) touch no credentials and no external
system, and are covered by the merge tests.
