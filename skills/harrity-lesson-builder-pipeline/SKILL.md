---
name: harrity-lesson-builder-pipeline
description: canonical harrity lesson builder pipeline for source-grounded nursing and healthcare lesson packages. use when asked to build, revise, or consolidate harrity-style slide deck packages; generate pptx lessons, high-level concept maps, clinical judgment model crosswalks, quiz-miss remediation, facilitator guides, learner handouts, speaker notes, tts/audio/video handoffs, qa logs, manifests, or controlled revisions. also use for requests naming lesson-builder-pipeline or lesson-video-builder; route those alias workflows into this single skill rather than creating separate skills.
---

# Harrity Lesson Builder Pipeline

## Canonical consolidation rule

This is the single canonical lesson-production skill. Do not create a separate skill for `lesson-builder-pipeline`, `lesson-video-builder`, slide generation, narration, audio handoff, remediation, or clinical judgment crosswalk work. Treat those names as historical aliases and route their workflows through this skill.

When the user asks to update or improve the lesson builder, preserve this skill name and package path: `harrity-lesson-builder-pipeline`. The skill lives in the repository at `skills/harrity-lesson-builder-pipeline/`; update it in place and keep `tests/` green rather than returning a zip.

## Prime directive

Build reusable, source-grounded Harrity lesson packages from runtime inputs. The package must help learners see the whole map first, then drill down into missed concepts, clinical cues, safety risks, nursing actions, and evaluation.

Do not fabricate source support. Do not hardcode a topic, chapter, patient, case, source family, deck name, or output path unless supplied by the user or resolved in the runtime config.

Every lesson follows this clinical spine:

`clinical question -> concept map -> structure/function logic -> patient cues -> risk -> nursing action -> evaluation`

Every major concept must answer:

1. what should the nurse notice?
2. what does it mean?
3. what matters first?
4. what should the nurse do?
5. how will the nurse know it worked?

## Runtime variable rule

Before producing instructional artifacts, resolve a `runtime_config` object. Lesson-specific values must come from:

1. `user_request`: the current instruction.
2. `source_inputs`: uploaded files, pasted text, retrieved chunks, tables, approved outlines, quiz data, question logs, or prior packages.
3. `runtime_defaults`: safe defaults in this skill's templates.
4. `derived_values`: package IDs, slide IDs, filenames, timing estimates, output folders, rebuild scope, and dependency impacts computed from runtime inputs.

If required content is missing, use the narrowest safe fallback:

- For package IDs and filenames, derive from run date, course code, unit title, chapter title, and lesson title.
- For uncertain source support, mark `provisional`, `inferred`, or `needs-verification` instead of inventing certainty.
- For clinical or policy-sensitive content, mark `needs-verification`; verify with user sources or authoritative current sources when needed.
- For unknown content scope, stop at source preflight or blueprint; do not generate a full lesson.
- For demo/testing, label all content as demo or illustrative and do not imply course-source support.

## Working modes

Use the narrowest mode that satisfies the request.

| Mode | Use when | Output |
|---|---|---|
| `source_preflight` | sources, scope, or variables are unclear | intake report, source inventory, assumptions, gaps |
| `blueprint` | user wants the high-level chapter map or lesson plan | clinical question, concept lanes, CJM map, slide outline |
| `full_production` | user asks for finished lesson package or files | PPTX, guides, maps, manifests, QA logs as files |
| `revision` | user asks to improve an existing package | targeted rebuild with stable IDs and revision log |
| `audio_video_handoff` | user asks for narration, TTS, or video plan | script package, TTS queue, binding manifest, export plan |

## Required package outputs

For full production, create actual files and provide links. Do not claim any artifact exists unless it was created.

Default lesson package:

- `lesson_deck.pptx`: PPTX deck with visual map-first slides.
- `facilitator_guide.md`: educator guide, teaching moves, debrief prompts, and answer key.
- `learner_handout.md`: learner-facing map, notes, activities, and exit check.
- `assessment_map.csv`: objective, concept lane, slide, activity, CJM function, item type, and remediation target.
- `lesson_manifest.json`: metadata, runtime config, source status, assumptions, slide list, CJM coverage, QA status, and revision log.

Optional package files:

- `outline.json`: locked slide outline.
- `script.json`: one verbatim script block per slide ID.
- `audio_handoff.json`: narration, pronunciation, pauses, emphasis, and TTS fields.
- `binding_manifest.json`: slide-to-audio timing, captions, and auto-advance metadata.
- `video_export_plan.md`: production checklist for video export.
- `qa_log.md`: blocker, major, and minor defect log.

## Unified workflow

Run stages in this order unless the user explicitly asks for a single stage.

### Stage 0: Resolve runtime

Create and freeze `runtime_config`. Set build mode, output targets, source inventory, lesson identity, taxonomy defaults, layout controls, media controls, QA gates, and rebuild scope.

Use `references/dynamic-variable-contract.yaml`, `templates/runtime_config.template.json`, and `scripts/validate_runtime_config.py` when producing or validating saved runtime config.

### Stage 1: Normalize sources

Create a source package with:

- provided files and text blocks
- source hierarchy
- course-source anchors
- quiz data or learner questions
- assumptions
- conflicts
- gaps
- source coverage status: `confirmed`, `partial`, `absent`, or `mixed`

Classify material as: `teach on slide`, `mention verbally`, `appendix`, or `exclude`.

### Stage 2: Lock glossary and taxonomy

Lock terminology before outlining:

- approved glossary
- concept tags
- outcome tags
- NCLEX client needs when relevant
- NGN/CJMM functions
- priority frameworks
- active-learning templates
- synonym policy
- forbidden substitutions

Do not allow taxonomy drift in later stages. New tags go only in `proposed_new_tags` until approved.

### Stage 3: Build the high-level Harrity blueprint

Use `references/map-first-lesson-blueprint.md`.

Produce:

- opening patient question
- one organizing clinical question
- 4 to 6 concept lanes
- chapter map route from foundation to bedside action
- map-to-drill-down plan
- first retrieval check
- likely learner difficulty points

Default concept-lane logic:

- physiology/process topics: create, support, protect, signal
- safety/triage topics: recognize, interpret, prioritize, act, evaluate
- patient education topics: teach, assess, escalate, reassure
- disease-process topics: baseline, disruption, cues, risk, response, follow-up

Adapt lane names to the topic. Do not force early-pregnancy lanes onto unrelated lessons.

### Stage 4: Map directly to clinical judgment

Use `references/cjm-concept-model.md`.

Every package must cover the six CJMM functions:

1. recognize cues
2. analyze cues
3. prioritize hypotheses
4. generate solutions
5. take action
6. evaluate outcomes

Embed CJM into the lesson map. Do not add it as a final decorative slide. The concept lanes organize what is being studied; CJM organizes what the learner must do clinically.

### Stage 5: Build the slide outline

Create one outline object per slide. Preserve stable `slide_id` values. Use `S01`, `S02`, and so on for first draft; never recycle an existing ID.

Each outline object must include:

- `slide_id`
- `slide_number`
- `slide_title`
- `lesson_section`
- `concept_lane`
- `learning_objective`
- `main_point`
- `sub_points`
- `definitions`
- `evidence_examples`
- `concept_tags`
- `outcome_tags`
- `cjm_functions`
- `nursing_action_category`
- `prerequisite_slide_ids`
- `estimated_duration_seconds`
- `evidence_status`
- `remediation_target`

Keep one core teaching objective per slide. Split overloaded slides instead of widening the slide.

### Stage 6: Run outline QA

Use `references/lesson-quality-gates.md` and `references/qa-checklist.md`.

Check for:

- coverage gaps
- duplicate or overlapping teaching objectives
- audience mismatch
- glossary drift
- tag inconsistency
- pacing violations
- unsupported claims
- missing CJM coverage
- missing map-to-bedside link
- overloaded slides

Fix blockers before scripting unless the user explicitly asks for a raw draft.

### Stage 7: Build slide content package

Create concise learner-facing slide text, visual layout instructions, activity prompts, answer keys, and source references.

Use the Harrity slide architecture:

- opening case/question
- organizing clinical question
- concept map
- chapter route map
- warm-up retrieval
- structure-function reasoning
- matching/sorting/sequencing activity
- debrief
- timeline or process model
- checkpoint question
- patient teaching script
- capstone clinical judgment scenario
- exit retrieval check
- takeaway and remediation map

Choose only the needed archetypes. Do not create decorative slides that do not support the clinical spine.

### Stage 8: Build script and timing package

Create exactly one script block per `slide_id`.

Each script block must include:

- `slide_id`
- `slide_title`
- `target_duration_seconds`
- `speaker_script`
- `tts_text`
- `delivery_notes`
- `pronunciation_notes`
- `net_new_items`
- `evidence_status`

Scripts must teach the slide objective, reuse approved terminology, and avoid unsupported new claims. Estimate timing at the configured words-per-minute target.

### Stage 9: Build PPTX deck package

Use the PPTX pipeline only after the outline and slide content pass QA.

The pipeline has three parts, all in `scripts/`:

| Part | File | Role |
|---|---|---|
| Gate + package writer | `validate_and_gate.py` | Validates `lesson_spec.json` against the production slide contract (`references/package-schema.md`), then writes guides, assessment map, traceability matrix, manifest and QA log. Stamps every output `_DRAFT` when a blocker exists. |
| Adapter | `spec_adapter.py` | Converts the gated spec into the renderer's slide dict (and legacy renderer specs back into `lesson_spec` for migration). |
| Renderer | `generate_lesson_package.py` | Canonical map-first PPTX renderer, 26 archetypes. Never called directly on production content; the gate calls it. |

Procedure:

1. Draft `lesson_spec.json` using `references/package-schema.md` (schema 1.2, 26-field slide contract, `layout_spec.card_data` for structured visuals).
2. Run the gate from the repository root:

```bash
python skills/harrity-lesson-builder-pipeline/scripts/validate_and_gate.py --spec lesson_spec.json --outdir output_folder
python skills/harrity-lesson-builder-pipeline/scripts/validate_unified_package.py output_folder
```

3. Read `qa_log.md`. A `blocked` status means the deck is `_DRAFT` and must not be delivered. Fix the spec and rerun; never edit generated files by hand.
4. Inspect generated files. Revise the JSON and rerun when sequencing, visual density, CJM coverage, or learner tasks are weak.

For a clearly labeled test package only:

```bash
python skills/harrity-lesson-builder-pipeline/scripts/validate_and_gate.py --demo --outdir output_folder
```

To migrate a package written in the renderer's own legacy spec format (`references/renderer-spec.md`):

```bash
python skills/harrity-lesson-builder-pipeline/scripts/validate_and_gate.py --legacy legacy_spec.json --outdir output_folder
```

### Stage 10: Build assessment and remediation map

Use `references/remediation-rules.md`.

When quiz performance, item misses, or learner questions are provided, classify the miss by failed thinking operation, not only by topic:

- cannot notice the relevant data -> recognize cues
- notices data but cannot explain meaning -> analyze cues
- explains meaning but chooses wrong urgency -> prioritize hypotheses
- knows priority but cannot select plan -> generate solutions
- knows plan but does not implement safely -> take action
- acts but does not reassess -> evaluate outcomes

For each weak area, produce:

- map location
- concept lane
- missed CJM function
- likely misconception
- one-slide fix
- active-learning task
- retrieval item
- improvement evidence

### Stage 11: Audio and video handoff

When requested, create audio and video packages from approved scripts only. Do not mutate content during audio export.

Audio fields:

- `slide_id`
- `narration_text`
- `target_duration_seconds`
- `pause_markers`
- `emphasis_terms`
- `pronunciation_notes`
- `voice_style`
- `transition_line`
- `output_mode`
- optional `ssml_ready_text`

Video fields:

- slide order
- audio filename
- duration
- caption text
- auto-advance timing
- export notes
- readiness status

### Stage 12: Full QA and release gate

Set package status:

- `release-ready`: no blockers or major defects.
- `faculty-review-needed`: no blockers, but source or clinical review remains.
- `draft-only`: source, taxonomy, or clinical verification gaps remain.
- `blocked`: unsafe issue, export failure, source insufficiency, or schema failure.

Severity rules:

- `blocker`: do not export as final.
- `major`: fix before final release.
- `minor`: acceptable draft or polish issue.

### Stage 13: Dependency-aware revision

When revising:

1. Identify changed slide IDs, glossary terms, taxonomy fields, source records, or media files.
2. Keep unaffected slide IDs locked.
3. Rebuild only affected downstream artifacts unless scope, order, taxonomy, or source base changed.
4. Produce a revision log with previous value summary, new value summary, reason, and downstream effects.
5. Re-run affected QA gates.

If a slide is split, preserve the original as retired parent and create child IDs such as `S03A` and `S03B`.

## Five-channel separation

Never collapse these channels:

1. `slide.on_slide_text`: concise learner-facing text.
2. `narration.speaker_script`: complete faculty script.
3. `speech.tts_text`: TTS-safe narration.
4. `layout.layout_spec`: regions, density budget, archetype, overlap rule.
5. `media.binding`: audio, captions, duration, auto-advance, and video export metadata.

## Production slide contract

Every production slide must carry:

- `slide_id`
- `slide_number`
- `slide_title`
- `slide_archetype`
- `lesson_section`
- `concept_lane`
- `source_refs`
- `evidence_status`
- `cjm_functions`
- `nursing_action_category`
- `learning_objective`
- `on_slide_text`
- `activity_prompt`
- `answer_key`
- `visual_notes`
- `speaker_script`
- `tts_text`
- `target_duration_sec`
- `audio_duration_sec`
- `auto_advance`
- `layout_spec`
- `allow_overlap`
- `qa_status`
- `qa_notes`
- `remediation_target`
- `audio_filename`

## Evidence status values

Use one of:

- `source-grounded`
- `source-aligned`
- `inferred`
- `illustrative-example`
- `instructor-added`
- `provisional`
- `unresolved`
- `needs-verification`

Do not label inferred content as source-grounded.

## Resource map

- `references/dynamic-variable-contract.yaml`: runtime variable requirements and anti-hardcoding rules.
- `references/runtime-pipeline-map.md`: stage map and variable flow.
- `references/runtime_config.schema.json`: runtime config validation schema.
- `references/map-first-lesson-blueprint.md`: Harrity high-level map and slide architecture.
- `references/cjm-concept-model.md`: clinical judgment model crosswalk requirements.
- `references/remediation-rules.md`: quiz-miss and learner-question drill-down rules.
- `references/package-schema.md`: `lesson_spec.json` schema 1.2 — production slide contract, card_data shapes, governance envelope, generator contract.
- `references/renderer-spec.md`: the renderer's native slide-dict format; reached only through `scripts/spec_adapter.py`.
- `references/master_lesson/`: master-lesson 1.0.0 JSON Schema and template (governance envelope source).
- `references/lesson-artifact-schemas.md`: outline, script, audio, and revision JSON shapes.
- `references/lesson-quality-gates.md`: stage QA gates.
- `references/qa-checklist.md`: blocker, major, and minor defects.
- `references/failure-modes.md`: common pipeline failures and prevention rules.
- `references/consolidated-prompt-pack.md`: copy-ready prompts for controlled lesson generation.
- `references/video-handoff-prompt-pack.md`: audio/video handoff prompts from the merged video workflow.
- `scripts/validate_runtime_config.py`: validates runtime config.
- `scripts/render_prompt.py`: renders templates from runtime config.
- `scripts/validate_lesson_json.py`: validates outline, script, and audio JSON artifacts.
- `scripts/validate_and_gate.py`: gate + package writer; the one command for Stage 9.
- `scripts/spec_adapter.py`: lesson_spec ⇄ renderer slide dict.
- `scripts/generate_lesson_package.py`: canonical PPTX renderer (26 archetypes).
- `scripts/validate_unified_package.py`: post-build package directory check.
- `assets/reference_montage.png`: visual reference for the map-first slide style.

## Final response pattern

When completing a user task, return:

1. what was built or revised
2. actual file links when files were created
3. assumptions and unresolved items
4. QA status
5. revision log when applicable

For skill-update tasks, change the files in place, log the change in `docs/`, and confirm `pytest -q tests/` passes.
