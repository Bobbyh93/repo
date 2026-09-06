#!/usr/bin/env python3
"""Harrity Lesson Builder — Stage 9 package generator.

Usage:
    python generate_lesson_package.py --spec lesson_spec.json --outdir OUT
    python generate_lesson_package.py --demo --outdir OUT

Reads lesson_spec.json (see references/package-schema.md) and writes:
    lesson_deck.pptx  facilitator_guide.md  learner_handout.md
    assessment_map.csv  lesson_manifest.json  qa_log.md

The generator never invents content. It renders what the spec carries,
logs every defect it detects, and stamps outputs _DRAFT when a blocker exists.
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

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Emu, Inches, Pt

# --------------------------------------------------------------------------
# Constants
# --------------------------------------------------------------------------
SCHEMA_VERSION = "1.1"
SLIDE_ID_RE = re.compile(r"^S\d{2}[A-Z]?$")
EVIDENCE = {"source-grounded", "source-aligned", "inferred", "illustrative-example",
            "instructor-added", "provisional", "unresolved", "needs-verification"}
CJM = ["recognize cues", "analyze cues", "prioritize hypotheses",
       "generate solutions", "take action", "evaluate outcomes"]
ARCHETYPES = {"title", "opening_case", "clinical_question", "chapter_map", "warmup_sequence",
              "concept_cards", "match_activity", "debrief", "timeline", "checkpoint_mcq",
              "mini_case", "urgency_sort", "capstone_mcq", "retrieval_check", "takeaway", "content"}
REQUIRED_SLIDE_KEYS = ["slide_id", "slide_number", "slide_title", "slide_archetype", "lesson_section",
                       "concept_lane", "source_refs", "evidence_status", "cjm_functions",
                       "nursing_action_category", "learning_objective", "on_slide_text",
                       "activity_prompt", "answer_key", "visual_notes", "speaker_script", "tts_text",
                       "target_duration_sec", "audio_duration_sec", "auto_advance", "layout_spec",
                       "allow_overlap", "qa_status", "qa_notes", "remediation_target", "audio_filename"]

# Palette — semantic, restrained. One dominant, one support, one accent.
INK = RGBColor(0x1A, 0x1A, 0x1A)
SLATE = RGBColor(0x2A, 0x33, 0x40)      # header band / dark slides
PAPER = RGBColor(0xFA, 0xF9, 0xF6)      # content background
PANEL = RGBColor(0xEF, 0xF2, 0xF6)      # cards
RULE = RGBColor(0xB8, 0xBE, 0xC7)
MUTED = RGBColor(0x6A, 0x6A, 0x6A)
ACCENT = RGBColor(0xB0, 0x00, 0x20)     # critical / answer / emphasis
GOLD = RGBColor(0xD8, 0xB3, 0x3C)       # activity / attention
GREEN = RGBColor(0x3E, 0x7C, 0x4F)      # confirmed / source-grounded
WHITE = RGBColor(0xFF, 0xFF, 0xFF)

W, H = Inches(13.333), Inches(7.5)
M = Inches(0.5)
HEAD_H = Inches(0.95)
FOOT_H = Inches(0.42)
BODY_TOP = HEAD_H + Inches(0.25)
BODY_H = H - BODY_TOP - FOOT_H - Inches(0.15)


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
        if arch not in {"title", "takeaway", "chapter_map"} and len(str(s.get("speaker_script", "")).split()) < 20:
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
    missing = [fn for fn in CJM if fn not in covered]
    if missing and not spec["qa"].get("cjm_coverage_rationale"):
        defects.add("blocker", "-", f"CJM functions never covered, no rationale: {', '.join(missing)}")


# --------------------------------------------------------------------------
# Drawing helpers
# --------------------------------------------------------------------------
def rect(slide, x, y, w, h, fill, line=None, shape=MSO_SHAPE.RECTANGLE):
    shp = slide.shapes.add_shape(shape, x, y, w, h)
    shp.fill.solid()
    shp.fill.fore_color.rgb = fill
    if line is None:
        shp.line.fill.background()
    else:
        shp.line.color.rgb = line
        shp.line.width = Pt(0.75)
    shp.shadow.inherit = False
    return shp


def text(slide, x, y, w, h, content, size=14, bold=False, color=INK, align=PP_ALIGN.LEFT,
         anchor=MSO_ANCHOR.TOP, italic=False, bullets=False, para_space=4):
    tb = slide.shapes.add_textbox(x, y, w, h)
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = Inches(0.05)
    tf.margin_top = tf.margin_bottom = Inches(0.03)
    lines = content if isinstance(content, list) else [content]
    for i, line in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.space_after = Pt(para_space)
        run = p.add_run()
        run.text = ("•  " if bullets else "") + str(line)
        f = run.font
        f.size = Pt(size)
        f.bold = bold
        f.italic = italic
        f.color.rgb = color
        f.name = "Calibri"
    return tb


def chip(slide, x, y, label, fill, color=WHITE, size=9, w=None):
    w = w or Inches(0.13 * len(label) + 0.25)
    s = rect(slide, x, y, w, Inches(0.26), fill, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
    s.adjustments[0] = 0.5
    tf = s.text_frame
    tf.margin_left = tf.margin_right = Inches(0.04)
    tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    r.text = label
    r.font.size = Pt(size)
    r.font.bold = True
    r.font.color.rgb = color
    r.font.name = "Calibri"
    return w


def evidence_color(ev: str) -> RGBColor:
    if ev in {"source-grounded", "source-aligned"}:
        return GREEN
    if ev in {"needs-verification", "unresolved"}:
        return ACCENT
    return GOLD


def frame(prs, s: Dict[str, Any], dark=False):
    """Header band, footer strip, CJM chips. Returns the slide."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    rect(slide, 0, 0, W, H, SLATE if dark else PAPER)
    if not dark:
        rect(slide, 0, 0, W, HEAD_H, SLATE)
        text(slide, M, Inches(0.12), W - 2 * M, Inches(0.5), s["slide_title"], size=24, bold=True, color=WHITE)
        text(slide, M, Inches(0.58), W - 2 * M, Inches(0.3), s.get("learning_objective", ""),
             size=11, color=RGBColor(0xCA, 0xD2, 0xDC), italic=True)
        # footer
        fy = H - FOOT_H
        rect(slide, 0, fy, W, Emu(9525), RULE)
        x = M
        for fn in s.get("cjm_functions") or []:
            x += chip(slide, x, fy + Inches(0.08), fn, SLATE) + Inches(0.06)
        meta = f"{s['slide_id']}   ·   {s.get('concept_lane', '')}   ·   {s.get('lesson_section', '')}"
        text(slide, W / 2, fy + Inches(0.06), W / 2 - M - Inches(1.8), Inches(0.3), meta, size=9, color=MUTED,
             align=PP_ALIGN.RIGHT)
        ev = s.get("evidence_status", "")
        chip(slide, W - M - Inches(1.7), fy + Inches(0.08), ev, evidence_color(ev), w=Inches(1.7))
    notes = s.get("speaker_script") or ""
    if s.get("answer_key"):
        notes += "\n\nANSWER KEY:\n" + "\n".join(f"- {a}" for a in s["answer_key"])
    if s.get("visual_notes"):
        notes += f"\n\nVISUAL NOTES: {s['visual_notes']}"
    slide.notes_slide.notes_text_frame.text = notes
    return slide


def body_bullets(slide, s, x=None, y=None, w=None, h=None, size=18):
    x = x if x is not None else M
    y = y if y is not None else BODY_TOP
    w = w if w is not None else W - 2 * M
    h = h if h is not None else BODY_H
    text(slide, x, y, w, h, s.get("on_slide_text") or [], size=size, bullets=True, para_space=10)


def activity_band(slide, s, y=None):
    if not s.get("activity_prompt"):
        return
    y = y if y is not None else H - FOOT_H - Inches(1.05)
    rect(slide, M, y, W - 2 * M, Inches(0.85), RGBColor(0xFF, 0xF6, 0xD6), line=GOLD)
    text(slide, M + Inches(0.12), y + Inches(0.05), Inches(1.2), Inches(0.3), "DO NOW", size=10, bold=True,
         color=RGBColor(0x6B, 0x53, 0x10))
    text(slide, M + Inches(1.2), y + Inches(0.05), W - 2 * M - Inches(1.4), Inches(0.75), s["activity_prompt"],
         size=14, color=INK, anchor=MSO_ANCHOR.MIDDLE)


# --------------------------------------------------------------------------
# Archetype renderers
# --------------------------------------------------------------------------
def r_title(prs, s, lesson, demo):
    slide = frame(prs, s, dark=True)
    title = ("DEMO — " if demo else "") + lesson["lesson_title"]
    text(slide, M, Inches(1.6), W - 2 * M, Inches(1.4), title, size=40, bold=True, color=WHITE)
    sub = f"{lesson.get('course_code', '')}  ·  {lesson.get('unit_title', '')}  ·  {lesson.get('chapter_title', '')}"
    text(slide, M, Inches(3.0), W - 2 * M, Inches(0.5), sub, size=16, color=RGBColor(0xCA, 0xD2, 0xDC))
    rect(slide, M, Inches(3.75), Inches(1.2), Emu(28575), GOLD)
    text(slide, M, Inches(4.0), W - 2 * M, Inches(1.2), lesson.get("organizing_clinical_question", ""),
         size=22, italic=True, color=WHITE)
    lanes = "   →   ".join(lesson.get("concept_lanes", []))
    text(slide, M, Inches(6.3), W - 2 * M, Inches(0.5), lanes, size=13, color=GOLD, bold=True)
    if demo:
        text(slide, M, Inches(6.9), W - 2 * M, Inches(0.4),
             "Illustrative demo content. Does not imply course-source support.", size=10, color=RGBColor(0xCA, 0xD2, 0xDC))


def r_takeaway(prs, s, lesson, demo):
    slide = frame(prs, s, dark=True)
    text(slide, M, Inches(0.6), W - 2 * M, Inches(0.9), s["slide_title"], size=30, bold=True, color=WHITE)
    rect(slide, M, Inches(1.5), Inches(1.2), Emu(28575), GOLD)
    text(slide, M, Inches(1.8), W - 2 * M, Inches(4.5), s.get("on_slide_text") or [], size=20, color=WHITE,
         bullets=True, para_space=14)
    text(slide, M, H - Inches(0.7), W - 2 * M, Inches(0.4),
         f"{s['slide_id']}  ·  {s.get('evidence_status', '')}", size=9, color=RGBColor(0xCA, 0xD2, 0xDC))


def r_chapter_map(prs, s, lesson, demo):
    slide = frame(prs, s)
    cards = (s.get("layout_spec") or {}).get("card_data") or [
        {"lane": ln, "nodes": []} for ln in lesson.get("concept_lanes", [])]
    n = max(1, len(cards))
    gap = Inches(0.2)
    col_w = (W - 2 * M - gap * (n - 1)) / n
    top = BODY_TOP
    for i, c in enumerate(cards):
        x = M + i * (col_w + gap)
        rect(slide, x, top, col_w, Inches(0.5), SLATE)
        text(slide, x, top, col_w, Inches(0.5), c.get("lane", ""), size=14, bold=True, color=WHITE,
             align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
        y = top + Inches(0.65)
        for j, node in enumerate(c.get("nodes", [])):
            rect(slide, x, y, col_w, Inches(0.62), PANEL, line=RULE, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
            text(slide, x, y, col_w, Inches(0.62), node, size=12, color=INK, align=PP_ALIGN.CENTER,
                 anchor=MSO_ANCHOR.MIDDLE)
            y += Inches(0.62)
            if j < len(c.get("nodes", [])) - 1:
                text(slide, x, y - Inches(0.04), col_w, Inches(0.22), "▼", size=9, color=MUTED, align=PP_ALIGN.CENTER)
                y += Inches(0.16)
    text(slide, M, H - FOOT_H - Inches(0.5), W - 2 * M, Inches(0.35),
         "foundation  ▼  bedside action", size=10, color=MUTED, align=PP_ALIGN.RIGHT, italic=True)


def r_concept_cards(prs, s, lesson, demo):
    slide = frame(prs, s)
    cards = (s.get("layout_spec") or {}).get("card_data") or []
    if not cards:
        body_bullets(slide, s)
        activity_band(slide, s)
        return
    n = len(cards)
    cols = 3 if n > 4 else min(n, 3)
    rows = (n + cols - 1) // cols
    gap = Inches(0.2)
    avail_h = BODY_H - (Inches(1.0) if s.get("activity_prompt") else 0)
    cw = (W - 2 * M - gap * (cols - 1)) / cols
    ch = (avail_h - gap * (rows - 1)) / rows
    for i, c in enumerate(cards):
        r, col = divmod(i, cols)
        x = M + col * (cw + gap)
        y = BODY_TOP + r * (ch + gap)
        rect(slide, x, y, cw, ch, PANEL, line=RULE)
        rect(slide, x, y, Inches(0.08), ch, SLATE)
        text(slide, x + Inches(0.18), y + Inches(0.08), cw - Inches(0.3), Inches(0.4), c.get("heading", ""),
             size=15, bold=True)
        text(slide, x + Inches(0.18), y + Inches(0.5), cw - Inches(0.3), ch - Inches(0.9), c.get("body", ""),
             size=12)
        if c.get("cjm"):
            chip(slide, x + Inches(0.18), y + ch - Inches(0.36), c["cjm"], SLATE)
    activity_band(slide, s)


def r_mcq(prs, s, lesson, demo):
    slide = frame(prs, s)
    q = ((s.get("layout_spec") or {}).get("card_data") or [{}])[0]
    text(slide, M, BODY_TOP, W - 2 * M, Inches(1.3), q.get("stem", s.get("activity_prompt", "")), size=18, bold=True)
    y = BODY_TOP + Inches(1.4)
    for opt in q.get("options", []):
        rect(slide, M, y, W - 2 * M, Inches(0.55), PANEL, line=RULE, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
        text(slide, M + Inches(0.15), y, W - 2 * M - Inches(0.3), Inches(0.55), opt, size=15, anchor=MSO_ANCHOR.MIDDLE)
        y += Inches(0.68)
    if q.get("correct"):
        slide.notes_slide.notes_text_frame.text += f"\n\nCORRECT: {q['correct']}\nRATIONALE: {q.get('rationale', '')}"


def r_case(prs, s, lesson, demo):
    slide = frame(prs, s)
    c = ((s.get("layout_spec") or {}).get("card_data") or [{}])[0]
    lw = (W - 2 * M) * 0.55
    rw = W - 2 * M - lw - Inches(0.25)
    h = BODY_H - Inches(1.05)
    rect(slide, M, BODY_TOP, lw, h, PANEL, line=RULE)
    text(slide, M + Inches(0.15), BODY_TOP + Inches(0.1), lw - Inches(0.3), Inches(0.35), "PRESENTATION", size=10,
         bold=True, color=MUTED)
    text(slide, M + Inches(0.15), BODY_TOP + Inches(0.45), lw - Inches(0.3), h - Inches(0.55),
         c.get("presentation", " ".join(s.get("on_slide_text") or [])), size=14)
    rx = M + lw + Inches(0.25)
    rect(slide, rx, BODY_TOP, rw, h, WHITE, line=RULE)
    text(slide, rx + Inches(0.15), BODY_TOP + Inches(0.1), rw - Inches(0.3), Inches(0.35), "CUES", size=10,
         bold=True, color=MUTED)
    text(slide, rx + Inches(0.15), BODY_TOP + Inches(0.45), rw - Inches(0.3), h - Inches(0.55),
         c.get("cues", []), size=14, bullets=True, para_space=8)
    prompt = c.get("prompt") or s.get("activity_prompt")
    if prompt:
        activity_band(slide, {"activity_prompt": prompt})


def r_urgency(prs, s, lesson, demo):
    slide = frame(prs, s)
    c = ((s.get("layout_spec") or {}).get("card_data") or [{}])[0]
    items = c.get("items", s.get("on_slide_text") or [])
    text(slide, M, BODY_TOP, W - 2 * M, Inches(0.5), s.get("activity_prompt", "Sort by urgency."), size=16, bold=True)
    y = BODY_TOP + Inches(0.65)
    for it in items:
        rect(slide, M, y, W - 2 * M, Inches(0.55), PANEL, line=RULE)
        text(slide, M + Inches(0.15), y, W - 2 * M - Inches(0.3), Inches(0.55), it, size=14, anchor=MSO_ANCHOR.MIDDLE)
        y += Inches(0.65)
    if c.get("correct_order"):
        order = " → ".join(items[i] for i in c["correct_order"] if i < len(items))
        slide.notes_slide.notes_text_frame.text += f"\n\nCORRECT ORDER: {order}"


def r_match(prs, s, lesson, demo):
    slide = frame(prs, s)
    c = ((s.get("layout_spec") or {}).get("card_data") or [{}])[0]
    left, right = c.get("left", []), c.get("right", [])
    cw = (W - 2 * M - Inches(0.6)) / 2
    for i, col in enumerate((left, right)):
        x = M + i * (cw + Inches(0.6))
        y = BODY_TOP
        for it in col:
            rect(slide, x, y, cw, Inches(0.55), PANEL if i == 0 else WHITE, line=RULE)
            text(slide, x + Inches(0.12), y, cw - Inches(0.24), Inches(0.55), it, size=13, anchor=MSO_ANCHOR.MIDDLE)
            y += Inches(0.65)
    activity_band(slide, s)
    if c.get("pairs"):
        pairs = "; ".join(f"{left[a]} ↔ {right[b]}" for a, b in c["pairs"] if a < len(left) and b < len(right))
        slide.notes_slide.notes_text_frame.text += f"\n\nPAIRS: {pairs}"


def r_timeline(prs, s, lesson, demo):
    slide = frame(prs, s)
    cards = (s.get("layout_spec") or {}).get("card_data") or []
    if not cards:
        body_bullets(slide, s)
        return
    n = len(cards)
    y_line = BODY_TOP + Inches(1.2)
    rect(slide, M, y_line, W - 2 * M, Emu(28575), SLATE)
    step = (W - 2 * M) / n
    for i, c in enumerate(cards):
        cx = M + step * i + step / 2
        rect(slide, cx - Inches(0.12), y_line - Inches(0.1), Inches(0.24), Inches(0.24), GOLD, shape=MSO_SHAPE.OVAL)
        text(slide, cx - step / 2, y_line - Inches(0.75), step, Inches(0.5), c.get("label", ""), size=12, bold=True,
             align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.BOTTOM)
        text(slide, cx - step / 2 + Inches(0.05), y_line + Inches(0.3), step - Inches(0.1), Inches(2.2),
             c.get("event", ""), size=12, align=PP_ALIGN.CENTER)
    activity_band(slide, s)


def r_content(prs, s, lesson, demo):
    slide = frame(prs, s)
    h = BODY_H - (Inches(1.05) if s.get("activity_prompt") else 0)
    body_bullets(slide, s, h=h)
    activity_band(slide, s)


RENDER = {
    "title": r_title, "takeaway": r_takeaway, "chapter_map": r_chapter_map,
    "concept_cards": r_concept_cards, "checkpoint_mcq": r_mcq, "capstone_mcq": r_mcq,
    "mini_case": r_case, "opening_case": r_case, "urgency_sort": r_urgency,
    "match_activity": r_match, "timeline": r_timeline,
}


# --------------------------------------------------------------------------
# Package writers
# --------------------------------------------------------------------------
def build_deck(spec, out: Path, demo: bool) -> Path:
    prs = Presentation()
    prs.slide_width, prs.slide_height = W, H
    lesson = spec["lesson"]
    slides = sorted((s for s in spec["slides"] if not s.get("retired")), key=lambda s: int(s["slide_number"]))
    for s in slides:
        RENDER.get(s.get("slide_archetype"), r_content)(prs, s, lesson, demo)
    prs.save(out)
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
            "course_objectives": L.get("course_objectives") or [], "matrix": rows, "unmapped_counts": unmapped}


def write_manifest_and_qa(spec, out: Path, defects: Defects, files: List[str], demo: bool) -> str:
    slides = [s for s in spec["slides"]]
    coverage = {fn: [s["slide_id"] for s in slides if not s.get("retired") and fn in (s.get("cjm_functions") or [])] for fn in CJM}
    all_defects = list(spec["qa"].get("defects") or []) + defects.items
    status = spec["qa"].get("release_status", "draft-only")
    if any(d["severity"] == "blocker" for d in all_defects):
        status = "blocked"
    elif any(d["severity"] == "major" for d in all_defects) and status == "release-ready":
        status = "faculty-review-needed"
    if demo:
        status = "draft-only" if status != "blocked" else status
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "generated_at_iso": datetime.now().isoformat(timespec="seconds"),
        "demo": demo,
        "runtime_config": spec["runtime_config"],
        "lesson": spec["lesson"],
        "sources": spec["sources"],
        "taxonomy": spec["taxonomy"],
        "slides": [{k: s.get(k) for k in ["slide_id", "slide_number", "slide_title", "slide_archetype", "concept_lane",
                                          "evidence_status", "source_refs", "cjm_functions", "target_duration_sec",
                                          "audio_duration_sec", "audio_filename", "qa_status", "retired"]} for s in slides],
        "cjm_coverage": coverage,
        "cjm_coverage_rationale": spec["qa"].get("cjm_coverage_rationale", ""),
        "qa": {"release_status": status, "gates_passed": (spec["qa"].get("gates_passed") or []) + ["deck_render", "package_manifest"],
               "defect_counts": {sev: sum(1 for d in all_defects if d["severity"] == sev) for sev in ("blocker", "major", "minor")}},
        "files": files,
        "revision_log": spec.get("revision_log") or [],
        "traceability": write_traceability(spec, out),
        "outcomes": spec.get("outcomes") or {},
        "improvement_log": spec.get("improvement_log") or [],
    }
    (out / "lesson_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    qa = [f"# QA Log — {spec['lesson']['lesson_title']}\n", f"**Release status:** `{status}`\n"]
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
        "audio_filename": "",
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
                   "opening_patient_question": "", "concept_lanes": lanes, "target_duration_minutes": 10},
        "sources": [{"source_id": "SRC01", "title": "Demo placeholder", "kind": "external", "license": "instructor-owned",
                     "locator": "n/a", "coverage_status": "absent"}],
        "taxonomy": {"glossary": [], "concept_tags": [], "outcome_tags": [], "nclex_client_needs": [],
                     "cjm_functions": CJM, "proposed_new_tags": []},
        "slides": [
            slide("S01", 1, "Title", "title", "opening", "cross-lane", "", [], "Demo title.", dur=20),
            slide("S02", 2, "Opening case", "opening_case", "opening", "cues",
                  "Recognize the cues that matter in a first look.", [], s, ["recognize cues"],
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
            slide("S09", 9, "Takeaway", "takeaway", "close", "cross-lane", "",
                  ["Notice", "Interpret", "Prioritize", "Act", "Evaluate"], "Close.", dur=30),
        ],
        "assessment_items": [],
        "remediation_map": [],
        "qa": {"release_status": "draft-only", "gates_passed": [], "defects": [],
               "cjm_coverage_rationale": "Demo package; coverage is illustrative."},
        "revision_log": [],
    }


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------
def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--spec", type=Path)
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--outdir", type=Path, required=True)
    a = ap.parse_args(argv)
    if bool(a.spec) == a.demo:
        ap.error("provide exactly one of --spec or --demo")
    spec = demo_spec() if a.demo else json.loads(a.spec.read_text(encoding="utf-8"))
    if a.demo:
        (a.outdir).mkdir(parents=True, exist_ok=True)
        (a.outdir / "lesson_spec.json").write_text(json.dumps(spec, indent=2), encoding="utf-8")
    a.outdir.mkdir(parents=True, exist_ok=True)

    defects = Defects()
    validate_spec(spec, defects)
    if defects.has("blocker") and any(d["slide_id"] == "-" and d["note"].startswith("missing top-level") for d in defects.items):
        for d in defects.items:
            print(f"[{d['severity'].upper()}] {d['slide_id']}: {d['note']}")
        return 2
    blocked = defects.has("blocker")
    name = deck_filename(spec, a.demo, blocked)
    build_deck(spec, a.outdir / name, a.demo)
    write_guides(spec, a.outdir, a.demo)
    n_items = write_assessment_map(spec, a.outdir)
    files = [name, "facilitator_guide.md", "learner_handout.md", "assessment_map.csv", "traceability_matrix.csv", "lesson_manifest.json", "qa_log.md"]
    status = write_manifest_and_qa(spec, a.outdir, defects, files, a.demo)
    print(f"deck: {a.outdir / name}")
    print(f"assessment rows: {n_items}")
    print(f"release status: {status}")
    for d in defects.items:
        print(f"[{d['severity'].upper()}] {d['slide_id']}: {d['note']}")
    return 1 if blocked else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
