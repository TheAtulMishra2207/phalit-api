"""
d1_engine.py — Phalit.ai D1 interpretation engine v0.1 (KAR-093 step 4).

Fills the ACCEPTED d1_contract.py (d1-engine-0.1.0) from a certified /chart
payload, and computes the typed doctrine layer the reclassified findings
require. KAR-093 rules honored structurally:

  - Astronomy is NEVER recalculated here. Dignity, longitudes, rāśi, houses'
    signs, retrogression arrive from chart engine 1.1.0 and are consumed
    directly (KAR-080). This module contains NO dignity table and NO
    ephemeris access; a chart missing a dignity is an input error, never a
    trigger to compute one.
  - ONE aspect graph (KAR-081/085): the 13-edge Parāśarī manifest is computed
    once; houses' aspected_by and every downstream consumer read the same
    edges. There is no second aspect computation anywhere.
  - Moon pakṣa resolved ONCE (KAR-086) from the given Sun/Moon longitudes,
    stored with its basis; natural nature of the Moon everywhere derives from
    that single stored value.
  - Natural nature is IMMUTABLE under dignity (KAR-083): an exalted Saturn is
    an exalted natural malefic. Favourability flows only through the
    functional_role layer (KAR-084, BPHS ch.34 by Lagna lordships).
  - House influence (KAR-082): every house's net status is derived from the
    SAME typed evidence list that is exposed for display. Positive-only
    evidence cannot resolve as afflicting; adverse-only cannot resolve as
    supportive — by construction, not by review.
  - Chart-level synthesis is a separate block (KAR-090): per-graha data holds
    only that graha's contribution; nothing chart-level is duplicated into
    graha entries.
  - Dignity display labels are a total mapping over the typed Dignity enum
    (KAR-089): every category has a distinct label; prose generators must
    consume these labels, never score buckets.
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from d1_contract import (
    ASPECT_CASTERS, SPECIAL_DRISHTI, AspectEdge, AspectKind, D1PrepareResponse,
    Dignity, EnginePolicy, FunctionalRole, FunctionalRoleKind, Graha,
    GrahaState, HouseState, NodalAxis, NODES,
)
from d1_functional_roles import (
    functional_roles as _bphs34_roles, FUNCTIONAL_ROLE_POLICY_VERSION,
    FunctionalNature, VerseYogaStatus, MarakaStatus, CellProvenance,
    FunctionalRoleV1,
)

SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra",
         "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
SIGN_LORDS = [Graha.MARS, Graha.VENUS, Graha.MERCURY, Graha.MOON, Graha.SUN,
              Graha.MERCURY, Graha.VENUS, Graha.MARS, Graha.JUPITER,
              Graha.SATURN, Graha.SATURN, Graha.JUPITER]
KENDRAS = {1, 4, 7, 10}
TRIKONAS = {1, 5, 9}          # 1 is both kendra and trikona
DUSTHANA_LORDSHIP = {3, 6, 11}
MARAKA_HOUSES = {2, 7}

# KAR-089: total mapping, every typed dignity gets a DISTINCT display label.
DIGNITY_LABELS: Dict[Dignity, str] = {
    Dignity.EXALTED: "Uchcha (Exalted)",
    Dignity.MOOLATRIKONA: "Mūlatrikoṇa",
    Dignity.OWN: "Sva-rāśi (Own Sign)",
    Dignity.GREAT_FRIEND: "Adhi-Mitra Rāśi (Great Friend)",
    Dignity.FRIEND: "Mitra Rāśi (Friend)",
    Dignity.NEUTRAL: "Sama Rāśi (Neutral)",
    Dignity.ENEMY: "Śatru Rāśi (Enemy)",
    Dignity.GREAT_ENEMY: "Adhi-Śatru Rāśi (Great Enemy)",
    Dignity.DEBILITATED: "Nīca (Debilitated)",
}

class D1EngineError(ValueError):
    """Raised on malformed or incomplete certified-chart input. This engine
    never repairs input by computing astronomy or dignity itself."""

# ── input model: the certified /chart subset this engine consumes ────────────

class ChartGraha(BaseModel):
    sign_index: int = Field(ge=0, le=11)
    degree_in_sign: float = Field(ge=0, lt=30)
    longitude: float = Field(ge=0, lt=360)     # sidereal, from chart engine
    dignity: Optional[Dignity] = None          # REQUIRED for the seven grahas
    retrograde: bool = False
    combust: bool = False
    nakshatra: Optional[str] = None
    nakshatra_pada: Optional[int] = Field(default=None, ge=1, le=4)

class CertifiedChart(BaseModel):
    chart_token: str = Field(min_length=8)
    lagna_sign_index: int = Field(ge=0, le=11)
    lagna_degree: float = Field(ge=0, lt=30)
    grahas: Dict[Graha, ChartGraha]

# ── doctrine models (step-5 payload extension candidates) ────────────────────

class NaturalNature(str, Enum):
    BENEFIC = "natural_benefic"
    MALEFIC = "natural_malefic"

class MoonPaksha(BaseModel):
    """KAR-086: resolved once, stored with basis, consumed everywhere.
    Boundary doctrine (QA step-4): exact pūrṇimā (180°) is BENEFIC and carries
    its own explicit state; exact amāvasyā (0°) is malefic with its own state.
    The bright branch is (0°, 180°]; the dark branch is (180°, 360°) plus 0°."""
    status: Literal["waxing", "full", "waning", "new"]
    sun_moon_separation_deg: float
    natural_nature: NaturalNature
    basis: str

class GrahaNature(BaseModel):
    """KAR-083: natural nature is separate from functional role and dignity,
    and dignity NEVER mutates it."""
    graha: Graha
    natural_nature: NaturalNature
    basis: str

class InfluencePolarity(str, Enum):
    SUPPORTIVE = "supportive"
    CHALLENGING = "challenging"
    MIXED = "mixed"          # genuinely conflicting evidence ONLY
    UNASSESSED = "unassessed"  # no occupation and no dṛṣṭi: absence of data,
                               # never presented as a balanced judgement

class InfluenceEvidence(BaseModel):
    source: Graha
    via: Literal["occupation", "drishti"]
    polarity: InfluencePolarity
    basis: str

class HouseInfluence(BaseModel):
    """KAR-082: net derives from the SAME evidence list shown, invariantly."""
    house: int = Field(ge=1, le=12)
    evidence: List[InfluenceEvidence]
    net: InfluencePolarity

class OrthogonalRole(BaseModel):
    """The versioned functional-role extension, serialized into the payload
    (QA v3 HIGH-1). verse_yoga_status and ownership_yogakaraka are SEPARATE
    fields (QA v3 HIGH-3), and nature_provenance tells the frontend whether a
    cell is verse-grounded or still under review."""
    graha: Graha
    lordships: List[int]
    functional_nature: FunctionalNature
    verse_yoga_status: VerseYogaStatus
    ownership_yogakaraka: bool
    maraka_status: MarakaStatus
    nature_provenance: CellProvenance
    maraka_provenance: Optional[CellProvenance] = None
    yoga_provenance: Optional[CellProvenance] = None
    verse: str
    note: str
    conditional_rules: List[str] = Field(default_factory=list)

class D1Doctrine(BaseModel):
    functional_role_policy_version: str = FUNCTIONAL_ROLE_POLICY_VERSION
    # QA: unknown doctrine must not masquerade as neutral, and RESOLVED doctrine
    # must not be published through the lossy flat field. Two separate flags:
    #   orthogonal_roles_publishable — true only when no cell is review_required
    #   legacy_flat_roles_publishable — ALWAYS false. The flat FunctionalRoleKind
    #     cannot express MIXED nature (Aries Moon/Mars collapse to
    #     functional_neutral) nor conditional vs unconditional māraka (Aries
    #     Mercury/Saturn collapse to an unconditional maraka). It exists for
    #     0.1.0 contract compatibility only; consumers must read
    #     functional_roles_orthogonal.
    functional_roles_status: str = "review_required"
    orthogonal_roles_publishable: bool = False
    legacy_flat_roles_publishable: bool = False
    moon_paksha: MoonPaksha
    natures: List[GrahaNature]
    functional_roles_orthogonal: List[OrthogonalRole]   # the versioned extension, exposed
    house_influences: List[HouseInfluence]
    dignity_labels: Dict[Dignity, str] = Field(default_factory=lambda: dict(DIGNITY_LABELS))
    # KAR-090: chart-level synthesis lives HERE, once. Per-graha payloads must
    # never contain it. Step 5 ports the actual corpus into this block.
    chart_level: Dict[str, str] = Field(default_factory=dict)

# ── computation ──────────────────────────────────────────────────────────────

def resolve_moon_paksha(chart: CertifiedChart) -> MoonPaksha:
    sun = chart.grahas[Graha.SUN].longitude
    moon = chart.grahas[Graha.MOON].longitude
    sep = (moon - sun) % 360.0
    if sep == 0.0:
        status, nature, phase = "new", NaturalNature.MALEFIC, "exact amāvasyā (new Moon) — darkest, malefic"
    elif sep < 180.0:
        status, nature, phase = "waxing", NaturalNature.BENEFIC, "śukla pakṣa — waxing Moon is a natural benefic"
    elif sep == 180.0:
        status, nature, phase = "full", NaturalNature.BENEFIC, "exact pūrṇimā (full Moon) — brightest, benefic"
    else:
        status, nature, phase = "waning", NaturalNature.MALEFIC, "kṛṣṇa pakṣa — waning Moon is a natural malefic"
    return MoonPaksha(
        status=status,
        sun_moon_separation_deg=round(sep, 4),
        natural_nature=nature,
        basis=f"Moon−Sun separation {sep:.2f}° → {phase} (BPHS ch.3)",
    )

def resolve_natures(chart: CertifiedChart, paksha: MoonPaksha,
                    house_of: Dict[Graha, int]) -> List[GrahaNature]:
    fixed = {
        Graha.SUN: NaturalNature.MALEFIC, Graha.MARS: NaturalNature.MALEFIC,
        Graha.SATURN: NaturalNature.MALEFIC, Graha.RAHU: NaturalNature.MALEFIC,
        Graha.KETU: NaturalNature.MALEFIC,
        Graha.JUPITER: NaturalNature.BENEFIC, Graha.VENUS: NaturalNature.BENEFIC,
    }
    out: List[GrahaNature] = []
    for g in Graha:
        if g == Graha.MOON:
            out.append(GrahaNature(graha=g, natural_nature=paksha.natural_nature,
                                   basis="from the single stored pakṣa resolution (KAR-086)"))
        elif g == Graha.MERCURY:
            mh = house_of[Graha.MERCURY]
            malefic_conj = [m for m in (Graha.SUN, Graha.MARS, Graha.SATURN,
                                        Graha.RAHU, Graha.KETU)
                            if house_of[m] == mh]
            if malefic_conj:
                out.append(GrahaNature(graha=g, natural_nature=NaturalNature.MALEFIC,
                                       basis="Mercury joined by malefic(s) "
                                             + ", ".join(m.value for m in malefic_conj)
                                             + " adopts malefic conduct (BPHS ch.3)"))
            else:
                out.append(GrahaNature(graha=g, natural_nature=NaturalNature.BENEFIC,
                                       basis="Mercury unafflicted by malefic association (BPHS ch.3)"))
        else:
            out.append(GrahaNature(graha=g, natural_nature=fixed[g],
                                   basis="fixed natural nature (BPHS ch.3); dignity never alters it (KAR-083)"))
    return out

# ── KAR-084 · functional roles come from the versioned BPHS-34 module ─────────
# parashari-functional-role-1.0 (d1_functional_roles.py) is the source of truth:
# orthogonal (functional_nature, yoga_status, maraka_status) transcribed from the
# verse text. For the ACCEPTED 0.1.0 contract we still emit the flat
# FunctionalRole; the orthogonal role rides in the doctrine block as the
# versioned extension. The flat mapping is lossy BY DESIGN and documented.
def _flatten_role(r) -> FunctionalRoleKind:
    if r.ownership_yogakaraka:
        return FunctionalRoleKind.YOGAKARAKA
    if r.maraka_status in (MarakaStatus.MARAKA, MarakaStatus.PRIMARY_KILLER, MarakaStatus.QUALIFIED) \
            and r.functional_nature in (FunctionalNature.MALEFIC, FunctionalNature.NEUTRAL):
        return FunctionalRoleKind.MARAKA
    if r.functional_nature == FunctionalNature.BENEFIC:
        return FunctionalRoleKind.FUNCTIONAL_BENEFIC
    if r.functional_nature == FunctionalNature.MALEFIC:
        return FunctionalRoleKind.FUNCTIONAL_MALEFIC
    return FunctionalRoleKind.FUNCTIONAL_NEUTRAL   # neutral and mixed both map here

def resolve_functional_roles(lagna_sign_index: int) -> List[FunctionalRole]:
    """Flat contract roles (0.1.0) derived from the versioned orthogonal source."""
    out: List[FunctionalRole] = []
    for r in _bphs34_roles(lagna_sign_index):
        out.append(FunctionalRole(
            graha=r.graha, lordships=r.lordships, role=_flatten_role(r),
            basis=f"{r.verse}: {r.note}"))
    for g in NODES:
        out.append(FunctionalRole(
            graha=g, lordships=[], role=FunctionalRoleKind.NODE_AXIS,
            basis="nodes own no rāśi; nature flows through axis, dispositor and association (locked ruling)"))
    return out

def build_aspect_manifest(house_of: Dict[Graha, int],
                          occupants: Dict[int, List[Graha]]) -> List[AspectEdge]:
    """The ONE canonical aspect graph (KAR-081/085). Exactly 13 Parāśarī
    edges; every consumer reads these, nothing recomputes."""
    kindmap = {7: AspectKind.SEVENTH, 4: AspectKind.FOURTH, 8: AspectKind.EIGHTH,
               5: AspectKind.FIFTH, 9: AspectKind.NINTH, 3: AspectKind.THIRD,
               10: AspectKind.TENTH}
    edges: List[AspectEdge] = []
    for caster in ASPECT_CASTERS:
        ch = house_of[caster]
        for off in [7, *SPECIAL_DRISHTI.get(caster, ())]:
            th = (ch - 1 + off - 1) % 12 + 1
            edges.append(AspectEdge(source=caster, kind=kindmap[off],
                                    target_house=th,
                                    target_grahas=sorted(occupants.get(th, []),
                                                         key=lambda g: g.value)))
    return edges

def _polarity_of(source: Graha, natures: Dict[Graha, NaturalNature],
                 func: Dict[Graha, object]) -> tuple:
    """Complete truth table over (natural_nature, functional_nature, has_support,
    has_affliction). Every combination of the four FunctionalNature values is
    covered — no fall-through (QA v3 CRITICAL-2). Dignity plays no part (KAR-083).
    An unreviewed (review_required) functional nature yields UNASSESSED, never a
    fabricated polarity."""
    nat = natures[source]                       # NaturalNature.BENEFIC / MALEFIC
    fr = func[source]
    fn = fr.functional_nature                   # benefic / malefic / neutral / mixed
    prov = getattr(fr, "nature_provenance", None)
    tag = (f"nat={nat.value.split('_')[-1]},fn={fn.value},"
           f"yoga={fr.verse_yoga_status.value},yk={fr.ownership_yogakaraka},"
           f"maraka={fr.maraka_status.value}")

    # Honesty gate: if the functional nature is unconfirmed, do not assert a
    # polarity from it — the house is UNASSESSED on this source.
    if prov == CellProvenance.REVIEW_REQUIRED:
        return InfluencePolarity.UNASSESSED, f"{source.value}: functional nature under review — {tag}"

    has_support = (fn == FunctionalNature.BENEFIC
                   or fr.verse_yoga_status == VerseYogaStatus.YOGA_AGENT
                   or fr.ownership_yogakaraka)
    has_affliction = (fn == FunctionalNature.MALEFIC
                      or fr.maraka_status != MarakaStatus.NONE)

    # Four functional-nature branches, each fully specified.
    if fn == FunctionalNature.MIXED:
        return InfluencePolarity.MIXED, f"{source.value}: functionally mixed — {tag}"
    if fn == FunctionalNature.NEUTRAL:
        if has_support and has_affliction:
            return InfluencePolarity.MIXED, f"{source.value}: neutral with both currents — {tag}"
        if has_affliction:
            return InfluencePolarity.CHALLENGING, f"{source.value}: neutral but māraka — {tag}"
        if has_support:
            return InfluencePolarity.SUPPORTIVE, f"{source.value}: neutral carrying a yoga — {tag}"
        return InfluencePolarity.UNASSESSED, f"{source.value}: functionally neutral, no other current — {tag}"
    if fn == FunctionalNature.BENEFIC:
        if has_affliction:
            return InfluencePolarity.MIXED, f"{source.value}: benefic but afflicting by role — {tag}"
        return InfluencePolarity.SUPPORTIVE, f"{source.value}: benefic — {tag}"
    # fn == MALEFIC
    if has_support:
        return InfluencePolarity.MIXED, f"{source.value}: malefic carrying support — {tag}"
    return InfluencePolarity.CHALLENGING, f"{source.value}: malefic — {tag}"

def build_house_influences(occupants: Dict[int, List[Graha]],
                           edges: List[AspectEdge],
                           natures: Dict[Graha, NaturalNature],
                           func: Dict[Graha, object]) -> List[HouseInfluence]:
    out: List[HouseInfluence] = []
    for h in range(1, 13):
        ev: List[InfluenceEvidence] = []
        for g in occupants.get(h, []):
            pol, why = _polarity_of(g, natures, func)
            ev.append(InfluenceEvidence(source=g, via="occupation", polarity=pol, basis=why))
        for e in edges:
            if e.target_house == h:
                pol, why = _polarity_of(e.source, natures, func)
                ev.append(InfluenceEvidence(source=e.source, via="drishti", polarity=pol,
                                            basis=why + f" ({e.kind.value} dṛṣṭi)"))
        # KAR-082 invariant BY CONSTRUCTION: net is a pure function of the
        # evidence polarities above — the same list the UI will display.
        # Aggregate over ASSESSED evidence only: an unassessed source contributes
        # no polarity, so it neither creates nor blocks a net (QA). A house with
        # only unassessed evidence stays UNASSESSED; otherwise the net is the
        # combination of the assessed polarities.
        assessed = {x.polarity for x in ev if x.polarity != InfluencePolarity.UNASSESSED}
        if not assessed:
            net = InfluencePolarity.UNASSESSED
        elif assessed == {InfluencePolarity.SUPPORTIVE}:
            net = InfluencePolarity.SUPPORTIVE
        elif assessed == {InfluencePolarity.CHALLENGING}:
            net = InfluencePolarity.CHALLENGING
        else:
            net = InfluencePolarity.MIXED
        out.append(HouseInfluence(house=h, evidence=ev, net=net))
    return out

def compute_d1(chart: CertifiedChart) -> tuple:
    """Returns (D1PrepareResponse, D1Doctrine). Raises D1EngineError on
    incomplete certified input — this engine never fills gaps by computing."""
    missing = [g.value for g in Graha if g not in chart.grahas]
    if missing:
        raise D1EngineError(f"certified chart missing grahas: {missing}")
    for g in ASPECT_CASTERS:
        if chart.grahas[g].dignity is None:
            raise D1EngineError(
                f"certified chart supplies no dignity for {g.value}; this engine "
                f"does not compute dignity (KAR-080/KAR-093: astronomy and dignity "
                f"come from chart engine 1.1.0 only)")

    lagna_idx = chart.lagna_sign_index
    def house_from_sign(si: int) -> int: return (si - lagna_idx) % 12 + 1
    house_of = {g: house_from_sign(cg.sign_index) for g, cg in chart.grahas.items()}
    occupants: Dict[int, List[Graha]] = {}
    for g, h in house_of.items(): occupants.setdefault(h, []).append(g)

    paksha = resolve_moon_paksha(chart)
    natures_list = resolve_natures(chart, paksha, house_of)
    natures = {n.graha: n.natural_nature for n in natures_list}
    roles_list = resolve_functional_roles(lagna_idx)          # flat, for the 0.1.0 contract
    func = {r.graha: r for r in _bphs34_roles(lagna_idx)}     # orthogonal, for polarity + doctrine
    # Nodes cast no dṛṣṭi but DO occupy houses, so they need a polarity role.
    # They carry natural maleficence with no functional-lordship doctrine.
    from d1_functional_roles import FunctionalRoleV1 as _FR
    for _n in NODES:
        func[_n] = _FR(graha=_n, lordships=[], functional_nature=FunctionalNature.MALEFIC,
                       verse_yoga_status=VerseYogaStatus.NONE, ownership_yogakaraka=False,
                       maraka_status=MarakaStatus.NONE, nature_provenance=CellProvenance.DERIVED_GENERAL_RULE,
                       verse="BPHS 34 (nodes)", note="node: natural malefic, no rāśi lordship")
    edges = build_aspect_manifest(house_of, occupants)

    aspected_by: Dict[int, set] = {}
    for e in edges: aspected_by.setdefault(e.target_house, set()).add(e.source)

    grahas = []
    for g in Graha:
        cg = chart.grahas[g]
        grahas.append(GrahaState(
            graha=g, sign_index=cg.sign_index, sign=SIGNS[cg.sign_index],
            degree_in_sign=cg.degree_in_sign, house=house_of[g],
            dignity=cg.dignity,        # consumed, never computed (KAR-080)
            retrograde=cg.retrograde, combust=cg.combust,
            nakshatra=cg.nakshatra, nakshatra_pada=cg.nakshatra_pada,
            dispositor=SIGN_LORDS[cg.sign_index],
        ))
    houses = [HouseState(
        house=h, sign_index=(lagna_idx + h - 1) % 12,
        sign=SIGNS[(lagna_idx + h - 1) % 12],
        lord=SIGN_LORDS[(lagna_idx + h - 1) % 12],
        occupants=sorted(occupants.get(h, []), key=lambda g: g.value),
        aspected_by=sorted(aspected_by.get(h, set()), key=lambda g: g.value),
    ) for h in range(1, 13)]

    rahu_h, ketu_h = house_of[Graha.RAHU], house_of[Graha.KETU]
    response = D1PrepareResponse(
        chart_token=chart.chart_token, policy=EnginePolicy(),
        lagna_sign_index=lagna_idx, lagna_sign=SIGNS[lagna_idx],
        lagna_degree=chart.lagna_degree,
        grahas=grahas, houses=houses, aspects=edges,
        functional_roles=roles_list,
        nodal_axis=NodalAxis(
            rahu_house=rahu_h, ketu_house=ketu_h,
            rahu_sign=SIGNS[chart.grahas[Graha.RAHU].sign_index],
            ketu_sign=SIGNS[chart.grahas[Graha.KETU].sign_index],
            rahu_dispositor=SIGN_LORDS[chart.grahas[Graha.RAHU].sign_index],
            ketu_dispositor=SIGN_LORDS[chart.grahas[Graha.KETU].sign_index]),
        generated_at=datetime.now(timezone.utc),
    )
    orthogonal = [OrthogonalRole(
        graha=r.graha, lordships=r.lordships, functional_nature=r.functional_nature,
        verse_yoga_status=r.verse_yoga_status, ownership_yogakaraka=r.ownership_yogakaraka,
        maraka_status=r.maraka_status, nature_provenance=r.nature_provenance,
        maraka_provenance=r.maraka_provenance, yoga_provenance=r.yoga_provenance,
        verse=r.verse, note=r.note, conditional_rules=r.conditional_rules)
        for r in _bphs34_roles(lagna_idx)]
    any_review = any(o.nature_provenance == CellProvenance.REVIEW_REQUIRED for o in orthogonal)
    doctrine = D1Doctrine(
        functional_roles_status=("review_required" if any_review else "published"),
        orthogonal_roles_publishable=(not any_review),
        legacy_flat_roles_publishable=False,   # invariant: never publishable
        moon_paksha=paksha, natures=natures_list,
        functional_roles_orthogonal=orthogonal,
        house_influences=build_house_influences(occupants, edges, natures, func),
        chart_level={},   # step 5: stature/complexion synthesis ports here, ONCE (KAR-090)
    )
    return response, doctrine
