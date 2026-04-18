from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import swisseph as swe
from datetime import datetime, timedelta
import requests

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
