# Quality Gates

Use these checks to decide whether to proceed, revise, or block the next stage.

## Decision rule

- `pass`: no blockers and no unresolved structural issues
- `pass_with_warnings`: usable but has non-blocking concerns that should be noted
- `fail`: at least one blocker is present

## Global blockers

Fail any stage if one of these is true:
- duplicate `slide_id` values exist
- a required field from `references/schemas.md` is missing
- the glossary or taxonomy changed silently after approval
- the duration budget is violated by more than 20 percent without an explicit note
- unsupported factual claims are presented as source-grounded

## Preflight QA

Check:
- required inputs are either present or replaced with explicit assumptions
- contradictions are surfaced in the conflict log
- the lesson goal is concrete enough to teach toward
- the audience level is locked or marked as assumed
- the scope is teachable within the stated budget

Common blocker examples:
- no clear lesson goal
- source material is too contradictory to outline without a decision
- taxonomy table is malformed and no fallback taxonomy is proposed

## Outline QA

Check:
- every required concept is covered
- each slide has one clear learning objective
- slide flow respects prerequisites
- definitions appear before or at first use
- concept tags and outcome tags come from the approved taxonomy
- total estimated duration fits the budget or is clearly flagged
- evidence status is set correctly for each slide
- appendix-worthy material is not crowding the main sequence

Warnings:
- a slide feels dense but still teachable
- a concept appears twice as reinforcement rather than duplication
- total duration is within 10 to 20 percent of the target

Blockers:
- duplicate teaching objectives
- missing foundational definition
- unsupported claim labeled as source-grounded
- major pacing mismatch

## Script QA

Check:
- there is exactly one script block per approved `slide_id`
- script order matches current slide order
- each script aligns to the slide objective and main point
- scripts reuse approved terminology
- net-new core topics are empty or explicitly flagged
- wording matches audience level
- estimated speaking rate is plausible for the target duration
- fluff, repetition, and meta commentary are minimized
- narration does not rely on visuals the listener cannot see unless clearly intentional

Warnings:
- speaking rate is slightly fast or slow
- a sentence could be tightened without changing meaning
- a delivery note should be added for pronunciation or emphasis

Blockers:
- missing or extra slide script
- a script changes the lesson meaning relative to the outline
- a script introduces unflagged net-new core content
- timing is implausible for normal narration

## Audio QA

Check:
- every approved script has a matching audio object
- pronunciation notes exist for hard terms when needed
- pause markers improve clarity rather than clutter the script
- transition lines connect adjacent slides cleanly
- optional ssml is syntactically plausible if included
- no new teaching content is introduced at the audio stage

Warnings:
- optional pronunciation note is missing for a low-risk term
- pause markers are sparse but acceptable

Blockers:
- narration text is missing for any slide
- audio stage changes the lesson meaning
- timing changed materially without explanation

## Revision QA

Check:
- only requested items were changed
- unaffected slide ids stayed locked
- the revision log explains the change and downstream effects
- affected downstream artifacts were regenerated
- affected QA gates were re-run

Blockers:
- unrelated slides changed without request
- no revision log exists
- downstream artifacts are stale after a structural change
