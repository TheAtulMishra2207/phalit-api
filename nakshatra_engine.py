"""
nakshatra_engine.py — NAK-001. Certified /chart body -> Nakshatra placements.

This module TRANSLATES and VERIFIES. It computes the partition (through the one
policy in nakshatra_contract) and it computes nothing else: no ayanamsha, no
longitude, no sign, no varga. Astronomy belongs to chart engine 1.1.0 and the
frozen Swiss deployment, and a second source of longitudes here would be the
same defect as the client-side engines this ticket exists to remove.

VERIFY IN BOTH DIRECTIONS. The certified chart already publishes `nakshatra`,
`nakshatra_pada` and `nakshatra_lord` per graha, produced by an independent code
path in main.py. This module derives all three from the absolute longitude and
compares. Agreement is not decoration: it is the only evidence that the new
partition and the deployed one describe the same zodiac. A mismatch is a refusal,
never a preference for one side.

The Moon has a THIRD independent witness in the same payload: `dasha`
carries `moon_nakshatra` and `moon_nakshatra_lord`, computed by the Vimshottari
seed rather than by the placement code. It is verified too when present, and the
test suite asserts the three agree on the chart of record.

WHAT IS NOT HERE. No corpus, no prose, no pada interpretation, no relationship
verdict, no strength, no Pushkara, Gandanta or Vargottama claim. NAK-001 is
placement. `vargottama` in particular is a certified chart fact and must never be
inferred from pada metadata.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import ValidationError

from d1_contract import Graha
# REUSED. The provenance gate is the accepted rule for whether a stored chart may
# enter an interpretation pipeline at all. A second, weaker gate here would mean
# a chart rejected by /d1/prepare could still be published through this route.
from d1_chart_adapter import ChartAdapterError, check_provenance
from nakshatra_contract import (
    GRAHA_SUBJECT_ORDER, NakshatraContractError, NakshatraPlacement,
    NakshatraPolicy, NakshatraPrepareResponse, NakshatraSubject,
    placement_for, require_longitude,
)

ENGINE_VERSION = "nakshatra-engine-0.1.0"


class NakshatraEngineError(ValueError):
    """The stored chart cannot produce a trustworthy placement set."""


def _require_mapping(value: Any, where: str) -> Dict[str, Any]:
    if value is None:
        raise NakshatraEngineError(f"certified chart is missing {where}")
    if not isinstance(value, dict):
        raise NakshatraEngineError(
            f"certified chart {where} must be an object, got {type(value).__name__}")
    return value


def _lagna_longitude(lagna: Dict[str, Any]) -> float:
    """Absolute sidereal longitude of the Ascendant.

    The certified chart publishes `longitude` directly. The sign_index/degree
    reconstruction is the documented fallback for a snapshot that predates that
    field; it is a REARRANGEMENT of two published certified values, not a
    calculation, and it is refused rather than approximated if either is absent
    or out of range.
    """
    if "longitude" in lagna:
        return require_longitude(lagna.get("longitude"), "lagna")

    sign_index = lagna.get("sign_index")
    if isinstance(sign_index, bool) or not isinstance(sign_index, int):
        raise NakshatraEngineError(
            "lagna carries no longitude and no usable sign_index; refusing to "
            "place the Ascendant")
    if not (0 <= sign_index <= 11):
        raise NakshatraEngineError(f"lagna sign_index {sign_index!r} outside 0..11")
    degree = lagna.get("degree")
    if isinstance(degree, bool) or not isinstance(degree, (int, float)):
        raise NakshatraEngineError(
            "lagna carries no longitude and no usable degree; refusing to place "
            "the Ascendant")
    degree = float(degree)
    if not (0.0 <= degree < 30.0):
        raise NakshatraEngineError(f"lagna degree {degree!r} outside [0, 30)")
    return require_longitude(sign_index * 30.0 + degree, "lagna")


def _verify_against_published(placement: NakshatraPlacement,
                              raw: Dict[str, Any]) -> None:
    """Compare the derived placement with the chart's own published fields.

    The certified engine emits all three for every graha. Their ABSENCE is a
    refusal, not a licence to publish the derived value unchecked: a payload
    that does not carry them was not produced by chart engine 1.1.0, and the
    verification this function exists to perform would simply not happen.
    """
    subject = placement.subject.value
    missing = [k for k in ("nakshatra", "nakshatra_pada", "nakshatra_lord")
               if raw.get(k) is None]
    if missing:
        raise NakshatraEngineError(
            f"{subject}: certified chart does not publish {', '.join(missing)}; "
            f"the derived placement cannot be verified and will not be published")

    mismatches = []
    for key, derived in (("nakshatra", placement.nakshatra),
                         ("nakshatra_pada", placement.pada),
                         ("nakshatra_lord", placement.nakshatra_lord)):
        published = raw.get(key)
        if published != derived:
            mismatches.append(f"{key}: chart says {published!r}, longitude gives {derived!r}")
    if mismatches:
        raise NakshatraEngineError(
            f"{subject}: derived placement disagrees with the certified chart "
            f"({'; '.join(mismatches)}); refusing to publish either")


def _verify_moon_against_dasha(placement: NakshatraPlacement,
                               dasha: Any) -> None:
    """Third witness. The Vimshottari seed names the Moon's nakshatra and lord
    from its own code path, so it is an independent check on the janma identity
    rather than a restatement of the planet block."""
    if not isinstance(dasha, dict):
        return
    published_name = dasha.get("moon_nakshatra")
    published_lord = dasha.get("moon_nakshatra_lord")
    mismatches = []
    if published_name is not None and published_name != placement.nakshatra:
        mismatches.append(
            f"moon_nakshatra: dasha says {published_name!r}, longitude gives "
            f"{placement.nakshatra!r}")
    if published_lord is not None and published_lord != placement.nakshatra_lord:
        mismatches.append(
            f"moon_nakshatra_lord: dasha says {published_lord!r}, longitude gives "
            f"{placement.nakshatra_lord!r}")
    if mismatches:
        raise NakshatraEngineError(
            "janma identity disagrees with the Vimshottari seed in the same "
            "chart (" + "; ".join(mismatches) + ")")


def build_nakshatra_payload(chart: Dict[str, Any], chart_token: str,
                            route_version: str) -> NakshatraPrepareResponse:
    """Whole module in one function: read, place, verify, publish."""
    if not isinstance(chart, dict):
        raise NakshatraEngineError("certified chart payload must be an object")

    try:
        check_provenance(chart.get("calculation_meta"))
    except ChartAdapterError as e:
        # Re-raised in this module's own type so the route has one class of
        # data refusal to handle, per the ticket.
        raise NakshatraEngineError(str(e)) from e

    lagna_block = _require_mapping(chart.get("lagna"), "lagna")
    planets = _require_mapping(chart.get("planets"), "planets")

    try:
        lagna = placement_for(NakshatraSubject.LAGNA, _lagna_longitude(lagna_block))
    except NakshatraContractError as e:
        raise NakshatraEngineError(str(e)) from e

    grahas: List[NakshatraPlacement] = []
    for graha in Graha:
        raw = planets.get(graha.value)
        if raw is None:
            raise NakshatraEngineError(
                f"certified chart is missing planet {graha.value!r}; a partial "
                f"placement set is never published")
        if not isinstance(raw, dict):
            raise NakshatraEngineError(
                f"chart.planets[{graha.value!r}] must be an object, got "
                f"{type(raw).__name__}")
        try:
            placement = placement_for(NakshatraSubject(graha.value),
                                      raw.get("longitude"))
        except NakshatraContractError as e:
            raise NakshatraEngineError(str(e)) from e
        _verify_against_published(placement, raw)
        grahas.append(placement)

    janma = next(g for g in grahas if g.subject is NakshatraSubject.MOON)
    _verify_moon_against_dasha(janma, chart.get("dasha"))

    policy = NakshatraPolicy(engine_version=ENGINE_VERSION)
    try:
        return NakshatraPrepareResponse(
            route_version=route_version,
            chart_token=chart_token,
            policy=policy,
            calculation_meta=chart.get("calculation_meta"),
            lagna=lagna,
            # The SAME object, not a second placement of the Moon. There is one
            # Moon truth in this payload by construction, so the contract's
            # janma-equals-Moon invariant cannot be satisfied by two computations
            # that happen to agree today.
            janma=janma,
            grahas=grahas,
        )
    except ValidationError as e:
        raise NakshatraEngineError(f"assembled payload failed its own contract: {e}") from e


# Order is part of the contract, so it is CHECKED here rather than assumed by the
# loop above happening to iterate the enum in the right order. Written as a raise
# and not an assert: python -O strips asserts, and a guard that disappears under a
# flag is a claim with nothing behind it.
if tuple(NakshatraSubject(g.value) for g in Graha) != GRAHA_SUBJECT_ORDER:
    raise NakshatraEngineError(
        "graha iteration order does not match the contract's canonical order")
