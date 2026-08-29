"""
d10_findings_contract.py — D10-003 · the shape of the core findings layer.

DETERMINISTIC FACTS AND SELECTOR OUTCOMES. Nothing in this file can hold a
customer-facing sentence: there is no free-text field anywhere in it, so a
prose key is a contract violation rather than something quietly ignored. That
is the D9-R2 provider lesson applied one layer earlier.

WHAT IS DELIBERATELY ABSENT, AND WHY IT IS ABSENT RATHER THAN EMPTY:

  * no Lagna gloss, no work-behaviour or overreach line, no "the days look
    like" line, no virtue or vice line — their corpora are unratified, and a
    placeholder field would invite someone to fill it from the old unproven
    product tables;
  * no rank, fame, success or reputation claim;
  * no Devata, no D1xD10, no D9xD10, no Integrated Reading;
  * no salary, income, wealth level, windfall or financial timing;
  * no job title, self-employment trigger, travel-career trigger, timing or
    remedy.

UNKNOWN != FALSE IS EXPRESSED IN THE TYPES. Every field that could be unknown
is Optional and is None when unknown, never False and never a sentinel. The
tension waterfall carries an explicit UNKNOWN state that is not a winner and
not a fallback.

Strict everywhere: `extra = "forbid"`.
"""
from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

import pydantic
from pydantic import BaseModel, Field

_PYDANTIC_V2 = pydantic.VERSION.startswith("2")

if _PYDANTIC_V2:
    from pydantic import ConfigDict

    class Strict(BaseModel):
        model_config = ConfigDict(extra="forbid")
else:  # pragma: no cover - exercised only on a v1 host

    class Strict(BaseModel):
        class Config:
            extra = "forbid"


FINDINGS_VERSION = "d10.findings.v1"

# ── house occupancy modes ────────────────────────────────────────────────────
#: A house with at least one graha in it.
MODE_OCCUPIED = "OCCUPIED"
#: A vacant house. The format requires downstream prose for an empty H10 to
#: begin exactly with "Through lord", so the mode is published as a state the
#: renderer can branch on rather than inferred from an empty list.
MODE_THROUGH_LORD = "THROUGH_LORD"

# ── tension waterfall ────────────────────────────────────────────────────────
P1_JAIMINI_RIFT = "JAIMINI_RIFT"
P2_CORE_OPERATIONAL_CONFLICT = "CORE_OPERATIONAL_CONFLICT"
P3_VISIBILITY_GAP = "VISIBILITY_GAP"
P4_SUN_SATURN_FRICTION = "SUN_SATURN_FRICTION"
FALLBACK_SUN_SATURN_CLIMATE = "FALLBACK_SUN_SATURN_CLIMATE"
#: Not a winner and not a fallback. A third outcome.
WATERFALL_UNKNOWN = "UNKNOWN"

TRUE, FALSE, UNKNOWN = "TRUE", "FALSE", "UNKNOWN"

# ── operational map groups · locked by the format ────────────────────────────
GROUP_ENTER_ROLE = "ENTER_ROLE"
GROUP_DO_WORK = "DO_WORK"
GROUP_BE_SEEN_AND_PAID = "BE_SEEN_AND_PAID"
GROUP_HANDLE_PRESSURE = "HANDLE_PRESSURE"
GROUP_PATRONS = "PATRONS"

#: Five groups, twelve houses, each house exactly once. Asserted by test.
OPERATIONAL_GROUPS: Dict[str, tuple] = {
    GROUP_ENTER_ROLE: (1, 3, 5),
    GROUP_DO_WORK: (6, 10, 4),
    GROUP_BE_SEEN_AND_PAID: (2, 7, 11),
    GROUP_HANDLE_PRESSURE: (8, 12),
    GROUP_PATRONS: (9,),
}

#: The Supported predicate, locked. Mulatrikona is absent because D10 publishes
#: no synthetic MT at all, so it cannot appear in a dignity to be tested.
SUPPORTED_DIGNITIES = frozenset({"Uchcha", "Sva", "Mitra"})
#: Section 12 strength. Narrower than Supported on purpose: Mitra does not
#: qualify a classical graha, and no node qualifies except on Uchcha.
STRONG_DIGNITIES_CLASSICAL = frozenset({"Uchcha", "Sva"})
STRONG_DIGNITIES_NODE = frozenset({"Uchcha"})
#: Houses that carry pressure.
DUSTHANA = frozenset({8, 12})

#: D10-003-CORR-01 · the COMPLETE set of publication states.
#:
#:     if pressured:   PRESSURED
#:     elif supported: SUPPORTED
#:     else:           base_mode          (OCCUPIED or THROUGH_LORD)
#:
#: There is no fifth value. A house that is neither supported nor pressured
#: still has a mode, so it never needs a "nothing to say" label, and the old
#: NEUTRAL is now STRUCTURALLY IMPOSSIBLE rather than merely unused: the field
#: below is a Literal over exactly these four, so any other string is a
#: ValidationError at construction.
PUBLICATION_STATES = ("OCCUPIED", "THROUGH_LORD", "SUPPORTED", "PRESSURED")
PUBLICATION_PRESSURED = "PRESSURED"
PUBLICATION_SUPPORTED = "SUPPORTED"


# ─────────────────────────────────────────────────────────────────────────────
# shared shapes
# ─────────────────────────────────────────────────────────────────────────────

class Placement(Strict):
    """One graha, where it sits in D10."""
    planet: str
    house: int = Field(ge=1, le=12)
    sign: str
    sign_index: int = Field(ge=0, le=11)
    dignity: str


class LordPlacement(Strict):
    """A house lord and where that lord itself sits."""
    planet: str
    house: int = Field(ge=1, le=12)
    sign: str
    sign_index: int = Field(ge=0, le=11)
    dignity: str


# ─────────────────────────────────────────────────────────────────────────────
# header chips
# ─────────────────────────────────────────────────────────────────────────────

class HeaderStance(Strict):
    """No one-word gloss. D10_LAGNA_DESC is unratified product corpus and this
    flight will not supply a field for it."""
    d10_lagna_sign: str
    d10_lagna_sign_index: int = Field(ge=0, le=11)


class HeaderKaraka(Strict):
    planet: str
    house: int = Field(ge=1, le=12)
    sign: str


class HeaderFacts(Strict):
    stance: HeaderStance
    work_ruler: LordPlacement
    standing: Placement
    #: None when the Chara Karaka state is not RESOLVED. Not a blank chip and
    #: not a guess.
    pull: Optional[HeaderKaraka] = None
    vehicle: Optional[HeaderKaraka] = None


# ─────────────────────────────────────────────────────────────────────────────
# the core triad
# ─────────────────────────────────────────────────────────────────────────────

class Stance(Strict):
    """SPEAKER · PARASHARA. Selector inputs only."""
    speaker: str = "PARASHARA"
    d10_lagna_sign: str
    d10_lagna_sign_index: int = Field(ge=0, le=11)
    lagnesh: LordPlacement


class HouseView(Strict):
    """One house, as Function and the operational map both need it."""
    house: int = Field(ge=1, le=12)
    sign: str
    sign_index: int = Field(ge=0, le=11)
    occupied: bool
    occupants: List[str]
    mode: Literal["OCCUPIED", "THROUGH_LORD"]
    lord: LordPlacement


class Function(Strict):
    """SPEAKER · PARASHARA · H10 + H10 LORD + H6.

    H3 IS FORBIDDEN HERE. It belongs to the Stance / Enter-the-role family, and
    the boundary is enforced by this contract having nowhere to put it: there is
    no h3 field, so H3 cannot enter Function even by accident.
    """
    speaker: str = "PARASHARA"
    h10: HouseView
    h6: HouseView


class Standing(Strict):
    """SPEAKER · DIGNITY + PARASHARA.

    Facts only. No claim about rank, fame, success or reputation — there is no
    field that could carry one.
    """
    speaker: str = "DIGNITY + PARASHARA"
    sun: Placement
    h2_occupants: List[str]
    h2_lord: LordPlacement
    h10_lord: LordPlacement


# ─────────────────────────────────────────────────────────────────────────────
# pull and vehicle · Jaimini only
# ─────────────────────────────────────────────────────────────────────────────

class PullVehicle(Strict):
    """SPEAKER · JAIMINI.

    The identities are the NATAL-ranked Chara Karakas read in D10. They are
    never reranked from D10 positions. The relation uses only the canonical
    server rashi_drishti primitive; no Parasari aspect enters this block.

    `available` False means the Chara Karaka state was not RESOLVED. Every
    other field is then None — not False, not an empty string.
    """
    speaker: str = "JAIMINI"
    available: bool
    unavailable_reason: Optional[str] = None
    ak: Optional[HeaderKaraka] = None
    amk: Optional[HeaderKaraka] = None
    same_house: Optional[bool] = None
    mutual_jaimini_rashi_drishti: Optional[bool] = None
    #: SAME_HOUSE · MUTUAL_DRISHTI · NO_LINK, or None when unavailable.
    relation_state: Optional[str] = None


RELATION_SAME_HOUSE = "SAME_HOUSE"
RELATION_MUTUAL_DRISHTI = "MUTUAL_DRISHTI"
RELATION_NO_LINK = "NO_LINK"


# ─────────────────────────────────────────────────────────────────────────────
# operational map
# ─────────────────────────────────────────────────────────────────────────────

class OperationalHouse(Strict):
    """Two independent booleans, deliberately not collapsed into one enum.

    A lossy status word would destroy the evidence: a house can be both
    supported by its lord's dignity and pressured by that lord sitting in a
    dusthana, and a reader auditing the finding needs to see both. Publication
    precedence is recorded separately in `publication_state`; the raw booleans
    stay inspectable.
    """
    house: int = Field(ge=1, le=12)
    sign: str
    occupants: List[str]
    lord: str
    lord_house: int = Field(ge=1, le=12)
    lord_sign: str
    lord_dignity: str
    base_mode: Literal["OCCUPIED", "THROUGH_LORD"]
    supported: bool
    pressured: bool
    #: PRESSURED wins over SUPPORTED, and a house that is neither falls back to
    #: its own mode. Derived, and derivable again by any reader from
    #: `pressured`, `supported` and `base_mode` above — the raw booleans are
    #: never overwritten by the precedence.
    #:
    #: A Literal, not a str: NEUTRAL and every other invention are rejected at
    #: construction rather than caught by a reviewer.
    publication_state: Literal["OCCUPIED", "THROUGH_LORD", "SUPPORTED",
                               "PRESSURED"]


class OperationalGroup(Strict):
    group: str
    houses: List[OperationalHouse]


# ─────────────────────────────────────────────────────────────────────────────
# tension
# ─────────────────────────────────────────────────────────────────────────────

class TensionPredicate(Strict):
    priority: int = Field(ge=1, le=4)
    name: str
    #: TRUE · FALSE · UNKNOWN. Never a bare bool: the third state is the point.
    state: str
    evidence: Dict[str, Any]


class Tension(Strict):
    """Server authority. The provider and the frontend may never choose this.

    `winner` is one of the four priorities, the fallback, or UNKNOWN. UNKNOWN is
    NOT a fallback: an unresolvable input stops the waterfall where it stands
    rather than descending into a Sun-Saturn claim the chart does not support.
    """
    winner: str
    #: 1-4 for a real winner, None for the fallback and for UNKNOWN.
    priority: Optional[int] = None
    evidence: Dict[str, Any]
    predicate_states: List[TensionPredicate]
    stopped_at: Optional[int] = None


# ─────────────────────────────────────────────────────────────────────────────
# money and strength
# ─────────────────────────────────────────────────────────────────────────────

class MoneyHouse(Strict):
    """Mechanism only. No salary, income amount, wealth level, windfall or
    financial timing field exists here."""
    house: int = Field(ge=1, le=12)
    sign: str
    occupants: List[str]
    empty: bool
    lord: LordPlacement


class Money(Strict):
    speaker: str = "PARASHARA"
    h2: MoneyHouse
    h11: MoneyHouse


class StrongPlanet(Strict):
    planet: str
    dignity: str
    house: int = Field(ge=1, le=12)
    sign: str


class Strength(Strict):
    """Section 12 eligibility only. No virtue or vice prose: their corpus is
    unratified and there is no field for it."""
    strong_planets: List[StrongPlanet]
    classical_qualifying_dignities: List[str]
    node_qualifying_dignities: List[str]


# ─────────────────────────────────────────────────────────────────────────────
# the whole thing
# ─────────────────────────────────────────────────────────────────────────────

class D10CoreFindings(Strict):
    findings_version: str = FINDINGS_VERSION
    #: D10-007-CORR-01 · the certified chart this findings layer describes.
    #: Carried so every downstream layer can prove it is reasoning about ONE
    #: chart rather than trusting the caller to have passed matching inputs.
    chart_token: str
    header_facts: HeaderFacts
    stance: Stance
    function: Function
    standing: Standing
    pull_vehicle: PullVehicle
    operational_map: List[OperationalGroup]
    tension: Tension
    money: Money
    strength: Strength
