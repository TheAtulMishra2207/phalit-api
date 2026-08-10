"""
D4-002-R1 · STRICT REQUEST/RESPONSE CONTRACT for POST /d4/prepare.

Pinned to pydantic 1.10.13 (fastapi 0.100.1, Python 3.11.12) — the accepted
Phalit pin. This file uses v1 idioms only: `class Config: extra = Extra.forbid`,
`validator`, `Field(..., regex=...)`. It must not be ported to v2 idioms while
the pin stands.

WHAT THIS FILE IS
  The typed boundary around the already-certified `d4_core.build_d4_facts()`.
  It adds no astrology, no doctrine and no interpretation. It only declares the
  shape that crosses the wire and refuses anything else.

WHAT IT DELIBERATELY DOES NOT DO
  * No birth data is accepted. The request carries a chart_token and nothing
    else, and unknown fields are REJECTED rather than ignored.
  * No field here is optional-by-accident. A missing core field is a contract
    failure, not a null in the payload.
  * `route_version` and `calculation_meta` are supplied BY THE ROUTE, not by
    the core, so the core stays free of deployment provenance.

ONE NORMALISATION, DECLARED RATHER THAN SILENT
  `d4_core` returns `house_lords` keyed by INT and `key_house_lords` keyed by
  STR. JSON object keys are strings on the wire either way, so the contract
  declares both as Dict[str, str] and normalises at the boundary. The
  normalisation is asserted lossless: identical key SET after stringification
  and identical values. `d4_core.py` is an accepted artefact and is NOT edited
  to achieve this.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Extra, Field, StrictStr, root_validator, validator

D4_ROUTE_VERSION = "d4-prepare-1.0.0"

# CORR-01 · SHARED TOKEN CONTRACT PARITY. The D4-specific regex and the 16..512
# bounds are REMOVED. The accepted prepare-route boundary is
#   chart_token: StrictStr = Field(min_length=8, max_length=256)
# and D4 now matches it exactly. A chart token is OPAQUE: D4 invents no
# semantics for its characters, so there is no charset pattern and no
# whitespace rule. StrictStr is load-bearing — it refuses an int, float or bool
# rather than coercing one into a token.
CHART_TOKEN_MIN_LENGTH = 8
CHART_TOKEN_MAX_LENGTH = 256


class _Strict(BaseModel):
    class Config:
        extra = Extra.forbid
        allow_mutation = False


# ── request ──────────────────────────────────────────────────────────────────

class D4PrepareRequest(_Strict):
    """The ENTIRE accepted request surface. No birth date, time, latitude,
    longitude or offset is accepted here by design: /d4/prepare resolves the
    already-certified snapshot and never recalculates astronomy."""
    chart_token: StrictStr = Field(..., min_length=CHART_TOKEN_MIN_LENGTH,
                                   max_length=CHART_TOKEN_MAX_LENGTH)


# ── response components ──────────────────────────────────────────────────────

class D4Engine(_Strict):
    d4_core_version: str
    method: str
    house_system: str
    aspect_doctrine: str
    varga_moolatrikona_policy: str
    node_dignity_policy: str
    vargottama_strength_modifier_applied: bool


class D4Lagna(_Strict):
    sign_index: int = Field(..., ge=0, le=11)
    sign: str
    lord: str


class D4House(_Strict):
    house: int = Field(..., ge=1, le=12)
    sign_index: int = Field(..., ge=0, le=11)
    sign: str
    lord: str
    occupants: List[str]


class D4DignityComponents(_Strict):
    sign_lord: str
    is_exalted: bool
    is_debilitated: bool
    is_own_sign: bool
    sign_lord_is_natural_friend: bool
    sign_lord_is_natural_enemy: bool


class D4Dignity(_Strict):
    """`dignity` is Optional ONLY because Rahu and Ketu publish none under
    `node_dignity_policy`. It is not optional for a classical graha, which the
    route tests assert separately. `bphs47_node_sign_state` is exposed and
    unconsumed, exactly as certified in D4-002."""
    graha: str
    d4_sign_index: int = Field(..., ge=0, le=11)
    d4_sign: str
    dignity: Optional[str]
    policy: str
    components: Optional[D4DignityComponents] = None
    bphs47_node_sign_state: Optional[str] = None


class D4Graha(_Strict):
    graha: str
    d1_sign_index: int = Field(..., ge=0, le=11)
    d1_sign: str
    d4_quarter: int = Field(..., ge=1, le=4)
    d4_sign_index: int = Field(..., ge=0, le=11)
    d4_sign: str
    d4_house: int = Field(..., ge=1, le=12)
    vargottama: bool
    dignity: D4Dignity
    aspects_cast: List[int]
    casts_drishti: bool


class D4AspectEdge(_Strict):
    source: str
    from_house: int = Field(..., ge=1, le=12)
    to_house: int = Field(..., ge=1, le=12)
    offset: int = Field(..., ge=1, le=12)
    kind: str


class D4Aspects(_Strict):
    edges: List[D4AspectEdge]
    received_by_house: Dict[str, List[str]]
    received_by_graha: Dict[str, List[str]]


class D4KarakaFacts(_Strict):
    graha: str
    d4_sign: str
    d4_sign_index: int = Field(..., ge=0, le=11)
    d4_house: int = Field(..., ge=1, le=12)
    dignity: D4Dignity
    vargottama: bool
    aspects_cast: List[int]
    aspects_received: List[str]


class D4FourthLordFacts(_Strict):
    graha: str
    d4_sign_index: int = Field(..., ge=0, le=11)
    d4_sign: str
    d4_house: int = Field(..., ge=1, le=12)
    dignity: D4Dignity
    vargottama: bool
    aspects_received: List[str]


class D4FourthHouse(_Strict):
    house: int = Field(..., ge=1, le=12)
    sign_index: int = Field(..., ge=0, le=11)
    sign: str
    lord: str
    occupants: List[str]
    aspects_received: List[str]
    lord_facts: D4FourthLordFacts
    mars_bhumi_karaka: D4KarakaFacts
    venus_vahana_karaka: D4KarakaFacts


class D4PropertyState(_Strict):
    """D4-003 · the deterministic Primary Property State block.

    Evidence sub-blocks are typed as Dict[str, Any] deliberately: they are
    AUDIT TRAILS whose shape belongs to d4_property_state.py, and re-declaring
    every nested field here would create a second description of one contract
    that could drift from it. The load-bearing fields — the selection, the
    resolution, the matched set and the truth table — ARE strictly typed, and
    the validators below enforce the resolution invariants.
    """
    engine: Dict[str, Any]
    selected_state: str
    state_id: str
    category: str
    resolution: str
    matched_states: List[str]
    predicates: Dict[str, Any]
    lock1_benefic_cancellation: Dict[str, Any]
    lock2_eighth_twelfth_involvement: Dict[str, Any]
    lock3_mercury_rahu_influence: Dict[str, Any]
    lock4_dignity_and_affliction: Dict[str, Any]
    supporting_evidence: Dict[str, Any]
    # D4-004 · explicit evidence hierarchy. Selection only — see
    # d4_property_state.evidence_hierarchy.
    authority: str
    d4_primary: Dict[str, Any]
    d1_root_context: Dict[str, Any]

    @validator("authority")
    def _d4_is_authoritative(cls, v):
        if v != "d4_primary":
            raise ValueError("authority must be d4_primary")
        return v

    @validator("d1_root_context")
    def _d1_never_overrides(cls, v):
        # The declaration is enforced, not merely printed: a payload claiming
        # D1 selects the state, or carrying a weighted D1+D4 score, is refused.
        if v.get("selects_or_overrides_d4_state") is not False:
            raise ValueError("D1 root context may never select or override the D4 state")
        if v.get("weighted_d1_d4_score_present") is not False:
            raise ValueError("no weighted D1+D4 score may be published")
        return v

    @validator("selected_state")
    def _known_state(cls, v):
        if v not in ("P1", "P2", "P3", "P4", "P5"):
            raise ValueError("selected_state must be one of P1..P5")
        return v

    @validator("resolution")
    def _known_resolution(cls, v):
        if v not in ("predicate_match", "coverage_fallback"):
            raise ValueError("resolution must be predicate_match or coverage_fallback")
        return v

    @validator("matched_states")
    def _matched_consistent(cls, v, values):
        sel = values.get("selected_state")
        res = values.get("resolution")
        if any(m not in ("P1", "P2", "P3", "P4") for m in v):
            raise ValueError("matched_states may contain only P1..P4")
        if len(set(v)) != len(v):
            raise ValueError("matched_states must not repeat a state")
        if res == "coverage_fallback":
            # P5 is never a matched yoga.
            if sel != "P5" or v:
                raise ValueError("coverage_fallback requires P5 and an empty matched_states")
        if res == "predicate_match":
            if sel == "P5" or not v:
                raise ValueError("predicate_match requires a specific state and a non-empty match set")
            order = ["P1", "P2", "P3", "P4"]
            if sel != min(v, key=order.index):
                raise ValueError("selected_state must be the first matched state by precedence")
        return v


class D4VahanaEvidence(_Strict):
    """D4-005 · Vāhana evidence. Mechanical only.

    The validators are the point: a payload that claims D1 authority, or that
    smuggles a tier, count, score or acquisition date into this block, cannot
    be serialised at all. The taxonomy is not Founder-locked, so the ABSENCE is
    enforced rather than merely intended.
    """
    engine: Dict[str, Any]
    authority: str
    venus: Dict[str, Any]
    contact_paths: Dict[str, bool]
    direct_venus_vahana_contact: bool
    vahana_sthana: Dict[str, Any]
    note: str

    @validator("authority")
    def _d4_is_authoritative(cls, v):
        if v != "d4_primary":
            raise ValueError("vahana evidence authority must be d4_primary")
        return v

    @validator("contact_paths")
    def _exactly_four_paths(cls, v):
        expected = {"venus_occupies_h4", "venus_conjoins_4l",
                    "venus_aspects_h4", "venus_aspects_4l"}
        if set(v) != expected:
            raise ValueError("contact_paths must carry exactly the four direct paths")
        return v

    @validator("direct_venus_vahana_contact")
    def _any_of_the_four(cls, v, values):
        paths = values.get("contact_paths")
        if paths is not None and v != any(paths.values()):
            raise ValueError("direct_venus_vahana_contact must be ANY-OF the four paths")
        return v

    @validator("engine")
    def _no_taxonomy_smuggled(cls, v):
        if v.get("tier_classification_policy") != "not_defined_pending_founder_lock":
            raise ValueError("the tier taxonomy is not locked and must be declared undefined")
        for flag in ("vehicle_tier_published", "vehicle_count_published",
                     "acquisition_timing_published", "weighted_score_published",
                     "provider_classification_authority", "d16_evidence_consumed"):
            if v.get(flag) is not False:
                raise ValueError("forbidden vahana output declared: " + flag)
        return v


class D4DashaContext(_Strict):
    """D4-007 · Dasha concurrence. CONTEXT ONLY.

    The validators enforce what the prose promises: authority is context_only,
    the policy names concurrence rather than activation, statuses are the three
    permitted values, and a coverage fallback may never carry a participant.
    A payload that smuggles activation language or a synthetic P5 participant
    cannot be serialised at all.
    """
    engine: Dict[str, Any]
    authority: str
    timing_policy: str
    selected_state: str
    timing_applicability: str
    selected_state_participants: List[Dict[str, Any]]
    selected_state_participant_grahas: List[str]
    participants_by_state: Dict[str, Any]
    current_mahadasha: Optional[str]
    current_antardasha: Optional[str]
    md_status: str
    ad_status: str
    concurrence_summary: str
    note: str

    @validator("authority")
    def _context_only(cls, v):
        if v != "context_only":
            raise ValueError("dasha authority must be context_only")
        return v

    @validator("timing_policy")
    def _not_activation(cls, v):
        if v != "structural_concurrence_not_activation":
            raise ValueError("timing policy must state concurrence, not activation")
        return v

    @validator("md_status", "ad_status")
    def _three_state(cls, v):
        if v not in ("match", "no_match", "unknown"):
            raise ValueError("timing status must be match, no_match or unknown")
        return v

    @validator("concurrence_summary")
    def _neutral_summary(cls, v):
        allowed = {"md_and_ad_concurrence", "md_concurrence", "ad_concurrence",
                   "no_current_concurrence", "unknown",
                   "not_applicable_coverage_fallback"}
        if v not in allowed:
            raise ValueError("concurrence summary must be one of the neutral labels")
        return v

    @validator("selected_state_participant_grahas")
    def _unique_identities(cls, v):
        if len(set(v)) != len(v):
            raise ValueError("participant identities must be unique")
        return v

    # D4-007-CORR-01 · THIS WAS A FIELD VALIDATOR AND IT COULD NOT WORK.
    #
    # In pydantic v1, field validators run in DECLARATION order, and
    # `timing_applicability` is declared ABOVE the three participant fields. A
    # validator attached to it therefore saw `values` without
    # selected_state_participants, selected_state_participant_grahas or
    # participants_by_state, so `values.get(...)` was always None and the
    # participant clause could never fire. A P5 payload carrying a synthetic
    # participant serialised cleanly while the contract claimed to forbid it —
    # the assertion read as protection and provided none.
    #
    # A root_validator runs AFTER every field is populated, which is the only
    # point at which a cross-field invariant like this one can be enforced.
    @root_validator(skip_on_failure=True)
    def _coverage_fallback_carries_nothing(cls, values):
        if values.get("selected_state") != "P5":
            return values
        if values.get("timing_applicability") != "not_applicable_coverage_fallback":
            raise ValueError("a coverage fallback must declare timing not applicable")
        if values.get("selected_state_participants") != []:
            raise ValueError("a coverage fallback may never carry a participant")
        if values.get("selected_state_participant_grahas") != []:
            raise ValueError("a coverage fallback may never carry a participant graha")
        if values.get("participants_by_state") != {}:
            raise ValueError("a coverage fallback has no matched state, so participants_by_state must be empty")
        if values.get("concurrence_summary") != "not_applicable_coverage_fallback":
            raise ValueError("a coverage fallback must publish the not-applicable summary")
        return values


class D4SemanticEnvelope(_Strict):
    """The layered, P-code-free view. The validators enforce the two rules that
    matter: no P-code may leak into a user-facing label, and the selected state
    must not erase the other matched layers."""
    engine: Dict[str, Any]
    primary_layer: Dict[str, Any]
    secondary_layers: List[Dict[str, Any]]
    active_layer_count: int
    expansion_capacity_matched: bool
    multi_asset_language_permitted: bool
    coverage_baseline: bool

    @validator("primary_layer", "secondary_layers")
    def _no_p_codes_in_labels(cls, v):
        import re as _re
        blob = str(v)
        if _re.search(r"\bP[1-5]\b", blob):
            raise ValueError("a P-code may not appear in a user-facing layer label")
        return v

    @validator("active_layer_count")
    def _count_matches(cls, v, values):
        sec = values.get("secondary_layers")
        if sec is not None and v != 1 + len(sec):
            raise ValueError("active layer count must be the primary plus every secondary")
        return v


class D4ComfortProfile(_Strict):
    """The four Founder-locked comfort tiers. The validators enforce the two
    things easiest to break by accident: every chart resolves to exactly ONE
    tier, and C4 is published as a coverage fallback rather than dressed up as a
    matched predicate."""
    engine: Dict[str, Any]
    profile: str
    resolution: str
    matched_predicate: Optional[str]
    rationale: str
    headline: str
    description: str
    approved_vocabulary: List[str]
    maintenance_attention: bool
    evidence: Dict[str, Any]
    inputs: Dict[str, Any]
    note: str

    @validator("engine")
    def _architecture_locked(cls, v):
        if v.get("venus_only_classifier") is not False:
            raise ValueError("a Venus-only comfort classifier is prohibited")
        if v.get("weighted_score_used") is not False:
            raise ValueError("no weighted comfort score may be used")
        if v.get("provider_may_infer_tier") is not False:
            raise ValueError("the provider may never infer a comfort tier")
        if v.get("middle_class_promotable_by_contacts") is not False:
            raise ValueError("Mitra/Sama may never be promoted to Strong by contacts")
        return v

    @validator("profile")
    def _only_the_four_tiers(cls, v):
        if v not in ("High Comfort Tier", "Maintenance-Heavy Comfort Tier",
                     "Constrained Comfort Tier", "Functional Comfort Tier"):
            raise ValueError("only the four Founder-locked comfort tiers exist")
        return v

    @validator("resolution")
    def _fallback_is_declared(cls, v, values):
        if v not in ("predicate_match", "coverage_fallback"):
            raise ValueError("unknown comfort resolution")
        prof = values.get("profile")
        if prof is None:
            return v
        # C4 is the ONLY fallback, and it must never be published as a match.
        if (prof == "Functional Comfort Tier") != (v == "coverage_fallback"):
            raise ValueError("the Functional Comfort Tier is the coverage fallback, "
                             "and no other tier may claim it")
        return v

    @validator("matched_predicate")
    def _predicate_matches_resolution(cls, v, values):
        res = values.get("resolution")
        if res == "coverage_fallback" and v is not None:
            raise ValueError("a coverage fallback has no matched predicate")
        if res == "predicate_match" and v not in ("C1", "C2", "C3"):
            raise ValueError("a matched tier must name C1, C2 or C3")
        return v


class D4ArchitecturalSignatures(_Strict):
    engine: Dict[str, Any]
    signatures: List[Dict[str, Any]]
    any_signature_active: bool
    caveat: str
    fourth_house_sign: Optional[str]

    @validator("signatures")
    def _only_the_three_mapped_grahas(cls, v):
        allowed = {"Mars", "Moon", "Sun"}
        bad = [s.get("graha") for s in v if s.get("graha") not in allowed]
        if bad:
            raise ValueError("only the Founder-supplied Mars, Moon and Sun signatures exist")
        if len({s.get("graha") for s in v}) != len(v):
            raise ValueError("a graha may carry only one signature")
        return v


class D4PrepareResponse(_Strict):
    route_version: str
    chart_token: str
    calculation_meta: Dict[str, Any]
    engine: D4Engine
    d4_lagna: D4Lagna
    houses: List[D4House]
    house_lords: Dict[str, str]
    key_house_lords: Dict[str, str]
    grahas: Dict[str, D4Graha]
    vargottama_grahas: List[str]
    aspects: D4Aspects
    fourth_house: D4FourthHouse
    property_state: D4PropertyState
    vahana_evidence: D4VahanaEvidence
    dasha_context: D4DashaContext
    semantic_envelope: D4SemanticEnvelope
    comfort_profile: D4ComfortProfile
    architectural_signatures: D4ArchitecturalSignatures

    @validator("houses")
    def _twelve_houses(cls, v):
        if len(v) != 12 or [h.house for h in v] != list(range(1, 13)):
            raise ValueError("houses must be exactly 1..12 in order")
        return v

    @validator("grahas")
    def _nine_grahas(cls, v):
        if len(v) != 9:
            raise ValueError("grahas must carry exactly nine entries")
        return v


class D4NarrativeSection(_Strict):
    title: str
    body: str


class D4ReportRequest(_Strict):
    """D4-008 · the ENTIRE accepted report request surface.

    The legacy /d4report trusted a browser-supplied `chart_brief` carrying
    locally computed D4 facts and a literal property count. That architecture is
    retired: this model forbids every field except the token, so a client cannot
    submit the interpretation the prose is meant to explain. Parity with
    /d4/prepare is deliberate — one token contract, not two.
    """
    chart_token: StrictStr = Field(..., min_length=CHART_TOKEN_MIN_LENGTH,
                                   max_length=CHART_TOKEN_MAX_LENGTH)


class D4ReportResponse(_Strict):
    chart_token: str
    narrative_version: str
    sections: List[D4NarrativeSection]

    @validator("sections")
    def _exactly_the_four_sections(cls, v):
        # D4-008-CORR-01 · the permissive "Interpretive Explanation" fallback is
        # REMOVED. A response now carries exactly the four fixed sections, once
        # each, in order — a formatting failure is a narrative failure, not
        # permission to publish something looser.
        required = ["Property Capacity & Stability", "Home & Asset Pattern",
                    "Vehicles & Material Comforts", "Current Timing Context"]
        if [s.title for s in v] != required:
            raise ValueError("a report must carry exactly the four fixed sections, "
                             "once each, in order")
        if any(not s.body.strip() for s in v):
            raise ValueError("a narrative section may not be empty")
        return v


def _stringify_keys(d: Dict[Any, Any]) -> Dict[str, Any]:
    """Declared normalisation. JSON object keys are strings regardless, so this
    only makes the Python-side type agree with the wire type. Lossless: the key
    set and every value are preserved, which the contract tests assert."""
    out = {str(k): v for k, v in d.items()}
    if len(out) != len(d):
        raise ValueError("key collision while stringifying")
    return out


def build_response(*, facts: Dict[str, Any], chart_token: str,
                   calculation_meta: Dict[str, Any],
                   property_state: Dict[str, Any],
                   vahana_evidence: Dict[str, Any],
                   dasha_context: Dict[str, Any],
                   semantic_envelope: Dict[str, Any],
                   comfort_profile: Dict[str, Any],
                   architectural_signatures: Dict[str, Any]) -> D4PrepareResponse:
    """Wrap a certified `build_d4_facts()` payload in the strict contract.

    `chart_token` is the RESOLVED token, echoed back so a caller can confirm
    which chart answered. `calculation_meta` is the deployment provenance the
    route supplies. Neither is invented here.
    """
    return D4PrepareResponse(
        route_version=D4_ROUTE_VERSION,
        chart_token=chart_token,
        calculation_meta=calculation_meta,
        engine=facts["engine"],
        d4_lagna=facts["d4_lagna"],
        houses=facts["houses"],
        house_lords=_stringify_keys(facts["house_lords"]),
        key_house_lords=_stringify_keys(facts["key_house_lords"]),
        grahas=facts["grahas"],
        vargottama_grahas=facts["vargottama_grahas"],
        aspects={
            "edges": facts["aspects"]["edges"],
            "received_by_house": _stringify_keys(facts["aspects"]["received_by_house"]),
            "received_by_graha": facts["aspects"]["received_by_graha"],
        },
        fourth_house=facts["fourth_house"],
        property_state=property_state,
        vahana_evidence=vahana_evidence,
        dasha_context=dasha_context,
        semantic_envelope=semantic_envelope,
        comfort_profile=comfort_profile,
        architectural_signatures=architectural_signatures,
    )
