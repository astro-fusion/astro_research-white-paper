"""Sky state arrays and candidate evaluation for the combination atlas.

:func:`sky_state` turns an hourly ephemeris frame into the integer arrays the
grammar's clauses read (sign, nakshatra lord, lagna sign, dasha lords, and
longitudes for conjunctions). :func:`clause_mask` and :func:`candidate_mask`
evaluate clauses on those arrays. :func:`shift_family` runs the
circular-shift rate test for every candidate with one shared set of offsets,
returning per-candidate p-values and the single-step Romano-Wolf (max-|z|)
adjusted p-values.
"""

from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from vedic_astrology_core.stats.nulls import circular_shift_offsets
from vedic_astrology_core.stats.permutation import empirical_p_value
from vedic_astrology_core.stats.rates import indicator_rate_ratio

PLANETS = (
    "SUN",
    "MOON",
    "MARS",
    "MERCURY",
    "VENUS",
    "JUPITER",
    "SATURN",
    "RAHU",
    "KETU",
)
VIMSHOTTARI = (
    "KETU",
    "VENUS",
    "SUN",
    "MOON",
    "MARS",
    "RAHU",
    "JUPITER",
    "SATURN",
    "MERCURY",
)


def lagna_signs(jds, lat: float, lon: float) -> np.ndarray:
    """Sidereal (Lahiri) ascendant sign index 0-11 at each Julian day."""
    import swisseph as swe

    swe.set_sid_mode(swe.SIDM_LAHIRI)
    out = np.empty(len(jds), dtype=np.int8)
    for i, jd in enumerate(np.asarray(jds, dtype=float)):
        asc = swe.houses_ex(float(jd), lat, lon, b"W", swe.FLG_SIDEREAL)[1][0]
        out[i] = int((asc % 360.0) // 30.0)
    return out


def dasha_lords(grid: pd.DatetimeIndex, chart: Dict, engine) -> Dict[int, np.ndarray]:
    """Vimshottari lord index (into :data:`PLANETS`) at levels 1 and 2."""
    from vedic_astrology_core.config.constants import Planet
    from vedic_astrology_core.dasha.vimshottari import (
        compute_vimshottari_nested_periods,
    )

    birth = pd.Timestamp(chart["datetime"]).to_pydatetime()
    jd = engine.datetime_to_julian_day(birth)
    moon = engine.get_planet_position(jd, Planet.MOON)["longitude"]
    periods = compute_vimshottari_nested_periods(birth, moon, depth=2, total_years=120)
    starts = pd.DatetimeIndex([pd.Timestamp(p["start"]) for p in periods]).tz_convert(
        "UTC"
    )
    pos = np.clip(starts.searchsorted(grid, side="right") - 1, 0, len(periods) - 1)
    out = {}
    for level in (1, 2):
        lords = np.array(
            [PLANETS.index(p["lords"][level - 1].upper()) for p in periods],
            dtype=np.int8,
        )
        out[level] = lords[pos]
    return out


def sky_state(eph: pd.DataFrame, lagna: np.ndarray, dasha: Dict) -> Dict:
    """Integer and float arrays every clause reads."""
    lon = {p: eph[f"lon_{p}"].to_numpy() for p in PLANETS if p != "RAHU"}
    lon["RAHU"] = (lon["KETU"] + 180.0) % 360.0
    sign = {p: (lon[p] // 30.0).astype(np.int8) % 12 for p in PLANETS}
    nak = {p: (lon[p] // (360.0 / 27.0)).astype(np.int16) % 27 for p in PLANETS}
    return {
        "lon": lon,
        "sign": sign,
        "nak_lord": {p: (nak[p] % 9).astype(np.int8) for p in PLANETS},
        "lagna": np.asarray(lagna, dtype=np.int8),
        "dasha": dasha,
        "n": len(eph),
    }


def clause_mask(c: Dict, sky: Dict, grammar: Dict) -> np.ndarray:
    """Boolean series of one clause."""
    k = c["kind"]
    if k == "placement":
        s = sky["sign"][c["planet"]]
        if c["frame"] == "sign":
            return s == c["value"]
        if c["frame"] == "house_from_lagna":
            return (s - sky["lagna"]) % 12 == c["value"]
        if c["frame"] == "house_from_moon":
            return (s - sky["sign"]["MOON"]) % 12 == c["value"]
        return sky["nak_lord"][c["planet"]] == c["value"]
    if k == "aspect":
        houses = grammar["relations"]["aspect"]["houses"]
        aspected = houses.get(c["from"], houses["default"])
        h = (sky["sign"][c["to"]] - sky["sign"][c["from"]]) % 12 + 1
        return np.isin(h, aspected)
    if k == "conjunction":
        d = np.abs(sky["lon"][c["a"]] - sky["lon"][c["b"]]) % 360.0
        d = np.minimum(d, 360.0 - d)
        return d <= float(grammar["relations"]["conjunction"]["orb_deg"])
    if k == "dasha":
        return sky["dasha"][c["level"]] == PLANETS.index(c["planet"])
    raise KeyError(f"unknown clause kind {k}")


def candidate_mask(
    cand: Dict, sky: Dict, grammar: Dict, cache: Optional[Dict] = None
) -> np.ndarray:
    """Logical AND of a candidate's clauses (relation clauses cached)."""
    out = None
    for c in cand["clauses"]:
        key = None
        if cache is not None and c["kind"] in ("aspect", "conjunction", "dasha"):
            key = tuple(sorted(c.items()))
            m = cache.get(key)
            if m is None:
                m = cache[key] = clause_mask(c, sky, grammar)
        else:
            m = clause_mask(c, sky, grammar)
        out = m.copy() if out is None else (out & m)
    return out


def shift_family(
    masks,
    events: np.ndarray,
    n: int,
    min_shift: int,
    n_draws: int,
    rng: np.random.Generator,
    min_expected: float,
) -> pd.DataFrame:
    """Two-sided circular-shift tests with shared offsets, plus max-|z|.

    Args:
        masks: Iterable of ``(id, bool array of length n)``.
        events: Event grid indices in ``[0, n)``.
        n: Series length.
        min_shift, n_draws, rng: Null settings; offsets are drawn once.
        min_expected: Testable when at least this many events are expected
            inside and outside under the null.

    Returns:
        One row per candidate with exposure, RR, CI, p and ``p_rw`` (the
        single-step Romano-Wolf adjusted p, NaN when untestable).
    """
    ev = np.asarray(events, dtype=np.int64)
    n_ev = len(ev)
    offsets = circular_shift_offsets(n, min_shift, n_draws, rng)
    idx = (ev[None, :] - offsets[:, None]) % n
    max_abs_z = np.zeros(len(offsets))
    rows: List[Dict] = []
    zs: List[float] = []
    for cid, mask in masks:
        m = np.asarray(mask, dtype=bool)
        duty = float(m.mean())
        row = {
            "id": cid,
            "n_active_hours": int(m.sum()),
            "n_active_days": int(np.ceil(m.sum() / 24.0)),
            "time_fraction": duty,
            "n_events": n_ev,
            "expected_in": n_ev * duty,
        }
        if n_ev * duty < min_expected or n_ev * (1 - duty) < min_expected:
            row["testable"] = False
            rows.append(row)
            zs.append(np.nan)
            continue
        rr = indicator_rate_ratio(ev, m)
        counts = m[idx].sum(axis=1)
        mu, sd = counts.mean(), counts.std()
        z_obs = abs(rr.n_in - mu) / sd if sd > 0 else 0.0
        if sd > 0:
            np.maximum(max_abs_z, np.abs(counts - mu) / sd, out=max_abs_z)
        row.update(
            {
                "testable": True,
                "n_in": rr.n_in,
                "rate_ratio": rr.rate_ratio,
                "ci_low": rr.ci_low,
                "ci_high": rr.ci_high,
                "p_value": empirical_p_value(rr.n_in, counts, "two-sided"),
            }
        )
        rows.append(row)
        zs.append(z_obs)
    out = pd.DataFrame(rows)
    z = np.asarray(zs)
    out["p_rw"] = [
        (
            float((1 + np.sum(max_abs_z >= zi)) / (len(max_abs_z) + 1))
            if np.isfinite(zi)
            else np.nan
        )
        for zi in z
    ]
    return out
