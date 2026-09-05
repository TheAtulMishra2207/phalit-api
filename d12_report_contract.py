"""d12_report_contract.py — the /d12report request and response shapes.

D12-006A. The request is `{chart_token}` and nothing else. The legacy contract —
name, chart_brief, father_maraka, mother_maraka, moksha_insights — is refused by
`extra = forbid` with a 422, which is the point: the old payload architecture is
condemned, not merely unused.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Extra, StrictStr

from d12_publication_contract import D12Report

REPORT_ROUTE_VERSION = "d12-report-1.0"


class D12ReportRequest(BaseModel):
    """chart_token only. Extras forbidden."""
    chart_token: StrictStr

    class Config:
        extra = Extra.forbid
        min_anystr_length = 8


class D12ReportResponse(BaseModel):
    """One complete typed response 006B can render with no astrology at all.

    The frontend computes no house, lord, dignity, vargottama, Devatā, residue
    domain, release weight, D1xD12 class or tension: every one of those arrives
    here already decided and already worded.
    """
    route_version: StrictStr = REPORT_ROUTE_VERSION
    report: D12Report

    class Config:
        extra = Extra.forbid
