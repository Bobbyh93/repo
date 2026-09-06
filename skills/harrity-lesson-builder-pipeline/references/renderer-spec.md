# Renderer spec (legacy format)

This is the native input format of `scripts/generate_lesson_package.py`, the canonical renderer. **Production content does not use this format directly.** Author `lesson_spec.json` per `package-schema.md` and let `scripts/spec_adapter.py` produce this shape. The format is documented so that (a) pass-through `card_data` keys can be written per archetype and (b) pre-v1 packages can be migrated with `validate_and_gate.py --legacy`.

## Top-level object

```json
{
  "metadata": {
    "course": "string",
    "unit": "string",
    "chapter": "string",
    "topic": "string",
    "audience": "string",
    "duration_minutes": 60,
    "source_status": "source-grounded | provisional | needs-verification",
    "package_id": "string"
  },
  "clinical_question": "string",
  "concept_lanes": [
    {"label": "string", "description": "string"}
  ],
  "slides": [],
  "quiz_analysis": []
}
```

## Required metadata rules

- `topic`, `chapter`, `audience`, and `clinical_question` must come from the user/source or be marked as assumptions.
- `source_status` must not be upgraded beyond the actual source support.
- `package_id` should match the frozen runtime config when one exists.

## Slide object

```json
{
  "type": "clinical_question",
  "slide_id": "S03",
  "title": "the clinical question that organizes the chapter",
  "subtitle": "optional short subtitle",
  "module_label": "chapter map",
  "concept_lane": "overview",
  "cjm_steps": ["recognize cues", "analyze cues"],
  "concepts": ["create", "support", "protect", "signal"],
  "learner_task": "explain which lane a cue belongs to",
  "remediation_target": "analyze cues",
  "source_status": "source-grounded",
  "speaker_notes": "educator-facing notes or answer key",
  "content": {}
}
```

## Supported slide types

The generator supports these `type` values. Unknown types render as generic content slides.

- `title`
- `opening_case`
- `clinical_question`
- `chapter_map`
- `warmup_sequence`
- `concept_cards`
- `match_activity`
- `debrief`
- `control_room`
- `timeline`
- `checkpoint_mcq`
- `process_map`
- `teaching_point`
- `exchange_model`
- `triad`
- `safety_chain`
- `compare`
- `risk_engine`
- `mini_case`
- `urgency_sort`
- `script_template`
- `basics_grid`
- `capstone_mcq`
- `debrief_three`
- `retrieval_check`
- `takeaway`
- `generic`

## Common content shapes

### Cards

```json
"cards": [
  {"title": "ovaries", "body": "produce ova and reproductive hormones"},
  {"title": "uterus", "body": "supports implantation, fetal growth, and contractions"}
]
```

### Timeline milestones

```json
"milestones": [
  {"label": "fertilization", "body": "sperm and ovum unite"},
  {"label": "implantation", "body": "blastocyst embeds in endometrium"}
]
```

### Multiple choice

```json
"question": "a patient asks... what is the best response?",
"options": ["option a", "option b", "option c", "option d"],
"answer": "c",
"rationale": "explain why c is safest"
```

### Match activity

```json
"left_items": ["cue", "structure", "risk"],
"right_items": ["meaning", "function", "priority"],
"answer_key": ["cue -> meaning", "structure -> function", "risk -> priority"]
```

## Quiz analysis input

```json
"quiz_analysis": [
  {
    "objective": "explain implantation timing and safety cues",
    "score_percent": 58,
    "miss_type": "risk priority",
    "cjm_step": "prioritize hypotheses",
    "evidence": "students selected reassurance when escalation cues were present",
    "remediation": "urgency sort plus patient teaching script"
  }
]
```

## Generated package files

The generator creates:

- `lesson_deck.pptx`
- `facilitator_guide.md`
- `learner_handout.md`
- `assessment_map.csv`
- `lesson_manifest.json`

Validate the package directory with:

```bash
python skills/harrity-lesson-builder-pipeline/scripts/validate_unified_package.py output_folder
```
