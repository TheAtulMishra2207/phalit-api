"""D7-002 · shared D7 server predicates.

Per the addendum §E these are implemented ONCE and consumed as booleans by every
state selector. No archetype reimplements qualitative logic of its own.

THE NODE DOCTRINE IS ENFORCED STRUCTURALLY, NOT BY CONVENTION.
`aspects_house` and `aspects_body` return False for Rahu and Ketu on every call.
There is no flag to turn that off and no second aspect table in the module. The
browser's `myAspects` is deliberately NOT ported: it grants every body a 7th
aspect, which is exactly the defect (D7-B08) that let a node alone fire a
childlessness verdict.

A node may still:
  · occupy a house            → occupies()
  · conjoin a body            → conjunct()
  · RECEIVE an aspect         → aspects_body(other, node) is evaluated normally
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

NODES = frozenset({"Rahu", "Ketu"})

# Parashari graha-drishti, special aspects only. The universal 7th is added for
# every eligible body. Offsets are house-distance counts, 1 = same house.
SPECIAL_ASPECTS = {
    "Mars": (4, 8),
    "Jupiter": (5, 9),
    "Saturn": (3, 10),
}
UNIVERSAL_ASPECT = 7

NATURAL_BENEFICS = frozenset({"Jupiter", "Venus"})
NATURAL_MALEFICS = frozenset({"Sun", "Mars", "Saturn", "Rahu", "Ketu"})


@dataclass(frozen=True)
class D7PredicateDoctrine:
    """Dignity tables, injected. This module keeps no copy."""
    exaltation_sign: Dict[str, int]
    debilitation_sign: Dict[str, int]
    own_signs: Dict[str, List[int]]
    natural_friends: Dict[str, List[str]]
    natural_enemies: Dict[str, List[str]]
    # CORR-02 · moolatrikona is required by Well_Placed and Stable_Dignity.
    # (sign_index, min_degree, max_degree), injected from the certified table.
    moolatrikona: Dict[str, Any] = None


_DOCTRINE: Optional[D7PredicateDoctrine] = None


def configure_predicate_doctrine(doctrine: D7PredicateDoctrine) -> None:
    global _DOCTRINE
    _DOCTRINE = doctrine


def _doctrine() -> D7PredicateDoctrine:
    if _DOCTRINE is None:
        raise RuntimeError("d7_predicates doctrine not configured")
    return _DOCTRINE


# ─── aspect authority ────────────────────────────────────────────────────────

def aspected_houses(body: str, from_house: int) -> frozenset:
    """Houses `body` aspects from `from_house`.

    Rahu and Ketu return the empty set. This is the single chokepoint for the
    node doctrine in the whole D7 stack.
    """
    if body in NODES:
        return frozenset()
    if from_house is None:
        return frozenset()
    offsets = (UNIVERSAL_ASPECT,) + SPECIAL_ASPECTS.get(body, ())
    return frozenset(((from_house - 1 + off - 1) % 12) + 1 for off in offsets)


def aspects_house(body: str, target_house: int,
                  placements: Dict[str, Dict[str, Any]]) -> bool:
    rec = placements.get(body)
    if not rec:
        return False
    return target_house in aspected_houses(body, rec["house"])


def aspects_body(source: str, target: str,
                 placements: Dict[str, Dict[str, Any]]) -> bool:
    """Does `source` aspect the house `target` sits in?

    `source` in NODES is always False. `target` in NODES is evaluated normally,
    because a node RECEIVING an aspect is doctrinally fine.
    """
    trec = placements.get(target)
    if not trec:
        return False
    return aspects_house(source, trec["house"], placements)


def occupies(body: str, house: int, placements: Dict[str, Dict[str, Any]]) -> bool:
    rec = placements.get(body)
    return bool(rec) and rec["house"] == house


def conjunct(a: str, b: str, placements: Dict[str, Dict[str, Any]]) -> bool:
    ra, rb = placements.get(a), placements.get(b)
    return bool(ra and rb) and ra["house"] == rb["house"]


def occupants_of(house: int, placements: Dict[str, Dict[str, Any]]) -> List[str]:
    return [b for b, r in placements.items() if r["house"] == house]


def benefics_on_house(house: int, placements: Dict[str, Dict[str, Any]]) -> List[str]:
    """Natural benefics occupying OR aspecting a house."""
    out = []
    for b in sorted(NATURAL_BENEFICS):
        if occupies(b, house, placements) or aspects_house(b, house, placements):
            out.append(b)
    return out


def malefics_on_house(house: int, placements: Dict[str, Dict[str, Any]]) -> List[str]:
    """Natural malefics occupying OR aspecting a house.

    Nodes can enter this list by OCCUPANCY only — `aspects_house` refuses them.
    """
    out = []
    for m in sorted(NATURAL_MALEFICS):
        if occupies(m, house, placements) or aspects_house(m, house, placements):
            out.append(m)
    return out


# ─── dignity ─────────────────────────────────────────────────────────────────

DIGNITY_ORDER = ("Debilitated", "Enemy", "Neutral", "Friend", "Own", "Exalted")


def dignity(body: str, sign_index: int, sign_lords: List[str]) -> str:
    """D7 dignity from the D7 sign placement.

    Load-bearing: the sign index passed here MUST be a D7 index and the result
    is a D7 dignity. The live browser passed D7 indices into the D1 score table
    (D7-B09); that path does not exist in this module.
    """
    doc = _doctrine()
    if body in NODES:
        return "Neutral"
    if doc.exaltation_sign.get(body) == sign_index:
        return "Exalted"
    if doc.debilitation_sign.get(body) == sign_index:
        return "Debilitated"
    if sign_index in doc.own_signs.get(body, []):
        return "Own"
    lord = sign_lords[sign_index]
    if lord == body:
        return "Own"
    if lord in doc.natural_friends.get(body, []):
        return "Friend"
    if lord in doc.natural_enemies.get(body, []):
        return "Enemy"
    return "Neutral"


def is_strong(dig: str) -> bool:
    return dig in ("Exalted", "Own", "Friend")


def is_afflicted_dignity(dig: str) -> bool:
    return dig in ("Debilitated", "Enemy")


def natural_relationship(a: str, b: str) -> str:
    """Friend / Enemy / Neutral between two grahas, from the shared tables."""
    doc = _doctrine()
    if a == b:
        return "Own"
    if b in doc.natural_friends.get(a, []):
        return "Friend"
    if b in doc.natural_enemies.get(a, []):
        return "Enemy"
    return "Neutral"


def build_predicate_surface(facts: Dict[str, Any],
                            sign_lords: List[str]) -> Dict[str, Any]:
    """The boolean/scalar surface every state selector consumes.

    Computed once. A selector that needs something not here must have it added
    here rather than deriving it locally.
    """
    pl = facts["placements"]
    kh = facts["key_houses"]
    pk = facts["putrakaraka"]["graha"]

    def _dig(body: str) -> Optional[str]:
        rec = pl.get(body)
        return dignity(body, rec["d7_sign_index"], sign_lords) if rec else None

    surface: Dict[str, Any] = {
        "d7_lagna_lord_dignity": _dig(facts["d7_lagna"]["lord"]),
        "putrakaraka_house": pk and pl.get(pk, {}).get("house"),
        "putrakaraka_dignity": _dig(pk),
        "putrakaraka_in_dusthana": (pl[pk]["house"] in (6, 8, 12)) if pk in pl else False,
        "dignities": {b: _dig(b) for b in pl},
    }

    for h in (5, 7, 9):
        rec = kh[f"h{h}"]
        lord = rec["lord"]
        surface[f"h{h}_occupants"] = list(rec["occupants"])
        surface[f"h{h}_lord"] = lord
        surface[f"h{h}_lord_dignity"] = _dig(lord)
        surface[f"h{h}_lord_house"] = rec["lord_house"]
        surface[f"h{h}_lord_in_dusthana"] = rec["lord_house"] in (6, 8, 12)
        surface[f"h{h}_benefics"] = benefics_on_house(h, pl)
        surface[f"h{h}_malefics"] = malefics_on_house(h, pl)
        surface[f"h{h}_nodes_present"] = sorted(
            n for n in NODES if occupies(n, h, pl))
        surface[f"h{h}_pk_aspects"] = aspects_house(pk, h, pl)

    for h in (6, 12):
        surface[f"h{h}_occupants"] = list(kh[f"h{h}"]["occupants"])
        surface[f"h{h}_malefics"] = malefics_on_house(h, pl)

    surface["sphuta_favourable"] = bool(facts["sphuta"]["favourable"])
    surface["sphuta_parity"] = facts["sphuta"]["parity"]
    return surface
