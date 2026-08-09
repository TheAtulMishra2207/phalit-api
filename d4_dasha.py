"""
d4_dasha.py — D4-007 · MAHADASHA / ANTARDASHA CONCURRENCE, CONTEXT ONLY.

WHAT A CONCURRENCE MEANS, AND NOTHING MORE
    "The current Dasha lord is one of the grahas structurally participating in
    the selected D4 state."

It does NOT activate a yoga, create a yoga that did not match structurally,
predict a purchase, litigation, a vehicle, an accident or any event, and it
produces no date. The words "activation", "trigger", "manifestation",
"fruition", "dormant", "imminent", "purchase window" and "litigation period"
appear nowhere in this module's output, deliberately. `timing_policy` is
published as `structural_concurrence_not_activation` so a reader cannot mistake
the block for a forecast.

THE STRUCTURAL STATE REMAINS AUTHORITATIVE. This module derives participants
FROM the evidence `d4_property_state.py` already emitted. It re-evaluates no
predicate, recomputes none of Locks 1-4, and never becomes a second property
classifier. If a predicate is false, it has no participant set at all.

VIMSHOTTARI IS NOT RECOMPUTED. The current Mahadasha and Antardasha identities
are read from the certified chart snapshot. No birth data is accepted, no Moon
nakshatra is re-derived, and the browser's `_DASHA_MD` / `_DASHA_AD` globals are
never consulted — the server is authoritative.

THREE-STATE TIMING, NEVER COLLAPSED. Missing Dasha facts resolve to `unknown`,
not to `no_match`. Treating an absence as a negative would publish a false
structural claim, which is the same class of error as manufacturing a positive.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

D4_DASHA_VERSION = "1.0.0"

NATURAL_MALEFIC_SET = ("Sun", "Mars", "Saturn", "Rahu", "Ketu")

STATUS_MATCH = "match"
STATUS_NO_MATCH = "no_match"
STATUS_UNKNOWN = "unknown"

SUMMARY_BOTH = "md_and_ad_concurrence"
SUMMARY_MD = "md_concurrence"
SUMMARY_AD = "ad_concurrence"
SUMMARY_NONE = "no_current_concurrence"
SUMMARY_UNKNOWN = "unknown"
SUMMARY_NA = "not_applicable_coverage_fallback"

APPLICABILITY_NA = "not_applicable_coverage_fallback"
APPLICABILITY_APPLIES = "applies_to_selected_structural_state"


class D4DashaError(ValueError):
    """Inputs are not the accepted structural evidence this module requires.
    Internal only — the route converts it to a neutral correlated error."""


# ── participant accumulation ────────────────────────────────────────────────

class _Participants:
    """Unique graha identities, with roles and evidence paths preserved.

    Deduplication is on IDENTITY only. A graha that enters twice keeps both
    roles and every evidence path, because flattening away WHY it entered is
    exactly what makes a participant list unauditable later.
    """

    def __init__(self) -> None:
        self._by_graha: Dict[str, Dict[str, Any]] = {}
        self._order: List[str] = []

    def add(self, graha: Optional[str], role: str, paths: Optional[List[str]] = None) -> None:
        if not graha:
            return
        if graha not in self._by_graha:
            self._by_graha[graha] = {"graha": graha, "roles": [], "evidence_paths": []}
            self._order.append(graha)
        rec = self._by_graha[graha]
        if role not in rec["roles"]:
            rec["roles"].append(role)
        for p in (paths or []):
            if p not in rec["evidence_paths"]:
                rec["evidence_paths"].append(p)

    def records(self) -> List[Dict[str, Any]]:
        return [self._by_graha[g] for g in self._order]

    def grahas(self) -> List[str]:
        return list(self._order)


# ── per-state participant derivation, all from accepted evidence ────────────

def _contact_paths_from_evidence(state: Dict[str, Any], graha: str) -> List[str]:
    """The contact paths d4_property_state already recorded for this graha."""
    contacts = state["lock1_benefic_cancellation"]
    for side in ("benefic_contacts", "malefic_contacts"):
        for rec in contacts.get(side, []):
            if rec.get("graha") == graha:
                return list(rec.get("paths", []))
    return []


def _p1_participants(state: Dict[str, Any]) -> _Participants:
    """D4 4L · actively-involved 8L/12L · every Natural Malefic contacting H4/4L.

    THE SUN CAVEAT, AND IT IS THE POINT: Sun is in the Natural Malefic set, so a
    contacting Sun IS a timing participant. It is NOT in the P1 structural
    trigger set and this module does not put it there — the D4-003 predicate is
    read, never re-evaluated.
    """
    p = _Participants()
    lock2 = state["lock2_eighth_twelfth_involvement"]
    lock4 = state["lock4_dignity_and_affliction"]
    p.add(lock4["fourth_lord"], "d4_fourth_lord", ["mandatory"])

    for key, role in (("eighth_lord", "d4_eighth_lord"), ("twelfth_lord", "d4_twelfth_lord")):
        ev = lock2[key]
        fired = [k for k in ("occupies_h4", "conjoins_4l", "aspects_h4", "aspects_4l")
                 if ev.get(k)]
        # ACTIVELY involved only: a lord that satisfied no Lock-2 path is not a
        # participant merely by holding the lordship.
        if fired:
            p.add(ev["lord"], role, fired)

    for m in NATURAL_MALEFIC_SET:
        paths = _contact_paths_from_evidence(state, m)
        if paths:
            p.add(m, "natural_malefic_contacting_h4_or_4l", paths)
    return p


def _p2_participants(state: Dict[str, Any]) -> _Participants:
    """D4 4L · D1 4L · Mars (mandatory) · Lock-1 benefics occupying/aspecting H4."""
    p = _Participants()
    lock4 = state["lock4_dignity_and_affliction"]
    p2 = state["predicates"]["P2"]
    p.add(lock4["fourth_lord"], "d4_fourth_lord", ["mandatory"])
    p.add(lock4["d1"]["d1_fourth_lord"], "d1_fourth_lord", ["mandatory"])
    p.add("Mars", "bhumi_karaka", ["mandatory"])
    for b in p2.get("limb2_benefics_contacting_h4", []):
        p.add(b, "lock1_benefic_contacting_h4", _contact_paths_from_evidence(state, b))
    if p2.get("limb2_mars_contacts_h4"):
        # Mars is already mandatory; this records the extra path, not a second Mars.
        p.add("Mars", "contacts_h4", _contact_paths_from_evidence(state, "Mars"))
    return p


def _p3_participants(state: Dict[str, Any]) -> _Participants:
    """D4 4L, plus Mercury or Rahu ONLY where Lock 3 actually recorded them.

    The movable/dual modality limb can make P3 true on its own. In that case the
    set is just the 4th Lord, and no participant is invented to fill it out.
    """
    p = _Participants()
    lock3 = state["lock3_mercury_rahu_influence"]
    p.add(state["lock4_dignity_and_affliction"]["fourth_lord"], "d4_fourth_lord", ["mandatory"])

    if lock3["mercury_qualifies"]:
        m = lock3["mercury"]
        paths = [k for k in ("occupies_h4", "conjoins_4l", "aspects_h4", "aspects_4l",
                             "dignity_swa", "dignity_uccha") if m.get(k)]
        p.add("Mercury", "lock3_strong_influence", paths)
    if lock3["rahu_qualifies"]:
        r = lock3["rahu"]
        # Occupancy or conjunction ONLY. Rahu casts no aspect, so no aspect path
        # can exist here even in principle.
        paths = [k for k in ("occupies_h4", "conjoins_4l") if r.get(k)]
        p.add("Rahu", "lock3_strong_influence", paths)
    return p


def _p4_participants(state: Dict[str, Any]) -> _Participants:
    """D4 4L · Mars (mandatory by Founder lock) · Lock-1 benefics contacting H4 OR 4L."""
    p = _Participants()
    p.add(state["lock4_dignity_and_affliction"]["fourth_lord"], "d4_fourth_lord", ["mandatory"])
    p.add("Mars", "bhumi_karaka", ["mandatory"])
    lock1 = state["lock1_benefic_cancellation"]
    for rec in lock1.get("benefic_contacts", []):
        p.add(rec["graha"], "lock1_benefic_contacting_h4_or_4l", list(rec.get("paths", [])))
    return p


_DERIVERS = {"P1": _p1_participants, "P2": _p2_participants,
             "P3": _p3_participants, "P4": _p4_participants}


# ── dasha reading ───────────────────────────────────────────────────────────

def read_current_dasha(dasha_facts: Any) -> Dict[str, Optional[str]]:
    """Current MD/AD graha identities from the CERTIFIED snapshot.

    Nothing is recomputed. An absent or malformed record yields None, which the
    caller turns into `unknown` — never into a negative.
    """
    md = ad = None
    if isinstance(dasha_facts, dict):
        m = dasha_facts.get("current_mahadasha")
        a = dasha_facts.get("current_antardasha")
        if isinstance(m, dict) and isinstance(m.get("planet"), str) and m["planet"]:
            md = m["planet"]
        if isinstance(a, dict) and isinstance(a.get("planet"), str) and a["planet"]:
            ad = a["planet"]
    return {"current_mahadasha": md, "current_antardasha": ad}


def _status(graha: Optional[str], participants: List[str]) -> str:
    if graha is None:
        return STATUS_UNKNOWN            # absence is never a negative
    return STATUS_MATCH if graha in participants else STATUS_NO_MATCH


def _summary(md: str, ad: str, applicable: bool) -> str:
    if not applicable:
        return SUMMARY_NA
    if md == STATUS_UNKNOWN and ad == STATUS_UNKNOWN:
        return SUMMARY_UNKNOWN
    if md == STATUS_MATCH and ad == STATUS_MATCH:
        return SUMMARY_BOTH
    if md == STATUS_MATCH:
        return SUMMARY_MD
    if ad == STATUS_MATCH:
        return SUMMARY_AD
    if STATUS_UNKNOWN in (md, ad):
        return SUMMARY_UNKNOWN
    return SUMMARY_NONE


# ── the block ───────────────────────────────────────────────────────────────

def build_dasha_context(property_state: Dict[str, Any],
                        dasha_facts: Any) -> Dict[str, Any]:
    """Concurrence context for the SELECTED state, plus per-state participants.

    Participants are derived for EVERY structurally matched state, but only the
    SELECTED state's set drives md_status/ad_status. A P3 or P4 concurrence can
    never override or masquerade as the selected P2 result.
    """
    for key in ("selected_state", "matched_states", "predicates",
                "lock1_benefic_cancellation", "lock2_eighth_twelfth_involvement",
                "lock3_mercury_rahu_influence", "lock4_dignity_and_affliction"):
        if key not in property_state:
            raise D4DashaError("accepted property state evidence is incomplete")

    selected = property_state["selected_state"]
    matched = list(property_state["matched_states"])

    # Only structurally matched states get participant sets. P5 gets none, and
    # no synthetic participant is invented for it.
    participants_by_state: Dict[str, Any] = {}
    for st in matched:
        acc = _DERIVERS[st](property_state)
        participants_by_state[st] = {
            "state": st,
            "participants": acc.records(),
            "participant_grahas": acc.grahas(),
        }

    is_fallback = (selected == "P5")
    if is_fallback:
        selected_records: List[Dict[str, Any]] = []
        selected_grahas: List[str] = []
        applicability = APPLICABILITY_NA
    else:
        blk = participants_by_state[selected]
        selected_records = blk["participants"]
        selected_grahas = blk["participant_grahas"]
        applicability = APPLICABILITY_APPLIES

    current = read_current_dasha(dasha_facts)
    md_status = _status(current["current_mahadasha"], selected_grahas)
    ad_status = _status(current["current_antardasha"], selected_grahas)

    return {
        "engine": {
            "d4_dasha_version": D4_DASHA_VERSION,
            "vimshottari_recomputed": False,
            "dasha_source": "certified_chart_snapshot",
            "predicates_re_evaluated": False,
            "provider_classification_authority": False,
            "date_prediction_published": False,
            "probability_published": False,
        },
        "authority": "context_only",
        "timing_policy": "structural_concurrence_not_activation",
        "selected_state": selected,
        "timing_applicability": applicability,
        "selected_state_participants": selected_records,
        "selected_state_participant_grahas": selected_grahas,
        "participants_by_state": participants_by_state,
        "current_mahadasha": current["current_mahadasha"],
        "current_antardasha": current["current_antardasha"],
        "md_status": md_status,
        "ad_status": ad_status,
        "concurrence_summary": _summary(md_status, ad_status, not is_fallback),
        "note": ("a concurrence means only that the current Dasha lord is one of the "
                 "grahas structurally participating in the selected D4 state; it "
                 "asserts no event, no timing and no outcome"),
    }
