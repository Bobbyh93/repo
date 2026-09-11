#!/usr/bin/env python3
"""Build lesson_spec.json for the NCLEX exemplar lesson: sepsis recognition.

Source: the author's own curriculum module, `shared/nclex-rn-2026.ts` in
Bobbyh93/Codex_Repo_2026, exemplar topic `pa-sepsis-recognition` ("Early
Recognition and Escalation of Sepsis", category physiological-adaptation,
safetyRisk high, releaseStage clinical_review). Registered as SRC02 in
handoff/source/SRC02_harrity_nclex_rn_2026_index.json.

Why this source and not Open RN: the build container's egress proxy denies
every publisher host, so no Open RN chapter beyond ch4 can be obtained. This
module is the author's own work and needs no external fetch.

Two deliberate constraints, both logged in qa.defects:

1. The module states cues qualitatively -- "altered mentation, abnormal
   perfusion, respiratory change, hypotension, reduced urine output" -- and
   names no numeric thresholds, no scoring tool, and no bundle timing. This
   lesson does not add any. Inventing vital-sign cut-offs or hour-one targets
   would be fabricating clinical content the source does not carry.
2. The module's five facts share one set of three distractors, all obviously
   wrong (delay to end of shift / document without follow-up / delegate the
   judgement). Reused across every item they teach test-taking, not clinical
   judgement. The distractors here are instructor-written and plausible; the
   keyed action and rationale remain the module's.

    python lessons/nclex_sepsis_recognition/build_spec.py
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = "SRC02"
LANES = ["baseline", "cues", "meaning", "escalate", "evaluate"]
CJM = ["recognize cues", "analyze cues", "prioritize hypotheses",
       "generate solutions", "take action", "evaluate outcomes"]

OCQ = ("A patient who might have an infection is changing. Which changes mean the "
       "body is failing to perfuse, and what does the nurse do before anything else?")

COURSE_OBJECTIVES = {
    # The module's three objectives, verbatim in intent.
    "CO1": "Recognize clinical deterioration consistent with possible sepsis.",
    "CO2": "Prioritize immediate assessment and escalation.",
    "CO3": "Evaluate response to time-sensitive interventions.",
}


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


def item(iid, sid, itype, lane, cjm, stem, options, answer, rationale, target, co, section):
    return {"item_id": iid, "slide_id": sid, "item_type": itype,
            "learning_objective": COURSE_OBJECTIVES[co],
            "concept_lane": lane, "cjm_function": cjm, "stem": stem, "options": options, "answer": answer,
            "rationale": rationale, "remediation_target_slide": target, "evidence_status": "source-aligned",
            "source_refs": [SRC], "course_objective_id": co, "source_section": section,
            "origin": "keyed action and rationale from the SRC02 topic's facts[]; distractors instructor-written "
                      "(the module's shared distractors repeat across all items)"}


SLIDES = [
    slide("S01", 1, "From suspicion to escalation", "title", "open", "cross-lane",
          "Orient to the lesson's promise.",
          ["Early recognition and escalation of sepsis",
           "Prelicensure RN · Physiological Adaptation · high safety risk"],
          "This lesson is about a patient who might have an infection and is beginning to change. By the end you can name the "
          "changes that mean the body is failing to perfuse, say what the nurse does first, and describe how to tell whether "
          "it worked. This is a high-risk topic: the cost of noticing late is measured in organs.",
          ev="instructor-added", refs=[], dur=35),

    slide("S02", 2, "Opening case: the patient who got quiet", "opening_case", "open", "cues",
          "Enter the lesson through a patient whose only early cue is a change in mentation.",
          [],
          "Here is your patient. Treated for an infection, stable this morning, and now different. The nurse who walks in says "
          "the patient seems confused, and the blood pressure is lower than it has been. Nothing here is dramatic. There is no "
          "alarm. Notice what you already want to do with this information, and hold on to it: we will come back to this patient "
          "at the end and see whether your first instinct was the safe one.",
          cjm=["recognize cues"],
          card=[{"presentation": "Treated for a suspected infection. Stable this morning. The nurse reports that the patient "
                                 "now seems confused, and the blood pressure is below the patient's trend for the shift.",
                 "cues": ["Suspected infection", "New confusion in a previously oriented patient",
                          "Blood pressure below this patient's own trend",
                          "Not yet known: source, urine output, perfusion elsewhere"],
                 "prompt": "Thirty seconds: is this a call-now change or a watch-and-recheck change?"}],
          co="CO1", visual="Case card left, cues centre, task right."),

    slide("S03", 3, "The question this lesson answers", "clinical_question", "map", "cross-lane",
          "State the organizing clinical question.",
          [],
          "One question organizes everything that follows. A patient who might have an infection is changing: which changes mean "
          "the body is failing to perfuse, and what does the nurse do before anything else? Five lanes carry the answer, from "
          "what normal looks like through to whether your action worked.",
          cjm=["recognize cues", "analyze cues"],
          card=[{"lane": "baseline", "nodes": ["what perfusion does", "this patient's own trend"]},
                {"lane": "cues", "nodes": ["mentation", "perfusion", "breathing", "pressure", "urine output"]},
                {"lane": "meaning", "nodes": ["new organ dysfunction", "trend beats single value"]},
                {"lane": "escalate", "nodes": ["activate the pathway", "communicate", "stabilize"]},
                {"lane": "evaluate", "nodes": ["reassess", "escalate again if needed"]}],
          ev="instructor-added", refs=[], dur=55),

    slide("S04", 4, "Lesson map: normal, changed, meaning, act, check", "chapter_map", "map", "cross-lane",
          "Locate any sepsis cue on the map before acting on it.",
          [],
          "Map first. Normal on the left, the check on the right. Every cue you meet today belongs somewhere on this line, and "
          "knowing where it sits tells you what to do with it.",
          card=[{"lane": "baseline", "nodes": ["perfusion delivers oxygen", "the patient's own baseline"]},
                {"lane": "cues", "nodes": ["altered mentation", "abnormal perfusion", "respiratory change", "hypotension", "reduced urine output"]},
                {"lane": "meaning", "nodes": ["possible infection + new organ dysfunction", "urgency rises"]},
                {"lane": "escalate", "nodes": ["sepsis or rapid-response pathway", "trend and suspected source", "diagnostics", "stabilization"]},
                {"lane": "evaluate", "nodes": ["trend the same findings", "persistent deterioration escalates again"]}],
          ev="instructor-added", refs=[], dur=55,
          visual="Horizontal route, foundation left to evaluation right."),

    slide("S05", 5, "Warm-up: what has to happen first?", "warmup_sequence", "activate", "cross-lane",
          "Sequence the nurse's actions before seeing the answer.",
          ["Reassess and trend the response",
           "Notice a change in a patient who might have an infection",
           "Activate the pathway and begin stabilization",
           "Ask whether the change indicates organ dysfunction"],
          "One minute. Put these four in the order the nurse actually performs them. Do not overthink it, and do not look ahead. "
          "Compare with a neighbour before the reveal. The order matters more than the words.",
          cjm=["analyze cues"],
          activity="Place the four actions in order.",
          answers=["notice the change", "ask whether it indicates organ dysfunction",
                   "activate the pathway and begin stabilization", "reassess and trend the response"],
          ev="instructor-added", refs=[], dur=70),

    slide("S06", 6, "Baseline: what perfusion is for", "concept_cards", "lane: baseline", "baseline",
          "Explain why a perfusion failure shows up in several systems at once.",
          ["Perfusion delivers oxygen to tissue",
           "Organs announce failure in their own language",
           "Compare against this patient's own trend, not a textbook number"],
          "Before cues make sense, hold on to why they cluster. Perfusion is the delivery of oxygen to tissue. When delivery "
          "falls, every organ that depends on it starts to complain, and each one complains in its own language: the brain "
          "becomes confused, the kidney makes less urine, the lungs work harder. That is why sepsis is recognised as a pattern "
          "across systems rather than as one abnormal number. And the comparison that matters is with this patient's own "
          "earlier readings, not with a population normal.",
          cjm=["analyze cues"],
          card=[{"heading": "Brain", "body": "Altered mentation: new confusion, less responsive than earlier.", "cjm": "recognize cues"},
                {"heading": "Kidney", "body": "Reduced urine output.", "cjm": "recognize cues"},
                {"heading": "Lungs", "body": "Respiratory change.", "cjm": "recognize cues"},
                {"heading": "Circulation", "body": "Abnormal perfusion; hypotension.", "cjm": "recognize cues"}],
          co="CO1", visual="Four organ cards, one cue each."),

    slide("S07", 7, "Cues: the five the module names", "concept_cards", "lane: cues", "cues",
          "Name the cue families that, with possible infection, require urgent assessment.",
          ["Possible infection PLUS any new organ dysfunction",
           "Altered mentation · abnormal perfusion · respiratory change",
           "Hypotension · reduced urine output",
           "Any other new organ dysfunction counts"],
          "Here is the recognition rule in full. Possible infection, plus altered mentation, abnormal perfusion, respiratory "
          "change, hypotension, reduced urine output, or other new organ dysfunction, requires urgent assessment. Read the word "
          "'or' carefully. You are not waiting to collect the set. One new organ dysfunction in a patient who might be infected "
          "is the trigger.",
          cjm=["recognize cues"],
          card=[{"heading": "Altered mentation", "body": "New confusion or reduced responsiveness."},
                {"heading": "Abnormal perfusion", "body": "Skin and circulatory findings that differ from this patient's earlier state."},
                {"heading": "Respiratory change", "body": "A new change in the work or rate of breathing."},
                {"heading": "Hypotension", "body": "Blood pressure below this patient's trend."},
                {"heading": "Reduced urine output", "body": "Less urine than earlier in the shift."},
                {"heading": "Other new organ dysfunction", "body": "The list is not a closed set."}],
          co="CO1"),

    slide("S08", 8, "Activity: match the cue to the organ it speaks for", "match_activity", "practice", "meaning",
          "Match each observed cue to the system whose perfusion it reports on.",
          [],
          "Work with one partner. Match each cue on the left to the system it reports on. This is not trivia: naming the system "
          "is what turns a number into a statement about perfusion, and that is the step that makes you escalate.",
          cjm=["recognize cues", "analyze cues"],
          activity="Write A-? B-? C-? D-? and one sentence saying what the match tells you about perfusion.",
          answers=["A-2 new confusion reports on cerebral perfusion",
                   "B-3 falling urine output reports on renal perfusion",
                   "C-1 rising respiratory rate reports on the lungs and on compensation",
                   "D-4 hypotension reports on circulatory failure to maintain pressure"],
          card=[{"left": ["A. New confusion in a previously oriented patient", "B. Urine output falling across the shift",
                          "C. Respiratory rate rising", "D. Blood pressure below the patient's trend"],
                 "right": ["1. Lungs and compensation", "2. Brain", "3. Kidney", "4. Circulation"]}],
          co="CO1", dur=170),

    slide("S09", 9, "Debrief: why naming the system changes what you do", "debrief", "practice", "meaning",
          "Explain how each match raises or lowers urgency.",
          [],
          "Here is the reasoning behind each match. Notice that in every row the cue is only meaningful because it is new. A "
          "patient with long-standing renal impairment and a low urine output is telling you something different from the "
          "patient whose output fell this afternoon. New is the word that carries the urgency.",
          cjm=["analyze cues"],
          card=[{"heading": "A to 2 · brain", "body": "New confusion in possible infection is organ dysfunction, not just an anxious patient.", "cjm": "analyze cues"},
                {"heading": "B to 3 · kidney", "body": "Falling output suggests the kidney is not being perfused.", "cjm": "analyze cues"},
                {"heading": "C to 1 · lungs", "body": "A rising rate is often the earliest visible compensation.", "cjm": "analyze cues"},
                {"heading": "D to 4 · circulation", "body": "Hypotension means compensation is no longer keeping up.", "cjm": "analyze cues"}],
          co="CO1"),

    slide("S10", 10, "Trend beats any single value", "timeline", "lane: meaning", "meaning",
          "Justify using the trend rather than one reading.",
          ["One value is a snapshot; the trend is the story",
           "Combined movement in several systems raises urgency",
           "A value inside the normal range can still be a change"],
          "This is the discipline the module keeps returning to: trend changes rather than relying on one value. A single "
          "reading tells you where the patient is. Two readings tell you where the patient is going, and direction is what "
          "decides urgency. Two findings moving together, such as urine output falling while heart rate and respiratory rate "
          "rise, are a stronger signal than any one of them alone.",
          cjm=["analyze cues"],
          card=[{"label": "single value", "event": "a snapshot; may sit inside the normal range"},
                {"label": "two values", "event": "direction becomes visible"},
                {"label": "several systems", "event": "combined movement suggests worsening perfusion"},
                {"label": "urgency", "event": "direction, not the number, decides"}],
          co="CO1", visual="Left-to-right progression, urgency rising."),

    slide("S11", 11, "Checkpoint: the patient with a normal temperature", "checkpoint_mcq", "practice", "cues",
          "Reject the assumption that a normal temperature excludes sepsis.",
          [],
          "One question, and it targets the most common misconception in this topic. Read the options and commit before the "
          "reveal.",
          cjm=["analyze cues"],
          activity="Choose the best response.",
          answers=["C. Continue evaluating for sepsis using the complete clinical picture and organ-function findings."],
          card=[{"stem": "A patient has a possible infection but a temperature within the normal range. What is the best nursing response?",
                 "options": ["A. Document the normal temperature and recheck at the next scheduled vitals.",
                             "B. Rule out sepsis, since fever is required for the diagnosis.",
                             "C. Continue evaluating for sepsis using the complete clinical picture and organ-function findings.",
                             "D. Wait for the culture result before assessing further."],
                 "correct": "C",
                 "rationale": "A normal temperature does not exclude serious infection or sepsis. The evaluation rests on the "
                              "whole picture and on organ-function findings, not on one vital sign."}],
          co="CO1", dur=120),

    slide("S12", 12, "Meaning: new organ dysfunction raises urgency", "concept_cards", "lane: meaning", "meaning",
          "State the rule that converts a cue into an escalation.",
          ["Possible infection + new organ dysfunction = urgent",
           "The dysfunction does not have to be severe, only new",
           "Absence of fever does not lower the urgency"],
          "The conversion rule is short. Possible infection plus new organ dysfunction requires urgent assessment. Two words "
          "carry the weight. 'New' rules out the chronic finding you already knew about. 'Organ dysfunction' rules in the brain, "
          "the kidney, the lungs and the circulation, whichever of them is speaking. Nothing in that rule mentions temperature.",
          cjm=["prioritize hypotheses"],
          card=[{"heading": "New", "body": "Different from this patient's own earlier state.", "cjm": "analyze cues"},
                {"heading": "Organ dysfunction", "body": "Any system reporting a perfusion failure.", "cjm": "analyze cues"},
                {"heading": "Together", "body": "With possible infection, the two together mean urgent assessment now.", "cjm": "prioritize hypotheses"}],
          co="CO2"),

    slide("S13", 13, "Escalate: what the nurse actually does", "concept_cards", "lane: escalate", "escalate",
          "List the four components of escalation named by the module.",
          ["Activate the organisation's sepsis or rapid-response pathway",
           "Communicate the trend and the suspected source",
           "Obtain ordered diagnostics promptly",
           "Begin stabilization"],
          "Escalation is four things, and the module lists them as one movement rather than a sequence. Activate your "
          "organisation's sepsis or rapid-response pathway. Communicate the trend and the suspected source, not just the latest "
          "number. Obtain the ordered diagnostics promptly. And begin stabilization. Notice that the pathway is your "
          "organisation's: this lesson does not tell you which one, because that is local.",
          cjm=["generate solutions", "take action"],
          card=[{"heading": "Activate", "body": "The organisation's sepsis or rapid-response pathway."},
                {"heading": "Communicate", "body": "The trend and the suspected source."},
                {"heading": "Obtain", "body": "Ordered diagnostics, promptly."},
                {"heading": "Begin", "body": "Stabilization."}],
          co="CO2", nac="escalate",
          visual="Four cards, equal weight, no arrows: these are concurrent."),

    slide("S14", 14, "Escalation and stabilization happen together", "timeline", "lane: escalate", "escalate",
          "Reject the sequential reading in which one step waits for another.",
          ["Deterioration requires parallel action",
           "Do not wait passively for one step to finish",
           "Diagnostics and treatment are coordinated, not queued"],
          "This is the slide that most often changes practice. When cultures and treatment are pending and the patient is "
          "deteriorating, the nurse coordinates time-sensitive diagnostics and treatment while continuing stabilization and "
          "escalation. Deterioration requires parallel action rather than waiting passively for one step to finish. The "
          "sequential habit -- order it, wait for it, then act -- is the one to unlearn here.",
          cjm=["take action"],
          card=[{"label": "recognise", "event": "possible infection plus new organ dysfunction"},
                {"label": "activate + communicate", "event": "pathway and trend, together"},
                {"label": "diagnostics + stabilization", "event": "coordinated, not queued"},
                {"label": "reassess", "event": "continuous, not at the next scheduled check"}],
          co="CO2", nac="escalate"),

    slide("S15", 15, "What you hand over when you escalate", "concept_cards", "lane: escalate", "escalate",
          "Compose an escalation message carrying trend and suspected source.",
          ["The trend, not only the latest value",
           "The suspected source of infection",
           "Which organ systems are involved",
           "What you have already begun"],
          "When you make the call, the content matters. The module asks for the trend and the suspected source. That means the "
          "receiving clinician hears where the patient is going and why you think there is an infection, rather than a single "
          "number out of context. Add which systems are involved and what you have already started, so no one repeats your work.",
          cjm=["take action"],
          activity="Say it aloud in two sentences: trend, then suspected source.",
          answers=["Sentence one names what has changed and in which direction, across which systems.",
                   "Sentence two names the suspected source and what has already been started."],
          card=[{"heading": "Trend", "body": "What has changed, in which direction, over what period."},
                {"heading": "Suspected source", "body": "Why infection is suspected."},
                {"heading": "Systems", "body": "Which organs are reporting dysfunction."},
                {"heading": "Already begun", "body": "Diagnostics obtained, stabilization started."}],
          co="CO2", nac="communicate", ev="instructor-added", refs=[SRC],
          visual="Four cards; the first two are the module's, the last two are instructor additions."),

    slide("S16", 16, "Sort by urgency: which of these calls now?", "urgency_sort", "signal", "meaning",
          "Sort findings by whether they require immediate escalation.",
          [],
          "Drag these mentally into two columns. The left column is escalate now. The right is assess and keep trending. The "
          "test for the left column is the rule from slide twelve: possible infection plus something new.",
          cjm=["prioritize hypotheses"],
          activity="Place each finding in a column and justify one of them.",
          answers=["Escalate now: new confusion with possible infection; hypotension below the patient's trend; "
                   "falling urine output with rising heart and respiratory rate",
                   "Assess and keep trending: a single reading at the edge of normal with no change from baseline; "
                   "a long-standing finding that has not changed"],
          card=[{"categories": [
                    {"title": "Escalate now",
                     "items": ["New confusion in possible infection", "Hypotension below this patient's trend",
                               "Urine output falling while heart and respiratory rates rise"]},
                    {"title": "Assess and keep trending",
                     "items": ["One value at the edge of normal, unchanged from baseline",
                               "A chronic finding that has not moved"]}]}],
          co="CO2", dur=165),

    slide("S17", 17, "Mini case: the patient who does not improve", "mini_case", "apply", "evaluate",
          "Choose the response when the first intervention has not worked.",
          [],
          "Back to a bedside. Initial interventions are done and the blood pressure has not come up. Three columns: what you "
          "assess, what you say, and the error to avoid. Write a two-sentence response before the debrief.",
          cjm=["evaluate outcomes", "take action"],
          activity="Write two sentences: one assessment sentence, one escalation sentence.",
          answers=["Assessment names perfusion and the trend since the intervention.",
                   "Escalation states that hypotension persists and requests higher-level support."],
          card=[{"presentation": "Blood pressure remains low after initial interventions for suspected sepsis.",
                 "cues": ["Assess: perfusion, mentation, urine output, and the full trend since the intervention",
                          "Escalate: report immediately that hypotension persists; keep reassessing response",
                          "Avoid: reading a completed intervention as a resolved problem"],
                 "prompt": "Write two sentences: one assessment sentence, one escalation sentence."}],
          co="CO3", nac="escalate", dur=165),

    slide("S18", 18, "Capstone: choose the next safe action", "capstone_mcq", "apply", "evaluate",
          "Select the priority response to persistent hypotension after intervention.",
          [],
          "One question. It is the same patient from the mini case, and the options are all things a nurse might plausibly do.",
          cjm=["take action", "evaluate outcomes"],
          activity="Choose the priority action.",
          answers=["B. Escalate immediately and continue reassessing perfusion and treatment response."],
          card=[{"scenario": "Blood pressure remains low after initial interventions. The patient is more difficult to rouse than an hour ago.",
                 "stem": "What is the priority nursing action?",
                 "options": ["A. Recheck the blood pressure in thirty minutes to confirm the trend before calling.",
                             "B. Escalate immediately and continue reassessing perfusion and treatment response.",
                             "C. Document that interventions were completed as ordered and continue the current plan.",
                             "D. Reposition the patient and repeat the reading in the other arm before escalating."],
                 "correct": "B",
                 "rationale": "Persistent hypotension indicates ongoing instability and the need for higher-level support. "
                              "A, C and D all delay escalation while the patient continues to deteriorate; the added difficulty "
                              "rousing the patient is a second organ system reporting."}],
          co="CO3", dur=150),

    slide("S19", 19, "Rapid retrieval: five-item exit check", "retrieval_check", "close", "cross-lane",
          "Retrieve one point per lane without notes.",
          ["Name three of the cue families that pair with possible infection",
           "Which single word makes a finding count as organ dysfunction?",
           "Does a normal temperature reduce your concern? Why not?",
           "Name the four components of escalation",
           "What does persistent hypotension after intervention tell you?"],
          "Five questions, one per lane, answered aloud or on paper. If a lane produces silence, that is the lane to remediate "
          "before this cohort meets a real one.",
          cjm=["evaluate outcomes"],
          activity="Answer all five.",
          answers=["any three of: altered mentation, abnormal perfusion, respiratory change, hypotension, reduced urine output, other new organ dysfunction",
                   "'new' -- different from this patient's own earlier state",
                   "no; a normal temperature does not exclude serious infection or sepsis",
                   "activate the pathway, communicate trend and suspected source, obtain ordered diagnostics, begin stabilization",
                   "ongoing instability and the need for higher-level support; escalate and keep reassessing"],
          co="CO3"),

    slide("S20", 20, "Takeaway: notice, name, act together, check again", "takeaway", "close", "cross-lane",
          "Carry one frame to the bedside.",
          ["Notice: any new organ dysfunction in possible infection",
           "Name: which system, and in which direction",
           "Act together: escalate and stabilize in parallel",
           "Check again: reassess, and escalate again if it persists"],
          "Closing frame. The patient from the opening case had one cue and no alarm. That is what this looks like in real life.",
          ev="instructor-added", refs=[], dur=45,
          card=[{"title": "notice", "body": "possible infection plus anything new"},
                {"title": "name", "body": "which system is reporting, and which way it is moving"},
                {"title": "act together", "body": "pathway, communication, diagnostics and stabilization, in parallel"},
                {"title": "check again", "body": "trend the response; persistent deterioration escalates again"}]),
]

ITEMS = [
    item("Q01", "S07", "mcq", "cues", "recognize cues",
         "A patient being treated for a suspected infection develops new confusion, and the blood pressure is below the "
         "patient's trend for the shift. Which action should the nurse take first?",
         ["A. Activate urgent sepsis evaluation and assess airway, breathing, circulation, and perfusion.",
          "B. Reorient the patient and recheck the blood pressure at the next scheduled vitals.",
          "C. Request a sedation review, since new confusion is most often medication-related.",
          "D. Obtain a repeat blood pressure in the opposite arm before taking further action."], "A",
         "Possible infection with new organ dysfunction and hypotension requires immediate escalation. B and D delay "
         "recognition of a time-sensitive change; C attributes a perfusion cue to a cause not supported by the picture.",
         "S12", "CO1", "SRC02.facts.recognition"),

    item("Q02", "S10", "mcq", "meaning", "analyze cues",
         "Over one shift a patient's urine output falls while the heart rate and respiratory rate rise. How should the nurse "
         "interpret this combination?",
         ["A. The findings are unrelated and should be charted separately.",
          "B. The combined trend can signal worsening organ perfusion and should be reported promptly.",
          "C. The rising respiratory rate is the only finding that requires action.",
          "D. The findings are expected after a period of reduced oral intake and require no escalation."], "B",
         "The combined trend can signal worsening organ perfusion; the nurse reports the deterioration promptly and "
         "reassesses perfusion and the full vital-sign trend. Reading the findings separately, or attributing them to intake, "
         "loses the pattern that carries the urgency.",
         "S10", "CO1", "SRC02.facts.perfusion"),

    item("Q03", "S11", "mcq", "cues", "analyze cues",
         "A patient has a possible infection but a temperature within the normal range. What should the nurse do?",
         ["A. Rule out sepsis, since fever is required for the diagnosis.",
          "B. Continue evaluating for sepsis using the complete clinical picture and organ-function findings.",
          "C. Defer further assessment until a fever develops.",
          "D. Treat the normal temperature as evidence that the infection is resolving."], "B",
         "A normal temperature does not exclude serious infection or sepsis. Evaluation continues on the complete clinical "
         "picture and the organ-function findings.",
         "S12", "CO1", "SRC02.facts.variable_presentation"),

    item("Q04", "S14", "mcq", "escalate", "take action",
         "Ordered cultures and treatment are pending while a patient with suspected sepsis continues to deteriorate. Which "
         "action best reflects safe practice?",
         ["A. Wait for the culture result before beginning any further intervention.",
          "B. Complete the diagnostics first, then begin stabilization once results return.",
          "C. Coordinate time-sensitive diagnostics and treatment while continuing stabilization and escalation.",
          "D. Hold escalation until the full set of ordered tests has been collected."], "C",
         "Deterioration requires parallel action rather than waiting passively for one step to finish. A, B and D all treat "
         "the steps as a queue, which delays both diagnosis and treatment in a time-sensitive presentation.",
         "S14", "CO2", "SRC02.facts.time_sensitive"),

    item("Q05", "S18", "mcq", "evaluate", "evaluate outcomes",
         "Blood pressure remains low after initial interventions for suspected sepsis. What does this finding indicate, and "
         "what should the nurse do?",
         ["A. The interventions need more time; continue the current plan and recheck at the next scheduled vitals.",
          "B. Persistent hypotension indicates ongoing instability; escalate immediately and continue reassessing perfusion and response.",
          "C. The reading is likely inaccurate; repeat it before reporting anything.",
          "D. Document that the ordered interventions were completed and hand over at the end of the shift."], "B",
         "Persistent hypotension indicates ongoing instability and the need for higher-level support. The other options all "
         "delay escalation while the patient remains under-perfused.",
         "S17", "CO3", "SRC02.facts.reassessment"),

    item("Q06", "S07", "sata", "cues", "recognize cues",
         "A patient is being treated for a possible infection. Which new findings should prompt urgent assessment for sepsis? "
         "Select all that apply.",
         ["A. New confusion in a previously oriented patient", "B. Reduced urine output compared with earlier in the shift",
          "C. A long-standing finding that has not changed", "D. A new respiratory change",
          "E. Blood pressure below this patient's own trend"], "A, B, D, E",
         "Altered mentation, reduced urine output, respiratory change and hypotension are all named cue families, and each "
         "counts when it is new. C fails the test that makes a finding count: it is not new.",
         "S07", "CO1", "SRC02.lessonSections.recognize_change"),

    item("Q07", "S13", "sata", "escalate", "generate solutions",
         "A nurse is escalating a patient with suspected sepsis. Which actions belong to escalation as described in this "
         "lesson? Select all that apply.",
         ["A. Activate the organisation's sepsis or rapid-response pathway",
          "B. Communicate the trend and the suspected source",
          "C. Obtain the ordered diagnostics promptly",
          "D. Begin stabilization",
          "E. Wait for the rapid-response team before starting anything"], "A, B, C, D",
         "The module names activation, communication of trend and suspected source, prompt diagnostics, and beginning "
         "stabilization. E contradicts the parallel-action principle.",
         "S13", "CO2", "SRC02.lessonSections.escalate"),

    item("Q08", "S19", "mcq", "evaluate", "evaluate outcomes",
         "Which set of findings should the nurse trend when evaluating a patient's response to treatment for suspected sepsis?",
         ["A. Temperature alone, since it reflects the infection most directly.",
          "B. Mental status, perfusion, blood pressure, oxygenation, urine output, laboratory results, and response to treatment.",
          "C. Blood pressure alone, since hypotension drove the escalation.",
          "D. Whatever was abnormal at the time of escalation, and nothing further."], "B",
         "Evaluation trends mental status, perfusion, blood pressure, oxygenation, urine output, laboratory results and "
         "response to treatment, and escalates persistent deterioration. Narrowing to one value repeats the single-value "
         "error the lesson warns against.",
         "S19", "CO3", "SRC02.lessonSections.evaluate"),
]


def build() -> dict:
    return {
        "schema_version": "1.2",
        "runtime_config": {
            "runtime": {"run_date_yyyymmdd": "20260911", "package_id": "NCLEX-PA-SEPSIS-RECOGNITION-R1",
                        "build_mode": "full_production", "deployment_mode": "hybrid", "rebuild_scope": "full",
                        "output_root": "."},
            "outputs": {"filename_pattern": "{{runtime.run_date_yyyymmdd}}_{{lesson.course_code}}_{{lesson.chapter_title}}_Part_{{deck.part_number}}.pptx"},
            "media": {"wpm_target": 140},
        },
        "lesson": {
            "course_code": "NCLEX", "program_level": "prelicensure RN", "audience": "prelicensure nursing students",
            "unit_title": "Physiological Adaptation", "chapter_id": "pa-sepsis-recognition",
            "chapter_title": "Sepsis Recognition",
            "lesson_title": "Early Recognition and Escalation of Sepsis",
            "concept": "Perfusion and Infection",
            "exemplars": ["altered mentation", "reduced urine output", "persistent hypotension", "parallel escalation"],
            "clinical_domain": "physiological adaptation / reduction of risk potential",
            "source_family": "Harrity NCLEX-RN 2026 exemplar topics",
            "source_anchor": "shared/nclex-rn-2026.ts, EXEMPLAR_TOPICS[pa-sepsis-recognition]",
            "page_range": "n/a (source module)",
            "organizing_clinical_question": OCQ,
            "opening_patient_question": "He was fine this morning. Why does he seem confused now?",
            "concept_lanes": LANES, "target_duration_minutes": 50,
            "program_outcomes": [],
            "course_objectives": [{"id": k, "text": v, "maps_to": []} for k, v in COURSE_OBJECTIVES.items()],
            # Package-level CA BRN Article 3 refs, proposed by the builder. The author confirms.
            "standards_refs": [
                {"framework_id": "CA-BRN-ART3", "ref": "BRN-14",
                 "basis": "1426(b): nursing process and clinical judgment integrated explicitly (S08-S09 cue-to-meaning reasoning, full CJM coverage matrix)"},
                {"framework_id": "CA-BRN-ART3", "ref": "BRN-17",
                 "basis": "1426(f): assessment items and traceability matrix link evaluation to the three course objectives"},
            ],
        },
        "sources": [{
            "source_id": SRC,
            "title": "Harrity NCLEX-RN 2026 exemplar topics, pa-sepsis-recognition",
            "kind": "authored",
            "license": "author's own work (R. Harrity)",
            "locator": "Bobbyh93/Codex_Repo_2026 shared/nclex-rn-2026.ts, EXEMPLAR_TOPICS[pa-sepsis-recognition]",
            "coverage_status": "confirmed",
            "attribution_statement": "Built from the author's own NCLEX-RN 2026 curriculum module (R. Harrity), "
                                     "exemplar topic pa-sepsis-recognition.",
            "index_path": "handoff/source/SRC02_harrity_nclex_rn_2026_index.json",
            "license_exclusions": ["No OpenStax text is reproduced. The module's own sources[] entry cites OpenStax "
                                   "Medical-Surgical Nursing, which this repository excludes pending the license "
                                   "contradiction check recorded in docs/REVIEW_HANDOFF.md."],
        }],
        "taxonomy": {
            "glossary": [
                {"term": "perfusion", "definition": "Delivery of oxygenated blood to tissue; its failure is reported by several organ systems at once.", "source_ref": SRC},
                {"term": "altered mentation", "definition": "New confusion or reduced responsiveness compared with the patient's earlier state.", "source_ref": SRC},
                {"term": "new organ dysfunction", "definition": "A perfusion-related change in an organ system that differs from this patient's own baseline.", "source_ref": SRC},
                {"term": "escalation", "definition": "Activating the organisation's sepsis or rapid-response pathway, communicating trend and suspected source, obtaining ordered diagnostics, and beginning stabilization.", "source_ref": SRC},
                {"term": "parallel action", "definition": "Coordinating diagnostics, treatment and stabilization together rather than waiting for one step to finish.", "source_ref": SRC},
            ],
            "concept_tags": ["perfusion", "infection", "organ dysfunction", "escalation", "trend", "clinical deterioration"],
            "outcome_tags": ["recognition of deterioration", "escalation and communication", "reassessment"],
            "nclex_client_needs": ["Physiological Adaptation", "Reduction of Risk Potential", "Management of Care"],
            "cjm_functions": CJM,
            "proposed_new_tags": [],
            "frameworks": [
                {"framework_id": "NCSBN-CJMM", "title": "NCSBN Clinical Judgment Measurement Model", "text_policy": "identifier-only"},
                {"framework_id": "CA-BRN-ART3", "title": "California BRN regulations, 16 CCR Article 3", "text_policy": "public-domain"},
                {"framework_id": "NCLEX-RN-2026", "title": "Harrity NCLEX-RN 2026 framework (shared/nclex-rn-2026.ts)", "text_policy": "author's own"},
            ],
        },
        "governance": {
            "promotion_state": "human_review",
            "administrative_metadata": {"lesson_id": "LESSON-NCLEX-PA-SEPSIS-RECOGNITION", "version": "0.1.0",
                                        "content_owner": "R. Harrity", "reviewer": "R. Harrity",
                                        "created_date": "2026-09-11"},
        },
        "slides": SLIDES,
        "assessment_items": ITEMS,
        "remediation_map": [
            {"miss_pattern": "learner waits for fever before evaluating for sepsis", "failed_operation": "analyze cues",
             "map_location": "S11", "concept_lane": "cues",
             "likely_misconception": "fever is required for sepsis",
             "one_slide_fix": "S11 checkpoint on the normal-temperature patient",
             "active_learning_task": "state the recognition rule without using the word temperature",
             "retrieval_item": "Q03", "improvement_evidence": ""},
            {"miss_pattern": "learner queues diagnostics and treatment instead of running them together",
             "failed_operation": "take action", "map_location": "S14", "concept_lane": "escalate",
             "likely_misconception": "each step must complete before the next begins",
             "one_slide_fix": "S14 parallel-action timeline",
             "active_learning_task": "re-order the four escalation components as concurrent, not sequential",
             "retrieval_item": "Q04", "improvement_evidence": ""},
            {"miss_pattern": "learner reads a completed intervention as a resolved problem",
             "failed_operation": "evaluate outcomes", "map_location": "S17", "concept_lane": "evaluate",
             "likely_misconception": "doing the intervention is the endpoint",
             "one_slide_fix": "S17 mini case on persistent hypotension",
             "active_learning_task": "name the finding that proves an intervention has not yet worked",
             "retrieval_item": "Q05", "improvement_evidence": ""},
        ],
        "qa": {
            "release_status": "review-needed",
            "gates_passed": ["runtime", "source", "taxonomy", "blueprint", "cjm_coverage", "outline", "script"],
            "defects": [
                {"severity": "minor", "slide_id": "-",
                 "note": "[clinical specificity] SRC02 states cues qualitatively and names no numeric thresholds, no "
                         "scoring tool, and no bundle timing. This lesson deliberately adds none. If the programme "
                         "teaches specific criteria or a local pathway, the author adds them; they are not inferable "
                         "from the source and were not invented here."},
                {"severity": "minor", "slide_id": "-",
                 "note": "[assessment] SRC02's facts[] share one set of three distractors, identical across all five "
                         "facts and all implausible. Reused as written they would teach test-taking rather than "
                         "clinical judgement, so distractors here are instructor-written; each keyed action and "
                         "rationale is the module's. Author to review the replacements."},
                {"severity": "minor", "slide_id": "-",
                 "note": "[evidence] All clinical slides are source-aligned to SRC02 (the author's own module), not "
                         "source-grounded. No OpenStax text is reproduced; the module's upstream OpenStax citation "
                         "remains excluded pending the license contradiction check."},
                {"severity": "minor", "slide_id": "S15",
                 "note": "[instructor-added] The 'systems' and 'already begun' handover cards extend the module's two "
                         "named elements (trend, suspected source). Confirm against local handover convention."},
                {"severity": "minor", "slide_id": "-",
                 "note": "[standards] Package-level CA-BRN-ART3 refs BRN-14 and BRN-17 are proposed by the builder; "
                         "author to confirm before any compliance filing. Slide-level standards_refs left empty."},
            ],
            "cjm_coverage_rationale": "",
        },
        "revision_log": [],
        "outcomes": {},
        "improvement_log": [],
    }


if __name__ == "__main__":
    spec = build()
    out = HERE / "lesson_spec.json"
    out.write_text(json.dumps(spec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    n_card = sum(1 for s in spec["slides"] if s["layout_spec"]["card_data"])
    clinical = [s for s in spec["slides"] if s["evidence_status"] in {"source-grounded", "source-aligned"}]
    print(f"wrote {out}: {len(spec['slides'])} slides, {n_card} with card_data, {len(clinical)} clinical slides all with "
          f"source_refs={all(s['source_refs'] for s in clinical)}, {len(spec['assessment_items'])} items")
