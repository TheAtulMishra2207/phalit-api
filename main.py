from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import swisseph as swe
from datetime import datetime, timedelta
import requests
import os
import json
from typing import Any, Dict

# ─────────────────────────────────────────────────────────────────────────────
# APP SETUP
# ─────────────────────────────────────────────────────────────────────────────

app = FastAPI(title="Phalit.ai Chart Engine", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────

SIGNS = [
    'Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo',
    'Libra', 'Scorpio', 'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces'
]

SIGN_ABBR = ['Ari', 'Tau', 'Gem', 'Can', 'Leo', 'Vir', 'Lib', 'Sco', 'Sag', 'Cap', 'Aqu', 'Pis']

SIGN_LORDS = [
    'Mars', 'Venus', 'Mercury', 'Moon', 'Sun', 'Mercury',
    'Venus', 'Mars', 'Jupiter', 'Saturn', 'Saturn', 'Jupiter'
]

PLANETS = ['Sun', 'Moon', 'Mars', 'Mercury', 'Jupiter', 'Venus', 'Saturn', 'Rahu', 'Ketu']

SWE_ID = {
    'Sun': swe.SUN, 'Moon': swe.MOON, 'Mars': swe.MARS,
    'Mercury': swe.MERCURY, 'Jupiter': swe.JUPITER,
    'Venus': swe.VENUS, 'Saturn': swe.SATURN,
    'Rahu': swe.MEAN_NODE
}

NAKSHATRAS = [
    'Ashwini', 'Bharani', 'Krittika', 'Rohini', 'Mrigashira', 'Ardra',
    'Punarvasu', 'Pushya', 'Ashlesha', 'Magha', 'Purva Phalguni', 'Uttara Phalguni',
    'Hasta', 'Chitra', 'Swati', 'Vishakha', 'Anuradha', 'Jyeshtha',
    'Mula', 'Purva Ashadha', 'Uttara Ashadha', 'Shravana', 'Dhanishtha',
    'Shatabhisha', 'Purva Bhadrapada', 'Uttara Bhadrapada', 'Revati'
]

NAKSHATRA_LORDS = [
    'Ketu', 'Venus', 'Sun', 'Moon', 'Mars', 'Rahu', 'Jupiter', 'Saturn', 'Mercury',
    'Ketu', 'Venus', 'Sun', 'Moon', 'Mars', 'Rahu', 'Jupiter', 'Saturn', 'Mercury',
    'Ketu', 'Venus', 'Sun', 'Moon', 'Mars', 'Rahu', 'Jupiter', 'Saturn', 'Mercury'
]

DASHA_ORDER = ['Ketu', 'Venus', 'Sun', 'Moon', 'Mars', 'Rahu', 'Jupiter', 'Saturn', 'Mercury']
DASHA_YEARS = {
    'Ketu': 7, 'Venus': 20, 'Sun': 6, 'Moon': 10, 'Mars': 7,
    'Rahu': 18, 'Jupiter': 16, 'Saturn': 19, 'Mercury': 17
}

# ─── Dignity Tables ───────────────────────────────────────────────────────────

EXALTATION_SIGN = {
    'Sun': 0, 'Moon': 1, 'Mars': 9, 'Mercury': 5,
    'Jupiter': 3, 'Venus': 11, 'Saturn': 6
}

DEBILITATION_SIGN = {
    'Sun': 6, 'Moon': 7, 'Mars': 3, 'Mercury': 11,
    'Jupiter': 9, 'Venus': 5, 'Saturn': 0
}

OWN_SIGNS = {
    'Sun': [4],
    'Moon': [3],
    'Mars': [0, 7],
    'Mercury': [2, 5],
    'Jupiter': [8, 11],
    'Venus': [1, 6],
    'Saturn': [9, 10]
}

MOOLATRIKONA = {
    'Sun':     (4, 20),
    'Moon':    (1, 30),
    'Mars':    (0, 12),
    'Mercury': (5, 20),
    'Jupiter': (8, 10),
    'Venus':   (6, 15),
    'Saturn':  (9, 20),
}

NATURAL_FRIENDS = {
    'Sun':     ['Moon', 'Mars', 'Jupiter'],
    'Moon':    ['Sun', 'Mercury'],
    'Mars':    ['Sun', 'Moon', 'Jupiter'],
    'Mercury': ['Sun', 'Venus'],
    'Jupiter': ['Sun', 'Moon', 'Mars'],
    'Venus':   ['Mercury', 'Saturn'],
    'Saturn':  ['Mercury', 'Venus'],
    'Rahu':    ['Venus', 'Saturn'],
    'Ketu':    ['Mars', 'Jupiter']
}

NATURAL_ENEMIES = {
    'Sun':     ['Venus', 'Saturn'],
    'Moon':    [],
    'Mars':    ['Mercury'],
    'Mercury': ['Moon'],
    'Jupiter': ['Mercury', 'Venus'],
    'Venus':   ['Sun', 'Moon'],
    'Saturn':  ['Sun', 'Moon', 'Mars'],
    'Rahu':    ['Sun', 'Moon'],
    'Ketu':    ['Venus', 'Saturn']
}

NAKSHATRA_SPAN = 360.0 / 27

# ─────────────────────────────────────────────────────────────────────────────
# D9 NAVAMSHA CALCULATION — Elemental Triplicity System
# Starting sign based on D1 sign's element:
#   Fire (Aries, Leo, Sagittarius)       → start from Aries (0)
#   Earth (Taurus, Virgo, Capricorn)     → start from Capricorn (9)
#   Air (Gemini, Libra, Aquarius)        → start from Libra (6)
#   Water (Cancer, Scorpio, Pisces)      → start from Cancer (3)
# Mathematically equivalent to: floor((lon × 9 % 360) / 30)
# ─────────────────────────────────────────────────────────────────────────────

def calc_d9_sign(lon: float) -> dict:
    sign_index = int(lon / 30)
    degree_in_sign = lon % 30
    pada = int(degree_in_sign * 9 / 30)   # 0-indexed pada (0-8)
    element = sign_index % 4
    starts = {0: 0, 1: 9, 2: 6, 3: 3}    # Fire, Earth, Air, Water
    d9_sign_index = (starts[element] + pada) % 12
    return {
        "d9_sign": SIGNS[d9_sign_index],
        "d9_sign_abbr": SIGN_ABBR[d9_sign_index],
        "d9_sign_index": d9_sign_index,
        "d9_lord": SIGN_LORDS[d9_sign_index]
    }

def calc_d20_sign(lon: float) -> dict:
    """D-20 Vimsamsa: each sign divided into 20 parts of 1°30' each."""
    sign_index = int(lon / 30)
    degree_in_sign = lon % 30
    part = int(degree_in_sign / 1.5)   # 0-19
    # Odd signs start from Aries (0), Even signs start from Sagittarius (8)
    if sign_index % 2 == 0:  # Odd sign (Aries, Gemini…)
        d20_sign_index = part % 12
    else:                     # Even sign (Taurus, Cancer…)
        d20_sign_index = (8 + part) % 12
    return {
        "d20_sign_index": d20_sign_index,
        "d20_sign": SIGNS[d20_sign_index],
        "d20_lord": SIGN_LORDS[d20_sign_index]
    }

# ─────────────────────────────────────────────────────────────────────────────
# AYANAMSHA — Manual Lahiri (IAE standard)
# Avoids pyswisseph version discrepancies on hosted environments
# ─────────────────────────────────────────────────────────────────────────────

def get_lahiri_ayanamsha(jd: float) -> float:
    """
    Compute Lahiri ayanamsha using the IAE reference formula.
    Reference epoch: Jan 1.0, 1950 TT = JD 2433282.42345905
    Value at epoch:  23°9'57.9" = 23.16608333°
    Annual rate:     50.2388475" per year
    """
    T0 = 2433282.42345905
    AYAN_T0 = 23.16608333
    RATE = 50.2388475 / 3600.0
    return AYAN_T0 + ((jd - T0) / 365.25) * RATE

# ─────────────────────────────────────────────────────────────────────────────
# CALCULATION FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

def to_julian_day(date_str: str, time_str: str, utc_offset: float) -> float:
    """Convert local birth date/time to Julian Day (UTC)."""
    dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
    utc_dt = dt - timedelta(hours=utc_offset)
    jd = swe.julday(
        utc_dt.year, utc_dt.month, utc_dt.day,
        utc_dt.hour + utc_dt.minute / 60.0 + utc_dt.second / 3600.0
    )
    return jd


def calc_lagna(jd: float, lat: float, lon: float) -> dict:
    """Calculate sidereal Ascendant using manual Lahiri ayanamsha."""
    cusps, ascmc = swe.houses(jd, lat, lon, b'P')
    asc_tropical = ascmc[0]
    ayanamsha = get_lahiri_ayanamsha(jd)
    asc_sidereal = (asc_tropical - ayanamsha) % 360.0
    sign_index = int(asc_sidereal / 30)
    degree_in_sign = asc_sidereal % 30
    d9 = calc_d9_sign(asc_sidereal)
    return {
        "sign": SIGNS[sign_index],
        "sign_abbr": SIGN_ABBR[sign_index],
        "sign_index": sign_index,
        "degree": round(degree_in_sign, 4),
        "longitude": round(asc_sidereal, 4),
        "lord": SIGN_LORDS[sign_index],
        "ayanamsha": round(ayanamsha, 4),
        "d9_sign": d9["d9_sign"],
        "d9_sign_abbr": d9["d9_sign_abbr"],
        "d9_sign_index": d9["d9_sign_index"],
        "d9_lord": d9["d9_lord"]
    }


def get_nakshatra_info(lon: float) -> dict:
    """Return nakshatra name, lord, pada."""
    nak_index = int(lon / NAKSHATRA_SPAN) % 27
    pos_in_nak = lon % NAKSHATRA_SPAN
    pada = int(pos_in_nak / (NAKSHATRA_SPAN / 4)) + 1
    return {
        "name": NAKSHATRAS[nak_index],
        "lord": NAKSHATRA_LORDS[nak_index],
        "pada": pada,
        "index": nak_index
    }


def get_dignity(planet: str, sign_index: int, degree_in_sign: float) -> str:
    """Determine planetary dignity using classical Parashari rules."""
    # Rahu & Ketu — BPHS Chapter 47
    if planet == 'Rahu':
        if sign_index == 1:
            return 'Exalted (Uccha)'
        elif sign_index == 7:
            return 'Debilitated (Neecha)'
        return 'Node'

    if planet == 'Ketu':
        if sign_index == 7:
            return 'Exalted (Uccha)'
        elif sign_index == 1:
            return 'Debilitated (Neecha)'
        return 'Node'

    # Seven classical planets
    if DEBILITATION_SIGN.get(planet) == sign_index:
        return 'Debilitated (Neecha)'

    if EXALTATION_SIGN.get(planet) == sign_index:
        return 'Exalted (Uccha)'

    if planet in MOOLATRIKONA:
        mt_sign, mt_max_deg = MOOLATRIKONA[planet]
        if mt_sign == sign_index and degree_in_sign <= mt_max_deg:
            return 'Moolatrikona'

    if sign_index in OWN_SIGNS.get(planet, []):
        return 'Own Sign (Swa)'

    sign_lord = SIGN_LORDS[sign_index]
    if sign_lord == planet:
        return 'Own Sign (Swa)'

    friends = NATURAL_FRIENDS.get(planet, [])
    enemies = NATURAL_ENEMIES.get(planet, [])

    if sign_lord in friends:
        return 'Friendly Sign (Mitra)'
    if sign_lord in enemies:
        return 'Enemy Sign (Shatru)'

    return 'Neutral Sign (Sama)'


def calc_planet_data(jd: float, planet: str, lagna_sign_index: int) -> dict:
    """Calculate full data for one planet using manual ayanamsha."""
    flags = swe.FLG_SWIEPH | swe.FLG_SPEED
    ayanamsha = get_lahiri_ayanamsha(jd)

    if planet == 'Ketu':
        rahu_result, _ = swe.calc_ut(jd, swe.MEAN_NODE, flags)
        lon_tropical = (rahu_result[0] + 180.0) % 360.0
        lon = (lon_tropical - ayanamsha) % 360.0
        speed = -rahu_result[3]
        retrograde = True
    else:
        result, _ = swe.calc_ut(jd, SWE_ID[planet], flags)
        lon_tropical = result[0]
        lon = (lon_tropical - ayanamsha) % 360.0
        speed = result[3]
        retrograde = speed < 0

    sign_index = int(lon / 30)
    degree_in_sign = lon % 30
    house = ((sign_index - lagna_sign_index) % 12) + 1
    nakshatra = get_nakshatra_info(lon)
    dignity = get_dignity(planet, sign_index, degree_in_sign)
    d9 = calc_d9_sign(lon)
    d20 = calc_d20_sign(lon)
    d9_dignity = get_dignity(planet, d9["d9_sign_index"], 0)
    vargottama = (sign_index == d9["d9_sign_index"])

    return {
        "sign": SIGNS[sign_index],
        "sign_abbr": SIGN_ABBR[sign_index],
        "sign_index": sign_index,
        "house": house,
        "degree": round(degree_in_sign, 4),
        "longitude": round(lon, 4),
        "speed": round(speed, 4),
        "retrograde": retrograde,
        "nakshatra": nakshatra["name"],
        "nakshatra_lord": nakshatra["lord"],
        "nakshatra_pada": nakshatra["pada"],
        "dignity": dignity,
        "d9_sign": d9["d9_sign"],
        "d9_sign_abbr": d9["d9_sign_abbr"],
        "d9_sign_index": d9["d9_sign_index"],
        "d9_lord": d9["d9_lord"],
        "d9_dignity": d9_dignity,
        "vargottama": vargottama,
        "d20_sign_index": d20["d20_sign_index"],
        "d20_sign": d20["d20_sign"],
        "d20_lord": d20["d20_lord"]
    }


def calc_all_planets(jd: float, lagna_sign_index: int) -> dict:
    result = {}
    for planet in PLANETS:
        result[planet] = calc_planet_data(jd, planet, lagna_sign_index)
    return result


def calc_houses(lagna_sign_index: int) -> dict:
    houses = {}
    for h in range(1, 13):
        sign_idx = (lagna_sign_index + h - 1) % 12
        houses[str(h)] = {
            "sign": SIGNS[sign_idx],
            "sign_abbr": SIGN_ABBR[sign_idx],
            "sign_index": sign_idx,
            "lord": SIGN_LORDS[sign_idx]
        }
    return houses


def calc_vimshottari_dasha(moon_lon: float, birth_date_str: str) -> dict:
    """Calculate Vimshottari Dasha sequence from birth."""
    nak_index = int(moon_lon / NAKSHATRA_SPAN) % 27
    pos_in_nak = moon_lon % NAKSHATRA_SPAN
    nak_lord = NAKSHATRA_LORDS[nak_index]
    nak_dasha_years = DASHA_YEARS[nak_lord]

    fraction_elapsed = pos_in_nak / NAKSHATRA_SPAN
    fraction_remaining = 1.0 - fraction_elapsed
    years_remaining_at_birth = nak_dasha_years * fraction_remaining

    birth_date = datetime.strptime(birth_date_str, "%Y-%m-%d")
    today = datetime.utcnow()

    lord_start_index = DASHA_ORDER.index(nak_lord)
    sequence = []
    current_start = birth_date

    # First dasha (partial)
    delta_days = years_remaining_at_birth * 365.25
    end = current_start + timedelta(days=delta_days)
    sequence.append({
        "planet": nak_lord,
        "start": current_start.strftime("%Y-%m-%d"),
        "end": end.strftime("%Y-%m-%d"),
        "years": round(years_remaining_at_birth, 2)
    })
    current_start = end

    # Remaining 8 dashas (full)
    for i in range(1, 9):
        lord = DASHA_ORDER[(lord_start_index + i) % 9]
        yrs = DASHA_YEARS[lord]
        end = current_start + timedelta(days=yrs * 365.25)
        sequence.append({
            "planet": lord,
            "start": current_start.strftime("%Y-%m-%d"),
            "end": end.strftime("%Y-%m-%d"),
            "years": yrs
        })
        current_start = end

    # Find current Mahadasha
    current_maha = None
    for d in sequence:
        d_start = datetime.strptime(d["start"], "%Y-%m-%d")
        d_end = datetime.strptime(d["end"], "%Y-%m-%d")
        if d_start <= today <= d_end:
            current_maha = d
            break
    if not current_maha:
        current_maha = sequence[-1]

    # Antardashas within current Mahadasha
    maha_lord = current_maha["planet"]
    maha_lord_idx = DASHA_ORDER.index(maha_lord)
    maha_total_years = DASHA_YEARS[maha_lord]
    maha_start = datetime.strptime(current_maha["start"], "%Y-%m-%d")

    antar_sequence = []
    antar_start = maha_start

    for i in range(9):
        antar_lord = DASHA_ORDER[(maha_lord_idx + i) % 9]
        antar_years = (maha_total_years * DASHA_YEARS[antar_lord]) / 120.0
        antar_end = antar_start + timedelta(days=antar_years * 365.25)
        antar_sequence.append({
            "planet": antar_lord,
            "start": antar_start.strftime("%Y-%m-%d"),
            "end": antar_end.strftime("%Y-%m-%d"),
            "years": round(antar_years, 2)
        })
        antar_start = antar_end

    # Find current Antardasha
    current_antar = None
    for a in antar_sequence:
        a_start = datetime.strptime(a["start"], "%Y-%m-%d")
        a_end = datetime.strptime(a["end"], "%Y-%m-%d")
        if a_start <= today <= a_end:
            current_antar = a
            break
    if not current_antar:
        current_antar = antar_sequence[0]

    return {
        "moon_nakshatra": NAKSHATRAS[nak_index],
        "moon_nakshatra_lord": nak_lord,
        "current_mahadasha": current_maha,
        "current_antardasha": current_antar,
        "mahadasha_sequence": sequence,
        "antardasha_sequence": antar_sequence
    }

# ─────────────────────────────────────────────────────────────────────────────
# REQUEST MODEL
# ─────────────────────────────────────────────────────────────────────────────

class ChartRequest(BaseModel):
    date: str
    time: str
    lat: float
    lon: float
    utc_offset: float

class PersonalityRequest(BaseModel):
    name: str
    chart_brief: Dict[str, Any]

class D2ReportRequest(BaseModel):
    name: str
    chart_brief: Dict[str, Any]

# ─────────────────────────────────────────────────────────────────────────────
# ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "Phalit.ai Chart Engine", "version": "1.0.0"}


@app.get("/geocode")
def geocode_place(place: str):
    try:
        response = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": place, "format": "json", "limit": 1},
            headers={"User-Agent": "Phalit.ai/1.0 (contact@phalit.ai)"},
            timeout=10
        )
        results = response.json()
        if not results:
            raise HTTPException(status_code=404, detail=f"Place '{place}' not found.")
        r = results[0]
        return {
            "lat": float(r["lat"]),
            "lon": float(r["lon"]),
            "display_name": r["display_name"]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Geocoding error: {str(e)}")


@app.post("/chart")
def calculate_chart(req: ChartRequest):
    try:
        jd = to_julian_day(req.date, req.time, req.utc_offset)
        lagna = calc_lagna(jd, req.lat, req.lon)
        planets = calc_all_planets(jd, lagna["sign_index"])
        houses = calc_houses(lagna["sign_index"])
        moon_lon = planets["Moon"]["longitude"]
        dasha = calc_vimshottari_dasha(moon_lon, req.date)

        return {
            "input": {
                "date": req.date,
                "time": req.time,
                "lat": req.lat,
                "lon": req.lon,
                "utc_offset": req.utc_offset
            },
            "lagna": lagna,
            "planets": planets,
            "houses": houses,
            "dasha": dasha
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chart calculation error: {str(e)}")


# ─────────────────────────────────────────────────────────────────────────────
# PERSONALITY REPORT ENDPOINT
# Proxies to Anthropic API server-side to avoid CORS restrictions
# Requires ANTHROPIC_API_KEY environment variable set on Render
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/personality")
def generate_personality_report(req: PersonalityRequest):
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not configured on server.")

    brief = req.chart_brief
    name  = req.name or "the native"

    system_prompt = """You are a prose writer producing a premium consumer personality report for a Vedic astrology platform.
Your job is ONLY to rewrite the provided classical corpus analysis into flowing, beautiful second-person prose.
You are NOT the astrologer. The astrology has already been done. Your corpus contains the analysis.

Absolute rules:
1. Use ONLY the information in the corpus provided. Do not add your own astrological knowledge or interpretations.
2. ZERO technical terminology of any kind in the output. This means:
   - No yoga names (not "Sasa Yoga", not "Dehakashta Yoga", not any yoga name)
   - No nakshatra names (not "Vishakha", not "Bharani", not any nakshatra name)
   - No planet names (not "Saturn", not "Mars", not "Venus" — say "a disciplining force", "a warrior energy", "a graceful relational energy")
   - No house numbers (not H1, not 7th house)
   - No dignity labels (not "exalted", not "debilitated", not "retrograde")
   - No Sanskrit terms of any kind
3. No meta-commentary. Never say "your chart shows" or "astrologically". State things as direct truths.
4. Pure second-person prose. "You are...", "Your..."
5. Each section minimum 5-7 rich sentences. No bullet points. Flowing paragraphs only.
6. Synthesise — weave corpus material into coherent narrative. Do not list traits.
7. classical_positive traits are strengths. classical_caution traits are challenges to manage.
8. rashi_prose = how this energy expresses through this sign. house_prose = what it does in this life domain.
9. Write exactly 5 sections with these headings (use ### before each):
   ### Core Identity and Temperament
   ### Mind, Intellect and Communication
   ### Career, Ambition and Public Life
   ### Relationships, Love and Family
   ### Vitality, Health and Inner Landscape
10. Complete all 5 sections fully. Do not truncate."""

    user_prompt = f"""Write a detailed personality report for {name} using ONLY the corpus analysis below as your source material.

PHYSICAL BASELINE:
- Build: {brief.get('physical', {}).get('height_prose', '')}
- Complexion: {brief.get('physical', {}).get('complexion_prose', '')}

LAGNA LORD (the planet governing core identity):
Domain: {brief.get('lagna', {}).get('lagna_lord', {}).get('domain', '')}
Classical result: {brief.get('lagna', {}).get('lagna_lord', {}).get('lv_classical', '')}
Retrograde: {brief.get('lagna', {}).get('lagna_lord', {}).get('retrograde', False)}

LAGNA NAKSHATRA (soul signature):
{brief.get('lagna_nakshatra', {})}

MOON NAKSHATRA (emotional/mind signature):
{brief.get('moon_nakshatra', {})}

PLANETARY CORPUS (use rashi_prose, house_prose, classical_positive, classical_caution for each planet):
{brief.get('planets', [])}

CLASSICAL COMBINATIONS PRESENT:
Benefic: {brief.get('benefic_yogas', [])}
Challenging: {brief.get('malefic_yogas', [])}

PLANETS AT PEAK POTENCY: {brief.get('param_uccha', [])}

Now write the 5-section report. Each section 5-8 sentences minimum. Synthesise — do not list traits. Make it feel deeply personal."""

    try:
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            },
            json={
                "model": "claude-sonnet-4-6",
                "max_tokens": 3000,
                "system": system_prompt,
                "messages": [{"role": "user", "content": user_prompt}]
            },
            timeout=60
        )
        if response.status_code != 200:
            raise HTTPException(
                status_code=500,
                detail=f"Anthropic API error {response.status_code}: {response.text[:600]}"
            )
        data = response.json()
        text = "".join(b["text"] for b in data.get("content", []) if b.get("type") == "text")
        return {"report": text}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Report generation error: {str(e)}")


# ─────────────────────────────────────────────────────────────────────────────
# D2 HORA WEALTH REPORT ENDPOINT
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/d2report")
def generate_d2_report(req: D2ReportRequest):
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not configured on server.")

    brief = req.chart_brief
    name  = req.name or "the native"

    system_prompt = """You are writing a focused wealth report for a Vedic astrology platform.
Stay strictly on topic. Cover only: wealth prospects and the nature/sources of wealth.

Absolute rules:
1. Use ONLY the corpus provided. No external knowledge.
2. ZERO technical terminology — no planet names, sign names, house numbers, Sanskrit terms, yoga names.
3. Second person throughout. "You will...", "Your wealth..."
4. Each section 7-10 sentences. No bullet points. Rich, expansive, specific prose.
5. NO personality observations. NO family life. NO speech analysis. NO career commentary. NO spiritual meandering.
6. Write exactly 2 sections with these headings (use ### before each):
   ### Your Wealth and Financial Prospects
   ### The Nature and Sources of Your Wealth
7. Both sections must be detailed and thorough. Be specific about wealth patterns, challenges, and the quality of financial life."""

    user_prompt = f"""Write a detailed wealth report for {name}.

HORA CHART ANALYSIS (wealth temperament and active/passive orientation):
{brief.get('parashara', {})}

DHANA YOGA RESULTS:
- Wealth category: {brief.get('dhana', {}).get('wealth_verdict', '')}
- Verdict detail: {brief.get('dhana', {}).get('verdict_detail', '')}
- Dhani Yogas active: {brief.get('dhana', {}).get('dhani_count', 0)}
- Daridra Yogas active: {brief.get('dhana', {}).get('daridra_count', 0)}
- Strong Dhani: {brief.get('dhana', {}).get('strong_dhani', 0)}
- Dhani details: {brief.get('dhana', {}).get('dhani_yogas', [])}
- Daridra details: {brief.get('dhana', {}).get('daridra_yogas', [])}

Write 2 rich, expanded sections on wealth prospects and sources of wealth. Each section must be thorough and specific."""

    try:
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            },
            json={
                "model": "claude-sonnet-4-6",
                "max_tokens": 2000,
                "system": system_prompt,
                "messages": [{"role": "user", "content": user_prompt}]
            },
            timeout=60
        )
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail=f"Anthropic API error {response.status_code}: {response.text[:600]}")
        data = response.json()
        text = "".join(b["text"] for b in data.get("content", []) if b.get("type") == "text")
        return {"report": text}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"D2 report error: {str(e)}")


# ─────────────────────────────────────────────────────────────────────────────
# D3 DREKKANA REPORT ENDPOINT
# ─────────────────────────────────────────────────────────────────────────────

class D3ReportRequest(BaseModel):
    name: str
    chart_brief: Dict[str, Any]

@app.post("/d3report")
def generate_d3_report(req: D3ReportRequest):
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not configured on server.")

    brief = req.chart_brief
    name  = req.name or "the native"

    system_prompt = """You are writing a focused siblings, courage and initiative report for a Vedic astrology platform.
Stay strictly on topic. Cover only: siblings, courage, communication, mental agility, short-distance travel, willpower, and friends.

Absolute rules:
1. Use ONLY the corpus provided. No external knowledge.
2. ZERO technical terminology — no planet names, sign names, house numbers, Sanskrit terms, yoga names.
3. Second person throughout. "You are...", "Your siblings...", "Your courage..."
4. Each section 4-6 sentences. No bullet points. Direct, factual, specific prose.
5. NO personality observations. NO career analysis. NO spiritual commentary. NO karmic philosophy.
6. Write exactly 4 sections with these headings (use ### before each):
   ### Your Siblings
   ### Courage, Willpower and Initiative
   ### Communication, Mental Agility and Short Travel
   ### Friends, Allies and Your Social Network
7. Complete all 4 sections. Be specific."""

    user_prompt = f"""Write a focused siblings and courage report for {name}.

LAGNA ARCHETYPE (primal drive quality):
{brief.get('lagna_archetype', {})}

CORE VARIABLES (3rd house lord position and condition):
{brief.get('core_variables', {})}

KARMIC TIMELINE — use only the present birth section for this report:
{[t for t in brief.get('tri_janma', []) if t.get('phase') == 'Present Birth']}

SIBLING & COURAGE PATTERNS:
{brief.get('tritiya_yogas', [])}

SPECIAL COMBINATIONS:
{brief.get('special_combinations', [])}

Write 4 focused sections. No fluff. Be specific about siblings, courage, communication, travel, willpower and friends."""

    try:
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
            json={"model": "claude-sonnet-4-6", "max_tokens": 2500, "system": system_prompt,
                  "messages": [{"role": "user", "content": user_prompt}]},
            timeout=60
        )
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail=f"Anthropic API error {response.status_code}: {response.text[:600]}")
        data = response.json()
        text = "".join(b["text"] for b in data.get("content", []) if b.get("type") == "text")
        return {"report": text}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"D3 report error: {str(e)}")


# ─────────────────────────────────────────────────────────────────────────────
# D4 CHATURTHAMSHA REPORT ENDPOINT
# ─────────────────────────────────────────────────────────────────────────────

class D4ReportRequest(BaseModel):
    name: str
    chart_brief: Dict[str, Any]

@app.post("/d4report")
def generate_d4_report(req: D4ReportRequest):
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not configured on server.")

    brief = req.chart_brief
    name  = req.name or "the native"

    system_prompt = """You are writing a focused property and domestic life report for a Vedic astrology platform.
This is NOT a personality report. Stay strictly on topic: house/property, vehicles, domestic comfort, and the mother.

Absolute rules:
1. Use ONLY the corpus provided. No external knowledge.
2. ZERO technical terminology — no planet names, sign names, house numbers, Sanskrit terms, yoga names.
3. Second person throughout. "You will...", "Your home...", "Your mother..."
4. Each section 4-6 sentences. No bullet points. Direct, factual, specific prose.
5. NO philosophical meandering. NO personality observations. NO career or relationship references.
6. Write exactly 4 sections with these headings (use ### before each):
   ### Your Home and Property
   ### The Character and Type of Your Properties
   ### Vehicles and Comfort
   ### Your Mother
7. Complete all 4 sections. Be specific about number of properties where indicated."""

    user_prompt = f"""Write a focused property and domestic life report for {name}.

RESIDENTIAL PATTERN: {brief.get('residential_nature', '')}

PROPERTY TYPE INDICATORS:
{brief.get('property_characteristics', [])}

4TH LORD CLASSICAL RESULT: {brief.get('fourth_lord_classical_result', '')}

PROPERTY COUNT INDICATED: approximately {brief.get('property_count_indicated', '?')} properties over a lifetime
(Based on {brief.get('property_count_planets', [])} in auspicious positions)

SPECIAL CONDITIONS:
{brief.get('special_conditions', [])}

HOME & HAPPINESS PATTERNS:
{brief.get('chaturtha_yogas', [])}

Write 4 focused sections on home/property, property type, vehicles/comfort, and mother. No fluff. Be specific."""

    try:
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
            json={"model": "claude-sonnet-4-6", "max_tokens": 2500, "system": system_prompt,
                  "messages": [{"role": "user", "content": user_prompt}]},
            timeout=60
        )
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail=f"Anthropic API error {response.status_code}: {response.text[:600]}")
        data = response.json()
        text = "".join(b["text"] for b in data.get("content", []) if b.get("type") == "text")
        return {"report": text}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"D4 report error: {str(e)}")


# ─────────────────────────────────────────────────────────────────────────────
# D7 SAPTAMSHA REPORT ENDPOINT
# ─────────────────────────────────────────────────────────────────────────────

class D7ReportRequest(BaseModel):
    name: str
    gender: str = 'male'
    chart_brief: Dict[str, Any]

@app.post("/d7report")
def generate_d7_report(req: D7ReportRequest):
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not configured on server.")

    brief = req.chart_brief
    name  = req.name or "the native"
    gender = req.gender or brief.get('gender', 'male')
    pronoun = 'his' if gender == 'male' else 'her'
    pronoun_subj = 'he' if gender == 'male' else 'she'
    parent_role = 'father' if gender == 'male' else 'mother'

    system_prompt = f"""You are writing a focused lineage and progeny report for a Vedic astrology platform.
The native is a {gender} — use correct pronouns: {"he/his/him" if gender=="male" else "she/her/her"}.
Their parental role is {parent_role}. Always use "{parent_role}" — NEVER the opposite gender role.
Stay strictly on topic. Cover only: children, progeny potential, lineage quality, and the karmic nature of parent-child bonds.

Absolute rules:
1. Use ONLY the corpus provided. No external knowledge.
2. ZERO technical terminology — no planet names, house numbers, sign names, Sanskrit terms, ocean/deity names.
3. Second person throughout. "You will...", "Your children...", "Your lineage..."
4. CRITICAL: This native is a {parent_role}. Do NOT call them {"mother" if gender=="male" else "father"}.
5. Each section 5-7 sentences. No bullet points. Direct, specific prose.
6. NO personality analysis. NO career references. NO wealth commentary.
7. Write exactly 4 sections with these headings (use ### before each):
   ### Your Capacity for Children and Lineage
   ### The Nature and Character of Your Children
   ### Karmic Patterns and Challenges in Progeny
   ### Your Legacy and the Fruit of Your Lineage
8. Complete all 4 sections. Be specific about number of children where the data indicates."""

    stree_header = "STREE JATAK FEMALE PROGENY INDICATORS (additional classical rules for female nativity):"
    stree_data   = brief.get('stree_jatak_progeny', [])
    stree_section = (stree_header + "\n" + str(stree_data)) if gender == 'female' and stree_data else ''

    user_prompt = f"""Write a focused lineage and progeny report for {name} ({gender}).

LAGNA OCEAN (sets the parental archetype tone):
{brief.get('lagna_ocean', {})}

BIOLOGICAL VITALITY:
Self sphuta: {brief.get('self_sphuta', {})}
Biological flag: {brief.get('bio_flag', False)}

PROGENY SEQUENCE (Manduka Gati):
Sequence: {brief.get('progeny_sequence', [])}
Terminates after child: {brief.get('terminator_at', 'none detected')}
Eldest child health flag: {brief.get('eldest_health_flag', False)}
Adoption indicator: {brief.get('adoption_flag', False)}

SEVEN OCEANS — CHILD TEMPERAMENT PROFILE:
{brief.get('ocean_profile', [])}

KARMIC OBSTACLES (D7 6th/8th/12th):
{brief.get('dushtana', {})}

QUALITATIVE OVERRIDES:
{brief.get('overrides', [])}

{stree_section}

Write 4 focused sections on children, their nature, karmic challenges, and legacy. For female natives, integrate the Stree Jatak indicators. Be specific about numbers where data supports it."""

    try:
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
            json={"model": "claude-sonnet-4-6", "max_tokens": 2500, "system": system_prompt,
                  "messages": [{"role": "user", "content": user_prompt}]},
            timeout=60
        )
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail=f"Anthropic API error {response.status_code}: {response.text[:600]}")
        data = response.json()
        text = "".join(b["text"] for b in data.get("content", []) if b.get("type") == "text")
        return {"report": text}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"D7 report error: {str(e)}")


# ─────────────────────────────────────────────────────────────────────────────
# D9 NAVAMSHA SOUL REPORT ENDPOINT
# ─────────────────────────────────────────────────────────────────────────────

class D9ReportRequest(BaseModel):
    name: str
    chart_brief: Dict[str, Any]

@app.post("/d9report")
def generate_d9_report(req: D9ReportRequest):
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not configured on server.")

    brief = req.chart_brief
    name  = req.name or "the native"

    system_prompt = """You are writing a focused Navamsha (D9) soul and dharma report for a Vedic astrology platform.
Cover only: soul nature, dharmic purpose, spiritual gifts, karmic patterns, and inner life.

Absolute rules:
1. Use ONLY the corpus provided. No external knowledge.
2. ZERO technical terminology — no planet names, sign names, house numbers, Sanskrit terms, yoga names.
3. Second person throughout. "You are...", "Your soul..."
4. Each section 5-7 sentences. No bullet points. Flowing, specific prose.
5. This is NOT a personality report. Focus on the soul, dharma, inner life, and spiritual destiny.
6. Write exactly 5 sections with these headings (use ### before each):
   ### Your Soul's Signature and Dharmic Purpose
   ### Your Innate Gifts and Spiritual Talents
   ### Karmic Patterns and Shadow Work
   ### Your Spiritual Path and Divine Alignment
   ### Your Spouse and the Marital Bond
7. The spouse section covers: nature, personality, appearance, profession, marital quality. Be specific.
8. Complete all 5 sections. Do not truncate."""

    user_prompt = f"""Write a focused D9 Navamsha soul report for {name}.

SOUL DASHBOARD:
- Atmakaraka (King of Chart): {brief.get('ak', '—')}
- Swamsa (Soul Sign): {brief.get('swamsa_sign', '—')}
- Navamsha Lagna: {brief.get('d9_lagna', '—')}
- Ishta Devata (Guiding Deity): {brief.get('ishta_devata', '—')}
- Vargottama (Integrated) Planets: {brief.get('vargottama_planets', [])}
- Karmic Friction Score: {brief.get('karmic_friction', '—')}

SOUL NATURE (Swamsa Analysis):
{brief.get('swamsa_soul', [])}

INNATE TALENTS:
{brief.get('swamsa_talents', [])}

SPIRITUAL HOME ENVIRONMENT:
{brief.get('swamsa_residence', '')}

DHARMIC ORIENTATION:
{brief.get('swamsa_dharma', '')}

PLANETARY VITALS (nature and house):
{brief.get('vitals', [])}

KARMIC WARNINGS:
{brief.get('warnings', [])}

LIFE AREA NOTES:
Marriage: {brief.get('marriage_note', '')}
Career/Soul Work: {brief.get('career_note', '')}
Shadow Work: {brief.get('shadow_note', '')}

NOURISHED PLANETS (Pushkara): {brief.get('pushkara_planets', [])}
PLANETS REQUIRING PURIFICATION (Dusthana D9): {brief.get('dusthana_planets', [])}
ISHTA DEVATA for spiritual alignment: {brief.get('ishta_devata', '—')}

SPOUSE ANALYSIS:
Nature & Personality: {brief.get('spouse', {}).get('nature_list', [])}
Likely Profession: {brief.get('spouse', {}).get('profession', [])}
Marital Grace Factors: {brief.get('spouse', {}).get('marital_grace', [])}
Marital Friction Factors: {brief.get('spouse', {}).get('marital_friction', [])}
Stability Score: {brief.get('spouse', {}).get('stability', '—')}

Write 5 focused sections on soul nature, gifts, karmic patterns, and spiritual path. Deep, specific, no fluff."""

    try:
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
            json={"model": "claude-sonnet-4-6", "max_tokens": 2500, "system": system_prompt,
                  "messages": [{"role": "user", "content": user_prompt}]},
            timeout=60
        )
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail=f"Anthropic API error {response.status_code}: {response.text[:600]}")
        data = response.json()
        text = "".join(b["text"] for b in data.get("content", []) if b.get("type") == "text")
        return {"report": text}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"D9 report error: {str(e)}")


# ─────────────────────────────────────────────────────────────────────────────
# D10 DASHAMSHA CAREER REPORT ENDPOINT
# ─────────────────────────────────────────────────────────────────────────────

class D10ReportRequest(BaseModel):
    name: str
    chart_brief: Dict[str, Any]

@app.post("/d10report")
def generate_d10_report(req: D10ReportRequest):
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not configured on server.")

    brief = req.chart_brief
    name  = req.name or "the native"

    system_prompt = """You are writing a focused career and professional destiny report for a Vedic astrology platform.
Cover only: career identity, professional path, work environment, financial earning, and timing.

Absolute rules:
1. Use ONLY the corpus provided. No external knowledge.
2. ZERO technical terminology — no planet names, house numbers, sign names, Sanskrit terms, deity names.
3. Second person throughout. "You are...", "Your career..."
4. Each section 5-7 sentences. No bullet points. Flowing, specific prose.
5. NO personality analysis. NO relationship commentary. NO spiritual meandering.
6. Write exactly 4 sections with these headings (use ### before each):
   ### Your Professional Identity and Status
   ### Your Career Path and Working Style
   ### Financial Earning and Professional Environment
   ### Career Timing and Key Pivots
7. Complete all 4 sections. Be specific about professional tendencies, strengths, and challenges."""

    user_prompt = f"""Write a focused career report for {name}.

PROFESSIONAL IDENTITY:
- D10 Lagna: {brief.get('d10_lagna', '—')} — {brief.get('lagna_title', '')}
- Lagna description: {brief.get('lagna_desc', '')}
- Lagna deity quality: {brief.get('lagna_deity', {}).get('quality', '')}
- Lagna lord placement: House {brief.get('lagna_lord', {}).get('house', '?')} — Self-employed path: {brief.get('lagna_lord', {}).get('self_employed', False)}
- Sun (status): House {brief.get('sun', {}).get('house', '?')} — {brief.get('sun', {}).get('dignity', '')} — Ketu conflict: {brief.get('sun', {}).get('ketu_conflict', False)}

SOUL'S CAREER DESTINATION (AK):
{brief.get('ak', {})}

CAREER VEHICLE (AmK):
{brief.get('amk', {})}

AK/AmK INTERACTION: {brief.get('ak_amk_interaction', '')}

DEITY PROFILES (professional flavour per planetary force):
{brief.get('deity_profiles', [])}

HOUSE BREAKDOWN:
{brief.get('house_breakdown', [])}

MOOLTRIKONA (peak-drive planets): {brief.get('mooltrikona_planets', [])}
SUN/KETU CONFLICT: {brief.get('ketu_sun_conflict', False)}
10TH LORD PLACEMENT: House {brief.get('d1_10th_lord_d10_house', '?')} — Travel career: {brief.get('travel_career', False)}

FINANCIALS:
2nd house: {brief.get('h2', {})}
11th house: {brief.get('h11', {})}

Write 4 focused sections on career identity, path, financials, and timing. No fluff. Be specific."""

    try:
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
            json={"model": "claude-sonnet-4-6", "max_tokens": 2500, "system": system_prompt,
                  "messages": [{"role": "user", "content": user_prompt}]},
            timeout=60
        )
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail=f"Anthropic API error {response.status_code}: {response.text[:600]}")
        data = response.json()
        text = "".join(b["text"] for b in data.get("content", []) if b.get("type") == "text")
        return {"report": text}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"D10 report error: {str(e)}")


# ─────────────────────────────────────────────────────────────────────────────
# MEDICAL ASTROLOGY VAIDYA REPORT ENDPOINT
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/medreport")
def generate_med_report(req: dict):
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not configured on server.")

    name = req.get('name', 'the native')

    system_prompt = """You are a classical Vaidya (Ayurvedic physician) writing a health assessment report for a Vedic astrology platform.
Write as a knowledgeable, compassionate practitioner who reads the body's signals through the lens of Ayurvedic and classical Jyotisha principles.

Absolute rules:
1. Use ONLY the corpus provided. No external medical advice.
2. No planet names, house numbers, sign names, Sanskrit terms, or yoga names in the output.
3. Write in second person. "Your constitution...", "Your body..."
4. Each section 5-6 sentences. No bullet points. Warm, authoritative, clinical prose.
5. NEVER use fatalistic or alarming language. Frame everything as "predisposition," "tendency," or "area warranting attention."
6. End every section with a constructive, actionable note.
7. Write exactly 4 sections with these headings (use ### before each):
   ### Constitutional Assessment
   ### Areas of Physiological Attention
   ### The Current Season of Health
   ### Restorative Recommendations
8. Complete all 4 sections."""

    brief = req
    user_prompt = f"""Write a Vaidya's health assessment for {name}.

CONSTITUTION (Prakriti):
Vata: {brief.get('doshas', {}).get('Vata', {}).get('score', '?')}% — {brief.get('doshas', {}).get('Vata', {}).get('status', '?')}
Pitta: {brief.get('doshas', {}).get('Pitta', {}).get('score', '?')}% — {brief.get('doshas', {}).get('Pitta', {}).get('status', '?')}
Kapha: {brief.get('doshas', {}).get('Kapha', {}).get('score', '?')}% — {brief.get('doshas', {}).get('Kapha', {}).get('status', '?')}

VITALITY STATUS: {brief.get('core_vitality', '')}
Jupiter Escape (natural healing support): {brief.get('jupiter_escape', False)}

ANATOMICAL VULNERABILITIES:
{brief.get('vulnerabilities', [])}

SPECIFIC CONDITIONS FLAGGED:
Piles risk: {brief.get('medical_yogas', {}).get('piles', False)}
Cardiac risk: {brief.get('medical_yogas', {}).get('cardiac', False)}
Mental wellness: {brief.get('medical_yogas', {}).get('mental', False)}
Eye sensitivity: {brief.get('medical_yogas', {}).get('eye', False)}
Kidney sensitivity: {brief.get('medical_yogas', {}).get('kidney', False)}

CURRENT PERIOD HEALTH RISK:
{brief.get('dasha_risk', 'Not available')}

Write as a Vaidya. Warm, clinical, specific. No fatalism. No technical astrology terms."""

    try:
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
            json={"model": "claude-sonnet-4-6", "max_tokens": 2000, "system": system_prompt,
                  "messages": [{"role": "user", "content": user_prompt}]},
            timeout=60
        )
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail=f"Anthropic API error {response.status_code}: {response.text[:600]}")
        data = response.json()
        text = "".join(b["text"] for b in data.get("content", []) if b.get("type") == "text")
        return {"report": text}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Med report error: {str(e)}")


# ─────────────────────────────────────────────────────────────────────────────
# D12 DWADASHAMSHA REPORT ENDPOINT
# ─────────────────────────────────────────────────────────────────────────────

class D12ReportRequest(BaseModel):
    name: str
    chart_brief: Dict[str, Any]

@app.post("/d12report")
def generate_d12_report(req: D12ReportRequest):
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not configured on server.")

    brief = req.chart_brief
    name  = req.name or "the native"

    system_prompt = """You are writing a focused D12 Dwadashamsha report covering parents, ancestral karma, past-life imprints, and Moksha trajectory.

Absolute rules:
1. Use ONLY the corpus provided.
2. ZERO technical terminology — no planet names, house numbers, sign names, Sanskrit terms.
3. Second person. "Your relationship with your father...", "Your soul carries..."
4. Each section 5-7 sentences. No bullet points. Flowing, specific prose.
5. Write exactly 3 sections with these headings (use ### before each):
   ### Your Parental Legacy and Ancestral Bonds
   ### Your Past-Life Inheritance and Karmic Blueprint
   ### Your Path Toward Liberation and Release
6. Complete all 3 sections."""

    user_prompt = f"""Write a D12 Dwadashamsha essay report for {name}.

LAGNA DEITY: {brief.get('lagna_deity','')} (Hidden Name: {brief.get('lagna_hidden','')}) — {brief.get('lagna_meaning','')}
KARAKA LOGIC: {brief.get('karaka_logic','')}

FATHER (Sun & 9th House):
Sun: H{brief.get('sun',{}).get('house','?')} — {brief.get('sun',{}).get('dignity','')}
9th House lord: {brief.get('h9_lord','')} | Occupants: {brief.get('h9_occupants',[])}
Father Maraka indicators: {brief.get('father_maraka',[])}

MOTHER (Moon & 4th House):
Moon: H{brief.get('moon',{}).get('house','?')} — {brief.get('moon',{}).get('dignity','')}
4th House lord: {brief.get('h4_lord','')} | Occupants: {brief.get('h4_occupants',[])}
Mother Maraka indicators: {brief.get('mother_maraka',[])}

6TH HOUSE (Karmic Debt): Occupants: {brief.get('h6_occupants',[])} | Lord: {brief.get('h6_lord','')}

PAST-LIFE & MOKSHA INSIGHTS:
{brief.get('moksha_insights',[])}

VASANA IMPRINTS (Deity per planet):
{brief.get('vasanas',[])}

KARYA RASHI QUALITY:
{brief.get('karya_karakas',[])}

ACTIVE DASHA THEMES:
Parental: {brief.get('parental_theme','')}
Moksha: {brief.get('moksha_theme','')}

Write 3 focused essay sections. No astrology jargon. Specific, warm, insightful."""

    try:
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
            json={"model": "claude-sonnet-4-6", "max_tokens": 2000, "system": system_prompt,
                  "messages": [{"role": "user", "content": user_prompt}]},
            timeout=60
        )
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail=f"Anthropic API error {response.status_code}: {response.text[:600]}")
        data = response.json()
        text = "".join(b["text"] for b in data.get("content", []) if b.get("type") == "text")
        return {"report": text}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"D12 report error: {str(e)}")


# ─────────────────────────────────────────────────────────────────────────────
# D16 SHODASHAMSHA REPORT ENDPOINT
# ─────────────────────────────────────────────────────────────────────────────

class D16ReportRequest(BaseModel):
    name: str
    chart_brief: Dict[str, Any]

@app.post("/d16report")
def generate_d16_report(req: D16ReportRequest):
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not configured on server.")

    brief = req.chart_brief
    name  = req.name or "the native"

    system_prompt = """You are writing a focused D16 Shodashamsha report on vehicles, material happiness, and the mastery of lower nature.

Absolute rules:
1. Use ONLY the corpus provided.
2. ZERO technical terminology — no planet names, house numbers, sign names, Sanskrit terms.
3. Second person. "Your happiness...", "Your relationship with vehicles..."
4. Each section 5-6 sentences. No bullet points. Flowing, specific prose.
5. Focus strictly on: vehicles/transport, material comforts, happiness blueprint, mastery of primal impulses.
6. Write exactly 3 sections with these headings (use ### before each):
   ### Your Relationship with Vehicles and Material Comfort
   ### Your Happiness Blueprint and Inner Fulfilment
   ### The Mastery Task — Taming the Vahana
7. Complete all 3 sections."""

    user_prompt = f"""Write a D16 Shodashamsha report for {name}.

LAGNA DEITY: {brief.get('lagna_deity','')} — {brief.get('lagna_archetype','')}
VAHANA: {brief.get('lagna_vahana','')} — {brief.get('lagna_mastery_note','')}
MASTERY LEVEL: {brief.get('mastery_level','')} — {brief.get('mastery_desc','')}

VEHICLE PROFILE:
Preference: {brief.get('vehicle_profile',{}).get('pref','')}
Quality: {brief.get('vehicle_profile',{}).get('quality','')}
Maintenance: {brief.get('vehicle_profile',{}).get('maintenance','')}
Transformation: {brief.get('vehicle_profile',{}).get('transform','')}

KARMIC NODE FOCUS:
Location: H{brief.get('node_house','?')} in {brief.get('node_sign','')}
Management: {brief.get('node_management','')}
Node deity/vahana: {brief.get('node_deity','')} / {brief.get('node_vahana','')}

HAPPINESS KARAKAS:
Internal (Moon): H{brief.get('moon_happiness',{}).get('house','?')} — {brief.get('moon_happiness',{}).get('dignity','')} — Strong: {brief.get('moon_happiness',{}).get('strong',False)}
Material (Venus): H{brief.get('venus_luxury',{}).get('house','?')} — {brief.get('venus_luxury',{}).get('dignity','')} — Strong: {brief.get('venus_luxury',{}).get('strong',False)}
Moksha (Ketu): H{brief.get('ketu_moksha',{}).get('house','?')} — {brief.get('ketu_moksha',{}).get('dignity','')} — Strong: {brief.get('ketu_moksha',{}).get('strong',False)}

ELEMENTAL ALIGNMENT:
D1 Element: {brief.get('d1_element','')} | D16 Element: {brief.get('d16_element','')}
Conflict: {brief.get('elemental_conflict',False)}

Write 3 focused sections. No astrology jargon. Specific and grounded."""

    try:
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
            json={"model": "claude-sonnet-4-6", "max_tokens": 1800, "system": system_prompt,
                  "messages": [{"role": "user", "content": user_prompt}]},
            timeout=60
        )
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail=f"Anthropic API error {response.status_code}: {response.text[:600]}")
        data = response.json()
        text = "".join(b["text"] for b in data.get("content", []) if b.get("type") == "text")
        return {"report": text}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"D16 report error: {str(e)}")


# ─────────────────────────────────────────────────────────────────────────────
# D20 VIMSHAMSHA REPORT ENDPOINT
# ─────────────────────────────────────────────────────────────────────────────

class D20ReportRequest(BaseModel):
    name: str
    chart_brief: Dict[str, Any]

@app.post("/d20report")
def generate_d20_report(req: D20ReportRequest):
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not configured on server.")

    brief = req.chart_brief
    name  = req.name or "the native"

    system_prompt = """You are writing a focused D20 Vimshamsha spiritual potential report.
Cover only: spiritual capacity, worship path, karmic obstacles to spiritual growth, Moksha potential.

Absolute rules:
1. Use ONLY the corpus provided.
2. ZERO technical terminology — no planet names, house numbers, sign names, Sanskrit terms, deity names.
3. Second person. "Your spiritual path...", "Your capacity for worship..."
4. Each section 5-6 sentences. No bullet points. Flowing, contemplative prose.
5. This is a SPIRITUAL report — no career, relationships, or material commentary.
6. Write exactly 3 sections with these headings (use ### before each):
   ### Your Spiritual Foundation and Capacity for Grace
   ### The Karmic Knot — What Must Be Untied
   ### Your Path to Liberation
7. Complete all 3 sections."""

    user_prompt = f"""Write a D20 spiritual potential report for {name}.

LAGNA DEITY: {brief.get('lagna_deity','')} — {brief.get('lagna_deity_attr','')}
VARGESH DIGNITY: {brief.get('vargesh_dignity','')}

SPIRITUAL KARAKAS:
Jupiter (Grace): H{brief.get('jupiter',{}).get('house','?')} — {brief.get('jupiter',{}).get('dignity','')} — Strong: {brief.get('jupiter',{}).get('strong',False)}
Saturn (Karmic Debt): H{brief.get('saturn',{}).get('house','?')} — {brief.get('saturn',{}).get('dignity','')} — Ashtamamsha: {brief.get('saturn',{}).get('ashtamamsha',False)}
Ketu (Moksha): H{brief.get('ketu',{}).get('house','?')} — {brief.get('ketu',{}).get('dignity','')} — Strong: {brief.get('ketu',{}).get('strong',False)}

KARMIC KNOT (Rahu-Ketu):
Location: H{brief.get('node_house','?')} in {brief.get('node_sign','')}
Dominant node: {brief.get('dominant_node','')}
Entangled forces: {brief.get('node_conjuncts',[])}

STRESS FLAGS: {brief.get('stress_flags',[])}

KARYESHA FRAMEWORK: {brief.get('karyesha',[])}

PRIMARY WORSHIP PATH: {brief.get('primary_deity','')} — {brief.get('primary_deity_attr','')}
TRANSFORMATION PATH: {brief.get('trans_deity','')} — {brief.get('trans_deity_attr','')}

MOKSHA SURRENDER STATUS: {brief.get('moksha_surrender','')}

Write 3 focused sections. Contemplative, no jargon, specific to this soul's spiritual path."""

    try:
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
            json={"model": "claude-sonnet-4-6", "max_tokens": 1800, "system": system_prompt,
                  "messages": [{"role": "user", "content": user_prompt}]},
            timeout=60
        )
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail=f"Anthropic API error {response.status_code}: {response.text[:600]}")
        data = response.json()
        text = "".join(b["text"] for b in data.get("content", []) if b.get("type") == "text")
        return {"report": text}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"D20 report error: {str(e)}")


# ─────────────────────────────────────────────────────────────────────────────
# D24 SIDDHAMSHA REPORT ENDPOINT
# ─────────────────────────────────────────────────────────────────────────────

class D24ReportRequest(BaseModel):
    name: str
    chart_brief: Dict[str, Any]

@app.post("/d24report")
def generate_d24_report(req: D24ReportRequest):
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not configured on server.")

    brief = req.chart_brief
    name  = req.name or "the native"

    system_prompt = """You are writing a focused D24 Siddhamsha mastery and accomplishment report.
Cover only: learning style, fields of expertise, academic potential, professional mastery, and the path to Siddhi.

Absolute rules:
1. Use ONLY the corpus provided.
2. ZERO technical terminology — no planet names, house numbers, sign names, Sanskrit terms, deity names.
3. Second person. "Your mastery...", "Your field of expertise..."
4. Each section 5-6 sentences. No bullet points. Flowing, specific prose.
5. Focus on: what the person is built to master, how they learn, where they excel professionally.
6. Write exactly 3 sections with these headings (use ### before each):
   ### Your Learning Style and Mastery Path
   ### Your Fields of Expertise and Accomplishment
   ### Your Path to Siddhi — Perfection in Practice
7. Complete all 3 sections."""

    user_prompt = f"""Write a D24 mastery profile report for {name}.

PRIMARY MASTERY PATH: {brief.get('mastery_path','')} — {brief.get('mastery_desc','')}
KNOWLEDGE RETENTION: {brief.get('retention','')} — {brief.get('retention_desc','')}
PRIMARY KARYESHA: {brief.get('primary_karyesha',{})}
VARGOTTAMA PLANETS (2x multiplier): {brief.get('vargottama_planets',[])}

PRIMARY FIELD (Lagna Deity): {brief.get('lagna_deity','')}
- {brief.get('lagna_deity_field','')}
- {brief.get('lagna_deity_quality','')}

SECONDARY FIELD: {brief.get('secondary_deity','')} — {brief.get('secondary_field','')}

PROFESSIONAL APTITUDE (10th/11th planets): {brief.get('professional_aptitude',[])}

EIGHT SIDDHIS STATUS: {brief.get('siddhis',[])}

EDUCATION CONTINUITY: breaks={brief.get('break_flag',False)}
MONETISATION: {brief.get('monetisation','')}
ADVANCED RESEARCH: {brief.get('phd_potential','')}

NODE SHADOW (area of darkness to master): H{brief.get('node_house','?')} — {brief.get('node_sign','')}
TRANSFORMATION REQUIRED: {brief.get('transformation_required','')}

Write 3 focused sections. Specific about what this person is built to master and achieve."""

    try:
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
            json={"model": "claude-sonnet-4-6", "max_tokens": 1800, "system": system_prompt,
                  "messages": [{"role": "user", "content": user_prompt}]},
            timeout=60
        )
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail=f"Anthropic API error {response.status_code}: {response.text[:600]}")
        data = response.json()
        text = "".join(b["text"] for b in data.get("content", []) if b.get("type") == "text")
        return {"report": text}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"D24 report error: {str(e)}")


# ─────────────────────────────────────────────────────────────────────────────
# D27 BHAMSHA REPORT ENDPOINT
# ─────────────────────────────────────────────────────────────────────────────

class D27ReportRequest(BaseModel):
    name: str
    chart_brief: Dict[str, Any]

@app.post("/d27report")
def generate_d27_report(req: D27ReportRequest):
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not configured on server.")

    brief = req.chart_brief
    name  = req.name or "the native"

    system_prompt = """You are writing a focused D27 Bhamsha inner resilience and mental architecture report.
Cover only: mental strength, psychological patterns, inner grit, subconscious fears, and the capacity for right thinking.

Absolute rules:
1. Use ONLY the corpus provided.
2. ZERO technical terminology — no planet names, house numbers, sign names, Sanskrit terms, deity names.
3. Second person. "Your mind...", "Your inner resilience..."
4. Each section 5-6 sentences. No bullet points. Grounded, insightful prose — corrective rather than predictive.
5. Focus on: mental strengths, psychological patterns, specific fears, and actionable mental practices.
6. Write exactly 3 sections with these headings (use ### before each):
   ### Your Mental Architecture and Inner Grit
   ### The Shadow Rooms — Fears, Anxieties, and Letting Go
   ### The Right Thinking Protocol — Building Inner Resilience
7. Complete all 3 sections."""

    user_prompt = f"""Write a D27 inner resilience report for {name}.

OVERALL MENTAL RESILIENCE: {brief.get('overall_resilience','')}
GUIDING DEVATA: {brief.get('lagna_devata','')} — {brief.get('lagna_devata_attr','')}
INNER CHARACTERISTIC: {brief.get('lagna_inner','')}

MENTAL KARAKAS:
Moon (Mental Core): H{brief.get('moon',{}).get('house','?')} — {brief.get('moon',{}).get('dignity','')} — Weak: {brief.get('moon',{}).get('weak',False)}
Mars (Coping): H{brief.get('mars',{}).get('house','?')} — {brief.get('mars',{}).get('dignity','')}
Jupiter (Right Thinking): H{brief.get('jupiter',{}).get('house','?')} — {brief.get('jupiter',{}).get('dignity','')}

KARYA ANALYSIS:
3rd Lord ({brief.get('lord3',{}).get('planet','?')}): H{brief.get('lord3',{}).get('d27house','?')} — {brief.get('lord3',{}).get('dignity','')}
9th Lord ({brief.get('lord9',{}).get('planet','?')}): H{brief.get('lord9',{}).get('d27house','?')} — {brief.get('lord9',{}).get('dignity','')}

HOUSE PATTERNS:
4th (Peace of Mind): {brief.get('h4_peace','')}
6th (Adversity/Grit): {brief.get('h6_grit','')}
8th occupants: {brief.get('h8_occupants',[])}
12th occupants: {brief.get('h12_occupants',[])}

HIDDEN STRENGTH: {brief.get('hidden_strength',[])}
VARGOTTAMA RATING: {brief.get('vargo_rating','')}

Write 3 grounded, specific sections on mental architecture, shadow patterns, and the right thinking protocol."""

    try:
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
            json={"model": "claude-sonnet-4-6", "max_tokens": 1800, "system": system_prompt,
                  "messages": [{"role": "user", "content": user_prompt}]},
            timeout=60
        )
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail=f"Anthropic API error {response.status_code}: {response.text[:600]}")
        data = response.json()
        text = "".join(b["text"] for b in data.get("content", []) if b.get("type") == "text")
        return {"report": text}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"D27 report error: {str(e)}")


# ─────────────────────────────────────────────────────────────────────────────
# D30 TRIMSHAMSHA REPORT ENDPOINT
# ─────────────────────────────────────────────────────────────────────────────

class D30ReportRequest(BaseModel):
    name: str
    chart_brief: Dict[str, Any]

@app.post("/d30report")
def generate_d30_report(req: D30ReportRequest):
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not configured on server.")

    brief = req.chart_brief
    name  = req.name or "the native"

    system_prompt = """You are writing a focused D30 Trimshamsha karmic obstacles and inner enemies report.
Cover only: elemental imbalances, the six inner enemies (Shad Ripu), psychological patterns, karmic blocks, and remedial path.

Absolute rules:
1. Use ONLY the corpus provided.
2. ZERO technical terminology — no planet names, house numbers, sign names, Sanskrit terms, deity names, tattva names.
3. Second person. "Your inner fire...", "Your karmic pattern..."
4. Each section 5-6 sentences. No bullet points. Direct, corrective, honest prose.
5. NOT a personality report — focus on obstacles, enemies, patterns, and remediation.
6. Write exactly 3 sections with these headings (use ### before each):
   ### Your Elemental Imbalances and Primary Karmic Resistance
   ### The Six Inner Enemies — Which Are Active
   ### The Path of Resolution
7. Complete all 3 sections."""

    user_prompt = f"""Write a D30 karmic blueprint report for {name}.

GLOBAL STATUS: {brief.get('global_badge','')}
LAGNA: {brief.get('lagna_sign','')} — {brief.get('lagna_tattva','')} — {brief.get('lagna_deity','')}

ELEMENTAL BALANCE:
{brief.get('tattva_scores',{})}

ELEMENTAL CONFLICTS: {brief.get('elemental_conflicts',[])}

SATTVIK CONTROLLERS: {brief.get('controllers',[])}

SHAD RIPU (Inner Enemies):
{brief.get('shad_ripu',[])}

VARANASI PSYCHOLOGICAL INSIGHT:
Tithi: {brief.get('moon_tithi','')} — Group: {brief.get('moon_group','')}
{brief.get('varanasi_insight','')}

HOUSE OBSTACLES: {brief.get('house_obstacles',[])}

PRIMARY REMEDY: {brief.get('primary_remedy',{})}

Write 3 honest, corrective sections. Focus on patterns and what the person can do about them. No astrology jargon."""

    try:
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
            json={"model": "claude-sonnet-4-6", "max_tokens": 1800, "system": system_prompt,
                  "messages": [{"role": "user", "content": user_prompt}]},
            timeout=60
        )
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail=f"Anthropic API error {response.status_code}: {response.text[:600]}")
        data = response.json()
        text = "".join(b["text"] for b in data.get("content", []) if b.get("type") == "text")
        return {"report": text}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"D30 report error: {str(e)}")

class D40ReportRequest(BaseModel):
    name: str
    chart_brief: Dict[str, Any]

@app.post("/d40report")
def generate_d40_report(req: D40ReportRequest):
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not configured on server.")

    brief = req.chart_brief
    name  = req.name or "the native"

    system_prompt = """You are writing a focused D40 Chatviramshamsha maternal lineage karma report.
Cover only: quality of inherited knowledge and traditions, maternal lineage blessings and debts, domestic peace vs career balance, and the path to resolve ancestral karmic accounts.

Absolute rules:
1. Use ONLY the corpus data provided.
2. ZERO technical terminology — no planet names, house numbers, sign names, Sanskrit terms, deity names.
3. Second person. "Your maternal lineage...", "The inheritance you carry..."
4. Each section 5-6 sentences. No bullet points. Direct, specific, honest prose.
5. NOT a personality report — focus on lineage karma, ancestral patterns, and what the person can actively do.
6. Write exactly 3 sections with these headings (use ### before each):
   ### The Maternal Inheritance — What Was Passed Down
   ### Lineage Debts & Active Karmic Patterns
   ### Building Your Future — The Architect's Path
7. Complete all 3 sections."""

    user_prompt = f"""Write a D40 maternal lineage karma report for {name}.

D40 LAGNA: {brief.get('lagna_sign','')} — Deity: {brief.get('lagna_deity','')} ({brief.get('lagna_deity_role','')})
KARYA RASHI: {brief.get('karya_rashi','')} — KARYESHA: {brief.get('karyesha','')} ({brief.get('karyesha_dig','')})
LAGNA LORD: {brief.get('lagna_lord','')} ({brief.get('lagna_lord_dig','')})

LINEAGE KARAKA — MOON: {brief.get('moon_sign','')} ({brief.get('moon_dig','')})
MARS (Gateway/Drive): {brief.get('mars_d40',{})}
VENUS (Gateway/Grace): {brief.get('venus_d40',{})}
JUPITER (Guru/Architect): {brief.get('jupiter_d40',{})}

DOMINANT GUNA: {brief.get('dominant_guna','')}
GUNA DISTRIBUTION: {brief.get('guna_count',{})}

VARGOTTAMA PLANETS: {brief.get('vargottama',[])}

KNOWLEDGE BLOCKS (planetary): {brief.get('knowledge_blocks',[])}

4TH HOUSE (Domestic Peace): {brief.get('house_4',{})}
10TH HOUSE (Professional): {brief.get('house_10',{})}
WORK-LIFE STATUS: {brief.get('work_life_status','')}

RAHU HOUSE: {brief.get('rahu_house','')} — KETU HOUSE: {brief.get('ketu_house','')}

CURRENT DASHA: {brief.get('mahadasha','')} / {brief.get('antardasha','')}

Write 3 honest, specific sections about the maternal lineage karma and what the person can do to honour, heal, or build upon it. No astrology jargon."""

    try:
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
            json={"model": "claude-sonnet-4-6", "max_tokens": 1800, "system": system_prompt,
                  "messages": [{"role": "user", "content": user_prompt}]},
            timeout=60
        )
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail=f"Anthropic API error {response.status_code}: {response.text[:600]}")
        data = response.json()
        text = "".join(b["text"] for b in data.get("content", []) if b.get("type") == "text")
        return {"report": text}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"D40 report error: {str(e)}")

class D45ReportRequest(BaseModel):
    name: str
    chart_brief: Dict[str, Any]

@app.post("/d45report")
def generate_d45_report(req: D45ReportRequest):
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not configured on server.")

    brief = req.chart_brief
    name  = req.name or "the native"

    system_prompt = """You are writing a focused D45 Akshavedamsha paternal lineage karma report.
Cover only: paternal ancestral support, dharmic inheritance, Guru connection, ancestral debts, soul attachments, and the path to either sustain or transcend the paternal legacy.

Absolute rules:
1. Use ONLY the corpus data provided.
2. ZERO technical terminology — no planet names, house numbers, sign names, Sanskrit terms, deity names.
3. Second person. "Your paternal lineage...", "The wisdom you inherit..."
4. Each section 5-6 sentences. No bullet points. Direct, specific, honest prose.
5. NOT a personality report — focus on lineage karma, ancestral patterns, and actionable guidance.
6. Write exactly 3 sections with these headings (use ### before each):
   ### The Paternal Inheritance — Fire & Foundation
   ### Ancestral Debts, Nodal Shadows & The Guru Test
   ### The Path Forward — Sustaining or Forging the Legacy
7. Complete all 3 sections. If the Independence Protocol is active, make the 3rd section about building an independent legacy."""

    user_prompt = f"""Write a D45 paternal lineage karma report for {name}.

D45 LAGNA: {brief.get('lagna_sign','')} — Deity: {brief.get('lagna_deity','')} ({brief.get('lagna_archetype','')}) — Modality: {brief.get('lagna_modality','')}
AGNI ANCHOR: {'Active — fire principle intact' if brief.get('agni_anchor') else 'Anomalous — verify'}
AGNI STRENGTH: {'Strong — can burn away negativity' if brief.get('agni_strong') else 'Challenged — needs rekindling'}
INDEPENDENCE PROTOCOL: {'ACTIVE — forge own path' if brief.get('forge_flag') else 'Not active — sustain legacy'}

KARYA RASHI: {brief.get('karya_rashi','')} — KARYESHA: {brief.get('karyesha','')} ({brief.get('karyesha_dig','')})
LAGNA LORD: {brief.get('lagna_lord','')} ({brief.get('lagna_lord_dig','')})

SUN (Father): {brief.get('sun_d45',{})}
JUPITER (Exit Variable/Guru): {brief.get('jupiter_d45',{})}
ATMAKARAKA: {brief.get('atmakaraka',{})}
D1 NINTH LORD: {brief.get('d1_ninth_lord',{})}

NODAL AXIS: Rahu H{brief.get('rahu_house','—')} / Ketu H{brief.get('ketu_house','—')}
Node in Trikona: {brief.get('node_in_trikona',False)} — Node in 8th: {brief.get('node_in_8th',False)}
Shadowed planets: {brief.get('node_conjunct_planets',[])}

HOUSE 2 (Legacy): {brief.get('house_2',{})}
HOUSE 6 (Ancestral Debt): {brief.get('house_6',{})}
HOUSE 9 (Guru Blessing): {brief.get('house_9',{})}
HOUSE 11 (Self-Earning): {brief.get('house_11',{})}
HOUSE 12 (Attachments): {brief.get('house_12',{})}

VARGOTTAMA: {brief.get('vargottama',[])}
LINEAGE SUPPORT: {brief.get('lineage_support_pct','')}% / SELF EFFORT: {brief.get('self_effort_pct','')}%

CURRENT DASHA: {brief.get('mahadasha','')} / {brief.get('antardasha','')}

Write 3 honest, specific sections about paternal lineage karma. No astrology jargon."""

    try:
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
            json={"model": "claude-sonnet-4-6", "max_tokens": 1800, "system": system_prompt,
                  "messages": [{"role": "user", "content": user_prompt}]},
            timeout=60
        )
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail=f"Anthropic API error {response.status_code}: {response.text[:600]}")
        data = response.json()
        text = "".join(b["text"] for b in data.get("content", []) if b.get("type") == "text")
        return {"report": text}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"D45 report error: {str(e)}")

class D60ReportRequest(BaseModel):
    name: str
    chart_brief: Dict[str, Any]

@app.post("/d60report")
def generate_d60_report(req: D60ReportRequest):
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not configured on server.")

    brief = req.chart_brief
    name  = req.name or "the native"

    system_prompt = """You are writing a focused D60 Shashtiamsha deep karma and past-life report.
Cover only: the soul's inherited karmic foundation, what was spoiled or purified from past lives, active karmic triggers, the specific attachment that caused this rebirth, and the purification path.

Absolute rules:
1. Use ONLY the corpus data provided.
2. ZERO technical terminology — no planet names, house numbers, sign names, Sanskrit deity names, amsha numbers.
3. Second person. "Your soul carries...", "In a previous life..."
4. Each section 5-6 sentences. No bullet points. Direct, specific, honest prose.
5. This is a DEEP KARMA report — speak of past-life causes and their present-life effects. Be specific about what the karmic triggers mean for daily experience.
6. Write exactly 3 sections with these headings (use ### before each):
   ### The Karmic Foundation — What the Soul Inherited
   ### Active Triggers — What Past Lives Left Unresolved
   ### The Purification Path — How to Redress the Balance
7. Complete all 3 sections. If Kroora or a Cause of Rebirth trigger is active, name the past-life wound clearly."""

    user_prompt = f"""Write a D60 deep karma report for {name}.

D60 LAGNA: {brief.get('lagna_sign','')}
LAGNA DEITY: #{brief.get('lagna_deity_id','')} {brief.get('lagna_deity','')} ({brief.get('lagna_deity_nature','')})
LAGNA ESSENCE: {brief.get('lagna_deity_essence','')}

ATMAKARAKA: {brief.get('atmakaraka','')}
AK IN 12TH (Moksha Bond): {brief.get('ak_in_12th',False)}

CAUSE OF REBIRTH: {brief.get('cause_of_rebirth',False)} — Planet: {brief.get('cause_of_rebirth_planet','')}
DEEP SOUL ANXIETY: {brief.get('deep_soul_anxiety',False)} — Planet: {brief.get('anxiety_planet','')}
IMMENSE WEALTH MARKER: {brief.get('immense_wealth',False)}
EGO/AMBITION RISK PLANETS: {brief.get('ego_planets',[])}
HEALER SIGNATURE PLANETS: {brief.get('healer_planets',[])}
VENUS KANTAKA (Spousal Barb): {brief.get('venus_kantaka',False)}
LINEAGE BREAK: {brief.get('lineage_break',False)} — Planet: {brief.get('lineage_break_planet','')}
KING STATUS PLANETS: {brief.get('king_planets',[])}
KROORA (Rebirth Cause): {brief.get('kroora_planets',[])}

OVERALL EVOLUTION: {brief.get('overall_evolution','')}
IMPROVED PLANETS: {brief.get('improved_planets',[])}
SPOILED PLANETS: {brief.get('spoiled_planets',[])}

12TH HOUSE REBIRTH TETHERS: {brief.get('h12_planets',[])}

PLANETARY DEITIES (D60):
{brief.get('planetary_deities',{})}

CURRENT DASHA: {brief.get('mahadasha','')} / {brief.get('antardasha','')}
MD DEITY: {brief.get('md_deity','')} ({brief.get('md_deity_nature','')}) — Block Active: {brief.get('md_block',False)}
AD DEITY: {brief.get('ad_deity','')} ({brief.get('ad_deity_nature','')})

Write 3 honest, specific sections about past-life karma and how it manifests in the present life. No astrology jargon."""

    try:
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
            json={"model": "claude-sonnet-4-6", "max_tokens": 2000, "system": system_prompt,
                  "messages": [{"role": "user", "content": user_prompt}]},
            timeout=60
        )
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail=f"Anthropic API error {response.status_code}: {response.text[:600]}")
        data = response.json()
        text = "".join(b["text"] for b in data.get("content", []) if b.get("type") == "text")
        return {"report": text}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"D60 report error: {str(e)}")

class KarakReportRequest(BaseModel):
    name: str
    chart_brief: Dict[str, Any]

@app.post("/karakreport")
def generate_karak_report(req: KarakReportRequest):
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not configured on server.")

    brief = req.chart_brief
    name  = req.name or "the native"

    system_prompt = """You are writing a focused Karakamsha soul analysis report.
Cover only: the soul's primary desire and purpose (Atmakaraka), the karmic inheritance embedded in the Karakamsha sign, vocational expertise carried from past lives, how the soul's intent manifests through the Karakamsha Lagna in D1, the spiritual path and Ishta Devata, and the dasha timing verdict.

Absolute rules:
1. Use ONLY the corpus data provided.
2. ZERO technical terminology — no planet names, house numbers, sign names, Sanskrit terms.
3. Second person. "Your soul carries...", "The king of your chart..."
4. Each section 5-6 sentences. No bullet points. Direct, specific, honest prose.
5. This is a SOUL report — speak of deep purpose, inherited mastery, and karmic direction. Be specific.
6. Write exactly 3 sections with these headings (use ### before each):
   ### The Soul's Primary Desire — Who You Came Here to Be
   ### Inherited Mastery & Worldly Manifestation
   ### The Spiritual Path & Timing
7. Complete all 3 sections."""

    user_prompt = f"""Write a Karakamsha soul analysis for {name}.

ATMAKARAKA: {brief.get('atmakaraka','')} at {brief.get('ak_degree','')}° in {brief.get('ak_d1_sign','')}
KARAKAMSHA SIGN: {brief.get('karakamsha_sign','')}
SOUL FULFILLMENT: {brief.get('soul_fulfillment','')} (KA in H{brief.get('trikona_house_from_d9','')} from D9 Lagna — {'Trikona' if brief.get('in_trikona') else 'Non-Trikona'})

KA SIGN CORE: {brief.get('ka_core','')}
KA SIGN OCCUPANTS (D9): {brief.get('ka_occupants',[])}

AK CONJUNCTIONS IN D9: {brief.get('ak_conjuncts_d9',[])}

KL HOUSE SUMMARY (D1):
{brief.get('kl_house_summary',{})}

SPIRITUAL PATH:
Gatekeeper Deity: {brief.get('gatekeeper_deity','')}
Final Destination Deity: {brief.get('final_destination_deity','')}
Moksha Status: {brief.get('moksha_status','')}
Spiritual Expenditure: {brief.get('spend_type','')}

DASHA ALIGNMENT:
Current Dasha: {brief.get('mahadasha','')}
D1 Dignity: {brief.get('md_d1_dignity','')}
KL House: H{brief.get('md_kl_house','')}
Verdict: {brief.get('dasha_verdict','')}

Write 3 specific sections about the soul's purpose and path. No astrology jargon."""

    try:
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
            json={"model": "claude-sonnet-4-6", "max_tokens": 1800, "system": system_prompt,
                  "messages": [{"role": "user", "content": user_prompt}]},
            timeout=60
        )
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail=f"Anthropic API error {response.status_code}: {response.text[:600]}")
        data = response.json()
        text = "".join(b["text"] for b in data.get("content", []) if b.get("type") == "text")
        return {"report": text}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Karakamsha report error: {str(e)}")

class DashaReportRequest(BaseModel):
    name: str
    chart_brief: Dict[str, Any]

@app.post("/dashareport")
def generate_dasha_report(req: DashaReportRequest):
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not configured on server.")

    brief = req.chart_brief
    name  = req.name or "the native"

    system_prompt = """You are writing an Executive Dasha Report — a flowing narrative that synthesises pre-computed Vimshottari Dasha corpus keywords into actionable intelligence.

The brief already contains the corpus-matched results: dignity table results, house-specific outputs, AD-within-MD matrix results, Lajjitadi states, positional distance results, and the synthesis verdict. Your job is to weave these into elegant, specific prose.

Style: "The Monarch's Briefing" — authoritative, specific, elegant. No jargon. No bullet points. Second person.

Structure: Write exactly 2 sections using ### headings:

### Section A: The [Planet] Reign — [Era Title]
The Mahadasha overview. Use the md_dignity_result, md_house_ausp/inausp, md_disposition_result, md_lord_results, md_timing, and ausp_factors/inausp_factors to paint the full picture. Name specific corpus keywords naturally woven into prose. Reference the net_result verdict. 5-7 sentences.

### Section B: The [AD Planet] Chapter — [Subtitle]
The Antardasha layer. Use ad_within_md_strong or ad_within_md_weak (depending on ad_score), ad_dignity_result, ad_house_ausp/inausp, ad_disposition_result, and md_ad_pos_ausp/inausp. End with a specific actionable instruction referencing direction, material, or health_focus. 4-6 sentences.

Rules:
- Never say "according to the corpus" or "the data shows" or "the brief states"
- Use present tense throughout  
- Quote specific corpus phrases (e.g., "Royal Service," "Extreme Opulence," "Anorexia," "Fear of Water") naturally
- Be specific to THIS native's placements — not generic
- If net_result is Balanced, acknowledge both the promise and the friction"""

    user_prompt = f"""Write an Executive Dasha Report for {name}.

=== MAHADASHA: {brief.get('md_planet','')} ===
Sign: {brief.get('md_sign','')} | House: H{brief.get('md_house','')} | Dignity: {brief.get('md_dignity','')} | Potency: {brief.get('md_potency','')}%
Disposition: {brief.get('md_disposition','')} — {brief.get('md_disposition_result','')}
Dignity Result: {brief.get('md_dignity_result','')}
H{brief.get('md_house','')} Auspicious: {brief.get('md_house_ausp','')}
H{brief.get('md_house','')} Inauspicious: {brief.get('md_house_inausp','')}
House Lordships: H{brief.get('md_lord_houses',[])}
Lord Results (H placement): {brief.get('md_lord_results',[])}
Timing Pattern: {brief.get('md_timing','')} — {brief.get('md_timing_desc','')}
Lagnesh Mobility: {brief.get('md_lagnesh_mobility','')}
Lajjit State: {brief.get('md_lajjit','None')}
Kshudhit State: {brief.get('md_kshudhit','None')}
Badhaka Risk: {brief.get('md_badhaka',False)}
Progress: {brief.get('md_pct_elapsed','')}% elapsed · Ends {brief.get('md_end','')}

=== ANTARDASHA: {brief.get('ad_planet','')} ===
Sign: {brief.get('ad_sign','')} | House: H{brief.get('ad_house','')} | Dignity: {brief.get('ad_dignity','')} | Potency: {brief.get('ad_potency','')}%
Disposition: {brief.get('ad_disposition','')} — {brief.get('ad_disposition_result','')}
Dignity Result: {brief.get('ad_dignity_result','')}
H{brief.get('ad_house','')} Auspicious: {brief.get('ad_house_ausp','')}
H{brief.get('ad_house','')} Inauspicious: {brief.get('ad_house_inausp','')}
AD within MD (Strong): {brief.get('ad_within_md_strong','')}
AD within MD (Weak): {brief.get('ad_within_md_weak','')}
MD→AD Positional Distance (H{brief.get('md_ad_distance','')}): Ausp: {brief.get('md_ad_pos_ausp','')} | Inausp: {brief.get('md_ad_pos_inausp','')}
Days remaining: {brief.get('ad_days_remaining','')} · Ends {brief.get('ad_end','')}

=== SYNTHESIS ===
Auspicious Factors: {brief.get('ausp_factors',[])}
Inauspicious Factors: {brief.get('inausp_factors',[])}
Net Result: {brief.get('net_result','')}
Lagna: {brief.get('lagna_sign','')} | Lagnesh: {brief.get('lagnesh','')} | Badhaka H: {brief.get('badhaka_house','')}
Direction: {brief.get('md_direction','')} | Material: {brief.get('md_material','')} | Taste: {brief.get('md_taste','')}
Health Focus: {brief.get('health_focus','')}

Write the 2-section executive report now."""

    try:
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
            json={"model": "claude-sonnet-4-6", "max_tokens": 1200, "system": system_prompt,
                  "messages": [{"role": "user", "content": user_prompt}]},
            timeout=60
        )
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail=f"Anthropic API error {response.status_code}: {response.text[:600]}")
        data = response.json()
        text = "".join(b["text"] for b in data.get("content", []) if b.get("type") == "text")
        return {"report": text}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Dasha report error: {str(e)}")


# ── GOCHAR: CURRENT TRANSITS ENDPOINT ────────────────────────────────────────

@app.get("/transits")
def get_current_transits():
    """Return current planetary positions (sidereal, Lahiri) for Gochar computation."""
    import swisseph as swe
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    jd  = swe.julday(now.year, now.month, now.day,
                     now.hour + now.minute/60.0 + now.second/3600.0)
    swe.set_ephe_path('/tmp')

    # Lahiri ayanamsha (same formula as natal chart)
    T  = (jd - 2451545.0) / 36525.0
    ayan = 23.85 + 0.013004 * T

    BODIES = {
        'Sun': swe.SUN, 'Moon': swe.MOON, 'Mars': swe.MARS,
        'Mercury': swe.MERCURY, 'Jupiter': swe.JUPITER,
        'Venus': swe.VENUS, 'Saturn': swe.SATURN, 'Rahu': swe.MEAN_NODE
    }
    result = {}
    for name, body in BODIES.items():
        pos, _ = swe.calc_ut(jd, body)
        lon = (pos[0] - ayan) % 360
        if name == 'Rahu': lon = (pos[0] - ayan) % 360  # north node
        result[name] = {
            'longitude':  round(lon, 4),
            'sign_index': int(lon / 30),
            'nakshatra':  int(lon / (360/27)),
            'deg_in_sign': round(lon % 30, 4),
            'retrograde': bool(pos[3] < 0)
        }
    # Ketu = opposite of Rahu
    k_lon = (result['Rahu']['longitude'] + 180) % 360
    result['Ketu'] = {
        'longitude':  round(k_lon, 4),
        'sign_index': int(k_lon / 30),
        'nakshatra':  int(k_lon / (360/27)),
        'deg_in_sign': round(k_lon % 30, 4),
        'retrograde': False
    }
    # Moon-Sun difference for Tithi
    moon_lon = result['Moon']['longitude']
    sun_lon  = result['Sun']['longitude']
    diff     = (moon_lon - sun_lon) % 360
    tithi    = int(diff / 12) + 1  # 1–30
    weekday  = now.isoweekday() % 7 + 1  # Sun=1 … Sat=7
    return {
        'planets':  result,
        'tithi':    tithi,
        'weekday':  weekday,
        'jd':       round(jd, 4),
        'date_utc': now.strftime('%Y-%m-%d %H:%M UTC')
    }


# ── GOCHAR: REPORT NARRATIVE ENDPOINT ────────────────────────────────────────

class GocharReportRequest(BaseModel):
    name: str
    chart_brief: Dict[str, Any]

@app.post("/gochareport")
def generate_gochar_report(req: GocharReportRequest):
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not configured.")
    brief = req.chart_brief
    name  = req.name or "the native"

    system_prompt = """You are writing a Supreme Transit Audit — a precise, executive-level Gochar (transit) analysis.

Style: Strategic intelligence briefing. Authoritative. Second person. No bullet points inside paragraphs.

Write exactly 2 sections using ### headings:

### The Integrated Synthesis
One paragraph (5-7 sentences) covering: the harmony or conflict between the active Mahadasha/Antardasha and the current dominant transits. Apply dignity overrides. Name the primary theme of this window (e.g., "Industrial Investment," "Strategic Toil," "Mental Metamorphosis"). Reference Moorthy Nirnaya quality and Sade Sati phase if active. Weave in 1-2 specific upcoming dates from the Important Dates list to ground the analysis in time.

### The Execution Directive
One paragraph (4-5 sentences) with specific actionable guidance tied to the calendar. Reference specific dates from the Important Dates list — tell the native exactly when to act and when to hold back. Reference Masa Dasa timing, Dhina Phala energy, Anga Phala anatomical zone, and the 10th house meridian indicator. End with the single most important date the native should mark in their calendar and why.

Rules:
- Never say "according to the corpus" or "the data shows"
- Quote corpus keywords naturally (e.g., "Janma Sani," "Swarna Moorthy," "Chandhrashtama")
- Always reference specific dates from important_dates when available
- Be specific to THIS native's positions — not generic
- Use present tense throughout"""

    user_prompt = f"""Write a Supreme Transit Audit for {name}.

DASHA CONTEXT:
MD: {brief.get('md_planet','')} in H{brief.get('md_house','')} ({brief.get('md_dignity','')}) | AD: {brief.get('ad_planet','')} in H{brief.get('ad_house','')} ({brief.get('ad_dignity','')})

CURRENT TRANSITS (from Moon):
{brief.get('transit_summary','')}

SADE SATI: {brief.get('sade_sati_status','')}
MOORTHY NIRNAYA: Saturn={brief.get('saturn_moorthy','')}, Jupiter={brief.get('jupiter_moorthy','')}
TARA CYCLE: {brief.get('tara_status','')}

PRECISION TIMING:
Varsha Dasa Lord: {brief.get('varsha_lord','')} | Masa Dasa Lord: {brief.get('masa_lord','')} ({brief.get('masa_days','')} days)
Dhina Phala: {brief.get('dhina_phala','')} — {brief.get('dhina_result','')}

ANGA PHALA: {brief.get('anga_phala','')}
NAKSHATRA VEDHA: {brief.get('nak_vedha','')}
10TH HOUSE MERIDIAN: {brief.get('meridian_planet','')} — {brief.get('meridian_result','')}
WORST HOUSE ALERTS: {brief.get('worst_house_alerts','')}

IMPORTANT DATES (next 12 months — USE THESE IN THE NARRATIVE):
{brief.get('important_dates','No dates computed')}

LAGNA: {brief.get('lagna_sign','')} | RASI: {brief.get('rasi','')} | NAKSHATRA: {brief.get('nakshatra','')}

Write the 2-section Supreme Transit Audit now. Reference specific dates from Important Dates in both sections."""

    try:
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": api_key, "anthropic-version": "2023-06-01",
                     "content-type": "application/json"},
            json={"model": "claude-sonnet-4-6", "max_tokens": 1000,
                  "system": system_prompt,
                  "messages": [{"role": "user", "content": user_prompt}]},
            timeout=60
        )
        if response.status_code != 200:
            raise HTTPException(status_code=500,
                detail=f"Anthropic API error {response.status_code}: {response.text[:400]}")
        data = response.json()
        text = "".join(b["text"] for b in data.get("content",[]) if b.get("type")=="text")
        return {"report": text}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gochar report error: {str(e)}")


# ── REMEDIES REPORT ENDPOINT ──────────────────────────────────────────────────

class RemediesReportRequest(BaseModel):
    name: str
    chart_brief: Dict[str, Any]

@app.post("/remediesreport")
def generate_remedies_report(req: RemediesReportRequest):
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not configured.")
    brief = req.chart_brief
    name  = req.name or "the native"

    system_prompt = """You are writing the Detailed Remedial Analysis section of a Supreme Remedial Dossier.

Style: A learned Jyotishi speaking directly to the native. Warm but authoritative. Second person. No bullet points.

Write exactly 2 paragraphs with no headings:

Paragraph 1 (The Diagnosis): Explain WHY these specific remedies were prescribed. Reference the Atma Karaka planet and its condition, the active Dasha/Antardasha afflictions, and the natal weaknesses identified. Connect the Ishta Devata to the soul's evolutionary need. Use corpus keywords naturally (e.g., "Malefic Rule," "Elemental Sign Attribution," "43-day gestation").

Paragraph 2 (The Prescription Logic): Explain the priority order of the recommended remedies and why. Which remedy is the foundation (usually the primary gem or Rudraksha), which is the amplifier (Yantra/Mantra), and which is the daily anchor (Vrata/Color). End with a specific motivating statement about the karmic window currently open.

Rules:
- Never say "according to the corpus" or cite chapter numbers
- Be specific to THIS native's chart — not generic
- Maximum 150 words per paragraph
- Quote the selected Devta name naturally"""

    user_prompt = f"""Write the Detailed Remedial Analysis for {name}.

CHART FOUNDATION:
Lagna: {brief.get('lagna_sign','')} | Lagna Lord: {brief.get('lagna_lord','')} ({brief.get('lagna_lord_dignity','')} in H{brief.get('lagna_lord_house','')})
Atma Karaka: {brief.get('ak_planet','')} in {brief.get('ak_sign','')} H{brief.get('ak_house','')} ({brief.get('ak_dignity','')}
Moon: {brief.get('moon_sign','')} | Nakshatra: {brief.get('nakshatra','')}

DASHA CONTEXT:
MD: {brief.get('md_planet','')} ({brief.get('md_dignity','')}) | AD: {brief.get('ad_planet','')} ({brief.get('ad_dignity','')})

DEVTA PROFILE:
Ishta Devata: {brief.get('ishta_devata','')} (from {brief.get('ishta_planet','')} in 12th from Karakamsa)
Kula Devata: {brief.get('kula_devata','')}
Sthana Devata: {brief.get('sthana_devata','')}

PRIMARY AFFLICTIONS: {brief.get('primary_afflictions','')}

PRESCRIBED REMEDIES:
Primary Gem: {brief.get('primary_gem','')}
Rudraksha: {brief.get('rudraksha','')}
Primary Yantra: {brief.get('primary_yantra','')}
Primary Mantra: {brief.get('primary_mantra','')}
Primary Vrata: {brief.get('primary_vrata','')}
Nakshatra Tree: {brief.get('nak_tree','')}

Write the 2-paragraph Detailed Remedial Analysis now."""

    try:
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": api_key, "anthropic-version": "2023-06-01",
                     "content-type": "application/json"},
            json={"model": "claude-sonnet-4-6", "max_tokens": 800,
                  "system": system_prompt,
                  "messages": [{"role": "user", "content": user_prompt}]},
            timeout=60
        )
        if response.status_code != 200:
            raise HTTPException(status_code=500,
                detail=f"Anthropic API error {response.status_code}: {response.text[:400]}")
        data = response.json()
        text = "".join(b["text"] for b in data.get("content",[]) if b.get("type")=="text")
        return {"report": text}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Remedies report error: {str(e)}")


# ── NAKSHATRA BIRTHDAY ENDPOINT ───────────────────────────────────────────────

@app.get("/nakshatra_birthday")
def get_nakshatra_birthday(nak_index: int, birth_month: int, birth_day: int):
    """
    Find the next annual Nakshatra Birthday — the date the Moon transits
    the birth nakshatra closest to the native's birth calendar date this year.
    """
    import swisseph as swe
    from datetime import datetime, timezone, timedelta

    NAK_SPAN = 360 / 27  # 13.333...°

    def moon_nak(jd, ayan):
        pos, _ = swe.calc_ut(jd, swe.MOON)
        lon = (pos[0] - ayan) % 360
        return int(lon / NAK_SPAN), lon

    swe.set_ephe_path('/tmp')
    now = datetime.now(timezone.utc)
    jd_now = swe.julday(now.year, now.month, now.day, now.hour + now.minute/60.0)

    # Lahiri ayanamsha
    T = (jd_now - 2451545.0) / 36525.0
    ayan = 23.85 + 0.013004 * T

    # Scan forward day by day for up to 400 days — collect all occurrences of birth nakshatra
    occurrences = []
    prev_nak = None
    jd = jd_now
    for day in range(400):
        cur_nak, cur_lon = moon_nak(jd, ayan)
        # Detect entry into birth nakshatra
        if cur_nak == nak_index and prev_nak != nak_index:
            dt = datetime(now.year, 1, 1, tzinfo=timezone.utc) + timedelta(days=(jd - swe.julday(now.year, 1, 1, 0)))
            # More precise: reconstruct date from jd
            y, m, d, h = swe.revjul(jd)
            entry_date = datetime(int(y), int(m), int(d), tzinfo=timezone.utc)
            occurrences.append(entry_date)
        prev_nak = cur_nak
        jd += 1

    if not occurrences:
        return {"error": "Could not find nakshatra birthday"}

    # Among all occurrences, pick the one closest to the birth calendar date
    # Target: birth_month / birth_day in current or next year
    best = None
    best_diff = float('inf')
    for year_offset in [0, 1]:
        try:
            target = datetime(now.year + year_offset, birth_month, birth_day, tzinfo=timezone.utc)
        except ValueError:
            continue
        for occ in occurrences:
            diff = abs((occ - target).days)
            if diff < best_diff:
                best_diff = diff
                best = occ

    if not best:
        best = occurrences[0]
        best_diff = 0

    days_away = (best - now.replace(hour=0, minute=0, second=0, microsecond=0)).days

    return {
        "nakshatra_birthday": best.strftime("%d/%m/%Y"),
        "days_away": max(0, days_away),
        "weekday": best.strftime("%A"),
        "note": f"Moon transits your birth Nakshatra (#{nak_index+1}) nearest to your birth anniversary"
    }


# ═══════════════════════════════════════════════════════════════════════════════
# TAJIK VARSHAPHAL ENGINE — Neelakanthi System
# ═══════════════════════════════════════════════════════════════════════════════

SIGNS_LIST = ["Aries","Taurus","Gemini","Cancer","Leo","Virgo",
              "Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"]
SIGN_ABBR_LIST = ["Ar","Ta","Ge","Cn","Le","Vi","Li","Sc","Sg","Cp","Aq","Pi"]
SIGN_LORDS_LIST = ["Mars","Venus","Mercury","Moon","Sun","Mercury",
                   "Venus","Mars","Jupiter","Saturn","Saturn","Jupiter"]

# ── Harsha Bala constants ─────────────────────────────────────────────────────
TAJ_HARSHA_STHANA = {          # 0-indexed house number
    "Sun":8, "Moon":2, "Mars":5, "Mercury":0,
    "Jupiter":10, "Venus":4, "Saturn":11
}
TAJ_GENDER = {
    "Sun":"M","Moon":"F","Mars":"M","Mercury":"F",
    "Jupiter":"M","Venus":"F","Saturn":"F"
}
TAJ_FEMALE_HOUSES = {0,1,2,6,7,8}   # houses 1,2,3,7,8,9 (0-indexed)
TAJ_MALE_HOUSES   = {3,4,5,9,10,11} # houses 4,5,6,10,11,12 (0-indexed)

# ── Exaltation / Own signs for dignity (Tajik uses same as Parashari) ─────────
TAJ_EXALT = {"Sun":4,"Moon":1,"Mars":9,"Mercury":5,"Jupiter":3,
             "Venus":11,"Saturn":6,"Rahu":1,"Ketu":7}
TAJ_OWN   = {"Sun":[4],"Moon":[3],"Mars":[0,7],"Mercury":[2,5],
             "Jupiter":[8,11],"Venus":[1,6],"Saturn":[9,10]}

# ── Antardasa friendship matrix (Vamanacharya) ───────────────────────────────
TAJ_AD_FRIENDS = {
    "Sun":    ["Moon","Mars","Jupiter"],
    "Moon":   ["Mercury","Jupiter","Venus"],
    "Mars":   ["Sun","Moon"],
    "Mercury":["Saturn","Jupiter","Venus"],
    "Jupiter":["Sun","Moon","Mars"],
    "Venus":  ["Jupiter","Mercury","Saturn"],
    "Saturn": ["Jupiter","Venus","Mercury"],
}

# ── Year Lord results matrix ──────────────────────────────────────────────────
TAJ_VARSHESHA_RESULTS = {
    "Sun":{
        "strong":"Comforts from family and land, state honors, fame, victory over enemies.",
        "medium":"Loss of property, unsound health, fear of state action (unless in Ithesal with a benefic).",
        "weak":"Foreign travels, loss of wealth, laziness, sickness, disputes with parents."
    },
    "Moon":{
        "strong":"Wealth, marriage, birth of a son, new clothes, promotion.",
        "medium":"Benefits in proportion; if in Esrapha with a malefic, friends become enemies.",
        "weak":"Cold/cough, fear of enemies, serious illness (if in debility, death-like situation)."
    },
    "Mars":{
        "strong":"Victory, honors, wealth, comforts from family.",
        "medium":"Boils, skin eruptions, cuts from weapons or fights.",
        "weak":"Victim of thieves and fire, hurdles everywhere. Jupiter's aspect lessens these misfortunes."
    },
    "Mercury":{
        "strong":"Witty, educated, ministerial positions, elevation in rank.",
        "medium":"Journeys, business involvement, comfort from friends.",
        "weak":"Irreligious, loss of prestige, false witnesses, loss of friends and wealth."
    },
    "Jupiter":{
        "strong":"Happy family, trusted by others, fame, vanquishing enemies.",
        "medium":"Results modified by strength; if in Esrapha with malefics, suffers poverty and misery.",
        "weak":"Loss of wealth, ill luck, forsaken by family, victim of false allegations."
    },
    "Venus":{
        "strong":"Charming physique, luxury, costly jewels, victory over enemies.",
        "medium":"Modified benefits; keeps secrets and pains to self, barely makes ends meet.",
        "weak":"Agonies, loss of livelihood, family turns against the native."
    },
    "Saturn":{
        "strong":"Landed property from lower-level sources, respected by clan.",
        "medium":"Proportional benefits; fond of others' company.",
        "weak":"All-round troubles, obstacles, poor sustenance. Ithesal from benefics reduces ill effects."
    },
}

# ── Muntha house placement ────────────────────────────────────────────────────
TAJ_MUNTHA_HOUSE = {
    "auspicious":[8,9,10],    # 0-indexed: houses 9,10,11
    "neutral":[0,1,2,4],      # houses 1,2,3,5
    "inauspicious":[3,5,6,7,11], # houses 4,6,7,8,12
}

# ── 50 Saham formulas ─────────────────────────────────────────────────────────
# Format: (name, domain, A_key, B_key, C_key, reverse_at_night)
# Keys: "Sun","Moon","Mars","Mercury","Jupiter","Venus","Saturn","Lagna"
#       "LagnaLord","2ndCusp","9thCusp","11thCusp","2ndLord","9thLord","11thLord"
#       "Punya","Vidya","PunyaSaham" (computed), "YearLord"
TAJ_SAHAM_FORMULAS = [
    # Stage 2 — Foundation (must compute first)
    (1,  "Punya",       "Fortune",      "Moon",    "Sun",     "Lagna",    True),
    (2,  "Vidya",       "Learning",     "Sun",     "Moon",    "Lagna",    True),
    # Stage 3 — Standard
    (3,  "Yashas",      "Fame",         "Jupiter", "Punya",   "Lagna",    True),
    (4,  "Mitra",       "Friends",      "Jupiter", "Punya",   "Venus",    False),
    (5,  "Mahatmya",    "Greatness",    "Punya",   "Mars",    "Lagna",    True),
    (6,  "Asha",        "Hope",         "Saturn",  "Venus",   "Lagna",    True),
    (7,  "Samartha",    "Ability",      "Mars",    "LagnaLord","Lagna",   True),
    (8,  "Bhratru",     "Brothers",     "Jupiter", "Saturn",  "Lagna",    False),
    (9,  "Gaurava",     "Respect",      "Jupiter", "Moon",    "Sun",      True),
    (10, "Pitru",       "Father",       "Saturn",  "Sun",     "Lagna",    True),
    (11, "Rajya",       "Power",        "Saturn",  "Sun",     "Lagna",    True),
    (12, "Matru",       "Mother",       "Moon",    "Venus",   "Lagna",    True),
    (13, "Putra",       "Children",     "Jupiter", "Moon",    "Lagna",    True),
    (14, "Jeeva",       "Life",         "Saturn",  "Jupiter", "Lagna",    True),
    (15, "Karma",       "Action",       "Mars",    "Mercury", "Lagna",    True),
    (16, "Roga",        "Disease",      "Lagna",   "Moon",    "Lagna",    False),  # 2×Lagna - Moon
    (17, "Kali",        "Strife",       "Jupiter", "Mars",    "Lagna",    True),
    (18, "Mrityu",      "Death",        "8thCusp", "Moon",    "Saturn",   False),
    (19, "Vivaha",      "Marriage",     "Venus",   "Saturn",  "Lagna",    False),
    (20, "Vanic",       "Trade",        "Moon",    "Mercury", "Lagna",    False),
    (21, "Labha",       "Gain",         "11thCusp","11thLord","Lagna",    False),
    (22, "Shatru",      "Enemy",        "Mars",    "Saturn",  "Lagna",    True),
    (23, "Bandhu",      "Relatives",    "Mercury", "Moon",    "Lagna",    True),
    (24, "Artha",       "Wealth",       "2ndCusp", "2ndLord", "Lagna",    False),
    (25, "Paradesha",   "Foreign",      "9thCusp", "9thLord", "Lagna",    False),
    (26, "Punya2",      "Virtue",       "Venus",   "Moon",    "Lagna",    True),
    (27, "Kshama",      "Patience",     "Saturn",  "Jupiter", "Lagna",    True),
    (28, "Harsana",     "Joy",          "Jupiter", "Sun",     "Lagna",    True),
    (29, "Dainya",      "Misery",       "Saturn",  "Punya",   "Lagna",    True),
    (30, "Jada",        "Dullness",     "Mars",    "Saturn",  "Mercury",  False),
    (31, "Priti",       "Affection",    "Punya",   "Vidya",   "Lagna",    False),
    (32, "KaryaSiddhi", "Success",      "YearLord","Sun",     "Lagna",    True),
    (33, "Vivaha2",     "Marriage2",    "Saturn",  "Venus",   "Lagna",    True),
    (34, "Santapa",     "Grief",        "Saturn",  "Moon",    "Mars",     False),
    (35, "Shraddha",    "Devotion",     "Venus",   "Mars",    "Lagna",    True),
    (36, "Preeti",      "Love",         "Venus",   "Sun",     "Lagna",    True),
    (37, "Apasmar",     "Seizures",     "Moon",    "Mars",    "Lagna",    True),
    (38, "Shastra",     "Science",      "Jupiter", "Saturn",  "Mercury",  False),
    (39, "Bandhana",    "Confinement",  "Saturn",  "Moon",    "Lagna",    True),
    (40, "Adhomukha",   "Decline",      "Mars",    "Sun",     "Lagna",    True),
    (41, "Chatra",      "Royal Seal",   "Venus",   "Jupiter", "Lagna",    True),
    (42, "Vyapara",     "Business",     "Mars",    "Mercury", "Lagna",    True),
    (43, "Satya",       "Truth",        "Venus",   "Moon",    "Jupiter",  False),
    (44, "Abhimana",    "Pride",        "Mars",    "Jupiter", "Lagna",    True),
    (45, "Sama",        "Equanimity",   "Moon",    "Jupiter", "Lagna",    False),
    (46, "Yartra",      "Journey",      "9thCusp", "9thLord", "Lagna",    False),
    (47, "Kutumba",     "Family",       "Jupiter", "Moon",    "Lagna",    False),
    (48, "Arthotsaha",  "Zeal",         "Venus",   "Sun",     "Lagna",    False),
    (49, "Koushalya",   "Skill",        "Mercury", "Moon",    "Lagna",    False),
    (50, "Pramoda",     "Delight",      "Moon",    "Venus",   "Lagna",    True),
]


# ── Helper: get sidereal longitude of Shripati house cusp ────────────────────
def calc_shripati_cusps(jd: float, lat: float, lon: float) -> list:
    """Alcabitius (Shripati) house cusps, returned as sidereal longitudes."""
    cusps, _ = swe.houses(jd, lat, lon, b'B')
    ayan = get_lahiri_ayanamsha(jd)
    return [(c - ayan) % 360.0 for c in cusps]  # 12 values, 0-indexed


# ── Solar return finder ───────────────────────────────────────────────────────
def find_solar_return(natal_sun_sid: float, target_year: int,
                      lat: float, lon: float) -> dict:
    """Binary-search for exact JD when Sun returns to natal sidereal longitude."""
    jd_start = swe.julday(target_year, 1, 1, 0.0)
    prev_diff = None
    jd_bracket = None

    for d in range(370):
        jd = jd_start + d
        sun_trop = swe.calc_ut(jd, swe.SUN)[0][0]
        sun_sid  = (sun_trop - get_lahiri_ayanamsha(jd)) % 360.0
        diff = (sun_sid - natal_sun_sid + 360) % 360
        if diff > 180: diff -= 360
        if prev_diff is not None and prev_diff < 0 and diff >= 0:
            jd_bracket = (jd - 1, jd)
            break
        prev_diff = diff

    if not jd_bracket:
        return {}

    jd_lo, jd_hi = jd_bracket
    for _ in range(60):
        jd_mid = (jd_lo + jd_hi) / 2
        sun_sid = (swe.calc_ut(jd_mid, swe.SUN)[0][0] - get_lahiri_ayanamsha(jd_mid)) % 360.0
        diff = (sun_sid - natal_sun_sid + 360) % 360
        if diff > 180: diff -= 360
        if diff < 0: jd_lo = jd_mid
        else:         jd_hi = jd_mid

    jd_sr = (jd_lo + jd_hi) / 2
    y, m, d, h = swe.revjul(jd_sr)
    hour_int = int(h); minute_int = int((h - hour_int) * 60)

    # Day/Night: simple hour check (local solar noon = 12h)
    # Approximate sunrise/sunset at ±6h from noon
    is_day = 6.0 <= h <= 18.0

    return {
        "jd": jd_sr,
        "year": int(y), "month": int(m), "day": int(d),
        "hour": hour_int, "minute": minute_int,
        "is_day": is_day,
    }


# ── Harsha Bala ───────────────────────────────────────────────────────────────
def calc_harsha_bala(planet: str, sign_index: int, house_0idx: int,
                     dignity_score: int, is_day: bool) -> dict:
    """4 criteria × 5 Biswas each, capped at 20. Rahu/Ketu return 0."""
    if planet in ("Rahu", "Ketu"):
        return {"biswas": 0, "tier": "Excluded", "criteria": []}

    biswas = 0; criteria = []

    # 1. Own/Exaltation (score ≥ 3 means Own=3 or Exalted=5)
    if dignity_score >= 3:
        biswas += 5; criteria.append("Own/Exaltation")

    # 2. Specific Harshasthana
    if house_0idx == TAJ_HARSHA_STHANA.get(planet, -1):
        biswas += 5; criteria.append(f"Harshasthana (H{house_0idx+1})")

    # 3. Temporal strength
    g = TAJ_GENDER.get(planet, "M")
    if (g == "M" and is_day) or (g == "F" and not is_day):
        biswas += 5; criteria.append("Temporal strength")

    # 4. Positional group
    if g == "F" and house_0idx in TAJ_FEMALE_HOUSES:
        biswas += 5; criteria.append("Positional (Female houses)")
    elif g == "M" and house_0idx in TAJ_MALE_HOUSES:
        biswas += 5; criteria.append("Positional (Male houses)")

    biswas = min(biswas, 20)
    tier = ("Very Strong" if biswas >= 15 else
            "Medium"      if biswas >= 10 else
            "Weak"        if biswas >= 5  else "Very Weak")
    return {"biswas": biswas, "tier": tier, "criteria": criteria}


# ── Single Saham computation ──────────────────────────────────────────────────
def compute_saham(A: float, B: float, C: float,
                  lagna_lon: float, is_day: bool, reverse: bool) -> float:
    """A - B + C with 30° correction. Reverses A/B for night if reverse=True."""
    if not is_day and reverse:
        A, B = B, A
    result = (A - B + C) % 360.0

    # 30° rule: Lagna NOT in arc from B → A → add 30°
    arc_B_A = (A - B + 360) % 360
    arc_B_L = (lagna_lon - B + 360) % 360
    if arc_B_L >= arc_B_A:
        result = (result + 30.0) % 360.0

    return round(result, 4)


# ── All 50 Sahams ─────────────────────────────────────────────────────────────
def calc_all_sahams(planets: dict, lagna_lon: float, cusps: list,
                    is_day: bool, lagna_si: int) -> list:
    """Compute all 50 Sahams. Returns list of dicts."""

    def plon(name):
        return planets.get(name, {}).get("longitude", 0.0)

    def lon_to_house(lon):
        si = int(lon / 30) % 12
        # Whole Sign house from Lagna
        return ((si - lagna_si + 12) % 12) + 1

    def cusp_lon(n):  # n = 1-based cusp index
        return cusps[n - 1] if cusps and len(cusps) >= n else 0.0

    def lord_of_cusp(n):
        si = int(cusp_lon(n) / 30) % 12
        return SIGN_LORDS_LIST[si]

    results = []
    computed = {}  # Cache computed Sahams for dependent formulas

    # Varshesha lon — use strongest Harsha Bala planet (placeholder: Sun if unknown)
    yl_name = planets.get("_varshesha", "Sun")
    year_lord_lon = plon(yl_name)

    def get_lon(key):
        mapping = {
            "Sun": plon("Sun"), "Moon": plon("Moon"), "Mars": plon("Mars"),
            "Mercury": plon("Mercury"), "Jupiter": plon("Jupiter"),
            "Venus": plon("Venus"), "Saturn": plon("Saturn"),
            "Lagna": lagna_lon,
            "LagnaLord": plon(SIGN_LORDS_LIST[lagna_si]),
            "2ndCusp":  cusp_lon(2),  "2ndLord":  plon(lord_of_cusp(2)),
            "9thCusp":  cusp_lon(9),  "9thLord":  plon(lord_of_cusp(9)),
            "11thCusp": cusp_lon(11), "11thLord": plon(lord_of_cusp(11)),
            "8thCusp":  cusp_lon(8),
            "Punya":    computed.get("Punya", 0.0),
            "Vidya":    computed.get("Vidya", 0.0),
            "YearLord": year_lord_lon,
        }
        return mapping.get(key, 0.0)

    for (num, name, domain, A_key, B_key, C_key, rev) in TAJ_SAHAM_FORMULAS:
        A = get_lon(A_key); B = get_lon(B_key); C = get_lon(C_key)
        lon = compute_saham(A, B, C, lagna_lon, is_day, rev)
        si  = int(lon / 30) % 12
        house = lon_to_house(lon)
        computed[name] = lon  # Cache for dependents

        results.append({
            "number": num,
            "name": name,
            "domain": domain,
            "longitude": lon,
            "sign": SIGNS_LIST[si],
            "sign_index": si,
            "house": house,
        })

    return results


# ── Patyayini Dasha ───────────────────────────────────────────────────────────
def calc_patyayini_dasha(planets: dict, lagna_lon: float,
                         muntha_lon: float, varshesha_lon: float) -> dict:
    """
    Sort 10 entities by Krissamsa (degree within sign), compute Patyamsas,
    derive K and Dasha days (365.25-day year).
    """
    PLANET_KEYS = ["Sun","Moon","Mars","Mercury","Jupiter","Venus","Saturn"]

    entities = []
    for p in PLANET_KEYS:
        lon = planets.get(p, {}).get("longitude", 0.0)
        krissamsa = lon % 30.0
        entities.append({"name": p, "longitude": lon, "krissamsa": krissamsa})

    entities.append({"name": "Lagna",      "longitude": lagna_lon,    "krissamsa": lagna_lon % 30.0})
    entities.append({"name": "Muntha",     "longitude": muntha_lon,   "krissamsa": muntha_lon % 30.0})
    entities.append({"name": "Varshesha",  "longitude": varshesha_lon,"krissamsa": varshesha_lon % 30.0})

    # Sort ascending by Krissamsa
    entities.sort(key=lambda x: x["krissamsa"])

    # Patyamsas
    for i, e in enumerate(entities):
        if i == 0:
            e["patyamsa"] = e["krissamsa"]
        else:
            e["patyamsa"] = entities[i]["krissamsa"] - entities[i-1]["krissamsa"]

    total_pat = sum(e["patyamsa"] for e in entities)
    K = 365.25 / total_pat if total_pat > 0 else 1.0

    for e in entities:
        e["dasha_days"] = round(e["patyamsa"] * K, 2)

    return {
        "entities": entities,
        "total_patyamsa": round(total_pat, 4),
        "K": round(K, 4),
    }


# ── Varshesha (Year Lord) selection — 5-contestant simplified ─────────────────
def select_varshesha(annual_lagna_si: int, muntha_si: int,
                     planets: dict, is_day: bool,
                     harsha_bala: dict) -> str:
    """
    5 contestants: Annual Lagna Lord, Muntha Lord, Tri-Rasi Lord,
    Strongest Harsha Bala planet, Day/Night Lord.
    Returns name of planet with highest Harsha Bala among contestants.
    """
    contestants = set()
    contestants.add(SIGN_LORDS_LIST[annual_lagna_si])   # 1. Annual Lagna Lord
    contestants.add(SIGN_LORDS_LIST[muntha_si])          # 2. Muntha Lord

    # 3. Tri-Rasi Lord: day = Sun sign lord, night = Moon sign lord
    sun_si  = int(planets.get("Sun",  {}).get("longitude", 0) / 30) % 12
    moon_si = int(planets.get("Moon", {}).get("longitude", 0) / 30) % 12
    contestants.add(SIGN_LORDS_LIST[sun_si] if is_day else SIGN_LORDS_LIST[moon_si])

    # 4. Strongest Harsha Bala planet
    best_planet = max(
        [p for p in harsha_bala if p not in ("Rahu","Ketu")],
        key=lambda p: harsha_bala[p]["biswas"]
    )
    contestants.add(best_planet)

    # 5. Day Lord (Sun) / Night Lord (Moon) directly
    contestants.add("Sun" if is_day else "Moon")

    # Winner = highest Harsha Bala among contestants
    winner = max(contestants, key=lambda p: harsha_bala.get(p, {}).get("biswas", 0))
    return winner



# ── Tajik Aspect & Ithesal/Esrapha Engine ─────────────────────────────────────
# Corpus: Neelakanthi — orb-gated aspects, Ithesal/Esrapha, Nakta, Yamaya

# Deeptamsha mean orbs (degrees)
TAJ_DEEPTAMSHA = {
    "Sun": 15, "Moon": 12, "Mars": 8, "Mercury": 7,
    "Jupiter": 9, "Venus": 7, "Saturn": 9
}

def tajik_combined_orb(p1: str, p2: str) -> float:
    return (TAJ_DEEPTAMSHA.get(p1, 9) + TAJ_DEEPTAMSHA.get(p2, 9)) / 2.0

# Aspect table: house distance → (name, strength%, nature)
TAJ_ASPECTS = {
    1:  ("Pratyaksha Shatru", 100, "Openly Inimical"),
    7:  ("Pratyaksha Shatru", 100, "Openly Inimical"),
    5:  ("Trikona Mitra",      75, "Openly Friendly"),
    9:  ("Trikona Mitra",      75, "Openly Friendly"),
    4:  ("Gupta Shatru",       75, "Secretly Inimical"),
    10: ("Gupta Shatru",       75, "Secretly Inimical"),
    3:  ("Gupta Mitra",        40, "Secretly Friendly"),
    11: ("Gupta Mitra",        10, "Secretly Friendly"),
    # 2, 6, 8, 12 → 0% — no functional aspect
}

# Speed tier: lower = faster
TAJ_SPEED_TIER = {
    "Moon": 1, "Mercury": 2, "Venus": 3, "Sun": 4,
    "Mars": 5, "Jupiter": 6, "Saturn": 7
}

# Natural friendship (Neelakanthi)
TAJ_FRIENDS = {
    "Sun":     ["Moon", "Mars", "Jupiter"],
    "Moon":    ["Sun", "Mercury"],
    "Mars":    ["Sun", "Moon", "Jupiter"],
    "Mercury": ["Sun", "Venus"],
    "Jupiter": ["Sun", "Moon", "Mars"],
    "Venus":   ["Mercury", "Saturn"],
    "Saturn":  ["Mercury", "Venus"],
}
TAJ_ENEMIES = {
    "Sun":     ["Venus", "Saturn"],
    "Moon":    [],
    "Mars":    ["Mercury"],
    "Mercury": ["Moon"],
    "Jupiter": ["Mercury", "Venus"],
    "Venus":   ["Sun", "Moon"],
    "Saturn":  ["Sun", "Moon", "Mars"],
}

def tajik_natural_friendship(p1: str, p2: str) -> str:
    if p2 in TAJ_FRIENDS.get(p1, []) and p1 in TAJ_FRIENDS.get(p2, []):
        return "Friend"
    if p2 in TAJ_ENEMIES.get(p1, []) or p1 in TAJ_ENEMIES.get(p2, []):
        return "Enemy"
    return "Neutral"

# ── Core: Orb-gated aspect + Ithesal/Esrapha between any two planets ──────────
def _tajik_aspect_between(name_a: str, lon_a: float,
                           name_b: str, lon_b: float) -> dict:
    """
    Step A: Effective_Orb = (Orb_A + Orb_B) / 2
    Step B: Diff = |lon_A - lon_B| (shortest arc, 0-180)
    Step C: deviation = min(Diff % 30, 30 - Diff % 30) — distance from exact aspect
    Rule: if Diff > Effective_Orb → Wide, yoga does NOT fire.
    """
    # Step B: angular distance (shortest arc)
    diff = abs(lon_a - lon_b)
    if diff > 180:
        diff = 360 - diff

    # Step C: deviation from nearest exact 30° interval
    remainder  = diff % 30
    deviation  = min(remainder, 30 - remainder)

    # Step A: effective orb
    eff_orb = tajik_combined_orb(name_a, name_b)

    # Determine aspect house from nearest multiple of 30
    nearest_mult = round(diff / 30)
    if nearest_mult == 0:
        nearest_mult = 1   # conjunct = 1st house
    house_num = nearest_mult if nearest_mult <= 12 else 12

    aspect_data = TAJ_ASPECTS.get(house_num)

    if deviation > eff_orb:
        # Wide — deviation from exact aspect exceeds combined Deeptamsha orb
        return {
            "within_orb":    False,
            "diff":          round(diff, 2),
            "deviation":     round(deviation, 2),
            "effective_orb": round(eff_orb, 2),
            "aspect_house":  house_num,
            "aspect_name":   aspect_data[0] if aspect_data else "No functional aspect",
            "yoga":          f"Wide (deviation {deviation:.1f}° > orb {eff_orb:.1f}°) — Yoga does NOT fire",
        }

    if not aspect_data:
        # Within range but non-functional house (2, 6, 8, 12)
        return {
            "within_orb":    False,
            "diff":          round(diff, 2),
            "deviation":     round(deviation, 2),
            "effective_orb": round(eff_orb, 2),
            "aspect_house":  house_num,
            "aspect_name":   "No functional aspect",
            "yoga":          "Non-functional house — no Tajik aspect",
        }

    # Functional aspect within orb — determine Ithesal/Esrapha
    aspect_name, aspect_pct, aspect_nature = aspect_data

    tier_a = TAJ_SPEED_TIER.get(name_a, 4)
    tier_b = TAJ_SPEED_TIER.get(name_b, 4)
    if tier_a <= tier_b:
        faster_name, faster_lon = name_a, lon_a
        slower_name, slower_lon = name_b, lon_b
    else:
        faster_name, faster_lon = name_b, lon_b
        slower_name, slower_lon = name_a, lon_a

    ithesal  = faster_lon < slower_lon   # faster is chasing (lower lon = behind)
    vartaman = deviation <= 1.0

    return {
        "within_orb":    True,
        "diff":          round(diff, 2),
        "deviation":     round(deviation, 2),
        "effective_orb": round(eff_orb, 2),
        "aspect_house":  house_num,
        "aspect_name":   aspect_name,
        "aspect_pct":    aspect_pct,
        "aspect_nature": aspect_nature,
        "faster_planet": faster_name,
        "slower_planet": slower_name,
        "ithesal":       ithesal,
        "vartaman":      vartaman,
        "yoga":          ("Ithesal" if ithesal else "Esrapha")
                         + (" — Vartaman (peak, within 1°)" if vartaman else ""),
    }


# ── Nakta Yoga: fast bridge ────────────────────────────────────────────────────
def _check_nakta(name_v: str, lon_v: float,
                 name_m: str, lon_m: float,
                 all_planets: dict) -> dict:
    """
    Nakta: Energy flow A (Faster) → Bridge (Fastest) → B (Slower)
    Longitude order MUST be: lon_A < bridge_lon < lon_B
    Bridge sits between A and B — chasing B while A chases Bridge.
    If Bridge has already passed B (bridge_lon > lon_B), the bridge is broken.
    """
    tier_v = TAJ_SPEED_TIER.get(name_v, 4)
    tier_m = TAJ_SPEED_TIER.get(name_m, 4)

    # Identify A (faster of the two) and B (slower)
    if tier_v <= tier_m:
        name_a, lon_a, name_b, lon_b = name_v, lon_v, name_m, lon_m
    else:
        name_a, lon_a, name_b, lon_b = name_m, lon_m, name_v, lon_v

    for bridge in ["Moon", "Mercury", "Venus", "Sun"]:
        if bridge in (name_v, name_m):
            continue
        bridge_tier = TAJ_SPEED_TIER.get(bridge, 4)
        if bridge_tier >= tier_v or bridge_tier >= tier_m:
            continue  # bridge must be faster than BOTH A and B

        bridge_lon = all_planets.get(bridge, {}).get("longitude")
        if bridge_lon is None:
            continue

        # Longitude sequence: lon_A < bridge_lon < lon_B
        # Bridge is ahead of A (A chasing Bridge) and behind B (Bridge chasing B)
        if not (lon_a < bridge_lon < lon_b):
            continue

        # Orb check: A within Deeptamsha of Bridge, Bridge within Deeptamsha of B
        asp_a_bridge = _tajik_aspect_between(name_a, lon_a, bridge, bridge_lon)
        asp_bridge_b = _tajik_aspect_between(bridge, bridge_lon, name_b, lon_b)

        if asp_a_bridge.get("within_orb") and asp_bridge_b.get("within_orb"):
            return {
                "type":         "Nakta",
                "intermediary": bridge,
                "description": (
                    f"Nakta Yoga — {bridge} sits between {name_a} (lon {lon_a:.1f}°) "
                    f"and {name_b} (lon {lon_b:.1f}°), with bridge at {bridge_lon:.1f}°. "
                    f"{name_a} is chasing {bridge}; {bridge} is chasing {name_b}. "
                    f"Direct cooperation between Year Lord and Muntha Lord is absent, "
                    f"but {bridge} acts as a living bridge — results come through a "
                    f"third party, intermediary, or unexpected facilitator."
                ),
                "a_to_bridge": asp_a_bridge,
                "bridge_to_b": asp_bridge_b,
            }
    return {}


# ── Yamaya Yoga: slow bridge ───────────────────────────────────────────────────
def _check_yamaya(name_v: str, lon_v: float,
                  name_m: str, lon_m: float,
                  all_planets: dict) -> dict:
    """
    Yamaya: Energy flow A (Faster) → Bridge (Slowest) ← B (Faster)
    Both primary planets at LOWER longitudes than Bridge — both converging on it.
    Longitude requirement: lon_V < bridge_lon AND lon_M < bridge_lon
    """
    tier_v = TAJ_SPEED_TIER.get(name_v, 4)
    tier_m = TAJ_SPEED_TIER.get(name_m, 4)

    for bridge in ["Saturn", "Jupiter", "Mars"]:
        if bridge in (name_v, name_m):
            continue
        bridge_tier = TAJ_SPEED_TIER.get(bridge, 5)
        if bridge_tier <= tier_v or bridge_tier <= tier_m:
            continue  # bridge must be slower than BOTH V and M

        bridge_lon = all_planets.get(bridge, {}).get("longitude")
        if bridge_lon is None:
            continue

        # Both primary planets must be at lower longitudes — converging on Bridge
        if not (lon_v < bridge_lon and lon_m < bridge_lon):
            continue

        # Orb check: both V and M within Deeptamsha of Bridge
        asp_v_bridge = _tajik_aspect_between(name_v, lon_v, bridge, bridge_lon)
        asp_m_bridge = _tajik_aspect_between(name_m, lon_m, bridge, bridge_lon)

        if asp_v_bridge.get("within_orb") and asp_m_bridge.get("within_orb"):
            return {
                "type":         "Yamaya",
                "intermediary": bridge,
                "description": (
                    f"Yamaya Yoga — both {name_v} (lon {lon_v:.1f}°) and {name_m} "
                    f"(lon {lon_m:.1f}°) are converging on {bridge} (lon {bridge_lon:.1f}°), "
                    f"which is slower than both and ahead of both in longitude. "
                    f"Success is mediated by an authority figure, institution, or external "
                    f"structure that binds both interests — not through direct action."
                ),
                "varshesha_to_bridge": asp_v_bridge,
                "munthesh_to_bridge":  asp_m_bridge,
            }
    return {}


# ── Master function ────────────────────────────────────────────────────────────
def compute_tajik_varshesha_munthesh(
    varshesha_name: str, varshesha_lon: float, varshesha_speed: float,
    munthesh_name:  str, munthesh_lon:  float, munthesh_speed:  float,
    all_planets: dict = None
) -> dict:
    """
    Priority:
    1. Direct aspect + orb check (Deeptamsha gate)
    2. If no direct active yoga → Nakta (fast bridge)
    3. If no Nakta → Yamaya (slow bridge)
    """
    friendship = tajik_natural_friendship(varshesha_name, munthesh_name)

    direct = _tajik_aspect_between(varshesha_name, varshesha_lon,
                                   munthesh_name,  munthesh_lon)

    intermediary = {}
    ithesal       = None
    vartaman      = False
    within_orb    = direct.get("within_orb", False)
    aspect_house  = direct.get("aspect_house")
    aspect_name   = direct.get("aspect_name", "No aspect")
    aspect_pct    = direct.get("aspect_pct", 0)
    aspect_nature = direct.get("aspect_nature", "Neutral")
    harmony       = "Neutral"

    if within_orb:
        ithesal  = direct["ithesal"]
        vartaman = direct["vartaman"]
        faster   = direct["faster_planet"]
        slower   = direct["slower_planet"]
        yoga_trigger = (
            f"{'Ithesal (Applying — building)' if ithesal else 'Esrapha (Separating — waning)'}: "
            f"{faster} is at {'lower' if ithesal else 'higher'} longitude — "
            f"{'chasing and will catch up' if ithesal else 'already passed the meeting point'}. "
            f"Angular diff {direct['diff']:.1f}° within orb {direct['effective_orb']:.1f}°."
            + (" Vartaman — peak 1° orb." if vartaman else "")
        )
        harmony = (
            "Harmonious" if (ithesal and "Friendly" in aspect_nature)  else
            "Friction"   if (ithesal and "Inimical" in aspect_nature)  else
            "Waning"     if (not ithesal and "Friendly" in aspect_nature) else
            "Tense"
        )
    else:
        yoga_trigger = direct.get("yoga", "No active yoga between Year Lord and Muntha Lord.")
        # Orb filter blocked or no functional aspect — try intermediaries
        if all_planets:
            intermediary = _check_nakta(varshesha_name, varshesha_lon,
                                        munthesh_name,  munthesh_lon, all_planets)
            if not intermediary:
                intermediary = _check_yamaya(varshesha_name, varshesha_lon,
                                             munthesh_name,  munthesh_lon, all_planets)
            if intermediary:
                yoga_trigger = intermediary["description"]
                harmony      = "Mediated"

    # Vartaman determination
    vartaman_active = within_orb and vartaman
    vartaman_label  = "TRUE — Impending and Certain (within 1° orb)" if vartaman_active else "FALSE — Standard Ithesal (effort required)" if (within_orb and ithesal) else "FALSE"

    relationship_header = (
        f"Varshesha: {varshesha_name} | Munthesh: {munthesh_name}\n"
        f"Distance: {aspect_house or 'N/A'} houses — {aspect_name} ({aspect_pct}% strength, {aspect_nature})\n"
        f"Yoga Trigger: {yoga_trigger}\n"
        f"Vartaman: {vartaman_label}\n"
        f"Natural Status: {varshesha_name} and {munthesh_name} are Natural {friendship}s."
        + (f"\nIntermediary Yoga: {intermediary.get('type')} via {intermediary.get('intermediary')}"
           if intermediary else "")
    )

    return {
        "varshesha":           varshesha_name,
        "munthesh":            munthesh_name,
        "aspect_house":        aspect_house,
        "aspect_name":         aspect_name,
        "aspect_strength_pct": aspect_pct,
        "aspect_nature":       aspect_nature,
        "within_orb":          within_orb,
        "ithesal":             ithesal,
        "vartaman":            vartaman,
        "friendship":          friendship,
        "harmony":             harmony,
        "intermediary":        intermediary or None,
        "relationship_header": relationship_header,
    }



# ── Request model ─────────────────────────────────────────────────────────────
class VarshaChartRequest(BaseModel):
    natal_chart:     Dict[str, Any]
    target_year:     int
    current_lat:     float
    current_lon:     float
    use_birth_place: bool = False


@app.post("/varsha_chart")
def get_varsha_chart(req: VarshaChartRequest):
    """Tajik Varsha Kundali — solar return chart + full Tajik analysis."""
    try:
        nc             = req.natal_chart
        planets_natal  = nc.get("planets", {})
        birth_lat      = float(nc.get("input", {}).get("lat",  28.6))
        birth_lon      = float(nc.get("input", {}).get("lon",  77.2))
        birth_year     = int(nc.get("input", {}).get("date", "1990-01-01").split("-")[0])
        birth_lagna_si = int(nc.get("lagna", {}).get("sign_index", 0))
        natal_sun_sid  = float(planets_natal.get("Sun", {}).get("longitude", 0.0))
        lat = birth_lat if req.use_birth_place else req.current_lat
        lon = birth_lon if req.use_birth_place else req.current_lon

        sr = find_solar_return(natal_sun_sid, req.target_year, lat, lon)
        if not sr:
            raise HTTPException(status_code=400, detail="Solar return not found for target year")
        jd_sr  = sr["jd"]
        is_day = sr["is_day"]

        annual_lagna    = calc_lagna(jd_sr, lat, lon)
        annual_lagna_si = annual_lagna["sign_index"]
        lagna_lon       = annual_lagna["longitude"]
        annual_planets  = calc_all_planets(jd_sr, annual_lagna_si)

        cusps = calc_shripati_cusps(jd_sr, lat, lon)
        cusps_out = [{"cusp": i+1, "longitude": round(c,4),
                      "sign": SIGNS_LIST[int(c/30)%12],
                      "degree": round(c%30,4)} for i,c in enumerate(cusps)]

        completed_years = req.target_year - birth_year
        muntha_si    = (birth_lagna_si + completed_years) % 12
        muntha_deg   = (annual_lagna["degree"] * 2) / 5
        muntha_lon   = muntha_si * 30.0 + muntha_deg
        muntha_house = ((muntha_si - annual_lagna_si + 12) % 12) + 1
        muntha_status = ("auspicious"   if muntha_house in [9,10,11] else
                         "neutral"      if muntha_house in [1,2,3,5]  else
                         "inauspicious")
        muntha_out = {"sign_index": muntha_si, "sign": SIGNS_LIST[muntha_si],
                      "degree": round(muntha_deg,4), "longitude": round(muntha_lon,4),
                      "house": muntha_house, "status": muntha_status}

        harsha_bala = {}
        for p in ["Sun","Moon","Mars","Mercury","Jupiter","Venus","Saturn"]:
            pd     = annual_planets.get(p, {})
            score  = (pd.get("dignity",{}).get("score",0)
                      if isinstance(pd.get("dignity"),dict) else 0)
            house0 = (pd.get("sign_index",0) - annual_lagna_si + 12) % 12
            harsha_bala[p] = calc_harsha_bala(p, pd.get("sign_index",0), house0, score, is_day)

        varshesha_name  = select_varshesha(annual_lagna_si, muntha_si,
                                            annual_planets, is_day, harsha_bala)
        varshesha_lon   = annual_planets.get(varshesha_name,{}).get("longitude",0.0)
        varshesha_speed = annual_planets.get(varshesha_name,{}).get("speed",1.0)
        varshesha_hb    = harsha_bala.get(varshesha_name,{})
        varshesha_tier  = varshesha_hb.get("tier","Weak")
        varshesha_result = TAJ_VARSHESHA_RESULTS.get(varshesha_name,{}).get(
            "strong" if varshesha_tier=="Very Strong" else
            "medium" if varshesha_tier=="Medium" else "weak","")

        munthesh_name  = SIGN_LORDS_LIST[muntha_si]
        munthesh_lon   = annual_planets.get(munthesh_name,{}).get("longitude",0.0)
        munthesh_speed = annual_planets.get(munthesh_name,{}).get("speed",1.0)
        vm_aspect = compute_tajik_varshesha_munthesh(
            varshesha_name, varshesha_lon, varshesha_speed,
            munthesh_name,  munthesh_lon,  munthesh_speed,
            all_planets=annual_planets)

        annual_planets["_varshesha"] = varshesha_name
        sahams = calc_all_sahams(annual_planets, lagna_lon, cusps, is_day, annual_lagna_si)
        dasha  = calc_patyayini_dasha(annual_planets, lagna_lon, muntha_lon, varshesha_lon)

        return {
            "solar_return":    sr,
            "completed_years": completed_years,
            "target_year":     req.target_year,
            "location":        {"lat":lat,"lon":lon,"use_birth_place":req.use_birth_place},
            "lagna":           annual_lagna,
            "planets":         annual_planets,
            "shripati_cusps":  cusps_out,
            "muntha":          muntha_out,
            "munthesh":        munthesh_name,
            "harsha_bala":     harsha_bala,
            "varshesha":       {"planet":varshesha_name,"longitude":round(varshesha_lon,4),
                                "harsha_biswas":varshesha_hb.get("biswas",0),
                                "tier":varshesha_tier,"result":varshesha_result},
            "varshesha_munthesh_aspect": vm_aspect,
            "sahams":          sahams,
            "patyayini_dasha": dasha,
            "is_day":          is_day,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Varsha chart error: {str(e)}")


# VARSHA PHALA REPORT ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

class VarshaReportRequest(BaseModel):
    varsha_brief: Dict[str, Any]
    natal_brief:  Dict[str, Any]
    report_type:  str = "narrative"

@app.post("/varshareport")
def get_varsha_report(req: VarshaReportRequest):
    """AI narrative reports for Tajik Varshaphal modules."""
    try:
        vb = req.varsha_brief
        nb = req.natal_brief
        rt = req.report_type

        vm_header = vb.get("varshesha_munthesh_aspect", {}).get("relationship_header",
                    vb.get("vm_aspect", "Not computed"))

        prompts = {
            "narrative": f"""You are a Tajik Neelakanthi Varshaphal expert. Write ONLY the narrative section of an annual report.

Annual Data: {json.dumps(vb, indent=2)}
Natal Context: {json.dumps(nb, indent=2)}

MASTER KEY — Varshesha-Munthesh Relationship:
{vm_header}

The Varshesha (Year Lord) governs the year's RESULTS. The Munthesh (Muntha Lord) governs the year's EVOLUTION and KARMIC FOCUS. Their aspect relationship determines whether these two forces work in harmony or against each other. You MUST open the Narrative Arc with this relationship — name both planets, the aspect type, whether it is building (Ithesal/Applying) or waning (Esrapha/Separating), the natural friendship status, and what this means for the native in plain, vivid language. This is not optional. If Vartaman is TRUE, use definite, certain language ('This year, X will...'). If Vartaman is FALSE but Ithesal, use effort-conditional language ('Through consistent effort, X can...'). If Esrapha, acknowledge the waning energy plainly. If an Intermediary Yoga (Nakta/Yamaya) is present, lead with it as the defining mechanism of the year.

Write EXACTLY these 3 paragraphs in plain English (no Sanskrit jargon, no technical terms):

**The Narrative Arc:**
Open with the Varshesha-Munthesh relationship. Then weave in: the Year Lord archetype, the Muntha house domain, and the specific opportunity or friction this creates. 3-4 sentences total.

**The Challenge & The Shield:**
Name the specific risk area and the specific protective planet/placement. If the aspect is Esrapha or hostile, acknowledge the internal friction plainly. 2-3 sentences.

**The Subconscious Echo:**
1-2 sentences. Translate the dietary indicator and dream theme into modern lifestyle language.

Write only these 3 paragraphs with bold headers. Plain English throughout.""",

            "vivaha": f"""You are a Tajik Neelakanthi Varshaphal expert writing a detailed annual relationship and union forecast.

Data: {json.dumps(vb, indent=2)}
Natal Context: {json.dumps(nb, indent=2)}

Write EXACTLY these 3 sections in plain English (bold headers, no Sanskrit jargon, no generic filler):

CRITICAL FLAGS FROM DATA:
- Saham Lord Combust: {vb.get('saham_lord_combust', False)}
- Dasa Conflict: {vb.get('dasa_conflict', 'FALSE')}

If Saham Lord is combust (TRUE above), you MUST note this in the Narrative Arc: the timing window opens but the planet governing it is weakened by the Sun's proximity. Use language like "the window activates but the planet governing it is dimmed — events may occur but with complications or need for extra effort."

**The Narrative Arc:**
3-4 sentences. State which house the Vivaha Saham falls in and what this means for partnership energy this year. The EXACT timing window is {vb.get('timing_calendar_month', 'unknown')} — use this specific month name in the narrative (e.g. 'September 2026 is your peak window') (Central/Active/Submerged). Name the relationship between the Annual Lagna Lord and the 7th Lord (friendly/hostile/neutral) and what practical outcome this creates. If a specific month window is active (based on Patyayini Dasha), name it with a concrete prediction.

**The Harmony & Friction:**
2-3 sentences. Based on Venus's Biswas score and the 7th house occupants, describe the actual emotional climate of partnerships this year. Name any specific planetary combination that creates friction (e.g. Mars near the Saham, Saturn in 7th) and any protective factor (Jupiter aspect, strong Venus) that nullifies or mitigates it. Be direct and specific.

**The Protection Note & Tactical Advice:**
2-3 sentences. State the single best month or window for a wedding, proposal, or major relationship commitment this year. State the single period to avoid (if any) due to Mars/Saturn influence on the 7th or Saham. End with one pithy, practical sentence based on the Year Lord's energy.""",

            "artha": f"""You are a Tajik Neelakanthi Varshaphal expert writing an annual wealth and commerce report.

Data: {json.dumps(vb, indent=2)}
Natal Context: {json.dumps(nb, indent=2)}

STRICT PLANETARY ROLE MAP (do not deviate — use this to name planets in the narrative):
{vb.get('role_map', 'See data above')}

Write EXACTLY these 3 sections in plain English (bold headers, no Sanskrit jargon):

**The Narrative Arc:**
3-4 sentences. State clearly whether this is a year of active wealth generation, consolidation, or caution. Name the specific house of the Artha Saham and what this means practically for income and assets. Reference the 2nd Lord relationship with the Lagna Lord. If a peak window month is in the data, name it with a concrete financial prediction. If the Indra Shield is active, name it as a specific protective force.

**The Commercial Strategy:**
2-3 sentences. Based on the Vyapara Saham and the planets influencing the 10th house, name the specific commercial activity favoured this year (trade, writing, contracts, real estate, state work, etc.). State whether the year's energy flows toward or away from financial gains based on the Ithesal/Esrapha status. Be direct about the commercial outlook.

**The Protective Note:**
2-3 sentences. Address the Kartari risk if present. End with one tactical sentence: the single most important financial action for this year based on the chart.""",

            "putra": f"""You are a Tajik Neelakanthi Varshaphal expert writing an annual progeny, fortune, and creative growth report.

Data: {json.dumps(vb, indent=2)}
Natal Context: {json.dumps(nb, indent=2)}

STRICT ROLE MAP: {vb.get('role_map', 'See data')}
PUNYA-YEAR LORD CONNECTION: {vb.get('punya_year_lord_bridge', 'Not applicable')}

Write EXACTLY these 3 sections in plain English (bold headers, no jargon):

**The Narrative Arc:**
3-4 sentences. State the Putra Saham house and what it means for children or creative projects this year. Name the 5th Lord and Lagna Lord relationship (friendly/inimical) and what this produces practically. If the natal promise gate is Confirmed, state it. Name the specific peak Punya window month from the data.

**The Creative & Parental Strategy:**
2-3 sentences. Based on the 5th house occupants and Jupiter's strength, name the specific focus — is this a year for actual child-related events, creative projects, or educational endeavours? If the Abortion Alert is active (retrograde Mars in 5th), state it plainly. Reference the Ithesal/Esrapha status of the 5th Lord.

**The Merit & Protection Note:**
2-3 sentences. If the Punya Shield is active (Punya Saham aspected by benefics in 5th), name it as a specific fortunate force. Address any educational warning (afflicted Mercury). End with one tactical sentence for the year.""",

            "arishta": f"""You are a Tajik Varshaphal analyst. Assess risk combinations for this annual chart.

Chart Data: {json.dumps(vb, indent=2)}

Scan for: Lagna Lord Armor and Jupiterian Grace cancellations, Muntha afflictions, 8th Lord combinations, and Rajya Yoga Bhanga conditions.

Output a structured risk report with 3 sections, each labelled GREEN (protected), AMBER (monitor), or RED (flagged). Each flag must cite the specific planetary combination in plain language. 300 words maximum.""",

            "saham": f"""You are a Tajik Saham analyst (Neelakanthi system).

Data: {json.dumps(vb, indent=2)}

Analyse the 4 featured Sahams (Vivaha, Artha, Putra, Mrityu). For each: state its house and sign placement, whether it is activated (auspicious houses: 1/5/9/10/11), and what it concretely predicts for this year. 300 words total. Plain English.""",

            "muntha": f"""You are a Tajik Muntha analyst (Neelakanthi system).

Muntha Data: {json.dumps(vb.get('muntha', {}), indent=2)}
Annual Context: {json.dumps(vb, indent=2)}

Write 250 words on: Muntha house status, Rahu-Muntha mouth/back protocol if applicable (Mouth 0-10° = auspicious, Back 20-30° = caution), timing of manifestation (early vs late year based on natal vs annual benefic aspects), and the year's karmic focus in plain language.""",
        }

        prompt = prompts.get(rt, prompts["narrative"])

        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            },
            json={
                "model": "claude-sonnet-4-6",
                "max_tokens": 2000,
                "messages": [{"role": "user", "content": prompt}]
            },
            timeout=90
        )
        if response.status_code != 200:
            raise HTTPException(
                status_code=500,
                detail=f"Anthropic API error {response.status_code}: {response.text[:400]}"
            )
        data = response.json()
        text = "".join(b["text"] for b in data.get("content", []) if b.get("type") == "text")
        return {"report": text}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Varsha report error: {str(e)}")


# ═══════════════════════════════════════════════════════════════════════════════
# MAAS PHALA ENGINE — Monthly Resolution
# ═══════════════════════════════════════════════════════════════════════════════

LUNAR_STATES = [
    '', 'Pravaas (Journey/Travel)', 'Nashta (Excess Expenditure)',
    'Maran (Death-like Fear)', 'Jaya (Victory)', 'Haasya (Joy & Laughter)',
    'Rati (Satisfaction)', 'Kreeda (Sports & Fun)', 'Prasupta (Inactivity)',
    'Bhukta (Fear & Pain)', 'Jwara (Fever & Illness)', 'Kampita (Sorrows & Loss)',
    'Susthita (Comfort & Joy)'
]

DREAM_THEMES = {
    "Sun":     "Red objects, fire, intense light, authority figures",
    "Moon":    "Water, white cloth, silver, beautiful landscapes, peace",
    "Mars":    "Combat, red stones, weapons, blood, high energy pursuits",
    "Mercury": "Flying, horse riding, books, intellectual discussions",
    "Jupiter": "Temples, elders, children, abundance, divine figures",
    "Venus":   "Rivers, flowers, romantic encounters, beautiful music",
    "Saturn":  "Dark spaces, crowds of strangers, slow journeys, old structures",
    "Rahu":    "Serpents, fog, confusion, underground spaces",
    "Ketu":    "Flags, fire, spiritual figures, detachment",
}

def find_maas_entry_for_month(natal_sun_sid: float, calendar_month: int,
                               calendar_year: int, lat: float, lon: float) -> dict:
    """
    Find the Maas Pravesha that falls within the requested calendar month.
    Strategy:
      1. Compute Sun's sidereal longitude at mid-month.
      2. Find which natal_sun + n*30° is nearest to mid-month Sun position.
      3. Binary-search for exact crossing of that longitude within the month.
    """
    import calendar as cal_mod
    end_day  = cal_mod.monthrange(calendar_year, calendar_month)[1]
    start_jd = swe.julday(calendar_year, calendar_month, 1, 0.0)
    end_jd   = swe.julday(calendar_year, calendar_month, end_day, 23.99)
    mid_jd   = (start_jd + end_jd) / 2.0

    # Step 1: Sun's sidereal lon at mid-month
    sun_trop = swe.calc_ut(mid_jd, swe.SUN)[0][0]
    sun_sid  = (sun_trop - get_lahiri_ayanamsha(mid_jd)) % 360.0

    # Step 2: Find nearest natal_sun + n*30° to mid-month Sun
    # signed angular distance from natal_sun to sun_sid
    delta = (sun_sid - natal_sun_sid + 360) % 360   # 0-360
    nearest_n = round(delta / 30.0)                  # n such that natal+n*30 ≈ sun_sid
    target_lon = (natal_sun_sid + nearest_n * 30.0) % 360.0

    # Step 3: Search within month ± 3-day buffer
    result = _find_sun_lon_in_range(target_lon, start_jd - 3, end_jd + 3, lat, lon)
    if result:
        return result

    # Fallback: try adjacent n values (±1)
    for dn in [1, -1, 2, -2]:
        tl = (natal_sun_sid + (nearest_n + dn) * 30.0) % 360.0
        r  = _find_sun_lon_in_range(tl, start_jd - 3, end_jd + 3, lat, lon)
        if r:
            return r

    return {}


def _find_sun_lon_in_range(target_lon: float, jd_lo: float, jd_hi: float,
                            lat: float, lon: float) -> dict:
    """Binary search for the JD when Sun reaches target_lon within a range."""
    # First check if target is crossed in this range
    def sun_diff(jd):
        s = (swe.calc_ut(jd, swe.SUN)[0][0] - get_lahiri_ayanamsha(jd)) % 360.0
        d = (s - target_lon + 360) % 360
        return (d - 360) if d > 180 else d   # negative=not yet reached, positive=already passed

    d_lo = sun_diff(jd_lo)
    d_hi = sun_diff(jd_hi)
    if d_lo * d_hi > 0 and abs(d_lo) > 5:
        return None  # Not crossed in this range

    for _ in range(60):
        jd_mid = (jd_lo + jd_hi) / 2
        d_mid  = sun_diff(jd_mid)
        if d_mid < 0: jd_lo = jd_mid
        else:          jd_hi = jd_mid

    jd_sr = (jd_lo + jd_hi) / 2
    y, m, d, h = swe.revjul(jd_sr)
    return {"jd": jd_sr, "year": int(y), "month": int(m), "day": int(d),
            "hour": int(h), "minute": int((h - int(h)) * 60),
            "is_day": 6 <= h <= 18, "target_lon": round(target_lon, 4)}


def find_maas_entry(natal_sun_sid: float, target_year: int,
                    month_num: int, lat: float, lon: float) -> dict:
    """
    Find the JD when Sun reaches natal_sun_sid + month_num * 30° (mod 360).
    This is the Maas Pravesha — start of the monthly chart.
    """
    target_lon = (natal_sun_sid + month_num * 30.0) % 360.0
    # Start search from Jan 1 of target year
    jd_start = swe.julday(target_year, 1, 1, 0.0)
    prev_diff = None
    jd_bracket = None
    for d in range(400):
        jd = jd_start + d
        sun_trop = swe.calc_ut(jd, swe.SUN)[0][0]
        sun_sid  = (sun_trop - get_lahiri_ayanamsha(jd)) % 360.0
        diff = (sun_sid - target_lon + 360) % 360
        if diff > 180: diff -= 360
        if prev_diff is not None and prev_diff < 0 and diff >= 0:
            jd_bracket = (jd - 1, jd)
            break
        prev_diff = diff
    if not jd_bracket:
        return {}
    jd_lo, jd_hi = jd_bracket
    for _ in range(60):
        jd_mid = (jd_lo + jd_hi) / 2
        sun_sid = (swe.calc_ut(jd_mid, swe.SUN)[0][0] - get_lahiri_ayanamsha(jd_mid)) % 360.0
        diff = (sun_sid - target_lon + 360) % 360
        if diff > 180: diff -= 360
        if diff < 0: jd_lo = jd_mid
        else:         jd_hi = jd_mid
    jd_sr = (jd_lo + jd_hi) / 2
    y, m, d, h = swe.revjul(jd_sr)
    hour_int = int(h)
    minute_int = int((h - hour_int) * 60)
    return {"jd": jd_sr, "year": int(y), "month": int(m), "day": int(d),
            "hour": hour_int, "minute": minute_int, "is_day": 6 <= h <= 18,
            "target_lon": round(target_lon, 4)}


def compute_maas_lord(monthly_lagna_si: int, muntha_si: int,
                      birth_lagna_si: int, planets: dict,
                      is_day: bool, harsha_bala: dict) -> str:
    """
    5-way Monthly Lord (Maas-Adhipati) selection:
    1. Monthly Lagna Lord  2. Muntha Sign Lord  3. Birth Lagna Lord
    4. Tri-Rasi Lord (day=Sun sign lord, night=Moon sign lord)
    5. Day/Night Lord
    Strongest Harsha Bala among contestants wins.
    """
    contestants = set()
    contestants.add(SIGN_LORDS_LIST[monthly_lagna_si])
    contestants.add(SIGN_LORDS_LIST[muntha_si])
    contestants.add(SIGN_LORDS_LIST[birth_lagna_si])
    sun_si  = int(planets.get("Sun",  {}).get("longitude", 0) / 30) % 12
    moon_si = int(planets.get("Moon", {}).get("longitude", 0) / 30) % 12
    contestants.add(SIGN_LORDS_LIST[sun_si] if is_day else SIGN_LORDS_LIST[moon_si])
    contestants.add("Sun" if is_day else "Moon")
    return max(contestants, key=lambda p: harsha_bala.get(p, {}).get("biswas", 0))


def compute_navamsa_aspect(planet_a: str, lon_a: float,
                           planet_b: str, lon_b: float) -> dict:
    """Check if two planets' D9 signs are in 3-11 or 5-9 aspect."""
    def d9_si(lon):
        sign_idx = int(lon / 30) % 12
        deg_in_sign = lon % 30
        pada = int(deg_in_sign / (30/9))
        return (sign_idx * 9 + pada) % 12

    si_a = d9_si(lon_a)
    si_b = d9_si(lon_b)
    dist_fwd = ((si_b - si_a + 12) % 12) + 1
    dist_rev = ((si_a - si_b + 12) % 12) + 1
    friendly = {3, 11, 5, 9}
    auspicious = dist_fwd in friendly or dist_rev in friendly
    return {
        "planet_a": planet_a, "d9_sign_a": SIGNS_LIST[si_a],
        "planet_b": planet_b, "d9_sign_b": SIGNS_LIST[si_b],
        "house_dist": min(dist_fwd, dist_rev),
        "auspicious": auspicious,
        "gate": "Auspicious" if auspicious else "Inauspicious",
    }


def check_kartari(planets: dict, monthly_lagna_si: int) -> dict:
    """Kartari (Scissors) Yoga: both 2nd and 12th houses occupied by malefics."""
    MALEFICS = {"Sun", "Mars", "Saturn", "Rahu", "Ketu"}
    h2_si  = (monthly_lagna_si + 1) % 12
    h12_si = (monthly_lagna_si + 11) % 12
    h2_malefics  = [p for p,d in planets.items()
                    if not p.startswith("_") and p in MALEFICS
                    and int(d.get("longitude",0)/30)%12 == h2_si]
    h12_malefics = [p for p,d in planets.items()
                    if not p.startswith("_") and p in MALEFICS
                    and int(d.get("longitude",0)/30)%12 == h12_si]
    afflicted = bool(h2_malefics and h12_malefics)
    return {
        "afflicted":    afflicted,
        "status":       "Afflicted — Kartari Scissors Active" if afflicted else "Safe",
        "h2_malefics":  h2_malefics,
        "h12_malefics": h12_malefics,
    }


class MaasChartRequest(BaseModel):
    natal_chart:      Dict[str, Any]
    varsha_data:      Dict[str, Any]
    calendar_month:   int            # 1-12 (actual calendar month)
    calendar_year:    int            # actual calendar year
    current_lat:      float
    current_lon:      float
    use_birth_place:  bool = False


@app.post("/maas_chart")
def get_maas_chart(req: MaasChartRequest):
    """Compute Tajik Maas Kundali (monthly chart) for a given month offset."""
    try:
        nc = req.natal_chart
        vd = req.varsha_data
        birth_lagna_si = int(nc.get("lagna",{}).get("sign_index", 0))
        natal_sun_sid  = float(nc.get("planets",{}).get("Sun",{}).get("longitude", 0.0))
        target_year    = int(vd.get("target_year", 2026))
        muntha_si      = int(vd.get("muntha",{}).get("sign_index", 0))
        lat = float(nc.get("input",{}).get("lat",28.6)) if req.use_birth_place else req.current_lat
        lon = float(nc.get("input",{}).get("lon",77.2)) if req.use_birth_place else req.current_lon

        # 1. Monthly entry moment
        # Find the Maas Pravesha that falls within the requested calendar month
        entry = find_maas_entry_for_month(natal_sun_sid, req.calendar_month,
                                          req.calendar_year, lat, lon)
        if not entry:
            raise HTTPException(status_code=400, detail="Monthly entry not found")
        jd_m   = entry["jd"]
        is_day = entry["is_day"]

        # 2. Monthly chart
        monthly_lagna    = calc_lagna(jd_m, lat, lon)
        monthly_lagna_si = monthly_lagna["sign_index"]
        lagna_lon        = monthly_lagna["longitude"]
        monthly_planets  = calc_all_planets(jd_m, monthly_lagna_si)

        # 3. Harsha Bala for monthly
        monthly_hb = {}
        for p in ["Sun","Moon","Mars","Mercury","Jupiter","Venus","Saturn"]:
            pd     = monthly_planets.get(p, {})
            score  = (pd.get("dignity",{}).get("score",0)
                      if isinstance(pd.get("dignity"),dict) else 0)
            house0 = (pd.get("sign_index",0) - monthly_lagna_si + 12) % 12
            monthly_hb[p] = calc_harsha_bala(p, pd.get("sign_index",0), house0, score, is_day)

        # 4. Monthly Lord (Maas-Adhipati)
        maas_lord = compute_maas_lord(monthly_lagna_si, muntha_si, birth_lagna_si,
                                      monthly_planets, is_day, monthly_hb)
        maas_lord_hb   = monthly_hb.get(maas_lord, {})
        maas_lord_tier = maas_lord_hb.get("tier", "Weak")
        maas_lord_pd   = monthly_planets.get(maas_lord, {})
        combust        = maas_lord_pd.get("dignity",{}).get("label","") == "Combust" if isinstance(maas_lord_pd.get("dignity"),dict) else False

        # 5. Navamsa overlay
        lg_lord = SIGN_LORDS_LIST[monthly_lagna_si]
        lg_lord_lon  = monthly_planets.get(lg_lord, {}).get("longitude", 0.0)
        moon_lon_m   = monthly_planets.get("Moon", {}).get("longitude", 0.0)
        navamsa_asp  = compute_navamsa_aspect(lg_lord, lg_lord_lon, "Moon", moon_lon_m)

        # 6. Kartari check
        kartari = check_kartari(monthly_planets, monthly_lagna_si)

        # 7. Lunar Quotient (12-state)
        moon_deg   = moon_lon_m % 30
        lq_raw     = int((moon_deg * 2) / 5)
        lq_state   = max(1, min(12, lq_raw if lq_raw > 0 else 12))
        lq_name    = LUNAR_STATES[lq_state]
        dream_lord = SIGN_LORDS_LIST[int(lagna_lon / 30) % 12]
        dream_theme = DREAM_THEMES.get(dream_lord, "Unclear themes")

        # 8. Artha Saham (monthly) — 2nd cusp based on Shripati
        cusps_m = calc_shripati_cusps(jd_m, lat, lon)
        h2_cusp_lon  = cusps_m[1]
        h2_lord      = SIGN_LORDS_LIST[int(h2_cusp_lon/30)%12]
        h2_lord_tier = monthly_hb.get(h2_lord, {}).get("tier", "Unknown")

        # 9. 6th house lord (health)
        h6_si       = (monthly_lagna_si + 5) % 12
        h6_lord     = SIGN_LORDS_LIST[h6_si]
        h6_lord_pd  = monthly_planets.get(h6_lord, {})
        _h6_dign = h6_lord_pd.get("dignity", "")
        if isinstance(_h6_dign, dict):
            h6_lord_dign = _h6_dign.get("label") or _h6_dign.get("score","")
            h6_lord_dign = str(h6_lord_dign) if h6_lord_dign else "Neutral"
        elif isinstance(_h6_dign, str) and _h6_dign:
            h6_lord_dign = _h6_dign
        else:
            # Fallback: derive from sign position
            h6_si   = h6_lord_pd.get("sign_index", -1)
            h6_lord_name = h6_lord
            exalt = {"Sun":4,"Moon":1,"Mars":9,"Mercury":5,"Jupiter":3,"Venus":11,"Saturn":6}
            own   = {"Sun":[4],"Moon":[3],"Mars":[0,7],"Mercury":[2,5],"Jupiter":[8,11],"Venus":[1,6],"Saturn":[9,10]}
            debit = {"Sun":6,"Moon":7,"Mars":3,"Mercury":11,"Jupiter":9,"Venus":4,"Saturn":0}
            if h6_si == exalt.get(h6_lord_name): h6_lord_dign = "Exalted"
            elif h6_si in own.get(h6_lord_name, []): h6_lord_dign = "Own Sign"
            elif h6_si == debit.get(h6_lord_name): h6_lord_dign = "Debilitated"
            else: h6_lord_dign = "Neutral"

        # 10. Dietary
        h4_si  = (monthly_lagna_si + 3) % 12
        food_planet = next((p for p,d in monthly_planets.items()
                           if not p.startswith("_")
                           and int(d.get("longitude",0)/30)%12 == h4_si), None)
        food_note = {
            "Mars":   "Cold food this month",
            "Venus":  "Oily, ghee-rich food",
            "Saturn": "Fried or dry food",
            "Moon":   "Fresh and warm food",
        }.get(food_planet, "Standard diet — no specific indicator active")

        MONTH_NAMES = ["Jan","Feb","Mar","Apr","May","Jun",
                       "Jul","Aug","Sep","Oct","Nov","Dec"]
        month_label = f"{MONTH_NAMES[entry['month']-1]} {entry['year']}"

        return {
            "month_num":        req.calendar_month,
            "month_label":      month_label,
            "entry":            entry,
            "lagna":            monthly_lagna,
            "planets":          monthly_planets,
            "harsha_bala":      monthly_hb,
            "maas_lord": {
                "planet":    maas_lord,
                "tier":      maas_lord_tier,
                "biswas":    maas_lord_hb.get("biswas", 0),
                "combust":   combust,
                "sign":      maas_lord_pd.get("sign",""),
                "house":     maas_lord_pd.get("house", 0),
            },
            "navamsa_aspect":   navamsa_asp,
            "kartari":          kartari,
            "lunar_quotient": {
                "state_num":  lq_state,
                "state_name": lq_name,
                "moon_degree": round(moon_deg, 2),
                "dream_lord":  dream_lord,
                "dream_theme": dream_theme,
            },
            "artha": {
                "h2_lord":  h2_lord,
                "h2_tier":  h2_lord_tier,
            },
            "h6_lord":          h6_lord,
            "h6_lord_dignity":  h6_lord_dign,
            "food_note":        food_note,
            "is_day":           is_day,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Maas chart error: {str(e)}")


class MaasReportRequest(BaseModel):
    maas_brief:   Dict[str, Any]
    varsha_brief: Dict[str, Any]
    natal_brief:  Dict[str, Any]


@app.post("/maasreport")
def get_maas_report(req: MaasReportRequest):
    """AI narrative for Maas Phala monthly report."""
    try:
        mb = req.maas_brief
        vb = req.varsha_brief
        nb = req.natal_brief

        prompt = f"""You are a Tajik Neelakanthi Varshaphal expert writing a monthly analysis report.

Monthly Data: {json.dumps(mb, indent=2)}
Annual Context (Year Lord / Muntha): {json.dumps({"varshesha": vb.get("varshesha"), "muntha": vb.get("muntha"), "munthesh": vb.get("munthesh")}, indent=2)}
Natal Context: {json.dumps(nb, indent=2)}

Write EXACTLY these 3 sections in plain English (bold headers, no Sanskrit jargon):

**The Narrative Arc:**
2-3 sentences. How does this month fit within the annual theme? What is the Monthly Lord's primary domain of influence, and how does its strength level (tier) shape this 30-day window? Connect the monthly focus to the broader annual Year Lord energy.

**The Navamsa Insight:**
2 sentences. Describe the Navamsa Lords' relationship (auspicious or inauspicious) and what psychological environment this creates. If the gate is auspicious, state the specific nature of the opportunity. If inauspicious, describe the internal friction plainly.

**The Warning & The Shield:**
2-3 sentences. If Kartari is active, name it plainly as a wealth-protection alert. Identify the key risk from the 6th house lord's status. If any benefic provides a shield (Jupiter/Venus strong in a good house), name it explicitly. End with actionable language."""

        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": api_key,
                     "anthropic-version": "2023-06-01",
                     "content-type": "application/json"},
            json={"model": "claude-sonnet-4-6", "max_tokens": 1200,
                  "messages": [{"role": "user", "content": prompt}]},
            timeout=90
        )
        if response.status_code != 200:
            raise HTTPException(status_code=500,
                detail=f"API error {response.status_code}: {response.text[:300]}")
        data = response.json()
        text = "".join(b["text"] for b in data.get("content",[]) if b.get("type")=="text")
        return {"report": text}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Maas report error: {str(e)}")


# ═══════════════════════════════════════════════════════════════════════════════
# DINA PHALA ENGINE — Daily Precision Pulse
# ═══════════════════════════════════════════════════════════════════════════════

DINA_HUMOR = {
    "Sun":    ("Pitta", "Bile/Heat", "Inflammatory conditions, eye strain, excess heat"),
    "Moon":   ("Kapha", "Phlegm/Water", "Cold, mucus, emotional sensitivity"),
    "Mars":   ("Pitta", "Bile/Fire", "Cuts, fever, blood pressure, aggression"),
    "Mercury":("Vata-Pitta", "Wind-Bile", "Nervous tension, skin sensitivity, digestion"),
    "Jupiter":("Kapha-Vata", "Phlegm-Wind", "Liver, obesity, water retention"),
    "Venus":  ("Kapha", "Phlegm/Water", "Kidney sensitivity, reproductive health"),
    "Saturn": ("Vata", "Wind/Dryness", "Joint stiffness, fatigue, cold extremities"),
    "Rahu":   ("Vata", "Wind", "Anxiety, nervous system, erratic energy"),
    "Ketu":   ("Pitta-Vata", "Fire-Wind", "Sudden ailments, infections, detachment"),
}

DINA_DAY_LORD_DOMAIN = {
    "Sun":     "Authority, government matters, father, status",
    "Moon":    "Emotions, home, mother, public dealings, travel",
    "Mars":    "Energy, competition, property, siblings, conflicts",
    "Mercury": "Communication, trade, writing, analysis, intellect",
    "Jupiter": "Wisdom, expansion, children, teachers, spiritual matters",
    "Venus":   "Relationships, luxury, creativity, social gains, pleasure",
    "Saturn":  "Discipline, service, slow work, elderly, long-term investments",
}

DINA_MOON_STATE_MOOD = {
    1: ("Pravaas", "Restless — travel energy, unsettled focus", 45),
    2: ("Nashta", "Cautious — prone to overspending, guarded decisions", 30),
    3: ("Maran", "Heavy — avoid major commitments; rest and restore", 15),
    4: ("Jaya", "Victorious — excellent for competitive action", 85),
    5: ("Haasya", "Joyful — social, creative, lighthearted", 75),
    6: ("Rati", "Indulgent — pleasure-seeking, romantic", 65),
    7: ("Kreeda", "Playful — sports, fun, informal interactions", 70),
    8: ("Prasupta", "Inert — low drive; better for planning than doing", 35),
    9: ("Bhukta", "Fearful — anxiety-prone; avoid confrontations", 25),
    10: ("Jwara", "Unwell — physical caution; rest recommended", 20),
    11: ("Kampita", "Sorrowful — emotional weight; losses possible", 25),
    12: ("Susthita", "Settled — calm, comfortable, good for steady work", 80),
}

def get_sunrise_jd(date_str: str, lat: float, lon: float) -> float:
    """
    Get approximate sunrise JD for a given date and location.
    Uses solar noon minus half daylight (approximately 6h for equator,
    adjusted for latitude). Simple and dependency-free.
    """
    parts = date_str.split("-")
    y, m, d = int(parts[0]), int(parts[1]), int(parts[2])
    # Approximate sunrise: 6 AM local solar time adjusted for longitude
    # Solar noon is at 12:00 UTC + longitude/15 hours offset
    lon_offset_h = lon / 15.0
    sunrise_utc  = max(3.0, min(9.0, 6.0 - lon_offset_h * 0.5))
    return swe.julday(y, m, d, sunrise_utc)


def compute_dina_lord(daily_lagna_si: int, muntha_si: int, birth_lagna_si: int,
                      planets: dict, is_day: bool, harsha_bala: dict) -> str:
    """5-way Day Lord selection — same logic as Maas-Adhipati."""
    contestants = set()
    contestants.add(SIGN_LORDS_LIST[daily_lagna_si])
    contestants.add(SIGN_LORDS_LIST[muntha_si])
    contestants.add(SIGN_LORDS_LIST[birth_lagna_si])
    sun_si  = int(planets.get("Sun",  {}).get("longitude", 0) / 30) % 12
    moon_si = int(planets.get("Moon", {}).get("longitude", 0) / 30) % 12
    contestants.add(SIGN_LORDS_LIST[sun_si]  if is_day else SIGN_LORDS_LIST[moon_si])
    contestants.add("Sun" if is_day else "Moon")
    return max(contestants, key=lambda p: harsha_bala.get(p, {}).get("biswas", 0))


def compute_moon_phase(moon_lon: float, sun_lon: float) -> dict:
    """Moon phase: Full (180° from Sun), New (0°), Waxing/Waning."""
    elongation = (moon_lon - sun_lon + 360) % 360
    if elongation >= 165:
        phase = "Full Moon"; illumination = 100; quality = "Sound health and vitality"
    elif elongation >= 90:
        phase = "Waxing Gibbous"; illumination = int(elongation / 180 * 100)
        quality = "Increasing strength"
    elif elongation >= 45:
        phase = "First Quarter"; illumination = 50; quality = "Building momentum"
    elif elongation >= 15:
        phase = "Waxing Crescent"; illumination = 25; quality = "New beginnings"
    elif elongation <= 15:
        phase = "New Moon"; illumination = 0; quality = "Introspection; avoid new ventures"
    elif elongation <= 90:
        phase = "Waning Gibbous"; illumination = int((360-elongation)/180*100)
        quality = "Releasing and consolidating"
    else:
        phase = "Last Quarter"; illumination = 50; quality = "Reflection; caution in action"
    is_strong = illumination >= 60
    return {"phase": phase, "illumination": illumination,
            "quality": quality, "is_strong": is_strong}


def compute_capture_metric(planets: dict, lagna_si: int) -> dict:
    """Hunting/competition success: Mars+Mercury strength + Lagna/7th lords in Kendra."""
    MALEFICS = {"Sun","Mars","Saturn","Rahu","Ketu"}
    mars_sign  = planets.get("Mars",  {}).get("sign_index", -1)
    merc_sign  = planets.get("Mercury",{}).get("sign_index", -1)
    mars_own   = mars_sign  in [0, 7]
    merc_own   = merc_sign  in [2, 5]
    prey_avail = mars_own or merc_own or (mars_sign == 9) or (merc_sign == 5)  # exalt/own

    h7_si      = (lagna_si + 6) % 12
    lg_lord    = SIGN_LORDS_LIST[lagna_si]
    h7_lord    = SIGN_LORDS_LIST[h7_si]
    lg_lord_si = int(planets.get(lg_lord, {}).get("longitude", 0) / 30) % 12
    h7_lord_si = int(planets.get(h7_lord,{}).get("longitude", 0) / 30) % 12
    KENDRAS    = {lagna_si, (lagna_si+3)%12, (lagna_si+6)%12, (lagna_si+9)%12}
    in_kendra  = lg_lord_si in KENDRAS and h7_lord_si in KENDRAS

    score = (40 if prey_avail else 20) + (40 if in_kendra else 15)
    return {"prey_available": prey_avail, "lords_in_kendra": in_kendra, "score": score,
            "verdict": "High" if score >= 65 else "Moderate" if score >= 40 else "Low"}


def compute_vitality_score(planets: dict, lagna_si: int) -> dict:
    """Humors of planets in Lagna house."""
    lagna_planets = [p for p,d in planets.items()
                     if not p.startswith("_") and int(d.get("longitude",0)/30)%12 == lagna_si]
    if not lagna_planets:
        lagna_planets = [SIGN_LORDS_LIST[lagna_si]]  # use lagna lord if empty

    humor_totals = {"Pitta":0, "Kapha":0, "Vata":0}
    alerts = []
    for p in lagna_planets:
        h = DINA_HUMOR.get(p)
        if h:
            primary = h[0].split("-")[0]
            humor_totals[primary] = humor_totals.get(primary, 0) + 1
            alerts.append(h[2])

    dominant = max(humor_totals, key=lambda k: humor_totals[k]) if any(humor_totals.values()) else "Balanced"
    score = 70 - (10 if dominant == "Vata" else 5 if dominant == "Pitta" else 0)
    return {"dominant_humor": dominant, "alerts": alerts[:2], "score": score,
            "lagna_planets": lagna_planets}


class DinaChartRequest(BaseModel):
    natal_chart:  Dict[str, Any]
    varsha_data:  Dict[str, Any]
    date_str:     str    # YYYY-MM-DD
    current_lat:  float
    current_lon:  float


@app.post("/dina_chart")
def get_dina_chart(req: DinaChartRequest):
    """Compute Tajik Dina Phala — daily precision pulse."""
    try:
        nc  = req.natal_chart
        vd  = req.varsha_data
        birth_lagna_si = int(nc.get("lagna", {}).get("sign_index", 0))
        muntha_si      = int(vd.get("muntha", {}).get("sign_index", 0))
        lat, lon       = req.current_lat, req.current_lon

        # 1. Sunrise JD for the date
        jd_sr   = get_sunrise_jd(req.date_str, lat, lon)
        is_day  = True  # sunrise cast = daytime chart

        # 2. Daily chart at sunrise
        daily_lagna   = calc_lagna(jd_sr, lat, lon)
        daily_lagna_si = daily_lagna["sign_index"]
        lagna_lon      = daily_lagna["longitude"]
        daily_planets  = calc_all_planets(jd_sr, daily_lagna_si)

        # 3. Harsha Bala
        daily_hb = {}
        for p in ["Sun","Moon","Mars","Mercury","Jupiter","Venus","Saturn"]:
            pd     = daily_planets.get(p, {})
            score  = (pd.get("dignity",{}).get("score",0)
                      if isinstance(pd.get("dignity"),dict) else 0)
            house0 = (pd.get("sign_index",0) - daily_lagna_si + 12) % 12
            daily_hb[p] = calc_harsha_bala(p, pd.get("sign_index",0), house0, score, is_day)

        # 4. Day Lord
        dina_lord     = compute_dina_lord(daily_lagna_si, muntha_si, birth_lagna_si,
                                           daily_planets, is_day, daily_hb)
        dina_lord_hb  = daily_hb.get(dina_lord, {})
        dina_lord_tier= dina_lord_hb.get("tier", "Weak")
        dina_lord_pd  = daily_planets.get(dina_lord, {})
        _dl_dign      = dina_lord_pd.get("dignity", "")
        if isinstance(_dl_dign, dict):
            dina_lord_dign = _dl_dign.get("label","Neutral") or "Neutral"
        else:
            dina_lord_dign = str(_dl_dign) if _dl_dign else "Neutral"

        # 5. Lunar Quotient
        moon_lon = daily_planets.get("Moon", {}).get("longitude", 0.0)
        moon_deg = moon_lon % 30
        lq_raw   = int((moon_deg * 2) / 5)
        lq_state = max(1, min(12, lq_raw if lq_raw > 0 else 12))
        lq_name, lq_mood, lq_pct = DINA_MOON_STATE_MOOD[lq_state]

        # 6. Moon phase
        sun_lon    = daily_planets.get("Sun", {}).get("longitude", 0.0)
        moon_phase = compute_moon_phase(moon_lon, sun_lon)
        moon_house = ((int(moon_lon/30)%12 - daily_lagna_si + 12) % 12) + 1

        # 7. Kartari check
        kartari = check_kartari(daily_planets, daily_lagna_si)

        # 8. Day Lord receiving benefic Ithesal?
        BENEFICS = ["Jupiter","Venus","Mercury","Moon"]
        dl_lon   = dina_lord_pd.get("longitude", 0.0)
        benefic_ithesal = False
        for ben in BENEFICS:
            if ben == dina_lord: continue
            ben_lon = daily_planets.get(ben, {}).get("longitude", 0.0)
            asp = _tajik_aspect_between(ben, ben_lon, dina_lord, dl_lon)
            if asp.get("within_orb") and asp.get("ithesal"):
                benefic_ithesal = True; break

        # 9. Vitality + Capture
        vitality = compute_vitality_score(daily_planets, daily_lagna_si)
        capture  = compute_capture_metric(daily_planets, daily_lagna_si)

        # 10. Go/Stop time windows (approximate based on Day Lord + Lunar state)
        goodTiers = ["Very Strong","Medium"]
        if lq_state in [4, 5, 12] and dina_lord_tier in goodTiers:
            go_time   = "08:00 AM – 11:00 AM (Morning power window)"
            stop_time = "02:00 PM – 04:00 PM (Afternoon friction zone)"
        elif lq_state in [3, 9, 10, 11]:
            go_time   = "No strong Go window today — prefer planning over action"
            stop_time = "Avoid all major decisions; entire day requires caution"
        else:
            go_time   = "10:00 AM – 12:00 PM (Solar peak window)"
            stop_time = "06:00 PM – 08:00 PM (Evening friction zone)"

        # Format date label
        MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
        y_int, m_int, d_int, _ = swe.revjul(jd_sr)
        date_label = f"{int(d_int)} {MONTHS[int(m_int)-1]} {int(y_int)}"

        return {
            "date_str":      req.date_str,
            "date_label":    date_label,
            "lagna":         daily_lagna,
            "planets":       daily_planets,
            "harsha_bala":   daily_hb,
            "dina_lord": {
                "planet":   dina_lord,
                "tier":     dina_lord_tier,
                "biswas":   dina_lord_hb.get("biswas", 0),
                "dignity":  dina_lord_dign,
                "sign":     dina_lord_pd.get("sign", ""),
                "house":    dina_lord_pd.get("house", 0),
                "domain":   DINA_DAY_LORD_DOMAIN.get(dina_lord, ""),
                "benefic_ithesal": benefic_ithesal,
            },
            "lunar_quotient": {
                "state_num":  lq_state,
                "state_name": lq_name,
                "mood":       lq_mood,
                "success_pct": lq_pct,
                "moon_degree": round(moon_deg, 2),
            },
            "moon_phase":    moon_phase,
            "moon_house":    moon_house,
            "kartari":       kartari,
            "vitality":      vitality,
            "capture":       capture,
            "go_time":       go_time,
            "stop_time":     stop_time,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Dina chart error: {str(e)}")


class DinaReportRequest(BaseModel):
    dina_brief:   Dict[str, Any]
    varsha_brief: Dict[str, Any]
    natal_brief:  Dict[str, Any]


@app.post("/dinareport")
def get_dina_report(req: DinaReportRequest):
    """AI narrative for Dina Phala daily report."""
    try:
        db = req.dina_brief
        prompt = f"""You are a Tajik Neelakanthi Varshaphal expert writing a daily cosmic weather forecast.

Daily Data: {json.dumps(db, indent=2)}
Annual Context: {json.dumps(req.varsha_brief, indent=2)}

Write a concise daily briefing in plain English (no Sanskrit jargon). Bold headers. Maximum 200 words total.

**Morning Briefing:**
2-3 sentences. What is the dominant theme of this day based on the Lunar State and Day Lord combined? Name both planets/states. What does this mean for the person's immediate focus and energy level?

**The Warning:**
1-2 sentences. Name the specific risk or friction point for today (Kartari, weak Moon state, Day Lord in dusthana, etc.). Be direct — this is tactical intelligence, not philosophy.

**The Opportunity:**
1-2 sentences. What is the single best use of today's energy? Be specific to the actual chart data."""

        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": api_key, "anthropic-version": "2023-06-01",
                     "content-type": "application/json"},
            json={"model": "claude-sonnet-4-6", "max_tokens": 600,
                  "messages": [{"role": "user", "content": prompt}]},
            timeout=60
        )
        if response.status_code != 200:
            raise HTTPException(status_code=500,
                detail=f"API error {response.status_code}: {response.text[:300]}")
        data = response.json()
        text = "".join(b["text"] for b in data.get("content",[]) if b.get("type")=="text")
        return {"report": text}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Dina report error: {str(e)}")
