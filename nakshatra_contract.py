"""
nakshatra_contract.py — NAK-001. The Nakshatra placement contract, and the ONE
placement policy that both the resolver and the validator read.

SCOPE. Astronomical placement only: index, name, pada, lord, longitude. No
prose, no corpus, no relationship verdict, no strength, no Pushkara, Gandanta
or Vargottama claim. Those are separate tickets with their own doctrinal and
harm review, and nothing here should make them look already decided.

ONE POLICY, TWO READERS. `placement_of()` below is the only implementation of
the partition in this module set. `NakshatraPlacement` calls it to RECOMPUTE
its own fields from `longitude` and reject any disagreement, and
`nakshatra_engine` calls it to build placements in the first place. That is the
Pratiphala shape: a validator that recomputes rather than one that cross-checks
fields against each other, because two fields agreeing proves only that they
agree.

EXACT RATIONAL PARTITION — why Fraction and not float division.
The partition points are multiples of 40/3 and 10/3 degrees, and neither is
representable in binary floating point. `int(longitude / (360.0 / 27))` is
therefore wrong near a boundary in a way that depends on how the boundary
constant was computed: multiplying k * (360.0/27) can land on the other side of
the true boundary from dividing by the same constant, so the "same" boundary has
two answers. Converting the incoming float to a Fraction is exact (a float IS a
rational), so the placement becomes the exact mathematical partition of the
exact value the payload carried. No epsilon, no tolerance, no rounded constant.

BOUNDARY OWNERSHIP. A value exactly on a boundary belongs to the LATER cell.
0 degrees is Ashwini pada 1; the boundary at 40/3 degrees is Bharani pada 1.

FAIL CLOSED. There is no `% 360`. A longitude outside [0, 360) is an error, not
something to normalise, because normalising turns corrupt data into a confident
placement. Missing data is an error for the same reason: the failure this module
exists to prevent is a chart with no Moon quietly rendering as Ashwini pada 1.
"""
from __future__ import annotations

import math
from enum import Enum
from fractions import Fraction
from typing import Any, List, Optional, Tuple

from pydantic import BaseModel, Extra, Field, StrictStr, conint, root_validator, validator

# REUSED, NOT REDEFINED. The nine grahas and their canonical order come from the
# accepted D1 contract. A private copy here would be a second vocabulary that
# could drift from the one the rest of the stack agrees on.
from d1_contract import Graha

CONTRACT_VERSION = "nakshatra-contract-0.1.0"
PARTITION_ID = "27x4-equal-sidereal"

# ── the partition, stated exactly ────────────────────────────────────────────

NAKSHATRA_COUNT = 27
PADA_PER_NAKSHATRA = 4
PADA_COUNT = NAKSHATRA_COUNT * PADA_PER_NAKSHATRA          # 108

ZODIAC_DEGREES = Fraction(360)
NAKSHATRA_SPAN = ZODIAC_DEGREES / NAKSHATRA_COUNT          # exactly 40/3
PADA_SPAN = NAKSHATRA_SPAN / PADA_PER_NAKSHATRA            # exactly 10/3

NAKSHATRA_NAMES: Tuple[str, ...] = (
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
    "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni",
    "Uttara Phalguni", "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha",
    "Jyeshtha", "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana",
    "Dhanishtha", "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada",
    "Revati",
)

# The Vimshottari cycle, in its canonical order, repeated three times across the
# 27. Written as the nine-element cycle and expanded, rather than as a
# transcribed 27-element list, because a transcribed list can carry a typo that
# no rule contradicts. Abhijit is NOT a member of this partition.
VIMSHOTTARI_LORD_CYCLE: Tuple[str, ...] = (
    "Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn",
    "Mercury",
)
NAKSHATRA_LORDS: Tuple[str, ...] = tuple(
    VIMSHOTTARI_LORD_CYCLE[i % len(VIMSHOTTARI_LORD_CYCLE)]
    for i in range(NAKSHATRA_COUNT)
)


class NakshatraContractError(ValueError):
    """A placement could not be produced or could not be trusted."""


class NakshatraSubject(str, Enum):
    """Who a placement belongs to. Lagna plus the nine grahas."""
    LAGNA = "Lagna"
    SUN = "Sun"; MOON = "Moon"; MARS = "Mars"; MERCURY = "Mercury"
    JUPITER = "Jupiter"; VENUS = "Venus"; SATURN = "Saturn"
    RAHU = "Rahu"; KETU = "Ketu"


GRAHA_SUBJECT_ORDER: Tuple[NakshatraSubject, ...] = tuple(
    NakshatraSubject(g.value) for g in Graha
)


# ── the one placement policy ─────────────────────────────────────────────────

def require_longitude(value: Any, where: str) -> float:
    """Accept only a real, finite, in-domain longitude. Never repair one.

    bool is rejected explicitly because it is a subclass of int in Python, and
    a silently coerced True would place a subject at 1 degree Ashwini. A string
    is rejected even when it parses, because a payload that sends "18.876" is a
    payload whose producer is not the certified engine.
    """
    if value is None:
        raise NakshatraContractError(f"{where}: longitude is missing")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise NakshatraContractError(
            f"{where}: longitude must be a real number, got "
            f"{type(value).__name__} {value!r}")
    value = float(value)
    if not math.isfinite(value):
        raise NakshatraContractError(f"{where}: longitude is not finite ({value!r})")
    if not (0.0 <= value < 360.0):
        raise NakshatraContractError(
            f"{where}: longitude {value!r} is outside [0, 360); this module does "
            f"not normalise out-of-domain values")
    return value


def pada_ordinal_of(longitude: float) -> int:
    """Global pada ordinal, 0..107. The single arithmetic statement of the
    partition; everything else in this file is derived from it."""
    lon = require_longitude(longitude, "placement")
    ordinal = math.floor(Fraction(lon) / PADA_SPAN)
    if not (0 <= ordinal < PADA_COUNT):
        # Unreachable for a longitude in [0, 360). Kept as a refusal rather than
        # a clamp: a clamp here would invent Revati pada 4 out of an arithmetic
        # fault instead of reporting it.
        raise NakshatraContractError(
            f"placement: pada ordinal {ordinal} outside 0..{PADA_COUNT - 1} for "
            f"longitude {lon!r}")
    return ordinal


def placement_of(longitude: float) -> Tuple[int, str, int, str]:
    """(nakshatra_index, nakshatra, pada, nakshatra_lord) for one longitude."""
    ordinal = pada_ordinal_of(longitude)
    index, pada = divmod(ordinal, PADA_PER_NAKSHATRA)
    return index, NAKSHATRA_NAMES[index], pada + 1, NAKSHATRA_LORDS[index]


# ── typed placement ──────────────────────────────────────────────────────────

class NakshatraPlacement(BaseModel):
    """One subject's placement, with every published field recomputed from
    `longitude` and compared. A payload cannot state Bharani at a Rohini
    longitude, whoever assembled it."""
    subject: NakshatraSubject
    longitude: float = Field(ge=0.0, lt=360.0)
    # conint(strict=True, ...) rather than StrictInt + Field(ge=): pydantic v1
    # silently DROPS ge/le set alongside a strict scalar type, and refuses to
    # build the model rather than enforce them. Strictness matters here because
    # True is an int and 2.0 is not a pada.
    nakshatra_index: conint(strict=True, ge=0, le=NAKSHATRA_COUNT - 1)
    nakshatra: StrictStr
    pada: conint(strict=True, ge=1, le=PADA_PER_NAKSHATRA)
    nakshatra_lord: StrictStr

    class Config:
        extra = Extra.forbid

    @validator("longitude", pre=True)
    def _longitude_is_real_and_in_domain(cls, v):
        return require_longitude(v, "placement")

    @root_validator(skip_on_failure=True)
    def _recompute_and_compare(cls, values):
        lon = values.get("longitude")
        if lon is None:
            return values
        index, name, pada, lord = placement_of(lon)
        mismatches = []
        for field, published, derived in (
            ("nakshatra_index", values.get("nakshatra_index"), index),
            ("nakshatra", values.get("nakshatra"), name),
            ("pada", values.get("pada"), pada),
            ("nakshatra_lord", values.get("nakshatra_lord"), lord),
        ):
            if published != derived:
                mismatches.append(f"{field}={published!r} (longitude gives {derived!r})")
        if mismatches:
            raise ValueError(
                f"placement contradicts its own longitude {lon!r}: "
                + "; ".join(mismatches))
        return values


def placement_for(subject: NakshatraSubject, longitude: Any) -> NakshatraPlacement:
    """Build a placement from a subject and a longitude, and nothing else."""
    lon = require_longitude(longitude, subject.value)
    index, name, pada, lord = placement_of(lon)
    return NakshatraPlacement(subject=subject, longitude=lon, nakshatra_index=index,
                              nakshatra=name, pada=pada, nakshatra_lord=lord)


# ── policy block ─────────────────────────────────────────────────────────────

class NakshatraPolicy(BaseModel):
    """What produced these placements, published so a stored response can be
    read years later without guessing which rules were in force."""
    contract_version: str = CONTRACT_VERSION
    engine_version: str
    partition: str = PARTITION_ID
    nakshatra_count: int = NAKSHATRA_COUNT
    pada_count: int = PADA_COUNT
    # Exact rather than decimal, because the decimal forms are not the values
    # used and publishing 13.3333 would misstate the partition.
    nakshatra_span_degrees: str = f"{NAKSHATRA_SPAN.numerator}/{NAKSHATRA_SPAN.denominator}"
    pada_span_degrees: str = f"{PADA_SPAN.numerator}/{PADA_SPAN.denominator}"
    lord_cycle: List[str] = Field(default_factory=lambda: list(VIMSHOTTARI_LORD_CYCLE))
    boundary_rule: str = "exact-boundary-belongs-to-the-later-cell"
    longitude_domain: str = "0 to 360 degrees, upper bound exclusive, never normalised"
    # NAK-001 publishes placement only. Stated positively so a later reader can
    # see the omission was a decision.
    publishes: List[str] = Field(
        default_factory=lambda: ["placement"])
    excluded: List[str] = Field(default_factory=lambda: [
        "corpus", "prose", "pada_interpretation", "relationship_verdict",
        "strength", "pushkara", "gandanta", "vargottama",
    ])

    class Config:
        extra = Extra.forbid


# ── request and response ─────────────────────────────────────────────────────

class NakshatraPrepareRequest(BaseModel):
    # StrictStr for the reason recorded on D1PrepareRequest: pydantic v1 coerces
    # a JSON number to a string, which turns a malformed request into a token
    # lookup and a 404 instead of an immediate 422.
    chart_token: StrictStr = Field(min_length=8, max_length=256)

    class Config:
        # The browser sends a token and nothing else. A longitude, a nakshatra
        # or a pada arriving here would be the client claiming authority over
        # placement, which is the whole defect NAK-B01 names. Extra.forbid makes
        # that a 422 at the boundary rather than a silent discard.
        extra = Extra.forbid


class NakshatraPrepareResponse(BaseModel):
    route_version: str
    chart_token: StrictStr
    policy: NakshatraPolicy
    calculation_meta: Optional[dict] = None
    lagna: NakshatraPlacement
    janma: NakshatraPlacement
    grahas: List[NakshatraPlacement] = Field(min_items=9, max_items=9)

    class Config:
        extra = Extra.forbid

    @root_validator(skip_on_failure=True)
    def _identities_are_exact(cls, values):
        lagna, janma = values.get("lagna"), values.get("janma")
        grahas = values.get("grahas") or []
        if lagna is not None and lagna.subject is not NakshatraSubject.LAGNA:
            raise ValueError(f"lagna block carries subject {lagna.subject.value}")
        if janma is not None and janma.subject is not NakshatraSubject.MOON:
            raise ValueError(
                f"janma is the Moon's nakshatra; got subject {janma.subject.value}")
        subjects = [g.subject for g in grahas]
        if subjects != list(GRAHA_SUBJECT_ORDER):
            raise ValueError(
                "grahas must be exactly the nine grahas in canonical order, got "
                + ", ".join(s.value for s in subjects))
        # ONE MOON. Janma is not a second computation of the Moon, it is the
        # same placement object's values. Publishing two Moon truths is how a
        # renderer ends up showing a different janma to the Moon card.
        moon = next((g for g in grahas if g.subject is NakshatraSubject.MOON), None)
        if janma is not None and moon is not None and janma.dict() != moon.dict():
            raise ValueError("janma does not match the Moon graha placement")
        return values
