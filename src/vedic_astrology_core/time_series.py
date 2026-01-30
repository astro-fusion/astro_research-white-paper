"""
Time-series utilities for Vedic Astrology + Numerology comparisons.

This module provides small, deterministic helpers to compute values over a
custom date range with a fixed step size. It is designed to be reused by:
- notebooks / Quarto
- the FastAPI server (`api.py`)
- the Streamlit app (`app.py`)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple, Union

import pandas as pd

from .astrology import EphemerisEngine
from .config.constants import Planet
from .dignity import DignityScorer

DateLike = Union[str, date, datetime]


def _to_date(d: DateLike) -> date:
    if isinstance(d, datetime):
        return d.date()
    if isinstance(d, date) and not isinstance(d, datetime):
        return d
    if isinstance(d, str):
        return datetime.strptime(d, "%Y-%m-%d").date()
    raise TypeError(f"Unsupported date type: {type(d)}")


def iter_dates(
    start_date: DateLike, end_date: DateLike, step_days: int = 1, inclusive: bool = True
) -> Iterable[date]:
    """
    Iterate dates from start_date to end_date with a step in days.

    Args:
        start_date: YYYY-MM-DD, date, or datetime
        end_date: YYYY-MM-DD, date, or datetime
        step_days: positive integer step
        inclusive: include end_date if it lands exactly on a step
    """
    start = _to_date(start_date)
    end = _to_date(end_date)
    if step_days <= 0:
        raise ValueError("step_days must be > 0")
    if end < start:
        raise ValueError("end_date must be >= start_date")

    cur = start
    step = timedelta(days=step_days)

    while cur <= end:
        yield cur
        cur += step


def iter_datetime_range(
    start_dt: datetime, end_dt: datetime, step_hours: float = 24.0
) -> Iterable[datetime]:
    """
    Iterate datetimes with a step in hours.

    Args:
        start_dt: Start datetime
        end_dt: End datetime
        step_hours: Step size in hours (can be float, e.g. 0.5 for 30 mins)
    """
    if step_hours <= 0:
        raise ValueError("step_hours must be > 0")

    cur = start_dt
    step = timedelta(hours=step_hours)

    while cur <= end_dt:
        yield cur
        cur += step


@dataclass(frozen=True)
class TimeSeriesConfig:
    """
    Parameters affecting astrology strength calculation.

    Notes:
      - We evaluate dignity at local noon for the provided date. This mirrors the
        existing temporal data generator and avoids timezone complexity.
    """

    latitude: float = 28.6139
    longitude: float = 77.1025
    noon_hour: int = 12


def compute_astrology_strength_series(
    start_date: DateLike,
    end_date: DateLike,
    step_days: int = 1,
    step_hours: Optional[float] = None,  # New: support 2-hour intervals
    planets: Optional[Sequence[Planet]] = None,
    config: Optional[TimeSeriesConfig] = None,
) -> pd.DataFrame:
    """
    Compute dignity/strength score (0-100) per planet across a date range.

    Supports both daily mode (classic) and high-res mode (step_hours).
    """
    cfg = config or TimeSeriesConfig()
    # If step_hours is provided, we switch to high-res mode
    is_high_res = step_hours is not None

    # Imports inside to avoid circular deps if any
    from .dignity.global_scorer import GlobalShadbalaScorer

    # Initialize Engines
    ephemeris = EphemerisEngine()
    # Use Global Shadbala Scorer for research-grade strength (Chesta/Yuddha included)
    global_scorer = GlobalShadbalaScorer(ephemeris=ephemeris)

    rows: List[Dict[str, Any]] = []

    # Determine iteration strategy
    if is_high_res:
        # Convert dates to datetimes if needed
        s_dt = datetime.combine(_to_date(start_date), time(0, 0))
        e_dt = datetime.combine(_to_date(end_date), time(23, 59))
        iterator = iter_datetime_range(s_dt, e_dt, step_hours=step_hours)
    else:
        # Classic daily mode
        iterator = [
            datetime.combine(d, time(hour=cfg.noon_hour))
            for d in iter_dates(start_date, end_date, step_days=step_days)
        ]

    for dt in iterator:
        jd = ephemeris.datetime_to_julian_day(dt)

        # Use Global Scorer for better quality metrics
        scores = global_scorer.calculate_global_power(jd)

        # Use full ISO format for high-res, but YYYY-MM-DD for daily compatibility
        date_str = dt.isoformat() if is_high_res else dt.date().isoformat()
        row: Dict[str, Any] = {"date": date_str}

        # Filter for requested planets if needed
        if planets:
            for p in planets:
                # Map to Title Case if needed by GlobalScorer (Sun, Moon, etc)
                # Or just handle it case-insensitively
                display_name = p.name.capitalize()
                row[f"astrology_{p.name}"] = scores.get(
                    display_name, scores.get(p.name, 0.0)
                )
        else:
            # Add all
            for pname, score in scores.items():
                row[f"astrology_{pname.upper()}"] = score

        rows.append(row)

    return pd.DataFrame(rows)


def compute_numerology_series(
    start_date: DateLike,
    end_date: DateLike,
    step_days: int = 1,
    planets: Optional[Sequence[Planet]] = None,
) -> pd.DataFrame:
    """
    Compute numerology "strength" per day using Vedic Mulanka mapping.

    Convention used (matches existing temporal generator):
      - Exactly one planet is "active" per day (Mulanka planet) with strength 100
      - All other planets have strength 0

    Returns a DataFrame with columns:
      - date (YYYY-MM-DD string)
      - numerology_active_planet
      - numerology_mulanka_number
      - numerology_<PLANET> for each planet
    """
    # Local import to avoid hard dependency on numerology package in the core lib.
    # In this repo, `vedic_numerology` provides the numerology implementation.
    from vedic_numerology.numerology import calculate_mulanka

    planets_to_use: Sequence[Planet] = planets or [
        Planet.SUN,
        Planet.MOON,
        Planet.MARS,
        Planet.MERCURY,
        Planet.JUPITER,
        Planet.VENUS,
        Planet.SATURN,
        Planet.RAHU,
        Planet.KETU,
    ]

    rows: List[Dict[str, Any]] = []
    for d in iter_dates(start_date, end_date, step_days=step_days, inclusive=True):
        mulanka_num, mulanka_planet = calculate_mulanka(d)

        row: Dict[str, Any] = {
            "date": d.isoformat(),
            "numerology_active_planet": mulanka_planet.name,
            "numerology_mulanka_number": int(mulanka_num),
        }
        for planet in planets_to_use:
            row[f"numerology_{planet.name}"] = (
                100.0 if planet == mulanka_planet else 0.0
            )
        rows.append(row)

    return pd.DataFrame(rows)


def compute_combined_series(
    start_date: DateLike,
    end_date: DateLike,
    step_days: int = 1,
    planets: Optional[Sequence[Planet]] = None,
    config: Optional[TimeSeriesConfig] = None,
) -> pd.DataFrame:
    """
    Compute a combined numerology + astrology dataset over time.

    The resulting DataFrame matches what `vedic_astrology_core.visualization.temporal_comparison`
    expects (date + numerology_* + astrology_* columns).
    """
    num_df = compute_numerology_series(
        start_date=start_date, end_date=end_date, step_days=step_days, planets=planets
    )
    ast_df = compute_astrology_strength_series(
        start_date=start_date,
        end_date=end_date,
        step_days=step_days,
        planets=planets,
        config=config,
    )
    return num_df.merge(ast_df, on="date", how="inner")
