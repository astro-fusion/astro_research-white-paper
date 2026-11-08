"""Generate ``tests/fixtures/golden_charts.json`` from independent oracles.

Oracles
-------
* pyswisseph (Swiss Ephemeris) with ``FLG_SIDEREAL`` and ``SIDM_LAHIRI``:
  sidereal longitudes, speeds, ascendant, house cusps and the ayanamsa.
* PyJHora (a Python port of Jagannatha Hora 8): Vimshottari dasha at three
  levels, the Parashari varga mappings, nakshatra/pada and its combustion list.

PyJHora is not installed. Point ``PYJHORA_SRC`` (or the default path below) at
the ``src`` directory of a read-only clone; this script never writes to it. The
PyJHora network helpers (geocoder, geopy, timezonefinder) are stubbed because
only offline functions are used.

Usage::

    PYJHORA_SRC=/path/to/PyJHora/src python tests/fixtures/generate_golden_charts.py

The library under test (``libs/vedic_astrology_core``) is never imported here,
so the fixture cannot inherit its bugs.
"""

from __future__ import annotations

import importlib.metadata
import json
import os
import random
import subprocess
import sys
import types
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import swisseph as swe

HERE = Path(__file__).resolve().parent
OUT_PATH = HERE / "golden_charts.json"
DEFAULT_PYJHORA_SRC = "/Users/bishalghimire/Documents/WORK/Open Source/PyJHora/src"
PYJHORA_SRC = os.environ.get("PYJHORA_SRC", DEFAULT_PYJHORA_SRC)

EPHE_PATH = os.path.join(PYJHORA_SRC, "jhora", "data", "ephe")
FLAGS = swe.FLG_SWIEPH | swe.FLG_SPEED | swe.FLG_SIDEREAL
DASHA_YEAR_DAYS = 365.25
RANDOM_SEED = 20261108
NAK_SPAN = 360.0 / 27.0

BODIES = {
    "SUN": swe.SUN,
    "MOON": swe.MOON,
    "MARS": swe.MARS,
    "MERCURY": swe.MERCURY,
    "JUPITER": swe.JUPITER,
    "VENUS": swe.VENUS,
    "SATURN": swe.SATURN,
}
# PyJHora planet ids: 0 Sun .. 6 Saturn, 7 Rahu, 8 Ketu.
JH_ID_TO_NAME = {
    0: "SUN",
    1: "MOON",
    2: "MARS",
    3: "MERCURY",
    4: "JUPITER",
    5: "VENUS",
    6: "SATURN",
    7: "RAHU",
    8: "KETU",
}
VIMSHOTTARI_NAMES = {
    0: "Sun",
    1: "Moon",
    2: "Mars",
    3: "Mercury",
    4: "Jupiter",
    5: "Venus",
    6: "Saturn",
    7: "Rahu",
    8: "Ketu",
}
# Surya Siddhanta combustion orbs (direct, retrograde); Sun and nodes excluded.
COMBUSTION_ORBS = {
    "MOON": (12.0, 12.0),
    "MARS": (17.0, 17.0),
    "MERCURY": (14.0, 12.0),
    "JUPITER": (11.0, 11.0),
    "VENUS": (10.0, 8.0),
    "SATURN": (15.0, 15.0),
}
VARGA_FACTORS = [1, 2, 3, 4, 7, 9, 10, 12, 16, 20, 24, 27, 30, 40, 45, 60]
D30_ODD = [(0, 5), (5, 10), (10, 18), (18, 25), (25, 30)]
D30_EVEN = [(0, 5), (5, 12), (12, 20), (20, 25), (25, 30)]


def _load_pyjhora():
    """Import PyJHora from its source tree with network helpers stubbed."""
    for name in ("geocoder", "timezonefinder", "geopy", "geopy.geocoders"):
        try:
            __import__(name)
        except ImportError:
            stub = types.ModuleType(name)
            stub.TimezoneFinder = object
            stub.Nominatim = object
            sys.modules[name] = stub
    sys.path.insert(0, PYJHORA_SRC)
    from jhora import _package_info, const  # noqa: E402

    # Dasha year convention: mean year of 365.25 days (the library default).
    const.dhasa_year_duration_default = const.DHASA_YEAR_DURATION.MEAN_SIDEREAL_YEAR
    const.sidereal_year = DASHA_YEAR_DAYS
    const.default_dasha_sesham_method = const.DASHA_SESHAM_METHOD.STANDARD
    from jhora.panchanga import drik  # noqa: E402

    drik.set_ayanamsa_mode("LAHIRI")
    # Apparent geocentric positions, identical flags to the swisseph oracle.
    drik.PLANET_FLAGS = FLAGS
    from jhora.horoscope.chart import charts  # noqa: E402
    from jhora.horoscope.dhasa.graha import vimsottari  # noqa: E402

    # Use the Swiss Ephemeris .se1 files shipped with PyJHora, explicitly.
    swe.set_ephe_path(EPHE_PATH)

    return _package_info, const, drik, charts, vimsottari


def _git_head(path: str) -> str:
    try:
        out = subprocess.run(
            ["git", "-C", path, "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return out.stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def _sid_mode() -> None:
    swe.set_sid_mode(swe.SIDM_LAHIRI, 0.0, 0.0)


def _jd_ut(dt_utc: datetime) -> float:
    hour = (
        dt_utc.hour
        + dt_utc.minute / 60
        + (dt_utc.second + dt_utc.microsecond / 1e6) / 3600
    )
    return swe.julday(dt_utc.year, dt_utc.month, dt_utc.day, hour, swe.GREG_CAL)


def _jd_to_utc(jd: float) -> datetime:
    y, m, d, h = swe.revjul(jd, swe.GREG_CAL)
    return datetime(y, m, d, tzinfo=timezone.utc) + timedelta(hours=h)


def chart_specs():
    """Return the 24 chart definitions as (id, label, place, lat, lon, tz, utc)."""

    def local(y, mo, d, h, mi, tz):
        return datetime(y, mo, d, h, mi, tzinfo=ZoneInfo(tz)).astimezone(timezone.utc)

    specs = [
        (
            "ktm_1990",
            "Kathmandu 1990",
            "Kathmandu",
            27.7172,
            85.3240,
            "Asia/Kathmandu",
            local(1990, 5, 15, 10, 30, "Asia/Kathmandu"),
        ),
        (
            "ktm_2015",
            "Nepal constitution 17:00 NPT",
            "Kathmandu",
            27.7172,
            85.3240,
            "Asia/Kathmandu",
            local(2015, 9, 20, 17, 0, "Asia/Kathmandu"),
        ),
        (
            "ktm_1955",
            "Kathmandu 1955",
            "Kathmandu",
            27.7172,
            85.3240,
            "Asia/Kathmandu",
            local(1955, 2, 10, 6, 15, "Asia/Kathmandu"),
        ),
        (
            "del_1947",
            "India independence",
            "Delhi",
            28.6139,
            77.2090,
            "Asia/Kolkata",
            local(1947, 8, 15, 0, 0, "Asia/Kolkata"),
        ),
        (
            "del_1984",
            "Delhi 1984",
            "Delhi",
            28.6139,
            77.2090,
            "Asia/Kolkata",
            local(1984, 8, 27, 10, 30, "Asia/Kolkata"),
        ),
        (
            "del_2030",
            "Delhi 2030",
            "Delhi",
            28.6139,
            77.2090,
            "Asia/Kolkata",
            local(2030, 3, 1, 18, 45, "Asia/Kolkata"),
        ),
        (
            "del_2000",
            "Delhi 2000-08-30 noon UTC",
            "Delhi",
            28.6139,
            77.2090,
            "UTC",
            datetime(2000, 8, 30, 12, 0, tzinfo=timezone.utc),
        ),
        (
            "lon_1900",
            "London 1900",
            "London",
            51.5074,
            -0.1278,
            "Europe/London",
            local(1900, 1, 1, 12, 0, "Europe/London"),
        ),
        (
            "lon_1969",
            "London 1969",
            "London",
            51.5074,
            -0.1278,
            "Europe/London",
            local(1969, 7, 20, 20, 17, "Europe/London"),
        ),
        (
            "lon_2050",
            "London 2050",
            "London",
            51.5074,
            -0.1278,
            "Europe/London",
            local(2050, 12, 31, 23, 0, "Europe/London"),
        ),
        (
            "grw_j2000",
            "Greenwich J2000",
            "Greenwich",
            51.4769,
            0.0,
            "UTC",
            datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc),
        ),
        (
            "nyc_1929",
            "New York 1929",
            "New York",
            40.7128,
            -74.0060,
            "America/New_York",
            local(1929, 10, 29, 9, 30, "America/New_York"),
        ),
        (
            "nyc_2001",
            "New York 2001",
            "New York",
            40.7128,
            -74.0060,
            "America/New_York",
            local(2001, 9, 11, 8, 46, "America/New_York"),
        ),
        (
            "nyc_2044",
            "New York 2044",
            "New York",
            40.7128,
            -74.0060,
            "America/New_York",
            local(2044, 7, 4, 12, 0, "America/New_York"),
        ),
        (
            "syd_1932",
            "Sydney 1932",
            "Sydney",
            -33.8688,
            151.2093,
            "Australia/Sydney",
            local(1932, 3, 19, 11, 0, "Australia/Sydney"),
        ),
        (
            "syd_1973",
            "Sydney 1973",
            "Sydney",
            -33.8688,
            151.2093,
            "Australia/Sydney",
            local(1973, 10, 20, 15, 0, "Australia/Sydney"),
        ),
        (
            "syd_2024",
            "Sydney 2024",
            "Sydney",
            -33.8688,
            151.2093,
            "Australia/Sydney",
            local(2024, 2, 29, 6, 0, "Australia/Sydney"),
        ),
        (
            "polar_2010",
            "Longyearbyen (polar)",
            "Longyearbyen",
            78.2232,
            15.6267,
            "Arctic/Longyearbyen",
            local(2010, 1, 15, 13, 0, "Arctic/Longyearbyen"),
        ),
    ]

    _sid_mode()
    # Moon at the middle of a nakshatra (elapsed fraction exactly 0.5).
    for cid, label, place, lat, lon, tz, start, nak in [
        (
            "del_mid_nak",
            "Delhi Moon mid-nakshatra",
            "Delhi",
            28.6139,
            77.2090,
            "Asia/Kolkata",
            datetime(1977, 6, 1, tzinfo=timezone.utc),
            11,
        ),
        (
            "ktm_mid_nak",
            "Kathmandu Moon mid-nakshatra",
            "Kathmandu",
            27.7172,
            85.3240,
            "Asia/Kathmandu",
            datetime(2008, 11, 11, tzinfo=timezone.utc),
            20,
        ),
        (
            "lon_mid_nak",
            "London Moon mid-nakshatra",
            "London",
            51.5074,
            -0.1278,
            "Europe/London",
            datetime(1918, 11, 11, tzinfo=timezone.utc),
            3,
        ),
    ]:
        target = nak * NAK_SPAN + NAK_SPAN / 2
        jd = swe.mooncross_ut(target, _jd_ut(start), FLAGS)
        specs.append((cid, label, place, lat, lon, tz, _jd_to_utc(jd)))

    # Near sidereal 0 deg Aries: Sun one hour before / after the ingress, and
    # the Moon 30 minutes after crossing 0 deg.
    jd = swe.solcross_ut(0.0, _jd_ut(datetime(1950, 3, 1, tzinfo=timezone.utc)), FLAGS)
    specs.append(
        (
            "del_sun_pre_aries",
            "Sun 1 h before 0 Aries",
            "Delhi",
            28.6139,
            77.2090,
            "Asia/Kolkata",
            _jd_to_utc(jd - 1.0 / 24.0),
        )
    )
    jd = swe.solcross_ut(0.0, _jd_ut(datetime(2021, 3, 1, tzinfo=timezone.utc)), FLAGS)
    specs.append(
        (
            "ktm_sun_post_aries",
            "Sun 1 h after 0 Aries",
            "Kathmandu",
            27.7172,
            85.3240,
            "Asia/Kathmandu",
            _jd_to_utc(jd + 1.0 / 24.0),
        )
    )
    jd = swe.mooncross_ut(0.0, _jd_ut(datetime(1999, 6, 1, tzinfo=timezone.utc)), FLAGS)
    specs.append(
        (
            "nyc_moon_aries",
            "Moon 30 min after 0 Aries",
            "New York",
            40.7128,
            -74.0060,
            "America/New_York",
            _jd_to_utc(jd + 0.5 / 24.0),
        )
    )
    return specs


def swisseph_chart(jd: float, lat: float, lon: float) -> dict:
    """Compute positions, nodes, ascendant and cusps with pyswisseph."""
    _sid_mode()
    bodies = {}
    retflags = set()
    for name, body in BODIES.items():
        xx, ret = swe.calc_ut(jd, body, FLAGS)
        retflags.add(ret & (swe.FLG_SWIEPH | swe.FLG_MOSEPH | swe.FLG_JPLEPH))
        bodies[name] = {"longitude": xx[0] % 360.0, "speed": xx[3]}
    for model, body in (("mean", swe.MEAN_NODE), ("true", swe.TRUE_NODE)):
        xx, _ = swe.calc_ut(jd, body, FLAGS)
        rahu = xx[0] % 360.0
        bodies[f"RAHU_{model.upper()}"] = {"longitude": rahu, "speed": xx[3]}
        bodies[f"KETU_{model.upper()}"] = {
            "longitude": (rahu + 180.0) % 360.0,
            "speed": xx[3],
        }
    cusps_w, ascmc = swe.houses_ex(jd, lat, lon, b"W", swe.FLG_SIDEREAL)
    out = {
        "ayanamsa": swe.get_ayanamsa_ut(jd),
        "ascendant": ascmc[0] % 360.0,
        "mc": ascmc[1] % 360.0,
        "cusps_whole_sign": [c % 360.0 for c in cusps_w[:12]],
        "bodies": bodies,
        "ephemeris_retflags": sorted(retflags),
    }
    if abs(lat) < 66.0:
        cusps_p, _ = swe.houses_ex(jd, lat, lon, b"P", swe.FLG_SIDEREAL)
        out["cusps_placidus"] = [c % 360.0 for c in cusps_p[:12]]
    return out


def expected_combustion(bodies: dict) -> list:
    """Planets combust under the Surya Siddhanta orbs (Sun and nodes excluded)."""
    sun = bodies["SUN"]["longitude"]
    combust = []
    for name, (direct, retro) in COMBUSTION_ORBS.items():
        b = bodies[name]
        orb = retro if b["speed"] < 0 else direct
        diff = abs(b["longitude"] - sun) % 360.0
        diff = min(diff, 360.0 - diff)
        if diff <= orb:
            combust.append(name)
    return combust


def _rasi_list(points: dict) -> list:
    return [[key, (int(lon // 30) % 12, lon % 30)] for key, lon in points.items()]


def pyjhora_vargas(charts, points: dict) -> dict:
    """Map each point to its varga sign using PyJHora's Parashara methods."""
    funcs = {
        2: (charts.hora_chart, 2),  # Traditional Parashara hora (Sun/Moon)
        3: (charts.drekkana_chart, 1),
        4: (charts.chaturthamsa_chart, 1),
        7: (charts.saptamsa_chart, 1),
        9: (charts.navamsa_chart, 1),
        10: (charts.dasamsa_chart, 1),
        12: (charts.dwadasamsa_chart, 1),
        16: (charts.shodasamsa_chart, 1),
        20: (charts.vimsamsa_chart, 1),
        24: (charts.chaturvimsamsa_chart, 1),
        27: (charts.nakshatramsa_chart, 1),
        30: (charts.trimsamsa_chart, 1),
        40: (charts.khavedamsa_chart, 1),
        45: (charts.akshavedamsa_chart, 1),
        60: (charts.shashtyamsa_chart, 1),
    }
    rasi = _rasi_list(points)
    result = {"D1": {k: int(lon // 30) % 12 for k, lon in points.items()}}
    for factor in VARGA_FACTORS[1:]:
        fn, method = funcs[factor]
        result[f"D{factor}"] = {
            key: int(sign) for key, (sign, _) in fn(rasi, chart_method=method)
        }
    return result


def varga_mid_points(charts) -> dict:
    """Return [longitude, sign] pairs at the middle of every varga part."""
    tables = {}
    for factor in VARGA_FACTORS:
        lons = []
        for sign in range(12):
            if factor == 30:
                segs = D30_ODD if sign % 2 == 0 else D30_EVEN
                lons += [sign * 30 + (a + b) / 2.0 for a, b in segs]
            else:
                width = 30.0 / factor
                lons += [sign * 30 + (k + 0.5) * width for k in range(factor)]
        points = {i: lon for i, lon in enumerate(lons)}
        signs = pyjhora_vargas(charts, points)[f"D{factor}"]
        tables[f"D{factor}"] = [[round(lon, 9), signs[i]] for i, lon in points.items()]
    return tables


def _lords(names):
    return [VIMSHOTTARI_NAMES[n] for n in names]


def pyjhora_dasha(vimsottari, drik, const, jd_ut: float, lat: float, lon: float):
    """Three-level Vimshottari from PyJHora, start times as JD (UT)."""
    tz_hours = 0.0
    place = drik.Place("golden", lat, lon, tz_hours)
    out = {}
    for level in (1, 2, 3):
        _, rows = vimsottari.get_dhasa_bhukthi(jd_ut, place, dhasa_level_index=level)
        out[level] = [
            [_lords(lords), swe.julday(y, m, d, h, swe.GREG_CAL), years]
            for lords, (y, m, d, h), years in rows
        ]
    moon = drik.sidereal_longitude(jd_ut, const._MOON)
    return moon, out


def _trim_dasha(levels: dict, jd_birth: float) -> dict:
    """Keep all MDs and ADs and the pratyantaras of the MD running at birth."""
    md = levels[1]
    running = None
    for i, (lords, start, _) in enumerate(md):
        end = md[i + 1][1] if i + 1 < len(md) else start + 1e9
        if start <= jd_birth < end:
            running = lords[0]
    return {
        "level1": [[r[0], round(r[1], 6)] for r in md],
        "level2": [[r[0], round(r[1], 6)] for r in levels[2]],
        "level3_birth_md": [
            [r[0], round(r[1], 6)] for r in levels[3] if r[0][0] == running
        ],
    }


def component_dasha(vimsottari, drik, moon: float, jd_birth: float) -> dict:
    """Three-level dasha tree from PyJHora's own building blocks.

    Used for arbitrary Moon longitudes, and for charts where PyJHora's
    end-to-end path cannot run (its Placidus ascendant fails at polar
    latitudes even though the dasha does not depend on it).
    """
    place = drik.Place("golden", 0.0, 0.0, 0.0)
    nak = int(moon / NAK_SPAN)
    frac = (moon - nak * NAK_SPAN) / NAK_SPAN
    lord = vimsottari.vimsottari_adhipati(nak)
    start = drik._get_dhasa_start_jd(
        jd_birth,
        place,
        fraction_elapsed=frac,
        total_dasa_years=vimsottari.vimsottari_dict[lord],
    )
    level1, level2, level3 = [], [], []
    md_lord, md_start = lord, start
    for _ in range(9):
        md_end = drik._get_dhasa_end_jd(
            md_start, place, vimsottari.vimsottari_dict[md_lord]
        )
        level1.append([_lords([md_lord]), round(md_start, 6)])
        running = md_start <= jd_birth < md_end
        bhuktis = vimsottari._vimsottari_bhukti(md_lord, md_start, place)
        for b_lord, b_start in bhuktis.items():
            level2.append([_lords([md_lord, b_lord]), round(b_start, 6)])
            if running:
                antara = vimsottari._vimsottari_antara(md_lord, b_lord, b_start, place)
                for a_lord, a_start in antara.items():
                    level3.append(
                        [_lords([md_lord, b_lord, a_lord]), round(a_start, 6)]
                    )
        md_lord = vimsottari.vimsottari_next_adhipati(md_lord)
        md_start = md_end
    return {"level1": level1, "level2": level2, "level3_birth_md": level3}


def random_moon_dashas(vimsottari, drik, n: int = 12) -> list:
    """Dasha trees for seeded random Moon longitudes and birth times."""
    rng = random.Random(RANDOM_SEED)
    lo = _jd_ut(datetime(1900, 1, 1, tzinfo=timezone.utc))
    hi = _jd_ut(datetime(2050, 1, 1, tzinfo=timezone.utc))
    cases = []
    for _ in range(n):
        moon = rng.uniform(0.0, 360.0)
        jd_birth = rng.uniform(lo, hi)
        case = {"moon_longitude": moon, "birth_jd_ut": jd_birth}
        case.update(component_dasha(vimsottari, drik, moon, jd_birth))
        cases.append(case)
    return cases


def _dump(fixture: dict) -> str:
    """Serialise with one chart / case / varga table per line (diff-friendly)."""
    compact = {"separators": (",", ":")}
    parts = ['"provenance":' + json.dumps(fixture["provenance"], indent=1)]
    for key in ("charts", "dasha_random_moon"):
        rows = ",\n".join(json.dumps(row, **compact) for row in fixture[key])
        parts.append(f'"{key}":[\n{rows}\n]')
    tables = ",\n".join(
        f"{json.dumps(k)}:{json.dumps(v, **compact)}"
        for k, v in fixture["varga_mid_points"].items()
    )
    parts.append(f'"varga_mid_points":{{\n{tables}\n}}')
    return "{\n" + ",\n".join(parts) + "\n}\n"


def main() -> None:
    """Build the golden fixture and write it to disk."""
    package_info, const, drik, charts, vimsottari = _load_pyjhora()
    retflags = set()
    out_charts = []
    for cid, label, place, lat, lon, tz, dt_utc in chart_specs():
        jd = _jd_ut(dt_utc)
        sw = swisseph_chart(jd, lat, lon)
        retflags.update(sw.pop("ephemeris_retflags"))
        bodies = sw["bodies"]
        points = {"ASC": sw["ascendant"]}
        for name in ("SUN", "MOON", "MARS", "MERCURY", "JUPITER", "VENUS", "SATURN"):
            points[name] = bodies[name]["longitude"]
        points["RAHU"] = bodies["RAHU_MEAN"]["longitude"]
        points["KETU"] = bodies["KETU_MEAN"]["longitude"]

        nakshatras = {}
        for key, value in points.items():
            nak, pada, _ = drik.nakshatra_pada(value)
            nakshatras[key] = {"nakshatra": nak - 1, "pada": pada}

        jh_rasi = [["L", (int(points["ASC"] // 30), points["ASC"] % 30)]]
        for jh_id in range(9):
            lon_ = points[JH_ID_TO_NAME[jh_id]]
            jh_rasi.append([jh_id, (int(lon_ // 30), lon_ % 30)])
        jh_combust = [JH_ID_TO_NAME[p] for p in charts.planets_in_combustion(jh_rasi)]

        try:
            moon_jh, dasha_levels = pyjhora_dasha(vimsottari, drik, const, jd, lat, lon)
            dasha = _trim_dasha(dasha_levels, jd)
            dasha["method"] = "pyjhora get_dhasa_bhukthi"
        except swe.Error:
            moon_jh = drik.sidereal_longitude(jd, const._MOON)
            dasha = component_dasha(vimsottari, drik, moon_jh, jd)
            dasha["method"] = "pyjhora components (end-to-end ascendant failed)"
        dasha["moon_longitude_pyjhora"] = moon_jh

        out_charts.append(
            {
                "id": cid,
                "label": label,
                "place": place,
                "latitude": lat,
                "longitude": lon,
                "timezone": tz,
                "utc": dt_utc.isoformat(),
                "jd_ut": jd,
                "ayanamsa": sw["ayanamsa"],
                "ascendant": sw["ascendant"],
                "mc": sw["mc"],
                "cusps_whole_sign": sw["cusps_whole_sign"],
                "cusps_placidus": sw.get("cusps_placidus"),
                "bodies": bodies,
                "nakshatra_pada": nakshatras,
                "vargas": pyjhora_vargas(charts, points),
                "combust": {
                    "expected": expected_combustion(bodies),
                    "pyjhora": jh_combust,
                },
                "dasha": dasha,
            }
        )

    eph = []
    if retflags & {swe.FLG_SWIEPH}:
        eph.append("swieph")
    if retflags & {swe.FLG_MOSEPH}:
        eph.append("moshier")
    fixture = {
        "provenance": {
            "generated_on": date.today().isoformat(),
            "generator": "tests/fixtures/generate_golden_charts.py",
            "oracles": {
                "positions_ascendant_ayanamsa": {
                    "name": "pyswisseph",
                    "version": importlib.metadata.version("pyswisseph"),
                    "swiss_ephemeris_version": swe.version,
                    "flags": "FLG_SWIEPH|FLG_SPEED|FLG_SIDEREAL",
                    "houses": "houses_ex(..., FLG_SIDEREAL)",
                    "ephemeris_used": eph,
                    "ephemeris_files": "PyJHora src/jhora/data/ephe (*.se1)",
                },
                "dasha_vargas_nakshatra_combustion": {
                    "name": "PyJHora",
                    "version": package_info.version,
                    "git_commit": _git_head(PYJHORA_SRC),
                    "dasha_year": "MEAN_SIDEREAL_YEAR with sidereal_year "
                    f"overridden to {DASHA_YEAR_DAYS} days",
                    "varga_methods": "D2 method 2 (traditional Parashara hora); "
                    "all others method 1 (traditional Parashara)",
                    "planet_flags": "FLG_SWIEPH|FLG_SPEED|FLG_SIDEREAL "
                    "(apparent, overriding PyJHora's TRUEPOS)",
                },
            },
            "ayanamsa": "Lahiri (SIDM_LAHIRI)",
            "node_model": "mean (RAHU/KETU); true nodes recorded as RAHU_TRUE",
            "ketu": "Rahu + 180 deg",
            "time_scale": "jd_ut is UT1 Julian day (swe.julday on UTC)",
            "combustion_expected": "Surya Siddhanta orbs: Moon 12, Mars 17, "
            "Mercury 14 (12 retro), Jupiter 11, "
            "Venus 10 (8 retro), Saturn 15",
            "tolerances": {
                "longitude_arcmin": 1.0,
                "ascendant_arcmin": 1.0,
                "dasha_days": 1.0,
                "varga_sign": "exact",
            },
        },
        "charts": out_charts,
        "dasha_random_moon": random_moon_dashas(vimsottari, drik),
        "varga_mid_points": varga_mid_points(charts),
    }
    OUT_PATH.write_text(_dump(fixture))
    print(f"wrote {OUT_PATH} with {len(out_charts)} charts")


if __name__ == "__main__":
    main()
