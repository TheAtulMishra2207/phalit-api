"""D7-002 · certified D1 and D9 joins.

Prepares the evidence FD-6 named. It does not write the triangulation article —
that is D7-003.

Everything here is READ from the certified snapshot. Nothing is recomputed: the
snapshot already carries `d9_sign_index` per body, so D9 is a read, not a second
navamsha implementation. A second implementation is how two charts on one screen
start disagreeing.
"""

from typing import Any, Dict, List, Optional

from d7_predicates import (
    aspects_house,
    dignity,
    natural_relationship,
    occupies,
    benefics_on_house,
    malefics_on_house,
)

KENDRAS = (1, 4, 7, 10)
TRIKONAS = (1, 5, 9)
D9_TRIANGULATION_BODIES = ("Jupiter", "Venus", "Mercury")


def _house_from(sign_idx: int, lagna_idx: int) -> int:
    return ((sign_idx - lagna_idx) % 12) + 1


def _certified_dignity(rec: Dict[str, Any]) -> Optional[str]:
    """Read the CERTIFIED D1 dignity the snapshot already carries.

    D7 must not recompute D1 dignity with D7-local logic: /chart already
    computed it through the accepted `get_dignity`, including the BPHS Ch.47
    node handling and the moolatrikona-before-exaltation ordering that D7's own
    divisional table deliberately does not implement. Recomputing here would
    create a second interpretation stack that disagrees with the D1 page.
    """
    for key in ("dignity", "d1_dignity"):
        val = rec.get(key)
        if isinstance(val, str) and val:
            return val
    return None


def _certified_d9_dignity(rec: Dict[str, Any]) -> Optional[str]:
    """Read the CERTIFIED D9 dignity from the snapshot. Same reasoning."""
    for key in ("d9_dignity", "navamsha_dignity"):
        val = rec.get(key)
        if isinstance(val, str) and val:
            return val
    return None


def build_d1_join(lagna: Dict[str, Any],
                  planets: Dict[str, Dict[str, Any]],
                  sign_lords: List[str]) -> Dict[str, Any]:
    """Physical readiness pillar evidence · D1 5th house and its lord.

    The Founder register for this pillar is a REALITY FILTER on physical
    capacity, expressed as lifestyle direction. No fertility verdict is formed
    here and none can be: this returns placement and dignity facts only.
    """
    lagna_idx = lagna["sign_index"]
    placements = {
        b: {"house": _house_from(p["sign_index"], lagna_idx),
            "sign_index": p["sign_index"],
            "degree": p["degree"]}
        for b, p in planets.items()
    }
    h5_sign_idx = (lagna_idx + 4) % 12
    h5_lord = sign_lords[h5_sign_idx]
    h5_lord_rec = placements.get(h5_lord)

    return {
        "lagna_sign_index": lagna_idx,
        "h5": {
            "sign_index": h5_sign_idx,
            "occupants": sorted(b for b, r in placements.items() if r["house"] == 5),
            "benefics": benefics_on_house(5, placements),
            "malefics": malefics_on_house(5, placements),
        },
        "h5_lord": {
            "graha": h5_lord,
            "house": h5_lord_rec["house"] if h5_lord_rec else None,
            "sign_index": h5_lord_rec["sign_index"] if h5_lord_rec else None,
            "dignity": (_certified_dignity(planets[h5_lord])
                        if h5_lord in planets else None),
            "dignity_authority": "certified_d1_snapshot",
            "in_dusthana": (h5_lord_rec["house"] in (6, 8, 12)) if h5_lord_rec else None,
        },
        "putrakaraka": {
            "graha": "Jupiter",
            "house": placements.get("Jupiter", {}).get("house"),
            "dignity": (_certified_dignity(planets["Jupiter"])
                        if "Jupiter" in planets else None),
            "dignity_authority": "certified_d1_snapshot",
        },
        "authority": "certified_d1_snapshot",
    }


def build_d9_join(lagna: Dict[str, Any],
                  planets: Dict[str, Dict[str, Any]],
                  sign_lords: List[str]) -> Dict[str, Any]:
    """Partner synergy pillar evidence · exactly the three FD-6 items.

    1. D9 7th house and its lord, placement and dignity.
    2. Natural relationship between the D9 Lagna lord and the D9 7th lord.
    3. Jupiter, Venus and Mercury in D9 kendras / trikonas.

    `d9_sign_index` is read per body from the certified snapshot. When a body
    lacks it the entry is None rather than guessed.
    """
    d9_lagna_idx = lagna.get("d9_sign_index")
    if d9_lagna_idx is None:
        return {"available": False,
                "reason": "certified snapshot carries no d9_sign_index for the lagna"}

    d9_placements: Dict[str, Dict[str, Any]] = {}
    for body, p in planets.items():
        si = p.get("d9_sign_index")
        if si is None:
            continue
        d9_placements[body] = {
            "d9_sign_index": si,
            "house": _house_from(si, d9_lagna_idx),
        }

    d9_lagna_lord = sign_lords[d9_lagna_idx]
    h7_sign_idx = (d9_lagna_idx + 6) % 12
    h7_lord = sign_lords[h7_sign_idx]
    h7_lord_rec = d9_placements.get(h7_lord)

    # D9 dignity is READ from the certified snapshot, which computed it through
    # the accepted D9 authority. There is NO fallback: an absent value is
    # reported unavailable per body, because a locally reconstructed D9 dignity
    # is a second interpretation stack and would disagree with the D9 page.
    dignities: Dict[str, Optional[str]] = {}
    dignity_source: Dict[str, str] = {}
    for b, r in d9_placements.items():
        certified = _certified_d9_dignity(planets.get(b, {}))
        if certified:
            dignities[b] = certified
            dignity_source[b] = "certified_d9_snapshot"
        else:
            # CORR-02 · spec J. NO local D9 dignity fallback. An absent
            # certified value is reported unavailable, never reconstructed.
            dignities[b] = None
            dignity_source[b] = "unavailable"

    angular = {}
    for body in D9_TRIANGULATION_BODIES:
        rec = d9_placements.get(body)
        if not rec:
            angular[body] = None
            continue
        angular[body] = {
            "house": rec["house"],
            "in_kendra": rec["house"] in KENDRAS,
            "in_trikona": rec["house"] in TRIKONAS,
            "dignity": dignities.get(body),
        }

    return {
        "available": True,
        "d9_lagna": {
            "sign_index": d9_lagna_idx,
            "lord": d9_lagna_lord,
            "lord_house": (d9_placements.get(d9_lagna_lord) or {}).get("house"),
            "lord_dignity": dignities.get(d9_lagna_lord),
        },
        "h7": {
            "sign_index": h7_sign_idx,
            "occupants": sorted(b for b, r in d9_placements.items() if r["house"] == 7),
            "benefics": benefics_on_house(7, d9_placements),
            "malefics": malefics_on_house(7, d9_placements),
        },
        "h7_lord": {
            "graha": h7_lord,
            "house": h7_lord_rec["house"] if h7_lord_rec else None,
            "d9_sign_index": h7_lord_rec["d9_sign_index"] if h7_lord_rec else None,
            "dignity": dignities.get(h7_lord),
        },
        "lagna_lord_to_h7_lord": {
            "from": d9_lagna_lord,
            "to": h7_lord,
            "relationship": natural_relationship(d9_lagna_lord, h7_lord),
            "same_graha": d9_lagna_lord == h7_lord,
        },
        "angular_benefics": angular,
        "dignity_source": dignity_source,
        "authority": "certified_d9_snapshot",
    }
