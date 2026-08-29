"""
d10_routes.py — D10-002 · POST /d10/prepare.

Built to the ACCEPTED boundary that d5_routes.py, pratiphala_routes.py and
nakshatra_routes.py already share, reusing their resolution contract rather
than restating it:

    from d1_routes import ChartNotFound, ChartResolver, get_chart_resolver

ONE RESOLVER, ONE DOOR. This module declares no snapshot store, no session
path, no caller dependency, no authentication and no `dependency_overrides`
call. It depends on the SAME `d1_routes.get_chart_resolver` function object
that `install_d1()` already overrode, so /d10/prepare inherits the
caller-scoped resolver automatically. A second binding here would be a second
door onto one snapshot store, and a second token system is forbidden outright.

NO ASTRONOMY IS RECALCULATED. The route resolves the certified snapshot and
reads what /chart already certified. It accepts no birth data and no astrology:
`D10PrepareRequest` carries a chart_token and forbids every other field.

CERTIFIED PROVENANCE. A resolved snapshot is put through the accepted D1
adapter's certificate gate BEFORE any D10 fact is computed. D10 keeps no copy
of the certificate: no engine version, no ayanamsha model, no house system, no
node type and no ephemeris backend literal appears in this file, so a future
change to the certificate cannot leave a stale second copy here disagreeing
with the first.

THE PROVIDER IS NOT PRESENT. There is no import of requests, httpx or anthropic
in this file and no call to /d10report. The legacy browser D10 path is
untouched and still live; this route runs beside it.
"""
from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, Mapping, Tuple

from fastapi import APIRouter, Depends, HTTPException

# REUSED, NOT REDEFINED. One resolver abstraction, one dependency provider.
from d1_routes import ChartNotFound, ChartResolver, get_chart_resolver
# REUSED, NOT RETYPED. The certified-provenance gate is the accepted D1
# adapter's, used exactly as d5_routes depends on it.
from d1_contract import Varga
from d1_chart_adapter import ChartAdapterError, to_certified_chart

from d10_contract import D10PrepareRequest, D10PrepareResponse, build_response
from d10_engine import ALL_GRAHAS, D10Doctrine, D10DomainError, build_d10_facts

router = APIRouter(tags=["d10"])
logger = logging.getLogger(__name__)

#: The accepted doctrine is INJECTED at wiring time, using the same
#: configure_*() idiom d4_routes and d5_routes use. This keeps d10_engine free
#: of any copy of the shared sign, lord and dignity tables and avoids importing
#: main from a route module.
_doctrine: "D10Doctrine | None" = None


def configure_d10_doctrine(doctrine: D10Doctrine) -> None:
    global _doctrine
    _doctrine = doctrine


def _require_doctrine() -> D10Doctrine:
    """FAIL CLOSED. An unconfigured deployment must not silently serve a D10
    layer graded against nothing."""
    if _doctrine is None:
        raise HTTPException(status_code=503,
                            detail="D10 preparation is unavailable.")
    return _doctrine


class D10SnapshotError(ValueError):
    """The resolved snapshot is not shaped like a certified chart. Internal
    only: the message never reaches a response."""


def _read_certified_facts(payload: Any) -> Tuple[Dict[str, Any],
                                                 Dict[str, Dict[str, Any]],
                                                 Dict[str, Any]]:
    """Read ONLY what D10-002 needs from the certified snapshot.

    The read set is NAMED here rather than taken wholesale:

        lagna:  sign_index, d10_sign_index
        graha:  sign_index, d10_sign_index, retrograde, combust,
                karaka_arcsecond

    `degree` IS NOT READ. The certified `d10_sign_index` is the D10 placement
    authority; the public `degree` is rounded to four decimals and re-deriving
    a placement from it can cross a 3-degree Dasamsa boundary or fall outside
    the mapping's domain entirely. Nothing in the D10 path touches it.

    `d10_sign_index` is REQUIRED. A snapshot that lacks it predates the
    certified D10 fields and there is no D10 placement to publish, so the route
    refuses rather than serving a chart derived from a rounded degree.

    `karaka_arcsecond` is OPTIONAL AT THIS SEAM ON PURPOSE: a snapshot minted
    before it existed simply lacks it, and the engine then returns Chara Karaka
    state INVALID — a determinate answer — rather than refusing a chart whose
    placements, houses, lordships and dignities are all perfectly good. The two
    fields fail differently because they carry different weight.
    """
    if not isinstance(payload, dict):
        raise D10SnapshotError("snapshot is not an object")
    lagna = payload.get("lagna")
    planets = payload.get("planets")
    if not isinstance(lagna, dict) or not isinstance(planets, dict):
        raise D10SnapshotError("snapshot lacks lagna or planets")

    def pick(rec: Any, what: str, need_flags: bool) -> Dict[str, Any]:
        if not isinstance(rec, dict):
            raise D10SnapshotError(f"{what} record is not an object")
        for key in ("sign_index", "d10_sign_index"):
            if key not in rec:
                raise D10SnapshotError(f"{what} record lacks {key}")
        out: Dict[str, Any] = {"sign_index": rec["sign_index"],
                               "d10_sign_index": rec["d10_sign_index"]}
        if need_flags:
            for key in ("retrograde", "combust"):
                if key not in rec:
                    raise D10SnapshotError(f"{what} record lacks {key}")
                out[key] = rec[key]
            if "karaka_arcsecond" in rec:
                out["karaka_arcsecond"] = rec["karaka_arcsecond"]
        return out

    d10_lagna = pick(lagna, "lagna", need_flags=False)
    d10_planets = {}
    for graha in ALL_GRAHAS:
        if graha not in planets:
            raise D10SnapshotError("snapshot is missing a graha")
        d10_planets[graha] = pick(planets[graha], graha, need_flags=True)

    meta = payload.get("calculation_meta")
    if not isinstance(meta, dict):
        raise D10SnapshotError("snapshot lacks calculation_meta")
    # A SHAPE check only. The certificate itself is enforced by the accepted D1
    # adapter in _assert_certified_provenance below, never here.
    return d10_lagna, d10_planets, meta


def _assert_certified_provenance(payload: Any, chart_token: str) -> None:
    """The accepted certified-provenance gate, reused wholesale and called
    PURELY AS A GATE — the return value is discarded, because everything D10
    needs is read from the certified snapshot by _read_certified_facts.

    The raised ChartAdapterError carries the mismatched value and may name the
    ephemeris backend, so it is caught at the route boundary and never
    published.
    """
    to_certified_chart(payload, chart_token, varga=Varga.D1)


def _resolve_and_prepare(chart_token: str, chart_payload: Any,
                         doctrine: D10Doctrine) -> D10PrepareResponse:
    """THE ONE ACCEPTED D10 PREPARATION PIPELINE.

        certified provenance gate
        -> read certified snapshot
        -> build D10 mechanical facts   (mapping, houses, lordship, dignity,
                                         chara karaka, jaimini)
        -> build the response

    Every layer runs EXACTLY ONCE and nothing is evaluated twice, so no field in
    the payload can disagree with another field derived from the same input.
    """
    try:
        # The provenance gate runs BEFORE any D10 fact is derived.
        _assert_certified_provenance(chart_payload, chart_token)
        lagna, planets, meta = _read_certified_facts(chart_payload)
        facts = build_d10_facts(lagna, planets, doctrine)
    except (ChartAdapterError, D10SnapshotError, D10DomainError,
            KeyError, TypeError, ValueError):
        # A correlation id, never the reason. The adapter error names the
        # mismatched certificate value; the domain error names the graha and the
        # out-of-domain number. Neither is the caller's business.
        correlation_id = uuid.uuid4().hex[:12]
        logger.exception("d10 snapshot failed certification [%s]", correlation_id)
        raise HTTPException(
            status_code=422,
            detail=f"Chart snapshot could not be prepared. Reference: {correlation_id}")

    return build_response(facts=facts, chart_token=chart_token,
                          calculation_meta=meta)


@router.post("/d10/prepare", response_model=D10PrepareResponse)
async def d10_prepare(req: D10PrepareRequest,
                      resolver: ChartResolver = Depends(get_chart_resolver)):
    doctrine = _require_doctrine()
    try:
        chart_payload = await resolver.resolve(req.chart_token)
    except ChartNotFound:
        # Unknown, expired, revoked and cross-owner all look identical here.
        raise HTTPException(status_code=404, detail="Unknown or expired chart_token.")
    except HTTPException as exc:
        # ONLY deliberate authentication statuses survive. Everything else is
        # correlated and generalised: an upstream 502/503 can carry response
        # text naming internal hosts.
        if exc.status_code in (401, 403):
            raise
        correlation_id = uuid.uuid4().hex[:12]
        logger.exception("d10 chart resolver upstream failure [%s]", correlation_id)
        raise HTTPException(status_code=500,
                            detail=f"Chart lookup failed. Reference: {correlation_id}")
    except Exception:
        correlation_id = uuid.uuid4().hex[:12]
        logger.exception("d10 chart resolver failed [%s]", correlation_id)
        raise HTTPException(status_code=500,
                            detail=f"Chart lookup failed. Reference: {correlation_id}")

    return _resolve_and_prepare(req.chart_token, chart_payload, doctrine)
