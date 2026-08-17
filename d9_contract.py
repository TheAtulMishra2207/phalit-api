"""D9-002 · request and response contract. pydantic v1 (1.10.13), matching prod.

Two lessons are encoded here rather than left to a reviewer.

D5: a pydantic `response_model` SILENTLY DROPS keys its schema does not declare.
A correctly built payload was once discarded at serialisation with HTTP 200 and
no error anywhere. So `report` is a permissive `Dict[str, Any]` rather than a
nested schema that would have to be kept in lockstep with `d9_client_reading`,
and the route asserts the key survives serialisation.

D7: the public response carries no `engine`. It is declared out of the response
model too, so a later edit cannot put it back on the wire.

D9-B22: the legacy `/d9report` took `{name, chart_brief: Dict[str, Any]}` and
therefore accepted astrology calculated by the browser, with no chart identity
and no way to certify anything. Both models below take a `chart_token` and
`extra = "forbid"`, so a client-authored `chart_brief` is a 422 at the boundary
rather than a silently honoured payload.
"""

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, StrictStr, validator


class D9PrepareRequest(BaseModel):
    """Token only. No birth data, no gender, no client astrology, ever.

    The token stays OPAQUE — D9 invents no semantics for its characters, so
    there is no regex, only a length bound.
    """
    chart_token: StrictStr = Field(..., min_length=8, max_length=256)

    class Config:
        extra = "forbid"


class D9PrepareResponse(BaseModel):
    """The PUBLIC R2 contract. `engine` is deliberately absent.

    ONE REPORT AUTHORITY: the R1 publication model is not carried alongside R2.

    The browser receives the safe reading and nothing else. Engine evidence —
    fired rule ids, selection scores, certified dignity in its raw vocabulary —
    stays server-side for QA, reachable through `d9_routes.resolve_and_prepare`,
    never over the wire.
    """
    chart_token: str
    route_version: str
    report_version: str
    report: Dict[str, Any]

    class Config:
        extra = "forbid"


class D9ReportRequest(BaseModel):
    """GENUINELY TOKEN-ONLY. Nothing astrological, and no identity either.

    Flight 11 accepted an optional `name` and forwarded it to the provider. The
    provider selects identifiers and writes no prose, so the name changed nothing
    in the output — it was an unnecessary PII transfer. `extra = "forbid"` now
    rejects it at the boundary with a 422 naming the field, so the drift cannot
    recur silently.

    The reader's name belongs in the local page header, never in a prompt.
    """
    chart_token: StrictStr = Field(..., min_length=8, max_length=256)

    class Config:
        extra = "forbid"


class D9ReportResponse(BaseModel):
    """Structured report plus the single bounded narrative section.

    `narrative` is nullable BY DESIGN. When the provider fails or returns
    something the publication wall rejects, the deterministic `report` must
    remain usable and only the prose goes neutral. A model that required
    `narrative` would force the whole response to fail with it.
    """
    chart_token: str
    route_version: str
    final_synthesis: Optional[str] = None
    synthesis_source: str = "deterministic"

    class Config:
        extra = "forbid"
