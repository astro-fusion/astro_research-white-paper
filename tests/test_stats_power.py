"""Tests for the simulated minimum detectable rate ratio."""

import numpy as np
import pandas as pd
import pytest
from scipy import stats as sps

from vedic_astrology_core.stats.power import (
    minimum_detectable_difference,
    minimum_detectable_rate_ratio,
    power_at_rate_ratio,
    power_table,
)


def _analytic_mdrr(n, d, alpha, power):
    """Return the normal-approximation MDRR of the one-sided binomial test."""
    za, zb = sps.norm.ppf(1 - alpha), sps.norm.ppf(power)
    p0 = d
    p1 = p0 + (za * np.sqrt(p0 * (1 - p0)) + zb * np.sqrt(p0 * (1 - p0))) / np.sqrt(n)
    return (p1 / (1 - p1)) * (1 - d) / d


def test_known_answer_against_normal_approximation():
    """1000 events, duty 0.5: simulation agrees with the binomial normal approx."""
    mdrr = minimum_detectable_rate_ratio(
        1000, 0.5, 0.05, 0.8, np.random.default_rng(1), n_sim=4000
    )
    assert mdrr == pytest.approx(_analytic_mdrr(1000, 0.5, 0.05, 0.8), rel=0.03)


def test_more_events_detect_smaller_effects():
    """MDRR shrinks as the event count grows and grows as duty falls."""
    rng = np.random.default_rng
    a = minimum_detectable_rate_ratio(100, 0.2, 0.05, 0.8, rng(2), n_sim=2000)
    b = minimum_detectable_rate_ratio(1000, 0.2, 0.05, 0.8, rng(2), n_sim=2000)
    c = minimum_detectable_rate_ratio(1000, 0.02, 0.05, 0.8, rng(2), n_sim=2000)
    assert a > b > 1.0
    assert c > b


def test_power_at_null_is_alpha():
    """At RR = 1 the rejection rate is at most alpha (up to MC error)."""
    pw = power_at_rate_ratio(1.0, 200, 0.3, 0.05, np.random.default_rng(3), 4000)
    assert pw <= 0.05 + 3 * np.sqrt(0.05 * 0.95 / 4000)


def test_two_sided_needs_a_larger_effect():
    """Two-sided tests spend alpha/2 per tail, so the MDRR is larger."""
    rng = np.random.default_rng
    one = minimum_detectable_rate_ratio(300, 0.2, 0.05, 0.8, rng(4), n_sim=2000)
    two = minimum_detectable_rate_ratio(
        300, 0.2, 0.05, 0.8, rng(4), n_sim=2000, two_sided=True
    )
    assert two > one > 1.0


def test_minimum_detectable_difference_from_ci():
    """MDE = (z_{1-a/2} + z_power) * SE, SE from a 95% CI."""
    mde = minimum_detectable_difference(-1.96, 1.96, alpha=0.05, power=0.8)
    assert mde == pytest.approx(1.959964 + 0.841621, rel=1e-4)


def test_power_table_one_row_per_indicator():
    """Check power table one row per indicator."""
    specs = [
        {"id": "a", "n_events": 150, "duty_cycle": 0.1, "direction": "greater"},
        {"id": "b", "n_events": 150, "duty_cycle": 0.5, "direction": "two-sided"},
    ]
    tab = power_table(specs, np.random.default_rng(5), n_sim=1000)
    assert isinstance(tab, pd.DataFrame)
    assert list(tab["id"]) == ["a", "b"]
    assert (tab["mdrr"] > 1).all()
    assert tab.loc[0, "expected_in"] == pytest.approx(15.0)
