# =================================================================
# Phalit.ai — Prashna Engine (Foundational Module)
# =================================================================
# Phase 1A–1E: Constants, pre-cast helpers, sincerity check,
# avastha engine, bhava bala matrix.
#
# Locked Decisions:
#   1. Chart casting modes: time-based + phonetic toggle
#   2. Shadow calculation: sec(altitude) — sun altitude geometry
#   3. Multi-query anchor: per-chart session, up to 5 questions
#   4. Velocity hierarchy: hardcoded classical
#      (Moon > Mercury > Venus > Sun > Mars > Jupiter > Saturn)
#   5. No Sahams in Prashna
#   6. Page architecture: clustered Hub + 7-8 War Rooms
#   7. Sincerity Check: soft-warning with confidence gauge
#   8. Category selection: picker + AI routing confirmation
#
# Author: Atul Kumar Mishra (Phalit.ai)
# Generated: May 2026
# =================================================================

import math
from typing import Dict, List, Optional, Tuple

# =================================================================
# SECTION 1A: CONSTANTS
# =================================================================

SIGNS = ['Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo',
         'Libra', 'Scorpio', 'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces']

SIGN_SANSKRIT = ['Mesha', 'Vrishabha', 'Mithuna', 'Karka', 'Simha', 'Kanya',
                 'Tula', 'Vrischika', 'Dhanu', 'Makara', 'Kumbha', 'Meena']

# Sign-lord mapping (0=Aries → Mars, 1=Taurus → Venus, etc.)
SIGN_LORDS = ['Mars', 'Venus', 'Mercury', 'Moon', 'Sun', 'Mercury',
              'Venus', 'Mars', 'Jupiter', 'Saturn', 'Saturn', 'Jupiter']

# Locked Decision #4: Hardcoded classical velocity hierarchy.
# This is the SYMBOLIC speed order used for Ithesal/Esrapha determinations.
# It deliberately ignores instantaneous ephemeris speeds (retrograde, fast/slow phases)
# because Tajik logic depends on the symbolic hierarchy.
# Index 0 = fastest, Index 6 = slowest.
VELOCITY_HIERARCHY = ['Moon', 'Mercury', 'Venus', 'Sun', 'Mars', 'Jupiter', 'Saturn']

# Deeptamsha (orbs of influence) for each planet
DEEPTAMSHA = {
    'Sun': 15.0, 'Moon': 12.0, 'Mars': 8.0,
    'Mercury': 7.0, 'Jupiter': 9.0, 'Venus': 7.0, 'Saturn': 9.0
}

# Natural benefics & malefics (Saumya / Krura graha)
BENEFICS = ['Jupiter', 'Venus', 'Mercury']
MALEFICS = ['Sun', 'Mars', 'Saturn', 'Rahu', 'Ketu']

# Exaltation signs (0-indexed)
EXALTATION = {
    'Sun': 0,        # Aries
    'Moon': 1,       # Taurus
    'Mars': 9,       # Capricorn
    'Mercury': 5,    # Virgo
    'Jupiter': 3,    # Cancer
    'Venus': 11,     # Pisces
    'Saturn': 6,     # Libra
    'Rahu': 1,       # Taurus (locked: BPHS Ch.47)
    'Ketu': 7,       # Scorpio
}

# Debilitation signs (0-indexed) — opposite of exaltation
DEBILITATION = {
    'Sun': 6,        # Libra
    'Moon': 7,       # Scorpio
    'Mars': 3,       # Cancer
    'Mercury': 11,   # Pisces
    'Jupiter': 9,    # Capricorn
    'Venus': 5,      # Virgo
    'Saturn': 0,     # Aries
    'Rahu': 7,       # Scorpio
    'Ketu': 1,       # Taurus
}

# Own signs (Swakshetra)
OWN_SIGNS = {
    'Sun':     [4],          # Leo
    'Moon':    [3],          # Cancer
    'Mars':    [0, 7],       # Aries, Scorpio
    'Mercury': [2, 5],       # Gemini, Virgo
    'Jupiter': [8, 11],      # Sagittarius, Pisces
    'Venus':   [1, 6],       # Taurus, Libra
    'Saturn':  [9, 10],      # Capricorn, Aquarius
}

# Permanent (Naisargika) friendships — BPHS standard
PERMANENT_FRIENDS = {
    'Sun':     ['Moon', 'Mars', 'Jupiter'],
    'Moon':    ['Sun', 'Mercury'],
    'Mars':    ['Sun', 'Moon', 'Jupiter'],
    'Mercury': ['Sun', 'Venus'],
    'Jupiter': ['Sun', 'Moon', 'Mars'],
    'Venus':   ['Mercury', 'Saturn'],
    'Saturn':  ['Mercury', 'Venus'],
}

PERMANENT_ENEMIES = {
    'Sun':     ['Venus', 'Saturn'],
    'Moon':    [],
    'Mars':    ['Mercury'],
    'Mercury': ['Moon'],
    'Jupiter': ['Mercury', 'Venus'],
    'Venus':   ['Sun', 'Moon'],
    'Saturn':  ['Sun', 'Moon', 'Mars'],
}

# Combustion orbs (BPHS standard, degrees from Sun)
COMBUSTION_ORB = {
    'Moon':    12.0,
    'Mars':    17.0,
    'Mercury': 14.0,
    'Jupiter': 11.0,
    'Venus':   10.0,
    'Saturn':  15.0,
}

# -----------------------------------------------------------------
# Pavarga Phonetic Lagna Table
# -----------------------------------------------------------------
# Maps Sanskrit/Hindi syllables → governing planet → Lagna sign.
# Sun & Moon are single-lordship (vowels → Leo, semivowels → Cancer).
# Other planets are dual-lordship: position 1/3/5 (odd) → odd sign,
# position 2/4 (even) → even sign.

PAVARGA_TABLE = {
    'Sun': {
        'devanagari': ['अ','आ','इ','ई','उ','ऊ','ए','ऐ','ओ','औ','ऋ','ॠ'],
        'iast':       ['a','aa','i','ii','u','uu','e','ai','o','au','r','rr'],
        'single_lord': True,
    },
    'Moon': {
        'devanagari': ['य','र','ल','व','श','ष','स','ह'],
        'iast':       ['ya','ra','la','va','sha','ssa','sa','ha'],
        'single_lord': True,
    },
    'Mars': {
        'devanagari': ['क','ख','ग','घ','ङ'],
        'iast':       ['ka','kha','ga','gha','nga'],
        'single_lord': False,
    },
    'Mercury': {
        'devanagari': ['ट','ठ','ड','ढ','ण'],
        'iast':       ['tta','ttha','dda','ddha','nna'],
        'single_lord': False,
    },
    'Jupiter': {
        'devanagari': ['त','थ','द','ध','न'],
        'iast':       ['ta','tha','da','dha','na'],
        'single_lord': False,
    },
    'Venus': {
        'devanagari': ['च','छ','ज','झ','ञ'],
        'iast':       ['cha','chha','ja','jha','nya'],
        'single_lord': False,
    },
    'Saturn': {
        'devanagari': ['प','फ','ब','भ','म'],
        'iast':       ['pa','pha','ba','bha','ma'],
        'single_lord': False,
    },
}

# Single-lord sign mapping
SINGLE_LORD_SIGN = {
    'Sun':  4,   # Leo
    'Moon': 3,   # Cancer
}

# Dual-lord sign mapping: planet → (odd_sign_index, even_sign_index)
DUAL_LORD_SIGN_MAP = {
    'Mars':    (0, 7),    # Aries (odd) / Scorpio (even)
    'Mercury': (2, 5),    # Gemini (odd) / Virgo (even)
    'Jupiter': (8, 11),   # Sagittarius (odd) / Pisces (even)
    'Venus':   (6, 1),    # Libra (odd) / Taurus (even)
    'Saturn':  (10, 9),   # Aquarius (odd) / Capricorn (even)
}


# =================================================================
# SECTION 1A.5: DEGREE-BAND, LONG-HORIZON, SIGN-LORD UTILITIES
# (Added in Phase 2 per Atul's audit — universal helpers used across
#  Avastha enrichment, Pariheena nuance, and verdict framing.)
# =================================================================


# Per Atul's "Master Design for degree_position_band":
#   0°–1°    Mrityu Bhaga / Sadyo-Gata     — Infantile / Extreme Weakness
#   1°–10°   Udaya (Forming)               — Emergent, building narrative
#   10°–20°  Pragalbha (Mature)            — Peak Utility, full Bala
#   20°–28°  Culminating / Pariheena Band  — Intense / Fading, brittle
#   28°–30°  Sandhi (Edge of Abyss)        — Functional Failure
def compute_degree_band(longitude_or_degree_in_sign: float) -> Dict:
    """
    Resolve a planet's degree-within-sign to one of the 5 classical bands.

    Accepts either a zodiacal longitude (0–360) or a degree-in-sign (0–30);
    the function modulos by 30 either way.

    Returns dict:
        deg_in_sign:    float (0–30)
        band_key:       'sadyo_gata' | 'udaya' | 'pragalbha' | 'culminating' | 'sandhi'
        band_name:      Sanskrit label
        band_english:   English label
        narrative:      one-line outcome signature
    """
    deg = float(longitude_or_degree_in_sign) % 30.0

    if deg < 1.0:
        return {
            'deg_in_sign': round(deg, 4),
            'band_key': 'sadyo_gata',
            'band_name': 'Mrityu Bhaga / Sadyo-Gata',
            'band_english': 'Infantile · Extreme Weakness',
            'narrative': ("The planet has just entered the sign; its energy is "
                          "unfamiliar. Results are delayed or phantom."),
        }
    if deg < 10.0:
        return {
            'deg_in_sign': round(deg, 4),
            'band_key': 'udaya',
            'band_name': 'Udaya',
            'band_english': 'Emergent · Forming',
            'narrative': ("The planet is building its narrative — active but "
                          "requires external support (aspects) to succeed."),
        }
    if deg < 20.0:
        return {
            'deg_in_sign': round(deg, 4),
            'band_key': 'pragalbha',
            'band_name': 'Pragalbha',
            'band_english': 'Mature · Peak Utility',
            'narrative': ("Full Bala — this is the only band where a YES verdict "
                          "is truly reliable."),
        }
    if deg < 28.0:
        return {
            'deg_in_sign': round(deg, 4),
            'band_key': 'culminating',
            'band_name': 'Culminating / Pariheena Band',
            'band_english': 'Intense · Fading',
            'narrative': ("The planet is desperate to finish its task — high effort, "
                          "but results are brittle."),
        }
    return {
        'deg_in_sign': round(deg, 4),
        'band_key': 'sandhi',
        'band_name': 'Sandhi',
        'band_english': 'Edge of Abyss · Functional Failure',
        'narrative': ("The planet is drowning between two elements (Gandanta) and "
                      "cannot fulfil the Karya."),
    }


# Long-horizon keywords — queries about life-long themes that exceed
# Prashna's classical 6–12 month horizon. Triggers a disclaimer card.
LONG_HORIZON_PATTERNS = [
    'old age', 'oldage',
    'lifelong', 'life-long', 'life long',
    'all my life', 'rest of my life', 'rest of life',
    'till death', 'until death', 'until i die', 'till i die',
    'forever', 'permanent', 'permanently',
    'whole life', 'entire life',
    'next decade', 'decade', 'decades',
    'ten years from now', 'twenty years',
    'retirement', 'retired life',
    'final years', 'last years',
    'peaceful old age', 'happy old age', 'comfortable old age',
    'shanti in old age',
]


def detect_long_horizon_query(query_text: Optional[str]) -> Dict:
    """
    Scan a query for long-horizon keywords. Returns whether Prashna's
    6-12 month window is mathematically appropriate for the question.

    Returns dict:
        is_long_horizon:  bool
        matched_keyword:  str | None
        disclaimer:       str | None
    """
    if not query_text:
        return {'is_long_horizon': False, 'matched_keyword': None, 'disclaimer': None}
    q = query_text.lower()
    for kw in LONG_HORIZON_PATTERNS:
        if kw in q:
            return {
                'is_long_horizon': True,
                'matched_keyword': kw,
                'disclaimer': (
                    f"This question concerns a multi-decade horizon "
                    f"(\"{kw}\"). Prashna shows current momentum within a 6–12 "
                    f"month window — it is not the appropriate sastra for "
                    f"lifelong themes. For multi-decade questions about marriage "
                    f"quality, consult your natal D-9 Navamsha and D-30 "
                    f"Trishamsha. The Prashna verdict below addresses only the "
                    f"immediate trajectory of the matter."
                ),
            }
    return {'is_long_horizon': False, 'matched_keyword': None, 'disclaimer': None}


def _sign_lord_signs(planet_name: str) -> List[int]:
    """Return the sign indices ruled by a planet. Moon→[Cancer], Sun→[Leo],
    others→both signs they rule (e.g. Mars→[Aries, Scorpio])."""
    out = []
    for s_idx, lord in enumerate(SIGN_LORDS):
        if lord == planet_name:
            out.append(s_idx)
    return out


def compute_avastha_band_synthesis(avastha_state: str, band_key: Optional[str],
                                    house_placement: Optional[int] = None) -> Dict:
    """
    Per Atul's audit: resolve the contradiction between an Avastha (a strength
    classification) and a degree-band (also a strength classification) when they
    point in opposite directions. Returns a synthesized label that the narrative
    AI must use to avoid contradictions like "Peak Utility but Conquered".

    The cross-product gives 5 bands × 10 Avasthas = 50 cases, collapsed into
    7 archetypes:
        - Full Power         (auspicious + peak/late band)
        - Thwarted Power     (inauspicious + Pragalbha — the audit case)
        - Building Power     (auspicious + Udaya — growing strength)
        - Forming Weakness   (inauspicious + Udaya — worsening)
        - Brittle Failure    (inauspicious + Culminating — desperate end-game)
        - Last Hurrah        (auspicious + Culminating — declining but effective)
        - Functional Failure (Sandhi — drowned regardless of Avastha)
        - Phantom            (Sadyo-Gata — too fresh; results unstable)

    `house_placement` (optional): the planet's house from Lagna (1-12).
    When provided and in (6, 8, 12) — i.e. a Dusthana — the auspiciousness
    rating is clamped to inauspicious before classification. This routes
    Deepta+Pragalbha+H8 to 'Thwarted Power' (the structurally honest label)
    instead of 'Full Power', and Deepta+Culminating+H8 to 'Brittle Failure'
    instead of 'Last Hurrah'. The dusthana frame occludes the delivery
    channel even when degree-band + avastha individually signal capacity.
    The dampening is recorded in the return dict as `dusthana_dampened`
    so callers/UI can surface the override transparently.
    """
    auspiciousness = AVASTHA_AUSPICIOUSNESS.get(avastha_state, 3)
    dusthana_dampened = False

    # Dusthana dampening — house frame override per Atul's audit (Bug 3).
    # A planet in 6/8/12 from Lagna cannot deliver its full auspicious
    # nature regardless of degree-band + avastha signaling. Clamp to
    # inauspicious so the label vocabulary ('Thwarted Power', 'Brittle
    # Failure', 'Forming Weakness') reflects the occluded delivery.
    if house_placement in (6, 8, 12):
        if auspiciousness >= 3:
            auspiciousness = 2  # force inauspicious bracket
            dusthana_dampened = True

    is_inauspicious = auspiciousness < 3
    is_auspicious = auspiciousness >= 5

    if band_key == 'sandhi':
        result = {
            'synthesis_label': 'Functional Failure',
            'synthesis_narrative': (
                "Drowning in Gandanta (sign-junction). Avastha is moot — the "
                "planet cannot deliver, even with strong dignity elsewhere."
            ),
        }
    elif band_key == 'sadyo_gata':
        result = {
            'synthesis_label': 'Phantom',
            'synthesis_narrative': (
                "Just entered the sign — the energy is unfamiliar. Avastha "
                "classifications are provisional; results remain phantom-like."
            ),
        }
    elif band_key == 'pragalbha':
        if is_inauspicious:
            result = {
                'synthesis_label': 'Thwarted Power',
                'synthesis_narrative': (
                    "Peak Bala (Pragalbha) — the planet has the raw capacity "
                    f"to act decisively. But the {avastha_state} state binds its "
                    "hands: it is strong enough to suffer fully, not strong "
                    "enough to redirect the outcome. High-stakes struggle."
                ),
            }
        elif is_auspicious:
            result = {
                'synthesis_label': 'Full Power',
                'synthesis_narrative': (
                    f"Pragalbha + {avastha_state} — full capacity AND favourable "
                    "dignity. The planet delivers cleanly within its remit."
                ),
            }
        else:
            result = {
                'synthesis_label': 'Standing Power',
                'synthesis_narrative': (
                    f"Pragalbha + {avastha_state} — strong capacity, ambiguous "
                    "dignity. Outcome depends on which planet wins the support battle."
                ),
            }
    elif band_key == 'udaya':
        if is_inauspicious:
            result = {
                'synthesis_label': 'Forming Weakness',
                'synthesis_narrative': (
                    f"Udaya (still building) + {avastha_state} — the affliction "
                    "is not yet at full force, but the trajectory worsens with "
                    "time. Acting early may pre-empt the worst phase."
                ),
            }
        elif is_auspicious:
            result = {
                'synthesis_label': 'Building Power',
                'synthesis_narrative': (
                    f"Udaya + {avastha_state} — momentum is gathering on the "
                    "favourable side. Results materialise as the planet matures."
                ),
            }
        else:
            result = {
                'synthesis_label': 'Forming Mediocrity',
                'synthesis_narrative': (
                    "Udaya in a neutral state — no narrative pull either way; "
                    "outcomes hinge on environmental triggers."
                ),
            }
    elif band_key == 'culminating':
        if is_inauspicious:
            result = {
                'synthesis_label': 'Brittle Failure',
                'synthesis_narrative': (
                    f"Culminating + {avastha_state} — the planet is desperate "
                    "to finish a losing fight. Late-stage effort produces "
                    "brittle, costly results. Cut losses where possible."
                ),
            }
        elif is_auspicious:
            result = {
                'synthesis_label': 'Last Hurrah',
                'synthesis_narrative': (
                    f"Culminating + {avastha_state} — fading favour, but "
                    "enough strength remains for one decisive delivery. "
                    "Time-bound window."
                ),
            }
        else:
            result = {
                'synthesis_label': 'Fading Trace',
                'synthesis_narrative': (
                    "Culminating in a neutral state — energy receding without a "
                    "clear directional pull."
                ),
            }
    else:
        # No band info — fall back to Avastha-only label
        result = {
            'synthesis_label': avastha_state,
            'synthesis_narrative': (
                f"{avastha_state} state — see Avastha column for outcome signature."
            ),
        }

    # Attach dusthana dampening metadata + narrative addendum
    result['dusthana_dampened'] = dusthana_dampened
    if dusthana_dampened:
        result['dusthana_house'] = house_placement
        result['synthesis_narrative'] += (
            f" House override: the H{house_placement} (Dusthana) placement "
            f"occludes what would otherwise read as a stronger label — "
            f"{avastha_state} dignity has no clean delivery channel from a "
            f"6/8/12 frame."
        )
    return result


# =================================================================
# SECTION 1B: PRE-CAST HELPERS
# =================================================================

def phonetic_to_lagna_sign(query_text: str) -> Dict:
    """
    Parse the first syllable of a query text and return the Lagna sign.
    Accepts both Devanagari and IAST/Roman input.

    Returns:
        sign_index:        0-11 (Aries=0, Pisces=11)
        sign_name:         e.g. 'Aries'
        sign_sanskrit:     e.g. 'Mesha'
        ruling_planet:     name of the governing planet
        position_in_group: 1-5 (None for single-lord groups)
        matched_letter:    the matched letter
        method:            'devanagari' | 'iast' | 'fallback'
        confidence:        1.0 (exact) | 0.5 (fallback) | 0.0 (no match)
    """
    if not query_text or not query_text.strip():
        return {'error': 'Empty query text', 'confidence': 0.0}

    text = query_text.strip()

    # 1. Try Devanagari first character
    first_dev = text[0]
    for planet, data in PAVARGA_TABLE.items():
        if first_dev in data['devanagari']:
            return _resolve_phonetic_match(planet, data, first_dev, 'devanagari')

    # 2. Try IAST/Roman — longest-prefix match
    text_lower = text.lower()
    best = None      # (planet, matched_iast, idx_in_group)
    best_len = 0
    for planet, data in PAVARGA_TABLE.items():
        for i, iast in enumerate(data['iast']):
            if text_lower.startswith(iast) and len(iast) > best_len:
                best = (planet, data, iast, i)
                best_len = len(iast)
    if best:
        planet, data, matched, idx = best
        return _resolve_phonetic_match(planet, data, matched, 'iast', idx)

    # 3. Roman first-consonant extraction.
    #    Handles English/romanized input like "Melody", "Putra", "Vivah",
    #    "Chocolaty" — where the first consonant determines the planetary group
    #    and the IAST whole-syllable list misses (because the following vowel
    #    isn't the default 'a').
    roman_result = _try_roman_first_consonant(text)
    if roman_result is not None:
        return roman_result

    # 4. Fallback: first character is a vowel → Sun → Leo
    if text_lower[0] in 'aeiou':
        return _resolve_phonetic_match('Sun', PAVARGA_TABLE['Sun'], text_lower[0], 'fallback', 0)

    return {
        'error': f"Could not parse first syllable of '{text[:10]}'",
        'confidence': 0.0,
    }


# Roman consonant → (planet, position_in_group) map.
# Order matters in iteration: longer digraphs MUST be tried before single letters.
# Position is 1-indexed (1, 3, 5 = odd sign; 2, 4 = even sign).
ROMAN_PREFIX_MAP = [
    # Aspirated digraphs first (longest prefix wins)
    ('chh', 'Venus',   2),  # छ → Taurus (chha, even)
    ('kh',  'Mars',    2),  # ख → Scorpio (kha, even)
    ('gh',  'Mars',    4),  # घ → Scorpio (gha, even)
    ('ng',  'Mars',    5),  # ङ → Aries  (nga, odd)
    ('ch',  'Venus',   1),  # च → Libra  (cha — default for English 'ch')
    ('jh',  'Venus',   4),  # झ → Taurus (jha, even)
    ('th',  'Jupiter', 2),  # थ → Pisces (tha; ambiguous cerebral/dental — default to dental)
    ('dh',  'Jupiter', 4),  # ध → Pisces (dha)
    ('ph',  'Saturn',  2),  # फ → Capricorn (pha, even)
    ('bh',  'Saturn',  4),  # भ → Capricorn (bha, even)
    ('sh',  'Moon',    0),  # श → Cancer (single-lord)
    # Single consonants
    ('k',   'Mars',    1),  # क → Aries
    ('g',   'Mars',    3),  # ग → Aries
    ('c',   'Venus',   1),  # treat bare 'c' as cha → Libra
    ('j',   'Venus',   3),  # ज → Libra
    ('t',   'Jupiter', 1),  # त → Sagittarius (default dental for ambiguous English 't')
    ('d',   'Jupiter', 3),  # द → Sagittarius
    ('n',   'Jupiter', 5),  # न → Sagittarius
    ('p',   'Saturn',  1),  # प → Aquarius
    ('f',   'Saturn',  2),  # f as variant of ph → Capricorn
    ('b',   'Saturn',  3),  # ब → Aquarius
    ('m',   'Saturn',  5),  # म → Aquarius
    ('y',   'Moon',    0),  # य → Cancer
    ('r',   'Moon',    0),  # र → Cancer
    ('l',   'Moon',    0),  # ल → Cancer
    ('v',   'Moon',    0),  # व → Cancer
    ('w',   'Moon',    0),  # w as variant of v → Cancer
    ('s',   'Moon',    0),  # स → Cancer
    ('h',   'Moon',    0),  # ह → Cancer
    ('z',   'Moon',    0),  # z as variant of sa/sha → Cancer
    ('q',   'Mars',    1),  # q as variant of k → Aries
    ('x',   'Mars',    1),  # x as variant of k → Aries
]


def _try_roman_first_consonant(text: str) -> Optional[Dict]:
    """
    Extract the first consonant (or aspirated digraph) from a romanized string
    and resolve to a Lagna sign per the Pavarga rules.
    Returns None if the first letter is a vowel or no consonant match is found.
    """
    text_lower = text.lower().strip()
    # Skip any leading non-letters (punctuation, digits, whitespace)
    while text_lower and not text_lower[0].isalpha():
        text_lower = text_lower[1:]
    if not text_lower:
        return None
    # Vowels are handled by the vowel fallback elsewhere
    if text_lower[0] in 'aeiou':
        return None

    for prefix, planet, position in ROMAN_PREFIX_MAP:
        if text_lower.startswith(prefix):
            return _resolve_position(planet, prefix, 'roman-consonant', position)

    return None


def _resolve_position(planet: str, matched_letter: str,
                      method: str, position: int) -> Dict:
    """
    Resolve a planet + position-in-group to a Lagna sign.
    Bypasses _resolve_phonetic_match for cases where we know the position
    directly (e.g. roman-consonant lookup) rather than from list-index.
    """
    # Pancha-Varga (strict 5-grid) belongs to Ka/Cha/Ta/ta/Pa-vargas → Mars/Venus/Mercury/Jupiter/Saturn
    # Extended (Ya/Sha + vowels) → Moon/Sun. Atul's "Hybrid" labels:
    pancha_planets = {'Mars', 'Venus', 'Mercury', 'Jupiter', 'Saturn'}
    if planet in pancha_planets:
        vibrational_accuracy = 'pancha-varga-high'
        accuracy_note = ("First letter falls inside the strict 5x5 Pavarga grid — "
                         "high vibrational accuracy.")
    elif planet == 'Moon':
        vibrational_accuracy = 'extended-sibilant'
        accuracy_note = ("First letter falls in the Ya/Sha extended varga (Moon-ruled) — "
                         "valid, but check Moon's sign for volatility.")
    else:  # Sun (vowels)
        vibrational_accuracy = 'extended-vowel'
        accuracy_note = ("First letter is a vowel (Sun-ruled varga) — "
                         "valid; vowel queries reflect raw intention.")

    if planet in SINGLE_LORD_SIGN:
        sign_idx = SINGLE_LORD_SIGN[planet]
        return {
            'sign_index': sign_idx,
            'sign_name': SIGNS[sign_idx],
            'sign_sanskrit': SIGN_SANSKRIT[sign_idx],
            'ruling_planet': planet,
            'position_in_group': position,  # ALWAYS set — Moon's varga has positions too
            'matched_letter': matched_letter,
            'method': method,
            'confidence': 1.0,
            'vibrational_accuracy': vibrational_accuracy,
            'accuracy_note': accuracy_note,
            'single_lord': True,
        }

    is_odd = (position % 2 == 1)
    odd_sign, even_sign = DUAL_LORD_SIGN_MAP[planet]
    sign_idx = odd_sign if is_odd else even_sign
    return {
        'sign_index': sign_idx,
        'sign_name': SIGNS[sign_idx],
        'sign_sanskrit': SIGN_SANSKRIT[sign_idx],
        'ruling_planet': planet,
        'position_in_group': position,
        'matched_letter': matched_letter,
        'method': method,
        'confidence': 1.0,
        'vibrational_accuracy': vibrational_accuracy,
        'accuracy_note': accuracy_note,
        'single_lord': False,
    }


def _resolve_phonetic_match(planet: str, data: Dict, matched_letter: str,
                            method: str, iast_idx: Optional[int] = None) -> Dict:
    """Resolve a matched letter to its Lagna sign per Pavarga rules."""

    # Determine position-in-group consistently (1-indexed) for ALL planets,
    # including single-lord (Moon, Sun) where Atul's audit specifies:
    # "The Moon always has a position."
    if method == 'devanagari':
        try:
            position = data['devanagari'].index(matched_letter) + 1
        except ValueError:
            position = 1
    else:
        position = (iast_idx if iast_idx is not None else 0) + 1

    # Vibrational accuracy classification (Atul's Hybrid Approach):
    pancha_planets = {'Mars', 'Venus', 'Mercury', 'Jupiter', 'Saturn'}
    if planet in pancha_planets:
        vibrational_accuracy = 'pancha-varga-high'
        accuracy_note = ("First letter falls inside the strict 5x5 Pavarga grid — "
                         "high vibrational accuracy.")
    elif planet == 'Moon':
        vibrational_accuracy = 'extended-sibilant'
        accuracy_note = ("First letter falls in the Ya/Sha extended varga (Moon-ruled) — "
                         "valid, but check Moon's sign for volatility.")
    else:  # Sun
        vibrational_accuracy = 'extended-vowel'
        accuracy_note = ("First letter is a vowel (Sun-ruled varga) — "
                         "valid; vowel queries reflect raw intention.")

    if data.get('single_lord'):
        sign_idx = SINGLE_LORD_SIGN[planet]
        return {
            'sign_index': sign_idx,
            'sign_name': SIGNS[sign_idx],
            'sign_sanskrit': SIGN_SANSKRIT[sign_idx],
            'ruling_planet': planet,
            'position_in_group': position,  # ALWAYS set
            'matched_letter': matched_letter,
            'method': method,
            'confidence': 1.0 if method != 'fallback' else 0.5,
            'vibrational_accuracy': vibrational_accuracy,
            'accuracy_note': accuracy_note,
            'single_lord': True,
        }

    # Dual-lord: determine odd/even sign
    is_odd = (position % 2 == 1)
    odd_sign, even_sign = DUAL_LORD_SIGN_MAP[planet]
    sign_idx = odd_sign if is_odd else even_sign

    return {
        'sign_index': sign_idx,
        'sign_name': SIGNS[sign_idx],
        'sign_sanskrit': SIGN_SANSKRIT[sign_idx],
        'ruling_planet': planet,
        'position_in_group': position,
        'matched_letter': matched_letter,
        'method': method,
        'confidence': 1.0,
        'vibrational_accuracy': vibrational_accuracy,
        'accuracy_note': accuracy_note,
        'single_lord': False,
    }


def compute_sun_altitude(jd_ut: float, lat: float, lon: float,
                         sun_lon: float, sun_lat: float = 0.0) -> float:
    """
    Compute the Sun's altitude above the horizon (degrees) at a given JD and location.
    Used to derive the shadow ratio for Prashna timing calculations.

    Args:
        jd_ut:    Julian Day (Universal Time)
        lat:      Observer latitude (degrees, N positive)
        lon:      Observer longitude (degrees, E positive)
        sun_lon:  Sun's tropical longitude (degrees)
        sun_lat:  Sun's ecliptic latitude (usually ≈0)

    Returns:
        Altitude in degrees (negative = below horizon).
    """
    eps = math.radians(23.4393)   # Obliquity of ecliptic (J2000)
    sl = math.radians(sun_lon)
    sb = math.radians(sun_lat)

    # Ecliptic → equatorial
    sin_dec = math.sin(sb) * math.cos(eps) + math.cos(sb) * math.sin(eps) * math.sin(sl)
    sin_dec = max(-1.0, min(1.0, sin_dec))
    dec = math.asin(sin_dec)
    ra = math.atan2(
        math.sin(sl) * math.cos(eps) - math.tan(sb) * math.sin(eps),
        math.cos(sl)
    )
    if ra < 0:
        ra += 2 * math.pi

    # Greenwich Mean Sidereal Time
    T = (jd_ut - 2451545.0) / 36525.0
    gmst_deg = (280.46061837
                + 360.98564736629 * (jd_ut - 2451545.0)
                + T * T * (0.000387933 - T / 38710000.0)) % 360.0
    gmst = math.radians(gmst_deg)

    # Local sidereal time → hour angle
    lst = gmst + math.radians(lon)
    H = lst - ra

    # Altitude
    lat_r = math.radians(lat)
    sin_alt = (math.sin(dec) * math.sin(lat_r)
               + math.cos(dec) * math.cos(lat_r) * math.cos(H))
    sin_alt = max(-1.0, min(1.0, sin_alt))
    return math.degrees(math.asin(sin_alt))


def compute_shadow_ratio_from_altitude(sun_altitude_deg: float,
                                       stick_length: float = 12.0) -> float:
    """
    Replace the classical 12-finger stick shadow measurement with deterministic geometry.
    Shadow length = stick_length / tan(altitude).

    Args:
        sun_altitude_deg: Sun's altitude above horizon (degrees). Must be > 0.
        stick_length:     Reference stick height (default 12 fingers).

    Returns:
        Shadow length in same units as stick_length.
        -1.0 if Sun is below horizon (night query — caller decides fallback).
        999.0 if Sun is at the horizon (effectively infinite shadow).
    """
    if sun_altitude_deg <= 0:
        return -1.0
    if sun_altitude_deg < 0.5:
        return 999.0
    return stick_length / math.tan(math.radians(sun_altitude_deg))


# -----------------------------------------------------------------
# Navamsa lord (used by Adhiveerya & elsewhere)
# -----------------------------------------------------------------

def navamsa_lord(longitude: float) -> str:
    """
    Return the Navamsa lord for a given tropical longitude (degrees).
    Each Navamsa = 3°20' = 200'.
    Sequence per BPHS Ch.6:
      - Movable signs (Aries/Cancer/Libra/Capricorn): Navamsa starts in same sign
      - Fixed signs (Taurus/Leo/Scorpio/Aquarius): starts in 9th sign from parent
      - Dual signs (Gemini/Virgo/Sagittarius/Pisces): starts in 5th sign from parent
    """
    sign_idx = int(longitude // 30) % 12
    pos_in_sign = longitude - sign_idx * 30  # 0–30°
    nav_idx = int(pos_in_sign // (30.0 / 9))  # 0–8

    quality = sign_idx % 3  # 0=Movable, 1=Fixed, 2=Dual
    if quality == 0:
        start = sign_idx
    elif quality == 1:
        start = (sign_idx + 8) % 12
    else:
        start = (sign_idx + 4) % 12

    navamsa_sign = (start + nav_idx) % 12
    return SIGN_LORDS[navamsa_sign]


# =================================================================
# SECTION 1C: SINCERITY CHECK (ETHICAL FILTER)
# =================================================================

def _planet_in_house(houses: List[Dict], planet: str, house_num: int) -> bool:
    """Whole-sign: planet is in house_num (1–12) if it occupies that house's sign."""
    if house_num < 1 or house_num > 12:
        return False
    return planet in houses[house_num - 1].get('occupants', [])


def _angular_diff(lon_a: float, lon_b: float) -> float:
    """Smallest angular difference (0–180°) between two longitudes."""
    return abs((lon_a - lon_b + 180) % 360 - 180)


def _is_combust(planets: Dict, planet_name: str) -> bool:
    """
    Determine combustion from longitudes (authoritative — does not trust input flags).
    Sun is never considered combust.
    """
    if planet_name == 'Sun':
        return False
    p_lon = planets.get(planet_name, {}).get('longitude')
    sun_lon = planets.get('Sun', {}).get('longitude')
    if p_lon is None or sun_lon is None:
        return False
    return _angular_diff(p_lon, sun_lon) <= COMBUSTION_ORB.get(planet_name, 8.0)


def _within_aspect_orb(planet_lon: float, target_lon: float,
                       planet_orb: float, target_orb: float = 0.0,
                       aspect_angles: Optional[List[float]] = None) -> bool:
    """
    Check if planet at planet_lon casts a Tajik aspect on target_lon
    within the larger of the two orbs.
    Default aspect_angles = full Tajik set.
    """
    if aspect_angles is None:
        aspect_angles = [0, 60, 90, 120, 180, 240, 270, 300]
    orb = max(planet_orb, target_orb)
    diff = (planet_lon - target_lon) % 360
    for asp in aspect_angles:
        if abs((diff - asp + 180) % 360 - 180) <= orb:
            return True
    return False


def compute_sincerity_score(chart_data: Dict,
                            natal_lagna_sign: Optional[int] = None,
                            garbha_mode: bool = False,
                            jd_ut: Optional[float] = None) -> Dict:
    """
    Evaluate querent sincerity per the Prashna Ethical Filter.

    Rebalanced per Atul's Master Tajik audit (Option C):
      - Soften the benefic-aspect-on-7th-cusp penalty: -10 → -4
      - Add classical Moon-in-Kendra sincere trigger: +12
      - Add classical Saturn-in-Lagna insincere trigger: -15
      - Add classical Saturn-in-7th insincere trigger: -12

    Extended per audit round 2 — natal house match:
      - When the Prashna Lagna falls in the user's natal Kendra (1/4/7/10) or
        Trikona (5/9), the query is considered "loyal" to the natal axis: +10

    Garbha extensions (when garbha_mode=True):
      - Combust Moon                                            (-10)
      - Saturn in 5th AND Moon aspects Saturn                   (-8)
      - Jupiter in 1st or 7th house                             (+8)
      - Sun in 5th house                                        (-5)
      - Mars-Saturn conjunction within orb                      (-5)
      - Prashna Lagna == natal 5th house sign  → +15 (SUPERSEDES the generic +10)
      - Eclipse proximity on relevant axis → hard cap at 45

    Returns dict with score (0–100), verdict, triggers, narrative_lead,
    natal_match (the natal house number activated, if any).
    """
    if 'planets' not in chart_data or 'houses' not in chart_data:
        return {
            'score': 0,
            'verdict': 'unknown',
            'triggers_insincere': [],
            'triggers_sincere': [],
            'narrative_lead': 'Chart data incomplete for sincerity assessment.',
        }

    planets = chart_data['planets']
    houses = chart_data['houses']
    lagna_sign_idx = chart_data.get('lagna_sign', 0)

    triggers_insincere: List[str] = []
    triggers_sincere: List[str] = []
    score = 50  # neutral baseline

    moon_lon = planets.get('Moon', {}).get('longitude')

    # -- INSINCERE 1: Moon in Lagna AND (Saturn OR combust Mercury) in angles
    if _planet_in_house(houses, 'Moon', 1):
        angles = [1, 4, 7, 10]
        if any(_planet_in_house(houses, 'Saturn', h) for h in angles):
            triggers_insincere.append("Moon in Lagna with Saturn in an angular house")
            score -= 20
        merc_combust = _is_combust(planets, 'Mercury')
        if merc_combust and any(_planet_in_house(houses, 'Mercury', h) for h in angles):
            triggers_insincere.append("Moon in Lagna with combust Mercury in an angular house")
            score -= 20

    # -- INSINCERE 2: Mars AND Mercury both aspect the Moon
    if moon_lon is not None:
        mars_lon = planets.get('Mars', {}).get('longitude')
        merc_lon = planets.get('Mercury', {}).get('longitude')
        mars_hits = (mars_lon is not None and
                     _within_aspect_orb(mars_lon, moon_lon,
                                        DEEPTAMSHA['Mars'], DEEPTAMSHA['Moon']))
        merc_hits = (merc_lon is not None and
                     _within_aspect_orb(merc_lon, moon_lon,
                                        DEEPTAMSHA['Mercury'], DEEPTAMSHA['Moon']))
        if mars_hits and merc_hits:
            triggers_insincere.append("Mars and Mercury both aspect the Moon")
            score -= 15

    # -- INSINCERE 3 [NEW per Atul]: Saturn in Lagna — querent is testing
    if _planet_in_house(houses, 'Saturn', 1):
        triggers_insincere.append("Saturn occupies the Lagna — the querent is testing the astrologer")
        score -= 15

    # -- INSINCERE 4 [NEW per Atul]: Saturn in 7th house
    if _planet_in_house(houses, 'Saturn', 7):
        triggers_insincere.append("Saturn occupies the 7th house — corruption of the judgment seat")
        score -= 12

    # -- INSINCERE 5 [SOFTENED]: Jupiter or Mercury inimical aspect on 7th cusp
    # Reduced from -10 to -4 — benefics in challenging aspect are mildly,
    # not strongly, adverse to query sincerity.
    seventh_cusp_lon = ((lagna_sign_idx + 6) % 12) * 30.0
    for p in ['Jupiter', 'Mercury']:
        if _planet_in_house(houses, p, 1) or _planet_in_house(houses, p, 7):
            continue
        p_lon = planets.get(p, {}).get('longitude')
        if p_lon is None:
            continue
        if _within_aspect_orb(p_lon, seventh_cusp_lon, DEEPTAMSHA[p],
                              aspect_angles=[90, 180, 270]):
            triggers_insincere.append(
                f"{p} casts a square/opposition on the 7th cusp (mild benefic friction)"
            )
            score -= 4

    # -- SINCERE 1: Lagna conjoined with natural benefics
    for b in ['Jupiter', 'Venus']:
        if _planet_in_house(houses, b, 1):
            triggers_sincere.append(f"{b} occupies the Lagna")
            score += 12
    if (_planet_in_house(houses, 'Mercury', 1)
            and not _is_combust(planets, 'Mercury')):
        triggers_sincere.append("Mercury (unafflicted) occupies the Lagna")
        score += 8

    # -- SINCERE 2 [NEW per Atul]: Moon in any Kendra
    # Classical principle: Moon (Mind) in 1/4/7/10 = mind firmly seated in
    # the seat of action; the querent's intent is grounded.
    for kendra in [1, 4, 7, 10]:
        if _planet_in_house(houses, 'Moon', kendra):
            triggers_sincere.append(
                f"Moon is in Kendra ({kendra}th house) — the mind is firmly seated"
            )
            score += 12
            break  # one bonus

    # -- SINCERE 3: Moon aspected by Jupiter
    if moon_lon is not None:
        jup_lon = planets.get('Jupiter', {}).get('longitude')
        if jup_lon is not None and _within_aspect_orb(
                jup_lon, moon_lon, DEEPTAMSHA['Jupiter'], DEEPTAMSHA['Moon']):
            triggers_sincere.append("Moon is aspected by Jupiter")
            score += 15

    # -- SINCERE 4: Mercury or Jupiter in Lagna or 7th house
    for p in ['Mercury', 'Jupiter']:
        if _planet_in_house(houses, p, 1) or _planet_in_house(houses, p, 7):
            triggers_sincere.append(f"{p} occupies the Lagna or the 7th house")
            score += 8
            break  # one bonus per group

    # -- SINCERE 5 [NEW per Atul audit r2]: Natal house match
    # When the Prashna Lagna lands in a natal Kendra (1/4/7/10) or Trikona (5/9),
    # the query is "loyal" to the user's life-axis — the question genuinely
    # concerns a meaningful life-area, not idle curiosity.
    #
    # Garbha extension: if Prashna Lagna lands specifically in natal 5th
    # (the progeny axis), the bonus is +15 (supersedes the generic +10).
    natal_match = None
    if natal_lagna_sign is not None:
        shift_house = ((lagna_sign_idx - natal_lagna_sign) % 12) + 1
        natal_match = shift_house
        zone_labels = {
            1: 'Tanu Bhava (Self / Life-Path)',
            4: 'Sukha Bhava (Home / Foundation)',
            5: 'Putra Bhava (Counsel / Creativity)',
            7: 'Yuvati Bhava (Partnership)',
            9: 'Dharma Bhava (Wisdom / Belief)',
            10: 'Karma Bhava (Career / Status)',
        }
        if garbha_mode and shift_house == 5:
            # Garbha-specific supersession (+15 flat, suppresses the +10)
            triggers_sincere.append(
                "Prashna Lagna activates natal Putra Bhava (progeny axis) — "
                "the question lands directly on the natal fertility frame"
            )
            score += 15
        elif shift_house in zone_labels:
            triggers_sincere.append(
                f"Prashna Lagna activates natal {zone_labels[shift_house]} — "
                "the query is loyal to your life-axis"
            )
            score += 10

    # -- GARBHA-SPECIFIC ADJUSTMENTS (Phase 3A) =====
    if garbha_mode:
        # Combust Moon → mind clouded / hormonal volatility
        if _is_combust(planets, 'Moon'):
            triggers_insincere.append(
                "Moon is combust — mind clouded, hormonal volatility colours the query"
            )
            score -= 10

        # Saturn in 5th AND Moon aspects Saturn → anxiety / infertility fear
        if (_planet_in_house(houses, 'Saturn', 5)
                and moon_lon is not None):
            sat_lon = planets.get('Saturn', {}).get('longitude')
            if sat_lon is not None and _within_aspect_orb(
                    sat_lon, moon_lon,
                    DEEPTAMSHA['Saturn'], DEEPTAMSHA['Moon']):
                triggers_insincere.append(
                    "Saturn in 5th, aspected by Moon — query driven by fear of infertility"
                )
                score -= 8

        # Jupiter in Lagna or 7th → devotional / sincere
        if (_planet_in_house(houses, 'Jupiter', 1)
                or _planet_in_house(houses, 'Jupiter', 7)):
            triggers_sincere.append(
                "Jupiter (Putrakaraka) in Lagna or 7th — devotional sincerity"
            )
            score += 8

        # Sun in 5th → ego-driven framing
        if _planet_in_house(houses, 'Sun', 5):
            triggers_insincere.append(
                "Sun in 5th — pride / ego-driven framing of the question"
            )
            score -= 5

        # Mars-Saturn conjunction → conflict-charged emotional state
        mars_lon = planets.get('Mars', {}).get('longitude')
        sat_lon = planets.get('Saturn', {}).get('longitude')
        if (mars_lon is not None and sat_lon is not None
                and _angular_diff(mars_lon, sat_lon) <= max(
                    DEEPTAMSHA['Mars'], DEEPTAMSHA['Saturn'])):
            triggers_insincere.append(
                "Mars-Saturn conjunction within orb — conflict-charged emotional state"
            )
            score -= 5

    score = max(0, min(100, score))

    # -- ECLIPSE CAP (last — overrides all positives) =====
    # If query falls within ±15 days of an eclipse on the progeny axis,
    # the judgment is shadowed regardless of other sincere triggers.
    eclipse_capped = False
    if garbha_mode and jd_ut is not None:
        eclipse_check = detect_eclipse_proximity(jd_ut, chart_data, target_house=5)
        if eclipse_check is not None and score > 45:
            score = 45
            eclipse_capped = True
            triggers_insincere.append(
                f"Eclipse shadow on progeny axis ({eclipse_check['axis_hit']}) — "
                "sincerity hard-capped at 45/100; medical monitoring advised"
            )

    if score >= 60:
        verdict = 'sincere'
        narrative_lead = ("The cosmic conditions support a sincere inquiry; "
                          "the following results carry full weight.")
    elif score >= 30:
        verdict = 'warning'
        narrative_lead = ("The cosmic conditions suggest the query may be coloured by "
                          "anxiety or hidden motives; the following results carry "
                          "reduced certainty.")
    else:
        verdict = 'doubt'
        narrative_lead = ("The Prashna Lagna shows strong indicators of insincerity, "
                          "contradiction, or hidden agenda; results should be treated "
                          "as provisional.")

    return {
        'score': score,
        'verdict': verdict,
        'triggers_insincere': triggers_insincere,
        'triggers_sincere': triggers_sincere,
        'natal_match': natal_match,
        'eclipse_capped': eclipse_capped if garbha_mode else False,
        'narrative_lead': narrative_lead,
    }


# =================================================================
# SECTION 1D: AVASTHA ENGINE (10-STATE STRENGTH MATRIX)
# =================================================================

AVASTHA_OUTCOMES = {
    'Deepta':     ('Exaltation',                  'Total Success'),
    'Deena':      ('Debility',                    'Sorrows, Pain'),
    'Mudita':     ("Friend's Sign",               'Great Pleasure'),
    'Swastha':    ('Own Sign',                    'Fame, Wealth'),
    'Supta':      ("Enemy's Sign",                'Fear, Enemies'),
    'Peedita':    ('Conquered by Malefics',       'Loss of Wealth'),
    'Pariheena':  ('Sign Preceding Debility',     'Failure in Attempts'),
    'Mushita':    ('Combust',                     'Loss of Wealth'),
    'Suveerya':   ('Sign Following Exaltation',   'Gains (Gold, Property)'),
    'Adhiveerya': ('Benefic Navamsa',             'Government/Friend Gains'),
}

# Precedence: when a planet satisfies multiple conditions, the earliest wins.
AVASTHA_PRECEDENCE = [
    'Mushita',     # Combust overrides everything — the planet is "stolen"
    'Deepta',      # Exalted
    'Deena',       # Debilitated
    'Pariheena',   # Edge of debility
    'Suveerya',    # Edge of exaltation
    'Adhiveerya',  # Benefic Navamsa
    'Peedita',     # Afflicted by malefics
    'Swastha',     # Own sign
    'Mudita',      # Friend's sign
    'Supta',       # Enemy's sign
]

# Auspiciousness scale — distinct from precedence. Used for "which planet is stronger"
# decisions (e.g. Q5 of the multi-query anchor rotation). Higher score = more auspicious.
AVASTHA_AUSPICIOUSNESS = {
    'Deepta':     10,   # Exaltation — total success
    'Suveerya':    8,   # Following exaltation — gains
    'Swastha':     7,   # Own sign — fame/wealth
    'Adhiveerya':  6,   # Benefic Navamsa — government/friend gains
    'Mudita':      5,   # Friend's sign — great pleasure
    'Neutral':     3,   # No state qualified
    'Supta':       2,   # Enemy's sign — fear/enemies
    'Peedita':     1,   # Conquered by malefics — loss of wealth
    'Pariheena':   0,   # Preceding debility — failure
    'Deena':      -1,   # Debility — sorrows
    'Mushita':    -2,   # Combust — loss of wealth (worst)
}


def compute_avasthas(chart_data: Dict) -> Dict[str, Dict]:
    """
    Compute the Avastha (10-state) for each of the 7 classical planets.

    Returns dict: planet → {
        avastha:          winning state name
        condition:        human-readable condition
        outcome:          predicted result
        priority_index:   0–9 (lower = stronger override)
        all_qualifying:   list of all states the planet satisfies
    }
    """
    if 'planets' not in chart_data:
        return {}

    planets = chart_data['planets']
    sun_lon = planets.get('Sun', {}).get('longitude')

    result: Dict[str, Dict] = {}

    for planet_name in ['Sun', 'Moon', 'Mars', 'Mercury', 'Jupiter', 'Venus', 'Saturn']:
        pdata = planets.get(planet_name)
        if not pdata:
            continue

        sign_idx = pdata.get('sign_index')
        if sign_idx is None:
            lon = pdata.get('longitude')
            if lon is None:
                continue
            sign_idx = int(lon // 30) % 12

        qualifying: List[str] = []

        # Mushita (combust) — Sun cannot be combust to itself
        if planet_name != 'Sun' and sun_lon is not None:
            p_lon = pdata.get('longitude')
            if p_lon is not None:
                diff = _angular_diff(p_lon, sun_lon)
                if diff <= COMBUSTION_ORB.get(planet_name, 8.0):
                    qualifying.append('Mushita')

        # Deepta (exalted)
        if sign_idx == EXALTATION.get(planet_name):
            qualifying.append('Deepta')

        # Deena (debilitated)
        if sign_idx == DEBILITATION.get(planet_name):
            qualifying.append('Deena')

        # Pariheena (sign immediately preceding debility)
        deb = DEBILITATION.get(planet_name)
        if deb is not None and sign_idx == (deb - 1) % 12:
            qualifying.append('Pariheena')

        # Suveerya (sign immediately following exaltation)
        exalt = EXALTATION.get(planet_name)
        if exalt is not None and sign_idx == (exalt + 1) % 12:
            qualifying.append('Suveerya')

        # Swastha (own sign)
        if sign_idx in OWN_SIGNS.get(planet_name, []):
            qualifying.append('Swastha')

        # Mudita & Supta (friend's / enemy's sign)
        sign_lord = SIGN_LORDS[sign_idx]
        if sign_lord != planet_name:
            if sign_lord in PERMANENT_FRIENDS.get(planet_name, []):
                qualifying.append('Mudita')
            elif sign_lord in PERMANENT_ENEMIES.get(planet_name, []):
                qualifying.append('Supta')

        # Peedita (within Deeptamsha orb of any natural malefic, including conjunction)
        p_lon = pdata.get('longitude')
        if p_lon is not None:
            for mal in ['Mars', 'Saturn']:
                if mal == planet_name:
                    continue
                m_lon = planets.get(mal, {}).get('longitude')
                if m_lon is None:
                    continue
                diff = _angular_diff(p_lon, m_lon)
                if diff <= max(DEEPTAMSHA[planet_name], DEEPTAMSHA[mal]):
                    qualifying.append('Peedita')
                    break

        # Adhiveerya (Navamsa lord is a natural benefic)
        if p_lon is not None:
            nl = navamsa_lord(p_lon)
            if nl in BENEFICS:
                qualifying.append('Adhiveerya')

        # Compute degree band (Phase 2 enrichment)
        p_lon = planets[planet_name].get('longitude')
        deg_band = compute_degree_band(p_lon) if p_lon is not None else None
        band_key = deg_band['band_key'] if deg_band else None

        # Resolve by precedence
        if qualifying:
            winning = min(qualifying, key=lambda s: AVASTHA_PRECEDENCE.index(s))
            cond, outcome = AVASTHA_OUTCOMES[winning]

            # Pariheena receives degree-band nuance per Atul's audit
            # (a 1° Pisces Saturn ≠ 29° Pisces Saturn).
            condition_enriched = cond
            if winning == 'Pariheena' and deg_band is not None:
                if band_key in ('culminating', 'sandhi'):
                    condition_enriched = (
                        f"{cond} — Pariheena (Strong): "
                        "the planet is frantically retreating before its fall."
                    )
                elif band_key == 'sadyo_gata':
                    condition_enriched = (
                        f"{cond} — Pariheena (Trace): "
                        "fresh into the sign; the debility is a distant fear."
                    )
                elif band_key == 'udaya':
                    condition_enriched = (
                        f"{cond} — Pariheena (Forming): "
                        "long road ahead; success is possible via patience."
                    )

            # Avastha+Band cross-product synthesis (Atul's "Thwarted Power" fix)
            # Now also passes the planet's house from Lagna so that dusthana
            # placement (6/8/12) can dampen the label correctly — preventing
            # mismatches like a Deepta Moon in H8 being labelled 'Last Hurrah'
            # or 'Full Power' when it should read as 'Brittle Failure' /
            # 'Thwarted Power'.
            lagna_sign = chart_data.get('lagna_sign', 0)
            p_sign = pdata.get('sign_index')
            house_from_lagna = (((p_sign - lagna_sign) % 12) + 1) if p_sign is not None else None
            synthesis = compute_avastha_band_synthesis(winning, band_key, house_from_lagna)

            result[planet_name] = {
                'avastha': winning,
                'condition': condition_enriched,
                'outcome': outcome,
                'priority_index': AVASTHA_PRECEDENCE.index(winning),
                'all_qualifying': qualifying,
                'degree_band': deg_band,
                'house_from_lagna': house_from_lagna,
                'synthesis_label': synthesis['synthesis_label'],
                'synthesis_narrative': synthesis['synthesis_narrative'],
                'dusthana_dampened': synthesis.get('dusthana_dampened', False),
            }
        else:
            lagna_sign = chart_data.get('lagna_sign', 0)
            p_sign = pdata.get('sign_index')
            house_from_lagna = (((p_sign - lagna_sign) % 12) + 1) if p_sign is not None else None
            synthesis = compute_avastha_band_synthesis('Neutral', band_key, house_from_lagna)
            result[planet_name] = {
                'avastha': 'Neutral',
                'condition': 'No specific state qualified',
                'outcome': 'Mixed / Mediocre results',
                'priority_index': 99,
                'all_qualifying': [],
                'degree_band': deg_band,
                'house_from_lagna': house_from_lagna,
                'synthesis_label': synthesis['synthesis_label'],
                'synthesis_narrative': synthesis['synthesis_narrative'],
                'dusthana_dampened': synthesis.get('dusthana_dampened', False),
            }

    return result


# =================================================================
# SECTION 1E: BHAVA BALA MATRIX (25 / 50 / 75 / 100 %)
# =================================================================

def compute_bhava_bala(chart_data: Dict, house_num: int) -> Dict:
    """
    Compute the strength of a given Bhava (house) per the Prashna corpus matrix.
    Extends the corpus's Lagna-only spec to all 12 houses, substituting the
    target house cusp + house lord + Moon as the three pivots.

    Strength tiers:
      25%   – Benefic aspects the house but not its lord
      50%   – The same benefic aspects both the house and its lord
      75%   – The house lord plus 2 or more benefics aspect the house
      100%  – House cusp + lord + Moon all touched by benefics with no malefic aspect

    Net strength: gross % minus 10 for each malefic aspect on the house or its lord.
    """
    if house_num < 1 or house_num > 12:
        return {'error': 'house_num must be in 1..12'}

    planets = chart_data['planets']
    lagna_sign_idx = chart_data.get('lagna_sign', 0)
    house_sign_idx = (lagna_sign_idx + house_num - 1) % 12
    house_cusp_lon = house_sign_idx * 30.0   # Whole-sign: cusp = start of sign
    house_lord = SIGN_LORDS[house_sign_idx]

    moon_lon = planets.get('Moon', {}).get('longitude')
    lord_lon = planets.get(house_lord, {}).get('longitude')

    def touches(planet: str, target_lon: Optional[float]) -> bool:
        if target_lon is None:
            return False
        p_lon = planets.get(planet, {}).get('longitude')
        if p_lon is None:
            return False
        return _within_aspect_orb(p_lon, target_lon,
                                  DEEPTAMSHA.get(planet, 8.0),
                                  DEEPTAMSHA.get('Moon', 12.0) if target_lon == moon_lon else 0.0)

    benefics_to_house = [b for b in BENEFICS if touches(b, house_cusp_lon)]
    benefics_to_lord  = [b for b in BENEFICS
                         if b != house_lord and touches(b, lord_lon)]
    benefics_to_moon  = [b for b in BENEFICS
                         if b != 'Moon' and touches(b, moon_lon)]

    malefics_to_house = [m for m in ['Mars', 'Saturn'] if touches(m, house_cusp_lon)]
    malefics_to_lord  = [m for m in ['Mars', 'Saturn']
                         if m != house_lord and touches(m, lord_lon)]
    malefics_to_moon  = [m for m in ['Mars', 'Saturn']
                         if touches(m, moon_lon)]

    lord_aspects_house = touches(house_lord, house_cusp_lon)

    triggers: List[str] = []
    pct = 0

    # 100% — strictest
    if (benefics_to_house and benefics_to_lord and benefics_to_moon
            and not malefics_to_house and not malefics_to_lord
            and not malefics_to_moon):
        pct = 100
        triggers.append("100% — house, lord, and Moon all touched by benefics; no malefic interference")

    # 75% — lord aspects house AND ≥2 benefics aspect house
    elif lord_aspects_house and len(benefics_to_house) >= 2:
        pct = 75
        triggers.append(
            f"75% — house lord ({house_lord}) plus "
            f"{len(benefics_to_house)} benefics aspect the house"
        )

    # 50% — same benefic aspects both house and lord
    elif benefics_to_house and benefics_to_lord:
        common = set(benefics_to_house) & set(benefics_to_lord)
        if common:
            pct = 50
            triggers.append(
                f"50% — benefic(s) {', '.join(sorted(common))} "
                f"aspect both the house and its lord"
            )
        else:
            pct = 25
            triggers.append("25% — separate benefics aspect house and lord, but none aspects both")

    # 25% — benefic aspects house only
    elif benefics_to_house:
        pct = 25
        triggers.append(
            f"25% — benefic(s) {', '.join(benefics_to_house)} "
            f"aspect the house but not its lord"
        )

    # Afflictions
    afflictions: List[str] = []
    for m in malefics_to_house:
        afflictions.append(f"{m} aspects the house")
    for m in malefics_to_lord:
        afflictions.append(f"{m} aspects the house lord ({house_lord})")

    net = max(0, pct - 10 * len(afflictions))

    if net >= 90:
        verdict = 'full'
    elif net >= 65:
        verdict = 'strong'
    elif net >= 40:
        verdict = 'modest'
    else:
        verdict = 'weak'

    return {
        'house_num': house_num,
        'house_sign': SIGNS[house_sign_idx],
        'house_sign_sanskrit': SIGN_SANSKRIT[house_sign_idx],
        'house_lord': house_lord,
        'gross_strength_pct': pct,
        'net_strength_pct': net,
        'verdict': verdict,
        'triggers_fired': triggers,
        'malefic_afflictions': afflictions,
        'benefics_to_house': benefics_to_house,
        'benefics_to_lord': benefics_to_lord,
        'benefics_to_moon': benefics_to_moon,
    }


# =================================================================
# END OF PHASE 1A–1E
# =================================================================


# =================================================================
# SECTION 1F: TAJIK ASPECT ENGINE (PRASHNA-FLAVORED)
# =================================================================
# Detects Ithesal / Esrapha / Ikkavala / Nakta / Kambool yogas
# between planets using the HARDCODED CLASSICAL VELOCITY HIERARCHY
# (locked decision #4) — NOT instantaneous ephemeris speeds.
#
# Yoga summary:
#   Ithesal (Muthasila):  faster planet BEHIND slower, within orb (applying).
#                         Auspicious — manifestation of result.
#   Esrapha (Musarif):    faster planet AHEAD of slower, within orb (separating).
#                         Result has passed; opportunity lost.
#   Ikkavala / Vartaman:  near-exact conjunction (within ~1°).
#                         Use definite language — event is "now".
#   Nakta:                no direct aspect, but a faster bridge planet sits
#                         between the two longitudes. Mediated success.
#   Kambool:              Moon in Ithesal with a target planet. Moon's blessing.
# =================================================================

VARTAMAN_ORB = 1.0  # degrees — used for Ikkavala / "exact" classification


def get_faster_planet(p_a: str, p_b: str) -> Optional[str]:
    """Return the faster of two planets per VELOCITY_HIERARCHY, or None if either is unknown."""
    if p_a not in VELOCITY_HIERARCHY or p_b not in VELOCITY_HIERARCHY:
        return None
    return p_a if VELOCITY_HIERARCHY.index(p_a) < VELOCITY_HIERARCHY.index(p_b) else p_b


def signed_separation(lon_faster: float, lon_slower: float) -> float:
    """
    Signed angular separation: faster − slower, mapped to (−180, +180].
    Negative ⇒ faster is BEHIND slower (will catch up) → applying / Ithesal.
    Positive ⇒ faster is AHEAD of slower (has already passed) → separating / Esrapha.
    """
    d = (lon_faster - lon_slower) % 360.0
    if d > 180.0:
        d -= 360.0
    return d


# =================================================================
# PHALA-KAALA · 4-VECTOR TIMING ENGINE (Phase 4D-Extended)
# =================================================================
# Implements the four canonical Tajik/Prashna timing vectors:
#
#   1. STANDARD            — degree distance L1 ↔ target lord,
#                             motility-scaled to days/weeks/months
#   2. DERIVED             — degree distance L1 ↔ derived-house lord
#                             (Bhavat Bhavam — e.g. L6 for child's voice)
#   3. BINDER              — degree distance to Yama/Nakta midpoint lock
#   4. ORB_CLEARANCE       — degree distance to clear/enter 12° Tajik orb
#
# Mean daily motion (degrees/day, tropical) — used when ephemeris-derived
# velocity isn't available on the chart object.
# =================================================================

DAILY_MEAN_MOTION_DEG = {
    'Sun':     0.9856,
    'Moon':   13.1764,
    'Mercury': 1.3833,   # mean; varies dramatically
    'Venus':   1.6021,   # mean; varies
    'Mars':    0.5240,   # mean; slow when retro
    'Jupiter': 0.0831,
    'Saturn':  0.0335,
    'Rahu':    0.0529,
    'Ketu':    0.0529,
}

# Sign motility class — drives the time-unit scaling for the Standard vector.
# Movable (Chara) signs:    fast results (days)
# Dual (Dvisvabhava) signs: medium results (weeks)
# Fixed (Sthira) signs:     slow results (months)
SIGN_MOTILITY = {
    0:  'movable',   # Aries
    1:  'fixed',     # Taurus
    2:  'dual',      # Gemini
    3:  'movable',   # Cancer
    4:  'fixed',     # Leo
    5:  'dual',      # Virgo
    6:  'movable',   # Libra
    7:  'fixed',     # Scorpio
    8:  'dual',      # Sagittarius
    9:  'movable',   # Capricorn
    10: 'fixed',     # Aquarius
    11: 'dual',      # Pisces
}

MOTILITY_UNIT = {
    'movable': 'days',
    'dual':    'weeks',
    'fixed':   'months',
}


def _get_planet_velocity(planet_name: str, chart_data: Dict) -> float:
    """
    Returns daily motion in degrees. Prefers ephemeris-derived velocity
    from chart_data['planets'][p]['daily_motion'] if present;
    falls back to mean motion constants.
    """
    p = (chart_data.get('planets') or {}).get(planet_name) or {}
    v = p.get('daily_motion') or p.get('velocity')
    if v is not None and v != 0:
        return abs(float(v))
    return DAILY_MEAN_MOTION_DEG.get(planet_name, 1.0)


def _get_planet_longitude(planet_name: str, chart_data: Dict) -> Optional[float]:
    p = (chart_data.get('planets') or {}).get(planet_name) or {}
    lon = p.get('longitude')
    if lon is None: return None
    return float(lon) % 360.0


def _get_planet_signed_velocity(planet_name: str, chart_data: Dict) -> float:
    """
    Returns SIGNED daily motion in degrees: positive for direct motion,
    negative for retrograde. Used for relative-velocity computation in
    timing engines (Karmika & Yaatra Rule 3 — velocity-to-distance).

    For "which planet is faster" comparisons (motility selection),
    callers should continue using _get_planet_velocity (abs value).
    """
    p = (chart_data.get('planets') or {}).get(planet_name) or {}
    is_retro = bool(p.get('retrograde', False))
    abs_vel = _get_planet_velocity(planet_name, chart_data)
    return -abs_vel if is_retro else abs_vel


def _compute_signed_relative_velocity(p1: str, p2: str,
                                       chart_data: Dict) -> Tuple[float, str]:
    """
    Returns (rel_vel, approach_kind) per Karmika & Yaatra Rule 3:

        Δt = θ / |V_L1 ± V_Target|
        + (sum) when one planet is retrograde, one direct (mutual approach)
        - (difference) when both same direction (chase)

    Using SIGNED velocities, `abs(v1_signed - v2_signed)` resolves all four
    cases correctly:
      - both direct:    abs(+a - +b) = |a - b|        (chase)
      - one retrograde: abs(+a - -b) = |a + b|        (mutual approach)
      - both retrograde:abs(-a - -b) = |b - a|        (chase, reversed)

    approach_kind is 'chase' or 'mutual_approach' (informational).
    """
    v1_s = _get_planet_signed_velocity(p1, chart_data)
    v2_s = _get_planet_signed_velocity(p2, chart_data)
    rel_vel = abs(v1_s - v2_s)
    if rel_vel < 0.001:
        rel_vel = max(abs(v1_s), abs(v2_s), 0.01)
    # Detect retrograde-direct configuration (mutual approach)
    p1_retro = (chart_data.get('planets') or {}).get(p1, {}).get('retrograde', False)
    p2_retro = (chart_data.get('planets') or {}).get(p2, {}).get('retrograde', False)
    approach_kind = 'mutual_approach' if (p1_retro != p2_retro) else 'chase'
    return rel_vel, approach_kind


def _check_reversal_at_border(faster_planet: str, slower_planet: str,
                                deg_remaining: float,
                                chart_data: Dict) -> Optional[Dict]:
    """
    Karmika & Yaatra Rule 3 Guardrail:
    If the FASTER planet is Stationary Retrograde within 1° of completing
    an Ithesal/approach, the timing window must append the modifier
    REVERSAL_AT_THE_BORDER (trip aborted at the gate, expat recalled).

    Stationary = |daily motion| < 0.15° (well below mean motion for any
    of the 7 classical planets and Rahu/Ketu).

    Returns dict with verdict_modifier + narrative, or None if not triggered.
    """
    if deg_remaining > 1.0:
        return None
    p = (chart_data.get('planets') or {}).get(faster_planet) or {}
    is_retro = bool(p.get('retrograde', False))
    abs_vel = _get_planet_velocity(faster_planet, chart_data)
    # Stationary threshold: well under each planet's mean motion
    STATIONARY_THRESHOLD = {
        'Sun': 0.50, 'Moon': 6.00, 'Mercury': 0.60, 'Venus': 0.70,
        'Mars': 0.25, 'Jupiter': 0.04, 'Saturn': 0.02,
        'Rahu': 0.03, 'Ketu': 0.03,
    }
    threshold = STATIONARY_THRESHOLD.get(faster_planet, 0.10)
    is_stationary = abs_vel < threshold
    if not (is_retro and is_stationary):
        return None
    return {
        'verdict_modifier': 'REVERSAL_AT_THE_BORDER',
        'narrative': (
            f'{faster_planet} is Stationary Retrograde within '
            f'{round(deg_remaining, 2)}° of completing the approach to '
            f'{slower_planet}. The Ithesal is mathematically at the gate but '
            f'will not close — the trip is aborted at the boundary, or the '
            f'authority recalls the candidate before the appointment is '
            f'formalized. Treat the outcome as already withdrawn.'
        ),
        'faster_planet': faster_planet,
        'is_retrograde': True,
        'is_stationary': True,
        'abs_velocity': round(abs_vel, 4),
        'deg_remaining': round(deg_remaining, 3),
    }


def _angular_separation(lon_a: float, lon_b: float) -> float:
    """Smallest unsigned angular distance, 0..180."""
    d = abs((lon_a - lon_b) % 360.0)
    return d if d <= 180.0 else 360.0 - d


def _applying_or_separating(lon_a: float, lon_b: float,
                              vel_a: float, vel_b: float) -> str:
    """
    Returns 'applying' if the two planets are approaching aspect,
    'separating' if moving apart. Uses signed angular gap delta.
    """
    # Position the faster planet's relative motion vs the slower.
    # Simpler heuristic: if (lon_faster - lon_slower) mod 360 is decreasing
    # toward 0, we're applying.
    if vel_a >= vel_b:
        gap = (lon_a - lon_b) % 360.0
        # If gap > 180, the faster is "behind" and applying clockwise;
        # else gap is decreasing and we're applying.
        return 'applying' if gap > 180.0 else 'separating'
    else:
        gap = (lon_b - lon_a) % 360.0
        return 'applying' if gap > 180.0 else 'separating'


def compute_phal_kaal(chart_data: Dict, vector_type: str,
                       **params) -> Dict:
    """
    Universal phala-kaala (result-time) engine. Returns a dict with
    {amount, unit, narrative, vector_type, motility, data}.

    Vector types:
      'standard'      — degree distance from Lagna lord to target lord.
                        params: target_house (int 1-12)
      'derived'       — Bhavat Bhavam: degree distance from Lagna lord to
                        a derived house lord (e.g. 2nd-from-5th = 6th for
                        child's speech).
                        params: derived_house (int 1-12)
      'binder'        — degree distance to completion of a Yama/Nakta
                        midpoint lock between two specified planets.
                        params: p1 (str), p2 (str)
      'orb_clearance' — degree distance for two planets to clear (or enter)
                        the 12° Tajik orb. Used for severance/extrication.
                        params: p1 (str), p2 (str),
                                direction: 'clear' (exit orb) or 'enter'.
    """
    lagna_sign = chart_data.get('lagna_sign', 0)
    lagna_lord = SIGN_LORDS[lagna_sign]
    l1_lon = _get_planet_longitude(lagna_lord, chart_data)
    l1_vel = _get_planet_velocity(lagna_lord, chart_data)

    if l1_lon is None:
        return {
            'vector_type': vector_type,
            'amount': None, 'unit': None,
            'narrative': 'Cannot compute timing — Lagna lord longitude unavailable.',
            'motility': None,
            'data': {'error': 'lagna_lord_no_longitude'},
        }

    # ── 1. STANDARD ──────────────────────────────────────────────
    if vector_type == 'standard':
        target_house = params.get('target_house', 7)
        target_sign  = (lagna_sign + target_house - 1) % 12
        target_lord  = SIGN_LORDS[target_sign]
        target_lon   = _get_planet_longitude(target_lord, chart_data)
        target_vel   = _get_planet_velocity(target_lord, chart_data)
        if target_lon is None:
            return {'vector_type': 'standard', 'amount': None, 'unit': None,
                    'narrative': f'Target lord {target_lord} longitude unavailable.',
                    'motility': None, 'data': {}}

        # Motility is taken from the FASTER planet's current sign
        faster, faster_sign = (lagna_lord, lagna_sign) if l1_vel >= target_vel \
                              else (target_lord, target_sign)
        # Use the faster planet's CURRENT sign (not nominal house sign)
        faster_curr_sign = int(_get_planet_longitude(faster, chart_data) // 30) % 12
        motility = SIGN_MOTILITY[faster_curr_sign]
        unit = MOTILITY_UNIT[motility]

        deg_dist = _angular_separation(l1_lon, target_lon)
        # SIGNED relative motion (Karmika Rule 3): handles retrograde-direct
        # approach correctly via abs(v_signed_1 - v_signed_2).
        rel_vel, approach_kind = _compute_signed_relative_velocity(
            lagna_lord, target_lord, chart_data)
        days = deg_dist / rel_vel

        # Reversal-at-the-border guardrail
        reversal = _check_reversal_at_border(
            faster, target_lord if faster == lagna_lord else lagna_lord,
            deg_dist, chart_data)

        # Convert to motility-appropriate unit
        if unit == 'days':
            amount = round(days, 1)
        elif unit == 'weeks':
            amount = round(days / 7.0, 1)
        else:  # months
            amount = round(days / 30.4, 1)

        return {
            'vector_type': 'standard',
            'amount':      amount,
            'unit':        unit,
            'narrative':   (f'Result horizon ≈ {amount} {unit}: '
                            f'{lagna_lord} (L1) and {target_lord} (L{target_house}) '
                            f'close their {round(deg_dist, 2)}° gap at {round(rel_vel, 3)}°/day; '
                            f'faster planet ({faster}) is in {motility} sign — '
                            f'time unit scales to {unit}.'),
            'motility':    motility,
            'approach_kind': approach_kind,
            'verdict_modifier': reversal['verdict_modifier'] if reversal else None,
            'reversal_at_border': reversal,
            'data': {
                'lagna_lord':   lagna_lord, 'l1_longitude': round(l1_lon, 3),
                'l1_velocity':  round(l1_vel, 3),
                'target_lord':  target_lord, 'target_house': target_house,
                'target_longitude': round(target_lon, 3),
                'target_velocity':  round(target_vel, 3),
                'deg_dist':     round(deg_dist, 3),
                'rel_vel':      round(rel_vel, 3),
                'days_raw':     round(days, 2),
                'faster_planet': faster,
                'faster_curr_sign': faster_curr_sign,
                'approach_kind': approach_kind,
            },
        }

    # ── 2. DERIVED ATTRIBUTE (Bhavat Bhavam) ────────────────────
    if vector_type == 'derived':
        derived_house = params['derived_house']
        derived_sign  = (lagna_sign + derived_house - 1) % 12
        derived_lord  = SIGN_LORDS[derived_sign]
        derived_lon   = _get_planet_longitude(derived_lord, chart_data)
        derived_vel   = _get_planet_velocity(derived_lord, chart_data)
        if derived_lon is None:
            return {'vector_type': 'derived', 'amount': None, 'unit': None,
                    'narrative': f'Derived lord {derived_lord} longitude unavailable.',
                    'motility': None, 'data': {}}

        # Motility from the derived lord's CURRENT sign
        d_curr_sign = int(derived_lon // 30) % 12
        motility = SIGN_MOTILITY[d_curr_sign]
        unit = MOTILITY_UNIT[motility]

        deg_dist = _angular_separation(l1_lon, derived_lon)
        rel_vel, approach_kind = _compute_signed_relative_velocity(
            lagna_lord, derived_lord, chart_data)
        days = deg_dist / rel_vel

        # Reversal-at-the-border check (faster of the two)
        faster_d = lagna_lord if l1_vel >= derived_vel else derived_lord
        slower_d = derived_lord if l1_vel >= derived_vel else lagna_lord
        reversal_d = _check_reversal_at_border(faster_d, slower_d, deg_dist, chart_data)

        amount = round(days, 1) if unit == 'days' else \
                 round(days / 7.0, 1) if unit == 'weeks' else \
                 round(days / 30.4, 1)

        return {
            'vector_type': 'derived',
            'amount':      amount,
            'unit':        unit,
            'narrative':   (f'Derived-attribute horizon ≈ {amount} {unit}: '
                            f'{lagna_lord} (L1) closes its gap to {derived_lord} '
                            f'(L{derived_house} · Bhavat Bhavam) over '
                            f'{round(deg_dist, 2)}° at {round(rel_vel, 3)}°/day; '
                            f'derived lord is in a {motility} sign.'),
            'motility':    motility,
            'approach_kind': approach_kind,
            'verdict_modifier': reversal_d['verdict_modifier'] if reversal_d else None,
            'reversal_at_border': reversal_d,
            'data': {
                'derived_house': derived_house, 'derived_lord': derived_lord,
                'derived_longitude': round(derived_lon, 3),
                'derived_velocity': round(derived_vel, 3),
                'deg_dist': round(deg_dist, 3), 'rel_vel': round(rel_vel, 3),
                'days_raw': round(days, 2),
                'lagna_lord': lagna_lord,
                'approach_kind': approach_kind,
            },
        }

    # ── 3. BINDER (Yama / Nakta midpoint lock) ──────────────────
    if vector_type == 'binder':
        p1, p2 = params['p1'], params['p2']
        lon1, lon2 = _get_planet_longitude(p1, chart_data), _get_planet_longitude(p2, chart_data)
        vel1, vel2 = _get_planet_velocity(p1, chart_data),  _get_planet_velocity(p2, chart_data)
        if lon1 is None or lon2 is None:
            return {'vector_type': 'binder', 'amount': None, 'unit': None,
                    'narrative': f'{p1} or {p2} longitude unavailable.',
                    'motility': None, 'data': {}}

        # Midpoint of the two longitudes
        midpoint = ((lon1 + lon2) / 2.0) % 360.0
        # Faster planet's distance to the midpoint
        faster, fast_lon, fast_vel = (p1, lon1, vel1) if vel1 >= vel2 else (p2, lon2, vel2)
        slower, slow_lon, slow_vel = (p2, lon2, vel2) if vel1 >= vel2 else (p1, lon1, vel1)

        deg_to_midpoint = _angular_separation(fast_lon, midpoint)
        # SIGNED rel-vel: closure rate of faster onto the midpoint, retrograde-aware
        rel_vel, approach_kind = _compute_signed_relative_velocity(p1, p2, chart_data)
        days = deg_to_midpoint / rel_vel

        # Motility from the faster planet's current sign
        fast_curr_sign = int(fast_lon // 30) % 12
        motility = SIGN_MOTILITY[fast_curr_sign]
        unit = MOTILITY_UNIT[motility]

        amount = round(days, 1) if unit == 'days' else \
                 round(days / 7.0, 1) if unit == 'weeks' else \
                 round(days / 30.4, 1)

        return {
            'vector_type': 'binder',
            'amount':      amount,
            'unit':        unit,
            'narrative':   (f'Binder midpoint lock ≈ {amount} {unit}: '
                            f'{faster} closes {round(deg_to_midpoint, 2)}° to the '
                            f'{p1}↔{p2} midpoint at {round(rel_vel, 3)}°/day.'),
            'motility':    motility,
            'data': {
                'p1': p1, 'p2': p2,
                'lon1': round(lon1, 3), 'lon2': round(lon2, 3),
                'midpoint': round(midpoint, 3),
                'faster': faster, 'slower': slower,
                'deg_to_midpoint': round(deg_to_midpoint, 3),
                'rel_vel': round(rel_vel, 3),
                'days_raw': round(days, 2),
            },
        }

    # ── 4. ORB CLEARANCE (Hidden / Severance) ───────────────────
    if vector_type == 'orb_clearance':
        p1, p2 = params['p1'], params['p2']
        direction = params.get('direction', 'clear')  # 'clear' or 'enter'
        lon1, lon2 = _get_planet_longitude(p1, chart_data), _get_planet_longitude(p2, chart_data)
        vel1, vel2 = _get_planet_velocity(p1, chart_data),  _get_planet_velocity(p2, chart_data)
        if lon1 is None or lon2 is None:
            return {'vector_type': 'orb_clearance', 'amount': None, 'unit': None,
                    'narrative': f'{p1} or {p2} longitude unavailable.',
                    'motility': None, 'data': {}}

        current_sep = _angular_separation(lon1, lon2)
        rel_vel, approach_kind = _compute_signed_relative_velocity(p1, p2, chart_data)

        if direction == 'clear':
            # Time to exceed 12° orb
            if current_sep >= 12.0:
                gap = 0
                narrative = (f'{p1} and {p2} are already separated by '
                             f'{round(current_sep, 2)}° — orb has cleared.')
                days = 0
            else:
                gap = 12.0 - current_sep
                days = gap / rel_vel
                narrative = (f'Severance horizon ≈ {round(days, 1)} days: '
                             f'{p1} and {p2} need {round(gap, 2)}° more to clear '
                             f'the 12° Tajik orb at {round(rel_vel, 3)}°/day.')
        else:  # 'enter'
            if current_sep <= 12.0:
                gap = 0
                narrative = (f'{p1} and {p2} are already within 12° — '
                             f'orb is active.')
                days = 0
            else:
                gap = current_sep - 12.0
                days = gap / rel_vel
                narrative = (f'Orb-entry horizon ≈ {round(days, 1)} days: '
                             f'{p1} and {p2} close from {round(current_sep, 2)}° '
                             f'to within 12° at {round(rel_vel, 3)}°/day.')

        # Always report in days for orb-clearance (high-precision events)
        return {
            'vector_type': 'orb_clearance',
            'amount':      round(days, 1),
            'unit':        'days',
            'narrative':   narrative,
            'motility':    None,
            'data': {
                'p1': p1, 'p2': p2, 'direction': direction,
                'current_sep': round(current_sep, 3),
                'rel_vel': round(rel_vel, 3),
                'gap_remaining': round(gap, 3),
                'orb_status': 'cleared' if (direction == 'clear' and current_sep >= 12.0)
                              else ('active' if (direction == 'enter' and current_sep <= 12.0)
                                    else 'in_motion'),
            },
        }

    raise ValueError(f"Unknown vector_type '{vector_type}'. "
                     f"Expected one of: standard, derived, binder, orb_clearance")


def pairwise_aspect(p_a: str, p_b: str, chart_data: Dict) -> Dict:
    """
    Compute the Tajik aspect between two named planets in a given chart.

    Returns dict:
        planet_a, planet_b:      original names
        faster, slower:          per hierarchy
        signed_separation:       degrees (−180, +180], faster − slower
        absolute_separation:     |signed|
        within_orb:              bool — within max(Deeptamsha) of the two
        orb_used:                the larger Deeptamsha
        yoga:                    'Ithesal' | 'Esrapha' | 'Ikkavala' | 'None'
        is_vartaman:             True if abs sep ≤ VARTAMAN_ORB (use definite language)
        narrative:               short human description
    """
    planets = chart_data.get('planets', {})
    if p_a not in planets or p_b not in planets:
        return {'error': f'Planet(s) not in chart: {p_a}, {p_b}'}

    lon_a = planets[p_a].get('longitude')
    lon_b = planets[p_b].get('longitude')
    if lon_a is None or lon_b is None:
        return {'error': f'Missing longitudes for {p_a}/{p_b}'}

    faster = get_faster_planet(p_a, p_b)
    if faster is None:
        return {'error': f'Velocity hierarchy unknown for {p_a}/{p_b}'}
    slower = p_b if faster == p_a else p_a

    lon_faster = planets[faster]['longitude']
    lon_slower = planets[slower]['longitude']
    sep = signed_separation(lon_faster, lon_slower)
    abs_sep = abs(sep)
    orb = max(DEEPTAMSHA.get(p_a, 8.0), DEEPTAMSHA.get(p_b, 8.0))

    within = abs_sep <= orb
    is_vartaman = abs_sep <= VARTAMAN_ORB

    if not within:
        yoga = 'None'
        narrative = (f"{faster} and {slower} are {abs_sep:.1f}° apart — "
                     f"outside the {orb:.1f}° orb. No direct aspect.")
    elif is_vartaman:
        yoga = 'Ikkavala'
        narrative = (f"{faster} and {slower} are within {abs_sep:.2f}° — "
                     f"Ikkavala / Vartaman (effectively conjunct). "
                     f"Event is unfolding now.")
    elif sep < 0:
        yoga = 'Ithesal'
        narrative = (f"{faster} ({abs_sep:.1f}° behind {slower}) is applying to {slower} "
                     f"within orb. Ithesal — result will manifest.")
    else:
        yoga = 'Esrapha'
        narrative = (f"{faster} ({abs_sep:.1f}° past {slower}) has separated from {slower}. "
                     f"Esrapha — opportunity is in the past.")

    return {
        'planet_a': p_a,
        'planet_b': p_b,
        'faster': faster,
        'slower': slower,
        'signed_separation': round(sep, 4),
        'absolute_separation': round(abs_sep, 4),
        'within_orb': within,
        'orb_used': orb,
        'yoga': yoga,
        'is_vartaman': is_vartaman,
        'narrative': narrative,
    }


def detect_nakta(p_a: str, p_b: str, chart_data: Dict) -> Optional[Dict]:
    """
    Detect Nakta yoga between p_a and p_b: when they are NOT in direct aspect,
    but a third planet (faster than both) sits at a longitude BETWEEN theirs
    and is in Ithesal-range with both. The bridge planet mediates the result.

    Returns dict if Nakta found, else None.
    """
    planets = chart_data.get('planets', {})
    if p_a not in planets or p_b not in planets:
        return None

    direct = pairwise_aspect(p_a, p_b, chart_data)
    if direct.get('within_orb'):
        return None  # Direct aspect exists — Nakta is for non-aspecting pairs

    lon_a = planets[p_a].get('longitude')
    lon_b = planets[p_b].get('longitude')
    if lon_a is None or lon_b is None:
        return None

    # Sort by longitude for the "between" check
    if lon_a <= lon_b:
        lo_planet, lo_lon = p_a, lon_a
        hi_planet, hi_lon = p_b, lon_b
    else:
        lo_planet, lo_lon = p_b, lon_b
        hi_planet, hi_lon = p_a, lon_a

    # Examine if the arc (hi - lo) is the "short way"; otherwise wrap-around is the short way.
    short_arc_is_direct = (hi_lon - lo_lon) <= 180.0

    a_idx = VELOCITY_HIERARCHY.index(p_a) if p_a in VELOCITY_HIERARCHY else 99
    b_idx = VELOCITY_HIERARCHY.index(p_b) if p_b in VELOCITY_HIERARCHY else 99
    min_idx = min(a_idx, b_idx)  # bridge must be FASTER than both

    bridge_candidates = []
    near_misses = []  # Atul's audit: show why almost-bridges failed
    for bridge in VELOCITY_HIERARCHY[:min_idx]:
        if bridge in (p_a, p_b):
            continue
        b_lon = planets.get(bridge, {}).get('longitude')
        if b_lon is None:
            continue
        # Check if bridge is between lo and hi
        if short_arc_is_direct:
            between = lo_lon <= b_lon <= hi_lon
        else:
            between = (b_lon >= hi_lon) or (b_lon <= lo_lon)
        if not between:
            continue
        # Bridge must be in Ithesal range (applying) with BOTH
        asp_with_a = pairwise_aspect(bridge, p_a, chart_data)
        asp_with_b = pairwise_aspect(bridge, p_b, chart_data)
        if asp_with_a.get('within_orb') and asp_with_b.get('within_orb'):
            bridge_candidates.append({
                'bridge': bridge,
                'bridge_lon': b_lon,
                'aspect_with_a': asp_with_a['yoga'],
                'aspect_with_b': asp_with_b['yoga'],
            })
        else:
            # Near-miss: in the arc but failed the orb check on one side.
            # Show our work so the user sees what was tried.
            failed_a = not asp_with_a.get('within_orb')
            failed_b = not asp_with_b.get('within_orb')
            is_retrograde = planets.get(bridge, {}).get('retrograde', False)
            reason_parts = []
            if failed_a:
                reason_parts.append(
                    f"too far from {p_a} "
                    f"({asp_with_a.get('absolute_separation', 0):.1f}° "
                    f"vs orb {asp_with_a.get('orb_used', 0):.1f}°)"
                )
            if failed_b:
                reason_parts.append(
                    f"too far from {p_b} "
                    f"({asp_with_b.get('absolute_separation', 0):.1f}° "
                    f"vs orb {asp_with_b.get('orb_used', 0):.1f}°)"
                )
            if is_retrograde:
                reason_parts.append("retrograde (advice would backfire)")

            # Identify what this would-be bridge does narratively if it had qualified
            bridge_role_hint = None
            l_idx = chart_data.get('lagna_sign')
            if l_idx is not None:
                br_signs = _sign_lord_signs(bridge)
                houses_ruled = sorted({((s - l_idx) % 12) + 1 for s in br_signs})
                if 3 in houses_ruled:
                    bridge_role_hint = "would have been a sibling/peer mediator"
                elif 9 in houses_ruled:
                    bridge_role_hint = "would have been an elder/guru bridge"
                elif bridge == 'Venus':
                    bridge_role_hint = "would have been a romantic catalyst"
                elif 5 in houses_ruled:
                    bridge_role_hint = "would have been an advisor mediator"
                elif 11 in houses_ruled:
                    bridge_role_hint = "would have been a friend-network bridge"

            near_misses.append({
                'candidate': bridge,
                'candidate_lon': round(b_lon, 2),
                'retrograde': is_retrograde,
                'failure_reasons': reason_parts,
                'would_have_been': bridge_role_hint,
                'narrative': (
                    f"{bridge} sits in the arc between {p_a} and {p_b} and "
                    f"{bridge_role_hint or 'would have been a useful intermediary'}, "
                    "but " + " AND ".join(reason_parts) + "."
                ),
            })

    if not bridge_candidates:
        # Return near-miss info even when no qualifying bridge — Atul's transparency fix
        if near_misses:
            return {
                'planet_a': p_a,
                'planet_b': p_b,
                'bridge': None,
                'bridge_role': None,
                'bridge_role_narrative': None,
                'near_misses': near_misses,
                'all_bridges': [],
                'narrative': (
                    f"No Nakta bridge qualified between {p_a} and {p_b}, but "
                    f"{len(near_misses)} candidate(s) came close — see near_misses "
                    "for the audit trail."
                ),
            }
        return None

    # Pick the fastest qualifying bridge (first in hierarchy)
    bridge_candidates.sort(key=lambda x: VELOCITY_HIERARCHY.index(x['bridge']))
    primary = bridge_candidates[0]
    bridge_planet = primary['bridge']

    # Identify the bridge's classical role (Atul's enrichment).
    # The role depends on the Lagna of the chart — what house does this
    # bridge planet RULE relative to the Prashna Lagna?
    lagna_sign_idx = chart_data.get('lagna_sign')
    role_label = None
    role_narrative = None
    if lagna_sign_idx is not None:
        # Find which houses this bridge planet rules
        bridge_signs = _sign_lord_signs(bridge_planet)
        bridge_houses_ruled = sorted({
            ((s - lagna_sign_idx) % 12) + 1 for s in bridge_signs
        })

        # Map house rulership to relationship role
        if 3 in bridge_houses_ruled:
            role_label = 'Sibling / Neighbour Facilitator'
            role_narrative = (
                f"{bridge_planet} rules the 3rd house — a sibling, neighbour, "
                "or peer-level mediator facilitates the matter."
            )
        elif 9 in bridge_houses_ruled:
            role_label = 'Elder / Guru Bridge'
            role_narrative = (
                f"{bridge_planet} rules the 9th house — a parent, guru, or "
                "elder figure bridges the gap between the parties."
            )
        elif bridge_planet == 'Venus':
            role_label = 'Romantic Catalyst'
            role_narrative = (
                "Venus is the bridge — a common friend, romantic intermediary, "
                "or social catalyst delivers the result."
            )
        elif 5 in bridge_houses_ruled:
            role_label = 'Children / Counsel Mediator'
            role_narrative = (
                f"{bridge_planet} rules the 5th house — a child, advisor, or "
                "person of confidence mediates."
            )
        elif 11 in bridge_houses_ruled:
            role_label = 'Friend-Group / Network Mediator'
            role_narrative = (
                f"{bridge_planet} rules the 11th house — a friend-of-friend "
                "or wider network connection delivers the result."
            )
        else:
            houses_str = ', '.join(f'{h}th' for h in bridge_houses_ruled)
            role_label = 'Generic Intermediary'
            role_narrative = (
                f"{bridge_planet} rules the {houses_str} house — an "
                "intermediary from that life-area bridges the matter."
            )

    return {
        'planet_a': p_a,
        'planet_b': p_b,
        'bridge': bridge_planet,
        'bridge_lon': primary['bridge_lon'],
        'bridge_role': role_label,
        'bridge_role_narrative': role_narrative,
        'all_bridges': bridge_candidates,
        'narrative': (f"Nakta — {p_a} and {p_b} have no direct aspect, but "
                      f"{bridge_planet} bridges them. Result reaches the querent "
                      f"through a mediator."),
    }


# =================================================================
# YAMA BINDER — Tajik interception detection
# Per Atul's Sammana Ch.14 spec: a third planet sitting at the geometric
# midpoint of the L1→L11 (or L1→target) arc, within a 3.5° absolute orb,
# intercepts the light traveling between the two principal lords. Used
# by Sammana Overlay B (credit_theft_check) where L7 binding L1↔L11
# signals the boss intercepting peer/industry recognition.
# =================================================================

def is_yama_binder(principal_a: str, binder: str, principal_b: str,
                    chart_data: Dict, midpoint_orb: float = 3.5) -> Dict:
    """
    Detect whether `binder` is a Yama Binder intercepting the forward
    zodiacal arc from principal_a to principal_b.

    Two conditions:
        1. The binder's longitude falls zodiacally between principal_a
           and principal_b on the FORWARD arc (handles 0°/360° wrap).
        2. The binder is within `midpoint_orb` (default 3.5°) of the
           geometric midpoint of that forward arc.

    Returns dict:
        is_binder:                bool
        forward_arc_degrees:      float — the size of the a→b forward arc
        binder_position_on_arc:   float — distance from a along the arc
        midpoint_longitude:       float — geometric midpoint of the arc
        distance_from_midpoint:   float — absolute distance to midpoint
        reason:                   str   — why fired / why didn't
        narrative:                str   — human-readable summary
    """
    planets = chart_data.get('planets', {})
    lon_a  = planets.get(principal_a, {}).get('longitude')
    lon_b  = planets.get(binder,      {}).get('longitude')
    lon_c  = planets.get(principal_b, {}).get('longitude')

    if None in (lon_a, lon_b, lon_c):
        return {
            'is_binder': False,
            'reason': 'missing_longitude',
            'narrative': f"Cannot evaluate Yama Binder — longitude missing for one of "
                         f"{principal_a}/{binder}/{principal_b}.",
        }

    # Forward arc from principal_a to principal_b (zodiacal direction)
    forward_arc = (lon_c - lon_a) % 360.0

    if forward_arc < 0.01:
        return {
            'is_binder': False,
            'reason': 'principals_conjoined',
            'forward_arc_degrees': round(forward_arc, 4),
            'narrative': f"{principal_a} and {principal_b} are effectively conjoined "
                         f"({forward_arc:.2f}° apart) — no arc for a binder to intercept.",
        }

    # Binder's position along the forward arc (0 = at a, forward_arc = at b)
    binder_position = (lon_b - lon_a) % 360.0
    on_arc = 0.0 < binder_position < forward_arc

    if not on_arc:
        return {
            'is_binder': False,
            'reason': 'binder_off_arc',
            'forward_arc_degrees': round(forward_arc, 4),
            'binder_position_on_arc': round(binder_position, 4),
            'narrative': (f"{binder} at {lon_b:.2f}° is NOT zodiacally between "
                          f"{principal_a} ({lon_a:.2f}°) and {principal_b} ({lon_c:.2f}°) "
                          f"on the forward arc — no interception."),
        }

    # Geometric midpoint of the forward arc
    midpoint = (lon_a + forward_arc / 2.0) % 360.0
    # Absolute distance between binder and midpoint (shorter of the two arcs around the zodiac)
    d_forward  = (midpoint - lon_b) % 360.0
    d_backward = (lon_b - midpoint) % 360.0
    distance_from_midpoint = min(d_forward, d_backward)

    is_binder_flag = distance_from_midpoint <= midpoint_orb

    return {
        'is_binder': is_binder_flag,
        'forward_arc_degrees':    round(forward_arc, 4),
        'binder_position_on_arc': round(binder_position, 4),
        'midpoint_longitude':     round(midpoint, 4),
        'distance_from_midpoint': round(distance_from_midpoint, 4),
        'midpoint_orb_used':      midpoint_orb,
        'reason': 'binder_active' if is_binder_flag else 'binder_outside_orb',
        'narrative': (
            f"{binder} at {lon_b:.2f}° intercepts the {principal_a}→{principal_b} "
            f"arc within {distance_from_midpoint:.2f}° of the midpoint "
            f"({midpoint:.2f}°) — Yama Binder active."
            if is_binder_flag else
            f"{binder} at {lon_b:.2f}° sits on the {principal_a}→{principal_b} arc "
            f"but {distance_from_midpoint:.2f}° from the midpoint — outside the "
            f"{midpoint_orb}° interception orb."
        ),
    }


# =================================================================
# ABHARA YOGA — when malefics interfere with a positive L1↔L7 aspect
# Per Atul's audit: even if the aspect mathematically exists, a malefic
# sitting between or aspecting the link makes the cost too high, shifting
# the verdict from YES → CONDITIONAL or "YES with extreme friction."
# =================================================================

def detect_abhara_yoga(p_a: str, p_b: str, chart_data: Dict) -> Optional[Dict]:
    """
    Detect Abhara Yoga between p_a and p_b: when they ARE in direct Tajik
    aspect, but a malefic (Mars, Saturn, or Rahu) sits at a longitude
    BETWEEN their arc OR within orb of either lord — interfering with
    the otherwise valid connection.

    Returns dict if Abhara found, else None.
    """
    planets = chart_data.get('planets', {})
    if p_a not in planets or p_b not in planets:
        return None

    direct = pairwise_aspect(p_a, p_b, chart_data)
    if not direct.get('within_orb'):
        return None  # No direct aspect → Abhara doesn't apply (use Nakta instead)

    lon_a = planets[p_a].get('longitude')
    lon_b = planets[p_b].get('longitude')
    if lon_a is None or lon_b is None:
        return None

    # Sort for arc check
    if lon_a <= lon_b:
        lo_lon, hi_lon = lon_a, lon_b
    else:
        lo_lon, hi_lon = lon_b, lon_a
    short_arc_is_direct = (hi_lon - lo_lon) <= 180.0

    blockers: List[Dict] = []
    for mal in ['Mars', 'Saturn', 'Rahu']:
        if mal in (p_a, p_b):
            continue
        m_lon = planets.get(mal, {}).get('longitude')
        if m_lon is None:
            continue

        # Mode 1: malefic sits between the two lords
        if short_arc_is_direct:
            between = lo_lon <= m_lon <= hi_lon
        else:
            between = (m_lon >= hi_lon) or (m_lon <= lo_lon)

        # Mode 2: malefic is in orb-aspect of either lord
        asp_a = pairwise_aspect(mal, p_a, chart_data)
        asp_b = pairwise_aspect(mal, p_b, chart_data)
        aspects_either = (asp_a.get('within_orb') or asp_b.get('within_orb'))

        if between or aspects_either:
            mode = 'sits_between' if between else 'aspects_link'
            blockers.append({
                'malefic': mal,
                'mode': mode,
                'narrative': (
                    f"{mal} sits in the arc between {p_a} and {p_b}, "
                    "blocking the line of intent."
                    if mode == 'sits_between' else
                    f"{mal} aspects {p_a} and/or {p_b} from elsewhere — "
                    "the link is contested."
                ),
            })

    if not blockers:
        return None

    # Sort: sits_between blockers are harsher than aspects_link
    blockers.sort(key=lambda b: 0 if b['mode'] == 'sits_between' else 1)

    return {
        'planet_a': p_a,
        'planet_b': p_b,
        'blockers': blockers,
        'severity': 'high' if blockers[0]['mode'] == 'sits_between' else 'moderate',
        'narrative': (
            f"Abhara Yoga — the aspect between {p_a} and {p_b} is valid, "
            f"but {len(blockers)} malefic interference(s) make the result "
            "structurally costly. Verdict downgraded by one band."
        ),
    }


# =================================================================
# YAMA YOGA — the "Binder". When L1 and L7 are OUTSIDE direct aspect orb,
# a third planet sitting exactly at the midpoint of their arc creates a
# structural compulsion ("forceful marriage" trigger). Distinct from Nakta
# (which transfers light via aspects) and Abhara (which interferes with an
# existing aspect). Yama produces results through external/structural force
# rather than mutual aspiration.
# =================================================================

def detect_yama_yoga(p_a: str, p_b: str, chart_data: Dict,
                      midpoint_tolerance_deg: float = 5.0) -> Optional[Dict]:
    """
    Detect Yama Yoga: when p_a and p_b are NOT in direct aspect, but a third
    planet sits within `midpoint_tolerance_deg` of the exact arc midpoint
    between them — binding the result through external compulsion.

    Returns dict if Yama detected, else None.
    """
    planets = chart_data.get('planets', {})
    if p_a not in planets or p_b not in planets:
        return None

    direct = pairwise_aspect(p_a, p_b, chart_data)
    if direct.get('within_orb'):
        return None  # In aspect already — Yama only fires for non-aspecting pairs

    lon_a = planets[p_a].get('longitude')
    lon_b = planets[p_b].get('longitude')
    if lon_a is None or lon_b is None:
        return None

    # Determine the short arc and its midpoint
    diff = abs(lon_a - lon_b)
    if diff > 180.0:
        diff = 360.0 - diff
        # short arc wraps; midpoint is on the other side
        midpoint = ((lon_a + lon_b) / 2.0 + 180.0) % 360.0
    else:
        midpoint = (lon_a + lon_b) / 2.0

    # Check every other planet for proximity to the midpoint
    binders: List[Dict] = []
    for binder in VELOCITY_HIERARCHY:
        if binder in (p_a, p_b):
            continue
        b_lon = planets.get(binder, {}).get('longitude')
        if b_lon is None:
            continue
        offset = _angular_diff(b_lon, midpoint)
        if offset <= midpoint_tolerance_deg:
            # Identify the binder's nature
            is_malefic = binder in ('Mars', 'Saturn', 'Sun', 'Rahu', 'Ketu')
            binders.append({
                'binder': binder,
                'midpoint_offset_deg': round(offset, 2),
                'midpoint_lon': round(midpoint, 2),
                'is_malefic': is_malefic,
                'narrative': (
                    f"{binder} sits within {offset:.1f}° of the exact midpoint "
                    f"between {p_a} and {p_b} — "
                    + ("a malefic binder forces the matter through pressure or "
                       "external compulsion (e.g. family pressure, financial necessity, "
                       "obligation)."
                       if is_malefic else
                       "a benefic binder offers a structural bridge — circumstances "
                       "conspire to bring the parties together gently.")
                ),
            })

    if not binders:
        return None

    binders.sort(key=lambda b: b['midpoint_offset_deg'])
    return {
        'planet_a': p_a,
        'planet_b': p_b,
        'midpoint_lon': round(midpoint, 2),
        'binders': binders,
        'severity': 'high' if binders[0]['is_malefic'] else 'moderate',
        'narrative': (
            f"Yama Yoga — {p_a} and {p_b} have no direct aspect, but "
            f"{binders[0]['binder']} binds the arc at its midpoint "
            "(structural compulsion). Result occurs through external force "
            "rather than mutual aspiration."
        ),
    }


def is_kambool(target_planet: str, chart_data: Dict) -> Dict:
    """
    Kambool: Moon in Ithesal (applying within orb) with a target planet.
    Granted regardless of which planet is faster — but the canonical
    Tajik form requires Moon to be the faster (it always is, by hierarchy).

    Returns dict:
        active:   bool — whether Kambool fires
        aspect:   the underlying pairwise aspect data
        narrative: short description
    """
    if target_planet == 'Moon':
        return {
            'active': False,
            'narrative': 'Moon cannot Kambool with itself.',
        }
    pa = pairwise_aspect('Moon', target_planet, chart_data)
    if 'error' in pa:
        return {'active': False, 'narrative': pa['error']}
    active = pa.get('yoga') == 'Ithesal'
    return {
        'active': active,
        'aspect': pa,
        'narrative': (f"Kambool active — Moon is applying to {target_planet} "
                      f"within orb. Lunar blessing on the indication."
                      if active else
                      f"No Kambool — Moon is not in Ithesal with {target_planet}."),
    }


def detect_all_aspects(chart_data: Dict,
                       include_nakta: bool = True,
                       include_kambool: bool = True) -> Dict:
    """
    Enumerate every Tajik yoga in the chart in one pass.

    Returns:
        pairwise:  list of all pairwise aspect dicts (within_orb only)
        nakta:     list of all Nakta detections
        kambool:   list of all planets in Kambool with the Moon
    """
    classical = ['Sun', 'Moon', 'Mars', 'Mercury', 'Jupiter', 'Venus', 'Saturn']
    present = [p for p in classical if p in chart_data.get('planets', {})]

    pairwise = []
    for i, p1 in enumerate(present):
        for p2 in present[i + 1:]:
            asp = pairwise_aspect(p1, p2, chart_data)
            if 'error' not in asp and asp.get('within_orb'):
                pairwise.append(asp)

    nakta = []
    if include_nakta:
        for i, p1 in enumerate(present):
            for p2 in present[i + 1:]:
                n = detect_nakta(p1, p2, chart_data)
                if n:
                    nakta.append(n)

    kambool = []
    if include_kambool and 'Moon' in present:
        for p in present:
            if p == 'Moon':
                continue
            k = is_kambool(p, chart_data)
            if k.get('active'):
                kambool.append({
                    'planet': p,
                    'aspect': k['aspect'],
                    'narrative': k['narrative'],
                })

    return {
        'pairwise': pairwise,
        'nakta': nakta,
        'kambool': kambool,
        'total_aspects': len(pairwise),
        'total_nakta': len(nakta),
        'total_kambool': len(kambool),
    }


# =================================================================
# SECTION 1G: MULTI-QUERY ANCHOR RESOLVER
# =================================================================
# A single Prashna chart is valid for up to 5 questions in the same sitting.
# Subsequent questions use shifting Lagna pivots:
#   Q1 → Prashna Lagna (the chart's actual ascendant)
#   Q2 → Moon's Sign as Lagna
#   Q3 → Sun's Sign as Lagna
#   Q4 → Jupiter's Sign as Lagna
#   Q5 → Stronger of Mercury or Venus as Lagna
#
# "Stronger" for Q5 is resolved via Avastha priority (lower priority_index = stronger).
# Tie goes to Mercury (alphabetical fallback). This default is documented and
# can be swapped if Atul prefers a different strength metric (e.g. Bhava Bala).
# =================================================================

MAX_QUERIES_PER_CHART = 5

QUERY_PIVOT_SOURCES = {
    1: 'Prashna Lagna (chart ascendant)',
    2: "Moon's Sign as Lagna",
    3: "Sun's Sign as Lagna",
    4: "Jupiter's Sign as Lagna",
    5: 'Stronger of Mercury or Venus as Lagna',
}


def resolve_query_lagna(chart_data: Dict, question_index: int) -> Dict:
    """
    Resolve the effective Lagna sign for the Nth question in a multi-query session.

    Args:
        chart_data:      standard chart dict
        question_index:  1–5

    Returns dict:
        question_index:        1–5
        effective_lagna_sign:  0–11
        effective_lagna_name:  sign name
        source:                description of the pivot source
        rationale:             additional context (e.g. which planet was chosen for Q5)
    """
    if question_index < 1 or question_index > MAX_QUERIES_PER_CHART:
        return {
            'error': f'question_index must be 1..{MAX_QUERIES_PER_CHART}, got {question_index}'
        }

    planets = chart_data.get('planets', {})
    source = QUERY_PIVOT_SOURCES[question_index]
    rationale = ''

    if question_index == 1:
        sign_idx = chart_data.get('lagna_sign', 0)

    elif question_index == 2:
        sign_idx = planets.get('Moon', {}).get('sign_index')
        if sign_idx is None:
            return {'error': 'Moon sign_index missing from chart_data'}

    elif question_index == 3:
        sign_idx = planets.get('Sun', {}).get('sign_index')
        if sign_idx is None:
            return {'error': 'Sun sign_index missing from chart_data'}

    elif question_index == 4:
        sign_idx = planets.get('Jupiter', {}).get('sign_index')
        if sign_idx is None:
            return {'error': 'Jupiter sign_index missing from chart_data'}

    else:  # question_index == 5
        avasthas = compute_avasthas(chart_data)
        merc_state = avasthas.get('Mercury', {}).get('avastha', 'Neutral')
        venus_state = avasthas.get('Venus', {}).get('avastha', 'Neutral')
        merc_score = AVASTHA_AUSPICIOUSNESS.get(merc_state, 3)
        venus_score = AVASTHA_AUSPICIOUSNESS.get(venus_state, 3)
        if venus_score > merc_score:
            stronger = 'Venus'
        else:
            stronger = 'Mercury'  # tie → Mercury (alphabetical)
        sign_idx = planets.get(stronger, {}).get('sign_index')
        if sign_idx is None:
            return {'error': f'{stronger} sign_index missing from chart_data'}
        rationale = (
            f"{stronger} chosen by Avastha auspiciousness "
            f"(Mercury: {merc_state}={merc_score}, Venus: {venus_state}={venus_score}; "
            f"higher wins, ties → Mercury)."
        )

    return {
        'question_index': question_index,
        'effective_lagna_sign': sign_idx,
        'effective_lagna_name': SIGNS[sign_idx],
        'effective_lagna_sanskrit': SIGN_SANSKRIT[sign_idx],
        'source': source,
        'rationale': rationale,
    }


def rederive_houses_for_lagna(chart_data: Dict, new_lagna_sign: int) -> List[Dict]:
    """
    Re-derive whole-sign house occupants for a new Lagna sign without re-casting.
    Used after resolve_query_lagna to give each multi-query question its own
    house mapping while keeping the planetary positions identical.

    Returns a fresh 12-element houses list with each entry containing:
        house_num, sign, sign_sanskrit, sign_index, occupants
    """
    planets = chart_data.get('planets', {})
    houses = []
    for h in range(12):
        sign_idx = (new_lagna_sign + h) % 12
        occupants = []
        for p_name, p_data in planets.items():
            p_sign = p_data.get('sign_index')
            if p_sign is None and p_data.get('longitude') is not None:
                p_sign = int(p_data['longitude'] // 30) % 12
            if p_sign == sign_idx:
                occupants.append(p_name)
        houses.append({
            'house_num': h + 1,
            'sign': SIGNS[sign_idx],
            'sign_sanskrit': SIGN_SANSKRIT[sign_idx],
            'sign_index': sign_idx,
            'occupants': occupants,
        })
    return houses


def build_query_chart(base_chart: Dict, question_index: int) -> Dict:
    """
    Convenience wrapper: given a base Prashna chart and a question index,
    return a fresh chart_data dict with the effective Lagna and re-derived
    houses ready to feed into compute_bhava_bala / compute_sincerity_score /
    etc. Planetary positions are preserved unchanged.
    """
    anchor = resolve_query_lagna(base_chart, question_index)
    if 'error' in anchor:
        return {'error': anchor['error']}

    new_lagna_sign = anchor['effective_lagna_sign']
    new_houses = rederive_houses_for_lagna(base_chart, new_lagna_sign)

    out = {
        'lagna_sign': new_lagna_sign,
        'lagna_name': SIGNS[new_lagna_sign],
        'lagna_sanskrit': SIGN_SANSKRIT[new_lagna_sign],
        'planets': base_chart['planets'],
        'houses': new_houses,
        'query_anchor': anchor,
    }
    # Carry over any other base-chart metadata (jd, location, etc.)
    for k in ('jd_ut', 'lat', 'lon', 'datetime_local', 'timezone',
              'sun_altitude', 'shadow_ratio', 'cast_mode'):
        if k in base_chart:
            out[k] = base_chart[k]
    return out


# =================================================================
# END OF PHASE 1F + 1G
# =================================================================


# =================================================================
# SECTION 1H: KARYA SUCCESS CHAIN
# =================================================================
# 4-rule logic from Prashna corpus determining whether the querent's
# objective will materialise. Rules 1-3 are POSITIVE (success indicators),
# Rule 4 is NEGATIVE (failure/obstacle indicator).
#
#   Rule 1 — Lord Aspect:      L1 ↔ L{target} aspect each other.
#   Rule 2 — Mutual Exchange:  Both lords in mutual aspect AND Moon
#                              aspects at least one.
#   Rule 3 — Speed Factor:     L1 and L{target} in Ithesal (applying).
#   Rule 4 — Combustion/Aff.:  Either lord combust OR conjoined within
#                              orb of a natural malefic (Mars/Saturn).
# =================================================================


def karya_success_chain(chart_data: Dict, target_house_num: int) -> Dict:
    """
    Evaluate the 4-rule Karya logic between the Lagna Lord and the lord
    of `target_house_num` (e.g. 7 for marriage, 11 for gains, 5 for progeny).

    Returns:
        querent_lord:        name of Lagna Lord
        quesited_lord:       name of target-house lord
        rules:               list of 4 dicts, each {rule, satisfied, narrative}
        positive_satisfied:  0–3 (rules 1-3 fired)
        rule4_fired:         bool (the negative rule)
        verdict_primitive:   'failure' | 'conditional' | 'success' | 'confirmed'
        verdict_modifier:    'with_delays' | None
    """
    planets = chart_data.get('planets', {})
    lagna_sign_idx = chart_data.get('lagna_sign', 0)
    lagna_lord = SIGN_LORDS[lagna_sign_idx]
    target_sign_idx = (lagna_sign_idx + target_house_num - 1) % 12
    target_lord = SIGN_LORDS[target_sign_idx]

    # If Lagna Lord IS the target lord (e.g. Mercury rules both 3rd and 6th
    # for some Lagnas), Karya is self-referential — flag as failure.
    if lagna_lord == target_lord:
        return {
            'querent_lord': lagna_lord,
            'quesited_lord': target_lord,
            'rules': [
                {'rule': 'Self-reference', 'satisfied': False,
                 'narrative': f"Both Lagna and {target_house_num}th house are ruled "
                              f"by {lagna_lord}; Karya chain cannot evaluate a "
                              f"separate querent-quesited dynamic."}
            ],
            'positive_satisfied': 0,
            'rule4_fired': False,
            'verdict_primitive': 'conditional',
            'verdict_modifier': None,
        }

    asp = pairwise_aspect(lagna_lord, target_lord, chart_data)
    moon_aspect_a = pairwise_aspect('Moon', lagna_lord, chart_data)
    moon_aspect_b = pairwise_aspect('Moon', target_lord, chart_data)

    rules = []

    # --- Rule 1: Lord Aspect (L1 and L{target} in any Tajik aspect within orb) ---
    rule1_sat = asp.get('within_orb', False) and asp.get('yoga') != 'None'
    rules.append({
        'rule': 'Lord Aspect',
        'satisfied': rule1_sat,
        'narrative': (asp.get('narrative')
                      if rule1_sat else
                      f"{lagna_lord} and {target_lord} are outside Deeptamsha orb — "
                      f"no direct Tajik aspect.")
    })

    # --- Rule 2: Mutual Sign Exchange (Rashi Parivartana) + Drishti gate ---
    # Per Atul's Master Sootra: a true Rule-2 fire requires BOTH
    #   (a) Rashi Parivartana — L1 occupies L7's natal sign AND L7 occupies L1's
    #   (b) Drishti — they have a Tajik aspect (1/4/7/10 kendra, 3/5/9/11 trikona-sahaja).
    # A 2/12 or 6/8 placement is "Andha Parivartana" (Blind Exchange) — Rule 2
    # fires but the verdict primitive is held at CONDITIONAL, not SUCCESS.
    # Moon Conjunction (Moon in same sign as either lord) is an independent
    # weaker channel that still satisfies Rule 2.
    l1_sign = planets.get(lagna_lord, {}).get('sign_index')
    l7_sign = planets.get(target_lord, {}).get('sign_index')

    l1_signs_natural = _sign_lord_signs(lagna_lord)
    l7_signs_natural = _sign_lord_signs(target_lord)

    rashi_parivartana = (
        l1_sign is not None and l7_sign is not None and
        l1_sign in l7_signs_natural and l7_sign in l1_signs_natural
    )

    # Drishti / Andha classification
    andha_parivartana = False
    parivartana_narr = None
    if rashi_parivartana:
        house_distance = ((l7_sign - l1_sign) % 12) + 1  # 1-indexed
        FAVOURABLE_HOUSES = {1, 4, 7, 10, 3, 5, 9, 11}
        ANDHA_HOUSES = {2, 12, 6, 8}
        if house_distance in FAVOURABLE_HOUSES:
            parivartana_narr = (
                f"Rashi Parivartana — {lagna_lord} sits in {target_lord}'s sign "
                f"AND {target_lord} sits in {lagna_lord}'s sign, with a "
                f"favourable {house_distance}/{((1 - house_distance) % 12) + 1} "
                "house relationship. Strong mutual exchange."
            )
        elif house_distance in ANDHA_HOUSES:
            andha_parivartana = True
            parivartana_narr = (
                f"Andha Parivartana (Blind Exchange) — the exchange exists "
                f"({lagna_lord} ↔ {target_lord}) but the {house_distance}/12 "
                "relationship blocks the result. Verdict held at conditional."
            )

    # Independent Moon-conjunction channel
    # NB: when the Moon IS one of the lords (Cancer Lagna → Lagna Lord = Moon),
    # the Moon-with-itself check would trivially pass. Guard against that.
    moon_sign = planets.get('Moon', {}).get('sign_index')
    moon_with_l1 = (lagna_lord != 'Moon' and
                    moon_sign is not None and moon_sign == l1_sign)
    moon_with_l7 = (target_lord != 'Moon' and
                    moon_sign is not None and moon_sign == l7_sign)
    moon_conjunction = moon_with_l1 or moon_with_l7
    if moon_conjunction and not parivartana_narr:
        if moon_with_l1 and moon_with_l7:
            parivartana_narr = (
                f"Moon Conjunction — Moon sits in the same sign as both "
                f"{lagna_lord} and {target_lord}. Strong lunar witness."
            )
        elif moon_with_l1:
            parivartana_narr = (
                f"Moon Conjunction — Moon sits in the same sign as {lagna_lord} "
                "(querent lord). Moon validates the querent's intent."
            )
        else:
            parivartana_narr = (
                f"Moon Conjunction — Moon sits in the same sign as {target_lord} "
                "(quesited lord). Moon validates the matter's reality."
            )

    rule2_sat = rashi_parivartana or moon_conjunction
    rules.append({
        'rule': 'Mutual Exchange / Moon Conjunction',
        'satisfied': rule2_sat,
        'andha': andha_parivartana,
        'narrative': (
            parivartana_narr if parivartana_narr else
            f"No Rashi Parivartana between {lagna_lord} and {target_lord}, "
            "and Moon does not conjoin either lord. Rule 2 not satisfied."
        )
    })

    # --- Rule 3: Speed Factor — Ithesal applying ---
    rule3_sat = asp.get('yoga') == 'Ithesal'
    rules.append({
        'rule': 'Speed Factor (Ithesal)',
        'satisfied': rule3_sat,
        'narrative': (
            f"{asp.get('faster')} is applying to {asp.get('slower')} — "
            f"momentum is building toward the result."
            if rule3_sat else
            (f"The aspect is {asp.get('yoga')}, not Ithesal — "
             f"no active momentum." if asp.get('within_orb') else
             "No aspect within orb to evaluate momentum.")
        )
    })

    # --- Rule 4: Combustion / Affliction (NEGATIVE) ---
    q_combust = _is_combust(planets, lagna_lord)
    t_combust = _is_combust(planets, target_lord)
    # Check malefic conjunction within orb
    def _afflicted(planet_name):
        p_lon = planets.get(planet_name, {}).get('longitude')
        if p_lon is None:
            return None
        for mal in ['Mars', 'Saturn']:
            if mal == planet_name:
                continue
            m_lon = planets.get(mal, {}).get('longitude')
            if m_lon is None:
                continue
            if _angular_diff(p_lon, m_lon) <= max(
                    DEEPTAMSHA.get(planet_name, 8.0), DEEPTAMSHA.get(mal, 8.0)):
                return mal
        return None
    q_afflictor = _afflicted(lagna_lord)
    t_afflictor = _afflicted(target_lord)
    rule4_sat = bool(q_combust or t_combust or q_afflictor or t_afflictor)
    rule4_narr_parts = []
    if q_combust:
        rule4_narr_parts.append(f"{lagna_lord} (querent lord) is combust")
    if t_combust:
        rule4_narr_parts.append(f"{target_lord} (quesited lord) is combust")
    if q_afflictor:
        rule4_narr_parts.append(f"{lagna_lord} is conjoined with malefic {q_afflictor}")
    if t_afflictor:
        rule4_narr_parts.append(f"{target_lord} is conjoined with malefic {t_afflictor}")
    rules.append({
        'rule': 'Combustion / Affliction',
        'satisfied': rule4_sat,
        'narrative': ('; '.join(rule4_narr_parts) + '.' if rule4_sat else
                      "Both significators are clean of combustion and malefic conjunction.")
    })

    positive_count = sum(1 for r in rules[:3] if r['satisfied'])

    # Detect Andha Parivartana from Rule 2 detail (caveat downgrade)
    andha_parivartana = rules[1].get('andha', False) if len(rules) > 1 else False

    # Verdict primitive
    if rule4_sat and positive_count == 0:
        verdict_primitive = 'failure'
    elif positive_count == 0:
        verdict_primitive = 'failure'
    elif positive_count == 1:
        verdict_primitive = 'conditional'
    elif positive_count == 2:
        verdict_primitive = 'success'
    else:
        verdict_primitive = 'confirmed'

    # Andha Parivartana ceiling — per Atul's audit, a 2/12 or 6/8 mutual
    # exchange is structurally blind. Even with positive_count=2, the result
    # is held at CONDITIONAL pending external resolution.
    if andha_parivartana and verdict_primitive in ('success', 'confirmed'):
        verdict_primitive = 'conditional'

    verdict_modifier = 'with_delays' if (rule4_sat and positive_count >= 1) else None
    if andha_parivartana and not verdict_modifier:
        verdict_modifier = 'andha_parivartana'

    return {
        'querent_lord': lagna_lord,
        'quesited_lord': target_lord,
        'rules': rules,
        'positive_satisfied': positive_count,
        'rule4_fired': rule4_sat,
        'andha_parivartana': andha_parivartana,
        'verdict_primitive': verdict_primitive,
        'verdict_modifier': verdict_modifier,
        # Surface the L1↔L_target aspect dict computed at the top of this
        # function (line ~2684, `asp = pairwise_aspect(lagna_lord, target_lord)`).
        # This lets the orchestrator's core_catalyst selector pick this up as
        # the decisive Tajik connection when no other overlay carries it —
        # e.g. for Karma topics where nakta_abhara_scan is NOT in the overlay
        # list. Before this surface, Karma queries always reported
        # "Core catalyst: None" even when Overlay B confirmed an active
        # Ithesal between L1 and L_target.
        'l1_target_aspect': asp,
    }


# =================================================================
# SECTION 1I: STRENGTH SCALING / CERTAINTY SCORE
# =================================================================
# Per Prashna corpus's "Probability Weightage" table:
#   1/4 Strength: No aspect of benefics to the Lagna
#   1/2 Strength: Benefics aspect Lagna Lord only
#   3/4 Strength: Benefics aspect Lagna itself
#   Full Strength: Lagna + Lagna Lord + Moon all benefic-aspected, no malefic
# Independent dimension from the Karya verdict — gives the certainty %.
# =================================================================


def compute_strength_scaling(chart_data: Dict) -> Dict:
    """
    Compute the Tajik certainty score for the chart on the corpus's
    25 / 50 / 75 / 100 scale.

    Returns:
        score:    25 | 50 | 75 | 100
        band:     '1/4 Strength' | '1/2 Strength' | '3/4 Strength' | 'Full Strength'
        narrative: descriptive text
    """
    planets = chart_data.get('planets', {})
    lagna_sign_idx = chart_data.get('lagna_sign', 0)
    lagna_lord = SIGN_LORDS[lagna_sign_idx]
    lagna_cusp_lon = lagna_sign_idx * 30.0
    lagna_lord_lon = planets.get(lagna_lord, {}).get('longitude')
    moon_lon = planets.get('Moon', {}).get('longitude')

    def _benefic_touches(target_lon):
        if target_lon is None:
            return []
        out = []
        for b in BENEFICS:
            p_lon = planets.get(b, {}).get('longitude')
            if p_lon is None:
                continue
            if _within_aspect_orb(p_lon, target_lon, DEEPTAMSHA.get(b, 7.0)):
                out.append(b)
        return out

    def _malefic_touches(target_lon):
        if target_lon is None:
            return []
        out = []
        for m in ['Mars', 'Saturn']:
            p_lon = planets.get(m, {}).get('longitude')
            if p_lon is None:
                continue
            if _within_aspect_orb(p_lon, target_lon, DEEPTAMSHA.get(m, 8.0)):
                out.append(m)
        return out

    ben_to_lagna = _benefic_touches(lagna_cusp_lon)
    ben_to_lord = _benefic_touches(lagna_lord_lon) if lagna_lord != 'Moon' else _benefic_touches(lagna_lord_lon)
    ben_to_moon = [b for b in _benefic_touches(moon_lon) if b != 'Moon']
    mal_anywhere = (_malefic_touches(lagna_cusp_lon)
                    + _malefic_touches(lagna_lord_lon)
                    + _malefic_touches(moon_lon))

    if ben_to_lagna and ben_to_lord and ben_to_moon and not mal_anywhere:
        score = 100
        band = 'Full Strength'
        narrative = ("Lagna, Lagna Lord, and Moon are all touched by benefics with "
                     "zero malefic interference — the result is assured.")
    elif ben_to_lagna and ben_to_lord:
        score = 75
        band = '3/4 Strength'
        narrative = (f"Benefic(s) {', '.join(set(ben_to_lagna) & set(ben_to_lord)) or 'separately'} "
                     f"aspect both the Lagna and its Lord — the result will manifest.")
    elif ben_to_lord:
        score = 50
        band = '1/2 Strength'
        narrative = (f"Benefic(s) {', '.join(ben_to_lord)} aspect the Lagna Lord but not "
                     f"the Lagna itself — partial support.")
    elif ben_to_lagna:
        score = 25
        band = '1/4 Strength'
        narrative = (f"Benefic(s) {', '.join(ben_to_lagna)} touch the Lagna but not its Lord — "
                     f"minimal support.")
    else:
        score = 25
        band = '1/4 Strength'
        narrative = ("No benefic aspects to Lagna or Lagna Lord — the chart offers "
                     "weak structural support.")

    return {
        'score': score,
        'band': band,
        'narrative': narrative,
        'benefics_to_lagna': ben_to_lagna,
        'benefics_to_lord': ben_to_lord,
        'benefics_to_moon': ben_to_moon,
        'malefic_interference': mal_anywhere,
    }


# =================================================================
# SECTION 1J: HORARY-TO-NATAL SHIFT
# =================================================================


HOUSE_FLOURISH_LABEL = {
    1:  ('Vitality Zone',           'no physical ailments; the inquiry directly impacts personal health.'),
    2:  ('Wealth Zone',              'financial gains; the outcome activates personal liquidity.'),
    3:  ('Effort Zone',              'progress through one\'s own initiative; the result depends on action.'),
    4:  ('Flourishing Zone',         'long-term domestic peace and core security are activated.'),
    5:  ('Creativity Zone',          'creative or progeny-related rewards; the result enriches one\'s legacy.'),
    6:  ('Defeat-of-Enemies Zone',   'obstacles weaken; the outcome neutralises adversaries.'),
    7:  ('Partnership Zone',         'relationships are activated; the outcome reshapes alliances.'),
    8:  ('Friction Zone',            'caution required; the outcome may bring transformative loss.'),
    9:  ('Fortune Zone',             'higher fortune and dharma activate; the result expands one\'s arc.'),
    10: ('Karma Zone',               'public reputation and career trajectory are activated.'),
    11: ('Gains Zone',               'accumulation of wealth and fulfilment of desires.'),
    12: ('Expenditure Zone',         'outflow of resources; the result may cost more than it gains.'),
}


def horary_to_natal_shift(prashna_lagna_sign: int,
                          natal_lagna_sign: Optional[int]) -> Dict:
    """
    Compute the house-distance from the natal Lagna to the Prashna Lagna.
    The activated natal house indicates which life-area is energised by the query.

    Returns dict (or {error} if natal is missing):
        shift:                   1–12 (house distance, 1-indexed)
        activated_natal_house:   1–12
        zone_label:              short descriptor
        zone_narrative:          longer descriptor
    """
    if natal_lagna_sign is None:
        return {'error': 'natal_lagna_sign not provided'}

    shift = ((prashna_lagna_sign - natal_lagna_sign) % 12) + 1  # 1–12
    activated = shift  # same number, 1-indexed
    label, narrative = HOUSE_FLOURISH_LABEL.get(activated, ('Neutral Zone', 'no specific activation.'))
    return {
        'shift': shift,
        'activated_natal_house': activated,
        'zone_label': label,
        'zone_narrative': narrative,
    }


# =================================================================
# SECTION 1K: VIVAHA JUDGMENT MODULE
# =================================================================
# Marriage-specific judgment per corpus:
#   - Karya chain (general)
#   - Match type: effortless / effort-based / failure
#   - Third-party interference (malefic 8L/3L/4L in 7th)
#   - Emotional reciprocity (Ithesal quality between L1 and L7)
# =================================================================


def _planet_house(chart_data: Dict, planet_name: str) -> Optional[int]:
    """Return the 1-12 house position of a planet under the chart's Whole-Sign Lagna."""
    p_sign = chart_data.get('planets', {}).get(planet_name, {}).get('sign_index')
    if p_sign is None:
        return None
    lagna_sign = chart_data.get('lagna_sign', 0)
    return ((p_sign - lagna_sign) % 12) + 1


def vivaha_judgment(chart_data: Dict,
                    natal_lagna_sign: Optional[int] = None,
                    query_text: Optional[str] = None) -> Dict:
    """
    Full Vivaha (Marriage) judgment package. Bundles Karya chain output with
    marriage-specific match-type detection, third-party interference scan,
    emotional reciprocity reading, Abhara Yoga (malefic interference on the
    direct link), and long-horizon disclaimer detection.

    Args:
        chart_data:        Prashna chart dict (from build_query_chart or base_chart)
        natal_lagna_sign:  Optional 0-11 sign index of the user's natal Lagna
        query_text:        Optional original question text for long-horizon detection

    Returns the full Vivaha verdict package consumed by the AI narrative + UI.
    """
    planets = chart_data.get('planets', {})
    lagna_sign = chart_data.get('lagna_sign', 0)
    lagna_lord = SIGN_LORDS[lagna_sign]
    seventh_sign = (lagna_sign + 6) % 12
    seventh_lord = SIGN_LORDS[seventh_sign]

    # 1. Karya chain (target = 7th)
    karya = karya_success_chain(chart_data, 7)

    # 2. Strength scaling → certainty score
    strength = compute_strength_scaling(chart_data)

    # 3. Bhava Bala for the 7th
    bhava_7 = compute_bhava_bala(chart_data, 7)

    # 4. Avasthas for both significators (already includes degree_band)
    avasthas = compute_avasthas(chart_data)
    querent_avastha = avasthas.get(lagna_lord, {'avastha': 'Neutral', 'condition': '—'})
    quesited_avastha = avasthas.get(seventh_lord, {'avastha': 'Neutral', 'condition': '—'})

    # 5. Match type
    asp_l1_l7 = pairwise_aspect(lagna_lord, seventh_lord, chart_data)
    asp_l7_moon = pairwise_aspect(seventh_lord, 'Moon', chart_data)
    l1_in_7th = _planet_house(chart_data, lagna_lord) == 7
    moon_in_7th = _planet_house(chart_data, 'Moon') == 7

    if karya['rule4_fired'] and karya['positive_satisfied'] == 0:
        match_type = 'failure'
        match_narrative = ("Significators are afflicted or combust with no positive Karya "
                           "support — the proposal is unlikely to materialise.")
    elif asp_l1_l7.get('yoga') == 'Ithesal' or asp_l7_moon.get('yoga') == 'Ithesal':
        match_type = 'effortless'
        match_narrative = (f"{seventh_lord} (7th lord) is in Ithesal with "
                           f"{'Lagna Lord' if asp_l1_l7.get('yoga') == 'Ithesal' else 'the Moon'} — "
                           "the match materialises without strenuous effort.")
    elif l1_in_7th or moon_in_7th:
        match_type = 'effort_based'
        match_narrative = (f"{'Lagna Lord' if l1_in_7th else 'The Moon'} occupies the 7th house — "
                           "the match materialises only after a formal request or sustained effort.")
    else:
        match_type = 'conditional'
        match_narrative = ("No effortless or effort-based trigger fires; the result depends "
                           "on circumstantial factors (Nakta bridges, transits).")

    # 6. Third-party interference
    interference = []
    for house_num, label in [(8, 'Female rival / other partner'),
                              (3, 'Sibling interference'),
                              (4, 'Parental interference')]:
        h_sign = (lagna_sign + house_num - 1) % 12
        h_lord = SIGN_LORDS[h_sign]
        # Is h_lord a malefic AND placed in 7th?
        if h_lord in ['Sun', 'Mars', 'Saturn'] and _planet_house(chart_data, h_lord) == 7:
            interference.append({
                'type': label,
                'trigger': f"Malefic {house_num}th lord ({h_lord}) occupies the 7th house",
            })

    # 7. Emotional reciprocity
    if asp_l1_l7.get('within_orb'):
        if asp_l1_l7.get('yoga') == 'Ithesal':
            reciprocity = 'mutual_love'
            recip_narrative = ("Lagna Lord and 7th Lord are in Ithesal — mutual attraction "
                               "and active emotional engagement.")
        elif asp_l1_l7.get('yoga') == 'Esrapha':
            reciprocity = 'past_engagement'
            recip_narrative = ("Lagna Lord and 7th Lord are in Esrapha — the emotional "
                               "energy is in the past; the connection is fading.")
        elif planets.get(lagna_lord, {}).get('sign_index') == planets.get(seventh_lord, {}).get('sign_index'):
            reciprocity = 'discord_short'
            recip_narrative = ("Both lords occupy the same sign — short-lived friction, "
                               "quickly resolved.")
        else:
            reciprocity = 'neutral'
            recip_narrative = "Active aspect but neither applying nor separating — neutral engagement."
    else:
        reciprocity = 'disengaged'
        recip_narrative = ("Lagna Lord and 7th Lord do not aspect each other within orb — "
                           "emotional disengagement or blind spot between partners.")

    # 8a. Nakta bridge (if no direct aspect, is there a bridge planet?)
    nakta = detect_nakta(lagna_lord, seventh_lord, chart_data)

    # 8b. Abhara Yoga (if there IS a direct aspect, are malefics interfering?)
    abhara = detect_abhara_yoga(lagna_lord, seventh_lord, chart_data)

    # 8c. Yama Yoga (if no direct aspect, is a planet at the midpoint binding them?)
    # Per Atul's audit — even without aspect or relay, a midpoint planet can
    # force the matter through structural compulsion (family pressure etc.)
    yama = detect_yama_yoga(lagna_lord, seventh_lord, chart_data)

    # 9. Verdict synthesis
    primitive = karya['verdict_primitive']
    modifier = karya['verdict_modifier']

    if primitive == 'failure' and not nakta:
        verdict = 'NO'
        verdict_text = 'No — the proposal will not materialise'
    elif primitive == 'failure' and nakta:
        verdict = 'CONDITIONAL'
        verdict_text = f'Conditional — only via {nakta["bridge"]} as intermediary'
    elif primitive == 'conditional':
        verdict = 'CONDITIONAL'
        if modifier == 'andha_parivartana':
            verdict_text = 'Conditional — Andha Parivartana (blind exchange) blocks the resolution'
        else:
            verdict_text = 'Conditional — depends on circumstantial support'
    elif primitive == 'success' and modifier == 'with_delays':
        verdict = 'YES_WITH_DELAYS'
        verdict_text = 'Yes — with initial delays or obstacles'
    elif primitive == 'success':
        verdict = 'YES'
        verdict_text = 'Yes — the proposal will materialise'
    elif primitive == 'confirmed' and modifier == 'with_delays':
        verdict = 'YES_WITH_DELAYS'
        verdict_text = 'Yes — confirmed, with initial delays'
    else:  # confirmed
        verdict = 'YES'
        verdict_text = 'Yes — strongly confirmed'

    # Abhara downgrade — even a positive verdict gets one band of friction added
    if abhara and verdict in ('YES', 'YES_WITH_DELAYS'):
        if verdict == 'YES':
            verdict = 'YES_WITH_DELAYS'
            verdict_text = 'Yes — but with malefic friction (Abhara Yoga)'
        else:
            # Already with delays; preserve but extend the text
            verdict_text = 'Yes — with delays AND malefic friction (Abhara Yoga)'

    # Core catalyst — the most decisive single yoga/factor
    if karya['positive_satisfied'] >= 2:
        core_catalyst = {
            'yoga': asp_l1_l7.get('yoga', 'Aspect'),
            'between': [f"Lagna Lord ({lagna_lord})", f"7th Lord ({seventh_lord})"],
            'narrative': asp_l1_l7.get('narrative', match_narrative),
        }
    elif nakta:
        core_catalyst = {
            'yoga': 'Nakta',
            'between': [f"Lagna Lord ({lagna_lord})", f"7th Lord ({seventh_lord})"],
            'narrative': nakta.get('narrative', ''),
            'bridge': nakta.get('bridge'),
            'bridge_role': nakta.get('bridge_role'),
            'bridge_role_narrative': nakta.get('bridge_role_narrative'),
        }
    else:
        core_catalyst = {
            'yoga': 'None',
            'between': [f"Lagna Lord ({lagna_lord})", f"7th Lord ({seventh_lord})"],
            'narrative': 'No decisive Tajik connection between the two significators.',
        }

    # Horary-to-natal
    h2n = horary_to_natal_shift(lagna_sign, natal_lagna_sign)

    # Long-horizon disclaimer (Atul's mandatory safety rail)
    long_horizon = detect_long_horizon_query(query_text)

    return {
        'sub_module': 'vivaha',
        'verdict': verdict,
        'verdict_text': verdict_text,
        'certainty_score': strength['score'],
        'certainty_band': strength['band'],
        'certainty_narrative': strength['narrative'],
        'core_catalyst': core_catalyst,
        'querent_lord': {
            'name': lagna_lord,
            'avastha': querent_avastha.get('avastha'),
            'condition': querent_avastha.get('condition'),
            'outcome': querent_avastha.get('outcome'),
            'degree_band': querent_avastha.get('degree_band'),
            'synthesis_label': querent_avastha.get('synthesis_label'),
            'synthesis_narrative': querent_avastha.get('synthesis_narrative'),
            'is_combust': _is_combust(planets, lagna_lord),
            'sign': planets.get(lagna_lord, {}).get('sign'),
            'house': _planet_house(chart_data, lagna_lord),
        },
        'quesited_lord': {
            'name': seventh_lord,
            'avastha': quesited_avastha.get('avastha'),
            'condition': quesited_avastha.get('condition'),
            'outcome': quesited_avastha.get('outcome'),
            'degree_band': quesited_avastha.get('degree_band'),
            'synthesis_label': quesited_avastha.get('synthesis_label'),
            'synthesis_narrative': quesited_avastha.get('synthesis_narrative'),
            'is_combust': _is_combust(planets, seventh_lord),
            'sign': planets.get(seventh_lord, {}).get('sign'),
            'house': _planet_house(chart_data, seventh_lord),
        },
        'aspect_l1_l7': asp_l1_l7,
        'nakta_bridge': nakta,
        'abhara_yoga': abhara,
        'yama_yoga': yama,
        'match_type': match_type,
        'match_narrative': match_narrative,
        'third_party_interference': interference,
        'emotional_reciprocity': reciprocity,
        'reciprocity_narrative': recip_narrative,
        'karya_chain': karya,
        'strength_scaling': strength,
        'bhava_bala_7th': bhava_7,
        'horary_to_natal': h2n,
        'long_horizon': long_horizon,
    }


# =================================================================
# END OF PHASE 1H + 1I + 1J + 1K (Vivaha)
# =================================================================


# =================================================================
# PHASE 3A — GARBHA (CONCEPTION) ENGINE MATH
# Locked corpus: /mnt/user-data/outputs/garbha_corpus_locked.md
# Reference priority: Prashna Marga > Tajik Neelkanthi > Phaladeepika
# =================================================================


# Alpa-Putra (sterile / low-fertility) signs per Atul's locked corpus.
# Used by Rule A (Sphuta-cap at 50%) and Rule C (5th-cusp YES → YES_WITH_DELAYS).
# Indices: Gemini=2, Leo=4, Virgo=5, Scorpio=7
STERILE_SIGNS = {2, 4, 5, 7}

# Mars-in-5th severity split per Atul's locked rulership-based decision:
#   Leo (Sun-ruled Sthira) concentrates dry heat → high risk
#   Sagittarius (Jupiter-ruled Dwiswabhava) → tempered, safe group
# RISK indices: Aries=0, Cancer=3, Leo=4, Libra=6, Capricorn=9
MARS_5TH_RISK_SIGNS = {0, 3, 4, 6, 9}

# Garbha intent classifier keyword bank.
# Order of evaluation matters — more specific intents are checked first.
GARBHA_INTENT_KEYWORDS = {
    'current_pregnancy_confirmation': [
        'am i pregnant', 'is she pregnant', 'is my wife pregnant',
        'did it work', 'did i conceive', 'has she conceived',
        'is the pregnancy real', 'am i carrying',
    ],
    'gestation_safety': [
        'go to term', 'will i miscarry', 'will the pregnancy', 'is the pregnancy safe',
        'will it last', 'will the baby survive', 'gestation safe', 'trimester',
        'high risk pregnancy', 'pregnancy go to term',
    ],
    'conception_timing': [
        'when will i conceive', 'when will we conceive', 'fertility window',
        'best time to try', 'when should we try', 'when can i get pregnant',
        'optimal time to try', 'when is the best time',
    ],
    'outcome_quality': [
        'healthy child', 'health of the child', "child's future", "baby's future",
        "kids' future", 'will the child be',
    ],
}

# Husband-pivot phrase bank — when male querent asks about partner's conception
HUSBAND_PIVOT_PHRASES = [
    'my wife', 'my partner', 'my spouse', 'my girlfriend', 'my fiancee',
    'is she', 'will she', 'when will she', 'her conception',
    'her pregnancy', 'her womb', 'she conceive',
]

# Self-pregnancy phrases — block the pivot even for male profile
SELF_PREGNANCY_PHRASES = [
    'am i pregnant', 'am i carrying', 'will i conceive', 'i conceive',
    'when will i give birth', 'i am pregnant', 'my pregnancy',
    'i give birth', 'i am carrying',
]

# 9th house exception keywords (lineage queries)
LINEAGE_KEYWORDS = ['lineage', 'heir', 'vansha', 'dynasty', 'family line', 'bloodline']

# Garbha-specific long-horizon keywords appended at lookup time
GARBHA_LONG_HORIZON_EXTRAS = [
    'ever have children', 'ever conceive', 'all my children',
    'how many children', "children's future", "kids' future",
    'multiple pregnancies', 'future kids', 'future babies',
]


# -----------------------------------------------------------------
# GROUP 1 — FERTILITY COORDINATES (Beeja & Kshetra Sphuta)
# -----------------------------------------------------------------

def compute_beeja_sphuta(planets: Dict) -> Dict:
    """
    Beeja Sphuta — male fertility coordinate (Parashari integration).
    Formula: (Sun_lon + Venus_lon + Jupiter_lon) mod 360°
    Returns dict with longitude, sign_index, sign_name, deg_in_sign.
    """
    sun_lon = planets.get('Sun', {}).get('longitude')
    venus_lon = planets.get('Venus', {}).get('longitude')
    jup_lon = planets.get('Jupiter', {}).get('longitude')
    if None in (sun_lon, venus_lon, jup_lon):
        return {'error': 'Missing required planet longitude for Beeja Sphuta'}
    sphuta = (sun_lon + venus_lon + jup_lon) % 360.0
    sign_idx = int(sphuta // 30)
    return {
        'longitude': round(sphuta, 4),
        'sign_index': sign_idx,
        'sign_name': SIGNS[sign_idx],
        'sign_sanskrit': SIGN_SANSKRIT[sign_idx],
        'deg_in_sign': round(sphuta - sign_idx * 30, 4),
        'sphuta_type': 'beeja',
        'gender_applicability': 'male',
    }


def compute_kshetra_sphuta(planets: Dict) -> Dict:
    """
    Kshetra Sphuta — female fertility coordinate.
    Formula: (Jupiter_lon + Moon_lon + Mars_lon) mod 360°
    """
    jup_lon = planets.get('Jupiter', {}).get('longitude')
    moon_lon = planets.get('Moon', {}).get('longitude')
    mars_lon = planets.get('Mars', {}).get('longitude')
    if None in (jup_lon, moon_lon, mars_lon):
        return {'error': 'Missing required planet longitude for Kshetra Sphuta'}
    sphuta = (jup_lon + moon_lon + mars_lon) % 360.0
    sign_idx = int(sphuta // 30)
    return {
        'longitude': round(sphuta, 4),
        'sign_index': sign_idx,
        'sign_name': SIGNS[sign_idx],
        'sign_sanskrit': SIGN_SANSKRIT[sign_idx],
        'deg_in_sign': round(sphuta - sign_idx * 30, 4),
        'sphuta_type': 'kshetra',
        'gender_applicability': 'female',
    }


def is_alpa_putra_sign(sign_index: int) -> bool:
    """True if sign is in the sterile Alpa-Putra list (Gem/Leo/Vir/Sco)."""
    return sign_index in STERILE_SIGNS


def is_mars_5th_high_risk(mars_sign_index: int) -> bool:
    """True if Mars sign places it in the 5th-house high-risk group."""
    return mars_sign_index in MARS_5TH_RISK_SIGNS


# -----------------------------------------------------------------
# GROUP 2 — TAJIK VIMSHOPAKA SURROGATE (0-20 strength scale)
# Per Atul's spec: skip full Shaddvarga Vimshopaka in favour of a
# Tajik-aligned approximation (Avastha base + degree-band modifier).
# -----------------------------------------------------------------

# Avastha → base score on 0–20 scale (Atul's three-tier mapping)
TAJIK_VIMSHOPAKA_AVASTHA_BASE = {
    # Tier 1: Exalted / Own (14-16)
    'Deepta':     16,
    'Swastha':    15,
    'Suveerya':   15,
    'Adhiveerya': 14,
    # Tier 2: Friend / Neutral (10-13)
    'Mudita':     12,
    'Neutral':    10,
    # Tier 3: Inimical / Debilitated (2-6)
    'Supta':       6,
    'Peedita':     4,
    'Pariheena':   4,
    'Deena':       3,
    'Mushita':     2,
}

TAJIK_VIMSHOPAKA_BAND_MOD = {
    'pragalbha':    4,   # Peak utility
    'sandhi':      -6,   # Edge of abyss
    'sadyo_gata':   0,
    'udaya':        0,
    'culminating':  0,
}


def compute_tajik_vimshopaka_surrogate(planet_name: str,
                                       chart_data: Dict) -> Dict:
    """
    Tajik-aligned Vimshopaka surrogate on 0-20 scale.
    Per Atul's spec: Avastha-tier base + degree-band modifier.
    Used as the gating threshold for Kamboola Yoga (≥12 = active).
    """
    avasthas = compute_avasthas(chart_data)
    planet_av = avasthas.get(planet_name, {})
    avastha = planet_av.get('avastha', 'Neutral')
    deg_band = planet_av.get('degree_band') or {}
    band_key = deg_band.get('band_key', 'udaya')

    base = TAJIK_VIMSHOPAKA_AVASTHA_BASE.get(avastha, 10)
    modifier = TAJIK_VIMSHOPAKA_BAND_MOD.get(band_key, 0)
    score = max(0, min(20, base + modifier))

    return {
        'planet': planet_name,
        'score': score,
        'avastha': avastha,
        'avastha_base': base,
        'band_key': band_key,
        'band_modifier': modifier,
        'narrative': (
            f"{planet_name} Tajik Vimshopaka (surrogate): {score}/20 — "
            f"{avastha} base ({base}) {modifier:+d} from {band_key} band."
        ),
    }


# -----------------------------------------------------------------
# GROUP 3 — NEW YOGAS (Kamboola + Gada)
# -----------------------------------------------------------------

def detect_kamboola_yoga(lagna_lord: str, target_lord: str,
                         chart_data: Dict,
                         vimshopaka_threshold: float = 12.0) -> Optional[Dict]:
    """
    Kamboola Yoga — Moon as cosmic proxy.
    Fires when:
      1. L1 ↔ L_target do NOT aspect each other within orb
      2. Moon aspects BOTH L1 and L_target within orb
      3. Moon's Tajik Vimshopaka surrogate ≥ threshold (12)

    Effect: substitute primitive NO with YES_WITH_DELAYS.
    Excludes the case where Moon IS one of the lords (tautology).
    """
    if lagna_lord == 'Moon' or target_lord == 'Moon':
        return None

    # Step 1: confirm L1 ↔ L_target lack direct aspect
    asp_lords = pairwise_aspect(lagna_lord, target_lord, chart_data)
    if asp_lords.get('within_orb'):
        return None

    # Step 2: Moon must aspect both within orb
    asp_moon_l1 = pairwise_aspect('Moon', lagna_lord, chart_data)
    asp_moon_lt = pairwise_aspect('Moon', target_lord, chart_data)
    if not (asp_moon_l1.get('within_orb') and asp_moon_lt.get('within_orb')):
        return None

    # Step 3: Moon's Vimshopaka strength
    vim = compute_tajik_vimshopaka_surrogate('Moon', chart_data)
    if vim['score'] < vimshopaka_threshold:
        return None

    return {
        'lagna_lord': lagna_lord,
        'target_lord': target_lord,
        'moon_vimshopaka_score': vim['score'],
        'moon_vimshopaka_narrative': vim['narrative'],
        'aspect_moon_to_l1': asp_moon_l1.get('yoga'),
        'aspect_moon_to_target': asp_moon_lt.get('yoga'),
        'narrative': (
            f"Kamboola Yoga — Moon (Vimshopaka {vim['score']}/20) aspects both "
            f"{lagna_lord} and {target_lord} when they themselves lack direct "
            "aspect. The Moon carries the fertility energy as a cosmic proxy; "
            "the Karya succeeds but with extended timing."
        ),
        'effect': 'substitute_failure_with_yes_with_delays',
    }


def detect_gada_yoga(chart_data: Dict) -> Optional[Dict]:
    """
    Gada Yoga — all 7 classical planets cluster into TWO CONSECUTIVE Kendras only.
    Consecutive Kendra pairs: (1,4), (4,7), (7,10), (10,1).
    Distinct from Kamala Yoga (all four Kendras populated).

    Effect: force resolution within 12 months.
    """
    KENDRA_PAIRS = [(1, 4), (4, 7), (7, 10), (10, 1)]
    CLASSICAL_7 = ['Sun', 'Moon', 'Mars', 'Mercury', 'Jupiter', 'Venus', 'Saturn']

    planet_houses = {}
    for p in CLASSICAL_7:
        h = _planet_house(chart_data, p)
        if h is None:
            return None
        planet_houses[p] = h

    occupied = set(planet_houses.values())

    for h1, h2 in KENDRA_PAIRS:
        if occupied == {h1, h2}:
            return {
                'kendras_occupied': [h1, h2],
                'planet_distribution': planet_houses,
                'narrative': (
                    f"Gada Yoga — all 7 classical planets cluster in houses "
                    f"{h1} and {h2} (consecutive Kendras). Structural compression "
                    "forces the Karya outcome within a 12-month horizon, often "
                    "through external or unconventional means."
                ),
                'effect': 'force_resolution_within_12_months',
            }

    return None


# -----------------------------------------------------------------
# GROUP 4 — ECLIPSE PROXIMITY DETECTION
# Per Atul's locked spec: ±15 day window AND eclipse longitude within
# ±5° orb of Lagna/Descendant, Putra/Labha, or L5's longitude.
# -----------------------------------------------------------------

def detect_eclipse_proximity(jd_ut: float,
                              chart_data: Dict,
                              window_days: float = 15.0,
                              axis_orb_deg: float = 5.0,
                              target_house: int = 5) -> Optional[Dict]:
    """
    Eclipse proximity detector. Fires when BOTH:
      1. A solar OR lunar eclipse occurs within ±window_days of jd_ut, AND
      2. That eclipse's sidereal longitude is within axis_orb_deg of:
           - Lagna or 7th cusp, OR
           - target_house cusp or its opposite (e.g. 5/11 for Garbha), OR
           - The L_target's natal-position longitude.

    Returns None if no eclipse meets both conditions.
    Effect: caller should hard-cap sincerity at 45 and emit safety warning.
    """
    try:
        import swisseph as swe
    except ImportError:
        return None

    lagna_sign = chart_data.get('lagna_sign', 0)
    target_sign = (lagna_sign + target_house - 1) % 12
    opposite_house = ((target_house - 1 + 6) % 12) + 1
    opposite_sign = (lagna_sign + opposite_house - 1) % 12

    target_lord = SIGN_LORDS[target_sign]
    target_lord_lon = chart_data.get('planets', {}).get(target_lord, {}).get('longitude')

    # Build the axis longitudes to check
    axes = [
        ('Lagna (1st cusp)', lagna_sign * 30.0),
        ('Descendant (7th cusp)', ((lagna_sign + 6) % 12) * 30.0),
        (f'Putra ({target_house}th cusp)', target_sign * 30.0),
        (f'Labha ({opposite_house}th cusp)', opposite_sign * 30.0),
    ]
    if target_lord_lon is not None:
        axes.append((f'{target_lord} ({target_house}th lord)', target_lord_lon))

    # Collect candidate eclipses within window
    eclipses = []

    # Solar eclipses — search forward from (jd - window)
    try:
        res = swe.sol_eclipse_when_glob(jd_ut - window_days - 1.0,
                                         swe.FLG_SWIEPH, 0)
        ecl_jd = res[1][0]
        if abs(ecl_jd - jd_ut) <= window_days:
            sun_pos, _ = swe.calc_ut(ecl_jd, swe.SUN)
            ayan = swe.get_ayanamsa_ut(ecl_jd)
            sidereal_lon = (sun_pos[0] - ayan) % 360.0
            eclipses.append({
                'type': 'solar', 'jd': ecl_jd,
                'days_offset': round(ecl_jd - jd_ut, 1),
                'longitude': round(sidereal_lon, 2),
            })
    except Exception:
        pass

    # Solar eclipses — search forward from (jd + 1)
    try:
        res = swe.sol_eclipse_when_glob(jd_ut + 1.0, swe.FLG_SWIEPH, 0)
        ecl_jd = res[1][0]
        if abs(ecl_jd - jd_ut) <= window_days:
            sun_pos, _ = swe.calc_ut(ecl_jd, swe.SUN)
            ayan = swe.get_ayanamsa_ut(ecl_jd)
            sidereal_lon = (sun_pos[0] - ayan) % 360.0
            eclipses.append({
                'type': 'solar', 'jd': ecl_jd,
                'days_offset': round(ecl_jd - jd_ut, 1),
                'longitude': round(sidereal_lon, 2),
            })
    except Exception:
        pass

    # Lunar eclipses — same two-direction search
    for offset in [-window_days - 1.0, 1.0]:
        try:
            res = swe.lun_eclipse_when(jd_ut + offset, swe.FLG_SWIEPH, 0)
            ecl_jd = res[1][0]
            if abs(ecl_jd - jd_ut) <= window_days:
                moon_pos, _ = swe.calc_ut(ecl_jd, swe.MOON)
                ayan = swe.get_ayanamsa_ut(ecl_jd)
                sidereal_lon = (moon_pos[0] - ayan) % 360.0
                eclipses.append({
                    'type': 'lunar', 'jd': ecl_jd,
                    'days_offset': round(ecl_jd - jd_ut, 1),
                    'longitude': round(sidereal_lon, 2),
                })
        except Exception:
            pass

    if not eclipses:
        return None

    # Deduplicate by JD
    seen_jd = set()
    unique = []
    for e in eclipses:
        key = round(e['jd'], 2)
        if key in seen_jd:
            continue
        seen_jd.add(key)
        unique.append(e)

    # Check axis intersection
    for ecl in unique:
        for axis_name, axis_lon in axes:
            diff = min(abs(ecl['longitude'] - axis_lon),
                       360 - abs(ecl['longitude'] - axis_lon))
            if diff <= axis_orb_deg:
                return {
                    'eclipse_type': ecl['type'],
                    'eclipse_jd': ecl['jd'],
                    'days_from_cast': ecl['days_offset'],
                    'eclipse_longitude': ecl['longitude'],
                    'axis_hit': axis_name,
                    'axis_longitude': round(axis_lon, 2),
                    'orb_offset_deg': round(diff, 2),
                    'narrative': (
                        f"{ecl['type'].capitalize()} eclipse at "
                        f"{ecl['longitude']:.1f}° (cast offset {ecl['days_offset']:+.1f} days) "
                        f"shadows the {axis_name} at {axis_lon:.1f}° "
                        f"(orb gap {diff:.1f}°). Progeny axis is under eclipse shadow — "
                        "sincerity capped, medical monitoring advised."
                    ),
                    'effect': 'cap_sincerity_at_45_emit_safety_warning',
                }

    return None  # Eclipse present but not on relevant axis


# -----------------------------------------------------------------
# GROUP 5 — INTENT CLASSIFIER + HUSBAND-PIVOT DETECTOR
# -----------------------------------------------------------------

def classify_garbha_intent(full_query: Optional[str]) -> str:
    """
    Classify a Garbha query into one of 5 intent codes.
    Default: 'conception_possibility'.
    """
    if not full_query:
        return 'conception_possibility'
    q = full_query.lower()
    # Order matters — more specific intents first
    for intent in ['current_pregnancy_confirmation',
                   'gestation_safety',
                   'conception_timing',
                   'outcome_quality']:
        for kw in GARBHA_INTENT_KEYWORDS[intent]:
            if kw in q:
                return intent
    return 'conception_possibility'


def detect_husband_pivot(full_query: Optional[str],
                          querent_gender: Optional[str]) -> bool:
    """
    Determine whether to pivot target house from 5th → 11th (5th from 7th)
    per Atul's locked rule logic.

    Pivot fires when:
      - Explicit husband phrase present in query ("my wife", "is she...", etc.), OR
      - querent_gender == 'male' AND no explicit self-pregnancy phrase

    Pivot blocked when:
      - Explicit self-pregnancy phrase present ("am I pregnant", "I conceive", etc.)
    """
    q = (full_query or '').lower()

    # Self-pregnancy phrases override pivot regardless of gender
    if any(p in q for p in SELF_PREGNANCY_PHRASES):
        return False

    # Explicit husband phrases trigger pivot regardless of gender field
    if any(p in q for p in HUSBAND_PIVOT_PHRASES):
        return True

    # Ambiguous query — fall back to gender field
    return querent_gender == 'male'


def detect_lineage_query(full_query: Optional[str]) -> bool:
    """True if query mentions lineage/heir/vansha — triggers 9th-house exception."""
    if not full_query:
        return False
    q = full_query.lower()
    return any(kw in q for kw in LINEAGE_KEYWORDS)


# -----------------------------------------------------------------
# GROUP 6 — UTILITIES (combustion depth, void-of-course Moon)
# -----------------------------------------------------------------

def is_heavily_combust(planets: Dict, planet_name: str,
                       heavy_threshold_deg: float = 4.0) -> bool:
    """
    True if planet is within heavy_threshold_deg of the Sun
    (vs standard combustion which uses ~8° per planet).
    Used to trigger INCONCLUSIVE_RECAST_REQUIRED for current-pregnancy queries.
    """
    if planet_name == 'Sun':
        return False
    p_lon = planets.get(planet_name, {}).get('longitude')
    sun_lon = planets.get('Sun', {}).get('longitude')
    if p_lon is None or sun_lon is None:
        return False
    return _angular_diff(p_lon, sun_lon) <= heavy_threshold_deg


def is_moon_void_of_course(chart_data: Dict) -> bool:
    """
    Void-of-course Moon: the Moon makes no further Tajik aspect (Ithesal type)
    before exiting its current sign. Simplified surrogate: if Moon's longitude
    is in the last 3° of its sign AND no faster planet is in orb...
    Since Moon is the fastest planet, we approximate by checking whether the
    Moon's degree-within-sign exceeds 27° AND no planet is within 3° aspect-arc
    of the Moon's projected ingress longitude.

    This is a conservative approximation — true VoC requires nakshatra-level
    transit projection.
    """
    moon_lon = chart_data.get('planets', {}).get('Moon', {}).get('longitude')
    if moon_lon is None:
        return False
    deg_in_sign = moon_lon % 30.0
    if deg_in_sign < 27.0:
        return False  # Plenty of room for further aspects in current sign

    # Moon is near sign-end. Check if any other planet is within 3° of Moon's
    # remaining arc — if so, an aspect is possible before sign change.
    remaining_arc_end = moon_lon + (30.0 - deg_in_sign)
    for p_name in ['Sun', 'Mercury', 'Venus', 'Mars', 'Jupiter', 'Saturn']:
        p_lon = chart_data.get('planets', {}).get(p_name, {}).get('longitude')
        if p_lon is None:
            continue
        if _angular_diff(p_lon, moon_lon) <= 3.0:
            return False
        # Check if planet is within 3° of remaining arc
        if _angular_diff(p_lon, remaining_arc_end) <= 3.0:
            return False

    return True  # No nearby planet → Moon is void-of-course


# -----------------------------------------------------------------
# GROUP 7 — GARBHA JUDGMENT ORCHESTRATOR
# -----------------------------------------------------------------

def garbha_judgment(chart_data: Dict,
                    natal_lagna_sign: Optional[int] = None,
                    query_text: Optional[str] = None,
                    full_query: Optional[str] = None,
                    intent: Optional[str] = None,
                    querent_gender: Optional[str] = None) -> Dict:
    """
    Full Garbha (Conception) judgment package. Returns the structured dict
    consumed by /prashna_garbha endpoint + AI narrative + UI.

    Args:
        chart_data:          Prashna chart dict
        natal_lagna_sign:    0-11 sign index of querent's natal Lagna (optional)
        query_text:          The first-word phonetic source (or None)
        full_query:          Full original question text (for intent + long-horizon)
        intent:              Pre-classified intent, or None to auto-classify
        querent_gender:      'male' | 'female' | None
    """
    planets = chart_data.get('planets', {})
    lagna_sign = chart_data.get('lagna_sign', 0)
    lagna_lord = SIGN_LORDS[lagna_sign]

    # ===== 1. Intent classification =====
    if intent is None:
        intent = classify_garbha_intent(full_query)

    # ===== 2. Target-house resolution =====
    is_lineage = detect_lineage_query(full_query)
    is_husband_pivot = detect_husband_pivot(full_query, querent_gender)
    if is_lineage:
        target_house = 9
        target_role = '9th — lineage / heir axis'
    elif is_husband_pivot:
        target_house = 11
        target_role = "11th (5th from 7th) — wife's progeny zone"
    else:
        target_house = 5
        target_role = '5th — Putra Bhava'

    target_sign = (lagna_sign + target_house - 1) % 12
    target_lord = SIGN_LORDS[target_sign]

    # ===== 3. Karya chain on the resolved target =====
    karya = karya_success_chain(chart_data, target_house)

    # ===== 4. Strength scaling (certainty score) =====
    strength = compute_strength_scaling(chart_data)

    # ===== 5. Bhava Bala on the target house =====
    bhava = compute_bhava_bala(chart_data, target_house)
    bhava_net = bhava.get('net_strength_pct', 0)

    # ===== 6. Avasthas (with synthesis_label carried from Vivaha) =====
    avasthas = compute_avasthas(chart_data)
    querent_av = avasthas.get(lagna_lord, {})
    quesited_av = avasthas.get(target_lord, {})

    # ===== 7. Sphuta fertility coordinates =====
    beeja = compute_beeja_sphuta(planets)
    kshetra = compute_kshetra_sphuta(planets)

    # Apply gender-specific Sphuta logic
    sphuta_active = None
    sphuta_effect = None
    if querent_gender == 'male' and 'error' not in beeja:
        sphuta_active = beeja
        sphuta_sign = beeja['sign_index']
        # 1-based parity check: Aries(1)/Gemini(3)/Leo(5)/Libra(7)/Sag(9)/Aqu(11) = odd
        is_1based_odd = ((sphuta_sign + 1) % 2 == 1)
        if is_alpa_putra_sign(sphuta_sign):
            # Cap Bhava Bala at 50%
            if bhava_net > 50:
                bhava_net = 50
                bhava['net_strength_pct'] = 50
                bhava['sphuta_cap_applied'] = True
            sphuta_effect = {
                'type': 'cap_50',
                'narrative': (
                    f"Beeja Sphuta lands in {SIGNS[sphuta_sign]} (Alpa-Putra sterile sign) "
                    f"— Bhava Bala hard-capped at 50%, forcing verdict toward delays or "
                    "medical intervention."
                ),
            }
        elif is_1based_odd:
            bhava_net = min(100, bhava_net + 15)
            bhava['net_strength_pct'] = bhava_net
            bhava['sphuta_bonus_applied'] = True
            sphuta_effect = {
                'type': 'bonus_15',
                'narrative': (
                    f"Beeja Sphuta lands in {SIGNS[sphuta_sign]} (masculine sign for male "
                    "querent) — +15% Bhava Bala bonus on the progeny axis."
                ),
            }
    elif querent_gender == 'female' and 'error' not in kshetra:
        sphuta_active = kshetra
        sphuta_sign = kshetra['sign_index']
        # 1-based parity check: Taurus(2)/Cancer(4)/Virgo(6)/Sco(8)/Cap(10)/Pis(12) = even
        is_1based_even = ((sphuta_sign + 1) % 2 == 0)
        if is_alpa_putra_sign(sphuta_sign):
            if bhava_net > 50:
                bhava_net = 50
                bhava['net_strength_pct'] = 50
                bhava['sphuta_cap_applied'] = True
            sphuta_effect = {
                'type': 'cap_50',
                'narrative': (
                    f"Kshetra Sphuta lands in {SIGNS[sphuta_sign]} (Alpa-Putra sterile sign) "
                    f"— Bhava Bala hard-capped at 50%, forcing verdict toward delays or "
                    "medical intervention."
                ),
            }
        elif is_1based_even:
            bhava_net = min(100, bhava_net + 15)
            bhava['net_strength_pct'] = bhava_net
            bhava['sphuta_bonus_applied'] = True
            sphuta_effect = {
                'type': 'bonus_15',
                'narrative': (
                    f"Kshetra Sphuta lands in {SIGNS[sphuta_sign]} (feminine sign for female "
                    "querent) — +15% Bhava Bala bonus on the progeny axis."
                ),
            }

    # ===== 8. L1 ↔ L_target aspect + Tajik yogas =====
    asp_l1_lt = pairwise_aspect(lagna_lord, target_lord, chart_data)
    nakta = detect_nakta(lagna_lord, target_lord, chart_data)
    abhara = detect_abhara_yoga(lagna_lord, target_lord, chart_data)
    yama = detect_yama_yoga(lagna_lord, target_lord, chart_data)
    kamboola = detect_kamboola_yoga(lagna_lord, target_lord, chart_data)
    gada = detect_gada_yoga(chart_data)

    # ===== 9. Mars-in-target-house split (rulership-based severity) =====
    mars_in_target = (_planet_house(chart_data, 'Mars') == target_house)
    mars_sign = planets.get('Mars', {}).get('sign_index')
    mars_5th_risk = (mars_in_target and mars_sign is not None
                     and is_mars_5th_high_risk(mars_sign))
    mars_5th_vitality = (mars_in_target and mars_sign is not None
                        and not is_mars_5th_high_risk(mars_sign))

    # ===== 10. Sterile cusp downgrade =====
    target_cusp_sterile = is_alpa_putra_sign(target_sign)

    # ===== 11. Rahu / intervention detection (modern Tajik) =====
    rahu_in_target = (_planet_house(chart_data, 'Rahu') == target_house)
    ketu_in_target = (_planet_house(chart_data, 'Ketu') == target_house)

    # ===== 12. Eclipse proximity =====
    jd_ut = chart_data.get('jd_ut')
    eclipse = None
    if jd_ut is not None:
        eclipse = detect_eclipse_proximity(jd_ut, chart_data,
                                            target_house=target_house)

    # ===== 13. Long-horizon (with Garbha keywords) =====
    long_horizon = detect_long_horizon_query(full_query or query_text)
    if not long_horizon['is_long_horizon']:
        q = (full_query or query_text or '').lower()
        for kw in GARBHA_LONG_HORIZON_EXTRAS:
            if kw in q:
                long_horizon = {
                    'is_long_horizon': True,
                    'matched_keyword': kw,
                    'disclaimer': (
                        "This question concerns a multi-decade horizon — Prashna "
                        "shows the current cycle's trajectory. For lifelong "
                        "fertility forecasting, consult D-7 Saptamsha and Jupiter's "
                        "full transit cycle through your natal 5th from Moon."
                    ),
                }
                break

    # ===== 14. Verdict synthesis =====
    primitive = karya['verdict_primitive']
    modifier = karya['verdict_modifier']

    # Resolution priority:
    #   failure + Kamboola      → YES_WITH_DELAYS (Moon proxy)
    #   failure + Gada          → YES_WITH_DELAYS (structural force, 12mo horizon)
    #   failure + Nakta         → CONDITIONAL_THIRD_PARTY (intermediary)
    #   failure (clean)         → NO
    #   conditional + Rahu/Ketu → CONDITIONAL_MEDICAL
    #   conditional             → YES_WITH_DELAYS
    #   success + Abhara        → YES_WITH_DELAYS (friction)
    #   success + sterile cusp  → YES_WITH_DELAYS
    #   success                 → YES
    if primitive == 'failure' and kamboola:
        verdict = 'YES_WITH_DELAYS'
        verdict_text = ("Yes — through Moon's cosmic proxy (Kamboola Yoga), "
                        "with extended timing")
    elif primitive == 'failure' and gada:
        verdict = 'YES_WITH_DELAYS'
        verdict_text = ("Yes — forced through structural compression (Gada Yoga); "
                        "resolution within a 12-month horizon")
    elif primitive == 'failure' and nakta:
        verdict = 'CONDITIONAL_THIRD_PARTY'
        verdict_text = f'Conditional — only via {nakta["bridge"]} as intermediary'
    elif primitive == 'failure':
        verdict = 'NO'
        verdict_text = 'No — conception not indicated within the Prashna horizon'
    elif primitive == 'conditional':
        if rahu_in_target:
            verdict = 'CONDITIONAL_MEDICAL'
            verdict_text = ("Conditional — Rahu in the progeny axis indicates "
                            "assisted conception (IVF / IUI / surrogacy)")
        else:
            verdict = 'YES_WITH_DELAYS'
            verdict_text = ('Yes — with delays; circumstantial support required '
                            'before the matter consolidates')
    elif primitive == 'success' and modifier == 'with_delays':
        verdict = 'YES_WITH_DELAYS'
        verdict_text = 'Yes — with initial delays'
    elif primitive == 'success':
        verdict = 'YES'
        verdict_text = 'Yes — conception indicated within the Prashna horizon'
    elif primitive == 'confirmed':
        verdict = 'YES'
        verdict_text = 'Yes — strongly confirmed'
    else:
        verdict = 'YES_WITH_DELAYS'
        verdict_text = 'Conditional — chart shows mixed indicators'

    # ===== Verdict downgrades (sterile cusp, Mars risk, Abhara) =====
    if target_cusp_sterile and verdict == 'YES':
        verdict = 'YES_WITH_DELAYS'
        verdict_text = (f"Yes — conception structurally promised, but the "
                        f"{target_house}th cusp falls in {SIGNS[target_sign]} "
                        "(Alpa-Putra sterile sign); physiological preparation required")

    if mars_5th_risk and verdict in ('YES', 'YES_WITH_DELAYS'):
        verdict = 'HIGH_RISK'
        verdict_text = (f"Yes — conception possible, but Mars in {SIGNS[mars_sign]} "
                        f"(risk-grouped sign) within the progeny house flags "
                        "miscarriage/surgical risk")

    if abhara and verdict in ('YES',):
        verdict = 'YES_WITH_DELAYS'
        verdict_text = 'Yes — but with malefic friction (Abhara Yoga)'

    # Adoption signal (Ketu)
    if ketu_in_target and verdict in ('NO', 'YES_WITH_DELAYS'):
        # Soft signal — flag adoption path as supplementary, don't override hard NO
        if verdict == 'NO':
            verdict = 'CONDITIONAL_THIRD_PARTY'
            verdict_text = ("Adoption path indicated — Ketu in the progeny axis "
                            "suggests spiritual detachment from biological conception")

    # ===== INCONCLUSIVE modifier (current-pregnancy intent only) =====
    verdict_modifier_flag = None
    if intent == 'current_pregnancy_confirmation':
        moon_voc = is_moon_void_of_course(chart_data)
        l_target_heavy_combust = is_heavily_combust(planets, target_lord)
        if moon_voc or l_target_heavy_combust:
            verdict_modifier_flag = 'INCONCLUSIVE_RECAST_REQUIRED'

    # ===== Core catalyst (mirrors Vivaha logic) =====
    if karya['positive_satisfied'] >= 2:
        core_catalyst = {
            'yoga': asp_l1_lt.get('yoga', 'Aspect'),
            'between': [f"Lagna Lord ({lagna_lord})",
                        f"{target_house}th Lord ({target_lord})"],
            'narrative': asp_l1_lt.get('narrative', ''),
        }
    elif kamboola:
        core_catalyst = {
            'yoga': 'Kamboola',
            'between': [f"Lagna Lord ({lagna_lord})",
                        f"{target_house}th Lord ({target_lord})"],
            'narrative': kamboola['narrative'],
            'proxy': 'Moon',
        }
    elif gada:
        core_catalyst = {
            'yoga': 'Gada',
            'between': ['All 7 planets in two consecutive Kendras'],
            'narrative': gada['narrative'],
        }
    elif nakta:
        core_catalyst = {
            'yoga': 'Nakta',
            'between': [f"Lagna Lord ({lagna_lord})",
                        f"{target_house}th Lord ({target_lord})"],
            'narrative': nakta.get('narrative', ''),
            'bridge': nakta.get('bridge'),
            'bridge_role': nakta.get('bridge_role'),
            'bridge_role_narrative': nakta.get('bridge_role_narrative'),
        }
    else:
        core_catalyst = {
            'yoga': 'None',
            'between': [f"Lagna Lord ({lagna_lord})",
                        f"{target_house}th Lord ({target_lord})"],
            'narrative': ('No decisive Tajik connection between Lagna and '
                          f'{target_house}th lords.'),
        }

    # Horary-to-natal
    h2n = horary_to_natal_shift(lagna_sign, natal_lagna_sign)

    return {
        'sub_module': 'garbha',
        'intent': intent,
        'verdict': verdict,
        'verdict_text': verdict_text,
        'verdict_modifier': verdict_modifier_flag,
        'target_house': target_house,
        'target_role': target_role,
        'is_husband_pivot': is_husband_pivot,
        'is_lineage_query': is_lineage,
        'querent_gender': querent_gender,
        'certainty_score': strength['score'],
        'certainty_band': strength['band'],
        'certainty_narrative': strength['narrative'],
        'core_catalyst': core_catalyst,
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
        'aspect_l1_lt': asp_l1_lt,
        'nakta_bridge': nakta,
        'abhara_yoga': abhara,
        'yama_yoga': yama,
        'kamboola_yoga': kamboola,
        'gada_yoga': gada,
        'beeja_sphuta': beeja,
        'kshetra_sphuta': kshetra,
        'sphuta_active': sphuta_active,
        'sphuta_effect': sphuta_effect,
        'mars_in_target': mars_in_target,
        'mars_5th_risk': mars_5th_risk,
        'mars_5th_vitality': mars_5th_vitality,
        'target_cusp_sterile': target_cusp_sterile,
        'rahu_in_target': rahu_in_target,
        'ketu_in_target': ketu_in_target,
        'eclipse_proximity': eclipse,
        'karya_chain': karya,
        'strength_scaling': strength,
        'bhava_bala_target': bhava,
        'horary_to_natal': h2n,
        'long_horizon': long_horizon,
    }


# =================================================================
# END OF PHASE 3A — GARBHA ENGINE MATH
# =================================================================
