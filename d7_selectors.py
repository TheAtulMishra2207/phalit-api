"""D7-002 · the three selector families, exactly as the addendum locks them.

§B  Archetype selection      — State_Evidence = Σ abs(Effective_Weight)
§C  Quick Snapshot           — Founder waterfalls, NOT archetype scoring
§D  Primary Parental Strength — SIGNED vectors, NOT absolute evidence

The three use three different arithmetic rules and the addendum is explicit that
they must not be collapsed into one. They are kept in one module so that fact is
visible, and separated into three functions so it cannot be lost.
"""

from typing import Any, Dict, List, Optional, Tuple

from d7_rules import (
    ARCHETYPES,
    ARCHETYPE_TITLES,
    NO_DOMINANT,
    STATE_LETTERS,
    STATE_NAMES,
    UNRESOLVED,
)

# Selection order when State_Evidence and |EW| both tie. Addendum §B.
STATE_PRECEDENCE = ("E", "D", "C", "B", "A")


# ─── §B · archetype selection ────────────────────────────────────────────────

def select_archetype(archetype: str, manifest: Dict[str, Any]) -> Dict[str, Any]:
    """Select one state for one archetype.

    Eligibility is FIRING, not arithmetic. A state with no fired rule never
    enters the candidate set, so it cannot be beaten by, or beat, a state
    scored at zero. A lone state whose only fired rule is -2.0 wins outright.

    Ladder: highest State_Evidence → highest individual |EW| → E > D > C > B > A.
    """
    fired = [r for r in manifest["fired"] if r["archetype"] == archetype]

    by_state: Dict[str, List[Dict[str, Any]]] = {}
    for r in fired:
        by_state.setdefault(r["state"], []).append(r)

    if not by_state:
        return {
            "archetype": archetype,
            "title": ARCHETYPE_TITLES[archetype],
            "state": None,
            "state_name": NO_DOMINANT,
            "state_evidence": 0.0,
            "candidates": [],
            "fired_rule_ids": [],
            "selection_basis": "no_fired_rules",
        }

    candidates = []
    for letter, rules in by_state.items():
        evidence = sum(abs(r["effective_weight"]) for r in rules)
        peak = max(abs(r["effective_weight"]) for r in rules)
        candidates.append({
            "state": letter,
            "state_name": STATE_NAMES[archetype][letter],
            "state_evidence": round(evidence, 6),
            "peak_abs_weight": round(peak, 6),
            "signed_total": round(sum(r["effective_weight"] for r in rules), 6),
            "fired_rule_ids": [r["rule_id"] for r in rules],
        })

    # Ladder. Precedence index is negated so a LOWER index (E first) sorts higher.
    def _key(c: Dict[str, Any]) -> Tuple[float, float, int]:
        return (c["state_evidence"],
                c["peak_abs_weight"],
                -STATE_PRECEDENCE.index(c["state"]))

    ordered = sorted(candidates, key=_key, reverse=True)
    win = ordered[0]

    tied_evidence = [c for c in ordered if c["state_evidence"] == win["state_evidence"]]
    if len(tied_evidence) == 1:
        basis = "state_evidence"
    elif len({c["peak_abs_weight"] for c in tied_evidence}) > 1:
        basis = "peak_abs_weight"
    else:
        basis = "state_precedence"

    return {
        "archetype": archetype,
        "title": ARCHETYPE_TITLES[archetype],
        "state": win["state"],
        "state_name": win["state_name"],
        "state_evidence": win["state_evidence"],
        "candidates": ordered,
        "fired_rule_ids": win["fired_rule_ids"],
        "selection_basis": basis,
    }


def select_all_archetypes(manifest: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [select_archetype(a, manifest) for a in ARCHETYPES]


# ─── §C · Quick Snapshot waterfalls ──────────────────────────────────────────
#
# The addendum is explicit that archetype scoring is NOT used here. Each
# dimension is a priority-ordered waterfall: the first condition that holds
# wins, and the LAST label is the terminal fallback reached when every
# higher-priority condition fails.
#
# The ORDERS below are the Founder's, verbatim. The CONDITIONS that fire each
# non-terminal rung were not supplied and are held as unresolved slots. Until
# they are supplied every chart falls through to the terminal label, which is
# recorded honestly in `resolved: False` rather than presented as a finding.

CONCEPTION_VITALITY_WATERFALL = (
    "Special Attention Needed",
    "Requires Patience",
    "Balanced",
    "High Vitality",
)

LINEAGE_SCOPE_WATERFALL = (
    "Sequence Interrupted",
    "Unconventional Path",
    "Delayed Bloom",
    "Expansive Lineage",
    "Compact & Focused",
)

PARENTAL_STRENGTH_LABELS = {
    5: "5th House: Direct Nurturing & Intuition",
    9: "9th House: Wise Guidance & Legacy",
    7: "7th House: Partner Harmony",
}


def _run_waterfall(order: Tuple[str, ...],
                   conditions: Dict[str, Optional[bool]]) -> Dict[str, Any]:
    """Walk the rungs in priority order. Terminal label is the fallback.

    A rung whose condition is None is UNRESOLVED. Walking past it would assert
    that it did not hold, which is not known, so the walk STOPS there and the
    dimension is reported unresolved rather than falling through to a label the
    chart may not be entitled to.
    """
    trace = []
    for label in order[:-1]:
        cond = conditions.get(label)
        trace.append({"label": label, "condition": cond})
        if cond is None:
            return {
                "value": None,
                "status": UNRESOLVED,
                "blocked_at": label,
                "resolved": False,
                "trace": trace,
            }
        if cond:
            return {
                "value": label,
                "status": "SELECTED",
                "resolved": True,
                "trace": trace,
            }
    # CORR-02 · spec H. Every rung including the last is a CONDITION. If none
    # fires the answer is a neutral no-dominant state, never an invented
    # positive. The old terminal-fallback published "High Vitality" by default.
    label = order[-1]
    cond = conditions.get(label)
    trace.append({"label": label, "condition": cond})
    if cond is None:
        return {"value": None, "status": UNRESOLVED, "blocked_at": label,
                "resolved": False, "trace": trace}
    if cond:
        return {"value": label, "status": "SELECTED", "resolved": True,
                "trace": trace}
    return {
        "value": None,
        "status": "NO_DOMINANT",
        "resolved": False,
        "selection_basis": "no_rung_fired",
        "trace": trace,
    }


def select_conception_vitality(conditions: Dict[str, Optional[bool]]) -> Dict[str, Any]:
    out = _run_waterfall(CONCEPTION_VITALITY_WATERFALL, conditions)
    out["dimension"] = "conception_vitality"
    return out


def select_lineage_scope(conditions: Dict[str, Optional[bool]]) -> Dict[str, Any]:
    out = _run_waterfall(LINEAGE_SCOPE_WATERFALL, conditions)
    out["dimension"] = "lineage_scope"
    return out


# ─── FD-2A · spec H rung conditions, exactly as written ─────────────────────

def conception_vitality_conditions(fd1b: Dict[str, Any]) -> Dict[str, Optional[bool]]:
    """Spec H, evaluated in the stated order.

    1 Special Attention Needed · sphuta afflicted AND natural malefic in H6/H12
    2 Requires Patience       · non-optimal polarity OR Saturn/Sun on 5H or 5L
    3 Balanced                · (non-optimal AND Jupiter/Venus aspect on 5H)
                                 OR (optimal AND mild malefic aspect)
    4 High Vitality           · optimal AND no malefic aspect on lagna or 5H
    """
    optimal = fd1b["sphuta_optimal_polarity"]
    return {
        "Special Attention Needed": bool(
            fd1b["afflicted_sphuta"] and fd1b["malefic_in_h6_or_h12"]),
        "Requires Patience": bool(
            (not optimal)
            or fd1b["saturn_aspects_5h_or_5l"]
            or fd1b["sun_aspects_5h_or_5l"]),
        "Balanced": bool(
            ((not optimal) and fd1b["jupiter_venus_benefic_aspect_5h"])
            or (optimal and fd1b["mild_malefic_aspect_5h"])),
        # CORR-05 · ASPECT only. `malefic_on_lagna_or_5h` also counts occupancy,
        # so a malefic merely sitting in the lagna blocked High Vitality against
        # the Founder wording, which says "no malefic ASPECT".
        "High Vitality": bool(
            optimal and not fd1b["malefic_aspect_on_lagna_or_5h"]),
    }


def lineage_scope_conditions(fd1b: Dict[str, Any]) -> Dict[str, Optional[bool]]:
    """Spec H, evaluated in the stated order.

    1 Sequence Interrupted · Rahu/Ketu/Saturn in slot 1 or 2 AND no secondary line
    2 Unconventional Path  · node occupies 5H OR valid influence on PK / 5L
    3 Delayed Bloom        · Saturn validly aspects lagna, 5H or 5L
    4 Expansive Lineage    · >= 3 unbroken slots AND Jupiter unafflicted
    5 Compact & Focused    · 1-2 clean slots AND no severe affliction
    """
    return {
        "Sequence Interrupted": bool(
            fd1b["slot1_or_2_blocked"] and not fd1b["secondary_line_activation"]),
        # CORR-04 · occupancy of the D7 5th ONLY. The Founder's "node aspects
        # PK/5L" branch is non-firing under shared doctrine, and conjunction is
        # not a replacement for a forbidden aspect.
        "Unconventional Path": bool(fd1b["node_occupies_5h"]),
        "Delayed Bloom": bool(
            fd1b["saturn_aspects_lagna_or_5h"] or fd1b["saturn_aspects_5h_or_5l"]),
        "Expansive Lineage": bool(
            fd1b["unbroken_slots"] >= 3 and not fd1b["afflicted_jupiter"]),
        "Compact & Focused": bool(
            1 <= fd1b["clean_slots"] <= 2 and not fd1b["heavy_affliction_5h"]),
    }


# ─── §D · Primary Parental Strength ──────────────────────────────────────────

PARENTAL_TIE_ORDER = (5, 9, 7)


def select_parental_strength(vectors: Dict[int, List[Dict[str, Any]]]) -> Dict[str, Any]:
    """SIGNED totals per house vector. Absolute evidence is NOT used here.

    `vectors` maps house → list of fired rule records contributing to it.
    Winner is the numerically largest signed total; ties break on the largest
    individual fired SIGNED value, then 5H > 9H > 7H.
    """
    # CORR-03 · F. With no fired rule anywhere across the three buckets there is
    # no evidence to rank. Falling through to the tie ladder published 5H purely
    # because precedence exists, which reads as a chart verdict and is not one.
    total_fired = sum(len(vectors.get(h, [])) for h in PARENTAL_TIE_ORDER)
    if total_fired == 0:
        return {
            "dimension": "primary_parental_strength",
            "house": None,
            "value": None,
            "status": "NO_DOMINANT",
            "signed_total": 0.0,
            "vectors": [{"house": h, "label": PARENTAL_STRENGTH_LABELS[h],
                         "signed_total": 0.0, "peak_signed_weight": 0.0,
                         "fired_rule_ids": []} for h in PARENTAL_TIE_ORDER],
            "selection_basis": "no_fired_rules",
            "resolved": False,
        }

    scored = []
    for house in PARENTAL_TIE_ORDER:
        rules = vectors.get(house, [])
        total = sum(r["effective_weight"] for r in rules)
        peak = max((r["effective_weight"] for r in rules), default=0.0)
        scored.append({
            "house": house,
            "label": PARENTAL_STRENGTH_LABELS[house],
            "signed_total": round(total, 6),
            "peak_signed_weight": round(peak, 6),
            "fired_rule_ids": [r["rule_id"] for r in rules],
        })

    def _key(c: Dict[str, Any]) -> Tuple[float, float, int]:
        return (c["signed_total"],
                c["peak_signed_weight"],
                -PARENTAL_TIE_ORDER.index(c["house"]))

    ordered = sorted(scored, key=_key, reverse=True)
    win = ordered[0]

    tied_total = [c for c in ordered if c["signed_total"] == win["signed_total"]]
    if len(tied_total) == 1:
        basis = "signed_total"
    elif len({c["peak_signed_weight"] for c in tied_total}) > 1:
        basis = "peak_signed_weight"
    else:
        basis = "house_precedence"

    return {
        "dimension": "primary_parental_strength",
        "house": win["house"],
        "value": win["label"],
        "signed_total": win["signed_total"],
        "vectors": ordered,
        "selection_basis": basis,
        "resolved": True,
    }


def build_parental_vectors(manifest: Dict[str, Any],
                           mapping: Dict[str, List[int]]) -> Dict[int, List[Dict[str, Any]]]:
    """Group fired clauses into the 5H / 9H / 7H Founder vectors.

    CORR-05 · `mapping` is rule_id → LIST of vectors, derived mechanically from
    each clause's declared Founder anchors. A clause may contribute to several
    vectors, or to none. The previous single-house mapping was hand-assigned and
    placed clauses in buckets their conditions never named.
    """
    vectors: Dict[int, List[Dict[str, Any]]] = {5: [], 9: [], 7: []}
    for r in manifest["fired"]:
        for house in mapping.get(r["rule_id"], ()):
            if house in vectors:
                vectors[house].append(r)
    return vectors
