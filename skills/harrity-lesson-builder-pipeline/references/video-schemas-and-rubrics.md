# Schemas and Rubrics

## Slide schema

```yaml
slide_id: S01
slide_number: 1
slide_title: string
lesson_section: string
learning_objective: string
main_point: string
sub_points:
  - string
definitions:
  - term: string
    definition: string
evidence_or_examples:
  - string
concept_tags:
  - string
outcome_tags:
  - string
prerequisite_links:
  - slide_id
estimated_duration_seconds: 60
source_status: source-grounded
```

## Script schema

```yaml
slide_id: S01
target_duration_seconds: 60
transition_in: optional string
presenter_script: string
transition_out: optional string
pronunciation_notes:
  - optional string
```

## Audio schema

```yaml
slide_id: S01
narration_text: string
target_duration_seconds: 60
pause_markers:
  - short pause after phrase x
emphasis_terms:
  - string
pronunciation_notes:
  - optional string
voice_style: clear instructional
transition_line: optional string
output_mode: plain narration
```

## Outline QA rubric

Pass only if all conditions hold:

- every slide has one clear learning objective
- the full concept set is covered
- the sequence fits the target audience
- definitions appear when needed
- estimated durations fit the lesson budget
- concept tags and outcome tags are valid
- no obvious duplication or overlap exists

## Script QA rubric

Pass only if all conditions hold:

- exactly one script block exists per slide id
- the script supports the approved slide objective
- the script uses glossary terms consistently
- timing is realistic for spoken delivery
- unsupported claims are flagged, not blended in
- wording is direct and not padded

## Common failure patterns

- outline generated before glossary lock
- slide ids change between rounds
- concept tags become freeform labels
- scripts add new concepts that were never outlined
- duration budgets are ignored until the end
- audio output repeats slide text instead of teaching naturally

## Default speaking-rate guidance

Use these assumptions unless overridden:

- dense instructional narration: 130 to 145 wpm
- standard clear instruction: 140 to 155 wpm
- highly technical explanation with pauses: 120 to 140 wpm

Estimate timing conservatively when the content is definition-heavy.
