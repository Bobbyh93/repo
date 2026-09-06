"""WP-3 exit criteria: the gate emits an .imscc (Common Cartridge 1.1 + QTI 1.2)
and an HTML/PPTX bundle; the cartridge passes structural validation; the
manifest lists the .imscc in files[]; learner-facing exports carry no answer
keys or speaker scripts; a blocked package stamps the cartridge _DRAFT too.
"""
from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "harrity-lesson-builder-pipeline" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import export_lms  # noqa: E402
import validate_and_gate as gate  # noqa: E402

REF_SPEC = ROOT / "lessons" / "openrn_hp_ch4" / "lesson_spec.json"


def _run(spec, out, demo=False):
    result = gate.run(spec, out, demo=demo)
    manifest = json.loads((out / "lesson_manifest.json").read_text(encoding="utf-8"))
    return result, manifest


def test_reference_lesson_exports_cartridge_with_qti12(tmp_path):
    spec = json.loads(REF_SPEC.read_text(encoding="utf-8"))
    result, manifest = _run(spec, tmp_path / "ref")
    assert result["exit"] == 0
    cc = [f for f in manifest["files"] if f.endswith(".imscc")]
    assert len(cc) == 1 and "_DRAFT" not in cc[0]
    assert manifest["exports"]["structural_validation"] == "pass"
    assert manifest["exports"]["assessment"].startswith("QTI 1.2")
    assert export_lms.validate_cartridge(tmp_path / "ref" / cc[0], len(spec["assessment_items"])) == []
    z = zipfile.ZipFile(tmp_path / "ref" / cc[0])
    names = set(z.namelist())
    assert {"imsmanifest.xml", "web/index.html", "web/learner_handout.html", "quiz/assessment.xml"} <= names
    q = ET.fromstring(z.read("quiz/assessment.xml"))
    ns = {"q": export_lms.QTI_NS}
    items = q.findall(".//q:item", ns)
    assert len(items) == len(spec["assessment_items"])
    profiles = {f.text for f in q.findall(".//q:item//q:fieldentry", ns)}
    assert "cc.multiple_choice.v0p1" in profiles and "cc.multiple_response.v0p1" in profiles and "cc.essay.v0p1" in profiles
    # every HTML file the manifest lists exists and the web pages exist on disk too
    for f in manifest["files"]:
        assert (tmp_path / "ref" / f).exists(), f


def test_learner_facing_exports_carry_no_answers_or_scripts(tmp_path):
    spec = json.loads(REF_SPEC.read_text(encoding="utf-8"))
    _run(spec, tmp_path / "ref")
    for page in ("web/index.html", "web/learner_handout.html"):
        text = (tmp_path / "ref" / page).read_text(encoding="utf-8")
        assert "ANSWER KEY" not in text and "Answer key" not in text
        for s in spec["slides"]:
            for a in s.get("answer_key") or []:
                if len(a) > 20:  # single-letter keys cannot be tested for absence
                    assert a not in text, (page, a)
            script = s.get("speaker_script") or ""
            if len(script) > 60:
                assert script[:60] not in text, page
        for it in spec["assessment_items"]:
            assert it["rationale"][:40] not in text


def test_demo_without_items_has_no_quiz_resource(tmp_path):
    result, manifest = _run(gate.demo_spec(), tmp_path / "demo", demo=True)
    cc = [f for f in manifest["files"] if f.endswith(".imscc")][0]
    assert cc.startswith("DEMO_")
    assert manifest["exports"]["assessment"] is None
    assert export_lms.validate_cartridge(tmp_path / "demo" / cc) == []


def test_blocked_package_stamps_cartridge_draft(tmp_path):
    spec = json.loads((ROOT / "fixtures" / "ch1_migrated_lesson_spec.json").read_text(encoding="utf-8"))
    result, manifest = _run(spec, tmp_path / "ch1")
    assert result["blocked"]
    cc = [f for f in manifest["files"] if f.endswith(".imscc")][0]
    assert "_DRAFT" in cc
    assert export_lms.validate_cartridge(tmp_path / "ch1" / cc) == []


def test_validator_catches_broken_cartridge(tmp_path):
    bad = tmp_path / "bad.imscc"
    with zipfile.ZipFile(bad, "w") as z:
        z.writestr("imsmanifest.xml", f'<manifest xmlns="{export_lms.CC_NS}"><metadata><schemaversion>1.1.0</schemaversion></metadata>'
                                      '<organizations><organization identifier="o"><item identifier="i" identifierref="r_missing"/></organization></organizations>'
                                      '<resources><resource identifier="r_x" type="webcontent" href="x.html"><file href="x.html"/></resource></resources></manifest>')
    errs = export_lms.validate_cartridge(bad, expected_items=3)
    assert any("unknown resource" in e for e in errs)
    assert any("missing from zip" in e for e in errs)
    assert any("no CC assessment" in e for e in errs)
