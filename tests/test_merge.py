"""WP-1 merge exit criteria, executable.

Runs the gate + adapter + canonical renderer on three inputs and checks:
  1. gate demo (schema v1.2)          -> renders, draft-only, no blockers
  2. migrated legacy chapter 1 (v1.0) -> renders, blocked, _DRAFT stamped
  3. original renderer demo (legacy)  -> renders through the gate, all 26
                                          renderer archetypes survive
Every deck must open with python-pptx with a slide count equal to the
manifest's active slide count.

    pytest -q tests/
"""
from __future__ import annotations

import json
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "harrity-lesson-builder-pipeline" / "scripts"
FIXTURES = ROOT / "fixtures"
sys.path.insert(0, str(SCRIPTS))

import generate_lesson_package as renderer  # noqa: E402
import spec_adapter  # noqa: E402
import validate_and_gate as gate  # noqa: E402

from pptx import Presentation  # noqa: E402


def _open_package(outdir: Path):
    manifest = json.loads((outdir / "lesson_manifest.json").read_text(encoding="utf-8"))
    decks = list(outdir.glob("*.pptx"))
    assert len(decks) == 1, decks
    assert zipfile.ZipFile(decks[0]).testzip() is None
    prs = Presentation(str(decks[0]))
    active = [s for s in manifest["slides"] if not s.get("retired")]
    assert len(prs.slides) == len(active)
    for f in manifest["files"]:
        assert (outdir / f).exists(), f
    for name in ("facilitator_guide.md", "learner_handout.md", "assessment_map.csv",
                 "traceability_matrix.csv", "qa_log.md"):
        assert (outdir / name).exists()
    return manifest, decks[0], prs


def _unified_validator(outdir: Path) -> int:
    return subprocess.call([sys.executable, str(SCRIPTS / "validate_unified_package.py"), str(outdir)])


def test_archetype_union_covers_both_sides():
    assert gate.V11_ARCHETYPES <= gate.ARCHETYPES
    assert set(renderer.RENDERERS) <= gate.ARCHETYPES
    # every renderer type is reachable from the adapter
    for t in renderer.RENDERERS:
        assert t in spec_adapter.RENDERER_CONTENT_KEYS, t


def test_case1_gate_demo(tmp_path):
    out = tmp_path / "demo"
    result = gate.run(gate.demo_spec(), out, demo=True)
    assert result["exit"] == 0
    manifest, deck, prs = _open_package(out)
    assert deck.name.startswith("DEMO_") and "_DRAFT" not in deck.name
    assert manifest["qa"]["release_status"] == "draft-only"
    assert manifest["qa"]["defect_counts"]["blocker"] == 0
    assert manifest["governance"]["envelope"] == "master-lesson-1.0.0"
    # five-channel separation: every slide carries its script in the notes slide
    for s in prs.slides:
        assert s.has_notes_slide and s.notes_slide.notes_text_frame.text.strip()
    # v1.1 card_data shapes reach the renderer: MCQ correct answer in notes
    mcq = [s for s in prs.slides][6]
    assert "CORRECT: B" in mcq.notes_slide.notes_text_frame.text
    assert _unified_validator(out) == 0


def test_case2_migrated_ch1_blocks_and_stamps_draft(tmp_path):
    spec = json.loads((FIXTURES / "ch1_migrated_lesson_spec.json").read_text(encoding="utf-8"))
    out = tmp_path / "ch1"
    result = gate.run(spec, out, demo=False)
    assert result["exit"] == 1 and result["blocked"]
    manifest, deck, prs = _open_package(out)
    assert "_DRAFT" in deck.name
    assert manifest["qa"]["release_status"] == "blocked"
    notes = [d["note"] for d in result["defects"] if d["severity"] == "blocker"]
    assert any("organizing_clinical_question" in n for n in notes)
    assert len(prs.slides) == 18
    assert _unified_validator(out) == 0


def test_case3_original_demo_through_gate(tmp_path):
    legacy = json.loads((FIXTURES / "renderer_legacy_demo_spec.json").read_text(encoding="utf-8"))
    spec = spec_adapter.legacy_to_spec(legacy)
    out = tmp_path / "legacy"
    result = gate.run(spec, out, demo=True)
    assert result["exit"] == 0, [d for d in result["defects"] if d["severity"] == "blocker"]
    manifest, deck, prs = _open_package(out)
    assert len(prs.slides) == 26
    kinds = {s["slide_archetype"] for s in manifest["slides"]}
    assert kinds == set(renderer.RENDERERS) - {"generic"}, kinds
    # the gate must flag what the original never checked: no verbatim scripts
    majors = [d["note"] for d in result["defects"] if d["severity"] == "major"]
    assert any("speaker_script under 20 words" in n for n in majors)
    assert _unified_validator(out) == 0


def test_governance_downgrades_unapproved_release_ready(tmp_path):
    spec = gate.demo_spec()
    spec["qa"]["release_status"] = "release-ready"
    result = gate.run(spec, tmp_path / "gov", demo=False)
    assert result["status"] == "review-needed"
    assert any("release-ready claimed without approvals" in d["note"] for d in result["defects"])


def test_governance_release_ready_with_full_approvals(tmp_path):
    spec = gate.demo_spec()
    spec["qa"]["release_status"] = "release-ready"
    spec["governance"] = {"promotion_state": "release_ready",
                          "approvals": {k: True for k in gate.APPROVAL_KEYS},
                          "taxonomy_lock": {"status": "locked", "approved_by": "Reviewer", "approval_date": "2026-09-06"}}
    result = gate.run(spec, tmp_path / "gov2", demo=False)
    assert result["status"] == "release-ready", result["defects"]


def test_evidence_gate_blocks_unsourced_claim(tmp_path):
    spec = gate.demo_spec()
    spec["slides"][3]["evidence_status"] = "source-grounded"  # source_refs is empty
    result = gate.run(spec, tmp_path / "ev", demo=False)
    assert result["blocked"]
    assert any("source-grounded with empty source_refs" in d["note"] for d in result["defects"])
    assert "_DRAFT" in Path(result["deck"]).name


def test_renderer_own_demo_still_runs(tmp_path):
    out = tmp_path / "orig"
    files = renderer.generate_package(renderer.make_demo_spec(), out)
    prs = Presentation(files["deck"])
    assert len(prs.slides) == 26
