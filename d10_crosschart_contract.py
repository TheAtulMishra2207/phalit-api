"""
d10_crosschart_contract.py — D10-004 · the shape of the two-chart handshake.

FACTS ONLY. The format's Section 6 eventually prints one agreement word for
D1xD10 and one sentence for D9xD10. Neither is here, because no deterministic
rule for `aligned / strained / redirected` has been ratified. There is no field
that could hold one, so the later synthesis layer cannot inherit a guess from
this flight.

WHAT THE CONTRACT CANNOT STORE, BY CONSTRUCTION: an agreement word, a career
meaning, a profession, a job title, a salary, a timing claim, a remedy, or any
free text. Tests assert every one of those is absent from every model.

PROVENANCE, NOT SPEAKER. The two blocks are labelled `D1_D10` and `D9_D10`.
Neither is PARASHARA and neither is JAIMINI: a cross-chart composition is a
product layer over two certified outputs, not a new classical rule family, and
labelling it with a classical speaker would let it impersonate one.

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


CROSSCHART_VERSION = "d10.crosschart.v1"

PROVENANCE_D1_D10 = "D1_D10"
PROVENANCE_D9_D10 = "D9_D10"

#: The four accepted D9-R2 contribution modes. Anything else is malformed.
CONTRIBUTION_MODES = ("MATURITY_FALLBACK", "UNIFIED_PURPOSE", "PAIRWISE",
                      "COMPOUND_MULTI_POLAR")

#: Machine reason for a D9 report that legitimately publishes no contribution.
#: Not an error and not FALSE.
D9_CONTRIBUTION_UNAVAILABLE = "D9_CONTRIBUTION_UNAVAILABLE"


# ─────────────────────────────────────────────────────────────────────────────
# D1 × D10
# ─────────────────────────────────────────────────────────────────────────────

class LordPlacement(Strict):
    planet: str
    house: int = Field(ge=1, le=12)
    sign: str
    dignity: str


class D1TenthHouse(Strict):
    """Read from the accepted D1PrepareResponse. Sign, lord and occupants, as
    the specification asks for — and nothing else, so no other natal house or
    natal claim can travel with it."""
    sign: str
    sign_index: int = Field(ge=0, le=11)
    lord: str
    occupants: List[str]


class D10TenthHouse(Strict):
    """Read from the D10-003 findings authority, never rederived."""
    sign: str
    sign_index: int = Field(ge=0, le=11)
    lord: str
    occupants: List[str]
    mode: Literal["OCCUPIED", "THROUGH_LORD"]
    lord_placement: LordPlacement


class D1D10Handshake(Strict):
    """The spine of the Ledger, as facts.

    THERE IS NO `agreement` FIELD. `aligned`, `strained` and `redirected` are
    the eventual output of a rule that has not been ratified, and inventing a
    home for them here would invite someone to fill it.
    """
    provenance: Literal["D1_D10"] = PROVENANCE_D1_D10
    d1_h10: D1TenthHouse
    d10_h10: D10TenthHouse


# ─────────────────────────────────────────────────────────────────────────────
# D9 × D10 · the D9 side
# ─────────────────────────────────────────────────────────────────────────────

class Proposition(Strict):
    """One archetype proposition, exactly as D9-R2 publishes it. The enum
    identifier is already dropped upstream; these two strings are the whole
    proposition."""
    title: str
    core_impulse: str


class ContextualVector(Strict):
    """PAIRWISE carries exactly one contextual vector with its Founder-locked
    role. THE ROLE KEY IS THE SEMANTICS AND THE LABEL IS DISPLAY, so both are
    preserved — carrying only the label is what forced D9 Flight 16 to compose
    one generic sentence for all three roles."""
    role_key: str
    role: str
    propositions: List[Proposition]


class D9Contribution(Strict):
    """The accepted `synthesis_material.contribution`, normalized.

    Every field any accepted mode can carry has a home here, and the normalizer
    refuses a payload carrying a key it does not recognise. That is what makes
    "no semantic loss" checkable rather than asserted: a new D9 mode or a new
    key inside an existing mode fails loudly instead of being silently dropped.

    NOTHING IS RECALCULATED. D10 is a consumer of D9 here, never a second D9
    engine.
    """
    mode: Literal["MATURITY_FALLBACK", "UNIFIED_PURPOSE", "PAIRWISE",
                  "COMPOUND_MULTI_POLAR"]
    # MATURITY_FALLBACK
    mature_quality: Optional[str] = None
    higher_value: Optional[str] = None
    # UNIFIED_PURPOSE and PAIRWISE
    primary: Optional[List[Proposition]] = None
    conviction: Optional[str] = None
    contextual_vector: Optional[ContextualVector] = None
    # COMPOUND_MULTI_POLAR
    primary_impact: Optional[List[Proposition]] = None
    ethical_driver: Optional[List[Proposition]] = None
    innate_aptitude: Optional[List[Proposition]] = None


# ─────────────────────────────────────────────────────────────────────────────
# D9 × D10 · the D10 delivery side
# ─────────────────────────────────────────────────────────────────────────────

class DeliveryStance(Strict):
    d10_lagna_sign: str
    lagnesh: str
    lagnesh_house: int = Field(ge=1, le=12)
    lagnesh_sign: str


class CounterpartyField(Strict):
    """H7 · clients, counterparties, public exchange."""
    house: Literal[7] = 7
    occupants: List[str]
    lord: str
    lord_placement: LordPlacement
    publication_state: Literal["OCCUPIED", "THROUGH_LORD", "SUPPORTED",
                               "PRESSURED"]


class WorkDelivery(Strict):
    """H10 · the vocation as lived."""
    house: Literal[10] = 10
    mode: Literal["OCCUPIED", "THROUGH_LORD"]
    occupants: List[str]
    lord: str
    lord_placement: LordPlacement


class D9D10Handshake(Strict):
    """`available` False means D9 published no contribution. That is a valid
    reading, not a failure and not FALSE: `contribution` is then None and
    `unavailable_reason` carries a machine code. Later publication can simply
    stay silent.

    The D10 delivery evidence is present either way, because it is D10's own
    fact and does not depend on what D9 said.

    NO AmK. Section 7 owns Work vehicle and the Amatyakaraka; pulling it in
    here would merge two speaker systems the format keeps apart. There is no
    field for it.
    """
    provenance: Literal["D9_D10"] = PROVENANCE_D9_D10
    available: bool
    unavailable_reason: Optional[str] = None
    contribution: Optional[D9Contribution] = None
    stance: DeliveryStance
    counterparty_field: CounterpartyField
    work_delivery: WorkDelivery


# ─────────────────────────────────────────────────────────────────────────────
# the whole thing
# ─────────────────────────────────────────────────────────────────────────────

class D10CrossChartFindings(Strict):
    crosschart_version: str = CROSSCHART_VERSION
    #: The single token all three inputs must share. Recorded so a consumer can
    #: see which chart this handshake belongs to without trusting the caller.
    chart_token: str
    d1_d10: D1D10Handshake
    d9_d10: D9D10Handshake
