"""D7-002-CORR-05 · POST /d7/prepare.

ONE RESOLVER, ONE DOOR. This module depends on the SAME `get_chart_resolver`
function object that `install_d1()` overrides. No second `dependency_overrides`,
no second snapshot store, no second session path, no second auth.

THREE INTEGRATION CORRECTIONS IN THIS REVISION
----------------------------------------------
1. The route is `async` and `await`s `resolver.resolve(...)`. The prior version
   called it synchronously, which against a real host returns a coroutine and
   fails on first contact — invisible before, because the route itself was
   never exercised by a test.

2. `to_certified_chart(body, chart_token)` is called with the accepted
   signature, and `ChartAdapterError` is caught into the neutral 422.

3. Certification is a GATE and nothing more. The return value is DISCARDED.
   D7 reads the already-resolved snapshot the resolver returned, which is the
   persisted /chart body. The prior versions both got this wrong: one
   subscripted the certificate as a dict, the next reached for attributes the
   production CertifiedChart does not expose.

D7 keeps NO copy of the certificate: no engine version, ayanamsha, house system,
node type or backend literal appears anywhere in the D7 stack.
"""

import logging
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException

from d1_routes import ChartNotFound, ChartResolver, get_chart_resolver
from d1_chart_adapter import ChartAdapterError, to_certified_chart

import d7_engine
import d7_fd1b
import d7_predicates
import d7_rules
import d7_selectors
import d7_timing
from d7_client_reading import (
    PublicationViolation,
    build_client_reading,
    build_provider_payload,
)
from d7_contract import D7PrepareRequest, D7PrepareResponse
from d7_engine import D7Doctrine, D7InputError
from d7_joins import build_d1_join, build_d9_join
from d7_predicates import D7PredicateDoctrine

log = logging.getLogger(__name__)
router = APIRouter(tags=["d7"])

MODULE_VERSION = "d7-002-corr-05"

_SIGN_LORDS: Optional[List[str]] = None
_CONFIGURED = False


def configure_d7_doctrine(engine_doctrine: D7Doctrine,
                          predicate_doctrine: D7PredicateDoctrine) -> None:
    """Inject doctrine. Called from main.py BELOW the tables it reads."""
    global _SIGN_LORDS, _CONFIGURED
    d7_engine.configure_engine_doctrine(engine_doctrine)
    d7_predicates.configure_predicate_doctrine(predicate_doctrine)
    _SIGN_LORDS = list(engine_doctrine.sign_lords)
    _CONFIGURED = True


def _require_doctrine() -> List[str]:
    if not _CONFIGURED or _SIGN_LORDS is None:
        raise HTTPException(status_code=503, detail="D7 doctrine not configured.")
    return _SIGN_LORDS


def resolve_and_prepare(snapshot: Dict[str, Any],
                        chart_token: str,
                        gender: str) -> Dict[str, Any]:
    """THE ONE PIPELINE. Each layer runs exactly once.

    Shared by `/d7/prepare` and by the `/d7report` narrative path, so the
    provider can never be handed a preparation the prepare route would not have
    produced.
    """
    sign_lords = _require_doctrine()

    # ── the certification GATE, and nothing more ─────────────────────────────
    #
    # CORR-02 · spec B. `to_certified_chart` is used STRICTLY as a gate. Its
    # return value is discarded: D7 does not read `.chart`, `.body`, `.raw`,
    # `.snapshot`, `.lagna` or `.planets` off it, because the production
    # CertifiedChart exposes none of them. The helper that reached into it is
    # deleted outright; its name is not repeated here so a release grep is clean.
    #
    # Once the gate passes, D7 reads the ALREADY-RESOLVED snapshot the resolver
    # returned. That is the persisted /chart body and it is the only source.
    to_certified_chart(snapshot, chart_token)

    lagna = snapshot["lagna"]
    planets = snapshot["planets"]

    facts = d7_engine.build_d7_facts(lagna, planets, gender)
    surface = d7_predicates.build_predicate_surface(facts, sign_lords)
    fd1b = d7_fd1b.build_fd1b_surface(facts, planets)
    surface.update(fd1b)

    manifest = d7_rules.evaluate_all(surface)
    archetypes = d7_selectors.select_all_archetypes(manifest)

    conception = d7_selectors.select_conception_vitality(
        d7_selectors.conception_vitality_conditions(fd1b))
    lineage = d7_selectors.select_lineage_scope(
        d7_selectors.lineage_scope_conditions(fd1b))

    vectors = d7_selectors.build_parental_vectors(
        manifest, mapping=d7_rules.RULE_VECTORS)
    parental = d7_selectors.select_parental_strength(vectors)

    joins = {
        "d1": build_d1_join(lagna, planets, sign_lords),
        "d9": build_d9_join(lagna, planets, sign_lords),
    }

    # The Jupiter window targets the D1 FIFTH LORD's D1 sign (spec I).
    d1_fifth_lord = joins["d1"]["h5_lord"]["graha"]
    d1_fifth_lord_sign = (planets.get(d1_fifth_lord) or {}).get("sign_index")

    # CORR-03 · E. Saturn stabilisation is measured from the D7 PLACEMENT of the
    # D7 lagna lord, not its D1 sign. The two differ on most charts, and reading
    # the D1 sign here silently evaluated a D7 timing rule in D1 space.
    lagna_lord = facts["d7_lagna"]["lord"]
    lagna_lord_sign = (facts["placements"].get(lagna_lord) or {}).get("d7_sign_index")

    timing = d7_timing.build_timing(
        snapshot, facts, lagna["sign_index"],
        d1_fifth_lord_sign_index=d1_fifth_lord_sign,
        lagna_lord_sign_index=lagna_lord_sign,
        lagna_lord_afflicted=bool(fd1b.get("afflicted_lagna_lord")))

    snapshot_fields = {
        "conception_vitality": conception,
        "lineage_scope": lineage,
        "primary_parental_strength": parental,
    }

    client_reading = build_client_reading(facts, archetypes, snapshot_fields,
                                          timing, joins)

    return {
        "client_reading": client_reading,
        "engine": {
            "d7_lagna": facts["d7_lagna"],
            "placements": facts["placements"],
            "houses": facts["houses"],
            "key_houses": facts["key_houses"],
            "putrakaraka": facts["putrakaraka"],
            "sphuta": facts["sphuta"],
            "sequence": facts["sequence"],
            "predicate_surface": surface,
            "fd1b_surface": fd1b,
            "rule_manifest": manifest,
            "archetype_selection": archetypes,
            "quick_snapshot_selection": snapshot_fields,
            "parental_vectors": vectors,
            "joins": joins,
            "timing": timing,
            "module_version": MODULE_VERSION,
        },
    }


async def resolve_token(resolver: ChartResolver, chart_token: str) -> Dict[str, Any]:
    """Await the shared resolver and map its failures to the D7 error boundary."""
    try:
        return await resolver.resolve(chart_token)
    except ChartNotFound:
        raise HTTPException(status_code=404, detail="Unknown or expired chart_token.")
    except HTTPException:
        raise                       # 401 / 403 propagate untouched
    except Exception:
        cid = uuid.uuid4().hex[:12]
        log.exception("d7 resolve failed correlation_id=%s", cid)
        raise HTTPException(status_code=500,
                            detail=f"Internal error. Correlation id {cid}.")


def prepare_or_raise(snapshot: Dict[str, Any], chart_token: str,
                     gender: str) -> Dict[str, Any]:
    """Run the pipeline, mapping every failure class to a neutral response."""
    try:
        return resolve_and_prepare(snapshot, chart_token, gender)
    except ChartAdapterError:
        cid = uuid.uuid4().hex[:12]
        log.warning("d7 certification refused correlation_id=%s", cid, exc_info=True)
        raise HTTPException(
            status_code=422,
            detail=f"Chart data is not usable for D7. Correlation id {cid}.")
    except (D7InputError, KeyError, TypeError):
        cid = uuid.uuid4().hex[:12]
        log.warning("d7 unusable snapshot correlation_id=%s", cid, exc_info=True)
        raise HTTPException(
            status_code=422,
            detail=f"Chart data is not usable for D7. Correlation id {cid}.")
    except PublicationViolation:
        # A prohibited claim reached the wall. Fail CLOSED: nothing partial is
        # served, and the reason never reaches the client.
        cid = uuid.uuid4().hex[:12]
        log.error("d7 publication violation correlation_id=%s", cid, exc_info=True)
        raise HTTPException(status_code=500,
                            detail=f"Internal error. Correlation id {cid}.")
    except HTTPException:
        raise
    except Exception:
        cid = uuid.uuid4().hex[:12]
        log.exception("d7 prepare failed correlation_id=%s", cid)
        raise HTTPException(status_code=500,
                            detail=f"Internal error. Correlation id {cid}.")


@router.post("/d7/prepare", response_model=D7PrepareResponse)
async def d7_prepare(
        req: D7PrepareRequest,
        resolver: ChartResolver = Depends(get_chart_resolver)) -> Dict[str, Any]:
    _require_doctrine()
    snapshot = await resolve_token(resolver, req.chart_token)
    prepared = prepare_or_raise(snapshot, req.chart_token, req.gender)
    # D7-003 · PUBLIC RESPONSE. `engine` is not returned. The frontend renders
    # `client_reading` and can never reconstruct interpretation from internals.
    return {
        "chart_token": req.chart_token,
        "gender": req.gender,
        "module_version": MODULE_VERSION,
        "client_reading": prepared["client_reading"],
    }
