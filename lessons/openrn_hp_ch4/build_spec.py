#!/usr/bin/env python3
"""Build lesson_spec.json for the WP-2 reference lesson.

Source: Open RN, Nursing Health Promotion, Chapter 4 "Family Dynamics"
(Ernstmeyer & Christman, eds., 2025), CC BY 4.0 — registered as SRC01 in
handoff/source/SRC01_openrn_healthpromo_ch4_index.json.

Every clinical slide cites SRC01 with the section chunk it draws on. All
content is a paraphrase of the facts captured in the index; nothing here is
quoted from the CC BY-NC learning activities (§4.9) or the ADAPT items.
Tables 4.2 / 4.3 / 4.5a / 4.5b / 4.7 were not retrievable in the build
environment (egress blocked); slides that would have used table cells are
written from the section body instead and the gap is logged in qa.defects.

    python lessons/openrn_hp_ch4/build_spec.py            # writes lesson_spec.json next to this file
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = "SRC01"
LANES = ["structure", "dynamics", "risk", "strain", "action"]
CJM = ["recognize cues", "analyze cues", "prioritize hypotheses",
       "generate solutions", "take action", "evaluate outcomes"]


def sec(*ids: str) -> str:
    return "; ".join(f"SRC01.4.{i}" for i in ids)


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
            "origin": "original item written for this lesson; not derived from Open RN CC BY-NC activities"}


# Chapter learning objectives (Open RN, CC BY) used as the course-objective layer.
COURSE_OBJECTIVES = {
    "CO1": "Identify family roles, structure, and functions",
    "CO2": "Examine family dynamics",
    "CO3": "Identify various factors that can lead to actual and potential family health problems",
    "CO4": "Compare and contrast parenting styles and behaviors",
    "CO5": "Consider the influence of family cultural practices related to health",
    "CO6": "Identify the psychosocial effect of illness on a client and their family's health",
    "CO7": "Apply the nursing process to caring for a client in the context of the family",
}

OCQ = ("When one person is the client, how does the nurse recognize whether the family is helping or harming "
       "that person's health, and what does the nurse do first?")

SLIDES = [
    slide("S01", 1, "Family Dynamics: the family is part of the assessment", "title", "opening", "cross-lane",
          "", ["See the whole map first: five lanes",
               "Notice what the family is doing to health",
               "Decide what the nurse does first"],
          "Title slide.", ev="instructor-added", refs=[], dur=30),

    slide("S02", 2, "Opening case: an 8-year-old with abdominal pain", "opening_case", "opening", "dynamics",
          "Recognize the family cues that belong in a pediatric abdominal pain assessment.",
          ["Living situation and household", "How family members interact", "What the child believes about the divorce",
           "Strengths, stressors, supports"],
          "Start with the client in front of you. An eight-year-old is admitted with abdominal pain. The mother is at the bedside. "
          "During the interview you learn the parents are divorcing. Before we teach a single definition, decide what you already "
          "know and what you still need. You know the pain complaint and that one parent is present. You do not yet know the "
          "living situation, how the family interacts, what the child believes about the divorce, or what supports exist. "
          "Hold this case; we return to it at the end and you will write the nursing response yourself.",
          cjm=["recognize cues"], activity="List three things you still need to know before you can plan care.",
          answers=["Living situation and household members", "How family members interact and communicate",
                   "The child's feelings about the divorce and any sense of responsibility for it",
                   "Family strengths, stressors, and available supports"],
          card=[{"presentation": "An 8-year-old is admitted with abdominal pain. The mother is present. "
                                 "During the history the nurse learns the parents are divorcing.",
                 "cues": ["Abdominal pain: onset, location, duration, character, what makes it better or worse",
                          "One parent at the bedside", "Parents divorcing"],
                 "prompt": "What do you still need to know before you can plan care?"}],
          co="CO7", nac="assess", refs=[SRC]),

    slide("S03", 3, "The organizing question", "clinical_question", "map", "cross-lane",
          "State the question every slide in this lesson answers.", [],
          "Every concept in this chapter serves one question: when one person is the client, how does the nurse recognize whether "
          "the family is helping or harming that person's health, and what does the nurse do first? Five lanes carry the answer, "
          "from foundation to bedside: structure, dynamics, risk, strain, and action.",
          cjm=["recognize cues", "analyze cues"],
          card=[{"lane": "structure", "nodes": ["who counts as family", "roles", "five functions"]},
                {"lane": "dynamics", "nodes": ["healthy vs unhealthy patterns", "resources"]},
                {"lane": "risk", "nodes": ["ACEs", "risk and protective factors", "parenting"]},
                {"lane": "strain", "nodes": ["illness hits the whole family", "caregiver role strain"]},
                {"lane": "action", "nodes": ["assess", "diagnose", "outcomes", "intervene", "evaluate"]}],
          ev="instructor-added", refs=[], dur=60),

    slide("S04", 4, "Chapter map: structure to action", "chapter_map", "map", "cross-lane",
          "Use the map to locate where a family cue belongs.", [],
          "Map first. Foundation on the left, bedside on the right.",
          card=[{"lane": "structure", "nodes": ["family defined", "orientation vs procreation", "roles", "five functions"]},
                {"lane": "dynamics", "nodes": ["security vs stress", "high- vs low-resource", "dysfunction transmits"]},
                {"lane": "risk", "nodes": ["ACE dose-response", "risk factors", "protective factors", "parenting styles"]},
                {"lane": "strain", "nodes": ["one illness, whole family", "caregiver role strain", "family-centered care"]},
                {"lane": "action", "nodes": ["recognize cues", "analyze cues", "outcomes", "take action", "evaluate"]}],
          ev="instructor-added", refs=[], dur=60, visual="Foundation on the left, bedside action on the right."),

    slide("S05", 5, "Structure: who is family, and what does a family do?", "concept_cards", "lane: structure", "structure",
          "Identify family structure, roles, and the five family functions.",
          ["Family: two or more people related by birth, marriage, or adoption, living together",
           "Family of orientation vs family of procreation",
           "Roles are recurrent behavior patterns; illness can impair them"],
          "The chapter opens with a working definition from the U.S. Census: two or more people, one the householder, related by "
          "birth, marriage, or adoption, living together. Nursing needs two more ideas. Family of orientation is the family you grew "
          "up in; family of procreation is the one you form as an adult. Roles are recurrent behavior patterns that fulfil family "
          "functions, and they change across the life span and can be impaired by chronic illness. The chapter names five functions. "
          "Read the five cards. When you assess a family, you are asking whether each function is being met for the client.",
          cjm=["analyze cues"],
          card=[{"heading": "Economic support", "body": "Meeting members' material needs.", "cjm": "analyze cues"},
                {"heading": "Emotional support", "body": "Intimacy: mutually shared trust that buffers outside stress.", "cjm": "analyze cues"},
                {"heading": "Socialization", "body": "First teacher of norms, values, and how emotions are shown. Can also pass on unhealthy behavior.", "cjm": "analyze cues"},
                {"heading": "Sexuality and reproduction", "body": "Family norms around partnership and reproduction.", "cjm": "analyze cues"},
                {"heading": "Ascribed social status", "body": "Status at birth versus achieved status by effort; family support shapes achievement.", "cjm": "analyze cues"}],
          co="CO1", visual="Table 4.2 (modern family structures) not retrievable at build; faculty may add examples."),

    slide("S06", 6, "Structure: roles, culture, and the nurse's own bias", "concept_cards", "lane: structure", "structure",
          "Recognize informal and unhealthy family roles and the nurse's obligation to cultural humility.",
          ["Informal roles: decision-maker, peace-maker, tradition-holder",
           "Decision-maker is culturally determined and may vary by decision",
           "ANA: respectful and equitable practice = cultural humility + inclusiveness",
           "Implicit bias is unconscious and can affect care"],
          "Two role families matter at the bedside. Informal roles include the decision-maker, the peace-maker, and the tradition-holder. "
          "The decision-maker is culturally determined and may change with the type of decision, so ask rather than assume. In family "
          "dysfunction the chapter lists roles such as the hero, the mascot, the identified patient or scapegoat, the lost child, the "
          "enabler, and the parentified child. Those are cues, not labels to put in a chart. The last card is about you: the ANA standard "
          "of respectful and equitable practice combines cultural humility with inclusiveness, and implicit bias, an unconscious attitude "
          "shaped by experience, can change the care you give without your noticing.",
          cjm=["recognize cues", "analyze cues"],
          card=[{"heading": "Informal roles", "body": "Decision-maker, peace-maker, tradition-holder.", "cjm": "recognize cues"},
                {"heading": "Dysfunction roles", "body": "Hero, mascot, scapegoat, lost child, enabler, parentified child.", "cjm": "recognize cues"},
                {"heading": "Culture", "body": "Shared values, norms, symbols, language, and way of life passed between generations.", "cjm": "analyze cues"},
                {"heading": "The nurse's lens", "body": "Cultural humility plus inclusiveness; watch for implicit bias.", "cjm": "analyze cues"}],
          co="CO5"),

    slide("S07", 7, "Dynamics: healthy or unhealthy?", "compare", "lane: dynamics", "dynamics",
          "Distinguish healthy from unhealthy family dynamics using observable cues.",
          ["A family can be functional in some ways and dysfunctional in others",
           "Dysfunction: the five functions fail; usually unintended; passed across generations"],
          "Family dynamics are the roles, relationships, and communication patterns that shape how members interact. The chapter gives "
          "a simple test. Healthy relationships produce security and comfort. Unhealthy ones produce stress: arguments, intrusion, "
          "criticism. The same family can be healthy in some characteristics and unhealthy in others at the same time, so avoid a single "
          "verdict. High-resource families combine resiliency with resources: money, extended family, friends, a faith community. "
          "Low-resource families do not effectively meet members' needs. Dysfunction is a failure of the five functions, usually "
          "unintended, and it is transmitted across generations, which is why caregiver trauma reaches into a child's sense of self.",
          cjm=["analyze cues"],
          card=[{"columns": [
              {"title": "healthy: security and comfort", "items": ["mutual respect", "trust", "caring communication", "needs met, or help sought", "resiliency plus resources"]},
              {"title": "unhealthy: stress", "items": ["arguments, intrusion, criticism", "unfriendly, disrespectful, hostile interaction", "needs not effectively met", "caregiver trauma reaching the child"]}]}],
          co="CO2", visual="Table 4.3 not retrievable at build; columns are built from the section body."),

    slide("S08", 8, "Risk: adverse childhood experiences are dose-dependent", "risk_engine", "lane: risk", "risk",
          "Explain why ACE count, not any single event, predicts later health risk.",
          ["ACE Study: more ACEs, more adolescent risk behavior and adult chronic illness",
           "Highest ACE exposure: about 20 years lower life expectancy"],
          "Adverse childhood experiences include neglect, abuse, divorce, a family member in prison, and witnessing substance abuse, "
          "mental illness, or violence against a parent. The ACE Study followed more than seventeen thousand people and found a "
          "dose-response relationship: the more ACEs, the more adolescent risk behavior and the more adult chronic illness, including "
          "alcoholism, COPD, depression, and liver disease. The highest exposure group lost about twenty years of life expectancy. "
          "The engine around the centre lists what raises the risk. Notice that most of these are things a nurse can screen for.",
          cjm=["analyze cues", "prioritize hypotheses"],
          card=[{"center": "how many ACEs, not which one",
                 "factors": [{"title": "caregiver history", "body": "abused as a child; young caregivers; limited understanding of child development"},
                             {"title": "household strain", "body": "single parent, low income or education, financial stress, special-needs caregiving"},
                             {"title": "discipline and supervision", "body": "inconsistent discipline or spanking, low supervision"},
                             {"title": "family climate", "body": "isolation, high conflict, attitudes that accept violence"},
                             {"title": "community", "body": "violence, poverty, food insecurity, drug and alcohol access, unstable housing"},
                             {"title": "opportunity", "body": "few youth activities, low involvement, limited opportunity"}]}],
          co="CO3"),

    slide("S09", 9, "Risk: protective factors the nurse can build", "teaching_point", "lane: risk", "risk",
          "Name protective factors and the divorce guidance a nurse can teach a parent.",
          ["Divorce is an ACE; its effect depends on how the parents treat each other",
           "Keep routine, friends, school; consistent rules across households; keep promises"],
          "Protective factors are the other half of the risk engine and they are teachable. In the family: basic needs met, stable and "
          "nurturing relationships, social support, positive shared activities, school valued, peaceful conflict resolution, outside "
          "mentors, caregiver education and employment, effective supervision. In the community: parenting education, financial "
          "assistance, health and mental health services, safe housing and childcare, quality preschool, after-school programs, "
          "family-friendly employment. Divorce is itself an ACE, and the chapter is specific: the effect is moderated by how the "
          "parents treat each other before, during, and after. That gives you a teaching script for the opening case.",
          cjm=["generate solutions", "take action"],
          activity="Write two sentences of anticipatory guidance for the divorcing parents in the opening case.",
          answers=["Never force the child to take sides; no arguments or criticism of the other parent in front of the child",
                   "Talk early and often, be honest in simple terms, tell the child it is not their fault, reassure them they are loved",
                   "Keep routine, friends, school, and environment; keep rules consistent across both households; keep promises",
                   "Inform teachers and counselors so problems at school are reported"],
          card=[{"cards": [{"title": "in the family", "body": "needs met; stable nurturing relationships; social support; shared activities; school valued; peaceful conflict resolution; mentors"},
                           {"title": "in the community", "body": "parenting education; financial help; health and mental health services; safe housing and childcare; preschool and after-school programs"},
                           {"title": "when parents divorce", "body": "no sides, no arguments in front of the child; talk early and often; not the child's fault; keep routine and promises"}],
                 "warning": "Anticipatory guidance is a nursing action. Give it in plain terms and check what the parent heard."}],
          co="CO3", nac="educate"),

    slide("S10", 10, "Risk: four parenting styles on two axes", "concept_cards", "lane: risk", "risk",
          "Compare parenting styles by responsiveness and demandingness and their outcomes.",
          ["Two axes: responsiveness (warmth) and demandingness (behavioral control)",
           "Third dimension: psychological control such as guilt or love withdrawal",
           "Authoritative explains the rationale; authoritarian expects compliance"],
          "The chapter places parenting on two axes: responsiveness, meaning warmth and support, and demandingness, meaning behavioral "
          "control. Crossing them gives four styles. Uninvolved is low on both and produces poor outcomes in every domain. Permissive is "
          "high warmth and low control: more behavior problems and lower academics, but higher self-esteem and social skills. "
          "Authoritarian is low warmth and high control: moderate academics, poorer social skills, lower self-esteem, more depression. "
          "Authoritative is high on both and does best across domains, including the lowest risk of underage drinking. A third "
          "dimension, psychological control through guilt, shaming, or withdrawing love, separates authoritarian from authoritative: "
          "one expects unquestioned compliance, the other explains the reason.",
          cjm=["analyze cues"],
          card=[{"heading": "Uninvolved", "body": "Low warmth, low control. Poor outcomes in all domains.", "cjm": "analyze cues"},
                {"heading": "Permissive", "body": "High warmth, low control. Behavior problems, lower academics; higher self-esteem and social skills.", "cjm": "analyze cues"},
                {"heading": "Authoritarian", "body": "Low warmth, high control. Moderate academics; poorer social skills, lower self-esteem, more depression.", "cjm": "analyze cues"},
                {"heading": "Authoritative", "body": "High warmth, high control, explains rationale. Best outcomes; lowest underage drinking risk.", "cjm": "analyze cues"}],
          co="CO4", visual="Tables 4.5a/4.5b not retrievable at build; cards are from the section body."),

    slide("S11", 11, "Risk: what positive discipline looks like", "script_template", "lane: risk", "risk",
          "Teach a caregiver a consequence sequence that guides rather than punishes.",
          ["Discipline is guidance, not punishment; make it age-appropriate",
           "Spanking is not effective; it teaches hitting to get what you want",
           "Time-out: one minute per year of age, then a hug and positive words"],
          "Discipline in this chapter means guidance, not punishment. The consequence steps are a script you can hand to a parent: "
          "clear guidelines and a warning; a specific if-then consequence that fits the behavior; immediate follow-through; positive "
          "reinforcement afterward. For a young child, time-out runs one minute per year of age and ends with a hug and positive words. "
          "For an older child, remove a privilege briefly, then restate the rule and give positive attention. Behaviorism adds a rule: "
          "attend to the behavior you want and, if the child is safe, ignore the tantrum, then name the emotion afterward and teach an "
          "acceptable way to show it. Spanking is not effective and teaches that hitting gets what you want. Rewards beat consequences.",
          cjm=["generate solutions", "take action"],
          card=[{"steps": [{"title": "set the guideline", "body": "clear rule plus a warning"},
                           {"title": "name the consequence", "body": "specific if-then that fits the behavior"},
                           {"title": "follow through", "body": "immediately, calmly"},
                           {"title": "reinforce", "body": "positive attention for the behavior you want"},
                           {"title": "teach the feeling", "body": "after a tantrum, name the emotion and show an acceptable way to express it"}]}],
          co="CO4", nac="educate"),

    slide("S12", 12, "Strain: one member's illness reaches the whole family", "control_room", "lane: strain", "strain",
          "Identify how a client's illness changes roles for parents, siblings, and caregivers.",
          ["Parents manage regimens, appointments, finances",
           "Siblings may feel unvalued and slip into the lost-child role",
           "Substance use disorder in the family: enabling, ignoring, financial drain"],
          "When one member is ill the family reorganises around the illness. Parents take on regimens, appointments, and the cost. "
          "Siblings can feel unvalued and adopt the lost-child role. A substance use disorder in the family produces enabling, "
          "ignoring, and financial drain. Family caregivers provide regular care for chronic illness or disability: activities of daily "
          "living, bills, shopping, transport, emotional support, and the strain rises as the needs rise. Caregiver role strain is the "
          "chapter's name for difficulty performing that role. Caregiving can enhance quality of life, and it can impair work, social "
          "life, and physical and mental health at the same time.",
          cjm=["recognize cues", "analyze cues"],
          card=[{"center": "one member's illness",
                 "nodes": [{"title": "parents", "body": "regimens, appointments, finances"},
                           {"title": "siblings", "body": "feel unvalued; lost-child role"},
                           {"title": "family caregivers", "body": "ADLs, bills, shopping, transport, emotional support; strain rises with need"},
                           {"title": "family with SUD", "body": "enabling, ignoring, financial drain"}]}],
          co="CO6"),

    slide("S13", 13, "Strain: caregiver role strain and what the nurse offers", "concept_cards", "lane: strain", "strain",
          "Recognize caregiver stress signs and match them to resources and self-care teaching.",
          ["US: 22% of adults gave care in the past 30 days; 10% for dementia",
           "Family-centered care: respect and dignity, collaboration, empowerment, information sharing"],
          "Watch the caregiver as closely as the client. The chapter's stress signs: anger or frustration, social withdrawal, anxiety "
          "about the future, depression or reduced coping, exhaustion, sleeplessness, irritability and poor concentration, and new "
          "health problems in the caregiver. Resources to offer: child or adult day care, respite care at home or in a facility, "
          "residential care, palliative care, and support groups such as Al-Anon, Nar-Anon, and Sibshops for siblings of children with "
          "disabilities. Self-care teaching covers provider visits, nutrition, exercise, rest, and relaxation techniques, framed as "
          "'taking care of yourself helps you be a better caregiver.' Family-centered care ties it together with four principles.",
          cjm=["recognize cues", "generate solutions"],
          card=[{"heading": "Stress signs", "body": "anger, withdrawal, anxiety, depression, exhaustion, sleeplessness, irritability, new illness", "cjm": "recognize cues"},
                {"heading": "Resources", "body": "day care, respite, residential or palliative care; Al-Anon, Nar-Anon, Sibshop; family therapy", "cjm": "generate solutions"},
                {"heading": "Self-care teaching", "body": "provider visits, nutrition, exercise, rest; relaxation breathing, visualization, meditation", "cjm": "generate solutions"},
                {"heading": "Family-centered care", "body": "respect and dignity; collaboration; empowerment; information sharing", "cjm": "generate solutions"}],
          co="CO6", nac="educate"),

    slide("S14", 14, "Action: the nursing process is the clinical judgment model", "process_map", "lane: action", "action",
          "Map each nursing process step to its NCSBN clinical judgment function for a family assessment.", [],
          "Section 4.7 lays the nursing process over the clinical judgment model explicitly, so this map is the chapter's, not ours. "
          "Assessment is recognize cues: establish cultural safety and privacy first, identify the decision-maker, and do a general "
          "survey of client and family. Diagnosis is analyze cues. Outcome identification is generate solutions with the family, in "
          "their values and culture. Implementation is take action, reprioritized against the current condition. Evaluation asks whether "
          "the diagnosis was accurate and the goals met, and whether to keep, modify, or delete each part of the plan.",
          cjm=["recognize cues", "analyze cues", "generate solutions", "take action", "evaluate outcomes"],
          card=[{"label": "recognize cues", "body": "cultural safety and privacy first; who decides; general survey of client and family"},
                {"label": "analyze cues", "body": "nursing diagnoses related to family processes, parenting, caregiving"},
                {"label": "generate solutions", "body": "collaborative, SMART, in the family's values and culture"},
                {"label": "take action", "body": "reprioritize; focused assessments; interventions"},
                {"label": "evaluate outcomes", "body": "diagnosis accurate? goals met? keep, modify, delete"}],
          co="CO7", visual="Table 4.7 (NANDA diagnoses) not retrievable at build; faculty to insert program's care-planning resource."),

    slide("S15", 15, "Action: assess the family without losing the client", "mini_case", "lane: action", "action",
          "Sequence a family assessment that protects the client's privacy and autonomy.",
          ["Ask the client privately who they want present",
           "General survey of client and family",
           "Hostile or disrespectful interaction is a cue to act on"],
          "Here is the assessment sequence for the opening case. First, establish cultural safety and privacy: one open-ended cultural "
          "question, then find out who the decision-maker is, which for a child under eighteen is the parent or guardian, while still "
          "advocating for the client's autonomy. Ask the client privately who they want present; the nurse does the asking because the "
          "client may not feel empowered to. Then the general survey of client and family: hygiene, affect, communication, nutrition, "
          "fluid status, for signs of neglect, abuse, or substance misuse, and observe roles and interaction. Then the family-effect "
          "questions: what the family knows about the illness, how they respond, and what supports they know of.",
          cjm=["recognize cues", "prioritize hypotheses"],
          activity="Which single step must happen before any family member is interviewed?",
          answers=["Establish cultural safety and privacy, and ask the client privately who they want present"],
          card=[{"presentation": "The 8-year-old from the opening case. Mother present. Parents divorcing. The nurse is about to take the family history.",
                 "cues": ["Minor: parent decides; autonomy still advocated",
                          "Survey hygiene, affect, communication, nutrition",
                          "What does the family know, and how do they respond?",
                          "Supports: respite, community, other family"],
                 "prompt": "Put the steps in order and say which one protects the client."}],
          co="CO7", nac="assess"),

    slide("S16", 16, "Action: sort the cues by what the nurse does next", "urgency_sort", "lane: action", "action",
          "Prioritize family cues by required nursing action, from mandated reporting to teaching.",
          [],
          "Not every family cue carries the same weight. The chapter gives three response levels. Suspected abuse or neglect triggers "
          "state mandated reporting and agency policy; that outranks everything. Unfriendly, disrespectful, or hostile interaction means "
          "notify the provider and refer to social work or case management per policy. Caregiver stress signs call for resources and "
          "self-care teaching. A parent asking about discipline is a teaching moment. Sort these four cues in the order the nurse acts.",
          cjm=["prioritize hypotheses", "take action"],
          activity="Order the four cues from most to least urgent nursing action.",
          answers=["1 bruises in different stages of healing with an inconsistent explanation: mandated report per state law and policy",
                   "2 mother speaks to the child with hostility and contempt during the survey: notify provider; social work referral",
                   "3 mother reports sleeplessness, irritability, and dread about the future: caregiver strain; resources and self-care",
                   "4 mother asks whether spanking is acceptable: teaching moment; positive discipline sequence"],
          card=[{"items": ["mother asks whether spanking is acceptable",
                           "bruises in different stages of healing with an inconsistent explanation",
                           "mother reports sleeplessness, irritability, and dread about the future",
                           "mother speaks to the child with hostility and contempt during the survey"],
                 "correct_order": [1, 3, 2, 0],
                 "categories": [
                     {"title": "cues to sort", "items": ["asks whether spanking is acceptable", "bruises in different stages of healing, inconsistent explanation",
                                                          "sleeplessness, irritability, dread about the future", "hostility and contempt toward the child during the survey"]},
                     {"title": "response ladder: most to least urgent", "items": ["mandated report per state law and agency policy", "notify provider; social work or case management referral",
                                                                                   "caregiver role strain: resources and self-care teaching", "teaching moment: positive discipline"]}]}],
          co="CO7", nac="escalate"),

    slide("S17", 17, "Checkpoint: the caregiver in the waiting room", "checkpoint_mcq", "lane: strain", "strain",
          "Select the priority nursing response to caregiver role strain.", [],
          "A checkpoint on the strain lane. Read the stem, choose one, and be ready to say why the other three are weaker. The "
          "correct answer is the one that names the cue as caregiver role strain and responds with a resource, not reassurance alone.",
          cjm=["analyze cues", "generate solutions"],
          activity="Select one.", answers=["C"],
          card=[{"stem": "An adult daughter caring for her father with dementia says she has not slept properly in weeks, snaps at him, "
                         "and 'cannot see how this ends.' What is the nurse's best response?",
                 "options": ["A. Reassure her that all caregivers feel this way and it will pass",
                             "B. Suggest she try harder to keep a routine at home",
                             "C. Identify caregiver role strain and offer respite care and support-group information",
                             "D. Tell her that her father would be safer in a residential facility"],
                 "correct": "C",
                 "rationale": "Sleeplessness, irritability, and anxiety about the future are the chapter's caregiver stress signs. "
                              "The nursing response is to recognize role strain and mobilize resources such as respite care and support groups. "
                              "A minimizes, B adds demand without support, D imposes a decision the family has not made."}],
          co="CO6"),

    slide("S18", 18, "Capstone: the abdominal pain case, resolved", "capstone_mcq", "lane: action", "action",
          "Choose the priority nursing action when a family cue and a clinical complaint arrive together.",
          ["Pain assessment complete; provider notified", "Then the family history produces a new cue"],
          "Back to the child from the opening case. The abdominal pain assessment is complete and the provider has been notified. "
          "During the family history the mother says, in front of the child, that the pain started when the father left and that it is "
          "the child's fault for upsetting everyone. Pick the priority nursing action. Think about which cue this is and which response "
          "level the chapter assigns to it.",
          cjm=["prioritize hypotheses", "take action"],
          activity="Select one.", answers=["B"],
          card=[{"scenario": "During the family history the mother says, in front of the child, that the pain started when his father left "
                              "and that it is his fault for upsetting everyone.",
                 "stem": "What is the nurse's priority action?",
                 "options": ["A. Correct the mother immediately in front of the child so the child hears it is not their fault",
                             "B. Speak with the child privately, then address the parent's statement and involve social work per policy",
                             "C. Document the statement and continue the physical assessment",
                             "D. File a mandated report for emotional abuse before doing anything else"],
                 "correct": "B",
                 "rationale": "The chapter's sequence protects the client first: privacy and the client's own account, then the family cue. "
                              "Blaming the child in front of them is an unhealthy interaction cue that warrants provider notification and a social "
                              "work referral per policy, not silence (C). A confrontation in front of the child escalates the interaction. A single "
                              "blaming statement does not by itself meet the mandated-reporting threshold (D); the nurse assesses further."}],
          co="CO7", nac="escalate"),

    slide("S19", 19, "Rapid retrieval: five-item exit check", "retrieval_check", "close", "cross-lane",
          "Retrieve one fact per lane without notes.",
          ["Name the five family functions",
           "State the one test that separates healthy from unhealthy dynamics",
           "Why does the number of ACEs matter more than which one?",
           "Name three caregiver stress signs",
           "What must the nurse do before interviewing any family member?"],
          "Close the loop. Five questions, one per lane, answered aloud or on paper. The answers are on the slides you just saw and "
          "in the facilitator guide. If a lane produces silence, that is the lane to remediate next session.",
          cjm=["evaluate outcomes"],
          activity="Answer all five.",
          answers=["economic support, emotional support, socialization, control of sexuality and reproduction, ascribed social status",
                   "healthy produces security and comfort; unhealthy produces stress",
                   "the ACE Study found a dose-response relationship: more ACEs, more risk behavior and chronic illness",
                   "any three of: anger, withdrawal, anxiety about the future, depression, exhaustion, sleeplessness, irritability, new health problems",
                   "establish cultural safety and privacy, and ask the client who they want present"],
          co="CO7"),

    slide("S20", 20, "Takeaway: what the nurse notices, and what the nurse does first", "takeaway", "close", "cross-lane",
          "A safe nurse assesses the family as part of the client, sorts cues by required action, and teaches what protects.",
          ["Notice: roles, functions, interaction, strain", "Sort: report, refer, resource, teach",
           "Protect: privacy first, client's voice first", "Teach: guidance, not punishment"],
          "Closing frame.",
          ev="instructor-added", refs=[], dur=45,
          card=[{"title": "notice", "body": "roles, functions, interaction patterns, caregiver strain"},
                {"title": "sort", "body": "mandated report, provider and social work referral, resources, teaching"},
                {"title": "protect", "body": "privacy first; ask the client who they want present"},
                {"title": "teach", "body": "protective factors, positive discipline, caregiver self-care"}]),
]

ITEMS = [
    item("Q01", "S05", "mcq", "structure", "analyze cues",
         "A school nurse notes that a 10-year-old regularly cooks dinner for younger siblings and reminds a parent to take medication. "
         "Which family role best describes this cue?",
         ["A. Tradition-holder", "B. Parentified child", "C. Mascot", "D. Decision-maker"], "B",
         "The parentified child takes on adult caregiving responsibilities; the chapter lists it among roles seen in family dysfunction. "
         "The others are informal or dysfunction roles that do not fit the cue.", "S06", "CO1", "SRC01.4.2"),
    item("Q02", "S07", "sata", "dynamics", "recognize cues",
         "During a home visit the nurse observes a family. Which findings are cues of healthy family dynamics? Select all that apply.",
         ["A. Members speak to each other with respect", "B. A member's needs are unmet and no help has been sought",
          "C. Members describe trusting each other", "D. Frequent criticism and intrusion into each other's decisions",
          "E. The family names friends and a faith community it can call on"], "A, C, E",
         "Mutual respect, trust, and caring communication are healthy cues; resources such as friends and a faith community mark a "
         "high-resource family. Unmet needs without seeking help and criticism or intrusion are unhealthy cues.", "S07", "CO2", "SRC01.4.3"),
    item("Q03", "S08", "mcq", "risk", "analyze cues",
         "A parent asks why the clinic screens for several kinds of childhood adversity instead of 'the serious ones.' "
         "Which explanation is most accurate?",
         ["A. Only abuse predicts adult illness; the other questions are for research",
          "B. Risk rises with the number of adverse experiences, not with any single one",
          "C. Divorce is not considered an adverse experience", "D. Screening identifies which parent caused the harm"], "B",
         "The ACE Study demonstrated a dose-response relationship between the number of ACEs and later risk behavior and chronic illness. "
         "Divorce is an ACE. Screening is not about assigning blame.", "S08", "CO3", "SRC01.4.4"),
    item("Q04", "S09", "mcq", "risk", "generate solutions",
         "Parents who are separating ask the nurse what will protect their 7-year-old. Which teaching is consistent with the chapter?",
         ["A. Wait until the child asks before discussing the separation", "B. Let the child choose which parent is right",
          "C. Keep the child's routine, school, and friends, and keep rules consistent in both homes",
          "D. Avoid mentioning the other parent so the child forgets the conflict"], "C",
         "The chapter's divorce guidance: talk early and often, never force sides, keep routine, friends, school and environment, keep rules "
         "consistent across households, and keep promises.", "S09", "CO3", "SRC01.4.4"),
    item("Q05", "S10", "matching", "risk", "analyze cues",
         "Match each parent description to the parenting style. 1: warm, sets firm limits, explains the reasons. 2: warm, few limits. "
         "3: strict, expects compliance without explanation. 4: neither warm nor demanding.",
         ["A. authoritative", "B. permissive", "C. authoritarian", "D. uninvolved"], "1-A, 2-B, 3-C, 4-D",
         "Styles are defined by responsiveness (warmth) crossed with demandingness (control); authoritative parents explain rationale where "
         "authoritarian parents expect unquestioned compliance.", "S10", "CO4", "SRC01.4.5"),
    item("Q06", "S11", "ordering", "risk", "take action",
         "A parent asks how to respond to a 4-year-old who throws food at dinner. Place the nurse's teaching in order: "
         "(a) follow through immediately, (b) state the rule and give a warning, (c) give positive attention when the child eats appropriately, "
         "(d) state the specific if-then consequence.",
         ["b, d, a, c"], "b, d, a, c",
         "The chapter's consequence sequence: clear guideline plus warning, a specific if-then consequence that fits the behavior, immediate "
         "follow-through, then positive reinforcement.", "S11", "CO4", "SRC01.4.5"),
    item("Q07", "S13", "mcq", "strain", "recognize cues",
         "Which statement by a family caregiver most clearly indicates caregiver role strain?",
         ["A. 'I have learned a lot about his medications.'", "B. 'I stopped seeing my friends and I cannot concentrate at work.'",
          "C. 'We go to his appointments together.'", "D. 'The home health aide comes twice a week.'"], "B",
         "Social withdrawal and poor concentration are among the chapter's caregiver stress signs. The other statements describe coping or "
         "resources in use.", "S13", "CO6", "SRC01.4.6"),
    item("Q08", "S15", "mcq", "action", "prioritize hypotheses",
         "An adult client's spouse answers every question during the admission interview. What should the nurse do first?",
         ["A. Ask the spouse to leave the room", "B. Continue; the spouse is the decision-maker",
          "C. Ask the client privately who they would like present during the interview",
          "D. Document that the client is unable to participate"], "C",
         "The chapter directs the nurse to ask the client privately who they want present and to do the asking for them, because the client may "
         "not feel empowered to. Decision-maker status is determined, not assumed (B), and A acts before the client's preference is known.",
         "S15", "CO7", "SRC01.4.7"),
    item("Q09", "S16", "mcq", "action", "take action",
         "During the general survey the nurse observes a parent speaking to the child with hostility and contempt. "
         "Which action does the chapter direct?",
         ["A. Ignore it; interaction style is a family's private matter", "B. Notify the provider and refer to social work or case management per policy",
          "C. Immediately file a mandated report", "D. Teach the parent positive communication before completing the assessment"], "B",
         "Unfriendly, disrespectful, or hostile interaction is a cue to notify the provider and refer per policy. Mandated reporting applies to "
         "suspected abuse; teaching comes after the assessment and the referral.", "S16", "CO7", "SRC01.4.7"),
    item("Q10", "S14", "mcq", "action", "evaluate outcomes",
         "After a teaching session the outcome was 'the parent will describe three home safety risks.' At evaluation the parent names one. "
         "What is the nurse's next step?",
         ["A. Record the outcome as met", "B. Delete the outcome because it was unrealistic",
          "C. Determine whether the goal is progressing and modify the plan or gather more data",
          "D. Repeat the identical teaching session"], "C",
         "Evaluation asks whether goals were met or are progressing and whether to keep, modify, or delete diagnoses, goals, outcomes, and "
         "interventions, and whether more data are needed.", "S14", "CO7", "SRC01.4.7"),
]


def build() -> dict:
    return {
        "schema_version": "1.2",
        "runtime_config": {
            "runtime": {"run_date_yyyymmdd": "20260906", "package_id": "HP-CH4-FAMILY-DYNAMICS-R1", "build_mode": "full_production",
                        "deployment_mode": "hybrid", "rebuild_scope": "full", "output_root": "."},
            "outputs": {"filename_pattern": "{{runtime.run_date_yyyymmdd}}_{{lesson.course_code}}_{{lesson.chapter_title}}_Part_{{deck.part_number}}.pptx"},
            "media": {"wpm_target": 140},
        },
        "lesson": {
            "course_code": "NHP", "program_level": "prelicensure RN", "audience": "prelicensure nursing students",
            "unit_title": "Health Promotion Across the Lifespan", "chapter_id": "4", "chapter_title": "Family Dynamics",
            "lesson_title": "Family Dynamics at the Bedside",
            "concept": "family dynamics", "exemplars": ["adverse childhood experiences", "parenting styles", "caregiver role strain", "family-centered care"],
            "clinical_domain": "health promotion / psychosocial integrity", "source_family": "Open RN Nursing Health Promotion",
            "source_anchor": "Chapter 4, sections 4.1-4.8", "page_range": "n/a (web text)",
            "organizing_clinical_question": OCQ,
            "opening_patient_question": "My son's stomach hurts. Is it because of the divorce?",
            "concept_lanes": LANES, "target_duration_minutes": 50,
            "program_outcomes": [],
            "course_objectives": [{"id": k, "text": v, "maps_to": []} for k, v in COURSE_OBJECTIVES.items()],
            # Package-level: which CA BRN Article 3 requirements this lesson is offered as evidence for.
            # Proposed by the builder; the faculty reviewer confirms before release (see qa.defects).
            "standards_refs": [
                {"framework_id": "CA-BRN-ART3", "ref": "BRN-14", "basis": "1426(b): nursing process and clinical judgment model integrated explicitly (S14 process map, CJM coverage matrix)"},
                {"framework_id": "CA-BRN-ART3", "ref": "BRN-17", "basis": "1426(f): assessment items and traceability matrix link evaluation to course objectives"},
            ],
        },
        "sources": [{
            "source_id": SRC, "title": "Nursing Health Promotion, Chapter 4: Family Dynamics", "kind": "authoritative",
            "license": "CC BY 4.0", "locator": "https://wtcs.pressbooks.pub/healthpromo/ (chapter 4); https://www.ncbi.nlm.nih.gov/books/NBK615335/",
            "coverage_status": "confirmed",
            "attribution_statement": "Adapted from Open RN, Nursing Health Promotion, Chapter 4 (Ernstmeyer & Christman, eds., 2025), CC BY 4.0. https://wtcs.pressbooks.pub/healthpromo/",
            "index_path": "handoff/source/SRC01_openrn_healthpromo_ch4_index.json",
            "license_exclusions": ["4.9 learning activities and case study (CC BY-NC 4.0)", "H5P cards and question sets (CC BY-NC 4.0)",
                                   "ADAPT NGN items (CC BY-NC 4.0)", "figure 4.11 (CC BY-SA 4.0)"],
        }],
        "taxonomy": {
            "glossary": [
                {"term": "family dynamics", "definition": "Roles, relationships, communication patterns, and factors shaping how family members interact.", "source_ref": SRC},
                {"term": "family dysfunction", "definition": "Failure of the five family functions; usually unintended; transmitted across generations.", "source_ref": SRC},
                {"term": "adverse childhood experiences (ACE)", "definition": "Neglect, abuse, divorce, incarceration of a family member, witnessing substance abuse, mental illness, or violence against a parent.", "source_ref": SRC},
                {"term": "caregiver role strain", "definition": "Difficulty performing the family caregiver role.", "source_ref": SRC},
                {"term": "family-centered care", "definition": "Client-centered approach emphasizing family involvement and collaboration in care and decisions.", "source_ref": SRC},
                {"term": "cultural humility", "definition": "With inclusiveness, the ANA standard of respectful and equitable practice.", "source_ref": SRC},
            ],
            "concept_tags": ["family", "family dynamics", "adverse childhood experiences", "parenting", "caregiver role strain", "family-centered care", "cultural humility"],
            "outcome_tags": ["assessment of family", "anticipatory guidance", "referral", "mandated reporting"],
            "nclex_client_needs": ["Psychosocial Integrity", "Management of Care", "Health Promotion and Maintenance"],
            "cjm_functions": CJM,
            "proposed_new_tags": [],
            "frameworks": [
                {"framework_id": "NCSBN-CJMM", "title": "NCSBN Clinical Judgment Measurement Model", "text_policy": "identifier-only"},
                {"framework_id": "CA-BRN-ART3", "title": "California BRN regulations, 16 CCR Article 3 (Airtable: Requirements (Article 3), ref = req_id)", "text_policy": "public-domain"},
                {"framework_id": "CCNE-2018", "title": "CCNE Standards for Accreditation of Baccalaureate and Graduate Nursing Programs", "text_policy": "identifier-only"},
                {"framework_id": "AACN-2021", "title": "AACN Essentials 2021", "text_policy": "identifier-only"},
                {"framework_id": "QSEN", "title": "QSEN competencies", "text_policy": "identifier-only"},
                {"framework_id": "PEARSON-CF", "title": "Pearson Concept Framework (Airtable: Pearson Concept Framework Loader, ref = Concept Key)", "text_policy": "identifier-only"},
            ],
        },
        "governance": {
            "promotion_state": "faculty_review",
            "approvals": {k: False for k in ["source_approved", "taxonomy_approved", "objectives_approved", "outline_approved",
                                             "script_approved", "faculty_approved", "release_approved"]},
            "taxonomy_lock": {"status": "unlocked", "approved_by": "", "approval_date": ""},
            "administrative_metadata": {"lesson_id": "LESSON-NHP-CH4-FAMILY-DYNAMICS", "version": "0.1.0",
                                        "content_owner": "R. Harrity", "faculty_reviewer": "R. Harrity", "created_date": "2026-09-06"},
        },
        "slides": SLIDES,
        "assessment_items": ITEMS,
        "remediation_map": [
            {"miss_pattern": "learner reassures instead of referring when interaction is hostile", "failed_operation": "take action",
             "map_location": "S16", "concept_lane": "action", "likely_misconception": "family conflict is private and outside the nurse's role",
             "one_slide_fix": "S16 urgency sort with the three response levels", "active_learning_task": "re-sort the four cues", "retrieval_item": "Q09", "improvement_evidence": ""},
            {"miss_pattern": "learner reads a single ACE as the risk rather than the count", "failed_operation": "analyze cues",
             "map_location": "S08", "concept_lane": "risk", "likely_misconception": "only abuse counts", "one_slide_fix": "S08 risk engine",
             "active_learning_task": "explain dose-response to a parent in two sentences", "retrieval_item": "Q03", "improvement_evidence": ""},
        ],
        "qa": {
            "release_status": "faculty-review-needed",
            "gates_passed": ["runtime", "source", "taxonomy", "blueprint", "cjm_coverage", "outline", "script"],
            "defects": [
                {"severity": "minor", "slide_id": "-", "note": "[source gap] Tables 4.2, 4.3, 4.5a, 4.5b, 4.7 not retrievable at build (pressbooks.pub and ncbi.nlm.nih.gov blocked by egress proxy). S05, S07, S10, S14 are written from section-body facts; faculty to verify against the live chapter before promoting any slide to source-grounded."},
                {"severity": "minor", "slide_id": "-", "note": "[evidence] All clinical slides are source-aligned (paraphrase of indexed facts), not source-grounded; promotion to source-grounded requires verification against the chapter text by the faculty reviewer."},
                {"severity": "minor", "slide_id": "S16", "note": "[clinical judgment] The urgency-sort cue about bruising is an instructor-written illustration of the chapter's mandated-reporting rule, not a chapter example; confirm wording against agency policy."},
                {"severity": "minor", "slide_id": "-", "note": "[standards] slide-level standards_refs left empty per MVP scope. Package-level CA-BRN-ART3 refs BRN-14 and BRN-17 are proposed by the builder; faculty to confirm, and to decide whether BRN-16 (1426(d) integrated content: cultural diversity) also applies, before compliance_sync --apply."},
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
    print(f"wrote {out}: {len(spec['slides'])} slides, {n_card} with card_data, {len(clinical)} clinical slides all with source_refs="
          f"{all(s['source_refs'] for s in clinical)}, {len(spec['assessment_items'])} items")
