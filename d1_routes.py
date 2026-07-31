"""
d1_routes.py — POST /d1/prepare (KAR-093 step 6a, route only).

Wires the accepted D1 stack into FastAPI:

    chart_token -> ChartResolver -> certified /chart body
                -> to_certified_chart()   (translate, never compute)
                -> compute_d1()           (contract response + doctrine)
                -> build_d1_drawers()     (drawer payload)

NO FRONTEND CHANGE accompanies this file. newphalit.html still runs its own
engines; the cutover is a separate pass.

TOKEN STORE — RULED. Production uses the DB-backed immutable chart-snapshot
store in d1_chart_store.py (CREATE_TABLE_SQL, persist_chart_snapshot,
issue_chart_response, DbChartResolver). An in-process TTL store is explicitly
NOT permitted in production: it loses tokens across restarts and diverges
across workers. InMemorySnapshotStore exists for tests and local development
only and is marked production_safe = False.

The resolver stays an injected dependency because it must be scoped to the
authenticated caller, so a token can never be read across owners:

    ChartResolver      — protocol: resolve(chart_token) -> certified chart body
    get_chart_resolver — FastAPI dependency; the app MUST override it

If the app does not override it, every request returns 503 rather than falling
back to anything.

Wiring in main.py (all four lines are required):

    from d1_chart_store import CallerIdentity, DbChartResolver
    from d1_routes import router as d1_router, get_chart_resolver

    app.include_router(d1_router)

    def _resolver(caller: CallerIdentity = Depends(current_caller)):
        return DbChartResolver(snapshot_store, caller)

    app.dependency_overrides[get_chart_resolver] = _resolver

where `snapshot_store` is the SnapshotStore adapter over the app's Supabase
client and `current_caller` yields CallerIdentity(user_id=...) for an
authenticated request or CallerIdentity(session_id=...) for an anonymous one.
/chart must call issue_chart_response so the token is minted from the exact
persisted snapshot.
"""
from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, Optional, Protocol

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Extra, Field, StrictStr

from d1_chart_adapter import ChartAdapterError, to_certified_chart
from d1_engine import D1EngineError, D1Doctrine, compute_d1
from d1_synthesis import D1DrawerPayload, build_d1_drawers
from d1_contract import D1PrepareResponse, Varga

logger = logging.getLogger(__name__)
router = APIRouter(tags=["d1"])

ROUTE_VERSION = "d1-route-0.1.0"


class ChartNotFound(LookupError):
    """The token is unknown, expired, or not readable by this caller."""


class ChartResolver(Protocol):
    async def resolve(self, chart_token: str) -> Dict[str, Any]:
        """Return the certified /chart body for this token.
        Raise ChartNotFound if the token is unknown or expired.

        ASYNC because the application's database layer is async: routes_kundalis
        reaches Supabase through httpx.AsyncClient. A sync port would have
        forced a blocking call inside the event loop."""


def get_chart_resolver() -> ChartResolver:
    """Dependency placeholder. The application MUST override this. Failing
    loudly is deliberate: a default in-process store would silently become
    production behaviour."""
    raise HTTPException(
        status_code=503,
        detail="D1 chart resolver is not configured; POST /d1/prepare is unavailable.",
    )


class D1PrepareRequest(BaseModel):
    # StrictStr, not str: pydantic v1 coerces a JSON NUMBER to a string, so
    # {"chart_token": 12345678} was accepted and turned into "12345678",
    # deferring a malformed request to a token lookup and a 404 instead of an
    # immediate 422. v2 rejected it outright; StrictStr restores that parity in
    # both versions.
    chart_token: StrictStr = Field(min_length=8, max_length=256)

    # KAR-093-B04. The page sends a varga; without this field pydantic v1's
    # default Extra.ignore DROPPED IT SILENTLY and every D9 request returned a
    # D1 payload. Typed as the enum rather than a str so an unknown varga is a
    # 422 at the boundary instead of a D1EngineError three layers down.
    varga: Varga = Varga.D1

    class Config:
        # An unknown field is now a 422, not a silent discard. B04 was invisible
        # precisely because the default swallowed the one field that mattered;
        # the next such field should fail loudly at the boundary.
        extra = Extra.forbid


class D1PrepareBody(BaseModel):
    """Everything the renderer needs, in one response."""
    route_version: str = ROUTE_VERSION
    chart_token: str
    d1: D1PrepareResponse
    doctrine: D1Doctrine
    drawers: D1DrawerPayload
    calculation_meta: Optional[Dict[str, Any]] = None


@router.post("/d1/prepare", response_model=D1PrepareBody)
async def prepare_d1(req: D1PrepareRequest,
                     resolver: ChartResolver = Depends(get_chart_resolver)) -> D1PrepareBody:
    try:
        chart = await resolver.resolve(req.chart_token)
    except ChartNotFound:
        # Unknown, expired, revoked and cross-owner all look identical here.
        raise HTTPException(status_code=404, detail="Unknown or expired chart_token.")
    except HTTPException as exc:
        # ONLY deliberate authentication statuses survive. Everything else —
        # notably the Supabase adapter's 502/503, which carry upstream response
        # text and can name internal hosts — is correlated and generalised.
        # A blanket re-raise here leaked "Could not reach Supabase: host:5432
        # timed out" to the caller (QA step-6a v4).
        if exc.status_code in (401, 403):
            raise
        correlation_id = uuid.uuid4().hex[:12]
        logger.exception("d1 chart resolver upstream failure [%s]", correlation_id)
        raise HTTPException(
            status_code=500,
            detail=f"Chart lookup failed. Reference: {correlation_id}",
        )
    except Exception:
        correlation_id = uuid.uuid4().hex[:12]
        logger.exception("d1 chart resolver failed [%s]", correlation_id)
        raise HTTPException(
            status_code=500,
            detail=f"Chart lookup failed. Reference: {correlation_id}",
        )

    try:
        certified = to_certified_chart(chart, req.chart_token, varga=req.varga)
    except ChartAdapterError as e:
        # The stored chart cannot be translated. That is a data problem, not a
        # malformed request, and it must never be repaired by guessing.
        correlation_id = uuid.uuid4().hex[:12]
        logger.error("d1 chart adapter rejected token [%s]: %s", correlation_id, e)
        raise HTTPException(
            status_code=422,
            detail=f"Certified chart could not be interpreted: {e} Reference: {correlation_id}",
        )

    try:
        d1, doctrine = compute_d1(certified, req.varga)
        drawers = build_d1_drawers(d1, doctrine)
    except HTTPException as exc:
        if exc.status_code in (401, 403):
            raise
        correlation_id = uuid.uuid4().hex[:12]
        logger.exception("d1 preparation upstream failure [%s]", correlation_id)
        raise HTTPException(
            status_code=500,
            detail=f"D1 preparation failed. Reference: {correlation_id}",
        )
    except D1EngineError as e:
        correlation_id = uuid.uuid4().hex[:12]
        logger.error("d1 engine refused input [%s]: %s", correlation_id, e)
        raise HTTPException(
            status_code=422,
            detail=f"D1 engine could not accept this chart: {e} Reference: {correlation_id}",
        )
    except Exception:
        correlation_id = uuid.uuid4().hex[:12]
        logger.exception("d1 preparation failed [%s]", correlation_id)
        raise HTTPException(
            status_code=500,
            detail=f"D1 preparation failed. Reference: {correlation_id}",
        )

    return D1PrepareBody(
        chart_token=req.chart_token, d1=d1, doctrine=doctrine, drawers=drawers,
        calculation_meta=chart.get("calculation_meta"),
    )
