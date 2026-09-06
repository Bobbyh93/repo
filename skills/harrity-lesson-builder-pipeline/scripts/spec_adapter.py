#!/usr/bin/env python3
"""Adapter between the v1.x lesson_spec contract and the canonical renderer.

Two directions:

  spec_to_renderer(spec)   v1.1/v1.2 lesson_spec  ->  renderer spec
                           (the dict shape consumed by
                            generate_lesson_package.make_presentation)

  legacy_to_spec(legacy)   renderer/legacy spec   ->  v1.2 lesson_spec
                           (migration path for pre-v1 packages such as the
                            renderer's own --demo; output must still pass
                            validate_and_gate.py)

Design rules (see docs/WP1_MERGE_LOG.md):

* The adapter never invents clinical content. Where the renderer archetype
  needs a field the spec does not carry, the field is left empty and the
  renderer's own neutral default text applies. Every such fallback is
  recorded in the returned `notes` list so the gate can log it.
* `layout_spec.card_data` is the structured channel. For the archetypes
  defined in package-schema v1.1 (chapter_map, concept_cards, *_mcq,
  *_case, urgency_sort, match_activity, timeline) the v1.1 element shapes
  are mapped. For every renderer-native archetype, `card_data[0]` may carry
  the renderer's own content keys verbatim ("pass-through"); pass-through
  keys always win over derived values.
* Speaker notes: `speaker_script` + answer key + correct answer/rationale +
  visual notes are assembled here into `speaker_notes`; the renderer writes
  that string into the PPTX notes slide.

Usage (module):
    from spec_adapter import spec_to_renderer, legacy_to_spec

Usage (CLI):
    python spec_adapter.py --to-renderer lesson_spec.json > renderer_spec.json
    python spec_adapter.py --from-legacy legacy_spec.json > lesson_spec.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

ADAPTER_VERSION = "1.2.0"

CJM = ["recognize cues", "analyze cues", "prioritize hypotheses",
       "generate solutions", "take action", "evaluate outcomes"]

# Archetype names in the v1.1 gate that differ from the renderer's type names.
ARCHETYPE_TO_TYPE = {
    "content": "generic",
}
TYPE_TO_ARCHETYPE = {v: k for k, v in ARCHETYPE_TO_TYPE.items()}

# Renderer content keys per type. Used for pass-through detection and for the
# reverse (legacy -> spec) mapping.
RENDERER_CONTENT_KEYS: Dict[str, List[str]] = {
    "title": ["module_label", "subtitle", "goals"],
    "opening_case": ["patient_prompt", "know", "need", "task"],
    "clinical_question": ["question", "lanes"],
    "chapter_map": ["milestones"],
    "process_map": ["milestones"],
    "safety_chain": ["milestones"],
    "timeline": ["milestones"],
    "warmup_sequence": ["prompt", "items"],
    "concept_cards": ["cards", "callout"],
    "basics_grid": ["cards", "callout"],
    "debrief": ["cards", "callout"],
    "debrief_three": ["cards", "callout"],
    "teaching_point": ["cards", "warning", "callout"],
    "triad": ["cards", "callout"],
    "match_activity": ["sources", "targets"],
    "control_room": ["center", "nodes", "callout"],
    "risk_engine": ["center", "factors", "callout"],
    "exchange_model": ["left", "center", "right", "warning", "callout"],
    "compare": ["columns", "callout"],
    "checkpoint_mcq": ["question", "options", "answer", "rationale", "callout"],
    "capstone_mcq": ["scenario", "question", "options", "answer", "rationale", "callout"],
    "mini_case": ["scenario", "steps", "callout"],
    "urgency_sort": ["categories", "callout"],
    "script_template": ["steps", "callout"],
    "retrieval_check": ["questions", "callout"],
    "takeaway": ["actions", "statement"],
    "generic": ["lead", "body", "bullets", "callout"],
}

OPTION_PREFIX = re.compile(r"^\s*([A-Ha-h])\s*[.):\-]\s+")


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def _card0(slide: Dict[str, Any]) -> Dict[str, Any]:
    cards = (slide.get("layout_spec") or {}).get("card_data") or []
    return cards[0] if cards and isinstance(cards[0], dict) else {}


def _cards(slide: Dict[str, Any]) -> List[Dict[str, Any]]:
    cards = (slide.get("layout_spec") or {}).get("card_data") or []
    return [c for c in cards if isinstance(c, dict)]


def _strip_option_prefix(opt: str) -> str:
    return OPTION_PREFIX.sub("", str(opt), count=1)


def _title_body_cards(slide: Dict[str, Any], title_keys=("heading", "title", "label"),
                      body_keys=("body", "description", "event")) -> List[Dict[str, str]]:
    out = []
    for c in _cards(slide):
        title = next((c[k] for k in title_keys if c.get(k)), "")
        body = next((c[k] for k in body_keys if c.get(k)), "")
        out.append({"title": str(title), "body": str(body)})
    return out


def _bullets_as_cards(bullets: List[str], title_prefix: str = "") -> List[Dict[str, str]]:
    return [{"title": f"{title_prefix}{i + 1}" if title_prefix else "", "body": str(b)}
            for i, b in enumerate(bullets)]


def build_speaker_notes(slide: Dict[str, Any]) -> str:
    """Assemble the notes-slide text from the five-channel fields."""
    parts: List[str] = []
    script = str(slide.get("speaker_script") or "").strip()
    if script:
        parts.append(script)
    c0 = _card0(slide)
    if c0.get("correct"):
        parts.append(f"CORRECT: {c0['correct']}\nRATIONALE: {c0.get('rationale', '')}".rstrip())
    if c0.get("correct_order") and c0.get("items"):
        items = c0["items"]
        order = " → ".join(str(items[i]) for i in c0["correct_order"] if isinstance(i, int) and i < len(items))
        parts.append(f"CORRECT ORDER: {order}")
    if c0.get("pairs") and c0.get("left") and c0.get("right"):
        left, right = c0["left"], c0["right"]
        pairs = "; ".join(f"{left[a]} ↔ {right[b]}" for a, b in c0["pairs"]
                          if isinstance(a, int) and isinstance(b, int) and a < len(left) and b < len(right))
        parts.append(f"PAIRS: {pairs}")
    if slide.get("answer_key"):
        parts.append("ANSWER KEY:\n" + "\n".join(f"- {a}" for a in slide["answer_key"]))
    if slide.get("visual_notes"):
        parts.append(f"VISUAL NOTES: {slide['visual_notes']}")
    return "\n\n".join(parts)


# --------------------------------------------------------------------------
# per-archetype content derivation (spec -> renderer)
# --------------------------------------------------------------------------
def _derive_content(slide: Dict[str, Any], rtype: str, lesson: Dict[str, Any],
                    demo: bool, notes: List[str]) -> Dict[str, Any]:
    """Return renderer content keys derived from the v1.x slide fields."""
    sid = slide.get("slide_id", "?")
    bullets = [str(b) for b in (slide.get("on_slide_text") or [])]
    prompt = str(slide.get("activity_prompt") or "")
    c0 = _card0(slide)
    out: Dict[str, Any] = {}

    if rtype == "title":
        out["module_label"] = lesson.get("chapter_title") or lesson.get("unit_title") or ""
        out["subtitle"] = "  ·  ".join(x for x in [lesson.get("course_code", ""), lesson.get("unit_title", ""),
                                                   lesson.get("chapter_title", "")] if x)
        if bullets:
            out["goals"] = bullets
        else:
            notes.append(f"{sid}: title goals not in spec; renderer default goal text used")
        if demo:
            out["subtitle"] = "DEMO — illustrative content; does not imply course-source support. " + out["subtitle"]

    elif rtype == "opening_case":
        out["patient_prompt"] = c0.get("presentation", " ".join(bullets))
        out["know"] = list(c0.get("cues") or [])
        out["need"] = bullets if c0.get("presentation") else []
        out["task"] = c0.get("prompt") or prompt
        if not out["task"]:
            notes.append(f"{sid}: opening_case task empty; renderer default task text used")

    elif rtype == "mini_case":
        out["scenario"] = c0.get("presentation", " ".join(bullets))
        steps = []
        if c0.get("cues"):
            steps.append({"title": "cues", "body": "\n".join(f"- {c}" for c in c0["cues"])})
        if c0.get("prompt") or prompt:
            steps.append({"title": "your task", "body": c0.get("prompt") or prompt})
        if bullets and c0.get("presentation"):
            steps.append({"title": "consider", "body": "\n".join(f"- {b}" for b in bullets)})
        out["steps"] = steps
        if not steps:
            notes.append(f"{sid}: mini_case has no cues/prompt; card grid empty")

    elif rtype == "clinical_question":
        out["question"] = lesson.get("organizing_clinical_question", "")
        # lanes: v1.1 chapter_map-style card_data [{lane, nodes}] or plain lane names
        lanes = []
        for c in _cards(slide):
            if c.get("lane"):
                lanes.append({"label": c["lane"], "description": "; ".join(c.get("nodes") or [])})
        if not lanes:
            lanes = [{"label": ln, "description": ""} for ln in lesson.get("concept_lanes") or []]
        out["lanes"] = lanes

    elif rtype in {"chapter_map", "process_map", "safety_chain"}:
        ms = []
        for c in _cards(slide):
            if c.get("lane"):
                ms.append({"label": c["lane"], "body": " → ".join(str(n) for n in (c.get("nodes") or []))})
            elif c.get("label"):
                ms.append({"label": c["label"], "body": c.get("body") or c.get("event") or ""})
        if not ms and rtype == "chapter_map":
            ms = [{"label": ln, "body": ""} for ln in lesson.get("concept_lanes") or []]
            notes.append(f"{sid}: chapter_map without card_data; lanes rendered without nodes")
        if not ms and bullets:
            ms = [{"label": str(i + 1), "body": b} for i, b in enumerate(bullets)]
        out["milestones"] = ms

    elif rtype == "timeline":
        out["milestones"] = [{"label": c.get("label", ""), "body": c.get("event") or c.get("body") or ""}
                             for c in _cards(slide)] or [{"label": str(i + 1), "body": b} for i, b in enumerate(bullets)]

    elif rtype == "warmup_sequence":
        out["prompt"] = prompt
        out["items"] = list(c0.get("items") or bullets)

    elif rtype in {"concept_cards", "basics_grid", "debrief", "debrief_three", "triad", "teaching_point"}:
        cards = _title_body_cards(slide)
        if not cards and bullets:
            cards = _bullets_as_cards(bullets)
            notes.append(f"{sid}: {rtype} without card_data; bullets rendered as untitled cards")
        out["cards"] = cards
        # the renderer's default callout is generic pipeline text; prefer the slide's own words
        if prompt:
            out["callout"] = prompt
        elif slide.get("learning_objective"):
            out["callout"] = slide["learning_objective"]
        if rtype == "teaching_point" and slide.get("answer_key"):
            out["warning"] = "; ".join(str(a) for a in slide["answer_key"])

    elif rtype == "match_activity":
        out["sources"] = list(c0.get("left") or [])
        out["targets"] = list(c0.get("right") or [])
        if not out["sources"]:
            notes.append(f"{sid}: match_activity without left/right; empty grid")

    elif rtype in {"checkpoint_mcq", "capstone_mcq"}:
        out["question"] = c0.get("stem") or prompt
        out["options"] = [_strip_option_prefix(o) for o in (c0.get("options") or [])]
        out["answer"] = c0.get("correct", "")
        out["rationale"] = c0.get("rationale", "")
        if rtype == "capstone_mcq":
            out["scenario"] = c0.get("scenario") or " ".join(bullets)
        if not out["options"]:
            notes.append(f"{sid}: {rtype} without options")

    elif rtype == "urgency_sort":
        if c0.get("categories"):
            out["categories"] = c0["categories"]
        else:
            items = list(c0.get("items") or bullets)
            out["categories"] = [{"title": prompt or "sort by urgency", "items": items}]
            notes.append(f"{sid}: urgency_sort v1.1 items rendered as one unsorted list; correct_order in notes")

    elif rtype == "control_room":
        out["center"] = c0.get("center") or slide.get("learning_objective", "")
        out["nodes"] = c0.get("nodes") or _bullets_as_cards(bullets)

    elif rtype == "risk_engine":
        out["center"] = c0.get("center") or slide.get("learning_objective", "")
        out["factors"] = c0.get("factors") or _bullets_as_cards(bullets)

    elif rtype == "exchange_model":
        for k in ("left", "center", "right"):
            if c0.get(k):
                out[k] = c0[k]
        if not out:
            notes.append(f"{sid}: exchange_model without left/center/right; renderer placeholders used")

    elif rtype == "compare":
        if c0.get("columns"):
            out["columns"] = c0["columns"]
        else:
            notes.append(f"{sid}: compare without columns; nothing to render in body")
            out["columns"] = []

    elif rtype == "script_template":
        out["steps"] = c0.get("steps") or [{"title": f"step {i + 1}", "body": b} for i, b in enumerate(bullets)]

    elif rtype == "retrieval_check":
        out["questions"] = list(c0.get("questions") or bullets)

    elif rtype == "takeaway":
        cards = _title_body_cards(slide)
        out["actions"] = cards or [{"title": b, "body": ""} for b in bullets]
        if slide.get("learning_objective"):
            out["statement"] = slide["learning_objective"]
        elif not bullets:
            notes.append(f"{sid}: takeaway without actions or objective; renderer defaults used")

    else:  # generic / content
        out["lead"] = slide.get("learning_objective") or slide.get("slide_title", "")
        out["bullets"] = bullets
        if prompt:
            out["callout"] = prompt

    if prompt and "callout" not in out and rtype not in {"title", "generic"}:
        out["callout"] = prompt
    return out


# --------------------------------------------------------------------------
# spec -> renderer
# --------------------------------------------------------------------------
def slide_to_renderer(slide: Dict[str, Any], lesson: Dict[str, Any], demo: bool = False,
                      notes: Optional[List[str]] = None) -> Dict[str, Any]:
    notes = notes if notes is not None else []
    arch = str(slide.get("slide_archetype") or "content")
    rtype = ARCHETYPE_TO_TYPE.get(arch, arch)
    if rtype not in RENDERER_CONTENT_KEYS:
        notes.append(f"{slide.get('slide_id')}: archetype '{arch}' unknown to renderer; rendered as generic")
        rtype = "generic"
    rs: Dict[str, Any] = {
        "type": rtype,
        "slide_id": slide.get("slide_id", ""),
        "title": slide.get("slide_title", ""),
        "module_label": slide.get("lesson_section", ""),
        "concept_lane": slide.get("concept_lane", ""),
        "cjm_steps": list(slide.get("cjm_functions") or []),
        "concepts": [slide["concept_lane"]] if slide.get("concept_lane") else [],
        "learner_task": slide.get("activity_prompt", ""),
        "remediation_target": (slide.get("remediation_target") or {}).get("cjm_function", ""),
        "source_status": slide.get("evidence_status", ""),
        "evidence_status": slide.get("evidence_status", ""),
        "source_refs": list(slide.get("source_refs") or []),
        "speaker_notes": build_speaker_notes(slide),
        "learning_objective": slide.get("learning_objective", ""),
        "answer": ", ".join(str(a) for a in (slide.get("answer_key") or [])),
    }
    if rtype == "title":
        rs["title"] = lesson.get("lesson_title") or rs["title"]
        if demo:
            rs["title"] = "DEMO — " + rs["title"]
    derived = _derive_content(slide, rtype, lesson, demo, notes)
    # pass-through: renderer-native keys in card_data[0] override derived values
    c0 = _card0(slide)
    native = {k: c0[k] for k in RENDERER_CONTENT_KEYS.get(rtype, []) if k in c0}
    if native:
        notes.append(f"{slide.get('slide_id')}: pass-through keys {sorted(native)}")
    derived.update(native)
    rs["content"] = derived
    return rs


def spec_to_renderer(spec: Dict[str, Any], demo: bool = False) -> Tuple[Dict[str, Any], List[str]]:
    """Return (renderer_spec, notes)."""
    notes: List[str] = []
    L = spec.get("lesson") or {}
    rc = spec.get("runtime_config") or {}
    coverage = ""
    for src in spec.get("sources") or []:
        coverage = src.get("coverage_status") or coverage
    active = sorted((s for s in spec.get("slides") or [] if not s.get("retired")),
                    key=lambda s: int(s.get("slide_number") or 0))
    lanes = []
    # lane descriptions come from a chapter_map slide when one exists
    lane_desc: Dict[str, str] = {}
    for s in active:
        if s.get("slide_archetype") == "chapter_map":
            for c in _cards(s):
                if c.get("lane"):
                    lane_desc[c["lane"]] = "; ".join(str(n) for n in (c.get("nodes") or []))
    for ln in L.get("concept_lanes") or []:
        lanes.append({"label": ln, "description": lane_desc.get(ln, "")})
    rspec: Dict[str, Any] = {
        "adapter_version": ADAPTER_VERSION,
        "metadata": {
            "course": L.get("course_code", ""),
            "unit": L.get("unit_title", ""),
            "chapter": L.get("chapter_title", ""),
            "topic": L.get("lesson_title", ""),
            "audience": L.get("audience", ""),
            "duration_minutes": L.get("target_duration_minutes", 0),
            "source_status": coverage or "provisional",
            "package_id": (rc.get("runtime") or {}).get("package_id", ""),
        },
        "clinical_question": L.get("organizing_clinical_question", ""),
        "concept_lanes": lanes,
        "slides": [slide_to_renderer(s, L, demo, notes) for s in active],
        "quiz_analysis": [
            {"objective": r.get("miss_pattern", ""), "score_percent": "n/a",
             "miss_type": r.get("likely_misconception", ""), "cjm_step": r.get("failed_operation", ""),
             "remediation": r.get("one_slide_fix", "")}
            for r in spec.get("remediation_map") or []
        ],
        "package_status": (spec.get("qa") or {}).get("release_status", "draft-only"),
        "runtime_config": rc,
    }
    return rspec, notes


# --------------------------------------------------------------------------
# legacy/renderer spec -> v1.2 lesson_spec
# --------------------------------------------------------------------------
def _legacy_slide(ls: Dict[str, Any], num: int, lanes: List[str]) -> Dict[str, Any]:
    rtype = str(ls.get("type") or "generic").strip().lower().replace(" ", "_")
    arch = TYPE_TO_ARCHETYPE.get(rtype, rtype)
    content = dict(ls.get("content") or {})
    for k in RENDERER_CONTENT_KEYS.get(rtype, []):
        if k in ls and k not in content:
            content[k] = ls[k]
    cjm = ls.get("cjm_steps") or []
    if isinstance(cjm, str):
        cjm = [cjm]
    cjm = [c for c in cjm if c in CJM]
    concepts = ls.get("concepts") or []
    lane = ls.get("concept_lane") or (concepts[0] if concepts and concepts[0] in lanes else "cross-lane")
    bullets: List[str] = []
    if content.get("bullets"):
        bullets = [str(b) for b in content["bullets"]]
    elif content.get("questions"):
        bullets = [str(q) for q in content["questions"]]
    elif content.get("items"):
        bullets = [str(i) for i in content["items"]]
    sid = ls.get("slide_id") or f"S{num:02d}"
    ev = ls.get("source_status") or ls.get("evidence_status") or "illustrative-example"
    return {
        "slide_id": sid, "slide_number": num, "slide_title": str(ls.get("title") or f"slide {num}"),
        "slide_archetype": arch, "lesson_section": str(ls.get("module_label") or ""),
        "concept_lane": lane, "source_refs": list(ls.get("source_refs") or []), "evidence_status": ev,
        "cjm_functions": cjm, "nursing_action_category": "",
        "learning_objective": str(ls.get("learning_objective") or ls.get("learner_task") or ""),
        "on_slide_text": bullets, "activity_prompt": str(ls.get("learner_task") or ""),
        "answer_key": [str(content["answer"])] if content.get("answer") else [],
        "visual_notes": "", "speaker_script": str(ls.get("speaker_notes") or ""), "tts_text": "",
        "target_duration_sec": int(ls.get("target_duration_sec") or 60), "audio_duration_sec": None,
        "auto_advance": False,
        "layout_spec": {"archetype": arch, "density_budget": {"max_bullets": 6, "max_words_per_bullet": 14},
                        "regions": ["header", "body", "footer"], "card_data": [content] if content else []},
        "allow_overlap": False, "qa_status": "unreviewed", "qa_notes": "",
        "remediation_target": {"concept_lane": lane, "cjm_function": str(ls.get("remediation_target") or (cjm[0] if cjm else "")),
                               "misconception": "", "fix_type": ""},
        "audio_filename": "", "course_objective_id": "", "standards_refs": [],
        "migration": {"from": "renderer-legacy", "legacy_type": rtype},
    }


def legacy_to_spec(legacy: Dict[str, Any]) -> Dict[str, Any]:
    md = legacy.get("metadata") or {}
    lanes_raw = legacy.get("concept_lanes") or []
    lanes = [ln.get("label", "") if isinstance(ln, dict) else str(ln) for ln in lanes_raw]
    lanes = [ln for ln in lanes if ln]
    slides = [_legacy_slide(ls, i, lanes) for i, ls in enumerate(legacy.get("slides") or [], start=1)]
    src_status = md.get("source_status", "provisional")
    return {
        "schema_version": "1.2",
        "runtime_config": legacy.get("runtime_config") or {
            "runtime": {"run_date_yyyymmdd": date.today().strftime("%Y%m%d"),
                        "package_id": md.get("package_id", "LEGACY"), "build_mode": "full_production",
                        "deployment_mode": "hybrid", "rebuild_scope": "full", "output_root": "."},
            "outputs": {"filename_pattern": ""}},
        "lesson": {
            "course_code": md.get("course", ""), "program_level": "", "audience": md.get("audience", ""),
            "unit_title": md.get("unit", "") or md.get("chapter", ""), "chapter_id": "",
            "chapter_title": md.get("chapter", ""), "lesson_title": md.get("topic", ""), "concept": "",
            "exemplars": [], "clinical_domain": "", "source_family": "", "source_anchor": "", "page_range": "",
            "organizing_clinical_question": legacy.get("clinical_question", ""), "opening_patient_question": "",
            "concept_lanes": lanes, "target_duration_minutes": md.get("duration_minutes", 0),
            "program_outcomes": [], "course_objectives": [],
        },
        "sources": [{"source_id": "SRC01", "title": "legacy package source (not attached)", "kind": "external",
                     "license": "restricted", "locator": "n/a",
                     "coverage_status": "absent" if src_status != "source-grounded" else "confirmed"}],
        "taxonomy": {"glossary": [], "concept_tags": [], "outcome_tags": [], "nclex_client_needs": [],
                     "cjm_functions": CJM, "proposed_new_tags": [], "frameworks": []},
        "governance": {"promotion_state": "intake_complete", "approvals": {}, "taxonomy_lock": {"status": "unlocked"}},
        "slides": slides,
        "assessment_items": [],
        "remediation_map": [
            {"miss_pattern": q.get("objective", ""), "failed_operation": q.get("cjm_step", ""), "map_location": "",
             "concept_lane": "", "likely_misconception": q.get("miss_type", ""), "one_slide_fix": q.get("remediation", ""),
             "active_learning_task": "", "retrieval_item": "", "improvement_evidence": q.get("evidence", "")}
            for q in legacy.get("quiz_analysis") or []],
        "qa": {"release_status": legacy.get("package_status", "draft-only"), "gates_passed": [], "defects": [],
               "cjm_coverage_rationale": ""},
        "revision_log": legacy.get("revision_log") or [],
        "outcomes": {}, "improvement_log": [],
    }


# --------------------------------------------------------------------------
def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--to-renderer", metavar="LESSON_SPEC")
    g.add_argument("--from-legacy", metavar="LEGACY_SPEC")
    ap.add_argument("--demo", action="store_true", help="label output as demo when converting to renderer")
    a = ap.parse_args(argv)
    if a.to_renderer:
        spec = json.load(open(a.to_renderer, encoding="utf-8"))
        out, notes = spec_to_renderer(spec, a.demo)
        for n in notes:
            print(f"[adapter] {n}", file=sys.stderr)
    else:
        out = legacy_to_spec(json.load(open(a.from_legacy, encoding="utf-8")))
    json.dump(out, sys.stdout, indent=2, ensure_ascii=False)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
