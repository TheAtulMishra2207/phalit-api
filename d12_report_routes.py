"""d12_report_routes.py — the replacement POST /d12report.

D12-006A. This route REPLACES the condemned legacy handler, which sent Maraka
arrays and browser-generated astrology to an unconstrained provider. The old
handler is removed from registration in main.py; it is not shadowed, and a route
enumeration test proves exactly one active POST /d12report.

The handler calls the shared `d12_routes.orchestrate` in process. It makes no
HTTP request to /d12/prepare.

FAILURE POLICY, stated once and applied everywhere: no partial customer report.
A provider that is unavailable is a stable service failure; provider output that
is malformed or unsafe is a stable synthesis failure. Neither ever falls back to
the legacy three-section essay — that prose is condemned evidence, not a spare
tyre.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Callable, Optional

from fastapi import APIRouter, Depends, HTTPException
from starlette.concurrency import run_in_threadpool

from d1_routes import ChartResolver, get_chart_resolver

from d12_publication_contract import D12Report, Section11, Section13
from d12_instruction_corpus import TENSION_TITLE
from d12_report_contract import D12ReportRequest, D12ReportResponse
from d12_routes import _require_doctrine, resolve_snapshot, run_pipeline
from d12_synthesis import (Provider, SynthesisRejected, SynthesisUnavailable,
                           build_atoms, compose)
from d12_synthesis_contract import BEATS

logger = logging.getLogger(__name__)
router = APIRouter()

_PROVIDER: Optional[Provider] = None


def configure_d12_report(provider: Provider) -> None:
    """Injected at wiring. Certification runs entirely offline through this."""
    global _PROVIDER
    _PROVIDER = provider


def _require_provider() -> Provider:
    if _PROVIDER is None:
        raise HTTPException(
            status_code=503,
            detail="Report composition is not configured.")
    return _PROVIDER


def build_report(chart_token: str, payload: Any, doctrine,
                 provider: Provider) -> D12Report:
    """The whole customer report, assembled and validated server-side."""
    result = run_pipeline(chart_token, payload, doctrine)
    tension = result["tension"]
    atoms = result["atoms"]

    # §12 already refused the fallback inside build_publication_atoms, so a
    # winner exists by the time we compose. Re-stated here because the next
    # line depends on it and a silent assumption would be worse.
    if tension.winner is None:
        raise HTTPException(
            status_code=422,
            detail="This chart cannot produce a complete D12 report.")

    synth_atoms = build_atoms(result["facts"], result["findings"],
                              result["crosschart"], result["topology"],
                              tension, result["section10_rows"])
    synthesis = compose(provider, synth_atoms, tension.winner)

    section11 = Section11(
        tension_key=tension.winner, title=TENSION_TITLE[tension.winner],
        body=synthesis.section11_body, fallback_applied=False,
        word_count=synthesis.section11_words)
    section13 = Section13(
        essay=synthesis.section13_essay, word_count=synthesis.section13_words,
        beat_order=list(BEATS), practice_sentence=synthesis.practice_sentence)

    return D12Report(
        chart_token=chart_token,
        calculation_meta={k: str(v)
                          for k, v in result["calculation_meta"].items()},
        section0=atoms["section0"], section1=atoms["section1"],
        section2=atoms["section2"], section3=atoms["section3"],
        section4=atoms["section4"], section5=atoms["section5"],
        section6=atoms["section6"], section7=atoms["section7"],
        section8=atoms["section8"], section9=atoms["section9"],
        section10=atoms["section10"], section11=section11,
        section12=atoms["section12"], section13=section13,
        section14=atoms["section14"], section15=atoms["section15"])


@router.post("/d12report", response_model=D12ReportResponse)
async def d12_report(req: D12ReportRequest,
                     resolver: ChartResolver = Depends(get_chart_resolver)):
    doctrine = _require_doctrine()
    provider = _require_provider()
    payload = await resolve_snapshot(resolver, req.chart_token)
    try:
        # D12-007-LIVE-CORR-02 · THE PROVIDER CALL MUST LEAVE THE EVENT LOOP.
        #
        # build_report() ends in a blocking requests.post to the provider with a
        # 60s timeout. Awaited directly here it ran ON the event-loop thread, so
        # with WEB_CONCURRENCY=1 a single slow provider call froze the only loop
        # and every unrelated route with it — /health measured 9,052 ms behind a
        # 5s provider sleep. Token resolution above stays async, because it is
        # genuinely async I/O; only the blocking composition moves.
        report = await run_in_threadpool(
            build_report, req.chart_token, payload, doctrine, provider)
    except HTTPException:
        raise
    except SynthesisUnavailable:
        correlation_id = uuid.uuid4().hex[:12]
        logger.exception("d12 report composition unavailable [%s]", correlation_id)
        raise HTTPException(
            status_code=503,
            detail=f"Report composition is temporarily unavailable. "
                   f"Reference: {correlation_id}")
    except SynthesisRejected:
        correlation_id = uuid.uuid4().hex[:12]
        logger.exception("d12 report composition rejected [%s]", correlation_id)
        raise HTTPException(
            status_code=502,
            detail=f"Report composition did not meet the content contract. "
                   f"Reference: {correlation_id}")
    return D12ReportResponse(report=report)


# ─────────────────────────────────────────────────────────────────────────────
# PRODUCTION PROVIDER
#
# The existing Anthropic transport pattern, reused. NOT the legacy D12 prompt or
# payload: the instruction below forbids astrology and the atoms are the
# certified ones build_atoms assembled. Every certification test injects its own
# provider instead, so nothing here runs offline.
# ─────────────────────────────────────────────────────────────────────────────

_SECTION11_INSTRUCTION = (
    "You are a prose composer, not an astrologer. Compose at most 90 words "
    "about the ONE tension named in the atoms. Do not introduce a second "
    "tension, a diagnosis, illness, death, Maraka, a rite, a mantra, a remedy, "
    "a past-life identity, or any claim that D12 cancels work or standing. "
    "Return JSON only: {\"tension_key\": <the key you were given>, "
    "\"body\": <prose>}.")

_SECTION13_INSTRUCTION = (
    "You are a prose composer, not an astrologer. Write eight beats in exactly "
    "this order: stance, father, mother, unpaid, handshake, ketu_pull, tension, "
    "practice. Together they must read as ONE essay of 220-280 words with no "
    "headings. The final practice beat must contain the supplied practice "
    "sentence verbatim. Do not introduce a diagnosis, illness, death, Maraka, a "
    "rite, a mantra, a remedy, a past-life identity, a second tension, a soul "
    "eulogy, or any claim that D12 cancels work or standing. Do not restate the "
    "Devatā table. Return JSON only: {\"beats\": [{\"name\": ..., \"text\": ...}]}.")


def anthropic_prose_provider(task: str, atoms, *, transport=None) -> dict:
    """Bounded composer over the existing provider transport.

    CORR-01 · THE TWO FAILURE KINDS ARE SEPARATED AT THIS BOUNDARY, because they
    mean different things to a caller and map to different statuses:

        no credential, network error, non-200          -> SynthesisUnavailable (503)
        HTTP 200 whose body is not the agreed shape    -> SynthesisRejected     (502)

    A 200 that carries unparseable text or the wrong shape is the model failing
    to follow the contract, not the service being down, and telling the caller
    to retry later would be wrong.

    `transport` is injectable so the 200-but-malformed path can be certified
    offline; production passes nothing and uses requests.
    """
    import json
    import os

    instruction = (_SECTION11_INSTRUCTION if task == "section11"
                   else _SECTION13_INSTRUCTION)
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise SynthesisUnavailable("provider credential is not configured")

    if transport is None:
        import requests
        transport = requests.post

    try:
        response = transport(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": api_key, "anthropic-version": "2023-06-01",
                     "content-type": "application/json"},
            json={"model": "claude-sonnet-4-6", "max_tokens": 1200,
                  "system": instruction,
                  "messages": [{"role": "user",
                                "content": json.dumps(atoms, ensure_ascii=False)}]},
            timeout=60)
    except Exception as exc:                       # transport, DNS, timeout
        raise SynthesisUnavailable(f"provider transport failed: {exc}") from exc

    if getattr(response, "status_code", None) != 200:
        raise SynthesisUnavailable(
            f"provider returned {getattr(response, 'status_code', 'no status')}")

    # From here the service answered. Everything else is a CONTENT verdict.
    try:
        body = response.json()
        text = "".join(part.get("text", "") for part in body.get("content", []))
        parsed = json.loads(text.strip().strip("`").removeprefix("json").strip())
    except Exception as exc:
        raise SynthesisRejected(
            f"provider returned 200 with output that is not the agreed "
            f"shape: {exc}") from exc
    if not isinstance(parsed, dict):
        raise SynthesisRejected("provider returned 200 with a non-object body")
    return parsed
