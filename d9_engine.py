"""D9-002 · the deterministic D9 engine. Server-authoritative, no astrology in the browser.

WHAT THIS MODULE COMPUTES, AND WHAT IT REFUSES TO
--------------------------------------------------
It computes the Atmakaraka, the Karakamsha, the Ishta Devata selection, and the
Karakamsha house occupancy that the accepted authority evaluates. It READS
certified D9 placement, certified D9 dignity and certified vargottama and never
recomputes any of them.

It holds NO doctrine table of its own. SIGNS and SIGN_LORDS are injected once by
main.py via `configure_d9_doctrine`, exactly as D4, D5 and D7 do, so there is one
copy in the process. The Karakamsha rules and the devata selection come from
`karak_house_data`, which is the single extraction of the accepted authority.

`getScore` and `getDignityLabel` are not recreated here or anywhere in the D9
stack. Certified dignity is read, never derived. That is D9-001's central ruling
and 21 of 108 graha/sign cells depended on it.

TWO FRAMES, BOTH DELIBERATE
---------------------------
The accepted Karakamsha module uses two different frames and a careless port
destroys one of them:

  · HOUSES are counted with D1 sign positions from the Karakamsha Lagna
      klH(si) = ((si - klSi) % 12) + 1, applied to `planets[g].sign_index`
  · ISHTA occupancy is by D9 SIGN identity with the twelfth sign from Karakamsha
      d9_sign_index === (klSi + 11) % 12

Both are reproduced exactly. The legacy D9 report used a third frame of its own
— D9 positions counted from the Swamsa — which is not the accepted authority and
does not appear here.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence

import karak_house_data as kh

CLASSICAL_SEVEN = ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn")
NODES = ("Rahu", "Ketu")
ORDER9 = CLASSICAL_SEVEN + NODES

# D9-001 FOUNDER-RULED · chara-karaka membership. Seven classical grahas.
# Rahu is EXCLUDED. Accepted doctrine, reused, not re-decided here.
AK_CANDIDATES = CLASSICAL_SEVEN

# An exact top-degree tie. Compared at this tolerance rather than by float
# equality, because two longitudes derived from the same ephemeris call can
# differ in the last bit and a tie that the reader would call exact must not
# turn on that.
AK_TIE_EPSILON = 1e-9


class D9InputError(ValueError):
    """A certified snapshot value that D9 cannot compute from."""


@dataclass(frozen=True)
class D9Doctrine:
    """The minimum doctrine surface this module reads. Injected, never imported."""
    signs: List[str]
    sign_lords: List[str]


_DOCTRINE: Optional[D9Doctrine] = None


def configure_engine_doctrine(doctrine: D9Doctrine) -> None:
    global _DOCTRINE
    _DOCTRINE = doctrine


def _doctrine() -> D9Doctrine:
    if _DOCTRINE is None:
        raise RuntimeError("d9_engine doctrine not configured")
    return _DOCTRINE


# ─── certified reads ─────────────────────────────────────────────────────────
#
# CERTIFIED DIGNITY BAND ORDER. This is a comparison order for selection only.
# It is NOT a publication vocabulary — `d9_client_reading` owns that, including
# the ruled collapse of Moolatrikona. Node is deliberately absent: an ungraded
# node has no band and `certified_rank` returns None for it.

CERTIFIED_BAND_ORDER = (
    "Debilitated (Neecha)",
    "Enemy Sign (Shatru)",
    "Neutral Sign (Sama)",
    "Friendly Sign (Mitra)",
    "Own Sign (Swa)",
    "Moolatrikona",
    "Exalted (Uccha)",
)
_BAND_RANK = {band: i for i, band in enumerate(CERTIFIED_BAND_ORDER)}
UNGRADED_CERTIFIED = "Node"


def certified_d9_dignity(rec: Dict[str, Any]) -> Optional[str]:
    """Read the CERTIFIED D9 dignity the snapshot already carries.

    /chart computes it through the accepted `get_dignity`, including the BPHS
    Ch.47 node handling. There is NO local fallback: an absent value is reported
    unavailable per graha rather than reconstructed, because a locally rebuilt
    dignity is a second interpretation stack that would disagree with the
    certified D9 drawer on the same chart.
    """
    val = rec.get("d9_dignity")
    return val if isinstance(val, str) and val else None


def certified_rank(rec: Dict[str, Any], graha: Optional[str] = None) -> Optional[int]:
    """Comparable rank for the certified D9 dignity, or None when unrankable.

    NODES ARE NEVER RANKABLE IN THIS REPORT, whatever band the certified engine
    carries for them. `graha` is therefore load-bearing and not decorative.

    CORR-02 · QA-08. CORR-01 forced `Not graded` at the PUBLICATION layer but
    left this comparator reading only the record, so a snapshot carrying the
    engine's legitimate node band — Rahu in Taurus is `Exalted (Uccha)` under
    BPHS Ch.47 — made Rahu rankable again and it won the Ishta comparison
    outright against Venus in its own sign. The publication rule said one thing
    and the selector did another, which is the two-surfaces-disagree class this
    whole programme exists to remove. The graha is checked FIRST here, exactly as
    it is in `publish_dignity`.

    The certified value is untouched and still reaches QA through the engine
    block. This is a selection rule, not an edit to the chart engine.

    A SOLE node occupant still resolves, because `select_devata` does not call
    this for a single candidate: one occupant is not a comparison.

    None means "cannot be compared", never "lowest". Callers must not order it.
    """
    if graha in NODES:
        return None
    band = certified_d9_dignity(rec)
    if band is None or band == UNGRADED_CERTIFIED:
        return None
    return _BAND_RANK.get(band)


def certified_vargottama(rec: Dict[str, Any]) -> Optional[bool]:
    val = rec.get("vargottama")
    return bool(val) if isinstance(val, bool) else None


# ─── Atmakaraka · FOUNDER-RULED membership, FOUNDER-RULED tie policy ─────────

def select_atmakaraka(planets: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Highest certified `degree` among the seven classical grahas.

    On an EXACT top-degree tie the result is AK_AMBIGUOUS: no winner is chosen,
    and every AK-dependent conclusion is withheld downstream. That is a safety
    and unavailability policy, not an astrological tie doctrine, and it is not a
    licence to fall back to list order — which is precisely what the legacy
    implementation did through `AK_PLANETS` ordering.
    """
    present = []
    for g in AK_CANDIDATES:
        rec = planets.get(g)
        if not rec:
            continue
        deg = rec.get("degree")
        if not isinstance(deg, (int, float)) or deg != deg:  # NaN
            raise D9InputError(f"certified snapshot has no usable degree for {g}")
        present.append((g, float(deg)))

    if not present:
        return {"status": "UNAVAILABLE", "graha": None, "amatyakaraka": None,
                "candidates": [], "reason": "no chara-karaka graha in the snapshot"}

    ordered = sorted(present, key=lambda p: p[1], reverse=True)
    top_degree = ordered[0][1]
    tied = [g for g, d in ordered if abs(d - top_degree) <= AK_TIE_EPSILON]

    scheme = {"scheme": "seven_classical_grahas", "rahu_excluded": True,
              "authority": "founder_ruled_d9_001"}

    if len(tied) > 1:
        return {"status": "AK_AMBIGUOUS", "graha": None, "amatyakaraka": None,
                "tied_grahas": sorted(tied),
                "candidates": [{"graha": g, "degree": round(d, 4)} for g, d in ordered],
                "reason": "exact top-degree tie; no winner selected and all "
                          "AK-dependent conclusions are withheld",
                **scheme}

    amk = None
    if len(ordered) > 1:
        second_degree = ordered[1][1]
        second_tied = [g for g, d in ordered[1:]
                       if abs(d - second_degree) <= AK_TIE_EPSILON]
        amk = ordered[1][0] if len(second_tied) == 1 else None

    return {"status": "RESOLVED", "graha": ordered[0][0],
            "degree": round(top_degree, 4),
            "amatyakaraka": amk,
            "candidates": [{"graha": g, "degree": round(d, 4)} for g, d in ordered],
            **scheme}


# ─── Karakamsha ──────────────────────────────────────────────────────────────

def build_karakamsha(ak: Dict[str, Any],
                     planets: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """The Karakamsha sign — the Atmakaraka's CERTIFIED D9 sign.

    Refuses rather than defaulting when the certified D9 position is missing.
    The accepted browser module made the same call for the same reason: a v1
    that defaulted a missing navamsha position to 0 produced a full report on an
    Aries Karakamsha the chart never indicated.
    """
    if ak["status"] != "RESOLVED":
        return {"status": ak["status"], "sign_index": None, "sign": None,
                "lord": None, "reason": ak.get("reason")}
    doc = _doctrine()
    rec = planets.get(ak["graha"]) or {}
    si = rec.get("d9_sign_index")
    if not isinstance(si, int) or isinstance(si, bool) or not (0 <= si <= 11):
        return {"status": "UNAVAILABLE", "sign_index": None, "sign": None,
                "lord": None,
                "reason": "certified snapshot carries no D9 position for the "
                          "Atmakaraka, so the Karakamsha cannot be derived"}
    return {"status": "RESOLVED", "sign_index": si, "sign": doc.signs[si],
            "lord": doc.sign_lords[si], "from_graha": ak["graha"]}


def placements_of(planets: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Minimal placement view for the completeness checks, before facts are built."""
    out = {}
    for g in ORDER9:
        rec = planets.get(g)
        si = (rec or {}).get("d9_sign_index")
        ok = isinstance(si, int) and not isinstance(si, bool)
        out[g] = {"status": "RESOLVED" if ok else "UNAVAILABLE",
                  "d9_sign_index": si if ok else None}
    return out


def _house_from(sign_index: int, origin_index: int) -> int:
    return ((sign_index - origin_index) % 12) + 1


def karakamsha_house_occupants(house: int, kl_index: int,
                               planets: Dict[str, Dict[str, Any]]) -> List[str]:
    """Occupants of a house counted from the Karakamsha Lagna, in the ACCEPTED frame.

    D1 sign positions. This is `klInH` from the accepted module and it is NOT
    the legacy D9 report's D9-from-Swamsa frame.
    """
    out = []
    for g in ORDER9:
        rec = planets.get(g)
        if not rec:
            continue
        si = rec.get("sign_index")
        if not isinstance(si, int) or isinstance(si, bool):
            continue
        if _house_from(si, kl_index) == house:
            out.append(g)
    return out


def evaluate_karakamsha_houses(kl: Dict[str, Any],
                               planets: Dict[str, Dict[str, Any]],
                               houses: Sequence[int]) -> Dict[int, Dict[str, Any]]:
    """Run the accepted authority over the requested houses.

    Nothing is evaluated locally: occupancy and the house lord are supplied, and
    `karak_house_data.eval_house` decides what fires. When nothing fires the
    result carries an empty `fired` list and NO negative statement, which is the
    property that closes D9-B13.
    """
    if kl["status"] != "RESOLVED":
        return {h: {"status": kl["status"], "house": h, "fired": [],
                    "reason": kl.get("reason")} for h in houses}
    doc = _doctrine()
    kl_index = kl["sign_index"]
    out: Dict[int, Dict[str, Any]] = {}
    for h in houses:
        house_sign_index = (kl_index + h - 1) % 12
        lord = doc.sign_lords[house_sign_index]
        occ = karakamsha_house_occupants(h, kl_index, planets)
        result = kh.eval_house(h, occ, lord)
        result["status"] = "RESOLVED"
        result["house_sign_index"] = house_sign_index
        result["house_sign"] = doc.signs[house_sign_index]
        out[h] = result
    return out


# ─── Ishta Devata · the accepted Karakamsha ruling, certified comparator ─────

def select_ishta_devata(kl: Dict[str, Any],
                        planets: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Occupants of the twelfth SIGN from Karakamsha, by CERTIFIED D9 position.

    The accepted rule, in order: occupants first; a sole occupant wins; several
    are ranked by certified D9 dignity; equal highest are returned as
    CO-INDICATORS; an empty house falls back to the sign lord OF THAT HOUSE.

    Three legacy behaviours are absent and must stay absent:
      · ORDER9 array-position tie-breaking (D9-B18)
      · the D9-Lagna twelfth as a fallback, which is a different house on every
        chart where the Atmakaraka does not occupy the D9 lagna sign (D9-B27)
      · the Remedies module's lord-only doctrine, which never reads occupancy
        (D9-B28)
    """
    if kl["status"] != "RESOLVED":
        return {"status": kl["status"], "grahas": [], "deities": [],
                "mode": None, "reason": kl.get("reason")}

    doc = _doctrine()
    kl12_index = (kl["sign_index"] + 11) % 12
    kl12_lord = doc.sign_lords[kl12_index]

    # CORR-05 · QA-16A. AN INCOMPLETE OCCUPANCY SET PROVES NOTHING.
    #
    # D9-002 built the occupant list by equality and silently skipped any graha
    # whose D9 position was unavailable. With Venus unknown and every known graha
    # outside the target sign it concluded the house was EMPTY and invoked the
    # sign-lord fallback, publishing a deity on a chart where Venus may well have
    # been sitting there. The same hole makes a sole-occupant claim unprovable:
    # one known occupant plus one unknown position is not one occupant.
    #
    # So occupancy is established only over a COMPLETE set.
    unresolved = unresolved_d9_positions(placements_of(planets))
    if unresolved:
        return {
            "status": "UNAVAILABLE",
            "house_sign_index": kl12_index,
            "house_sign": doc.signs[kl12_index],
            "house_sign_lord": kl12_lord,
            "grahas": [], "deities": [], "orientations": [],
            "mode": None, "co_indicators": False,
            "unresolved_positions": unresolved,
            "reason": "one or more certified D9 positions are unavailable, so "
                      "the occupants of this house cannot be established and "
                      "neither the sole-occupant nor the empty-house rule can "
                      "be applied",
        }


    occupants = [g for g in ORDER9
                 if (planets.get(g) or {}).get("d9_sign_index") == kl12_index]

    def _rank(graha: str) -> Optional[int]:
        return certified_rank(planets.get(graha) or {}, graha)

    sel = kh.select_devata(occupants, kl12_lord, _rank, "Ishta Devata")
    grahas = list(sel["grahas"])

    # CORR-01 · a multi-occupant house containing an unrankable graha yields no
    # selection at all. The engine reports it as its own status rather than as a
    # resolved result with an empty graha list, so the publication layer cannot
    # mistake it for a co-indicator case.
    if sel["mode"] == "unrankable":
        return {
            "status": "UNRANKABLE",
            "house_sign_index": kl12_index,
            "house_sign": doc.signs[kl12_index],
            "house_sign_lord": kl12_lord,
            "occupants": occupants,
            "grahas": [],
            "deities": [],
            "orientations": [],
            "mode": "unrankable",
            "co_indicators": False,
            "unrankable_occupants": list(sel["unrankable"]),
            "dignity_authority": "certified_d9_snapshot",
            "basis": sel["basis"],
        }

    return {
        "status": "RESOLVED",
        "house_sign_index": kl12_index,
        "house_sign": doc.signs[kl12_index],
        "house_sign_lord": kl12_lord,
        "occupants": occupants,
        "grahas": grahas,
        "deities": [kh.DEITY_JAIMINI[g] for g in grahas if g in kh.DEITY_JAIMINI],
        # CORR-01 · deity AND the accepted plain-language orientation, paired, so
        # a co-indicator result stays multi-valued on both.
        "orientations": [{"deity": kh.DEITY_JAIMINI[g],
                          "orientation": kh.ISHTA_ARCHETYPE[g]}
                         for g in grahas
                         if g in kh.DEITY_JAIMINI and g in kh.ISHTA_ARCHETYPE],
        "mode": sel["mode"],
        "co_indicators": sel["mode"] == "co-indicator",
        "unrankable_occupants": list(sel["unrankable"]),
        "dignity_authority": "certified_d9_snapshot",
        "deity_authority": "accepted_jaimini_mapping",
        "orientation_authority": "accepted_karakamsha_archetype",
        "basis": sel["basis"],
    }


# ─── the assembled fact set ──────────────────────────────────────────────────

KARAKAMSHA_HOUSES_IN_SCOPE = (5, 7, 8, 10)

# D9-001-C classified dusthana membership as MECHANICAL DERIVATION and D9-002
# never built it, which QA-13 caught. It is a counting operation over certified
# fields and introduces no doctrine: which grahas sit in the D9 6th, 8th or 12th.
DUSTHANA_HOUSES = (6, 8, 12)


def unresolved_d9_positions(placements: Dict[str, Dict[str, Any]]) -> List[str]:
    """Grahas whose certified D9 position is not available.

    CORR-05 · QA-16. THIS IS THE FUNCTION THAT MAKES "UNKNOWN IS NOT NO" TRUE
    RATHER THAN STATED. Any graha in this list could be anywhere, so no claim
    about the CONTENTS OF A HOUSE — occupied, empty, sole — can be made while it
    is non-empty.
    """
    return sorted(g for g in ORDER9
                  if (placements.get(g) or {}).get("status") != "RESOLVED"
                  or (placements.get(g) or {}).get("d9_sign_index") is None)


def build_dusthana_membership(placements: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Grahas occupying the D9 6th, 8th or 12th. Certified inputs, no doctrine.

    CORR-05 · QA-16B. AN INCOMPLETE SET CANNOT PRODUCE `emphasis: False`.

    D9-002 returned RESOLVED with `emphasis` false whenever every KNOWN graha sat
    outside 6/8/12, and the reader was told "no part of this reading carries that
    emphasis". The unknown graha could be sitting in the 8th. That is a
    conclusion drawn from an absence of data, and it is the same fail-open shape
    as the Ishta case below.

    Requires the D9 lagna too, because a house number is meaningless without one.
    """
    unresolved = unresolved_d9_positions(placements)
    if unresolved:
        return {"status": "UNAVAILABLE", "grahas": [],
                "unresolved_positions": unresolved,
                "reason": "one or more certified D9 positions are unavailable, "
                          "so occupancy of the 6th, 8th and 12th cannot be "
                          "established either way"}

    resolved = {g: p for g, p in placements.items()
                if p.get("status") == "RESOLVED"}
    if not resolved or any(p.get("d9_house") is None for p in resolved.values()):
        return {"status": "UNAVAILABLE", "grahas": [],
                "reason": "no certified D9 house positions"}
    grahas = sorted(g for g, p in resolved.items()
                    if p.get("d9_house") in DUSTHANA_HOUSES)
    return {
        "status": "RESOLVED",
        "grahas": grahas,
        "houses": DUSTHANA_HOUSES,
        "emphasis": bool(grahas),
        "authority": "mechanical_derivation_over_certified_d9_house",
    }


# ─── Integration · three-valued · CORR-05 · QA-17 ────────────────────────────

def build_integration(placements: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Vargottama, with UNKNOWN kept distinct from FALSE.

    The certified adapter deliberately preserves a missing `vargottama` as None,
    and D9-002 discarded that distinction by filtering for True and publishing
    "no graha repeats its birth sign" whenever the filter came back empty. With
    one unknown and no known True, that sentence asserts something never
    established.

    Four states, and the middle two are the ones D9-002 collapsed:

      RESOLVED    at least one True, nothing unknown
      PARTIAL     at least one True, and something unknown — the known ones are
                  published and the result is marked incomplete
      NO_SIGNAL   everything known, none True. A genuine finding
      UNAVAILABLE none True but something unknown. NOT a finding
    """
    known_true, unknown = [], []
    for g in ORDER9:
        p = placements.get(g) or {}
        if p.get("status") != "RESOLVED":
            unknown.append(g)
            continue
        v = p.get("vargottama")
        if v is None:
            unknown.append(g)
        elif v is True:
            known_true.append(g)

    known_true, unknown = sorted(known_true), sorted(unknown)
    if known_true and not unknown:
        status = "RESOLVED"
    elif known_true:
        status = "PARTIAL"
    elif unknown:
        status = "UNAVAILABLE"
    else:
        status = "NO_SIGNAL"
    return {"status": status, "integrated_grahas": known_true,
            "unknown_grahas": unknown, "complete": not unknown}


def build_d9_facts(lagna: Dict[str, Any],
                   planets: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    doc = _doctrine()
    if not lagna:
        raise D9InputError("certified snapshot has no lagna")

    d9_lagna_index = lagna.get("d9_sign_index")
    if not isinstance(d9_lagna_index, int) or isinstance(d9_lagna_index, bool):
        d9_lagna = {"status": "UNAVAILABLE",
                    "reason": "certified snapshot carries no d9_sign_index for "
                              "the lagna"}
        d9_lagna_index = None
    else:
        d9_lagna = {"status": "RESOLVED", "sign_index": d9_lagna_index,
                    "sign": doc.signs[d9_lagna_index],
                    "lord": doc.sign_lords[d9_lagna_index]}

    placements: Dict[str, Dict[str, Any]] = {}
    for g in ORDER9:
        rec = planets.get(g)
        if not rec:
            continue
        si = rec.get("d9_sign_index")
        if not isinstance(si, int) or isinstance(si, bool):
            placements[g] = {"status": "UNAVAILABLE",
                             "reason": "no certified D9 position"}
            continue
        placements[g] = {
            "status": "RESOLVED",
            "d9_sign_index": si,
            "d9_sign": doc.signs[si],
            "d9_house": (_house_from(si, d9_lagna_index)
                         if d9_lagna_index is not None else None),
            "certified_dignity": certified_d9_dignity(rec),
            "vargottama": certified_vargottama(rec),
            "dignity_authority": "certified_d9_snapshot",
        }

    ak = select_atmakaraka(planets)
    kl = build_karakamsha(ak, planets)

    return {
        "d9_lagna": d9_lagna,
        "placements": placements,
        "atmakaraka": ak,
        "karakamsha": kl,
        "ishta_devata": select_ishta_devata(kl, planets),
        "karakamsha_houses": evaluate_karakamsha_houses(
            kl, planets, KARAKAMSHA_HOUSES_IN_SCOPE),
        "integration": build_integration(placements),
        "dusthana": build_dusthana_membership(placements),
    }
