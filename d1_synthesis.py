"""
d1_synthesis.py — Phalit.ai D1 drawer synthesis, server-side (KAR-093 step 5).

Ports the per-graha drawer that newphalit.html currently composes in
buildDrawerContent(). SCOPE IS DELIBERATELY NARROW (founder ruling): synthesis
only. Harm classification and neutral framing (KAR-091) stay client-side for
now and are layered in afterwards.

WHAT THIS MODULE EMITS: structured, typed facts and DERIVED JUDGMENTS.
WHAT IT DOES NOT EMIT: HTML, corpus prose, colours, or any harm framing. The
frontend keeps the corpus and renders from `corpus_key` + the typed fields, so
this port does not duplicate the corpus or disturb KAR-091.

The defects this port exists to remove, all present in the client version:

  KAR-081/085  buildDrawerContent calls getPlanetsAspectingHouse /
               getPlanetsAspectingPlanet three separate times. Here every
               drishti fact is read from the ONE canonical aspect manifest
               produced by compute_d1 — nothing is recomputed.

  KAR-083      the client's `_isEff(a, positive)` treats a natural malefic as
               positive when getScore(a) >= 3, i.e. dignity reverses natural
               maleficence. That override is NOT ported. Influence polarity
               comes from the doctrine layer (natural nature + functional
               role), where dignity plays no part.

  KAR-086      the client computes Moon waxing/waning twice in this one
               function (`moonWaningS` and `_moonW2`). Here the single stored
               paksha resolution is consumed.

  KAR-080      dignity is read from the certified chart, never recomputed.

  KAR-090      chart-level material stays out of the per-graha payload.

Shadbala (client section 6) is NOT computed here. The client's own note calls
the full engine "Phase 6"; digbala/uchcha values are accepted as optional
pass-through inputs and only banded, so this port invents no strength formula.
"""
from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from d1_contract import D1PrepareResponse, Dignity, Graha
from d1_engine import (
    D1Doctrine, DIGNITY_LABELS, InfluencePolarity, NaturalNature,
)
from d1_functional_roles import (
    FunctionalNature, MarakaStatus, VerseYogaStatus, SIGN_LORDS,
)

SYNTHESIS_VERSION = "d1-synthesis-0.1.0"

HOUSE_NAMES = {
    1: "Tanu", 2: "Dhana", 3: "Sahaja", 4: "Sukha", 5: "Putra", 6: "Ari",
    7: "Yuvati", 8: "Randhra", 9: "Dharma", 10: "Karma", 11: "Labha", 12: "Vyaya",
}
# Bhavat Bhavam: the house as many houses from itself (H1->H1, H4->H7, ...).
def bhavat_bhavam(house: int) -> int:
    return (2 * house - 1 - 1) % 12 + 1

# TWO DISTINCT client tables, kept separate (QA step-5 HIGH-2 — merging them
# corrupted H4 and H10).
#
#   BHAVA_KARAKA          — the drawer's Bhava-Karaka section (client line 6556).
#                           H4 is Moon alone; H10 is Sun/Mercury.
#   HOUSE_NATURAL_KARAKA  — the Graha-Saar own-house awareness map (client line
#                           29381). H10 additionally includes Jupiter and Saturn.
#
# The client assesses only the FIRST listed karaka of the Bhava-Karaka entry
# ("Saturn/Mars".split('/')[0]), so section order is significant here.
BHAVA_KARAKA: Dict[int, List[Graha]] = {
    1: [Graha.SUN], 2: [Graha.JUPITER], 3: [Graha.MARS], 4: [Graha.MOON],
    5: [Graha.JUPITER], 6: [Graha.SATURN, Graha.MARS], 7: [Graha.VENUS],
    8: [Graha.SATURN], 9: [Graha.JUPITER, Graha.SUN], 10: [Graha.SUN, Graha.MERCURY],
    11: [Graha.JUPITER], 12: [Graha.SATURN],
}
HOUSE_NATURAL_KARAKA: Dict[int, List[Graha]] = {
    1: [Graha.SUN], 2: [Graha.JUPITER], 3: [Graha.MARS], 4: [Graha.MOON],
    5: [Graha.JUPITER], 6: [Graha.SATURN, Graha.MARS], 7: [Graha.VENUS],
    8: [Graha.SATURN], 9: [Graha.JUPITER, Graha.SUN],
    10: [Graha.SUN, Graha.MERCURY, Graha.JUPITER, Graha.SATURN],
    11: [Graha.JUPITER], 12: [Graha.SATURN],
}
# House of maximum directional strength (flag only; no digbala value computed).
DIGBALA_PEAK_HOUSE: Dict[Graha, int] = {
    Graha.SUN: 10, Graha.MOON: 4, Graha.MARS: 10, Graha.MERCURY: 1,
    Graha.JUPITER: 1, Graha.VENUS: 4, Graha.SATURN: 7,
}

# ── corpus reference contract (QA step-5 HIGH-3) ─────────────────────────────
# The renderer must index the corpus directly from these fields — never parse a
# composite string and never reconstruct a numeric score.
#
#   RASHI_CORPUS[ref.graha][ref.key]   key is a legacy dignity tier
#   HOUSE_CORPUS[ref.graha][ref.key]   key is the house number
#   BHAVAT_DESC[ref.key]               key is the house number
#   BHAVA_KARAKA[ref.key]              key is the house number
#
# The RASHI corpus is keyed by the Dignity ENUM VALUE directly. The former
# LEGACY_RASHI_KEY table (which mapped nine Dignity values onto the seven
# numeric tiers the legacy client corpus defined, collapsing
# GREAT_FRIEND/FRIEND and ENEMY/GREAT_ENEMY) is DELETED. The client now carries
# a D1-only enum-keyed projection, so no score is ever reconstructed and no
# collapse happens on the server side.
class CorpusName(str, Enum):
    RASHI = "RASHI_CORPUS"
    HOUSE = "HOUSE_CORPUS"
    BHAVAT = "BHAVAT_DESC"
    BHAVA_KARAKA = "BHAVA_KARAKA"

class CorpusRef(BaseModel):
    """A directly resolvable corpus lookup. No composite strings."""
    corpus: CorpusName
    key: str
    graha: Optional[Graha] = None      # required for RASHI_CORPUS / HOUSE_CORPUS
    dignity: Optional[Dignity] = None  # echoed for RASHI so the renderer can
                                       # migrate to enum keys without a reparse
    resolvable: bool = True            # false when no dignity is available

class SynthesisError(ValueError):
    """Raised when the payload cannot be built from the given inputs. This
    module never repairs missing inputs by computing astronomy or dignity."""

# ── typed judgment vocabularies (no prose, no scores) ────────────────────────

class SupportLevel(str, Enum):
    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"
    UNKNOWN = "unknown"      # dignity absent (nodes) — never guessed

class StrengthVerdict(str, Enum):
    EXCEPTIONAL = "exceptional"
    WELL_PLACED = "well_placed"
    NEUTRAL = "neutral"
    STRAINED = "strained"
    WEAKENED = "weakened"
    UNKNOWN = "unknown"

class BalaBand(str, Enum):
    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"

# Dignity → support/strength, read from the CERTIFIED dignity enum rather than
# the client's degree-blind numeric score table (KAR-080).
_SUPPORT_BY_DIGNITY: Dict[Dignity, SupportLevel] = {
    Dignity.EXALTED: SupportLevel.STRONG,
    Dignity.MOOLATRIKONA: SupportLevel.STRONG,
    Dignity.OWN: SupportLevel.STRONG,
    Dignity.GREAT_FRIEND: SupportLevel.MODERATE,
    Dignity.FRIEND: SupportLevel.MODERATE,
    Dignity.NEUTRAL: SupportLevel.MODERATE,
    Dignity.ENEMY: SupportLevel.WEAK,
    Dignity.GREAT_ENEMY: SupportLevel.WEAK,
    Dignity.DEBILITATED: SupportLevel.WEAK,
}
_VERDICT_BY_DIGNITY: Dict[Dignity, StrengthVerdict] = {
    Dignity.EXALTED: StrengthVerdict.EXCEPTIONAL,
    Dignity.MOOLATRIKONA: StrengthVerdict.EXCEPTIONAL,
    Dignity.OWN: StrengthVerdict.WELL_PLACED,
    Dignity.GREAT_FRIEND: StrengthVerdict.WELL_PLACED,
    Dignity.FRIEND: StrengthVerdict.WELL_PLACED,
    Dignity.NEUTRAL: StrengthVerdict.NEUTRAL,
    Dignity.ENEMY: StrengthVerdict.STRAINED,
    Dignity.GREAT_ENEMY: StrengthVerdict.WEAKENED,
    Dignity.DEBILITATED: StrengthVerdict.WEAKENED,
}

# The client applies DIFFERENT thresholds per section: Bhavesh and Bhavat
# Bhavam treat score >= 2 as strong, but Bhava Karaka requires score >= 3.
# Both thresholds are preserved rather than unified.
_KARAKA_SUPPORT_BY_DIGNITY: Dict[Dignity, SupportLevel] = {
    Dignity.EXALTED: SupportLevel.STRONG,        # score 4
    Dignity.MOOLATRIKONA: SupportLevel.STRONG,   # score 3
    Dignity.OWN: SupportLevel.MODERATE,          # score 2 — NOT strong for a karaka
    Dignity.GREAT_FRIEND: SupportLevel.MODERATE,
    Dignity.FRIEND: SupportLevel.MODERATE,
    Dignity.NEUTRAL: SupportLevel.MODERATE,
    Dignity.ENEMY: SupportLevel.WEAK,
    Dignity.GREAT_ENEMY: SupportLevel.WEAK,
    Dignity.DEBILITATED: SupportLevel.WEAK,
}

def support_of(dignity: Optional[Dignity]) -> SupportLevel:
    """Bhavesh / Bhavat-Bhavam threshold (client: score >= 2 strong)."""
    return _SUPPORT_BY_DIGNITY.get(dignity, SupportLevel.UNKNOWN) if dignity else SupportLevel.UNKNOWN

def karaka_support_of(dignity: Optional[Dignity]) -> SupportLevel:
    """Bhava-Karaka threshold (client: score >= 3 strong)."""
    return _KARAKA_SUPPORT_BY_DIGNITY.get(dignity, SupportLevel.UNKNOWN) if dignity else SupportLevel.UNKNOWN

def verdict_of(dignity: Optional[Dignity]) -> StrengthVerdict:
    return _VERDICT_BY_DIGNITY.get(dignity, StrengthVerdict.UNKNOWN) if dignity else StrengthVerdict.UNKNOWN

# ── payload models ───────────────────────────────────────────────────────────

class GrahaRef(BaseModel):
    """A graha and where it sits. Dignity is echoed from the certified chart."""
    graha: Graha
    house: int = Field(ge=1, le=12)
    sign: str
    degree_in_sign: float
    dignity: Optional[Dignity] = None
    dignity_label: Optional[str] = None
    retrograde: bool = False

class DrishtiSource(BaseModel):
    """One aspect landing on the subject, taken from the canonical manifest."""
    source: Graha
    kind: str                      # AspectKind value, e.g. "7th"
    polarity: InfluencePolarity    # from the doctrine layer, NOT from dignity
    basis: str

class DrishtiBlock(BaseModel):
    subject: str                   # "H7" or "Venus (Bhavesh)"
    sources: List[DrishtiSource] = Field(default_factory=list)
    net: InfluencePolarity
    # Grouped for rendering; a source appears in exactly one list.
    supportive: List[Graha] = Field(default_factory=list)
    challenging: List[Graha] = Field(default_factory=list)
    mixed: List[Graha] = Field(default_factory=list)
    unassessed: List[Graha] = Field(default_factory=list)

class RashiSection(BaseModel):
    sign: str
    sign_index: int = Field(ge=0, le=11)
    dignity: Optional[Dignity] = None
    dignity_label: Optional[str] = None
    sign_lord: GrahaRef
    corpus_ref: CorpusRef

class HouseSection(BaseModel):
    house: int = Field(ge=1, le=12)
    house_name: str
    sign: str
    house_lord: Graha
    drishti: DrishtiBlock
    corpus_ref: CorpusRef

class BhaveshSection(BaseModel):
    bhavesh: Graha
    of_sign: str
    position: Optional[GrahaRef] = None
    support: SupportLevel
    retrograde_note: bool = False
    drishti: Optional[DrishtiBlock] = None

class BhavatBhavamSection(BaseModel):
    from_house: int = Field(ge=1, le=12)
    bb_house: int = Field(ge=1, le=12)
    bb_house_name: str
    bb_lord: Optional[Graha] = None
    bb_lord_position: Optional[GrahaRef] = None
    sustaining: SupportLevel
    corpus_ref: CorpusRef

class BhavaKarakaSection(BaseModel):
    house: int = Field(ge=1, le=12)
    karakas: List[Graha] = Field(default_factory=list)
    karaka_positions: List[GrahaRef] = Field(default_factory=list)
    primary_karaka: Optional[Graha] = None   # the client assesses only the first
    karaka_support: SupportLevel = SupportLevel.UNKNOWN
    subject_is_karaka_of_own_house: bool = False
    corpus_ref: CorpusRef

class ShadbalaInput(BaseModel):
    """Pass-through Bala values supplied by the caller. Shashtiamsa scale is
    0-60, so out-of-range values are rejected rather than banded (QA bounded
    correction). None means the component was not supplied."""
    digbala: Optional[float] = Field(default=None, ge=0, le=60)
    uchcha_bala: Optional[float] = Field(default=None, ge=0, le=60)
    naisargika_bala: Optional[float] = Field(default=None, ge=0, le=60)

class ShadbalaSection(BaseModel):
    """NOT computed here — see the module docstring. Values are optional
    pass-through inputs; only the band is derived."""
    computed_server_side: bool = False
    digbala: Optional[float] = None
    digbala_band: Optional[BalaBand] = None
    uchcha_bala: Optional[float] = None
    uchcha_band: Optional[BalaBand] = None
    naisargika_bala: Optional[float] = None
    naisargika_band: Optional[BalaBand] = None
    at_digbala_peak_house: bool = False
    note_key: str = "shadbala_phase6"

class OverallVerdict(str, Enum):
    """The client's composite Graha-Saar conclusion, as a typed value."""
    STRONG = "strong"
    NUANCED = "nuanced"
    WEAK = "weak"
    UNKNOWN = "unknown"

class VerdictFactor(BaseModel):
    factor: str
    direction: str      # "positive" | "negative"
    detail: str

class GrahaSaarSection(BaseModel):
    """The overall summary, as typed judgments only.

    The functional_* fields are None for Rahu and Ketu: they own no rāśi, so
    the BPHS 34 lordship doctrine does not apply to them (locked node ruling).
    They are NOT given a fabricated functional role."""
    strength_verdict: StrengthVerdict
    natural_nature: NaturalNature
    natural_nature_basis: str
    has_lordship_doctrine: bool = True
    functional_nature: Optional[FunctionalNature] = None
    verse_yoga_status: Optional[VerseYogaStatus] = None
    ownership_yogakaraka: Optional[bool] = None
    maraka_status: Optional[MarakaStatus] = None
    functional_basis_verse: Optional[str] = None
    functional_roles_publishable: bool
    retrograde: bool = False
    at_digbala_peak_house: bool = False
    is_natural_karaka_of_own_house: bool = False
    house_drishti: DrishtiBlock
    bhavesh_drishti: Optional[DrishtiBlock] = None
    # Composite conclusion, replacing the client's inline paragraph assembly.
    overall_verdict: OverallVerdict = OverallVerdict.UNKNOWN
    verdict_factors: List[VerdictFactor] = Field(default_factory=list)

class GrahaDrawer(BaseModel):
    synthesis_version: str = SYNTHESIS_VERSION
    graha: Graha
    position: GrahaRef
    rashi: RashiSection
    house: HouseSection
    bhavesh: BhaveshSection
    bhavat_bhavam: BhavatBhavamSection
    bhava_karaka: BhavaKarakaSection
    shadbala: ShadbalaSection
    graha_saar: GrahaSaarSection

class D1DrawerPayload(BaseModel):
    synthesis_version: str = SYNTHESIS_VERSION
    chart_token: str
    drawers: List[GrahaDrawer] = Field(min_items=9, max_items=9)

# ── synthesis ────────────────────────────────────────────────────────────────

def _slug(text: str) -> str:
    """Corpus keys are short identifiers, never sentences."""
    return text.lower().replace(" ", "_")

def _band(value: Optional[float], strong: float, moderate: float) -> Optional[BalaBand]:
    if value is None:
        return None
    if value >= strong:
        return BalaBand.STRONG
    if value >= moderate:
        return BalaBand.MODERATE
    return BalaBand.WEAK

def _graha_ref(resp: D1PrepareResponse, g: Graha) -> GrahaRef:
    st = next((x for x in resp.grahas if x.graha == g), None)
    if st is None:
        raise SynthesisError(f"graha {g.value} missing from the D1 response")
    return GrahaRef(
        graha=g, house=st.house, sign=st.sign, degree_in_sign=st.degree_in_sign,
        dignity=st.dignity,
        dignity_label=DIGNITY_LABELS.get(st.dignity) if st.dignity else None,
        retrograde=st.retrograde)

def _polarity_index(doc: D1Doctrine) -> Dict[int, Dict[Graha, tuple]]:
    """house -> {source graha: (polarity, basis)} taken from the doctrine's
    house_influences, i.e. the SAME evidence the UI displays (KAR-082)."""
    out: Dict[int, Dict[Graha, tuple]] = {}
    for hi in doc.house_influences:
        bucket = out.setdefault(hi.house, {})
        for e in hi.evidence:
            if e.via == "drishti":
                bucket[e.source] = (e.polarity, e.basis)
    return out

def _drishti_block(subject: str, house: int, resp: D1PrepareResponse,
                   pol_index: Dict[int, Dict[Graha, tuple]],
                   exclude: Optional[Graha] = None,
                   only_targets: Optional[Graha] = None) -> DrishtiBlock:
    """Build a drishti block by READING the canonical manifest (KAR-081/085).
    only_targets restricts to edges that land on a particular graha, which is
    how the Bhavesh block is built without a second aspect computation."""
    sources: List[DrishtiSource] = []
    for e in resp.aspects:
        if e.target_house != house:
            continue
        if exclude is not None and e.source == exclude:
            continue
        if only_targets is not None and only_targets not in e.target_grahas:
            continue
        pol, basis = pol_index.get(house, {}).get(
            e.source, (InfluencePolarity.UNASSESSED, f"{e.source.value}: no recorded influence evidence"))
        sources.append(DrishtiSource(source=e.source, kind=e.kind.value, polarity=pol, basis=basis))

    groups: Dict[InfluencePolarity, List[Graha]] = {p: [] for p in InfluencePolarity}
    for s in sources:
        groups[s.polarity].append(s.source)
    assessed = {s.polarity for s in sources if s.polarity != InfluencePolarity.UNASSESSED}
    if not assessed:
        net = InfluencePolarity.UNASSESSED
    elif assessed == {InfluencePolarity.SUPPORTIVE}:
        net = InfluencePolarity.SUPPORTIVE
    elif assessed == {InfluencePolarity.CHALLENGING}:
        net = InfluencePolarity.CHALLENGING
    else:
        net = InfluencePolarity.MIXED
    return DrishtiBlock(
        subject=subject, sources=sources, net=net,
        supportive=groups[InfluencePolarity.SUPPORTIVE],
        challenging=groups[InfluencePolarity.CHALLENGING],
        mixed=groups[InfluencePolarity.MIXED],
        unassessed=groups[InfluencePolarity.UNASSESSED])

def _overall_verdict(strength: StrengthVerdict, bhavesh_support: SupportLevel,
                     house_net: InfluencePolarity, karaka_support: SupportLevel,
                     at_digbala_peak: bool, is_own_karaka: bool) -> tuple:
    """Composite Graha-Saar conclusion — DECISION TABLE, not factor counting.

    Client parity rule (QA step-5 v2):

        strong = (well placed OR own-house natural karaka OR digbala peak)
                 AND Bhavesh strong
                 AND house drishti neither challenging nor mixed

        weak   = strained/weakened
                 AND Bhavesh weak
                 AND NOT own-house natural karaka
                 AND NOT digbala peak

        otherwise = nuanced

    Every clause is conjunctive: a single missing condition drops the verdict to
    nuanced. Deliberately NOT ported: the client's `_isEff` score-based polarity
    flip (KAR-083). Dignity enters only through `strength`; it never reverses a
    drishti polarity. `verdict_factors` is explanatory output for the renderer
    and plays no part in choosing the verdict.
    """
    factors: List[VerdictFactor] = []

    well_placed = strength in (StrengthVerdict.EXCEPTIONAL, StrengthVerdict.WELL_PLACED)
    strained = strength in (StrengthVerdict.STRAINED, StrengthVerdict.WEAKENED)

    if well_placed:
        factors.append(VerdictFactor(factor="strength", direction="positive", detail=strength.value))
    elif strained:
        factors.append(VerdictFactor(factor="strength", direction="negative", detail=strength.value))
    if bhavesh_support == SupportLevel.STRONG:
        factors.append(VerdictFactor(factor="bhavesh", direction="positive", detail="sign lord well placed"))
    elif bhavesh_support == SupportLevel.WEAK:
        factors.append(VerdictFactor(factor="bhavesh", direction="negative", detail="sign lord weakly placed"))
    if house_net == InfluencePolarity.SUPPORTIVE:
        factors.append(VerdictFactor(factor="house_drishti", direction="positive", detail="supportive drishti"))
    elif house_net == InfluencePolarity.CHALLENGING:
        factors.append(VerdictFactor(factor="house_drishti", direction="negative", detail="challenging drishti"))
    elif house_net == InfluencePolarity.MIXED:
        factors.append(VerdictFactor(factor="house_drishti", direction="negative", detail="mixed drishti"))
    if karaka_support == SupportLevel.STRONG:
        factors.append(VerdictFactor(factor="bhava_karaka", direction="positive", detail="natural significator strong"))
    elif karaka_support == SupportLevel.WEAK:
        factors.append(VerdictFactor(factor="bhava_karaka", direction="negative", detail="natural significator weak"))
    if at_digbala_peak:
        factors.append(VerdictFactor(factor="digbala_house", direction="positive", detail="house of maximum directional strength"))
    if is_own_karaka:
        factors.append(VerdictFactor(factor="natural_karaka", direction="positive", detail="natural karaka of its own house"))

    is_strong = (
        (well_placed or is_own_karaka or at_digbala_peak)
        and bhavesh_support == SupportLevel.STRONG
        and house_net not in (InfluencePolarity.CHALLENGING, InfluencePolarity.MIXED)
    )
    is_weak = (
        strained
        and bhavesh_support == SupportLevel.WEAK
        and not is_own_karaka
        and not at_digbala_peak
    )
    if is_strong:
        return OverallVerdict.STRONG, factors
    if is_weak:
        return OverallVerdict.WEAK, factors
    if strength == StrengthVerdict.UNKNOWN and not factors:
        return OverallVerdict.UNKNOWN, factors
    return OverallVerdict.NUANCED, factors

def build_drawer(graha: Graha, resp: D1PrepareResponse, doc: D1Doctrine,
                 shadbala_inputs: Optional[ShadbalaInput] = None) -> GrahaDrawer:
    pos = _graha_ref(resp, graha)
    pol_index = _polarity_index(doc)
    house_state = next(h for h in resp.houses if h.house == pos.house)

    # 1 · Rashi — dignity echoed, never recomputed (KAR-080)
    sign_index = next(x.sign_index for x in resp.grahas if x.graha == graha)
    sign_lord = SIGN_LORDS[sign_index]
    rashi = RashiSection(
        sign=pos.sign, sign_index=sign_index, dignity=pos.dignity,
        dignity_label=pos.dignity_label, sign_lord=_graha_ref(resp, sign_lord),
        corpus_ref=CorpusRef(
            corpus=CorpusName.RASHI, graha=graha, dignity=pos.dignity,
            key=pos.dignity.value if pos.dignity else "",
            resolvable=pos.dignity is not None))

    # 2 · House — drishti from the one manifest
    house_sec = HouseSection(
        house=pos.house, house_name=HOUSE_NAMES[pos.house], sign=house_state.sign,
        house_lord=house_state.lord,
        drishti=_drishti_block(f"H{pos.house}", pos.house, resp, pol_index, exclude=graha),
        corpus_ref=CorpusRef(corpus=CorpusName.HOUSE, graha=graha, key=str(pos.house)))

    # 3 · Bhavesh — the lord of the sign the graha occupies
    bh_ref = _graha_ref(resp, sign_lord)
    bhavesh = BhaveshSection(
        bhavesh=sign_lord, of_sign=pos.sign, position=bh_ref,
        support=support_of(bh_ref.dignity), retrograde_note=bh_ref.retrograde,
        drishti=_drishti_block(f"{sign_lord.value} (Bhavesh)", bh_ref.house, resp,
                               pol_index, exclude=graha, only_targets=sign_lord))

    # 4 · Bhavat Bhavam
    bb_h = bhavat_bhavam(pos.house)
    bb_state = next(h for h in resp.houses if h.house == bb_h)
    bb_lord_ref = _graha_ref(resp, bb_state.lord)
    bb = BhavatBhavamSection(
        from_house=pos.house, bb_house=bb_h, bb_house_name=HOUSE_NAMES[bb_h],
        bb_lord=bb_state.lord, bb_lord_position=bb_lord_ref,
        sustaining=support_of(bb_lord_ref.dignity),
        corpus_ref=CorpusRef(corpus=CorpusName.BHAVAT, key=str(pos.house)))

    # 5 · Bhava Karaka
    bk_karakas = BHAVA_KARAKA.get(pos.house, [])
    bk_primary = bk_karakas[0] if bk_karakas else None
    bk_primary_ref = _graha_ref(resp, bk_primary) if bk_primary else None
    bk = BhavaKarakaSection(
        house=pos.house, karakas=bk_karakas,
        karaka_positions=[_graha_ref(resp, k) for k in bk_karakas],
        primary_karaka=bk_primary,
        karaka_support=karaka_support_of(bk_primary_ref.dignity) if bk_primary_ref else SupportLevel.UNKNOWN,
        subject_is_karaka_of_own_house=graha in bk_karakas,
        corpus_ref=CorpusRef(corpus=CorpusName.BHAVA_KARAKA, key=str(pos.house)))
    # Graha-Saar awareness uses the SEPARATE map (H10 adds Jupiter and Saturn)
    saar_karakas = HOUSE_NATURAL_KARAKA.get(pos.house, [])

    # 6 · Shadbala — pass-through only
    sb_in = shadbala_inputs or ShadbalaInput()
    sb = ShadbalaSection(
        computed_server_side=False,
        digbala=sb_in.digbala, digbala_band=_band(sb_in.digbala, 45, 25),
        uchcha_bala=sb_in.uchcha_bala, uchcha_band=_band(sb_in.uchcha_bala, 45, 25),
        naisargika_bala=sb_in.naisargika_bala, naisargika_band=_band(sb_in.naisargika_bala, 40, 25),
        at_digbala_peak_house=(DIGBALA_PEAK_HOUSE.get(graha) == pos.house))

    # 7 · Graha Saar — typed judgments only; dignity NEVER reverses nature
    nature = next(n for n in doc.natures if n.graha == graha)
    role = next((o for o in doc.functional_roles_orthogonal if o.graha == graha), None)
    saar = GrahaSaarSection(
        strength_verdict=verdict_of(pos.dignity),
        natural_nature=nature.natural_nature, natural_nature_basis=nature.basis,
        has_lordship_doctrine=(role is not None),
        functional_nature=role.functional_nature if role else None,
        verse_yoga_status=role.verse_yoga_status if role else None,
        ownership_yogakaraka=role.ownership_yogakaraka if role else None,
        maraka_status=role.maraka_status if role else None,
        functional_basis_verse=role.verse if role else None,
        functional_roles_publishable=doc.orthogonal_roles_publishable,
        retrograde=pos.retrograde,
        at_digbala_peak_house=(DIGBALA_PEAK_HOUSE.get(graha) == pos.house),
        is_natural_karaka_of_own_house=graha in saar_karakas,
        house_drishti=house_sec.drishti, bhavesh_drishti=bhavesh.drishti)
    saar.overall_verdict, saar.verdict_factors = _overall_verdict(
        strength=saar.strength_verdict, bhavesh_support=bhavesh.support,
        house_net=house_sec.drishti.net, karaka_support=bk.karaka_support,
        at_digbala_peak=saar.at_digbala_peak_house,
        is_own_karaka=saar.is_natural_karaka_of_own_house)

    return GrahaDrawer(graha=graha, position=pos, rashi=rashi, house=house_sec,
                       bhavesh=bhavesh, bhavat_bhavam=bb, bhava_karaka=bk,
                       shadbala=sb, graha_saar=saar)

def build_d1_drawers(resp: D1PrepareResponse, doc: D1Doctrine,
                     shadbala_inputs: Optional[Dict[Graha, ShadbalaInput]] = None
                     ) -> D1DrawerPayload:
    si = shadbala_inputs or {}
    return D1DrawerPayload(
        chart_token=resp.chart_token,
        drawers=[build_drawer(g, resp, doc, si.get(g)) for g in Graha])
