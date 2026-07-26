"""
test_d1_synthesis.py — KAR-093 step 5: server-side drawer synthesis.

Scope is narrow by founder ruling: synthesis only, harm framing stays
client-side. These tests therefore assert (a) the payload is faithful to the
client's drawer structure, (b) the four client defects this port exists to
remove cannot reappear, and (c) the scope boundary holds — no HTML, no corpus
prose, no harm framing leaks into the server payload.
"""
import inspect
import io
import json
import tokenize

import pytest

import d1_synthesis
from d1_synthesis import (
    _overall_verdict,
    build_d1_drawers, build_drawer, bhavat_bhavam, BalaBand, SupportLevel,
    StrengthVerdict, SYNTHESIS_VERSION, BHAVA_KARAKA, HOUSE_NATURAL_KARAKA,
    CorpusName, OverallVerdict, ShadbalaInput,
    karaka_support_of, support_of,
)
from pydantic import ValidationError
from d1_engine import compute_d1, InfluencePolarity, NaturalNature
from d1_contract import Graha, Dignity
from test_d1_engine import founder_chart


def code_only(module) -> str:
    """Module source with comments and string literals stripped, so the
    defect guards below test executable code rather than the docstrings that
    describe the defects being guarded against."""
    src = inspect.getsource(module)
    out = []
    for tok in tokenize.generate_tokens(io.StringIO(src).readline):
        if tok.type in (tokenize.COMMENT, tokenize.STRING):
            continue
        out.append(tok.string)
    return " ".join(out)


@pytest.fixture(scope="module")
def payload():
    resp, doc = compute_d1(founder_chart())
    return resp, doc, build_d1_drawers(resp, doc)


def drawer(payload, g):
    return next(d for d in payload[2].drawers if d.graha == g)


# ── payload shape mirrors the client's seven drawer sections ────────────────

def test_nine_drawers_with_all_seven_sections(payload):
    _, _, p = payload
    assert len(p.drawers) == 9
    assert {d.graha for d in p.drawers} == set(Graha)
    for d in p.drawers:
        for section in ("rashi", "house", "bhavesh", "bhavat_bhavam",
                        "bhava_karaka", "shadbala", "graha_saar"):
            assert getattr(d, section) is not None, (d.graha.value, section)

def test_bhavat_bhavam_arithmetic():
    # the house as many houses from itself: H1->H1, H4->H7, H7->H1, H10->H7
    assert bhavat_bhavam(1) == 1
    assert bhavat_bhavam(4) == 7
    assert bhavat_bhavam(7) == 1
    assert bhavat_bhavam(10) == 7
    for h in range(1, 13):
        assert 1 <= bhavat_bhavam(h) <= 12

def test_serializes_to_json(payload):
    _, _, p = payload
    json.dumps(p.dict())


# ── KAR-080: dignity consumed, never recomputed ─────────────────────────────

def test_kar080_dignity_echoed_from_certified_chart(payload):
    resp, _, _ = payload
    for st in resp.grahas:
        d = drawer(payload, st.graha)
        assert d.position.dignity == st.dignity, st.graha.value
        assert d.rashi.dignity == st.dignity, st.graha.value

def test_kar080_module_contains_no_dignity_computation():
    src = code_only(d1_synthesis)
    for marker in ("DIGNITY_SCORES", "getScore", "EXALTATION", "MOOLATRIKONA_RANGE",
                   "def compute_dignity", "sign_index in EXALT"):
        assert marker not in src, f"synthesis must not compute dignity ({marker})"


# ── KAR-081 / KAR-085: one aspect graph, nothing recomputed ─────────────────

def test_kar081_every_drishti_source_comes_from_the_canonical_manifest(payload):
    resp, _, p = payload
    manifest = {(e.source, e.kind.value, e.target_house) for e in resp.aspects}
    for d in p.drawers:
        for block, house in ((d.house.drishti, d.house.house),
                             (d.bhavesh.drishti, d.bhavesh.position.house)):
            if block is None:
                continue
            for s in block.sources:
                assert (s.source, s.kind, house) in manifest, (d.graha.value, s.source.value)

def test_kar081_house_block_matches_the_manifest_exactly(payload):
    resp, _, p = payload
    for d in p.drawers:
        expected = {e.source for e in resp.aspects
                    if e.target_house == d.house.house and e.source != d.graha}
        assert {s.source for s in d.house.drishti.sources} == expected, d.graha.value

def test_kar081_module_does_not_recompute_aspects():
    src = code_only(d1_synthesis)
    for marker in ("getPlanetsAspecting", "SPECIAL_DRISHTI", "def _aspects_of",
                   "def compute_aspects", "% 12 + 1) == target"):
        assert marker not in src, f"synthesis must read the manifest, not rebuild it ({marker})"

def test_kar085_special_aspects_survive_into_the_drawers(payload):
    resp, _, p = payload
    special = {(e.source, e.kind.value) for e in resp.aspects
               if e.kind.value in ("3rd", "4th", "5th", "8th", "9th", "10th")}
    assert special, "fixture should contain special drishti"
    seen = {(s.source, s.kind) for d in p.drawers for s in d.house.drishti.sources}
    assert seen & special, "no special drishti reached any drawer"


# ── KAR-083: dignity must never reverse natural maleficence ────────────────

def test_kar083_exalted_saturn_stays_a_natural_malefic(payload):
    sat = drawer(payload, Graha.SATURN)
    assert sat.position.dignity == Dignity.EXALTED
    assert sat.graha_saar.strength_verdict == StrengthVerdict.EXCEPTIONAL
    assert sat.graha_saar.natural_nature == NaturalNature.MALEFIC

def test_kar083_no_score_based_polarity_override_exists():
    """The client's `_isEff(a, positive)` returns true for a malefic whenever
    getScore(a) >= 3. That override must not exist here in any form."""
    src = code_only(d1_synthesis)
    for marker in ("_isEff", "score >= 3", "score>=3", "sc>=3", "sc >= 3"):
        assert marker not in src, f"dignity must not flip natural maleficence ({marker})"

def test_kar083_drishti_polarity_never_cites_dignity(payload):
    _, _, p = payload
    for d in p.drawers:
        for block in (d.house.drishti, d.bhavesh.drishti):
            if block is None:
                continue
            for s in block.sources:
                assert "dignit" not in s.basis.lower(), (d.graha.value, s.source.value)
                assert "exalt" not in s.basis.lower(), (d.graha.value, s.source.value)

def test_kar083_polarity_equals_the_doctrine_evidence(payload):
    """Polarity is taken from the same house_influences evidence the UI shows
    (KAR-082), not derived a second time inside the synthesis."""
    _, doc, p = payload
    for d in p.drawers:
        evidence = {e.source: e.polarity
                    for hi in doc.house_influences if hi.house == d.house.house
                    for e in hi.evidence if e.via == "drishti"}
        for s in d.house.drishti.sources:
            assert s.polarity == evidence[s.source], (d.graha.value, s.source.value)


# ── KAR-086: one paksha resolution, consumed ───────────────────────────────

def test_kar086_moon_nature_comes_from_the_single_paksha_resolution(payload):
    _, doc, _ = payload
    moon = drawer(payload, Graha.MOON)
    assert moon.graha_saar.natural_nature == doc.moon_paksha.natural_nature
    assert "pakṣa" in moon.graha_saar.natural_nature_basis

def test_kar086_module_does_not_recompute_paksha():
    src = code_only(d1_synthesis)
    for marker in ("longitude - sun", "moonWaning", "% 360) > 180", "sun_moon_separation ="):
        assert marker not in src, f"paksha must be consumed, not recomputed ({marker})"


# ── KAR-090: chart-level material stays out of per-graha payloads ──────────

def test_kar090_no_chart_level_content_in_drawers(payload):
    _, _, p = payload
    for d in p.drawers:
        blob = json.dumps(d.dict()).lower()
        for marker in ("chart_level", "stature", "complexion"):
            assert marker not in blob, (d.graha.value, marker)


# ── scope boundary: synthesis only, no framing and no prose ────────────────

def test_scope_no_html_in_the_payload(payload):
    _, _, p = payload
    blob = json.dumps(p.dict())
    for marker in ("<div", "<p>", "<strong", "<span", "style=", "class="):
        assert marker not in blob, f"synthesis must emit data, not HTML ({marker})"

def test_scope_corpus_is_referenced_not_inlined(payload):
    """Corpus text never enters the payload; only resolvable references do."""
    _, _, p = payload
    for d in p.drawers:
        for ref in (d.rashi.corpus_ref, d.house.corpus_ref,
                    d.bhavat_bhavam.corpus_ref, d.bhava_karaka.corpus_ref):
            # a key, never a sentence: the RASHI key is a Dignity enum value
            # ("Own Sign", "Great Friend"), the rest are house numbers
            assert len(ref.key) <= 13, ref.key
            assert ref.key == "" or not ref.key.endswith(".")


# ── QA HIGH-3: every corpus reference resolves against the real corpus ──────

def test_corpus_refs_are_directly_resolvable(payload):
    """The renderer indexes CORPUS[ref.graha][ref.key] with no reparsing and no
    score reconstruction."""
    _, _, p = payload
    for d in p.drawers:
        r = d.rashi.corpus_ref
        assert r.corpus == CorpusName.RASHI and r.graha == d.graha
        h = d.house.corpus_ref
        assert h.corpus == CorpusName.HOUSE and h.graha == d.graha
        assert h.key == str(d.house.house)
        b = d.bhavat_bhavam.corpus_ref
        assert b.corpus == CorpusName.BHAVAT and b.graha is None
        assert b.key == str(d.bhavat_bhavam.from_house)
        k = d.bhava_karaka.corpus_ref
        assert k.corpus == CorpusName.BHAVA_KARAKA and k.key == str(d.bhava_karaka.house)

def test_rashi_key_is_the_dignity_enum_value_not_a_score():
    """The legacy numeric-tier mapping is deleted: no score reconstruction."""
    import d1_synthesis as _m
    assert not hasattr(_m, "LEGACY_RASHI_KEY")
    for lagna_dignity in Dignity:
        assert lagna_dignity.value  # every enum value is a usable corpus key

def test_rashi_ref_carries_dignity_for_the_step6_migration(payload):
    """The dignity enum is echoed so the corpus can be re-keyed at step 6
    without the renderer reparsing anything."""
    _, _, p = payload
    for d in p.drawers:
        r = d.rashi.corpus_ref
        assert r.dignity == d.position.dignity
        if d.position.dignity is None:
            assert r.resolvable is False and r.key == ""
        else:
            assert r.resolvable is True
            assert r.key == d.position.dignity.value

def test_nodes_have_an_unresolvable_rashi_ref_not_a_guessed_key(payload):
    for g in (Graha.RAHU, Graha.KETU):
        d = drawer(payload, g)
        assert d.rashi.corpus_ref.resolvable is False


# ── QA HIGH-2: the two karaka maps stay separate ───────────────────────────

def test_the_two_karaka_maps_differ_where_the_client_differs():
    assert BHAVA_KARAKA[4] == [Graha.MOON]                       # Venus is NOT here
    assert HOUSE_NATURAL_KARAKA[4] == [Graha.MOON]
    assert BHAVA_KARAKA[10] == [Graha.SUN, Graha.MERCURY]
    assert HOUSE_NATURAL_KARAKA[10] == [Graha.SUN, Graha.MERCURY,
                                        Graha.JUPITER, Graha.SATURN]

def test_venus_in_h4_is_not_a_bhava_karaka(payload):
    """Edge case the founder fixture does not exercise."""
    resp, doc, _ = payload
    for lagna_house in (4,):
        assert Graha.VENUS not in BHAVA_KARAKA[lagna_house]
        assert Graha.VENUS not in HOUSE_NATURAL_KARAKA[lagna_house]

@pytest.mark.parametrize("graha", [Graha.JUPITER, Graha.SATURN])
def test_jupiter_and_saturn_in_h10_are_saar_karakas_but_not_bhava_karakas(graha):
    assert graha in HOUSE_NATURAL_KARAKA[10]
    assert graha not in BHAVA_KARAKA[10]

def test_h10_edge_case_through_the_builder(payload):
    """Build a drawer for a graha actually sitting in H10 and confirm the two
    maps drive different fields."""
    resp, doc, _ = payload
    tenth = [st.graha for st in resp.grahas if st.house == 10]
    for g in tenth:
        d = build_drawer(g, resp, doc)
        assert d.bhava_karaka.karakas == BHAVA_KARAKA[10]
        assert d.graha_saar.is_natural_karaka_of_own_house == (g in HOUSE_NATURAL_KARAKA[10])
        assert d.bhava_karaka.subject_is_karaka_of_own_house == (g in BHAVA_KARAKA[10])

def test_scope_no_harm_framing_ported_in_this_step():
    """KAR-091 framing stays client-side for now (founder ruling). The
    synthesis must not import or reimplement it."""
    src = code_only(d1_synthesis)
    for marker in ("kar091", "KAR091", "harm_categories", "withheld", "SAFE_SUMMARY"):
        assert marker not in src, f"harm framing is out of scope for step 5 ({marker})"


# ── derived judgments are typed, and honest where inputs are missing ───────

def test_support_and_verdict_are_enums_not_scores(payload):
    _, _, p = payload
    for d in p.drawers:
        assert isinstance(d.bhavesh.support, SupportLevel)
        assert isinstance(d.bhavat_bhavam.sustaining, SupportLevel)
        assert isinstance(d.graha_saar.strength_verdict, StrengthVerdict)
        blob = json.dumps(d.dict())
        assert '"score"' not in blob

def test_nodes_get_no_fabricated_functional_role(payload):
    for g in (Graha.RAHU, Graha.KETU):
        d = drawer(payload, g)
        assert d.graha_saar.has_lordship_doctrine is False
        assert d.graha_saar.functional_nature is None
        assert d.graha_saar.ownership_yogakaraka is None
        assert d.graha_saar.maraka_status is None

def test_missing_dignity_yields_unknown_not_a_guess(payload):
    """Nodes carry no dignity in the certified chart; the payload must say
    unknown rather than invent a level."""
    for g in (Graha.RAHU, Graha.KETU):
        d = drawer(payload, g)
        assert d.position.dignity is None
        assert d.graha_saar.strength_verdict == StrengthVerdict.UNKNOWN


# ── shadbala is explicitly not computed here ───────────────────────────────

def test_shadbala_not_computed_server_side(payload):
    _, _, p = payload
    for d in p.drawers:
        assert d.shadbala.computed_server_side is False
        assert d.shadbala.digbala is None and d.shadbala.uchcha_bala is None

def test_shadbala_bands_only_derive_from_supplied_values(payload):
    resp, doc, _ = payload
    d = build_drawer(Graha.SUN, resp, doc,
                     shadbala_inputs=ShadbalaInput(digbala=50, uchcha_bala=30,
                                                   naisargika_bala=20))
    assert d.shadbala.digbala_band == BalaBand.STRONG
    assert d.shadbala.uchcha_band == BalaBand.MODERATE
    assert d.shadbala.naisargika_band == BalaBand.WEAK
    assert d.shadbala.computed_server_side is False

def test_digbala_peak_house_is_a_flag_not_a_value(payload):
    """Saturn peaks in H7, and the founder's Saturn is in H1 — flag false."""
    sat = drawer(payload, Graha.SATURN)
    assert sat.shadbala.at_digbala_peak_house is False
    assert sat.graha_saar.at_digbala_peak_house is False


# ── drishti block construction ─────────────────────────────────────────────

def test_drishti_block_excludes_the_subject_graha(payload):
    _, _, p = payload
    for d in p.drawers:
        assert d.graha not in {s.source for s in d.house.drishti.sources}

def test_bhavesh_block_only_contains_edges_landing_on_the_bhavesh(payload):
    resp, _, p = payload
    for d in p.drawers:
        block = d.bhavesh.drishti
        if block is None:
            continue
        for s in block.sources:
            edge = next(e for e in resp.aspects
                        if e.source == s.source and e.kind.value == s.kind)
            assert d.bhavesh.bhavesh in edge.target_grahas, (d.graha.value, s.source.value)

def test_net_aggregates_assessed_evidence_only(payload):
    _, _, p = payload
    for d in p.drawers:
        for block in (d.house.drishti, d.bhavesh.drishti):
            if block is None:
                continue
            assessed = {s.polarity for s in block.sources
                        if s.polarity != InfluencePolarity.UNASSESSED}
            if not assessed:
                assert block.net == InfluencePolarity.UNASSESSED
            elif assessed == {InfluencePolarity.SUPPORTIVE}:
                assert block.net == InfluencePolarity.SUPPORTIVE
            elif assessed == {InfluencePolarity.CHALLENGING}:
                assert block.net == InfluencePolarity.CHALLENGING
            else:
                assert block.net == InfluencePolarity.MIXED

def test_each_source_appears_in_exactly_one_group(payload):
    _, _, p = payload
    for d in p.drawers:
        b = d.house.drishti
        groups = b.supportive + b.challenging + b.mixed + b.unassessed
        assert sorted(groups, key=lambda g: g.value) == sorted(
            [s.source for s in b.sources], key=lambda g: g.value)


def test_shadbala_inputs_are_range_validated():
    """Shashtiamsa scale is 0-60; out-of-range values are rejected, not banded."""
    ShadbalaInput(digbala=0)
    ShadbalaInput(digbala=60)
    for bad in (-1, 61, 100):
        with pytest.raises(ValidationError):
            ShadbalaInput(digbala=bad)
        with pytest.raises(ValidationError):
            ShadbalaInput(uchcha_bala=bad)
        with pytest.raises(ValidationError):
            ShadbalaInput(naisargika_bala=bad)


# ── QA HIGH-1: the two missing derived judgments ───────────────────────────

def test_bhava_karaka_support_is_typed(payload):
    _, _, p = payload
    for d in p.drawers:
        assert isinstance(d.bhava_karaka.karaka_support, SupportLevel)
        assert d.bhava_karaka.primary_karaka == (
            d.bhava_karaka.karakas[0] if d.bhava_karaka.karakas else None)

def test_karaka_threshold_differs_from_bhavesh_threshold():
    """The client requires score >= 3 for a strong KARAKA but only >= 2 for a
    strong BHAVESH. Own Sign (score 2) is the discriminating case."""
    assert support_of(Dignity.OWN) == SupportLevel.STRONG
    assert karaka_support_of(Dignity.OWN) == SupportLevel.MODERATE
    for dig in (Dignity.EXALTED, Dignity.MOOLATRIKONA):
        assert karaka_support_of(dig) == SupportLevel.STRONG
    for dig in (Dignity.ENEMY, Dignity.GREAT_ENEMY, Dignity.DEBILITATED):
        assert karaka_support_of(dig) == SupportLevel.WEAK
    assert karaka_support_of(None) == SupportLevel.UNKNOWN

def test_overall_verdict_is_typed_and_present(payload):
    _, _, p = payload
    for d in p.drawers:
        assert isinstance(d.graha_saar.overall_verdict, OverallVerdict)

def test_overall_verdict_composes_the_client_inputs(payload):
    """Every recorded factor must be one the client's summary actually used."""
    _, _, p = payload
    allowed = {"strength", "bhavesh", "house_drishti", "bhava_karaka",
               "digbala_house", "natural_karaka"}
    for d in p.drawers:
        for f in d.graha_saar.verdict_factors:
            assert f.factor in allowed
            assert f.direction in ("positive", "negative")

# Decision-table parity (QA step-5 v2). Columns:
#   strength, bhavesh support, house drishti net, karaka support,
#   digbala peak, own-house natural karaka  ->  expected verdict
VERDICT_TABLE = [
    # the four QA parity probes — all must be nuanced
    ("neutral strength, supportive drishti only",
     StrengthVerdict.NEUTRAL, SupportLevel.MODERATE, InfluencePolarity.SUPPORTIVE,
     SupportLevel.MODERATE, False, False, OverallVerdict.NUANCED),
    ("neutral strength, challenging drishti only",
     StrengthVerdict.NEUTRAL, SupportLevel.MODERATE, InfluencePolarity.CHALLENGING,
     SupportLevel.MODERATE, False, False, OverallVerdict.NUANCED),
    ("well placed, moderate Bhavesh",
     StrengthVerdict.WELL_PLACED, SupportLevel.MODERATE, InfluencePolarity.SUPPORTIVE,
     SupportLevel.MODERATE, False, False, OverallVerdict.NUANCED),
    ("well placed, strong Bhavesh, mixed drishti",
     StrengthVerdict.WELL_PLACED, SupportLevel.STRONG, InfluencePolarity.MIXED,
     SupportLevel.MODERATE, False, False, OverallVerdict.NUANCED),
    # the only routes to strong: all three clauses satisfied
    ("well placed + strong Bhavesh + supportive drishti",
     StrengthVerdict.WELL_PLACED, SupportLevel.STRONG, InfluencePolarity.SUPPORTIVE,
     SupportLevel.MODERATE, False, False, OverallVerdict.STRONG),
    ("exceptional + strong Bhavesh + unassessed drishti",
     StrengthVerdict.EXCEPTIONAL, SupportLevel.STRONG, InfluencePolarity.UNASSESSED,
     SupportLevel.MODERATE, False, False, OverallVerdict.STRONG),
    ("digbala peak substitutes for well placed",
     StrengthVerdict.NEUTRAL, SupportLevel.STRONG, InfluencePolarity.SUPPORTIVE,
     SupportLevel.MODERATE, True, False, OverallVerdict.STRONG),
    ("own-house natural karaka substitutes for well placed",
     StrengthVerdict.NEUTRAL, SupportLevel.STRONG, InfluencePolarity.SUPPORTIVE,
     SupportLevel.MODERATE, False, True, OverallVerdict.STRONG),
    # weak requires every clause; any protector blocks it
    ("strained + weak Bhavesh + challenging drishti",
     StrengthVerdict.STRAINED, SupportLevel.WEAK, InfluencePolarity.CHALLENGING,
     SupportLevel.WEAK, False, False, OverallVerdict.WEAK),
    ("weakened but at digbala peak",
     StrengthVerdict.WEAKENED, SupportLevel.WEAK, InfluencePolarity.CHALLENGING,
     SupportLevel.WEAK, True, False, OverallVerdict.NUANCED),
    ("weakened but own-house natural karaka",
     StrengthVerdict.WEAKENED, SupportLevel.WEAK, InfluencePolarity.CHALLENGING,
     SupportLevel.WEAK, False, True, OverallVerdict.NUANCED),
    ("weakened but Bhavesh only moderate",
     StrengthVerdict.WEAKENED, SupportLevel.MODERATE, InfluencePolarity.CHALLENGING,
     SupportLevel.WEAK, False, False, OverallVerdict.NUANCED),
]

@pytest.mark.parametrize(
    "label,strength,bhavesh,house_net,karaka,digbala,own_karaka,expected",
    VERDICT_TABLE)
def test_overall_verdict_decision_table(label, strength, bhavesh, house_net,
                                        karaka, digbala, own_karaka, expected):
    got, _ = _overall_verdict(strength, bhavesh, house_net, karaka, digbala, own_karaka)
    assert got == expected, label

def test_strong_requires_all_three_clauses():
    """Dropping any single clause must fall back to nuanced."""
    base = (StrengthVerdict.WELL_PLACED, SupportLevel.STRONG,
            InfluencePolarity.SUPPORTIVE, SupportLevel.MODERATE, False, False)
    assert _overall_verdict(*base)[0] == OverallVerdict.STRONG
    no_strength = (StrengthVerdict.NEUTRAL,) + base[1:]
    assert _overall_verdict(*no_strength)[0] == OverallVerdict.NUANCED
    no_bhavesh = (base[0], SupportLevel.MODERATE) + base[2:]
    assert _overall_verdict(*no_bhavesh)[0] == OverallVerdict.NUANCED
    for blocking in (InfluencePolarity.CHALLENGING, InfluencePolarity.MIXED):
        blocked = base[:2] + (blocking,) + base[3:]
        assert _overall_verdict(*blocked)[0] == OverallVerdict.NUANCED

def test_verdict_is_not_factor_counting():
    """A payload with more positive than negative factors is still not strong
    unless the decision table's clauses are met."""
    got, factors = _overall_verdict(
        StrengthVerdict.WELL_PLACED, SupportLevel.MODERATE,
        InfluencePolarity.SUPPORTIVE, SupportLevel.STRONG, True, True)
    assert [f.direction for f in factors].count("positive") >= 4
    assert not any(f.direction == "negative" for f in factors)
    assert got == OverallVerdict.NUANCED      # Bhavesh not strong -> blocked

def test_overall_verdict_unknown_when_nothing_is_known(payload):
    """Nodes have no dignity and no lordship doctrine; if no factor fires the
    verdict must be unknown rather than a default."""
    _, _, p = payload
    for g in (Graha.RAHU, Graha.KETU):
        d = drawer(payload, g)
        if not d.graha_saar.verdict_factors:
            assert d.graha_saar.overall_verdict == OverallVerdict.UNKNOWN

def test_overall_verdict_does_not_reuse_score_polarity():
    src = code_only(d1_synthesis)
    for marker in ("_isEff", "score >= 3", "sc>=3"):
        assert marker not in src


# ── determinism ────────────────────────────────────────────────────────────

def test_synthesis_is_deterministic():
    resp, doc = compute_d1(founder_chart())
    a = build_d1_drawers(resp, doc).dict()
    b = build_d1_drawers(resp, doc).dict()
    assert a == b

def test_version_stamped(payload):
    _, _, p = payload
    assert p.synthesis_version == SYNTHESIS_VERSION
    assert all(d.synthesis_version == SYNTHESIS_VERSION for d in p.drawers)
