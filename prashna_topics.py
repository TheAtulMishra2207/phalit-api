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

from typing import Dict, List, Optional, Any, Callable
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
    # Constants
    GARBHA_LONG_HORIZON_EXTRAS,
)


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
        'overlays': [
            'third_party_interference',
            'emotional_reciprocity',
            'nakta_abhara_scan',
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
    # 'putra':         { 'container': 'vaivahika', 'target_house': 5, ... },
    # 'anya_sambandha':{ 'container': 'vaivahika', 'target_house': 7, ... },
    # 'karma':         { 'container': 'karmika',   'target_house': 10, ... },
    # 'shatru':        { 'container': 'yuddha',    'target_house': 6,
    #                    'required_inputs': ['enemy_name'], ... },
    # 'dhana':         { 'container': 'arthika',   'target_house': 2, ... },
    # 'roga':          { 'container': 'aarogya',   'target_house': 6, ... },
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

    return {
        'overlay': 'nakta_abhara_scan',
        'fired': bool(nakta or abhara or yama),
        'data': {
            'nakta_bridge': nakta,
            'abhara_yoga':  abhara,
            'yama_yoga':    yama,
            'aspect_l1_lt': pairwise_aspect(lagna_lord, target_lord, chart),
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
    Vivaha-specific. Per Ch 9: malefic 8L/3L/4L in 7th identifies
    third-party interference source (rival/sibling/parent).
    """
    target_house = state['target']['house']  # 7 for Vivaha
    lagna_sign = chart.get('lagna_sign', 0)

    interferers = []
    role_map = {
        8: ('Female Rival / Outside Party', '8th lord'),
        3: ('Brother / Sibling', '3rd lord'),
        4: ('Parents', '4th lord'),
    }
    for house_num, (label, descr) in role_map.items():
        lord_sign = (lagna_sign + house_num - 1) % 12
        lord = SIGN_LORDS[lord_sign]
        if _planet_house(chart, lord) == target_house:
            # Check if malefic by classical sect
            if lord in ('Mars', 'Saturn', 'Sun') or _is_combust(chart.get('planets', {}), lord):
                interferers.append({
                    'trigger': descr, 'malefic_lord': lord, 'type': label,
                })

    if not interferers:
        return _empty_finding('third_party_interference')

    return {
        'overlay': 'third_party_interference',
        'fired': True,
        'data': {'third_party_interference': interferers},
        'narrative': f'Detected {len(interferers)} third-party interference source(s) on the 7th cusp.',
        'frontend_card_id': 'third-party-card',
    }


def overlay_emotional_reciprocity(chart: Dict, state: Dict, inputs: Dict) -> Dict:
    """
    Vivaha-specific. Per Ch 9: emotional dynamics from L1↔L7 aspect quality
    + Moon's relationship to both lords.
    """
    lagna_sign = chart.get('lagna_sign', 0)
    lagna_lord = SIGN_LORDS[lagna_sign]
    target_house = state['target']['house']
    target_sign = (lagna_sign + target_house - 1) % 12
    target_lord = SIGN_LORDS[target_sign]

    asp_l1_lt = pairwise_aspect(lagna_lord, target_lord, chart)
    asp_l7_moon = pairwise_aspect(target_lord, 'Moon', chart)

    if asp_l1_lt.get('within_orb') and asp_l1_lt.get('yoga') in ('Ithesal', 'Mutthashila'):
        reciprocity = 'mutual_love'
        narrative = 'Mutual emotional reciprocity — both lords meet within applying aspect.'
    elif asp_l7_moon.get('within_orb'):
        reciprocity = 'past_engagement'
        narrative = 'Partner-significator engages with Moon — emotional thread from one side.'
    elif asp_l1_lt.get('yoga') == 'Esrapha':
        reciprocity = 'discord_short'
        narrative = 'Separating aspect between lords — recent friction; may pass.'
    else:
        reciprocity = 'disengaged'
        narrative = 'No active emotional bridge between significators.'

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
    'nakta_abhara_scan':         overlay_nakta_abhara_scan,
    'kamboola_yoga':             overlay_kamboola_yoga,
    'gada_yoga':                 overlay_gada_yoga,
    'eclipse_proximity_axis':    overlay_eclipse_proximity_axis,
    # Vivaha overlays
    'third_party_interference':  overlay_third_party_interference,
    'emotional_reciprocity':     overlay_emotional_reciprocity,
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
    'CONDITIONAL':           'Conditional — depends on circumstantial support',
    'CONDITIONAL_MEDICAL':   ('Conditional — assisted intervention (IVF / IUI / surrogacy) '
                              'is the indicated path'),
    'CONDITIONAL_THIRD_PARTY': 'Conditional — only via intermediary or alternative path',
    'HIGH_RISK':             'Yes — but with significant risk; medical monitoring essential',
    'NO':                    'No — outcome not indicated within the Prashna horizon',
}

# Verdict severity for promotion ordering (higher number = more severe)
_VERDICT_SEVERITY = {
    'YES': 1, 'YES_WITH_DELAYS': 2, 'CONDITIONAL': 3,
    'CONDITIONAL_MEDICAL': 4, 'CONDITIONAL_THIRD_PARTY': 4,
    'HIGH_RISK': 6, 'NO': 5,
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
        base = 'CONDITIONAL' if 'CONDITIONAL' in allowed_states else 'YES_WITH_DELAYS'
    elif primitive == 'success' and modifier == 'with_delays':
        base = 'YES_WITH_DELAYS'
    elif primitive in ('success', 'confirmed'):
        base = 'YES'
    else:
        base = 'YES_WITH_DELAYS'

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

    # ===== 1. Initialize target =====
    lagna_sign = chart_data.get('lagna_sign', 0)
    initial_target_house = spec['target_house']
    initial_target_sign = (lagna_sign + initial_target_house - 1) % 12

    # ===== 2. Base engine layers =====
    sincerity_mode = spec.get('sincerity_mode', 'standard')
    sincerity = compute_sincerity_score(
        chart_data,
        natal_lagna_sign=inputs.get('natal_lagna_sign'),
        garbha_mode=(sincerity_mode == 'garbha'),
        jd_ut=chart_data.get('jd_ut'),
    )

    avasthas = compute_avasthas(chart_data)
    aspects = detect_all_aspects(chart_data)
    strength = compute_strength_scaling(chart_data)

    initial_bhava = compute_bhava_bala(chart_data, initial_target_house)
    initial_karya = karya_success_chain(chart_data, initial_target_house)

    # ===== 3. Initialize orchestrator state =====
    state = {
        'chart':    chart_data,
        'target': {
            'house': initial_target_house,
            'role':  spec['target_role'],
            'sign_index': initial_target_sign,
            'lord': SIGN_LORDS[initial_target_sign],
            'override_reason': None,
        },
        'karya':     initial_karya,
        'bhava':     initial_bhava,
        'bhava_net': initial_bhava.get('net_strength_pct', 0),
        'sincerity': sincerity,
        # Collected mutations (deferred)
        'pending_caps':           [],
        'pending_substitutions':  [],
        'pending_promotions':     [],
        'pending_downgrades':     [],
        'pending_modifier_flags': [],
    }

    # ===== 4. Long-horizon detection (with topic-specific keyword extras) =====
    horizon_text = inputs.get('full_query') or inputs.get('query_text')
    long_horizon = detect_long_horizon_query(horizon_text)
    if not long_horizon['is_long_horizon'] and spec.get('long_horizon_extras'):
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

    # ===== 5. Intent classification (for topics that use it) =====
    classified_intent = None
    if topic_id == 'garbha':
        classified_intent = inputs.get('intent') or classify_garbha_intent(horizon_text)
        # Patch back into inputs so overlays see the resolved intent
        inputs = dict(inputs)
        inputs['intent'] = classified_intent

    # ===== 6. Run overlays in declared order =====
    overlay_findings = []
    for overlay_name in spec['overlays']:
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
        'narrative_tone':        spec['narrative_tone'],
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
        # Verdict resolution trace
        'verdict_trace': {
            'primitive':       state['karya']['verdict_primitive'],
            'substitution':    verdict['substitution_applied'],
            'downgrade':       verdict['downgrade_applied'],
            'promotion':       verdict['promotion_applied'],
        },
    }


def _select_core_catalyst(state: Dict, findings: List[Dict],
                           lagna_lord: str, target_lord: str) -> Dict:
    """
    Pick the single most decisive yoga/finding as the verdict's 'core catalyst'
    for display in the hero card.
    """
    # Priority: substitution-firing yogas > L1↔L_target aspect > "no catalyst"
    fired_findings_by_name = {f['overlay']: f for f in findings if f.get('fired')}

    for name in ('kamboola_yoga', 'gada_yoga', 'rahu_ketu_progeny_axis'):
        if name in fired_findings_by_name:
            f = fired_findings_by_name[name]
            return {
                'yoga': name.replace('_', ' ').title(),
                'between': [f"Lagna Lord ({lagna_lord})", f"Target Lord ({target_lord})"],
                'narrative': f.get('narrative'),
                'source_overlay': name,
            }

    # L1↔L_target aspect from nakta_abhara_scan data
    nakta_finding = fired_findings_by_name.get('nakta_abhara_scan')
    if nakta_finding:
        asp = (nakta_finding.get('data') or {}).get('aspect_l1_lt') or {}
        if asp.get('within_orb'):
            return {
                'yoga': asp.get('yoga', 'Aspect'),
                'between': [f"Lagna Lord ({lagna_lord})", f"Target Lord ({target_lord})"],
                'narrative': asp.get('narrative', ''),
                'source_overlay': 'nakta_abhara_scan',
            }

        nakta = (nakta_finding.get('data') or {}).get('nakta_bridge')
        if nakta and nakta.get('bridge'):
            return {
                'yoga': 'Nakta',
                'between': [f"Lagna Lord ({lagna_lord})", f"Target Lord ({target_lord})"],
                'bridge': nakta.get('bridge'),
                'bridge_role': nakta.get('bridge_role'),
                'narrative': nakta.get('narrative'),
                'source_overlay': 'nakta_abhara_scan',
            }

    return {
        'yoga': 'None',
        'between': [f"Lagna Lord ({lagna_lord})", f"Target Lord ({target_lord})"],
        'narrative': 'No decisive Tajik connection between Lagna and target lords.',
    }


# =================================================================
# END OF PHASE 4A — prashna_topics.py
# =================================================================
