"""Vimshottari dasha computations (core engine)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional, Tuple, Dict
from enum import Enum

from ..astrology.chart import get_nakshatra

VIMSHOTTARI_SEQUENCE = [
    "Ketu",
    "Venus",
    "Sun",
    "Moon",
    "Mars",
    "Rahu",
    "Jupiter",
    "Saturn",
    "Mercury",
]

VIMSHOTTARI_YEARS = {
    "Ketu": 7,
    "Venus": 20,
    "Sun": 6,
    "Moon": 10,
    "Mars": 7,
    "Rahu": 18,
    "Jupiter": 16,
    "Saturn": 19,
    "Mercury": 17,
}

SIDEREAL_YEAR_DAYS = 365.2425


@dataclass(frozen=True)
class DashaPeriod:
    lord: str
    start: datetime
    end: datetime
    years: float
    balance_years: float


def get_vimshottari_start_lord(moon_longitude: float) -> str:
    """Return the starting mahadasha lord based on Moon's nakshatra."""
    nak = get_nakshatra(moon_longitude)
    return _normalize_lord(nak["lord"])


def _normalize_lord(lord) -> str:
    if isinstance(lord, Enum):
        return lord.name.title()
    if isinstance(lord, str):
        return lord
    return str(lord)


def _balance_years_in_start_dasha(moon_longitude: float) -> float:
    """Compute remaining years of the starting mahadasha from Moon longitude."""
    nak = get_nakshatra(moon_longitude)
    lord = _normalize_lord(nak["lord"])
    nak_span = 360 / 27
    remaining = nak_span - nak["degrees_in_nakshatra"]
    fraction = remaining / nak_span
    return VIMSHOTTARI_YEARS[lord] * fraction


def compute_vimshottari_periods(
    birth_datetime: datetime,
    moon_longitude: float,
    total_years: float = 120,
    start_lord: Optional[str] = None,
) -> List[DashaPeriod]:
    """Compute Vimshottari mahadasha periods for the given span.

    Args:
        birth_datetime: Birth datetime (start reference).
        moon_longitude: Moon sidereal longitude at birth.
        total_years: Total years to compute (default 120).
        start_lord: Optional override for the starting dasha lord.

    Returns:
        List of DashaPeriod entries with start/end timestamps.
    """
    if start_lord is None:
        start_lord = get_vimshottari_start_lord(moon_longitude)

    if start_lord not in VIMSHOTTARI_SEQUENCE:
        raise ValueError(f"Unknown Vimshottari lord: {start_lord}")

    balance_years = _balance_years_in_start_dasha(moon_longitude)
    periods: List[DashaPeriod] = []

    idx = VIMSHOTTARI_SEQUENCE.index(start_lord)
    current = birth_datetime
    remaining = total_years

    first_years = min(balance_years, remaining)
    end = current + timedelta(days=first_years * SIDEREAL_YEAR_DAYS)
    periods.append(
        DashaPeriod(
            lord=start_lord,
            start=current,
            end=end,
            years=first_years,
            balance_years=balance_years,
        )
    )
    current = end
    remaining -= first_years

    step = 1
    while remaining > 0:
        lord = VIMSHOTTARI_SEQUENCE[(idx + step) % len(VIMSHOTTARI_SEQUENCE)]
        years = min(VIMSHOTTARI_YEARS[lord], remaining)
        end = current + timedelta(days=years * SIDEREAL_YEAR_DAYS)
        periods.append(
            DashaPeriod(
                lord=lord,
                start=current,
                end=end,
                years=years,
                balance_years=years,
            )
        )
        current = end
        remaining -= years
        step += 1

    return periods


def get_vimshottari_lord_at(
    target_datetime: datetime,
    birth_datetime: datetime,
    moon_longitude: float,
) -> str:
    """Return the active Vimshottari mahadasha lord for a target datetime."""
    periods = compute_vimshottari_periods(
        birth_datetime=birth_datetime,
        moon_longitude=moon_longitude,
        total_years=120,
    )
    for period in periods:
        if period.start <= target_datetime < period.end:
            return period.lord
    return periods[-1].lord


def compute_vimshottari_nested_periods(
    birth_datetime: datetime,
    moon_longitude: float,
    depth: int = 2,
    total_years: float = 120,
) -> List[Dict]:
    """Compute nested Vimshottari periods up to a given depth.

    depth=1 -> mahadasha only
    depth=2 -> mahadasha + antardasha
    depth=3 -> mahadasha + antardasha + pratyantar
    """
    if depth < 1:
        raise ValueError("depth must be >= 1")

    maha_periods = compute_vimshottari_periods(
        birth_datetime=birth_datetime,
        moon_longitude=moon_longitude,
        total_years=total_years,
    )

    results: List[Dict] = []

    def expand_period(start: datetime, years: float, start_index: int, level: int, lords_prefix: Tuple[str, ...]):
        if level == 0:
            results.append(
                {
                    "lords": lords_prefix,
                    "start": start,
                    "end": start + timedelta(days=years * SIDEREAL_YEAR_DAYS),
                    "years": years,
                    "level": len(lords_prefix),
                }
            )
            return

        current = start
        for offset in range(len(VIMSHOTTARI_SEQUENCE)):
            sub_lord = VIMSHOTTARI_SEQUENCE[(start_index + offset) % len(VIMSHOTTARI_SEQUENCE)]
            sub_years = years * (VIMSHOTTARI_YEARS[sub_lord] / 120.0)
            sub_start = current
            sub_end = sub_start + timedelta(days=sub_years * SIDEREAL_YEAR_DAYS)

            if level == 1:
                results.append(
                    {
                        "lords": lords_prefix + (sub_lord,),
                        "start": sub_start,
                        "end": sub_end,
                        "years": sub_years,
                        "level": len(lords_prefix) + 1,
                    }
                )
            else:
                expand_period(
                    sub_start,
                    sub_years,
                    VIMSHOTTARI_SEQUENCE.index(sub_lord),
                    level - 1,
                    lords_prefix + (sub_lord,),
                )

            current = sub_end

    for period in maha_periods:
        if depth == 1:
            results.append(
                {
                    "lords": (period.lord,),
                    "start": period.start,
                    "end": period.end,
                    "years": period.years,
                    "level": 1,
                }
            )
        else:
            expand_period(
                period.start,
                period.years,
                VIMSHOTTARI_SEQUENCE.index(period.lord),
                depth - 1,
                (period.lord,),
            )

    return results


def get_vimshottari_chain_at(
    target_datetime: datetime,
    nested_periods: List[Dict],
) -> Tuple[str, ...]:
    """Return the lords tuple for a target datetime from nested periods."""
    for period in nested_periods:
        if period["start"] <= target_datetime < period["end"]:
            return period["lords"]
    return nested_periods[-1]["lords"]
