"""
d4_property_state.py — D4-003 · DETERMINISTIC FIVE-STATE PROPERTY ENGINE.

Pure. No I/O, no birth data, no provider output, no astronomy. It consumes the
already-certified D4 mechanical facts from `d4_core.build_d4_facts()`, the
minimum D1 root facts needed for Lock 4, and the injected doctrine. The
provider has ZERO classification authority: nothing here asks a model anything,
and nothing a model returns can reach a predicate.

NO SECOND ENGINE. Aspects are read from the certified `aspects.edges` manifest
that d4_core already produced. This module builds no aspect table, no
sign-lord table and no modality corpus — modality is derived mechanically by
sign index exactly as the ticket specifies.

──────────────────────────────────────────────────────────────────────────────
TWO MECHANICAL EDGES THE LOCKS DO NOT COVER. Both are made explicit, versioned
policy fields rather than silent choices, and both are reported for ruling.

  * `self_conjunction_policy = "excluded"`.
    Conjunction is defined as "same D4 house/sign". Taken literally, every
    graha shares a house with itself, so the 4th Lord would conjoin itself, the
    8th Lord would conjoin the 4th Lord whenever they are the same graha, and a
    benefic 4th Lord would auto-count as contacting itself. Conjunction here
    therefore requires TWO DISTINCT grahas. Occupancy and aspect are unaffected:
    a 4th Lord sitting in H4 still contacts H4, and a graha that also lords H8
    still contributes every other involvement path.

  * `same_graha_lordship` is EXPOSED, not resolved away.
    One graha can lord two of H4/H6/H8/H12 (Mars lords Aries and Scorpio, and
    so on). Where that collapses a condition to a self-test, the condition is
    reported false under the policy above and the coincidence is published as
    evidence so a reader can see why.

ONE OBSERVATION, IMPLEMENTED AS WRITTEN RATHER THAN "CORRECTED":
  Lock 4 affliction reason 3 ("4L conjoins a Natural Malefic that is itself
  occupying H6/H8/H12") is LOGICALLY SUBSUMED by reason 1 ("4L occupies
  H6/H8/H12"), because conjunction means same house: if the malefic is in a
  dusthana and shares the 4L's house, the 4L is in that dusthana too. Reason 3
  can therefore never fire alone. It is implemented exactly as specified and
  its evidence is kept separate; the redundancy is reported, not silently
  removed.
──────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

D4_PROPERTY_STATE_VERSION = "1.0.0"

# ── Lock 1 sets ──────────────────────────────────────────────────────────────
BENEFIC_BASE_SET = ("Jupiter", "Venus", "Moon", "Mercury")
NATURAL_MALEFIC_SET = ("Sun", "Mars", "Saturn", "Rahu", "Ketu")

#: P1's trigger set is NOT the Lock-1 malefic set. The Founder's P1 trigger is
#: Saturn/Mars/Rahu/Ketu, and Sun is deliberately absent. Sun still counts in
#: the Lock-1 comparison, in Mercury disqualification and in Lock-4 reason 3.
P1_AFFLICTING_SET = ("Saturn", "Mars", "Rahu", "Ketu")

KENDRA_HOUSES = (1, 4, 7, 10)
TRIKONA_HOUSES = (1, 5, 9)
DUSTHANA_HOUSES = (6, 8, 12)

DIGNITY_SWA = "Own Sign (Swa)"
DIGNITY_UCCHA = "Exalted (Uccha)"
DIGNITY_MOOLATRIKONA = "Moolatrikona"
#: Lock 4. Mitra and Sama do NOT qualify.
D1_DIGNIFIED_LABELS = (DIGNITY_UCCHA, DIGNITY_MOOLATRIKONA, DIGNITY_SWA)
#: D4 dignity qualifying labels for P2 / P3 / Mars strength.
D4_STRONG_DIGNITY_LABELS = (DIGNITY_SWA, DIGNITY_UCCHA)

STATE_CATEGORIES = {
    "P1": ("Pratibandha_Vivada_Yoga", "Asset Friction / Encumbered Assets"),
    "P2": ("Bahu_Kshetra_Yoga", "High Multi-Property Potential"),
    "P3": ("Cala_Asthira_Sampatti", "Dynamic / Mobile Assets"),
    "P4": ("Sthira_Sampatti_Yoga", "Stable Tangible Asset Retention"),
    "P5": ("Sadharna_Simita_Sampatti", "Moderate Functional Base"),
}
PRECEDENCE = ("P1", "P2", "P3", "P4")


class D4PropertyStateError(ValueError):
    """Inputs are not the certified facts this engine requires. Internal only —
    the route converts it to a neutral correlated error and never publishes it."""


# ── modality, derived mechanically, no corpus ───────────────────────────────

def sign_modality(sign_index: int) -> str:
    if not isinstance(sign_index, int) or isinstance(sign_index, bool) or not 0 <= sign_index <= 11:
        raise D4PropertyStateError("sign index out of range")
    return ("Movable", "Fixed", "Dual")[sign_index % 3]


# ── contact primitives, all reading the CERTIFIED manifest ──────────────────

class _Facts:
    """A thin reader over the certified payload. It derives nothing new: every
    value below is already present in `build_d4_facts()` output."""

    def __init__(self, facts: Dict[str, Any], doctrine: Any):
        for key in ("grahas", "houses", "house_lords", "aspects", "d4_lagna"):
            if key not in facts:
                raise D4PropertyStateError("certified D4 facts are incomplete")
        self.f = facts
        self.doctrine = doctrine
        self.grahas = facts["grahas"]
        self.house_of = {g: facts["grahas"][g]["d4_house"] for g in self.grahas}
        self.sign_of = {g: facts["grahas"][g]["d4_sign_index"] for g in self.grahas}
        self.dignity_of = {g: facts["grahas"][g]["dignity"].get("dignity") for g in self.grahas}
        self.lord_of = {int(h["house"]): h["lord"] for h in facts["houses"]}
        self.h4_sign_index = next(h["sign_index"] for h in facts["houses"] if h["house"] == 4)
        self.fourth_lord = self.lord_of[4]
        self.fourth_lord_house = self.house_of[self.fourth_lord]
        self.fourth_lord_sign_index = self.sign_of[self.fourth_lord]
        # Certified aspect manifest, keyed source -> set of houses aspected.
        self.aspects_from = {}
        for e in facts["aspects"]["edges"]:
            self.aspects_from.setdefault(e["source"], set()).add(int(e["to_house"]))

    # occupancy
    def occupies(self, graha: str, house: int) -> bool:
        return self.house_of.get(graha) == house

    # conjunction — TWO DISTINCT grahas, same D4 house. See module docstring.
    def conjoins(self, graha: str, other: str) -> bool:
        if graha == other:
            return False
        return self.house_of.get(graha) is not None and self.house_of.get(graha) == self.house_of.get(other)

    # aspect — certified manifest only. Nodes appear with no edges at all.
    def aspects_house(self, graha: str, house: int) -> bool:
        return house in self.aspects_from.get(graha, set())

    def aspects_graha(self, graha: str, other: str) -> bool:
        h = self.house_of.get(other)
        return h is not None and self.aspects_house(graha, h)

    # ── the two contact surfaces ────────────────────────────────────────────
    def contact_paths_h4(self, graha: str) -> List[str]:
        paths = []
        if self.occupies(graha, 4):
            paths.append("occupies_h4")
        if self.aspects_house(graha, 4):
            paths.append("aspects_h4")
        return paths

    def contact_paths_4l(self, graha: str) -> List[str]:
        paths = []
        if self.conjoins(graha, self.fourth_lord):
            paths.append("conjoins_4l")
        if self.aspects_graha(graha, self.fourth_lord):
            paths.append("aspects_4l")
        return paths

    def all_contact_paths(self, graha: str) -> List[str]:
        return self.contact_paths_h4(graha) + self.contact_paths_4l(graha)


def _contact_record(F: _Facts, graha: str) -> Dict[str, Any]:
    return {
        "graha": graha,
        "d4_house": F.house_of.get(graha),
        "d4_sign_index": F.sign_of.get(graha),
        "paths": F.all_contact_paths(graha),
    }


# ── Lock 1 ───────────────────────────────────────────────────────────────────

def evaluate_lock1(F: _Facts) -> Dict[str, Any]:
    """Qualifying benefic set, malefic count set, and net cancellation.

    Counting is by UNIQUE GRAHA IDENTITY: a graha contacting both H4 and the
    4th Lord contributes 1, not 2. Every individual path is retained as
    evidence so the count is auditable rather than asserted.
    """
    # Mercury disqualification: conjoined in D4 with ANY natural malefic.
    mercury_malefic_conjunctions = [
        m for m in NATURAL_MALEFIC_SET if F.conjoins("Mercury", m)
    ]
    mercury_excluded = bool(mercury_malefic_conjunctions)
    qualifying_benefics = tuple(
        g for g in BENEFIC_BASE_SET if not (g == "Mercury" and mercury_excluded)
    )

    benefic_contacts = [
        _contact_record(F, g) for g in qualifying_benefics if F.all_contact_paths(g)
    ]
    malefic_contacts = [
        _contact_record(F, g) for g in NATURAL_MALEFIC_SET if F.all_contact_paths(g)
    ]
    benefic_count = len(benefic_contacts)
    malefic_count = len(malefic_contacts)

    return {
        "benefic_base_set": list(BENEFIC_BASE_SET),
        "qualifying_benefic_set": list(qualifying_benefics),
        "natural_malefic_set": list(NATURAL_MALEFIC_SET),
        "mercury_excluded_from_benefic_set": mercury_excluded,
        "mercury_malefic_conjunctions": mercury_malefic_conjunctions,
        "benefic_contacts": benefic_contacts,
        "malefic_contacts": malefic_contacts,
        "benefic_count": benefic_count,
        "malefic_count": malefic_count,
        # Equality does NOT cancel. One benefic does not cancel one malefic.
        "benefic_cancellation": benefic_count > malefic_count,
    }


# ── Lock 2 ───────────────────────────────────────────────────────────────────

def evaluate_lock2(F: _Facts) -> Dict[str, Any]:
    """The six 8L/12L involvement paths, each exposed separately."""
    l8, l12 = F.lord_of[8], F.lord_of[12]
    fl = F.fourth_lord
    fl_house = F.fourth_lord_house

    def per_lord(lord: str, label: str) -> Dict[str, Any]:
        return {
            "lord": lord,
            "role": label,
            "d4_house": F.house_of.get(lord),
            "occupies_h4": F.occupies(lord, 4),
            "conjoins_4l": F.conjoins(lord, fl),
            "aspects_h4": F.aspects_house(lord, 4),
            "aspects_4l": F.aspects_graha(lord, fl),
            "is_same_graha_as_4l": lord == fl,
        }

    e8, e12 = per_lord(l8, "eighth_lord"), per_lord(l12, "twelfth_lord")

    c1 = e8["occupies_h4"] or e12["occupies_h4"]
    c2 = e8["conjoins_4l"] or e12["conjoins_4l"]
    c3 = e8["aspects_h4"] or e12["aspects_h4"]
    c4 = e8["aspects_4l"] or e12["aspects_4l"]
    c5 = fl_house in (8, 12)
    c6 = ((fl_house == 8 and F.occupies(l8, 4))
          or (fl_house == 12 and F.occupies(l12, 4)))

    return {
        "eighth_lord": e8,
        "twelfth_lord": e12,
        "conditions": {
            "c1_lord_occupies_h4": c1,
            "c2_lord_conjoins_4l": c2,
            "c3_lord_aspects_h4": c3,
            "c4_lord_aspects_4l": c4,
            "c5_4l_occupies_h8_or_h12": c5,
            "c6_direct_parivartana": c6,
        },
        "eighth_or_twelfth_involvement": any((c1, c2, c3, c4, c5, c6)),
    }


# ── Lock 3 ───────────────────────────────────────────────────────────────────

def evaluate_lock3(F: _Facts) -> Dict[str, Any]:
    """Rahu qualifies by occupancy or conjunction ONLY — never by aspect, which
    is consistent with the standing no-independent-node-drishti doctrine and is
    also structurally impossible here, since the certified manifest carries no
    node edges at all. Mercury qualifies by six paths. Vargottama alone is NOT
    a trigger; it stays supporting evidence."""
    fl = F.fourth_lord
    rahu = {
        "occupies_h4": F.occupies("Rahu", 4),
        "conjoins_4l": F.conjoins("Rahu", fl),
        # Recorded to prove the aspect route is dead, not merely unused.
        "aspect_paths_available": sorted(F.aspects_from.get("Rahu", set())),
    }
    rahu_qualifies = rahu["occupies_h4"] or rahu["conjoins_4l"]

    merc_dignity = F.dignity_of.get("Mercury")
    mercury = {
        "occupies_h4": F.occupies("Mercury", 4),
        "conjoins_4l": F.conjoins("Mercury", fl),
        "aspects_h4": F.aspects_house("Mercury", 4),
        "aspects_4l": F.aspects_graha("Mercury", fl),
        "d4_dignity": merc_dignity,
        "dignity_swa": merc_dignity == DIGNITY_SWA,
        "dignity_uccha": merc_dignity == DIGNITY_UCCHA,
        "vargottama_supporting_only": bool(F.grahas["Mercury"]["vargottama"]),
    }
    mercury_qualifies = any((mercury["occupies_h4"], mercury["conjoins_4l"],
                             mercury["aspects_h4"], mercury["aspects_4l"],
                             mercury["dignity_swa"], mercury["dignity_uccha"]))

    return {
        "rahu": rahu,
        "rahu_qualifies": rahu_qualifies,
        "mercury": mercury,
        "mercury_qualifies": mercury_qualifies,
        "strong_mercury_rahu_influence": rahu_qualifies or mercury_qualifies,
    }


# ── Lock 4 ───────────────────────────────────────────────────────────────────

def evaluate_lock4(F: _Facts, d1_root: Dict[str, Any],
                   benefic_cancellation: bool) -> Dict[str, Any]:
    """D1 4th-Lord dignity plus raw D4 6/8/12 affliction and effective freedom.

    D1 dignity is NOT recomputed. `d1_root` carries the dignity the certified
    chart snapshot already published, in which Moolatrikona IS active — unlike
    the D4 layer, whose moolatrikona policy remains not_evaluated.
    """
    lagna_si = d1_root.get("lagna_sign_index")
    dign_by_graha = d1_root.get("dignity_by_graha") or {}
    if not isinstance(lagna_si, int) or isinstance(lagna_si, bool) or not 0 <= lagna_si <= 11:
        raise D4PropertyStateError("D1 lagna sign index is not certified")
    d1_fourth_sign = (lagna_si + 3) % 12
    d1_fourth_lord = F.doctrine.sign_lords[d1_fourth_sign]
    d1_dignity = dign_by_graha.get(d1_fourth_lord)
    if d1_dignity is None:
        raise D4PropertyStateError("D1 dignity for the 4th lord is not certified")

    d1_block = {
        "d1_lagna_sign_index": lagna_si,
        "d1_fourth_house_sign_index": d1_fourth_sign,
        "d1_fourth_lord": d1_fourth_lord,
        "d1_fourth_lord_dignity": d1_dignity,
        "qualifying_labels": list(D1_DIGNIFIED_LABELS),
        "d1_fourth_lord_dignified": d1_dignity in D1_DIGNIFIED_LABELS,
    }

    fl = F.fourth_lord
    fl_house = F.fourth_lord_house
    dusthana_lords = {h: F.lord_of[h] for h in DUSTHANA_HOUSES}

    r1 = fl_house in DUSTHANA_HOUSES
    r2_conj = sorted({lord for h, lord in dusthana_lords.items() if F.conjoins(lord, fl)})
    r2_asp = sorted({lord for h, lord in dusthana_lords.items() if F.aspects_graha(lord, fl)})
    r2 = bool(r2_conj or r2_asp)
    # Reason 3 is subsumed by reason 1 — see the module docstring. Implemented
    # exactly as specified anyway, with its own evidence.
    r3_malefics = sorted({m for m in NATURAL_MALEFIC_SET
                          if F.conjoins(m, fl) and F.house_of.get(m) in DUSTHANA_HOUSES})
    r3 = bool(r3_malefics)

    raw = any((r1, r2, r3))
    return {
        "d1": d1_block,
        "fourth_lord": fl,
        "fourth_lord_d4_house": fl_house,
        "dusthana_lords": {str(h): lord for h, lord in dusthana_lords.items()},
        "reasons": {
            "r1_4l_occupies_dusthana": r1,
            "r2_4l_conjoined_or_aspected_by_dusthana_lord": r2,
            "r2_conjoined_by": r2_conj,
            "r2_aspected_by": r2_asp,
            "r3_4l_conjoins_malefic_placed_in_dusthana": r3,
            "r3_malefics": r3_malefics,
        },
        "raw_dusthana_affliction": raw,
        "benefic_cancellation": benefic_cancellation,
        # Effective freedom: no raw affliction, OR the Lock-1 net cancellation.
        "fourth_lord_free_from_dusthana_affliction": (not raw) or benefic_cancellation,
    }


# ── supporting evidence, never predicate truth ──────────────────────────────

def supporting_evidence(F: _Facts) -> Dict[str, Any]:
    mars_house = F.house_of.get("Mars")
    mars_dignity = F.dignity_of.get("Mars")
    return {
        "vargottama": {
            "grahas": list(F.f.get("vargottama_grahas", [])),
            "approved_modifier": "+1",
            "applied_to_any_predicate": False,
            "composite_score_present": False,
        },
        "mars_bhumi_karaka": {
            "d4_house": mars_house,
            "d4_dignity": mars_dignity,
            "in_kendra_or_trikona": mars_house in set(KENDRA_HOUSES) | set(TRIKONA_HOUSES),
            "dignity_swa_or_uccha": mars_dignity in D4_STRONG_DIGNITY_LABELS,
            "strong": (mars_house in set(KENDRA_HOUSES) | set(TRIKONA_HOUSES))
                      or (mars_dignity in D4_STRONG_DIGNITY_LABELS),
            "note": "supporting evidence for P2/P4 interpretation; not a predicate",
        },
        "venus_vahana_karaka": {
            "d4_house": F.house_of.get("Venus"),
            "d4_dignity": F.dignity_of.get("Venus"),
            "note": "carried mechanically; Vahana tiers are a later bounded ticket",
        },
    }


# ── the five predicates ──────────────────────────────────────────────────────

def _evaluate_p1(F: _Facts, lock1: Dict[str, Any], lock2: Dict[str, Any]) -> Dict[str, Any]:
    afflictors = []
    for g in P1_AFFLICTING_SET:
        paths = F.all_contact_paths(g)
        if paths:
            afflictors.append({"graha": g, "paths": paths})
    limb1 = bool(afflictors)
    limb2 = lock2["eighth_or_twelfth_involvement"]
    limb3 = not lock1["benefic_cancellation"]
    return {
        "trigger_set": list(P1_AFFLICTING_SET),
        "sun_deliberately_excluded_from_trigger_set": True,
        "afflicting_contacts": afflictors,
        "limb1_h4_or_4l_afflicted": limb1,
        "limb2_eighth_or_twelfth_involvement": limb2,
        "limb3_no_benefic_cancellation": limb3,
        "value": limb1 and limb2 and limb3,
    }


def _evaluate_p2(F: _Facts, lock1: Dict[str, Any], lock4: Dict[str, Any]) -> Dict[str, Any]:
    fl_house = F.fourth_lord_house
    fl_dignity = F.dignity_of.get(F.fourth_lord)
    in_kendra = fl_house in KENDRA_HOUSES
    in_trikona = fl_house in TRIKONA_HOUSES
    strong_dignity = fl_dignity in D4_STRONG_DIGNITY_LABELS
    limb1 = in_kendra or in_trikona or strong_dignity

    benefic_h4 = [g for g in lock1["qualifying_benefic_set"] if F.contact_paths_h4(g)]
    mars_h4 = bool(F.contact_paths_h4("Mars"))
    limb2 = bool(benefic_h4) or mars_h4

    limb3 = lock4["d1"]["d1_fourth_lord_dignified"]
    return {
        "fourth_lord": F.fourth_lord,
        "fourth_lord_d4_house": fl_house,
        "fourth_lord_d4_dignity": fl_dignity,
        "limb1_4l_kendra": in_kendra,
        "limb1_4l_trikona": in_trikona,
        "limb1_4l_dignity_swa_or_uccha": strong_dignity,
        "limb1": limb1,
        "limb2_benefics_contacting_h4": benefic_h4,
        "limb2_mars_contacts_h4": mars_h4,
        "limb2": limb2,
        "limb3_d1_4l_dignified": limb3,
        "value": limb1 and limb2 and limb3,
    }


def _evaluate_p3(F: _Facts, lock3: Dict[str, Any]) -> Dict[str, Any]:
    h4_mod = sign_modality(F.h4_sign_index)
    fl_mod = sign_modality(F.fourth_lord_sign_index)
    structural = h4_mod in ("Movable", "Dual") and fl_mod in ("Movable", "Dual")
    influence = lock3["strong_mercury_rahu_influence"]
    return {
        "h4_sign_index": F.h4_sign_index,
        "h4_modality": h4_mod,
        "fourth_lord_sign_index": F.fourth_lord_sign_index,
        "fourth_lord_modality": fl_mod,
        "limb1_both_movable_or_dual": structural,
        "limb2_strong_mercury_rahu_influence": influence,
        "value": structural or influence,
    }


def _evaluate_p4(F: _Facts, lock4: Dict[str, Any]) -> Dict[str, Any]:
    h4_fixed = sign_modality(F.h4_sign_index) == "Fixed"
    fl_fixed = sign_modality(F.fourth_lord_sign_index) == "Fixed"
    free = lock4["fourth_lord_free_from_dusthana_affliction"]
    return {
        "limb1_h4_sign_fixed": h4_fixed,
        "limb1_4l_sign_fixed": fl_fixed,
        "limb1": h4_fixed or fl_fixed,
        "limb2_4l_free_from_dusthana_affliction": free,
        "value": (h4_fixed or fl_fixed) and free,
    }


# ── D4-004 · explicit evidence hierarchy ────────────────────────────────────

def evidence_hierarchy(F: _Facts, state: Dict[str, Any], lock4: Dict[str, Any],
                       facts: Dict[str, Any]) -> Dict[str, Any]:
    """D4 PRIMARY EVIDENCE -> D1 ROOT CONTEXT, made explicit on the wire.

    SELECTION ONLY. Every value below already exists in the certified facts or
    in the state this module just resolved. Nothing is recomputed, no astrology
    is added, and there is deliberately NO weighted D1+D4 score: D1 is carried
    as supporting natal context and cannot select or override the D4 state.
    """
    fl = F.fourth_lord
    g = F.grahas[fl]
    h4 = facts["fourth_house"]
    d1 = lock4["d1"]
    return {
        "authority": "d4_primary",
        "d4_primary": {
            "selected_state": state["selected_state"],
            "state_id": state["state_id"],
            "category": state["category"],
            "resolution": state["resolution"],
            "matched_states": list(state["matched_states"]),
            "d4_lagna": facts["d4_lagna"],
            "fourth_house": {
                "house": h4["house"],
                "sign": h4["sign"],
                "sign_index": h4["sign_index"],
                "occupants": list(h4["occupants"]),
                "aspects_received": list(h4["aspects_received"]),
            },
            "fourth_lord": {
                "graha": fl,
                "d4_sign": g["d4_sign"],
                "d4_sign_index": g["d4_sign_index"],
                "d4_house": g["d4_house"],
                "dignity": g["dignity"].get("dignity"),
                "vargottama": g["vargottama"],
            },
            "affliction_evidence": {
                "raw_dusthana_affliction": lock4["raw_dusthana_affliction"],
                "reasons": lock4["reasons"],
                "fourth_lord_free_from_dusthana_affliction":
                    lock4["fourth_lord_free_from_dusthana_affliction"],
            },
            "contact_evidence": {
                "benefic_contacts": state["lock1_benefic_cancellation"]["benefic_contacts"],
                "malefic_contacts": state["lock1_benefic_cancellation"]["malefic_contacts"],
                "benefic_count": state["lock1_benefic_cancellation"]["benefic_count"],
                "malefic_count": state["lock1_benefic_cancellation"]["malefic_count"],
                "benefic_cancellation": state["lock1_benefic_cancellation"]["benefic_cancellation"],
            },
            "mars_supporting_evidence": state["supporting_evidence"]["mars_bhumi_karaka"],
            "vargottama_supporting_evidence": state["supporting_evidence"]["vargottama"],
        },
        "d1_root_context": {
            "label": "D1 Root Context · Supporting",
            "fourth_house_sign_index": d1["d1_fourth_house_sign_index"],
            "fourth_house_sign": F.doctrine.signs[d1["d1_fourth_house_sign_index"]],
            "fourth_lord": d1["d1_fourth_lord"],
            "fourth_lord_dignity": d1["d1_fourth_lord_dignity"],
            "fourth_lord_dignified": d1["d1_fourth_lord_dignified"],
            # Declared, not implied. D1 feeds ONE predicate limb (P2 limb 3) and
            # otherwise contributes no authority at all.
            "selects_or_overrides_d4_state": False,
            "weighted_d1_d4_score_present": False,
            "note": "supporting natal context only; the Primary Property State is D4-selected",
        },
    }


# ── the classifier ───────────────────────────────────────────────────────────

def classify_property_state(facts: Dict[str, Any], d1_root: Dict[str, Any],
                            doctrine: Any) -> Dict[str, Any]:
    """Exactly ONE Primary Property State, by first-match precedence.

    All four specific predicates are evaluated INDEPENDENTLY and every true one
    is retained in `matched_states`, even though exactly one is selected.
    """
    F = _Facts(facts, doctrine)

    lock1 = evaluate_lock1(F)
    lock2 = evaluate_lock2(F)
    lock3 = evaluate_lock3(F)
    lock4 = evaluate_lock4(F, d1_root, lock1["benefic_cancellation"])

    predicates = {
        "P1": _evaluate_p1(F, lock1, lock2),
        "P2": _evaluate_p2(F, lock1, lock4),
        "P3": _evaluate_p3(F, lock3),
        "P4": _evaluate_p4(F, lock4),
    }
    truth = {k: bool(v["value"]) for k, v in predicates.items()}
    matched = [k for k in PRECEDENCE if truth[k]]

    if matched:
        selected = matched[0]                 # first-match precedence
        resolution = "predicate_match"
        matched_states = matched
    else:
        selected = "P5"
        resolution = "coverage_fallback"
        matched_states = []                   # P5 is never a matched yoga

    state_id, category = STATE_CATEGORIES[selected]
    result = {
        "engine": {
            "d4_property_state_version": D4_PROPERTY_STATE_VERSION,
            "precedence": list(PRECEDENCE) + ["P5"],
            "conjunction_rule": "same_d4_house_no_orb",
            "self_conjunction_policy": "excluded",
            "aspect_source": "certified_d4_manifest",
            "provider_classification_authority": False,
            "literal_property_count_published": False,
        },
        "selected_state": selected,
        "state_id": state_id,
        "category": category,
        "resolution": resolution,
        "matched_states": matched_states,
        "predicates": {
            "truth_table": truth,
            "P1": predicates["P1"],
            "P2": predicates["P2"],
            "P3": predicates["P3"],
            "P4": predicates["P4"],
        },
        "lock1_benefic_cancellation": lock1,
        "lock2_eighth_twelfth_involvement": lock2,
        "lock3_mercury_rahu_influence": lock3,
        "lock4_dignity_and_affliction": lock4,
        "supporting_evidence": supporting_evidence(F),
    }
    result.update(evidence_hierarchy(F, result, lock4, facts))
    return result
