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


def build_report_payload(facts: Mapping[str, Any], score: Mapping[str, Any],
                         timing_outcomes: Mapping[str, RuleOutcome],
                         triangulation_outcomes: Mapping[str, RuleOutcome]
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
