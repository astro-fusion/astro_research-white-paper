"""Tests for Vimshottari dasha core engine."""
from datetime import datetime, timedelta

from vedic_astrology_core.dasha.vimshottari import (
    VIMSHOTTARI_SEQUENCE,
    VIMSHOTTARI_YEARS,
    compute_vimshottari_periods,
    get_vimshottari_lord_at,
    get_vimshottari_start_lord,
)


def test_start_lord_from_moon_longitude():
    # 0° falls in Ashwini, which is ruled by Ketu
    assert get_vimshottari_start_lord(0.0) == "Ketu"


def test_periods_sum_to_total_years():
    birth = datetime(2000, 1, 1)
    moon_long = 0.0  # Ashwini (Ketu)
    periods = compute_vimshottari_periods(birth, moon_long, total_years=120)
    total = sum(p.years for p in periods)
    assert abs(total - 120) < 1e-6


def test_first_period_balance_years():
    birth = datetime(2000, 1, 1)
    moon_long = 0.0  # start of nakshatra
    periods = compute_vimshottari_periods(birth, moon_long, total_years=120)
    first = periods[0]
    assert first.lord == "Ketu"
    assert abs(first.years - VIMSHOTTARI_YEARS["Ketu"]) < 1e-6


def test_lord_at_target_date():
    birth = datetime(2000, 1, 1)
    moon_long = 0.0
    target = birth + timedelta(days=365.2425 * 8)  # year 8 should be Venus
    lord = get_vimshottari_lord_at(target, birth, moon_long)
    assert lord == VIMSHOTTARI_SEQUENCE[1]  # Venus
