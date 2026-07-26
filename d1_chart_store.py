"""
d1_chart_store.py — DB-backed immutable chart-snapshot store (KAR-093 step 6a v2).

Founder/QA ruling: production uses a DB-backed immutable snapshot, never an
in-process TTL store, which would lose tokens across restarts and diverge
across workers.

/chart flow:
    1. calculate the certified chart
    2. persist the exact response body and its calculation_meta
    3. mint a high-entropy opaque token
    4. store ONLY the token hash
    5. return chart_token alongside the existing /chart response

This module owns the token lifecycle and the fail-closed resolution rules. It
deliberately does NOT own the database client: the API's DB access lives in
routes_kundalis/routes_auth, which are not visible here, so guessing a client
signature would be inventing integration. Instead it defines a narrow port:

    SnapshotStore.insert(row)                 -> None
    SnapshotStore.fetch(chart_token_hash)     -> row dict or None

Wire that port to the existing Supabase/PostgREST client in one small adapter.
The SQL for the table is CREATE_TABLE_SQL below.

Resolution fails closed and returns ChartNotFound — never a distinguishing
error — for unknown, expired, revoked and cross-owner tokens alike, so the
route cannot leak whether a token exists.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Protocol

from d1_routes import ChartNotFound

STORE_VERSION = "d1-chart-store-0.1.0"
TOKEN_BYTES = 32                     # 256-bit opaque token
DEFAULT_TTL = timedelta(minutes=30)  # public access window (KAR-058 precedent)

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS chart_snapshots (
    id                 bigserial PRIMARY KEY,
    chart_token_hash   text        NOT NULL UNIQUE,
    -- Matches the live schema's convention: kundalis.user_id references
    -- profiles(id), which in turn references auth.users(id). Cascading means a
    -- deleted account takes its snapshots with it instead of orphaning rows
    -- that still contain that person's birth chart.
    owner_user_id      uuid        NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    session_id         text        NULL,
    chart_payload      jsonb       NOT NULL,
    calculation_meta   jsonb       NOT NULL,
    created_at         timestamptz NOT NULL DEFAULT now(),
    expires_at         timestamptz NOT NULL,
    revoked_at         timestamptz NULL,
    -- Exactly one owner key, never both and never neither.
    CONSTRAINT chart_snapshots_owner_xor CHECK (
        (owner_user_id IS NOT NULL AND session_id IS NULL)
     OR (owner_user_id IS NULL     AND session_id IS NOT NULL)
    ),
    CONSTRAINT chart_snapshots_ttl_positive CHECK (expires_at > created_at)
);
CREATE INDEX IF NOT EXISTS chart_snapshots_expires_idx ON chart_snapshots (expires_at);

-- IMMUTABILITY IS ENFORCED BY THE DATABASE, not by convention (QA step-6a v2
-- HIGH-2). The only legal mutation is revocation: revoked_at NULL -> timestamp.
-- Every other column is update-protected, so a client with UPDATE rights still
-- cannot rewrite chart_payload, provenance, ownership or expiry after minting.
CREATE OR REPLACE FUNCTION chart_snapshots_guard() RETURNS trigger AS $$
BEGIN
    IF  NEW.id               IS DISTINCT FROM OLD.id
     OR NEW.chart_token_hash IS DISTINCT FROM OLD.chart_token_hash
     OR NEW.owner_user_id    IS DISTINCT FROM OLD.owner_user_id
     OR NEW.session_id       IS DISTINCT FROM OLD.session_id
     OR NEW.chart_payload    IS DISTINCT FROM OLD.chart_payload
     OR NEW.calculation_meta IS DISTINCT FROM OLD.calculation_meta
     OR NEW.created_at       IS DISTINCT FROM OLD.created_at
     OR NEW.expires_at       IS DISTINCT FROM OLD.expires_at
    THEN
        RAISE EXCEPTION 'chart_snapshots rows are immutable; only revoked_at may be set';
    END IF;
    IF OLD.revoked_at IS NOT NULL AND NEW.revoked_at IS DISTINCT FROM OLD.revoked_at THEN
        RAISE EXCEPTION 'revocation is one-way; revoked_at cannot be changed or cleared';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS chart_snapshots_guard_trg ON chart_snapshots;
CREATE TRIGGER chart_snapshots_guard_trg
    BEFORE UPDATE ON chart_snapshots
    FOR EACH ROW EXECUTE FUNCTION chart_snapshots_guard();

-- ROW LEVEL SECURITY. Every other table in this project runs with RLS on, and
-- only the service_role backend touches chart_snapshots. RLS is therefore
-- enabled with NO policies at all: service_role bypasses RLS, while anon and
-- authenticated get nothing. A leaked publishable key cannot read a stranger's
-- birth chart even if it learns a token hash.
ALTER TABLE chart_snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE chart_snapshots FORCE ROW LEVEL SECURITY;

-- Belt and braces: revoke from the client-facing roles explicitly. Revoking
-- from PUBLIC alone is not sufficient in Supabase, where anon and authenticated
-- carry their own grants. Deletion is not part of the lifecycle: expiry is by
-- timestamp; purge with a privileged maintenance role if retention requires it.
REVOKE ALL ON chart_snapshots FROM PUBLIC;
REVOKE ALL ON chart_snapshots FROM anon;
REVOKE ALL ON chart_snapshots FROM authenticated;
"""


SESSION_PREFIX = "anon_"

def mint_session_token(secret: str) -> str:
    """Server-issued anonymous session identifier, VERIFIABLE.

    A prefix and a length prove nothing — a client could invent
    "anon_whatever". The token is a random nonce plus an HMAC over it, so the
    server can later prove it issued the value. The browser never mints one:
    a client-chosen owner key would let a caller name itself the owner of
    another visitor's snapshot."""
    if not secret:
        raise ValueError("a session secret is required to mint anonymous sessions")
    nonce = secrets.token_urlsafe(24)
    sig = hmac.new(secret.encode("utf-8"), nonce.encode("utf-8"), hashlib.sha256).hexdigest()[:32]
    return f"{SESSION_PREFIX}{nonce}.{sig}"


def verify_session_token(token: Optional[str], secret: str) -> bool:
    """True only for a token this server issued. Constant-time comparison."""
    if not token or not secret or not token.startswith(SESSION_PREFIX):
        return False
    body = token[len(SESSION_PREFIX):]
    nonce, _, sig = body.partition(".")
    if not nonce or not sig:
        return False
    expected = hmac.new(secret.encode("utf-8"), nonce.encode("utf-8"), hashlib.sha256).hexdigest()[:32]
    return hmac.compare_digest(sig, expected)


def mint_token() -> str:
    """High-entropy opaque token. Returned to the caller once and never stored."""
    return secrets.token_urlsafe(TOKEN_BYTES)


def hash_token(chart_token: str) -> str:
    """Only the hash is persisted, so a database read cannot replay a token."""
    return hashlib.sha256(chart_token.encode("utf-8")).hexdigest()


class SnapshotStore(Protocol):
    """ASYNC: the app's DB layer is httpx.AsyncClient over Supabase PostgREST."""
    async def insert(self, row: Dict[str, Any]) -> None: ...
    async def fetch(self, chart_token_hash: str) -> Optional[Dict[str, Any]]: ...
    async def revoke(self, chart_token_hash: str, revoked_at: datetime) -> bool:
        """Set revoked_at on an un-revoked row. Returns False if the row is
        absent or already revoked. This is the ONLY mutation the database
        permits, so production revocation is representable through the port."""
        ...


async def revoke_chart_token(store: SnapshotStore, chart_token: str,
                             now: Optional[datetime] = None) -> bool:
    """Revoke by raw token. The caller never needs to know the hash."""
    return await store.revoke(hash_token(chart_token), now or datetime.now(timezone.utc))


class CallerIdentity:
    """Who is asking. Exactly one of user_id / session_id is the owner key."""
    def __init__(self, user_id: Optional[str] = None, session_id: Optional[str] = None):
        # XOR, matching the chart_snapshots_owner_xor constraint. Accepting both
        # would leave the effective owner ambiguous at resolution time.
        if bool(user_id) == bool(session_id):
            raise ValueError(
                "caller must have exactly one of user_id or session_id, not both and not neither")
        self.user_id, self.session_id = user_id, session_id

    def owns(self, row: Dict[str, Any]) -> bool:
        if row.get("owner_user_id") is not None:
            return self.user_id is not None and row["owner_user_id"] == self.user_id
        return self.session_id is not None and row.get("session_id") == self.session_id


async def persist_chart_snapshot(store: SnapshotStore, chart_body: Dict[str, Any],
                                 caller: CallerIdentity, ttl: timedelta = DEFAULT_TTL,
                                 now: Optional[datetime] = None) -> str:
    """Persist the exact certified body and return the one-time chart_token."""
    if ttl <= timedelta(0):
        raise ValueError("ttl must be positive; a non-positive ttl mints an already-expired token")
    now = now or datetime.now(timezone.utc)
    token = mint_token()
    await store.insert({
        "chart_token_hash": hash_token(token),
        "owner_user_id": caller.user_id,
        "session_id": caller.session_id,
        "chart_payload": chart_body,
        "calculation_meta": chart_body.get("calculation_meta"),
        "created_at": now,
        "expires_at": now + ttl,
        "revoked_at": None,
    })
    return token


async def issue_chart_response(chart_body: Dict[str, Any], store: SnapshotStore,
                               caller: CallerIdentity, ttl: timedelta = DEFAULT_TTL,
                               now: Optional[datetime] = None,
                               echo_session: Optional[str] = None) -> Dict[str, Any]:
    """The /chart integration point: persist the EXACT certified body, mint a
    token, and return the body with chart_token added. Nothing else about the
    /chart response changes.

    Patch for main.py /chart, immediately before its existing return:

        from d1_chart_store import CallerIdentity, issue_chart_response
        body = { ... the existing response dict ... }
        return await issue_chart_response(body, snapshot_store, caller)

    where `snapshot_store` is the SnapshotStore adapter over the app's DB
    client and `caller` is CallerIdentity(user_id=...) or
    CallerIdentity(session_id=...).
    """
    token = await persist_chart_snapshot(store, chart_body, caller, ttl=ttl, now=now)
    out = {**chart_body, "chart_token": token}
    if echo_session:
        # Anonymous caller: hand back the server-issued session so the client can
        # echo it on /d1/prepare. Authenticated callers own by user_id and get
        # no session token.
        out["anon_session"] = echo_session
    return out


class DbChartResolver:
    """Caller-scoped resolver. Construct one per request with the authenticated
    caller, so a token can never be read across owners."""

    def __init__(self, store: SnapshotStore, caller: CallerIdentity,
                 now: Optional[datetime] = None):
        self.store, self.caller, self._now = store, caller, now

    def _clock(self) -> datetime:
        return self._now or datetime.now(timezone.utc)

    async def resolve(self, chart_token: str) -> Dict[str, Any]:
        row = await self.store.fetch(hash_token(chart_token))
        # Every failure mode raises the SAME error: unknown, expired, revoked
        # and cross-owner are indistinguishable to the caller.
        if row is None:
            raise ChartNotFound()
        if row.get("revoked_at") is not None:
            raise ChartNotFound()
        expires_at = row.get("expires_at")
        if expires_at is None or expires_at <= self._clock():
            raise ChartNotFound()
        if not self.caller.owns(row):
            raise ChartNotFound()
        payload = row.get("chart_payload")
        if not isinstance(payload, dict):
            raise ChartNotFound()
        return payload


class InMemorySnapshotStore:
    """TEST AND LOCAL DEVELOPMENT ONLY. Never wire this in production: it loses
    tokens across restarts and diverges across workers (founder ruling)."""
    production_safe = False

    def __init__(self) -> None:
        self.rows: Dict[str, Dict[str, Any]] = {}

    async def insert(self, row: Dict[str, Any]) -> None:
        self.rows[row["chart_token_hash"]] = dict(row)

    async def fetch(self, chart_token_hash: str) -> Optional[Dict[str, Any]]:
        row = self.rows.get(chart_token_hash)
        return dict(row) if row else None

    async def revoke(self, chart_token_hash: str, revoked_at: datetime) -> bool:
        row = self.rows.get(chart_token_hash)
        if row is None or row.get("revoked_at") is not None:
            return False
        row["revoked_at"] = revoked_at
        return True
