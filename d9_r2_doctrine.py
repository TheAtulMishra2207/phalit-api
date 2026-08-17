"""D9-R2-002 · d9_r2_doctrine · DOCTRINE TABLES ONLY.

No route wiring. No selector execution. No import of any live D9 module. This
file is data plus the ratification gate that guards it.

═══════════════════════════════════════════════════════════════════════════════
THE RATIFICATION GATE
═══════════════════════════════════════════════════════════════════════════════

Every table carries a `Status`. The accessors below REFUSE to return anything
that is not `RATIFIED`, and they raise rather than returning empty — a caller
cannot silently proceed on unratified doctrine, and cannot mistake absence for
"no signal".

    RATIFIED        Founder-supplied or Founder-locked verbatim. Consumable.
    AWAITING_RATIFICATION   Dev drafted under explicit Founder authorisation.
                            Readable for review, NOT consumable.
    BLOCKED_INPUT   Founder-supplied text that was never delivered to this
                    thread. Not drafted, not guessed, not consumable.
    SERIALIZATION   Engineering ordering with ZERO doctrinal precedence.

EVERY TABLE IN THIS FILE IS RATIFIED. The doctrine queue is closed: the two
twelve-sign corpora, the seven-graha Mature Capacity corpus, the Contribution
grid and derivation, convergence, strength election, Vargottama, the Growth Edge
binding and the Practise corpus are all Founder-locked, with every value pinned
by full equality in test.

The ratification gate remains in force for future additions — a new table
defaults to unratified and `consume()` refuses it — but nothing is currently
pending.

HISTORICAL: earlier flights wrongly recorded several corpora as missing. They
were supplied; the search was incomplete. Nothing here claims any is absent.
"""

from enum import Enum
from typing import Any, Dict, FrozenSet, List, Optional, Sequence, Tuple


class Status(str, Enum):
    RATIFIED = "RATIFIED"
    AWAITING_RATIFICATION = "AWAITING_RATIFICATION"
    BLOCKED_INPUT = "BLOCKED_INPUT"
    PARTIAL_INPUT = "PARTIAL_INPUT"
    SERIALIZATION = "SERIALIZATION"


class DoctrineNotRatified(RuntimeError):
    """A caller tried to consume doctrine that is not production-authorised."""


class DoctrineInputMissing(RuntimeError):
    """A caller tried to consume a table whose Founder text was never supplied."""


_TABLE_STATUS: Dict[str, Status] = {}


def _register(name: str, status: Status) -> None:
    _TABLE_STATUS[name] = status


def status_of(name: str) -> Status:
    return _TABLE_STATUS[name]


def consume(name: str, table: Any) -> Any:
    """THE ONLY SANCTIONED WAY TO READ A DOCTRINE TABLE.

    Direct module-level access is possible in Python and is not the contract.
    `tests/test_d9_r2_doctrine.py` asserts that every selector path goes through
    here, so an unratified table cannot reach a runtime caller by accident.
    """
    st = _TABLE_STATUS[name]
    if st is Status.PARTIAL_INPUT:
        raise DoctrineInputMissing(
            f"{name}: only part of the Founder text has been supplied. The "
            f"delivered fields are readable through their own accessor; the "
            f"table as a whole is not consumable.")
    if st is Status.BLOCKED_INPUT:
        raise DoctrineInputMissing(
            f"{name}: the Founder-supplied text has not been delivered. It was "
            f"not drafted, because drafting it would present an invention as an "
            f"authority.")
    if st is not Status.RATIFIED:
        raise DoctrineNotRatified(
            f"{name} is {st.value} and may not be consumed as production "
            f"doctrine.")
    return table


# ═════════════════════════════════════════════════════════════════════════════
# SIGNS · shared index, no doctrine
# ═════════════════════════════════════════════════════════════════════════════

SIGNS: Tuple[str, ...] = (
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
)

ELEMENT: Dict[str, str] = {
    "Aries": "Fire", "Leo": "Fire", "Sagittarius": "Fire",
    "Taurus": "Earth", "Virgo": "Earth", "Capricorn": "Earth",
    "Gemini": "Air", "Libra": "Air", "Aquarius": "Air",
    "Cancer": "Water", "Scorpio": "Water", "Pisces": "Water",
}

# Retained for reference only. No doctrine consumes it.
MODALITY: Dict[str, str] = {
    "Aries": "Cardinal", "Cancer": "Cardinal", "Libra": "Cardinal", "Capricorn": "Cardinal",
    "Taurus": "Fixed", "Leo": "Fixed", "Scorpio": "Fixed", "Aquarius": "Fixed",
    "Gemini": "Mutable", "Virgo": "Mutable", "Sagittarius": "Mutable", "Pisces": "Mutable",
}

CLASSICAL_SEVEN: Tuple[str, ...] = (
    "Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn",
)
NODES: Tuple[str, ...] = ("Rahu", "Ketu")


# ═════════════════════════════════════════════════════════════════════════════
# DECISION 1a · THE TWELVE-SIGN D9 MATURITY TABLE
# Status: RATIFIED — Founder corpus, encoded verbatim, 48 values pinned
# ═════════════════════════════════════════════════════════════════════════════
#
# The ticket authorises Dev to draft these twelve for Founder review. They are
# NEW R2 DOCTRINE and are not derived at runtime from element or modality, and
# KARAK_SIGN_DATA is not used as a substitute — that corpus is Swāṁśa-specific
# and says something else.
#
# Register: mature psychological/executive. Not fortune-telling. Each entry
# answers four questions about the sign as a maturation task, in second-person-
# ready form:
#   mature_quality          what matures
#   constructive_expression what it looks like when consciously developed
#   shadow_expression       what it looks like when it runs unconsciously
#   higher_value            what the quality should be placed in service of

D9_MATURITY: Dict[str, Dict[str, str]] = {
    "Aries": {
        "mature_quality": (
            "Autonomous initiative that does not require friction or "
            "external opposition to validate its purpose."
        ),
        "constructive_expression": (
            "Moving decisively when action is warranted, with clear "
            "situational command and strategic restraint."
        ),
        "shadow_expression": (
            "Reactive aggression and manufactured urgency, mistaking speed "
            "for direction and friction for proof of purpose."
        ),
        "higher_value": (
            "Clearing paths for purposeful action and defending what is "
            "vital."
        ),
    },
    "Taurus": {
        "mature_quality": (
            "Deliberate groundedness and sustained stewardship of enduring "
            "value."
        ),
        "constructive_expression": (
            "Creating dependable stability and cultivating tangible "
            "resources that hold through external turbulence."
        ),
        "shadow_expression": (
            "Obstinate inertia, possessiveness, and clinging to familiar "
            "structures past their utility out of fear of loss."
        ),
        "higher_value": (
            "Establishing durable foundations and material security that "
            "sustain life."
        ),
    },
    "Gemini": {
        "mature_quality": (
            "Cognitive versatility that distills multiplicity into clear, "
            "coherent understanding."
        ),
        "constructive_expression": (
            "Translating complex or disparate streams of knowledge into "
            "precise, actionable, and accessible communication."
        ),
        "shadow_expression": (
            "Restless distraction, superficial novelty-seeking, and "
            "weaponized cleverness detached from commitment."
        ),
        "higher_value": (
            "Bridging separate perspectives to make essential truths "
            "understandable and workable."
        ),
    },
    "Cancer": {
        "mature_quality": (
            "Emotional containment and protective care that preserves its "
            "own boundaries."
        ),
        "constructive_expression": (
            "Providing steady psychological safety and nurturing "
            "environments that allow oneself and others to thrive."
        ),
        "shadow_expression": (
            "Defensive withdrawal, emotional manipulation, or fostering "
            "dependency under the guise of care."
        ),
        "higher_value": (
            "Preserving emotional integrity and creating sanctuaries where "
            "life can replenish itself."
        ),
    },
    "Leo": {
        "mature_quality": (
            "Centered sovereignty and authentic dignity that does not "
            "require an audience."
        ),
        "constructive_expression": (
            "Generous, visible stewardship that elevates and empowers the "
            "standing of those within one's sphere."
        ),
        "shadow_expression": (
            "Fragile entitlement, performative pride, and demanding "
            "constant external validation to sustain self-worth."
        ),
        "higher_value": (
            "Living from an incorruptible center that naturally illuminates "
            "and protects the collective."
        ),
    },
    "Virgo": {
        "mature_quality": (
            "Constructive discrimination that refines and remedies rather "
            "than diminishes."
        ),
        "constructive_expression": (
            "Identifying operational flaws clearly and applying practical, "
            "elegant corrections that elevate overall quality."
        ),
        "shadow_expression": (
            "Hyper-critical paralysis, punitive perfectionism, or becoming "
            "lost in trivial details at the expense of completion."
        ),
        "higher_value": (
            "Bringing order, functional integrity, and practical "
            "remediation to complex systems."
        ),
    },
    "Libra": {
        "mature_quality": (
            "Objective equilibrium and structural fairness that can "
            "withstand necessary friction."
        ),
        "constructive_expression": (
            "Establishing durable, balanced agreements and harmonizing "
            "competing interests without compromising core principles."
        ),
        "shadow_expression": (
            "Conflict avoidance, superficial consensus-seeking, and "
            "paralysis masquerading as diplomacy."
        ),
        "higher_value": (
            "Upholding balance, genuine reciprocity, and systemic justice."
        ),
    },
    "Scorpio": {
        "mature_quality": (
            "Psychological depth and emotional truth that does not rely on "
            "concealment or control."
        ),
        "constructive_expression": (
            "Confronting difficult, hidden realities with steady courage, "
            "transforming crisis into unshakeable resilience."
        ),
        "shadow_expression": (
            "Chronic suspicion, calculated secrecy, emotional scorekeeping, "
            "and preemptive self-protection through domination."
        ),
        "higher_value": (
            "Mastering inner transformation and converting vulnerability "
            "into enduring strength."
        ),
    },
    "Sagittarius": {
        "mature_quality": (
            "Principled conviction that remains humble, answerable, and "
            "grounded in lived reality."
        ),
        "constructive_expression": (
            "Inspiring purposeful expansion and ethical alignment while "
            "respecting the complexity of individual cases."
        ),
        "shadow_expression": (
            "Dogmatic moralizing, ungrounded pontification, and dismissing "
            "pragmatic constraints in pursuit of theoretical ideals."
        ),
        "higher_value": (
            "Orienting life toward genuine wisdom, higher meaning, and "
            "universal truth."
        ),
    },
    "Capricorn": {
        "mature_quality": (
            "Sustained accountability and structural mastery carried "
            "without bitterness or martyrdom."
        ),
        "constructive_expression": (
            "Building resilient, long-term frameworks and quietly carrying "
            "duty through adversity to achieve mastery."
        ),
        "shadow_expression": (
            "Cynical rigidity, emotional hardening, and hoarding control "
            "under the belief that only suffering proves value."
        ),
        "higher_value": (
            "Building enduring institutions and systems that outlast the "
            "builder."
        ),
    },
    "Aquarius": {
        "mature_quality": (
            "Principled objectivity that remains engaged and accountable to "
            "the collective."
        ),
        "constructive_expression": (
            "Seeing systemic patterns clearly and designing innovative, "
            "equitable structures that serve the broader whole."
        ),
        "shadow_expression": (
            "Ideological aloofness, intellectual contempt, and using "
            "detachment as a shield against personal vulnerability."
        ),
        "higher_value": (
            "Advancing systemic progress and collective freedom through "
            "grounded innovation."
        ),
    },
    "Pisces": {
        "mature_quality": (
            "Transcendent receptivity anchored into grounded, discerning "
            "form."
        ),
        "constructive_expression": (
            "Translating deep empathy and subtle perception into tangible "
            "relief, creative resonance, and quiet compassion."
        ),
        "shadow_expression": (
            "Escapist boundary dissolution, self-victimization, and diffuse "
            "longing that evades practical responsibility."
        ),
        "higher_value": (
            "Dissolving isolation through authentic grace, spiritual "
            "surrender, and universal empathy."
        ),
    },
}
_register("D9_MATURITY", Status.RATIFIED)


# ═════════════════════════════════════════════════════════════════════════════
# CENTRAL THEME · Section 1 · the ratified four-field spine
# Status: STRUCTURE RATIFIED · VALUES await the two corpora
# ═════════════════════════════════════════════════════════════════════════════
#
# HISTORICAL · CORR-03 deleted the element-relation tension model rather than
# deprecating it in place. It competed with this protocol, and a superseded model left in the file
# is a model someone eventually reads. Gone with it: `Relation`,
# `ELEMENT_RELATION`, `RELATION_RESOLUTION`, `TENSION_FRAMES`,
# `classify_relation`, `MODALITY_QUESTION` and the `developmental_tension` slot.
#
# THE ENGINE MUST NOT GENERATE A FIFTH PROPOSITION. Section 1 is exactly four
# fields, each a straight read from a ratified corpus. The narrative layer may
# connect them grammatically; it may not infer a causal explanation between them.

CENTRAL_THEME_FIELDS: Tuple[str, ...] = (
    "instinctive_playbook",     # ← D1_OUTER_TENDENCY[d1_lagna].outer_orientation
    "emerging_bottleneck",      # ← D1_OUTER_TENDENCY[d1_lagna].default_overextension
    "mature_demanded_mode",     # ← D9_MATURITY[d9_lagna].mature_quality
    "horizon_of_integration",   # ← D9_MATURITY[d9_lagna].higher_value
)

# Each field's source, so a selector cannot silently read the wrong corpus.
CENTRAL_THEME_SOURCES: Dict[str, Tuple[str, str]] = {
    "instinctive_playbook":   ("D1_OUTER_TENDENCY", "outer_orientation"),
    "emerging_bottleneck":    ("D1_OUTER_TENDENCY", "default_overextension"),
    "mature_demanded_mode":   ("D9_MATURITY", "mature_quality"),
    "horizon_of_integration": ("D9_MATURITY", "higher_value"),
}
_register("CENTRAL_THEME_CONTRACT", Status.RATIFIED)

# There is no `developmental_tension`. A test asserts the name appears nowhere.
FORBIDDEN_THEME_FIELDS: Tuple[str, ...] = ("developmental_tension",)


# ── the twelve-sign D1 outer-tendency corpus · RATIFIED ─────────────────────
#
# Founder-supplied, encoded verbatim, 24 values pinned by full equality in test.
# A SEPARATE AUTHORITY from D9_MATURITY: the D1 corpus describes the instinctive
# outer tendency, the D9 corpus describes what maturation demands. Reading one
# for the other was CORR-01's error and a test now forbids it.
#
D1_OUTER_TENDENCY_FIELDS: Tuple[str, ...] = ("outer_orientation",
                                             "default_overextension")
D1_OUTER_TENDENCY: Dict[str, Dict[str, str]] = {
    "Aries": {
        "outer_orientation": (
            "Direct initiative, rapid mobilization, and meeting "
            "circumstances head-on with instinctive momentum and clear "
            "personal agency."
        ),
        "default_overextension": (
            "Forcing outcomes prematurely, escalating friction, and acting "
            "before context or downstream consequences are absorbed."
        ),
    },
    "Taurus": {
        "outer_orientation": (
            "Methodical pacing, sensory realism, and stabilizing situations "
            "through steady, predictable, and tangible execution."
        ),
        "default_overextension": (
            "Habitual inertia, defensive entrenchment, and prioritizing "
            "familiar comfort over necessary operational adaptation."
        ),
    },
    "Gemini": {
        "outer_orientation": (
            "Agile environmental scanning, intellectual curiosity, and "
            "navigating demands through quick communication and conceptual "
            "flexibility."
        ),
        "default_overextension": (
            "Diffuse distraction, endless improvisation without commitment, "
            "and using clever rationalization to avoid depth."
        ),
    },
    "Cancer": {
        "outer_orientation": (
            "Intuitive environmental reading, protective engagement, and "
            "anchoring circumstances through personal rapport and "
            "instinctual care."
        ),
        "default_overextension": (
            "Reactive defensiveness, mood-driven boundary shifts, and "
            "absorbing emotional custody of problems that do not belong to "
            "you."
        ),
    },
    "Leo": {
        "outer_orientation": (
            "Centralized presence, creative ownership, and leading "
            "situations through visible personal authority and decisive "
            "conviction."
        ),
        "default_overextension": (
            "Over-personalizing outcomes, demanding narrative control, and "
            "mistaking external acknowledgment for functional substance."
        ),
    },
    "Virgo": {
        "outer_orientation": (
            "Observational precision, practical troubleshooting, and "
            "improving situations through methodical diagnosis and "
            "functional utility."
        ),
        "default_overextension": (
            "Hyper-fixation on micro-flaws, compulsive over-tinkering, and "
            "analytical paralysis driven by unattainable thresholds of "
            "readiness."
        ),
    },
    "Libra": {
        "outer_orientation": (
            "Social calibration, diplomatic accommodation, and managing "
            "circumstances through consensus, mutual alignment, and "
            "reciprocal agreements."
        ),
        "default_overextension": (
            "Chronic indecision, reflexive conflict avoidance, and diluting "
            "essential positions to preserve superficial harmony."
        ),
    },
    "Scorpio": {
        "outer_orientation": (
            "Strategic wariness, penetrating investigation, and navigating "
            "friction through contained, high-stakes emotional and "
            "situational control."
        ),
        "default_overextension": (
            "Preemptive secrecy, hyper-vigilant suspicion, and "
            "manufacturing tactical leverage where simple transparency "
            "would suffice."
        ),
    },
    "Sagittarius": {
        "outer_orientation": (
            "Expansive optimism, big-picture framing, and meeting demands "
            "through inspiring vision, broad principles, and directional "
            "movement."
        ),
        "default_overextension": (
            "Over-promising on abstract ideals, bypassing structural "
            "constraints, and imposing moralizing answers over pragmatic "
            "realities."
        ),
    },
    "Capricorn": {
        "outer_orientation": (
            "Pragmatic realism, structural discipline, and executing "
            "objectives through patient endurance and strict hierarchical "
            "awareness."
        ),
        "default_overextension": (
            "Rigid transactionalism, emotional hardening, and hoarding "
            "operational burdens out of chronic distrust in others' "
            "competence."
        ),
    },
    "Aquarius": {
        "outer_orientation": (
            "Systemic observation, objective neutrality, and engaging "
            "circumstances through unconventional perspectives and broad "
            "collective principles."
        ),
        "default_overextension": (
            "Ideological aloofness, intellectual contempt, and using "
            "theoretical distance as an excuse to avoid personal "
            "vulnerability or messy execution."
        ),
    },
    "Pisces": {
        "outer_orientation": (
            "Fluid adaptability, holistic empathy, and navigating "
            "circumstances through intuitive resonance and porous "
            "contextual flexibility."
        ),
        "default_overextension": (
            "Diffuse boundaries, passive avoidance of friction, and "
            "drifting away from definitive accountability when direct "
            "action is required."
        ),
    },
}
_register("D1_OUTER_TENDENCY", Status.RATIFIED)


# ═════════════════════════════════════════════════════════════════════════════
# DECISION 2 · STRENGTH ELECTION
# Status: RATIFIED — Founder-locked in the D9-R2-002 ticket, encoded verbatim
# ═════════════════════════════════════════════════════════════════════════════

STRENGTH_ELIGIBLE_GRAHAS: Tuple[str, ...] = CLASSICAL_SEVEN     # nodes excluded absolutely

# Published band, highest first. Moolatrikona is subsumed under Own Sign by the
# publication wall and is NOT a separate band here — restoring it would undo the
# collapse the wall performs.
STRENGTH_BANDS: Tuple[str, ...] = ("Exalted", "Own Sign", "Friendly Sign")


class Election(str, Enum):
    SINGLE = "SINGLE"
    DUAL = "DUAL"
    COMPOUND = "COMPOUND"
    FOUNDATIONAL_RESILIENCE = "FOUNDATIONAL_RESILIENCE"


def elect_strength_shape(candidates_by_band: Dict[str, List[str]]) -> Tuple[Election, Optional[str], List[str]]:
    """Highest OCCUPIED qualifying band, then cardinality. No scoring.

    Explicitly absent, and each absence is a Founder lock:
      · no `certified_rank` — it orders Moolatrikona above Own Sign, a
        distinction publication deliberately collapses;
      · no natural-planet hierarchy tie-break;
      · no promotion of Neutral, Enemy or Debilitated grahas.
    """
    for band in STRENGTH_BANDS:
        occupants = [g for g in candidates_by_band.get(band, [])
                     if g in STRENGTH_ELIGIBLE_GRAHAS]
        if not occupants:
            continue
        n = len(occupants)
        shape = (Election.SINGLE if n == 1 else
                 Election.DUAL if n == 2 else Election.COMPOUND)
        return shape, band, sorted(occupants, key=CLASSICAL_SEVEN.index)
    return Election.FOUNDATIONAL_RESILIENCE, None, []


# ── serialization order · ZERO doctrinal precedence ──────────────────────────
#
# DUAL is symmetric, so no operand assignment depends on order. The canonical
# classical sequence exists only to make output stable and diffable, and a test
# asserts that passing the same two grahas in either order produces an identical
# payload.
#
# HISTORICAL: an earlier asymmetric rule made order load-bearing, which is why
# this constant is registered as SERIALIZATION rather than doctrine.
SERIALIZATION_ORDER: Tuple[str, ...] = CLASSICAL_SEVEN
SERIALIZATION_HAS_NO_PRECEDENCE = True
_register("SERIALIZATION_ORDER", Status.SERIALIZATION)


# ═════════════════════════════════════════════════════════════════════════════
# VARGOTTAMA MODIFIER · Status: RATIFIED · single tag
# ═════════════════════════════════════════════════════════════════════════════
#
# CORR-03 · the two-tag question is answered and closed. One tag.

VARGOTTAMA_TAG = "Rooted Across Both Charts"

VARGOTTAMA_DESCRIPTION = (
    "This capacity carries direct continuity between your instinctive "
    "expression and its mature form, developing through refinement rather than "
    "a shift in fundamental orientation."
)

# Condition, evaluated POST-ELECTION ONLY.
VARGOTTAMA_CONDITION = "D1_sign(elected_graha) == D9_sign(elected_graha)"

# The modifier has no selective power whatsoever.
VARGOTTAMA_MAY_ELECT = False
VARGOTTAMA_MAY_BREAK_TIE = False
VARGOTTAMA_MAY_INCREASE_DIGNITY = False
VARGOTTAMA_MAY_DISPLACE_HIGHER_BAND = False
VARGOTTAMA_MAY_RESCUE_ZERO_CANDIDATE = False
VARGOTTAMA_IS_POST_ELECTION_ONLY = True
_register("VARGOTTAMA", Status.RATIFIED)


def vargottama_tags(elected: Sequence[str],
                    d1_sign_of: Dict[str, str],
                    d9_sign_of: Dict[str, str]) -> Dict[str, str]:
    """Tag the qualifying elected grahas. PER GRAHA, not per election.

    In DUAL and COMPOUND the tag attaches only to the grahas that actually
    qualify, so one may carry it and another may not. Applied strictly after
    election: this function cannot change who was elected because it is not
    given the candidate set.
    """
    return {g: VARGOTTAMA_TAG for g in elected
            if d1_sign_of.get(g) is not None
            and d1_sign_of.get(g) == d9_sign_of.get(g)}


# ═════════════════════════════════════════════════════════════════════════════
# DECISION 3 · SEVEN-GRAHA MATURE CAPACITY CORPUS
# Status: RATIFIED — Founder Decision 3, all four fields, all seven grahas
# ═════════════════════════════════════════════════════════════════════════════
#
# RATIFIED · Founder Decision 3, all four fields. HISTORICAL: earlier flights
# twice recorded this as missing or partial.
# Flight 2 called it missing; Flight 3 called it partial, on the ground
# that only `core_capacity` had reached me. Both were wrong, and the second was
# wrong in a way that looked like diligence — I searched, found one field,
# and concluded the rest did not exist rather than that I had not found them.
#
# All 28 values below are the Founder's, encoded verbatim. A test pins every one
# by full-value equality, not by non-emptiness, so a transcription slip fails
# loudly rather than shipping as doctrine.

MATURE_CAPACITY_FIELDS: Tuple[str, ...] = (
    "core_capacity",
    "constructive_expression",
    "misuse_shadow",            # EXCLUDED from the strength card
    "dependable_mechanism",
)

MATURE_CAPACITY: Dict[str, Dict[str, str]] = {
    "Sun": {
        "core_capacity": "Sovereignty & Moral Centeredness",
        "constructive_expression": (
            "Responsible authority, self-evident integrity, authentic "
            "leadership, and the ability to hold space for others without "
            "diminishing oneself."),
        "misuse_shadow": (
            "Egoic entrenchment, demand for external validation, autocratic "
            "control, or mistaking personal pride for principle."),
        "dependable_mechanism": (
            "When actions are anchored in selfless stewardship and duty "
            "(Dharma) rather than the pursuit of recognition."),
    },
    "Moon": {
        "core_capacity": "Intuitive Receptivity & Emotional Attunement",
        "constructive_expression": (
            "Psychological safety, adaptive empathy, nurturing discernment, "
            "and the ability to stay grounded through cyclical internal and "
            "external changes."),
        "misuse_shadow": (
            "Emotional volatility, over-identification with fluctuating moods, "
            "codependency, or protective withdrawal."),
        "dependable_mechanism": (
            "When emotional perception is treated as an informative signal "
            "rather than an absolute, reactive reality."),
    },
    "Mars": {
        "core_capacity": "Decisive Agency & Disciplined Drive",
        "constructive_expression": (
            "Direct courage, strategic friction tolerance, boundary "
            "enforcement, and clear, purposeful execution under pressure."),
        "misuse_shadow": (
            "Impulsive aggression, unnecessary conflict-seeking, impatience, "
            "or brute force replacing calibrated skill."),
        "dependable_mechanism": (
            "When raw vigor is subordinated to a clear goal and governed by "
            "deliberate ethical restraint."),
    },
    "Mercury": {
        "core_capacity": "Cognitive Discrimination & Articulation",
        "constructive_expression": (
            "Objective analysis, intellectual flexibility, precise "
            "communication, data synthesis, and agile problem-solving."),
        "misuse_shadow": (
            "Overthinking, cynical detachment, superficial rationalization, or "
            "weaponized cleverness without substance."),
        "dependable_mechanism": (
            "When intellectual sharpness is tethered to tangible reality and "
            "applied toward functional clarity."),
    },
    "Jupiter": {
        "core_capacity": "Ethical Perspective & Sound Counsel",
        "constructive_expression": (
            "High-order discernment, principled optimism, expansive "
            "perspective, authentic mentorship, and synthesizing long-term "
            "wisdom."),
        "misuse_shadow": (
            "Dogmatic self-righteousness, ungrounded idealism, intellectual "
            "inflation, or offering unsolicited moralizing advice."),
        "dependable_mechanism": (
            "When broad philosophical principles are tested against lived "
            "experience and humble self-correction."),
    },
    "Venus": {
        "core_capacity": "Relational Intelligence & Value Alignment",
        "constructive_expression": (
            "Diplomatic mediation, aesthetic and structural refinement, "
            "creating mutually generative agreements, and elevating quality of "
            "life."),
        "misuse_shadow": (
            "Conflict avoidance, superficial appeasement, transactional "
            "vanity, or compromising core values for short-term ease."),
        "dependable_mechanism": (
            "When relational harmony is built on genuine mutual respect rather "
            "than artificial peacekeeping."),
    },
    "Saturn": {
        "core_capacity": "Structural Endurance & Long-Horizon Discipline",
        "constructive_expression": (
            "Realistic appraisal, patient craftsmanship, accountability under "
            "adversity, and building durable frameworks that outlast immediate "
            "pressure."),
        "misuse_shadow": (
            "Chronic fatalism, emotional paralysis, rigid conservatism, or "
            "imposing punitive control out of fear."),
        "dependable_mechanism": (
            "When constraints and burdens are accepted without bitterness as "
            "necessary scaffolding for mastery."),
    },
}
_register("MATURE_CAPACITY", Status.RATIFIED)

# Convenience view. Not a separate authority — derived from the corpus above.
MATURE_CAPACITY_CORE: Dict[str, str] = {
    g: e["core_capacity"] for g, e in MATURE_CAPACITY.items()
}

# The Principal Strength card publishes three of the four. `misuse_shadow` is
# excluded from it and is CALIBRATION for the strength — "when this strength
# overreaches". It is NOT the Growth Edge, which reads the D9 shadow only.
STRENGTH_CARD_FIELDS: Tuple[str, ...] = (
    "core_capacity", "constructive_expression", "dependable_mechanism",
)
# Calibration only. `GROWTH_EDGE_MAY_CONSUME` is DELETED, not renamed: it was an
# exported executable authority whose name invited exactly the wrong read, and a
# compatibility alias that contradicts the doctrine is worse than no alias.
# The Growth Edge layer belongs to D9_MATURITY.shadow_expression alone.
STRENGTH_CALIBRATION_FIELD: Tuple[str, ...] = ("misuse_shadow",)


def strength_card_renderable() -> bool:
    """True: every card field is present for every classical graha."""
    return all(all(f in MATURE_CAPACITY[g] for f in STRENGTH_CARD_FIELDS)
               for g in CLASSICAL_SEVEN)


# ── DUAL / COMPOUND rendering · RATIFIED · SYMMETRIC ────────────────────────
#
# DUAL is unordered semantic co-indicators: both constructive expressions and
# both dependable mechanisms travel co-equally, and the serialization order
# carries no interpretive meaning. COMPOUND retains every elected graha.
#
# HISTORICAL: an earlier asymmetric model blended graha A's constructive
# expression with graha B's mechanism. It was replaced, not assigned.
DUAL_MODE = "unordered semantic co-indicators"
DUAL_FIELDS: Tuple[str, ...] = ("title", "constructive_expressions",
                                "dependable_mechanisms")
# No driver, stabilizer, lead, secondary, vision or execution field exists.
DUAL_FORBIDDEN_FIELDS: Tuple[str, ...] = (
    "driver", "stabilizer", "stabiliser", "lead", "secondary", "vision",
    "execution", "primary_graha", "supporting_graha",
)
COMPOUND_TITLE = "A Foundation of Convergent Capacities"
_register("DUAL_CONTRACT", Status.RATIFIED)
_register("COMPOUND_CONTRACT", Status.RATIFIED)


def build_strength_payload(shape: "Election", grahas: Sequence[str]) -> Dict[str, Any]:
    """Structured source model for the Strength card. No hierarchy, ever.

    DUAL is co-equal: both constructive expressions and both dependable
    mechanisms travel, and the serialization order carries zero interpretive
    meaning. COMPOUND keeps EVERY elected graha in the factual basis — no top-two
    election, no weighting. The narrative layer may compress the prose; it may
    not drop a graha or rank them.
    """
    ordered = [g for g in SERIALIZATION_ORDER if g in grahas]
    caps = consume("MATURE_CAPACITY", MATURE_CAPACITY)
    if shape is Election.SINGLE:
        g = ordered[0]
        return {"mode": "SINGLE", "grahas": ordered,
                "title": caps[g]["core_capacity"],
                "constructive_expressions": [caps[g]["constructive_expression"]],
                "dependable_mechanisms": [caps[g]["dependable_mechanism"]]}
    if shape is Election.DUAL:
        return {"mode": "DUAL", "grahas": ordered,
                "title": " & ".join(caps[g]["core_capacity"] for g in ordered),
                "constructive_expressions": [caps[g]["constructive_expression"] for g in ordered],
                "dependable_mechanisms": [caps[g]["dependable_mechanism"] for g in ordered],
                "co_equal": True}
    if shape is Election.COMPOUND:
        return {"mode": "COMPOUND", "grahas": ordered,
                "title": COMPOUND_TITLE,
                "constructive_expressions": [caps[g]["constructive_expression"] for g in ordered],
                "dependable_mechanisms": [caps[g]["dependable_mechanism"] for g in ordered],
                "co_equal": True}
    return {"mode": "FOUNDATIONAL_RESILIENCE", "grahas": [],
            "basis": "d9_lagna_mature_capacity"}


# ═════════════════════════════════════════════════════════════════════════════
# DECISION 4 · CONTRIBUTION ARCHETYPES
# Status: RATIFIED — names, grid and publication meanings all Founder-supplied
# ═════════════════════════════════════════════════════════════════════════════

class Archetype(str, Enum):
    KNOWLEDGE_TRANSMISSION = "KNOWLEDGE_TRANSMISSION"
    CREATION_CULTIVATION = "CREATION_CULTIVATION"
    STEWARDSHIP_INSTITUTION = "STEWARDSHIP_INSTITUTION"
    ENTERPRISE_MATERIAL_VALUE = "ENTERPRISE_MATERIAL_VALUE"
    SERVICE_RESTORATION = "SERVICE_RESTORATION"
    DHARMA_INNER_ORIENTATION = "DHARMA_INNER_ORIENTATION"

ARCHETYPES: Tuple[Archetype, ...] = tuple(Archetype)
_register("ARCHETYPES", Status.RATIFIED)

# ── the human meaning of each archetype · RATIFIED · Founder Decision 4 ──────
#
# Flight 6 encoded the six enum labels and the grid, and stopped there — so
# Section 2.3 returned classification codes with no proposition a reader could
# use, and Flight 8's provider would have had to INFER what
# `KNOWLEDGE_TRANSMISSION` means. That is the provider becoming the astrologer,
# which is the one thing R2 exists to prevent.
#
# The enum stays an internal identifier. This table is the customer content.

ARCHETYPE_PUBLICATION: Dict[Archetype, Dict[str, str]] = {
    Archetype.KNOWLEDGE_TRANSMISSION: {
        "title": "Knowledge & Transmission",
        "core_impulse": ("Understanding, teaching, translating, systematizing "
                         "insight"),
    },
    Archetype.CREATION_CULTIVATION: {
        "title": "Creation & Cultivation",
        "core_impulse": ("Shaping aesthetics, culture, emotional resonance, and "
                         "creative forms"),
    },
    Archetype.STEWARDSHIP_INSTITUTION: {
        "title": "Stewardship & Institution",
        "core_impulse": ("Sustaining governance, structural order, systemic "
                         "longevity"),
    },
    Archetype.ENTERPRISE_MATERIAL_VALUE: {
        "title": "Enterprise & Material Value",
        "core_impulse": ("Initiative, economic circulation, resource "
                         "orchestration"),
    },
    Archetype.SERVICE_RESTORATION: {
        "title": "Service & Restoration",
        "core_impulse": ("Healing, practical maintenance, systemic remediation, "
                         "relief"),
    },
    Archetype.DHARMA_INNER_ORIENTATION: {
        "title": "Dharma & Inner Orientation",
        "core_impulse": ("Spiritual alignment, moral compass, philosophical "
                         "grounding"),
    },
}
_register("ARCHETYPE_PUBLICATION", Status.RATIFIED)


def publish_archetypes(values: Sequence[str]) -> List[Dict[str, str]]:
    """Enum identifiers → the deterministic human propositions.

    Used everywhere an archetype reaches a customer surface, so no consumer ever
    has to interpret an enum name.
    """
    table = consume("ARCHETYPE_PUBLICATION", ARCHETYPE_PUBLICATION)
    out = []
    for v in values:
        arch = v if isinstance(v, Archetype) else Archetype(v)
        out.append({"archetype": arch.value, **table[arch]})
    return out

# ── Karakāṁśa domains · FRAME IS LOAD-BEARING ────────────────────────────────
#
# KARAKAMSHA_Hx_D1_FRAME: D1 planetary sign positions counted from the Karakāṁśa
# Lagna. These are NOT ordinary D9-Lagna houses, and converting them would
# silently change what every accepted rule asserts.

# The FAMILY name, for documentation only. It must never be a live domain value —
# the whole point of the frame lock is that a reader can tell H5 from H9 from H10
# without inferring it, and a wildcard reintroduces exactly the ambiguity the
# lock was written against.
CONTRIBUTION_FRAME_FAMILY = "KARAKAMSHA_Hx_D1_FRAME"

CONTRIBUTION_DOMAIN_FRAMES: Dict[int, str] = {
    5: "KARAKAMSHA_H5_D1_FRAME",
    9: "KARAKAMSHA_H9_D1_FRAME",
    10: "KARAKAMSHA_H10_D1_FRAME",
}
_register("CONTRIBUTION_DOMAIN_FRAMES", Status.RATIFIED)

CONTRIBUTION_DOMAINS: Dict[int, str] = {
    5: "Innate Capacity",
    9: "Ethical Alignment",
    10: "Visible Impact",
}
_register("CONTRIBUTION_DOMAINS", Status.RATIFIED)

# ── the Founder Contribution grid · RATIFIED · Decision 4, verbatim ──────────
#
# HISTORICAL · CORR-01 wrongly recorded this grid as missing. Supplied in Founder
# Decision 4 and encoded below exactly as given, with Sanskrit graha names mapped
# to the engine's English names:
#   Sūrya=Sun · Candra=Moon · Maṅgala=Mars · Budha=Mercury
#   Guru=Jupiter · Śukra=Venus · Śani=Saturn · Ketu=Ketu
#
# ⚠ KETU IS A CONTRIBUTION SIGNIFIER AND IS NOT ELIGIBLE FOR STRENGTH.
# The Founder grid includes Ketu under Dharma & Inner Orientation. Nodes remain
# excluded from the STRENGTH election absolutely. These are two different rules
# over the same graha and must never be conflated — a test pins both directions.

ARCHETYPE_GRAHAS: Dict[Archetype, Tuple[str, ...]] = {
    Archetype.KNOWLEDGE_TRANSMISSION:  ("Jupiter", "Mercury"),
    Archetype.CREATION_CULTIVATION:    ("Venus", "Moon"),
    Archetype.STEWARDSHIP_INSTITUTION: ("Sun", "Saturn"),
    Archetype.ENTERPRISE_MATERIAL_VALUE: ("Mercury", "Mars", "Venus"),
    Archetype.SERVICE_RESTORATION:     ("Saturn", "Mercury", "Moon"),
    Archetype.DHARMA_INNER_ORIENTATION: ("Jupiter", "Sun", "Ketu"),
}

ARCHETYPE_SIGNS: Dict[Archetype, Tuple[str, ...]] = {
    Archetype.KNOWLEDGE_TRANSMISSION:  ("Gemini", "Virgo", "Sagittarius"),
    Archetype.CREATION_CULTIVATION:    ("Taurus", "Libra", "Cancer", "Leo"),
    Archetype.STEWARDSHIP_INSTITUTION: ("Capricorn", "Leo", "Aries"),
    Archetype.ENTERPRISE_MATERIAL_VALUE: ("Taurus", "Virgo", "Scorpio"),
    Archetype.SERVICE_RESTORATION:     ("Virgo", "Pisces", "Aquarius"),
    Archetype.DHARMA_INNER_ORIENTATION: ("Sagittarius", "Pisces", "Aries"),
}


def _invert(table: Dict[Archetype, Tuple[str, ...]]) -> Dict[str, FrozenSet[Archetype]]:
    out: Dict[str, set] = {}
    for arch, keys in table.items():
        for k in keys:
            out.setdefault(k, set()).add(arch)
    return {k: frozenset(v) for k, v in out.items()}


# Derived by inversion, never hand-written — so the grid has exactly one source
# of truth and a transcription slip cannot survive in only one direction.
GRAHA_ARCHETYPES: Dict[str, FrozenSet[Archetype]] = _invert(ARCHETYPE_GRAHAS)
SIGN_ARCHETYPES: Dict[str, FrozenSet[Archetype]] = _invert(ARCHETYPE_SIGNS)
_register("ARCHETYPE_GRAHAS", Status.RATIFIED)
_register("ARCHETYPE_SIGNS", Status.RATIFIED)
_register("GRAHA_ARCHETYPES", Status.RATIFIED)
_register("SIGN_ARCHETYPES", Status.RATIFIED)

# Independent check the ticket itself supplies: its §9 worked examples say
# Mercury and Virgo each map to {Knowledge, Enterprise, Service} and Jupiter to
# {Knowledge, Dharma}. The inversion above must reproduce all three. Asserted by
# test rather than trusted.

# ── domain evidence precedence · RATIFIED ───────────────────────────────────
#
# The Founder supplied the GRID, the H5/H9/H10 domain meanings and the
# cross-domain convergence logic. He did NOT rule that occupant evidence
# suppresses lord and sign evidence. CORR-00 labelled that precedence RATIFIED;
# it is a Dev proposal and is marked as one.
# RATIFIED. HISTORICAL: a Dev proposal suppressed by precedence; the
# ratified rule is different and better — the SIGN REFINES BUT NEVER EXPANDS.
#
#   if the house is occupied: primary grahas = all CLASSICAL occupants + Ketu
#   else:                     primary grahas = the house lord
#   A_graha = union of archetypes over the primary grahas
#   A_sign  = archetypes of the house sign
#   domain_signal = (A_graha ∩ A_sign) if non-empty else A_graha
#
# RAHU DOES NOT CONTRIBUTE. It is not in the Founder grid and is not mapped.
# Ketu does contribute, and is still never strength-eligible.
CONTRIBUTION_OCCUPANT_GRAHAS: Tuple[str, ...] = CLASSICAL_SEVEN + ("Ketu",)
CONTRIBUTION_EXCLUDED_GRAHAS: Tuple[str, ...] = ("Rahu",)
SIGN_REFINES_NEVER_EXPANDS = True
_register("DOMAIN_DERIVATION", Status.RATIFIED)


# ═════════════════════════════════════════════════════════════════════════════
# CROSS-DOMAIN CONVERGENCE · Founder-locked, encoded verbatim
# ═════════════════════════════════════════════════════════════════════════════

class Convergence(str, Enum):
    UNIFIED_PURPOSE = "UNIFIED_PURPOSE"          # H5 ∩ H9 ∩ H10 non-empty
    PAIRWISE = "PAIRWISE"                        # a pair intersects
    COMPOUND_MULTI_POLAR = "COMPOUND_MULTI_POLAR"  # all pairs empty
    SUPPRESSED = "SUPPRESSED"                    # every domain signal empty

# CORR-03 · Founder-ratified. `DoctrineTopologyUnresolved` is DELETED — the
# two-domain disagreement it guarded is now covered by COMPOUND_MULTI_POLAR, so
# the guard has nothing left to catch and keeping it would be superstition.
#
# PAIRWISE PRECEDENCE: when several pairs intersect, H9 ∩ H10 wins and H5 becomes
# the operational/aptitude modifier.
PAIRWISE_PRECEDENCE: Tuple[Tuple[int, int], ...] = ((9, 10), (5, 9), (5, 10))
PAIRWISE_MODIFIER_DOMAIN = 5

# CORR-04 · the dissenting domain always supplies a vector, and its doctrinal
# name depends on which domain dissents.
PAIRWISE_DISSENT_ROLE: Dict[int, str] = {
    10: "Functional/Impact Vector",
    9: "Ethical Functional Vector",
    5: "Innate/Aptitude Modifier",
}
PAIRWISE_DISSENT_KEY: Dict[int, str] = {
    10: "functional_vector",
    9: "ethical_functional_vector",
    5: "aptitude_modifier",
}

MULTI_POLAR_ROLES: Dict[int, str] = {
    10: "Primary Impact Vector",
    9: "Ethical Driver",
    5: "Innate Aptitude",
}
UNIFIED_PURPOSE_LABEL = "Unified Purpose"
_register("CONVERGENCE", Status.RATIFIED)

# No "No Signal" customer card. SUPPRESSED hides the archetype reading and the
# selector attaches the authorised D9 LAGNA MATURITY material — `mature_quality`
# and `higher_value`. No Swāṁśa proposition is claimed.
SUPPRESSED_EMITS_CUSTOMER_CARD = False


# ═════════════════════════════════════════════════════════════════════════════
# GROWTH EDGE / INNER FRICTION · section 2.2 · candidate model
# ═════════════════════════════════════════════════════════════════════════════
#
# No new astrology engine. Three deterministic inputs, all already selected
# elsewhere in the report:

# FOUNDER MICRO-RULING 1 of 2 · RATIFIED. There is NO selector and NO precedence
# table — the question I returned in Flight 5 is answered by removing the choice:
#
#     growth_edge = D9_MATURITY[d9_lagna]["shadow_expression"]
#
# THREE SEPARATE LAYERS, and none may substitute for another. They describe
# different things about different subjects, and collapsing any two would be the
# same class of error as reading the D1 corpus for the D9 one.
#
#   Section 1    D1 default_overextension  → Emerging Bottleneck
#   Section 2.1  elected graha misuse_shadow → "when this strength overreaches"
#   Section 2.2  D9 shadow_expression      → Growth Edge / Inner Friction

GROWTH_EDGE_SOURCE: Tuple[str, str] = ("D9_MATURITY", "shadow_expression")
GROWTH_EDGE_CONTEXT: Tuple[str, str] = ("D9_MATURITY", "mature_quality")

# Each layer's sole permitted consumer. A test asserts no crossover.
LAYER_OWNERSHIP: Dict[str, Tuple[str, str]] = {
    "emerging_bottleneck": ("D1_OUTER_TENDENCY", "default_overextension"),
    "strength_calibration": ("MATURE_CAPACITY", "misuse_shadow"),
    "growth_edge": ("D9_MATURITY", "shadow_expression"),
}
_register("GROWTH_EDGE", Status.RATIFIED)


# ═════════════════════════════════════════════════════════════════════════════
# YOUR THREE INSTRUCTIONS · section 4 · mappings only
# ═════════════════════════════════════════════════════════════════════════════

# The ratified triad. `cultivate` reads TWO fields.
THREE_INSTRUCTIONS_SOURCES: Dict[str, Tuple[str, str]] = {
    "cultivate": ("D9_MATURITY", "mature_quality+constructive_expression"),
    "watch":     ("D9_MATURITY", "shadow_expression"),
    "practise":  ("PRACTISE_BEHAVIOUR", "d9_lagna_sign"),
}

# FOUNDER MICRO-RULING 2 of 2 · RATIFIED · Founder corpus, encoded verbatim.
#
# HISTORICAL: Flight 6 shipped the Flight 5 Dev draft under this name on a
# guessed reading of "exactly as supplied". All twelve differed from the Founder
# text. A guess dressed as a reading is still a guess, and it was wrong 12/12.
# The real corpus is below, pinned by full equality, and a test asserts the old
# draft cannot silently reappear.
#
# Keyed by the D9 Lagna sign. One bounded, concrete, repeatable behaviour each.
#
# STANDING BANS HOLD, asserted by test: no mantra, gemstone, weekday, deity
# remedy, donation, ritual or promised remedial result.
PRACTISE_BEHAVIOUR: Dict[str, str] = {
    "Aries": (
        "Before acting on urgency, name the objective, the real "
        "constraint, and the likely consequence. Then act decisively."
    ),
    "Taurus": (
        "At regular intervals, review what you are maintaining and "
        "deliberately release or change one structure that no longer "
        "serves its purpose."
    ),
    "Gemini": (
        "Reduce competing inputs to one written conclusion and one next "
        "action before opening another line of inquiry."
    ),
    "Cancer": (
        "Before taking responsibility for another person's difficulty, "
        "identify clearly what is yours to hold and what must remain "
        "theirs."
    ),
    "Leo": (
        "Make important decisions from the principle you are "
        "responsible for upholding, then communicate the decision "
        "without seeking validation for yourself."
    ),
    "Virgo": (
        "Define the standard for “complete enough” before beginning, "
        "finish when that standard is met, and schedule refinement "
        "separately."
    ),
    "Libra": (
        "State the principle or boundary you cannot compromise before "
        "beginning negotiation over the terms."
    ),
    "Scorpio": (
        "When stakes rise, state the difficult fact directly before "
        "resorting to withholding, testing, strategic silence, or "
        "control."
    ),
    "Sagittarius": (
        "Before acting on a broad principle, name the concrete "
        "constraint, the specific case, and one fact that could "
        "challenge your preferred conclusion."
    ),
    "Capricorn": (
        "Delegate one bounded responsibility with a clear standard, "
        "deadline, and owner, and do not reclaim it unless the agreed "
        "standard actually fails."
    ),
    "Aquarius": (
        "Convert one systemic insight into a small accountable "
        "experiment with an owner, a measurable result, and a review "
        "point."
    ),
    "Pisces": (
        "Convert one intuitive concern or compassionate impulse into a "
        "concrete action with a boundary, a timeframe, and an "
        "observable outcome."
    ),
}
_register("PRACTISE_BEHAVIOUR", Status.RATIFIED)

PRACTISE_BEHAVIOUR_KEY = "d9_lagna_sign"

# Backward-compatible alias for the Flight 5 name. Same object, not a copy.
BEHAVIOURAL_TRANSLATION = PRACTISE_BEHAVIOUR
_register("BEHAVIOURAL_TRANSLATION", Status.RATIFIED)
_register("THREE_INSTRUCTIONS_SOURCES", Status.RATIFIED)


# ═════════════════════════════════════════════════════════════════════════════
# DECISION 5 · TIMING
# ═════════════════════════════════════════════════════════════════════════════

# CORR-03 · every v1 timing stub is deleted. One policy constant remains so the
# omission is stated rather than merely absent.
R2_TIMING_POLICY = "OMITTED"
_register("TIMING", Status.RATIFIED)


# ═════════════════════════════════════════════════════════════════════════════
# ASPECT BOUNDARY
# ═════════════════════════════════════════════════════════════════════════════

D9_ASPECTS_AUTHORISED = False
KARAKAMSHA_ASPECTS_AUTHORISED = False
NEW_ASPECT_SUBSYSTEM_AUTHORISED = False
# No already-certified D1-frame aspect primitive was found that the accepted
# house doctrine consumes, so aspects stay out of the Contribution selector.
CONTRIBUTION_CONSUMES_ASPECTS = False
_register("ASPECT_BOUNDARY", Status.RATIFIED)


# ═════════════════════════════════════════════════════════════════════════════
# TABLE REGISTRY · what a reviewer should look at first
# ═════════════════════════════════════════════════════════════════════════════

def registry() -> List[Tuple[str, str]]:
    return sorted((name, st.value) for name, st in _TABLE_STATUS.items())


def blocked_inputs() -> List[str]:
    return sorted(n for n, st in _TABLE_STATUS.items() if st is Status.BLOCKED_INPUT)


def awaiting_ratification() -> List[str]:
    return sorted(n for n, st in _TABLE_STATUS.items()
                  if st is Status.AWAITING_RATIFICATION)
