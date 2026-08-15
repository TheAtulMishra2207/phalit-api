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
    """The PUBLIC contract. `engine` is deliberately absent.

    The browser receives the safe reading and nothing else. Engine evidence —
    fired rule ids, selection scores, certified dignity in its raw vocabulary —
    stays server-side for QA, reachable through `d9_routes.resolve_and_prepare`,
    never over the wire.
    """
    chart_token: str
    module_version: str
    report: Dict[str, Any]

    class Config:
        extra = "forbid"


class D9ReportRequest(BaseModel):
    """The narrative route. Token in, and nothing astrological in.

    `name` is optional and is the ONLY non-astrological identity accepted. It is
    length-bounded and stripped; it never reaches a selector and is used solely
    to address the reader.
    """
    chart_token: StrictStr = Field(..., min_length=8, max_length=256)
    name: Optional[StrictStr] = Field(None, max_length=120)

    @validator("name")
    def _clean_name(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        cleaned = v.strip()
        return cleaned or None

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
    module_version: str
    report: Dict[str, Any]
    narrative: Optional[Dict[str, Any]] = None
    narrative_status: str

    class Config:
        extra = "forbid"
