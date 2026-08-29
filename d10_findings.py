"""
d10_findings.py — D10-003 · the server-owned deterministic findings authority.

PURE AND DETERMINISTIC. One public function, `build_core_findings`. It takes the
certified D10-002 prepare payload and returns facts and selector outcomes. It
performs no I/O, holds no state, calls no provider, reads no browser value and
touches no clock. The same payload yields the same result forever.

THE ONLY INPUT IS THE CERTIFIED SERVER RESULT. Nothing here reads a browser D10
calculation, browser dignity, browser AK/AmK, browser aspects, a /d10report
chart_brief or provider-supplied astrology. It reads the D10-002 payload and
nothing else, and it refuses that payload if it is malformed.

UNKNOWN != FALSE, ENFORCED AT THE WATERFALL. The tension selector evaluates its
priorities in order and STOPS at the first one whose inputs are unknown. It does
not descend, and it never reaches the Sun-Saturn fallback on an unknown. The
fallback is a climate contrast reachable only after four priorities have all
been VALIDLY evaluated FALSE.

WHAT THIS FILE DOES NOT DO. No prose of any kind. No Devata. No D1xD10 or
D9xD10. No Integrated Reading. No job title, self-employment trigger,
travel-career trigger, timing or remedy. No Lagna gloss, house signification or
planet-expression text: those corpora are unratified, and the old browser tables
are NOT reused merely because they exist.
"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Tuple

from d10_findings_contract import (
    DUSTHANA, FALLBACK_SUN_SATURN_CLIMATE, FALSE,
    MODE_OCCUPIED, MODE_THROUGH_LORD, OPERATIONAL_GROUPS,
    P1_JAIMINI_RIFT, P2_CORE_OPERATIONAL_CONFLICT, P3_VISIBILITY_GAP,
    P4_SUN_SATURN_FRICTION, RELATION_MUTUAL_DRISHTI, RELATION_NO_LINK,
    RELATION_SAME_HOUSE, STRONG_DIGNITIES_CLASSICAL, STRONG_DIGNITIES_NODE,
    PUBLICATION_PRESSURED, PUBLICATION_SUPPORTED,
    SUPPORTED_DIGNITIES, TRUE, UNKNOWN, WATERFALL_UNKNOWN,
    D10CoreFindings, Function, HeaderFacts, HeaderKaraka, HeaderStance,
    HouseView, LordPlacement, Money, MoneyHouse, OperationalGroup,
    OperationalHouse, Placement, PullVehicle, Stance, Standing, Strength,
    StrongPlanet, Tension, TensionPredicate,
)

NODES = frozenset({"Rahu", "Ketu"})
CK_RESOLVED = "RESOLVED"


class D10FindingsError(ValueError):
    """The certified payload is missing something this layer requires. Raised,
    never defaulted: a findings layer built from an incomplete chart would
    publish confident facts about placements it never had."""


# ─────────────────────────────────────────────────────────────────────────────
# strict readers
# ─────────────────────────────────────────────────────────────────────────────

def _obj(payload: Any, key: str, where: str) -> Mapping[str, Any]:
    if not isinstance(payload, Mapping):
        raise D10FindingsError(f"{where} is not an object")
    value = payload.get(key)
    if not isinstance(value, Mapping):
        raise D10FindingsError(f"{where}.{key} is missing or not an object")
    return value


def _house_no(value: Any, where: str) -> int:
    if type(value) is not int or not 1 <= value <= 12:
        raise D10FindingsError(f"{where}: house must be an integer 1-12, got {value!r}")
    return value


def _sign_index(value: Any, where: str) -> int:
    if type(value) is not int or not 0 <= value <= 11:
        raise D10FindingsError(f"{where}: sign_index must be 0-11, got {value!r}")
    return value


def _text(value: Any, where: str) -> str:
    if not isinstance(value, str) or not value:
        raise D10FindingsError(f"{where}: expected a non-empty string, got {value!r}")
    return value


# ─────────────────────────────────────────────────────────────────────────────
# house arithmetic
# ─────────────────────────────────────────────────────────────────────────────

def _count_from(a: int, b: int) -> int:
    """How many houses b is from a, counting a as the first. 1..12."""
    return ((b - a) % 12) + 1


def _is_6_8(a: int, b: int) -> bool:
    """A 6/8 relationship: one is the 6th from the other, which makes the other
    the 8th from it. Symmetric, and checked in both directions rather than
    assumed."""
    return {_count_from(a, b), _count_from(b, a)} == {6, 8}


def _is_2_12(a: int, b: int) -> bool:
    return {_count_from(a, b), _count_from(b, a)} == {2, 12}


def _is_1_7(a: int, b: int) -> bool:
    """Opposition. Distinct from same-house, which is tested separately."""
    return _count_from(a, b) == 7 and _count_from(b, a) == 7


# ─────────────────────────────────────────────────────────────────────────────
# reading the certified payload
# ─────────────────────────────────────────────────────────────────────────────

class _Chart:
    """A read-only view over the certified D10-002 payload.

    Every accessor raises on absence. There is no `.get(key, default)` anywhere
    in this class, so a missing placement cannot become a confident value.
    """

    def __init__(self, payload: Mapping[str, Any]):
        d10 = _obj(payload, "d10", "payload")
        self.lagna = _obj(d10, "lagna", "payload.d10")
        grahas = d10.get("grahas")
        if not isinstance(grahas, Mapping) or not grahas:
            raise D10FindingsError("payload.d10.grahas is missing or empty")
        self.grahas: Dict[str, Mapping[str, Any]] = dict(grahas)
        houses = d10.get("houses")
        if not isinstance(houses, list) or len(houses) != 12:
            raise D10FindingsError("payload.d10.houses must be a list of 12")
        self.houses: Dict[int, Mapping[str, Any]] = {}
        for h in houses:
            if not isinstance(h, Mapping):
                raise D10FindingsError("a house entry is not an object")
            self.houses[_house_no(h.get("house"), "house")] = h
        if set(self.houses) != set(range(1, 13)):
            raise D10FindingsError("payload.d10.houses does not cover 1-12 exactly once")
        self.chara_karaka = _obj(payload, "chara_karaka", "payload")
        self.atmakaraka = payload.get("atmakaraka")
        self.amatyakaraka = payload.get("amatyakaraka")
        self.jaimini = _obj(payload, "jaimini", "payload")
        self.d10_lagna_sign = _text(self.lagna.get("d10_sign"), "lagna.d10_sign")
        self.d10_lagna_sign_index = _sign_index(
            self.lagna.get("d10_sign_index"), "lagna.d10_sign_index")
        self.lagnesh_name = _text(self.lagna.get("d10_lord"), "lagna.d10_lord")

    # ── grahas ──────────────────────────────────────────────────────────────
    def graha(self, name: str) -> Mapping[str, Any]:
        rec = self.grahas.get(name)
        if not isinstance(rec, Mapping):
            raise D10FindingsError(f"certified payload has no graha {name!r}")
        return rec

    def placement(self, name: str) -> Placement:
        rec = self.graha(name)
        return Placement(
            planet=name,
            house=_house_no(rec.get("d10_house"), f"{name}.d10_house"),
            sign=_text(rec.get("d10_sign"), f"{name}.d10_sign"),
            sign_index=_sign_index(rec.get("d10_sign_index"), f"{name}.d10_sign_index"),
            dignity=_text(rec.get("d10_dignity"), f"{name}.d10_dignity"),
        )

    def lord_placement(self, name: str) -> LordPlacement:
        p = self.placement(name)
        return LordPlacement(planet=p.planet, house=p.house, sign=p.sign,
                             sign_index=p.sign_index, dignity=p.dignity)

    # ── houses ──────────────────────────────────────────────────────────────
    def house(self, n: int) -> Mapping[str, Any]:
        rec = self.houses.get(n)
        if rec is None:
            raise D10FindingsError(f"certified payload has no house {n}")
        return rec

    def occupants(self, n: int) -> List[str]:
        occ = self.house(n).get("occupants")
        if not isinstance(occ, list):
            raise D10FindingsError(f"house {n} occupants is not a list")
        return sorted(str(o) for o in occ)

    def house_lord(self, n: int) -> str:
        return _text(self.house(n).get("lord"), f"house {n} lord")

    def house_sign(self, n: int) -> str:
        return _text(self.house(n).get("sign"), f"house {n} sign")

    def house_view(self, n: int) -> HouseView:
        occ = self.occupants(n)
        return HouseView(
            house=n,
            sign=self.house_sign(n),
            sign_index=_sign_index(self.house(n).get("sign_index"), f"house {n}"),
            occupied=bool(occ),
            occupants=occ,
            mode=MODE_OCCUPIED if occ else MODE_THROUGH_LORD,
            lord=self.lord_placement(self.house_lord(n)),
        )

    # ── chara karaka ────────────────────────────────────────────────────────
    @property
    def karaka_resolved(self) -> bool:
        return self.chara_karaka.get("state") == CK_RESOLVED

    def karaka(self, block: Any, which: str) -> HeaderKaraka:
        if not isinstance(block, Mapping):
            raise D10FindingsError(f"{which} block is missing on a resolved chart")
        return HeaderKaraka(
            planet=_text(block.get("planet"), f"{which}.planet"),
            house=_house_no(block.get("d10_house"), f"{which}.d10_house"),
            sign=_text(block.get("d10_sign"), f"{which}.d10_sign"),
        )


# ─────────────────────────────────────────────────────────────────────────────
# sections
# ─────────────────────────────────────────────────────────────────────────────

def _pull_vehicle(c: _Chart) -> PullVehicle:
    """JAIMINI ONLY.

    The identities are the natal-ranked Chara Karakas, consumed as certified.
    Nothing here reranks them from D10 positions, and no Parasari aspect enters:
    the only relation consulted is the certified `jaimini` block, which the
    D10-002 engine derived from the canonical server rashi_drishti primitive.
    """
    if not c.karaka_resolved:
        reason = c.chara_karaka.get("state")
        return PullVehicle(available=False,
                           unavailable_reason=f"chara_karaka_{str(reason).lower()}")

    ak = c.karaka(c.atmakaraka, "atmakaraka")
    amk = c.karaka(c.amatyakaraka, "amatyakaraka")
    mutual = c.jaimini.get("ak_amk_mutual_rashi_drishti")
    if mutual is None:
        # The engine reports None when it will not assert a relation. That is
        # not False and must not become False here.
        return PullVehicle(available=False, ak=ak, amk=amk,
                           same_house=(ak.house == amk.house),
                           unavailable_reason="jaimini_relation_unavailable")
    if not isinstance(mutual, bool):
        raise D10FindingsError("jaimini relation is neither a boolean nor None")

    same_house = ak.house == amk.house
    if same_house:
        state = RELATION_SAME_HOUSE
    elif mutual:
        state = RELATION_MUTUAL_DRISHTI
    else:
        state = RELATION_NO_LINK
    return PullVehicle(available=True, ak=ak, amk=amk, same_house=same_house,
                       mutual_jaimini_rashi_drishti=mutual, relation_state=state)


def _operational_house(c: _Chart, n: int) -> OperationalHouse:
    """SUPPORTED and PRESSURED are independent and both are published.

    Supported, locked:
        lord dignity in {Uchcha, Sva, Mitra}  AND  lord D10 house not in {8,12}

    Pressured, per the format's own definition — "lord or occupants in H8/H12":
        the lord sits in H8 or H12,  OR  this house IS H8 or H12 and is occupied.

    H6 ALONE NEVER MEANS PRESSURED. There is no clause here that mentions H6,
    so involvement of the sixth house cannot contribute to pressure by any
    path.
    """
    occ = c.occupants(n)
    lord = c.lord_placement(c.house_lord(n))
    supported = (lord.dignity in SUPPORTED_DIGNITIES
                 and lord.house not in DUSTHANA)
    pressured = (lord.house in DUSTHANA) or (n in DUSTHANA and bool(occ))
    base_mode = MODE_OCCUPIED if occ else MODE_THROUGH_LORD
    # D10-003-CORR-01 · precedence for publication only, and the FALLTHROUGH IS
    # THE MODE, not a fifth label. A house that is neither supported nor
    # pressured is still occupied or still runs through its lord, and saying so
    # is more useful than saying NEUTRAL. The raw booleans above are the
    # evidence and are never overwritten by this.
    publication_state = (PUBLICATION_PRESSURED if pressured
                         else PUBLICATION_SUPPORTED if supported
                         else base_mode)
    return OperationalHouse(
        house=n, sign=c.house_sign(n), occupants=occ,
        lord=lord.planet, lord_house=lord.house, lord_sign=lord.sign,
        lord_dignity=lord.dignity,
        base_mode=base_mode, supported=supported, pressured=pressured,
        publication_state=publication_state,
    )


def _operational_map(c: _Chart) -> List[OperationalGroup]:
    return [OperationalGroup(group=name,
                             houses=[_operational_house(c, h) for h in houses])
            for name, houses in OPERATIONAL_GROUPS.items()]


# ── the tension waterfall ────────────────────────────────────────────────────

def _p1(c: _Chart) -> Tuple[str, Dict[str, Any]]:
    """JAIMINI_RIFT · AK and AmK share no house and do not mutually aspect.

    If either identity or the relation is unknown, this returns UNKNOWN and the
    caller STOPS. It does not descend: a chart whose karakas are ambiguous
    cannot be said to lack a rift.
    """
    if not c.karaka_resolved:
        return UNKNOWN, {"reason": f"chara_karaka_{str(c.chara_karaka.get('state')).lower()}"}
    mutual = c.jaimini.get("ak_amk_mutual_rashi_drishti")
    if mutual is None:
        return UNKNOWN, {"reason": "jaimini_relation_unavailable"}
    ak = c.karaka(c.atmakaraka, "atmakaraka")
    amk = c.karaka(c.amatyakaraka, "amatyakaraka")
    ev = {"ak": ak.planet, "ak_house": ak.house,
          "amk": amk.planet, "amk_house": amk.house,
          "same_house": ak.house == amk.house,
          "mutual_rashi_drishti": mutual}
    fired = (ak.house != amk.house) and not mutual
    return (TRUE if fired else FALSE), ev


def _p2(c: _Chart) -> Tuple[str, Dict[str, Any]]:
    """CORE_OPERATIONAL_CONFLICT · Lagnesh and 10th lord in 6/8 or 2/12."""
    lagnesh = c.lord_placement(c.lagnesh_name)
    tenth = c.lord_placement(c.house_lord(10))
    six_eight = _is_6_8(lagnesh.house, tenth.house)
    two_twelve = _is_2_12(lagnesh.house, tenth.house)
    ev = {"lagnesh": lagnesh.planet, "lagnesh_house": lagnesh.house,
          "tenth_lord": tenth.planet, "tenth_lord_house": tenth.house,
          "six_eight": six_eight, "two_twelve": two_twelve}
    return (TRUE if (six_eight or two_twelve) else FALSE), ev


def _p3(c: _Chart) -> Tuple[str, Dict[str, Any]]:
    """VISIBILITY_GAP · at least two grahas in H5 and at least two in H12."""
    h5, h12 = c.occupants(5), c.occupants(12)
    ev = {"h5_occupants": h5, "h5_count": len(h5),
          "h12_occupants": h12, "h12_count": len(h12)}
    return (TRUE if (len(h5) >= 2 and len(h12) >= 2) else FALSE), ev


def _p4(c: _Chart) -> Tuple[str, Dict[str, Any]]:
    """SUN_SATURN_FRICTION · same house, 1/7 axis, or 6/8."""
    sun, saturn = c.placement("Sun"), c.placement("Saturn")
    same = sun.house == saturn.house
    axis = _is_1_7(sun.house, saturn.house)
    six_eight = _is_6_8(sun.house, saturn.house)
    ev = {"sun_house": sun.house, "saturn_house": saturn.house,
          "same_house": same, "one_seven_axis": axis, "six_eight": six_eight}
    return (TRUE if (same or axis or six_eight) else FALSE), ev


_WATERFALL = (
    (1, P1_JAIMINI_RIFT, _p1),
    (2, P2_CORE_OPERATIONAL_CONFLICT, _p2),
    (3, P3_VISIBILITY_GAP, _p3),
    (4, P4_SUN_SATURN_FRICTION, _p4),
)


def _tension(c: _Chart) -> Tension:
    """SERVER AUTHORITY. The provider and the frontend may never choose this.

    Strict priority, evaluated in order. The first TRUE wins and evaluation
    stops. The first UNKNOWN stops evaluation with winner UNKNOWN — it is
    neither a winner nor a fallback, and lower priorities are NOT consulted,
    because a predicate that was never evaluated must not be reported FALSE.

    The fallback is reached only after all four have been VALIDLY evaluated
    FALSE. It is a climate contrast and carries no conflict claim: nothing in
    its evidence asserts conjunction, opposition, 6/8 or affliction.
    """
    states: List[TensionPredicate] = []
    for priority, name, fn in _WATERFALL:
        state, evidence = fn(c)
        states.append(TensionPredicate(priority=priority, name=name,
                                       state=state, evidence=evidence))
        if state == TRUE:
            return Tension(winner=name, priority=priority, evidence=evidence,
                           predicate_states=states)
        if state == UNKNOWN:
            return Tension(winner=WATERFALL_UNKNOWN, priority=None,
                           evidence=evidence, predicate_states=states,
                           stopped_at=priority)

    sun, saturn = c.placement("Sun"), c.placement("Saturn")
    return Tension(
        winner=FALLBACK_SUN_SATURN_CLIMATE, priority=None,
        # A CLIMATE CONTRAST, NOT A CONFLICT. House and dignity for each, and
        # nothing that could be read as a harsh relationship: the three
        # relationship predicates were all evaluated FALSE above and are
        # recorded there.
        evidence={"sun_house": sun.house, "sun_sign": sun.sign,
                  "sun_dignity": sun.dignity,
                  "saturn_house": saturn.house, "saturn_sign": saturn.sign,
                  "saturn_dignity": saturn.dignity,
                  "conflict_claimed": False},
        predicate_states=states)


def _money(c: _Chart) -> Money:
    """MECHANISM ONLY. Occupancy and lordship for H2 and H11. There is no
    field here for salary, income, wealth level, windfall or timing."""
    def block(n: int) -> MoneyHouse:
        occ = c.occupants(n)
        return MoneyHouse(house=n, sign=c.house_sign(n), occupants=occ,
                          empty=not occ,
                          lord=c.lord_placement(c.house_lord(n)))
    return Money(h2=block(2), h11=block(11))


def _strength(c: _Chart) -> Strength:
    """Section 12 eligibility. Narrower than Supported on purpose.

    A classical graha qualifies only on Uchcha or Sva. A node qualifies only on
    Uchcha. Mitra, Sama, Shatru, Neecha and a node's Ungraded never qualify.
    """
    strong: List[StrongPlanet] = []
    for name in sorted(c.grahas):
        p = c.placement(name)
        qualifying = (STRONG_DIGNITIES_NODE if name in NODES
                      else STRONG_DIGNITIES_CLASSICAL)
        if p.dignity in qualifying:
            strong.append(StrongPlanet(planet=name, dignity=p.dignity,
                                       house=p.house, sign=p.sign))
    return Strength(strong_planets=strong,
                    classical_qualifying_dignities=sorted(STRONG_DIGNITIES_CLASSICAL),
                    node_qualifying_dignities=sorted(STRONG_DIGNITIES_NODE))


# ─────────────────────────────────────────────────────────────────────────────
# the one public entry point
# ─────────────────────────────────────────────────────────────────────────────

def build_core_findings(prepare_payload: Mapping[str, Any]) -> D10CoreFindings:
    """Turn the certified D10-002 payload into the core findings layer.

    Pure. Deterministic. No I/O, no provider, no clock, no browser input.
    """
    c = _Chart(prepare_payload)
    # D10-007-CORR-01 · the certified identity travels with the findings.
    token = prepare_payload.get("chart_token") if isinstance(
        prepare_payload, Mapping) else None
    if not isinstance(token, str) or not token:
        raise D10FindingsError(
            "certified payload carries no chart_token; a findings layer with "
            "no identity cannot be checked against any other layer")

    lagnesh = c.lord_placement(c.lagnesh_name)
    sun = c.placement("Sun")
    tenth_lord = c.lord_placement(c.house_lord(10))
    pv = _pull_vehicle(c)

    header = HeaderFacts(
        stance=HeaderStance(d10_lagna_sign=c.d10_lagna_sign,
                            d10_lagna_sign_index=c.d10_lagna_sign_index),
        work_ruler=lagnesh,
        standing=sun,
        # None, not a blank chip, when the karakas are not resolved.
        pull=pv.ak if pv.ak is not None else None,
        vehicle=pv.amk if pv.amk is not None else None,
    )

    return D10CoreFindings(
        chart_token=token,
        header_facts=header,
        stance=Stance(d10_lagna_sign=c.d10_lagna_sign,
                      d10_lagna_sign_index=c.d10_lagna_sign_index,
                      lagnesh=lagnesh),
        # H10 + H10 LORD + H6. H3 is not read anywhere in this call.
        function=Function(h10=c.house_view(10), h6=c.house_view(6)),
        standing=Standing(sun=sun, h2_occupants=c.occupants(2),
                          h2_lord=c.lord_placement(c.house_lord(2)),
                          h10_lord=tenth_lord),
        pull_vehicle=pv,
        operational_map=_operational_map(c),
        tension=_tension(c),
        money=_money(c),
        strength=_strength(c),
    )
