# Prompt Pack

Use these prompts when the user wants a copy-ready template, when a separate ChatGPT instance needs an exact workflow, or when Codex needs a deterministic instruction block.

## 1. End-to-end orchestration prompt

```text
Build a lesson package from the source material below using this locked sequence:
1. preflight and normalize input
2. lock glossary and taxonomy
3. build slide outline
4. run outline qa
5. generate slide-by-slide presenter scripts
6. run script qa
7. export audio-ready narration
8. produce a revision log

Operating rules:
- keep stable slide_id values across all stages
- use one core teaching objective per slide
- distinguish source-grounded, inferred, illustrative-example, and unresolved content
- use approved tags only; put any new tag into proposed_new_tags
- keep total duration within budget or flag the mismatch clearly
- keep scripts dense, detailed, and free of fluff
- do not introduce net-new core topics in scripts unless they are flagged in net_new_items
- return assumptions instead of blocking on missing details

Inputs:
- mode: <interactive|automation>
- source_text: <paste or summarize source text>
- source_tables: <paste taxonomy tables or category tables>
- audience_level: <beginner|intermediate|advanced|mixed>
- lesson_goal: <what learners should be able to do>
- duration_budget_seconds: <target total duration>
- slide_budget: <optional min/max slide count>
- required_terminology: <terms that must be preserved>
- forbidden_assumptions: <what cannot be guessed>
- language: <output language>

Return the full pipeline in stage order.
```

## 2. Preflight prompt

```text
Normalize the lesson inputs below before drafting slides.

Required output sections:
1. normalized intake
2. assumptions
3. conflict log
4. warnings
5. proposed scope

Inputs:
- source_text:
- source_tables:
- audience_level:
- lesson_goal:
- duration_budget_seconds:
- slide_budget:
- required_terminology:
- forbidden_assumptions:
- language:
- mode:

Rules:
- do not draft slides yet
- if content is contradictory or incomplete, surface it explicitly
- propose a reasonable scope even when details are missing
```

### Interactive preflight template

```markdown
## Preflight

### Normalized intake
- Audience level:
- Lesson goal:
- Language:
- Mode:
- Duration budget:
- Slide budget:
- Source summary:

### Assumptions
- ...

### Conflict log
- issue:
  source conflict:
  working decision:

### Warnings
- ...

### Proposed scope
- ...
```

## 3. Glossary and taxonomy prompt

```text
Create the locked glossary and tag taxonomy for the lesson before building slides.

Return:
- approved glossary
- concept_tags
- outcome_tags
- synonym policy
- forbidden substitutions
- proposed_new_tags

Rules:
- keep definitions short and stable
- reuse supplied category tables when available
- do not allow freeform tag drift
```

## 4. Outline generation prompt

```text
Using the approved preflight and glossary artifacts, create the slide outline.

Return one slide object per slide with these fields:
- slide_id
- slide_number
- slide_title
- lesson_section
- learning_objective
- main_point
- sub_points
- definitions
- evidence_examples
- concept_tags
- outcome_tags
- prerequisite_slide_ids
- estimated_duration_seconds
- evidence_status

Rules:
- keep one core teaching objective per slide
- fit total estimated time to the duration budget
- mark unsupported or inferred material explicitly
- prefer appendix placement over overloaded slides
```

### Interactive outline template

```markdown
## Slide S01 - <title>
- Lesson section:
- Learning objective:
- Main point:
- Sub-points:
  - ...
- Definitions:
  - term: definition
- Evidence/examples:
  - [source-grounded|inferred|illustrative-example|unresolved] ...
- Concept tags:
- Outcome tags:
- Prerequisites:
- Estimated duration:
```

## 5. Outline QA prompt

```text
Audit the outline before scripting.

Return:
- qa_status: pass | pass_with_warnings | fail
- blockers
- warnings
- recommended_fixes
- locked_slide_ids_for_scripting

Check for:
- coverage gaps
- duplicate slides
- audience mismatch
- taxonomy drift
- pacing errors
- unsupported claims
- overloaded slides
```

## 6. Script generation prompt

```text
Write one presenter script block per approved slide.

Return for each slide:
- slide_id
- slide_title
- target_duration_seconds
- script
- evidence_status
- delivery_notes
- net_new_items

Rules:
- do not change slide_id values
- keep scripts detailed and efficient, with no filler
- explain for the locked audience level
- reuse approved glossary terms exactly
- flag any net-new core topic instead of blending it in silently
```

### Interactive script template

```markdown
## Script for S01 - <title>
- Target duration:
- Evidence status:
- Delivery notes:
- Net-new items:

Speaker script:
<verbatim narration>
```

## 7. Script QA prompt

```text
Audit the script package against the approved outline.

Return:
- qa_status: pass | pass_with_warnings | fail
- blockers
- warnings
- timing_notes
- glossary_issues
- revision_targets

Check for:
- one-to-one mapping between slide ids and script blocks
- outline-to-script alignment
- unsupported claims
- duration mismatch
- audience mismatch
- narration that depends on unseen visuals
- redundancy or fluff
```

## 8. Audio export prompt

```text
Convert the approved scripts into an audio-ready narration package.

Return for each slide:
- slide_id
- narration_text
- target_duration_seconds
- pronunciation_notes
- pause_markers
- emphasis_terms
- transition_line
- ssml_ready_text (optional)

Rules:
- keep narration natural for voice delivery
- add pronunciation notes only when helpful
- use pause markers for clarity, not decoration
- do not introduce new teaching content here
```

### Interactive audio template

```markdown
## Audio for S01 - <title>
- Target duration:
- Pronunciation notes:
- Pause markers:
- Emphasis terms:
- Transition line:

Narration text:
...
```

## 9. Revision prompt

```text
Apply a controlled revision to the lesson package.

Inputs:
- items_to_change: <slide ids, glossary terms, or taxonomy items>
- change_request:
- keep_locked: <everything else that must remain fixed>

Return:
- updated artifacts for affected items only
- revision_log with previous value summary, new value summary, reason, and downstream effects
- qa results for the affected stages

Rules:
- do not regenerate untouched slides
- keep stable slide ids
- if a slide is split, retire the parent id and create child ids like S03A and S03B
```
