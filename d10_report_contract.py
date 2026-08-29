"""
d10_report_contract.py — D10-008 · the public /d10report contract.

THE REQUEST IS A TOKEN. The legacy endpoint accepted `name` and a nineteen-key
`chart_brief` of browser-asserted astrology; this one accepts a chart token and
`extra = "forbid"`, so the old payload is a 422 rather than something the route
has to defend against.

THE RESPONSE IS CUSTOMER MATERIAL ONLY. The synthesis plan, the provider
request, atom alternatives, `default_atom_id`, `omitted_beats`,
`omission_reasons`, `provider_rejected_reason` and every internal diagnostic
have no field here. The browser has no use for them, and a field that does not
exist cannot leak.

`IntegratedReadingPublic` carries the composed reading and nothing else — no
`atom_id`, no `source`, no `word_count`, no beat enum. Those are how the
sentence was assembled, not the sentence.
"""
from __future__ import annotations

import pydantic
from pydantic import BaseModel, Field

from d10_publication_contract import D10Publication

_PYDANTIC_V2 = pydantic.VERSION.startswith("2")

if _PYDANTIC_V2:
    from pydantic import ConfigDict

    class Strict(BaseModel):
        model_config = ConfigDict(extra="forbid")
else:  # pragma: no cover - exercised only on a v1 host

    class Strict(BaseModel):
        class Config:
            extra = "forbid"


REPORT_ROUTE_VERSION = "d10-report-route-1.0.0"


class D10ReportRequest(Strict):
    """A chart token. Nothing else is accepted, and nothing else is needed.

    No birth data. No browser astrology. No `name`, no `chart_brief`. The
    legacy payload receives a 422 at the contract boundary before any handler
    runs.
    """
    chart_token: str = Field(min_length=8)


class IntegratedReadingPublic(Strict):
    """§14 as the customer receives it: one composed reading.

    Deliberately not the internal `IntegratedReading`. That model carries
    `source`, `beats[].atom_id`, `word_count` and `provider_rejected_reason` —
    provider mechanics, which §21 keeps off the wire.
    """
    text: str


class D10ReportResponse(Strict):
    route_version: str = REPORT_ROUTE_VERSION
    chart_token: str
    publication: D10Publication
    integrated_reading: IntegratedReadingPublic
