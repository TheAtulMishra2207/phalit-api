"""D9-R2 · d9_r2_publication · the deterministic customer report model.

Selectors in, structured report out. **No provider prose.** Flight 6 proves the
material substrate is sufficient; it does not render anything.

TWO STRUCTURAL RULES, and both are enforced rather than documented.

1 · ABSENCE CHANGES THE SHAPE, RECURSIVELY. An unsupported key is omitted at
    ANY depth — not just at the top level. Flight 6 claimed this and checked only
    top-level values, so `vargottama_modifier: None`, empty
    `vargottama_modifiers` and `published_dignity: None` all reached the customer
    model while the test stayed green. `prune()` now walks the whole tree and a
    test walks it again to confirm.

    There is no `available: False`, no `reason`, no `not_shown`, no `NO_SIGNAL`,
    no `REDUCED`.

2 · THE SYNTHESIS MATERIAL INTRODUCES NOTHING. Every proposition it carries is
    already present elsewhere in the model, and a test proves it by string
    containment rather than by inspection.

No `timing` key exists, and no R1 concept survives: Guiding Frequency, Career &
Purpose, Growth Frontiers and Daily Alignment are all gone.
"""

from typing import Any, Dict, List, Optional, Sequence

import d9_r2_doctrine as doc

REPORT_VERSION = "d9-r2"

PUBLIC_TITLE = "Navāṁśa · Marriage, Maturity & Dharma"
PUBLIC_SUBTITLE = ("How your inner nature, partnership and deeper life pattern "
                   "develop")

# SERVER-OWNED COPY. The provider never writes any of this.
#
# Every claim below is structural — what the Navāṁśa IS and how this report uses
# it. No timing folklore: no age-32 or age-36 activation, no Saturn-return
# switch, no automatic early/late destiny rule from D1/D9 strength, and no
# categorical "four minutes changes the D9 Lagna".
NAVAMSHA_EXPLAINER = {
    "heading": "What the Navāṁśa Reveals",
    "paragraphs": [
        "The Navāṁśa is the ninth divisional chart. It is not a second horoscope "
        "and not a prediction of different events — it is your own birth data "
        "read at finer resolution, with each sign divided into nine parts and "
        "every planet and the ascendant mapped into that finer framework.",
        "It is read together with your natal chart rather than instead of it. "
        "Where the natal chart shows how you meet the world, the Navāṁśa shows "
        "what those same tendencies mature into when they are developed "
        "deliberately.",
        "This reading covers four things: how your natal tendencies mature, what "
        "partnership asks of you where the chart directly supports a statement, "
        "the kind of contribution your effort is suited to, and the capacities "
        "you can depend on. It is not an event-timing report.",
    ],
}

SCOPE_NOTE = {
    "heading": "How to use this reading",
    "points": [
        "The Navāṁśa deepens and qualifies your natal chart. It does not replace "
        "it, and it is not a separate fate.",
        "Contribution describes the kind of value your work tends to create. It "
        "is not a profession prediction — career mechanics belong to the "
        "Dashamsha reading.",
        "This reading does not tell you when things happen. Timing belongs to "
        "Dashā analysis.",
        "Nothing here prescribes a remedy. Remedial guidance belongs to the "
        "Remedial Dossier.",
    ],
}

CONTRIBUTION_NOTE = ("Contribution describes how the chart tends to create value "
                     "or serve a larger purpose. It is not a profession "
                     "prediction; detailed career mechanics belong to the "
                     "Dashamsha reading.")

# Plain-language public labels for the Founder-locked role names. The engine
# name survives in the Astrological Basis for an auditing reader.
CONTRIBUTION_ROLE_LABELS = {
    "primary_mode": "Primary Contribution Mode",
    "primary_contribution_mode": "Primary Contribution Mode",
    "functional_vector": "How this contribution reaches the world",
    "ethical_functional_vector": "How this contribution should be carried",
    "aptitude_modifier": "The aptitude underneath it",
    "primary_impact_vector": "Where the visible impact lands",
    "ethical_driver": "What drives it",
    "innate_aptitude": "The aptitude underneath it",
}
CONTRIBUTION_ROLE_TECHNICAL = {
    "functional_vector": "Functional / Impact Vector",
    "ethical_functional_vector": "Ethical Functional Vector",
    "aptitude_modifier": "Innate / Aptitude Modifier",
    "primary_impact_vector": "Primary Impact Vector",
    "ethical_driver": "Ethical Driver",
    "innate_aptitude": "Innate Aptitude",
}

# Vocabulary that must never appear anywhere in a built model.
ARCHETYPE_ENUM_IDS = tuple(a.value for a in doc.ARCHETYPES)


class R2PublicationViolation(Exception):
    """Internal provenance or telemetry reached a customer surface."""


# ═════════════════════════════════════════════════════════════════════════════
# THE CUSTOMER-PROVENANCE GATE · general, not a point fix
# ═════════════════════════════════════════════════════════════════════════════
#
# Four flights running, each correction fixed the instance QA named and left the
# adjacent one standing — Contribution cleaned while Growth Edge, Strength
# fallback and Partnership still carried `source` and `basis`. This gate walks
# the whole customer tree by KEY, so the next instance is caught here rather
# than in review.
#
# Keys, not string scanning: a value may legitimately contain the word "source",
# and a key named `source` is provenance whatever it holds.

CUSTOMER_FORBIDDEN_KEYS = frozenset({
    "source", "basis", "confidence", "_provenance", "provenance",
    "rule_id", "rule_ids", "weight", "weights", "score", "scores",
    "debug", "telemetry", "provider", "scanner", "traceback",
    "correlation_id", "certified_rank", "frame",
})

# The one intentional technical section. Excluded by PATH, not by key name, so
# nothing else inherits the exemption.
TECHNICAL_SECTIONS = ("astrological_basis",)


def scan_customer_provenance(report: Dict[str, Any]) -> List[str]:
    """Every forbidden key on a customer surface, with its path."""
    found: List[str] = []

    def walk(node: Any, path: str) -> None:
        if isinstance(node, dict):
            for k, v in node.items():
                if k in TECHNICAL_SECTIONS and path == "$":
                    continue                      # the technical section only
                if k in CUSTOMER_FORBIDDEN_KEYS:
                    found.append(f"{path}.{k}")
                walk(v, f"{path}.{k}")
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, f"{path}[{i}]")

    walk(report, "$")
    return found


def assert_customer_clean(report: Dict[str, Any]) -> None:
    hits = scan_customer_provenance(report)
    if hits:
        raise R2PublicationViolation(
            f"internal provenance on a customer surface: {hits}")

FORBIDDEN_PUBLICATION_VOCABULARY = (
    "NO_SIGNAL", "REDUCED", "Not shown", "not_shown", "unavailable",
    "misuse_shadow",          # exists only under calibration, never as a key
    "Guiding Frequency", "Career & Purpose", "Growth Frontiers",
    "Daily Alignment", "timing", "Timing",
)


def prune(value: Any) -> Any:
    """Drop None, {} and [] RECURSIVELY, bottom-up.

    Bottom-up matters: a dict whose only entries were None becomes {} and is then
    dropped by its own parent. A single-pass top-level filter leaves exactly the
    nested emptiness Flight 6 shipped.

    `False` and `0` are preserved — they are values, not absences.
    """
    if isinstance(value, dict):
        cleaned = {k: prune(v) for k, v in value.items()}
        return {k: v for k, v in cleaned.items()
                if v is not None and v != {} and v != []}
    if isinstance(value, list):
        cleaned = [prune(v) for v in value]
        return [v for v in cleaned if v is not None and v != {} and v != []]
    return value


def scan_empties(value: Any, path: str = "$") -> List[str]:
    """Every surviving None/{}/[] with its path. Empty means clean."""
    found: List[str] = []
    if isinstance(value, dict):
        for k, v in value.items():
            if v is None or v == {} or v == []:
                found.append(f"{path}.{k}")
            else:
                found.extend(scan_empties(v, f"{path}.{k}"))
    elif isinstance(value, list):
        for i, v in enumerate(value):
            if v is None or v == {} or v == []:
                found.append(f"{path}[{i}]")
            else:
                found.extend(scan_empties(v, f"{path}[{i}]"))
    return found


# ═════════════════════════════════════════════════════════════════════════════
# STRENGTH · the customer projection · ONE home for the shadow
# ═════════════════════════════════════════════════════════════════════════════

CALIBRATION_LABEL = "When this strength overreaches..."


def strength_public(selection: Dict[str, Any]) -> Dict[str, Any]:
    """Project the selector's source model onto the customer surface.

    THE PRIMARY SURFACE CARRIES ONLY core capacity, constructive expression and
    dependable mechanism. Flight 6 emitted `misuse_shadow` at the strength root
    AND inside `calibration`, giving one proposition two publication paths — and
    a boundary with two doors is not a boundary.

    The selector output may stay richer for provenance. This is what publishes.
    """
    mode = selection.get("mode")
    out: Dict[str, Any] = {"mode": mode}

    if mode == "FOUNDATIONAL_RESILIENCE":
        # Only meaningful fallback fields. No `grahas: []`, no null dignity —
        # technical emptiness is not published to prove nothing was elected.
        # No `basis` — that discriminator is internal.
        for f in ("title", "mature_quality", "constructive_expression",
                  "higher_value"):
            if selection.get(f):
                out[f] = selection[f]
        return out

    for f in ("published_dignity", "title", "graha", "grahas", "core_capacity",
              "core_capacities", "constructive_expression",
              "constructive_expressions", "dependable_mechanism",
              "dependable_mechanisms", "co_equal"):
        if selection.get(f) is not None:
            out[f] = selection[f]

    shadows = ([selection["misuse_shadow"]] if selection.get("misuse_shadow")
               else list(selection.get("calibration_shadows") or []))
    if shadows:
        out["calibration"] = {"label": CALIBRATION_LABEL, "shadows": shadows}

    mods = selection.get("vargottama_modifiers")
    if selection.get("vargottama_modifier"):
        out["vargottama_modifier"] = selection["vargottama_modifier"]
    elif mods:
        out["vargottama_modifiers"] = mods
    return out


def growth_edge_public(selection: Dict[str, Any]) -> Dict[str, Any]:
    """Human content only. `source` is provenance and stays upstream."""
    return {k: selection[k] for k in ("growth_edge", "mature_counterpart")
            if selection.get(k)}


def partnership_public(selection: Dict[str, Any]) -> Dict[str, Any]:
    """Customer projection for Partnership Dynamics.

    Handles the Flight 16 three-tier shape and strips provenance — `frame`,
    `basis` and `confidence` are technical evidence and live in the
    Astrological Basis, never in the human section.

    The legacy `sections` shape is still projected so earlier suites and any
    caller that has not moved yet keep working.
    """
    if not selection:
        return {}

    if selection.get("relational_field"):
        out: Dict[str, Any] = {"heading": selection.get("heading",
                                                        "Partnership Dynamics")}
        rf = selection["relational_field"]
        out["relational_field"] = {"sign": rf["sign"], "statement": rf["statement"]}
        gf = selection["governing_function"]
        out["governing_function"] = {"graha": gf["graha"],
                                     "dignity": gf["dignity"],
                                     "statement": gf["statement"]}
        ko = selection.get("karmic_orientation") or []
        if ko:
            out["karmic_orientation"] = [{"graha": o["graha"],
                                          "statement": o["statement"]}
                                         for o in ko]
        return out

    sections = [{"heading": sec["heading"], "statements": list(sec["statements"])}
                for sec in (selection.get("sections") or [])
                if sec.get("statements")]
    return {"sections": sections} if sections else {"sections": []}


def build_d9_chart_projection(d9_lagna_sign_index: int,
                              placements: Dict[str, Any],
                              signs: Sequence[str]) -> Dict[str, Any]:
    """DISPLAY-ONLY projection of already-certified D9 placements.

    The browser gets houses, signs and occupants as finished values. There is no
    arithmetic left for it to do and therefore no second D9 engine — the frontend
    becomes a pure renderer of this structure.
    """
    if not isinstance(d9_lagna_sign_index, int) or not signs:
        return {}
    houses = []
    for h in range(1, 13):
        idx = (d9_lagna_sign_index + h - 1) % 12
        houses.append({"house": h, "sign": signs[idx],
                       "sign_number": idx + 1, "grahas": []})
    for graha, rec in (placements or {}).items():
        si = rec.get("d9_sign_index")
        if not isinstance(si, int) or isinstance(si, bool):
            continue
        house = ((si - d9_lagna_sign_index) % 12) + 1
        houses[house - 1]["grahas"].append(graha)
    for h in houses:
        h["grahas"].sort(key=lambda g: list(placements).index(g)
                         if g in placements else 99)
    return {"style": "north_indian", "lagna_house": 1,
            "lagna_sign": signs[d9_lagna_sign_index % 12], "houses": houses}


def build_reading_basis(d1_lagna: str, d9_lagna: str,
                        strength: Dict[str, Any],
                        contribution: Optional[Dict[str, Any]],
                        partnership_published: bool) -> Dict[str, str]:
    """One short evidence line per major interpretation.

    THE STRENGTH / GROWTH EDGE DISTINCTION IS THE POINT. The elected graha is
    named against the Strength only; the Growth Edge names the D9 Lagna sign and
    never a graha, so a reader cannot infer "Jupiter good, Mars bad" from a
    section that never elected Mars.
    """
    out: Dict[str, str] = {}
    if d1_lagna and d9_lagna:
        out["central_theme"] = (f"{d1_lagna} natal orientation → "
                                f"{d9_lagna} Navāṁśa maturity")
    grahas = strength.get("grahas") or []
    if grahas:
        dignity = strength.get("published_dignity")
        who = " · ".join(grahas)
        out["strength"] = f"{who} · {dignity} in the Navāṁśa" if dignity else who
    elif strength.get("mode") == "FOUNDATIONAL_RESILIENCE":
        out["strength"] = f"{d9_lagna} Navāṁśa Lagna · no single elected placement"
    if d9_lagna:
        out["growth_edge"] = f"{d9_lagna} Navāṁśa Lagna maturity pattern"
        out["instructions"] = f"{d9_lagna} Navāṁśa Lagna maturity pattern"
    if contribution:
        out["dharma_contribution"] = ("Karakāṁśa 5th, 9th and 10th domains")
    if partnership_published:
        out["partnership"] = "Karakāṁśa 7th domain · directly supported evidence"
    return out


def build_key_anchors(d1_lagna: str, d9_lagna: str,
                      strength: Dict[str, Any],
                      contribution: Optional[Dict[str, Any]]) -> List[Dict[str, str]]:
    """The compact orientation row. Deterministic payload values, no enums."""
    rows = []
    if d1_lagna:
        rows.append({"label": "Outer tendency", "value": d1_lagna})
    if d9_lagna:
        rows.append({"label": "Navāṁśa Lagna", "value": d9_lagna})
    grahas = strength.get("grahas") or []
    if grahas:
        rows.append({"label": "Reliable strength", "value": " · ".join(grahas)})
    elif strength.get("mode") == "FOUNDATIONAL_RESILIENCE":
        rows.append({"label": "Reliable strength", "value": "Foundational Resilience"})
    if contribution:
        titles = []
        for key in ("primary_mode", "primary_contribution_mode",
                    "primary_impact_vector"):
            titles = [e["title"] for e in (contribution.get(key) or [])]
            if titles:
                break
        if titles:
            rows.append({"label": "Contribution", "value": " · ".join(titles)})
        elif contribution.get("mode") == "MATURITY_FALLBACK":
            rows.append({"label": "Contribution",
                         "value": "Read from Navāṁśa Lagna maturity"})
    return rows


def build_report(chart_token: str,
                 central_theme: Dict[str, str],
                 strength: Dict[str, Any],
                 growth_edge: Dict[str, str],
                 instructions: Dict[str, Any],
                 partnership: Optional[Dict[str, Any]] = None,
                 contribution: Optional[Dict[str, Any]] = None,
                 astrological_basis: Optional[Dict[str, Any]] = None,
                 d9_chart: Optional[Dict[str, Any]] = None,
                 reading_basis: Optional[Dict[str, str]] = None,
                 key_anchors: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
    """Assemble the model. Optional blocks are OMITTED, never emptied."""
    signatures: Dict[str, Any] = {"strength": strength_public(strength),
                                  "growth_edge": growth_edge_public(growth_edge)}

    # Dharma & Contribution is optional. A suppressed convergence contributes
    # its authorised fallback or nothing at all — never a placeholder.
    if contribution is not None:
        block = _contribution_block(contribution)
        if block is not None:
            signatures["dharma_contribution"] = block

    report: Dict[str, Any] = {
        "report_version": REPORT_VERSION,
        "chart_token": chart_token,
        "title": PUBLIC_TITLE,
        "subtitle": PUBLIC_SUBTITLE,
        "explainer": NAVAMSHA_EXPLAINER,
        "scope_note": SCOPE_NOTE,
        "contribution_note": CONTRIBUTION_NOTE,
        "central_theme": central_theme,
        "defining_signatures": signatures,
        "instructions": instructions,
    }

    # Partnership is evidence-responsive: present only when a section survived.
    # Section 3 is UNIVERSAL now: tiers 1 and 2 always resolve, so the block is
    # always present. It carries no `basis` or `confidence` provenance.
    if partnership:
        pp = partnership_public(partnership)
        # Section 3 is universal under the Flight 16 architecture, but the
        # legacy shape can still yield nothing — omit rather than publish empty.
        if pp.get("relational_field") or pp.get("sections"):
            report["partnership"] = pp

    if d9_chart:
        report["d9_chart"] = d9_chart
    if key_anchors:
        report["key_anchors"] = key_anchors
    if reading_basis:
        report["reading_basis"] = reading_basis
    if astrological_basis:
        # THE FLIGHT 10 SEAM, CLOSED AT THE WIRING PHASE.
        #
        # Flight 10 accepted whatever dictionary a caller passed. The safe
        # builder existed and nothing required its use, so a route could
        # hand-roll the appendix and publish rule ids — and an output-only test
        # would still pass, because the output looks the same right up until it
        # does not.
        leaked = scan_basis_telemetry(astrological_basis)
        if leaked:
            raise R2PublicationViolation(
                f"astrological_basis carries telemetry {sorted(leaked)}; build it "
                f"through build_astrological_basis()")
        unknown = set(astrological_basis) - set(BASIS_PERMITTED_KEYS)
        if unknown:
            raise R2PublicationViolation(
                f"astrological_basis has unpermitted keys {sorted(unknown)}")
        report["astrological_basis"] = astrological_basis

    report["synthesis_material"] = build_synthesis_material(report)
    cleaned = prune(report)
    # FAIL CLOSED. The gate runs on every build, not only in tests.
    assert_customer_clean(cleaned)
    return cleaned


# Internal mechanics. Useful to QA, meaningless to a reader, and — like the enum
# identifiers — never customer content.
CONTRIBUTION_TOPOLOGY_FIELDS = (
    "agreeing_domains", "dissenting_domain", "dissenting_role",
    "precedence_applied", "aptitude_modifier_domain", "supporting_domains",
    "integrated", "competing_pairs", "roles", "dissenting_signal",
)


def _human_propositions(entries: Any) -> List[Dict[str, str]]:
    """Keep title and core impulse. DROP the enum identifier.

    `KNOWLEDGE_TRANSMISSION` is an internal id. A reader needs the title and the
    impulse, and the synthesis substrate already proves nothing downstream
    requires the id.
    """
    return [{"title": e["title"], "core_impulse": e["core_impulse"]}
            for e in entries or []
            if isinstance(e, dict) and e.get("title") and e.get("core_impulse")]


def _contribution_block(conv: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """The CUSTOMER projection. Human meaning only.

    Flight 8 cleaned the synthesis substrate and left the customer model still
    carrying enum ids, `agreeing_domains`, `dissenting_domain`,
    `precedence_applied` and the rest. The Flight 8 rule — one publication path
    per human proposition, internal mechanics elsewhere — applies here too, and
    I applied it one layer short.

    Topology stays available on the selector output for QA. It does not reach a
    reader.
    """
    kind = conv.get("convergence")
    name = getattr(kind, "value", kind)

    if name == "SUPPRESSED":
        fb = conv.get("fallback_material")
        if not fb:
            return None
        return {"mode": "MATURITY_FALLBACK",
                **{k: fb[k] for k in ("mature_quality", "higher_value")
                   if fb.get(k)}}

    out: Dict[str, Any] = {"mode": name}
    if name == "UNIFIED_PURPOSE":
        out["primary_mode"] = _human_propositions(conv.get("primary_mode"))
        out["conviction"] = conv.get("label") or doc.UNIFIED_PURPOSE_LABEL
        return out

    if name == "PAIRWISE":
        out["primary_contribution_mode"] = _human_propositions(
            conv.get("primary_contribution_mode"))
        for key in ("functional_vector", "ethical_functional_vector",
                    "aptitude_modifier"):
            vec = _human_propositions(conv.get(key))
            if vec:
                out[key] = vec
                break
        return out

    if name == "COMPOUND_MULTI_POLAR":
        for key in ("primary_impact_vector", "ethical_driver",
                    "innate_aptitude"):
            vec = _human_propositions(conv.get(key))
            if vec:
                out[key] = vec
        return out
    return None


# ═════════════════════════════════════════════════════════════════════════════
# ASTROLOGICAL BASIS · facts actually consumed, nothing else
# ═════════════════════════════════════════════════════════════════════════════

# The complete permitted key set. A basis built any other way fails closed.
BASIS_PERMITTED_KEYS = (
    "d1_lagna", "d9_lagna", "d9_lagna_lord", "atmakaraka", "swamsa",
    "strength_grahas", "published_dignity", "vargottama",
    "karakamsha_evidence", "relationship_evidence",
    "d9_seventh_sign", "d9_seventh_lord", "d9_seventh_lord_dignity",
    "karakamsha_h7_sign", "karakamsha_h7_occupants",
    "growth_edge_source", "contribution_convergence", "contribution_roles",
    "instructions_source",
)

BASIS_TELEMETRY_BANNED = ("rule_id", "rule_ids", "weight", "weights", "score",
                          "debug", "telemetry", "provider", "scanner",
                          "traceback", "correlation_id", "certified_rank")


def build_astrological_basis(d1_lagna: str, d9_lagna: str,
                             d9_lagna_lord: Optional[str] = None,
                             atmakaraka: Optional[str] = None,
                             swamsa: Optional[str] = None,
                             strength_grahas: Sequence[str] = (),
                             published_dignity: Optional[Dict[str, str]] = None,
                             vargottama: Optional[Dict[str, bool]] = None,
                             karakamsha_evidence: Optional[Dict[str, Any]] = None,
                             relationship_evidence: Optional[Sequence[str]] = None,
                             d9_seventh_sign: Optional[str] = None,
                             d9_seventh_lord: Optional[str] = None,
                             d9_seventh_lord_dignity: Optional[str] = None,
                             karakamsha_h7_sign: Optional[str] = None,
                             karakamsha_h7_occupants: Optional[Sequence[str]] = None,
                             growth_edge_source: Optional[str] = None,
                             contribution_convergence: Optional[str] = None,
                             contribution_roles: Optional[Sequence[str]] = None,
                             instructions_source: Optional[str] = None
                             ) -> Dict[str, Any]:
    """Only what R2 actually consumed. No rule ids, weights or telemetry."""
    basis: Dict[str, Any] = {"d1_lagna": d1_lagna, "d9_lagna": d9_lagna}
    if d9_lagna_lord:
        basis["d9_lagna_lord"] = d9_lagna_lord
    if atmakaraka:
        basis["atmakaraka"] = atmakaraka          # omitted when AK_AMBIGUOUS
    if swamsa:
        basis["swamsa"] = swamsa
    if strength_grahas:
        basis["strength_grahas"] = list(strength_grahas)
        if published_dignity:
            basis["published_dignity"] = {
                g: published_dignity[g] for g in strength_grahas
                if g in published_dignity}
    if vargottama:
        rooted = sorted(g for g, v in vargottama.items() if v)
        if rooted:
            basis["vargottama"] = rooted
    if karakamsha_evidence:
        # Frames stay explicitly named. Never generic H5/H9/H10.
        basis["karakamsha_evidence"] = {
            f"KARAKAMSHA_H{h}_D1_FRAME": ev
            for h, ev in karakamsha_evidence.items()}
    if relationship_evidence:
        basis["relationship_evidence"] = list(relationship_evidence)
    # Section 3 evidence. `karakamsha_h7_occupants` reports "none" in the
    # technical drawer when empty — the MAIN reading simply omits the Karmic
    # Orientation card rather than publishing an empty one.
    if d9_seventh_sign:
        basis["d9_seventh_sign"] = d9_seventh_sign
    if d9_seventh_lord:
        basis["d9_seventh_lord"] = d9_seventh_lord
    if d9_seventh_lord_dignity:
        basis["d9_seventh_lord_dignity"] = d9_seventh_lord_dignity
    if karakamsha_h7_sign:
        basis["karakamsha_h7_sign"] = karakamsha_h7_sign
    if d9_seventh_sign:
        basis["karakamsha_h7_occupants"] = (list(karakamsha_h7_occupants)
                                            if karakamsha_h7_occupants else "none")
    # Enough for an informed reader to audit the report without raw JSON.
    if growth_edge_source:
        basis["growth_edge_source"] = growth_edge_source
    if contribution_convergence:
        basis["contribution_convergence"] = contribution_convergence
    if contribution_roles:
        basis["contribution_roles"] = list(contribution_roles)
    if instructions_source:
        basis["instructions_source"] = instructions_source

    # FAIL CLOSED, and never scrub. `scan_basis_telemetry` existed since Flight 6
    # and nothing called it — a detector that is never enforced is not a wall.
    hits = scan_basis_telemetry(basis)
    if hits:
        raise R2PublicationViolation(
            f"telemetry in the Astrological Basis: {sorted(set(hits))}")
    return basis


# ═════════════════════════════════════════════════════════════════════════════
# SYNTHESIS MATERIAL · substrate only, zero novel propositions
# ═════════════════════════════════════════════════════════════════════════════

SYNTHESIS_DOMAINS = ("central_theme", "strength", "growth_edge",
                     "contribution", "partnership", "instructions")


def _propositions(entries: Any) -> List[Dict[str, str]]:
    """Archetype publication entries → {title, core_impulse} pairs.

    THE ENUM IDENTIFIER IS DROPPED. A synthesis consumer must not need
    `KNOWLEDGE_TRANSMISSION` to understand the reading — the two human strings
    are the whole proposition.
    """
    out = []
    for e in entries or []:
        if isinstance(e, dict) and e.get("title") and e.get("core_impulse"):
            out.append({"title": e["title"], "core_impulse": e["core_impulse"]})
    return out


def _strength_synthesis(st: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """MODE-AWARE, and structured rather than a flat list.

    Flight 11 flattened Strength into `[core capacities..., constructive
    expressions..., dependable mechanisms...]` and the narrative layer then read
    index 0/1/2 as capacity/expression/mechanism. On a COMPOUND election that
    produced "Intuitive Receptivity is the capacity you can rely on... it stays
    dependable when Cognitive Discrimination" — three different grahas' CORE
    CAPACITIES presented as one graha's three fields.

    NO ARRAY INDEX MAY DETERMINE A SEMANTIC ROLE. Every field is named.
    """
    mode = st.get("mode")
    if mode == "FOUNDATIONAL_RESILIENCE":
        out = {k: st[k] for k in ("mature_quality", "constructive_expression",
                                  "higher_value") if st.get(k)}
        return {"mode": mode, **out} if out else None

    if mode == "SINGLE":
        out = {k: st[k] for k in ("core_capacity", "constructive_expression",
                                  "dependable_mechanism") if st.get(k)}
        return {"mode": mode, **out} if out else None

    if mode in ("DUAL", "COMPOUND"):
        # NEVER derived by splitting the title: capacity names contain " & ".
        caps = st.get("core_capacities")
        out: Dict[str, Any] = {"mode": mode}
        if st.get("title"):
            out["title"] = st["title"]
        # Carried so the narrative can ATTRIBUTE each expression and mechanism.
        # Without it the attribution degrades silently to bare clauses, which is
        # how one graha's text starts speaking for the set again.
        if st.get("grahas"):
            out["grahas"] = list(st["grahas"])
        if caps:
            out["core_capacities"] = list(caps)
        if st.get("constructive_expressions"):
            out["constructive_expressions"] = list(st["constructive_expressions"])
        if st.get("dependable_mechanisms"):
            out["dependable_mechanisms"] = list(st["dependable_mechanisms"])
        return out if len(out) > 1 else None
    return None


def _contribution_synthesis(dc: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Structured meaning and role. NEVER `str(dict)`.

    Flight 7 stringified the archetype dictionaries into prose atoms, so the
    substrate carried serialized implementation data and dropped the
    Founder-locked dissenting role entirely. Flight 9 would have had to parse a
    Python repr or reinvent the meaning/role relationship in the provider — both
    of which make the provider the astrologer.
    """
    mode = dc.get("mode")
    if mode == "MATURITY_FALLBACK":
        out = {k: dc[k] for k in ("mature_quality", "higher_value") if dc.get(k)}
        return {"mode": mode, **out} if out else None

    if mode == "UNIFIED_PURPOSE":
        primary = _propositions(dc.get("primary_mode"))
        if not primary:
            return None
        return {"mode": mode, "primary": primary,
                "conviction": dc.get("label") or doc.UNIFIED_PURPOSE_LABEL}

    if mode == "PAIRWISE":
        primary = _propositions(dc.get("primary_contribution_mode"))
        if not primary:
            return None
        out: Dict[str, Any] = {"mode": mode, "primary": primary}
        # Exactly one contextual vector, carrying its Founder-locked role name.
        # The role is derived from WHICH FIELD published, not from a topology
        # field, so the customer block needs no `dissenting_role` for the
        # substrate to stay complete.
        # PUBLIC LABELS. The engine ontology — "Ethical Functional Vector" and
        # the rest — belongs in the collapsed Astrological Basis, never in the
        # customer synthesis.
        for key in ("functional_vector", "ethical_functional_vector",
                    "aptitude_modifier"):
            vec = _propositions(dc.get(key))
            if vec:
                # THE ROLE KEY IS THE SEMANTICS; THE LABEL IS DISPLAY.
                # Flight 16 carried only the label, so the narrative had to
                # compose one generic sentence for all three roles — which both
                # inserted a heading as a noun phrase and described the Ethical
                # Functional Vector as "how it reaches the world".
                out["contextual_vector"] = {
                    "role_key": key,
                    "role": CONTRIBUTION_ROLE_LABELS[key],
                    "propositions": vec}
                break
        return out

    if mode == "COMPOUND_MULTI_POLAR":
        out = {"mode": mode}
        for src, dest in (("primary_impact_vector", "primary_impact"),
                          ("ethical_driver", "ethical_driver"),
                          ("innate_aptitude", "innate_aptitude")):
            vec = _propositions(dc.get(src))
            if vec:
                out[dest] = vec
        return out if len(out) > 1 else None
    return None


def build_synthesis_material(report: Dict[str, Any]) -> Dict[str, Any]:
    """Collect the already-selected propositions, by domain.

    EVERY string here is lifted from the model above it. Nothing is composed,
    bridged or explained — Flight 6 proves the substrate is sufficient, and the
    250-400 word rendering is Flight 7's problem.
    """
    material: Dict[str, List[str]] = {}
    ct = report.get("central_theme") or {}
    if ct:
        material["central_theme"] = [ct[f] for f in doc.CENTRAL_THEME_FIELDS if ct.get(f)]

    sigs = report.get("defining_signatures") or {}
    st = sigs.get("strength") or {}
    if st:
        strength = _strength_synthesis(st)
        if strength:
            material["strength"] = strength

    ge = sigs.get("growth_edge") or {}
    if ge.get("growth_edge"):
        material["growth_edge"] = [ge["growth_edge"]]

    dc = sigs.get("dharma_contribution")
    if dc:
        contribution = _contribution_synthesis(dc)
        if contribution:
            material["contribution"] = contribution

    # PARTNERSHIP AS A FIRST-CLASS SYNTHESIS STRAND (Flight 16 · Job 9).
    # Relational field, governing function and — when present — karmic
    # orientation all reach the Integrated Reading.
    pt = report.get("partnership") or {}
    if pt.get("relational_field"):
        material["partnership"] = {
            "field_sign": pt["relational_field"]["sign"],
            "field": pt["relational_field"]["statement"],
            "lord": pt["governing_function"]["graha"],
            "dignity": pt["governing_function"]["dignity"],
            "capacity": pt["governing_function"]["statement"],
            "orientation": [o["statement"] for o in
                            (pt.get("karmic_orientation") or [])],
            "orientation_grahas": [o["graha"] for o in
                                   (pt.get("karmic_orientation") or [])],
        }
    else:
        stmts = [s for sec in (pt.get("sections") or [])
                 for s in sec.get("statements", [])]
        if stmts:
            material["partnership"] = stmts

    ins = report.get("instructions") or {}
    if ins:
        vals = [ins["cultivate"]["mature_quality"],
                ins["cultivate"]["constructive_expression"],
                ins["watch"]["shadow_expression"],
                ins["practise"]["behaviour"]]
        material["instructions"] = vals

    return {"domains": material,
            "domain_count": len(material),
            "introduces_new_propositions": False}


# ═════════════════════════════════════════════════════════════════════════════
# GUARDS
# ═════════════════════════════════════════════════════════════════════════════

def published_strings(report: Dict[str, Any]) -> set:
    """Every string in the model EXCLUDING synthesis_material.

    Collected structurally by walking the tree, not by `repr()`. The Flight 7
    gate compared synthesis strings against `repr(report)` and so accepted a
    stringified dict — because the same serialization naturally appears inside
    the repr. The test agreed with the defect by construction.
    """
    found: set = set()

    def walk(v: Any) -> None:
        if isinstance(v, dict):
            for val in v.values():
                walk(val)
        elif isinstance(v, list):
            for val in v:
                walk(val)
        elif isinstance(v, str):
            found.add(v)

    walk({k: val for k, val in report.items() if k != "synthesis_material"})
    return found


def synthesis_strings(material: Dict[str, Any]) -> List[str]:
    """Every human proposition the synthesis substrate carries."""
    out: List[str] = []

    def walk(v: Any) -> None:
        if isinstance(v, dict):
            for k, val in v.items():
                # Structural labels and the internal role key are not
                # propositions — `role_key` names WHICH deterministic role
                # published, and never reaches a customer surface.
                if k in ("mode", "role", "role_key", "conviction"):
                    continue
                walk(val)
        elif isinstance(v, list):
            for val in v:
                walk(val)
        elif isinstance(v, str):
            out.append(v)

    walk(material.get("domains") or {})
    return out


STRINGIFIED_MARKERS = ("{'", '{"', "'archetype':", '"archetype":', "': '")


def scan_stringified_structures(material: Dict[str, Any]) -> List[str]:
    """Serialized implementation data masquerading as a proposition."""
    bad = []
    for s in synthesis_strings(material):
        if s.startswith("{") or any(m in s for m in STRINGIFIED_MARKERS):
            bad.append(s[:80])
    return bad


def scan_internal_identifiers(material: Dict[str, Any]) -> List[str]:
    """No consumer should need an enum name to read the synthesis."""
    ids = {a.value for a in doc.ARCHETYPES}
    return [s[:80] for s in synthesis_strings(material)
            if any(i in s for i in ids)]


# Server-owned copy that legitimately NAMES a banned concept in order to deny
# it — "not an event-timing report", "Timing belongs to Dashā analysis". The
# scan checks for a timing SECTION, not for the word.
_VOCAB_EXEMPT_PATHS = ("explainer", "scope_note", "contribution_note")


def scan_forbidden_vocabulary(report: Dict[str, Any]) -> List[str]:
    """Absence states and R1 concepts must not appear anywhere.

    The exemption is by KEY PATH, not by phrase: the three server-owned copy
    blocks may say "not an event-timing report" while nothing else may carry a
    timing concept at all.
    """
    scanned = {k: v for k, v in report.items() if k not in _VOCAB_EXEMPT_PATHS}
    blob = repr(scanned)
    return [t for t in FORBIDDEN_PUBLICATION_VOCABULARY if t in blob]


def scan_customer_internals(report: Dict[str, Any]) -> List[str]:
    """Enum identifiers and topology telemetry on a customer surface."""
    blob = repr(report)
    return ([t for t in ARCHETYPE_ENUM_IDS if t in blob]
            + [t for t in CONTRIBUTION_TOPOLOGY_FIELDS if f"'{t}'" in blob])


def scan_basis_telemetry(basis: Dict[str, Any]) -> List[str]:
    """Walk keys AND string values, at any depth.

    Flight 9's version checked `repr()`, which caught the flat case but this
    walks the structure — a banned key nested several levels inside Karakāṁśa
    evidence is the shape that actually reaches production.
    """
    found: List[str] = []

    def walk(node: Any, path: str) -> None:
        if isinstance(node, dict):
            for k, v in node.items():
                if str(k).lower() in BASIS_TELEMETRY_BANNED:
                    found.append(f"{path}.{k}")
                walk(v, f"{path}.{k}")
        elif isinstance(node, (list, tuple)):
            for i, v in enumerate(node):
                walk(v, f"{path}[{i}]")
        elif isinstance(node, str):
            low = node.lower()
            for t in BASIS_TELEMETRY_BANNED:
                if t in low:
                    found.append(f"{path}<{t}>")

    walk(basis, "$")
    return found
