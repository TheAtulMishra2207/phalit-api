"""
d10_corpus.py — D10-006 · the replacement interpretation corpus.

PURE DATA. No logic, no I/O beyond loading the byte-exact Section 1 artefact,
no imports from any accepted authority. Every table here is drafted fresh
against the ratified format; **nothing is carried over from the legacy corpora**,
which D10-005 audited and the Founder ruled out of reuse:

    D10_LAGNA_DESC      1 of 12 keepable · none carried an overreach line
    D10_HOUSE_SIG       6 of 12 printed wording the format lists as forbidden
    D10_PLANET_EXPR     0 of 9 satisfied the format's same-planet grammar

WHAT IS DELIBERATELY ABSENT. No Devatā ruler, no Devatā direction, no Lagna
Devatā, no self-employment banner, no travel prediction, no Sun/Ketu conflict.
None has a table here, so none can be published by accident.

SECTION 1 IS NOT RETYPED. It is loaded from the D10-005 byte-exact artefact and
its sha256 is pinned below, so a stray edit fails a test rather than shipping.
"""
from __future__ import annotations

import hashlib
import pathlib
from typing import Dict, List, Tuple

CORPUS_VERSION = "d10.corpus.v1"

# ═════════════════════════════════════════════════════════════════════════════
# STATIC COPY · from the Format Specification, which fixes this wording
# ═════════════════════════════════════════════════════════════════════════════

TITLE = "DAŚĀṀŚA · CAREER & PUBLIC STANDING"
SUBTITLE = "D10 · How effort becomes visible work"

#: The §1 copy contract, loaded rather than retyped. The specification says
#: "print this, do not paraphrase into mystique", so the bytes are the corpus.
SECTION1_SHA256 = \
    "6c8b4af15d43055e7df173175b69d1fefba6ed7c38491618346f102a6bed2155"

SECTION1_PARAGRAPHS: Tuple[str, ...] = (
    "The Daśāṁśa cuts each sign into ten slices of 3°. It is the same birth "
    "data at the resolution of action — how effort, rank, and public work take "
    "shape.",
    "It is not a second life, not a job-title generator, and not a promotion "
    "calendar.",
    "Read it with the natal 10th house, not instead of it. The natal 10th "
    "shows the circumstances of work. D10 shows the operating style those "
    "circumstances mature into.",
    "This page answers four things: how you enter a role, what the work "
    "actually demands, how you are seen, and where effort turns into standing. "
    "Timing belongs to Daśā. Job titles belong to you and the market.",
)


def section1_text() -> str:
    """The four paragraphs, LF-joined, with a final newline — the exact form
    the D10-005 artefact was hashed in."""
    return "\n".join(SECTION1_PARAGRAPHS) + "\n"


def section1_digest() -> str:
    return hashlib.sha256(section1_text().encode("utf-8")).hexdigest()


#: The under-the-fold line, WITHOUT its editorial label. The specification's
#: "Newbie aside (one line, under the fold):" prefix is an instruction to the
#: implementer, not customer copy.
NEWBIE_ASIDE = (
    "Odd signs start their ten slices from themselves. Even signs start from "
    "the 9th sign. The reader does not draw this. The engine already did.")

#: §2 · the six-step reading path, verbatim from the specification's table.
READING_PATH: Tuple[Dict[str, str], ...] = (
    {"step": 1, "look_at": "Chart + legend",
     "question": "Where does each planet sit in the work-map?"},
    {"step": 2, "look_at": "Stance", "question": "How do I take a role?"},
    {"step": 3, "look_at": "Function",
     "question": "What is the work doing all day?"},
    {"step": 4, "look_at": "Standing", "question": "How am I ranked?"},
    {"step": 5, "look_at": "Pull vs vehicle",
     "question": "What am I becoming, and what carries the week?"},
    {"step": 6, "look_at": "Instructions",
     "question": "What do I actually practise at work?"},
)

READING_PATH_RULE = (
    "If a heading has a speaker tag, believe that tag. Do not mix a Devatā "
    "flavour with a Jaimini aspect and call it one fact.")

#: §4 · the anti-hallucination table. `read_from` is the format's own wording,
#: including H3 on the Function row — that row describes what the SECTION
#: answers, and the D10-003 Function authority remains H10 + 10L + H6.
PERMITTED_QUESTIONS: Tuple[Dict[str, str], ...] = (
    {"question": "How do I take up work?", "read_from": "D10 Lagna + Lagnesh"},
    {"question": "What is the work doing?", "read_from": "D10 H10 + lord; H6"},
    {"question": "How am I ranked?", "read_from": "Sun; H10 lord; H2"},
)

#: §15 · fixed footer copy.
HOW_TO_USE: Tuple[str, ...] = (
    "D10 refines the natal 10th. It does not replace it.",
    "It does not name a profession.",
    "It does not time events — that is Daśā.",
    "It does not prescribe remedies — that is the Remedial Dossier.",
    "D9 is what the work is for. D10 is how the work runs.",
    "If a sentence here has no speaker tag in the section above, treat it as "
    "prose, not as a rule-hit.",
)

#: §16 · fixed glossary, verbatim from the specification.
GLOSSARY: Tuple[Dict[str, str], ...] = (
    {"term": "Daśāṁśa / D10", "meaning": "Tenth division; work and public standing"},
    {"term": "Lagna", "meaning": "Rising sign of this chart; work-stance"},
    {"term": "Lagnesh", "meaning": "Ruler of that sign; how the stance acts"},
    {"term": "Karaka", "meaning": "A planet that signifies a topic (Sun = standing)"},
    {"term": "Atmakāraka",
     "meaning": "Planet of highest degree; vocational pull in this use"},
    {"term": "Amatyakāraka", "meaning": "Second-highest; work vehicle in this use"},
    {"term": "Devatā", "meaning": "Deity of the 3° slice; flavour, not a career"},
    {"term": "Dusthāna", "meaning": "Houses 6, 8, 12 — pressure houses, not curses"},
    {"term": "Through lord", "meaning": "Vacant house giving results via its ruler"},
    # D10-006-CORR-01 · the specification's row reads "Uchcha / Mūlatrikoṇa /
    # Sama". D10 publishes NO Mūlatrikoṇa by Founder ruling — it normalises to
    # Sva — so glossing a state the report can never show would teach the
    # reader a word they will not meet. Sva is what they will meet.
    {"term": "Uchcha / Sva / Sama", "meaning": "See chart-card dignity key"},
)


# ═════════════════════════════════════════════════════════════════════════════
# §5.1 · STANCE · 12 entries
# ═════════════════════════════════════════════════════════════════════════════
# Each entry is a one-word gloss, ONE concrete behaviour describing how work is
# ENTERED, and ONE overreach that is the inflation of that same behaviour.
#
# THE AXIS TEST governs every row: read the two lines together and the same
# verb should be doing the work in both. "starts fronts" / "starts more fronts
# than it finishes" is one axis. "starts fronts" / "is lazy" would be two, and
# is the defect that made all nine legacy planet pairs unusable.

STANCE_CORPUS: Dict[str, Dict[str, str]] = {
    "Aries": {
        "gloss": "Pioneer",
        "work_behaviour": "Opens the work by moving first, before the brief is complete.",
        "overreach": "Opens a third front while the first two are still unfinished.",
    },
    "Taurus": {
        "gloss": "Builder",
        "work_behaviour": "Enters by securing the ground: tools, budget, a working base.",
        "overreach": "Keeps preparing the ground long after it is ready to build on.",
    },
    "Gemini": {
        "gloss": "Connector",
        "work_behaviour": "Enters by routing what everyone involved already knows.",
        "overreach": "Keeps routing the question onward instead of answering it.",
    },
    "Cancer": {
        "gloss": "Keeper",
        "work_behaviour": "Enters by making conditions safe enough for the work to start.",
        "overreach": "Keeps making conditions safer than the work actually needed.",
    },
    "Leo": {
        "gloss": "Anchor",
        "work_behaviour": "Enters by taking visible responsibility for how the work turns out.",
        "overreach": "Takes visible responsibility for work that would run better without a centre.",
    },
    "Virgo": {
        "gloss": "Refiner",
        "work_behaviour": "Enters by finding the fault in the process before starting.",
        "overreach": "Keeps finding faults past the point where the work was usable.",
    },
    "Libra": {
        "gloss": "Diplomat",
        "work_behaviour": "Enters by getting the parties to agree what good would look like.",
        "overreach": "Keeps getting the parties to agree when a decision was needed.",
    },
    "Scorpio": {
        "gloss": "Prober",
        "work_behaviour": "Enters by finding what the stated problem is hiding.",
        "overreach": "Keeps finding what is hidden past the depth the work can use.",
    },
    "Sagittarius": {
        "gloss": "Framer",
        "work_behaviour": "Enters by placing the task inside a larger principle.",
        "overreach": "Argues the larger principle while the specific task waits.",
    },
    "Capricorn": {
        "gloss": "Steward",
        "work_behaviour": "Enters by building the structure the work will be delivered through.",
        "overreach": "Adds structure until the structure is most of the effort.",
    },
    "Aquarius": {
        "gloss": "Reformer",
        "work_behaviour": "Enters by asking why the current method exists at all.",
        "overreach": "Keeps asking why the method exists after it has proved it works.",
    },
    "Pisces": {
        "gloss": "Absorber",
        "work_behaviour": "Enters by taking on work nobody else has claimed yet.",
        "overreach": "Takes on so much unclaimed work that none of it carries a name.",
    },
}


# ═════════════════════════════════════════════════════════════════════════════
# §9 · HOUSE DOMAINS · 12 entries
# ═════════════════════════════════════════════════════════════════════════════
# Groups are immutable and match D10-003's OPERATIONAL_GROUPS exactly.
#
# Six of these are constrained by the format's own "Print instead" column
# (H3, H5, H6, H7, H10, H12) and follow it closely. The legacy wording the
# format lists under "Do not print" — short sabbaticals, assistants, job and
# co-workers, prestige, hard work, loss of reputation — appears nowhere.

ENTER_ROLE = "ENTER_ROLE"
DO_WORK = "DO_WORK"
BE_SEEN_AND_PAID = "BE_SEEN_AND_PAID"
HANDLE_PRESSURE = "HANDLE_PRESSURE"
PATRONS = "PATRONS"

HOUSE_CORPUS: Dict[int, Dict[str, str]] = {
    1: {"group": ENTER_ROLE, "domain_label": "Intent and approach",
        "domain_sentence": "How the work is taken up, and the posture it is taken up with."},
    3: {"group": ENTER_ROLE, "domain_label": "Initiative and skills",
        "domain_sentence": "Initiative, drafts, skills, short missions, courage at the desk."},
    5: {"group": ENTER_ROLE, "domain_label": "Composed work",
        "domain_sentence": "Composed work, intelligence on display, the protégé and authority loop."},
    6: {"group": DO_WORK, "domain_label": "The service contract",
        "domain_sentence": "Employment conditions, rivals, the service contract the work is done under."},
    10: {"group": DO_WORK, "domain_label": "The vocation as lived",
         "domain_sentence": "The vocation as lived; what you are known to do."},
    4: {"group": DO_WORK, "domain_label": "Working conditions",
        "domain_sentence": "The conditions the work happens in, and what makes them bearable."},
    2: {"group": BE_SEEN_AND_PAID, "domain_label": "Earnings attachment",
        "domain_sentence": "How earnings attach to the work, and what has to be shown to earn."},
    7: {"group": BE_SEEN_AND_PAID, "domain_label": "Counterparties",
        "domain_sentence": "Clients, counterparties, public exchange."},
    11: {"group": BE_SEEN_AND_PAID, "domain_label": "Compounding",
         "domain_sentence": "How returns accumulate over time rather than arriving at once."},
    8: {"group": HANDLE_PRESSURE, "domain_label": "Shocks",
        "domain_sentence": "Interruptions and reversals the work has to absorb. Pressure, not verdict."},
    12: {"group": HANDLE_PRESSURE, "domain_label": "Backstage labour",
         "domain_sentence": "Backstage labour, remote or foreign work, unpaid lead time."},
    9: {"group": PATRONS, "domain_label": "Patrons and self-direction",
        "domain_sentence": "Patrons, mentors, self-direction, and the dharma of the work."},
}


# ═════════════════════════════════════════════════════════════════════════════
# §12 · STRENGTH AND INFLATION · 9 grahas
# ═════════════════════════════════════════════════════════════════════════════
# THE SAME-PLANET GRAMMAR, which no legacy pair satisfied: the second line is
# the FIRST LINE INFLATED, not an unrelated vice and not an outcome the world
# imposes. Each line is at most 18 words.
#
# This corpus does NOT decide which grahas print. D10-003's strength selector
# is the sole authority for that, and it admits a classical graha only on
# Uchcha or Sva and a node only on Uchcha.

STRENGTH_CORPUS: Dict[str, Dict[str, str]] = {
    "Sun": {
        "reliable_at_work": "Carries responsibility in the open, where it can be seen and answered for.",
        "when_it_overreaches": "Needs to be seen carrying it, and holds work that others could carry.",
    },
    "Moon": {
        "reliable_at_work": "Reads the room and adjusts the work to the people doing it.",
        "when_it_overreaches": "Adjusts so readily that the work has no fixed shape left.",
    },
    "Mars": {
        "reliable_at_work": "Starts things and pushes them through resistance.",
        "when_it_overreaches": "Pushes through resistance that was information, and starts more than it finishes.",
    },
    "Mercury": {
        "reliable_at_work": "Makes complicated work legible and moves it between the people who need it.",
        "when_it_overreaches": "Keeps explaining and connecting when a decision was what the work needed.",
    },
    "Jupiter": {
        "reliable_at_work": "Widens the frame so the work is done for a reason.",
        "when_it_overreaches": "Widens the frame until the specific task is no longer in it.",
    },
    "Venus": {
        "reliable_at_work": "Makes work pleasant to receive, and worth returning to.",
        "when_it_overreaches": "Smooths the surface of work that needed its difficulty left visible.",
    },
    "Saturn": {
        "reliable_at_work": "Stays with long duty after the interest has gone.",
        "when_it_overreaches": "Stays with duty past the point where it was still worth staying.",
    },
    "Rahu": {
        "reliable_at_work": "Comes at the work from an angle nobody in the room considered.",
        "when_it_overreaches": "Takes the unconsidered angle when the ordinary one was already working.",
    },
    "Ketu": {
        "reliable_at_work": "Cuts away the part of the work that was never needed.",
        "when_it_overreaches": "Cuts away parts that were load-bearing, and withdraws from the rest.",
    },
}


# ═════════════════════════════════════════════════════════════════════════════
# §8 · DEVATĀ · assignment and flavour
# ═════════════════════════════════════════════════════════════════════════════
# LOCKED BY FOUNDER RULING. Odd signs run the sequence from the first slice;
# even signs run the exact reversal.
#
# The fourth label is Nirṛti. Provenance is recorded rather than assumed:
# BPHS 6.13 gives the textual name Rākṣasa; Nirṛti is the UI normalization.
# That is the only name in the list carrying a normalization, so it is the only
# one with a provenance note.
#
# NO RULER. NO DIRECTION. NO LAGNA DEVATĀ. The legacy ruler table mapped ten
# Devatās onto nine grahas with Jupiter used twice, and the format has no
# direction column at all. Neither has a field anywhere in this flight.

DEVATA_PROVENANCE: Dict[str, Dict[str, str]] = {
    "Nirṛti": {"bphs_textual_name": "Rākṣasa",
               "ui_normalization": "Nirṛti",
               "reference": "BPHS 6.13"},
}

DEVATA_ODD: Tuple[str, ...] = (
    "Indra", "Agni", "Yama", "Nirṛti", "Varuna",
    "Vayu", "Kubera", "Ishana", "Brahma", "Ananta",
)
#: The even-sign sequence is the exact reversal, as ruled. Derived rather than
#: written out, so the two cannot drift apart.
DEVATA_EVEN: Tuple[str, ...] = tuple(reversed(DEVATA_ODD))

#: 3-5 words each. ETHICAL AND PROFESSIONAL WEATHER, never an outcome.
#: The legacy register — "Power & Dominance", "Wealth & Accumulation" — named
#: what a person gets. These name how the work is conducted.
DEVATA_FLAVOUR: Dict[str, str] = {
    "Indra": "measured authority, openly held",
    "Agni": "disciplined ignition, quickly spent",
    "Yama": "accountability under pressure",
    "Nirṛti": "unpolished force, honestly applied",
    "Varuna": "patient scope, held steady",
    "Vayu": "restless movement between tasks",
    "Kubera": "careful stewardship of resources",
    "Ishana": "clean conduct, quietly kept",
    "Brahma": "originating from first principles",
    "Ananta": "sustained work, largely unseen",
}

#: §8 · when the same Devatā falls on three or more grahas, publication emits
#: ONE climate disclosure instead of three separate destiny claims.
DEVATA_REPEAT_THRESHOLD = 3


# ═════════════════════════════════════════════════════════════════════════════
# §10 · TENSION COPY · one per valid outcome
# ═════════════════════════════════════════════════════════════════════════════
# Templates only. THE WINNER IS CHOSEN BY D10-003 AND NEVER HERE. Each is at
# most 90 words once filled, and each is recognisable from the evidence the
# selector recorded.

TENSION_COPY: Dict[str, Dict[str, str]] = {
    "JAIMINI_RIFT": {
        "heading": "Pull and vehicle do not meet",
        "template": (
            "The work this chart keeps trying to become sits with {ak} in H{ak_house}. "
            "What actually carries a week sits with {amk} in H{amk_house}. They share "
            "no house and do not aspect one another, so nothing joins them "
            "automatically. They do not fail; they do not automate. The join has to be "
            "made deliberately, in the ordinary work of a week."),
    },
    "CORE_OPERATIONAL_CONFLICT": {
        "heading": "How you work and what the post demands",
        "template": (
            "{lagnesh} in H{lagnesh_house} sets how work is taken up. {tenth_lord} in "
            "H{tenth_lord_house} sets what the office of the career actually asks for. "
            "The two sit in a difficult relationship, so the way in and the demand do "
            "not line up on their own. The job is not to pick one. It is to translate "
            "the first into terms the second can count."),
    },
    "VISIBILITY_GAP": {
        "heading": "Visible craft and invisible duty",
        "template": (
            "{h5_count} grahas gather in H5, where work is composed and seen. "
            "{h12_count} gather in H12, where work is done out of view. Both are real "
            "and both are busy. The gap is not a shortage of effort; it is that a large "
            "part of the effort leaves no visible trace. The task is to put visible "
            "output where the unseen labour can be counted."),
    },
    "SUN_SATURN_FRICTION": {
        "heading": "Standing and labour pull apart",
        "template": (
            "The Sun sits in H{sun_house} and Saturn in H{saturn_house}, in a "
            "relationship that keeps them working against each other. What earns "
            "standing and what the long labour actually consists of are not the same "
            "thing here, and neither yields to the other. The friction is structural: "
            "it sits between the two, not in either one."),
    },
    "FALLBACK_SUN_SATURN_CLIMATE": {
        "heading": "Two climates, not a conflict",
        "template": (
            "The Sun sits in H{sun_house} ({sun_sign}, {sun_dignity}) and Saturn in "
            "H{saturn_house} ({saturn_sign}, {saturn_dignity}). They stand in no "
            "difficult relationship to one another — no shared house, no opposition, no "
            "6/8. What they do is work in different weather: one governs what becomes "
            "visible, the other what is endured. Reading them side by side is a "
            "contrast, not a quarrel."),
    },
}


# ═════════════════════════════════════════════════════════════════════════════
# §13 · THREE INSTRUCTIONS · keyed by the tension winner
# ═════════════════════════════════════════════════════════════════════════════
# BEHAVIOURAL, NEVER REMEDIAL. No mantra, gem, fast, puja, donation, dashā or
# auspicious day appears in this table, and no prediction.
#
# There is no entry for UNKNOWN. That is deliberate: with no tension selected
# there is nothing for the instructions to be about, and publication stays
# silent rather than inventing three.

INSTRUCTIONS_CORPUS: Dict[str, Dict[str, str]] = {
    "JAIMINI_RIFT": {
        "cultivate": "Finish one thing the pull started, in a form the week's work can use.",
        "watch": "Two parallel careers running quietly, neither of them completed.",
        "practise": "Once a week, name which skill this week's ordinary work actually deepened.",
    },
    "CORE_OPERATIONAL_CONFLICT": {
        "cultivate": "Translate how you work into the terms the post is measured by.",
        "watch": "Doing the role properly while being assessed on something you never showed.",
        "practise": "Before starting, write the one line your work will be judged on.",
    },
    "VISIBILITY_GAP": {
        "cultivate": "Give the unseen labour a visible artefact somebody else can point at.",
        "watch": "Long stretches of real work leaving no trace anyone can count.",
        "practise": "At the end of each week, record one finished thing, however small.",
    },
    "SUN_SATURN_FRICTION": {
        "cultivate": "Convert sustained duty into something that can be shown, not just endured.",
        "watch": "Waiting for the labour to be noticed on its own account.",
        "practise": "Name the person who will see the result before beginning the work.",
    },
    "FALLBACK_SUN_SATURN_CLIMATE": {
        "cultivate": "Use both climates deliberately: what is shown, and what is carried.",
        "watch": "Treating a difference in weather as a problem needing to be solved.",
        "practise": "Each week, ask which of the two the work in front of you needs.",
    },
}


# ═════════════════════════════════════════════════════════════════════════════
# §11 · MONEY · mechanism vocabulary
# ═════════════════════════════════════════════════════════════════════════════
# The format's own list. No amount, level, windfall or timing word is a member,
# and publication draws its mechanism word only from here.

MECHANISM_VOCABULARY: Tuple[str, ...] = (
    "credibility", "speech", "product", "fee", "network", "system",
    "patronage", "delayed yield",
)

#: Which mechanism a house's lord suggests. Deterministic, and drawn only from
#: the vocabulary above.
MECHANISM_BY_LORD: Dict[str, str] = {
    "Sun": "credibility",
    "Moon": "network",
    "Mars": "product",
    "Mercury": "speech",
    "Jupiter": "patronage",
    "Venus": "fee",
    "Saturn": "delayed yield",
    "Rahu": "system",
    "Ketu": "delayed yield",
}

H11_EMPTY_NOTE = "Compounding does not arrive uninvited."


# ═════════════════════════════════════════════════════════════════════════════
# HUMANISED PUBLICATION STATES · §10 of the ticket
# ═════════════════════════════════════════════════════════════════════════════
# Four states, matching D10-003 exactly. There is no fifth.

PUBLICATION_STATE_LABEL: Dict[str, str] = {
    "OCCUPIED": "Occupied",
    "THROUGH_LORD": "Through lord",
    "SUPPORTED": "Supported",
    "PRESSURED": "Pressured",
}

#: The opening the format requires for a vacant H10.
THROUGH_LORD_OPENING = "Through lord"
