"""
d10_contract.py — D10-002 · THE PUBLIC SURFACE OF /d10/prepare.

THE REQUEST IS A TOKEN AND NOTHING ELSE. `D10PrepareRequest` accepts one field
and forbids every other, so no caller can smuggle a D10 Lagna, a placement, a
house, a dignity, an AK, an AmK, an aspect, a lordship, a Devatā, a tension or
any other browser-asserted astrology into the D10 layer. This is the hardened
convention `d5_contract.D5PrepareRequest` already sets, and it is preserved
rather than restated loosely: `extra = "forbid"` means an injected field is a
422 naming the field, not a silent discard.

THE RESPONSE IS MECHANICAL. Every field below is a placement, a derivation from
a placement, or a state code. There is no prose, no provider plan, no tension,
no Devatā, no Three Instructions, no D1xD10 or D9xD10 handshake and no report
section. Those are D10-002 deferrals and the contract has nowhere to put them.

PYDANTIC v1 AND v2. The Founder host and the QA host have differed before, so
strictness is expressed once through the same shim d5_contract uses.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

import pydantic
from pydantic import BaseModel, Field, StrictStr

_PYDANTIC_V2 = pydantic.VERSION.startswith("2")

if _PYDANTIC_V2:
    from pydantic import ConfigDict

    class _Forbidding(BaseModel):
        model_config = ConfigDict(extra="forbid")
else:  # pragma: no cover - exercised only on a v1 host

    class _Forbidding(BaseModel):
        class Config:
            extra = "forbid"


ROUTE_VERSION = "d10.prepare.v1"


class D10PrepareRequest(_Forbidding):
    """One opaque chart token. Every other field is rejected with a 422."""
    chart_token: StrictStr = Field(..., min_length=8, max_length=256)


class D10Policy(BaseModel):
    """What this layer did and did not do, stated in the payload so no reader
    has to infer it from the absence of a field."""
    module: str = "D10 · Dashamsha"
    house_system: str = "whole-sign"
    mapping_rule: str = "odd-signs-from-self, even-signs-from-ninth"
    portion_arc_degrees: float = 3.0
    portion_count: int = 10
    chara_karaka_system: str = "7-karaka"
    rahu_in_chara_karaka: bool = False
    #: The comparison basis is the server-owned integer arcsecond, computed
    #: from the unrounded degree before display rounding.
    chara_karaka_basis: str = "karaka_arcsecond"
    chara_karaka_rounding: str = "half-up"
    #: Mūlatrikoṇa is not in the D10 vocabulary at all. See d10_engine.
    moolatrikona_published: bool = False
    node_dignity_states: List[str] = ["Uchcha", "Neecha", "Ungraded"]
    rashi_drishti_source: str = "d5_predicates.rashi_drishti"
    #: Carried mechanically, weighted at zero.
    retrograde_interpretive_weight: float = 0.0
    combust_interpretive_weight: float = 0.0


class D10Lagna(BaseModel):
    d10_sign_index: int = Field(ge=0, le=11)
    d10_sign: str
    d10_sign_abbr: str
    d10_lord: str
    source_sign_index: int = Field(ge=0, le=11)
    source_sign: str


class D10Graha(BaseModel):
    planet: str
    d10_sign_index: int = Field(ge=0, le=11)
    d10_sign: str
    d10_sign_abbr: str
    #: ge=1 is load-bearing. A house of 0 is unrepresentable in this contract,
    #: so the browser's `?.house || 0` idiom cannot be reproduced here even by
    #: accident: a 0 is a ValidationError, not a publication.
    d10_house: int = Field(ge=1, le=12)
    d10_lord: str
    d10_dignity: str
    retrograde: bool
    combust: bool


class D10House(BaseModel):
    house: int = Field(ge=1, le=12)
    sign_index: int = Field(ge=0, le=11)
    sign: str
    sign_abbr: str
    lord: str
    occupants: List[str]


class CharaKarakaRank(BaseModel):
    planet: str
    rank: int = Field(ge=1, le=7)
    karaka_arcsecond: int = Field(ge=0)


class CharaKarakaBlock(BaseModel):
    """Three states, kept distinct.

    RESOLVED  — a strict total order exists; `ranking` is present
    AMBIGUOUS — two or more eligible grahas share an integer arcsecond;
                `tied_grahas` names them and `ranking` is absent
    INVALID   — an eligible graha's basis is missing or malformed

    AMBIGUOUS is a determinate finding and must never be read as missing data.
    """
    state: str
    reason: Optional[str] = None
    eligible_planets: List[str]
    rahu_eligible: bool
    ketu_eligible: bool
    tied_grahas: Optional[List[str]] = None
    ranking: Optional[List[CharaKarakaRank]] = None


class KarakaPlacement(BaseModel):
    planet: str
    karaka_arcsecond: int = Field(ge=0)
    d10_sign: str
    d10_sign_index: int = Field(ge=0, le=11)
    d10_house: int = Field(ge=1, le=12)


class JaiminiBlock(BaseModel):
    """UNKNOWN != FALSE, expressed in the type.

    The three relation fields are Optional[bool] and are None — not False —
    whenever `available` is False. A reader that treats None as False is making
    a claim the server refused to make, and the field name says so.
    """
    available: bool
    ak_aspects_amk: Optional[bool] = None
    amk_aspects_ak: Optional[bool] = None
    ak_amk_mutual_rashi_drishti: Optional[bool] = None
    unavailable_reason: Optional[str] = None


class D10Block(BaseModel):
    engine_version: str
    lagna: D10Lagna
    grahas: Dict[str, D10Graha]
    houses: List[D10House]


class D10PrepareResponse(BaseModel):
    route_version: str = ROUTE_VERSION
    chart_token: str
    policy: D10Policy
    calculation_meta: Dict[str, Any]
    d10: D10Block
    chara_karaka: CharaKarakaBlock
    atmakaraka: Optional[KarakaPlacement] = None
    amatyakaraka: Optional[KarakaPlacement] = None
    jaimini: JaiminiBlock


def build_response(facts: Dict[str, Any], chart_token: str,
                   calculation_meta: Dict[str, Any]) -> D10PrepareResponse:
    """Assemble the public response from engine facts. Adds nothing, decides
    nothing, and words nothing."""
    return D10PrepareResponse(
        route_version=ROUTE_VERSION,
        chart_token=chart_token,
        policy=D10Policy(),
        calculation_meta=calculation_meta,
        d10=D10Block(
            engine_version=facts["engine_version"],
            lagna=D10Lagna(**facts["lagna"]),
            grahas={k: D10Graha(**v) for k, v in facts["grahas"].items()},
            houses=[D10House(**h) for h in facts["houses"]],
        ),
        chara_karaka=CharaKarakaBlock(**facts["chara_karaka"]),
        atmakaraka=(KarakaPlacement(**facts["atmakaraka"])
                    if facts["atmakaraka"] is not None else None),
        amatyakaraka=(KarakaPlacement(**facts["amatyakaraka"])
                      if facts["amatyakaraka"] is not None else None),
        jaimini=JaiminiBlock(**facts["jaimini"]),
    )
