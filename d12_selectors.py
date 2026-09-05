"""d12_selectors.py — FR-002 tension waterfall and FR-003 Three Instructions.

D12-005. Strict order, first TRUE wins, evaluation stops there. There are no
weights beyond FR-004 and no second ranking system: each trigger is a predicate,
not a score, and nothing is compared against anything else.

Trigger 4 is worth naming explicitly. Its TITLE says "Loaded 4th-Lord Saturn",
but the ratified predicate is exact — D1 4th lord IS Saturn and Saturn is Neecha
in D12. The general FR-001 classifier is NOT substituted for it, because the two
can disagree: Saturn could be classified Loaded by heavy occupancy while not
being Neecha at all. The ruling's predicate governs; the title is a label.
"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional

from d12_crosschart_contract import Tri
from d12_instruction_corpus import (
    TENSION_FALLBACK, TENSION_KEYS, TENSION_TITLE, instruction_text)
from d12_selectors_contract import (
    D12Interpretation, Tension, ThreeInstructions, TriggerEvaluation)

__all__ = ["D12SelectorError", "build_tension", "build_instructions",
           "build_interpretation"]

DUSTHANA = (6, 8, 12)

_ABSENT_REASON = (
    "the tension fell back to the FR-002 static-architecture sentence, and "
    "FR-003 authorises exactly four instruction triads with no fifth set for "
    "the fallback")


class D12SelectorError(ValueError):
    """A selector input that cannot be resolved. Raised, never defaulted."""


def _b(x: bool) -> Tri:
    return Tri.TRUE if x else Tri.FALSE


def _placements(fact_set: Any):
    if isinstance(fact_set, Mapping):
        return {g: dict(p) for g, p in fact_set["placements"].items()}
    raise D12SelectorError(f"unrecognised fact set {type(fact_set).__name__}")


def build_tension(fact_set: Any, release_topology: Any,
                  devata_counts: Mapping[str, int],
                  hidden_counts: Mapping[str, int],
                  d1_house_lords: Mapping[int, str]) -> Tension:
    """FR-002 - the strict waterfall. Evaluate in order, stop at the first TRUE.

    Every candidate is still RECORDED so QA can see the whole ladder, but only
    the first TRUE is the winner and later candidates are not consulted for it.

    CORR-01 - REQUIRED AUTHORITIES FAIL CLOSED. An absent count mapping or an
    absent D1 house-lord authority used to coerce to {}, which silently made
    trigger 3 or trigger 4 evaluate FALSE and handed the win to a lower
    priority - or printed the fallback - because an INPUT was missing rather
    than because the predicate was false. A missing authority is now an error
    raised before any selection happens. Absence and falsity are different
    facts and must not share a code path.
    """
    if devata_counts is None or not isinstance(devata_counts, Mapping):
        raise D12SelectorError(
            "trigger 3 requires the accepted section 9 PRIMARY imprint counts; "
            "refusing to select a tension with the authority absent")
    if hidden_counts is None or not isinstance(hidden_counts, Mapping):
        raise D12SelectorError(
            "trigger 3 requires the accepted section 9 HIDDEN imprint counts; "
            "refusing to select a tension with the authority absent")
    if d1_house_lords is None or not isinstance(d1_house_lords, Mapping):
        raise D12SelectorError(
            "trigger 4 requires the accepted D1 house-lord authority; refusing "
            "to select a tension with it absent")
    if 4 not in d1_house_lords or not d1_house_lords[4]:
        raise D12SelectorError(
            "trigger 4 requires the D1 H4 lord; refusing to evaluate it as "
            "FALSE merely because the lord was not supplied")
    pl = _placements(fact_set)
    hidden = dict(hidden_counts)
    primary = dict(devata_counts)
    lords = dict(d1_house_lords)

    def lum(name):
        p = pl.get(name)
        if p is None:
            raise D12SelectorError(f"{name} absent from the D12 placements")
        return p

    sun, moon = lum("Sun"), lum("Moon")
    mercury, saturn = pl.get("Mercury"), pl.get("Saturn")

    candidates: List[TriggerEvaluation] = []

    # ── 1 · Ketu-pull vs Living Parents ─────────────────────────────────────
    # CORR-02 · proper three-valued conjunction. `bool(dominance)` is forbidden:
    # Tri.UNKNOWN is a truthy enum member, so truthiness would silently convert
    # "unevaluated" into "yes". UNKNOWN AND FALSE is FALSE — a definite answer,
    # because the second conjunct alone settles it. UNKNOWN AND TRUE is UNKNOWN,
    # and that blocks the whole waterfall below it.
    dominance = getattr(release_topology, "dominance", None)
    if not isinstance(dominance, Tri):
        raise D12SelectorError(
            f"trigger 1 requires a three-valued FR-004 release dominance, got "
            f"{dominance!r}; refusing to coerce it with truthiness")
    luminary_afflicted = (
        sun["dignity_state"] == "Neecha" or sun["house"] in DUSTHANA
        or moon["dignity_state"] == "Neecha" or moon["house"] in DUSTHANA)
    if not luminary_afflicted:
        t1 = Tri.FALSE                       # UNKNOWN AND FALSE = FALSE
    elif dominance is Tri.UNKNOWN:
        t1 = Tri.UNKNOWN
    else:
        t1 = _b(dominance is Tri.TRUE)
    candidates.append(TriggerEvaluation(
        key="ketu_pull_vs_living_parents", priority=1, result=t1,
        basis={"fr004_release_dominance": dominance.value,
               "sun": f"H{sun['house']} {sun['dignity_state']}",
               "moon": f"H{moon['house']} {moon['dignity_state']}",
               "luminary_neecha_or_dusthana": str(luminary_afflicted),
               "three_valued": "UNKNOWN AND FALSE = FALSE; UNKNOWN AND TRUE = UNKNOWN"}))

    # ── 2 · Father as Landmark vs Mother as Debt ────────────────────────────
    t2 = (sun["house"] == 4 and moon["house"] == 6
          and moon["dignity_state"] == "Neecha")
    candidates.append(TriggerEvaluation(
        key="father_landmark_vs_mother_debt", priority=2, result=_b(t2),
        basis={"sun_house": str(sun["house"]), "moon_house": str(moon["house"]),
               "moon_dignity": moon["dignity_state"]}))

    # ── 3 · Vihwala Climate vs Ganesha Opening ──────────────────────────────
    # The §9 INTERNAL imprint counts. Never inferred from printed gloss text.
    vihwala = int(hidden.get("Vihwala", 0))
    ganesha = int(primary.get("Ganesha", 0))
    candidates.append(TriggerEvaluation(
        key="vihwala_climate_vs_ganesha_opening", priority=3,
        result=_b(vihwala >= 2 and ganesha >= 1),
        basis={"vihwala_hidden_count": str(vihwala),
               "ganesha_primary_count": str(ganesha),
               "source": "accepted §9 internal imprint counts"}))

    # ── 4 · Reliable Mercury vs Loaded 4th-Lord Saturn ──────────────────────
    merc_ok = bool(mercury) and (
        mercury.get("vargottama") is True
        or (mercury["dignity_state"] == "Mitra" and mercury["house"] == 3))
    saturn_is_h4_lord = lords.get(4) == "Saturn"
    saturn_neecha = bool(saturn) and saturn["dignity_state"] == "Neecha"
    candidates.append(TriggerEvaluation(
        key="reliable_mercury_vs_loaded_saturn", priority=4,
        result=_b(merc_ok and saturn_is_h4_lord and saturn_neecha),
        basis={"mercury_vargottama": str(bool(mercury) and mercury.get("vargottama")),
               "mercury": f"H{mercury['house']} {mercury['dignity_state']}" if mercury else "(absent)",
               "d1_h4_lord": str(lords.get(4)),
               "saturn_d12_dignity": saturn["dignity_state"] if saturn else "(absent)",
               "note": "the ratified exact predicate, not the FR-001 classifier"}))

    # CORR-02 · walk the waterfall in order and stop at the FIRST non-FALSE
    # result. A TRUE is the winner. An UNKNOWN blocks everything below it: no
    # lower trigger may win and the fallback may not print, because either would
    # assert that the unresolved trigger evaluated FALSE.
    winner = None
    unresolved_at = None
    for c in candidates:
        if c.result is Tri.UNKNOWN:
            unresolved_at = c.key
            break
        if c.result is Tri.TRUE:
            winner = c.key
            break
    return Tension(candidates=candidates, winner=winner,
                   title=TENSION_TITLE[winner] if winner else None,
                   fallback_applied=winner is None and unresolved_at is None,
                   fallback_text=(TENSION_FALLBACK if winner is None
                                  and unresolved_at is None else None),
                   unresolved_at=unresolved_at)


UNRESOLVED_REASON = (
    "the tension is unresolved: a higher-priority trigger could not be "
    "evaluated, so no winner exists and FR-003 has no triad to supply")


def build_instructions(tension: Tension) -> ThreeInstructions:
    """FR-003 · the winning key maps directly to the locked triad.

    No generation, no paraphrase, no interpolation, and no fifth set: when the
    tension falls back, the instructions are ABSENT and say so.
    """
    if tension.winner is None:
        reason = (UNRESOLVED_REASON if tension.unresolved_at
                  else _ABSENT_REASON)
        return ThreeInstructions(available=False, winner_key=None,
                                 cultivate=None, watch=None, practise=None,
                                 absent_reason=reason)
    return ThreeInstructions(
        available=True, winner_key=tension.winner,
        cultivate=instruction_text(tension.winner, "cultivate"),
        watch=instruction_text(tension.winner, "watch"),
        practise=instruction_text(tension.winner, "practise"),
        absent_reason=None)


def build_interpretation(crosschart, release_topology, fact_set,
                         devata_counts, hidden_counts,
                         d1_house_lords) -> D12Interpretation:
    """The full deterministic §§10-12 layer for one certified chart."""
    tension = build_tension(fact_set, release_topology, devata_counts,
                            hidden_counts, d1_house_lords)
    return D12Interpretation(crosschart=crosschart,
                             release_topology=release_topology,
                             tension=tension,
                             instructions=build_instructions(tension))
