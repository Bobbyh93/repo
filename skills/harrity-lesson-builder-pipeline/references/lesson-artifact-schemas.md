# Lesson Artifact Schemas

Use these canonical shapes for automation mode, Codex handoff, or saved JSON packages. Keep field names stable across revisions.

## Enumerations

- `audience_level`: `beginner` | `intermediate` | `advanced` | `mixed`
- `mode`: `interactive` | `automation`
- `evidence_status`: `source-grounded` | `source-aligned` | `inferred` | `illustrative-example` | `instructor-added` | `provisional` | `unresolved` | `needs-verification`
- `qa_status`: `pass` | `pass_with_warnings` | `fail`
- `package_status`: `release-ready` | `faculty-review-needed` | `draft-only` | `blocked`
- `cjm_function`: `recognize cues` | `analyze cues` | `prioritize hypotheses` | `generate solutions` | `take action` | `evaluate outcomes`

## Slide identity rule

- `slide_id` is the persistent identifier and should match `^S\d{2}[A-Z]?$`.
- `slide_number` is the current order and may change if slides are inserted or reordered.
- Never recycle a retired `slide_id`.

## Normalized intake object

```json
{
  "audience_level": "beginner",
  "lesson_goal": "Explain the core process and apply it to nursing judgment.",
  "language": "en",
  "mode": "automation",
  "duration_budget_seconds": 1200,
  "slide_budget": {"min": 8, "max": 16},
  "sources": {
    "text_items": ["..."],
    "files": ["..."],
    "tables": [
      {
        "name": "outcome_taxonomy",
        "notes": "Approved outcome categories",
        "rows": [{"category": "...", "description": "..."}]
      }
    ],
    "quiz_analysis": []
  },
  "required_terminology": ["..."],
  "forbidden_assumptions": ["..."],
  "assumptions": ["..."],
  "warnings": ["..."],
  "conflicts": [
    {
      "issue": "...",
      "source_conflict": ["source A", "source B"],
      "working_decision": "...",
      "status": "open"
    }
  ]
}
```

## Glossary and taxonomy object

```json
{
  "glossary": [
    {
      "term": "cue",
      "definition": "Patient information relevant to the clinical problem.",
      "synonyms_allowed": ["finding"],
      "forbidden_variants": [],
      "first_introduced_slide_id": null
    }
  ],
  "concept_tags": ["structure-function", "risk", "teaching"],
  "outcome_tags": ["explain", "apply", "prioritize"],
  "nclex_client_needs": [],
  "ngn_cjmm_functions": [
    "recognize cues",
    "analyze cues",
    "prioritize hypotheses",
    "generate solutions",
    "take action",
    "evaluate outcomes"
  ],
  "synonym_policy": "Use approved glossary terms exactly unless a synonym is explicitly allowed.",
  "proposed_new_tags": []
}
```

## Harrity blueprint object

```json
{
  "opening_patient_question": "A patient asks a clinically relevant question.",
  "organizing_clinical_question": "What must the nurse understand, notice, prioritize, do, and evaluate?",
  "concept_lanes": [
    {"label": "recognize", "description": "what data matter"},
    {"label": "interpret", "description": "what the data mean"},
    {"label": "prioritize", "description": "what matters first"},
    {"label": "act", "description": "what the nurse does"},
    {"label": "evaluate", "description": "how response is judged"}
  ],
  "chapter_map": [
    {"step": 1, "label": "foundation", "question": "what is normal or expected?"},
    {"step": 2, "label": "cue", "question": "what changed?"},
    {"step": 3, "label": "risk", "question": "what could happen next?"},
    {"step": 4, "label": "action", "question": "what should the nurse do?"}
  ],
  "drill_down_triggers": ["low quiz performance", "frequent learner question", "unsafe priority choice"]
}
```

## Outline package

```json
{
  "stage": "outline",
  "audience_level": "beginner",
  "lesson_goal": "Explain the concept and apply it to bedside nursing judgment.",
  "duration_budget_seconds": 1200,
  "slides": [
    {
      "slide_id": "S01",
      "slide_number": 1,
      "slide_title": "What the nurse is trying to decide",
      "lesson_section": "Map",
      "concept_lane": "overview",
      "learning_objective": "State the organizing clinical question.",
      "main_point": "The chapter is organized around a patient-centered clinical decision.",
      "sub_points": ["Recognize the relevant cues.", "Explain meaning.", "Choose safe action."],
      "definitions": [
        {"term": "clinical judgment", "definition": "The process of noticing, interpreting, prioritizing, acting, and evaluating."}
      ],
      "evidence_examples": [
        {"type": "source-grounded", "text": "Source or course objective reference."}
      ],
      "concept_tags": ["map"],
      "outcome_tags": ["explain"],
      "cjm_functions": ["recognize cues"],
      "nursing_action_category": "assess",
      "prerequisite_slide_ids": [],
      "estimated_duration_seconds": 75,
      "evidence_status": "source-grounded",
      "remediation_target": null
    }
  ]
}
```

## Script package

```json
{
  "stage": "script",
  "audience_level": "beginner",
  "slides": [
    {
      "slide_id": "S01",
      "slide_title": "What the nurse is trying to decide",
      "target_duration_seconds": 75,
      "speaker_script": "This slide frames the lesson around the patient question and the nurse's decision.",
      "tts_text": "This slide frames the lesson around the patient question and the nurse's decision.",
      "delivery_notes": ["Keep the focus on the decision, not memorization."],
      "pronunciation_notes": [],
      "net_new_items": [],
      "evidence_status": "source-grounded"
    }
  ]
}
```

## Audio package

```json
{
  "stage": "audio",
  "voice_style": "clear, instructional, measured",
  "slides": [
    {
      "slide_id": "S01",
      "narration_text": "This slide frames the lesson around the patient question and the nurse's decision.",
      "target_duration_seconds": 75,
      "pronunciation_notes": [],
      "pause_markers": ["After the patient question"],
      "emphasis_terms": ["notice", "meaning", "priority", "action"],
      "transition_line": "Next, we map the concepts that support that decision.",
      "output_mode": "plain narration",
      "ssml_ready_text": null
    }
  ]
}
```

## Revision log object

```json
{
  "revision_log": [
    {
      "item_type": "slide",
      "item_id": "S03",
      "previous_value_summary": "One overloaded slide covering cue recognition and priority.",
      "new_value_summary": "Split into S03A cue recognition and S03B priority sort.",
      "reason": "Quiz misses showed separate failures in recognizing cues and prioritizing hypotheses.",
      "downstream_effects": ["Update scripts for S03A and S03B", "Recompute pacing", "Update assessment map"]
    }
  ]
}
```
