---
name: harrity-lesson-builder-pipeline
description: Build learner-facing, exam-prep nursing lesson experiences from source content. Use when converting uploaded decks, notes, chapter files, concept maps, or approved taxonomy rows into student-facing active content presentations, guided notes, embedded retrieval/application items, speaker notes, item maps, QA logs, and package manifests. Default output is the learner's actual class experience, not a presentation about the lesson plan.
version: 0.3.0
updated: 2026-05-09
---

# Harrity Lesson Builder Pipeline

## Operating Goal

Build the learner's actual content experience.

The primary deliverable is a student-facing, exam-prep active teaching presentation. Instructor planning artifacts are secondary and must not become the centerpiece unless the user explicitly requests instructor-only planning.

## Core Rule

```text
VISIBLE SLIDES ARE FOR LEARNERS.
```

Do not place instructor planning language on visible slides. Speaker notes and secondary guides may contain facilitation guidance, expected answers, timing, remediation prompts, and rationale expansion.

## Default Output Mode

If the user does not specify otherwise, set:

```yaml
primary_output_mode: learner_facing_content_experience
learner_population: prelicensure_bsn
exam_orientation: ati_nclex_ngn
learner_priority:
  - exam_readiness
  - clinical_judgment
  - retention
  - patient_teaching
```

Allowed output modes:

1. `learner_facing_content_experience` - default; actual student-facing lesson deck.
2. `student_study_guide` - study handout or guided notes.
3. `instructor_lesson_plan` - instructor planning package only when explicitly requested.
4. `assessment_item_bank` - questions, rationales, distractor logic, and blueprint.
5. `remediation_module` - targeted reteaching and practice for at-risk learners.
6. `production_package` - manifests, render checks, accessibility checks, and QA logs.

## Default Artifact Hierarchy

Primary outputs:

1. Learner-facing active content deck or deck assembly manifest.
2. Student guided notes or study handout.
3. Embedded retrieval/application item bank.
4. QA and coverage map.

Secondary outputs:

5. Instructor facilitation notes in speaker notes or a separate guide.
6. Item map and rationale map.
7. Production manifest.
8. Accessibility/readability report.

The instructor guide must never outrank the learner-facing deck unless `primary_output_mode = instructor_lesson_plan`.

## Required Input Contract

Every run must require, infer, or explicitly mark unresolved:

```yaml
lesson_build_request:
  source_files:
    - deck_or_notes_or_text
  learner_population: prelicensure_bsn
  course_context: string
  chapter_or_topic: string
  session_length_minutes: integer
  exam_orientation: ati_nclex_ngn
  output_mode:
    primary: learner_facing_content_experience
    secondary:
      - student_handout
      - instructor_facilitation_notes
      - item_map
      - qa_log
  learner_priority:
    - exam_readiness
    - clinical_judgment
    - retention
    - patient_teaching
  source_status:
    exact_source_text_available: boolean
    proprietary_text_restriction: boolean
```

If required values are missing, do not stop unless the missing value blocks safe content creation. Infer conservative defaults, log assumptions, and mark unresolved fields.

## Required Execution Order

```text
1. Ingest source content.
2. Extract concept clusters and source status.
3. Build learner profile and exam-readiness goal.
4. Generate concept-to-assessment blueprint.
5. Select running case or clinical frame.
6. Build content sequence using required slide grammar.
7. Generate learner-facing slide deck or deterministic deck manifest.
8. Generate speaker notes separately.
9. Generate student handout or guided notes.
10. Generate item/rationale map.
11. Run QA gates.
12. Render visual preview when possible.
13. Package outputs.
14. Report limitations and unresolved source gaps.
```

Do not generate visible slide content from raw source fragments without organizing the fragments into concept clusters and learner-facing exam anchors.

## Required Slide Grammar

Each major content block must follow this loop:

```text
Patient cue -> Student prediction -> Core concept -> Exam anchor -> Common trap -> Practice item -> Rationale -> Takeaway
```

Minimum required block types:

| Block Type | Function |
|---|---|
| Case opener | Establish clinical relevance. |
| Concept build | Teach necessary content visibly and simply. |
| Exam anchor | Declare what students must know for testing. |
| Common trap | Prevent high-frequency misconceptions. |
| Student response | Force retrieval or decision-making. |
| Rationale | Explain why the answer/action is safest. |
| Transfer prompt | Apply concept to a new cue. |
| Exit check | Confirm retention targets. |

## Learner-Facing Slide Rules

Visible slide body must:

- Use student-facing language.
- Avoid lesson-plan labels such as `teaching move`, `facilitator note`, `presenter intent`, `production note`, `script focus`, or `visual production note`.
- Include a clear task when asking students to respond.
- Keep cognitive load controlled: one major decision or concept per slide whenever possible.
- Give students a retrieval opportunity before revealing the answer/rationale.
- Make testable priorities explicit.
- Keep text concise enough for projection and note-taking.

Speaker notes may include:

- Instructor timing.
- Expected answers.
- Rationale expansion.
- Facilitation prompts.
- Remediation notes.
- Optional escalation or debrief language.
- Source limitations and proprietary-source safety notes.

## Exam-Prep Design Controls

Every lesson must include:

| Control | Minimum Standard |
|---|---|
| Exam anchors | At least 1 per major concept cluster. |
| Common traps | At least 1 per high-risk misconception cluster. |
| Retrieval density | At least 1 retrieval or decision prompt every 3-4 slides. |
| NGN/CJM alignment | At least one cue-recognition, prioritization, or next-action item. |
| Rationales | Every scored/checkpoint item must include a rationale. |
| Study summary | Final takeaways must be formatted as student-study notes. |
| Transfer | At least one second patient scenario or altered cue set. |

## Source and Safety Rules

- Preserve source status: `source-grounded`, `inferred`, `provisional`, or `unresolved`.
- Do not claim exact ATI wording or proprietary textbook wording unless exact source text is provided and allowed.
- Do not fabricate citations, page numbers, item IDs, or official standards.
- Use external current clinical safety sources only when user-provided materials are insufficient or safety guidance is current-sensitive.
- Mark all assumptions in the manifest and QA log.

## Required QA Gates

Run these checks before delivery:

```yaml
qa_gates:
  QA01_source_traceability: each major content area maps to source material
  QA02_visible_learner_only: no instructor/meta language on slide bodies
  QA03_exam_anchor_density: exam anchors present for major concepts
  QA04_interaction_density: retrieval/application prompt every 3-4 slides
  QA05_rationale_coverage: every item has a rationale
  QA06_clinical_judgment_alignment: cues/actions map to CJM-style reasoning
  QA07_common_trap_coverage: misconceptions explicitly addressed
  QA08_cognitive_load: slide text and task complexity checked
  QA09_accessibility: font size, contrast, reading order, alt-text placeholder
  QA10_assessment_blueprint: outputs include item/concept/objective mapping
  QA11_student_reception_review: anxious exam-focused learners can identify what to study
  QA12_proprietary_source_safety: no claim of exact ATI/proprietary language unless provided
  QA13_artifact_truthfulness: no claim that a file exists unless it was created
  QA14_preview_render: preview checked or render limitation recorded
```

If any P0 gate fails, report `status = blocked` or `status = conditional` and state the defect plainly.

## Required Metadata Tables

### Slide Map

| Field | Description |
|---|---|
| slide_id | Stable ID: S01, S02, etc. |
| slide_number | Slide number. |
| slide_title | Visible title. |
| block_type | case, concept, exam_anchor, trap, item, rationale, summary. |
| source_concept | Source concept cluster. |
| learner_task | What the learner does. |
| exam_anchor | Must-know testable point. |
| cjm_step | Recognize cues, analyze cues, prioritize hypotheses, generate solutions, take action, evaluate outcomes. |
| visible_language_check | pass, revise, blocked. |
| notes_status | Speaker notes present or not. |

### Item Map

| Field | Description |
|---|---|
| item_id | Unique ID. |
| slide_id | Related slide. |
| item_type | MCQ, cue sort, sequencing, short answer, teach-back. |
| objective | Tested learning target. |
| correct_answer | Correct answer or expected response. |
| rationale | Reasoning. |
| distractor_logic | Why wrong answers are wrong. |
| difficulty | low, moderate, high. |
| cjm_step | CJM/NCJMM step. |

## Definition of Done

A build is complete only when:

- A learner could use the deck to identify what to study for the exam.
- Visible slides contain no instructor/meta planning language.
- Every major concept has a testable anchor.
- Every activity has a correct answer or expected response.
- Every checkpoint item has a rationale.
- Clinical judgment content includes cue recognition and prioritization.
- A QA log identifies passes, limitations, and unresolved source gaps.
- A preview render has been checked for readability and clipping, or render constraints are stated.
- Generated files actually exist before they are claimed.

## Continuation Behavior

For user commands such as `continue`, `proceed`, or `use the full skill`, identify the next incomplete stage and execute it. Do not skip to deck generation if source ingestion, concept clustering, learner mode selection, or QA prerequisites are incomplete.
