"""
test_ephemeris.py — configuration state machine for ephemeris.py.

Save to E:\\phalit.ai\\test_ephemeris.py and upload to the repo root.

Runs two ways:
    python test_ephemeris.py
    pytest test_ephemeris.py -q

No real Swiss Ephemeris dataset is required: a fake `swisseph` module is
installed before each import, and .se1 files are temporary random bytes.
ephemeris.py does all its checking at import time, so each test imports it
fresh inside a controlled environment and asserts either a successful boot
with the right provenance or a RuntimeError with the right message.
"""

import hashlib
import importlib
import os
import sys
import tempfile
import types

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

_ENV_KEYS = ["SWISSEPH_PATH", "EXPECTED_EPHEMERIS_BACKEND", "EPHEMERIS_BOOTSTRAP",
             "EPHEMERIS_DATASET", "SUPPORTED_YEAR_MIN", "SUPPORTED_YEAR_MAX"]


class FakeSwe(types.ModuleType):
    """Minimal swisseph stand-in. Backend per body is scripted per test."""
    FLG_SWIEPH = 2
    FLG_JPLEPH = 1
    FLG_MOSEPH = 4
    FLG_SPEED = 256
    SUN = 0
    MOON = 1

    def __init__(self, sun_backend="moshier", moon_backend=None):
        super().__init__("swisseph")
        self._flags = {
            self.SUN: self._flag(sun_backend),
            self.MOON: self._flag(moon_backend or sun_backend),
        }
        self.ephe_path = None

    def _flag(self, name):
        return {"swisseph": self.FLG_SWIEPH, "moshier": self.FLG_MOSEPH,
                "jpl": self.FLG_JPLEPH}[name]

    def set_ephe_path(self, path):
        self.ephe_path = path

    def calc_ut(self, jd, body, flags):
        return (0.0, 0.0, 0.0, 0.0, 0.0, 0.0), self._flags.get(body, self.FLG_MOSEPH)


def _write(directory, name, content):
    path = os.path.join(directory, name)
    with open(path, "wb") as fh:
        fh.write(content)
    return hashlib.sha256(content).hexdigest()


def load_ephemeris(env=None, backend="moshier", moon_backend=None, manifest=None):
    """Import ephemeris.py fresh under a controlled environment.

    Returns (module, error). Exactly one is None.
    """
    for k in _ENV_KEYS:
        os.environ.pop(k, None)
    for k, v in (env or {}).items():
        os.environ[k] = v
    sys.modules["swisseph"] = FakeSwe(backend, moon_backend)
    sys.modules.pop("ephemeris", None)
    try:
        import ephemeris  # noqa: F401
        mod = sys.modules["ephemeris"]
        if manifest is not None:  # not used; manifest is patched via source below
            pass
        return mod, None
    except RuntimeError as e:
        return None, e
    finally:
        for k in _ENV_KEYS:
            os.environ.pop(k, None)


def load_with_manifest(env, backend, manifest, moon_backend=None):
    """Like load_ephemeris but patches EPHEMERIS_MANIFEST before the checks run.

    ephemeris.py evaluates everything at import, so the manifest is injected by
    executing the module source with the dict replaced.
    """
    for k in _ENV_KEYS:
        os.environ.pop(k, None)
    for k, v in (env or {}).items():
        os.environ[k] = v
    sys.modules["swisseph"] = FakeSwe(backend, moon_backend)
    src = open(os.path.join(HERE, "ephemeris.py"), encoding="utf-8").read()
    marker_start = "EPHEMERIS_MANIFEST: Dict[str, str] = {"
    i = src.index(marker_start)
    j = src.index("}", i)
    manifest_src = ("EPHEMERIS_MANIFEST: Dict[str, str] = "
                    + repr(manifest))
    src = src[:i] + manifest_src + src[j + 1:]
    mod = types.ModuleType("ephemeris_test_instance")
    mod.__file__ = os.path.join(HERE, "ephemeris.py")
    try:
        exec(compile(src, "ephemeris.py", "exec"), mod.__dict__)
        return mod, None
    except RuntimeError as e:
        return None, e
    finally:
        for k in _ENV_KEYS:
            os.environ.pop(k, None)


# ── 1. default swiss expectation, no files -> deploy fails ──────────────────

def test_default_swiss_with_no_files_fails():
    with tempfile.TemporaryDirectory() as d:
        mod, err = load_ephemeris({"SWISSEPH_PATH": d}, backend="moshier")
    assert err is not None
    assert "missing required ephemeris files" in str(err)
    assert "backend mismatch" in str(err)


# ── 2. explicit moshier, no files -> boots ──────────────────────────────────

def test_explicit_moshier_without_files_boots():
    with tempfile.TemporaryDirectory() as d:
        mod, err = load_ephemeris(
            {"SWISSEPH_PATH": d, "EXPECTED_EPHEMERIS_BACKEND": "moshier"},
            backend="moshier")
    assert err is None
    p = mod.provenance()
    assert p["ephemeris_backend"] == "moshier"
    assert p["ephemeris_manifest_enforced"] is False


# ── 3. swiss mode missing either required file fails ────────────────────────

def test_swiss_missing_moon_file_fails():
    with tempfile.TemporaryDirectory() as d:
        h = _write(d, "sepl_18.se1", b"planets" * 100)
        mod, err = load_with_manifest(
            {"SWISSEPH_PATH": d}, "swisseph", {"sepl_18.se1": h})
    assert err is not None
    assert "semo_18.se1" in str(err)


def test_swiss_missing_planet_file_fails():
    with tempfile.TemporaryDirectory() as d:
        h = _write(d, "semo_18.se1", b"moon" * 100)
        mod, err = load_with_manifest(
            {"SWISSEPH_PATH": d}, "swisseph", {"semo_18.se1": h})
    assert err is not None
    assert "sepl_18.se1" in str(err)


# ── 4. partial manifest fails, and is NOT reported enforced (KAR-071) ───────

def test_partial_manifest_fails():
    """QA's exact reproduction: both files present, only the planet file pinned.
    Previously this booted and reported ephemeris_manifest_enforced: true while
    the Moon file sat unverified."""
    with tempfile.TemporaryDirectory() as d:
        hp = _write(d, "sepl_18.se1", b"planets" * 100)
        _write(d, "semo_18.se1", b"moon" * 100)
        mod, err = load_with_manifest(
            {"SWISSEPH_PATH": d}, "swisseph", {"sepl_18.se1": hp})
    assert err is not None
    assert "unpinned" in str(err) and "semo_18.se1" in str(err)


def test_pin_for_absent_file_fails():
    with tempfile.TemporaryDirectory() as d:
        hp = _write(d, "sepl_18.se1", b"planets" * 100)
        hm = _write(d, "semo_18.se1", b"moon" * 100)
        mod, err = load_with_manifest(
            {"SWISSEPH_PATH": d}, "swisseph",
            {"sepl_18.se1": hp, "semo_18.se1": hm, "seas_18.se1": "0" * 64})
    assert err is not None
    assert "pinned file absent" in str(err)


# ── 5. incorrect hash fails ─────────────────────────────────────────────────

def test_checksum_mismatch_fails():
    with tempfile.TemporaryDirectory() as d:
        _write(d, "sepl_18.se1", b"planets" * 100)
        hm = _write(d, "semo_18.se1", b"moon" * 100)
        mod, err = load_with_manifest(
            {"SWISSEPH_PATH": d}, "swisseph",
            {"sepl_18.se1": "0" * 64, "semo_18.se1": hm})
    assert err is not None
    assert "checksum mismatch" in str(err) and "sepl_18.se1" in str(err)


# ── 6. mixed planet/moon backend fails ──────────────────────────────────────

def test_mixed_backend_fails():
    """The Moon file can be absent or unreadable independently of the planet
    file, in which case the Moon silently computes on Moshier while the
    planets use Swiss files. That state must fail the deploy."""
    with tempfile.TemporaryDirectory() as d:
        hp = _write(d, "sepl_18.se1", b"planets" * 100)
        hm = _write(d, "semo_18.se1", b"moon" * 100)
        mod, err = load_with_manifest(
            {"SWISSEPH_PATH": d}, "swisseph",
            {"sepl_18.se1": hp, "semo_18.se1": hm},
            moon_backend="moshier")
    assert err is not None
    assert "mixed" in str(err)


# ── 7. exact complete manifest succeeds (KAR-071 positive case) ─────────────

def test_complete_manifest_boots_and_is_enforced():
    with tempfile.TemporaryDirectory() as d:
        hp = _write(d, "sepl_18.se1", b"planets" * 100)
        hm = _write(d, "semo_18.se1", b"moon" * 100)
        mod, err = load_with_manifest(
            {"SWISSEPH_PATH": d}, "swisseph",
            {"sepl_18.se1": hp, "semo_18.se1": hm})
    assert err is None
    p = mod.provenance()
    assert p["ephemeris_backend"] == "swisseph"
    assert p["ephemeris_manifest_enforced"] is True
    assert p["ephemeris_manifest_status"] == "verified"
    assert p["ephemeris_files"] == ["semo_18.se1", "sepl_18.se1"]
    assert p["ephemeris_dataset_hash"]


# ── 8. moshier provenance labels itself moshier-built-in (KAR-073) ──────────

def test_moshier_dataset_label():
    with tempfile.TemporaryDirectory() as d:
        mod, err = load_ephemeris(
            {"SWISSEPH_PATH": d, "EXPECTED_EPHEMERIS_BACKEND": "moshier"},
            backend="moshier")
    assert err is None
    p = mod.provenance()
    assert p["ephemeris_dataset"] == "moshier-built-in"
    assert p["ephemeris_dataset_hash"] == ""
    assert p["ephemeris_files"] == []


# ── 9. unsupported chart year raises (KAR-072) ──────────────────────────────

def test_unsupported_year_raises():
    with tempfile.TemporaryDirectory() as d:
        mod, err = load_ephemeris(
            {"SWISSEPH_PATH": d, "EXPECTED_EPHEMERIS_BACKEND": "moshier"},
            backend="moshier")
    assert err is None
    for bad in (1799, 2151, 1500, 3000):
        try:
            mod.check_supported_year(bad)
            raise AssertionError(f"accepted year {bad}")
        except ValueError as e:
            assert "1800" in str(e) and "2150" in str(e)
    for ok in (1800, 1984, 2026, 2150):
        mod.check_supported_year(ok)
    assert mod.provenance()["supported_year_range"] == [1800, 2150]


# ── 10. bootstrap state boots, self-labels, and is not enforced ─────────────

def test_bootstrap_state_is_explicit_and_unenforced():
    with tempfile.TemporaryDirectory() as d:
        _write(d, "sepl_18.se1", b"planets" * 100)
        _write(d, "semo_18.se1", b"moon" * 100)
        mod, err = load_with_manifest(
            {"SWISSEPH_PATH": d, "EPHEMERIS_BOOTSTRAP": "1"}, "swisseph", {})
    assert err is None
    p = mod.provenance()
    assert p["ephemeris_manifest_status"] == "bootstrap_unpinned"
    assert p["ephemeris_manifest_enforced"] is False


def test_empty_manifest_without_bootstrap_fails():
    """An empty manifest must not be an ordinary production state."""
    with tempfile.TemporaryDirectory() as d:
        _write(d, "sepl_18.se1", b"planets" * 100)
        _write(d, "semo_18.se1", b"moon" * 100)
        mod, err = load_with_manifest({"SWISSEPH_PATH": d}, "swisseph", {})
    assert err is not None
    assert "EPHEMERIS_BOOTSTRAP" in str(err)


# ── KAR-074 / KAR-075 regression tests ──────────────────────────────────────

def test_bootstrap_with_complete_manifest_is_never_enforced():
    """KAR-075 exact reproduction: a complete, correct manifest booted with
    the bootstrap flag reported status bootstrap_unpinned AND enforced true."""
    with tempfile.TemporaryDirectory() as d:
        hp = _write(d, "sepl_18.se1", b"planets" * 100)
        hm = _write(d, "semo_18.se1", b"moon" * 100)
        mod, err = load_with_manifest(
            {"SWISSEPH_PATH": d, "EPHEMERIS_BOOTSTRAP": "1"}, "swisseph",
            {"sepl_18.se1": hp, "semo_18.se1": hm})
    assert err is None
    p = mod.provenance()
    assert p["ephemeris_manifest_status"] == "bootstrap_unpinned"
    assert p["ephemeris_manifest_enforced"] is False


def test_moshier_status_is_not_applicable_even_with_bootstrap_flag():
    """Backend-aware precedence: not_applicable outranks bootstrap."""
    with tempfile.TemporaryDirectory() as d:
        mod, err = load_ephemeris(
            {"SWISSEPH_PATH": d, "EXPECTED_EPHEMERIS_BACKEND": "moshier",
             "EPHEMERIS_BOOTSTRAP": "1"},
            backend="moshier")
    assert err is None
    assert mod.provenance()["ephemeris_manifest_status"] == "not_applicable"


def test_supported_range_cannot_be_widened_by_environment():
    """KAR-074: the certified interval is a code constant. Env vars that used
    to widen it must have no effect."""
    with tempfile.TemporaryDirectory() as d:
        mod, err = load_ephemeris(
            {"SWISSEPH_PATH": d, "EXPECTED_EPHEMERIS_BACKEND": "moshier",
             "SUPPORTED_YEAR_MIN": "1600", "SUPPORTED_YEAR_MAX": "2300"},
            backend="moshier")
    assert err is None
    assert mod.SUPPORTED_YEAR_MIN == 1800
    assert mod.SUPPORTED_YEAR_MAX == 2150
    assert mod.provenance()["supported_year_range"] == [1800, 2150]
    for bad in (1700, 2200):
        try:
            mod.check_supported_year(bad)
            raise AssertionError(f"accepted {bad} despite env override")
        except ValueError:
            pass


def test_check_supported_date_parses_year():
    with tempfile.TemporaryDirectory() as d:
        mod, err = load_ephemeris(
            {"SWISSEPH_PATH": d, "EXPECTED_EPHEMERIS_BACKEND": "moshier"},
            backend="moshier")
    assert err is None
    mod.check_supported_date("1984-07-22")
    for bad in ("1799-12-31", "2151-01-01"):
        try:
            mod.check_supported_date(bad)
            raise AssertionError(f"accepted {bad}")
        except ValueError:
            pass


# ── KAR-076 / KAR-077 unit tests ────────────────────────────────────────────

def test_invalid_calendar_dates_raise():
    """KAR-077 exact reproduction: 1984-99-99 previously passed the year check
    and Swiss Ephemeris normalised it into 23 June 1992."""
    with tempfile.TemporaryDirectory() as d:
        mod, err = load_ephemeris(
            {"SWISSEPH_PATH": d, "EXPECTED_EPHEMERIS_BACKEND": "moshier"},
            backend="moshier")
    assert err is None
    for bad in ("1984-99-99", "1984-02-30", "1984-13-01", "1984-00-10",
                "1984garbage", "99-99-1984", "", "1984-7-2x"):
        try:
            mod.check_supported_date(bad)
            raise AssertionError(f"accepted {bad!r}")
        except ValueError as e:
            assert "YYYY-MM-DD" in str(e) or "Supported chart years" in str(e)
    mod.check_supported_date("1984-07-22")
    mod.check_supported_date("2150-12-31")


def test_certified_jd_bounds():
    """KAR-076: the interval exists at the JD level, half-open, and instants
    outside it are rejected."""
    with tempfile.TemporaryDirectory() as d:
        mod, err = load_ephemeris(
            {"SWISSEPH_PATH": d, "EXPECTED_EPHEMERIS_BACKEND": "moshier"},
            backend="moshier")
    assert err is None
    # Known Julian day numbers: 1800-01-01 00:00 UT and 2151-01-01 00:00 UT.
    assert mod.CERTIFIED_JD_MIN == 2378496.5
    assert mod.CERTIFIED_JD_MAX == 2506696.5
    mod.check_supported_jd(mod.CERTIFIED_JD_MIN)          # inclusive lower
    mod.check_supported_jd(mod.CERTIFIED_JD_MAX - 0.01)
    for bad in (mod.CERTIFIED_JD_MIN - 0.01, mod.CERTIFIED_JD_MAX, 0.0):
        try:
            mod.check_supported_jd(bad)
            raise AssertionError(f"accepted JD {bad}")
        except ValueError as e:
            assert "certified interval" in str(e)


# ── KAR-078 · the converted UTC instant is what gets certified ──────────────

def test_chart_utc_instant_respects_certified_jd_bounds():
    """A valid local date can convert to an uncertified UTC instant. The JD
    check must apply to the instant the engine calculates at. This test drives
    the arithmetic directly through check_supported_jd, mirroring the route:
    local datetime minus offset -> JD -> check."""
    with tempfile.TemporaryDirectory() as d:
        mod, err = load_ephemeris(
            {"SWISSEPH_PATH": d, "EXPECTED_EPHEMERIS_BACKEND": "moshier"},
            backend="moshier")
    assert err is None

    def jd_of(y, mth, day, hh, mm, offset_hours):
        # Same conversion shape as main.to_julian_day: local wall time shifted
        # to UT, expressed against the pure-Python Gregorian JD.
        # _gregorian_jd already returns the midnight-UT instant (X.5), so the
        # time fraction is added directly. An earlier draft added 0.5 twice.
        frac = (hh + mm / 60.0 - offset_hours) / 24.0
        return mod._gregorian_jd(y, mth, day) + frac

    # Outside after offset conversion — QA's two reproductions.
    for args in [(1800, 1, 1, 0, 0, +5.5), (2150, 12, 31, 23, 59, -12.0)]:
        jd = jd_of(*args)
        try:
            mod.check_supported_jd(jd)
            raise AssertionError(f"accepted uncertified instant {args} -> JD {jd}")
        except ValueError:
            pass

    # Inside at UTC, same wall times.
    for args in [(1800, 1, 1, 0, 0, 0.0), (2150, 12, 31, 23, 59, 0.0)]:
        mod.check_supported_jd(jd_of(*args))


# ── runner ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    tests = [(n, o) for n, o in sorted(globals().items()) if n.startswith("test_")]
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"  pass  {name}")
        except Exception as e:
            failed += 1
            print(f"  FAIL  {name}: {e}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
