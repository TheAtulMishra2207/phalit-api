"""
nakshatra_routes.py — POST /nakshatra/prepare (NAK-001, route only).

    chart_token -> ChartResolver -> certified /chart body
                -> build_nakshatra_payload()   (place, verify, publish)

NO FRONTEND CHANGE accompanies this file. newphalit_fixed.html still runs its
own nakshatra helpers; the cutover is NAK-002.

ONE RESOLVER, ONE TOKEN SYSTEM. This route depends on `get_chart_resolver` from
d1_routes — the same function object the D1 and Pratiphala routes depend on, not
a copy — so `install_d1(app)` binds it once and this route inherits the
caller-scoped, fail-closed resolver automatically. A private Nakshatra store or
a second token mechanism would be a second door onto one snapshot, which is how
two views of the same chart come apart.

ERROR BOUNDARY. Deliberately identical to d1_routes, because two boundaries that
are supposed to behave the same and are written separately will diverge:

    unknown / expired / cross-owner token   404, one public detail for all three
    resolver not configured                 503 (from get_chart_resolver itself)
    malformed request                       422 (pydantic, at the boundary)
    unusable chart data                     422, static detail plus a reference
    401 / 403 from the auth layer           preserved verbatim
    anything else                           500 with a correlation reference

Upstream text never reaches the caller: the Supabase adapter raises 502/503
carrying response bodies and internal hostnames, and a blanket re-raise leaked
them once already (QA step-6a v4).
"""
from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException

# REUSED, NOT REDEFINED. One resolver abstraction and one dependency provider
# serve every prepare route.
from d1_routes import ChartNotFound, ChartResolver, get_chart_resolver
from nakshatra_contract import NakshatraPrepareRequest, NakshatraPrepareResponse
from nakshatra_engine import NakshatraEngineError, build_nakshatra_payload

logger = logging.getLogger(__name__)
router = APIRouter(tags=["nakshatra"])

ROUTE_VERSION = "nakshatra-route-0.1.0"


@router.post("/nakshatra/prepare", response_model=NakshatraPrepareResponse)
async def prepare_nakshatra(
    req: NakshatraPrepareRequest,
    resolver: ChartResolver = Depends(get_chart_resolver),
) -> NakshatraPrepareResponse:
    try:
        chart = await resolver.resolve(req.chart_token)
    except ChartNotFound:
        # Unknown, expired, revoked and cross-owner are one public answer. Any
        # distinction here tells a caller whether someone else's token exists.
        raise HTTPException(status_code=404, detail="Unknown or expired chart_token.")
    except HTTPException as exc:
        if exc.status_code in (401, 403):
            raise
        correlation_id = uuid.uuid4().hex[:12]
        logger.exception("nakshatra chart resolver upstream failure [%s]", correlation_id)
        raise HTTPException(
            status_code=500,
            detail=f"Chart lookup failed. Reference: {correlation_id}",
        )
    except Exception:
        correlation_id = uuid.uuid4().hex[:12]
        logger.exception("nakshatra chart resolver failed [%s]", correlation_id)
        raise HTTPException(
            status_code=500,
            detail=f"Chart lookup failed. Reference: {correlation_id}",
        )

    try:
        return build_nakshatra_payload(chart, req.chart_token, ROUTE_VERSION)
    except NakshatraEngineError as e:
        # The stored chart cannot be placed or cannot be verified. That is a data
        # problem, not a malformed request, and it is never repaired by guessing.
        #
        # NAK-001-CORR-01. The refusal message names chart contents by design:
        # the subject, the published nakshatra, the derived one, the pada, the
        # lord, and for a domain failure the longitude itself. All of that is
        # diagnostic value for the operator and disclosure to the caller, so it
        # goes to the LOG and the response carries only the correlation
        # reference. The public detail is a fixed string with one variable in it;
        # nothing derived from the chart can reach it, whatever the engine says.
        correlation_id = uuid.uuid4().hex[:12]
        logger.exception("nakshatra engine refused chart [%s]: %s", correlation_id, e)
        raise HTTPException(
            status_code=422,
            detail=f"Certified chart could not be placed. Reference: {correlation_id}",
        )
    except HTTPException as exc:
        if exc.status_code in (401, 403):
            raise
        correlation_id = uuid.uuid4().hex[:12]
        logger.exception("nakshatra preparation upstream failure [%s]", correlation_id)
        raise HTTPException(
            status_code=500,
            detail=f"Nakshatra preparation failed. Reference: {correlation_id}",
        )
    except Exception:
        correlation_id = uuid.uuid4().hex[:12]
        logger.exception("nakshatra preparation failed [%s]", correlation_id)
        raise HTTPException(
            status_code=500,
            detail=f"Nakshatra preparation failed. Reference: {correlation_id}",
        )
