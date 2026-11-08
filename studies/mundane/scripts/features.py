"""Sign-level transit-to-natal features for the mundane study.

Everything here is sidereal (Lahiri) and uses ``libs/vedic_astrology_core``.
A country whose founding time is unknown gets a natal chart computed at local
noon with ``houses = None``; ``time_known`` is copied onto every feature row so
no later analysis can quietly treat the noon placeholder as a real chart.

Features at sign level only:

* transit planet sign relative to each natal planet sign (signs between,
  conjunct-by-sign, opposition-by-sign, whole-sign Parashari aspect);
* eclipses within N days (Swiss Ephemeris global solar / lunar search);
* Sun ingresses within N days;
* planetary stations within N days (sign change of the longitude speed).
"""

import sys
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

import swisseph as swe

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "libs"))
from vedic_astrology_core.astrology.ephemeris import EphemerisEngine  # noqa: E402
from vedic_astrology_core.config.constants import Planet, PlanetDict  # noqa: E402

TRANSIT_PLANETS = (
    Planet.SUN,
    Planet.MOON,
    Planet.MARS,
    Planet.MERCURY,
    Planet.JUPITER,
    Planet.VENUS,
    Planet.SATURN,
    Planet.RAHU,
    Planet.KETU,
)
NATAL_PLANETS = TRANSIT_PLANETS
STATION_PLANETS = (
    Planet.MARS,
    Planet.MERCURY,
    Planet.JUPITER,
    Planet.VENUS,
    Planet.SATURN,
)
# Whole-sign Parashari aspects as house offsets counted from the aspecting
# planet's own sign (1 = same sign, 7 = opposite). Rahu and Ketu use the 5-7-9
# convention several schools apply to them; it is a rule choice, not a fact.
ASPECT_OFFSETS: Dict[Planet, frozenset] = {
    Planet.SUN: frozenset({7}),
    Planet.MOON: frozenset({7}),
    Planet.MERCURY: frozenset({7}),
    Planet.VENUS: frozenset({7}),
    Planet.MARS: frozenset({4, 7, 8}),
    Planet.JUPITER: frozenset({5, 7, 9}),
    Planet.SATURN: frozenset({3, 7, 10}),
    Planet.RAHU: frozenset({5, 7, 9}),
    Planet.KETU: frozenset({5, 7, 9}),
}
LOCAL_NOON = time(12, 0)
_ENGINE: Optional[EphemerisEngine] = None


def get_engine() -> EphemerisEngine:
    """Return a shared Lahiri / mean-node ephemeris engine."""
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = EphemerisEngine()
    return _ENGINE


def local_datetime(day: date, tz_name: str, at: time = LOCAL_NOON) -> datetime:
    """Return ``day`` at ``at`` in ``tz_name`` as an aware datetime."""
    return datetime.combine(day, at, tzinfo=ZoneInfo(tz_name))


def _jd(dt: datetime, engine: EphemerisEngine) -> float:
    if dt.tzinfo is None:
        raise ValueError("naive datetime: attach a ZoneInfo before computing")
    return engine.datetime_to_julian_day(dt)


def planet_signs(dt: datetime, engine: Optional[EphemerisEngine] = None) -> PlanetDict:
    """Return ``PlanetDict`` of 0-based sidereal sign indices (Aries = 0)."""
    engine = engine or get_engine()
    positions = engine.get_all_planet_positions(_jd(dt, engine))
    return PlanetDict({p: pos["sign"] for p, pos in positions.items()})


def natal_chart(
    country: Dict[str, Any], engine: Optional[EphemerisEngine] = None
) -> Dict[str, Any]:
    """Natal planet signs for a country entry; houses only with a sourced time."""
    engine = engine or get_engine()
    f = country["founding"]
    known = bool(f.get("time_known")) and f.get("time") is not None
    at = time.fromisoformat(f["time"]) if known else LOCAL_NOON
    day = date.fromisoformat(f["date"]) if isinstance(f["date"], str) else f["date"]
    dt = local_datetime(day, country["timezone"], at)
    return {
        "iso": country["iso"],
        "datetime": dt,
        "time_known": known,
        "signs": planet_signs(dt, engine),
        # Houses need a lagna, which needs a sourced time. Never faked.
        "houses": None,
    }


def sign_relation(transit_sign: int, natal_sign: int, planet: Planet) -> Dict[str, Any]:
    """Sign-level relation of a transit planet to a natal planet's sign."""
    between = (natal_sign - transit_sign) % 12  # signs from transit to natal
    offset = between + 1  # house count from the transit planet's sign
    return {
        "signs_between": between,
        "conjunct_sign": between == 0,
        "opposition_sign": between == 6,
        "aspect_whole_sign": offset in ASPECT_OFFSETS[planet],
    }


def transit_natal_rows(
    natal: Dict[str, Any], transit: PlanetDict
) -> List[Dict[str, Any]]:
    """One row per (transit planet, natal planet) pair."""
    rows = []
    for tp in TRANSIT_PLANETS:
        for npl in NATAL_PLANETS:
            row = {
                "family": "transit_natal",
                "transit_planet": tp.name,
                "natal_planet": npl.name,
                "transit_sign": transit[tp],
                "natal_sign": natal["signs"][npl],
                "time_known": natal["time_known"],
            }
            row.update(sign_relation(transit[tp], natal["signs"][npl], tp))
            rows.append(row)
    return rows


def _sign_at(engine: EphemerisEngine, jd: float, planet: Planet) -> int:
    return engine.get_planet_position(jd, planet)["sign"]


def _speed_at(engine: EphemerisEngine, jd: float, planet: Planet) -> float:
    return engine.get_planet_position(jd, planet)["longitude_speed"]


def _bisect(fn, lo: float, hi: float, steps: int = 40) -> float:
    """Find the transition of the boolean ``fn`` between ``lo`` and ``hi``."""
    flo = fn(lo)
    for _ in range(steps):
        mid = (lo + hi) / 2
        if fn(mid) == flo:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def sun_ingresses(
    jd: float, days: float, engine: Optional[EphemerisEngine] = None
) -> List[Dict[str, Any]]:
    """Sidereal Sun sign changes within ``days`` of ``jd``."""
    engine = engine or get_engine()
    out = []
    start = jd - days
    n = int(2 * days)
    prev_jd, prev_sign = start, _sign_at(engine, start, Planet.SUN)
    for i in range(1, n + 2):
        cur = min(start + i, jd + days)
        sign = _sign_at(engine, cur, Planet.SUN)
        if sign != prev_sign:
            t = _bisect(
                lambda x: _sign_at(engine, x, Planet.SUN) == prev_sign, prev_jd, cur
            )
            out.append(
                {
                    "family": "ingress",
                    "planet": "SUN",
                    "days_offset": round(t - jd, 3),
                    "to_sign": sign,
                }
            )
        prev_jd, prev_sign = cur, sign
    return out


def stations(
    jd: float, days: float, engine: Optional[EphemerisEngine] = None
) -> List[Dict[str, Any]]:
    """Find planetary stations within ``days`` of ``jd``."""
    engine = engine or get_engine()
    out = []
    start = jd - days
    n = int(2 * days)
    for planet in STATION_PLANETS:
        prev_jd, prev_v = start, _speed_at(engine, start, planet)
        for i in range(1, n + 2):
            cur = min(start + i, jd + days)
            v = _speed_at(engine, cur, planet)
            if (v < 0) != (prev_v < 0):
                t = _bisect(lambda x: _speed_at(engine, x, planet) < 0, prev_jd, cur)
                out.append(
                    {
                        "family": "station",
                        "planet": planet.name,
                        "days_offset": round(t - jd, 3),
                        "kind": "retrograde" if v < 0 else "direct",
                        "sign": _sign_at(engine, t, planet),
                    }
                )
            prev_jd, prev_v = cur, v
    return out


def eclipses(
    jd: float, days: float, engine: Optional[EphemerisEngine] = None
) -> List[Dict[str, Any]]:
    """Find global solar and lunar eclipses within ``days`` of ``jd``."""
    engine = engine or get_engine()
    out = []
    for kind, finder in (
        ("solar", lambda t, b: swe.sol_eclipse_when_glob(t, swe.FLG_SWIEPH, 0, b)),
        ("lunar", lambda t, b: swe.lun_eclipse_when(t, swe.FLG_SWIEPH, 0, b)),
    ):
        for back in (False, True):
            t, cursor = None, jd
            for _ in range(4):  # a handful of eclipses per window at most
                tret = finder(cursor, back)[1]
                t = tret[0]
                if abs(t - jd) > days:
                    break
                out.append(
                    {
                        "family": "eclipse",
                        "kind": kind,
                        "days_offset": round(t - jd, 3),
                        "sign": _sign_at(engine, t, Planet.SUN),
                    }
                )
                cursor = t + (-1 if back else 1)
    seen, uniq = set(), []
    for row in sorted(out, key=lambda r: r["days_offset"]):
        key = (row["kind"], row["days_offset"])
        if key not in seen:
            seen.add(key)
            uniq.append(row)
    return uniq


def moment_features(
    country: Dict[str, Any],
    when: datetime,
    *,
    window_days: int = 30,
    natal: Optional[Dict[str, Any]] = None,
    engine: Optional[EphemerisEngine] = None,
) -> List[Dict[str, Any]]:
    """All feature rows for ``country`` at the aware datetime ``when``."""
    engine = engine or get_engine()
    natal = natal or natal_chart(country, engine)
    jd = _jd(when, engine)
    rows = transit_natal_rows(natal, planet_signs(when, engine))
    rows += eclipses(jd, window_days, engine)
    rows += sun_ingresses(jd, window_days, engine)
    rows += stations(jd, window_days, engine)
    for row in rows:
        row["time_known"] = natal["time_known"]
        row["iso"] = country["iso"]
        row["when"] = when.isoformat()
        row["window_days"] = window_days
    return rows


def window_end(when: datetime, days: int) -> datetime:
    """Return ``when`` plus ``days``, keeping the tzinfo."""
    return when + timedelta(days=days)
