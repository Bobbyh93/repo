# Harrity Lesson Builder Pipeline v0.3.0

This is a Skill Builder-ready replacement/update package for `harrity-lesson-builder-pipeline`.

## Main update

The skill now defaults to the student's actual learner-facing content experience, not instructor meta-planning.

## Install/update contents

- `SKILL.md`
- `agents/openai.yaml`
- references for pipeline, slide grammar, QA gates, and student reception review
- CSV templates for slide maps, item maps, QA logs, and assessment blueprints
- JSON schemas for package manifest and student reception review
- validation script for generated lesson packages
- changelog and package manifest

## Key controls

1. Learner-facing deck is primary by default.
2. Instructor guidance belongs in speaker notes or secondary files.
3. Every major concept needs an exam anchor.
4. Questions require rationales.
5. QA includes a student-reception review.
6. Artifact claims must match files that actually exist.
