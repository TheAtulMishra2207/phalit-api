# =================================================================
# Phalit.ai — Prashna Topic Engine (Phase 4A)
# =================================================================
# Registry-driven, declarative replacement for the bespoke
# vivaha_judgment / garbha_judgment procedural functions.
#
# Architecture (per Atul's Phase 4A clearance):
#   1. PRASHNA_TOPICS registry: declarative specs per sub-module
#   2. OVERLAY_REGISTRY: pure functions, one per overlay name
#   3. prashna_topic_judgment(): generic orchestrator
#   4. Three safeguards hard-coded:
#      (a) Sequential overlay execution — earlier overlays can rewrite
#          target/state before later overlays compute (e.g. lineage →
#          husband_pivot → sphuta-on-resolved-target).
#      (b) Centralized mutation safety via _apply_finding(): targets,
#          sincerity caps, and Bhava bonuses apply immediately; Bhava
#          *caps* are deferred to a final clamping pass.
#      (c) Verdict synthesis collects all influences then resolves with
#          a fixed priority hierarchy, independent of overlay order.
#
# This file does NOT replicate engine math. It composes existing
# utilities from prashna_engine.py into a parameterized framework.
# =================================================================

from typing import Dict, List, Optional, Any, Callable, Tuple
from copy import deepcopy

from prashna_engine import (
    SIGNS, SIGN_LORDS, SIGN_SANSKRIT,
    # Core compute layer
    compute_sincerity_score, compute_avasthas, compute_bhava_bala,
    karya_success_chain, compute_strength_scaling,
    detect_all_aspects, pairwise_aspect,
    # Tajik yogas
    detect_nakta, detect_abhara_yoga, detect_yama_yoga,
    detect_kamboola_yoga, detect_gada_yoga,
    # Garbha-specific math (Phase 3A)
    detect_eclipse_proximity,
    compute_beeja_sphuta, compute_kshetra_sphuta,
    detect_husband_pivot, detect_lineage_query,
    classify_garbha_intent,
    is_alpa_putra_sign, is_mars_5th_high_risk,
    is_heavily_combust, is_moon_void_of_course,
    # Diagnostic layer
    horary_to_natal_shift,
    detect_long_horizon_query,
    # Internal helpers
    _planet_house, _is_combust,
    is_yama_binder,
    # Constants
    GARBHA_LONG_HORIZON_EXTRAS,
    AVASTHA_AUSPICIOUSNESS,
)


# =================================================================
# PHASE 4D · INTENT ROUTING HELPERS (generic)
# =================================================================

# Putra sub-intent: child-development markers.
# Highest-priority signal that the query is about an EXISTING child's
# health/development/wellbeing, NOT about progeny capacity or family-size.
PUTRA_CHILD_DEV_KEYWORDS = (
    # Possessive references to an existing child
    'my child', 'my son', 'my daughter', 'my kid', 'my baby',
    'my children', 'our child', 'our son', 'our daughter', 'our kid',
    # Speech / verbal development
    'speech', 'speaking', 'talk ', 'talking', 'verbal', 'language ',
    'pronounce', 'pronunciation', 'stutter', 'speaking skills',
    # Cognitive / developmental
    'development', 'developmental', 'milestone', 'milestones',
    'cognition', 'cognitive', 'autism', 'autistic',
    'adhd', 'asperger', 'special needs', 'developmental delay',
    'iep', 'therapy', 'speech therapy', 'occupational therapy',
    # Education / learning (about an existing child)
    'school', 'studies', 'learning', 'study', 'grades',
    'tuition', 'academic',
    # Motor skills
    'walk', 'walking', 'crawl', 'crawling', 'motor skills',
    'fine motor', 'gross motor',
    # General wellbeing of a known child
    'health of my child', 'health of my son', 'health of my daughter',
    'recover', 'recovery', 'illness',
    # Generic developmental verbs in context
    'develop normal', 'develop normally', 'develop properly',
    'normal speech', 'normal development', 'on schedule',
)


# Putra · child_acute_illness route markers
PUTRA_CHILD_ILLNESS_KEYWORDS = (
    'my child sick', 'my son sick', 'my daughter sick',
    'my child ill', 'my son ill', 'my daughter ill',
    'fever', 'hospital', 'hospitalized', 'icu', 'admitted',
    'diagnosed', 'diagnosis', 'cancer', 'chronic',
    'will my child recover', 'will my son recover', 'will my daughter recover',
    'will my child get well', 'will my child be okay',
    "child's illness", "kid's illness", "son's illness", "daughter's illness",
    'serious illness',
)

# Putra · runaway_estranged_child route markers
PUTRA_RUNAWAY_KEYWORDS = (
    'my child ran away', 'son ran away', 'daughter ran away',
    'child is missing', 'son is missing', 'daughter is missing',
    'estranged child', 'estranged son', 'estranged daughter',
    'child left home', 'son left home', 'daughter left home',
    'no contact with my child', 'cut me off', 'cut us off',
    'when will my child return', 'when will my son return',
    'when will my daughter return', 'will my child come back',
    'will my son come back', 'will my daughter come back',
    'reconcile with my child', 'reconcile with my son',
    'reconcile with my daughter',
)

# Putra · legal_child_custody route markers
PUTRA_CUSTODY_KEYWORDS = (
    'custody', 'visitation', 'court', 'family court',
    'divorce custody', 'shared custody', 'sole custody',
    'will i get custody', 'will i win custody',
    'custody hearing', 'custody battle', 'custody case',
    'child support', 'parenting plan', 'guardian ad litem',
)


def classify_putra_intent(query_text: Optional[str]) -> str:
    """
    Classify a Putra query into one of:
      - 'child_acute_illness'       : query about a child's acute or chronic
                                       illness, hospitalization, recovery
      - 'runaway_estranged_child'   : query about a runaway/estranged child's
                                       return — an Aagaman (return) reading
      - 'legal_child_custody'       : query about custody disputes, hearings,
                                       visitation rights
      - 'child_development_health'  : query about an existing child's wellbeing,
                                       speech, education, milestones
      - 'progeny_capacity'          : default — capacity / family-size / conception
                                       horizon (the original Putra reading)

    Precedence (most specific first):
      illness → runaway → custody → child-dev → progeny-capacity.

    Per Prashna Marga Ch.16: when a child is already born and the query is
    about their state, the chart pivots — the 5th house becomes the child's
    Lagna, and we count houses from there for child-specific topics.
    """
    if not query_text:
        return 'progeny_capacity'
    q = ' ' + query_text.lower() + ' '

    # Most specific first — these are mutually exclusive intents.
    for marker in PUTRA_CHILD_ILLNESS_KEYWORDS:
        if marker in q:
            return 'child_acute_illness'
    for marker in PUTRA_RUNAWAY_KEYWORDS:
        if marker in q:
            return 'runaway_estranged_child'
    for marker in PUTRA_CUSTODY_KEYWORDS:
        if marker in q:
            return 'legal_child_custody'
    for marker in PUTRA_CHILD_DEV_KEYWORDS:
        if marker in q:
            return 'child_development_health'
    return 'progeny_capacity'


def _resolve_intent_route(spec: Dict, topic_id: str,
                          horizon_text: Optional[str],
                          inputs: Dict) -> Tuple[Dict, Optional[str]]:
    """
    Resolve a topic's intent-routed configuration into an effective spec.

    For topics that declare an 'intent_routing' sub-dict, classify the
    intent (from query text or explicit input) and overlay the route's
    fields (target_house, target_role, overlays, narrative_tone,
    secondary_karaka) on top of the base spec.

    Topics without intent_routing get back their original spec unchanged.

    Returns (effective_spec, classified_intent).
    """
    intent_routing = spec.get('intent_routing')
    if not intent_routing:
        return spec, None

    # 1. Classify intent — explicit input wins, else topic-specific classifier
    intent = inputs.get('intent')
    if not intent:
        if topic_id == 'putra':
            intent = classify_putra_intent(horizon_text)
        elif topic_id == 'garbha':
            intent = classify_garbha_intent(horizon_text)
        elif topic_id == 'karma':
            intent = classify_karma_intent(horizon_text)
        elif topic_id == 'sammana':
            # Sammana accepts an optional `recognition_scope` enum input
            # which is the authoritative signal (per Atul's Gap 5 lock);
            # falls back to keyword classification on horizon_text otherwise.
            intent = classify_sammana_intent(horizon_text,
                                              inputs.get('recognition_scope'))
        else:
            intent = spec.get('default_intent')

    # 2. Validate / fall back
    if intent not in intent_routing:
        intent = spec.get('default_intent') or next(iter(intent_routing))

    # 3. Layer route fields over the base spec
    route = intent_routing[intent]
    effective = dict(spec)
    for key in ('target_house', 'target_role', 'overlays',
                'narrative_tone', 'secondary_karaka'):
        if key in route:
            effective[key] = route[key]

    return effective, intent


# =================================================================
# PHASE 4D · KARMIKA CONTAINER · MATHEMATICAL GUARDRAILS
# =================================================================
# Per Atul's Step 1 Karmika & Yaatra clearance (3-guardrail spec):
#
#   Rule 1 — Corporate Master Pivot: resolved at intent-routing time.
#     For employer_relationship intent, target_house = 4 (10th-from-7th
#     = boss's throne). See karma topic registry intent_routing.
#
#   Rule 2 — Saturn/Mars functional transformation: implemented below
#     as apply_karmika_avastha_transformation(). Runs in the orchestrator
#     AFTER standard avastha computation but BEFORE the 4 Karma overlays,
#     so that overlays read the transformed labels.
#
#   Rule 3 — Velocity-aware timing + REVERSAL_AT_THE_BORDER: implemented
#     in prashna_engine.compute_phal_kaal (signed velocities) and the
#     _check_reversal_at_border helper. Surfaced via the standard/derived
#     vector return dict's verdict_modifier field.
# =================================================================

# Karmika sign sets for Saturn-Sthira test
_FIXED_SIGNS_INDICES = {1, 4, 7, 10}      # Taurus, Leo, Scorpio, Aquarius
_SATURN_OWN_SIGNS    = {9, 10}            # Capricorn, Aquarius

_KARMIKA_TOPICS = {'karma', 'sammana', 'pravasa'}


def apply_karmika_avastha_transformation(chart_data: Dict,
                                          avasthas: Dict[str, Dict]) -> Dict:
    """
    Karmika & Yaatra Rule 2 — Saturn/Mars functional transformation.

    Mutates the avasthas dict IN-PLACE when Karmika conditions are met
    (caller must pass a fresh avasthas dict or accept the mutation):

      • Saturn in 10th house AND in a Fixed sign (Taurus, Leo, Scorpio,
        Aquarius) OR in its own sign (Capricorn, Aquarius):
          → synthesis_label re-labeled "Standing Power (Sthira)"
          → outcome re-narrated as unshakeable corporate position
          → karmika_transformed flag added for downstream consumers

      • Mars in 10th house (regardless of affliction):
          → synthesis_label re-labeled "Executive Command (Mangala Digbala)"
          → outcome re-narrated as administrative authority
          → karmika_transformed flag added

    Returns a metadata dict describing which transformations fired,
    suitable for diagnostic display. Returns {'fired': []} if neither
    condition matched.

    This function is IDEMPOTENT — re-running it on an already-transformed
    avasthas dict has no additional effect (transformations have unique
    synthesis_label markers).
    """
    fired: List[Dict] = []

    # ── Saturn check ──
    saturn_data = (chart_data.get('planets') or {}).get('Saturn') or {}
    saturn_sign = saturn_data.get('sign_index')
    saturn_house = _planet_house(chart_data, 'Saturn')

    if (saturn_house == 10 and saturn_sign is not None
            and (saturn_sign in _FIXED_SIGNS_INDICES
                 or saturn_sign in _SATURN_OWN_SIGNS)):
        sign_name = SIGNS[saturn_sign] if 0 <= saturn_sign < 12 else f"sign #{saturn_sign}"
        is_own = saturn_sign in _SATURN_OWN_SIGNS
        is_fixed = saturn_sign in _FIXED_SIGNS_INDICES
        # Re-label
        prior = avasthas.get('Saturn', {})
        prior_label = prior.get('synthesis_label', 'Unspecified')
        avasthas['Saturn'] = {
            **prior,
            'synthesis_label': 'Standing Power (Sthira)',
            'karmika_transformed': True,
            'karmika_reason': (
                f"Saturn in 10th house in "
                f"{'own sign ' if is_own else ''}"
                f"{sign_name}"
                f"{' (Fixed)' if is_fixed and not is_own else ''}"
                f" — Karmakaraka triggers Sthira (immovable corporate position) "
                f"and bypasses the standard '{prior_label}' label."
            ),
            'karmika_prior_label': prior_label,
            'outcome': (
                'Unshakeable, highly resilient, slow-moving corporate position. '
                'Even when the chart shows friction elsewhere, Saturn here '
                'guarantees the tenure cannot be displaced by external pressure.'
            ),
        }
        fired.append({
            'planet': 'Saturn',
            'transformation': 'standing_power_sthira',
            'reason': avasthas['Saturn']['karmika_reason'],
            'prior_label': prior_label,
            'new_label': 'Standing Power (Sthira)',
        })

    # ── Mars check ──
    mars_data = (chart_data.get('planets') or {}).get('Mars') or {}
    mars_house = _planet_house(chart_data, 'Mars')
    mars_sign = mars_data.get('sign_index')

    if mars_house == 10:
        sign_name = SIGNS[mars_sign] if (mars_sign is not None
                                          and 0 <= mars_sign < 12) else 'unknown sign'
        prior = avasthas.get('Mars', {})
        prior_label = prior.get('synthesis_label', 'Unspecified')
        avasthas['Mars'] = {
            **prior,
            'synthesis_label': 'Executive Command (Mangala Digbala)',
            'karmika_transformed': True,
            'karmika_reason': (
                f"Mars in 10th house in {sign_name} — absolute Digbala "
                f"(directional strength) in the throne. Triggers executive "
                f"command overlay regardless of affliction, overriding the "
                f"standard '{prior_label}' label."
            ),
            'karmika_prior_label': prior_label,
            'outcome': (
                'Administrative command authority. Even with afflicting aspects, '
                'Mars here grants the native a decisive hand in operations — '
                'the chart confers the right to execute, not merely participate.'
            ),
        }
        fired.append({
            'planet': 'Mars',
            'transformation': 'executive_command_digbala',
            'reason': avasthas['Mars']['karmika_reason'],
            'prior_label': prior_label,
            'new_label': 'Executive Command (Mangala Digbala)',
        })

    return {'fired': fired, 'count': len(fired)}


# =================================================================
# PHASE 4D · KARMA INTENT CLASSIFIER (4 routes)
# =================================================================
# Precedence (most specific → least specific):
#   1. exit_resignation       — termination/severance language
#   2. career_pivot_startup   — leaving corporate, building business
#   3. employer_relationship  — about a specific authority figure
#   4. promotion_elevation    — default (raise, title, scale)
#
# Atul's Ch 13 keyword anchors (Part 2.2):
#   promotion_elevation:    promotion, raise, title change, scale up
#   employer_relationship:  boss, CEO, board, management, reporting
#   career_pivot_startup:   quit job, start business, equity, founder
#   exit_resignation:       fire me, laid off, resign, severance, leave
# =================================================================

_KARMA_EXIT_KEYWORDS = (
    'fire me', 'fired', 'firing', 'getting fired',
    'laid off', 'lay off', 'layoff', 'redundant', 'redundancy',
    'resign', 'resignation', 'resigning',
    'severance', 'severence',
    'leave the job', 'leave the company', 'leave my job', 'quit and leave',
    'forced exit', 'forced out', 'asked to leave',
    'terminated', 'termination',
    'exit the company', 'leaving employer',
    'भीतर से निकाल', 'बर्खास्त', 'इस्तीफा', 'त्यागपत्र',
)

_KARMA_STARTUP_KEYWORDS = (
    'start business', 'start a business', 'starting business', 'start my business',
    'start up', 'startup', 'launch startup', 'launch a startup',
    'quit job', 'quit my job', 'leave job to start', 'leave corporate',
    'become founder', 'as a founder', 'become entrepreneur',
    'co-founder', 'cofounder',
    'equity stake', 'take equity', 'equity offer',
    'build my own', 'start my own', 'own venture', 'own company',
    'go independent', 'go solo', 'consulting practice',
    'व्यवसाय शुरू', 'अपना काम', 'फाउंडर',
)

_KARMA_EMPLOYER_KEYWORDS = (
    'boss', 'my boss', 'the boss',
    'ceo', 'my ceo', 'the ceo',
    'manager', 'my manager', 'reporting manager',
    'board', 'the board', 'board of directors',
    'management', 'senior management', 'leadership team',
    'supervisor', 'my supervisor',
    'vc ', ' vc', 'venture capital', 'venture capitalist',
    'investor approval', 'investor sign',
    'will my boss', 'will my ceo', 'will the boss', 'will the ceo',
    'will management', 'will the board',
    'reporting line', 'reporting structure',
    'approve my', 'approving my', 'sign off on', 'green light',
    'मालिक', 'बॉस', 'सीईओ',
)

_KARMA_PROMOTION_KEYWORDS = (
    'promotion', 'promoted', 'get promoted', 'getting promoted',
    'raise', 'pay raise', 'salary raise', 'salary hike', 'hike',
    'title change', 'new title', 'title bump', 'promoted to',
    'scale up', 'scale my role', 'expand my role',
    'next level', 'senior role', 'senior position',
    'elevation', 'elevate', 'step up',
    'designation change', 'better designation',
    'पदोन्नति', 'तरक्की', 'प्रमोशन', 'वेतन वृद्धि',
)

# Aspiration-override phrases. These intercept role keywords ('ceo', 'manager',
# 'executive', 'director') that ALSO appear in _KARMA_EMPLOYER_KEYWORDS but
# here describe a role the QUERENT is asking about BECOMING (not about their
# boss). Checked between STARTUP and EMPLOYER in classify_karma_intent so that
# "Will I become a top 100 CEO?" routes to promotion_elevation, not to
# employer_relationship via the bare 'ceo' substring match.
_KARMA_PROMOTION_ASPIRATION_OVERRIDES = (
    # Aspirational verbs + role nouns
    'become a ceo', 'become ceo', 'becoming a ceo', 'becoming ceo',
    'be a ceo', 'be ceo', 'being a ceo', 'being ceo',
    'become an executive', 'be an executive',
    'become a manager', 'be a manager',
    'become a director', 'be a director',
    'become president', 'be president',
    "i'll be a ceo", 'i will be a ceo', 'i will become a ceo',
    'i want to be a ceo', 'i want to become a ceo',
    # Ranking / aspirational tier
    'top ceo', 'top 10', 'top ten', 'top 100', 'top hundred',
    'one of the top', 'as a ceo', 'as ceo',
    'future ceo', 'aspiring ceo',
    'ceos in india', 'ceo in india',
    # Climb / reach metaphors
    'reach the top', 'rise to the top', 'climb to the top',
    'will i be', 'will i become', 'will i make it',
    # Devanagari
    'सीईओ बन', 'मैनेजर बन', 'शीर्ष पर', 'शीर्ष',
)


def classify_karma_intent(query_text: Optional[str]) -> str:
    """
    Classify a Karma query into one of 4 sub-intents.

    Precedence (highest → lowest priority):
        1. exit_resignation
        2. career_pivot_startup
        2b. aspiration_override → promotion_elevation
            (intercepts before EMPLOYER consumes 'ceo'/'manager'/etc when the
             querent is asking about BECOMING that role, not about their boss)
        3. employer_relationship
        4. promotion_elevation  (default)

    Returns one of the 4 intent strings.
    """
    q = (query_text or '').lower()

    # 1. EXIT — highest priority; if user mentions firing/severance, route here
    if any(kw in q for kw in _KARMA_EXIT_KEYWORDS):
        return 'exit_resignation'

    # 2. STARTUP — second priority; founder/equity/quit-to-start
    if any(kw in q for kw in _KARMA_STARTUP_KEYWORDS):
        return 'career_pivot_startup'

    # 2b. ASPIRATION OVERRIDE — intercepts EMPLOYER keyword matches when the
    #     querent is asking about BECOMING a CEO/manager/exec/director rather
    #     than about THEIR boss who holds that role. Without this, "Will I
    #     become a top 100 CEO?" hits the bare 'ceo' substring and misroutes.
    if any(kw in q for kw in _KARMA_PROMOTION_ASPIRATION_OVERRIDES):
        return 'promotion_elevation'

    # 3. EMPLOYER — third priority; specific authority figure or approval
    if any(kw in q for kw in _KARMA_EMPLOYER_KEYWORDS):
        return 'employer_relationship'

    # 4. PROMOTION — default for "promotion / raise / scale" or generic Karma
    return 'promotion_elevation'


# =================================================================
# PRASHNA_TOPICS REGISTRY

# =================================================================
# Each topic declares:
#   - container:        Phase-4 UI hub (vaivahika | karmika_yaatra | arthika |
#                                       aarogya | yuddha)
#   - target_house:     primary house under analysis (can be rewritten by
#                       overlays returning target_override)
#   - target_role:      human-readable target description for UI/narrative
#   - required_inputs:  list of input keys the frontend must provide
#   - optional_inputs:  list of input keys the frontend may provide
#   - sincerity_mode:   'standard' or 'garbha' (enables Garbha-specific
#                       deltas + eclipse cap in compute_sincerity_score)
#   - long_horizon_extras: if True, append topic-specific long-horizon
#                          keywords (Garbha appends "ever conceive" etc.)
#   - overlays:         ordered list of overlay names — sequence matters
#                       since earlier overlays can mutate state
#   - verdict_states:   allowed terminal verdict states for this topic
#   - verdict_modifiers: allowed orthogonal modifier flags
#   - narrative_tone:   AI prompt selector
# =================================================================

PRASHNA_TOPICS: Dict[str, Dict] = {

    'vivaha': {
        'container':            'vaivahika',
        'display_name':         'Vivaha · Marriage',
        'sanskrit_name':        'विवाह',
        'target_house':         7,
        'target_role':          '7th — Yuvati Bhava (Partner)',
        'required_inputs':      [],
        'optional_inputs':      ['natal_lagna_sign', 'full_query'],
        'sincerity_mode':       'standard',
        'long_horizon_extras':  False,
        # Per Atul's Phase 4D spec: sincerity_option_c declares the BPHS audit
        # standard; nakta_abhara_scan handles the core Tajik connection scan.
        # third_party_interference + emotional_reciprocity preserve the legacy
        # vivaha_judgment output shape (Ch 9 readings) — kept for equivalence
        # gate parity; can be moved into a "Vivaha+" tier in a future pass.
        'overlays': [
            'sincerity_option_c',
            'nakta_abhara_scan',
            'third_party_interference',
            'emotional_reciprocity',
        ],
        'verdict_states':       ['YES', 'YES_WITH_DELAYS', 'CONDITIONAL', 'NO'],
        'verdict_modifiers':    [],
        'narrative_tone':       'dignified',
    },

    'garbha': {
        'container':            'vaivahika',
        'display_name':         'Garbha · Conception',
        'sanskrit_name':        'गर्भ',
        'target_house':         5,
        'target_role':          '5th — Putra Bhava (Progeny)',
        'required_inputs':      ['querent_gender'],
        'optional_inputs':      ['intent', 'natal_lagna_sign', 'full_query'],
        'sincerity_mode':       'garbha',
        'long_horizon_extras':  True,
        'overlays': [
            # — Phase 1: target resolution (must run first)
            'lineage_query_check',      # → 9th house if lineage keyword
            'husband_pivot_auto',       # → 11th house if male+partner query
            # — Phase 2: structural reads against resolved target
            'beeja_kshetra_sphuta',     # gender-specific Sphuta bonus/cap
            'nakta_abhara_scan',        # bridges + blockers on resolved L1-L_target
            'kamboola_yoga',            # Moon-proxy verdict substitution
            'gada_yoga',                # 12-month structural compression
            'mars_5_vitality_split',    # HIGH_RISK promotion (rulership-based)
            'rahu_ketu_progeny_axis',   # IVF / adoption modern signals
            'sterile_sign_downgrade',   # Alpa-Putra cusp downgrade
            # — Phase 3: sincerity + modifiers (last)
            'eclipse_proximity_axis',   # sincerity hard-cap at 45
            'inconclusive_check',       # current-pregnancy void Moon / heavy combust
        ],
        'verdict_states':       ['YES', 'YES_WITH_DELAYS', 'CONDITIONAL_MEDICAL',
                                 'CONDITIONAL_THIRD_PARTY', 'HIGH_RISK', 'NO'],
        'verdict_modifiers':    ['INCONCLUSIVE_RECAST_REQUIRED'],
        'narrative_tone':       'tender',
    },

    # Future topics register here. Sample shells (commented out until built):
    #
    # 'karma':         { 'container': 'karmika',   'target_house': 10, ... },
    # 'shatru':        { 'container': 'yuddha',    'target_house': 6,
    #                    'required_inputs': ['enemy_name'], ... },
    # 'dhana':         { 'container': 'arthika',   'target_house': 2, ... },
    # 'roga':          { 'container': 'aarogya',   'target_house': 6, ... },

    # =================================================================
    # Phase 4D · Putra (Progeny + Child Development & Health)
    # =================================================================
    # INTENT-ROUTED. Two routes:
    #
    #   progeny_capacity (default) — long-horizon family-size reading via
    #     5th house, 5L, Jupiter (Putra Karaka), and the Saptamsha (D7).
    #     Reflective tone. Never predicts exact child counts.
    #
    #   child_development_health  — query about an EXISTING child's
    #     speech, cognition, wellbeing, or milestones. Per Prashna Marga
    #     Ch.16, the 5th house BECOMES the child's Lagna; speech reads
    #     from 2nd-of-5th = 6th of the radix. Mercury (Vak-karaka)
    #     replaces Jupiter (Putra Karaka). Clinical-empathetic tone —
    #     diagnostic and parent-focused, no fertility/family-size talk.
    'putra': {
        'container':            'vaivahika',
        'display_name':         'Putra · Progeny',
        'sanskrit_name':        'पुत्र',
        'required_inputs':      [],
        'optional_inputs':      ['natal_lagna_sign', 'full_query', 'intent'],
        'sincerity_mode':       'standard',
        'long_horizon_extras':  True,
        'verdict_states':       ['YES', 'YES_WITH_DELAYS', 'CONDITIONAL', 'NO'],
        'verdict_modifiers':    [],
        # Default fields (used when intent_routing falls through, or by
        # legacy callers that don't trigger intent classification)
        'target_house':         5,
        'target_role':          '5th — Putra Bhava (Long-Horizon Progeny)',
        'overlays': [
            'sincerity_option_c',
            'putra_yoga_catalogue',
            'saptamsha_varga_anchor',
        ],
        'narrative_tone':       'reflective',
        'default_intent':       'progeny_capacity',
        'intent_routing': {
            'progeny_capacity': {
                'target_house':       5,
                'target_role':        '5th — Putra Bhava (Long-Horizon Progeny)',
                'secondary_karaka':   'Jupiter',
                'overlays': [
                    'sincerity_option_c',
                    'putra_yoga_catalogue',
                    'saptamsha_varga_anchor',
                ],
                'narrative_tone':     'reflective',
            },
            'child_development_health': {
                # 6th of radix = 2nd from 5th (speech house of the child).
                # The 5th house is the child themselves; we read from there.
                'target_house':       6,
                'target_role':        '6th — Vak Bhava of the Child (2nd from 5th)',
                'secondary_karaka':   'Mercury',
                'overlays': [
                    'sincerity_option_c',
                    'child_wellbeing_scan',
                    'mercury_speech_affliction_check',
                ],
                'narrative_tone':     'clinical_empathetic',
            },
            'child_acute_illness': {
                # 10th of radix = 6th from 5th = child's illness.
                'target_house':       10,
                'target_role':        '10th — Roga Bhava of the Child (6th from 5th)',
                'secondary_karaka':   'Moon',  # Karaka of vitality
                'overlays': [
                    'sincerity_option_c',
                    'child_wellbeing_scan',
                    'child_illness_scan',
                ],
                'narrative_tone':     'clinical_protective',
            },
            'runaway_estranged_child': {
                # 8th of radix = 4th from 5th = the child's home/stability.
                'target_house':       8,
                'target_role':        '8th — Bandhu Bhava of the Child (4th from 5th)',
                'secondary_karaka':   'Mercury',  # Karaka of communication/return
                'overlays': [
                    'sincerity_option_c',
                    'runaway_aagaman_check',
                    'child_wellbeing_scan',
                ],
                'narrative_tone':     'crisis_supportive',
            },
            'legal_child_custody': {
                # Target stays at 5th (the child themselves) but the overlay
                # runs the competitive Ithasala between L1 ↔ L5 and L7 ↔ L5.
                'target_house':       5,
                'target_role':        '5th — Putra Bhava (custody / parental claim)',
                'secondary_karaka':   'Jupiter',
                'overlays': [
                    'sincerity_option_c',
                    'custody_ithasala_competition',
                    'child_wellbeing_scan',
                ],
                'narrative_tone':     'tactical_legal',
            },
        },
    },

    # =================================================================
    # Phase 4D · Anya-Sambandha (Unconventional / Hidden Alliances)
    # =================================================================
    # Pivots dynamically: 7th house default; 12th for hidden contexts;
    # Rahu-Ketu activation on 5/11 or 1/7. Circumspect tone — clinical
    # distance, no moralising.
    'anya_sambandha': {
        'container':            'vaivahika',
        'display_name':         'Anya-Sambandha · Unconventional Alliances',
        'sanskrit_name':        'अन्य-सम्बन्ध',
        'target_house':         7,
        'target_role':          '7th — Yuvati Bhava (with 12th-house pivots)',
        'required_inputs':      [],
        'optional_inputs':      ['natal_lagna_sign', 'full_query'],
        'sincerity_mode':       'standard',
        'long_horizon_extras':  False,
        'overlays': [
            'sincerity_option_c',
            'secret_aspect_scan',     # NEW · Phase 4D
            'node_axis_activation',   # NEW · Phase 4D
            'nakta_abhara_scan',
        ],
        'verdict_states':       ['YES', 'YES_WITH_DELAYS', 'CONDITIONAL', 'NO'],
        'verdict_modifiers':    [],
        'narrative_tone':       'circumspect',
    },

    # =================================================================
    # Phase 4D · Kinship & Alliances (Siblings + Networks)
    # =================================================================
    # Dual-target: 3rd house (siblings) AND 11th house (networks).
    # Aggregates legacy Sahaja + Mitra chapters. Pragmatic tone.
    'kinship': {
        'container':            'vaivahika',
        'display_name':         'Kinship & Alliances · Sahaja + Mitra',
        'sanskrit_name':        'सहज-मित्र',
        'target_house':         3,   # primary; 11 handled in overlays
        'secondary_house':      11,  # used by overlays
        'target_role':          '3rd / 11th — Sahaja Bhava + Labha Bhava',
        'required_inputs':      [],
        'optional_inputs':      ['natal_lagna_sign', 'full_query'],
        'sincerity_mode':       'standard',
        'long_horizon_extras':  False,
        'overlays': [
            'sincerity_option_c',
            'alliance_reciprocity_check',  # NEW · Phase 4D
            'nakta_bridge_relay',          # NEW · Phase 4D
        ],
        'verdict_states':       ['YES', 'YES_WITH_DELAYS', 'CONDITIONAL', 'NO'],
        'verdict_modifiers':    [],
        'narrative_tone':       'pragmatic',
    },

    # =================================================================
    # Phase 4D · Karmika & Yaatra · Karma (Ch 13)
    # =================================================================
    # Career, Authority, Rulership. 4 intent routes per Atul's Part 2.2
    # mapping. Saturn/Mars functional transformation (Rule 2) is applied
    # at the orchestrator level before overlays run, so overlays read
    # transformed avastha labels via state['avasthas'].
    #
    # verdict_remap: re-codes the default verdict vocabulary into the
    # Karmika container vocabulary (YES_WITH_DELAYS → YES_WITH_EFFORT,
    # CONDITIONAL → CONDITIONAL_SUBORDINATE). Applied in _synthesize_verdict
    # after primitive resolution.
    'karma': {
        'container':            'karmika_yaatra',
        'display_name':         'Karma · Career & Authority',
        'sanskrit_name':        'कर्म',
        'required_inputs':      [],
        'optional_inputs':      ['natal_lagna_sign', 'full_query', 'intent'],
        'sincerity_mode':       'standard',
        'long_horizon_extras':  False,
        'karmika_avastha_transform': True,   # signals orchestrator hook
        'verdict_states': [
            'YES', 'YES_WITH_EFFORT',
            'CONDITIONAL_SUBORDINATE',
            'ABDICATION_SIGNAL',
            'NO',
        ],
        'verdict_modifiers': ['FOUNDER_TRANSITION', 'REVERSAL_AT_THE_BORDER', 'THRONE_OCCLUDED'],
        'verdict_remap': {
            'YES_WITH_DELAYS':       'YES_WITH_EFFORT',
            'CONDITIONAL':           'CONDITIONAL_SUBORDINATE',
            'CONDITIONAL_MEDICAL':   'CONDITIONAL_SUBORDINATE',
            'CONDITIONAL_THIRD_PARTY': 'CONDITIONAL_SUBORDINATE',
        },
        # Default fields (used when no intent classified, e.g. test harness)
        'target_house':         10,
        'target_role':          '10th — Karma Bhava (Sovereign Throne)',
        'overlays': [
            'sincerity_option_c',
            'rulership_confirmed',
            'subordinate_trajectory',
            'abdication_signal',
            'mushita_sovereignty',
        ],
        'narrative_tone':       'executive_strategic',
        'default_intent':       'promotion_elevation',
        'intent_routing': {
            'promotion_elevation': {
                # Standard upward trajectory query — target H10 directly
                'target_house':       10,
                'target_role':        '10th — Karma Bhava (Sovereign Throne)',
                'secondary_karaka':   'Sun',   # Status karaka; Jupiter checked supplementally
                'overlays': [
                    'sincerity_option_c',
                    'rulership_confirmed',
                    'subordinate_trajectory',
                    'abdication_signal',
                    'mushita_sovereignty',
                ],
                'narrative_tone':     'executive_strategic',
            },
            'employer_relationship': {
                # Rule 1 — Corporate Master Pivot. Target is the boss as a PERSON
                # (7th from your Lagna), but the action/approval we read on is
                # 10th-from-7th = H4 of the Prashna chart. We set target_house
                # to 4 so the orchestrator builds Karya + Bhava Bala on that
                # axis — that's where the boss's institutional authority lives.
                'target_house':       4,
                'target_role':        ("4th — Employer's Throne "
                                        "(10th-from-7th · Corporate Master Pivot)"),
                'secondary_karaka':   'Mercury',  # Dialogue/messaging karaka
                'overlays': [
                    'sincerity_option_c',
                    'rulership_confirmed',
                    'subordinate_trajectory',
                    'abdication_signal',
                ],
                'narrative_tone':     'executive_strategic',
            },
            'career_pivot_startup': {
                # Target H7 (the business axis as the querent's new identity).
                # Overlay D (startup_pivot_crosscheck) does the L7-vs-L10
                # competition and the L11 (gains) cross-check.
                'target_house':       7,
                'target_role':        '7th — Vyapara Axis (Business Identity)',
                'secondary_karaka':   'Mars',   # Risk/execution karaka
                'overlays': [
                    'sincerity_option_c',
                    'startup_pivot_crosscheck',
                    'rulership_confirmed',
                ],
                'narrative_tone':     'executive_strategic',
            },
            'exit_resignation': {
                # Target H12 — the house of severance, loss, and dissolution
                # of the current role. Overlay C (abdication_signal) handles
                # the forced-exit logic; subordinate_trajectory catches
                # softer "stuck" readings.
                'target_house':       12,
                'target_role':        '12th — Vyaya Bhava (Severance Axis)',
                'secondary_karaka':   'Saturn',  # Termination/longevity karaka
                'overlays': [
                    'sincerity_option_c',
                    'abdication_signal',
                    'subordinate_trajectory',
                ],
                'narrative_tone':     'executive_strategic',
            },
        },
    },

    # =================================================================
    # SAMMANA · Recognition & Honour (Ch 14)
    # Container: Karmika & Yaatra · second of 3 sub-modules
    # =================================================================
    'sammana': {
        'display_name': 'Sammana · Recognition & Honour',
        'container':    'karmika_yaatra',
        'sanskrit_name': 'सम्मान',
        'description': (
            'Reputation, formal accolades, peer/public validation, internal '
            'recognition, and the materialization (or theft) of credit. '
            'Read on H11 (Labha — public reception) or H10 (Karma — vertical '
            'standing), with Jupiter and Sun as karakas.'
        ),
        'required_inputs':      [],  # recognition_scope optional; classifier handles absence
        'verdict_states': [
            'YES', 'YES_WITH_FRICTION', 'CONDITIONAL_PRIVY',
            'OBSCURED_VALIDATION', 'NO',
        ],
        'verdict_modifiers': [
            'PUBLIC_COMMENDATION',  # L3↔L11 Ithesal (Overlay E)
            'MUTED_RECEPTION',      # L3↔L11 Esrapha (Overlay E)
        ],
        # Map default-vocabulary primitives into Sammana's vocabulary
        'verdict_remap': {
            'YES_WITH_DELAYS':         'YES_WITH_FRICTION',
            'CONDITIONAL':             'CONDITIONAL_PRIVY',
            'CONDITIONAL_MEDICAL':     'CONDITIONAL_PRIVY',
            'CONDITIONAL_THIRD_PARTY': 'CONDITIONAL_PRIVY',
        },

        # Default fields (used when no intent classified)
        'target_house':         11,
        'target_role':          '11th — Labha Bhava (Public Reception)',
        'overlays': [
            'sincerity_option_c',
            'accolade_materialization',
            'peer_envy_scan',
            'peer_recognition_axis',
            'executive_privy_lock',
            'credit_theft_check',
        ],
        'narrative_tone':       'executive_strategic',
        'default_intent':       'industry_award',

        'intent_routing': {
            'industry_award': {
                # External / peer / industry recognition — target H11, Jupiter karaka
                'target_house':       11,
                'target_role':        '11th — Labha Bhava (Public Reception)',
                'secondary_karaka':   'Jupiter',  # Honor karaka
                'overlays': [
                    'sincerity_option_c',
                    'accolade_materialization',   # Overlay A — YES generator
                    'peer_envy_scan',             # Overlay C — YES_WITH_FRICTION
                    'peer_recognition_axis',      # Overlay E — modifier flag
                    'executive_privy_lock',       # Overlay F — CONDITIONAL_PRIVY
                    'credit_theft_check',         # Overlay B — OBSCURED_VALIDATION
                ],
                'narrative_tone':     'executive_strategic',
            },
            'internal_validation': {
                # Internal / executive / board recognition — target H10, Sun karaka
                'target_house':       10,
                'target_role':        '10th — Karma Bhava (Vertical Standing)',
                'secondary_karaka':   'Sun',      # Radiance karaka
                'overlays': [
                    'sincerity_option_c',
                    'kendra_solar_radiance',      # Overlay D — YES generator
                    'credit_theft_check',         # Overlay B — OBSCURED_VALIDATION
                    'peer_envy_scan',             # Overlay C — YES_WITH_FRICTION
                    'executive_privy_lock',       # Overlay F — CONDITIONAL_PRIVY
                    'peer_recognition_axis',      # Overlay E — modifier flag
                ],
                'narrative_tone':     'executive_strategic',
            },
        },
    },
}


# =================================================================
# OVERLAY CONTRACT
# =================================================================
# def overlay(chart: Dict, state: Dict, inputs: Dict) -> Dict
#
# Return a "finding" dict. Possible keys (all optional except 'overlay'):
#
#   overlay              : str   — the overlay's registered name
#   fired                : bool  — whether this overlay produced any effect
#   data                 : Dict  — passthrough payload for frontend/AI
#   narrative            : str   — human-readable description
#   frontend_card_id     : str   — which UI card to surface (None = no card)
#
#   # Mutations — applied by orchestrator
#   target_override      : Dict or None   — {'house': int, 'role': str}
#   sincerity_modifier   : Dict or None   — {'cap': int, 'reason': str}
#   bhava_bonus          : Dict or None   — {'house': int, 'pct': int}
#   bhava_cap            : Dict or None   — {'house': int, 'pct': int}
#   verdict_substitution : Dict or None   — overrides primitive failure
#   verdict_promotion_to : Dict or None   — promotes to higher-severity state
#   verdict_downgrade    : Dict or None   — gentle downgrade (YES→YES_WITH_DELAYS)
#   verdict_modifier_flag: str or None    — orthogonal modifier (INCONCLUSIVE etc.)
#
# Overlays are PURE: they read state, return a finding, and must not
# mutate state directly. The orchestrator applies findings deterministically.
# =================================================================


def _empty_finding(name: str) -> Dict:
    """Standard 'did not fire' finding shape."""
    return {'overlay': name, 'fired': False}


# -----------------------------------------------------------------
def overlay_sincerity_option_c(chart: Dict, state: Dict, inputs: Dict) -> Dict:
    """
    Declarative overlay confirming the topic uses BPHS Option-C sincerity audit
    (audit-r2 scoring). Surfaces the already-computed sincerity from state into
    overlay_findings for downstream UI/narrative consumption.

    The sincerity scoring itself runs in the orchestrator's base layer before
    overlays execute. This overlay merely exposes it under a stable key.
    """
    sincerity = state.get('sincerity') or {}
    return {
        'overlay': 'sincerity_option_c',
        'fired': bool(sincerity.get('triggers_insincere') or sincerity.get('score', 100) < 100),
        'data': {
            'sincerity_score':         sincerity.get('score'),
            'sincerity_band':          sincerity.get('band'),
            'sincerity_triggers':      sincerity.get('triggers_insincere'),
            'sincerity_audit_version': 'option_c',
        },
        'narrative': ('Sincerity audit (Option C / audit-r2) applied — '
                      'measures the querent\'s motivation strength at the moment of casting.'),
    }


# OVERLAY: lineage_query_check
# Garbha-specific. If the question contains lineage keywords
# (lineage / heir / vansha / dynasty / family line / bloodline),
# rewrite target → 9th house (Dharma / heir axis).
# Must run before husband_pivot_auto (lineage priority wins).
# -----------------------------------------------------------------

def overlay_lineage_query_check(chart: Dict, state: Dict, inputs: Dict) -> Dict:
    full_query = inputs.get('full_query') or ''
    is_lineage = detect_lineage_query(full_query)
    if not is_lineage:
        return _empty_finding('lineage_query_check')

    return {
        'overlay': 'lineage_query_check',
        'fired': True,
        'data': {'is_lineage': True},
        'target_override': {
            'house': 9,
            'role': '9th — Dharma Bhava (lineage / heir axis)',
            'reason': 'Lineage keyword detected — Dharma axis activated.',
        },
        'narrative': ('The question concerns the family line itself, not just a '
                      'single conception. The chart is rotated to read the 9th '
                      'house (Dharma — lineage and heritage).'),
        'frontend_card_id': None,
    }


# -----------------------------------------------------------------
# OVERLAY: husband_pivot_auto
# Garbha-specific. If male querent asks about partner's conception
# (or query contains husband-pivot phrasing), rewrite target → 11th
# (5th from 7th). Self-pregnancy phrasing blocks the pivot.
# Must run AFTER lineage_query_check (lineage wins priority).
# -----------------------------------------------------------------

def overlay_husband_pivot_auto(chart: Dict, state: Dict, inputs: Dict) -> Dict:
    # Don't pivot if lineage already rewrote target
    if state['target']['house'] == 9:
        return _empty_finding('husband_pivot_auto')

    full_query = inputs.get('full_query') or ''
    gender = inputs.get('querent_gender')

    is_pivot = detect_husband_pivot(full_query, gender)
    if not is_pivot:
        return _empty_finding('husband_pivot_auto')

    return {
        'overlay': 'husband_pivot_auto',
        'fired': True,
        'data': {'is_husband_pivot': True},
        'target_override': {
            'house': 11,
            'role': "11th (5th-from-7th) — wife's progeny zone",
            'reason': 'Male querent + partner-conception query → rotate to wife\'s 5th.',
        },
        'narrative': ('The querent is the husband, asking about his partner\'s '
                      'conception. The chart is rotated to read the 11th '
                      '(which is the 5th house counted from the 7th, the '
                      'partner\'s Lagna).'),
        'frontend_card_id': None,
    }


# -----------------------------------------------------------------
# OVERLAY: beeja_kshetra_sphuta
# Garbha-specific. Compute gender-relevant Sphuta:
#   - male querent   → Beeja Sphuta (Sun + Venus + Jupiter)
#   - female querent → Kshetra Sphuta (Jupiter + Moon + Mars)
# Then:
#   - If Sphuta sign matches gender parity → +15% Bhava Bala on target
#   - If Sphuta sign is Alpa-Putra (Gem/Leo/Vir/Sco) → 50% cap on target
# -----------------------------------------------------------------

def overlay_beeja_kshetra_sphuta(chart: Dict, state: Dict, inputs: Dict) -> Dict:
    gender = inputs.get('querent_gender')
    planets = chart.get('planets', {})

    beeja = compute_beeja_sphuta(planets)
    kshetra = compute_kshetra_sphuta(planets)

    if gender == 'male' and 'error' not in beeja:
        sphuta_active = beeja
        sphuta_sign = beeja['sign_index']
        gender_match = ((sphuta_sign + 1) % 2 == 1)  # masculine = 1-based odd
        gender_label = 'masculine'
    elif gender == 'female' and 'error' not in kshetra:
        sphuta_active = kshetra
        sphuta_sign = kshetra['sign_index']
        gender_match = ((sphuta_sign + 1) % 2 == 0)  # feminine = 1-based even
        gender_label = 'feminine'
    else:
        return {
            'overlay': 'beeja_kshetra_sphuta',
            'fired': False,
            'data': {'beeja': beeja, 'kshetra': kshetra,
                     'sphuta_active': None, 'sphuta_effect': None},
        }

    target_house = state['target']['house']

    # Sphuta in Alpa-Putra sign → cap
    if is_alpa_putra_sign(sphuta_sign):
        return {
            'overlay': 'beeja_kshetra_sphuta',
            'fired': True,
            'data': {
                'beeja': beeja, 'kshetra': kshetra,
                'sphuta_active': sphuta_active,
                'sphuta_effect': {
                    'type': 'cap_50',
                    'narrative': (
                        f"{sphuta_active['sphuta_type'].title()} Sphuta lands in "
                        f"{SIGNS[sphuta_sign]} (Alpa-Putra sterile sign) — "
                        f"Bhava Bala hard-capped at 50%, forcing verdict toward "
                        "delays or medical intervention."
                    ),
                },
            },
            'bhava_cap': {
                'house': target_house,
                'pct': 50,
                'reason': f'Sphuta in sterile sign {SIGNS[sphuta_sign]}',
            },
            'narrative': (
                f"The fertility coordinate lands in {SIGNS[sphuta_sign]}, "
                "a classical low-fertility sign — physiological friction at "
                "the cellular level."
            ),
        }

    # Sphuta matches gender parity → +15% bonus
    if gender_match:
        return {
            'overlay': 'beeja_kshetra_sphuta',
            'fired': True,
            'data': {
                'beeja': beeja, 'kshetra': kshetra,
                'sphuta_active': sphuta_active,
                'sphuta_effect': {
                    'type': 'bonus_15',
                    'narrative': (
                        f"{sphuta_active['sphuta_type'].title()} Sphuta lands in "
                        f"{SIGNS[sphuta_sign]} ({gender_label} sign for "
                        f"{gender} querent) — +15% Bhava Bala bonus."
                    ),
                },
            },
            'bhava_bonus': {
                'house': target_house,
                'pct': 15,
                'reason': f'Sphuta in {gender_label} sign {SIGNS[sphuta_sign]}',
            },
            'narrative': (
                f"The fertility coordinate lands in {SIGNS[sphuta_sign]}, a "
                f"{gender_label} sign aligned with the querent's gender — "
                "the body's cellular configuration favours conception."
            ),
        }

    # Neutral — Sphuta neither sterile nor parity-aligned
    return {
        'overlay': 'beeja_kshetra_sphuta',
        'fired': True,
        'data': {
            'beeja': beeja, 'kshetra': kshetra,
            'sphuta_active': sphuta_active,
            'sphuta_effect': {'type': 'neutral', 'narrative': 'Sphuta neutral.'},
        },
        'narrative': ('The fertility coordinate is neutral — no bonus or cap '
                      'on the progeny axis from the Sphuta layer.'),
    }


# -----------------------------------------------------------------
# OVERLAY: nakta_abhara_scan
# Shared. Detect:
#   - Nakta bridge (third-planet relay between L1 and L_target)
#   - Abhara Yoga (malefic interference on the direct link)
#   - Yama Yoga (midpoint binder when no direct aspect)
# These influence verdict synthesis (Nakta = CONDITIONAL_THIRD_PARTY,
# Abhara = YES→YES_WITH_DELAYS).
# -----------------------------------------------------------------

def overlay_nakta_abhara_scan(chart: Dict, state: Dict, inputs: Dict) -> Dict:
    lagna_sign = chart.get('lagna_sign', 0)
    lagna_lord = SIGN_LORDS[lagna_sign]
    target_house = state['target']['house']
    target_sign = (lagna_sign + target_house - 1) % 12
    target_lord = SIGN_LORDS[target_sign]

    nakta = detect_nakta(lagna_lord, target_lord, chart)
    abhara = detect_abhara_yoga(lagna_lord, target_lord, chart)
    yama = detect_yama_yoga(lagna_lord, target_lord, chart)

    # Positional helpers for downstream flatteners + match-type derivation
    # (l1_in_target, moon_in_target, aspect_l7_moon are required by the
    # Vivaha legacy decision tree replicated in _flatten_to_legacy_vivaha)
    l1_in_target   = (_planet_house(chart, lagna_lord) == target_house)
    moon_in_target = (_planet_house(chart, 'Moon')      == target_house)
    aspect_l1_lt   = pairwise_aspect(lagna_lord, target_lord, chart)
    aspect_lt_moon = pairwise_aspect(target_lord, 'Moon', chart) if target_lord != 'Moon' else {}

    return {
        'overlay': 'nakta_abhara_scan',
        'fired': bool(nakta or abhara or yama),
        'data': {
            'nakta_bridge':   nakta,
            'abhara_yoga':    abhara,
            'yama_yoga':      yama,
            'aspect_l1_lt':   aspect_l1_lt,
            'aspect_lt_moon': aspect_lt_moon,
            'l1_in_target':   l1_in_target,
            'moon_in_target': moon_in_target,
            'lagna_lord':     lagna_lord,
            'target_lord':    target_lord,
        },
        'narrative': ('Scanned for indirect relays (Nakta), malefic interference '
                      '(Abhara), and midpoint binders (Yama) on the L1–L_target '
                      'axis.'),
    }


# -----------------------------------------------------------------
# OVERLAY: kamboola_yoga
# Moon as cosmic proxy — substitutes failure → YES_WITH_DELAYS when:
#   L1 ↔ L_target lack direct aspect
#   AND Moon aspects both within orb
#   AND Moon's Tajik Vimshopaka surrogate ≥ 12
# -----------------------------------------------------------------

def overlay_kamboola_yoga(chart: Dict, state: Dict, inputs: Dict) -> Dict:
    lagna_sign = chart.get('lagna_sign', 0)
    lagna_lord = SIGN_LORDS[lagna_sign]
    target_house = state['target']['house']
    target_sign = (lagna_sign + target_house - 1) % 12
    target_lord = SIGN_LORDS[target_sign]

    kamboola = detect_kamboola_yoga(lagna_lord, target_lord, chart)
    if not kamboola:
        return _empty_finding('kamboola_yoga')

    return {
        'overlay': 'kamboola_yoga',
        'fired': True,
        'data': {'kamboola_yoga': kamboola},
        'verdict_substitution': {
            'when_primitives': ['failure'],
            'new_state': 'YES_WITH_DELAYS',
            'reason': 'Kamboola Yoga — Moon carries the connection as cosmic proxy.',
        },
        'narrative': kamboola['narrative'],
        'frontend_card_id': 'kamboola-card',
    }


# -----------------------------------------------------------------
# OVERLAY: gada_yoga
# All 7 classical planets in two consecutive Kendras → forces
# resolution within a 12-month horizon.
# -----------------------------------------------------------------

def overlay_gada_yoga(chart: Dict, state: Dict, inputs: Dict) -> Dict:
    gada = detect_gada_yoga(chart)
    if not gada:
        return _empty_finding('gada_yoga')

    return {
        'overlay': 'gada_yoga',
        'fired': True,
        'data': {'gada_yoga': gada},
        'verdict_substitution': {
            'when_primitives': ['failure'],
            'new_state': 'YES_WITH_DELAYS',
            'reason': 'Gada Yoga — structural compression forces resolution.',
        },
        'narrative': gada['narrative'],
        'frontend_card_id': 'gada-card',
    }


# -----------------------------------------------------------------
# OVERLAY: mars_5_vitality_split
# Garbha-specific. Mars in target house split by rulership:
#   - Risk signs (Aries/Cancer/Leo/Libra/Capricorn) → HIGH_RISK promotion
#   - Safe signs (Tau/Sco/Aqu/Gem/Vir/Sag/Pis)     → vitality narrative
# -----------------------------------------------------------------

def overlay_mars_5_vitality_split(chart: Dict, state: Dict, inputs: Dict) -> Dict:
    target_house = state['target']['house']
    mars_in_target = (_planet_house(chart, 'Mars') == target_house)
    if not mars_in_target:
        return _empty_finding('mars_5_vitality_split')

    mars_sign = chart.get('planets', {}).get('Mars', {}).get('sign_index')
    if mars_sign is None:
        return _empty_finding('mars_5_vitality_split')

    is_risk = is_mars_5th_high_risk(mars_sign)

    if is_risk:
        return {
            'overlay': 'mars_5_vitality_split',
            'fired': True,
            'data': {'mars_5_risk': True, 'mars_5_vitality': False,
                     'mars_sign': SIGNS[mars_sign]},
            'verdict_promotion_to': {
                'state': 'HIGH_RISK',
                'priority': 'absolute',
                'reason': f'Mars in {SIGNS[mars_sign]} (risk-grouped sign) within target house.',
            },
            'narrative': (
                f"Mars sits in the progeny house in {SIGNS[mars_sign]} — a "
                "Sun-ruled Sthira or Movable sign where its heat concentrates. "
                "Miscarriage / surgical-intervention risk is flagged. Medical "
                "monitoring through gestation is essential."
            ),
            'frontend_card_id': 'mars-risk-card',
        }

    return {
        'overlay': 'mars_5_vitality_split',
        'fired': True,
        'data': {'mars_5_risk': False, 'mars_5_vitality': True,
                 'mars_sign': SIGNS[mars_sign]},
        'narrative': (
            f"Mars sits in the progeny house in {SIGNS[mars_sign]} — a tempered "
            "sign where its heat translates to vitality rather than risk. If "
            "Jupiter aspects, signals a strong male child (Mangala Karaka)."
        ),
        'frontend_card_id': 'mars-vitality-card',
    }


# -----------------------------------------------------------------
# OVERLAY: sterile_sign_downgrade
# Garbha-specific. If target cusp falls in Alpa-Putra sign
# (Gem/Leo/Vir/Sco), downgrade YES → YES_WITH_DELAYS.
# -----------------------------------------------------------------

def overlay_sterile_sign_downgrade(chart: Dict, state: Dict, inputs: Dict) -> Dict:
    lagna_sign = chart.get('lagna_sign', 0)
    target_house = state['target']['house']
    target_sign = (lagna_sign + target_house - 1) % 12

    if not is_alpa_putra_sign(target_sign):
        return _empty_finding('sterile_sign_downgrade')

    return {
        'overlay': 'sterile_sign_downgrade',
        'fired': True,
        'data': {'target_cusp_sterile': True,
                 'target_cusp_sign': SIGNS[target_sign]},
        'verdict_downgrade': {
            'from_states': ['YES'],
            'to': 'YES_WITH_DELAYS',
            'reason': f'Target cusp in {SIGNS[target_sign]} (Alpa-Putra sterile sign).',
        },
        'narrative': (
            f"The progeny cusp falls in {SIGNS[target_sign]} — a classical "
            "low-fertility (Alpa-Putra) sign. Conception is structurally "
            "promised but physiological preparation is required: gentle "
            "reset through diet, stress reduction, or pre-conception workup."
        ),
        'frontend_card_id': 'sterile-card',
    }


# -----------------------------------------------------------------
# OVERLAY: rahu_ketu_progeny_axis
# Garbha-specific modern Tajik signaling:
#   - Rahu in target → CONDITIONAL_MEDICAL (IVF/IUI/surrogacy path)
#   - Ketu in target → adoption path; NO → CONDITIONAL_THIRD_PARTY
# -----------------------------------------------------------------

def overlay_rahu_ketu_progeny_axis(chart: Dict, state: Dict, inputs: Dict) -> Dict:
    target_house = state['target']['house']
    rahu_in_target = (_planet_house(chart, 'Rahu') == target_house)
    ketu_in_target = (_planet_house(chart, 'Ketu') == target_house)

    if not (rahu_in_target or ketu_in_target):
        return _empty_finding('rahu_ketu_progeny_axis')

    data = {'rahu_in_target': rahu_in_target, 'ketu_in_target': ketu_in_target}

    if rahu_in_target:
        return {
            'overlay': 'rahu_ketu_progeny_axis',
            'fired': True,
            'data': data,
            'verdict_substitution': {
                'when_primitives': ['conditional'],
                'new_state': 'CONDITIONAL_MEDICAL',
                'reason': 'Rahu in progeny axis — assisted conception path.',
            },
            'narrative': (
                "Rahu occupies the progeny axis. In modern Tajik reading, this "
                "indicates assisted conception — IVF, IUI, or surrogacy — as a "
                "viable and supported path, not an affliction."
            ),
            'frontend_card_id': 'rahu-target-card',
        }

    # Ketu case
    return {
        'overlay': 'rahu_ketu_progeny_axis',
        'fired': True,
        'data': data,
        'verdict_substitution': {
            'when_primitives': ['failure'],
            'new_state': 'CONDITIONAL_THIRD_PARTY',
            'reason': 'Ketu in progeny axis — adoption path indicated.',
        },
        'narrative': (
            "Ketu occupies the progeny axis. Spiritual detachment from "
            "biological conception is suggested — adoption may be the path "
            "this Prashna foretells."
        ),
        'frontend_card_id': 'ketu-target-card',
    }


# -----------------------------------------------------------------
# OVERLAY: eclipse_proximity_axis
# Shared (Garbha-active by default). If cast falls within ±15 days of
# a solar/lunar eclipse on a relevant axis (Lagna/7th, target/opposite,
# or L_target longitude), hard-cap sincerity at 45/100.
# -----------------------------------------------------------------

def overlay_eclipse_proximity_axis(chart: Dict, state: Dict, inputs: Dict) -> Dict:
    jd_ut = chart.get('jd_ut')
    if jd_ut is None:
        return _empty_finding('eclipse_proximity_axis')

    target_house = state['target']['house']
    eclipse = detect_eclipse_proximity(jd_ut, chart, target_house=target_house)
    if not eclipse:
        return _empty_finding('eclipse_proximity_axis')

    return {
        'overlay': 'eclipse_proximity_axis',
        'fired': True,
        'data': {'eclipse_proximity': eclipse},
        'sincerity_modifier': {
            'cap': 45,
            'reason': f'Eclipse shadow on {eclipse["axis_hit"]}.',
        },
        'narrative': eclipse['narrative'],
        'frontend_card_id': 'eclipse-card',
    }


# -----------------------------------------------------------------
# OVERLAY: inconclusive_check
# Garbha-specific. For current_pregnancy_confirmation intent only:
# if Moon is void-of-course OR target lord is heavily combust (<4°
# from Sun), set verdict modifier to INCONCLUSIVE_RECAST_REQUIRED.
# -----------------------------------------------------------------

def overlay_inconclusive_check(chart: Dict, state: Dict, inputs: Dict) -> Dict:
    intent = inputs.get('intent')
    if intent != 'current_pregnancy_confirmation':
        return _empty_finding('inconclusive_check')

    lagna_sign = chart.get('lagna_sign', 0)
    target_house = state['target']['house']
    target_sign = (lagna_sign + target_house - 1) % 12
    target_lord = SIGN_LORDS[target_sign]
    planets = chart.get('planets', {})

    moon_voc = is_moon_void_of_course(chart)
    l_target_heavy = is_heavily_combust(planets, target_lord)

    if not (moon_voc or l_target_heavy):
        return _empty_finding('inconclusive_check')

    reasons = []
    if moon_voc: reasons.append('Moon is void-of-course')
    if l_target_heavy: reasons.append(f'{target_lord} (target lord) is heavily combust')

    return {
        'overlay': 'inconclusive_check',
        'fired': True,
        'data': {'moon_voc': moon_voc, 'l_target_heavy_combust': l_target_heavy},
        'verdict_modifier_flag': 'INCONCLUSIVE_RECAST_REQUIRED',
        'narrative': (
            f"Cosmic indeterminacy detected: {' and '.join(reasons)}. "
            "Recast in 27–28 days as the lunar cycle completes. Repeat any "
            "clinical pregnancy test in the same window."
        ),
        'frontend_card_id': 'inconclusive-card',
    }


# -----------------------------------------------------------------
# VIVAHA-SPECIFIC OVERLAYS
# -----------------------------------------------------------------

def overlay_third_party_interference(chart: Dict, state: Dict, inputs: Dict) -> Dict:
    """
    Vivaha-specific. Per Ch 9 + legacy decision tree:
    Iterate 8th, 3rd, 4th lords — if a lord is classical malefic
    (Sun, Mars, Saturn) AND placed in target house, flag as interference.
    Format matches legacy vivaha_judgment exactly.
    """
    target_house = state['target']['house']  # 7 for Vivaha
    lagna_sign = chart.get('lagna_sign', 0)

    interferers = []
    house_labels = [
        (8, 'Female rival / other partner'),
        (3, 'Sibling interference'),
        (4, 'Parental interference'),
    ]
    for house_num, label in house_labels:
        h_sign = (lagna_sign + house_num - 1) % 12
        h_lord = SIGN_LORDS[h_sign]
        if h_lord in ('Sun', 'Mars', 'Saturn') and _planet_house(chart, h_lord) == target_house:
            interferers.append({
                'type': label,
                'trigger': f"Malefic {house_num}th lord ({h_lord}) occupies the {target_house}th house",
            })

    if not interferers:
        return _empty_finding('third_party_interference')

    return {
        'overlay': 'third_party_interference',
        'fired': True,
        'data': {'third_party_interference': interferers},
        'narrative': f'Detected {len(interferers)} third-party interference source(s) on the {target_house}th cusp.',
        'frontend_card_id': 'third-party-card',
    }


def overlay_emotional_reciprocity(chart: Dict, state: Dict, inputs: Dict) -> Dict:
    """
    Vivaha-specific. Per Ch 9 + legacy vivaha_judgment decision tree:
      - L1↔L7 in Ithesal             → 'mutual_love'
      - L1↔L7 in Esrapha             → 'past_engagement'
      - Both lords in same sign      → 'discord_short'
      - L1↔L7 within_orb otherwise   → 'neutral'
      - No L1↔L7 aspect within orb   → 'disengaged'
    """
    planets = chart.get('planets', {})
    lagna_sign = chart.get('lagna_sign', 0)
    lagna_lord = SIGN_LORDS[lagna_sign]
    target_house = state['target']['house']
    target_sign = (lagna_sign + target_house - 1) % 12
    target_lord = SIGN_LORDS[target_sign]

    asp_l1_l7 = pairwise_aspect(lagna_lord, target_lord, chart)

    if asp_l1_l7.get('within_orb'):
        yoga = asp_l1_l7.get('yoga')
        if yoga == 'Ithesal':
            reciprocity = 'mutual_love'
            narrative = ("Lagna Lord and 7th Lord are in Ithesal — mutual attraction "
                         "and active emotional engagement.")
        elif yoga == 'Esrapha':
            reciprocity = 'past_engagement'
            narrative = ("Lagna Lord and 7th Lord are in Esrapha — the emotional "
                         "energy is in the past; the connection is fading.")
        elif (planets.get(lagna_lord, {}).get('sign_index') ==
              planets.get(target_lord, {}).get('sign_index')):
            reciprocity = 'discord_short'
            narrative = ("Both lords occupy the same sign — short-lived friction, "
                         "quickly resolved.")
        else:
            reciprocity = 'neutral'
            narrative = "Active aspect but neither applying nor separating — neutral engagement."
    else:
        reciprocity = 'disengaged'
        narrative = ("Lagna Lord and 7th Lord do not aspect each other within orb — "
                     "emotional disengagement or blind spot between partners.")

    return {
        'overlay': 'emotional_reciprocity',
        'fired': True,
        'data': {
            'emotional_reciprocity': reciprocity,
            'reciprocity_narrative': narrative,
        },
        'narrative': narrative,
    }


# =================================================================
# PHASE 4D · PUTRA OVERLAYS (Long-Horizon Progeny — Family Size)
# =================================================================
# Distinct from Garbha (immediate biological cycle):
# Putra reads long-term capacity and family size from the 5th house,
# 5L (Putra Bhava lord), Jupiter (natural Putra Karaka), and the
# Saptamsha (D7) varga as the classical progeny anchor.

def overlay_putra_yoga_catalogue(chart: Dict, state: Dict, inputs: Dict) -> Dict:
    """
    Scans classical progeny yogas — 5L placement, Jupiter (Putra Karaka)
    condition, and 5th-house occupants. Produces a yoga list + family-size
    band, not a count promise (per Atul's guardrail: 'avoid fatalistic
    over-promises').
    """
    planets = chart.get('planets', {})
    lagna_sign = chart.get('lagna_sign', 0)
    fifth_sign = (lagna_sign + 4) % 12
    fifth_lord = SIGN_LORDS[fifth_sign]
    fifth_lord_house = _planet_house(chart, fifth_lord)
    jupiter_house = _planet_house(chart, 'Jupiter')

    yogas = []

    # 5L in Kendra (1/4/7/10) or Trikona (1/5/9) — fertile sthana
    if fifth_lord_house in (1, 4, 5, 7, 9, 10):
        yogas.append({
            'name': f'5th Lord in Kendra/Trikona',
            'detail': f'{fifth_lord} (5L) occupies the {fifth_lord_house}{_ordinal_suffix(fifth_lord_house)} '
                      f'house — Putra Bhava lord is well-placed.',
        })

    # Jupiter (Putra Karaka) in 5, 9, or 11
    if jupiter_house in (5, 9, 11):
        yogas.append({
            'name': 'Putra Karaka Strong',
            'detail': f'Jupiter (Putra Karaka) occupies the {jupiter_house}{_ordinal_suffix(jupiter_house)} '
                      f'house — natural progeny significator in a productive sthana.',
        })

    # Jupiter aspects 5th house (classical Putra Yoga)
    if jupiter_house and jupiter_house in (5,):  # Jupiter directly in 5th
        yogas.append({
            'name': 'Jupiter in 5th (Putra Yoga)',
            'detail': 'Jupiter occupies Putra Bhava directly — classical fertility yoga.',
        })

    # 5L–Jupiter relationship via aspect
    asp_5l_jup = pairwise_aspect(fifth_lord, 'Jupiter', chart) if fifth_lord != 'Jupiter' else {}
    if asp_5l_jup.get('within_orb') and asp_5l_jup.get('yoga') in ('Ithesal', 'Mutthashila'):
        yogas.append({
            'name': '5L–Jupiter Ithesal',
            'detail': f'{fifth_lord} (5L) is in applying aspect with Jupiter — '
                      f'Putra Karaka and Bhava lord are bound.',
        })

    # 5L combust / debilitated downgrades
    debilitations = {'Sun': 6, 'Moon': 7, 'Mars': 3, 'Mercury': 11, 'Jupiter': 9, 'Venus': 5, 'Saturn': 0}
    fifth_lord_sign = planets.get(fifth_lord, {}).get('sign_index')
    if debilitations.get(fifth_lord) == fifth_lord_sign:
        yogas.append({
            'name': '5L Debilitated',
            'detail': f'{fifth_lord} is in its sign of debilitation — Putra capacity diminished.',
            'is_caveat': True,
        })

    # Synthesise a family-size band — strictly qualitative (Atul's guardrail)
    positive_yogas = sum(1 for y in yogas if not y.get('is_caveat'))
    caveats = sum(1 for y in yogas if y.get('is_caveat'))
    if positive_yogas >= 3 and caveats == 0:
        band = 'Abundant'
        band_narrative = ('Multiple Putra yogas fire with no caveats — the long-horizon '
                          'reading favours a full family.')
    elif positive_yogas >= 2:
        band = 'Moderate'
        band_narrative = ('Putra Bhava is supported by some yogas — the long-horizon '
                          'reading favours a moderate family size.')
    elif positive_yogas == 1:
        band = 'Modest'
        band_narrative = ('A single positive Putra yoga fires — the long-horizon '
                          'reading suggests a modest family size, dependent on lifestyle choices.')
    else:
        band = 'Restricted'
        band_narrative = ('No clear Putra yogas fire — the long-horizon reading is '
                          'restrictive; this does not predict childlessness but indicates '
                          'the chart does not actively support a large family.')

    return {
        'overlay': 'putra_yoga_catalogue',
        'fired': len(yogas) > 0,
        'data': {
            'yogas':            yogas,
            'family_size_band': band,
            'band_narrative':   band_narrative,
            'fifth_lord':       fifth_lord,
            'fifth_lord_house': fifth_lord_house,
            'jupiter_house':    jupiter_house,
        },
        'narrative': band_narrative,
    }


def overlay_saptamsha_varga_anchor(chart: Dict, state: Dict, inputs: Dict) -> Dict:
    """
    Saptamsha (D7) varga is the classical anchor for progeny.
    Each 30° sign is divided into 7 parts of 4°17'09" each.
    The D7 Lagna sign is the strongest progeny indicator.

    Compute D7 position of: Lagna, 5L, Jupiter — and report their
    D7 sign placements as a progeny-quality reading.
    """
    planets = chart.get('planets', {})
    lagna_sign = chart.get('lagna_sign', 0)
    lagna_lon = chart.get('lagna_longitude', 0.0)
    fifth_sign = (lagna_sign + 4) % 12
    fifth_lord = SIGN_LORDS[fifth_sign]

    def to_d7_sign(longitude: float) -> int:
        """
        BPHS Saptamsha: each sign (30°) divided into 7 parts of 4°17'09" (~4.2857°).
        Odd signs (Aries, Gemini, ..., Aquarius) start D7 from same sign;
        even signs (Taurus, Cancer, ..., Pisces) start D7 from 7th sign.
        """
        sign = int(longitude // 30) % 12
        deg_in_sign = longitude % 30
        part = int(deg_in_sign / (30.0 / 7.0))  # 0..6
        if sign % 2 == 0:  # odd sign (Aries=0)
            d7_sign = (sign + part) % 12
        else:  # even sign
            d7_sign = (sign + 6 + part) % 12
        return d7_sign

    lagna_d7    = to_d7_sign(lagna_lon)
    fifth_lord_lon = planets.get(fifth_lord, {}).get('longitude', 0)
    fifth_lord_d7 = to_d7_sign(fifth_lord_lon)
    jupiter_lon = planets.get('Jupiter', {}).get('longitude', 0)
    jupiter_d7 = to_d7_sign(jupiter_lon)

    SIGN_NAMES = ['Aries','Taurus','Gemini','Cancer','Leo','Virgo',
                  'Libra','Scorpio','Sagittarius','Capricorn','Aquarius','Pisces']

    # Fertile vs barren signs (classical Putra evaluation)
    fertile_signs   = {3, 7, 11}      # Cancer, Scorpio, Pisces (water)
    semi_fertile    = {1, 6}           # Taurus, Libra (Venus-ruled)
    barren_signs    = {0, 4, 5, 9}     # Aries, Leo, Virgo, Capricorn

    def classify_sign(s):
        if s in fertile_signs:    return ('fertile', 'productive D7 sign')
        if s in semi_fertile:     return ('semi_fertile', 'mixed D7 sign')
        if s in barren_signs:     return ('barren', 'restrictive D7 sign')
        return ('neutral', 'neutral D7 sign')

    lagna_d7_class    = classify_sign(lagna_d7)
    fifth_lord_d7_class = classify_sign(fifth_lord_d7)
    jupiter_d7_class  = classify_sign(jupiter_d7)

    # Scoring: how many indicators land in fertile signs?
    fertile_count = sum(1 for c in (lagna_d7_class, fifth_lord_d7_class, jupiter_d7_class)
                        if c[0] == 'fertile')
    barren_count  = sum(1 for c in (lagna_d7_class, fifth_lord_d7_class, jupiter_d7_class)
                        if c[0] == 'barren')

    if fertile_count >= 2:
        verdict = 'strong'
        narrative = (f'Saptamsha (D7) anchor confirms long-horizon progeny capacity — '
                     f'{fertile_count} of 3 key indicators (D7 Lagna, 5L, Jupiter) sit in fertile signs.')
    elif barren_count >= 2:
        verdict = 'weak'
        narrative = (f'Saptamsha (D7) anchor weakens long-horizon progeny capacity — '
                     f'{barren_count} of 3 key indicators sit in barren signs. The Rashi reading '
                     f'should be weighed against this restriction.')
    else:
        verdict = 'moderate'
        narrative = ('Saptamsha (D7) anchor is mixed — no dominant fertile or barren signal. '
                     'The Rashi chart\'s Putra reading should be taken at face value.')

    return {
        'overlay': 'saptamsha_varga_anchor',
        'fired': True,
        'data': {
            'd7_verdict':      verdict,
            'd7_narrative':    narrative,
            'lagna_d7_sign':   SIGN_NAMES[lagna_d7],
            'fifth_lord_d7_sign': SIGN_NAMES[fifth_lord_d7],
            'jupiter_d7_sign': SIGN_NAMES[jupiter_d7],
            'lagna_d7_class':  lagna_d7_class[0],
            'fifth_lord_d7_class': fifth_lord_d7_class[0],
            'jupiter_d7_class': jupiter_d7_class[0],
            'fertile_count':   fertile_count,
            'barren_count':    barren_count,
        },
        'narrative': narrative,
    }


# =================================================================
# PHASE 4D · CHILD-DEVELOPMENT OVERLAYS (Putra → child_development_health)
# =================================================================
# Per Prashna Marga Ch.16: when a child already exists and the query is
# about their wellbeing/speech/development, the chart pivots — the 5th
# house BECOMES the child's Lagna, so child-specific topics count from
# there (speech = 2nd from 5th = 6th of the radix). Mercury (Vak-karaka)
# replaces Jupiter (Putra Karaka) as the operative significator.

def overlay_child_wellbeing_scan(chart: Dict, state: Dict, inputs: Dict) -> Dict:
    """
    Reads the child as a person: 5th lord condition, 5th house occupants,
    and the parent → child connection (Lagna lord vs 5th lord).
    This is the child's general 'state of being' scan — not their specific
    speech/cognition (that is mercury_speech_affliction_check).
    """
    planets = chart.get('planets', {})
    lagna_sign = chart.get('lagna_sign', 0)
    lagna_lord = SIGN_LORDS[lagna_sign]
    fifth_sign = (lagna_sign + 4) % 12
    fifth_lord = SIGN_LORDS[fifth_sign]
    fifth_lord_house = _planet_house(chart, fifth_lord)

    # 5th-house occupants — malefics indicate stress on the child's body/mind
    fifth_house_occupants = []
    for planet_name, pdata in planets.items():
        if isinstance(pdata, dict) and _planet_house(chart, planet_name) == 5:
            fifth_house_occupants.append(planet_name)

    classical_malefics = {'Sun', 'Mars', 'Saturn', 'Rahu', 'Ketu'}
    classical_benefics = {'Moon', 'Mercury', 'Jupiter', 'Venus'}
    malefics_in_5th  = [p for p in fifth_house_occupants if p in classical_malefics]
    benefics_in_5th  = [p for p in fifth_house_occupants if p in classical_benefics]

    # 5th lord condition
    fifth_lord_combust = _is_combust(planets, fifth_lord)
    fifth_lord_in_dushtana = fifth_lord_house in (6, 8, 12)
    fifth_lord_in_kendra_trikona = fifth_lord_house in (1, 4, 5, 7, 9, 10)

    # Parent-child connection: aspect between Lagna lord and 5th lord
    asp_l1_l5 = pairwise_aspect(lagna_lord, fifth_lord, chart) if lagna_lord != fifth_lord else {}

    findings = []
    if fifth_lord_in_dushtana:
        findings.append({
            'name': '5L in Dushtana',
            'detail': f'{fifth_lord} (5L · child as person) sits in the '
                      f'{fifth_lord_house}{_ordinal_suffix(fifth_lord_house)} house '
                      f'(Dushtana — a house of difficulty). The child carries '
                      f'a structural challenge that asks for sustained support.',
            'severity': 'caveat',
        })
    elif fifth_lord_in_kendra_trikona:
        findings.append({
            'name': '5L in Kendra/Trikona',
            'detail': f'{fifth_lord} (5L · child as person) is well-placed in the '
                      f'{fifth_lord_house}{_ordinal_suffix(fifth_lord_house)} house. '
                      f'The child has a stable foundation to grow from.',
            'severity': 'positive',
        })

    if fifth_lord_combust:
        findings.append({
            'name': '5L Combust',
            'detail': f'{fifth_lord} (5L) is combust by the Sun — the child\u2019s '
                      f'expression and visibility are temporarily eclipsed. Often '
                      f'reads as developmental matters taking longer to surface.',
            'severity': 'caveat',
        })

    if malefics_in_5th:
        findings.append({
            'name': f'{len(malefics_in_5th)} malefic(s) in 5th',
            'detail': f'{", ".join(malefics_in_5th)} occupy the 5th house directly '
                      f'(the child\u2019s body and mind). Stress markers — does not '
                      f'predict outcome, but indicates the child\u2019s '
                      f'developmental terrain carries friction.',
            'severity': 'caveat',
        })
    if benefics_in_5th:
        findings.append({
            'name': f'Benefic support in 5th',
            'detail': f'{", ".join(benefics_in_5th)} occupy the 5th house — '
                      f'protective influence on the child\u2019s developmental field.',
            'severity': 'positive',
        })

    if asp_l1_l5.get('within_orb'):
        yoga = asp_l1_l5.get('yoga')
        if yoga in ('Ithesal', 'Mutthashila'):
            findings.append({
                'name': f'Lagna lord ↔ 5L · {yoga}',
                'detail': f'Active connection between {lagna_lord} (you) and '
                          f'{fifth_lord} (the child) — your engagement '
                          f'reaches the child directly. This is your strongest asset.',
                'severity': 'positive',
            })
        elif yoga == 'Esrapha':
            findings.append({
                'name': 'Lagna lord ↔ 5L · Esrapha',
                'detail': f'Parent-child connection is separating — energy is '
                          f'flowing past rather than landing. Slow it down, '
                          f'be deliberate.',
                'severity': 'caveat',
            })

    # Aggregate severity
    positive_n = sum(1 for f in findings if f.get('severity') == 'positive')
    caveat_n   = sum(1 for f in findings if f.get('severity') == 'caveat')
    if positive_n >= 2 and caveat_n <= 1:
        verdict = 'supportive'
    elif caveat_n >= 2 and positive_n == 0:
        verdict = 'structurally challenged'
    else:
        verdict = 'mixed'

    narrative = (f'Child\u2019s wellbeing read via 5th lord ({fifth_lord}) and 5th-house '
                 f'occupants. Verdict: {verdict}. {len(findings)} marker(s) detected.')

    return {
        'overlay': 'child_wellbeing_scan',
        'fired': len(findings) > 0,
        'data': {
            'findings':           findings,
            'verdict':            verdict,
            'fifth_lord':         fifth_lord,
            'fifth_lord_house':   fifth_lord_house,
            'fifth_lord_combust': fifth_lord_combust,
            'malefics_in_5th':    malefics_in_5th,
            'benefics_in_5th':    benefics_in_5th,
            'parent_child_aspect': asp_l1_l5.get('yoga') if asp_l1_l5.get('within_orb') else None,
        },
        'narrative': narrative,
    }


def overlay_mercury_speech_affliction_check(chart: Dict, state: Dict, inputs: Dict) -> Dict:
    """
    Mercury as Vak-karaka (universal significator of speech / cognition).
    Per Prashna Marga Ch.16, for queries about a child\u2019s speech or
    cognitive development, Mercury\u2019s condition is the operative reading
    (not Jupiter, which is Putra Karaka for capacity/family-size).

    Evaluates: combust, retrograde, debilitation, dushtana placement,
    malefic aspects, benefic aspects. Aggregates into an affliction band.
    """
    planets = chart.get('planets', {})
    lagna_sign = chart.get('lagna_sign', 0)
    mercury = planets.get('Mercury', {}) or {}

    mercury_house = _planet_house(chart, 'Mercury')
    mercury_sign  = mercury.get('sign_index', -1)
    mercury_combust = _is_combust(planets, 'Mercury')
    mercury_retro   = bool(mercury.get('retrograde'))

    # Debilitation
    mercury_debilitated = (mercury_sign == 11)  # Pisces is Mercury's debilitation
    mercury_exalted     = (mercury_sign == 5)   # Virgo (own sign + exaltation)

    mercury_in_dushtana = mercury_house in (6, 8, 12)

    # Malefic and benefic aspects to Mercury
    classical_malefics = ['Sun', 'Mars', 'Saturn', 'Rahu', 'Ketu']
    classical_benefics = ['Moon', 'Jupiter', 'Venus']

    malefic_aspects = []
    benefic_aspects = []
    for p in classical_malefics:
        if p == 'Mercury': continue
        if not planets.get(p): continue
        asp = pairwise_aspect(p, 'Mercury', chart)
        if asp.get('within_orb'):
            malefic_aspects.append({'planet': p, 'yoga': asp.get('yoga')})
    for p in classical_benefics:
        if p == 'Mercury': continue
        if not planets.get(p): continue
        asp = pairwise_aspect(p, 'Mercury', chart)
        if asp.get('within_orb'):
            benefic_aspects.append({'planet': p, 'yoga': asp.get('yoga')})

    findings = []
    if mercury_combust:
        findings.append({
            'name': 'Mercury Combust',
            'detail': 'Mercury (Vak-karaka — speech and cognition) is combust by the Sun. '
                      'Speech and cognitive expression are eclipsed; the child\u2019s '
                      'voice has not yet found its full register.',
            'severity': 'caveat',
        })
    if mercury_retro:
        findings.append({
            'name': 'Mercury Retrograde',
            'detail': 'Mercury is retrograde — internal processing runs ahead of '
                      'external expression. The child often understands more than '
                      'they can yet articulate.',
            'severity': 'note',
        })
    if mercury_debilitated:
        findings.append({
            'name': 'Mercury Debilitated (in Pisces)',
            'detail': 'Mercury is in Pisces — its sign of debilitation. Communication '
                      'tends to be intuitive and non-linear rather than precise. '
                      'Structured speech support helps significantly.',
            'severity': 'caveat',
        })
    if mercury_exalted:
        findings.append({
            'name': 'Mercury Exalted (in Virgo)',
            'detail': 'Mercury is in Virgo — its own sign and exaltation. The cognitive '
                      'and speech apparatus is structurally sound; any delay is '
                      'temporal, not constitutional.',
            'severity': 'positive',
        })
    if mercury_in_dushtana:
        findings.append({
            'name': f'Mercury in {mercury_house}{_ordinal_suffix(mercury_house)} (Dushtana)',
            'detail': f'Mercury occupies the {mercury_house}th house (Dushtana). '
                      f'Speech development requires sustained external support and '
                      f'protected practice space.',
            'severity': 'caveat',
        })

    for m in malefic_aspects:
        findings.append({
            'name': f'{m["planet"]} aspects Mercury · {m["yoga"]}',
            'detail': f'{m["planet"]} casts a {m["yoga"]} aspect on Mercury. Malefic '
                      f'pressure on speech — friction, frustration around verbal '
                      f'self-expression.',
            'severity': 'caveat',
        })
    for b in benefic_aspects:
        findings.append({
            'name': f'{b["planet"]} aspects Mercury · {b["yoga"]}',
            'detail': f'{b["planet"]} casts a {b["yoga"]} aspect on Mercury. Benefic '
                      f'support — speech development has structural backing.',
            'severity': 'positive',
        })

    # Affliction band
    caveat_n   = sum(1 for f in findings if f.get('severity') == 'caveat')
    positive_n = sum(1 for f in findings if f.get('severity') == 'positive')
    net = positive_n - caveat_n

    if net >= 2:
        band = 'Mercury well-supported'
        verdict = 'supported'
    elif net <= -2:
        band = 'Mercury heavily afflicted'
        verdict = 'afflicted'
    elif caveat_n >= 1 and positive_n >= 1:
        band = 'Mercury mixed'
        verdict = 'mixed'
    elif caveat_n == 0 and positive_n == 0:
        band = 'Mercury neutral'
        verdict = 'neutral'
    else:
        band = 'Mercury lightly afflicted' if caveat_n > positive_n else 'Mercury lightly supported'
        verdict = 'mixed'

    narrative = (f'Mercury (Vak-karaka) condition: {band}. '
                 f'{positive_n} supportive marker(s), {caveat_n} affliction marker(s).')

    return {
        'overlay': 'mercury_speech_affliction_check',
        'fired': len(findings) > 0,
        'data': {
            'findings':              findings,
            'verdict':               verdict,
            'band':                  band,
            'mercury_house':         mercury_house,
            'mercury_combust':       mercury_combust,
            'mercury_retrograde':    mercury_retro,
            'mercury_debilitated':   mercury_debilitated,
            'mercury_exalted':       mercury_exalted,
            'mercury_in_dushtana':   mercury_in_dushtana,
            'malefic_aspects':       malefic_aspects,
            'benefic_aspects':       benefic_aspects,
            'positive_count':        positive_n,
            'caveat_count':          caveat_n,
        },
        'narrative': narrative,
    }


# =================================================================
# PHASE 4D-EXT · PUTRA · child_acute_illness OVERLAYS
# =================================================================
# Target = 10th house = 6th from 5th = the child's illness.
# Recovery coordinates with 10th lord separating from malefics (Esrapha)
# or 5th lord (child's Lagna) gaining a Pragalbha degree-band bonus.

def overlay_child_illness_scan(chart: Dict, state: Dict, inputs: Dict) -> Dict:
    """
    Reads the child's illness via the 10th house of the radix (= 6th-from-5th).
    Evaluates 10L condition, malefic aspects to 5L (child), and Esrapha
    between L10 and L5 as a recovery signal.
    """
    planets = chart.get('planets', {})
    lagna_sign = chart.get('lagna_sign', 0)
    fifth_sign = (lagna_sign + 4) % 12
    fifth_lord = SIGN_LORDS[fifth_sign]
    tenth_sign = (lagna_sign + 9) % 12  # 10th-from-Lagna = 6th-from-5th
    tenth_lord = SIGN_LORDS[tenth_sign]

    fifth_lord_house  = _planet_house(chart, fifth_lord)
    tenth_lord_house  = _planet_house(chart, tenth_lord)

    fifth_lord_combust = _is_combust(planets, fifth_lord)
    tenth_lord_combust = _is_combust(planets, tenth_lord)

    classical_malefics = ['Sun', 'Mars', 'Saturn', 'Rahu', 'Ketu']
    classical_benefics = ['Moon', 'Jupiter', 'Venus', 'Mercury']

    # Malefic aspects to 5L (the child) — illness pressure
    malefic_to_5l = []
    for m in classical_malefics:
        if m == fifth_lord: continue
        if not planets.get(m): continue
        asp = pairwise_aspect(m, fifth_lord, chart)
        if asp.get('within_orb'):
            malefic_to_5l.append({'planet': m, 'yoga': asp.get('yoga')})

    # Benefic aspects to 5L — recovery support
    benefic_to_5l = []
    for b in classical_benefics:
        if b == fifth_lord: continue
        if not planets.get(b): continue
        asp = pairwise_aspect(b, fifth_lord, chart)
        if asp.get('within_orb'):
            benefic_to_5l.append({'planet': b, 'yoga': asp.get('yoga')})

    # Esrapha between L10 (illness) and L5 (child) → recovery signal
    asp_10_5 = pairwise_aspect(tenth_lord, fifth_lord, chart) if tenth_lord != fifth_lord else {}
    illness_separating = (asp_10_5.get('yoga') == 'Esrapha')
    illness_applying   = (asp_10_5.get('yoga') in ('Ithesal', 'Mutthashila'))

    findings = []
    if illness_separating:
        findings.append({
            'name': 'L10 ↔ L5 Esrapha (illness separating)',
            'detail': f'{tenth_lord} (illness) is in separating aspect with '
                      f'{fifth_lord} (child) — the illness is moving past. '
                      f'Recovery direction is established.',
            'severity': 'positive',
        })
    elif illness_applying:
        findings.append({
            'name': f'L10 ↔ L5 {asp_10_5.get("yoga")} (illness applying)',
            'detail': f'{tenth_lord} (illness) is in applying aspect with '
                      f'{fifth_lord} (child) — the illness is still actively '
                      f'pressing. Symptom intensity is not yet past peak.',
            'severity': 'caveat',
        })

    if tenth_lord_combust:
        findings.append({
            'name': 'L10 Combust',
            'detail': f'{tenth_lord} (illness lord) is combust by the Sun — '
                      f'the illness is in an acute, blazing phase rather than '
                      f'a chronic plateau. Often resolves more decisively '
                      f'once the combustion clears.',
            'severity': 'note',
        })

    if fifth_lord_combust:
        findings.append({
            'name': 'L5 Combust',
            'detail': f'{fifth_lord} (the child) is combust — the child\u2019s '
                      f'vitality is temporarily eclipsed. Watch closely; '
                      f'preserve rest.',
            'severity': 'caveat',
        })

    for mm in malefic_to_5l:
        findings.append({
            'name': f'{mm["planet"]} aspects L5 ({mm["yoga"]})',
            'detail': f'{mm["planet"]} casts a {mm["yoga"]} aspect on '
                      f'{fifth_lord} (the child). Pressure on the child\u2019s '
                      f'vitality during this aspect window.',
            'severity': 'caveat',
        })

    for bb in benefic_to_5l:
        findings.append({
            'name': f'{bb["planet"]} aspects L5 ({bb["yoga"]})',
            'detail': f'{bb["planet"]} casts a {bb["yoga"]} aspect on '
                      f'{fifth_lord} (the child). Recovery support is active.',
            'severity': 'positive',
        })

    # Aggregate recovery prognosis
    positive_n = sum(1 for f in findings if f.get('severity') == 'positive')
    caveat_n   = sum(1 for f in findings if f.get('severity') == 'caveat')
    if illness_separating and positive_n > caveat_n:
        prognosis = 'recovery indicated'
    elif positive_n >= 2 and caveat_n <= 1:
        prognosis = 'recovery supported'
    elif caveat_n >= 3 and positive_n == 0:
        prognosis = 'extended care indicated'
    elif caveat_n > positive_n:
        prognosis = 'sustained vigilance required'
    else:
        prognosis = 'mixed signals'

    narrative = (f'Child illness scan via L10 ({tenth_lord}) / L5 ({fifth_lord}). '
                 f'Prognosis: {prognosis}. {positive_n} support, {caveat_n} caveat.')

    return {
        'overlay': 'child_illness_scan',
        'fired': len(findings) > 0,
        'data': {
            'findings':              findings,
            'prognosis':             prognosis,
            'fifth_lord':            fifth_lord,
            'fifth_lord_house':      fifth_lord_house,
            'fifth_lord_combust':    fifth_lord_combust,
            'tenth_lord':            tenth_lord,
            'tenth_lord_house':      tenth_lord_house,
            'tenth_lord_combust':    tenth_lord_combust,
            'illness_separating':    illness_separating,
            'illness_applying':      illness_applying,
            'malefic_to_5l_count':   len(malefic_to_5l),
            'benefic_to_5l_count':   len(benefic_to_5l),
        },
        'narrative': narrative,
    }


# =================================================================
# PHASE 4D-EXT · PUTRA · runaway_estranged_child OVERLAYS
# =================================================================
# An Aagaman (return) reading. Target = 8th house = 4th from 5th = the
# child's home/stability. Watch L5 motion: retrograding toward L1 or the
# Prashna Lagna cusp indicates the child returning.

def overlay_runaway_aagaman_check(chart: Dict, state: Dict, inputs: Dict) -> Dict:
    """
    Aagaman (return) reading for a runaway or estranged child.
    Reads L5's direction (retrograde → returning), its longitude vs L1
    and the Prashna Lagna cusp (degree-distance = time to return), and
    whether L5 has reached the 8th house (4th-from-5th = a stable home).
    """
    planets = chart.get('planets', {})
    lagna_sign = chart.get('lagna_sign', 0)
    lagna_lord = SIGN_LORDS[lagna_sign]
    fifth_sign = (lagna_sign + 4) % 12
    fifth_lord = SIGN_LORDS[fifth_sign]

    fifth_lord_house  = _planet_house(chart, fifth_lord)
    fifth_lord_lon    = (planets.get(fifth_lord, {}) or {}).get('longitude')
    fifth_lord_retro  = bool((planets.get(fifth_lord, {}) or {}).get('retrograde'))

    lagna_lord_lon    = (planets.get(lagna_lord, {}) or {}).get('longitude')
    prashna_lagna_lon = chart.get('lagna_longitude')

    findings = []

    # Retrograde L5 → returning motion
    if fifth_lord_retro:
        findings.append({
            'name': f'{fifth_lord} (L5) Retrograde',
            'detail': f'{fifth_lord} — the child\u2019s significator — is in '
                      f'retrograde motion. The classical signal for return: '
                      f'the child\u2019s trajectory has reversed direction.',
            'severity': 'positive',
        })
    else:
        findings.append({
            'name': f'{fifth_lord} (L5) Direct',
            'detail': f'{fifth_lord} is direct in motion — the child\u2019s '
                      f'trajectory has not yet reversed. Return is not '
                      f'classically signalled at this cast.',
            'severity': 'caveat',
        })

    # L5 placement — in 4th-from-5th (= 8th of radix) means settled-elsewhere
    if fifth_lord_house == 8:
        findings.append({
            'name': 'L5 in 8th (4th-from-5th)',
            'detail': f'{fifth_lord} occupies the 8th house of the radix, '
                      f'which is the 4th-from-5th — the child\u2019s home. '
                      f'The child is in some kind of settled domestic '
                      f'situation (theirs, not yours).',
            'severity': 'note',
        })
    elif fifth_lord_house in (1, 4):
        findings.append({
            'name': f'L5 in {fifth_lord_house}{_ordinal_suffix(fifth_lord_house)} (your space)',
            'detail': f'{fifth_lord} sits in YOUR 1st or 4th house — the '
                      f'child\u2019s significator has returned to the querent\u2019s '
                      f'space. Classical homecoming signature.',
            'severity': 'positive',
        })
    elif fifth_lord_house == 12:
        findings.append({
            'name': 'L5 in 12th',
            'detail': f'{fifth_lord} sits in the 12th house — the child is '
                      f'in a far-away, hidden, or dissolution-toned setting. '
                      f'Distance is currently prevailing.',
            'severity': 'caveat',
        })

    # Degree distance from L5 to L1 (parent) and to Prashna Lagna cusp
    distance_to_l1   = None
    distance_to_cusp = None
    if fifth_lord_lon is not None and lagna_lord_lon is not None:
        distance_to_l1 = round(abs((fifth_lord_lon - lagna_lord_lon + 360) % 360), 2)
        if distance_to_l1 > 180: distance_to_l1 = round(360 - distance_to_l1, 2)
    if fifth_lord_lon is not None and prashna_lagna_lon is not None:
        distance_to_cusp = round(abs((fifth_lord_lon - prashna_lagna_lon + 360) % 360), 2)
        if distance_to_cusp > 180: distance_to_cusp = round(360 - distance_to_cusp, 2)

    if distance_to_l1 is not None and distance_to_l1 <= 6:
        findings.append({
            'name': f'L5 within 6° of L1',
            'detail': f'{fifth_lord} (child) is within 6° of {lagna_lord} '
                      f'(you). Physical reunion is energetically near.',
            'severity': 'positive',
        })

    # Aggregate verdict
    positive_n = sum(1 for f in findings if f.get('severity') == 'positive')
    caveat_n   = sum(1 for f in findings if f.get('severity') == 'caveat')
    if fifth_lord_retro and positive_n >= 2:
        return_likelihood = 'return indicated'
    elif fifth_lord_retro:
        return_likelihood = 'return signalled but not immediate'
    elif positive_n > caveat_n:
        return_likelihood = 'reconciliation possible without physical return'
    else:
        return_likelihood = 'no clear return signal in this cast'

    narrative = (f'Aagaman check via L5 ({fifth_lord}). Verdict: {return_likelihood}. '
                 f'L5 motion: {"retrograde" if fifth_lord_retro else "direct"}; '
                 f'L5 in house {fifth_lord_house}.')

    return {
        'overlay': 'runaway_aagaman_check',
        'fired': True,
        'data': {
            'findings':           findings,
            'return_likelihood':  return_likelihood,
            'fifth_lord':         fifth_lord,
            'fifth_lord_house':   fifth_lord_house,
            'fifth_lord_retro':   fifth_lord_retro,
            'fifth_lord_longitude':   fifth_lord_lon,
            'lagna_lord_longitude':   lagna_lord_lon,
            'prashna_lagna_longitude': prashna_lagna_lon,
            'distance_to_l1':     distance_to_l1,
            'distance_to_cusp':   distance_to_cusp,
        },
        'narrative': narrative,
    }


# =================================================================
# PHASE 4D-EXT · PUTRA · legal_child_custody OVERLAYS
# =================================================================
# Competitive Ithasala test: which parent's lord (L1 = querent, L7 =
# ex-spouse) holds a stronger aspect with L5 (the child).

def overlay_custody_ithasala_competition(chart: Dict, state: Dict, inputs: Dict) -> Dict:
    """
    Compares the L1↔L5 Ithasala strength against the L7↔L5 Ithasala
    strength. The parent whose lord holds a closer, more positive aspect
    is the chart's favored custodian.
    """
    lagna_sign = chart.get('lagna_sign', 0)
    lagna_lord = SIGN_LORDS[lagna_sign]
    fifth_sign = (lagna_sign + 4) % 12
    fifth_lord = SIGN_LORDS[fifth_sign]
    seventh_sign = (lagna_sign + 6) % 12
    seventh_lord = SIGN_LORDS[seventh_sign]

    # L1 ↔ L5 aspect (you ↔ the child)
    asp_1_5 = pairwise_aspect(lagna_lord, fifth_lord, chart) if lagna_lord != fifth_lord else {}
    # L7 ↔ L5 aspect (ex-spouse ↔ the child)
    asp_7_5 = pairwise_aspect(seventh_lord, fifth_lord, chart) if seventh_lord != fifth_lord else {}

    POSITIVE_YOGAS = {'Ithesal': 3, 'Mutthashila': 2, 'Kamboola': 2}
    NEUTRAL_YOGAS  = {'Nakta': 1, 'Yama': 1}
    NEGATIVE_YOGAS = {'Esrapha': -2, 'Manaoo': -1}

    def score_aspect(asp):
        if not asp.get('within_orb'):
            return 0, 'no aspect'
        yoga = asp.get('yoga')
        for table, label in [(POSITIVE_YOGAS, 'positive'),
                              (NEUTRAL_YOGAS, 'neutral'),
                              (NEGATIVE_YOGAS, 'negative')]:
            if yoga in table:
                return table[yoga], f'{yoga} ({label})'
        return 0, yoga or 'unspecified'

    score_l1_l5, label_l1_l5 = score_aspect(asp_1_5)
    score_l7_l5, label_l7_l5 = score_aspect(asp_7_5)

    if lagna_lord == fifth_lord:
        score_l1_l5 = 3  # self-rule = strongest possible
        label_l1_l5 = 'self-ruled (lagna lord IS the 5th lord)'
    if seventh_lord == fifth_lord:
        score_l7_l5 = 3
        label_l7_l5 = 'self-ruled (7th lord IS the 5th lord)'

    if score_l1_l5 > score_l7_l5:
        winner = 'querent'
        winner_lord = lagna_lord
        narrative = (f'L1 ↔ L5 ({label_l1_l5}, +{score_l1_l5}) is stronger than '
                     f'L7 ↔ L5 ({label_l7_l5}, +{score_l7_l5}). The chart favors '
                     f'the querent\u2019s connection to the child.')
    elif score_l7_l5 > score_l1_l5:
        winner = 'ex_spouse'
        winner_lord = seventh_lord
        narrative = (f'L7 ↔ L5 ({label_l7_l5}, +{score_l7_l5}) is stronger than '
                     f'L1 ↔ L5 ({label_l1_l5}, +{score_l1_l5}). The chart favors '
                     f'the other parent\u2019s connection to the child.')
    else:
        winner = 'tied'
        winner_lord = None
        narrative = (f'Both parents\u2019 connections to the child read at '
                     f'equivalent strength (L1↔L5: {label_l1_l5}; L7↔L5: '
                     f'{label_l7_l5}). The chart does not favor either side; '
                     f'outcome rests on external factors.')

    return {
        'overlay': 'custody_ithasala_competition',
        'fired': True,
        'data': {
            'lagna_lord':    lagna_lord,
            'fifth_lord':    fifth_lord,
            'seventh_lord':  seventh_lord,
            'l1_l5_aspect':  label_l1_l5,
            'l1_l5_score':   score_l1_l5,
            'l7_l5_aspect':  label_l7_l5,
            'l7_l5_score':   score_l7_l5,
            'winner':        winner,
            'winner_lord':   winner_lord,
        },
        'narrative': narrative,
    }


# =================================================================
# PHASE 4D · ANYA-SAMBANDHA OVERLAYS (Unconventional & Hidden)
# =================================================================

def overlay_secret_aspect_scan(chart: Dict, state: Dict, inputs: Dict) -> Dict:
    """
    Scans for hidden-relationship signatures:
      - 7L in 12th (hidden partnerships)
      - 12L in 7th (secret influence over partner)
      - Combust planets near the 7L (concealed by Sun)
      - Venus in 12th (private affections)
      - Mars-Venus connection via 12th
    """
    planets = chart.get('planets', {})
    lagna_sign = chart.get('lagna_sign', 0)
    seventh_sign = (lagna_sign + 6) % 12
    twelfth_sign = (lagna_sign + 11) % 12
    seventh_lord = SIGN_LORDS[seventh_sign]
    twelfth_lord = SIGN_LORDS[twelfth_sign]

    signatures = []

    if _planet_house(chart, seventh_lord) == 12:
        signatures.append({
            'name': '7L in 12th',
            'detail': f'{seventh_lord} (7L) is in the 12th house — partnerships happen '
                      f'in hidden, private, or unconventional contexts.',
        })

    if _planet_house(chart, twelfth_lord) == 7:
        signatures.append({
            'name': '12L in 7th',
            'detail': f'{twelfth_lord} (12L) is in the 7th house — secret or background '
                      f'influences shape the partnership domain.',
        })

    if _is_combust(planets, seventh_lord):
        signatures.append({
            'name': '7L Combust',
            'detail': f'{seventh_lord} (7L) is combust — partnership matters operate '
                      f'in concealment; the relationship may be private or hidden.',
        })

    venus_house = _planet_house(chart, 'Venus')
    if venus_house == 12:
        signatures.append({
            'name': 'Venus in 12th',
            'detail': 'Venus occupies the 12th house — affections expressed privately or in seclusion.',
        })

    # Mars-Venus 12th-house mutual aspect (intensity signature)
    mars_house  = _planet_house(chart, 'Mars')
    if {venus_house, mars_house} <= {12}:
        signatures.append({
            'name': 'Mars-Venus in 12th',
            'detail': 'Both Mars and Venus tenant the 12th — strong private-intensity signature.',
        })

    fired = len(signatures) > 0

    if not fired:
        narrative = ('No strong hidden-relationship signatures detected — partnership '
                     'activity, if any, operates in overt registers.')
    else:
        narrative = (f'{len(signatures)} hidden-relationship signature(s) detected. '
                     f'The partnership terrain is unconventional or concealed.')

    return {
        'overlay': 'secret_aspect_scan',
        'fired': fired,
        'data': {
            'signatures':       signatures,
            'count':            len(signatures),
            'seventh_lord':     seventh_lord,
            'twelfth_lord':     twelfth_lord,
            'venus_house':      venus_house,
            'mars_house':       mars_house,
        },
        'narrative': narrative,
    }


def overlay_node_axis_activation(chart: Dict, state: Dict, inputs: Dict) -> Dict:
    """
    Rahu-Ketu axis activation on alliance-relevant axes:
      - 1/7 axis (self vs partner)
      - 5/11 axis (creative bonds vs networks)
      - Nodes aspecting/conjuncting target lord
    Indicates karmic, sudden, or unconventional alliance dynamics.
    """
    planets = chart.get('planets', {})
    rahu_house = _planet_house(chart, 'Rahu')
    ketu_house = _planet_house(chart, 'Ketu')

    activations = []
    axis_axes_hit = []

    # 1/7 axis — self / partner
    if {rahu_house, ketu_house} == {1, 7}:
        activations.append({
            'name': 'Rahu-Ketu on 1/7 axis',
            'detail': 'Nodes split the self–partner axis — alliances carry karmic charge, '
                      'sudden formations or dissolutions, and unconventional dynamics.',
        })
        axis_axes_hit.append('1/7')

    # 5/11 axis — creative bonds / networks
    if {rahu_house, ketu_house} == {5, 11}:
        activations.append({
            'name': 'Rahu-Ketu on 5/11 axis',
            'detail': 'Nodes split the creative-bond/network axis — fated friendships, '
                      'unconventional creative partnerships, or boundary-blurring alliances.',
        })
        axis_axes_hit.append('5/11')

    # 3/9 axis — kinship / dharma
    if {rahu_house, ketu_house} == {3, 9}:
        activations.append({
            'name': 'Rahu-Ketu on 3/9 axis',
            'detail': 'Nodes split the kinship/dharma axis — sibling-like bonds outside '
                      'biological family or alliances that test moral frame.',
        })
        axis_axes_hit.append('3/9')

    # Node in target house directly
    target_house = state['target']['house']
    if rahu_house == target_house:
        activations.append({
            'name': f'Rahu in {target_house}{_ordinal_suffix(target_house)}',
            'detail': f'Rahu occupies the target house — alliance dynamics carry '
                      f'amplification, novelty, foreign or unconventional flavour.',
        })
    if ketu_house == target_house:
        activations.append({
            'name': f'Ketu in {target_house}{_ordinal_suffix(target_house)}',
            'detail': f'Ketu occupies the target house — alliance dynamics carry '
                      f'detachment, dissolution, or karmic completion energy.',
        })

    fired = len(activations) > 0

    if not fired:
        narrative = ('Nodes do not activate alliance-relevant axes — relational dynamics '
                     'operate without strong karmic or unconventional pressure.')
    else:
        narrative = (f'Node-axis activation detected: {len(activations)} signature(s). '
                     f'Alliance dynamics carry karmic weight.')

    return {
        'overlay': 'node_axis_activation',
        'fired': fired,
        'data': {
            'activations':     activations,
            'rahu_house':      rahu_house,
            'ketu_house':      ketu_house,
            'axes_hit':        axis_axes_hit,
            'target_house':    target_house,
        },
        'narrative': narrative,
    }


# =================================================================
# PHASE 4D · KINSHIP & ALLIANCES OVERLAYS (Sahaja + Mitra)
# =================================================================
# Dual-target reading: 3L (siblings/co-borns) + 11L (deep networks).
# Aggregates legacy Sahaja and Mitra chapters into one modern frame.

def overlay_alliance_reciprocity_check(chart: Dict, state: Dict, inputs: Dict) -> Dict:
    """
    Dual-house reciprocity check on 3L (siblings) and 11L (alliances/networks).
    Evaluates each lord's house placement, friendship/enmity to Lagna lord
    by Naisargika friendship, and mutual aspect quality.
    """
    planets = chart.get('planets', {})
    lagna_sign = chart.get('lagna_sign', 0)
    lagna_lord = SIGN_LORDS[lagna_sign]
    third_sign = (lagna_sign + 2) % 12
    eleventh_sign = (lagna_sign + 10) % 12
    third_lord = SIGN_LORDS[third_sign]
    eleventh_lord = SIGN_LORDS[eleventh_sign]

    # Naisargika friendships (BPHS Ch.13)
    FRIENDS = {
        'Sun':     {'Moon', 'Mars', 'Jupiter'},
        'Moon':    {'Sun', 'Mercury'},
        'Mars':    {'Sun', 'Moon', 'Jupiter'},
        'Mercury': {'Sun', 'Venus'},
        'Jupiter': {'Sun', 'Moon', 'Mars'},
        'Venus':   {'Mercury', 'Saturn'},
        'Saturn':  {'Mercury', 'Venus'},
    }
    ENEMIES = {
        'Sun':     {'Venus', 'Saturn'},
        'Moon':    set(),
        'Mars':    {'Mercury'},
        'Mercury': {'Moon'},
        'Jupiter': {'Mercury', 'Venus'},
        'Venus':   {'Sun', 'Moon'},
        'Saturn':  {'Sun', 'Moon', 'Mars'},
    }

    def classify(other):
        if other in FRIENDS.get(lagna_lord, set()): return ('friend',  'naisargika friend')
        if other in ENEMIES.get(lagna_lord, set()): return ('enemy',   'naisargika enemy')
        return ('neutral', 'naisargika neutral')

    # Sibling branch (3L)
    third_lord_house = _planet_house(chart, third_lord)
    asp_l1_l3 = pairwise_aspect(lagna_lord, third_lord, chart) if third_lord != lagna_lord else {}
    sibling = {
        'lord':           third_lord,
        'lord_house':     third_lord_house,
        'friendship':     classify(third_lord)[1] if third_lord != lagna_lord else 'self-ruled',
        'aspect_quality': asp_l1_l3.get('yoga') if asp_l1_l3.get('within_orb') else 'no_aspect',
        'is_combust':     _is_combust(planets, third_lord),
    }
    # Sibling verdict
    sibling_score = 0
    if sibling['friendship'] == 'naisargika friend': sibling_score += 2
    elif sibling['friendship'] == 'naisargika neutral': sibling_score += 1
    if sibling['aspect_quality'] == 'Ithesal': sibling_score += 2
    elif sibling['aspect_quality'] == 'Mutthashila': sibling_score += 1
    if sibling['is_combust']: sibling_score -= 2
    if third_lord_house in (1, 3, 5, 9, 10, 11): sibling_score += 1

    sibling['verdict'] = ('supportive' if sibling_score >= 3
                          else 'estranged' if sibling_score <= 0
                          else 'mixed')

    # Network branch (11L)
    eleventh_lord_house = _planet_house(chart, eleventh_lord)
    asp_l1_l11 = pairwise_aspect(lagna_lord, eleventh_lord, chart) if eleventh_lord != lagna_lord else {}
    networks = {
        'lord':           eleventh_lord,
        'lord_house':     eleventh_lord_house,
        'friendship':     classify(eleventh_lord)[1] if eleventh_lord != lagna_lord else 'self-ruled',
        'aspect_quality': asp_l1_l11.get('yoga') if asp_l1_l11.get('within_orb') else 'no_aspect',
        'is_combust':     _is_combust(planets, eleventh_lord),
    }
    network_score = 0
    if networks['friendship'] == 'naisargika friend': network_score += 2
    elif networks['friendship'] == 'naisargika neutral': network_score += 1
    if networks['aspect_quality'] == 'Ithesal': network_score += 2
    elif networks['aspect_quality'] == 'Mutthashila': network_score += 1
    if networks['is_combust']: network_score -= 2
    if eleventh_lord_house in (1, 5, 9, 10, 11): network_score += 1

    networks['verdict'] = ('rewarding' if network_score >= 3
                           else 'depleting' if network_score <= 0
                           else 'mixed')

    narrative = (f'Sibling axis: {sibling["verdict"]} ({third_lord} in {third_lord_house}{_ordinal_suffix(third_lord_house)}). '
                 f'Network axis: {networks["verdict"]} ({eleventh_lord} in {eleventh_lord_house}{_ordinal_suffix(eleventh_lord_house)}).')

    return {
        'overlay': 'alliance_reciprocity_check',
        'fired': True,
        'data': {
            'sibling':  sibling,
            'networks': networks,
            'lagna_lord': lagna_lord,
            'aggregated_verdict': ('strong_support' if sibling['verdict'] == 'supportive' and networks['verdict'] == 'rewarding'
                                   else 'weak_support' if sibling['verdict'] == 'estranged' and networks['verdict'] == 'depleting'
                                   else 'mixed_support'),
        },
        'narrative': narrative,
    }


def overlay_nakta_bridge_relay(chart: Dict, state: Dict, inputs: Dict) -> Dict:
    """
    Indirect-relay reading: checks for Nakta bridge between Lagna lord and
    BOTH 3L (siblings) and 11L (allies) — surfaces intermediary planets
    that mediate kinship/alliance connections.
    """
    lagna_sign = chart.get('lagna_sign', 0)
    lagna_lord = SIGN_LORDS[lagna_sign]
    third_sign = (lagna_sign + 2) % 12
    eleventh_sign = (lagna_sign + 10) % 12
    third_lord = SIGN_LORDS[third_sign]
    eleventh_lord = SIGN_LORDS[eleventh_sign]

    bridge_sibling = detect_nakta(lagna_lord, third_lord, chart) if third_lord != lagna_lord else None
    bridge_network = detect_nakta(lagna_lord, eleventh_lord, chart) if eleventh_lord != lagna_lord else None

    has_sibling_bridge = bool(bridge_sibling and bridge_sibling.get('bridge'))
    has_network_bridge = bool(bridge_network and bridge_network.get('bridge'))

    fired = has_sibling_bridge or has_network_bridge

    if not fired:
        narrative = ('No active Nakta bridges between Lagna lord and the kinship/alliance '
                     'significators — connections, when present, are direct or absent.')
    else:
        parts = []
        if has_sibling_bridge:
            parts.append(f'Sibling axis routed via {bridge_sibling["bridge"]} ({bridge_sibling.get("bridge_role", "intermediary")})')
        if has_network_bridge:
            parts.append(f'Network axis routed via {bridge_network["bridge"]} ({bridge_network.get("bridge_role", "intermediary")})')
        narrative = '; '.join(parts) + '.'

    return {
        'overlay': 'nakta_bridge_relay',
        'fired': fired,
        'data': {
            'sibling_bridge':  bridge_sibling,
            'network_bridge':  bridge_network,
            'lagna_lord':      lagna_lord,
            'third_lord':      third_lord,
            'eleventh_lord':   eleventh_lord,
            'has_sibling_bridge': has_sibling_bridge,
            'has_network_bridge': has_network_bridge,
        },
        'narrative': narrative,
    }


# =================================================================
# PHASE 4D · KARMIKA CONTAINER · KARMA OVERLAYS (Chapter 13)
# =================================================================
# Atul's locked Karma corpus (Part 2.3): 4 IF-THEN overlays operating
# on the Karya success chain output + Tajik aspects + planetary house
# placements. All overlays receive the transformed avasthas dict
# (via state['avasthas']) — see apply_karmika_avastha_transformation.
#
# Verdict pipeline interaction:
#   - rulership_confirmed:    metadata + narrative; no verdict mutation
#                              (base YES from karya is preserved)
#   - subordinate_trajectory: verdict_downgrade YES → CONDITIONAL_SUBORDINATE
#   - abdication_signal:      verdict_substitution forcing ABDICATION_SIGNAL
#                              from any primitive
#   - startup_pivot_crosscheck: verdict_substitution forcing YES + modifier
#                                FOUNDER_TRANSITION (career_pivot_startup intent)
# =================================================================


# Positive Tajik yogas (used by all 4 Karma overlays)
_KARMA_POSITIVE_YOGAS = {'Ithesal', 'Mutthashila', 'Kamboola'}
_KARMA_NEGATIVE_YOGAS = {'Esrapha', 'Manaoo', 'Esrapha (separating)'}

# Supportive aspect houses-from-Lagna (3rd/5th/9th/11th counted as benefic
# placements from L1 for traditional sunlight). 4th/7th/8th/10th/12th
# considered neutral or afflicting in this context.
_SUPPORTIVE_HOUSES_FROM_LAGNA = {3, 5, 9, 11}

# Kendra (1,4,7,10) and Trikona (5,9) — the angular/trinal placements.
_KENDRA_TRIKONA = {1, 4, 5, 7, 9, 10}

# Dusthana houses where authority decays
_DUSTHANA_HOUSES = {6, 8, 12}

# =================================================================
# SAMMANA (Ch 14) · CONSTANTS — Recognition & Honour
# =================================================================

_SAMMANA_TOPICS = {'sammana'}

# Upachaya houses (3, 10, 11) — the houses of growing/maturing affairs.
# Used by Sammana Overlay A: L11 in Kendra OR Upachaya is structurally
# strong for public recognition.
_UPACHAYA_HOUSES = {3, 10, 11}

# Yama Binder midpoint precision orb (per Atul's Gap 4 lock).
_YAMA_BINDER_ORB = 3.5

# Sandhi-band thresholds for Sun's own-light occlusion check
# (kendra_solar_radiance Overlay D condition 3). Sun must NOT be in
# the first or last degree of its sign — neither freshly arrived
# (sadyo-gata) nor at the edge of the abyss (sandhi).
_SUN_SANDHI_LOW  = 1.0
_SUN_SANDHI_HIGH = 29.0

# Sun-cluster orb — Sun's radiance is diluted when ANY other classical
# planet sits within 12° of it. The Sun is busy combusting its companion
# rather than illuminating the throne. (Gap 1, condition 3.)
_SUN_CLUSTER_ORB = 12.0

# Recognition-scope enum mapping (Gap 5 lock). The frontend passes one
# of these four values; the classifier maps each to one of the 2 intents.
_RECOGNITION_SCOPE_TO_INTENT = {
    'INDUSTRY_AWARD':              'industry_award',
    'PEER_ACKNOWLEDGMENT':         'industry_award',
    'INTERNAL_VALIDATION':         'internal_validation',
    'EXECUTIVE_BOARD_RECOGNITION': 'internal_validation',
}

_VALID_RECOGNITION_SCOPES = tuple(_RECOGNITION_SCOPE_TO_INTENT.keys())

# Keyword anchors for fallback classification when recognition_scope
# is not supplied. industry_award covers external/peer/industry signals;
# internal_validation covers boss/board/team internal signals.
_SAMMANA_INDUSTRY_AWARD_KEYWORDS = (
    # Awards / honors / industry recognition
    'award', 'awards', 'industry award', 'won the award', 'win the award',
    'trophy', 'medal', 'honor', 'honour', 'honors', 'honours',
    'fellowship', 'fellow', 'laureate',
    'recognition', 'recognised', 'recognized',
    'prize', 'prizes', 'top award', 'industry recognition',
    # Public/peer-network signals
    'public recognition', 'industry visibility', 'industry standing',
    'peer recognition', 'peer acknowledgment', 'peer acknowledgement',
    'peer praise', 'peer respect', 'peer validation', 'will my peers',
    # Commendation / media
    'commendation', 'media coverage', 'press coverage', 'feature in',
    'profiled in', 'cover story', 'magazine feature',
    # Devanagari
    'पुरस्कार', 'सम्मान', 'मान', 'प्रतिष्ठा',
)

_SAMMANA_INTERNAL_VALIDATION_KEYWORDS = (
    # Boss / board / executive layer
    'boss recognize', 'boss validate', 'boss acknowledg', 'boss\'s validation',
    'board recognize', 'board acknowledg', 'board validate',
    'ceo recognize', 'ceo acknowledg', 'ceo validate',
    'executive recognition', 'executive validation', 'executive board',
    'senior leadership', 'senior management',
    # Internal channels
    'internal recognition', 'internal validation', 'internal acknowledgment',
    'internal award', 'company award', 'company recognition',
    'team recognition', 'team validation',
    'town hall', 'all hands recognition',
    'closed door', 'behind closed doors',
    'private recognition', 'quiet recognition',
    # Devanagari
    'आंतरिक सम्मान', 'भीतर का सम्मान',
)


def classify_sammana_intent(query_text: Optional[str],
                             recognition_scope: Optional[str] = None) -> str:
    """
    Classify a Sammana query into one of 2 sub-intents.

    Precedence:
        1. If recognition_scope enum supplied, use the direct mapping
           (per Atul's Gap 5 lock). This is the AUTHORITATIVE signal —
           the frontend dropdown captures user intent unambiguously.
        2. Else fall back to keyword classification on query_text:
              industry_award  ← award/peer/recognition/honor language
              internal_validation ← boss/board/CEO/executive language
        3. Default: industry_award (the more common Sammana query in practice).

    Returns one of: 'industry_award' | 'internal_validation'.
    """
    if recognition_scope and recognition_scope in _RECOGNITION_SCOPE_TO_INTENT:
        return _RECOGNITION_SCOPE_TO_INTENT[recognition_scope]

    q = (query_text or '').lower()

    # Internal beats industry_award when BOTH match — "boss" wins over generic "recognition"
    if any(kw in q for kw in _SAMMANA_INTERNAL_VALIDATION_KEYWORDS):
        return 'internal_validation'

    if any(kw in q for kw in _SAMMANA_INDUSTRY_AWARD_KEYWORDS):
        return 'industry_award'

    return 'industry_award'  # default


def _karma_supportive_aspect_to_lagna(chart: Dict, planet: str) -> Optional[Dict]:
    """
    Returns aspect dict if `planet` is in a supportive house-count from
    the Prashna Lagna (3/5/9/11), else None.

    Per Atul's Overlay A clause 3 — Sun or Jupiter must "cast a supportive
    aspect" onto the Prashna Lagna. In Tajik horary, support from these
    classical benefics is counted by their house-distance from the Lagna
    rather than full graha-drishti.
    """
    p_house = _planet_house(chart, planet)
    if p_house is None:
        return None
    if p_house in _SUPPORTIVE_HOUSES_FROM_LAGNA:
        return {
            'planet': planet,
            'house_from_lagna': p_house,
            'kind': 'supportive_distance',
            'narrative': (
                f'{planet} occupies the {p_house}th house from the Prashna '
                f'Lagna — classical benefic distance, casting support onto L1.'
            ),
        }
    return None


def overlay_rulership_confirmed(chart: Dict, state: Dict, inputs: Dict) -> Dict:
    """
    Karma Overlay A — Executive Ascent Trigger ("Command Architecture").

    Fires when all three conditions hold:
      1. Karya success chain to the target house (10 for promotion,
         4 for employer pivot) returns success.
      2. The target lord is placed in a Kendra (1/4/7/10) or
         Trikona (5/9) — angular/trinal strength.
      3. Sun OR Jupiter casts a supportive aspect (occupies the
         3rd/5th/9th/11th house) onto the Prashna Lagna.

    Output: fired=True, no verdict mutation (base YES from karya is
    preserved); narrative tags the verdict as 'Command Architecture'.
    """
    target = state['target']
    target_house = target['house']
    target_lord = target['lord']
    karya = state['karya']

    # Condition 1: karya chain success
    karya_succeeds = karya.get('verdict_primitive') in ('success', 'confirmed')
    if not karya_succeeds:
        return _empty_finding('rulership_confirmed')

    # Condition 2: target lord in Kendra or Trikona
    target_lord_house = _planet_house(chart, target_lord)
    in_kendra_trikona = target_lord_house in _KENDRA_TRIKONA

    # Condition 3: Sun OR Jupiter supportive to Lagna
    sun_support  = _karma_supportive_aspect_to_lagna(chart, 'Sun')
    jup_support  = _karma_supportive_aspect_to_lagna(chart, 'Jupiter')
    benefic_support = sun_support or jup_support

    if not (in_kendra_trikona and benefic_support):
        return _empty_finding('rulership_confirmed')

    benefic = benefic_support['planet']
    narrative = (
        f'The throne recognizes your signature. The Karya chain to H{target_house} '
        f"({target['role']}) closes cleanly, the target lord {target_lord} occupies "
        f'a strong angular/trinal house (H{target_lord_house}), and {benefic} '
        f'(classical benefic) casts support onto the Prashna Lagna from H'
        f"{benefic_support['house_from_lagna']}. The authority you are seeking is "
        f'mathematically aligned with your current trajectory; the management layer '
        f'sees you as a natural custodian of power.'
    )

    return {
        'overlay': 'rulership_confirmed',
        'fired': True,
        'synthesis_tag': 'Command Architecture',
        'data': {
            'target_lord': target_lord,
            'target_lord_house': target_lord_house,
            'target_lord_in_kendra_trikona': True,
            'benefic_support': benefic,
            'benefic_support_detail': benefic_support,
            'karya_succeeded': True,
        },
        'narrative': narrative,
    }


def overlay_subordinate_trajectory(chart: Dict, state: Dict, inputs: Dict) -> Dict:
    """
    Karma Overlay B — Glass Ceiling Lock.

    Fires when there is an active Ithesal applying-aspect between L1 and
    L_target, BUT one of the following structural blockers is present:
      a. The target lord is combust (within 6° of the Sun)
      b. The target lord is placed in a Dusthana (6/8/12)
      c. Saturn casts a square (90°) or opposition (180°) aspect onto L1
         (-4 friction penalty)

    Output: fired=True; verdict_downgrade YES → CONDITIONAL_SUBORDINATE.
    """
    lagna_sign = chart.get('lagna_sign', 0)
    lagna_lord = SIGN_LORDS[lagna_sign]
    target = state['target']
    target_lord = target['lord']

    if lagna_lord == target_lord:
        # Self-rule — no Ithesal because no two lords
        return _empty_finding('subordinate_trajectory')

    # Active Ithesal L1↔L_target? Use pairwise_aspect for the Tajik reading.
    # NOTE: in this engine's Tajik model, yoga == 'Ithesal' is by definition
    # the applying configuration (faster planet behind slower); yoga ==
    # 'Esrapha' is the separating configuration. So we don't need to check
    # an extra applying_or_separating key — the yoga name carries the direction.
    asp = pairwise_aspect(lagna_lord, target_lord, chart)
    has_ithesal = (asp.get('within_orb') and asp.get('yoga') == 'Ithesal')

    if not has_ithesal:
        return _empty_finding('subordinate_trajectory')

    # Structural blockers
    blockers = []

    # Blocker (a): target lord combust
    is_combust = _is_combust(chart.get('planets', {}), target_lord)
    if is_combust:
        blockers.append({
            'kind': 'target_combust',
            'narrative': f'{target_lord} is combust by the Sun — burning ambition that cannot crystallize as title.',
        })

    # Blocker (b): target lord in Dusthana (6/8/12)
    target_lord_house = _planet_house(chart, target_lord)
    in_dusthana = target_lord_house in _DUSTHANA_HOUSES
    if in_dusthana:
        blockers.append({
            'kind': 'target_lord_in_dusthana',
            'house': target_lord_house,
            'narrative': (
                f'{target_lord} occupies H{target_lord_house} (Dusthana) — the '
                f'institutional layer denies the formal title even when execution succeeds.'
            ),
        })

    # Blocker (c): Saturn ↔ L1 negative Tajik aspect (-4 friction penalty)
    # In this engine's model, any Saturn-L1 Esrapha (separating within orb) is
    # the mathematical analog of the classical "square/opposition" friction
    # Atul's spec calls out — Saturn's malefic angular pressure on Lagna lord.
    if lagna_lord != 'Saturn':
        saturn_asp_l1 = pairwise_aspect('Saturn', lagna_lord, chart)
        saturn_friction = (saturn_asp_l1.get('within_orb')
                            and saturn_asp_l1.get('yoga') in ('Esrapha',))
        if saturn_friction:
            blockers.append({
                'kind': 'saturn_friction',
                'aspect_yoga': saturn_asp_l1.get('yoga'),
                'absolute_separation': saturn_asp_l1.get('absolute_separation'),
                'narrative': (
                    f'Saturn casts a separating ({saturn_asp_l1.get("yoga")}) '
                    f'aspect on the Lagna lord at '
                    f'{saturn_asp_l1.get("absolute_separation", "?")}° — '
                    f'-4 friction penalty, slowing the ascent.'
                ),
            })

    if not blockers:
        return _empty_finding('subordinate_trajectory')

    blocker_summary = '; '.join(b['narrative'] for b in blockers)
    narrative = (
        f'The capacity to execute is undeniable — the Ithesal between '
        f'{lagna_lord} (L1) and {target_lord} (L{target["house"]}) is applying — '
        f'but your hands remain tied by an invisible institutional ceiling. '
        f'{blocker_summary} You will be handed the responsibility of the role '
        f'without the formal title or matching compensation.'
    )

    return {
        'overlay': 'subordinate_trajectory',
        'fired': True,
        'synthesis_tag': 'Glass Ceiling',
        'verdict_downgrade': {
            'from_states': ['YES', 'YES_WITH_EFFORT'],
            'to': 'CONDITIONAL_SUBORDINATE',
            'reason': 'Subordinate Trajectory overlay — structural blockers on target lord/Lagna',
        },
        'data': {
            'lagna_lord': lagna_lord,
            'target_lord': target_lord,
            'ithesal_active': True,
            'blockers': blockers,
        },
        'narrative': narrative,
    }


def overlay_abdication_signal(chart: Dict, state: Dict, inputs: Dict) -> Dict:
    """
    Karma Overlay C — Termination / Exit Trigger.

    Three independent firing paths:
      Path 1: intent == 'exit_resignation' AND 10th Lord in 12th or 8th
      Path 2: L1 separating from L10 (Eshrapha, outside 12° orb) AND
              10th Lord in 12th or 8th
      Path 3: Rahu conjoins the 10th house cusp within 3.5° precision orb

    Output: fired=True; verdict_substitution forcing ABDICATION_SIGNAL
    from any karya primitive (this overlay overrides positive readings).
    """
    intent = inputs.get('intent', '')
    lagna_sign = chart.get('lagna_sign', 0)
    lagna_lord = SIGN_LORDS[lagna_sign]

    # 10th lord (always evaluated regardless of intent — the throne axis)
    tenth_sign = (lagna_sign + 9) % 12
    tenth_lord = SIGN_LORDS[tenth_sign]
    tenth_lord_house = _planet_house(chart, tenth_lord)
    tenth_lord_in_8_or_12 = tenth_lord_house in (8, 12)

    fired_paths: List[Dict] = []

    # Path 1: exit_resignation intent + L10 in 8 or 12
    if intent == 'exit_resignation' and tenth_lord_in_8_or_12:
        fired_paths.append({
            'path': 'intent_plus_dusthana',
            'narrative': (
                f'The user is explicitly framing a severance question, and '
                f'{tenth_lord} (10th Lord) is placed in H{tenth_lord_house} '
                f"({'loss of status' if tenth_lord_house == 12 else 'sudden collapse'}). "
                f'The exit is structurally confirmed.'
            ),
        })

    # Path 2: L1 ↔ L10 separating Eshrapha outside orb + L10 in 8 or 12
    if lagna_lord != tenth_lord:
        asp_l1_l10 = pairwise_aspect(lagna_lord, tenth_lord, chart)
        l1_separating = (asp_l1_l10.get('applying_or_separating') == 'separating'
                          and asp_l1_l10.get('yoga') in ('Esrapha', 'Esrapha (separating)'))
        # "Outside 12° orb" = orb_used > 12 OR within_orb is False
        outside_orb = (not asp_l1_l10.get('within_orb', False)) or \
                      (asp_l1_l10.get('orb_used', 999) > 12.0)
        if l1_separating and outside_orb and tenth_lord_in_8_or_12:
            fired_paths.append({
                'path': 'eshrapha_outside_orb',
                'narrative': (
                    f'{lagna_lord} (L1) is separating from {tenth_lord} (L10) '
                    f'in Eshrapha outside the 12° orb, AND {tenth_lord} is placed '
                    f'in H{tenth_lord_house}. The chart shows the link to the '
                    f'10th-house authority is already broken; you have walked '
                    f'past the threshold without realizing it.'
                ),
            })

    # Path 3: Rahu within 3.5° of the 10th cusp longitude
    # 10th cusp longitude (whole-sign) = (lagna_sign + 9) * 30 = start of 10th sign
    tenth_cusp_lon = ((lagna_sign + 9) % 12) * 30.0
    rahu_lon = _get_planet_longitude_safe(chart, 'Rahu')
    if rahu_lon is not None:
        # Distance from Rahu to 10th cusp (in degrees, smallest arc)
        diff = abs((rahu_lon - tenth_cusp_lon + 180) % 360 - 180)
        if diff <= 3.5:
            fired_paths.append({
                'path': 'rahu_cusp_conjunction',
                'rahu_longitude': round(rahu_lon, 3),
                'cusp_longitude': round(tenth_cusp_lon, 3),
                'orb_deg': round(diff, 3),
                'narrative': (
                    f'Rahu sits at {round(rahu_lon, 2)}° — only {round(diff, 2)}° '
                    f'from the 10th house cusp ({round(tenth_cusp_lon, 2)}°). '
                    f'Within the 3.5° precision orb, this signals an obsessive '
                    f'destabilization of the position itself; the throne is '
                    f'about to be uprooted.'
                ),
            })

    if not fired_paths:
        return _empty_finding('abdication_signal')

    fired_summary = ' || '.join(f'[{p["path"]}]' for p in fired_paths)
    overall_narrative = (
        f'The chart captures an energy of severance via {len(fired_paths)} '
        f"convergent path{'s' if len(fired_paths) > 1 else ''} ({fired_summary}). "
        f'The current corporate structure cannot hold your weight, and '
        f'attempting to sustain your positioning here will result in an abrupt, '
        f'forced displacement. Prepare your exit runway immediately — the '
        f'decision will be made for you, not by you.'
    )

    return {
        'overlay': 'abdication_signal',
        'fired': True,
        'synthesis_tag': 'Abdication',
        'verdict_substitution': {
            'new_state': 'ABDICATION_SIGNAL',
            'when_primitives': ['success', 'confirmed', 'conditional', 'failure'],
            'reason': 'Abdication Signal overlay fired',
        },
        'data': {
            'lagna_lord':       lagna_lord,
            'tenth_lord':       tenth_lord,
            'tenth_lord_house': tenth_lord_house,
            'fired_paths':      fired_paths,
            'paths_count':      len(fired_paths),
        },
        'narrative': overall_narrative,
    }


def overlay_startup_pivot_crosscheck(chart: Dict, state: Dict, inputs: Dict) -> Dict:
    """
    Karma Overlay D — Founder Transition.

    Fires when ALL four conditions hold AND the query is career_pivot_startup:
      1. Intent == 'career_pivot_startup'
      2. L7 (Business axis) has higher Tajik Strength Scaling than L10 (Job)
      3. L7 forms a positive aspect with L11 (Gains)
      4. L10 is in a Pariheena (weakened) band

    Pariheena = synthesis_label in {Forming Weakness, Brittle Failure,
                                     Thwarted Power, Functional Failure,
                                     Fading Trace, Phantom}.

    Output: fired=True; verdict_substitution forcing YES + modifier_flag
    FOUNDER_TRANSITION.
    """
    intent = inputs.get('intent', '')
    if intent != 'career_pivot_startup':
        return _empty_finding('startup_pivot_crosscheck')

    lagna_sign = chart.get('lagna_sign', 0)
    seventh_sign  = (lagna_sign + 6) % 12   # H7 (business)
    tenth_sign    = (lagna_sign + 9) % 12   # H10 (job)
    eleventh_sign = (lagna_sign + 10) % 12  # H11 (gains)

    seventh_lord  = SIGN_LORDS[seventh_sign]
    tenth_lord    = SIGN_LORDS[tenth_sign]
    eleventh_lord = SIGN_LORDS[eleventh_sign]

    avasthas = state.get('avasthas') or {}
    pariheena_labels = {
        'Forming Weakness', 'Brittle Failure', 'Thwarted Power',
        'Functional Failure', 'Fading Trace', 'Phantom',
        'Forming Mediocrity',
    }

    # Condition 2: L7 has higher strength than L10
    strength = state.get('strength_scaling') or {}
    l7_score = (strength.get('per_planet', {}) or {}).get(seventh_lord, {}).get('score')
    l10_score = (strength.get('per_planet', {}) or {}).get(tenth_lord, {}).get('score')
    if l7_score is None or l10_score is None:
        # Fall back to avastha priority comparison
        l7_pri = (avasthas.get(seventh_lord, {}) or {}).get('priority_index', 99)
        l10_pri = (avasthas.get(tenth_lord, {}) or {}).get('priority_index', 99)
        l7_stronger = l7_pri < l10_pri  # lower priority_index = stronger
        score_basis = 'avastha_priority'
    else:
        l7_stronger = l7_score > l10_score
        score_basis = 'strength_scaling'

    if not l7_stronger:
        return _empty_finding('startup_pivot_crosscheck')

    # Condition 3: L7 ↔ L11 positive aspect
    if seventh_lord == eleventh_lord:
        l7_l11_positive = True
        asp_summary = 'self-rule (L7 IS L11)'
    else:
        asp_7_11 = pairwise_aspect(seventh_lord, eleventh_lord, chart)
        l7_l11_positive = (asp_7_11.get('within_orb')
                            and asp_7_11.get('yoga') in _KARMA_POSITIVE_YOGAS)
        asp_summary = asp_7_11.get('yoga', 'none')

    if not l7_l11_positive:
        return _empty_finding('startup_pivot_crosscheck')

    # Condition 4: L10 in Pariheena band
    l10_label = (avasthas.get(tenth_lord, {}) or {}).get('synthesis_label', '')
    l10_pariheena = l10_label in pariheena_labels

    if not l10_pariheena:
        return _empty_finding('startup_pivot_crosscheck')

    narrative = (
        f'The corporate anchor is dragging. {tenth_lord} (L10 · the Job) shows '
        f'"{l10_label}" — a Pariheena band where the institutional path is '
        f'structurally weak. Meanwhile {seventh_lord} (L7 · the Business axis) '
        f'is stronger ({score_basis}) AND forms a positive {asp_summary} with '
        f'{eleventh_lord} (L11 · Gains). The planetary velocity favors '
        f'independent commercial risk over institutional safety. Shift your '
        f'assets to the 7th axis now — the chart is mathematically endorsing '
        f'the founder transition.'
    )

    return {
        'overlay': 'startup_pivot_crosscheck',
        'fired': True,
        'synthesis_tag': 'Founder Transition',
        'verdict_substitution': {
            'new_state': 'YES',
            'when_primitives': ['success', 'confirmed', 'conditional', 'failure'],
            'reason': 'Startup pivot crosscheck — chart endorses founder transition',
        },
        'verdict_modifier_flag': 'FOUNDER_TRANSITION',
        'data': {
            'seventh_lord':   seventh_lord,
            'tenth_lord':     tenth_lord,
            'eleventh_lord':  eleventh_lord,
            'l7_score':       l7_score,
            'l10_score':      l10_score,
            'score_basis':    score_basis,
            'l7_stronger':    True,
            'l7_l11_aspect':  asp_summary,
            'l10_synthesis_label': l10_label,
            'l10_pariheena':  True,
        },
        'narrative': narrative,
    }


def _get_planet_longitude_safe(chart: Dict, planet_name: str) -> Optional[float]:
    """Compact wrapper around planets dict access — returns longitude or None."""
    p = (chart.get('planets') or {}).get(planet_name) or {}
    lon = p.get('longitude')
    return float(lon) % 360.0 if lon is not None else None


def _supportive_aspect_to_house(chart: Dict, planet: str,
                                  reference_house: int) -> Optional[Dict]:
    """
    Generalized version of `_karma_supportive_aspect_to_lagna`. Returns
    an aspect dict if `planet` occupies a supportive house-distance
    (3/5/9/11) FROM the given `reference_house` (1 for Lagna, 11 for the
    11th cusp, etc), else None.

    Sammana Overlay A uses this with reference_house=11 to test whether
    Jupiter "casts a supportive aspect onto the 11th cusp" — i.e. Jupiter
    sits 3/5/9/11 houses forward from H11. Same helper with reference=1
    reproduces the legacy Karma behaviour (supportive to L1).
    """
    p_house = _planet_house(chart, planet)
    if p_house is None:
        return None

    # Forward house-count from reference: 1-indexed
    house_count_from_ref = ((p_house - reference_house) % 12) + 1

    if house_count_from_ref in _SUPPORTIVE_HOUSES_FROM_LAGNA:
        return {
            'planet': planet,
            'house_from_lagna':     p_house,
            'house_from_reference': house_count_from_ref,
            'reference_house':      reference_house,
            'kind': 'supportive_distance',
            'narrative': (
                f'{planet} occupies the {house_count_from_ref}th house from H'
                f'{reference_house} — classical benefic distance, casting '
                f'support onto H{reference_house}.'
            ),
        }
    return None


# =================================================================
# KARMA · OVERLAY E — Occluded Throne ("Mushita Sovereignty")
# Hotfix per Atul: when L10 reads as luminous (auspicious avastha) but
# combust by Sun while sitting in dusthana, flag the structural darkness
# as a verdict modifier so the narrative engine doesn't miss it.
# =================================================================

def overlay_mushita_sovereignty(chart: Dict, state: Dict, inputs: Dict) -> Dict:
    """
    Karma Overlay E — Occluded Throne ("Mushita Sovereignty").

    Fires when the target lord shows a structurally dark configuration:
      1. Target lord is COMBUST (within combustion orb of the Sun)
      2. Target lord is in DUSTHANA (6/8/12)
      3. Target lord's avastha is AUSPICIOUS (AVASTHA_AUSPICIOUSNESS >= 5
         — i.e. Deepta, Adhiveerya, Mudita, or similarly luminous states)

    Output: verdict_modifier_flag THRONE_OCCLUDED + synthesis_tag
    'Occluded Throne'. Does NOT mutate verdict state — the verdict NO
    already comes from karya failure or downgrade overlays. This
    overlay's job is to label WHY the NO is structural rather than
    tactical, so the narrative tone surfaces the right framing.
    """
    target = state['target']
    target_lord = target['lord']
    planets = chart.get('planets', {})

    # Condition 1: target lord in dusthana
    target_lord_house = _planet_house(chart, target_lord)
    if target_lord_house not in _DUSTHANA_HOUSES:
        return _empty_finding('mushita_sovereignty')

    # Condition 2: target lord is combust by Sun
    if not _is_combust(planets, target_lord):
        return _empty_finding('mushita_sovereignty')

    # Condition 3: target lord's avastha is strongly auspicious
    avasthas = state.get('avasthas') or {}
    target_av = avasthas.get(target_lord, {}) or {}
    avastha_name = target_av.get('avastha', 'Neutral')
    auspiciousness = AVASTHA_AUSPICIOUSNESS.get(avastha_name, 3)
    if auspiciousness < 5:
        return _empty_finding('mushita_sovereignty')

    narrative = (
        f"Mushita Sovereignty — the throne-lord {target_lord} operates under "
        f"solar combustion in H{target_lord_house} (Dusthana). Even with the "
        f"{avastha_name} avastha (auspiciousness {auspiciousness}/7), the chart "
        f"shows the Sun cannibalizing the very lord of the querent's career axis. "
        f"Capacity is real; visibility is occluded; the throne is structurally "
        f"dark within this Prashna horizon."
    )

    return {
        'overlay': 'mushita_sovereignty',
        'fired': True,
        'synthesis_tag': 'Occluded Throne',
        'verdict_modifier_flag': 'THRONE_OCCLUDED',
        'data': {
            'target_lord':            target_lord,
            'target_lord_house':      target_lord_house,
            'target_lord_combust':    True,
            'target_lord_avastha':    avastha_name,
            'avastha_auspiciousness': auspiciousness,
        },
        'narrative': narrative,
    }


# =================================================================
# SAMMANA (Ch 14) · 6 OVERLAYS — Recognition & Honour
# =================================================================

def overlay_accolade_materialization(chart: Dict, state: Dict, inputs: Dict) -> Dict:
    """
    Sammana Overlay A — Radiant Validation (Gap 1 spec lock).

    Conditions:
      1. karya_success_chain(target=11) succeeds
      2. L11 in Kendra (1/4/7/10), Trikona (5/9), OR Upachaya (3/10/11)
      3. Jupiter casts a supportive aspect (in H3/5/9/11) onto L1
         OR onto the 11th cusp

    Output: verdict_substitution → YES; synthesis_tag 'Radiant Validation'.
    Fires only for the H11 target (industry_award route).
    """
    target = state['target']
    if target['house'] != 11:
        return _empty_finding('accolade_materialization')

    karya = state['karya']
    if karya.get('verdict_primitive') not in ('success', 'confirmed'):
        return _empty_finding('accolade_materialization')

    l11_lord = target['lord']
    l11_lord_house = _planet_house(chart, l11_lord)
    in_kendra_trikona = l11_lord_house in _KENDRA_TRIKONA
    in_upachaya = l11_lord_house in _UPACHAYA_HOUSES
    if not (in_kendra_trikona or in_upachaya):
        return _empty_finding('accolade_materialization')

    jup_to_l1  = _supportive_aspect_to_house(chart, 'Jupiter', 1)
    jup_to_h11 = _supportive_aspect_to_house(chart, 'Jupiter', 11)
    jup_support = jup_to_l1 or jup_to_h11
    if not jup_support:
        return _empty_finding('accolade_materialization')

    placement_kind = (
        'Kendra/Trikona' if in_kendra_trikona else 'Upachaya'
    )
    target_label = "L1 (Lagna)" if jup_to_l1 else "the 11th cusp"

    narrative = (
        f"The public architecture is completely clear. The industry validation, "
        f"award, or formal commendation you are tracking is mathematically pulling "
        f"toward you. The 11th lord {l11_lord} sits in H{l11_lord_house} "
        f"({placement_kind} — a structurally favourable house), the karya chain to "
        f"H11 closes cleanly, and Jupiter (honor-karaka) casts a supportive aspect "
        f"({jup_support.get('house_from_reference')}th from {target_label}). Your "
        f"signature has broken through the noise; the wider ecosystem is prepared "
        f"to acknowledge your contribution on record."
    )

    return {
        'overlay': 'accolade_materialization',
        'fired': True,
        'synthesis_tag': 'Radiant Validation',
        'verdict_substitution': {
            'when_primitives': ['success', 'confirmed', 'conditional'],
            'new_state':       'YES',
            'reason':          'Accolade Materialization — full architecture for public recognition',
        },
        'data': {
            'l11_lord':                       l11_lord,
            'l11_lord_house':                 l11_lord_house,
            'l11_placement_kind':             placement_kind,
            'jupiter_support_target':         'l1' if jup_to_l1 else 'h11',
            'jupiter_house_from_reference':   jup_support.get('house_from_reference'),
        },
        'narrative': narrative,
    }


def overlay_credit_theft_check(chart: Dict, state: Dict, inputs: Dict) -> Dict:
    """
    Sammana Overlay B — Obscured Validation (credit-theft pattern).

    Three independent firing paths per spec:
      Path 1 (L1_L11_dusthana): L1↔L11 Ithesal within orb AND L11 in H12 or H6
      Path 2 (L1_L10_dusthana): L1↔L10 Ithesal within orb AND L10 in H12 or H6
      Path 3 (L7_yama_binds_L1_L11): L7 (manager) Yama-binds the L1↔L11 arc
                                      within a 3.5° midpoint orb (Gap 4 lock)

    Output: verdict_substitution → OBSCURED_VALIDATION.
    """
    lagna_sign = chart.get('lagna_sign', 0)
    lagna_lord = SIGN_LORDS[lagna_sign]
    l7_lord    = SIGN_LORDS[(lagna_sign + 6)  % 12]
    l10_lord   = SIGN_LORDS[(lagna_sign + 9)  % 12]
    l11_lord   = SIGN_LORDS[(lagna_sign + 10) % 12]

    fired_paths: List[Dict] = []

    # Path 1: L1↔L11 Ithesal + L11 in H12/H6
    if lagna_lord != l11_lord:
        asp_111 = pairwise_aspect(lagna_lord, l11_lord, chart)
        if asp_111.get('within_orb') and asp_111.get('yoga') == 'Ithesal':
            l11_house = _planet_house(chart, l11_lord)
            if l11_house in (12, 6):
                fired_paths.append({
                    'path': 'L1_L11_dusthana',
                    'l11_lord':  l11_lord,
                    'l11_house': l11_house,
                    'aspect_orb': asp_111.get('absolute_separation'),
                    'narrative': (f"L1↔L11 Ithesal active, but L11 ({l11_lord}) sits "
                                  f"in H{l11_house}."),
                })

    # Path 2: L1↔L10 Ithesal + L10 in H12/H6
    if lagna_lord != l10_lord:
        asp_110 = pairwise_aspect(lagna_lord, l10_lord, chart)
        if asp_110.get('within_orb') and asp_110.get('yoga') == 'Ithesal':
            l10_house = _planet_house(chart, l10_lord)
            if l10_house in (12, 6):
                fired_paths.append({
                    'path': 'L1_L10_dusthana',
                    'l10_lord':  l10_lord,
                    'l10_house': l10_house,
                    'aspect_orb': asp_110.get('absolute_separation'),
                    'narrative': (f"L1↔L10 Ithesal active, but L10 ({l10_lord}) sits "
                                  f"in H{l10_house}."),
                })

    # Path 3: L7 Yama-binds L1↔L11
    if len({lagna_lord, l7_lord, l11_lord}) == 3:
        yama = is_yama_binder(lagna_lord, l7_lord, l11_lord, chart,
                              midpoint_orb=_YAMA_BINDER_ORB)
        if yama.get('is_binder'):
            fired_paths.append({
                'path': 'L7_yama_binds_L1_L11',
                'l7_lord': l7_lord,
                'midpoint_longitude': yama.get('midpoint_longitude'),
                'distance_from_midpoint': yama.get('distance_from_midpoint'),
                'narrative': yama.get('narrative'),
            })

    if not fired_paths:
        return _empty_finding('credit_theft_check')

    path_summary = ' · '.join(p['narrative'] for p in fired_paths)
    narrative = (
        f"The energy of validation exists, but it carries a signature of "
        f"occlusion. {path_summary} An institutional intermediary — most likely "
        f"a reporting manager or internal stakeholder — is positioned to "
        f"intercept the light. Your output will be leveraged to validate "
        f"their standing, leaving your recognition obscured behind the scenes. "
        f"Secure your public receipts immediately."
    )

    return {
        'overlay': 'credit_theft_check',
        'fired': True,
        'synthesis_tag': 'Obscured Validation',
        'verdict_substitution': {
            'when_primitives': ['success', 'conditional', 'confirmed'],
            'new_state':       'OBSCURED_VALIDATION',
            'reason':          'Credit Theft pattern — L11/L10 occluded or L7 Yama-binds the arc',
        },
        'data': {
            'fired_paths':       [p['path'] for p in fired_paths],
            'firing_path_count': len(fired_paths),
            'path_details':      fired_paths,
        },
        'narrative': narrative,
    }


def overlay_peer_envy_scan(chart: Dict, state: Dict, inputs: Dict) -> Dict:
    """
    Sammana Overlay C — Peer Envy (friction trigger).

    Conditions:
      1. karya_success_chain indicates success (primitive 'success' or 'confirmed')
      2. Mars OR Ketu casts a square (~90° ± 8° orb) or opposition (~180° ± 8° orb)
         onto L11 — the inimical Shatru-drishti

    Output: verdict_substitution → YES_WITH_FRICTION.
    """
    if state['karya'].get('verdict_primitive') not in ('success', 'confirmed'):
        return _empty_finding('peer_envy_scan')

    lagna_sign = chart.get('lagna_sign', 0)
    l11_lord = SIGN_LORDS[(lagna_sign + 10) % 12]
    planets = chart.get('planets', {})
    l11_lon = (planets.get(l11_lord) or {}).get('longitude')
    if l11_lon is None:
        return _empty_finding('peer_envy_scan')

    afflictors: List[Dict] = []
    for malefic in ('Mars', 'Ketu'):
        m_lon = (planets.get(malefic) or {}).get('longitude')
        if m_lon is None:
            continue
        # Shortest separation around the zodiac
        raw_sep = abs(m_lon - l11_lon)
        sep = min(raw_sep, 360.0 - raw_sep)
        for angle, label in ((90.0, 'square'), (180.0, 'opposition')):
            if abs(sep - angle) <= 8.0:
                afflictors.append({
                    'malefic':           malefic,
                    'aspect':            label,
                    'target':            f'L11 ({l11_lord})',
                    'angular_sep_deg':   round(sep, 2),
                })
                break

    if not afflictors:
        return _empty_finding('peer_envy_scan')

    summary = '; '.join(f"{a['malefic']} {a['aspect']} {a['target']} ({a['angular_sep_deg']}°)"
                        for a in afflictors)

    narrative = (
        f"The accolade will land, but it will not arrive clean. The chart warns "
        f"of sharp undercurrents of professional envy (Shatru-Drishti) within "
        f"your peer circle: {summary}. The applause will be public, but the "
        f"immediate consequence will be a tightening of political friction from "
        f"lateral colleagues. Step into the recognition with clinical poise — "
        f"do not expect universal celebration."
    )

    return {
        'overlay': 'peer_envy_scan',
        'fired': True,
        'synthesis_tag': 'Peer Envy',
        'verdict_substitution': {
            'when_primitives': ['success', 'confirmed'],
            'new_state':       'YES_WITH_FRICTION',
            'reason':          'Mars/Ketu inimical aspect on L11 — peer envy',
        },
        'data': {
            'afflictors':       afflictors,
            'afflictor_count':  len(afflictors),
        },
        'narrative': narrative,
    }


def overlay_kendra_solar_radiance(chart: Dict, state: Dict, inputs: Dict) -> Dict:
    """
    Sammana Overlay D — Solar Radiance (Gap 1 spec lock).

    Conditions (all four required):
      1. karya_success_chain(target=10) succeeds
      2. Sun occupies a Kendra house (1, 4, 7, 10) from Lagna
      3. Sun's own light is clear:
         - degree-in-sign in (1°, 29°) — not sadyo-gata or sandhi
         - no other classical planet within 12° of Sun (cluster check)
      4. L10 in Kendra/Trikona (1/4/5/7/9/10)

    Output: verdict_substitution → YES; synthesis_tag 'Solar Radiance'.
    Fires only for the H10 target (internal_validation route).
    """
    target = state['target']
    if target['house'] != 10:
        return _empty_finding('kendra_solar_radiance')

    karya = state['karya']
    if karya.get('verdict_primitive') not in ('success', 'confirmed'):
        return _empty_finding('kendra_solar_radiance')

    sun_house = _planet_house(chart, 'Sun')
    if sun_house not in (1, 4, 7, 10):
        return _empty_finding('kendra_solar_radiance')

    planets = chart.get('planets', {})
    sun_lon = (planets.get('Sun') or {}).get('longitude')
    if sun_lon is None:
        return _empty_finding('kendra_solar_radiance')

    sun_deg_in_sign = sun_lon % 30.0
    if sun_deg_in_sign < _SUN_SANDHI_LOW or sun_deg_in_sign > _SUN_SANDHI_HIGH:
        return _empty_finding('kendra_solar_radiance')

    # Cluster check — no other classical planet within 12° of Sun
    sun_cluster_companions: List[Dict] = []
    for other in ('Moon', 'Mars', 'Mercury', 'Jupiter', 'Venus', 'Saturn'):
        o_lon = (planets.get(other) or {}).get('longitude')
        if o_lon is None:
            continue
        raw_sep = abs(o_lon - sun_lon)
        sep = min(raw_sep, 360.0 - raw_sep)
        if sep <= _SUN_CLUSTER_ORB:
            sun_cluster_companions.append({
                'planet': other,
                'separation_deg': round(sep, 2),
            })
    if sun_cluster_companions:
        return _empty_finding('kendra_solar_radiance')

    l10_lord = target['lord']
    l10_lord_house = _planet_house(chart, l10_lord)
    if l10_lord_house not in _KENDRA_TRIKONA:
        return _empty_finding('kendra_solar_radiance')

    narrative = (
        f"The vertical axis of corporate authority is fully illuminated. Sun "
        f"sits in H{sun_house} (Kendra) at {sun_deg_in_sign:.1f}° — alone in "
        f"its sign-arc, radiating without combustion or cluster-dilution. The "
        f"10th lord {l10_lord} occupies H{l10_lord_house} (Kendra/Trikona — "
        f"angular/trinal strength). The sovereign layer of leadership — your "
        f"board, your CEO, your executive stakeholders — is paying direct "
        f"attention to your trajectory. Solar radiance confirms that your "
        f"validation is verified at the highest tier of corporate power."
    )

    return {
        'overlay': 'kendra_solar_radiance',
        'fired': True,
        'synthesis_tag': 'Solar Radiance',
        'verdict_substitution': {
            'when_primitives': ['success', 'confirmed', 'conditional'],
            'new_state':       'YES',
            'reason':          'Solar Radiance — Sun in Kendra alone + L10 angular + karya success',
        },
        'data': {
            'sun_house':        sun_house,
            'sun_deg_in_sign':  round(sun_deg_in_sign, 2),
            'l10_lord':         l10_lord,
            'l10_lord_house':   l10_lord_house,
        },
        'narrative': narrative,
    }


def overlay_peer_recognition_axis(chart: Dict, state: Dict, inputs: Dict) -> Dict:
    """
    Sammana Overlay E — Peer Recognition Axis (Gap 2 lock — Option B).

    Modifier-flag overlay. Does NOT mutate the verdict state; produces
    a verdict_modifier_flag based on the L3↔L11 Tajik aspect:
      Ithesal applying  → PUBLIC_COMMENDATION
      Esrapha separating → MUTED_RECEPTION

    L3 = commendation channel (media, written praise). L11 = public arena.
    Their coupling determines whether the announcement carries fanfare or
    arrives muted.
    """
    lagna_sign = chart.get('lagna_sign', 0)
    l3_lord  = SIGN_LORDS[(lagna_sign + 2)  % 12]
    l11_lord = SIGN_LORDS[(lagna_sign + 10) % 12]

    if l3_lord == l11_lord:
        return _empty_finding('peer_recognition_axis')

    asp = pairwise_aspect(l3_lord, l11_lord, chart)
    if not asp.get('within_orb'):
        return _empty_finding('peer_recognition_axis')

    yoga = asp.get('yoga')
    if yoga == 'Ithesal':
        flag = 'PUBLIC_COMMENDATION'
        synthesis = 'Public Commendation'
        narrative = (
            f"L3↔L11 Ithesal: the commendation channel ({l3_lord} — media, "
            f"written praise) is actively coupling with the public arena "
            f"({l11_lord}). Recognition will arrive with maximum public "
            f"visibility and industry-wide fanfare. Aspect orb: "
            f"{asp.get('absolute_separation')}°."
        )
    elif yoga == 'Esrapha':
        flag = 'MUTED_RECEPTION'
        synthesis = 'Muted Reception'
        narrative = (
            f"L3↔L11 Esrapha (separating): the commendation channel ({l3_lord}) "
            f"and the public arena ({l11_lord}) are decoupling. You may win "
            f"the recognition, but the announcement will be handled poorly or "
            f"lack systemic visibility. Aspect orb: "
            f"{asp.get('absolute_separation')}°."
        )
    else:
        return _empty_finding('peer_recognition_axis')

    return {
        'overlay': 'peer_recognition_axis',
        'fired': True,
        'synthesis_tag':         synthesis,
        'verdict_modifier_flag': flag,
        'data': {
            'l3_lord':              l3_lord,
            'l11_lord':             l11_lord,
            'l3_l11_yoga':          yoga,
            'absolute_separation':  asp.get('absolute_separation'),
        },
        'narrative': narrative,
    }


_NEECHA_SIGNS = {
    'Sun': 6,      # Libra
    'Moon': 7,     # Scorpio
    'Mars': 3,     # Cancer
    'Mercury': 11, # Pisces
    'Jupiter': 9,  # Capricorn
    'Venus': 5,    # Virgo
    'Saturn': 0,   # Aries
}


def overlay_executive_privy_lock(chart: Dict, state: Dict, inputs: Dict) -> Dict:
    """
    Sammana Overlay F — Closed-Door Recognition (Gap 3 spec lock).

    Conditions:
      1. karya primitive is 'success', 'conditional', or 'confirmed'
      2. L10 strong: in Kendra/Trikona (1/4/5/7/9/10) AND positive aspect
         with L1 (applying Ithesal within orb, OR L10==L1 = self-rule)
      3. L11 compromised: in Dusthana (6/8/12) OR Neecha (sign of debility)

    Output: verdict_substitution → CONDITIONAL_PRIVY.
    """
    karya = state['karya']
    if karya.get('verdict_primitive') not in ('success', 'conditional', 'confirmed'):
        return _empty_finding('executive_privy_lock')

    lagna_sign = chart.get('lagna_sign', 0)
    lagna_lord = SIGN_LORDS[lagna_sign]
    l10_lord   = SIGN_LORDS[(lagna_sign + 9)  % 12]
    l11_lord   = SIGN_LORDS[(lagna_sign + 10) % 12]

    # Condition 2a: L10 in Kendra/Trikona
    l10_house = _planet_house(chart, l10_lord)
    if l10_house not in _KENDRA_TRIKONA:
        return _empty_finding('executive_privy_lock')

    # Condition 2b: L10 positive Tajik aspect with L1 (self-rule counts as full coupling).
    # Per Atul's spec, "positive aspect" is the full positive Tajik family —
    # _KARMA_POSITIVE_YOGAS = {Ithesal, Mutthashila, Kamboola}. Prior version
    # gated on Ithesal only, which caused the overlay to stay silent when
    # the coupling came through Mutthashila or Kamboola — surfacing a
    # CONDITIONAL_PRIVY verdict via verdict_remap with no overlay attribution.
    if lagna_lord == l10_lord:
        l10_l1_coupled = True
        coupling_kind = 'self_rule'
        coupling_orb = None
        coupling_yoga = None
    else:
        asp = pairwise_aspect(lagna_lord, l10_lord, chart)
        asp_yoga = asp.get('yoga')
        l10_l1_coupled = bool(asp.get('within_orb') and asp_yoga in _KARMA_POSITIVE_YOGAS)
        coupling_kind = 'positive_tajik_yoga' if l10_l1_coupled else None
        coupling_orb = asp.get('absolute_separation') if l10_l1_coupled else None
        coupling_yoga = asp_yoga if l10_l1_coupled else None

    if not l10_l1_coupled:
        return _empty_finding('executive_privy_lock')

    # Condition 3: L11 compromised — dusthana OR Neecha
    l11_house = _planet_house(chart, l11_lord)
    l11_sign  = (chart.get('planets', {}).get(l11_lord, {}) or {}).get('sign_index')

    l11_in_dusthana = l11_house in _DUSTHANA_HOUSES
    l11_neecha = l11_sign is not None and l11_sign == _NEECHA_SIGNS.get(l11_lord)

    if not (l11_in_dusthana or l11_neecha):
        return _empty_finding('executive_privy_lock')

    compromise_parts: List[str] = []
    if l11_in_dusthana:
        compromise_parts.append(f"L11 ({l11_lord}) sits in H{l11_house} (Dusthana)")
    if l11_neecha:
        compromise_parts.append(f"L11 ({l11_lord}) is Neecha (debilitated in sign {l11_sign})")
    compromise_reason = ' AND '.join(compromise_parts)

    narrative = (
        f"The validation is real, but its echo is strictly restricted. The "
        f"executive layer ({l10_lord}) is fully engaged — sitting in H{l10_house} "
        f"(Kendra/Trikona) and coupling with your Lagna lord "
        f"({coupling_kind}{(' via ' + coupling_yoga) if coupling_yoga else ''}). "
        f"But {compromise_reason}. "
        f"The decision-makers recognize and reward your contribution behind closed "
        f"doors, but the organizational grid prevents this validation from "
        f"becoming a matter of public record or lateral peer praise. You hold "
        f"private equity of status, not public currency."
    )

    return {
        'overlay': 'executive_privy_lock',
        'fired': True,
        'synthesis_tag': 'Closed-Door Recognition',
        'verdict_substitution': {
            'when_primitives': ['success', 'conditional', 'confirmed'],
            'new_state':       'CONDITIONAL_PRIVY',
            'reason':          'L10 strong + L11 compromised — private-only recognition',
        },
        'data': {
            'l10_lord':                  l10_lord,
            'l10_lord_house':            l10_house,
            'l10_l1_coupling_kind':      coupling_kind,
            'l10_l1_coupling_yoga':      coupling_yoga,
            'l10_l1_coupling_orb':       coupling_orb,
            'l11_lord':                  l11_lord,
            'l11_lord_house':            l11_house,
            'l11_in_dusthana':           l11_in_dusthana,
            'l11_neecha':                l11_neecha,
            'compromise_reason':         compromise_reason,
        },
        'narrative': narrative,
    }


# =================================================================
# OVERLAY REGISTRY
# =================================================================

OVERLAY_REGISTRY: Dict[str, Callable] = {
    # Garbha overlays
    'lineage_query_check':       overlay_lineage_query_check,
    'husband_pivot_auto':        overlay_husband_pivot_auto,
    'beeja_kshetra_sphuta':      overlay_beeja_kshetra_sphuta,
    'mars_5_vitality_split':     overlay_mars_5_vitality_split,
    'sterile_sign_downgrade':    overlay_sterile_sign_downgrade,
    'rahu_ketu_progeny_axis':    overlay_rahu_ketu_progeny_axis,
    'inconclusive_check':        overlay_inconclusive_check,
    # Shared overlays
    'sincerity_option_c':        overlay_sincerity_option_c,
    'nakta_abhara_scan':         overlay_nakta_abhara_scan,
    'kamboola_yoga':             overlay_kamboola_yoga,
    'gada_yoga':                 overlay_gada_yoga,
    'eclipse_proximity_axis':    overlay_eclipse_proximity_axis,
    # Vivaha overlays
    'third_party_interference':  overlay_third_party_interference,
    'emotional_reciprocity':     overlay_emotional_reciprocity,
    # Phase 4D · Putra overlays
    'putra_yoga_catalogue':      overlay_putra_yoga_catalogue,
    'saptamsha_varga_anchor':    overlay_saptamsha_varga_anchor,
    # Phase 4D · Putra · child_development_health route overlays
    'child_wellbeing_scan':           overlay_child_wellbeing_scan,
    'mercury_speech_affliction_check': overlay_mercury_speech_affliction_check,
    # Phase 4D-EXT · Putra · child_acute_illness, runaway, custody overlays
    'child_illness_scan':              overlay_child_illness_scan,
    'runaway_aagaman_check':           overlay_runaway_aagaman_check,
    'custody_ithasala_competition':    overlay_custody_ithasala_competition,
    # Phase 4D · Anya-Sambandha overlays
    'secret_aspect_scan':        overlay_secret_aspect_scan,
    'node_axis_activation':      overlay_node_axis_activation,
    # Phase 4D · Kinship & Alliances overlays
    'alliance_reciprocity_check': overlay_alliance_reciprocity_check,
    'nakta_bridge_relay':        overlay_nakta_bridge_relay,
    # Phase 4D · Karmika & Yaatra · Karma (Ch 13) overlays
    'rulership_confirmed':       overlay_rulership_confirmed,
    'subordinate_trajectory':    overlay_subordinate_trajectory,
    'abdication_signal':         overlay_abdication_signal,
    'startup_pivot_crosscheck':  overlay_startup_pivot_crosscheck,
    'mushita_sovereignty':       overlay_mushita_sovereignty,
    # Phase 4D · Karmika & Yaatra · Sammana (Ch 14) overlays
    'accolade_materialization':  overlay_accolade_materialization,
    'credit_theft_check':        overlay_credit_theft_check,
    'peer_envy_scan':            overlay_peer_envy_scan,
    'kendra_solar_radiance':     overlay_kendra_solar_radiance,
    'peer_recognition_axis':     overlay_peer_recognition_axis,
    'executive_privy_lock':      overlay_executive_privy_lock,
}


# =================================================================
# INPUT VALIDATION
# =================================================================

def _validate_inputs(spec: Dict, inputs: Dict) -> None:
    """Raise ValueError if required inputs are missing."""
    missing = [k for k in spec.get('required_inputs', []) if inputs.get(k) is None]
    if missing:
        raise ValueError(
            f"Topic '{spec.get('display_name')}' missing required inputs: {missing}"
        )


# =================================================================
# MUTATION HANDLER — applies findings to state with phase ordering
# =================================================================

def _apply_finding_immediate(finding: Dict, state: Dict) -> None:
    """
    Apply mutations that must be visible to subsequent overlays:
      - target_override (re-resolves karya + bhava)
      - sincerity_modifier (cap applied immediately)
      - bhava_bonus (additive, immediate)

    Deferred mutations (bhava_cap, verdict influences, modifier flags)
    are collected into state['pending_*'] and applied in _finalize_state().
    """
    if not finding.get('fired'):
        return

    # --- target_override: rewrites target house immediately ---
    to = finding.get('target_override')
    if to is not None:
        new_house = to['house']
        if new_house != state['target']['house']:
            lagna_sign = state['chart'].get('lagna_sign', 0)
            target_sign = (lagna_sign + new_house - 1) % 12
            state['target'] = {
                'house': new_house,
                'role':  to['role'],
                'sign_index': target_sign,
                'lord': SIGN_LORDS[target_sign],
                'override_reason': to.get('reason'),
            }
            # Recompute karya + bhava bala on the resolved target
            state['karya'] = karya_success_chain(state['chart'], new_house)
            state['bhava'] = compute_bhava_bala(state['chart'], new_house)
            state['bhava_net'] = state['bhava'].get('net_strength_pct', 0)

    # --- sincerity_modifier: cap applied immediately ---
    sm = finding.get('sincerity_modifier')
    if sm is not None:
        cap = sm.get('cap')
        if cap is not None and state['sincerity']['score'] > cap:
            state['sincerity']['score'] = cap
            state['sincerity']['eclipse_capped'] = True
            state['sincerity']['triggers_insincere'].append(
                f"{sm.get('reason')} — sincerity hard-capped at {cap}/100."
            )

    # --- bhava_bonus: additive, immediate ---
    bb = finding.get('bhava_bonus')
    if bb is not None and bb['house'] == state['target']['house']:
        new_pct = min(100, state['bhava_net'] + bb['pct'])
        state['bhava_net'] = new_pct
        state['bhava']['net_strength_pct'] = new_pct
        state['bhava']['sphuta_bonus_applied'] = True

    # --- Collect deferred mutations ---
    if finding.get('bhava_cap'):
        state['pending_caps'].append(finding['bhava_cap'])
    if finding.get('verdict_substitution'):
        state['pending_substitutions'].append(finding['verdict_substitution'])
    if finding.get('verdict_promotion_to'):
        state['pending_promotions'].append(finding['verdict_promotion_to'])
    if finding.get('verdict_downgrade'):
        state['pending_downgrades'].append(finding['verdict_downgrade'])
    if finding.get('verdict_modifier_flag'):
        state['pending_modifier_flags'].append(finding['verdict_modifier_flag'])


def _finalize_state(state: Dict) -> None:
    """
    Apply deferred mutations:
      - Bhava caps (clamping, last — Atul's "caps over bonuses" rule)
    Verdict synthesis happens separately in _synthesize_verdict.
    """
    target_house = state['target']['house']
    for cap in state['pending_caps']:
        if cap['house'] == target_house:
            current = state['bhava_net']
            cap_pct = cap['pct']
            if current > cap_pct:
                state['bhava_net'] = cap_pct
                state['bhava']['net_strength_pct'] = cap_pct
                state['bhava']['sphuta_cap_applied'] = True
                state['bhava']['cap_reason'] = cap.get('reason')


# =================================================================
# VERDICT SYNTHESIS
# =================================================================
# Priority hierarchy (independent of overlay declaration order):
#   1. verdict_modifier_flag (INCONCLUSIVE)  — orthogonal, doesn't override
#   2. verdict_promotion_to (HIGH_RISK)      — highest severity always wins
#   3. verdict_substitution (Kamboola/Gada/Ketu) — applies if primitive matches
#   4. Base primitive from karya chain mapped to topic's verdict_states
#   5. verdict_downgrade (YES → YES_WITH_DELAYS for sterile cusp)
# =================================================================

# Base verdict text templates per state
_VERDICT_TEXTS = {
    'YES':                   'Yes — outcome indicated within the Prashna horizon',
    'YES_WITH_DELAYS':       'Yes — with initial delays or circumstantial support required',
    'YES_WITH_EFFORT':       'Yes — advancement secured only after heavy negotiation or structural changes',
    'YES_WITH_FRICTION':     ('Yes — recognition arrives, but accompanied by peer envy, '
                              'procedural friction, or political turbulence'),
    'CONDITIONAL':           'Conditional — depends on circumstantial support',
    'CONDITIONAL_MEDICAL':   ('Conditional — assisted intervention (IVF / IUI / surrogacy) '
                              'is the indicated path'),
    'CONDITIONAL_THIRD_PARTY': 'Conditional — only via intermediary or alternative path',
    'CONDITIONAL_SUBORDINATE': ('Conditional — no immediate elevation; the trajectory remains '
                                'bound to a subordinate execution layer'),
    'CONDITIONAL_PRIVY':     ('Conditional — recognition granted internally behind closed doors, '
                              'but hidden from public or wider organizational record'),
    'OBSCURED_VALIDATION':   ('Credit absorbed — your contribution is captured silently by a '
                              'reporting superior or institutional intermediary, without public acclaim'),
    'HIGH_RISK':             'Yes — but with significant risk; medical monitoring essential',
    'ABDICATION_SIGNAL':     ('Forced exit — sudden loss of authority, resignation, '
                              'or displacement from the current position'),
    'NO':                    'No — outcome not indicated within the Prashna horizon',
}

# Verdict severity for promotion ordering (higher number = more severe)
_VERDICT_SEVERITY = {
    'YES': 1,
    'YES_WITH_DELAYS': 2, 'YES_WITH_EFFORT': 2,
    'YES_WITH_FRICTION': 2,    # Sammana — recognition with friction
    'CONDITIONAL': 3,
    'CONDITIONAL_PRIVY': 3,    # Sammana — private recognition
    'CONDITIONAL_MEDICAL': 4, 'CONDITIONAL_THIRD_PARTY': 4,
    'CONDITIONAL_SUBORDINATE': 4,
    'OBSCURED_VALIDATION': 4,  # Sammana — credit theft (severe but not absolute denial)
    'NO': 5,
    'HIGH_RISK': 6,
    'ABDICATION_SIGNAL': 7,   # Karma-specific: forced exit > simple NO
}


def _synthesize_verdict(state: Dict, spec: Dict) -> Dict:
    """
    Resolve the final verdict from the karya chain primitive + all collected
    overlay influences, constrained to spec['verdict_states'].
    """
    karya = state['karya']
    primitive = karya['verdict_primitive']
    modifier = karya['verdict_modifier']
    allowed_states = set(spec['verdict_states'])

    # --- Step 1: Map primitive to base state ---
    if primitive == 'failure':
        base = 'NO'
    elif primitive == 'conditional':
        # Allow the natural 'CONDITIONAL' vocabulary to flow ONLY when the
        # topic either (a) accepts CONDITIONAL directly in allowed_states
        # (e.g. Vivaha), or (b) provides a verdict_remap entry for CONDITIONAL
        # (e.g. Karma → CONDITIONAL_SUBORDINATE). For topics that do neither
        # — notably Garbha, which keeps CONDITIONAL out of allowed_states and
        # relies on overlay SUBSTITUTION to refine YES_WITH_DELAYS into
        # CONDITIONAL_MEDICAL / CONDITIONAL_THIRD_PARTY — preserve the
        # historic fallback to YES_WITH_DELAYS so the overlay substitution
        # paths remain reachable.
        #
        # Previously this line short-circuited unconditionally to
        # YES_WITH_DELAYS when CONDITIONAL wasn't in allowed_states, which
        # caused Karma to mis-render conditional primitives as YES_WITH_EFFORT
        # (the verdict_remap then mapped YES_WITH_DELAYS → YES_WITH_EFFORT
        # and the intended CONDITIONAL → CONDITIONAL_SUBORDINATE path was
        # never seen).
        _remap = spec.get('verdict_remap') or {}
        if 'CONDITIONAL' in allowed_states or 'CONDITIONAL' in _remap:
            base = 'CONDITIONAL'
        else:
            base = 'YES_WITH_DELAYS'
    elif primitive == 'success' and modifier == 'with_delays':
        base = 'YES_WITH_DELAYS'
    elif primitive in ('success', 'confirmed'):
        base = 'YES'
    else:
        base = 'YES_WITH_DELAYS'

    # --- Step 1b: Topic-level verdict remap ---
    # Some containers (Karmika) use a vocabulary divergent from the default
    # Vaivahika states. E.g. Karma uses YES_WITH_EFFORT in place of
    # YES_WITH_DELAYS and CONDITIONAL_SUBORDINATE in place of CONDITIONAL.
    # The remap is applied AFTER base resolution but BEFORE substitution/
    # downgrade/promotion, so overlays operate on the remapped vocabulary.
    verdict_remap = spec.get('verdict_remap') or {}
    remap_applied = None
    if base in verdict_remap and verdict_remap[base] in allowed_states:
        # Capture the remap step for transparency in verdict_trace — this
        # is what surfaces e.g. "primitive=conditional was remapped via
        # sammana_remap from CONDITIONAL → CONDITIONAL_PRIVY" when no
        # overlay substitution fires. Without this trace entry, the
        # diagnostic shows all overlays silent but a non-base final state,
        # which made users (correctly) wonder where the mutation came from.
        remap_applied = {
            'from': base,
            'to':   verdict_remap[base],
            'source': 'verdict_remap',
            'reason': f"Topic-level verdict_remap: {base} → {verdict_remap[base]}",
        }
        base = verdict_remap[base]
    # If base STILL isn't in allowed_states (e.g. CONDITIONAL fell through
    # but topic doesn't accept it), fall back to the closest equivalent
    if base not in allowed_states:
        # Find any state in allowed with same severity tier
        target_severity = _VERDICT_SEVERITY.get(base, 3)
        candidates = sorted(
            [(s, _VERDICT_SEVERITY.get(s, 99)) for s in allowed_states],
            key=lambda x: abs(x[1] - target_severity)
        )
        if candidates:
            fallback_to = candidates[0][0]
            if fallback_to != base:
                # Record this as a remap-style fallback too — same diagnostic
                # transparency principle. The user should be able to see when
                # a state got coerced via severity-tier matching.
                remap_applied = {
                    'from': base,
                    'to':   fallback_to,
                    'source': 'severity_fallback',
                    'reason': f"Severity-tier coercion: {base} → {fallback_to} "
                              f"(target severity {target_severity}, available "
                              f"states {sorted(allowed_states)})",
                }
            base = fallback_to

    # --- Step 2: Apply verdict_substitution if primitive matches ---
    # (Kamboola/Gada substitute failure→YES_WITH_DELAYS;
    #  Rahu/Ketu substitute conditional→CONDITIONAL_MEDICAL or failure→CONDITIONAL_THIRD_PARTY)
    substitution_applied = None
    for sub in state['pending_substitutions']:
        if primitive in sub.get('when_primitives', []) and sub['new_state'] in allowed_states:
            new_state = sub['new_state']
            # Apply only the highest-severity substitution that fits
            if substitution_applied is None or \
               _VERDICT_SEVERITY.get(new_state, 0) > _VERDICT_SEVERITY.get(substitution_applied['new_state'], 0):
                substitution_applied = sub
                base = new_state

    # --- Step 3: Apply downgrades (YES → YES_WITH_DELAYS for sterile cusp etc.) ---
    downgrade_applied = None
    for dg in state['pending_downgrades']:
        if base in dg.get('from_states', []) and dg['to'] in allowed_states:
            base = dg['to']
            downgrade_applied = dg

    # --- Step 4: Apply promotion (HIGH_RISK always wins if it fires) ---
    promotion_applied = None
    for promo in state['pending_promotions']:
        new_state = promo['state']
        if new_state in allowed_states:
            if _VERDICT_SEVERITY.get(new_state, 0) >= _VERDICT_SEVERITY.get(base, 0):
                base = new_state
                promotion_applied = promo

    # --- Step 5: Modifier flag (orthogonal — does NOT change state) ---
    modifier_flag = None
    if state['pending_modifier_flags']:
        # Take the first valid modifier
        for flag in state['pending_modifier_flags']:
            if flag in spec.get('verdict_modifiers', []):
                modifier_flag = flag
                break

    return {
        'state':            base,
        'text':             _VERDICT_TEXTS.get(base, base),
        'modifier':         modifier_flag,
        'substitution_applied': substitution_applied,
        'downgrade_applied': downgrade_applied,
        'promotion_applied': promotion_applied,
        'remap_applied':    remap_applied,
    }


# =================================================================
# GENERIC ORCHESTRATOR
# =================================================================

def prashna_topic_judgment(chart_data: Dict, topic_id: str, **inputs) -> Dict:
    """
    Generic Prashna sub-module judgment, driven by PRASHNA_TOPICS registry.

    Args:
        chart_data:  the cast Prashna chart dict
        topic_id:    registered topic key (e.g. 'vivaha', 'garbha')
        **inputs:    topic-specific inputs (querent_gender, full_query,
                     natal_lagna_sign, intent, etc.)

    Returns the structured judgment package consumed by the route layer
    and the AI narrative builder.
    """
    if topic_id not in PRASHNA_TOPICS:
        raise ValueError(f"Unknown topic_id: {topic_id}. Available: {list(PRASHNA_TOPICS)}")

    spec = PRASHNA_TOPICS[topic_id]
    _validate_inputs(spec, inputs)

    # ===== 1a. Resolve intent route (if topic uses intent_routing) =====
    # Topics like 'putra' route to different (target_house, overlays, tone,
    # secondary_karaka) configurations based on the query's classified intent.
    # Topics without intent_routing get back the original spec unchanged.
    horizon_text = inputs.get('full_query') or inputs.get('query_text')
    effective_spec, classified_intent = _resolve_intent_route(
        spec, topic_id, horizon_text, inputs
    )

    # ===== 1. Initialize target =====
    lagna_sign = chart_data.get('lagna_sign', 0)
    initial_target_house = effective_spec['target_house']
    initial_target_sign = (lagna_sign + initial_target_house - 1) % 12

    # ===== 2. Base engine layers =====
    sincerity_mode = effective_spec.get('sincerity_mode', 'standard')
    sincerity = compute_sincerity_score(
        chart_data,
        natal_lagna_sign=inputs.get('natal_lagna_sign'),
        garbha_mode=(sincerity_mode == 'garbha'),
        jd_ut=chart_data.get('jd_ut'),
    )

    avasthas = compute_avasthas(chart_data)
    aspects = detect_all_aspects(chart_data)
    strength = compute_strength_scaling(chart_data)

    # ===== 2b. Karmika container hook — Rule 2 functional transformation =====
    # Saturn/Mars synthesis-label rewriting MUST happen before overlays run,
    # so that subordinate_trajectory et al. read the transformed labels.
    # Idempotent and a no-op for non-Karmika topics.
    karmika_transform_meta = None
    if effective_spec.get('karmika_avastha_transform') or topic_id in _KARMIKA_TOPICS:
        karmika_transform_meta = apply_karmika_avastha_transformation(
            chart_data, avasthas
        )

    initial_bhava = compute_bhava_bala(chart_data, initial_target_house)
    initial_karya = karya_success_chain(chart_data, initial_target_house)

    # ===== 3. Initialize orchestrator state =====
    state = {
        'chart':    chart_data,
        'target': {
            'house': initial_target_house,
            'role':  effective_spec['target_role'],
            'sign_index': initial_target_sign,
            'lord': SIGN_LORDS[initial_target_sign],
            'override_reason': None,
            'secondary_karaka': effective_spec.get('secondary_karaka'),
        },
        'karya':     initial_karya,
        'bhava':     initial_bhava,
        'bhava_net': initial_bhava.get('net_strength_pct', 0),
        'sincerity': sincerity,
        # Karmika-related diagnostic data, exposed to overlays
        'avasthas':         avasthas,                   # transformed if Karmika
        'strength_scaling': strength,                   # for startup_pivot_crosscheck
        'karmika_transform_meta': karmika_transform_meta,
        # Collected mutations (deferred)
        'pending_caps':           [],
        'pending_substitutions':  [],
        'pending_promotions':     [],
        'pending_downgrades':     [],
        'pending_modifier_flags': [],
    }

    # ===== 4. Long-horizon detection (with topic-specific keyword extras) =====
    long_horizon = detect_long_horizon_query(horizon_text)
    if not long_horizon['is_long_horizon'] and effective_spec.get('long_horizon_extras'):
        q = (horizon_text or '').lower()
        for kw in GARBHA_LONG_HORIZON_EXTRAS:
            if kw in q:
                long_horizon = {
                    'is_long_horizon': True,
                    'matched_keyword': kw,
                    'disclaimer': (
                        "This question concerns a multi-decade horizon — Prashna "
                        "shows the current cycle's trajectory only."
                    ),
                }
                break

    # ===== 5. Intent classification (legacy Garbha path — unified below) =====
    if classified_intent is None and topic_id == 'garbha':
        classified_intent = inputs.get('intent') or classify_garbha_intent(horizon_text)
    # Patch back into inputs so overlays see the resolved intent
    inputs = dict(inputs)
    if classified_intent is not None:
        inputs['intent'] = classified_intent

    # ===== 6. Run overlays in declared order =====
    overlay_findings = []
    for overlay_name in effective_spec['overlays']:
        if overlay_name not in OVERLAY_REGISTRY:
            raise ValueError(f"Unknown overlay '{overlay_name}' in topic '{topic_id}'")
        fn = OVERLAY_REGISTRY[overlay_name]
        finding = fn(chart_data, state, inputs)
        finding['overlay'] = overlay_name  # ensure name is set
        overlay_findings.append(finding)
        _apply_finding_immediate(finding, state)

    # ===== 7. Finalize state (apply deferred caps) =====
    _finalize_state(state)

    # ===== 8. Synthesize verdict =====
    verdict = _synthesize_verdict(state, spec)

    # ===== 9. Build response =====
    lagna_lord = SIGN_LORDS[lagna_sign]
    target = state['target']
    target_lord = target['lord']

    querent_av = avasthas.get(lagna_lord, {'avastha': 'Neutral', 'condition': '—'})
    quesited_av = avasthas.get(target_lord, {'avastha': 'Neutral', 'condition': '—'})
    planets = chart_data.get('planets', {})

    # H2N
    h2n = horary_to_natal_shift(lagna_sign, inputs.get('natal_lagna_sign'))

    # Core catalyst — pick from the most decisive overlay finding
    catalyst = _select_core_catalyst(state, overlay_findings, lagna_lord, target_lord)

    # Build per-overlay data passthrough (flattened for UI consumption)
    overlay_data = {}
    for f in overlay_findings:
        overlay_data[f['overlay']] = {
            'fired': f.get('fired', False),
            'data':  f.get('data'),
            'narrative': f.get('narrative'),
            'frontend_card_id': f.get('frontend_card_id'),
        }

    return {
        'topic_id':              topic_id,
        'topic_display_name':    spec['display_name'],
        'container':             spec['container'],
        'narrative_tone':        effective_spec['narrative_tone'],
        # Intent routing (None for topics that don't use it)
        'intent':                classified_intent,
        'secondary_karaka':      effective_spec.get('secondary_karaka'),
        # Core verdict
        'verdict':               verdict['state'],
        'verdict_text':          verdict['text'],
        'verdict_modifier':      verdict['modifier'],
        'certainty_score':       strength['score'],
        'certainty_band':        strength['band'],
        'certainty_narrative':   strength['narrative'],
        # Target resolution
        'target_house':          target['house'],
        'target_role':           target['role'],
        'target_override_reason': target.get('override_reason'),
        # Significators
        'querent_lord': {
            'name': lagna_lord,
            'avastha': querent_av.get('avastha'),
            'condition': querent_av.get('condition'),
            'outcome': querent_av.get('outcome'),
            'degree_band': querent_av.get('degree_band'),
            'synthesis_label': querent_av.get('synthesis_label'),
            'synthesis_narrative': querent_av.get('synthesis_narrative'),
            'is_combust': _is_combust(planets, lagna_lord),
            'sign': planets.get(lagna_lord, {}).get('sign'),
            'house': _planet_house(chart_data, lagna_lord),
        },
        'quesited_lord': {
            'name': target_lord,
            'avastha': quesited_av.get('avastha'),
            'condition': quesited_av.get('condition'),
            'outcome': quesited_av.get('outcome'),
            'degree_band': quesited_av.get('degree_band'),
            'synthesis_label': quesited_av.get('synthesis_label'),
            'synthesis_narrative': quesited_av.get('synthesis_narrative'),
            'is_combust': _is_combust(planets, target_lord),
            'is_heavily_combust': is_heavily_combust(planets, target_lord),
            'sign': planets.get(target_lord, {}).get('sign'),
            'house': _planet_house(chart_data, target_lord),
        },
        # Catalyst + base layers
        'core_catalyst':         catalyst,
        'karya_chain':           state['karya'],
        'strength_scaling':      strength,
        'bhava_bala_target':     state['bhava'],
        'horary_to_natal':       h2n,
        'long_horizon':          long_horizon,
        'intent':                classified_intent,  # None for non-Garbha
        # Per-overlay findings (flat for UI rendering)
        'overlay_findings':      overlay_data,
        # Karmika container metadata (None for non-Karmika topics)
        'karmika_transform_meta': state.get('karmika_transform_meta'),
        # Verdict resolution trace
        'verdict_trace': {
            'primitive':       state['karya']['verdict_primitive'],
            'remap':           verdict['remap_applied'],
            'substitution':    verdict['substitution_applied'],
            'downgrade':       verdict['downgrade_applied'],
            'promotion':       verdict['promotion_applied'],
        },
    }


def _ordinal_suffix(n: int) -> str:
    """Returns 'st', 'nd', 'rd', or 'th' for a number."""
    if 10 <= n % 100 <= 20:
        return 'th'
    return {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')


def _select_core_catalyst(state: Dict, findings: List[Dict],
                           lagna_lord: str, target_lord: str) -> Dict:
    """
    Pick the single most decisive yoga/finding as the verdict's 'core catalyst'
    for display in the hero card. Topic-aware: formats target lord descriptor
    as "7th Lord" / "5th Lord" / etc. to match legacy convention.
    """
    target_house = state['target']['house']
    ord_suffix = _ordinal_suffix(target_house)
    target_descriptor = f"{target_house}{ord_suffix} Lord ({target_lord})"
    lagna_descriptor  = f"Lagna Lord ({lagna_lord})"

    fired_findings_by_name = {f['overlay']: f for f in findings if f.get('fired')}
    karya = state.get('karya') or {}

    # Priority 1: substitution-firing yogas (Kamboola, Gada, Rahu/Ketu axis)
    for name in ('kamboola_yoga', 'gada_yoga', 'rahu_ketu_progeny_axis'):
        if name in fired_findings_by_name:
            f = fired_findings_by_name[name]
            return {
                'yoga': name.replace('_', ' ').title(),
                'between': [lagna_descriptor, target_descriptor],
                'narrative': f.get('narrative'),
                'source_overlay': name,
            }

    # Priority 1.5: Direct L1↔L_target Tajik aspect from karya_success_chain.
    # karya_success_chain ALWAYS computes pairwise_aspect(L1, L_target) for
    # Rule 1 and now surfaces it in the return dict as `l1_target_aspect`.
    # This is the catch-all for topics (notably Karma) where the
    # nakta_abhara_scan overlay isn't run — Overlay B may have confirmed
    # the Ithesal but its data shouldn't have to be the catalyst's
    # sole carrier. Using karya's own aspect computation also covers
    # the inverse case: Ithesal exists, Overlay B doesn't fire (no
    # blockers), and yet karya succeeded — we still want to surface
    # the connecting yoga rather than fall through to "None".
    k_asp = karya.get('l1_target_aspect') or {}
    if (karya.get('positive_satisfied', 0) >= 1
            and k_asp.get('within_orb')
            and k_asp.get('yoga') not in (None, 'None')):
        return {
            'yoga': k_asp.get('yoga'),
            'between': [lagna_descriptor, target_descriptor],
            'narrative': k_asp.get('narrative', ''),
            'source_overlay': 'karya_chain_rule1',
            'absolute_separation': k_asp.get('absolute_separation'),
            'orb_used': k_asp.get('orb_used'),
        }

    # Priority 2: L1↔L_target direct aspect via nakta_abhara_scan data
    nakta_finding = fired_findings_by_name.get('nakta_abhara_scan') or {}
    nakta_data = nakta_finding.get('data') or {}
    asp = nakta_data.get('aspect_l1_lt') or {}

    # Legacy vivaha_judgment used `positive_satisfied >= 2` as the gate
    # for picking a strong-aspect catalyst vs Nakta/None fallback.
    if karya.get('positive_satisfied', 0) >= 2 and asp.get('within_orb'):
        return {
            'yoga': asp.get('yoga', 'Aspect'),
            'between': [lagna_descriptor, target_descriptor],
            'narrative': asp.get('narrative', ''),
            'source_overlay': 'nakta_abhara_scan',
        }

    # Priority 3: Nakta bridge as catalyst (legacy used `elif nakta:` truthy check)
    nakta = nakta_data.get('nakta_bridge')
    if nakta:
        return {
            'yoga': 'Nakta',
            'between': [lagna_descriptor, target_descriptor],
            'narrative': nakta.get('narrative', ''),
            'bridge':      nakta.get('bridge'),
            'bridge_role': nakta.get('bridge_role'),
            'bridge_role_narrative': nakta.get('bridge_role_narrative'),
            'source_overlay': 'nakta_abhara_scan',
        }

    # Priority 4: No decisive connection
    return {
        'yoga': 'None',
        'between': [lagna_descriptor, target_descriptor],
        'narrative': 'No decisive Tajik connection between the two significators.',
    }


# =================================================================
# END OF PHASE 4A — prashna_topics.py
# =================================================================
