#!/usr/bin/env python3
"""Migrate a legacy (2026-06) blueprint package chapter into lesson_spec.json v1.0.

Usage:
    python migrate_blueprint_to_spec.py --package DIR --chapter N --out lesson_spec.json

Every mapping decision is logged to <out>.migration_log.md. Nothing is inferred
silently: lane and CJM assignments derived from archetype are marked `inferred`,
and evidence_status is set from what the legacy source inventory actually claims.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from datetime import date
from pathlib import Path

from pptx import Presentation

CJM = ["recognize cues", "analyze cues", "prioritize hypotheses",
       "generate solutions", "take action", "evaluate outcomes"]
LANES = ["recognize", "interpret", "prioritize", "act", "evaluate"]

# legacy layout_archetype -> (new archetype, lane, cjm functions)
ARCH_MAP = {
    "title":             ("title",           "cross-lane", []),
    "concept":           ("content",         "interpret",  ["analyze cues"]),
    "teaching":          ("content",         "act",        ["take action"]),
    "teachback":         ("content",         "act",        ["take action", "evaluate outcomes"]),
    "assessment":        ("content",         "recognize",  ["recognize cues"]),
    "screening":         ("content",         "recognize",  ["recognize cues"]),
    "growth":            ("content",         "interpret",  ["analyze cues"]),
    "development":       ("content",         "interpret",  ["analyze cues"]),
    "nutrition":         ("content",         "interpret",  ["analyze cues"]),
    "sleep":             ("content",         "interpret",  ["analyze cues"]),
    "play":              ("content",         "interpret",  ["analyze cues"]),
    "pain":              ("content",         "interpret",  ["analyze cues"]),
    "priority":          ("content",         "prioritize", ["prioritize hypotheses"]),
    "pitfalls":          ("content",         "prioritize", ["prioritize hypotheses"]),
    "actions":           ("content",         "act",        ["generate solutions", "take action"]),
    "communication":     ("content",         "act",        ["take action"]),
    "policy":            ("content",         "act",        ["take action"]),
    "interprofessional": ("content",         "act",        ["generate solutions"]),
    "documentation":     ("content",         "act",        ["take action"]),
    "case":              ("mini_case",       "prioritize", ["prioritize hypotheses", "generate solutions"]),
    "rationale":         ("content",         "evaluate",   ["evaluate outcomes"]),
    "evaluation":        ("content",         "evaluate",   ["evaluate outcomes"]),
    "nclex":             ("retrieval_check", "evaluate",   ["evaluate outcomes"]),
    "summary":           ("takeaway",        "cross-lane", []),
    "template":          ("content",         "cross-lane", []),
    "process":           ("content",         "act",        ["take action"]),
}


def split_bullets(s: str) -> list[str]:
    return [b.strip() for b in re.split(r";\s*", s or "") if b.strip()]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--package", type=Path, required=True)
    ap.add_argument("--chapter", type=int, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    pkg = a.package
    log: list[str] = []

    manifest = json.loads(next(pkg.glob("*_package_manifest.json")).read_text())
    ch = next(c for c in manifest["chapters"] if c["chapter_number"] == a.chapter)
    bp = list(csv.DictReader(next(pkg.glob("manifests/*_slide_blueprint.csv")).open(encoding="utf-8")))
    tag = f"CH{a.chapter:03d}_"
    rows = sorted((r for r in bp if tag in r["slide_id"]), key=lambda r: int(r["slide_number"]))
    src_inv = list(csv.DictReader(next(pkg.glob("manifests/*_source_inventory.csv")).open(encoding="utf-8")))
    src_row = next(r for r in src_inv if int(r["chapter_number"]) == a.chapter)
    legacy_qa = [r for r in csv.DictReader(next(pkg.glob("qa/*_QA_log.csv")).open(encoding="utf-8"))
                 if r["chapter_number"].strip() in {str(a.chapter), "ALL"}]

    deck = pkg / "decks" / Path(ch["pptx_path"]).name
    prs = Presentation(deck)
    notes = [s.notes_slide.notes_text_frame.text if s.has_notes_slide else "" for s in prs.slides]
    log.append(f"- Deck `{deck.name}`: {len(prs.slides)} slides; blueprint rows for chapter: {len(rows)}. "
               + ("Counts match." if len(prs.slides) == len(rows) else "**COUNT MISMATCH** — notes aligned by slide_number."))

    # Evidence status: the legacy inventory states source text was not attached at build time.
    ev = "needs-verification"
    log.append(f"- Legacy source_status `{ch['source_status']}` with inventory assumption: \"{src_row['assumptions'][:120]}…\". "
               f"Mapped to `evidence_status: {ev}` on every clinical slide because no source text was attached at build. "
               "`source-aligned` would require resolvable source_refs, which do not exist.")
    log.append("- Lane and CJM assignments derived from legacy `layout_archetype` via a fixed table (ARCH_MAP). "
               "These are **inferred**, not sourced; every migrated slide carries `migration.lane_inferred: true`.")
    log.append("- `activity_statement` is a slide directive in the legacy schema (e.g. 'Set the chapter lens.'), not a learner task. "
               "Mapped to `activity_prompt` only for `case` archetype; elsewhere preserved in `visual_notes`. "
               "No legacy slide has an answer key; expect a `major` on the case slide.")
    log.append("- Legacy IDs `NCOC_RN2019_CH001_S0NN` renumbered to `SNN` by slide_number (legacy S020 → S18). "
               "Original kept in `legacy_slide_id`.")

    slides = []
    unknown = set()
    for i, r in enumerate(rows):
        la = r["layout_archetype"]
        arch, lane, cjm = ARCH_MAP.get(la, ("content", "cross-lane", []))
        if la not in ARCH_MAP:
            unknown.add(la)
        n = int(r["slide_number"])
        script = notes[n - 1] if n - 1 < len(notes) else ""
        is_case = la == "case"
        bullets = split_bullets(r["on_slide_content"])
        slides.append({
            "slide_id": f"S{n:02d}", "slide_number": n, "slide_title": r["slide_title"],
            "slide_archetype": arch, "lesson_section": r["framework_section"], "concept_lane": lane,
            "source_refs": [], "evidence_status": ev if arch not in {"title", "takeaway"} else "instructor-added",
            "cjm_functions": cjm, "nursing_action_category": la,
            "learning_objective": r["learning_objective"], "on_slide_text": bullets,
            "activity_prompt": r["activity_statement"] if is_case else "",
            "answer_key": [],
            "visual_notes": "" if is_case else f"legacy activity_statement: {r['activity_statement']}",
            "speaker_script": script, "tts_text": "",
            "target_duration_sec": max(20, round(len(script.split()) / 140 * 60)),
            "audio_duration_sec": None, "auto_advance": False,
            "layout_spec": {"archetype": arch, "density_budget": {"max_bullets": 6, "max_words_per_bullet": 14},
                            "regions": ["header", "body", "footer"], "card_data": []},
            "allow_overlap": False,
            "qa_status": "unreviewed", "qa_notes": r["qa_notes"],
            "remediation_target": {"concept_lane": lane, "cjm_function": cjm[0] if cjm else "", "misconception": "", "fix_type": ""},
            "audio_filename": "",
            "legacy_slide_id": r["slide_id"], "legacy_archetype": la,
            "migration": {"lane_inferred": True, "cjm_inferred": True},
        })
    if unknown:
        log.append(f"- Legacy archetypes with no mapping (rendered as content): {sorted(unknown)}")

    spec = {
        "schema_version": "1.0",
        "runtime_config": {
            "runtime": {"run_date_yyyymmdd": date.today().strftime("%Y%m%d"),
                        "package_id": f"MIGRATION_{manifest['package_id']}_CH{a.chapter:02d}",
                        "build_mode": "revision", "deployment_mode": "hybrid",
                        "rebuild_scope": "full", "output_root": "."},
            "outputs": {"filename_pattern": "{{runtime.run_date_yyyymmdd}}_{{lesson.course_code}}_{{lesson.chapter_title}}_Part_{{deck.part_number}}.pptx"},
        },
        "lesson": {
            "course_code": "NCC", "program_level": "RN", "audience": manifest["program"],
            "unit_title": manifest["unit_title"], "chapter_id": str(a.chapter), "chapter_title": ch["chapter_title"],
            "lesson_title": ch["chapter_title"], "concept": ch["chapter_title"], "exemplars": [],
            "clinical_domain": "pediatrics", "source_family": manifest["program"],
            "source_anchor": ch["section_title"], "page_range": f"{ch['source_page_start']}-{ch['source_page_end']}",
            "organizing_clinical_question": "",   # legacy package has no organizing question
            "opening_patient_question": "", "concept_lanes": LANES, "target_duration_minutes": 0,
        },
        "sources": [{
            "source_id": "SRC01", "title": manifest["program"], "kind": "authoritative", "license": "restricted",
            "locator": f"pp. {ch['source_page_start']}-{ch['source_page_end']}", "coverage_status": "absent",
        }],
        "taxonomy": {"glossary": [], "concept_tags": sorted({t.strip() for r in rows for t in r["concept_tags"].split(";") if t.strip()}),
                     "outcome_tags": [], "nclex_client_needs": [], "cjm_functions": CJM, "proposed_new_tags": []},
        "slides": slides, "assessment_items": [], "remediation_map": [],
        "qa": {"release_status": "draft-only", "gates_passed": [],
               "defects": [{"severity": r["severity"], "slide_id": "-", "note": f"[legacy {r['check_area']}] {r['finding']}"} for r in legacy_qa],
               "cjm_coverage_rationale": ""},
        "revision_log": [{"revision_id": "R00", "date": date.today().isoformat(), "changed_ids": ["*"],
                          "previous_summary": "legacy blueprint CSV + notes", "new_summary": "lesson_spec v1.0",
                          "reason": "schema migration", "downstream_effects": ["all"]}],
    }
    log.append("- `organizing_clinical_question` is empty: the legacy package has no organizing question or concept lanes. "
               "Lanes set to the safety/triage default from SKILL.md. Expect a **blocker** from the generator on the empty question.")
    log.append(f"- Legacy source registered as `SRC01`, license `restricted`, coverage `absent`. Legacy QA rows ({len(legacy_qa)}) carried into `qa.defects` with a `[legacy …]` prefix.")

    a.out.write_text(json.dumps(spec, indent=2, ensure_ascii=False), encoding="utf-8")
    Path(str(a.out) + ".migration_log.md").write_text(
        f"# Migration log — chapter {a.chapter}: {ch['chapter_title']}\n\n" + "\n".join(log) + "\n", encoding="utf-8")
    print(f"wrote {a.out} ({len(slides)} slides)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
