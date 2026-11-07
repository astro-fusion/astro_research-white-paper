"""src/celestial/retrograde_detector.py.

Retrograde Station Scanner and Progression Engine
===================================================
See: papers/astrology/04_temporal_inflection_retrogrades_progressions.md
     SYMBOLOGY.md §II.D
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class Station:
    """Celestial station record."""

    body_name: str
    jd_tt: float
    station_type: str  # "retrograde" | "direct"
    lambda_ecl: float  # ecliptic longitude at station point


def short_arc_diff(lambda_a: float, lambda_b: float) -> float:
    """Return signed short-arc difference λ_a − λ_b (−180 to +180)."""
    diff = lambda_a - lambda_b
    if diff > 180.0:
        diff -= 360.0
    elif diff < -180.0:
        diff += 360.0
    return diff


def scan_retrograde_stations(
    body_name: str,
    jd_start: float,
    jd_end: float,
    step_days: float = 1.0,
) -> list[Station]:
    """
    Scan for all station-retrograde and station-direct points.

    Uses centred finite differences to compute dλ/dt and detects
    sign changes (see papers/astrology/04 §1.3).

    Requires: pyswisseph
    """
    try:
        import swisseph as swe
    except ImportError as exc:
        raise ImportError("pyswisseph required: pip install pyswisseph") from exc

    from src.celestial.ephemeris_engine import BODY_IDS

    body_id = BODY_IDS[body_name]
    jd_range = np.arange(jd_start, jd_end, step_days)

    lons = np.array(
        [swe.calc_ut(float(jd), body_id, swe.FLG_SWIEPH)[0][0] for jd in jd_range]
    )
    velocities = np.gradient(lons, step_days)

    stations: list[Station] = []
    for i in range(1, len(velocities)):
        v_prev, v_curr = velocities[i - 1], velocities[i]
        if v_prev > 0 and v_curr <= 0:
            stations.append(
                Station(body_name, float(jd_range[i]), "retrograde", lons[i])
            )
            logger.info(
                "Station retrograde: %s at JD %.2f (λ=%.2f°)",
                body_name,
                jd_range[i],
                lons[i],
            )
        elif v_prev <= 0 and v_curr > 0:
            stations.append(Station(body_name, float(jd_range[i]), "direct", lons[i]))
            logger.info(
                "Station direct:     %s at JD %.2f (λ=%.2f°)",
                body_name,
                jd_range[i],
                lons[i],
            )

    return stations


def refine_station_jd(
    body_id: int,
    jd_bracket_low: float,
    jd_bracket_high: float,
    tolerance_days: float = 1e-6,
) -> float:
    """
    Bisection refinement for sub-minute station accuracy.

    See papers/astrology/04 §4.
    """
    import swisseph as swe

    def velocity_at(jd: float) -> float:
        delta = 0.05
        l_plus = swe.calc_ut(jd + delta, body_id, swe.FLG_SWIEPH)[0][0]
        l_minus = swe.calc_ut(jd - delta, body_id, swe.FLG_SWIEPH)[0][0]
        return short_arc_diff(l_plus, l_minus) / (2 * delta)

    lo, hi = jd_bracket_low, jd_bracket_high
    while (hi - lo) > tolerance_days:
        mid = (lo + hi) / 2
        if velocity_at(lo) * velocity_at(mid) < 0:
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2


def compute_secondary_progression(
    natal_jd: float,
    age_years: float,
) -> float:
    """
    Return the progressed Julian Day corresponding to `age_years` after birth.

    Formula: t_prog = t_natal + Δt (days = years of life)
    See papers/astrology/04 §2.
    """
    return natal_jd + age_years


def compute_solar_arc_direction(
    natal_jd: float,
    age_years: float,
) -> float:
    """
    Compute the Solar Arc (degrees) to apply to all natal positions.

    SA_σ = λ_☉(t_natal + age_years_as_days) − λ_☉(t_natal)
    """
    import swisseph as swe

    SUN_ID = 0
    jd_prog = natal_jd + age_years  # 1 day = 1 year
    lon_natal = swe.calc_ut(natal_jd, SUN_ID, swe.FLG_SWIEPH)[0][0]
    lon_prog = swe.calc_ut(jd_prog, SUN_ID, swe.FLG_SWIEPH)[0][0]
    return short_arc_diff(lon_prog, lon_natal)
