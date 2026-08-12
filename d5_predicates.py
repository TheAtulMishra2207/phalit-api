"""
d5_predicates.py — D5-002 · THE DETERMINISTIC PREDICATE KERNEL.

ONE VOCABULARY, CALLED BY EVERY LATER RULE. The 80-rule matrix must ask these
questions here rather than re-answering them rule by rule. Eighty private
answers to "does this graha aspect that house" is eighty places for one of them
to be wrong.

WHAT THIS MODULE IS NOT. No rule fires here. No score, no weight, no tier, no
index, no archetype, no timing, no narrative, no provider call, no HTTP, no
frontend. `/d5/prepare` is untouched. Every function is pure.

NO D4 DEPENDENCY. D4 is scheduled for rebuild, so a primitive that exists only
inside D4 is historical evidence and never an import. Nothing here reaches into
d4_core, d4_routes or any other d4_* module, and a source scan in the suite
proves it.

SHARED TABLES ARE INJECTED, NOT RESTATED. Sign lordship comes from the accepted
D5-001 `D5Doctrine`, which already carries the product's one SIGN_LORDS table.
This module defines no second zodiac lordship table.

FOUR OPERATORS ARE DELIBERATELY ABSENT. Association, Rāśi-dṛṣṭi, "strong /
well-placed" and benefic/malefic are NOT implemented here. D5-002's inventory
found no certified backend primitive for any of them and found the last three
implemented inconsistently elsewhere. Choosing a convention to close that gap is
exactly what the ticket forbids, so each is exposed as an explicit unavailable
operator that RAISES rather than a default that quietly picks a side. See
D5-002-PRIMITIVE-INVENTORY.md.
"""
from __future__ import annotations

from typing import (Any, Dict, FrozenSet, Iterable, Mapping, Optional,
                    Sequence, Set, Tuple)

from d5_engine import D5Doctrine, D5DomainError

__all__ = [
    "D5PrimitiveUnavailable", "GRAHA_DRISHTI", "NODES", "KENDRA", "TRIKONA",
    "KENDRA_TRIKONA", "BARREN_SIGNS", "RASHI_DRISHTI_AVAILABLE",
    "conjunct", "graha_aspects_house", "graha_aspects_sign",
    "mutual_graha_aspect", "mutual_graha_aspect_by_sign", "sign_exchange",
    "nth_house_sign_index", "nth_house_lord", "d1_house_lord", "d5_house_lord",
    "house_of_sign", "is_kendra", "is_trikona", "is_kendra_or_trikona",
    "conjunction_in_kendra_trikona", "aspect_with_both_in_kendra_trikona",
    "is_d1_d5_vargottama", "is_d1_d9_vargottama",
    "jaimini_mutual_kendra", "jai_18_axis", "aff_04", "par_14_branches",
    "anal_05", "anal_06", "is_barren_sign", "distinct_key_planets_in_tattva",
    # D5-005 · the Founder locks that close the D5-002 doctrine gaps
    "associated", "rashi_drishti", "MOVABLE_SIGNS", "FIXED_SIGNS", "DUAL_SIGNS",
    "MOOLATRIKONA_SIGN", "is_moolatrikona", "debilitation_sign", "DUSTHANA",
    "positive_dignity", "deterministic_negative_placement",
]


class D5PrimitiveUnavailable(NotImplementedError):
    """An operator the D5-002 inventory could NOT resolve to a certified
    primitive.

    Raised rather than defaulted. A default here would be this module silently
    choosing a Jyotisha convention, which is the one thing D5-002 forbids, and
    the choice would then be invisible inside every rule that consumed it.
    """


# ─────────────────────────────────────────────────────────────────────────────
# LOCKED MANIFESTS
# ─────────────────────────────────────────────────────────────────────────────

#: Classical graha-dṛṣṭi, as house counts from the graha's own house, the
#: graha's own house counted as 1. The universal 7th plus the special aspects.
#: RAHU AND KETU ARE ABSENT BY DOCTRINE, not by omission: they cast no
#: independent graha-dṛṣṭi. They remain valid TARGETS.
GRAHA_DRISHTI: Dict[str, Tuple[int, ...]] = {
    "Sun": (7,),
    "Moon": (7,),
    "Mars": (4, 7, 8),
    "Mercury": (7,),
    "Jupiter": (5, 7, 9),
    "Venus": (7,),
    "Saturn": (3, 7, 10),
}

NODES: FrozenSet[str] = frozenset({"Rahu", "Ketu"})

KENDRA: FrozenSet[int] = frozenset({1, 4, 7, 10})
TRIKONA: FrozenSet[int] = frozenset({1, 5, 9})
#: The canonical union the Founder scope rules use. Stated as its own constant
#: because {1,4,5,7,9,10} is the scope, not "Kendra or Trikona" re-derived at
#: each call site.
KENDRA_TRIKONA: FrozenSet[int] = frozenset({1, 4, 5, 7, 9, 10})

#: Founder-locked barren signs, by 0-based sign index:
#: Aries 0 · Taurus 1 · Leo 4 · Virgo 5.
BARREN_SIGNS: FrozenSet[int] = frozenset({0, 1, 4, 5})

#: D5-002 inventory result. No certified Rāśi-dṛṣṭi primitive exists in the
#: accepted backend, so every rule branch depending on it is unavailable.
RASHI_DRISHTI_AVAILABLE = False


# ─────────────────────────────────────────────────────────────────────────────
# GUARDS
# ─────────────────────────────────────────────────────────────────────────────

def _sign(value: Any, what: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise D5DomainError(f"{what} sign index is not an integer")
    if not 0 <= value <= 11:
        raise D5DomainError(f"{what} sign index is outside 0..11")
    return value


def _house(value: Any, what: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise D5DomainError(f"{what} house is not an integer")
    if not 1 <= value <= 12:
        raise D5DomainError(f"{what} house is outside 1..12")
    return value


def _graha(value: Any, what: str) -> str:
    if not isinstance(value, str) or not value:
        raise D5DomainError(f"{what} is not a graha name")
    return value


# ─────────────────────────────────────────────────────────────────────────────
# A · WHOLE-SIGN CONJUNCTION
# ─────────────────────────────────────────────────────────────────────────────

def conjunct(sign_a: Any, sign_b: Any) -> bool:
    """Two placements are conjunct when they share a sign in the same chart.

    NO DEGREE ORB. Two grahas at opposite ends of one sign are conjunct; two
    grahas one arcsecond apart across a sign boundary are not. The degree is
    never consulted, so no orb can be introduced by accident later.
    """
    return _sign(sign_a, "first") == _sign(sign_b, "second")


# ─────────────────────────────────────────────────────────────────────────────
# B · CLASSICAL GRAHA DRISHTI
# ─────────────────────────────────────────────────────────────────────────────

def graha_aspects_house(source_graha: Any, source_house: Any,
                        target_house: Any) -> bool:
    """Does this graha, sitting in this house, cast graha-dṛṣṭi on that house?

    A node ALWAYS returns False on the source side. It is not an error to ask —
    rules legitimately test both directions — but the answer is never True.
    """
    graha = _graha(source_graha, "source graha")
    src = _house(source_house, "source")
    tgt = _house(target_house, "target")
    counts = GRAHA_DRISHTI.get(graha)
    if counts is None:
        return False
    return any(((src - 1 + count - 1) % 12) + 1 == tgt for count in counts)


def graha_aspects_sign(source_graha: Any, source_sign: Any,
                       target_sign: Any) -> bool:
    """The same relation stated over signs rather than houses.

    Whole-sign houses make these two forms equivalent, and both are provided so
    a rule never has to convert a sign to a house just to ask the question.
    """
    graha = _graha(source_graha, "source graha")
    src = _sign(source_sign, "source")
    tgt = _sign(target_sign, "target")
    counts = GRAHA_DRISHTI.get(graha)
    if counts is None:
        return False
    return any((src + count - 1) % 12 == tgt for count in counts)


# ─────────────────────────────────────────────────────────────────────────────
# C · MUTUAL GRAHA ASPECT
# ─────────────────────────────────────────────────────────────────────────────

def mutual_graha_aspect(graha_a: Any, house_a: Any,
                        graha_b: Any, house_b: Any) -> bool:
    """True only when EACH aspects the other.

    A node can never satisfy either side, because it never satisfies the source
    side, so any pair involving a node is False.
    """
    return (graha_aspects_house(graha_a, house_a, house_b)
            and graha_aspects_house(graha_b, house_b, house_a))


def mutual_graha_aspect_by_sign(graha_a: Any, sign_a: Any,
                                graha_b: Any, sign_b: Any) -> bool:
    return (graha_aspects_sign(graha_a, sign_a, sign_b)
            and graha_aspects_sign(graha_b, sign_b, sign_a))


# ─────────────────────────────────────────────────────────────────────────────
# D · SIGN EXCHANGE
# ─────────────────────────────────────────────────────────────────────────────

def sign_exchange(planet_a: Any, sign_a: Any, planet_b: Any, sign_b: Any,
                  doctrine: D5Doctrine) -> bool:
    """Each planet occupies a sign the other owns.

    A planet cannot manufacture an exchange with itself: Mercury in Gemini owns
    the sign it sits in, which is own-sign placement and not an exchange, so the
    identity case is rejected before the lordship test.
    """
    a = _graha(planet_a, "first planet")
    b = _graha(planet_b, "second planet")
    if a == b:
        return False
    si_a = _sign(sign_a, "first")
    si_b = _sign(sign_b, "second")
    return (doctrine.sign_lords[si_a] == b) and (doctrine.sign_lords[si_b] == a)


# ─────────────────────────────────────────────────────────────────────────────
# E · HOUSE LORD RESOLUTION
# ─────────────────────────────────────────────────────────────────────────────

def nth_house_sign_index(lagna_sign_index: Any, n: Any) -> int:
    """The sign occupying the nth whole-sign house from a lagna."""
    return (_sign(lagna_sign_index, "lagna") + _house(n, "nth") - 1) % 12


def nth_house_lord(lagna_sign_index: Any, n: Any, doctrine: D5Doctrine) -> str:
    """The lord of the nth house. ONE implementation serves every rule.

    Per-rule hard-coded lord tables are what this exists to prevent: D1 5L and
    D5 5L differ only in which lagna is passed, never in the lookup.
    """
    return doctrine.sign_lords[nth_house_sign_index(lagna_sign_index, n)]


def d1_house_lord(d1_lagna_sign_index: Any, n: Any, doctrine: D5Doctrine) -> str:
    """Named for legibility at the call site. Same lookup, D1 lagna."""
    return nth_house_lord(d1_lagna_sign_index, n, doctrine)


def d5_house_lord(d5_lagna_sign_index: Any, n: Any, doctrine: D5Doctrine) -> str:
    """Named for legibility at the call site. Same lookup, D5 lagna."""
    return nth_house_lord(d5_lagna_sign_index, n, doctrine)


def house_of_sign(sign_index: Any, lagna_sign_index: Any) -> int:
    """The whole-sign house a sign occupies, relative to a lagna."""
    return ((_sign(sign_index, "sign") - _sign(lagna_sign_index, "lagna")) % 12) + 1


# ─────────────────────────────────────────────────────────────────────────────
# KENDRA / TRIKONA AND THE FOUNDER SCOPE MECHANICS
# ─────────────────────────────────────────────────────────────────────────────

def is_kendra(house: Any) -> bool:
    return _house(house, "house") in KENDRA


def is_trikona(house: Any) -> bool:
    return _house(house, "house") in TRIKONA


def is_kendra_or_trikona(house: Any) -> bool:
    """The canonical union {1,4,5,7,9,10} the Founder scope rules use."""
    return _house(house, "house") in KENDRA_TRIKONA


def conjunction_in_kendra_trikona(house_a: Any, house_b: Any) -> bool:
    """The CONJUNCTION branch of the PAR_02 / PAR_12 scope.

    The two grahas must share a house AND that house must be in the union. A
    conjunction in H3 does not qualify however strong it looks.
    """
    a = _house(house_a, "first")
    b = _house(house_b, "second")
    return a == b and a in KENDRA_TRIKONA


def aspect_with_both_in_kendra_trikona(graha_a: Any, house_a: Any,
                                       graha_b: Any, house_b: Any) -> bool:
    """The ASPECT branch of the PAR_02 / PAR_12 scope.

    The scope is INDIVIDUAL: each participating graha must itself occupy the
    union. An aspect from H3 onto H10 fails even though the target is a Kendra —
    reading the scope as "the aspected house is in the union" is the misreading
    this function exists to prevent. The aspect itself may run either way.
    """
    a = _house(house_a, "first")
    b = _house(house_b, "second")
    if a not in KENDRA_TRIKONA or b not in KENDRA_TRIKONA:
        return False
    return (graha_aspects_house(graha_a, a, b)
            or graha_aspects_house(graha_b, b, a))


# ─────────────────────────────────────────────────────────────────────────────
# VARGOTTAMA — THREE RELATIONS, KEPT APART
# ─────────────────────────────────────────────────────────────────────────────

def is_d1_d5_vargottama(d1_sign_index: Any, d5_sign_index: Any) -> bool:
    """Same zodiac sign in D1 and D5. NOT interchangeable with the D9 relation."""
    return _sign(d1_sign_index, "D1") == _sign(d5_sign_index, "D5")


def is_d1_d9_vargottama(d1_sign_index: Any, d9_sign_index: Any) -> bool:
    """Same zodiac sign in D1 and D9. NOT interchangeable with the D5 relation.

    There is deliberately NO generic `vargottama()` in this module. A single
    call taking an unnamed pair is exactly how D5_PAR_03, D5_JAI_14 and
    D5_TRI_03 would come to share a bug: the argument order would be right in
    two of them and silently wrong in the third.
    """
    return _sign(d1_sign_index, "D1") == _sign(d9_sign_index, "D9")


# ─────────────────────────────────────────────────────────────────────────────
# FOUNDER-LOCKED JAIMINI GEOMETRY
# ─────────────────────────────────────────────────────────────────────────────

def jaimini_mutual_kendra(house_a: Any, house_b: Any) -> bool:
    """D5_JAI_07 · mutual angle, meaning KENDRA ONLY.

    The relative distance between the two houses must be 1, 4, 7 or 10. Trines
    do NOT qualify: "mutual angle" is not every angular relationship, and
    reading it that way would admit 5 and 9 and roughly double the rule's hit
    rate. The relation is symmetric — 1/4 and 4/1 both give a distance in the
    set — so argument order cannot change the answer.
    """
    a = _house(house_a, "first")
    b = _house(house_b, "second")
    return (((b - a) % 12) + 1) in KENDRA


#: D5_JAI_18 · the ONLY four qualifying AK/PK arrangements, as (AK house, PK
#: house). No other pair qualifies, including 5/7 and 7/5.
_JAI_18_PAIRS: FrozenSet[Tuple[int, int]] = frozenset({
    (1, 7), (7, 1), (1, 5), (5, 1),
})


def jai_18_axis(ak_house: Any, pk_house: Any) -> bool:
    """D5_JAI_18 · exact membership, not a computed relation."""
    return (_house(ak_house, "AK"), _house(pk_house, "PK")) in _JAI_18_PAIRS


# ─────────────────────────────────────────────────────────────────────────────
# FOUNDER-LOCKED NODE PREDICATES
# ─────────────────────────────────────────────────────────────────────────────

def par_14_branches(rahu_house: Any, ketu_house: Any,
                    rahu_sign: Any, ketu_sign: Any,
                    venus_sign: Any) -> Dict[str, Any]:
    """D5_PAR_14 · all THREE branches, now that Rāśi-dṛṣṭi is locked.

    The branches are still returned separately rather than as one boolean, so a
    caller can see which one established the result — that is what the
    participant extractor reads. `complete` is now True: the third branch is a
    real answer instead of a gap.

    A node standing in a sign participates in Rāśi-dṛṣṭi. That is not node
    graha-dṛṣṭi, which remains forbidden — `GRAHA_DRISHTI` still has no entry
    for Rahu or Ketu.
    """
    node_in_fifth = (_house(rahu_house, "Rahu") == 5
                     or _house(ketu_house, "Ketu") == 5)
    node_conjunct_venus = (conjunct(rahu_sign, venus_sign)
                           or conjunct(ketu_sign, venus_sign))
    node_rashi_drishti_venus = (rashi_drishti(rahu_sign, venus_sign)
                                or rashi_drishti(ketu_sign, venus_sign))
    return {
        "node_in_d5_fifth": node_in_fifth,
        "node_conjunct_d5_venus": node_conjunct_venus,
        "node_rashi_drishti_d5_venus": node_rashi_drishti_venus,
        "rashi_drishti_available": RASHI_DRISHTI_AVAILABLE,
        "resolved_branches_true": (node_in_fifth or node_conjunct_venus
                                   or node_rashi_drishti_venus),
        "complete": RASHI_DRISHTI_AVAILABLE,
    }


def aff_04(saturn_sign: Any, rahu_sign: Any,
           saturn_house: Any, rahu_house: Any) -> bool:
    """D5_AFF_04 · exactly three branches, none of them an aspect.

    There is deliberately no generic Saturn-Rahu aspect branch. The Founder
    normalisation is conjunction plus two NAMED house axes, and Saturn casts
    3/7/10 while Rahu casts nothing, so an aspect substitute would both add
    hits the rule does not license and be asymmetric in a way the rule is not.
    """
    sat_si = _sign(saturn_sign, "Saturn")
    rah_si = _sign(rahu_sign, "Rahu")
    sat_h = _house(saturn_house, "Saturn")
    rah_h = _house(rahu_house, "Rahu")
    return (conjunct(sat_si, rah_si)
            or (sat_h == 1 and rah_h == 7)
            or (sat_h == 7 and rah_h == 11))


# ─────────────────────────────────────────────────────────────────────────────
# FOUNDER-LOCKED ANAL HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def anal_05(lord_11_house: Any, lord_8_house: Any,
            lord_11_graha: Any, lord_8_graha: Any) -> bool:
    """D5_ANAL_05 · both lords conjunct in H4, then EITHER aspecting H10.

    The aspect branch is a disjunction. Requiring both would be a stricter rule
    than the Founder stated, and the two lords have different aspect manifests,
    so "both" and "either" are not close to equivalent.
    """
    h11 = _house(lord_11_house, "11L")
    h8 = _house(lord_8_house, "8L")
    # Both lords in H4. Stated once and plainly: the conjunction is not "in the
    # Kendra/Trikona union", it is in the FOURTH house specifically.
    if not (h11 == 4 and h8 == 4):
        return False
    return (graha_aspects_house(lord_11_graha, h11, 10)
            or graha_aspects_house(lord_8_graha, h8, 10))


def anal_06(lord_3_graha: Any, lord_3_house: Any,
            lord_12_graha: Any, lord_12_house: Any,
            ketu_house: Any, lord_9_graha: Any, lord_9_house: Any) -> bool:
    """D5_ANAL_06 · either the 3rd or the 12th lord, conjunct Ketu in H9, and
    aspected by the 9th lord.

    ONE PHYSICAL GRAHA MAY OWN BOTH 3H AND 12H, and when it does it satisfies
    the disjunction on its own. The rule does not require two distinct planets,
    and de-duplicating the candidates is what makes that true rather than an
    accident of evaluation order.
    """
    candidates = []
    for graha, house in ((lord_3_graha, lord_3_house),
                         (lord_12_graha, lord_12_house)):
        entry = (_graha(graha, "lord"), _house(house, "lord"))
        if entry not in candidates:  # one graha owning both counts ONCE
            candidates.append(entry)
    ketu_h = _house(ketu_house, "Ketu")
    ninth_lord = _graha(lord_9_graha, "9L")
    ninth_h = _house(lord_9_house, "9L")
    for _candidate_graha, house in candidates:
        if house == 9 and ketu_h == 9:
            if graha_aspects_house(ninth_lord, ninth_h, 9):
                return True
    return False


# ─────────────────────────────────────────────────────────────────────────────
# BARREN SIGNS
# ─────────────────────────────────────────────────────────────────────────────

def is_barren_sign(sign_index: Any) -> bool:
    """Founder-locked: Aries, Taurus, Leo, Virgo.

    The "Occupied_By Malefic" half of D5_PAR_17 is NOT implemented, because the
    inventory found no authoritative benefic/malefic classification. See
    `is_malefic` below.
    """
    return _sign(sign_index, "sign") in BARREN_SIGNS


# ─────────────────────────────────────────────────────────────────────────────
# TATTVA / KEY-PLANET MECHANICS
# ─────────────────────────────────────────────────────────────────────────────

#: The five key-planet ROLES. Roles are slots; the grahas filling them may
#: coincide, and when they do the graha counts once.
KEY_PLANET_ROLES: Tuple[str, ...] = (
    "d5_lagna_lord", "d1_fifth_lord", "sun", "jupiter", "atmakaraka",
)


def distinct_key_planets_in_tattva(role_assignments: Dict[str, str],
                                   tattva_by_graha: Dict[str, str],
                                   tattva: str) -> Set[str]:
    """The DISTINCT physical grahas filling a key role and sitting in a tattva.

    Five roles can be filled by as few as two grahas — the Sun is frequently
    also the Atmakaraka, and the D5 Lagna lord is often the D1 fifth lord. A
    count over ROLES would then report five where there are two, and every
    downstream TAJ threshold would be inflated by the duplication. Returning a
    set of graha names makes double-counting impossible at the call site rather
    than merely unlikely.
    """
    unknown = set(role_assignments) - set(KEY_PLANET_ROLES)
    if unknown:
        raise D5DomainError("unknown key-planet role")
    return {graha for role, graha in role_assignments.items()
            if tattva_by_graha.get(graha) == tattva}


# ─────────────────────────────────────────────────────────────────────────────
# LOCK 1 · ASSOCIATION — ONE CANONICAL PREDICATE
# ─────────────────────────────────────────────────────────────────────────────

def associated(graha_a: Any, sign_a: Any, house_a: Any,
               graha_b: Any, sign_b: Any, house_b: Any,
               doctrine: D5Doctrine) -> bool:
    """Founder-locked Association: conjunction OR mutual aspect OR exchange.

    A SINGLE-DIRECTION ASPECT IS NOT ASSOCIATION. Jupiter in H1 aspects H5 and
    the Sun in H5 does not aspect back; that is a one-way dṛṣṭi and it does not
    establish Association. Rules that genuinely want one direction say `Aspects`
    or `Aspected_By` and call `graha_aspects_house` instead.

    THE SAME PHYSICAL GRAHA CANNOT ASSOCIATE WITH ITSELF. Where two lordships
    resolve to one body, every branch is vacuously satisfiable — it is trivially
    in its own sign, and `sign_exchange` already rejects the identity case — so
    the identity is rejected once, here, rather than three times downstream.

    This is the ONLY definition of Association in the product. No rule carries a
    second per-rule reading.
    """
    a = _graha(graha_a, "first planet")
    b = _graha(graha_b, "second planet")
    if a == b:
        return False
    return (conjunct(sign_a, sign_b)
            or mutual_graha_aspect(a, house_a, b, house_b)
            or sign_exchange(a, sign_a, b, sign_b, doctrine))


# ─────────────────────────────────────────────────────────────────────────────
# LOCK 2 · JAIMINI RĀŚI-DṚṢṬI — SIGN TO SIGN, NOT GRAHA-DṚṢṬI
# ─────────────────────────────────────────────────────────────────────────────

#: Sign modality by 0-based index: movable 0,3,6,9 · fixed 1,4,7,10 ·
#: dual 2,5,8,11. The pattern is exactly `sign_index % 3`.
MOVABLE_SIGNS: FrozenSet[int] = frozenset({0, 3, 6, 9})
FIXED_SIGNS: FrozenSet[int] = frozenset({1, 4, 7, 10})
DUAL_SIGNS: FrozenSet[int] = frozenset({2, 5, 8, 11})

RASHI_DRISHTI_AVAILABLE = True


def rashi_drishti(source_sign: Any, target_sign: Any) -> bool:
    """Jaimini sign aspect, server-side and Founder-locked.

        movable -> every fixed sign EXCEPT the adjacent one
        fixed   -> every movable sign EXCEPT the adjacent one
        dual    -> every OTHER dual sign

    THIS IS NOT GRAHA-DṚṢṬI AND DOES NOT TOUCH IT. The locked node doctrine is
    unchanged: Rahu and Ketu still cast no independent graha-dṛṣṭi, and
    `GRAHA_DRISHTI` still has no entry for either. A node can nonetheless
    participate in Rāśi-dṛṣṭi, because this is a relation between SIGNS and the
    node is merely standing in one.

    No sign aspects itself: `movable` excludes its own class, `fixed` excludes
    its own class, and `dual` excludes itself explicitly.
    """
    src = _sign(source_sign, "source")
    tgt = _sign(target_sign, "target")
    if src in MOVABLE_SIGNS:
        return tgt in FIXED_SIGNS and tgt != (src + 1) % 12
    if src in FIXED_SIGNS:
        return tgt in MOVABLE_SIGNS and tgt != (src - 1) % 12
    return tgt in DUAL_SIGNS and tgt != src


# ─────────────────────────────────────────────────────────────────────────────
# LOCK 3A · MOOLATRIKONA IS SIGN-WIDE IN EVERY DIVISIONAL CHART
# ─────────────────────────────────────────────────────────────────────────────

#: Founder-locked Moolatrikona signs, 0-based. Sun Leo · Moon Taurus ·
#: Mars Aries · Mercury Virgo · Jupiter Sagittarius · Venus Libra ·
#: Saturn Aquarius. Nodes have none.
MOOLATRIKONA_SIGN: Dict[str, int] = {
    "Sun": 4, "Moon": 1, "Mars": 0, "Mercury": 5,
    "Jupiter": 8, "Venus": 6, "Saturn": 10,
}


def is_moolatrikona(graha: Any, sign_index: Any) -> bool:
    """SIGN-WIDE in D5 and every other varga. No intra-sign degree.

    The D1 degree-range semantics are deliberately NOT reused: D5-001 publishes
    no synthetic D5 degree, so a degree-sensitive divisional test would have to
    manufacture one. The Founder has ruled the sign alone decides it.
    """
    return MOOLATRIKONA_SIGN.get(_graha(graha, "graha")) == _sign(sign_index,
                                                                  "sign")


def debilitation_sign(graha: str, exaltation_sign: Mapping[str, int]) -> Optional[int]:
    """The sign opposite exaltation. DERIVED, not a second table.

    Debilitation is exaltation plus six in every classical source, so deriving
    it means one table can never drift against another.
    """
    exalted = exaltation_sign.get(graha)
    return None if exalted is None else (exalted + 6) % 12


#: The houses whose occupancy vetoes Strong, in any chart context.
DUSTHANA: FrozenSet[int] = frozenset({6, 8, 12})


def positive_dignity(graha: str, sign_index: int, vargottama: bool,
                     doctrine: D5Doctrine,
                     exaltation_sign: Mapping[str, int]) -> Dict[str, bool]:
    """The four positive dignity branches of the Founder Strong predicate.

    `vargottama` is passed IN rather than computed here, because the chart pair
    is load-bearing — D1/D5 for a D5 reading, D1/D9 for TRI_03 — and a function
    that chose the pair for the caller would be the unnamed generic Vargottama
    the doctrine forbids.
    """
    return {
        "exalted": exaltation_sign.get(graha) == sign_index,
        "own_sign": doctrine.sign_lords[sign_index] == graha,
        "moolatrikona": is_moolatrikona(graha, sign_index),
        "vargottama": bool(vargottama),
    }


def deterministic_negative_placement(graha: str, sign_index: int, house: int,
                                     exaltation_sign: Mapping[str, int]
                                     ) -> Dict[str, bool]:
    """The two negative branches that need no operational fact.

    Combustion is deliberately absent: it is a certified physical fact the
    caller supplies, and it is three-valued. These two are decided by placement
    alone.
    """
    return {
        "debilitated": debilitation_sign(graha, exaltation_sign) == sign_index,
        "dusthana": house in DUSTHANA,
    }
