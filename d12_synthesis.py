"""d12_synthesis.py — bounded §11 and §13 prose composition.

D12-006A. The provider composes prose around certified atoms and does nothing
else. The interface is INJECTABLE so every certification test runs offline with
no network and no key: `compose()` takes a provider callable, and the production
transport is supplied at wiring.

WHAT THE PROVIDER NEVER SEES: the person's name, place, any Maraka array, any
raw chart_brief, medical or remedy flags, legacy moksha_insights, or anything
computed in a browser. `build_atoms` constructs its payload field by field from
certified server values, so a new field cannot leak in by being present on an
upstream object.

WHAT THE PROVIDER NEVER DECIDES: the tension winner, any classification, any
dignity, any house, the release result, or the practice sentence. Its output is
read only for the two prose fields, and the practice is inserted by the server.
"""

from __future__ import annotations

import json
from typing import Any, Callable, Dict, List, Mapping, Optional

from d12_crosschart_contract import Tri
from d12_instruction_corpus import TENSION_TITLE, instruction_text
from d12_synthesis_contract import (
    BEATS, SECTION_11_MAX_WORDS, SECTION_13_MAX_WORDS, SECTION_13_MIN_WORDS,
    Beat, Section11Draft, Section13Draft, SynthesisRejected, SynthesisResult,
    check_grounding, scan_claims,
)

__all__ = ["SynthesisUnavailable", "SynthesisRejected", "Provider",
           "build_atoms", "compose"]

# A provider takes (task, atoms) and returns a parsed JSON object.
Provider = Callable[[str, Mapping[str, Any]], Mapping[str, Any]]


class SynthesisUnavailable(RuntimeError):
    """The provider could not be reached or is not configured.

    Distinct from SynthesisRejected on purpose: one is a service condition and
    the other is a content verdict, and the route maps them to different
    failures. Neither ever falls back to the legacy three-section essay.
    """


def build_atoms(facts, findings, crosschart, topology, tension,
                section10_rows) -> Dict[str, Any]:
    """The certified atoms the provider may see. Field by field, deliberately.

    No name, no place, no birth data, no snapshot object, no chart_brief. If a
    field is not listed here the provider cannot receive it.
    """
    if tension.winner is None:
        raise SynthesisRejected(
            "there is no selected tension to compose around")
    lagna = facts["d12_lagna"]
    lp = facts["placements"][lagna["lagnesh"]]
    sun = facts["placements"]["Sun"]
    moon = facts["placements"]["Moon"]
    ketu = facts["placements"]["Ketu"]
    s7 = findings.section7
    # CORR-02 · the certified per-subject facts the grounding firewall checks
    # provider prose against. Server-owned values only; no identity, no degree.
    chart = {"d12_lagna_sign": lagna["d12_sign"],
             "lagnesh": lagna["lagnesh"],
             "grahas": {g: {"house": p["house"], "sign": p["d12_sign"],
                            "dignity": p["dignity_state"]}
                        for g, p in facts["placements"].items()}}

    # CORR-03 · THE ROLE REGISTRY. Publication metadata, not new astrology:
    # every identity here is READ from an already-certified source — the §10
    # rows for the D1 lords, the accepted §7 finding for the H6 lord, the D12
    # facts for the Lagnesh. No lordship is recomputed.
    def _facts_of(graha):
        p = facts["placements"][graha]
        return {"graha": graha, "house": p["house"], "sign": p["d12_sign"],
                "dignity": p["dignity_state"]}

    roles = {"D12 Lagna": {"sign": lagna["d12_sign"]},
             "Lagnesh": _facts_of(lagna["lagnesh"]),
             "H6 lord": {"graha": s7.h6_lord, "house": s7.h6_lord_house}}
    for row in section10_rows:
        entry = _facts_of(row.lord)
        entry["classification"] = row.classification
        roles[f"D1 {row.d1_lord_of}th lord"] = entry
    return {
        "chart": chart,
        "roles": roles,
        "stance": {"d12_lagna_sign": lagna["d12_sign"],
                   "lagnesh": lagna["lagnesh"],
                   "lagnesh_house": lp["house"],
                   "lagnesh_sign": lp["d12_sign"],
                   "lagnesh_dignity": lp["dignity_state"]},
        "father": {"karaka_house": sun["house"], "karaka_sign": sun["d12_sign"],
                   "karaka_dignity": sun["dignity_state"],
                   "sentence": findings.section6.father[0].finding.text},
        "mother": {"karaka_house": moon["house"], "karaka_sign": moon["d12_sign"],
                   "karaka_dignity": moon["dignity_state"],
                   "sentence": findings.section6.mother[0].finding.text},
        "unpaid": {"h6_occupants": list(s7.h6_occupants), "h6_lord": s7.h6_lord,
                   "h6_lord_house": s7.h6_lord_house,
                   "sentence": s7.finding.text},
        "handshake": [{"d1_lord_of": r.d1_lord_of, "lord": r.lord,
                       "in_d12": r.in_d12,
                       "classification": r.classification}
                      for r in section10_rows],
        "ketu_pull": {"house": ketu["house"], "sign": ketu["d12_sign"],
                      "dominance": topology.dominance.value,
                      "basis": topology.basis,
                      "boundary": "a D12 pull only; it may not cancel D10, "
                                  "work or standing"},
        "tension": {"key": tension.winner, "title": TENSION_TITLE[tension.winner]},
        "practice": instruction_text(tension.winner, "practise"),
        "constraints": {
            "section11_max_words": SECTION_11_MAX_WORDS,
            "section13_word_range": [SECTION_13_MIN_WORDS, SECTION_13_MAX_WORDS],
            "beat_order": list(BEATS),
            "forbidden": ["parent biography", "illness or death claims",
                          "Maraka", "rites, Shraddha or mantra", "remedies",
                          "past-life identity", "a second tension",
                          "cancelling D10 or work", "soul eulogy",
                          "restating the Devatā table"],
        },
    }


def compose(provider: Provider, atoms: Mapping[str, Any],
            tension_key: str) -> SynthesisResult:
    """Compose §11 and §13, validate, and assemble server-side.

    Every failure path is explicit. Nothing partial reaches a caller and the
    legacy essay is never substituted.
    """
    try:
        s11_raw = provider("section11", atoms)
        s13_raw = provider("section13", atoms)
    except SynthesisRejected:
        raise
    except Exception as exc:                       # transport, config, parse
        raise SynthesisUnavailable(f"prose composition unavailable: {exc}") from exc

    try:
        s11 = Section11Draft(**dict(s11_raw))
        s13 = Section13Draft(**dict(s13_raw))
    except SynthesisRejected:
        raise
    except Exception as exc:
        raise SynthesisRejected(f"provider output failed the contract: {exc}") from exc

    # The provider does not get to choose which tension it wrote about.
    if s11.tension_key != tension_key:
        raise SynthesisRejected(
            f"provider composed for {s11.tension_key!r} but the deterministic "
            f"winner is {tension_key!r}")

    # CORR-01 · the grounding rule, on §11 and on every §13 beat. A claim scan
    # cannot catch prose that states a certified fact incorrectly; this can.
    grounded = check_grounding(s11.body, atoms)
    for beat in s13.beats:
        grounded += check_grounding(beat.text, atoms)
    if grounded:
        raise SynthesisRejected(
            f"provider prose contradicts the certified atoms: "
            f"{'; '.join(sorted(set(grounded)))}")

    practice = instruction_text(tension_key, "practise")

    # THE PRACTICE IS INSERTED BY THE SERVER. The provider's own practice beat
    # is checked for banned claims like every other beat, then replaced — a
    # paraphrase is a rejection, not something to tidy up.
    if practice not in s13.beats[-1].text:
        raise SynthesisRejected(
            "the §13 practice beat does not carry the exact winning FR-003 "
            "Practise sentence")
    beats = list(s13.beats[:-1]) + [Beat(name="practice", text=practice)]
    essay = " ".join(b.text.strip() for b in beats)

    found = scan_claims(essay)
    if found:
        raise SynthesisRejected(f"§13 essay introduces {', '.join(found)}")
    grounded = check_grounding(essay, atoms)
    if grounded:
        raise SynthesisRejected(
            f"the joined §13 essay contradicts the certified atoms: "
            f"{'; '.join(grounded)}")

    try:
        return SynthesisResult(
            tension_key=tension_key,
            section11_body=s11.body, section11_words=len(s11.body.split()),
            section13_essay=essay, section13_words=len(essay.split()),
            beat_order=list(BEATS), practice_sentence=practice)
    except Exception as exc:
        raise SynthesisRejected(f"assembled prose failed the contract: {exc}") from exc
