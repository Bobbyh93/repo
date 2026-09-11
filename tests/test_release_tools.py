"""lesson-release skill scripts: record_gate (approvals drive the computed
status), verify_sources (term overlap against a local chapter), qa_visual
(structural report even when rendering is unavailable)."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "harrity-lesson-builder-pipeline" / "scripts"
REF = ROOT / "lessons" / "openrn_hp_ch4"
sys.path.insert(0, str(SCRIPTS))

import record_gate  # noqa: E402
import validate_and_gate as gate  # noqa: E402


def _copy_lesson(tmp_path: Path) -> Path:
    dst = tmp_path / "lesson"
    dst.mkdir()
    shutil.copy(REF / "lesson_spec.json", dst / "lesson_spec.json")
    return dst / "lesson_spec.json"


def _rg(spec: Path, *args: str) -> dict:
    r = subprocess.run([sys.executable, str(SCRIPTS / "record_gate.py"), str(spec), *args], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout[r.stdout.index("{"):])


def test_status_is_read_only(tmp_path):
    spec = _copy_lesson(tmp_path)
    before = spec.read_text()
    out = _rg(spec, "--no-regate", "status")
    assert out["release_status_declared"] == "review-needed"
    assert "approvals_missing" not in out  # no sign-off workflow
    assert spec.read_text() == before


def test_release_ready_needs_no_sign_off(tmp_path):
    """A clean package reaches release-ready on set-release alone.

    There are no approval keys and no taxonomy lock; the reference lesson
    carries only minor defects, so nothing stands between it and release.
    """
    spec = _copy_lesson(tmp_path)
    out = _rg(spec, "set-release", "release-ready", "--by", "Tester")
    assert out["release_status_computed"] == "release-ready"
    assert out["defects"]["blocker"] == 0 and out["defects"]["major"] == 0
    deck = Path(out["deck"])
    assert deck.exists() and "_DRAFT" not in deck.name


def test_major_defect_still_downgrades_release_ready(tmp_path):
    """Defects are the only thing that can hold a package back."""
    spec_path = _copy_lesson(tmp_path)
    spec = json.loads(spec_path.read_text())
    spec["qa"]["release_status"] = "release-ready"
    spec["slides"][3]["concept_lane"] = "not-a-declared-lane"  # major defect
    spec_path.write_text(json.dumps(spec, indent=2))

    result = gate.run(json.loads(spec_path.read_text()), tmp_path / "pkg", demo=False)

    assert result["status"] == "review-needed"
    assert any(d["severity"] == "major" for d in result["defects"])


def test_approve_and_lock_commands_are_gone(tmp_path):
    spec = _copy_lesson(tmp_path)
    for argv in (["approve", "source_approved", "--by", "Tester"], ["lock-taxonomy", "--by", "Tester"]):
        r = subprocess.run([sys.executable, str(SCRIPTS / "record_gate.py"), str(spec), *argv],
                           capture_output=True, text=True)
        assert r.returncode != 0, f"{argv[0]} should no longer exist"


def test_promote_requires_source_refs_and_logs_evidence(tmp_path):
    spec = _copy_lesson(tmp_path)
    out = _rg(spec, "promote", "S05", "--to", "source-grounded", "--by", "Tester", "--evidence", "4.2 five functions verified")
    data = json.loads(spec.read_text())
    s05 = next(s for s in data["slides"] if s["slide_id"] == "S05")
    assert s05["evidence_status"] == "source-grounded" and "4.2 five functions" in s05["qa_notes"]
    assert out["evidence_status_counts"]["source-grounded"] == 1
    r = subprocess.run([sys.executable, str(SCRIPTS / "record_gate.py"), str(spec), "--no-regate", "promote", "S01",
                        "--to", "source-grounded", "--by", "T", "--evidence", "x"], capture_output=True, text=True)
    assert r.returncode != 0 and "no source_refs" in r.stderr


def test_verify_sources_against_local_html(tmp_path):
    spec = _copy_lesson(tmp_path)
    chapter = tmp_path / "ch4.html"
    chapter.write_text("""<html><body><h2>4.2 Family Structures</h2><p>A family is two or more people related by birth,
    marriage, or adoption residing together. Family of orientation and family of procreation. The five family functions are
    economic support, emotional support, socialization, control of sexuality and reproduction, and ascribed social status.
    Intimacy is mutually shared trust. Achieved status by effort.</p>
    <table><caption>Table 4.2 Examples of Modern Family Structures</caption><tr><th>Structure</th><th>Description</th></tr>
    <tr><td>Blended family</td><td>Two families joined</td></tr></table>
    <h2>4.6 Caregivers</h2><p>Caregiver role strain: anger, withdrawal, anxiety, depression, exhaustion, sleeplessness, irritability.
    Resources: day care, respite, residential, palliative care, Al-Anon, Nar-Anon, Sibshop. Family-centered care: respect, dignity,
    collaboration, empowerment, information sharing.</p></body></html>""")
    out = tmp_path / "verification"
    r = subprocess.run([sys.executable, str(SCRIPTS / "verify_sources.py"), str(spec), "--out", str(out), f"--html=SRC01={chapter}"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    v = json.loads((out / "verification.json").read_text())
    assert v["summary"]["sources"]["SRC01"]["tables"] == 1
    assert "Table 4.2" in v["summary"]["sources"]["SRC01"]["table_captions"][0]
    by_id = {x["id"]: x for x in v["results"] if x["kind"] == "slide"}
    assert by_id["S05"]["share"] > by_id["S08"]["share"]          # structure slide matches; ACE slide does not
    assert by_id["S05"]["best_section"].startswith("4.2")
    assert by_id["S08"]["suggestion"].startswith(("flag", "review"))
    assert (out / "verification_report.md").exists()
    assert (out / "sources" / "SRC01.txt").exists()


def test_verify_sources_without_text_flags_not_verifies(tmp_path):
    spec = _copy_lesson(tmp_path)
    out = tmp_path / "v"
    r = subprocess.run([sys.executable, str(SCRIPTS / "verify_sources.py"), str(spec), "--out", str(out)], capture_output=True, text=True)
    assert r.returncode == 0
    v = json.loads((out / "verification.json").read_text())
    assert all(x["suggestion"].startswith("flag: source text unavailable") for x in v["results"])


def test_qa_visual_structural_report(tmp_path):
    pkg = tmp_path / "package"
    shutil.copytree(REF / "package", pkg)
    r = subprocess.run([sys.executable, str(SCRIPTS / "qa_visual.py"), str(pkg)], capture_output=True, text=True)
    rep = json.loads((pkg / "qa_visual" / "report.json").read_text())
    assert rep["structural_pass"] is True and r.returncode == 0
    assert rep["slide_count"] == 20 and rep["cartridge"]["pass"]
    assert rep["canvas_import"]["ran"] is False
    assert "ran" in rep["render"]


def test_pre_removal_faculty_vocabulary_is_normalised_not_flagged(tmp_path):
    """A spec written before the sign-off workflow was retired still gates cleanly.

    Regression: normalise_governance() originally ran inside resolve_release_status(),
    i.e. after validate_spec(), so legacy values produced two MAJOR defects and an
    unknown-key MINOR even though the status resolved correctly.
    """
    spec_path = _copy_lesson(tmp_path)
    spec = json.loads(spec_path.read_text())
    spec["governance"]["promotion_state"] = "faculty_review"
    spec["governance"].setdefault("approvals", {})["faculty_approved"] = False
    spec["qa"]["release_status"] = "faculty-review-needed"
    spec_path.write_text(json.dumps(spec, indent=2))

    result = gate.run(json.loads(spec_path.read_text()), tmp_path / "pkg", demo=False)

    assert result["status"] == "review-needed"
    notes = [d["note"] for d in result["defects"] if d["severity"] in {"major", "blocker"}]
    assert not any("promotion_state" in n or "release_status" in n for n in notes), notes
    assert not any("faculty_approved" in d["note"] for d in result["defects"])
