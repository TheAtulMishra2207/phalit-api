"""D7-002 · Saptamsha engine.

Owns the certified D7 facts: placements, house/lord structure, the gendered
Beeja/Kshetra Sphuta, the four structural Sequence Slots and the ocean facts the
Sequence needs.

This module holds NO doctrine table of its own. SIGNS and SIGN_LORDS are
injected once by main.py via `configure_d7_doctrine`, exactly as D4 and D5 do,
so there is one copy of each in the process.

Vocabulary note, load-bearing: nothing in this module names a child. The
structural positions are SLOTS. See d7_client_reading for the publication wall.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

CLASSICAL_SEVEN = ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn")
NODES = ("Rahu", "Ketu")
ORDER_NINE = CLASSICAL_SEVEN + NODES

# D7-002 · Jupiter is the natural Putrakaraka. Fixed doctrine, not derived.
PUTRAKARAKA = "Jupiter"

# Exactly four potential slots. The ticket fixes both the count and the names.
# Slot houses follow the accepted Manduka base sequence, whose first four
# entries (5, 7, 9, 11) match the Founder format table row for row.
SLOT_HOUSES = (5, 7, 9, 11)
SLOT_COUNT = 4

SEGMENT = 30.0 / 7.0  # 4°17'8.57" — the Saptamsha septile

# The presiding ocean of each of the seven divisions. Ported verbatim from the
# accepted browser corpus; only its placement in the report changes.
D7_OCEAN: Dict[int, Dict[str, str]] = {
    1: {"odd": "Kshara (Salt)", "even": "Shuddha Jala", "element": "Earth",
        "deity": "Navagraha",
        "trait": "Grounded and practical, oriented to ordinary and durable joys."},
    2: {"odd": "Kshira (Milk)", "even": "Madhu/Sura", "element": "Water",
        "deity": "Varuna",
        "trait": "Emotionally nurturing and sensitive, a deeply caring presence."},
    3: {"odd": "Dadhi (Yogurt)", "even": "Ikshu Rasa", "element": "Air",
        "deity": "Vayu",
        "trait": "Meditative and contemplative, drawn toward inner stillness."},
    4: {"odd": "Ghruta (Ghee)", "even": "Ghruta", "element": "Fire",
        "deity": "Agni",
        "trait": "Vibrant and ritual-minded, with a natural sense of ceremony."},
    5: {"odd": "Ikshu Rasa (Sugar)", "even": "Dadhi", "element": "Solar",
        "deity": "Surya",
        "trait": "Leadership and endurance, carrying solar authority."},
    6: {"odd": "Madhu/Sura (Soma)", "even": "Kshira", "element": "Lunar",
        "deity": "Chandra",
        "trait": "Intuitive and receptive, emotionally perceptive."},
    7: {"odd": "Shuddha Jala (Pure)", "even": "Kshara", "element": "Creator",
        "deity": "Brahma",
        "trait": "Original in vision, with deep inner reserves."},
}


@dataclass(frozen=True)
class D7Doctrine:
    """The minimum doctrine surface this module reads. Injected, never imported."""
    signs: List[str]
    sign_lords: List[str]


_DOCTRINE: Optional[D7Doctrine] = None


def configure_engine_doctrine(doctrine: D7Doctrine) -> None:
    global _DOCTRINE
    _DOCTRINE = doctrine


def _doctrine() -> D7Doctrine:
    if _DOCTRINE is None:
        raise RuntimeError("d7_engine doctrine not configured")
    return _DOCTRINE


class D7InputError(ValueError):
    """A certified snapshot value that D7 cannot compute from."""


# ─── placement arithmetic ────────────────────────────────────────────────────

def division_number(degree: float) -> int:
    """Which of the seven 4°17' segments a degree falls in. 1-based.

    Half-open on the lower bound: a segment owns its lower bound, not its upper.
    The browser used `min(ceil(deg/SEGMENT), 7) || 1`, which maps exactly 0.0 to
    0 and then rescues it with `|| 1`. Computed here as a floor so 0.0 lands in
    segment 1 directly and no rescue branch is needed.
    """
    if degree is None or degree != degree:  # NaN
        raise D7InputError("degree is not a number")
    if not (0.0 <= degree < 30.0):
        raise D7InputError(f"degree {degree!r} outside [0, 30)")
    return min(int(degree / SEGMENT) + 1, 7)


def d7_sign_index(degree: float, sign_index: int) -> int:
    """D7 sign for a body at `degree` in `sign_index`.

    Odd signs count from the sign itself; even signs from the 7th from it.
    `sign_index` is 0-based, so Aries (0) is an ODD sign.
    """
    if not isinstance(sign_index, int) or isinstance(sign_index, bool):
        raise D7InputError(f"sign_index {sign_index!r} is not an int")
    if not (0 <= sign_index <= 11):
        raise D7InputError(f"sign_index {sign_index!r} outside [0, 11]")
    n = division_number(degree)
    is_odd_sign = sign_index % 2 == 0
    base = sign_index if is_odd_sign else (sign_index + 6) % 12
    return (base + n - 1) % 12


def _house_from(sign_idx: int, lagna_idx: int) -> int:
    return ((sign_idx - lagna_idx) % 12) + 1


# ─── Beeja / Kshetra Sphuta ──────────────────────────────────────────────────
#
# D7-002 locks BOTH the arithmetic and the publication vocabulary per gender.
# The live browser held two incompatible polarity rules at once (D7-B07); this
# module holds exactly one, and it is gendered.
#
#   Male   · Sun + Venus + Jupiter    · ODD  favourable
#   Female · Mars + Moon + Jupiter    · EVEN favourable
#
# No medical defect language is produced here or anywhere downstream.

SPHUTA_PARTS = {
    "male": ("Sun", "Venus", "Jupiter"),
    "female": ("Mars", "Moon", "Jupiter"),
}
SPHUTA_LABEL = {"male": "Beeja Sphuta", "female": "Kshetra Sphuta"}

SPHUTA_ALIGNMENT = {
    ("male", True): "Robust Seed / Optimal Vitality",
    ("male", False): "Receptive / Requires Patience & Health Preparation",
    ("female", False): "Optimal Receptive Field / High Compatibility",
    ("female", True): "Dynamic Field / Requires Preparation & Health Optimization",
}


def build_sphuta(gender: str, planets: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """The active Sphuta for this gender. Never both, never the partner's."""
    doc = _doctrine()
    if gender not in SPHUTA_PARTS:
        raise D7InputError(f"gender {gender!r} is not 'male' or 'female'")
    parts = SPHUTA_PARTS[gender]
    total = 0.0
    for body in parts:
        p = planets.get(body)
        if not p:
            raise D7InputError(f"certified snapshot has no {body}")
        total += (p["sign_index"] * 30.0) + p["degree"]
    lon = total % 360.0
    si = int(lon // 30)
    is_odd = si % 2 == 0
    return {
        "label": SPHUTA_LABEL[gender],
        "components": list(parts),
        "longitude": round(lon, 4),
        "sign": doc.signs[si],
        "sign_index": si,
        "degree": round(lon % 30, 4),
        "lord": doc.sign_lords[si],
        "parity": "odd" if is_odd else "even",
        "favourable": is_odd if gender == "male" else not is_odd,
        "energetic_alignment": SPHUTA_ALIGNMENT[(gender, is_odd)],
    }


# ─── the four structural Sequence Slots ──────────────────────────────────────

def build_sequence(d7_lagna_index: int,
                   d7_placements: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Exactly four slots. Structural energy only.

    Ruling energy is the slot house's OCCUPANTS; when the house is empty it
    falls back to the house lord. Nothing here counts, caps or terminates: the
    accepted `terminatedAfter` concept is deliberately not computed, because it
    has no publishable meaning under FD-S3 and computing it invites a later
    caller to publish it.
    """
    doc = _doctrine()
    slots: List[Dict[str, Any]] = []
    for ordinal, house in enumerate(SLOT_HOUSES, start=1):
        house_sign_idx = (d7_lagna_index + house - 1) % 12
        house_lord = doc.sign_lords[house_sign_idx]
        occupants = [b for b in ORDER_NINE
                     if b in d7_placements and d7_placements[b]["house"] == house]
        if occupants:
            ruling, source = list(occupants), "occupants"
        else:
            ruling, source = [house_lord], "house_lord"
        slots.append({
            "slot": ordinal,
            "name": f"Sequence Slot {ordinal}",
            "house": house,
            "house_sign": doc.signs[house_sign_idx],
            "house_sign_index": house_sign_idx,
            "house_lord": house_lord,
            "occupants": occupants,
            "ruling_energy": ruling,
            "ruling_energy_source": source,
        })
    return slots


def ocean_for(degree: float, sign_index: int) -> Dict[str, Any]:
    n = division_number(degree)
    entry = D7_OCEAN[n]
    is_odd_sign = sign_index % 2 == 0
    return {
        "division": n,
        "name": entry["odd"] if is_odd_sign else entry["even"],
        "element": entry["element"],
        "deity": entry["deity"],
        "trait": entry["trait"],
    }


# ─── the assembled fact set ──────────────────────────────────────────────────

def build_d7_facts(lagna: Dict[str, Any],
                   planets: Dict[str, Dict[str, Any]],
                   gender: str) -> Dict[str, Any]:
    doc = _doctrine()
    if not lagna:
        raise D7InputError("certified snapshot has no lagna")

    d7_lagna_idx = d7_sign_index(lagna["degree"], lagna["sign_index"])

    placements: Dict[str, Dict[str, Any]] = {}
    for body in ORDER_NINE:
        p = planets.get(body)
        if not p:
            continue
        si = d7_sign_index(p["degree"], p["sign_index"])
        placements[body] = {
            "d7_sign": doc.signs[si],
            "d7_sign_index": si,
            "house": _house_from(si, d7_lagna_idx),
            "d1_sign_index": p["sign_index"],
            "d1_degree": p["degree"],
            "ocean": ocean_for(p["degree"], p["sign_index"]),
        }

    houses = []
    for h in range(1, 13):
        sidx = (d7_lagna_idx + h - 1) % 12
        houses.append({
            "house": h,
            "sign": doc.signs[sidx],
            "sign_index": sidx,
            "lord": doc.sign_lords[sidx],
            "occupants": [b for b in ORDER_NINE
                          if b in placements and placements[b]["house"] == h],
        })

    def _house(h: int) -> Dict[str, Any]:
        return houses[h - 1]

    # The house set the Founder rules actually read. Named explicitly so a later
    # reader can see the whole surface without re-deriving it.
    key_houses = {}
    for h in (5, 6, 7, 9, 12):
        rec = _house(h)
        lord = rec["lord"]
        key_houses[f"h{h}"] = {
            "sign": rec["sign"],
            "sign_index": rec["sign_index"],
            "occupants": rec["occupants"],
            "lord": lord,
            "lord_house": placements[lord]["house"] if lord in placements else None,
            "lord_d7_sign_index": (placements[lord]["d7_sign_index"]
                                   if lord in placements else None),
        }

    return {
        "d7_lagna": {
            "sign": doc.signs[d7_lagna_idx],
            "sign_index": d7_lagna_idx,
            "lord": doc.sign_lords[d7_lagna_idx],
            "d1_sign_index": lagna["sign_index"],
            "d1_degree": lagna["degree"],
        },
        "placements": placements,
        "houses": houses,
        "key_houses": key_houses,
        "putrakaraka": {
            "graha": PUTRAKARAKA,
            "house": placements.get(PUTRAKARAKA, {}).get("house"),
            "d7_sign_index": placements.get(PUTRAKARAKA, {}).get("d7_sign_index"),
        },
        "sphuta": build_sphuta(gender, planets),
        "sequence": build_sequence(d7_lagna_idx, placements),
    }
