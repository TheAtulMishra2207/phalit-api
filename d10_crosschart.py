"""
d10_crosschart.py — D10-004 · the cross-chart handshake facts authority.

PURE AND DETERMINISTIC. One public function, `build_crosschart_findings`. It
takes three accepted server outputs and returns facts. No I/O, no provider, no
clock, no browser input, no route.

IT CONSUMES; IT DOES NOT RECOMPUTE. Three certified authorities, each read for
exactly one thing:

    D10   the certified D10PrepareResponse, put through the D10-003
          `build_core_findings`. D10 houses, lords, dignity, AK/AmK,
          operational states and tension are all taken from there. None is
          rederived here.
    D1    the accepted D1PrepareResponse. ONLY natal H10 is read, and it is
          read out of the published `houses` list. No natal house is computed
          from a lagna or a planet sign anywhere in this file.
    D9    the accepted D9-R2 response, read at
          `report.synthesis_material.domains.contribution` and nowhere else.

D10 IS A CONSUMER OF D9, NEVER A SECOND D9 ENGINE. This module imports no D9
module at all — not the contribution selector, not the selectors, not the
doctrine tables, not Karakamsa. A structural test asserts the absence.

FAIL CLOSED ON A TOKEN MISMATCH. All three inputs must carry the same
chart_token. A handshake assembled from two different charts would be a
confident statement about a person who does not exist, so any mismatch raises
before a single fact is read.

WHAT THIS FLIGHT DOES NOT PRODUCE. No agreement word — `aligned`, `strained`
and `redirected` have no ratified rule and no field. No career meaning, no
profession, no job title, no salary, no timing, no remedy, no prose.
"""
from __future__ import annotations

import copy
from typing import Any, Dict, List, Mapping, Optional, Tuple

from d10_crosschart_contract import (
    CONTRIBUTION_MODES, D9_CONTRIBUTION_UNAVAILABLE,
    ContextualVector, CounterpartyField, D1D10Handshake, D1TenthHouse,
    D9Contribution, D9D10Handshake, D10CrossChartFindings, D10TenthHouse,
    DeliveryStance, LordPlacement, Proposition, WorkDelivery,
)
from d10_findings import build_core_findings

#: The keys each accepted contribution mode may carry, beyond `mode`.
#: A payload carrying anything else is MALFORMED, not silently trimmed: that is
#: what makes "normalized without semantic loss" a checkable claim rather than
#: an assertion. A new D9 mode, or a new key inside an existing one, fails
#: loudly here instead of vanishing.
_CONTRIBUTION_KEYS: Dict[str, Tuple[str, ...]] = {
    "MATURITY_FALLBACK": ("mature_quality", "higher_value"),
    "UNIFIED_PURPOSE": ("primary", "conviction"),
    "PAIRWISE": ("primary", "contextual_vector"),
    "COMPOUND_MULTI_POLAR": ("primary_impact", "ethical_driver",
                             "innate_aptitude"),
}
_PROPOSITION_LISTS = frozenset({"primary", "primary_impact", "ethical_driver",
                                "innate_aptitude"})


class D10CrossChartError(ValueError):
    """An input is missing, malformed, or belongs to another chart. Raised,
    never defaulted."""


class ChartTokenMismatch(D10CrossChartError):
    """Two of the three inputs describe different charts."""


# ─────────────────────────────────────────────────────────────────────────────
# readers
# ─────────────────────────────────────────────────────────────────────────────

def _mapping(value: Any, where: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise D10CrossChartError(f"{where} is missing or not an object")
    return value


def _text(value: Any, where: str) -> str:
    if not isinstance(value, str) or not value:
        raise D10CrossChartError(f"{where}: expected a non-empty string, got {value!r}")
    return value


def _token(payload: Any, where: str) -> str:
    return _text(_mapping(payload, where).get("chart_token"),
                 f"{where}.chart_token")


def _names(value: Any, where: str) -> List[str]:
    """A list of graha names. Accepts the enum-valued lists D1 publishes and
    the plain strings D10 publishes, without caring which."""
    if not isinstance(value, (list, tuple)):
        raise D10CrossChartError(f"{where}: expected a list, got {value!r}")
    out = []
    for item in value:
        out.append(_text(getattr(item, "value", item), f"{where} entry"))
    return out


def _assert_same_chart(d10: Any, d1: Any, d9: Any) -> str:
    """FAIL CLOSED. All three must be the same chart, checked pairwise so the
    error names which pair disagreed.

    No partial handshake is possible: this runs before any fact is read, so a
    mismatch cannot produce a half-assembled result.
    """
    t10 = _token(d10, "d10_prepare")
    t1 = _token(d1, "d1_prepare")
    t9 = _token(d9, "d9_report")
    for (a, an), (b, bn) in (((t10, "d10"), (t1, "d1")),
                             ((t10, "d10"), (t9, "d9")),
                             ((t1, "d1"), (t9, "d9"))):
        if a != b:
            raise ChartTokenMismatch(
                f"{an} and {bn} chart tokens differ ({a!r} vs {b!r}); refusing "
                f"to combine two charts into one handshake")
    return t10


# ─────────────────────────────────────────────────────────────────────────────
# D1 × D10
# ─────────────────────────────────────────────────────────────────────────────

def _d1_tenth(d1_payload: Mapping[str, Any]) -> D1TenthHouse:
    """Read natal H10 out of the accepted D1 output.

    NOTHING IS RECOMPUTED. The house is located by its published `house`
    number, and its sign, lord and occupants are taken as published. This
    function contains no lagna arithmetic and no sign offset.
    """
    d1 = _mapping(_mapping(d1_payload, "d1_prepare").get("d1"), "d1_prepare.d1")
    houses = d1.get("houses")
    if not isinstance(houses, list):
        raise D10CrossChartError("d1_prepare.d1.houses is missing or not a list")
    tenth = None
    for h in houses:
        rec = h if isinstance(h, Mapping) else getattr(h, "__dict__", None)
        if not isinstance(rec, Mapping):
            raise D10CrossChartError("a D1 house entry is not an object")
        if rec.get("house") == 10:
            if tenth is not None:
                raise D10CrossChartError("D1 publishes house 10 more than once")
            tenth = rec
    if tenth is None:
        raise D10CrossChartError("D1 output publishes no house 10")
    lord = tenth.get("lord")
    return D1TenthHouse(
        sign=_text(tenth.get("sign"), "d1.h10.sign"),
        sign_index=_sign_index(tenth.get("sign_index"), "d1.h10.sign_index"),
        lord=_text(getattr(lord, "value", lord), "d1.h10.lord"),
        occupants=sorted(_names(tenth.get("occupants"), "d1.h10.occupants")),
    )


def _sign_index(value: Any, where: str) -> int:
    if type(value) is not int or not 0 <= value <= 11:
        raise D10CrossChartError(f"{where}: sign_index must be 0-11, got {value!r}")
    return value


def _lord_placement(p: Any) -> LordPlacement:
    return LordPlacement(planet=p.planet, house=p.house, sign=p.sign,
                         dignity=p.dignity)


def _d10_tenth(findings) -> D10TenthHouse:
    """Read D10 H10 from the D10-003 findings authority.

    The Function block already holds it, computed by the accepted builder. The
    THROUGH_LORD mode travels through unchanged: it is not recomputed from an
    empty occupant list here, because the mode is the authority's finding and
    an independent rederivation could disagree with it.
    """
    h10 = findings.function.h10
    return D10TenthHouse(
        sign=h10.sign, sign_index=h10.sign_index, lord=h10.lord.planet,
        occupants=list(h10.occupants), mode=h10.mode,
        lord_placement=_lord_placement(h10.lord),
    )


# ─────────────────────────────────────────────────────────────────────────────
# D9 × D10 · the D9 side
# ─────────────────────────────────────────────────────────────────────────────

def _propositions(value: Any, where: str) -> List[Proposition]:
    if not isinstance(value, (list, tuple)) or not value:
        raise D10CrossChartError(f"{where}: expected a non-empty list")
    out = []
    for e in value:
        rec = _mapping(e, f"{where} entry")
        extra = set(rec) - {"title", "core_impulse"}
        if extra:
            raise D10CrossChartError(
                f"{where} entry carries unrecognised keys {sorted(extra)}; "
                f"refusing rather than dropping D9 meaning")
        out.append(Proposition(title=_text(rec.get("title"), f"{where}.title"),
                               core_impulse=_text(rec.get("core_impulse"),
                                                  f"{where}.core_impulse")))
    return out


def _normalize_contribution(raw: Any) -> D9Contribution:
    """Normalize the accepted `synthesis_material.contribution`.

    MALFORMED IS NOT UNAVAILABLE. A contribution key that is present but does
    not match an accepted mode raises. Turning it into "unavailable" would let a
    broken D9 report look like a silent one, and the two mean opposite things:
    silence is a valid reading, breakage is not.
    """
    rec = _mapping(raw, "d9 contribution")
    mode = rec.get("mode")
    if mode not in CONTRIBUTION_MODES:
        raise D10CrossChartError(
            f"d9 contribution mode {mode!r} is not an accepted D9-R2 mode "
            f"{list(CONTRIBUTION_MODES)}")

    allowed = set(_CONTRIBUTION_KEYS[mode]) | {"mode"}
    unknown = set(rec) - allowed
    if unknown:
        raise D10CrossChartError(
            f"d9 contribution mode {mode} carries unrecognised keys "
            f"{sorted(unknown)}; refusing rather than dropping D9 meaning")

    fields: Dict[str, Any] = {"mode": mode}
    for key in _CONTRIBUTION_KEYS[mode]:
        if key not in rec:
            continue
        value = rec[key]
        if key in _PROPOSITION_LISTS:
            fields[key] = _propositions(value, f"contribution.{key}")
        elif key == "contextual_vector":
            cv = _mapping(value, "contribution.contextual_vector")
            extra = set(cv) - {"role_key", "role", "propositions"}
            if extra:
                raise D10CrossChartError(
                    f"contextual_vector carries unrecognised keys {sorted(extra)}")
            fields[key] = ContextualVector(
                role_key=_text(cv.get("role_key"), "contextual_vector.role_key"),
                role=_text(cv.get("role"), "contextual_vector.role"),
                propositions=_propositions(cv.get("propositions"),
                                           "contextual_vector.propositions"))
        else:
            fields[key] = _text(value, f"contribution.{key}")

    if len(fields) == 1:
        raise D10CrossChartError(
            f"d9 contribution mode {mode} carries no content beyond its mode")
    return D9Contribution(**fields)


def _read_contribution(d9_payload: Mapping[str, Any]):
    """Locate the accepted contribution on the ONE accepted D9 path.

        d9_prepare -> report -> synthesis_material -> domains -> contribution

    D10-004-CORR-01 · this was previously read one level too shallow, at
    `synthesis_material.contribution`. `build_synthesis_material` returns
    `{"domains": material, "domain_count": ..., "introduces_new_propositions":
    ...}`, so the contribution has always sat inside `domains`. The old binding
    could never have found a real one, and the D10-004 fixture manufactured the
    wrong container, which is why the suite passed against the mistake rather
    than catching it.

    THERE IS NO COMPATIBILITY FALLBACK. The shallow path is not tried, not
    accepted, and not read as silence: one accepted server authority means one
    path. A payload carrying the old shape reaches `domains` missing and is
    REFUSED, which is what makes the correction verifiable.

    SILENCE VERSUS MALFORMED. A valid accepted D9 preparation always carries
    `report`, `synthesis_material` and `domains`. Absence of any of those is a
    broken upstream payload, not a reading, and is refused. The ONLY valid
    silence is `domains` present and well formed with no `contribution` key —
    a D9 report that had nothing publishable to say, which later publication
    can honour by staying quiet.
    """
    payload = _mapping(d9_payload, "d9_report")
    # Each of the three containers is REQUIRED. A missing one is a malformed
    # upstream payload, never silence.
    report = _mapping(payload.get("report"),
                      "d9_report.report (a valid D9 preparation always has one)")
    material = _mapping(
        report.get("synthesis_material"),
        "d9_report.report.synthesis_material (a valid D9 preparation always "
        "has one)")
    domains = _mapping(
        material.get("domains"),
        "d9_report.report.synthesis_material.domains (a valid D9 preparation "
        "always has one; note the contribution lives INSIDE domains)")

    # D10-004-CORR-02 · SILENCE IS KEY ABSENCE, NOT A FALSY VALUE.
    #
    # `domains.get("contribution")` conflated two different upstream states: a
    # container that never mentions contribution, and one that mentions it and
    # supplies None. The first is a D9 report with nothing publishable to say.
    # The second is a broken payload — D9 does not emit a null contribution,
    # and treating it as silence would let a malformed upstream look like a
    # valid quiet one, which is the distinction this layer exists to keep.
    #
    # `not in` also stops False, 0 and "" from reading as silence for the same
    # reason: they are values, and any value present here goes to the
    # normalizer, which refuses everything that is not an accepted mode.
    if "contribution" not in domains:
        return None, D9_CONTRIBUTION_UNAVAILABLE
    # PRESENT. From here a problem is a refusal, never a downgrade to silence.
    return _normalize_contribution(domains["contribution"]), None


# ─────────────────────────────────────────────────────────────────────────────
# D9 × D10 · the D10 delivery side
# ─────────────────────────────────────────────────────────────────────────────

def _delivery(findings) -> Tuple[DeliveryStance, CounterpartyField, WorkDelivery]:
    """Stance, H7 and H10, all read from the D10-003 authority.

    NO AmK. Section 7 owns the Work vehicle, and the Amatyakaraka is not read
    anywhere in this function.
    """
    stance = DeliveryStance(
        d10_lagna_sign=findings.stance.d10_lagna_sign,
        lagnesh=findings.stance.lagnesh.planet,
        lagnesh_house=findings.stance.lagnesh.house,
        lagnesh_sign=findings.stance.lagnesh.sign,
    )
    seventh = None
    for group in findings.operational_map:
        for house in group.houses:
            if house.house == 7:
                seventh = house
    if seventh is None:
        raise D10CrossChartError("D10 findings publish no house 7")
    counterparty = CounterpartyField(
        occupants=list(seventh.occupants),
        lord=seventh.lord,
        lord_placement=LordPlacement(planet=seventh.lord,
                                     house=seventh.lord_house,
                                     sign=seventh.lord_sign,
                                     dignity=seventh.lord_dignity),
        publication_state=seventh.publication_state,
    )
    h10 = findings.function.h10
    work = WorkDelivery(mode=h10.mode, occupants=list(h10.occupants),
                        lord=h10.lord.planet,
                        lord_placement=_lord_placement(h10.lord))
    return stance, counterparty, work


# ─────────────────────────────────────────────────────────────────────────────
# the one public entry point
# ─────────────────────────────────────────────────────────────────────────────

def build_crosschart_findings(d10_prepare: Mapping[str, Any],
                              d1_prepare: Mapping[str, Any],
                              d9_report: Mapping[str, Any]
                              ) -> D10CrossChartFindings:
    """Assemble the two-chart handshake substrate from three certified outputs.

    Pure. Deterministic. The inputs are deep-copied before anything is read, so
    an accepted upstream model handed in by a caller cannot be mutated by this
    layer.
    """
    token = _assert_same_chart(d10_prepare, d1_prepare, d9_report)

    d10_prepare = copy.deepcopy(dict(d10_prepare))
    d1_prepare = copy.deepcopy(dict(d1_prepare))
    d9_report = copy.deepcopy(dict(d9_report))

    # THE D10-003 AUTHORITY, REUSED. Houses, lords, dignity, operational states
    # and modes all come from here; none is rederived in this module.
    findings = build_core_findings(d10_prepare)

    contribution, reason = _read_contribution(d9_report)
    stance, counterparty, work = _delivery(findings)

    return D10CrossChartFindings(
        chart_token=token,
        d1_d10=D1D10Handshake(d1_h10=_d1_tenth(d1_prepare),
                              d10_h10=_d10_tenth(findings)),
        d9_d10=D9D10Handshake(
            available=contribution is not None,
            unavailable_reason=reason,
            contribution=contribution,
            stance=stance, counterparty_field=counterparty,
            work_delivery=work),
    )
