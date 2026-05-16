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
from typing import Dict, List, Optional, Literal

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


class PrashnaReportRequest(BaseModel):
    """
    Request body for /prashnareport. Accepts a complete judgment package
    (the dict returned by /prashna_vivaha or /prashna_garbha) plus optional
    persona context, and returns a 3-tranche narrative + 3 action cards via
    the LLM.
    """
    sub_module: Literal['vivaha', 'garbha'] = Field(
        'vivaha',
        description="Which Vaivahika sub-module produced the judgment. "
                    "Routes to the matching system prompt + user-prompt builder."
    )
    judgment: Dict = Field(
        ...,
        description="The full judgment dict — from /prashna_vivaha's 'vivaha' key, "
                    "or /prashna_garbha's 'garbha' key."
    )
    query_text: Optional[str] = Field(
        None, description="The original question text (for narrative context)"
    )
    cast_meta: Optional[Dict] = Field(
        None, description="Cast metadata (JD, datetime, place_name) for narrative context"
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
# PHASE 2: VIVAHA JUDGMENT ENDPOINT
# -----------------------------------------------------------------

@router.post("/prashna_vivaha")
def prashna_vivaha(req: PrashnaVivahaRequest) -> Dict:
    """
    Cast a Prashna chart AND compute the full Vivaha (Marriage) judgment package.

    This is the primary endpoint for the Vaivahika · Vivaha War Room. It returns
    everything /prashna_chart returns, plus a 'vivaha' block containing:
      - verdict           (YES / YES_WITH_DELAYS / CONDITIONAL / NO)
      - verdict_text      (human-readable verdict line)
      - certainty_score   (0/25/50/75/100 — Tajik strength scaling)
      - core_catalyst     (the decisive yoga driving the verdict)
      - querent_lord      (Lagna Lord with Avastha + house + combust state)
      - quesited_lord     (7th Lord with Avastha + house + combust state)
      - aspect_l1_l7      (full Tajik pairwise reading between the two lords)
      - nakta_bridge      (intermediary planet if no direct aspect)
      - match_type        (effortless / effort_based / conditional / failure)
      - third_party_interference  (8L/3L/4L malefic in 7th list)
      - emotional_reciprocity     (mutual_love / past_engagement / discord_short / disengaged)
      - karya_chain               (the 4-rule success chain detail)
      - strength_scaling          (composite certainty narrative)
      - bhava_bala_7th            (target house strength)
      - horary_to_natal           (shift to natal chart, if natal_lagna_sign provided)
    """

    # ===== 1. Cast chart (identical logic to /prashna_chart) =====
    jd_info = _resolve_jd_ut(req.date, req.time, req.timezone_str)
    jd_ut = jd_info['jd_ut']
    planets = _compute_planet_positions(jd_ut)

    casting_note = ''
    if req.lagna_override is not None:
        lagna_sign = int(req.lagna_override) % 12
        lagna_lon = lagna_sign * 30.0
        casting_note = f"Manual Lagna override: {SIGNS[lagna_sign]}"
        phon = None
    elif req.mode == 'phonetic':
        if not req.query_text:
            raise HTTPException(status_code=400,
                                detail="query_text is required when mode='phonetic'")
        phon = phonetic_to_lagna_sign(req.query_text)
        if 'error' in phon:
            lagna_lon = _compute_ascendant(jd_ut, req.lat, req.lon)
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
        lagna_lon = _compute_ascendant(jd_ut, req.lat, req.lon)
        lagna_sign = int(lagna_lon // 30) % 12
        casting_note = (f"Time-based Lagna: {SIGNS[lagna_sign]} "
                        f"({lagna_lon - lagna_sign*30:.2f}° into sign)")
        phon = None

    houses = _build_whole_sign_houses(lagna_sign, planets)
    sun_alt = compute_sun_altitude(jd_ut, req.lat, req.lon, planets['Sun']['longitude'])
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
        'lat': req.lat,
        'lon': req.lon,
        'place_name': req.place_name,
        'sun_altitude': round(sun_alt, 4),
        'shadow_ratio': round(shadow, 4) if shadow >= 0 else None,
        'sun_above_horizon': sun_above_horizon,
        'cast_mode': req.mode,
        'casting_note': casting_note,
    }

    # Active chart — Vivaha always uses Q1 anchor (Prashna Lagna).
    # Multi-query rotation is reserved for the diagnostic Hub.
    active_chart = base_chart

    # ===== 2. Diagnostic layers =====
    sincerity = compute_sincerity_score(active_chart,
                                        natal_lagna_sign=req.natal_lagna_sign)
    avasthas = compute_avasthas(active_chart)
    aspects = detect_all_aspects(active_chart)
    bhava_bala = {
        str(h): compute_bhava_bala(active_chart, h) for h in range(1, 13)
    }

    # ===== 3. Vivaha judgment =====
    # Long-horizon detection uses the FULL question text. In phonetic mode,
    # the frontend sends just the first word as query_text (for Lagna derivation)
    # and the complete sentence as full_query. Fall back to query_text otherwise.
    horizon_text = req.full_query or req.query_text
    vivaha = vivaha_judgment(active_chart,
                             natal_lagna_sign=req.natal_lagna_sign,
                             query_text=horizon_text)

    return {
        'base_chart': base_chart,
        'active_chart': active_chart,
        'sincerity': sincerity,
        'avasthas': avasthas,
        'aspects': aspects,
        'bhava_bala': bhava_bala,
        'vivaha': vivaha,
        'cast_meta': {
            'jd_ut': jd_ut,
            'datetime_utc_iso': jd_info['datetime_utc_iso'],
            'datetime_local_iso': jd_info['datetime_local_iso'],
            'timezone_used': jd_info['timezone_used'],
            'casting_note': casting_note,
            'phonetic_match': phon,  # vibrational_accuracy + accuracy_note (None if not phonetic)
            'ayanamsha': 'Lahiri',
            'house_system': 'Whole Sign',
            'nodes': 'Mean',
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

    # ===== 1. Cast chart (identical logic to /prashna_vivaha) =====
    jd_info = _resolve_jd_ut(req.date, req.time, req.timezone_str)
    jd_ut = jd_info['jd_ut']
    planets = _compute_planet_positions(jd_ut)

    casting_note = ''
    if req.lagna_override is not None:
        lagna_sign = int(req.lagna_override) % 12
        lagna_lon = lagna_sign * 30.0
        casting_note = f"Manual Lagna override: {SIGNS[lagna_sign]}"
        phon = None
    elif req.mode == 'phonetic':
        if not req.query_text:
            raise HTTPException(status_code=400,
                                detail="query_text is required when mode='phonetic'")
        phon = phonetic_to_lagna_sign(req.query_text)
        if 'error' in phon:
            lagna_lon = _compute_ascendant(jd_ut, req.lat, req.lon)
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
        lagna_lon = _compute_ascendant(jd_ut, req.lat, req.lon)
        lagna_sign = int(lagna_lon // 30) % 12
        casting_note = (f"Time-based Lagna: {SIGNS[lagna_sign]} "
                        f"({lagna_lon - lagna_sign*30:.2f}° into sign)")
        phon = None

    houses = _build_whole_sign_houses(lagna_sign, planets)
    sun_alt = compute_sun_altitude(jd_ut, req.lat, req.lon, planets['Sun']['longitude'])
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
        'lat': req.lat,
        'lon': req.lon,
        'place_name': req.place_name,
        'sun_altitude': round(sun_alt, 4),
        'shadow_ratio': round(shadow, 4) if shadow >= 0 else None,
        'sun_above_horizon': sun_above_horizon,
        'cast_mode': req.mode,
        'casting_note': casting_note,
    }
    active_chart = base_chart  # Garbha uses Q1 anchor like Vivaha

    # ===== 2. Diagnostic layers (sincerity in garbha_mode + jd_ut for eclipse cap) =====
    sincerity = compute_sincerity_score(active_chart,
                                        natal_lagna_sign=req.natal_lagna_sign,
                                        garbha_mode=True,
                                        jd_ut=jd_ut)
    avasthas = compute_avasthas(active_chart)
    aspects = detect_all_aspects(active_chart)
    bhava_bala = {
        str(h): compute_bhava_bala(active_chart, h) for h in range(1, 13)
    }

    # ===== 3. Garbha judgment =====
    # Long-horizon + intent classification + husband-pivot detection all
    # use the FULL question text. In phonetic mode, query_text holds the
    # first word (Lagna source); full_query holds the complete sentence.
    horizon_text = req.full_query or req.query_text
    garbha = garbha_judgment(active_chart,
                             natal_lagna_sign=req.natal_lagna_sign,
                             query_text=req.query_text,
                             full_query=horizon_text,
                             intent=req.intent,
                             querent_gender=req.querent_gender)

    return {
        'base_chart': base_chart,
        'active_chart': active_chart,
        'sincerity': sincerity,
        'avasthas': avasthas,
        'aspects': aspects,
        'bhava_bala': bhava_bala,
        'garbha': garbha,
        'cast_meta': {
            'jd_ut': jd_ut,
            'datetime_utc_iso': jd_info['datetime_utc_iso'],
            'datetime_local_iso': jd_info['datetime_local_iso'],
            'timezone_used': jd_info['timezone_used'],
            'casting_note': casting_note,
            'phonetic_match': phon,
            'querent_gender': req.querent_gender,
            'intent_resolved': garbha.get('intent'),
            'intent_was_overridden': req.intent is not None,
            'ayanamsha': 'Lahiri',
            'house_system': 'Whole Sign',
            'nodes': 'Mean',
        },
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
PRASHNA_AI_MODEL = "claude-sonnet-4-6"


VIVAHA_NARRATIVE_SYSTEM_PROMPT = """You are Phalit, a senior Vedic Jyotisha consultant trained in the Tajik (Prashna) school. You are advising a sincere, professional querent in their 30s-40s — not someone seeking entertainment or daily horoscopes. They face a real life-relationship decision and need an honest, structured, action-oriented reading.

TONE & STYLE:
- Professional, dignified, never melodramatic. No "destiny," no "cosmic," no "the universe is telling you."
- Translate every Sanskrit term inline the first time you use it (e.g. "Ithesal — an applying aspect within orb").
- Cite the actual planets and houses from the chart — never speak in generalities.
- Address the querent directly in second person ("you", "your partner"), but never name them.
- Action-oriented. Every observation must connect to "so what should you do."
- Honest about negative indicators. If the verdict is NO or CONDITIONAL, do not soften it into false hope.

CONSISTENCY REQUIREMENTS (per Atul's audit):
1. PLANETARY STATE CONSISTENCY — If a planet's synthesis_label is "Thwarted Power" (raw strength + affliction), describe it as a high-stakes struggle, NOT as weakness or incapacity. If "Brittle Failure", describe as desperate end-game. If "Building Power", describe as gathering momentum. The synthesis_label IS the lens — do not contradict it with "weak/feeble" or "strong/competent" language that contradicts the label.

2. TIMING COHERENCE — Use a SINGLE temporal framework across all three tranches. If the macro-horizon is a Saturn cycle (months-to-years), reference it consistently. Micro-checks (e.g. "re-evaluate in 4 months") must be explicitly nested under the macro-horizon, not presented as alternative timelines. Example of CORRECT framing: "While the structural matter won't resolve until [macro window] when Saturn shifts out of Pariheena, you should take an emotional pulse-check at [micro window] as the Moon re-crosses the natal angle." NEVER give two timelines that imply different end-points.

3. NATAL-PRASHNA HANDSHAKE — If the judgment contains a horary_to_natal shift that activates a meaningful natal house, name it explicitly in the narrative (e.g. "This question lands in your natal 10th house — your career/status axis"). The Sincerity section already credits this; the Arc tranche must reinforce it.

OUTPUT FORMAT:
Return ONLY a single valid JSON object. No preamble, no markdown fences, no commentary outside the JSON. The JSON must have exactly these keys:
{
  "tranche_arc":       "150-200 word narrative of the relationship dynamic — who is putting in effort, what is the emotional state of each lord (USE the synthesis_label, not the raw avastha), the aspect/Nakta/Yama/Abhara structure, and what story the chart tells. If the horary_to_natal shift activates a meaningful natal house, name it.",
  "tranche_strategy":  "150-200 word strategic guidance — how to handle the matchmaking / engagement / proposal process given the indicators. References the match_type, third_party_interference (if any), and emotional_reciprocity. Tells the querent what posture to adopt: assert, wait, mediate, withdraw. Time-references must align with tranche_timeline.",
  "tranche_timeline":  "100-150 word timeline using the actual planetary timing indicators. State the SINGLE macro-horizon (e.g. 'Saturn's traversal of Pisces, roughly through [date]') AND any nested micro-checks (e.g. 'Moon's monthly return to your natal angle around [date]'). NEVER contradict the strategy tranche's timing. Give directional windows, not exact dates unless the chart strongly indicates them.",
  "platinum_rule":     "30-50 word directive — the single most important thing the querent should DO. Action verb leading. Concrete.",
  "friction_gate":     "30-50 word warning — the single most important thing the querent should AVOID. Concrete trigger or behaviour.",
  "sensory_remedy":    "30-50 word grounding / remedial practice. Lifestyle, dietary, or temporal (auspicious day/hour). May reference a planet's day (Friday for Venus, etc.) but never prescribe gems or expensive remedies."
}

Do not include any other keys. Do not nest. Do not use markdown inside string values."""


def _build_vivaha_user_prompt(judgment: Dict,
                              query_text: Optional[str],
                              cast_meta: Optional[Dict]) -> str:
    """Compose the user prompt for the Vivaha narrative. Inlines all judgment data."""

    q = judgment.get('querent_lord', {})
    qs = judgment.get('quesited_lord', {})
    asp = judgment.get('aspect_l1_l7', {})
    nakta = judgment.get('nakta_bridge')
    karya = judgment.get('karya_chain', {})
    strength = judgment.get('strength_scaling', {})
    bhava7 = judgment.get('bhava_bala_7th', {})
    h2n = judgment.get('horary_to_natal', {})
    catalyst = judgment.get('core_catalyst', {})
    interference = judgment.get('third_party_interference', [])

    place = (cast_meta or {}).get('place_name') or 'the querent\'s location'
    when_local = (cast_meta or {}).get('datetime_local_iso', 'now')

    lines = [
        f"# VIVAHA PRASHNA — JUDGMENT PACKAGE",
        f"",
        f"## Querent's Question",
        f"\"{query_text or '(no text provided)'}\"",
        f"",
        f"## Cast Context",
        f"- Cast at: {when_local}",
        f"- Place: {place}",
        f"",
        f"## Verdict (already computed by engine)",
        f"- Verdict: **{judgment.get('verdict')}** — {judgment.get('verdict_text')}",
        f"- Certainty Score: {judgment.get('certainty_score')}% ({judgment.get('certainty_band')})",
        f"- Certainty Narrative: {judgment.get('certainty_narrative')}",
        f"",
        f"## Significators (USE synthesis_label as the dominant frame — do not contradict it)",
        f"- **Querent (Lagna Lord)**: {q.get('name')} in {q.get('sign')} (house {q.get('house')}).",
        f"  - Avastha: {q.get('avastha')} — {q.get('condition')}",
        f"  - Degree band: {(q.get('degree_band') or {}).get('band_name', '—')} ({(q.get('degree_band') or {}).get('band_english', '—')})",
        f"  - **Synthesis (use this frame): {q.get('synthesis_label')}** — {q.get('synthesis_narrative')}",
        f"  - Outcome signature: {q.get('outcome')}. Combust: {q.get('is_combust')}.",
        f"- **Quesited (7th Lord)**: {qs.get('name')} in {qs.get('sign')} (house {qs.get('house')}).",
        f"  - Avastha: {qs.get('avastha')} — {qs.get('condition')}",
        f"  - Degree band: {(qs.get('degree_band') or {}).get('band_name', '—')} ({(qs.get('degree_band') or {}).get('band_english', '—')})",
        f"  - **Synthesis (use this frame): {qs.get('synthesis_label')}** — {qs.get('synthesis_narrative')}",
        f"  - Outcome signature: {qs.get('outcome')}. Combust: {qs.get('is_combust')}.",
        f"",
        f"## Tajik Aspect (Lagna Lord ↔ 7th Lord)",
        f"- Yoga: {asp.get('yoga', 'None')}",
        f"- Within orb: {asp.get('within_orb', False)}",
        f"- Orb: {asp.get('orb_used', '—')}°, separation {asp.get('absolute_separation', '—')}°",
        f"- Aspect narrative: {asp.get('narrative', '—')}",
    ]

    if nakta:
        bridge_label = nakta.get('bridge') or '(no qualifying bridge)'
        lines += [
            f"",
            f"## Nakta Bridge (third-planet relay)",
            f"- Bridge planet: {bridge_label}",
            f"- Bridge role: {nakta.get('bridge_role') or '—'}",
            f"- Role narrative: {nakta.get('bridge_role_narrative') or '—'}",
            f"- Narrative: {nakta.get('narrative')}",
        ]
        near_misses = nakta.get('near_misses') or []
        if near_misses:
            lines.append(f"- Near-misses (candidates that almost qualified):")
            for nm in near_misses:
                lines.append(f"  - {nm.get('narrative', '—')}")

    abhara = judgment.get('abhara_yoga')
    if abhara:
        lines += [
            f"",
            f"## Abhara Yoga (malefic interference on a valid link)",
            f"- Severity: {abhara.get('severity')}",
            f"- Narrative: {abhara.get('narrative')}",
        ]
        for b in (abhara.get('blockers') or [])[:3]:
            lines.append(f"  - {b.get('malefic')} ({b.get('mode')}): {b.get('narrative')}")

    yama = judgment.get('yama_yoga')
    if yama:
        lines += [
            f"",
            f"## Yama Yoga (midpoint binder — forceful/structural compulsion)",
            f"- Severity: {yama.get('severity')}",
            f"- Narrative: {yama.get('narrative')}",
        ]
        for b in (yama.get('binders') or [])[:2]:
            lines.append(f"  - {b.get('binder')} at midpoint offset {b.get('midpoint_offset_deg')}°: {b.get('narrative')}")

    lines += [
        f"",
        f"## Core Catalyst",
        f"- Yoga: {catalyst.get('yoga')}",
        f"- Between: {' & '.join(catalyst.get('between', []))}",
        f"- Narrative: {catalyst.get('narrative')}",
        f"",
        f"## Karya Success Chain",
        f"- Positive rules satisfied: {karya.get('positive_satisfied', 0)} / 3",
        f"- Verdict primitive: {karya.get('verdict_primitive')}",
        f"- Verdict modifier: {karya.get('verdict_modifier')}",
        f"- Rule details: {karya.get('rule_detail', '—')}",
        f"",
        f"## Match Type & Reciprocity",
        f"- Match type: {judgment.get('match_type')} — {judgment.get('match_narrative')}",
        f"- Emotional reciprocity: {judgment.get('emotional_reciprocity')} — {judgment.get('reciprocity_narrative')}",
        f"",
        f"## Bhava Bala — 7th House",
        f"- Net strength: {bhava7.get('net_strength_pct', '—')}% ({bhava7.get('verdict', '—')})",
        f"- Gross: {bhava7.get('gross_strength_pct', '—')}%, afflictions: {len(bhava7.get('malefic_afflictions', []))}",
    ]

    if interference:
        lines += [f"", f"## Third-Party Interference"]
        for itf in interference:
            lines.append(f"- {itf.get('type')}: {itf.get('trigger')}")

    if h2n and 'error' not in h2n:
        lines += [
            f"",
            f"## Horary-to-Natal Shift (NAME THIS NATAL HOUSE in tranche_arc per consistency rule #3)",
            f"- House shift: {h2n.get('shift')} houses",
            f"- Activated natal house: {h2n.get('activated_natal_house')}",
            f"- Flourishing zone: {h2n.get('zone_label')}",
            f"- Zone narrative: {h2n.get('zone_narrative')}",
        ]

    lh = judgment.get('long_horizon') or {}
    if lh.get('is_long_horizon'):
        lines += [
            f"",
            f"## Horizon Boundary (CRITICAL — incorporate into tranche_timeline)",
            f"- Long-horizon keyword matched: \"{lh.get('matched_keyword')}\"",
            f"- The question implies a multi-decade horizon; Prashna's 6-12 month window",
            f"  cannot answer it on its own. Acknowledge this boundary explicitly in",
            f"  tranche_timeline. Frame the verdict as 'current trajectory' rather than",
            f"  'lifelong forecast'. Recommend D-9/D-30 follow-up for the full horizon.",
        ]

    lines += [
        f"",
        f"---",
        f"",
        f"Produce the 3-tranche narrative and 3 action cards now. JSON only, no other text.",
    ]

    return "\n".join(lines)


# -----------------------------------------------------------------
# PHASE 3C — GARBHA AI NARRATIVE
# Reference weighting hardcoded: Prashna Marga > Tajik Neelkanthi > Phaladeepika
# Tonal shift from Vivaha: more tender, less transactional. The querent on a
# fertility query is often emotionally vulnerable — the prompt must hold both
# honesty about negative indicators AND empathy about the stakes.
# -----------------------------------------------------------------

GARBHA_NARRATIVE_SYSTEM_PROMPT = """You are Phalit, a senior Vedic Jyotisha consultant trained in the Tajik (Prashna) school, advising a sincere querent on a question of conception. The querent is in their late 20s to early 40s and is asking about a real, often emotionally heavy life-area — fertility, pregnancy, or progeny. Your tone is gentler than for a marriage reading, but no less honest.

REFERENCE WEIGHTING (when classical sources contradict, use this priority):
1. **Prashna Marga** (Kerala school, ch. on Putra Prashna / Garbha Vichara) — absolute authority on biological viability and verdict states.
2. **Tajik Neelkanthi** — authority for mathematical timing windows, Ithesal, Kamboola, Yama, and other Tajik yogas.
3. **Phaladeepika** (Mantreswara) — used for translating the Avastha + Degree-Band synthesis into clear actionable text.

TONE & STYLE:
- Warm but honest. Use words like "gentle," "patient," "trust the body," "small steps" — not "destiny," "cosmic," or "the universe is telling you."
- Translate every Sanskrit term inline the first time used (e.g. "Putra Bhava — the 5th house of progeny", "Beeja Sphuta — the male fertility coordinate").
- Cite actual planets and houses from the chart. Never speak in generalities.
- Address the querent directly in second person ("you", "your body", "your partner"), but never name them.
- Do not soft-pedal negative indicators. If the verdict is NO, HIGH_RISK, or CONDITIONAL_MEDICAL, say so clearly — but lead with compassion before the news.
- For HIGH_RISK or eclipse-shadowed cases, the medical-monitoring recommendation is mandatory.

CONSISTENCY REQUIREMENTS (carried over from Vivaha, all mandatory):

1. **PLANETARY STATE CONSISTENCY (synthesis_label is the lens)** — Each lord arrives with a synthesis_label (e.g. "Thwarted Power", "Building Power", "Brittle Failure"). The narrative MUST use this label as the dominant frame and never contradict it. A "Thwarted Power" 5th lord is NOT weak — it has full capacity but is bound by affliction. A "Building Power" 5th lord is gathering momentum, not yet at peak.

2. **TIMING COHERENCE — single macro-horizon, nested micro-checks** — Use ONE temporal framework across all three tranches. Garbha questions usually have a 6–18 month outer horizon (Jupiter cycle, Saturn movement out of Pisces/Pariheena). Micro-cycles (Moon's monthly return, 27–28 day cellular window) are NESTED under the macro horizon, not presented as competing timelines. NEVER state two end-points that contradict each other.

3. **NATAL-PRASHNA HANDSHAKE** — If the horary_to_natal data activates a meaningful natal house, name it explicitly in tranche_arc (e.g. "This question lands on your natal 5th — your own progeny axis").

4. **INCONCLUSIVE MODIFIER HANDLING** — If the judgment's verdict_modifier is "INCONCLUSIVE_RECAST_REQUIRED" (fires for current_pregnancy_confirmation when Moon is void-of-course or 5th lord is heavily combust), the tone shifts to "next cellular window." Do NOT issue a YES or NO. Frame the verdict as "the chart cannot resolve this cleanly right now; recast in 27–28 days as the lunar cycle completes." Stress that this is cosmic indeterminacy, not denial. The clinical disclaimer is mandatory.

5. **MEDICAL DISCLAIMER FOR PREGNANCY CONFIRMATION** — When intent is `current_pregnancy_confirmation`, every tranche must reinforce that Prashna is supplementary to a clinical pregnancy test. Phrase it as "the chart suggests direction; only a test confirms" — not "you should get tested" (which is intrusive).

6. **SPHUTA INTERPRETATION** — Beeja and Kshetra Sphutas are biological-coordinate filters. When sphuta_effect is "bonus_15," frame as "the body's cellular configuration favours conception this cycle." When sphuta_effect is "cap_50" (Sphuta in Alpa-Putra sterile sign), frame as "physiological friction at the coordinate level — a gentle reset is needed, often through diet, stress reduction, or medical workup."

7. **MARS-5TH POLARITY** — If mars_5th_risk is true, the narrative must flag miscarriage/surgical risk firmly. If mars_5th_vitality is true, frame Mars as "vital warmth, often signalling a strong male child" (Mangala Karaka).

8. **HUSBAND-PIVOT ACKNOWLEDGMENT** — If is_husband_pivot is true, the querent is the husband. Address him directly. Mention that the chart was rotated to read the partner's progeny zone (11th from his Prashna Lagna).

9. **LINEAGE-QUERY FRAMING** — If is_lineage_query is true, the question targets the 9th house (lineage/heir), not the 5th (progeny generally). The narrative must distinguish between "will a child be conceived" and "will the family line continue through this child."

OUTPUT FORMAT:
Return ONLY a single valid JSON object. No preamble, no markdown fences, no commentary outside the JSON. The JSON must have exactly these keys:
{
  "tranche_arc":       "150-200 word narrative of the fertility dynamic. USE synthesis_label for both lords. If horary_to_natal activates a meaningful natal house, name it. If husband-pivot, address the husband. If lineage-query, frame the 9th-house lens. Name the Sphuta coordinate and its effect (bonus or cap).",
  "tranche_strategy":  "150-200 word strategic guidance. Reference the active yogas (Kamboola substitution, Gada compression, Abhara friction, sterile cusp downgrade) and any third-party signals (Rahu = assisted conception, Ketu = adoption path). Tell the querent what posture to adopt: try actively, wait, seek medical workup, or explore alternative paths. Timing-references must align with tranche_timeline.",
  "tranche_timeline":  "100-150 word timeline. Use the conception window: state the macro horizon (Jupiter shift, Saturn movement out of Pariheena) AND nested micro-checks (Moon's monthly return). If verdict_modifier is INCONCLUSIVE_RECAST_REQUIRED, frame the 27-28 day window as primary. If eclipse_proximity is active, mention the shadow window and recommend deferring major decisions until it passes. NEVER contradict the strategy tranche's timing.",
  "platinum_rule":     "30-50 word directive — the single most important thing the querent should DO. Action verb leading. Concrete. Tender phrasing for emotional weight.",
  "friction_gate":     "30-50 word warning — the single most important thing the querent should AVOID. Concrete trigger or behaviour. For HIGH_RISK verdicts, this is where medical monitoring or activity restriction goes.",
  "sensory_remedy":    "30-50 word grounding / remedial practice. Lifestyle, dietary, temporal (Thursday for Jupiter, Friday for Venus, Monday for Moon). Pregnancy-relevant practices: prenatal preparation, stress reduction, fertility-friendly diet. Never prescribe gems, expensive remedies, or specific medical interventions."
}

Do not include any other keys. Do not nest. Do not use markdown inside string values."""


def _build_garbha_user_prompt(judgment: Dict,
                              query_text: Optional[str],
                              cast_meta: Optional[Dict]) -> str:
    """Compose the user prompt for the Garbha narrative. Inlines all judgment data."""

    q = judgment.get('querent_lord', {})
    qs = judgment.get('quesited_lord', {})
    asp = judgment.get('aspect_l1_lt', {})
    nakta = judgment.get('nakta_bridge')
    abhara = judgment.get('abhara_yoga')
    yama = judgment.get('yama_yoga')
    kamboola = judgment.get('kamboola_yoga')
    gada = judgment.get('gada_yoga')
    karya = judgment.get('karya_chain', {})
    strength = judgment.get('strength_scaling', {})
    bhava = judgment.get('bhava_bala_target', {})
    h2n = judgment.get('horary_to_natal', {})
    catalyst = judgment.get('core_catalyst', {})
    eclipse = judgment.get('eclipse_proximity')

    intent = judgment.get('intent', 'conception_possibility')
    target_house = judgment.get('target_house', 5)
    target_role = judgment.get('target_role', '5th — Putra Bhava')
    is_husband_pivot = judgment.get('is_husband_pivot', False)
    is_lineage_query = judgment.get('is_lineage_query', False)
    querent_gender = judgment.get('querent_gender', 'female')
    verdict_modifier = judgment.get('verdict_modifier')

    sphuta_active = judgment.get('sphuta_active')
    sphuta_effect = judgment.get('sphuta_effect')
    mars_5th_risk = judgment.get('mars_5th_risk', False)
    mars_5th_vitality = judgment.get('mars_5th_vitality', False)
    target_cusp_sterile = judgment.get('target_cusp_sterile', False)
    rahu_in_target = judgment.get('rahu_in_target', False)
    ketu_in_target = judgment.get('ketu_in_target', False)

    place = (cast_meta or {}).get('place_name') or "the querent's location"
    when_local = (cast_meta or {}).get('datetime_local_iso', 'now')

    lines = [
        f"# GARBHA PRASHNA — JUDGMENT PACKAGE",
        f"",
        f"## Querent's Question",
        f"\"{query_text or '(no text provided)'}\"",
        f"",
        f"## Querent Profile",
        f"- Gender: {querent_gender}",
        f"- Intent (classified): {intent}",
        f"- Husband-pivot: {is_husband_pivot} (target rotated to 5th-from-7th when True)",
        f"- Lineage-query: {is_lineage_query} (target on 9th house when True)",
        f"",
        f"## Cast Context",
        f"- Cast at: {when_local}",
        f"- Place: {place}",
        f"- Target house: {target_house} ({target_role})",
        f"",
        f"## Verdict (already computed by engine)",
        f"- Verdict: **{judgment.get('verdict')}** — {judgment.get('verdict_text')}",
        f"- Verdict modifier: **{verdict_modifier or 'None'}**",
        f"- Certainty Score: {judgment.get('certainty_score')}% ({judgment.get('certainty_band')})",
        f"- Certainty narrative: {judgment.get('certainty_narrative')}",
    ]

    if verdict_modifier == 'INCONCLUSIVE_RECAST_REQUIRED':
        lines += [
            f"",
            f"## ⚠ INCONCLUSIVE MODIFIER ACTIVE",
            f"- The Moon is void-of-course OR the {target_house}th lord is heavily combust.",
            f"- The narrative MUST frame the verdict as 'cosmic indeterminacy, not denial.'",
            f"- Recommend recasting in 27-28 days as the lunar cycle completes.",
            f"- Clinical disclaimer is mandatory in every tranche.",
        ]

    if intent == 'current_pregnancy_confirmation':
        lines += [
            f"",
            f"## 🏥 MEDICAL DISCLAIMER REQUIRED",
            f"- Intent is current_pregnancy_confirmation.",
            f"- Every tranche must reinforce that Prashna is supplementary to a clinical test.",
            f"- Frame as 'chart suggests direction; only a test confirms' — never 'you should get tested.'",
        ]

    lines += [
        f"",
        f"## Significators (USE synthesis_label as the dominant frame — do not contradict it)",
        f"- **Querent (Lagna Lord)**: {q.get('name')} in {q.get('sign')} (house {q.get('house')}).",
        f"  - Avastha: {q.get('avastha')} — {q.get('condition')}",
        f"  - Degree band: {(q.get('degree_band') or {}).get('band_name', '—')} ({(q.get('degree_band') or {}).get('band_english', '—')})",
        f"  - **Synthesis (use this frame): {q.get('synthesis_label')}** — {q.get('synthesis_narrative')}",
        f"  - Outcome signature: {q.get('outcome')}. Combust: {q.get('is_combust')}.",
        f"- **Quesited ({target_house}th Lord)**: {qs.get('name')} in {qs.get('sign')} (house {qs.get('house')}).",
        f"  - Avastha: {qs.get('avastha')} — {qs.get('condition')}",
        f"  - Degree band: {(qs.get('degree_band') or {}).get('band_name', '—')} ({(qs.get('degree_band') or {}).get('band_english', '—')})",
        f"  - **Synthesis (use this frame): {qs.get('synthesis_label')}** — {qs.get('synthesis_narrative')}",
        f"  - Outcome signature: {qs.get('outcome')}. Combust: {qs.get('is_combust')}. Heavily combust: {qs.get('is_heavily_combust')}.",
        f"",
        f"## Tajik Aspect (Lagna Lord ↔ {target_house}th Lord)",
        f"- Yoga: {asp.get('yoga', 'None')}",
        f"- Within orb: {asp.get('within_orb', False)}",
        f"- Orb: {asp.get('orb_used', '—')}°, separation {asp.get('absolute_separation', '—')}°",
        f"- Aspect narrative: {asp.get('narrative', '—')}",
    ]

    # Sphuta block
    if sphuta_active:
        lines += [
            f"",
            f"## Fertility Coordinate (Sphuta — Parashari biological filter)",
            f"- Type: {sphuta_active.get('sphuta_type', '—').title()} Sphuta "
            f"({'male' if sphuta_active.get('sphuta_type') == 'beeja' else 'female'} fertility point)",
            f"- Computed longitude: {sphuta_active.get('longitude', '—')}° → "
            f"{sphuta_active.get('sign_name', '—')} ({sphuta_active.get('deg_in_sign', '—')}°)",
        ]
        if sphuta_effect:
            lines.append(f"- **Effect:** {sphuta_effect.get('type', '—')} — {sphuta_effect.get('narrative', '—')}")

    # New yogas
    if kamboola:
        lines += [
            f"",
            f"## Kamboola Yoga (Moon as cosmic proxy — overrides primitive NO to YES_WITH_DELAYS)",
            f"- Moon Vimshopaka: {kamboola.get('moon_vimshopaka_score')}/20",
            f"- Narrative: {kamboola.get('narrative')}",
        ]

    if gada:
        lines += [
            f"",
            f"## Gada Yoga (structural compression — forces resolution within 12 months)",
            f"- Kendras occupied: {gada.get('kendras_occupied')}",
            f"- Narrative: {gada.get('narrative')}",
        ]

    if nakta:
        bridge_label = nakta.get('bridge') or '(no qualifying bridge)'
        lines += [
            f"",
            f"## Nakta Bridge (third-planet relay)",
            f"- Bridge planet: {bridge_label}",
            f"- Bridge role: {nakta.get('bridge_role') or '—'}",
            f"- Role narrative: {nakta.get('bridge_role_narrative') or '—'}",
            f"- Narrative: {nakta.get('narrative')}",
        ]
        near = nakta.get('near_misses') or []
        if near:
            lines.append(f"- Near-misses checked:")
            for nm in near:
                lines.append(f"  - {nm.get('narrative', '—')}")

    if abhara:
        lines += [
            f"",
            f"## Abhara Yoga (malefic interference on a valid link)",
            f"- Severity: {abhara.get('severity')}",
            f"- Narrative: {abhara.get('narrative')}",
        ]
        for b in (abhara.get('blockers') or [])[:3]:
            lines.append(f"  - {b.get('malefic')} ({b.get('mode')}): {b.get('narrative')}")

    if yama:
        lines += [
            f"",
            f"## Yama Yoga (midpoint binder — structural / forced conception)",
            f"- Severity: {yama.get('severity')}",
            f"- Narrative: {yama.get('narrative')}",
        ]

    # Garbha-specific structural flags
    lines += [
        f"",
        f"## Garbha Structural Indicators",
    ]
    if target_cusp_sterile:
        lines.append(f"- ⚠ **Sterile cusp (Alpa-Putra):** {target_house}th cusp falls in Gemini/Leo/Virgo/Scorpio. Conception structurally promised but the cellular runway requires preparation.")
    if mars_5th_risk:
        lines.append(f"- 🩸 **Mars in target (risk group — Aries/Cancer/Leo/Libra/Capricorn):** miscarriage / surgical-intervention flag. The narrative must mention medical monitoring.")
    if mars_5th_vitality:
        lines.append(f"- 🟢 **Mars in target (vitality group — Sagittarius/Pisces/etc.):** Mars's heat is tempered. If Jupiter aspects, signals a strong male child (Mangala Karaka).")
    if rahu_in_target:
        lines.append(f"- 🌙 **Rahu in {target_house}th house:** Modern Tajik reading — assisted conception (IVF/IUI/surrogacy). Frame as a viable, modern path, NOT 'demonic affliction.'")
    if ketu_in_target:
        lines.append(f"- 🍃 **Ketu in {target_house}th house:** Spiritual detachment from biological conception — adoption path may be indicated.")
    if not (target_cusp_sterile or mars_5th_risk or mars_5th_vitality or rahu_in_target or ketu_in_target):
        lines.append(f"- No special structural indicators — verdict driven by Karya chain + Sphuta + Bhava Bala only.")

    # Eclipse
    if eclipse:
        lines += [
            f"",
            f"## ⚠ Eclipse Proximity (sincerity hard-capped at 45/100)",
            f"- Eclipse type: {eclipse.get('eclipse_type')}",
            f"- Days from cast: {eclipse.get('days_from_cast')}",
            f"- Axis hit: {eclipse.get('axis_hit')}",
            f"- Narrative: {eclipse.get('narrative')}",
            f"- The tranche_timeline must mention the shadow window and recommend deferring major decisions until it passes.",
        ]

    # Core catalyst + Karya
    lines += [
        f"",
        f"## Core Catalyst",
        f"- Yoga: {catalyst.get('yoga')}",
        f"- Between: {' & '.join(catalyst.get('between', []))}",
        f"- Narrative: {catalyst.get('narrative')}",
        f"",
        f"## Karya Success Chain",
        f"- Positive rules satisfied: {karya.get('positive_satisfied', 0)} / 3",
        f"- Rule 4 fired (combustion/affliction): {karya.get('rule4_fired', False)}",
        f"- Verdict primitive: {karya.get('verdict_primitive')}",
        f"- Verdict modifier: {karya.get('verdict_modifier')}",
        f"- Andha Parivartana: {karya.get('andha_parivartana', False)}",
        f"",
        f"## Bhava Bala — {target_house}th House (progeny axis)",
        f"- Net strength: {bhava.get('net_strength_pct', '—')}% ({bhava.get('verdict', '—')})",
        f"- Sphuta cap applied: {bhava.get('sphuta_cap_applied', False)}",
        f"- Sphuta bonus applied: {bhava.get('sphuta_bonus_applied', False)}",
    ]

    # H2N
    if h2n and 'error' not in h2n:
        lines += [
            f"",
            f"## Horary-to-Natal Shift (NAME THIS NATAL HOUSE in tranche_arc per consistency rule #3)",
            f"- House shift: {h2n.get('shift')} houses",
            f"- Activated natal house: {h2n.get('activated_natal_house')}",
            f"- Flourishing zone: {h2n.get('zone_label')}",
            f"- Zone narrative: {h2n.get('zone_narrative')}",
        ]

    # Long horizon
    lh = judgment.get('long_horizon') or {}
    if lh.get('is_long_horizon'):
        lines += [
            f"",
            f"## Horizon Boundary (CRITICAL — incorporate into tranche_timeline)",
            f"- Long-horizon keyword matched: \"{lh.get('matched_keyword')}\"",
            f"- The question implies a multi-decade horizon; Prashna's 6-12 month window",
            f"  cannot answer it on its own. Acknowledge this boundary explicitly in",
            f"  tranche_timeline. Recommend D-7 Saptamsha follow-up for the full horizon.",
        ]

    lines += [
        f"",
        f"---",
        f"",
        f"Produce the 3-tranche narrative and 3 action cards now. JSON only, no other text.",
    ]

    return "\n".join(lines)


@router.post("/prashnareport")
def prashnareport(req: PrashnaReportRequest) -> Dict:
    """
    Generate the AI narrative for a Vaivahika judgment package.

    Takes the judgment block from /prashna_vivaha or /prashna_garbha and
    produces a structured 3-tranche narrative (Arc / Strategy / Timeline)
    plus 3 action cards (Platinum Rule / Friction Gate / Sensory Remedy)
    using claude-sonnet-4-6 with a sub-module-specific system prompt.

    Dispatch:
      sub_module='vivaha' → VIVAHA_NARRATIVE_SYSTEM_PROMPT + _build_vivaha_user_prompt
      sub_module='garbha' → GARBHA_NARRATIVE_SYSTEM_PROMPT + _build_garbha_user_prompt
    """

    if req.sub_module not in ('vivaha', 'garbha'):
        raise HTTPException(
            status_code=400,
            detail=f"sub_module '{req.sub_module}' not supported. "
                   f"Available: 'vivaha', 'garbha'."
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

    # Dispatch on sub_module
    if req.sub_module == 'vivaha':
        system_prompt = VIVAHA_NARRATIVE_SYSTEM_PROMPT
        user_prompt = _build_vivaha_user_prompt(req.judgment, req.query_text, req.cast_meta)
    else:  # 'garbha'
        system_prompt = GARBHA_NARRATIVE_SYSTEM_PROMPT
        user_prompt = _build_garbha_user_prompt(req.judgment, req.query_text, req.cast_meta)

    try:
        msg = client.messages.create(
            model=PRASHNA_AI_MODEL,
            max_tokens=2000,
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_prompt}
            ],
        )
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"LLM call failed: {type(exc).__name__}: {str(exc)[:300]}"
        )

    # Extract text from response
    raw_text = ""
    for block in msg.content:
        if getattr(block, 'type', None) == 'text':
            raw_text += block.text

    # Strip any accidental markdown fences
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        # Drop the first fence line
        cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
        # Drop trailing fence
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        # Drop leading "json" tag if present
        if cleaned.lstrip().startswith("json"):
            cleaned = cleaned.lstrip()[4:]
    cleaned = cleaned.strip()

    try:
        parsed = _json.loads(cleaned)
    except _json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"LLM returned non-JSON: {str(exc)[:200]}. "
                   f"First 200 chars of response: {raw_text[:200]}"
        )

    # Validate required keys
    required = {'tranche_arc', 'tranche_strategy', 'tranche_timeline',
                'platinum_rule', 'friction_gate', 'sensory_remedy'}
    missing = required - set(parsed.keys())
    if missing:
        raise HTTPException(
            status_code=502,
            detail=f"LLM response missing required keys: {sorted(missing)}. "
                   f"Got: {sorted(parsed.keys())}"
        )

    return {
        'sub_module': req.sub_module,
        'narrative': parsed,
        'model': PRASHNA_AI_MODEL,
        'usage': {
            'input_tokens': getattr(msg.usage, 'input_tokens', None),
            'output_tokens': getattr(msg.usage, 'output_tokens', None),
        },
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
        ],
        'max_queries_per_chart': MAX_QUERIES_PER_CHART,
        'ai_model': PRASHNA_AI_MODEL,
    }


# ================== END PASTE ==================
