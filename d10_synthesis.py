"""
d10_synthesis.py — D10-007 · synthesis plan, provider boundary, §14 reading.

NO PROVIDER CALL IS MADE OR IMPORTED. This module contains no HTTP client, no
API key, no endpoint and no network import. A test walks the import graph.

THE PROVIDER IS OPTIONAL BY CONSTRUCTION. `build_synthesis` produces a complete
Integrated Reading with no provider argument at all. Passing a provider
response changes only WHICH ATOM each beat foregrounds; every sentence is still
composed here, from ratified corpus text and certified facts.

AN INVALID PROVIDER RESPONSE IS NEVER A FAILURE OF THE READING. It is rejected,
the reason is recorded, and the deterministic path produces the reading. A
chart never loses its §14 because a provider misbehaved.

WHAT CANNOT RE-ENTER HERE. No job title, salary, timing, remedy, agreement word
(`aligned` / `strained` / `redirected`), Devatā ruler or direction, Lagna
Devatā, self-employment claim, travel prediction or Sun/Ketu conflict. None has
a corpus entry or a composition path, and tests assert the absence in the
produced text.
"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Tuple

import d10_corpus as CORPUS
from d10_synthesis_contract import (
    Atom, Beat, BEAT_D9_HANDSHAKE, BEAT_FUNCTION, BEAT_INSTRUCTION, BEAT_ORDER,
    BEAT_STANCE, BEAT_STANDING, BEAT_TENSION,
    CONDITIONAL_BEATS, D10Synthesis, INTEGRATED_READING_MAX_WORDS,
    IntegratedReading, MANDATORY_BEATS, ProviderAtom, ProviderBeat,
    ProviderRequest, ProviderResponse,
    ReadingBeat, SOURCE_DETERMINISTIC, SOURCE_PROVIDER_SELECTION,
    SynthesisPlan,
)

#: The fixed server-owned instruction. It carries no chart material and asks
#: for identifiers only, so it agrees with the schema rather than compensating
#: for it.
PROVIDER_INSTRUCTION = (
    "You are selecting, not writing. For each beat in the plan, choose exactly "
    "one atom_id from the atoms that beat offers, and return only "
    "{beat, atom_id} pairs. Do not write sentences. Do not reorder, add or "
    "omit beats. Do not return any field other than the selections list. Every "
    "sentence in this report is composed by the server from ratified text; "
    "your selection changes only which fact each beat foregrounds."
)

OMISSION_TENSION = "tension_unknown"
OMISSION_D9 = "d9_contribution_unavailable"
OMISSION_INSTRUCTIONS = "no_tension_to_key_instructions_to"


class D10SynthesisError(ValueError):
    """A required certified fact or ratified corpus entry is missing. Raised,
    never defaulted."""


class ProviderResponseRejected(ValueError):
    """The provider response is not a valid selection over this plan. Carried
    as a reason on the reading; never allowed to suppress the reading."""


def _lower_first(text: str) -> str:
    """Lowercase the first character only, so a stored verb phrase can be given
    a subject without disturbing anything else in the line."""
    return text[0].lower() + text[1:] if text else text


def _corpus(table: Mapping, key, what: str):
    if key not in table:
        raise D10SynthesisError(f"no ratified {what} for {key!r}")
    return table[key]


# ─────────────────────────────────────────────────────────────────────────────
# ATOM CONSTRUCTION · one beat at a time
# ─────────────────────────────────────────────────────────────────────────────

def _stance_atoms(f) -> List[Atom]:
    sign = f.stance.d10_lagna_sign
    c = _corpus(CORPUS.STANCE_CORPUS, sign, "stance")
    lg = f.stance.lagnesh
    # D10-007-CORR-01 · THE CORPUS LINES ARE FRAGMENTS AND ARE WRAPPED HERE.
    # `work_behaviour` and `overreach` are stored as verb phrases — "Opens the
    # work by...", "Keeps routing..." — because in §5 they sit under a labelled
    # heading that supplies the subject. Read alone in §14 they have none, so
    # each is given an explicit subject at this seam. The corpus is unchanged.
    return [
        Atom(atom_id="stance.behaviour", beat=BEAT_STANCE, kind="corpus",
             text=f"This chart {_lower_first(c['work_behaviour'])}"),
        Atom(atom_id="stance.lagnesh", beat=BEAT_STANCE, kind="fact",
             text=(f"The stance is {sign} — {c['gloss']} — and it acts through "
                   f"{lg.planet} in H{lg.house} {lg.sign}.")),
        Atom(atom_id="stance.overreach", beat=BEAT_STANCE, kind="corpus",
             text=(f"The same stance overreaches when it "
                   f"{_lower_first(c['overreach'])}")),
    ]


def _function_atoms(f) -> List[Atom]:
    h10, h6 = f.function.h10, f.function.h6
    d10 = _corpus(CORPUS.HOUSE_CORPUS, 10, "house domain")
    d6 = _corpus(CORPUS.HOUSE_CORPUS, 6, "house domain")
    if h10.mode == "THROUGH_LORD":
        lead = (f"The vocation runs through {h10.lord.planet} in "
                f"H{h10.lord.house} {h10.lord.sign} rather than through "
                f"anything sitting in the tenth.")
    else:
        lead = (f"The vocation is worked directly by "
                f"{', '.join(h10.occupants)} in the tenth.")
    return [
        Atom(atom_id="function.h10", beat=BEAT_FUNCTION, kind="fact", text=lead),
        Atom(atom_id="function.domain", beat=BEAT_FUNCTION, kind="corpus",
             text=(f"Day to day, the work is "
                   f"{_lower_first(d10['domain_sentence'])}")),
        Atom(atom_id="function.h6", beat=BEAT_FUNCTION, kind="corpus",
             text=(f"The working conditions are set by "
                   f"{d6['domain_label'].lower()}, with {h6.lord.planet} in "
                   f"H{h6.lord.house}.")),
    ]


def _standing_atoms(f) -> List[Atom]:
    sun = f.standing.sun
    h2 = f.standing.h2_lord
    tenth = f.standing.h10_lord
    return [
        Atom(atom_id="standing.sun", beat=BEAT_STANDING, kind="fact",
             text=(f"Standing attaches at the Sun in H{sun.house} {sun.sign}, "
                   f"{sun.dignity}.")),
        Atom(atom_id="standing.h2", beat=BEAT_STANDING, kind="fact",
             text=(f"What becomes legible runs through {h2.planet} in "
                   f"H{h2.house} {h2.sign}.")),
        Atom(atom_id="standing.tenth_lord", beat=BEAT_STANDING, kind="fact",
             text=(f"The office of the career itself is held by "
                   f"{tenth.planet} in H{tenth.house} {tenth.sign}.")),
    ]


# D10-007-CORR-01 · `_pull_vehicle_atoms` IS DELETED. Pull and vehicle belong
# to §7, where the Jaimini publication is unchanged and complete. Keeping an
# unused builder would leave a §14 beat one line away from returning.


def _tension_atoms(f, publication) -> List[Atom]:
    """The winner is the certified one. This beat offers ways to foreground it,
    never an alternative to it."""
    t = f.tension
    entry = _corpus(CORPUS.TENSION_COPY, t.winner, "tension copy")
    atoms = [Atom(atom_id="tension.heading", beat=BEAT_TENSION, kind="corpus",
                  text=f"The tension worth naming is this: {entry['heading'].lower()}.")]
    e = t.evidence
    if t.winner == "JAIMINI_RIFT":
        detail = (f"{e['ak']} and {e['amk']} share no house and do not aspect "
                  f"one another.")
    elif t.winner == "CORE_OPERATIONAL_CONFLICT":
        detail = (f"{e['lagnesh']} in H{e['lagnesh_house']} and "
                  f"{e['tenth_lord']} in H{e['tenth_lord_house']} sit in a "
                  f"difficult relationship.")
    elif t.winner == "VISIBILITY_GAP":
        detail = (f"{e['h5_count']} grahas gather where work is seen and "
                  f"{e['h12_count']} where it is not.")
    elif t.winner == "SUN_SATURN_FRICTION":
        detail = (f"The Sun in H{e['sun_house']} and Saturn in "
                  f"H{e['saturn_house']} work against each other.")
    else:
        detail = (f"The Sun in H{e['sun_house']} and Saturn in "
                  f"H{e['saturn_house']} stand in no difficult relationship; "
                  f"they simply work in different weather.")
    atoms.append(Atom(atom_id="tension.evidence", beat=BEAT_TENSION,
                      kind="fact", text=detail))
    return atoms


def _d9_handshake_atoms(publication) -> List[Atom]:
    """THE SAME SENTENCE SECTION 6 PUBLISHES, reused unchanged.

    It is not recomposed here and there is no second variant: the value is read
    off the publication's own Section 6 field, which
    `d10_publication.compose_d9_handshake` produced. If D9 published no
    contribution the value is None, this beat is omitted, and Section 6 is
    silent — both from the same source.
    """
    sentence = publication.crosschart_facts.d9_handshake_sentence
    if not sentence:
        return []
    return [Atom(atom_id="d9.handshake", beat=BEAT_D9_HANDSHAKE, kind="fact",
                 text=sentence)]


def _instruction_atoms(publication) -> List[Atom]:
    """One instruction, from the publication's own §13 block.

    D10-007-CORR-01 · `instruction.neutral` IS DELETED. When the publication
    reports `instructions.available == False` there is no tension to key to,
    and a generic practice would be a sentence nobody selected. The beat is
    omitted instead.
    """
    i = publication.instructions
    if not i.available:
        return []
    return [
        Atom(atom_id="instruction.practise", beat=BEAT_INSTRUCTION,
             kind="corpus", text=f"Practise: {_lower_first(i.practise)}"),
        Atom(atom_id="instruction.cultivate", beat=BEAT_INSTRUCTION,
             kind="corpus", text=f"Cultivate: {_lower_first(i.cultivate)}"),
        Atom(atom_id="instruction.watch", beat=BEAT_INSTRUCTION,
             kind="corpus", text=f"Watch: {_lower_first(i.watch)}"),
    ]


# ─────────────────────────────────────────────────────────────────────────────
# THE PLAN
# ─────────────────────────────────────────────────────────────────────────────

class ChartIdentityMismatch(D10SynthesisError):
    """Two layers describe different charts. Raised before any atom is built."""


def _assert_one_chart(findings, crosschart, publication) -> str:
    """D10-007-CORR-01 · IDENTITY IS CLOSED BEFORE ANY ATOM IS BUILT.

    All three layers must name the same certified chart. Checked pairwise so
    the error says which pair disagreed, and checked first so no partial plan
    can exist.
    """
    pairs = (("findings", findings.chart_token, "crosschart", crosschart.chart_token),
             ("findings", findings.chart_token, "publication", publication.chart_token),
             ("crosschart", crosschart.chart_token, "publication", publication.chart_token))
    for a_name, a, b_name, b in pairs:
        if not a or not b:
            raise ChartIdentityMismatch(
                f"{a_name if not a else b_name} carries no chart token")
        if a != b:
            raise ChartIdentityMismatch(
                f"{a_name} and {b_name} chart tokens differ ({a!r} vs {b!r}); "
                f"refusing to synthesise a reading from two charts")
    return findings.chart_token


def build_plan(findings, crosschart, publication) -> SynthesisPlan:
    """Atoms only, in the corrected §14 order.

    A conditional beat is omitted for ENGINE-SILENCE REASONS ONLY: the tension
    was UNKNOWN, D9 published no contribution, or the publication has no
    instructions to key to. Each is a determinate consequence of the certified
    layers, never a provider choice and never a consequence of length.
    """
    token = _assert_one_chart(findings, crosschart, publication)

    builders = [
        (BEAT_STANCE, lambda: _stance_atoms(findings)),
        (BEAT_FUNCTION, lambda: _function_atoms(findings)),
        (BEAT_STANDING, lambda: _standing_atoms(findings)),
        (BEAT_TENSION, lambda: _tension_atoms(findings, publication)),
        (BEAT_D9_HANDSHAKE, lambda: _d9_handshake_atoms(publication)),
        (BEAT_INSTRUCTION, lambda: _instruction_atoms(publication)),
    ]
    beats: List[Beat] = []
    omitted: List[str] = []
    reasons: Dict[str, str] = {}
    position = 0
    for beat_id, make in builders:
        if beat_id == BEAT_TENSION and findings.tension.winner == "UNKNOWN":
            omitted.append(beat_id)
            reasons[beat_id] = OMISSION_TENSION
            continue
        atoms = make()
        if not atoms:
            if beat_id in MANDATORY_BEATS:
                raise D10SynthesisError(f"beat {beat_id} produced no atoms")
            omitted.append(beat_id)
            reasons[beat_id] = (OMISSION_D9 if beat_id == BEAT_D9_HANDSHAKE
                                else OMISSION_INSTRUCTIONS)
            continue
        position += 1
        beats.append(Beat(beat=beat_id, position=position, atoms=atoms,
                          default_atom_id=atoms[0].atom_id))

    present = {b.beat for b in beats}
    missing = set(MANDATORY_BEATS) - present
    if missing:
        raise D10SynthesisError(f"mandatory beats missing: {sorted(missing)}")
    order = [b.beat for b in beats]
    assert order == [b for b in BEAT_ORDER if b in present], order

    return SynthesisPlan(chart_token=token, beats=beats,
                         omitted_beats=omitted, omission_reasons=reasons)


def build_provider_request(plan: SynthesisPlan) -> ProviderRequest:
    """The provider-safe request. NO CALL IS MADE.

    D10-007-CORR-02 · THE PLAN IS NOT SERIALIZED. It carries `chart_token`,
    which is a live chart-resolution capability and has no part in choosing
    emphasis. Only the beat, its position and its atoms are copied across, into
    a contract that has no field for anything else.

    `default_atom_id`, `kind`, `omitted_beats` and `omission_reasons` are also
    left behind: the provider does not need to know what the server would have
    chosen, nor why a beat is missing.
    """
    return ProviderRequest(
        instruction=PROVIDER_INSTRUCTION,
        beats=[ProviderBeat(
            beat=b.beat, position=b.position,
            atoms=[ProviderAtom(atom_id=a.atom_id, text=a.text)
                   for a in b.atoms])
               for b in plan.beats])


# ─────────────────────────────────────────────────────────────────────────────
# PROVIDER VALIDATION
# ─────────────────────────────────────────────────────────────────────────────

def validate_provider_response(plan: SynthesisPlan,
                               response: ProviderResponse) -> Dict[str, str]:
    """Return a beat → atom_id map, or raise.

    Every rejection reason below is a structural one. Nothing is repaired,
    nothing is partially accepted, and a rejected response contributes nothing:
    the reading is then composed deterministically.
    """
    offered = {b.beat: {a.atom_id for a in b.atoms} for b in plan.beats}
    seen: Dict[str, str] = {}
    for sel in response.selections:
        if sel.beat not in offered:
            raise ProviderResponseRejected(
                f"selection names beat {sel.beat!r}, which this plan does not "
                f"contain")
        if sel.beat in seen:
            raise ProviderResponseRejected(
                f"beat {sel.beat!r} selected more than once")
        if sel.atom_id not in offered[sel.beat]:
            raise ProviderResponseRejected(
                f"atom {sel.atom_id!r} is not offered by beat {sel.beat!r}")
        seen[sel.beat] = sel.atom_id
    missing = set(offered) - set(seen)
    if missing:
        raise ProviderResponseRejected(
            f"no selection for beat(s) {sorted(missing)}")
    return seen


# ─────────────────────────────────────────────────────────────────────────────
# THE INTEGRATED READING
# ─────────────────────────────────────────────────────────────────────────────

def _compose(plan: SynthesisPlan, chosen: Mapping[str, str],
             source: str, rejected: Optional[str]) -> IntegratedReading:
    """One sentence per beat, in the fixed order, from the chosen atoms.

    D10-007-CORR-01 · THE BUDGET IS AN INVARIANT, NOT A TRIMMER. Beats are
    omitted upstream for engine-silence reasons only. What remains is what the
    chart supports, and if it exceeds the budget the engine REFUSES.

    The old drop-a-beat loop is deleted. It could remove a VALID tension or a
    VALID D9 handshake to fit a word count, which is a length decision
    overriding a doctrinal one — the reader would lose a finding the chart
    actually made and nothing would say so.
    """
    beats: List[ReadingBeat] = []
    for b in plan.beats:
        atom_id = chosen[b.beat]
        atom = next(a for a in b.atoms if a.atom_id == atom_id)
        beats.append(ReadingBeat(beat=b.beat, position=b.position,
                                 atom_id=atom_id, sentence=atom.text))

    text = " ".join(i.sentence for i in beats)
    words = len(text.split())
    if words > INTEGRATED_READING_MAX_WORDS:
        raise D10SynthesisError(
            f"the integrated reading is {words} words, over the "
            f"{INTEGRATED_READING_MAX_WORDS}-word budget. Refusing: no "
            f"sentence may be truncated and no valid beat may be dropped to "
            f"fit a length.")

    return IntegratedReading(source=source, beats=beats, text=text,
                             word_count=words,
                             provider_rejected_reason=rejected)


def build_integrated_reading(plan: SynthesisPlan,
                             response: Optional[ProviderResponse] = None
                             ) -> IntegratedReading:
    """Compose §14. A provider response is optional and never load-bearing.

    With no response, or with one that fails validation, the deterministic path
    runs and the reading is complete. A rejection is recorded on the reading
    rather than raised, because the customer's reading must not depend on a
    provider behaving.
    """
    default = {b.beat: b.default_atom_id for b in plan.beats}
    if response is None:
        return _compose(plan, default, SOURCE_DETERMINISTIC, None)
    try:
        chosen = validate_provider_response(plan, response)
    except ProviderResponseRejected as exc:
        return _compose(plan, default, SOURCE_DETERMINISTIC, str(exc))
    return _compose(plan, chosen, SOURCE_PROVIDER_SELECTION, None)


def build_integrated_reading_from_raw(plan: SynthesisPlan,
                                      raw: Any) -> IntegratedReading:
    """THE UNTRUSTED BOUNDARY. Accepts whatever a provider actually returned.

    D10-007-CORR-01 · `build_integrated_reading` takes an already-parsed
    `ProviderResponse`, which means the schema rejection happens in the
    CALLER — and an unhandled ValidationError there would cost the customer
    their reading. A provider that returns prose would take the report down.

    Here, EVERY failure mode is caught and converted into a recorded rejection:

        None                 -> deterministic reading, no rejection recorded
        not an object        -> rejected, deterministic reading
        extra prose field    -> rejected, deterministic reading
        malformed selections -> rejected, deterministic reading
        wrong beat or atom   -> rejected, deterministic reading
        valid                -> provider selection used

    Nothing escapes. The reading is produced in every case.
    """
    if raw is None:
        return build_integrated_reading(plan, None)
    try:
        response = (raw if isinstance(raw, ProviderResponse)
                    else ProviderResponse(**raw)
                    if isinstance(raw, Mapping)
                    else None)
        if response is None:
            raise TypeError(
                f"provider output is {type(raw).__name__}, not an object")
    except Exception as exc:                       # noqa: BLE001
        # Deliberately broad. A provider can return anything at all, and the
        # customer's reading must not depend on it being well formed. The
        # reason is recorded rather than swallowed.
        reason = f"{type(exc).__name__}: {str(exc).splitlines()[0][:180]}"
        return _compose(plan, {b.beat: b.default_atom_id for b in plan.beats},
                        SOURCE_DETERMINISTIC, reason)
    return build_integrated_reading(plan, response)


# ─────────────────────────────────────────────────────────────────────────────
# the one public entry point
# ─────────────────────────────────────────────────────────────────────────────

def build_synthesis(findings, crosschart, publication,
                    provider_response: Optional[ProviderResponse] = None,
                    raw_provider_output: Any = None) -> D10Synthesis:
    """Plan plus reading. Deterministic unless a valid provider selection is
    supplied, and complete either way.

    `publication` is REQUIRED. It carries the third chart token the identity
    gate needs, the §13 instructions and the one D9 handshake sentence.
    """
    plan = build_plan(findings, crosschart, publication)
    if raw_provider_output is not None:
        return D10Synthesis(chart_token=plan.chart_token, plan=plan,
                            integrated_reading=build_integrated_reading_from_raw(
                                plan, raw_provider_output))
    return D10Synthesis(chart_token=plan.chart_token, plan=plan,
                        integrated_reading=build_integrated_reading(
                            plan, provider_response))
