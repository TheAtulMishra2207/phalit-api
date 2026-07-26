"""
test_d1_functional_roles.py — KAR-084, parashari-functional-role-1.0.

Doctrine is populated one BATCH of two Lagnas at a time from source-confirmed
BPHS 34 verses. Each populated Lagna gets per-cell assertions read from
bphs34_fixture.json — a SEPARATE file transcribed independently of the engine
matrix, which is what makes these tests verify doctrine rather than
implementation parity. Unpopulated Lagnas must remain REVIEW_REQUIRED, and a
count guard fails if any is populated out of turn.

Also asserted here, independently of any single Lagna: the orthogonality of the
three dimensions (functional nature, verse yoga vs ownership yogakāraka,
māraka), the provenance splits (nature vs māraka vs yoga), cross-Lagna māraka
gradation, and that commentary readings never silently become verse claims.

Coverage: COMPLETE — all twelve Lagnas from BPHS 34.19-44.
The review-gate behaviour is preserved by SYNTHETIC tests (a monkeypatched
unresolved row), since no real Lagna is withheld any more.
"""
import json, os
import pytest
from d1_functional_roles import (
    functional_roles, ownership_yogakarakas, BPHS34_MATRIX,
    FunctionalNature, VerseYogaStatus, MarakaStatus, CellProvenance,
)
from d1_contract import Graha

SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra",
         "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
CLASSICAL = [Graha.SUN, Graha.MOON, Graha.MARS, Graha.MERCURY,
             Graha.JUPITER, Graha.VENUS, Graha.SATURN]

with open(os.path.join(os.path.dirname(__file__), "bphs34_fixture.json")) as f:
    _RAW = json.load(f)
FIXTURE = {k: v for k, v in _RAW.items() if not k.startswith("_")}

# ── ownership yogakāraka: the one datum independent of the disputed verses ────

def test_ownership_yogakaraka_exact_six():
    assert ownership_yogakarakas() == sorted([
        (1, Graha.SATURN), (6, Graha.SATURN),
        (3, Graha.MARS), (4, Graha.MARS),
        (9, Graha.VENUS), (10, Graha.VENUS),
    ])

def test_ownership_flag_set_on_those_six_only():
    yk = set(ownership_yogakarakas())
    for lagna in range(12):
        for r in functional_roles(lagna):
            assert r.ownership_yogakaraka == ((lagna, r.graha) in yk)

# ── orthogonality: verse yoga and ownership yogakāraka are SEPARATE fields ────

def test_yoga_fields_are_independent():
    """QA v3 HIGH-3: both facts must be able to coexist; neither overwrites the
    other. Leo Mars is an ownership yogakāraka whose verse-yoga can still be
    none, and a verse yoga_agent need not be an ownership yogakāraka."""
    leo_mars = next(r for r in functional_roles(4) if r.graha == Graha.MARS)
    assert leo_mars.ownership_yogakaraka is True
    assert leo_mars.verse_yoga_status in (VerseYogaStatus.NONE, VerseYogaStatus.YOGA_AGENT)
    # the two fields are distinct attributes, not one enum
    for lagna in range(12):
        for r in functional_roles(lagna):
            assert hasattr(r, "verse_yoga_status") and hasattr(r, "ownership_yogakaraka")
            assert isinstance(r.ownership_yogakaraka, bool)

# ── provenance honesty: nothing asserts doctrine it cannot cite ──────────────

def test_no_cell_asserts_unconfirmed_doctrine_as_verse():
    """Every cell whose provenance is review_required must NOT carry a verse
    citation — it must say review_required (QA v3 HIGH-2: no laundering)."""
    for lagna in range(12):
        for r in functional_roles(lagna):
            if r.nature_provenance == CellProvenance.REVIEW_REQUIRED:
                assert r.verse == "review_required"
            else:
                assert r.verse.startswith("BPHS 34.")

def test_fixture_is_pure_oracle_no_derivation_in_cells():
    """The fixture must not store ownership-derived yogakāraka inside per-Lagna
    verse cells (the v3 laundering defect). Ownership data lives in its own
    section, and verse cells carry only verse fields."""
    assert "_ownership_yogakaraka_derived" in _RAW
    for sign in SIGNS:
        for g in [x.value for x in CLASSICAL]:
            cell = FIXTURE[sign][g]
            assert set(cell) == {"nature", "verse_yoga", "maraka", "provenance",
                                 "maraka_provenance", "yoga_provenance", "verse",
                                 "conditional_rules"}
            # verse_yoga can never be "yogakaraka" — that concept is not a verse field
            assert cell["verse_yoga"] in ("none", "yoga_agent", "review_required")

POPULATED_LAGNAS = list(range(12))   # COMPLETE: BPHS 34.19-44

def test_doctrine_population_complete():
    """All 84 classical-graha cells are source-resolved; nothing remains
    review_required."""
    review = 0
    for lagna in range(12):
        for r in functional_roles(lagna):
            if r.nature_provenance == CellProvenance.REVIEW_REQUIRED:
                review += 1
    assert review == 0, "BPHS 34.19-44 population is complete: zero review_required cells"
    for lagna in range(12):
        assert len(functional_roles(lagna)) == 7, f"lagna {lagna} incomplete"

# ── ARIES doctrine (BPHS 34.19-22), asserted against the independent fixture ──

ARIES_EXPECTED = [
    (Graha.SUN, FunctionalNature.BENEFIC, MarakaStatus.NONE, CellProvenance.EXPLICIT_VERSE),
    (Graha.MOON, FunctionalNature.MIXED, MarakaStatus.NONE, CellProvenance.TRANSLATION_JUDGMENT),
    (Graha.MARS, FunctionalNature.MIXED, MarakaStatus.NONE, CellProvenance.TRANSLATION_JUDGMENT),
    (Graha.MERCURY, FunctionalNature.MALEFIC, MarakaStatus.QUALIFIED, CellProvenance.EXPLICIT_VERSE),
    (Graha.JUPITER, FunctionalNature.BENEFIC, MarakaStatus.NONE, CellProvenance.EXPLICIT_VERSE),
    (Graha.VENUS, FunctionalNature.MALEFIC, MarakaStatus.PRIMARY_KILLER, CellProvenance.EXPLICIT_VERSE),
    (Graha.SATURN, FunctionalNature.MALEFIC, MarakaStatus.QUALIFIED, CellProvenance.EXPLICIT_VERSE),
]

@pytest.mark.parametrize("graha,nature,maraka,prov", ARIES_EXPECTED)
def test_aries_cells(graha, nature, maraka, prov):
    r = next(x for x in functional_roles(0) if x.graha == graha)
    assert r.functional_nature == nature
    assert r.maraka_status == maraka
    assert r.nature_provenance == prov
    assert r.verse_yoga_status == VerseYogaStatus.NONE
    assert r.ownership_yogakaraka is False

def test_aries_matches_independent_fixture():
    """Engine matrix vs the separately transcribed verse oracle."""
    for r in functional_roles(0):
        cell = FIXTURE["Aries"][r.graha.value]
        assert r.functional_nature.value == cell["nature"], r.graha.value
        assert r.maraka_status.value == cell["maraka"], r.graha.value
        assert r.nature_provenance.value == cell["provenance"], r.graha.value
        assert r.verse == f"BPHS {cell['verse']}", r.graha.value
        assert r.conditional_rules == cell["conditional_rules"], r.graha.value

def test_aries_venus_is_the_principal_killer_not_merely_maraka():
    v = next(r for r in functional_roles(0) if r.graha == Graha.VENUS)
    assert v.maraka_status == MarakaStatus.PRIMARY_KILLER   # 34.21 sākṣāt nihantā

def test_aries_saturn_and_mercury_killers_are_conditional_only():
    for g in (Graha.SATURN, Graha.MERCURY):
        r = next(x for x in functional_roles(0) if x.graha == g)
        assert r.maraka_status == MarakaStatus.QUALIFIED
        assert any("association" in c for c in r.conditional_rules)

def test_aries_conditional_rules_not_flattened():
    """The conditional statements survive as data, not folded into base polarity."""
    jup = next(r for r in functional_roles(0) if r.graha == Graha.JUPITER)
    assert jup.functional_nature == FunctionalNature.BENEFIC          # base nature unchanged
    assert any("subordinated to a malefic" in c for c in jup.conditional_rules)
    assert any("does not form an auspicious yoga" in c for c in jup.conditional_rules)
    sat = next(r for r in functional_roles(0) if r.graha == Graha.SATURN)
    assert any("11th lordship predominates" in c for c in sat.conditional_rules)
    mars = next(r for r in functional_roles(0) if r.graha == Graha.MARS)
    assert mars.functional_nature == FunctionalNature.MIXED           # helper, not independently auspicious
    assert any("supports benefics" in c for c in mars.conditional_rules)

def test_aries_moon_provenance_is_commentary_not_verse():
    """Moon is not classified in the ślokas; its reading must be marked as a
    translation/commentary judgment, never as explicit verse."""
    m = next(r for r in functional_roles(0) if r.graha == Graha.MOON)
    assert m.nature_provenance == CellProvenance.TRANSLATION_JUDGMENT
    assert m.nature_provenance != CellProvenance.EXPLICIT_VERSE
    assert any("commentary" in c for c in m.conditional_rules)

def test_aries_mars_not_derived_from_ownership_yogakaraka():
    """Aries Mars owns 1+8, not kendra+trikoṇa — no ownership YK."""
    mars = next(r for r in functional_roles(0) if r.graha == Graha.MARS)
    assert sorted(mars.lordships) == [1, 8]
    assert mars.ownership_yogakaraka is False

# ── TAURUS doctrine (BPHS 34.23-24), asserted against the independent fixture ─

TAURUS_EXPECTED = [
    (Graha.SUN, FunctionalNature.BENEFIC, MarakaStatus.NONE, CellProvenance.EXPLICIT_VERSE),
    (Graha.MOON, FunctionalNature.MALEFIC, MarakaStatus.QUALIFIED, CellProvenance.EXPLICIT_VERSE),
    (Graha.MARS, FunctionalNature.NEUTRAL, MarakaStatus.MARAKA, CellProvenance.TRANSLATION_JUDGMENT),
    (Graha.MERCURY, FunctionalNature.MIXED, MarakaStatus.NONE, CellProvenance.TRANSLATION_JUDGMENT),
    (Graha.JUPITER, FunctionalNature.MALEFIC, MarakaStatus.MARAKA, CellProvenance.EXPLICIT_VERSE),
    (Graha.VENUS, FunctionalNature.MALEFIC, MarakaStatus.MARAKA, CellProvenance.EXPLICIT_VERSE),
    (Graha.SATURN, FunctionalNature.BENEFIC, MarakaStatus.NONE, CellProvenance.EXPLICIT_VERSE),
]

@pytest.mark.parametrize("graha,nature,maraka,prov", TAURUS_EXPECTED)
def test_taurus_cells(graha, nature, maraka, prov):
    r = next(x for x in functional_roles(1) if x.graha == graha)
    assert r.functional_nature == nature
    assert r.maraka_status == maraka
    assert r.nature_provenance == prov

def test_taurus_matches_independent_fixture():
    for r in functional_roles(1):
        cell = FIXTURE["Taurus"][r.graha.value]
        assert r.functional_nature.value == cell["nature"], r.graha.value
        assert r.verse_yoga_status.value == cell["verse_yoga"], r.graha.value
        assert r.maraka_status.value == cell["maraka"], r.graha.value
        assert r.nature_provenance.value == cell["provenance"], r.graha.value
        assert r.verse == f"BPHS {cell['verse']}", r.graha.value
        assert r.conditional_rules == cell["conditional_rules"], r.graha.value

def test_taurus_saturn_holds_both_yoga_facts_independently():
    """Verse rājayoga language AND ownership yogakāraka (9th+10th) coexist —
    neither overwrites the other."""
    sat = next(r for r in functional_roles(1) if r.graha == Graha.SATURN)
    assert sat.verse_yoga_status == VerseYogaStatus.YOGA_AGENT
    assert sat.ownership_yogakaraka is True
    assert sorted(sat.lordships) == [9, 10]

def test_taurus_moon_is_qualified_never_unconditional_killer():
    moon = next(r for r in functional_roles(1) if r.graha == Graha.MOON)
    assert moon.maraka_status == MarakaStatus.QUALIFIED
    assert moon.maraka_status != MarakaStatus.PRIMARY_KILLER
    assert moon.maraka_status != MarakaStatus.MARAKA
    assert any("not independent" in c for c in moon.conditional_rules)

def test_taurus_mercury_is_mixed_not_full_benefic():
    """alpa-śubha (mild auspiciousness) is mixed, not a full benefic."""
    merc = next(r for r in functional_roles(1) if r.graha == Graha.MERCURY)
    assert merc.functional_nature == FunctionalNature.MIXED
    assert merc.functional_nature != FunctionalNature.BENEFIC
    assert merc.nature_provenance == CellProvenance.TRANSLATION_JUDGMENT

def test_taurus_venus_malefic_under_locked_parashara_reading():
    ven = next(r for r in functional_roles(1) if r.graha == Graha.VENUS)
    assert ven.functional_nature == FunctionalNature.MALEFIC
    assert ven.maraka_status == MarakaStatus.MARAKA
    assert any("Suśloka Śataka" in c for c in ven.conditional_rules)

def test_taurus_no_primary_killer_maraka_lakshana_is_weaker():
    """34.24 gives māraka-lakṣaṇa, not the sākṣāt nihantā of Aries Venus —
    nothing in Taurus may be a primary_killer."""
    for r in functional_roles(1):
        assert r.maraka_status != MarakaStatus.PRIMARY_KILLER, r.graha.value
    aries_venus = next(r for r in functional_roles(0) if r.graha == Graha.VENUS)
    assert aries_venus.maraka_status == MarakaStatus.PRIMARY_KILLER   # the contrast

# ── GEMINI doctrine (BPHS 34.25-26) ──────────────────────────────────────────

GEMINI_EXPECTED = [
    (Graha.SUN, FunctionalNature.MALEFIC, MarakaStatus.NONE, CellProvenance.EXPLICIT_VERSE),
    (Graha.MOON, FunctionalNature.NEUTRAL, MarakaStatus.PRIMARY_KILLER, CellProvenance.TRANSLATION_JUDGMENT),
    (Graha.MARS, FunctionalNature.MALEFIC, MarakaStatus.NONE, CellProvenance.EXPLICIT_VERSE),
    (Graha.MERCURY, FunctionalNature.NEUTRAL, MarakaStatus.NONE, CellProvenance.TRANSLATION_JUDGMENT),
    (Graha.JUPITER, FunctionalNature.MALEFIC, MarakaStatus.NONE, CellProvenance.EXPLICIT_VERSE),
    (Graha.VENUS, FunctionalNature.BENEFIC, MarakaStatus.NONE, CellProvenance.EXPLICIT_VERSE),
    (Graha.SATURN, FunctionalNature.NEUTRAL, MarakaStatus.NONE, CellProvenance.TRANSLATION_JUDGMENT),
]

@pytest.mark.parametrize("graha,nature,maraka,prov", GEMINI_EXPECTED)
def test_gemini_cells(graha, nature, maraka, prov):
    r = next(x for x in functional_roles(2) if x.graha == graha)
    assert r.functional_nature == nature
    assert r.maraka_status == maraka
    assert r.nature_provenance == prov

def _assert_matches_fixture(lagna, sign):
    for r in functional_roles(lagna):
        cell = FIXTURE[sign][r.graha.value]
        assert r.functional_nature.value == cell["nature"], (sign, r.graha.value)
        assert r.verse_yoga_status.value == cell["verse_yoga"], (sign, r.graha.value)
        assert r.maraka_status.value == cell["maraka"], (sign, r.graha.value)
        assert r.nature_provenance.value == cell["provenance"], (sign, r.graha.value)
        mp = r.maraka_provenance.value if r.maraka_provenance else None
        assert mp == cell["maraka_provenance"], (sign, r.graha.value)
        yp = r.yoga_provenance.value if r.yoga_provenance else None
        assert yp == cell["yoga_provenance"], (sign, r.graha.value)
        assert r.verse == f"BPHS {cell['verse']}", (sign, r.graha.value)
        assert r.conditional_rules == cell["conditional_rules"], (sign, r.graha.value)

def test_gemini_matches_independent_fixture():
    _assert_matches_fixture(2, "Gemini")

def test_gemini_moon_is_primary_killer_with_association_stored_separately():
    """mukhya-nihantā is explicit verse — association-dependence is conditional
    data and must NOT weaken the status to qualified."""
    m = next(r for r in functional_roles(2) if r.graha == Graha.MOON)
    assert m.maraka_status == MarakaStatus.PRIMARY_KILLER
    assert m.maraka_status != MarakaStatus.QUALIFIED
    assert m.maraka_provenance == CellProvenance.EXPLICIT_VERSE   # killer status is explicit
    assert m.nature_provenance == CellProvenance.TRANSLATION_JUDGMENT  # nature is not
    assert any("association" in c for c in m.conditional_rules)

def test_gemini_venus_is_the_only_explicit_benefic():
    roles = functional_roles(2)
    benefics = [r.graha for r in roles if r.functional_nature == FunctionalNature.BENEFIC]
    assert benefics == [Graha.VENUS]

def test_gemini_mercury_and_saturn_are_not_fabricated_malefics():
    """'Venus alone is benefic' must not become a malefic classification for the
    unmentioned grahas."""
    for g in (Graha.MERCURY, Graha.SATURN):
        r = next(x for x in functional_roles(2) if x.graha == g)
        assert r.functional_nature == FunctionalNature.NEUTRAL
        assert r.functional_nature != FunctionalNature.MALEFIC
        assert r.nature_provenance == CellProvenance.TRANSLATION_JUDGMENT
        assert any("must not be expanded" in c for c in r.conditional_rules)

def test_gemini_jupiter_saturn_rule_matches_aries():
    gem = next(r for r in functional_roles(2) if r.graha == Graha.JUPITER)
    ari = next(r for r in functional_roles(0) if r.graha == Graha.JUPITER)
    assert any("does not" in c and "auspicious yoga" in c for c in gem.conditional_rules)
    assert any("does not form an auspicious yoga" in c for c in ari.conditional_rules)

# ── CANCER doctrine (BPHS 34.27-28) ──────────────────────────────────────────

CANCER_EXPECTED = [
    (Graha.SUN, FunctionalNature.NEUTRAL, MarakaStatus.QUALIFIED, CellProvenance.TRANSLATION_JUDGMENT),
    (Graha.MOON, FunctionalNature.BENEFIC, MarakaStatus.NONE, CellProvenance.EXPLICIT_VERSE),
    (Graha.MARS, FunctionalNature.BENEFIC, MarakaStatus.NONE, CellProvenance.EXPLICIT_VERSE),
    (Graha.MERCURY, FunctionalNature.MALEFIC, MarakaStatus.NONE, CellProvenance.EXPLICIT_VERSE),
    (Graha.JUPITER, FunctionalNature.BENEFIC, MarakaStatus.NONE, CellProvenance.EXPLICIT_VERSE),
    (Graha.VENUS, FunctionalNature.MALEFIC, MarakaStatus.NONE, CellProvenance.EXPLICIT_VERSE),
    (Graha.SATURN, FunctionalNature.NEUTRAL, MarakaStatus.PRIMARY_KILLER, CellProvenance.TRANSLATION_JUDGMENT),
]

@pytest.mark.parametrize("graha,nature,maraka,prov", CANCER_EXPECTED)
def test_cancer_cells(graha, nature, maraka, prov):
    r = next(x for x in functional_roles(3) if x.graha == graha)
    assert r.functional_nature == nature
    assert r.maraka_status == maraka
    assert r.nature_provenance == prov

def test_cancer_matches_independent_fixture():
    _assert_matches_fixture(3, "Cancer")

def test_cancer_mars_holds_both_yoga_facts_independently():
    mars = next(r for r in functional_roles(3) if r.graha == Graha.MARS)
    assert mars.verse_yoga_status == VerseYogaStatus.YOGA_AGENT   # pūrṇa-yogakara 34.27
    assert mars.ownership_yogakaraka is True                      # 5th + 10th lordship
    assert sorted(mars.lordships) == [5, 10]
    assert any("must not be derived from dignity" in c for c in mars.conditional_rules)

def test_cancer_saturn_is_the_explicit_primary_killer():
    sat = next(r for r in functional_roles(3) if r.graha == Graha.SATURN)
    assert sat.maraka_status == MarakaStatus.PRIMARY_KILLER
    assert sat.maraka_provenance == CellProvenance.EXPLICIT_VERSE   # arka-sutaḥ nihantā
    assert sat.nature_provenance == CellProvenance.TRANSLATION_JUDGMENT

def test_cancer_sun_killer_reading_is_not_laundered_as_explicit_sanskrit():
    """The Sanskrit says only that the Sun gives results through association;
    the killer reading is the translation's, and must be marked as such."""
    sun = next(r for r in functional_roles(3) if r.graha == Graha.SUN)
    assert sun.maraka_status == MarakaStatus.QUALIFIED
    assert sun.maraka_provenance == CellProvenance.TRANSLATION_JUDGMENT
    assert sun.maraka_provenance != CellProvenance.EXPLICIT_VERSE
    assert sun.nature_provenance == CellProvenance.TRANSLATION_JUDGMENT
    assert any("Sanskrit directly names Saturn" in c for c in sun.conditional_rules)

def test_cancer_natures():
    roles = {r.graha: r.functional_nature for r in functional_roles(3)}
    for g in (Graha.MARS, Graha.JUPITER, Graha.MOON):
        assert roles[g] == FunctionalNature.BENEFIC
    for g in (Graha.VENUS, Graha.MERCURY):
        assert roles[g] == FunctionalNature.MALEFIC

# ── cross-Lagna strength: the same graha differs by Lagna ────────────────────

def test_moon_killer_strength_differs_across_lagnas():
    """Taurus Moon is qualified (māraka-lakṣaṇa); Gemini Moon is primary_killer
    (mukhya-nihantā). The gradation must never collapse."""
    taurus = next(r for r in functional_roles(1) if r.graha == Graha.MOON)
    gemini = next(r for r in functional_roles(2) if r.graha == Graha.MOON)
    assert taurus.maraka_status == MarakaStatus.QUALIFIED
    assert gemini.maraka_status == MarakaStatus.PRIMARY_KILLER

def test_primary_killers_are_exactly_the_direct_killing_cells():
    expected = {
        (0, Graha.VENUS), (2, Graha.MOON), (3, Graha.SATURN), (6, Graha.MARS),
        (8, Graha.SATURN), (9, Graha.MARS), (9, Graha.JUPITER), (9, Graha.MOON),
        (10, Graha.JUPITER), (10, Graha.SUN), (10, Graha.MARS),
    }
    found = {(l, r.graha) for l in range(12) for r in functional_roles(l)
             if r.maraka_status == MarakaStatus.PRIMARY_KILLER}
    assert found == expected

def test_accepted_aries_and_taurus_cells_unchanged_by_this_batch():
    """Regression guard: this batch must not have touched accepted doctrine."""
    for lagna, sign in ((0, "Aries"), (1, "Taurus")):
        _assert_matches_fixture(lagna, sign)

# ── LEO doctrine (BPHS 34.29-30) ─────────────────────────────────────────────

LEO_EXPECTED = [
    (Graha.SUN, FunctionalNature.BENEFIC, MarakaStatus.NONE, CellProvenance.EXPLICIT_VERSE),
    (Graha.MOON, FunctionalNature.NEUTRAL, MarakaStatus.QUALIFIED, CellProvenance.TRANSLATION_JUDGMENT),
    (Graha.MARS, FunctionalNature.BENEFIC, MarakaStatus.NONE, CellProvenance.EXPLICIT_VERSE),
    (Graha.MERCURY, FunctionalNature.MALEFIC, MarakaStatus.NONE, CellProvenance.EXPLICIT_VERSE),
    (Graha.JUPITER, FunctionalNature.BENEFIC, MarakaStatus.NONE, CellProvenance.EXPLICIT_VERSE),
    (Graha.VENUS, FunctionalNature.MALEFIC, MarakaStatus.NONE, CellProvenance.EXPLICIT_VERSE),
    (Graha.SATURN, FunctionalNature.MALEFIC, MarakaStatus.QUALIFIED, CellProvenance.EXPLICIT_VERSE),
]

@pytest.mark.parametrize("graha,nature,maraka,prov", LEO_EXPECTED)
def test_leo_cells(graha, nature, maraka, prov):
    r = next(x for x in functional_roles(4) if x.graha == graha)
    assert r.functional_nature == nature
    assert r.maraka_status == maraka
    assert r.nature_provenance == prov

def test_leo_matches_independent_fixture():
    _assert_matches_fixture(4, "Leo")

def test_leo_mars_ownership_yk_without_verse_yoga():
    """Mars satisfies the ownership rule (4th + 9th) but the verses never call
    it a yoga agent — the two fields must stay separate."""
    mars = next(r for r in functional_roles(4) if r.graha == Graha.MARS)
    assert mars.ownership_yogakaraka is True
    assert mars.verse_yoga_status == VerseYogaStatus.NONE
    assert sorted(mars.lordships) == [4, 9]

def test_leo_saturn_and_moon_are_qualified_never_primary():
    """34.30 gives māraka with association-dependent operation, not
    mukhya-/sākṣāt-nihantā."""
    for g in (Graha.SATURN, Graha.MOON):
        r = next(x for x in functional_roles(4) if x.graha == g)
        assert r.maraka_status == MarakaStatus.QUALIFIED
        assert r.maraka_status != MarakaStatus.PRIMARY_KILLER
        assert any("association" in c for c in r.conditional_rules)

def test_leo_moon_provenance_stays_split():
    moon = next(r for r in functional_roles(4) if r.graha == Graha.MOON)
    assert moon.nature_provenance == CellProvenance.TRANSLATION_JUDGMENT
    assert moon.maraka_provenance == CellProvenance.EXPLICIT_VERSE

def test_leo_moon_commentary_never_promotes_to_verse_yoga_agent():
    moon = next(r for r in functional_roles(4) if r.graha == Graha.MOON)
    assert moon.verse_yoga_status == VerseYogaStatus.NONE
    assert any("commentary data only" in c for c in moon.conditional_rules)

def test_leo_jupiter_venus_rule_present_on_both_grahas():
    for g in (Graha.JUPITER, Graha.VENUS):
        r = next(x for x in functional_roles(4) if x.graha == g)
        assert any("Jupiter-Venus association alone does not produce" in c
                   for c in r.conditional_rules), g.value

def test_leo_no_strength_hierarchy_invented():
    """The commentary's benefic ranking is stored as text only — no new score,
    enum or ordering field may appear on the model."""
    mars = next(r for r in functional_roles(4) if r.graha == Graha.MARS)
    assert any("descending benefic strength" in c for c in mars.conditional_rules)
    for field in ("strength", "rank", "score", "hierarchy"):
        assert field not in mars.dict()

# ── VIRGO doctrine (BPHS 34.31-32) ───────────────────────────────────────────

VIRGO_EXPECTED = [
    (Graha.SUN, FunctionalNature.NEUTRAL, MarakaStatus.NONE, CellProvenance.TRANSLATION_JUDGMENT),
    (Graha.MOON, FunctionalNature.MALEFIC, MarakaStatus.NONE, CellProvenance.EXPLICIT_VERSE),
    (Graha.MARS, FunctionalNature.MALEFIC, MarakaStatus.QUALIFIED, CellProvenance.EXPLICIT_VERSE),
    (Graha.MERCURY, FunctionalNature.BENEFIC, MarakaStatus.NONE, CellProvenance.EXPLICIT_VERSE),
    (Graha.JUPITER, FunctionalNature.MALEFIC, MarakaStatus.NONE, CellProvenance.EXPLICIT_VERSE),
    (Graha.VENUS, FunctionalNature.BENEFIC, MarakaStatus.MARAKA, CellProvenance.EXPLICIT_VERSE),
    (Graha.SATURN, FunctionalNature.MIXED, MarakaStatus.NONE, CellProvenance.TRANSLATION_JUDGMENT),
]

@pytest.mark.parametrize("graha,nature,maraka,prov", VIRGO_EXPECTED)
def test_virgo_cells(graha, nature, maraka, prov):
    r = next(x for x in functional_roles(5) if x.graha == graha)
    assert r.functional_nature == nature
    assert r.maraka_status == maraka
    assert r.nature_provenance == prov

def test_virgo_matches_independent_fixture():
    _assert_matches_fixture(5, "Virgo")

def test_virgo_verse_yoga_agents_are_not_ownership_yogakarakas():
    """34.31 names Mercury and Venus yoga agents, but neither satisfies the
    locked ownership rule (Lagna excluded as the trikoṇa half; Venus holds no
    kendra)."""
    for g, lords in ((Graha.MERCURY, [1, 10]), (Graha.VENUS, [2, 9])):
        r = next(x for x in functional_roles(5) if x.graha == g)
        assert r.verse_yoga_status == VerseYogaStatus.YOGA_AGENT, g.value
        assert r.ownership_yogakaraka is False, g.value
        assert sorted(r.lordships) == lords, g.value
    assert not any(l == 5 for l, _ in ownership_yogakarakas())

def test_virgo_venus_holds_three_dimensions_at_once():
    ven = next(r for r in functional_roles(5) if r.graha == Graha.VENUS)
    assert ven.functional_nature == FunctionalNature.BENEFIC
    assert ven.verse_yoga_status == VerseYogaStatus.YOGA_AGENT
    assert ven.maraka_status == MarakaStatus.MARAKA
    assert any("none of these dimensions may overwrite another" in c for c in ven.conditional_rules)

def test_virgo_mars_nature_explicit_but_maraka_is_commentary():
    mars = next(r for r in functional_roles(5) if r.graha == Graha.MARS)
    assert mars.nature_provenance == CellProvenance.EXPLICIT_VERSE
    assert mars.maraka_status == MarakaStatus.QUALIFIED
    assert mars.maraka_provenance == CellProvenance.TRANSLATION_JUDGMENT
    assert mars.maraka_provenance != CellProvenance.EXPLICIT_VERSE

def test_virgo_sun_is_association_dependent_neutral():
    sun = next(r for r in functional_roles(5) if r.graha == Graha.SUN)
    assert sun.functional_nature == FunctionalNature.NEUTRAL
    assert sun.nature_provenance == CellProvenance.TRANSLATION_JUDGMENT
    assert any("do not infer an unconditional" in c for c in sun.conditional_rules)

def test_virgo_saturn_is_mixed_by_commentary_not_manufactured_verse():
    sat = next(r for r in functional_roles(5) if r.graha == Graha.SATURN)
    assert sat.functional_nature == FunctionalNature.MIXED
    assert sat.nature_provenance == CellProvenance.TRANSLATION_JUDGMENT
    assert any("Do not manufacture a verse classification" in c for c in sat.conditional_rules)

def test_virgo_has_no_primary_killer():
    for r in functional_roles(5):
        assert r.maraka_status != MarakaStatus.PRIMARY_KILLER, r.graha.value

# ── corpus guards after batch 2 ──────────────────────────────────────────────

def test_final_primary_killer_set():
    expected = {
        (0, Graha.VENUS), (2, Graha.MOON), (3, Graha.SATURN), (6, Graha.MARS),
        (8, Graha.SATURN), (9, Graha.MARS), (9, Graha.JUPITER), (9, Graha.MOON),
        (10, Graha.JUPITER), (10, Graha.SUN), (10, Graha.MARS),
    }
    found = {(l, r.graha) for l in range(12) for r in functional_roles(l)
             if r.maraka_status == MarakaStatus.PRIMARY_KILLER}
    assert found == expected

def test_all_lagnas_match_the_independent_fixture():
    for lagna, sign in ((0, "Aries"), (1, "Taurus"), (2, "Gemini"), (3, "Cancer"),
                        (4, "Leo"), (5, "Virgo"), (6, "Libra"), (7, "Scorpio"),
                        (8, "Sagittarius"), (9, "Capricorn"), (10, "Aquarius"),
                        (11, "Pisces")):
        _assert_matches_fixture(lagna, sign)

# ── LIBRA doctrine (BPHS 34.33-34) ───────────────────────────────────────────

LIBRA_EXPECTED = [
    (Graha.SUN, FunctionalNature.MALEFIC, MarakaStatus.MARAKA, CellProvenance.EXPLICIT_VERSE),
    (Graha.MOON, FunctionalNature.NEUTRAL, MarakaStatus.NONE, CellProvenance.TRANSLATION_JUDGMENT),
    (Graha.MARS, FunctionalNature.MALEFIC, MarakaStatus.PRIMARY_KILLER, CellProvenance.EXPLICIT_VERSE),
    (Graha.MERCURY, FunctionalNature.BENEFIC, MarakaStatus.NONE, CellProvenance.EXPLICIT_VERSE),
    (Graha.JUPITER, FunctionalNature.MALEFIC, MarakaStatus.MARAKA, CellProvenance.EXPLICIT_VERSE),
    (Graha.VENUS, FunctionalNature.NEUTRAL, MarakaStatus.NONE, CellProvenance.EXPLICIT_VERSE),
    (Graha.SATURN, FunctionalNature.BENEFIC, MarakaStatus.NONE, CellProvenance.EXPLICIT_VERSE),
]

@pytest.mark.parametrize("graha,nature,maraka,prov", LIBRA_EXPECTED)
def test_libra_cells(graha, nature, maraka, prov):
    r = next(x for x in functional_roles(6) if x.graha == graha)
    assert r.functional_nature == nature
    assert r.maraka_status == maraka
    assert r.nature_provenance == prov

def test_libra_matches_independent_fixture():
    _assert_matches_fixture(6, "Libra")

def test_libra_moon_and_mercury_are_verse_yoga_agents():
    for g in (Graha.MOON, Graha.MERCURY):
        r = next(x for x in functional_roles(6) if x.graha == g)
        assert r.verse_yoga_status == VerseYogaStatus.YOGA_AGENT, g.value
        assert any("rājayoga agents" in c for c in r.conditional_rules), g.value

def test_libra_moon_has_split_nature_and_yoga_provenance():
    """Nature unclassified, yoga explicit — the new split this batch introduces."""
    moon = next(r for r in functional_roles(6) if r.graha == Graha.MOON)
    assert moon.nature_provenance == CellProvenance.TRANSLATION_JUDGMENT
    assert moon.yoga_provenance == CellProvenance.EXPLICIT_VERSE

def test_libra_saturn_ownership_yk_without_verse_yoga():
    sat = next(r for r in functional_roles(6) if r.graha == Graha.SATURN)
    assert sat.ownership_yogakaraka is True
    assert sat.verse_yoga_status == VerseYogaStatus.NONE
    assert sorted(sat.lordships) == [4, 5]

def test_libra_mars_is_the_direct_primary_killer():
    """kujo nihanti is direct killing language, stronger than māraka-lakṣaṇa."""
    mars = next(r for r in functional_roles(6) if r.graha == Graha.MARS)
    assert mars.maraka_status == MarakaStatus.PRIMARY_KILLER
    assert mars.maraka_provenance == CellProvenance.EXPLICIT_VERSE

def test_libra_sun_and_jupiter_stay_maraka_not_promoted():
    for g in (Graha.SUN, Graha.JUPITER):
        r = next(x for x in functional_roles(6) if x.graha == g)
        assert r.maraka_status == MarakaStatus.MARAKA, g.value
        assert r.maraka_status != MarakaStatus.PRIMARY_KILLER, g.value

def test_libra_venus_is_explicit_neutral():
    ven = next(r for r in functional_roles(6) if r.graha == Graha.VENUS)
    assert ven.functional_nature == FunctionalNature.NEUTRAL
    assert ven.nature_provenance == CellProvenance.EXPLICIT_VERSE
    assert any("not benefic or malefic" in c for c in ven.conditional_rules)

def test_libra_alternate_school_stays_commentary_only():
    """The 'Mars or Sun may act beneficially' school is stored as data and must
    not alter their base malefic nature."""
    for g in (Graha.MARS, Graha.SUN):
        r = next(x for x in functional_roles(6) if x.graha == g)
        assert r.functional_nature == FunctionalNature.MALEFIC, g.value
        assert any("alternate commentary view" in c for c in r.conditional_rules), g.value

# ── SCORPIO doctrine (BPHS 34.35-36) ─────────────────────────────────────────

SCORPIO_EXPECTED = [
    (Graha.SUN, FunctionalNature.NEUTRAL, MarakaStatus.NONE, CellProvenance.TRANSLATION_JUDGMENT),
    (Graha.MOON, FunctionalNature.BENEFIC, MarakaStatus.NONE, CellProvenance.EXPLICIT_VERSE),
    (Graha.MARS, FunctionalNature.NEUTRAL, MarakaStatus.NONE, CellProvenance.EXPLICIT_VERSE),
    (Graha.MERCURY, FunctionalNature.MALEFIC, MarakaStatus.MARAKA, CellProvenance.EXPLICIT_VERSE),
    (Graha.JUPITER, FunctionalNature.BENEFIC, MarakaStatus.NONE, CellProvenance.EXPLICIT_VERSE),
    (Graha.VENUS, FunctionalNature.MALEFIC, MarakaStatus.MARAKA, CellProvenance.EXPLICIT_VERSE),
    (Graha.SATURN, FunctionalNature.MALEFIC, MarakaStatus.MARAKA, CellProvenance.EXPLICIT_VERSE),
]

@pytest.mark.parametrize("graha,nature,maraka,prov", SCORPIO_EXPECTED)
def test_scorpio_cells(graha, nature, maraka, prov):
    r = next(x for x in functional_roles(7) if x.graha == graha)
    assert r.functional_nature == nature
    assert r.maraka_status == maraka
    assert r.nature_provenance == prov

def test_scorpio_matches_independent_fixture():
    _assert_matches_fixture(7, "Scorpio")

def test_scorpio_sun_and_moon_are_yoga_agents_not_ownership_yogakarakas():
    for g in (Graha.SUN, Graha.MOON):
        r = next(x for x in functional_roles(7) if x.graha == g)
        assert r.verse_yoga_status == VerseYogaStatus.YOGA_AGENT, g.value
        assert r.ownership_yogakaraka is False, g.value
        assert any("Do not invent ownership-yogakāraka" in c for c in r.conditional_rules), g.value
    assert not any(l == 7 for l, _ in ownership_yogakarakas())

def test_scorpio_sun_has_split_nature_and_yoga_provenance():
    sun = next(r for r in functional_roles(7) if r.graha == Graha.SUN)
    assert sun.nature_provenance == CellProvenance.TRANSLATION_JUDGMENT
    assert sun.yoga_provenance == CellProvenance.EXPLICIT_VERSE

def test_scorpio_mars_is_explicit_neutral():
    mars = next(r for r in functional_roles(7) if r.graha == Graha.MARS)
    assert mars.functional_nature == FunctionalNature.NEUTRAL
    assert mars.nature_provenance == CellProvenance.EXPLICIT_VERSE
    assert any("kujaḥ samaḥ" in c for c in mars.conditional_rules)

def test_scorpio_three_malefic_marakas():
    for g in (Graha.VENUS, Graha.MERCURY, Graha.SATURN):
        r = next(x for x in functional_roles(7) if x.graha == g)
        assert r.functional_nature == FunctionalNature.MALEFIC, g.value
        assert r.maraka_status == MarakaStatus.MARAKA, g.value

def test_scorpio_has_no_primary_killer():
    for r in functional_roles(7):
        assert r.maraka_status != MarakaStatus.PRIMARY_KILLER, r.graha.value

def test_scorpio_saturn_favourable_placement_is_commentary_only():
    sat = next(r for r in functional_roles(7) if r.graha == Graha.SATURN)
    assert sat.functional_nature == FunctionalNature.MALEFIC   # base unchanged
    assert any("5th or 9th" in c and "commentary only" in c for c in sat.conditional_rules)

# ── orthogonality across the corpus after batch 3 ────────────────────────────

def test_verse_yoga_and_ownership_yk_are_independent_across_corpus():
    """Both mismatches exist in the corpus, proving neither field implies the
    other: ownership-YK without verse yoga (Leo Mars, Libra Saturn) and verse
    yoga without ownership-YK (Virgo Mercury/Venus, Scorpio Sun/Moon)."""
    own_no_verse, verse_no_own = [], []
    for lagna in range(12):
        for r in functional_roles(lagna):
            if r.ownership_yogakaraka and r.verse_yoga_status == VerseYogaStatus.NONE:
                own_no_verse.append((lagna, r.graha))
            if r.verse_yoga_status == VerseYogaStatus.YOGA_AGENT and not r.ownership_yogakaraka:
                verse_no_own.append((lagna, r.graha))
    assert (4, Graha.MARS) in own_no_verse and (6, Graha.SATURN) in own_no_verse
    assert (5, Graha.MERCURY) in verse_no_own and (7, Graha.SUN) in verse_no_own

# ── SAGITTARIUS doctrine (BPHS 34.37-38) ─────────────────────────────────────

SAGITTARIUS_EXPECTED = [
    (Graha.SUN, FunctionalNature.BENEFIC, MarakaStatus.NONE, CellProvenance.EXPLICIT_VERSE),
    (Graha.MOON, FunctionalNature.NEUTRAL, MarakaStatus.NONE, CellProvenance.TRANSLATION_JUDGMENT),
    (Graha.MARS, FunctionalNature.BENEFIC, MarakaStatus.NONE, CellProvenance.EXPLICIT_VERSE),
    (Graha.MERCURY, FunctionalNature.NEUTRAL, MarakaStatus.NONE, CellProvenance.TRANSLATION_JUDGMENT),
    (Graha.JUPITER, FunctionalNature.MIXED, MarakaStatus.NONE, CellProvenance.EXPLICIT_VERSE),
    (Graha.VENUS, FunctionalNature.MALEFIC, MarakaStatus.MARAKA, CellProvenance.EXPLICIT_VERSE),
    (Graha.SATURN, FunctionalNature.NEUTRAL, MarakaStatus.PRIMARY_KILLER, CellProvenance.TRANSLATION_JUDGMENT),
]

@pytest.mark.parametrize("graha,nature,maraka,prov", SAGITTARIUS_EXPECTED)
def test_sagittarius_cells(graha, nature, maraka, prov):
    r = next(x for x in functional_roles(8) if x.graha == graha)
    assert r.functional_nature == nature
    assert r.maraka_status == maraka
    assert r.nature_provenance == prov

def test_sagittarius_matches_independent_fixture():
    _assert_matches_fixture(8, "Sagittarius")

def test_sagittarius_sun_and_mercury_are_verse_yoga_agents():
    for g in (Graha.SUN, Graha.MERCURY):
        r = next(x for x in functional_roles(8) if x.graha == g)
        assert r.verse_yoga_status == VerseYogaStatus.YOGA_AGENT, g.value
        assert r.yoga_provenance == CellProvenance.EXPLICIT_VERSE, g.value

def test_sagittarius_mercury_yoga_does_not_imply_benefic_nature():
    merc = next(r for r in functional_roles(8) if r.graha == Graha.MERCURY)
    assert merc.verse_yoga_status == VerseYogaStatus.YOGA_AGENT
    assert merc.functional_nature == FunctionalNature.NEUTRAL
    assert merc.nature_provenance == CellProvenance.TRANSLATION_JUDGMENT
    assert merc.yoga_provenance == CellProvenance.EXPLICIT_VERSE
    assert any("do not infer benefic nature" in c for c in merc.conditional_rules)

def test_sagittarius_saturn_split_provenance_and_primary_killer():
    sat = next(r for r in functional_roles(8) if r.graha == Graha.SATURN)
    assert sat.maraka_status == MarakaStatus.PRIMARY_KILLER      # nihantā
    assert sat.maraka_provenance == CellProvenance.EXPLICIT_VERSE
    assert sat.nature_provenance == CellProvenance.TRANSLATION_JUDGMENT

def test_sagittarius_jupiter_is_mixed_never_neutral():
    """sama-phala maps to MIXED under the locked enum semantics."""
    jup = next(r for r in functional_roles(8) if r.graha == Graha.JUPITER)
    assert jup.functional_nature == FunctionalNature.MIXED
    assert jup.functional_nature != FunctionalNature.NEUTRAL
    assert jup.nature_provenance == CellProvenance.EXPLICIT_VERSE

def test_sagittarius_venus_is_maraka_never_primary():
    ven = next(r for r in functional_roles(8) if r.graha == Graha.VENUS)
    assert ven.maraka_status == MarakaStatus.MARAKA
    assert ven.maraka_status != MarakaStatus.PRIMARY_KILLER

def test_sagittarius_moon_unclassified_with_no_fabricated_yoga():
    moon = next(r for r in functional_roles(8) if r.graha == Graha.MOON)
    assert moon.functional_nature == FunctionalNature.NEUTRAL
    assert moon.nature_provenance == CellProvenance.TRANSLATION_JUDGMENT
    assert moon.verse_yoga_status == VerseYogaStatus.NONE
    assert moon.yoga_provenance is None
    assert any("conditional data only" in c for c in moon.conditional_rules)

def test_sagittarius_has_no_ownership_yogakaraka():
    assert not any(l == 8 for l, _ in ownership_yogakarakas())
    assert all(r.ownership_yogakaraka is False for r in functional_roles(8))

# ── CAPRICORN doctrine (BPHS 34.39-40) ───────────────────────────────────────

CAPRICORN_EXPECTED = [
    (Graha.SUN, FunctionalNature.MIXED, MarakaStatus.NONE, CellProvenance.EXPLICIT_VERSE),
    (Graha.MOON, FunctionalNature.MALEFIC, MarakaStatus.PRIMARY_KILLER, CellProvenance.EXPLICIT_VERSE),
    (Graha.MARS, FunctionalNature.MALEFIC, MarakaStatus.PRIMARY_KILLER, CellProvenance.EXPLICIT_VERSE),
    (Graha.MERCURY, FunctionalNature.BENEFIC, MarakaStatus.NONE, CellProvenance.EXPLICIT_VERSE),
    (Graha.JUPITER, FunctionalNature.MALEFIC, MarakaStatus.PRIMARY_KILLER, CellProvenance.EXPLICIT_VERSE),
    (Graha.VENUS, FunctionalNature.BENEFIC, MarakaStatus.NONE, CellProvenance.EXPLICIT_VERSE),
    (Graha.SATURN, FunctionalNature.NEUTRAL, MarakaStatus.QUALIFIED, CellProvenance.TRANSLATION_JUDGMENT),
]

@pytest.mark.parametrize("graha,nature,maraka,prov", CAPRICORN_EXPECTED)
def test_capricorn_cells(graha, nature, maraka, prov):
    r = next(x for x in functional_roles(9) if x.graha == graha)
    assert r.functional_nature == nature
    assert r.maraka_status == maraka
    assert r.nature_provenance == prov

def test_capricorn_matches_independent_fixture():
    _assert_matches_fixture(9, "Capricorn")

def test_capricorn_venus_holds_three_dimensions():
    ven = next(r for r in functional_roles(9) if r.graha == Graha.VENUS)
    assert ven.functional_nature == FunctionalNature.BENEFIC
    assert ven.verse_yoga_status == VerseYogaStatus.YOGA_AGENT
    assert ven.yoga_provenance == CellProvenance.EXPLICIT_VERSE
    assert ven.ownership_yogakaraka is True
    assert sorted(ven.lordships) == [5, 10]

def test_capricorn_sun_is_mixed():
    sun = next(r for r in functional_roles(9) if r.graha == Graha.SUN)
    assert sun.functional_nature == FunctionalNature.MIXED
    assert sun.nature_provenance == CellProvenance.EXPLICIT_VERSE

def test_capricorn_kujadi_trio_are_primary_killers():
    """hanti pāpāḥ kujādayaḥ — Mars, Jupiter and Moon all kill directly."""
    for g in (Graha.MARS, Graha.JUPITER, Graha.MOON):
        r = next(x for x in functional_roles(9) if x.graha == g)
        assert r.maraka_status == MarakaStatus.PRIMARY_KILLER, g.value
        assert r.maraka_provenance == CellProvenance.EXPLICIT_VERSE, g.value
        assert any("kujādayaḥ" in c for c in r.conditional_rules), g.value

def test_capricorn_saturn_qualified_never_primary():
    sat = next(r for r in functional_roles(9) if r.graha == Graha.SATURN)
    assert sat.maraka_status == MarakaStatus.QUALIFIED
    assert sat.maraka_status != MarakaStatus.PRIMARY_KILLER
    assert sat.maraka_provenance == CellProvenance.TRANSLATION_JUDGMENT
    assert any("Do not promote Saturn to primary_killer" in c for c in sat.conditional_rules)

def test_capricorn_mercury_benefic_without_verse_yoga():
    merc = next(r for r in functional_roles(9) if r.graha == Graha.MERCURY)
    assert merc.functional_nature == FunctionalNature.BENEFIC
    assert merc.verse_yoga_status == VerseYogaStatus.NONE
    assert merc.ownership_yogakaraka is False

# ── cross-Lagna: sama-phala is MIXED wherever it appears ─────────────────────

def test_sama_phala_cells_are_all_mixed():
    """Sagittarius Jupiter (34.38) and Capricorn Sun (34.40) both read
    sama-phala and must both be MIXED, never NEUTRAL."""
    for lagna, g in ((8, Graha.JUPITER), (9, Graha.SUN)):
        r = next(x for x in functional_roles(lagna) if x.graha == g)
        assert r.functional_nature == FunctionalNature.MIXED, (lagna, g.value)
        assert any("sama-phala" in c for c in r.conditional_rules), (lagna, g.value)

def test_saturn_killer_strength_differs_across_lagnas():
    """Sagittarius Saturn is the explicit nihantā (primary_killer); Capricorn
    Saturn explicitly does NOT kill independently (qualified, commentary)."""
    sag = next(r for r in functional_roles(8) if r.graha == Graha.SATURN)
    cap = next(r for r in functional_roles(9) if r.graha == Graha.SATURN)
    assert sag.maraka_status == MarakaStatus.PRIMARY_KILLER
    assert sag.maraka_provenance == CellProvenance.EXPLICIT_VERSE
    assert cap.maraka_status == MarakaStatus.QUALIFIED
    assert cap.maraka_provenance == CellProvenance.TRANSLATION_JUDGMENT

# ── AQUARIUS doctrine (BPHS 34.41-42) ────────────────────────────────────────

AQUARIUS_EXPECTED = [
    (Graha.SUN, FunctionalNature.NEUTRAL, MarakaStatus.PRIMARY_KILLER, CellProvenance.TRANSLATION_JUDGMENT),
    (Graha.MOON, FunctionalNature.MALEFIC, MarakaStatus.NONE, CellProvenance.EXPLICIT_VERSE),
    (Graha.MARS, FunctionalNature.MALEFIC, MarakaStatus.PRIMARY_KILLER, CellProvenance.EXPLICIT_VERSE),
    (Graha.MERCURY, FunctionalNature.MIXED, MarakaStatus.NONE, CellProvenance.EXPLICIT_VERSE),
    (Graha.JUPITER, FunctionalNature.MALEFIC, MarakaStatus.PRIMARY_KILLER, CellProvenance.EXPLICIT_VERSE),
    (Graha.VENUS, FunctionalNature.BENEFIC, MarakaStatus.NONE, CellProvenance.EXPLICIT_VERSE),
    (Graha.SATURN, FunctionalNature.BENEFIC, MarakaStatus.NONE, CellProvenance.EXPLICIT_VERSE),
]

@pytest.mark.parametrize("graha,nature,maraka,prov", AQUARIUS_EXPECTED)
def test_aquarius_cells(graha, nature, maraka, prov):
    r = next(x for x in functional_roles(10) if x.graha == graha)
    assert r.functional_nature == nature
    assert r.maraka_status == maraka
    assert r.nature_provenance == prov

def test_aquarius_matches_independent_fixture():
    _assert_matches_fixture(10, "Aquarius")

def test_aquarius_venus_is_both_kinds_of_yoga():
    ven = next(r for r in functional_roles(10) if r.graha == Graha.VENUS)
    assert ven.verse_yoga_status == VerseYogaStatus.YOGA_AGENT
    assert ven.yoga_provenance == CellProvenance.EXPLICIT_VERSE
    assert ven.ownership_yogakaraka is True
    assert sorted(ven.lordships) == [4, 9]

def test_aquarius_saturn_is_benefic_with_neither_yoga():
    sat = next(r for r in functional_roles(10) if r.graha == Graha.SATURN)
    assert sat.functional_nature == FunctionalNature.BENEFIC
    assert sat.verse_yoga_status == VerseYogaStatus.NONE
    assert sat.ownership_yogakaraka is False
    assert sorted(sat.lordships) == [1, 12]

def test_aquarius_three_direct_killers():
    """bṛhaspatiḥ | sūryo bhaumaś ca hantāraḥ runs across the verse boundary."""
    for g in (Graha.JUPITER, Graha.SUN, Graha.MARS):
        r = next(x for x in functional_roles(10) if x.graha == g)
        assert r.maraka_status == MarakaStatus.PRIMARY_KILLER, g.value
        assert r.maraka_provenance == CellProvenance.EXPLICIT_VERSE, g.value

def test_aquarius_sun_has_split_nature_and_maraka_provenance():
    sun = next(r for r in functional_roles(10) if r.graha == Graha.SUN)
    assert sun.nature_provenance == CellProvenance.TRANSLATION_JUDGMENT
    assert sun.maraka_provenance == CellProvenance.EXPLICIT_VERSE

def test_aquarius_mercury_madhya_phala_is_mixed():
    merc = next(r for r in functional_roles(10) if r.graha == Graha.MERCURY)
    assert merc.functional_nature == FunctionalNature.MIXED
    assert merc.nature_provenance == CellProvenance.EXPLICIT_VERSE

def test_no_killer_ranking_field_exists():
    """The commentary's ordering of the three killers stays prose."""
    r = next(x for x in functional_roles(10) if x.graha == Graha.JUPITER)
    for field in ("killer_rank", "killer_strength", "rank", "score", "severity"):
        assert field not in r.dict()
    assert any("prose only" in c for c in r.conditional_rules)

# ── PISCES doctrine (BPHS 34.43-44) ──────────────────────────────────────────

PISCES_EXPECTED = [
    (Graha.SUN, FunctionalNature.MALEFIC, MarakaStatus.NONE, CellProvenance.EXPLICIT_VERSE),
    (Graha.MOON, FunctionalNature.BENEFIC, MarakaStatus.NONE, CellProvenance.EXPLICIT_VERSE),
    (Graha.MARS, FunctionalNature.BENEFIC, MarakaStatus.QUALIFIED, CellProvenance.EXPLICIT_VERSE),
    (Graha.MERCURY, FunctionalNature.MALEFIC, MarakaStatus.MARAKA, CellProvenance.EXPLICIT_VERSE),
    (Graha.JUPITER, FunctionalNature.NEUTRAL, MarakaStatus.NONE, CellProvenance.TRANSLATION_JUDGMENT),
    (Graha.VENUS, FunctionalNature.MALEFIC, MarakaStatus.QUALIFIED, CellProvenance.EXPLICIT_VERSE),
    (Graha.SATURN, FunctionalNature.MALEFIC, MarakaStatus.MARAKA, CellProvenance.EXPLICIT_VERSE),
]

@pytest.mark.parametrize("graha,nature,maraka,prov", PISCES_EXPECTED)
def test_pisces_cells(graha, nature, maraka, prov):
    r = next(x for x in functional_roles(11) if x.graha == graha)
    assert r.functional_nature == nature
    assert r.maraka_status == maraka
    assert r.nature_provenance == prov

def test_pisces_matches_independent_fixture():
    _assert_matches_fixture(11, "Pisces")

def test_pisces_mars_holds_three_dimensions_and_is_never_primary():
    """mārako'pi na hantā'sau — a māraka that explicitly does not kill."""
    mars = next(r for r in functional_roles(11) if r.graha == Graha.MARS)
    assert mars.functional_nature == FunctionalNature.BENEFIC
    assert mars.verse_yoga_status == VerseYogaStatus.YOGA_AGENT
    assert mars.maraka_status == MarakaStatus.QUALIFIED
    assert mars.maraka_status != MarakaStatus.PRIMARY_KILLER
    assert mars.yoga_provenance == CellProvenance.EXPLICIT_VERSE
    assert mars.maraka_provenance == CellProvenance.EXPLICIT_VERSE
    assert any("na hantā" in c for c in mars.conditional_rules)
    assert any("requires activation" in c for c in mars.conditional_rules)

def test_pisces_jupiter_split_nature_and_yoga_provenance():
    jup = next(r for r in functional_roles(11) if r.graha == Graha.JUPITER)
    assert jup.verse_yoga_status == VerseYogaStatus.YOGA_AGENT
    assert jup.yoga_provenance == CellProvenance.EXPLICIT_VERSE
    assert jup.functional_nature == FunctionalNature.NEUTRAL
    assert jup.nature_provenance == CellProvenance.TRANSLATION_JUDGMENT

def test_pisces_saturn_and_mercury_are_ordinary_marakas():
    for g in (Graha.SATURN, Graha.MERCURY):
        r = next(x for x in functional_roles(11) if x.graha == g)
        assert r.maraka_status == MarakaStatus.MARAKA, g.value
        assert r.maraka_status != MarakaStatus.PRIMARY_KILLER, g.value

def test_pisces_venus_maraka_is_commentary_derived():
    ven = next(r for r in functional_roles(11) if r.graha == Graha.VENUS)
    assert ven.nature_provenance == CellProvenance.EXPLICIT_VERSE
    assert ven.maraka_status == MarakaStatus.QUALIFIED
    assert ven.maraka_provenance == CellProvenance.TRANSLATION_JUDGMENT

def test_pisces_has_no_ownership_yogakaraka():
    assert not any(l == 11 for l, _ in ownership_yogakarakas())
    assert all(r.ownership_yogakaraka is False for r in functional_roles(11))

def test_pisces_has_no_primary_killer():
    for r in functional_roles(11):
        assert r.maraka_status != MarakaStatus.PRIMARY_KILLER, r.graha.value

# ── cross-corpus semantic guard: samaḥ ≠ sama-phala ─────────────────────────

def test_samah_is_neutral_but_samaphala_is_mixed():
    """The two readings must never collapse into one enum value:
    samaḥ (Libra Venus, Scorpio Mars) → NEUTRAL;
    sama-phala / madhya-phala (Sag Jupiter, Cap Sun, Aq Mercury) → MIXED."""
    for lagna, g in ((6, Graha.VENUS), (7, Graha.MARS)):
        r = next(x for x in functional_roles(lagna) if x.graha == g)
        assert r.functional_nature == FunctionalNature.NEUTRAL, (lagna, g.value)
        assert r.functional_nature != FunctionalNature.MIXED, (lagna, g.value)
    for lagna, g in ((8, Graha.JUPITER), (9, Graha.SUN), (10, Graha.MERCURY)):
        r = next(x for x in functional_roles(lagna) if x.graha == g)
        assert r.functional_nature == FunctionalNature.MIXED, (lagna, g.value)
        assert r.functional_nature != FunctionalNature.NEUTRAL, (lagna, g.value)

def test_review_gate_still_works_on_a_synthetic_unresolved_row(monkeypatch):
    """No real Lagna is withheld any more, so the withholding path is exercised
    synthetically — the gate must still fire."""
    import d1_functional_roles as m
    synthetic = {g: m._REVIEW for g in (Graha.SUN, Graha.MOON, Graha.MARS, Graha.MERCURY,
                                        Graha.JUPITER, Graha.VENUS, Graha.SATURN)}
    monkeypatch.setitem(m.BPHS34_MATRIX, 0, synthetic)
    for r in functional_roles(0):
        assert r.nature_provenance == CellProvenance.REVIEW_REQUIRED
        assert r.verse == "review_required"

# ── completeness ─────────────────────────────────────────────────────────────

def test_matrix_and_fixture_complete():
    for lagna in range(12):
        assert set(BPHS34_MATRIX[lagna]) == set(CLASSICAL)
        assert set(FIXTURE[SIGNS[lagna]]) == {g.value for g in CLASSICAL}
