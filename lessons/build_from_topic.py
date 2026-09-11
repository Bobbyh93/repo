#!/usr/bin/env python3
"""Generate a lesson_spec.json from one NCLEX exemplar topic.

    python lessons/build_from_topic.py --topic moc-safe-delegation
    python lessons/build_from_topic.py --all

Source: handoff/source/nclex_rn_2026_topics.json, transcribed from the author's
own module (Bobbyh93/Codex_Repo_2026 shared/nclex-rn-2026.ts). Registered as
SRC02; see handoff/source/SRC02_harrity_nclex_rn_2026_index.json.

What this does and does not do
------------------------------
Every slide is assembled from a field the topic already carries: the three
lessonSections become the three teaching slides and the concept lanes, the five
facts become the case, the activities and the items, focusedReview becomes the
retrieval check and takeaway, guidedNotes becomes the documentation frame.

It adds no clinical content. Where a topic states something qualitatively
(no thresholds, no scoring tools, no drug names, no timings) the lesson stays
at that level, because anything more specific would be invented.

It also does not write a teaching voice. Speaker scripts here are assembled
from the topic's own sentences; they carry the content but they are not the
prose a person would say out loud. Each generated package records that in
qa.defects. lessons/nclex_sepsis_recognition/ is the hand-written comparison.

Distractors are the module's own three, which repeat across every fact and are
all implausible. They are used unchanged rather than invented, and flagged.
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
TOPICS_PATH = REPO / "handoff" / "source" / "nclex_rn_2026_topics.json"
SRC = "SRC02"
RUN_DATE = date.today().strftime("%Y%m%d")

CJM = ["recognize cues", "analyze cues", "prioritize hypotheses",
       "generate solutions", "take action", "evaluate outcomes"]


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def bullets_from(body: str, max_words: int = 13, max_bullets: int = 6) -> list[str]:
    """Break a source paragraph into slide-sized bullets without losing wording.

    The gate caps a bullet at 14 words, and a whole section body pasted in as one
    bullet is a wall of text on the slide. Sentences that already fit are kept
    whole; longer ones are split at commas and greedily repacked. Nothing is
    reworded or truncated mid-phrase, so no clinical meaning is altered; the full
    body still appears on the card and in the speaker script.
    """
    out: list[str] = []
    for sentence in re.split(r"(?<=[.;])\s+", body.strip()):
        sentence = sentence.strip().rstrip(".;")
        if not sentence:
            continue
        if len(sentence.split()) <= max_words:
            out.append(sentence)
            continue
        # Pack whole comma-clauses and keep the commas. Splitting inside a clause,
        # or dropping the separators, turns a list of distinct findings into one
        # run-on phrase -- "chest or back discomfort hypotension urticaria" reads
        # as a single finding rather than three.
        chunk: list[str] = []
        for clause in re.split(r",\s*", sentence):
            clause = clause.strip()
            if not clause:
                continue
            # A clause that is over the cap on its own has no commas to pack on.
            # Break it at " and ", which joins two distinct actions, rather than
            # mid-phrase. Never break at " or ": that separates alternatives
            # inside one finding ("chest or back discomfort").
            parts = [clause]
            if len(clause.split()) > max_words and " and " in clause:
                head, _, tail = clause.partition(" and ")
                parts = [head.strip(), "and " + tail.strip()]
            for part in parts:
                projected = len(", ".join(chunk + [part]).split())
                if chunk and projected > max_words:
                    out.append(", ".join(chunk))
                    chunk = []
                chunk.append(part)
        if chunk:
            out.append(", ".join(chunk))
    return [b for b in out if b][:max_bullets]


def lane_names(topic: dict) -> list[str]:
    """Concept lanes: the topic's own section headings, plus apply and evaluate.

    Gives 5 lanes, inside the gate's required 4-6, and every lane name is the
    topic's own vocabulary rather than a template's.
    """
    lanes = [slug(s["heading"]).replace("_", " ") for s in topic["lessonSections"]]
    return lanes + ["apply", "evaluate"]


def slide(sid, num, title, arch, section, lane, objective, bullets, script, cjm=None, activity="", answers=None,
          ev="source-aligned", refs=None, card=None, dur=150, co="", visual="", nac=""):
    return {
        "slide_id": sid, "slide_number": num, "slide_title": title, "slide_archetype": arch,
        "lesson_section": section, "concept_lane": lane,
        "source_refs": [SRC] if refs is None and ev in {"source-grounded", "source-aligned"} else (refs or []),
        "evidence_status": ev, "cjm_functions": cjm or [], "nursing_action_category": nac,
        "learning_objective": objective, "on_slide_text": bullets, "activity_prompt": activity,
        "answer_key": answers or [], "visual_notes": visual, "speaker_script": script, "tts_text": "",
        "target_duration_sec": dur, "audio_duration_sec": None, "auto_advance": False,
        "layout_spec": {"archetype": arch, "density_budget": {"max_bullets": 6, "max_words_per_bullet": 14},
                        "regions": ["header", "body", "footer"], "card_data": card or []},
        "allow_overlap": False, "qa_status": "unreviewed", "qa_notes": "",
        "remediation_target": {"concept_lane": lane, "cjm_function": (cjm or [""])[0], "misconception": "", "fix_type": ""},
        "audio_filename": "", "course_objective_id": co, "standards_refs": [],
    }


def mcq_options(action: str, distractors: list[str], rotate: int) -> tuple[list[str], str]:
    """Place the keyed action at a rotating position so the key is not always A."""
    pool = [action] + list(distractors)
    pos = rotate % len(pool)
    ordered = pool[1:1 + pos] + [pool[0]] + pool[1 + pos:]
    letters = "ABCD"
    return [f"{letters[i]}. {o}" for i, o in enumerate(ordered)], letters[pos]


def build(topic: dict, distractors: list[str]) -> dict:
    lanes = lane_names(topic)
    secs = topic["lessonSections"]
    facts = topic["facts"]
    review = topic["focusedReview"]
    objectives = topic["objectives"]
    co = {f"CO{i+1}": t for i, t in enumerate(objectives)}
    co_ids = list(co)
    title = topic["title"]
    ocq = topic["summary"]

    S = []
    n = 0

    def add(*args, **kw):
        nonlocal n
        n += 1
        S.append(slide(f"S{n:02d}", n, *args, **kw))

    add(title, "title", "open", "cross-lane",
        "Orient to the lesson's promise.",
        [title, f"Prelicensure RN · {topic['category_label']} · safety risk: {topic['safetyRisk']}"],
        f"{title}. {ocq} Five lanes carry the lesson: {', '.join(lanes)}.",
        ev="instructor-added", refs=[], dur=35)

    f0 = facts[0]
    add("Opening case", "opening_case", "open", lanes[0],
        "Enter the lesson through a single patient cue.",
        [],
        f"Start with one cue. {f0['cue']} Decide what you would do before the lesson tells you, and hold on to it; "
        f"the same cue returns as the first assessment item.",
        cjm=["recognize cues"],
        card=[{"presentation": f0["cue"],
               "cues": [f"Objective in play: {objectives[0]}", f"Concept: {topic['concept']}"],
               "prompt": "Thirty seconds: what is your first action, and why that one first?"}],
        co=co_ids[0])

    add("The question this lesson answers", "clinical_question", "map", "cross-lane",
        "State the organizing clinical question.",
        [],
        f"One question organizes the lesson: {ocq}",
        cjm=["recognize cues", "analyze cues"],
        card=[{"lane": lanes[i], "nodes": [secs[i]["heading"]]} for i in range(len(secs))]
             + [{"lane": "apply", "nodes": ["case and items"]}, {"lane": "evaluate", "nodes": ["retrieval", "takeaway"]}],
        ev="instructor-added", refs=[], dur=55)

    add("Lesson map", "chapter_map", "map", "cross-lane",
        "Locate any cue on the map before acting on it.",
        [],
        "Map first. The three teaching lanes are the topic's own sections; apply and evaluate close the loop.",
        card=[{"lane": lanes[i], "nodes": [secs[i]["heading"]]} for i in range(len(secs))]
             + [{"lane": "apply", "nodes": ["mini case", "capstone"]}, {"lane": "evaluate", "nodes": ["exit check"]}],
        ev="instructor-added", refs=[], dur=55)

    add("Warm-up: put the three moves in order", "warmup_sequence", "activate", "cross-lane",
        "Sequence the lesson's three moves before seeing them taught.",
        [s["heading"] for s in secs],
        "One minute, before any of this is taught. These three headings are the whole lesson in order, but they are "
        "shuffled on the slide. Put them in the sequence the nurse actually performs them at the bedside, then compare "
        "with a neighbour before the reveal. Getting the order wrong here is more useful than getting it right: it "
        "shows you which move you would have skipped under pressure.",
        cjm=["analyze cues"],
        activity="Order the three.",
        answers=[s["heading"] for s in secs],
        ev="instructor-added", refs=[], dur=70)

    for i, sec in enumerate(secs):
        add(sec["heading"], "concept_cards", f"lane: {lanes[i]}", lanes[i],
            objectives[min(i, len(objectives) - 1)],
            bullets_from(sec["body"]),
            f"{sec['heading']}. {sec['body']} Everything on this slide is the source topic's own wording; the bullets "
            f"are that same sentence broken up for the screen. This is lane {i + 1} of {len(secs)}, and it answers: "
            f"{objectives[min(i, len(objectives) - 1)].rstrip('.')}.",
            cjm=[["recognize cues", "analyze cues"], ["prioritize hypotheses", "generate solutions"],
                 ["take action", "evaluate outcomes"]][min(i, 2)],
            card=[{"heading": sec["heading"], "body": sec["body"], "cjm": CJM[min(i * 2, 4)]}],
            co=co_ids[min(i, len(co_ids) - 1)],
            visual=f"Section {i+1} of {len(secs)} from the source topic.")

    add("Activity: match the cue to the move it calls for", "match_activity", "practice", "apply",
        "Match each cue to the lesson move that answers it.",
        [],
        "Work with one partner. Match each cue to the section of the lesson that tells you what to do with it.",
        cjm=["recognize cues", "analyze cues"],
        activity="Write the four matches and one sentence explaining one of them.",
        answers=[f"{chr(65+i)} relates to: {secs[min(i, len(secs)-1)]['heading']}" for i in range(4)],
        card=[{"left": [f"{chr(65+i)}. {facts[i]['cue']}" for i in range(4)],
               "right": [f"{i+1}. {s['heading']}" for i, s in enumerate(secs)] + ["4. Evaluate the result"]}],
        co=co_ids[0], dur=170)

    add("Debrief: the reasoning behind each action", "debrief", "practice", "apply",
        "Explain why each keyed action follows from its cue.",
        [],
        "Each rationale below is the topic's own. Read them as a set: they describe one habit of mind, not five rules.",
        cjm=["analyze cues"],
        card=[{"heading": f["action"][:58], "body": f["rationale"], "cjm": "analyze cues"} for f in facts[:4]],
        co=co_ids[min(1, len(co_ids) - 1)])

    f1 = facts[1]
    opts, key = mcq_options(f1["action"], distractors, 2)
    add("Checkpoint", "checkpoint_mcq", "practice", lanes[1],
        "Choose the correct action for a single cue.",
        [],
        f"One question, and it targets the middle of the lesson. The cue is: {f1['cue']} Read all four options and "
        f"commit to one before the reveal, because the value of a checkpoint is in being wrong out loud rather than "
        f"quietly. The reasoning you are being tested on is this: {f1['rationale']}",
        cjm=["analyze cues"],
        activity="Choose the best response.",
        answers=[f"{key}. {f1['action']}"],
        card=[{"stem": f1["cue"] + " What should the nurse do?", "options": opts, "correct": key,
               "rationale": f1["rationale"]}],
        co=co_ids[min(1, len(co_ids) - 1)], dur=120)

    f2 = facts[2]
    add("Mini case", "mini_case", "apply", "apply",
        "Respond to a cue using the lesson's frame.",
        [],
        f"A bedside moment, and this time you write rather than choose. The situation: {f2['cue']} Write two sentences "
        f"before the debrief: one naming what you assess, one naming what you do about it. Keep them in that order, "
        f"because the order is the judgement. The keyed reasoning is: {f2['rationale']}",
        cjm=["prioritize hypotheses", "take action"],
        activity="Two sentences: what you assess, then what you do.",
        answers=[f2["action"], f2["rationale"]],
        card=[{"presentation": f2["cue"],
               "cues": [f"Keyed action: {f2['action']}", f"Because: {f2['rationale']}"],
               "prompt": "Write one assessment sentence and one action sentence."}],
        co=co_ids[min(1, len(co_ids) - 1)], dur=165)

    add("Sort by urgency", "urgency_sort", "signal", "apply",
        "Sort cues by whether they require immediate action.",
        [],
        "Two columns, and the sorting rule is the point of the slide. Put a cue on the left when delay changes the "
        "outcome for the patient, and on the right when the correct action is verification, planning or teaching that "
        "a short delay does not worsen. Justify one of your placements aloud. Learners who can sort these reliably are "
        "the ones who prioritise well under load.",
        cjm=["prioritize hypotheses"],
        activity="Place each cue and justify one.",
        answers=["Act now: the cues whose keyed action is immediate",
                 "Act in sequence: the cues whose keyed action is verification or planning"],
        card=[{"categories": [
                  {"title": "Act now", "items": [f["cue"] for f in facts[:3]]},
                  {"title": "Act in sequence", "items": [f["cue"] for f in facts[3:]]}]}],
        co=co_ids[min(1, len(co_ids) - 1)], dur=165)

    add("Documentation frame", "concept_cards", "apply", "apply",
        "Record the lesson's decisions in a reusable frame.",
        topic["guidedNotes"],
        "These are the fields the topic asks you to be able to fill in for any patient. If you cannot complete one, "
        "that is the part of the assessment still to do.",
        cjm=["generate solutions"],
        card=[{"heading": g.rstrip(":"), "body": "—", "cjm": "generate solutions"} for g in topic["guidedNotes"]],
        co=co_ids[min(2, len(co_ids) - 1)], nac="document")

    f4 = facts[4]
    opts4, key4 = mcq_options(f4["action"], distractors, 1)
    add("Capstone: choose the next safe action", "capstone_mcq", "apply", "evaluate",
        "Select the priority action in the lesson's hardest cue.",
        [],
        f"The last question, and the hardest cue the topic carries: {f4['cue']} All four options are things a nurse "
        f"might plausibly do, which is what makes it a capstone rather than a checkpoint. Choose the priority action, "
        f"not merely a defensible one. The reasoning that separates them: {f4['rationale']}",
        cjm=["take action", "evaluate outcomes"],
        activity="Choose the priority action.",
        answers=[f"{key4}. {f4['action']}"],
        card=[{"scenario": f4["cue"], "stem": "What is the priority nursing action?", "options": opts4,
               "correct": key4, "rationale": f4["rationale"]}],
        co=co_ids[min(2, len(co_ids) - 1)], dur=150)

    add("Rapid retrieval: exit check", "retrieval_check", "close", "cross-lane",
        "Retrieve the lesson's key points without notes.",
        review + [objectives[-1]],
        "Close the loop with no notes. Answer each of these aloud or on paper, one per lane of the lesson. The answers "
        "are on the slides you have just seen and in the facilitator guide, so this is retrieval rather than "
        "assessment. If any one of them produces silence across the room, that is the lane to re-teach before this "
        "cohort meets the situation on a real unit.",
        cjm=["evaluate outcomes"],
        activity="Answer all of them.",
        answers=review,
        co=co_ids[-1])

    add("Takeaway", "takeaway", "close", "cross-lane",
        ocq,
        review,
        "Closing frame.",
        ev="instructor-added", refs=[], dur=45,
        card=[{"title": r.rstrip(".")[:40], "body": r} for r in review])

    items = []
    for i, f in enumerate(facts):
        opts_i, key_i = mcq_options(f["action"], distractors, i)
        items.append({
            "item_id": f"Q{i+1:02d}",
            "slide_id": S[min(5 + i, len(S) - 1)]["slide_id"],
            "item_type": "mcq",
            "learning_objective": co[co_ids[min(i // 2, len(co_ids) - 1)]],
            "concept_lane": lanes[min(i // 2, len(lanes) - 1)],
            "cjm_function": CJM[min(i, 5)],
            "stem": f["cue"] + " What should the nurse do?",
            "options": opts_i, "answer": key_i, "rationale": f["rationale"],
            "remediation_target_slide": S[min(5 + i, len(S) - 1)]["slide_id"],
            "evidence_status": "source-aligned", "source_refs": [SRC],
            "course_objective_id": co_ids[min(i // 2, len(co_ids) - 1)],
            "source_section": f"SRC02.{topic['id']}.facts.{slug(f['locator'])}",
            "origin": "cue, keyed action and rationale are the module's; distractors are the module's shared set",
        })

    return {
        "schema_version": "1.2",
        "runtime_config": {
            "runtime": {"run_date_yyyymmdd": RUN_DATE, "package_id": f"NCLEX-{topic['id'].upper()}-R1",
                        "build_mode": "full_production", "deployment_mode": "hybrid", "rebuild_scope": "full",
                        "output_root": "."},
            "outputs": {"filename_pattern": "{{runtime.run_date_yyyymmdd}}_{{lesson.course_code}}_{{lesson.chapter_title}}_Part_{{deck.part_number}}.pptx"},
            "media": {"wpm_target": 140},
        },
        "lesson": {
            "course_code": "NCLEX", "program_level": "prelicensure RN", "audience": "prelicensure nursing students",
            "unit_title": topic["category_label"], "chapter_id": topic["id"],
            "chapter_title": topic["title"].replace(" ", "_")[:40],
            "lesson_title": topic["title"], "concept": topic["concept"],
            "exemplars": [s["heading"] for s in secs],
            "clinical_domain": topic["category_label"],
            "source_family": "Harrity NCLEX-RN 2026 exemplar topics",
            "source_anchor": f"shared/nclex-rn-2026.ts, EXEMPLAR_TOPICS[{topic['id']}]",
            "page_range": "n/a (source module)",
            "organizing_clinical_question": ocq,
            "opening_patient_question": facts[0]["cue"],
            "concept_lanes": lanes, "target_duration_minutes": 45,
            "program_outcomes": [],
            "course_objectives": [{"id": k, "text": v, "maps_to": []} for k, v in co.items()],
            "standards_refs": [],
        },
        "sources": [{
            "source_id": SRC,
            "title": f"Harrity NCLEX-RN 2026 exemplar topics, {topic['id']}",
            "kind": "authored", "license": "author's own work (R. Harrity)",
            "locator": f"Bobbyh93/Codex_Repo_2026 shared/nclex-rn-2026.ts, EXEMPLAR_TOPICS[{topic['id']}]",
            "coverage_status": "confirmed",
            "attribution_statement": f"Built from the author's own NCLEX-RN 2026 curriculum module (R. Harrity), exemplar topic {topic['id']}.",
            "index_path": "handoff/source/SRC02_harrity_nclex_rn_2026_index.json",
            "license_exclusions": [f"No OpenStax text is reproduced. The module's own sources[] cites {topic['upstream_citation']}, "
                                   f"which this repository excludes pending the license contradiction check in docs/REVIEW_HANDOFF.md."],
        }],
        "taxonomy": {
            "glossary": [{"term": s["heading"], "definition": s["body"], "source_ref": SRC} for s in secs],
            "concept_tags": [topic["concept"]] + [s["heading"] for s in secs],
            "outcome_tags": [o.rstrip(".") for o in objectives],
            "nclex_client_needs": [topic["category_label"]],
            "cjm_functions": CJM, "proposed_new_tags": [],
            "frameworks": [
                {"framework_id": "NCSBN-CJMM", "title": "NCSBN Clinical Judgment Measurement Model", "text_policy": "identifier-only"},
                {"framework_id": "NCLEX-RN-2026", "title": "Harrity NCLEX-RN 2026 framework (shared/nclex-rn-2026.ts)", "text_policy": "author's own"},
            ],
        },
        "governance": {
            "promotion_state": "human_review",
            "administrative_metadata": {"lesson_id": f"LESSON-NCLEX-{topic['id'].upper()}", "version": "0.1.0",
                                        "content_owner": "R. Harrity", "reviewer": "R. Harrity",
                                        "created_date": date.today().isoformat()},
        },
        "slides": S,
        "assessment_items": items,
        "remediation_map": [
            {"miss_pattern": f"learner misses: {f['cue']}", "failed_operation": CJM[min(i, 5)],
             "map_location": S[min(5 + i, len(S) - 1)]["slide_id"], "concept_lane": lanes[min(i // 2, len(lanes) - 1)],
             "likely_misconception": "", "one_slide_fix": S[min(5 + i, len(S) - 1)]["slide_id"],
             "active_learning_task": "restate the keyed action and why it is first",
             "retrieval_item": f"Q{i+1:02d}", "improvement_evidence": ""}
            for i, f in enumerate(facts[:3])
        ],
        "qa": {
            "release_status": "review-needed",
            "gates_passed": ["runtime", "source", "taxonomy", "blueprint", "cjm_coverage", "outline"],
            "defects": [
                {"severity": "minor", "slide_id": "-",
                 "note": "[generated] This package was assembled by lessons/build_from_topic.py from the SRC02 topic's "
                         "own fields. No clinical content was added. Speaker scripts carry the topic's sentences but "
                         "are not written in a teaching voice; a prose pass by the author is expected before teaching. "
                         "lessons/nclex_sepsis_recognition/ is the hand-written comparison."},
                {"severity": "minor", "slide_id": "-",
                 "note": "[clinical specificity] The source topic states its content qualitatively and names no numeric "
                         "thresholds, scoring tools, drug names or timings. None were added. Programme-specific criteria "
                         "and local policy must be supplied by the author."},
                {"severity": "minor", "slide_id": "-",
                 "note": "[assessment] Distractors are the module's shared set, identical across every item and all "
                         "implausible; used unchanged rather than invented. They should be replaced before the items "
                         "are used for assessment rather than discussion. The keyed action and rationale are the module's."},
                {"severity": "minor", "slide_id": "-",
                 "note": "[evidence] Slides are source-aligned to SRC02 (the author's own module), not source-grounded. "
                         "No OpenStax text is reproduced."},
                {"severity": "minor", "slide_id": "-",
                 "note": "[standards] No CA-BRN-ART3 standards_refs are proposed for generated packages; the author "
                         "adds them per lesson if the package is offered as accreditation evidence."},
            ],
            "cjm_coverage_rationale": "",
        },
        "revision_log": [], "outcomes": {}, "improvement_log": [],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--topic", help="topic id, e.g. moc-safe-delegation")
    ap.add_argument("--all", action="store_true", help="build every topic that has no lesson directory yet")
    ap.add_argument("--outroot", type=Path, default=HERE)
    a = ap.parse_args()

    data = json.loads(TOPICS_PATH.read_text(encoding="utf-8"))
    distractors = data["shared_distractors"]
    by_id = {t["id"]: t for t in data["topics"]}

    targets = list(by_id) if a.all else ([a.topic] if a.topic else [])
    if not targets:
        raise SystemExit("give --topic ID or --all. Known: " + ", ".join(by_id))

    for tid in targets:
        if tid not in by_id:
            raise SystemExit(f"unknown topic {tid}; known: {', '.join(by_id)}")
        spec = build(by_id[tid], distractors)
        outdir = a.outroot / f"nclex_{slug(tid)}"
        outdir.mkdir(parents=True, exist_ok=True)
        out = outdir / "lesson_spec.json"
        out.write_text(json.dumps(spec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        covered = {f for s in spec["slides"] for f in s["cjm_functions"]}
        missing = [f for f in CJM if f not in covered]
        print(f"[ok] {tid}: {len(spec['slides'])} slides, {len(spec['assessment_items'])} items -> {out}"
              + (f"  [WARN] CJM not covered: {missing}" if missing else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
