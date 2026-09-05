"""d12_contract.py — Phalit.ai D12 Dvādaśāṁśa mechanical contract.

D12-003. The typed shape of certified D12 mechanical facts, for the later
/d12/prepare flight to publish and for tests to pin. Mirrors the strictness of
the accepted d10_contract (pydantic v1, Extra.forbid, bounded fields); carries
NO doctrine, NO dignity, NO prose — those are governed by the locked FR
artifacts and belong to later flights.

Nothing in main.py imports this module in D12-003: the /chart seam publishes
only the bare `d12_sign_index` integer per body, computed by d12_engine. This
contract exists now so the field's meaning is pinned in the same change that
introduces it, and so the follow-on route flight has a frozen shape to build
against instead of inventing one mid-flight.
"""

from __future__ import annotations

from typing import Any, Dict, List

from pydantic import BaseModel, Extra, StrictBool, confloat, conint, constr, validator

from d12_engine import (  # noqa: F401  (re-exported for consumers and tests)
    D12DomainError,
    DIGNITY_STATES,
    GRADED_STATES,
    NODES,
    PORTION_COUNT,
    PORTION_DEGREES,
    UNGRADED,
    D12Doctrine,
    build_d12_facts,
    d12_dignity,
    d12_house,
    d12_sign_index,
    is_d12_first_slice_vargottama,
)

CONTRACT_VERSION = "d12-mechanical-1.0"

# The nine bodies D12 places. Lordship of the D12 Lagna sign decides nothing
# here; lords are derivable downstream from sign_lords and are deliberately not
# duplicated into this contract.
D12_GRAHAS = ("Sun", "Moon", "Mars", "Mercury", "Jupiter",
              "Venus", "Saturn", "Rahu", "Ketu")

# Ungraded is admissible as a mechanical/publication state but carries NO rank.
# A consumer ordering dignity must use GRADED_STATES and handle Ungraded
# separately; nothing here assigns it a position among the six.
DignityState = constr(strict=True)

SignIndex = conint(strict=True, ge=0, le=11)
HouseNumber = conint(strict=True, ge=1, le=12)


class D12Placement(BaseModel):
    """One body's certified D12 mechanical facts."""
    d12_sign_index: SignIndex
    d12_house: HouseNumber
    first_slice_vargottama: StrictBool

    class Config:
        extra = Extra.forbid
        allow_mutation = False


class D12MechanicalFacts(BaseModel):
    """The full mechanical layer for one chart: the D12 Lagna sign and all nine
    placements. House 1..12 always; there is no 0 and no absent-body sentinel —
    a chart that cannot supply a body fails validation instead of publishing a
    neutral-looking value (D12-001 finding F-09).
    """
    contract_version: str = CONTRACT_VERSION
    d12_lagna_sign_index: SignIndex
    lagna_first_slice_vargottama: StrictBool
    placements: Dict[str, D12Placement]

    class Config:
        extra = Extra.forbid
        allow_mutation = False

    def validate_complete(self) -> "D12MechanicalFacts":
        """Exactly the nine grahas, no more, no fewer, houses consistent with
        the Lagna. Called by the future route before anything is published."""
        names = tuple(sorted(self.placements))
        if names != tuple(sorted(D12_GRAHAS)):
            raise D12DomainError(
                f"placements must cover exactly the nine grahas, got {names}")
        for graha, p in self.placements.items():
            expect = d12_house(p.d12_sign_index, self.d12_lagna_sign_index)
            if p.d12_house != expect:
                raise D12DomainError(
                    f"{graha}: house {p.d12_house} inconsistent with lagna "
                    f"{self.d12_lagna_sign_index} (expected {expect})")
        return self


D12Degree = confloat(strict=True, ge=0.0, lt=30.0)


class D12GrahaPosition(BaseModel):
    """One graha's full mechanical D12 row (contract §7)."""
    graha: constr(strict=True, min_length=1)
    d1_sign_index: SignIndex
    d12_sign_index: SignIndex
    # D12-005-CORR-01 · the certified exact D12 coordinate FR-004 needs.
    d12_degree_in_sign: D12Degree
    d12_sign: constr(strict=True, min_length=1)
    slice: conint(strict=True, ge=1, le=12)
    house: HouseNumber
    dignity_state: DignityState
    vargottama: StrictBool

    class Config:
        extra = Extra.forbid
        allow_mutation = False

    @validator("dignity_state")
    def _state_is_in_the_frozen_vocabulary(cls, v):
        if v not in DIGNITY_STATES:
            raise ValueError(f"dignity_state {v!r} outside the frozen D12 vocabulary")
        return v

    @validator("dignity_state")
    def _nodes_are_ungraded(cls, v, values):
        # FR-004, enforced by the contract as well as the engine, so a future
        # producer cannot publish a graded node through this shape.
        if values.get("graha") in NODES and v != UNGRADED:
            raise ValueError(f"{values['graha']} must be {UNGRADED} in D12, got {v!r}")
        return v


class D12HouseRow(BaseModel):
    """One of the twelve whole-sign D12 house rows (contract §7)."""
    house: HouseNumber
    sign_index: SignIndex
    sign: constr(strict=True, min_length=1)
    lord: constr(strict=True, min_length=1)
    occupants: List[str] = []

    class Config:
        extra = Extra.forbid
        allow_mutation = False


class D12Lagna(BaseModel):
    d1_sign_index: SignIndex
    d12_sign_index: SignIndex
    d12_degree_in_sign: D12Degree
    d12_sign: constr(strict=True, min_length=1)
    lagnesh: constr(strict=True, min_length=1)

    class Config:
        extra = Extra.forbid
        allow_mutation = False


class D12FactSet(BaseModel):
    """Exactly one Lagna, nine grahas, twelve houses. No prose fields.

    Deliberately absent, and forbidden by Extra.forbid: father, mother, debt,
    residue, release, tension, instruction, remedy, health, maraka, past-life
    identity. Those belong to the frozen §§0-15 and to later bounded flights.
    """
    schema_version: str = CONTRACT_VERSION
    lagna: D12Lagna
    placements: Dict[str, D12GrahaPosition]
    houses: List[D12HouseRow]

    class Config:
        extra = Extra.forbid
        allow_mutation = False

    @validator("placements")
    def _exactly_the_nine_grahas(cls, v):
        if tuple(sorted(v)) != tuple(sorted(D12_GRAHAS)):
            raise ValueError(f"placements must be exactly the nine grahas, got {sorted(v)}")
        return v

    @validator("houses")
    def _exactly_twelve_houses_in_order(cls, v):
        if [r.house for r in v] != list(range(1, 13)):
            raise ValueError("houses must be rows 1..12 in order")
        return v


def facts_to_contract(facts: Dict[str, Any]) -> D12FactSet:
    """Typed view of build_d12_facts output. Validation only; no derivation."""
    return D12FactSet(
        lagna=D12Lagna(**facts["d12_lagna"]),
        placements={g: D12GrahaPosition(**p) for g, p in facts["placements"].items()},
        houses=[D12HouseRow(**r) for r in facts["houses"]])
