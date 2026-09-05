"""
pratiphala_routes.py — POST /pratiphala/prepare.

The resolution logic is a set of PURE FUNCTIONS with no I/O, and the route is a
thin shell over them. That split is deliberate: every rule in the spec is
testable without a chart, a snapshot store or a network, so the tests exercise
the doctrine rather than the plumbing.

The route CONSUMES the certified stack and modifies none of it: one snapshot,
one adapter call, and two compute_d1 calls (D1 and D9) off the same
CertifiedChart. Reading one snapshot twice is what keeps the two views from
drifting — the varga is a view selection, not a second chart.
"""
from __future__ import annotations

import logging
import uuid
from typing import Callable, Dict, List, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException
from starlette.concurrency import run_in_threadpool

from d1_contract import Dignity, Graha, Varga
from d1_chart_adapter import ChartAdapterError, to_certified_chart
from d1_engine import CertifiedChart, D1EngineError, compute_d1
# REUSED, NOT REDEFINED. One resolver abstraction and one dependency provider
# serve both routes. A second token store or a private accessor here would be
# two doors onto one snapshot, which is how the two views come apart.
from d1_routes import ChartNotFound, ChartResolver, get_chart_resolver
from pratiphala_narrative import build_narrative_brief, generate_report
from pratiphala_contract import (
    CorpusRef, DIGNITY_RANK, GoverningLabel, GrahaPratiphala, HOUSE_NAMES,
    HouseLordOverlay, PratiphalaPolicyError, RASHI_LORDS, STATE_SA, STRONG_AT,
    expected_lord_of, governing_of,
    governing_sa_of,
    graha_corpus_key_of, quadrant_of, rank_of, strength_of, sub_tier_of,
    PratiphalaEvidence, PratiphalaPolicy, PratiphalaPrepareRequest,
    PratiphalaPrepareResponse, PratiphalaReportRequest, PratiphalaReportResponse,
    PratiphalaState, STATE_SA, SOVEREIGN_SA,
    STRONG_AT, Strength, SubTier,
)

router = APIRouter()
logger = logging.getLogger(__name__)

# PF-009. The sign-lord table now lives in the contract as ONE object; this is
# an alias to it, not a second copy, so the builder and the validator read the
# same sequence by construction.
SIGN_LORDS = RASHI_LORDS


# PF-006. The rank, strength, tier, quadrant and precedence rules now live in
# pratiphala_contract as ONE shared policy, imported above. They were defined
# here and cross-checked there, which is two engines with a handshake; a drift
# in either would have been invisible to the other.
PratiphalaError = PratiphalaPolicyError


def corpus_key_for(state: PratiphalaState, graha: Graha) -> Optional[str]:
    if state is PratiphalaState.UNKNOWN:
        return None
    return f"PRATIPHALA-{graha.value}-{state.value}"


def house_corpus_key_for(house: int, graha: Graha, governing: str) -> Optional[str]:
    """PF-004. House-specific identity: house AND state, never the planetary key.

    The -H{n}- segment is what the contract validator checks, so a key naming a
    different house than its overlay cannot construct.
    """
    if governing == GoverningLabel.UNKNOWN.value:
        return None
    return f"PRATIPHALA-H{house}-{graha.value}-{governing}"


def resolve(graha: Graha, d1_dignity: Optional[Dignity], d9_dignity: Optional[Dignity],
            is_vargottama: bool = False,
            corpus_lookup: Optional[Callable[[str], Optional[str]]] = None
            ) -> GrahaPratiphala:
    """The whole doctrine, in one pure function."""
    d1_rank = rank_of(d1_dignity)
    d9_rank = rank_of(d9_dignity)
    quadrant = quadrant_of(d1_rank, d9_rank)

    # PF-001. PRECEDENCE: ABSENT D9 DIGNITY OUTRANKS THE VARGOTTAMA OVERRIDE.
    # Sovereign is a statement ABOUT a Pratiphala classification — that the
    # quadrant does not govern it. With no certified D9 dignity there is no
    # classification to override, so claiming Sovereign would assert a reading
    # the chart does not support. This branch was second before; UNKNOWN and
    # Sovereign were each tested in isolation and their collision was not.
    # The precedence and the labels come from the shared policy, so the
    # resolver and the validator cannot disagree about them.
    governing = governing_of(quadrant, bool(is_vargottama))
    governing_sa = governing_sa_of(governing)
    key = graha_corpus_key_of(graha, governing)

    if governing is GoverningLabel.UNKNOWN:
        # Name WHICH side is missing, including both, so a reader can tell an
        # unassessed node from a half-assessed one.
        if d1_rank is None and d9_rank is None:
            missing = "D1 or D9"
        else:
            missing = "D1" if d1_rank is None else "D9"
        vg_note = ("; vargottama does not apply because there is no classification "
                   "to override" if is_vargottama else "")
        # PF-013. Was "...which is not the same as depleted". A negation still
        # puts the word beside the graha, and a reader skimming a report sees
        # the word, not the "not". Stated positively instead.
        basis = (f"no certified {missing} dignity for {graha.value}; the manifestation "
                 f"state is unknown, an absence of evidence rather than a "
                 f"judgement{vg_note}")
    elif governing is GoverningLabel.SOVEREIGN:
        # SOVEREIGN OVERRIDES THE QUADRANT. The quadrant stays true and stays
        # recorded, but it does not govern; a consumer renders `governing_state`.
        basis = (f"{graha.value} occupies the same sign in D1 and D9 (vargottama), "
                 f"so the Sovereign override governs; the underlying quadrant is "
                 f"{quadrant.value}")
    else:
        basis = (f"D1 {d1_dignity.value} ({strength_of(d1_rank).value}) with "
                 f"D9 {d9_dignity.value} ({strength_of(d9_rank).value})")  # both present here

    # PF-002. The lookup is not invoked at all without a key, so UNKNOWN never
    # reaches it. `resolvable` reports whether prose was OBTAINED, never whether
    # a key could be built: a known key with no authored prose is resolvable=False.
    raw = corpus_lookup(key) if (key and corpus_lookup) else None
    # PF-003. A lookup that returns "" or whitespace has found nothing. It
    # NORMALISES to None here rather than reaching the model, which rejects
    # blanks: the resolver knows the value came from a miss, the contract only
    # sees the result. Prose is trimmed so trailing newlines from an authored
    # table cannot decide whether a reference resolved.
    text = raw.strip() if (isinstance(raw, str) and raw.strip()) else None
    corpus = CorpusRef(key=key, text=text, resolvable=bool(key and text))

    return GrahaPratiphala(
        graha=graha, d1_dignity=d1_dignity, d9_dignity=d9_dignity,
        d1_sub_tier=sub_tier_of(d1_rank), d9_sub_tier=sub_tier_of(d9_rank),
        is_vargottama=is_vargottama,
        governing_state=governing, governing_state_sa=governing_sa,
        basis=basis, corpus=corpus,
        evidence=PratiphalaEvidence(
            d1_rank=d1_rank, d9_rank=d9_rank,
            d1_strength=strength_of(d1_rank), d9_strength=strength_of(d9_rank),
            underlying_state=quadrant,
            underlying_state_sa=STATE_SA[quadrant],
            strong_at_rank=STRONG_AT,
            # Follows the VERDICT, not the input flag: an UNKNOWN graha may
            # still be vargottama, but no override was applied to it.
            sovereign_override_applied=(governing is GoverningLabel.SOVEREIGN)))


def house_lord_overlays(lagna_sign_index: int,
                        by_graha: Dict[Graha, GrahaPratiphala],
                        corpus_lookup: Optional[Callable[[str], Optional[str]]] = None
                        ) -> List[HouseLordOverlay]:
    """One overlay per house, keyed by house.

    A multi-house lord produces one overlay per owned house. Venus on a Libra
    lagna owns H1 and H8 and appears twice with distinct identity; keying on the
    graha would merge them and lose a house.
    """
    out: List[HouseLordOverlay] = []
    for house in range(1, 13):
        lord = expected_lord_of(lagna_sign_index, house)
        verdict = by_graha[lord]
        gov = verdict.governing_state.value
        name = HOUSE_NAMES[house]
        key = house_corpus_key_for(house, lord, gov)
        # UNKNOWN yields no key, so the lookup is never reached for it.
        raw = corpus_lookup(key) if (key and corpus_lookup) else None
        text = raw.strip() if (isinstance(raw, str) and raw.strip()) else None
        basis = (f"{lord.value} lords H{house} ({name}); "
                 f"{'manifestation unknown' if gov == GoverningLabel.UNKNOWN.value else gov} "
                 f"for this bhāva follows the graha verdict: {verdict.basis}")
        out.append(HouseLordOverlay(
            house=house, house_name=name, lord=lord,
            overlay_key=f"H{house}:{lord.value}",
            verdict=verdict, basis=basis,
            corpus=CorpusRef(key=key, text=text, resolvable=bool(key and text))))
    return out


def build_pratiphala(chart_token: str, d1_by_graha: Dict[Graha, Dignity],
                     d9_by_graha: Dict[Graha, Optional[Dignity]],
                     vargottama: Dict[Graha, bool], lagna_sign_index: int,
                     corpus_lookup: Optional[Callable[[str], Optional[str]]] = None
                     ) -> PratiphalaPrepareResponse:
    by_graha = {
        g: resolve(g, d1_by_graha[g], d9_by_graha.get(g),
                   bool(vargottama.get(g)), corpus_lookup)
        for g in Graha
    }
    return PratiphalaPrepareResponse(
        chart_token=chart_token, policy=PratiphalaPolicy(),
        lagna_sign_index=lagna_sign_index,
        grahas=[by_graha[g] for g in Graha],
        house_lord_overlays=house_lord_overlays(lagna_sign_index, by_graha,
                                                corpus_lookup))


# ── the route ───────────────────────────────────────────────────────────────

def _from_certified(chart: CertifiedChart) -> Tuple[Dict, Dict, Dict, int]:
    """Read both views off ONE snapshot, so they cannot drift."""
    d1_resp, _ = compute_d1(chart, Varga.D1)
    d9_resp, _ = compute_d1(chart, Varga.D9)
    d1 = {g.graha: g.dignity for g in d1_resp.grahas}
    d9 = {g.graha: g.dignity for g in d9_resp.grahas}
    vg = {g.graha: bool(g.vargottama) for g in d1_resp.grahas}
    return d1, d9, vg, d1_resp.lagna_sign_index


async def _prepare_pratiphala(chart_token: str,
                              resolver: ChartResolver) -> PratiphalaPrepareResponse:
    """ONE authoritative path, shared by the structured and narrative endpoints.

    Extracted rather than duplicated: two copies of resolve -> adapt -> compute
    -> build would be two engines that agree today, and the narrative would be
    free to drift from the cards it sits beside.
    """
    try:
        chart_payload = await resolver.resolve(chart_token)
    except ChartNotFound:
        # Unknown, expired, revoked and cross-owner all look identical here.
        raise HTTPException(status_code=404, detail="Unknown or expired chart_token.")
    except HTTPException as exc:
        # ONLY deliberate authentication statuses survive. Everything else is
        # correlated and generalised, because the upstream adapter's own 502/503
        # carry response text that can name internal hosts.
        if exc.status_code in (401, 403):
            raise
        correlation_id = uuid.uuid4().hex[:12]
        logger.exception("pratiphala chart resolver upstream failure [%s]", correlation_id)
        raise HTTPException(status_code=500,
                            detail=f"Chart lookup failed. Reference: {correlation_id}")
    except Exception:
        correlation_id = uuid.uuid4().hex[:12]
        logger.exception("pratiphala chart resolver failed [%s]", correlation_id)
        raise HTTPException(status_code=500,
                            detail=f"Chart lookup failed. Reference: {correlation_id}")

    try:
        # ONE resolved snapshot, ONE adapter call, and both vargas computed off
        # the resulting CertifiedChart. Resolving twice would be two snapshots.
        certified = to_certified_chart(chart_payload, chart_token, varga=Varga.D9)
        d1, d9, vg, lagna = _from_certified(certified)
        return build_pratiphala(chart_token, d1, d9, vg, lagna, _corpus_lookup)
    except (ChartAdapterError, D1EngineError, PratiphalaError) as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.post("/pratiphala/prepare", response_model=PratiphalaPrepareResponse)
async def pratiphala_prepare(req: PratiphalaPrepareRequest,
                             resolver: ChartResolver = Depends(get_chart_resolver)):
    return await _prepare_pratiphala(req.chart_token, resolver)


@router.post("/pratiphalareport", response_model=PratiphalaReportResponse)
async def pratiphala_report(req: PratiphalaReportRequest,
                            resolver: ChartResolver = Depends(get_chart_resolver)):
    """The narrative, generated from the SERVER'S OWN Pratiphala result.

    The client submits a token and an optional name. It cannot submit the
    interpretation the prose describes, so the report and the cards are the
    same reading by construction rather than by agreement.
    """
    result = await _prepare_pratiphala(req.chart_token, resolver)
    # PF-013. The TYPED RESULT is handed to the generator, not a brief. The
    # report is assembled from it server-side; the provider supplies framing
    # only, so its text can never become a verdict.
    # D12-007-LIVE-CORR-02-CORR-01 · THE NARRATIVE FETCH LEAVES THE LOOP.
    #
    # generate_report -> fetch_framing -> requests.post is blocking network I/O
    # reached from this async route. Only the transport placement changes; the
    # released fallback and status semantics are untouched.
    report = await run_in_threadpool(generate_report, result, req.name)
    # The RESOLVED token, which _prepare_pratiphala already bound to the request.
    return PratiphalaReportResponse(chart_token=result.chart_token, report=report)


# ── the one seam that remains ───────────────────────────────────────────────
# The corpus prose does not exist yet: 36 graha entries plus 48 house-lord
# entries is authored content, not engineering. Returning None keeps every
# corpus_ref unresolvable rather than fabricating text.

def _corpus_lookup(key: str) -> Optional[str]:   # pragma: no cover - wiring
    return None
