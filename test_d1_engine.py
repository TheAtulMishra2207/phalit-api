"""
test_d1_engine.py — KAR-093 step 4: engine tests + the seven reclassified
regression findings (KAR-080/081/082/085/086/089/090) and the two doctrine
requirements (KAR-083/084), each labeled with its ticket.

Fixture: founder natal (Libra Lagna 20.0586°), with the exact KAR-080 repro
value — Jupiter Sagittarius 11.70°, certified dignity Own Sign.
"""
import pytest
from d1_contract import (AspectKind, Dignity, FunctionalRoleKind, Graha)
from d1_engine import (
    CertifiedChart, ChartGraha, D1EngineError, DIGNITY_LABELS,
    InfluencePolarity, NaturalNature, compute_d1, resolve_functional_roles,
    build_house_influences, InfluenceEvidence, HouseInfluence,
)
from d1_functional_roles import (
    FunctionalRoleV1, FunctionalNature, VerseYogaStatus, MarakaStatus, CellProvenance,
)

def _fr(graha, nature, vyoga=VerseYogaStatus.NONE, yk=False, maraka=MarakaStatus.NONE,
        prov=CellProvenance.EXPLICIT_VERSE):
    return FunctionalRoleV1(graha=graha, lordships=[], functional_nature=nature,
                            verse_yoga_status=vyoga, ownership_yogakaraka=yk,
                            maraka_status=maraka, nature_provenance=prov,
                            verse="BPHS 34.test", note="test role")

def lon(sign_index, deg): return sign_index * 30.0 + deg

def synthetic_unresolved(monkeypatch, lagna):
    """BPHS 34.19-44 is fully populated, so no real Lagna is withheld. The
    review-gate path is exercised by monkeypatching one row to _REVIEW."""
    import d1_functional_roles as m
    row = {g: m._REVIEW for g in (Graha.SUN, Graha.MOON, Graha.MARS, Graha.MERCURY,
                                  Graha.JUPITER, Graha.VENUS, Graha.SATURN)}
    monkeypatch.setitem(m.BPHS34_MATRIX, lagna, row)
    from d1_engine import CertifiedChart
    c = founder_chart()
    return CertifiedChart(chart_token=c.chart_token, lagna_sign_index=lagna,
                          lagna_degree=10.0, grahas=c.grahas)

def founder_chart(**overrides):
    g = {
        Graha.SUN:     ChartGraha(sign_index=3, degree_in_sign=5.9,  longitude=lon(3, 5.9),  dignity=Dignity.NEUTRAL),
        Graha.MOON:    ChartGraha(sign_index=0, degree_in_sign=17.2, longitude=lon(0, 17.2), dignity=Dignity.NEUTRAL),
        Graha.MARS:    ChartGraha(sign_index=6, degree_in_sign=24.4068, longitude=lon(6, 24.4068), dignity=Dignity.NEUTRAL),
        Graha.MERCURY: ChartGraha(sign_index=3, degree_in_sign=25.1, longitude=lon(3, 25.1), dignity=Dignity.FRIEND),
        # KAR-080 repro value: Sag 11.70°, certified as OWN SIGN by engine 1.1.0
        Graha.JUPITER: ChartGraha(sign_index=8, degree_in_sign=11.70, longitude=lon(8, 11.70), dignity=Dignity.OWN),
        Graha.VENUS:   ChartGraha(sign_index=4, degree_in_sign=2.3,  longitude=lon(4, 2.3),  dignity=Dignity.NEUTRAL),
        Graha.SATURN:  ChartGraha(sign_index=6, degree_in_sign=16.5, longitude=lon(6, 16.5), dignity=Dignity.EXALTED),
        Graha.RAHU:    ChartGraha(sign_index=1, degree_in_sign=11.0, longitude=lon(1, 11.0)),
        Graha.KETU:    ChartGraha(sign_index=7, degree_in_sign=11.0, longitude=lon(7, 11.0)),
    }
    g.update(overrides)
    return CertifiedChart(chart_token="tok_founder_1984",
                          lagna_sign_index=6, lagna_degree=20.0586, grahas=g)

# ── engine fills the accepted contract ───────────────────────────────────────

def test_contract_payload_validates():
    resp, doc = compute_d1(founder_chart())
    assert len(resp.aspects) == 13
    assert resp.policy.node_aspect_policy == "no_independent_drishti"

# ── KAR-080: dignity is consumed, never recomputed ───────────────────────────

def test_kar080_certified_dignity_passes_through_unchanged():
    resp, _ = compute_d1(founder_chart())
    jup = next(g for g in resp.grahas if g.graha == Graha.JUPITER)
    assert jup.sign == "Sagittarius" and abs(jup.degree_in_sign - 11.70) < 1e-9
    assert jup.dignity == Dignity.OWN, "Sag 11.70° is Own Sign per certified engine; module must not override"

def test_kar080_missing_dignity_is_an_error_not_a_computation():
    broken = founder_chart(**{Graha.JUPITER: ChartGraha(
        sign_index=8, degree_in_sign=11.70, longitude=lon(8, 11.70), dignity=None)})
    with pytest.raises(D1EngineError, match="does not compute dignity"):
        compute_d1(broken)

def test_kar080_no_dignity_table_exists_in_module():
    import d1_engine, inspect
    src = inspect.getsource(d1_engine)
    for marker in ("DIGNITY_SCORES", "EXALTATION", "MOOLATRIKONA_RANGE", "getScore"):
        assert marker not in src, f"engine must not contain a dignity computation table ({marker})"

# ── KAR-081: one canonical aspect graph supplies every section ───────────────

def test_kar081_houses_aspected_by_equals_the_manifest():
    resp, _ = compute_d1(founder_chart())
    derived = {}
    for e in resp.aspects: derived.setdefault(e.target_house, set()).add(e.source)
    for h in resp.houses:
        assert set(h.aspected_by) == derived.get(h.house, set()), \
            f"house {h.house} aspected_by diverges from the single manifest"

def test_kar081_symmetry_of_graha_visibility():
    # If X's dṛṣṭi lands on Y's house, Y appears in that edge's target_grahas —
    # the two directions of the KAR-081 contradiction read one structure.
    resp, _ = compute_d1(founder_chart())
    house_of = {g.graha: g.house for g in resp.grahas}
    for e in resp.aspects:
        for g, h in house_of.items():
            if h == e.target_house:
                assert g in e.target_grahas

# ── KAR-082: net polarity invariants, by construction ────────────────────────

def test_kar082_positive_only_cannot_be_afflicting():
    ev_all_good = {1: [Graha.JUPITER, Graha.VENUS]}
    natures = {Graha.JUPITER: NaturalNature.BENEFIC, Graha.VENUS: NaturalNature.BENEFIC}
    func = {Graha.JUPITER: _fr(Graha.JUPITER, FunctionalNature.BENEFIC),
            Graha.VENUS: _fr(Graha.VENUS, FunctionalNature.BENEFIC)}
    infl = build_house_influences(ev_all_good, [], natures, func)
    h1 = next(x for x in infl if x.house == 1)
    assert all(e.polarity == InfluencePolarity.SUPPORTIVE for e in h1.evidence)
    assert h1.net == InfluencePolarity.SUPPORTIVE

def test_kar082_adverse_only_cannot_be_positive():
    ev_all_bad = {1: [Graha.SATURN]}
    natures = {Graha.SATURN: NaturalNature.MALEFIC}
    func = {Graha.SATURN: _fr(Graha.SATURN, FunctionalNature.MALEFIC)}
    infl = build_house_influences(ev_all_bad, [], natures, func)
    h1 = next(x for x in infl if x.house == 1)
    assert h1.net == InfluencePolarity.CHALLENGING

def test_kar082_net_is_function_of_displayed_evidence():
    resp, doc = compute_d1(founder_chart())
    for hi in doc.house_influences:
        # net aggregates the ASSESSED evidence only (unassessed removed first)
        assessed = {e.polarity for e in hi.evidence if e.polarity != InfluencePolarity.UNASSESSED}
        if not assessed: assert hi.net == InfluencePolarity.UNASSESSED
        elif assessed == {InfluencePolarity.SUPPORTIVE}: assert hi.net == InfluencePolarity.SUPPORTIVE
        elif assessed == {InfluencePolarity.CHALLENGING}: assert hi.net == InfluencePolarity.CHALLENGING
        else: assert hi.net == InfluencePolarity.MIXED

def test_kar082_empty_evidence_is_unassessed_never_mixed():
    """QA MID-HIGH defect: no evidence is not mixed evidence."""
    infl = build_house_influences({}, [], {}, {})
    for hi in infl:
        assert hi.evidence == []
        assert hi.net == InfluencePolarity.UNASSESSED
        assert hi.net != InfluencePolarity.MIXED

def test_kar082_mixed_reserved_for_conflicting_evidence():
    natures = {Graha.JUPITER: NaturalNature.BENEFIC, Graha.SATURN: NaturalNature.MALEFIC}
    func = {Graha.JUPITER: _fr(Graha.JUPITER, FunctionalNature.BENEFIC),
            Graha.SATURN: _fr(Graha.SATURN, FunctionalNature.MALEFIC)}
    infl = build_house_influences({1: [Graha.JUPITER, Graha.SATURN]}, [], natures, func)
    h1 = next(x for x in infl if x.house == 1)
    assert {e.polarity for e in h1.evidence} == {InfluencePolarity.SUPPORTIVE, InfluencePolarity.CHALLENGING}
    assert h1.net == InfluencePolarity.MIXED

def test_kar082_mixed_only_evidence_resolves_mixed():
    natures = {Graha.SATURN: NaturalNature.MALEFIC}
    func = {Graha.SATURN: _fr(Graha.SATURN, FunctionalNature.MALEFIC, yk=True)}  # malefic nature + ownership support → mixed
    infl = build_house_influences({1: [Graha.SATURN]}, [], natures, func)
    h1 = next(x for x in infl if x.house == 1)
    assert all(e.polarity == InfluencePolarity.MIXED for e in h1.evidence)
    assert h1.net == InfluencePolarity.MIXED

# ── KAR-083: dignity never reverses natural maleficence ──────────────────────

def test_kar083_exalted_saturn_stays_natural_malefic():
    resp, doc = compute_d1(founder_chart())
    sat_state = next(g for g in resp.grahas if g.graha == Graha.SATURN)
    assert sat_state.dignity == Dignity.EXALTED
    sat_nat = next(n for n in doc.natures if n.graha == Graha.SATURN)
    assert sat_nat.natural_nature == NaturalNature.MALEFIC, \
        "exaltation must not flip natural nature (KAR-083)"

def test_kar083_saturn_support_flows_from_yogakaraka_not_exaltation():
    # Founder chart (Libra): Saturn is exalted AND an ownership yogakāraka.
    resp, doc = compute_d1(founder_chart())
    sat_role = next(r for r in resp.functional_roles if r.graha == Graha.SATURN)
    assert sat_role.role == FunctionalRoleKind.YOGAKARAKA
    # KAR-083 invariant: dignity is NEVER the basis for the role or the polarity.
    assert "dignit" not in sat_role.basis.lower()
    for hi in doc.house_influences:
        for e in hi.evidence:
            if e.source == Graha.SATURN:
                assert "dignit" not in e.basis.lower()

def test_kar083_unresolved_doctrine_yields_unassessed_not_fabricated(monkeypatch):
    """Where a graha's functional nature is still review_required, its polarity
    must be UNASSESSED rather than a fabricated supportive/challenging. The
    nodes are exempt: their maleficence comes from a general rule, not from
    per-Lagna doctrine, so they resolve normally."""
    _, doc = compute_d1(synthetic_unresolved(monkeypatch, 3))
    classical = {Graha.SUN, Graha.MOON, Graha.MARS, Graha.MERCURY,
                 Graha.JUPITER, Graha.VENUS, Graha.SATURN}
    seen = 0
    for hi in doc.house_influences:
        for e in hi.evidence:
            if e.source in classical:
                assert e.polarity == InfluencePolarity.UNASSESSED, e.source.value
                seen += 1
            else:
                assert e.source in (Graha.RAHU, Graha.KETU)
    assert seen > 0, "fixture should produce classical-graha evidence"

# ── KAR-084: functional roles — full doctrine lives in test_d1_functional_roles.py
# (sourced from the independent BPHS-34 verse fixture). Here we assert only that
# the engine's FLAT 0.1.0 contract role is correctly derived from that source.

def test_kar084_flat_role_review_required_when_doctrine_unresolved(monkeypatch):
    """Doctrine values are under review (QA v3 CRITICAL-1). The flat contract
    role still derives cleanly: ownership yogakāraka survives (verse-independent),
    review_required nature maps to the neutral flat bucket, nodes are node_axis."""
    import d1_functional_roles as m
    row = {g: m._REVIEW for g in (Graha.SUN, Graha.MOON, Graha.MARS, Graha.MERCURY,
                                  Graha.JUPITER, Graha.VENUS, Graha.SATURN)}
    monkeypatch.setitem(m.BPHS34_MATRIX, 3, row)
    roles = {r.graha: r for r in resolve_functional_roles(3)}
    # a review_required cell must not masquerade as decided doctrine
    assert all("review_required" in roles[g].basis
               for g in (Graha.SUN, Graha.MOON, Graha.MARS, Graha.MERCURY,
                         Graha.JUPITER, Graha.VENUS, Graha.SATURN))
    for n in (Graha.RAHU, Graha.KETU):
        assert roles[n].role == FunctionalRoleKind.NODE_AXIS and roles[n].lordships == []

def test_kar084_flat_role_every_lagna_covers_nine_grahas():
    for lagna in range(12):
        roles = resolve_functional_roles(lagna)
        assert {r.graha for r in roles} == set(Graha)

def test_kar084_ownership_yogakaraka_exact_six_through_engine():
    yk = []
    for lagna in range(12):
        for r in resolve_functional_roles(lagna):
            if r.role == FunctionalRoleKind.YOGAKARAKA:
                yk.append((lagna, r.graha))
    assert sorted(yk) == sorted([(1, Graha.SATURN), (6, Graha.SATURN),
                                 (3, Graha.MARS), (4, Graha.MARS),
                                 (9, Graha.VENUS), (10, Graha.VENUS)])

# ── QA v3 CRITICAL-2: complete polarity truth table, no fall-through ─────────

def test_polarity_benefic_neutral_is_not_challenging():
    from d1_engine import _polarity_of
    pol, why = _polarity_of(Graha.VENUS, {Graha.VENUS: NaturalNature.BENEFIC},
                            {Graha.VENUS: _fr(Graha.VENUS, FunctionalNature.NEUTRAL)})
    assert pol != InfluencePolarity.CHALLENGING
    assert "natural malefic" not in why

def test_polarity_benefic_mixed_is_mixed():
    from d1_engine import _polarity_of
    pol, why = _polarity_of(Graha.VENUS, {Graha.VENUS: NaturalNature.BENEFIC},
                            {Graha.VENUS: _fr(Graha.VENUS, FunctionalNature.MIXED)})
    assert pol == InfluencePolarity.MIXED
    assert "natural malefic" not in why

def test_polarity_review_required_is_unassessed():
    from d1_engine import _polarity_of
    pol, why = _polarity_of(Graha.VENUS, {Graha.VENUS: NaturalNature.BENEFIC},
                            {Graha.VENUS: _fr(Graha.VENUS, FunctionalNature.NEUTRAL,
                                              prov=CellProvenance.REVIEW_REQUIRED)})
    assert pol == InfluencePolarity.UNASSESSED

def test_polarity_truth_table_total():
    """Every (natural, functional) combination returns a real polarity, never
    a fall-through. No benefic is ever labelled 'natural malefic'."""
    from d1_engine import _polarity_of
    for nat in (NaturalNature.BENEFIC, NaturalNature.MALEFIC):
        for fn in FunctionalNature:
            pol, why = _polarity_of(Graha.VENUS, {Graha.VENUS: nat},
                                    {Graha.VENUS: _fr(Graha.VENUS, fn)})
            assert pol in InfluencePolarity
            if nat == NaturalNature.BENEFIC:
                assert "natural malefic" not in why

# ── QA v3 HIGH-1: the versioned extension is in the serialized payload ───────

def test_orthogonal_roles_exposed_in_payload():
    resp, doc = compute_d1(founder_chart())
    assert doc.functional_role_policy_version == "parashari-functional-role-1.0"
    assert len(doc.functional_roles_orthogonal) == 7
    fields = doc.functional_roles_orthogonal[0].dict()
    for k in ("functional_nature", "verse_yoga_status", "ownership_yogakaraka",
              "maraka_status", "nature_provenance", "verse", "note"):
        assert k in fields
    # serializes cleanly (frontend can consume it)
    import json as _j
    _j.dumps(doc.dict())

# ── KAR-085# ── KAR-085: special aspects never disappear ─────────────────────────────────

def test_kar085_full_parashari_set_present():
    resp, _ = compute_d1(founder_chart())
    kinds = {}
    for e in resp.aspects: kinds.setdefault(e.source, set()).add(e.kind)
    assert kinds[Graha.MARS] == {AspectKind.SEVENTH, AspectKind.FOURTH, AspectKind.EIGHTH}
    assert kinds[Graha.JUPITER] == {AspectKind.SEVENTH, AspectKind.FIFTH, AspectKind.NINTH}
    assert kinds[Graha.SATURN] == {AspectKind.SEVENTH, AspectKind.THIRD, AspectKind.TENTH}

# ── KAR-086: Moon pakṣa resolved once, with basis, consumed everywhere ──────

def test_kar086_waning_moon_fixture():
    # Sun Cancer 5.9° (95.9°), Moon Aries 17.2° (17.2°): separation 281.3° → waning
    resp, doc = compute_d1(founder_chart())
    assert doc.moon_paksha.status == "waning"
    assert doc.moon_paksha.natural_nature == NaturalNature.MALEFIC
    assert "pakṣa" in doc.moon_paksha.basis
    moon_nat = next(n for n in doc.natures if n.graha == Graha.MOON)
    assert moon_nat.natural_nature == doc.moon_paksha.natural_nature
    assert "stored pakṣa" in moon_nat.basis

def test_kar086_waxing_moon():
    c = founder_chart(**{Graha.MOON: ChartGraha(
        sign_index=4, degree_in_sign=10.0, longitude=lon(4, 10.0), dignity=Dignity.NEUTRAL)})
    _, doc = compute_d1(c)   # Moon 130° − Sun 95.9° = 34.1° → waxing
    assert doc.moon_paksha.status == "waxing"
    assert doc.moon_paksha.natural_nature == NaturalNature.BENEFIC

def _paksha_at(sep_deg):
    sun_long = 10.0
    moon_long = (sun_long + sep_deg) % 360.0
    msi, mdeg = int(moon_long // 30), moon_long % 30.0
    c = founder_chart(**{
        Graha.SUN: ChartGraha(sign_index=0, degree_in_sign=10.0, longitude=sun_long, dignity=Dignity.NEUTRAL),
        Graha.MOON: ChartGraha(sign_index=msi, degree_in_sign=mdeg, longitude=moon_long, dignity=Dignity.NEUTRAL),
    })
    _, doc = compute_d1(c)
    return doc.moon_paksha

def test_kar086_boundary_exact_new_moon_0deg():
    p = _paksha_at(0.0)
    assert p.status == "new" and p.natural_nature == NaturalNature.MALEFIC

def test_kar086_boundary_just_above_0deg_is_waxing():
    p = _paksha_at(0.01)
    assert p.status == "waxing" and p.natural_nature == NaturalNature.BENEFIC

def test_kar086_boundary_just_below_180deg_is_waxing():
    p = _paksha_at(179.99)
    assert p.status == "waxing" and p.natural_nature == NaturalNature.BENEFIC

def test_kar086_boundary_exact_purnima_180deg_is_benefic():
    """QA HIGH defect: exact full Moon must be benefic with an explicit state."""
    p = _paksha_at(180.0)
    assert p.status == "full"
    assert p.natural_nature == NaturalNature.BENEFIC
    assert "pūrṇimā" in p.basis

def test_kar086_boundary_just_above_180deg_is_waning():
    p = _paksha_at(180.01)
    assert p.status == "waning" and p.natural_nature == NaturalNature.MALEFIC

# ── KAR-089: dignity labels are a total, distinct, typed mapping ─────────────

def test_kar089_labels_total_and_distinct():
    assert set(DIGNITY_LABELS) == set(Dignity)
    assert len(set(DIGNITY_LABELS.values())) == len(DIGNITY_LABELS)

def test_kar089_friend_is_never_labelled_neutral():
    assert "neutral" not in DIGNITY_LABELS[Dignity.FRIEND].lower()
    assert "neutral" not in DIGNITY_LABELS[Dignity.GREAT_FRIEND].lower()

# ── KAR-090: chart-level synthesis is one block, never per-graha ────────────

def test_kar090_chart_level_block_is_separate():
    resp, doc = compute_d1(founder_chart())
    assert hasattr(doc, "chart_level")
    graha_payloads = [g.dict() for g in resp.grahas]
    for gp in graha_payloads:
        assert "chart_level" not in gp and "stature" not in str(gp).lower()

# ── input hygiene ────────────────────────────────────────────────────────────

def test_conditional_rules_reach_the_payload():
    """Aries conditionals (Jupiter subordination, Saturn 11th predominance,
    Mars helper status) must serialize, not be dropped at the boundary."""
    from d1_engine import CertifiedChart
    c = founder_chart()
    aries = CertifiedChart(chart_token=c.chart_token, lagna_sign_index=0,
                           lagna_degree=10.0, grahas=c.grahas)
    _, doc = compute_d1(aries)
    assert doc.orthogonal_roles_publishable is True   # Aries is source-confirmed
    assert doc.functional_roles_status == "published"
    jup = next(o for o in doc.functional_roles_orthogonal if o.graha == Graha.JUPITER)
    assert any("subordinated to a malefic" in c for c in jup.conditional_rules)
    import json as _j
    d = _j.loads(_j.dumps(doc.dict()))
    payload_jup = next(o for o in d["functional_roles_orthogonal"] if o["graha"] == "Jupiter")
    assert payload_jup["conditional_rules"], "conditionals dropped at serialization"

def test_flat_roles_not_publishable_while_under_review(monkeypatch):
    """QA: unknown doctrine must not masquerade as neutral. While any cell is
    review_required, neither payload is publishable."""
    resp, doc = compute_d1(synthetic_unresolved(monkeypatch, 3))
    assert doc.functional_roles_status == "review_required"
    assert doc.orthogonal_roles_publishable is False
    assert doc.legacy_flat_roles_publishable is False
    import json as _j
    d = _j.loads(_j.dumps(doc.dict()))
    assert d["orthogonal_roles_publishable"] is False
    assert d["legacy_flat_roles_publishable"] is False

def test_taurus_payload_flags():
    """Taurus is source-confirmed: orthogonal payload publishes, flat never does."""
    from d1_engine import CertifiedChart
    c = founder_chart()
    taurus = CertifiedChart(chart_token=c.chart_token, lagna_sign_index=1,
                            lagna_degree=10.0, grahas=c.grahas)
    _, doc = compute_d1(taurus)
    assert doc.functional_roles_status == "published"
    assert doc.orthogonal_roles_publishable is True
    assert doc.legacy_flat_roles_publishable is False
    sat = next(o for o in doc.functional_roles_orthogonal if o.graha == Graha.SATURN)
    assert sat.ownership_yogakaraka is True and sat.verse_yoga_status.value == "yoga_agent"

@pytest.mark.parametrize("lagna", range(12))
def test_all_lagnas_publish_orthogonal_only(lagna):
    """Doctrine is complete: every Lagna publishes the orthogonal payload, and
    the lossy flat field is never publishable anywhere."""
    name = lagna
    from d1_engine import CertifiedChart
    c = founder_chart()
    ch = CertifiedChart(chart_token=c.chart_token, lagna_sign_index=lagna,
                        lagna_degree=10.0, grahas=c.grahas)
    _, doc = compute_d1(ch)
    assert doc.functional_roles_status == "published", name
    assert doc.orthogonal_roles_publishable is True, name
    assert doc.legacy_flat_roles_publishable is False, name

def test_synthetic_unresolved_row_withholds_publication(monkeypatch):
    """The withholding gate must still fire if doctrine ever becomes unresolved
    again (a corrected verse, a new policy version)."""
    ch = synthetic_unresolved(monkeypatch, 3)
    _, doc = compute_d1(ch)
    assert doc.functional_roles_status == "review_required"
    assert doc.orthogonal_roles_publishable is False
    assert doc.legacy_flat_roles_publishable is False

def test_maraka_provenance_reaches_the_payload():
    """Split provenance (Cancer Saturn: explicit killer, unclassified nature)
    must survive serialization."""
    from d1_engine import CertifiedChart
    c = founder_chart()
    cancer = CertifiedChart(chart_token=c.chart_token, lagna_sign_index=3,
                            lagna_degree=10.0, grahas=c.grahas)
    _, doc = compute_d1(cancer)
    import json as _j
    d = _j.loads(_j.dumps(doc.dict()))
    sat = next(o for o in d["functional_roles_orthogonal"] if o["graha"] == "Saturn")
    assert sat["maraka_provenance"] == "explicit_verse"
    assert sat["nature_provenance"] == "translation_judgment"
    sun = next(o for o in d["functional_roles_orthogonal"] if o["graha"] == "Sun")
    assert sun["maraka_provenance"] == "translation_judgment"

def test_yoga_provenance_reaches_the_payload():
    """Split yoga provenance (Libra Moon: explicit verse yoga, unclassified
    nature) must survive serialization end to end."""
    from d1_engine import CertifiedChart
    c = founder_chart()
    libra = CertifiedChart(chart_token=c.chart_token, lagna_sign_index=6,
                           lagna_degree=10.0, grahas=c.grahas)
    _, doc = compute_d1(libra)
    import json as _j
    d = _j.loads(_j.dumps(doc.dict()))
    moon = next(o for o in d["functional_roles_orthogonal"] if o["graha"] == "Moon")
    assert moon["yoga_provenance"] == "explicit_verse"
    assert moon["nature_provenance"] == "translation_judgment"
    assert moon["verse_yoga_status"] == "yoga_agent"
    sat = next(o for o in d["functional_roles_orthogonal"] if o["graha"] == "Saturn")
    assert sat["yoga_provenance"] is None and sat["ownership_yogakaraka"] is True

def test_resolved_doctrine_never_authorizes_the_lossy_flat_field():
    """QA bounded correction: Aries is fully source-confirmed, so the ORTHOGONAL
    payload becomes publishable — but the flat field must stay unpublishable
    because it silently loses MIXED nature (Moon, Mars → functional_neutral) and
    conditional māraka status (Mercury, Saturn → unconditional maraka)."""
    from d1_engine import CertifiedChart
    c = founder_chart()
    aries = CertifiedChart(chart_token=c.chart_token, lagna_sign_index=0,
                           lagna_degree=10.0, grahas=c.grahas)
    resp, doc = compute_d1(aries)
    assert doc.functional_roles_status == "published"
    assert doc.orthogonal_roles_publishable is True
    assert doc.legacy_flat_roles_publishable is False, \
        "the lossy flat field must never be authorized for publication"
    # demonstrate the loss the flag guards against
    flat = {r.graha: r.role for r in resp.functional_roles}
    orth = {o.graha: o for o in doc.functional_roles_orthogonal}
    for g in (Graha.MOON, Graha.MARS):
        assert orth[g].functional_nature == FunctionalNature.MIXED
        assert flat[g] == FunctionalRoleKind.FUNCTIONAL_NEUTRAL      # nuance lost
    for g in (Graha.MERCURY, Graha.SATURN):
        assert orth[g].maraka_status == MarakaStatus.QUALIFIED
        assert flat[g] == FunctionalRoleKind.MARAKA                  # conditionality lost
    import json as _j
    d = _j.loads(_j.dumps(doc.dict()))
    assert d["legacy_flat_roles_publishable"] is False

def test_house_net_ignores_unassessed_supportive():
    """supportive + unassessed → SUPPORTIVE (unassessed removed before net)."""
    natures = {Graha.JUPITER: NaturalNature.BENEFIC, Graha.SATURN: NaturalNature.MALEFIC}
    func = {Graha.JUPITER: _fr(Graha.JUPITER, FunctionalNature.BENEFIC),
            Graha.SATURN: _fr(Graha.SATURN, FunctionalNature.NEUTRAL,
                              prov=CellProvenance.REVIEW_REQUIRED)}
    infl = build_house_influences({1: [Graha.JUPITER, Graha.SATURN]}, [], natures, func)
    h1 = next(x for x in infl if x.house == 1)
    pols = {e.polarity for e in h1.evidence}
    assert InfluencePolarity.UNASSESSED in pols and InfluencePolarity.SUPPORTIVE in pols
    assert h1.net == InfluencePolarity.SUPPORTIVE

def test_house_net_ignores_unassessed_challenging():
    """challenging + unassessed → CHALLENGING."""
    natures = {Graha.SATURN: NaturalNature.MALEFIC, Graha.MARS: NaturalNature.MALEFIC}
    func = {Graha.SATURN: _fr(Graha.SATURN, FunctionalNature.MALEFIC),
            Graha.MARS: _fr(Graha.MARS, FunctionalNature.NEUTRAL,
                            prov=CellProvenance.REVIEW_REQUIRED)}
    infl = build_house_influences({1: [Graha.SATURN, Graha.MARS]}, [], natures, func)
    h1 = next(x for x in infl if x.house == 1)
    assert h1.net == InfluencePolarity.CHALLENGING

def test_house_net_only_unassessed_stays_unassessed():
    func = {Graha.SATURN: _fr(Graha.SATURN, FunctionalNature.NEUTRAL,
                              prov=CellProvenance.REVIEW_REQUIRED)}
    infl = build_house_influences({1: [Graha.SATURN]}, [], {Graha.SATURN: NaturalNature.MALEFIC}, func)
    h1 = next(x for x in infl if x.house == 1)
    assert h1.net == InfluencePolarity.UNASSESSED

def test_house_net_supportive_plus_challenging_is_mixed():
    natures = {Graha.JUPITER: NaturalNature.BENEFIC, Graha.SATURN: NaturalNature.MALEFIC}
    func = {Graha.JUPITER: _fr(Graha.JUPITER, FunctionalNature.BENEFIC),
            Graha.SATURN: _fr(Graha.SATURN, FunctionalNature.MALEFIC)}
    infl = build_house_influences({1: [Graha.JUPITER, Graha.SATURN]}, [], natures, func)
    h1 = next(x for x in infl if x.house == 1)
    assert h1.net == InfluencePolarity.MIXED

def test_missing_graha_is_error():
    c = founder_chart()
    del c.grahas[Graha.KETU]
    with pytest.raises(D1EngineError, match="missing grahas"):
        compute_d1(c)
