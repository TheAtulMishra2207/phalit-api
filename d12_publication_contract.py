"""d12_publication_contract.py — the frozen §§0-15 page contract.

D12-006A. `D12_Format_Specification.pdf`
(8fa8ea73a56a8d12b0fc1f2f7cae676c8c2bc7faaa381f7af0198113ab0f0fb1) is the page
contract, and this module is that contract expressed as types.

The locked copy for §§1, 2, 14 and 15 is transcribed verbatim from the PDF. It is
not rewritten, shortened or "improved": the specification says to print it.

WHAT THIS MODULE MAKES IMPOSSIBLE, by construction rather than by convention:
  * sections out of order, missing, or duplicated;
  * an UNKNOWN handshake row reaching a customer as a class;
  * an unresolved tension printed as the static fallback;
  * altered FR-003 instruction text;
  * more than the seven approved §8 residue rows;
  * uncollapsed Devatā climates;
  * Strong / Weakened / remediation vocabulary on the §10 grid.

Every deterministic sentence keeps the corpus key or selector result that
produced it, so a reader never has to reverse-engineer why it printed.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from pydantic import (BaseModel, Extra, StrictBool, StrictInt, StrictStr,
                      conint, validator)

from d12_corpus import (D12_DEITIES, D12_HIDDEN, DEVATA_GLOSS, S6_BESPOKE,
                        S8_DOMAINS, SPEAKER_FAMILIES, SPEAKER_PARENT,
                        devata_for_slice)
from d12_corpus import text_for_key as K_text_for_key
from d12_crosschart_contract import Classification, Tri
from d12_engine import D12_GRAHAS
from d12_instruction_corpus import (INSTRUCTION_SLOTS, TENSION_FALLBACK,
                                    TENSION_KEYS, TENSION_TITLE,
                                    instruction_text)

PUBLICATION_CONTRACT_VERSION = "d12-publication-1.0"
FORMAT_SPEC_SHA256 = "8fa8ea73a56a8d12b0fc1f2f7cae676c8c2bc7faaa381f7af0198113ab0f0fb1"

# The frozen page map, §0 through §15, in the only admissible order.
SECTION_TITLES: Tuple[Tuple[int, str], ...] = (
    (0, "Header"),
    (1, "What this chart is"),
    (2, "How to read this page in 30 seconds"),
    (3, "Chart card"),
    (4, "The only three questions D12 is allowed to answer"),
    (5, "How the inheritance is met"),
    (6, "Father / Mother"),
    (7, "What is still unpaid"),
    (8, "What this life is still carrying"),
    (9, "Devatā climate"),
    (10, "D1 × D12 handshake"),
    (11, "The tension worth naming"),
    (12, "Three instructions"),
    (13, "Integrated reading"),
    (14, "How to use this reading"),
    (15, "Glossary"),
)
SECTION_ORDER: Tuple[int, ...] = tuple(n for n, _ in SECTION_TITLES)

CHIPS: Tuple[str, ...] = ("STANCE", "RULER", "FATHER", "MOTHER", "RELEASE", "NOW")

# The frozen dignity legend, §3, verbatim.
DIGNITY_LEGEND = ("Uchcha strongest · Sva own · Mitra friend · Sama neither · "
                  "Shatru enemy · Neecha weakest · Ungraded nodes outside "
                  "those states")

GLYPHS = ("Su Sun · Mo Moon · Ma Mars · Me Mercury · Ju Jupiter · "
          "Ve Venus · Sa Saturn · Ra Rahu · Ke Ketu")
CHART_CARD_NOTES = (
    "North-Indian diamond. Caption is a legend. Centre label is D12.",
    "Top diamond = House 1 (always). Number + sign abbreviation = the rāśi in "
    "that house. Count houses anti-clockwise.",
    "H = house    R = retrograde",
)

# §4 · exactly three questions. There is no fourth.
PERMITTED_QUESTIONS: Tuple[Tuple[str, str], ...] = (
    ("How do I meet what I inherited?", "D12 Lagna + Lagnesh"),
    ("What is still unpaid with the parents?", "D12 H6 + Moon + 6th lord"),
    ("What does release look like here?",
     "H12 + Ketu vs luminaries + D1 12th lord in D12"),
)

# ── LOCKED PDF COPY · §§1, 2, 14, 15 ────────────────────────────────────────

SECTION_1_COPY: Tuple[str, ...] = (
    "The Dwādaśāṁśa cuts each sign into twelve slices of 2°30′. It is the same "
    "birth data at the resolution of inheritance — parents, what they handed "
    "on, and the pattern that was already in motion before this life.",
    "It is not a second biography, not a medical chart for the parents, and "
    "not a promise of moksha.",
    "Read it with the natal 4th and 9th, not instead of them. D1 shows the "
    "visible family circumstances. D12 shows how that inheritance is met.",
    "This page answers three things: how you take up what came from the "
    "parents, what is still unpaid, and what release looks like as a stance — "
    "not as a monastery.",
)
SECTION_1_ASIDE = ("Each slice starts from the sign the planet is in and counts "
                   "forward twelve signs. The reader does not draw this.")

SECTION_2_STEPS: Tuple[Tuple[int, str, str], ...] = (
    (1, "Chart + legend", "Where does each graha sit in the inheritance-map?"),
    (2, "Stance", "How do I meet what I inherited?"),
    (3, "Father / Mother", "Karaka and house, separately?"),
    (4, "Unpaid", "What is still charged with the parents?"),
    (5, "Carried forward", "What leftover pattern is mapped?"),
    (6, "Handshake", "How do the natal 4th, 9th, 12th lords sit in D12?"),
    (7, "Prose", "What is the one pattern?"),
)

SECTION_14_COPY: Tuple[str, ...] = (
    "D12 refines the natal 4th and 9th. It does not replace them.",
    "It does not diagnose the parents.",
    "It does not time illness or death.",
    "It does not assign a past-life identity.",
    "It does not prescribe rites — that is the Remedial Dossier.",
    "D9 is what the life is for. D10 is how work runs. D12 is what was handed "
    "on and what is still charged.",
    "Ketu-logic here is not a veto of D10 standing or of a Kubera climate in "
    "work.",
    "If a sentence has no speaker tag in the section above, treat it as prose, "
    "not as a rule-hit.",
)

SECTION_15_GLOSSARY: Tuple[Tuple[str, str], ...] = (
    ("Dwādaśāṁśa / D12", "Twelfth division; parents and inherited charge"),
    ("Lagna / Lagnesh",
     "Rising sign of this chart / its ruler — how inheritance is met"),
    ("Karaka", "Significator — Sun father, Moon mother, Ketu release-pull"),
    ("Neecha", "Debilitated; weakest sign. Not a verdict on a parent\u2019s worth"),
    ("Vasana", "Leftover tendency; not a past-life movie"),
    ("Devatā / hidden name", "Flavour of the 2°30′ slice"),
    ("Sarpa", "Coiled / shedding; not an omen"),
    ("Karya rashi", "D1 house-lords judged in D12 (handshake)"),
    ("Through lord", "Vacant house giving results via its ruler"),
    ("Maraka",
     "Timing technique for harm-windows — not a D12 finding"),
    ("Vargottama first slice",
     "Same sign in D1 and D12, occupying 0°–2°30′ of the D1 sign"),
)

# §6 · the pointer the PDF permits when a Maraka flag fires. It is a POINTER,
# not a finding, and it is the only sentence on this page that may name the
# technique outside the glossary.
MARAKA_POINTER = "Parental health windows are a dasha question."

# §8 · "Through lord" is the frozen phrase for a vacant house.
THROUGH_LORD = "Through lord"

# §10 · vocabulary the PDF explicitly bans on this grid.
BANNED_GRID_WORDS: Tuple[str, ...] = ("strong", "weakened", "weak",
                                      "remediation", "remedy", "score")

# §10 · THE CANONICAL ONE-LINE REGISTRY. CORR-01: the finite mapping lives here,
# not inside the builder, so (source house, classification) binds to exactly one
# sentence and an H4 Loaded row cannot carry the H4 Supported line.
GRID_ONE_LINE: Dict[Tuple[int, str], str] = {
    (4, "Loaded"): "Mother / home-opportunity comes with a grind",
    (4, "Supported"): "Mother / home-opportunity reachable in the inheritance field",
    (4, "Redirected"): "Mother / home-opportunity runs through an indirect house",
    (9, "Loaded"): "Father / dharma-opportunity comes with a grind",
    (9, "Supported"): "Father / dharma-opportunity reachable through the same graha",
    (9, "Redirected"): "Father / dharma-opportunity runs through an indirect house",
    (12, "Loaded"): "Release carries a grind before it carries ease",
    (12, "Supported"): "Release uses the same graha — naming, not fleeing",
    (12, "Redirected"): "Release runs through an indirect house",
}


def grid_one_line(source_house: int, classification: str) -> str:
    """The one sentence a (house, class) pair is authorised to carry."""
    key = (source_house, classification)
    if key not in GRID_ONE_LINE:
        raise KeyError(f"no §10 one-line is authorised for {key}")
    return GRID_ONE_LINE[key]


class _Closed(BaseModel):
    class Config:
        extra = Extra.forbid
        allow_mutation = False


class Chip(_Closed):
    """§0 · one header chip. The value summarises an already-certified fact."""
    label: StrictStr
    value: StrictStr
    source: StrictStr

    @validator("label")
    def _one_of_the_six(cls, v):
        if v not in CHIPS:
            raise ValueError(f"{v!r} is not one of the six frozen chips")
        return v


class Section0(_Closed):
    title: StrictStr = "DWĀDAŚĀṀŚA · PARENTS & WHAT WAS CARRIED"
    subtitle: StrictStr = "D12 · Inheritance, unpaid pattern, release"
    # Astrology-neutral presentation metadata only. Display name and place are
    # NOT carried: the snapshot has no reliable label for either, and 006B
    # overlays the active UI identity after its own token+epoch guard.
    birth_date: Optional[StrictStr]
    birth_time: Optional[StrictStr]
    chips: List[Chip]

    @validator("chips")
    def _exactly_the_six_in_order(cls, v):
        if tuple(c.label for c in v) != CHIPS:
            raise ValueError(f"the six chips must appear in order {CHIPS}")
        return v


class Section1(_Closed):
    paragraphs: List[StrictStr]
    newbie_aside: StrictStr

    @validator("paragraphs")
    def _locked_copy(cls, v):
        if tuple(v) != SECTION_1_COPY:
            raise ValueError("§1 must print the locked PDF copy verbatim")
        return v

    @validator("newbie_aside")
    def _locked_aside(cls, v):
        if v != SECTION_1_ASIDE:
            raise ValueError("§1 aside must print the locked PDF copy verbatim")
        return v


class ReadStep(_Closed):
    step: conint(strict=True, ge=1, le=7)
    look_at: StrictStr
    question: StrictStr


class Section2(_Closed):
    steps: List[ReadStep]

    @validator("steps")
    def _locked_steps(cls, v):
        got = tuple((s.step, s.look_at, s.question) for s in v)
        if got != SECTION_2_STEPS:
            raise ValueError("§2 must print the locked seven steps verbatim")
        return v


class ChartRow(_Closed):
    house: conint(strict=True, ge=1, le=12)
    sign: StrictStr
    sign_abbr: StrictStr
    lord: StrictStr
    occupants: List[StrictStr] = []


class GrahaRow(_Closed):
    graha: StrictStr
    house: conint(strict=True, ge=1, le=12)
    sign: StrictStr
    dignity: StrictStr
    vargottama: StrictBool


class Section3(_Closed):
    d12_lagna_sign: StrictStr
    d12_lagnesh: StrictStr
    houses: List[ChartRow]
    grahas: List[GrahaRow]
    legend_dignity: StrictStr = DIGNITY_LEGEND
    legend_glyphs: StrictStr = GLYPHS
    notes: List[StrictStr] = list(CHART_CARD_NOTES)

    @validator("houses")
    def _twelve_rows_in_order(cls, v):
        if [r.house for r in v] != list(range(1, 13)):
            raise ValueError("§3 needs houses 1..12 in order")
        return v

    @validator("grahas")
    def _nine_grahas(cls, v):
        if len(v) != 9:
            raise ValueError("§3 needs exactly nine grahas")
        return v

    @validator("legend_dignity")
    def _frozen_legend(cls, v):
        if v != DIGNITY_LEGEND:
            raise ValueError("§3 legend must be the frozen dignity vocabulary")
        return v


class PermittedQuestion(_Closed):
    question: StrictStr
    read_from: StrictStr
    answer: StrictStr

    @validator("read_from")
    def _pair_is_frozen(cls, v, values):
        q = values.get("question")
        if q is None:
            return v
        if (q, v) not in PERMITTED_QUESTIONS:
            raise ValueError(f"{q!r}/{v!r} is not one of the three permitted pairs")
        return v


class Section4(_Closed):
    questions: List[PermittedQuestion]

    @validator("questions")
    def _exactly_three_in_order(cls, v):
        got = tuple((q.question, q.read_from) for q in v)
        if got != PERMITTED_QUESTIONS:
            raise ValueError("§4 carries exactly the three permitted questions")
        return v


class TaggedBlock(_Closed):
    """A deterministic block that keeps the key or selector result behind it.

    CORR-01 · when `corpus_key` is present the text is validated against the
    canonical D12-004 registry through `d12_corpus.text_for_key`. There is no
    duplicated copy here: the same registry the selectors read is the one that
    decides, so a validated finding cannot become a free string at publication.
    """
    speaker: StrictStr
    label: StrictStr
    text: StrictStr
    corpus_key: Optional[StrictStr] = None
    basis: Dict[StrictStr, StrictStr] = {}

    @validator("corpus_key")
    def _text_matches_the_canonical_corpus(cls, v, values):
        if v is None:
            return v
        text = values.get("text")
        if text is None:
            return v
        try:
            expected = K_text_for_key(v)
        except Exception as exc:
            raise ValueError(str(exc))
        if text != expected:
            raise ValueError(
                f"the block text is not the locked corpus string for {v!r}")
        return v


class Section5(_Closed):
    speaker: StrictStr = "PARĀŚARA · D12 LAGNA + LAGNESH"
    lagna: TaggedBlock
    lagnesh: TaggedBlock
    imprint: TaggedBlock
    vargottama_first_slice: Optional[TaggedBlock]
    corpus_key: StrictStr

    @validator("corpus_key")
    def _mirrors_the_lagna_block(cls, v, values):
        lagna = values.get("lagna")
        if lagna is not None and lagna.corpus_key is not None and v != lagna.corpus_key:
            raise ValueError("§5 corpus_key must be the lagna block's own key")
        return v


# CORR-02 · reuse the already-certified D12-004 authority. No competing family
# table is built here: SPEAKER_PARENT decides which parent a family speaks for,
# and the bespoke-cell prefixes decide which family owns a cell.
FATHER_FAMILIES: Tuple[str, ...] = tuple(
    f for f in SPEAKER_FAMILIES if SPEAKER_PARENT[f] == "Father")
MOTHER_FAMILIES: Tuple[str, ...] = tuple(
    f for f in SPEAKER_FAMILIES if SPEAKER_PARENT[f] == "Mother")

_BESPOKE_PREFIX_TO_FAMILY = {"sun_karaka.": "Sun Karaka",
                             "moon_karaka.": "Moon Karaka",
                             "h9_lord.": "D12 H9 Lord",
                             "h4_occupied.": "D12 H4 Lord"}
S6_BESPOKE_FAMILY: Dict[str, str] = {}
for _cell in S6_BESPOKE:
    for _pfx, _fam in _BESPOKE_PREFIX_TO_FAMILY.items():
        if _cell.startswith(_pfx):
            S6_BESPOKE_FAMILY[_cell] = _fam
            break
if set(S6_BESPOKE_FAMILY) != set(S6_BESPOKE):
    raise RuntimeError("every §6 bespoke cell needs an authorised family")


def family_of_key(corpus_key: str) -> Optional[str]:
    """The frozen family a §6 corpus key speaks for, or None if it is not one."""
    if corpus_key.startswith("S6.fallback."):
        return corpus_key[len("S6.fallback."):].split(".")[0]
    if corpus_key.startswith("S6.bespoke."):
        return S6_BESPOKE_FAMILY.get(corpus_key[len("S6.bespoke."):])
    return None


class ParentCard(_Closed):
    """§6 · Karaka and house are SEPARATE speakers and never share a sentence.
    The Sun's house is never captioned Mother inside the Father card.

    CORR-02 · each block keeps its frozen D12-004 FAMILY, so the typed object
    proves which of the six spoke. The display tag stays as it is; the semantic
    identity is carried alongside it and validated against SPEAKER_PARENT.
    """
    parent: StrictStr
    karaka: TaggedBlock
    house_of_parent: TaggedBlock
    d1_lord_in_d12: TaggedBlock
    families: List[StrictStr]

    @validator("families")
    def _the_three_frozen_families_for_this_parent(cls, v, values):
        parent = values.get("parent")
        if parent is None:
            return v
        expected = FATHER_FAMILIES if parent == "Father" else MOTHER_FAMILIES
        if tuple(v) != expected:
            raise ValueError(
                f"a {parent} card must carry exactly {list(expected)}, got {v}")
        for family in v:
            if SPEAKER_PARENT[family] != parent:
                raise ValueError(f"{family!r} does not speak for {parent}")
        return v

    @validator("families")
    def _each_corpus_key_belongs_to_its_own_family(cls, v, values):
        blocks = [values.get("karaka"), values.get("house_of_parent"),
                  values.get("d1_lord_in_d12")]
        for family, block in zip(v, blocks):
            if block is None or block.corpus_key is None:
                continue
            owner = family_of_key(block.corpus_key)
            if owner is not None and owner != family:
                raise ValueError(
                    f"corpus key {block.corpus_key!r} speaks for {owner!r}, "
                    f"not {family!r}")
        return v

    @validator("parent")
    def _father_or_mother(cls, v):
        if v not in ("Father", "Mother"):
            raise ValueError(f"unknown parent {v!r}")
        return v

    @validator("d1_lord_in_d12")
    def _speakers_never_merge(cls, v, values):
        blocks = [values.get("karaka"), values.get("house_of_parent"), v]
        speakers = [b.speaker for b in blocks if b is not None]
        if len(set(speakers)) != len(speakers):
            raise ValueError("each §6 layer must carry its own distinct speaker")
        return v


class Section6(_Closed):
    speaker: StrictStr = "KARAKA + PARĀŚARA"
    father: ParentCard
    mother: ParentCard
    maraka_pointer: Optional[StrictStr]

    @validator("father")
    def _father_card_is_father(cls, v):
        if v.parent != "Father":
            raise ValueError("the father card must speak for the Father")
        return v

    @validator("mother")
    def _mother_card_is_mother(cls, v):
        if v.parent != "Mother":
            raise ValueError("the mother card must speak for the Mother")
        return v

    @validator("maraka_pointer")
    def _pointer_is_the_frozen_sentence_only(cls, v):
        # The PDF permits ONE pointer sentence and no finding.
        if v is not None and v != MARAKA_POINTER:
            raise ValueError("§6 may carry only the frozen dasha pointer")
        return v


class Section7(_Closed):
    speaker: StrictStr = "PARĀŚARA · H6"
    occupants: List[StrictStr]
    lord: StrictStr
    lord_house: conint(strict=True, ge=1, le=12)
    status: StrictStr
    picture: TaggedBlock
    corpus_key: StrictStr

    @validator("corpus_key")
    def _mirrors_the_picture_block(cls, v, values):
        pic = values.get("picture")
        if pic is not None and pic.corpus_key is not None and v != pic.corpus_key:
            raise ValueError("§7 corpus_key must be the picture block's own key")
        return v


class ResidueRow(_Closed):
    domain: StrictStr
    house: conint(strict=True, ge=1, le=12)
    read: StrictStr
    clause: StrictStr

    @validator("house")
    def _permitted_domain(cls, v):
        if v not in S8_DOMAINS:
            raise ValueError(f"H{v} is not one of the seven §8 residue domains")
        return v


class Section8(_Closed):
    speaker: StrictStr = "PARĀŚARA · LEFTOVER-MAP"
    teaching: StrictStr
    rows: List[ResidueRow]

    @validator("rows")
    def _exactly_the_seven_in_order(cls, v):
        if [r.house for r in v] != list(S8_DOMAINS):
            raise ValueError(
                f"§8 carries exactly H{list(S8_DOMAINS)} in order — no "
                f"twelve-row dump")
        return v


class DevataClimateRow(_Closed):
    deity: StrictStr
    subjects: List[StrictStr]
    count: StrictInt
    printed_once_as: StrictStr

    @validator("printed_once_as")
    def _the_display_is_deterministic(cls, v, values):
        """CORR-02 · no arbitrary customer prose. One imprint prints the exact
        Founder gloss; repeats print that gloss plus the one canonical
        collapse sentence."""
        deity, count = values.get("deity"), values.get("count")
        if deity is None or count is None:
            return v
        gloss = DEVATA_GLOSS.get(deity)
        if gloss is None:
            raise ValueError(f"{deity!r} has no Founder gloss")
        expected = gloss if count == 1 else (
            gloss + " " + CLIMATE_COLLAPSE.format(count=count))
        if v != expected:
            raise ValueError(
                f"the {deity!r} climate display is not the deterministic string")
        return v

    @validator("deity")
    def _a_real_primary_deity(cls, v):
        if v not in set(D12_DEITIES):
            raise ValueError(f"{v!r} is not a D12 primary deity")
        return v

    @validator("count")
    def _counts_its_own_subjects(cls, v, values):
        subjects = values.get("subjects")
        if subjects is not None and v != len(subjects):
            raise ValueError("a climate count must be its own subject count")
        if v < 1:
            raise ValueError("a climate collapses at least one imprint")
        return v


CLIMATE_COLLAPSE = "A climate, not {count} destinies."


class DevataImprintRow(_Closed):
    """§9 · one public imprint row. CORR-01: the frozen table is restored.

    `display_name` is the safe primary deity — FR-005 authorises no compound
    pair display — and `who_this_is` is its exact Founder gloss. The hidden
    deity stays internal to the deterministic selectors and is not carried here.
    """
    subject: StrictStr
    slice: conint(strict=True, ge=1, le=12)
    display_name: StrictStr
    who_this_is: StrictStr

    @validator("display_name")
    def _the_deity_the_slice_determines(cls, v):
        """CORR-02 · slice -> D12_DEITIES[slice-1] -> display_name, proven here
        rather than trusted. The hidden deity stays internal."""
        if v not in set(D12_DEITIES):
            raise ValueError(f"{v!r} is not a D12 primary deity")
        return v

    @validator("display_name")
    def _matches_its_own_slice(cls, v, values):
        slice_no = values.get("slice")
        if slice_no is None:
            return v
        expected = D12_DEITIES[slice_no - 1]
        if v != expected:
            raise ValueError(
                f"slice {slice_no} determines {expected!r}, got {v!r}")
        return v

    @validator("who_this_is")
    def _the_exact_founder_gloss(cls, v, values):
        deity = values.get("display_name")
        if deity is None:
            return v
        if DEVATA_GLOSS.get(deity) != v:
            raise ValueError(f"the gloss for {deity!r} is not the Founder string")
        return v


class Section9(_Closed):
    speaker: StrictStr = "DEVATĀ"
    imprints: List[DevataImprintRow]
    climates: List[DevataClimateRow]

    @validator("imprints")
    def _nine_subjects_exactly_once(cls, v):
        names = [r.subject for r in v]
        if sorted(names) != sorted(D12_GRAHAS):
            raise ValueError(
                f"§9 carries exactly the nine grahas, got {sorted(names)}")
        return v

    @validator("climates")
    def _the_ledger_is_the_exact_collapse_of_these_imprints(cls, v, values):
        """CORR-02 · the climate table must BE the collapse of the nine public
        imprints — same deity set, same membership, same counts — not a
        separately assembled tally that merely looks well-formed."""
        imprints = values.get("imprints")
        if imprints is None:
            return v
        expected: Dict[str, List[str]] = {}
        for im in imprints:
            expected.setdefault(im.display_name, []).append(im.subject)
        got = {c.deity: sorted(c.subjects) for c in v}
        if set(got) != set(expected):
            raise ValueError(
                f"§9 climates name {sorted(got)} but the imprints carry "
                f"{sorted(expected)}")
        for deity, subjects in expected.items():
            if got[deity] != sorted(subjects):
                raise ValueError(
                    f"the {deity!r} climate collapses {sorted(subjects)}, got "
                    f"{got[deity]}")
        for c in v:
            if c.count != len(expected[c.deity]):
                raise ValueError(
                    f"the {c.deity!r} climate count is {c.count}, but it "
                    f"collapses {len(expected[c.deity])} imprints")
        return v

    @validator("climates")
    def _repeats_are_collapsed(cls, v):
        names = [c.deity for c in v]
        if len(names) != len(set(names)):
            raise ValueError("§9 repeats collapse into one climate each")
        return v


class HandshakeRow(_Closed):
    d1_lord_of: conint(strict=True, ge=1, le=12)
    lord: StrictStr
    in_d12: StrictStr
    classification: StrictStr
    one_line: StrictStr

    @validator("d1_lord_of")
    def _the_three_grid_houses(cls, v):
        if v not in (4, 9, 12):
            raise ValueError("the §10 grid is exactly H4, H9, H12")
        return v

    @validator("classification")
    def _only_the_three_publishable_classes(cls, v):
        # UNKNOWN is an engineering state and is NOT customer copy.
        if v not in (Classification.SUPPORTED.value, Classification.LOADED.value,
                     Classification.REDIRECTED.value):
            raise ValueError(
                f"{v!r} is not publishable on the §10 grid; UNKNOWN must fail "
                f"closed rather than be renamed")
        return v

    @validator("one_line")
    def _no_banned_grid_vocabulary(cls, v):
        low = v.lower()
        for banned in BANNED_GRID_WORDS:
            if banned in low:
                raise ValueError(f"§10 must not print {banned!r}")
        return v

    @validator("one_line")
    def _the_line_is_bound_to_the_house_and_class(cls, v, values):
        """CORR-01 · an H4 Loaded row may not carry the H4 Supported line."""
        house, cls_ = values.get("d1_lord_of"), values.get("classification")
        if house is None or cls_ is None:
            return v
        if v != GRID_ONE_LINE.get((house, cls_)):
            raise ValueError(
                f"§10 one_line is not the canonical sentence for "
                f"(H{house}, {cls_})")
        return v


class Section10(_Closed):
    speaker: StrictStr = "D1 × D12"
    rows: List[HandshakeRow]

    @validator("rows")
    def _exactly_three_in_grid_order(cls, v):
        if [r.d1_lord_of for r in v] != [4, 9, 12]:
            raise ValueError("§10 carries exactly H4, H9, H12 in order")
        return v


class Section11(_Closed):
    """One box. The engine picks the split; only one prints."""
    tension_key: Optional[StrictStr]
    title: Optional[StrictStr]
    body: StrictStr
    fallback_applied: StrictBool
    word_count: StrictInt

    @validator("title")
    def _title_is_the_locked_one(cls, v, values):
        key = values.get("tension_key")
        if key is None:
            if v is not None:
                raise ValueError("the fallback carries no tension title")
            return v
        if key not in TENSION_KEYS:
            raise ValueError(f"unknown tension key {key!r}")
        if v != TENSION_TITLE[key]:
            raise ValueError("§11 title must be the locked string")
        return v

    @validator("fallback_applied")
    def _fallback_iff_no_key(cls, v, values):
        if "tension_key" not in values:
            return v
        if v is (values["tension_key"] is not None):
            raise ValueError(
                "an unresolved or absent tension must never be published as a "
                "winner, and a winner is never the fallback")
        return v

    @validator("body")
    def _fallback_body_is_the_frozen_sentence(cls, v, values):
        if values.get("tension_key") is None and v != TENSION_FALLBACK:
            raise ValueError("the §11 fallback body is the locked FR-002 string")
        return v

    @validator("word_count")
    def _ninety_word_limit(cls, v, values):
        body = values.get("body")
        if body is not None and v != len(body.split()):
            raise ValueError("word_count must be the body's own word count")
        if v > 90:
            raise ValueError(f"§11 is limited to 90 words; got {v}")
        return v


class Section12(_Closed):
    """The exact FR-003 triad for the winning tension. No paraphrase."""
    tension_key: StrictStr
    cultivate: StrictStr
    watch: StrictStr
    practise: StrictStr

    @validator("tension_key")
    def _a_real_tension(cls, v):
        if v not in TENSION_KEYS:
            raise ValueError(
                f"{v!r} has no FR-003 triad; §12 may not be invented for the "
                f"fallback")
        return v

    @validator("cultivate", "watch", "practise")
    def _exact_corpus_text(cls, v, values, field):
        key = values.get("tension_key")
        if key is None:
            return v
        if v != instruction_text(key, field.name):
            raise ValueError(
                f"§12 {field.name} is not the locked FR-003 string for {key!r}")
        return v


class Section13(_Closed):
    """One essay, 220-280 words, eight beats in the frozen order."""
    essay: StrictStr
    word_count: StrictInt
    beat_order: List[StrictStr]
    practice_sentence: StrictStr

    @validator("word_count")
    def _within_the_frozen_budget(cls, v, values):
        essay = values.get("essay")
        if essay is not None and v != len(essay.split()):
            raise ValueError("word_count must be the essay's own word count")
        if not 220 <= v <= 280:
            raise ValueError(f"§13 must be 220-280 words inclusive; got {v}")
        return v

    @validator("essay")
    def _one_essay_not_eight_cards(cls, v):
        if "\n\n" in v or v.lstrip().startswith("#"):
            raise ValueError("§13 is one joined essay with no headings")
        return v


class Section14(_Closed):
    lines: List[StrictStr]

    @validator("lines")
    def _locked_copy(cls, v):
        if tuple(v) != SECTION_14_COPY:
            raise ValueError("§14 must print the locked PDF copy verbatim")
        return v


class GlossaryEntry(_Closed):
    term: StrictStr
    meaning: StrictStr


class Section15(_Closed):
    entries: List[GlossaryEntry]

    @validator("entries")
    def _locked_glossary(cls, v):
        got = tuple((e.term, e.meaning) for e in v)
        if got != SECTION_15_GLOSSARY:
            raise ValueError("§15 must print the locked glossary verbatim")
        return v


class D12Report(_Closed):
    """The whole customer report: §§0-15, in order, once each."""
    publication_version: StrictStr = PUBLICATION_CONTRACT_VERSION
    format_spec_sha256: StrictStr = FORMAT_SPEC_SHA256
    chart_token: StrictStr
    calculation_meta: Dict[StrictStr, StrictStr]
    section_order: List[StrictInt] = list(SECTION_ORDER)
    section0: Section0
    section1: Section1
    section2: Section2
    section3: Section3
    section4: Section4
    section5: Section5
    section6: Section6
    section7: Section7
    section8: Section8
    section9: Section9
    section10: Section10
    section11: Section11
    section12: Section12
    section13: Section13
    section14: Section14
    section15: Section15

    @validator("section_order")
    def _canonical_order(cls, v):
        if tuple(v) != SECTION_ORDER:
            raise ValueError(f"sections must serialize in the order {SECTION_ORDER}")
        return v

    @validator("format_spec_sha256")
    def _the_frozen_spec(cls, v):
        if v != FORMAT_SPEC_SHA256:
            raise ValueError("the page contract is the frozen specification")
        return v

    @validator("section13")
    def _the_practice_is_the_winning_triad(cls, v, values):
        s12 = values.get("section12")
        if s12 is None:
            return v
        if v.practice_sentence != s12.practise:
            raise ValueError(
                "the §13 practice must be the winning FR-003 Practise sentence")
        if not v.essay.rstrip().endswith(v.practice_sentence):
            # CORR-01 · endswith, not substring presence.
            raise ValueError("the §13 essay must END on that practice sentence")
        return v

    @validator("section12")
    def _instructions_follow_the_selected_tension(cls, v, values):
        s11 = values.get("section11")
        if s11 is None:
            return v
        if s11.tension_key is None:
            raise ValueError(
                "the frozen page requires §12, and the fallback has no ratified "
                "triad; publication must fail closed rather than invent one")
        if v.tension_key != s11.tension_key:
            raise ValueError("§12 must serve the tension §11 selected")
        return v
