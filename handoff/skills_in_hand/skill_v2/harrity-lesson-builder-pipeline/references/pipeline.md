# Pipeline Reference

## Default sequence

1. Source ingest
2. Concept clustering
3. Learner profile and exam-readiness goal
4. Concept-to-assessment blueprint
5. Running case selection
6. Learner-facing content sequence
7. Deck or deck manifest
8. Speaker notes
9. Student guided notes
10. Item/rationale map
11. QA gates
12. Preview/render check
13. Package manifest

## Stage state values

- pending
- running
- pass
- conditional
- blocked
- not_run

## Critical rule

The learner-facing deck is the primary product unless the user explicitly requests a different output mode.
