"""d12_routes.py — /d12/prepare and the shared D12 orchestration.

D12-006A. The accepted D10 route pattern, reused wholesale: the SAME
`d1_routes.get_chart_resolver` dependency, one snapshot store, one caller
identity, one token system. No second resolver, no D12 cache, no session
mechanism of its own, and NO HTTP CALL from one Phalit endpoint to another —
`/d12report` imports `orchestrate` from here and runs it in process.

The pipeline runs each layer exactly once, in order, so no published field can
disagree with another derived from the same input.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, Mapping, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Extra, StrictStr

from d1_routes import ChartNotFound, ChartResolver, get_chart_resolver
from d1_chart_adapter import ChartAdapterError, to_certified_chart
from d1_contract import Varga
from d1_engine import compute_d1

from d12_engine import D12Doctrine, D12DomainError, build_d12_facts
from d12_findings import D12FindingsError, UpstreamPredicates, build_d12_findings
from d12_crosschart import (D12CrossChartError, build_crosschart,
                            build_release_topology, classify_target)
from d12_crosschart_contract import Classification
from d12_selectors import D12SelectorError, build_instructions, build_tension
from d12_publication import (D12PublicationError, PublicationBlocked,
                             build_publication_atoms)

logger = logging.getLogger(__name__)
router = APIRouter()

_DOCTRINE: Optional[D12Doctrine] = None


def configure_d12_routes(doctrine: D12Doctrine) -> None:
    """Injected at wiring, exactly as the D10 router is."""
    global _DOCTRINE
    _DOCTRINE = doctrine.validate()


def _require_doctrine() -> D12Doctrine:
    if _DOCTRINE is None:
        raise HTTPException(status_code=503,
                            detail="D12 doctrine is not configured.")
    return _DOCTRINE


class D12PrepareRequest(BaseModel):
    """chart_token only. No birth data, no browser facts, no parent flags, no
    chart_brief, no Maraka arrays, no provider-authored astrology."""
    chart_token: StrictStr

    class Config:
        extra = Extra.forbid
        min_anystr_length = 8


def _read_snapshot(payload: Any) -> Tuple[Mapping[str, Any], Mapping[str, Any],
                                          Mapping[str, Any]]:
    if not isinstance(payload, dict):
        raise D12DomainError("snapshot is not an object")
    lagna, planets = payload.get("lagna"), payload.get("planets")
    meta = payload.get("calculation_meta")
    if not isinstance(lagna, dict) or not isinstance(planets, dict):
        raise D12DomainError("snapshot lacks lagna or planets")
    if not isinstance(meta, dict):
        raise D12DomainError("snapshot lacks calculation_meta")
    return lagna, planets, meta


def _house_row(facts, house: int):
    for row in facts["houses"]:
        if row["house"] == house:
            return row
    raise D12DomainError(f"house row {house} absent")


def orchestrate(chart_token: str, payload: Any,
                doctrine: D12Doctrine) -> Dict[str, Any]:
    """THE ONE D12 SERVER PIPELINE. Shared by /d12/prepare and /d12report.

        certified provenance gate (1.4.0)
        -> D12 facts, built ONCE from the certified d12_sign_index and
           d12_degree_in_sign
        -> accepted D1 computation IN PROCESS for the H4/H9/H12 lord identities
           and the upstream relation evidence
        -> §§5-9 -> §10 -> FR-004 -> §11 -> §12
        -> typed publication atoms

    No provider call happens here.
    """
    # The provenance gate runs BEFORE any D12 fact is derived.
    chart = to_certified_chart(payload, chart_token, varga=Varga.D1)
    lagna, planets, meta = _read_snapshot(payload)
    facts = build_d12_facts(lagna, planets, doctrine)

    # The accepted D1 engine, in process. Never over HTTP.
    d1_response, d1_doctrine = compute_d1(chart)
    lords = {h.house: (h.lord.value if hasattr(h.lord, "value") else h.lord)
             for h in d1_response.houses}
    evidence = d1_doctrine.relation_evidence

    natures = {n.graha.value if hasattr(n.graha, "value") else str(n.graha):
               ("benefic" if n.natural_nature.value.endswith("benefic")
                else "malefic")
               for n in d1_doctrine.natures}

    # CORR-01 · FR-001 AUTHORITY INTO §6. The D12 H9 and H4 lords are classified
    # by the accepted D12-005 classifier against these same facts and the same
    # upstream relation evidence, and only a DEFINITIVE class is passed on.
    #
    # UNKNOWN is deliberately not translated: it means the classifier could not
    # decide, and turning that into a token would let a §6 bespoke cell fire on
    # an unresolved premise. Absent is the honest state, and the selector
    # already treats absent as unproven.
    structural = {}
    for house, key in ((9, "H9_lord"), (4, "H4_lord")):
        row = _house_row(facts, house)
        lord = row["lord"]
        if lord in facts["placements"]:
            klass = classify_target(lord, 4 if house == 4 else 9,
                                    facts["placements"], facts["houses"],
                                    evidence).classification
            if klass in (Classification.SUPPORTED, Classification.LOADED,
                         Classification.REDIRECTED):
                structural[key] = klass.value

    predicates = UpstreamPredicates(natural_nature=natures,
                                    structural_class=structural)

    findings = build_d12_findings(facts, {"H9": lords.get(9), "H4": lords.get(4)},
                                  predicates)
    crosschart = build_crosschart(facts, lords, chart.chart_token, chart_token,
                                  evidence)
    topology = build_release_topology(facts)
    tension = build_tension(facts, topology, findings.section9.primary_counts,
                            findings.section9.hidden_counts, lords)
    instructions = build_instructions(tension)
    atoms = build_publication_atoms(facts, findings, crosschart, topology,
                                    tension, payload)
    return {"facts": facts, "findings": findings, "crosschart": crosschart,
            "topology": topology, "tension": tension,
            "instructions": instructions, "atoms": atoms,
            "calculation_meta": meta, "chart_token": chart_token,
            "section10_rows": atoms["section10"].rows}


def _correlated(exc_label: str, status: int, message: str) -> HTTPException:
    correlation_id = uuid.uuid4().hex[:12]
    logger.exception("%s [%s]", exc_label, correlation_id)
    return HTTPException(status_code=status,
                         detail=f"{message} Reference: {correlation_id}")


async def resolve_snapshot(resolver: ChartResolver, chart_token: str) -> Any:
    """Unknown, expired, revoked and cross-owner all look identical: 404."""
    try:
        return await resolver.resolve(chart_token)
    except ChartNotFound:
        raise HTTPException(status_code=404,
                            detail="Unknown or expired chart_token.")
    except HTTPException as exc:
        if exc.status_code in (401, 403):
            raise
        raise _correlated("d12 chart resolver upstream failure", 500,
                          "Chart lookup failed.")
    except Exception:
        raise _correlated("d12 chart resolver failed", 500, "Chart lookup failed.")


def run_pipeline(chart_token: str, payload: Any,
                 doctrine: D12Doctrine) -> Dict[str, Any]:
    """orchestrate() with every internal failure correlated at the boundary.

    PublicationBlocked is separated from the malformed-input family: it is a
    correct engine result the frozen page cannot print, and conflating the two
    would tell the caller a good chart was corrupt.
    """
    try:
        return orchestrate(chart_token, payload, doctrine)
    except PublicationBlocked:
        raise _correlated("d12 publication blocked by a deterministic state", 422,
                          "This chart cannot produce a complete D12 report.")
    except (ChartAdapterError, D12DomainError, D12FindingsError,
            D12CrossChartError, D12SelectorError, D12PublicationError,
            KeyError, TypeError, ValueError):
        # A correlation id, never the reason: the adapter names the mismatched
        # certificate value and the domain errors name the graha and the
        # out-of-domain number. Neither is the caller's business.
        raise _correlated("d12 snapshot failed certification", 422,
                          "Chart snapshot could not be prepared.")


class D12PrepareResponse(BaseModel):
    """The deterministic layer, before any prose. §11 and §13 are absent by
    design: they are composed by the bounded synthesiser at report time."""
    chart_token: StrictStr
    calculation_meta: Dict[str, str]
    sections: Dict[str, Any]
    tension_key: Optional[str]
    tension_unresolved_at: Optional[str]
    release_dominance: str

    class Config:
        extra = Extra.forbid


@router.post("/d12/prepare", response_model=D12PrepareResponse)
async def d12_prepare(req: D12PrepareRequest,
                      resolver: ChartResolver = Depends(get_chart_resolver)):
    doctrine = _require_doctrine()
    payload = await resolve_snapshot(resolver, req.chart_token)
    result = run_pipeline(req.chart_token, payload, doctrine)
    atoms = result["atoms"]
    return D12PrepareResponse(
        chart_token=req.chart_token,
        calculation_meta={k: str(v) for k, v in result["calculation_meta"].items()},
        sections={k: v.dict() for k, v in atoms.items()},
        tension_key=result["tension"].winner,
        tension_unresolved_at=result["tension"].unresolved_at,
        release_dominance=result["topology"].dominance.value)
