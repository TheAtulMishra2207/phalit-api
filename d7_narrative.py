"""D7-003 · the structured narrative contract for `/d7report`.

The legacy four-heading prose report is retired. The provider now returns a
TYPED set of sections, each owned by exactly one part of the Founder report, and
each validated before anything reaches a reader.

OWNERSHIP IS THE CONTRACT. Section cardinality and ownership may not vary: there
are thirteen sections, no more and no fewer, and each belongs to one place in
the reading. A provider that omits one, invents one, or returns an unsafe one
has its whole response discarded.

THE PROVIDER EXPLAINS. IT DOES NOT DECIDE.
It receives the safe client reading — already-selected Snapshot values, already
selected archetype states, already-computed facts — and writes prose about
them. It is never given the inputs from which a state could be re-derived, and
`assert_selection_untouched` proves afterwards that it did not restate a
different selection than the server chose.
"""

import json
import re
from typing import Any, Dict, List, Optional, Tuple

from d7_client_reading import (
    PublicationViolation,
    assert_publication_safe,
    scan_publication,
)

# The thirteen sections. Order is the reading order; ownership is fixed.
NARRATIVE_SECTIONS: Tuple[str, ...] = (
    "foundation.parental_lens_insight",
    "foundation.biological_seed_insight",
    "archetypes.conception_insight",
    "archetypes.lineage_insight",
    "archetypes.bond_insight",
    "timing.current_period_insight",
    "timing.jupiter_window_insight",
    "timing.saturn_window_insight",
    "lessons.h6_insight",
    "lessons.h12_insight",
    "triangulation.d1",
    "triangulation.d9",
    "triangulation.d7",
)

SECTION_SET = frozenset(NARRATIVE_SECTIONS)

MIN_SECTION_CHARS = 40
MAX_SECTION_CHARS = 1600


class NarrativeContractError(Exception):
    """The provider response does not satisfy the structured contract."""


def _flatten(payload: Dict[str, Any]) -> Dict[str, str]:
    """Flatten one nesting level into dotted keys."""
    flat: Dict[str, str] = {}
    for group, body in payload.items():
        if isinstance(body, dict):
            for leaf, text in body.items():
                flat[f"{group}.{leaf}"] = text
        else:
            flat[group] = body
    return flat


def parse_provider_output(raw: str) -> Dict[str, str]:
    """Parse the provider's JSON response into the flat section map.

    Fail-closed at every step. A response that is not JSON, not an object, or
    carries a non-string section is rejected whole — never partially salvaged.
    """
    text = (raw or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\s*|\s*```$", "", text).strip()
    try:
        payload = json.loads(text)
    except Exception as exc:
        raise NarrativeContractError(f"provider output is not JSON: {exc}")
    if not isinstance(payload, dict):
        raise NarrativeContractError("provider output is not an object")
    flat = _flatten(payload)
    for key, value in flat.items():
        if not isinstance(value, str):
            raise NarrativeContractError(f"section {key!r} is not a string")
    return flat


def validate_sections(flat: Dict[str, str]) -> Dict[str, str]:
    """Exact cardinality and ownership. No missing, no extra."""
    got = set(flat)
    missing = SECTION_SET - got
    if missing:
        raise NarrativeContractError(
            f"missing required sections: {sorted(missing)}")
    extra = got - SECTION_SET
    if extra:
        raise NarrativeContractError(
            f"unexpected sections returned: {sorted(extra)}")
    for key in NARRATIVE_SECTIONS:
        body = flat[key].strip()
        if len(body) < MIN_SECTION_CHARS:
            raise NarrativeContractError(f"section {key!r} is too short")
        if len(body) > MAX_SECTION_CHARS:
            raise NarrativeContractError(f"section {key!r} is too long")
    return {k: flat[k].strip() for k in NARRATIVE_SECTIONS}


def assert_selection_untouched(sections: Dict[str, str],
                               client_reading: Dict[str, Any]) -> None:
    """The provider may not restate a selection the server did not make.

    Two things are checked, both narrow and both mechanical:

    1. No Quick Snapshot label the server did NOT select may appear anywhere in
       the narrative. Naming a rival label is how a narrative silently
       overrides a deterministic verdict.
    2. No archetype state letter other than the selected one may be asserted in
       the `Selected State: State X` form.
    """
    from d7_selectors import (CONCEPTION_VITALITY_WATERFALL,
                              LINEAGE_SCOPE_WATERFALL,
                              PARENTAL_STRENGTH_LABELS)

    blob = "\n".join(sections.values())
    qs = client_reading.get("quick_snapshot", {})

    selected = {
        (qs.get("conception_vitality") or {}).get("value"),
        (qs.get("lineage_scope") or {}).get("value"),
        (qs.get("primary_parental_strength") or {}).get("value"),
    }
    universe = (set(CONCEPTION_VITALITY_WATERFALL)
                | set(LINEAGE_SCOPE_WATERFALL)
                | set(PARENTAL_STRENGTH_LABELS.values()))
    for label in universe - selected:
        if re.search(rf"\b{re.escape(label)}\b", blob):
            raise NarrativeContractError(
                f"narrative asserts a snapshot value the server did not select: {label!r}")

    chosen = {a.get("state") for a in client_reading.get("archetypes", [])}
    for letter in "ABCDE":
        if letter in chosen:
            continue
        if re.search(rf"Selected State:\s*State\s+{letter}\b", blob):
            raise NarrativeContractError(
                f"narrative asserts archetype State {letter}, which was not selected")


def build_narrative(raw: str, client_reading: Dict[str, Any]) -> Dict[str, str]:
    """Parse, validate, safety-scan and selection-check. Fail closed throughout.

    Nothing is scrubbed or partially retained: a violating response is rejected
    whole, and the caller shows the neutral unavailable state.
    """
    flat = parse_provider_output(raw)
    sections = validate_sections(flat)
    assert_publication_safe(sections)          # FD-S1 / FD-S3, fail-closed
    assert_selection_untouched(sections, client_reading)
    return sections


def build_provider_instruction(client_reading: Dict[str, Any]) -> str:
    """The system prompt. Names the schema and the absolute prohibitions."""
    schema = json.dumps(
        {"foundation": {"parental_lens_insight": "…", "biological_seed_insight": "…"},
         "archetypes": {"conception_insight": "…", "lineage_insight": "…",
                        "bond_insight": "…"},
         "timing": {"current_period_insight": "…", "jupiter_window_insight": "…",
                    "saturn_window_insight": "…"},
         "lessons": {"h6_insight": "…", "h12_insight": "…"},
         "triangulation": {"d1": "…", "d9": "…", "d7": "…"}},
        indent=2)
    return f"""You are writing the interpretive prose for a Vedic astrology lineage report.

Return ONLY a JSON object with exactly this shape and no other keys:

{schema}

Absolute rules:
1. Use ONLY the certified reading supplied. No external knowledge, no astrology
   of your own. Every conclusion has already been decided; you explain it.
1b. The approved Parental Lens reading supplied in the certified client reading
   is AUTHORITATIVE. You may explain it, lightly personalise its phrasing to the
   native, and integrate it into the surrounding report. Do not derive a new
   interpretation from the rising sign. Do not contradict, materially expand or
   replace the approved reading. Do not introduce additional Jyotisha.
2. ZERO technical terminology in the prose — no house numbers, no sign names,
   no Sanskrit, no planet names, no rule identifiers, no scores.
3. Second person throughout. Each section 3-6 sentences, plain language first.
4. NEVER state or imply a number of children, the sex of a child,
   childlessness, miscarriage, infant survival, a child's health or illness,
   infertility, a medical or fertility diagnosis, biological compatibility,
   guaranteed adoption or guaranteed conception. This is absolute.
5. The sequence slots are structural positions in a chart, NOT children. Never
   describe a slot as a person and never number a child.
6. Do not name any state, rating or scope label other than the ones supplied.
   You may not change a selection.
7. Timing describes activation CONDITIONS, never guarantees and never dates.
8. Return raw JSON. No markdown fence, no preamble, no trailing commentary."""


def build_provider_user_prompt(client_reading: Dict[str, Any]) -> str:
    return (
        "CERTIFIED READING (this is the complete corpus; nothing else exists):\n"
        + json.dumps(client_reading, indent=1)
        + "\n\nReturn the JSON object with all thirteen sections."
    )
