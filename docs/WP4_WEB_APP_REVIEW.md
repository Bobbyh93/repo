# WP-4 — Web app review: rebuild vs redesign

Date: 2026-09-06 · Scope: read-only review of `Bobbyh93/codex_repo_2026` (Render service `nursestudy-lesson-builder`) against the 3-screen target flow: **source in → review/approve → download**.

## Recommendation

**Redesign the surface, rebuild the lesson data path.** Keep the app's shell (auth, Render deploy, Postgres, knowledge-base upload, source registry) and replace the lesson generation/export path with the file-based pipeline merged in WP-1. Do not try to retrofit the 26-field slide contract onto the existing `lesson_slides` table; put `lesson_spec.json` in `lesson_package_artifacts` as the package of record and let the gate produce everything else.

Reasoning in one line each:

- The app has no PPTX output, no `lesson_spec`, no evidence status, no concept lanes, no card data. The generation path would be replaced, not adapted.
- The app *does* have the expensive parts: magic-link auth, admin roles, Render deploy config, a working document upload + chunking pipeline, a source registry with approval/citation policy, and a promotion state (`releaseStage`) with an audit table.
- 407 API routes and 63 page files (17 of them imported but unrouted) is the cost of the Replit-era growth. A 3-screen flow needs about a dozen routes.

## What exists (facts)

| Area | Finding |
|---|---|
| Stack | Express + React/Vite (wouter) + Drizzle/Postgres; Python scripts are ops-only, never imported by the app |
| Routes | ~40 registered client routes; lesson-related: `/admin/lesson-builder` (4-tab page, 4,455 lines), `/admin/topic-production`, `/admin/knowledge-base`, `/admin/curriculum-catalog`, `/curriculum/*`, `/lessons/:id` (learner runtime) |
| API | 407 registrations in 13 files; `lesson-builder-routes.ts` alone is 14,234 lines and 99 routes |
| Lesson generation | `POST /api/admin/lesson-builder/generate` → RAG over knowledge base → template slides → optional OpenAI overlay (`gpt-4o-mini` default) → DB rows → QA → "harrity" contract validation |
| Output | zip of JSON/CSV/MD artifacts from `lesson_package_artifacts`; export is hard-blocked (HTTP 400) when any control-plane gate fails; **no PPTX, DOCX or PDF** |
| CC/QTI | only for the 8 hard-coded NCLEX exemplars; cannot read a DB package (see WP-0) |
| Replit | same codebase; Render/GitHub is canonical per `PRODUCT_CONSOLIDATION_LOG.md` |
| Duplication | `scripts/lesson-builder-preview-server.mjs` (6,000+ lines) duplicates large blocks of the route file line-for-line |

## Gap list vs the 3-screen flow

| Screen | Closest existing | Missing |
|---|---|---|
| 1 Source in | `/admin/knowledge-base` upload + `/admin/lesson-builder` sources tab | one entry point (today: upload in one screen, attach in another, 7 import endpoints); inline ingest status; license capture per source (`license`, `coverage_status` as in `sources[]` v1.2) |
| 2 Review/approve | `/admin/lesson-builder` review tab + `/admin/topic-production` + learner preview checklist | one approve gate (today: 8 overlapping decision verbs across ~58 endpoints); slide-level approve/reject state; source-excerpt vs claim view; `qa_log` display; the seven master-lesson approvals |
| 3 Download | `packages/:id/export` | PPTX + facilitator guide + handout + manifest (the WP-1 package); `.imscc` (WP-3); non-Canvas targets; a draft download when blocked (today: 400) |

## Estimate

| Option | Work | Rough size |
|---|---|---|
| A. Redesign surface, rebuild data path (recommended) | 3 new pages, ~12 routes; a `packages` table holding `lesson_spec.json` + gate outputs as artifacts; Python gate invoked as a subprocess or via a small worker; keep auth, upload, source registry | 3–5 build days after WP-2/WP-3 |
| B. Retrofit v1.2 contract into existing tables and route file | schema migration on 4 tables; edit a 14k-line route file; keep 8 decision verbs | not recommended; larger and leaves the duplication |
| C. Greenfield app | rebuild auth, upload, deploy | only if the Replit-era code is abandoned entirely; more than A |

## Hygiene findings to act on regardless (in that repo, not this one)

- 45 Playwright screenshot PNGs at repo root (~5 MB) and a `screenshots/` dir.
- Six committed OpenStax PDFs in `attached_assets/` that the repo's own `OPENSTAX_NURSING_SOURCE_AUDIT.md` says are CC BY-NC-SA and must not be ingested; two are duplicates.
- Files that look like real student assessment reports (`Cohort 5 exit exam_*.pdf`, `assessments_individual_report (1|2|3)_*.pdf`, `test_export.csv`). Confirm synthetic or remove — this intersects the "no learner identifiers" constraint.
- `replit.md` documents default admin credentials; the claim that the hash was invalidated was not verified.
- No committed secrets found by pattern scan (`sk-`, `AKIA`, `ghp_`, `SG.`).

## Not verified

Live behaviour of the Render service; whether the app builds cleanly today; the OpenStax license contradiction (manifest says CC BY 4.0, audit says CC BY-NC-SA).
