"""d12_synthesis_contract.py — the bounded prose-composition contract.

D12-006A. The provider is a PROSE COMPOSER and never an astrologer. It receives
already-certified atoms and returns structured fields; it cannot change a house,
dignity, parent speaker, classification, release result, tension winner or
instruction, because none of those is ever read back from its output.

Two structural defences, not one:

  * SHAPE — §11 returns {tension_key, body}; §13 returns exactly eight named
    beats. Asking for one unconstrained essay and hoping the model obeyed is
    what this replaces.
  * CLAIMS — a rejection battery over the generated prose only. The frozen page
    legitimately explains Maraka and past-life residue in order to LIMIT them,
    so the scan runs against provider output and never against the locked
    glossary or safety copy.

The final §13 practice sentence is INSERTED BY THE SERVER from the winning
FR-003 corpus. The provider is not trusted to reproduce it, and a beat that
disagrees with the corpus is rejected rather than corrected.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Mapping, Optional, Tuple

from pydantic import BaseModel, Extra, StrictStr, validator

from d12_instruction_corpus import TENSION_KEYS, instruction_text

SYNTHESIS_CONTRACT_VERSION = "d12-synthesis-1.0"

# §13 · the frozen beat order.
BEATS: Tuple[str, ...] = ("stance", "father", "mother", "unpaid", "handshake",
                          "ketu_pull", "tension", "practice")

SECTION_11_MAX_WORDS = 90
SECTION_13_MIN_WORDS = 220
SECTION_13_MAX_WORDS = 280

# The rejection battery. Each entry is (pattern, what it would smuggle in).
BANNED_CLAIMS: Tuple[Tuple[str, str], ...] = (
    (r"\bmaraka\b", "a Maraka finding"),
    (r"\bdiagnos", "a diagnosis"),
    (r"\b(illness|disease|ill health|health window)\b", "an illness claim"),
    (r"\b(dies|death|dying|fatal|mortality)\b", "a death claim"),
    # CORR-01 · the QA bypasses. The previous family matched only the abstract
    # nouns, so ordinary clinical and euphemistic wording walked straight
    # through it. These are the words a real draft actually uses.
    (r"\b(cancer|tumou?r|stroke|dementia|diabet|cardiac|terminal)\b",
     "a disease claim"),
    (r"\b(unwell|frail|sick|ailing|infirm|invalid|bedridden)\b",
     "a health claim"),
    (r"\b(pass(es|ed)? away|passing away|will not survive|final years|"
     r"deathbed|end of (his|her|their) life)\b", "a death claim"),
    (r"\b(develop|contract|suffer from|be diagnosed with)\b[^.]{0,40}"
     r"\b(condition|disease|illness|cancer)\b", "a prognosis"),
    # A bounded parent-biography prohibition. Medical vocabulary alone was never
    # the whole of the harm: an invented employment, residence or identity is a
    # fabricated life history about a real person.
    (r"\b(father|mother|parent)\b[^.]{0,60}\b(was|were|had been|worked as|"
     r"served as|employed|职)\b[^.]{0,40}\b(officer|official|teacher|doctor|"
     r"lawyer|engineer|soldier|clerk|merchant|farmer|businessman|professor)\b",
     "an invented parental employment"),
    (r"\b(father|mother|parent)\b[^.]{0,60}\b(lived|moved|emigrated|settled|"
     r"was born)\b[^.]{0,30}\b(abroad|overseas|in another|another country|"
     r"far from)\b", "an invented parental residence"),
    (r"\b(your|his|her) (father|mother) was a\b", "an invented parental identity"),
    (r"\bshraddha\b", "a rite prescription"),
    (r"\bmantra\b", "a mantra prescription"),
    (r"\b(remedy|remedies|remedial|propitiat)", "a remedy prescription"),
    (r"\b(past[- ]life|previous birth|incarnation|reincarnat)",
     "a past-life identity claim"),
    (r"\bwho you were\b", "a past-life identity claim"),
    (r"\b(abandon|renounce|leave behind) (your |the )?(parents|family)\b",
     "abandoning parents as liberation"),
    (r"\b(cancel|override|overrides|negate|nullif)\w*\b[^.]{0,40}\b(d10|work|"
     r"career|vocation|standing|profession)", "D12 cancelling D10"),
    (r"\bsoul (will |shall )?(finally )?(rest|be at rest)", "a soul eulogy"),
    (r"\byour soul\b", "a soul eulogy"),
)


class _Closed(BaseModel):
    class Config:
        extra = Extra.forbid
        allow_mutation = False


class SynthesisRejected(ValueError):
    """Provider output that does not reach the customer. Never repaired."""


def _word_count(text: str) -> int:
    return len(text.split())


def scan_claims(text: str) -> List[str]:
    """Every banned claim the generated prose introduces. Empty is clean."""
    low = text.lower()
    return sorted({why for pattern, why in BANNED_CLAIMS
                   if re.search(pattern, low)})


# ─────────────────────────────────────────────────────────────────────────────
# CORR-01 · THE GROUNDING RULE
#
# A claim scan catches what prose must never say. It does not catch prose that
# says something certified but WRONG — "the 4th lord is Supported" when the
# certified row reads Loaded. That is a fabricated astrological fact wearing
# entirely permitted words, and it needs a different check.
#
# So: reserved tokens may appear only consistently with the atoms for that beat.
# The rule is deliberately one-directional — silence is always allowed, and only
# an explicit CONFLICT is rejected — because a composer that omits a fact has
# written thin prose, while one that contradicts a fact has invented astrology.
# ─────────────────────────────────────────────────────────────────────────────

GRAHAS: Tuple[str, ...] = ("Sun", "Moon", "Mars", "Mercury", "Jupiter",
                           "Venus", "Saturn", "Rahu", "Ketu")
SIGNS: Tuple[str, ...] = ("Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
                          "Libra", "Scorpio", "Sagittarius", "Capricorn",
                          "Aquarius", "Pisces")
DIGNITIES: Tuple[str, ...] = ("Uchcha", "Sva", "Mitra", "Sama", "Shatru",
                              "Neecha", "Ungraded")
CLASSES: Tuple[str, ...] = ("Supported", "Loaded", "Redirected")


def _mentioned(text: str, tokens) -> set:
    return {t for t in tokens if re.search(rf"\b{re.escape(t)}\b", text, re.I)}


# CORR-03 · HARD CLAUSE BOUNDARIES ONLY.
#
# Boundaries are sentence terminators, semicolons/colons, and contrast
# conjunctions — the places where a genuinely new subject can begin. Commas and
# "and" are NOT boundaries: they do not start a new subject, and treating them
# as one severed a subject from its own facts.
_SEGMENT_SPLIT = re.compile(r"[.;:!?]|\bwhile\b|\bwhereas\b|\bbut\b", re.I)


def _segments(text: str) -> List[str]:
    return [c for c in _SEGMENT_SPLIT.split(text) if c.strip()]


# ─────────────────────────────────────────────────────────────────────────────
# CORR-04 · THE NORMALIZATION LAYER
#
# The firewall previously recognised only canonical tokens — H6, Neecha,
# Scorpio — so ordinary English carrying exactly the same claim walked past it.
# "Moon is exalted" and "Moon is Uchcha" are the SAME assertion, and only one of
# them was being checked.
#
# So there is now one normalization step in front of the grounding comparison:
#
#     generated phrase -> canonical technical assertion -> certified anchor
#                      -> compare with atoms
#
# and a phrase that LOOKS technical but cannot be brought safely to canonical
# form is REJECTED rather than skipped. That is the whole point: a growing list
# of bad sentences would always be one paraphrase behind.
# ─────────────────────────────────────────────────────────────────────────────

_ORDINALS = {"first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5,
             "sixth": 6, "seventh": 7, "eighth": 8, "ninth": 9, "tenth": 10,
             "eleventh": 11, "twelfth": 12}
_ORD_WORDS = "|".join(_ORDINALS)

# Dignity synonyms. The canonical value is what gets compared with the atom.
_DIGNITY_ALIASES: Tuple[Tuple[str, str], ...] = (
    (r"\bUchcha\b", "Uchcha"),
    (r"\bexalt(?:ed|ation)\b", "Uchcha"),
    (r"\bSva\b", "Sva"),
    (r"\bin its own sign\b|\bown sign\b", "Sva"),
    (r"\bMitra\b", "Mitra"),
    (r"\bfriendly sign\b", "Mitra"),
    (r"\bSama\b", "Sama"),
    (r"\bneutral(?:\s+sign)?\b", "Sama"),
    (r"\bShatru\b", "Shatru"),
    (r"\benemy sign\b", "Shatru"),
    (r"\bNeecha\b", "Neecha"),
    (r"\bdebilitat(?:ed|ion)\b", "Neecha"),
    (r"\bUngraded\b", "Ungraded"),
)

# A generic strength verdict. The synthesis provider has no certified strength
# fact to publish, in any wording, so every one of these rejects.
_STRENGTH = re.compile(
    r"\b(strong|strongest|stronger|strengthened|weak|weakest|weaker|weakened|"
    r"powerful|potent|feeble|dignified|undignified)\b", re.I)

# LORDSHIP is a different claim from PLACEMENT. "rules the fourth house" asserts
# an identity; "is in the fourth house" asserts a position. The house number in a
# lordship phrase must never be read as a placement, so these phrases are
# consumed out of the segment before houses are extracted.
_LORDSHIP_PATTERNS: Tuple[str, ...] = (
    rf"\b(?:the\s+)?(?:H)?(\d{{1,2}}|{_ORD_WORDS})(?:st|nd|rd|th)?[-\s]+house\s+(?:lord|ruler)\b",
    rf"\b(?:lord|ruler)\s+of\s+the\s+(?:H)?(\d{{1,2}}|{_ORD_WORDS})(?:st|nd|rd|th)?\s+house\b",
    rf"\brules?\s+the\s+(?:H)?(\d{{1,2}}|{_ORD_WORDS})(?:st|nd|rd|th)?\s+house\b",
    rf"\b(?:the\s+)?(?:H)?(\d{{1,2}}|{_ORD_WORDS})(?:st|nd|rd|th)?\s+lord\b",
)

_HOUSE_PATTERNS: Tuple[str, ...] = (
    r"\bH(\d{1,2})\b",
    rf"\b(\d{{1,2}})(?:st|nd|rd|th)\s+house\b",
    rf"\b({_ORD_WORDS})\s+house\b",
    r"\bhouse\s+(\d{1,2})\b",
    rf"\bin\s+the\s+(\d{{1,2}})(?:st|nd|rd|th)\b",
    rf"\bin\s+the\s+({_ORD_WORDS})\b",
)

# A phrase that signals a technical relation even when nothing normalizes.
_TECHNICAL_CUE = re.compile(
    r"\b(lord|ruler|rules?|exalt\w*|debilitat\w*|own sign|friendly sign|"
    r"enemy sign|neutral sign|ungraded|vargottama|dignity|dignities|"
    r"Supported|Loaded|Redirected)\b", re.I)


def _house_number(token: str) -> Optional[int]:
    token = token.lower()
    if token in _ORDINALS:
        return _ORDINALS[token]
    if token.isdigit():
        n = int(token)
        return n if 1 <= n <= 12 else None
    return None


def normalize_segment(segment: str) -> Dict[str, Any]:
    """One canonical technical assertion from an ordinary English segment.

    Returns the houses, signs, dignities, classifications and lordship claims
    the segment asserts, plus whether it makes a generic strength claim and
    whether it carries an unresolved technical cue.
    """
    working = segment

    lordships: set = set()
    unresolved_lordship = False
    for pattern in _LORDSHIP_PATTERNS:
        for m in re.finditer(pattern, working, re.I):
            n = _house_number(m.group(1))
            if n is None:
                unresolved_lordship = True
            else:
                lordships.add(n)
        # consumed, so the house number is never re-read as a placement
        working = re.sub(pattern, " ", working, flags=re.I)

    houses: set = set()
    for pattern in _HOUSE_PATTERNS:
        for m in re.finditer(pattern, working, re.I):
            n = _house_number(m.group(1))
            if n is not None:
                houses.add(n)

    dignities: set = set()
    for pattern, canonical in _DIGNITY_ALIASES:
        if re.search(pattern, working, re.I):
            dignities.add(canonical)

    return {"houses": houses,
            "signs": _mentioned(working, SIGNS),
            "dignities": dignities,
            "classes": _mentioned(working, CLASSES),
            "lordships": lordships,
            "strength": bool(_STRENGTH.search(working)),
            "unresolved_lordship": unresolved_lordship,
            "cue": bool(_TECHNICAL_CUE.search(working))}


ROLE_BY_HOUSE = {4: "D1 4th lord", 9: "D1 9th lord", 12: "D1 12th lord",
                 6: "H6 lord"}

_LAGNESH = re.compile(r"\bLagnesh\b", re.I)
_LAGNA = re.compile(r"\bD12 Lagna\b|\bLagna\b(?!sh)", re.I)


def check_grounding(text: str, atoms: Mapping[str, Any]) -> List[str]:
    """Reserved facts the prose asserts that the certified atoms contradict, or
    asserts with no certified subject to attach them to.

    CORR-04 · every technical claim is NORMALIZED first, so ordinary English
    reaches the same comparison as canonical vocabulary: "Moon is exalted" is
    checked exactly as "Moon is Uchcha" is.

    NO SILENT TECHNICAL ESCAPE. A segment that carries a technical cue but
    cannot be brought unambiguously to canonical form is rejected, not skipped.

    ROLES ARE IDENTITIES. "rules the fourth house" and "is in the fourth house"
    are different claims and are normalized separately; a role's identity is
    part of what it asserts.

    Silence and ordinary connective prose remain allowed.
    """
    problems: List[str] = []
    chart = atoms.get("chart") or {}
    grahas = chart.get("grahas") or {}
    roles = atoms.get("roles") or {}
    by_house = {r["d1_lord_of"]: r["classification"]
                for r in atoms.get("handshake", [])}
    role_class = {f"D1 {h}th lord": c for h, c in by_house.items()}

    for segment in _segments(text):
        norm = normalize_segment(segment)
        named = _mentioned(segment, GRAHAS) & set(grahas)

        # ── generic strength: never certified, in any wording ───────────────
        if norm["strength"]:
            problems.append(
                f"asserts a generic strength verdict, which the atoms never "
                f"certify: {segment.strip()!r}")
            continue

        if norm["unresolved_lordship"]:
            problems.append(
                f"makes a lordship claim that cannot be resolved to a certified "
                f"role: {segment.strip()!r}")
            continue

        # ── role identity, before anchors are counted ───────────────────────
        roles_named: List[str] = []
        for n in norm["lordships"]:
            role = ROLE_BY_HOUSE.get(n)
            if role and role in roles:
                roles_named.append(role)
            else:
                problems.append(
                    f"claims a lordship for H{n}, which the certified role "
                    f"registry does not cover")
        if _LAGNESH.search(segment) and "Lagnesh" in roles:
            roles_named.append("Lagnesh")
        lagna_named = bool(_LAGNA.search(segment)) and "D12 Lagna" in roles

        identity_conflict = False
        for role in roles_named:
            certified_graha = roles[role].get("graha")
            if certified_graha and named and certified_graha not in named:
                problems.append(
                    f"names the {role} as {', '.join(sorted(named))} where the "
                    f"certified {role} is {certified_graha}")
                identity_conflict = True
        if identity_conflict:
            continue

        technical = bool(norm["houses"] or norm["signs"] or norm["dignities"]
                         or norm["classes"])
        if not technical:
            # A bare, correct role identity ("Mercury is the ninth lord") is a
            # complete and grounded assertion; it needs no further facts.
            if roles_named or lagna_named:
                continue
            if norm["cue"]:
                problems.append(
                    f"makes a technical assertion that cannot be normalized "
                    f"and grounded: {segment.strip()!r}")
            continue

        anchors = set()
        for role in roles_named:
            graha = roles[role].get("graha")
            anchors.add(("graha", graha) if graha else ("lagna", None))
        if lagna_named and not roles_named:
            anchors.add(("lagna", None))
        for g in named:
            anchors.add(("graha", g))

        if not anchors:
            problems.append(
                f"asserts technical facts with no certified subject to attach "
                f"them to: {segment.strip()!r}")
            continue
        if len(anchors) > 1:
            problems.append(
                f"attaches technical facts ambiguously to more than one "
                f"certified subject: {segment.strip()!r}")
            continue

        kind, subject = next(iter(anchors))
        if kind == "lagna":
            certified_sign = chart.get("d12_lagna_sign")
            for sign in norm["signs"]:
                if sign != certified_sign:
                    problems.append(
                        f"claims the D12 Lagna is {sign} where the certified "
                        f"Lagna is {certified_sign}")
            for house in norm["houses"]:
                problems.append(
                    f"attaches H{house} to the D12 Lagna, which the atoms do "
                    f"not certify a house for")
            for dignity in norm["dignities"]:
                problems.append(
                    f"attaches the dignity {dignity} to the D12 Lagna, which "
                    f"the atoms do not certify one for")
            continue

        certified = grahas[subject]
        for house in norm["houses"]:
            if house != certified["house"]:
                problems.append(
                    f"places {subject} in H{house} where the certified house "
                    f"is H{certified['house']}")
        for sign in norm["signs"]:
            if sign != certified["sign"]:
                problems.append(
                    f"places {subject} in {sign} where the certified sign is "
                    f"{certified['sign']}")
        for dignity in norm["dignities"]:
            if dignity != certified["dignity"]:
                problems.append(
                    f"gives {subject} the dignity {dignity} where the certified "
                    f"dignity is {certified['dignity']}")
        if norm["classes"]:
            allowed = {role_class[r] for r in roles_named if r in role_class}
            if not allowed:
                allowed = {c for role, c in role_class.items()
                           if roles.get(role, {}).get("graha") == subject}
            for claimed in norm["classes"]:
                if allowed and claimed not in allowed:
                    problems.append(
                        f"claims {subject} is {claimed} where the certified "
                        f"classification is {', '.join(sorted(allowed))}")
                elif not allowed:
                    problems.append(
                        f"attaches the classification {claimed} to {subject}, "
                        f"which the §10 grid does not certify one for")

    # Tension titles: any explicit title must be the deterministic winner.
    from d12_instruction_corpus import TENSION_TITLE
    winner_title = atoms.get("tension", {}).get("title")
    for key, title in TENSION_TITLE.items():
        if title.lower() in text.lower() and title != winner_title:
            problems.append(f"names the unselected tension {title!r}")

    return sorted(set(problems))


class Section11Draft(_Closed):
    """What the provider returns for §11: the key it was given, and prose."""
    tension_key: StrictStr
    body: StrictStr

    @validator("tension_key")
    def _a_real_tension(cls, v):
        if v not in TENSION_KEYS:
            raise ValueError(f"unknown tension key {v!r}")
        return v

    @validator("body")
    def _within_ninety_words(cls, v):
        n = _word_count(v)
        if n == 0:
            raise ValueError("§11 body is empty")
        if n > SECTION_11_MAX_WORDS:
            raise ValueError(
                f"§11 is limited to {SECTION_11_MAX_WORDS} words; got {n}")
        return v

    @validator("body")
    def _no_banned_claim(cls, v):
        found = scan_claims(v)
        if found:
            raise ValueError(f"§11 prose introduces {', '.join(found)}")
        return v

    @validator("body")
    def _no_second_tension(cls, v):
        from d12_instruction_corpus import TENSION_TITLE
        hits = [k for k, title in TENSION_TITLE.items() if title.lower() in v.lower()]
        if len(hits) > 1:
            raise ValueError("§11 must name at most the one selected tension")
        return v


class Beat(_Closed):
    name: StrictStr
    text: StrictStr

    @validator("name")
    def _a_frozen_beat(cls, v):
        if v not in BEATS:
            raise ValueError(f"{v!r} is not one of the eight frozen beats")
        return v

    @validator("text")
    def _not_empty_and_no_heading(cls, v):
        if not v.strip():
            raise ValueError("a beat may not be empty")
        if v.lstrip().startswith("#") or "\n\n" in v:
            raise ValueError("a beat is prose, not a card with a heading")
        return v


class Section13Draft(_Closed):
    """Exactly eight ordered beats. The SERVER joins them into one essay."""
    beats: List[Beat]

    @validator("beats")
    def _exactly_the_eight_in_order(cls, v):
        if tuple(b.name for b in v) != BEATS:
            raise ValueError(
                f"§13 needs exactly the eight beats in the order {BEATS}, got "
                f"{[b.name for b in v]}")
        return v

    @validator("beats")
    def _no_banned_claim_in_any_beat(cls, v):
        found = sorted({why for b in v for why in scan_claims(b.text)})
        if found:
            raise ValueError(f"§13 prose introduces {', '.join(found)}")
        return v

    def join(self) -> str:
        """One joined reading, not eight cards."""
        return " ".join(b.text.strip() for b in self.beats)


class SynthesisResult(_Closed):
    """The validated, server-assembled prose."""
    synthesis_version: StrictStr = SYNTHESIS_CONTRACT_VERSION
    tension_key: StrictStr
    section11_body: StrictStr
    section11_words: int
    practice_sentence: StrictStr
    section13_essay: StrictStr
    section13_words: int
    beat_order: List[StrictStr]

    @validator("section11_words")
    def _s11_budget(cls, v, values):
        body = values.get("section11_body")
        if body is not None and v != _word_count(body):
            raise ValueError("section11_words must be the body's own count")
        if v > SECTION_11_MAX_WORDS:
            raise ValueError(f"§11 exceeds {SECTION_11_MAX_WORDS} words")
        return v

    @validator("section13_words")
    def _s13_budget(cls, v, values):
        essay = values.get("section13_essay")
        if essay is not None and v != _word_count(essay):
            raise ValueError("section13_words must be the essay's own count")
        if not SECTION_13_MIN_WORDS <= v <= SECTION_13_MAX_WORDS:
            raise ValueError(
                f"§13 must be {SECTION_13_MIN_WORDS}-{SECTION_13_MAX_WORDS} "
                f"words inclusive; got {v}")
        return v

    @validator("beat_order")
    def _frozen_order(cls, v):
        if tuple(v) != BEATS:
            raise ValueError(f"§13 beat order must be {BEATS}")
        return v

    @validator("practice_sentence")
    def _the_winning_corpus_practise(cls, v, values):
        key = values.get("tension_key")
        if key is None:
            return v
        if v != instruction_text(key, "practise"):
            raise ValueError(
                "the §13 practice must be the exact winning FR-003 Practise "
                "sentence, not a provider paraphrase")
        return v

    @validator("section13_essay")
    def _one_essay(cls, v):
        if "\n\n" in v or v.lstrip().startswith("#"):
            raise ValueError("§13 is one joined essay with no headings")
        return v

    @validator("section13_essay")
    def _ends_on_the_practice(cls, v, values):
        """CORR-01 · endswith, not substring presence. The practice is the CLOSE
        of the reading; a sentence buried mid-essay is not that."""
        practice = values.get("practice_sentence")
        if practice and not v.rstrip().endswith(practice):
            raise ValueError("the §13 essay must END on the practice sentence")
        return v
