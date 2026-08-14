"""D7-002 · timing primitives.

Two things only, and the second is deliberately partial.

1. CURRENT PERIOD — Mahadasha and Antardasha identities READ from the certified
   snapshot at `dasha.current_mahadasha.planet` / `.current_antardasha.planet`.
   Vimshottari is never recomputed here. This follows the accepted D4-007
   boundary: a concurrence is CONTEXT ONLY. It activates nothing, creates no
   yoga, predicts no conception and produces no date.

2. WINDOW 1 · Jupiter — the transit target is mechanically defined: the accepted
   Parashari Jupiter graha-drishti (5th, 7th, 9th from Jupiter's transit
   position) landing on the relevant sign. NO Jaimini Rashi Drishti is
   introduced anywhere in D7.

   WINDOW 2 · Saturn is NOT implemented. "Saturn stabilizes your Lagna Lord" has
   no mechanical definition anywhere in the product, and the ticket forbids
   inventing an affliction definition for the unresolved clause. It is returned
   as UNRESOLVED_FOUNDER_PRIMITIVE.
"""

from typing import Any, Dict, List, Optional

from d7_rules import UNRESOLVED

JUPITER_DRISHTI_OFFSETS = (5, 7, 9)

TIMING_AUTHORITY = "context_only"
TIMING_POLICY = "structural_concurrence_not_activation"


def read_current_period(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    """MD/AD identities from the certified snapshot.

    THREE-STATE, never collapsed: present / absent / malformed. A missing level
    resolves to `unknown`, never to a negative, because treating an absence as a
    negative publishes a structural claim that was never computed.
    """
    dasha = snapshot.get("dasha") or {}
    out: Dict[str, Any] = {
        "authority": TIMING_AUTHORITY,
        "timing_policy": TIMING_POLICY,
    }
    for level, key in (("mahadasha", "current_mahadasha"),
                       ("antardasha", "current_antardasha")):
        rec = dasha.get(key)
        if not isinstance(rec, dict):
            out[level] = {"planet": None, "status": "unknown"}
            continue
        planet = rec.get("planet")
        if not isinstance(planet, str) or not planet:
            out[level] = {"planet": None, "status": "unknown"}
            continue
        out[level] = {"planet": planet, "status": "known"}

    known = [out[l]["planet"] for l in ("mahadasha", "antardasha")
             if out[l]["status"] == "known"]
    out["period_label"] = " / ".join(known) if known else None
    out["resolved"] = len(known) == 2
    return out


def jupiter_drishti_from(transit_sign_index: int) -> List[int]:
    """Signs receiving Jupiter's graha-drishti from a transit position.

    Parashari only: the 5th, 7th and 9th counted from Jupiter's own sign.
    """
    if transit_sign_index is None:
        return []
    return sorted(((transit_sign_index + off - 1) % 12) for off in JUPITER_DRISHTI_OFFSETS)


def build_jupiter_window(d7_facts: Dict[str, Any],
                         d1_lagna_sign_index: int,
                         d1_fifth_lord_sign_index: Optional[int] = None) -> Dict[str, Any]:
    """WINDOW 1 · the target set Jupiter must occupy or aspect.

    Returns the SIGNS that constitute the window's target, not a date. Which
    sign a transiting Jupiter currently occupies is a transit read that belongs
    to the shared transit provider, and turning a sign set into a calendar
    window is D7-003 presentation work.

    The 5th house axis is interpreted as the D7 5th house sign together with the
    D1 5th house sign, both named explicitly, so a later reader can see which is
    which rather than inferring it.
    """
    # CORR-02 · spec I. The three targets are D7 Lagna, D7 5H and the sign of
    # the D1 FIFTH LORD. The D1 5th HOUSE is deliberately NOT a substitute.
    d7_lagna_sign_index = d7_facts["d7_lagna"]["sign_index"]
    d7_h5_sign_index = d7_facts["key_houses"]["h5"]["sign_index"]
    targets = {d7_lagna_sign_index, d7_h5_sign_index}
    if d1_fifth_lord_sign_index is not None:
        targets.add(d1_fifth_lord_sign_index)
    return {
        "window": "jupiter_fifth_axis",
        "resolved": True,
        "aspect_system": "parashari_graha_drishti",
        "jupiter_offsets": list(JUPITER_DRISHTI_OFFSETS),
        "target_sign_indices": sorted(targets),
        "d7_lagna_sign_index": d7_lagna_sign_index,
        "d7_h5_sign_index": d7_h5_sign_index,
        "d1_fifth_lord_sign_index": d1_fifth_lord_sign_index,
        "trigger": "transiting Jupiter occupying or casting graha-drishti on a target sign",
        "authority": TIMING_AUTHORITY,
    }


SATURN_DRISHTI_OFFSETS = (3, 7, 10)
SATURN_KENDRAS = (1, 4, 7, 10)
SATURN_TRIKONAS = (1, 5, 9)


def saturn_drishti_from(transit_sign_index: int) -> List[int]:
    """Signs receiving Saturn's Parashari graha-drishti from a transit position."""
    if transit_sign_index is None:
        return []
    return sorted(((transit_sign_index + off - 1) % 12) for off in SATURN_DRISHTI_OFFSETS)


def _house_between(from_sign: int, to_sign: int) -> int:
    return ((to_sign - from_sign) % 12) + 1


def saturn_stabilises(transit_sign_index: Optional[int],
                      lagna_lord_sign_index: Optional[int],
                      d7_h11_sign_index: Optional[int],
                      lagna_lord_afflicted: bool) -> Dict[str, Any]:
    """CORR-02 · spec I. The locked Saturn stabilisation predicate.

    TRUE when transiting Saturn is in a KENDRA {1,4,7,10} or a TRIKONA {1,5,9}
    RELATIVE TO the D7 Lagna Lord, OR when Saturn casts accepted Saturn graha
    drishti onto D7 H11.

    The Founder non-affliction condition applies to the Lagna Lord: an afflicted
    Lagna Lord cannot be stabilised, so the predicate is False regardless of
    Saturn's position.

    This deliberately replaces the earlier reading, which tested only whether
    Saturn occupied or aspected the Lagna Lord's sign.
    """
    if transit_sign_index is None or lagna_lord_sign_index is None:
        return {"stabilises": None, "reason": "transit or lagna lord sign unavailable"}
    if lagna_lord_afflicted:
        return {"stabilises": False, "reason": "lagna lord afflicted",
                "kendra": False, "trikona": False, "h11_aspect": False}
    house = _house_between(lagna_lord_sign_index, transit_sign_index)
    kendra = house in SATURN_KENDRAS
    trikona = house in SATURN_TRIKONAS
    h11 = (d7_h11_sign_index is not None
           and d7_h11_sign_index in saturn_drishti_from(transit_sign_index))
    return {
        "stabilises": bool(kendra or trikona or h11),
        "house_from_lagna_lord": house,
        "kendra": kendra,
        "trikona": trikona,
        "h11_aspect": h11,
    }


def build_saturn_window(d7_facts: Dict[str, Any],
                        lagna_lord_sign_index: Optional[int],
                        lagna_lord_afflicted: bool = False,
                        transit_sign_index: Optional[int] = None) -> Dict[str, Any]:
    """WINDOW 2 · the target description plus, when a transit is supplied, the
    evaluated predicate. No date is produced and no affliction definition is
    invented: `lagna_lord_afflicted` is read from the FD-1B surface."""
    h11_sign = d7_facts["houses"][10]["sign_index"]
    out = {
        "window": "saturn_stabilisation",
        "resolved": True,
        "aspect_system": "parashari_graha_drishti",
        "saturn_offsets": list(SATURN_DRISHTI_OFFSETS),
        "kendras_from_lagna_lord": list(SATURN_KENDRAS),
        "trikonas_from_lagna_lord": list(SATURN_TRIKONAS),
        "lagna_lord": d7_facts["d7_lagna"]["lord"],
        "lagna_lord_sign_index": lagna_lord_sign_index,
        "lagna_lord_afflicted": bool(lagna_lord_afflicted),
        "d7_h11_sign_index": h11_sign,
        "trigger": ("transiting Saturn in a kendra or trikona from the D7 lagna "
                    "lord, or casting graha-drishti on D7 H11, with the lagna "
                    "lord unafflicted"),
        "semantics": "consolidation_not_affliction",
        "authority": TIMING_AUTHORITY,
    }
    if transit_sign_index is not None:
        out["evaluation"] = saturn_stabilises(
            transit_sign_index, lagna_lord_sign_index, h11_sign, lagna_lord_afflicted)
    return out


def build_timing(snapshot: Dict[str, Any],
                 d7_facts: Dict[str, Any],
                 d1_lagna_sign_index: int,
                 d1_fifth_lord_sign_index: Optional[int] = None,
                 lagna_lord_sign_index: Optional[int] = None,
                 lagna_lord_afflicted: bool = False) -> Dict[str, Any]:
    return {
        "current_period": read_current_period(snapshot),
        "windows": [
            build_jupiter_window(d7_facts, d1_lagna_sign_index,
                                 d1_fifth_lord_sign_index),
            build_saturn_window(d7_facts, lagna_lord_sign_index,
                                lagna_lord_afflicted),
        ],
        "authority": TIMING_AUTHORITY,
        "timing_policy": TIMING_POLICY,
    }
