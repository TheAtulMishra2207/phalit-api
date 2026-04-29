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
