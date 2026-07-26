"""
d1_functional_roles.py — Phalit.ai functional-role doctrine, versioned extension
parashari-functional-role-1.0 (KAR-084, KAR-093 step 4).

A single mutually-exclusive `role` cannot represent BPHS Chapter 34: the verses
assign OVERLAPPING attributes to one graha (benefic nature AND conditional
killer capability, or a verse yoga alongside an ownership yogakāraka). Roles are
therefore split into orthogonal typed fields — functional_nature, verse yoga vs
ownership yogakāraka, maraka_status — each cell carrying its own provenance and
any conditional rules that must not be flattened into base polarity.

DOCTRINE STATE. The twelve-Lagna functional-nature verses run BPHS 34.19-44 and
are populated one Lagna at a time, only from source-confirmed text:

  COMPLETE — all twelve Lagnas are source-resolved from BPHS 34.19-44:
    ARIES (Meṣa)        34.19-22      LIBRA (Tulā)          34.33-34
    TAURUS (Vṛṣabha)    34.23-24      SCORPIO (Vṛścika)     34.35-36
    GEMINI (Mithuna)    34.25-26      SAGITTARIUS (Dhanus)  34.37-38
    CANCER (Karka)      34.27-28      CAPRICORN (Makara)    34.39-40
    LEO (Siṃha)         34.29-30      AQUARIUS (Kumbha)     34.41-42
    VIRGO (Kanyā)       34.31-32      PISCES (Mīna)         34.43-44
  Every cell carries its provenance; no cell asserts a nature it cannot cite.
  The _REVIEW sentinel remains in the module so any future doctrine change can
  be withheld the same way, and the review-gate behaviour stays under test.

SCOPE OF THIS MATRIX (BPHS 34.45-46). These verses establish the Lagna-specific
LORDSHIP roles as the base doctrine: evaṃ bhāvādhipatyena janma-lagna-vaśāt iha
śubhatvam aśubhatvaṃ ca grahāṇāṃ pratipāditam. Nābhasa and other yogas are
separate DOWNSTREAM considerations (34.46). They may modify manifested results,
but they must never rewrite this source matrix, its provenance, or its base
functional classifications. Consistent with the rest of this module:
  - yoga and māraka are independent dimensions; neither overwrites the other,
  - a yoga-producing graha may retain māraka status,
  - a māraka may participate in a favourable yoga without losing that status.
Nābhasa-yoga evaluation is NOT implemented here.

The one verse-independent datum, ownership_yogakaraka (the general kendra +
trikoṇa rule), is computed live for every Lagna regardless of doctrine state.

The flat FunctionalRoleKind emitted for the accepted d1-engine-0.1.0 contract is
LOSSY by construction — it cannot express MIXED nature or conditional (vs
unconditional) māraka status — and is therefore never publishable. Consumers
must read functional_roles_orthogonal.
"""
from __future__ import annotations
from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

from d1_contract import Graha

FUNCTIONAL_ROLE_POLICY_VERSION = "parashari-functional-role-1.0"

SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra",
         "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
SIGN_LORDS = [Graha.MARS, Graha.VENUS, Graha.MERCURY, Graha.MOON, Graha.SUN,
              Graha.MERCURY, Graha.VENUS, Graha.MARS, Graha.JUPITER,
              Graha.SATURN, Graha.SATURN, Graha.JUPITER]

class FunctionalNature(str, Enum):
    BENEFIC = "benefic"       # śubha
    MALEFIC = "malefic"       # pāpa
    NEUTRAL = "neutral"       # sama
    MIXED = "mixed"           # sama-phala / madhya-phala (explicitly mixed)

class VerseYogaStatus(str, Enum):
    """What the per-Lagna VERSE says about yoga — never overwritten by the
    ownership rule (QA v3 HIGH-3: the two are distinct dimensions)."""
    NONE = "none"
    YOGA_AGENT = "yoga_agent"       # yogakāraka / rājayoga language in the verse

class CellProvenance(str, Enum):
    """QA v3 HIGH-2: every cell declares WHERE its value comes from, so the
    fixture stops laundering derivations and judgments as scripture."""
    EXPLICIT_VERSE = "explicit_verse"          # the Lagna verse states it directly
    DERIVED_GENERAL_RULE = "derived_general_rule"  # from vv.2-17 general rules, not the Lagna verse
    TRANSLATION_JUDGMENT = "translation_judgment"  # a defensible reading of ambiguous verse wording
    REVIEW_REQUIRED = "review_required"        # NOT yet confirmed against the source — must not ship asserted

class MarakaStatus(str, Enum):
    NONE = "none"
    MARAKA = "maraka"               # māraka / maraka-lakṣaṇa
    PRIMARY_KILLER = "primary_killer"   # mukhya-nihantā / nihantā / hantā (chief)
    QUALIFIED = "qualified"         # māraka but explicitly not the chief killer

class FunctionalRoleV1(BaseModel):
    graha: Graha
    lordships: List[int] = Field(default_factory=list)
    functional_nature: FunctionalNature
    verse_yoga_status: VerseYogaStatus       # what the VERSE says (independent)
    ownership_yogakaraka: bool               # kendra+trikoṇa ownership (computed)
    maraka_status: MarakaStatus
    nature_provenance: CellProvenance
    maraka_provenance: Optional[CellProvenance] = None
    yoga_provenance: Optional[CellProvenance] = None
    # Some cells split provenance: the verse names a killer or a yoga agent
    # explicitly while the functional NATURE is unclassified (Gemini Moon and
    # Cancer Saturn for māraka; Libra Moon and Scorpio Sun for yoga). None means
    # "not separately specified — nature_provenance applies".
    verse: str                      # BPHS 34 verse citation (or "review_required")
    note: str
    conditional_rules: List[str] = Field(default_factory=list)
    # Conditional statements from the verse/commentary that must NOT be
    # flattened into the unconditional base polarity (founder ruling).

# Shorthand for populating cells once verse boundaries are confirmed.
_N, _B, _M, _X = (FunctionalNature.NEUTRAL, FunctionalNature.BENEFIC,
                  FunctionalNature.MALEFIC, FunctionalNature.MIXED)
_Yn, _Ya = VerseYogaStatus.NONE, VerseYogaStatus.YOGA_AGENT
_Kn, _Km, _Kp, _Kq = (MarakaStatus.NONE, MarakaStatus.MARAKA,
                      MarakaStatus.PRIMARY_KILLER, MarakaStatus.QUALIFIED)
_EV, _DG, _TJ = (CellProvenance.EXPLICIT_VERSE, CellProvenance.DERIVED_GENERAL_RULE,
                 CellProvenance.TRANSLATION_JUDGMENT)

# ── DOCTRINE MATRIX — populated one Lagna at a time from confirmed verses ────
# Every Lagna starts as _REVIEW and is replaced only when its verse boundary and
# text are source-confirmed (see the module header for current coverage). Cells
# still at _REVIEW assert nothing: the engine will not claim a functional nature
# it cannot cite, and charts of an unpopulated Lagna return
# orthogonal_roles_publishable=false. ownership_yogakaraka is the one datum
# independent of the per-Lagna verses (the general kendra+trikoṇa rule, vv.2/13),
# so it is computed live for all twelve.
#
# To populate a Lagna, replace its row with cells of the form
#   (nature, verse_yoga, maraka, nature_provenance, "34.NN", "note", [rules])
# or, when the verse names a killer while leaving the nature unclassified, the
# eight-element form adding maraka_provenance:
#   (..., [rules], MARAKA_PROVENANCE)
# or, when it also names a yoga agent with an unclassified nature, the
# nine-element form adding yoga_provenance:
#   (..., [rules], MARAKA_PROVENANCE, YOGA_PROVENANCE)
# Provenance values: EXPLICIT_VERSE / DERIVED_GENERAL_RULE / TRANSLATION_JUDGMENT.
_REVIEW = (FunctionalNature.NEUTRAL, VerseYogaStatus.NONE, MarakaStatus.NONE,
           CellProvenance.REVIEW_REQUIRED, "review_required",
           "verse boundary and text not yet supplied for this Lagna",
           [])

_CLASSICAL = (Graha.SUN, Graha.MOON, Graha.MARS, Graha.MERCURY,
              Graha.JUPITER, Graha.VENUS, Graha.SATURN)

BPHS34_MATRIX: Dict[int, Dict[Graha, tuple]] = {
    lagna: {g: _REVIEW for g in _CLASSICAL} for lagna in range(12)
}

# ── ARIES (Meṣa) — SOURCE-CONFIRMED, BPHS 34.19-22 ───────────────────────────
# Founder-supplied canonical transcription. 34.20 states the base natures
# (Saturn/Mercury/Venus pāpa; Jupiter/Sun śubha); 34.21 names Venus the direct
# principal killer; 34.22 makes Saturn and the other malefics killers through
# adverse association. Mars (34.19) supports auspicious grahas despite the 8th
# lordship — favourable helper, NOT independently auspicious → mixed. Moon is
# not classified in the ślokas at all; the commentary reading (sole kendra
# lordship, association-dependent) is recorded as a translation judgment.
BPHS34_MATRIX[0] = {
    Graha.SUN: (_B, _Yn, _Kn, _EV, "34.20", "sūrya śubha (guru-divākarau śubhau)", []),
    Graha.MOON: (_X, _Yn, _Kn, _TJ, "34.19-22",
                 "not classified in the ślokas; commentary reads sole kendra lordship as mixed",
                 ["Moon remains association-dependent; its classification comes from commentary, not the śloka"]),
    Graha.MARS: (_X, _Yn, _Kn, _TJ, "34.19",
                 "randhreśatve api śubha-sahāyavān — favourable helper, not independently auspicious",
                 ["Mars supports benefics when associated and suitably placed"]),
    Graha.MERCURY: (_M, _Yn, _Kq, _EV, "34.20",
                    "saumya pāpa; killer status conditional under 34.22",
                    ["Mercury becomes killer-capable through adverse association, particularly with Venus"]),
    Graha.JUPITER: (_B, _Yn, _Kn, _EV, "34.20", "guru śubha",
                    ["Jupiter becomes adverse when subordinated to a malefic (34.21 pāratantrya)",
                     "Saturn-Jupiter conjunction alone does not form an auspicious yoga (34.20)",
                     "Jupiter-Sun and Jupiter-Mars associations are favourable"]),
    Graha.VENUS: (_M, _Yn, _Kp, _EV, "34.20-21",
                  "sita pāpa; śukraḥ sākṣāt nihantā — direct and principal killer", []),
    Graha.SATURN: (_M, _Yn, _Kq, _EV, "34.20",
                   "manda pāpa; killer status conditional under 34.22",
                   ["Saturn becomes killer-capable through adverse association, particularly with Venus",
                    "Saturn-Jupiter association is not favourable — Saturn's 11th lordship predominates"]),
}

# ── TAURUS (Vṛṣabha) — SOURCE-CONFIRMED, BPHS 34.23-24 ───────────────────────
# 34.23 states the base natures (Jupiter/Venus/Moon pāpa; Saturn/Sun śubha),
# names Saturn a rājayoga agent (rājayogakaraḥ sauriḥ), and gives Mercury only
# alpa-śubha — mild auspiciousness, read as mixed rather than a full benefic.
# 34.24 gives Jupiter and the others, including Mars, māraka-lakṣaṇa — the
# WEAKER "characteristics of a killer" language, NOT the sākṣāt nihantā used
# for Aries Venus, so none of them is a primary_killer here. Mars's functional
# nature is not asserted by either verse (only its māraka status via 7th+12th
# lordship), so it is encoded neutral by translation judgment. Saturn carries
# BOTH the verse yoga_agent and the ownership yogakāraka (9th+10th) — the two
# facts are independent and neither overwrites the other.
BPHS34_MATRIX[1] = {
    Graha.SUN: (_B, _Yn, _Kn, _EV, "34.23", "sūrya śubha (śubhau śani-divākarau)", []),
    Graha.MOON: (_M, _Yn, _Kq, _EV, "34.23-24",
                 "indu pāpa (34.23); māraka-lakṣaṇa (34.24), but not an independent killer",
                 ["Moon's māraka capacity is not independent; association with Jupiter or Mars can activate it"]),
    Graha.MARS: (_N, _Yn, _Km, _TJ, "34.24",
                 "kuja māraka-lakṣaṇa; functional nature not asserted by the verse",
                 ["Mars is māraka by 7th + 12th lordship; its functional nature remains unasserted by the verse and is encoded neutral by translation judgment"]),
    Graha.MERCURY: (_X, _Yn, _Kn, _TJ, "34.23",
                    "budhaḥ tu alpa-śubha-pradaḥ — only mildly auspicious, read as mixed",
                    ["Mercury becomes more effective when associated with Saturn or Sun"]),
    Graha.JUPITER: (_M, _Yn, _Km, _EV, "34.23-24",
                    "jīva pāpa (34.23); māraka-lakṣaṇa (34.24)", []),
    Graha.VENUS: (_M, _Yn, _Km, _EV, "34.23-24",
                  "śukra pāpa (34.23); māraka-lakṣaṇa (34.24)",
                  ["Venus is treated as malefic under the accepted Parāśara policy despite the competing Suśloka Śataka interpretation for Taurus Lagna"]),
    Graha.SATURN: (_B, _Ya, _Kn, _EV, "34.23",
                   "śani śubha and rājayogakaraḥ sauriḥ — explicit verse yoga agent",
                   ["Saturn carries both facts independently: verse_yoga_status=yoga_agent (34.23) and ownership_yogakaraka=true (9th + 10th lordship)"]),
}

# ── GEMINI (Mithuna / Dvandva) — SOURCE-CONFIRMED, BPHS 34.25-26 ─────────────
# 34.25: Mars, Jupiter and Sun are pāpa; Venus ALONE is explicitly śubha
# (eka eva kaviḥ śubhaḥ); the Jupiter-Saturn association behaves as under Aries
# and forms no independent auspicious yoga. 34.26: śaśī mukhya-nihantā — the
# Moon is the PRINCIPAL killer, so primary_killer stands on explicit verse; its
# association-dependence (sāhacaryāt) is conditional data, NOT a weakening to
# qualified. Mercury and Saturn get no independent functional-nature statement,
# so both are neutral by translation judgment — "Venus alone is benefic" must
# never be expanded into unsupported malefic classifications for them.
BPHS34_MATRIX[2] = {
    Graha.SUN: (_M, _Yn, _Kn, _EV, "34.25", "aruṇa pāpa", []),
    Graha.MOON: (_N, _Yn, _Kp, _TJ, "34.26",
                 "śaśī mukhya-nihantā — principal killer by explicit verse; functional nature unclassified",
                 ["Moon's principal-killer capacity operates through association (sāhacaryāt)"],
                 _EV),
    Graha.MARS: (_M, _Yn, _Kn, _EV, "34.25", "bhauma pāpa", []),
    Graha.MERCURY: (_N, _Yn, _Kn, _TJ, "34.25-26",
                    "functional nature unclassified by the verses",
                    ["Mercury's functional nature is unclassified by the verses and is encoded neutral by translation judgment",
                     "'Venus alone is benefic' must not be expanded into an unsupported malefic classification for Mercury"]),
    Graha.JUPITER: (_M, _Yn, _Kn, _EV, "34.25", "jīva pāpa",
                    ["Jupiter-Saturn association does not independently produce an auspicious yoga, exactly as under Aries (34.25)"]),
    Graha.VENUS: (_B, _Yn, _Kn, _EV, "34.25", "eka eva kaviḥ śubhaḥ — Venus alone is benefic", []),
    Graha.SATURN: (_N, _Yn, _Kn, _TJ, "34.25",
                   "mentioned only in the Jupiter-Saturn association rule; functional nature unclassified",
                   ["Saturn's functional nature is unclassified; the verse mentions Saturn only in the Jupiter-Saturn association rule",
                    "'Venus alone is benefic' must not be expanded into an unsupported malefic classification for Saturn"]),
}

# ── CANCER (Karka) — SOURCE-CONFIRMED, BPHS 34.27-28 ─────────────────────────
# 34.27: Venus and Mercury are pāpa; Mars, Jupiter and Moon are śubha; Mars is
# pūrṇa-yogakara sākṣāt — an explicit FULL yoga agent — and independently also
# satisfies the ownership rule via 5th + 10th lordship, so BOTH facts are held.
# 34.28: arka-sutaḥ nihantā names SATURN the killer (explicit), while
# arkaḥ tu sāhacaryāt phala-pradaḥ says only that the SUN gives results through
# association. The supplied English reading of the Sun as a killer too is
# therefore interpretive: recorded as qualified with TRANSLATION_JUDGMENT
# provenance, never laundered as explicit Sanskrit. Saturn's own functional
# nature is not separately classified, hence neutral by translation judgment
# with the killer status marked explicit.
BPHS34_MATRIX[3] = {
    Graha.SUN: (_N, _Yn, _Kq, _TJ, "34.28",
                "arkaḥ tu sāhacaryāt phala-pradaḥ — gives results through association; killer reading is interpretive",
                ["Sun's results depend on association (sāhacaryāt)",
                 "Sun's qualified māraka reading comes from the supplied translation, while the Sanskrit directly names Saturn as the killer"],
                _TJ),
    Graha.MOON: (_B, _Yn, _Kn, _EV, "34.27", "indu śubha", []),
    Graha.MARS: (_B, _Ya, _Kn, _EV, "34.27",
                 "pūrṇa-yogakaraḥ sākṣāt maṅgalaḥ maṅgala-pradaḥ — explicit full yoga agent",
                 ["Mars carries both facts independently: verse_yoga_status=yoga_agent (34.27) and ownership_yogakaraka=true (5th + 10th lordship)",
                  "Mars's yoga status must not be derived from dignity or any client-side heuristic"]),
    Graha.MERCURY: (_M, _Yn, _Kn, _EV, "34.27", "indu-suta pāpa", []),
    Graha.JUPITER: (_B, _Yn, _Kn, _EV, "34.27", "ijya śubha", []),
    Graha.VENUS: (_M, _Yn, _Kn, _EV, "34.27", "bhārgava pāpa", []),
    Graha.SATURN: (_N, _Yn, _Kp, _TJ, "34.28",
                   "arka-sutaḥ nihantā — the killer by explicit verse; functional nature not separately classified",
                   ["Saturn is the explicit killer, but its functional nature is not separately classified in the verses"],
                   _EV),
}

# ── LEO (Siṃha) — SOURCE-CONFIRMED, BPHS 34.29-30 ────────────────────────────
# 34.29: Mercury, Venus and Saturn are pāpa; Mars, Jupiter and Sun are śubha;
# the Jupiter-Venus association forms no independent auspicious yoga
# (na śubhaṃ yoga-mātreṇa guru-śukrayoḥ). 34.30: mārakaḥ tu śaniḥ candraḥ —
# Saturn and Moon are mārakas whose operation is association-dependent
# (sāhacaryāt phala-pradaḥ). That is māraka language, NOT mukhya-/sākṣāt-
# nihantā, so both stay QUALIFIED and neither becomes a primary_killer. The
# Moon's functional nature is unclassified → neutral by translation judgment,
# with the killer statement itself explicit. Mars satisfies the ownership rule
# (4th + 9th) but the verses never call it a yoga agent: verse_yoga_status
# stays none while ownership_yogakaraka computes true.
BPHS34_MATRIX[4] = {
    Graha.SUN: (_B, _Yn, _Kn, _EV, "34.29", "arka śubha (kujejyārkāḥ śubhāvahāḥ)", []),
    Graha.MOON: (_N, _Yn, _Kq, _TJ, "34.30",
                 "mārakaḥ tu śaniḥ candraḥ — māraka by explicit verse; functional nature unclassified",
                 ["Saturn and Moon exercise their māraka capacity according to association (sāhacaryāt)",
                  "Moon's functional nature is unclassified and is therefore neutral by translation judgment",
                  "Commentary reports the Moon may become auspicious or yoga-producing under suitable conditions — commentary data only, never verse_yoga_status=yoga_agent"],
                 _EV),
    Graha.MARS: (_B, _Yn, _Kn, _EV, "34.29", "kuja śubha",
                 ["Mars carries ownership_yogakaraka=true through 4th + 9th lordship, while verse_yoga_status remains none — the verses do not call Mars a yoga agent for Leo",
                  "Commentary ranks Mars, Jupiter and Sun in descending benefic strength; recorded as commentary only, with no score, enum or hierarchy introduced"]),
    Graha.MERCURY: (_M, _Yn, _Kn, _EV, "34.29", "saumya pāpa", []),
    Graha.JUPITER: (_B, _Yn, _Kn, _EV, "34.29", "ijya śubha",
                    ["Jupiter-Venus association alone does not produce an auspicious yoga (34.29)"]),
    Graha.VENUS: (_M, _Yn, _Kn, _EV, "34.29", "śukra pāpa",
                  ["Jupiter-Venus association alone does not produce an auspicious yoga (34.29)"]),
    Graha.SATURN: (_M, _Yn, _Kq, _EV, "34.29-30",
                   "arkaja pāpa (34.29); māraka (34.30) with association-dependent operation",
                   ["Saturn and Moon exercise their māraka capacity according to association (sāhacaryāt)"]),
}

# ── VIRGO (Kanyā) — SOURCE-CONFIRMED, BPHS 34.31-32 ──────────────────────────
# 34.31: Mars, Jupiter and Moon are pāpa; Mercury and Venus are śubha AND are
# explicitly the yoga agents (bhārgava-indusutau eva bhavetāṃ yogakārakau).
# 34.32: mārako'pi kaviḥ — Venus is ALSO a māraka, so benefic + yoga agent +
# māraka coexist in one graha; and sūryaḥ sāhacarya-phala-pradaḥ gives the Sun
# results by association without classifying its base nature → neutral by
# translation judgment. Saturn is unclassified by both verses; commentary reads
# 5th lordship as supportive but 6th lordship as preventing an invariant
# benefic, hence MIXED by translation judgment — no verse classification is
# manufactured. Mars's killer capacity via 8th lordship is commentary-derived,
# so QUALIFIED with translation-judgment māraka provenance.
# NOTE ON OWNERSHIP: Mercury owns 1st + 10th and Venus owns 2nd + 9th; neither
# is an ownership yogakāraka — the locked rule excludes the Lagna as the trikoṇa
# half, and Venus holds no kendra. Their yoga status comes from 34.31 alone.
BPHS34_MATRIX[5] = {
    Graha.SUN: (_N, _Yn, _Kn, _TJ, "34.32",
                "sūryaḥ sāhacarya-phala-pradaḥ — results by association; base nature unclassified",
                ["Sun's results depend on association; do not infer an unconditional benefic or malefic nature"]),
    Graha.MOON: (_M, _Yn, _Kn, _EV, "34.31", "indu pāpa", []),
    Graha.MARS: (_M, _Yn, _Kq, _EV, "34.31",
                 "kuja pāpa by explicit verse; killer capacity via 8th lordship is commentary-derived",
                 ["Mars's qualified māraka capacity comes from the supplied commentary and 8th lordship, not explicit māraka language in the śloka"],
                 _TJ),
    Graha.MERCURY: (_B, _Ya, _Kn, _EV, "34.31",
                    "budha śubha and explicitly yogakāraka (34.31)",
                    ["Mercury carries verse_yoga_status=yoga_agent while ownership_yogakaraka remains false — owning the 1st and 10th does not satisfy the locked ownership rule, which excludes the Lagna as the trikoṇa half"]),
    Graha.JUPITER: (_M, _Yn, _Kn, _EV, "34.31", "jīva pāpa", []),
    Graha.VENUS: (_B, _Ya, _Km, _EV, "34.31-32",
                  "śukra śubha and yogakāraka (34.31); mārako'pi kaviḥ (34.32)",
                  ["Venus simultaneously remains benefic, yoga agent and māraka — none of these dimensions may overwrite another",
                   "Venus owns the 2nd and 9th but no kendra, so ownership_yogakaraka remains false; her yoga status comes from 34.31"]),
    Graha.SATURN: (_X, _Yn, _Kn, _TJ, "34.31-32",
                   "not classified by either verse; commentary reads 5th lordship as supportive, 6th lordship as preventing an invariant benefic",
                   ["Saturn is mixed by commentary judgment: 5th lordship supports, while 6th lordship prevents an invariant benefic classification",
                    "Do not manufacture a verse classification for Saturn"]),
}

# ── LIBRA (Tulā) — SOURCE-CONFIRMED, BPHS 34.33-34 ───────────────────────────
# 34.33: Jupiter, Sun and Mars are pāpa; Saturn and Mercury are śubha; and
# bhavetāṃ rājayogasya kārakau candra-tat-sutau names the MOON and MERCURY the
# rājayoga agents. 34.34: kujo nihanti — Mars DIRECTLY kills, which is stronger
# than the māraka-lakṣaṇa carried by Jupiter and the other listed malefics, so
# Mars alone is primary_killer here and Sun/Jupiter stay maraka. śukraḥ samaḥ
# makes Venus explicitly NEUTRAL — neither benefic nor malefic. Saturn owns the
# 4th + 5th and so satisfies the ownership rule, though the verses never call it
# a yoga agent: ownership_yogakaraka=true with verse_yoga_status=none.
# NOTE ON SOURCE: the opening compound was supplied as जीवार्कमूसुताः; भूसुत
# (bhū-suta, "earth-born" = Mars) is the standard epithet and मूसुत is not an
# attested form, so जीवार्कभूसुताः is the expected reading. The Devanagari is
# not stored here, and the encoding below is unaffected either way.
BPHS34_MATRIX[6] = {
    Graha.SUN: (_M, _Yn, _Km, _EV, "34.33-34",
                "arka pāpa (34.33); māraka-lakṣaṇa among jīvādi (34.34)",
                ["Mars is the direct killer; Jupiter and Sun possess only māraka characteristics",
                 "Commentary: Jupiter, Mars and Sun become more harmful when mutually associated and disconnected from Saturn, Mercury or Moon — commentary data only",
                 "One school states Mars or Sun may act beneficially when associated with Saturn, Mercury or Venus — alternate commentary view; base malefic nature is unchanged"],
                _EV),
    Graha.MOON: (_N, _Ya, _Kn, _TJ, "34.33",
                 "rājayogasya kārakau candra-tat-sutau — explicit verse yoga agent; functional nature unclassified",
                 ["Moon and Mercury are explicit rājayoga agents (34.33)"],
                 None, _EV),
    Graha.MARS: (_M, _Yn, _Kp, _EV, "34.33-34",
                 "bhūsuta pāpa (34.33); kujo nihanti — direct killing language (34.34)",
                 ["Mars is the direct killer; Jupiter and Sun possess only māraka characteristics",
                  "Commentary: Jupiter, Mars and Sun become more harmful when mutually associated and disconnected from Saturn, Mercury or Moon — commentary data only",
                  "One school states Mars or Sun may act beneficially when associated with Saturn, Mercury or Venus — alternate commentary view; base malefic nature is unchanged"],
                 _EV),
    Graha.MERCURY: (_B, _Ya, _Kn, _EV, "34.33",
                    "budha śubha and explicit rājayoga agent (34.33)",
                    ["Moon and Mercury are explicit rājayoga agents (34.33)"],
                    None, _EV),
    Graha.JUPITER: (_M, _Yn, _Km, _EV, "34.33-34",
                    "jīva pāpa (34.33); jīvādyāḥ pāpā māraka-lakṣaṇāḥ (34.34)",
                    ["Mars is the direct killer; Jupiter and Sun possess only māraka characteristics",
                     "Commentary: Jupiter, Mars and Sun become more harmful when mutually associated and disconnected from Saturn, Mercury or Moon — commentary data only"],
                    _EV),
    Graha.VENUS: (_N, _Yn, _Kn, _EV, "34.34",
                  "śukraḥ samaḥ — explicitly neutral",
                  ["Venus is explicitly neutral, not benefic or malefic"]),
    Graha.SATURN: (_B, _Yn, _Kn, _EV, "34.33",
                   "śanaiścara śubha",
                   ["Saturn is an ownership yogakāraka (4th + 5th lordship) but not a verse yoga agent"]),
}

# ── SCORPIO (Vṛścika) — SOURCE-CONFIRMED, BPHS 34.35-36 ──────────────────────
# 34.35: Venus, Mercury and Saturn are pāpa; Jupiter and Moon are śubha; and
# sūryā-candramasau eva bhavetāṃ yogakārakau names the SUN and MOON the yoga
# agents — the Sun's own functional nature is never classified, so it is neutral
# by translation judgment with the yoga statement itself explicit. 34.36:
# kujaḥ samaḥ makes Mars explicitly NEUTRAL, and sitādyāḥ ca pāpā
# māraka-lakṣaṇāḥ gives Venus, Mercury and Saturn māraka characteristics — the
# weaker language, so no Scorpio graha is a primary_killer. No Scorpio graha
# satisfies the locked ownership rule, and being a verse yoga agent never
# creates one.
BPHS34_MATRIX[7] = {
    Graha.SUN: (_N, _Ya, _Kn, _TJ, "34.35",
                "sūryā-candramasau eva bhavetāṃ yogakārakau — explicit verse yoga agent; base nature unclassified",
                ["Sun and Moon are explicit verse yoga agents (34.35)",
                 "Sun's base nature remains unclassified and is encoded neutral by translation judgment",
                 "Do not invent ownership-yogakāraka status for Sun or Moon merely because the verse calls them yoga agents"],
                None, _EV),
    Graha.MOON: (_B, _Ya, _Kn, _EV, "34.35",
                 "niśākara śubha and explicit verse yoga agent",
                 ["Sun and Moon are explicit verse yoga agents (34.35)",
                  "Do not invent ownership-yogakāraka status for Sun or Moon merely because the verse calls them yoga agents"],
                 None, _EV),
    Graha.MARS: (_N, _Yn, _Kn, _EV, "34.36",
                 "kujaḥ samaḥ — explicitly neutral",
                 ["Mars is explicitly neutral because the verse says kujaḥ samaḥ"]),
    Graha.MERCURY: (_M, _Yn, _Km, _EV, "34.35-36",
                    "jña pāpa (34.35); māraka-lakṣaṇa among sitādi (34.36)",
                    ["Venus, Mercury and Saturn are mārakas through māraka-lakṣaṇa; none is a primary_killer"],
                    _EV),
    Graha.JUPITER: (_B, _Yn, _Kn, _EV, "34.35", "guru śubha", []),
    Graha.VENUS: (_M, _Yn, _Km, _EV, "34.35-36",
                  "sita pāpa (34.35); sitādyāḥ ca pāpā māraka-lakṣaṇāḥ (34.36)",
                  ["Venus, Mercury and Saturn are mārakas through māraka-lakṣaṇa; none is a primary_killer"],
                  _EV),
    Graha.SATURN: (_M, _Yn, _Km, _EV, "34.35-36",
                   "śani pāpa (34.35); māraka-lakṣaṇa among sitādi (34.36)",
                   ["Venus, Mercury and Saturn are mārakas through māraka-lakṣaṇa; none is a primary_killer",
                    "Commentary: Saturn may produce practical auspicious results when placed in the 5th or 9th — conditional commentary only; base malefic classification is unchanged"],
                   _EV),
}

# ── SAGITTARIUS (Dhanus) — SOURCE-CONFIRMED, BPHS 34.37-38 ───────────────────
# 34.37: eka eva kaviḥ pāpaḥ — VENUS ALONE is malefic; Mars and Sun are śubha;
# yogo bhāskara-saumyābhyām makes the SUN and MERCURY yoga agents; and
# nihantā bhāskarātmajaḥ names SATURN the direct killer. Mercury's and Saturn's
# own natures are never classified, so both are neutral by translation judgment
# while their verse-given yoga / killer statements stay explicit. 34.38:
# guruḥ sama-phalaḥ khyātaḥ — Jupiter is explicitly MIXED (sama-phala), not
# neutral; śukro māraka-lakṣaṇaḥ gives Venus the weaker killer language, so
# Venus is maraka and never primary_killer. No Sagittarius graha satisfies the
# locked ownership rule.
BPHS34_MATRIX[8] = {
    Graha.SUN: (_B, _Ya, _Kn, _EV, "34.37",
                "divākara śubha and yogo bhāskara-saumyābhyām — explicit verse yoga agent",
                ["Sun and Mercury are explicit yoga agents (34.37)"],
                None, _EV),
    Graha.MOON: (_N, _Yn, _Kn, _TJ, "34.37-38",
                 "base nature not classified by either verse",
                 ["Moon remains neutral by translation judgment",
                  "Commentary-based yoga possibilities through association with Jupiter, Mercury, Sun or Mars remain conditional data only"]),
    Graha.MARS: (_B, _Yn, _Kn, _EV, "34.37", "bhauma śubha",
                 ["Commentary may describe Mars as predominantly favourable; this must not overwrite its verse-grounded dimensions"]),
    Graha.MERCURY: (_N, _Ya, _Kn, _TJ, "34.37",
                    "yogo bhāskara-saumyābhyām — explicit verse yoga agent; base nature unclassified",
                    ["Sun and Mercury are explicit yoga agents (34.37)",
                     "Mercury's functional nature remains unclassified — do not infer benefic nature merely from yoga status",
                     "Commentary may describe Mercury as auspicious; this must not overwrite its verse-grounded dimensions"],
                    None, _EV),
    Graha.JUPITER: (_X, _Yn, _Kn, _EV, "34.38",
                    "guruḥ sama-phalaḥ khyātaḥ — explicitly MIXED",
                    ["Jupiter is explicitly sama-phala and must remain MIXED, not NEUTRAL"]),
    Graha.VENUS: (_M, _Yn, _Km, _EV, "34.37-38",
                  "eka eva kaviḥ pāpaḥ (34.37); śukro māraka-lakṣaṇaḥ (34.38)",
                  ["Venus carries only māraka-lakṣaṇa, so it is maraka, never primary_killer"],
                  _EV),
    Graha.SATURN: (_N, _Yn, _Kp, _TJ, "34.37",
                   "nihantā bhāskarātmajaḥ — explicit direct killer; base nature unclassified",
                   ["Saturn is the explicit direct killer through nihantā; its base nature remains unclassified"],
                   _EV),
}

# ── CAPRICORN (Makara / Mṛga) — SOURCE-CONFIRMED, BPHS 34.39-40 ──────────────
# 34.39: Mars, Jupiter and Moon are pāpa; Venus and Mercury are śubha;
# mandaḥ svayaṃ na hantā syāt — SATURN does not kill independently — while
# hanti pāpāḥ kujādayaḥ gives DIRECT killing to the verse-listed malefics
# beginning with Mars, i.e. Mars, Jupiter and Moon (all three primary_killer).
# Saturn's qualified status is commentary-derived (association with those three
# can activate killing capacity), so its māraka provenance is a translation
# judgment and it is never promoted to primary_killer. 34.40:
# sūryaḥ sama-phalaḥ proktaḥ — the Sun is explicitly MIXED; kavir ekaḥ
# su-yoga-kṛt makes VENUS the sole superior-yoga agent, and Venus independently
# satisfies the ownership rule through 5th + 10th lordship.
BPHS34_MATRIX[9] = {
    Graha.SUN: (_X, _Yn, _Kn, _EV, "34.40",
                "sūryaḥ sama-phalaḥ proktaḥ — explicitly MIXED",
                ["Sun is explicitly sama-phala and must remain MIXED"]),
    Graha.MOON: (_M, _Yn, _Kp, _EV, "34.39",
                 "indu pāpa; hanti pāpāḥ kujādayaḥ — direct killing among the listed malefics",
                 ["hanti pāpāḥ kujādayaḥ applies to the verse-listed malefics Mars, Jupiter and Moon; all three carry direct killing status"],
                 _EV),
    Graha.MARS: (_M, _Yn, _Kp, _EV, "34.39",
                 "kuja pāpa; hanti pāpāḥ kujādayaḥ — direct killing",
                 ["hanti pāpāḥ kujādayaḥ applies to the verse-listed malefics Mars, Jupiter and Moon; all three carry direct killing status"],
                 _EV),
    Graha.MERCURY: (_B, _Yn, _Kn, _EV, "34.39", "candraja śubha",
                    ["Mercury remains benefic but is not a verse yoga agent"]),
    Graha.JUPITER: (_M, _Yn, _Kp, _EV, "34.39",
                    "jīva pāpa; hanti pāpāḥ kujādayaḥ — direct killing",
                    ["hanti pāpāḥ kujādayaḥ applies to the verse-listed malefics Mars, Jupiter and Moon; all three carry direct killing status"],
                    _EV),
    Graha.VENUS: (_B, _Ya, _Kn, _EV, "34.39-40",
                  "bhārgava śubha (34.39); kavir ekaḥ su-yoga-kṛt — sole superior-yoga agent (34.40)",
                  ["Venus carries both facts independently: verse_yoga_status=yoga_agent (34.40) and ownership_yogakaraka=true (5th + 10th lordship)"],
                  None, _EV),
    Graha.SATURN: (_N, _Yn, _Kq, _TJ, "34.39",
                   "mandaḥ svayaṃ na hantā syāt — not an independent killer; base nature unclassified",
                   ["Saturn is not an independent killer; its qualified status comes from the supplied commentary that association with Mars, Jupiter or Moon can activate killing capacity",
                    "Do not promote Saturn to primary_killer"],
                   _TJ),
}

# ── AQUARIUS (Kumbha) — SOURCE-CONFIRMED, BPHS 34.41-42 ──────────────────────
# 34.41: Jupiter, Moon and Mars are pāpa; Venus and Saturn are śubha; and
# rājayogakaraḥ ... kavir eva makes VENUS ALONE the rājayoga agent — Venus also
# independently satisfies the ownership rule (4th + 9th). Saturn stays benefic
# with NEITHER kind of yoga status (1st + 12th does not satisfy the locked rule,
# which excludes the Lagna). The sentence runs across the verse boundary:
# bṛhaspatiḥ | sūryo bhaumaś ca hantāraḥ — JUPITER, SUN and MARS are the direct
# killers, so all three are primary_killer. The Sun's own nature is never
# classified → neutral by translation judgment with the killer statement
# explicit. 34.42: budho madhya-phalaḥ smṛtaḥ — Mercury is explicitly MIXED.
BPHS34_MATRIX[10] = {
    Graha.SUN: (_N, _Yn, _Kp, _TJ, "34.42",
                "sūryo bhaumaś ca hantāraḥ — direct killer by explicit verse; base nature unclassified",
                ["Jupiter, Sun and Mars are primary killers because the verse uses direct hantāraḥ language (34.41-42)",
                 "Sun's nature remains unclassified and is encoded neutral by translation judgment",
                 "The commentary's relative ordering of the three killers remains prose only; no killer-strength score or rank is introduced"],
                _EV),
    Graha.MOON: (_M, _Yn, _Kn, _EV, "34.41", "candra pāpa", []),
    Graha.MARS: (_M, _Yn, _Kp, _EV, "34.41-42",
                 "kuja pāpa (34.41); sūryo bhaumaś ca hantāraḥ (34.42)",
                 ["Jupiter, Sun and Mars are primary killers because the verse uses direct hantāraḥ language (34.41-42)",
                  "The commentary's relative ordering of the three killers remains prose only; no killer-strength score or rank is introduced"],
                 _EV),
    Graha.MERCURY: (_X, _Yn, _Kn, _EV, "34.42",
                    "budho madhya-phalaḥ smṛtaḥ — explicitly MIXED",
                    ["Mercury is explicitly madhya-phala and must remain MIXED",
                     "Mercury's improvement with Venus or Saturn and deterioration with adverse associations remain conditional commentary data"]),
    Graha.JUPITER: (_M, _Yn, _Kp, _EV, "34.41-42",
                    "jīva pāpa (34.41); bṛhaspatiḥ ... hantāraḥ across the verse boundary (34.41-42)",
                    ["Jupiter, Sun and Mars are primary killers because the verse uses direct hantāraḥ language (34.41-42)",
                     "The commentary's relative ordering of the three killers remains prose only; no killer-strength score or rank is introduced"],
                    _EV),
    Graha.VENUS: (_B, _Ya, _Kn, _EV, "34.41",
                  "śukra śubha and rājayogakaraḥ kavir eva — sole verse yoga agent",
                  ["Venus alone carries verse_yoga_status=yoga_agent (34.41)",
                   "Venus independently carries ownership_yogakaraka=true through 4th + 9th lordship"],
                  None, _EV),
    Graha.SATURN: (_B, _Yn, _Kn, _EV, "34.41",
                   "sūryātmaja śubha",
                   ["Saturn remains benefic but has neither verse yoga nor ownership-yogakāraka status; 1st + 12th lordship does not satisfy the locked rule, which excludes the Lagna"]),
}

# ── PISCES (Mīna) — SOURCE-CONFIRMED, BPHS 34.43-44 ──────────────────────────
# 34.43: Saturn, Venus, Sun and Mercury are pāpa; Mars and Moon are śubha; and
# mahīsuta-gurū yogakārakau names MARS and JUPITER the yoga agents — Jupiter's
# own nature is never classified, so it is neutral by translation judgment with
# the yoga statement explicit. 34.44: mārako'pi na hantā'sau — Mars IS a māraka
# but explicitly does NOT kill independently, which is exactly the QUALIFIED
# semantics and forbids promoting it to primary_killer; manda-jñau mārakau
# smṛtau gives Saturn and Mercury ordinary māraka status. Venus's killer
# capacity is commentary-derived from 8th lordship, so its māraka provenance is
# a translation judgment. No Pisces graha satisfies the locked ownership rule,
# and verse yoga status never creates one.
BPHS34_MATRIX[11] = {
    Graha.SUN: (_M, _Yn, _Kn, _EV, "34.43", "aṃśumat pāpa", []),
    Graha.MOON: (_B, _Yn, _Kn, _EV, "34.43", "vidhu śubha", []),
    Graha.MARS: (_B, _Ya, _Kq, _EV, "34.43-44",
                 "bhauma śubha and yogakāraka (34.43); mārako'pi na hantā'sau (34.44)",
                 ["Mars simultaneously remains benefic, verse yoga agent and qualified māraka",
                  "mārako'pi na hantā'sau explicitly prevents Mars from becoming a primary_killer",
                  "Mars requires activation by another killer, specifically Saturn or Mercury according to the commentary",
                  "Do not infer ownership-yogakāraka status for Mars from its verse yoga status"],
                 _EV, _EV),
    Graha.MERCURY: (_M, _Yn, _Km, _EV, "34.43-44",
                    "saumya pāpa (34.43); manda-jñau mārakau smṛtau (34.44)",
                    ["Saturn and Mercury are ordinary maraka, not primary_killer, because the verse says mārakau"],
                    _EV),
    Graha.JUPITER: (_N, _Ya, _Kn, _TJ, "34.43",
                    "mahīsuta-gurū yogakārakau — explicit verse yoga agent; base nature unclassified",
                    ["Jupiter is an explicit yoga agent, but its base nature remains unclassified and is encoded neutral by translation judgment",
                     "Do not infer ownership-yogakāraka status for Jupiter from its verse yoga status"],
                    None, _EV),
    Graha.VENUS: (_M, _Yn, _Kq, _EV, "34.43-44",
                  "śukra pāpa (34.43); killer capacity is commentary-derived from 8th lordship",
                  ["Venus's qualified killer capacity is commentary-derived from 8th lordship and must not be presented as explicit verse"],
                  _TJ),
    Graha.SATURN: (_M, _Yn, _Km, _EV, "34.43-44",
                   "manda pāpa (34.43); manda-jñau mārakau smṛtau (34.44)",
                   ["Saturn and Mercury are ordinary maraka, not primary_killer, because the verse says mārakau"],
                   _EV),
}

def _lordships(lagna_sign_index: int) -> Dict[Graha, List[int]]:
    out: Dict[Graha, List[int]] = {}
    for h in range(1, 13):
        out.setdefault(SIGN_LORDS[(lagna_sign_index + h - 1) % 12], []).append(h)
    return {g: sorted(v) for g, v in out.items()}

def functional_roles(lagna_sign_index: int) -> List[FunctionalRoleV1]:
    """Roles from the doctrine matrix, with ownership_yogakaraka computed live
    and kept ORTHOGONAL to the verse's yoga language (QA v3 HIGH-3). While the
    doctrine is populated one Lagna at a time, cells of unpopulated Lagnas remain
    REVIEW_REQUIRED; ownership_yogakaraka is valid for every Lagna because it
    derives from the general kendra+trikoṇa rule, not the per-Lagna verses."""
    lords = _lordships(lagna_sign_index)
    row = BPHS34_MATRIX[lagna_sign_index]
    yk_here = {g for (l, g) in ownership_yogakarakas() if l == lagna_sign_index}
    out: List[FunctionalRoleV1] = []
    for g in (Graha.SUN, Graha.MOON, Graha.MARS, Graha.MERCURY,
              Graha.JUPITER, Graha.VENUS, Graha.SATURN):
        cell = row[g]
        nature, vyoga, maraka, prov, verse, note, conds = cell[:7]
        maraka_prov = cell[7] if len(cell) > 7 else None
        yoga_prov = cell[8] if len(cell) > 8 else None
        out.append(FunctionalRoleV1(
            graha=g, lordships=lords.get(g, []),
            functional_nature=nature, verse_yoga_status=vyoga,
            ownership_yogakaraka=(g in yk_here), maraka_status=maraka,
            nature_provenance=prov, maraka_provenance=maraka_prov,
            yoga_provenance=yoga_prov,
            verse=(f"BPHS {verse}" if verse != "review_required" else "review_required"),
            note=f"{SIGNS[lagna_sign_index]} Lagna: {note}",
            conditional_rules=list(conds)))
    return out

# The strict OWNERSHIP-based yogakāraka invariant (a graha owning a kendra AND a
# trikoṇa), kept SEPARATE from the broader verse yoga language. This is the
# exact-six set and is derivable, not doctrinal-by-reading.
def ownership_yogakarakas() -> List[tuple]:
    out = []
    KENDRA, TRIKONA = {4, 7, 10}, {5, 9}   # 1 excluded: lagna is not the trikoṇa half
    for lagna in range(12):
        for g, owned in _lordships(lagna).items():
            if g in (Graha.RAHU, Graha.KETU):
                continue
            if any(h in KENDRA for h in owned) and any(h in TRIKONA for h in owned):
                out.append((lagna, g))
    return sorted(out)
