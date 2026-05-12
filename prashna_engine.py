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

    # 3. Fallback: first character is a vowel → Sun → Leo
    if text_lower[0] in 'aeiou':
        return _resolve_phonetic_match('Sun', PAVARGA_TABLE['Sun'], text_lower[0], 'fallback', 0)

    return {
        'error': f"Could not parse first syllable of '{text[:10]}'",
        'confidence': 0.0,
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
# -----------------------------------------------------------------
# Next: 1H — /prashna_chart FastAPI endpoint (delivered separately
# as a paste-in block for main.py).
# =================================================================
