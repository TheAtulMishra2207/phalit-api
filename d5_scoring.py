"""
d5_scoring.py — D5-007 · THE DETERMINISTIC SCORING LAYER.

Consumes certified outcomes and produces Effective Weights, a Final Score, a
score band, Core Authority buckets, Purva Punya and the Primary Power Vector.

WHAT THIS DOES NOT DO. No narrative, no prose, no headline, no state labels, no
provider call, no route, no astrological fact. Nothing here recomputes a chart,
a Tithi, a Dasha, a transit or a TRI predicate — every input arrives already
certified, and the module consumes it.

IT FAILS CLOSED. `assess_score_readiness` is RECOMPUTED from the actual
outcomes, never taken on a caller's word, and an unresolved rule or an inexact
binding raises rather than scoring approximately. There is no partial score:
a number that looks exact and is not would be indistinguishable downstream from
a real one.

SEVENTY ADDITIVE RULES, THREE FILTERS. The 67 static rules and the 3 TIM rules
are additive. The three TRI rules are NOT additive entries — their base weights
are never summed. They enter solely through the per-planet multipliers that
`build_tri_bindings` already computed, and TIM rules are not re-triangulated.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, FrozenSet, List, Mapping, Optional, Sequence, Tuple

import d5_rules as R
import d5_temporal_tri as X
from d5_archetypes import PURVA_PUNYA_UNIVERSE as ARCH_PURVA_UNIVERSE
from d5_engine import D5DomainError
from d5_rules import FIRED, NOT_FIRED, UNRESOLVED, RuleOutcome


class D5ScoringError(D5DomainError):
    """Exact scoring is impossible. Raised rather than approximated."""


# ─────────────────────────────────────────────────────────────────────────────
# THE ADDITIVE UNIVERSE
# ─────────────────────────────────────────────────────────────────────────────

#: The three triangulation rules. FILTERS, NOT ADDENDS. Their base weights
#: (-2, -1.5, +3) are never summed into the Final Score; they act only through
#: the per-planet multipliers.
TRIANGULATION_RULE_IDS: FrozenSet[str] = frozenset(X.TRI_META)

#: The timing rules. ADDITIVE, and NOT re-triangulated — the TRI layer is a
#: separate certified filter surface and does not attach to a Dasha relation, a
#: transit body or a TIM_03 activation.
TIMING_RULE_IDS: FrozenSet[str] = frozenset(X.TIM_META)

IDENTITY = 1.00

#: D5-009-CORR-03 §4 · FOUNDER SCORING LOCK. When TRI_02 fires, these four Raj
#: Yoga rules contribute nothing, even where they fired on their own terms.
#:
#: Expressed as an explicit ZERO MULTIPLIER rather than a post-score overwrite,
#: so the certified equation still holds:
#:     Effective Weight = Base Weight x Product(applicable TRI multipliers)
#: The status stays FIRED, the base weight and participants are untouched, and
#: the human meaning remains available to the reading as a present but
#: suppressed signature.
RAJ_YOGA_RULE_IDS: FrozenSet[str] = frozenset({
    "D5_PAR_02", "D5_PAR_03", "D5_JAI_02", "D5_JAI_03",
})


def additive_rule_ids() -> List[str]:
    """The 70 rules that contribute an addend: 67 static plus 3 timing."""
    return sorted(set(R.RULE_META) | set(X.TIM_META))


# ─────────────────────────────────────────────────────────────────────────────
# FOUNDER-LOCKED BANDS AND BUCKETS
# ─────────────────────────────────────────────────────────────────────────────

#: Final Score bands. Half-open and exhaustive: no gap, no overlap.
#:     > +3            Elite / Legendary
#:     +1 .. +3        Moderate / Stable
#:     -1 .. < +1      Neutral / Mixed
#:     < -1            Afflicted / Blocked
SCORE_BANDS: Tuple[Tuple[str, str], ...] = (
    ("ELITE_LEGENDARY", "Elite / Legendary"),
    ("MODERATE_STABLE", "Moderate / Stable"),
    ("NEUTRAL_MIXED", "Neutral / Mixed"),
    ("AFFLICTED_BLOCKED", "Afflicted / Blocked"),
)


def score_band(final_score: float) -> Dict[str, str]:
    """The Founder band for a Final Score.

    The comparisons are written in descending order so the boundaries are read
    once each: +3 belongs to Moderate (strictly greater is Elite), +1 belongs to
    Moderate, and -1 belongs to Neutral (strictly less is Afflicted).
    """
    if final_score > 3:
        code, label = SCORE_BANDS[0]
    elif final_score >= 1:
        code, label = SCORE_BANDS[1]
    elif final_score >= -1:
        code, label = SCORE_BANDS[2]
    else:
        code, label = SCORE_BANDS[3]
    return {"code": code, "label": label}


#: Founder-locked Core Authority bucket membership.
CORE_AUTHORITY_BUCKETS: Dict[str, Tuple[str, ...]] = {
    "Executive Leader": ("D5_PAR_02", "D5_PAR_04", "D5_PAR_05", "D5_PAR_06",
                         "D5_JAI_02", "D5_JAI_03", "D5_TAJ_01", "D5_TIM_02"),
    "Creative Pioneer": ("D5_JAI_06", "D5_JAI_07", "D5_JAI_08", "D5_JAI_09",
                         "D5_TAJ_03", "D5_TAJ_04", "D5_TAJ_05", "D5_TAJ_06",
                         "D5_PAR_01", "D5_MISC_01"),
    "Spiritual Visionary": ("D5_PAR_08", "D5_PAR_09", "D5_ANAL_01",
                            "D5_TAJ_02", "D5_TAJ_07", "D5_CLA_01"),
}

CORE_AUTHORITY_OVERRIDE = "Unmanifested Potential"

#: D5-009-CORR-04 §1 · ONE UNIVERSE. The Founder Purva Punya set is defined by
#: the archetype clusters and IMPORTED here rather than restated, so the two
#: cannot drift. The superseded 10-rule list omitted JAI_09, CLA_01 and AFF_01,
#: which meant the Quick Snapshot Index and the archetype disagreed about which
#: rules even count.
PURVA_PUNYA_RULE_IDS: Tuple[str, ...] = ARCH_PURVA_UNIVERSE

PURVA_PUNYA_NO_SIGNAL = "Earned Progression"


def purva_punya_classification(score: float) -> str:
    """The Quick Snapshot Purva Punya INDEX. Exactly four values.

    D5-009-CORR-04 §1 · `Earned Progression` is NOT an Index value. It is State
    C of the `Purva Punya & Divine Grace` archetype, which is a different
    question — the Index says how much credit there is, the archetype says what
    kind of relationship the native has with it.

        >= +2.5          High Credit
        0 .. < +2.5      Balanced
        -1.5 .. < 0      Karmic Debt
        < -1.5           Blocked
    """
    if score >= 2.5:
        return "High Credit"
    if score >= 0:
        return "Balanced"
    if score >= -1.5:
        return "Karmic Debt"
    return "Blocked"


PURVA_PUNYA_OVERRIDE = "Blocked"


# ─────────────────────────────────────────────────────────────────────────────
# BRANCH-AWARE POWER VECTOR ATTRIBUTION
# ─────────────────────────────────────────────────────────────────────────────
#
# D5-007-CORR-01C · A FIRED rule contributes to 5H, 10H or 9H IF AND ONLY IF ITS
# ACTUAL TRUE BRANCH DIRECTLY INVOKES THAT D5 HOUSE.
#
# The earlier model attributed by RULE MEMBERSHIP, which was wrong twice over.
# It counted a rule whose fired branch had nothing to do with the house — PAR_14
# firing purely on a node/Venus relation was credited to 5H — and it anchored
# D5_AFF_03 to 10H because its SUBJECT is the tenth lord, when the house its
# condition names is H12.
#
# WHAT DOES NOT ANCHOR:
#   * lordship alone — being the 5L, 9L or 10L is not a house invocation;
#   * generic geometry — Kendra/Trikona contains H5, H9 and H10, but a rule
#     scoped to that union does not thereby invoke any of them;
#   * derived positions — fifth-from-PK, fifth-from-Karakamsha;
#   * D1 houses — a D1 H10 reference is not a D5 H10 reference;
#   * family, name or symbolic meaning.
#
# MULTI-VECTOR ATTRIBUTION IS FULL, NEVER PRORATED. A rule whose true branches
# invoke two houses contributes its WHOLE Effective Weight to each — the rule
# is evidence for both claims, and splitting it would understate both. Within
# one vector it counts once however many of its branches hit that house.
#
# A ZERO EFFECTIVE WEIGHT DOES NOT ERASE A BRANCH. A directly-anchored rule that
# fires with weight zero still counts toward `fired_support_count`.

POWER_VECTOR_HOUSES: Dict[str, int] = {"5H": 5, "10H": 10, "9H": 9}


def _houses_to_vectors(houses) -> FrozenSet[str]:
    inverse = {house: name for name, house in POWER_VECTOR_HOUSES.items()}
    return frozenset(inverse[h] for h in houses if h in inverse)


def _house_set(house) -> FrozenSet[str]:
    """One house, which may be absent.

    ABSENT BRANCH EVIDENCE MEANS NO DEMONSTRATED HOUSE INVOCATION, so the rule
    hits nothing. That is the conservative reading and the correct one: the
    attribution must rest on evidence the rule actually published, never on an
    assumption about what it would have published.
    """
    return frozenset() if house is None else _houses_to_vectors({house})


def power_vector_hits(rule_id: str, outcome: RuleOutcome) -> FrozenSet[str]:
    """The vectors a FIRED rule's TRUE branch directly invokes.

    Read from the rule's own EVIDENCE — the house it actually placed a graha in,
    the branch that actually held — never from its name or family. A rule that
    is not FIRED hits nothing.
    """
    if outcome.status != FIRED:
        return frozenset()
    ev = outcome.evidence

    # ── rules whose fired condition NECESSARILY names one house ──────────────
    #   The house is fixed by the rule itself, so firing is sufficient.
    fixed = {
        "D5_ANAL_02": 5,    # 1L and 9L both in D5 H5
        "D5_ANAL_03": 5,    # D5 H5 occupied by the 1L
        "D5_PAR_13": 5,     # D1 7L or Venus in D5 H5
        "D5_JAI_10": 5,     # DK in D5 H5
        "D5_CLA_04": 5,     # Saturn in D5 H5
        "D5_AFF_05": 5,     # Rahu in D5 H5
        "D5_AFF_06": 5,     # Ketu in D5 H5
        "D5_ANAL_05": 10,   # the conjunction aspects D5 H10
        "D5_PAR_04": 10,    # Sun in D5 H10
        "D5_PAR_05": 10,    # Mars in D5 H10
        "D5_PAR_06": 10,    # Saturn in D5 H10
        "D5_ANAL_01": 9,    # Ketu in D5 H9
    }
    if rule_id in fixed:
        return _houses_to_vectors({fixed[rule_id]})

    # ── rules whose branch decides WHICH house, if any ──────────────────────
    if rule_id == "D5_PAR_01":
        # D1 5L in D5 H1, H5, H9 or H10 — only the house it actually occupies.
        return _house_set(ev.get("d5_house"))
    if rule_id in ("D5_PAR_09", "D5_PAR_15"):
        # Jupiter in a trikona. PAR_15 also fires on a lagna aspect, which
        # invokes H1 and therefore no vector.
        if rule_id == "D5_PAR_15" and not ev.get("in_trikona"):
            return frozenset()          # fired on the aspect branch only
        return _house_set(ev.get("d5_house", ev.get("jupiter_d5_house")))
    if rule_id == "D5_PAR_07":
        # Two participants can establish two different houses at once.
        return _houses_to_vectors(set(ev.get("qualifying_houses_hit", [])))
    if rule_id == "D5_PAR_14":
        # ONLY the node-in-H5 branch invokes a house. The conjunction and
        # rāśi-dṛṣṭi branches are relations with Venus and invoke none.
        return _houses_to_vectors({5}) if ev.get("branch_node_in_5H") \
            else frozenset()
    if rule_id == "D5_PAR_17":
        # The lagna branch invokes H1; only the fifth-house branch counts.
        for target in ev.get("targets", []):
            if target.get("target") == "d5_5H" and target.get("branch") is True:
                return _houses_to_vectors({5})
        return frozenset()
    if rule_id in ("D5_JAI_01", "D5_JAI_06"):
        # AK / PK in H1, H5 or H11 — only H5 is a vector house.
        return _house_set(ev.get("d5_house"))
    if rule_id == "D5_JAI_18":
        # Only the 1H/5H axis invokes H5; the 1H/7H axis invokes neither.
        houses = {ev.get("ak_d5_house"), ev.get("pk_d5_house")}
        return _houses_to_vectors({5}) if 5 in houses else frozenset()
    if rule_id == "D5_ANAL_06":
        # The qualifying conjunction sits in H9 when the rule fires.
        return _houses_to_vectors({9})
    if rule_id == "D5_TIM_03":
        # Only a transit branch that crossed or aspected the FIFTH invokes H5;
        # a lagna-only hit invokes H1.
        for branch in ev.get("transit_branches", []):
            for key in ("crossing", "aspecting"):
                targets = branch.get(key)
                if isinstance(targets, list) and "d5_5H" in targets:
                    return _houses_to_vectors({5})
        return frozenset()

    # Everything else has no direct D5 house branch. See D5-007-CLOSURE.md §8
    # for the per-rule justification.
    return frozenset()


# ─────────────────────────────────────────────────────────────────────────────
# EFFECTIVE WEIGHT
# ─────────────────────────────────────────────────────────────────────────────

def _participants_of(rule_id: str, outcome: RuleOutcome) -> Tuple[List[str], bool]:
    """The physical grahas of the ACTUAL FIRED BRANCH, and whether the absence
    of any is legitimate.

    THE PARTICIPANT GATE. A FIRED non-zero rule with no participants is only
    acceptable when its evidence explicitly records a non-planetary subject —
    the D5 Lagna satisfying a Tattva rule, for instance. Anything else is a rule
    that forgot to publish its participants, and identity must NOT be silently
    assigned to it: that would let a scoring bug present as a clean number.
    """
    evidence = outcome.evidence
    participants = sorted({g for g in evidence.get("participants", [])})
    non_planetary = bool(evidence.get("non_planetary_subjects"))
    return participants, non_planetary


def effective_weight(rule_id: str, outcome: RuleOutcome,
                     bindings: Mapping[str, Any],
                     tri_02_fired: bool = False) -> Dict[str, Any]:
    """One additive rule's scoring entry.

        Effective_Weight = Base_Weight x Π(participant TRI multipliers)

    Each PHYSICAL graha contributes its multiplier ONCE, however many roles it
    fills in the rule — a single body cannot be triangulated twice.

    TIM rules are additive but NOT re-triangulated, so their rule multiplier is
    always the identity.
    """
    status = outcome.status
    base_weight = outcome.base_weight
    if status == UNRESOLVED:
        raise D5ScoringError(f"{rule_id} is UNRESOLVED; exact scoring forbidden")

    entry: Dict[str, Any] = {
        "rule_id": rule_id, "status": status, "polarity": outcome.polarity,
        "base_weight": base_weight, "participants": [],
        "participant_multipliers": {}, "rule_multiplier": IDENTITY,
        "effective_weight": 0.0, "triangulated": False,
        "non_planetary_branch": False, "raj_yoga_suppressed": False,
        "power_vector_hits": sorted(power_vector_hits(rule_id, outcome)),
    }
    if status == NOT_FIRED:
        return entry

    if rule_id in TIMING_RULE_IDS:
        # The TRI layer does not attach to a Dasha relation or a transit body.
        entry["rule_multiplier"] = IDENTITY
        entry["effective_weight"] = base_weight
        return entry

    participants, non_planetary = _participants_of(rule_id, outcome)
    if not participants and base_weight != 0 and not non_planetary:
        raise D5ScoringError(
            f"{rule_id} is FIRED with a non-zero weight but publishes no "
            "physical participants and no non-planetary justification")

    multipliers: Dict[str, float] = {}
    rule_multiplier = IDENTITY
    for graha in participants:                      # already de-duplicated
        binding = bindings.get(graha)
        if binding is None:
            # Not applicable to any TRI evaluation: multiplicative identity.
            multipliers[graha] = IDENTITY
            continue
        if not binding["multiplier_exact"]:
            raise D5ScoringError(
                f"{rule_id} participant {graha} has an inexact TRI binding")
        multipliers[graha] = binding["multiplier"]
    for factor in multipliers.values():
        rule_multiplier *= factor

    if tri_02_fired and rule_id in RAJ_YOGA_RULE_IDS:
        # The global Raj Yoga gate. Recorded in `rule_multiplier`, which is the
        # audit field the equation already multiplies through, so the zero is
        # visible in the evidence rather than applied invisibly afterwards.
        rule_multiplier = 0.0
        entry["raj_yoga_suppressed"] = True

    entry["participants"] = participants
    entry["participant_multipliers"] = multipliers
    entry["rule_multiplier"] = rule_multiplier
    entry["effective_weight"] = base_weight * rule_multiplier
    entry["triangulated"] = any(m != IDENTITY for m in multipliers.values())
    entry["non_planetary_branch"] = bool(non_planetary and not participants)
    return entry


# ─────────────────────────────────────────────────────────────────────────────
# CORE AUTHORITY · PURVA PUNYA · POWER VECTOR
# ─────────────────────────────────────────────────────────────────────────────

def _bucket_scores(entries: Mapping[str, Dict[str, Any]]) -> Dict[str, float]:
    return {name: sum(entries[r]["effective_weight"] for r in members
                      if r in entries)
            for name, members in CORE_AUTHORITY_BUCKETS.items()}


def core_authority(entries: Mapping[str, Dict[str, Any]], final_score: float,
                   tri_02_fired: bool) -> Dict[str, Any]:
    """The leading archetype, or the Founder override.

    THE OVERRIDE USES THE ACTUAL TRI_02 OUTCOME, not an inference from some
    rule's Effective Weight having become zero — a weight can be zero for
    several unrelated reasons.

    AN EXACT TIE IS PRESERVED, NOT BROKEN. No tie-break is authorised here, so a
    tie publishes every leader and leaves `primary` null; choosing one by rule
    order, dictionary order or alphabet would be inventing doctrine.
    """
    scores = _bucket_scores(entries)
    override = None
    if tri_02_fired:
        override = "D5_TRI_02 FIRED"
    elif final_score < -1:
        override = "Final Score below -1"

    if override is not None:
        return {"override": override, "override_label": CORE_AUTHORITY_OVERRIDE,
                "bucket_scores": scores, "primary": CORE_AUTHORITY_OVERRIDE,
                "leaders": [CORE_AUTHORITY_OVERRIDE], "tied": False}

    top = max(scores.values())
    leaders = sorted(name for name, value in scores.items() if value == top)
    tied = len(leaders) > 1
    return {"override": None, "override_label": None, "bucket_scores": scores,
            "primary": None if tied else leaders[0],
            "leaders": leaders, "tied": tied}


def purva_punya(entries: Mapping[str, Dict[str, Any]],
                tri_02_fired: bool) -> Dict[str, Any]:
    """The Purva Punya score and classification.

    NO SIGNAL IS NOT THE SAME AS ZERO. `Earned Progression` is a no-signal
    presentation state and is used only when NO rule in the set fired. A set
    whose fired positives and negatives cancel to exactly zero is a real
    measurement of Balanced, and reporting it as no-signal would erase it.
    """
    members = [r for r in PURVA_PUNYA_RULE_IDS if r in entries]
    score = sum(entries[r]["effective_weight"] for r in members)
    fired = sorted(r for r in members if entries[r]["status"] == FIRED)
    no_signal = not fired

    # D5-009-CORR-04 §1 · `no_signal` is retained as an INTERNAL boolean and no
    # longer selects a classification. A chart with no fired Purva rule scores
    # 0, which is Balanced — the absence of signal is a separate fact from the
    # amount of credit, and the archetype (State C) is where it is expressed.
    override = "D5_TRI_02 FIRED" if tri_02_fired else None
    classification = (PURVA_PUNYA_OVERRIDE if tri_02_fired
                      else purva_punya_classification(score))

    return {"score": score, "classification": classification,
            "no_signal": no_signal, "override": override,
            "member_rule_ids": sorted(members), "fired_rule_ids": fired}


def primary_power_vector(entries: Mapping[str, Dict[str, Any]]) -> Dict[str, Any]:
    """The leading power vector, from BRANCH ATTRIBUTIONS.

        1 · highest vector total
        2 · highest single attributed FIRED Effective Weight
        3 · larger count of attributed FIRED rules
        4 · still tied -> publish every tied vector

    A rule that fired but whose branch did not hit a vector contributes nothing
    to that vector's score, its largest single weight, or its support count.
    """
    vectors: Dict[str, Dict[str, Any]] = {}
    for name in POWER_VECTOR_HOUSES:
        attributed = sorted(rid for rid, entry in entries.items()
                            if name in entry["power_vector_hits"])
        weights = [entries[rid]["effective_weight"] for rid in attributed]
        vectors[name] = {
            "vector_score": sum(weights),
            "highest_single_effective_weight": max(weights) if weights else 0.0,
            "fired_support_count": len(attributed),
            "attributed_rule_ids": attributed,
            # Retained for continuity with the earlier evidence shape.
            "fired_rule_ids": attributed,
        }

    leaders = sorted(vectors)
    for key in ("vector_score", "highest_single_effective_weight",
                "fired_support_count"):
        best = max(vectors[name][key] for name in leaders)
        leaders = [name for name in leaders if vectors[name][key] == best]
        if len(leaders) == 1:
            break

    tied = len(leaders) > 1
    return {"vectors": vectors, "primary": None if tied else leaders[0],
            "leaders": sorted(leaders), "tied": tied}


# ─────────────────────────────────────────────────────────────────────────────
# THE SCORING ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

def build_score(static_outcomes: Mapping[str, RuleOutcome],
                timing_outcomes: Mapping[str, RuleOutcome],
                triangulation_outcomes: Mapping[str, RuleOutcome]
                ) -> Dict[str, Any]:
    """The complete deterministic score.

    THE READINESS GATE IS RECOMPUTED, NEVER ACCEPTED. A caller asserting
    `score_ready=True` proves nothing; the verdict is derived here from the
    actual outcomes, and anything short of exact raises.
    """
    readiness = X.assess_score_readiness(static_outcomes, timing_outcomes,
                                         triangulation_outcomes)
    if not readiness["exact_score_ready"]:
        raise D5ScoringError(
            "exact scoring refused: "
            f"blocking rules {readiness['blocking_rule_ids']}, "
            f"blocking TRI {readiness['blocking_tri_rules']}, "
            f"inexact bindings "
            f"{readiness['triangulation_bindings']['inexact_bindings']}")

    bindings = readiness["triangulation_bindings"]["bindings"]
    for planet, binding in sorted(bindings.items()):
        if not binding["multiplier_exact"]:
            raise D5ScoringError(f"{planet} has an inexact TRI binding")

    tri_02_outcome = triangulation_outcomes.get("D5_TRI_02")
    tri_02_active = tri_02_outcome is not None and tri_02_outcome.status == FIRED

    entries: Dict[str, Dict[str, Any]] = {}
    for rule_id in additive_rule_ids():
        outcome = (static_outcomes.get(rule_id)
                   or timing_outcomes.get(rule_id))
        if outcome is None:
            raise D5ScoringError(f"{rule_id} has no outcome to score")
        entries[rule_id] = effective_weight(rule_id, outcome, bindings,
                                            tri_02_active)

    # THE TRI RULES ARE NOT SUMMED. Only the 70 additive entries contribute.
    final_score = sum(entry["effective_weight"] for entry in entries.values())

    tri_02 = triangulation_outcomes.get("D5_TRI_02")
    tri_02_fired = tri_02 is not None and tri_02.status == FIRED

    return {
        "score_ready": True,
        "rules": entries,
        "additive_rule_count": len(entries),
        "final_score": final_score,
        "score_band": score_band(final_score),
        "core_authority": core_authority(entries, final_score, tri_02_fired),
        "purva_punya": purva_punya(entries, tri_02_fired),
        "primary_power_vector": primary_power_vector(entries),
        "triangulation_bindings": readiness["triangulation_bindings"],
    }
