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
    if planet in SINGLE_LORD_SIGN:
        sign_idx = SINGLE_LORD_SIGN[planet]
        return {
            'sign_index': sign_idx,
            'sign_name': SIGNS[sign_idx],
            'sign_sanskrit': SIGN_SANSKRIT[sign_idx],
            'ruling_planet': planet,
            'position_in_group': None,
            'matched_letter': matched_letter,
            'method': method,
            'confidence': 1.0,
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
    }


def _resolve_phonetic_match(planet: str, data: Dict, matched_letter: str,
                            method: str, iast_idx: Optional[int] = None) -> Dict:
    """Resolve a matched letter to its Lagna sign per Pavarga rules."""
    if data.get('single_lord'):
        sign_idx = SINGLE_LORD_SIGN[planet]
        return {
            'sign_index': sign_idx,
            'sign_name': SIGNS[sign_idx],
            'sign_sanskrit': SIGN_SANSKRIT[sign_idx],
            'ruling_planet': planet,
            'position_in_group': None,
            'matched_letter': matched_letter,
            'method': method,
            'confidence': 1.0 if method != 'fallback' else 0.5,
        }

    # Dual-lord: determine position in group
    if method == 'devanagari':
        position = data['devanagari'].index(matched_letter) + 1
    else:
        position = (iast_idx if iast_idx is not None else 0) + 1

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


def compute_sincerity_score(chart_data: Dict) -> Dict:
    """
    Evaluate querent sincerity per the Prashna Ethical Filter.

    Insincere triggers (each reduces score):
      - Moon in Lagna AND (Saturn or combust-Mercury) in any angular house
      - Mars AND Mercury both aspect the Moon
      - Jupiter or Mercury cast inimical aspect (square/opposition) on the 7th cusp

    Sincere triggers (each increases score):
      - Lagna conjoined with Jupiter / Venus / unafflicted Mercury
      - Moon aspected by Jupiter
      - Mercury or Jupiter in Lagna or 7th house

    Returns dict with score (0–100), verdict, triggers, narrative_lead.
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

    # -- INSINCERE 3: Jupiter or Mercury inimical aspect (square/opposition) on 7th cusp
    # Only counts when the planet sits elsewhere — occupation of Lagna or 7th supersedes
    # this aspect-from-elsewhere reading and is handled under SINCERE 3 instead.
    seventh_cusp_lon = ((lagna_sign_idx + 6) % 12) * 30.0
    for p in ['Jupiter', 'Mercury']:
        if _planet_in_house(houses, p, 1) or _planet_in_house(houses, p, 7):
            continue
        p_lon = planets.get(p, {}).get('longitude')
        if p_lon is None:
            continue
        if _within_aspect_orb(p_lon, seventh_cusp_lon, DEEPTAMSHA[p],
                              aspect_angles=[90, 180, 270]):
            triggers_insincere.append(f"{p} casts an inimical aspect on the 7th cusp")
            score -= 10

    # -- SINCERE 1: Lagna conjoined with natural benefics
    for b in ['Jupiter', 'Venus']:
        if _planet_in_house(houses, b, 1):
            triggers_sincere.append(f"{b} occupies the Lagna")
            score += 12
    if (_planet_in_house(houses, 'Mercury', 1)
            and not _is_combust(planets, 'Mercury')):
        triggers_sincere.append("Mercury (unafflicted) occupies the Lagna")
        score += 8

    # -- SINCERE 2: Moon aspected by Jupiter
    if moon_lon is not None:
        jup_lon = planets.get('Jupiter', {}).get('longitude')
        if jup_lon is not None and _within_aspect_orb(
                jup_lon, moon_lon, DEEPTAMSHA['Jupiter'], DEEPTAMSHA['Moon']):
            triggers_sincere.append("Moon is aspected by Jupiter")
            score += 15

    # -- SINCERE 3: Mercury or Jupiter in Lagna or 7th house
    for p in ['Mercury', 'Jupiter']:
        if _planet_in_house(houses, p, 1) or _planet_in_house(houses, p, 7):
            triggers_sincere.append(f"{p} occupies the Lagna or the 7th house")
            score += 8
            break  # one bonus per group

    score = max(0, min(100, score))

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

        # Resolve by precedence
        if qualifying:
            winning = min(qualifying, key=lambda s: AVASTHA_PRECEDENCE.index(s))
            cond, outcome = AVASTHA_OUTCOMES[winning]
            result[planet_name] = {
                'avastha': winning,
                'condition': cond,
                'outcome': outcome,
                'priority_index': AVASTHA_PRECEDENCE.index(winning),
                'all_qualifying': qualifying,
            }
        else:
            result[planet_name] = {
                'avastha': 'Neutral',
                'condition': 'No specific state qualified',
                'outcome': 'Mixed / Mediocre results',
                'priority_index': 99,
                'all_qualifying': [],
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

    if not bridge_candidates:
        return None

    # Pick the fastest qualifying bridge (first in hierarchy)
    bridge_candidates.sort(key=lambda x: VELOCITY_HIERARCHY.index(x['bridge']))
    primary = bridge_candidates[0]

    return {
        'planet_a': p_a,
        'planet_b': p_b,
        'bridge': primary['bridge'],
        'bridge_lon': primary['bridge_lon'],
        'all_bridges': bridge_candidates,
        'narrative': (f"Nakta — {p_a} and {p_b} have no direct aspect, but "
                      f"{primary['bridge']} bridges them. Result reaches the querent "
                      f"through a mediator."),
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

    # --- Rule 2: Mutual Exchange + Moon aspect ---
    moon_in = (moon_aspect_a.get('within_orb', False)
               or moon_aspect_b.get('within_orb', False))
    rule2_sat = rule1_sat and moon_in
    rules.append({
        'rule': 'Mutual Exchange + Moon',
        'satisfied': rule2_sat,
        'narrative': (
            f"L1 ↔ L{target_house_num} are in aspect AND Moon aspects "
            f"{lagna_lord if moon_aspect_a.get('within_orb') else target_lord} — "
            f"Moon validates the connection."
            if rule2_sat else
            "Moon is not aspecting either significator within orb; the connection "
            "lacks lunar witness."
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

    verdict_modifier = 'with_delays' if (rule4_sat and positive_count >= 1) else None

    return {
        'querent_lord': lagna_lord,
        'quesited_lord': target_lord,
        'rules': rules,
        'positive_satisfied': positive_count,
        'rule4_fired': rule4_sat,
        'verdict_primitive': verdict_primitive,
        'verdict_modifier': verdict_modifier,
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
                    natal_lagna_sign: Optional[int] = None) -> Dict:
    """
    Full Vivaha (Marriage) judgment package. Bundles Karya chain output with
    marriage-specific match-type detection, third-party interference scan, and
    emotional reciprocity reading.

    Args:
        chart_data:        Prashna chart dict (from build_query_chart or base_chart)
        natal_lagna_sign:  Optional 0-11 sign index of the user's natal Lagna

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

    # 4. Avasthas for both significators
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

    # 8. Nakta bridge (if no direct aspect, is there a bridge planet?)
    nakta = detect_nakta(lagna_lord, seventh_lord, chart_data)

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
        }
    else:
        core_catalyst = {
            'yoga': 'None',
            'between': [f"Lagna Lord ({lagna_lord})", f"7th Lord ({seventh_lord})"],
            'narrative': 'No decisive Tajik connection between the two significators.',
        }

    # Horary-to-natal
    h2n = horary_to_natal_shift(lagna_sign, natal_lagna_sign)

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
            'is_combust': _is_combust(planets, lagna_lord),
            'sign': planets.get(lagna_lord, {}).get('sign'),
            'house': _planet_house(chart_data, lagna_lord),
        },
        'quesited_lord': {
            'name': seventh_lord,
            'avastha': quesited_avastha.get('avastha'),
            'condition': quesited_avastha.get('condition'),
            'outcome': quesited_avastha.get('outcome'),
            'is_combust': _is_combust(planets, seventh_lord),
            'sign': planets.get(seventh_lord, {}).get('sign'),
            'house': _planet_house(chart_data, seventh_lord),
        },
        'aspect_l1_l7': asp_l1_l7,
        'nakta_bridge': nakta,
        'match_type': match_type,
        'match_narrative': match_narrative,
        'third_party_interference': interference,
        'emotional_reciprocity': reciprocity,
        'reciprocity_narrative': recip_narrative,
        'karya_chain': karya,
        'strength_scaling': strength,
        'bhava_bala_7th': bhava_7,
        'horary_to_natal': h2n,
    }


# =================================================================
# END OF PHASE 1H + 1I + 1J + 1K (Vivaha)
# =================================================================
