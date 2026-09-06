# Lesson Package Schema — `lesson_spec.json`

Version: 1.2 (2026-09-06) — WP-1 merge: archetype set = union with the canonical renderer, `card_data` pass-through (§5.3), governance envelope from master-lesson 1.0.0 (§13), assessment-item `source_refs`/`options`.
Previous: 1.1 (2026-09-05) added §11 traceability and §12 improvement loop.
Consumed by: `scripts/validate_and_gate.py` (Stage 9), which renders through `scripts/spec_adapter.py` → `scripts/generate_lesson_package.py`.
Derived from: `slide_contract_template.json`, `runtime_config.template.json`, SKILL.md production slide contract, `qa-checklist.md`.

`lesson_spec.json` is the single input to the PPTX generator. It is produced after Stage 7 (Full QA) passes. It carries the frozen `runtime_config` plus the ordered slide list, each slide conforming to the production slide contract. The generator does not invent content; every value on a slide comes from this file.

---

## 1. Top-level shape

```json
{
  "schema_version": "1.2",
  "runtime_config": { ... },
  "lesson": { ... },
  "sources": [ ... ],
  "taxonomy": { ... },
  "slides": [ ... ],
  "assessment_items": [ ... ],
  "remediation_map": [ ... ],
  "qa": { ... },
  "revision_log": [ ... ],
  "outcomes": { ... },
  "improvement_log": [ ... ],
  "governance": { ... }
}
```

| Key | Required | Type | Notes |
|---|---|---|---|
| `schema_version` | yes | string | `"1.2"` (`"1.0"`/`"1.1"` accepted; anything else is a major defect) |
| `runtime_config` | yes | object | Frozen Stage 0 object. Must validate with `validate_runtime_config.py`. |
| `lesson` | yes | object | Lesson identity (§2). Usually a copy of `runtime_config.lesson`, may add resolved values. |
| `sources` | yes | array | Source records (§3). Every `source_refs[]` entry on a slide must resolve to a `source_id` here. |
| `taxonomy` | yes | object | Locked Stage 2 taxonomy (§4). |
| `slides` | yes | array | Ordered production slides (§5). Minimum 1. |
| `assessment_items` | no | array | Quiz/checkpoint items (§6). Feeds `assessment_map.csv`. |
| `remediation_map` | no | array | Stage 10 output (§7). |
| `qa` | yes | object | Release status and defect log summary (§8). |
| `revision_log` | no | array | Stage 13 entries (§9). Empty on first build. |
| `outcomes` | no | object | Aggregated assessment/learner outcome data for this lesson (§12). Empty on first build. |
| `improvement_log` | no | array | Analysis → action → evidence records (§12). Empty on first build. |
| `governance` | no | object | master-lesson 1.0.0 envelope (§13): promotion state, approvals, taxonomy lock, administrative metadata. Absent = `intake_complete`, nothing approved. |

---

## 2. `lesson`

```json
{
  "course_code": "string",
  "program_level": "string",
  "audience": "string",
  "unit_title": "string",
  "chapter_id": "string",
  "chapter_title": "string",
  "lesson_title": "string",
  "concept": "string",
  "exemplars": ["string"],
  "clinical_domain": "string",
  "source_family": "string",
  "source_anchor": "string",
  "page_range": "string",
  "organizing_clinical_question": "string",
  "opening_patient_question": "string",
  "concept_lanes": ["string"],
  "target_duration_minutes": 0,
  "program_outcomes": [{"id": "PO3", "text": "string", "standards_refs": []}],
  "course_objectives": [{"id": "CO2", "text": "string", "maps_to": ["PO3"]}]
}
```

`program_outcomes` and `course_objectives` are the top of the traceability chain (§11). Optional in MVP; when present, every slide `learning_objective` should name a `course_objective_id`.

Required for generation: `course_code`, `unit_title`, `chapter_title`, `lesson_title`, `organizing_clinical_question`, `concept_lanes` (4–6 entries). Everything else may be empty strings but the key must exist.

`concept_lanes` is authoritative. Every slide's `concept_lane` must be one of these values or `"cross-lane"`.

---

## 3. `sources[]`

One record per source used. This is the Stage 1 source package, carried forward so citations are resolvable inside the package.

```json
{
  "source_id": "SRC01",
  "title": "string",
  "kind": "authoritative | supporting | external | learner-data",
  "license": "CC BY 4.0 | public domain | instructor-owned | restricted",
  "locator": "chapter/section/page/url as given",
  "coverage_status": "confirmed | partial | absent | mixed"
}
```

`source_id` pattern: `^SRC\d{2,3}$`. Restricted-license sources may be cited but their text must not appear in `on_slide_text` or `speaker_script`; the generator does not check this — Stage 7 QA does.

---

## 4. `taxonomy`

```json
{
  "glossary": [{"term": "string", "definition": "string", "source_ref": "SRC01"}],
  "concept_tags": ["string"],
  "outcome_tags": ["string"],
  "nclex_client_needs": ["string"],
  "cjm_functions": [
    "recognize cues", "analyze cues", "prioritize hypotheses",
    "generate solutions", "take action", "evaluate outcomes"
  ],
  "proposed_new_tags": ["string"],
  "frameworks": [{"framework_id": "AACN-2021", "title": "string", "text_policy": "identifier-only | public-domain | licensed"}]
}
```

`frameworks` registers which external standards are active for this program (see §11). `text_policy` governs whether descriptor text may be stored: AACN Essentials, QSEN, ANA are `identifier-only`; California regulation text (16 CCR §1426, §2530; Title 22) is `public-domain`.

`cjm_functions` is fixed to the six NCSBN CJMM values in this order. Slides reference them by exact string.

---

## 5. `slides[]` — production slide contract

Every slide carries every key below. Empty arrays and empty strings are permitted where noted; missing keys are a schema failure.

| Key | Type | Required non-empty | Rule |
|---|---|---|---|
| `slide_id` | string | yes | `^S\d{2}[A-Z]?$`. Unique. Never recycled. Split children are `S03A`, `S03B`; parent retained with `"retired": true`. |
| `slide_number` | integer | yes | 1-based render order. Retired slides have `slide_number: 0`. |
| `slide_title` | string | yes | ≤ 70 characters. |
| `slide_archetype` | string | yes | One of the archetype set (§5.1). |
| `lesson_section` | string | yes | Free text, e.g. `"opening"`, `"map"`, `"lane: protect"`, `"evaluation"`. |
| `concept_lane` | string | yes | One of `lesson.concept_lanes` or `"cross-lane"`. |
| `source_refs` | string[] | conditional | Required non-empty when `evidence_status` is `source-grounded` or `source-aligned`. Each must match a `sources[].source_id`. |
| `evidence_status` | string | yes | One of: `source-grounded`, `source-aligned`, `inferred`, `illustrative-example`, `instructor-added`, `provisional`, `unresolved`, `needs-verification`. |
| `cjm_functions` | string[] | no | Subset of taxonomy `cjm_functions`. Empty allowed on `title` / `takeaway` only. |
| `nursing_action_category` | string | no | e.g. `"assess"`, `"monitor"`, `"intervene"`, `"educate"`, `"escalate"`, `"evaluate"`. |
| `learning_objective` | string | yes | One objective. One sentence. |
| `on_slide_text` | string[] | yes | Learner-facing bullets. Density budget in §5.2. |
| `activity_prompt` | string | no | Empty string when the archetype has no learner task. |
| `answer_key` | string[] | conditional | Required non-empty when `activity_prompt` is non-empty. |
| `visual_notes` | string | no | Instruction to the renderer/designer. Not rendered on slide. |
| `speaker_script` | string | yes | Verbatim faculty script. Goes to speaker notes. Never an outline. |
| `tts_text` | string | no | TTS-safe narration. May be empty when audio not requested. Never merged with `on_slide_text`. |
| `target_duration_sec` | integer | yes | Estimated at `media.wpm_target`. |
| `audio_duration_sec` | number \| null | no | Filled by Stage 11. |
| `auto_advance` | boolean | yes | |
| `layout_spec` | object | yes | §5.2. |
| `allow_overlap` | boolean | yes | Default `false`. |
| `qa_status` | string | yes | `pass`, `pass-with-minor`, `major`, `blocker`, `unreviewed`. |
| `qa_notes` | string | no | |
| `remediation_target` | object | yes | `{concept_lane, cjm_function, misconception, fix_type}`. May be all empty strings on non-assessment slides. |
| `audio_filename` | string | no | Filled by Stage 11. Pattern `{slide_id}.mp3`. |
| `retired` | boolean | no | Default `false`. Retired slides are excluded from render but retained in manifest. |
| `course_objective_id` | string | no | Links this slide to `lesson.course_objectives[].id`. Empty in MVP. |
| `standards_refs` | object[] | no | `{"framework_id": "AACN-2021", "ref": "2.1"}` — identifiers only, never descriptor text unless the framework's `text_policy` permits. Empty in MVP. |

### 5.1 Archetype set

The gate accepts the union of the v1.1 set and every archetype the canonical renderer implements. Unknown archetypes fall back to `content` and are logged as a **major** defect.

v1.1 set (visual data via §5.3 `card_data` element shapes):

`title`, `opening_case`, `clinical_question`, `chapter_map`, `warmup_sequence`, `concept_cards`, `match_activity`, `debrief`, `timeline`, `checkpoint_mcq`, `mini_case`, `urgency_sort`, `capstone_mcq`, `retrieval_check`, `takeaway`, `content`

Renderer-native additions (visual data via §5.3 pass-through):

`control_room`, `process_map`, `teaching_point`, `exchange_model`, `triad`, `safety_chain`, `compare`, `risk_engine`, `script_template`, `basics_grid`, `debrief_three`

`content` renders as the renderer's `generic` layout. The speaker-script minimum (20 words) is waived for `title`, `takeaway`, `chapter_map`, `clinical_question`.

### 5.2 `layout_spec`

```json
{
  "archetype": "concept_cards",
  "density_budget": {"max_bullets": 6, "max_words_per_bullet": 14},
  "regions": ["header", "body", "footer"],
  "card_data": []
}
```

- `density_budget` defaults: `max_bullets` 6, `max_words_per_bullet` 14. Exceeding the budget is a **major** defect; the generator renders anyway and logs it.
- `card_data` is archetype-specific structured content (§5.3). When present the generator prefers it over `on_slide_text` for the body region.

### 5.3 Archetype-specific `card_data`

**v1.1 element shapes** (mapped by the adapter):

| Archetype | `card_data` element shape |
|---|---|
| `chapter_map` | `{"lane": "string", "nodes": ["string"]}` — one per concept lane, ordered foundation → bedside. Rendered as a horizontal milestone line; nodes are joined with " → " into the milestone body. |
| `concept_cards` | `{"heading": "string", "body": "string", "cjm": "string"}` — 2 to 6 cards. `cjm` is not drawn by the renderer; it stays in the manifest. |
| `checkpoint_mcq`, `capstone_mcq` | `{"stem": "string", "options": ["A. …"], "correct": "A", "rationale": "string"}` — exactly one element. The renderer letters options itself; a leading `A.`/`A)` is stripped. `correct` + `rationale` go to speaker notes. |
| `mini_case`, `opening_case` | `{"presentation": "string", "cues": ["string"], "prompt": "string"}` — exactly one element. For `opening_case`, `on_slide_text` becomes the "what you do not know yet" column. |
| `urgency_sort` | `{"items": ["string"], "correct_order": [0,2,1]}` — exactly one element. Rendered as one unsorted list; the correct order goes to speaker notes. To render pre-sorted buckets use pass-through `categories`. |
| `match_activity` | `{"left": ["string"], "right": ["string"], "pairs": [[0,1]]}` — exactly one element. Pairs go to speaker notes. |
| `timeline` | `{"label": "string", "event": "string"}` — 3 to 8 elements |

**Pass-through** (any archetype): `card_data[0]` may carry the renderer's own content keys for that archetype verbatim, as documented in `renderer-spec.md` (for example `control_room`: `center`, `nodes`; `exchange_model`: `left`, `center`, `right`, `warning`; `compare`: `columns`). Pass-through keys override adapter-derived values and are logged as a minor "adapter: pass-through keys" note so reviewers can see where a slide bypassed the v1.1 shapes.

**Fallbacks** (logged as minor `adapter:` notes, never silent): when an archetype has no `card_data`, the adapter derives what it can from `on_slide_text`, `activity_prompt`, `learning_objective` and `lesson.concept_lanes`. Where nothing can be derived the renderer's neutral default text applies.

## 6. `assessment_items[]`

```json
{
  "item_id": "Q01",
  "slide_id": "S07",
  "item_type": "mcq | sata | ordering | matching | short-answer | retrieval",
  "learning_objective": "string",
  "concept_lane": "string",
  "cjm_function": "string",
  "stem": "string",
  "answer": "string",
  "rationale": "string",
  "remediation_target_slide": "S04",
  "evidence_status": "string",
  "source_refs": ["SRC01"],
  "options": ["A. …", "B. …"]
}
```

`source_refs` follows the slide rule: required non-empty when `evidence_status` is `source-grounded`/`source-aligned` (**major** in v1.2). `options` is optional and used by `facilitator_guide.md` and the LMS export.

Feeds `assessment_map.csv` columns: `objective, concept_lane, slide, activity, cjm_function, item_type, remediation_target`.

---

## 7. `remediation_map[]` (Stage 10)

```json
{
  "miss_pattern": "string",
  "failed_operation": "one of six cjm_functions",
  "map_location": "S04",
  "concept_lane": "string",
  "likely_misconception": "string",
  "one_slide_fix": "string",
  "active_learning_task": "string",
  "retrieval_item": "string",
  "improvement_evidence": "string"
}
```

---

## 8. `qa`

```json
{
  "release_status": "release-ready | faculty-review-needed | draft-only | blocked",
  "gates_passed": ["runtime", "source", "taxonomy", "blueprint", "cjm_coverage", "outline", "script", "timing", "layout"],
  "defects": [{"severity": "blocker | major | minor", "slide_id": "S03", "note": "string"}],
  "cjm_coverage_rationale": "string"
}
```

The generator appends its own defects (`deck_render` gate) and writes the merged log to `qa_log.md`. If any `blocker` exists the generator still renders but stamps every output filename with `_DRAFT` and sets manifest status `blocked`.

---

## 9. `revision_log[]`

```json
{
  "revision_id": "R01",
  "date": "YYYY-MM-DD",
  "changed_ids": ["S03"],
  "previous_summary": "string",
  "new_summary": "string",
  "reason": "string",
  "downstream_effects": ["script S03", "audio S03"]
}
```

---

## 10. Generator contract

```
python scripts/validate_and_gate.py --spec lesson_spec.json --outdir OUTDIR
python scripts/validate_and_gate.py --demo --outdir OUTDIR
python scripts/validate_and_gate.py --legacy renderer_spec.json --outdir OUTDIR   # migration
```

Exit codes: `0` rendered without blockers, `1` rendered with blockers (`_DRAFT` stamped, status `blocked`), `2` spec unreadable (no output).

Outputs to `OUTDIR` (names fixed; `filename_pattern` from runtime_config is applied to the PPTX only):

| File | Built from |
|---|---|
| `lesson_deck.pptx` (or patterned name) | `slides[]` non-retired, ordered by `slide_number`; `speaker_script` → notes |
| `facilitator_guide.md` | lesson, per-slide objective + script + activity + answer key, remediation map |
| `learner_handout.md` | lesson map, per-slide `on_slide_text`, activities without answers, exit check |
| `assessment_map.csv` | `assessment_items[]`, falling back to slides with non-empty `activity_prompt` |
| `lesson_manifest.json` | metadata, runtime_config, source table, slide list with status fields, CJM coverage matrix, QA status, revision log |
| `qa_log.md` | `qa.defects` + generator-detected defects |
| `web/index.html`, `web/learner_handout.html` | learner-facing HTML (no scripts, no answer keys) — v1.2 |
| `<deck stem>.imscc` | IMS Common Cartridge 1.1 with the HTML pages and a QTI 1.2 assessment from `assessment_items[]`; carries the `_DRAFT` stamp; structurally validated (`exports.structural_validation`) — v1.2 |
| `<deck stem>.pdf` | deck PDF when LibreOffice is available; otherwise a minor defect — v1.2 |

Generator-detected defects (all logged, never silently fixed):

| Check | Severity |
|---|---|
| Duplicate `slide_id` | blocker |
| Missing required slide key | blocker |
| `source-grounded`/`source-aligned` with empty `source_refs` | blocker |
| `source_refs` entry not in `sources[]` | blocker |
| `evidence_status` not in allowed set | blocker |
| CJM function never covered across deck, no rationale | blocker |
| Unknown archetype | major |
| Density budget exceeded | major |
| `concept_lane` not in `lesson.concept_lanes` | major |
| `activity_prompt` without `answer_key` | major |
| `speaker_script` under 20 words on a content slide | major |
| `slide_title` over 70 chars | minor |
| `schema_version` outside {1.0, 1.1, 1.2} | major |
| `assessment_items[].source_refs` empty while source-grounded/aligned | major |
| adapter fallback or pass-through used on a slide | minor |

Demo mode labels every slide `illustrative-example`, sets `release_status: draft-only`, and prefixes the deck title with `DEMO —`. Demo content does not imply course-source support.

---

## 11. Traceability (accreditation layer) — v1.1

Accreditors and boards audit the chain, not the slides:

`program outcome → course objective → lesson objective (slide) → assessment item → outcome data → improvement action`

The schema carries every link as an identifier. The generator does not author any of them; it validates that referenced IDs resolve and emits the rolled-up matrix.

**Package-level standards refs (v1.2).** `lesson.standards_refs[]` uses the same `{framework_id, ref}` shape plus an optional `basis` string and states what the whole package is offered as evidence for (for `CA-BRN-ART3`, `ref` is the base's `req_id`, validated against `references/frameworks/ca_brn_article3_requirements.json`). `scripts/compliance_sync.py` turns these into Evidence Registry records once the package is `release-ready`. Slide-level `standards_refs` remain the fine-grained mapping.

**Generator outputs added in v1.1**

| File | Content |
|---|---|
| `traceability_matrix.csv` | one row per slide: `slide_id, learning_objective, course_objective_id, program_outcome_ids, standards_refs, cjm_functions, assessment_item_ids, evidence_status` |
| `lesson_manifest.json › traceability` | same matrix as JSON plus `frameworks` registry and `unmapped_counts` (slides with no course objective, no standards ref, no assessment item) |

**Generator checks added (all `minor` in MVP so they never block; promote to `major` once a program activates the layer)**

| Check | Severity |
|---|---|
| `course_objective_id` not in `lesson.course_objectives[]` | minor |
| `standards_refs[].framework_id` not in `taxonomy.frameworks[]` | minor |
| `course_objectives[].maps_to` names an unknown program outcome | minor |
| Framework `text_policy: identifier-only` but a `ref` exceeds 24 characters (likely pasted text) | major |

---

## 12. Improvement loop — v1.1

Lesson generation is stage one. The product is the loop that follows it. This section holds the data that closes it; it is empty on a first build and grows per delivery.

### 12.1 `outcomes`

```json
{
  "cohort_id": "string (no learner identifiers)",
  "delivery_date": "YYYY-MM-DD",
  "n_learners": 0,
  "item_results": [{"item_id": "Q01", "n": 0, "p_correct": 0.0, "distractor_counts": {"A": 0}}],
  "cjm_function_performance": {"recognize cues": 0.0},
  "concept_lane_performance": {"baseline": 0.0},
  "learner_questions": [{"slide_id": "S05", "question": "string", "count": 0}],
  "source": "lms-export | instructor-entered | ehr-sim | other"
}
```

Aggregate only. No learner-level records, no names, no IDs that resolve to a person. FERPA applies to anything finer than this.

### 12.2 `improvement_log[]`

```json
{
  "action_id": "IA01",
  "date": "YYYY-MM-DD",
  "trigger": "outcome-data | learner-question | faculty-review | accreditation-finding | source-update",
  "finding": "string — what the data showed",
  "failed_operation": "one of six cjm_functions, or null",
  "affected_ids": ["S05", "Q01", "CO2"],
  "action_taken": "string",
  "revision_id": "R02",
  "expected_effect": "string",
  "evidence_of_effect": "string or null — filled on the next delivery",
  "standards_refs": []
}
```

Each record links backward to a Stage 10 remediation finding and forward to a Stage 13 revision. That link is what turns a revision log into a systematic evaluation record.

### 12.3 Cycle

```
deliver → collect outcomes (12.1) → Stage 10 classify by failed operation
        → improvement_log entry (12.2) → Stage 13 revision (stable IDs)
        → re-deliver → evidence_of_effect
```

**Generator behaviour in v1.1:** carries `outcomes` and `improvement_log` through to the manifest unchanged, and appends a `## Improvement history` section to `facilitator_guide.md` when the log is non-empty. Analysis and dashboards are out of scope for the generator; they read the manifest.

---

## 13. Governance envelope — v1.2

Adopted from `references/master_lesson/master_lesson_schema.json` (master-lesson 1.0.0, WP-HLB-20260723). The envelope is a slot: MVP packages may omit it entirely.

```json
{
  "promotion_state": "template | intake_complete | faculty_review | production_ready | release_ready | released",
  "approvals": {
    "source_approved": false, "taxonomy_approved": false, "objectives_approved": false,
    "outline_approved": false, "script_approved": false,
    "faculty_approved": false, "release_approved": false
  },
  "taxonomy_lock": {"status": "unlocked | locked", "approved_by": "string", "approval_date": "YYYY-MM-DD"},
  "administrative_metadata": {"lesson_id": "LESSON-…", "version": "0.1.0", "content_owner": "string", "faculty_reviewer": "string"}
}
```

Rules enforced by the gate:

| Check | Severity / effect |
|---|---|
| `qa.release_status: release-ready` without all seven approvals `true` | major; manifest status downgraded to `faculty-review-needed` |
| `release-ready` with `taxonomy_lock.status != locked` | major; same downgrade |
| `promotion_state` in {`release_ready`, `released`} while `qa.release_status` ≠ `release-ready` | major |
| unknown `promotion_state` | major |
| unknown approval key / non-boolean approval | minor |

Human approval remains the terminal gate: the generator can only lower a status, never raise it.

**Not adopted (recorded as conflicts, see `docs/WP1_MERGE_LOG.md`):** master-lesson `S###` slide IDs and `LO-##` objective IDs (v1.x keeps `S##[A-Z]?` and `CO#`), `required_slide_types` (a different archetype vocabulary), per-slide `accessibility` block (v2 candidate).
