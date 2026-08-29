"""
d10_publication_contract.py — D10-006 · the shape of the customer publication.

DETERMINISTIC PUBLICATION, NOT NARRATIVE. Every string in this contract is
assembled from a ratified corpus entry and a certified fact. There is no
free-text bucket anywhere: no `notes`, no `extra`, no `Dict[str, Any]` a
provider could later fill.

WHAT HAS NO FIELD, AND THEREFORE CANNOT BE PUBLISHED:

  * `integrated_reading` — §14 is the next flight's, not this one's;
  * `aligned` / `strained` / `redirected` — unratified, and the cross-chart
    block carries facts only;
  * the D9xD10 handshake sentence — composed in the synthesis flight;
  * a Devatā ruler, a Devatā direction, a Lagna Devatā;
  * a self-employment claim, a travel prediction, a Sun/Ketu conflict;
  * a job title, a salary, a timing claim, a remedy.

Strict everywhere: `extra = "forbid"`.
"""
from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

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


PUBLICATION_VERSION = "d10.publication.v1"

PublicationState = Literal["OCCUPIED", "THROUGH_LORD", "SUPPORTED", "PRESSURED"]
HouseMode = Literal["OCCUPIED", "THROUGH_LORD"]


# ─────────────────────────────────────────────────────────────────────────────
# §0 · header
# ─────────────────────────────────────────────────────────────────────────────

class Chip(Strict):
    label: str
    value: str


class Header(Strict):
    """Five chips. `pull` and `vehicle` are Optional because the Chara Karaka
    state may be unresolved, and an absent chip is not a blank one."""
    title: str
    subtitle: str
    stance: Chip
    work_ruler: Chip
    standing: Chip
    pull: Optional[Chip] = None
    vehicle: Optional[Chip] = None


# ─────────────────────────────────────────────────────────────────────────────
# §1 · §2 · §4 · static
# ─────────────────────────────────────────────────────────────────────────────

class Section1(Strict):
    """The copy contract. `sha256` travels with the paragraphs so a consumer
    can verify the bytes were not paraphrased in transit."""
    paragraphs: List[str] = Field(min_items=4, max_items=4)
    newbie_aside: str
    sha256: str


class ReadingStep(Strict):
    step: int = Field(ge=1, le=6)
    look_at: str
    question: str


class Section2(Strict):
    steps: List[ReadingStep] = Field(min_items=6, max_items=6)
    rule: str


class PermittedQuestion(Strict):
    question: str
    read_from: str


# ─────────────────────────────────────────────────────────────────────────────
# §3 · chart card metadata
# ─────────────────────────────────────────────────────────────────────────────

class ChartMeta(Strict):
    """Publication metadata for the diamond. `centre_label` is a Literal fixed
    to D10 — the legacy page printed D9 here, and this contract makes that
    unrepresentable rather than merely corrected."""
    centre_label: Literal["D10"] = "D10"
    d10_lagna_sign: str
    d10_lagnesh: str
    caption: str
    dignity_key: List[str]


# ─────────────────────────────────────────────────────────────────────────────
# §5 · the core triad
# ─────────────────────────────────────────────────────────────────────────────

class StancePublication(Strict):
    speaker: Literal["PARĀŚARA"] = "PARĀŚARA"
    lagna_sign: str
    gloss: str
    lagnesh_line: str
    work_behaviour: str
    overreach: str


class FunctionPublication(Strict):
    """H10 + 10th lord + H6. There is no h3 field."""
    speaker: Literal["PARĀŚARA"] = "PARĀŚARA"
    h10_mode: HouseMode
    #: When `h10_mode` is THROUGH_LORD this MUST begin "Through lord", which
    #: the builder enforces and a test verifies.
    h10_line: str
    h6_line: str
    days_look_like: str


class StandingPublication(Strict):
    speaker: Literal["DIGNITY + PARĀŚARA"] = "DIGNITY + PARĀŚARA"
    sun_line: str
    #: Exactly two claims, in this order: what the public rewards, and what it
    #: does not automatically grant.
    what_is_rewarded: str
    what_is_not_automatic: str


# ─────────────────────────────────────────────────────────────────────────────
# §6 · cross-chart FACTS ONLY
# ─────────────────────────────────────────────────────────────────────────────

class CrossChartFacts(Strict):
    """Packaged from D10-004. NO agreement word and NO handshake sentence:
    neither has a field, so the synthesis flight inherits no guess."""
    provenance_d1_d10: Literal["D1_D10"] = "D1_D10"
    d1_h10_line: str
    d10_h10_line: str
    #: D10-007-CORR-02 · the Founder D1xD10 ruling for Release 1. A FIXED,
    #: NEUTRAL bridge — not a computed relationship grade. `aligned`,
    #: `strained` and `redirected` have no field here and no rule behind them,
    #: so Release 1 states how the two charts relate as a matter of kind and
    #: makes no evaluation. A Literal, so it cannot be paraphrased or extended
    #: with an evaluative second sentence.
    d1_d10_bridge: Literal[
        "Natal H10 describes the visible circumstances of work; D10 shows how "
        "those circumstances are carried when the work is actually lived."
    ] = ("Natal H10 describes the visible circumstances of work; D10 shows how "
         "those circumstances are carried when the work is actually lived.")
    provenance_d9_d10: Literal["D9_D10"] = "D9_D10"
    d9_contribution_available: bool
    d9_contribution_mode: Optional[str] = None
    d10_delivery_line: str
    #: D10-007-CORR-01 · the ONE handshake sentence, composed by
    #: `d10_publication.compose_d9_handshake` and reused unchanged as the §14
    #: D9_HANDSHAKE beat. None when D9 published no contribution, in which case
    #: Section 6 is silent and the §14 beat is omitted — the two stay silent
    #: together because they share this value.
    #:
    #: THIS IS NOT AN AGREEMENT WORD. It names how a certified contribution is
    #: carried through the D10 structure; it classifies nothing.
    d9_handshake_sentence: Optional[str] = None


# ─────────────────────────────────────────────────────────────────────────────
# §7 · pull and vehicle
# ─────────────────────────────────────────────────────────────────────────────

class PullVehiclePublication(Strict):
    speaker: Literal["JAIMINI"] = "JAIMINI"
    available: bool
    unavailable_reason: Optional[str] = None
    vocational_pull: Optional[str] = None
    work_vehicle: Optional[str] = None
    link: Optional[str] = None
    weekly_question: Optional[str] = None


# ─────────────────────────────────────────────────────────────────────────────
# §8 · Devatā
# ─────────────────────────────────────────────────────────────────────────────

class DevataRow(Strict):
    """PLANETARY ROWS ONLY. There is no lagna row, no ruler and no direction."""
    planet: str
    house: int = Field(ge=1, le=12)
    sign: str
    devata: str
    flavour: str


class DevataSection(Strict):
    speaker: Literal["DEVATĀ"] = "DEVATĀ"
    teaching: str
    rows: List[DevataRow]
    #: One climate disclosure when a Devatā falls on three or more grahas,
    #: instead of three separate destiny claims.
    repeat_disclosures: List[str]


# ─────────────────────────────────────────────────────────────────────────────
# §9 · operational map
# ─────────────────────────────────────────────────────────────────────────────

class HouseLine(Strict):
    house: int = Field(ge=1, le=12)
    domain_label: str
    #: "Occupants: …" or "Through lord: {planet} in H{n} {sign}"
    occupancy_line: str
    status: PublicationState
    status_label: Literal["Occupied", "Through lord", "Supported", "Pressured"]
    reading: str


class OperationalGroupPublication(Strict):
    group: Literal["ENTER_ROLE", "DO_WORK", "BE_SEEN_AND_PAID",
                   "HANDLE_PRESSURE", "PATRONS"]
    title: str
    houses: List[HouseLine]


# ─────────────────────────────────────────────────────────────────────────────
# §10 · tension
# ─────────────────────────────────────────────────────────────────────────────

class TensionPublication(Strict):
    """`winner` is copied from D10-003 and never chosen here. `available` is
    False when the selector returned UNKNOWN, and then there is no copy."""
    available: bool
    winner: str
    heading: Optional[str] = None
    body: Optional[str] = None
    word_count: Optional[int] = None
    #: True only for the fallback, which is a contrast and asserts no conflict.
    is_contrast_only: bool = False


# ─────────────────────────────────────────────────────────────────────────────
# §11 · money
# ─────────────────────────────────────────────────────────────────────────────

class MoneyCard(Strict):
    house: Literal[2, 11]
    question: str
    occupancy_line: str
    lord_line: str
    mechanism: str
    note: Optional[str] = None


class MoneyPublication(Strict):
    speaker: Literal["PARĀŚARA"] = "PARĀŚARA"
    h2: MoneyCard
    h11: MoneyCard


# ─────────────────────────────────────────────────────────────────────────────
# §12 · strength
# ─────────────────────────────────────────────────────────────────────────────

class StrengthPair(Strict):
    planet: str
    dignity: str
    house: int = Field(ge=1, le=12)
    sign: str
    reliable_at_work: str
    when_it_overreaches: str


class StrengthPublication(Strict):
    pairs: List[StrengthPair]
    #: Present when no graha qualified. Not an error.
    none_note: Optional[str] = None


# ─────────────────────────────────────────────────────────────────────────────
# §13 · three instructions
# ─────────────────────────────────────────────────────────────────────────────

class InstructionsPublication(Strict):
    """Keyed by the tension winner. `available` is False when the tension is
    UNKNOWN, and then all three lines are absent — not invented."""
    available: bool
    keyed_to: Optional[str] = None
    cultivate: Optional[str] = None
    watch: Optional[str] = None
    practise: Optional[str] = None


# ─────────────────────────────────────────────────────────────────────────────
# §15 · §16
# ─────────────────────────────────────────────────────────────────────────────

class GlossaryEntry(Strict):
    term: str
    meaning: str


# ─────────────────────────────────────────────────────────────────────────────
# the whole publication
# ─────────────────────────────────────────────────────────────────────────────

class D10Publication(Strict):
    publication_version: str = PUBLICATION_VERSION
    chart_token: str
    header: Header
    section1: Section1
    section2: Section2
    chart_meta: ChartMeta
    permitted_questions: List[PermittedQuestion] = Field(min_items=3, max_items=3)
    stance: StancePublication
    function: FunctionPublication
    standing: StandingPublication
    crosschart_facts: CrossChartFacts
    pull_vehicle: PullVehiclePublication
    devata: DevataSection
    operational_map: List[OperationalGroupPublication] = Field(min_items=5,
                                                               max_items=5)
    tension: TensionPublication
    money: MoneyPublication
    strength: StrengthPublication
    instructions: InstructionsPublication
    how_to_use: List[str]
    glossary: List[GlossaryEntry]
