#!/usr/bin/env python3
"""Harrity Lesson Builder — gate + package writer (schema v1.2).

    python validate_and_gate.py --spec lesson_spec.json --outdir OUT
    python validate_and_gate.py --demo --outdir OUT
    python validate_and_gate.py --legacy renderer_spec.json --outdir OUT

Pipeline:  lesson_spec (v1.1/v1.2)
             -> validate_spec()            26-field slide contract, evidence/source
                                           enforcement, traceability, governance
             -> spec_adapter.spec_to_renderer()
             -> generate_lesson_package.make_presentation()   canonical renderer
             -> package writers            guides, assessment map, traceability
                                           matrix, manifest, qa_log
             -> _DRAFT stamping when any blocker exists

The generator never invents content. It renders what the spec carries,
logs every defect it detects, and stamps outputs _DRAFT when a blocker exists.

History: this file is the Stage 9 generator of 2026-09-05 (package-schema
v1.1) with its private PPTX drawing code removed in the WP-1 merge. The
canonical renderer is generate_lesson_package.py in this directory.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent))
import export_lms  # noqa: E402  Common Cartridge / QTI 1.2 / HTML / PDF
import generate_lesson_package as renderer  # noqa: E402  canonical renderer
import spec_adapter  # noqa: E402

# --------------------------------------------------------------------------
# Constants
# --------------------------------------------------------------------------
SCHEMA_VERSION = "1.2"
ACCEPTED_SCHEMA_VERSIONS = {"1.0", "1.1", "1.2"}
SLIDE_ID_RE = re.compile(r"^S\d{2}[A-Z]?$")
EVIDENCE = {"source-grounded", "source-aligned", "inferred", "illustrative-example",
            "instructor-added", "provisional", "unresolved", "needs-verification"}
CJM = ["recognize cues", "analyze cues", "prioritize hypotheses",
       "generate solutions", "take action", "evaluate outcomes"]
# v1.1 archetype set ∪ every renderer-native type. "content" is the v1.1 name
# for the renderer's "generic". Nothing from either side is dropped.
V11_ARCHETYPES = {"title", "opening_case", "clinical_question", "chapter_map", "warmup_sequence",
                  "concept_cards", "match_activity", "debrief", "timeline", "checkpoint_mcq",
                  "mini_case", "urgency_sort", "capstone_mcq", "retrieval_check", "takeaway", "content"}
ARCHETYPES = V11_ARCHETYPES | set(renderer.RENDERERS.keys())
NO_SCRIPT_ARCHETYPES = {"title", "takeaway", "chapter_map", "clinical_question"}
REQUIRED_SLIDE_KEYS = ["slide_id", "slide_number", "slide_title", "slide_archetype", "lesson_section",
                       "concept_lane", "source_refs", "evidence_status", "cjm_functions",
                       "nursing_action_category", "learning_objective", "on_slide_text",
                       "activity_prompt", "answer_key", "visual_notes", "speaker_script", "tts_text",
                       "target_duration_sec", "audio_duration_sec", "auto_advance", "layout_spec",
                       "allow_overlap", "qa_status", "qa_notes", "remediation_target", "audio_filename"]
RELEASE_STATES = {"release-ready", "faculty-review-needed", "draft-only", "blocked"}
# Gate vocabulary. A recorded gate outside this set is almost always a typo, and a
# typo silently satisfies nothing while the operator believes QA is on record.
KNOWN_GATES = {"runtime", "source", "taxonomy", "blueprint", "cjm_coverage", "outline", "script",
               "timing", "layout", "deck_render", "package_manifest",
               "visual_qa", "visual_qa_ai", "lms_import", "source_verification"}
# A release-ready claim must be backed by a human having looked at the rendered deck.
# A lesson may require more (e.g. lms_import) via qa.required_gates.
DEFAULT_REQUIRED_GATES = ["visual_qa"]
# master-lesson 1.0.0 envelope (references/master_lesson/master_lesson_schema.json)
PROMOTION_STATES = ["template", "intake_complete", "faculty_review", "production_ready", "release_ready", "released"]
APPROVAL_KEYS = ["source_approved", "taxonomy_approved", "objectives_approved", "outline_approved",
                 "script_approved", "faculty_approved", "release_approved"]
PRODUCTION_APPROVALS = APPROVAL_KEYS[:5]
RELEASE_APPROVALS = APPROVAL_KEYS[5:]


# --------------------------------------------------------------------------
# Defect log
# --------------------------------------------------------------------------
class Defects:
    def __init__(self) -> None:
        self.items: List[Dict[str, str]] = []

    def add(self, severity: str, slide_id: str, note: str) -> None:
        self.items.append({"severity": severity, "slide_id": slide_id, "note": note})

    def has(self, severity: str) -> bool:
        return any(d["severity"] == severity for d in self.items)


# --------------------------------------------------------------------------
# Spec validation (generator gate only — not a substitute for Stage 7 QA)
# --------------------------------------------------------------------------
def validate_spec(spec: Dict[str, Any], defects: Defects) -> None:
    for key in ["schema_version", "runtime_config", "lesson", "sources", "taxonomy", "slides", "qa"]:
        if key not in spec:
            defects.add("blocker", "-", f"missing top-level key '{key}'")
    if defects.has("blocker"):
        return
    if str(spec.get("schema_version")) not in ACCEPTED_SCHEMA_VERSIONS:
        defects.add("major", "-", f"schema_version '{spec.get('schema_version')}' not in {sorted(ACCEPTED_SCHEMA_VERSIONS)}")
    lesson = spec["lesson"]
    for key in ["course_code", "unit_title", "chapter_title", "lesson_title",
                "organizing_clinical_question", "concept_lanes"]:
        if not lesson.get(key):
            defects.add("blocker", "-", f"lesson.{key} is empty")
    lanes = set(lesson.get("concept_lanes", [])) | {"cross-lane"}
    if not 4 <= len(lesson.get("concept_lanes", [])) <= 6:
        defects.add("major", "-", "lesson.concept_lanes should have 4-6 entries")
    source_ids = {s.get("source_id") for s in spec["sources"]}
    seen: set = set()
    covered: set = set()
    active = [s for s in spec["slides"] if not s.get("retired")]
    if not active:
        defects.add("blocker", "-", "no active slides")
    for s in spec["slides"]:
        sid = str(s.get("slide_id", "?"))
        for key in REQUIRED_SLIDE_KEYS:
            if key not in s:
                defects.add("blocker", sid, f"missing slide key '{key}'")
        if not SLIDE_ID_RE.match(sid):
            defects.add("blocker", sid, "slide_id does not match ^S\\d{2}[A-Z]?$")
        if sid in seen:
            defects.add("blocker", sid, "duplicate slide_id")
        seen.add(sid)
        if s.get("retired"):
            continue
        ev = s.get("evidence_status")
        if ev not in EVIDENCE:
            defects.add("blocker", sid, f"evidence_status '{ev}' not allowed")
        if ev in {"source-grounded", "source-aligned"} and not s.get("source_refs"):
            defects.add("blocker", sid, f"{ev} with empty source_refs")
        for ref in s.get("source_refs", []):
            if ref not in source_ids:
                defects.add("blocker", sid, f"source_ref '{ref}' not in sources[]")
        arch = s.get("slide_archetype")
        if arch not in ARCHETYPES:
            defects.add("major", sid, f"unknown archetype '{arch}', rendering as content")
        if s.get("concept_lane") not in lanes:
            defects.add("major", sid, f"concept_lane '{s.get('concept_lane')}' not in lesson.concept_lanes")
        if s.get("activity_prompt") and not s.get("answer_key"):
            defects.add("major", sid, "activity_prompt without answer_key")
        if arch not in NO_SCRIPT_ARCHETYPES and len(str(s.get("speaker_script", "")).split()) < 20:
            defects.add("major", sid, "speaker_script under 20 words on a content slide")
        if len(str(s.get("slide_title", ""))) > 70:
            defects.add("minor", sid, "slide_title over 70 characters")
        budget = (s.get("layout_spec") or {}).get("density_budget") or {}
        max_b = int(budget.get("max_bullets", 6))
        max_w = int(budget.get("max_words_per_bullet", 14))
        bullets = s.get("on_slide_text") or []
        if len(bullets) > max_b:
            defects.add("major", sid, f"{len(bullets)} bullets exceeds budget {max_b}")
        for b in bullets:
            if len(str(b).split()) > max_w:
                defects.add("major", sid, f"bullet exceeds {max_w} words: '{str(b)[:40]}…'")
        for fn in s.get("cjm_functions") or []:
            if fn not in CJM:
                defects.add("major", sid, f"cjm_function '{fn}' not in the six CJMM functions")
            covered.add(fn)
    # v1.1 traceability checks — minor in MVP so they never block
    cos = {c.get("id") for c in lesson.get("course_objectives") or []}
    pos = {p.get("id") for p in lesson.get("program_outcomes") or []}
    fws = {f.get("framework_id"): f for f in (spec["taxonomy"].get("frameworks") or [])}
    for c in lesson.get("course_objectives") or []:
        for po in c.get("maps_to") or []:
            if po not in pos:
                defects.add("minor", "-", f"course_objective {c.get('id')} maps_to unknown program outcome '{po}'")
    for s in active:
        sid = s["slide_id"]
        co = s.get("course_objective_id")
        if co and co not in cos:
            defects.add("minor", sid, f"course_objective_id '{co}' not in lesson.course_objectives")
        for ref in s.get("standards_refs") or []:
            fid = ref.get("framework_id")
            if fid not in fws:
                defects.add("minor", sid, f"standards_ref framework '{fid}' not in taxonomy.frameworks")
            elif fws[fid].get("text_policy") == "identifier-only" and len(str(ref.get("ref", ""))) > 24:
                defects.add("major", sid, f"standards_ref for identifier-only framework '{fid}' looks like pasted text")
    # package-level standards refs (what the whole package evidences) — same rules as slide-level
    for ref in lesson.get("standards_refs") or []:
        fid = ref.get("framework_id")
        if fid not in fws:
            defects.add("minor", "-", f"lesson.standards_ref framework '{fid}' not in taxonomy.frameworks")
        elif fws[fid].get("text_policy") == "identifier-only" and len(str(ref.get("ref", ""))) > 24:
            defects.add("major", "-", f"lesson.standards_ref for identifier-only framework '{fid}' looks like pasted text")
        if fid == "CA-BRN-ART3":
            fw_file = Path(__file__).resolve().parent.parent / "references" / "frameworks" / "ca_brn_article3_requirements.json"
            if fw_file.exists() and ref.get("ref") not in json.loads(fw_file.read_text(encoding="utf-8"))["requirements"]:
                defects.add("minor", "-", f"lesson.standards_ref '{ref.get('ref')}' not a known CA-BRN-ART3 req_id")
    for it in spec.get("assessment_items") or []:
        iid = it.get("item_id", "?")
        if it.get("slide_id") and it["slide_id"] not in seen:
            defects.add("minor", "-", f"assessment_item {iid} names unknown slide '{it['slide_id']}'")
        if it.get("evidence_status") in {"source-grounded", "source-aligned"} and not it.get("source_refs"):
            defects.add("major", "-", f"assessment_item {iid} is {it['evidence_status']} with empty source_refs")
    missing = [fn for fn in CJM if fn not in covered]
    rationale = str(spec["qa"].get("cjm_coverage_rationale") or "")
    if not covered:
        # No slide maps to any clinical-judgment function. That is not a coverage
        # gap a sentence can excuse; the lesson simply is not mapped to the model.
        defects.add("blocker", "-", "no slide maps to any CJM function; a coverage rationale "
                                    "cannot stand in for the mapping itself")
    elif missing:
        unexplained = [fn for fn in missing if fn.lower() not in rationale.lower()]
        if unexplained:
            defects.add("blocker", "-", f"CJM functions never covered and not named in "
                                        f"qa.cjm_coverage_rationale: {', '.join(unexplained)}")
    validate_governance(spec, defects)


def validate_governance(spec: Dict[str, Any], defects: Defects) -> None:
    """master-lesson 1.0.0 envelope: promotion_state, approvals, taxonomy_lock.

    v1.2 slot. Absent block = MVP default (`intake_complete`, nothing approved).
    Only the consistency between qa.release_status and the approvals is
    enforced; a claimed `release-ready` without faculty + release approval is
    downgraded by the manifest writer and logged as major here.
    """
    gov = spec.get("governance") or {}
    state = gov.get("promotion_state", "intake_complete")
    if state not in PROMOTION_STATES:
        defects.add("major", "-", f"governance.promotion_state '{state}' not in {PROMOTION_STATES}")
    approvals = gov.get("approvals") or {}
    for k, v in approvals.items():
        if k not in APPROVAL_KEYS:
            defects.add("minor", "-", f"governance.approvals has unknown key '{k}'")
        elif not isinstance(v, bool):
            defects.add("minor", "-", f"governance.approvals.{k} must be boolean")
    lock = gov.get("taxonomy_lock") or {}
    if lock.get("status") not in (None, "unlocked", "locked"):
        defects.add("minor", "-", f"governance.taxonomy_lock.status '{lock.get('status')}' invalid")
    rs = spec["qa"].get("release_status", "draft-only")
    if rs not in RELEASE_STATES:
        defects.add("major", "-", f"qa.release_status '{rs}' not in {sorted(RELEASE_STATES)}")
    # Recorded gates are only meaningful if their names mean something.
    passed = [str(x) for x in (spec["qa"].get("gates_passed") or [])]
    for name in passed:
        if name not in KNOWN_GATES:
            defects.add("minor", "-", f"qa.gates_passed has unknown gate '{name}' "
                                      f"(typo? known gates: {sorted(KNOWN_GATES)})")
    # D1: a release-ready claim has to be backed by the QA gates the lesson requires.
    if rs == "release-ready":
        required = spec["qa"].get("required_gates")
        if required is None:
            required = DEFAULT_REQUIRED_GATES
        absent = [gname for gname in required if gname not in passed]
        if absent:
            defects.add("major", "-", f"release-ready claimed without required QA gate(s): "
                                      f"{', '.join(absent)}; record them with record_gate.py gate-pass "
                                      f"(set qa.required_gates to change what this lesson requires)")
    if rs == "release-ready":
        missing = [k for k in PRODUCTION_APPROVALS + RELEASE_APPROVALS if approvals.get(k) is not True]
        if missing:
            defects.add("major", "-", f"release-ready claimed without approvals: {', '.join(missing)}; downgraded to faculty-review-needed")
        if lock.get("status") != "locked":
            defects.add("major", "-", "release-ready claimed with taxonomy_lock.status != locked")
    if state in {"release_ready", "released"} and rs != "release-ready":
        defects.add("major", "-", f"governance.promotion_state '{state}' inconsistent with qa.release_status '{rs}'")


# --------------------------------------------------------------------------
# Deck
# --------------------------------------------------------------------------
def build_deck(spec, out: Path, demo: bool, defects: Defects) -> Path:
    rspec, notes = spec_adapter.spec_to_renderer(spec, demo)
    for n in notes:
        # adapter fallbacks are informational; unknown-archetype is already major
        defects.add("minor", n.split(":", 1)[0], f"adapter: {n.split(':', 1)[1].strip()}")
    renderer.make_presentation(rspec, out)
    return out


def deck_filename(spec, demo, blocked) -> str:
    rc = spec["runtime_config"]
    pattern = (rc.get("outputs") or {}).get("filename_pattern") or ""
    L = spec["lesson"]
    vals = {
        "runtime.run_date_yyyymmdd": (rc.get("runtime") or {}).get("run_date_yyyymmdd") or date.today().strftime("%Y%m%d"),
        "lesson.course_code": L.get("course_code", ""), "lesson.unit_title": L.get("unit_title", ""),
        "lesson.chapter_title": L.get("chapter_title", ""), "deck.part_number": "1",
    }
    name = pattern
    for k, v in vals.items():
        name = name.replace("{{" + k + "}}", str(v))
    if not name or "{{" in name:
        name = "lesson_deck.pptx"
    name = re.sub(r"[^\w.\-]+", "_", name)
    if demo:
        name = "DEMO_" + name
    if blocked:
        name = name.replace(".pptx", "_DRAFT.pptx")
    return name


# --------------------------------------------------------------------------
# Package writers
# --------------------------------------------------------------------------
def write_guides(spec, out: Path, demo: bool) -> None:
    L = spec["lesson"]
    slides = sorted((s for s in spec["slides"] if not s.get("retired")), key=lambda s: int(s["slide_number"]))
    banner = "> **DEMO / illustrative content — does not imply course-source support.**\n\n" if demo else ""

    fg = [f"# Facilitator Guide — {L['lesson_title']}\n", banner,
          f"**Course:** {L.get('course_code', '')}  ·  **Unit:** {L.get('unit_title', '')}  ·  **Chapter:** {L.get('chapter_title', '')}\n",
          f"**Organizing clinical question:** {L.get('organizing_clinical_question', '')}\n",
          f"**Concept lanes:** {' → '.join(L.get('concept_lanes', []))}\n",
          f"**Target duration:** {sum(int(s.get('target_duration_sec', 0)) for s in slides) // 60} min\n",
          "\n## Sources\n"]
    for src in spec["sources"]:
        fg.append(f"- `{src.get('source_id')}` {src.get('title', '')} — {src.get('kind', '')}, {src.get('license', '')}, {src.get('locator', '')} ({src.get('coverage_status', '')})")
        if src.get("attribution_statement"):
            fg.append(f"  - Attribution: {src['attribution_statement']}")
    fg.append("\n## Slide-by-slide\n")
    for s in slides:
        fg.append(f"### {s['slide_id']} · {s['slide_title']}")
        fg.append(f"*{s.get('slide_archetype')} · {s.get('concept_lane')} · {s.get('evidence_status')} · {s.get('target_duration_sec')} s*  ")
        fg.append(f"**Objective:** {s.get('learning_objective', '')}  ")
        if s.get("cjm_functions"):
            fg.append(f"**CJM:** {', '.join(s['cjm_functions'])}  ")
        if s.get("source_refs"):
            fg.append(f"**Sources:** {', '.join(s['source_refs'])}  ")
        fg.append(f"\n**Script:**\n\n{s.get('speaker_script', '')}\n")
        if s.get("activity_prompt"):
            fg.append(f"**Activity:** {s['activity_prompt']}\n")
            fg.append("**Answer key:**\n" + "\n".join(f"- {a}" for a in s.get("answer_key", [])) + "\n")
        if s.get("qa_notes"):
            fg.append(f"*QA note:* {s['qa_notes']}\n")
    items = spec.get("assessment_items") or []
    if items:
        fg.append("\n## Assessment items\n")
        for it in items:
            fg.append(f"### {it.get('item_id')} · {it.get('item_type')} · {it.get('concept_lane')} · {it.get('cjm_function')}")
            fg.append(f"**Stem:** {it.get('stem', '')}  ")
            for opt in it.get("options") or []:
                fg.append(f"- {opt}")
            fg.append(f"\n**Answer:** {it.get('answer', '')}  ")
            fg.append(f"**Rationale:** {it.get('rationale', '')}  ")
            fg.append(f"*remediation → {it.get('remediation_target_slide', '')} · {it.get('evidence_status', '')} · sources {', '.join(it.get('source_refs') or [])}*\n")
    if spec.get("remediation_map"):
        fg.append("\n## Remediation map\n")
        fg.append("| Miss pattern | Failed operation | Map location | Misconception | One-slide fix |")
        fg.append("|---|---|---|---|---|")
        for r in spec["remediation_map"]:
            fg.append(f"| {r.get('miss_pattern', '')} | {r.get('failed_operation', '')} | {r.get('map_location', '')} | {r.get('likely_misconception', '')} | {r.get('one_slide_fix', '')} |")
    if spec.get("improvement_log"):
        fg.append("\n## Improvement history\n")
        fg.append("| Action | Date | Trigger | Finding | Action taken | Evidence of effect |")
        fg.append("|---|---|---|---|---|---|")
        for ia in spec["improvement_log"]:
            fg.append(f"| {ia.get('action_id', '')} | {ia.get('date', '')} | {ia.get('trigger', '')} | {ia.get('finding', '')} | {ia.get('action_taken', '')} | {ia.get('evidence_of_effect') or '—'} |")
    (out / "facilitator_guide.md").write_text("\n".join(fg), encoding="utf-8")

    lh = [f"# {L['lesson_title']} — Learner Handout\n", banner,
          f"**Clinical question:** {L.get('organizing_clinical_question', '')}\n",
          "## The map\n", " → ".join(L.get("concept_lanes", [])) + "\n"]
    for s in slides:
        if s.get("slide_archetype") in {"title"}:
            continue
        lh.append(f"### {s['slide_title']}")
        for b in s.get("on_slide_text") or []:
            lh.append(f"- {b}")
        if s.get("activity_prompt"):
            lh.append(f"\n**Try it:** {s['activity_prompt']}\n")
        lh.append("")
    lh.append("## Exit check\n")
    lh.append("For each concept lane, write one thing the nurse should *notice*, and one thing the nurse should *do*.\n")
    attributions = [src["attribution_statement"] for src in spec["sources"] if src.get("attribution_statement")]
    if attributions:
        lh.append("\n## Attribution\n")
        lh.extend(f"- {a}" for a in attributions)
    (out / "learner_handout.md").write_text("\n".join(lh), encoding="utf-8")


def write_assessment_map(spec, out: Path) -> int:
    rows = []
    items = spec.get("assessment_items") or []
    if items:
        for it in items:
            rows.append([it.get("learning_objective", ""), it.get("concept_lane", ""), it.get("slide_id", ""),
                         it.get("stem", ""), it.get("cjm_function", ""), it.get("item_type", ""),
                         it.get("remediation_target_slide", "")])
    else:
        for s in spec["slides"]:
            if s.get("retired") or not s.get("activity_prompt"):
                continue
            rt = s.get("remediation_target") or {}
            rows.append([s.get("learning_objective", ""), s.get("concept_lane", ""), s["slide_id"],
                         s["activity_prompt"], ", ".join(s.get("cjm_functions") or []), s.get("slide_archetype", ""),
                         rt.get("concept_lane", "")])
    with (out / "assessment_map.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["objective", "concept_lane", "slide", "activity", "cjm_function", "item_type", "remediation_target"])
        w.writerows(rows)
    return len(rows)


def write_traceability(spec, out: Path) -> Dict[str, Any]:
    L = spec["lesson"]
    co_map = {c.get("id"): c for c in L.get("course_objectives") or []}
    items_by_slide: Dict[str, List[str]] = {}
    for it in spec.get("assessment_items") or []:
        items_by_slide.setdefault(it.get("slide_id", ""), []).append(it.get("item_id", ""))
    rows = []
    unmapped = {"no_course_objective": 0, "no_standards_ref": 0, "no_assessment_item": 0}
    for s in sorted((s for s in spec["slides"] if not s.get("retired")), key=lambda s: int(s["slide_number"])):
        co = s.get("course_objective_id") or ""
        po_ids = (co_map.get(co) or {}).get("maps_to") or []
        refs = s.get("standards_refs") or []
        item_ids = items_by_slide.get(s["slide_id"], [])
        if not co: unmapped["no_course_objective"] += 1
        if not refs: unmapped["no_standards_ref"] += 1
        if not item_ids and s.get("slide_archetype") not in {"title", "takeaway", "chapter_map"}: unmapped["no_assessment_item"] += 1
        rows.append({"slide_id": s["slide_id"], "learning_objective": s.get("learning_objective", ""),
                     "course_objective_id": co, "program_outcome_ids": ";".join(po_ids),
                     "standards_refs": ";".join(f"{r.get('framework_id')}:{r.get('ref')}" for r in refs),
                     "cjm_functions": ";".join(s.get("cjm_functions") or []),
                     "assessment_item_ids": ";".join(item_ids), "evidence_status": s.get("evidence_status", "")})
    with (out / "traceability_matrix.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else ["slide_id"])
        w.writeheader(); w.writerows(rows)
    return {"frameworks": spec["taxonomy"].get("frameworks") or [], "program_outcomes": L.get("program_outcomes") or [],
            "course_objectives": L.get("course_objectives") or [], "package_standards_refs": L.get("standards_refs") or [],
            "matrix": rows, "unmapped_counts": unmapped}


def resolve_release_status(spec, all_defects: List[Dict[str, str]], demo: bool) -> str:
    status = spec["qa"].get("release_status", "draft-only")
    approvals = (spec.get("governance") or {}).get("approvals") or {}
    lock = ((spec.get("governance") or {}).get("taxonomy_lock") or {}).get("status")
    if any(d["severity"] == "blocker" for d in all_defects):
        status = "blocked"
    elif status == "release-ready":
        approved = all(approvals.get(k) is True for k in PRODUCTION_APPROVALS + RELEASE_APPROVALS) and lock == "locked"
        if any(d["severity"] == "major" for d in all_defects) or not approved:
            status = "faculty-review-needed"
    if demo:
        status = "draft-only" if status != "blocked" else status
    return status


def write_manifest_and_qa(spec, out: Path, defects: Defects, files: List[str], demo: bool,
                          exports: Dict[str, Any] | None = None) -> str:
    slides = [s for s in spec["slides"]]
    coverage = {fn: [s["slide_id"] for s in slides if not s.get("retired") and fn in (s.get("cjm_functions") or [])] for fn in CJM}
    all_defects = list(spec["qa"].get("defects") or []) + defects.items
    status = resolve_release_status(spec, all_defects, demo)
    gov = spec.get("governance") or {}
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "adapter_version": spec_adapter.ADAPTER_VERSION,
        "generated_at_iso": datetime.now().isoformat(timespec="seconds"),
        "demo": demo,
        "runtime_config": spec["runtime_config"],
        "lesson": spec["lesson"],
        "sources": spec["sources"],
        "taxonomy": spec["taxonomy"],
        "governance": {
            "envelope": "master-lesson-1.0.0",
            "promotion_state": gov.get("promotion_state", "intake_complete"),
            "approvals": {k: bool((gov.get("approvals") or {}).get(k, False)) for k in APPROVAL_KEYS},
            "taxonomy_lock": gov.get("taxonomy_lock") or {"status": "unlocked"},
            "administrative_metadata": gov.get("administrative_metadata") or {},
        },
        "slides": [{k: s.get(k) for k in ["slide_id", "slide_number", "slide_title", "slide_archetype", "concept_lane",
                                          "evidence_status", "source_refs", "cjm_functions", "target_duration_sec",
                                          "audio_duration_sec", "audio_filename", "qa_status", "retired"]} for s in slides],
        "assessment_items": [{k: it.get(k) for k in ["item_id", "slide_id", "item_type", "concept_lane", "cjm_function",
                                                     "evidence_status", "source_refs", "remediation_target_slide"]}
                             for it in spec.get("assessment_items") or []],
        "cjm_coverage": coverage,
        "cjm_coverage_rationale": spec["qa"].get("cjm_coverage_rationale", ""),
        "qa": {"release_status": status, "gates_passed": (spec["qa"].get("gates_passed") or []) + ["deck_render", "package_manifest"],
               "defect_counts": {sev: sum(1 for d in all_defects if d["severity"] == sev) for sev in ("blocker", "major", "minor")}},
        "files": files,
        "exports": exports or {},
        "revision_log": spec.get("revision_log") or [],
        "traceability": write_traceability(spec, out),
        "outcomes": spec.get("outcomes") or {},
        "improvement_log": spec.get("improvement_log") or [],
    }
    (out / "lesson_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    qa = [f"# QA Log — {spec['lesson']['lesson_title']}\n", f"**Release status:** `{status}`\n",
          f"**Promotion state:** `{manifest['governance']['promotion_state']}`\n"]
    for sev in ("blocker", "major", "minor"):
        rows = [d for d in all_defects if d["severity"] == sev]
        qa.append(f"\n## {sev.title()} ({len(rows)})\n")
        qa.extend(f"- `{d.get('slide_id', '-')}` {d.get('note', '')}" for d in rows)
    qa.append("\n## CJM coverage\n")
    qa.extend(f"- {fn}: {', '.join(ids) if ids else '**none**'}" for fn, ids in coverage.items())
    (out / "qa_log.md").write_text("\n".join(qa), encoding="utf-8")
    return status


# --------------------------------------------------------------------------
# Demo spec — illustrative only, generic clinical topic, no source claims
# --------------------------------------------------------------------------
def slide(sid, num, title, arch, section, lane, objective, bullets, script, cjm=None, activity="", answers=None,
          ev="illustrative-example", refs=None, card=None, dur=60):
    return {
        "slide_id": sid, "slide_number": num, "slide_title": title, "slide_archetype": arch,
        "lesson_section": section, "concept_lane": lane, "source_refs": refs or [], "evidence_status": ev,
        "cjm_functions": cjm or [], "nursing_action_category": "", "learning_objective": objective,
        "on_slide_text": bullets, "activity_prompt": activity, "answer_key": answers or [],
        "visual_notes": "", "speaker_script": script, "tts_text": "", "target_duration_sec": dur,
        "audio_duration_sec": None, "auto_advance": False,
        "layout_spec": {"archetype": arch, "density_budget": {"max_bullets": 6, "max_words_per_bullet": 14},
                        "regions": ["header", "body", "footer"], "card_data": card or []},
        "allow_overlap": False, "qa_status": "unreviewed", "qa_notes": "",
        "remediation_target": {"concept_lane": lane, "cjm_function": (cjm or [""])[0], "misconception": "", "fix_type": ""},
        "audio_filename": "", "course_objective_id": "", "standards_refs": [],
    }


def demo_spec() -> Dict[str, Any]:
    lanes = ["baseline", "disruption", "cues", "risk", "response", "follow-up"]
    s = ("This is demonstration narration. It exists to show that the speaker-notes channel carries a complete "
         "verbatim script separate from the on-slide text, and that the script length passes the generator gate.")
    return {
        "schema_version": SCHEMA_VERSION,
        "runtime_config": {"runtime": {"run_date_yyyymmdd": date.today().strftime("%Y%m%d"), "package_id": "DEMO",
                                       "build_mode": "full_production", "deployment_mode": "hybrid",
                                       "rebuild_scope": "full", "output_root": "."},
                           "outputs": {"filename_pattern": ""}},
        "lesson": {"course_code": "DEMO", "program_level": "", "audience": "demo", "unit_title": "Demo Unit",
                   "chapter_id": "0", "chapter_title": "Demo Chapter", "lesson_title": "Generator Demonstration",
                   "concept": "", "exemplars": [], "clinical_domain": "", "source_family": "none",
                   "source_anchor": "", "page_range": "",
                   "organizing_clinical_question": "What does the nurse notice, and what does the nurse do first?",
                   "opening_patient_question": "", "concept_lanes": lanes, "target_duration_minutes": 10,
                   "program_outcomes": [], "course_objectives": []},
        "sources": [{"source_id": "SRC01", "title": "Demo placeholder", "kind": "external", "license": "instructor-owned",
                     "locator": "n/a", "coverage_status": "absent"}],
        "taxonomy": {"glossary": [], "concept_tags": [], "outcome_tags": [], "nclex_client_needs": [],
                     "cjm_functions": CJM, "proposed_new_tags": [], "frameworks": []},
        "governance": {"promotion_state": "intake_complete", "approvals": {}, "taxonomy_lock": {"status": "unlocked"}},
        "slides": [
            slide("S01", 1, "Title", "title", "opening", "cross-lane", "", [], "Demo title.", dur=20),
            slide("S02", 2, "Opening case", "opening_case", "opening", "cues",
                  "Recognize the cues that matter in a first look.", ["Missing: onset", "Missing: vitals"], s, ["recognize cues"],
                  card=[{"presentation": "Demo presentation text describing a patient scenario in plain language.",
                         "cues": ["Cue one", "Cue two", "Cue three"], "prompt": "Which cue matters first?"}],
                  activity="Which cue matters first?", answers=["Cue two — demo rationale."]),
            slide("S03", 3, "Chapter map", "chapter_map", "map", "cross-lane",
                  "See the whole route from foundation to bedside action.", [], "Map slide.",
                  card=[{"lane": ln, "nodes": [f"{ln} node A", f"{ln} node B"]} for ln in lanes], dur=45),
            slide("S04", 4, "Concept cards", "concept_cards", "lane: baseline", "baseline",
                  "Connect structure to function.", [], s, ["analyze cues"],
                  card=[{"heading": "Card one", "body": "Demo body text for a concept card.", "cjm": "analyze cues"},
                        {"heading": "Card two", "body": "Demo body text for a concept card.", "cjm": "analyze cues"},
                        {"heading": "Card three", "body": "Demo body text for a concept card.", "cjm": "prioritize hypotheses"}]),
            slide("S05", 5, "Content fallback", "content", "lane: risk", "risk",
                  "Show the plain bullet layout with an activity band.",
                  ["Bullet one within budget", "Bullet two within budget", "Bullet three within budget"], s,
                  ["prioritize hypotheses"], activity="Rank these by risk.", answers=["Demo order."]),
            slide("S06", 6, "Urgency sort", "urgency_sort", "lane: response", "response",
                  "Choose what matters first.", [], s, ["prioritize hypotheses", "generate solutions"],
                  activity="Drag into order of urgency.", answers=["C, A, B"],
                  card=[{"items": ["Item A", "Item B", "Item C"], "correct_order": [2, 0, 1]}]),
            slide("S07", 7, "Checkpoint", "checkpoint_mcq", "lane: response", "response",
                  "Select the priority action.", [], s, ["take action"],
                  activity="Select one.", answers=["B"],
                  card=[{"stem": "Demo stem: which action is first?", "options": ["A. Option", "B. Option", "C. Option", "D. Option"],
                         "correct": "B", "rationale": "Demo rationale."}]),
            slide("S08", 8, "Timeline", "timeline", "lane: follow-up", "follow-up",
                  "Sequence the reassessment.", [], s, ["evaluate outcomes"],
                  card=[{"label": "0 min", "event": "Act"}, {"label": "15 min", "event": "Reassess"},
                        {"label": "60 min", "event": "Evaluate"}]),
            slide("S09", 9, "Exchange model (renderer-native pass-through)", "exchange_model", "lane: disruption", "disruption",
                  "Show a renderer-native archetype fed through card_data pass-through.", [], s, ["analyze cues"],
                  card=[{"left": {"title": "input", "body": "demo"}, "center": {"title": "exchange", "body": "demo"},
                         "right": {"title": "output", "body": "demo"}}]),
            slide("S10", 10, "Takeaway", "takeaway", "close", "cross-lane", "",
                  ["Notice", "Interpret", "Prioritize", "Act", "Evaluate"], "Close.", dur=30),
        ],
        "assessment_items": [],
        "remediation_map": [],
        "qa": {"release_status": "draft-only", "gates_passed": [], "defects": [],
               "cjm_coverage_rationale": "Demo package; coverage is illustrative."},
        "revision_log": [],
        "outcomes": {}, "improvement_log": [],
    }


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------
def run(spec: Dict[str, Any], outdir: Path, demo: bool) -> Dict[str, Any]:
    outdir.mkdir(parents=True, exist_ok=True)
    defects = Defects()
    validate_spec(spec, defects)
    if defects.has("blocker") and any(d["slide_id"] == "-" and d["note"].startswith("missing top-level") for d in defects.items):
        return {"status": "invalid", "defects": defects.items, "exit": 2}
    blocked = defects.has("blocker")
    name = deck_filename(spec, demo, blocked)
    build_deck(spec, outdir / name, demo, defects)
    write_guides(spec, outdir, demo)
    n_items = write_assessment_map(spec, outdir)
    files = [name, "facilitator_guide.md", "learner_handout.md", "assessment_map.csv", "traceability_matrix.csv",
             "lesson_manifest.json", "qa_log.md"]
    export_files, exports, export_warnings = export_lms.export(spec, outdir, name, demo)
    files.extend(export_files)
    for w in export_warnings:
        defects.add("major" if w.startswith("cartridge:") else "minor", "-", f"export: {w}")
    status = write_manifest_and_qa(spec, outdir, defects, files, demo, exports)
    return {"status": status, "deck": str(outdir / name), "assessment_rows": n_items, "defects": defects.items,
            "blocked": blocked, "exit": 1 if blocked else 0}


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--spec", type=Path, help="v1.1/v1.2 lesson_spec.json")
    g.add_argument("--legacy", type=Path, help="renderer-format spec; converted with spec_adapter.legacy_to_spec first")
    g.add_argument("--demo", action="store_true")
    ap.add_argument("--outdir", type=Path, required=True)
    ap.add_argument("--label-demo", action="store_true", help="treat --spec/--legacy content as demo (draft-only, DEMO_ prefix)")
    a = ap.parse_args(argv)
    demo = a.demo or a.label_demo
    if a.demo:
        spec = demo_spec()
        a.outdir.mkdir(parents=True, exist_ok=True)
        (a.outdir / "lesson_spec.json").write_text(json.dumps(spec, indent=2), encoding="utf-8")
    elif a.legacy:
        spec = spec_adapter.legacy_to_spec(json.loads(a.legacy.read_text(encoding="utf-8")))
        a.outdir.mkdir(parents=True, exist_ok=True)
        (a.outdir / "lesson_spec.json").write_text(json.dumps(spec, indent=2, ensure_ascii=False), encoding="utf-8")
    else:
        spec = json.loads(a.spec.read_text(encoding="utf-8"))
    result = run(spec, a.outdir, demo)
    if result["status"] == "invalid":
        for d in result["defects"]:
            print(f"[{d['severity'].upper()}] {d['slide_id']}: {d['note']}")
        return 2
    print(f"deck: {result['deck']}")
    print(f"assessment rows: {result['assessment_rows']}")
    print(f"release status: {result['status']}")
    for d in result["defects"]:
        print(f"[{d['severity'].upper()}] {d['slide_id']}: {d['note']}")
    return result["exit"]


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
