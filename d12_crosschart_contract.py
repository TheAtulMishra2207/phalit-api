"""d12_crosschart_contract.py — typed FR-001 classification and §10 handshake.

D12-005. Four-valued internally: Supported / Loaded / Redirected / UNKNOWN.
UNKNOWN is an ENGINEERING state and must never masquerade as Redirected — a
consumer must always be able to tell "Redirected" from "could not safely
classify". No prose verdict field exists anywhere in this module.
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Extra, StrictBool, StrictInt, StrictStr, conint, validator

CROSSCHART_CONTRACT_VERSION = "d12-crosschart-1.0"

HouseNumber = conint(strict=True, ge=1, le=12)
SignIndex = conint(strict=True, ge=0, le=11)

# The §10 grid is exactly these three. Not four, not the Lagnesh, not a score.
HANDSHAKE_SOURCE_HOUSES = (4, 9, 12)


class Classification(str, Enum):
    SUPPORTED = "Supported"
    LOADED = "Loaded"
    REDIRECTED = "Redirected"
    UNKNOWN = "UNKNOWN"


class Tri(str, Enum):
    """Three-valued predicate. Missing upstream authority is UNKNOWN, never
    FALSE — FR-001's strict-dusthāna rule turns on exactly this distinction."""
    TRUE = "TRUE"
    FALSE = "FALSE"
    UNKNOWN = "UNKNOWN"


class _Closed(BaseModel):
    class Config:
        extra = Extra.forbid
        allow_mutation = False


class UpstreamEvidence(_Closed):
    """What the D1 authority published about this target. Consumed, never
    recomputed: D12 owns no natural-nature, functional-nature, pakṣa, aspect or
    mitigation rule of its own."""
    authority_resolved: StrictBool
    tight_functional_malefic_affliction: Tri
    approved_benefic_mitigation: Tri
    tight_node_conjunction: Tri
    functional_malefic_sources: List[StrictStr] = []
    mitigator_sources: List[StrictStr] = []


class LoadedBasis(_Closed):
    lord_neecha: StrictBool
    structural_malefic_occupants: List[StrictStr] = []
    heavily_occupied: StrictBool
    tight_node_conjunction: Tri


class SupportedBasis(_Closed):
    in_kendra: StrictBool
    in_trikona: StrictBool
    dignity_mitra_or_sva: StrictBool
    supportive_topology: StrictBool
    interference: Tri


class StructuralClassification(_Closed):
    """One classified target. Bounded evidence only — no verdict prose, and
    none of Strong / Weak / Weakened / score / remediation vocabulary."""
    target: StrictStr
    d1_source_house: HouseNumber
    d12_house: HouseNumber
    d12_sign: StrictStr
    dignity: StrictStr
    classification: Classification
    loaded_basis: LoadedBasis
    supported_basis: SupportedBasis
    interference_status: Tri
    upstream_evidence: UpstreamEvidence

    @validator("interference_status")
    def _unknown_is_not_a_topology(cls, v, values):
        """UNKNOWN may only arise from an unresolved interference predicate —
        never as a quiet stand-in for a topological answer.

        Declared on interference_status rather than classification because
        pydantic v1 validators see only the fields declared BEFORE them, and
        classification is declared first.
        """
        classification = values.get("classification")
        if classification is Classification.UNKNOWN and v is not Tri.UNKNOWN:
            raise ValueError(
                "UNKNOWN classification requires an UNKNOWN interference "
                "status; it must not stand in for a topological result")
        return v

    @validator("d1_source_house")
    def _source_is_in_the_grid(cls, v):
        if v not in HANDSHAKE_SOURCE_HOUSES:
            raise ValueError(f"§10 grid is exactly {HANDSHAKE_SOURCE_HOUSES}, got H{v}")
        return v


class CrossChart(_Closed):
    """§10 · the D1×D12 handshake. Exactly three rows, in grid order."""
    contract_version: StrictStr = CROSSCHART_CONTRACT_VERSION
    chart_token: StrictStr
    rows: List[StructuralClassification]

    @validator("rows")
    def _exactly_the_three_grid_houses_in_order(cls, v):
        if tuple(r.d1_source_house for r in v) != HANDSHAKE_SOURCE_HOUSES:
            raise ValueError(
                f"rows must be exactly H{HANDSHAKE_SOURCE_HOUSES} in order, "
                f"got {[r.d1_source_house for r in v]}")
        return v


# ─────────────────────────────────────────────────────────────────────────────
# FR-004 · RELEASE TOPOLOGY
# ─────────────────────────────────────────────────────────────────────────────

class LuminaryFact(_Closed):
    graha: StrictStr
    d12_house: HouseNumber
    dignity: StrictStr
    weight: StrictInt
    strong: StrictBool
    dusthana_afflicted: StrictBool

    @validator("weight")
    def _weight_is_in_the_locked_scale(cls, v):
        if v not in (0, 1, 2):
            raise ValueError(f"luminary weight must be 0, 1 or 2; got {v}")
        return v


class KetuFact(_Closed):
    d12_house: HouseNumber
    d12_sign: StrictStr
    dignity: StrictStr
    base_weight: StrictInt
    # Nodes are ungraded in D12 (FR-004). Recorded so no reader mistakes the
    # weight for a dignity grade.
    ungraded: StrictBool = True

    @validator("base_weight")
    def _base_is_three_or_zero(cls, v):
        if v not in (0, 3):
            raise ValueError(f"Ketu base weight is 3 or 0; got {v}")
        return v

    @validator("dignity")
    def _ketu_is_ungraded(cls, v):
        if v != "Ungraded":
            raise ValueError(f"Ketu must be Ungraded in D12; got {v!r}")
        return v

    @validator("ungraded")
    def _ungraded_is_an_invariant(cls, v):
        if v is not True:
            raise ValueError("Ketu is always Ungraded in D12 (FR-004)")
        return v


class LagnaAxisEvidence(_Closed):
    """FR-004's exception evidence. Only the locked definitions."""
    within_five_degrees_of_ascendant: Tri
    occupies_h1_or_h7: StrictBool
    # CORR-02 · Tri, not a boolean. No certified D12 aspect/opposition authority
    # exists, so the honest value is UNKNOWN; representing it as False would
    # assert an absence nothing has established. It is never caller-supplied.
    full_drishti_or_opposition: Tri
    proximity_basis: StrictStr
    aspect_basis: StrictStr


class ReleaseTopology(_Closed):
    ketu: KetuFact
    sun: LuminaryFact
    moon: LuminaryFact
    luminary_mean: float
    ordinary_comparison: StrictBool
    single_dusthana_override: StrictBool
    dual_strong_luminaries: StrictBool
    lagna_axis: LagnaAxisEvidence
    # CORR-02 · three-valued. UNKNOWN means a locked exception leg could not be
    # evaluated, and it must never be read with Python truthiness: `if
    # topology.dominance` would treat the enum member as True and silently turn
    # "unevaluated" into "yes".
    dominance: Tri
    basis: StrictStr

    @validator("basis")
    def _unknown_dominance_must_say_why(cls, v, values):
        if values.get("dominance") is Tri.UNKNOWN and "UNKNOWN" not in v:
            raise ValueError(
                "an UNKNOWN dominance must identify in its basis exactly which "
                "prerequisite is unevaluated")
        return v
