"""
d5_contract.py — D5-001 · THE PUBLIC SURFACE OF /d5/prepare.

THE REQUEST IS A TOKEN AND NOTHING ELSE. `D5PrepareRequest` accepts one field
and forbids every other, so no caller can smuggle birth data, a browser-computed
fact, a selected state or an engine parameter into the D5 layer. The token is
opaque: it is bounded in length and type, and D5 invents no meaning for its
characters — no regex, no prefix convention, no embedded identifier.

PYDANTIC v1 AND v2. The Founder host and the QA host have differed on this
before, so the strictness is expressed once through a shim rather than in a form
that only one major version honours. Nothing in the contract depends on which
branch is taken.
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


# D5-008 · the deliberate contract expansion D5-001 reserved. v1 published
# certified placement facts only; v2 adds the operational provenance, the
# scoring surface and the deterministic report payload.
ROUTE_VERSION = "d5.prepare.v2"


class D5PrepareRequest(_Forbidding):
    """One opaque chart token. Every other field is rejected."""
    chart_token: StrictStr = Field(..., min_length=8, max_length=256)


class D5Policy(BaseModel):
    module: str = "D5 · Panchamsha"
    house_system: str = "whole-sign"
    node_independent_graha_drishti: bool = False
    chara_karaka_system: str = "7-karaka"
    rahu_in_chara_karaka: bool = False
    #: D5-008 · TRUE since D5-005 locked the server-side Jaimini primitive and
    #: D5-006 put it into live rule evaluation. Publishing the D5-001 value here
    #: would be a STALE POLICY: the response would deny evaluating a relation
    #: the score in the same payload depends on.
    rasi_drishti_evaluated: bool = True
    segment_arc_degrees: int = 6
    segment_count: int = 5


class D5Placement(BaseModel):
    subject: str
    source_longitude: Optional[float] = None
    source_sign: str
    source_sign_index: int
    source_degree_in_sign: float
    source_modality: str
    segment_number: int
    segment_index: int
    segment_start_degree: float
    segment_end_degree: float
    tattva: str
    tattva_lords: List[str]
    counting_start_sign: str
    counting_start_sign_index: int
    d5_sign: str
    d5_sign_index: int
    d5_house: Optional[int] = None


class D5House(BaseModel):
    house: int
    sign: str
    sign_index: int
    lord: str
    occupants: List[str]


class D5LagnaLord(BaseModel):
    planet: str
    rules_d5_sign: str
    rules_d5_sign_index: int
    placement: Optional[D5Placement] = None


class D5Block(BaseModel):
    lagna: D5Placement
    lagna_lord: D5LagnaLord
    houses: List[D5House]
    grahas: Dict[str, D5Placement]


class CharaKarakaEntry(BaseModel):
    karaka: Optional[str] = None
    planet: str
    rank: int
    source_sign: str
    source_sign_index: int
    source_degree_in_sign: float
    source_arcseconds: float
    ranking_key_ten_thousandths_degree: int
    tie_priority: int


class CharaKarakaBlock(BaseModel):
    system: str
    rahu_eligible: bool
    ketu_eligible: bool
    eligible_planets: List[str]
    assignments: Dict[str, CharaKarakaEntry]
    ranking: List[CharaKarakaEntry]


class D1FifthLordMirroring(BaseModel):
    d1_fifth_house_sign: str
    d1_fifth_house_sign_index: int
    planet: str
    d1_sign: str
    d1_sign_index: int
    d1_house: int
    d1_degree_in_sign: float
    d1_longitude: Optional[float] = None
    segment_number: int
    tattva: str
    tattva_lords: List[str]
    d5_sign: str
    d5_sign_index: int
    d5_house: int


class KarakamshaBlock(BaseModel):
    atmakaraka: str
    d9_ak_sign: str
    d9_ak_sign_index: int
    d5_karakamsha_sign: str
    d5_karakamsha_sign_index: int
    d5_karakamsha_house: int
    transformation: str


class FoundationalBlock(BaseModel):
    chara_karakas: CharaKarakaBlock
    d1_fifth_lord_mirroring: D1FifthLordMirroring
    karakamsha: KarakamshaBlock


class CurrentPeriod(BaseModel):
    mahadasha: Optional[str] = None
    antardasha: Optional[str] = None


class CurrentTransits(BaseModel):
    as_of: str
    jupiter_sign_index: Optional[int] = None
    saturn_sign_index: Optional[int] = None


class OperationalBlock(BaseModel):
    """BOUNDED provenance and context.

    No birth date, no birth time, no coordinates, no raw snapshot, no host
    detail and no exception text — only which sources answered and the two
    current-period identities the timing rules used.
    """
    score_ready: bool
    current_period: CurrentPeriod
    current_transits: CurrentTransits
    source_status: Dict[str, str]


class ScoredRule(BaseModel):
    """One additive rule's scoring entry. Explicit, so no frontend has to
    reconstruct an Effective Weight."""
    rule_id: str
    status: str
    polarity: str
    base_weight: float
    participants: List[str]
    participant_multipliers: Dict[str, float]
    rule_multiplier: float
    effective_weight: float
    power_vector_hits: List[str]


class ScoreBand(BaseModel):
    code: str
    label: str


class CoreAuthorityBlock(BaseModel):
    bucket_scores: Dict[str, float]
    primary: Optional[str] = None
    leaders: List[str]
    tied: bool
    override: Optional[str] = None


class PurvaPunyaBlock(BaseModel):
    score: float
    classification: str
    no_signal: bool
    override: Optional[str] = None
    member_rule_ids: List[str]
    fired_rule_ids: List[str]


class PowerVectorBlock(BaseModel):
    vectors: Dict[str, Dict[str, Any]]
    primary: Optional[str] = None
    leaders: List[str]
    tied: bool


class ScoringBlock(BaseModel):
    score_ready: bool
    final_score: float
    score_band: ScoreBand
    rules: Dict[str, ScoredRule]
    core_authority: CoreAuthorityBlock
    purva_punya: PurvaPunyaBlock
    primary_power_vector: PowerVectorBlock
    triangulation_bindings: Dict[str, Any]


class ScoredFinding(BaseModel):
    rule_id: str
    polarity: str
    base_weight: float
    effective_weight: float
    participants: List[str]
    power_vector_hits: List[str]


class QuickSnapshot(BaseModel):
    final_score: float
    score_band: ScoreBand
    core_authority: Dict[str, Any]
    purva_punya_classification: str
    purva_punya_no_signal: bool
    primary_power_vector: Dict[str, Any]


class TimingEntry(BaseModel):
    rule_id: str
    status: str
    base_weight: float
    effective_weight: float
    evidence: Dict[str, Any]


class ClientSection(BaseModel):
    key: str
    title: str
    body: str
    state: str
    planets: List[str]


class ClientSignature(BaseModel):
    """One fired rule's MEANING. No rule_id, no weight, no status code."""
    key: str
    chapter: str
    title: str
    body: str
    state: str
    planets: List[str]


class ClientReading(BaseModel):
    """The Founder report structure, in the Founder's order."""
    quick_snapshot: Dict[str, str]
    foundational_metrics: List[Dict[str, str]]
    archetypes: Dict[str, Dict[str, Any]]
    temporal_activation: Dict[str, Any]
    karmic_friction: Dict[str, Any]
    detailed_analysis: Dict[str, Any]   # chapters carry narrative + supporting
    detailed_signatures: List[ClientSignature]


class ReportBlock(BaseModel):
    title: str
    subtitle: str
    quick_snapshot: QuickSnapshot
    client_reading: ClientReading
    foundational: Dict[str, Any]
    authority: CoreAuthorityBlock
    purva_punya: PurvaPunyaBlock
    power_vector: PowerVectorBlock
    timing: List[TimingEntry]
    triangulation: Dict[str, Any]
    scored_findings: List[ScoredFinding]


class D5PrepareResponse(BaseModel):
    route_version: str = ROUTE_VERSION
    chart_token: str
    policy: D5Policy
    calculation_meta: Dict[str, Any]
    d5: D5Block
    foundational: FoundationalBlock
    operational: OperationalBlock
    scoring: ScoringBlock
    report: ReportBlock


def build_response(facts: Dict[str, Any], chart_token: str,
                   calculation_meta: Dict[str, Any],
                   operational: Optional[Dict[str, Any]] = None,
                   scoring: Optional[Dict[str, Any]] = None,
                   report: Optional[Dict[str, Any]] = None
                   ) -> D5PrepareResponse:
    """Assemble the v2 public response.

    STILL NO NARRATIVE. The scoring and report blocks are deterministic data
    built by the accepted engines; nothing here interprets, ranks or words
    anything.
    """
    return D5PrepareResponse(
        route_version=ROUTE_VERSION,
        chart_token=chart_token,
        policy=D5Policy(),
        calculation_meta=calculation_meta,
        d5=D5Block(
            lagna=D5Placement(**facts["lagna"]),
            lagna_lord=D5LagnaLord(**facts["lagna_lord"]),
            houses=[D5House(**h) for h in facts["houses"]],
            grahas={k: D5Placement(**v) for k, v in facts["grahas"].items()},
        ),
        foundational=FoundationalBlock(
            chara_karakas=CharaKarakaBlock(**facts["chara_karakas"]),
            d1_fifth_lord_mirroring=D1FifthLordMirroring(
                **facts["d1_fifth_lord_mirroring"]),
            karakamsha=KarakamshaBlock(**facts["karakamsha"]),
        ),
        operational=OperationalBlock(**operational),
        scoring=ScoringBlock(**scoring),
        report=ReportBlock(**report),
    )
