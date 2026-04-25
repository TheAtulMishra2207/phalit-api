from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import swisseph as swe
from datetime import datetime, timedelta
import requests
import os
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
    d9_dignity = get_dignity(planet, d9["d9_sign_index"], 0)  # degree 0 within D9 sign (sign-level dignity)
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
        "vargottama": vargottama
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
    chart_brief: Dict[str, Any]

@app.post("/d7report")
def generate_d7_report(req: D7ReportRequest):
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not configured on server.")

    brief = req.chart_brief
    name  = req.name or "the native"
    gender = brief.get('gender', 'male')

    system_prompt = """You are writing a focused lineage and progeny report for a Vedic astrology platform.
Stay strictly on topic. Cover only: children, progeny potential, lineage quality, and the karmic nature of parent-child bonds.

Absolute rules:
1. Use ONLY the corpus provided. No external knowledge.
2. ZERO technical terminology — no planet names, house numbers, sign names, Sanskrit terms, ocean/deity names.
3. Second person throughout. "You will...", "Your children...", "Your lineage..."
4. Each section 5-7 sentences. No bullet points. Direct, specific prose.
5. NO personality analysis. NO career references. NO wealth commentary.
6. Write exactly 4 sections with these headings (use ### before each):
   ### Your Capacity for Children and Lineage
   ### The Nature and Character of Your Children
   ### Karmic Patterns and Challenges in Progeny
   ### Your Legacy and the Fruit of Your Lineage
7. Complete all 4 sections. Be specific about number of children where the data indicates."""

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

Write 4 focused sections on children, their nature, karmic challenges, and legacy. Specific about numbers where data supports it."""

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
