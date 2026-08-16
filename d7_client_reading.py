"""D7-002 · THE PUBLICATION WALL.

Two surfaces, one wall. The engine surface keeps rule ids, tiers, weights,
fired/not-fired status and UNRESOLVED codes for QA and audit. The client surface
carries none of them.

This module is the ONLY place an internal state becomes something a customer
reads, and the only place a provider payload is assembled.

TWO INDEPENDENT DEFENCES, deliberately:

  1. CONSTRUCTION BY WHITELIST. `build_client_reading` builds the customer model
     field by field from named inputs. It never copies a dict through, never
     spreads the fact set and never iterates the manifest. A key that is not
     written here cannot appear downstream, so a new engine field cannot leak by
     being added upstream.

  2. FAIL-CLOSED SCAN. `assert_publication_safe` walks every string in the
     finished payload against the FD-S3 and FD-S1 prohibited families and raises
     on a hit. Nothing is scrubbed, redacted or partially retained — a violating
     payload is rejected WHOLE. A guard that repairs its input teaches the layer
     above that violations are survivable.

Defence 1 is what makes leaks structurally impossible. Defence 2 is what catches
the corpus text a future ticket writes into an allowed field. Neither is
sufficient alone, which is why both are here.
"""

import re
from copy import deepcopy
from typing import Any, Dict, List, Optional

from d7_engine import D7InputError

# ─── prohibited publication families · FD-S3 and FD-S1 ───────────────────────
#
# Patterns are deliberately narrow enough not to catch the Founder's own
# approved vocabulary. "Parent-Child Bond & Dynamics" is an archetype TITLE, so
# the bare word "child" is not prohibited; a COUNTED or ORDINAL child is.

PROHIBITED_PATTERNS = [
    # childlessness / barrenness
    # `childless` alone missed `childlessness`, caught by a route test.
    ("childlessness", r"\bchildless(?:ness)?\b"),
    ("childlessness", r"\bno\s+(?:biological\s+)?children\b"),
    ("childlessness", r"\bwithout\s+children\b"),
    ("childlessness", r"\babsence\s+of\s+(?:biological\s+)?children\b"),
    ("childlessness", r"\bbarren(?:ness)?\b"),
    ("childlessness", r"\bissueless\b"),
    ("childlessness", r"\banapatya\b"),
    ("childlessness", r"\bkakabandhya\b"),
    ("childlessness", r"\bcrow-?barren"),
    ("childlessness", r"\bbiological\s+block\b"),
    ("childlessness", r"\bdenial\s+of\s+(?:progeny|children)\b"),

    # actual child number
    ("child_count", r"\b(?:one|two|three|four|five|six|seven|eight|nine|ten|\d+)\s+"
                    r"(?:son|sons|daughter|daughters|child|children)\b"),
    ("child_count", r"\b(?:1st|2nd|3rd|4th|5th|first|second|third|fourth|fifth|eldest)\s+child\b"),
    ("child_count", r"\bnumber\s+of\s+children\b"),
    ("child_count", r"\bhow\s+many\s+children\b"),
    ("child_count", r"\bmany\s+(?:sons|daughters|children)\b"),
    ("child_count", r"\bonly\s+(?:one|a\s+single)\s+child\b"),
    ("child_count", r"\bfew\s+children\b"),
    ("child_count", r"\bsequence\s+ends\s+after\b"),
    ("child_count", r"\bterminat\w*\s+after\s+child\b"),

    # sex of children
    ("child_sex", r"\bsons?\b"),
    ("child_sex", r"\bdaughters?\b"),
    ("child_sex", r"\bmale\s+child\b"),
    ("child_sex", r"\bfemale\s+child\b"),
    ("child_sex", r"\bkanya-?yoga\b"),
    ("child_sex", r"\bbahu-?putra\b"),

    # miscarriage
    ("miscarriage", r"\bmiscarriage\b"),
    ("miscarriage", r"\bgarbhapaat\b"),
    ("miscarriage", r"\babortion\b"),
    ("miscarriage", r"\bpregnancy\s+loss\b"),
    ("miscarriage", r"\bfoetal\b|\bfetal\b"),

    # infant mortality / survival
    ("infant_survival", r"\bmay\s+not\s+survive\b"),
    ("infant_survival", r"\binfant\s+(?:death|mortality)\b"),
    ("infant_survival", r"\bloss\s+of\s+a\s+child\b"),
    ("infant_survival", r"\bbal-?arishta\b"),
    ("infant_survival", r"\bsurvive\s+infancy\b"),
    ("infant_survival", r"\bstillbirth\b"),

    # child disease / medical diagnosis
    ("child_health", r"\bchild(?:'s|ren's)?\s+(?:health|illness|disease|disorder)\b"),
    ("child_health", r"\bhealth\s+of\s+(?:the\s+)?(?:child|children|progeny)\b"),
    ("child_health", r"\bchildhood\s+(?:illness|disease)\b"),
    ("child_health", r"\bcongenital\b"),

    # medical fertility diagnosis · FD-S1 and FD-S3
    ("fertility_medical", r"\binfertil(?:e|ity)\b"),
    ("fertility_medical", r"\bsteril(?:e|ity)\b"),
    ("fertility_medical", r"\bfertility\s+(?:treatment|problem|issue|mismatch|defect)\b"),
    ("fertility_medical", r"\bconception\s+(?:difficult\w*|problem|failure)\b"),
    ("fertility_medical", r"\bdifficulty\s+conceiving\b"),
    ("fertility_medical", r"\bmedical\s+(?:support|intervention|treatment)\b"),
    ("fertility_medical", r"\bconsult\s+a\s+(?:physician|doctor)\b"),
    ("fertility_medical", r"\bivf\b|\bin\s+vitro\b"),
    ("fertility_medical", r"\bbiological\s+(?:compatibility|incompatibility)\b"),
    ("fertility_medical", r"\bseed\s+and\s+field\s+are\b"),

    # CORR-02 · spec K. Internal engine state labels that must never publish.
    ("internal_state_label", r"\bAssisted Conception\b"),
    ("internal_state_label", r"\bBiological Block\b"),

    # guaranteed adoption / conception
    ("guaranteed_outcome", r"\bwill\s+(?:adopt|conceive)\b"),
    ("guaranteed_outcome", r"\bguarantee\w*\s+(?:adoption|conception|children)\b"),
    ("guaranteed_outcome", r"\bcertain\s+to\s+(?:conceive|adopt)\b"),
    ("guaranteed_outcome", r"\bmust\s+adopt\b"),
    ("guaranteed_outcome", r"\bassured\s+(?:progeny|conception)\b"),
]

_COMPILED = [(family, re.compile(pat, re.IGNORECASE))
             for family, pat in PROHIBITED_PATTERNS]

# Internal vocabulary that must never reach a customer or a provider.
INTERNAL_TOKENS = re.compile(
    r"UNRESOLVED_FOUNDER_PRIMITIVE|effective_weight|base_weight|"
    r"\brule_id\b|\bstate_evidence\b|\bfired_rule_ids\b|\bnot_fired\b|"
    r"\bMAJOR_PRIMARY_YOGA\b|\bSEVERE_MALEFIC_AFFLICTION\b",
    re.IGNORECASE,
)


class PublicationViolation(Exception):
    """A prohibited claim reached a publication surface. Fail closed."""

    def __init__(self, family: str, pattern: str, path: str, excerpt: str):
        self.family = family
        self.pattern = pattern
        self.path = path
        super().__init__(f"{family} at {path}: /{pattern}/ matched {excerpt!r}")


def _walk_strings(node: Any, path: str = "$"):
    if isinstance(node, str):
        yield path, node
    elif isinstance(node, dict):
        for k, v in node.items():
            yield from _walk_strings(v, f"{path}.{k}")
            if isinstance(k, str):
                yield f"{path}<key>", k
    elif isinstance(node, (list, tuple)):
        for i, v in enumerate(node):
            yield from _walk_strings(v, f"{path}[{i}]")


def scan_publication(payload: Any, allowed_spans: tuple = ()) -> List[Dict[str, str]]:
    """Every prohibited hit in `payload`. Empty list means clean.

    `allowed_spans` are EXACT approved values. The allowance applies only when
    BOTH hold:

      · the WHOLE scanned string equals an approved value, and
      · it sits at an approved publication path — `.badge` or `.state_name`
        beneath `archetypes[...]`.

    Substring coverage was tried first and is too loose: it would let narrative
    prose QUOTE the approved badge inside a sentence and pass. Whole-string
    equality alone is still looser than needed, because the same string in any
    other field would pass; the path condition closes that.

    The allowance is passed per payload, so a caller that does not pass it —
    the provider narrative — gets no allowance at all.
    """
    hits: List[Dict[str, str]] = []
    approved = frozenset(allowed_spans)
    for path, text in _walk_strings(payload):
        if text in approved and _is_approved_publication_path(path):
            continue
        for family, rx in _COMPILED:
            m = rx.search(text)
            if m:
                hits.append({"family": family, "pattern": rx.pattern,
                             "path": path, "excerpt": m.group(0)})
        m = INTERNAL_TOKENS.search(text)
        if m:
            hits.append({"family": "internal_vocabulary", "pattern": "INTERNAL_TOKENS",
                         "path": path, "excerpt": m.group(0)})
    return hits


def assert_publication_safe(payload: Any, allowed_spans: tuple = ()) -> None:
    """Fail closed. Never scrub, never partially retain."""
    hits = scan_publication(payload, allowed_spans)
    if hits:
        first = hits[0]
        raise PublicationViolation(first["family"], first["pattern"],
                                   first["path"], first["excerpt"])


# ─── the customer model, built by whitelist ──────────────────────────────────

SEQUENCE_PREAMBLE = (
    "These are structural positions in your Saptamsha chart, not a count of "
    "children. Each slot describes an energetic quality present in the sequence."
)


from d7_rules import INTERNAL_ONLY_STATE_NAMES

# D7-004-LIVE-CORR-01 §3 · EXPLICIT publication names.
#
# An internal engine state name is never exposed wholesale. A state publishes
# only if it appears here, and only with the wording written here. Conception
# State D gets an approved customer badge; State E stays withheld.
PUBLICATION_STATE_NAMES = {
    ("conception_path", "D"): "Assisted Conception & Deliberate Preparation",
}

# The approved Conception badge, and the ONLY values the FD-S3 scanner will
# accept containing a prohibited-family phrase.
#
# THE ALLOWANCE IS DOUBLY NARROW:
#   1. WHOLE-STRING equality. A field that IS the badge is approved; a sentence
#      quoting it is not.
#   2. PATH-SCOPED. Only the archetype publication fields — `.badge` and
#      `.state_name` beneath `archetypes[...]` — may carry it. The same exact
#      string anywhere else in the payload is still rejected.
#
# It is also granted per PAYLOAD. `build_client_reading` and
# `build_provider_payload` pass it; `build_narrative` does not, so provider
# prose gets no allowance under any circumstances.
APPROVED_BADGE_SPANS = (
    "Assisted Conception & Deliberate Preparation",
    "State D: Assisted Conception & Deliberate Preparation",
)

# The only paths at which an approved value may appear.
_APPROVED_FIELD_SUFFIXES = (".badge", ".state_name")
_APPROVED_PATH_ROOT = "archetypes["


def _is_approved_publication_path(path: str) -> bool:
    return (_APPROVED_PATH_ROOT in path
            and path.endswith(_APPROVED_FIELD_SUFFIXES))


def _archetype_public(sel: Dict[str, Any]) -> Dict[str, Any]:
    """One archetype, stripped to what a reader sees.

    D7-003 · the state LETTER is published — `Selected State: State D` — while
    the internal-only NAME is withheld. That is the ticket's rule: the customer
    learns which state was selected without ever seeing `Assisted Conception`
    or `Biological Block / Spiritual Focus`.

    No evidence total, rule id, weight or UNRESOLVED code ever appears here.
    """
    name = sel.get("state_name")
    letter = sel.get("state")
    base = {
        "title": sel["title"],
        "state": letter,
        "selected_state_label": (f"Selected State: State {letter}"
                                 if letter else None),
    }
    # CORR-02 · spec K. FD-S1/FD-S3 outrank every engine state. Three engine
    # states carry labels that must never reach a reader; they are withheld
    # here BEFORE the scanner ever sees them, so the customer gets a neutral
    # unavailable rather than a diagnosis.
    approved = PUBLICATION_STATE_NAMES.get((sel.get("archetype"), letter))
    if approved:
        base.update({"available": True, "state_name": approved,
                     "name_withheld": False,
                     "badge": f"State {letter}: {approved}"})
        return base
    if name in INTERNAL_ONLY_STATE_NAMES:
        # The letter still publishes; the internal label never does.
        base.update({"available": True, "state_name": None,
                     "name_withheld": True, "badge": f"State {letter}"})
        return base
    available = bool(name) and letter is not None
    base.update({"available": available,
                 "state_name": name if available else None,
                 "name_withheld": False,
                 "badge": f"State {letter}: {name}" if available else None})
    return base


def _slot_public(slot: Dict[str, Any], ocean: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "name": slot["name"],
        "house": slot["house"],
        "house_sign": slot["house_sign"],
        "ruling_energy": list(slot["ruling_energy"]),
        "ruling_energy_source": slot["ruling_energy_source"],
        "elemental_influence": (ocean or {}).get("element"),
        "ocean": (ocean or {}).get("name"),
        "temperament": (ocean or {}).get("trait"),
    }


# D7-003-CORR-01 · the certified DISPLAY facts the diamond needs.
#
# The chart cannot be reconstructed from the four Sequence Slots: those carry
# only the energies attached to four houses, so most grahas are missing and the
# result is not the D7 chart. These are display facts — a lagna index and nine
# graha houses — and nothing more. They are not engine evidence and carry no
# dignity, no aspect and no rule.
DIAMOND_BODIES = ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus",
                  "Saturn", "Rahu", "Ketu")


def _diamond_public(facts: Dict[str, Any]) -> Dict[str, Any]:
    placements = facts["placements"]
    planets = {}
    for body in DIAMOND_BODIES:
        rec = placements.get(body)
        if rec:
            planets[body] = {"house": rec["house"]}
    return {
        "lagna_sign_index": facts["d7_lagna"]["sign_index"],
        "planets": planets,
    }


# D7-003-CORR-02 · FD-7A · the 12-sign D7 Lagna Parental Lens corpus.
#
# All twelve are Founder-supplied and reproduced BYTE FOR BYTE. The compressed
# Aquarius fragment shipped in CORR-01 was my own summary of the format
# document, not Founder text; it is replaced here by the full two-sentence
# reading, and the byte-for-byte requirement against that fragment is withdrawn.
#
# THE CORPUS IS THE AUTHORITY. There is no valid runtime state in which a known
# zodiac sign lacks a seed: `parental_lens_seed` RAISES on an unknown index
# rather than falling through to generic prose, and the provider branch that
# handled a missing seed is deleted.
PARENTAL_LENS_CORPUS: Dict[int, str] = {
    # Aries
    0: 'You approach parenthood with vibrant energy, directness and courage. You focus on instilling confidence, resilience and a strong spirit of independent initiative in your children.',
    # Taurus
    1: 'You approach parenthood with patience, calm consistency and steady devotion. You focus on creating a secure, comforting environment while teaching the value of perseverance and self-worth.',
    # Gemini
    2: 'You approach parenthood with curiosity, open communication and intellectual playfulness. You focus on broadening your child’s worldview and encouraging lifelong learning through active dialogue and exploration.',
    # Cancer
    3: 'You approach parenthood with deep emotional attunement, protective warmth and instinctual care. You focus on providing a secure emotional sanctuary where children feel unconditionally loved and understood.',
    # Leo
    4: 'You approach parenthood with warmth, generous enthusiasm and proud encouragement. You focus on nurturing your child’s unique self-expression and building their self-belief through celebration and praise.',
    # Virgo
    5: 'You approach parenthood with thoughtful attentiveness, practical guidance and dedicated care. You focus on helping your children build healthy habits, discernment and real-world problem-solving skills.',
    # Libra
    6: 'You approach parenthood with fairness, gentle harmony and emotional balance. You focus on teaching cooperation, empathy and good judgment while helping children navigate relationships with grace.',
    # Scorpio
    7: 'You approach parenthood with profound emotional depth, unwavering loyalty and fierce protection. You focus on fostering inner strength, authentic connection and psychological resilience in your children.',
    # Sagittarius
    8: 'You approach parenthood with optimism, humor and an expansive spirit of adventure. You focus on broadening your child’s horizons through diverse experiences, honesty and the freedom to discover their own path.',
    # Capricorn
    9: 'You approach parenthood with steady discipline, pragmatic wisdom and purposeful mentorship. You focus on teaching responsibility, integrity and the foundational tools needed to achieve lasting self-sufficiency.',
    # Aquarius
    10: 'You approach parenthood with a strong sense of responsibility, structure, and long-term vision. You want to give your children a solid foundation and teach them self-reliance.',
    # Pisces
    11: 'You approach parenthood with gentle empathy, boundless imagination and soulful sensitivity. You focus on nurturing your child’s creativity, emotional intuition and capacity for unconditional compassion.',
}


def parental_lens_seed(sign_index: int) -> str:
    """The approved reading for a D7 lagna sign. FAILS CLOSED.

    A sign index outside the corpus raises rather than returning None, because
    a missing entry is a contract failure, not a runtime state. Returning None
    here is what would let invented prose reach a customer under an "approved
    reading" label.
    """
    try:
        return PARENTAL_LENS_CORPUS[sign_index]
    except (KeyError, TypeError):
        raise D7InputError(
            f"no approved Parental Lens reading for sign index {sign_index!r}")


# The locked public wording for a valid no-dominant result.
NO_DOMINANT_PUBLIC = "No Single Dominant Pattern"


LESSON_TITLES = {
    6: "6th House · Karmic Discipline & Health Routines",
    12: "12th House · Independence & Letting Go",
}


def _lessons_public(facts: Dict[str, Any]) -> Dict[str, Any]:
    """The two customer-safe lesson zones. FACTS only, no diagnosis.

    D7-003 §8 fixes the register: H6 is routine, stress and discipline; H12 is
    distance, independence and release. Nothing about loss, mortality, disease
    or survival is computed here, so nothing of that kind can be rendered.
    """
    out = {}
    for h in (6, 12):
        rec = facts["key_houses"][f"h{h}"]
        out[f"h{h}"] = {
            "title": LESSON_TITLES[h],
            "house": h,
            "sign": rec["sign"],
            "occupants": list(rec["occupants"]),
        }
    return out


def _triangulation_public(joins: Dict[str, Any]) -> Dict[str, Any]:
    """Whitelisted D1 and D9 evidence for the three-part synthesis.

    Placement and dignity facts only. No verdict is formed here; the narrative
    layer EXPLAINS these, and it receives nothing else to reason from.
    """
    d1 = joins.get("d1") or {}
    d9 = joins.get("d9") or {}
    out: Dict[str, Any] = {
        "d1": {
            "available": bool(d1),
            "h5_occupants": list((d1.get("h5") or {}).get("occupants", [])),
            "h5_benefics": list((d1.get("h5") or {}).get("benefics", [])),
            "h5_lord": (d1.get("h5_lord") or {}).get("graha"),
            "h5_lord_house": (d1.get("h5_lord") or {}).get("house"),
            "h5_lord_dignity": (d1.get("h5_lord") or {}).get("dignity"),
        },
        "d9": {"available": bool(d9.get("available"))},
    }
    if d9.get("available"):
        out["d9"].update({
            "h7_occupants": list((d9.get("h7") or {}).get("occupants", [])),
            "h7_lord": (d9.get("h7_lord") or {}).get("graha"),
            "h7_lord_house": (d9.get("h7_lord") or {}).get("house"),
            "h7_lord_dignity": (d9.get("h7_lord") or {}).get("dignity"),
            "lagna_lord_to_h7_lord":
                (d9.get("lagna_lord_to_h7_lord") or {}).get("relationship"),
            "angular_benefics": {
                b: (None if v is None else
                    {"house": v.get("house"), "in_kendra": v.get("in_kendra"),
                     "in_trikona": v.get("in_trikona")})
                for b, v in (d9.get("angular_benefics") or {}).items()},
        })
    return out


def build_client_reading(facts: Dict[str, Any],
                         archetypes: List[Dict[str, Any]],
                         snapshot_fields: Dict[str, Any],
                         timing: Dict[str, Any],
                         joins: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Assemble the customer surface. Whitelist only, then fail-closed scan."""
    sph = facts["sphuta"]
    lagna = facts["d7_lagna"]
    placements = facts["placements"]

    slots = []
    for slot in facts["sequence"]:
        lead = slot["ruling_energy"][0] if slot["ruling_energy"] else None
        ocean = placements.get(lead, {}).get("ocean") if lead else None
        slots.append(_slot_public(slot, ocean))

    # D7-004-LIVE-CORR-02 §3 · a valid neutral astrological result is NOT the
    # same thing as an absence of data, and the customer must be able to tell
    # them apart.
    #
    #   NO_DOMINANT  → "No Single Dominant Pattern"   (computed, valid, neutral)
    #   anything else unresolved → available: False   → "Not available"
    #
    # `Not available` is reserved strictly for missing server data, a malformed
    # state, a genuinely uncomputed result or a failed preparation.
    def _snap(field: Dict[str, Any]) -> Dict[str, Any]:
        if field.get("resolved"):
            return {"available": True, "value": field.get("value")}
        if field.get("status") == "NO_DOMINANT":
            return {"available": True, "value": NO_DOMINANT_PUBLIC}
        return {"available": False, "value": None}

    joins = joins or {}
    period = timing["current_period"]
    jupiter = next((w for w in timing["windows"]
                    if w["window"] == "jupiter_fifth_axis"), {})
    saturn = next((w for w in timing["windows"]
                   if w["window"] == "saturn_stabilisation"), {})

    reading = {
        "quick_snapshot": {
            "conception_vitality": _snap(snapshot_fields["conception_vitality"]),
            "lineage_scope": _snap(snapshot_fields["lineage_scope"]),
            "primary_parental_strength": _snap(snapshot_fields["primary_parental_strength"]),
        },
        "diamond": _diamond_public(facts),
        "parental_lens": {
            "rising_sign": lagna["sign"],
            "ruler": lagna["lord"],
            # FD-7A · the approved reading. Always present for a valid sign.
            "insight_seed": parental_lens_seed(lagna["sign_index"]),
            "corpus_pending": False,
        },
        "biological_foundation": {
            "label": sph["label"],
            "sign": sph["sign"],
            "longitude": sph["longitude"],
            "parity": sph["parity"],
            "energetic_alignment": sph["energetic_alignment"],
        },
        "archetypes": [_archetype_public(a) for a in archetypes],
        "sequence": {
            "preamble": SEQUENCE_PREAMBLE,
            "slots": slots,
        },
        "lessons": _lessons_public(facts),
        "triangulation": _triangulation_public(joins),
        "timing": {
            "current_period": period.get("period_label"),
            "available": bool(period.get("resolved")),
            "authority": "context_only",
            # D7-003 §7 · both windows are named. They describe ACTIVATION
            # CONDITIONS, never guarantees, and carry no calendar date: the
            # server model supplies the condition, not the next occurrence.
            # D7-004-LIVE-CORR-01 §2 · the raw trigger predicate is INTERNAL
            # implementation evidence, not customer data. It stays on the engine
            # surface for calculation and tests and leaves the public contract.
            "windows": [w for w in (
                {"title": "Jupiter Fifth-Axis Window"} if jupiter.get("resolved") else None,
                {"title": "Saturn Stabilisation Window"} if saturn.get("resolved") else None,
            ) if w],
        },
    }

    assert_publication_safe(reading, APPROVED_BADGE_SPANS)
    return reading


# ─── the provider projection · D9-004-LIVE-CORR-02B ─────────────────────────
#
# CUSTOMER-SAFE-AT-AN-EXACT-PATH IS NOT PROVIDER-SAFE-FOR-FREE-PROSE.
#
# `APPROVED_BADGE_SPANS` grants "Assisted Conception & Deliberate Preparation"
# at `archetypes[...].badge` and `.state_name` and nowhere else. That rule is
# correct and is unchanged. But `build_provider_payload` forwarded the customer
# reading essentially intact, so the provider was HANDED the phrase and then
# rejected for repeating it — the output wall grants no allowance, by design.
#
# The provider was being actively prompted with the thing it is forbidden to
# say. That is a deterministic input defect, not a compliance failure, and no
# instruction can reliably fix it: a model given a phrase in its context will
# sometimes use it.
#
# So the projection REMOVES the wording before the provider sees it, and the
# boundary is then asserted WITH NO ALLOWANCE. The property becomes structural
# rather than dependent on the model behaving.
#
# The selection survives. `state`, `selected_state_label` and `available` all
# travel, so the provider still knows exactly which deterministic state was
# chosen — which is what it needs to explain it. It never needed the badge.

_PROVIDER_WITHHELD_ARCHETYPE_FIELDS = ("state_name", "badge")


def _archetype_provider_projection(arc: Dict[str, Any]) -> Dict[str, Any]:
    """One archetype, with any publication-protected wording removed.

    SCAN-DRIVEN, NOT PHRASE-LIST-DRIVEN. A field is withheld when scanning its
    value WITHOUT an allowance produces a hit, rather than when it matches a
    hard-coded string. So a future addition to `APPROVED_BADGE_SPANS`, or any
    other protected wording that reaches a badge, is covered the day it is
    added and nobody has to remember to extend a second list here.
    """
    out = dict(arc)
    withheld = []
    for field in _PROVIDER_WITHHELD_ARCHETYPE_FIELDS:
        value = out.get(field)
        if isinstance(value, str) and value and scan_publication({field: value}):
            out[field] = None
            withheld.append(field)
    if withheld:
        # Structural metadata only. NOT a replacement phrase, and deliberately
        # not an invented substitute: the ticket forbids putting new astrology
        # where the badge was, and a paraphrase would be exactly that.
        out["state_name_withheld_from_provider"] = True
    return out


def build_provider_payload(client_reading: Dict[str, Any]) -> Dict[str, Any]:
    """What a narrative provider may receive.

    THE PROVIDER RECEIVES A PROJECTION OF THE SAFE CLIENT-READING MODEL. It
    never sees the fact set, the manifest, the predicate surface or any withheld
    classical evidence, and since CORR-02B it never sees publication-protected
    wording either. It cannot re-derive a verdict it was never given the inputs
    for, and it cannot echo a phrase it was never shown.

    NON-MUTATING. `client_reading` is deep-copied first, so the customer payload
    still carries its approved State-D badge after this runs. Sanitising the
    provider's input must never erase the deterministic card.
    """
    projected = deepcopy(client_reading)
    archetypes = projected.get("archetypes")
    if isinstance(archetypes, list):
        projected["archetypes"] = [
            _archetype_provider_projection(a) if isinstance(a, dict) else a
            for a in archetypes
        ]

    payload = {"client_reading": projected}
    # NO ALLOWANCE. This is the heart of the fix and the difference from the
    # customer scan two functions above: the customer reading may carry the
    # approved badge at its approved path, and the provider payload must be
    # INTRINSICALLY clean. If any protected phrase survives projection this
    # raises here, before the provider is ever called.
    assert_publication_safe(payload)
    return payload
