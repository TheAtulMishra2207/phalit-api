"""
d5_engine.py — D5-001 · THE PURE D5 FACT CORE.

No FastAPI, no HTTP, no provider, no I/O. Every function here is a pure
transform over already-certified numbers, so the whole module is testable
without an application.

DEPENDENCY-INJECTED SHARED DOCTRINE. `D5Doctrine` carries the product's SIGNS
and SIGN_LORDS tables rather than restating them. Those two tables already exist
exactly once in the process, in main.py, and d4_core is injected with the same
pair for the same reason: a second copy here would be a second table that agrees
today and drifts later.

D5'S OWN LOCKED TABLES LIVE HERE. Sign modality, the 6-degree segment arc and
the Pancha-Tattva map are D5 doctrine, not shared product doctrine — no other
module holds a copy that this one could disagree with. They are module-level
frozen constants, stated in the same form the Founder specification states them
so that a reader can check the code against the ticket line by line.

DOMAIN GUARDS RAISE. The D4 frontend's getD4SignIdx silently returned quarter 4
for NaN, for 30 and for undefined. Nothing here returns a plausible answer for
an impossible input: `D5DomainError` is raised and the route converts it to a
neutral correlated failure.

SEGMENTATION IS EXACT, NOT FLOATING POINT. The certified in-sign degree is
carried into `Decimal` through its own string form and floor-divided by 6, so a
graha sitting exactly on 6.0000, 12.0000, 18.0000 or 24.0000 lands on the higher
segment by the half-open rule and cannot be pushed across a boundary by a binary
representation error. `int(degree / 6)` on floats was rejected for that reason.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict, List, Optional, Sequence, Tuple


class D5DomainError(ValueError):
    """An input cannot describe a real certified position. Internal only: the
    message never reaches a response."""


# ─────────────────────────────────────────────────────────────────────────────
# D5'S OWN LOCKED DOCTRINE
# ─────────────────────────────────────────────────────────────────────────────

#: Five equal segments of six degrees each. Half-open: a segment owns its lower
#: bound and not its upper.
D5_SEGMENT_ARC = Decimal(6)
D5_SEGMENT_COUNT = 5

#: Sign modality in normal zodiac sequence, indexed by D1 sign index.
#: Aries/Cancer/Libra/Capricorn movable · Taurus/Leo/Scorpio/Aquarius fixed ·
#: Gemini/Virgo/Sagittarius/Pisces dual.
MODALITY_BY_SIGN_INDEX: Tuple[str, ...] = (
    "movable", "fixed", "dual",
    "movable", "fixed", "dual",
    "movable", "fixed", "dual",
    "movable", "fixed", "dual",
)

#: Where counting begins, as an offset in signs from the source sign.
#: movable -> that sign (1st, offset 0) · fixed -> the 5th from it (offset 4) ·
#: dual -> the 9th from it (offset 8).
COUNTING_START_OFFSET: Dict[str, int] = {"movable": 0, "fixed": 4, "dual": 8}

#: Founder-locked Pancha-Tattva of the ORIGINAL 6-degree source arc, by 0-based
#: segment number. The lords are the Tattva's lords, not a lordship claim over
#: the resulting D5 sign.
TATTVA_BY_SEGMENT: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    ("Agni", ("Mars", "Sun")),
    ("Prithvi", ("Mercury",)),
    ("Vayu", ("Saturn", "Rahu")),
    ("Jala", ("Venus", "Moon")),
    ("Akasha", ("Jupiter",)),
)

#: The nine grahas D5-001 places, plus the Lagna handled separately.
ALL_GRAHAS: Tuple[str, ...] = (
    "Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu",
)

#: The seven Chara Karakas in rank order, highest traversed degree first.
CHARA_KARAKA_ORDER: Tuple[str, ...] = ("AK", "AMK", "BK", "MK", "PK", "GK", "DK")

#: Chara Karaka eligibility. RAHU AND KETU ARE EXCLUDED — this is the 7-karaka
#: system, not the 8-karaka system, and no node may ever be assigned a karaka.
CHARA_KARAKA_PLANETS: Tuple[str, ...] = (
    "Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn",
)

#: Founder priority, applied ONLY when two eligible planets are identical to the
#: full precision the certified snapshot carries. Earlier wins.
CHARA_KARAKA_TIE_PRIORITY: Tuple[str, ...] = (
    "Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn",
)


@dataclass(frozen=True)
class D5Doctrine:
    """The SHARED product tables, injected at wiring time.

    D5 holds no copy of either. `signs` and `sign_lords` are the same objects
    main.py already passes to `configure_d4_doctrine`.
    """
    signs: Sequence[str]
    sign_lords: Sequence[str]

    def __post_init__(self) -> None:
        if len(self.signs) != 12:
            raise D5DomainError("sign table is not twelve entries")
        if len(self.sign_lords) != 12:
            raise D5DomainError("sign lord table is not twelve entries")


# ─────────────────────────────────────────────────────────────────────────────
# GUARDS
# ─────────────────────────────────────────────────────────────────────────────

def _require_sign_index(value: Any, what: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise D5DomainError(f"{what} sign index is not an integer")
    if not 0 <= value <= 11:
        raise D5DomainError(f"{what} sign index is outside 0..11")
    return value


def _require_degree(value: Any, what: str) -> Decimal:
    """The certified in-sign degree, as an exact Decimal.

    Rejects bool, non-numeric, NaN, infinity, negatives and 30 itself. Thirty is
    NOT a degree in a sign: it is the first degree of the next one, and treating
    it as segment 5 is precisely the silent-wrong-answer the D4 frontend gave.
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise D5DomainError(f"{what} degree is not a number")
    if not math.isfinite(float(value)):
        raise D5DomainError(f"{what} degree is not finite")
    # Through the string form: Decimal(float) would import the binary
    # representation error this conversion exists to avoid.
    dec = Decimal(str(value))
    if dec < 0 or dec >= 30:
        raise D5DomainError(f"{what} degree is outside [0, 30)")
    return dec


# ─────────────────────────────────────────────────────────────────────────────
# PLACEMENT ARITHMETIC
# ─────────────────────────────────────────────────────────────────────────────

def segment_of(degree: Any, what: str = "position") -> int:
    """0-based segment number for an in-sign degree, half-open on 6-degree arcs."""
    return int(_require_degree(degree, what) // D5_SEGMENT_ARC)


def counting_start_index(sign_index: int) -> int:
    """The sign counting begins from, for a source sign."""
    modality = MODALITY_BY_SIGN_INDEX[sign_index]
    return (sign_index + COUNTING_START_OFFSET[modality]) % 12


def d5_sign_index(sign_index: Any, degree: Any, what: str = "position") -> int:
    """The canonical D5 sign index for a certified D1 position."""
    si = _require_sign_index(sign_index, what)
    return (counting_start_index(si) + segment_of(degree, what)) % 12


def d5_house_of(planet_d5_sign_index: int, lagna_d5_sign_index: int) -> int:
    """Whole-sign D5 house. The D5 Lagna's own sign is H1 by definition."""
    return ((planet_d5_sign_index - lagna_d5_sign_index) % 12) + 1


def build_placement(subject: str, sign_index: Any, degree: Any,
                    doctrine: D5Doctrine,
                    source_longitude: Optional[float] = None) -> Dict[str, Any]:
    """One fully audited D5 placement.

    `source_longitude` IS PROVENANCE ONLY. It is carried through from the
    certified snapshot exactly as received and is never read by any arithmetic
    in this module. The segment is taken from the certified in-sign `degree`,
    because `degree` and `longitude` are rounded to four decimals independently
    by the chart engine and can therefore disagree in the fourth place — and the
    displayed chart was drawn from `degree`. Computing the segment from
    `longitude` would let the D5 layer and the chart the reader was shown
    disagree about which 6-degree arc a graha occupies.
    """
    si = _require_sign_index(sign_index, subject)
    dec = _require_degree(degree, subject)
    segment = int(dec // D5_SEGMENT_ARC)
    start_si = counting_start_index(si)
    target_si = (start_si + segment) % 12
    tattva, tattva_lords = TATTVA_BY_SEGMENT[segment]
    return {
        "subject": subject,
        "source_longitude": source_longitude,
        "source_sign": doctrine.signs[si],
        "source_sign_index": si,
        "source_degree_in_sign": float(dec),
        "source_modality": MODALITY_BY_SIGN_INDEX[si],
        "segment_number": segment + 1,
        "segment_index": segment,
        "segment_start_degree": float(D5_SEGMENT_ARC * segment),
        "segment_end_degree": float(D5_SEGMENT_ARC * (segment + 1)),
        "tattva": tattva,
        "tattva_lords": list(tattva_lords),
        "counting_start_sign": doctrine.signs[start_si],
        "counting_start_sign_index": start_si,
        "d5_sign": doctrine.signs[target_si],
        "d5_sign_index": target_si,
        "d5_house": None,  # filled once the D5 Lagna is known
    }


# ─────────────────────────────────────────────────────────────────────────────
# HOUSES
# ─────────────────────────────────────────────────────────────────────────────

def build_houses(lagna_d5_sign_index: int, placements: Dict[str, Dict[str, Any]],
                 doctrine: D5Doctrine) -> List[Dict[str, Any]]:
    """The twelve whole-sign D5 houses, with occupants."""
    houses = []
    for house in range(1, 13):
        si = (lagna_d5_sign_index + house - 1) % 12
        occupants = [g for g in ALL_GRAHAS
                     if placements[g]["d5_sign_index"] == si]
        houses.append({
            "house": house,
            "sign": doctrine.signs[si],
            "sign_index": si,
            "lord": doctrine.sign_lords[si],
            "occupants": occupants,
        })
    return houses


# ─────────────────────────────────────────────────────────────────────────────
# CHARA KARAKAS
# ─────────────────────────────────────────────────────────────────────────────

def _arcsecond_key(degree: Decimal) -> int:
    """Exact integer ranking key in ten-thousandths of a degree.

    THE PRECISION IS STATED, NOT ASSUMED. The certified snapshot carries the
    in-sign degree rounded to four decimals, which resolves to 0.36 arcseconds.
    Ranking on this key therefore compares strictly finer than one arcsecond, as
    the specification requires. It cannot compare finer than 0.36 arcseconds,
    because no value in the snapshot carries that precision — two planets whose
    true separation is smaller than that are indistinguishable here and fall to
    the Founder priority order. Integer arithmetic is used so that two equal
    degrees compare equal exactly.
    """
    return int(degree.scaleb(4).to_integral_value())


def build_chara_karakas(planets: Dict[str, Dict[str, Any]],
                        doctrine: D5Doctrine) -> Dict[str, Any]:
    """The seven Chara Karakas, ranked by traversed degree within the D1 sign.

    Rahu and Ketu are not candidates and are never assigned. Highest degree
    takes AK. Exact ties fall to the Founder priority order.
    """
    ranked = []
    for planet in CHARA_KARAKA_PLANETS:
        record = planets.get(planet)
        if not isinstance(record, dict):
            raise D5DomainError("a Chara Karaka candidate is missing")
        si = _require_sign_index(record.get("sign_index"), planet)
        dec = _require_degree(record.get("degree"), planet)
        ranked.append({
            "planet": planet,
            "source_sign": doctrine.signs[si],
            "source_sign_index": si,
            "source_degree_in_sign": float(dec),
            "source_arcseconds": float(dec * 3600),
            "ranking_key_ten_thousandths_degree": _arcsecond_key(dec),
            "tie_priority": CHARA_KARAKA_TIE_PRIORITY.index(planet),
        })

    ranked.sort(key=lambda r: (-r["ranking_key_ten_thousandths_degree"],
                               r["tie_priority"]))

    assignments: Dict[str, Any] = {}
    for rank, record in enumerate(ranked):
        karaka = CHARA_KARAKA_ORDER[rank]
        entry = dict(record)
        entry["karaka"] = karaka
        entry["rank"] = rank + 1
        assignments[karaka] = entry
    return {
        "system": "7-karaka",
        "rahu_eligible": False,
        "ketu_eligible": False,
        "eligible_planets": list(CHARA_KARAKA_PLANETS),
        "assignments": assignments,
        "ranking": [dict(r, rank=i + 1) for i, r in enumerate(ranked)],
    }


# ─────────────────────────────────────────────────────────────────────────────
# D1 FIFTH-LORD MIRRORING
# ─────────────────────────────────────────────────────────────────────────────

def build_d1_fifth_lord_mirroring(lagna_sign_index: int,
                                  planets: Dict[str, Dict[str, Any]],
                                  placements: Dict[str, Dict[str, Any]],
                                  doctrine: D5Doctrine) -> Dict[str, Any]:
    """The D1 fifth-house lord, and where that same graha sits in D5.

    The lordship is read from the certified D1 lagna and the shared sign-lord
    table. Nothing is recalculated and nothing is derived in the browser.
    """
    fifth_si = (lagna_sign_index + 4) % 12
    lord = doctrine.sign_lords[fifth_si]
    record = planets.get(lord)
    if not isinstance(record, dict):
        raise D5DomainError("the D1 fifth lord is missing from the snapshot")
    placement = placements.get(lord)
    if placement is None:
        raise D5DomainError("the D1 fifth lord has no D5 placement")
    lord_si = _require_sign_index(record.get("sign_index"), lord)
    return {
        "d1_fifth_house_sign": doctrine.signs[fifth_si],
        "d1_fifth_house_sign_index": fifth_si,
        "planet": lord,
        "d1_sign": doctrine.signs[lord_si],
        "d1_sign_index": lord_si,
        "d1_house": ((lord_si - lagna_sign_index) % 12) + 1,
        "d1_degree_in_sign": placement["source_degree_in_sign"],
        "d1_longitude": placement["source_longitude"],
        "segment_number": placement["segment_number"],
        "tattva": placement["tattva"],
        "tattva_lords": list(placement["tattva_lords"]),
        "d5_sign": placement["d5_sign"],
        "d5_sign_index": placement["d5_sign_index"],
        "d5_house": placement["d5_house"],
    }


# ─────────────────────────────────────────────────────────────────────────────
# KARAKAMSHA
# ─────────────────────────────────────────────────────────────────────────────

def build_karakamsha(chara_karakas: Dict[str, Any],
                     planets: Dict[str, Dict[str, Any]],
                     lagna_d5_sign_index: int,
                     doctrine: D5Doctrine) -> Dict[str, Any]:
    """AK's D9 sign, located as the SAME zodiac sign in the D5 chart.

    There is no additional sign transformation. The D9 sign index is read from
    the certified snapshot's own published `d9_sign_index` — the D9 division is
    never recomputed here.
    """
    ak = chara_karakas["assignments"]["AK"]["planet"]
    record = planets.get(ak)
    if not isinstance(record, dict):
        raise D5DomainError("the Atmakaraka is missing from the snapshot")
    d9_si = _require_sign_index(record.get("d9_sign_index"), f"{ak} D9")
    return {
        "atmakaraka": ak,
        "d9_ak_sign": doctrine.signs[d9_si],
        "d9_ak_sign_index": d9_si,
        "d5_karakamsha_sign": doctrine.signs[d9_si],
        "d5_karakamsha_sign_index": d9_si,
        "d5_karakamsha_house": d5_house_of(d9_si, lagna_d5_sign_index),
        "transformation": "none · the D9 Atmakaraka sign is located unchanged in D5",
    }


# ─────────────────────────────────────────────────────────────────────────────
# THE ONE ASSEMBLY
# ─────────────────────────────────────────────────────────────────────────────

def build_d5_facts(lagna: Dict[str, Any], planets: Dict[str, Dict[str, Any]],
                   doctrine: D5Doctrine) -> Dict[str, Any]:
    """Every D5-001 fact, from certified D1 inputs only.

    `lagna` and `planets` carry `sign_index`, `degree` and — provenance only —
    `longitude`; `planets` additionally carries the certified `d9_sign_index`
    that the Karakamsha reference reads.
    """
    lagna_si = _require_sign_index(lagna.get("sign_index"), "lagna")
    lagna_placement = build_placement("Lagna", lagna_si, lagna.get("degree"),
                                      doctrine, lagna.get("longitude"))
    lagna_d5_si = lagna_placement["d5_sign_index"]
    lagna_placement["d5_house"] = 1

    placements: Dict[str, Dict[str, Any]] = {}
    for graha in ALL_GRAHAS:
        record = planets.get(graha)
        if not isinstance(record, dict):
            raise D5DomainError("a graha is missing from the snapshot")
        placement = build_placement(graha, record.get("sign_index"),
                                    record.get("degree"), doctrine,
                                    record.get("longitude"))
        placement["d5_house"] = d5_house_of(placement["d5_sign_index"], lagna_d5_si)
        placements[graha] = placement

    houses = build_houses(lagna_d5_si, placements, doctrine)
    lagna_lord_name = doctrine.sign_lords[lagna_d5_si]
    lagna_lord = {
        "planet": lagna_lord_name,
        "rules_d5_sign": doctrine.signs[lagna_d5_si],
        "rules_d5_sign_index": lagna_d5_si,
        "placement": placements.get(lagna_lord_name),
    }

    chara_karakas = build_chara_karakas(planets, doctrine)
    return {
        "lagna": lagna_placement,
        "lagna_lord": lagna_lord,
        "houses": houses,
        "grahas": placements,
        "chara_karakas": chara_karakas,
        "d1_fifth_lord_mirroring": build_d1_fifth_lord_mirroring(
            lagna_si, planets, placements, doctrine),
        "karakamsha": build_karakamsha(chara_karakas, planets, lagna_d5_si, doctrine),
    }
