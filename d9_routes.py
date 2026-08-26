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
from d9_client_reading import PublicationViolation, publish_dignity

import d9_r2_contribution as r2_con
import d9_r2_partnership as r2_partner
import d9_r2_doctrine as r2_doc
import d9_r2_narrative as r2_nar
import d9_r2_publication as r2_pub
import d9_r2_selectors as r2_sel
from d9_contract import (
    D9PrepareRequest,
    D9PrepareResponse,
    D9ReportRequest,
    D9ReportResponse,
)
from d9_engine import (D9Doctrine, D9InputError, build_d9_facts,
                        configure_engine_doctrine, karakamsha_house_occupants)
# `d9_narrative` (R1) is deliberately NOT imported. R2 owns the Final Synthesis
# through `d9_r2_narrative`, and leaving the R1 import in place would keep a
# second narrative authority one call site away from the route.

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
# The injected doctrine, retained so R2 can read signs and lords without a
# second source. `_require_doctrine()` returns None — it is a gate, not a getter,
# and reconfiguring the engine with its return value silently wiped the doctrine.
_DOCTRINE: Optional[D9Doctrine] = None


def configure_d9_doctrine(engine_doctrine: D9Doctrine,
                          pratiphala_provider: Optional[Callable] = None) -> None:
    """Inject doctrine. Called from main.py BELOW the tables it reads."""
    global _CONFIGURED, _PRATIPHALA_PROVIDER, _DOCTRINE
    d9_engine.configure_engine_doctrine(engine_doctrine)
    _DOCTRINE = engine_doctrine
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


# ═════════════════════════════════════════════════════════════════════════════
# R2 · the live wiring
# ═════════════════════════════════════════════════════════════════════════════
#
# ONE REPORT AUTHORITY. The R1 publication model is not returned alongside R2
# "for compatibility" — two authorities on one surface is how the old report
# survived its own replacement.

R2_ROUTE_VERSION = "d9-r2-003"


def _karakamsha_domain_facts(facts: Dict[str, Any],
                             planets: Dict[str, Any]) -> Dict[int, Dict[str, Any]]:
    """H5 / H9 / H10 in the accepted `KARAKAMSHA_Hx_D1_FRAME`.

    NO CHANGE TO `karak_house_data.py` WAS NEEDED. Its `HOUSE_DATA` covers
    houses 5, 7, 8 and 10 because those are the houses with accepted RULES —
    but R2's Contribution needs OCCUPANCY, not rules, and
    `d9_engine.karakamsha_house_occupants` is already generic over any house.
    So H9 comes from the shared mechanical authority unchanged, and no parallel
    Karakāṁśa implementation exists.
    """
    _require_doctrine()
    doc_ = _DOCTRINE
    kl = facts.get("karakamsha") or {}
    if kl.get("status") != "RESOLVED":
        return {}
    kl_index = kl["sign_index"]
    out: Dict[int, Dict[str, Any]] = {}
    for house in (5, 9, 10):
        sign_index = (kl_index + house - 1) % 12
        out[house] = {
            "occupants": karakamsha_house_occupants(house, kl_index, planets),
            "sign": doc_.signs[sign_index],
            "lord": doc_.sign_lords[sign_index],
        }
    return out


# NO CONFIDENCE NORMALIZATION EXISTS HERE, DELIBERATELY.
#
# Flight 15 added `_normalise_h7_confidence()` to recover KL_H7_JUP / KL_H7_BEN.
# It was unnecessary — `karak_house_data.eval_house()` already defaults a fired
# rule's confidence to "direct" — and it was unsafe: its accepted-ID set was
# drawn from EVERY house, so a record carrying a non-H7 id such as KL_H5_BEN
# could be upgraded through the H7 path and acquire partnership publication
# authority it never had.
#
# Removing a false claim downstream is not removing it. The mechanism is gone,
# not narrowed, and an adversarial regression proves a non-H7 id cannot reach
# H7 authority.
def build_r2_report(facts: Dict[str, Any], snapshot: Dict[str, Any],
                    chart_token: str) -> Dict[str, Any]:
    """Certified facts -> R2 selectors -> R2 publication model."""
    planets = snapshot.get("planets") or {}
    d1_lagna = (snapshot.get("lagna") or {}).get("sign")
    d9_lagna = (facts.get("d9_lagna") or {}).get("sign")
    if not d1_lagna or not d9_lagna:
        raise D9InputError("chart lacks a resolved D1 or D9 lagna")

    published = {g: p["published_dignity"]
                 for g, p in _published_dignities(facts).items()}
    d1_sign_of = {g: rec.get("sign") for g, rec in planets.items() if rec.get("sign")}
    d9_sign_of = {g: p.get("d9_sign") for g, p in (facts.get("placements") or {}).items()
                  if p.get("d9_sign")}

    strength = r2_sel.select_strength(published, d1_sign_of, d9_sign_of, d9_lagna)
    theme = r2_sel.select_central_theme(d1_lagna, d9_lagna)
    growth = r2_sel.select_growth_edge(d9_lagna)
    instructions = r2_sel.select_instructions(d9_lagna)

    # PARTNERSHIP DYNAMICS · universal. Tiers 1 and 2 always resolve or the
    # preparation fails closed; Karakāṁśa H7 is an optional modifier and no
    # longer the gate that decides whether Section 3 exists.
    kl7 = (facts.get("karakamsha_houses") or {}).get(7) or {}
    kl7_occupants = list(kl7.get("occupants") or [])
    partnership = r2_partner.build_partnership(
        d9_lagna_sign_index=(facts.get("d9_lagna") or {}).get("sign_index"),
        published_dignity=published,
        karakamsha_h7_occupants=kl7_occupants,
        karakamsha_h7_sign=kl7.get("sign"))

    domains = _karakamsha_domain_facts(facts, planets)
    contribution = None
    if domains:
        grid = r2_con.ContributionGrid(r2_doc.GRAHA_ARCHETYPES, r2_doc.SIGN_ARCHETYPES)
        signals = []
        for house in (5, 9, 10):
            d = domains[house]
            signals.append(r2_con.resolve_domain(
                house, d["occupants"], d["lord"], d["sign"], grid)["signal"])
        contribution = r2_sel.select_contribution(
            r2_con.converge(*signals), d9_lagna)

    # THE SAFE BUILDER PATH. No arbitrary dictionary is injected into the
    # technical appendix — it is constructed and validated, and it raises rather
    # than publishing telemetry.
    basis = r2_pub.build_astrological_basis(
        d1_lagna=d1_lagna, d9_lagna=d9_lagna,
        d9_lagna_lord=(facts.get("d9_lagna") or {}).get("lord"),
        atmakaraka=((facts.get("atmakaraka") or {}).get("graha")
                    if (facts.get("atmakaraka") or {}).get("status") == "RESOLVED"
                    else None),
        swamsa=(facts.get("karakamsha") or {}).get("sign"),
        strength_grahas=strength.get("grahas") or [],
        published_dignity=published,
        vargottama={g: True for g in
                    (facts.get("integration") or {}).get("integrated_grahas") or []},
        karakamsha_evidence={h: list(d["occupants"]) for h, d in domains.items()},
        d9_seventh_sign=partnership["relational_field"]["sign"],
        d9_seventh_lord=partnership["governing_function"]["graha"],
        d9_seventh_lord_dignity=partnership["governing_function"]["dignity"],
        karakamsha_h7_sign=kl7.get("sign"),
        karakamsha_h7_occupants=kl7_occupants,
        growth_edge_source=f"{d9_lagna} Navāṁśa Lagna · shadow_expression",
        contribution_convergence=(contribution or {}).get("convergence"),
        contribution_roles=[r2_pub.CONTRIBUTION_ROLE_TECHNICAL[k]
                            for k in r2_pub.CONTRIBUTION_ROLE_TECHNICAL
                            if (contribution or {}).get(k)] or None,
        instructions_source=f"{d9_lagna} Navāṁśa Lagna maturity pattern",
    )

    # DISPLAY-ONLY D9 chart, built from already-certified placements. The
    # browser receives finished houses/signs/occupants and performs no
    # divisional arithmetic of its own.
    d9_lagna_index = (facts.get("d9_lagna") or {}).get("sign_index")
    d9_chart = r2_pub.build_d9_chart_projection(
        d9_lagna_index, facts.get("placements") or {}, _DOCTRINE.signs)

    reading_basis = r2_pub.build_reading_basis(
        d1_lagna, d9_lagna, strength, contribution, True)
    reading_basis["partnership"] = r2_partner.build_partnership_basis(
        partnership, kl7.get("sign"), kl7_occupants)
    key_anchors = r2_pub.build_key_anchors(
        d1_lagna, d9_lagna, strength, contribution)

    return r2_pub.build_report(
        chart_token=chart_token, central_theme=theme, strength=strength,
        growth_edge=growth, instructions=instructions,
        partnership=partnership, contribution=contribution,
        astrological_basis=basis, d9_chart=d9_chart,
        reading_basis=reading_basis, key_anchors=key_anchors)


def _published_dignities(facts: Dict[str, Any]) -> Dict[str, Dict[str, str]]:
    """Published band per graha. The certified band never leaves the engine."""
    out = {}
    for graha, p in (facts.get("placements") or {}).items():
        if p.get("status") != "RESOLVED":
            continue
        out[graha] = {"published_dignity":
                      publish_dignity(p["certified_dignity"], graha)}
    return out


def resolve_and_prepare(snapshot: Dict[str, Any], chart_token: str) -> Dict[str, Any]:
    """Certified snapshot -> the R2 report. One authority, no R1 model."""
    certified = to_certified_chart(snapshot, chart_token)      # gate, value unused
    _require_doctrine()
    facts = build_d9_facts(snapshot["lagna"], snapshot["planets"])
    return {
        "route_version": R2_ROUTE_VERSION,
        "chart_token": chart_token,
        "report_version": r2_pub.REPORT_VERSION,
        "report": build_r2_report(facts, snapshot, chart_token),
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
        "route_version": prepared["route_version"],
        "report_version": prepared["report_version"],
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


def build_final_synthesis(report: Dict[str, Any],
                          provider: Optional[Callable[[str, str], str]]
                          ) -> Dict[str, Any]:
    """One provider call, then a deterministic canonical plan.

    THE READER ALWAYS GETS A FINAL SYNTHESIS. Timeout, malformed JSON, unknown
    atom, unknown connector, bad cardinality — every failure lands on the same
    server-owned atoms in the server's own editorial order. The old
    "Interpretive explanation unavailable" is not reproduced.

    No diagnostic reaches the response: no provider body, no billing text, no
    correlation id, no exception detail. Those are logged.

    THE PROVIDER RECEIVES NO USER NAME. It selects identifiers and writes no
    prose, so a name changes nothing in the output — Flight 11 sent it anyway,
    which was an unnecessary PII transfer and a drift from the token-only
    contract.
    """
    return r2_nar.build_final_synthesis(
        report.get("synthesis_material") or {}, provider)


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
    # THE SERVER REBUILDS FROM THE CERTIFIED CHART. The browser's report is
    # never narrative authority.
    report = prepared["report"]

    synthesis = build_final_synthesis(report, _call_provider)

    return {
        "chart_token": req.chart_token,
        "route_version": R2_ROUTE_VERSION,
        "final_synthesis": synthesis["final_synthesis"],
        "synthesis_source": synthesis["synthesis_source"],
    }
