"""
d10_publication.py — D10-006 · the deterministic publication authority.

PURE AND DETERMINISTIC. One public function, `build_publication`. It composes
ratified corpus entries with certified facts. No I/O, no provider, no clock, no
browser input, no route, and no randomness: the same inputs produce the same
bytes forever.

IT COMPOSES; IT DOES NOT DECIDE. Everything it publishes was already
determined upstream:

    D10-002   placements, houses, lordships, dignity
    D10-003   the core findings, the operational states, THE TENSION WINNER
    D10-004   the cross-chart facts
    D10-005   the ratified corpus, via d10_corpus

**The tension winner is copied, never chosen.** This module contains no
predicate that could select a different one, and a test asserts the published
winner equals the findings' winner on every fixture.

WHAT IT WILL NOT DO. No Integrated Reading — §14 belongs to the next flight.
No `aligned / strained / redirected` — unratified, so the cross-chart block
carries facts only. No D9xD10 handshake sentence. No Devatā ruler, direction or
Lagna Devatā. No self-employment claim, travel prediction or Sun/Ketu conflict:
those tables do not exist in `d10_corpus`, so there is nothing to publish them
from.
"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional

import d10_corpus as CORPUS
from d10_publication_contract import (
    ChartMeta, Chip, CrossChartFacts, DevataRow, DevataSection,
    FunctionPublication, GlossaryEntry, Header, HouseLine,
    InstructionsPublication, MoneyCard, MoneyPublication,
    OperationalGroupPublication, PermittedQuestion, PullVehiclePublication,
    ReadingStep, Section1, Section2, StancePublication, StandingPublication,
    StrengthPair, StrengthPublication, TensionPublication, D10Publication,
)

GROUP_TITLES: Dict[str, str] = {
    "ENTER_ROLE": "Enter the role",
    "DO_WORK": "Do the work",
    "BE_SEEN_AND_PAID": "Be seen and paid",
    "HANDLE_PRESSURE": "Handle pressure",
    "PATRONS": "Patrons of the work",
}

DEVATA_TEACHING = (
    "Each 3° slice of the Daśāṁśa has a presiding Devatā. It does not pick a "
    "job. It colours how that graha works when it is used professionally — the "
    "ethical weather around the graha.")

CHART_CAPTION = (
    "Top diamond = House 1 (always). Number + sign abbreviation = the rāśi in "
    "that house. Count houses anti-clockwise.")

DIGNITY_KEY = [
    "Uchcha — strongest sign for that graha",
    "Sva — own sign",
    "Mitra — friend's sign",
    "Sama — neither helped nor harmed by the sign's ruler",
    "Shatru — enemy's sign",
    "Neecha — weakest sign for that graha",
    "Ungraded — the nodes outside their exaltation and debilitation",
]

#: The nine canonical grahas. Exactly these, exactly once, in the Devatā table.
CANONICAL_GRAHAS = ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus",
                    "Saturn", "Rahu", "Ketu")

DUSTHANA = frozenset({8, 12})

TENSION_UNKNOWN = "UNKNOWN"
FALLBACK = "FALLBACK_SUN_SATURN_CLIMATE"


class D10PublicationError(ValueError):
    """A required corpus entry or certified fact is missing. Raised, never
    defaulted: a publication assembled around a gap would read as a complete
    reading of a chart it never had."""


def _corpus(table: Mapping, key, what: str):
    if key not in table:
        raise D10PublicationError(f"no ratified {what} for {key!r}")
    return table[key]


# ─────────────────────────────────────────────────────────────────────────────
# §0 · §1 · §2 · §4 · static
# ─────────────────────────────────────────────────────────────────────────────

def _header(f) -> Header:
    h = f.header_facts
    lagnesh = h.work_ruler
    stance = _corpus(CORPUS.STANCE_CORPUS, h.stance.d10_lagna_sign, "stance")
    return Header(
        title=CORPUS.TITLE, subtitle=CORPUS.SUBTITLE,
        stance=Chip(label="STANCE",
                    value=f"{h.stance.d10_lagna_sign} · {stance['gloss']}"),
        work_ruler=Chip(label="WORK-RULER",
                        value=f"{lagnesh.planet} · H{lagnesh.house} {lagnesh.sign}"),
        standing=Chip(label="STANDING",
                      value=f"{h.standing.planet} · H{h.standing.house} "
                            f"{h.standing.sign} · {h.standing.dignity}"),
        # Absent, not blank, when the karakas are unresolved.
        pull=(Chip(label="PULL", value=f"AK {h.pull.planet} · H{h.pull.house}")
              if h.pull else None),
        vehicle=(Chip(label="VEHICLE",
                      value=f"AmK {h.vehicle.planet} · H{h.vehicle.house}")
                 if h.vehicle else None),
    )


def _section1() -> Section1:
    """The copy contract, carried with its digest so a consumer can verify the
    bytes were not paraphrased in transit."""
    return Section1(paragraphs=list(CORPUS.SECTION1_PARAGRAPHS),
                    newbie_aside=CORPUS.NEWBIE_ASIDE,
                    sha256=CORPUS.section1_digest())


def _chart_meta(f) -> ChartMeta:
    return ChartMeta(d10_lagna_sign=f.stance.d10_lagna_sign,
                     d10_lagnesh=f.stance.lagnesh.planet,
                     caption=CHART_CAPTION, dignity_key=list(DIGNITY_KEY))


# ─────────────────────────────────────────────────────────────────────────────
# §5 · the core triad
# ─────────────────────────────────────────────────────────────────────────────

def _stance(f) -> StancePublication:
    sign = f.stance.d10_lagna_sign
    c = _corpus(CORPUS.STANCE_CORPUS, sign, "stance")
    lg = f.stance.lagnesh
    return StancePublication(
        lagna_sign=sign, gloss=c["gloss"],
        lagnesh_line=f"{lg.planet} in H{lg.house} {lg.sign} · {lg.dignity}",
        work_behaviour=c["work_behaviour"], overreach=c["overreach"])


def _house_domain(n: int) -> Dict[str, str]:
    return _corpus(CORPUS.HOUSE_CORPUS, n, "house domain")


def _occupancy_line(house_no: int, occupants: List[str], lord, mode: str) -> str:
    """The format's own two forms. A vacant house opens with 'Through lord',
    which is why the mode is carried rather than inferred from the list."""
    if mode == "OCCUPIED":
        return "Occupants: " + ", ".join(occupants)
    return (f"{CORPUS.THROUGH_LORD_OPENING}: {lord.planet} in "
            f"H{lord.house} {lord.sign}")


def _function(f) -> FunctionPublication:
    h10, h6 = f.function.h10, f.function.h6
    d10, d6 = _house_domain(10), _house_domain(6)
    h10_line = _occupancy_line(10, list(h10.occupants), h10.lord, h10.mode)
    h6_line = _occupancy_line(6, list(h6.occupants), h6.lord, h6.mode)

    # "The days look like ___", derived only from the H10/H6 domains and the
    # certified placements. No job title enters: neither corpus sentence names
    # an occupation, and nothing else is consulted.
    # D10-006-CORR-01 · H6 IS CONTEXT, NOT AN ADVERSARY. The earlier wording
    # said "against {H6 domain}", which asserted a relation between H10 and H6
    # that no selector had found. H6 is the service contract the vocation runs
    # under; naming it as an opponent invented a conflict.
    if h10.mode == "THROUGH_LORD":
        days = (f"The days look like {d10['domain_sentence'][0].lower()}"
                f"{d10['domain_sentence'][1:].rstrip('.')}, reached through "
                f"{h10.lord.planet} in H{h10.lord.house} {h10.lord.sign}, "
                f"with {d6['domain_label'].lower()} setting the working "
                f"conditions.")
    else:
        days = (f"The days look like {d10['domain_sentence'][0].lower()}"
                f"{d10['domain_sentence'][1:].rstrip('.')}, carried by "
                f"{', '.join(h10.occupants)}, with "
                f"{d6['domain_label'].lower()} setting the working "
                f"conditions.")
    return FunctionPublication(h10_mode=h10.mode, h10_line=h10_line,
                               h6_line=h6_line, days_look_like=days)


def _standing(f) -> StandingPublication:
    sun = f.standing.sun
    h2_lord = f.standing.h2_lord
    tenth = f.standing.h10_lord
    d2 = _house_domain(2)
    rewarded = (f"What becomes legible is {d2['domain_sentence'][0].lower()}"
                f"{d2['domain_sentence'][1:].rstrip('.')}, with "
                f"{h2_lord.planet} in H{h2_lord.house} {h2_lord.sign} setting "
                f"the terms.")
    not_automatic = (f"Standing is not granted by the Sun's presence alone: "
                     f"{sun.dignity} in {sun.sign} describes the climate, and "
                     f"the office of the career runs through {tenth.planet} in "
                     f"H{tenth.house}.")
    return StandingPublication(
        sun_line=f"Sun in H{sun.house} {sun.sign} · {sun.dignity}",
        what_is_rewarded=rewarded, what_is_not_automatic=not_automatic)


# ─────────────────────────────────────────────────────────────────────────────
# §6 · cross-chart FACTS
# ─────────────────────────────────────────────────────────────────────────────

def _crosschart(x) -> CrossChartFacts:
    """Packaged, not interpreted. No agreement word is computed and no
    handshake sentence is written."""
    a, b = x.d1_d10.d1_h10, x.d1_d10.d10_h10
    occ = ", ".join(a.occupants) if a.occupants else "empty"
    d1_line = f"Natal 10th: {a.sign}, lord {a.lord}, occupants {occ}"
    d10_occ = ", ".join(b.occupants) if b.occupants else "empty"
    d10_line = (f"D10 10th: {b.sign}, lord {b.lord}, occupants {d10_occ} · "
                f"{CORPUS.PUBLICATION_STATE_LABEL[b.mode]} · lord in "
                f"H{b.lord_placement.house} {b.lord_placement.sign}")
    d = x.d9_d10
    delivery = (f"Delivery: {d.stance.d10_lagna_sign} stance, "
                f"{d.stance.lagnesh} in H{d.stance.lagnesh_house}; "
                f"counterparties H7 {', '.join(d.counterparty_field.occupants) or 'empty'}; "
                f"vocation H10 {CORPUS.PUBLICATION_STATE_LABEL[d.work_delivery.mode]}")
    return CrossChartFacts(
        d1_h10_line=d1_line, d10_h10_line=d10_line,
        d9_contribution_available=d.available,
        d9_contribution_mode=(d.contribution.mode if d.contribution else None),
        d10_delivery_line=delivery,
        # None when D9 published nothing. Section 6 then stays silent.
        d9_handshake_sentence=compose_d9_handshake(x))


# ─────────────────────────────────────────────────────────────────────────────
# §6 · THE D9 x D10 HANDSHAKE SENTENCE · composed ONCE, used twice
# ─────────────────────────────────────────────────────────────────────────────

#: What each accepted D9 contribution mode contributes to the sentence. The
#: contribution itself is consumed as certified; nothing about D9 is
#: recalculated and no new D9 doctrine is introduced.
#: D10-007-CORR-02 · each accepted contextual role means something different,
#: and flattening all three into "reaching the world as" promotes one into the
#: others. The role_key is the semantics; the grammar follows it.
_ROLE_GRAMMAR = {
    "functional_vector": "reaches the world through",
    "ethical_functional_vector": "is carried with",
    "aptitude_modifier": "is supported by an aptitude for",
}


def _proposition(p) -> str:
    """Title AND core impulse. D10-004 deliberately preserved both, so the
    handshake carries both: dropping the impulse to shorten a sentence is
    semantic loss, not concision."""
    return f"{p.title} — {p.core_impulse}"


def _propositions(items) -> str:
    return "; ".join(_proposition(p) for p in (items or []))


def _contribution_phrase(c) -> str:
    """One clause per accepted mode, preserving everything D10-004 retained.

    No mode is forced through another's template. Every field the normalized
    contribution can carry appears: titles and core impulses, the contextual
    role, `mature_quality`, `higher_value` and `conviction`.
    """
    if c.mode == "MATURITY_FALLBACK":
        phrase = f"a contribution that matures as {c.mature_quality}"
        if c.higher_value:
            phrase += f", held toward {c.higher_value}"
        return phrase

    if c.mode == "UNIFIED_PURPOSE":
        phrase = f"one settled contribution — {_propositions(c.primary)}"
        if c.conviction:
            phrase += f" — held as {c.conviction}"
        return phrase

    if c.mode == "PAIRWISE":
        phrase = f"a contribution of {_propositions(c.primary)}"
        cv = c.contextual_vector
        if cv is not None:
            grammar = _ROLE_GRAMMAR.get(cv.role_key)
            if grammar is None:
                # FAIL CLOSED rather than flatten an unrecognised role into a
                # known one, which would silently promote its meaning.
                raise D10PublicationError(
                    f"unrecognised D9 contextual role_key {cv.role_key!r}; "
                    f"refusing rather than flattening it into another role")
            phrase += f", which {grammar} {_propositions(cv.propositions)}"
        return phrase

    if c.mode == "COMPOUND_MULTI_POLAR":
        parts = []
        for label, items in (("impact", c.primary_impact),
                             ("ethic", c.ethical_driver),
                             ("aptitude", c.innate_aptitude)):
            if items:
                parts.append(f"{label} {_propositions(items)}")
        return "a contribution on several poles — " + "; ".join(parts)

    raise D10PublicationError(f"unhandled contribution mode {c.mode!r}")


def _article(word: str) -> str:
    """`a` or `an`, from the word itself. Generic: no sign is special-cased,
    and the same helper serves Aries, Aquarius and the other ten."""
    return "an" if word[:1].upper() in "AEIOU" else "a"


def compose_d9_handshake(crosschart) -> Optional[str]:
    """THE ONE SENTENCE. Section 6 publishes it and §14 reuses it unchanged.

    It answers exactly one question: how does the already-certified D9
    contribution get carried through the D10 work structure? It is built from
    the D10-004 handshake and nothing else — the certified contribution, the
    D10 stance, the counterparty field and the work delivery.

    Returns None when D9 published no contribution. There is NO substitute
    sentence: silence is the reading, and both consumers stay silent together
    because they share this single return value.
    """
    d = crosschart.d9_d10
    if not d.available or d.contribution is None:
        return None
    phrase = _contribution_phrase(d.contribution)
    stance = d.stance
    work = d.work_delivery
    counterparties = (", ".join(d.counterparty_field.occupants)
                      if d.counterparty_field.occupants
                      else f"the seventh through {d.counterparty_field.lord}")
    carrier = (f"{work.lord} in H{work.lord_placement.house}"
               if work.mode == "THROUGH_LORD"
               else ", ".join(work.occupants))
    return (f"D9 certifies {phrase}; in D10 that is taken up as "
            f"{_article(stance.d10_lagna_sign)} "
            f"{stance.d10_lagna_sign} stance through {stance.lagnesh} in "
            f"H{stance.lagnesh_house}, met at {counterparties}, and delivered "
            f"as work through {carrier}.")


# ─────────────────────────────────────────────────────────────────────────────
# §7 · pull and vehicle
# ─────────────────────────────────────────────────────────────────────────────

def _pull_vehicle(f) -> PullVehiclePublication:
    """JAIMINI ONLY. Nothing Parāśari is consulted, and the no-link copy is the
    format's own: they do not fail, they do not automate."""
    pv = f.pull_vehicle
    if not pv.available:
        return PullVehiclePublication(available=False,
                                      unavailable_reason=pv.unavailable_reason)
    pull = (f"AK {pv.ak.planet} in H{pv.ak.house} {pv.ak.sign} — the work this "
            f"chart keeps trying to become.")
    vehicle = (f"AmK {pv.amk.planet} in H{pv.amk.house} {pv.amk.sign} — the "
               f"instrument that actually carries a week.")
    if pv.relation_state == "SAME_HOUSE":
        link = (f"They share H{pv.ak.house}. Pull and vehicle move together "
                f"without being joined deliberately.")
        weekly = ("Which part of this week's work served the pull rather than "
                  "only the vehicle?")
    elif pv.relation_state == "MUTUAL_DRISHTI":
        link = ("They aspect one another by rāśi dṛṣṭi. The join exists and "
                "does not have to be manufactured.")
        weekly = ("Where did the pull and the week's instrument reinforce each "
                  "other without being made to?")
    else:
        link = ("No shared house and no mutual rāśi dṛṣṭi. They do not fail. "
                "They do not automate.")
        weekly = ("Which skill did this week's ordinary work actually deepen?")
    return PullVehiclePublication(available=True, vocational_pull=pull,
                                  work_vehicle=vehicle, link=link,
                                  weekly_question=weekly)


# ─────────────────────────────────────────────────────────────────────────────
# §8 · Devatā
# ─────────────────────────────────────────────────────────────────────────────

def _devata_for_slice(sign_index: int, d10_sign_index: int) -> str:
    """Read back WHICH CERTIFIED SLICE produced the certified `d10_sign_index`.

    D10-006-CORR-01 · this previously selected from the published `degree`,
    which is round(..., 4). A true 2.99996° in Aries publishes as 3.0000 and
    would have been read as the second slice while the certified
    `d10_sign_index` says the first — the same rounded-seam defect D10-002
    removed from the placement path, left behind in the Devatā path.

    This does NOT recalculate D10. The mapping is invertible: the slice is
    recovered from the two certified integers and nothing else.

        start   = sign_index          for an odd sign  (even 0-based index)
                = (sign_index + 8) % 12  for an even sign
        portion = (d10_sign_index - start) % 12

    A portion outside 0..9 means the two certified values do not belong to the
    same chart, which is a refusal rather than a clamp.

    `degree`, `longitude` and any rounded display coordinate are never read.
    """
    if type(sign_index) is not int or not 0 <= sign_index <= 11:
        raise D10PublicationError(
            f"devatā: sign_index must be an integer 0-11, got {sign_index!r}")
    if type(d10_sign_index) is not int or not 0 <= d10_sign_index <= 11:
        raise D10PublicationError(
            f"devatā: d10_sign_index must be an integer 0-11, "
            f"got {d10_sign_index!r}")
    odd_sign = (sign_index % 2 == 0)
    start = sign_index if odd_sign else (sign_index + 8) % 12
    portion = (d10_sign_index - start) % 12
    if not 0 <= portion <= 9:
        raise D10PublicationError(
            f"devatā: sign_index {sign_index} and d10_sign_index "
            f"{d10_sign_index} imply slice {portion}, which is outside 0-9; "
            f"the two certified values do not describe one placement")
    seq = CORPUS.DEVATA_ODD if odd_sign else CORPUS.DEVATA_EVEN
    return seq[portion]


def _devata(f, certified: Mapping[str, Mapping[str, Any]]) -> DevataSection:
    """PLANETARY ROWS ONLY, and exactly the nine canonical grahas.

    A missing graha and an extra one are both refusals: a Devatā table that
    silently covers eight grahas would read as a complete one.
    """
    if not isinstance(certified, Mapping):
        raise D10PublicationError("certified planets payload is not an object")
    supplied = set(certified)
    missing = set(CANONICAL_GRAHAS) - supplied
    extra = supplied - set(CANONICAL_GRAHAS)
    if missing:
        raise D10PublicationError(
            f"devatā: certified payload is missing {sorted(missing)}")
    if extra:
        raise D10PublicationError(
            f"devatā: certified payload carries unexpected {sorted(extra)}")

    placement_by_planet = {}
    for group in f.operational_map:
        for house in group.houses:
            for occupant in house.occupants:
                placement_by_planet[occupant] = house

    rows: List[DevataRow] = []
    counts: Dict[str, List[str]] = {}
    for planet in CANONICAL_GRAHAS:
        rec = certified[planet]
        if not isinstance(rec, Mapping):
            raise D10PublicationError(f"{planet}: certified record is not an object")
        for key in ("sign_index", "d10_sign_index"):
            if key not in rec:
                raise D10PublicationError(f"{planet}: certified {key} missing")
        name = _devata_for_slice(rec["sign_index"], rec["d10_sign_index"])
        placement = placement_by_planet.get(planet)
        if placement is None:
            raise D10PublicationError(f"{planet} occupies no D10 house")
        rows.append(DevataRow(planet=planet, house=placement.house,
                              sign=placement.sign, devata=name,
                              flavour=_corpus(CORPUS.DEVATA_FLAVOUR, name,
                                              "devatā flavour")))
        counts.setdefault(name, []).append(planet)

    if len(rows) != len(CANONICAL_GRAHAS):
        raise D10PublicationError(
            f"devatā: produced {len(rows)} rows, expected "
            f"{len(CANONICAL_GRAHAS)}")

    # ONE climate disclosure, not three destinies.
    disclosures = [
        (f"{name} repeats on {', '.join(sorted(planets))} — "
         f"{_corpus(CORPUS.DEVATA_FLAVOUR, name, 'devatā flavour')} is a "
         f"climate in this D10, not {len(planets)} separate destinies.")
        for name, planets in sorted(counts.items())
        if len(planets) >= CORPUS.DEVATA_REPEAT_THRESHOLD
    ]
    rows.sort(key=lambda r: r.planet)
    return DevataSection(teaching=DEVATA_TEACHING, rows=rows,
                         repeat_disclosures=disclosures)


# ─────────────────────────────────────────────────────────────────────────────
# §9 · operational map
# ─────────────────────────────────────────────────────────────────────────────

def _house_reading(house, domain: Dict[str, str]) -> str:
    """One deterministic sentence from the house corpus, the occupancy and the
    publication state. H8 and H12 stay proportionate: pressure, never curse or
    purification."""
    base = domain["domain_sentence"].rstrip(".")
    if house.publication_state == "PRESSURED":
        # D10-006-CORR-01 · NAME THE ACTUAL CAUSE. Pressure has two sources and
        # the earlier sentence blamed the lord in every case, including when the
        # lord was nowhere near a dusthāna. Each branch below is reconstructible
        # from the supplied OperationalHouse and nothing else.
        lord_cause = house.lord_house in DUSTHANA
        house_cause = house.house in DUSTHANA and bool(house.occupants)
        if lord_cause and house_cause:
            return (f"{base}. Under pressure from both directions: "
                    f"{', '.join(house.occupants)} work here in a pressure "
                    f"house, and the lord {house.lord} sits in "
                    f"H{house.lord_house} as well.")
        if lord_cause:
            return (f"{base}. Under pressure through its lord: {house.lord} "
                    f"sits in H{house.lord_house}, so this runs with a load "
                    f"on it.")
        return (f"{base}. Under pressure in place: "
                f"{', '.join(house.occupants)} work here, and this is a "
                f"pressure house.")
    if house.publication_state == "SUPPORTED":
        return (f"{base}. Well held: {house.lord} carries it from "
                f"H{house.lord_house} in {house.lord_dignity}.")
    if house.publication_state == "OCCUPIED":
        return f"{base}. Worked directly by {', '.join(house.occupants)}."
    return (f"{base}. Vacant, so the results run through {house.lord} in "
            f"H{house.lord_house}.")


def _operational_map(f) -> List[OperationalGroupPublication]:
    out = []
    for group in f.operational_map:
        lines = []
        for house in group.houses:
            domain = _house_domain(house.house)
            occ = ("Occupants: " + ", ".join(house.occupants)
                   if house.occupants
                   else f"{CORPUS.THROUGH_LORD_OPENING}: {house.lord} in "
                        f"H{house.lord_house} {house.lord_sign}")
            lines.append(HouseLine(
                house=house.house, domain_label=domain["domain_label"],
                occupancy_line=occ, status=house.publication_state,
                status_label=CORPUS.PUBLICATION_STATE_LABEL[house.publication_state],
                reading=_house_reading(house, domain)))
        out.append(OperationalGroupPublication(
            group=group.group, title=GROUP_TITLES[group.group], houses=lines))
    return out


# ─────────────────────────────────────────────────────────────────────────────
# §10 · tension
# ─────────────────────────────────────────────────────────────────────────────

def _tension(f) -> TensionPublication:
    """THE WINNER IS COPIED, NEVER CHOSEN. No predicate in this function could
    select a different one; it looks up copy for the winner it was given."""
    t = f.tension
    if t.winner == TENSION_UNKNOWN:
        return TensionPublication(available=False, winner=TENSION_UNKNOWN)
    entry = _corpus(CORPUS.TENSION_COPY, t.winner, "tension copy")
    body = entry["template"].format(**_tension_fields(f, t))
    return TensionPublication(available=True, winner=t.winner,
                              heading=entry["heading"], body=body,
                              word_count=len(body.split()),
                              is_contrast_only=(t.winner == FALLBACK))


def _tension_fields(f, t) -> Dict[str, Any]:
    """Every value comes from the selector's own recorded evidence, so the
    published sentence is recognisable from it."""
    e = dict(t.evidence)
    fields: Dict[str, Any] = {}
    if t.winner == "JAIMINI_RIFT":
        fields = {"ak": e["ak"], "ak_house": e["ak_house"],
                  "amk": e["amk"], "amk_house": e["amk_house"]}
    elif t.winner == "CORE_OPERATIONAL_CONFLICT":
        fields = {"lagnesh": e["lagnesh"], "lagnesh_house": e["lagnesh_house"],
                  "tenth_lord": e["tenth_lord"],
                  "tenth_lord_house": e["tenth_lord_house"]}
    elif t.winner == "VISIBILITY_GAP":
        fields = {"h5_count": e["h5_count"], "h12_count": e["h12_count"]}
    elif t.winner == "SUN_SATURN_FRICTION":
        fields = {"sun_house": e["sun_house"], "saturn_house": e["saturn_house"]}
    elif t.winner == FALLBACK:
        fields = {"sun_house": e["sun_house"], "sun_sign": e["sun_sign"],
                  "sun_dignity": e["sun_dignity"],
                  "saturn_house": e["saturn_house"],
                  "saturn_sign": e["saturn_sign"],
                  "saturn_dignity": e["saturn_dignity"]}
    return fields


# ─────────────────────────────────────────────────────────────────────────────
# §11 · money
# ─────────────────────────────────────────────────────────────────────────────

def _money_card(block, house_no: int, question: str) -> MoneyCard:
    occ = ("Occupants: " + ", ".join(block.occupants) if block.occupants
           else "Empty")
    mech = _corpus(CORPUS.MECHANISM_BY_LORD, block.lord.planet, "mechanism")
    note = (CORPUS.H11_EMPTY_NOTE if house_no == 11 and block.empty else None)
    return MoneyCard(house=house_no, question=question, occupancy_line=occ,
                     lord_line=(f"Lord {block.lord.planet} in "
                                f"H{block.lord.house} {block.lord.sign} · "
                                f"{block.lord.dignity}"),
                     mechanism=mech, note=note)


def _money(f) -> MoneyPublication:
    return MoneyPublication(
        h2=_money_card(f.money.h2, 2, "How earnings attach to work"),
        h11=_money_card(f.money.h11, 11, "How gains compound"))


# ─────────────────────────────────────────────────────────────────────────────
# §12 · strength
# ─────────────────────────────────────────────────────────────────────────────

def _strength(f) -> StrengthPublication:
    """This corpus does not decide who prints. D10-003's selector already did,
    and this function publishes exactly the grahas it named."""
    pairs = []
    for s in f.strength.strong_planets:
        c = _corpus(CORPUS.STRENGTH_CORPUS, s.planet, "strength pair")
        pairs.append(StrengthPair(planet=s.planet, dignity=s.dignity,
                                  house=s.house, sign=s.sign,
                                  reliable_at_work=c["reliable_at_work"],
                                  when_it_overreaches=c["when_it_overreaches"]))
    note = (None if pairs else
            "No graha reaches the strength threshold in this D10. That is a "
            "neutral reading, not a weakness.")
    return StrengthPublication(pairs=pairs, none_note=note)


# ─────────────────────────────────────────────────────────────────────────────
# §13 · instructions
# ─────────────────────────────────────────────────────────────────────────────

def _instructions(f) -> InstructionsPublication:
    """Keyed only by the tension winner. With no tension there is nothing for
    the instructions to be about, so none is invented."""
    winner = f.tension.winner
    if winner == TENSION_UNKNOWN:
        return InstructionsPublication(available=False)
    c = _corpus(CORPUS.INSTRUCTIONS_CORPUS, winner, "instructions")
    return InstructionsPublication(available=True, keyed_to=winner,
                                   cultivate=c["cultivate"], watch=c["watch"],
                                   practise=c["practise"])


# ─────────────────────────────────────────────────────────────────────────────
# the one public entry point
# ─────────────────────────────────────────────────────────────────────────────

class ChartIdentityMismatch(D10PublicationError):
    """Two layers describe different charts. Raised before any fact is read, so
    no partial publication can exist."""


def build_publication(findings, crosschart,
                      certified_chart: Mapping[str, Any]) -> D10Publication:
    """Compose the deterministic customer publication.

    `findings`    a D10-003 `D10CoreFindings`
    `crosschart`  a D10-004 `D10CrossChartFindings`
    `certified_chart` the certified `/chart` snapshot — the whole response,
                  carrying `chart_token` and `planets`. Its planets are read
                  ONLY for `sign_index` and `d10_sign_index`. The Devatā slice is read
                  back from those two certified integers; no degree, longitude
                  or rounded display coordinate is consulted, and no D10 fact
                  is recomputed here.
    """
    # D10-007-CORR-01 · IDENTITY IS CLOSED BEFORE ANY FACT IS READ.
    # The snapshot is the certified /chart response, NOT a naked planets dict:
    # a bare mapping of grahas carries no identity, so nothing could be checked
    # against it and a publication could be assembled from two charts.
    if not isinstance(certified_chart, Mapping):
        raise D10PublicationError("certified chart snapshot is not an object")
    chart_token = certified_chart.get("chart_token")
    if not isinstance(chart_token, str) or not chart_token:
        raise D10PublicationError(
            "certified chart snapshot carries no chart_token; a naked planets "
            "mapping cannot be published from because it has no identity")
    planets = certified_chart.get("planets")
    if not isinstance(planets, Mapping):
        raise D10PublicationError("certified chart snapshot has no planets")

    for a_name, a, b_name, b in (
            ("findings", findings.chart_token, "crosschart", crosschart.chart_token),
            ("findings", findings.chart_token, "certified chart", chart_token),
            ("crosschart", crosschart.chart_token, "certified chart", chart_token)):
        if a != b:
            raise ChartIdentityMismatch(
                f"{a_name} and {b_name} chart tokens differ ({a!r} vs {b!r}); "
                f"refusing to publish a report assembled from two charts")

    return D10Publication(
        chart_token=chart_token,
        header=_header(findings),
        section1=_section1(),
        section2=Section2(steps=[ReadingStep(**s) for s in CORPUS.READING_PATH],
                          rule=CORPUS.READING_PATH_RULE),
        chart_meta=_chart_meta(findings),
        permitted_questions=[PermittedQuestion(**q)
                             for q in CORPUS.PERMITTED_QUESTIONS],
        stance=_stance(findings),
        function=_function(findings),
        standing=_standing(findings),
        crosschart_facts=_crosschart(crosschart),
        pull_vehicle=_pull_vehicle(findings),
        devata=_devata(findings, planets),
        operational_map=_operational_map(findings),
        tension=_tension(findings),
        money=_money(findings),
        strength=_strength(findings),
        instructions=_instructions(findings),
        how_to_use=list(CORPUS.HOW_TO_USE),
        glossary=[GlossaryEntry(**g) for g in CORPUS.GLOSSARY],
    )
