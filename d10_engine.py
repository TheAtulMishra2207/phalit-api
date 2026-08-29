"""
d10_engine.py — D10-002 · THE SERVER-OWNED DAŚĀṀŚA MECHANICAL AUTHORITY.

MECHANICAL ONLY. This module maps, derives and grades. It interprets nothing:
no Devatā, no archetype, no house signification, no tension, no Stance,
Function or Standing, no D1×D10 and no D9×D10 handshake. Every one of those is
an explicit D10-002 deferral.

ONE MAPPING, ONE PROCESS. `d10_sign_index` is the only Daśāṁśa mapping on the
server. The browser's `D10_MATRIX` is not ported: the matrix is a precomputed
table of the rule, and the rule itself is shorter than the table and cannot
drift out of agreement with itself. D10-001 verified the browser matrix against
an independently expressed oracle in 120/120 cells, so the rule below and that
matrix are the same function; the test suite re-proves it cell by cell against
an oracle that is again independent of this file.

DOCTRINE IS INJECTED, NEVER COPIED. `D10Doctrine` carries the sign, lord and
dignity tables. They live in exactly one place in the process — the chart
engine — and are passed in at wiring time, the same idiom d4_routes and
d5_routes use. This file holds no copy of SIGNS, SIGN_LORDS, EXALTATION_SIGN,
DEBILITATION_SIGN, OWN_SIGNS, NATURAL_FRIENDS or NATURAL_ENEMIES, so a future
correction to any of them cannot leave a stale second copy here.

JAIMINI IS REUSED, NOT REIMPLEMENTED. `d5_predicates.rashi_drishti` is the
accepted server-side Rāśi-dṛṣṭi primitive (D5-005). D10 imports it. Writing a
second sign-aspect function would be exactly the defect D10-002 §15 forbids.
Nothing Parāśari touches the Jaimini block: no graha-dṛṣṭi, no special dṛṣṭi,
no conjunction.

FAIL CLOSED, EVERYWHERE. There is no `or 0`, no `.get(k, 0)` and no defaulted
sentinel anywhere in this file. A missing or malformed input raises
`D10DomainError`. A house is never 0. An unknown Chara Karaka state is never
False. `Ungraded` is a VALUE, not an absence.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Dict, FrozenSet, List, Mapping, Optional, Sequence, Tuple

# REUSED, NOT REIMPLEMENTED. The accepted server-side Jaimini primitive.
from d5_predicates import rashi_drishti

ENGINE_VERSION = "d10-engine-1.0.0"

#: Publication order. Nine grahas, nodes last.
ALL_GRAHAS: Tuple[str, ...] = ("Sun", "Moon", "Mars", "Mercury", "Jupiter",
                               "Venus", "Saturn", "Rahu", "Ketu")

#: The nodes. Graded by the two-state node policy, never by friendship.
NODES: FrozenSet[str] = frozenset({"Rahu", "Ketu"})

#: D10-002 §12 · the existing Phalit seven-graha Chara Karaka set. Rahu is NOT
#: a member and no node is. Declared as an ordered tuple only so the module has
#: a stable membership list; ORDER CARRIES NO MEANING AND IS NEVER A TIEBREAK.
CHARA_KARAKA_GRAHAS: Tuple[str, ...] = ("Sun", "Moon", "Mars", "Mercury",
                                        "Jupiter", "Venus", "Saturn")

#: Chara Karaka resolution states. The contract must keep all three distinct:
#: AMBIGUOUS is a determinate finding, not missing data.
CK_RESOLVED = "RESOLVED"
CK_AMBIGUOUS = "AMBIGUOUS"
CK_INVALID = "INVALID"

#: D10-002 §9 · the complete D10 publication dignity vocabulary. Mūlatrikoṇa is
#: deliberately ABSENT: it is a degree-bound D1 natal state and a Daśāṁśa
#: position has no degree, so it is not expressible here at all rather than
#: being computed and then suppressed.
UCHCHA = "Uchcha"
SVA = "Sva"
MITRA = "Mitra"
SAMA = "Sama"
SHATRU = "Shatru"
NEECHA = "Neecha"
UNGRADED = "Ungraded"

SEVEN_GRAHA_DIGNITIES: FrozenSet[str] = frozenset(
    {UCHCHA, SVA, MITRA, SAMA, SHATRU, NEECHA})
NODE_DIGNITIES: FrozenSet[str] = frozenset({UCHCHA, NEECHA, UNGRADED})

#: Each rāśi is cut into ten portions of this width.
PORTION_DEGREES = 3.0
PORTION_COUNT = 10

#: 1 degree = 3600 arcseconds. The one place this factor appears.
ARCSECONDS_PER_DEGREE = 3600


class D10DomainError(ValueError):
    """An input is missing, malformed, or outside its domain. Never repaired,
    never defaulted, never silently converted into a confident value."""


# ─────────────────────────────────────────────────────────────────────────────
# INJECTED DOCTRINE
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class D10Doctrine:
    """The chart engine's own tables, passed in at wiring time.

    Every field is REQUIRED. There is no default anywhere in this class: an
    unconfigured deployment must fail at wiring, not serve a D10 layer graded
    against an empty table.
    """
    signs: Sequence[str]
    sign_abbr: Sequence[str]
    sign_lords: Sequence[str]
    exaltation_sign: Mapping[str, int]
    debilitation_sign: Mapping[str, int]
    own_signs: Mapping[str, Sequence[int]]
    natural_friends: Mapping[str, Sequence[str]]
    natural_enemies: Mapping[str, Sequence[str]]
    node_exaltation_sign: Mapping[str, int]
    node_debilitation_sign: Mapping[str, int]

    def validate(self) -> None:
        for name, seq in (("signs", self.signs), ("sign_abbr", self.sign_abbr),
                          ("sign_lords", self.sign_lords)):
            if len(seq) != 12:
                raise D10DomainError(f"doctrine.{name} must have 12 entries")
        for graha in CHARA_KARAKA_GRAHAS:
            if graha not in self.exaltation_sign or graha not in self.debilitation_sign:
                raise D10DomainError(f"doctrine lacks exaltation/debilitation for {graha}")
            if graha not in self.own_signs:
                raise D10DomainError(f"doctrine lacks own signs for {graha}")
        for node in sorted(NODES):
            if node not in self.node_exaltation_sign or node not in self.node_debilitation_sign:
                raise D10DomainError(f"doctrine lacks node dignity signs for {node}")


# ─────────────────────────────────────────────────────────────────────────────
# STRICT READERS
# ─────────────────────────────────────────────────────────────────────────────
# `type(v) is not int` rather than isinstance: bool is an int subclass in
# Python, and True would otherwise pass as Taurus. The same trap the accepted
# graha_yuddha primitive documents.

def _sign_index(value: Any, where: str) -> int:
    if type(value) is not int or not 0 <= value <= 11:
        raise D10DomainError(f"{where}: sign_index must be an integer 0-11, got {value!r}")
    return value


def _degree_in_sign(value: Any, where: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise D10DomainError(f"{where}: degree must be numeric, got {value!r}")
    v = float(value)
    if not 0.0 <= v < 30.0:
        raise D10DomainError(f"{where}: degree must be in [0, 30), got {v!r}")
    return v


def _bool(value: Any, where: str, field: str) -> bool:
    if not isinstance(value, bool):
        raise D10DomainError(
            f"{where}.{field} must be a boolean, got {type(value).__name__} {value!r}; "
            f"the engine will not coerce")
    return value


def _required(record: Mapping[str, Any], key: str, where: str) -> Any:
    if not isinstance(record, Mapping):
        raise D10DomainError(f"{where} is not an object")
    if key not in record:
        raise D10DomainError(f"{where} lacks required field {key!r}")
    return record[key]


# ─────────────────────────────────────────────────────────────────────────────
# 1 · THE DAŚĀṀŚA MAPPING
# ─────────────────────────────────────────────────────────────────────────────

def d10_sign_index(degree_in_sign: Any, sign_index: Any, where: str = "graha") -> int:
    """The accepted Parāśari Daśāṁśa rule, stated once.

        each rāśi is cut into ten portions of 3 degrees
        ODD  signs begin the sequence from THEMSELVES
        EVEN signs begin from the 9TH SIGN from themselves

    `sign_index` is 0-based, so Aries (the 1st, an odd sign) is index 0 and the
    odd signs are the EVEN indices. The 9th sign from a sign is that sign + 8.

    THE ONLY CALLERS ARE `calc_planet_data` AND `calc_lagna`, both at the
    full-precision seam before display rounding. `/d10/prepare` consumes the
    certified result and never calls this function, so there is one mapping in
    the process and exactly one place it can be fed from.

    NO CLAMP. The browser reached the tenth portion through `Math.min(...,9)`,
    which silently absorbed an out-of-domain degree. Here `_degree_in_sign`
    rejects anything outside [0, 30) first, so the portion is arithmetically in
    0..9 and no clamp is needed. A clamp that can never fire is worse than none:
    it hides the input that should have been refused.
    """
    deg = _degree_in_sign(degree_in_sign, where)
    si = _sign_index(sign_index, where)
    portion = int(deg // PORTION_DEGREES)
    if not 0 <= portion < PORTION_COUNT:
        # Unreachable given the domain check above. Present because an
        # unreachable refusal is cheap and a wrong publication is not.
        raise D10DomainError(f"{where}: portion {portion} outside 0-9 for degree {deg!r}")
    odd_sign = (si % 2 == 0)
    start = si if odd_sign else (si + 8) % 12
    return (start + portion) % 12


def d10_house(d10_graha_sign: int, d10_lagna_sign: int) -> int:
    """Whole-sign house of a D10 position, counted from the D10 Lagna.

    Returns 1..12. NEVER 0. There is no sentinel: a caller that cannot supply
    both signs has already raised."""
    g = _sign_index(d10_graha_sign, "d10_house.graha_sign")
    l = _sign_index(d10_lagna_sign, "d10_house.lagna_sign")
    house = ((g - l) % 12) + 1
    if not 1 <= house <= 12:
        raise D10DomainError(f"derived house {house} outside 1-12")
    return house


# ─────────────────────────────────────────────────────────────────────────────
# 2 · D10 PUBLICATION DIGNITY
# ─────────────────────────────────────────────────────────────────────────────

def d10_dignity(graha: str, sign_index: int, doctrine: D10Doctrine) -> str:
    """Sign-based D10 publication dignity, per the locked Founder policy.

    NO DEGREE IS ACCEPTED OR INVENTED. The signature takes no degree, so
    `get_dignity(graha, sign, 0)` — the artefact ERRATA-01 and the CORR-01
    rulings exist to prevent — is not expressible through this function. Five of
    the seven Mūlatrikoṇa signs are that graha's own sign and the other two are
    its exaltation sign, so 'Mūlatrikoṇa normalizes to Sva' is exactly the master
    rule WITH THE MŪLATRIKOṆA BRANCH ABSENT. There is no branch to suppress
    because there is no branch.

    NOTE FOR A FUTURE READER. `d5_predicates.MOOLATRIKONA_SIGN` and its LOCK 3A
    state that Mūlatrikoṇa is sign-wide in every divisional chart. That is D5
    doctrine and it governs D5. D10's Founder ruling is different and governs
    D10. Neither is touched by the other, and D10 does not import that table.

    NODES: Uchcha, Neecha or Ungraded, and nothing else. The seven-graha
    friendship matrix is never consulted for a node — not as a fallback, not as
    a default. `Ungraded` is the answer for every other sign, and it is a
    VALUE, not an absence.
    """
    si = _sign_index(sign_index, f"d10_dignity[{graha}]")
    if graha in NODES:
        if doctrine.node_exaltation_sign[graha] == si:
            return UCHCHA
        if doctrine.node_debilitation_sign[graha] == si:
            return NEECHA
        return UNGRADED
    if graha not in CHARA_KARAKA_GRAHAS:
        raise D10DomainError(f"unknown graha {graha!r}")

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
# 3 · THE ARCSECOND BASIS
# ─────────────────────────────────────────────────────────────────────────────

def half_up_to_int(value: Decimal) -> int:
    """THE ROUNDING PRIMITIVE, NAMED. Decimal.quantize with ROUND_HALF_UP.

    Founder-ratified semantics for `karaka_arcsecond`. Stated as its own
    function so the rule is a thing that can be pointed at and tested directly,
    rather than an argument buried in an expression.

        1000.49 -> 1000
        1000.50 -> 1001
        1000.51 -> 1001
        1001.50 -> 1002

    PARITY HAS NO EFFECT. 1000.5 and 1001.5 both go UP. Python's built-in
    round() is half-to-EVEN and gives 1000 for the first of those, which is
    doctrinally invalid here: it would make a tie's outcome depend on the
    parity of the neighbouring integer, which is exactly the arbitrary,
    chart-independent tiebreak the Chara Karaka ruling outlaws.

    Decimal is used rather than `math.floor(v + 0.5)` because adding 0.5 in
    binary floating point can carry a value across the boundary before the
    floor sees it. Decimal(float) is exact — it takes the true binary value of
    the float, not a decimal approximation — so the comparison against .5 is
    made against the number actually held.
    """
    if not isinstance(value, Decimal):
        raise D10DomainError(
            f"half_up_to_int takes a Decimal, got {type(value).__name__}")
    return int(value.quantize(Decimal(1), rounding=ROUND_HALF_UP))


def to_karaka_arcsecond(full_precision_degree_within_sign: Any) -> int:
    """`ROUND_HALF_UP(full_precision_degree_within_sign x 3600)`.

    Computed from the unrounded natal degree-within-sign, before any display
    rounding, on the server, for the seven eligible Chara Karaka grahas.

    The rounding semantics are NOT inherited from the language. They are the
    named primitive above. See its docstring for why half-to-even is refused.

    The domain is [0, 30), so the result is in [0, 108000) and half-up and
    half-away-from-zero coincide. No negative case exists and none is invented.
    """
    deg = _degree_in_sign(full_precision_degree_within_sign, "karaka_arcsecond")
    return half_up_to_int(Decimal(deg) * ARCSECONDS_PER_DEGREE)


# ─────────────────────────────────────────────────────────────────────────────
# 4 · CHARA KARAKA
# ─────────────────────────────────────────────────────────────────────────────

def chara_karaka_state(karaka_arcseconds: Mapping[str, Any]) -> Dict[str, Any]:
    """Rank the seven eligible grahas on the server-owned integer arcsecond.

    THE TIE RULE, EXACTLY AS LOCKED. If ANY TWO of the seven eligible grahas
    share an integer arcsecond, the state is AMBIGUOUS — not only a tie that
    happens to straddle the AK/AmK boundary. The ticket says "any two eligible
    Chara Karaka grahas" and that is implemented literally: a tie between the
    fifth and sixth ranked grahas returns AMBIGUOUS with no AK and no AmK.

    NO TIEBREAK OF ANY KIND EXISTS IN THIS FUNCTION. There is no sort on a
    secondary key, no array order, no planet priority, no epsilon, no fractional
    degree. The sort below runs only AFTER the tie check has passed, so it can
    never be reached with equal keys and can never silently decide anything.

    NODES DO NOT PARTICIPATE. Rahu and Ketu are not in CHARA_KARAKA_GRAHAS and
    are not read from the mapping. A caller that passes them is not rejected —
    they are simply not eligible — but a test asserts they cannot influence the
    outcome.

    Returns one of three states and never conflates them:
        INVALID   — an eligible graha's arcsecond is missing or malformed
        AMBIGUOUS — two or more eligible grahas share an integer arcsecond
        RESOLVED  — a strict total order exists over all seven
    """
    values: Dict[str, int] = {}
    for graha in CHARA_KARAKA_GRAHAS:
        if graha not in karaka_arcseconds:
            return {"state": CK_INVALID, "reason": "missing_karaka_arcsecond",
                    "atmakaraka": None, "amatyakaraka": None, "ranking": None,
                    "tied_grahas": None}
        raw = karaka_arcseconds[graha]
        if type(raw) is not int or raw < 0:
            return {"state": CK_INVALID, "reason": "malformed_karaka_arcsecond",
                    "atmakaraka": None, "amatyakaraka": None, "ranking": None,
                    "tied_grahas": None}
        values[graha] = raw

    seen: Dict[int, List[str]] = {}
    for graha, arcsec in values.items():
        seen.setdefault(arcsec, []).append(graha)
    tied = sorted(g for group in seen.values() if len(group) > 1 for g in group)
    if tied:
        return {"state": CK_AMBIGUOUS, "reason": "equal_karaka_arcsecond",
                "atmakaraka": None, "amatyakaraka": None, "ranking": None,
                "tied_grahas": tied}

    # Reached only when every key is distinct, so this sort decides nothing a
    # tiebreak could have decided.
    order = sorted(values, key=lambda g: values[g], reverse=True)
    return {"state": CK_RESOLVED, "reason": None,
            "atmakaraka": order[0], "amatyakaraka": order[1],
            "ranking": [{"planet": g, "rank": i + 1,
                         "karaka_arcsecond": values[g]}
                        for i, g in enumerate(order)],
            "tied_grahas": None}


# ─────────────────────────────────────────────────────────────────────────────
# 5 · THE ONE PUBLIC ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

def build_d10_facts(lagna: Mapping[str, Any],
                    planets: Mapping[str, Mapping[str, Any]],
                    doctrine: D10Doctrine) -> Dict[str, Any]:
    """Every mechanical D10 fact this flight is authorised to publish.

    Reads ONLY these certified snapshot fields, and names them here rather than
    reaching for whatever happens to be present:

        lagna:  sign_index, d10_sign_index
        graha:  sign_index, d10_sign_index, retrograde, combust,
                karaka_arcsecond

    `degree` IS DELIBERATELY NOT IN THE READ SET. It is the rounded public
    value, and every D10 fact that once came from it now arrives already
    mapped.

    `karaka_arcsecond` and `d10_sign_index` are both READ, never recomputed.
    The chart engine produces both from the unrounded degree before display
    rounding; deriving either here from the published four-decimal `degree`
    would reintroduce exactly the precision loss they exist to avoid.

    They fail differently, and deliberately. A missing `karaka_arcsecond`
    yields Chara Karaka state INVALID and the chart is still served, because
    placements, houses, lordships and dignity are all unaffected by it. A
    missing `d10_sign_index` RAISES, because without it there is no D10
    placement at all and there is nothing partial worth publishing.
    """
    doctrine.validate()

    lagna_si = _sign_index(_required(lagna, "sign_index", "lagna"), "lagna")
    # CONSUMED, NOT RECOMPUTED. The chart engine mapped this at the
    # full-precision seam; the published `degree` beside it is round(..., 4)
    # and re-deriving from it can land on the wrong side of a 3-degree
    # boundary, or refuse a true 29.99995+ that published as 30.0000. This
    # function does not call d10_sign_index at all.
    d10_lagna_si = _sign_index(_required(lagna, "d10_sign_index", "lagna"),
                               "lagna.d10_sign_index")

    grahas: Dict[str, Dict[str, Any]] = {}
    karaka_arcseconds: Dict[str, Any] = {}
    for graha in ALL_GRAHAS:
        if graha not in planets:
            raise D10DomainError(f"snapshot is missing graha {graha!r}")
        rec = planets[graha]
        si = _sign_index(_required(rec, "sign_index", graha), graha)
        # CONSUMED, NOT RECOMPUTED — see the lagna note above. `degree` is not
        # read here at all, so the rounded value cannot reach the mapping.
        d10_si = _sign_index(_required(rec, "d10_sign_index", graha),
                             f"{graha}.d10_sign_index")
        house = d10_house(d10_si, d10_lagna_si)
        grahas[graha] = {
            "planet": graha,
            "d10_sign_index": d10_si,
            "d10_sign": doctrine.signs[d10_si],
            "d10_sign_abbr": doctrine.sign_abbr[d10_si],
            "d10_house": house,
            "d10_lord": doctrine.sign_lords[d10_si],
            "d10_dignity": d10_dignity(graha, d10_si, doctrine),
            # Mechanical carry-through. Zero interpretive weight: no branch in
            # this file reads either value.
            "retrograde": _bool(_required(rec, "retrograde", graha), graha, "retrograde"),
            "combust": _bool(_required(rec, "combust", graha), graha, "combust"),
        }
        if graha in CHARA_KARAKA_GRAHAS and "karaka_arcsecond" in rec:
            karaka_arcseconds[graha] = rec["karaka_arcsecond"]

    houses = [{"house": h,
               "sign_index": (d10_lagna_si + h - 1) % 12,
               "sign": doctrine.signs[(d10_lagna_si + h - 1) % 12],
               "sign_abbr": doctrine.sign_abbr[(d10_lagna_si + h - 1) % 12],
               "lord": doctrine.sign_lords[(d10_lagna_si + h - 1) % 12],
               "occupants": sorted(g for g in ALL_GRAHAS
                                   if grahas[g]["d10_house"] == h)}
              for h in range(1, 13)]

    ck = chara_karaka_state(karaka_arcseconds)

    ak_block: Optional[Dict[str, Any]] = None
    amk_block: Optional[Dict[str, Any]] = None
    jaimini: Dict[str, Any]
    if ck["state"] == CK_RESOLVED:
        def karaka_block(planet: str) -> Dict[str, Any]:
            g = grahas[planet]
            return {"planet": planet,
                    "karaka_arcsecond": karaka_arcseconds[planet],
                    "d10_sign": g["d10_sign"],
                    "d10_sign_index": g["d10_sign_index"],
                    "d10_house": g["d10_house"]}
        ak_block = karaka_block(ck["atmakaraka"])
        amk_block = karaka_block(ck["amatyakaraka"])
        ak_si = ak_block["d10_sign_index"]
        amk_si = amk_block["d10_sign_index"]
        # JAIMINI ONLY. rashi_drishti is a relation between SIGNS. Nothing
        # Parāśari — no graha-dṛṣṭi, no special dṛṣṭi, no conjunction, no orb —
        # is consulted, and mutuality is evaluated in BOTH directions rather
        # than assumed symmetric.
        jaimini = {"available": True,
                   "ak_aspects_amk": rashi_drishti(ak_si, amk_si),
                   "amk_aspects_ak": rashi_drishti(amk_si, ak_si),
                   "ak_amk_mutual_rashi_drishti": (rashi_drishti(ak_si, amk_si)
                                                   and rashi_drishti(amk_si, ak_si)),
                   "unavailable_reason": None}
    else:
        # UNKNOWN != FALSE. With no resolved AK/AmK identity there is no
        # relation to report, and reporting `false` would assert that the two
        # do not aspect one another — a claim about grahas that have not been
        # identified. The booleans are ABSENT, not False.
        jaimini = {"available": False,
                   "ak_aspects_amk": None,
                   "amk_aspects_ak": None,
                   "ak_amk_mutual_rashi_drishti": None,
                   "unavailable_reason": ("chara_karaka_" + ck["state"].lower())}

    return {
        "engine_version": ENGINE_VERSION,
        "lagna": {"d10_sign_index": d10_lagna_si,
                  "d10_sign": doctrine.signs[d10_lagna_si],
                  "d10_sign_abbr": doctrine.sign_abbr[d10_lagna_si],
                  "d10_lord": doctrine.sign_lords[d10_lagna_si],
                  "source_sign_index": lagna_si,
                  "source_sign": doctrine.signs[lagna_si]},
        "grahas": grahas,
        "houses": houses,
        "chara_karaka": {"state": ck["state"],
                         "reason": ck["reason"],
                         "eligible_planets": list(CHARA_KARAKA_GRAHAS),
                         "rahu_eligible": False,
                         "ketu_eligible": False,
                         "tied_grahas": ck["tied_grahas"],
                         "ranking": ck["ranking"]},
        "atmakaraka": ak_block,
        "amatyakaraka": amk_block,
        "jaimini": jaimini,
    }
