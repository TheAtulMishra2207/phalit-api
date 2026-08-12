"""
graha_yuddha.py — THE SHARED GRAHA YUDDHA PRIMITIVE.

D5-008-CORR-01C. A PRODUCT primitive, not a D5-private formula. `main.py`
certifies its result into the snapshot; D5 consumes that result, and derives it
through this same engine for snapshots minted before the field existed. There is
exactly one implementation, so the certified path and the derived path cannot
disagree.

PURE AND DETERMINISTIC. It takes certified D1 sign indices and longitudes and
returns verdicts. No ephemeris call, no `swe.calc_ut`, no second longitude
calculation, no date, no randomness — the accepted chart engine has already
computed everything this needs.
"""
from __future__ import annotations

from typing import Any, Dict, FrozenSet, List, Mapping, Optional, Tuple


class GrahaYuddhaError(ValueError):
    """A combatant record is not shaped like certified chart data."""


#: FOUNDER LOCK · the five eligible combatants.
ELIGIBLE: Tuple[str, ...] = ("Mars", "Mercury", "Jupiter", "Venus", "Saturn")

#: Strictly excluded. These bodies never initiate a war, never receive a
#: defeated flag from one, never enter a cluster and never appear in pair
#: evidence. The Sun and Moon are luminaries and the nodes are shadow bodies —
#: none of them fights.
EXCLUDED: Tuple[str, ...] = ("Sun", "Moon", "Rahu", "Ketu")

ALL_GRAHAS: Tuple[str, ...] = tuple(sorted(ELIGIBLE + EXCLUDED))

#: FOUNDER LOCK · the war trigger orb, in degrees, INCLUSIVE.
WAR_ORB_DEGREES = 1.0

#: FOUNDER LOCK · the natural hierarchy, strongest first. Consulted only for a
#: non-Venus pair whose certified longitudes are exactly equal and for which no
#: certified north latitude exists.
#:
#: Venus sits fourth here and that is NOT a contradiction: Venus primacy is
#: resolved earlier, so this fallback is never reached for a Venus pairing.
NATURAL_HIERARCHY: Tuple[str, ...] = ("Jupiter", "Mars", "Mercury", "Venus",
                                      "Saturn")

#: The four decision codes. Nothing else may appear.
DECISION_VENUS = "venus_primacy"
DECISION_LONGITUDE = "higher_longitude"
DECISION_LATITUDE = "higher_north_latitude"
DECISION_HIERARCHY = "natural_hierarchy"


def _sign_index(record: Mapping[str, Any], graha: str) -> int:
    value = record.get("sign_index")
    # `type(...) is int` rather than isinstance: a bool is an int subclass, and
    # True would otherwise pass as Taurus.
    if type(value) is not int or not 0 <= value <= 11:
        raise GrahaYuddhaError(f"{graha} has no certified sign index")
    return value


def _longitude(record: Mapping[str, Any], graha: str) -> float:
    value = record.get("longitude")
    if type(value) not in (int, float) or isinstance(value, bool):
        raise GrahaYuddhaError(f"{graha} has no certified longitude")
    return float(value)


def _north_latitude(record: Mapping[str, Any]) -> Optional[float]:
    """The certified north latitude, if the accepted ephemeris path published
    one for this body.

    OPTIONAL BY DESIGN. The Founder lock says higher north latitude wins *if
    ephemeris data supports it*. Where the field is absent the tie-break is
    UNAVAILABLE and the hierarchy decides — no coordinate conversion is invented
    and no second ephemeris call is made to manufacture it.
    """
    for key in ("north_latitude", "latitude", "declination"):
        value = record.get(key)
        if type(value) in (int, float) and not isinstance(value, bool):
            return float(value)
    return None


def _resolve_pair(a: str, b: str, record_a: Mapping[str, Any],
                  record_b: Mapping[str, Any]) -> Tuple[str, str, str]:
    """The winner, the loser and the decision code for one qualifying pair."""
    # 1 · VENUS PRIMACY. Always, and before anything else — longitude ordering
    #     never overrides it, so the hierarchy is never consulted for a Venus
    #     pairing even on an exact tie.
    if a == "Venus":
        return a, b, DECISION_VENUS
    if b == "Venus":
        return b, a, DECISION_VENUS

    lon_a = _longitude(record_a, a)
    lon_b = _longitude(record_b, b)

    # 2 · HIGHER LONGITUDE WINS.
    if lon_a != lon_b:
        return (a, b, DECISION_LONGITUDE) if lon_a > lon_b \
            else (b, a, DECISION_LONGITUDE)

    # 3 · EXACT TIE · higher north latitude, only where certified for BOTH.
    lat_a = _north_latitude(record_a)
    lat_b = _north_latitude(record_b)
    if lat_a is not None and lat_b is not None and lat_a != lat_b:
        return (a, b, DECISION_LATITUDE) if lat_a > lat_b \
            else (b, a, DECISION_LATITUDE)

    # 4 · FOUNDER HIERARCHY. Deterministic for every remaining non-Venus tie.
    rank_a = NATURAL_HIERARCHY.index(a)
    rank_b = NATURAL_HIERARCHY.index(b)
    return (a, b, DECISION_HIERARCHY) if rank_a < rank_b \
        else (b, a, DECISION_HIERARCHY)


def evaluate(planets: Mapping[str, Mapping[str, Any]]) -> Dict[str, Any]:
    """Every qualifying pair, evaluated independently.

    THE TRIGGER, EXACTLY AS LOCKED:

        same D1 zodiac sign  AND  abs(longitude_a - longitude_b) <= 1.0

    Same-sign equality is REQUIRED, so there is no circular shortcut across 0
    degrees: Pisces 29.8 and Aries 0.2 are 0.4 degrees apart and are NOT at war,
    because they occupy different signs.

    CLUSTERS ARE PAIRWISE, NOT A TOURNAMENT. With three or more combatants every
    pair is resolved on its own terms, and a planet is defeated if it lost AT
    LEAST ONE pair. A planet may beat one opponent, lose to another and still
    finish defeated — there is no global cluster winner and no ranking.
    """
    defeated: Dict[str, bool] = {graha: False for graha in ALL_GRAHAS}
    wars: List[Dict[str, Any]] = []

    present = [g for g in ELIGIBLE if isinstance(planets.get(g), dict)]
    for i, a in enumerate(sorted(present)):
        for b in sorted(present)[i + 1:]:
            record_a, record_b = planets[a], planets[b]
            same_sign = _sign_index(record_a, a) == _sign_index(record_b, b)
            distance = abs(_longitude(record_a, a) - _longitude(record_b, b))
            if not (same_sign and distance <= WAR_ORB_DEGREES):
                continue
            winner, loser, decision = _resolve_pair(a, b, record_a, record_b)
            defeated[loser] = True
            wars.append({"planet_a": a, "planet_b": b, "same_sign": same_sign,
                         "distance_degrees": round(distance, 6),
                         "winner": winner, "loser": loser,
                         "decision": decision})

    # Deterministic pair ordering, independent of dict iteration order.
    wars.sort(key=lambda w: (w["planet_a"], w["planet_b"]))
    return {"defeated": {g: defeated[g] for g in ALL_GRAHAS}, "wars": wars}


def defeated_map(planets: Mapping[str, Mapping[str, Any]]) -> Dict[str, bool]:
    """Just the per-graha booleans, for callers that need no evidence."""
    return evaluate(planets)["defeated"]
