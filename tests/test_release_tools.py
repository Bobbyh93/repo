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
    assert out["release_status_declared"] == "faculty-review-needed"
    assert len(out["approvals_missing"]) == 7
    assert spec.read_text() == before


def test_release_ready_requires_all_approvals_and_lock(tmp_path):
    spec = _copy_lesson(tmp_path)
    out = _rg(spec, "set-release", "release-ready", "--by", "Tester")
    assert out["release_status_computed"] == "faculty-review-needed"
    for key in gate.APPROVAL_KEYS:
        out = _rg(spec, "approve", key, "--by", "Tester", "--date", "2026-09-06")
    assert out["release_status_computed"] == "faculty-review-needed"  # lock still missing
    out = _rg(spec, "lock-taxonomy", "--by", "Tester")
    assert out["release_status_computed"] == "release-ready"
    assert out["approvals_missing"] == []
    data = json.loads(spec.read_text())
    assert len(data["governance"]["approval_log"]) == 7
    assert all(e["by"] == "Tester" for e in data["governance"]["approval_log"])
    # 7 approvals + set-release + lock, on top of whatever the lesson already had
    before = len(json.loads((REF / "lesson_spec.json").read_text()).get("revision_log") or [])
    assert len(data["revision_log"]) == before + 9
    deck = Path(out["deck"])
    assert deck.exists() and "_DRAFT" not in deck.name


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


def test_render_with_no_images_does_not_open_the_visual_gate(tmp_path, monkeypatch):
    """A PDF that rasterises to nothing must not report a passed visual gate."""
    sys.path.insert(0, str(SCRIPTS))
    import qa_visual
    out = tmp_path / "qa"; out.mkdir()
    monkeypatch.setattr(qa_visual.shutil, "which", lambda n: "/usr/bin/soffice")
    monkeypatch.setattr(qa_visual.subprocess, "run", lambda *a, **k: None)

    def fake_glob(self, pat):
        if pat == "*.pptx":
            return iter([tmp_path / "deck.pptx"])
        return iter([])
    monkeypatch.setattr(Path, "glob", fake_glob)
    report = {}
    qa_visual.render(tmp_path, out, 50, report)
    assert report["render"]["ran"] is False


def test_canvas_failure_path_does_not_write_upload_credentials(tmp_path, monkeypatch):
    """The Canvas pre-upload response carries signed upload params; only its
    shape may reach report.json, never its contents."""
    sys.path.insert(0, str(SCRIPTS))
    import qa_visual
    pkg = tmp_path / "package"; pkg.mkdir()
    (pkg / "x.imscc").write_bytes(b"zip")
    monkeypatch.setenv("CANVAS_BASE_URL", "https://canvas.example")
    monkeypatch.setenv("CANVAS_TOKEN", "tok")
    secret = {"id": 1, "pre_attachment": {"upload_params": {"Signature": "SIGNED-SECRET"}}}
    monkeypatch.setattr(qa_visual, "_canvas", lambda *a, **k: secret)
    report = {}
    qa_visual.canvas_import(pkg, "123", report)
    assert report["canvas_import"]["ran"] is False
    assert "SIGNED-SECRET" not in json.dumps(report)
    assert report["canvas_import"]["response_keys"] == ["id", "pre_attachment"]
