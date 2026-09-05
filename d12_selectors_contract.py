"""d12_selectors_contract.py — typed §11 tension and §12 Three Instructions.

D12-005. Every instruction string is exact-key bound at the contract boundary,
in the discipline CORR-01 and CORR-02 established: a valid key may carry only the
text authorised for that key, resolved through the corpus itself so there is no
second copy to drift.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Extra, StrictBool, StrictInt, StrictStr, validator

from d12_crosschart_contract import CrossChart, ReleaseTopology, Tri
from d12_instruction_corpus import (
    INSTRUCTION_CORPUS_VERSION, INSTRUCTION_SLOTS, InstructionKeyError,
    TENSION_FALLBACK, TENSION_KEYS, TENSION_TITLE, instruction_text,
)

SELECTORS_CONTRACT_VERSION = "d12-selectors-1.0"


class _Closed(BaseModel):
    class Config:
        extra = Extra.forbid
        allow_mutation = False


class TriggerEvaluation(_Closed):
    """One waterfall candidate, with the evidence that decided it."""
    key: StrictStr
    priority: StrictInt
    result: Tri
    basis: Dict[StrictStr, StrictStr]

    @validator("key")
    def _key_is_a_frozen_tension(cls, v):
        if v not in TENSION_KEYS:
            raise ValueError(f"unknown tension key {v!r}")
        return v

    @validator("priority")
    def _priority_matches_the_locked_order(cls, v, values):
        key = values.get("key")
        if key is not None and TENSION_KEYS.index(key) + 1 != v:
            raise ValueError(
                f"{key!r} sits at priority {TENSION_KEYS.index(key) + 1} in the "
                f"locked waterfall, not {v}")
        return v


class Tension(_Closed):
    """§11 · exactly one tension result: a winner, the exact fallback, or an
    explicitly UNRESOLVED state.

    CORR-02 · the third state is new and load-bearing. If a candidate evaluates
    UNKNOWN before any candidate evaluates TRUE, the waterfall cannot honestly
    continue: a lower trigger winning, or the fallback printing, would both
    assert that the unresolved higher trigger was FALSE. `unresolved_at` names
    the first such candidate and no winner or fallback is produced.
    """
    candidates: List[TriggerEvaluation]
    winner: Optional[StrictStr]
    title: Optional[StrictStr]
    fallback_applied: StrictBool
    fallback_text: Optional[StrictStr]
    unresolved_at: Optional[StrictStr] = None

    @validator("candidates")
    def _all_four_in_waterfall_order(cls, v):
        if tuple(c.key for c in v) != TENSION_KEYS:
            raise ValueError(
                f"candidates must be the four tensions in the locked order, "
                f"got {[c.key for c in v]}")
        return v

    @validator("winner")
    def _winner_is_the_first_true_and_no_unknown_precedes_it(cls, v, values):
        candidates = values.get("candidates")
        if candidates is None:
            return v
        first = None
        for c in candidates:
            if c.result is Tri.UNKNOWN:
                # An unresolved candidate blocks everything below it.
                break
            if c.result is Tri.TRUE:
                first = c.key
                break
        if v != first:
            raise ValueError(
                f"the winner must be the first candidate evaluating TRUE with "
                f"no UNKNOWN before it ({first!r}), got {v!r}")
        return v

    @validator("title")
    def _title_is_the_locked_one(cls, v, values):
        winner = values.get("winner")
        if winner is None:
            if v is not None:
                raise ValueError("no winner, so no title")
            return v
        if v != TENSION_TITLE[winner]:
            raise ValueError(f"title for {winner!r} is not the locked string")
        return v

    @validator("fallback_applied")
    def _fallback_iff_no_winner_and_nothing_unresolved(cls, v, values):
        candidates = values.get("candidates")
        if "winner" not in values or candidates is None:
            return v
        blocked = False
        for c in candidates:
            if c.result is Tri.UNKNOWN:
                blocked = True
                break
            if c.result is Tri.TRUE:
                break
        if blocked and v:
            raise ValueError(
                "the fallback must not print while a higher-priority trigger is "
                "UNKNOWN; that would assert it evaluated FALSE")
        if not blocked and v is (values["winner"] is not None):
            raise ValueError(
                "fallback_applied must be True exactly when there is no winner")
        return v

    @validator("unresolved_at")
    def _unresolved_names_the_blocking_candidate(cls, v, values):
        candidates = values.get("candidates")
        if candidates is None:
            return v
        blocking = None
        for c in candidates:
            if c.result is Tri.UNKNOWN:
                blocking = c.key
                break
            if c.result is Tri.TRUE:
                break
        if v != blocking:
            raise ValueError(
                f"unresolved_at must name the first blocking UNKNOWN candidate "
                f"({blocking!r}), got {v!r}")
        if v is not None and values.get("winner") is not None:
            raise ValueError("an unresolved tension has no winner")
        return v

    @validator("fallback_text")
    def _fallback_text_is_exact_and_only_when_applied(cls, v, values):
        applied = values.get("fallback_applied")
        if applied is None:
            return v
        if applied:
            if v != TENSION_FALLBACK:
                raise ValueError("the fallback text is not the locked FR-002 string")
        elif v is not None:
            raise ValueError("a winning tension carries no fallback text")
        return v


class ThreeInstructions(_Closed):
    """§12 · exactly Cultivate / Watch / Practise for the winning tension.

    `available` is False when the tension fell back: FR-003 authorises exactly
    four triads and the Format Specification supplies no fallback instruction
    rule, so the absence is REPRESENTED rather than filled.
    """
    available: StrictBool
    winner_key: Optional[StrictStr]
    cultivate: Optional[StrictStr]
    watch: Optional[StrictStr]
    practise: Optional[StrictStr]
    absent_reason: Optional[StrictStr]

    @validator("winner_key")
    def _key_present_iff_available(cls, v, values):
        available = values.get("available")
        if available is None:
            return v
        if available and v is None:
            raise ValueError("an available instruction set needs its winner key")
        if not available and v is not None:
            raise ValueError("no instruction set exists without a winning tension")
        return v

    @validator("cultivate", "watch", "practise")
    def _each_slot_is_exact_key_bound(cls, v, values, field):
        available = values.get("available")
        if available is None:
            return v
        if not available:
            if v is not None:
                raise ValueError(
                    f"{field.name} must be absent when no tension won; FR-003 "
                    f"authorises no fifth instruction set")
            return v
        key = values.get("winner_key")
        if key is None:
            return v
        try:
            expected = instruction_text(key, field.name)
        except InstructionKeyError as exc:
            raise ValueError(str(exc))
        if v != expected:
            raise ValueError(
                f"{field.name} is not the locked FR-003 string for {key!r}")
        return v

    @validator("absent_reason")
    def _reason_present_iff_absent(cls, v, values):
        available = values.get("available")
        if available is None:
            return v
        if available and v is not None:
            raise ValueError("an available instruction set carries no absent_reason")
        if not available and not v:
            raise ValueError("an absent instruction set must say why")
        return v


class D12Interpretation(_Closed):
    """The full deterministic §§10-12 layer."""
    selectors_version: StrictStr = SELECTORS_CONTRACT_VERSION
    instruction_corpus_version: StrictStr = INSTRUCTION_CORPUS_VERSION
    crosschart: CrossChart
    release_topology: ReleaseTopology
    tension: Tension
    instructions: ThreeInstructions

    @validator("instructions")
    def _instructions_follow_the_tension(cls, v, values):
        tension = values.get("tension")
        if tension is None:
            return v
        # An unresolved tension has no winner, so it has no instructions either.
        if v.available is not (tension.winner is not None):
            raise ValueError(
                "instructions must be available exactly when a tension won")
        if v.winner_key != tension.winner:
            raise ValueError("the instruction key must be the winning tension")
        return v
