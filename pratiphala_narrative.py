"""
pratiphala_narrative.py — the model-facing brief and the narrative provider call.

TWO SEPARATIONS THIS MODULE EXISTS TO ENFORCE:

  1. THE MODEL SEES DISPLAY FIELDS ONLY. build_narrative_brief projects an
     ALLOWLIST out of the typed response. Ranks, strengths, strong_at_rank, the
     underlying quadrant and unresolved corpus keys never reach the prompt.
     Projecting by allowlist rather than deleting a blocklist means a field
     added to the contract later is absent by default rather than leaked by
     omission — the blocklist mistake this programme has already paid for once.

  2. THE MODEL DOES NOT INTERPRET. Every governing state, sub-tier and basis in
     the brief was decided by the server. The prompt says so explicitly and the
     brief carries no inputs from which a state could be recomputed, so the
     model cannot silently disagree with the structured cards.

Provider failures are correlated and generalised. The existing /personality
endpoint returns `Anthropic API error {status}: {response.text[:600]}` straight
to the caller; that is a provider response body on a user-facing error path and
is deliberately NOT reproduced here.
"""
from __future__ import annotations

import json
import logging
import os
import re
import uuid
from typing import Any, Dict, List, Optional

import requests
from fastapi import HTTPException

logger = logging.getLogger(__name__)

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 3000
TIMEOUT_S = 60

# Exactly the display-authorized fields. Nothing else is projected.
GRAHA_FIELDS = ("graha", "d1_dignity", "d9_dignity", "d1_sub_tier", "d9_sub_tier",
                "governing_state", "governing_state_sa", "basis")
HOUSE_FIELDS = ("house", "house_name", "lord", "basis")


def _resolved_text(corpus) -> Optional[str]:
    """Prose ONLY when the server resolved it.

    An unresolvable reference contributes nothing — not the key, not a
    placeholder. A key in the prompt is an invitation to invent what it means.
    """
    if corpus is None:
        return None
    if not getattr(corpus, "resolvable", False):
        return None
    text = getattr(corpus, "text", None)
    return text if (text and text.strip()) else None


def build_narrative_brief(response) -> Dict[str, Any]:
    """Project the typed Pratiphala response down to display fields."""
    grahas: List[Dict[str, Any]] = []
    for g in response.grahas:
        entry = {f: getattr(g, f) for f in GRAHA_FIELDS}
        for k, v in list(entry.items()):
            if hasattr(v, "value"):
                entry[k] = v.value
        text = _resolved_text(g.corpus)
        if text:
            entry["corpus_text"] = text
        grahas.append(entry)

    houses: List[Dict[str, Any]] = []
    for o in response.house_lord_overlays:
        entry = {f: getattr(o, f) for f in HOUSE_FIELDS}
        for k, v in list(entry.items()):
            if hasattr(v, "value"):
                entry[k] = v.value
        entry["governing_state"] = o.verdict.governing_state.value
        text = _resolved_text(o.corpus)
        if text:
            entry["corpus_text"] = text
        houses.append(entry)

    return {"grahas": grahas, "house_overlays": houses}


# ── the server-owned body ───────────────────────────────────────────────────
# PF-013. Every astrological claim in the final report is ASSEMBLED HERE from
# the typed response. The provider contributes two stylistic strings and nothing
# else, so a contradictory or score-bearing model output cannot become the
# report: there is no path from provider text to a verdict.

# SERVER-OWNED TEMPLATES. Static strings in source, chosen by identifier.
#
# PF-013 step B. These replace provider prose entirely. Each one is checked by
# eye once, here, rather than by a growing blocklist on every request: none
# names a graha or a bhava, states a finding, or contains a state, dignity,
# tier, score or rank. They take no substitutions, so nothing from the request
# or the provider can be interpolated into them — the `name` on the request
# reaches the prompt and never the report.
INTRODUCTION_TEMPLATES = {
    "plain": ("What follows is a reading of how the promise in your birth chart "
              "carries through into lived result. Each section is set out in "
              "turn, with the reasoning shown alongside it."),
    "reflective": ("Some things a chart promises arrive readily, and some ask "
                   "more of us before they do. What follows sets out, area by "
                   "area, how that unfolds for you."),
    "practical": ("This reading works through your chart one area at a time. "
                  "For each, you will see what the engine found and the "
                  "reasoning it rested on."),
}

CONCLUSION_TEMPLATES = {
    "plain": ("Read this as a description rather than a verdict. Where the "
              "evidence was not available to assess something, that is said "
              "plainly rather than guessed at."),
    "reflective": ("Take from this what is useful and leave the rest. A "
                   "reading describes tendencies, not certainties, and where "
                   "something could not be assessed it has been left open."),
    "practical": ("Return to this whenever it is useful. Anything that could "
                  "not be assessed from the available evidence has been marked "
                  "as such rather than filled in."),
}


def framing_text(framing):
    """Look up the SERVER'S strings. The provider supplied only the keys."""
    return (INTRODUCTION_TEMPLATES[framing.introduction_id.value],
            CONCLUSION_TEMPLATES[framing.conclusion_id.value])


def _graha_section(g) -> str:
    """Deterministic. Every claim is a field of the typed response."""
    state = g.governing_state.value
    sa = g.governing_state_sa or ""
    head = f"{g.graha.value} \u2014 {state}" + (f" ({sa})" if sa else "")
    if state == "UNKNOWN":
        # Assembled WITHOUT any provider prose, and phrased as unavailable
        # evidence rather than a poor result.
        body = ("The evidence needed to assess this graha is not available. "
                f"{g.basis} No manifestation state is claimed here.")
        return f"{head}\n{body}"
    d1 = f"{g.d1_dignity.value} ({g.d1_sub_tier.value})" if g.d1_dignity else "not available"
    d9 = f"{g.d9_dignity.value} ({g.d9_sub_tier.value})" if g.d9_dignity else "not available"
    body = f"Root: {d1}. Fruit: {d9}. {g.basis}"
    text = _resolved_text(g.corpus)
    if text:
        body += f" {text}"          # verbatim, unaltered
    return f"{head}\n{body}"


def _house_section(o) -> str:
    state = o.verdict.governing_state.value
    sa = o.verdict.governing_state_sa or ""
    head = f"H{o.house} {o.house_name} \u2014 {state}" + (f" ({sa})" if sa else "")
    if state == "UNKNOWN":
        body = ("The evidence needed to assess this bhava is not available. "
                f"{o.basis} No manifestation state is claimed here.")
        return f"{head}\n{body}"
    body = f"{o.basis}"
    text = _resolved_text(o.corpus)
    if text:
        body += f" {text}"
    return f"{head}\n{body}"


def assemble_report(response, framing) -> str:
    """Every string in the output is the server's own.

    The provider contributed two dictionary KEYS. Nothing it returned appears
    anywhere in the result.
    """
    intro, conclusion = framing_text(framing)
    grahas = [_graha_section(g) for g in response.grahas]
    houses = [_house_section(o) for o in response.house_lord_overlays]
    return "\n\n".join(
        [intro, "GRAHA PRATIPHALA"] + grahas +
        ["BHAVA PRATIPHALA"] + houses + [conclusion])


SYSTEM_PROMPT = """You are choosing the tone of a Vedic astrology report.

YOU WRITE NOTHING. The report is written by the engine. Your only job is to pick
which of three prepared openings and which of three prepared closings suits the
reading, and to return those two choices as identifiers.

Return ONLY a JSON object with exactly two keys:

  {"introduction_id": "...", "conclusion_id": "..."}

Each value must be exactly one of:

  "plain"       direct and unadorned
  "reflective"  slower, more contemplative
  "practical"   oriented toward what to do with the reading

Any other value, any extra key, and any prose is rejected. Do not attempt to
write an introduction or a conclusion; the text of both is fixed and is not
yours to supply."""


def _fail(correlation_prefix: str) -> HTTPException:
    correlation_id = uuid.uuid4().hex[:12]
    logger.exception("%s [%s]", correlation_prefix, correlation_id)
    return HTTPException(status_code=500,
                         detail=f"Report generation failed. Reference: {correlation_id}")


def fetch_framing(brief: Dict[str, Any], name: Optional[str] = None):
    """Ask the provider for two stylistic strings. Nothing else is accepted."""
    from pratiphala_contract import ProviderFraming     # local: avoid a cycle

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise HTTPException(status_code=500,
                            detail="ANTHROPIC_API_KEY not configured on server.")

    subject = name or "the native"
    user_prompt = (
        f"Choose the opening and closing tone for {subject}'s Pratiphala "
        f"reading. Return only the JSON object with the two identifiers.")
    try:
        response = requests.post(
            ANTHROPIC_URL,
            headers={"x-api-key": api_key,
                     "anthropic-version": "2023-06-01",
                     "content-type": "application/json"},
            json={"model": MODEL, "max_tokens": MAX_TOKENS,
                  "system": SYSTEM_PROMPT,
                  "messages": [{"role": "user", "content": user_prompt}]},
            timeout=TIMEOUT_S)
    except Exception:
        raise _fail("pratiphala narrative provider unreachable")

    if response.status_code != 200:
        logger.error("pratiphala narrative provider returned %s: %s",
                     response.status_code, str(response.text)[:600])
        raise _fail(f"pratiphala narrative provider returned {response.status_code}")

    try:
        data = response.json()
        text = "".join(b["text"] for b in data.get("content", [])
                       if b.get("type") == "text").strip()
        if text.startswith("```"):
            text = text.strip("`")
            text = text[text.index("{"):]
        parsed = json.loads(text[text.index("{"):text.rindex("}") + 1])
    except Exception:
        raise _fail("pratiphala framing response was unreadable")

    try:
        # Extra.forbid: a missing, duplicate or extra field is refused here.
        framing = ProviderFraming(**parsed)
    except Exception:
        # Only the KEYS are logged. An unknown id or a smuggled prose field is
        # provider content and never reaches the caller or the log body.
        logger.error("pratiphala framing did not match the contract: keys=%s",
                     sorted(parsed) if isinstance(parsed, dict) else type(parsed).__name__)
        raise _fail("pratiphala provider framing did not match the contract")

    return framing


def generate_report(response, name: Optional[str] = None) -> str:
    """PF-013. The report is ASSEMBLED, never adopted.

    `response` is the accepted typed PratiphalaPrepareResponse. The provider's
    text reaches the output only as an introduction and a conclusion, both
    validated, and neither can carry a verdict because verdicts are built from
    the typed result rather than parsed out of prose.
    """
    brief = build_narrative_brief(response)
    framing = fetch_framing(brief, name)
    return assemble_report(response, framing)
