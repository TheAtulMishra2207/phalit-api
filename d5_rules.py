"""
d5_rules.py — D5-003 · THE 67-RULE STATIC EVALUATOR.

WHAT THIS DOES. Each of the 67 static rules is evaluated to exactly one of
FIRED / NOT_FIRED / UNRESOLVED against the D5-001 fact dictionary. Nothing is
scored, weighted, summed, tiered or narrated: `base_weight` is carried through
from the workbook as metadata and is never arithmetic here.

THREE-VALUED LOGIC IS THE POINT. Four operator families have no certified
primitive (see D5-002-PRIMITIVE-INVENTORY.md), so their operands evaluate to
UNKNOWN rather than to a guessed boolean. `t_or` and `t_and` then extract every
conclusion that is still logically determined:

    TRUE  OR  UNKNOWN -> TRUE      (one branch already established truth)
    FALSE OR  UNKNOWN -> UNKNOWN
    FALSE AND UNKNOWN -> FALSE     (already impossible)
    TRUE  AND UNKNOWN -> UNKNOWN

An unresolved primitive therefore never contaminates a rule whose result is
already decided, and never lets an undecided rule be reported as NOT_FIRED.

NO PREDICATE IS REDEFINED HERE. Conjunction, graha-dṛṣṭi, mutual aspect, sign
exchange, house lordship, Kendra/Trikona scope, Vargottama, the Jaimini geometry
and the barren signs all come from `d5_predicates`. This module composes them
and holds the rule table.

TICKET §8 OVERRIDES THE WORKBOOK IN FOUR PLACES. Where the D5-003 ticket's
locked normalisation and the workbook's Logic Condition column disagree, the
ticket wins, because §8 says to preserve the Founder locks already encoded in
D5-002 exactly. Every divergence is named at its rule and listed in
D5-003-RULE-COVERAGE.md rather than silently reconciled.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import (Any, Callable, Dict, FrozenSet, List, Mapping,
                    Optional, Sequence, Set, Tuple)

import d5_predicates as P
from d5_engine import D5Doctrine, D5DomainError

# ─────────────────────────────────────────────────────────────────────────────
# THREE-VALUED LOGIC
# ─────────────────────────────────────────────────────────────────────────────

TRUE, FALSE, UNKNOWN = True, False, None

FIRED, NOT_FIRED, UNRESOLVED = "FIRED", "NOT_FIRED", "UNRESOLVED"

_STATUS = {TRUE: FIRED, FALSE: NOT_FIRED}


def t_or(*values: Optional[bool]) -> Optional[bool]:
    """TRUE dominates; UNKNOWN otherwise survives; all-FALSE is FALSE."""
    if any(v is TRUE for v in values):
        return TRUE
    if any(v is UNKNOWN for v in values):
        return UNKNOWN
    return FALSE


def t_and(*values: Optional[bool]) -> Optional[bool]:
    """FALSE dominates; UNKNOWN otherwise survives; all-TRUE is TRUE."""
    if any(v is FALSE for v in values):
        return FALSE
    if any(v is UNKNOWN for v in values):
        return UNKNOWN
    return TRUE


def t_not(value: Optional[bool]) -> Optional[bool]:
    return UNKNOWN if value is UNKNOWN else (not value)


def status_of(value: Optional[bool]) -> str:
    return _STATUS.get(value, UNRESOLVED)


# ─────────────────────────────────────────────────────────────────────────────
# THE MANIFEST — polarity and base weight, transcribed from the workbook
# ─────────────────────────────────────────────────────────────────────────────

#: (polarity, base_weight) for all 67 static rules, from
#: D5_Panchamansha_Rules_Matrix.xlsx, sheet "D-5 Rules Matrix Master".
#: The static universe is the workbook's 80 rules less CALC (4), APP (3),
#: TIM (3) and TRI (3), which is exactly 67.
RULE_META: Dict[str, Tuple[str, float]] = {
    "D5_ANAL_01": ("Positive", 1.5), "D5_ANAL_02": ("Positive", 2),
    "D5_ANAL_03": ("Positive", 2), "D5_ANAL_04": ("Positive", 1.5),
    "D5_ANAL_05": ("Positive", 1), "D5_ANAL_06": ("Positive", 1.5),
    "D5_ANAL_07": ("Positive", 1.5), "D5_ANAL_08": ("Positive", 1.5),
    "D5_PAR_01": ("Positive", 2), "D5_PAR_02": ("Positive", 2),
    "D5_PAR_03": ("Positive", 2), "D5_PAR_04": ("Positive", 1.5),
    "D5_PAR_05": ("Positive", 1.5), "D5_PAR_06": ("Positive", 1.5),
    "D5_PAR_07": ("Positive", 2), "D5_PAR_08": ("Positive", 1.5),
    "D5_PAR_09": ("Positive", 2), "D5_PAR_10": ("Positive", 2),
    "D5_PAR_11": ("Positive", 1.5), "D5_PAR_12": ("Positive", 2),
    "D5_PAR_13": ("Positive", 1.5), "D5_PAR_14": ("Neutral", 0),
    "D5_PAR_15": ("Positive", 2), "D5_PAR_16": ("Positive", 2),
    "D5_PAR_17": ("Negative", -1.5), "D5_PAR_18": ("Negative", -1.5),
    "D5_JAI_01": ("Positive", 2), "D5_JAI_02": ("Positive", 1.5),
    "D5_JAI_03": ("Positive", 2), "D5_JAI_04": ("Positive", 1.5),
    "D5_JAI_05": ("Positive", 1.5), "D5_JAI_06": ("Positive", 1.5),
    "D5_JAI_07": ("Positive", 2), "D5_JAI_08": ("Positive", 1.5),
    "D5_JAI_09": ("Positive", 1.5), "D5_JAI_10": ("Positive", 1.5),
    "D5_JAI_11": ("Positive", 2), "D5_JAI_12": ("Positive", 1.5),
    "D5_JAI_13": ("Positive", 1.5), "D5_JAI_14": ("Positive", 2),
    "D5_JAI_15": ("Positive", 2), "D5_JAI_16": ("Neutral", 0),
    "D5_JAI_17": ("Neutral", 0), "D5_JAI_18": ("Positive", 2),
    "D5_TAJ_01": ("Positive", 1), "D5_TAJ_02": ("Positive", 1),
    "D5_TAJ_03": ("Positive", 1), "D5_TAJ_04": ("Positive", 1),
    "D5_TAJ_05": ("Positive", 1), "D5_TAJ_06": ("Positive", 1),
    "D5_TAJ_07": ("Positive", 1), "D5_TAJ_08": ("Positive", 1),
    "D5_TAJ_09": ("Positive", 1), "D5_TAJ_10": ("Positive", 1),
    "D5_TAJ_11": ("Positive", 1),
    "D5_MISC_01": ("Positive", 1.5), "D5_MISC_02": ("Positive", 1.5),
    "D5_CLA_01": ("Positive", 1.5), "D5_CLA_02": ("Negative", -1),
    "D5_CLA_03": ("Positive", 1.5), "D5_CLA_04": ("Neutral", 0),
    "D5_AFF_01": ("Negative", -1.5), "D5_AFF_02": ("Negative", -1.5),
    "D5_AFF_03": ("Negative", -1.5), "D5_AFF_04": ("Negative", -2),
    "D5_AFF_05": ("Negative", -1.5), "D5_AFF_06": ("Neutral", 0),
}

# ─────────────────────────────────────────────────────────────────────────────
# UNRESOLVED-INPUT VOCABULARY
# ─────────────────────────────────────────────────────────────────────────────
#
# D5-005 CLOSED THE FOUR D5-002 DOCTRINE GAPS. `Association`, `Rashi_Drishti`,
# `Strong/Well_Placed` and `Benefic/Malefic` are no longer unresolved primitives
# and no rule may report them as such — the Founder locks made all four
# deterministic. What remains unresolved is of two kinds only:
#
#   * OPERATIONAL — a certified physical fact nobody has supplied yet. These
#     resolve by wiring, not by doctrine.
#   * RESIDUAL OPERAND BINDING — a workbook expression whose operand is not a
#     planet-to-planet primitive and for which no accepted mechanical binding
#     exists in the product. See D5-005-CLOSURE.md.

#: OPERATIONAL — certified facts the caller supplies.
CERTIFIED_TITHI = "Certified_Moon_Tithi"
CERTIFIED_COMBUSTION = "Certified_Combustion_Fact"

# D5-006 CLOSED THE LAST THREE RESIDUAL OPERAND BINDINGS. The house qualifier
# for ANAL_02/04, "D5_11H Strong" for CLA_03 and "Connected to a house" for
# TRI_03 are all Founder-locked now, so no residual-binding name survives in the
# production vocabulary. Everything still capable of UNRESOLVED is a certified
# OPERATIONAL fact and nothing else.


@dataclass(frozen=True)
class D5RuleInputs:
    """Certified OPERATIONAL facts the rule layer consumes but never derives.

    `None` means NOT SUPPLIED, exactly as in `TemporalInputs`. A missing fact
    propagates as UNKNOWN through the three-valued operators and can still be
    dominated by an already-decided branch, but is never read as False.

    Birth Tithi is NOT computed here and combustion is NOT computed here. Both
    are certified astronomical facts injected by the caller; D5-005 does not
    wire them from `main.py`.
    """
    #: Certified Tithi, 1..30. Founder bright-Moon interval is 11..20 inclusive
    #: (Shukla Ekadashi through Krishna Panchami).
    moon_tithi: Optional[int] = None
    #: {graha: bool} certified combustion, per physical planet.
    combust_by_graha: Optional[Mapping[str, bool]] = None


#: Founder bright-Moon interval, inclusive, in certified Tithi numbering.
BRIGHT_MOON_TITHI = (11, 20)

#: LOCK 4 · the fixed halves of the natural classification.
ALWAYS_BENEFIC: FrozenSet[str] = frozenset({"Jupiter", "Venus"})
ALWAYS_MALEFIC: FrozenSet[str] = frozenset({"Sun", "Mars", "Saturn",
                                            "Rahu", "Ketu"})


@dataclass(frozen=True)
class D5RulesDoctrine:
    """Doctrine D5-003 needs that the accepted D5-001 `D5Doctrine` does not
    carry.

    INJECTED, NOT RESTATED. `exaltation_sign` is the product's one accepted
    table — the same object `main.py` already passes to `configure_d4_doctrine`.
    Own-sign needs no table at all: it is `sign_lords[si] == planet`, read from
    the D5-001 doctrine.

    `d5_engine.D5Doctrine` is a frozen D5-001 product file and `main.py` is not
    authorised in D5-003, so the exaltation table is carried here rather than
    added there. Wiring it in `main.py` belongs to whichever ticket next touches
    that file.
    """
    exaltation_sign: Mapping[str, int]

    def __post_init__(self) -> None:
        if not self.exaltation_sign:
            raise D5DomainError("exaltation table is empty")


# ─────────────────────────────────────────────────────────────────────────────
# EVALUATION CONTEXT
# ─────────────────────────────────────────────────────────────────────────────

class Ctx:
    """Read-only accessors over the D5-001 fact dictionary.

    Every value comes from `build_d5_facts`. Nothing is recomputed: the D5 signs,
    houses, tattvas, Chara Karakas and Karakamsha reference are all already
    certified by D5-001, and re-deriving any of them here would create a second
    answer that could disagree with the one the reader was shown.
    """

    def __init__(self, facts: Dict[str, Any], doctrine: D5Doctrine,
                 rules_doctrine: D5RulesDoctrine,
                 inputs: "Optional[D5RuleInputs]" = None) -> None:
        self.facts = facts
        self.doctrine = doctrine
        self.rules = rules_doctrine
        #: Callers written before D5-005 pass no inputs. They keep working:
        #: an empty input set simply leaves the operational facts unsupplied,
        #: which the three-valued operators handle as UNKNOWN.
        self.inputs = inputs if inputs is not None else D5RuleInputs()
        self.lagna = facts["lagna"]
        self.grahas = facts["grahas"]
        self.d5_lagna_si = self.lagna["d5_sign_index"]
        self.d1_lagna_si = self.lagna["source_sign_index"]
        self.karakas = facts["chara_karakas"]["assignments"]
        self.karakamsha = facts["karakamsha"]

    # ── D5 positions ────────────────────────────────────────────────────────
    def d5_house(self, graha: str) -> int:
        return self.grahas[graha]["d5_house"]

    def d5_sign(self, graha: str) -> int:
        return self.grahas[graha]["d5_sign_index"]

    def tattva(self, graha: str) -> str:
        return self.grahas[graha]["tattva"]

    def occupants_of_d5_house(self, house: int) -> List[str]:
        return [g for g in self.grahas if self.d5_house(g) == house]

    # ── D1 positions ────────────────────────────────────────────────────────
    def d1_house(self, graha: str) -> int:
        return ((self.grahas[graha]["source_sign_index"] - self.d1_lagna_si) % 12) + 1

    def d1_sign(self, graha: str) -> int:
        return self.grahas[graha]["source_sign_index"]

    # ── lords ───────────────────────────────────────────────────────────────
    def d5_lord(self, n: int) -> str:
        return P.d5_house_lord(self.d5_lagna_si, n, self.doctrine)

    def d1_lord(self, n: int) -> str:
        return P.d1_house_lord(self.d1_lagna_si, n, self.doctrine)

    # ── karakas ─────────────────────────────────────────────────────────────
    def karaka(self, name: str) -> str:
        return self.karakas[name]["planet"]

    # ── dignity, per §9: only Exalted, Own Sign and D1-D5 Vargottama ────────
    def is_exalted_in_d5(self, graha: str) -> bool:
        return self.rules.exaltation_sign.get(graha) == self.d5_sign(graha)

    def is_own_sign_in_d5(self, graha: str) -> bool:
        return self.doctrine.sign_lords[self.d5_sign(graha)] == graha

    def is_vargottama_d1_d5(self, graha: str) -> bool:
        return P.is_d1_d5_vargottama(self.d1_sign(graha), self.d5_sign(graha))

    # ── the D5-001 key-planet roles, de-duplicated by physical graha ────────
    def key_planet_roles(self) -> Dict[str, str]:
        return {
            "d5_lagna_lord": self.d5_lord(1),
            "d1_fifth_lord": self.facts["d1_fifth_lord_mirroring"]["planet"],
            "sun": "Sun",
            "jupiter": "Jupiter",
            "atmakaraka": self.karaka("AK"),
        }

    # ── LOCK 1 · Association, one call ──────────────────────────────────────
    def associated(self, a: str, b: str) -> bool:
        """The canonical Association predicate over two grahas' D5 positions."""
        return P.associated(a, self.d5_sign(a), self.d5_house(a),
                            b, self.d5_sign(b), self.d5_house(b), self.doctrine)

    def rashi_drishti(self, a: str, b: str) -> bool:
        return P.rashi_drishti(self.d5_sign(a), self.d5_sign(b))

    def combust(self, graha: str) -> Optional[bool]:
        """Certified combustion, three-valued. Absent means UNKNOWN."""
        table = self.inputs.combust_by_graha
        if table is None or graha not in table:
            return UNKNOWN
        return bool(table[graha])

    # ── LOCK 3 · Strong / Well-Placed ───────────────────────────────────────
    def strong(self, graha: str, sign_index: int, house: int,
               vargottama: bool) -> Tuple[Optional[bool], Dict[str, Any]]:
        """(Exalted OR Own OR Moolatrikona OR Vargottama) AND NOT (Combust OR
        Debilitated OR 6/8/12).

        THE CHART PAIR IS THE CALLER'S. `vargottama` is passed in, so a D5
        reading passes D1-D5 and TRI_03 passes D1-D9. Nothing here chooses.

        Combustion is the only three-valued operand, and it only matters when
        everything else has already passed: a false positive side, or a
        debilitation, or a dusthana, decides the answer without it.
        """
        positive = P.positive_dignity(graha, sign_index, vargottama,
                                      self.doctrine, self.rules.exaltation_sign)
        negative = P.deterministic_negative_placement(
            graha, sign_index, house, self.rules.exaltation_sign)
        combust = self.combust(graha)
        value = t_and(any(positive.values()),
                      t_not(t_or(combust, negative["debilitated"],
                                 negative["dusthana"])))
        evidence = {"graha": graha, "sign_index": sign_index, "house": house,
                    "positive_dignity": positive,
                    "debilitated": negative["debilitated"],
                    "in_dusthana": negative["dusthana"],
                    "combust": "unresolved" if combust is UNKNOWN else combust}
        return value, evidence

    def strong_in_d5(self, graha: str) -> Tuple[Optional[bool], Dict[str, Any]]:
        return self.strong(graha, self.d5_sign(graha), self.d5_house(graha),
                           self.is_vargottama_d1_d5(graha))

    # ── LOCK 4 · natural benefic / malefic ──────────────────────────────────
    def natural_benefic(self, graha: str) -> Tuple[Optional[bool], Dict[str, Any]]:
        """TRUE benefic · FALSE malefic · UNKNOWN only for a Moon with no Tithi.

        Mercury is BINARY once D5 placements are known, because Association is
        now locked: benefic exactly when it is associated with none of the five
        natural malefics. Nothing about Mercury is unresolved.
        """
        if graha in ALWAYS_BENEFIC:
            return TRUE, {"graha": graha, "basis": "always benefic"}
        if graha in ALWAYS_MALEFIC:
            return FALSE, {"graha": graha, "basis": "always malefic"}
        if graha == "Moon":
            tithi = self.inputs.moon_tithi
            if tithi is None:
                return UNKNOWN, {"graha": graha, "basis": "tithi",
                                 "moon_tithi": "unresolved"}
            low, high = BRIGHT_MOON_TITHI
            return (low <= tithi <= high), {"graha": graha, "basis": "tithi",
                                            "moon_tithi": tithi,
                                            "bright_interval": [low, high]}
        if graha == "Mercury":
            partners = sorted(g for g in ALWAYS_MALEFIC
                              if g in self.grahas and self.associated("Mercury", g))
            return (not partners), {"graha": graha, "basis": "association",
                                    "associated_malefics": partners}
        return UNKNOWN, {"graha": graha, "basis": "unclassified"}

    def natural_malefic(self, graha: str) -> Tuple[Optional[bool], Dict[str, Any]]:
        value, evidence = self.natural_benefic(graha)
        return t_not(value), evidence


@dataclass
class RuleOutcome:
    rule_id: str
    status: str
    polarity: str
    base_weight: float
    evidence: Dict[str, Any]
    unresolved_primitives: List[str]


# ─────────────────────────────────────────────────────────────────────────────
# SHARED SHAPES
# ─────────────────────────────────────────────────────────────────────────────

def _in_houses(ctx: Ctx, graha: str, houses: Sequence[int]) -> bool:
    return ctx.d5_house(graha) in houses


def _any_in_houses(ctx: Ctx, grahas: Sequence[str],
                   houses: Sequence[int]) -> Tuple[bool, List[str]]:
    """The grahas satisfying the placement, DE-DUPLICATED by physical body.

    Where two roles resolve to one graha, it appears once — a single body cannot
    contribute twice to a rule's triangulation product.
    """
    hits = sorted({g for g in grahas if _in_houses(ctx, g, houses)})
    return bool(hits), hits


def _both_lords_in_house(ctx: Ctx, a: str, b: str, house: int
                         ) -> Tuple[bool, Dict[str, Any]]:
    """D5-006 §3 · FINAL LOCK. "A associated with B in house H" means A AND B
    physically occupy H together.

    So the operative condition is a conjunction of two DISTINCT physical grahas
    inside the named D5 house. The wider Lock 1 Association branches do not
    independently satisfy these two rules: a mutual aspect or a sign exchange
    puts the two bodies in different houses by construction, and neither places
    the pair "in house H".

    A graha that owns both relevant houses cannot conjunct itself, so the
    identity case is FALSE — one body is not two.

    There is NO unresolved path left here.
    """
    distinct = a != b
    house_a, house_b = ctx.d5_house(a), ctx.d5_house(b)
    both_in = house_a == house and house_b == house
    value = bool(distinct and both_in)
    evidence = {"required_house": house, "distinct_grahas": distinct,
                "first_in_required_house": house_a == house,
                "second_in_required_house": house_b == house,
                "both_in_required_house": both_in,
                # Recorded for audit only — these branches no longer decide the
                # rule, and a reader should be able to see that they did not.
                "association_branches_not_operative": {
                    "conjunct": P.conjunct(ctx.d5_sign(a), ctx.d5_sign(b)) if distinct else False,
                    "mutual_aspect": P.mutual_graha_aspect(a, house_a, b, house_b) if distinct else False,
                    "sign_exchange": P.sign_exchange(a, ctx.d5_sign(a), b,
                                                     ctx.d5_sign(b), ctx.doctrine)}}
    return value, evidence


def _anal_01(ctx):
    l9 = ctx.d5_lord(9)
    asp = P.graha_aspects_house(l9, ctx.d5_house(l9), 1)
    ketu = ctx.d5_house("Ketu") == 9
    value = t_and(asp, ketu)
    # Both conjuncts must hold, so both bodies establish the fired condition.
    parts = sorted({l9, "Ketu"}) if value is TRUE else []
    return value, {"d5_9L": l9, "d5_9L_house": ctx.d5_house(l9),
                   "aspects_lagna": asp, "ketu_house": ctx.d5_house("Ketu"),
                   "participants": parts}, []


def _anal_02(ctx):
    a, b = ctx.d5_lord(1), ctx.d5_lord(9)
    value, detail = _both_lords_in_house(ctx, a, b, 5)
    ev = {"d5_1L": a, "d5_1L_house": ctx.d5_house(a),
          "d5_9L": b, "d5_9L_house": ctx.d5_house(b),
          "same_graha_rules_both": a == b,
          "participants": sorted({a, b}) if value else [], **detail}
    return value, ev, []


def _anal_03(ctx):
    l1, l9 = ctx.d5_lord(1), ctx.d5_lord(9)
    occ = ctx.d5_house(l1) == 5
    asp = P.graha_aspects_house(l9, ctx.d5_house(l9), 11)
    value = t_and(occ, asp)
    # An AND, so both lords participate — de-duplicated where one graha rules
    # both the 1st and the 9th.
    parts = sorted({l1, l9}) if value is TRUE else []
    return value, {"d5_1L": l1, "d5_1L_house": ctx.d5_house(l1),
                   "d5_9L": l9, "d5_9L_house": ctx.d5_house(l9),
                   "aspects_11H": asp, "same_graha_rules_both": l1 == l9,
                   "participants": parts}, []


def _anal_04(ctx):
    a, b = ctx.d5_lord(5), ctx.d5_lord(2)
    value, detail = _both_lords_in_house(ctx, a, b, 8)
    ev = {"d5_5L": a, "d5_5L_house": ctx.d5_house(a),
          "d5_2L": b, "d5_2L_house": ctx.d5_house(b),
          "same_graha_rules_both": a == b,
          "participants": sorted({a, b}) if value else [], **detail}
    return value, ev, []


def _anal_05(ctx):
    """TICKET §8 LOCK, overriding the workbook's "associated".

    Both lords conjunct in H4, then either aspecting H10. The aspect clause is
    redundant under the universal 7th — H10 is the seventh from H4 — and §8
    directs that it be kept exactly as written rather than repaired.

    D5-007-CORR-01A · PARTICIPANTS. Both lords establish the fired condition, so
    both are published. A same-physical-graha case cannot satisfy the required
    conjunction — one body is not two — so a FIRED case always carries exactly
    two distinct bodies, and the de-duplication is belt-and-braces rather than
    load-bearing.
    """
    l11, l8 = ctx.d5_lord(11), ctx.d5_lord(8)
    h11, h8 = ctx.d5_house(l11), ctx.d5_house(l8)
    if l11 == l8:
        return FALSE, {"d5_11L": l11, "d5_8L": l8, "same_graha_rules_both": True,
                       "participants": [],
                       "note": "one graha cannot be conjunct with itself"}, []
    value = P.anal_05(h11, h8, l11, l8)
    return value, {"d5_11L": l11, "d5_11L_house": h11, "d5_8L": l8,
                   "d5_8L_house": h8, "required_conjunction_house": 4,
                   "aspect_target": 10,
                   "participants": sorted({l11, l8}) if value else []}, []


def _anal_06(ctx):
    """TICKET §8 LOCK. Either the 3rd or the 12th lord; one graha owning both
    counts once.

    PARTICIPANTS FOLLOW THE ACTUAL FIRING BRANCH. A 3L/12L alternative that did
    not satisfy the H9 condition is NOT a participant, even though the rule
    named it as a candidate. The verdict still comes from the single accepted
    `P.anal_06` predicate — only the branch attribution is computed here.
    """
    l3, l12, l9 = ctx.d5_lord(3), ctx.d5_lord(12), ctx.d5_lord(9)
    h3, h12, h9 = ctx.d5_house(l3), ctx.d5_house(l12), ctx.d5_house(l9)
    ketu_house = ctx.d5_house("Ketu")
    value = P.anal_06(l3, h3, l12, h12, ketu_house, l9, h9)
    # De-duplicate by physical graha before asking which candidate qualified.
    candidates = []
    for graha, house, role in ((l3, h3, "d5_3L"), (l12, h12, "d5_12L")):
        if (graha, house) not in [(c["graha"], c["house"]) for c in candidates]:
            candidates.append({"graha": graha, "house": house, "role": role,
                               "qualified": house == 9 and ketu_house == 9})
        else:
            for c in candidates:
                if c["graha"] == graha:
                    c["role"] += "+" + role
    qualifying = [c["graha"] for c in candidates if c["qualified"]]
    parts = sorted(set(qualifying) | {"Ketu", l9}) if value is TRUE else []
    return value, {"d5_3L": l3, "d5_3L_house": h3,
                   "d5_12L": l12, "d5_12L_house": h12,
                   "same_graha_rules_both": l3 == l12,
                   "ketu_house": ketu_house, "d5_9L": l9, "d5_9L_house": h9,
                   "candidates": candidates, "qualifying_lords": qualifying,
                   "participants": parts}, []


def _anal_07(ctx):
    """No house is named, so the rule is purely an Association claim — and
    Association is now locked, which makes it fully deterministic."""
    a = ctx.facts["d1_fifth_lord_mirroring"]["planet"]
    b = ctx.d5_lord(1)
    value = ctx.associated(a, b) if a != b else False
    return value, {"d1_5L": a, "d1_5L_d5_house": ctx.d5_house(a),
                   "d5_1L": b, "d5_1L_d5_house": ctx.d5_house(b),
                   "same_graha": a == b,
                   "participants": [a, b] if value else []}, []


def _anal_08(ctx):
    l5 = ctx.d5_lord(5)
    l11_d1 = ctx.d1_lord(11)
    in10 = ctx.d1_house(l5) == 10
    target_in_1 = ctx.d1_house(l11_d1) == 1
    asp = P.graha_aspects_house(l5, ctx.d1_house(l5), 1)
    value = t_and(in10, target_in_1, asp)
    parts = sorted({l5, l11_d1}) if value is TRUE else []
    return value, {
        "d5_5L": l5, "d5_5L_d1_house": ctx.d1_house(l5),
        "d1_11L": l11_d1, "d1_11L_d1_house": ctx.d1_house(l11_d1),
        "same_graha_fills_both": l5 == l11_d1,
        "aspects_d1_1H": asp, "participants": parts}, []


def _par_01(ctx):
    l = ctx.facts["d1_fifth_lord_mirroring"]["planet"]
    h = ctx.d5_house(l)
    hit = h in (1, 5, 9, 10)
    return hit, {"d1_5L": l, "d5_house": h, "qualifying_houses": [1, 5, 9, 10],
                 "participants": [l] if hit else []}, []


def _par_scope(ctx, primary: int, alternatives: Sequence[int]):
    """Shared PAR_02 / PAR_12 mechanics. §8: the conjunction branch needs the
    SHARED house in {1,4,5,7,9,10}; the aspect branch needs BOTH grahas
    individually in it.

    PARTICIPANTS ARE THE ACTUAL FIRED ALTERNATIVE ONLY. Where 1L qualifies with
    the 10th lord and not the 5th, the 5th lord is NOT a participant — it sits
    in an alternative that did not fire.
    """
    a = ctx.d5_lord(primary)
    branches = []
    fired = FALSE
    parts: List[str] = []
    for n in alternatives:
        b = ctx.d5_lord(n)
        ha, hb = ctx.d5_house(a), ctx.d5_house(b)
        same = (a == b)
        conj = FALSE if same else P.conjunction_in_kendra_trikona(ha, hb)
        asp = FALSE if same else P.aspect_with_both_in_kendra_trikona(a, ha, b, hb)
        branches.append({"other_lord_house": n, "other_lord": b,
                         "other_lord_d5_house": hb, "same_graha": same,
                         "conjunction_in_scope": conj, "aspect_in_scope": asp})
        if conj or asp:
            parts.extend([a, b])
        fired = t_or(fired, conj, asp)
    return fired, {"primary_lord": a, "primary_lord_d5_house": ctx.d5_house(a),
                   "scope": sorted(P.KENDRA_TRIKONA), "branches": branches,
                   "participants": sorted(set(parts))}, []


def _par_02(ctx):
    return _par_scope(ctx, 1, (10, 5))


def _par_12(ctx):
    return _par_scope(ctx, 1, (5, 7))


def _par_03(ctx):
    """§9: Exalted, Own Sign and D1-D5 Vargottama are named relations and are
    evaluated exactly. They are NOT read as a generic Strong.

    Only a candidate whose OWN branch fired is a participant.
    """
    hits = []
    for graha in ("Sun", "Jupiter"):
        rel = {"exalted": ctx.is_exalted_in_d5(graha),
               "own_sign": ctx.is_own_sign_in_d5(graha),
               "vargottama_d1_d5": ctx.is_vargottama_d1_d5(graha)}
        if any(rel.values()):
            hits.append({"graha": graha, "d5_sign_index": ctx.d5_sign(graha), **rel})
    return bool(hits), {"qualifying": hits, "candidates": ["Sun", "Jupiter"],
                        "participants": [h["graha"] for h in hits]}, []


def _planet_in_house(ctx, graha: str, house: int):
    h = ctx.d5_house(graha)
    hit = (h == house)
    return hit, {"graha": graha, "d5_house": h, "required_house": house,
                 "participants": [graha] if hit else []}, []


def _par_04(ctx):
    return _planet_in_house(ctx, "Sun", 10)


def _par_05(ctx):
    return _planet_in_house(ctx, "Mars", 10)


def _par_06(ctx):
    return _planet_in_house(ctx, "Saturn", 10)


def _par_07(ctx):
    """D1 9L or D1 5L in D5 H1, H5 or H9.

    `qualifying_houses_hit` records WHICH of the three houses the qualifying
    participants actually occupy. Two participants can establish two different
    houses at once, and a later attribution layer must be able to see both
    without re-deriving them.
    """
    cands = [ctx.d1_lord(9), ctx.d1_lord(5)]
    ok, hits = _any_in_houses(ctx, cands, (1, 5, 9))
    return ok, {"d1_9L": cands[0], "d1_5L": cands[1],
                "d5_houses": {g: ctx.d5_house(g) for g in set(cands)},
                "qualifying": hits, "participants": sorted(set(hits)),
                "qualifying_houses_hit": sorted({ctx.d5_house(g) for g in hits})}, []


def _par_08(ctx):
    """Exalted OR Strongly_Placed. Strong is now Founder-locked, so the only
    thing that can leave this unresolved is a MISSING CERTIFIED COMBUSTION
    FACT — an operational input, not a doctrine gap."""
    l5 = ctx.d5_lord(5)
    exalted = ctx.is_exalted_in_d5(l5)
    strong, detail = ctx.strong_in_d5(l5)
    value = t_or(exalted, strong)
    return value, {"d5_5L": l5, "d5_sign_index": ctx.d5_sign(l5),
                   "exalted": exalted,
                   "strong": "unresolved" if strong is UNKNOWN else strong,
                   "strong_detail": detail,
                   "participants": [l5] if value is TRUE else []}, \
        ([CERTIFIED_COMBUSTION] if value is UNKNOWN else [])


def _par_09(ctx):
    h = ctx.d5_house("Jupiter")
    hit = h in (1, 5, 9)
    return hit, {"graha": "Jupiter", "d5_house": h,
                 "qualifying_houses": [1, 5, 9],
                 "participants": ["Jupiter"] if hit else []}, []


def _par_10(ctx):
    """The workbook says "5L Vargottama" with target chart "D-1 / D-5". Read as
    the D1 fifth lord, which is the 5L the D5-001 facts already resolve."""
    l = ctx.facts["d1_fifth_lord_mirroring"]["planet"]
    v = ctx.is_vargottama_d1_d5(l)
    return v, {"d1_5L": l, "d1_sign_index": ctx.d1_sign(l),
               "d5_sign_index": ctx.d5_sign(l), "vargottama_d1_d5": v,
               "participants": [l] if v else []}, []


def _par_11(ctx):
    conj = P.conjunct(ctx.d5_sign("Venus"), ctx.d5_sign("Mars"))
    mutual = P.mutual_graha_aspect("Venus", ctx.d5_house("Venus"),
                                   "Mars", ctx.d5_house("Mars"))
    exch = P.sign_exchange("Venus", ctx.d5_sign("Venus"),
                           "Mars", ctx.d5_sign("Mars"), ctx.doctrine)
    hit = bool(conj or mutual or exch)
    return hit, {
        "venus_d5_house": ctx.d5_house("Venus"), "mars_d5_house": ctx.d5_house("Mars"),
        "conjunct": conj, "mutual_aspect": mutual, "sign_exchange": exch,
        "participants": ["Venus", "Mars"] if hit else []}, []


def _par_13(ctx):
    cands = [ctx.d1_lord(7), "Venus"]
    ok, hits = _any_in_houses(ctx, cands, (5,))
    return ok, {"d1_7L": cands[0], "d5_houses": {g: ctx.d5_house(g) for g in set(cands)},
                "qualifying": hits, "required_house": 5,
                "participants": sorted(set(hits))}, []


def _par_14(ctx):
    """TICKET §8 LOCK, three branches — and the third is now REAL.

    Rāśi-dṛṣṭi is locked, so the branch the workbook could not express and
    D5-002 could not resolve is now computed. PAR_14 is fully deterministic.

    A node participates in Rāśi-dṛṣṭi because that is a relation between signs.
    It still casts no graha-dṛṣṭi.
    """
    out = P.par_14_branches(ctx.d5_house("Rahu"), ctx.d5_house("Ketu"),
                            ctx.d5_sign("Rahu"), ctx.d5_sign("Ketu"),
                            ctx.d5_sign("Venus"))
    value = out["resolved_branches_true"]
    parts = []
    if value:
        for node in ("Rahu", "Ketu"):
            if (ctx.d5_house(node) == 5
                    or P.conjunct(ctx.d5_sign(node), ctx.d5_sign("Venus"))
                    or P.rashi_drishti(ctx.d5_sign(node), ctx.d5_sign("Venus"))):
                parts.append(node)
        if out["node_conjunct_d5_venus"] or out["node_rashi_drishti_d5_venus"]:
            parts.append("Venus")
    return value, {"rahu_d5_house": ctx.d5_house("Rahu"),
                   "ketu_d5_house": ctx.d5_house("Ketu"),
                   "venus_d5_sign_index": ctx.d5_sign("Venus"),
                   "branch_node_in_5H": out["node_in_d5_fifth"],
                   "branch_node_conjunct_venus": out["node_conjunct_d5_venus"],
                   "branch_node_rashi_drishti_venus":
                       out["node_rashi_drishti_d5_venus"],
                   "participants": parts}, []


def _par_15(ctx):
    h = ctx.d5_house("Jupiter")
    placed = h in (1, 5, 9)
    asp = P.graha_aspects_house("Jupiter", h, 1)
    hit = bool(placed or asp)
    return hit, {"jupiter_d5_house": h, "in_trikona": placed,
                 "aspects_d5_lagna": asp,
                 "participants": ["Jupiter"] if hit else []}, []


def _par_16(ctx):
    l = ctx.facts["d1_fifth_lord_mirroring"]["planet"]
    h = ctx.d5_house(l)
    hit = P.is_kendra_or_trikona(h)
    return hit, {"d1_5L": l, "d5_house": h, "kendra": P.is_kendra(h),
                 "trikona": P.is_trikona(h),
                 "participants": [l] if hit else []}, []


def _par_17(ctx):
    """Barren Lagna or 5th, occupied by a Malefic — with Malefic now locked.

    D5-003-CORR-01B kept this unresolved because no benefic/malefic
    classification existed. Lock 4 supplies one, so the rule is deterministic
    except where a Moon in the target house needs a certified Tithi.
    """
    branches = []
    combined = FALSE
    parts: List[str] = []
    for label, sign_index, house in (
            ("d5_lagna", ctx.d5_lagna_si, 1),
            ("d5_5H", (ctx.d5_lagna_si + 4) % 12, 5)):
        barren = P.is_barren_sign(sign_index)
        occupants = ctx.occupants_of_d5_house(house)
        classified = {}
        occupied_by_malefic: Optional[bool] = FALSE
        if barren:
            for graha in occupants:
                malefic, _detail = ctx.natural_malefic(graha)
                classified[graha] = ("unresolved" if malefic is UNKNOWN
                                     else malefic)
                occupied_by_malefic = t_or(occupied_by_malefic, malefic)
                if malefic is TRUE:
                    parts.append(graha)
        value = t_and(barren, occupied_by_malefic)
        branches.append({"target": label, "sign_index": sign_index,
                         "barren": barren, "occupants": occupants,
                         "occupant_classification": classified,
                         "branch": "unresolved" if value is UNKNOWN else value})
        combined = t_or(combined, value)
    evidence = {"barren_signs": sorted(P.BARREN_SIGNS), "targets": branches,
                "participants": sorted(set(parts)) if combined is TRUE else []}
    return combined, evidence, ([CERTIFIED_TITHI] if combined is UNKNOWN else [])


def _par_18(ctx):
    l5 = ctx.d5_lord(5)
    h = ctx.d5_house(l5)
    hit = h in (8, 12)
    return hit, {"d5_5L": l5, "d5_house": h, "qualifying_houses": [8, 12],
                 "participants": [l5] if hit else []}, []


def _karaka_in_houses(ctx, karaka: str, houses: Sequence[int]):
    g = ctx.karaka(karaka)
    h = ctx.d5_house(g)
    hit = h in houses
    return hit, {"karaka": karaka, "graha": g, "d5_house": h,
                 "qualifying_houses": list(houses),
                 "participants": [g] if hit else []}, []


def _jai_01(ctx):
    return _karaka_in_houses(ctx, "AK", (1, 5, 11))


def _jai_02(ctx):
    g = ctx.karaka("AMK")
    h = ctx.d5_house(g)
    hit = P.is_kendra_or_trikona(h)
    return hit, {"karaka": "AMK", "graha": g, "d5_house": h,
                 "kendra": P.is_kendra(h), "trikona": P.is_trikona(h),
                 "participants": [g] if hit else []}, []


def _jai_03(ctx):
    """AK Rāśi-dṛṣṭi AMK. Deterministic under Lock 2."""
    ak, amk = ctx.karaka("AK"), ctx.karaka("AMK")
    value = P.rashi_drishti(ctx.d5_sign(ak), ctx.d5_sign(amk))
    return value, {"ak": ak, "amk": amk,
                   "ak_d5_sign_index": ctx.d5_sign(ak),
                   "amk_d5_sign_index": ctx.d5_sign(amk),
                   "rashi_drishti": value,
                   "participants": [ak, amk] if value else []}, []


def _jai_04(ctx):
    si = ctx.karakamsha["d5_karakamsha_sign_index"]
    house = ctx.karakamsha["d5_karakamsha_house"]
    occupied = [g for g in ("Jupiter", "Venus", "Mercury") if ctx.d5_sign(g) == si]
    aspecting = [g for g in ("Jupiter", "Venus", "Mercury")
                 if P.graha_aspects_house(g, ctx.d5_house(g), house)]
    hit = bool(occupied or aspecting)
    return hit, {
        "karakamsha_sign_index": si, "karakamsha_house": house,
        "occupied_by": occupied, "aspected_by": aspecting,
        "participants": sorted(set(occupied) | set(aspecting))}, []


def _jai_05(ctx):
    hs, hm = ctx.d5_house("Sun"), ctx.d5_house("Moon")
    distance = ((hm - hs) % 12) + 1
    hit = distance in P.KENDRA_TRIKONA
    return hit, {
        "sun_d5_house": hs, "moon_d5_house": hm, "relative_distance": distance,
        "scope": sorted(P.KENDRA_TRIKONA),
        "participants": ["Sun", "Moon"] if hit else []}, []


def _jai_06(ctx):
    return _karaka_in_houses(ctx, "PK", (1, 5, 11))


def _jai_07(ctx):
    """TICKET §8 LOCK · conjunction OR Kendra-only Mutual_Angle OR Rāśi-dṛṣṭi.

    All three branches are computable now, so the rule is deterministic. The
    Mutual_Angle branch stays Kendra-only — Lock 2 did not widen it.
    """
    ak, pk = ctx.karaka("AK"), ctx.karaka("PK")
    conj = P.conjunct(ctx.d5_sign(ak), ctx.d5_sign(pk))
    angle = P.jaimini_mutual_kendra(ctx.d5_house(ak), ctx.d5_house(pk))
    rashi = P.rashi_drishti(ctx.d5_sign(ak), ctx.d5_sign(pk))
    value = bool(conj or angle or rashi)
    return value, {"ak": ak, "ak_d5_house": ctx.d5_house(ak),
                   "pk": pk, "pk_d5_house": ctx.d5_house(pk),
                   "conjunct": conj, "mutual_angle_kendra_only": angle,
                   "rashi_drishti": rashi,
                   "participants": [ak, pk] if value else []}, []


def _jai_08(ctx):
    si = (ctx.karakamsha["d5_karakamsha_sign_index"] + 4) % 12
    hits = [g for g in ("Mercury", "Jupiter", "Venus") if ctx.d5_sign(g) == si]
    return bool(hits), {"fifth_from_karakamsha_sign_index": si,
                        "karakamsha_sign_index":
                            ctx.karakamsha["d5_karakamsha_sign_index"],
                        "occupying": hits, "participants": hits}, []


def _conj_or_rashi(ctx, a: str, b: str, labels: Tuple[str, str]):
    """Conjunct OR Rāśi-dṛṣṭi. Both branches are locked, so this shape is
    deterministic wherever it is used — JAI_09, JAI_11, JAI_13 and JAI_15."""
    conj = False if a == b else P.conjunct(ctx.d5_sign(a), ctx.d5_sign(b))
    rashi = False if a == b else P.rashi_drishti(ctx.d5_sign(a), ctx.d5_sign(b))
    value = bool(conj or rashi)
    ev = {labels[0]: a, labels[1]: b, "same_graha": a == b,
          f"{labels[0]}_d5_house": ctx.d5_house(a),
          f"{labels[1]}_d5_house": ctx.d5_house(b),
          "conjunct": conj, "rashi_drishti": rashi,
          "participants": [a, b] if value else []}
    return value, ev, []


def _jai_09(ctx):
    return _conj_or_rashi(ctx, "Mercury", "Moon", ("mercury", "moon"))


def _jai_10(ctx):
    return _karaka_in_houses(ctx, "DK", (5,))


def _jai_11(ctx):
    return _conj_or_rashi(ctx, ctx.karaka("AK"), ctx.karaka("DK"), ("ak", "dk"))


def _jai_12(ctx):
    """PK Rāśi-dṛṣṭi Venus. Deterministic under Lock 2."""
    pk = ctx.karaka("PK")
    value = (False if pk == "Venus"
             else P.rashi_drishti(ctx.d5_sign(pk), ctx.d5_sign("Venus")))
    return value, {"pk": pk, "pk_d5_sign_index": ctx.d5_sign(pk),
                   "venus_d5_sign_index": ctx.d5_sign("Venus"),
                   "same_graha": pk == "Venus", "rashi_drishti": value,
                   "participants": [pk, "Venus"] if value else []}, []


def _jai_13(ctx):
    return _conj_or_rashi(ctx, "Moon", "Venus", ("moon", "venus"))


def _jai_14(ctx):
    """§9 named relations, evaluated exactly. Not a generic Strong."""
    pk = ctx.karaka("PK")
    rel = {"exalted": ctx.is_exalted_in_d5(pk),
           "vargottama_d1_d5": ctx.is_vargottama_d1_d5(pk),
           "own_sign": ctx.is_own_sign_in_d5(pk)}
    hit = any(rel.values())
    return hit, {"pk": pk, "d5_sign_index": ctx.d5_sign(pk),
                 "d1_sign_index": ctx.d1_sign(pk),
                 "participants": [pk] if hit else [], **rel}, []


def _jai_15(ctx):
    return _conj_or_rashi(ctx, ctx.karaka("PK"), "Jupiter", ("pk", "jupiter"))


def _fifth_from_pk(ctx) -> int:
    return ((ctx.d5_house(ctx.karaka("PK")) - 1 + 4) % 12) + 1


def _jai_16(ctx):
    house = _fifth_from_pk(ctx)
    hits = [g for g in ("Rahu", "Ketu") if ctx.d5_house(g) == house]
    return bool(hits), {"pk": ctx.karaka("PK"),
                        "pk_d5_house": ctx.d5_house(ctx.karaka("PK")),
                        "fifth_from_pk_house": house, "occupying": hits}, []


def _jai_17(ctx):
    house = _fifth_from_pk(ctx)
    hit = ctx.d5_house("Mars") == house
    return hit, {"pk": ctx.karaka("PK"), "fifth_from_pk_house": house,
                 "mars_d5_house": ctx.d5_house("Mars")}, []


def _jai_18(ctx):
    """TICKET §8 LOCK. Exactly AK1/PK7, AK7/PK1, AK1/PK5, AK5/PK1."""
    ak, pk = ctx.karaka("AK"), ctx.karaka("PK")
    ha, hp = ctx.d5_house(ak), ctx.d5_house(pk)
    value = P.jai_18_axis(ha, hp)
    return value, {"ak": ak, "ak_d5_house": ha, "pk": pk, "pk_d5_house": hp,
                   "accepted_pairs": [(1, 7), (7, 1), (1, 5), (5, 1)],
                   "participants": sorted({ak, pk}) if value else []}, []


def _key_planets_in_tattva(ctx, tattva: str):
    """TAJ_01 / TAJ_02 · the DISTINCT key planets sitting in one tattva arc.

    D5-003-CORR-01A · THE FOUNDER-LOCKED THRESHOLD IS TWO. A single key planet
    in the arc does NOT fire the rule; two distinct PHYSICAL grahas are needed.

    The distinction between roles and grahas is what makes the threshold mean
    anything. There are five role slots and they routinely collapse — the Sun is
    often also the Atmakaraka, and the D5 Lagna lord is often the D1 fifth lord —
    so counting slots would report two where one graha stands, and a rule
    requiring two planets would fire on one.

    The participants are exactly those distinct grahas: they ARE the fired
    condition, already de-duplicated by physical body.
    """
    roles = ctx.key_planet_roles()
    tattva_by_graha = {g: ctx.tattva(g) for g in ctx.grahas}
    found = P.distinct_key_planets_in_tattva(roles, tattva_by_graha, tattva)
    fired = len(found) >= 2
    return fired, {"tattva": tattva, "roles": roles,
                   "distinct_key_planets": sorted(found),
                   "distinct_count": len(found),
                   "threshold_applied": ">= 2",
                   "participants": sorted(found) if fired else []}, []


def _taj_01(ctx):
    return _key_planets_in_tattva(ctx, "Agni")


def _taj_02(ctx):
    return _key_planets_in_tattva(ctx, "Akasha")


def _pair_in_tattva(ctx, first: str, second: Optional[str], tattva: str,
                    first_is_lagna: bool = False):
    """One subject pair against a tattva arc.

    PARTICIPANTS ARE THE MATCHING SUBJECTS ONLY, and the D5 LAGNA IS NOT A
    PHYSICAL GRAHA — it is a point, so it can satisfy the rule without
    contributing anything for triangulation to attach to. That case is recorded
    explicitly as `non_planetary_subjects` rather than left as a bare empty
    participant list, so the scorer can tell a legitimately non-planetary branch
    from a rule that forgot to publish its participants.
    """
    entries = []
    fired = FALSE
    parts: List[str] = []
    non_planetary: List[str] = []
    for label, value in ((first, ctx.lagna["tattva"] if first_is_lagna
                          else ctx.tattva(first)),
                         (second, ctx.tattva(second) if second else None)):
        if label is None:
            continue
        hit = value == tattva
        entries.append({"subject": label, "tattva": value, "match": hit})
        if hit:
            if label in ctx.grahas:
                parts.append(label)
            else:
                non_planetary.append(label)
        fired = t_or(fired, hit)
    return fired, {"required_tattva": tattva, "subjects": entries,
                   "participants": sorted(set(parts)),
                   "non_planetary_subjects": sorted(set(non_planetary))}, []


def _lagna_or_moon(tattva):
    def rule(ctx):
        return _pair_in_tattva(ctx, "D5_Lagna", "Moon", tattva, first_is_lagna=True)
    return rule


def _fifth_lord_or_jupiter(tattva):
    def rule(ctx):
        return _pair_in_tattva(ctx, ctx.d5_lord(5), "Jupiter", tattva)
    return rule


# ─────────────────────────────────────────────────────────────────────────────
# CLASSICAL AND MISC RULES
# ─────────────────────────────────────────────────────────────────────────────

def _misc_01(ctx):
    """(Benefic OR Strong) in H11. Both operators are now locked; only a
    missing Tithi or combustion fact can leave it unresolved."""
    occupants = ctx.occupants_of_d5_house(11)
    if not occupants:
        return FALSE, {"d5_11H_occupants": [], "participants": [],
                       "note": "no graha in H11, so nothing could satisfy it"}, []
    combined = FALSE
    detail = []
    parts: List[str] = []
    missing: Set[str] = set()
    for graha in occupants:
        benefic, _b = ctx.natural_benefic(graha)
        strong, _s = ctx.strong_in_d5(graha)
        value = t_or(benefic, strong)
        if benefic is UNKNOWN:
            missing.add(CERTIFIED_TITHI)
        if strong is UNKNOWN:
            missing.add(CERTIFIED_COMBUSTION)
        detail.append({"graha": graha,
                       "benefic": "unresolved" if benefic is UNKNOWN else benefic,
                       "strong": "unresolved" if strong is UNKNOWN else strong})
        if value is TRUE:
            parts.append(graha)
        combined = t_or(combined, value)
    return combined, {"d5_11H_occupants": occupants, "per_occupant": detail,
                      "participants": parts if combined is TRUE else []}, \
        (sorted(missing) if combined is UNKNOWN else [])


def _misc_02(ctx):
    named = ("Rahu", "Mars", "Saturn")
    hits = [{"graha": g, "d5_house": ctx.d5_house(g)} for g in named
            if ctx.d5_house(g) in (3, 6)]
    return bool(hits), {"named": list(named), "qualifying": hits,
                        "qualifying_houses": [3, 6],
                        "participants": [h["graha"] for h in hits]}, []


def _cla_01(ctx):
    """Exchange OR Association — and Association subsumes exchange under Lock 1,
    so the rule is now decided by the single canonical predicate."""
    a, b = ctx.d5_lord(5), ctx.d5_lord(8)
    exchange = P.sign_exchange(a, ctx.d5_sign(a), b, ctx.d5_sign(b), ctx.doctrine)
    association = ctx.associated(a, b) if a != b else False
    value = exchange or association
    return value, {"d5_5L": a, "d5_5L_d5_sign_index": ctx.d5_sign(a),
                   "d5_8L": b, "d5_8L_d5_sign_index": ctx.d5_sign(b),
                   "same_graha": a == b, "sign_exchange": exchange,
                   "association": association,
                   "participants": [a, b] if value else []}, []


def _cla_02(ctx):
    """(Rahu OR Saturn OR Malefic) in H12, with Malefic now locked."""
    occupants = ctx.occupants_of_d5_house(12)
    named = [g for g in ("Rahu", "Saturn") if g in occupants]
    if named:
        return TRUE, {"d5_12H_occupants": occupants, "qualifying_named": named,
                      "participants": named}, []
    if not occupants:
        return FALSE, {"d5_12H_occupants": [], "qualifying_named": [],
                       "participants": [], "note": "H12 is unoccupied"}, []
    combined = FALSE
    classified = {}
    parts: List[str] = []
    for graha in occupants:
        malefic, _d = ctx.natural_malefic(graha)
        classified[graha] = "unresolved" if malefic is UNKNOWN else malefic
        if malefic is TRUE:
            parts.append(graha)
        combined = t_or(combined, malefic)
    return combined, {"d5_12H_occupants": occupants, "qualifying_named": [],
                      "occupant_classification": classified,
                      "participants": parts if combined is TRUE else []}, \
        ([CERTIFIED_TITHI] if combined is UNKNOWN else [])


def _supports_house(ctx: Ctx, graha: str, house: int) -> Dict[str, bool]:
    """D5-006 §4 · the three support geometries, computed against the HOUSE.

    THE HOUSE IS NOT REPLACED BY ITS LORD. Rāśi-dṛṣṭi targets the zodiac sign
    that occupies the house; graha-dṛṣṭi targets the house itself. Substituting
    the lord is the shortcut the D5-005 audit rejected in the browser's
    `houseStrength`, and it is not taken here.
    """
    target_sign = (ctx.d5_lagna_si + house - 1) % 12
    occupies = ctx.d5_house(graha) == house
    graha_drishti = P.graha_aspects_house(graha, ctx.d5_house(graha), house)
    rashi = P.rashi_drishti(ctx.d5_sign(graha), target_sign)
    return {"occupies": occupies, "graha_drishti": graha_drishti,
            "rashi_drishti": rashi,
            "supports": bool(occupies or graha_drishti or rashi)}


def _cla_03(ctx):
    """D5-006 §4 · "D5_11H Strong" AND "D5_11H Occupied_By Benefics".

        Branch A — the D5 11th lord is Strong/Well-Placed;
        Branch B — the 11th lord occupies, graha-aspects or rāśi-aspects H11;
        Branch C — any natural benefic does the same.

    Branch B is deliberately blind to the 11th lord's own benefic/malefic
    classification: the lord supports its own house whatever its nature.

    D5-006-CORR-01C · UNRESOLVED SOURCES ARE TRACKED PER BRANCH AND PROPAGATED
    ONLY WHERE STILL LOAD-BEARING. A missing combustion fact makes Branch A
    UNKNOWN, but if Branch B is definitely TRUE then `house_strong` is TRUE and
    combustion can no longer change any answer — so it must NOT be reported.
    Reporting it would send someone to fetch a fact that would not move the
    result. Sources are attached to the operand that owns them, and only the
    operands still capable of deciding the outcome contribute.
    """
    l11 = ctx.d5_lord(11)
    occupants = ctx.occupants_of_d5_house(11)
    parts: Set[str] = set()

    # ── Branch A · the 11th lord is Strong ──
    strong, strong_detail = ctx.strong_in_d5(l11)
    branch_a_sources = {CERTIFIED_COMBUSTION} if strong is UNKNOWN else set()
    if strong is TRUE:
        parts.add(l11)

    # ── Branch B · the 11th lord supports H11 · always deterministic ──
    lord_support = _supports_house(ctx, l11, 11)
    if lord_support["supports"]:
        parts.add(l11)

    # ── Branch C · a natural benefic supports H11 ──
    benefic_support: Optional[bool] = FALSE
    branch_c_sources: Set[str] = set()
    support_detail = []
    for graha in sorted(ctx.grahas):
        geometry = _supports_house(ctx, graha, 11)
        if not geometry["supports"]:
            continue                      # no geometry, so classification is moot
        benefic, _b = ctx.natural_benefic(graha)
        if benefic is UNKNOWN:
            branch_c_sources.add(CERTIFIED_TITHI)
        elif benefic is TRUE:
            parts.add(graha)
        support_detail.append({"graha": graha, **geometry,
                               "benefic": ("unresolved" if benefic is UNKNOWN
                                           else benefic)})
        benefic_support = t_or(benefic_support, benefic)

    house_strong = t_or(strong, lord_support["supports"], benefic_support)
    # Only an UNKNOWN house_strong carries sources, and only from the branches
    # that are themselves UNKNOWN.
    house_strong_sources: Set[str] = set()
    if house_strong is UNKNOWN:
        if strong is UNKNOWN:
            house_strong_sources |= branch_a_sources
        if benefic_support is UNKNOWN:
            house_strong_sources |= branch_c_sources

    # ── the second conjunct · a natural benefic PHYSICALLY occupies H11 ──
    benefic_occupancy: Optional[bool] = FALSE
    occupancy_sources: Set[str] = set()
    occupancy_detail = {}
    for graha in occupants:
        benefic, _b = ctx.natural_benefic(graha)
        occupancy_detail[graha] = ("unresolved" if benefic is UNKNOWN
                                   else benefic)
        if benefic is UNKNOWN:
            occupancy_sources.add(CERTIFIED_TITHI)
        elif benefic is TRUE:
            parts.add(graha)
        benefic_occupancy = t_or(benefic_occupancy, benefic)

    value = t_and(house_strong, benefic_occupancy)
    # Only an UNKNOWN result reports anything, and only from the conjuncts that
    # are themselves still UNKNOWN.
    sources: Set[str] = set()
    if value is UNKNOWN:
        if house_strong is UNKNOWN:
            sources |= house_strong_sources
        if benefic_occupancy is UNKNOWN:
            sources |= occupancy_sources

    evidence = {
        "d5_11L": l11, "d5_11H_occupants": occupants,
        "branch_a_lord_strong": ("unresolved" if strong is UNKNOWN else strong),
        "branch_a_detail": strong_detail,
        "branch_b_lord_supports": lord_support,
        "branch_c_benefic_support": ("unresolved" if benefic_support is UNKNOWN
                                     else benefic_support),
        "branch_c_detail": support_detail,
        "house_strong": ("unresolved" if house_strong is UNKNOWN
                         else house_strong),
        "house_strong_sources": sorted(house_strong_sources),
        "benefic_occupancy": ("unresolved" if benefic_occupancy is UNKNOWN
                              else benefic_occupancy),
        "benefic_occupancy_sources": sorted(occupancy_sources),
        "occupant_classification": occupancy_detail,
        "participants": sorted(parts) if value is TRUE else []}
    return value, evidence, sorted(sources)


def _cla_04(ctx):
    return _planet_in_house(ctx, "Saturn", 5)


# ─────────────────────────────────────────────────────────────────────────────
# AFFLICTION RULES
# ─────────────────────────────────────────────────────────────────────────────

def _aff_01(ctx):
    cands = [ctx.d5_lord(1), ctx.karaka("PK")]
    ok, hits = _any_in_houses(ctx, cands, (6,))
    return ok, {"d5_1L": cands[0], "pk": cands[1],
                "d5_houses": {g: ctx.d5_house(g) for g in set(cands)},
                "qualifying": hits, "required_house": 6,
                "participants": hits}, []


def _aff_02(ctx):
    cands = [ctx.facts["d1_fifth_lord_mirroring"]["planet"], "Jupiter"]
    ok, hits = _any_in_houses(ctx, cands, (8,))
    return ok, {"d1_5L": cands[0],
                "d5_houses": {g: ctx.d5_house(g) for g in set(cands)},
                "qualifying": hits, "required_house": 8,
                "participants": hits}, []


def _aff_03(ctx):
    l10 = ctx.d5_lord(10)
    h = ctx.d5_house(l10)
    hit = (h == 12)
    return hit, {"d5_10L": l10, "d5_house": h, "required_house": 12,
                 "participants": [l10] if hit else []}, []


def _aff_04(ctx):
    """TICKET §8 LOCK, three branches, none of them an aspect.

    The workbook offers "Conjunct OR Mutual_Aspect". A mutual aspect with Rahu
    is impossible under the locked node doctrine, so that branch is dead and the
    workbook rule reduces to conjunction alone. §8 replaces it with the two
    named house axes. The divergence is deliberate.
    """
    value = P.aff_04(ctx.d5_sign("Saturn"), ctx.d5_sign("Rahu"),
                     ctx.d5_house("Saturn"), ctx.d5_house("Rahu"))
    return value, {"saturn_d5_house": ctx.d5_house("Saturn"),
                   "rahu_d5_house": ctx.d5_house("Rahu"),
                   "conjunct": P.conjunct(ctx.d5_sign("Saturn"),
                                          ctx.d5_sign("Rahu")),
                   "accepted_axes": [(1, 7), (7, 11)],
                   # Both bodies establish every branch of this rule.
                   "participants": ["Rahu", "Saturn"] if value else []}, []


def _aff_05(ctx):
    return _planet_in_house(ctx, "Rahu", 5)


def _aff_06(ctx):
    return _planet_in_house(ctx, "Ketu", 5)


# ─────────────────────────────────────────────────────────────────────────────
# THE RULE TABLE
# ─────────────────────────────────────────────────────────────────────────────

RULES: Dict[str, Callable[[Ctx], Tuple[Optional[bool], Dict[str, Any], List[str]]]] = {
    "D5_ANAL_01": _anal_01, "D5_ANAL_02": _anal_02, "D5_ANAL_03": _anal_03,
    "D5_ANAL_04": _anal_04, "D5_ANAL_05": _anal_05, "D5_ANAL_06": _anal_06,
    "D5_ANAL_07": _anal_07, "D5_ANAL_08": _anal_08,
    "D5_PAR_01": _par_01, "D5_PAR_02": _par_02, "D5_PAR_03": _par_03,
    "D5_PAR_04": _par_04, "D5_PAR_05": _par_05, "D5_PAR_06": _par_06,
    "D5_PAR_07": _par_07, "D5_PAR_08": _par_08, "D5_PAR_09": _par_09,
    "D5_PAR_10": _par_10, "D5_PAR_11": _par_11, "D5_PAR_12": _par_12,
    "D5_PAR_13": _par_13, "D5_PAR_14": _par_14, "D5_PAR_15": _par_15,
    "D5_PAR_16": _par_16, "D5_PAR_17": _par_17, "D5_PAR_18": _par_18,
    "D5_JAI_01": _jai_01, "D5_JAI_02": _jai_02, "D5_JAI_03": _jai_03,
    "D5_JAI_04": _jai_04, "D5_JAI_05": _jai_05, "D5_JAI_06": _jai_06,
    "D5_JAI_07": _jai_07, "D5_JAI_08": _jai_08, "D5_JAI_09": _jai_09,
    "D5_JAI_10": _jai_10, "D5_JAI_11": _jai_11, "D5_JAI_12": _jai_12,
    "D5_JAI_13": _jai_13, "D5_JAI_14": _jai_14, "D5_JAI_15": _jai_15,
    "D5_JAI_16": _jai_16, "D5_JAI_17": _jai_17, "D5_JAI_18": _jai_18,
    "D5_TAJ_01": _taj_01, "D5_TAJ_02": _taj_02,
    "D5_TAJ_03": _lagna_or_moon("Agni"), "D5_TAJ_04": _lagna_or_moon("Prithvi"),
    "D5_TAJ_05": _lagna_or_moon("Vayu"), "D5_TAJ_06": _lagna_or_moon("Jala"),
    "D5_TAJ_07": _lagna_or_moon("Akasha"),
    "D5_TAJ_08": _fifth_lord_or_jupiter("Agni"),
    "D5_TAJ_09": _fifth_lord_or_jupiter("Prithvi"),
    "D5_TAJ_10": _fifth_lord_or_jupiter("Vayu"),
    "D5_TAJ_11": _fifth_lord_or_jupiter("Jala"),
    "D5_MISC_01": _misc_01, "D5_MISC_02": _misc_02,
    "D5_CLA_01": _cla_01, "D5_CLA_02": _cla_02, "D5_CLA_03": _cla_03,
    "D5_CLA_04": _cla_04,
    "D5_AFF_01": _aff_01, "D5_AFF_02": _aff_02, "D5_AFF_03": _aff_03,
    "D5_AFF_04": _aff_04, "D5_AFF_05": _aff_05, "D5_AFF_06": _aff_06,
}


def evaluate_rule(rule_id: str, facts: Dict[str, Any], doctrine: D5Doctrine,
                  rules_doctrine: D5RulesDoctrine,
                  inputs: Optional[D5RuleInputs] = None) -> RuleOutcome:
    """One rule, evaluated against the certified D5-001 facts.

    `inputs` is optional so every caller written before D5-005 keeps working:
    an absent input set leaves the operational facts unsupplied, which the
    three-valued operators handle as UNKNOWN rather than as False.
    """
    if rule_id not in RULES:
        raise D5DomainError("unknown rule id")
    ctx = Ctx(facts, doctrine, rules_doctrine, inputs)
    value, evidence, unresolved = RULES[rule_id](ctx)
    polarity, weight = RULE_META[rule_id]
    status = status_of(value)
    if status != UNRESOLVED:
        unresolved = []
    if status == UNRESOLVED and not unresolved:
        raise D5DomainError("an UNRESOLVED rule must name its unresolved primitive")
    return RuleOutcome(rule_id=rule_id, status=status, polarity=polarity,
                       base_weight=weight, evidence=evidence,
                       unresolved_primitives=sorted(set(unresolved)))


def evaluate_all(facts: Dict[str, Any], doctrine: D5Doctrine,
                 rules_doctrine: D5RulesDoctrine,
                 inputs: Optional[D5RuleInputs] = None) -> Dict[str, RuleOutcome]:
    """All 67 static rules. NOTHING IS SUMMED, WEIGHTED OR RANKED."""
    return {rid: evaluate_rule(rid, facts, doctrine, rules_doctrine, inputs)
            for rid in RULES}


# ─────────────────────────────────────────────────────────────────────────────
# PARTICIPANT EXTRACTION — ONE CANONICAL PATH
# ─────────────────────────────────────────────────────────────────────────────

#: Evidence keys that name the physical grahas of a FIRED rule's actual firing
#: branch. Rules that can fire write `participants` deliberately at the point
#: where the branch is decided, so extraction reads a fact the rule asserted
#: rather than re-deriving it from prose. THIS IS THE ONLY EXTRACTION PATH.
_PARTICIPANT_KEY = "participants"


def extract_rule_participants(rule_id: str, outcome: RuleOutcome,
                              facts: Dict[str, Any],
                              doctrine: D5Doctrine) -> FrozenSet[str]:
    """The physical grahas establishing a FIRED rule's condition.

    A rule that is NOT_FIRED or UNRESOLVED asserts NO participants — an
    unresolved rule has established nothing, so it contributes nothing.

    Nothing is parsed from prose, and a graha named in a FAILED OR branch is not
    a participant: the rule records only the branch that actually fired.
    """
    if outcome.status != FIRED:
        return frozenset()
    named = outcome.evidence.get(_PARTICIPANT_KEY, [])
    grahas = set(facts["grahas"])
    return frozenset(g for g in named if g in grahas)


#: LOCK 5 · a qualifying positive yoga. All three conditions, no exceptions.
POSITIVE_YOGA_MIN_WEIGHT = 1.5


def qualifies_as_positive_yoga(outcome: RuleOutcome) -> bool:
    return (outcome.status == FIRED and outcome.polarity == "Positive"
            and outcome.base_weight >= POSITIVE_YOGA_MIN_WEIGHT)


def derive_positive_fired_yoga_participants(
        static_outcomes: Mapping[str, RuleOutcome], facts: Dict[str, Any],
        doctrine: D5Doctrine) -> FrozenSet[str]:
    """LOCK 5 · the authoritative `positive_fired_yoga_participants` for TIM_03.

    STATIC RULES ONLY. TIM rules are excluded deliberately: TIM_03 consumes this
    set, so including timing would make the definition circular. TRI rules are
    excluded by the same lock.
    """
    participants: Set[str] = set()
    for rule_id, outcome in static_outcomes.items():
        if rule_id.startswith("D5_TIM") or rule_id.startswith("D5_TRI"):
            continue
        if not qualifies_as_positive_yoga(outcome):
            continue
        participants |= extract_rule_participants(rule_id, outcome, facts,
                                                  doctrine)
    return frozenset(participants)


#: LOCK 6 · the four rules that can contribute a Raj Yoga participant.
RAJ_YOGA_RULE_IDS: Tuple[str, ...] = ("D5_PAR_02", "D5_PAR_03",
                                      "D5_JAI_02", "D5_JAI_03")


def derive_d5_raj_yoga_participants(
        static_outcomes: Mapping[str, RuleOutcome], facts: Dict[str, Any],
        doctrine: D5Doctrine) -> FrozenSet[str]:
    """LOCK 6 · the authoritative `d5_raj_yoga_participants` for TRI_02.

    ONLY A FIRED RULE CONTRIBUTES. An UNRESOLVED Raj Yoga rule asserts no
    participant, which is why JAI_03 contributes AK and AMK only when it fires.
    """
    participants: Set[str] = set()
    for rule_id in RAJ_YOGA_RULE_IDS:
        outcome = static_outcomes.get(rule_id)
        if outcome is None or outcome.status != FIRED:
            continue
        participants |= extract_rule_participants(rule_id, outcome, facts,
                                                  doctrine)
    return frozenset(participants)
