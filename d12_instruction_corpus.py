"""d12_instruction_corpus.py — FR-002 tension keys and the FR-003 corpus.

D12-005. Verbatim from D12_FR_002_004_LOCKED.md and D12_FR_003_005_LOCKED.md
(`0c18ba69…` and `d9a1fd8a…`). No generation, no paraphrase, no interpolation.

THE FALLBACK HAS NO INSTRUCTION SET, DELIBERATELY. FR-002 supplies an exact
fallback tension sentence; FR-003 supplies exactly four instruction triads, one
per tension. There is no authorised fifth triad, and the frozen Format
Specification supplies no independent fallback instruction rule. So the fallback
tension prints and Three Instructions are ABSENT — represented explicitly, never
filled with an invented set. Adding a fifth triad here would be manufacturing
doctrine; a Founder ruling is the only thing that may add one.
"""

from __future__ import annotations

from typing import Dict, Tuple

INSTRUCTION_CORPUS_VERSION = "d12-instructions-1.0"


class InstructionKeyError(KeyError):
    """An instruction lookup that does not resolve. Raised, never defaulted."""


# FR-002 · the waterfall, in the locked evaluation order. First TRUE wins.
TENSION_KEYS: Tuple[str, ...] = (
    "ketu_pull_vs_living_parents",
    "father_landmark_vs_mother_debt",
    "vihwala_climate_vs_ganesha_opening",
    "reliable_mercury_vs_loaded_saturn",
)

TENSION_TITLE: Dict[str, str] = {
    "ketu_pull_vs_living_parents": "Ketu-Pull vs. Living Parents",
    "father_landmark_vs_mother_debt": "Father as Landmark vs. Mother as Debt",
    "vihwala_climate_vs_ganesha_opening": "Vihwala Climate vs. Ganesha Opening",
    "reliable_mercury_vs_loaded_saturn": "Reliable Mercury vs. Loaded 4th-Lord Saturn",
}

# FR-002 · the exact fallback sentence when no trigger fires.
TENSION_FALLBACK = (
    "The static architecture balances formal inheritance with everyday "
    "domestic friction.")

# FR-003 · exactly four triads. Cultivate / Watch / Practise, verbatim.
INSTRUCTIONS: Dict[str, Dict[str, str]] = {
    "ketu_pull_vs_living_parents": {
        "cultivate": "Meet one living duty in the family field without "
                     "explaining it first.",
        "watch": "Searching the lineage for an emotional resolution that only "
                 "present, mundane care will settle.",
        "practise": "Once a month, name one inherited thread you will carry, "
                    "and one you will not.",
    },
    "father_landmark_vs_mother_debt": {
        "cultivate": "Honor structural stability where it stands without "
                     "demanding emotional warmth from a fixed landmark.",
        "watch": "Treating maternal emotional friction as a cosmic indictment "
                 "rather than a living bill to be cleared.",
        "practise": "Set a hard boundary between routine parental duty and "
                    "personal life-purpose every weekend.",
    },
    "vihwala_climate_vs_ganesha_opening": {
        "cultivate": "Lean into immediate, practical obstacle-removal rather "
                     "than mental over-elaboration.",
        "watch": "Letting an agitated search for meaning paralyze simple, "
                 "mundane beginnings.",
        "practise": "Take one concrete action on a stalled project before "
                    "attempting to rationalize its outcome.",
    },
    "reliable_mercury_vs_loaded_saturn": {
        "cultivate": "Rely on analytical articulation to untangle domestic "
                     "heavy grinds.",
        "watch": "Over-intellectualizing structural home burdens to escape "
                 "physical labor.",
        "practise": "Write down the single operational bottleneck in your "
                    "domestic or professional foundation and address it directly.",
    },
}

INSTRUCTION_SLOTS: Tuple[str, ...] = ("cultivate", "watch", "practise")


def instruction_text(tension_key: str, slot: str) -> str:
    """The one string a (tension, slot) pair is authorised to carry."""
    if tension_key not in INSTRUCTIONS:
        raise InstructionKeyError(
            f"{tension_key!r} has no authorised instruction triad; the fallback "
            f"has none by design and none may be invented")
    if slot not in INSTRUCTION_SLOTS:
        raise InstructionKeyError(f"unknown instruction slot {slot!r}")
    return INSTRUCTIONS[tension_key][slot]


def all_instruction_keys() -> Tuple[Tuple[str, str], ...]:
    """Every (tension, slot) pair. Finite and enumerable: 4 x 3 = 12."""
    return tuple((k, s) for k in TENSION_KEYS for s in INSTRUCTION_SLOTS)
