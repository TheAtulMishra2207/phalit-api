"""
ephemeris.py — Swiss Ephemeris configuration, backend lock and dataset integrity.

Save to E:\\phalit.ai\\ephemeris.py and upload to the repo root alongside main.py.

Why this exists
---------------
Until now `swe.set_ephe_path` was called inside two endpoints and nowhere else,
nothing recorded which backend actually served a calculation, and the process
silently fell back to Moshier. Moshier is roughly 0.1 arcsec on the planets but
around 3 arcsec on the Moon, and the Moon is what nakshatra, pada and the
Vimshottari balance are computed from. Fixtures generated under one backend must
never be compared against results produced under another.

Behaviour
---------
On import this module:
  1. Resolves the ephemeris directory. SWISSEPH_PATH wins; otherwise ./ephe
     beside this file, so vendoring the .se1 files into the repo needs no
     env var at all.
  2. Calls swe.set_ephe_path once.
  3. Probes the ACTUAL backend for a planet and, separately, for the Moon,
     by reading the returned flag rather than the requested one.
  4. Hashes every .se1 file present and compares against EPHEMERIS_MANIFEST.
  5. Raises RuntimeError if the backend is not the expected one, or if a
     pinned hash does not match. On Render a raise at import fails the deploy
     and leaves the previous version serving, which is the desired outcome.

Bootstrapping the manifest
--------------------------
EPHEMERIS_MANIFEST starts empty, and an empty manifest is NOT an ordinary
production state: in Swiss mode the module refuses to boot without either a
complete pinned manifest or the explicit EPHEMERIS_BOOTSTRAP=1 flag. Set the
flag for exactly one deploy, copy the logged SHA-256 lines into the dict,
remove the flag, redeploy. While the flag is set, provenance reports
ephemeris_manifest_status: bootstrap_unpinned and enforcement is always false,
regardless of manifest completeness.
"""

import hashlib
import logging
import os
from typing import Any, Dict, List

import swisseph as swe

logger = logging.getLogger("phalit.ephemeris")

# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────

_DEFAULT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ephe")
EPHE_PATH = os.environ.get("SWISSEPH_PATH", "").strip() or _DEFAULT_DIR

# Fail the deploy rather than serve Moshier by accident. Set to "moshier"
# explicitly and deliberately if you ever want the fallback in an environment.
EXPECTED_EPHEMERIS_BACKEND = os.environ.get(
    "EXPECTED_EPHEMERIS_BACKEND", "swisseph").strip().lower()

# Dataset label recorded in calculation provenance when Swiss files are in use.
# KAR-073: the reported dataset derives from the ACTUAL backend, so a deliberate
# Moshier boot says "moshier-built-in" rather than naming a file set it never read.
_SWISS_DATASET_LABEL = os.environ.get("EPHEMERIS_DATASET", "modern-era-se1").strip()

# KAR-071: first-deploy hash discovery is an explicit, self-labelling state,
# not a silent default. Set EPHEMERIS_BOOTSTRAP=1 for exactly one deploy to
# capture the hashes, paste them into EPHEMERIS_MANIFEST, then remove the flag.
EPHEMERIS_BOOTSTRAP = os.environ.get("EPHEMERIS_BOOTSTRAP", "").strip() == "1"

# Files the engine actually needs. It uses Sun through Saturn plus the mean
# node, so the planet and moon segments are required and the asteroid segment
# is not. The _18 segment covers 1800 to 2399; add sepl_12.se1 and semo_12.se1
# if you intend to support birth dates before 1800.
REQUIRED_FILES: List[str] = ["sepl_18.se1", "semo_18.se1"]

# Populate after the first boot. Empty means log-only; populated means enforced.
EPHEMERIS_MANIFEST: Dict[str, str] = {
    "sepl_18.se1": "ca1393ceab3a44fbc895887cf789c68819ae6a1cbc9b22225872dbe4ccd99a66",
    "semo_18.se1": "1ca07bd67c24374d77226180c20a4f9996cba013697894810518e7eb582ca4f7",
}


# ─────────────────────────────────────────────────────────────────────────────
# Probing and verification
# ─────────────────────────────────────────────────────────────────────────────

def _backend_from_flag(retflag: int) -> str:
    if retflag < 0:
        return f"error (retflag={retflag})"
    if retflag & swe.FLG_JPLEPH:
        return "jpl"
    if retflag & swe.FLG_SWIEPH:
        return "swisseph"
    if retflag & swe.FLG_MOSEPH:
        return "moshier"
    return f"unknown (retflag={retflag})"


class EphemerisBackendViolation(RuntimeError):
    """A calculation was served by a backend other than the expected one.

    D10-002-CORR-02. Raised, never returned, and never downgraded to a warning:
    a chart computed from an unexpected backend must not exist, because the
    published calculation_meta would certify a provenance the numbers do not
    have.
    """


def calc_ut_checked(jd: float, body: int, flags: int):
    """THE ONE PER-CALCULATION BACKEND GATE.

    `swe.calc_ut` falls back silently: asked for the Swiss files and unable to
    serve them, it returns a perfectly usable number computed analytically and
    signals that only in the return flag, which callers routinely discard as
    `_`. The startup J2000 probe cannot catch this, because a fallback can
    depend on the date being computed and the probe uses one fixed date.

    This wrapper inspects the retflag the call ACTUALLY returned, at the
    requested JD, and refuses anything that is not EXPECTED_EPHEMERIS_BACKEND.

    FAIL CLOSED. On a mismatch it raises before the caller can read `values`,
    so no result from an unexpected backend can enter a chart.
    """
    values, retflag = swe.calc_ut(jd, body, flags)
    actual = _backend_from_flag(retflag)
    if actual != EXPECTED_EPHEMERIS_BACKEND:
        raise EphemerisBackendViolation(
            f"ephemeris backend mismatch at jd={jd!r} body={body}: the "
            f"calculation was served by {actual!r}, not the expected "
            f"{EXPECTED_EPHEMERIS_BACKEND!r}. Refusing rather than publishing "
            f"a chart whose calculation_meta would claim "
            f"{EXPECTED_EPHEMERIS_BACKEND!r}."
        )
    return values, retflag


def probe_backend(body: int = swe.SUN) -> str:
    """Which backend Swiss Ephemeris actually used, not which was requested."""
    try:
        _, retflag = swe.calc_ut(2451545.0, body, swe.FLG_SWIEPH | swe.FLG_SPEED)
        return _backend_from_flag(retflag)
    except Exception as exc:  # pragma: no cover
        return f"probe failed: {exc}"


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def scan_dataset(directory: str) -> Dict[str, str]:
    """SHA-256 of every .se1 file in `directory`, keyed by filename."""
    if not os.path.isdir(directory):
        return {}
    return {
        name: _sha256(os.path.join(directory, name))
        for name in sorted(os.listdir(directory))
        if name.lower().endswith(".se1")
    }


def dataset_hash(hashes: Dict[str, str]) -> str:
    """One stable hash over the whole file set, for provenance."""
    if not hashes:
        return ""
    joined = "\n".join(f"{k}:{v}" for k, v in sorted(hashes.items()))
    return hashlib.sha256(joined.encode()).hexdigest()


# ─────────────────────────────────────────────────────────────────────────────
# Import-time configuration
# ─────────────────────────────────────────────────────────────────────────────

if os.path.isdir(EPHE_PATH):
    swe.set_ephe_path(EPHE_PATH)
else:
    logger.warning("Ephemeris directory not found: %s", EPHE_PATH)

FILE_HASHES: Dict[str, str] = scan_dataset(EPHE_PATH)
EPHEMERIS_DATASET_HASH: str = dataset_hash(FILE_HASHES)

# Probe the planets and the Moon separately. The Moon is the accuracy-critical
# body here and it has its own file, so it can fall back independently.
PLANET_BACKEND = probe_backend(swe.SUN)
MOON_BACKEND = probe_backend(swe.MOON)
EPHEMERIS_BACKEND = PLANET_BACKEND if PLANET_BACKEND == MOON_BACKEND else \
    f"mixed (planets={PLANET_BACKEND}, moon={MOON_BACKEND})"

logger.warning(
    "Ephemeris: dir=%s backend=%s files=%d dataset_hash=%s",
    EPHE_PATH, EPHEMERIS_BACKEND, len(FILE_HASHES), EPHEMERIS_DATASET_HASH[:12] or "none",
)

_problems: List[str] = []

# ── KAR-071 · manifest verification is all-or-nothing ────────────────────────
# "Enforced" previously meant the manifest dict was non-empty, so a manifest
# pinning the planet file but not the Moon file booted and reported itself
# fully enforced while the accuracy-critical file sat unverified. Enforcement
# now requires exact bijection: every required file present, every present
# file pinned, every pin present, every hash matching.
_required = set(REQUIRED_FILES)
_present  = set(FILE_HASHES)
_pinned   = set(EPHEMERIS_MANIFEST)

_missing_files     = sorted(_required - _present)
_missing_pins      = sorted(_present - _pinned)
_absent_pins       = sorted(_pinned - _present)
_hash_mismatches   = sorted(
    name for name in (_pinned & _present)
    if EPHEMERIS_MANIFEST[name] != FILE_HASHES[name]
)

MANIFEST_VERIFIED = (
    # KAR-075. Bootstrap is a discovery state and can never count as enforced,
    # even when the manifest happens to be complete and correct. A deploy that
    # forgets to remove the flag must not satisfy a fixture gate.
    not EPHEMERIS_BOOTSTRAP
    and EXPECTED_EPHEMERIS_BACKEND == "swisseph"
    and not _missing_files
    and not _missing_pins
    and not _absent_pins
    and not _hash_mismatches
    and bool(_pinned)
)

if EXPECTED_EPHEMERIS_BACKEND == "swisseph":
    if _missing_files:
        _problems.append(f"missing required ephemeris files: {', '.join(_missing_files)}")
    if EPHEMERIS_BOOTSTRAP:
        logger.warning(
            "EPHEMERIS_BOOTSTRAP=1: hashes are logged, nothing is pinned. Paste "
            "these into EPHEMERIS_MANIFEST and redeploy WITHOUT the flag:\n%s",
            "\n".join(f'    "{k}": "{v}",' for k, v in sorted(FILE_HASHES.items()))
            or "    (no .se1 files found)",
        )
    else:
        if _missing_pins:
            _problems.append(f"present but unpinned: {', '.join(_missing_pins)}")
        if _absent_pins:
            _problems.append(f"pinned file absent: {', '.join(_absent_pins)}")
        for name in _hash_mismatches:
            _problems.append(
                f"checksum mismatch for {name}: expected "
                f"{EPHEMERIS_MANIFEST[name][:12]}…, got {FILE_HASHES[name][:12]}…")
        if not _pinned and not _missing_files:
            _problems.append(
                "EPHEMERIS_MANIFEST is empty. Boot once with EPHEMERIS_BOOTSTRAP=1 "
                "to capture hashes, then pin them.")

if EPHEMERIS_BACKEND != EXPECTED_EPHEMERIS_BACKEND:
    _problems.append(
        f"backend mismatch: expected {EXPECTED_EPHEMERIS_BACKEND!r}, got {EPHEMERIS_BACKEND!r}")

if _problems:
    raise RuntimeError(
        "Ephemeris configuration rejected. "
        + " | ".join(_problems)
        + f" | directory={EPHE_PATH!r}"
        + " | Place the Swiss Ephemeris .se1 files there, or set"
          " EXPECTED_EPHEMERIS_BACKEND=moshier to run deliberately on the"
          " fallback. Fixtures generated on Moshier are not comparable with"
          " Swiss Ephemeris results."
    )


# ── KAR-072 · supported calculation interval ─────────────────────────────────
# The startup probe runs at J2000 and certifies nothing about other instants:
# a request outside the installed file segment would fall back to Moshier per
# call while calculation_meta went on certifying swisseph. Rather than audit
# every calc_ut return flag, the calculable interval is locked to the range
# that both the installed _18 segment (1800-2399) and the ayanamsha fit
# (validated 1800-2150) cover. Widening it later requires both the matching
# file segments and revalidation of the ayanamsha residual over the wider span.
# KAR-074. These are certification facts, not configuration. An env override
# advertised whatever range it was handed while the file segment and the
# ayanamsha validation stayed exactly where they were, so 1700 and 2200 charts
# were accepted with provenance claiming a certification that did not exist.
# Widening this interval is a code change that must also update REQUIRED_FILES,
# the pinned manifest, the ayanamsha validation evidence, and the chart engine
# version, together and in one commit.
SUPPORTED_YEAR_MIN = 1800
SUPPORTED_YEAR_MAX = 2150


def _gregorian_jd(year: int, month: int, day: int) -> float:
    """Julian day at 00:00 UT for a Gregorian calendar date. Pure Python so the
    test suite's fake swisseph module needs no julday implementation."""
    a = (14 - month) // 12
    y = year + 4800 - a
    m = month + 12 * a - 3
    jdn = day + (153 * m + 2) // 5 + 365 * y + y // 4 - y // 100 + y // 400 - 32045
    return jdn - 0.5

# KAR-076. The certified interval as Julian-day instants, half-open. Input-year
# validation on the routes does not establish calculation containment: search
# helpers buffer past month starts and scan past year ends, so they must be
# clamped against these instants and their results asserted with
# check_supported_jd.
CERTIFIED_JD_MIN = _gregorian_jd(SUPPORTED_YEAR_MIN, 1, 1)          # 1800-01-01 00:00
CERTIFIED_JD_MAX = _gregorian_jd(SUPPORTED_YEAR_MAX + 1, 1, 1)      # exclusive


def check_supported_jd(jd: float) -> None:
    """Raise ValueError for an instant outside the certified interval."""
    if not (CERTIFIED_JD_MIN <= jd < CERTIFIED_JD_MAX):
        raise ValueError(
            f"Calculation instant JD {jd:.2f} lies outside the certified interval "
            f"{SUPPORTED_YEAR_MIN}-01-01 to {SUPPORTED_YEAR_MAX}-12-31."
        )


def check_supported_date(date_value: str) -> None:
    """Validate a complete YYYY-MM-DD calendar date. Raises ValueError.

    KAR-077. The previous version read the first four characters only, so
    1984-99-99 passed the year check and Swiss Ephemeris silently normalised
    the overflow into 23 June 1992: malformed input produced a plausible
    result for an entirely different date.
    """
    from datetime import datetime as _dt
    try:
        parsed = _dt.strptime(str(date_value).strip(), "%Y-%m-%d")
    except ValueError as exc:
        raise ValueError(
            "Date must be a valid calendar date in YYYY-MM-DD format."
        ) from exc
    check_supported_year(parsed.year)


def check_supported_year(year: int) -> None:
    """Raise ValueError for a year outside the certified interval."""
    if not SUPPORTED_YEAR_MIN <= year <= SUPPORTED_YEAR_MAX:
        raise ValueError(
            f"Supported chart years are {SUPPORTED_YEAR_MIN} through "
            f"{SUPPORTED_YEAR_MAX}; received {year}."
        )


def _dataset_label() -> str:
    if EPHEMERIS_BACKEND == "moshier":
        return "moshier-built-in"
    if EPHEMERIS_BACKEND == "swisseph":
        return _SWISS_DATASET_LABEL
    return "unknown"


def _manifest_status() -> str:
    if EXPECTED_EPHEMERIS_BACKEND != "swisseph":
        return "not_applicable"
    if EPHEMERIS_BOOTSTRAP:
        return "bootstrap_unpinned"
    if MANIFEST_VERIFIED:
        return "verified"
    return "unverified"


def provenance() -> Dict[str, Any]:
    """Ephemeris half of calculation_meta."""
    return {
        "ephemeris_backend": EPHEMERIS_BACKEND,
        "ephemeris_dataset": _dataset_label(),
        "ephemeris_dataset_hash": EPHEMERIS_DATASET_HASH if EPHEMERIS_BACKEND == "swisseph" else "",
        "ephemeris_files": sorted(FILE_HASHES.keys()) if EPHEMERIS_BACKEND == "swisseph" else [],
        "ephemeris_manifest_status": _manifest_status(),
        "ephemeris_manifest_enforced": MANIFEST_VERIFIED,
        "supported_year_range": [SUPPORTED_YEAR_MIN, SUPPORTED_YEAR_MAX],
    }
