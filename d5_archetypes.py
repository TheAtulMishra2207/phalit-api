"""
d5_archetypes.py — D5-009-CORR-03 · THE THREE FOUNDER STATE SELECTORS.

PURE SELECTION FROM CERTIFIED SCORING. This module identifies which mapped
rules fired, sums Effective Weights the scoring engine already computed, and
applies the Founder precedence. It calculates no placement, aspect, dignity,
Tattva, Chara Karaka, combustion, Graha Yuddha — and no Effective Weight of its
own.

ELIGIBILITY IS FIRING, NOT ARITHMETIC. A state is eligible when at least one of
its mapped rules FIRED, whatever the sign or size of the total. A state scoring
-1.50 as the only eligible one WINS: it is not compared against four inactive
states scored as zero, because those states are not in the running at all. That
distinction is the difference between "this signature is present and difficult"
and "nothing was found".

FALLBACK IS ZERO SIGNAL, NOT ZERO SCORE. `No Dominant Signature` is returned
only when NO mapped rule fired. A subsystem whose fired rules cancel to exactly
zero produced a real measurement and keeps its state.
"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Tuple

FIRED = "FIRED"

NO_DOMINANT = "No Dominant Signature"

#: Restrained neutral fallback copy. It means only that this subsystem produced
#: no dominant mapped signal — never bad, blocked, absent or denied.
NO_DOMINANT_BODY = ("No single dominant signature emerges in this area of the "
                    "Panchamsha. This is a neutral reading: the division simply "
                    "does not emphasise one pattern here over another.")


# ─────────────────────────────────────────────────────────────────────────────
# FOUNDER STATE COPY · transcribed verbatim from the report template
# ─────────────────────────────────────────────────────────────────────────────

PURVA_PUNYA = ("Purva Punya & Divine Grace", {
    "A": ("Divine Shield",
          "Massive past credit; unearned breakthroughs and spontaneous "
          "protection in crises."),
    "B": ("Unlocked Genius",
          "Sharp intuition and natural talent from early childhood; rapid "
          "manifestation of intent."),
    "C": ("Earned Progression",
          "Balanced past karma; rewards align strictly with personal effort "
          "and discipline."),
    "D": ("Dormant Vault",
          "High talent present, but locked behind an occult, emotional, or "
          "spiritual threshold."),
    "E": ("Karmic Rina",
          "Past spiritual debts block immediate luck; requires selfless "
          "service/tapasya to unlock."),
})

ROMANTIC = ("Romantic Signature & Creative Drive", {
    "A": ("Soulmate Synergy",
          "Deep past-life emotional resonance; whirlwind, highly fulfilling "
          "partnerships."),
    "B": ("Creative Catalyst",
          "Romantic encounters act as the primary spark for artistic, "
          "written, or career genius."),
    "C": ("Unconventional Spark",
          "Boundary-breaking love affairs, sudden infatuations, or "
          "cross-cultural alliances."),
    "D": ("Playful Courtship",
          "Relationships thrive on intellectual banter, courtship, and "
          "dynamic attraction."),
    "E": ("Karmic Friction",
          "Passion exists alongside intense lessons; relationships serve as "
          "tests of emotional maturity."),
})

PROGENY = ("Progeny Dynamics & Legacy", {
    "A": ("High Lineage Blessing",
          "Blessed with virtuous, highly accomplished children who elevate "
          "the family name."),
    "B": ("Intellectual Continuity",
          "Children inherit the native's exact intellectual/creative spark "
          "and expand upon it."),
    "C": ("Deep Soul-Bond",
          "Multi-lifetime friendship with progeny; strong mutual respect and "
          "alignment."),
    "D": ("Delayed Bloom",
          "Childbirth or progeny alignment occurs later in life; yields "
          "serious, old-souled offspring."),
    "E": ("Unconventional Trajectory",
          "Complex progeny dynamics; potential medical/surgical intervention "
          "or non-traditional parenting paths."),
})


# ─────────────────────────────────────────────────────────────────────────────
# FOUNDER RULE CLUSTERS
# ─────────────────────────────────────────────────────────────────────────────

ROMANTIC_RULES: Dict[str, Tuple[str, ...]] = {
    "A": ("D5_JAI_11", "D5_PAR_12"),
    "B": ("D5_JAI_12", "D5_PAR_13"),
    "C": ("D5_PAR_14",),
    "D": ("D5_JAI_10", "D5_JAI_13", "D5_PAR_11"),
    "E": ("D5_AFF_05",),
}

PROGENY_RULES: Dict[str, Tuple[str, ...]] = {
    "A": ("D5_PAR_15", "D5_PAR_16", "D5_JAI_15", "D5_CLA_03"),
    "B": ("D5_JAI_14", "D5_TAJ_08", "D5_TAJ_09", "D5_TAJ_10", "D5_TAJ_11"),
    "C": ("D5_JAI_18",),
    "D": ("D5_CLA_04",),
    "E": ("D5_PAR_17", "D5_PAR_18", "D5_JAI_16", "D5_JAI_17"),
}

#: State C has NO cluster: it is the boundary-selected balanced band.
PURVA_PUNYA_RULES: Dict[str, Tuple[str, ...]] = {
    "A": ("D5_PAR_07", "D5_PAR_09"),
    "B": ("D5_PAR_08", "D5_PAR_10", "D5_JAI_06", "D5_JAI_07", "D5_JAI_08",
          "D5_JAI_09"),
    "C": (),
    "D": ("D5_AFF_02", "D5_CLA_01"),
    "E": ("D5_CLA_02", "D5_AFF_01", "D5_AFF_04"),
}

#: The Purva Punya subsystem universe: every rule in the clusters above. The
#: ticket is explicit that a stale historical membership set must NOT be reused.
PURVA_PUNYA_UNIVERSE: Tuple[str, ...] = tuple(sorted(
    r for rules in PURVA_PUNYA_RULES.values() for r in rules))

#: Risk-first precedence for an exact tie that survives the weight comparison.
ROMANTIC_PRECEDENCE: Tuple[str, ...] = ("E", "C", "D", "B", "A")
PROGENY_PRECEDENCE: Tuple[str, ...] = ("E", "D", "C", "B", "A")


# ─────────────────────────────────────────────────────────────────────────────
# SELECTION
# ─────────────────────────────────────────────────────────────────────────────

def _fired(rules: Mapping[str, Any], rule_ids) -> List[str]:
    return [r for r in rule_ids
            if r in rules and rules[r]["status"] == FIRED]


def _state(archetype, key: Optional[str], **extra) -> Dict[str, Any]:
    """The PUBLIC archetype object. Any `_audit` a caller passes is kept under a
    leading underscore so the report layer can strip it before publication —
    the eligibility record names rule ids and is QA material, not customer copy.
    """
    title, states = archetype
    if key is None:
        out = {"archetype": title, "state": None, "name": NO_DOMINANT,
               "body": NO_DOMINANT_BODY, "has_dominant_signature": False}
    else:
        name, body = states[key]
        out = {"archetype": title, "state": key, "name": name, "body": body,
               "has_dominant_signature": True}
    out.update(extra)
    return out


def _argmax_state(rules: Mapping[str, Any], clusters: Mapping[str, Tuple[str, ...]],
                  precedence: Tuple[str, ...]) -> Tuple[Optional[str], Dict[str, Any]]:
    """The Founder ladder: eligibility, signed total, largest single, precedence.

    Only ELIGIBLE states compete. An inactive state is absent from the contest,
    not present with a score of zero — otherwise a lone negative state could
    never win, and a real difficult signature would be reported as no signature.
    """
    eligible: Dict[str, Dict[str, Any]] = {}
    for key, rule_ids in clusters.items():
        fired = _fired(rules, rule_ids)
        if not fired:
            continue
        weights = [rules[r]["effective_weight"] for r in fired]
        eligible[key] = {"score": sum(weights), "highest": max(weights),
                         "fired": sorted(fired)}
    if not eligible:
        return None, {"eligible": {}}

    leaders = list(eligible)
    best = max(eligible[k]["score"] for k in leaders)
    leaders = [k for k in leaders if eligible[k]["score"] == best]
    if len(leaders) > 1:
        top = max(eligible[k]["highest"] for k in leaders)
        leaders = [k for k in leaders if eligible[k]["highest"] == top]
    if len(leaders) > 1:
        leaders = [min(leaders, key=lambda k: precedence.index(k))]
    return leaders[0], {"eligible": eligible}


def romantic_signature(rules: Mapping[str, Any]) -> Dict[str, Any]:
    key, audit = _argmax_state(rules, ROMANTIC_RULES, ROMANTIC_PRECEDENCE)
    return _state(ROMANTIC, key, _audit=audit)


def progeny_dynamics(rules: Mapping[str, Any]) -> Dict[str, Any]:
    key, audit = _argmax_state(rules, PROGENY_RULES, PROGENY_PRECEDENCE)
    return _state(PROGENY, key, _audit=audit)


def purva_punya(rules: Mapping[str, Any], tri_02_fired: bool) -> Dict[str, Any]:
    """Boundary-selected, with the TRI_02 override ahead of every boundary.

    The override runs FIRST and dominates the number: a chart can score highly
    and still be a Dormant Vault, because the vault is exactly what a high score
    behind a block looks like.
    """
    if tri_02_fired:
        return _state(PURVA_PUNYA, "D", _audit={"override": "triangulation"})

    fired = _fired(rules, PURVA_PUNYA_UNIVERSE)
    score = sum(rules[r]["effective_weight"] for r in fired)

    if score >= 2.5:
        # The two High Credit flavours. Exact ties go to A.
        sum_a = sum(rules[r]["effective_weight"]
                    for r in _fired(rules, PURVA_PUNYA_RULES["A"]))
        sum_b = sum(rules[r]["effective_weight"]
                    for r in _fired(rules, PURVA_PUNYA_RULES["B"]))
        key = "B" if sum_b > sum_a else "A"
        return _state(PURVA_PUNYA, key,
                      _audit={"score": score, "sum_a": sum_a, "sum_b": sum_b})
    if score >= 0.0:
        key = "C"
    elif score >= -1.5:
        key = "E"
    else:
        key = "D"
    return _state(PURVA_PUNYA, key, _audit={"score": score})


def all_archetypes(rules: Mapping[str, Any],
                   tri_02_fired: bool) -> Dict[str, Dict[str, Any]]:
    return {
        "purva_punya": purva_punya(rules, tri_02_fired),
        "romantic_signature": romantic_signature(rules),
        "progeny_dynamics": progeny_dynamics(rules),
    }
