"""src/celestial/dasha_engine.py.

Vimshottari Dasha Fractional Engine
===================================
Recursive time-series calculator for the major and sub-periods
of the Vimshottari Dasha system (120-year cycle).

See: SYMBOLOGY.md §II.I
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List


@dataclass
class DashaPeriod:
    """A specific period in the dasha hierarchy."""

    level: int  # 1=Mahadasha, 2=Antardasha, etc.
    planet: str
    start_date: datetime
    end_date: datetime
    sub_periods: List[DashaPeriod] = None


# Vimshottari Cycle: {Planet: Duration_in_Years}
# Order: Ketu -> Venus -> Sun -> Moon -> Mars -> Rahu -> Jupiter -> Saturn -> Mercury
DASHA_CYCLE: List[tuple[str, int]] = [
    ("Ketu", 7),
    ("Venus", 20),
    ("Sun", 6),
    ("Moon", 10),
    ("Mars", 7),
    ("Rahu", 18),
    ("Jupiter", 16),
    ("Saturn", 19),
    ("Mercury", 17),
]

PLANET_ORDER = [p[0] for p in DASHA_CYCLE]
DURATIONS = {p[0]: p[1] for p in DASHA_CYCLE}


def get_nakshatra_info(moon_lon: float) -> tuple[int, float]:
    """Return Nakshatra index (0-26) and the elapsed percentage."""
    nakshatra_width = 360.0 / 27.0
    index = int(moon_lon // nakshatra_width)
    elapsed = (moon_lon % nakshatra_width) / nakshatra_width
    return index, elapsed


def get_starting_planet_index(nakshatra_index: int) -> int:
    """Map Nakshatra (0-26) to starting planet in DASHA_CYCLE."""
    # Ashwini (0), Magha (9), Mula (18) are ruled by Ketu (0)
    return nakshatra_index % 9


def calculate_vimshottari(
    birth_date: datetime, moon_lon: float, levels: int = 2
) -> List[DashaPeriod]:
    """
    Generate the Vimshottari Dasha timeline.

    Parameters
    ----------
    birth_date : datetime
        UTC birth time.
    moon_lon : float
        Moon's sidereal (Lahiri) longitude.
    levels : int
        Hierarchy depth (1=MD, 2=MD+AD, 3=MD+AD+PD).
    """
    nak_idx, elapsed = get_nakshatra_info(moon_lon)
    start_planet_idx = get_starting_planet_index(nak_idx)

    current_start = birth_date
    timeline = []

    # Calculate the remaining portion of the first Mahadasha
    _, full_duration = DASHA_CYCLE[start_planet_idx]
    remaining_years = full_duration * (1.0 - elapsed)

    # Start the cycle
    planet_ptr = start_planet_idx

    # We generate a 120-year cycle (roughly)
    total_years_generated = 0

    while total_years_generated < 120:
        planet, years = DASHA_CYCLE[planet_ptr]

        # Adjust for first planet
        actual_years = remaining_years if total_years_generated == 0 else years

        # Approximate datetime math (365.2425 days/year)
        duration_days = actual_years * 365.2425
        end_date = current_start + timedelta(days=duration_days)

        md_period = DashaPeriod(
            level=1,
            planet=planet,
            start_date=current_start,
            end_date=end_date,
            sub_periods=[],
        )

        if levels >= 2:
            md_period.sub_periods = _calculate_sub_periods(
                md_period, levels, planet_ptr
            )

        timeline.append(md_period)

        current_start = end_date
        total_years_generated += actual_years
        planet_ptr = (planet_ptr + 1) % 9

    return timeline


def _calculate_sub_periods(
    parent: DashaPeriod, max_level: int, md_start_idx: int
) -> List[DashaPeriod]:
    """Recursively calculate Antardashas, Pratyantardashas, etc."""
    level = parent.level + 1
    if level > max_level:
        return []

    child_start = parent.start_date
    md_planet = parent.planet
    md_years = DURATIONS[md_planet]

    children = []

    # Sub-periods always start from the Mahadasha lord themselves
    # and follow the same cyclic order.
    current_ptr = md_start_idx

    for _ in range(9):
        sub_planet, sub_years = DASHA_CYCLE[current_ptr]

        # AD duration is (MD_years * AD_years) / 120.
        ad_duration_days = (md_years * sub_years / 120.0) * 365.2425
        child_end = child_start + timedelta(days=ad_duration_days)

        # Clip to parent end date
        if child_start >= parent.end_date:
            break

        actual_end = min(child_end, parent.end_date)

        child_period = DashaPeriod(
            level=level,
            planet=sub_planet,
            start_date=child_start,
            end_date=actual_end,
            sub_periods=[],
        )

        if level < max_level:
            child_period.sub_periods = _calculate_sub_periods(
                child_period, max_level, current_ptr
            )

        children.append(child_period)
        child_start = actual_end
        current_ptr = (current_ptr + 1) % 9

    return children


if __name__ == "__main__":
    # Test birth: 2000-01-01, Moon at 0 deg Aries (Ashwini, Ketu starts)
    birth = datetime(2000, 1, 1)
    dasha = calculate_vimshottari(birth, 0.0, levels=2)

    for md in dasha[:3]:
        print(f"MD: {md.planet} | {md.start_date.date()} to {md.end_date.date()}")
        for ad in md.sub_periods:
            print(f"  AD: {ad.planet} | {ad.start_date.date()}")
