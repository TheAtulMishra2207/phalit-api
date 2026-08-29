"""
d10_report_routes.py — D10-008 · POST /d10report, the live report.

ONE PIPELINE, ALL IN PROCESS:

    resolver.resolve(chart_token)          the accepted chart resolver
      -> d10_routes._resolve_and_prepare   the accepted D10 preparation
      -> d1_engine.compute_d1              the accepted D1 preparation
      -> d9_routes.resolve_and_prepare     the accepted D9-R2 preparation
      -> build_core_findings               D10-003
      -> build_crosschart_findings         D10-004
      -> build_publication                 D10-006
      -> build_synthesis                   D10-007

NOTHING IS RECALCULATED HERE. This module contains no house derivation, no
dignity, no Chara Karaka, no Jaimini and no D9 contribution logic. It calls the
certified authorities and assembles their outputs.

NO HTTP CALL TO OUR OWN ENDPOINTS. Every step above is an in-process function
call, so the report cannot disagree with `/d10/prepare` about the same chart.

RELEASE 1 MAKES NO PROVIDER CALL. `build_synthesis` is invoked with no provider
output at all, and this module imports no HTTP client. The D10-007 provider
machinery stays certified and unused.

THE LEGACY ENDPOINT IS GONE, NOT FLAGGED. `name` and `chart_brief` are not
accepted anywhere in this file.
"""
from __future__ import annotations

import logging
import uuid
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException

from d1_chart_adapter import ChartAdapterError, to_certified_chart
from d1_contract import Varga
from d1_engine import compute_d1
from d1_routes import ChartNotFound, ChartResolver, get_chart_resolver
from d10_crosschart import D10CrossChartError, build_crosschart_findings
from d10_findings import D10FindingsError, build_core_findings
from d10_publication import D10PublicationError, build_publication
from d10_report_contract import (
    D10ReportRequest, D10ReportResponse, IntegratedReadingPublic,
    REPORT_ROUTE_VERSION,
)
from d10_routes import _require_doctrine, _resolve_and_prepare
from d10_synthesis import D10SynthesisError, build_synthesis

logger = logging.getLogger("phalit")

router = APIRouter()


def _fail(prefix: str, status: int = 500) -> HTTPException:
    """A correlation id, never the reason.

    The underlying errors name certificate values, out-of-domain numbers and
    internal module paths. None of that is the caller's business, and a report
    endpoint is the last place to start leaking it.
    """
    correlation_id = uuid.uuid4().hex[:12]
    logger.exception("%s [%s]", prefix, correlation_id)
    return HTTPException(
        status_code=status,
        detail=f"Report could not be produced. Reference: {correlation_id}")


def _d1_payload(snapshot: Dict[str, Any], chart_token: str) -> Dict[str, Any]:
    """The accepted D1 preparation, in process.

    `compute_d1` is the same function `/d1/prepare` calls. The wrapper below
    matches the shape D10-004 reads, and adds nothing to it.
    """
    certified = to_certified_chart(snapshot, chart_token, varga=Varga.D1)
    d1, _doctrine = compute_d1(certified, Varga.D1)
    return {"chart_token": chart_token, "d1": d1.dict()}


def build_report(chart_token: str, snapshot: Dict[str, Any]) -> D10ReportResponse:
    """Assemble the certified report. Pure with respect to the snapshot.

    Every layer receives the SAME chart token, and D10-006 and D10-007 each
    check three-way identity before doing any work — so a mismatch anywhere in
    this pipeline is a refusal rather than a blended report.
    """
    doctrine = _require_doctrine()

    # The certified snapshot, carrying its identity. D10-006 refuses a naked
    # planets mapping precisely so this cannot be assembled from two charts.
    certified_chart = dict(snapshot)
    certified_chart["chart_token"] = chart_token

    d10_payload = _resolve_and_prepare(chart_token, snapshot, doctrine).dict()
    d1_payload = _d1_payload(snapshot, chart_token)

    # D9-R2, in process. Imported here rather than at module scope so a D9
    # doctrine that is not yet configured is a runtime refusal on this route
    # instead of an import-time failure for the whole service.
    import d9_routes
    d9_payload = d9_routes.resolve_and_prepare(snapshot, chart_token)

    findings = build_core_findings(d10_payload)
    crosschart = build_crosschart_findings(d10_payload, d1_payload, d9_payload)
    publication = build_publication(findings, crosschart, certified_chart)

    # RELEASE 1 · NO PROVIDER. No response is passed and none is requested.
    synthesis = build_synthesis(findings, crosschart, publication)

    return D10ReportResponse(
        route_version=REPORT_ROUTE_VERSION,
        chart_token=chart_token,
        publication=publication,
        # The composed reading only. `source`, `atom_id`, `word_count` and
        # `provider_rejected_reason` stay server-side.
        integrated_reading=IntegratedReadingPublic(
            text=synthesis.integrated_reading.text),
    )


@router.post("/d10report", response_model=D10ReportResponse)
async def d10_report(req: D10ReportRequest,
                     resolver: ChartResolver = Depends(get_chart_resolver)):
    try:
        snapshot = await resolver.resolve(req.chart_token)
    except ChartNotFound:
        # Unknown, expired, revoked and cross-owner all look identical here.
        raise HTTPException(status_code=404,
                            detail="Unknown or expired chart_token.")
    except HTTPException as exc:
        if exc.status_code in (401, 403):
            raise                      # deliberate auth statuses survive
        raise _fail("d10report chart resolver upstream failure")
    except Exception:
        raise _fail("d10report chart resolver failed")

    try:
        return build_report(req.chart_token, snapshot)
    except HTTPException:
        raise                          # the D10 preparation's own 422
    except (ChartAdapterError, D10FindingsError, D10CrossChartError,
            D10PublicationError, D10SynthesisError, KeyError, TypeError,
            ValueError):
        raise _fail("d10report assembly failed", status=422)
    except Exception:
        raise _fail("d10report failed")
