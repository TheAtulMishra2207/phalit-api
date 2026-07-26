"""
test_d1_snapshot_supabase.py — the Supabase SnapshotStore adapter.

No live Supabase: request_fn is injected so the PostgREST call shape, the
timestamp round-trip and the outage-vs-absent distinction are all verifiable.
"""
import asyncio
import json as jsonlib
from datetime import datetime, timedelta, timezone

import httpx
import pytest
from fastapi import HTTPException

from d1_chart_store import (
    CallerIdentity, DbChartResolver, hash_token, issue_chart_response,
    persist_chart_snapshot, revoke_chart_token,
)
from d1_routes import ChartNotFound
from d1_snapshot_supabase import SupabaseSnapshotStore, parse_timestamp
from test_d1_routes import certified_body


def run(coro):
    return asyncio.run(coro)


class FakePostgrest:
    """Records calls and returns rows the way PostgREST does: timestamps as
    ISO-8601 strings, never datetimes."""

    def __init__(self):
        self.rows = {}
        self.calls = []
        self.fail_with = None

    async def __call__(self, method, path, *, params=None, json=None, headers_extra=None):
        self.calls.append({"method": method, "path": path, "params": params,
                           "json": json, "headers": headers_extra})
        if self.fail_with:
            raise self.fail_with

        if method == "POST":
            self.rows[json["chart_token_hash"]] = dict(json)
            return httpx.Response(201, json=[])
        if method == "GET":
            key = params["chart_token_hash"].split("eq.", 1)[1]
            row = self.rows.get(key)
            return httpx.Response(200, json=[row] if row else [])
        if method == "PATCH":
            key = params["chart_token_hash"].split("eq.", 1)[1]
            row = self.rows.get(key)
            if row is None or row.get("revoked_at") is not None:
                return httpx.Response(200, json=[])      # is.null filter matched nothing
            row["revoked_at"] = json["revoked_at"]
            return httpx.Response(200, json=[row])
        raise AssertionError(method)


def store_and_caller():
    fake = FakePostgrest()
    return SupabaseSnapshotStore(request_fn=fake), fake, CallerIdentity(user_id="u1")


# ── timestamp handling (the flagged risk) ───────────────────────────────────

def test_iso_strings_become_timezone_aware_datetimes():
    for text in ("2026-07-26T12:00:00+00:00", "2026-07-26T12:00:00Z",
                 "2026-07-26T17:30:00+05:30"):
        dt = parse_timestamp(text)
        assert isinstance(dt, datetime) and dt.tzinfo is not None

def test_naive_values_are_read_as_utc_not_left_ambiguous():
    assert parse_timestamp("2026-07-26T12:00:00").tzinfo == timezone.utc
    assert parse_timestamp(datetime(2026, 7, 26, 12)).tzinfo == timezone.utc

def test_none_and_datetime_pass_through():
    assert parse_timestamp(None) is None
    aware = datetime(2026, 7, 26, tzinfo=timezone.utc)
    assert parse_timestamp(aware) == aware

def test_unexpected_timestamp_type_raises():
    with pytest.raises(ValueError):
        parse_timestamp(1753531200)

def test_timestamps_are_serialised_as_iso_on_insert():
    store, fake, caller = store_and_caller()
    run(persist_chart_snapshot(store, certified_body(), caller))
    sent = fake.calls[0]["json"]
    for col in ("created_at", "expires_at"):
        assert isinstance(sent[col], str), col
        assert "T" in sent[col]
    jsonlib.dumps(sent)          # must be JSON-serialisable for PostgREST

def test_fetch_returns_datetimes_so_the_resolver_can_compare():
    """A str expires_at would raise TypeError inside the resolver and surface as
    a 500 instead of a 404. This is the case QA flagged."""
    store, fake, caller = store_and_caller()
    token = run(persist_chart_snapshot(store, certified_body(), caller))
    row = run(store.fetch(hash_token(token)))
    assert isinstance(row["expires_at"], datetime) and row["expires_at"].tzinfo
    assert isinstance(row["created_at"], datetime)
    assert row["revoked_at"] is None
    # and the resolver actually resolves against it
    assert run(DbChartResolver(store, caller).resolve(token))["lagna"]["sign_index"] == 6


# ── PostgREST call shape ───────────────────────────────────────────────────

def test_fetch_filters_by_token_hash_only_and_limits_one():
    store, fake, caller = store_and_caller()
    token = run(persist_chart_snapshot(store, certified_body(), caller))
    run(store.fetch(hash_token(token)))
    call = fake.calls[-1]
    assert call["method"] == "GET" and call["path"] == "/chart_snapshots"
    assert call["params"]["chart_token_hash"] == f"eq.{hash_token(token)}"
    assert call["params"]["limit"] == "1"

def test_raw_token_is_never_sent_to_the_database():
    store, fake, caller = store_and_caller()
    token = run(persist_chart_snapshot(store, certified_body(), caller))
    assert token not in jsonlib.dumps(fake.calls, default=str)

def test_revoke_uses_the_is_null_filter_and_is_one_way():
    store, fake, caller = store_and_caller()
    token = run(persist_chart_snapshot(store, certified_body(), caller))
    assert run(revoke_chart_token(store, token)) is True
    patch = fake.calls[-1]
    assert patch["method"] == "PATCH"
    assert patch["params"]["revoked_at"] == "is.null"
    assert run(revoke_chart_token(store, token)) is False       # already revoked
    with pytest.raises(ChartNotFound):
        run(DbChartResolver(store, caller).resolve(token))


# ── outage must not read as "not found" ────────────────────────────────────

def test_backend_outage_raises_rather_than_returning_none():
    store, fake, caller = store_and_caller()
    token = run(persist_chart_snapshot(store, certified_body(), caller))
    fake.fail_with = HTTPException(status_code=503, detail="Could not reach Supabase")
    with pytest.raises(HTTPException) as exc:
        run(store.fetch(hash_token(token)))
    assert exc.value.status_code == 503

def test_absent_row_returns_none_which_becomes_chart_not_found():
    store, fake, caller = store_and_caller()
    assert run(store.fetch("deadbeef")) is None
    with pytest.raises(ChartNotFound):
        run(DbChartResolver(store, caller).resolve("no-such-token"))


# ── expiry and ownership still hold through the real adapter ───────────────

def test_expired_snapshot_fails_closed_through_the_adapter():
    store, fake, caller = store_and_caller()
    past = datetime.now(timezone.utc) - timedelta(hours=2)
    token = run(persist_chart_snapshot(store, certified_body(), caller,
                                       ttl=timedelta(minutes=30), now=past))
    with pytest.raises(ChartNotFound):
        run(DbChartResolver(store, caller).resolve(token))

def test_cross_owner_fails_closed_through_the_adapter():
    store, fake, owner = store_and_caller()
    token = run(persist_chart_snapshot(store, certified_body(), owner))
    with pytest.raises(ChartNotFound):
        run(DbChartResolver(store, CallerIdentity(user_id="u2")).resolve(token))

def test_issue_chart_response_round_trips_through_the_adapter():
    store, fake, caller = store_and_caller()
    body = run(issue_chart_response(certified_body(), store, caller))
    assert "chart_token" in body
    resolved = run(DbChartResolver(store, caller).resolve(body["chart_token"]))
    assert resolved["planets"] == certified_body()["planets"]
    assert "chart_token" not in resolved

def test_adapter_is_marked_production_safe():
    assert SupabaseSnapshotStore.production_safe is True
