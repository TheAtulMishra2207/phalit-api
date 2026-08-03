"""
pratiphala_contract.py — Pratiphala (प्रतिफल) response contract.

Pratiphala is a CROSS-VARGA SYNTHESIS: it reads a graha's D1 dignity against its
D9 dignity and reports whether the chart's promise actually ripens. It is a
SEPARATE typed layer on purpose. The founder ruled on 27 Jul that D1 and D9
values plus a manifestation verdict must not be bolted onto /d1/prepare, because
that silently expands the D1 migration into a partial Pratiphala one. This module
CONSUMES the certified D1 and D9 payloads and adds nothing to them.

TWO SEPARATIONS THIS FILE ENFORCES STRUCTURALLY:

  1. DISPLAY vs EVIDENCE. Numeric dignity ranks are an internal ordering, not a
     reading. They live only inside PratiphalaEvidence, which is a distinct
     nested model, so no display path can reach a bare integer by accident. The
     frontend renders sub-tier labels; it never renders 0..6.

  2. GOVERNING vs UNDERLYING. A vargottama graha is Sovereign regardless of its
     quadrant, but the quadrant is still true and still worth recording. The
     verdict a consumer must render is `governing_state`; the quadrant survives
     as `underlying_state` and is explicitly marked non-governing.

UNKNOWN IS A FIFTH STATE, NOT A MISSING FOURTH. Rahu and Ketu carry no D9
dignity outside Taurus/Scorpio — the certified adapter maps the 'Node' sentinel
to None. Absence of dignity is absence of data, not a weak result, so UNKNOWN
never collapses into Rikt. It carries an explicit basis and NO corpus text,
because the corpus covers the four real quadrants only.

Pydantic v1 (production pins 1.10.13). Extra.forbid throughout: an unknown or
misspelled field is a 422 at the boundary rather than a silently ignored one.
"""
from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Extra, Field, StrictStr, root_validator, validator

from d1_contract import Dignity, Graha

# PF-007. Only the nodes may lack a certified dignity: the adapter maps the
# 'Node' sentinel to None for Rahu and Ketu outside Taurus/Scorpio. A classical
# graha with no dignity is a broken chart, not an unknown reading, so absence is
# permitted here and refused everywhere else.
DIGNITY_OPTIONAL_FOR = frozenset({Graha.RAHU, Graha.KETU})

# PF-008. The seven classical rāśi lords. Rahu and Ketu own no sign in the
# Parāśarī scheme, so they can never lord a house. The production builder
# already only ever selects from these; this is the CONTRACT saying so, which is
# what stops a hand-built or deserialised payload asserting otherwise.
# PF-009. The twelve rāśi lords, index = sign_index, Aries first. ONE immutable
# copy: the route imports this object rather than keeping its own list, so the
# builder and the validator cannot disagree about who rules what. A second table
# would let a drift in either be invisible to the other.
RASHI_LORDS = (
    Graha.MARS,     # 0  Aries
    Graha.VENUS,    # 1  Taurus
    Graha.MERCURY,  # 2  Gemini
    Graha.MOON,     # 3  Cancer
    Graha.SUN,      # 4  Leo
    Graha.MERCURY,  # 5  Virgo
    Graha.VENUS,    # 6  Libra
    Graha.MARS,     # 7  Scorpio
    Graha.JUPITER,  # 8  Sagittarius
    Graha.SATURN,   # 9  Capricorn
    Graha.SATURN,   # 10 Aquarius
    Graha.JUPITER,  # 11 Pisces
)


def expected_lord_of(lagna_sign_index: int, house: int) -> Graha:
    """Whole Sign: the house's sign is counted from the lagna."""
    return RASHI_LORDS[(lagna_sign_index + house - 1) % 12]


CLASSICAL_HOUSE_LORDS = frozenset({
    Graha.SUN, Graha.MOON, Graha.MARS, Graha.MERCURY,
    Graha.JUPITER, Graha.VENUS, Graha.SATURN,
})

CONTRACT_VERSION = "pratiphala-contract-0.1.0"

# ── the locked dignity scale ────────────────────────────────────────────────
# Seven positions, 0..6. This is the ordering the verdict is computed on; it is
# NEVER a display value and NEVER a corpus key.
#
# Dignity.GREAT_FRIEND and Dignity.GREAT_ENEMY are deliberately ABSENT. They are
# valid contract values but the certified engine has no panchadha-maitri layer
# and cannot produce them (d1_chart_adapter.UNREACHABLE_FROM_LIVE_ENGINE says so
# explicitly). Admitting them here would mean inventing their rank; a payload
# carrying one is refused instead, and that refusal is a finding worth seeing.
DIGNITY_RANK = {
    Dignity.DEBILITATED: 0,
    Dignity.ENEMY: 1,
    Dignity.NEUTRAL: 2,
    Dignity.FRIEND: 3,
    Dignity.OWN: 4,
    Dignity.MOOLATRIKONA: 5,
    Dignity.EXALTED: 6,
}
RANK_MIN, RANK_MAX = 0, 6
STRONG_AT = 3            # rank >= 3 is Strong; rank <= 2 is Weak

# PF-010. The published policy block's exact strings, as named constants. The
# defaults AND the validator read these same objects, so the block cannot state
# one rule while the shared policy functions implement another. Duplicate
# literals would be two declarations of one rule, which is how the stale
# "absent D9" wording survived PF-007 in the first place.
SCALE_DESCRIPTION = "debilitated0-enemy1-neutral2-friend3-own4-moolatrikona5-exalted6"
SOVEREIGN_RULE = ("vargottama overrides an assessed four-state quadrant only; it "
                  "never overrides UNKNOWN")
UNKNOWN_RULE = ("an absent D1 OR D9 dignity yields UNKNOWN, which never becomes "
                "Rikt or Sovereign")


class Strength(str, Enum):
    STRONG = "Strong"
    WEAK = "Weak"


class SubTier(str, Enum):
    """Qualitative band. The consumer renders this; it never renders the rank."""
    UTTAMA = "Uttama"        # 5-6
    MADHYA = "Madhya"        # 3-4
    ALPA = "Alpa"            # 2
    WEAK = "Weak"            # 0-1
    UNKNOWN = "UNKNOWN"      # no dignity to band


class PratiphalaState(str, Enum):
    """Four quadrants plus UNKNOWN. UNKNOWN is a state, not a gap."""
    SIDDHA = "Siddha"          # D1 Strong x D9 Strong
    VIPHALA = "Viphala"        # D1 Strong x D9 Weak
    PRACHANNA = "Prachanna"    # D1 Weak   x D9 Strong
    RIKT = "Rikt"              # D1 Weak   x D9 Weak
    UNKNOWN = "UNKNOWN"        # no certified D9 dignity


class GoverningLabel(str, Enum):
    """What the consumer actually renders as the verdict."""
    SIDDHA = "Siddha"
    VIPHALA = "Viphala"
    PRACHANNA = "Prachanna"
    RIKT = "Rikt"
    UNKNOWN = "UNKNOWN"
    SOVEREIGN = "Sovereign"    # vargottama override


STATE_SA = {
    PratiphalaState.SIDDHA: "सिद्ध",
    PratiphalaState.VIPHALA: "विफल",
    PratiphalaState.PRACHANNA: "प्रच्छन्न",
    PratiphalaState.RIKT: "रिक्त",
    PratiphalaState.UNKNOWN: "",
}
SOVEREIGN_SA = "सार्वभौम"

# Bhāva names, transcribed from the page's HOUSE_NAMES so the server and the
# renderer name the same house the same way. Index 0 is unused.
HOUSE_NAMES = ["", "Lagna", "Dhana", "Parakrama", "Sukha", "Putra", "Ripu",
               "Kalatra", "Randhra", "Bhagya", "Karma", "Labha", "Vyaya"]


# ── THE SHARED POLICY (PF-006) ──────────────────────────────────────────────
# One copy of the rank, strength, tier and quadrant rules, used by BOTH the
# resolver and the contract validator. Two copies would be two engines: the
# validator could agree with a resolver that had drifted, which is the exact
# shape this programme exists to remove.

class PratiphalaPolicyError(ValueError):
    """A dignity with no position on the locked scale. Never repaired."""


def rank_of(dignity) -> Optional[int]:
    """None stays None. An unknown dignity RAISES rather than defaulting.

    Great Friend and Great Enemy are valid contract values the live engine
    cannot produce, so they have no rank here. Guessing one would invent
    doctrine; refusing makes the gap visible.
    """
    if dignity is None:
        return None
    if dignity not in DIGNITY_RANK:
        raise PratiphalaPolicyError(
            f"{getattr(dignity, 'value', dignity)!r} has no position on the "
            f"locked Pratiphala scale; the scale covers "
            f"{sorted(d.value for d in DIGNITY_RANK)}")
    return DIGNITY_RANK[dignity]


def strength_of(rank: Optional[int]):
    if rank is None:
        return None
    return Strength.STRONG if rank >= STRONG_AT else Strength.WEAK


def sub_tier_of(rank: Optional[int]):
    if rank is None:
        return SubTier.UNKNOWN
    if rank >= 5:
        return SubTier.UTTAMA        # 5-6
    if rank >= 3:
        return SubTier.MADHYA        # 3-4
    if rank == 2:
        return SubTier.ALPA          # 2
    return SubTier.WEAK              # 0-1


def quadrant_of(d1_rank: Optional[int], d9_rank: Optional[int]):
    """The four ordinary states, or UNKNOWN when either side has no dignity.

    UNKNOWN is returned rather than falling through to Rikt: a graha with no
    certified dignity has not been assessed and found weak, it has not been
    assessed at all.
    """
    if d1_rank is None or d9_rank is None:
        return PratiphalaState.UNKNOWN
    d1_strong, d9_strong = d1_rank >= STRONG_AT, d9_rank >= STRONG_AT
    if d1_strong and d9_strong:
        return PratiphalaState.SIDDHA
    if d1_strong and not d9_strong:
        return PratiphalaState.VIPHALA
    if not d1_strong and d9_strong:
        return PratiphalaState.PRACHANNA
    return PratiphalaState.RIKT


def governing_of(quadrant, is_vargottama: bool):
    """PRECEDENCE, in one place: absent D9 outranks vargottama (PF-001)."""
    if quadrant is PratiphalaState.UNKNOWN:
        return GoverningLabel.UNKNOWN
    if is_vargottama:
        return GoverningLabel.SOVEREIGN
    return GoverningLabel(quadrant.value)


def governing_sa_of(governing) -> str:
    if governing is GoverningLabel.SOVEREIGN:
        return SOVEREIGN_SA
    if governing is GoverningLabel.UNKNOWN:
        return ""
    return STATE_SA[PratiphalaState(governing.value)]


def graha_corpus_key_of(graha, governing) -> Optional[str]:
    if governing is GoverningLabel.UNKNOWN:
        return None
    return f"PRATIPHALA-{graha.value}-{governing.value}"


class _Strict(BaseModel):
    class Config:
        extra = Extra.forbid
        use_enum_values = False


# ── request ─────────────────────────────────────────────────────────────────

class PratiphalaPrepareRequest(_Strict):
    """POST /pratiphala/prepare.

    One field. Extra.forbid means a misspelled `chart_tokn` is a 422 rather than
    a request that looks well-formed and quietly does the wrong thing — the
    failure mode KAR-093-B04 produced when a dropped field defaulted silently.
    """
    chart_token: StrictStr = Field(min_length=8, max_length=256)


class PratiphalaReportRequest(_Strict):
    """POST /pratiphalareport.

    TWO FIELDS. Extra.forbid, so the client CANNOT submit the interpretation the
    narrative describes: no graha array, no house overlays, no governing states,
    no dignities, no corpus text, no evidence. The server resolves the chart and
    derives the reading itself, which is the only arrangement under which the
    prose and the structured cards cannot disagree.
    """
    chart_token: StrictStr = Field(min_length=8, max_length=256)
    name: Optional[StrictStr] = Field(default=None, max_length=120)


class FramingIntroductionId(str, Enum):
    """The provider may CHOOSE a framing. It may not write one."""
    PLAIN = "plain"
    REFLECTIVE = "reflective"
    PRACTICAL = "practical"


class FramingConclusionId(str, Enum):
    PLAIN = "plain"
    REFLECTIVE = "reflective"
    PRACTICAL = "practical"


class ProviderFraming(_Strict):
    """PF-013 step B. SELECTION, not authorship.

    Free prose could not be proved non-interpretive. A blocklist rejected
    "Rikt" and "score" and cheerfully accepted "Rahu brings misfortune and
    failure" — same claim, different words — and no amount of added synonyms
    fixes that, because the space of ways to say a thing is not enumerable.

    So the provider no longer returns text at all. It returns two identifiers,
    and the server looks up its own static templates. There is nothing left to
    validate for meaning: a value that is not one of the declared IDs simply
    does not parse.

    Extra.forbid, and the legacy `introduction`/`conclusion` prose fields are
    therefore rejected as unknown fields rather than quietly ignored.
    """
    introduction_id: FramingIntroductionId
    conclusion_id: FramingConclusionId


class PratiphalaReportResponse(_Strict):
    chart_token: StrictStr = Field(min_length=8, max_length=256)
    report: StrictStr = Field(min_length=1)


# ── evidence, deliberately quarantined from display ─────────────────────────

class PratiphalaEvidence(_Strict):
    """Internal ordering. NOT a display surface.

    Ranks live here and nowhere else, so a renderer cannot reach a bare integer
    by walking the display fields. Publishing them at all follows the
    birth_lagna_sign_index principle: a derived verdict whose inputs are absent
    from the payload is a claim nothing can check.
    """
    d1_rank: Optional[int] = Field(default=None, ge=RANK_MIN, le=RANK_MAX)
    d9_rank: Optional[int] = Field(default=None, ge=RANK_MIN, le=RANK_MAX)
    d1_strength: Optional[Strength] = None
    d9_strength: Optional[Strength] = None
    strong_at_rank: int = STRONG_AT
    # The quadrant that WOULD govern absent the Sovereign override. Retained as
    # non-governing evidence so the override is auditable rather than opaque.
    underlying_state: PratiphalaState
    underlying_state_sa: str = ""
    sovereign_override_applied: bool = False


class CorpusRef(_Strict):
    """Key plus resolved text. UNKNOWN carries neither.

    PF-002. `resolvable` reports whether prose was ACTUALLY OBTAINED, not
    whether a key could be constructed. Setting it from the key alone claimed a
    reference had resolved while no text existed anywhere — a flag contradicting
    the payload it describes, which is the same shape as a declared constraint
    with nothing behind it.

    Exactly three states are legal:
      key + text + resolvable=True    prose obtained
      key + no text + resolvable=False  key known, prose not authored yet
      no key + no text + resolvable=False  UNKNOWN
    """
    key: Optional[StrictStr] = None
    text: Optional[StrictStr] = None
    resolvable: bool = False

    @validator("key", "text")
    def _absent_or_substantive(cls, v, field):
        """PF-003. A blank-but-present value is a FOURTH state.

        Treating whitespace as absent for comparison while keeping it in the
        payload meant the flag logic and the serialised value disagreed about
        whether anything was there. Absent is None; present means trimmed and
        non-empty. Rejected rather than silently coerced, because a caller who
        sent "   " believed they were sending something.
        """
        if v is None:
            return None
        if not v.strip():
            raise ValueError(
                f"{field.name} is present but blank; use None for absent, or a "
                f"non-empty value. A blank string is a fourth corpus state and "
                f"the contract declares exactly three")
        return v.strip()

    @root_validator(skip_on_failure=True)
    def _flag_matches_the_payload(cls, values):
        key, text, resolvable = values.get("key"), values.get("text"), values.get("resolvable")
        has_key, has_text = bool(key and key.strip()), bool(text and text.strip())
        # Most specific diagnosis first: text with no key is a distinct fault
        # from a flag set without text, and the generic message would mask it.
        if has_text and not has_key:
            raise ValueError("corpus text without a key: nothing identifies where it came from")
        if resolvable and not (has_key and has_text):
            raise ValueError(
                "resolvable=True requires BOTH a non-empty key and non-empty text; "
                f"got key={key!r}, text={'present' if has_text else 'absent'}")
        if has_text and not resolvable:
            raise ValueError("text is present but resolvable=False; the flag contradicts the payload")
        return values


# ── the per-graha verdict ───────────────────────────────────────────────────

class GrahaPratiphala(_Strict):
    graha: Graha
    # PF-007. Optional, because a certified chart legitimately carries no D1
    # dignity for a node in an ordinary sign. Non-optional made the real route
    # return 500 for such charts while the policy already resolved them
    # correctly — the contract was narrower than the doctrine it encoded.
    d1_dignity: Optional[Dignity] = None
    # None for a node outside Taurus/Scorpio. Optional because ABSENT and WEAK
    # are different facts and must not be collapsed.
    d9_dignity: Optional[Dignity] = None
    d1_sub_tier: SubTier
    d9_sub_tier: SubTier
    is_vargottama: bool = False

    governing_state: GoverningLabel
    governing_state_sa: str
    basis: StrictStr = Field(min_length=1)
    corpus: CorpusRef
    evidence: PratiphalaEvidence

    @root_validator(skip_on_failure=True)
    def _derived_fields_match_the_dignities(cls, values):
        """PF-006. RECOMPUTE, do not merely cross-check.

        Every derived field is regenerated from the two declared dignities using
        the SAME functions the resolver calls, then compared. A consistently
        false reading — Friend/Friend presented as Rikt with matching ranks,
        strengths, tiers and labels — was internally coherent and therefore
        passed. Coherence is not correctness; only the dignities are input.
        """
        d1, d9 = values.get("d1_dignity"), values.get("d9_dignity")
        ev = values.get("evidence")
        graha = values.get("graha")
        if ev is None or graha is None:
            return values

        # Absence is a node privilege. Skipping the validator for a None D1 —
        # the obvious shortcut — would have left every other derived field
        # unchecked on exactly the payloads this fix exists to admit.
        for side, value in (("D1", d1), ("D9", d9)):
            if value is None and graha not in DIGNITY_OPTIONAL_FOR:
                raise ValueError(
                    f"{graha.value} carries no {side} dignity; only Rahu and Ketu "
                    f"may lack one, so this is a broken chart rather than an "
                    f"unknown reading")

        d1_rank = rank_of(d1)          # raises for Great Friend / Great Enemy
        d9_rank = rank_of(d9)
        quadrant = quadrant_of(d1_rank, d9_rank)
        governing = governing_of(quadrant, bool(values.get("is_vargottama")))

        expected = {
            "evidence.d1_rank": (ev.d1_rank, d1_rank),
            "evidence.d9_rank": (ev.d9_rank, d9_rank),
            "evidence.d1_strength": (ev.d1_strength, strength_of(d1_rank)),
            "evidence.d9_strength": (ev.d9_strength, strength_of(d9_rank)),
            "evidence.strong_at_rank": (ev.strong_at_rank, STRONG_AT),
            "evidence.underlying_state": (ev.underlying_state, quadrant),
            "evidence.underlying_state_sa": (ev.underlying_state_sa, STATE_SA[quadrant]),
            "d1_sub_tier": (values.get("d1_sub_tier"), sub_tier_of(d1_rank)),
            "d9_sub_tier": (values.get("d9_sub_tier"), sub_tier_of(d9_rank)),
            "governing_state": (values.get("governing_state"), governing),
            "governing_state_sa": (values.get("governing_state_sa"), governing_sa_of(governing)),
        }
        wrong = [f"{k}={got!r} but the dignities give {want!r}"
                 for k, (got, want) in expected.items() if got != want]
        corpus = values.get("corpus")
        if corpus is not None:
            want_key = graha_corpus_key_of(values["graha"], governing)
            if corpus.key != want_key:
                wrong.append(f"corpus.key={corpus.key!r} but the dignities give {want_key!r}")
        if wrong:
            raise ValueError(
                f"the reading contradicts its own dignities "
                f"(D1 {d1.value if d1 else None}, D9 {d9.value if d9 else None}): "
                + "; ".join(wrong))
        return values

    @root_validator(skip_on_failure=True)
    def _unknown_and_sovereign_invariants(cls, values):
        gov = values.get("governing_state")
        d9 = values.get("d9_dignity")
        corpus = values.get("corpus")
        ev = values.get("evidence")

        # PF-001. This validator PERMITTED Sovereign with an absent D9 dignity —
        # the defect was not an omission here, it was written in as an allowance.
        # Absent D9 admits exactly one verdict.
        # PF-007. EITHER required dignity being absent forces UNKNOWN, not just
        # D9. The rule was written when only D9 could be missing.
        d1 = values.get("d1_dignity")
        if (d1 is None or d9 is None) and gov is not GoverningLabel.UNKNOWN:
            missing = "D1" if d1 is None else "D9"
            raise ValueError(
                f"no certified {missing} dignity, so the verdict must be UNKNOWN, "
                f"not {gov.value}; absent dignity outranks the vargottama override")
        if gov is GoverningLabel.UNKNOWN:
            if corpus is not None and (corpus.text or corpus.key):
                raise ValueError("UNKNOWN carries no corpus key and no corpus text")
            if ev is not None and ev.underlying_state is not PratiphalaState.UNKNOWN:
                raise ValueError("UNKNOWN must not record a quadrant as its underlying state")
        if gov is GoverningLabel.SOVEREIGN:
            if not values.get("is_vargottama"):
                raise ValueError("Sovereign is reachable only through vargottama")
            if d1 is None or d9 is None:
                raise ValueError(
                    "Sovereign asserts that a quadrant does not govern; with a "
                    "missing certified dignity there is no quadrant to override")
            if ev is not None and not ev.sovereign_override_applied:
                raise ValueError("Sovereign must record that the override was applied")
        if gov is not GoverningLabel.SOVEREIGN and ev is not None and ev.sovereign_override_applied:
            raise ValueError("the override flag is set but Sovereign does not govern")
        return values


# ── house-lord overlays, keyed by HOUSE ─────────────────────────────────────

class HouseLordOverlay(_Strict):
    """One overlay per OWNED HOUSE, never one per graha.

    Venus on a Libra lagna owns H1 and H8 and produces two overlays with the
    same graha and different identity. Keying on the graha alone would silently
    merge them and lose one house's reading entirely.
    """
    house: int = Field(ge=1, le=12)
    house_name: StrictStr = Field(min_length=1)
    lord: Graha
    overlay_key: StrictStr        # "H1:Venus" — house first, because house is the identity
    # PF-004. The graha verdict is SHARED EVIDENCE, not the overlay's reading.
    # Venus lords H1 and H8 on a Libra lagna; the planetary verdict is one fact
    # about Venus, but what it means for the body and for longevity are two
    # readings. Carrying only the shared verdict made the two overlays identical
    # apart from their labels.
    verdict: GrahaPratiphala
    basis: StrictStr = Field(min_length=1)
    corpus: CorpusRef

    @validator("lord")
    def _lord_owns_a_rasi(cls, v):
        """PF-008. A node cannot lord a house, whatever else the payload says.

        Checked on the FIELD, so it fires before any of the key, verdict or
        corpus reasoning below and cannot be satisfied by making the rest of the
        overlay internally consistent. An H1:Rahu overlay carrying the genuine
        Rahu UNKNOWN verdict and an empty corpus is coherent in every other
        respect and still impossible.
        """
        if v not in CLASSICAL_HOUSE_LORDS:
            raise ValueError(
                f"{v.value} owns no rāśi in the Parāśarī scheme and cannot lord a "
                f"house; house lords are "
                f"{sorted(g.value for g in CLASSICAL_HOUSE_LORDS)}")
        return v

    @root_validator(skip_on_failure=True)
    def _key_is_house_scoped(cls, values):
        h, lord, key = values.get("house"), values.get("lord"), values.get("overlay_key")
        if h is None or lord is None:
            return values
        expected = f"H{h}:{lord.value}"
        if key != expected:
            raise ValueError(f"overlay_key must be {expected!r}, got {key!r}")
        name = values.get("house_name")
        if name != HOUSE_NAMES[h]:
            raise ValueError(f"house_name for house {h} must be {HOUSE_NAMES[h]!r}, got {name!r}")
        # PF-005. THE KEY IS BOUND EXACTLY, not merely tested for a house token.
        # Containment accepted the right house carrying the wrong graha, the
        # wrong state, or arbitrary text — a card that looks correct while
        # displaying another graha's prose. Every component is reconstructed
        # from the overlay's own declared identity and compared whole.
        verdict = values.get("verdict")
        if verdict is None:
            return values

        # The overlay and the verdict it shares must describe the same graha.
        # Without this the key can be self-consistent and still wrong, because
        # the governing state it names comes from a different graha's reading.
        if verdict.graha is not lord:
            raise ValueError(
                f"overlay declares lord {lord.value} but carries a verdict for "
                f"{verdict.graha.value}; the shared verdict must be the lord's own")

        corpus = values.get("corpus")
        if corpus is None:
            return values
        governing = verdict.governing_state
        if governing is GoverningLabel.UNKNOWN:
            if corpus.key or corpus.text or corpus.resolvable:
                raise ValueError(
                    "an UNKNOWN overlay carries no house corpus identity: "
                    f"got key={corpus.key!r}")
            return values
        expected_key = f"PRATIPHALA-H{h}-{lord.value}-{governing.value}"
        if corpus.key != expected_key:
            raise ValueError(
                f"house corpus key must be exactly {expected_key!r}, got "
                f"{corpus.key!r}; house, lord and governing state are all bound")
        return values


# ── response ────────────────────────────────────────────────────────────────

class PratiphalaPolicy(_Strict):
    """An IMMUTABLE declaration of the rules the shared policy actually uses.

    PF-010. These were overridable defaults, so a response could publish
    strong_at_rank=2 while every reading in it had been computed at 3 — a policy
    block describing a system that does not exist. Each field is now locked to
    the constant the policy functions read, and a mismatch is refused rather
    than accepted as an override.

    The unknown_rule string also still said "absent D9", which PF-007 had
    already superseded. A rule statement nobody validates goes stale silently.
    """
    contract_version: StrictStr = CONTRACT_VERSION
    strong_at_rank: int = STRONG_AT
    scale: StrictStr = SCALE_DESCRIPTION
    sovereign_rule: StrictStr = SOVEREIGN_RULE
    unknown_rule: StrictStr = UNKNOWN_RULE

    @root_validator(skip_on_failure=True)
    def _locked_to_the_shared_policy(cls, values):
        locked = {
            "contract_version": CONTRACT_VERSION,
            "strong_at_rank": STRONG_AT,
            "scale": SCALE_DESCRIPTION,
            "sovereign_rule": SOVEREIGN_RULE,
            "unknown_rule": UNKNOWN_RULE,
        }
        wrong = []
        for name, want in locked.items():
            got = values.get(name)
            # `True == 1` in Python, so strong_at_rank=True would pass a bare
            # equality check while publishing a boolean as the threshold.
            if isinstance(want, int) and not isinstance(want, bool):
                if isinstance(got, bool) or got != want:
                    wrong.append(f"{name}={got!r}")
                continue
            if got != want:
                wrong.append(f"{name}={got!r}")
        if wrong:
            raise ValueError(
                "the policy block must declare the rules the shared policy "
                "actually uses; these do not: " + ", ".join(wrong))
        return values


class PratiphalaPrepareResponse(_Strict):
    chart_token: StrictStr = Field(min_length=8, max_length=256)
    # PF-009. Published so the lordship claim is CHECKABLE. Without it the
    # response asserted "Venus lords H1" with nothing in the payload able to
    # confirm or refute it — the same defect class as a derived verdict whose
    # inputs are absent.
    lagna_sign_index: int = Field(ge=0, le=11)
    policy: PratiphalaPolicy = Field(default_factory=PratiphalaPolicy)
    grahas: List[GrahaPratiphala] = Field(min_items=9, max_items=9)
    house_lord_overlays: List[HouseLordOverlay] = Field(min_items=12, max_items=12)

    @root_validator(skip_on_failure=True)
    def _complete_and_house_keyed(cls, values):
        grahas = values.get("grahas") or []
        overlays = values.get("house_lord_overlays") or []
        if {g.graha for g in grahas} != set(Graha):
            raise ValueError("grahas must cover exactly the nine grahas")
        # PF-005. One graha, one verdict, across the whole response. An overlay
        # carrying a DIFFERENT verdict for the same lord would put two readings
        # of one graha on one screen, which is the defect this whole programme
        # exists to remove.
        top = {g.graha: g for g in grahas}
        for o in overlays:
            shared = top.get(o.lord)
            if shared is not None and o.verdict.dict() != shared.dict():
                raise ValueError(
                    f"overlay {o.overlay_key} carries a verdict for {o.lord.value} "
                    f"that differs from the top-level {o.lord.value} verdict; "
                    f"one graha has one reading")
        houses = [o.house for o in overlays]
        if sorted(houses) != list(range(1, 13)):
            raise ValueError("house_lord_overlays must cover houses 1..12 exactly once each")
        if len({o.overlay_key for o in overlays}) != len(overlays):
            raise ValueError("overlay_key must be unique per house")
        # PF-009. Every declared lord is recomputed from the response's OWN
        # lagna. A locally self-consistent overlay — matching key, matching
        # verdict, classical lord — is still wrong if that graha does not rule
        # that house for this chart.
        lagna = values.get("lagna_sign_index")
        if lagna is not None:
            for o in overlays:
                want = expected_lord_of(lagna, o.house)
                if o.lord is not want:
                    sign_index = (lagna + o.house - 1) % 12
                    raise ValueError(
                        f"H{o.house} declares lord {o.lord.value}, but with lagna "
                        f"sign_index {lagna} that house falls in sign_index "
                        f"{sign_index}, ruled by {want.value}")
        return values
