"""D7-002 · request and response contract. pydantic v1 (1.10.13), matching prod.

A note earned the hard way in D5: a pydantic `response_model` SILENTLY DROPS
keys its schema does not declare. A correctly built `client_reading` was once
discarded at serialisation with HTTP 200 and no error anywhere. So the response
model here declares `client_reading` as a permissive `Dict[str, Any]` rather
than a nested schema that would have to be kept in lockstep with
d7_client_reading, and the route asserts the key survives serialisation.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, StrictStr, validator

GENDERS = ("male", "female")


class D7PrepareRequest(BaseModel):
    """Token plus gender. No birth data, ever.

    Gender is part of request identity because Beeja/Kshetra selection is
    gender-dependent and gender is not carried by the certified natal snapshot.
    The token stays OPAQUE — D7 invents no semantics for its characters, so
    there is no regex, only a length bound.
    """
    chart_token: StrictStr = Field(..., min_length=8, max_length=256)
    gender: StrictStr

    @validator("gender")
    def _gender_known(cls, v: str) -> str:
        lowered = v.strip().lower()
        if lowered not in GENDERS:
            raise ValueError("gender must be 'male' or 'female'")
        return lowered

    class Config:
        extra = "forbid"   # every other field is rejected


class D7PrepareResponse(BaseModel):
    """D7-003 · the PUBLIC contract. `engine` is deliberately absent.

    The browser receives the safe reading and nothing else. Engine evidence —
    rule manifest, predicate surface, weights, selections — stays server-side
    for QA and the internal pipeline, reachable through
    `d7_routes.resolve_and_prepare`, never over the wire.
    """
    chart_token: str
    gender: str
    module_version: str
    client_reading: Dict[str, Any]

    class Config:
        extra = "forbid"
