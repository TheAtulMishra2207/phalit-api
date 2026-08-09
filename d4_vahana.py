"""
d4_vahana.py — D4-005 · VĀHANA / VEHICLES & MATERIAL COMFORTS, evidence only.

MECHANICAL LAYER ONLY. This module publishes certified D4 facts about Venus and
the D4 Vāhana Sthāna. It produces NO tier, NO count, NO score, NO probability
and NO purchase timing, because the vehicle/comfort taxonomy is NOT
Founder-locked. `tier_classification_policy = "not_defined_pending_founder_lock"`
is published in its place, so a reader can see that the absence is deliberate
rather than an omission.

NO SECOND CONTACT ENGINE. The conjunction and aspect semantics are the ones
D4-003 already certified, reached by REUSING d4_property_state's certified fact
reader rather than restating them here:

  * conjunction  = same D4 house, between TWO DISTINCT grahas
  * aspect       = the certified D4 manifest only, in which Rahu and Ketu
                   carry no edges at all

Importing that reader is deliberate. A private copy of "what a contact is"
living in two modules is exactly how two engines that agree today come apart
later, and D4-003 already paid for getting these rules right.

NO SUBSTITUTION. Where a D4 fact is absent it stays absent. D1 Venus is never
substituted for D4 Venus, and no D16 fact is consulted — D16 owns its own
Vāhana apparatus and this module does not import, read or mention it.
"""

from __future__ import annotations

from typing import Any, Dict

# REUSED, NOT REDEFINED. See the module docstring: one definition of contact.
from d4_property_state import _Facts as CertifiedFactReader

D4_VAHANA_VERSION = "1.0.0"

VAHANA_KARAKA = "Venus"


class D4VahanaError(ValueError):
    """The certified facts are not shaped as this module requires. Internal
    only — the route converts it to a neutral correlated error."""


def build_vahana_evidence(facts: Dict[str, Any], doctrine: Any) -> Dict[str, Any]:
    """Venus and Vāhana Sthāna evidence, selected from certified D4 facts.

    Nothing here recalculates a placement, a dignity or an aspect. Every value
    is read from `build_d4_facts()` output or derived from it using the same
    certified contact rules D4-003 uses.
    """
    try:
        F = CertifiedFactReader(facts, doctrine)
    except Exception as exc:                       # pragma: no cover - guard
        raise D4VahanaError("certified D4 facts are incomplete") from exc

    if VAHANA_KARAKA not in F.grahas:
        raise D4VahanaError("certified facts carry no Venus record")

    venus = F.grahas[VAHANA_KARAKA]
    fl = F.fourth_lord
    h4 = facts["fourth_house"]

    # ── the four direct contact paths, each independent ────────────────────
    occupies_h4 = F.occupies(VAHANA_KARAKA, 4)
    conjoins_4l = F.conjoins(VAHANA_KARAKA, fl)     # distinct grahas only
    aspects_h4 = F.aspects_house(VAHANA_KARAKA, 4)
    aspects_4l = F.aspects_graha(VAHANA_KARAKA, fl)
    paths = {
        "venus_occupies_h4": occupies_h4,
        "venus_conjoins_4l": conjoins_4l,
        "venus_aspects_h4": aspects_h4,
        "venus_aspects_4l": aspects_4l,
    }

    # Venus IS the 4th Lord on Taurus and Libra D4 lagnas. Conjunction with
    # itself is excluded under the D4-003 self-conjunction policy, so the
    # coincidence is PUBLISHED rather than allowed to look like a contact.
    venus_is_fourth_lord = (fl == VAHANA_KARAKA)

    received = list(facts["aspects"]["received_by_graha"].get(VAHANA_KARAKA, []))

    return {
        "engine": {
            "d4_vahana_version": D4_VAHANA_VERSION,
            "karaka": VAHANA_KARAKA,
            "conjunction_rule": "same_d4_house_no_orb",
            "self_conjunction_policy": "excluded",
            "aspect_source": "certified_d4_manifest",
            # The absence of a taxonomy is DECLARED, not silently filled in.
            "tier_classification_policy": "not_defined_pending_founder_lock",
            "vehicle_tier_published": False,
            "vehicle_count_published": False,
            "acquisition_timing_published": False,
            "weighted_score_published": False,
            "provider_classification_authority": False,
            "d16_evidence_consumed": False,
            "d1_substituted_for_missing_d4": False,
        },
        "authority": "d4_primary",
        "venus": {
            "graha": VAHANA_KARAKA,
            "d4_sign": venus["d4_sign"],
            "d4_sign_index": venus["d4_sign_index"],
            "d4_house": venus["d4_house"],
            "d4_dignity": venus["dignity"].get("dignity"),
            "vargottama": venus["vargottama"],
            "aspects_received": received,
            "aspects_cast": list(venus["aspects_cast"]),
            "is_fourth_lord": venus_is_fourth_lord,
        },
        "contact_paths": paths,
        # ANY-OF the four. Not a count, not a strength, not a tier.
        "direct_venus_vahana_contact": any(paths.values()),
        "vahana_sthana": {
            "house": h4["house"],
            "sign": h4["sign"],
            "sign_index": h4["sign_index"],
            "occupants": list(h4["occupants"]),
            "aspects_received": list(h4["aspects_received"]),
            "fourth_lord": {
                "graha": fl,
                "d4_sign": F.grahas[fl]["d4_sign"],
                "d4_sign_index": F.grahas[fl]["d4_sign_index"],
                "d4_house": F.grahas[fl]["d4_house"],
                "d4_dignity": F.grahas[fl]["dignity"].get("dignity"),
                "vargottama": F.grahas[fl]["vargottama"],
                "aspects_received": list(
                    facts["aspects"]["received_by_graha"].get(fl, [])),
            },
        },
        "note": ("mechanical D4 evidence only; no vehicle tier, count, score or "
                 "acquisition timing is produced, and none may be inferred from "
                 "this block until the taxonomy is locked"),
    }
