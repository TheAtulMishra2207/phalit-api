"""
d5_routes.py — D5-001 · POST /d5/prepare.

Built to the ACCEPTED boundary that pratiphala_routes.py, nakshatra_routes.py
and the released d4_routes.py all share, reusing their resolution contract
rather than restating it:

    from d1_routes import ChartNotFound, ChartResolver, get_chart_resolver

ONE RESOLVER, ONE DOOR. This module declares no snapshot store, no session path,
no caller dependency, no authentication and no `dependency_overrides` call. It
depends on the SAME `d1_routes.get_chart_resolver` function object that
`install_d1()` already overrode, so /d5/prepare inherits the caller-scoped
resolver automatically. A second binding here would be a second door onto one
snapshot store.

NO ASTRONOMY IS RECALCULATED. The route resolves the certified snapshot and
reads what /chart already certified. It accepts no birth data: `D5PrepareRequest`
carries a chart_token and forbids every other field.

CERTIFIED PROVENANCE. A resolved snapshot is put through the accepted D1
adapter's certificate gate BEFORE any D5 fact is computed. D5 keeps no copy of
the certificate: no engine version, no ayanamsha model, no house system, no node
type and no ephemeris backend literal appears in this file, so a future change to
the certificate cannot leave a stale second copy here disagreeing with the first.

WHAT IS READ FROM THE SNAPSHOT, AND THE TWO READS BEYOND THE D4 SET. D4 reads
`sign_index` and `degree` only. D5-001 reads two further certified fields, both
NAMED HERE rather than slipped in:

  * `longitude` — PROVENANCE ONLY. The Founder placement payload requires
    `source_longitude`, so the certified value is carried through unchanged. It
    is never an arithmetic input: `d5_engine` takes the segment from `degree`,
    because the chart engine rounds `degree` and `longitude` to four decimals
    INDEPENDENTLY from the same underlying value and they can therefore differ
    in the fourth place. The chart the reader was shown was drawn from `degree`.
  * `d9_sign_index` — required by the Karakamsha reference, which must read the
    sign AK occupies in D9. It is published by the certified snapshot and is
    carried through unchanged; the D9 division is never recomputed here.

Both are absent from the released D4 read set purely because D4 had no use for
them, not because they are uncertified.
"""
from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, Tuple

from fastapi import APIRouter, Depends, HTTPException

# REUSED, NOT REDEFINED. One resolver abstraction and one dependency provider
# serve every prepare route.
from d1_routes import ChartNotFound, ChartResolver, get_chart_resolver
# REUSED, NOT RETYPED. The certified-provenance gate is the accepted D1
# adapter's, used exactly as the accepted pratiphala_routes.py depends on it.
from d1_contract import Varga
from d1_chart_adapter import ChartAdapterError, to_certified_chart

from d5_contract import D5PrepareRequest, D5PrepareResponse, build_response
from d5_engine import ALL_GRAHAS, D5Doctrine, D5DomainError, build_d5_facts
import d5_operational as OPS
import d5_report as REPORT
import d5_rules as RULES
import d5_scoring as SCORING
import d5_temporal_tri as TEMPORAL
from d5_rules import D5RulesDoctrine

router = APIRouter()
logger = logging.getLogger(__name__)

# The accepted doctrine is INJECTED at wiring time, using the same configure_*()
# idiom d1_wiring and d4_routes use. This keeps d5_engine free of any copy of
# the shared SIGNS and SIGN_LORDS tables and avoids importing main.py from a
# route module.
_doctrine: "D5Doctrine | None" = None


#: The scoring-side doctrine (the accepted exaltation table). Injected for the
#: same reason as the sign tables: one copy in the process.
_rules_doctrine: "D5RulesDoctrine | None" = None


def configure_d5_doctrine(doctrine: D5Doctrine,
                          rules_doctrine: "D5RulesDoctrine | None" = None) -> None:
    global _doctrine, _rules_doctrine
    _doctrine = doctrine
    if rules_doctrine is not None:
        _rules_doctrine = rules_doctrine


def _require_rules_doctrine() -> "D5RulesDoctrine":
    if _rules_doctrine is None:
        raise HTTPException(status_code=503,
                            detail="D5 preparation is unavailable.")
    return _rules_doctrine


def _require_doctrine() -> D5Doctrine:
    """FAIL CLOSED. An unconfigured deployment must not silently serve a D5
    layer computed from nothing."""
    if _doctrine is None:
        raise HTTPException(status_code=503,
                            detail="D5 preparation is unavailable.")
    return _doctrine


class D5SnapshotError(ValueError):
    """The resolved snapshot is not shaped like a certified chart. Internal
    only: the message never reaches a response."""


def _read_certified_facts(payload: Any) -> Tuple[Dict[str, Any],
                                                 Dict[str, Dict[str, Any]],
                                                 Dict[str, Any]]:
    """Read ONLY what D5-001 needs from the certified snapshot."""
    if not isinstance(payload, dict):
        raise D5SnapshotError("snapshot is not an object")
    lagna = payload.get("lagna")
    planets = payload.get("planets")
    if not isinstance(lagna, dict) or not isinstance(planets, dict):
        raise D5SnapshotError("snapshot lacks lagna or planets")

    def pick(rec: Any, what: str, need_d9: bool) -> Dict[str, Any]:
        if not isinstance(rec, dict):
            raise D5SnapshotError(f"{what} record is not an object")
        if "sign_index" not in rec or "degree" not in rec:
            raise D5SnapshotError(f"{what} record lacks sign_index or degree")
        out = {"sign_index": rec["sign_index"], "degree": rec["degree"],
               "longitude": rec.get("longitude")}
        if need_d9:
            if "d9_sign_index" not in rec:
                raise D5SnapshotError(f"{what} record lacks d9_sign_index")
            out["d9_sign_index"] = rec["d9_sign_index"]
        return out

    d5_lagna = pick(lagna, "lagna", need_d9=False)
    d5_planets = {}
    for graha in ALL_GRAHAS:
        if graha not in planets:
            raise D5SnapshotError("snapshot is missing a graha")
        d5_planets[graha] = pick(planets[graha], graha, need_d9=True)

    meta = payload.get("calculation_meta")
    if not isinstance(meta, dict):
        raise D5SnapshotError("snapshot lacks calculation_meta")
    # NOTE: a SHAPE check only. The certificate itself is enforced by the
    # accepted D1 adapter in _assert_certified_provenance below, never here.
    return d5_lagna, d5_planets, meta


def _assert_certified_provenance(payload: Any, chart_token: str) -> None:
    """The accepted certified-provenance gate, reused wholesale and called
    PURELY AS A GATE — the result is discarded, because everything D5 needs is
    read from the certified snapshot by _read_certified_facts.

    The raised ChartAdapterError carries the mismatched value and may name the
    backend, so it is caught at the route boundary and never published.
    """
    to_certified_chart(payload, chart_token, varga=Varga.D1)


async def _resolve_and_prepare(chart_token: str, chart_payload: Any,
                               doctrine: D5Doctrine) -> D5PrepareResponse:
    """THE ONE ACCEPTED D5 PREPARATION PIPELINE.

    Order is load-bearing and every layer runs EXACTLY ONCE:

        certified provenance gate
        -> read certified snapshot
        -> build D5 facts
        -> build certified operational facts (one transit call)
        -> evaluate the 67 static rules ONCE
        -> derive the Lock 5 and Lock 6 participant sets from THOSE outcomes
        -> evaluate timing ONCE
        -> evaluate triangulation ONCE
        -> assess readiness
        -> build the score
        -> build the report payload from that score
        -> build the response

    THERE IS NO SECOND EVALUATION. The report is assembled from the same
    outcomes the score was computed from, so a card can never disagree with the
    number printed beside it — the failure the accepted D4 hierarchy exists to
    prevent. A call-count spy asserts one call per layer.
    """
    rules_doctrine = _require_rules_doctrine()
    try:
        # The provenance gate runs BEFORE any D5 fact is derived.
        _assert_certified_provenance(chart_payload, chart_token)
        lagna, planets, meta = _read_certified_facts(chart_payload)
        facts = build_d5_facts(lagna, planets, doctrine)
    except (ChartAdapterError, D5SnapshotError, D5DomainError,
            KeyError, TypeError, ValueError):
        correlation_id = uuid.uuid4().hex[:12]
        logger.exception("d5 snapshot failed certification [%s]", correlation_id)
        raise HTTPException(
            status_code=422,
            detail=f"Chart snapshot could not be prepared. Reference: {correlation_id}")

    try:
        operational = OPS.build_operational_facts(chart_payload)
        rule_inputs = operational.rule_inputs()

        # ONE static evaluation. The participant sets are derived from these
        # very outcomes, and these very outcomes are what gets scored.
        static_outcomes = RULES.evaluate_all(facts, doctrine, rules_doctrine,
                                             rule_inputs)
        temporal_inputs = OPS.build_temporal_inputs(
            operational,
            RULES.derive_positive_fired_yoga_participants(static_outcomes, facts,
                                                          doctrine),
            RULES.derive_d5_raj_yoga_participants(static_outcomes, facts,
                                                  doctrine))
        timing_outcomes = TEMPORAL.evaluate_timing(
            facts, doctrine, rules_doctrine, temporal_inputs, rule_inputs)
        triangulation_outcomes = TEMPORAL.evaluate_triangulation(
            facts, doctrine, rules_doctrine, temporal_inputs, rule_inputs)
        score = SCORING.build_score(static_outcomes, timing_outcomes,
                                    triangulation_outcomes)
        report = REPORT.build_report_payload(facts, score, timing_outcomes,
                                             triangulation_outcomes)
    except (OPS.D5OperationalError, SCORING.D5ScoringError) as exc:
        # A SERVER-SIDE SOURCE GAP, not a caller error. Misclassifying it as a
        # 4xx would tell the customer their request was wrong when it was not.
        # The blocker is logged in full and NEVER published: naming Graha
        # Yuddha, combustion, D9 or a Tithi would leak the internal shape.
        correlation_id = uuid.uuid4().hex[:12]
        logger.exception("d5 operational source unavailable [%s]: %s",
                         correlation_id, exc)
        raise HTTPException(
            status_code=503,
            detail=f"D5 scoring is temporarily unavailable. Reference: {correlation_id}")
    except (D5DomainError, KeyError, TypeError, ValueError):
        correlation_id = uuid.uuid4().hex[:12]
        logger.exception("d5 preparation failed [%s]", correlation_id)
        raise HTTPException(
            status_code=422,
            detail=f"Chart snapshot could not be prepared. Reference: {correlation_id}")

    transits = operational.transits
    return build_response(
        facts=facts, chart_token=chart_token, calculation_meta=meta,
        operational={
            "score_ready": True,
            "current_period": {"mahadasha": operational.mahadasha_lord,
                               "antardasha": operational.antardasha_lord},
            # THE SAME transit snapshot the score was computed from.
            "current_transits": {
                "as_of": transits.as_of,
                "jupiter_sign_index": transits.sign_index_by_body.get("Jupiter"),
                "saturn_sign_index": transits.sign_index_by_body.get("Saturn")},
            "source_status": operational.source_status(),
        },
        scoring={
            "score_ready": score["score_ready"],
            "final_score": score["final_score"],
            "score_band": score["score_band"],
            "rules": score["rules"],
            "core_authority": score["core_authority"],
            "purva_punya": score["purva_punya"],
            "primary_power_vector": score["primary_power_vector"],
            "triangulation_bindings": score["triangulation_bindings"],
        },
        report=report)


@router.post("/d5/prepare", response_model=D5PrepareResponse)
async def d5_prepare(req: D5PrepareRequest,
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
        logger.exception("d5 chart resolver upstream failure [%s]", correlation_id)
        raise HTTPException(status_code=500,
                            detail=f"Chart lookup failed. Reference: {correlation_id}")
    except Exception:
        correlation_id = uuid.uuid4().hex[:12]
        logger.exception("d5 chart resolver failed [%s]", correlation_id)
        raise HTTPException(status_code=500,
                            detail=f"Chart lookup failed. Reference: {correlation_id}")

    return await _resolve_and_prepare(req.chart_token, chart_payload, doctrine)
