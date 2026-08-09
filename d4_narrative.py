"""
d4_narrative.py — D4-008 · PROVIDER BRIEF AND AUTHORITY BOUNDARY.

THE ARCHITECTURE IN ONE LINE
    server facts -> deterministic Property / Vahana / Dasha blocks -> provider
    EXPLANATION ONLY.

The provider has ZERO authority to select, alter or infer a D4 state. The state
is already chosen by d4_property_state.py before a single token is sent, and the
brief below carries the RESULT, never the raw material a model could reclassify
from. That is the point of an allowlist: a model cannot re-derive a verdict it
was never given the inputs for.

WHAT THE BRIEF DELIBERATELY EXCLUDES
  * the raw chart, the planet table, degrees, houses and every audit structure
  * any literal property count, in any form
  * every legacy corpus — ChV_DATA, CHATURTHA_YOGAS, D4_PLANET_PROP and the rest
  * Moksha / spiritual-orientation material
  * maternal health or longevity material, because the certified evidence does
    not support that narrative and a model given fragments would invent one
  * any vehicle tier, because the taxonomy is not Founder-locked
  * birth data of any kind

DASHA STAYS CONTEXT. The envelope repeats the boundary sentence verbatim so the
model reads it beside the data rather than only in the system prompt.

THE OUTPUT SIDE, ADDED IN D4-008-CORR-01. The module now also bounds what the
provider EMITS. The earlier delivery flagged this gap and argued against fixing
it, on the grounds that a scrubber mangles legitimate prose and hides provider
misbehaviour. That reasoning was right about SCRUBBING and wrong to conclude no
guard was possible: `validate_provider_output` REJECTS THE WHOLE NARRATIVE
rather than repairing any part of it, which avoids the scrubber problem
entirely. Nothing is rewritten, nothing is redacted, and no "safe" paragraph is
salvaged from a violating response — the route fails closed into the existing
sanitized 502 and the reader sees the neutral unavailable state, with the
deterministic evidence above it untouched.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

D4_NARRATIVE_VERSION = "d4-narrative-1.0.0"

#: The four user-facing sections, fixed. The model may not add or rename one.
SECTION_TITLES = (
    "Property Capacity & Stability",
    "Home & Asset Pattern",
    "Vehicles & Material Comforts",
    "Current Timing Context",
)

DASHA_BOUNDARY_SENTENCE = (
    "A concurrence means only that the current Dasha lord is one of the grahas "
    "structurally participating in the selected D4 state. It asserts no event, "
    "no timing and no outcome."
)


class D4NarrativeError(ValueError):
    """The accepted deterministic blocks are not shaped as this module requires.
    Internal only — the route converts it to a neutral correlated error."""


def _require(block: Dict[str, Any], keys, what: str) -> None:
    if not isinstance(block, dict):
        raise D4NarrativeError(what + " is not an object")
    for k in keys:
        if k not in block:
            raise D4NarrativeError(what + " is missing a required field")


def build_narrative_brief(property_state: Dict[str, Any],
                          vahana_evidence: Dict[str, Any],
                          dasha_context: Dict[str, Any]) -> Dict[str, Any]:
    """The bounded envelope. SELECTION ONLY — nothing is computed here.

    Every value is copied from a block the accepted deterministic pipeline
    already produced, so the brief cannot disagree with the surface the reader
    is looking at.
    """
    _require(property_state, ("selected_state", "category", "resolution",
                              "d4_primary", "d1_root_context"), "property_state")
    _require(vahana_evidence, ("venus", "contact_paths",
                               "direct_venus_vahana_contact", "vahana_sthana"),
             "vahana_evidence")
    _require(dasha_context, ("md_status", "ad_status", "concurrence_summary",
                             "timing_applicability"), "dasha_context")

    prim = property_state["d4_primary"]
    root = property_state["d1_root_context"]
    fh = prim.get("fourth_house", {})
    fl = prim.get("fourth_lord", {})
    aff = prim.get("affliction_evidence", {})
    contact = prim.get("contact_evidence", {})

    ven = vahana_evidence["venus"]
    sth = vahana_evidence["vahana_sthana"]
    sfl = sth.get("fourth_lord", {})

    return {
        "narrative_version": D4_NARRATIVE_VERSION,
        "authority": {
            "state_selected_by": "server",
            "provider_may_select_state": False,
            "provider_may_rank_states": False,
            "provider_may_create_yoga": False,
        },
        "property": {
            "selected_state": property_state["selected_state"],
            "category": property_state["category"],
            "resolution": property_state["resolution"],
            "matched_states": list(property_state.get("matched_states", [])),
            "is_coverage_fallback": property_state["resolution"] == "coverage_fallback",
            "d4_fourth_house_sign": fh.get("sign"),
            "d4_fourth_house_occupants": list(fh.get("occupants", [])),
            "d4_fourth_house_aspected_by": list(fh.get("aspects_received", [])),
            "d4_fourth_lord": fl.get("graha"),
            "d4_fourth_lord_sign": fl.get("d4_sign"),
            "d4_fourth_lord_house": fl.get("d4_house"),
            "d4_fourth_lord_dignity": fl.get("dignity"),
            "d4_fourth_lord_vargottama": fl.get("vargottama"),
            "fourth_lord_free_from_dusthana_affliction":
                aff.get("fourth_lord_free_from_dusthana_affliction"),
            "benefic_contact_count": contact.get("benefic_count"),
            "malefic_contact_count": contact.get("malefic_count"),
            "benefic_cancellation": contact.get("benefic_cancellation"),
        },
        "vahana": {
            "venus_sign": ven.get("d4_sign"),
            "venus_house": ven.get("d4_house"),
            "venus_dignity": ven.get("d4_dignity"),
            "venus_vargottama": ven.get("vargottama"),
            "venus_aspected_by": list(ven.get("aspects_received", [])),
            "venus_is_fourth_lord": ven.get("is_fourth_lord"),
            "direct_venus_contact": vahana_evidence["direct_venus_vahana_contact"],
            "contact_paths": dict(vahana_evidence["contact_paths"]),
            "sthana_sign": sth.get("sign"),
            "sthana_occupants": list(sth.get("occupants", [])),
            "sthana_aspected_by": list(sth.get("aspects_received", [])),
            "sthana_fourth_lord": sfl.get("graha"),
            "sthana_fourth_lord_sign": sfl.get("d4_sign"),
            "sthana_fourth_lord_dignity": sfl.get("d4_dignity"),
            # Stated as a FACT in the data, not only in the prompt, so the model
            # reads it beside the evidence it might otherwise embellish.
            "no_vehicle_tier_exists": True,
            "vehicle_tier_note": ("No vehicle or comfort tier has been defined. Do not "
                                  "describe vehicles as premium, luxury, moderate or any "
                                  "other grade, and do not rank them."),
        },
        "dasha": {
            "current_mahadasha": dasha_context.get("current_mahadasha"),
            "current_antardasha": dasha_context.get("current_antardasha"),
            "md_status": dasha_context["md_status"],
            "ad_status": dasha_context["ad_status"],
            "concurrence_summary": dasha_context["concurrence_summary"],
            "timing_applicability": dasha_context["timing_applicability"],
            "selected_state_participants":
                list(dasha_context.get("selected_state_participant_grahas", [])),
            "policy": "context_only_structural_concurrence_not_activation",
            "boundary": DASHA_BOUNDARY_SENTENCE,
        },
        "d1_root_context": {
            "role": "SUPPORTING ONLY",
            "fourth_house_sign": root.get("fourth_house_sign"),
            "fourth_lord": root.get("fourth_lord"),
            "fourth_lord_dignity": root.get("fourth_lord_dignity"),
            "selects_or_overrides_d4_state": False,
            "note": ("supporting natal context; it may support sections 1-2 but may "
                     "never contradict or replace the D4 evidence above"),
        },
    }


SYSTEM_PROMPT = """You are writing an interpretive explanation for a Vedic astrology platform.

THE MOST IMPORTANT RULE: THE RESULT IS ALREADY DETERMINED.
The D4 property state has already been selected by the platform's deterministic
engine. Your job is to EXPLAIN the supplied result in readable prose. You are not
performing astrology and you are not being asked to.

You may NOT:
1. choose a different state, or suggest another state might apply;
2. rank, compare or weigh competing states against each other;
3. create, name or imply a yoga or combination that is not in the supplied data;
4. alter, reinterpret or second-guess the selected state or its category;
5. state or estimate a number of properties, now or over a lifetime;
6. give a purchase date, timeframe, window or season;
7. say an acquisition is guaranteed, certain, assured or inevitable;
8. say litigation, dispute or loss is certain or will occur;
9. describe vehicles by tier, grade or quality — no premium, luxury, moderate or
   equivalent, and no ranking of vehicles;
10. treat a Dasha concurrence as an activation, trigger, fruition, manifestation
    or imminent event;
11. make any claim about the mother's health, longevity, survival or character;
12. introduce Moksha, spiritual liberation, or a material-versus-spiritual
    orientation of the soul.

DASHA BOUNDARY. A concurrence means ONLY that the current Dasha lord is one of
the grahas structurally participating in the selected state. It asserts no event,
no timing and no outcome. If a status is "unknown", say the current timing
information is unavailable. If timing applicability is a coverage fallback, say
timing concurrence is not applicable because the result is a general baseline
rather than a matched combination.

D1 is SUPPORTING CONTEXT ONLY. It may add nuance to sections 1 and 2. It may
never contradict, override or replace the D4 result.

Write EXACTLY these four sections, each with '### ' before the heading, in this
order and with no others:
### Property Capacity & Stability
### Home & Asset Pattern
### Vehicles & Material Comforts
### Current Timing Context

Each section is 3-6 sentences of direct, readable prose. No bullet points, no
headings beyond the four above, no preamble and no closing summary. Use only the
supplied data; add no external knowledge."""


def build_user_prompt(brief: Dict[str, Any]) -> str:
    """The brief, rendered as labelled lines. No birth data, no chart, no count."""
    p, v, d, r = brief["property"], brief["vahana"], brief["dasha"], brief["d1_root_context"]
    fallback = ("This is a COVERAGE FALLBACK: no specific combination matched, so describe "
                "a general baseline and do not present it as a matched combination."
                if p["is_coverage_fallback"] else
                "Matched combinations: " + (", ".join(p["matched_states"]) or "none"))
    return "\n".join([
        "SELECTED D4 PROPERTY STATE (already determined by the platform; explain it):",
        "  state: " + str(p["selected_state"]),
        "  category: " + str(p["category"]),
        "  " + fallback,
        "",
        "D4 PRIMARY EVIDENCE:",
        "  4th house sign: " + str(p["d4_fourth_house_sign"]),
        "  4th house occupants: " + (", ".join(p["d4_fourth_house_occupants"]) or "none"),
        "  4th house aspected by: " + (", ".join(p["d4_fourth_house_aspected_by"]) or "none"),
        "  4th lord: " + str(p["d4_fourth_lord"]) + " in " + str(p["d4_fourth_lord_sign"])
        + ", house " + str(p["d4_fourth_lord_house"]),
        "  4th lord dignity: " + str(p["d4_fourth_lord_dignity"]),
        "  4th lord vargottama: " + str(p["d4_fourth_lord_vargottama"]),
        "  4th lord free from 6/8/12 affliction: "
        + str(p["fourth_lord_free_from_dusthana_affliction"]),
        "  supportive vs difficult contacts: " + str(p["benefic_contact_count"]) + " vs "
        + str(p["malefic_contact_count"]),
        "",
        "VAHANA AND MATERIAL COMFORTS (mechanical evidence only):",
        "  Venus: " + str(v["venus_sign"]) + ", house " + str(v["venus_house"])
        + ", dignity " + str(v["venus_dignity"]),
        "  Venus vargottama: " + str(v["venus_vargottama"]),
        "  Venus aspected by: " + (", ".join(v["venus_aspected_by"]) or "none"),
        "  direct Venus contact with the 4th house or its lord: " + str(v["direct_venus_contact"]),
        "  Vahana Sthana sign: " + str(v["sthana_sign"]),
        "  Sthana occupants: " + (", ".join(v["sthana_occupants"]) or "none"),
        "  " + v["vehicle_tier_note"],
        "",
        "CURRENT DASHA CONTEXT (context only):",
        "  current Mahadasha: " + (str(d["current_mahadasha"]) if d["current_mahadasha"]
                                   else "unavailable"),
        "  Mahadasha status: " + str(d["md_status"]),
        "  current Antardasha: " + (str(d["current_antardasha"]) if d["current_antardasha"]
                                    else "unavailable"),
        "  Antardasha status: " + str(d["ad_status"]),
        "  summary: " + str(d["concurrence_summary"]),
        "  applicability: " + str(d["timing_applicability"]),
        "  " + d["boundary"],
        "",
        "D1 ROOT CONTEXT (" + r["role"] + "):",
        "  D1 4th house sign: " + str(r["fourth_house_sign"]),
        "  D1 4th lord: " + str(r["fourth_lord"]) + ", dignity " + str(r["fourth_lord_dignity"]),
        "  " + r["note"],
        "",
        "Write the four sections now.",
    ])


# ── the output contract ─────────────────────────────────────────────────────
#
# Every rule below is FAIL-CLOSED and REJECTS THE ENTIRE NARRATIVE. None of them
# edits, redacts or partially retains anything. A rule is either scoped GLOBAL
# (the vocabulary has no legitimate use anywhere in a D4 explanation) or scoped
# to one section, where a word that is fine elsewhere is prohibited.

_WORD_NUMBERS = (r"one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|"
                 r"a couple of|several|multiple|numerous")
# D4-008-CORR-02 · the vocabulary a count can be expressed in is wider than the
# first pass allowed. "pieces of real estate" and "real-estate holdings" are the
# same claim as "properties" and must be caught by the same rule.
_ASSET_NOUNS = (r"propert(?:y|ies)|homes?|houses|plots?|flats?|apartments?|dwellings?|"
                r"land\s+parcels?|residences?|real[-\s]?estate\s+holdings?|"
                r"pieces?\s+of\s+real[-\s]?estate|holdings?|real[-\s]?estate")

#: Up to two intervening words, so "4 RESIDENTIAL properties" and "three
#: REAL-ESTATE holdings" are caught. Bounded at two deliberately: an unbounded
#: gap would let a number anywhere in a sentence bind to an unrelated noun.
_ADJ_GAP = r"(?:[A-Za-z][A-Za-z-]*\s+){0,2}"

#: A literal lifetime asset COUNT. The digit alternative is \d+ with word
#: boundaries, so an ORDINAL like "4th house" cannot match — that phrase is a
#: house reference, not a count, and rejecting it would make the guard useless.
_COUNT_RULES = [
    (r"\b(?:\d+|" + _WORD_NUMBERS + r")\s+" + _ADJ_GAP + r"(?:" + _ASSET_NOUNS + r")\b",
     "a literal asset count"),
    (r"\bproperty\s+count\b", "an explicit property count"),
    (r"\bnumber\s+of\s+(?:" + _ASSET_NOUNS + r")\b", "a number-of-properties claim"),
    (r"\bcount\s*[:=]\s*\d+", "a numeric count field"),
]

#: Acquisition / property-event vocabulary, used to scope the year rules.
_ACQ_TRIGGER = (r"(?:acquisitions?|acquires?|acquiring|acquired|purchas(?:e|es|ing|ed)|"
                r"buy|buying|bought|owns?|owning|ownership|propert(?:y|ies)|"
                r"real[-\s]?estate|holdings?|homes?)")

_TIMING_RULES = [
    (r"\bwithin\s+(?:\d+|" + _WORD_NUMBERS + r")\s+(?:days?|weeks?|months?|years?)\b",
     "a predictive time window"),
    (r"\bin\s+the\s+next\s+(?:\d+|" + _WORD_NUMBERS + r")\s+(?:months?|years?)\b",
     "a predictive time window"),
    (r"\bpurchase\s+(?:date|window|period|time|timing)\b", "a purchase timing claim"),
    (r"\bby\s+(?:19|20)\d\d\b", "a predictive year"),
    # D4-008-CORR-02 · "in/during/around YEAR" is only a violation when it is
    # doing ACQUISITION or PROPERTY-EVENT work. A global four-digit ban would
    # reject ordinary prose that merely mentions a year, so the rule is scoped
    # by proximity in BOTH directions.
    #
    # NOTE ON THE TRIGGER LIST: bare "house" is deliberately EXCLUDED. Including
    # it would let "the 4th house" bind to any year in the same sentence and
    # start rejecting correct prose — the exact false-positive class this
    # ticket forbids. "home", "property" and the acquisition verbs carry it.
    (_ACQ_TRIGGER + r"[^.]{0,60}?\b(?:in|during|around|by)\s+(?:19|20)\d\d\b",
     "an acquisition-year prediction"),
    (r"\b(?:in|during|around|by)\s+(?:19|20)\d\d\b[^.]{0,60}?" + _ACQ_TRIGGER,
     "an acquisition-year prediction"),
    (r"\b(?:19|20)\d\d\s*[-–]\s*(?:19|20)\d\d\b", "a predictive year range"),
    (r"\b(?:in|during|around)\s+(?:january|february|march|april|may|june|july|august|"
     r"september|october|november|december)\b", "a predictive month"),
    (r"\b(?:next|coming)\s+(?:spring|summer|autumn|fall|winter)\b", "a predictive season"),
]

_CERTAINTY_RULES = [
    (r"\bguarantee[sd]?\b", "a guarantee"),
    (r"\bassured\b", "an assurance"),
    (r"\binevitab(?:le|ly)\b", "an inevitability claim"),
    (r"\bwill\s+definitely\b", "a definite-outcome claim"),
    # "certain" only where it is doing predictive work. "a certain kind of
    # stability" is ordinary English and must not trip the guard.
    (r"\b(?:is|are)\s+certain\s+to\b", "a certainty claim"),
    (r"\bcertain\s+to\s+(?:acquire|own|lose|face|encounter)\b", "a certainty claim"),
    (r"\bcertainty\s+of\s+(?:acquisition|purchase|loss|litigation|dispute)\b",
     "a certainty claim"),
]

#: Activation vocabulary. GLOBAL: none of it has a legitimate use in a Dasha
#: CONTEXT block, which may only explain structural concurrence.
_ACTIVATION_RULES = [
    (r"\bactivat(?:e|es|ed|ing|ion)\b", "activation language"),
    (r"\btrigger(?:s|ed|ing)?\b", "trigger language"),
    (r"\bfruition\b", "fruition language"),
    (r"\bmanifestation\b", "manifestation language"),
    (r"\bimminent(?:ly)?\b", "imminence language"),
    (r"\bpurchase\s+window\b", "a purchase window"),
    (r"\blitigation\s+period\b", "a litigation period"),
]

_MATERNAL_RULES = [
    (r"\b(?:mother|mother's|maternal)\b[^.]{0,80}?"
     r"\b(?:health|longevity|lifespan|life\s+expectancy|survival|survives?|illness|"
     r"disease|die|dies|death|long-?lived|short-?lived|"
     # D4-008-CORR-02 · "a long life" / "a short life" is the same longevity
     # claim as "long-lived" and was slipping through on the hyphen alone.
     r"long\s+life|short\s+life|longer\s+life|shorter\s+life|full\s+life\s+span)\b",
     "a maternal health or longevity claim"),
    (r"\b(?:health|longevity|lifespan|life\s+expectancy|survival|long-?lived|"
     r"long\s+life|short\s+life)\b[^.]{0,80}?"
     r"\b(?:mother|mother's|maternal)\b", "a maternal health or longevity claim"),
]

_SPIRITUAL_RULES = [
    (r"\bmoksha\b", "Moksha doctrine"),
    (r"\bspiritual\s+liberation\b", "spiritual-liberation doctrine"),
    (r"\bself[-\s]?realisation\b|\bself[-\s]?realization\b", "self-realisation doctrine"),
    (r"\bmaterial(?:ism|istic)?\s+(?:versus|vs\.?|against)\s+spiritual\b",
     "material-versus-spiritual doctrine"),
    (r"\bspiritual\s+(?:versus|vs\.?)\s+material\b", "material-versus-spiritual doctrine"),
]

#: Vehicle tier vocabulary, scoped to the Vehicles section ONLY. "Moderate" in
#: particular is part of a legitimate server category name ("Moderate Functional
#: Base"), so a global ban would reject correct prose.
_VEHICLE_TIER_RULES = [
    (r"\bpremium\b", "a vehicle tier"),
    (r"\bluxur(?:y|ious)\b", "a vehicle tier"),
    (r"\bmoderate\b", "a vehicle tier"),
    (r"\btier\b", "a vehicle tier"),
    (r"\bgrade[sd]?\b", "a vehicle grade"),
    (r"\bupgrade[sd]?\b", "a vehicle upgrade claim"),
]

GLOBAL_RULES = (_COUNT_RULES + _TIMING_RULES + _CERTAINTY_RULES
                + _ACTIVATION_RULES + _MATERNAL_RULES + _SPIRITUAL_RULES)


def _split_strict(text: str) -> List[Dict[str, str]]:
    """Exactly the four headings, once each, in order. No fallback.

    The permissive `Interpretive Explanation` fallback that shipped in D4-008 is
    GONE from this path: a formatting failure is a narrative failure, not
    permission to weaken the contract.
    """
    found = re.findall(r"^###\s*(.+?)\s*$", text, re.M)
    if found != list(SECTION_TITLES):
        raise D4NarrativeError("provider output does not carry exactly the four "
                               "required headings, once each, in order")
    out: List[Dict[str, str]] = []
    positions = [text.index("### " + t) for t in SECTION_TITLES]
    for i, title in enumerate(SECTION_TITLES):
        start = positions[i] + len("### " + title)
        end = positions[i + 1] if i + 1 < len(positions) else len(text)
        body = text[start:end].strip()
        if not body:
            raise D4NarrativeError("a required narrative section is empty")
        out.append({"title": title, "body": body})
    return out


def validate_provider_output(text: Any, brief: Dict[str, Any]) -> List[Dict[str, str]]:
    """Fail-closed structural and doctrine guard over what the provider EMITTED.

    Raises D4NarrativeError on ANY violation. Nothing is scrubbed, rewritten,
    redacted or partially retained: a violating narrative is rejected whole and
    the route publishes its existing sanitized correlated failure.
    """
    if not isinstance(text, str) or not text.strip():
        raise D4NarrativeError("the provider returned no narrative text")

    sections = _split_strict(text)

    for pattern, what in GLOBAL_RULES:
        if re.search(pattern, text, re.I):
            raise D4NarrativeError("provider output carries " + what)

    # Vehicle tiers, scoped to one section. The server's own category name is
    # removed first, so a legitimate quotation of "Moderate Functional Base"
    # cannot trip a rule aimed at vehicle grading.
    category = str((brief.get("property") or {}).get("category") or "")
    vehicles = next(s["body"] for s in sections
                    if s["title"] == "Vehicles & Material Comforts")
    if category:
        vehicles = vehicles.replace(category, "")
    for pattern, what in _VEHICLE_TIER_RULES:
        if re.search(pattern, vehicles, re.I):
            raise D4NarrativeError("the vehicles section carries " + what)

    # A state code other than the one the server selected is an override attempt.
    selected = str((brief.get("property") or {}).get("selected_state") or "")
    for code in re.findall(r"\bP[1-5]\b", text):
        if code != selected:
            raise D4NarrativeError("provider output names a state other than the "
                                   "server-selected one")
    return sections
