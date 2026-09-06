# WP-1 Merge Log — one data model, one renderer, one gate

Date: 2026-09-06 · Session: claude/new-session-dnyjal · Status: **exit criterion met, pending your review**

## Objective

Merge three lesson-package designs into one pipeline without losing the renderer's visual archetypes or the gate's evidence enforcement:

| Component | Chosen source | Kept as |
|---|---|---|
| Renderer | original `skill.zip` `generate_lesson_package.py` (26 archetypes) | `skills/…/scripts/generate_lesson_package.py` (canonical name unchanged) |
| Gate + contract | Stage 9 `generate_lesson_package.py` v1.1 (26-field slide contract, evidence/source enforcement, defect severities, `_DRAFT` stamping, traceability, outcomes/improvement log) | `skills/…/scripts/validate_and_gate.py` (drawing code removed) |
| Envelope | master-lesson 1.0.0 (promotion states, approvals, taxonomy_lock) | `governance` block in `lesson_spec` v1.2 + gate checks + manifest section |
| Bridge | new | `skills/…/scripts/spec_adapter.py` |

## Exit criterion — evidence

Executable form: `pytest -q tests/` (8 tests, pass).

| Criterion | Result |
|---|---|
| Gate demo runs gate → render | `DEMO_lesson_deck.pptx`, 10 slides, status `draft-only`, 0 blockers |
| Migrated Ch.1 runs gate → render | `20260906_NCC_Family-Centered_Nursing_Care_Part_1_DRAFT.pptx`, 18 slides, status `blocked` (empty organizing question, as in the 09-05 run) |
| Original renderer demo runs through gate → render | via `--legacy`: 26 slides, all 26 renderer archetypes present in the manifest, status `draft-only` |
| PPTX validates | every deck re-opens with python-pptx, zip integrity passes, slide count = manifest active count; `validate_unified_package.py` passes on all three |
| No archetype lost | `ARCHETYPES = v1.1 set ∪ renderer.RENDERERS` (27 names incl. `content`≡`generic`); test asserts both inclusions |
| Evidence gate still stamps `_DRAFT` | test flips one demo slide to `source-grounded` with empty `source_refs` → blocker → `_DRAFT` |

Not verified here: visual rendering. LibreOffice in this container refuses to load any file ("source file could not be loaded"), so no PDF/PNG thumbnails were produced. Structural round-trip only. **Open the three decks in PowerPoint before accepting.** Regenerate with:

```bash
python skills/harrity-lesson-builder-pipeline/scripts/validate_and_gate.py --demo --outdir out/demo
python skills/harrity-lesson-builder-pipeline/scripts/validate_and_gate.py --spec fixtures/ch1_migrated_lesson_spec.json --outdir out/ch1
python skills/harrity-lesson-builder-pipeline/scripts/validate_and_gate.py --legacy fixtures/renderer_legacy_demo_spec.json --label-demo --outdir out/legacy
```

## Changes to the canonical renderer (two, both additive)

1. `make_presentation()` writes `speaker_notes` to the PPTX notes slide. The original renderer read `speaker_notes` only for the facilitator guide; the deck carried no narration. This was the single hard requirement for five-channel separation to survive the merge.
2. `add_footer()` prints `slide_id · evidence_status` at bottom-right when either is present. The v1.1 gate's own drawing code put an evidence chip on every slide; this is the minimal equivalent so provenance is visible to a faculty reviewer without the manifest.

Everything else in the renderer is byte-identical to the ChatGPT build. Its own `--demo` still runs (test `test_renderer_own_demo_still_runs`).

## Fields that change meaning in the merge

| Field | v1.1 gate meaning | Renderer meaning | Merge decision |
|---|---|---|---|
| `slide_archetype` `content` | plain bullets + activity band | `generic`: one card with `lead` title + bullets + callout | adapter maps `content`→`generic`; `lead` ← `learning_objective`, callout ← `activity_prompt` |
| `chapter_map.card_data[].nodes` | vertical node chain per lane (foundation ▼ bedside) | horizontal milestone line, one label + one body per milestone | nodes flattened to `"A → B → C"` in the milestone body. **Visual loss vs the 09-05 build**; the lane→nodes structure is preserved in the manifest. Candidate for a renderer `lane_map` archetype later. |
| `concept_cards.card_data[].cjm` | drawn as a chip on each card | not a renderer field | not drawn; kept in manifest/traceability |
| `urgency_sort.card_data[0].items` + `correct_order` | one list, order in notes | `categories` = pre-sorted buckets | items rendered as one list titled by `activity_prompt`; `correct_order` → notes. Pass-through `categories` available. |
| `*_mcq.options` `"A. text"` | rendered verbatim | renderer letters options itself | leading `A.`/`A)` stripped by adapter to avoid `A A.` |
| `opening_case` | presentation / cues / prompt | patient_prompt / know / need / task | `presentation`→`patient_prompt`, `cues`→`know`, **`on_slide_text`→`need`** ("what you do not know yet"), `prompt`→`task` |
| `mini_case` | presentation / cues / prompt | scenario + step cards | `presentation`→`scenario`; steps synthesised as `cues`, `your task`, `consider` (from `on_slide_text`) |
| `timeline.card_data[].event` | `event` | `body` | renamed in adapter |
| `takeaway` | dark slide, bullets | action cards + closing statement | bullets → action card titles; `learning_objective` → statement |
| `title` | organizing question + lanes on slide | clinical question card + goals + hard-coded "nurse lens" panel | `on_slide_text` → goals; demo prefix `DEMO — ` on title and subtitle; renderer's fixed strings ("TEACH / ASSESS / ESCALATE", "today is not a vocabulary tour") remain — **open item** |
| `speaker_script` | notes slide | (not written) | renderer patched; notes = script + CORRECT/RATIONALE + CORRECT ORDER + PAIRS + ANSWER KEY + VISUAL NOTES |
| `evidence_status` | footer chip, colour-coded | `source_status` (metadata-level, one value per package) | per-slide value flows to footer text and manifest; colour coding dropped |
| `concept_lanes` (lesson) | plain strings | `[{label, description}]` | descriptions taken from the `chapter_map` slide's nodes when present, else empty |
| `remediation_map[]` | §7 records | `quiz_analysis[]` (`score_percent` etc.) | mapped both ways; `score_percent` has no v1.1 home → `"n/a"` |
| `qa.release_status` | 4 states | `package_status` (free text) | v1.2 adds governance consistency (below) |
| slide IDs | `S##[A-Z]?` | `S##` | unchanged; **master-lesson `S###` not adopted** |

## Governance envelope (master-lesson 1.0.0) — what was adopted

Adopted as schema slots plus one consistency rule: `release-ready` requires all seven approvals `true` and `taxonomy_lock.status: locked`; otherwise the manifest is downgraded to `faculty-review-needed` and a major is logged. `promotion_state` values are validated. Manifest gains a `governance` section (`envelope: master-lesson-1.0.0`). The generator can only lower a status, never raise it, so human approval stays terminal.

Not adopted, recorded as conflicts for a later reconciliation pass:

- ID patterns (`S###`, `LO-##`, `REF-###`) differ from v1.x (`S##`, `CO#`, `SRC##`). Converting IDs would break the Stage 13 lock on the migrated Ch.1.
- `required_slide_types` is a different archetype vocabulary (lesson_title, pathophysiology, medications …). It describes a lecture outline, not a map-first lesson.
- Per-slide `accessibility` block (reading order, alt text, contrast). Real requirement; v2 candidate once images enter the pipeline.
- `media_binding.tts_model: gpt-4o-mini-tts` — vendor-specific; the runtime_config already owns media settings.

## Assumptions logged

1. `bobbyh93/repo` was empty at session start; it is now the build repo. `Codex_Repo_2026` (public, read-only here) was inventoried but not modified. The handoff assumed the build would happen inside `Codex_Repo_2026`; nothing here depends on that.
2. The ChatGPT `skill.zip` is canonical for the renderer; `agents/openai.yaml` was dropped and `/home/oai/...` paths replaced with repository-relative paths.
3. Schema v1.0 and v1.1 specs are accepted by the v1.2 gate unchanged (the migrated Ch.1 is v1.0).
4. Adapter fallbacks are minor defects, not major: they change layout, not content. Unknown archetypes remain major.
5. The v1.1 speaker-script minimum is waived for `clinical_question` in addition to `title`/`takeaway`/`chapter_map`, because the renderer's clinical-question slide is a map, not a taught slide.
6. `validate_unified_package.py` now accepts any single `*.pptx` (the v1.1 filename pattern and `_DRAFT` stamp made the fixed `lesson_deck.pptx` name obsolete) and checks the `_DRAFT` ↔ `blocked` pairing.
7. `skill_v2` (2026-05-09) was not merged; it stays under `handoff/skills_in_hand/` as a migration source only. Its `student_reception_review` and `package_manifest.schema.json` are not represented in v1.2.

## Open items carried to WP-2 / later

- Renderer title slide carries fixed strings; make them adapter-supplied (`goals` already is).
- `chapter_map` vertical lane layout: add a renderer archetype or accept the milestone line.
- Visual QA of the three decks in PowerPoint (blocked here by LibreOffice).
- `taxonomy.frameworks[]` registration of `CA-BRN-ART3` / `CCNE` happens in WP-2's spec, not in the schema (schema already has the slot).
