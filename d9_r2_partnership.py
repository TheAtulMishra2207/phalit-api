"""D9-R2 · d9_r2_partnership · Founder-locked Partnership Dynamics.

Three tiers, and the first two are UNIVERSAL — Section 3 exists on every valid
D9 report:

    1 · Relational Field    ← sign on the D9 7th house
    2 · Governing Function  ← D9 7th lord + published D9 dignity
    3 · Karmic Orientation  ← graha(s) in the 7th from Karakāṁśa · OPTIONAL

This supersedes the old rule under which Partnership existed only when a
Karakāṁśa H7 finding carried `confidence == "direct"`. Karakāṁśa H7 is now an
optional modifier, never the gate.

WHAT THIS SECTION IS ABOUT. The native's relational orientation and mature
capacity for enduring partnership. It never describes the spouse as an external
deterministic object — no appearance, caste, profession, health, morality,
origin, family wealth, divorce probability, number of marriages, or any date.

NO ARITHMETIC BEYOND WHOLE-SIGN COUNTING. No aspects, no rāśi dṛṣṭi, no
secondary lordship chains, and no independent dignity recomputation.
"""

from typing import Any, Dict, List, Optional, Sequence

SIGNS: Sequence[str] = (
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
)

# Ordinary Parashari sign lordship. No Rahu/Ketu co-lordship.
SIGN_LORDS: Dict[str, str] = {
    "Aries": "Mars", "Taurus": "Venus", "Gemini": "Mercury", "Cancer": "Moon",
    "Leo": "Sun", "Virgo": "Mercury", "Libra": "Venus", "Scorpio": "Mars",
    "Sagittarius": "Jupiter", "Capricorn": "Saturn", "Aquarius": "Saturn",
    "Pisces": "Jupiter",
}


class PartnershipUnresolved(RuntimeError):
    """Tier 2 could not resolve. Preparation fails closed rather than inventing
    a Neutral band or silently dropping the tier."""


# ═════════════════════════════════════════════════════════════════════════════
# TIER 1 · RELATIONAL FIELD · Founder corpus, verbatim
# ═════════════════════════════════════════════════════════════════════════════

RELATIONAL_FIELD: Dict[str, str] = {
    "Aries": (
        "Commitment works best when both people can act directly, retain "
        "healthy autonomy, and address friction without turning disagreement "
        "into a contest of will."),
    "Taurus": (
        "Commitment works best through emotional and structural steadiness, "
        "dependable routines, and a shared sense that what is being built will "
        "endure."),
    "Gemini": (
        "Commitment works best through explicit communication, intellectual "
        "flexibility, and the freedom to keep learning about one another "
        "without losing consistency."),
    "Cancer": (
        "Commitment works best where emotional safety, care, and protective "
        "belonging are strong without either person becoming responsible for "
        "the other's entire emotional world."),
    "Leo": (
        "Commitment works best through loyalty, dignity, visible appreciation, "
        "and a shared willingness to protect the relationship without making "
        "validation its centre."),
    "Virgo": (
        "Commitment works best through practical reliability, clear "
        "responsibilities, thoughtful correction, and care expressed in "
        "useful, repeatable ways."),
    "Libra": (
        "Commitment works best through fairness, reciprocity, balanced "
        "agreements, and the ability to preserve harmony without sacrificing "
        "necessary truth or boundaries."),
    "Scorpio": (
        "Commitment works best where trust is deep enough for difficult "
        "truths, emotional intensity can be faced directly, and vulnerability "
        "does not have to be managed through secrecy or control."),
    "Sagittarius": (
        "Commitment works best through shared principles, room for growth, "
        "honest perspective, and a sense that the union supports a larger "
        "direction without becoming doctrinaire."),
    "Capricorn": (
        "Commitment works best through accountability, reliability, "
        "long-horizon planning, and a willingness to carry duty without "
        "allowing the relationship to harden into mere obligation."),
    "Aquarius": (
        "Commitment works best through equality, friendship, intellectual "
        "freedom, and shared ideals while preserving enough personal "
        "engagement that detachment does not replace intimacy."),
    "Pisces": (
        "Commitment works best through compassion, receptivity, and a sense of "
        "emotional or spiritual connection held inside clear boundaries and "
        "practical responsibility."),
}


# ═════════════════════════════════════════════════════════════════════════════
# TIER 2 · GOVERNING FUNCTION · three bands, no scores
# ═════════════════════════════════════════════════════════════════════════════
#
# The dignity describes the NATIVE'S governing relational function. It is never
# a quality rating of a marriage or of a spouse.

CAPACITY_BANDS: Dict[str, str] = {
    "strong": (
        "There is strong capacity to maintain relational agreements, navigate "
        "compromise without resentment, and sustain mutual respect."),
    "workable": (
        "Relational equilibrium is workable, but harmony depends on deliberate "
        "effort, clear communication, and continued mutual alignment."),
    "frontier": (
        "Partnership becomes a significant growth frontier, especially around "
        "boundaries, projected expectations, compromise, and the management of "
        "relational strain."),
}

# Published dignity → band. Moolatrikona is already normalised into Own Sign by
# the publication wall; it is accepted here only for robustness and never
# recomputed.
DIGNITY_BAND: Dict[str, str] = {
    "Exalted": "strong",
    "Own Sign": "strong",
    "Moolatrikona": "strong",
    "Friendly Sign": "workable",
    "Neutral Sign": "workable",
    "Enemy Sign": "frontier",
    "Debilitated": "frontier",
}


# ═════════════════════════════════════════════════════════════════════════════
# TIER 3 · KARMIC ORIENTATION · optional, occupancy-driven
# ═════════════════════════════════════════════════════════════════════════════

ORIENTATION_INDIVIDUAL: Dict[str, str] = {
    "Jupiter": (
        "You are instinctively drawn toward partnership that supports meaning, "
        "sound counsel, and the work you consider worth doing."),
    "Venus": (
        "You are strongly drawn toward aesthetic and emotional harmony in "
        "union."),
    "Rahu": (
        "You are drawn toward unconventional relationship patterns or forms of "
        "partnership that do not fit the expected template."),
    "Ketu": (
        "You are drawn toward spiritual detachment or unconventional "
        "independence within union, even when the bond itself is important."),
}

# Category clauses emit ONCE however many members occupy the house.
ORIENTATION_CATEGORY: Dict[str, Dict[str, Any]] = {
    "benefic": {
        "members": ("Moon", "Mercury"),
        "text": ("You are instinctively drawn toward partnership that feels "
                 "cooperative, constructive, and supportive rather than "
                 "adversarial."),
    },
    "friction": {
        "members": ("Sun", "Mars", "Saturn"),
        "text": ("Partnership carries an instinctive tolerance for friction; "
                 "enduring union requires that conflict be worked directly "
                 "rather than allowed to harden."),
    },
}

# Order of emission, so multi-occupant output is deterministic.
ORIENTATION_ORDER = ("Jupiter", "Venus", "benefic", "Rahu", "Ketu", "friction")


# ═════════════════════════════════════════════════════════════════════════════
# BUILD
# ═════════════════════════════════════════════════════════════════════════════

def seventh_sign(d9_lagna_sign_index: int) -> str:
    """Whole-sign 7th from the certified D9 Lagna. Nothing else."""
    if not isinstance(d9_lagna_sign_index, int) or isinstance(d9_lagna_sign_index, bool):
        raise PartnershipUnresolved("certified D9 Lagna sign index is missing")
    return SIGNS[(d9_lagna_sign_index + 6) % 12]


def build_partnership(d9_lagna_sign_index: int,
                      published_dignity: Dict[str, str],
                      karakamsha_h7_occupants: Optional[Sequence[str]] = None,
                      karakamsha_h7_sign: Optional[str] = None) -> Dict[str, Any]:
    """Section 3. Tiers 1 and 2 are mandatory; tier 3 appears only if occupied.

    `published_dignity` is the already-certified published band. Dignity is
    never recomputed here.
    """
    field_sign = seventh_sign(d9_lagna_sign_index)
    field_text = RELATIONAL_FIELD.get(field_sign)
    if not field_text:
        raise PartnershipUnresolved(f"no relational field for {field_sign!r}")

    lord = SIGN_LORDS.get(field_sign)
    if not lord:
        raise PartnershipUnresolved(f"no classical lord for {field_sign!r}")

    dignity = (published_dignity or {}).get(lord)
    band = DIGNITY_BAND.get(dignity) if dignity else None
    if not band:
        # FAIL CLOSED. Never invent Neutral, never drop the tier silently.
        raise PartnershipUnresolved(
            f"published D9 dignity for the 7th lord {lord} is missing or "
            f"unrecognised ({dignity!r})")

    out: Dict[str, Any] = {
        "heading": "Partnership Dynamics",
        "relational_field": {"sign": field_sign, "statement": field_text},
        "governing_function": {"graha": lord, "dignity": dignity,
                               "statement": CAPACITY_BANDS[band]},
    }

    orientation = build_karmic_orientation(karakamsha_h7_occupants)
    if orientation:
        out["karmic_orientation"] = orientation
    return out


def build_karmic_orientation(occupants: Optional[Sequence[str]]) -> List[Dict[str, str]]:
    """Distinct signals preserved, category-equivalents deduplicated.

    Jupiter + Venus emits two clauses. Moon + Mercury emits ONE benefic clause.
    Mars + Saturn emits ONE friction clause. An empty house emits nothing at
    all — there is no lordship fallback and no empty card.
    """
    present = [g for g in (occupants or []) if g]
    if not present:
        return []

    emitted: List[Dict[str, str]] = []
    for key in ORIENTATION_ORDER:
        if key in ORIENTATION_INDIVIDUAL:
            if key in present:
                emitted.append({"graha": key, "statement": ORIENTATION_INDIVIDUAL[key]})
        else:
            cat = ORIENTATION_CATEGORY[key]
            members = [g for g in cat["members"] if g in present]
            if members:
                emitted.append({"graha": " · ".join(members),
                                "statement": cat["text"]})
    return emitted


def build_partnership_basis(partnership: Dict[str, Any],
                            karakamsha_h7_sign: Optional[str],
                            occupants: Optional[Sequence[str]]) -> str:
    """The customer-facing reading-basis line. No internal rule ids."""
    rf = partnership["relational_field"]
    gf = partnership["governing_function"]
    line = (f"D9 7th house {rf['sign']} · 7th lord {gf['graha']} "
            f"{gf['dignity']}")
    if occupants:
        line += f" · Karakāṁśa 7th {' · '.join(occupants)}"
    return line
