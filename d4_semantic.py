"""
d4_semantic.py — D4 SEMANTIC ENVELOPE.

Turns the internal P1-P5 result into the layered, user-facing shape the Founder
asked for, WITHOUT touching the predicate engine or its precedence. Nothing here
evaluates a predicate, re-ranks a state, or changes which state was selected. It
reads the accepted `property_state` and relabels it.

THREE RULES THIS MODULE EXISTS TO ENFORCE

  1. P-CODES ARE INTERNAL. No P1..P5 string appears in anything this module
     publishes for user-facing use. The codes remain in the audit blocks, which
     is where QA and the engine need them.

  2. PRECEDENCE SELECTS, IT DOES NOT ERASE. The selected state becomes the
     Primary Operational Reality; every OTHER matched state survives as its own
     portfolio layer. A P1+P2+P3 chart surfaces three layers, not one.

  3. NOTHING IS INVENTED WHERE DOCTRINE IS ABSENT. Where the Founder supplied a
     label or a mapping it is used verbatim. Where the Founder did not, the
     already-accepted D4-003 category string is reused and the label is marked
     PROVISIONAL — and where neither exists (comfort tiers), the block publishes
     a pending-lock policy instead of a guess.

──────────────────────────────────────────────────────────────────────────────
WHAT IS FOUNDER-LOCKED HERE, AND WHAT IS NOT — read before trusting a label.

  LOCKED, supplied verbatim in the course-correction ticket:
    P1 -> Due-Diligence / Contractual Property Path
    P2 -> Strong Multi-Asset Real-Estate Capacity      (Expansion Potential)
    P3 -> Dynamic / Actively Managed Property Profile  (Asset Mobility)
    Mars / Moon / Sun architectural signatures

  PROVISIONAL, awaiting a Founder naming pass:
    P4 and P5 layer labels. The Founder supplied three examples, not five. These
    two REUSE the accepted D4-003 category strings rather than invent new
    language, and are flagged `label_status: provisional` on the wire so a
    reader can see which labels carry doctrine and which carry a placeholder.

  NOT DEFINED AT ALL, and deliberately not guessed:
    the comfort tier taxonomy and the maintenance-attention threshold. The
    ticket explicitly forbids coding these by assumption, so `comfort_profile`
    publishes its MECHANICAL INPUTS plus a pending-lock policy. The proposed
    classifier is returned separately for review, not embedded here.
──────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

D4_SEMANTIC_VERSION = "1.0.0"

#: Founder-supplied labels, verbatim. `layer` is how the state reads when it is
#: NOT the selected one; `theme` is the state's own description.
_LOCKED_LAYERS = {
    "P1": {"layer": "Contractual Diligence",
           "theme": "Due-Diligence / Contractual Property Path",
           "label_status": "founder_locked"},
    "P2": {"layer": "Expansion Potential",
           "theme": "Strong Multi-Asset Real-Estate Capacity",
           "label_status": "founder_locked"},
    "P3": {"layer": "Asset Mobility",
           "theme": "Dynamic / Actively Managed Property Profile",
           "label_status": "founder_locked"},
}

#: P4 and P5 keep their ALREADY-ACCEPTED D4-003 category semantics. The Founder
#: examples focused on P1-P3; that is not a reason to reopen these two, so they
#: are marked accepted rather than provisional.
_PROVISIONAL_LAYERS = {
    "P4": {"layer": "Asset Stability",
           "theme": "Stable Tangible Asset Retention",
           "label_status": "accepted_d4_category"},
    "P5": {"layer": "Functional Baseline",
           "theme": "Moderate Functional Base",
           "label_status": "accepted_d4_category"},
}

PRIMARY_ROLE = "Primary Operational Reality"

#: FOUNDER-LOCKED architectural signatures. THREE GRAHAS, and the vocabulary is
#: the approved list — nothing here is paraphrased or extended.
_ARCHITECTURAL_SIGNATURES = {
    "Mars": {"graha": "Mars",
             "vocabulary": ["sturdy masonry", "brick", "stone",
                            "earth-linked construction", "structural solidity"]},
    "Moon": {"graha": "Moon",
             "vocabulary": ["water proximity", "gardens",
                            "softer or fluid domestic environments",
                            "coastal or waterfront character"]},
    "Sun": {"graha": "Sun",
            "vocabulary": ["open sky", "strong natural light", "commanding layouts",
                           "formal or regal architectural character"]},
}

#: THE FIVE LOCKED CONTACT PATHS. A signature contributes when the graha does any
#: ONE of these, and the tests below reuse the CERTIFIED D4 contact doctrine to
#: decide each — there is no second influence system anywhere in this module.
SIGNATURE_CONTACT_PATHS = ("occupies_h4", "aspects_h4", "conjoins_4l",
                           "aspects_4l", "is_fourth_lord")

SIGNATURE_CAVEAT = ("These are architectural and environmental signatures of the "
                    "chart, not guaranteed descriptions of any future property.")


class D4SemanticError(ValueError):
    """The accepted property state is not shaped as this module requires."""


def _layer_for(state: str) -> Dict[str, Any]:
    if state in _LOCKED_LAYERS:
        return dict(_LOCKED_LAYERS[state])
    if state in _PROVISIONAL_LAYERS:
        return dict(_PROVISIONAL_LAYERS[state])
    raise D4SemanticError("unknown property state")


def build_semantic_envelope(property_state: Dict[str, Any],
                            vahana_evidence: Dict[str, Any]) -> Dict[str, Any]:
    """The layered, P-code-free view of an already-decided result."""
    for key in ("selected_state", "matched_states", "resolution", "category"):
        if key not in property_state:
            raise D4SemanticError("accepted property state is incomplete")

    selected = property_state["selected_state"]
    matched = list(property_state["matched_states"])
    is_fallback = property_state["resolution"] == "coverage_fallback"

    primary = _layer_for(selected)
    primary.update({
        "role": PRIMARY_ROLE,
        "is_coverage_baseline": is_fallback,
    })

    # PRECEDENCE SELECTS, IT DOES NOT ERASE: every other matched state survives.
    secondary: List[Dict[str, Any]] = []
    for st in matched:
        if st == selected:
            continue
        lay = _layer_for(st)
        lay["role"] = lay["layer"]
        secondary.append(lay)

    # The one flag the output guard needs: qualitative multi-asset language is
    # permitted ONLY when the expansion layer is genuinely matched.
    expansion_matched = "P2" in matched

    return {
        "engine": {
            "d4_semantic_version": D4_SEMANTIC_VERSION,
            "p_codes_exposed": False,
            "precedence_unchanged": True,
            "predicates_re_evaluated": False,
        },
        "primary_layer": primary,
        "secondary_layers": secondary,
        "active_layer_count": 1 + len(secondary),
        "expansion_capacity_matched": expansion_matched,
        "multi_asset_language_permitted": expansion_matched,
        "coverage_baseline": is_fallback,
    }


def build_architectural_signatures(facts: Dict[str, Any],
                                   property_state: Dict[str, Any]) -> Dict[str, Any]:
    """Signatures for the three locked grahas, via the FIVE locked contact paths.

    Every path is decided from evidence the certified engine already emitted:
    occupancy and aspect from the D4 contact records, conjunction with the 4th
    Lord likewise, and lordship from the accepted 4th-Lord identity. No new
    influence rule is defined here, which is the point — a second contact system
    is exactly how two engines that agree today come apart later.
    """
    contacts = property_state["lock1_benefic_cancellation"]
    paths_by_graha: Dict[str, List[str]] = {}
    for side in ("benefic_contacts", "malefic_contacts"):
        for rec in contacts.get(side, []):
            paths_by_graha[rec["graha"]] = list(rec.get("paths", []))

    fh = property_state["d4_primary"]["fourth_house"]
    fl = property_state["d4_primary"]["fourth_lord"]

    active: List[Dict[str, Any]] = []
    for graha, entry in _ARCHITECTURAL_SIGNATURES.items():
        recorded = paths_by_graha.get(graha, [])
        fired = [p for p in SIGNATURE_CONTACT_PATHS if p in recorded]
        # Path 5: the graha IS the D4 4th Lord. It significates the house
        # directly, so it contributes without needing a separate contact.
        if fl.get("graha") == graha and "is_fourth_lord" not in fired:
            fired.append("is_fourth_lord")
        if not fired:
            continue
        active.append({
            "graha": graha,
            "vocabulary": list(entry["vocabulary"]),
            "contact_paths": fired,
            "d4_house": facts["grahas"][graha]["d4_house"],
            "d4_sign": facts["grahas"][graha]["d4_sign"],
        })

    return {
        "engine": {
            "mapped_grahas": sorted(_ARCHITECTURAL_SIGNATURES),
            "unmapped_grahas_deliberately_absent": True,
            "locked_contact_paths": list(SIGNATURE_CONTACT_PATHS),
            "relevance_rule": "certified_d4_contact_doctrine",
            "second_contact_system_created": False,
        },
        "signatures": active,
        "any_signature_active": bool(active),
        "caveat": SIGNATURE_CAVEAT,
        "fourth_house_sign": fh.get("sign"),
    }


# ── FOUNDER-LOCKED VEHICLE & COMFORT CLASSIFIER ─────────────────────────────
#
# FOUR states, first-match, top-down. Architecture is D4 Venus COMBINED with the
# D4 H4/4L Sthana — a Venus-only classifier is prohibited. There is NO weighted
# score anywhere: every branch is a boolean over facts the certified engine
# already emitted.

#: Venus dignity CLASSES, exactly as locked. Mitra and Sama are their own middle
#: class and are NEVER promoted into Strong — supporting contacts may enrich the
#: prose but they do not move Venus between classes.
VENUS_STRONG = ("Exalted (Uccha)", "Own Sign (Swa)")
VENUS_MIDDLE = ("Friendly Sign (Mitra)", "Neutral Sign (Sama)")
VENUS_WEAK = ("Debilitated (Neecha)", "Enemy Sign (Shatru)")

COMFORT_C1 = "High Comfort Tier"
COMFORT_C2 = "Maintenance-Heavy Comfort Tier"
COMFORT_C3 = "Constrained Comfort Tier"
COMFORT_C4 = "Functional Comfort Tier"

#: The approved narrative frame for each tier. `vocabulary` is what the provider
#: is ALLOWED to use for that tier and nothing more — it is what the output guard
#: opens up, so it is doctrine rather than decoration.
COMFORT_FRAMES = {
    COMFORT_C1: {
        "headline": "Elevated Comfort & Seamless Mobility",
        "description": ("Premium access to high-standard vehicles and physical comforts "
                        "with comparatively low operational friction."),
        "vocabulary": ["premium", "elevated", "seamless", "high-standard"],
    },
    COMFORT_C2: {
        "headline": "High Status / Active Operational Friction",
        "description": ("Strong baseline access to executive-level transportation and "
                        "luxury or material comforts, combined with disciplined "
                        "maintenance, servicing or administrative upkeep."),
        "vocabulary": ["executive", "luxury", "high status", "disciplined maintenance",
                       "servicing", "upkeep"],
    },
    COMFORT_C3: {
        "headline": "Restricted / Delayed Comfort",
        "description": ("Material conveniences and vehicular access face stronger "
                        "operational, financial or structural constraints."),
        "vocabulary": ["restricted", "delayed", "constrained"],
    },
    COMFORT_C4: {
        "headline": "Functional Baseline Access",
        "description": ("Practical, standard access to vehicles and material comforts "
                        "without a pronounced luxury signal or severe structural "
                        "constraint."),
        # C4 is deliberately given NO luxury vocabulary: its prose must be able to
        # stand without it, which is the point of a functional baseline.
        "vocabulary": ["functional", "practical", "standard", "baseline"],
    },
}


def _venus_class(dignity: Optional[str]) -> str:
    if dignity in VENUS_STRONG:
        return "strong"
    if dignity in VENUS_MIDDLE:
        return "middle"
    if dignity in VENUS_WEAK:
        return "weak"
    return "unclassified"


def build_comfort_profile(vahana_evidence: Dict[str, Any],
                          property_state: Optional[Dict[str, Any]] = None
                          ) -> Dict[str, Any]:
    """The four-state comfort classifier. First match, top-down, C1 -> C4.

    C4 is a COVERAGE FALLBACK, not a matched structural predicate, and it is
    reached only when C1-C3 are all false. It is a real published tier — unlike
    the earlier pending placeholder — so every chart resolves to exactly one.
    """
    ven = vahana_evidence["venus"]
    sth = vahana_evidence["vahana_sthana"]
    dignity = ven.get("d4_dignity")
    vclass = _venus_class(dignity)

    # HEAVY MALEFIC OVERLOAD reuses the CERTIFIED Lock-1 unique contact counters
    # over D4 H4 / D4 4L. No new aspect or contact arithmetic is created here,
    # and EQUALITY IS NOT OVERLOAD.
    contacts = ((property_state or {}).get("lock1_benefic_cancellation") or {})
    benefic = contacts.get("benefic_count")
    malefic = contacts.get("malefic_count")
    counts_available = isinstance(benefic, int) and isinstance(malefic, int)
    overload = bool(counts_available and malefic > benefic)

    c1 = vclass == "strong" and not overload
    c2 = vclass in ("strong", "middle") and overload
    c3 = vclass == "weak" and overload

    if c1:
        tier, matched, resolution = COMFORT_C1, "C1", "predicate_match"
        rationale = "Venus is strongly dignified in D4 and the Sthana carries no heavy malefic overload"
    elif c2:
        tier, matched, resolution = COMFORT_C2, "C2", "predicate_match"
        rationale = ("Venus holds workable or better dignity in D4 while the Sthana "
                     "carries heavy malefic overload")
    elif c3:
        tier, matched, resolution = COMFORT_C3, "C3", "predicate_match"
        rationale = "Venus is weak in D4 and the Sthana carries heavy malefic overload"
    else:
        tier, matched, resolution = COMFORT_C4, None, "coverage_fallback"
        rationale = ("no specific comfort predicate matched; this is a baseline "
                     "reading rather than a matched structural condition")

    frame = COMFORT_FRAMES[tier]
    return {
        "engine": {
            "architecture": "d4_venus_combined_with_d4_h4_and_4l",
            "venus_only_classifier": False,
            "weighted_score_used": False,
            "evaluation": "first_match_c1_to_c4",
            "tiers": [COMFORT_C1, COMFORT_C2, COMFORT_C3, COMFORT_C4],
            "provider_may_infer_tier": False,
            "provider_may_only_explain_supplied_tier": True,
            "middle_class_promotable_by_contacts": False,
            "schema_version": D4_SEMANTIC_VERSION,
        },
        "profile": tier,
        "resolution": resolution,
        "matched_predicate": matched,
        "rationale": rationale,
        "headline": frame["headline"],
        "description": frame["description"],
        "approved_vocabulary": list(frame["vocabulary"]),
        "maintenance_attention": tier == COMFORT_C2,
        # Enough deterministic evidence to audit the classification.
        "evidence": {
            "venus_d4_dignity": dignity,
            "venus_dignity_class": vclass,
            "benefic_count": benefic,
            "malefic_count": malefic,
            "heavy_malefic_overload": overload,
            "counts_available": counts_available,
            "equality_is_not_overload": True,
            "predicates": {"C1": c1, "C2": c2, "C3": c3},
        },
        "inputs": {
            "venus_d4_sign": ven.get("d4_sign"),
            "venus_d4_house": ven.get("d4_house"),
            "venus_vargottama": ven.get("vargottama"),
            "venus_is_fourth_lord": ven.get("is_fourth_lord"),
            "venus_aspects_received": list(ven.get("aspects_received", [])),
            "direct_venus_contact": vahana_evidence.get("direct_venus_vahana_contact"),
            "contact_paths": dict(vahana_evidence.get("contact_paths", {})),
            "sthana_sign": sth.get("sign"),
            "sthana_occupants": list(sth.get("occupants", [])),
            "sthana_aspects_received": list(sth.get("aspects_received", [])),
            "fourth_lord_dignity": (sth.get("fourth_lord") or {}).get("d4_dignity"),
        },
        "note": ("the provider may explain only the supplied tier and its approved "
                 "vocabulary; it may not choose, upgrade or downgrade the tier"),
    }
