"""
d4_routes.py — POST /d4/prepare.

Built to the ACCEPTED Pratiphala boundary in pratiphala_routes.py
(86cee4a5965d776e), reusing its resolution contract rather than restating it:

    from d1_routes import ChartNotFound, ChartResolver, get_chart_resolver

ONE RESOLVER, ONE DOOR. This module declares no snapshot store, no session
path, no caller dependency, no authentication and no `dependency_overrides`
call. It depends on the SAME `d1_routes.get_chart_resolver` function object that
`install_d1()` already overrode, so /d4/prepare inherits the caller-scoped
resolver automatically. A second binding here would be a second door onto one
snapshot store, which is exactly what the reference warns against.

NO ASTRONOMY IS RECALCULATED. The route resolves the certified snapshot and
reads the D1 `sign_index` and in-sign `degree` that /chart already certified.
It accepts no birth data: `D4PrepareRequest` carries a chart_token and forbids
every other field.

CERTIFIED PROVENANCE (CORR-01). A resolved snapshot is put through the accepted
D1 adapter's certificate gate BEFORE any D4 fact is computed. D4 keeps no copy
of the certificate and never publishes the rejection: the mismatched value, the
backend name and the raw exception all stay in the log, and the caller gets the
same neutral correlated 422 as any other malformed snapshot.

ONE DELIBERATE DEVIATION FROM THE REFERENCE, FLAGGED FOR QA.
  pratiphala_routes returns `detail=str(e)` on its 422. D4-002-R1 requires a
  neutral correlated 422 and states that no raw exception text may reach
  `detail`, so this route logs the exception and publishes a correlation id
  only. That is a deviation from the accepted reference and it is intentional;
  the reference's own 422 is recorded in the delivery note as a same-class
  finding, not fixed here.
"""
from __future__ import annotations

import logging
import os
import uuid

import requests
from typing import Any, Dict, Tuple

from fastapi import APIRouter, Depends, HTTPException

# REUSED, NOT REDEFINED. One resolver abstraction and one dependency provider
# serve every prepare route.
from d1_routes import ChartNotFound, ChartResolver, get_chart_resolver
# CORR-01 · REUSED, NOT RETYPED. The certified-provenance gate is the accepted
# D1 adapter's. D4 holds NO copy of the certificate: the engine version, the
# ayanamsha model, the house system, the node type and the ephemeris backend
# appear nowhere in this file, so a future change to the certificate cannot
# leave a stale second copy here disagreeing with the first. The interface used
# is exactly the one the accepted pratiphala_routes.py depends on.
from d1_contract import Varga
from d1_chart_adapter import ChartAdapterError, to_certified_chart

from d4_contract import (D4PrepareRequest, D4PrepareResponse, D4ReportRequest,
                          D4ReportResponse, build_response)
from d4_core import ALL_GRAHAS, D4DomainError, D4Doctrine, build_d4_facts
from d4_property_state import D4PropertyStateError, classify_property_state
from d4_vahana import D4VahanaError, build_vahana_evidence
from d4_dasha import D4DashaError, build_dasha_context
from d4_semantic import (D4SemanticError, build_architectural_signatures,
                         build_comfort_profile, build_semantic_envelope)
from d4_narrative import (D4NarrativeError, D4_NARRATIVE_VERSION, SYSTEM_PROMPT,
                          build_narrative_brief, build_user_prompt, validate_provider_output)

router = APIRouter()
logger = logging.getLogger(__name__)

# The accepted doctrine is INJECTED at wiring time, using the same
# configure_*() idiom d1_wiring uses for the session secret and the optional
# user dependency. This keeps d4_core's "no doctrine table of its own"
# guarantee intact and avoids importing main.py from a route module.
_doctrine: "D4Doctrine | None" = None


def configure_d4_doctrine(doctrine: D4Doctrine) -> None:
    global _doctrine
    _doctrine = doctrine


def _require_doctrine() -> D4Doctrine:
    """FAIL CLOSED, like d1_wiring._secret(). An unconfigured deployment must
    not silently serve a D4 layer computed from nothing."""
    if _doctrine is None:
        raise HTTPException(status_code=503,
                            detail="D4 preparation is unavailable.")
    return _doctrine


class D4SnapshotError(ValueError):
    """The resolved snapshot is not shaped like a certified chart, or carries a
    value the certified engine could not have produced. Internal only: the
    message never reaches a response."""


def _read_certified_facts(payload: Any) -> Tuple[Dict[str, Any], Dict[str, Dict[str, Any]],
                                                 Dict[str, Any], Dict[str, Any]]:
    """Read ONLY what D4 needs from the certified snapshot: the Lagna and the
    nine grahas' D1 sign index and in-sign degree, calculation_meta, and — new
    in D4-003 — the minimum D1 ROOT FACTS Lock 4 requires.

    D4-003 EXTENSION, NAMED RATHER THAN SLIPPED IN: Lock 4 needs the D1 4th
    Lord's dignity, and the ticket forbids recomputing it. The certified
    snapshot already publishes `planets[G].dignity` from the accepted
    `get_dignity`, in which Moolatrikona IS active. That published value is read
    here and passed through unchanged. Nothing recomputes D1 dignity, and no
    additional astronomy is touched.

    The in-sign `degree` the snapshot carries is the CERTIFIED value, rounded to
    four decimals by the chart engine. D4 quarters are read from that same
    certified value rather than re-deriving one from `longitude`, so the D4
    layer and the chart the user was shown cannot disagree about which quarter a
    graha occupies.
    """
    if not isinstance(payload, dict):
        raise D4SnapshotError("snapshot is not an object")
    lagna = payload.get("lagna")
    planets = payload.get("planets")
    if not isinstance(lagna, dict) or not isinstance(planets, dict):
        raise D4SnapshotError("snapshot lacks lagna or planets")

    def pick(rec: Any, what: str) -> Dict[str, Any]:
        if not isinstance(rec, dict):
            raise D4SnapshotError(f"{what} record is not an object")
        if "sign_index" not in rec or "degree" not in rec:
            raise D4SnapshotError(f"{what} record lacks sign_index or degree")
        return {"sign_index": rec["sign_index"], "degree": rec["degree"]}

    d4_lagna = pick(lagna, "lagna")
    d4_planets = {}
    for g in ALL_GRAHAS:
        if g not in planets:
            raise D4SnapshotError("snapshot is missing a graha")
        d4_planets[g] = pick(planets[g], g)

    # D1 root facts for Lock 4. Read from the SAME certified records above.
    d1_dignity = {}
    for g in ALL_GRAHAS:
        rec = planets[g]
        if "dignity" not in rec or not isinstance(rec["dignity"], str) or not rec["dignity"]:
            raise D4SnapshotError("snapshot lacks a certified D1 dignity for a graha")
        d1_dignity[g] = rec["dignity"]
    if "sign_index" not in lagna:
        raise D4SnapshotError("snapshot lagna lacks sign_index")
    # D4-007 EXTENSION, NAMED NOT SLIPPED IN: the certified snapshot's own
    # `dasha` block is carried through unchanged so the Dasha module can read
    # the CURRENT MD/AD identities. Vimshottari is never recomputed and no birth
    # data is touched. A snapshot without usable Dasha facts is not an error —
    # it resolves to `unknown`, never to a negative.
    d1_root = {"lagna_sign_index": lagna["sign_index"], "dignity_by_graha": d1_dignity,
               "dasha": payload.get("dasha")}

    meta = payload.get("calculation_meta")
    if not isinstance(meta, dict):
        raise D4SnapshotError("snapshot lacks calculation_meta")
    # NOTE: this is a SHAPE check only. The certificate itself is enforced by
    # the accepted D1 adapter in _assert_certified_provenance below, never here.
    return d4_lagna, d4_planets, meta, d1_root


def _assert_certified_provenance(payload: Any, chart_token: str) -> None:
    """CORR-01 · The accepted certified-provenance gate, reused wholesale.

    `to_certified_chart` is the accepted entry point into d1_chart_adapter and
    is what the accepted pratiphala_routes.py relies on; it raises
    ChartAdapterError for a snapshot that does not satisfy the certificate.
    D4 calls it PURELY AS A GATE and discards the result, because D4 needs only
    the D1 sign_index and in-sign degree that _read_certified_facts already
    reads from the certified snapshot.

    The raised ChartAdapterError carries the mismatched value and may name the
    backend, so it is caught at the route boundary and never published.
    """
    to_certified_chart(payload, chart_token, varga=Varga.D1)


async def _prepare_d4(chart_token: str, resolver: ChartResolver,
                      doctrine: D4Doctrine) -> D4PrepareResponse:
    try:
        chart_payload = await resolver.resolve(chart_token)
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
        logger.exception("d4 chart resolver upstream failure [%s]", correlation_id)
        raise HTTPException(status_code=500,
                            detail=f"Chart lookup failed. Reference: {correlation_id}")
    except Exception:
        correlation_id = uuid.uuid4().hex[:12]
        logger.exception("d4 chart resolver failed [%s]", correlation_id)
        raise HTTPException(status_code=500,
                            detail=f"Chart lookup failed. Reference: {correlation_id}")

    return await _resolve_and_prepare(chart_token, chart_payload, doctrine)


async def _resolve_and_prepare(chart_token: str, chart_payload: Any,
                               doctrine: D4Doctrine) -> D4PrepareResponse:
    """The ONE accepted D4 preparation pipeline.

    Extracted rather than duplicated: two copies of gate -> read -> facts ->
    state -> vahana -> dasha would be two engines that agree today, and the
    narrative would be free to drift from the cards it sits beside. The report
    route consumes THIS result, so the prose can only ever explain the surface
    the reader is looking at.
    """
    try:
        # ORDER IS LOAD-BEARING: the provenance gate runs BEFORE any D4 fact is
        # computed, so a snapshot that fails certification never reaches
        # build_d4_facts and no D4 layer is ever derived from an uncertified
        # chart. Asserted by a call-spy in the route suite.
        _assert_certified_provenance(chart_payload, chart_token)
        lagna, planets, meta, d1_root = _read_certified_facts(chart_payload)
        facts = build_d4_facts(lagna, planets, doctrine)
        # D4-003 · deterministic classification, server-authoritative. The
        # provider has no classification authority: this runs before any
        # response exists and consumes only certified mechanical facts.
        property_state = classify_property_state(facts, d1_root, doctrine)
        # D4-005 · Vāhana evidence, selected from the SAME certified facts. No
        # second astrology pass and no D16 consultation.
        vahana_evidence = build_vahana_evidence(facts, doctrine)
        # D4-007 · timing CONTEXT derived from the structural evidence just
        # resolved. It re-evaluates no predicate and classifies nothing.
        dasha_context = build_dasha_context(property_state, d1_root.get("dasha"))
        # COURSE CORRECTION · presentation layers, derived from the already
        # decided result. None of these re-evaluates a predicate.
        semantic_envelope = build_semantic_envelope(property_state, vahana_evidence)
        comfort_profile = build_comfort_profile(vahana_evidence, property_state)
        architectural_signatures = build_architectural_signatures(facts, property_state)
        # The RESOLVED token is echoed, so a caller can confirm which chart
        # answered.
        return build_response(facts=facts, chart_token=chart_token,
                              calculation_meta=meta, property_state=property_state,
                              vahana_evidence=vahana_evidence,
                              dasha_context=dasha_context,
                              semantic_envelope=semantic_envelope,
                              comfort_profile=comfort_profile,
                              architectural_signatures=architectural_signatures)
    except (ChartAdapterError, D4SnapshotError, D4DomainError,
            D4PropertyStateError, D4VahanaError, D4DashaError, D4SemanticError,
            KeyError, TypeError, ValueError):
        correlation_id = uuid.uuid4().hex[:12]
        logger.exception("d4 snapshot failed certification [%s]", correlation_id)
        raise HTTPException(
            status_code=422,
            detail=f"Chart snapshot could not be prepared. Reference: {correlation_id}")


#: D4-PROD-05 · appended to the SECOND attempt only. It restates the contract
#: the first draft broke, WITHOUT naming which rule failed and WITHOUT quoting
#: the rejected prose — the customer never sees the violation reason, and the
#: model is asked to rewrite rather than patch.
REGENERATION_INSTRUCTION = """YOUR PREVIOUS DRAFT VIOLATED THE OUTPUT CONTRACT AND WAS DISCARDED.

Write the complete reading again from scratch. Do not attempt to recall, repeat
or repair the previous draft. Obey every rule above, and in particular:

- emit EXACTLY the four required headings, once each, in order, each beginning
  with three hash marks and one space, with no preamble and no closing note;
- attach NO number to properties, homes, houses, plots, real estate or holdings,
  in digits or in words — describe the pattern without counting it;
- give NO purchase date, year, window, season or timeframe;
- use NO guarantee, assurance, certainty or inevitability vocabulary, in either
  direction;
- use NO activation, trigger, fruition or imminence language, in either
  direction;
- make NO claim about the mother's health, longevity or survival;
- introduce NO Moksha or spiritual-versus-material material;
- use NO internal state code such as P1 through P5;
- state ONLY the comfort tier supplied above, and never invent, rename or
  re-rank one."""


def _provider_narrative(system_prompt: str, user_prompt: str) -> str:
    """The ONLY provider call in the D4 stack.

    Nothing derived from the response reaches a caller: a non-200, a malformed
    body or a transport failure all raise, and the route publishes a neutral
    correlated error. This is the WC-001/WC-002 contract applied on the backend
    from the start, rather than retro-fitted after a leak.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise D4NarrativeError("narrative provider is not configured")
    response = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={"x-api-key": api_key, "anthropic-version": "2023-06-01",
                 "content-type": "application/json"},
        json={"model": "claude-sonnet-4-6", "max_tokens": 2000,
              "system": system_prompt,
              "messages": [{"role": "user", "content": user_prompt}]},
        timeout=60)
    if response.status_code != 200:
        # The status and body are deliberately NOT carried: they are logged by
        # the caller's correlated handler and never published.
        raise D4NarrativeError("narrative provider returned a non-success status")
    data = response.json()
    return "".join(b.get("text", "") for b in data.get("content", [])
                   if b.get("type") == "text")


@router.post("/d4report", response_model=D4ReportResponse)
async def d4_report(req: D4ReportRequest,
                    resolver: ChartResolver = Depends(get_chart_resolver)):
    """D4-008 · the interpretive explanation.

    The request surface is a chart_token and nothing else. No chart_brief, no
    browser-computed facts, no client-selected state and no birth data: the
    server rebuilds the accepted deterministic hierarchy from the certified
    snapshot and the provider explains THAT.
    """
    doctrine = _require_doctrine()
    try:
        chart_payload = await resolver.resolve(req.chart_token)
    except ChartNotFound:
        raise HTTPException(status_code=404, detail="Unknown or expired chart_token.")
    except HTTPException as exc:
        if exc.status_code in (401, 403):
            raise
        correlation_id = uuid.uuid4().hex[:12]
        logger.exception("d4 report resolver upstream failure [%s]", correlation_id)
        raise HTTPException(status_code=500,
                            detail=f"Chart lookup failed. Reference: {correlation_id}")
    except Exception:
        correlation_id = uuid.uuid4().hex[:12]
        logger.exception("d4 report resolver failed [%s]", correlation_id)
        raise HTTPException(status_code=500,
                            detail=f"Chart lookup failed. Reference: {correlation_id}")

    prepared = await _resolve_and_prepare(req.chart_token, chart_payload, doctrine)

    regeneration_attempted = False
    try:
        brief = build_narrative_brief(prepared.property_state.dict(),
                                      prepared.vahana_evidence.dict(),
                                      prepared.dasha_context.dict(),
                                      prepared.semantic_envelope.dict(),
                                      prepared.comfort_profile.dict(),
                                      prepared.architectural_signatures.dict())
        # The prompt is built ONCE from the deterministic brief and reused for
        # both attempts, so a regeneration cannot change what the provider is
        # explaining — only how carefully it obeys the contract.
        user_prompt = build_user_prompt(brief)
        text = _provider_narrative(SYSTEM_PROMPT, user_prompt)
        # D4-008-CORR-01 · FAIL CLOSED. A violating narrative is rejected whole
        # and falls into the sanitized 502 below; nothing is scrubbed or
        # partially published, and the deterministic evidence already on the
        # page is unaffected.
        #
        # D4-PROD-05 · ONE-SHOT REGENERATION. The live failure was a provider
        # that produced a literal asset count. The guard was RIGHT to reject it,
        # so the guard does not move; the route simply gives the provider one
        # more attempt against the SAME brief. The rejected draft is DISCARDED
        # ENTIRELY and never sent back — regenerating from scratch is the point,
        # and echoing the bad prose would invite the model to edit rather than
        # rewrite, and would put a violating count back on the wire.
        #
        # The retry is scoped to exactly one cause: a response was obtained and
        # FAILED VALIDATION. `_provider_narrative` sits OUTSIDE this try, so a
        # missing key, a non-success status or a transport failure still fails
        # closed on the first attempt with no second call.
        try:
            sections = validate_provider_output(text, brief)
        except D4NarrativeError:
            regeneration_attempted = True
            text = _provider_narrative(SYSTEM_PROMPT,
                                       user_prompt + "\n\n" + REGENERATION_INSTRUCTION)
            sections = validate_provider_output(text, brief)
    except HTTPException:
        raise
    except Exception:
        correlation_id = uuid.uuid4().hex[:12]
        logger.exception("d4 narrative generation failed [%s] (regeneration_attempted=%s)",
                         correlation_id, regeneration_attempted)
        raise HTTPException(
            status_code=502,
            detail=f"Interpretive explanation unavailable. Reference: {correlation_id}")

    return D4ReportResponse(chart_token=req.chart_token,
                            narrative_version=D4_NARRATIVE_VERSION,
                            sections=sections)


@router.post("/d4/prepare", response_model=D4PrepareResponse)
async def d4_prepare(req: D4PrepareRequest,
                     resolver: ChartResolver = Depends(get_chart_resolver)):
    return await _prepare_d4(req.chart_token, resolver, _require_doctrine())
