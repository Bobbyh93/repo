"""Speaker-script quality for generated lessons, in the places the gate cannot see.

validate_and_gate.py exempts four archetypes from its 20-word script floor --
title, takeaway, chapter_map and clinical_question -- because a pre-v1 deck could
legitimately leave them blank. That exemption is how a two-word script ("Closing
frame.") sat in a shipped package while every gate run reported zero majors. The
gate cannot be tightened without failing older packages, so the floor for lessons
this repository generates lives here instead.

These tests also pin the split the generator depends on: the clinical sentences in
a script are the source topic's, interpolated verbatim, and everything the
generator writes around them is teaching frame that asserts nothing clinical.

    pytest -q tests/test_generated_scripts.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lessons"))

import build_from_topic as gen  # noqa: E402

TOPICS = json.loads(gen.TOPICS_PATH.read_text(encoding="utf-8"))
DISTRACTORS = TOPICS["shared_distractors"]
TOPIC_IDS = [t["id"] for t in TOPICS["topics"]]
BY_ID = {t["id"]: t for t in TOPICS["topics"]}

# Every slide gets a script a person could read aloud, including the four the gate
# exempts. Forty words is roughly seventeen seconds at the pipeline's 140 wpm --
# short for a slide, but well clear of a stub.
SCRIPT_FLOOR_WORDS = 40


@pytest.fixture(scope="module", params=TOPIC_IDS)
def spec(request):
    return gen.build(BY_ID[request.param], DISTRACTORS)


def test_every_slide_script_clears_the_floor(spec):
    short = [(s["slide_id"], s["slide_archetype"], len(s["speaker_script"].split()))
             for s in spec["slides"] if len(s["speaker_script"].split()) < SCRIPT_FLOOR_WORDS]
    assert not short, f"scripts under {SCRIPT_FLOOR_WORDS} words: {short}"


def test_the_gate_exempt_archetypes_are_the_ones_this_guards():
    """If the gate stops exempting these, this module has become redundant --
    which is worth knowing, not worth silently keeping."""
    sys.path.insert(0, str(ROOT / "skills" / "harrity-lesson-builder-pipeline" / "scripts"))
    import validate_and_gate as vg
    assert vg.NO_SCRIPT_ARCHETYPES == {"title", "takeaway", "chapter_map", "clinical_question"}


def test_teaching_slides_carry_the_source_sentence_verbatim(spec):
    """The clinical content of a teaching script is the topic's own wording.

    Paraphrasing it in the generator would be inventing clinical text, so the
    body is interpolated whole. This fails if anyone starts rewording it.
    """
    topic = BY_ID[spec["lesson"]["chapter_id"]]
    bodies = [s["body"] for s in topic["lessonSections"]]
    teaching = [s for s in spec["slides"]
                if s["slide_archetype"] == "concept_cards" and s["slide_title"] in
                {sec["heading"] for sec in topic["lessonSections"]}]
    assert len(teaching) == len(bodies)
    for slide, body in zip(teaching, bodies):
        assert body in slide["speaker_script"], slide["slide_id"]


def test_the_slides_that_must_carry_topic_wording_do(spec):
    """Frame-only scripts are legitimate on the map and the activity slides.

    They are not legitimate where the slide's job is to state the lesson's own
    content: the open, the organizing question, the first cue and the close all
    have to say the topic's words, or the deck is describing itself.
    """
    topic = BY_ID[spec["lesson"]["chapter_id"]]
    by_arch = {s["slide_archetype"]: s["speaker_script"] for s in spec["slides"]}

    assert topic["summary"] in by_arch["title"]
    for objective in topic["objectives"]:
        assert gen.lowered(objective) in by_arch["title"]
    assert topic["summary"] in by_arch["clinical_question"]
    assert topic["facts"][0]["cue"] in by_arch["opening_case"]
    assert topic["summary"] in by_arch["takeaway"]
    assert topic["focusedReview"][0] in by_arch["takeaway"]


def test_frame_sentences_make_no_clinical_claim():
    """The generator's own prose is checked by reading it, not by a regex.

    What is mechanical is that the frame is a fixed, reviewable set of strings
    rather than something assembled per topic: a reviewer can read LANE_ROLE and
    RISK_CLAUSE once and know what every lesson says.
    """
    assert set(gen.RISK_CLAUSE) == {"high", "elevated"}
    assert len(gen.LANE_ROLE) == 3
    for text in list(gen.RISK_CLAUSE.values()) + gen.LANE_ROLE:
        assert len(text.split()) >= 10


def test_rebuild_keeps_the_original_run_date(tmp_path):
    """Changing how a script reads must not rename every file in the package."""
    out = tmp_path / "lesson_spec.json"
    first = gen.build(BY_ID[TOPIC_IDS[0]], DISTRACTORS, "20200101")
    out.write_text(json.dumps(first), encoding="utf-8")
    assert gen.existing_run_date(out) == "20200101"
    second = gen.build(BY_ID[TOPIC_IDS[0]], DISTRACTORS, gen.existing_run_date(out) or gen.RUN_DATE)
    assert second["runtime_config"]["runtime"]["run_date_yyyymmdd"] == "20200101"


def test_existing_run_date_tolerates_a_missing_or_broken_spec(tmp_path):
    assert gen.existing_run_date(tmp_path / "absent.json") is None
    broken = tmp_path / "broken.json"
    broken.write_text("{not json", encoding="utf-8")
    assert gen.existing_run_date(broken) is None
    empty = tmp_path / "empty.json"
    empty.write_text("{}", encoding="utf-8")
    assert gen.existing_run_date(empty) is None


def test_spoken_counts_are_words_not_digits():
    assert gen.spoken(3) == "three"
    assert gen.spoken(11) == "11"
    for spec_ in (gen.build(BY_ID[t], DISTRACTORS) for t in TOPIC_IDS):
        title_script = spec_["slides"][0]["speaker_script"]
        assert " 3 " not in title_script and " 5 " not in title_script
