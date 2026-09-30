"""Every lesson committed to lessons/ still gates clean.

tests/test_merge.py proves the pipeline works on three fixtures. Nothing proved
that the lessons this repository actually ships still pass it -- so a spec could
be edited, or the gate tightened, and the breakage would only surface the next
time someone rebuilt that lesson by hand. This closes that: each committed
lesson_spec.json is re-gated from scratch into a temp directory, and the package
that comes out is validated and opened.

Nothing here touches the committed packages. The gate writes only to its outdir.

    pytest -q tests/test_committed_lessons.py
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from pptx import Presentation

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "harrity-lesson-builder-pipeline" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import validate_and_gate as gate  # noqa: E402

LESSON_SPECS = sorted(ROOT.glob("lessons/*/lesson_spec.json"))
LESSON_IDS = [p.parent.name for p in LESSON_SPECS]

# A status the tooling will ship. "blocked" means a blocker defect; "draft-only"
# means the package was built in demo mode and is not a real lesson.
SHIPPABLE = {"release-ready", "review-needed"}


def test_there_are_lessons_to_check():
    """A glob that matches nothing would make every test below pass vacuously."""
    assert LESSON_SPECS, f"no lessons/*/lesson_spec.json under {ROOT}"


@pytest.fixture(scope="module", params=LESSON_SPECS, ids=LESSON_IDS)
def gated(request, tmp_path_factory):
    spec_path = request.param
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    outdir = tmp_path_factory.mktemp(spec_path.parent.name)
    result = gate.run(spec, outdir, demo=False)
    return spec_path, spec, outdir, result


def test_no_blocker_or_major_defects(gated):
    _, _, _, result = gated
    serious = [d for d in result["defects"] if d["severity"] in {"blocker", "major"}]
    assert not serious, "\n".join(f"[{d['severity']}] {d['slide_id']}: {d['note']}" for d in serious)


def test_status_is_shippable(gated):
    _, _, _, result = gated
    assert result["status"] in SHIPPABLE
    assert result["exit"] == 0


def test_deck_renders_with_every_slide(gated):
    _, spec, _, result = gated
    deck = Path(result["deck"])
    assert deck.exists()
    assert "_DRAFT" not in deck.name, "a blocker stamped the deck _DRAFT"
    assert len(Presentation(str(deck)).slides) == len(spec["slides"])


def test_package_validates(gated):
    _, _, outdir, _ = gated
    proc = subprocess.run([sys.executable, str(SCRIPTS / "validate_unified_package.py"), str(outdir)],
                          capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "[PASS]" in proc.stdout


def test_gating_does_not_touch_the_repository(gated):
    """The gate writes to outdir only; a lesson directory must come out unchanged."""
    spec_path, _, _, _ = gated
    proc = subprocess.run(["git", "status", "--porcelain", "--", str(spec_path.parent)],
                          cwd=ROOT, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == "", f"gating dirtied the working tree:\n{proc.stdout}"
