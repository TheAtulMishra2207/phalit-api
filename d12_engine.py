"""d12_engine.py — Phalit.ai D12 Dvādaśāṁśa mechanical fact authority.

D12-003. The ONE D12 mapping in the process, mirroring the accepted
d10_engine discipline (strict readers, domain rejection before arithmetic,
no clamp, no sentinel values) with D12's OWN accepted division rule.

THE ACCEPTED PARĀŚARI DVĀDAŚĀṀŚA RULE, STATED ONCE
    each rāśi is cut into TWELVE portions of 2°30′
    every sign begins the sequence FROM ITSELF and runs forward

This is deliberately NOT the D10 rule (odd from self, even from the 9th) and
NOT the D20 rule (movable/fixed/dual anchors). D12-001 Fixture 1 verified that
this forward-from-own-sign rule, applied to the chart of record, reproduces the
frozen D12 Format Specification's specimen cell for cell (D12 Lagna Gemini,
Mercury first-slice vargottama, Sun Virgo H4, Moon Scorpio H6 …). A future
reader who "fixes" this to an anchored rule is introducing the exact class of
error the D20 correction history records in main.py — do not.

THE ONLY INTENDED CALLERS of d12_sign_index are `calc_planet_data` and
`calc_lagna` in main.py, both at the full-precision seam BEFORE display
rounding. The published `degree` is round(…, 4); rounding to four decimals and
then flooring at a 2°30′ edge disagrees with flooring once from the true value
inside ±0.00005° of each of the eleven interior boundaries, and the same edge
flips first-slice vargottama at 2°30′ exactly. The consumer reads the published
`d12_sign_index` field. It never re-derives the placement from the published
degree. (D12-001 finding F-13; same defect class D10-002 §10 records for the
Karaka arcsecond.)

NO CLAMP. The legacy browser mapping reached the twelfth portion through
`Math.min(…, 11)`, which silently absorbed an out-of-domain degree — D12-001
finding F-10: null coerced to 0°, NaN rendered as the literal string
"undefined". Here `_degree_in_sign` rejects anything outside [0, 30) first, so
the portion is arithmetically in 0..11 and no clamp is needed. A clamp that can
never fire is worse than none: it hides the input that should have been
refused.

NO DIGNITY, NO DOCTRINE TABLE. This module publishes placement mechanics only:
slice, sign, whole-sign house, first-slice vargottama. D12 interpretive dignity
is governed by the locked FR-004 ruling (nodes UNGRADED for sign dignity in
D12) and belongs to a later flight with its own injected D12 doctrine — it must
NOT reuse d10_engine.d10_dignity, whose node branch carries D10's Founder
policy. Nothing here consults a dignity table, so nothing here can violate
FR-004.
"""

from __future__ import annotations

from typing import Any

__all__ = [
    "D12DomainError",
    "PORTION_DEGREES",
    "PORTION_COUNT",
    "d12_sign_index",
    "d12_house",
    "is_d12_first_slice_vargottama",
    "d12_degree_in_sign",
]

# 2.5 is a dyadic rational (5/2) and every interior boundary (2.5, 5.0 … 27.5)
# is exactly representable in binary floating point, so `deg // 2.5` at an
# exact boundary cannot drift. Verified explicitly in test_d12_engine.py.
PORTION_DEGREES = 2.5
PORTION_COUNT = 12


class D12DomainError(ValueError):
    """An input outside the mechanical domain. Raised, never absorbed."""


# ─────────────────────────────────────────────────────────────────────────────
# STRICT READERS
# `type(v) is not int` rather than isinstance: bool is an int subclass in
# Python, and True would otherwise pass as Taurus — the same trap the accepted
# graha_yuddha primitive and d10_engine both document.
# ─────────────────────────────────────────────────────────────────────────────

def _sign_index(value: Any, where: str) -> int:
    if type(value) is not int or not 0 <= value <= 11:
        raise D12DomainError(f"{where}: sign_index must be an int 0..11, got {value!r}")
    return value


def _degree_in_sign(value: Any, where: str) -> float:
    # bool is rejected for the same subclass reason as above; NaN fails every
    # comparison and is rejected by the domain check rather than propagating.
    if type(value) not in (int, float) or not 0.0 <= float(value) < 30.0:
        raise D12DomainError(
            f"{where}: degree_in_sign must be a number in [0, 30), got {value!r}")
    return float(value)


# ─────────────────────────────────────────────────────────────────────────────
# 1 · THE MAPPING
# ─────────────────────────────────────────────────────────────────────────────

def d12_sign_index(degree_in_sign: Any, sign_index: Any, where: str = "graha") -> int:
    """D12 sign of a body from its D1 sign and full-precision degree-in-sign.

    portion = floor(degree / 2°30′), left-closed: 2.5 belongs to the second
    slice, 0.0 to the first, and 30.0 is not in the domain at all. The slice
    sequence starts from the body's own sign and runs forward — see the module
    docstring for why this must never be "corrected" to an anchored rule.
    """
    deg = _degree_in_sign(degree_in_sign, where)
    si = _sign_index(sign_index, where)
    portion = int(deg // PORTION_DEGREES)
    if not 0 <= portion < PORTION_COUNT:
        # Unreachable given the domain check above. Present because an
        # unreachable refusal is cheap and a wrong publication is not.
        raise D12DomainError(
            f"{where}: portion {portion} outside 0-{PORTION_COUNT - 1} for degree {deg!r}")
    return (si + portion) % 12


def d12_house(d12_graha_sign: Any, d12_lagna_sign: Any) -> int:
    """Whole-sign house of a D12 position, counted from the D12 Lagna.

    Returns 1..12. NEVER 0. There is no sentinel: a caller that cannot supply
    both signs has already raised. (The legacy browser rendered an absent graha
    as `H0 · — · Sama Rashi` — D12-001 finding F-09. Absence is an error here,
    not a value.)
    """
    g = _sign_index(d12_graha_sign, "d12_house.graha_sign")
    l = _sign_index(d12_lagna_sign, "d12_house.lagna_sign")
    house = ((g - l) % 12) + 1
    if not 1 <= house <= 12:
        raise D12DomainError(f"derived house {house} outside 1-12")
    return house


def d12_degree_in_sign(degree_in_sign: Any, where: str = "graha") -> float:
    """The body's degree WITHIN its D12 sign, 0.0 <= d < 30.0.

    D12-005-CORR-01. Each 2°30' slice maps onto a whole 30° sign, so the
    position inside the slice scales by exactly 12:

        d12_degree = (degree_in_sign mod 2.5) * 12

    THE ONE IMPLEMENTATION. Like `d12_sign_index`, its only intended callers are
    `calc_lagna` and `calc_planet_data` at the FULL-PRECISION seam, before
    display rounding. Deriving it later from the published 4-decimal `degree`
    reintroduces exactly the quantisation the seam exists to remove — and here
    the error is amplified twelvefold, because a ±0.00005° error in the natal
    degree becomes ±0.0006° in the D12 degree, which is then compared against
    FR-004's 5° Lagna-axis orb.

    2.5 is dyadic, so the modulus is exact at every slice boundary and a body
    exactly on a boundary returns 0.0 — the first moment of the next D12 sign,
    consistent with the half-open [0, 2.5) ownership `d12_sign_index` applies.
    """
    deg = _degree_in_sign(degree_in_sign, where)
    out = (deg % PORTION_DEGREES) * PORTION_COUNT
    if not 0.0 <= out < 30.0:
        # Unreachable given the domain check; kept for the same reason the
        # portion guard above is kept.
        raise D12DomainError(f"{where}: derived D12 degree {out!r} outside [0, 30)")
    return out


def is_d12_first_slice_vargottama(degree_in_sign: Any, where: str = "graha") -> bool:
    """First-slice vargottama: the body sits in the first 2°30′ of its sign, so
    its D12 sign equals its D1 sign. Strict less-than: 2°30′.0000 exactly is the
    SECOND slice and is not vargottama. Evaluated at full precision, before the
    4-decimal display rounding — a true 2.49995° must remain vargottama even
    though it publishes as 2.5000 (D12-001 Fixture 2).
    """
    return _degree_in_sign(degree_in_sign, where) < PORTION_DEGREES


# ─────────────────────────────────────────────────────────────────────────────
# 2 · D12 SIGN DIGNITY
#
# Sign-based, degree-free, and governed by the LOCKED D12 rulings — NOT by
# D10's. Two differences are load-bearing and must never be "harmonised":
#
#   1. THERE IS NO MŪLATRIKOṆA STATE IN D12. The frozen D12 vocabulary is
#      exactly Uchcha / Sva / Mitra / Sama / Shatru / Neecha. No branch for it
#      exists below, so none can fire; `main.MOOLATRIKONA` is never imported.
#      (d5_predicates.MOOLATRIKONA_SIGN and its LOCK 3A state that Mūlatrikoṇa
#      is sign-wide in every divisional chart. That is D5 doctrine and it
#      governs D5. D12's Founder ruling is different and governs D12.)
#
#   2. RAHU AND KETU ARE ALWAYS UNGRADED — FR-004, for all twelve signs. D10
#      grades the nodes Uchcha/Neecha in two signs each from its own
#      Founder-locked BPHS Ch.47 tables. Reusing `d10_engine.d10_dignity` here
#      would import that policy and violate FR-004. D12Doctrine therefore
#      carries NO node tables at all: the violation is not merely rejected,
#      it is unexpressible.
#
# `Ungraded` is a VALUE, not an absence, and it is never numerically ordered
# alongside the six graded states (see DIGNITY_STATES / GRADED_STATES).
# ─────────────────────────────────────────────────────────────────────────────

from dataclasses import dataclass          # noqa: E402
from typing import Dict, List, Mapping, Sequence, Tuple   # noqa: E402

UCHCHA, SVA, MITRA, SAMA, SHATRU, NEECHA = (
    "Uchcha", "Sva", "Mitra", "Sama", "Shatru", "Neecha")
UNGRADED = "Ungraded"

# The six graded states, in the frozen order. Ungraded is deliberately OUTSIDE
# this tuple: it has no rank, and any consumer that sorts or compares dignity
# must use this sequence and handle Ungraded separately.
GRADED_STATES: Tuple[str, ...] = (UCHCHA, SVA, MITRA, SAMA, SHATRU, NEECHA)
DIGNITY_STATES: Tuple[str, ...] = GRADED_STATES + (UNGRADED,)

CLASSICAL_GRAHAS: Tuple[str, ...] = (
    "Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn")
NODES: Tuple[str, ...] = ("Rahu", "Ketu")
D12_GRAHAS: Tuple[str, ...] = CLASSICAL_GRAHAS + NODES

__all__ += [
    "UCHCHA", "SVA", "MITRA", "SAMA", "SHATRU", "NEECHA", "UNGRADED",
    "GRADED_STATES", "DIGNITY_STATES", "CLASSICAL_GRAHAS", "NODES",
    "D12_GRAHAS", "D12Doctrine", "d12_dignity", "build_d12_facts",
]


@dataclass(frozen=True)
class D12Doctrine:
    """The chart engine's master tables, passed in at wiring time.

    Every field is REQUIRED and there is no default: an unconfigured deployment
    must fail at wiring, not serve a D12 layer graded against an empty table.
    The tables are NOT copied into this module — one copy in the process.

    Note what is absent by design: no Mūlatrikoṇa table, and no node
    exaltation/debilitation tables. FR-004 makes the nodes ungraded in D12, so
    there is nothing for such a table to say.
    """
    signs: Sequence[str]
    sign_lords: Sequence[str]
    exaltation_sign: Mapping[str, int]
    debilitation_sign: Mapping[str, int]
    own_signs: Mapping[str, Sequence[int]]
    natural_friends: Mapping[str, Sequence[str]]
    natural_enemies: Mapping[str, Sequence[str]]

    def validate(self) -> "D12Doctrine":
        for name, seq in (("signs", self.signs), ("sign_lords", self.sign_lords)):
            if len(seq) != 12:
                raise D12DomainError(f"doctrine.{name} must have 12 entries")
        for graha in CLASSICAL_GRAHAS:
            for table in ("exaltation_sign", "debilitation_sign", "own_signs",
                          "natural_friends", "natural_enemies"):
                if graha not in getattr(self, table):
                    raise D12DomainError(f"doctrine.{table} lacks {graha}")
        return self


def d12_dignity(graha: str, sign_index: Any, doctrine: D12Doctrine) -> str:
    """Sign-based D12 dignity. Returns one of DIGNITY_STATES.

    NO DEGREE IS ACCEPTED OR INVENTED. The signature takes no degree, so
    `get_dignity(graha, sign, 0)` — the legacy degree-blind call D12-001 finding
    F-11 records in the browser — is not expressible through this function.
    """
    si = _sign_index(sign_index, f"d12_dignity[{graha}]")
    if graha in NODES:
        # FR-004. Every sign, without exception, and without consulting the
        # seven-graha friendship matrix as a fallback.
        return UNGRADED
    if graha not in CLASSICAL_GRAHAS:
        raise D12DomainError(f"unknown graha {graha!r}")
    if doctrine.debilitation_sign[graha] == si:
        return NEECHA
    if doctrine.exaltation_sign[graha] == si:
        return UCHCHA
    if si in doctrine.own_signs[graha] or doctrine.sign_lords[si] == graha:
        return SVA
    lord = doctrine.sign_lords[si]
    if lord in doctrine.natural_friends[graha]:
        return MITRA
    if lord in doctrine.natural_enemies[graha]:
        return SHATRU
    return SAMA


# ─────────────────────────────────────────────────────────────────────────────
# 3 · THE DETERMINISTIC FACT BUILDER
# ─────────────────────────────────────────────────────────────────────────────

def _required_certified_degree(record: Mapping[str, Any], where: str) -> float:
    """Read the CERTIFIED d12_degree_in_sign and nothing else.

    FAIL CLOSED, for the same reason as the sign index and more sharply: the
    published natal `degree` is round(..., 4) and the D12 scaling multiplies its
    error by twelve, which then meets FR-004's 5° orb. There is no fallback.
    """
    if "d12_degree_in_sign" not in record:
        raise D12DomainError(
            f"{where}: certified d12_degree_in_sign absent — refusing to derive "
            f"it from the rounded degree")
    value = record["d12_degree_in_sign"]
    if type(value) not in (int, float) or not 0.0 <= float(value) < 30.0:
        raise D12DomainError(
            f"{where}.d12_degree_in_sign must be a number in [0, 30), got {value!r}")
    return float(value)


def _required_certified_sign(record: Mapping[str, Any], where: str) -> int:
    """Read the CERTIFIED d12_sign_index and nothing else.

    FAIL CLOSED. If the field is missing or malformed this raises. It must
    NEVER fall back to recomputing from the published `degree`: that value is
    round(…, 4) and disagrees with the true placement within ±0.00005° of every
    2°30′ boundary, which is the entire reason the seam exists.
    """
    if "d12_sign_index" not in record:
        raise D12DomainError(
            f"{where}: certified d12_sign_index absent — refusing to derive it "
            f"from the rounded degree")
    return _sign_index(record["d12_sign_index"], f"{where}.d12_sign_index")


def build_d12_facts(lagna: Mapping[str, Any],
                    planets: Mapping[str, Mapping[str, Any]],
                    doctrine: D12Doctrine) -> Dict[str, Any]:
    """Mechanical D12 facts from a certified /chart payload.

    Consumes the certified `d12_sign_index` on the lagna and on each of the
    nine grahas. Derives houses, dignity, first-slice vargottama, and the twelve
    house rows. Computes no astronomy and reads no degree.
    """
    doctrine.validate()
    lagna_si = _required_certified_sign(lagna, "lagna")
    lagna_deg = _required_certified_degree(lagna, "lagna")

    placements: Dict[str, Dict[str, Any]] = {}
    for graha in D12_GRAHAS:
        if graha not in planets:
            raise D12DomainError(f"planets lacks {graha}")
        rec = planets[graha]
        si = _required_certified_sign(rec, graha)
        deg = _required_certified_degree(rec, graha)
        d1_si = _sign_index(rec.get("sign_index"), f"{graha}.sign_index")
        placements[graha] = {
            "d12_degree_in_sign": deg,
            "graha": graha,
            "d1_sign_index": d1_si,
            "d12_sign_index": si,
            "d12_sign": doctrine.signs[si],
            "slice": ((si - d1_si) % 12) + 1,
            "house": d12_house(si, lagna_si),
            "dignity_state": d12_dignity(graha, si, doctrine),
            # Vargottama is the SIGN identity, exactly as the ruling states.
            # Equivalent to slice 1 under this mapping, and proven so in the
            # test suite rather than assumed here.
            "vargottama": si == d1_si,
        }

    houses: List[Dict[str, Any]] = []
    for house in range(1, 13):
        si = (lagna_si + house - 1) % 12
        houses.append({
            "house": house,
            "sign_index": si,
            "sign": doctrine.signs[si],
            "lord": doctrine.sign_lords[si],
            "occupants": sorted(g for g, p in placements.items()
                                if p["house"] == house),
        })

    return {
        "d12_lagna": {
            "d1_sign_index": _sign_index(lagna.get("sign_index"), "lagna.sign_index"),
            "d12_sign_index": lagna_si,
            "d12_degree_in_sign": lagna_deg,
            "d12_sign": doctrine.signs[lagna_si],
            "lagnesh": doctrine.sign_lords[lagna_si],
        },
        "placements": placements,
        "houses": houses,
    }
