"""D9-R2 · d9_r2_selectors · THE SINGLE DETERMINISTIC SELECTION AUTHORITY.

Certified facts in, structured selections out. No prose, no HTTP, no FastAPI, no
provider, no live D9 module. Every value returned comes from a ratified doctrine
table through `consume()`, so an unratified table cannot reach a caller here.

WHAT THIS MODULE MAY NOT DO, and each is a rule someone paid for:
  · no `certified_rank` — it orders Moolatrikona above Own Sign, a distinction
    publication deliberately collapses;
  · no kendra/koṇa, dispositor or lordship ranking of any kind;
  · no fifth Central Theme proposition — no tension, reason, causal bridge or
    karmic explanation;
  · no layer substitution: the D1 bottleneck, the strength calibration shadow and
    the Growth Edge are three different things about three different subjects.
"""

from typing import Any, Dict, List, Optional, Sequence, Tuple

import d9_r2_doctrine as doc
from d9_r2_doctrine import Election, consume


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 1 · CENTRAL THEME
# ═════════════════════════════════════════════════════════════════════════════

def select_central_theme(d1_lagna_sign: str, d9_lagna_sign: str) -> Dict[str, str]:
    """Four fields, each a straight read from its own corpus.

    THE FOUR PROPOSITIONS ARE THE SPINE. Nothing is derived, related or
    explained between them — the narrative layer may connect them
    grammatically and may not infer why one follows from another.
    """
    d1 = consume("D1_OUTER_TENDENCY", doc.D1_OUTER_TENDENCY)
    d9 = consume("D9_MATURITY", doc.D9_MATURITY)
    if d1_lagna_sign not in d1 or d9_lagna_sign not in d9:
        raise KeyError(f"unknown sign: {d1_lagna_sign!r} / {d9_lagna_sign!r}")
    return {
        "instinctive_playbook":   d1[d1_lagna_sign]["outer_orientation"],
        "emerging_bottleneck":    d1[d1_lagna_sign]["default_overextension"],
        "mature_demanded_mode":   d9[d9_lagna_sign]["mature_quality"],
        "horizon_of_integration": d9[d9_lagna_sign]["higher_value"],
    }


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 2.1 · STRENGTH
# ═════════════════════════════════════════════════════════════════════════════

def _by_published_band(published_dignity: Dict[str, str]) -> Dict[str, List[str]]:
    """Bucket eligible grahas by PUBLISHED band. Nodes never enter."""
    out: Dict[str, List[str]] = {b: [] for b in doc.STRENGTH_BANDS}
    for graha, band in published_dignity.items():
        if graha in doc.NODES or graha not in doc.STRENGTH_ELIGIBLE_GRAHAS:
            continue
        if band in out:
            out[band].append(graha)
    return out


def select_strength(published_dignity: Dict[str, str],
                    d1_sign_of: Optional[Dict[str, str]] = None,
                    d9_sign_of: Optional[Dict[str, str]] = None,
                    d9_lagna_sign: Optional[str] = None) -> Dict[str, Any]:
    """Elect from the highest OCCUPIED qualifying tier, then by cardinality.

    `published_dignity` must already be the PUBLISHED label — Moolatrikona
    collapsed into Own Sign by the publication wall. This function never sees the
    certified band and so cannot restore a distinction publication removed.

    `misuse_shadow` travels but is flagged `primary_card False /
    calibration_only True`. It is calibration for the strength, not the Growth
    Edge, and §2.2 must not read it.
    """
    caps = consume("MATURE_CAPACITY", doc.MATURE_CAPACITY)
    shape, band, grahas = doc.elect_strength_shape(_by_published_band(published_dignity))

    if shape is Election.FOUNDATIONAL_RESILIENCE:
        return _foundational_resilience(d9_lagna_sign)

    tags = doc.vargottama_tags(grahas, d1_sign_of or {}, d9_sign_of or {})

    def entry(g: str) -> Dict[str, Any]:
        c = caps[g]
        return {
            "graha": g,
            "core_capacity": c["core_capacity"],
            "constructive_expression": c["constructive_expression"],
            "dependable_mechanism": c["dependable_mechanism"],
            "misuse_shadow": c["misuse_shadow"],
            "vargottama_modifier": (
                {"tag": doc.VARGOTTAMA_TAG,
                 "description": doc.VARGOTTAMA_DESCRIPTION} if g in tags else None),
        }

    entries = [entry(g) for g in grahas]     # already canonically serialized

    # `misuse_shadow` is structurally present and flagged so a renderer cannot
    # put it on the primary card by accident.
    calibration = {"primary_card": False, "calibration_only": True,
                   "shadows": [e["misuse_shadow"] for e in entries]}

    if shape is Election.SINGLE:
        e = entries[0]
        return {"mode": "SINGLE", "published_dignity": band, "grahas": grahas,
                "graha": e["graha"], "core_capacity": e["core_capacity"],
                "constructive_expression": e["constructive_expression"],
                "dependable_mechanism": e["dependable_mechanism"],
                "misuse_shadow": e["misuse_shadow"],
                "vargottama_modifier": e["vargottama_modifier"],
                "calibration": calibration}

    payload = {
        "mode": shape.value, "published_dignity": band, "grahas": grahas,
        "constructive_expressions": [e["constructive_expression"] for e in entries],
        "dependable_mechanisms": [e["dependable_mechanism"] for e in entries],
        "calibration_shadows": [e["misuse_shadow"] for e in entries],
        "vargottama_modifiers": {e["graha"]: e["vargottama_modifier"]
                                 for e in entries if e["vargottama_modifier"]},
        "co_equal": True,
        "calibration": calibration,
    }
    if shape is Election.DUAL:
        payload["title"] = " & ".join(e["core_capacity"] for e in entries)
        # Emitted for DUAL as well as COMPOUND. Core capacity names themselves
        # contain " & " — "Ethical Perspective & Sound Counsel" — so a consumer
        # that splits the title to recover them shatters the names.
        payload["core_capacities"] = [e["core_capacity"] for e in entries]
    else:
        payload["title"] = doc.COMPOUND_TITLE
        payload["core_capacities"] = [e["core_capacity"] for e in entries]
    return payload


def _foundational_resilience(d9_lagna_sign: Optional[str]) -> Dict[str, Any]:
    """No qualifying graha. NEVER promote a Neutral, Enemy or Debilitated one.

    The D9 Lagna maturity corpus is the fallback source. A weak Lagna lord may
    appear later as a fact in the Astrological Basis; it is not relabelled a
    strength here.
    """
    out: Dict[str, Any] = {"mode": "FOUNDATIONAL_RESILIENCE",
                           "title": "Foundational Resilience",
                           "grahas": [], "published_dignity": None}
    if d9_lagna_sign:
        m = consume("D9_MATURITY", doc.D9_MATURITY)[d9_lagna_sign]
        out.update({"mature_quality": m["mature_quality"],
                    "constructive_expression": m["constructive_expression"],
                    "higher_value": m["higher_value"],
                    "shadow_expression": m["shadow_expression"],
                    "basis": "d9_lagna_maturity"})
    return out


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 2.2 · GROWTH EDGE · no selector
# ═════════════════════════════════════════════════════════════════════════════

def select_growth_edge(d9_lagna_sign: str) -> Dict[str, str]:
    """A direct binding, not an election.

    The Founder ruling removed the choice I returned in Flight 5 rather than
    answering it. **The D1 bottleneck is not read here, and neither is the
    elected graha's misuse shadow** — those belong to Section 1 and Section 2.1
    and a test asserts no crossover.
    """
    m = consume("D9_MATURITY", doc.D9_MATURITY)[d9_lagna_sign]
    return {"growth_edge": m["shadow_expression"],
            "mature_counterpart": m["mature_quality"],
            "source": "D9_MATURITY.shadow_expression"}


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 4 · THREE INSTRUCTIONS
# ═════════════════════════════════════════════════════════════════════════════

def select_instructions(d9_lagna_sign: str) -> Dict[str, Any]:
    """Mappings from already-selected findings. No extra astrology, no remedy,
    no timing, no raw planet advice."""
    m = consume("D9_MATURITY", doc.D9_MATURITY)[d9_lagna_sign]
    practise = consume("PRACTISE_BEHAVIOUR", doc.PRACTISE_BEHAVIOUR)
    return {
        "cultivate": {"mature_quality": m["mature_quality"],
                      "constructive_expression": m["constructive_expression"]},
        "watch": {"shadow_expression": m["shadow_expression"]},
        "practise": {"behaviour": practise[d9_lagna_sign]},
    }


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 3 · PARTNERSHIP · deliberately narrow
# ═════════════════════════════════════════════════════════════════════════════

def select_partnership(h7_fired: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """CONFIRMED native-side evidence only.

    ONLY AN EXPLICIT `confidence == "direct"` PUBLISHES. Every
    `requires_confirmation` caution is excluded, and so is anything whose
    confidence is missing, `None`, malformed or unknown — confirmation is never
    inferred from absence. Publishing a provisional finding as settled would
    silently upgrade its authority, and under the absence rule it cannot be
    captioned as provisional either.

    On the accepted table that leaves `KL_H7_JUP` and `KL_H7_BEN`, both `direct`
    and both native-side. **What Draws You In, Your Relationship Challenge and
    Practical Relationship Guidance are not manufactured** because their headings
    once existed: absence changes the report shape.
    """
    # Flight 9 · FAIL CLOSED. The Flight 8 default of "direct" meant a record
    # with NO confidence field published as confirmed — confirmation inferred
    # from absence, which is the opposite of the rule. Missing, None, malformed
    # and unknown are all excluded now; only an explicit "direct" publishes.
    confirmed = [r for r in h7_fired
                 if r.get("confidence") == "direct" and r.get("plain")]
    if not confirmed:
        return {"sections": []}
    return {"sections": [{
        "heading": "What Supports You in Partnership",
        "statements": [r["plain"] for r in confirmed],
        # EXACT frame, never the Contribution-domain wildcard. Generic house
        # language is what caused the earlier ambiguity this lock exists for.
        "frame": "KARAKAMSHA_H7_D1_FRAME",
        "basis": "confirmed_native_side_h7",
    }]}


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 2.3 · CONTRIBUTION · the selection/publication bridge
# ═════════════════════════════════════════════════════════════════════════════

def select_contribution(convergence: Dict[str, Any],
                        d9_lagna_sign: str) -> Dict[str, Any]:
    """Attach the human meanings; build the real fallback when nothing converges.

    ONE PUBLICATION PATH PER PROPOSITION. Flight 7 emitted the dissenting vector
    twice — once under its doctrinal name and once as `dissenting_signal` — which
    is the duplicate-path defect we had just removed from the Strength shadow.
    `dissenting_signal` and the raw `roles` map are selector provenance and are
    kept under `_provenance`, out of the customer projection.

    THE SWĀṀŚA SUPPLEMENT IS GONE. Flight 7 set `basis` to
    `d9_lagna_maturity+swamsa` when a `swamsa_sign` was merely a valid key in
    `D9_MATURITY` — but that table is the D9 LAGNA maturity corpus, and a sign
    being a key in it authorises nothing about the Swāṁśa. R2-001 established
    that `KARAK_SIGN_DATA` is the Swāṁśa authority and that the two must not be
    conflated; Flight 7 conflated them and then labelled the result. Swāṁśa
    remains eligible for the Astrological Basis as a certified fact.
    """
    kind = convergence.get("convergence")
    name = getattr(kind, "value", kind)
    out: Dict[str, Any] = {"convergence": name}

    if name == "SUPPRESSED":
        m = consume("D9_MATURITY", doc.D9_MATURITY)[d9_lagna_sign]
        out["fallback_material"] = {
            "mature_quality": m["mature_quality"],
            "higher_value": m["higher_value"],
            "basis": "d9_lagna_maturity",
        }
        return out

    # Exactly one dissenting field publishes, named for the domain that dissents.
    published = ("primary_mode", "primary_contribution_mode",
                 "primary_impact_vector", "ethical_driver", "innate_aptitude",
                 "functional_vector", "ethical_functional_vector",
                 "aptitude_modifier")
    for key in published:
        if convergence.get(key):
            out[key] = doc.publish_archetypes(convergence[key])
    for key in ("agreeing_domains", "dissenting_domain", "dissenting_role",
                "label", "integrated", "precedence_applied",
                "aptitude_modifier_domain", "supporting_domains"):
        if key in convergence:
            out[key] = convergence[key]

    # Provenance only. `roles` restates the three named Compound fields and
    # `dissenting_signal` restates whichever vector already published.
    prov = {k: convergence[k] for k in ("roles", "dissenting_signal",
                                        "competing_pairs")
            if convergence.get(k)}
    if prov:
        out["_provenance"] = prov
    return out
