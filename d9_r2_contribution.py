"""D9-R2-002-CORR-03 · d9_r2_contribution · Founder-ratified derivation.

Every rule here is Founder-locked. The module contributes set operations and
nothing else — no scoring, no weighting, no ranking.

The Founder grid is RATIFIED and lives in `d9_r2_doctrine`. It is INJECTED here
rather than imported so a missing grid fails loudly at wiring time instead of
yielding an empty signal on every chart that looks like a real finding.

HISTORICAL NOTES
  · CORR-03 replaced a Dev precedence proposal with the ratified rule, in which
    the sign REFINES BUT NEVER EXPANDS, and deleted `DoctrineTopologyUnresolved`
    once Founder doctrine covered the topology it guarded.
  · CORR-04 fixed two bugs: an occupied house with no permitted occupants no
    longer falls through to the house lord, and the dissenting domain in a
    pairwise convergence always supplies its contextual vector.
"""

from typing import Dict, FrozenSet, List, Optional, Sequence, Set, Tuple

from d9_r2_doctrine import (
    Archetype,
    CONTRIBUTION_DOMAINS,
    CONTRIBUTION_EXCLUDED_GRAHAS,
    CONTRIBUTION_DOMAIN_FRAMES,
    CONTRIBUTION_OCCUPANT_GRAHAS,
    Convergence,
    MULTI_POLAR_ROLES,
    PAIRWISE_DISSENT_KEY,
    PAIRWISE_DISSENT_ROLE,
    PAIRWISE_MODIFIER_DOMAIN,
    PAIRWISE_PRECEDENCE,
    SUPPRESSED_EMITS_CUSTOMER_CARD,
    UNIFIED_PURPOSE_LABEL,
)


class ContributionGrid:
    """The Founder grid, injected. Never defaulted, never guessed."""

    def __init__(self, graha_map: Dict[str, FrozenSet[Archetype]],
                 sign_map: Dict[str, FrozenSet[Archetype]]):
        if not graha_map or not sign_map:
            raise ValueError(
                "Founder Contribution grid injection is empty; doctrine "
                "contract violated")
        self.graha = graha_map
        self.sign = sign_map


# ═════════════════════════════════════════════════════════════════════════════
# DOMAIN DERIVATION · Founder-ratified
# ═════════════════════════════════════════════════════════════════════════════

def resolve_domain(house: int,
                   occupants: Sequence[str],
                   house_lord: Optional[str],
                   house_sign: Optional[str],
                   grid: ContributionGrid) -> Dict[str, object]:
    """One Karakāṁśa domain → one archetype set.

    FRAME: the EXACT per-domain name — `KARAKAMSHA_H5_D1_FRAME`,
    `KARAKAMSHA_H9_D1_FRAME` or `KARAKAMSHA_H10_D1_FRAME` — D1 sign positions
    counted from the Karakāṁśa Lagna. Never the wildcard. Callers supply occupancy in that frame; this function does
    not compute it and cannot detect a caller using the wrong one, so the frame
    is recorded in the output for a downstream reader to check.

        if occupied:  primary = classical occupants + Ketu if present
        else:         primary = the house lord
        A_graha = union of archetypes over primary
        A_sign  = archetypes of the house sign
        signal  = (A_graha ∩ A_sign) if non-empty else A_graha

    THE SIGN REFINES BUT NEVER EXPANDS. When the sign shares nothing with the
    grahas it is discarded rather than added, so a sign can narrow a reading and
    can never introduce an archetype the grahas do not carry.

    RAHU DOES NOT CONTRIBUTE — it is not in the Founder grid. KETU DOES, and is
    still never strength-eligible. Two different rules, one graha.

    A HOUSE OCCUPIED ONLY BY RAHU IS STILL OCCUPIED. It yields `basis_kind
    "occupant"`, an empty primary set and an empty signal — it does NOT fall
    through to the lord, because the lord fallback exists for an empty house.
    """
    if house not in CONTRIBUTION_DOMAINS:
        raise KeyError(f"house {house} is not a contribution domain")

    # CORR-04 · OCCUPANCY IS A PROPERTY OF THE HOUSE, NOT OF THE ELIGIBLE SET.
    #
    # Flight 4 asked "are there any ELIGIBLE occupants?" and fell through to the
    # lord when there were none. On a house occupied only by Rahu that produced
    # house-lord evidence for a house that is not empty — the lord fallback is
    # for an EMPTY house, and Rahu occupying it does not make it empty.
    #
    # An occupied house with no permitted occupants yields an EMPTY signal, which
    # is a real answer: the house is spoken for, and nothing in it contributes.
    house_is_occupied = bool(occupants)
    eligible = [g for g in occupants
                if g in CONTRIBUTION_OCCUPANT_GRAHAS
                and g not in CONTRIBUTION_EXCLUDED_GRAHAS]

    if house_is_occupied:
        primary, basis_kind = eligible, "occupant"
    elif house_lord and house_lord not in CONTRIBUTION_EXCLUDED_GRAHAS:
        primary, basis_kind = [house_lord], "house_lord"
    else:
        primary, basis_kind = [], "none"

    a_graha: Set[Archetype] = set()
    for g in primary:
        a_graha |= set(grid.graha.get(g) or ())

    a_sign: Set[Archetype] = set(grid.sign.get(house_sign) or ())
    refined = a_graha & a_sign
    signal = refined if refined else a_graha

    return {
        "house": house,
        "domain": CONTRIBUTION_DOMAINS[house],
        "frame": CONTRIBUTION_DOMAIN_FRAMES[house],
        "signal": frozenset(signal),
        "basis_kind": basis_kind,
        "primary_grahas": list(primary),
        "a_graha": frozenset(a_graha),
        "a_sign": frozenset(a_sign),
        "sign_refined": bool(refined),
    }


# ═════════════════════════════════════════════════════════════════════════════
# CROSS-DOMAIN CONVERGENCE · Founder-ratified · set intersection only
# ═════════════════════════════════════════════════════════════════════════════

def converge(h5: FrozenSet[Archetype],
             h9: FrozenSet[Archetype],
             h10: FrozenSet[Archetype]) -> Dict[str, object]:
    """Four states, in strict order.

    UNIFIED_PURPOSE       H5 ∩ H9 ∩ H10 non-empty. Multiple archetypes are ALL
                          retained as the integrated Primary Mode.
    PAIRWISE              any pair intersects. The dissenting domain ALWAYS
                          supplies a contextual vector — H10 Functional/Impact,
                          H9 Ethical Functional, H5 Innate/Aptitude Modifier.
                          H9 ∩ H10 takes precedence when several compete.
    COMPOUND_MULTI_POLAR  every pair empty. H10 Primary Impact Vector ·
                          H9 Ethical Driver · H5 Innate Aptitude.
    SUPPRESSED            every domain signal empty. No customer card; the
                          selector attaches the authorised D9 Lagna maturity
                          material. No Swāṁśa proposition is claimed here.
    """
    domains = {5: set(h5), 9: set(h9), 10: set(h10)}

    if not any(domains.values()):
        # Flight 9 · the discriminator names ONLY what is authorised. Flight 8
        # removed the Swāṁśa claim from the selector and left it here, so the
        # deterministic substrate still carried a false authority claim for a
        # later wiring path to pick up. Removing it downstream is not removing
        # it.
        return {"convergence": Convergence.SUPPRESSED,
                "emits_customer_card": SUPPRESSED_EMITS_CUSTOMER_CARD,
                "fallback": "d9_lagna_maturity"}

    triple = domains[5] & domains[9] & domains[10]
    if triple:
        return {"convergence": Convergence.UNIFIED_PURPOSE,
                "label": UNIFIED_PURPOSE_LABEL,
                "primary_mode": sorted(a.value for a in triple),
                "integrated": len(triple) > 1,
                "supporting_domains": [5, 9, 10]}

    # Pairs in ratified precedence order. H9 ∩ H10 first — the tie is decided by
    # doctrine, not by iteration order, and the constant makes that legible.
    for a, b in PAIRWISE_PRECEDENCE:
        inter = domains[a] & domains[b]
        if inter:
            competing = [f"H{x}∩H{y}" for x, y in PAIRWISE_PRECEDENCE
                         if (x, y) != (a, b) and domains[x] & domains[y]]
            # CORR-04 · THE DISSENTING DOMAIN ALWAYS SUPPLIES A VECTOR.
            #
            # Flight 4 emitted a dissenting signal only for H9∩H10, where H5
            # becomes the aptitude modifier — so H5∩H9 and H5∩H10 silently
            # dropped the third domain's evidence. The dissenting house is not
            # noise: it is contextual vector evidence, and it is preserved rather
            # than promoted to a second winner.
            dissenting = ({5, 9, 10} - {a, b}).pop()
            out = {"convergence": Convergence.PAIRWISE,
                   "primary_contribution_mode": sorted(x.value for x in inter),
                   "agreeing_domains": [a, b],
                   "dissenting_domain": dissenting,
                   "competing_pairs": competing,
                   "precedence_applied": bool(competing)}
            signal = sorted(x.value for x in domains[dissenting])
            role = PAIRWISE_DISSENT_ROLE[dissenting]
            out["dissenting_role"] = role
            out["dissenting_signal"] = signal
            # Named alias per role, so a consumer reads the doctrinal name.
            out[PAIRWISE_DISSENT_KEY[dissenting]] = signal
            if dissenting == PAIRWISE_MODIFIER_DOMAIN:
                out["aptitude_modifier_domain"] = PAIRWISE_MODIFIER_DOMAIN
            return out

    return {"convergence": Convergence.COMPOUND_MULTI_POLAR,
            "roles": {MULTI_POLAR_ROLES[h]: sorted(a.value for a in domains[h])
                      for h in (10, 9, 5)},
            "primary_impact_vector": sorted(a.value for a in domains[10]),
            "ethical_driver": sorted(a.value for a in domains[9]),
            "innate_aptitude": sorted(a.value for a in domains[5])}
