"""d12_crosschart.py — FR-001 classification and FR-004 release topology.

D12-005. Two independent machines, deliberately not entangled:

  * FR-001 classifies a target as Supported / Loaded / Redirected / UNKNOWN,
    with precedence strictly Loaded > Supported > Redirected and no score.
  * FR-004 decides Ketu release dominance, and is evaluated INDEPENDENTLY of
    tension selection so the tension waterfall consumes a finished result
    rather than re-deriving one.

Nothing here recomputes a D12 placement, and nothing here invents a natural
nature, functional nature, Moon pakṣa, aspect relation or benefic mitigation:
those arrive as published `d1_engine.RelationEvidence` and are consumed.

BOUNDARY (§13): nothing in this module says or implies that D12 cancels D10,
overrides vocation, removes professional duty or defeats public standing. Ketu
dominance is a D12 pull and is named as one.
"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Sequence

from d12_crosschart_contract import (
    CROSSCHART_CONTRACT_VERSION, Classification, CrossChart, HANDSHAKE_SOURCE_HOUSES,
    KetuFact, LagnaAxisEvidence, LoadedBasis, LuminaryFact, ReleaseTopology,
    StructuralClassification, SupportedBasis, Tri, UpstreamEvidence,
)

__all__ = ["D12CrossChartError", "STRUCTURAL_MALEFICS", "KETU_RELEASE_HOUSES",
           "d12_longitude", "d12_separation",
           "classify_target", "build_crosschart", "build_release_topology"]


class D12CrossChartError(ValueError):
    """A cross-chart input that cannot be resolved. Raised, never defaulted."""


# FR-001 · exactly these four. The Sun is NOT counted merely because it is a
# natural malefic — the ruling says so explicitly and the omission is the point.
STRUCTURAL_MALEFICS = ("Mars", "Saturn", "Rahu", "Ketu")

KENDRA = (1, 4, 7, 10)
TRIKONA = (1, 5, 9)            # H1 appears in both; one topology, not two
DUSTHANA = (6, 8, 12)
REDIRECTED_HOUSES = (2, 3, 6, 8, 11, 12)

KETU_RELEASE_HOUSES = (8, 10, 12)
LUMINARY_WEIGHT = {"Uchcha": 2, "Sva": 2, "Mitra": 2, "Sama": 1,
                   "Shatru": 0, "Neecha": 0}

LAGNA_AXIS_ORB = 5.0


def _facts(fact_set: Any):
    if isinstance(fact_set, Mapping):
        return (dict(fact_set["d12_lagna"]),
                {g: dict(p) for g, p in fact_set["placements"].items()},
                [dict(h) for h in fact_set["houses"]])
    raise D12CrossChartError(f"unrecognised fact set {type(fact_set).__name__}")


def _row(houses: Sequence[Mapping[str, Any]], n: int) -> Mapping[str, Any]:
    for h in houses:
        if h["house"] == n:
            return h
    raise D12CrossChartError(f"house row {n} absent")


def _tri(value: Optional[bool], resolved: bool) -> Tri:
    """Missing upstream authority is UNKNOWN. Never FALSE."""
    if not resolved or value is None:
        return Tri.UNKNOWN
    return Tri.TRUE if value else Tri.FALSE


def _upstream_for(target: str, evidence: Any) -> UpstreamEvidence:
    """Read the published relation evidence for one target, or record its
    absence honestly as UNKNOWN."""
    if evidence is None:
        return UpstreamEvidence(
            authority_resolved=False,
            tight_functional_malefic_affliction=Tri.UNKNOWN,
            approved_benefic_mitigation=Tri.UNKNOWN,
            tight_node_conjunction=Tri.UNKNOWN)
    per = getattr(evidence, "targets", None) or {}
    ev = None
    for graha, item in per.items():
        if getattr(graha, "value", str(graha)) == target:
            ev = item
            break
    if ev is None:
        return UpstreamEvidence(
            authority_resolved=False,
            tight_functional_malefic_affliction=Tri.UNKNOWN,
            approved_benefic_mitigation=Tri.UNKNOWN,
            tight_node_conjunction=Tri.UNKNOWN)
    resolved = bool(getattr(evidence, "functional_authority_resolved", False)
                    and getattr(ev, "functional_authority_resolved", False))
    def _names(edges):
        return sorted({getattr(e.source, "value", str(e.source)) for e in edges})
    return UpstreamEvidence(
        authority_resolved=resolved,
        tight_functional_malefic_affliction=_tri(
            ev.tight_functional_malefic_affliction, resolved),
        approved_benefic_mitigation=_tri(ev.approved_benefic_mitigation, resolved),
        tight_node_conjunction=_tri(ev.tight_node_conjunction, resolved),
        functional_malefic_sources=_names(
            list(ev.functional_malefic_conjunctions) + list(ev.functional_malefic_drishti)),
        mitigator_sources=_names(ev.benefic_mitigations))


# ─────────────────────────────────────────────────────────────────────────────
# FR-001
# ─────────────────────────────────────────────────────────────────────────────

def classify_target(target: str, source_house: int, placements, houses,
                    evidence: Any = None) -> StructuralClassification:
    """FR-001, in the locked precedence: Loaded > Supported > Redirected.

    No score is computed and no state is weighed against another; each is a
    predicate, and the first that holds wins.
    """
    if target not in placements:
        raise D12CrossChartError(f"{target!r} absent from the D12 placements")
    p = placements[target]
    house, dignity = p["house"], p["dignity_state"]
    up = _upstream_for(target, evidence)

    # ── Loaded ───────────────────────────────────────────────────────────────
    occupants = list(_row(houses, house)["occupants"])
    structural = sorted(g for g in occupants if g in STRUCTURAL_MALEFICS)
    heavily = len(structural) >= 2 or up.tight_node_conjunction is Tri.TRUE
    loaded_basis = LoadedBasis(
        lord_neecha=(dignity == "Neecha"),
        structural_malefic_occupants=structural,
        heavily_occupied=heavily,
        tight_node_conjunction=up.tight_node_conjunction)
    loaded = loaded_basis.lord_neecha or heavily

    # ── Supported · evaluated only if Loaded is FALSE ────────────────────────
    in_kendra = house in KENDRA
    in_trikona = house in TRIKONA
    # H1 is in both lists. Counted once: this is a boolean topology, not a tally.
    topology = in_kendra or in_trikona
    dignified = dignity in ("Mitra", "Sva")

    # Strict dusthāna interference: all three must hold. If the upstream
    # authority cannot prove the affliction or the mitigation, the predicate is
    # UNKNOWN — and an UNKNOWN interference can never print a Supported result.
    if house not in DUSTHANA:
        interference = Tri.FALSE
    elif up.tight_functional_malefic_affliction is Tri.UNKNOWN \
            or up.approved_benefic_mitigation is Tri.UNKNOWN:
        interference = Tri.UNKNOWN
    elif up.tight_functional_malefic_affliction is Tri.TRUE \
            and up.approved_benefic_mitigation is Tri.FALSE:
        interference = Tri.TRUE
    else:
        interference = Tri.FALSE

    supported_basis = SupportedBasis(
        in_kendra=in_kendra, in_trikona=in_trikona,
        dignity_mitra_or_sva=dignified, supportive_topology=(topology or dignified),
        interference=interference)

    # CORR-01 · UNKNOWN is scoped to where it can actually change the answer.
    # Strict dusthana interference only ever BLOCKS Supported, so an unresolved
    # interference predicate matters only for a target that could otherwise BE
    # Supported. A target with no supportive basis at all - neither
    # Kendra/Trikona nor Mitra/Sva - cannot reach Supported however the
    # interference resolves, so the missing evidence is irrelevant to it and
    # Redirected is the definite answer, not a guess.
    supported_possible = topology or dignified
    if loaded:
        classification = Classification.LOADED
    elif supported_possible and interference is Tri.UNKNOWN:
        classification = Classification.UNKNOWN
    elif supported_possible and interference is Tri.FALSE:
        classification = Classification.SUPPORTED
    elif house in REDIRECTED_HOUSES:
        classification = Classification.REDIRECTED
    else:
        classification = Classification.UNKNOWN

    return StructuralClassification(
        target=target, d1_source_house=source_house, d12_house=house,
        d12_sign=p["d12_sign"], dignity=dignity, classification=classification,
        loaded_basis=loaded_basis, supported_basis=supported_basis,
        interference_status=interference, upstream_evidence=up)


def build_crosschart(fact_set: Any, d1_house_lords: Mapping[int, str],
                     d1_chart_token: str, d12_chart_token: str,
                     evidence: Any = None) -> CrossChart:
    """§10 · the D1×D12 handshake over exactly H4, H9, H12.

    The D1 lord identities are READ from the accepted D1 house output. They are
    never derived from Lagna arithmetic here — the D1 layer already published
    them and a second derivation could disagree with the first.
    """
    if d1_chart_token != d12_chart_token:
        raise D12CrossChartError(
            "D1 and D12 inputs carry different chart tokens; refusing to "
            "combine two charts")
    _, placements, houses = _facts(fact_set)
    rows: List[StructuralClassification] = []
    for source in HANDSHAKE_SOURCE_HOUSES:
        lord = d1_house_lords.get(source)
        if not lord:
            raise D12CrossChartError(
                f"the accepted D1 output publishes no lord for H{source}; "
                f"refusing to derive it from Lagna arithmetic")
        rows.append(classify_target(lord, source, placements, houses, evidence))
    return CrossChart(chart_token=d12_chart_token, rows=rows)


# ─────────────────────────────────────────────────────────────────────────────
# FR-004 · RELEASE TOPOLOGY
# ─────────────────────────────────────────────────────────────────────────────

def _luminary(graha: str, placements) -> LuminaryFact:
    p = placements[graha]
    dignity, house = p["dignity_state"], p["house"]
    if dignity not in LUMINARY_WEIGHT:
        raise D12CrossChartError(
            f"{graha}: {dignity!r} has no FR-004 weight (nodes are ungraded and "
            f"are never luminaries)")
    weight = LUMINARY_WEIGHT[dignity]
    return LuminaryFact(
        graha=graha, d12_house=house, dignity=dignity, weight=weight,
        strong=weight == 2,
        dusthana_afflicted=(dignity == "Neecha" or house in DUSTHANA))


def d12_longitude(sign_index: int, degree_in_sign: float) -> float:
    """Absolute D12 longitude from the certified pair, 0 <= lon < 360.

    CORR-02. Two within-sign degrees are NOT comparable: a body at 12° of Pisces
    and a Lagna at 10° of Aries differ by 2° within their signs and by 28° in the
    zodiac. Every FR-004 separation is measured on this longitude.
    """
    if type(sign_index) is not int or not 0 <= sign_index <= 11:
        raise D12CrossChartError(
            f"d12_longitude: sign_index must be an int 0..11, got {sign_index!r}")
    si = sign_index
    if type(degree_in_sign) not in (int, float) or not 0.0 <= float(degree_in_sign) < 30.0:
        raise D12CrossChartError(
            f"d12_longitude: degree must be a number in [0, 30), got {degree_in_sign!r}")
    return si * 30.0 + float(degree_in_sign)


def d12_separation(a: float, b: float) -> float:
    """Shortest circular separation in [0, 180]. Wraps Pisces to Aries."""
    delta = abs(a - b) % 360.0
    return min(delta, 360.0 - delta)


def build_release_topology(fact_set: Any) -> ReleaseTopology:
    """FR-004 Ketu release dominance, evaluated independently of tension.

    THE 5-DEGREE LAGNA-AXIS PREDICATE is production-evaluable from the certified
    (d12_sign_index, d12_degree_in_sign) pair carried through build_d12_facts.
    CORR-02: the separation is measured on the ABSOLUTE D12 LONGITUDE, not on two
    within-sign degrees, so it is correct across a sign boundary and does not
    call two bodies in adjacent D12 signs "close" merely because their degrees
    within their own signs happen to be near each other.

    THE ASPECT LEG IS UNOWNED. No certified D12 aspect/opposition authority
    exists, so `full_drishti_or_opposition` is UNKNOWN. It is not a caller
    argument: a boolean handed in by a caller is an assertion, not a
    certification, and no Ketu graha-dṛṣṭi is invented here.
    """
    lagna, placements, houses = _facts(fact_set)
    for g in ("Sun", "Moon", "Ketu"):
        if g not in placements:
            raise D12CrossChartError(f"{g} absent from the D12 placements")

    kp = placements["Ketu"]
    if kp["dignity_state"] != "Ungraded":
        raise D12CrossChartError(
            f"Ketu must be Ungraded in D12; got {kp['dignity_state']!r}")
    lagna_deg = lagna.get("d12_degree_in_sign")
    lagna_si = lagna.get("d12_sign_index")
    ketu_deg = kp.get("d12_degree_in_sign")
    ketu_si = kp.get("d12_sign_index")
    ketu = KetuFact(d12_house=kp["house"], d12_sign=kp["d12_sign"],
                    dignity=kp["dignity_state"],
                    base_weight=3 if kp["house"] in KETU_RELEASE_HOUSES else 0)

    sun, moon = _luminary("Sun", placements), _luminary("Moon", placements)
    mean = (sun.weight + moon.weight) / 2.0

    # Strictly greater. Equality is not "outweighs".
    ordinary = ketu.base_weight > mean

    # CORR-01 - implemented literally: exactly ONE luminary afflicted, and THE
    # OTHER one strong. The afflicted luminary may itself hold Uchcha/Sva/Mitra
    # dignity while sitting in a dusthana, so it can appear in a "strong" list
    # too and a cardinality test on that list would wrongly fail. The predicate
    # names the other luminary directly instead.
    afflicted = [l for l in (sun, moon) if l.dusthana_afflicted]
    single_dusthana = False
    other_luminary = None
    if len(afflicted) == 1 and ketu.d12_house in KETU_RELEASE_HOUSES:
        other_luminary = moon if afflicted[0].graha == sun.graha else sun
        single_dusthana = other_luminary.strong
    dual_strong = (sun.strong and moon.strong
                   and not sun.dusthana_afflicted and not moon.dusthana_afflicted)

    if None in (ketu_deg, lagna_deg, ketu_si, lagna_si):
        proximity = Tri.UNKNOWN
        proximity_basis = ("the certified fact set carries no complete "
                           "(d12_sign_index, d12_degree_in_sign) pair; refusing "
                           "to reconstruct it")
    else:
        lagna_lon = d12_longitude(lagna_si, lagna_deg)
        ketu_lon = d12_longitude(ketu_si, ketu_deg)
        sep = d12_separation(ketu_lon, lagna_lon)
        proximity = Tri.TRUE if sep <= LAGNA_AXIS_ORB else Tri.FALSE
        proximity_basis = (
            f"certified D12 longitudes: Lagna {lagna_lon:.10f} deg, Ketu "
            f"{ketu_lon:.10f} deg, shortest circular separation {sep:.10f} deg "
            f"against a {LAGNA_AXIS_ORB} deg orb")

    axis = LagnaAxisEvidence(
        within_five_degrees_of_ascendant=proximity,
        occupies_h1_or_h7=ketu.d12_house in (1, 7),
        # CORR-02 · unowned, therefore UNKNOWN. Not False, which would assert an
        # absence nothing has established.
        full_drishti_or_opposition=Tri.UNKNOWN,
        proximity_basis=proximity_basis,
        aspect_basis=("no certified D12 aspect/opposition authority exists; "
                      "this leg is unevaluated and is never caller-supplied"))
    if dual_strong:
        # CORR-01 · THE H12 CONDITION IS MANDATORY. Ketu on the H1/H7 axis, or
        # in H10 with a close proximity, or in H8 with any other otherwise
        # positive relation, does NOT override two strong unafflicted luminaries.
        #
        # CORR-02 · three-valued. With Ketu outside H12 the answer is a definite
        # FALSE, because the mandatory house condition fails and the unowned
        # aspect leg cannot rescue it. Inside H12 with certified proximity TRUE
        # the answer is a definite TRUE. Inside H12 with proximity FALSE the
        # exception has one leg proven absent and one leg UNEVALUATED, so the
        # honest answer is UNKNOWN — claiming FALSE would assert that a relation
        # nobody has certified is absent.
        if ketu.d12_house != 12:
            dominance = Tri.FALSE
            basis = (f"dual strong luminaries; the H12 condition fails "
                     f"(Ketu H{ketu.d12_house}), so the exception cannot fire")
        elif proximity is Tri.TRUE:
            dominance = Tri.TRUE
            basis = ("dual strong luminaries; the H12 Lagna-axis exception is "
                     "proven by certified D12 proximity")
        else:
            dominance = Tri.UNKNOWN
            basis = ("dual strong luminaries with Ketu in H12: certified "
                     f"proximity is {proximity.value} and the full "
                     "dṛṣṭi/opposition leg is UNKNOWN — no certified D12 aspect "
                     "authority exists, so the exception is unevaluated")
    elif single_dusthana:
        dominance = Tri.TRUE
        basis = (f"one luminary afflicted ({afflicted[0].graha}), the other "
                 f"strong ({other_luminary.graha}), Ketu in H{ketu.d12_house}")
    else:
        dominance = Tri.TRUE if ordinary else Tri.FALSE
        basis = (f"Ketu weight {ketu.base_weight} "
                 f"{'>' if ordinary else '<='} luminary mean {mean}")

    return ReleaseTopology(
        ketu=ketu, sun=sun, moon=moon, luminary_mean=mean,
        ordinary_comparison=ordinary, single_dusthana_override=single_dusthana,
        dual_strong_luminaries=dual_strong, lagna_axis=axis,
        dominance=dominance,
        # A D12 pull. Never a statement about vocation, public standing or D10.
        basis=f"D12 release pull: {basis}")
