"""Tests for nested Vimshottari periods."""
from datetime import datetime

from vedic_astrology_core.dasha.vimshottari import compute_vimshottari_nested_periods


def test_nested_depth_two_generates_antardasha():
    birth = datetime(2000, 1, 1)
    moon_long = 0.0
    nested = compute_vimshottari_nested_periods(birth, moon_long, depth=2, total_years=120)
    # Should have 9*9 periods for depth=2
    assert len(nested) == 81
    # Each entry should include lords tuple of length 2
    assert all(len(p["lords"]) == 2 for p in nested)


def test_nested_depth_three_generates_pratyantar():
    birth = datetime(2000, 1, 1)
    moon_long = 0.0
    nested = compute_vimshottari_nested_periods(birth, moon_long, depth=3, total_years=120)
    assert len(nested) == 729
    assert all(len(p["lords"]) == 3 for p in nested)
