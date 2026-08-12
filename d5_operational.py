"""
d5_operational.py — D5-008 · THE CERTIFIED OPERATIONAL FACT ADAPTER.

Turns a certified chart snapshot plus one current-transit snapshot into the
`D5RuleInputs` and `TemporalInputs` the accepted D5 layers consume.

EVERY FACT IS READ OR MECHANICALLY DERIVED FROM CERTIFIED SERVER DATA. Nothing
here recomputes an astrological quantity: no dignity, no D9 division, no
Vimshottari arithmetic, no combustion orb, no ephemeris call. Where a fact must
be derived, it is derived by a transformation over values the chart engine
already certified — never by a second implementation of the underlying doctrine.

NO CLIENT INPUT REACHES THIS MODULE. The route accepts a chart_token and
nothing else, so there is no path by which a browser could supply a Tithi, a
transit, a D9 fact, a participant set or a score.

UNAVAILABLE IS NEVER FALSE. A fact with no certified source stays absent, and
the three-valued layers above decide what that means for each rule. See
D5-008-B01 in the closure document.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Mapping, Optional, Tuple

import d5_rules as R
import d5_temporal_tri as X
import graha_yuddha as YUDDHA
from d5_engine import D5DomainError

#: The nine physical grahas the D5 layers place.
GRAHAS: Tuple[str, ...] = ("Sun", "Moon", "Mars", "Mercury", "Jupiter",
                           "Venus", "Saturn", "Rahu", "Ketu")

#: The EXACT dignity strings the certified live engine emits. Nothing else is a
#: certified dignity.
#:
#: D5-008-CORR-02A · PREFIX MATCHING WAS TOO PERMISSIVE. `startswith` accepted
#: "FriendlyAlien", "Nodegarbage", "ExaltedXXX" and — worst — "Debilitated-ish",
#: which mapped to `debilitated = True` and moved TRI_02 and the Final Score.
#: Membership is now exact: no prefix, no substring, no trimming, no synonyms.
CERTIFIED_DIGNITIES: FrozenSet[str] = frozenset({
    "Exalted (Uccha)",
    "Moolatrikona",
    "Own Sign (Swa)",
    "Friendly Sign (Mitra)",
    "Neutral Sign (Sama)",
    "Enemy Sign (Shatru)",
    "Debilitated (Neecha)",
    "Node",
})

#: The one certified value that denotes debilitation. Exact, not a prefix.
DEBILITATED_DIGNITY = "Debilitated (Neecha)"


def _strict_bool(value: Any, what: str) -> bool:
    """A CERTIFIED boolean, not a truthy value.

    `bool(...)` would read the string "False" as True and the integer 1 as True.
    Neither is a certified boolean, and coercing them turns malformed data into
    astrology. This is the authority boundary, so the type is checked exactly.
    """
    if type(value) is not bool:
        raise D5OperationalError(f"{what} is not a certified boolean")
    return value


def _strict_sign_index(value: Any, what: str) -> int:
    """A certified 0..11 sign index.

    `type(...) is int` rather than isinstance: a bool IS an int in Python, so
    `d9_sign_index = True` would otherwise pass as Taurus — QA demonstrated that
    reaching HTTP 200 and materially changing the Final Score.
    """
    if type(value) is not int or not 0 <= value <= 11:
        raise D5OperationalError(f"{what} is not a certified sign index")
    return value


def _strict_dignity(value: Any, what: str) -> bool:
    """True when the dignity is EXACTLY the certified debilitation string.

    An unrecognised string raises rather than returning False. Reporting an
    unknown dignity as "not debilitated" would quietly clear a planet that the
    engine may have flagged, and the error would be invisible in the score.

    Equally, a near-miss must not be READ as debilitation: "Debilitated-ish" is
    not a verdict the engine ever emitted, and treating it as one would invent a
    weakening the chart does not carry.
    """
    if not isinstance(value, str) or value not in CERTIFIED_DIGNITIES:
        # Exact set membership. The `isinstance` guard comes first so an
        # UNHASHABLE value (a list, a dict) raises D5OperationalError rather
        # than a bare TypeError — malformed certified data must always surface
        # through the one error class the route maps to a neutral 503.
        raise D5OperationalError(f"{what} is not a certified dignity")
    return value == DEBILITATED_DIGNITY

#: TIM_03 needs exactly these two transiting bodies.
TRANSIT_BODIES: Tuple[str, ...] = ("Jupiter", "Saturn")


class D5OperationalError(D5DomainError):
    """A required certified operational source is unavailable or malformed.

    Distinct from a malformed snapshot: this is a SERVER-SIDE source gap, not a
    caller error, and the route maps it to a neutral correlated 503 rather than
    a 422.
    """


# ─────────────────────────────────────────────────────────────────────────────
# BIRTH TITHI — one shared primitive, called on certified natal longitudes
# ─────────────────────────────────────────────────────────────────────────────

def tithi_from_longitudes(moon_longitude: float, sun_longitude: float) -> int:
    """The accepted Moon-Sun Tithi, 1..30.

    THIS IS THE PRODUCT'S OWN FORMULA, FACTORED OUT — not a D5 alternative. The
    same expression already computes the CURRENT Tithi inside the accepted
    `/transits` handler; D5 needs the BIRTH Tithi, which is the identical
    calculation over the natal longitudes. Publishing it once means the two can
    never drift.

    The separation is circular, so a Moon behind the Sun wraps rather than going
    negative, and the arc is divided into thirty 12-degree Tithis.
    """
    for name, value in (("moon", moon_longitude), ("sun", sun_longitude)):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise D5OperationalError(f"{name} longitude is not a number")
    separation = (float(moon_longitude) - float(sun_longitude)) % 360.0
    return int(separation / 12.0) + 1


def birth_tithi(snapshot: Mapping[str, Any]) -> int:
    """The certified birth Tithi.

    OLD SNAPSHOTS REMAIN USABLE. A snapshot that already publishes `birth_tithi`
    is read directly; one minted before that field existed is derived from its
    certified natal Sun and Moon longitudes through the shared primitive above.
    Both paths produce the same number by construction, and a test asserts it.
    """
    # KEY ABSENT means an old snapshot and derives below. KEY PRESENT BUT NULL
    # is malformed certified data and is rejected — the two are different facts.
    if "birth_tithi" in snapshot:
        published = snapshot["birth_tithi"]
        # `type(...) is int` excludes bool, which would otherwise pass as 1.
        if type(published) is not int or not 1 <= published <= 30:
            raise D5OperationalError("published birth_tithi is not certified")
        return published
    planets = snapshot.get("planets")
    if not isinstance(planets, dict):
        raise D5OperationalError("snapshot lacks planets for Tithi derivation")
    try:
        moon = planets["Moon"]["longitude"]
        sun = planets["Sun"]["longitude"]
    except (KeyError, TypeError):
        raise D5OperationalError(
            "snapshot lacks certified natal Sun/Moon longitudes")
    return tithi_from_longitudes(moon, sun)


# ─────────────────────────────────────────────────────────────────────────────
# NATAL CONDITIONS — read, never recomputed
# ─────────────────────────────────────────────────────────────────────────────

def combustion_map(snapshot: Mapping[str, Any]) -> Dict[str, bool]:
    """The server-authoritative combustion boolean, per graha.

    READ, NOT RECOMPUTED. D5 introduces no combustion orb table and no
    Sun-distance arithmetic — the accepted engine runs one combustion pass after
    every longitude exists, and its verdict is the authority. Rahu, Ketu and the
    Sun are whatever that pass certified.
    """
    planets = snapshot.get("planets")
    if not isinstance(planets, dict):
        raise D5OperationalError("snapshot lacks planets")
    out: Dict[str, bool] = {}
    for graha in GRAHAS:
        record = planets.get(graha)
        if not isinstance(record, dict) or "combust" not in record:
            raise D5OperationalError("snapshot lacks certified combustion")
        out[graha] = _strict_bool(record["combust"], f"{graha} combustion")
    return out


def graha_yuddha_defeated(snapshot: Mapping[str, Any]) -> Dict[str, bool]:
    """The certified Graha Yuddha verdicts.

    READ when the snapshot publishes the flag for every graha; otherwise DERIVED
    through the SAME shared engine `main.py` certifies with, from the certified
    D1 sign indices and longitudes the snapshot already carries.

    OLD TOKENS STAY VALID. A snapshot minted before D5-008-CORR-01 has no flag,
    and it does not need one: the engine is pure, so deriving now gives exactly
    what certifying then would have. A test asserts the two paths agree.
    """
    planets = snapshot.get("planets")
    if not isinstance(planets, dict):
        raise D5OperationalError("snapshot lacks planets")
    published = {}
    for graha in GRAHAS:
        record = planets.get(graha)
        if not isinstance(record, dict) or "graha_yuddha_defeated" not in record:
            published = None
            break
        published[graha] = _strict_bool(record["graha_yuddha_defeated"],
                                        f"{graha} graha yuddha")
    if published is not None:
        return published
    try:
        return YUDDHA.defeated_map(planets)
    except YUDDHA.GrahaYuddhaError as exc:
        raise D5OperationalError(f"graha yuddha could not be derived: {exc}")


def d1_conditions(snapshot: Mapping[str, Any]) -> Dict[str, Dict[str, Any]]:
    """The D1 weakening facts TRI_01 reads, per graha.

    `debilitated` is mapped from the CERTIFIED D1 dignity string — dignity is
    never recalculated from sign or degree here. `combust` is the certified
    boolean.

    `graha_yuddha_defeated` IS NOW CERTIFIED. D5-008-B01 recorded that no
    implementation existed; the Founder supplied the doctrine in
    D5-008-CORR-01C, and one shared primitive now closes it. The flag is read
    from the snapshot where published and derived through that same engine
    otherwise — never defaulted.
    """
    planets = snapshot.get("planets")
    if not isinstance(planets, dict):
        raise D5OperationalError("snapshot lacks planets")
    combust = combustion_map(snapshot)
    yuddha = graha_yuddha_defeated(snapshot)
    out: Dict[str, Dict[str, Any]] = {}
    for graha in GRAHAS:
        record = planets.get(graha)
        if not isinstance(record, dict) or "dignity" not in record:
            raise D5OperationalError("snapshot lacks certified D1 dignity")
        out[graha] = {
            "combust": combust[graha],
            "debilitated": _strict_dignity(record["dignity"],
                                           f"{graha} D1 dignity"),
            "graha_yuddha_defeated": yuddha[graha],
        }
    return out


# ─────────────────────────────────────────────────────────────────────────────
# DASHA — read from the certified Vimshottari block
# ─────────────────────────────────────────────────────────────────────────────

def current_period(snapshot: Mapping[str, Any]) -> Tuple[Optional[str],
                                                          Optional[str]]:
    """The current Mahadasha and Antardasha lords.

    READ ONLY. No Vimshottari arithmetic runs in D5 — no boundary dates, no
    ladder walk, no proportional division. The accepted block already resolves
    which period is current, and its answer is taken as given.
    """
    block = snapshot.get("vimshottari") or snapshot.get("dasha")
    if not isinstance(block, dict):
        return None, None

    def lord_of(key: str) -> Optional[str]:
        """The lord, or None when the block genuinely has no current identity.

        A MALFORMED value is NOT quietly turned into None. `7` or `"NotAPlanet"`
        would then read as "there is no current lord", which the three-valued
        timing layer treats as a legitimate absence — so malformed data would
        silently become a known answer.
        """
        if key not in block:
            return None
        entry = block[key]
        if entry is None:
            return None
        if isinstance(entry, dict):
            for field in ("lord", "planet", "mahadasha", "antardasha", "name"):
                if field in entry:
                    value = entry[field]
                    if value is None:
                        return None
                    if not isinstance(value, str):
                        raise D5OperationalError(f"the {key} lord is malformed")
                    return value
            # A dict carrying none of the recognised lord fields is malformed
            # certified data, not an absence of identity.
            raise D5OperationalError(f"the {key} block names no lord")
        if not isinstance(entry, str):
            raise D5OperationalError(f"the {key} lord is malformed")
        return entry

    mahadasha, antardasha = (lord_of("current_mahadasha"),
                             lord_of("current_antardasha"))
    for label, lord in (("mahadasha", mahadasha), ("antardasha", antardasha)):
        # None stays permitted — the three-valued timing layer handles a genuinely
        # absent identity. A MALFORMED one must not become a known mismatch:
        # "NotAPlanet" would silently read as "this lord is not a participant".
        if lord is not None and lord not in GRAHAS:
            raise D5OperationalError(f"the current {label} lord is not a graha")
    return mahadasha, antardasha


# ─────────────────────────────────────────────────────────────────────────────
# D9 — certified signs, whole-sign relative houses, certified dignity
# ─────────────────────────────────────────────────────────────────────────────

def d9_facts(snapshot: Mapping[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Per graha: certified D9 sign, its whole-sign D9 house, certified D9
    dignity.

    THE SIGN IS READ, NOT DIVIDED. `d9_sign_index` is already certified by the
    accepted engine; no Navamsha calculation runs here.

    THE HOUSE IS DERIVED, NOT DIVIDED. It is whole-sign relative indexing over
    two already-certified sign positions:

        ((graha_d9_sign - d9_lagna_sign) % 12) + 1

    That is the same arithmetic the product uses for D1 houses, applied to D9
    signs it did not compute. It is a transformation, not a second Navamsha.

    DEBILITATION IS READ from the certified `d9_dignity`.
    """
    planets = snapshot.get("planets")
    lagna = snapshot.get("lagna")
    if not isinstance(planets, dict) or not isinstance(lagna, dict):
        raise D5OperationalError("snapshot lacks planets or lagna")
    if "d9_sign_index" not in lagna:
        raise D5OperationalError("snapshot lacks a certified D9 lagna sign")
    lagna_d9 = _strict_sign_index(lagna["d9_sign_index"], "D9 lagna sign")

    out: Dict[str, Dict[str, Any]] = {}
    for graha in GRAHAS:
        record = planets.get(graha)
        if not isinstance(record, dict):
            raise D5OperationalError("snapshot lacks a graha")
        if "d9_sign_index" not in record or "d9_dignity" not in record:
            raise D5OperationalError("snapshot lacks certified D9 facts")
        sign_index = _strict_sign_index(record["d9_sign_index"],
                                        f"{graha} D9 sign")
        out[graha] = {
            "sign_index": sign_index,
            "house": ((sign_index - lagna_d9) % 12) + 1,
            "debilitated": _strict_dignity(record["d9_dignity"],
                                           f"{graha} D9 dignity"),
        }
    return out


# ─────────────────────────────────────────────────────────────────────────────
# CURRENT TRANSITS — one shared provider, one snapshot per request
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class TransitSnapshot:
    """ONE current-transit reading, used by every surface in a request.

    TIM_03 and the public report read the SAME snapshot. Calling the provider
    again during payload assembly could return a different `as_of` and, at a
    sign boundary, a different sign — so the response would describe a transit
    the score was not computed from.
    """
    as_of: str
    sign_index_by_body: Mapping[str, int]

    def transit_signs(self) -> Dict[str, int]:
        return {body: self.sign_index_by_body[body] for body in TRANSIT_BODIES
                if body in self.sign_index_by_body}


#: The shared current-transit callable, injected at wiring time. D5 does NOT
#: import main.py, does NOT call swisseph, and does NOT make an HTTP request to
#: /transits — a loopback would be a second network dependency and could return
#: a different snapshot from the one the score used.
_transit_provider: Optional[Callable[[], Mapping[str, Any]]] = None


def configure_transit_provider(provider: Callable[[], Mapping[str, Any]]) -> None:
    global _transit_provider
    _transit_provider = provider


def transit_provider_configured() -> bool:
    return _transit_provider is not None


def read_current_transits() -> TransitSnapshot:
    """One call to the shared provider, one snapshot back.

    FAILS CLOSED when unconfigured: a deployment that forgot to wire the shared
    transit callable must not silently score TIM_03 as unresolved forever, it
    must say so.
    """
    if _transit_provider is None:
        raise D5OperationalError("the current-transit provider is not configured")
    payload = _transit_provider()
    if not isinstance(payload, dict):
        raise D5OperationalError("the transit provider returned no snapshot")
    planets = payload.get("planets")
    if not isinstance(planets, dict):
        raise D5OperationalError("the transit snapshot lacks planets")
    signs: Dict[str, int] = {}
    for body in TRANSIT_BODIES:
        record = planets.get(body)
        if not isinstance(record, dict) or "sign_index" not in record:
            raise D5OperationalError("the transit snapshot lacks a body")
        signs[body] = _strict_sign_index(record["sign_index"],
                                         f"{body} transit sign")
    as_of = payload.get("date_utc") or payload.get("as_of")
    if not isinstance(as_of, str):
        raise D5OperationalError("the transit snapshot lacks an as_of stamp")
    return TransitSnapshot(as_of=as_of, sign_index_by_body=signs)


# ─────────────────────────────────────────────────────────────────────────────
# THE ROOT FACTS
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class OperationalFacts:
    """Every certified operational fact one request needs, gathered once."""
    moon_tithi: int
    combust_by_graha: Mapping[str, bool]
    d1_conditions: Mapping[str, Mapping[str, Any]]
    mahadasha_lord: Optional[str]
    antardasha_lord: Optional[str]
    d9_facts: Mapping[str, Mapping[str, Any]]
    transits: TransitSnapshot
    graha_yuddha_available: bool = True

    def rule_inputs(self) -> R.D5RuleInputs:
        return R.D5RuleInputs(moon_tithi=self.moon_tithi,
                              combust_by_graha=dict(self.combust_by_graha))

    def source_status(self) -> Dict[str, str]:
        """Bounded provenance for the public block. No values, only sourcing."""
        return {
            "moon_tithi": "certified",
            "combustion": "certified",
            "d1_dignity": "certified",
            "d9": "certified",
            "dasha": "certified" if (self.mahadasha_lord
                                     and self.antardasha_lord) else "unavailable",
            "transit": "certified",
            "graha_yuddha": ("certified" if self.graha_yuddha_available
                             else "unavailable"),
        }


def build_operational_facts(snapshot: Mapping[str, Any]) -> OperationalFacts:
    """Gather every certified operational fact. ONE transit call."""
    mahadasha, antardasha = current_period(snapshot)
    return OperationalFacts(
        moon_tithi=birth_tithi(snapshot),
        combust_by_graha=combustion_map(snapshot),
        d1_conditions=d1_conditions(snapshot),
        mahadasha_lord=mahadasha,
        antardasha_lord=antardasha,
        d9_facts=d9_facts(snapshot),
        transits=read_current_transits(),
        # D5-008-B01 RESOLVED · the shared certified primitive now answers.
        graha_yuddha_available=True,
    )


def build_temporal_inputs(facts: OperationalFacts,
                          positive_fired_yoga_participants,
                          d5_raj_yoga_participants) -> X.TemporalInputs:
    """`TemporalInputs` from certified facts plus the DERIVED participant sets.

    The two participant sets are never read from a caller — they are derived
    from the same static outcomes that will later be scored, so the participants
    and the score can never describe different evaluations.
    """
    return X.TemporalInputs(
        mahadasha_lord=facts.mahadasha_lord,
        antardasha_lord=facts.antardasha_lord,
        transit_signs=facts.transits.transit_signs(),
        positive_fired_yoga_participants=positive_fired_yoga_participants,
        d5_raj_yoga_participants=d5_raj_yoga_participants,
        d1_conditions={g: dict(c) for g, c in facts.d1_conditions.items()},
        d9_facts={g: dict(f) for g, f in facts.d9_facts.items()},
    )
