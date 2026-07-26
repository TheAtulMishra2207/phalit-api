"""
test_d1_routes.py — KAR-093 step 6a: POST /d1/prepare and the chart adapter.

Backend only. No frontend change is exercised here.
"""
import asyncio
import copy
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from datetime import datetime, timedelta, timezone

from d1_chart_adapter import (
    CERTIFIED_DIGNITY, REQUIRED_CALCULATION_META, ChartAdapterError,
    UNREACHABLE_FROM_LIVE_ENGINE, map_dignity, to_certified_chart,
)
from d1_chart_store import (
    CREATE_TABLE_SQL, CallerIdentity, DbChartResolver, InMemorySnapshotStore,
    hash_token, issue_chart_response, mint_token, persist_chart_snapshot,
    revoke_chart_token,
)
from d1_contract import Dignity, Graha
from d1_routes import ChartNotFound, get_chart_resolver, router
from test_d1_engine import founder_chart


# ── a certified /chart body in the exact shape main_live.py returns ─────────

SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra",
         "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
LIVE_DIGNITY = {   # certified strings, not contract enum values
    Graha.SUN: "Neutral Sign (Sama)", Graha.MOON: "Neutral Sign (Sama)",
    Graha.MARS: "Neutral Sign (Sama)", Graha.MERCURY: "Friendly Sign (Mitra)",
    Graha.JUPITER: "Own Sign (Swa)", Graha.VENUS: "Neutral Sign (Sama)",
    Graha.SATURN: "Exalted (Uccha)", Graha.RAHU: "Node", Graha.KETU: "Node",
}

def certified_body():
    c = founder_chart()
    planets = {}
    for g, cg in c.grahas.items():
        planets[g.value] = {
            "sign": SIGNS[cg.sign_index], "sign_index": cg.sign_index,
            "house": ((cg.sign_index - c.lagna_sign_index) % 12) + 1,
            "degree": cg.degree_in_sign, "longitude": cg.longitude,
            "speed": 0.5, "retrograde": cg.retrograde,
            "nakshatra": "Chitra", "nakshatra_lord": "Mars", "nakshatra_pada": 3,
            "dignity": LIVE_DIGNITY[g],
        }
    return {
        "input": {"date": "1984-07-22"},
        "calculation_meta": dict(REQUIRED_CALCULATION_META),
        "lagna": {"sign": "Libra", "sign_index": c.lagna_sign_index,
                  "degree": c.lagna_degree},
        "planets": planets,
        "houses": {}, "dasha": {},
    }


class StubResolver:
    def __init__(self, body=None, raises=None):
        self.body, self.raises = body, raises
    async def resolve(self, chart_token):
        if self.raises:
            raise self.raises
        return self.body


def make_client(resolver):
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_chart_resolver] = lambda: resolver
    return TestClient(app)


# ── adapter: dignity vocabulary is the live engine's, and fails closed ──────

def test_certified_vocabulary_is_exactly_the_live_engine_strings():
    assert set(CERTIFIED_DIGNITY) == {
        "Exalted (Uccha)", "Moolatrikona", "Own Sign (Swa)", "Friendly Sign (Mitra)",
        "Neutral Sign (Sama)", "Enemy Sign (Shatru)", "Debilitated (Neecha)", "Node",
    }

def test_node_sentinel_is_not_a_dignity():
    assert map_dignity("Node") is None

def test_exalted_and_debilitated_nodes_are_carried_through():
    """BPHS Ch.47: Rahu exalts in Taurus, Ketu in Scorpio. The certified engine
    emits real dignity for those, and it must not be discarded."""
    assert map_dignity("Exalted (Uccha)") == Dignity.EXALTED
    assert map_dignity("Debilitated (Neecha)") == Dignity.DEBILITATED

def test_great_friend_and_great_enemy_are_unreachable_from_the_live_engine():
    """The certified engine has no panchadha-maitri layer, so these two contract
    values cannot arise today. Asserted rather than assumed."""
    assert UNREACHABLE_FROM_LIVE_ENGINE == {Dignity.GREAT_FRIEND, Dignity.GREAT_ENEMY}
    assert not (set(CERTIFIED_DIGNITY.values()) & UNREACHABLE_FROM_LIVE_ENGINE)

def test_unknown_dignity_fails_closed():
    for bad in ("Great Friend", "Adhi Mitra", "exalted", "", 3):
        with pytest.raises(ChartAdapterError):
            map_dignity(bad)

def test_adapter_translates_the_founder_chart():
    cc = to_certified_chart(certified_body(), "tok_abcdefgh")
    assert cc.lagna_sign_index == 6
    assert cc.grahas[Graha.SATURN].dignity == Dignity.EXALTED
    assert cc.grahas[Graha.RAHU].dignity is None

def test_adapter_rejects_missing_pieces():
    for drop in ("lagna", "planets"):
        body = certified_body(); del body[drop]
        with pytest.raises(ChartAdapterError):
            to_certified_chart(body, "tok_abcdefgh")
    body = certified_body(); del body["planets"]["Ketu"]
    with pytest.raises(ChartAdapterError, match="Ketu"):
        to_certified_chart(body, "tok_abcdefgh")
    body = certified_body(); del body["planets"]["Sun"]["longitude"]
    with pytest.raises(ChartAdapterError, match="longitude"):
        to_certified_chart(body, "tok_abcdefgh")


# ── route behaviour ────────────────────────────────────────────────────────

def test_prepare_returns_the_full_payload():
    client = make_client(StubResolver(certified_body()))
    r = client.post("/d1/prepare", json={"chart_token": "tok_abcdefgh"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["chart_token"] == "tok_abcdefgh"
    assert len(body["d1"]["aspects"]) == 13
    assert len(body["drawers"]["drawers"]) == 9
    assert body["doctrine"]["orthogonal_roles_publishable"] is True
    assert body["doctrine"]["legacy_flat_roles_publishable"] is False
    assert body["calculation_meta"]["ephemeris_backend"] == "swisseph"
    assert body["calculation_meta"]["chart_engine_version"] == "1.1.0"

def test_unknown_token_is_404():
    client = make_client(StubResolver(raises=ChartNotFound()))
    r = client.post("/d1/prepare", json={"chart_token": "tok_missing1"})
    assert r.status_code == 404
    assert "expired" in r.json()["detail"]

def test_untranslatable_chart_is_422_with_a_reference():
    body = certified_body()
    body["planets"]["Sun"]["dignity"] = "Great Friend"      # not a live value
    client = make_client(StubResolver(body))
    r = client.post("/d1/prepare", json={"chart_token": "tok_abcdefgh"})
    assert r.status_code == 422
    assert "Reference:" in r.json()["detail"]

def test_missing_dignity_is_422_not_a_guess():
    """KAR-080: the engine refuses to invent dignity."""
    body = certified_body()
    body["planets"]["Jupiter"]["dignity"] = "Node"          # -> None for a caster
    client = make_client(StubResolver(body))
    r = client.post("/d1/prepare", json={"chart_token": "tok_abcdefgh"})
    assert r.status_code == 422
    assert "does not compute dignity" in r.json()["detail"]

@pytest.mark.parametrize("bad_token", [12345678, 1234.5678, True, False, None,
                                       ["tok_abcdefgh"], {"t": "tok_abcdefgh"}])
def test_non_string_chart_token_is_422_not_coerced(bad_token):
    """pydantic v1 coerces a JSON number to a string, so {"chart_token":
    12345678} was accepted as "12345678" and deferred a malformed request to a
    token lookup and a 404. StrictStr keeps it an immediate 422, matching v2."""
    client = make_client(StubResolver(certified_body()))
    r = client.post("/d1/prepare", json={"chart_token": bad_token})
    assert r.status_code == 422, (bad_token, r.text)

def test_valid_string_token_still_accepted():
    client = make_client(StubResolver(certified_body()))
    assert client.post("/d1/prepare", json={"chart_token": "tok_abcdefgh"}).status_code == 200
    # boundary: exactly eight characters is the documented minimum
    r = client.post("/d1/prepare", json={"chart_token": "12345678"})
    assert r.status_code in (200, 404), r.text     # well-formed; resolution is separate

def test_request_model_rejects_numeric_tokens_directly():
    from d1_routes import D1PrepareRequest
    import pydantic
    for bad in (12345678, 1234.5678, True):
        with pytest.raises(pydantic.ValidationError):
            D1PrepareRequest(chart_token=bad)
    assert D1PrepareRequest(chart_token="tok_abcdefgh").chart_token == "tok_abcdefgh"

def test_malformed_request_is_422():
    client = make_client(StubResolver(certified_body()))
    assert client.post("/d1/prepare", json={}).status_code == 422
    assert client.post("/d1/prepare", json={"chart_token": "short"}).status_code == 422

def test_unconfigured_resolver_returns_503_not_a_fallback():
    """No silent default store may exist."""
    app = FastAPI(); app.include_router(router)
    client = TestClient(app, raise_server_exceptions=False)
    r = client.post("/d1/prepare", json={"chart_token": "tok_abcdefgh"})
    assert r.status_code == 503
    assert "not configured" in r.json()["detail"]

def test_route_is_deterministic():
    client = make_client(StubResolver(certified_body()))
    a = client.post("/d1/prepare", json={"chart_token": "tok_abcdefgh"}).json()
    b = client.post("/d1/prepare", json={"chart_token": "tok_abcdefgh"}).json()
    for blob in (a, b):
        blob["d1"].pop("generated_at", None)
    assert a == b

def test_payload_carries_no_html_or_harm_framing():
    client = make_client(StubResolver(certified_body()))
    text = client.post("/d1/prepare", json={"chart_token": "tok_abcdefgh"}).text
    for marker in ("<div", "<p>", "<strong", "kar091", "harm_categories"):
        assert marker not in text


# ── QA step-6a HIGH-1: certified provenance gate ───────────────────────────

def test_missing_calculation_meta_is_422():
    body = certified_body(); del body["calculation_meta"]
    r = make_client(StubResolver(body)).post("/d1/prepare", json={"chart_token": "tok_abcdefgh"})
    assert r.status_code == 422 and "provenance" in r.json()["detail"]

@pytest.mark.parametrize("key,bad", [
    ("chart_engine_version", "0.9.0"),
    ("ephemeris_backend", "moshier"),
    ("ayanamsha_model", "lahiri-2020"),
    ("house_system", "placidus"),
    ("node_type", "true"),
])
def test_wrong_provenance_is_422(key, bad):
    body = certified_body(); body["calculation_meta"][key] = bad
    r = make_client(StubResolver(body)).post("/d1/prepare", json={"chart_token": "tok_abcdefgh"})
    assert r.status_code == 422
    assert key in r.json()["detail"]

def test_provenance_gate_is_the_frozen_certificate():
    assert REQUIRED_CALCULATION_META == {
        "chart_engine_version": "1.1.0",
        "ayanamsha_model": "lahiri-linear-fit-2026-07",
        "house_system": "whole-sign",
        "node_type": "mean",
        "ephemeris_backend": "swisseph",
    }


# ── QA step-6a HIGH-2: no error path bypasses correlation handling ─────────

@pytest.mark.parametrize("field,bad", [("sign_index", 99), ("longitude", 400.0),
                                       ("degree", 45.0)])
def test_out_of_range_certified_values_are_422_with_reference(field, bad):
    body = certified_body(); body["planets"]["Sun"][field] = bad
    r = make_client(StubResolver(body)).post("/d1/prepare", json={"chart_token": "tok_abcdefgh"})
    assert r.status_code == 422, r.text
    assert "Reference:" in r.json()["detail"]

def test_non_object_lagna_is_422_with_reference():
    body = certified_body(); body["lagna"] = "Libra"
    r = make_client(StubResolver(body)).post("/d1/prepare", json={"chart_token": "tok_abcdefgh"})
    assert r.status_code == 422 and "Reference:" in r.json()["detail"]

def test_non_object_planet_entry_is_422_with_reference():
    body = certified_body(); body["planets"]["Sun"] = "bad"
    r = make_client(StubResolver(body)).post("/d1/prepare", json={"chart_token": "tok_abcdefgh"})
    assert r.status_code == 422 and "Reference:" in r.json()["detail"]

def test_resolver_infrastructure_failure_is_500_with_reference():
    class Exploding:
        async def resolve(self, chart_token): raise RuntimeError("db down")
    client = TestClient(make_client(Exploding()).app, raise_server_exceptions=False)
    r = client.post("/d1/prepare", json={"chart_token": "tok_abcdefgh"})
    assert r.status_code == 500
    assert "Reference:" in r.json()["detail"]
    assert "db down" not in r.text          # internals are not leaked

def test_resolver_may_raise_deliberate_http_statuses():
    from fastapi import HTTPException as HE
    class Unauthorised:
        async def resolve(self, chart_token): raise HE(status_code=401, detail="nope")
    r = make_client(Unauthorised()).post("/d1/prepare", json={"chart_token": "tok_abcdefgh"})
    assert r.status_code == 401


# ── DB-backed snapshot store: fail-closed resolution ───────────────────────

def _store_with_snapshot(caller, ttl=timedelta(minutes=30), now=None):
    store = InMemorySnapshotStore()
    token = asyncio.run(persist_chart_snapshot(store, certified_body(), caller, ttl=ttl, now=now))
    return store, token

def _run(coro):
    return asyncio.run(coro)

def test_token_is_high_entropy_and_only_the_hash_is_stored():
    caller = CallerIdentity(user_id="u1")
    store, token = _store_with_snapshot(caller)
    assert len(token) >= 32
    assert mint_token() != mint_token()
    row = next(iter(store.rows.values()))
    assert row["chart_token_hash"] == hash_token(token)
    assert token not in str(row)            # the raw token is never persisted

def test_snapshot_resolves_for_its_owner():
    caller = CallerIdentity(user_id="u1")
    store, token = _store_with_snapshot(caller)
    body = _run(DbChartResolver(store, caller).resolve(token))
    assert body["lagna"]["sign_index"] == 6

def test_unknown_token_fails_closed():
    caller = CallerIdentity(user_id="u1")
    store, _ = _store_with_snapshot(caller)
    with pytest.raises(ChartNotFound):
        _run(DbChartResolver(store, caller).resolve("not-a-real-token"))

def test_expired_token_fails_closed():
    caller = CallerIdentity(user_id="u1")
    past = datetime.now(timezone.utc) - timedelta(hours=2)
    store, token = _store_with_snapshot(caller, ttl=timedelta(minutes=30), now=past)
    with pytest.raises(ChartNotFound):
        _run(DbChartResolver(store, caller).resolve(token))

def test_revoked_token_fails_closed():
    """Revocation goes through the store PORT, never by mutating internals."""
    caller = CallerIdentity(user_id="u1")
    store, token = _store_with_snapshot(caller)
    assert _run(revoke_chart_token(store, token)) is True
    with pytest.raises(ChartNotFound):
        _run(DbChartResolver(store, caller).resolve(token))

def test_cross_owner_token_fails_closed():
    owner = CallerIdentity(user_id="u1")
    store, token = _store_with_snapshot(owner)
    for intruder in (CallerIdentity(user_id="u2"), CallerIdentity(session_id="s9")):
        with pytest.raises(ChartNotFound):
            _run(DbChartResolver(store, intruder).resolve(token))

def test_anonymous_session_binding_is_enforced():
    s1, s2 = CallerIdentity(session_id="sess-1"), CallerIdentity(session_id="sess-2")
    store, token = _store_with_snapshot(s1)
    assert _run(DbChartResolver(store, s1).resolve(token))["lagna"]["sign_index"] == 6
    with pytest.raises(ChartNotFound):
        _run(DbChartResolver(store, s2).resolve(token))

def test_caller_requires_an_identity():
    with pytest.raises(ValueError):
        CallerIdentity()

def test_in_memory_store_is_marked_not_production_safe():
    assert InMemorySnapshotStore.production_safe is False

def _app_with_chart_endpoint(store, caller):
    """A FastAPI app exposing BOTH endpoints, so the production flow is
    exercised for real: POST /chart mints the token, POST /d1/prepare
    resolves it. /chart here calls issue_chart_response — the same function
    main.py will call — over a certified body."""
    app = FastAPI()

    @app.post("/chart")
    async def chart():
        return await issue_chart_response(certified_body(), store, caller)

    app.include_router(router)
    app.dependency_overrides[get_chart_resolver] = lambda: DbChartResolver(store, caller)
    return TestClient(app)

def test_chart_mints_a_token_that_d1_prepare_resolves():
    """POST /chart -> chart_token -> POST /d1/prepare, end to end."""
    store, caller = InMemorySnapshotStore(), CallerIdentity(user_id="u1")
    client = _app_with_chart_endpoint(store, caller)

    chart = client.post("/chart").json()
    assert "chart_token" in chart
    token = chart["chart_token"]
    # the rest of the /chart response is unchanged
    assert chart["lagna"]["sign_index"] == 6
    assert chart["calculation_meta"]["ephemeris_backend"] == "swisseph"

    r = client.post("/d1/prepare", json={"chart_token": token})
    assert r.status_code == 200, r.text
    assert len(r.json()["drawers"]["drawers"]) == 9
    assert len(r.json()["d1"]["aspects"]) == 13

def test_chart_persists_the_exact_snapshot_not_a_recomputation():
    store, caller = InMemorySnapshotStore(), CallerIdentity(user_id="u1")
    client = _app_with_chart_endpoint(store, caller)
    chart = client.post("/chart").json()
    row = store.rows[hash_token(chart["chart_token"])]
    stored = row["chart_payload"]
    assert stored["planets"] == certified_body()["planets"]
    assert row["calculation_meta"] == certified_body()["calculation_meta"]
    assert "chart_token" not in stored          # the token is not inside its own snapshot

def test_each_chart_call_mints_a_distinct_token():
    store, caller = InMemorySnapshotStore(), CallerIdentity(user_id="u1")
    client = _app_with_chart_endpoint(store, caller)
    a = client.post("/chart").json()["chart_token"]
    b = client.post("/chart").json()["chart_token"]
    assert a != b and len(store.rows) == 2

def test_revoked_token_stops_resolving_through_the_route():
    """Revocation via the PORT, not by mutating store internals."""
    store, caller = InMemorySnapshotStore(), CallerIdentity(user_id="u1")
    client = _app_with_chart_endpoint(store, caller)
    token = client.post("/chart").json()["chart_token"]
    assert client.post("/d1/prepare", json={"chart_token": token}).status_code == 200
    assert _run(revoke_chart_token(store, token)) is True
    r = client.post("/d1/prepare", json={"chart_token": token})
    assert r.status_code == 404

def test_revocation_is_one_way_and_idempotent():
    store, caller = InMemorySnapshotStore(), CallerIdentity(user_id="u1")
    token = _run(persist_chart_snapshot(store, certified_body(), caller))
    assert _run(revoke_chart_token(store, token)) is True
    assert _run(revoke_chart_token(store, token)) is False
    assert _run(revoke_chart_token(store, "no-such-token")) is False


# ── database-enforced immutability (QA step-6a v2 HIGH-2) ──────────────────

def test_sql_enforces_immutability_with_a_trigger():
    for fragment in ("chart_snapshots_guard_trg", "BEFORE UPDATE",
                     "rows are immutable", "revocation is one-way"):
        assert fragment in CREATE_TABLE_SQL

def test_sql_guards_every_field_except_revoked_at():
    protected = ("chart_token_hash", "owner_user_id", "session_id",
                 "chart_payload", "calculation_meta", "created_at", "expires_at")
    guard = CREATE_TABLE_SQL[CREATE_TABLE_SQL.index("chart_snapshots_guard()"):]
    for col in protected:
        assert f"NEW.{col}" in guard, col
    assert "NEW.revoked_at IS DISTINCT FROM OLD.revoked_at" in guard

def test_sql_enforces_owner_xor_and_positive_ttl():
    assert "chart_snapshots_owner_xor" in CREATE_TABLE_SQL
    assert "chart_snapshots_ttl_positive" in CREATE_TABLE_SQL


# ── strict certified types (QA step-6a v2 HIGH-1) ──────────────────────────

@pytest.mark.parametrize("field,bad", [
    ("sign_index", "6"), ("sign_index", 6.0), ("sign_index", True),
    ("degree", "5.9"), ("degree", True),
    ("longitude", "95.9"), ("longitude", True),
])
def test_string_and_bool_certified_values_are_rejected(field, bad):
    body = certified_body(); body["planets"]["Sun"][field] = bad
    with pytest.raises(ChartAdapterError):
        to_certified_chart(body, "tok_abcdefgh")

@pytest.mark.parametrize("bad", ["false", "true", 0, 1, None])
def test_retrograde_must_be_a_real_boolean(bad):
    """bool('false') is True — coercion here silently reverses the chart."""
    body = certified_body(); body["planets"]["Sun"]["retrograde"] = bad
    with pytest.raises(ChartAdapterError, match="boolean"):
        to_certified_chart(body, "tok_abcdefgh")

def test_combust_must_be_a_real_boolean():
    body = certified_body(); body["planets"]["Sun"]["combust"] = "yes"
    with pytest.raises(ChartAdapterError, match="boolean"):
        to_certified_chart(body, "tok_abcdefgh")

@pytest.mark.parametrize("bad", ["3", 3.0, True])
def test_nakshatra_pada_must_be_an_integer_when_present(bad):
    body = certified_body(); body["planets"]["Sun"]["nakshatra_pada"] = bad
    with pytest.raises(ChartAdapterError, match="integer"):
        to_certified_chart(body, "tok_abcdefgh")

def test_lagna_fields_are_strictly_typed():
    for field, bad in (("sign_index", "6"), ("degree", "20.05")):
        body = certified_body(); body["lagna"][field] = bad
        with pytest.raises(ChartAdapterError):
            to_certified_chart(body, "tok_abcdefgh")

def test_valid_booleans_still_pass():
    body = certified_body()
    body["planets"]["Sun"]["retrograde"] = True
    body["planets"]["Sun"]["combust"] = False
    assert to_certified_chart(body, "tok_abcdefgh").grahas[Graha.SUN].retrograde is True


# ── caller identity XOR and TTL ────────────────────────────────────────────

def test_caller_identity_requires_exactly_one_key():
    CallerIdentity(user_id="u1")
    CallerIdentity(session_id="s1")
    with pytest.raises(ValueError):
        CallerIdentity()
    with pytest.raises(ValueError):
        CallerIdentity(user_id="u1", session_id="s1")

@pytest.mark.parametrize("ttl", [timedelta(0), timedelta(seconds=-1)])
def test_non_positive_ttl_is_rejected(ttl):
    store, caller = InMemorySnapshotStore(), CallerIdentity(user_id="u1")
    with pytest.raises(ValueError, match="positive"):
        _run(persist_chart_snapshot(store, certified_body(), caller, ttl=ttl))


# ── QA step-6a v4: resolver upstream failures must not leak (route level) ───

def _client_with_failing_supabase(exc):
    """A REAL SupabaseSnapshotStore whose injected request_fn fails, resolved
    through the route — the path the adapter-only tests did not exercise."""
    from d1_snapshot_supabase import SupabaseSnapshotStore
    async def boom(*a, **kw):
        raise exc
    store = SupabaseSnapshotStore(request_fn=boom)
    caller = CallerIdentity(user_id="u1")
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_chart_resolver] = lambda: DbChartResolver(store, caller)
    return TestClient(app, raise_server_exceptions=False)

@pytest.mark.parametrize("status_code,leak", [
    (503, "Could not reach Supabase: secret-host:5432 timed out"),
    (502, "Supabase rejected request: relation chart_snapshots does not exist"),
])
def test_supabase_failure_is_correlated_500_without_upstream_detail(status_code, leak):
    from fastapi import HTTPException as HE
    client = _client_with_failing_supabase(HE(status_code=status_code, detail=leak))
    r = client.post("/d1/prepare", json={"chart_token": "tok_abcdefgh"})
    assert r.status_code == 500, r.text
    detail = r.json()["detail"]
    assert "Reference:" in detail
    assert leak not in r.text
    for fragment in ("Supabase", "secret-host", "5432", "chart_snapshots"):
        assert fragment not in r.text, fragment

@pytest.mark.parametrize("status_code", [401, 403])
def test_deliberate_auth_statuses_still_pass_through(status_code):
    from fastapi import HTTPException as HE
    client = _client_with_failing_supabase(HE(status_code=status_code, detail="nope"))
    r = client.post("/d1/prepare", json={"chart_token": "tok_abcdefgh"})
    assert r.status_code == status_code

def test_unconfigured_resolver_503_is_unaffected():
    """That dependency fails before the handler runs, so it is not correlated."""
    app = FastAPI(); app.include_router(router)
    r = TestClient(app, raise_server_exceptions=False).post(
        "/d1/prepare", json={"chart_token": "tok_abcdefgh"})
    assert r.status_code == 503 and "not configured" in r.json()["detail"]

def test_404_for_a_missing_row_is_not_correlated_away():
    """A genuinely absent snapshot must still read as 404, not 500."""
    from d1_snapshot_supabase import SupabaseSnapshotStore
    import httpx as _httpx
    async def empty(*a, **kw):
        return _httpx.Response(200, json=[])
    store = SupabaseSnapshotStore(request_fn=empty)
    caller = CallerIdentity(user_id="u1")
    app = FastAPI(); app.include_router(router)
    app.dependency_overrides[get_chart_resolver] = lambda: DbChartResolver(store, caller)
    r = TestClient(app).post("/d1/prepare", json={"chart_token": "tok_abcdefgh"})
    assert r.status_code == 404


# ── QA step-6b: anonymous ownership is server-issued AND verifiable ────────

SECRET = "test-session-secret"

def _wiring():
    import d1_wiring as w
    w.configure_session_secret(SECRET)
    w.configure_caller(None)
    return w

def test_anonymous_session_is_server_issued_and_binds_both_requests():
    import asyncio as _a
    from d1_chart_store import issue_chart_response
    w = _wiring()
    store = InMemorySnapshotStore()

    cc = _a.run(w.chart_caller(x_phalit_session=None))
    assert cc.echo_session and cc.echo_session.startswith("anon_")
    body = _a.run(issue_chart_response(certified_body(), store, cc.caller,
                                       echo_session=cc.echo_session))
    assert body["anon_session"] == cc.echo_session
    token, session = body["chart_token"], body["anon_session"]

    caller_ok = _a.run(w.current_caller(x_phalit_session=session))
    assert _a.run(DbChartResolver(store, caller_ok).resolve(token))["lagna"]["sign_index"] == 6

    other_cc = _a.run(w.chart_caller(x_phalit_session=None))     # a different visitor
    other = _a.run(w.current_caller(x_phalit_session=other_cc.echo_session))
    with pytest.raises(ChartNotFound):
        _a.run(DbChartResolver(store, other).resolve(token))

@pytest.mark.parametrize("invented", ["anon_existing", "probe-1", "sess-abc",
                                      "anon_nonce.deadbeef", "anon_"])
def test_client_invented_sessions_are_refused_at_both_endpoints(invented):
    """A prefix and a length prove nothing. Only a token this server signed is
    an identity; anything else is a claim to own someone else's snapshots."""
    import asyncio as _a
    from fastapi import HTTPException as HE
    w = _wiring()
    for dep in (w.chart_caller, w.current_caller):
        with pytest.raises(HE) as exc:
            _a.run(dep(x_phalit_session=invented))
        assert exc.value.status_code == 400, (dep.__name__, invented)

def test_empty_session_header_is_treated_as_absent_not_as_an_identity():
    """An empty header is no header: /chart issues one, /d1/prepare refuses."""
    import asyncio as _a
    from fastapi import HTTPException as HE
    w = _wiring()
    assert _a.run(w.chart_caller(x_phalit_session="")).echo_session is not None
    with pytest.raises(HE) as exc:
        _a.run(w.current_caller(x_phalit_session=""))
    assert exc.value.status_code == 400

def test_session_token_is_hmac_verifiable():
    from d1_chart_store import mint_session_token, verify_session_token
    t = mint_session_token(SECRET)
    assert verify_session_token(t, SECRET)
    assert not verify_session_token(t, "a-different-secret")
    assert not verify_session_token(t[:-1] + ("0" if t[-1] != "0" else "1"), SECRET)
    assert not verify_session_token("anon_existing", SECRET)
    assert mint_session_token(SECRET) != mint_session_token(SECRET)

def test_anonymous_flow_fails_closed_without_a_configured_secret(monkeypatch):
    import asyncio as _a
    from fastapi import HTTPException as HE
    import d1_wiring as w
    w.configure_session_secret(None)
    monkeypatch.delenv("D1_SESSION_SECRET", raising=False)
    try:
        with pytest.raises(HE) as exc:
            _a.run(w.chart_caller(x_phalit_session=None))
        assert exc.value.status_code == 503
    finally:
        w.configure_session_secret(SECRET)

def test_d1_prepare_never_mints_a_session():
    import asyncio as _a
    from fastapi import HTTPException as HE
    w = _wiring()
    with pytest.raises(HE) as exc:
        _a.run(w.current_caller(x_phalit_session=None))
    assert exc.value.status_code == 400 and "anon_session" in exc.value.detail

def test_chart_reuses_a_valid_issued_session_rather_than_reissuing():
    import asyncio as _a
    w = _wiring()
    issued = _a.run(w.chart_caller(x_phalit_session=None)).echo_session
    again = _a.run(w.chart_caller(x_phalit_session=issued))
    assert again.caller.session_id == issued and again.echo_session is None

def test_authenticated_caller_gets_no_anonymous_session():
    import asyncio as _a
    w = _wiring()
    class _U: user_id = "u-42"
    w.configure_caller(lambda: _U())
    try:
        cc = _a.run(w.chart_caller(x_phalit_session=None))
        assert cc.caller.user_id == "u-42" and cc.echo_session is None
    finally:
        w.configure_caller(None)


# ── QA step-6b: auth failure must never downgrade to anonymous ─────────────

@pytest.mark.parametrize("boom", [
    RuntimeError("auth db down"),
    ConnectionError("auth service unreachable"),
])
def test_auth_infrastructure_failure_propagates(boom):
    """An outage previously became user=None, minting an anonymous session and
    persisting an authenticated user's chart under the wrong owner."""
    import asyncio as _a
    w = _wiring()
    def raiser(): raise boom
    w.configure_caller(raiser)
    try:
        with pytest.raises(type(boom)):
            _a.run(w.chart_caller(x_phalit_session=None))
        with pytest.raises(type(boom)):
            _a.run(w.current_caller(x_phalit_session=None))
    finally:
        w.configure_caller(None)

def test_deliberate_auth_rejection_propagates():
    import asyncio as _a
    from fastapi import HTTPException as HE
    w = _wiring()
    def unauthorised(): raise HE(status_code=401, detail="token expired")
    w.configure_caller(unauthorised)
    try:
        with pytest.raises(HE) as exc:
            _a.run(w.chart_caller(x_phalit_session=None))
        assert exc.value.status_code == 401       # not downgraded to anonymous
    finally:
        w.configure_caller(None)

def test_only_a_clean_none_becomes_anonymous():
    import asyncio as _a
    w = _wiring()
    w.configure_caller(lambda: None)
    try:
        cc = _a.run(w.chart_caller(x_phalit_session=None))
        assert cc.caller.user_id is None and cc.echo_session is not None
    finally:
        w.configure_caller(None)

def test_user_object_without_an_id_is_an_error_not_anonymity():
    import asyncio as _a
    from fastapi import HTTPException as HE
    w = _wiring()
    class _Broken: pass
    w.configure_caller(lambda: _Broken())
    try:
        with pytest.raises(HE) as exc:
            _a.run(w.chart_caller(x_phalit_session=None))
        assert exc.value.status_code == 500
    finally:
        w.configure_caller(None)


# ── SQL matches the live Supabase schema conventions ───────────────────────

def test_owner_fk_cascades_like_the_kundalis_table():
    """kundalis.user_id references profiles(id); a deleted account must not
    leave orphaned birth charts behind."""
    assert "REFERENCES public.profiles(id) ON DELETE CASCADE" in CREATE_TABLE_SQL

def test_rls_is_enabled_with_no_policies():
    """Only the service_role backend touches this table. RLS on with zero
    policies means anon/authenticated get nothing while service_role bypasses."""
    assert "ENABLE ROW LEVEL SECURITY" in CREATE_TABLE_SQL
    assert "FORCE ROW LEVEL SECURITY" in CREATE_TABLE_SQL
    assert "CREATE POLICY" not in CREATE_TABLE_SQL

def test_client_facing_roles_are_revoked_explicitly():
    """Revoking from PUBLIC alone is not enough in Supabase."""
    for role in ("PUBLIC", "anon", "authenticated"):
        assert f"REVOKE ALL ON chart_snapshots FROM {role};" in CREATE_TABLE_SQL
