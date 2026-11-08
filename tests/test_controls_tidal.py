"""Tests for positive and negative controls."""

import numpy as np
import pandas as pd
import pytest

from vedic_astrology_core.stats.controls import (
    REFERENCES,
    lunar_elongation,
    monsoon_flag,
    shifted_sky,
    tidal_phase_indicators,
)


def test_elongation_wraps():
    """Check elongation wraps."""
    assert lunar_elongation(10.0, 350.0) == pytest.approx(20.0)
    assert lunar_elongation(350.0, 10.0) == pytest.approx(340.0)


def test_tidal_indicators_duty_cycles():
    """Check tidal indicators duty cycles."""
    ha = np.linspace(0, 360, 3601)[:-1]
    el = np.linspace(0, 360, 3601)[:-1]
    t = tidal_phase_indicators(
        ha, el, semidiurnal_half_width_deg=45, spring_half_width_deg=45
    )
    assert t["tide_semidiurnal_peak"].mean() == pytest.approx(0.5, abs=0.002)
    assert t["tide_spring"].mean() == pytest.approx(0.5, abs=0.002)
    # Upper and lower culmination are both peaks; quadrature is not.
    assert t["tide_semidiurnal_peak"][0] and t["tide_semidiurnal_peak"][1800]
    assert not t["tide_semidiurnal_peak"][900]
    # New and full Moon are spring tides; quarters are neap.
    assert t["tide_spring"][0] and t["tide_spring"][1800]
    assert not t["tide_spring"][900]


def test_combined_is_intersection():
    """Check combined is intersection."""
    rng = np.random.default_rng(0)
    ha, el = rng.uniform(0, 360, 1000), rng.uniform(0, 360, 1000)
    t = tidal_phase_indicators(ha, el)
    both = t["tide_semidiurnal_peak"] & t["tide_spring"]
    assert (t["tide_spring_and_peak"] == both).all()


def test_shifted_sky_rolls_every_column_by_the_same_offset():
    """Check shifted sky rolls every column by the same offset."""
    f = pd.DataFrame({"a": [1, 0, 0, 0], "b": [0, 1, 0, 0]}, dtype=bool)
    s = shifted_sky(f, 1)
    assert s["a"].tolist() == [False, True, False, False]
    assert s["b"].tolist() == [False, False, True, False]
    assert (s.index == f.index).all()
    with pytest.raises(ValueError):
        shifted_sky(f, 0)


def test_monsoon_flag_and_references():
    """Check monsoon flag and references."""
    idx = pd.date_range("2020-01-01", "2020-12-31", freq="D", tz="UTC")
    m = monsoon_flag(idx)
    assert m.sum() == 30 + 31 + 31 + 30
    assert "ide2016" in REFERENCES and "cochran2004" in REFERENCES


def test_moon_hour_angle_range():
    """Check moon hour angle range."""
    pytest.importorskip("swisseph")
    from vedic_astrology_core.stats.controls import moon_hour_angle

    jd = 2451545.0 + np.arange(0, 2, 1 / 24)
    ha = moon_hour_angle(jd, 85.0)
    assert ((ha >= 0) & (ha < 360)).all()
    # The hour angle advances by 360 deg minus the Moon's daily RA motion
    # (about 11 to 18 deg) per solar day.
    step = np.diff(np.unwrap(np.radians(ha)))
    assert 340 < np.degrees(step.sum()) / 2 < 350
