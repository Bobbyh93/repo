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
    # D1: approvals and the lock are sign-offs, not QA. The visual gate is still
    # outstanding, so release-ready is refused even with every human box ticked.
    assert out["release_status_computed"] == "faculty-review-needed"
    assert out["approvals_missing"] == []
    out = _rg(spec, "gate-pass", "visual_qa", "--by", "Tester", "--note", "deck opened")
    assert out["release_status_computed"] == "release-ready"
    data = json.loads(spec.read_text())
    assert len(data["governance"]["approval_log"]) == 7
    assert all(e["by"] == "Tester" for e in data["governance"]["approval_log"])
    # 7 approvals + set-release + lock + gate-pass, on top of the lesson's own log
    before = len(json.loads((REF / "lesson_spec.json").read_text()).get("revision_log") or [])
    assert len(data["revision_log"]) == before + 10
    deck = Path(out["deck"])
    assert deck.exists() and "_DRAFT" not in deck.name


def test_d3_gate_pass_refuses_an_unknown_gate_name(tmp_path):
    """D3: a typo'd gate name used to be recorded verbatim, so the operator saw
    a gate on file that no check would ever match. It must fail at the boundary,
    leave the spec untouched, and still be possible for a genuinely new gate."""
    spec = _copy_lesson(tmp_path)
    before = spec.read_text()
    r = subprocess.run([sys.executable, str(SCRIPTS / "record_gate.py"), str(spec), "--no-regate",
                        "gate-pass", "visaul_qa", "--by", "Tester"], capture_output=True, text=True)
    assert r.returncode != 0 and "unknown gate 'visaul_qa'" in r.stderr
    assert spec.read_text() == before
    out = _rg(spec, "--no-regate", "gate-pass", "peer_review", "--by", "Tester", "--new-gate")
    assert "peer_review" in out["gates_passed"]


def test_d3_status_never_implies_it_recomputed(tmp_path):
    """D3: with no package on disk `status` printed the declared release status
    and omitted release_status_computed, which reads as agreement. It must say
    outright that nothing was recomputed."""
    spec = _copy_lesson(tmp_path)          # copied alone; no package/ beside it
    out = _rg(spec, "status")
    assert out["release_status_computed"] == "not recomputed (no package directory)"


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


# --- D6: a cache of unknown or partial completeness -------------------------
# The suite always handed verify_sources a whole chapter. It never handed it the
# state a blocked proxy actually leaves behind: a cache holding part of the
# source, which on the next run is indistinguishable from a complete one.

def _partial_cache(tmp_path: Path, sid: str = "SRC01") -> Path:
    """Two sections of the chapter downloaded; the rest did not."""
    out = tmp_path / "v"
    (out / "sources").mkdir(parents=True)
    (out / "sources" / f"{sid}.txt").write_text(
        "## https://example.org/4-2\n4.2 Family Structures\nA family is two or more people related by "
        "birth, marriage, or adoption residing together.\n", encoding="utf-8")
    return out


def test_d6_partial_cache_is_reported_as_partial_not_as_a_source(tmp_path):
    """D6: the provenance of a partial fetch ("3/12 urls") lived only in the
    string returned by that run. The next run read the cache and reported
    `cache <path>`, so a verification against a fragment of the chapter looked
    exactly like one against the whole of it."""
    spec = _copy_lesson(tmp_path)
    out = _partial_cache(tmp_path)
    r = subprocess.run([sys.executable, str(SCRIPTS / "verify_sources.py"), str(spec), "--out", str(out)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    v = json.loads((out / "verification.json").read_text())
    src = v["summary"]["sources"]["SRC01"]
    assert src["complete"] is False
    assert "PARTIAL" in src["how"]


def test_d6_low_overlap_against_a_partial_source_is_not_a_content_finding(tmp_path):
    """D6, the consequence: against a half-loaded chapter, "this claim is not in
    the source" and "the section holding it never downloaded" are the same
    number. Reporting the first is a fabricated finding against the lesson."""
    spec = _copy_lesson(tmp_path)
    out = _partial_cache(tmp_path)
    subprocess.run([sys.executable, str(SCRIPTS / "verify_sources.py"), str(spec), "--out", str(out)],
                   capture_output=True, text=True)
    v = json.loads((out / "verification.json").read_text())
    low = [x for x in v["results"] if x["share"] < 0.85]
    assert low, "fixture must produce low-overlap results to be decisive"
    assert all(x["suggestion"].startswith("cannot verify") for x in low), \
        [(x["id"], x["suggestion"]) for x in low][:5]


def test_d6_complete_source_still_reports_content_findings(tmp_path):
    """The inverse: the D6 fix must not mute real findings on a whole chapter.
    A supplied --html file is complete by construction, so a slide that is
    genuinely absent from it must still be flagged."""
    spec = _copy_lesson(tmp_path)
    chapter = tmp_path / "ch4.html"
    chapter.write_text("<html><body><h2>4.2 Family Structures</h2><p>A family is two or more people related "
                       "by birth, marriage, or adoption residing together.</p></body></html>", encoding="utf-8")
    out = tmp_path / "whole"
    subprocess.run([sys.executable, str(SCRIPTS / "verify_sources.py"), str(spec), "--out", str(out),
                    f"--html=SRC01={chapter}"], capture_output=True, text=True)
    v = json.loads((out / "verification.json").read_text())
    assert v["summary"]["sources"]["SRC01"]["complete"] is True
    assert any(x["suggestion"].startswith(("flag", "review")) for x in v["results"])
    assert not any(x["suggestion"].startswith("cannot verify") for x in v["results"])


def test_d6_html_override_writes_its_provenance_sidecar(tmp_path):
    """A cache is only trustworthy on the next run if its provenance was written
    with it; a sidecar-less cache must read as unknown, therefore incomplete."""
    spec = _copy_lesson(tmp_path)
    chapter = tmp_path / "ch.html"
    chapter.write_text("<html><body><p>A family is two or more people.</p></body></html>", encoding="utf-8")
    out = tmp_path / "p"
    subprocess.run([sys.executable, str(SCRIPTS / "verify_sources.py"), str(spec), "--out", str(out),
                    f"--html=SRC01={chapter}"], capture_output=True, text=True)
    prov = json.loads((out / "sources" / "SRC01.provenance.json").read_text())
    assert prov["complete"] is True and prov["origin"] == "html_override"


# --- D9: `visual_gate_ready` must mean the reviewer can see the deck --------

def test_d9_thumbnails_must_cover_every_slide(tmp_path, monkeypatch):
    """D9: `render.ran` only said the rasteriser produced at least one image.
    A render yielding 1 thumbnail for a 20-slide deck reported
    `visual_gate_ready: True` — and post-D1, that flag is what tells the
    operator the last gate standing between the package and release-ready can
    be recorded. It must require one thumbnail per slide."""
    sys.path.insert(0, str(SCRIPTS))
    import qa_visual
    report = {"slide_count": 20, "render": {"ran": True, "thumbnails": ["slide-01.png"]}}
    qa_visual.finalize(report)
    assert report["thumbnails_cover_deck"] is False
    assert report["visual_gate_ready"] is False
    assert "20-slide deck" in report["render"]["reason"]


def test_d9_zero_slides_is_not_a_rendered_deck(tmp_path):
    """Zero thumbnails for zero slides is vacuously equal. An empty deck is not
    a deck a reviewer has seen."""
    sys.path.insert(0, str(SCRIPTS))
    import qa_visual
    report = {"slide_count": 0, "render": {"ran": True, "thumbnails": ["slide-01.png"]}}
    qa_visual.finalize(report)
    assert report["visual_gate_ready"] is False
    report2 = {"slide_count": 0, "render": {"ran": True, "thumbnails": []}}
    qa_visual.finalize(report2)
    assert report2["visual_gate_ready"] is False


def test_d9_full_render_still_opens_the_gate(tmp_path):
    """The inverse guard: a complete render must still report ready."""
    sys.path.insert(0, str(SCRIPTS))
    import qa_visual
    report = {"slide_count": 3, "render": {"ran": True, "thumbnails": ["a.png", "b.png", "c.png"]}}
    qa_visual.finalize(report)
    assert report["thumbnails_cover_deck"] is True and report["visual_gate_ready"] is True


def test_d9_end_to_end_empty_deck_does_not_open_the_visual_gate(tmp_path):
    """D9 through the CLI, which is where the defect was reproduced: before the
    fix this package reported `visual_gate_ready: True` for a deck holding no
    slides, because LibreOffice emits one blank page and `ran` only counted
    images. The unit cases above fail on the old code for want of `finalize`;
    this one fails on the old behaviour."""
    from pptx import Presentation
    pkg = tmp_path / "package"
    shutil.copytree(REF / "package", pkg)
    Presentation().save(str(next(pkg.glob("*.pptx"))))          # a deck with no slides
    m = json.loads((pkg / "lesson_manifest.json").read_text(encoding="utf-8"))
    m["slides"] = []
    (pkg / "lesson_manifest.json").write_text(json.dumps(m), encoding="utf-8")
    r = subprocess.run([sys.executable, str(SCRIPTS / "qa_visual.py"), str(pkg)], capture_output=True, text=True)
    rep = json.loads((pkg / "qa_visual" / "report.json").read_text())
    assert rep["slide_count"] == 0
    assert rep["visual_gate_ready"] is False
    assert r.returncode != 0
