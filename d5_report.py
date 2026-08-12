"""
d5_report.py — D5-008 · THE DETERMINISTIC REPORT VIEW MODEL.

A VIEW MODEL, NOT A PROSE ENGINE. Every value here is SELECTED from a certified
surface — the D5-001 facts, the accepted scoring output, the accepted timing and
triangulation outcomes. Nothing is reclassified, re-ranked, re-scored or
re-worded, and no sentence is generated.

THE CLASSIFICATIONS ARE COPIED, NEVER RECOMPUTED. `quick_snapshot` reads the
Core Authority, Purva Punya and Power Vector results that `build_score` already
decided. A second classification here — even one that agreed today — would be a
second doctrine, and the report would eventually drift from the number beside it.

TIES ARE PRESERVED. Where the scoring layer published two or three tied leaders
and a null primary, this passes both through unchanged. Choosing a
frontend-friendly winner would be inventing a tie-break the Founder did not
authorise.
"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping

import d5_archetypes as ARCH
import d5_client_reading as CR
from d5_rules import FIRED, NOT_FIRED, UNRESOLVED, RuleOutcome

REPORT_TITLE = "D-5 · Panchamsha | Fame, Authority & Purva Punya Report"
REPORT_SUBTITLE = "Power dynamics, past-life merits & intellectual legacy"

TIMING_RULE_ORDER = ("D5_TIM_01", "D5_TIM_02", "D5_TIM_03")
TRIANGULATION_RULE_ORDER = ("D5_TRI_01", "D5_TRI_02", "D5_TRI_03")


def _quick_snapshot(score: Mapping[str, Any]) -> Dict[str, Any]:
    """COPIED from certified scoring. Nothing is reclassified.

    A tied Core Authority or Power Vector arrives with `primary: None` and every
    leader listed, and it leaves the same way.
    """
    authority = score["core_authority"]
    punya = score["purva_punya"]
    vector = score["primary_power_vector"]
    return {
        "final_score": score["final_score"],
        "score_band": dict(score["score_band"]),
        "core_authority": {
            "primary": authority["primary"],
            "leaders": list(authority["leaders"]),
            "tied": authority["tied"],
            "override": authority["override"],
        },
        "purva_punya_classification": punya["classification"],
        "purva_punya_no_signal": punya["no_signal"],
        "primary_power_vector": {
            "primary": vector["primary"],
            "leaders": list(vector["leaders"]),
            "tied": vector["tied"],
        },
    }


def _foundational(facts: Mapping[str, Any]) -> Dict[str, Any]:
    """SELECTED from the accepted D5-001 facts. No placement arithmetic."""
    lagna = facts["lagna"]
    karakas = facts["chara_karakas"]["assignments"]
    return {
        "d5_lagna": {"sign": lagna["d5_sign"],
                     "sign_index": lagna["d5_sign_index"],
                     "source_sign": lagna["source_sign"],
                     "segment_number": lagna["segment_number"],
                     "tattva": lagna["tattva"]},
        "d5_lagna_lord": dict(facts["lagna_lord"]),
        "chara_karakas": {name: {"planet": entry["planet"],
                                 "rank": entry["rank"]}
                          for name, entry in sorted(karakas.items())},
        "d1_fifth_lord_mirroring": dict(facts["d1_fifth_lord_mirroring"]),
        "karakamsha": dict(facts["karakamsha"]),
    }


def _scored_findings(score: Mapping[str, Any]) -> List[Dict[str, Any]]:
    """Every FIRED additive rule, sorted by rule_id.

    NO SEMANTIC RANKING AND NO "TOP THREE". Ordering is by rule ID because that
    is deterministic and carries no interpretation; deciding which finding
    matters most is a Founder question that has not been asked.

    NOT_FIRED rules stay in the scoring audit table and are not duplicated here.
    """
    findings = []
    for rule_id in sorted(score["rules"]):
        entry = score["rules"][rule_id]
        if entry["status"] != FIRED:
            continue
        findings.append({
            "rule_id": rule_id,
            "polarity": entry["polarity"],
            "base_weight": entry["base_weight"],
            "effective_weight": entry["effective_weight"],
            "participants": list(entry["participants"]),
            "power_vector_hits": list(entry["power_vector_hits"]),
        })
    return findings


def _timing(score: Mapping[str, Any],
            timing_outcomes: Mapping[str, RuleOutcome]) -> List[Dict[str, Any]]:
    """Context only. TIM_03 is a transit condition, not a prediction.

    Nothing here converts a fired timing rule into a guaranteed event, an
    imminent event or a date — the block reports the status, the weights and the
    rule's own evidence, and stops.
    """
    out = []
    for rule_id in TIMING_RULE_ORDER:
        outcome = timing_outcomes[rule_id]
        entry = score["rules"][rule_id]
        out.append({
            "rule_id": rule_id,
            "status": outcome.status,
            "base_weight": entry["base_weight"],
            "effective_weight": entry["effective_weight"],
            "evidence": outcome.evidence,
        })
    return out


def _triangulation(score: Mapping[str, Any],
                   triangulation_outcomes: Mapping[str, RuleOutcome]
                   ) -> Dict[str, Any]:
    """The TRI statuses and the per-planet bindings, SELECTED not re-evaluated.

    TRI base weights are NOT added to anything here — they are filters, and the
    scoring layer already excluded them from the additive universe.
    """
    bindings = score["triangulation_bindings"]
    return {
        "rules": [{"rule_id": rule_id,
                   "status": triangulation_outcomes[rule_id].status,
                   "base_weight": triangulation_outcomes[rule_id].base_weight,
                   "additive": False}
                  for rule_id in TRIANGULATION_RULE_ORDER],
        "applicable_planets": list(bindings["applicable_planets"]),
        "bindings": {planet: {"tri_01": entry["tri_01"],
                              "tri_02": entry["tri_02"],
                              "tri_03": entry["tri_03"],
                              "applied_multipliers": dict(
                                  entry.get("applied_multipliers", {})),
                              "multiplier": entry["multiplier"],
                              "multiplier_exact": entry["multiplier_exact"]}
                     for planet, entry in sorted(bindings["bindings"].items())},
        "inexact_bindings": list(bindings["inexact_bindings"]),
    }


def _publication_state(entry: Mapping[str, Any]) -> str:
    """active · neutral · suppressed, by the REASON the weight is what it is."""
    if entry["effective_weight"] != 0:
        return "active"
    if entry["base_weight"] == 0:
        # Neutral by doctrine. Nothing is restricting it.
        return "neutral"
    return "suppressed"


def _handle(title: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in title.lower()).strip("_")


def _signatures(rules: Mapping[str, Any]) -> List[Dict[str, Any]]:
    """Every FIRED rule's MEANING, in its Founder chapter.

    §18 · all fired rules remain visible in MEANING — not as printed ids. Each
    carries a human title and interpretation from the certified matrix, and no
    rule_id reaches this public model.

    D5-009-CORR-05 §1 · THREE STATES, DISTINGUISHED BY REASON not by result.
    A zero Effective Weight has two entirely different causes and the earlier
    code conflated them:

        base 0, nothing suppressing   -> NEUTRAL   (present, carries no weight)
        base non-zero, zeroed by TRI   -> SUPPRESSED (real, held in check)
        effective non-zero             -> ACTIVE

    Five Founder rules carry Base Weight 0 by design — PAR_14, AFF_06, CLA_04,
    JAI_16, JAI_17. Calling them "held in check" told the customer a
    restriction existed where the doctrine simply assigns no weight.
    """
    out: List[Dict[str, Any]] = []
    for rule_id in sorted(rules):
        entry = rules[rule_id]
        if entry["status"] != FIRED:
            continue
        pub = CR.RULE_PUBLICATION[rule_id]       # KeyError is a build failure
        out.append({
            # A stable handle derived from the TITLE, never the rule id: §20
            # forbids a rule_id in this public model, and `rule_id.lower()` is
            # still the rule id.
            "key": _handle(pub["title"]),
            "chapter": pub["chapter"],
            "title": pub["title"],
            "body": pub["body"],
            "state": _publication_state(entry),
            "planets": list(entry["participants"]),
        })
    return out


def _chapter(signatures, chapter, heading, authority=None, archetypes=None):
    """§2 · narrative first, supporting signatures underneath."""
    return CR.compose_chapter(chapter, heading, signatures, authority,
                              archetypes)


def _client_reading(facts: Mapping[str, Any], score: Mapping[str, Any],
                    timing_outcomes: Mapping[str, RuleOutcome],
                    triangulation_outcomes: Mapping[str, RuleOutcome],
                    static_outcomes: Mapping[str, RuleOutcome] = None
                    ) -> Dict[str, Any]:
    """The Founder report, in the Founder's order.

    Quick Snapshot -> Foundational Metrics -> Core Life Archetypes ->
    Temporal Activation Keys -> Karmic Friction & Potential Ceilings ->
    Detailed Analysis (I, II, III).
    """
    rules = score["rules"]
    # The certified per-rule EVIDENCE, read-only. Needed because the scoring
    # entry records participants and weights but not the branch that fired.
    static_evidence = {rid: o.evidence
                       for rid, o in (static_outcomes or {}).items()}
    tri_02 = triangulation_outcomes.get("D5_TRI_02")
    tri_02_fired = tri_02 is not None and tri_02.status == FIRED
    tri_01 = triangulation_outcomes.get("D5_TRI_01")
    tri_01_fired = tri_01 is not None and tri_01.status == FIRED
    # §3 · the third certified outcome, READ not re-evaluated.
    tri_03 = triangulation_outcomes.get("D5_TRI_03")
    tri_03_fired = tri_03 is not None and tri_03.status == FIRED

    authority = score["core_authority"]
    vector = CR.power_vector_language(score["primary_power_vector"])
    signatures = _signatures(rules)
    archetypes = {name: {k: v for k, v in state.items()
                         if not k.startswith("_")}
                  for name, state in
                  ARCH.all_archetypes(rules, tri_02_fired).items()}
    lagna = facts["lagna"]
    karakas = facts["chara_karakas"]["assignments"]
    mirror = facts["d1_fifth_lord_mirroring"]
    kshamsha = facts["karakamsha"]
    ak = karakas.get("AK", {}).get("planet", "")

    return {
        # ── Quick Snapshot · exactly the three template items. Final Score and
        #    Score Band are engine summaries and stay backend-side.
        "quick_snapshot": {
            "core_authority_tier": authority["primary"]
                                   or " / ".join(authority["leaders"]),
            "purva_punya_index": score["purva_punya"]["classification"],
            "primary_power_vector": vector["title"],
        },
        # ── the five Foundational Metrics, named by the template ──
        "foundational_metrics": [
            {"title": "D-5 Lagna & Lord Placement",
             "body": f"{lagna['d5_sign']} Panchamsha rises, ruled by "
                     f"{facts['lagna_lord']['planet']}. The rising arc falls in "
                     f"segment {lagna['segment_number']} of its source sign, "
                     f"{lagna['source_sign']}, under the {lagna['tattva']} "
                     f"elemental current."},
            # §5 · resonance is SELECTED from evaluated outcomes. The report
            # computes no aspect, no house arithmetic and no geometry.
            {"title": "Atmakaraka (AK) Strength in D-5",
             "body": CR.atmakaraka_strength(
                 ak, facts["grahas"][ak]["d5_sign"],
                 facts["grahas"][ak]["d5_house"],
                 [CR.RULE_PUBLICATION[r]["title"]
                  for r in CR.AK_RESONANCE_RULES
                  if r in rules and rules[r]["status"] == FIRED
                  # The BRANCH must prove the H1/H5 relation, not merely that
                  # the rule fired somewhere involving the Atmakaraka.
                  and CR.AK_RESONANCE_EVIDENCE[r](
                      static_evidence.get(r, {}))])["body"]},
            {"title": "D-1 5th Lord Mirroring",
             "body": f"The natal fifth lord, {mirror['planet']}, mirrors into "
                     f"{mirror['d5_sign']} in the Panchamsha, house "
                     f"{mirror['d5_house']}. This is where creative and "
                     f"intellectual promise from the birth chart actually lands "
                     f"in the division of fame."},
            {"title": "Pancha-Tattva Dominance",
             "body": _tattva_summary(facts)},
            {"title": "Karakamsha (D-9 AK) Alignment",
             "body": f"The Karakamsha, drawn from {kshamsha['atmakaraka']} in "
                     f"{kshamsha['d9_ak_sign']} of the Navamsha, aligns to "
                     f"{kshamsha['d5_karakamsha_sign']} in house "
                     f"{kshamsha['d5_karakamsha_house']} here — the seat of the "
                     f"soul's declared direction within this division."},
        ],
        # The selector's eligibility record names rule ids, so it is STRIPPED
        # here. It remains reachable to QA through the archetype module itself;
        # it must not ride into the published surface.
        "archetypes": archetypes,
        # ── Temporal Activation Keys ──
        "temporal_activation": CR.temporal_activation(timing_outcomes),
        # ── Karmic Friction & Potential Ceilings ──
        "karmic_friction": CR.karmic_friction(signatures),
        # ── Detailed Analysis, three Founder chapters ──
        "detailed_analysis": {
            "foundation_public_footprint": _chapter(
                signatures, "foundation_public_footprint",
                "I. Foundation & Public Footprint", authority),
            "intellectual_legacy": _chapter(
                signatures, "intellectual_legacy",
                "II. Intellectual Legacy & Creative Output", authority,
                archetypes),
            "karmic_triangulation": CR.karmic_triangulation(
                tri_01_fired, tri_02_fired, tri_03_fired, authority),
        },
        "detailed_signatures": signatures,
    }


def _tattva_summary(facts: Mapping[str, Any]) -> str:
    """A count over ALREADY CERTIFIED Tattva facts. No second placement."""
    import collections
    ak = facts["chara_karakas"]["assignments"].get("AK", {}).get("planet", "")
    key_planets = [facts["lagna_lord"]["planet"],
                   facts["d1_fifth_lord_mirroring"]["planet"],
                   "Sun", "Jupiter", ak]
    tattvas = [facts["grahas"][p]["tattva"] for p in key_planets
               if p in facts["grahas"]]
    if not tattvas:
        return "The elemental distribution across the key planets is even."
    top, count = collections.Counter(tattvas).most_common(1)[0]
    return (f"Among the five key significators of this division, {count} fall "
            f"in the {top} elemental arc, which sets the working temperament "
            f"of how recognition is pursued and held.")


def build_report_payload(facts: Mapping[str, Any], score: Mapping[str, Any],
                         timing_outcomes: Mapping[str, RuleOutcome],
                         triangulation_outcomes: Mapping[str, RuleOutcome],
                         static_outcomes: Mapping[str, RuleOutcome] = None
                         ) -> Dict[str, Any]:
    """The complete deterministic report payload.

    NO ROMANCE OR PROGENY SECTION. Their rule membership has not been
    mechanically established by any Founder lock, and inventing a grouping to
    fill a frontend card — then attaching a "No Dominant Signature" fallback to
    it — would be manufacturing a taxonomy. Deferred deliberately.

    NO HEADLINE. The locked precedence turns on signed weight versus magnitude,
    which is unresolved; the scored findings give the frontend everything a
    later headline stage needs.
    """
    authority = score["core_authority"]
    punya = score["purva_punya"]
    vector = score["primary_power_vector"]
    return {
        "title": REPORT_TITLE,
        "subtitle": REPORT_SUBTITLE,
        "quick_snapshot": _quick_snapshot(score),
        # THE CLIENT SURFACE. Everything below it stays available for QA and
        # audit; only this block is meant for a customer's eyes.
        "client_reading": _client_reading(facts, score, timing_outcomes,
                                          triangulation_outcomes,
                                          static_outcomes),
        "foundational": _foundational(facts),
        "authority": {
            "bucket_scores": dict(authority["bucket_scores"]),
            "primary": authority["primary"],
            "leaders": list(authority["leaders"]),
            "tied": authority["tied"],
            "override": authority["override"],
        },
        "purva_punya": {
            "score": punya["score"],
            "classification": punya["classification"],
            "no_signal": punya["no_signal"],
            "override": punya["override"],
            "member_rule_ids": list(punya["member_rule_ids"]),
            "fired_rule_ids": list(punya["fired_rule_ids"]),
        },
        "power_vector": {
            "vectors": {name: dict(entry)
                        for name, entry in sorted(vector["vectors"].items())},
            "primary": vector["primary"],
            "leaders": list(vector["leaders"]),
            "tied": vector["tied"],
        },
        "timing": _timing(score, timing_outcomes),
        "triangulation": _triangulation(score, triangulation_outcomes),
        "scored_findings": _scored_findings(score),
    }
