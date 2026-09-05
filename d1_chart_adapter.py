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

from d1_contract import Dignity, Graha, Varga
from d1_engine import CertifiedChart, ChartGraha

ADAPTER_VERSION = "d1-chart-adapter-0.1.0"

class ChartAdapterError(ValueError):
    """Raised when the certified payload cannot be translated. Never repaired."""

# ── certified provenance gate (QA step-6a HIGH-1) ────────────────────────────
# A chart may only enter the D1 pipeline if it was produced by the frozen
# certified build. Without this, a stale or Moshier-backed chart would flow
# through an engine whose output claims the accepted Lahiri / whole-sign /
# Swiss policy. Values are the FIXTURE-FREEZE CERTIFICATE of 2026-07-25.
# D10-002 §35 · 1.1.0 -> 1.2.0, ATOMIC WITH main.CHART_ENGINE_VERSION. The
# /chart graha contract gained the additive `karaka_arcsecond` field. This
# certificate pins the engine version by exact equality, so leaving it at 1.1.0
# would make every certified chart fail provenance the moment the engine ships.
# The two are one change and must land in one commit.
REQUIRED_CALCULATION_META: Dict[str, str] = {
    "chart_engine_version": "1.4.0",
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

# ── varga view (D9 port) ─────────────────────────────────────────────────────
# The engine requires varga_sign_index, varga_dignity and varga_lagna_sign_index
# and RAISES without them, because it never computes a varga mapping. The live
# /chart already carries them under its own D9-prefixed names, so this is a
# rename at the seam and nothing more: no arithmetic, no navamsa derivation.
#
# The source names are held in a TABLE rather than inlined, for the same reason
# the policy key is varga_aspect_policy and not d9_aspect_policy: the next varga
# is a row here, not a rewrite of to_certified_chart. Only D9 is declared,
# because only D9's dignity is emitted by the certified engine today. /chart
# carries d20_sign_index but no d20_dignity, so declaring D20 here would promise
# a view the engine cannot fill.
VARGA_SOURCE_FIELDS: Dict[Varga, Dict[str, str]] = {
    Varga.D9: {"graha_sign_index": "d9_sign_index",
               "graha_dignity": "d9_dignity",
               "lagna_sign_index": "d9_sign_index"},
}

# Absent varga fields are left as None rather than defaulted. The engine then
# fails closed and names the grahas it could not find a view for, which is the
# correct place for that refusal: the adapter translates, the engine judges.

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

def _opt_bool_or_none(d: Dict[str, Any], key: str, where: str) -> Optional[bool]:
    """Absent stays None, never False.

    _opt_bool defaults a missing key to False, which for vargottama would print
    "no" for every graha on a payload that simply did not carry the field. The
    unknown state has to stay reachable, so absence is None and the renderer
    shows an explicit unknown rather than a confident negative.
    """
    v = d.get(key)
    if v is None:
        return None
    if not isinstance(v, bool):
        raise ChartAdapterError(
            f"{where}.{key} must be a boolean when present, got {type(v).__name__} {v!r}")
    return v

def _opt_str(d: Dict[str, Any], key: str, where: str) -> Optional[str]:
    v = d.get(key)
    if v is None or isinstance(v, str):
        return v
    raise ChartAdapterError(
        f"{where}.{key} must be a string when present, got {type(v).__name__} {v!r}")

def to_certified_chart(chart: Dict[str, Any], chart_token: str,
                       varga: Varga = Varga.D9) -> CertifiedChart:
    """Translate a /chart response body into the D1 engine's input model.

    `varga` selects which secondary view is carried alongside the birth chart.
    One certified snapshot holds both, so a D1 request and a D9 request read the
    same object and no second /chart call happens.
    """
    src = VARGA_SOURCE_FIELDS.get(varga, {})
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
                # Rename only. map_dignity already returns None for the 'Node'
                # sentinel, which is what yields the UNKNOWN dignity shift for
                # Rahu and Ketu with no special-casing anywhere.
                varga_sign_index=(_opt_int(raw, src["graha_sign_index"], g.value)
                                  if src else None),
                varga_dignity=(map_dignity(raw.get(src["graha_dignity"]))
                               if src else None),
                # Pure carry-through of a certified boolean, read exactly as
                # dignity is read. The alternative, comparing sign_index across
                # two payloads in the browser, is the derivation already ruled
                # out for house.
                vargottama=_opt_bool_or_none(raw, "vargottama", g.value),
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
            varga_lagna_sign_index=(_opt_int(lagna, src["lagna_sign_index"], "lagna")
                                    if src else None),
        )
    except ValidationError as e:
        raise ChartAdapterError(f"invalid certified lagna values: {e}") from e
