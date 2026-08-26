"""D9-R2 · d9_r2_narrative · the bounded Final Synthesis.

The provider returns **identifiers, not sentences**. The server owns every
astrological proposition, every prose variant and every connector, and renders
the final text itself. That is the accepted two-tier extractive architecture,
carried over intact.

    server publishes atoms + variants  ->  provider returns an ORDER/VARIANT PLAN
    ->  server renders the prose

There is no free-text field in the schema, so an unknown atom, an unknown
variant, an unknown connector, a duplicate, a bad cardinality or a prose value
anywhere all fail closed.

AND A FAILURE NEVER COSTS THE READER THE SECTION. Every failure path falls
through to a deterministic canonical plan over the same server-owned atoms, so
the report always carries a Final Synthesis. The old
"Interpretive explanation unavailable" is not reproduced.
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional, Sequence, Tuple

LOG = logging.getLogger(__name__)

MIN_ATOMS = 4
MAX_ATOMS = 16
MIN_DOMAINS = 4          # when four substantive domains exist
TARGET_WORDS = (800, 1300)
DEPTH_TARGET = (800, 1200)

# Domain order is the server's editorial spine: who they are becoming, what they
# can rely on, what deserves attention, what the work should serve, what
# partnership asks, what to practise now.
# FLIGHT 15 · the reading is now built from finer atoms so it can reach real
# depth without repetition and without giving the provider one inch more
# astrological authority. Every atom below still restates a proposition the
# deterministic report already published.
DOMAIN_ORDER = ("central_theme", "outer_cost", "strength", "strength_calibration",
                "growth_edge", "distinction", "contribution",
                "partnership", "partnership_orientation", "cultivate", "watch",
                "instructions", "integration")

# Finite, server-owned, additive only. No causal, hierarchical or contradictory
# connective survives — the provider may juxtapose, never relate.
# `lower` says whether the connective runs INTO the next sentence — a lead-in
# needs the following text lowercased, a full stop does not. Getting that wrong
# produces "There is also this. watch for...", which is what the first draft did.
CONNECTORS: Dict[str, Tuple[str, bool]] = {
    "none": ("", False),
    "also": ("There is also this. ", False),
    "alongside": ("Alongside that, ", True),
    "another_part": ("Another part of the same picture: ", True),
    "at_the_same_time": ("At the same time, ", True),
}

VARIANTS = ("reflective", "integrative", "direct")

OPENING = ("Taken as one reading rather than a set of findings, this is what the "
           "Navāṁśa keeps returning to. ")
# Not an apology. The Flight 14 ending retreated from the reading at the moment
# it should have landed.
CLOSING = ("Held together, these are not separate observations but one operating "
           "pattern: what you lead with, what it costs, what steadies it, and "
           "what it is finally for.")


class NarrativeContractError(Exception):
    """The provider plan does not satisfy the composition contract."""


# ═════════════════════════════════════════════════════════════════════════════
# ATOMS · built from the Flight 10 synthesis material
# ═════════════════════════════════════════════════════════════════════════════
#
# SYNTHESIS-SPECIFIC WORDING, not the card copy. Each variant restates a
# proposition the deterministic report already published, in a register that
# reads as continuous prose rather than a card being quoted back. That is what
# stops the synthesis becoming a replay.

# Three registers per domain. Each restates a proposition the deterministic
# report already published, at a length that lets six atoms reach the 250-400
# word target without padding. `{a}` `{b}` `{c}` are operands supplied by
# `_operands`; `TITLE_OPERANDS` marks which arrive already capitalised.
_FRAMES: Dict[str, Dict[str, str]] = {
    "central_theme": {
        "reflective": "Left to itself your instinct is {a}. What this chart "
                      "matures is something else — {b} — and the distance "
                      "between the two is the whole of the work here. That is "
                      "not a contradiction to be resolved. The natal chart "
                      "shows what you reach for without deciding to; the "
                      "Navāṁśa shows what the same material becomes when it is "
                      "held on purpose. One is temperament and the other is "
                      "development, and they run on the same fuel. Held over "
                      "time, what that development is finally for is {c}",
        "integrative": "Your working default is {a}, while the mature demand of "
                       "the chart is {b}. Neither replaces the other; the second "
                       "has to be chosen where the first would simply happen, "
                       "and the direction it serves is {c}",
        "direct": "You lead with {a}. The chart asks instead for {b}, and asks "
                  "it deliberately rather than by temperament. What it is for "
                  "is {c}",
    },
    # SINGLE only. DUAL and COMPOUND have their own frames, because a
    # multi-graha election has no single capacity/expression/mechanism triple —
    # reading one out of a flat list is what produced the Flight 11 nonsense.
    "strength": {
        "reflective": "There is ground here you can stand on. {a} is the "
                      "steadiest thing you carry, showing up as {b}, and it "
                      "holds because {c}. This is read from how the planet sits "
                      "in the Navāṁśa rather than from the natal chart, so it "
                      "describes the mature demanded mode rather than the "
                      "outer default. It is the faculty to lean on when the "
                      "situation is genuinely difficult and your usual "
                      "reflexes are not enough.",
        "integrative": "{a} is the capacity you can rely on rather than hope "
                       "for. In practice that reads as {b}, and it stays "
                       "dependable when {c}",
        "direct": "You can rely on {a}. It looks like {b}, and it becomes "
                  "dependable when {c}",
    },
    # THREE DIMENSIONS, SYMMETRICALLY. `{b}` is EVERY constructive expression
    # and `{c}` is EVERY dependable mechanism, both attributed. Flight 12 passed
    # `mechs[0]`, so Moon's mechanism was presented as the stabiliser of all four
    # co-equal capacities — the same asymmetry the A/B ruling removed, arriving
    # by a different route.
    "strength_multi": {
        "reflective": "What you can rely on is not one faculty but several "
                      "working together — {a}. Their constructive range appears "
                      "as {b}. Their dependability rests on {c}",
        "integrative": "Several capacities carry equal weight here: {a}. None is "
                       "the lead and none is support. They express as {b}. The "
                       "set stays dependable on {c}",
        "direct": "You can rely on a convergence rather than a single strength: "
                  "{a}. It expresses as {b}. It holds on {c}",
    },
    "strength_foundational": {
        "reflective": "No single placement dominates, and what you rely on is "
                      "the ground itself: {a}, showing up as {b}",
        "integrative": "Your reliability is structural rather than located in "
                       "one faculty. It reads as {a}, expressed through {b}",
        "direct": "What you can rely on is {a}, which shows up as {b}",
    },
    "growth_edge": {
        "reflective": "The friction worth watching is {a}. It is not a flaw so "
                      "much as the same material running without supervision — "
                      "which is why it tends to appear at precisely the moments "
                      "you are most convinced you are handling things well. It "
                      "is read from the Navāṁśa ascendant rather than from any "
                      "planet, so it describes a pattern in how you mature "
                      "rather than a weakness located somewhere in the chart.",
        "integrative": "Where this goes wrong, it goes wrong predictably: {a}. "
                       "Noticing it early is most of the correction.",
        "direct": "Watch for {a}. It arrives quietly and it repeats.",
    },
    "contribution": {
        "reflective": "As for what the work should serve, the chart points "
                      "toward {a} — {b}. That is the direction achievement is "
                      "worth pointing at here.",
        "integrative": "Your contribution reads as {a}: {b}. The question worth "
                       "carrying is what your achievement is for.",
        "direct": "This points toward {a} — {b}",
    },
    # The dissenting role is Founder-locked doctrine and must survive into the
    # prose. Flight 11 read `primary` and discarded the vector entirely.
    # ROLE-SPECIFIC COMPOSITION. One frame set per deterministic role, and none
    # of them inserts a customer heading as a noun phrase — the meaning is
    # written into the sentence instead. A role must never borrow another
    # role's prose.
    "contribution_functional": {
        "reflective": "Where the work should point is {a}, and {b} describes how "
                      "that contribution reaches the world — the register it is "
                      "actually carried in rather than a second vocation.",
        "integrative": "Your contribution reads as {a}. {b} describes how that "
                       "contribution reaches the world, which is the form the "
                       "same purpose takes in practice.",
        "direct": "This points toward {a}. {b} describes how that contribution "
                  "reaches the world.",
    },
    "contribution_ethical": {
        "reflective": "Where the work should point is {a}, and {b} describes how "
                      "that contribution should be carried — the standard it is "
                      "held to rather than the field it operates in.",
        "integrative": "Your contribution reads as {a}. {b} describes how that "
                       "contribution should be carried, which is a question of "
                       "conduct rather than of visible form.",
        "direct": "This points toward {a}. {b} describes how that contribution "
                  "should be carried.",
    },
    "contribution_aptitude": {
        "reflective": "Where the work should point is {a}, with {b} describing "
                      "the aptitude underneath it — what the capacity is built "
                      "on rather than what it produces.",
        "integrative": "Your contribution reads as {a}, and {b} describes the "
                       "aptitude underneath it: the native material the "
                       "contribution draws on.",
        "direct": "This points toward {a}, with {b} describing the aptitude "
                  "underneath it.",
    },
    "contribution_polar": {
        "reflective": "The chart does not converge on one contribution. Visible "
                      "impact points toward {a}, what drives it ethically is "
                      "{b}, and the aptitude underneath is {c}",
        "integrative": "Three distinct threads carry your contribution: {a} as "
                       "visible impact, {b} as the ethical driver, {c} as "
                       "innate aptitude.",
        "direct": "Impact: {a}. Ethical driver: {b}. Innate aptitude: {c}",
    },
    "partnership_tiers": {
        "reflective": "Partnership has its own shape here, and it is a "
                      "statement about you rather than about anyone else. {a}. "
                      "What governs your capacity to sustain that field is {b}, "
                      "and on its Navāṁśa standing {c}",
        "integrative": "In enduring partnership the field asks for something "
                       "specific: {a}. That capacity is governed by {b}, and "
                       "what its standing implies is this — {c}",
        "direct": "The relationship field asks for this: {a}. It is governed by "
                  "{b}, and {c}",
    },
    "partnership_orientation": {
        "reflective": "Underneath that sits an inner orientation toward union "
                      "itself: {a}. It does not contradict the field above; it "
                      "colours how you inhabit it.",
        "integrative": "There is also a karmic tilt in how you approach union: "
                       "{a}. It is a disposition rather than an outcome.",
        "direct": "Your inner orientation toward union: {a}",
    },
    "partnership": {
        "reflective": "In partnership, {a}. That is a real support rather than "
                      "a consolation, and it is worth using deliberately rather "
                      "than assuming it will hold on its own. What the chart "
                      "supports directly is this much and no more: it says "
                      "something about the ground partnership stands on for "
                      "you, not about a particular person, a particular time, "
                      "or a particular outcome.",
        "integrative": "Closeness is not neutral ground for you: {a}. It repays "
                       "attention rather than merely tolerating it.",
        "direct": "In partnership, {a}. Lean on that rather than working around "
                  "it.",
    },
    "outer_cost": {
        "reflective": "The cost of that default is worth naming plainly. Left "
                      "unchecked it becomes {a}, and it does so most reliably "
                      "when the situation is urgent and you are certain you are "
                      "right. Nothing about that is unusual or disqualifying — "
                      "every instinct that is good enough to rely on is also "
                      "good enough to run past its own usefulness. The point of "
                      "naming it is that it is recognisable in advance, which "
                      "is the only stage at which it is cheap to correct.",
        "integrative": "Every instinct has a failure mode, and yours is {a}. It "
                       "is not a separate flaw; it is the same reflex running "
                       "without supervision.",
        "direct": "Watch the overextension: {a}. It shows up under pressure, "
                  "not in calm conditions.",
    },
    "strength_calibration": {
        "reflective": "The same capacity has a failure mode, and it is worth "
                      "knowing before it arrives: {a}. That is not a warning "
                      "against the strength — it is what the strength does when "
                      "it stops being examined.",
        "integrative": "Where this strength overreaches, it overreaches "
                       "predictably: {a}. Naming it in advance is most of the "
                       "correction.",
        "direct": "When it overreaches: {a}. It is the same faculty, unchecked.",
    },
    "distinction": {
        "reflective": "It is worth being clear that these two findings are not "
                      "the same signal and do not come from the same place. What "
                      "you can rely on is read from planetary dignity in the "
                      "Navāṁśa; the friction is read from the Navāṁśa ascendant "
                      "itself. A strength is not the absence of the friction, "
                      "and the friction is not a weak planet.",
        "integrative": "These two are separately sourced and should be held "
                       "separately: the dependable capacity comes from how "
                       "planets sit in the Navāṁśa, while the growth edge comes "
                       "from the Navāṁśa ascendant. Neither cancels the other.",
        "direct": "Keep these apart: the strength is a planetary reading, the "
                  "growth edge is an ascendant reading. One does not fix or "
                  "explain the other.",
    },
    "cultivate": {
        "reflective": "What is worth cultivating deliberately is {a} — chosen "
                      "rather than waited for, because it will not arrive by "
                      "temperament alone. This is the constructive face of the "
                      "same Navāṁśa ascendant that supplies the friction above, "
                      "which is worth noticing: the thing to develop and the "
                      "thing to watch are two ends of one pattern, not two "
                      "unrelated instructions.",
        "integrative": "The developmental instruction is straightforward: "
                       "cultivate {a}, and cultivate it on ordinary days rather "
                       "than only in difficulty.",
        "direct": "Cultivate {a}.",
    },
    "watch": {
        "reflective": "What deserves watching is {a}. It rarely announces itself; "
                      "it simply becomes the default when attention drops.",
        "integrative": "The thing to watch for is {a}. Catching it early costs "
                       "very little; catching it late costs a great deal.",
        "direct": "Watch for {a}",
    },
    "integration": {
        "reflective": "Put together, the pattern is coherent rather than "
                      "contradictory. The instinct you lead with and the "
                      "maturity the chart asks for are not opponents — the "
                      "second is what the first becomes when it is held "
                      "deliberately, and the capacity you can depend on is what "
                      "carries you across that distance. The friction is not an "
                      "obstacle sitting outside that process; it is what the "
                      "same material does when the holding lapses. And the "
                      "contribution is not a separate ambition bolted on at the "
                      "end — it is the direction all of it points once the "
                      "development is actually underway.",
        "integrative": "None of these findings needs to be resolved against the "
                       "others. The outer tendency supplies momentum, the "
                       "dependable capacity supplies steadiness, the growth edge "
                       "names what erodes both, and the contribution says what "
                       "the whole arrangement is finally for.",
        "direct": "These are one pattern, not four verdicts: momentum from the "
                  "outer tendency, steadiness from the dependable capacity, "
                  "friction to watch, and a direction the whole thing serves.",
    },
    "instructions": {
        "reflective": "The practical end of all this is small. {a}. It is "
                      "deliberately modest, because the change here comes from "
                      "repetition rather than from decisions.",
        "integrative": "If you take one thing from this reading into the next "
                       "month, take this: {a}. Small and repeatable beats "
                       "decisive here.",
        "direct": "Practise this: {a}. Nothing larger is required.",
    },
}

# Operands that arrive already capitalised and must not be lowercased mid-clause.
TITLE_OPERANDS = {("strength", "a"), ("contribution", "a")}


def _derive_domains(domains: Dict[str, Any]) -> Dict[str, Any]:
    """Split the published material into finer atoms.

    NOTHING NEW IS INTRODUCED. Every derived domain is a slice of a proposition
    already in the publication model — the D1 overextension the Central Theme
    already carries, the calibration shadow already on the Strength card, the
    Cultivate and Watch lines already in the instructions, and one server-owned
    structural statement about how the sections relate.
    """
    out = dict(domains)
    ct = domains.get("central_theme")
    if isinstance(ct, list) and len(ct) > 1:
        out["outer_cost"] = [ct[1]]

    st = domains.get("strength")
    if isinstance(st, dict):
        shadows = st.get("calibration_shadows") or (
            [st["misuse_shadow"]] if st.get("misuse_shadow") else [])
        if shadows:
            out["strength_calibration"] = {"mode": st.get("mode"),
                                           "grahas": st.get("grahas"),
                                           "shadows": shadows}
        if domains.get("growth_edge"):
            # The structural statement is server-owned and takes no operand.
            out["distinction"] = ["distinction"]

    pt = domains.get("partnership")
    if isinstance(pt, dict) and pt.get("orientation"):
        out["partnership_orientation"] = pt["orientation"]

    ins = domains.get("instructions")
    if isinstance(ins, list) and len(ins) >= 4:
        out["cultivate"] = [ins[1]]        # constructive_expression
        out["watch"] = [ins[2]]            # shadow_expression
        out["instructions"] = ins          # practise, unchanged
        out["integration"] = ["integration"]
    return out


def _frame_key(domain: str, value: Any) -> str:
    """Which frame set applies. Driven by the MODE, never by list length."""
    if domain == "partnership" and isinstance(value, dict):
        return "partnership_tiers"
    if domain == "strength" and isinstance(value, dict):
        mode = value.get("mode")
        if mode in ("DUAL", "COMPOUND"):
            return "strength_multi"
        if mode == "FOUNDATIONAL_RESILIENCE":
            return "strength_foundational"
        return "strength"
    if domain == "contribution" and isinstance(value, dict):
        mode = value.get("mode")
        if mode == "COMPOUND_MULTI_POLAR":
            return "contribution_polar"
        vec = value.get("contextual_vector") or {}
        key = vec.get("role_key")
        if mode == "PAIRWISE" and key:
            # Keyed on the deterministic role. A missing or unknown key falls to
            # the plain contribution frame rather than borrowing another role's
            # prose.
            return {"functional_vector": "contribution_functional",
                    "ethical_functional_vector": "contribution_ethical",
                    "aptitude_modifier": "contribution_aptitude"}.get(
                        key, "contribution")
    return domain


def _lower_first(text: str) -> str:
    return text[0].lower() + text[1:] if text[:1].isupper() else text


def _strip_stop(text: str) -> str:
    return text.rstrip(".")


def build_atoms(material: Dict[str, Any]) -> Dict[str, Any]:
    """One atom per substantive domain, each with its variants pre-rendered.

    Every operand comes from `synthesis_material`, which Flight 10 already proved
    contains no proposition absent from the publication model.
    """
    domains = dict((material or {}).get("domains") or {})
    domains = _derive_domains(domains)
    atoms: List[Dict[str, Any]] = []

    for domain in DOMAIN_ORDER:
        value = domains.get(domain)
        if not value:
            continue
        ops = _operands(domain, value)
        if not ops.get("a"):
            continue
        frames = _FRAMES[_frame_key(domain, value)]
        variants = {}
        for name, frame in frames.items():
            try:
                variants[name] = frame.format(
                    a=ops["a"], b=ops.get("b") or ops["a"],
                    c=ops.get("c") or ops.get("b") or ops["a"])
            except (KeyError, IndexError):
                continue
        if variants:
            atoms.append({"id": f"atom.{domain}", "domain": domain,
                          "variants": variants})

    return {"atoms": atoms,
            "atom_ids": [a["id"] for a in atoms],
            "domains": [a["domain"] for a in atoms],
            "connector_ids": sorted(CONNECTORS)}


def _operands(domain: str, value: Any) -> Dict[str, str]:
    """Named-field extraction. NO INDEX EVER CARRIES A SEMANTIC ROLE."""
    if domain == "partnership" and isinstance(value, dict):
        return {"a": _lower_first(_strip_stop(value["field"])),
                "b": f'{value["lord"]}, {value["dignity"].lower()} in the Navāṁśa',
                "c": _lower_first(value["capacity"])}
    if domain == "partnership_orientation":
        joined = " ".join(str(v) for v in (value or []))
        return {"a": _lower_first(_strip_stop(joined))} if joined else {}
    if domain in ("distinction", "integration"):
        return {"a": domain}               # frames take no operand
    if domain == "strength":
        return _strength_operands(value)
    if domain == "strength_calibration":
        shadows = (value or {}).get("shadows") or []
        grahas = (value or {}).get("grahas") or []
        if not shadows:
            return {}
        return {"a": _attributed(grahas, shadows) if len(shadows) > 1
                else _lower_first(shadows[0])}
    if domain == "contribution":
        return _contribution_operands(value)
    if not isinstance(value, list) or not value:
        return {}

    def clause(i: int) -> Optional[str]:
        if i >= len(value) or not isinstance(value[i], str):
            return None
        return _lower_first(_strip_stop(value[i]))

    if domain == "central_theme":
        # Index 0 is the instinctive playbook; index 2 is the MATURE DEMANDED
        # MODE. Index 1 is the emerging bottleneck and belongs to Section 1.
        # 0 instinctive playbook · 2 mature demanded mode · 3 horizon of
        # integration. Index 1 is the emerging bottleneck and belongs to
        # Section 1 and the `outer_cost` atom, not here.
        return {k: v for k, v in
                {"a": clause(0), "b": clause(2) or clause(1),
                 "c": clause(3)}.items() if v}
    if domain == "instructions":
        # [mature_quality, constructive_expression, shadow_expression, practise]
        return {k: v for k, v in {"a": clause(3) or clause(0)}.items() if v}
    return {k: v for k, v in {"a": clause(0), "b": clause(1)}.items() if v}


def _join(items: Sequence[str]) -> str:
    vals = [v for v in items if v]
    if not vals:
        return ""
    if len(vals) == 1:
        return vals[0]
    return ", ".join(vals[:-1]) + " and " + vals[-1]


def _attributed(grahas: Sequence[str], values: Any,
                demechanise: bool = False) -> str:
    """Every value present, each named, joined so it reads as prose.

    Expressions take a possessive — "Moon's psychological safety" — and
    mechanisms keep their own "when", so the clause lands as "Moon when
    emotional perception is treated as...". A bare "Moon, <clause>" parsed as a
    list of two things.

    Symmetric by construction: no index produces a lead, and dropping any graha
    changes the string a test asserts on.
    """
    vals = [v for v in (values or []) if isinstance(v, str)]
    if not vals:
        return ""
    parts = []
    for i, v in enumerate(vals):
        graha = grahas[i] if i < len(grahas) else None
        if demechanise:
            body = _demechanise(v)
            if not body:
                continue
            parts.append(f"{graha} when {body}" if graha else body)
        else:
            body = _lower_first(_strip_stop(v))
            if not body:
                continue
            parts.append(f"{graha}'s {body}" if graha else body)
    return "; ".join(parts)


def _demechanise(text: Optional[str]) -> Optional[str]:
    """The mechanism strings begin "When ..." and the frames supply their own."""
    return re.sub(r"^when\s+", "", _lower_first(_strip_stop(text))) if text else None


def _strength_operands(value: Any) -> Dict[str, str]:
    """Mode-aware. Each operand comes from its OWN Founder field.

    On DUAL and COMPOUND there is no single triple to read, so the frame takes
    the capacity SET and one shared mechanism clause — never another graha's
    core capacity standing in for an expression or a mechanism.
    """
    if not isinstance(value, dict):
        return {}
    mode = value.get("mode")

    if mode == "FOUNDATIONAL_RESILIENCE":
        mq, ce = value.get("mature_quality"), value.get("constructive_expression")
        if not mq:
            return {}
        return {"a": _lower_first(_strip_stop(mq)),
                "b": _lower_first(_strip_stop(ce or value.get("higher_value") or mq))}

    if mode == "SINGLE":
        cap = value.get("core_capacity")
        if not cap:
            return {}
        out = {"a": cap}
        ce = value.get("constructive_expression")
        if ce:
            out["b"] = _lower_first(_strip_stop(ce))
        dm = _demechanise(value.get("dependable_mechanism"))
        if dm:
            out["c"] = dm
        return out

    if mode in ("DUAL", "COMPOUND"):
        caps = value.get("core_capacities") or []
        if not caps:
            return {}
        grahas = value.get("grahas") or []
        # EVERY expression and EVERY mechanism, attributed by graha so no one
        # graha's clause can be read as speaking for the set.
        return {k: v for k, v in {
            "a": _join(caps),
            "b": _attributed(grahas, value.get("constructive_expressions")),
            "c": _attributed(grahas, value.get("dependable_mechanisms"),
                             demechanise=True),
        }.items() if v}
    return {}


def _contribution_operands(value: Any) -> Dict[str, str]:
    """Role-preserving. The dissenting vector and its ROLE NAME both survive."""
    if not isinstance(value, dict):
        return {}
    mode = value.get("mode")

    if mode == "MATURITY_FALLBACK":
        mq, hv = value.get("mature_quality"), value.get("higher_value")
        if not mq:
            return {}
        return {"a": _lower_first(_strip_stop(mq)),
                "b": _lower_first(_strip_stop(hv or mq))}

    if mode == "COMPOUND_MULTI_POLAR":
        impact = _titles(value.get("primary_impact"))
        ethical = _titles(value.get("ethical_driver"))
        aptitude = _titles(value.get("innate_aptitude"))
        if not impact:
            return {}
        return {k: v for k, v in
                {"a": impact, "b": ethical or impact,
                 "c": aptitude or impact}.items() if v}

    primary = _titles(value.get("primary"))
    if not primary:
        return {}
    vector = value.get("contextual_vector") or {}
    vtitles = _titles(vector.get("propositions"))
    if vtitles and vector.get("role_key"):
        # No role STRING is passed as an operand. The role's meaning is written
        # into the frame, so a customer heading can never be inserted as though
        # it were a noun phrase — "its What this contribution should serve is X".
        return {"a": primary, "b": vtitles}
    entries = value.get("primary") or []
    impulse = entries[0].get("core_impulse") if entries else None
    return {k: v for k, v in
            {"a": primary,
             "b": (_strip_stop(impulse) + ".") if impulse else None}.items() if v}


def _titles(entries: Any) -> str:
    return _join([e["title"] for e in (entries or [])
                  if isinstance(e, dict) and e.get("title")])


# ═════════════════════════════════════════════════════════════════════════════
# PROVIDER PLAN · parse, validate, render
# ═════════════════════════════════════════════════════════════════════════════

def parse_plan(raw: str) -> Dict[str, Any]:
    """Identifiers only. A prose value anywhere is itself the violation."""
    text = (raw or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\s*|\s*```$", "", text).strip()
    try:
        payload = json.loads(text)
    except Exception as exc:
        raise NarrativeContractError(f"plan is not JSON: {exc}")
    if not isinstance(payload, dict):
        raise NarrativeContractError("plan is not an object")

    allowed = {"order", "variants", "connectors", "paragraph_break_after"}
    extra = set(payload) - allowed
    if extra:
        raise NarrativeContractError(
            f"unexpected keys {sorted(extra)}; there is no free-text field")

    order = payload.get("order")
    if not isinstance(order, list) or not all(isinstance(x, str) for x in order):
        raise NarrativeContractError("order must be a list of atom ids")
    variants = payload.get("variants") or {}
    if not isinstance(variants, dict):
        raise NarrativeContractError("variants must be an object")
    connectors = payload.get("connectors") or []
    if not isinstance(connectors, list):
        raise NarrativeContractError("connectors must be a list")
    breaks = payload.get("paragraph_break_after") or []
    if not isinstance(breaks, list):
        raise NarrativeContractError("paragraph_break_after must be a list")
    return {"order": order, "variants": variants, "connectors": connectors,
            "paragraph_break_after": breaks}


def validate_plan(plan: Dict[str, Any], pool: Dict[str, Any]) -> Dict[str, Any]:
    """Membership, uniqueness, cardinality and domain spread. Fail closed."""
    known = set(pool["atom_ids"])
    order = plan["order"]

    if not (MIN_ATOMS <= len(order) <= MAX_ATOMS):
        raise NarrativeContractError(
            f"order selects {len(order)} atoms; permitted {MIN_ATOMS}-{MAX_ATOMS}")
    if len(set(order)) != len(order):
        raise NarrativeContractError("an atom is selected more than once")
    for atom_id in order:
        if atom_id not in known:
            raise NarrativeContractError(f"unknown atom {atom_id!r}")
    for atom_id, variant in plan["variants"].items():
        if atom_id not in known:
            raise NarrativeContractError(f"variant for unknown atom {atom_id!r}")
        if variant not in VARIANTS:
            raise NarrativeContractError(f"unknown variant {variant!r}")
    for c in plan["connectors"]:
        if c not in CONNECTORS:
            raise NarrativeContractError(f"unknown connector {c!r}")
    for atom_id in plan["paragraph_break_after"]:
        if atom_id not in order:
            raise NarrativeContractError(
                f"paragraph break after unselected atom {atom_id!r}")

    available = len(pool["atom_ids"])
    required = min(MIN_DOMAINS, available)
    by_id = {a["id"]: a for a in pool["atoms"]}
    spread = {by_id[a]["domain"] for a in order}
    if len(spread) < required:
        raise NarrativeContractError(
            f"plan spans {len(spread)} domains; {required} required")
    return plan


SENTENCE_START = re.compile(r'(^|(?<=[.!?])\s+)([a-z])')


# THE SEAM DEFECT IS FIXED IN THE FRAMES, NOT BY A REGEX.
#
# Flight 15 produced "...humble self-correction This is read..." because a frame
# continued after an operand that had already been stripped of its full stop. A
# post-hoc regex looked tempting and is wrong: "Ethical Perspective & Sound
# Counsel" is a legitimate capitalised title mid-sentence, and any rule blunt
# enough to seal the seam is blunt enough to split that. Every frame that
# continues after an operand now carries its own punctuation, and a test asserts
# the invariant across all frames.


def _fix_prose(text: str) -> str:
    """Mechanical grammar repair on server-owned strings only.

    Flight 14 shipped "the practical end of all this is small. before acting..."
    in a paid flagship report. Sentence starts are capitalised, duplicate
    punctuation collapsed, and spacing normalised. No wording is invented — this
    only fixes the seams where server strings are joined.
    """
    text = re.sub(r'\s+([.,;:])', r'\1', text)
    text = re.sub(r'([.;,:])\1+', r'\1', text)
    text = re.sub(r'\.\s*\.', '.', text)
    text = re.sub(r'[ \t]{2,}', ' ', text)
    text = SENTENCE_START.sub(lambda m: m.group(1) + m.group(2).upper(), text)
    return text.strip()


def render(plan: Dict[str, Any], pool: Dict[str, Any]) -> str:
    """Server strings only. Nothing the provider sent appears in the output."""
    by_id = {a["id"]: a for a in pool["atoms"]}
    connectors = list(plan.get("connectors") or [])
    breaks = set(plan.get("paragraph_break_after") or [])

    paragraphs: List[List[str]] = [[]]
    for i, atom_id in enumerate(plan["order"]):
        atom = by_id[atom_id]
        variant = plan["variants"].get(atom_id, "reflective")
        text = atom["variants"].get(variant) or next(iter(atom["variants"].values()))
        if not text.endswith("."):
            text += "."
        if i and paragraphs[-1]:
            key = connectors[i - 1] if i - 1 < len(connectors) else "none"
            lead, lower = CONNECTORS.get(key, ("", False))
            if lead:
                text = lead + (_lower_first(text) if lower else text)
        paragraphs[-1].append(text)
        if atom_id in breaks and i < len(plan["order"]) - 1:
            paragraphs.append([])

    body = "\n\n".join(" ".join(p) for p in paragraphs if p)
    out = (OPENING + body + " " + CLOSING).strip()
    return "\n\n".join(_fix_prose(par) for par in out.split("\n\n"))


def canonical_plan(pool: Dict[str, Any]) -> Dict[str, Any]:
    """THE DETERMINISTIC FALLBACK.

    Used whenever the provider is unavailable or its plan fails validation. It
    is a real synthesis over the same server-owned atoms in the server's own
    editorial order — the reader gets a Final Synthesis either way, and the only
    thing lost is the provider's ordering judgement.
    """
    ids = pool["atom_ids"][:MAX_ATOMS]
    variants = {}
    for i, atom_id in enumerate(ids):
        variants[atom_id] = ("reflective", "integrative", "direct")[i % 3]
    connectors = ["none"] + ["also", "alongside", "another_part",
                             "at_the_same_time"][:max(0, len(ids) - 1)]
    # A 900-word reading in two paragraphs is a wall. Break roughly every third
    # atom, never after the last one.
    breaks = [ids[i] for i in range(2, len(ids) - 1, 3)]
    return {"order": ids, "variants": variants,
            "connectors": connectors[:max(0, len(ids) - 1)],
            "paragraph_break_after": breaks}


def _longest_plan(pool: Dict[str, Any]) -> Dict[str, Any]:
    """EVERY atom, in the server's editorial order, at its fullest register.

    Completeness first: the flagship reading should carry every finding the
    chart actually supports, and depth follows from that rather than from
    stretching a few atoms.
    """
    plan = canonical_plan(pool)
    by_id = {a["id"]: a for a in pool["atoms"]}
    plan["variants"] = {
        atom_id: max(by_id[atom_id]["variants"],
                     key=lambda v: len(by_id[atom_id]["variants"][v]))
        for atom_id in plan["order"]}
    return plan


def build_final_synthesis(material: Dict[str, Any],
                          provider=None) -> Dict[str, Any]:
    """One provider call, then deterministic fallback. Never a missing section.

    No diagnostic ever reaches the caller's payload: no response body, no
    billing text, no correlation id, no exception detail. Those are logged.
    """
    pool = build_atoms(material)
    if len(pool["atoms"]) < MIN_ATOMS:
        return {"final_synthesis": None, "synthesis_source": "insufficient_material"}

    # DEPTH IS EVIDENCE-RESPONSIVE, AND NEVER REACHED BY REPETITION.
    #
    # The deterministic reading uses EVERY available atom at its fullest
    # register. Its length is therefore whatever the chart actually supports —
    # a well-supported chart lands in the 800-1200 target, a genuinely thin one
    # comes in shorter, and neither is padded.
    #
    # A provider plan is accepted only if it is at least as complete as the
    # deterministic reading and stays under the hard ceiling. A provider cannot
    # shorten the flagship section by dropping findings.
    baseline = render(_longest_plan(pool), pool)
    baseline_words = len(baseline.split())
    floor = min(DEPTH_TARGET[0], baseline_words)

    text = None
    source = "deterministic"
    if provider is not None:
        try:
            raw = provider(build_instruction(pool), build_user_prompt(pool))
            plan = validate_plan(parse_plan(raw), pool)
            candidate = render(plan, pool)
            words = len(candidate.split())
            if words < floor:
                raise NarrativeContractError(
                    f"rendered plan is {words} words; at least {floor} required")
            if words > TARGET_WORDS[1]:
                raise NarrativeContractError(
                    f"rendered plan is {words} words; ceiling {TARGET_WORDS[1]}")
            text, source = candidate, "provider"
        except Exception:
            LOG.warning("d9 r2 synthesis plan rejected; using canonical plan",
                        exc_info=True)
            text = None

    if text is None:
        text = baseline
        if baseline_words > TARGET_WORDS[1]:
            LOG.info("d9 r2 deterministic reading over ceiling (%s words)",
                     baseline_words)

    return {"final_synthesis": text, "synthesis_source": source}


# ═════════════════════════════════════════════════════════════════════════════
# PROMPTS
# ═════════════════════════════════════════════════════════════════════════════

def build_instruction(pool: Dict[str, Any]) -> str:
    required = min(MIN_DOMAINS, len(pool["atom_ids"]))
    return f"""You are ordering the closing synthesis of a Navamsha reading.

You do NOT write sentences. Every sentence is already written. You choose which
statements appear, in what order, in which register, how each is joined to the
one before, and where the paragraphs break.

Return ONLY a JSON object with exactly these keys:

{{
  "order": ["<atom id>", ...],
  "variants": {{"<atom id>": "reflective|integrative|direct"}},
  "connectors": ["<connector id>", ...],
  "paragraph_break_after": ["<atom id>", ...]
}}

Rules:
1. Every id must come from the supplied lists. Nothing else is accepted.
2. Select between {MIN_ATOMS} and {MAX_ATOMS} atoms, none twice.
3. Your selection must span at least {required} distinct domains.
4. `connectors` has one entry per join, so one fewer than the number of atoms.
5. Break into 2 to 4 natural paragraphs. Do not break after the final atom.
6. Order so the piece reads as one thought: what frames the person first, what
   they can act on last.
7. There is no field for your own words. A response with any other key is
   discarded and the server composes the piece itself.
8. Return raw JSON. No markdown fence, no preamble."""


def build_user_prompt(pool: Dict[str, Any]) -> str:
    """NO USER NAME. The provider selects identifiers and writes no prose, so a
    name contributes nothing to the output and its transfer buys nothing."""
    return ("ATOMS — the complete set. Nothing else exists:\n"
            + json.dumps(pool["atoms"], indent=1, ensure_ascii=False)
            + "\n\nCONNECTOR IDS:\n" + json.dumps(pool["connector_ids"])
            + "\n\nReturn the JSON plan.")
