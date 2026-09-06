# Drive Source Inventory — 2026-09-05

Scope: Google Drive search for lesson-builder source material and prior artifacts. Folder-name search returned ~30 npm `source-map*` package folders (synced `node_modules`) — noise, excluded. Real hits below.

## A. Prior pipeline artifacts (reuse candidates)

| Item | Drive ID | What it is | Disposition |
|---|---|---|---|
| `nclex-rn-2026/` (2026-07-20) | folder `1rpoKEi0mhf2j_V9tjI5I1WNPs3BwXQXm` | Curriculum framework build: 8 exemplar topics, 24 objectives, 120 assessment items, 48 CJ items, 8 approved OER sources. Exports: `curriculum-manifest.json` (212 KB), `qti-exemplar-bank.xml` (146 KB), `nclex-rn-2026.imscc`, `canvas-outcomes.csv`, `pathway-rules.json`. Gates: automated validation pass; portable export pass; licensed-RN review pending; public release blocked. Proprietary policy: "aliases and report parsing only; no ATI prose." | **Reuse.** A working Common Cartridge + QTI export path already exists. The LMS-agnostic output should be built on it, not from scratch. Pull the 8-source registry from `curriculum-manifest.json` next session (grep, don't read whole). |
| `harrity_master_lesson_template/` (2026-07-20, WP-HLB-20260723) | folder `1jlTAVy_Hwcn_ZMgJPNvt3M77ReNsrHvh` | JSON Schema `master-lesson-1.0.0` + validator + QA checklist. Six promotion states (template → released), fail-closed validator, approval sequence, `taxonomy_lock` already carrying NCLEX client need, Bloom, QSEN domains, AACN competencies, six NCJMM functions. IDs: `LESSON-…`, `LO-01`, `S001`, `REF-001`, `IMG001`. | **Reconcile.** This is a third lesson schema. It already has the governance and standards-crosswalk layer I added to `package-schema` v1.1 — designed two months earlier. |
| `20260610_NCC_Unit_1_…full_production.zip` | `1Oym8SVgx_ZfMlwcmny1zpVSLgAHu5LDO` | Legacy blueprint package (migrated this session) | Superseded; keep as VSM baseline. |
| `OPENSTAX_NURSING_SOURCE_AUDIT.md` (×3 copies) | `1P3d5tqdP07InIhwCjmqin9Dkr0AEj-Ao` | License audit: OpenStax Nursing = CC BY-NC-SA + no-AI-ingestion clause | Authoritative for source policy. Deduplicate. |

## B. Source material

| Item | License / status | Disposition |
|---|---|---|
| OpenStax *Pharmacology for Nurses* PDF (×4 copies), *Psychiatric-Mental Health Nursing* PDF (×4) | Per audit: CC BY-NC-SA 4.0, AI-ingestion restricted, `blockedForGeneration` | Link-only. Delete duplicate downloads. |
| Open RN *Nursing Health Promotion* Ch.4 | CC BY 4.0 (verified today) | **Registered as SRC01.** Not in Drive — lives at Pressbooks/NCBI; index in `outputs/source/`. |
| `RN Orientation Binder (1)/` — charting requirements, discharge tip sheet, acute care documentation, orientation binder PDF | Institutional onboarding documents; ownership unverified | **Not read.** Likely employer-proprietary; may contain institutional identifiers. Exclude from lesson sources unless ownership and de-identification are confirmed. Possibly relevant to the placement engine, not the lesson builder. |
| `Nursing Care of Children.tar` (13 MB) | Unknown | Not opened. Probably the legacy package source tree. |

**No other CC BY source (Open RN, other WTCS titles) was found in Drive under any name.** The CC BY backbone currently exists only as the SRC01 index.

## C. Finding: three parallel lesson schemas

| Schema | Date | Strength | Gap |
|---|---|---|---|
| Legacy blueprint CSV | Jun 2026 | Shipped 11 decks | No source, no question, no keys, visuals not in data |
| `master-lesson-1.0.0` | Jul 2026 | Governance, promotion gates, standards taxonomy, fail-closed validator | No generator; no improvement loop; no card_data |
| `package-schema` v1.1 | Sep 2026 (this session) | Working generator, migration path, traceability matrix, outcomes/improvement loop | No promotion states; AACN/QSEN slots less developed than master-lesson |

Plus the `nclex-rn-2026` curriculum manifest as a fourth data model at the framework level.

**Recommendation:** one merge session. Adopt `master-lesson` governance (promotion states, approval sequence, taxonomy_lock) as the outer envelope; keep `package-schema` slide contract, generator, and §12 improvement loop as the inner production model; bind export to the `nclex-rn-2026` CC/QTI path. Retire the other two as read-only migration sources. Until this is done, every new artifact widens the fork.

## D. Housekeeping

- Deduplicate: OpenStax PDFs (8 files → 0, per audit policy), source audit (3 → 1), blueprint CSV (2 → 1).
- Quarantine synced `node_modules` trees out of Drive search scope (they dominate title searches).
- Create one `sources/` folder with a `source_registry.json` mirroring the SRC01 index format; this is the source index we discussed in place of RAG.
