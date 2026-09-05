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
    Varga, VARGA_ASPECT_POLICY,
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
    # VARGA PORT. One certified snapshot carries every view. longitude stays the
    # true sidereal longitude in all of them, which is what keeps Moon pakṣa
    # anchored to the birth moment by construction instead of by convention.
    # The engine SELECTS a view; it never computes the varga mapping, because
    # astronomy and dignity come from chart engine 1.1.0 only (KAR-080).
    varga_sign_index: Optional[int] = Field(default=None, ge=0, le=11)
    varga_dignity: Optional[Dignity] = None
    vargottama: Optional[bool] = None   # certified, never derived here
    sign_index: int = Field(ge=0, le=11)
    degree_in_sign: float = Field(ge=0, lt=30)
    longitude: float = Field(ge=0, lt=360)     # sidereal, from chart engine
    dignity: Optional[Dignity] = None          # REQUIRED for the seven grahas
    retrograde: bool = False
    combust: bool = False
    nakshatra: Optional[str] = None
    nakshatra_pada: Optional[int] = Field(default=None, ge=1, le=4)

class _VargaView:
    """The (sign_index, dignity, lagna) triple a computation actually reads."""
    __slots__ = ("sign_of", "dignity_of", "lagna_idx", "varga")
    def __init__(self, sign_of, dignity_of, lagna_idx, varga):
        self.sign_of, self.dignity_of = sign_of, dignity_of
        self.lagna_idx, self.varga = lagna_idx, varga

class CertifiedChart(BaseModel):
    chart_token: str = Field(min_length=8)
    lagna_sign_index: int = Field(ge=0, le=11)   # BIRTH lagna, always
    lagna_degree: float = Field(ge=0, lt=30)
    grahas: Dict[Graha, ChartGraha]
    # VARGA PORT. Supplied by chart engine 1.1.0 alongside the D1 view; the
    # snapshot, chart_token, session, resolver and adapter are unchanged, this
    # is one more certified field on the object they already carry.
    varga_lagna_sign_index: Optional[int] = Field(default=None, ge=0, le=11)

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
    NOT_APPLICABLE = "not_applicable"
    # DOCTRINE SAYS THERE IS NOTHING TO RESOLVE. Distinct from UNASSESSED, which
    # means the doctrine could not be resolved. Collapsing the two repeats the
    # samah / sama-phala error already on record. Under varga_aspect_policy=
    # "none" the dṛṣṭi dimension is not-applicable, and that is a positive fact
    # about the chart, not missing data. It is EXCLUDED from net aggregation
    # rather than counted as zero, and the drawer renders it as an explicit
    # marked state rather than an empty block that reads as neutral.

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
    # Declared so the frontend has a path to bind and P3 sees a marked leaf
    # instead of an unmarked one. "not_applicable" is doctrine, not absence.
    drishti_applicability: Literal["applicable", "not_applicable"] = "applicable"

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
    # D12-005 · the relation evidence FR-001A requires. Optional so every
    # existing consumer and fixture is unaffected; populated by compute_d1.
    relation_evidence: Optional["RelationEvidence"] = None
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

# ─────────────────────────────────────────────────────────────────────────────
# D12-005 · RELATION EVIDENCE (upstream authority, published once)
#
# FR-001A forbids D12 from inventing functional-malefic status, Mercury's
# natural nature, Moon pakṣa, Parāśari aspect authority, or benefic mitigation.
# The first four already live here. Only benefic mitigation was absent, and the
# ruling is explicit that D12 must NOT grow a private formula for it — so the
# relation evidence is published HERE, once, from the authorities that already
# exist, and D12 classifies from it.
#
# TWO DISTINCT RELATIONS, never conflated:
#   * CONJUNCTION is measured directly as longitudinal separation. It is not
#     graha-dṛṣṭi and is never labelled as such.
#   * ASPECT orb is LAYERED ON the canonical manifest. This code does not decide
#     which aspects exist — build_aspect_manifest already did, and it remains the
#     only place that answers that question. Here we only measure how exact an
#     aspect the manifest already asserts happens to be.
# ─────────────────────────────────────────────────────────────────────────────

# Degrees of separation each Parāśarī dṛṣṭi is exact at, keyed by house offset.
_ASPECT_EXACT_DEG = {7: 180.0, 4: 90.0, 8: 210.0, 5: 120.0, 9: 240.0,
                     3: 60.0, 10: 270.0}

TIGHT_CONJUNCTION_ORB = 3.0        # functional-malefic and benefic mitigation
TIGHT_NODE_ORB = 2.0               # Rahu/Ketu, FR-001 heavy occupancy
TIGHT_ASPECT_ORB = 3.0             # full Parāśari dṛṣṭi


def _separation(a: float, b: float) -> float:
    """Shortest angular separation in [0, 180]."""
    d = abs(a - b) % 360.0
    return d if d <= 180.0 else 360.0 - d


def _directed_arc(frm: float, to: float) -> float:
    """Zodiacal arc from `frm` to `to`, in [0, 360)."""
    return (to - frm) % 360.0


class RelationEdge(BaseModel):
    """One measured relation between a source and a target graha."""
    source: Graha
    target: Graha
    relation: Literal["conjunction", "drishti"]
    aspect_kind: Optional[AspectKind] = None      # drishti only
    orb_deg: float
    within_orb: bool
    basis: str


class TargetRelationEvidence(BaseModel):
    """Everything a D12 consumer needs about ONE target graha, so it can
    classify without recreating any upstream doctrine."""
    target: Graha
    functional_malefic_conjunctions: List[RelationEdge] = Field(default_factory=list)
    functional_malefic_drishti: List[RelationEdge] = Field(default_factory=list)
    node_conjunctions: List[RelationEdge] = Field(default_factory=list)
    benefic_mitigations: List[RelationEdge] = Field(default_factory=list)
    tight_functional_malefic_affliction: bool = False
    tight_node_conjunction: bool = False
    approved_benefic_mitigation: bool = False
    # Three-valued at the consumer: a target whose functional roles are under
    # review yields UNKNOWN, never a fabricated FALSE.
    functional_authority_resolved: bool = True


class RelationEvidence(BaseModel):
    """The published block. `mitigators` records WHICH grahas qualified and why,
    so a consumer never has to re-derive Mercury's nature or the Moon's pakṣa."""
    conjunction_orb_deg: float = TIGHT_CONJUNCTION_ORB
    node_conjunction_orb_deg: float = TIGHT_NODE_ORB
    aspect_orb_deg: float = TIGHT_ASPECT_ORB
    approved_mitigators: List[Graha]
    mitigator_basis: Dict[Graha, str]
    functional_malefics: List[Graha]
    functional_authority_resolved: bool
    targets: Dict[Graha, TargetRelationEvidence]


def approved_benefic_mitigators(natures: Dict[Graha, NaturalNature],
                                paksha: MoonPaksha) -> tuple:
    """Exactly Jupiter, Venus, Mercury-when-benefic, Moon-when-bright.

    Mercury and the Moon are decided by the MASTER authorities above — the same
    `resolve_natures` and `resolve_moon_paksha` every other consumer reads. There
    is deliberately no local Mercury rule and no local pakṣa rule here.
    """
    approved: List[Graha] = [Graha.JUPITER, Graha.VENUS]
    basis: Dict[Graha, str] = {
        Graha.JUPITER: "fixed natural benefic (BPHS ch.3)",
        Graha.VENUS: "fixed natural benefic (BPHS ch.3)",
    }
    if natures.get(Graha.MERCURY) == NaturalNature.BENEFIC:
        approved.append(Graha.MERCURY)
        basis[Graha.MERCURY] = ("master natural-nature authority reports Mercury "
                                "benefic; no D12-local Mercury rule")
    else:
        basis[Graha.MERCURY] = ("master natural-nature authority reports Mercury "
                                "malefic by association; not a mitigator")
    if paksha.natural_nature == NaturalNature.BENEFIC:
        approved.append(Graha.MOON)
        basis[Graha.MOON] = (f"master pakṣa authority reports {paksha.status}; "
                             f"bright Moon is a mitigator")
    else:
        basis[Graha.MOON] = (f"master pakṣa authority reports {paksha.status}; "
                             f"dark Moon is not a mitigator")
    return tuple(approved), basis


def build_relation_evidence(chart: CertifiedChart,
                            natures: Dict[Graha, NaturalNature],
                            paksha: MoonPaksha,
                            roles: Dict[Graha, object],
                            aspect_edges: List[AspectEdge],
                            house_of: Dict[Graha, int]) -> RelationEvidence:
    """Measure, for every graha, the four relations FR-001A needs.

    FUNCTIONAL malefic status is read from the birth-Lagna anchored orthogonal
    classification and nothing else — not natural malefic, not dignity, not
    māraka, and never re-decided from a varga Lagna.
    """
    lon = {g: cg.longitude for g, cg in chart.grahas.items()}

    resolved = all(getattr(r, "nature_provenance", None) is not CellProvenance.REVIEW_REQUIRED
                   for r in roles.values() if getattr(r, "lordships", None))

    # CORR-01 · FUNCTIONAL malefic status comes ONLY from the genuine
    # primary-Lagna BPHS-34 authority. compute_d1 additionally synthesises a
    # house-polarity role for Rahu and Ketu so they can colour a house they
    # occupy — that synthetic role carries no rāśi lordship and no Founder-
    # ratified functional classification, and it must never be read as one here.
    #
    # The nodes remain natural malefics and remain fully available through
    # node_conjunctions. What they are NOT is functional malefics, and a tight
    # conjunction with a node must therefore not be reported as a
    # functional-malefic affliction.
    func_malefics = [g for g, r in roles.items()
                     if g not in (Graha.RAHU, Graha.KETU)
                     and getattr(r, "lordships", None)
                     and getattr(r, "functional_nature", None) == FunctionalNature.MALEFIC]
    mitigators, mit_basis = approved_benefic_mitigators(natures, paksha)

    # The manifest is the ONLY authority on which aspects exist. Index it by
    # (source, target graha) so orb measurement can never invent an edge.
    offset_of = {AspectKind.SEVENTH: 7, AspectKind.FOURTH: 4, AspectKind.EIGHTH: 8,
                 AspectKind.FIFTH: 5, AspectKind.NINTH: 9, AspectKind.THIRD: 3,
                 AspectKind.TENTH: 10}
    asserted: List[tuple] = []
    for e in aspect_edges:
        for tgt in e.target_grahas:
            asserted.append((e.source, tgt, e.kind))

    targets: Dict[Graha, TargetRelationEvidence] = {}
    for target in Graha:
        ev = TargetRelationEvidence(target=target,
                                    functional_authority_resolved=resolved)
        for source in Graha:
            if source == target:
                continue
            sep = _separation(lon[source], lon[target])
            if source in func_malefics:
                if sep <= TIGHT_CONJUNCTION_ORB:
                    ev.functional_malefic_conjunctions.append(RelationEdge(
                        source=source, target=target, relation="conjunction",
                        orb_deg=round(sep, 4), within_orb=True,
                        basis=f"functional malefic within {TIGHT_CONJUNCTION_ORB}° "
                              f"longitudinal separation"))
            if source in (Graha.RAHU, Graha.KETU) and sep <= TIGHT_NODE_ORB:
                ev.node_conjunctions.append(RelationEdge(
                    source=source, target=target, relation="conjunction",
                    orb_deg=round(sep, 4), within_orb=True,
                    basis=f"node within {TIGHT_NODE_ORB}° longitudinal separation"))
            if source in mitigators and sep <= TIGHT_CONJUNCTION_ORB:
                ev.benefic_mitigations.append(RelationEdge(
                    source=source, target=target, relation="conjunction",
                    orb_deg=round(sep, 4), within_orb=True,
                    basis=f"approved mitigator: {mit_basis[source]}"))

        # Aspect orbs, measured only where the canonical manifest already
        # asserts the aspect. No new aspect can be born here.
        for source, tgt, kind in asserted:
            if tgt != target or source == target:
                continue
            exact = _ASPECT_EXACT_DEG[offset_of[kind]]
            orb = abs(_directed_arc(lon[source], lon[target]) - exact)
            orb = min(orb, 360.0 - orb)
            edge = RelationEdge(source=source, target=target, relation="drishti",
                                aspect_kind=kind, orb_deg=round(orb, 4),
                                within_orb=orb <= TIGHT_ASPECT_ORB,
                                basis=f"orb on the canonical {kind.value} dṛṣṭi "
                                      f"asserted by build_aspect_manifest")
            if source in func_malefics and edge.within_orb:
                ev.functional_malefic_drishti.append(edge)
            if source in mitigators and edge.within_orb:
                ev.benefic_mitigations.append(edge)

        ev.tight_functional_malefic_affliction = bool(
            ev.functional_malefic_conjunctions or ev.functional_malefic_drishti)
        ev.tight_node_conjunction = bool(ev.node_conjunctions)
        ev.approved_benefic_mitigation = bool(ev.benefic_mitigations)
        targets[target] = ev

    return RelationEvidence(approved_mitigators=list(mitigators),
                            mitigator_basis=mit_basis,
                            functional_malefics=sorted(func_malefics, key=lambda g: g.value),
                            functional_authority_resolved=resolved,
                            targets=targets)


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
                           func: Dict[Graha, object],
                           drishti_applicable: bool = True) -> List[HouseInfluence]:
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
        assessed = {x.polarity for x in ev
                    if x.polarity not in (InfluencePolarity.UNASSESSED,
                                          InfluencePolarity.NOT_APPLICABLE)}
        if not assessed:
            net = InfluencePolarity.UNASSESSED
        elif assessed == {InfluencePolarity.SUPPORTIVE}:
            net = InfluencePolarity.SUPPORTIVE
        elif assessed == {InfluencePolarity.CHALLENGING}:
            net = InfluencePolarity.CHALLENGING
        else:
            net = InfluencePolarity.MIXED
        out.append(HouseInfluence(
            house=h, evidence=ev, net=net,
            drishti_applicability=("applicable" if drishti_applicable else "not_applicable")))
    return out

def compute_d1(chart: CertifiedChart, varga: Varga = Varga.D1) -> tuple:
    """Returns (response, doctrine) for the requested varga.

    VARGA PORT. The whole stack is one computation over a selected view. Houses,
    dignity and occupancy read the varga view; three things stay anchored to D1
    and must NEVER flow through:

      functional roles  BPHS 34 nature is a rāśi-lordship property that does not
                        change across vargas (founder ruling). Always read from
                        the BIRTH lagna, and the anchor is published as
                        birth_lagna_sign_index so the claim is checkable.
      Moon pakṣa        a property of the birth moment. Computed from true
                        sidereal longitudes, which every view shares, so it is
                        anchored by construction and cannot silently drift.
      natural nature    a property of the graha, not of the chart.

    Graha-dṛṣṭi is governed by varga_aspect_policy. Under "none" the manifest is
    empty, no house records an aspecting graha, and the dṛṣṭi dimension is marked
    NOT_APPLICABLE rather than left blank.
    """
    missing = [g.value for g in Graha if g not in chart.grahas]
    if missing:
        raise D1EngineError(f"certified chart missing grahas: {missing}")
    for g in ASPECT_CASTERS:
        if chart.grahas[g].dignity is None:
            raise D1EngineError(
                f"certified chart supplies no dignity for {g.value}; this engine "
                f"does not compute dignity (KAR-080/KAR-093: astronomy and dignity "
                f"come from chart engine 1.1.0 only)")

    birth_lagna_idx = chart.lagna_sign_index
    if varga is Varga.D1:
        lagna_idx = birth_lagna_idx
        sign_of = {g: cg.sign_index for g, cg in chart.grahas.items()}
        dignity_of = {g: cg.dignity for g, cg in chart.grahas.items()}
    else:
        if chart.varga_lagna_sign_index is None:
            raise D1EngineError(
                f"{varga.value} requested but the certified chart carries no "
                f"varga_lagna_sign_index; this engine does not compute the varga "
                f"mapping (KAR-080: astronomy comes from chart engine 1.1.0)")
        missing_view = [g.value for g, cg in chart.grahas.items()
                        if cg.varga_sign_index is None]
        if missing_view:
            raise D1EngineError(
                f"{varga.value} requested but no varga_sign_index for: {missing_view}")
        lagna_idx = chart.varga_lagna_sign_index
        sign_of = {g: cg.varga_sign_index for g, cg in chart.grahas.items()}
        dignity_of = {g: cg.varga_dignity for g, cg in chart.grahas.items()}
        for g in ASPECT_CASTERS:
            if dignity_of[g] is None:
                raise D1EngineError(
                    f"certified chart supplies no varga_dignity for {g.value} in "
                    f"{varga.value}; this engine does not compute dignity")

    aspect_policy = VARGA_ASPECT_POLICY[varga]
    drishti_applicable = aspect_policy == "parashari_full"

    def house_from_sign(si: int) -> int: return (si - lagna_idx) % 12 + 1
    house_of = {g: house_from_sign(sign_of[g]) for g in chart.grahas}
    occupants: Dict[int, List[Graha]] = {}
    for g, h in house_of.items(): occupants.setdefault(h, []).append(g)

    paksha = resolve_moon_paksha(chart)
    natures_list = resolve_natures(chart, paksha, house_of)
    natures = {n.graha: n.natural_nature for n in natures_list}
    # BIRTH lagna, in every varga. This is the one place the varga parameter is
    # deliberately withheld (founder ruling: functional_role_lagna_anchor).
    roles_list = resolve_functional_roles(birth_lagna_idx)
    func = {r.graha: r for r in _bphs34_roles(birth_lagna_idx)}
    # Nodes cast no dṛṣṭi but DO occupy houses, so they need a polarity role.
    # They carry natural maleficence with no functional-lordship doctrine.
    from d1_functional_roles import FunctionalRoleV1 as _FR
    for _n in NODES:
        func[_n] = _FR(graha=_n, lordships=[], functional_nature=FunctionalNature.MALEFIC,
                       verse_yoga_status=VerseYogaStatus.NONE, ownership_yogakaraka=False,
                       maraka_status=MarakaStatus.NONE, nature_provenance=CellProvenance.DERIVED_GENERAL_RULE,
                       verse="BPHS 34 (nodes)", note="node: natural malefic, no rāśi lordship")
    edges = build_aspect_manifest(house_of, occupants) if drishti_applicable else []

    aspected_by: Dict[int, set] = {}
    for e in edges: aspected_by.setdefault(e.target_house, set()).add(e.source)

    grahas = []
    for g in Graha:
        cg = chart.grahas[g]
        grahas.append(GrahaState(
            graha=g, sign_index=sign_of[g], sign=SIGNS[sign_of[g]],
            degree_in_sign=cg.degree_in_sign, house=house_of[g],
            dignity=dignity_of[g],     # consumed, never computed (KAR-080)
            birth_dignity=cg.dignity,  # the D1 view, in every varga
            vargottama=cg.vargottama,  # consumed, never computed (KAR-080)
            retrograde=cg.retrograde, combust=cg.combust,
            nakshatra=cg.nakshatra, nakshatra_pada=cg.nakshatra_pada,
            dispositor=SIGN_LORDS[sign_of[g]],
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
        chart_token=chart.chart_token,
        policy=EnginePolicy(varga=varga, varga_aspect_policy=aspect_policy),
        lagna_sign_index=lagna_idx, lagna_sign=SIGNS[lagna_idx],
        birth_lagna_sign_index=birth_lagna_idx,
        lagna_degree=chart.lagna_degree,
        grahas=grahas, houses=houses, aspects=edges,
        functional_roles=roles_list,
        nodal_axis=NodalAxis(
            rahu_house=rahu_h, ketu_house=ketu_h,
            rahu_sign=SIGNS[sign_of[Graha.RAHU]],
            ketu_sign=SIGNS[sign_of[Graha.KETU]],
            rahu_dispositor=SIGN_LORDS[sign_of[Graha.RAHU]],
            ketu_dispositor=SIGN_LORDS[sign_of[Graha.KETU]]),
        generated_at=datetime.now(timezone.utc),
    )
    orthogonal = [OrthogonalRole(
        graha=r.graha, lordships=r.lordships, functional_nature=r.functional_nature,
        verse_yoga_status=r.verse_yoga_status, ownership_yogakaraka=r.ownership_yogakaraka,
        maraka_status=r.maraka_status, nature_provenance=r.nature_provenance,
        maraka_provenance=r.maraka_provenance, yoga_provenance=r.yoga_provenance,
        verse=r.verse, note=r.note, conditional_rules=r.conditional_rules)
        for r in _bphs34_roles(birth_lagna_idx)]
    any_review = any(o.nature_provenance == CellProvenance.REVIEW_REQUIRED for o in orthogonal)
    doctrine = D1Doctrine(
        functional_roles_status=("review_required" if any_review else "published"),
        orthogonal_roles_publishable=(not any_review),
        legacy_flat_roles_publishable=False,   # invariant: never publishable
        moon_paksha=paksha, natures=natures_list,
        functional_roles_orthogonal=orthogonal,
        house_influences=build_house_influences(occupants, edges, natures, func,
                                                drishti_applicable=drishti_applicable),
        # D12-005 · published once, here, from the authorities already resolved
        # above. Nothing downstream recreates natural nature, functional nature,
        # Moon pakṣa or the aspect graph.
        relation_evidence=build_relation_evidence(
            chart=chart, natures=natures, paksha=paksha, roles=func,
            aspect_edges=edges, house_of=house_of),
        chart_level={},   # step 5: stature/complexion synthesis ports here, ONCE (KAR-090)
    )
    return response, doctrine


# D12-005 · D1Doctrine forward-references RelationEvidence, defined below it.
D1Doctrine.update_forward_refs()
