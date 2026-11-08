"""Vimshottari dasha (BPHS Ch. 46), virtual-start algorithm.

Algorithm
---------
1. The Moon's nakshatra gives the first mahadasha (MD) lord; the fraction of
   the nakshatra already traversed is the elapsed fraction of that MD.
2. The first MD therefore started *before* birth, at
   ``birth - elapsed_fraction * MD_years`` (the "virtual start").
3. The full tree is expanded from the virtual start. At every level a child's
   length is ``parent_length * child_lord_years / 120`` and the children
   start with the parent's own lord.
4. Periods that end on or before birth are dropped. The period running at
   birth keeps its true (pre-birth) start.

An earlier version scaled the nine antardashas of the first MD into its
*balance*; that is only correct when the Moon is at 0 deg of a nakshatra.

Year length
-----------
The length of a dasha year is a convention, not a fact. It is a named
parameter, :class:`DashaYear`, defaulting to the Julian year of 365.25 days.
The Gregorian mean year (365.2425 d) and the 360-day savana year are also
available. (The old constant ``SIDEREAL_YEAR_DAYS = 365.2425`` was the
Gregorian year mislabelled as sidereal; the sidereal year is 365.2564 d.)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Tuple, TypedDict, Union, cast

from ..astrology.chart import get_nakshatra
from ..utils.datetime_utils import require_aware

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

VIMSHOTTARI_TOTAL_YEARS = 120

JULIAN_YEAR_DAYS = 365.25
GREGORIAN_YEAR_DAYS = 365.2425
SAVANA_YEAR_DAYS = 360.0


class DashaYear(Enum):
    """Named conventions for the length of one dasha year, in days."""

    JULIAN = JULIAN_YEAR_DAYS
    GREGORIAN = GREGORIAN_YEAR_DAYS
    SAVANA = SAVANA_YEAR_DAYS


DEFAULT_DASHA_YEAR = DashaYear.JULIAN
YearLike = Union[DashaYear, float]


def year_length_days(year: YearLike = DEFAULT_DASHA_YEAR) -> float:
    """Return the number of days in a dasha year for a convention or float."""
    if isinstance(year, DashaYear):
        return float(year.value)
    value = float(year)
    if value <= 0:
        raise ValueError("year length must be positive")
    return value


@dataclass(frozen=True)
class DashaPeriod:
    """One mahadasha.

    Attributes:
        lord: Dasha lord name ("Ketu", "Venus", ...).
        start: True start (the first period starts before birth).
        end: End of the period.
        years: Full length of the period in dasha years.
        balance_years: Years of the period remaining after birth.
    """

    lord: str
    start: datetime
    end: datetime
    years: float
    balance_years: float


class VimshottariPeriodDict(TypedDict):
    """One node of the nested dasha tree (leaf at the requested depth)."""

    lords: Tuple[str, ...]
    start: datetime
    end: datetime
    years: float
    level: int


def _normalize_lord(lord: object) -> str:
    if isinstance(lord, Enum):
        return lord.name.title()
    return str(lord)


def get_vimshottari_start_lord(moon_longitude: float) -> str:
    """Return the first mahadasha lord from the Moon's nakshatra."""
    nak = cast(Dict[str, object], get_nakshatra(moon_longitude))
    return _normalize_lord(nak["lord"])


def elapsed_fraction(moon_longitude: float) -> float:
    """Fraction (0-1) of the Moon's nakshatra already traversed at birth."""
    nak = cast(Dict[str, object], get_nakshatra(moon_longitude))
    return float(cast(float, nak["degrees_in_nakshatra"])) / (360.0 / 27.0)


def _balance_years_in_start_dasha(moon_longitude: float) -> float:
    """Years of the first mahadasha remaining at birth."""
    lord = get_vimshottari_start_lord(moon_longitude)
    return VIMSHOTTARI_YEARS[lord] * (1.0 - elapsed_fraction(moon_longitude))


def virtual_start(
    birth_datetime: datetime,
    moon_longitude: float,
    year: YearLike = DEFAULT_DASHA_YEAR,
) -> datetime:
    """Start of the first mahadasha: birth minus the elapsed part of it."""
    require_aware(birth_datetime, "birth_datetime")
    lord = get_vimshottari_start_lord(moon_longitude)
    elapsed_years = elapsed_fraction(moon_longitude) * VIMSHOTTARI_YEARS[lord]
    return birth_datetime - timedelta(days=elapsed_years * year_length_days(year))


def _children(
    lord: str, start: datetime, years: float, days_per_year: float
) -> List[Tuple[str, datetime, datetime, float]]:
    """Nine sub-periods of a period, starting with its own lord."""
    out = []
    idx = VIMSHOTTARI_SEQUENCE.index(lord)
    cursor = start
    for offset in range(len(VIMSHOTTARI_SEQUENCE)):
        sub = VIMSHOTTARI_SEQUENCE[(idx + offset) % len(VIMSHOTTARI_SEQUENCE)]
        sub_years = years * VIMSHOTTARI_YEARS[sub] / VIMSHOTTARI_TOTAL_YEARS
        end = cursor + timedelta(days=sub_years * days_per_year)
        out.append((sub, cursor, end, sub_years))
        cursor = end
    return out


def _mahadashas(
    birth_datetime: datetime,
    moon_longitude: float,
    total_years: float,
    start_lord: Optional[str],
    year: YearLike,
) -> List[Tuple[str, datetime, datetime, float]]:
    """Mahadashas from the virtual start that overlap [birth, birth+total]."""
    require_aware(birth_datetime, "birth_datetime")
    days_per_year = year_length_days(year)
    if start_lord is None:
        start_lord = get_vimshottari_start_lord(moon_longitude)
    if start_lord not in VIMSHOTTARI_SEQUENCE:
        raise ValueError(f"Unknown Vimshottari lord: {start_lord}")
    elapsed_years = elapsed_fraction(moon_longitude) * VIMSHOTTARI_YEARS[start_lord]
    cursor = birth_datetime - timedelta(days=elapsed_years * days_per_year)
    horizon = birth_datetime + timedelta(days=total_years * days_per_year)
    out = []
    idx = VIMSHOTTARI_SEQUENCE.index(start_lord)
    while cursor < horizon:
        lord = VIMSHOTTARI_SEQUENCE[idx % len(VIMSHOTTARI_SEQUENCE)]
        years = float(VIMSHOTTARI_YEARS[lord])
        end = cursor + timedelta(days=years * days_per_year)
        out.append((lord, cursor, end, years))
        cursor = end
        idx += 1
    return out


def compute_vimshottari_periods(
    birth_datetime: datetime,
    moon_longitude: float,
    total_years: float = 120,
    start_lord: Optional[str] = None,
    year: YearLike = DEFAULT_DASHA_YEAR,
) -> List[DashaPeriod]:
    """Compute the mahadashas running from birth to ``birth + total_years``.

    Args:
        birth_datetime: Timezone-aware birth instant.
        moon_longitude: Sidereal longitude of the Moon at birth.
        total_years: Span after birth to cover (default 120).
        start_lord: Optional override for the first mahadasha lord.
        year: Dasha-year convention (default :attr:`DashaYear.JULIAN`).

    Returns:
        DashaPeriod list. The first period starts before birth (virtual
        start); ``balance_years`` is the part of it after birth.
    """
    days_per_year = year_length_days(year)
    periods = []
    for lord, start, end, years in _mahadashas(
        birth_datetime, moon_longitude, total_years, start_lord, year
    ):
        after_birth = (end - max(start, birth_datetime)).total_seconds() / 86400.0
        periods.append(
            DashaPeriod(
                lord=lord,
                start=start,
                end=end,
                years=years,
                balance_years=after_birth / days_per_year,
            )
        )
    return periods


def get_vimshottari_lord_at(
    target_datetime: datetime,
    birth_datetime: datetime,
    moon_longitude: float,
    year: YearLike = DEFAULT_DASHA_YEAR,
) -> str:
    """Return the mahadasha lord running at ``target_datetime``."""
    require_aware(target_datetime, "target_datetime")
    periods = compute_vimshottari_periods(
        birth_datetime, moon_longitude, total_years=120, year=year
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
    year: YearLike = DEFAULT_DASHA_YEAR,
) -> List[VimshottariPeriodDict]:
    """Compute nested Vimshottari periods down to ``depth``.

    depth=1 -> mahadasha, 2 -> antardasha, 3 -> pratyantardasha, and so on.
    Leaves that end on or before birth, or start after
    ``birth + total_years``, are dropped.
    """
    if depth < 1:
        raise ValueError("depth must be >= 1")
    days_per_year = year_length_days(year)
    horizon = birth_datetime + timedelta(days=total_years * days_per_year)
    results: List[VimshottariPeriodDict] = []

    def expand(
        lords: Tuple[str, ...], start: datetime, end: datetime, years: float
    ) -> None:
        if end <= birth_datetime or start >= horizon:
            return
        if len(lords) == depth:
            results.append(
                {
                    "lords": lords,
                    "start": start,
                    "end": end,
                    "years": years,
                    "level": depth,
                }
            )
            return
        for sub, s, e, y in _children(lords[-1], start, years, days_per_year):
            expand(lords + (sub,), s, e, y)

    for lord, start, end, years in _mahadashas(
        birth_datetime, moon_longitude, total_years, None, year
    ):
        expand((lord,), start, end, years)
    return results


def get_vimshottari_chain_at(
    target_datetime: datetime,
    nested_periods: List[VimshottariPeriodDict],
) -> Tuple[str, ...]:
    """Return the lords tuple running at ``target_datetime``."""
    require_aware(target_datetime, "target_datetime")
    for period in nested_periods:
        if period["start"] <= target_datetime < period["end"]:
            return period["lords"]
    return nested_periods[-1]["lords"]
