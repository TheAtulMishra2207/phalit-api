"""
d1_contract.py — Phalit.ai D1 interpretation engine: response contract.

KAR-093 step 3. This module defines the COMPLETE response shape of
POST /d1/prepare {chart_token} before any synthesis logic exists. The frontend
becomes a renderer of this payload; the client-side dignity and aspect engines
are deleted after cutover.

DOCTRINAL INVARIANTS (enforced by validators, not convention):

  1. NODE ASPECT POLICY — locked by founder ruling 2026-07-25:
     strict Parāśarī. Rahu and Ketu cast NO independent graha-dṛṣṭi.
       - node_aspect_policy is the literal "no_independent_drishti".
       - No AspectEdge may have Rahu or Ketu as its source; a payload that
         contains one is INVALID and fails model validation.
       - Nodes may RECEIVE aspects, occupy houses and rāśis, have dispositors,
         and form the nodal axis — all of that is modelled.
       - The 5/7/9 extension is NOT implemented. Any future node-aspect system
         must arrive as a new explicit aspect_policy_version value, never as a
         silent change to this one.

  2. ASPECT POLICY — Parāśarī full dṛṣṭi (aspect_policy_version
     "parashari-d1-1.0"): every graha Sun through Saturn casts the 7th;
     Mars additionally 4 and 8; Jupiter 5 and 9; Saturn 3 and 10.
     No other kinds exist in this version.

  3. FUNCTIONAL ROLES (KAR-083/084 typed doctrine): a graha's functional
     nature is a typed enum derived from lordships relative to the Lagna,
     with the deriving rule cited in `basis`. Free-text roles are invalid.

Whole Sign houses, Lahiri ayanāṁśa, Vimśottarī epoch = birth — matching the
closed chart engine 1.1.0.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, root_validator, validator

ENGINE_VERSION = "d1-engine-0.1.0"
ASPECT_POLICY_VERSION = "parashari-d1-1.0"
NODE_ASPECT_POLICY = "no_independent_drishti"

# ── varga parameterisation (D9 port) ────────────────────────────────────────
# The same stack computes any varga. Two things are policy, not code:
#
#   varga_aspect_policy         whether graha-dṛṣṭi is cast inside this varga
#   functional_role_lagna_anchor  which lagna BPHS 34 functional nature reads
#
# FOUNDER RULING: no drishti in D9. BPHS casts dṛṣṭi in the rāśi chart; carrying
# it into a varga is a doctrinal position this build does not take. The key is
# deliberately NOT d9-prefixed, because D9 is the template for D10 and beyond
# and a varga-named field would force a rename at the next one. A third position
# later arrives as a NEW EXPLICIT VALUE, never as a silent change to an
# existing one.
#
# The policy is ENFORCED below, not merely declared. A declared policy the
# contract does not check is the same defect class as the legacy flat
# functional_roles field: a claim with nothing behind it.

class Varga(str, Enum):
    D1 = "D1"
    D9 = "D9"

VARGA_ASPECT_POLICY = {
    Varga.D1: "parashari_full",
    Varga.D9: "none",
}
FUNCTIONAL_ROLE_LAGNA_ANCHOR = "birth_lagna"

# ── vocabulary ───────────────────────────────────────────────────────────────

class Graha(str, Enum):
    SUN = "Sun"; MOON = "Moon"; MARS = "Mars"; MERCURY = "Mercury"
    JUPITER = "Jupiter"; VENUS = "Venus"; SATURN = "Saturn"
    RAHU = "Rahu"; KETU = "Ketu"

ASPECT_CASTERS = [Graha.SUN, Graha.MOON, Graha.MARS, Graha.MERCURY,
                  Graha.JUPITER, Graha.VENUS, Graha.SATURN]
NODES = [Graha.RAHU, Graha.KETU]

# Parāśarī special dṛṣṭi beyond the universal 7th.
SPECIAL_DRISHTI = {Graha.MARS: (4, 8), Graha.JUPITER: (5, 9), Graha.SATURN: (3, 10)}

class AspectKind(str, Enum):
    SEVENTH = "7th"
    FOURTH = "4th"; EIGHTH = "8th"          # Mars only
    FIFTH = "5th"; NINTH = "9th"            # Jupiter only
    THIRD = "3rd"; TENTH = "10th"           # Saturn only

_KIND_OWNER = {
    AspectKind.FOURTH: Graha.MARS, AspectKind.EIGHTH: Graha.MARS,
    AspectKind.FIFTH: Graha.JUPITER, AspectKind.NINTH: Graha.JUPITER,
    AspectKind.THIRD: Graha.SATURN, AspectKind.TENTH: Graha.SATURN,
}

class Dignity(str, Enum):
    EXALTED = "Exalted"; MOOLATRIKONA = "Moolatrikona"; OWN = "Own Sign"
    GREAT_FRIEND = "Great Friend"; FRIEND = "Friend"; NEUTRAL = "Neutral"
    ENEMY = "Enemy"; GREAT_ENEMY = "Great Enemy"; DEBILITATED = "Debilitated"

class FunctionalRoleKind(str, Enum):
    """KAR-083/084: typed functional-nature doctrine. No free text."""
    YOGAKARAKA = "yogakaraka"                 # kendra + trikona lord in one graha
    FUNCTIONAL_BENEFIC = "functional_benefic"
    FUNCTIONAL_MALEFIC = "functional_malefic"
    FUNCTIONAL_NEUTRAL = "functional_neutral"
    MARAKA = "maraka"                         # 2nd/7th lordship involvement
    NODE_AXIS = "node_axis"                   # Rahu/Ketu: role via axis, dispositor, association

# ── payload models ───────────────────────────────────────────────────────────

class EnginePolicy(BaseModel):
    engine_version: Literal["d1-engine-0.1.0"] = ENGINE_VERSION
    ayanamsha: Literal["lahiri"] = "lahiri"
    house_system: Literal["whole_sign"] = "whole_sign"
    aspect_policy_version: Literal["parashari-d1-1.0"] = ASPECT_POLICY_VERSION
    node_aspect_policy: Literal["no_independent_drishti"] = NODE_ASPECT_POLICY
    varga: Varga = Varga.D1
    varga_aspect_policy: Literal["parashari_full", "none"] = "parashari_full"
    # BPHS 34 functional nature is a rāśi-lordship property and does not change
    # across vargas, so it stays anchored to the birth lagna in every varga.
    # The value the payload must carry to be verifiable is
    # birth_lagna_sign_index on D1PrepareResponse.
    functional_role_lagna_anchor: Literal["birth_lagna"] = FUNCTIONAL_ROLE_LAGNA_ANCHOR

    @root_validator(skip_on_failure=True)
    def _policy_matches_varga(cls, values):
        varga, declared = values.get("varga"), values.get("varga_aspect_policy")
        expected = VARGA_ASPECT_POLICY.get(varga)
        if expected is not None and declared != expected:
            raise ValueError(
                f"varga {varga.value} carries varga_aspect_policy={expected!r}, "
                f"not {declared!r}; a new position is a new explicit value")
        return values

class GrahaState(BaseModel):
    graha: Graha
    sign_index: int = Field(ge=0, le=11)      # 0 = Aries
    sign: str
    degree_in_sign: float = Field(ge=0, lt=30)
    house: int = Field(ge=1, le=12)           # Whole Sign from Lagna
    dignity: Optional[Dignity] = None          # None for nodes if not assigned
    # VARGA PORT, constraint 4 (publish the inputs to a derived claim). In D1
    # this equals `dignity`; in a varga `dignity` is the varga dignity and this
    # stays the birth-chart one. varga_dignity_shift is derived from the pair,
    # and a derived verdict whose inputs are not in the payload is a claim
    # nothing can verify. Same principle as birth_lagna_sign_index.
    birth_dignity: Optional[Dignity] = None
    # Certified by the chart engine. Optional because ABSENT and FALSE are
    # different facts: absent means the chart did not say, and the renderer
    # shows an explicit unknown rather than a confident "no".
    vargottama: Optional[bool] = None
    retrograde: bool = False
    combust: bool = False
    nakshatra: Optional[str] = None
    nakshatra_pada: Optional[int] = Field(default=None, ge=1, le=4)
    dispositor: Optional[Graha] = None

    @root_validator(skip_on_failure=True)
    def _nodes_have_dispositor_context(cls, values):
        # Ruling: nodal dispositor condition remains available — require it.
        graha = values.get("graha")
        if graha in NODES and values.get("dispositor") is None:
            raise ValueError(f"{graha.value} must carry its dispositor")
        return values

class AspectEdge(BaseModel):
    """One full Parāśarī dṛṣṭi. Source is ALWAYS one of the seven grahas."""
    source: Graha
    kind: AspectKind
    target_house: int = Field(ge=1, le=12)
    target_grahas: List[Graha] = Field(default_factory=list)  # occupants receiving it

    @validator("source")
    def _no_node_drishti(cls, v: Graha) -> Graha:
        if v in NODES:
            raise ValueError(
                "node_aspect_policy=no_independent_drishti: "
                f"{v.value} cannot be the source of a graha-dṛṣṭi")
        return v

    @root_validator(skip_on_failure=True)
    def _kind_matches_source(cls, values):
        kind, source = values.get("kind"), values.get("source")
        owner = _KIND_OWNER.get(kind)
        if owner is not None and source != owner:
            raise ValueError(f"{kind.value} dṛṣṭi belongs to {owner.value} only, not {source.value}")
        return values

class FunctionalRole(BaseModel):
    graha: Graha
    lordships: List[int] = Field(default_factory=list)   # houses owned; [] for nodes
    role: FunctionalRoleKind
    basis: str = Field(min_length=8)   # the deriving rule, cited (e.g. "BPHS 34: kendra+trikona lord")

    @root_validator(skip_on_failure=True)
    def _node_roles_are_axis(cls, values):
        graha, role = values.get("graha"), values.get("role")
        if graha in NODES and role != FunctionalRoleKind.NODE_AXIS:
            raise ValueError("nodes carry role=node_axis; their nature flows from axis/dispositor/association")
        if graha not in NODES and role == FunctionalRoleKind.NODE_AXIS:
            raise ValueError("node_axis role is reserved for Rahu/Ketu")
        if graha in NODES and values.get("lordships"):
            raise ValueError("nodes own no houses in the Parāśarī scheme")
        return values

class HouseState(BaseModel):
    house: int = Field(ge=1, le=12)
    sign_index: int = Field(ge=0, le=11)
    sign: str
    lord: Graha
    occupants: List[Graha] = Field(default_factory=list)
    aspected_by: List[Graha] = Field(default_factory=list)

    @validator("lord")
    def _lord_is_classical(cls, v: Graha) -> Graha:
        if v in NODES:
            raise ValueError("Rahu/Ketu own no rāśi in the Parāśarī scheme")
        return v

    @validator("aspected_by")
    def _aspecting_grahas_are_casters(cls, v: List[Graha]) -> List[Graha]:
        for g in v:
            if g in NODES:
                raise ValueError("houses cannot be aspected by nodes under no_independent_drishti")
        return v

class NodalAxis(BaseModel):
    rahu_house: int = Field(ge=1, le=12)
    ketu_house: int = Field(ge=1, le=12)
    rahu_sign: str
    ketu_sign: str
    rahu_dispositor: Graha
    ketu_dispositor: Graha

    @root_validator(skip_on_failure=True)
    def _axis_is_opposite(cls, values):
        rahu, ketu = values.get("rahu_house"), values.get("ketu_house")
        if (rahu - 1 + 6) % 12 + 1 != ketu:
            raise ValueError("Rahu and Ketu must occupy opposite houses (nodal axis)")
        return values

class D1PrepareResponse(BaseModel):
    chart_token: str = Field(min_length=8)
    policy: EnginePolicy = Field(default_factory=EnginePolicy)
    lagna_sign_index: int = Field(ge=0, le=11)
    lagna_sign: str
    lagna_degree: float = Field(ge=0, lt=30)
    # The lagna functional roles were ACTUALLY anchored to. In D1 it equals
    # lagna_sign_index; in a varga it is the birth lagna while lagna_sign_index
    # is the varga lagna. Without it, functional_role_lagna_anchor is a claim
    # nothing in the payload can check.
    birth_lagna_sign_index: int = Field(ge=0, le=11)
    grahas: List[GrahaState] = Field(min_items=9, max_items=9)
    houses: List[HouseState] = Field(min_items=12, max_items=12)
    aspects: List[AspectEdge]
    functional_roles: List[FunctionalRole] = Field(min_items=9, max_items=9)
    nodal_axis: NodalAxis
    generated_at: datetime

    @root_validator(skip_on_failure=True)
    def _complete_and_consistent(cls, values):
        grahas = values.get("grahas") or []
        houses = values.get("houses") or []
        roles = values.get("functional_roles") or []
        aspects = values.get("aspects") or []

        names = {g.graha for g in grahas}
        if names != set(Graha):
            raise ValueError("grahas must contain exactly the nine grahas")
        role_names = {r.graha for r in roles}
        if role_names != set(Graha):
            raise ValueError("functional_roles must cover exactly the nine grahas")
        if {h.house for h in houses} != set(range(1, 13)):
            raise ValueError("houses must be exactly 1..12")

        # POLICY GATE (varga port). Under varga_aspect_policy="none" doctrine
        # says there is nothing to cast, so the manifest must be EMPTY and no
        # house may record an aspecting graha. Permitting zero edges would let a
        # D9 payload carry aspects and still validate, which is the declared-
        # but-unenforced hole this port exists to avoid.
        policy = values.get("policy")
        varga_policy = getattr(policy, "varga_aspect_policy", "parashari_full")
        if varga_policy == "none":
            if aspects:
                raise ValueError(
                    "varga_aspect_policy=none forbids graha-dṛṣṭi; the manifest "
                    f"carries {len(aspects)} edge(s)")
            offenders = [h.house for h in houses if h.aspected_by]
            if offenders:
                raise ValueError(
                    "varga_aspect_policy=none forbids graha-dṛṣṭi; houses "
                    f"{offenders} record aspected_by")
            return values

        # Aspect GEOMETRY: the manifest must be the exact Parāśarī dṛṣṭi set —
        # for every permitted (source, kind) pair EXACTLY ONE edge, landing on
        # the mathematically correct house counted from the source graha's own
        # house. Wrong targets and duplicate edges are contract violations.
        source_house = {g.graha: g.house for g in grahas}
        kind_offset = {AspectKind.SEVENTH: 7, AspectKind.FOURTH: 4, AspectKind.EIGHTH: 8,
                       AspectKind.FIFTH: 5, AspectKind.NINTH: 9, AspectKind.THIRD: 3,
                       AspectKind.TENTH: 10}
        offset_kind = {v: k for k, v in kind_offset.items()}
        seen_pairs = set()
        for a in aspects:
            pair = (a.source, a.kind)
            if pair in seen_pairs:
                raise ValueError(f"duplicate dṛṣṭi edge: {a.source.value} {a.kind.value}")
            seen_pairs.add(pair)
            expected = (source_house[a.source] - 1 + kind_offset[a.kind] - 1) % 12 + 1
            if a.target_house != expected:
                raise ValueError(
                    f"{a.source.value} {a.kind.value} dṛṣṭi from house {source_house[a.source]} "
                    f"must land on house {expected}, not {a.target_house}")
        permitted_pairs = set()
        for caster in ASPECT_CASTERS:
            permitted_pairs.add((caster, AspectKind.SEVENTH))
            for off in SPECIAL_DRISHTI.get(caster, ()):
                permitted_pairs.add((caster, offset_kind[off]))
        if seen_pairs != permitted_pairs:
            missing = permitted_pairs - seen_pairs
            extra = seen_pairs - permitted_pairs
            detail = []
            if missing: detail.append("missing: " + ", ".join(f"{s.value} {k.value}" for s, k in sorted(missing, key=lambda p: (p[0].value, p[1].value))))
            if extra: detail.append("extra: " + ", ".join(f"{s.value} {k.value}" for s, k in sorted(extra, key=lambda p: (p[0].value, p[1].value))))
            raise ValueError("aspect manifest must contain exactly one edge per permitted (source, kind); " + "; ".join(detail))
        return values
