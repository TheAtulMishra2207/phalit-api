"""D7-002-CORR-02 · FD-1B mechanical predicates, spec E, exactly as written.

Every definition below is the ticket's formula. Nothing is generalised, and no
"number of malefic contacts" substitute survives anywhere.

THE NODE CONSTRAINT IS STRUCTURAL, NOT A CONVENTION.
Every aspect test routes through `aspects_house` / `aspects_body`, which return
False for Rahu and Ketu at the single chokepoint in `aspected_houses`. So every
`Aspected_By(... Rahu | Ketu ...)` branch below is dead by construction, exactly
as the ticket requires. Node OCCUPANCY and CONJUNCTION remain fully live and
several predicates depend on them.

UNAVAILABLE IS A REAL ANSWER.
`stable_dignity` returns None when the only category that could still qualify is
Great_Friend, which needs a compound (natural + temporal) friendship table that
the certified doctrine surface does not carry. The ticket forbids substituting
Friendly, so the predicate reports unavailable instead of guessing.
"""

from typing import Any, Dict, List, Optional

from d7_predicates import (  # noqa: F401
    NODES,
    aspects_body,
    aspects_house,
    conjunct,
    natural_relationship,
    occupies,
)
from d7_predicates import _doctrine as _pred_doctrine

# Spec E, verbatim.
NATURAL_MALEFICS = ("Sun", "Mars", "Saturn", "Rahu", "Ketu")
HEAVY_MALEFICS = ("Saturn", "Rahu", "Ketu")
MILD_MALEFICS = ("Sun", "Mars")
DUSTHANAS = (6, 8, 12)
KENDRAS = (1, 4, 7, 10)
TRIKONAS = (1, 5, 9)

# Spec E · Standard_5L_Placement house set, verbatim.
STANDARD_5L_HOUSES = frozenset({1, 2, 4, 5, 7, 9, 10, 11})

# Spec E · Vayu_Dominant counts only these four bodies, in these three signs.
# Ocean element labels are explicitly NOT a substitute.
VAYU_SIGN_INDICES = frozenset({2, 6, 10})          # Gemini, Libra, Aquarius
VAYU_COUNTED_ROLES = ("d7_lagna_lord", "d7_5l", "Jupiter", "Sun")

# Spec E · Malefic_Axis_Touching house set, verbatim.
AXIS_HOUSES = frozenset({1, 5, 7, 11})


# ─── dignity categories, read from certified data where it exists ────────────

def is_combust(body: str, planets: Dict[str, Any]) -> bool:
    """Certified combustion. /chart computes it; D7 never recomputes an orb."""
    rec = planets.get(body) or {}
    return bool(rec.get("combust"))


def is_vargottama(body: str, planets: Dict[str, Any]) -> bool:
    """Certified vargottama flag from the snapshot."""
    rec = planets.get(body) or {}
    return bool(rec.get("vargottama"))


def is_exalted(body: str, d7_sign_index: int) -> bool:
    return _pred_doctrine().exaltation_sign.get(body) == d7_sign_index


def is_debilitated(body: str, d7_sign_index: int) -> bool:
    return _pred_doctrine().debilitation_sign.get(body) == d7_sign_index


def is_own_sign(body: str, d7_sign_index: int) -> bool:
    return d7_sign_index in (_pred_doctrine().own_signs.get(body) or [])


def is_moolatrikona(body: str, d7_sign_index: int) -> bool:
    """Sign-level moolatrikona.

    The certified table is (sign, min_deg, max_deg), but a divisional placement
    has no meaningful degree inside its varga sign, so only the SIGN is tested.
    That is the same limit D4 recorded as `varga_moolatrikona_policy`.
    """
    table = _pred_doctrine().moolatrikona or {}
    entry = table.get(body)
    if not entry:
        return False
    return entry[0] == d7_sign_index


def is_great_friend(body: str, d7_sign_index: int) -> Optional[bool]:
    """Great Friend (Adhi Mitra) needs compound natural+temporal friendship.

    The injected doctrine carries natural friendship only, so this is
    UNAVAILABLE rather than approximated by the natural table. Returning
    `Friend` here is precisely the substitution the ticket forbids.
    """
    return None


# ─── FD-1B · Well_Placed ─────────────────────────────────────────────────────

def well_placed(body: str, facts: Dict[str, Any], planets: Dict[str, Any]) -> bool:
    """(Exalted OR Own OR Moolatrikona OR Vargottama)
       AND NOT (Combust OR Debilitated OR in 6/8/12)."""
    rec = (facts["placements"] or {}).get(body)
    if not rec:
        return False
    si = rec["d7_sign_index"]
    positive = (is_exalted(body, si) or is_own_sign(body, si)
                or is_moolatrikona(body, si) or is_vargottama(body, planets))
    if not positive:
        return False
    negative = (is_combust(body, planets) or is_debilitated(body, si)
                or rec["house"] in DUSTHANAS)
    return not negative


# ─── FD-1B · Afflicted ───────────────────────────────────────────────────────

def resides_with_malefic(body: str, placements: Dict[str, Any]) -> bool:
    return any(m != body and conjunct(m, body, placements) for m in NATURAL_MALEFICS)


def aspected_by_malefic(body: str, placements: Dict[str, Any]) -> bool:
    """Rahu and Ketu can never satisfy this: they are refused at the chokepoint."""
    return any(m != body and aspects_body(m, body, placements) for m in NATURAL_MALEFICS)


def afflicted(body: str, facts: Dict[str, Any], planets: Dict[str, Any]) -> bool:
    """Resides_With(malefic) OR Aspected_By(malefic) OR Combust OR Debilitated."""
    rec = (facts["placements"] or {}).get(body)
    if not rec:
        return False
    pl = facts["placements"]
    return bool(resides_with_malefic(body, pl)
                or aspected_by_malefic(body, pl)
                or is_combust(body, planets)
                or is_debilitated(body, rec["d7_sign_index"]))


def house_resides_with_malefic(house: int, placements: Dict[str, Any]) -> bool:
    return any(occupies(m, house, placements) for m in NATURAL_MALEFICS)


def house_aspected_by_malefic(house: int, placements: Dict[str, Any]) -> bool:
    return any(aspects_house(m, house, placements) for m in NATURAL_MALEFICS)


def house_afflicted(house: int, placements: Dict[str, Any]) -> bool:
    return house_resides_with_malefic(house, placements) or \
        house_aspected_by_malefic(house, placements)


# ─── FD-1B · Mild_Malefic_Aspect ─────────────────────────────────────────────

def mild_malefic_aspect(house: int, placements: Dict[str, Any]) -> bool:
    """Aspected_By(Sun OR Mars)
       AND NOT Aspected_By(Saturn OR Rahu OR Ketu)
       AND NOT Resides_With(Natural_Malefic).

    The Rahu/Ketu half of the second clause is structurally false, so in
    practice the exclusion turns on Saturn. That is a consequence of the locked
    node doctrine, not a simplification of the formula.
    """
    mild = any(aspects_house(m, house, placements) for m in MILD_MALEFICS)
    if not mild:
        return False
    heavy = any(aspects_house(m, house, placements) for m in HEAVY_MALEFICS)
    if heavy:
        return False
    return not house_resides_with_malefic(house, placements)


# ─── FD-1B · Heavy_Malefic_Affliction ────────────────────────────────────────

def heavy_malefic_affliction(house: int, placements: Dict[str, Any]) -> bool:
    """Resides_With(Sat/Rahu/Ketu) OR Aspected_By(Sat/Rahu/Ketu) OR in 6/8/12."""
    if any(occupies(m, house, placements) for m in HEAVY_MALEFICS):
        return True
    if any(aspects_house(m, house, placements) for m in HEAVY_MALEFICS):
        return True
    return house in DUSTHANAS


def heavy_malefic_affliction_body(body: str, placements: Dict[str, Any]) -> bool:
    rec = placements.get(body)
    if not rec:
        return False
    if any(m != body and conjunct(m, body, placements) for m in HEAVY_MALEFICS):
        return True
    if any(m != body and aspects_body(m, body, placements) for m in HEAVY_MALEFICS):
        return True
    return rec["house"] in DUSTHANAS


# ─── FD-1B · Benefic_Relief ──────────────────────────────────────────────────

def unassociated_mercury(placements: Dict[str, Any]) -> bool:
    """Mercury is a natural benefic only when unassociated with a malefic."""
    if "Mercury" not in placements:
        return False
    return not any(m != "Mercury" and conjunct(m, "Mercury", placements)
                   for m in NATURAL_MALEFICS)


def natural_benefics(placements: Dict[str, Any]) -> List[str]:
    out = [b for b in ("Jupiter", "Venus") if b in placements]
    if unassociated_mercury(placements):
        out.append("Mercury")
    return out


def benefic_relief(house: int, placements: Dict[str, Any]) -> bool:
    """Resides_With(Benefic) OR Aspected_By_Graha(Benefic).

    Graha drishti only. The Founder phrase `Aspected_By_Rashi` does NOT
    authorise a Jaimini system, and none is introduced anywhere in D7.
    """
    for b in natural_benefics(placements):
        if occupies(b, house, placements) or aspects_house(b, house, placements):
            return True
    return False


def benefic_relief_body(body: str, placements: Dict[str, Any]) -> bool:
    for b in natural_benefics(placements):
        if b == body:
            continue
        if conjunct(b, body, placements) or aspects_body(b, body, placements):
            return True
    return False


# ─── FD-1B · Standard_5L_Placement ───────────────────────────────────────────

def standard_5l_placement(facts: Dict[str, Any], planets: Dict[str, Any]) -> bool:
    """5L house IN {1,2,4,5,7,9,10,11} AND NOT Debilitated AND NOT Combust."""
    lord = facts["key_houses"]["h5"]["lord"]
    rec = (facts["placements"] or {}).get(lord)
    if not rec:
        return False
    if rec["house"] not in STANDARD_5L_HOUSES:
        return False
    if is_debilitated(lord, rec["d7_sign_index"]):
        return False
    return not is_combust(lord, planets)


# ─── FD-1B · Stable_Dignity ──────────────────────────────────────────────────

def stable_dignity(body: str, facts: Dict[str, Any]) -> Optional[bool]:
    """Exalted OR Moolatrikona OR Own_Sign OR Great_Friend_Sign.

    THREE-VALUED, and the False branch is load-bearing:

      True  · Exalted, Moolatrikona or Own sign
      False · DEFINITIVELY not stable — debilitated, or in a natural enemy's
              sign. Neither can be a Great_Friend sign under any temporal
              friendship, so no compound table is needed to rule them out.
      None  · UNAVAILABLE — none of the three holds and the sign's lord is a
              natural friend or neutral, so Great_Friend remains possible and
              the compound table the certified doctrine lacks would be required
              to decide.

    Returning True here on a natural-friend sign would be the Friendly
    substitution the ticket forbids.
    """
    rec = (facts["placements"] or {}).get(body)
    if not rec:
        return None
    si = rec["d7_sign_index"]
    if is_exalted(body, si) or is_moolatrikona(body, si) or is_own_sign(body, si):
        return True
    if is_debilitated(body, si):
        return False
    if natural_relationship(body, _pred_doctrine_sign_lord(si)) == "Enemy":
        return False
    return None


def _pred_doctrine_sign_lord(sign_index: int) -> str:
    """Sign lord from the injected doctrine. No local table."""
    from d7_predicates import _doctrine as _d
    doc = _d()
    lords = getattr(doc, "sign_lords", None)
    if lords:
        return lords[sign_index]
    # d7_predicates carries no sign_lords; read it from the engine doctrine.
    import d7_engine
    return d7_engine._doctrine().sign_lords[sign_index]


# ─── FD-1B · Secondary_Line_Activation ───────────────────────────────────────

def secondary_line_activation(facts: Dict[str, Any]) -> bool:
    """Slot-1 occupant in {Rahu,Ketu,Saturn}
       AND (H9 or H11 occupied by Jupiter/9L/11L
            OR H9 or H11 receiving their accepted graha drishti)."""
    pl = facts["placements"]
    slots = facts["sequence"]
    slot1 = slots[0]["occupants"] if slots else []
    if not any(o in ("Rahu", "Ketu", "Saturn") for o in slot1):
        return False
    lord9 = facts["key_houses"]["h9"]["lord"]
    lord11 = facts["houses"][10]["lord"]
    actors = {"Jupiter", lord9, lord11}
    for h in (9, 11):
        for a in actors:
            if occupies(a, h, pl) or aspects_house(a, h, pl):
                return True
    return False


# ─── FD-1B · Vayu_Dominant ───────────────────────────────────────────────────

def vayu_dominant(facts: Dict[str, Any]) -> bool:
    """Count ONLY D7 Lagna Lord, D7 5L, Jupiter, Sun in Gemini/Libra/Aquarius.
       True when the count is 2 or more. Ocean labels are NOT used."""
    pl = facts["placements"]
    bodies = [facts["d7_lagna"]["lord"], facts["key_houses"]["h5"]["lord"],
              "Jupiter", "Sun"]
    count = 0
    for b in bodies:
        rec = pl.get(b)
        if rec and rec["d7_sign_index"] in VAYU_SIGN_INDICES:
            count += 1
    return count >= 2


# ─── FD-1B · Malefic_Axis_Touching ───────────────────────────────────────────

def malefic_axis_touching(facts: Dict[str, Any]) -> bool:
    """(Rahu AND Ketu both in {1,5,7,11}) OR (Saturn AND Mars both in {1,5,7,11}).
       No 'number of malefic contacts' substitute exists anywhere."""
    pl = facts["placements"]

    def _h(b):
        rec = pl.get(b)
        return rec["house"] if rec else None

    nodes = _h("Rahu") in AXIS_HOUSES and _h("Ketu") in AXIS_HOUSES
    satmars = _h("Saturn") in AXIS_HOUSES and _h("Mars") in AXIS_HOUSES
    return bool(nodes or satmars)


# ─── influence · the shared 'touches' primitive ──────────────────────────────

def influences_house(body: str, house: int, placements: Dict[str, Any]) -> bool:
    """Occupancy OR accepted graha drishti. Nodes cannot satisfy the drishti half."""
    return occupies(body, house, placements) or aspects_house(body, house, placements)


def influences_body(source: str, target: str, placements: Dict[str, Any]) -> bool:
    """Conjunction OR accepted graha drishti. Nodes cannot satisfy the drishti half."""
    return conjunct(source, target, placements) or aspects_body(source, target, placements)


def influences_5h_or_5l(body: str, facts: Dict[str, Any]) -> bool:
    pl = facts["placements"]
    lord5 = facts["key_houses"]["h5"]["lord"]
    return influences_house(body, 5, pl) or influences_body(body, lord5, pl)


# ─── CORR-03 · D · stability of the CLEAN SLOT lords ────────────────────────

def clean_slot_lords_stable(facts: Dict[str, Any]) -> Optional[bool]:
    """Stable_Dignity of the lord of each qualifying clean Sequence Slot.

    A clean slot is one carrying no Rahu, Ketu or Saturn. The relevant lord is
    that slot's own house lord, never a universal fifth-lord proxy.

    Three-valued, deliberately:
      True  · every clean slot lord holds stable dignity
      False · at least one clean slot lord does not
      None  · a required dignity is UNAVAILABLE (Great_Friend is the only
              category that could still qualify and the certified doctrine
              surface does not carry it)

    None is returned only when no clean slot lord has already answered False,
    so an unavailable dignity cannot mask a definite negative.
    """
    slots = facts["sequence"]
    clean = [sl for sl in slots
             if not any(o in ("Rahu", "Ketu", "Saturn") for o in sl["occupants"])]
    if not clean:
        return False
    results = []
    for sl in clean:
        lord = sl.get("house_lord")
        if lord is None:
            house = sl["house"]
            lord = facts["houses"][house - 1]["lord"]
        results.append(stable_dignity(lord, facts))
    if any(r is False for r in results):
        return False
    if any(r is None for r in results):
        return None
    return True


# ─── CORR-04 · terms the atomic clause registry needs ───────────────────────

def sphuta_house(facts: Dict[str, Any]) -> int:
    """Whole-sign house of the active Sphuta point from the D7 lagna."""
    return ((facts["sphuta"]["sign_index"]
             - facts["d7_lagna"]["sign_index"]) % 12) + 1


def on_five_or_sphuta(body: str, facts: Dict[str, Any],
                      occupancy_only: bool = False) -> bool:
    """`occupies or graha-aspects D7 5H, D7 5L or the Sphuta point`.

    With `occupancy_only=True` the aspect half is dropped entirely, which is how
    the Founder's Rahu clause is expressed: the node aspect branch is
    structurally false, so only occupancy and conjunction remain.
    """
    pl = facts["placements"]
    lord5 = facts["key_houses"]["h5"]["lord"]
    sh = sphuta_house(facts)
    if occupancy_only:
        return bool(occupies(body, 5, pl) or conjunct(body, lord5, pl)
                    or occupies(body, sh, pl))
    return bool(influences_house(body, 5, pl) or influences_body(body, lord5, pl)
                or influences_house(body, sh, pl))


def saturn_drishti_on_slot(facts: Dict[str, Any], slot_index: int = 0) -> bool:
    """Saturn's accepted graha drishti landing on a Sequence Slot's house."""
    slots = facts["sequence"]
    if slot_index >= len(slots):
        return False
    return aspects_house("Saturn", slots[slot_index]["house"], facts["placements"])


def _early_slot_occupants(facts: Dict[str, Any]) -> List[str]:
    """Occupants of Sequence Slots 1 and 2."""
    out: List[str] = []
    for sl in facts["sequence"][:2]:
        out.extend(sl["occupants"])
    return out


def node_in_early_slot(facts: Dict[str, Any]) -> bool:
    return any(o in ("Rahu", "Ketu") for o in _early_slot_occupants(facts))


def saturn_in_early_slot(facts: Dict[str, Any]) -> bool:
    return "Saturn" in _early_slot_occupants(facts)


def resides_with_or_aspects_body(source: str, target: str,
                                 placements: Dict[str, Any]) -> bool:
    """`resides with or graha-aspects` — the D7_BND_A3 primitive."""
    return influences_body(source, target, placements)


def dusthana_lord_on_progeny_axis(facts: Dict[str, Any]) -> bool:
    """D7 6L, 8L or 12L OCCUPIES D7 5H, or CONJUNCTS D7 5L. No aspect branch."""
    pl = facts["placements"]
    lord5 = facts["key_houses"]["h5"]["lord"]
    for h in (6, 8, 12):
        lord = facts["houses"][h - 1]["lord"]
        if occupies(lord, 5, pl) or conjunct(lord, lord5, pl):
            return True
    return False


def heavy_ketu_saturn_affliction_of_5h(facts: Dict[str, Any]) -> bool:
    """5H heavily afflicted specifically by Ketu or Saturn.

    Ketu enters by OCCUPANCY only; Saturn may also reach by graha drishti.
    """
    pl = facts["placements"]
    return bool(occupies("Ketu", 5, pl)
                or occupies("Saturn", 5, pl)
                or aspects_house("Saturn", 5, pl))


# ─── CORR-05 · exact FD-1E atomic primitives ────────────────────────────────
#
# Each of these exists because a Founder clause states a condition that the
# GENERIC FD-1B predicate does not express. Reusing the generic predicate in
# those places both added conditions the Founder did not specify and dropped one
# the Founder did. They are separate functions so the difference is visible.

FD1E_JUPITER_HOUSES = frozenset({1, 4, 5, 7, 9, 10})   # Kendra ∪ Trikona


def lagna_lord_fd1e_unafflicted(facts: Dict[str, Any]) -> bool:
    """FD-1E · D7 Lagna Lord is Unafflicted.

        house NOT IN {6,8,12}  AND  NOT Aspected_By(Natural_Malefic)

    Deliberately NOT the generic `Afflicted` negation. Generic Afflicted covers
    conjunction, aspect, combustion and debilitation but says nothing about
    residence in 6/8/12. The Founder condition is the other way round: it names
    the dusthana residence and the aspect, and nothing else.
    """
    lord = facts["d7_lagna"]["lord"]
    pl = facts["placements"]
    rec = pl.get(lord)
    if not rec:
        return False
    if rec["house"] in DUSTHANAS:
        return False
    return not aspected_by_malefic(lord, pl)


def jupiter_fd1e_well_placed(facts: Dict[str, Any]) -> bool:
    """FD-1E · Jupiter Well-Placed in D7 = Kendra/Trikona OR Own OR Exalted.

    Kendra/Trikona is SUFFICIENT on its own. The generic `well_placed` would
    veto a Jupiter sitting cleanly in an ordinary kendra because it demands a
    dignity positive, which is not what this clause says.
    """
    rec = facts["placements"].get("Jupiter")
    if not rec:
        return False
    si = rec["d7_sign_index"]
    return bool(rec["house"] in FD1E_JUPITER_HOUSES
                or is_own_sign("Jupiter", si)
                or is_exalted("Jupiter", si))


def malefic_aspect_on_house(house: int, placements: Dict[str, Any]) -> bool:
    """ASPECT ONLY. Occupancy is deliberately excluded.

    Nodes cannot satisfy this: they are refused at the aspect chokepoint.
    """
    return house_aspected_by_malefic(house, placements)


def malefic_aspect_on_lagna_or_5h(facts: Dict[str, Any]) -> bool:
    """FD-2A High Vitality reads `no malefic ASPECT on D7 Lagna or 5H`.

    The broader `house_afflicted` includes occupancy, so a malefic merely
    sitting in the lagna blocked High Vitality against the Founder wording.
    """
    pl = facts["placements"]
    return malefic_aspect_on_house(1, pl) or malefic_aspect_on_house(5, pl)


# ─── the assembled FD-1B surface ─────────────────────────────────────────────

def build_fd1b_surface(facts: Dict[str, Any],
                       planets: Dict[str, Any]) -> Dict[str, Any]:
    pl = facts["placements"]
    lord5 = facts["key_houses"]["h5"]["lord"]
    lord9 = facts["key_houses"]["h9"]["lord"]
    lord7 = facts["key_houses"]["h7"]["lord"]
    lord6 = facts["key_houses"]["h6"]["lord"]
    lord8 = facts["houses"][7]["lord"]
    lord12 = facts["key_houses"]["h12"]["lord"]
    lagna_lord = facts["d7_lagna"]["lord"]
    sph = facts["sphuta"]

    slots = facts["sequence"]
    slot_occ = [s["occupants"] for s in slots]

    def _clean(occ):
        return not any(o in ("Rahu", "Ketu", "Saturn") for o in occ)

    unbroken = 0
    for occ in slot_occ:
        if _clean(occ):
            unbroken += 1
        else:
            break
    clean_slots = sum(1 for occ in slot_occ if _clean(occ))

    return {
        # well placed
        "well_placed_lagna_lord": well_placed(lagna_lord, facts, planets),
        "well_placed_5l": well_placed(lord5, facts, planets),
        "well_placed_jupiter": well_placed("Jupiter", facts, planets),
        # affliction
        "afflicted_lagna_lord": afflicted(lagna_lord, facts, planets),
        "afflicted_5l": afflicted(lord5, facts, planets),
        "afflicted_jupiter": afflicted("Jupiter", facts, planets),
        "afflicted_5h": house_afflicted(5, pl),
        "afflicted_sphuta": house_afflicted(
            ((sph["sign_index"] - facts["d7_lagna"]["sign_index"]) % 12) + 1, pl),
        "mild_malefic_aspect_5h": mild_malefic_aspect(5, pl),
        "heavy_affliction_5h": heavy_malefic_affliction(5, pl),
        # relief
        "benefic_relief_5h": benefic_relief(5, pl),
        "benefic_relief_5l": benefic_relief_body(lord5, pl),
        # placement and dignity
        "standard_5l_placement": standard_5l_placement(facts, planets),
        "stable_dignity_5l": stable_dignity(lord5, facts),
        "clean_slot_lords_stable": clean_slot_lords_stable(facts),
        "stable_dignity_lagna_lord": stable_dignity(lagna_lord, facts),
        "lagna_lord_combust": is_combust(lagna_lord, planets),
        "lagna_lord_debilitated": is_debilitated(
            lagna_lord, pl[lagna_lord]["d7_sign_index"]) if lagna_lord in pl else False,
        "lagna_lord_in_kendra_trikona": (
            pl[lagna_lord]["house"] in (set(KENDRAS) | set(TRIKONAS))
            if lagna_lord in pl else False),
        # sequence
        "unbroken_slots": unbroken,
        "clean_slots": clean_slots,
        "slot1_or_2_blocked": any(
            not _clean(occ) for occ in slot_occ[:2]),
        "secondary_line_activation": secondary_line_activation(facts),
        # vayu / axis
        "vayu_dominant": vayu_dominant(facts),
        "malefic_axis_touching": malefic_axis_touching(facts),
        # sphuta
        "sphuta_optimal_polarity": bool(sph["favourable"]),
        "sphuta_in_saturnian_sign": sph["sign_index"] in (9, 10),
        "male_beeja_in_even_sign": (sph["label"] == "Beeja Sphuta"
                                    and sph["parity"] == "even"),
        # per-graha influence on the progeny axis
        "influence_5_sun": influences_5h_or_5l("Sun", facts),
        "influence_5_jupiter": influences_5h_or_5l("Jupiter", facts),
        "influence_5_9l": influences_5h_or_5l(lord9, facts),
        "influence_5_mercury": influences_5h_or_5l("Mercury", facts),
        "influence_5_mars": influences_5h_or_5l("Mars", facts),
        "influence_5_moon": influences_5h_or_5l("Moon", facts),
        "influence_5_venus": influences_5h_or_5l("Venus", facts),
        "influence_5_saturn": influences_5h_or_5l("Saturn", facts),
        "influence_5_6l": influences_5h_or_5l(lord6, facts),
        "influence_5_8l": influences_5h_or_5l(lord8, facts),
        "influence_5_12l": influences_5h_or_5l(lord12, facts),
        # nodes, occupancy-only branches
        #
        # CORR-04 · `node_conjunct_5l` and `node_conjunct_pk` are REMOVED from
        # the surface. They existed only as stand-ins for the Founder's node
        # ASPECT branch, which is structurally non-firing under locked doctrine,
        # and no Founder-locked rule genuinely needs them. Conjunction is not a
        # substitute for a forbidden aspect.
        "node_occupies_5h": occupies("Rahu", 5, pl) or occupies("Ketu", 5, pl),
        "ketu_or_saturn_afflicts_5h": heavy_ketu_saturn_affliction_of_5h(facts),

        # CORR-04 · atomic clause terms
        "sphuta_house": sphuta_house(facts),
        "mars_on_5_or_sphuta": on_five_or_sphuta("Mars", facts),
        "rahu_on_5_or_sphuta": on_five_or_sphuta("Rahu", facts, occupancy_only=True),
        "node_aspect_on_pk_or_5l": (aspects_body("Rahu", "Jupiter", pl)
                                    or aspects_body("Ketu", "Jupiter", pl)
                                    or aspects_body("Rahu", lord5, pl)
                                    or aspects_body("Ketu", lord5, pl)),
        "saturn_drishti_on_slot1": saturn_drishti_on_slot(facts, 0),
        "node_in_early_slot": node_in_early_slot(facts),
        "saturn_in_early_slot": saturn_in_early_slot(facts),
        "ninth_lord_on_5l": resides_with_or_aspects_body(lord9, lord5, pl),
        "dusthana_lord_on_progeny_axis": dusthana_lord_on_progeny_axis(facts),
        # saturn / sun on the 5th axis, used by the snapshot waterfall
        "saturn_aspects_lagna_or_5h": (aspects_house("Saturn", 1, pl)
                                       or aspects_house("Saturn", 5, pl)),
        "saturn_aspects_5h_or_5l": (aspects_house("Saturn", 5, pl)
                                    or aspects_body("Saturn", lord5, pl)),
        "sun_aspects_5h_or_5l": (aspects_house("Sun", 5, pl)
                                 or aspects_body("Sun", lord5, pl)),
        "saturn_in_5h": occupies("Saturn", 5, pl),
        "saturn_rules_5h": lord5 == "Saturn",
        "jupiter_venus_benefic_aspect_5h": (aspects_house("Jupiter", 5, pl)
                                            or aspects_house("Venus", 5, pl)),
        # Retained for any consumer that genuinely wants occupancy-or-aspect.
        "malefic_on_lagna_or_5h": (house_afflicted(1, pl) or house_afflicted(5, pl)),
        # CORR-05 · ASPECT ONLY. This is what FD-2A High Vitality reads.
        "malefic_aspect_on_lagna_or_5h": malefic_aspect_on_lagna_or_5h(facts),
        # CORR-05 · exact FD-1E atomic primitives
        "lagna_lord_fd1e_unafflicted": lagna_lord_fd1e_unafflicted(facts),
        "jupiter_fd1e_well_placed": jupiter_fd1e_well_placed(facts),
        "malefic_in_h6_or_h12": (house_resides_with_malefic(6, pl)
                                 or house_resides_with_malefic(12, pl)),
    }
