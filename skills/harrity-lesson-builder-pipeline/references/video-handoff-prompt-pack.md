# Prompt Pack

Use these prompts as starting templates. Replace bracketed values before use.

## 1. Intake and preflight

```text
Use the lesson-video-builder process.

Source material:
[source text, notes, file summaries, or tables]

Inputs:
- target audience: [beginner/intermediate/advanced]
- lesson goal: [goal]
- lesson scope: [scope]
- target duration minutes: [n]
- target slide count: [n or auto]
- output language: [language]
- required terms: [list]
- forbidden assumptions: [list]
- concept tag taxonomy: [list]
- outcome tag taxonomy: [list]

First, run intake and preflight only.
Return:
1. normalized inputs
2. assumptions
3. blockers
4. conflict log
5. teach/mention/appendix/exclude classification
Do not generate the outline yet.
```

## 2. Glossary and taxonomy lock

```text
Using the approved intake and source material, generate:
1. approved glossary
2. approved concept tags
3. approved outcome tags
4. proposed new tags if absolutely required
5. conflict log

Do not generate slides yet.
```

## 3. Slide outline generation

```text
Using the approved intake, glossary, and taxonomy, generate a slide-by-slide lesson outline.

Requirements:
- one core teaching objective per slide
- stable slide ids
- include definitions when terms first appear
- estimated duration per slide
- concept tags and outcome tags only from the approved taxonomy
- mark each slide source_status as source-grounded, inferred, suggested-example, or unresolved

Return both:
1. readable markdown outline
2. machine-readable slide schema block
```

## 4. Outline QA

```text
Audit the outline before scripting.
Check for:
- missing required concepts
- duplicate slides
- overloaded slides
- timing problems
- taxonomy mismatches
- glossary inconsistencies
- audience mismatch

Return:
1. pass/fail summary
2. issue list by slide id
3. corrected outline if fixes are straightforward
```

## 5. Presenter scripts per slide

```text
Generate exactly one presenter script per slide id using the approved outline.

Requirements:
- follow the approved glossary
- no fluff
- no unsupported net-new claims
- natural spoken style
- one script block per slide id
- include target_duration_seconds
- include pronunciation_notes only when useful

Audience level: [level]
Narration density: [density]
```

## 6. Script QA

```text
Audit the scripts against the outline and glossary.
Reject or fix any script that:
- overruns timing
- changes approved definitions
- adds unsupported claims
- merges multiple slides
- sounds padded or repetitive
- relies too heavily on visuals

Return a per-slide QA result and corrected scripts where needed.
```

## 7. Audio handoff

```text
Convert the approved scripts into audio-ready narration.

Output mode: [plain narration / tts prompt / ssml-ready]
Voice style: [style]

For each slide return:
- slide_id
- narration_text
- target_duration_seconds
- pause_markers
- emphasis_terms
- pronunciation_notes
- transition_line
- output_mode
```

## 8. Controlled revision

```text
Revise only these slide ids: [ids]
Requested changes: [changes]

Preserve all unchanged slide ids, timing assumptions, and glossary terms unless the request explicitly changes them.
Return:
1. revised items only
2. change log
3. any downstream impacts on adjacent slides or audio handoff
```
