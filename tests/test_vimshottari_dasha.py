"""Tests for the Vimshottari mahadasha engine (virtual-start algorithm).

Expected values come from PyJHora via ``tests/fixtures/golden_charts.json``.
"""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from vedic_astrology_core.dasha.vimshottari import (
    VIMSHOTTARI_SEQUENCE,
    VIMSHOTTARI_YEARS,
    DashaYear,
    compute_vimshottari_periods,
    get_vimshottari_lord_at,
    get_vimshottari_start_lord,
    virtual_start,
)
from vedic_astrology_core.utils.datetime_utils import NaiveDatetimeError

FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "golden_charts.json").read_text()
)
CASES = FIXTURE["dasha_random_moon"]
UTC = timezone.utc


def _jd_to_dt(jd):
    return datetime(1970, 1, 1, tzinfo=UTC) + timedelta(days=jd - 2440587.5)


@pytest.mark.parametrize("case", CASES, ids=[f"case{i}" for i in range(len(CASES))])
def test_mahadashas_match_pyjhora(case):
    """All nine mahadasha starts within 1 day of PyJHora, any Moon longitude."""
    birth = _jd_to_dt(case["birth_jd_ut"])
    periods = compute_vimshottari_periods(birth, case["moon_longitude"])
    for period, (lords, start_jd) in zip(periods, case["level1"]):
        assert period.lord == lords[0]
        assert abs((period.start - _jd_to_dt(start_jd)).total_seconds()) < 86400
    first = periods[0]
    assert first.start <= birth < first.end
    assert first.years == VIMSHOTTARI_YEARS[first.lord]
    assert first.balance_years == pytest.approx(
        (first.end - birth).total_seconds() / 86400 / 365.25
    )


def test_start_lord_from_moon_longitude():
    """Nakshatra lords: Ashwini Ketu, Bharani Venus, Revati Mercury."""
    assert get_vimshottari_start_lord(0.0) == "Ketu"
    assert get_vimshottari_start_lord(20.0) == "Venus"
    assert get_vimshottari_start_lord(359.0) == "Mercury"


def test_virtual_start_mid_bharani():
    """Moon halfway through Bharani: Venus MD started 10 years before birth."""
    birth = datetime(2000, 1, 1, tzinfo=UTC)
    moon = 360 / 27 * 1.5
    assert virtual_start(birth, moon) == birth - timedelta(days=10 * 365.25)
    first = compute_vimshottari_periods(birth, moon)[0]
    assert first.lord == "Venus"
    assert first.balance_years == pytest.approx(10.0)


def test_year_conventions():
    """Year length is a named convention: 365.25 (default), 365.2425, 360."""
    birth = datetime(2000, 1, 1, tzinfo=UTC)
    for year, days in (
        (DashaYear.JULIAN, 365.25),
        (DashaYear.GREGORIAN, 365.2425),
        (DashaYear.SAVANA, 360.0),
    ):
        first = compute_vimshottari_periods(birth, 0.0, year=year)[0]
        assert first.end - first.start == timedelta(days=7 * days)


def test_periods_cover_total_years():
    """Mahadashas are contiguous and cover birth to birth + 120 years."""
    birth = datetime(1984, 8, 27, 5, tzinfo=UTC)
    periods = compute_vimshottari_periods(birth, 200.0, total_years=120)
    for a, b in zip(periods, periods[1:]):
        assert a.end == b.start
        assert VIMSHOTTARI_SEQUENCE.index(b.lord) == (
            VIMSHOTTARI_SEQUENCE.index(a.lord) + 1
        ) % 9
    assert periods[-1].end >= birth + timedelta(days=120 * 365.25)


def test_lord_at_target_date():
    """Moon at 0 deg: Ketu for 7 years, then Venus."""
    birth = datetime(2000, 1, 1, tzinfo=UTC)
    assert get_vimshottari_lord_at(birth + timedelta(days=365), birth, 0.0) == "Ketu"
    target = birth + timedelta(days=365.25 * 8)
    assert get_vimshottari_lord_at(target, birth, 0.0) == "Venus"


def test_naive_birth_datetime_rejected():
    """Naive datetimes raise instead of being read as UT."""
    with pytest.raises(NaiveDatetimeError):
        compute_vimshottari_periods(datetime(2000, 1, 1), 0.0)
