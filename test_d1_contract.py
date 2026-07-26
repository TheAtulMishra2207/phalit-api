"""
test_d1_contract.py — contract tests for the D1 engine response models.

Fixture: the founder natal chart (Libra Lagna 20.06°), matching the closed
chart engine 1.1.0 values. The doctrinal tests construct INVALID payloads and
assert the contract rejects them — the node-aspect ruling is enforced by the
models, not by the good behavior of engine code.
"""
import pytest
from datetime import datetime, timezone
from pydantic import ValidationError

from d1_contract import (
    D1PrepareResponse, EnginePolicy, GrahaState, HouseState, AspectEdge,
    FunctionalRole, FunctionalRoleKind, NodalAxis, Graha, AspectKind, Dignity,
    ASPECT_CASTERS, SPECIAL_DRISHTI, NODE_ASPECT_POLICY,
)

SIGNS = ["Aries","Taurus","Gemini","Cancer","Leo","Virgo","Libra","Scorpio",
         "Sagittarius","Capricorn","Aquarius","Pisces"]
LORDS = [Graha.MARS, Graha.VENUS, Graha.MERCURY, Graha.MOON, Graha.SUN, Graha.MERCURY,
         Graha.VENUS, Graha.MARS, Graha.JUPITER, Graha.SATURN, Graha.SATURN, Graha.JUPITER]

def founder_payload():
    """Libra Lagna; placements per chart engine 1.1.0 (houses Whole Sign)."""
    lagna_idx = 6
    def house_of(sign_idx): return (sign_idx - lagna_idx) % 12 + 1
    placements = {
        Graha.SUN: (3, 5.9), Graha.MOON: (0, 17.2), Graha.MARS: (6, 24.4068),
        Graha.MERCURY: (3, 25.1), Graha.JUPITER: (8, 9.8), Graha.VENUS: (4, 2.3),
        Graha.SATURN: (6, 16.5), Graha.RAHU: (1, 11.0), Graha.KETU: (7, 11.0),
    }
    grahas = []
    for g, (si, deg) in placements.items():
        grahas.append(GrahaState(
            graha=g, sign_index=si, sign=SIGNS[si], degree_in_sign=deg,
            house=house_of(si),
            dignity=Dignity.NEUTRAL if g not in (Graha.RAHU, Graha.KETU) else None,
            dispositor=LORDS[si],
        ))
    occupants = {}
    for gs in grahas: occupants.setdefault(gs.house, []).append(gs.graha)
    aspects = []
    for caster in ASPECT_CASTERS:
        ch = next(g.house for g in grahas if g.graha == caster)
        offs = [7] + list(SPECIAL_DRISHTI.get(caster, ()))
        kindmap = {7: AspectKind.SEVENTH, 4: AspectKind.FOURTH, 8: AspectKind.EIGHTH,
                   5: AspectKind.FIFTH, 9: AspectKind.NINTH, 3: AspectKind.THIRD, 10: AspectKind.TENTH}
        for off in offs:
            th = (ch - 1 + off - 1) % 12 + 1
            aspects.append(AspectEdge(source=caster, kind=kindmap[off],
                                      target_house=th, target_grahas=occupants.get(th, [])))
    aspected_by = {}
    for a in aspects: aspected_by.setdefault(a.target_house, []).append(a.source)
    houses = [HouseState(house=h, sign_index=(lagna_idx + h - 1) % 12,
                         sign=SIGNS[(lagna_idx + h - 1) % 12],
                         lord=LORDS[(lagna_idx + h - 1) % 12],
                         occupants=occupants.get(h, []),
                         aspected_by=sorted(set(aspected_by.get(h, [])), key=lambda g: g.value))
              for h in range(1, 13)]
    lordships = {}
    for h in houses: lordships.setdefault(h.lord, []).append(h.house)
    roles = []
    for g in Graha:
        if g in (Graha.RAHU, Graha.KETU):
            roles.append(FunctionalRole(graha=g, lordships=[], role=FunctionalRoleKind.NODE_AXIS,
                                        basis="nature via nodal axis, dispositor and association"))
        elif g == Graha.SATURN:
            roles.append(FunctionalRole(graha=g, lordships=lordships[g], role=FunctionalRoleKind.YOGAKARAKA,
                                        basis="BPHS 34: kendra (4) + trikona (5) lordship for Libra Lagna"))
        else:
            roles.append(FunctionalRole(graha=g, lordships=lordships.get(g, []),
                                        role=FunctionalRoleKind.FUNCTIONAL_NEUTRAL,
                                        basis="placeholder functional derivation for contract fixture"))
    return D1PrepareResponse(
        chart_token="tok_founder_1984",
        lagna_sign_index=lagna_idx, lagna_sign="Libra", lagna_degree=20.0586,
        grahas=grahas, houses=houses, aspects=aspects, functional_roles=roles,
        nodal_axis=NodalAxis(rahu_house=house_of(1), ketu_house=house_of(7),
                             rahu_sign="Taurus", ketu_sign="Scorpio",
                             rahu_dispositor=Graha.VENUS, ketu_dispositor=Graha.MARS),
        generated_at=datetime.now(timezone.utc),
    )

# ── happy path ───────────────────────────────────────────────────────────────

def test_founder_fixture_validates():
    p = founder_payload()
    assert p.policy.node_aspect_policy == "no_independent_drishti"
    assert p.policy.aspect_policy_version == "parashari-d1-1.0"
    assert len(p.aspects) == 7 + 2 + 2 + 2   # seven 7ths + Mars/Jup/Sat specials

def test_saturn_yogakaraka_for_libra():
    p = founder_payload()
    sat = next(r for r in p.functional_roles if r.graha == Graha.SATURN)
    assert sat.role == FunctionalRoleKind.YOGAKARAKA
    assert sorted(sat.lordships) == [4, 5]

def test_nodes_receive_aspects():
    """Ruling: nodes RECEIVE aspects — they appear as targets, never sources."""
    p = founder_payload()
    received = [a for a in p.aspects if Graha.RAHU in a.target_grahas or Graha.KETU in a.target_grahas]
    assert received, "fixture should have at least one dṛṣṭi landing on a node"
    assert all(a.source not in (Graha.RAHU, Graha.KETU) for a in p.aspects)

# ── doctrinal enforcement: the ruling is validated, not assumed ─────────────

def test_node_drishti_rejected():
    with pytest.raises(ValidationError, match="no_independent_drishti"):
        AspectEdge(source=Graha.RAHU, kind=AspectKind.SEVENTH, target_house=5)

def test_ketu_drishti_rejected():
    with pytest.raises(ValidationError, match="no_independent_drishti"):
        AspectEdge(source=Graha.KETU, kind=AspectKind.NINTH, target_house=2)

def test_579_extension_not_expressible_for_nodes():
    """The 5/7/9 node extension cannot be smuggled through any kind value."""
    for kind in AspectKind:
        with pytest.raises(ValidationError):
            AspectEdge(source=Graha.RAHU, kind=kind, target_house=1)

def test_special_drishti_ownership():
    with pytest.raises(ValidationError, match="belongs to Mars"):
        AspectEdge(source=Graha.SUN, kind=AspectKind.EIGHTH, target_house=3)
    with pytest.raises(ValidationError, match="belongs to Saturn"):
        AspectEdge(source=Graha.JUPITER, kind=AspectKind.TENTH, target_house=3)

def test_house_cannot_be_node_aspected():
    with pytest.raises(ValidationError, match="cannot be aspected by nodes"):
        HouseState(house=1, sign_index=6, sign="Libra", lord=Graha.VENUS,
                   aspected_by=[Graha.RAHU])

def test_nodes_own_no_houses():
    with pytest.raises(ValidationError, match="own no rāśi"):
        HouseState(house=1, sign_index=6, sign="Libra", lord=Graha.KETU)

def test_node_role_must_be_axis():
    with pytest.raises(ValidationError, match="node_axis"):
        FunctionalRole(graha=Graha.RAHU, lordships=[], role=FunctionalRoleKind.FUNCTIONAL_MALEFIC,
                       basis="wrongly typed nodal nature")

def test_axis_must_be_opposite():
    with pytest.raises(ValidationError, match="opposite"):
        NodalAxis(rahu_house=8, ketu_house=3, rahu_sign="Taurus", ketu_sign="Scorpio",
                  rahu_dispositor=Graha.VENUS, ketu_dispositor=Graha.MARS)

def test_policy_is_versioned_not_silent():
    """A different node policy is a NEW literal — the current one cannot express it."""
    with pytest.raises(ValidationError):
        EnginePolicy(node_aspect_policy="rahu_ketu_579")

def test_missing_seventh_rejected():
    p = founder_payload()
    trimmed = [a for a in p.aspects if not (a.source == Graha.MOON and a.kind == AspectKind.SEVENTH)]
    with pytest.raises(ValidationError, match="missing: Moon 7th"):
        D1PrepareResponse(**{**p.dict(), "aspects": [a.dict() for a in trimmed]})

def test_wrong_sun_seventh_target_rejected():
    # QA step-3 blocker: geometry. Sun's 7th must land opposite Sun's own house.
    p = founder_payload()
    dump = p.dict()
    for a in dump["aspects"]:
        if a["source"] == "Sun" and a["kind"] == "7th":
            a["target_house"] = a["target_house"] % 12 + 1   # deliberately wrong
            break
    with pytest.raises(ValidationError, match="Sun 7th .* must land on house"):
        D1PrepareResponse(**dump)

def test_wrong_mars_eighth_target_rejected():
    p = founder_payload()
    dump = p.dict()
    for a in dump["aspects"]:
        if a["source"] == "Mars" and a["kind"] == "8th":
            a["target_house"] = a["target_house"] % 12 + 1
            break
    with pytest.raises(ValidationError, match="Mars 8th .* must land on house"):
        D1PrepareResponse(**dump)

def test_duplicate_source_kind_edge_rejected():
    p = founder_payload()
    dump = p.dict()
    sun7 = next(a for a in dump["aspects"] if a["source"] == "Sun" and a["kind"] == "7th")
    dump["aspects"] = dump["aspects"] + [dict(sun7)]   # byte-identical duplicate
    with pytest.raises(ValidationError, match="duplicate"):
        D1PrepareResponse(**dump)

def test_nine_grahas_required():
    p = founder_payload()
    with pytest.raises(ValidationError):
        D1PrepareResponse(**{**p.dict(), "grahas": [g.dict() for g in p.grahas[:8]]})
