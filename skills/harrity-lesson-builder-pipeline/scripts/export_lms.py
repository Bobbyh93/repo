#!/usr/bin/env python3
"""LMS-neutral export for a gated lesson package (WP-3).

Emits, into the package directory:

  web/index.html            learner-facing lesson page (question, map, per-slide
                            text, activities without answer keys, attribution)
  web/learner_handout.html  same content as learner_handout.md, as HTML
  <stem>.imscc              IMS Common Cartridge 1.1 containing the two HTML
                            pages and a QTI 1.2 assessment built from
                            assessment_items[] (CC assessment profile)
  <stem>.pdf                deck PDF via LibreOffice when available; skipped
                            with a logged defect otherwise

Design rules:
* Learner-facing only inside the cartridge: no speaker scripts, no answer
  keys, no facilitator guide. Those stay in the package directory. QTI
  items carry their correct answer and rationale because the LMS grades
  and reveals them under its own policy.
* No learner identifiers exist anywhere in the spec, so none can be emitted.
* The cartridge name carries the same _DRAFT stamp as the deck.
* `validate_cartridge()` is the structural check the exit criterion asks
  for: zip integrity, well-formed manifest, every resource href present,
  every organization item resolving to a resource, the QTI resource typed
  as a CC assessment and parseable with one item per assessment item.

This module has no dependency beyond the standard library.
"""
from __future__ import annotations

import html
import re
import shutil
import subprocess
import tempfile
import uuid
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from xml.etree import ElementTree as ET

CC_NS = "http://www.imsglobal.org/xsd/imsccv1p1/imscp_v1p1"
LOM_NS = "http://ltsc.ieee.org/xsd/imsccv1p1/LOM/manifest"
QTI_NS = "http://www.imsglobal.org/xsd/ims_qtiasiv1p2"
CC_ASSESSMENT_TYPE = "imsqti_xmlv1p2/imscc_xmlv1p1/assessment"
OPTION_PREFIX = re.compile(r"^\s*([A-Ha-h])\s*[.):\-]\s+")


def _e(s: Any) -> str:
    return html.escape(str(s if s is not None else ""), quote=True)


def _ident(prefix: str, s: str) -> str:
    return prefix + re.sub(r"[^A-Za-z0-9_\-]", "_", s)


# --------------------------------------------------------------------------
# HTML
# --------------------------------------------------------------------------
_CSS = """
body{font-family:Georgia,serif;max-width:52rem;margin:2rem auto;padding:0 1rem;line-height:1.5;color:#1a1a1a}
h1{font-size:1.8rem}h2{margin-top:2rem;border-bottom:1px solid #b8bec7;padding-bottom:.2rem}
.meta{color:#6a6a6a;font-size:.9rem}.lanes{display:flex;gap:.5rem;flex-wrap:wrap;margin:1rem 0}
.lane{background:#eff2f6;border:1px solid #b8bec7;border-radius:.4rem;padding:.3rem .6rem}
.activity{background:#fff6d6;border-left:4px solid #d8b33c;padding:.5rem .8rem;margin:.6rem 0}
.tag{font-size:.75rem;color:#6a6a6a}.attrib{margin-top:3rem;font-size:.85rem;color:#444;border-top:1px solid #b8bec7;padding-top:.8rem}
"""


def _page(title: str, body: str) -> str:
    return (f'<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{_e(title)}</title><style>{_CSS}</style></head><body>{body}</body></html>')


def _attribution(spec: Dict[str, Any]) -> str:
    lines = [s.get("attribution_statement") for s in spec.get("sources") or [] if s.get("attribution_statement")]
    if not lines:
        return ""
    return '<div class="attrib"><strong>Attribution</strong><ul>' + "".join(f"<li>{_e(a)}</li>" for a in lines) + "</ul></div>"


def write_html(spec: Dict[str, Any], outdir: Path, demo: bool) -> List[str]:
    L = spec["lesson"]
    web = outdir / "web"
    web.mkdir(parents=True, exist_ok=True)
    slides = sorted((s for s in spec["slides"] if not s.get("retired")), key=lambda s: int(s["slide_number"]))
    banner = '<p class="meta"><strong>DEMO / illustrative content. Does not imply course-source support.</strong></p>' if demo else ""

    parts = [f"<h1>{_e(L['lesson_title'])}</h1>", banner,
             f'<p class="meta">{_e(L.get("course_code", ""))} · {_e(L.get("unit_title", ""))} · {_e(L.get("chapter_title", ""))}</p>',
             f"<p><strong>Organizing clinical question:</strong> {_e(L.get('organizing_clinical_question', ''))}</p>",
             '<div class="lanes">' + "".join(f'<span class="lane">{_e(ln)}</span>' for ln in L.get("concept_lanes") or []) + "</div>"]
    for s in slides:
        if s.get("slide_archetype") == "title":
            continue
        parts.append(f'<h2 id="{_e(s["slide_id"])}">{_e(s["slide_title"])}</h2>')
        parts.append(f'<p class="tag">{_e(s.get("concept_lane", ""))} · {_e(s.get("evidence_status", ""))}'
                     + (f' · sources {_e(", ".join(s.get("source_refs") or []))}' if s.get("source_refs") else "") + "</p>")
        if s.get("learning_objective"):
            parts.append(f"<p><em>{_e(s['learning_objective'])}</em></p>")
        bullets = s.get("on_slide_text") or []
        if bullets:
            parts.append("<ul>" + "".join(f"<li>{_e(b)}</li>" for b in bullets) + "</ul>")
        for c in (s.get("layout_spec") or {}).get("card_data") or []:
            if not isinstance(c, dict):
                continue
            if c.get("heading") or c.get("title"):
                parts.append(f"<p><strong>{_e(c.get('heading') or c.get('title'))}</strong> {_e(c.get('body', ''))}</p>")
            elif c.get("lane"):
                parts.append(f"<p><strong>{_e(c['lane'])}</strong>: {_e(' → '.join(str(n) for n in c.get('nodes') or []))}</p>")
            elif c.get("presentation"):
                parts.append(f"<p>{_e(c['presentation'])}</p>")
                if c.get("cues"):
                    parts.append("<ul>" + "".join(f"<li>{_e(x)}</li>" for x in c["cues"]) + "</ul>")
            elif c.get("label"):
                parts.append(f"<p><strong>{_e(c['label'])}</strong> {_e(c.get('event') or c.get('body') or '')}</p>")
            elif c.get("stem"):
                parts.append(f"<p>{_e(c['stem'])}</p><ol type='A'>" + "".join(f"<li>{_e(OPTION_PREFIX.sub('', str(o), count=1))}</li>" for o in c.get("options") or []) + "</ol>")
            elif c.get("items") and not c.get("categories"):
                parts.append("<ul>" + "".join(f"<li>{_e(x)}</li>" for x in c["items"]) + "</ul>")
        if s.get("activity_prompt"):
            parts.append(f'<div class="activity"><strong>Try it:</strong> {_e(s["activity_prompt"])}</div>')
    parts.append(_attribution(spec))
    (web / "index.html").write_text(_page(L["lesson_title"], "".join(parts)), encoding="utf-8")

    hp = [f"<h1>{_e(L['lesson_title'])} — Learner Handout</h1>", banner,
          f"<p><strong>Clinical question:</strong> {_e(L.get('organizing_clinical_question', ''))}</p>",
          "<h2>The map</h2><p>" + _e(" → ".join(L.get("concept_lanes") or [])) + "</p>"]
    for s in slides:
        if s.get("slide_archetype") == "title":
            continue
        hp.append(f"<h2>{_e(s['slide_title'])}</h2>")
        if s.get("on_slide_text"):
            hp.append("<ul>" + "".join(f"<li>{_e(b)}</li>" for b in s["on_slide_text"]) + "</ul>")
        if s.get("activity_prompt"):
            hp.append(f'<div class="activity"><strong>Try it:</strong> {_e(s["activity_prompt"])}</div>')
    hp.append("<h2>Exit check</h2><p>For each concept lane, write one thing the nurse should <em>notice</em>, and one thing the nurse should <em>do</em>.</p>")
    hp.append(_attribution(spec))
    (web / "learner_handout.html").write_text(_page(L["lesson_title"] + " — handout", "".join(hp)), encoding="utf-8")
    return ["web/index.html", "web/learner_handout.html"]


# --------------------------------------------------------------------------
# QTI 1.2 (Common Cartridge assessment profile)
# --------------------------------------------------------------------------
def _split_options(options: List[str]) -> List[Tuple[str, str]]:
    out = []
    for i, o in enumerate(options or []):
        m = OPTION_PREFIX.match(str(o))
        letter = m.group(1).upper() if m else chr(ord("A") + i)
        out.append((letter, OPTION_PREFIX.sub("", str(o), count=1)))
    return out


def _qti_item(it: Dict[str, Any]) -> str:
    iid = _ident("", str(it.get("item_id", "Q")))
    title = _e(f"{it.get('item_id', '')} · {it.get('concept_lane', '')} · {it.get('cjm_function', '')}")
    itype = str(it.get("item_type", "mcq")).lower()
    stem = _e(it.get("stem", ""))
    rationale = _e(it.get("rationale", ""))
    opts = _split_options(it.get("options") or [])
    answer = str(it.get("answer", ""))
    parts = [f'<item ident="{iid}" title="{title}">']

    if itype in {"mcq", "sata"} and opts:
        profile = "cc.multiple_choice.v0p1" if itype == "mcq" else "cc.multiple_response.v0p1"
        card = "Single" if itype == "mcq" else "Multiple"
        parts.append(f'<itemmetadata><qtimetadata><qtimetadatafield><fieldlabel>cc_profile</fieldlabel><fieldentry>{profile}</fieldentry></qtimetadatafield></qtimetadata></itemmetadata>')
        parts.append(f'<presentation><material><mattext texttype="text/html">&lt;p&gt;{stem}&lt;/p&gt;</mattext></material>')
        parts.append(f'<response_lid ident="response1" rcardinality="{card}"><render_choice>')
        for letter, text in opts:
            parts.append(f'<response_label ident="{letter}"><material><mattext texttype="text/plain">{_e(text)}</mattext></material></response_label>')
        parts.append("</render_choice></response_lid></presentation>")
        correct = [a.strip().upper() for a in re.split(r"[,\s]+", answer) if a.strip()]
        parts.append('<resprocessing><outcomes><decvar maxvalue="100" minvalue="0" varname="SCORE" vartype="Decimal"/></outcomes>')
        parts.append('<respcondition continue="No"><conditionvar>')
        if itype == "mcq":
            parts.append(f'<varequal respident="response1">{_e(correct[0] if correct else "")}</varequal>')
        else:
            parts.append("<and>")
            for letter, _ in opts:
                if letter in correct:
                    parts.append(f'<varequal respident="response1">{letter}</varequal>')
                else:
                    parts.append(f'<not><varequal respident="response1">{letter}</varequal></not>')
            parts.append("</and>")
        parts.append('</conditionvar><setvar action="Set" varname="SCORE">100</setvar>'
                     '<displayfeedback feedbacktype="Response" linkrefid="general_fb"/></respcondition></resprocessing>')
    else:
        # matching / ordering / short-answer / retrieval: essay profile, graded by the instructor
        parts.append('<itemmetadata><qtimetadata><qtimetadatafield><fieldlabel>cc_profile</fieldlabel><fieldentry>cc.essay.v0p1</fieldentry></qtimetadatafield></qtimetadata></itemmetadata>')
        body = stem
        if opts:
            body += " " + _e(" ".join(f"({l}) {t}" for l, t in opts))
        parts.append(f'<presentation><material><mattext texttype="text/html">&lt;p&gt;{body}&lt;/p&gt;</mattext></material>')
        parts.append('<response_str ident="response1" rcardinality="Single"><render_fib><response_label ident="answer" rshuffle="No"/></render_fib></response_str></presentation>')
        parts.append('<resprocessing><outcomes><decvar maxvalue="100" minvalue="0" varname="SCORE" vartype="Decimal"/></outcomes>'
                     '<respcondition continue="No"><conditionvar><other/></conditionvar>'
                     '<displayfeedback feedbacktype="Response" linkrefid="general_fb"/></respcondition></resprocessing>')
        rationale = _e(f"Expected answer: {answer}. ") + rationale
    parts.append(f'<itemfeedback ident="general_fb"><flow_mat><material><mattext texttype="text/html">&lt;p&gt;{rationale}&lt;/p&gt;</mattext></material></flow_mat></itemfeedback>')
    parts.append("</item>")
    return "".join(parts)


def qti_xml(spec: Dict[str, Any]) -> str:
    L = spec["lesson"]
    items = spec.get("assessment_items") or []
    aid = _ident("a_", (spec.get("runtime_config", {}).get("runtime") or {}).get("package_id") or L.get("lesson_title", "lesson"))
    title = _e(f"{L.get('lesson_title', 'Lesson')} — checkpoint")
    head = (f'<?xml version="1.0" encoding="UTF-8"?><questestinterop xmlns="{QTI_NS}" '
            f'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
            f'xsi:schemaLocation="{QTI_NS} http://www.imsglobal.org/xsd/ims_qtiasiv1p2p1.xsd">'
            f'<assessment ident="{aid}" title="{title}"><qtimetadata>'
            f'<qtimetadatafield><fieldlabel>cc_profile</fieldlabel><fieldentry>cc.exam.v0p1</fieldentry></qtimetadatafield>'
            f'<qtimetadatafield><fieldlabel>qmd_assessmenttype</fieldlabel><fieldentry>Examination</fieldentry></qtimetadatafield>'
            f'<qtimetadatafield><fieldlabel>qmd_scoretype</fieldlabel><fieldentry>Percentage</fieldentry></qtimetadatafield>'
            f'</qtimetadata><section ident="root_section">')
    return head + "".join(_qti_item(it) for it in items) + "</section></assessment></questestinterop>"


# --------------------------------------------------------------------------
# Common Cartridge 1.1
# --------------------------------------------------------------------------
def build_cartridge(spec: Dict[str, Any], outdir: Path, stem: str, html_files: List[str], demo: bool) -> Tuple[str, Dict[str, Any]]:
    L = spec["lesson"]
    cc_path = outdir / f"{stem}.imscc"
    man_id = _ident("m_", str(uuid.uuid4()))
    title = ("DEMO — " if demo else "") + L.get("lesson_title", "Lesson")
    items = spec.get("assessment_items") or []
    resources = [
        ("r_lesson", "webcontent", "web/index.html", ["web/index.html"], L.get("lesson_title", "Lesson")),
        ("r_handout", "webcontent", "web/learner_handout.html", ["web/learner_handout.html"], "Learner handout"),
    ]
    if items:
        resources.append(("r_quiz", CC_ASSESSMENT_TYPE, "quiz/assessment.xml", ["quiz/assessment.xml"], "Checkpoint quiz"))
    org_items = "".join(
        f'<item identifier="{_ident("i_", rid)}" identifierref="{rid}"><title>{_e(t)}</title></item>'
        for rid, _, _, _, t in resources)
    res_xml = "".join(
        f'<resource identifier="{rid}" type="{rtype}" href="{_e(href)}">' + "".join(f'<file href="{_e(f)}"/>' for f in files) + "</resource>"
        for rid, rtype, href, files, _ in resources)
    manifest = (f'<?xml version="1.0" encoding="UTF-8"?>'
                f'<manifest identifier="{man_id}" xmlns="{CC_NS}" xmlns:lomimscc="{LOM_NS}" '
                f'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
                f'xsi:schemaLocation="{CC_NS} http://www.imsglobal.org/profile/cc/ccv1p1/ccv1p1_imscp_v1p2_v1p0.xsd '
                f'{LOM_NS} http://www.imsglobal.org/profile/cc/ccv1p1/LOM/ccv1p1_lommanifest_v1p0.xsd">'
                f'<metadata><schema>IMS Common Cartridge</schema><schemaversion>1.1.0</schemaversion>'
                f'<lomimscc:lom><lomimscc:general><lomimscc:title><lomimscc:string>{_e(title)}</lomimscc:string></lomimscc:title>'
                f'<lomimscc:description><lomimscc:string>{_e(L.get("organizing_clinical_question", ""))}</lomimscc:string></lomimscc:description>'
                f'</lomimscc:general></lomimscc:lom></metadata>'
                f'<organizations><organization identifier="org_1" structure="rooted-hierarchy"><item identifier="root">'
                f'<item identifier="mod_1"><title>{_e(L.get("chapter_title") or L.get("lesson_title", ""))}</title>{org_items}</item>'
                f'</item></organization></organizations><resources>{res_xml}</resources></manifest>')
    with zipfile.ZipFile(cc_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("imsmanifest.xml", manifest)
        for f in html_files:
            z.write(outdir / f, f)
        if items:
            z.writestr("quiz/assessment.xml", qti_xml(spec))
    return cc_path.name, {"cartridge": "IMS Common Cartridge 1.1", "assessment": "QTI 1.2 (cc.exam.v0p1)" if items else None,
                          "resources": [r[0] for r in resources], "item_count": len(items)}


# --------------------------------------------------------------------------
# Structural validation
# --------------------------------------------------------------------------
def validate_cartridge(path: Path, expected_items: Optional[int] = None) -> List[str]:
    """Return a list of error strings; empty means the cartridge passed."""
    errors: List[str] = []
    try:
        z = zipfile.ZipFile(path)
    except zipfile.BadZipFile as exc:
        return [f"not a zip: {exc}"]
    if z.testzip() is not None:
        errors.append("zip integrity check failed")
    names = set(z.namelist())
    if "imsmanifest.xml" not in names:
        return errors + ["imsmanifest.xml missing"]
    try:
        root = ET.fromstring(z.read("imsmanifest.xml"))
    except ET.ParseError as exc:
        return errors + [f"imsmanifest.xml not well-formed: {exc}"]
    ns = {"cp": CC_NS}
    if root.tag != f"{{{CC_NS}}}manifest":
        errors.append(f"root element is {root.tag}, expected CC 1.1 manifest")
    if root.findtext("cp:metadata/cp:schemaversion", namespaces=ns) != "1.1.0":
        errors.append("metadata/schemaversion is not 1.1.0")
    res_ids = {}
    for r in root.findall("cp:resources/cp:resource", ns):
        rid = r.get("identifier")
        res_ids[rid] = r
        for f in r.findall("cp:file", ns):
            if f.get("href") not in names:
                errors.append(f"resource {rid} file missing from zip: {f.get('href')}")
        if r.get("href") and r.get("href") not in names:
            errors.append(f"resource {rid} href missing from zip: {r.get('href')}")
    if not res_ids:
        errors.append("no resources")
    for it in root.iter(f"{{{CC_NS}}}item"):
        ref = it.get("identifierref")
        if ref and ref not in res_ids:
            errors.append(f"organization item {it.get('identifier')} references unknown resource {ref}")
    if not root.findall("cp:organizations/cp:organization", ns):
        errors.append("no organization")
    quiz = [r for r in res_ids.values() if r.get("type") == CC_ASSESSMENT_TYPE]
    if expected_items:
        if not quiz:
            errors.append("no CC assessment resource although assessment items exist")
        else:
            href = quiz[0].get("href")
            try:
                q = ET.fromstring(z.read(href))
            except (KeyError, ET.ParseError) as exc:
                errors.append(f"QTI not readable: {exc}")
            else:
                if q.tag != f"{{{QTI_NS}}}questestinterop":
                    errors.append("QTI root is not questestinterop (QTI 1.2)")
                qitems = q.findall(f".//{{{QTI_NS}}}item")
                if len(qitems) != expected_items:
                    errors.append(f"QTI has {len(qitems)} items, expected {expected_items}")
                for qi in qitems:
                    if qi.find(f"{{{QTI_NS}}}presentation") is None or qi.find(f"{{{QTI_NS}}}resprocessing") is None:
                        errors.append(f"QTI item {qi.get('ident')} lacks presentation or resprocessing")
    return errors


# --------------------------------------------------------------------------
# PDF (best effort)
# --------------------------------------------------------------------------
def try_pdf(deck: Path, outdir: Path, timeout: int = 180) -> Optional[str]:
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        return None
    try:
        with tempfile.TemporaryDirectory() as prof:
            subprocess.run([soffice, f"-env:UserInstallation=file://{prof}", "--headless", "--convert-to", "pdf",
                            "--outdir", str(outdir), str(deck)], check=False, timeout=timeout,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except (subprocess.TimeoutExpired, OSError):
        return None
    pdf = outdir / (deck.stem + ".pdf")
    return pdf.name if pdf.exists() and pdf.stat().st_size > 0 else None


def export(spec: Dict[str, Any], outdir: Path, deck_name: str, demo: bool) -> Tuple[List[str], Dict[str, Any], List[str]]:
    """Run the whole export. Returns (files, export_manifest_section, warnings)."""
    warnings: List[str] = []
    stem = Path(deck_name).stem
    files = write_html(spec, outdir, demo)
    cc_name, info = build_cartridge(spec, outdir, stem, files, demo)
    files.append(cc_name)
    errs = validate_cartridge(outdir / cc_name, len(spec.get("assessment_items") or []))
    info["structural_validation"] = "pass" if not errs else "fail"
    info["errors"] = errs
    warnings.extend(f"cartridge: {e}" for e in errs)
    pdf = try_pdf(outdir / deck_name, outdir)
    if pdf:
        files.append(pdf)
        info["pdf"] = pdf
    else:
        info["pdf"] = None
        warnings.append("pdf export unavailable in this environment (LibreOffice missing or failed); deck PDF not produced")
    return files, info, warnings
