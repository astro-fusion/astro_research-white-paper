"""Astrological indicator series on a regular UTC time grid.

Positions come from :class:`vedic_astrology_core.astrology.ephemeris.EphemerisEngine`
(sidereal, Lahiri, mean node, ``FLG_SPEED``). Eclipse maxima come from the
Swiss Ephemeris global eclipse search. Every indicator is a boolean array
on the grid, defined only by the parameters in ``hypothesis.yaml``.
"""

from datetime import datetime
from typing import Dict, List, Sequence
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import swisseph as swe

from vedic_astrology_core.astrology.ephemeris import EphemerisEngine
from vedic_astrology_core.config.constants import Planet

UTC = ZoneInfo("UTC")
BODIES = ("SUN", "MOON", "MARS", "MERCURY", "VENUS", "JUPITER", "SATURN", "KETU")
NAKSHATRAS = (
    "Ashvini",
    "Bharani",
    "Krittika",
    "Rohini",
    "Mrigashira",
    "Ardra",
    "Punarvasu",
    "Pushya",
    "Ashlesha",
    "Magha",
    "Purva Phalguni",
    "Uttara Phalguni",
    "Hasta",
    "Chitra",
    "Swati",
    "Vishakha",
    "Anuradha",
    "Jyeshtha",
    "Mula",
    "Purva Ashadha",
    "Uttara Ashadha",
    "Shravana",
    "Dhanishtha",
    "Shatabhisha",
    "Purva Bhadrapada",
    "Uttara Bhadrapada",
    "Revati",
)


def time_grid(start: str, end: str, step_hours: int = 1) -> pd.DatetimeIndex:
    """Return the left edges of ``[start, end)`` in UTC steps of ``step_hours``."""
    s = pd.Timestamp(start)
    e = pd.Timestamp(end)
    s = s.tz_convert(UTC) if s.tzinfo else s.tz_localize(UTC)
    e = e.tz_convert(UTC) if e.tzinfo else e.tz_localize(UTC)
    return pd.date_range(s, e, freq=f"{int(step_hours)}h", inclusive="left")


def event_bins(times, grid: pd.DatetimeIndex) -> np.ndarray:
    """Return the grid index of each event time (the step that contains it)."""
    t = pd.to_datetime(pd.Series(times), utc=True, format="ISO8601")
    step = grid[1] - grid[0]
    idx = ((t - grid[0]) // step).to_numpy(dtype=np.int64)
    if (idx < 0).any() or (idx >= len(grid)).any():
        raise ValueError("event outside the time grid")
    return idx


def ephemeris_frame(grid: pd.DatetimeIndex, engine: EphemerisEngine) -> pd.DataFrame:
    """Return sidereal longitude and speed of every body at every grid step."""
    first = grid[0].to_pydatetime()
    jd0 = engine.datetime_to_julian_day(
        datetime(first.year, first.month, first.day, first.hour, tzinfo=UTC)
    )
    step_days = (grid[1] - grid[0]) / pd.Timedelta(days=1)
    jds = jd0 + step_days * np.arange(len(grid))
    lon = np.empty((len(grid), len(BODIES)))
    spd = np.empty((len(grid), len(BODIES)))
    keys = [Planet[b] for b in BODIES]
    for i, jd in enumerate(jds):
        pos = engine.get_all_planet_positions(float(jd))
        for k, key in enumerate(keys):
            rec = pos[key]
            lon[i, k] = rec["longitude"]
            spd[i, k] = rec["longitude_speed"]
    data = {"jd": jds}
    for k, b in enumerate(BODIES):
        data[f"lon_{b}"] = lon[:, k]
        data[f"speed_{b}"] = spd[:, k]
    return pd.DataFrame(data, index=grid)


def separation(a, b) -> np.ndarray:
    """Return the shortest angular distance in degrees."""
    d = np.abs(np.asarray(a) - np.asarray(b)) % 360.0
    return np.minimum(d, 360.0 - d)


def window_mask(n: int, centres: Sequence[int], half_width: int) -> np.ndarray:
    """Return a mask that is True within ``half_width`` steps of any centre."""
    diff = np.zeros(n + 1, dtype=np.int64)
    for c in centres:
        lo, hi = max(0, int(c) - half_width), min(n, int(c) + half_width + 1)
        if lo < hi:
            diff[lo] += 1
            diff[hi] -= 1
    return np.cumsum(diff[:-1]) > 0


def sign_change_bins(values) -> np.ndarray:
    """Return indices ``k`` where ``values[k]`` and ``values[k-1]`` differ in sign."""
    s = np.sign(np.asarray(values, dtype=float))
    return np.flatnonzero(s[1:] * s[:-1] < 0) + 1


def eclipse_jds(jd_start: float, jd_end: float) -> Dict[str, List[float]]:
    """Return the JD (UT) of maximum of solar and partial/total lunar eclipses."""
    out = {"solar": [], "lunar": []}
    jd = jd_start - 30.0
    while True:
        _, tret = swe.sol_eclipse_when_glob(jd, swe.FLG_SWIEPH, 0)
        if tret[0] > jd_end + 30.0:
            break
        out["solar"].append(float(tret[0]))
        jd = tret[0] + 1.0
    jd = jd_start - 30.0
    lunar_types = swe.ECL_TOTAL | swe.ECL_PARTIAL
    while True:
        _, tret = swe.lun_eclipse_when(jd, swe.FLG_SWIEPH, lunar_types)
        if tret[0] > jd_end + 30.0:
            break
        out["lunar"].append(float(tret[0]))
        jd = tret[0] + 1.0
    return out


def build_indicators(hyp: Dict, eph: pd.DataFrame) -> pd.DataFrame:
    """Return one boolean column per registered indicator."""
    n = len(eph)
    step_days = float(eph["jd"].iloc[1] - eph["jd"].iloc[0])
    per_day = int(round(1.0 / step_days))
    jd0 = float(eph["jd"].iloc[0])
    eclipses = eclipse_jds(jd0, float(eph["jd"].iloc[-1]))
    ecl_bins = [
        int(round((j - jd0) / step_days)) for j in eclipses["solar"] + eclipses["lunar"]
    ]
    nak = np.floor(eph["lon_MOON"].to_numpy() / (360.0 / 27.0)).astype(int) % 27
    out = {}
    for ind in hyp["indicators"]:
        iid = ind["id"]
        if iid == "mars_saturn_conj":
            col = separation(eph["lon_MARS"], eph["lon_SATURN"]) <= ind["orb_deg"]
        elif iid == "mars_ketu_conj":
            col = separation(eph["lon_MARS"], eph["lon_KETU"]) <= ind["orb_deg"]
        elif iid == "eclipse_window":
            col = window_mask(n, ecl_bins, ind["window_days"] * per_day)
        elif iid == "sun_ingress":
            sign = np.floor(eph["lon_SUN"].to_numpy() / 30.0)
            ingress = np.flatnonzero(np.diff(sign) != 0) + 1
            col = window_mask(n, ingress, ind["window_days"] * per_day)
        elif iid.startswith("station_"):
            stations = sign_change_bins(eph[f"speed_{ind['planet']}"])
            col = window_mask(n, stations, ind["window_days"] * per_day)
        elif iid.startswith("moon_mandala_"):
            members = [NAKSHATRAS.index(name) for name in ind["nakshatras"]]
            col = np.isin(nak, members)
        else:
            raise KeyError(f"no definition for indicator {iid!r}")
        out[iid] = np.asarray(col, dtype=bool)
    frame = pd.DataFrame(out, index=eph.index)
    frame.attrs["n_solar_eclipses"] = len(eclipses["solar"])
    frame.attrs["n_lunar_eclipses"] = len(eclipses["lunar"])
    return frame
