"""
test_nakshatra.py — NAK-001. Backend Nakshatra placement contract.

TWO RULES THIS SUITE FOLLOWS.

1. It never restates the code it tests. The canonical name and lord tables are
   checked against an INDEPENDENT ORACLE: the tables in main.py, transcribed
   separately by the deployed chart engine and read here with `ast` rather than
   imported, so a shared typo cannot make both sides agree. The 108 boundary
   expectations are built from the cell ordinal k directly — cell k must be
   nakshatra k//4, pada k%4+1, by the definition of the enumeration — not by
   re-running the engine's own arithmetic and comparing it with itself.

2. It proves the refusals, not only the successes. Roughly half of these cases
   assert that something is REJECTED, because the defect this module exists to
   prevent is a missing Moon quietly rendering as Ashwini pada 1.

Requirement map (the numbering is the ticket's):
    1  test_twenty_seven_names_match_the_deployed_engine_table
    2  test_lord_sequence_matches_the_deployed_engine_table
       test_lord_cycle_is_nine_repeated_three_times
    3  test_every_nakshatra_holds_exactly_four_padas
    4  test_all_108_cells_are_reachable_exactly_once
    5  test_nakshatra_boundaries_below_at_and_above
    6  test_pada_boundaries_below_at_and_above
    7  test_zero_degrees_is_ashwini_pada_one
    8  test_just_below_360_is_revati_pada_four
    9  test_360_and_invalid_longitudes_are_rejected
    10 test_missing_moon_longitude_is_rejected
    11 test_missing_lagna_longitude_inputs_are_rejected
    12 test_missing_graha_longitude_is_rejected
    13 test_no_missing_value_becomes_ashwini_pada_one
    14 test_founder_chart_placements_match_the_golden_astronomy
       test_founder_lagna_placement
       test_janma_agrees_with_the_vimshottari_seed
    15 test_all_nine_grahas_returned_exactly_once
    16 test_janma_is_exactly_the_moon_placement
       test_janma_that_disagrees_with_the_moon_is_rejected
    17 test_published_nakshatra_mismatch_is_rejected
       test_published_pada_mismatch_is_rejected
       test_published_lord_mismatch_is_rejected
       test_placement_contradicting_its_own_longitude_is_rejected
    17 (corr) test_422_detail_is_static_and_leaks_no_chart_contents
       (corr) test_422_detail_is_identical_across_different_refusals
       (corr) test_valid_requests_are_unchanged_by_the_correction
    18 test_response_token_is_the_requested_token
    19 test_non_string_token_types_return_422
       test_token_length_bounds_return_422
       test_unknown_request_field_returns_422
       test_raw_chart_facts_in_the_request_return_422
    20 test_unknown_token_returns_404
    21 test_unconfigured_resolver_returns_503
    22 test_repeated_preparation_is_deterministic
    23 test_response_contains_no_html
    24 test_response_contains_no_prose
    25 test_response_contains_no_relationship_score_or_strength_fields
    26 test_route_is_registered_exactly_once_in_main
    27 covered by the cross-suite pytest invocation, not by this file
"""
from __future__ import annotations

import ast
import json
import logging
import math
import os
import re
from fractions import Fraction

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from d1_contract import Graha
from d1_routes import ChartNotFound, get_chart_resolver
from nakshatra_contract import (
    NAKSHATRA_COUNT, NAKSHATRA_LORDS, NAKSHATRA_NAMES, NAKSHATRA_SPAN,
    PADA_COUNT, PADA_SPAN, PADA_PER_NAKSHATRA, VIMSHOTTARI_LORD_CYCLE,
    NakshatraContractError, NakshatraPlacement, NakshatraPrepareResponse,
    NakshatraSubject, placement_for, placement_of,
)
from nakshatra_engine import NakshatraEngineError, build_nakshatra_payload
from nakshatra_routes import ROUTE_VERSION, router

HERE = os.path.dirname(os.path.abspath(__file__))
CHART_OF_RECORD = os.path.join(HERE, "step10_chart_of_record.json")
MAIN_PY = os.path.join(HERE, "main.py")


# ── independent oracle: the deployed engine's own tables ─────────────────────

def _main_py_literal(name):
    """Read a module-level list literal out of main.py WITHOUT importing it.

    Importing main.py pulls in pyswisseph and the whole application; parsing it
    gets the transcribed table and nothing else. The point is that this table
    was written by a different author on a different day from the one in
    nakshatra_contract.py, so agreement between them is evidence rather than
    tautology.
    """
    with open(MAIN_PY, "r", encoding="utf-8") as fh:
        tree = ast.parse(fh.read())
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    return ast.literal_eval(node.value)
    raise AssertionError(f"{name} not found at module level in main.py")


@pytest.fixture(scope="module")
def chart_of_record():
    with open(CHART_OF_RECORD, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _boundary_floats(exact: Fraction):
    """(largest float strictly below `exact`, smallest float at or above it).

    Built from the exact rational boundary rather than from a float constant,
    because k * (360.0/27) and 360.0/27 * k can land on opposite sides of the
    true boundary. Every boundary assertion in this file is anchored to the
    mathematics, not to a particular float expression.
    """
    at = float(exact)
    if Fraction(at) < exact:
        at = math.nextafter(at, math.inf)
    below = at
    while Fraction(below) >= exact:
        below = math.nextafter(below, -math.inf)
    return below, at


class StubResolver:
    def __init__(self, body=None, raises=None):
        self.body, self.raises = body, raises
        self.calls = 0

    async def resolve(self, chart_token):
        self.calls += 1
        if self.raises:
            raise self.raises
        return self.body


def make_client(resolver):
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_chart_resolver] = lambda: resolver
    return TestClient(app)


# ── 1, 2 · canonical tables against the independent oracle ───────────────────

def test_twenty_seven_names_match_the_deployed_engine_table():
    oracle = _main_py_literal("NAKSHATRAS")
    assert len(NAKSHATRA_NAMES) == NAKSHATRA_COUNT == 27
    assert len(set(NAKSHATRA_NAMES)) == 27, "names must be unique"
    assert list(NAKSHATRA_NAMES) == list(oracle)
    assert NAKSHATRA_NAMES[0] == "Ashwini" and NAKSHATRA_NAMES[-1] == "Revati"
    assert "Abhijit" not in NAKSHATRA_NAMES


def test_lord_sequence_matches_the_deployed_engine_table():
    oracle = _main_py_literal("NAKSHATRA_LORDS")
    assert list(NAKSHATRA_LORDS) == list(oracle)


def test_lord_cycle_is_nine_repeated_three_times():
    assert VIMSHOTTARI_LORD_CYCLE == (
        "Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn",
        "Mercury")
    assert len(NAKSHATRA_LORDS) == 27
    first, second, third = (NAKSHATRA_LORDS[0:9], NAKSHATRA_LORDS[9:18],
                            NAKSHATRA_LORDS[18:27])
    assert first == second == third == VIMSHOTTARI_LORD_CYCLE


def test_span_constants_are_exact_rationals_not_rounded():
    # NAK-AST-003 / NAK-AST-004: 40/3 and 10/3, not 13.3333 and 3.3333.
    assert NAKSHATRA_SPAN == Fraction(40, 3)
    assert PADA_SPAN == Fraction(10, 3)
    assert NAKSHATRA_SPAN * NAKSHATRA_COUNT == Fraction(360)
    assert PADA_SPAN * PADA_COUNT == Fraction(360)


# ── 3, 4 · the partition ─────────────────────────────────────────────────────

def test_every_nakshatra_holds_exactly_four_padas():
    seen = {}
    for cell in range(PADA_COUNT):
        _, at = _boundary_floats(PADA_SPAN * cell)
        index, _, pada, _ = placement_of(at)
        seen.setdefault(index, []).append(pada)
    assert sorted(seen) == list(range(27))
    for index, padas in seen.items():
        assert padas == [1, 2, 3, 4], f"nakshatra {index} padas were {padas}"


def test_all_108_cells_are_reachable_exactly_once():
    reached = set()
    for cell in range(PADA_COUNT):
        _, at = _boundary_floats(PADA_SPAN * cell)
        index, name, pada, lord = placement_of(at)
        # Expectation comes from the ordinal, not from the engine.
        assert index == cell // PADA_PER_NAKSHATRA
        assert pada == cell % PADA_PER_NAKSHATRA + 1
        assert name == NAKSHATRA_NAMES[index]
        assert lord == NAKSHATRA_LORDS[index]
        reached.add((index, pada))
    assert len(reached) == 108


# ── 5, 6, 7, 8 · boundaries ──────────────────────────────────────────────────

def test_nakshatra_boundaries_below_at_and_above():
    for k in range(1, NAKSHATRA_COUNT):
        below, at = _boundary_floats(NAKSHATRA_SPAN * k)
        assert placement_of(below)[0] == k - 1, f"below boundary {k}"
        assert placement_of(below)[2] == 4, "the cell before a boundary is pada 4"
        # Exact boundary belongs to the LATER nakshatra.
        assert placement_of(at)[0] == k, f"at boundary {k}"
        assert placement_of(at)[2] == 1, "a nakshatra opens on pada 1"
        above = math.nextafter(at, math.inf)
        assert placement_of(above)[0] == k


def test_pada_boundaries_below_at_and_above():
    for cell in range(1, PADA_COUNT):
        below, at = _boundary_floats(PADA_SPAN * cell)
        prev_index, _, prev_pada, _ = placement_of(below)
        assert (prev_index, prev_pada) == ((cell - 1) // 4, (cell - 1) % 4 + 1)
        index, _, pada, _ = placement_of(at)
        assert (index, pada) == (cell // 4, cell % 4 + 1)
        above_index, _, above_pada, _ = placement_of(math.nextafter(at, math.inf))
        assert (above_index, above_pada) == (index, pada)


def test_zero_degrees_is_ashwini_pada_one():
    index, name, pada, lord = placement_of(0.0)
    assert (index, name, pada, lord) == (0, "Ashwini", 1, "Ketu")


def test_just_below_360_is_revati_pada_four():
    index, name, pada, lord = placement_of(math.nextafter(360.0, 0.0))
    assert (index, name, pada, lord) == (26, "Revati", 4, "Mercury")


# ── 9 · domain refusals ──────────────────────────────────────────────────────

@pytest.mark.parametrize("value", [
    360.0, 360, 400.0, -0.0000001, -1.0, -360.0,
    float("nan"), float("inf"), float("-inf"),
    None, True, False, "18.876", "", [18.876], {"deg": 18.876}, object(),
])
def test_360_and_invalid_longitudes_are_rejected(value):
    with pytest.raises(NakshatraContractError):
        placement_of(value)


def test_out_of_domain_longitude_is_never_wrapped():
    # 360 + 18.876 would be Bharani pada 2 under a % 360 normalisation.
    with pytest.raises(NakshatraContractError):
        placement_of(378.876)


# ── 10, 11, 12, 13 · fail closed on missing data ─────────────────────────────

def _mutate(chart, path, value=..., delete=False):
    """Deep-copy the chart and change or delete one field."""
    out = json.loads(json.dumps(chart))
    node = out
    for key in path[:-1]:
        node = node[key]
    if delete:
        node.pop(path[-1], None)
    else:
        node[path[-1]] = value
    return out


def test_missing_moon_longitude_is_rejected(chart_of_record):
    broken = _mutate(chart_of_record, ["planets", "Moon", "longitude"], delete=True)
    with pytest.raises(NakshatraEngineError):
        build_nakshatra_payload(broken, "tok-abcdefgh", ROUTE_VERSION)


def test_missing_moon_block_is_rejected(chart_of_record):
    broken = _mutate(chart_of_record, ["planets", "Moon"], delete=True)
    with pytest.raises(NakshatraEngineError):
        build_nakshatra_payload(broken, "tok-abcdefgh", ROUTE_VERSION)


def test_missing_lagna_longitude_inputs_are_rejected(chart_of_record):
    # No longitude AND no usable sign_index/degree to rearrange it from.
    broken = _mutate(chart_of_record, ["lagna", "longitude"], delete=True)
    broken = _mutate(broken, ["lagna", "sign_index"], delete=True)
    with pytest.raises(NakshatraEngineError):
        build_nakshatra_payload(broken, "tok-abcdefgh", ROUTE_VERSION)

    broken = _mutate(chart_of_record, ["lagna", "longitude"], delete=True)
    broken = _mutate(broken, ["lagna", "degree"], delete=True)
    with pytest.raises(NakshatraEngineError):
        build_nakshatra_payload(broken, "tok-abcdefgh", ROUTE_VERSION)

    broken = _mutate(chart_of_record, ["lagna"], delete=True)
    with pytest.raises(NakshatraEngineError):
        build_nakshatra_payload(broken, "tok-abcdefgh", ROUTE_VERSION)


def test_lagna_longitude_may_be_rearranged_from_certified_sign_and_degree(chart_of_record):
    """The documented fallback, and it must reproduce the published longitude."""
    without = _mutate(chart_of_record, ["lagna", "longitude"], delete=True)
    payload = build_nakshatra_payload(without, "tok-abcdefgh", ROUTE_VERSION)
    assert payload.lagna.longitude == pytest.approx(
        chart_of_record["lagna"]["longitude"], abs=1e-9)
    assert payload.lagna.nakshatra == "Vishakha" and payload.lagna.pada == 1


@pytest.mark.parametrize("graha", [g.value for g in Graha])
def test_missing_graha_longitude_is_rejected(chart_of_record, graha):
    broken = _mutate(chart_of_record, ["planets", graha, "longitude"], delete=True)
    with pytest.raises(NakshatraEngineError):
        build_nakshatra_payload(broken, "tok-abcdefgh", ROUTE_VERSION)


@pytest.mark.parametrize("bad", [None, "0", True, [], {}, float("nan")])
def test_malformed_graha_longitude_is_rejected(chart_of_record, bad):
    broken = _mutate(chart_of_record, ["planets", "Mars", "longitude"], bad)
    with pytest.raises(NakshatraEngineError):
        build_nakshatra_payload(broken, "tok-abcdefgh", ROUTE_VERSION)


def test_non_object_graha_block_is_rejected(chart_of_record):
    broken = _mutate(chart_of_record, ["planets", "Venus"], "Pushya")
    with pytest.raises(NakshatraEngineError):
        build_nakshatra_payload(broken, "tok-abcdefgh", ROUTE_VERSION)


def test_no_missing_value_becomes_ashwini_pada_one(chart_of_record):
    """The named defect, asserted directly: every way of removing a longitude
    raises, and none of them yields a payload placed at 0 degrees."""
    removals = [["lagna", "longitude"], ["planets", "Moon", "longitude"]]
    removals += [["planets", g.value, "longitude"] for g in Graha]
    for path in removals:
        broken = _mutate(chart_of_record, path, delete=True)
        if path[:2] == ["lagna", "longitude"]:
            broken = _mutate(broken, ["lagna", "sign_index"], delete=True)
        with pytest.raises(NakshatraEngineError) as exc:
            payload = build_nakshatra_payload(broken, "tok-abcdefgh", ROUTE_VERSION)
            pytest.fail(f"{path} produced a payload instead of failing: {payload}")
        assert "Ashwini" not in str(exc.value)


# ── 14 · the chart of record ─────────────────────────────────────────────────

FOUNDER_EXPECTED = {
    "Sun": ("Pushya", 1, "Saturn"),
    "Moon": ("Bharani", 2, "Venus"),
    "Mars": ("Vishakha", 2, "Jupiter"),
    "Mercury": ("Magha", 1, "Ketu"),
    "Jupiter": ("Mula", 4, "Ketu"),
    "Venus": ("Pushya", 4, "Saturn"),
    "Saturn": ("Swati", 3, "Rahu"),
    "Rahu": ("Rohini", 1, "Moon"),
    "Ketu": ("Anuradha", 3, "Saturn"),
}


def test_founder_chart_placements_match_the_golden_astronomy(chart_of_record):
    payload = build_nakshatra_payload(chart_of_record, "tok-abcdefgh", ROUTE_VERSION)
    got = {p.subject.value: (p.nakshatra, p.pada, p.nakshatra_lord)
           for p in payload.grahas}
    assert got == FOUNDER_EXPECTED
    for placement in payload.grahas:
        published = chart_of_record["planets"][placement.subject.value]["longitude"]
        assert placement.longitude == published, "longitude is carried, not adjusted"


def test_founder_lagna_placement(chart_of_record):
    payload = build_nakshatra_payload(chart_of_record, "tok-abcdefgh", ROUTE_VERSION)
    assert payload.lagna.subject is NakshatraSubject.LAGNA
    assert (payload.lagna.nakshatra, payload.lagna.pada,
            payload.lagna.nakshatra_lord) == ("Vishakha", 1, "Jupiter")
    assert payload.lagna.longitude == chart_of_record["lagna"]["longitude"]


def test_janma_agrees_with_the_vimshottari_seed(chart_of_record):
    """Three independent witnesses to one Moon: the planet block's published
    nakshatra, the dasha seed, and this module's derivation from longitude."""
    payload = build_nakshatra_payload(chart_of_record, "tok-abcdefgh", ROUTE_VERSION)
    assert payload.janma.nakshatra == chart_of_record["dasha"]["moon_nakshatra"]
    assert payload.janma.nakshatra_lord == chart_of_record["dasha"]["moon_nakshatra_lord"]
    assert payload.janma.nakshatra == chart_of_record["planets"]["Moon"]["nakshatra"]


def test_janma_disagreeing_with_the_dasha_seed_is_rejected(chart_of_record):
    broken = _mutate(chart_of_record, ["dasha", "moon_nakshatra"], "Ashwini")
    with pytest.raises(NakshatraEngineError):
        build_nakshatra_payload(broken, "tok-abcdefgh", ROUTE_VERSION)


def test_mean_node_axis_is_carried_unchanged(chart_of_record):
    payload = build_nakshatra_payload(chart_of_record, "tok-abcdefgh", ROUTE_VERSION)
    by = {p.subject.value: p for p in payload.grahas}
    assert abs(by["Ketu"].longitude - by["Rahu"].longitude) == pytest.approx(180.0, abs=1e-9)


def test_calculation_meta_is_passed_through_not_recomputed(chart_of_record):
    payload = build_nakshatra_payload(chart_of_record, "tok-abcdefgh", ROUTE_VERSION)
    assert payload.calculation_meta == chart_of_record["calculation_meta"]


def test_uncertified_chart_provenance_is_refused(chart_of_record):
    broken = _mutate(chart_of_record, ["calculation_meta", "ephemeris_backend"], "moshier")
    with pytest.raises(NakshatraEngineError):
        build_nakshatra_payload(broken, "tok-abcdefgh", ROUTE_VERSION)


# ── 15, 16 · cardinality and identity ────────────────────────────────────────

def test_all_nine_grahas_returned_exactly_once(chart_of_record):
    payload = build_nakshatra_payload(chart_of_record, "tok-abcdefgh", ROUTE_VERSION)
    subjects = [p.subject.value for p in payload.grahas]
    assert subjects == [g.value for g in Graha]
    assert len(set(subjects)) == 9


def test_janma_is_exactly_the_moon_placement(chart_of_record):
    payload = build_nakshatra_payload(chart_of_record, "tok-abcdefgh", ROUTE_VERSION)
    moon = next(p for p in payload.grahas if p.subject is NakshatraSubject.MOON)
    assert payload.janma.dict() == moon.dict()
    assert payload.janma.subject is NakshatraSubject.MOON


def test_janma_that_disagrees_with_the_moon_is_rejected(chart_of_record):
    payload = build_nakshatra_payload(chart_of_record, "tok-abcdefgh", ROUTE_VERSION)
    fields = payload.dict()
    fields["janma"] = placement_for(NakshatraSubject.MOON, 0.0).dict()
    with pytest.raises(Exception):
        NakshatraPrepareResponse(**fields)


def test_lagna_block_cannot_carry_a_graha_subject(chart_of_record):
    payload = build_nakshatra_payload(chart_of_record, "tok-abcdefgh", ROUTE_VERSION)
    fields = payload.dict()
    fields["lagna"] = placement_for(NakshatraSubject.SUN, 10.0).dict()
    with pytest.raises(Exception):
        NakshatraPrepareResponse(**fields)


def test_graha_list_out_of_canonical_order_is_rejected(chart_of_record):
    payload = build_nakshatra_payload(chart_of_record, "tok-abcdefgh", ROUTE_VERSION)
    fields = payload.dict()
    fields["grahas"] = list(reversed(fields["grahas"]))
    with pytest.raises(Exception):
        NakshatraPrepareResponse(**fields)


# ── 17 · contradiction is refused, in both directions ────────────────────────

def test_published_nakshatra_mismatch_is_rejected(chart_of_record):
    broken = _mutate(chart_of_record, ["planets", "Saturn", "nakshatra"], "Chitra")
    with pytest.raises(NakshatraEngineError) as exc:
        build_nakshatra_payload(broken, "tok-abcdefgh", ROUTE_VERSION)
    assert "Saturn" in str(exc.value)


def test_published_pada_mismatch_is_rejected(chart_of_record):
    broken = _mutate(chart_of_record, ["planets", "Jupiter", "nakshatra_pada"], 2)
    with pytest.raises(NakshatraEngineError):
        build_nakshatra_payload(broken, "tok-abcdefgh", ROUTE_VERSION)


def test_published_lord_mismatch_is_rejected(chart_of_record):
    broken = _mutate(chart_of_record, ["planets", "Rahu", "nakshatra_lord"], "Saturn")
    with pytest.raises(NakshatraEngineError):
        build_nakshatra_payload(broken, "tok-abcdefgh", ROUTE_VERSION)


@pytest.mark.parametrize("field", ["nakshatra", "nakshatra_pada", "nakshatra_lord"])
def test_absent_published_placement_field_is_rejected(chart_of_record, field):
    broken = _mutate(chart_of_record, ["planets", "Mercury", field], delete=True)
    with pytest.raises(NakshatraEngineError):
        build_nakshatra_payload(broken, "tok-abcdefgh", ROUTE_VERSION)


@pytest.mark.parametrize("field,value", [
    ("nakshatra", "Ashwini"), ("nakshatra_index", 0), ("pada", 3),
    ("nakshatra_lord", "Mars"),
])
def test_placement_contradicting_its_own_longitude_is_rejected(field, value):
    good = placement_for(NakshatraSubject.MOON, 18.8760).dict()
    good[field] = value
    with pytest.raises(Exception):
        NakshatraPlacement(**good)


@pytest.mark.parametrize("field,value", [
    ("nakshatra_index", -1), ("nakshatra_index", 27), ("pada", 0), ("pada", 5),
    ("pada", "2"), ("pada", 2.0), ("pada", True), ("nakshatra_index", "1"),
])
def test_typed_field_constraints(field, value):
    good = placement_for(NakshatraSubject.MOON, 18.8760).dict()
    good[field] = value
    with pytest.raises(Exception):
        NakshatraPlacement(**good)


def test_placement_rejects_unknown_fields():
    good = placement_for(NakshatraSubject.MOON, 18.8760).dict()
    good["strength"] = 4
    with pytest.raises(Exception):
        NakshatraPlacement(**good)


# ── 18, 19, 20, 21, 22 · the route ───────────────────────────────────────────

def test_valid_request_returns_the_payload(chart_of_record):
    client = make_client(StubResolver(body=chart_of_record))
    r = client.post("/nakshatra/prepare", json={"chart_token": "tok-abcdefgh"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["route_version"] == ROUTE_VERSION
    assert body["policy"]["partition"] == "27x4-equal-sidereal"
    assert body["policy"]["nakshatra_span_degrees"] == "40/3"
    assert body["policy"]["pada_span_degrees"] == "10/3"
    assert len(body["grahas"]) == 9


def test_response_token_is_the_requested_token(chart_of_record):
    client = make_client(StubResolver(body=chart_of_record))
    token = "tok-" + "a" * 40
    r = client.post("/nakshatra/prepare", json={"chart_token": token})
    assert r.status_code == 200, r.text
    assert r.json()["chart_token"] == token


@pytest.mark.parametrize("token", [12345678, 1.5, True, None, ["abcdefgh"],
                                   {"v": "abcdefgh"}])
def test_non_string_token_types_return_422(chart_of_record, token):
    resolver = StubResolver(body=chart_of_record)
    client = make_client(resolver)
    r = client.post("/nakshatra/prepare", json={"chart_token": token})
    assert r.status_code == 422
    assert resolver.calls == 0, "a malformed request must not reach the resolver"


@pytest.mark.parametrize("token", ["a" * 7, "a" * 257])
def test_token_length_bounds_return_422(chart_of_record, token):
    resolver = StubResolver(body=chart_of_record)
    client = make_client(resolver)
    r = client.post("/nakshatra/prepare", json={"chart_token": token})
    assert r.status_code == 422
    assert resolver.calls == 0


def test_token_length_bounds_accept_the_inclusive_edges(chart_of_record):
    client = make_client(StubResolver(body=chart_of_record))
    for token in ("a" * 8, "a" * 256):
        assert client.post("/nakshatra/prepare",
                           json={"chart_token": token}).status_code == 200


def test_unknown_request_field_returns_422(chart_of_record):
    resolver = StubResolver(body=chart_of_record)
    client = make_client(resolver)
    r = client.post("/nakshatra/prepare",
                    json={"chart_token": "tok-abcdefgh", "varga": "D9"})
    assert r.status_code == 422
    assert resolver.calls == 0


@pytest.mark.parametrize("extra", [
    {"longitude": 18.876}, {"nakshatra": "Bharani"}, {"pada": 2},
    {"planets": {}}, {"lagna": {}}, {"chart_tokn": "tok-abcdefgh"},
])
def test_raw_chart_facts_in_the_request_return_422(chart_of_record, extra):
    """The browser submits a token. Anything that looks like an astronomical
    claim is refused at the boundary rather than ignored."""
    resolver = StubResolver(body=chart_of_record)
    client = make_client(resolver)
    payload = {"chart_token": "tok-abcdefgh"}
    payload.update(extra)
    assert client.post("/nakshatra/prepare", json=payload).status_code == 422
    assert resolver.calls == 0


def test_unknown_token_returns_404(chart_of_record):
    client = make_client(StubResolver(raises=ChartNotFound("nope")))
    r = client.post("/nakshatra/prepare", json={"chart_token": "tok-abcdefgh"})
    assert r.status_code == 404
    assert r.json()["detail"] == "Unknown or expired chart_token."


def test_unknown_expired_and_cross_owner_are_indistinguishable():
    details = set()
    for reason in ("unknown", "expired", "owned by someone else"):
        client = make_client(StubResolver(raises=ChartNotFound(reason)))
        r = client.post("/nakshatra/prepare", json={"chart_token": "tok-abcdefgh"})
        assert r.status_code == 404
        details.add(r.json()["detail"])
    assert len(details) == 1, "the public detail must not vary by cause"


def test_unconfigured_resolver_returns_503():
    app = FastAPI()
    app.include_router(router)          # deliberately no dependency override
    client = TestClient(app)
    r = client.post("/nakshatra/prepare", json={"chart_token": "tok-abcdefgh"})
    assert r.status_code == 503


PUBLIC_422_DETAIL = re.compile(
    r"^Certified chart could not be placed\. Reference: ([0-9a-f]{6,32})$")

# NAK-001-CORR-01. Each row breaks the chart in one way and names a value that
# WILL appear in the engine's refusal message. The sentinels are deliberately
# unmistakable: if any of them reaches the wire, it can only have come from the
# chart. The real derived values are listed alongside, because the leak QA found
# was not only the sentinel side of a mismatch but the derived side too.
LEAK_CASES = [
    ("published nakshatra",
     ["planets", "Saturn", "nakshatra"], "ZZPUBLISHEDNAKZZ",
     ["ZZPUBLISHEDNAKZZ", "Saturn", "Swati", "Rahu"]),
    ("published pada",
     ["planets", "Jupiter", "nakshatra_pada"], 987654,
     ["987654", "Jupiter", "Mula", "Ketu"]),
    ("published lord",
     ["planets", "Venus", "nakshatra_lord"], "ZZPUBLISHEDLORDZZ",
     ["ZZPUBLISHEDLORDZZ", "Venus", "Pushya", "Saturn"]),
    ("out-of-domain longitude",
     ["planets", "Mars", "longitude"], 999.777,
     ["999.777", "Mars"]),
    ("missing longitude",
     ["planets", "Moon", "longitude"], None,
     ["Moon", "Bharani", "18.876"]),
    ("uncertified provenance",
     ["calculation_meta", "ephemeris_backend"], "ZZMOSHIERZZ",
     ["ZZMOSHIERZZ", "ephemeris_backend", "swisseph"]),
]

LEAK_TOKEN = "ZZCHARTTOKENSENTINELZZ"


@pytest.mark.parametrize("label,path,value,sentinels",
                         LEAK_CASES, ids=[c[0] for c in LEAK_CASES])
def test_422_detail_is_static_and_leaks_no_chart_contents(
        chart_of_record, caplog, label, path, value, sentinels):
    broken = _mutate(chart_of_record, path, delete=(value is None), value=value)
    client = make_client(StubResolver(body=broken))
    with caplog.at_level(logging.ERROR, logger="nakshatra_routes"):
        r = client.post("/nakshatra/prepare", json={"chart_token": LEAK_TOKEN})

    assert r.status_code == 422
    detail = r.json()["detail"]
    match = PUBLIC_422_DETAIL.match(detail)
    assert match, f"422 detail is not the static public shape: {detail!r}"

    # The whole response, not only the detail field, so a leak cannot hide in a
    # validation-error structure or an added key.
    wire = r.text
    for sentinel in sentinels + [LEAK_TOKEN]:
        assert sentinel not in wire, f"{label}: {sentinel!r} reached the caller"

    # The correction moves the detail to the log; it must not lose it. A silent
    # refusal is a different defect, not a fix for this one.
    logged = "\n".join(rec.getMessage() for rec in caplog.records)
    assert match.group(1) in logged, "the correlation reference is not in the log"
    assert any(s in logged for s in sentinels), (
        f"{label}: the internal refusal did not reach the log at all")


def test_422_detail_is_identical_across_different_refusals(chart_of_record):
    """Two different failures must not be distinguishable by their public text.
    Only the reference varies, and it varies per request."""
    details, references = set(), set()
    for _, path, value, _ in LEAK_CASES:
        broken = _mutate(chart_of_record, path, delete=(value is None), value=value)
        client = make_client(StubResolver(body=broken))
        r = client.post("/nakshatra/prepare", json={"chart_token": LEAK_TOKEN})
        assert r.status_code == 422
        match = PUBLIC_422_DETAIL.match(r.json()["detail"])
        assert match
        details.add(PUBLIC_422_DETAIL.sub("STATIC", r.json()["detail"]))
        references.add(match.group(1))
    assert len(details) == 1, "the public wording varies with the cause"
    assert len(references) == len(LEAK_CASES), "the reference is not per-request"


def test_valid_requests_are_unchanged_by_the_correction(chart_of_record):
    """The correction touches one exception handler. A 200 still carries the
    token, the placements and the certified metadata."""
    client = make_client(StubResolver(body=chart_of_record))
    r = client.post("/nakshatra/prepare", json={"chart_token": LEAK_TOKEN})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["chart_token"] == LEAK_TOKEN
    assert body["janma"]["nakshatra"] == "Bharani" and body["janma"]["pada"] == 2
    assert body["lagna"]["nakshatra"] == "Vishakha" and body["lagna"]["pada"] == 1
    assert len(body["grahas"]) == 9
    assert body["calculation_meta"] == chart_of_record["calculation_meta"]


def test_auth_statuses_are_preserved_and_upstream_detail_is_not():
    from fastapi import HTTPException
    for status in (401, 403):
        client = make_client(StubResolver(raises=HTTPException(status_code=status,
                                                               detail="denied")))
        r = client.post("/nakshatra/prepare", json={"chart_token": "tok-abcdefgh"})
        assert r.status_code == status

    leak = HTTPException(status_code=502, detail="Could not reach Supabase: db-int:5432")
    client = make_client(StubResolver(raises=leak))
    r = client.post("/nakshatra/prepare", json={"chart_token": "tok-abcdefgh"})
    assert r.status_code == 500
    assert "Supabase" not in r.text and "db-int" not in r.text
    assert "Reference:" in r.json()["detail"]


def test_unexpected_resolver_failure_is_generalised():
    client = make_client(StubResolver(raises=RuntimeError("boom /secret/path")))
    r = client.post("/nakshatra/prepare", json={"chart_token": "tok-abcdefgh"})
    assert r.status_code == 500
    assert "boom" not in r.text and "Reference:" in r.json()["detail"]


def test_repeated_preparation_is_deterministic(chart_of_record):
    client = make_client(StubResolver(body=chart_of_record))
    first = client.post("/nakshatra/prepare", json={"chart_token": "tok-abcdefgh"})
    second = client.post("/nakshatra/prepare", json={"chart_token": "tok-abcdefgh"})
    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()
    assert json.dumps(first.json(), sort_keys=True) == json.dumps(second.json(),
                                                                  sort_keys=True)


# ── 23, 24, 25 · publication surface ─────────────────────────────────────────

def _all_strings(node):
    if isinstance(node, str):
        yield node
    elif isinstance(node, dict):
        for key, value in node.items():
            yield key
            yield from _all_strings(value)
    elif isinstance(node, list):
        for item in node:
            yield from _all_strings(item)


def _all_keys(node):
    if isinstance(node, dict):
        for key, value in node.items():
            yield key
            yield from _all_keys(value)
    elif isinstance(node, list):
        for item in node:
            yield from _all_keys(item)


def test_response_contains_no_html(chart_of_record):
    client = make_client(StubResolver(body=chart_of_record))
    raw = client.post("/nakshatra/prepare", json={"chart_token": "tok-abcdefgh"}).text
    for marker in ("<", ">", "&lt;", "&#", "javascript:", "onerror", "style="):
        assert marker not in raw, f"payload carried {marker!r}"


def test_response_contains_no_prose(chart_of_record):
    """No corpus, no interpretation. Every published string is an identifier, a
    version, a name or a declared policy phrase, so none of them is a sentence."""
    client = make_client(StubResolver(body=chart_of_record))
    body = client.post("/nakshatra/prepare", json={"chart_token": "tok-abcdefgh"}).json()
    for text in _all_strings(body):
        assert ". " not in text, f"sentence-like string published: {text!r}"
        assert len(text) <= 64, f"prose-length string published: {text!r}"


BANNED_KEYS = {
    "score", "bar", "barpct", "strength", "strength_bar", "relationship",
    "friend", "enemy", "verdict", "effect", "text", "prose", "description",
    "personality", "remedy", "pushkara", "gandanta", "vargottama", "deity",
    "symbol", "gana", "swarupa", "interpretation", "corpus",
}


def test_response_contains_no_relationship_score_or_strength_fields(chart_of_record):
    client = make_client(StubResolver(body=chart_of_record))
    body = client.post("/nakshatra/prepare", json={"chart_token": "tok-abcdefgh"}).json()
    for key in _all_keys(body):
        assert key.lower() not in BANNED_KEYS, f"out-of-scope field published: {key!r}"


def test_response_publishes_exactly_the_contracted_top_level_keys(chart_of_record):
    client = make_client(StubResolver(body=chart_of_record))
    body = client.post("/nakshatra/prepare", json={"chart_token": "tok-abcdefgh"}).json()
    assert set(body) == {"route_version", "chart_token", "policy",
                         "calculation_meta", "lagna", "janma", "grahas"}
    for placement in [body["lagna"], body["janma"], *body["grahas"]]:
        assert set(placement) == {"subject", "longitude", "nakshatra_index",
                                  "nakshatra", "pada", "nakshatra_lord"}


# ── 26 · registration ────────────────────────────────────────────────────────

def test_route_is_registered_exactly_once_in_main():
    with open(MAIN_PY, "r", encoding="utf-8") as fh:
        tree = ast.parse(fh.read())

    imported = [n for n in ast.walk(tree)
                if isinstance(n, ast.ImportFrom) and n.module == "nakshatra_routes"]
    assert len(imported) == 1, "nakshatra_routes must be imported exactly once"
    aliases = [a.asname or a.name for a in imported[0].names]
    assert aliases == ["nakshatra_router"]

    registrations = [
        n for n in ast.walk(tree)
        if isinstance(n, ast.Call)
        and isinstance(n.func, ast.Attribute)
        and n.func.attr == "include_router"
        and any(isinstance(a, ast.Name) and a.id == "nakshatra_router" for a in n.args)
    ]
    assert len(registrations) == 1, (
        f"expected exactly one app.include_router(nakshatra_router), "
        f"found {len(registrations)}")
    # No prefix: the path is declared in full on the router.
    assert not registrations[0].keywords


def test_registered_path_is_the_contracted_one():
    paths = [r.path for r in router.routes]
    assert paths == ["/nakshatra/prepare"]
    assert [sorted(r.methods) for r in router.routes] == [["POST"]]
