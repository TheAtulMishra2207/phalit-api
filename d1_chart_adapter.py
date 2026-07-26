"""
d1_chart_adapter.py — certified /chart payload -> CertifiedChart (KAR-093 step 6a).

The integration seam between the live chart engine and the D1 engine. It
TRANSLATES; it never computes. Two findings recorded here, both surfaced by
reading main_live.py rather than assuming:

  1. The certified engine emits eight dignity strings:
        Exalted (Uccha) · Moolatrikona · Own Sign (Swa) · Friendly Sign (Mitra)
        Neutral Sign (Sama) · Enemy Sign (Shatru) · Debilitated (Neecha) · Node
     It has NO panchadha-maitri layer, so it never produces a "great friend" or
     "great enemy". Dignity.GREAT_FRIEND and Dignity.GREAT_ENEMY therefore
     cannot arise from the live engine today. They remain valid contract values
     (a future temporary-friendship layer would emit them); they are simply
     unreachable through this adapter, which is asserted by test rather than
     left to chance.

  2. Rahu and Ketu DO carry dignity in the certified chart: 'Exalted (Uccha)'
     in Taurus/Scorpio per BPHS Ch.47, 'Debilitated (Neecha)' opposite, and the
     sentinel 'Node' elsewhere. 'Node' is not a dignity — it maps to None, so a
     node in an ordinary sign yields StrengthVerdict.UNKNOWN as before, while an
     exalted or debilitated node is carried through faithfully.

Anything outside the known vocabulary raises ChartAdapterError. The adapter
fails closed: an unrecognised dignity is never silently coerced to Neutral.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import ValidationError

from d1_contract import Dignity, Graha
from d1_engine import CertifiedChart, ChartGraha

ADAPTER_VERSION = "d1-chart-adapter-0.1.0"

class ChartAdapterError(ValueError):
    """Raised when the certified payload cannot be translated. Never repaired."""

# ── certified provenance gate (QA step-6a HIGH-1) ────────────────────────────
# A chart may only enter the D1 pipeline if it was produced by the frozen
# certified build. Without this, a stale or Moshier-backed chart would flow
# through an engine whose output claims the accepted Lahiri / whole-sign /
# Swiss policy. Values are the FIXTURE-FREEZE CERTIFICATE of 2026-07-25.
REQUIRED_CALCULATION_META: Dict[str, str] = {
    "chart_engine_version": "1.1.0",
    "ayanamsha_model": "lahiri-linear-fit-2026-07",
    "house_system": "whole-sign",
    "node_type": "mean",
    "ephemeris_backend": "swisseph",
}

def check_provenance(meta: Any) -> None:
    """Raise unless the chart carries the exact certified provenance."""
    if meta is None:
        raise ChartAdapterError(
            "certified chart carries no calculation_meta; provenance cannot be verified")
    if not isinstance(meta, dict):
        raise ChartAdapterError("calculation_meta must be an object")
    mismatched = []
    for key, expected in REQUIRED_CALCULATION_META.items():
        actual = meta.get(key)
        if actual != expected:
            mismatched.append(f"{key}={actual!r} (expected {expected!r})")
    if mismatched:
        raise ChartAdapterError(
            "certified chart provenance does not match the frozen build: "
            + "; ".join(sorted(mismatched)))

# Exact strings emitted by main_live.get_dignity(). 'Node' is a sentinel, not a
# dignity, and maps to None.
CERTIFIED_DIGNITY: Dict[str, Optional[Dignity]] = {
    "Exalted (Uccha)": Dignity.EXALTED,
    "Moolatrikona": Dignity.MOOLATRIKONA,
    "Own Sign (Swa)": Dignity.OWN,
    "Friendly Sign (Mitra)": Dignity.FRIEND,
    "Neutral Sign (Sama)": Dignity.NEUTRAL,
    "Enemy Sign (Shatru)": Dignity.ENEMY,
    "Debilitated (Neecha)": Dignity.DEBILITATED,
    "Node": None,
}
# Not producible by the live engine (no panchadha maitri). Kept explicit so the
# gap is visible rather than implied by absence.
UNREACHABLE_FROM_LIVE_ENGINE = frozenset({Dignity.GREAT_FRIEND, Dignity.GREAT_ENEMY})

def map_dignity(value: Any) -> Optional[Dignity]:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ChartAdapterError(f"dignity must be a string, got {type(value).__name__}")
    if value not in CERTIFIED_DIGNITY:
        raise ChartAdapterError(
            f"unrecognised certified dignity {value!r}; the adapter will not guess. "
            f"Known values: {sorted(CERTIFIED_DIGNITY)}")
    return CERTIFIED_DIGNITY[value]

def _require(d: Dict[str, Any], key: str, where: str) -> Any:
    if key not in d:
        raise ChartAdapterError(f"certified chart missing {key!r} in {where}")
    return d[key]

# ── strict certified types (QA step-6a v2 HIGH-1) ────────────────────────────
# Pydantic coercion is not acceptable at this trust boundary: it accepted
# sign_index="6" and, worse, bool("false") silently reversed retrograde. Types
# are checked BEFORE model construction. bool is excluded explicitly because in
# Python bool is a subclass of int.

def _req_int(d: Dict[str, Any], key: str, where: str) -> int:
    v = _require(d, key, where)
    if isinstance(v, bool) or not isinstance(v, int):
        raise ChartAdapterError(
            f"{where}.{key} must be an integer, got {type(v).__name__} {v!r}")
    return v

def _req_num(d: Dict[str, Any], key: str, where: str) -> float:
    v = _require(d, key, where)
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise ChartAdapterError(
            f"{where}.{key} must be numeric, got {type(v).__name__} {v!r}")
    return float(v)

def _opt_bool(d: Dict[str, Any], key: str, where: str) -> bool:
    v = d.get(key, False)
    if not isinstance(v, bool):
        raise ChartAdapterError(
            f"{where}.{key} must be a boolean, got {type(v).__name__} {v!r}; "
            f"the adapter will not coerce (bool('false') is True)")
    return v

def _opt_int(d: Dict[str, Any], key: str, where: str) -> Optional[int]:
    v = d.get(key)
    if v is None:
        return None
    if isinstance(v, bool) or not isinstance(v, int):
        raise ChartAdapterError(
            f"{where}.{key} must be an integer when present, got {type(v).__name__} {v!r}")
    return v

def _opt_str(d: Dict[str, Any], key: str, where: str) -> Optional[str]:
    v = d.get(key)
    if v is None or isinstance(v, str):
        return v
    raise ChartAdapterError(
        f"{where}.{key} must be a string when present, got {type(v).__name__} {v!r}")

def to_certified_chart(chart: Dict[str, Any], chart_token: str) -> CertifiedChart:
    """Translate a /chart response body into the D1 engine's input model."""
    if not isinstance(chart, dict):
        raise ChartAdapterError("certified chart payload must be an object")
    check_provenance(chart.get("calculation_meta"))
    lagna = _require(chart, "lagna", "chart")
    if not isinstance(lagna, dict):
        raise ChartAdapterError("chart.lagna must be an object")
    planets = _require(chart, "planets", "chart")
    if not isinstance(planets, dict):
        raise ChartAdapterError("chart.planets must be an object keyed by graha")

    grahas: Dict[Graha, ChartGraha] = {}
    for g in Graha:
        raw = planets.get(g.value)
        if raw is None:
            raise ChartAdapterError(f"certified chart missing planet {g.value!r}")
        if not isinstance(raw, dict):
            raise ChartAdapterError(f"chart.planets[{g.value!r}] must be an object")
        try:
            grahas[g] = ChartGraha(
                sign_index=_req_int(raw, "sign_index", g.value),
                degree_in_sign=_req_num(raw, "degree", g.value),
                longitude=_req_num(raw, "longitude", g.value),
                dignity=map_dignity(raw.get("dignity")),
                retrograde=_opt_bool(raw, "retrograde", g.value),
                combust=_opt_bool(raw, "combust", g.value),
                nakshatra=_opt_str(raw, "nakshatra", g.value),
                nakshatra_pada=_opt_int(raw, "nakshatra_pada", g.value),
            )
        except ValidationError as e:
            # Out-of-range or wrongly typed certified values are a translation
            # failure, not an unhandled server fault (QA step-6a HIGH-2).
            raise ChartAdapterError(f"invalid certified values for {g.value}: {e}") from e
    try:
        return CertifiedChart(
            chart_token=chart_token,
            lagna_sign_index=_req_int(lagna, "sign_index", "lagna"),
            lagna_degree=_req_num(lagna, "degree", "lagna"),
            grahas=grahas,
        )
    except ValidationError as e:
        raise ChartAdapterError(f"invalid certified lagna values: {e}") from e
