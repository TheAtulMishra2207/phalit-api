"""
d1_snapshot_supabase.py — SnapshotStore over Supabase PostgREST (KAR-093 step 6a).

Written against the real pattern in routes_kundalis.py: httpx.AsyncClient,
service_role key from config.get_settings(), PostgREST filters, and the same
502/503 mapping for upstream failures. It does NOT import routes_kundalis, so
D1 does not depend on kundali routing.

Two things this adapter is careful about:

  TIMESTAMPS. PostgREST returns timestamptz as ISO-8601 STRINGS. DbChartResolver
  compares expires_at against an aware datetime, and comparing a str would raise
  TypeError inside the resolver — surfacing as a correlated 500 rather than the
  intended 404. Every timestamp column is parsed back to a timezone-aware
  datetime on the way out, and serialised to ISO on the way in. A naive value
  is treated as UTC rather than left ambiguous.

  BACKEND ERRORS. A Supabase outage must not read as "token not found". The
  store raises (502/503, matching routes_kundalis), the route catches it as an
  unexpected resolver failure and returns a correlated 500. Only a genuinely
  absent row returns None, which the resolver turns into ChartNotFound.

Wiring:

    from d1_snapshot_supabase import SupabaseSnapshotStore
    snapshot_store = SupabaseSnapshotStore()
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Dict, Optional

import httpx
from fastapi import HTTPException, status

TABLE = "/chart_snapshots"
TIMESTAMP_COLUMNS = ("created_at", "expires_at", "revoked_at")

RequestFn = Callable[..., Awaitable[httpx.Response]]


def parse_timestamp(value: Any) -> Any:
    """PostgREST ISO string -> timezone-aware datetime. Naive values are read
    as UTC. Anything already a datetime is normalised, not re-parsed."""
    if value is None or isinstance(value, datetime):
        if isinstance(value, datetime) and value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
    if not isinstance(value, str):
        raise ValueError(f"unexpected timestamp type {type(value).__name__}")
    text = value.replace("Z", "+00:00")
    dt = datetime.fromisoformat(text)
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _row_out(row: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(row)
    for col in TIMESTAMP_COLUMNS:
        if col in out:
            out[col] = parse_timestamp(out[col])
    return out


def _row_in(row: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(row)
    for col in TIMESTAMP_COLUMNS:
        v = out.get(col)
        if isinstance(v, datetime):
            out[col] = (v if v.tzinfo else v.replace(tzinfo=timezone.utc)).isoformat()
    return out


async def _default_request(method: str, path: str, *, params: dict | None = None,
                           json: Any = None, headers_extra: dict | None = None) -> httpx.Response:
    """Same shape and error mapping as routes_kundalis._supabase_request."""
    from config import get_settings          # imported lazily so tests need no config
    settings = get_settings()
    url = f"{settings.supabase_url}/rest/v1{path}"
    headers = {
        "apikey": settings.supabase_secret_key,
        "Authorization": f"Bearer {settings.supabase_secret_key}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    if headers_extra:
        headers.update(headers_extra)
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.request(method, url, params=params, json=json, headers=headers)
            response.raise_for_status()
            return response
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Supabase rejected request: {e.response.text}") from e
    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Could not reach Supabase: {e}") from e


class SupabaseSnapshotStore:
    """Production SnapshotStore. request_fn is injectable purely so tests can
    exercise the adapter without a live Supabase."""
    production_safe = True

    def __init__(self, request_fn: Optional[RequestFn] = None, table: str = TABLE):
        self._request = request_fn or _default_request
        self._table = table

    async def insert(self, row: Dict[str, Any]) -> None:
        await self._request("POST", self._table, json=_row_in(row),
                            headers_extra={"Prefer": "return=minimal"})

    async def fetch(self, chart_token_hash: str) -> Optional[Dict[str, Any]]:
        response = await self._request(
            "GET", self._table,
            params={"chart_token_hash": f"eq.{chart_token_hash}",
                    "select": "*", "limit": "1"})
        rows = response.json()
        if not rows:
            return None            # absent row only; outages raise above
        return _row_out(rows[0])

    async def revoke(self, chart_token_hash: str, revoked_at: datetime) -> bool:
        """One-way revocation. The revoked_at=is.null filter makes a second
        revoke a no-op returning False, and matches the DB trigger which
        forbids changing or clearing an existing revoked_at."""
        response = await self._request(
            "PATCH", self._table,
            params={"chart_token_hash": f"eq.{chart_token_hash}",
                    "revoked_at": "is.null"},
            json=_row_in({"revoked_at": revoked_at}),
            headers_extra={"Prefer": "return=representation"})
        return bool(response.json())
