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
                          dasha_context: Dict[str, Any],
                          semantic_envelope: Optional[Dict[str, Any]] = None,
                          comfort_profile: Optional[Dict[str, Any]] = None,
                          architectural_signatures: Optional[Dict[str, Any]] = None
                          ) -> Dict[str, Any]:
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
            # OBSOLETE UNDER THE FOUR-STATE LOCK, REMOVED. These two facts were
            # written when no comfort taxonomy existed, and they told the model
            # that no tier had been defined. The classifier now resolves EVERY
            # valid chart to exactly one of the four tiers, so carrying them
            # alongside `comfort_profile` put two contradictory instructions in
            # one prompt. The `comfort_profile` block is the SOLE tier authority.
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
        # COURSE CORRECTION · the provider synthesises LAYERS, not a single
        # verdict. Precedence chose which layer leads; it did not delete the
        # others, and the brief carries every one of them.
        "layers": {
            "primary": (semantic_envelope or {}).get("primary_layer"),
            "secondary": (semantic_envelope or {}).get("secondary_layers", []),
            "active_layer_count": (semantic_envelope or {}).get("active_layer_count"),
            "multi_asset_language_permitted":
                bool((semantic_envelope or {}).get("multi_asset_language_permitted")),
            "coverage_baseline": bool((semantic_envelope or {}).get("coverage_baseline")),
        },
        "comfort_profile": {
            "profile": (comfort_profile or {}).get("profile"),
            "headline": (comfort_profile or {}).get("headline"),
            "description": (comfort_profile or {}).get("description"),
            "approved_vocabulary": list((comfort_profile or {}).get("approved_vocabulary") or []),
            "resolution": (comfort_profile or {}).get("resolution"),
            "maintenance_attention": (comfort_profile or {}).get("maintenance_attention"),
            "policy": ("explain ONLY the supplied profile; where none is supplied no "
                       "tier exists and none may be implied"),
        },
        "architectural_vocabulary": sorted({w for x in
                                            (architectural_signatures or {}).get("signatures", [])
                                            for w in x.get("vocabulary", [])}),
        "architectural_signatures": {
            "signatures": [{"graha": x["graha"],
                            "vocabulary": list(x.get("vocabulary", []))}
                           for x in (architectural_signatures or {}).get("signatures", [])],
            "caveat": (architectural_signatures or {}).get("caveat", ""),
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
The platform's deterministic engine has already decided what this chart shows.
Your job is to EXPLAIN the supplied result in warm, readable prose for the person
whose chart it is. You are not performing astrology and you are not being asked to.

OPEN WITH THE ANSWER. The first sentence of "Property Capacity & Stability" must
answer the reader's property question directly, in plain terms. Do not open with
evidence, mechanics, or a description of what the chart "shows". When expansion
capacity is among the supplied layers, lead with that capacity and then explain
the primary operational reality and the other active dimensions around it. When
it is not supplied, do not imply strong or multi-property capacity in any wording.

This should read like a premium, authoritative life reading — strategic prose a
person would pay for. It must not read like a server response, an engineering
audit, a compliance report or astrology-debug output.

WRITE FOR A READER, NOT FOR AN AUDIT LOG. Do not narrate the calculation, list
evidence, or use the platform's internal vocabulary - no bare house numbers as
labels, no dignity codes, no contact counts, and no internal state codes. Turn
the supplied facts into plain, grounded sentences a thoughtful person would want
to read about their own life.

SYNTHESISE THE LAYERS. When more than one layer is supplied they are CONCURRENT
aspects of one picture, not competing verdicts and not ranked alternatives. The
primary reality leads; the others are woven in as real, simultaneously active
features. Never present a secondary layer as weaker, hypothetical, or as
something that might apply instead.

You may NOT:
1. choose a different result, or suggest another might apply;
2. rank, compare or weigh the layers against each other;
3. create, name or imply a yoga or combination that is not in the supplied data;
4. use any internal state code, such as P1 through P5;
5. state or estimate a NUMBER of properties, now or over a lifetime;
6. claim multi-property or portfolio capacity UNLESS the supplied layers include
   it - if expansion capacity is not supplied, do not imply it in any wording;
7. give a purchase date, timeframe, window or season;
8. say an acquisition is guaranteed, certain, assured or inevitable;
9. say litigation, dispute or loss is certain or will occur;
10. invent, rename or re-rank a comfort tier. If a comfort profile IS supplied you
    may state and explain THAT profile and no other; if none is supplied, describe
    the placement without grading it and never use premium, executive, luxury or
    equivalent language of your own;
11. treat a Dasha concurrence as an activation, trigger, fruition, manifestation
    or imminent event;
12. make any claim about the mother's health, longevity, survival or character;
13. introduce Moksha, spiritual liberation, or a material-versus-spiritual
    orientation of the soul.

ARCHITECTURAL SIGNATURES, where supplied, use only the supplied vocabulary and are
contextual character only. Write
them as the flavour the chart carries, never as a prediction that a specific
future property will have those features.

DASHA BOUNDARY. A concurrence means ONLY that the current Dasha lord is one of
the grahas structurally participating in the result. It asserts no event, no
timing and no outcome. If a status is "unknown", say the current timing
information is unavailable. If the result is a coverage baseline, say the reading
is a general one rather than a specific matched pattern.

D1 is SUPPORTING CONTEXT ONLY. It may add nuance to sections 1 and 2. It may
never contradict, override or replace the D4 result.

FORMAT IS NOT NEGOTIABLE. Emit the four headings EXACTLY as written below, each
on its own line, each beginning with three hash marks and one space. Do not use
two hash marks, do not add a colon, do not add any other heading, and do not
write a preamble before the first heading or a note after the last section. A
formatting deviation makes the whole reading unusable.

NEVER QUANTIFY HOLDINGS. Do not attach a number to properties, homes, houses,
plots or real estate — not "four properties", not "three homes", and not "one
home". Describe the pattern without counting it.

DO NOT RAISE GUARANTEES OR ACTIVATION AT ALL, in any direction. Do not promise
them and do not deny them: leave the words guarantee, assured, inevitable,
activate, trigger, fruition and imminent out of the reading entirely.

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
    # P-CODE LEAK FOUND AND CLOSED: this line used to append
    # "Matched combinations: P2, P4" straight into the prompt, which put internal
    # codes in front of the provider — the exact thing the correction forbids.
    # The layers above already carry every matched state in semantic form, so the
    # code listing is simply gone rather than reworded.
    fallback = ("This is a COVERAGE BASELINE: no specific pattern matched, so describe "
                "a general reading and do not present it as a matched pattern."
                if p["is_coverage_fallback"] else
                "All layers listed above are active simultaneously.")
    lay = brief.get("layers") or {}
    prim = lay.get("primary") or {}
    sec = lay.get("secondary") or []
    comfort = brief.get("comfort_profile") or {}
    arch = brief.get("architectural_signatures") or {}

    layer_lines = ["PRIMARY OPERATIONAL REALITY (already determined; explain it, "
                   "do not re-decide it):",
                   "  " + str(prim.get("theme", "")),
                   "  layer: " + str(prim.get("layer", ""))]
    if sec:
        layer_lines.append("")
        layer_lines.append("ALSO ACTIVE — these are CONCURRENT layers of the same "
                           "picture, not alternatives and not lesser results. "
                           "Weave them together with the primary reality:")
        for x in sec:
            layer_lines.append("  " + str(x.get("role", "")) + " — " + str(x.get("theme", "")))
    else:
        layer_lines.append("")
        layer_lines.append("No additional layers are active; describe the primary "
                           "reality alone without implying others were considered.")

    sig_lines = []
    if arch.get("signatures"):
        sig_lines.append("ARCHITECTURAL AND ENVIRONMENTAL SIGNATURES "
                         "(contextual character, never a description of a specific "
                         "future property):")
        for x in arch["signatures"]:
            sig_lines.append("  " + str(x["graha"]) + ": "
                             + ", ".join(x.get("vocabulary", [])))
        sig_lines.append("  " + str(arch.get("caveat", "")))
        sig_lines.append("")

    return "\n".join(layer_lines + ["",
        "  " + fallback,
        "",] + sig_lines + [
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
        "  comfort tier determined by the platform: " + str(comfort.get("profile")),
        "  its meaning: " + str(comfort.get("headline")) + " — "
        + str(comfort.get("description")),
        "  you may use ONLY this vocabulary for grading: "
        + (", ".join(comfort.get("approved_vocabulary") or []) or "none"),
        "  you may not choose, upgrade or downgrade this tier.",
        "  maintenance attention: " + ("yes — disciplined upkeep and operational "
                                       "attention are indicated"
                                       if comfort.get("maintenance_attention")
                                       else "not indicated"),
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

#: EXACT quantities. Vague quantifiers were removed from this set by the course
#: correction — they are qualitative, not counts, and are governed by the
#: expansion-layer gate instead of by an outright ban.
_EXACT_WORD_NUMBERS = (r"one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve")
_WORD_NUMBERS = _EXACT_WORD_NUMBERS + r"|a couple of|several|multiple|numerous"
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
    # EXACT quantities only. `_WORD_NUMBERS` no longer carries the vague
    # quantifiers — "several"/"multiple"/"a couple of" are qualitative, and the
    # expansion-layer gate below decides whether they are allowed at all.
    (r"\b(?:\d+|" + _EXACT_WORD_NUMBERS + r")\s+" + _ADJ_GAP + r"(?:" + _ASSET_NOUNS + r")\b",
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
    # The missive names "executive" explicitly as an invented luxury claim, and
    # C2's locked frame is the only place it is permitted.
    (r"\bexecutive(?:-level)?\b", "a vehicle tier"),
    (r"\bhigh[-\s]status\b", "a vehicle tier"),
    (r"\bhigh[-\s]standard\b", "a vehicle tier"),
    (r"\bluxur(?:y|ious)\b", "a vehicle tier"),
    (r"\bmoderate\b", "a vehicle tier"),
    (r"\btier\b", "a vehicle tier"),
    (r"\bgrade[sd]?\b", "a vehicle grade"),
    (r"\bupgrade[sd]?\b", "a vehicle upgrade claim"),
]

#: COURSE CORRECTION · qualitative multi-asset language is PERMITTED, but only
#: when the deterministic expansion layer actually matched. This is not a
#: loosening of the count rule: an EXACT quantity is still rejected in every
#: case. What changes is that "a broader real-estate portfolio" stops being
#: treated as a count — and, crucially, it is rejected when the expansion layer
#: is ABSENT, so the provider cannot invent capacity the engine did not find.
_QUALITATIVE_MULTI_ASSET = [
    r"\bmulti[-\s]?asset\b",
    r"\bbroader\s+real[-\s]?estate\s+portfolio\b",
    r"\breal[-\s]?estate\s+portfolio\b",
    r"\bmultiple[-\s]?asset\s+orientation\b",
    r"\bproperty\s+portfolio\b",
    r"\bmultiple\s+holdings?\b",
    r"\bmultiple\s+propert(?:y|ies)\b",
    r"\bportfolio\s+of\s+(?:propert(?:y|ies)|real[-\s]?estate|holdings?)\b",
    # Vague quantifiers over asset nouns. These left the EXACT-count rule when
    # the correction landed, so they are governed here instead — permitted when
    # the expansion layer matched, rejected when it did not.
    r"\b(?:several|multiple|numerous|a\s+couple\s+of|many)\s+" + _ADJ_GAP
    + r"(?:" + _ASSET_NOUNS + r")\b",
]

#: The three Founder-approved comfort tiers. Only the SERVER-SELECTED one may
#: appear in prose; the other two, and any tier at all when none was selected,
#: are rejected.
APPROVED_COMFORT_TIERS = ("High Comfort Tier", "Maintenance-Heavy Comfort Tier",
                          "Constrained Comfort Tier", "Functional Comfort Tier")

#: P-codes are INTERNAL. They may never appear in user-facing prose, whichever
#: code it is — including the selected one.
_P_CODE_RULE = (r"\bP[1-5]\b", "an internal P-code")

#: EVERY FAMILY IS ABSOLUTE. Certainty and activation were briefly
#: negation-aware; PROD-01-CORR-04 returned them to the same footing as counts,
#: timing, maternal and spiritual rules.

def _rule_fires(text: str, pattern: str, what: str) -> bool:
    """A prohibited pattern occurring anywhere fires its rule. No exceptions.

    PROD-01-CORR-04 · THE SEMANTIC NEGATION MACHINERY IS GONE. Four rounds of it
    — character proximity, clause boundary plus word gap, a target-specific
    allowlist, then an enumerated filler — each fixed its assigned cases and each
    left a new construction that meant the opposite of what it was read as:
    "not difficult AND guaranteed", "no doubt … guaranteed", "nothing BUT
    acquisition is guaranteed", "nothing is guaranteed EXCEPT acquisition".

    The contract is simplified rather than patched again. The prompt already
    tells the provider to leave this vocabulary out ENTIRELY, in either
    direction, so the guard has no need to tell an assertion from a denial, a
    double negative, an exception or a qualified denial. If the vocabulary
    appears at all, the narrative is rejected.
    """
    return re.search(pattern, text, re.I) is not None


GLOBAL_RULES = (_COUNT_RULES + _TIMING_RULES + _CERTAINTY_RULES
                + _ACTIVATION_RULES + _MATERNAL_RULES + _SPIRITUAL_RULES
                + [_P_CODE_RULE])


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
        if _rule_fires(text, pattern, what):
            raise D4NarrativeError("provider output carries " + what)

    # Vehicle tiers, scoped to one section. The server's own category name is
    # removed first, so a legitimate quotation of "Moderate Functional Base"
    # cannot trip a rule aimed at vehicle grading.
    category = str((brief.get("property") or {}).get("category") or "")
    vehicles = next(s["body"] for s in sections
                    if s["title"] == "Vehicles & Material Comforts")
    if category:
        # WORD-BOUNDARY STRIP, not a raw replace. `vehicles.replace(category, "")`
        # deletes the category's characters ANYWHERE they occur, so a short
        # category silently mangles the section it is meant to protect — a
        # one-letter category would strip that letter from every word. Found by a
        # probe, not in production, because the real categories are long phrases.
        vehicles = re.sub(r"\b" + re.escape(category) + r"\b", "", vehicles, flags=re.I)
    # REVISED BY THE CONSOLIDATED MISSIVE: the blanket tier ban is replaced by a
    # CONDITIONAL one. The provider may reproduce the SERVER-SELECTED tier and
    # nothing else — so the selected tier's own words are removed before the scan,
    # and every other grading word still rejects. An unmatched (pending) chart has
    # no tier, so the blanket ban still applies to it in full.
    comfort = brief.get("comfort_profile") or {}
    supplied_tier = str(comfort.get("profile") or "")
    approved_vocab = list(comfort.get("approved_vocabulary") or [])
    vehicles_scanned = vehicles
    if supplied_tier:
        # ONLY THE FULL TIER NAME IS STRIPPED. An earlier version also stripped
        # each word of the name, which deleted "Tier" from the whole section and
        # let "a higher tier of vehicle" through — the per-word loop was a
        # leftover from when the tier names were free phrases, and it defeated
        # the very rule it sat beside.
        vehicles_scanned = re.sub(re.escape(supplied_tier), "", vehicles_scanned, flags=re.I)
    # THE SELECTED TIER'S OWN APPROVED VOCABULARY IS OPENED UP, and only it. C2
    # may say "executive" and "luxury" because its locked frame does; C4 may not,
    # which is exactly what stops a functional baseline being written up as a
    # luxury reading. Everything outside the selected tier's list still rejects.
    for phrase in approved_vocab:
        vehicles_scanned = re.sub(r"\b" + re.escape(phrase) + r"\b", "",
                                  vehicles_scanned, flags=re.I)
    # The approved tier NAMES are not made of banned words, so the vocabulary
    # rules alone would let a provider name a tier it was never given — or name
    # the WRONG one. Only the supplied tier may appear.
    for approved in APPROVED_COMFORT_TIERS:
        if approved == supplied_tier:
            continue
        if re.search(re.escape(approved), vehicles, re.I):
            raise D4NarrativeError("the vehicles section names a comfort tier the "
                                   "engine did not select")
    for pattern, what in _VEHICLE_TIER_RULES:
        if re.search(pattern, vehicles_scanned, re.I):
            raise D4NarrativeError("the vehicles section carries " + what)

    # COURSE CORRECTION · qualitative multi-asset language is gated on the
    # DETERMINISTIC expansion layer. Permitted when the engine matched it,
    # rejected when it did not — the provider cannot invent capacity.
    layers = brief.get("layers") or {}
    if not layers.get("multi_asset_language_permitted"):
        for pattern in _QUALITATIVE_MULTI_ASSET:
            if re.search(pattern, text, re.I):
                raise D4NarrativeError("provider output claims multi-asset capacity "
                                       "that the engine did not match")
    return sections
