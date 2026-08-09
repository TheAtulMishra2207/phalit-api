"""
D4-002 · Chaturthamsha MECHANICAL CORE.

Scope, deliberately narrow. This module computes MECHANICAL FACTS ONLY:
D4 sign placement, the D4 whole-sign house map, D4 house lords, D4 sign-based
dignity, Vargottama, and the full Parashari D4 aspect manifest. It resolves no
property state, computes no composite strength score, produces no narrative,
and has no provider or LLM authority of any kind.

TWO DESIGN RULES THIS MODULE IS BUILT AROUND
--------------------------------------------
1. NO COMPETING DOCTRINE TABLE. This file contains no sign-lord table, no
   exaltation table, no debilitation table, no friendship table and no sign
   names. Every one of those is INJECTED through `D4Doctrine` from the accepted
   Phalit tables in main.py. There is exactly one copy of the doctrine in the
   system and it is not this file.

2. NO SERVER/BROWSER SPLIT BRAIN. The functions here are the intended single
   source of D4 mechanical truth. The legacy browser implementation is NOT
   consulted, NOT imported and NOT used as an oracle.

TWO POLICIES THAT REQUIRE A FOUNDER RULING — see D4-002-DELIVERY.md §Ambiguity.
Both are explicit, versioned fields in the payload rather than silent choices:

  * `varga_moolatrikona_policy = "not_evaluated"`.
    Moolatrikona is a DEGREE RANGE inside a rasi (Sun Leo 0-20, Moon Taurus
    4-30, ...). A D4 sign is the image of a 7 deg 30 min quarter, so a graha has
    no defined degree within its D4 sign, and there is therefore no degree to
    test a moolatrikona range against. Passing any placeholder degree changes
    the answer: at degree 0.0 the accepted `get_dignity` returns Moolatrikona
    for Sun/Mars/Jupiter/Venus/Saturn in their own signs but Exalted for Moon in
    Taurus and Mercury in Virgo, because those two have a non-zero range floor.
    No placeholder is defensible, so moolatrikona is NOT EVALUATED for D4 and
    the graha resolves to the next accepted branch. The certification proves
    that on every (graha, sign) pair NOT affected by this policy the result is
    identical to the accepted `get_dignity`.

  * `node_dignity_policy = "not_published_pending_ruling"`.
    `dignity` is null for Rahu and Ketu. The BPHS Ch.47 node-sign doctrine IS
    already certified and shipped in `get_dignity`, so its D4-sign result is
    computed and exposed separately under `bphs47_node_sign_state` for a ruling
    to adopt or reject. Nothing invents a node dignity, and no downstream field
    consumes it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Sequence

D4_CORE_VERSION = "1.0.0"

# ── Mechanical constants owned by this module ────────────────────────────────
# These are D4 geometry, not doctrine tables, so they live here.

#: Half-open quarter boundaries. Quarter q covers [BOUNDS[q], BOUNDS[q+1]).
QUARTER_BOUNDS = (0.0, 7.5, 15.0, 22.5, 30.0)

#: Sign offset applied per quarter: same sign, 4th, 7th, 10th.
QUARTER_SIGN_OFFSET = (0, 3, 6, 9)

CLASSICAL_GRAHAS = ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn")
NODES = ("Rahu", "Ketu")
ALL_GRAHAS = CLASSICAL_GRAHAS + NODES

#: Full Parashari drishti, expressed as house counts from the occupied house.
#: 7 is universal for the seven classical grahas. Nodes are ABSENT from this
#: map by doctrine, not by omission: they cast no independent drishti.
SPECIAL_ASPECTS: Dict[str, tuple] = {
    "Mars": (4, 8),
    "Jupiter": (5, 9),
    "Saturn": (3, 10),
}
UNIVERSAL_ASPECT = 7


class D4DomainError(ValueError):
    """Raised for out-of-domain input. Callers convert this to a neutral
    public error; the message is internal and must never be published."""


# ── Injected doctrine ────────────────────────────────────────────────────────

@dataclass(frozen=True)
class D4Doctrine:
    """The accepted Phalit doctrine, injected. Production passes the objects
    from main.py directly. Nothing here is re-declared or copied."""
    signs: Sequence[str]                  # main.SIGNS
    sign_lords: Sequence[str]             # main.SIGN_LORDS
    exaltation_sign: Dict[str, int]       # main.EXALTATION_SIGN
    debilitation_sign: Dict[str, int]     # main.DEBILITATION_SIGN
    own_signs: Dict[str, List[int]]       # main.OWN_SIGNS
    natural_friends: Dict[str, List[str]] # main.NATURAL_FRIENDS
    natural_enemies: Dict[str, List[str]] # main.NATURAL_ENEMIES
    node_dignity_fn: Optional[Callable[[str, int, float], str]] = None  # main.get_dignity

    def __post_init__(self) -> None:
        if len(self.signs) != 12 or len(self.sign_lords) != 12:
            raise D4DomainError("doctrine tables must be twelve-long")
        for lord in self.sign_lords:
            if lord in NODES:
                # Guard, not decoration: a node can never become a sign lord,
                # so a node reaching this table would silently produce node
                # house-lordships downstream.
                raise D4DomainError("a node may never appear in the sign-lord table")


# ── 1 · D4 sign placement ────────────────────────────────────────────────────

def _validate(sign_index: Any, degree: Any) -> None:
    if isinstance(sign_index, bool) or not isinstance(sign_index, int):
        raise D4DomainError("sign_index must be an int")
    if not 0 <= sign_index <= 11:
        raise D4DomainError("sign_index out of range")
    if isinstance(degree, bool) or not isinstance(degree, (int, float)):
        raise D4DomainError("degree must be a number")
    if degree != degree:                       # NaN
        raise D4DomainError("degree is NaN")
    if degree in (float("inf"), float("-inf")):
        raise D4DomainError("degree is not finite")
    if not 0.0 <= degree < 30.0:               # half-open: 30.0 is the NEXT sign
        raise D4DomainError("degree out of range")


def d4_quarter(degree: float, sign_index: int = 0) -> int:
    """Quarter index 0-3 for a degree in sign. Half-open at every boundary:
    7.5 is quarter 1, 15.0 is quarter 2, 22.5 is quarter 3, 30.0 is invalid."""
    _validate(sign_index, degree)
    if degree < 7.5:
        return 0
    if degree < 15.0:
        return 1
    if degree < 22.5:
        return 2
    return 3


def d4_sign_index(sign_index: int, degree: float) -> int:
    """The D4 sign. Raises D4DomainError rather than returning a confident
    wrong answer, which is what the legacy browser function did for NaN, 30 and
    undefined (all silently produced the fourth quarter)."""
    q = d4_quarter(degree, sign_index)
    return (sign_index + QUARTER_SIGN_OFFSET[q]) % 12


def is_vargottama(sign_index: int, degree: float) -> bool:
    """Mechanical boolean: D1 sign == D4 sign. Exposed as its own fact. The
    approved +1 strength modifier is NOT applied here — D4-002 certifies the
    underlying fact only and computes no composite score."""
    return d4_sign_index(sign_index, degree) == sign_index


# ── 2 · House map ────────────────────────────────────────────────────────────

def d4_house_of(d4_sign: int, d4_lagna_sign: int) -> int:
    """Whole-sign house number 1-12 counted from the D4 Lagna."""
    if not (0 <= d4_sign <= 11 and 0 <= d4_lagna_sign <= 11):
        raise D4DomainError("sign index out of range")
    return ((d4_sign - d4_lagna_sign) % 12) + 1


def d4_house_sign(house: int, d4_lagna_sign: int) -> int:
    if not 1 <= house <= 12:
        raise D4DomainError("house out of range")
    return (d4_lagna_sign + house - 1) % 12


# ── 3 · Aspects ──────────────────────────────────────────────────────────────

def aspect_offsets(graha: str) -> tuple:
    """House counts this graha aspects. Nodes cast nothing."""
    if graha in NODES:
        return ()
    if graha not in CLASSICAL_GRAHAS:
        raise D4DomainError("unknown graha")
    return (UNIVERSAL_ASPECT,) + SPECIAL_ASPECTS.get(graha, ())


def aspected_houses(graha: str, from_house: int) -> List[int]:
    if not 1 <= from_house <= 12:
        raise D4DomainError("house out of range")
    return sorted(((from_house - 1 + off - 1) % 12) + 1 for off in aspect_offsets(graha))


# ── 4 · Dignity, from the D4 SIGN ────────────────────────────────────────────

def d4_dignity(graha: str, d4_sign: int, doctrine: D4Doctrine) -> Dict[str, Any]:
    """Dignity evaluated from the graha's D4 SIGN, never its D1 sign.

    Branch order is the accepted `get_dignity` order with the moolatrikona
    branch REMOVED per `varga_moolatrikona_policy` (see module docstring):
    debilitation, exaltation, own sign, then the sign-lord relation.

    Raw components are exposed alongside the label so a later ruling can
    re-derive a different label without recomputing anything, and so no
    downstream rule has to parse the label string.
    """
    if graha in NODES:
        return {
            "graha": graha,
            "d4_sign_index": d4_sign,
            "d4_sign": doctrine.signs[d4_sign],
            "dignity": None,
            "policy": "not_published_pending_ruling",
            "bphs47_node_sign_state": (
                doctrine.node_dignity_fn(graha, d4_sign, 0.0)
                if doctrine.node_dignity_fn else None
            ),
        }
    if graha not in CLASSICAL_GRAHAS:
        raise D4DomainError("unknown graha")

    sign_lord = doctrine.sign_lords[d4_sign]
    is_debilitated = doctrine.debilitation_sign.get(graha) == d4_sign
    is_exalted = doctrine.exaltation_sign.get(graha) == d4_sign
    is_own = d4_sign in doctrine.own_signs.get(graha, []) or sign_lord == graha
    lord_is_friend = sign_lord in doctrine.natural_friends.get(graha, [])
    lord_is_enemy = sign_lord in doctrine.natural_enemies.get(graha, [])

    if is_debilitated:
        label = "Debilitated (Neecha)"
    elif is_exalted:
        label = "Exalted (Uccha)"
    elif is_own:
        label = "Own Sign (Swa)"
    elif lord_is_friend:
        label = "Friendly Sign (Mitra)"
    elif lord_is_enemy:
        label = "Enemy Sign (Shatru)"
    else:
        label = "Neutral Sign (Sama)"

    return {
        "graha": graha,
        "d4_sign_index": d4_sign,
        "d4_sign": doctrine.signs[d4_sign],
        "dignity": label,
        "policy": "sign_only_moolatrikona_not_evaluated",
        "components": {
            "sign_lord": sign_lord,
            "is_exalted": is_exalted,
            "is_debilitated": is_debilitated,
            "is_own_sign": is_own,
            "sign_lord_is_natural_friend": lord_is_friend,
            "sign_lord_is_natural_enemy": lord_is_enemy,
        },
    }


# ── 5 · The bundle ───────────────────────────────────────────────────────────

def build_d4_facts(lagna: Dict[str, Any],
                   planets: Dict[str, Dict[str, Any]],
                   doctrine: D4Doctrine) -> Dict[str, Any]:
    """Full mechanical D4 fact layer for one chart.

    `lagna` and `planets` carry the certified D1 `sign_index` and in-sign
    `degree` exactly as the chart snapshot holds them. Nothing else is read,
    and no birth data is accepted.
    """
    if not isinstance(lagna, dict):
        raise D4DomainError("lagna must be an object")
    d4_lagna = d4_sign_index(lagna["sign_index"], lagna["degree"])

    missing = [g for g in ALL_GRAHAS if g not in planets]
    if missing:
        raise D4DomainError("missing graha in snapshot")

    grahas: Dict[str, Any] = {}
    for g in ALL_GRAHAS:
        p = planets[g]
        si, deg = p["sign_index"], p["degree"]
        ds = d4_sign_index(si, deg)
        house = d4_house_of(ds, d4_lagna)
        grahas[g] = {
            "graha": g,
            "d1_sign_index": si,
            "d1_sign": doctrine.signs[si],
            "d4_quarter": d4_quarter(deg, si) + 1,          # 1-4, human facing
            "d4_sign_index": ds,
            "d4_sign": doctrine.signs[ds],
            "d4_house": house,
            "vargottama": ds == si,
            "dignity": d4_dignity(g, ds, doctrine),
            "aspects_cast": aspected_houses(g, house),
            "casts_drishti": g not in NODES,
        }

    houses = []
    for h in range(1, 13):
        hs = d4_house_sign(h, d4_lagna)
        houses.append({
            "house": h,
            "sign_index": hs,
            "sign": doctrine.signs[hs],
            "lord": doctrine.sign_lords[hs],
            "occupants": [g for g in ALL_GRAHAS if grahas[g]["d4_house"] == h],
        })

    edges = []
    for g in ALL_GRAHAS:
        src = grahas[g]["d4_house"]
        for off in aspect_offsets(g):
            edges.append({
                "source": g,
                "from_house": src,
                "to_house": ((src - 1 + off - 1) % 12) + 1,
                "offset": off,
                "kind": "universal_7th" if off == UNIVERSAL_ASPECT else "special",
            })

    received_by_house: Dict[int, List[str]] = {h: [] for h in range(1, 13)}
    for e in edges:
        received_by_house[e["to_house"]].append(e["source"])
    for h in received_by_house:
        received_by_house[h].sort()

    # Nodes cast nothing but DO receive. Computed from the same edge list, so
    # the two facts cannot drift apart.
    received_by_graha = {
        g: sorted({e["source"] for e in edges
                   if e["to_house"] == grahas[g]["d4_house"] and e["source"] != g})
        for g in ALL_GRAHAS
    }

    h4 = houses[3]
    fourth_lord = h4["lord"]
    fourth_bundle = {
        "house": 4,
        "sign_index": h4["sign_index"],
        "sign": h4["sign"],
        "lord": fourth_lord,
        "occupants": h4["occupants"],
        "aspects_received": received_by_house[4],
        "lord_facts": {
            "graha": fourth_lord,
            "d4_sign_index": grahas[fourth_lord]["d4_sign_index"],
            "d4_sign": grahas[fourth_lord]["d4_sign"],
            "d4_house": grahas[fourth_lord]["d4_house"],
            "dignity": grahas[fourth_lord]["dignity"],
            "vargottama": grahas[fourth_lord]["vargottama"],
            "aspects_received": received_by_graha[fourth_lord],
        },
        # Bhumi and Vahana karakas, mechanical facts only. No property or
        # vehicle interpretation is attached, and none may be inferred here.
        "mars_bhumi_karaka": _karaka_facts("Mars", grahas, received_by_graha),
        "venus_vahana_karaka": _karaka_facts("Venus", grahas, received_by_graha),
    }

    return {
        "engine": {
            "d4_core_version": D4_CORE_VERSION,
            "method": "chaturthamsha_kendra_7deg30",
            "house_system": "whole-sign-from-d4-lagna",
            "aspect_doctrine": "parashari_full_no_independent_node_drishti",
            "varga_moolatrikona_policy": "not_evaluated",
            "node_dignity_policy": "not_published_pending_ruling",
            "vargottama_strength_modifier_applied": False,
        },
        "d4_lagna": {
            "sign_index": d4_lagna,
            "sign": doctrine.signs[d4_lagna],
            "lord": doctrine.sign_lords[d4_lagna],
        },
        "houses": houses,
        "house_lords": {h["house"]: h["lord"] for h in houses},
        "key_house_lords": {"4": houses[3]["lord"], "8": houses[7]["lord"], "12": houses[11]["lord"]},
        "grahas": grahas,
        "vargottama_grahas": [g for g in ALL_GRAHAS if grahas[g]["vargottama"]],
        "aspects": {
            "edges": edges,
            "received_by_house": received_by_house,
            "received_by_graha": received_by_graha,
        },
        "fourth_house": fourth_bundle,
    }


def _karaka_facts(graha: str, grahas: Dict[str, Any], received: Dict[str, List[str]]) -> Dict[str, Any]:
    g = grahas[graha]
    return {
        "graha": graha,
        "d4_sign": g["d4_sign"],
        "d4_sign_index": g["d4_sign_index"],
        "d4_house": g["d4_house"],
        "dignity": g["dignity"],
        "vargottama": g["vargottama"],
        "aspects_cast": g["aspects_cast"],
        "aspects_received": received[graha],
    }
