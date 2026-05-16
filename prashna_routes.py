# =================================================================
# Phalit.ai — Prashna API Routes (Phase 1H)
# =================================================================
# Exposes the /prashna_chart endpoint that wires together the
# foundational engine (constants, sincerity, avasthas, bhava bala,
# Tajik aspects, multi-query anchors) into a single API response.
#
# INTEGRATION OPTIONS:
#   (a) APIRouter pattern (recommended — keeps main.py uncluttered):
#         from prashna_routes import router as prashna_router
#         app.include_router(prashna_router)
#
#   (b) Inline paste — copy everything below the "BEGIN PASTE" marker
#       and append it to main.py. Replace the `router = APIRouter()`
#       and `@router.post(...)` lines with `@app.post(...)`.
#
# DEPENDENCIES (all already in main.py environment):
#   - fastapi
#   - pydantic
#   - pyswisseph (imported as `swe`)
#   - prashna_engine (the foundation module — must be importable)
#
# Locked decisions reflected:
#   - Lahiri ayanamsha (manual setting)
#   - Whole-Sign houses
#   - Mean nodes
#   - Rahu exalted in Taurus / Ketu in Scorpio (BPHS Ch.47)
#   - datetime.utcnow() for any "now" defaults
# =================================================================

# ================= BEGIN PASTE (for inline integration) =================

import math
from datetime import datetime, timezone
from typing import Dict, List, Optional, Literal, Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

import swisseph as swe

from prashna_engine import (
    SIGNS, SIGN_SANSKRIT, SIGN_LORDS,
    phonetic_to_lagna_sign,
    compute_sun_altitude,
    compute_shadow_ratio_from_altitude,
    compute_sincerity_score,
    compute_avasthas,
    compute_bhava_bala,
    detect_all_aspects,
    resolve_query_lagna,
    build_query_chart,
    MAX_QUERIES_PER_CHART,
    # Vivaha (Phase 2)
    karya_success_chain,
    compute_strength_scaling,
    horary_to_natal_shift,
    vivaha_judgment,
    # Garbha (Phase 3A)
    garbha_judgment,
    classify_garbha_intent,
    compute_beeja_sphuta,
    compute_kshetra_sphuta,
)

# Phase 4A — generic topic orchestrator
from prashna_topics import (
    prashna_topic_judgment,
    PRASHNA_TOPICS,
)

# Phase 4C — AI narrative dispatcher
from prashna_narratives import (
    generate_narrative,
    NarrativeError,
    NARRATIVE_TONES,
    USER_PROMPT_BUILDERS,
    PRASHNA_AI_MODEL,
)

router = APIRouter(prefix="", tags=["prashna"])


# -----------------------------------------------------------------
# REQUEST / RESPONSE MODELS
# -----------------------------------------------------------------

class PrashnaChartRequest(BaseModel):
    """
    Request body for /prashna_chart.

    Two casting modes:
      - 'time':     Standard time-based Lagna from date/time/lat/lon.
      - 'phonetic': Lagna derived from the first syllable of `query_text`
                    (Pavarga table). Planets still computed for the supplied
                    or current UTC time.

    Notes on phonetic mode:
      - If `query_text` cannot be parsed (e.g. English start letter not in
        the Pavarga table), the endpoint silently falls back to time-based
        Lagna and reports this in `casting_note`.
      - If date/time are omitted in phonetic mode, current UTC is used.
    """

    mode: Literal['time', 'phonetic'] = Field('time', description="Casting mode")

    # Location — required for both modes (Sun altitude / time-based Lagna)
    lat: float = Field(..., description="Latitude (degrees, N positive)")
    lon: float = Field(..., description="Longitude (degrees, E positive)")
    place_name: Optional[str] = Field(None, description="Human-readable place name")

    # Date / time — required for 'time' mode; optional for 'phonetic'
    date: Optional[str] = Field(None, description="ISO date YYYY-MM-DD")
    time: Optional[str] = Field(None, description="Local time HH:MM or HH:MM:SS")
    timezone_str: Optional[str] = Field(
        None,
        alias='timezone',
        description="IANA timezone (e.g. 'Asia/Kolkata'). "
                    "Required if date/time are supplied without UTC offset."
    )

    # Required for phonetic mode
    query_text: Optional[str] = Field(None, description="The query text — first syllable drives the Lagna")

    # Multi-query anchor (Q1 = the Prashna Lagna, Q2–Q5 use shifting pivots)
    question_index: int = Field(1, ge=1, le=MAX_QUERIES_PER_CHART,
                                description="Which question in the session (1–5)")

    # Advanced overrides
    lagna_override: Optional[int] = Field(None, ge=0, le=11,
                                          description="Force a specific Lagna sign (0=Aries..11=Pisces). "
                                                      "Bypasses both time-based and phonetic logic.")

    class Config:
        populate_by_name = True


class PrashnaVivahaRequest(PrashnaChartRequest):
    """
    Request body for /prashna_vivaha.

    Identical to /prashna_chart but adds an optional natal_lagna_sign so the
    Horary-to-Natal Shift can localise the verdict to the user's natal chart.
    If absent, the validation bar shows only the Sincerity gauge.
    """
    natal_lagna_sign: Optional[int] = Field(
        None, ge=0, le=11,
        description="User's natal Lagna sign (0=Aries..11=Pisces). "
                    "If provided, enables Horary-to-Natal Shift in the validation bar."
    )
    full_query: Optional[str] = Field(
        None,
        description="The complete question text (used for long-horizon keyword "
                    "detection). When mode='phonetic', query_text holds just the "
                    "first crystallised word for Lagna derivation, while full_query "
                    "holds the full sentence. When omitted, falls back to query_text."
    )


class PrashnaGarbhaRequest(PrashnaChartRequest):
    """
    Request body for /prashna_garbha (Vaivahika · Garbha · Conception).

    Mirrors PrashnaVivahaRequest with Garbha-specific extensions:
      - querent_gender: REQUIRED. Drives Beeja vs Kshetra Sphuta computation.
      - intent: optional pre-classification; auto-classified from full_query otherwise.
      - full_query: full sentence for intent classification, long-horizon detection,
                    and husband-pivot phrasing detection.
    """
    natal_lagna_sign: Optional[int] = Field(
        None, ge=0, le=11,
        description="User's natal Lagna sign (0=Aries..11=Pisces). "
                    "Enables Horary-to-Natal Shift and natal-5th sincerity bonus."
    )
    full_query: Optional[str] = Field(
        None,
        description="Full question text. Drives intent classification, "
                    "long-horizon detection, husband-pivot phrasing detection, "
                    "and lineage-keyword 9th-house exception."
    )
    querent_gender: Literal['male', 'female'] = Field(
        ...,
        description="Required. Male → Beeja Sphuta applied; Female → Kshetra Sphuta. "
                    "Drives the 5th Bhava Bala +15% bonus or 50%-cap depending on "
                    "Sphuta sign parity."
    )
    intent: Optional[Literal[
        'conception_possibility',
        'current_pregnancy_confirmation',
        'conception_timing',
        'gestation_safety',
        'outcome_quality',
    ]] = Field(
        None,
        description="Override the intent classifier. When omitted, the engine "
                    "infers intent from full_query via keyword matching."
    )


# -----------------------------------------------------------------
# PHASE 4B — Canonical /prashna_topic schema
# -----------------------------------------------------------------

class PrashnaChartInputs(BaseModel):
    """
    Casting parameters nested under PrashnaTopicRequest.chart_data.
    Mirrors PrashnaChartRequest fields without the topic_id concerns.
    """
    mode: Literal['time', 'phonetic'] = Field(
        'time', description="'time' for time+place casting or 'phonetic' for first-syllable Pavarga"
    )
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)
    place_name: Optional[str] = None
    date: Optional[str] = Field(None, description="YYYY-MM-DD, defaults to current UTC date")
    time: Optional[str] = Field(None, description="HH:MM, defaults to current UTC time")
    timezone: Optional[str] = Field(None, alias='timezone_str',
                                     description="IANA timezone string, defaults to UTC")
    query_text: Optional[str] = Field(None, description="Question text (full sentence or first word)")
    lagna_override: Optional[int] = Field(None, ge=0, le=11)
    question_index: int = Field(1, ge=1, le=5,
                                 description="Q1=Prashna Lagna; Q2-Q5 rotate Moon→Sun→Jupiter→Mercury/Venus")

    class Config:
        populate_by_name = True
        extra = 'allow'  # tolerate extra cast fields


class PrashnaTopicRequest(BaseModel):
    """
    Canonical Phase 4B request body for /prashna_topic.

    Generic shape that drives the registry-based orchestrator. Replaces
    the per-topic schemas (PrashnaVivahaRequest, PrashnaGarbhaRequest)
    with a single declarative payload structure.

    Example:
        {
            "topic_id": "garbha",
            "chart_data": {
                "mode": "phonetic", "lat": 28.57, "lon": 77.32,
                "query_text": "Santaan", "date": "2026-05-15",
                "time": "10:00", "timezone": "Asia/Kolkata",
                "place_name": "Noida"
            },
            "topic_inputs": {
                "querent_gender": "female",
                "full_query": "Will we conceive a child this year?",
                "natal_lagna_sign": 6
            }
        }

    The orchestrator validates topic_inputs against
    PRASHNA_TOPICS[topic_id]['required_inputs'] at run time.
    """
    topic_id: str = Field(
        ...,
        description=f"Registered topic. Currently available: {sorted(PRASHNA_TOPICS)}"
    )
    chart_data: PrashnaChartInputs = Field(
        ...,
        description="Casting parameters for the Prashna Lagna chart."
    )
    topic_inputs: Dict[str, Any] = Field(
        default_factory=dict,
        description="Topic-specific inputs (see registry's required_inputs/optional_inputs)."
    )


class PrashnaReportRequest(BaseModel):
    """
    Request body for /prashnareport. Accepts a complete judgment package
    (the dict returned by /prashna_vivaha, /prashna_garbha, or /prashna_topic)
    plus optional persona context, and returns a 3-tranche narrative + 3
    action cards via the LLM.

    Topic dispatch (Phase 4C):
      - 'topic_id' is the canonical field; pass it from /prashna_topic clients
      - 'sub_module' is the legacy field; preserved for /prashna_vivaha and
        /prashna_garbha clients. If both are supplied, topic_id wins.
    """
    topic_id: Optional[str] = Field(
        None,
        description="Canonical topic identifier from PRASHNA_TOPICS. "
                    "When omitted, falls back to sub_module."
    )
    sub_module: Optional[str] = Field(
        None,
        description="Legacy alias for topic_id. Accepted for backward compat "
                    "with /prashna_vivaha and /prashna_garbha clients."
    )
    judgment: Dict = Field(
        ...,
        description="The full judgment dict — either the canonical shape from "
                    "/prashna_topic's 'judgment' key, or the legacy flat shape "
                    "from /prashna_vivaha's 'vivaha' / /prashna_garbha's 'garbha' key."
    )
    query_text: Optional[str] = Field(
        None, description="The original question text (for narrative context)"
    )
    cast_meta: Optional[Dict] = Field(
        None, description="Cast metadata (JD, datetime, place_name) for narrative context"
    )
    topic_inputs: Optional[Dict] = Field(
        None,
        description="Topic-specific inputs (e.g. querent_gender for Garbha). "
                    "Required only when the judgment came from /prashna_topic and "
                    "the prompt builder needs inputs not present in overlay data."
    )


# -----------------------------------------------------------------
# CHART-CAST HELPERS (self-contained — does not depend on
# main.py's existing /chart logic; can be refactored later to share)
# -----------------------------------------------------------------

# Locked: Lahiri ayanamsha
swe.set_sid_mode(swe.SIDM_LAHIRI)

# Planet → Swiss Ephemeris code (Mean nodes per locked decision)
PLANET_CODES = {
    'Sun':     swe.SUN,
    'Moon':    swe.MOON,
    'Mars':    swe.MARS,
    'Mercury': swe.MERCURY,
    'Jupiter': swe.JUPITER,
    'Venus':   swe.VENUS,
    'Saturn':  swe.SATURN,
    'Rahu':    swe.MEAN_NODE,
    # Ketu is computed as Rahu + 180°
}


def _resolve_jd_ut(date_str: Optional[str], time_str: Optional[str],
                   tz_str: Optional[str]) -> Dict:
    """
    Resolve the user-supplied date/time/timezone to JD UT.
    Falls back to current UTC if any field is missing.

    Returns dict: {jd_ut, datetime_utc_iso, datetime_local_iso, timezone_used}.
    """
    if not (date_str and time_str):
        # Default: current UTC
        now_utc = datetime.now(timezone.utc)
        hour_frac = (now_utc.hour
                     + now_utc.minute / 60.0
                     + now_utc.second / 3600.0)
        jd_ut = swe.julday(now_utc.year, now_utc.month, now_utc.day,
                           hour_frac, swe.GREG_CAL)
        return {
            'jd_ut': jd_ut,
            'datetime_utc_iso': now_utc.isoformat(),
            'datetime_local_iso': now_utc.isoformat(),
            'timezone_used': 'UTC (default)',
        }

    # Parse supplied date+time
    try:
        # Tolerate both HH:MM and HH:MM:SS
        time_normalised = time_str if time_str.count(':') == 2 else f"{time_str}:00"
        naive = datetime.fromisoformat(f"{date_str}T{time_normalised}")
    except ValueError as e:
        raise HTTPException(status_code=400,
                            detail=f"Invalid date/time format: {e}")

    if tz_str:
        try:
            try:
                from zoneinfo import ZoneInfo
                tz = ZoneInfo(tz_str)
            except ImportError:
                import pytz
                tz = pytz.timezone(tz_str)
            if hasattr(tz, 'localize'):
                local_dt = tz.localize(naive)
            else:
                local_dt = naive.replace(tzinfo=tz)
        except Exception as e:
            raise HTTPException(status_code=400,
                                detail=f"Invalid timezone '{tz_str}': {e}")
        utc_dt = local_dt.astimezone(timezone.utc)
        local_iso = local_dt.isoformat()
        tz_used = tz_str
    else:
        # Assume the supplied time IS already UTC
        utc_dt = naive.replace(tzinfo=timezone.utc)
        local_iso = naive.isoformat()
        tz_used = 'UTC (assumed)'

    hour_frac = (utc_dt.hour + utc_dt.minute / 60.0
                 + utc_dt.second / 3600.0)
    jd_ut = swe.julday(utc_dt.year, utc_dt.month, utc_dt.day,
                       hour_frac, swe.GREG_CAL)
    return {
        'jd_ut': jd_ut,
        'datetime_utc_iso': utc_dt.isoformat(),
        'datetime_local_iso': local_iso,
        'timezone_used': tz_used,
    }


def _compute_planet_positions(jd_ut: float) -> Dict[str, Dict]:
    """
    Compute sidereal (Lahiri) longitudes for the 7 classical planets + Rahu + Ketu.
    Returns dict planet → {longitude, sign_index, sign, sign_sanskrit, retrograde}.
    """
    flags = swe.FLG_SIDEREAL | swe.FLG_SPEED
    out: Dict[str, Dict] = {}
    for name, code in PLANET_CODES.items():
        result, _ = swe.calc_ut(jd_ut, code, flags)
        lon = result[0] % 360.0
        speed = result[3]  # daily motion in longitude
        sign_idx = int(lon // 30) % 12
        out[name] = {
            'longitude': lon,
            'sign_index': sign_idx,
            'sign': SIGNS[sign_idx],
            'sign_sanskrit': SIGN_SANSKRIT[sign_idx],
            'retrograde': speed < 0,
            'speed': speed,
        }
    # Ketu = Rahu + 180°
    rahu_lon = out['Rahu']['longitude']
    ketu_lon = (rahu_lon + 180.0) % 360.0
    sign_idx = int(ketu_lon // 30) % 12
    out['Ketu'] = {
        'longitude': ketu_lon,
        'sign_index': sign_idx,
        'sign': SIGNS[sign_idx],
        'sign_sanskrit': SIGN_SANSKRIT[sign_idx],
        'retrograde': True,  # Nodes are always retrograde in motion
        'speed': -out['Rahu']['speed'],
    }
    return out


def _compute_ascendant(jd_ut: float, lat: float, lon: float) -> float:
    """
    Compute the sidereal (Lahiri) ascendant longitude using Swiss Ephemeris
    in Whole-Sign-house mode ('W'). Returns longitude in degrees [0, 360).
    """
    # houses_ex returns (cusps[12], ascmc[10]); ascmc[0] is ascendant longitude
    cusps, ascmc = swe.houses_ex(jd_ut, lat, lon, b'W', swe.FLG_SIDEREAL)
    return ascmc[0] % 360.0


def _build_whole_sign_houses(lagna_sign: int, planets: Dict) -> List[Dict]:
    """
    Build 12 Whole-Sign house dicts, each carrying its sign name, occupants,
    and lord. Houses are 1-indexed starting from the Lagna sign.
    """
    houses = []
    for h in range(12):
        s = (lagna_sign + h) % 12
        occupants = [p for p, pd in planets.items() if pd['sign_index'] == s]
        houses.append({
            'house_num': h + 1,
            'sign': SIGNS[s],
            'sign_sanskrit': SIGN_SANSKRIT[s],
            'sign_index': s,
            'lord': SIGN_LORDS[s],
            'occupants': occupants,
        })
    return houses


# -----------------------------------------------------------------
# ENDPOINT
# -----------------------------------------------------------------

@router.post("/prashna_chart")
def prashna_chart(req: PrashnaChartRequest) -> Dict:
    """
    Cast a Prashna chart and return the full diagnostic package:
      - base_chart:           the Q1 (Prashna Lagna) chart with planets + houses
      - active_chart:         the chart re-anchored for the requested question_index
      - multi_query_anchors:  all 5 possible Lagna pivots for this session
      - sincerity:            ethical-filter score, verdict, triggers, narrative_lead
      - avasthas:             10-state classification for each classical planet
      - aspects:              all Tajik pairwise + Nakta + Kambool detections
      - bhava_bala:           25/50/75/100 % strength for all 12 houses
      - cast_meta:            date/time/JD/casting_note for audit
    """

    # 1. Resolve JD UT
    jd_info = _resolve_jd_ut(req.date, req.time, req.timezone_str)
    jd_ut = jd_info['jd_ut']

    # 2. Planet positions
    planets = _compute_planet_positions(jd_ut)

    # 3. Lagna determination
    casting_note = ''
    if req.lagna_override is not None:
        lagna_sign = int(req.lagna_override) % 12
        lagna_lon = lagna_sign * 30.0
        casting_note = f"Manual Lagna override: {SIGNS[lagna_sign]}"

    elif req.mode == 'phonetic':
        if not req.query_text:
            raise HTTPException(status_code=400,
                                detail="query_text is required when mode='phonetic'")
        phon = phonetic_to_lagna_sign(req.query_text)
        if 'error' in phon:
            # Fall back silently to time-based
            lagna_lon = _compute_ascendant(jd_ut, req.lat, req.lon)
            lagna_sign = int(lagna_lon // 30) % 12
            casting_note = (f"Phonetic parsing failed ('{phon['error']}'). "
                            f"Fell back to time-based Lagna: {SIGNS[lagna_sign]}.")
        else:
            lagna_sign = phon['sign_index']
            lagna_lon = lagna_sign * 30.0
            casting_note = (f"Phonetic Lagna from '{phon['matched_letter']}' "
                            f"(via {phon['ruling_planet']}, "
                            f"position {phon['position_in_group']}, "
                            f"method {phon['method']}) → {SIGNS[lagna_sign]}")
    else:
        lagna_lon = _compute_ascendant(jd_ut, req.lat, req.lon)
        lagna_sign = int(lagna_lon // 30) % 12
        casting_note = (f"Time-based Lagna: {SIGNS[lagna_sign]} "
                        f"({lagna_lon - lagna_sign*30:.2f}° into sign)")

    # 4. Build houses (Whole Sign)
    houses = _build_whole_sign_houses(lagna_sign, planets)

    # 5. Sun altitude + shadow ratio (replaces 12-finger stick measurement)
    sun_alt = compute_sun_altitude(jd_ut, req.lat, req.lon, planets['Sun']['longitude'])
    shadow = compute_shadow_ratio_from_altitude(sun_alt)
    sun_above_horizon = sun_alt > 0

    # 6. Assemble base chart (Q1 Prashna Lagna)
    base_chart = {
        'lagna_sign': lagna_sign,
        'lagna_name': SIGNS[lagna_sign],
        'lagna_sanskrit': SIGN_SANSKRIT[lagna_sign],
        'lagna_longitude': lagna_lon,
        'planets': planets,
        'houses': houses,
        'jd_ut': jd_ut,
        'lat': req.lat,
        'lon': req.lon,
        'place_name': req.place_name,
        'sun_altitude': round(sun_alt, 4),
        'shadow_ratio': round(shadow, 4) if shadow >= 0 else None,
        'sun_above_horizon': sun_above_horizon,
        'cast_mode': req.mode,
        'casting_note': casting_note,
    }

    # 7. Re-anchor to the requested question_index
    if req.question_index == 1:
        active_chart = base_chart
        active_chart_meta = {
            'question_index': 1,
            'source': 'Prashna Lagna (chart ascendant)',
            'effective_lagna_sign': lagna_sign,
            'effective_lagna_name': SIGNS[lagna_sign],
        }
    else:
        active_chart = build_query_chart(base_chart, req.question_index)
        if 'error' in active_chart:
            raise HTTPException(status_code=400, detail=active_chart['error'])
        active_chart_meta = active_chart.get('query_anchor', {})

    # 8. Diagnostic layers (all computed on the active chart)
    sincerity = compute_sincerity_score(active_chart)
    avasthas = compute_avasthas(active_chart)
    aspects = detect_all_aspects(active_chart)
    bhava_bala = {
        str(h): compute_bhava_bala(active_chart, h) for h in range(1, 13)
    }

    # 9. All 5 multi-query anchors (for the UI's question-switcher)
    multi_query_anchors = [
        resolve_query_lagna(base_chart, qi)
        for qi in range(1, MAX_QUERIES_PER_CHART + 1)
    ]

    return {
        'base_chart': base_chart,
        'active_chart': active_chart,
        'active_chart_meta': active_chart_meta,
        'active_question_index': req.question_index,
        'multi_query_anchors': multi_query_anchors,
        'sincerity': sincerity,
        'avasthas': avasthas,
        'aspects': aspects,
        'bhava_bala': bhava_bala,
        'cast_meta': {
            'jd_ut': jd_ut,
            'datetime_utc_iso': jd_info['datetime_utc_iso'],
            'datetime_local_iso': jd_info['datetime_local_iso'],
            'timezone_used': jd_info['timezone_used'],
            'casting_note': casting_note,
            'ayanamsha': 'Lahiri',
            'house_system': 'Whole Sign',
            'nodes': 'Mean',
        },
    }


# -----------------------------------------------------------------
# PHASE 4B — Shared casting pipeline + legacy-shape flatteners
# -----------------------------------------------------------------

def _cast_chart_pipeline(req_like: Any) -> Dict:
    """
    Generic chart-casting pipeline used by all three route handlers
    (/prashna_topic, /prashna_vivaha, /prashna_garbha).

    Accepts any request-like object exposing the casting fields:
    `mode`, `lat`, `lon`, `place_name`, `date`, `time`, `query_text`,
    `lagna_override`, `question_index`. Supports both `timezone_str` and
    `timezone` attribute names.

    Returns dict with: base_chart, active_chart, jd_info, phon,
    casting_note, sun_alt, shadow, sun_above_horizon — everything the
    diagnostic + judgment layers need.
    """
    # Tolerate either 'timezone_str' or 'timezone' attribute
    tz = getattr(req_like, 'timezone_str', None) or getattr(req_like, 'timezone', None)

    jd_info = _resolve_jd_ut(req_like.date, req_like.time, tz)
    jd_ut = jd_info['jd_ut']
    planets = _compute_planet_positions(jd_ut)

    casting_note = ''
    lagna_override = getattr(req_like, 'lagna_override', None)
    if lagna_override is not None:
        lagna_sign = int(lagna_override) % 12
        lagna_lon = lagna_sign * 30.0
        casting_note = f"Manual Lagna override: {SIGNS[lagna_sign]}"
        phon = None
    elif req_like.mode == 'phonetic':
        if not req_like.query_text:
            raise HTTPException(status_code=400,
                                detail="query_text is required when mode='phonetic'")
        phon = phonetic_to_lagna_sign(req_like.query_text)
        if 'error' in phon:
            lagna_lon = _compute_ascendant(jd_ut, req_like.lat, req_like.lon)
            lagna_sign = int(lagna_lon // 30) % 12
            casting_note = (f"Phonetic parsing failed ('{phon['error']}'). "
                            f"Fell back to time-based Lagna: {SIGNS[lagna_sign]}.")
            phon = None
        else:
            lagna_sign = phon['sign_index']
            lagna_lon = lagna_sign * 30.0
            single_lord_note = " (single-lord varga)" if phon.get('single_lord') else ""
            casting_note = (f"Phonetic Lagna from '{phon['matched_letter']}' "
                            f"(via {phon['ruling_planet']}, "
                            f"position {phon['position_in_group']}{single_lord_note}, "
                            f"method {phon['method']}) → {SIGNS[lagna_sign]}")
    else:
        lagna_lon = _compute_ascendant(jd_ut, req_like.lat, req_like.lon)
        lagna_sign = int(lagna_lon // 30) % 12
        casting_note = (f"Time-based Lagna: {SIGNS[lagna_sign]} "
                        f"({lagna_lon - lagna_sign*30:.2f}° into sign)")
        phon = None

    houses = _build_whole_sign_houses(lagna_sign, planets)
    sun_alt = compute_sun_altitude(jd_ut, req_like.lat, req_like.lon, planets['Sun']['longitude'])
    shadow = compute_shadow_ratio_from_altitude(sun_alt)
    sun_above_horizon = sun_alt > 0

    base_chart = {
        'lagna_sign': lagna_sign,
        'lagna_name': SIGNS[lagna_sign],
        'lagna_sanskrit': SIGN_SANSKRIT[lagna_sign],
        'lagna_longitude': lagna_lon,
        'planets': planets,
        'houses': houses,
        'jd_ut': jd_ut,
        'lat': req_like.lat,
        'lon': req_like.lon,
        'place_name': getattr(req_like, 'place_name', None),
        'sun_altitude': round(sun_alt, 4),
        'shadow_ratio': round(shadow, 4) if shadow >= 0 else None,
        'sun_above_horizon': sun_above_horizon,
        'cast_mode': req_like.mode,
        'casting_note': casting_note,
    }
    return {
        'base_chart': base_chart,
        'active_chart': base_chart,  # Q1 anchor; multi-query rotation reserved for diagnostic hub
        'jd_info': jd_info,
        'phon': phon,
        'casting_note': casting_note,
    }


def _flatten_to_legacy_vivaha(judgment: Dict) -> Dict:
    """
    Map prashna_topic_judgment output → legacy vivaha_judgment shape.

    Keeps /prashnareport and any client code reading req.judgment.<key>
    fields working without modification. Phase 4C may eliminate this when
    the AI narrative builder reads from overlay_findings directly.

    Phase 4D: replicates the legacy vivaha_judgment decision tree for
    verdict_text + match_type + match_narrative + reciprocity_narrative
    so the equivalence gate produces byte-identical output for the four
    fields Atul flagged.
    """
    findings = judgment.get('overlay_findings', {})
    nakta_data = findings.get('nakta_abhara_scan', {}).get('data') or {}
    karya = judgment.get('karya_chain') or {}

    # Topic-faithful derivation of match_type + match_narrative + verdict_text
    match_type, match_narrative = _vivaha_derive_match(judgment, nakta_data, karya)
    verdict_text, verdict_final = _vivaha_derive_verdict_text(judgment, nakta_data, karya)

    # Strip the canonical-only `source_overlay` metadata field from core_catalyst
    # so the legacy shape matches byte-for-byte.
    catalyst = judgment.get('core_catalyst')
    if catalyst and 'source_overlay' in catalyst:
        catalyst = {k: v for k, v in catalyst.items() if k != 'source_overlay'}

    # Vivaha legacy did NOT include target_house/target_role in its dict
    # (they were inferred). Preserve that to keep the equivalence gate clean.
    return {
        'sub_module':           'vivaha',
        'verdict':              verdict_final,
        'verdict_text':         verdict_text,
        'certainty_score':      judgment.get('certainty_score'),
        'certainty_band':       judgment.get('certainty_band'),
        'certainty_narrative':  judgment.get('certainty_narrative'),
        'core_catalyst':        catalyst,
        'querent_lord':         judgment.get('querent_lord'),
        'quesited_lord':        judgment.get('quesited_lord'),
        # Tajik aspect + yogas (lifted from overlay data)
        'aspect_l1_l7':         nakta_data.get('aspect_l1_lt'),
        'nakta_bridge':         nakta_data.get('nakta_bridge'),
        'abhara_yoga':          nakta_data.get('abhara_yoga'),
        'yama_yoga':            nakta_data.get('yama_yoga'),
        # Vivaha-specific overlays
        'third_party_interference': (findings.get('third_party_interference', {}).get('data') or {}).get('third_party_interference', []),
        'emotional_reciprocity':    (findings.get('emotional_reciprocity', {}).get('data') or {}).get('emotional_reciprocity'),
        'reciprocity_narrative':    _vivaha_derive_reciprocity_narrative(judgment, nakta_data),
        # Core layers
        'karya_chain':          karya,
        'strength_scaling':     judgment.get('strength_scaling'),
        'bhava_bala_7th':       judgment.get('bhava_bala_target'),  # legacy key name
        'horary_to_natal':      judgment.get('horary_to_natal'),
        'long_horizon':         judgment.get('long_horizon'),
        # Legacy match-type derivation (matches vivaha_judgment decision tree)
        'match_type':           match_type,
        'match_narrative':      match_narrative,
    }


# -----------------------------------------------------------------
# Legacy vivaha_judgment decision-tree replicas — exact strings
# -----------------------------------------------------------------

def _vivaha_derive_match(judgment, nakta_data, karya):
    """
    Replica of vivaha_judgment's match_type / match_narrative decision tree.
    Decision precedence:
      1. Karya rule 4 fired AND positive_satisfied == 0 → 'failure'
      2. L1↔L7 Ithesal OR L7↔Moon Ithesal              → 'effortless'
      3. L1 in 7th OR Moon in 7th                       → 'effort_based'
      4. otherwise                                       → 'conditional'
    """
    lagna_lord_name  = (judgment.get('querent_lord')  or {}).get('name', 'Lagna Lord')
    target_lord_name = (judgment.get('quesited_lord') or {}).get('name', '7th Lord')

    asp_l1_l7   = nakta_data.get('aspect_l1_lt') or {}
    asp_l7_moon = nakta_data.get('aspect_lt_moon') or {}
    l1_in_7th   = bool(nakta_data.get('l1_in_target'))
    moon_in_7th = bool(nakta_data.get('moon_in_target'))

    if karya.get('rule4_fired') and karya.get('positive_satisfied') == 0:
        return ('failure',
                'Significators are afflicted or combust with no positive Karya '
                'support — the proposal is unlikely to materialise.')

    if asp_l1_l7.get('yoga') == 'Ithesal' or asp_l7_moon.get('yoga') == 'Ithesal':
        if asp_l1_l7.get('yoga') == 'Ithesal':
            partner = f'{lagna_lord_name} (Lagna Lord)'
        else:
            partner = 'the Moon'
        return ('effortless',
                f"{target_lord_name} (7th lord) is in Ithesal with {partner} — "
                "the match materialises without strenuous effort.")

    if l1_in_7th or moon_in_7th:
        who = 'Lagna Lord' if l1_in_7th else 'The Moon'
        return ('effort_based',
                f"{who} occupies the 7th house — the match materialises only "
                "after a formal request or sustained effort.")

    return ('conditional',
            'No effortless or effort-based trigger fires; the result depends '
            'on circumstantial factors (Nakta bridges, transits).')


def _vivaha_derive_verdict_text(judgment, nakta_data, karya):
    """
    Replica of vivaha_judgment's verdict_text decision tree, including the
    nakta-rewrites-failure-to-conditional path and the Abhara downgrade band.

    Returns (verdict_text, final_verdict) — final_verdict may differ from
    judgment['verdict'] if Abhara forces a YES → YES_WITH_DELAYS downgrade
    that wasn't captured in the orchestrator's generic synthesis.
    """
    primitive = karya.get('verdict_primitive')
    modifier  = karya.get('verdict_modifier')
    verdict   = judgment.get('verdict')
    nakta     = nakta_data.get('nakta_bridge')
    abhara    = nakta_data.get('abhara_yoga')

    # Base verdict_text from primitive
    if primitive == 'failure' and not nakta:
        text = 'No — the proposal will not materialise'
        verdict = 'NO'
    elif primitive == 'failure' and nakta:
        text = f'Conditional — only via {nakta["bridge"]} as intermediary'
        verdict = 'CONDITIONAL'
    elif primitive == 'conditional':
        verdict = 'CONDITIONAL'
        if modifier == 'andha_parivartana':
            text = 'Conditional — Andha Parivartana (blind exchange) blocks the resolution'
        else:
            text = 'Conditional — depends on circumstantial support'
    elif primitive == 'success' and modifier == 'with_delays':
        verdict = 'YES_WITH_DELAYS'
        text = 'Yes — with initial delays or obstacles'
    elif primitive == 'success':
        verdict = 'YES'
        text = 'Yes — the proposal will materialise'
    elif primitive == 'confirmed' and modifier == 'with_delays':
        verdict = 'YES_WITH_DELAYS'
        text = 'Yes — confirmed, with initial delays'
    else:  # confirmed
        verdict = 'YES'
        text = 'Yes — strongly confirmed'

    # Abhara downgrade band — preserves legacy quirk
    if abhara and verdict in ('YES', 'YES_WITH_DELAYS'):
        if verdict == 'YES':
            verdict = 'YES_WITH_DELAYS'
            text = 'Yes — but with malefic friction (Abhara Yoga)'
        else:
            text = 'Yes — with delays AND malefic friction (Abhara Yoga)'

    return text, verdict


def _vivaha_derive_reciprocity_narrative(judgment, nakta_data):
    """
    Topic-faithful reciprocity narrative based on the Vivaha-specific overlay.
    Falls back to the overlay's stock text when no Lagna data is available.
    """
    findings = judgment.get('overlay_findings', {})
    overlay = findings.get('emotional_reciprocity', {}) or {}
    data = overlay.get('data') or {}
    # The overlay already produces topic-faithful narrative — use it directly
    return data.get('reciprocity_narrative') or overlay.get('narrative')


def _flatten_to_legacy_garbha(judgment: Dict, querent_gender: Optional[str]) -> Dict:
    """
    Map prashna_topic_judgment output → legacy garbha_judgment shape.

    Spreads each overlay's `data` into top-level keys while preserving the
    new `overlay_findings` structure underneath. /prashnareport's existing
    _build_garbha_user_prompt reads from the flat top-level keys.
    """
    findings = judgment.get('overlay_findings', {})

    def _data(name: str, key: str, default=None):
        return (findings.get(name, {}).get('data') or {}).get(key, default)

    nakta_data = findings.get('nakta_abhara_scan', {}).get('data') or {}

    return {
        'sub_module':           'garbha',
        'intent':               judgment.get('intent'),
        'verdict':              judgment.get('verdict'),
        'verdict_text':         judgment.get('verdict_text'),
        'verdict_modifier':     judgment.get('verdict_modifier'),
        'target_house':         judgment.get('target_house'),
        'target_role':          judgment.get('target_role'),
        'is_husband_pivot':     _data('husband_pivot_auto', 'is_husband_pivot', False),
        'is_lineage_query':     _data('lineage_query_check', 'is_lineage', False),
        'querent_gender':       querent_gender,
        'certainty_score':      judgment.get('certainty_score'),
        'certainty_band':       judgment.get('certainty_band'),
        'certainty_narrative':  judgment.get('certainty_narrative'),
        'core_catalyst':        judgment.get('core_catalyst'),
        'querent_lord':         judgment.get('querent_lord'),
        'quesited_lord':        judgment.get('quesited_lord'),
        # Tajik aspect + relay yogas
        'aspect_l1_lt':         nakta_data.get('aspect_l1_lt'),
        'nakta_bridge':         nakta_data.get('nakta_bridge'),
        'abhara_yoga':          nakta_data.get('abhara_yoga'),
        'yama_yoga':            nakta_data.get('yama_yoga'),
        'kamboola_yoga':        _data('kamboola_yoga', 'kamboola_yoga'),
        'gada_yoga':            _data('gada_yoga', 'gada_yoga'),
        # Sphuta layer
        'beeja_sphuta':         _data('beeja_kshetra_sphuta', 'beeja'),
        'kshetra_sphuta':       _data('beeja_kshetra_sphuta', 'kshetra'),
        'sphuta_active':        _data('beeja_kshetra_sphuta', 'sphuta_active'),
        'sphuta_effect':        _data('beeja_kshetra_sphuta', 'sphuta_effect'),
        # Mars + sterile + Rahu/Ketu
        'mars_in_target':       findings.get('mars_5_vitality_split', {}).get('fired', False),
        'mars_5th_risk':        _data('mars_5_vitality_split', 'mars_5_risk', False),
        'mars_5th_vitality':    _data('mars_5_vitality_split', 'mars_5_vitality', False),
        'target_cusp_sterile':  _data('sterile_sign_downgrade', 'target_cusp_sterile', False),
        'rahu_in_target':       _data('rahu_ketu_progeny_axis', 'rahu_in_target', False),
        'ketu_in_target':       _data('rahu_ketu_progeny_axis', 'ketu_in_target', False),
        # Eclipse
        'eclipse_proximity':    _data('eclipse_proximity_axis', 'eclipse_proximity'),
        # Core layers
        'karya_chain':          judgment.get('karya_chain'),
        'strength_scaling':     judgment.get('strength_scaling'),
        'bhava_bala_target':    judgment.get('bhava_bala_target'),
        'horary_to_natal':      judgment.get('horary_to_natal'),
        'long_horizon':         judgment.get('long_horizon'),
    }


# -----------------------------------------------------------------
# PHASE 2: VIVAHA JUDGMENT ENDPOINT
# -----------------------------------------------------------------

@router.post("/prashna_vivaha")
def prashna_vivaha(req: PrashnaVivahaRequest) -> Dict:
    """
    Cast a Prashna chart AND compute the Vivaha (Marriage) judgment package.

    **Phase 4B**: this is now a thin backward-compatibility wrapper around
    the canonical `/prashna_topic` orchestrator. The response shape (with
    'vivaha' key + legacy field names like `bhava_bala_7th`, `match_type`,
    `aspect_l1_l7`) is preserved via `_flatten_to_legacy_vivaha()` so
    existing clients (frontend + /prashnareport) require no changes.

    New canonical equivalent:
        POST /prashna_topic  { "topic_id": "vivaha", ... }
    """
    cast = _cast_chart_pipeline(req)

    # Diagnostic layers (same as before, kept for legacy response shape)
    active_chart = cast['active_chart']
    sincerity = compute_sincerity_score(active_chart,
                                        natal_lagna_sign=req.natal_lagna_sign)
    avasthas = compute_avasthas(active_chart)
    aspects = detect_all_aspects(active_chart)
    bhava_bala = {str(h): compute_bhava_bala(active_chart, h) for h in range(1, 13)}

    # Route through the generic orchestrator
    horizon_text = req.full_query or req.query_text
    judgment = prashna_topic_judgment(
        active_chart, 'vivaha',
        natal_lagna_sign=req.natal_lagna_sign,
        full_query=horizon_text,
        query_text=req.query_text,
    )

    # Flatten back to legacy 'vivaha' shape for backward compat
    vivaha = _flatten_to_legacy_vivaha(judgment)

    return {
        'base_chart':   cast['base_chart'],
        'active_chart': cast['active_chart'],
        'sincerity':    sincerity,
        'avasthas':     avasthas,
        'aspects':      aspects,
        'bhava_bala':   bhava_bala,
        'vivaha':       vivaha,
        'cast_meta': {
            'jd_ut':              cast['jd_info']['jd_ut'],
            'datetime_utc_iso':   cast['jd_info']['datetime_utc_iso'],
            'datetime_local_iso': cast['jd_info']['datetime_local_iso'],
            'timezone_used':      cast['jd_info']['timezone_used'],
            'casting_note':       cast['casting_note'],
            'phonetic_match':     cast['phon'],
            'ayanamsha':          'Lahiri',
            'house_system':       'Whole Sign',
            'nodes':              'Mean',
        },
    }


# -----------------------------------------------------------------
# PHASE 3B: /prashna_garbha endpoint
# Locked corpus: garbha_corpus_locked.md
# Mirrors /prashna_vivaha shape with Garbha-specific layers:
#   - querent_gender + Beeja/Kshetra Sphuta computation
#   - intent classification (5 intents) with optional override
#   - garbha_mode sincerity (combust Moon, Saturn-5 + Moon aspect,
#     Jupiter L/7, Sun-5, Mars-Saturn, eclipse cap, natal-5 supersession)
#   - Verdict modifier INCONCLUSIVE_RECAST_REQUIRED for ambiguous
#     current-pregnancy queries
# -----------------------------------------------------------------

@router.post("/prashna_garbha")
def prashna_garbha(req: PrashnaGarbhaRequest) -> Dict:
    """
    Cast a Prashna chart AND compute the full Garbha (Conception) judgment package.

    Primary endpoint for the Vaivahika · Garbha War Room. Returns everything
    /prashna_chart returns, plus a 'garbha' block containing:
      - verdict           (YES / YES_WITH_DELAYS / CONDITIONAL_MEDICAL /
                           CONDITIONAL_THIRD_PARTY / HIGH_RISK / NO)
      - verdict_text      (human-readable verdict line)
      - verdict_modifier  ('INCONCLUSIVE_RECAST_REQUIRED' or None)
      - intent            (classified intent: one of 5 codes)
      - target_house      (5 normally, 9 for lineage queries, 11 for husband pivot)
      - target_role       (human-readable description of the target)
      - is_husband_pivot  (bool — pivoted to wife's 5th = 11th overall)
      - is_lineage_query  (bool — 9th-house exception fired)
      - querent_gender    (echoed back)
      - certainty_score, certainty_band, certainty_narrative
      - core_catalyst     (decisive yoga driving the verdict)
      - querent_lord      (L1 with Avastha + degree_band + synthesis_label)
      - quesited_lord     (L_target with Avastha + degree_band + synthesis_label
                           + is_heavily_combust for INCONCLUSIVE check)
      - aspect_l1_lt      (Tajik pairwise reading)
      - nakta_bridge      (relay with bridge_role + near_misses)
      - abhara_yoga       (malefic interference on the link)
      - yama_yoga         (midpoint binder when no direct aspect)
      - kamboola_yoga     (Moon as cosmic proxy when Vimshopaka ≥ 12)
      - gada_yoga         (consecutive-Kendra structural compression)
      - beeja_sphuta, kshetra_sphuta (both computed; gender-active marked)
      - sphuta_active     (the gender-relevant Sphuta dict)
      - sphuta_effect     (bonus_15 / cap_50 / None)
      - mars_in_target, mars_5th_risk, mars_5th_vitality
      - target_cusp_sterile (Alpa-Putra downgrade flag)
      - rahu_in_target, ketu_in_target
      - eclipse_proximity (None or full eclipse dict)
      - karya_chain, strength_scaling, bhava_bala_target
      - horary_to_natal   (shift to natal chart if natal_lagna_sign provided)
      - long_horizon      (Garbha-specific keywords appended)
    """

    # ===== 1. Cast chart via shared pipeline =====
    cast = _cast_chart_pipeline(req)
    active_chart = cast['active_chart']
    jd_ut = cast['jd_info']['jd_ut']

    # ===== 2. Diagnostic layers =====
    sincerity = compute_sincerity_score(active_chart,
                                        natal_lagna_sign=req.natal_lagna_sign,
                                        garbha_mode=True,
                                        jd_ut=jd_ut)
    avasthas = compute_avasthas(active_chart)
    aspects = detect_all_aspects(active_chart)
    bhava_bala = {str(h): compute_bhava_bala(active_chart, h) for h in range(1, 13)}

    # ===== 3. Route through the generic orchestrator =====
    horizon_text = req.full_query or req.query_text
    judgment = prashna_topic_judgment(
        active_chart, 'garbha',
        querent_gender=req.querent_gender,
        intent=req.intent,
        natal_lagna_sign=req.natal_lagna_sign,
        full_query=horizon_text,
        query_text=req.query_text,
    )

    # ===== 4. Flatten to legacy 'garbha' shape =====
    garbha = _flatten_to_legacy_garbha(judgment, req.querent_gender)

    return {
        'base_chart':   cast['base_chart'],
        'active_chart': active_chart,
        'sincerity':    sincerity,
        'avasthas':     avasthas,
        'aspects':      aspects,
        'bhava_bala':   bhava_bala,
        'garbha':       garbha,
        'cast_meta': {
            'jd_ut':                jd_ut,
            'datetime_utc_iso':     cast['jd_info']['datetime_utc_iso'],
            'datetime_local_iso':   cast['jd_info']['datetime_local_iso'],
            'timezone_used':        cast['jd_info']['timezone_used'],
            'casting_note':         cast['casting_note'],
            'phonetic_match':       cast['phon'],
            'querent_gender':       req.querent_gender,
            'intent_resolved':      garbha.get('intent'),
            'intent_was_overridden': req.intent is not None,
            'ayanamsha':            'Lahiri',
            'house_system':         'Whole Sign',
            'nodes':                'Mean',
        },
    }


# -----------------------------------------------------------------
# PHASE 4B: /prashna_topic — CANONICAL endpoint
# Generic, registry-driven entry point for all current and future
# sub-modules. Routes new traffic here; legacy /prashna_vivaha and
# /prashna_garbha are wrappers around this same orchestrator.
# -----------------------------------------------------------------

@router.post("/prashna_topic")
def prashna_topic(req: PrashnaTopicRequest) -> Dict:
    """
    Canonical Prashna sub-module endpoint.

    Casts a chart from `chart_data` and runs the registry-driven judgment
    for `topic_id`, with topic-specific inputs validated against the spec
    in PRASHNA_TOPICS.

    Returns:
        {
            "topic_id":     str,            # echoed back
            "container":    str,            # 'vaivahika' / 'karmika' / ...
            "base_chart":   Dict,
            "active_chart": Dict,
            "sincerity":    Dict,
            "avasthas":     Dict,
            "aspects":      Dict,
            "bhava_bala":   Dict,           # all 12 houses
            "judgment":     Dict,           # full orchestrator output (new shape)
            "cast_meta":    Dict,
        }
    """
    if req.topic_id not in PRASHNA_TOPICS:
        raise HTTPException(
            status_code=400,
            detail=(f"Unknown topic_id '{req.topic_id}'. "
                    f"Registered topics: {sorted(PRASHNA_TOPICS)}")
        )

    spec = PRASHNA_TOPICS[req.topic_id]

    # ===== 1. Cast chart from the nested chart_data block =====
    cast = _cast_chart_pipeline(req.chart_data)
    active_chart = cast['active_chart']
    jd_ut = cast['jd_info']['jd_ut']

    # ===== 2. Diagnostic layers (sincerity_mode from registry) =====
    sincerity_mode = spec.get('sincerity_mode', 'standard')
    sincerity = compute_sincerity_score(
        active_chart,
        natal_lagna_sign=req.topic_inputs.get('natal_lagna_sign'),
        garbha_mode=(sincerity_mode == 'garbha'),
        jd_ut=jd_ut,
    )
    avasthas = compute_avasthas(active_chart)
    aspects = detect_all_aspects(active_chart)
    bhava_bala = {str(h): compute_bhava_bala(active_chart, h) for h in range(1, 13)}

    # ===== 3. Run the orchestrator =====
    try:
        judgment = prashna_topic_judgment(
            active_chart, req.topic_id, **req.topic_inputs
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        'topic_id':       req.topic_id,
        'container':      judgment.get('container'),
        'base_chart':     cast['base_chart'],
        'active_chart':   active_chart,
        'sincerity':      sincerity,
        'avasthas':       avasthas,
        'aspects':        aspects,
        'bhava_bala':     bhava_bala,
        'judgment':       judgment,  # NEW CANONICAL SHAPE (overlay_findings, verdict_trace, etc.)
        'cast_meta': {
            'jd_ut':              jd_ut,
            'datetime_utc_iso':   cast['jd_info']['datetime_utc_iso'],
            'datetime_local_iso': cast['jd_info']['datetime_local_iso'],
            'timezone_used':      cast['jd_info']['timezone_used'],
            'casting_note':       cast['casting_note'],
            'phonetic_match':     cast['phon'],
            'topic_inputs_used':  req.topic_inputs,
            'ayanamsha':          'Lahiri',
            'house_system':       'Whole Sign',
            'nodes':              'Mean',
        },
    }


@router.get("/prashna_topics")
def prashna_topics_registry() -> Dict:
    """
    Returns the public registry — frontend reads this to dynamically build
    casting forms (required_inputs / optional_inputs / target_house etc.)
    per Atul's "single source of truth" payload contract.
    """
    return {
        'topics': {
            tid: {
                'display_name':    spec['display_name'],
                'sanskrit_name':   spec.get('sanskrit_name'),
                'container':       spec['container'],
                'target_house':    spec['target_house'],
                'target_role':     spec['target_role'],
                'required_inputs': spec.get('required_inputs', []),
                'optional_inputs': spec.get('optional_inputs', []),
                'verdict_states':  spec.get('verdict_states', []),
                'narrative_tone':  spec.get('narrative_tone'),
            }
            for tid, spec in PRASHNA_TOPICS.items()
        }
    }


# -----------------------------------------------------------------
# PHASE 2: AI NARRATIVE ENDPOINT (3-Tranche + Action Cards)
# -----------------------------------------------------------------

import os
import json as _json

# Anthropic SDK is imported lazily — only when /prashnareport is called —
# so the module loads even if the SDK isn't yet installed in some envs.
_anthropic_client = None

def _get_anthropic_client():
    global _anthropic_client
    if _anthropic_client is None:
        import anthropic
        _anthropic_client = anthropic.Anthropic(
            api_key=os.environ.get("ANTHROPIC_API_KEY")
        )
    return _anthropic_client


# Locked AI model per Atul's stack-wide decision
# Locked AI model — imported from prashna_narratives via PRASHNA_AI_MODEL.
# System prompts and per-topic user-prompt builders live in prashna_narratives.py
# and are dispatched via generate_narrative(). See Phase 4C refactor.


# -----------------------------------------------------------------
# PHASE 2 + 4C: AI NARRATIVE ENDPOINT
# -----------------------------------------------------------------
# Topic dispatch: reads narrative_tone from PRASHNA_TOPICS[topic_id],
# pairs with the user-prompt builder registered in
# prashna_narratives.USER_PROMPT_BUILDERS, generates the 3-tranche
# narrative + 3 action cards via Claude.
#
# Accepts both the canonical `topic_id` field and the legacy
# `sub_module` field for backward compatibility with existing
# /prashna_vivaha and /prashna_garbha clients.
# -----------------------------------------------------------------

@router.post("/prashnareport")
def prashnareport(req: PrashnaReportRequest) -> Dict:
    """
    Generate the AI narrative for any Prashna sub-module judgment.

    Dispatches via prashna_narratives.generate_narrative() which:
      1. Reads the narrative_tone from PRASHNA_TOPICS[topic_id]
      2. Looks up the matching system prompt in NARRATIVE_TONES
      3. Invokes the topic's registered user-prompt builder
      4. Calls Claude, parses the JSON response, validates required keys
    """
    # Resolve topic_id from either field (topic_id wins if both provided)
    topic_id = req.topic_id or req.sub_module
    if topic_id is None:
        raise HTTPException(
            status_code=400,
            detail="Must provide either 'topic_id' or 'sub_module'."
        )

    if topic_id not in PRASHNA_TOPICS:
        raise HTTPException(
            status_code=400,
            detail=(f"Unknown topic_id/sub_module '{topic_id}'. "
                    f"Registered: {sorted(PRASHNA_TOPICS)}")
        )

    if topic_id not in USER_PROMPT_BUILDERS:
        raise HTTPException(
            status_code=501,
            detail=(f"Topic '{topic_id}' is registered in PRASHNA_TOPICS but has no "
                    f"narrative builder yet. Add an entry to "
                    f"prashna_narratives.USER_PROMPT_BUILDERS.")
        )

    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise HTTPException(
            status_code=500,
            detail="ANTHROPIC_API_KEY not configured on the server."
        )

    try:
        client = _get_anthropic_client()
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="anthropic SDK is not installed on the server. "
                   "Add 'anthropic' to requirements.txt and redeploy."
        )

    try:
        result = generate_narrative(
            anthropic_client=client,
            topic_id=topic_id,
            judgment=req.judgment,
            query_text=req.query_text,
            cast_meta=req.cast_meta,
            topic_inputs=req.topic_inputs,
        )
    except NarrativeError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"LLM call failed: {type(exc).__name__}: {str(exc)[:300]}"
        )

    return {
        "topic_id":   topic_id,
        "sub_module": topic_id,  # legacy echo for backward compat
        "narrative":  result["narrative"],
        "model":      result["model"],
        "usage":      result["usage"],
    }



# -----------------------------------------------------------------
# Convenience: ping endpoint for the Prashna module
# -----------------------------------------------------------------

@router.get("/prashna_health")
def prashna_health() -> Dict:
    """Verify the Prashna module is loaded and engine functions are importable."""
    return {
        'status': 'ok',
        'engine': 'prashna_engine',
        'capabilities': [
            'time_based_casting',
            'phonetic_casting',
            'multi_query_5_anchor',
            'sincerity_check',
            'sincerity_garbha_mode',
            'avastha_10_state',
            'avastha_band_synthesis',
            'bhava_bala_matrix',
            'tajik_aspect_engine_hardcoded_velocity',
            'shadow_ratio_from_sun_altitude',
            'karya_success_chain',
            'tajik_strength_scaling',
            'horary_to_natal_shift',
            'vaivahika_vivaha_judgment',
            'vaivahika_garbha_judgment',
            'beeja_kshetra_sphuta',
            'tajik_vimshopaka_surrogate',
            'kamboola_yoga_detection',
            'gada_yoga_detection',
            'eclipse_proximity_axis_check',
            'garbha_intent_classifier',
            'husband_pivot_auto_detection',
            'ai_narrative_3_tranche',
            'ai_narrative_garbha_tonal_shift',
            # Phase 4 — registry-driven orchestrator
            'prashna_topic_orchestrator',
            'prashna_topics_registry_endpoint',
            'overlay_based_judgment_engine',
        ],
        'registered_topics': sorted(PRASHNA_TOPICS),
        'max_queries_per_chart': MAX_QUERIES_PER_CHART,
        'ai_model': PRASHNA_AI_MODEL,
    }


# ================== END PASTE ==================
