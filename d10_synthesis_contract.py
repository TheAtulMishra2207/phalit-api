"""
d10_synthesis_contract.py — D10-007 · the synthesis and provider boundary.

THE PROVIDER CANNOT WRITE. Not "is asked not to" — cannot. `ProviderSelection`
carries two identifiers and nothing else, and `ProviderResponse` holds a list of
those and nothing else. There is no string field anywhere in the provider
response models, so a returned sentence has nowhere to land and is a
ValidationError rather than something a filter has to catch.

That is the D9-R2 lesson stated structurally: the provider returns identifiers,
never sentences, because the schema has no free-text field.

WHAT THE PROVIDER MAY DO. For each beat it may choose ONE atom to foreground,
from the closed list of atoms that beat offered. That is the entire permitted
influence. It may not reorder beats, add a beat, omit a beat, choose an atom
another beat offered, or supply a value of any kind.

WHAT THE PROVIDER MAY NOT TOUCH. Beat order is fixed. Which beats exist is
determined by the certified findings. Every sentence is composed by the server
from ratified corpus text and certified facts.

THE INTEGRATED READING IS ALWAYS PRODUCIBLE WITHOUT A PROVIDER. `source` records
which path produced it, and the deterministic path is not a degraded mode: it is
the default, and the provider path differs from it only in which atom each beat
foregrounds.

Strict everywhere: `extra = "forbid"`.
"""
from __future__ import annotations

from typing import Dict, List, Literal, Optional

import pydantic
from pydantic import BaseModel, Field

_PYDANTIC_V2 = pydantic.VERSION.startswith("2")

if _PYDANTIC_V2:
    from pydantic import ConfigDict

    class Strict(BaseModel):
        model_config = ConfigDict(extra="forbid")
else:  # pragma: no cover - exercised only on a v1 host

    class Strict(BaseModel):
        class Config:
            extra = "forbid"


SYNTHESIS_VERSION = "d10.synthesis.v1"

#: §14 · the fixed beat order. Not a suggestion and not provider-controllable.
BEAT_STANCE = "STANCE"
BEAT_FUNCTION = "FUNCTION"
BEAT_STANDING = "STANDING"
BEAT_TENSION = "TENSION"
BEAT_D9_HANDSHAKE = "D9_HANDSHAKE"
BEAT_INSTRUCTION = "INSTRUCTION"

#: D10-007-CORR-01 · the corrected §14 order. PULL_VEHICLE IS NOT A §14 BEAT —
#: it belongs to §7, where the Jaimini publication is unchanged. `D9_HANDSHAKE`
#: takes the fourth-from-last position the ticket assigns it.
BEAT_ORDER = (BEAT_STANCE, BEAT_FUNCTION, BEAT_STANDING, BEAT_TENSION,
              BEAT_D9_HANDSHAKE, BEAT_INSTRUCTION)

#: Present on every chart.
MANDATORY_BEATS = (BEAT_STANCE, BEAT_FUNCTION, BEAT_STANDING)

#: Present only when the certified layers support them. Each omission is a
#: determinate consequence of the chart, never a provider choice and never
#: something the word budget may take away.
CONDITIONAL_BEATS = (BEAT_TENSION, BEAT_D9_HANDSHAKE, BEAT_INSTRUCTION)

BeatId = Literal["STANCE", "FUNCTION", "STANDING", "TENSION", "D9_HANDSHAKE",
                 "INSTRUCTION"]

#: §14 word budget.
INTEGRATED_READING_MAX_WORDS = 220

SOURCE_DETERMINISTIC = "DETERMINISTIC"
SOURCE_PROVIDER_SELECTION = "PROVIDER_SELECTION"


# ─────────────────────────────────────────────────────────────────────────────
# ATOMS · what the plan offers
# ─────────────────────────────────────────────────────────────────────────────

class Atom(Strict):
    """One certified fact or ratified corpus line, addressable by id.

    `text` is composed by the server from a ratified corpus entry and certified
    values. It is IN the plan so a reviewer can read what a selection would
    foreground — but the provider returns only `atom_id`, never text, and a
    returned `text` has nowhere to go in `ProviderSelection`.
    """
    atom_id: str
    beat: BeatId
    kind: str
    text: str


class Beat(Strict):
    beat: BeatId
    position: int = Field(ge=1, le=6)
    #: At least one, so a beat can never offer nothing to foreground.
    atoms: List[Atom] = Field(min_items=1)
    #: The atom the deterministic path foregrounds. Always the first offered,
    #: so the default is reproducible by inspection.
    default_atom_id: str


class SynthesisPlan(Strict):
    """Atoms only. No prose the provider could echo back as its own, and no
    field for a sentence."""
    synthesis_version: str = SYNTHESIS_VERSION
    chart_token: str
    beats: List[Beat] = Field(min_items=3, max_items=6)
    omitted_beats: List[BeatId]
    omission_reasons: Dict[str, str]


# ─────────────────────────────────────────────────────────────────────────────
# PROVIDER REQUEST AND RESPONSE
# ─────────────────────────────────────────────────────────────────────────────

class ProviderAtom(Strict):
    """One atom as the PROVIDER sees it. Two fields, and neither identifies a
    chart or a person."""
    atom_id: str
    text: str


class ProviderBeat(Strict):
    """One beat as the provider sees it. No omission reason, no default, no
    `kind` — none of which the provider needs to choose emphasis."""
    beat: BeatId
    position: int = Field(ge=1, le=6)
    atoms: List[ProviderAtom] = Field(min_items=1)


class ProviderRequest(Strict):
    """D10-007-CORR-02 · THE PROVIDER-SAFE REQUEST.

    It previously serialized the whole `SynthesisPlan`, which carries
    `chart_token` — a live chart-resolution capability handed to an outside
    system that has no use for it. A provider choosing emphasis needs the beat,
    its position, and the atoms it may choose between. Nothing else.

    THE REDACTION IS STRUCTURAL. There is no `plan` field, no `chart_token`
    field, and no nested model that carries either, so the token cannot travel
    even if a caller passes the plan by mistake — there is nowhere to put it.

    Absent by construction: chart_token, birth date, birth time, place,
    latitude, longitude, chart resolver identifiers, omission reasons, engine
    metadata, and any raw D1/D9/D10 structure.
    """
    request_version: str = SYNTHESIS_VERSION
    instruction: str
    beats: List[ProviderBeat] = Field(min_items=1, max_items=6)


class ProviderSelection(Strict):
    """TWO IDENTIFIERS. There is no text field, so a sentence cannot be
    returned even by a provider that ignores every instruction."""
    beat: BeatId
    atom_id: str


class ProviderResponse(Strict):
    """A list of selections and nothing else.

    No `notes`, no `reasoning`, no `summary`, no `text`. A provider that returns
    prose produces a ValidationError at the boundary, which is a refusal rather
    than something downstream has to strip.
    """
    selections: List[ProviderSelection] = Field(max_items=6)


# ─────────────────────────────────────────────────────────────────────────────
# THE INTEGRATED READING
# ─────────────────────────────────────────────────────────────────────────────

class ReadingBeat(Strict):
    beat: BeatId
    position: int = Field(ge=1, le=6)
    atom_id: str
    sentence: str


class IntegratedReading(Strict):
    """§14 · composed by the server, always.

    `source` says which path chose the atoms. Both paths compose the same way
    from the same corpus, so the deterministic one is the default rather than a
    fallback in the degraded sense.
    """
    source: Literal["DETERMINISTIC", "PROVIDER_SELECTION"]
    beats: List[ReadingBeat] = Field(min_items=3, max_items=6)
    text: str
    word_count: int = Field(ge=1, le=INTEGRATED_READING_MAX_WORDS)
    #: Present when a provider response was offered and rejected. The reading
    #: is still produced; the rejection is recorded rather than hidden.
    provider_rejected_reason: Optional[str] = None


class D10Synthesis(Strict):
    synthesis_version: str = SYNTHESIS_VERSION
    chart_token: str
    plan: SynthesisPlan
    integrated_reading: IntegratedReading
