"""d12_corpus.py — Phalit.ai D12 Dvādaśāṁśa deterministic corpus, Sections 5-9.

D12-004. Every customer-visible string in this module is a verbatim transcription
of a Founder-ratified artifact. Nothing here is generated, paraphrased,
shortened, beautified or provider-sourced, and nothing here may be edited to
suit a selector: if a selector cannot resolve a state, that is an engineering
binding gap to report, not a licence to write a new sentence.

SOURCE AUTHORITY, per string family:
  §5 bespoke cells, fallback template and its four substitution tables
  §6 bespoke cells, fallback template and its four substitution tables
  §7 three specific cells and the mandatory baseline
  §8 the seven domain-constant clauses
      -> D12_FR_006A_LOCKED.md
         2b5fa19a0ab2f7561a781a702a2fe2403637fc5f0bd1d022bf9efe90ebc055af
  §9 the ten authoritative Devatā glosses, and the pair-name rule
      -> D12_FR_003_005_LOCKED.md
         d9a1fd8a5f84f6724568c929059d109ce71293c0f7cef68e43cea93d496be9ef

MECHANICAL LEGACY TABLES (§9) are ported byte-exact from the audited production
frontend newphalit_fixed.html
(6e446c03b3eaef33c27a5400f4dfb0892a14c452f0f7456c28d287095090b573) at lines
25046-25052 — `D12_DEITIES`, `D12_HIDDEN`, `D12_MEANING`. The frozen
specification explicitly directs that this one mechanical surface be retained.
Its neighbouring interpretive tables in that file — `D12_PARENT_SIG`,
`D12_MOKSHA_SIG`, `D12_DEITY_DESC` — are CONDEMNED EVIDENCE and are deliberately
NOT ported: they carry the maraka, parental-health, Shraddha-prescription and
past-life-identity claims the frozen contract forbids.

The element authority is `d9_r2_doctrine.ELEMENT`, the existing certified
sign-element table in this parent. A second zodiac-element taxonomy is not
created here.
"""

from __future__ import annotations

from typing import Dict, Mapping, Tuple

from d9_r2_doctrine import ELEMENT as SIGN_ELEMENT   # the certified authority

__all__ = [
    "CORPUS_VERSION", "HOUSE_CATEGORY", "DIGNITY_BUCKET", "ELEMENTS",
    "SIGN_ELEMENT", "S5_BESPOKE", "S5_TEMPLATE", "S5_ELEMENT_MODE",
    "S5_ELEMENT_RISK", "S5_DIGNITY_DESCRIPTOR", "S5_CATEGORY_TOKEN",
    "SPEAKER_FAMILIES", "S6_BESPOKE", "S6_TEMPLATE", "S6_CATEGORY_LANGUAGE",
    "S6_DIGNITY_LOAD", "S6_ELEMENT_TONE", "S7_CELLS", "S7_BASELINE",
    "S8_DOMAINS", "S8_VISIBLE_LABEL", "S8_CLAUSE", "S8_TUPLES",
    "text_for_key", "all_corpus_keys",
    "D12_DEITIES", "D12_HIDDEN", "D12_MEANING", "DEVATA_GLOSS",
    "STRUCTURAL_CLASSES", "CorpusKeyError",
]

CORPUS_VERSION = "d12-corpus-1.0"


class CorpusKeyError(KeyError):
    """A corpus lookup that does not resolve. Raised, never papered over with a
    default sentence: a missing cell is a binding gap to report."""


# ─────────────────────────────────────────────────────────────────────────────
# SHARED VOCABULARY
# ─────────────────────────────────────────────────────────────────────────────

ELEMENTS: Tuple[str, ...] = ("Fire", "Earth", "Air", "Water")

# FR-006A §5. Exactly these four, exactly these members.
HOUSE_CATEGORY: Dict[int, str] = {
    1: "Kendra", 4: "Kendra", 7: "Kendra", 10: "Kendra",
    5: "Trikona", 9: "Trikona",
    6: "Dusthana", 8: "Dusthana", 12: "Dusthana",
    2: "Auxiliary", 3: "Auxiliary", 11: "Auxiliary",
}
CATEGORIES: Tuple[str, ...] = ("Kendra", "Trikona", "Dusthana", "Auxiliary")

# The six graded D12 dignity states collapse into the four corpus buckets.
# `Ungraded` is deliberately absent: it has no bucket, and a node can never
# occupy a §5 Lagnesh or §6 speaker slot (both are always sign lords or the
# luminaries). A selector meeting `Ungraded` here must fail closed.
DIGNITY_BUCKET: Dict[str, str] = {
    "Uchcha": "Uchcha/Sva", "Sva": "Uchcha/Sva",
    "Mitra": "Mitra",
    "Sama": "Sama",
    "Shatru": "Shatru/Neecha", "Neecha": "Shatru/Neecha",
}
BUCKETS: Tuple[str, ...] = ("Uchcha/Sva", "Mitra", "Sama", "Shatru/Neecha")

# FR-001 vocabulary. Defined and validated here; NOT calculated in this flight.
STRUCTURAL_CLASSES: Tuple[str, ...] = ("Supported", "Loaded", "Redirected")


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 5 · INHERITANCE MET
# ─────────────────────────────────────────────────────────────────────────────

# key: (lagna sign, lagnesh house, dignity bucket)
S5_BESPOKE: Dict[Tuple[str, int, str], str] = {
    ("Gemini", 3, "Mitra"): (
        "Inheritance is met by naming, sorting, and verbal articulation. "
        "Overreach: explaining the family structure instead of directly "
        "meeting its operational demands."),
    ("Gemini", 3, "Uchcha/Sva"): (
        "Inheritance is met by naming, sorting, and verbal articulation. "
        "Overreach: explaining the family structure instead of directly "
        "meeting its operational demands."),
    ("Aries", 10, "Uchcha/Sva"): (
        "Inheritance is met through direct executive action and professional "
        "positioning. Overreach: treating family history as an engineering "
        "problem to be forcibly solved."),
    ("Cancer", 1, "Uchcha/Sva"): (
        "Inheritance is met through intuitive emotional absorption and "
        "defensive preservation. Overreach: carrying domestic grievances as a "
        "personal identity shield."),
}

# The Gemini and Aries cells are each authorised for two dignity states
# ("Mitra or Sva", "Uchcha or Sva") and the buckets collapse Uchcha with Sva, so
# the Gemini cell needs both bucket keys and the Aries and Cancer cells need the
# Uchcha/Sva bucket. No string is altered between them.
#
# FD-004-01 (LOCKED) · the Taurus / Venus H4 / Mitra cell is RETIRED and must
# not be reinstated. Under accepted D12 mechanics a Taurus D12 Lagna puts H4 in
# Leo, and Venus in Leo is Shatru — Leo's lord Sun is one of Venus's natural
# enemies — so the Mitra state was mechanically unreachable and the cell could
# never fire. A mechanically valid Taurus / Venus-H4 / Shatru chart resolves
# through the ordinary §5 fallback matrix. No replacement Taurus cell is
# authorised.
S5_BESPOKE_SOURCE: Dict[Tuple[str, int, str], str] = {
    k: "FR-006A §5 approved bespoke cell" for k in S5_BESPOKE}

S5_TEMPLATE = (
    "Inheritance is met through {mode} channelized via the {category} domain "
    "under {dignity} conditions. Overreach: {risk} rather than directly meeting "
    "the ancestral framework.")

S5_ELEMENT_MODE: Dict[str, str] = {
    "Fire": "direct executive drive",
    "Earth": "practical structural consolidation",
    "Air": "analytical sorting and verbal mapping",
    "Water": "absorptive emotional processing",
}

S5_ELEMENT_RISK: Dict[str, str] = {
    "Fire": "over-agitating the structural landscape through personal force",
    "Earth": "over-securing material permanence to offset emotional uncertainty",
    "Air": "over-explaining the family mechanics instead of directly meeting them",
    "Water": "over-absorbing domestic turbulence at the expense of personal equilibrium",
}

S5_DIGNITY_DESCRIPTOR: Dict[str, str] = {
    "Uchcha/Sva": "peak structural integrity",
    "Mitra": "supportive operational",
    "Sama": "neutral baseline",
    "Shatru/Neecha": "strained and heavily weighted",
}

# The template's [House Category] slot takes the category name itself.
S5_CATEGORY_TOKEN: Dict[str, str] = {c: c for c in CATEGORIES}


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 6 · FATHER & MOTHER
# ─────────────────────────────────────────────────────────────────────────────

# FR-006A §6 fallback key, in the locked order. Father speakers first.
SPEAKER_FAMILIES: Tuple[str, ...] = (
    "Sun Karaka", "D12 H9 Lord", "D1 9th Lord in D12",
    "Moon Karaka", "D12 H4 Lord", "D1 4th Lord in D12",
)

# Which parent each family speaks for. Strict separation: no string crosses.
SPEAKER_PARENT: Dict[str, str] = {
    "Sun Karaka": "Father", "D12 H9 Lord": "Father", "D1 9th Lord in D12": "Father",
    "Moon Karaka": "Mother", "D12 H4 Lord": "Mother", "D1 4th Lord in D12": "Mother",
}

KARAKA_FAMILIES: Tuple[str, ...] = ("Sun Karaka", "Moon Karaka")

S6_BESPOKE: Dict[str, str] = {
    "sun_karaka.virgo.h4.sama": (
        "The father is experienced as a fixed structural landmark within the "
        "domestic framework rather than an active, variable presence; authority "
        "is expressed through quiet standards rather than open warmth."),
    "sun_karaka.aries.h10.uchcha": (
        "The father is encountered as an institutional or public force, leaving "
        "a legacy of high expectation and structural demand."),
    "h9_lord.empty_h9.lord_in_h11.neecha_or_loaded": (
        "The paternal dharma field runs through a heavily loaded operational "
        "channel, bringing heavy obligations, structural friction, and "
        "long-term endurance."),
    # FD-004-02 (LOCKED) · this key replaces the retired
    # "empty_h9.lord_in_h9.supported" predicate, which was self-contradictory:
    # a lord sitting in H9 makes H9 occupied, so "vacant except for its lord"
    # could never be true and the cell was unreachable. The approved text is
    # unchanged; only the firing condition moved.
    "h9_lord.vacant_h9.lord_well_placed_kendra_or_trikona.supported": (
        "The paternal dharma field offers clean continuity, supporting "
        "traditional knowledge transfer and disciplined study."),
    "moon_karaka.scorpio.h6.neecha": (
        "The mother's legacy is knotted with service, struggle, and historical "
        "friction; emotional care feels bound to repayment and duty."),
    "moon_karaka.cancer.h4.sva": (
        "The mother's legacy provides deep emotional nourishment anchored in "
        "traditional domestic routines and protective care."),
    "h4_occupied.sun_and_rahu": (
        "The maternal and domestic field is public, irregular, and complex, "
        "characterized by competing external demands and shifting internal "
        "pressures."),
}

S6_TEMPLATE = (
    "{speaker} is encountered as a {category} dynamic carrying {load}, "
    "expressing legacy through {tone} without collapsing active personal "
    "boundaries.")

S6_CATEGORY_LANGUAGE: Dict[str, str] = {
    "Kendra": "structural foundation",
    "Trikona": "dharmic continuity",
    "Dusthana": "karmic friction",
    "Auxiliary": "operational network",
}

S6_DIGNITY_LOAD: Dict[str, str] = {
    "Uchcha/Sva": "clean and unencumbered power",
    "Mitra": "steady, reliable support",
    "Sama": "unyielding baseline gravity",
    "Shatru/Neecha": "deep structural friction and historical drag",
}

S6_ELEMENT_TONE: Dict[str, str] = {
    "Fire": "direct, uncompromising authority",
    "Earth": "deliberate physical permanence",
    "Air": "calculated intellectual distance",
    "Water": "dense emotional resonance",
}

# The template's [Speaker Family Identity] slot. FR-006A names the six families
# but supplies no separate identity prose for them, so the locked family name is
# substituted verbatim. Inventing six identity phrases would be manufacturing
# corpus; see the D12-004 report, "binding note 1".
S6_SPEAKER_IDENTITY: Dict[str, str] = {f: f for f in SPEAKER_FAMILIES}


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 7 · THE UNPAID PATTERN — corpus CLOSED
# ─────────────────────────────────────────────────────────────────────────────

S7_CELLS: Dict[str, str] = {
    "moon_occupant.lord_h2.neecha": (
        "Emotional labor, care given, and historical debts constitute the "
        "primary active balance sheet; the pattern requires steady, bounded "
        "service without lapsing into self-erasure or martyrdom."),
    "empty_h6.malefic_lord_in_dusthana": (
        "Service obligations manifest as practical administrative burdens "
        "rather than deep emotional entanglements, requiring objective "
        "execution without personal sacrifice."),
    "benefic_occupant_h6.strong_lord": (
        "The debt of care is met naturally through professional mentorship or "
        "structured community contribution, maintaining clear operational "
        "boundaries."),
}

S7_BASELINE = (
    "Service obligations manifest as practical operational boundaries requiring "
    "objective execution without personal emotional entanglement.")


# ─────────────────────────────────────────────────────────────────────────────
# CANONICAL KEY -> TEXT RESOLUTION
#
# One resolver over the registries ABOVE. There is no second copy of any string:
# this reads the same tables the selectors read, so a corpus edit moves both the
# emitted sentence and the expected sentence together and can never split them.
#
# The typed findings contract calls this to enforce, at the boundary, that a
# valid corpus key may carry ONLY the text authorised for that key. QA proved
# the previous contract accepted arbitrary prose under a legitimate key; this
# closes that.
# ─────────────────────────────────────────────────────────────────────────────

def _s5_fallback_text(element: str, category: str, bucket: str) -> str:
    return S5_TEMPLATE.format(mode=S5_ELEMENT_MODE[element],
                              category=S5_CATEGORY_TOKEN[category],
                              dignity=S5_DIGNITY_DESCRIPTOR[bucket],
                              risk=S5_ELEMENT_RISK[element])


def _s6_fallback_text(family: str, category: str, element: str, bucket: str) -> str:
    return S6_TEMPLATE.format(speaker=S6_SPEAKER_IDENTITY[family],
                              category=S6_CATEGORY_LANGUAGE[category],
                              load=S6_DIGNITY_LOAD[bucket],
                              tone=S6_ELEMENT_TONE[element])


def text_for_key(corpus_key: str) -> str:
    """The one text a corpus key is authorised to carry. Raises otherwise.

    Key grammar, all finite and enumerable:
        S5.bespoke.<lagna sign>.H<house>.<bucket>
        S5.fallback.<element>.<category>.<bucket>
        S6.bespoke.<cell key>
        S6.fallback.<speaker family>.<category>.<element>.<bucket>
        S7.cell.<cell key>
        S7.baseline
    """
    if not isinstance(corpus_key, str) or not corpus_key:
        raise CorpusKeyError(f"corpus_key must be a non-empty string, got {corpus_key!r}")

    if corpus_key == "S7.baseline":
        return S7_BASELINE

    if corpus_key.startswith("S7.cell."):
        cell = corpus_key[len("S7.cell."):]
        if cell not in S7_CELLS:
            raise CorpusKeyError(f"unknown §7 cell {cell!r}")
        return S7_CELLS[cell]

    if corpus_key.startswith("S6.bespoke."):
        cell = corpus_key[len("S6.bespoke."):]
        if cell not in S6_BESPOKE:
            raise CorpusKeyError(f"unknown §6 bespoke cell {cell!r}")
        return S6_BESPOKE[cell]

    if corpus_key.startswith("S6.fallback."):
        parts = corpus_key[len("S6.fallback."):].split(".")
        if len(parts) != 4:
            raise CorpusKeyError(f"malformed §6 fallback key {corpus_key!r}")
        family, category, element, bucket = parts
        if (family not in S6_SPEAKER_IDENTITY or category not in S6_CATEGORY_LANGUAGE
                or element not in S6_ELEMENT_TONE or bucket not in S6_DIGNITY_LOAD):
            raise CorpusKeyError(f"§6 fallback key out of vocabulary: {corpus_key!r}")
        return _s6_fallback_text(family, category, element, bucket)

    if corpus_key.startswith("S5.bespoke."):
        parts = corpus_key[len("S5.bespoke."):].split(".")
        if len(parts) != 3 or not parts[1].startswith("H"):
            raise CorpusKeyError(f"malformed §5 bespoke key {corpus_key!r}")
        sign, house_token, bucket = parts
        try:
            house = int(house_token[1:])
        except ValueError:
            raise CorpusKeyError(f"malformed §5 bespoke house in {corpus_key!r}")
        cell = (sign, house, bucket)
        if cell not in S5_BESPOKE:
            raise CorpusKeyError(f"unknown §5 bespoke cell {cell!r}")
        return S5_BESPOKE[cell]

    if corpus_key.startswith("S5.fallback."):
        parts = corpus_key[len("S5.fallback."):].split(".")
        if len(parts) != 3:
            raise CorpusKeyError(f"malformed §5 fallback key {corpus_key!r}")
        element, category, bucket = parts
        if (element not in S5_ELEMENT_MODE or category not in S5_CATEGORY_TOKEN
                or bucket not in S5_DIGNITY_DESCRIPTOR):
            raise CorpusKeyError(f"§5 fallback key out of vocabulary: {corpus_key!r}")
        return _s5_fallback_text(element, category, bucket)

    raise CorpusKeyError(f"unrecognised corpus key {corpus_key!r}")


def all_corpus_keys():
    """Every key the resolver accepts. Finite and enumerable by construction."""
    keys = ["S7.baseline"]
    keys += [f"S7.cell.{k}" for k in S7_CELLS]
    keys += [f"S6.bespoke.{k}" for k in S6_BESPOKE]
    keys += [f"S5.bespoke.{sign}.H{house}.{bucket}"
             for (sign, house, bucket) in S5_BESPOKE]
    for element in ELEMENTS:
        for category in CATEGORIES:
            for bucket in BUCKETS:
                keys.append(f"S5.fallback.{element}.{category}.{bucket}")
    for family in SPEAKER_FAMILIES:
        for category in CATEGORIES:
            for element in ELEMENTS:
                for bucket in BUCKETS:
                    keys.append(f"S6.fallback.{family}.{category}.{element}.{bucket}")
    return tuple(keys)



# ─────────────────────────────────────────────────────────────────────────────
# SECTION 8 · RESIDUE MAP — domain-constant, corpus complete
# ─────────────────────────────────────────────────────────────────────────────

S8_DOMAINS: Tuple[int, ...] = (2, 5, 6, 7, 8, 11, 12)

S8_VISIBLE_LABEL: Dict[int, str] = {
    2: "Already skilled",
    5: "Merit on tap",
    6: "Still owed",
    7: "What sticks in union",
    8: "What must be cleaned",
    11: "Company",
    12: "Release valve",
}

S8_CLAUSE: Dict[int, str] = {
    2: "Force and craft already in the hands.",
    5: "Support exists as a structural reservoir; it is not a personality trait.",
    6: "Emotional care bound to active repayment without martyrdom.",
    7: "Partnership and desire mapped as a completion-fantasy.",
    8: "Charm and intensity under pressure requiring deep inner cleaning.",
    11: "Help and heaviness inhabiting the same social room.",
    12: "Freedom runs through how pleasure and loss are held without grasping.",
}

# §8 is a domain-constant TUPLE, not three independent fields. The contract
# binds all three together, so H6 can never carry the H8 clause or an internal
# identifier as its label — QA's finding, closed at the type boundary.
S8_TUPLES = tuple((h, S8_VISIBLE_LABEL[h], S8_CLAUSE[h]) for h in S8_DOMAINS)


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 9 · DEVATĀ
# ─────────────────────────────────────────────────────────────────────────────

# Ported byte-exact from newphalit_fixed.html L25046-25052. Index is the
# ZERO-BASED slice (slice number - 1).
D12_DEITIES: Tuple[str, ...] = (
    "Ganesha", "Ashwini", "Yama", "Sarpa",
    "Ganesha", "Ashwini", "Yama", "Sarpa",
    "Ganesha", "Ashwini", "Yama", "Sarpa",
)

D12_HIDDEN: Tuple[str, ...] = (
    "Kubera", "Patanga", "Hala", "Kireeti",
    "Vihwala", "Mayavee", "Mohan", "Kinnara",
    "Sarpa", "Indra", "Leela", "Kokila",
)

# INTERNAL MAPPING METADATA ONLY. Never published, never glossed, never joined
# to a customer-facing sentence. Retained so the legacy mapping stays traceable.
D12_MEANING: Tuple[str, ...] = (
    "Wealth & Beginnings", "Fire of Life", "Intoxicating Spirit", "Enthroned Fame",
    "Agitated Mind", "World of Illusion", "Beloved, Magnetic", "Mystical Being",
    "Serpentine Wisdom", "King of Kings", "Play of Delusion", "Sweet Song of Maya",
)

# FR-005 authoritative glosses. Exactly ten. Any deity absent from this mapping
# is an internal label and MUST NOT receive explanatory prose: Patanga, Kireeti,
# Mayavee, Leela and Kokila are deliberately unglossed.
DEVATA_GLOSS: Dict[str, str] = {
    "Ganesha": "Beginnings and obstacle-clearing.",
    "Yama": "Limit, consequence, and law.",
    "Ashwini": "Swift healing and swift entry.",
    "Sarpa": "Coiled intelligence that sheds skin.",
    "Kinnara": "Celestial singer of hidden forms.",
    "Indra": "Sovereign ruler of divine authority.",
    "Kubera": "Keeper of subterranean divine wealth.",
    "Vihwala": "Agitated search for ultimate truth.",
    "Mohan": "Enchanting and magnetic emotional pull.",
    "Hala": "Intoxicating spirit of deep dissolution.",
}

UNGLOSSED_HIDDEN: Tuple[str, ...] = tuple(
    d for d in D12_HIDDEN if d not in DEVATA_GLOSS)

# FR-005 pair-name rule: no Founder-approved compound clause exists, so the
# customer-facing name is the primary deity alone. There is no compound table
# in this module and none may be added without a Founder ruling.
PAIR_COMPOUND_CLAUSES: Mapping[Tuple[str, str], str] = {}


def devata_for_slice(slice_number: int) -> Tuple[str, str]:
    """(primary, hidden) for a 1-based slice. Mechanical lookup only."""
    if type(slice_number) is not int or not 1 <= slice_number <= 12:
        raise CorpusKeyError(f"slice must be an int 1..12, got {slice_number!r}")
    return D12_DEITIES[slice_number - 1], D12_HIDDEN[slice_number - 1]


def gloss(deity: str) -> str:
    """The Founder gloss, or raise. Never invents one for an unglossed name."""
    if deity not in DEVATA_GLOSS:
        raise CorpusKeyError(
            f"{deity!r} has no Founder-approved gloss and must not receive "
            f"invented prose")
    return DEVATA_GLOSS[deity]
