"""D7-002-CORR-05 · the FD-1E atomic clause registry, weights and selection.

WEIGHTS ARE LOCKED. The Founder tier table is reproduced exactly and the
triangulation multiplier is exactly 1.0, so:

    Effective_Weight = Base_Weight × 1.0 = Base_Weight

`weight_for` raises on any tier outside the table rather than defaulting, so a
typo fails the build instead of silently scoring zero.

THE REGISTRY HOLDS 33 ATOMIC CLAUSES — 11 Conception, 11 Lineage, 11 Bond —
each with its exact Founder ID, condition, state and signed Base Weight.
Clauses are NEVER collapsed into a composite: three fired clauses in a state
must accumulate more evidence than one, and a composite erases that difference.

Each clause also declares the Founder ANCHORS its condition explicitly names
(5H, 5L, 9H, 9L, Jupiter, 7H, 7L, Venus). The FD-2A parental vectors are DERIVED
from those anchors, never hand-assigned, so a clause cannot be placed in a
bucket its condition does not name.

Predicates are THREE-VALUED. `None` means a primitive is unavailable and is
recorded as UNRESOLVED, never coerced to False. Negation goes through `_not3`,
because Python's `not None` is True and would turn an unavailable primitive
into positive evidence.
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

# ─── addendum §A · the locked tier table ─────────────────────────────────────

WEIGHT_TIERS: Dict[str, float] = {
    "MAJOR_PRIMARY_YOGA": 2.0,
    "STANDARD_BENEFIC_SIGNAL": 1.5,
    "MINOR_ELEMENTAL_SIGNAL": 1.0,
    "NEUTRAL_STRUCTURAL": 0.0,
    "MILD_NEGATIVE_FRICTION": -1.0,
    "STANDARD_MALEFIC_AFFLICTION": -1.5,
    "SEVERE_MALEFIC_AFFLICTION": -2.0,
}

# Locked at exactly 1.0 by the addendum. Named rather than inlined so a test can
# assert the value and so any future change is a one-line, reviewable diff.
WEIGHT_MULTIPLIER = 1.0

UNRESOLVED = "UNRESOLVED_FOUNDER_PRIMITIVE"


def weight_for(tier: str) -> float:
    if tier not in WEIGHT_TIERS:
        raise KeyError(f"unknown weight tier {tier!r}; the tier table is closed")
    return WEIGHT_TIERS[tier]


def effective_weight(tier: str) -> float:
    return weight_for(tier) * WEIGHT_MULTIPLIER


# ─── the 15 state slots ──────────────────────────────────────────────────────
#
# Three archetypes × five states. Only three state NAMES were supplied, in the
# Founder format document, and each of those is the state that one example chart
# selected. The other twelve are unnamed and are held as slots rather than
# invented.

ARCHETYPES: Tuple[str, str, str] = (
    "conception_path",
    "lineage_trajectory",
    "bond_dynamics",
)

ARCHETYPE_TITLES = {
    "conception_path": "Conception & Family Planning Path",
    "lineage_trajectory": "Lineage Scope & Arrival Trajectory",
    "bond_dynamics": "Parent-Child Bond & Dynamics",
}

STATE_LETTERS = ("A", "B", "C", "D", "E")

# name = supplied by the Founder format; None = not supplied, held as a slot.
# CORR-02 · Founder-locked. Dev may not rename any state.
STATE_NAMES: Dict[str, Dict[str, str]] = {
    "conception_path": {
        "A": "Abundant Fertility",
        "B": "Balanced Lineage",
        "C": "Karmic Delay & Steady Preparation",
        "D": "Assisted Conception",
        "E": "Biological Block / Spiritual Focus",
    },
    "lineage_trajectory": {
        "A": "Expansive Lineage",
        "B": "Compact Continuity",
        "C": "Delayed Bloom",
        "D": "Unconventional Trajectory",
        "E": "Sequence Interrupted",
    },
    "bond_dynamics": {
        "A": "Devotional & Noble Bond",
        "B": "Intellectual & Dynamic",
        "C": "Sensitive & Artistic",
        "D": "Detached & Independent",
        "E": "Karmic Friction",
    },
}

# CORR-02 · spec K. These three engine states must NEVER reach a customer or a
# provider as a raw label. They exist internally only; the publication layer
# maps them out and the scanner rejects them if they ever appear.
INTERNAL_ONLY_STATE_NAMES = frozenset({
    "Assisted Conception",
    "Biological Block",
    "Biological Block / Spiritual Focus",
})

NO_DOMINANT = "No Dominant Signature"


@dataclass(frozen=True)
class Rule:
    """One Founder rule.

    `predicate` returns True (fired), False (did not fire) or None. None means
    the rule depends on a primitive the Founder has not yet defined; it is
    recorded as UNRESOLVED and is NEVER coerced to False, because a silent False
    would let an unresolved adverse rule read as an absent one.
    """
    rule_id: str
    archetype: str
    state: str
    tier: str
    description: str
    predicate: Callable[[Dict[str, Any]], Optional[bool]]
    unresolved_reason: str = ""

    def effective_weight(self) -> float:
        return effective_weight(self.tier)


REGISTRY: List[Rule] = []

# ─── the Founder rule table · spec D, one rule per state ─────────────────────
#
# Each state fires on the EXACT boolean composition the ticket states. The
# composition is expressed as a callable over the FD-1B surface so the formula
# is readable next to the spec, and so no state can quietly compute a term of
# its own.
#
# `house_vector` is the spec-H signed-bucket anchor:
#   5 = anchored to 5H/5L · 9 = to 9H/9L/Jupiter · 7 = to 7H/7L/Venus

def _f(s, k):
    """Read one FD-1B term. None propagates as UNRESOLVED, never as False."""
    return s.get(k)


def _not3(v):
    """Three-valued negation.

    Python's `not None` is True, so `not _f(surface, term)` silently turned an
    UNAVAILABLE primitive into POSITIVE evidence. Every atomic clause that
    negates a possibly-three-valued term uses this instead.
    """
    if v is None:
        return None
    return not v


def _all(*vals):
    """AND with three-valued logic: any None with no False present -> None."""
    if any(v is False for v in vals):
        return False
    if any(v is None for v in vals):
        return None
    return True


def _any(*vals):
    if any(v is True for v in vals):
        return True
    if any(v is None for v in vals):
        return None
    return False


# ─── CORR-04 · FD-1E · THE 33 ATOMIC CLAUSES ────────────────────────────────
#
# One record per Founder clause ID. Clauses are NEVER collapsed into a composite
# rule: three fired clauses in a state must accumulate more evidence than one,
# and a composite would erase that difference entirely.
#
# Columns: id · state · base weight · condition · predicate · vector bucket
#
# The signed Base Weight is written here as a NUMBER, taken from the Founder
# table, and the tier name is derived from it. That direction matters: the
# ticket's authority is the weight column, so the weight is the literal and the
# tier is the label, not the other way round.

_WEIGHT_TO_TIER = {v: k for k, v in WEIGHT_TIERS.items()}


def _tier_for(weight: float) -> str:
    if weight not in _WEIGHT_TO_TIER:
        raise KeyError(f"weight {weight!r} is not a Founder tier value")
    return _WEIGHT_TO_TIER[weight]


_SPEC = [
    # ── Module 1 · Conception & Family Planning · 11 clauses ────────────────
    ("D7_CON_A1", "conception_path", "A", +2.0,
     "D7 Lagna Lord Well-Placed in Kendra/Trikona",
     lambda s: _all(_f(s, "well_placed_lagna_lord"),
                    _f(s, "lagna_lord_in_kendra_trikona")), ()),
    # CORR-05 · this clause is about the SPHUTA. It previously read 5H and
    # lagna-lord affliction, so an afflicted Sphuta with a clean 5H fired it.
    ("D7_CON_A2", "conception_path", "A", +1.5,
     "Optimal Beeja/Kshetra polarity with no malefic affliction of the Sphuta",
     lambda s: _all(_f(s, "sphuta_optimal_polarity"),
                    _not3(_f(s, "afflicted_sphuta"))), ()),
    # CORR-05 · the exact FD-1E condition, not the generic Afflicted negation.
    ("D7_CON_B1", "conception_path", "B", +1.5,
     "D7 Lagna Lord Unafflicted: outside 6/8/12 and no direct malefic aspect",
     lambda s: _f(s, "lagna_lord_fd1e_unafflicted"), ()),
    # CORR-05 · Benefic Relief of the 5L, not of the 5th house.
    ("D7_CON_B2", "conception_path", "B", +1.5,
     "D7 5L Standard Placement with Benefic Relief of the 5L",
     lambda s: _all(_f(s, "standard_5l_placement"),
                    _f(s, "benefic_relief_5l")), ("5L",)),
    ("D7_CON_C1", "conception_path", "C", -1.5,
     "Saturn Graha Drishti onto D7 Lagna or D7 5H",
     lambda s: _f(s, "saturn_aspects_lagna_or_5h"), ('5H',)),
    ("D7_CON_C2", "conception_path", "C", -1.0,
     "Sphuta in Capricorn/Aquarius",
     lambda s: _f(s, "sphuta_in_saturnian_sign"), ()),
    ("D7_CON_C3", "conception_path", "C", -1.0,
     "Non-optimal Beeja/Kshetra polarity",
     lambda s: _not3(_f(s, "sphuta_optimal_polarity")), ()),
    ("D7_CON_D1", "conception_path", "D", -1.5,
     "Mars occupies or graha-aspects D7 5H, 5L or Sphuta",
     lambda s: _f(s, "mars_on_5_or_sphuta"), ('5H', '5L')),
    ("D7_CON_D2", "conception_path", "D", -1.5,
     "Rahu occupies D7 5H, 5L or Sphuta (aspect branch structurally false)",
     lambda s: _f(s, "rahu_on_5_or_sphuta"), ('5H', '5L')),
    ("D7_CON_E1", "conception_path", "E", -2.0,
     "D7 Lagna Lord combust or debilitated",
     lambda s: _any(_f(s, "lagna_lord_combust"),
                    _f(s, "lagna_lord_debilitated")), ()),
    ("D7_CON_E2", "conception_path", "E", -2.0,
     "D7 5H heavily afflicted by Ketu/Saturn with no Benefic Relief",
     lambda s: _all(_f(s, "ketu_or_saturn_afflicts_5h"),
                    _not3(_f(s, "benefic_relief_5h"))), ("5H",)),

    # ── Module 2 · Lineage Scope & Arrival Trajectory · 11 clauses ──────────
    ("D7_LIN_A1", "lineage_trajectory", "A", +2.0,
     "Unbroken structural sequence of three or more valid slots",
     lambda s: s.get("unbroken_slots", 0) >= 3, ()),
    # CORR-05 · Kendra/Trikona is SUFFICIENT here; the generic Well_Placed
    # vetoes would have failed a clean Jupiter in an ordinary kendra.
    ("D7_LIN_A2", "lineage_trajectory", "A", +2.0,
     "Jupiter Well-Placed in D7 (Kendra/Trikona, Own or Exalted)",
     lambda s: _f(s, "jupiter_fd1e_well_placed"), ("Jupiter",)),
    ("D7_LIN_A3", "lineage_trajectory", "A", +1.5,
     "D7 5L Well-Placed",
     lambda s: _f(s, "well_placed_5l"), ('5L',)),
    ("D7_LIN_B1", "lineage_trajectory", "B", +1.5,
     "Exactly one or two clean structural sequence slots",
     lambda s: 1 <= s.get("clean_slots", 0) <= 2, ()),
    ("D7_LIN_B2", "lineage_trajectory", "B", +1.0,
     "Relevant Slot House Lords hold Stable Dignity",
     lambda s: _f(s, "clean_slot_lords_stable"), ()),
    ("D7_LIN_C1", "lineage_trajectory", "C", -1.5,
     "Saturn occupies D7 5H or is the D7 5L",
     lambda s: _any(_f(s, "saturn_in_5h"), _f(s, "saturn_rules_5h")), ('5H', '5L')),
    ("D7_LIN_C2", "lineage_trajectory", "C", -1.5,
     "Saturn Graha Drishti onto the Sequence Slot 1 house",
     lambda s: _f(s, "saturn_drishti_on_slot1"), ('5H',)),
    ("D7_LIN_D1", "lineage_trajectory", "D", -1.5,
     "Rahu or Ketu occupies D7 5H",
     lambda s: _f(s, "node_occupies_5h"), ('5H',)),
    # STRUCTURALLY NON-FIRING, and present on purpose. The Founder clause reads
    # "node aspect onto PK/5L"; under locked doctrine nodes cast no independent
    # aspect, so this clause can never fire. It is registered rather than
    # silently dropped so the registry matches the Founder table ID for ID, and
    # a test proves it cannot fire from any placement.
    ("D7_LIN_D2", "lineage_trajectory", "D", -1.5,
     "Node aspect onto PK/5L — structurally non-firing under locked doctrine",
     lambda s: _f(s, "node_aspect_on_pk_or_5l"), ('5L', 'Jupiter')),
    ("D7_LIN_E1", "lineage_trajectory", "E", -2.0,
     "Early Rahu/Ketu occupancy in Slot 1 or 2 without Secondary Activation",
     lambda s: _all(_f(s, "node_in_early_slot"),
                    _not3(_f(s, "secondary_line_activation"))), ("5H", "7H")),
    ("D7_LIN_E2", "lineage_trajectory", "E", -1.5,
     "Early Saturn occupancy in Slot 1 or 2 without Secondary Activation",
     lambda s: _all(_f(s, "saturn_in_early_slot"),
                    _not3(_f(s, "secondary_line_activation"))), ("5H", "7H")),

    # ── Module 3 · Parent-Child Bond & Dynamics · 11 clauses ────────────────
    ("D7_BND_A1", "bond_dynamics", "A", +2.0,
     "Jupiter occupies or graha-aspects D7 5H or 5L",
     lambda s: _f(s, "influence_5_jupiter"), ('5H', '5L', 'Jupiter')),
    ("D7_BND_A2", "bond_dynamics", "A", +1.5,
     "Sun occupies or graha-aspects D7 5H or 5L",
     lambda s: _f(s, "influence_5_sun"), ('5H', '5L')),
    ("D7_BND_A3", "bond_dynamics", "A", +1.5,
     "D7 9L resides with or graha-aspects D7 5L",
     lambda s: _f(s, "ninth_lord_on_5l"), ('5H', '5L', '9L')),
    ("D7_BND_B1", "bond_dynamics", "B", +1.5,
     "Mercury occupies or graha-aspects D7 5H or 5L",
     lambda s: _f(s, "influence_5_mercury"), ('5H', '5L')),
    ("D7_BND_B2", "bond_dynamics", "B", +1.5,
     "Mars occupies or graha-aspects D7 5H or 5L",
     lambda s: _f(s, "influence_5_mars"), ('5H', '5L')),
    ("D7_BND_C1", "bond_dynamics", "C", +1.5,
     "Moon occupies or graha-aspects D7 5H or 5L",
     lambda s: _f(s, "influence_5_moon"), ('5H', '5L')),
    ("D7_BND_C2", "bond_dynamics", "C", +1.5,
     "Venus occupies or graha-aspects D7 5H or 5L",
     lambda s: _f(s, "influence_5_venus"), ('5H', '5L', 'Venus')),
    ("D7_BND_D1", "bond_dynamics", "D", -1.5,
     "Saturn occupies or graha-aspects D7 5H or 5L",
     lambda s: _f(s, "influence_5_saturn"), ('5H', '5L')),
    ("D7_BND_D2", "bond_dynamics", "D", +1.0,
     "Vayu Dominance",
     lambda s: _f(s, "vayu_dominant"), ()),
    ("D7_BND_E1", "bond_dynamics", "E", -2.0,
     "Malefic Axis Touching",
     lambda s: _f(s, "malefic_axis_touching"), ()),
    ("D7_BND_E2", "bond_dynamics", "E", -1.5,
     "D7 6L/8L/12L occupies D7 5H or conjuncts D7 5L",
     lambda s: _f(s, "dusthana_lord_on_progeny_axis"), ('5H', '5L')),
]

# ─── CORR-05 · FD-2A parental vectors, DERIVED not hand-assigned ────────────
#
# The Founder lock, applied literally:
#
#   5H vector · clause explicitly references D7 5H or D7 5L
#   9H vector · clause explicitly references D7 9H, D7 9L or Jupiter
#   7H vector · clause explicitly references D7 7H, D7 7L or Venus
#
# A clause with none of those anchors contributes to NO vector. A clause may
# legitimately contribute to SEVERAL — `D7_BND_A1` (Jupiter influences 5H/5L)
# lands in both 5H and 9H, and `D7_BND_C2` (Venus influences 5H/5L) lands in
# both 5H and 7H.
#
# The anchor tuple is declared on each clause record and the buckets are DERIVED
# from it below. There is no hand-assigned bucket anywhere, so a future Dev
# cannot quietly place a clause in a vector its condition does not name.

VECTOR_ANCHORS: Dict[int, frozenset] = {
    5: frozenset({"5H", "5L"}),
    9: frozenset({"9H", "9L", "Jupiter"}),
    7: frozenset({"7H", "7L", "Venus"}),
}

# Slot 1 and Slot 2 are D7 H5 and D7 H7 by locked definition
# (d7_engine.SLOT_HOUSES == (5, 7, 9, 11)), so a clause naming those slots
# names those houses. Asserted by test rather than assumed.
SLOT_ANCHOR_NOTE = "SLOT_HOUSES[0] == 5 and SLOT_HOUSES[1] == 7"

RULE_ANCHORS: Dict[str, tuple] = {}
RULE_VECTORS: Dict[str, list] = {}


def vectors_for(anchors) -> list:
    """Derive the applicable Founder vectors from a clause's anchor set."""
    a = frozenset(anchors)
    return [h for h in (5, 9, 7) if a & VECTOR_ANCHORS[h]]


def _make_predicate(key: str):
    """Read one FD-1B boolean. Missing key -> None (UNRESOLVED), never False."""
    def _p(surface: Dict[str, Any]) -> Optional[bool]:
        if key not in surface:
            return None
        return bool(surface[key])
    return _p


def _install() -> None:
    for rid, arch, state, weight, desc, pred, anchors in _SPEC:
        register(Rule(rule_id=rid, archetype=arch, state=state,
                      tier=_tier_for(weight), description=desc, predicate=pred,
                      unresolved_reason="an FD-1B term this clause reads is unavailable"))
        RULE_ANCHORS[rid] = tuple(anchors)
        RULE_VECTORS[rid] = vectors_for(anchors)


def register(rule: Rule) -> Rule:
    if rule.archetype not in ARCHETYPES:
        raise ValueError(f"unknown archetype {rule.archetype!r}")
    if rule.state not in STATE_LETTERS:
        raise ValueError(f"unknown state {rule.state!r}")
    weight_for(rule.tier)  # fail fast on an unknown tier
    if any(r.rule_id == rule.rule_id for r in REGISTRY):
        raise ValueError(f"duplicate rule id {rule.rule_id!r}")
    REGISTRY.append(rule)
    return rule


# ─── evaluation ──────────────────────────────────────────────────────────────

def evaluate_all(surface: Dict[str, Any],
                 registry: Optional[List[Rule]] = None) -> Dict[str, Any]:
    """Evaluate every registered rule ONCE and return the fired-rule manifest.

    The manifest is the internal QA surface. It carries rule ids, tiers, weights
    and status, and it never crosses the publication wall.
    """
    rules = REGISTRY if registry is None else registry
    fired: List[Dict[str, Any]] = []
    not_fired: List[Dict[str, Any]] = []
    unresolved: List[Dict[str, Any]] = []

    for rule in rules:
        try:
            outcome = rule.predicate(surface)
        except Exception as exc:  # a broken predicate is unresolved, not False
            outcome = None
            reason = f"predicate raised {type(exc).__name__}"
        else:
            reason = rule.unresolved_reason
        record = {
            "rule_id": rule.rule_id,
            "archetype": rule.archetype,
            "state": rule.state,
            "tier": rule.tier,
            "base_weight": weight_for(rule.tier),
            "effective_weight": rule.effective_weight(),
            "description": rule.description,
        }
        if outcome is None:
            record["status"] = UNRESOLVED
            record["reason"] = reason or "founder primitive undefined"
            unresolved.append(record)
        elif outcome:
            record["status"] = "FIRED"
            fired.append(record)
        else:
            record["status"] = "NOT_FIRED"
            not_fired.append(record)

    return {
        "fired": fired,
        "not_fired": not_fired,
        "unresolved": unresolved,
        "counts": {
            "registered": len(rules),
            "fired": len(fired),
            "not_fired": len(not_fired),
            "unresolved": len(unresolved),
        },
        "multiplier": WEIGHT_MULTIPLIER,
    }


_install()
