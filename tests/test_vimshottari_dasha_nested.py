"""Tests for nested Vimshottari periods (antardasha, pratyantardasha)."""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from vedic_astrology_core.dasha.vimshottari import (
    VIMSHOTTARI_YEARS,
    compute_vimshottari_nested_periods,
    get_vimshottari_chain_at,
)

FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "golden_charts.json").read_text()
)
UTC = timezone.utc


def _jd_to_dt(jd):
    return datetime(1970, 1, 1, tzinfo=UTC) + timedelta(days=jd - 2440587.5)


def test_nested_durations_scale_with_parent():
    """Child length = parent length x child lord years / 120 at every level."""
    birth = datetime(2000, 1, 1, tzinfo=UTC)
    moon = 123.456
    level2 = compute_vimshottari_nested_periods(birth, moon, depth=2)
    level3 = compute_vimshottari_nested_periods(birth, moon, depth=3)
    ad = {}
    for p in level2:
        ad.setdefault(p["lords"], []).append(p)
    for p in level3:
        md, sub, sub2 = p["lords"]
        expected = VIMSHOTTARI_YEARS[md] * VIMSHOTTARI_YEARS[sub] / 120
        expected *= VIMSHOTTARI_YEARS[sub2] / 120
        assert p["years"] == pytest.approx(expected)
        assert any(a["start"] <= p["start"] < a["end"] for a in ad[(md, sub)])


def test_running_chain_at_birth_matches_pyjhora():
    """The MD/AD/PD running at birth agrees with PyJHora for every chart."""
    for chart in FIXTURE["charts"]:
        birth = datetime.fromisoformat(chart["utc"])
        moon = chart["bodies"]["MOON"]["longitude"]
        nested = compute_vimshottari_nested_periods(birth, moon, depth=3)
        rows = chart["dasha"]["level3_birth_md"]
        expected = None
        for lords, start_jd in rows:
            if _jd_to_dt(start_jd) <= birth:
                expected = tuple(lords)
        assert get_vimshottari_chain_at(birth, nested) == expected, chart["id"]
        assert nested[0]["lords"] == expected
        assert nested[0]["start"] <= birth < nested[0]["end"]


def test_moon_mid_ashwini_rahu_antardasha():
    """Review probe: Moon halfway through Ashwini runs Ketu-Rahu at birth."""
    birth = datetime(2000, 1, 1, tzinfo=UTC)
    nested = compute_vimshottari_nested_periods(birth, 360 / 54, depth=2)
    assert get_vimshottari_chain_at(birth, nested) == ("Ketu", "Rahu")
    assert all(p["end"] > birth for p in nested)


def test_depth_validation():
    """Depth must be at least 1."""
    with pytest.raises(ValueError):
        compute_vimshottari_nested_periods(datetime(2000, 1, 1, tzinfo=UTC), 0.0, 0)
