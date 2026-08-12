"""
d5_temporal_tri.py — D5-004 · TIMING, TRIANGULATION AND SCORE READINESS.

THREE TIMING RULES, THREE TRIANGULATION RULES, ONE HONEST VERDICT. TIM_01..03
and TRI_01..03 evaluate to FIRED / NOT_FIRED / UNRESOLVED under the same
three-valued contract D5-003 established, reusing `t_or` and `t_and` rather than
restating them. `assess_score_readiness` then answers one question: can a single
exact Final Score be computed without guessing?

NOTHING IS SCORED HERE. No Final Score, no archetype, no Purva Punya Index, no
Primary Power Vector, no tier and no label. The multipliers are frozen as
constants and are attached to a binding only where the binding is unambiguous;
they are never multiplied into a weight.

AN UNRESOLVED RULE IS NOT ZERO, AND AN UNRESOLVED MULTIPLIER IS NOT 1.0. That is
the whole point of the readiness layer. Treating either as its neutral element
would produce a number that looks exact and is not, and the number would then be
indistinguishable from a real one downstream.

EVERY EXTERNAL FACT IS SUPPLIED, NEVER DERIVED. Dasha and Bhukti identity,
transit positions, yoga participation, D1 affliction facts and D9 facts all
arrive through `TemporalInputs` as certified values. This module recomputes no
Vimshottari, no transit, no D9 division and no D1 dignity. An input that has not
been supplied yields UNRESOLVED for whatever depends on it — never a default.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, FrozenSet, List, Mapping, Optional, Sequence, Tuple

import d5_predicates as P
import d5_rules as R
from d5_engine import D5Doctrine, D5DomainError
from d5_rules import (FALSE, FIRED, NOT_FIRED, TRUE, UNKNOWN, UNRESOLVED,
                      CERTIFIED_COMBUSTION, Ctx, D5RuleInputs, D5RulesDoctrine,
                      RuleOutcome, status_of, t_and, t_or)

# ─────────────────────────────────────────────────────────────────────────────
# MANIFEST — transcribed from the workbook, same source as RULE_META
# ─────────────────────────────────────────────────────────────────────────────

TIM_META: Dict[str, Tuple[str, float]] = {
    "D5_TIM_01": ("Positive", 2), "D5_TIM_02": ("Positive", 2),
    "D5_TIM_03": ("Positive", 1.5),
}

TRI_META: Dict[str, Tuple[str, float]] = {
    "D5_TRI_01": ("Negative", -2), "D5_TRI_02": ("Negative", -1.5),
    "D5_TRI_03": ("Positive", 3),
}

#: Founder-locked triangulation multipliers. FROZEN, and never applied to a
#: weight in this module.
TRI_MULTIPLIER: Dict[str, float] = {
    "D5_TRI_01": 0.50, "D5_TRI_02": 0.00, "D5_TRI_03": 1.50,
}

#: TRI_02's factor is zero, so any product containing it collapses to zero. That
#: is why TRI_02 "dominates" — it is arithmetic, not a precedence rule, and the
#: binding code multiplies rather than selecting.
TRI_02_DOMINANT_MULTIPLIER = 0.00

#: Every multiplier a fully-resolved binding can produce, as products of the
#: three frozen factors. 0.75 is TRI_01 x TRI_03 and was unreachable while the
#: binding used precedence.
EXACT_MULTIPLIER_VALUES = frozenset({0.00, 0.50, 0.75, 1.00, 1.50})

#: The multiplicative identity, for a binding where every applicable TRI state
#: is resolved and none of the filters fired. NOT the same thing as None.
IDENTITY_MULTIPLIER = 1.00

#: The relative whole-sign positions TIM_01 accepts — the Kendra/Trikona union.
TIM_01_QUALIFYING_POSITIONS = P.KENDRA_TRIKONA

#: The two transit bodies TIM_03 recognises. Either alone is sufficient.
TIM_03_TRANSIT_BODIES: Tuple[str, ...] = ("Jupiter", "Saturn")

# ── unresolved-input vocabulary ──────────────────────────────────────────────
PERIOD_IDENTITY = "Dasha_Period_Identity"
TRANSIT_POSITIONS = "Transit_Positions"
YOGA_PARTICIPATION = "Positive_Fired_Yoga_Participation"
RAJ_YOGA_PARTICIPATION = "D5_Raj_Yoga_Participation"
D1_AFFLICTION_FACTS = "Certified_D1_Affliction_Facts"
D9_FACTS = "Certified_D9_Facts"
EXACT_D5_DEGREE = "Exact_D5_Target_Degree"
# D5-006 CLOSED THE LAST RESIDUAL. "Connected to D5_1H/5H/10H" is Founder-locked
# as five explicit branches, so TRI_03 names no residual binding at all. The only
# thing that can leave it unresolved now is a genuinely missing certified fact.

#: D5-006 §5 · the houses a karaka may be connected to.
TRI_03_TARGET_HOUSES: Tuple[int, ...] = (1, 5, 10)


@dataclass(frozen=True)
class TemporalInputs:
    """Certified facts this layer consumes but never derives.

    Every field defaults to None, and None means NOT SUPPLIED — never "absent
    and therefore false". A missing input propagates as UNKNOWN through `t_or`
    and `t_and`, so it can still be dominated by an already-decided branch but
    can never be silently read as a negative.
    """
    #: Current Mahadasha and Antardasha lords, from the certified Vimshottari.
    mahadasha_lord: Optional[str] = None
    antardasha_lord: Optional[str] = None
    #: Transiting sign index per body, e.g. {"Jupiter": 4, "Saturn": 9}.
    transit_signs: Optional[Mapping[str, int]] = None
    #: The grahas participating in at least one positive FIRED D5 yoga. Supplied
    #: explicitly; never inferred from interpretation prose.
    positive_fired_yoga_participants: Optional[FrozenSet[str]] = None
    #: The grahas forming a D5 Raj Yoga. D5-004 does not define the term.
    d5_raj_yoga_participants: Optional[FrozenSet[str]] = None
    #: {graha: {"combust": bool, "debilitated": bool, "graha_yuddha_defeated": bool}}
    d1_conditions: Optional[Mapping[str, Mapping[str, Any]]] = None
    #: {graha: {"debilitated": bool, "house": int, "sign_index": int}}
    d9_facts: Optional[Mapping[str, Mapping[str, Any]]] = None
    #: {"d5_lagna": degree, "d5_5H": degree} — only if a CERTIFIED exact D5
    #: degree ever exists. D5-001 deliberately publishes none.
    exact_d5_target_degrees: Optional[Mapping[str, float]] = None


def _outcome(rule_id: str, meta: Mapping[str, Tuple[str, float]],
             value: Optional[bool], evidence: Dict[str, Any],
             unresolved: Sequence[str]) -> RuleOutcome:
    polarity, weight = meta[rule_id]
    status = status_of(value)
    names = [] if status != UNRESOLVED else sorted(set(unresolved))
    if status == UNRESOLVED and not names:
        raise D5DomainError("an UNRESOLVED rule must name its unresolved input")
    return RuleOutcome(rule_id=rule_id, status=status, polarity=polarity,
                       base_weight=weight, evidence=evidence,
                       unresolved_primitives=names)


def _period(inputs: TemporalInputs) -> Tuple[Optional[str], Optional[str]]:
    return inputs.mahadasha_lord, inputs.antardasha_lord


# ─────────────────────────────────────────────────────────────────────────────
# TIM_01 · Dasha lord's relative position from the Bhukti lord, in D5
# ─────────────────────────────────────────────────────────────────────────────

def evaluate_tim_01(ctx: Ctx, inputs: TemporalInputs) -> RuleOutcome:
    """The Mahadasha lord counted FROM the Antardasha lord, in whole D5 signs.

    Direction is load-bearing and the workbook states it: the Dasha lord's
    position *from* the Bhukti lord. The relation is not symmetric — 4 from a
    body means 10 the other way, and both happen to be in the qualifying set, but
    2 and 12 are not, so a reversed count would agree on some charts and not on
    others. Counted one way, always.
    """
    md, ad = _period(inputs)
    evidence: Dict[str, Any] = {"mahadasha_lord": md, "antardasha_lord": ad,
                                "qualifying_positions": sorted(TIM_01_QUALIFYING_POSITIONS)}
    if md is None or ad is None:
        evidence["relative_position"] = "unresolved"
        return _outcome("D5_TIM_01", TIM_META, UNKNOWN, evidence, [PERIOD_IDENTITY])
    for label, graha in (("mahadasha", md), ("antardasha", ad)):
        if graha not in ctx.grahas:
            evidence["relative_position"] = "unresolved"
            evidence[f"{label}_unknown_graha"] = graha
            return _outcome("D5_TIM_01", TIM_META, UNKNOWN, evidence,
                            [PERIOD_IDENTITY])
    md_si, ad_si = ctx.d5_sign(md), ctx.d5_sign(ad)
    position = ((md_si - ad_si) % 12) + 1
    evidence.update({"mahadasha_d5_sign_index": md_si,
                     "mahadasha_d5_house": ctx.d5_house(md),
                     "antardasha_d5_sign_index": ad_si,
                     "antardasha_d5_house": ctx.d5_house(ad),
                     "relative_position": position})
    return _outcome("D5_TIM_01", TIM_META,
                    position in TIM_01_QUALIFYING_POSITIONS, evidence, [])


# ─────────────────────────────────────────────────────────────────────────────
# TIM_02 · D1 5th or 10th lord in D5 H1, during its own period
# ─────────────────────────────────────────────────────────────────────────────

def evaluate_tim_02(ctx: Ctx, inputs: TemporalInputs) -> RuleOutcome:
    """Either candidate is sufficient, and each needs BOTH halves.

    A candidate outside D5 H1 fails on placement alone, whatever the period is,
    so period identity cannot rescue it: FALSE AND UNKNOWN is FALSE. Missing
    period identity therefore blocks the rule only where a candidate is actually
    sitting in H1 — which is exactly the "only where it could alter the result"
    the ticket asks for.
    """
    md, ad = _period(inputs)
    candidates = [("d1_5L", ctx.d1_lord(5)), ("d1_10L", ctx.d1_lord(10))]
    branches: List[Dict[str, Any]] = []
    combined = FALSE
    for label, graha in candidates:
        in_h1 = ctx.d5_house(graha) == 1
        if not in_h1:
            period_match: Optional[bool] = FALSE
        elif md is not None and graha == md:
            period_match = TRUE
        elif ad is not None and graha == ad:
            period_match = TRUE
        elif md is None or ad is None:
            # At least one period identity is missing and the placement holds,
            # so the missing one could still make this candidate qualify.
            period_match = UNKNOWN
        else:
            period_match = FALSE
        value = t_and(in_h1, period_match)
        branches.append({"candidate": label, "graha": graha,
                         "d5_house": ctx.d5_house(graha), "in_d5_1H": in_h1,
                         "period_match": "unresolved" if period_match is UNKNOWN
                                         else period_match})
        combined = t_or(combined, value)
    evidence = {"mahadasha_lord": md, "antardasha_lord": ad,
                "same_graha_rules_both": candidates[0][1] == candidates[1][1],
                "branches": branches}
    return _outcome("D5_TIM_02", TIM_META, combined, evidence,
                    [PERIOD_IDENTITY] if combined is UNKNOWN else [])


# ─────────────────────────────────────────────────────────────────────────────
# TIM_03 · Jupiter or Saturn on the D5 Lagna or 5th, during an active D5 yoga
# ─────────────────────────────────────────────────────────────────────────────

def evaluate_tim_03(ctx: Ctx, inputs: TemporalInputs) -> RuleOutcome:
    """Sign-wide activation, gated on an explicitly supplied yoga participation.

    PEAK INTENSITY IS REPORTED SEPARATELY AND NEVER GATES THE RULE. The Founder
    lock mentions a plus-or-minus three degree window from the exact Lagna or 5th
    degree, and D5-001 deliberately publishes no synthetic D5 degree, so peak
    intensity is UNRESOLVED unless a certified exact target degree is supplied.
    Folding it into the firing condition would make a supplementary refinement
    block the sign-wide rule it is meant to refine.
    """
    md, ad = _period(inputs)
    lagna_si = ctx.d5_lagna_si
    fifth_si = (lagna_si + 4) % 12
    targets = {"d5_lagna": lagna_si, "d5_5H": fifth_si}

    # ── active yoga branch ───────────────────────────────────────────────────
    #
    # D5-004-CORR-01A · None AND frozenset() ARE DIFFERENT FACTS.
    #   None        -> participant identity was never supplied      -> UNKNOWN
    #   frozenset() -> authoritatively NO qualifying participants    -> FALSE
    #
    # The distinction is load-bearing because FALSE AND UNKNOWN is FALSE: an
    # explicitly empty set decides TIM_03 outright, even with the period lords
    # and the transit positions both missing. Collapsing the two would turn a
    # determinable NOT_FIRED into a permanent UNRESOLVED.
    participants = inputs.positive_fired_yoga_participants
    if participants is None:
        active = UNKNOWN
        active_detail = "unresolved · participant set not supplied"
    elif not participants:
        active = FALSE
        active_detail = "no qualifying positive fired D5 yoga participants"
    else:
        known = [g for g in (md, ad) if g is not None]
        hits = [g for g in known if g in participants]
        if hits:
            active = TRUE
            active_detail = hits
        elif md is not None and ad is not None:
            # Both period lords are known and neither participates.
            active = FALSE
            active_detail = []
        else:
            # A missing period lord could still turn out to participate.
            active = UNKNOWN
            active_detail = "unresolved · a period lord identity is missing"

    # ── transit branch ───────────────────────────────────────────────────────
    transit_signs = inputs.transit_signs or {}
    transit_branches: List[Dict[str, Any]] = []
    transit_hit: Optional[bool] = FALSE
    for body in TIM_03_TRANSIT_BODIES:
        sign = transit_signs.get(body)
        if sign is None:
            transit_branches.append({"body": body, "transit_sign_index": None,
                                     "crossing": "unresolved",
                                     "aspecting": "unresolved"})
            transit_hit = t_or(transit_hit, UNKNOWN)
            continue
        crossing = [name for name, si in targets.items() if si == sign]
        aspecting = [name for name, si in targets.items()
                     if P.graha_aspects_sign(body, sign, si)]
        transit_branches.append({"body": body, "transit_sign_index": sign,
                                 "crossing": crossing, "aspecting": aspecting})
        transit_hit = t_or(transit_hit, bool(crossing or aspecting))

    # ── peak intensity, supplementary only ───────────────────────────────────
    exact = inputs.exact_d5_target_degrees
    peak = {"status": "unresolved",
            "reason": "D5-001 publishes no synthetic D5 degree",
            "window_degrees": 3.0, "gates_the_rule": False}
    if exact:
        peak = {"status": "supplied", "targets": dict(exact),
                "window_degrees": 3.0, "gates_the_rule": False}

    combined = t_and(active, transit_hit)
    unresolved: List[str] = []
    if active is UNKNOWN:
        unresolved.append(YOGA_PARTICIPATION if participants is None
                          else PERIOD_IDENTITY)
    if transit_hit is UNKNOWN:
        unresolved.append(TRANSIT_POSITIONS)
    evidence = {"mahadasha_lord": md, "antardasha_lord": ad,
                "d5_lagna_sign_index": lagna_si, "d5_5H_sign_index": fifth_si,
                "active_yoga": "unresolved" if active is UNKNOWN else active,
                "active_yoga_detail": active_detail,
                "transit_branches": transit_branches,
                "peak_intensity": peak}
    return _outcome("D5_TIM_03", TIM_META, combined, evidence, unresolved)


# ─────────────────────────────────────────────────────────────────────────────
# TRI_01 · exalted in D5 but weakened in D1
# ─────────────────────────────────────────────────────────────────────────────

D1_WEAKENING_BRANCHES = ("combust", "debilitated", "graha_yuddha_defeated")

#: Sentinel for a field the caller did not supply. `record.get(field)` returning
#: None cannot distinguish "absent" from "explicitly null", and `bool(...)` on it
#: silently reads absent as False — which is exactly the substitution
#: D5-004-CORR-01B forbids.
_MISSING = object()


def _tri_branch(record: Mapping[str, Any], field: str) -> Optional[bool]:
    """One three-valued branch from a partially supplied certified record.

    Supplied -> the boolean the caller stated. Absent -> UNKNOWN. Never False by
    default: a fact nobody asserted is not a fact asserted to be absent.
    """
    value = record.get(field, _MISSING)
    return UNKNOWN if value is _MISSING else bool(value)


def evaluate_tri_01(ctx: Ctx, inputs: TemporalInputs) -> RuleOutcome:
    """Per PHYSICAL PLANET, never globalised.

    A planet not exalted in D5 fails on the first conjunct, so its D1 facts are
    not needed and their absence does not make it unresolved.

    D5-004-CORR-01B · PARTIAL D1 RECORDS. The three weakening branches are ORed
    three-valuedly, so:
      * any branch explicitly True  -> TRUE, whatever else is missing;
      * all three explicitly False  -> FALSE;
      * no True branch and at least one missing -> UNKNOWN.
    A record naming two clean branches and omitting the third does NOT clear the
    planet — the omitted branch could still be the one that fires.
    """
    conditions = inputs.d1_conditions
    findings: List[Dict[str, Any]] = []
    unresolved_planets: List[str] = []
    fired_planets: List[str] = []
    combined = FALSE
    for graha in sorted(ctx.grahas):
        exalted = ctx.is_exalted_in_d5(graha)
        record = (conditions or {}).get(graha)
        branch_states: Any = {}
        if not exalted:
            value: Optional[bool] = FALSE
            supplied_true: List[str] = []
        elif record is None:
            value = UNKNOWN
            branch_states = {b: "unresolved" for b in D1_WEAKENING_BRANCHES}
            supplied_true = []
            unresolved_planets.append(graha)
        else:
            branches = {b: _tri_branch(record, b) for b in D1_WEAKENING_BRANCHES}
            branch_states = {b: ("unresolved" if v is UNKNOWN else v)
                             for b, v in branches.items()}
            supplied_true = [b for b, v in branches.items() if v is TRUE]
            value = t_or(*branches.values())
            if value is TRUE:
                fired_planets.append(graha)
            elif value is UNKNOWN:
                unresolved_planets.append(graha)
        if exalted or value is not FALSE:
            findings.append({"planet": graha, "d5_exalted": exalted,
                             "d5_sign_index": ctx.d5_sign(graha),
                             "branch_states": branch_states,
                             "d1_weakening_branches": supplied_true,
                             # ONE state vocabulary across TRI_01/02/03, so the
                             # binding map can read every surface the same way.
                             "state": status_of(value)})
        combined = t_or(combined, value)
    evidence = {"multiplier": TRI_MULTIPLIER["D5_TRI_01"],
                "weakening_branches_considered": list(D1_WEAKENING_BRANCHES),
                "per_planet": findings,
                "triggering_planets": fired_planets,
                "unresolved_planets": unresolved_planets}
    return _outcome("D5_TRI_01", TRI_META, combined, evidence,
                    [D1_AFFLICTION_FACTS] if combined is UNKNOWN else [])


# ─────────────────────────────────────────────────────────────────────────────
# TRI_02 · a D5 Raj Yoga participant wrecked in D9
# ─────────────────────────────────────────────────────────────────────────────

D9_DUSTHANA = (6, 8, 12)


def evaluate_tri_02(ctx: Ctx, inputs: TemporalInputs) -> RuleOutcome:
    """D5-004 DOES NOT DEFINE "planet forming a D5 Raj Yoga".

    The participant set is supplied by an authoritative later binding. With no
    set supplied the rule is UNRESOLVED — not empty, and therefore not false. A
    planet afflicted in D9 that is NOT a supplied participant never triggers the
    rule, however badly placed it is.
    """
    participants = inputs.d5_raj_yoga_participants
    facts = inputs.d9_facts
    if participants is None:
        return _outcome("D5_TRI_02", TRI_META, UNKNOWN,
                        {"multiplier": TRI_MULTIPLIER["D5_TRI_02"],
                         "participants": "unresolved",
                         "d9_dusthana": list(D9_DUSTHANA)},
                        [RAJ_YOGA_PARTICIPATION])
    findings: List[Dict[str, Any]] = []
    unresolved_planets: List[str] = []
    fired_planets: List[str] = []
    combined = FALSE
    for graha in sorted(participants):
        record = (facts or {}).get(graha)
        if record is None:
            value: Optional[bool] = UNKNOWN
            detail: Any = "unresolved"
            unresolved_planets.append(graha)
        else:
            # D5-004-CORR-01C · PARTIAL D9 RECORDS. Either branch alone can fire
            # the rule, so an explicit True on one settles it whatever the other
            # is missing; and an explicit clean value on one CANNOT settle it
            # while the other is absent.
            debilitated = _tri_branch(record, "debilitated")
            house = record.get("house", _MISSING)
            in_dusthana: Optional[bool] = (UNKNOWN if house is _MISSING
                                           else house in D9_DUSTHANA)
            value = t_or(debilitated, in_dusthana)
            detail = {"d9_debilitated": ("unresolved" if debilitated is UNKNOWN
                                         else debilitated),
                      "d9_house": ("unresolved" if house is _MISSING else house),
                      "d9_dusthana": ("unresolved" if in_dusthana is UNKNOWN
                                      else in_dusthana)}
            if value is TRUE:
                fired_planets.append(graha)
            elif value is UNKNOWN:
                unresolved_planets.append(graha)
        findings.append({"planet": graha, "d9": detail,
                         "state": status_of(value)})
        combined = t_or(combined, value)
    evidence = {"multiplier": TRI_MULTIPLIER["D5_TRI_02"],
                "participants": sorted(participants),
                "d9_dusthana": list(D9_DUSTHANA),
                "per_planet": findings, "triggering_planets": fired_planets,
                "unresolved_planets": unresolved_planets}
    return _outcome("D5_TRI_02", TRI_META, combined, evidence,
                    [D9_FACTS] if combined is UNKNOWN else [])


# ─────────────────────────────────────────────────────────────────────────────
# TRI_03 · the ultimate truth test — structurally unresolved
# ─────────────────────────────────────────────────────────────────────────────

def _connected_to_target_houses(ctx: Ctx, karaka: str) -> Dict[str, Any]:
    """D5-006 §5 · FIVE explicit branches, any one of which connects.

    Occupancy · lordship by physical identity · graha-dṛṣṭi onto a target house ·
    rāśi-dṛṣṭi onto a target house's SIGN · Association with a target house lord.

    NO SELF-ASSOCIATION. Where the karaka IS one of the three lords, the explicit
    lordship branch establishes the connection; asking whether it is associated
    with itself would be meaningless and is skipped.

    A ONE-WAY ASPECT ONTO A LORD IS NOT ASSOCIATION — branch 5 uses the canonical
    Lock 1 predicate, which needs a mutual aspect, a conjunction or an exchange.
    Branch 3 is the place where a single-direction dṛṣṭi counts, and it targets
    the HOUSE, not the lord.
    """
    house = ctx.d5_house(karaka)
    lords = {n: ctx.d5_lord(n) for n in TRI_03_TARGET_HOUSES}
    target_signs = {n: (ctx.d5_lagna_si + n - 1) % 12
                    for n in TRI_03_TARGET_HOUSES}

    occupancy = [n for n in TRI_03_TARGET_HOUSES if house == n]
    lordship = [n for n, lord in lords.items() if lord == karaka]
    graha_drishti = [n for n in TRI_03_TARGET_HOUSES
                     if P.graha_aspects_house(karaka, house, n)]
    rashi = [n for n, si in target_signs.items()
             if P.rashi_drishti(ctx.d5_sign(karaka), si)]
    association = [n for n, lord in lords.items()
                   if lord != karaka and ctx.associated(karaka, lord)]

    branches = {"occupancy": occupancy, "lordship": lordship,
                "graha_drishti": graha_drishti, "rashi_drishti": rashi,
                "association_with_house_lord": association}
    return {"connected": bool(occupancy or lordship or graha_drishti
                              or rashi or association),
            "d5_house": house, "house_lords": lords,
            "target_houses": list(TRI_03_TARGET_HOUSES), "branches": branches}


def evaluate_tri_03(ctx: Ctx, inputs: TemporalInputs) -> RuleOutcome:
    """(AK OR AMK) (Well_Placed OR Vargottama) in D9 AND Connected in D5.

    D5-006 · BOTH OPERANDS ARE NOW LOCKED. Well_Placed is the Founder Strong
    predicate read in the D9 context with the D1-D9 Vargottama pair; Connected
    is the five-branch relation above. TRI_03 can therefore FIRE.

    `Well_Placed OR Vargottama` stays an OR, so a Vargottama karaka satisfies
    the D9 side even where the Strong branch is FALSE.

    MISSING FACTS ARE NOT OVER-REPORTED. A karaka whose Connected conjunct is
    already FALSE contributes nothing unresolved, because no D9 or combustion
    value could change its result — FALSE AND UNKNOWN is FALSE.
    """
    facts = inputs.d9_facts or {}
    findings: List[Dict[str, Any]] = []
    combined = FALSE
    unresolved: List[str] = []
    for karaka in ("AK", "AMK"):
        graha = ctx.karaka(karaka)
        connection = _connected_to_target_houses(ctx, graha)
        connected = connection["connected"]
        d1_si = ctx.d1_sign(graha)
        record = facts.get(graha) or {}
        d9_si = record.get("sign_index")
        if d9_si is None and karaka == "AK":
            d9_si = ctx.karakamsha["d9_ak_sign_index"]
        d9_house = record.get("house")
        vargottama = (P.is_d1_d9_vargottama(d1_si, d9_si)
                      if d9_si is not None else UNKNOWN)
        karaka_unresolved: List[str] = []
        if d9_si is None or d9_house is None:
            well_placed: Optional[bool] = UNKNOWN
            strong_detail: Any = "unresolved · D9 sign or house not supplied"
            karaka_unresolved.append(D9_FACTS)
        else:
            well_placed, strong_detail = ctx.strong(graha, d9_si, d9_house,
                                                    bool(vargottama))
            if well_placed is UNKNOWN:
                karaka_unresolved.append(CERTIFIED_COMBUSTION)
        d9_condition = t_or(well_placed, vargottama)
        karaka_result = t_and(d9_condition, connected)
        if karaka_result is UNKNOWN:
            # Only a karaka that could still change the answer reports anything.
            unresolved.extend(karaka_unresolved)
        findings.append({
            "karaka": karaka, "graha": graha, "d1_sign_index": d1_si,
            "d9_sign_index": d9_si if d9_si is not None else "unresolved",
            "d9_house": d9_house if d9_house is not None else "unresolved",
            "vargottama_d1_d9": (vargottama if vargottama is not UNKNOWN
                                 else "unresolved"),
            "well_placed_d9": ("unresolved" if well_placed is UNKNOWN
                               else well_placed),
            "well_placed_detail": strong_detail,
            "d9_condition": ("unresolved" if d9_condition is UNKNOWN
                             else d9_condition),
            "connected": connected, "connection": connection,
            "state": status_of(karaka_result)})
        combined = t_or(combined, karaka_result)
    if combined is not UNKNOWN:
        unresolved = []
    evidence = {"multiplier": TRI_MULTIPLIER["D5_TRI_03"],
                "target_houses": list(TRI_03_TARGET_HOUSES),
                "per_karaka": findings,
                "participants": sorted({f["graha"] for f in findings
                                        if f["state"] == FIRED})}
    return _outcome("D5_TRI_03", TRI_META, combined, evidence, unresolved)


# ─────────────────────────────────────────────────────────────────────────────
# TRIANGULATION BINDING
# ─────────────────────────────────────────────────────────────────────────────

def build_tri_bindings(tri_outcomes: Mapping[str, RuleOutcome]) -> Dict[str, Any]:
    """Per-planet triangulation bindings, and a multiplier only where exact.

    D5-006-CORR-01A · THE APPLICABILITY UNIVERSE IS THE PER-PLANET SURFACE.
    A physical planet belongs to the binding universe when it appears in ANY
    authoritative per-planet or per-karaka evaluation:

        TRI_01.evidence["per_planet"] ∪ TRI_02.evidence["per_planet"]
                                     ∪ TRI_03.evidence["per_karaka"]

    Building the map from `triggering_planets` and `unresolved_planets` alone —
    as D5-006 did — silently DROPPED every planet a rule evaluated and cleared.
    An exalted planet with certified-clean D1 facts is applicable to TRI_01 and
    resolved to NOT_FIRED; it must carry an explicit identity multiplier, not
    vanish. `NOT_FIRED` is an answer.

    THREE DISTINCT STATES, and they must never be conflated:
      * `multiplier = 1.0`, exact  — applicable, resolved, no filter fired;
      * any product of the fired factors, exact — e.g. 0.50 x 1.50 = 0.75;
      * `multiplier = None`, inexact — applicable, but something is UNRESOLVED;
      * absent from the map entirely — not applicable to any TRI evaluation.

    NOT GLOBALISED ACROSS THE CHART. Every finding names the physical planet it
    was measured on, and a later weight multiplication may only reach a rule
    whose own evidence is bound to that same planet.
    """
    bindings: Dict[str, Dict[str, Any]] = {}

    def slot(planet: str) -> Dict[str, Any]:
        return bindings.setdefault(planet, {"planet": planet, "tri_01": None,
                                            "tri_02": None, "tri_03": None,
                                            "multiplier": None,
                                            "multiplier_exact": False,
                                            "applied_multipliers": {},
                                            "notes": []})

    for rule_id, key in (("D5_TRI_01", "tri_01"), ("D5_TRI_02", "tri_02")):
        outcome = tri_outcomes.get(rule_id)
        if outcome is None:
            continue
        per_planet = outcome.evidence.get("per_planet")
        if per_planet is not None:
            # THE AUTHORITATIVE SURFACE. Every state is carried through,
            # NOT_FIRED included.
            for finding in per_planet:
                slot(finding["planet"])[key] = finding["state"]
        else:
            # Compatibility only, for an outcome that predates the per-planet
            # surface or was hand-built by a caller.
            for planet in outcome.evidence.get("triggering_planets", []):
                slot(planet)[key] = FIRED
            for planet in outcome.evidence.get("unresolved_planets", []):
                slot(planet)[key] = UNRESOLVED

    tri_03 = tri_outcomes.get("D5_TRI_03")
    if tri_03 is not None:
        for finding in tri_03.evidence.get("per_karaka", []):
            entry = slot(finding["graha"])
            entry["tri_03"] = finding["state"]
            entry["notes"].append(f"{finding['karaka']} karaka")

    for entry in bindings.values():
        states = {"D5_TRI_01": entry["tri_01"], "D5_TRI_02": entry["tri_02"],
                  "D5_TRI_03": entry["tri_03"]}
        if UNRESOLVED in states.values():
            # UNRESOLVED DOMINATES EXACTNESS. Known filters are NOT partially
            # multiplied around an unresolved one — a partial product would look
            # exact and be wrong. An unresolved multiplier is not 1.0 either, so
            # none is attached, and this is what `inexact_bindings` means.
            entry["multiplier"] = None
            entry["multiplier_exact"] = False
            entry["applied_multipliers"] = {}
            entry["notes"].append("multiplier withheld: an unresolved TRI state "
                                  "is not 1.0")
            continue
        # D5-006-CORR-02 · THE TRI FILTERS ARE MULTIPLICATIVE, NOT A PRECEDENCE
        # LADDER. The earlier if/elif chain returned the FIRST matching filter
        # and so MASKED TRI_03 whenever TRI_01 also fired, reporting 0.50 where
        # the product is 0.50 x 1.50 = 0.75.
        #
        # TRI_02 still dominates — but as a CONSEQUENCE of the arithmetic rather
        # than as a special case: any product containing 0.00 is 0.00.
        applied: Dict[str, float] = {}
        multiplier = IDENTITY_MULTIPLIER
        for rule_id, state in states.items():
            if state != FIRED:
                continue
            factor = TRI_MULTIPLIER[rule_id]
            applied[rule_id] = factor
            multiplier *= factor
        entry["multiplier"] = multiplier
        entry["multiplier_exact"] = True
        # The arithmetic source stays visible, so the result can be
        # reconstructed from evidence rather than trusted.
        entry["applied_multipliers"] = applied
        if not applied:
            entry["notes"].append("no triangulation filter applies; identity")
        elif entry["tri_02"] == FIRED:
            entry["notes"].append("TRI_02 applies; zero dominates the product")
    return {"bindings": bindings,
            "applicable_planets": sorted(bindings),
            "exact_bindings": sorted(p for p, e in bindings.items()
                                     if e["multiplier_exact"]),
            "inexact_bindings": sorted(p for p, e in bindings.items()
                                       if not e["multiplier_exact"])}


# ─────────────────────────────────────────────────────────────────────────────
# THE EVALUATORS
# ─────────────────────────────────────────────────────────────────────────────

TIMING_RULES = {"D5_TIM_01": evaluate_tim_01, "D5_TIM_02": evaluate_tim_02,
                "D5_TIM_03": evaluate_tim_03}
TRIANGULATION_RULES = {"D5_TRI_01": evaluate_tri_01,
                       "D5_TRI_02": evaluate_tri_02,
                       "D5_TRI_03": evaluate_tri_03}


def evaluate_timing(facts: Dict[str, Any], doctrine: D5Doctrine,
                    rules_doctrine: D5RulesDoctrine,
                    inputs: TemporalInputs,
                    rule_inputs: Optional[D5RuleInputs] = None
                    ) -> Dict[str, RuleOutcome]:
    ctx = Ctx(facts, doctrine, rules_doctrine, rule_inputs)
    return {rid: fn(ctx, inputs) for rid, fn in TIMING_RULES.items()}


def evaluate_triangulation(facts: Dict[str, Any], doctrine: D5Doctrine,
                           rules_doctrine: D5RulesDoctrine,
                           inputs: TemporalInputs,
                           rule_inputs: Optional[D5RuleInputs] = None
                           ) -> Dict[str, RuleOutcome]:
    """`rule_inputs` carries the certified combustion fact TRI_03's Well_Placed
    reading needs. Absent, combustion is UNKNOWN — never False."""
    ctx = Ctx(facts, doctrine, rules_doctrine, rule_inputs)
    return {rid: fn(ctx, inputs) for rid, fn in TRIANGULATION_RULES.items()}


# ─────────────────────────────────────────────────────────────────────────────
# SCORE READINESS
# ─────────────────────────────────────────────────────────────────────────────

#: Weight-zero rules do not change a sum, so an UNRESOLVED one is arithmetically
#: harmless — UNLESS it controls a multiplier or an override, in which case its
#: absence changes the result without changing the addend. No static rule
#: currently does, and the set is empty rather than assumed away, so a later
#: ticket that makes one load-bearing has a place to say so.
OVERRIDE_CONTROLLING_RULE_IDS: FrozenSet[str] = frozenset()


def assess_score_readiness(static_outcomes: Mapping[str, RuleOutcome],
                           timing_outcomes: Mapping[str, RuleOutcome],
                           triangulation_outcomes: Mapping[str, RuleOutcome],
                           ) -> Dict[str, Any]:
    """Can a single EXACT Final Score be computed without guessing?

    THE TWO POLICIES THAT DECIDE THIS:
      * an UNRESOLVED weighted rule is NOT zero;
      * an UNRESOLVED multiplier is NOT 1.0.

    Either substitution would produce a number that looks exact, and downstream
    nothing could tell it from a real one. So any unresolved information that
    could move the total makes `exact_score_ready` False. Returning False here is
    an honest verdict about the doctrine, not a defect in this layer.
    """
    blocking_rule_ids: List[str] = []
    non_blocking_zero_weight: List[str] = []
    blocking_primitives: set = set()

    for outcomes in (static_outcomes, timing_outcomes):
        for rule_id, outcome in outcomes.items():
            if outcome.status != UNRESOLVED:
                continue
            if outcome.base_weight == 0 and rule_id not in OVERRIDE_CONTROLLING_RULE_IDS:
                non_blocking_zero_weight.append(rule_id)
                continue
            blocking_rule_ids.append(rule_id)
            blocking_primitives.update(outcome.unresolved_primitives)

    blocking_tri_rules: List[str] = []
    for rule_id, outcome in triangulation_outcomes.items():
        if outcome.status == UNRESOLVED:
            blocking_tri_rules.append(rule_id)
            blocking_primitives.update(outcome.unresolved_primitives)

    binding_report = build_tri_bindings(triangulation_outcomes)
    inexact = binding_report["inexact_bindings"]

    # D5-006 §8 · A GENUINELY INEXACT BINDING BLOCKS THE SCORE. A TRI rule can
    # be FIRED overall while one physical binding is still unresolved — the AK
    # resolves, the AMK does not — and that unresolved per-planet multiplier can
    # still move a later Effective Weight. Readiness must not ignore it.
    notes: List[str] = []
    if inexact:
        notes.append("triangulation bindings with an unresolved multiplier: "
                     + ", ".join(inexact))
    if blocking_rule_ids:
        notes.append(f"{len(blocking_rule_ids)} weighted rule(s) are UNRESOLVED; "
                     "an unresolved weighted rule is not zero")
    if blocking_tri_rules:
        notes.append(f"{len(blocking_tri_rules)} triangulation rule(s) are "
                     "UNRESOLVED; an unresolved multiplier is not 1.0")
    if non_blocking_zero_weight:
        notes.append("UNRESOLVED but weight 0, so arithmetically inert: "
                     + ", ".join(sorted(non_blocking_zero_weight)))
    if not blocking_rule_ids and not blocking_tri_rules and not inexact:
        notes.append("every weighted rule and every triangulation multiplier is "
                     "resolved")

    return {
        "exact_score_ready": (not blocking_rule_ids and not blocking_tri_rules
                              and not inexact),
        "blocking_rule_ids": sorted(blocking_rule_ids),
        "blocking_primitives": sorted(blocking_primitives),
        "blocking_tri_rules": sorted(blocking_tri_rules),
        "non_blocking_zero_weight_rule_ids": sorted(non_blocking_zero_weight),
        "triangulation_bindings": binding_report,
        "notes": notes,
    }
