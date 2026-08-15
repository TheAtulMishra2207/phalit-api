"""D9-002 · POST /d9/prepare and POST /d9report.

ONE RESOLVER, ONE DOOR. This module depends on the SAME `get_chart_resolver`
function object that `install_d1()` overrides. No second `dependency_overrides`,
no second snapshot store, no second session path, no second auth.

FOUR INTEGRATION FACTS CARRIED FROM D7, EACH OF WHICH COST A CORRECTION THERE
-----------------------------------------------------------------------------
1. `resolver.resolve()` is a COROUTINE. The route is `async` and awaits it. A
   synchronous call passed 133 green tests in D7 because the route itself was
   never exercised.
2. `to_certified_chart(snapshot, chart_token)` takes two arguments and its
   return value is DISCARDED. It exposes no `.chart`, `.body`, `.raw`, `.lagna`
   or `.planets`. Two separate corrections were spent getting this wrong.
3. The public response carries no `engine`, and the response model declares it
   out too, so a later edit cannot put it back on the wire.
4. Escape every provider string at the render boundary. That is the frontend's
   `d1Esc`, already in place on the shared report path; the safety scanner here
   is a vocabulary guard, not an HTML sanitizer.

THE PROVIDER TRUST BOUNDARY IS THE POINT OF THIS TICKET
-------------------------------------------------------
The legacy `/d9report` accepted `chart_brief: Dict[str, Any]` — nineteen keys of
browser-computed astrology — with no token, no resolver and no way to certify
anything. `D9ReportRequest` now takes a token and forbids extra fields, so a
client-authored brief is a 422 at the boundary. The server rebuilds the approved
reading through the SAME pipeline `/d9/prepare` uses before the provider is
invoked, so the provider can never be handed a preparation the prepare route
would not have produced.
"""

import logging
import os
import uuid
from typing import Any, Callable, Dict, List, Optional

import requests
from fastapi import APIRouter, Depends, HTTPException

from d1_routes import ChartNotFound, ChartResolver, get_chart_resolver
from d1_chart_adapter import ChartAdapterError, to_certified_chart

import d9_engine
from d9_client_reading import (
    PublicationViolation,
    build_atom_pool,
    build_client_reading,
)
from d9_contract import (
    D9PrepareRequest,
    D9PrepareResponse,
    D9ReportRequest,
    D9ReportResponse,
)
from d9_engine import D9Doctrine, D9InputError
from d9_narrative import (
    MIN_ATOMS,
    MIN_SUBSTANTIVE_DOMAINS,
    NarrativeContractError,
    build_narrative,
    build_provider_instruction,
    build_provider_user_prompt,
)

log = logging.getLogger(__name__)
router = APIRouter(tags=["d9"])

MODULE_VERSION = "d9-002"

PROVIDER_MODEL = "claude-sonnet-4-6"
PROVIDER_MAX_TOKENS = 1400
PROVIDER_TIMEOUT = 60

_CONFIGURED = False
# Optional accepted-Pratiphala corroboration. A CALLABLE, injected by main.py.
# When it is not wired the corroboration blocks report unavailable, which is a
# reduced state and not a failure: no D9 reading depends on it.
_PRATIPHALA_PROVIDER: Optional[Callable[[Dict[str, Any], str], Dict[int, Dict[str, Any]]]] = None


def configure_d9_doctrine(engine_doctrine: D9Doctrine,
                          pratiphala_provider: Optional[Callable] = None) -> None:
    """Inject doctrine. Called from main.py BELOW the tables it reads."""
    global _CONFIGURED, _PRATIPHALA_PROVIDER
    d9_engine.configure_engine_doctrine(engine_doctrine)
    _PRATIPHALA_PROVIDER = pratiphala_provider
    _CONFIGURED = True


def _require_doctrine() -> None:
    if not _CONFIGURED:
        raise HTTPException(status_code=503, detail="D9 doctrine not configured.")


def _pratiphala_corroboration(snapshot: Dict[str, Any],
                              chart_token: str) -> Optional[Dict[int, Dict[str, Any]]]:
    """Accepted Pratiphala verdicts for houses 7, 8 and 10, or None.

    Contained at the call site: a Pratiphala failure must not abort a D9
    preparation, because D9's own readings come from Karakamsha and certified
    facts. The corroboration is additive.
    """
    if _PRATIPHALA_PROVIDER is None:
        return None
    try:
        return _PRATIPHALA_PROVIDER(snapshot, chart_token)
    except Exception:
        cid = uuid.uuid4().hex[:12]
        log.warning("d9 pratiphala corroboration unavailable correlation_id=%s",
                    cid, exc_info=True)
        return None


def resolve_and_prepare(snapshot: Dict[str, Any],
                        chart_token: str) -> Dict[str, Any]:
    """THE ONE PIPELINE. Each layer runs exactly once.

    Shared by `/d9/prepare` and by the `/d9report` narrative path, so the
    provider can never be handed a preparation the prepare route would not have
    produced.
    """
    _require_doctrine()

    # ── the certification GATE, and nothing more ─────────────────────────────
    #
    # `to_certified_chart` is used STRICTLY as a gate. Its return value is
    # discarded: D9 does not read `.chart`, `.body`, `.snapshot`, `.lagna` or
    # `.planets` off it, because the production CertifiedChart exposes none of
    # them. Once the gate passes, D9 reads the ALREADY-RESOLVED snapshot the
    # resolver returned. That is the persisted /chart body and it is the only
    # source.
    to_certified_chart(snapshot, chart_token)

    lagna = snapshot["lagna"]
    planets = snapshot["planets"]

    facts = d9_engine.build_d9_facts(lagna, planets)
    prati = _pratiphala_corroboration(snapshot, chart_token)
    report = build_client_reading(facts, prati)

    return {
        "report": report,
        "engine": {
            "d9_lagna": facts["d9_lagna"],
            "placements": facts["placements"],
            "atmakaraka": facts["atmakaraka"],
            "karakamsha": facts["karakamsha"],
            "ishta_devata": facts["ishta_devata"],
            "karakamsha_houses": facts["karakamsha_houses"],
            "integration": facts["integration"],
            "dusthana": facts["dusthana"],
            "pratiphala_corroboration": prati,
            "module_version": MODULE_VERSION,
        },
    }


async def resolve_token(resolver: ChartResolver, chart_token: str) -> Dict[str, Any]:
    """Await the shared resolver and map its failures to the D9 error boundary."""
    try:
        return await resolver.resolve(chart_token)
    except ChartNotFound:
        raise HTTPException(status_code=404, detail="Unknown or expired chart_token.")
    except HTTPException:
        raise                       # 401 / 403 propagate untouched
    except Exception:
        cid = uuid.uuid4().hex[:12]
        log.exception("d9 resolve failed correlation_id=%s", cid)
        raise HTTPException(status_code=500,
                            detail=f"Internal error. Correlation id {cid}.")


def prepare_or_raise(snapshot: Dict[str, Any], chart_token: str) -> Dict[str, Any]:
    """Run the pipeline, mapping every failure class to a neutral response."""
    try:
        return resolve_and_prepare(snapshot, chart_token)
    except ChartAdapterError:
        cid = uuid.uuid4().hex[:12]
        log.warning("d9 certification refused correlation_id=%s", cid, exc_info=True)
        raise HTTPException(
            status_code=422,
            detail=f"Chart data is not usable for D9. Correlation id {cid}.")
    except (D9InputError, KeyError, TypeError):
        cid = uuid.uuid4().hex[:12]
        log.warning("d9 unusable snapshot correlation_id=%s", cid, exc_info=True)
        raise HTTPException(
            status_code=422,
            detail=f"Chart data is not usable for D9. Correlation id {cid}.")
    except PublicationViolation:
        # A prohibited claim reached the wall. Fail CLOSED: nothing partial is
        # served, and the reason never reaches the client.
        cid = uuid.uuid4().hex[:12]
        log.error("d9 publication violation correlation_id=%s", cid, exc_info=True)
        raise HTTPException(status_code=500,
                            detail=f"Internal error. Correlation id {cid}.")
    except HTTPException:
        raise
    except Exception:
        cid = uuid.uuid4().hex[:12]
        log.exception("d9 prepare failed correlation_id=%s", cid)
        raise HTTPException(status_code=500,
                            detail=f"Internal error. Correlation id {cid}.")


@router.post("/d9/prepare", response_model=D9PrepareResponse)
async def d9_prepare(
        req: D9PrepareRequest,
        resolver: ChartResolver = Depends(get_chart_resolver)) -> Dict[str, Any]:
    _require_doctrine()
    snapshot = await resolve_token(resolver, req.chart_token)
    prepared = prepare_or_raise(snapshot, req.chart_token)
    # PUBLIC RESPONSE. `engine` is not returned. The frontend renders `report`
    # and can never reconstruct interpretation from internals.
    return {
        "chart_token": req.chart_token,
        "module_version": MODULE_VERSION,
        "report": prepared["report"],
    }


# ─── the narrative route ─────────────────────────────────────────────────────

def _call_provider(system_prompt: str, user_prompt: str) -> str:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise RuntimeError("provider key not configured")
    response = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={"x-api-key": api_key,
                 "anthropic-version": "2023-06-01",
                 "content-type": "application/json"},
        json={"model": PROVIDER_MODEL, "max_tokens": PROVIDER_MAX_TOKENS,
              "system": system_prompt,
              "messages": [{"role": "user", "content": user_prompt}]},
        timeout=PROVIDER_TIMEOUT,
    )
    if response.status_code != 200:
        # The provider body NEVER travels. WC-001: error text reaching the DOM is
        # a publication surface, so nothing derived from the response escapes
        # this function.
        raise RuntimeError("provider call failed")
    data = response.json()
    return "".join(b.get("text", "") for b in data.get("content", [])
                   if b.get("type") == "text")


def build_narrative_or_neutral(report: Dict[str, Any],
                               name: Optional[str],
                               provider: Callable[[str, str], str]
                               ) -> Dict[str, Any]:
    """Narrative failure preserves certified facts. Only the prose goes neutral.

    Every failure class lands in the same place — a null narrative and a status
    string — because the reader's experience of "the provider returned invalid
    JSON" and "the provider named a deity we did not select" is identical and
    neither is their business.
    """
    # CORR-03 · the provider receives an ATOM POOL and returns a composition
    # plan. It is never handed a blank page.
    pool = build_atom_pool(report)
    # CORR-04 · eligibility is DOMAIN SPREAD, not atom count. A pool that cannot
    # span three substantive domains cannot produce an integrative synthesis, so
    # the closing is withheld rather than faked. The structured report is
    # unaffected and remains fully visible.
    if (len(pool["atoms"]) < MIN_ATOMS
            or len(pool["substantive_domains"]) < MIN_SUBSTANTIVE_DOMAINS):
        return {"narrative": None, "narrative_status": "insufficient_material"}
    try:
        raw = provider(build_provider_instruction(pool),
                       build_provider_user_prompt(pool, name))
    except Exception:
        cid = uuid.uuid4().hex[:12]
        log.warning("d9 provider call failed correlation_id=%s", cid, exc_info=True)
        return {"narrative": None, "narrative_status": "unavailable"}

    try:
        sections = build_narrative(raw, pool)
    except (NarrativeContractError, PublicationViolation):
        cid = uuid.uuid4().hex[:12]
        log.warning("d9 narrative rejected correlation_id=%s", cid, exc_info=True)
        return {"narrative": None, "narrative_status": "unavailable"}

    return {"narrative": sections, "narrative_status": "ok"}


@router.post("/d9report", response_model=D9ReportResponse)
async def d9_report(
        req: D9ReportRequest,
        resolver: ChartResolver = Depends(get_chart_resolver)) -> Dict[str, Any]:
    """Token in, server-rebuilt reading out, one bounded narrative section.

    The request carries NO astrology. `D9ReportRequest` forbids extra fields, so
    a legacy client sending `chart_brief` receives a 422 naming the field rather
    than having its browser-computed astrology honoured.
    """
    _require_doctrine()
    snapshot = await resolve_token(resolver, req.chart_token)
    prepared = prepare_or_raise(snapshot, req.chart_token)
    report = prepared["report"]

    narrative = build_narrative_or_neutral(report, req.name, _call_provider)

    return {
        "chart_token": req.chart_token,
        "module_version": MODULE_VERSION,
        "report": report,
        "narrative": narrative["narrative"],
        "narrative_status": narrative["narrative_status"],
    }
