"""d12_publication.py — assemble the frozen §§0-15 page from accepted layers.

D12-006A. This module PUBLISHES. It computes no astrology, selects no
interpretation and writes no corpus: every deterministic sentence arrives from
D12-004 (§§5-9) or D12-005 (§§10-12) and is placed into the frozen page shape.

FAIL CLOSED, TWICE, DELIBERATELY:
  * an UNKNOWN §10 classification is an engineering state, not customer copy.
    It is never renamed, never softened, never printed as a fourth class — the
    whole publication refuses.
  * an unresolved §11 is never converted into the static fallback. Converting it
    would assert that the unresolved trigger evaluated FALSE, which is exactly
    the defect D12-005-CORR-02 closed one layer down.

And a third, from the frozen page itself: the page REQUIRES §12, and FR-003
authorises no triad for the fallback. So a legitimately-fallback tension yields
usable §§0-11 atoms but no complete report. Inventing a fifth instruction set to
make the total come out would be manufacturing doctrine.
"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional

import d12_corpus as K
from d12_crosschart_contract import Classification, CrossChart, ReleaseTopology, Tri
from d12_instruction_corpus import TENSION_FALLBACK, TENSION_TITLE, instruction_text
from d12_publication_contract import (
    CHART_CARD_NOTES, CHIPS, DIGNITY_LEGEND, GLYPHS, MARAKA_POINTER,
    PERMITTED_QUESTIONS, PUBLICATION_CONTRACT_VERSION, SECTION_1_ASIDE,
    SECTION_1_COPY, SECTION_2_STEPS, SECTION_14_COPY, SECTION_15_GLOSSARY,
    THROUGH_LORD, ChartRow, Chip, DevataClimateRow, GlossaryEntry, GrahaRow,
    CLIMATE_COLLAPSE, DevataImprintRow, HandshakeRow, ParentCard, PermittedQuestion, ReadStep,
    ResidueRow, grid_one_line,
    Section0, Section1, Section2, Section3, Section4, Section5, Section6,
    Section7, Section8, Section9, Section10, Section11, Section12, Section14,
    Section15, TaggedBlock,
)

__all__ = ["D12PublicationError", "PublicationBlocked", "build_publication_atoms"]

SIGN_ABBR = ("Ar", "Ta", "Ge", "Cn", "Le", "Vi", "Li", "Sc", "Sg", "Cp", "Aq", "Pi")

STANCE_GLOSS = {
    "Aries": "Through initiative", "Taurus": "Through holding",
    "Gemini": "Through mind", "Cancer": "Through feeling",
    "Leo": "Through standing", "Virgo": "Through sorting",
    "Libra": "Through pairing", "Scorpio": "Through depth",
    "Sagittarius": "Through aim", "Capricorn": "Through structure",
    "Aquarius": "Through distance", "Pisces": "Through dissolving",
}

SECTION_8_TEACHING = (
    "Some readers use D12 houses as the residue of the last life — what was "
    "already skilled, owed, or stuck. This is leftover charge, not a past-life "
    "documentary. It does not name who you were.")


class D12PublicationError(ValueError):
    """A publication input that cannot be placed into the frozen page."""


class PublicationBlocked(D12PublicationError):
    """The deterministic layer produced a state the frozen page cannot print.

    Distinct from a malformed input on purpose: this is a correct engine result
    that is simply not publishable, and the caller must refuse rather than
    repair it.
    """


def _dignity_word(state: str) -> str:
    return state


def _through(house_row: Mapping[str, Any]) -> str:
    """The frozen phrase for a vacant house."""
    occ = list(house_row["occupants"])
    return ", ".join(occ) if occ else f"{THROUGH_LORD} {house_row['lord']}"


def _placement(facts, graha: str) -> Mapping[str, Any]:
    p = facts["placements"].get(graha)
    if p is None:
        raise D12PublicationError(f"{graha} absent from the accepted D12 facts")
    return p


def _row(facts, house: int) -> Mapping[str, Any]:
    for r in facts["houses"]:
        if r["house"] == house:
            return r
    raise D12PublicationError(f"house row {house} absent")


def _short(graha: str, facts) -> str:
    p = _placement(facts, graha)
    return f"{graha} · H{p['house']} {p['d12_sign']} · {p['dignity_state']}"


# ─────────────────────────────────────────────────────────────────────────────
# §0 · HEADER
# ─────────────────────────────────────────────────────────────────────────────

def _current_mahadasha_graha(snapshot: Mapping[str, Any]) -> str:
    """NOW consumes ONLY the already-certified current Mahādaśā graha.

    No Mahādaśā is calculated, today's date is never inspected, and the
    sequence is never scanned to infer a current period — the snapshot either
    carries the fact or the report is unavailable.
    """
    dasha = snapshot.get("dasha")
    if not isinstance(dasha, Mapping):
        raise PublicationBlocked("the snapshot carries no dasha block")
    current = dasha.get("current_mahadasha")
    if not isinstance(current, Mapping) or not current.get("planet"):
        raise PublicationBlocked(
            "the snapshot carries no current_mahadasha.planet; the NOW chip has "
            "no certified authority and the report is unavailable")
    return str(current["planet"])


def _build_section0(facts, topology: ReleaseTopology, snapshot) -> Section0:
    lagna = facts["d12_lagna"]
    lagnesh = lagna["lagnesh"]
    lp = _placement(facts, lagnesh)
    sun, moon = _placement(facts, "Sun"), _placement(facts, "Moon")

    # FATHER / MOTHER · Karaka first, per the frozen display rule. The house
    # fallback is used only when the karaka is absent, which cannot happen on a
    # complete fact set but is expressed rather than assumed.
    father = f"Sun · H{sun['house']}"
    mother = f"Moon · H{moon['house']}"
    if moon["dignity_state"] == "Neecha":
        mother += " Neecha"          # the display rule: print Neecha if true

    # RELEASE consumes FR-004 and nothing else. Short logic, not a sermon.
    if topology.dominance is Tri.TRUE:
        release = "Ketu outweighs"
    elif topology.dominance is Tri.FALSE:
        release = "Luminaries hold"
    else:
        raise PublicationBlocked(
            "FR-004 release dominance is UNKNOWN; the RELEASE chip has no "
            "publishable value and the report is unavailable")

    md = _current_mahadasha_graha(snapshot)
    mdp = _placement(facts, md)

    chips = [
        Chip(label="STANCE", value=f"{lagna['d12_sign']} · "
                                   f"{STANCE_GLOSS[lagna['d12_sign']]}",
             source="D12 Lagna"),
        Chip(label="RULER",
             value=f"{lagnesh} · H{lp['house']} {lp['d12_sign']} "
                   f"{lp['dignity_state']}",
             source="D12 Lagnesh"),
        Chip(label="FATHER", value=father, source="Sun in D12"),
        Chip(label="MOTHER", value=mother, source="Moon in D12"),
        Chip(label="RELEASE", value=release, source="FR-004 release topology"),
        Chip(label="NOW", value=f"{md} · H{mdp['house']}",
             source="certified dasha.current_mahadasha.planet"),
    ]
    inp = snapshot.get("input") or {}
    return Section0(birth_date=inp.get("date"), birth_time=inp.get("time"),
                    chips=chips)


# ─────────────────────────────────────────────────────────────────────────────
# §§1-4
# ─────────────────────────────────────────────────────────────────────────────

def _build_section3(facts) -> Section3:
    houses = [ChartRow(house=r["house"], sign=r["sign"],
                       sign_abbr=SIGN_ABBR[r["sign_index"]], lord=r["lord"],
                       occupants=list(r["occupants"]))
              for r in facts["houses"]]
    grahas = [GrahaRow(graha=g, house=p["house"], sign=p["d12_sign"],
                       dignity=_dignity_word(p["dignity_state"]),
                       vargottama=bool(p["vargottama"]))
              for g, p in facts["placements"].items()]
    return Section3(d12_lagna_sign=facts["d12_lagna"]["d12_sign"],
                    d12_lagnesh=facts["d12_lagna"]["lagnesh"],
                    houses=houses, grahas=grahas)


def _build_section4(facts, findings, topology) -> Section4:
    lagna = facts["d12_lagna"]
    lp = _placement(facts, lagna["lagnesh"])
    h6 = _row(facts, 6)
    moon = _placement(facts, "Moon")
    answers = (
        f"{lagna['d12_sign']} / {lagna['lagnesh']} in H{lp['house']} — "
        f"{STANCE_GLOSS[lagna['d12_sign']].lower()}.",
        f"H6 {'occupied by ' + ', '.join(h6['occupants']) if h6['occupants'] else _through(h6)}"
        f"; Moon {moon['dignity_state']} in H{moon['house']}.",
        ("Ketu outweighs Sun/Moon — a pull, not a career instruction."
         if topology.dominance is Tri.TRUE
         else "The luminaries hold — release reads as stance, not exit."),
    )
    return Section4(questions=[
        PermittedQuestion(question=q, read_from=r, answer=a)
        for (q, r), a in zip(PERMITTED_QUESTIONS, answers)])


# ─────────────────────────────────────────────────────────────────────────────
# §§5-9 · consume D12-004, place, never regenerate
# ─────────────────────────────────────────────────────────────────────────────

def _lagna_slice(lagna: Mapping[str, Any]) -> int:
    """CORR-01 · the LAGNA's own slice, from the certified D1/D12 sign pair.

        slice = ((d12_sign_index - d1_sign_index) mod 12) + 1

    No rounded degree is read. The previous build used the LAGNESH's slice,
    which printed Mercury's slice-1 Kubera imprint under a §5 heading that
    speaks for the Lagna — a crossed speaker, and the wrong deity.
    """
    d12 = lagna.get("d12_sign_index")
    d1 = lagna.get("d1_sign_index")
    if type(d12) is not int or type(d1) is not int:
        raise D12PublicationError("the D12 Lagna carries no certified sign pair")
    return ((d12 - d1) % 12) + 1


def _build_section5(facts, findings) -> Section5:
    s5 = findings.section5
    lagna = facts["d12_lagna"]
    lp = _placement(facts, lagna["lagnesh"])
    slice_no = _lagna_slice(lagna)
    primary, hidden = K.devata_for_slice(slice_no)

    imprint_bits = [f"{primary}: {K.DEVATA_GLOSS[primary]}"]
    if hidden in K.DEVATA_GLOSS:
        imprint_bits.append(f"{hidden}: {K.DEVATA_GLOSS[hidden]}")
    varg = None
    if lp["vargottama"]:
        varg = TaggedBlock(
            speaker="PARĀŚARA · VARGOTTAMA FIRST SLICE",
            label="Vargottama first slice",
            text=f"{lagna['lagnesh']} holds the same sign in D1 and D12, in the "
                 f"first 2°30′: the reliable faculty of this D12.",
            basis={"graha": lagna["lagnesh"], "slice": str(slice_no)})
    return Section5(
        lagna=TaggedBlock(speaker="PARĀŚARA · D12 LAGNA", label="Lagna",
                          text=s5.finding.text,
                          corpus_key=s5.finding.corpus_key,
                          basis=dict(s5.finding.basis)),
        lagnesh=TaggedBlock(
            speaker="PARĀŚARA · D12 LAGNESH", label="Lagnesh",
            text=f"{lagna['lagnesh']} in H{lp['house']} {lp['d12_sign']} · "
                 f"{lp['dignity_state']}.",
            basis={"house": str(lp["house"]), "dignity": lp["dignity_state"]}),
        imprint=TaggedBlock(speaker="DEVATĀ", label="Imprint",
                            text=" ".join(imprint_bits),
                            basis={"slice": str(slice_no), "primary": primary,
                                   "hidden": hidden}),
        vargottama_first_slice=varg,
        corpus_key=s5.finding.corpus_key)


def _parent_card(parent: str, findings, facts) -> ParentCard:
    speakers = (findings.section6.father if parent == "Father"
                else findings.section6.mother)
    karaka, house_lord, d1_lord = speakers          # locked family order
    def block(sp, sf, label):
        return TaggedBlock(speaker=sp, label=label, text=sf.finding.text,
                           corpus_key=sf.finding.corpus_key,
                           basis=dict(sf.finding.basis))
    families = (["Sun Karaka", "D12 H9 Lord", "D1 9th Lord in D12"]
                if parent == "Father"
                else ["Moon Karaka", "D12 H4 Lord", "D1 4th Lord in D12"])
    return ParentCard(
        parent=parent, families=families,
        karaka=block("KARAKA", karaka, f"{karaka.subject or '—'} in D12"),
        house_of_parent=block("PARĀŚARA · HOUSE", house_lord,
                              "D12 9th" if parent == "Father" else "D12 4th"),
        d1_lord_in_d12=block("D1 × D12", d1_lord,
                             "D1 9th lord in D12" if parent == "Father"
                             else "D1 4th lord in D12"))


def _build_section6(facts, findings) -> Section6:
    return Section6(father=_parent_card("Father", findings, facts),
                    mother=_parent_card("Mother", findings, facts),
                    # CORR-01 · ABSENT. The PDF permits this pointer only WHEN a
                    # Maraka flag fires, and no certified Maraka trigger exists
                    # anywhere in this server pipeline. Printing it on every
                    # report raised parental health unprompted — the exact
                    # implication the frozen page cuts. None is computed here and
                    # no legacy flag is restored; the glossary keeps the term's
                    # limiting explanation.
                    maraka_pointer=None)


def _build_section7(findings, facts) -> Section7:
    s7 = findings.section7
    h6 = _row(facts, 6)
    return Section7(
        occupants=list(s7.h6_occupants), lord=s7.h6_lord,
        lord_house=s7.h6_lord_house,
        status=("Occupied" if s7.h6_occupants else _through(h6)),
        picture=TaggedBlock(speaker="PARĀŚARA · H6", label="The unpaid item",
                            text=s7.finding.text,
                            corpus_key=s7.finding.corpus_key,
                            basis=dict(s7.finding.basis)),
        corpus_key=s7.finding.corpus_key)


def _build_section8(findings, facts) -> Section8:
    rows = []
    for d in findings.section8.domains:
        hr = _row(facts, d.house)
        rows.append(ResidueRow(domain=d.visible_label, house=d.house,
                               read=_through(hr), clause=d.constant_clause))
    return Section8(teaching=SECTION_8_TEACHING, rows=rows)


def _build_section9(findings) -> Section9:
    """CORR-01 · the frozen table restored: nine public imprint rows, then the
    collapsed climates. The hidden deity stays internal — FR-005 authorises no
    compound pair display — and the hidden counts never reach customer prose."""
    imprints = [DevataImprintRow(subject=im.subject, slice=im.slice,
                                 display_name=im.display_name,
                                 who_this_is=K.DEVATA_GLOSS[im.display_name])
                for im in findings.section9.imprints]
    rows = []
    for c in findings.section9.primary_climates:
        gloss = c.gloss or ""
        rows.append(DevataClimateRow(
            deity=c.deity, subjects=list(c.subjects), count=c.count,
            printed_once_as=(gloss + " " + CLIMATE_COLLAPSE.format(count=c.count)
                             if c.count > 1 else gloss)))
    return Section9(imprints=imprints, climates=rows)


# ─────────────────────────────────────────────────────────────────────────────
# §§10-12 · consume D12-005
# ─────────────────────────────────────────────────────────────────────────────

def _build_section10(crosschart: CrossChart) -> Section10:
    rows = []
    for r in crosschart.rows:
        if r.classification is Classification.UNKNOWN:
            raise PublicationBlocked(
                f"the §10 row for the D1 H{r.d1_source_house} lord classifies "
                f"UNKNOWN; that is an engineering state, not a customer class, "
                f"and it may not be renamed or softened to complete the page")
        rows.append(HandshakeRow(
            d1_lord_of=r.d1_source_house, lord=r.target,
            in_d12=f"{r.d12_sign} H{r.d12_house} · {r.dignity}",
            classification=r.classification.value,
            one_line=grid_one_line(r.d1_source_house, r.classification.value)))
    return Section10(rows=rows)


def _build_section11(tension, body: Optional[str] = None) -> Section11:
    if tension.unresolved_at is not None:
        raise PublicationBlocked(
            f"§11 is unresolved at {tension.unresolved_at!r}; converting it to "
            f"the static fallback would assert that the unresolved trigger "
            f"evaluated FALSE")
    if tension.winner is None:
        text = TENSION_FALLBACK
        return Section11(tension_key=None, title=None, body=text,
                         fallback_applied=True, word_count=len(text.split()))
    text = body if body is not None else ""
    if not text.strip():
        raise D12PublicationError("§11 needs composed prose for the winner")
    return Section11(tension_key=tension.winner,
                     title=TENSION_TITLE[tension.winner], body=text,
                     fallback_applied=False, word_count=len(text.split()))


def _build_section12(tension) -> Section12:
    if tension.winner is None:
        raise PublicationBlocked(
            "the tension reached the static fallback, for which FR-003 "
            "authorises no Three Instructions triad; the frozen page requires "
            "§12, so the report is unavailable rather than invented")
    return Section12(tension_key=tension.winner,
                     cultivate=instruction_text(tension.winner, "cultivate"),
                     watch=instruction_text(tension.winner, "watch"),
                     practise=instruction_text(tension.winner, "practise"))


# ─────────────────────────────────────────────────────────────────────────────
# THE ATOM SET
# ─────────────────────────────────────────────────────────────────────────────

def build_publication_atoms(facts, findings, crosschart, topology, tension,
                            snapshot) -> Dict[str, Any]:
    """Everything §§0-12, 14 and 15 need, with no provider involved.

    §11's prose and §13's essay are composed later, by the bounded synthesiser,
    from these atoms. §11 is returned here in its fallback form only; for a
    winning tension the caller supplies the composed body.
    """
    return {
        "section0": _build_section0(facts, topology, snapshot),
        "section1": Section1(paragraphs=list(SECTION_1_COPY),
                             newbie_aside=SECTION_1_ASIDE),
        "section2": Section2(steps=[ReadStep(step=s, look_at=l, question=q)
                                    for s, l, q in SECTION_2_STEPS]),
        "section3": _build_section3(facts),
        "section4": _build_section4(facts, findings, topology),
        "section5": _build_section5(facts, findings),
        "section6": _build_section6(facts, findings),
        "section7": _build_section7(findings, facts),
        "section8": _build_section8(findings, facts),
        "section9": _build_section9(findings),
        "section10": _build_section10(crosschart),
        "section12": _build_section12(tension),
        "section14": Section14(lines=list(SECTION_14_COPY)),
        "section15": Section15(entries=[GlossaryEntry(term=t, meaning=m)
                                        for t, m in SECTION_15_GLOSSARY]),
    }
