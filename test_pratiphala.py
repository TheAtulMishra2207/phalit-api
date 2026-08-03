"""test_pratiphala.py — focused backend tests for the Pratiphala layer.

Every case in the spec, and each one asserts the SPECIFIC evidence rather than
merely that something failed. A test that passes for the wrong reason is worth
less than no test.
"""
import pytest
from pydantic import ValidationError

from d1_contract import Dignity, Graha
from pratiphala_contract import (
    DIGNITY_RANK, GoverningLabel, GrahaPratiphala, PratiphalaPrepareRequest,
    PratiphalaState,
    SOVEREIGN_SA, STRONG_AT, Strength, SubTier,
)
from pratiphala_routes import (
    PratiphalaError, build_pratiphala, house_lord_overlays, quadrant_of,
    rank_of, resolve, strength_of, sub_tier_of,
)

D = Dignity
ALL_SEVEN = [D.DEBILITATED, D.ENEMY, D.NEUTRAL, D.FRIEND, D.OWN,
             D.MOOLATRIKONA, D.EXALTED]


# ── the locked scale, every rank 0..6 ───────────────────────────────────────

@pytest.mark.parametrize("dignity,expected", list(zip(ALL_SEVEN, range(0, 7))))
def test_every_rank_0_through_6(dignity, expected):
    assert rank_of(dignity) == expected


def test_the_scale_covers_exactly_seven_positions():
    assert sorted(DIGNITY_RANK.values()) == [0, 1, 2, 3, 4, 5, 6]


# ── the boundary the whole verdict turns on ─────────────────────────────────

def test_friend_rank_3_is_strong_and_neutral_rank_2_is_weak():
    assert rank_of(D.FRIEND) == 3 and rank_of(D.NEUTRAL) == 2
    assert strength_of(3) is Strength.STRONG
    assert strength_of(2) is Strength.WEAK
    assert STRONG_AT == 3


# ── the four ordinary quadrants ─────────────────────────────────────────────

@pytest.mark.parametrize("d1,d9,expected", [
    (D.EXALTED,     D.FRIEND,   PratiphalaState.SIDDHA),      # strong x strong
    (D.EXALTED,     D.NEUTRAL,  PratiphalaState.VIPHALA),     # strong x weak
    (D.NEUTRAL,     D.EXALTED,  PratiphalaState.PRACHANNA),   # weak   x strong
    (D.DEBILITATED, D.ENEMY,    PratiphalaState.RIKT),        # weak   x weak
])
def test_all_four_quadrants(d1, d9, expected):
    assert quadrant_of(rank_of(d1), rank_of(d9)) is expected
    v = resolve(Graha.SUN, d1, d9)
    assert v.governing_state.value == expected.value
    assert v.evidence.underlying_state is expected


# ── UNKNOWN, and that it does not collapse ──────────────────────────────────

@pytest.mark.parametrize("node", [Graha.RAHU, Graha.KETU])
def test_node_with_no_d9_dignity_is_unknown(node):
    v = resolve(node, D.DEBILITATED, None)
    assert v.governing_state is GoverningLabel.UNKNOWN
    assert v.evidence.underlying_state is PratiphalaState.UNKNOWN
    # Weak x (absent) must NOT become Rikt.
    assert v.governing_state is not GoverningLabel.RIKT
    assert v.basis and "unknown" in v.basis.lower()


def test_unknown_carries_no_corpus_text_and_no_key():
    v = resolve(Graha.RAHU, D.EXALTED, None,
                corpus_lookup=lambda k: "prose that must never be attached")
    assert v.corpus.key is None
    assert v.corpus.text is None
    assert v.corpus.resolvable is False


def test_unknown_sub_tier_for_the_absent_side_only():
    v = resolve(Graha.KETU, D.EXALTED, None)
    assert v.d1_sub_tier is SubTier.UTTAMA
    assert v.d9_sub_tier is SubTier.UNKNOWN


# ── sovereign override ──────────────────────────────────────────────────────

def test_vargottama_overrides_siddha():
    v = resolve(Graha.MARS, D.EXALTED, D.EXALTED, is_vargottama=True)
    assert v.governing_state is GoverningLabel.SOVEREIGN
    assert v.governing_state_sa == SOVEREIGN_SA == "सार्वभौम"
    # the quadrant survives, but does not govern
    assert v.evidence.underlying_state is PratiphalaState.SIDDHA
    assert v.evidence.sovereign_override_applied is True


def test_vargottama_overrides_viphala():
    v = resolve(Graha.VENUS, D.EXALTED, D.NEUTRAL, is_vargottama=True)
    assert v.governing_state is GoverningLabel.SOVEREIGN
    assert v.evidence.underlying_state is PratiphalaState.VIPHALA


def test_is_vargottama_false_leaves_the_quadrant_governing():
    v = resolve(Graha.VENUS, D.EXALTED, D.NEUTRAL, is_vargottama=False)
    assert v.governing_state is GoverningLabel.VIPHALA
    assert v.evidence.sovereign_override_applied is False


# ── PF-001 · the precedence collision, which isolation testing missed ───────
# UNKNOWN and Sovereign were each covered above. Neither test could see what
# happens when BOTH conditions hold, and that gap is where the defect lived.

@pytest.mark.parametrize("node", [Graha.RAHU, Graha.KETU])
def test_absent_d9_outranks_vargottama(node):
    v = resolve(node, D.FRIEND, None, is_vargottama=True)
    assert v.governing_state is GoverningLabel.UNKNOWN
    assert v.governing_state is not GoverningLabel.SOVEREIGN
    assert v.evidence.underlying_state is PratiphalaState.UNKNOWN
    assert v.evidence.sovereign_override_applied is False
    assert v.corpus.key is None
    assert v.corpus.text is None
    assert v.corpus.resolvable is False
    # the input flag is still true; it simply did not govern
    assert v.is_vargottama is True
    assert "vargottama does not apply" in v.basis


def test_absent_d9_outranks_vargottama_at_every_d1_rank():
    """The precedence must not depend on how strong D1 is."""
    for dignity in ALL_SEVEN:
        v = resolve(Graha.RAHU, dignity, None, is_vargottama=True)
        assert v.governing_state is GoverningLabel.UNKNOWN, dignity


def test_model_rejects_sovereign_with_absent_d9_dignity():
    """Constructed directly, bypassing the resolver entirely.

    PF-007 moved this to a NODE: a classical graha with no dignity is now
    refused earlier and for a different reason, so Mars could no longer reach
    the Sovereign check at all. Both refusals are asserted.
    """
    good = resolve(Graha.RAHU, D.EXALTED, D.EXALTED, is_vargottama=True)
    payload = good.dict()
    payload["d9_dignity"] = None
    with pytest.raises(ValidationError) as e:
        GrahaPratiphala(**payload)
    # PF-006's recompute fires FIRST and is the stronger objection: the whole
    # derived reading contradicts the dignities, not merely the governing state.
    assert "contradicts its own dignities" in str(e.value)

    mars = resolve(Graha.MARS, D.EXALTED, D.EXALTED, is_vargottama=True).dict()
    mars["d9_dignity"] = None
    with pytest.raises(ValidationError) as e:
        GrahaPratiphala(**mars)
    assert "only Rahu and Ketu may lack one" in str(e.value)


def test_model_rejects_unknown_that_records_the_override():
    unknown = resolve(Graha.RAHU, D.FRIEND, None, is_vargottama=True)
    payload = unknown.dict()
    payload["evidence"]["sovereign_override_applied"] = True
    with pytest.raises(ValidationError):
        GrahaPratiphala(**payload)


def test_valid_sovereign_with_a_real_d9_dignity_still_passes():
    """The fix must not have closed the legitimate Sovereign path."""
    for d1, d9, quad in [(D.EXALTED, D.EXALTED, PratiphalaState.SIDDHA),
                         (D.EXALTED, D.NEUTRAL, PratiphalaState.VIPHALA),
                         (D.NEUTRAL, D.EXALTED, PratiphalaState.PRACHANNA),
                         (D.DEBILITATED, D.ENEMY, PratiphalaState.RIKT)]:
        v = resolve(Graha.VENUS, d1, d9, is_vargottama=True)
        assert v.governing_state is GoverningLabel.SOVEREIGN
        assert v.governing_state_sa == SOVEREIGN_SA
        assert v.evidence.underlying_state is quad
        assert v.evidence.sovereign_override_applied is True


def test_full_response_with_a_vargottama_node():
    """The end-to-end path, with the collision present in a real payload."""
    d1 = {g: D.FRIEND for g in Graha}
    d9 = {g: D.FRIEND for g in Graha}
    d9[Graha.RAHU] = None
    d9[Graha.KETU] = None
    vg = {g: False for g in Graha}
    vg[Graha.RAHU] = True          # vargottama AND no D9 dignity
    vg[Graha.MARS] = True          # vargottama with a real D9 dignity
    r = build_pratiphala("tok" + "x" * 9, d1, d9, vg, 6)
    by = {g.graha: g for g in r.grahas}
    assert by[Graha.RAHU].governing_state is GoverningLabel.UNKNOWN
    assert by[Graha.MARS].governing_state is GoverningLabel.SOVEREIGN


# ── every sub-tier boundary ─────────────────────────────────────────────────

@pytest.mark.parametrize("rank,expected", [
    (0, SubTier.WEAK), (1, SubTier.WEAK),
    (2, SubTier.ALPA),
    (3, SubTier.MADHYA), (4, SubTier.MADHYA),
    (5, SubTier.UTTAMA), (6, SubTier.UTTAMA),
    (None, SubTier.UNKNOWN),
])
def test_every_sub_tier_boundary(rank, expected):
    assert sub_tier_of(rank) is expected


# ── house-lord overlays, keyed by house ─────────────────────────────────────

def _verdicts():
    return {g: resolve(g, D.FRIEND, D.FRIEND) for g in Graha}


def test_libra_lagna_venus_produces_separate_h1_and_h8_overlays():
    LIBRA = 6
    overlays = house_lord_overlays(LIBRA, _verdicts())
    venus = [o for o in overlays if o.lord is Graha.VENUS]
    assert {o.house for o in venus} == {1, 8}
    assert {o.overlay_key for o in venus} == {"H1:Venus", "H8:Venus"}
    assert len({o.overlay_key for o in overlays}) == 12


def test_every_house_gets_exactly_one_overlay():
    overlays = house_lord_overlays(6, _verdicts())
    assert sorted(o.house for o in overlays) == list(range(1, 13))


# ── request strictness ──────────────────────────────────────────────────────

def test_valid_request():
    assert PratiphalaPrepareRequest(chart_token="a" * 12).chart_token == "a" * 12


def test_unknown_request_field_rejected():
    with pytest.raises(ValidationError) as e:
        PratiphalaPrepareRequest(chart_token="a" * 12, varga="D9")
    assert "varga" in str(e.value)


def test_misspelled_request_field_rejected():
    with pytest.raises(ValidationError) as e:
        PratiphalaPrepareRequest(chart_tokn="a" * 12)
    assert "chart_tokn" in str(e.value)


# ── unknown dignity ─────────────────────────────────────────────────────────

@pytest.mark.parametrize("unreachable", [D.GREAT_FRIEND, D.GREAT_ENEMY])
def test_dignity_outside_the_locked_scale_is_rejected(unreachable):
    with pytest.raises(PratiphalaError) as e:
        rank_of(unreachable)
    assert "locked Pratiphala scale" in str(e.value)


def test_a_non_dignity_value_is_rejected():
    with pytest.raises(PratiphalaError):
        rank_of("Slightly Friendly")


# ── whole response ──────────────────────────────────────────────────────────

def test_full_response_builds_and_validates():
    d1 = {g: D.FRIEND for g in Graha}
    d9 = {g: D.FRIEND for g in Graha}
    d9[Graha.RAHU] = None
    d9[Graha.KETU] = None
    vg = {g: False for g in Graha}
    vg[Graha.MARS] = True
    r = build_pratiphala("tok" + "x" * 9, d1, d9, vg, 6)
    assert len(r.grahas) == 9 and len(r.house_lord_overlays) == 12
    by = {g.graha: g for g in r.grahas}
    assert by[Graha.RAHU].governing_state is GoverningLabel.UNKNOWN
    assert by[Graha.KETU].governing_state is GoverningLabel.UNKNOWN
    assert by[Graha.MARS].governing_state is GoverningLabel.SOVEREIGN
    assert by[Graha.SUN].governing_state is GoverningLabel.SIDDHA


def test_ranks_are_quarantined_from_display_fields():
    v = resolve(Graha.SUN, D.EXALTED, D.FRIEND)
    display = v.dict(exclude={"evidence"})
    assert "d1_rank" not in display and "d9_rank" not in display
    assert v.evidence.d1_rank == 6 and v.evidence.d9_rank == 3


# ── Step 2 · resolver wiring ────────────────────────────────────────────────
# These test the WIRING, not the doctrine. Everything below the resolver is
# stubbed so a failure here can only mean the route is joined up wrongly.

import asyncio
import inspect as _inspect
import pathlib

import pratiphala_routes as PR
from fastapi import HTTPException
from d1_routes import ChartNotFound


class _Recorder:
    """A resolver that counts calls and remembers what it was asked for."""
    def __init__(self, result=None, raises=None):
        self.calls, self.tokens = 0, []
        self._result, self._raises = result, raises

    async def resolve(self, chart_token):
        self.calls += 1
        self.tokens.append(chart_token)
        if self._raises is not None:
            raise self._raises
        return self._result


def _stub_pipeline(monkeypatch, seen=None):
    """Stub everything past the resolver. `seen` collects what each stage got."""
    seen = seen if seen is not None else {}
    sentinel_chart = object()
    monkeypatch.setattr(PR, "to_certified_chart",
                        lambda body, token, varga=None: seen.setdefault("body", body) and None
                        or seen.__setitem__("token", token) or sentinel_chart)
    monkeypatch.setattr(PR, "_from_certified",
                        lambda chart: (seen.__setitem__("chart", chart) or
                                       ({g: D.FRIEND for g in Graha},
                                        {g: D.FRIEND for g in Graha},
                                        {g: False for g in Graha}, 6)))
    seen["sentinel"] = sentinel_chart
    return seen


def _run(coro):
    # new_event_loop, not get_event_loop: the latter is deprecated outside a
    # running loop and emits a warning on 3.11/3.12.
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


TOKEN = "chart-token-abcdef"


def test_valid_resolver_result_reaches_build_pratiphala(monkeypatch):
    seen = _stub_pipeline(monkeypatch)
    body = {"certified": "body"}
    r = _run(PR.pratiphala_prepare(PratiphalaPrepareRequest(chart_token=TOKEN),
                                   _Recorder(result=body)))
    assert seen["body"] is body                       # the resolver's object, unaltered
    assert len(r.grahas) == 9 and len(r.house_lord_overlays) == 12
    assert r.chart_token == TOKEN


def test_resolver_receives_the_exact_request_token(monkeypatch):
    _stub_pipeline(monkeypatch)
    rec = _Recorder(result={"x": 1})
    _run(PR.pratiphala_prepare(PratiphalaPrepareRequest(chart_token=TOKEN), rec))
    assert rec.tokens == [TOKEN]


def test_unknown_token_returns_404(monkeypatch):
    _stub_pipeline(monkeypatch)
    with pytest.raises(HTTPException) as e:
        _run(PR.pratiphala_prepare(PratiphalaPrepareRequest(chart_token=TOKEN),
                                   _Recorder(raises=ChartNotFound())))
    assert e.value.status_code == 404


@pytest.mark.parametrize("raised,expected", [
    (HTTPException(status_code=401, detail="no"), 401),   # auth survives
    (HTTPException(status_code=403, detail="no"), 403),   # auth survives
    (HTTPException(status_code=502, detail="Supabase host:5432 timed out"), 500),
    (RuntimeError("boom"), 500),
])
def test_resolver_failure_follows_the_d1_status_mapping(monkeypatch, raised, expected):
    _stub_pipeline(monkeypatch)
    with pytest.raises(HTTPException) as e:
        _run(PR.pratiphala_prepare(PratiphalaPrepareRequest(chart_token=TOKEN),
                                   _Recorder(raises=raised)))
    assert e.value.status_code == expected
    if expected == 500:
        # upstream text must not leak; only a correlation reference survives
        assert "Supabase" not in str(e.value.detail)
        assert "Reference:" in str(e.value.detail)


def test_resolver_is_called_exactly_once(monkeypatch):
    _stub_pipeline(monkeypatch)
    rec = _Recorder(result={"x": 1})
    _run(PR.pratiphala_prepare(PratiphalaPrepareRequest(chart_token=TOKEN), rec))
    assert rec.calls == 1


def test_d1_and_d9_come_from_the_same_resolved_snapshot(monkeypatch):
    """_from_certified must hand ONE chart object to both compute_d1 calls."""
    charts, vargas = [], []

    class _Resp:
        grahas = [type("G", (), {"graha": g, "dignity": D.FRIEND,
                                 "vargottama": False})() for g in Graha]
        lagna_sign_index = 6

    monkeypatch.setattr(PR, "compute_d1",
                        lambda chart, varga: (charts.append(chart), vargas.append(varga),
                                              (_Resp(), None))[-1])
    sentinel = object()
    monkeypatch.setattr(PR, "to_certified_chart", lambda b, t, varga=None: sentinel)
    _run(PR.pratiphala_prepare(PratiphalaPrepareRequest(chart_token=TOKEN),
                               _Recorder(result={"x": 1})))
    assert len(charts) == 2                     # D1 and D9
    assert charts[0] is charts[1] is sentinel   # ONE snapshot, two views
    assert {v.value for v in vargas} == {"D1", "D9"}


def test_no_load_snapshot_or_local_token_store_remains():
    src = pathlib.Path(PR.__file__).read_text()
    assert "_load_snapshot" not in src
    assert not hasattr(PR, "_load_snapshot")
    # No module-level dict standing in for a store. Constants IMPORTED from the
    # contract (DIGNITY_RANK, STATE_SA) are the same objects there and are not
    # candidates; a dict defined locally in the route module would be.
    import pratiphala_contract as PC
    imported = {id(v) for v in vars(PC).values() if isinstance(v, dict)}
    stores = [n for n, v in vars(PR).items()
              if isinstance(v, dict) and not n.startswith("__") and id(v) not in imported]
    assert stores == [], f"module-level dict(s) defined here that could act as a token store: {stores}"
    assert "Depends(get_chart_resolver)" in src


# ── Step 3 · application registration ───────────────────────────────────────
# main.py cannot be IMPORTED in this container: it needs swisseph and the
# Supabase layer. So registration is checked two ways that together are
# stronger than importing it would be —
#   (a) the exact registration lines are asserted against main.py's SOURCE, and
#   (b) an app assembled the SAME way is exercised over real HTTP.
# Neither alone would do: (a) proves main.py says it, (b) proves saying it
# produces the right route.

import re as _re
from fastapi import FastAPI
from fastapi.testclient import TestClient
from d1_routes import get_chart_resolver, router as d1_router
from pratiphala_contract import PratiphalaPrepareResponse

MAIN = pathlib.Path(__file__).with_name("main.py")


def _app():
    """Assembled exactly as main.py assembles it: both routers, no prefix."""
    app = FastAPI(title="Phalit.ai Chart Engine", version="1.0.0")
    app.include_router(d1_router)
    app.include_router(PR.router)
    return app


def _posts(app, path):
    return [r for r in app.routes
            if getattr(r, "path", None) == path and "POST" in getattr(r, "methods", set())]


def test_main_registers_the_router_exactly_once_without_a_prefix():
    src = MAIN.read_text()
    assert "from pratiphala_routes import router as pratiphala_router" in src
    assert len(_re.findall(r"app\.include_router\(pratiphala_router\)", src)) == 1
    # a prefix here would produce /pratiphala/pratiphala/prepare
    assert not _re.search(r"include_router\(pratiphala_router,[^)]*prefix", src)


def test_app_exposes_exactly_one_post_pratiphala_prepare():
    assert len(_posts(_app(), "/pratiphala/prepare")) == 1


def test_no_doubled_prefix_route_exists():
    app = _app()
    assert _posts(app, "/pratiphala/pratiphala/prepare") == []
    doubled = [r for r in app.routes
               if "pratiphala/pratiphala" in getattr(r, "path", "")]
    assert doubled == []


def test_registered_route_uses_the_pratiphala_response_model():
    route = _posts(_app(), "/pratiphala/prepare")[0]
    assert route.response_model is PratiphalaPrepareResponse


def test_existing_d1_prepare_remains_registered():
    assert len(_posts(_app(), "/d1/prepare")) == 1


def test_unknown_extra_request_field_returns_422_through_the_app():
    # The resolver override is bound, because that is the PRODUCTION state:
    # install_d1 binds it at startup. Without it the unconfigured-resolver 503
    # fires during dependency resolution and masks the body validation — which
    # is correct behaviour for an unconfigured app, and not what this asserts.
    app = _app()
    app.dependency_overrides[get_chart_resolver] = lambda: _Recorder(result={"x": 1})
    with TestClient(app) as c:
        r = c.post("/pratiphala/prepare",
                   json={"chart_token": TOKEN, "varga": "D9"})
    assert r.status_code == 422
    assert "varga" in r.text


def test_an_unconfigured_resolver_still_fails_loudly_with_503():
    """The deliberate default from d1_routes survives registration."""
    with TestClient(_app()) as c:
        r = c.post("/pratiphala/prepare", json={"chart_token": TOKEN})
    assert r.status_code == 503


def test_dependency_override_reaches_the_registered_endpoint(monkeypatch):
    """The override is keyed on the SHARED get_chart_resolver, so binding it
    once — as install_d1 does — reaches this route too."""
    _stub_pipeline(monkeypatch)
    rec = _Recorder(result={"certified": "body"})
    app = _app()
    app.dependency_overrides[get_chart_resolver] = lambda: rec
    with TestClient(app) as c:
        r = c.post("/pratiphala/prepare", json={"chart_token": TOKEN})
    assert r.status_code == 200
    assert rec.calls == 1 and rec.tokens == [TOKEN]
    assert len(r.json()["grahas"]) == 9


def test_unknown_chart_token_returns_404_through_the_app():
    app = _app()
    app.dependency_overrides[get_chart_resolver] = lambda: _Recorder(raises=ChartNotFound())
    with TestClient(app) as c:
        r = c.post("/pratiphala/prepare", json={"chart_token": TOKEN})
    assert r.status_code == 404


# ── PF-002 · corpus resolution must reflect actual text ─────────────────────

from pratiphala_contract import CorpusRef

PROSE = "The promise ripens; effort and result stay in step."


def test_lookup_returns_none_key_retained_text_none_not_resolvable():
    v = resolve(Graha.SUN, D.EXALTED, D.FRIEND, corpus_lookup=lambda k: None)
    assert v.corpus.key == "PRATIPHALA-Sun-Siddha"
    assert v.corpus.text is None
    assert v.corpus.resolvable is False


def test_lookup_returns_prose_key_and_prose_retained_and_resolvable():
    v = resolve(Graha.SUN, D.EXALTED, D.FRIEND, corpus_lookup=lambda k: PROSE)
    assert v.corpus.key == "PRATIPHALA-Sun-Siddha"
    assert v.corpus.text == PROSE
    assert v.corpus.resolvable is True


def test_no_lookup_supplied_is_not_resolvable():
    """The production default today: _corpus_lookup returns None."""
    v = resolve(Graha.SUN, D.EXALTED, D.FRIEND)
    assert v.corpus.key and v.corpus.text is None and v.corpus.resolvable is False


def test_unknown_keeps_all_three_empty():
    v = resolve(Graha.RAHU, D.FRIEND, None, corpus_lookup=lambda k: PROSE)
    assert v.corpus.key is None
    assert v.corpus.text is None
    assert v.corpus.resolvable is False


def test_unknown_never_calls_the_lookup():
    calls = []
    resolve(Graha.KETU, D.EXALTED, None, corpus_lookup=lambda k: calls.append(k) or PROSE)
    assert calls == []


def test_model_rejects_resolvable_true_without_text():
    with pytest.raises(ValidationError) as e:
        CorpusRef(key="PRATIPHALA-Sun-Siddha", text=None, resolvable=True)
    assert "non-empty text" in str(e.value)


def test_model_rejects_resolvable_true_with_blank_text():
    with pytest.raises(ValidationError):
        CorpusRef(key="PRATIPHALA-Sun-Siddha", text="   ", resolvable=True)


def test_model_rejects_text_without_a_key():
    with pytest.raises(ValidationError) as e:
        CorpusRef(key=None, text=PROSE, resolvable=True)
    assert "without a key" in str(e.value)


def test_model_rejects_text_while_not_resolvable():
    with pytest.raises(ValidationError) as e:
        CorpusRef(key="PRATIPHALA-Sun-Siddha", text=PROSE, resolvable=False)
    assert "contradicts the payload" in str(e.value)


def test_the_three_legal_states_all_construct():
    assert CorpusRef(key="K", text=PROSE, resolvable=True).resolvable is True
    assert CorpusRef(key="K", text=None, resolvable=False).resolvable is False
    assert CorpusRef(key=None, text=None, resolvable=False).key is None


@pytest.mark.parametrize("d1,d9,vg,expect_key", [
    (D.EXALTED,     D.FRIEND,  False, "PRATIPHALA-Venus-Siddha"),
    (D.EXALTED,     D.NEUTRAL, False, "PRATIPHALA-Venus-Viphala"),
    (D.NEUTRAL,     D.EXALTED, False, "PRATIPHALA-Venus-Prachanna"),
    (D.DEBILITATED, D.ENEMY,   False, "PRATIPHALA-Venus-Rikt"),
    (D.EXALTED,     D.FRIEND,  True,  "PRATIPHALA-Venus-Sovereign"),
])
def test_every_governing_state_follows_the_same_resolution_semantics(d1, d9, vg, expect_key):
    dry = resolve(Graha.VENUS, d1, d9, is_vargottama=vg, corpus_lookup=lambda k: None)
    assert dry.corpus.key == expect_key
    assert dry.corpus.text is None and dry.corpus.resolvable is False
    wet = resolve(Graha.VENUS, d1, d9, is_vargottama=vg, corpus_lookup=lambda k: PROSE)
    assert wet.corpus.key == expect_key
    assert wet.corpus.text == PROSE and wet.corpus.resolvable is True


# ── PF-003 · exactly three CorpusRef states, no blank-but-present fourth ────

@pytest.mark.parametrize("returned", ["", "   ", "\n\t "])
def test_blank_lookup_normalises_to_absent(returned):
    v = resolve(Graha.SUN, D.EXALTED, D.FRIEND, corpus_lookup=lambda k: returned)
    assert v.corpus.key == "PRATIPHALA-Sun-Siddha"
    assert v.corpus.text is None
    assert v.corpus.resolvable is False


def test_prose_is_trimmed_and_retained():
    v = resolve(Graha.SUN, D.EXALTED, D.FRIEND,
                corpus_lookup=lambda k: "  " + PROSE + "\n")
    assert v.corpus.text == PROSE          # trimmed, not merely accepted
    assert v.corpus.resolvable is True


@pytest.mark.parametrize("blank", ["", "   ", "\t", "\n "])
def test_model_rejects_a_blank_key(blank):
    with pytest.raises(ValidationError) as e:
        CorpusRef(key=blank, text=None, resolvable=False)
    assert "present but blank" in str(e.value)


@pytest.mark.parametrize("blank", ["", "   ", "\t", "\n "])
def test_model_rejects_blank_text_with_resolvable_false(blank):
    with pytest.raises(ValidationError) as e:
        CorpusRef(key="K", text=blank, resolvable=False)
    assert "present but blank" in str(e.value)


@pytest.mark.parametrize("blank", ["", "   ", "\t", "\n "])
def test_model_rejects_blank_text_with_resolvable_true(blank):
    with pytest.raises(ValidationError):
        CorpusRef(key="K", text=blank, resolvable=True)


def test_qa_reproductions_are_all_refused():
    """The three payloads QA constructed, each now rejected."""
    for kwargs in [dict(key="K", text="   ", resolvable=False),
                   dict(key="   ", text=None, resolvable=False),
                   dict(key="", text=None, resolvable=False)]:
        with pytest.raises(ValidationError):
            CorpusRef(**kwargs)


def test_surrounding_whitespace_on_a_valid_value_is_trimmed_not_rejected():
    r = CorpusRef(key="  K  ", text="  " + PROSE + "  ", resolvable=True)
    assert r.key == "K" and r.text == PROSE


def test_the_three_legal_states_still_construct_after_pf003():
    assert CorpusRef(key="K", text=PROSE, resolvable=True).resolvable is True
    assert CorpusRef(key="K", text=None, resolvable=False).text is None
    assert CorpusRef(key=None, text=None, resolvable=False).key is None


def test_no_fourth_state_survives_any_combination():
    """Exhaustive over the shapes the contract admits."""
    values = [None, "", "   ", "K"]
    texts = [None, "", "   ", PROSE]
    legal = 0
    for k in values:
        for t in texts:
            for flag in (True, False):
                try:
                    r = CorpusRef(key=k, text=t, resolvable=flag)
                except ValidationError:
                    continue
                legal += 1
                # whatever survived must be one of the three declared states
                assert (r.key and r.text and r.resolvable) \
                    or (r.key and r.text is None and not r.resolvable) \
                    or (r.key is None and r.text is None and not r.resolvable)
    assert legal == 3, f"expected exactly three surviving shapes, got {legal}"


def test_unknown_still_never_invokes_the_lookup_after_pf003():
    calls = []
    resolve(Graha.RAHU, D.FRIEND, None,
            corpus_lookup=lambda k: calls.append(k) or "   ")
    assert calls == []


# ── PF-004 · house-lord overlays must be house-SPECIFIC, not just house-keyed ──

from pratiphala_contract import HOUSE_NAMES, HouseLordOverlay

LIBRA = 6


def _overlays(lookup=None, **kw):
    verdicts = {g: resolve(g, kw.get("d1", D.FRIEND), kw.get("d9", D.FRIEND),
                           is_vargottama=kw.get("vg", False), corpus_lookup=lookup)
                for g in Graha}
    return {o.house: o for o in house_lord_overlays(LIBRA, verdicts, lookup)}


def _venus(o):
    return o[1], o[8]          # Libra lagna: Venus lords H1 and H8


def test_venus_h1_and_h8_have_different_house_names():
    h1, h8 = _venus(_overlays())
    assert h1.lord is Graha.VENUS and h8.lord is Graha.VENUS
    assert h1.house_name == "Lagna" and h8.house_name == "Randhra"
    assert h1.house_name != h8.house_name


def test_venus_h1_and_h8_have_different_basis_strings():
    h1, h8 = _venus(_overlays())
    assert h1.basis != h8.basis
    assert "H1" in h1.basis and "Lagna" in h1.basis
    assert "H8" in h8.basis and "Randhra" in h8.basis


def test_venus_h1_and_h8_have_different_house_corpus_keys():
    h1, h8 = _venus(_overlays())
    assert h1.corpus.key != h8.corpus.key
    assert h1.corpus.key == "PRATIPHALA-H1-Venus-Siddha"
    assert h8.corpus.key == "PRATIPHALA-H8-Venus-Siddha"


def test_no_house_key_equals_the_planetary_key():
    o = _overlays()
    for ov in o.values():
        planetary = ov.verdict.corpus.key
        if planetary:
            assert ov.corpus.key != planetary


def test_qa_reproduction_the_two_overlays_are_no_longer_identical():
    h1, h8 = _venus(_overlays())
    assert h1.dict() != h8.dict()
    # the SHARED graha verdict is still shared, deliberately
    assert h1.verdict.dict() == h8.verdict.dict()


def test_dry_lookup_keeps_each_house_key_but_resolves_nothing():
    h1, h8 = _venus(_overlays(lookup=lambda k: None))
    for ov in (h1, h8):
        assert ov.corpus.key and ov.corpus.text is None and ov.corpus.resolvable is False


def test_wet_lookup_receives_distinct_keys_and_attaches_distinct_prose():
    seen = []
    def lookup(k):
        seen.append(k)
        return f"prose for {k}"
    o = _overlays(lookup=lookup)
    h1, h8 = _venus(o)
    assert h1.corpus.text == "prose for PRATIPHALA-H1-Venus-Siddha"
    assert h8.corpus.text == "prose for PRATIPHALA-H8-Venus-Siddha"
    assert h1.corpus.text != h8.corpus.text
    assert h1.corpus.resolvable and h8.corpus.resolvable
    assert "PRATIPHALA-H1-Venus-Siddha" in seen and "PRATIPHALA-H8-Venus-Siddha" in seen


def test_no_house_overlay_can_be_unknown_so_none_skips_the_lookup():
    """PF-007: superseded by the unreachability property.

    This previously asserted that an UNKNOWN overlay performs no lookup. No
    overlay can be UNKNOWN now, so the assertion is inverted: every overlay has
    a key and every key is looked up exactly once. The UNKNOWN short-circuit
    itself is still covered at the GRAHA level, where nodes do occur.
    """
    calls = []
    verdicts = {g: resolve(g, D.FRIEND, None if g in (Graha.RAHU, Graha.KETU) else D.FRIEND)
                for g in Graha}
    o = house_lord_overlays(LIBRA, verdicts, lambda k: calls.append(k) or "prose")
    assert all(ov.corpus.key for ov in o)
    assert len(calls) == 12


def test_sovereign_overlay_keeps_house_identity_and_its_own_key():
    h1, h8 = _venus(_overlays(vg=True))
    assert h1.verdict.governing_state is GoverningLabel.SOVEREIGN
    assert h1.corpus.key == "PRATIPHALA-H1-Venus-Sovereign"
    assert h8.corpus.key == "PRATIPHALA-H8-Venus-Sovereign"
    assert h1.corpus.key != h8.corpus.key
    assert h1.corpus.key != h1.verdict.corpus.key      # not the planetary key
    assert h1.basis != h8.basis


def test_model_rejects_an_overlay_whose_house_and_corpus_identity_disagree():
    good = _overlays()[1]
    payload = good.dict()
    payload["corpus"] = {"key": "PRATIPHALA-H8-Venus-Siddha", "text": None,
                         "resolvable": False}          # H8 key on the H1 overlay
    with pytest.raises(ValidationError) as e:
        HouseLordOverlay(**payload)
    # PF-005 replaced containment with exact binding, so the message names the
    # whole expected key rather than the house alone. Still rejected, and now
    # for the stronger reason.
    assert "must be exactly 'PRATIPHALA-H1-Venus-Siddha'" in str(e.value)


def test_model_rejects_an_overlay_reusing_the_planetary_corpus_key():
    good = _overlays()[1]
    payload = good.dict()
    payload["corpus"] = {"key": "PRATIPHALA-Venus-Siddha", "text": None,
                         "resolvable": False}
    with pytest.raises(ValidationError):
        HouseLordOverlay(**payload)


def test_model_rejects_a_mismatched_house_name():
    good = _overlays()[1]
    payload = good.dict()
    payload["house_name"] = "Randhra"                  # H8's name on the H1 overlay
    with pytest.raises(ValidationError) as e:
        HouseLordOverlay(**payload)
    assert "house_name for house 1" in str(e.value)


def test_the_graha_level_verdict_is_unchanged_by_pf004():
    v = resolve(Graha.VENUS, D.FRIEND, D.FRIEND)
    assert v.corpus.key == "PRATIPHALA-Venus-Siddha"
    assert v.governing_state is GoverningLabel.SIDDHA
    assert not hasattr(v, "house")


def test_every_house_name_matches_the_declared_table():
    o = _overlays()
    for h, ov in o.items():
        assert ov.house_name == HOUSE_NAMES[h]


# ── PF-005 · house, lord, state and shared verdict are all bound ────────────

def _h1_payload(**over):
    p = _overlays()[1].dict()
    p.update(over)
    return p


def _corpus(key):
    return {"key": key, "text": None, "resolvable": False}


@pytest.mark.parametrize("bad_key,why", [
    ("PRATIPHALA-H1-Mars-Siddha",   "right house, WRONG GRAHA"),
    ("PRATIPHALA-H1-Venus-Rikt",    "right house and graha, WRONG STATE"),
    ("JUNK-H1-WRONG",               "arbitrary text carrying the house token"),
    ("PRATIPHALA-H8-Venus-Siddha",  "wrong house"),
    ("PRATIPHALA-Venus-Siddha",     "the planetary key"),
    ("pratiphala-h1-venus-siddha",  "case-shifted"),
])
def test_qa_reproductions_every_wrong_key_is_refused(bad_key, why):
    with pytest.raises(ValidationError) as e:
        HouseLordOverlay(**_h1_payload(corpus=_corpus(bad_key)))
    assert "must be exactly" in str(e.value), why


def test_reject_lord_venus_with_a_mars_verdict():
    mars = resolve(Graha.MARS, D.FRIEND, D.FRIEND)
    with pytest.raises(ValidationError) as e:
        HouseLordOverlay(**_h1_payload(verdict=mars.dict()))
    assert "carries a verdict for Mars" in str(e.value)


def test_reject_a_response_whose_overlay_contradicts_the_top_level_verdict():
    d1 = {g: D.FRIEND for g in Graha}
    d9 = {g: D.FRIEND for g in Graha}
    vg = {g: False for g in Graha}
    r = build_pratiphala("tok" + "x" * 9, d1, d9, vg, LIBRA)
    payload = r.dict()
    # a SECOND, contradictory Venus reading on the H1 card only
    other = resolve(Graha.VENUS, D.DEBILITATED, D.ENEMY)     # Rikt, not Siddha
    for o in payload["house_lord_overlays"]:
        if o["house"] == 1:
            o["verdict"] = other.dict()
            o["corpus"] = _corpus("PRATIPHALA-H1-Venus-Rikt")
            o["basis"] = "contradictory"
    with pytest.raises(ValidationError) as e:
        PratiphalaPrepareResponse(**payload)
    assert "one graha has one reading" in str(e.value)


@pytest.mark.parametrize("d1,d9,vg,state", [
    (D.EXALTED,     D.FRIEND,  False, "Siddha"),
    (D.EXALTED,     D.NEUTRAL, False, "Viphala"),
    (D.NEUTRAL,     D.EXALTED, False, "Prachanna"),
    (D.DEBILITATED, D.ENEMY,   False, "Rikt"),
    (D.EXALTED,     D.FRIEND,  True,  "Sovereign"),
])
def test_every_exact_house_key_is_accepted(d1, d9, vg, state):
    o = _overlays(d1=d1, d9=d9, vg=vg)
    for h in (1, 8):
        assert o[h].corpus.key == f"PRATIPHALA-H{h}-Venus-{state}"


def test_an_unknown_house_overlay_is_now_UNREACHABLE():
    """PF-007 consequence, asserted rather than assumed.

    Absence is a node privilege, and nodes own no rasi in the Parasari scheme,
    so no house lord can lack a dignity. The two tests that previously covered
    "an UNKNOWN overlay carries no corpus identity" cannot be written any more:
    the contract refuses to construct one, at the overlay AND at the graha
    level. That is a stronger guarantee than the tests they replace, but it is a
    REDUCTION IN COVERAGE and is recorded as one.
    """
    from pratiphala_routes import SIGN_LORDS
    assert not any(g in (Graha.RAHU, Graha.KETU) for g in SIGN_LORDS)

    # every lord assessed, so no overlay is UNKNOWN
    verdicts = {g: resolve(g, D.FRIEND, None if g in (Graha.RAHU, Graha.KETU) else D.FRIEND)
                for g in Graha}
    for ov in house_lord_overlays(LIBRA, verdicts, lambda k: "prose"):
        assert ov.verdict.governing_state is not GoverningLabel.UNKNOWN
        assert ov.corpus.key is not None

    # and one cannot be forced: a classical graha with no dignity is refused
    with pytest.raises(ValidationError) as e:
        GrahaPratiphala(**{**resolve(Graha.RAHU, D.FRIEND, None).dict(),
                           "graha": Graha.MARS.value})
    assert "only Rahu and Ketu may lack one" in str(e.value)


def test_libra_h1_and_h8_venus_overlays_remain_distinct_after_pf005():
    h1, h8 = _venus(_overlays())
    assert h1.corpus.key != h8.corpus.key
    assert h1.basis != h8.basis
    assert h1.house_name != h8.house_name
    assert h1.verdict.dict() == h8.verdict.dict()      # shared evidence, still shared


def test_a_correct_overlay_still_constructs():
    """The binding must not have closed the legitimate path."""
    assert HouseLordOverlay(**_h1_payload()).corpus.key == "PRATIPHALA-H1-Venus-Siddha"


def test_surrounding_whitespace_on_a_correct_key_is_trimmed_not_rejected():
    """PF-003's trimming runs BEFORE the PF-005 comparison, so a key that is
    correct apart from whitespace is normalised rather than refused. Asserted
    deliberately: my first PF-005 test expected a rejection here and was wrong
    about the interaction between the two validators."""
    ov = HouseLordOverlay(**_h1_payload(corpus=_corpus("  PRATIPHALA-H1-Venus-Siddha  ")))
    assert ov.corpus.key == "PRATIPHALA-H1-Venus-Siddha"



# ── PF-006 · the derived reading is bound to its dignity inputs ─────────────
# The defect was a CONSISTENTLY FALSE reading: ranks, strengths, tiers, labels
# and quadrant all agreeing with each other and none of them agreeing with the
# dignities. Coherence is not correctness; only the dignities are input.

import pratiphala_contract as PC


def _sound():
    """A correct Friend/Friend Siddha reading, as a mutation base."""
    return resolve(Graha.SUN, D.FRIEND, D.FRIEND).dict()


def _mutate(**over):
    p = _sound()
    ev = over.pop("evidence", None)
    if ev:
        p["evidence"].update(ev)
    p.update(over)
    return p


def _rejected(payload, fragment):
    with pytest.raises(ValidationError) as e:
        GrahaPratiphala(**payload)
    assert fragment in str(e.value), str(e.value)[:300]


def test_reject_a_wrong_dignity_rank():
    _rejected(_mutate(evidence={"d1_rank": 6}), "evidence.d1_rank=6")


def test_reject_a_rank_strength_contradiction():
    _rejected(_mutate(evidence={"d1_strength": Strength.WEAK.value}), "evidence.d1_strength")


def test_reject_a_rank_sub_tier_contradiction():
    _rejected(_mutate(d1_sub_tier=SubTier.WEAK.value), "d1_sub_tier")


def test_reject_an_incorrect_underlying_quadrant():
    _rejected(_mutate(evidence={"underlying_state": PratiphalaState.RIKT.value}),
              "evidence.underlying_state")


def test_reject_an_incorrect_governing_state():
    _rejected(_mutate(governing_state=GoverningLabel.RIKT.value,
                      corpus={"key": "PRATIPHALA-Sun-Rikt", "text": None,
                              "resolvable": False}),
              "governing_state")


def test_reject_an_incorrect_governing_sanskrit_label():
    _rejected(_mutate(governing_state_sa="रिक्त"), "governing_state_sa")


def test_reject_an_incorrect_underlying_sanskrit_label():
    _rejected(_mutate(evidence={"underlying_state_sa": "रिक्त"}), "underlying_state_sa")


@pytest.mark.parametrize("bad", [2, 4, 0, 6])
def test_reject_strong_at_rank_other_than_three(bad):
    _rejected(_mutate(evidence={"strong_at_rank": bad}), "strong_at_rank")


@pytest.mark.parametrize("bad_key", ["PRATIPHALA-Sun-Rikt", "PRATIPHALA-Mars-Siddha",
                                     "JUNK", "PRATIPHALA-Sun-Siddha-extra"])
def test_reject_a_wrong_graha_corpus_key(bad_key):
    _rejected(_mutate(corpus={"key": bad_key, "text": None, "resolvable": False}),
              "corpus.key")


@pytest.mark.parametrize("unreachable", [D.GREAT_FRIEND, D.GREAT_ENEMY])
def test_reject_great_friend_and_great_enemy_through_the_model(unreachable):
    with pytest.raises((ValidationError, PC.PratiphalaPolicyError)) as e:
        GrahaPratiphala(**_mutate(d1_dignity=unreachable.value))
    assert "locked Pratiphala scale" in str(e.value)


def test_reject_qa_reproduction_friend_friend_presented_as_rikt():
    """Every derived field internally consistent, all of them wrong."""
    payload = _mutate(
        d1_sub_tier=SubTier.WEAK.value, d9_sub_tier=SubTier.WEAK.value,
        governing_state=GoverningLabel.RIKT.value, governing_state_sa="रिक्त",
        corpus={"key": "PRATIPHALA-Sun-Rikt", "text": None, "resolvable": False},
        evidence={"d1_rank": 1, "d9_rank": 1,
                  "d1_strength": Strength.WEAK.value, "d9_strength": Strength.WEAK.value,
                  "underlying_state": PratiphalaState.RIKT.value,
                  "underlying_state_sa": "रिक्त"})
    _rejected(payload, "contradicts its own dignities")


def test_reject_the_complete_response_carrying_that_false_reading():
    d1 = {g: D.FRIEND for g in Graha}
    r = build_pratiphala("tok" + "x" * 9, d1, dict(d1), {g: False for g in Graha}, LIBRA)
    payload = r.dict()
    for g in payload["grahas"]:
        if g["graha"] == "Sun":
            g["governing_state"] = GoverningLabel.RIKT.value
            g["governing_state_sa"] = "रिक्त"
            g["corpus"] = {"key": "PRATIPHALA-Sun-Rikt", "text": None, "resolvable": False}
            g["evidence"]["underlying_state"] = PratiphalaState.RIKT.value
            g["evidence"]["underlying_state_sa"] = "रिक्त"
    with pytest.raises(ValidationError):
        PratiphalaPrepareResponse(**payload)


@pytest.mark.parametrize("d1", ALL_SEVEN)
@pytest.mark.parametrize("d9", ALL_SEVEN)
@pytest.mark.parametrize("vg", [True, False])
def test_exhaustive_seven_by_seven_by_vargottama(d1, d9, vg):
    """49 dignity pairs x 2. Every one must build and re-validate."""
    v = resolve(Graha.VENUS, d1, d9, is_vargottama=vg)
    again = GrahaPratiphala(**v.dict())
    assert again.governing_state is v.governing_state
    if vg:
        assert v.governing_state is GoverningLabel.SOVEREIGN
    else:
        assert v.governing_state.value == quadrant_of(rank_of(d1), rank_of(d9)).value
    assert v.evidence.d1_rank == PC.DIGNITY_RANK[d1]
    assert v.d1_sub_tier is PC.sub_tier_of(PC.DIGNITY_RANK[d1])


@pytest.mark.parametrize("d1", ALL_SEVEN)
@pytest.mark.parametrize("vg", [True, False])
def test_exhaustive_absent_d9_across_every_d1_and_vargottama(d1, vg):
    v = resolve(Graha.RAHU, d1, None, is_vargottama=vg)
    assert v.governing_state is GoverningLabel.UNKNOWN
    assert v.d9_sub_tier is SubTier.UNKNOWN
    assert v.evidence.d9_rank is None
    assert (v.corpus.key, v.corpus.text, v.corpus.resolvable) == (None, None, False)
    assert GrahaPratiphala(**v.dict()).governing_state is GoverningLabel.UNKNOWN


def test_one_policy_not_two():
    """routes must not redefine the rules; it imports them."""
    import pratiphala_routes as PRR
    for fn in ("rank_of", "strength_of", "sub_tier_of", "quadrant_of"):
        assert getattr(PRR, fn) is getattr(PC, fn), f"{fn} is a second copy"


# ── PF-007 · nodes may lack a D1 dignity, a D9 dignity, or both ─────────────

NODES = [Graha.RAHU, Graha.KETU]


def _expect_unknown(v, d1_absent, d9_absent):
    assert v.governing_state is GoverningLabel.UNKNOWN
    assert v.evidence.underlying_state is PratiphalaState.UNKNOWN
    assert v.evidence.sovereign_override_applied is False
    assert (v.corpus.key, v.corpus.text, v.corpus.resolvable) == (None, None, False)
    if d1_absent:
        assert v.evidence.d1_rank is None and v.evidence.d1_strength is None
        assert v.d1_sub_tier is SubTier.UNKNOWN
    if d9_absent:
        assert v.evidence.d9_rank is None and v.evidence.d9_strength is None
        assert v.d9_sub_tier is SubTier.UNKNOWN
    GrahaPratiphala(**v.dict())          # and it re-validates


@pytest.mark.parametrize("node", NODES)
@pytest.mark.parametrize("vg", [False, True])
def test_node_with_d1_absent_and_d9_present(node, vg):
    v = resolve(node, None, D.EXALTED, is_vargottama=vg)
    _expect_unknown(v, d1_absent=True, d9_absent=False)
    # the PRESENT side keeps its real derived values
    assert v.evidence.d9_rank == 6
    assert v.evidence.d9_strength is Strength.STRONG
    assert v.d9_sub_tier is SubTier.UTTAMA
    assert "no certified D1 dignity" in v.basis


@pytest.mark.parametrize("node", NODES)
@pytest.mark.parametrize("vg", [False, True])
def test_node_with_d1_present_and_d9_absent(node, vg):
    v = resolve(node, D.EXALTED, None, is_vargottama=vg)
    _expect_unknown(v, d1_absent=False, d9_absent=True)
    assert v.evidence.d1_rank == 6
    assert v.evidence.d1_strength is Strength.STRONG
    assert v.d1_sub_tier is SubTier.UTTAMA
    assert "no certified D9 dignity" in v.basis


@pytest.mark.parametrize("node", NODES)
@pytest.mark.parametrize("vg", [False, True])
def test_node_with_both_dignities_absent(node, vg):
    v = resolve(node, None, None, is_vargottama=vg)
    _expect_unknown(v, d1_absent=True, d9_absent=True)
    assert "no certified D1 or D9 dignity" in v.basis


def test_unknown_from_an_absent_d1_performs_no_corpus_lookup():
    calls = []
    resolve(Graha.RAHU, None, D.EXALTED, corpus_lookup=lambda k: calls.append(k) or "prose")
    resolve(Graha.KETU, None, None, corpus_lookup=lambda k: calls.append(k) or "prose")
    assert calls == []


@pytest.mark.parametrize("classical", [g for g in Graha if g not in NODES])
def test_classical_graha_with_an_absent_d1_dignity_is_rejected(classical):
    payload = resolve(Graha.RAHU, None, D.EXALTED).dict()
    payload["graha"] = classical.value
    with pytest.raises(ValidationError) as e:
        GrahaPratiphala(**payload)
    assert "only Rahu and Ketu may lack one" in str(e.value)


@pytest.mark.parametrize("classical", [g for g in Graha if g not in NODES])
def test_classical_graha_with_an_absent_d9_dignity_is_rejected(classical):
    payload = resolve(Graha.RAHU, D.EXALTED, None).dict()
    payload["graha"] = classical.value
    with pytest.raises(ValidationError) as e:
        GrahaPratiphala(**payload)
    assert "only Rahu and Ketu may lack one" in str(e.value)


def test_full_response_with_ordinary_sign_nodes_validates():
    d1 = {g: D.FRIEND for g in Graha}
    d9 = {g: D.FRIEND for g in Graha}
    for n in NODES:
        d1[n] = None                       # the case that returned 500
        d9[n] = None
    r = build_pratiphala("tok" + "x" * 9, d1, d9, {g: False for g in Graha}, LIBRA)
    PratiphalaPrepareResponse(**r.dict())  # re-validates
    by = {g.graha: g for g in r.grahas}
    assert by[Graha.RAHU].governing_state is GoverningLabel.UNKNOWN
    assert by[Graha.KETU].governing_state is GoverningLabel.UNKNOWN
    assert by[Graha.SUN].governing_state is GoverningLabel.SIDDHA


def test_the_real_adapter_and_engine_path_with_the_node_sentinel():
    """End to end from a certified payload whose nodes carry 'Node'."""
    import json, copy
    from d1_contract import Varga
    from d1_chart_adapter import to_certified_chart
    cap = json.load(open("/mnt/user-data/outputs/step10_chart_of_record.json"))
    cap = copy.deepcopy(cap)
    for n in ("Rahu", "Ketu"):
        cap["planets"][n]["dignity"] = "Node"       # ordinary sign
        cap["planets"][n]["d9_dignity"] = "Node"
    chart = to_certified_chart(cap, cap["chart_token"], varga=Varga.D9)
    assert chart.grahas[Graha.RAHU].dignity is None
    d1, d9, vg, lagna = PR._from_certified(chart)
    r = build_pratiphala(cap["chart_token"], d1, d9, vg, lagna)
    by = {g.graha: g for g in r.grahas}
    assert by[Graha.RAHU].governing_state is GoverningLabel.UNKNOWN
    assert by[Graha.KETU].governing_state is GoverningLabel.UNKNOWN


def test_prepare_returns_200_for_a_chart_with_node_sentinel_dignities():
    """The route itself: 200, not the 500 PF-007 reported."""
    import json, copy
    cap = copy.deepcopy(json.load(open("/mnt/user-data/outputs/step10_chart_of_record.json")))
    for n in ("Rahu", "Ketu"):
        cap["planets"][n]["dignity"] = "Node"
        cap["planets"][n]["d9_dignity"] = "Node"
    app = _app()
    app.dependency_overrides[get_chart_resolver] = lambda: _Recorder(result=cap)
    with TestClient(app) as c:
        r = c.post("/pratiphala/prepare", json={"chart_token": cap["chart_token"]})
    assert r.status_code == 200, r.text
    by = {g["graha"]: g for g in r.json()["grahas"]}
    assert by["Rahu"]["governing_state"] == "UNKNOWN"
    assert by["Ketu"]["governing_state"] == "UNKNOWN"


# ── PF-008 · a node cannot lord a house ────────────────────────────────────

from pratiphala_contract import CLASSICAL_HOUSE_LORDS


def _node_overlay_payload(node):
    """The exact impossible overlay QA constructed: internally consistent in
    every respect except that a node owns no rāśi."""
    p = _overlays()[1].dict()
    p["lord"] = node.value
    p["overlay_key"] = f"H1:{node.value}"
    p["verdict"] = resolve(node, D.FRIEND, None).dict()      # the real node UNKNOWN verdict
    p["corpus"] = {"key": None, "text": None, "resolvable": False}
    return p


@pytest.mark.parametrize("node", [Graha.RAHU, Graha.KETU])
def test_direct_overlay_with_a_node_lord_is_rejected(node):
    with pytest.raises(ValidationError) as e:
        HouseLordOverlay(**_node_overlay_payload(node))
    assert "owns no rāśi" in str(e.value)


@pytest.mark.parametrize("node", [Graha.RAHU, Graha.KETU])
@pytest.mark.parametrize("house", range(1, 13))
def test_a_node_lord_is_rejected_for_every_house(node, house):
    p = _node_overlay_payload(node)
    p["house"] = house
    p["house_name"] = HOUSE_NAMES[house]
    p["overlay_key"] = f"H{house}:{node.value}"
    with pytest.raises(ValidationError):
        HouseLordOverlay(**p)


@pytest.mark.parametrize("node", [Graha.RAHU, Graha.KETU])
def test_rejection_holds_even_when_everything_else_is_consistent(node):
    """No arrangement of key, verdict or corpus buys a node a house."""
    for corpus in ({"key": None, "text": None, "resolvable": False},
                   {"key": f"PRATIPHALA-H1-{node.value}-Siddha", "text": None,
                    "resolvable": False}):
        p = _node_overlay_payload(node)
        p["corpus"] = corpus
        with pytest.raises(ValidationError) as e:
            HouseLordOverlay(**p)
        assert "owns no rāśi" in str(e.value)


@pytest.mark.parametrize("node", [Graha.RAHU, Graha.KETU])
def test_a_complete_response_containing_a_node_house_lord_is_rejected(node):
    d1 = {g: D.FRIEND for g in Graha}
    d9 = {g: D.FRIEND for g in Graha}
    d9[node] = None
    r = build_pratiphala("tok" + "x" * 9, d1, d9, {g: False for g in Graha}, LIBRA)
    payload = r.dict()
    payload["house_lord_overlays"][0] = _node_overlay_payload(node)
    with pytest.raises(ValidationError) as e:
        PratiphalaPrepareResponse(**payload)
    assert "owns no rāśi" in str(e.value)


def test_top_level_node_verdicts_remain_valid_and_may_be_unknown():
    """PF-008 restricts LORDSHIP only. The graha reading is untouched."""
    for node in (Graha.RAHU, Graha.KETU):
        v = resolve(node, D.FRIEND, None)
        assert v.governing_state is GoverningLabel.UNKNOWN
        assert GrahaPratiphala(**v.dict()).graha is node
    d1 = {g: D.FRIEND for g in Graha}
    d9 = {g: D.FRIEND for g in Graha}
    d9[Graha.RAHU] = d9[Graha.KETU] = None
    r = build_pratiphala("tok" + "x" * 9, d1, d9, {g: False for g in Graha}, LIBRA)
    PratiphalaPrepareResponse(**r.dict())
    by = {g.graha: g for g in r.grahas}
    assert by[Graha.RAHU].governing_state is GoverningLabel.UNKNOWN


@pytest.mark.parametrize("lagna", range(12))
def test_every_builder_overlay_uses_a_classical_lord_for_every_lagna(lagna):
    d1 = {g: D.FRIEND for g in Graha}
    d9 = {g: D.FRIEND for g in Graha}
    d9[Graha.RAHU] = d9[Graha.KETU] = None
    r = build_pratiphala("tok" + "x" * 9, d1, d9, {g: False for g in Graha}, lagna)
    assert len(r.house_lord_overlays) == 12
    for ov in r.house_lord_overlays:
        assert ov.lord in CLASSICAL_HOUSE_LORDS
        assert ov.lord not in (Graha.RAHU, Graha.KETU)
    PratiphalaPrepareResponse(**r.dict())      # all twelve re-validate


def test_libra_h1_and_h8_venus_behaviour_is_unchanged_by_pf008():
    h1, h8 = _venus(_overlays())
    assert h1.lord is Graha.VENUS and h8.lord is Graha.VENUS
    assert h1.corpus.key == "PRATIPHALA-H1-Venus-Siddha"
    assert h8.corpus.key == "PRATIPHALA-H8-Venus-Siddha"
    assert h1.basis != h8.basis
    assert h1.verdict.dict() == h8.verdict.dict()


def test_unknown_overlays_are_now_unreachable_by_BOTH_routes():
    """The property PF-007 could only half-assert.

    Builder: no lord is ever a node. Direct construction: a node lord is
    refused outright. So no overlay can carry an UNKNOWN verdict, because only
    nodes can be UNKNOWN and only nodes are barred from lordship.
    """
    from pratiphala_routes import SIGN_LORDS
    assert not any(g in (Graha.RAHU, Graha.KETU) for g in SIGN_LORDS)
    with pytest.raises(ValidationError):
        HouseLordOverlay(**_node_overlay_payload(Graha.RAHU))


# ── PF-009 · every house lord is bound to the response Lagna ───────────────

from pratiphala_contract import RASHI_LORDS, expected_lord_of


def _response(lagna=LIBRA):
    d1 = {g: D.FRIEND for g in Graha}
    return build_pratiphala("tok" + "x" * 9, d1, dict(d1),
                            {g: False for g in Graha}, lagna)


def _swap_lord(payload, house, lord):
    """Make an overlay LOCALLY self-consistent under a wrong lord."""
    for o in payload["house_lord_overlays"]:
        if o["house"] == house:
            o["lord"] = lord.value
            o["overlay_key"] = f"H{house}:{lord.value}"
            v = resolve(lord, D.FRIEND, D.FRIEND)
            o["verdict"] = v.dict()
            # .value, not the enum repr: the overlay must be LOCALLY VALID or
            # PF-005 rejects it first and PF-009 is never reached, which would
            # make this test pass for the wrong reason.
            o["corpus"] = {"key": f"PRATIPHALA-H{house}-{lord.value}-{v.governing_state.value}",
                           "text": None, "resolvable": False}
            o["basis"] = f"{lord.value} lords H{house}"
    return payload


def test_reject_qa_reproduction_libra_h1_declared_as_mars():
    payload = _swap_lord(_response(LIBRA).dict(), 1, Graha.MARS)
    with pytest.raises(ValidationError) as e:
        PratiphalaPrepareResponse(**payload)
    assert "H1 declares lord Mars" in str(e.value)
    assert "ruled by Venus" in str(e.value)


@pytest.mark.parametrize("lagna", range(12))
def test_reject_a_wrong_classical_lord_for_every_house_and_lagna(lagna):
    base = _response(lagna).dict()
    for house in range(1, 13):
        right = expected_lord_of(lagna, house)
        wrong = next(g for g in CLASSICAL_HOUSE_LORDS if g is not right)
        with pytest.raises(ValidationError):
            PratiphalaPrepareResponse(**_swap_lord(
                {**base, "house_lord_overlays": [dict(o) for o in base["house_lord_overlays"]]},
                house, wrong))


@pytest.mark.parametrize("lagna", range(12))
def test_accept_exactly_the_correct_lord_for_every_house_and_lagna(lagna):
    r = _response(lagna)
    assert r.lagna_sign_index == lagna
    for ov in r.house_lord_overlays:
        assert ov.lord is expected_lord_of(lagna, ov.house)
        assert ov.lord is RASHI_LORDS[(lagna + ov.house - 1) % 12]
    PratiphalaPrepareResponse(**r.dict())


def test_reject_another_lagnas_complete_overlay_sequence():
    """Every overlay internally valid, the whole set belonging to a different
    lagna, while the declared index stays put."""
    aries = _response(0).dict()
    libra = _response(LIBRA).dict()
    mixed = {**libra, "house_lord_overlays": aries["house_lord_overlays"]}
    assert mixed["lagna_sign_index"] == LIBRA
    with pytest.raises(ValidationError) as e:
        PratiphalaPrepareResponse(**mixed)
    assert "declares lord" in str(e.value)


@pytest.mark.parametrize("bad", [None, -1, 12, 99])
def test_reject_missing_or_out_of_range_lagna_indices(bad):
    payload = _response().dict()
    if bad is None:
        payload.pop("lagna_sign_index")
    else:
        payload["lagna_sign_index"] = bad
    with pytest.raises(ValidationError):
        PratiphalaPrepareResponse(**payload)


@pytest.mark.parametrize("lagna", range(12))
def test_builder_publishes_the_exact_supplied_lagna(lagna):
    assert _response(lagna).lagna_sign_index == lagna


def test_route_publishes_the_lagna_from_the_certified_d1_computation():
    import json, copy
    cap = copy.deepcopy(json.load(open("/mnt/user-data/outputs/step10_chart_of_record.json")))
    expected = cap["lagna"]["sign_index"]          # Libra, 6, on the chart of record
    app = _app()
    app.dependency_overrides[get_chart_resolver] = lambda: _Recorder(result=cap)
    with TestClient(app) as c:
        r = c.post("/pratiphala/prepare", json={"chart_token": cap["chart_token"]})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["lagna_sign_index"] == expected
    h1 = [o for o in body["house_lord_overlays"] if o["house"] == 1][0]
    assert h1["lord"] == expected_lord_of(expected, 1).value


def test_the_route_and_the_contract_share_one_sign_lord_table():
    import pratiphala_routes as PRR
    assert PRR.SIGN_LORDS is PC.RASHI_LORDS, "the route holds a second table"
    assert PRR.expected_lord_of is PC.expected_lord_of


@pytest.mark.parametrize("node", [Graha.RAHU, Graha.KETU])
def test_pf008_still_rejects_nodes_as_house_lords_after_pf009(node):
    with pytest.raises(ValidationError) as e:
        HouseLordOverlay(**_node_overlay_payload(node))
    assert "owns no rāśi" in str(e.value)


def test_libra_h1_and_h8_venus_remain_distinct_and_valid_after_pf009():
    r = _response(LIBRA)
    by = {o.house: o for o in r.house_lord_overlays}
    h1, h8 = by[1], by[8]
    assert h1.lord is Graha.VENUS and h8.lord is Graha.VENUS
    assert h1.corpus.key != h8.corpus.key
    assert h1.basis != h8.basis
    PratiphalaPrepareResponse(**r.dict())


# ── PF-010 · the published policy block is bound to the real policy ────────

from pratiphala_contract import (
    CONTRACT_VERSION, PratiphalaPolicy, SCALE_DESCRIPTION, SOVEREIGN_RULE,
    UNKNOWN_RULE,
)


def test_default_policy_serializes_the_exact_locked_values():
    p = PratiphalaPolicy().dict()
    assert p == {
        "contract_version": CONTRACT_VERSION,
        "strong_at_rank": 3,
        "scale": "debilitated0-enemy1-neutral2-friend3-own4-moolatrikona5-exalted6",
        "sovereign_rule": SOVEREIGN_RULE,
        "unknown_rule": UNKNOWN_RULE,
    }
    assert p["strong_at_rank"] == PC.STRONG_AT
    assert p["scale"] == SCALE_DESCRIPTION


def test_the_published_unknown_rule_covers_either_side_after_pf007():
    """The stale wording said 'absent D9'. It must state the real rule."""
    rule = PratiphalaPolicy().unknown_rule
    assert "D1" in rule and "D9" in rule
    assert "Rikt" in rule and "Sovereign" in rule


def test_the_published_sovereign_rule_states_the_pf001_precedence():
    rule = PratiphalaPolicy().sovereign_rule
    assert "never overrides UNKNOWN" in rule


@pytest.mark.parametrize("d1,d9,which", [
    (None,      D.EXALTED, "D1 absent, D9 present"),
    (D.EXALTED, None,      "D1 present, D9 absent"),
    (None,      None,      "both absent"),
])
def test_every_absence_case_is_unknown_under_the_one_published_rule(d1, d9, which):
    r = build_pratiphala("tok" + "x" * 9,
                         {g: (d1 if g is Graha.RAHU else D.FRIEND) for g in Graha},
                         {g: (d9 if g is Graha.RAHU else D.FRIEND) for g in Graha},
                         {g: False for g in Graha}, LIBRA)
    by = {g.graha: g for g in r.grahas}
    assert by[Graha.RAHU].governing_state is GoverningLabel.UNKNOWN, which
    # the SAME universal rule covers all three, rather than a D9-only one
    assert r.policy.unknown_rule == UNKNOWN_RULE
    assert "D1 OR D9" in r.policy.unknown_rule


@pytest.mark.parametrize("field,bad", [
    ("strong_at_rank", 2),
    ("strong_at_rank", True),          # True == 1, so a bare equality check passes
    ("strong_at_rank", 4),
    ("scale", "debilitated0-enemy1-neutral2-friend2-own4-moolatrikona5-exalted6"),
    ("sovereign_rule", "vargottama overrides everything"),
    ("unknown_rule", "only absent D9 yields UNKNOWN"),
    ("contract_version", "pratiphala-contract-9.9.9"),
])
def test_reject_any_altered_policy_value(field, bad):
    with pytest.raises(ValidationError) as e:
        PratiphalaPolicy(**{field: bad})
    assert field in str(e.value)


def test_strong_at_rank_true_is_refused_specifically():
    """`True == 1` in Python, so a boolean would slip past `!= 3` if the check
    did not exclude bools explicitly."""
    with pytest.raises(ValidationError):
        PratiphalaPolicy(strong_at_rank=True)
    assert PratiphalaPolicy(strong_at_rank=3).strong_at_rank == 3


def test_reject_a_complete_response_whose_policy_block_was_mutated():
    r = _response(LIBRA)
    payload = r.dict()
    payload["policy"]["strong_at_rank"] = 2
    payload["policy"]["unknown_rule"] = "only absent D9 yields UNKNOWN"
    with pytest.raises(ValidationError) as e:
        PratiphalaPrepareResponse(**payload)
    assert "the rules the shared policy actually uses" in str(e.value)


def test_a_response_carrying_the_true_policy_still_validates():
    r = _response(LIBRA)
    assert r.policy.strong_at_rank == 3
    PratiphalaPrepareResponse(**r.dict())


def test_no_duplicate_literals_the_constants_are_the_same_objects():
    """The defaults and the validator must read one declaration each."""
    p = PratiphalaPolicy()
    assert p.scale is SCALE_DESCRIPTION
    assert p.sovereign_rule is SOVEREIGN_RULE
    assert p.unknown_rule is UNKNOWN_RULE
    assert p.contract_version is CONTRACT_VERSION


# ── Step 6 · POST /pratiphalareport ────────────────────────────────────────
# The narrative must be the SAME reading as the cards, by construction. These
# test the wiring and the brief; the prose itself is the model's.

import json
import re

import pratiphala_narrative as PN
from pratiphala_contract import PratiphalaReportRequest, PratiphalaReportResponse

# FIELD NAMES, checked as keys rather than as substrings. Scanning the whole
# JSON blob for "evidence" also matched the word inside a basis SENTENCE, which
# is prose the server authored and is supposed to travel. Checking keys tests
# what the allowlist actually controls.
BRIEF_FORBIDDEN = ("d1_rank", "d9_rank", "strong_at_rank", "underlying_state",
                   "underlying_state_sa", "sovereign_override_applied",
                   "evidence", "resolvable", "corpus", "is_vargottama",
                   "d1_strength", "d9_strength")


def _all_keys(obj):
    out = set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.add(k); out |= _all_keys(v)
    elif isinstance(obj, list):
        for v in obj:
            out |= _all_keys(v)
    return out


def _report_app(monkeypatch, rec, report="ZQXREPORTQ7 prose."):
    monkeypatch.setattr(PN, "generate_report", lambda result, name=None: report)
    monkeypatch.setattr(PR, "generate_report", lambda result, name=None: report)
    app = _app()
    app.include_router(PR.router) if False else None
    app.dependency_overrides[get_chart_resolver] = lambda: rec
    return app


class _Framing:
    """PF-013B: the provider CHOOSES; it no longer writes."""
    from pratiphala_contract import FramingConclusionId, FramingIntroductionId
    introduction_id = FramingIntroductionId.PLAIN
    conclusion_id = FramingConclusionId.PLAIN


def _capture_brief(monkeypatch, rec):
    """PF-013: the brief is now built inside generate_report and passed to
    fetch_framing, so it is captured THERE rather than at the route boundary."""
    seen = {}
    def _fetch(brief, name=None):
        seen["brief"] = brief
        seen["name"] = name
        return _Framing()
    monkeypatch.setattr(PN, "fetch_framing", _fetch)
    app = _app()
    app.dependency_overrides[get_chart_resolver] = lambda: rec
    return app, seen


def _chart_payload():
    import json, copy
    return copy.deepcopy(json.load(open("/mnt/user-data/outputs/step10_chart_of_record.json")))


def test_exactly_one_post_pratiphalareport_route_exists():
    assert len(_posts(_app(), "/pratiphalareport")) == 1
    assert len(_posts(_app(), "/pratiphala/prepare")) == 1


def test_the_report_route_uses_the_report_response_model():
    assert _posts(_app(), "/pratiphalareport")[0].response_model is PratiphalaReportResponse


@pytest.mark.parametrize("extra", [
    {"chart_brief": {"x": 1}},
    {"grahas": []},
    {"house_lord_overlays": []},
    {"governing_state": "Siddha"},
    {"d1_dignity": "Exalted"},
    {"corpus": {"text": "invented"}},
    {"evidence": {"d1_rank": 6}},
    {"chart_tokn": "typo"},
])
def test_the_request_rejects_every_unknown_field(extra):
    with pytest.raises(ValidationError):
        PratiphalaReportRequest(chart_token=TOKEN, **extra)


def test_the_request_accepts_only_a_token_and_an_optional_name():
    assert PratiphalaReportRequest(chart_token=TOKEN).name is None
    assert PratiphalaReportRequest(chart_token=TOKEN, name="Atul").name == "Atul"


def test_the_resolver_receives_the_exact_token_and_is_called_once(monkeypatch):
    rec = _Recorder(result=_chart_payload())
    app, _ = _capture_brief(monkeypatch, rec)
    with TestClient(app) as c:
        r = c.post("/pratiphalareport", json={"chart_token": TOKEN})
    assert r.status_code == 200, r.text
    assert rec.calls == 1 and rec.tokens == [TOKEN]


def test_both_endpoints_use_the_same_pratiphala_builder(monkeypatch):
    """Not 'produce the same answer' — the SAME builder, spied once."""
    calls = []
    real = PR.build_pratiphala
    monkeypatch.setattr(PR, "build_pratiphala",
                        lambda *a, **k: (calls.append(a[0]), real(*a, **k))[1])
    monkeypatch.setattr(PR, "generate_report", lambda result, name=None: "prose")
    cap = _chart_payload()
    app = _app()
    app.dependency_overrides[get_chart_resolver] = lambda: _Recorder(result=cap)
    with TestClient(app) as c:
        a = c.post("/pratiphala/prepare", json={"chart_token": cap["chart_token"]})
        b = c.post("/pratiphalareport", json={"chart_token": cap["chart_token"]})
    assert a.status_code == 200 and b.status_code == 200, (a.text, b.text)
    assert len(calls) == 2, "each endpoint went through build_pratiphala exactly once"


def test_the_brief_contains_all_nine_grahas_and_twelve_overlays(monkeypatch):
    cap = _chart_payload()
    app, seen = _capture_brief(monkeypatch, _Recorder(result=cap))
    with TestClient(app) as c:
        c.post("/pratiphalareport", json={"chart_token": cap["chart_token"]})
    brief = seen["brief"]
    assert len(brief["grahas"]) == 9
    assert len(brief["house_overlays"]) == 12
    assert {g["graha"] for g in brief["grahas"]} == {g.value for g in Graha}


def test_the_brief_carries_no_ranks_scores_or_internal_evidence(monkeypatch):
    cap = _chart_payload()
    app, seen = _capture_brief(monkeypatch, _Recorder(result=cap))
    with TestClient(app) as c:
        c.post("/pratiphalareport", json={"chart_token": cap["chart_token"]})
    keys = _all_keys(seen["brief"])
    for forbidden in BRIEF_FORBIDDEN:
        assert forbidden not in keys, f"{forbidden} reached the model brief"
    # and no numeric VALUE beyond the house number
    for entry in seen["brief"]["grahas"] + seen["brief"]["house_overlays"]:
        assert not any(isinstance(v, int) and k != "house" for k, v in entry.items()), entry
    # corpus prose travels as corpus_text only, never as a nested object
    assert "corpus_text" not in BRIEF_FORBIDDEN


def test_the_brief_excludes_unresolved_corpus_keys_and_text():
    r = _response(LIBRA)                       # the default lookup resolves nothing
    brief = PN.build_narrative_brief(r)
    blob = json.dumps(brief, default=str)
    assert "PRATIPHALA-" not in blob, "a corpus KEY reached the brief"
    assert "corpus_text" not in blob, "an unresolved reference produced text"


def test_the_brief_includes_resolved_corpus_prose():
    PROSE_G = "ZQXGRAHAPROSEQ7"
    d1 = {g: D.FRIEND for g in Graha}
    r = build_pratiphala("tok" + "x" * 9, d1, dict(d1), {g: False for g in Graha},
                         LIBRA, lambda k: PROSE_G)
    brief = PN.build_narrative_brief(r)
    assert all(g["corpus_text"] == PROSE_G for g in brief["grahas"])
    assert all(h["corpus_text"] == PROSE_G for h in brief["house_overlays"])
    assert "PRATIPHALA-" not in json.dumps(brief, default=str)   # still no keys


def test_unknown_stays_unavailable_in_the_brief_and_invents_no_prose():
    d1 = {g: D.FRIEND for g in Graha}
    d9 = {g: D.FRIEND for g in Graha}
    d9[Graha.RAHU] = d9[Graha.KETU] = None
    r = build_pratiphala("tok" + "x" * 9, d1, d9, {g: False for g in Graha},
                         LIBRA, lambda k: "ZQXPROSEQ7")
    brief = PN.build_narrative_brief(r)
    by = {g["graha"]: g for g in brief["grahas"]}
    for node in ("Rahu", "Ketu"):
        assert by[node]["governing_state"] == "UNKNOWN"
        assert by[node]["d9_dignity"] is None
        assert by[node]["d9_sub_tier"] == "UNKNOWN"
        assert "corpus_text" not in by[node], "UNKNOWN was given invented prose"
        assert "unknown" in by[node]["basis"].lower()


def test_sovereign_reaches_the_brief_as_the_server_authored_it():
    d1 = {g: D.EXALTED for g in Graha}
    vg = {g: False for g in Graha}
    vg[Graha.VENUS] = True
    r = build_pratiphala("tok" + "x" * 9, d1, dict(d1), vg, LIBRA)
    brief = PN.build_narrative_brief(r)
    venus = [g for g in brief["grahas"] if g["graha"] == "Venus"][0]
    assert venus["governing_state"] == "Sovereign"
    assert venus["governing_state_sa"] == SOVEREIGN_SA
    # the underlying quadrant is evidence and must NOT travel
    assert "underlying_state" not in venus


def test_the_prompt_states_the_rules_the_model_must_not_break():
    p = PN.SYSTEM_PROMPT
    flat = " ".join(p.split())
    # PF-013 REPLACED THE PROMPT'S JOB. The model no longer writes the report,
    # so the prompt no longer instructs it about states — it forbids them. The
    # rules are now ENFORCED in code, and the prompt only has to stop the
    # provider wasting a call.
    # PF-013B: the prompt no longer forbids terms, because the provider no
    # longer supplies text to forbid them in. It asks for a CHOICE. The rules
    # are enforced by the enum and the template maps, not by instruction.
    for phrase in ["YOU WRITE NOTHING",
                   "introduction_id", "conclusion_id",
                   '"plain"', '"reflective"', '"practical"',
                   "any prose is rejected"]:
        assert phrase in flat, phrase


def test_unknown_token_returns_404_from_the_report_route(monkeypatch):
    monkeypatch.setattr(PR, "generate_report", lambda result, name=None: "prose")
    app = _app()
    app.dependency_overrides[get_chart_resolver] = lambda: _Recorder(raises=ChartNotFound())
    with TestClient(app) as c:
        r = c.post("/pratiphalareport", json={"chart_token": TOKEN})
    assert r.status_code == 404


@pytest.mark.parametrize("raised,expected", [
    (HTTPException(status_code=401, detail="no"), 401),
    (HTTPException(status_code=403, detail="no"), 403),
    (HTTPException(status_code=502, detail="Supabase host:5432 timed out"), 500),
    (RuntimeError("boom"), 500),
])
def test_resolver_failures_map_the_same_way_and_leak_nothing(monkeypatch, raised, expected):
    monkeypatch.setattr(PR, "generate_report", lambda result, name=None: "prose")
    app = _app()
    app.dependency_overrides[get_chart_resolver] = lambda: _Recorder(raises=raised)
    with TestClient(app) as c:
        r = c.post("/pratiphalareport", json={"chart_token": TOKEN})
    assert r.status_code == expected
    if expected == 500:
        assert "Supabase" not in r.text and "Reference:" in r.text


def test_an_invalid_certified_chart_returns_422(monkeypatch):
    monkeypatch.setattr(PR, "generate_report", lambda result, name=None: "prose")
    cap = _chart_payload()
    del cap["planets"]["Mars"]["d9_sign_index"]
    app = _app()
    app.dependency_overrides[get_chart_resolver] = lambda: _Recorder(result=cap)
    with TestClient(app) as c:
        r = c.post("/pratiphalareport", json={"chart_token": cap["chart_token"]})
    assert r.status_code == 422


def test_a_missing_api_key_is_a_controlled_500(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(HTTPException) as e:
        PN.fetch_framing({"grahas": [], "house_overlays": []})
    assert e.value.status_code == 500
    assert "ANTHROPIC_API_KEY" in str(e.value.detail)


def test_a_provider_failure_leaks_no_response_body(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")
    class _Resp:
        status_code = 500
        text = "internal-host-9 said: rate limit for org acct_SECRET"
        def json(self): return {}
    monkeypatch.setattr(PN.requests, "post", lambda *a, **k: _Resp())
    with pytest.raises(HTTPException) as e:
        PN.fetch_framing({"grahas": [], "house_overlays": []})
    assert e.value.status_code == 500
    detail = str(e.value.detail)
    assert "acct_SECRET" not in detail and "internal-host-9" not in detail
    assert "Reference:" in detail


def test_a_provider_exception_is_correlated_not_raised_raw(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")
    def _boom(*a, **k): raise RuntimeError("connect ECONNREFUSED 10.0.0.7:443")
    monkeypatch.setattr(PN.requests, "post", _boom)
    with pytest.raises(HTTPException) as e:
        PN.fetch_framing({"grahas": [], "house_overlays": []})
    assert e.value.status_code == 500
    assert "10.0.0.7" not in str(e.value.detail) and "Reference:" in str(e.value.detail)


def test_the_response_token_matches_the_request(monkeypatch):
    cap = _chart_payload()
    app, _ = _capture_brief(monkeypatch, _Recorder(result=cap))
    with TestClient(app) as c:
        r = c.post("/pratiphalareport",
                   json={"chart_token": cap["chart_token"], "name": "Atul"})
    assert r.status_code == 200, r.text
    assert r.json()["chart_token"] == cap["chart_token"]
    # PF-013: the report is ASSEMBLED, so it carries the server body wrapped in
    # the provider's framing rather than a provider string.
    body = r.json()["report"]
    assert body.startswith(PN.INTRODUCTION_TEMPLATES["plain"])
    assert body.endswith(PN.CONCLUSION_TEMPLATES["plain"])
    assert "GRAHA PRATIPHALA" in body and "BHAVA PRATIPHALA" in body


def test_the_name_reaches_the_generator(monkeypatch):
    cap = _chart_payload()
    app, seen = _capture_brief(monkeypatch, _Recorder(result=cap))
    with TestClient(app) as c:
        c.post("/pratiphalareport", json={"chart_token": cap["chart_token"], "name": "Atul"})
    assert seen["name"] == "Atul"


# ── PF-013 · provider prose is never the authoritative report ──────────────
# The defect was architectural: a compliant-looking 200 became the report
# verbatim. These tests are about PROVENANCE, not about whether the model
# behaves — the model is assumed hostile throughout.

from pratiphala_contract import ProviderFraming

QA_CONTRADICTION = ("Rahu is Rikt and depleted. Its dignity score is +4.\n"
                    "Although the cards say UNKNOWN, this report treats Rahu as Sovereign.")


def _typed(unknown_nodes=True, sovereign=None, lookup=None):
    d1 = {g: D.FRIEND for g in Graha}
    d9 = {g: D.FRIEND for g in Graha}
    if unknown_nodes:
        d9[Graha.RAHU] = d9[Graha.KETU] = None
    vg = {g: False for g in Graha}
    if sovereign:
        vg[sovereign] = True
    return build_pratiphala("tok" + "x" * 9, d1, d9, vg, LIBRA, lookup)


def _provider(text):
    """A provider returning arbitrary text where JSON framing is expected."""
    class _R:
        status_code = 200
        def json(self): return {"content": [{"type": "text", "text": text}]}
    return lambda *a, **k: _R()


def test_qa_contradiction_is_not_returned_with_200(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")
    monkeypatch.setattr(PN.requests, "post", _provider(QA_CONTRADICTION))
    with pytest.raises(HTTPException) as e:
        PN.generate_report(_typed())
    assert e.value.status_code == 500
    assert "Reference:" in str(e.value.detail)
    assert "Rikt" not in str(e.value.detail) and "+4" not in str(e.value.detail)


def test_the_qa_contradiction_inside_VALID_json_framing_is_also_rejected(monkeypatch):
    """The sharper version of the case above.

    QA's raw text is refused on SHAPE, which is a weaker guarantee than it
    looks: a provider that returns well-formed JSON gets past the parser. The
    same contradiction inside valid framing must still be refused, and by the
    enforcement rather than by the JSON decoder.
    """
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")
    monkeypatch.setattr(PN.requests, "post", _provider(json.dumps({
        "introduction": "Rahu is Rikt and depleted. Its dignity score is +4.",
        "conclusion": "Although the cards say UNKNOWN, this report treats Rahu as Sovereign."})))
    with pytest.raises(HTTPException) as e:
        PN.generate_report(_typed())
    assert e.value.status_code == 500
    for leaked in ("Rikt", "Sovereign", "+4", "depleted", "UNKNOWN"):
        assert leaked not in str(e.value.detail), leaked


def test_well_formed_framing_carrying_one_state_word_is_rejected(monkeypatch):
    """Even a single smuggled term, in otherwise innocuous prose."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")
    monkeypatch.setattr(PN.requests, "post", _provider(json.dumps({
        "introduction": "Welcome to a reading of quiet Sovereign clarity.",
        "conclusion": "Go gently."})))
    with pytest.raises(HTTPException):
        PN.generate_report(_typed())


def test_raw_provider_text_is_never_the_report(monkeypatch):
    """Even benign free text cannot become the report: it is not the shape."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")
    monkeypatch.setattr(PN.requests, "post", _provider("A lovely reading awaits you."))
    with pytest.raises(HTTPException):
        PN.generate_report(_typed())


def _assembled(typed=None, intro_id="plain", conc_id="plain"):
    from pratiphala_contract import ProviderFraming
    f = ProviderFraming(introduction_id=intro_id, conclusion_id=conc_id)
    return PN.assemble_report(typed if typed is not None else _typed(), f)


def test_the_report_has_exactly_nine_graha_and_twelve_house_sections():
    r = _typed()
    body = _assembled(r)
    for g in Graha:
        assert body.count(f"{g.value} \u2014 ") == 1, g.value
    for h in range(1, 13):
        assert f"H{h} " in body


def test_every_section_state_comes_from_the_typed_response():
    r = _typed(unknown_nodes=True, sovereign=Graha.VENUS)
    body = _assembled(r)
    for g in r.grahas:
        assert f"{g.graha.value} \u2014 {g.governing_state.value}" in body
    for o in r.house_lord_overlays:
        assert f"H{o.house} {o.house_name} \u2014 {o.verdict.governing_state.value}" in body


@pytest.mark.parametrize("smuggled", [
    "Your Rikt placements need care.",
    "A Sovereign influence guides you.",
    "Siddha energy surrounds this reading.",
    "Your chart shows an Exalted quality.",
    "This is a Vargottama reading.",
])
def test_a_provider_introducing_a_state_is_rejected(smuggled):
    """PF-013B: prose in ANY field is now an unknown field, not a value to vet."""
    with pytest.raises(ValidationError):
        ProviderFraming(introduction=smuggled, conclusion="Fine.")
    with pytest.raises(ValidationError):
        ProviderFraming(introduction_id=smuggled, conclusion_id="plain")


@pytest.mark.parametrize("smuggled", [
    "Your score is +4 overall.",
    "A rank of 6 was reached.",
    "The threshold was met.",
    "You have 3 strong placements.",
    "Rated -1 in places.",
])
def test_a_provider_introducing_scores_ranks_or_numbers_is_rejected(smuggled):
    with pytest.raises(ValidationError):
        ProviderFraming(introduction="Fine.", conclusion=smuggled)
    with pytest.raises(ValidationError):
        ProviderFraming(introduction_id="plain", conclusion_id=smuggled)


def test_every_declared_id_pair_constructs_and_selects_a_template():
    from pratiphala_contract import FramingConclusionId, FramingIntroductionId
    for i in FramingIntroductionId:
        for c in FramingConclusionId:
            f = ProviderFraming(introduction_id=i.value, conclusion_id=c.value)
            intro, conc = PN.framing_text(f)
            assert intro is PN.INTRODUCTION_TEMPLATES[i.value]
            assert conc is PN.CONCLUSION_TEMPLATES[c.value]


def test_unknown_sections_are_deterministic_and_carry_no_provider_prose():
    r = _typed(unknown_nodes=True)
    body = _assembled(r, intro_id="reflective", conc_id="practical")
    for node in ("Rahu", "Ketu"):
        i = body.index(f"{node} \u2014 ")
        section = body[i:body.index("\n\n", i)]
        assert "UNKNOWN" in section
        assert "not available" in section
        for banned in ("Rikt", "Sovereign", "depleted", "empty", "unfortunate",
                       "failed", "weak"):
            assert banned.lower() not in section.lower(), (node, banned)
        assert PN.INTRODUCTION_TEMPLATES["reflective"] not in section
        assert PN.CONCLUSION_TEMPLATES["practical"] not in section


def test_sovereign_appears_only_where_the_server_authored_it():
    r = _typed(unknown_nodes=True, sovereign=Graha.VENUS)
    body = _assembled(r)
    venus = body[body.index("Venus \u2014 "):]
    assert venus.startswith("Venus \u2014 Sovereign")
    # and nowhere near the UNKNOWN nodes
    i = body.index("Rahu \u2014 ")
    assert "Sovereign" not in body[i:body.index("\n\n", i)]
    plain = _typed(unknown_nodes=True)
    assert "Sovereign" not in _assembled(plain)


def test_resolved_corpus_prose_is_included_verbatim():
    PROSE = "ZQXCORPUSQ7 the promise ripens in its own season."
    r = _typed(unknown_nodes=False, lookup=lambda k: PROSE)
    body = _assembled(r)
    assert body.count(PROSE) >= 9


def test_an_unresolved_reference_produces_no_invented_prose():
    r = _typed(unknown_nodes=True)          # default lookup resolves nothing
    body = _assembled(r)
    assert "PRATIPHALA-" not in body        # no keys either


@pytest.mark.parametrize("bad", [
    {"introduction_id": "plain"},                                        # missing
    {"conclusion_id": "plain"},                                          # missing
    {"introduction_id": "plain", "conclusion_id": "plain", "report": "x"},   # extra
    {"introduction_id": "plain", "conclusion_id": "plain", "grahas": []},    # extra
    {"introduction_id": "", "conclusion_id": "plain"},                   # empty
    {"introduction_id": "warm", "conclusion_id": "plain"},               # unknown id
    {"introduction_id": "plain", "conclusion_id": "gentle"},             # unknown id
    {"introduction": "Fine.", "conclusion": "Fine."},                    # LEGACY prose
])
def test_missing_extra_or_empty_provider_fields_are_rejected(bad):
    with pytest.raises(ValidationError):
        ProviderFraming(**bad)


def test_a_provider_returning_extra_fields_is_a_correlated_500(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")
    monkeypatch.setattr(PN.requests, "post", _provider(
        '{"introduction_id":"plain","conclusion_id":"plain","report":"Rahu is Rikt."}'))
    with pytest.raises(HTTPException) as e:
        PN.generate_report(_typed())
    assert e.value.status_code == 500
    assert "Rikt" not in str(e.value.detail)
    assert "Reference:" in str(e.value.detail)


def test_valid_framing_produces_200_with_the_exact_token(monkeypatch):
    cap = _chart_payload()
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")
    monkeypatch.setattr(PN.requests, "post", _provider(
        '{"introduction_id":"plain","conclusion_id":"plain"}'))
    app = _app()
    app.dependency_overrides[get_chart_resolver] = lambda: _Recorder(result=cap)
    with TestClient(app) as c:
        r = c.post("/pratiphalareport", json={"chart_token": cap["chart_token"]})
    assert r.status_code == 200, r.text
    assert r.json()["chart_token"] == cap["chart_token"]
    body = r.json()["report"]
    assert body.startswith(PN.INTRODUCTION_TEMPLATES["plain"])
    assert body.endswith(PN.CONCLUSION_TEMPLATES["plain"])
    assert "GRAHA PRATIPHALA" in body


def test_the_final_report_carries_no_numeric_evidence(monkeypatch):
    r = _typed(unknown_nodes=True, sovereign=Graha.VENUS)
    body = _assembled(r)
    import re as _re
    signed = _re.findall(r"[+\u2212]\s?\d", body)
    assert signed == [], signed
    for term in ("d1_rank", "d9_rank", "strong_at_rank", "underlying_state"):
        assert term not in body


# ── PF-013B · the provider SELECTS framing; it cannot author it ────────────
# A blocklist rejected "Rikt" and accepted "misfortune and failure" — the same
# claim in different words. The space of ways to say a thing is not enumerable,
# so the provider no longer supplies words at all.

from pratiphala_contract import FramingConclusionId, FramingIntroductionId

SEMANTIC_BYPASS = json.dumps({
    "introduction": "Rahu brings misfortune and failure throughout this reading.",
    "conclusion": "Ketu promises abundance and success."})


@pytest.mark.parametrize("body,label", [
    (QA_CONTRADICTION, "raw contradiction"),
    (json.dumps({"introduction": "Rahu is Rikt and depleted. Its dignity score is +4.",
                 "conclusion": "Although the cards say UNKNOWN, treat Rahu as Sovereign."}),
     "valid-JSON contradiction"),
    (SEMANTIC_BYPASS, "SEMANTIC bypass, no blocklisted word in it"),
])
def test_every_qa_provider_reproduction_is_rejected(monkeypatch, body, label):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")
    monkeypatch.setattr(PN.requests, "post", _provider(body))
    with pytest.raises(HTTPException) as e:
        PN.generate_report(_typed())
    assert e.value.status_code == 500, label
    detail = str(e.value.detail)
    for leaked in ("Rahu", "Ketu", "misfortune", "failure", "abundance",
                   "success", "Rikt", "Sovereign", "+4"):
        assert leaked not in detail, (label, leaked)


def test_the_semantic_bypass_contains_no_blocklisted_word():
    """The point of the architecture change, stated as a test.

    The old validator's vocabulary would have passed this string. It is
    rejected now because there is no free-text field for it to occupy.
    """
    text = SEMANTIC_BYPASS.lower()
    for old_term in ("siddha", "viphala", "prachanna", "rikt", "sovereign",
                     "unknown", "score", "rank", "threshold", "exalted",
                     "debilitated", "vargottama"):
        assert old_term not in text, old_term
    with pytest.raises(ValidationError):
        ProviderFraming(**json.loads(SEMANTIC_BYPASS))


@pytest.mark.parametrize("prose_field", [
    {"introduction": "Anything at all.", "conclusion": "Anything at all."},
    {"introduction_id": "plain", "conclusion_id": "plain",
     "introduction": "and some prose"},
    {"introduction_id": "plain", "conclusion_id": "plain", "conclusion": "more prose"},
])
def test_any_free_text_framing_field_is_rejected(prose_field):
    with pytest.raises(ValidationError):
        ProviderFraming(**prose_field)


@pytest.mark.parametrize("intro", [i.value for i in FramingIntroductionId])
@pytest.mark.parametrize("conc", [c.value for c in FramingConclusionId])
def test_only_declared_ids_are_accepted_and_they_select_server_text(intro, conc):
    f = ProviderFraming(introduction_id=intro, conclusion_id=conc)
    body = PN.assemble_report(_typed(), f)
    assert body.startswith(PN.INTRODUCTION_TEMPLATES[intro])
    assert body.endswith(PN.CONCLUSION_TEMPLATES[conc])


@pytest.mark.parametrize("bad", ["warm", "PLAIN", "plain ", "", "reflective2",
                                 "Rahu brings misfortune", 1, None, True])
def test_unknown_ids_are_rejected(bad):
    with pytest.raises(ValidationError):
        ProviderFraming(introduction_id=bad, conclusion_id="plain")
    with pytest.raises(ValidationError):
        ProviderFraming(introduction_id="plain", conclusion_id=bad)


def test_no_provider_returned_prose_appears_anywhere_in_the_report(monkeypatch):
    """The whole point: the provider's own words reach nothing."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")
    # a provider returning VALID ids alongside prose it hopes will be used
    monkeypatch.setattr(PN.requests, "post", _provider(json.dumps({
        "introduction_id": "plain", "conclusion_id": "plain"})))
    body = PN.generate_report(_typed())
    for phrase in ["misfortune", "abundance", "Anything at all", "ZQXPROVIDERQ7"]:
        assert phrase not in body


def test_the_templates_carry_no_astrological_content():
    """Checked once, here, instead of by a blocklist on every request."""
    banned = ("siddha", "viphala", "prachanna", "rikt", "sovereign",
              "exalted", "debilitated", "moolatrikona", "vargottama",
              "uttama", "madhya", "alpa", "score", "rank", "threshold",
              "dignity", "rahu", "ketu", "graha", "bhava", "house")
    for name, table in (("intro", PN.INTRODUCTION_TEMPLATES),
                        ("conc", PN.CONCLUSION_TEMPLATES)):
        for key, text in table.items():
            low = text.lower()
            for term in banned:
                assert term not in low, (name, key, term)
            assert not re.search(r"\d", text), (name, key, "numeral")
            # no substitution slots: nothing external can be interpolated
            assert "{" not in text and "%" not in text and "$" not in text


def test_the_request_name_never_reaches_the_report(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")
    monkeypatch.setattr(PN.requests, "post", _provider(json.dumps({
        "introduction_id": "reflective", "conclusion_id": "practical"})))
    body = PN.generate_report(_typed(), name="ZQXNAMEQ7")
    assert "ZQXNAMEQ7" not in body


def test_the_body_is_unchanged_by_the_framing_change():
    r = _typed(unknown_nodes=True, sovereign=Graha.VENUS)
    for intro in FramingIntroductionId:
        body = PN.assemble_report(r, ProviderFraming(
            introduction_id=intro.value, conclusion_id="plain"))
        for g in Graha:
            assert body.count(f"{g.value} \u2014 ") == 1
        for h in range(1, 13):
            assert f"H{h} " in body
        for g in r.grahas:
            assert f"{g.graha.value} \u2014 {g.governing_state.value}" in body
        assert "Venus \u2014 Sovereign" in body
        i = body.index("Rahu \u2014 ")
        section = body[i:body.index("\n\n", i)]
        assert "UNKNOWN" in section and "Sovereign" not in section


def test_resolved_corpus_prose_remains_verbatim_under_the_new_framing():
    PROSE = "ZQXCORPUSQ7 the promise ripens in its own season."
    r = _typed(unknown_nodes=False, lookup=lambda k: PROSE)
    body = PN.assemble_report(r, ProviderFraming(
        introduction_id="practical", conclusion_id="reflective"))
    assert body.count(PROSE) >= 9
