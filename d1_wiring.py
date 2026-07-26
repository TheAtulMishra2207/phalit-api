"""
d1_wiring.py — everything main.py needs to turn on POST /d1/prepare.

Paste-ready. The only judgement call left to the app is WHO the caller is,
because /chart serves both authenticated users and anonymous visitors and the
snapshot is owned by exactly one of them.

──────────────────────────────────────────────────────────────────────────────
STEP 1 — run d1_chart_store.CREATE_TABLE_SQL in the Supabase SQL editor, once.

STEP 2 — main.py, near the other router imports:

    from d1_wiring import install_d1, snapshot_store
    install_d1(app)

STEP 3 — main.py, inside /chart, replace the existing `return {...}` with:

    body = { ...the existing response dict, unchanged... }
    return await issue_chart_response(body, snapshot_store, caller)

  and make the handler `async def`, adding the caller dependency:

    from d1_wiring import ChartCaller, chart_caller
    from d1_chart_store import issue_chart_response

    @app.post("/chart")
    async def calculate_chart(req: ChartRequest,
                              cc: ChartCaller = Depends(chart_caller)):
        body = { ...existing response dict... }
        return await issue_chart_response(body, snapshot_store, cc.caller,
                                          echo_session=cc.echo_session)

STEP 4 — deploy, then verify against the live boundary:

    curl -s -X POST $API/chart \\
         -H 'Content-Type: application/json' \\
         -d '{"date":"1984-07-22","time":"13:05","lat":25.2139,"lon":84.9896,"utc_offset":5.5}' \\
      | tee /tmp/chart.json | python -c 'import sys,json; d=json.load(sys.stdin); print(d["chart_token"], d["anon_session"])'

    curl -s -X POST $API/d1/prepare -H 'X-Phalit-Session: <anon_session from above>' \\
         -H 'Content-Type: application/json' \\
         -d "{\\"chart_token\\":\\"<token from above>\\"}" | head -c 400

  Expect 200 and a body containing d1, doctrine and drawers. A 404 means the
  session header differed between the two calls (ownership is enforced).
──────────────────────────────────────────────────────────────────────────────

CALLER IDENTITY. current_caller below reads an authenticated user if the app
supplies one, else falls back to an opaque session header. It does NOT invent a
session: a request with neither identity is rejected, because a server-minted
session would make the snapshot unreadable on the very next call. If the app
already has an optional-user dependency, pass it to configure_caller() and the
header fallback applies only to anonymous traffic.
"""
from __future__ import annotations

import os
from typing import Any, Callable, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, status

from d1_chart_store import (CallerIdentity, DbChartResolver, mint_session_token,
                            verify_session_token)
from d1_routes import get_chart_resolver, router as d1_router
from d1_snapshot_supabase import SupabaseSnapshotStore

SESSION_HEADER = "X-Phalit-Session"

# HMAC secret for anonymous session tokens. Set D1_SESSION_SECRET in the
# environment, or call configure_session_secret(). Anonymous flow FAILS CLOSED
# if neither is present rather than falling back to an unsigned identifier.
_session_secret: Optional[str] = None


def configure_session_secret(secret: str) -> None:
    global _session_secret
    _session_secret = secret


def _secret() -> str:
    if _session_secret:
        return _session_secret
    env = os.environ.get("D1_SESSION_SECRET")
    if env:
        return env
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Anonymous sessions are unavailable: D1_SESSION_SECRET is not configured.")

# One store for the process. Stateless: it holds no rows, only the request shape.
snapshot_store = SupabaseSnapshotStore()

# Optional hook: set this to the app's "current user or None" dependency.
_optional_user_dependency: Optional[Callable[..., Any]] = None


def configure_caller(optional_user_dependency: Optional[Callable[..., Any]]) -> None:
    """Give D1 the app's optional-user dependency so authenticated callers own
    their snapshots by user_id instead of by session header."""
    global _optional_user_dependency
    _optional_user_dependency = optional_user_dependency


class ChartCaller:
    """Who owns the snapshot /chart is about to persist, plus the session token
    to echo back when that owner is anonymous."""
    def __init__(self, caller: CallerIdentity, echo_session: Optional[str] = None):
        self.caller, self.echo_session = caller, echo_session


async def _authenticated_user_id() -> Optional[str]:
    """Only a CLEAN optional-auth result of None may fall through to the
    anonymous flow. Exceptions PROPAGATE: an auth-service or database outage
    previously became `user = None`, which minted an anonymous session and
    silently persisted an authenticated user's chart under the wrong owner.
    A deliberate 401/403 from the dependency propagates for the same reason."""
    if _optional_user_dependency is None:
        return None
    user = _optional_user_dependency()
    if hasattr(user, "__await__"):
        user = await user
    if user is None:
        return None                      # genuinely anonymous
    uid = getattr(user, "user_id", None)
    if not uid:
        # A user object without an id is a contract violation, not anonymity.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authenticated caller has no user_id.")
    return str(uid)


async def chart_caller(
    x_phalit_session: Optional[str] = Header(default=None, alias=SESSION_HEADER),
) -> ChartCaller:
    """Dependency for /chart ONLY. Authenticated users own by user_id. An
    anonymous caller reuses the session it already holds, or is ISSUED a new
    server-minted one which /chart returns as anon_session."""
    uid = await _authenticated_user_id()
    if uid:
        return ChartCaller(CallerIdentity(user_id=uid))
    secret = _secret()
    if x_phalit_session:
        # Reuse only a token THIS SERVER issued. A client-invented value such as
        # "anon_existing" or "probe-1" is not an identity — it is a claim to own
        # somebody else's snapshots, so it is refused rather than honoured.
        if not verify_session_token(x_phalit_session, secret):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(f"{SESSION_HEADER} is not a valid server-issued session. "
                        f"Omit the header to be issued one."))
        return ChartCaller(CallerIdentity(session_id=x_phalit_session))
    issued = mint_session_token(secret)
    return ChartCaller(CallerIdentity(session_id=issued), echo_session=issued)


async def current_caller(
    x_phalit_session: Optional[str] = Header(default=None, alias=SESSION_HEADER),
) -> CallerIdentity:
    """Dependency for /d1/prepare. Never mints: minting here would create a
    brand-new owner that owns nothing, turning every anonymous lookup into a
    404. The client must echo the session /chart issued."""
    uid = await _authenticated_user_id()
    if uid:
        return CallerIdentity(user_id=uid)
    if x_phalit_session:
        if not verify_session_token(x_phalit_session, _secret()):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{SESSION_HEADER} is not a valid server-issued session.")
        return CallerIdentity(session_id=x_phalit_session)
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=(f"Anonymous requests must echo the {SESSION_HEADER} value that "
                f"/chart returned as anon_session; a chart snapshot is owned by "
                f"the caller that created it."),
    )


async def d1_resolver(caller: CallerIdentity = Depends(current_caller)) -> DbChartResolver:
    """Caller-scoped, so a token can never be read across owners."""
    return DbChartResolver(snapshot_store, caller)


def install_d1(app: FastAPI) -> None:
    """Register POST /d1/prepare and bind its resolver."""
    app.include_router(d1_router)
    app.dependency_overrides[get_chart_resolver] = d1_resolver
