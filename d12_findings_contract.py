"""d12_findings_contract.py — typed deterministic outputs for D12 §§5-9.

D12-004. Every text field carries the corpus key that produced it and the input
state that selected it, so QA can trace

    output sentence -> exact corpus key -> deterministic input state

without reading a provider prompt. There is no open-ended prose field anywhere
in this module: `text` is always a value drawn from d12_corpus, and `basis`
records why.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from pydantic import BaseModel, Extra, StrictBool, StrictInt, StrictStr, conint, validator

from d12_corpus import (
    BUCKETS, CATEGORIES, CORPUS_VERSION, DEVATA_GLOSS, D12_DEITIES, D12_HIDDEN,
    ELEMENTS, KARAKA_FAMILIES, S6_BESPOKE, S8_DOMAINS, S8_TUPLES,
    SPEAKER_FAMILIES, SPEAKER_PARENT, STRUCTURAL_CLASSES,
    CorpusKeyError, text_for_key,
)

# ─────────────────────────────────────────────────────────────────────────────
# CORR-02 · SEMANTIC BINDING TABLES
#
# CORR-01 closed "a valid key may carry only its own text". QA then showed the
# remaining hole: the right sentence could still be filed under the wrong
# section, the wrong speaker, or an unrelated climate ledger. These tables bind
# the metadata to the key, so a Finding cannot be misfiled even when its text is
# perfectly canonical.
#
# Derived from the corpus, never hand-listed, so a corpus edit cannot leave a
# stale duplicate behind. The coverage assertion below fails at import if a new
# bespoke cell ever arrives without an authorised speaker.
# ─────────────────────────────────────────────────────────────────────────────

CANONICAL_SPEAKER_KEY = {"S5": "inheritance", "S7": "unpaid_pattern"}

_BESPOKE_PREFIX_TO_FAMILY = {
    "sun_karaka.": "Sun Karaka",
    "moon_karaka.": "Moon Karaka",
    "h9_lord.": "D12 H9 Lord",
    "h4_occupied.": "D12 H4 Lord",
}

S6_BESPOKE_FAMILY: Dict[str, str] = {}
for _cell in S6_BESPOKE:
    for _prefix, _family in _BESPOKE_PREFIX_TO_FAMILY.items():
        if _cell.startswith(_prefix):
            S6_BESPOKE_FAMILY[_cell] = _family
            break
if set(S6_BESPOKE_FAMILY) != set(S6_BESPOKE):          # import-time coverage gate
    raise RuntimeError(
        "every §6 bespoke cell must have an authorised speaker family; "
        f"unmapped: {sorted(set(S6_BESPOKE) - set(S6_BESPOKE_FAMILY))}")

FATHER_FAMILIES = tuple(f for f in SPEAKER_FAMILIES if SPEAKER_PARENT[f] == "Father")
MOTHER_FAMILIES = tuple(f for f in SPEAKER_FAMILIES if SPEAKER_PARENT[f] == "Mother")

FINDINGS_CONTRACT_VERSION = "d12-findings-1.0"

HouseNumber = conint(strict=True, ge=1, le=12)
SliceNumber = conint(strict=True, ge=1, le=12)


class _Closed(BaseModel):
    class Config:
        extra = Extra.forbid
        allow_mutation = False


class Finding(_Closed):
    """One traceable deterministic sentence."""
    section_id: StrictStr
    speaker_key: StrictStr
    corpus_key: StrictStr
    text: StrictStr
    basis: Dict[str, StrictStr]

    @validator("section_id")
    def _known_section(cls, v):
        if v not in ("S5", "S6", "S7"):
            raise ValueError(f"unknown section_id {v!r}")
        return v

    @validator("text")
    def _text_is_not_empty(cls, v):
        if not v.strip():
            raise ValueError("text must not be empty")
        return v

    @validator("corpus_key")
    def _key_section_matches_the_declared_section(cls, v, values):
        """CORR-02 · a valid sentence filed under the wrong section fails here.
        The key's own prefix is the authority; section_id must agree with it."""
        section = values.get("section_id")
        if section is None:                  # section_id already failed
            return v
        if not isinstance(v, str) or "." not in v:
            raise ValueError(f"malformed corpus_key {v!r}")
        prefix = v.split(".", 1)[0]
        if prefix != section:
            raise ValueError(
                f"corpus_key {v!r} belongs to section {prefix}, not {section}")
        return v

    @validator("speaker_key")
    def _speaker_key_is_canonical_for_the_section(cls, v, values):
        """CORR-02 · §5 and §7 have exactly one speaker each; §6 speakers must
        be one of the six frozen families."""
        section = values.get("section_id")
        if section is None:
            return v
        if section in CANONICAL_SPEAKER_KEY:
            expected = CANONICAL_SPEAKER_KEY[section]
            if v != expected:
                raise ValueError(
                    f"{section} speaker_key must be {expected!r}, got {v!r}")
        elif section == "S6" and v not in SPEAKER_FAMILIES:
            raise ValueError(f"§6 speaker_key {v!r} is not a frozen family")
        return v

    @validator("text")
    def _text_is_exactly_what_the_key_authorises(cls, v, values):
        """CORR-01 · the contract closure QA required.

        A valid corpus key may carry ONLY the text authorised for that key.
        Resolution goes through d12_corpus.text_for_key, which reads the same
        registries the selectors read — there is no second copy of any string,
        so a corpus edit moves the emitted and the expected sentence together.

        Exact equality, deliberately: a one-character alteration, an added
        space, provider prose, or another key's text all fail here. This is the
        boundary that makes "output sentence -> corpus key -> input state"
        a guarantee rather than a convention.
        """
        key = values.get("corpus_key")
        if key is None:                      # corpus_key already failed; don't mask it
            return v
        try:
            expected = text_for_key(key)
        except CorpusKeyError as exc:
            raise ValueError(str(exc))
        if v != expected:
            raise ValueError(
                f"text does not match the locked corpus string for {key!r}")
        return v


class Section5(_Closed):
    """§5 · The inheritance you met. Exactly one finding."""
    lagna_sign: StrictStr
    lagna_element: StrictStr
    lagnesh: StrictStr
    lagnesh_house: HouseNumber
    house_category: StrictStr
    dignity_bucket: StrictStr
    bespoke: StrictBool
    finding: Finding

    @validator("lagna_element")
    def _element(cls, v):
        if v not in ELEMENTS:
            raise ValueError(f"unknown element {v!r}")
        return v

    @validator("house_category")
    def _category(cls, v):
        if v not in CATEGORIES:
            raise ValueError(f"unknown house category {v!r}")
        return v

    @validator("dignity_bucket")
    def _bucket(cls, v):
        if v not in BUCKETS:
            raise ValueError(f"unknown dignity bucket {v!r}")
        return v

    @validator("finding")
    def _finding_belongs_to_this_section_and_matches_its_state(cls, v, values):
        """CORR-02 · key-to-metadata consistency. No astrology is recomputed
        here: the contract only checks that the key the selector chose agrees
        with the state the selector reported alongside it."""
        if v.section_id != "S5":
            raise ValueError(f"Section5 requires an S5 finding, got {v.section_id}")
        bespoke = values.get("bespoke")
        if bespoke is None:
            return v
        if bespoke and not v.corpus_key.startswith("S5.bespoke."):
            raise ValueError("bespoke=True requires an S5.bespoke.* key")
        if not bespoke:
            if not v.corpus_key.startswith("S5.fallback."):
                raise ValueError("bespoke=False requires an S5.fallback.* key")
            parts = v.corpus_key[len("S5.fallback."):].split(".")
            if len(parts) != 3:
                raise ValueError(f"malformed §5 fallback key {v.corpus_key!r}")
            element, category, bucket = parts
            for name, from_key, from_state in (
                    ("element", element, values.get("lagna_element")),
                    ("house category", category, values.get("house_category")),
                    ("dignity bucket", bucket, values.get("dignity_bucket"))):
                if from_state is not None and from_key != from_state:
                    raise ValueError(
                        f"§5 fallback key {name} {from_key!r} disagrees with the "
                        f"section state {from_state!r}")
        return v


class SpeakerFinding(_Closed):
    """§6 · one speaker, kept strictly separate from every other speaker."""
    family: StrictStr
    parent: StrictStr
    subject: Optional[StrictStr]
    house: Optional[HouseNumber]
    house_category: Optional[StrictStr]
    element: Optional[StrictStr]
    dignity_bucket: Optional[StrictStr]
    structural_class: Optional[StrictStr]
    bespoke: StrictBool
    finding: Finding

    @validator("family")
    def _family(cls, v):
        if v not in SPEAKER_FAMILIES:
            raise ValueError(f"unknown speaker family {v!r}")
        return v

    @validator("parent")
    def _parent(cls, v):
        if v not in ("Father", "Mother"):
            raise ValueError(f"unknown parent {v!r}")
        return v

    @validator("parent")
    def _parent_matches_the_frozen_family_membership(cls, v, values):
        """CORR-02 · a family cannot migrate parents by changing this string."""
        family = values.get("family")
        if family is not None and SPEAKER_PARENT[family] != v:
            raise ValueError(
                f"{family!r} belongs to {SPEAKER_PARENT[family]}, not {v}")
        return v

    @validator("structural_class")
    def _structural(cls, v):
        if v is not None and v not in STRUCTURAL_CLASSES:
            raise ValueError(f"unknown structural class {v!r}")
        return v

    @validator("finding")
    def _finding_belongs_to_this_speaker(cls, v, values):
        """CORR-02 · the finding must be an §6 finding spoken by THIS family.

        For a fallback, the key's own speaker segment must match. For a bespoke
        cell, the cell is bound to its authorised family — so no Karaka cell can
        validate under a lord speaker, whatever the text says.
        """
        family = values.get("family")
        if v.section_id != "S6":
            raise ValueError(f"Section6 requires an S6 finding, got {v.section_id}")
        if family is None:
            return v
        if v.speaker_key != family:
            raise ValueError(
                f"finding speaker_key {v.speaker_key!r} is not the family {family!r}")
        if v.corpus_key.startswith("S6.fallback."):
            key_family = v.corpus_key[len("S6.fallback."):].split(".")[0]
            if key_family != family:
                raise ValueError(
                    f"§6 fallback key speaks for {key_family!r}, not {family!r}")
        elif v.corpus_key.startswith("S6.bespoke."):
            cell = v.corpus_key[len("S6.bespoke."):]
            authorised = S6_BESPOKE_FAMILY.get(cell)
            if authorised is None:
                raise ValueError(f"unknown §6 bespoke cell {cell!r}")
            if authorised != family:
                raise ValueError(
                    f"§6 bespoke cell {cell!r} is authorised for {authorised!r}, "
                    f"not {family!r}")
        bespoke = values.get("bespoke")
        if bespoke is not None:
            if bespoke and not v.corpus_key.startswith("S6.bespoke."):
                raise ValueError("bespoke=True requires an S6.bespoke.* key")
            if not bespoke and not v.corpus_key.startswith("S6.fallback."):
                raise ValueError("bespoke=False requires an S6.fallback.* key")
        return v


class Section6(_Closed):
    """§6 · Father & Mother. Six speakers, never merged into one sentence."""
    father: List[SpeakerFinding]
    mother: List[SpeakerFinding]

    @validator("father")
    def _father_is_exactly_the_three_frozen_paternal_families(cls, v):
        """CORR-02 · six unique families is not enough: the previous check
        passed a set where Moon Karaka sat under father and Sun Karaka under
        mother. Membership is frozen, in order."""
        if tuple(s.family for s in v) != FATHER_FAMILIES:
            raise ValueError(
                f"father must be exactly {list(FATHER_FAMILIES)}, "
                f"got {[s.family for s in v]}")
        return v

    @validator("mother")
    def _mother_is_exactly_the_three_frozen_maternal_families(cls, v):
        if tuple(s.family for s in v) != MOTHER_FAMILIES:
            raise ValueError(
                f"mother must be exactly {list(MOTHER_FAMILIES)}, "
                f"got {[s.family for s in v]}")
        return v


class Section7(_Closed):
    """§7 · The unpaid pattern. Exactly one finding, never silent."""
    h6_occupants: List[StrictStr]
    h6_lord: StrictStr
    h6_lord_house: HouseNumber
    baseline_applied: StrictBool
    unproven_predicates: List[StrictStr]
    finding: Finding

    @validator("finding")
    def _finding_matches_the_declared_baseline_state(cls, v, values):
        """CORR-02 · baseline_applied and the corpus key are one fact stated
        twice; they may not disagree."""
        if v.section_id != "S7":
            raise ValueError(f"Section7 requires an S7 finding, got {v.section_id}")
        baseline = values.get("baseline_applied")
        if baseline is None:
            return v
        if baseline and v.corpus_key != "S7.baseline":
            raise ValueError("baseline_applied=True requires the S7.baseline key")
        if not baseline and not v.corpus_key.startswith("S7.cell."):
            raise ValueError("baseline_applied=False requires an S7.cell.* key")
        return v


class ResidueDomain(_Closed):
    """§8 · one permitted residue house. Domain-constant clause."""
    house: HouseNumber
    visible_label: StrictStr
    subjects: List[StrictStr]
    constant_clause: StrictStr

    @validator("house")
    def _permitted(cls, v):
        if v not in S8_DOMAINS:
            raise ValueError(f"house {v} is not a permitted §8 residue domain")
        return v

    @validator("constant_clause")
    def _house_label_and_clause_are_one_indivisible_tuple(cls, v, values):
        """CORR-01 · §8 closure. The three fields are validated together, not
        independently: H6 cannot carry the H8 clause, and no house can carry an
        internal identifier as its visible label."""
        house = values.get("house")
        label = values.get("visible_label")
        if house is None or label is None:   # an earlier field already failed
            return v
        if (house, label, v) not in S8_TUPLES:
            raise ValueError(
                f"(house {house}, label {label!r}, clause) is not one of the "
                f"seven locked §8 domain tuples")
        return v


class Section8(_Closed):
    """§8 · What you are still carrying. Exactly the seven permitted domains."""
    domains: List[ResidueDomain]

    @validator("domains")
    def _exactly_seven_in_order(cls, v):
        if [d.house for d in v] != list(S8_DOMAINS):
            raise ValueError("§8 must carry exactly houses 2,5,6,7,8,11,12 in order")
        return v


class DevataImprint(_Closed):
    """§9 · one subject's Devatā imprint. Primary is customer-facing; hidden is
    internal and remains available for the later FR-002 counting."""
    subject: StrictStr
    slice: SliceNumber
    primary_deity: StrictStr
    hidden_deity: StrictStr
    display_name: StrictStr
    hidden_is_internal_only: StrictBool = True

    @validator("primary_deity")
    def _primary_is_the_one_the_slice_determines(cls, v, values):
        """CORR-02 · the imprint is a deterministic tuple, not three free
        fields. The slice decides both deities; neither may be substituted."""
        slice_no = values.get("slice")
        if slice_no is None:
            return v
        expected = D12_DEITIES[slice_no - 1]
        if v != expected:
            raise ValueError(
                f"slice {slice_no} determines primary {expected!r}, got {v!r}")
        return v

    @validator("hidden_deity")
    def _hidden_is_the_one_the_slice_determines(cls, v, values):
        if v not in D12_HIDDEN:
            raise ValueError(f"unknown hidden deity {v!r}")
        slice_no = values.get("slice")
        if slice_no is None:
            return v
        expected = D12_HIDDEN[slice_no - 1]
        if v != expected:
            raise ValueError(
                f"slice {slice_no} determines hidden {expected!r}, got {v!r}")
        return v

    @validator("display_name")
    def _display_is_the_primary_alone(cls, v, values):
        # FR-005: with no approved compound clause, the customer-facing name is
        # the primary deity alone. A compound display is a contract violation.
        if v != values.get("primary_deity"):
            raise ValueError("display_name must be the primary deity alone")
        return v

    @validator("hidden_is_internal_only")
    def _the_hidden_deity_stays_internal(cls, v):
        """CORR-02 · an invariant of this flight, not a toggle. The hidden
        imprint is available to later selectors and never published."""
        if v is not True:
            raise ValueError("hidden_is_internal_only must be True")
        return v


class DevataClimate(_Closed):
    """One collapsed climate record. Repeats become ONE record with a count —
    Vihwala never prints four repetitive descriptions."""
    deity: StrictStr
    count: StrictInt
    subjects: List[StrictStr]
    gloss: Optional[StrictStr]

    @validator("deity")
    def _deity_is_in_the_known_vocabulary(cls, v):
        """CORR-02 · a climate may only name a deity the D12 tables produce."""
        if v not in set(D12_DEITIES) | set(D12_HIDDEN):
            raise ValueError(f"{v!r} is not a D12 primary or hidden deity")
        return v

    @validator("count")
    def _count_is_at_least_one(cls, v):
        if v < 1:
            raise ValueError(
                f"a climate record must collapse at least one imprint, got {v}")
        return v

    @validator("subjects")
    def _subjects_are_present_unique_and_counted(cls, v, values):
        if not v:
            raise ValueError("a climate must name at least one subject")
        if len(set(v)) != len(v):
            raise ValueError(f"climate subjects must be unique, got {v}")
        count = values.get("count")
        if count is not None and count != len(v):
            raise ValueError(f"count {count} disagrees with {len(v)} subjects")
        return v

    @validator("gloss")
    def _only_approved_glosses(cls, v, values):
        deity = values.get("deity")
        if v is None:
            if deity in DEVATA_GLOSS:
                raise ValueError(f"{deity!r} has an approved gloss and must carry it")
            return v
        if deity not in DEVATA_GLOSS or DEVATA_GLOSS[deity] != v:
            raise ValueError(f"gloss for {deity!r} is not the Founder string")
        return v


class Section9(_Closed):
    """§9 · Devatā climate. Imprints plus collapsed climates plus the raw counts
    FR-002 will consume later. No tension winner is computed here."""
    imprints: List[DevataImprint]
    primary_climates: List[DevataClimate]
    hidden_climates: List[DevataClimate]
    primary_counts: Dict[StrictStr, StrictInt]
    hidden_counts: Dict[StrictStr, StrictInt]

    @validator("primary_climates", "hidden_climates")
    def _one_record_per_deity(cls, v):
        names = [c.deity for c in v]
        if len(names) != len(set(names)):
            raise ValueError("repeated deity imprints must collapse into one record")
        return v

    @validator("primary_climates", "hidden_climates")
    def _climates_are_the_collapse_of_the_supplied_imprints(cls, v, values, field):
        """CORR-02 · the ledger must BE the collapse of THESE imprints, not an
        unrelated tally that merely looks well-formed."""
        imprints = values.get("imprints")
        if imprints is None:
            return v
        attr = ("primary_deity" if field.name == "primary_climates"
                else "hidden_deity")
        expected: Dict[str, List[str]] = {}
        for im in imprints:
            expected.setdefault(getattr(im, attr), []).append(im.subject)
        if {c.deity for c in v} != set(expected):
            raise ValueError(
                f"{field.name} name {sorted(c.deity for c in v)}, but the "
                f"imprints carry {sorted(expected)}")
        for c in v:
            if sorted(c.subjects) != sorted(expected[c.deity]):
                raise ValueError(
                    f"{field.name}: {c.deity!r} collapses "
                    f"{sorted(expected[c.deity])}, got {sorted(c.subjects)}")
        return v

    @validator("primary_counts", "hidden_counts")
    def _counts_agree_with_the_climate_ledger(cls, v, values, field):
        key = ("primary_climates" if field.name == "primary_counts"
               else "hidden_climates")
        climates = values.get(key)
        if climates is None:
            return v
        expected = {c.deity: c.count for c in climates}
        if v != expected:
            raise ValueError(
                f"{field.name} {v} disagrees with the {key} ledger {expected}")
        return v


class D12Findings(_Closed):
    """The full deterministic §§5-9 layer."""
    findings_version: StrictStr = FINDINGS_CONTRACT_VERSION
    corpus_version: StrictStr = CORPUS_VERSION
    section5: Section5
    section6: Section6
    section7: Section7
    section8: Section8
    section9: Section9
