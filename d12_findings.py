"""d12_findings.py — Phalit.ai D12 deterministic selectors for §§5-9.

D12-004. Pure lookup and predicate evaluation over the accepted D12-003 fact
layer. This module:

  * computes no astrology and re-derives no D12 placement — it consumes the
    certified D12FactSet and nothing else;
  * imports no provider, no network library and no main.py;
  * generates no text. Every sentence it returns is a value from d12_corpus,
    reached by a named key that travels with the output.

WHAT THIS FLIGHT DELIBERATELY DOES NOT DO. FR-001's Supported / Loaded /
Redirected classification needs the upstream certified benefic-mitigation
designation, which this parent does not publish (D12-002-CORR-02 §E: the
`mitigation` symbol does not exist anywhere in the parent). The enum is defined
and validated here and an externally supplied value is consumed where a Founder
cell requires one — but it is NEVER inferred. Absent the token, the ordinary §6
fallback applies. The same discipline governs §7: where a cell needs a
benefic/malefic or strength predicate that cannot be proven from supplied
authority, that cell does not fire and the Founder-approved baseline applies.
Inventing a D12-private substitute for either would be manufacturing doctrine.
"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import d12_corpus as K
from d12_corpus import CorpusKeyError
from d12_findings_contract import (
    D12Findings, DevataClimate, DevataImprint, Finding, ResidueDomain,
    Section5, Section6, Section7, Section8, Section9, SpeakerFinding,
)

__all__ = ["D12FindingsError", "UpstreamPredicates", "build_d12_findings",
           "build_section5", "build_section6", "build_section7",
           "build_section8", "build_section9"]


class D12FindingsError(ValueError):
    """A selector input that cannot be resolved. Raised, never defaulted."""


class UpstreamPredicates:
    """Optional certified facts this flight may consume but must not compute.

    Every field defaults to "not supplied". A predicate that is not supplied is
    UNPROVEN, and an unproven predicate never fires a cell — it falls through to
    the Founder-approved baseline and is recorded in `unproven_predicates` so QA
    can see exactly which authority was missing.
    """

    def __init__(self,
                 natural_nature: Optional[Mapping[str, str]] = None,
                 strong_grahas: Optional[Sequence[str]] = None,
                 structural_class: Optional[Mapping[str, str]] = None):
        self.natural_nature = dict(natural_nature or {})
        # CORR-01 · strength authority is THREE-STATE and tracked independently.
        # None means the authority was never supplied (UNKNOWN); an empty set
        # means it WAS supplied and names nobody strong (a proven FALSE for
        # every graha). Conflating those two, or deciding presence from an
        # unrelated field such as natural_nature, was QA's finding.
        self.strong_grahas: Optional[frozenset] = (
            None if strong_grahas is None else frozenset(strong_grahas))
        self.structural_class = dict(structural_class or {})
        for graha, nature in self.natural_nature.items():
            if nature not in ("benefic", "malefic"):
                raise D12FindingsError(
                    f"natural_nature[{graha!r}] must be 'benefic' or 'malefic', "
                    f"got {nature!r}")
        for key, value in self.structural_class.items():
            if value not in K.STRUCTURAL_CLASSES:
                raise D12FindingsError(
                    f"structural_class[{key!r}] must be one of "
                    f"{K.STRUCTURAL_CLASSES}, got {value!r}")

    def nature_of(self, graha: str) -> Optional[str]:
        return self.natural_nature.get(graha)

    @property
    def has_strength_authority(self) -> bool:
        """Whether a strength authority was supplied at all. Independent of
        every other field."""
        return self.strong_grahas is not None

    def is_strong(self, graha: str) -> Optional[bool]:
        """True / False / None, where None means UNKNOWN — no authority."""
        if self.strong_grahas is None:
            return None
        return graha in self.strong_grahas

    def classification(self, key: str) -> Optional[str]:
        return self.structural_class.get(key)


# ─────────────────────────────────────────────────────────────────────────────
# SHARED READERS OVER THE CERTIFIED FACT SET
# ─────────────────────────────────────────────────────────────────────────────

def _facts(fact_set: Any) -> Tuple[Dict[str, Any], Dict[str, Any], List[Any]]:
    """Accept either the typed D12FactSet or the build_d12_facts mapping."""
    if hasattr(fact_set, "placements") and hasattr(fact_set, "houses"):
        lagna = fact_set.lagna if hasattr(fact_set, "lagna") else fact_set.d12_lagna
        lagna = lagna.dict() if hasattr(lagna, "dict") else dict(lagna)
        placements = {g: (p.dict() if hasattr(p, "dict") else dict(p))
                      for g, p in fact_set.placements.items()}
        houses = [(h.dict() if hasattr(h, "dict") else dict(h))
                  for h in fact_set.houses]
    elif isinstance(fact_set, Mapping):
        lagna = dict(fact_set["d12_lagna"])
        placements = {g: dict(p) for g, p in fact_set["placements"].items()}
        houses = [dict(h) for h in fact_set["houses"]]
    else:
        raise D12FindingsError(f"unrecognised fact set {type(fact_set).__name__}")
    if len(placements) != 9:
        raise D12FindingsError("fact set must carry exactly nine placements")
    if len(houses) != 12:
        raise D12FindingsError("fact set must carry exactly twelve house rows")
    return lagna, placements, houses


def _bucket(state: str, where: str) -> str:
    """Collapse a graded dignity state into its corpus bucket.

    `Ungraded` has no bucket by design: the nodes are ungraded in D12 (FR-004)
    and no §5 or §6 speaker slot can be occupied by a node, since every one of
    them is a sign lord or a luminary. Meeting one here means the caller has
    routed a node into a speaker slot — fail closed rather than pick a bucket.
    """
    if state not in K.DIGNITY_BUCKET:
        raise D12FindingsError(
            f"{where}: {state!r} has no corpus dignity bucket "
            f"(Ungraded cannot occupy a speaker slot)")
    return K.DIGNITY_BUCKET[state]


def _category(house: int, where: str) -> str:
    if house not in K.HOUSE_CATEGORY:
        raise D12FindingsError(f"{where}: house {house!r} outside 1..12")
    return K.HOUSE_CATEGORY[house]


def _element(sign: str, where: str) -> str:
    if sign not in K.SIGN_ELEMENT:
        raise D12FindingsError(f"{where}: unknown sign {sign!r}")
    return K.SIGN_ELEMENT[sign]


def _house_row(houses: Sequence[Mapping[str, Any]], number: int) -> Mapping[str, Any]:
    for row in houses:
        if row["house"] == number:
            return row
    raise D12FindingsError(f"house row {number} absent")


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 5 · INHERITANCE MET
# ─────────────────────────────────────────────────────────────────────────────

def build_section5(fact_set: Any) -> Section5:
    lagna, placements, houses = _facts(fact_set)
    lagna_sign = lagna["d12_sign"]
    lagnesh = lagna["lagnesh"]
    if lagnesh not in placements:
        raise D12FindingsError(f"Lagnesh {lagnesh!r} absent from the placements")
    p = placements[lagnesh]
    house = p["house"]
    element = _element(lagna_sign, "S5.lagna")
    category = _category(house, "S5.lagnesh")
    bucket = _bucket(p["dignity_state"], "S5.lagnesh")

    key = (lagna_sign, house, bucket)
    basis = {"lagna_sign": lagna_sign, "lagnesh": lagnesh,
             "lagnesh_house": str(house), "house_category": category,
             "element": element, "dignity_bucket": bucket}

    if key in K.S5_BESPOKE:
        finding = Finding(section_id="S5", speaker_key="inheritance",
                          corpus_key=f"S5.bespoke.{lagna_sign}.H{house}.{bucket}",
                          text=K.S5_BESPOKE[key], basis=basis)
        bespoke = True
    else:
        text = K.S5_TEMPLATE.format(
            mode=K.S5_ELEMENT_MODE[element],
            category=K.S5_CATEGORY_TOKEN[category],
            dignity=K.S5_DIGNITY_DESCRIPTOR[bucket],
            risk=K.S5_ELEMENT_RISK[element])
        finding = Finding(section_id="S5", speaker_key="inheritance",
                          corpus_key=f"S5.fallback.{element}.{category}.{bucket}",
                          text=text, basis=basis)
        bespoke = False

    return Section5(lagna_sign=lagna_sign, lagna_element=element,
                    lagnesh=lagnesh, lagnesh_house=house,
                    house_category=category, dignity_bucket=bucket,
                    bespoke=bespoke, finding=finding)


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 6 · FATHER & MOTHER
# ─────────────────────────────────────────────────────────────────────────────

def _speaker_subject(family: str, lagna, placements, houses,
                     d1_lords: Mapping[str, str]) -> Optional[str]:
    """Which body speaks for this family. None when the authority is absent."""
    if family == "Sun Karaka":
        return "Sun"
    if family == "Moon Karaka":
        return "Moon"
    if family == "D12 H9 Lord":
        return _house_row(houses, 9)["lord"]
    if family == "D12 H4 Lord":
        return _house_row(houses, 4)["lord"]
    if family == "D1 9th Lord in D12":
        return d1_lords.get("H9")
    if family == "D1 4th Lord in D12":
        return d1_lords.get("H4")
    raise D12FindingsError(f"unknown speaker family {family!r}")


def _s6_bespoke_key(family: str, subject: Optional[str], placements,
                    houses, predicates: UpstreamPredicates) -> Optional[str]:
    """The first Founder cell that fires for this speaker, or None.

    Cells needing a structural class consume a supplied token only. Absent the
    token the cell does not fire — nothing is inferred.
    """
    if subject is None or subject not in placements:
        return None
    p = placements[subject]
    sign, house, state = p["d12_sign"], p["house"], p["dignity_state"]

    if family == "Sun Karaka":
        if (sign, house, state) == ("Virgo", 4, "Sama"):
            return "sun_karaka.virgo.h4.sama"
        if (sign, house, state) == ("Aries", 10, "Uchcha"):
            return "sun_karaka.aries.h10.uchcha"
    if family == "Moon Karaka":
        if (sign, house, state) == ("Scorpio", 6, "Neecha"):
            return "moon_karaka.scorpio.h6.neecha"
        if (sign, house, state) == ("Cancer", 4, "Sva"):
            return "moon_karaka.cancer.h4.sva"
    if family == "D12 H9 Lord":
        h9_empty = not _house_row(houses, 9)["occupants"]
        if h9_empty and house == 11:
            cls = predicates.classification("H9_lord")
            if state == "Neecha" or cls == "Loaded":
                return "h9_lord.empty_h9.lord_in_h11.neecha_or_loaded"
        # FD-004-02 (LOCKED) · "Vacant 9th House / Lord Well-Placed in Kendra
        # or Trikona (Supported)". All three conditions must hold.
        #
        # THE CRITICAL QUALIFICATION: if the H9 lord itself occupies H9, then
        # H9 is NOT vacant and this cell cannot fire — `h9_empty` is computed
        # from the occupancy table, so a lord in H9 fails the first condition
        # before the placement test is reached. There is no "vacant except for
        # its lord" reading, and none is authorised.
        #
        # Supported is CONSUMED, never calculated. Kendra/Trikona placement
        # alone does not imply it.
        if h9_empty and _category(house, "S6.h9_lord") in ("Kendra", "Trikona"):
            if predicates.classification("H9_lord") == "Supported":
                return ("h9_lord.vacant_h9.lord_well_placed_kendra_or_trikona"
                        ".supported")
    return None


def _s6_h4_special(houses) -> bool:
    """H4 occupied by Sun AND Rahu — fully mechanical, no predicate needed."""
    occ = set(_house_row(houses, 4)["occupants"])
    return {"Sun", "Rahu"} <= occ


def build_section6(fact_set: Any,
                   d1_lords: Optional[Mapping[str, str]] = None,
                   predicates: Optional[UpstreamPredicates] = None) -> Section6:
    lagna, placements, houses = _facts(fact_set)
    d1_lords = dict(d1_lords or {})
    predicates = predicates or UpstreamPredicates()

    speakers: List[SpeakerFinding] = []
    for family in K.SPEAKER_FAMILIES:
        parent = K.SPEAKER_PARENT[family]
        subject = _speaker_subject(family, lagna, placements, houses, d1_lords)
        cls = predicates.classification(
            "H9_lord" if family == "D12 H9 Lord" else
            "H4_lord" if family == "D12 H4 Lord" else family)

        # The H4 Sun+Rahu cell is a maternal-field statement and belongs to the
        # D12 H4 Lord speaker. It is fully mechanical, so it takes precedence
        # over that speaker's ordinary bespoke/fallback resolution.
        if family == "D12 H4 Lord" and _s6_h4_special(houses):
            key = "h4_occupied.sun_and_rahu"
        else:
            key = _s6_bespoke_key(family, subject, placements, houses, predicates)

        if subject is not None and subject in placements:
            p = placements[subject]
            house: Optional[int] = p["house"]
            category: Optional[str] = _category(house, f"S6.{family}")
            element: Optional[str] = _element(p["d12_sign"], f"S6.{family}")
            bucket: Optional[str] = _bucket(p["dignity_state"], f"S6.{family}")
        else:
            house = category = element = bucket = None

        basis = {"family": family, "parent": parent,
                 "subject": subject or "(absent)",
                 "structural_class": cls or "(not supplied)"}
        if house is not None:
            basis.update({"house": str(house), "house_category": category,
                          "element": element, "dignity_bucket": bucket})

        if key is not None:
            finding = Finding(section_id="S6", speaker_key=family,
                              corpus_key=f"S6.bespoke.{key}",
                              text=K.S6_BESPOKE[key], basis=basis)
            bespoke = True
        else:
            if house is None:
                raise D12FindingsError(
                    f"S6.{family}: no subject and no bespoke cell — the speaker "
                    f"cannot be resolved. Supply the D1 lord authority.")
            text = K.S6_TEMPLATE.format(
                speaker=K.S6_SPEAKER_IDENTITY[family],
                category=K.S6_CATEGORY_LANGUAGE[category],
                load=K.S6_DIGNITY_LOAD[bucket],
                tone=K.S6_ELEMENT_TONE[element])
            finding = Finding(
                section_id="S6", speaker_key=family,
                corpus_key=f"S6.fallback.{family}.{category}.{element}.{bucket}",
                text=text, basis=basis)
            bespoke = False

        speakers.append(SpeakerFinding(
            family=family, parent=parent, subject=subject, house=house,
            house_category=category, element=element, dignity_bucket=bucket,
            structural_class=cls, bespoke=bespoke, finding=finding))

    return Section6(father=[s for s in speakers if s.parent == "Father"],
                    mother=[s for s in speakers if s.parent == "Mother"])


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 7 · THE UNPAID PATTERN
# ─────────────────────────────────────────────────────────────────────────────

def build_section7(fact_set: Any,
                   predicates: Optional[UpstreamPredicates] = None) -> Section7:
    lagna, placements, houses = _facts(fact_set)
    predicates = predicates or UpstreamPredicates()

    h6 = _house_row(houses, 6)
    occupants = list(h6["occupants"])
    lord = h6["lord"]
    if lord not in placements:
        raise D12FindingsError(f"H6 lord {lord!r} absent from the placements")
    lord_house = placements[lord]["house"]
    lord_state = placements[lord]["dignity_state"]

    unproven: List[str] = []
    key: Optional[str] = None

    # Cell 1 · Moon occupant / lord in H2 / Neecha. Fully mechanical.
    if "Moon" in occupants and lord_house == 2 and lord_state == "Neecha":
        key = "moon_occupant.lord_h2.neecha"

    # Cell 2 · empty H6 / malefic lord in a dusthana. Needs natural nature.
    if key is None and not occupants and _category(lord_house, "S7") == "Dusthana":
        nature = predicates.nature_of(lord)
        if nature == "malefic":
            key = "empty_h6.malefic_lord_in_dusthana"
        elif nature is None:
            unproven.append(f"natural_nature[{lord}]")

    # Cell 3 · benefic occupant in H6 / strong lord. Needs nature and strength.
    if key is None and occupants:
        benefics = [o for o in occupants if predicates.nature_of(o) == "benefic"]
        unknown = [o for o in occupants if predicates.nature_of(o) is None]
        strong = predicates.is_strong(lord)          # True / False / None
        if benefics and strong is True:
            key = "benefic_occupant_h6.strong_lord"
        else:
            if unknown:
                unproven.extend(f"natural_nature[{o}]" for o in unknown)
            # CORR-01 · only UNKNOWN is unproven. A supplied authority that does
            # not name this lord is a proven FALSE: the branch does not fire and
            # the predicate is NOT reported as missing.
            if strong is None:
                unproven.append(f"strength[{lord}]")

    basis = {"h6_occupants": ", ".join(occupants) or "(empty)",
             "h6_lord": lord, "h6_lord_house": str(lord_house),
             "h6_lord_dignity": lord_state,
             "unproven_predicates": ", ".join(sorted(set(unproven))) or "(none)"}

    if key is not None:
        finding = Finding(section_id="S7", speaker_key="unpaid_pattern",
                          corpus_key=f"S7.cell.{key}", text=K.S7_CELLS[key],
                          basis=basis)
        baseline = False
    else:
        finding = Finding(section_id="S7", speaker_key="unpaid_pattern",
                          corpus_key="S7.baseline", text=K.S7_BASELINE,
                          basis=basis)
        baseline = True

    return Section7(h6_occupants=occupants, h6_lord=lord,
                    h6_lord_house=lord_house, baseline_applied=baseline,
                    unproven_predicates=sorted(set(unproven)), finding=finding)


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 8 · RESIDUE MAP
# ─────────────────────────────────────────────────────────────────────────────

def build_section8(fact_set: Any) -> Section8:
    """One deterministic domain object per permitted house.

    `subjects` are the factual occupants plus the house lord. No identity story
    is generated from them, and no internal corpus identifier — 'Past-Life
    Debt' above all, for H6 — is ever exposed: the visible label is the
    Founder's, and the clause is domain-constant.
    """
    lagna, placements, houses = _facts(fact_set)
    domains: List[ResidueDomain] = []
    for house in K.S8_DOMAINS:
        row = _house_row(houses, house)
        subjects = list(row["occupants"])
        lord = row["lord"]
        if lord not in subjects:
            subjects.append(lord)
        domains.append(ResidueDomain(
            house=house,
            visible_label=K.S8_VISIBLE_LABEL[house],
            subjects=subjects,
            constant_clause=K.S8_CLAUSE[house]))
    return Section8(domains=domains)


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 9 · DEVATĀ CLIMATE
# ─────────────────────────────────────────────────────────────────────────────

def _collapse(pairs: Sequence[Tuple[str, str]]) -> Tuple[List[DevataClimate],
                                                         Dict[str, int]]:
    """Repeated imprints collapse into ONE record carrying a count and the
    subjects. Four Vihwala subjects produce one Vihwala climate, not four
    repetitive descriptions."""
    order: List[str] = []
    grouped: Dict[str, List[str]] = {}
    for deity, subject in pairs:
        if deity not in grouped:
            grouped[deity] = []
            order.append(deity)
        grouped[deity].append(subject)
    climates = [DevataClimate(deity=d, count=len(grouped[d]),
                              subjects=grouped[d],
                              gloss=K.DEVATA_GLOSS.get(d))
                for d in order]
    return climates, {d: len(grouped[d]) for d in order}


def build_section9(fact_set: Any) -> Section9:
    lagna, placements, houses = _facts(fact_set)
    imprints: List[DevataImprint] = []
    primary_pairs: List[Tuple[str, str]] = []
    hidden_pairs: List[Tuple[str, str]] = []

    for graha in sorted(placements):
        slice_no = placements[graha]["slice"]
        primary, hidden = K.devata_for_slice(slice_no)
        imprints.append(DevataImprint(
            subject=graha, slice=slice_no,
            primary_deity=primary, hidden_deity=hidden,
            # FR-005: no approved compound clause exists, so the customer-facing
            # name is the primary alone. The hidden name stays internal and
            # remains available for the later FR-002 counting.
            display_name=primary))
        primary_pairs.append((primary, graha))
        hidden_pairs.append((hidden, graha))

    primary_climates, primary_counts = _collapse(primary_pairs)
    hidden_climates, hidden_counts = _collapse(hidden_pairs)
    return Section9(imprints=imprints,
                    primary_climates=primary_climates,
                    hidden_climates=hidden_climates,
                    primary_counts=primary_counts,
                    hidden_counts=hidden_counts)


# ─────────────────────────────────────────────────────────────────────────────
# THE FULL LAYER
# ─────────────────────────────────────────────────────────────────────────────

def build_d12_findings(fact_set: Any,
                       d1_lords: Optional[Mapping[str, str]] = None,
                       predicates: Optional[UpstreamPredicates] = None
                       ) -> D12Findings:
    """Deterministic §§5-9 for one certified D12 fact set.

    Same input, same output, always: no clock, no randomness, no network, no
    provider. No tension winner, no Cultivate/Watch/Practise, no D1xD12
    handshake, no Integrated Reading — those are later flights.
    """
    predicates = predicates or UpstreamPredicates()
    return D12Findings(
        section5=build_section5(fact_set),
        section6=build_section6(fact_set, d1_lords, predicates),
        section7=build_section7(fact_set, predicates),
        section8=build_section8(fact_set),
        section9=build_section9(fact_set))
