"""Tests for event-rate ratios and the circular-shift rate test."""

import numpy as np
import pytest

from vedic_astrology_core.stats.rates import (
    indicator_rate_ratio,
    rate_ratio,
    rate_ratio_shift_test,
)


def test_equal_rates_known_interval():
    """10 events in each of two equal exposures: Clopper-Pearson 10/20."""
    rr = rate_ratio(10, 100.0, 10, 100.0)
    assert rr.rate_ratio == pytest.approx(1.0)
    assert rr.ci_low == pytest.approx(0.2720 / 0.7280, rel=2e-3)
    assert rr.ci_high == pytest.approx(0.7280 / 0.2720, rel=2e-3)
    assert rr.p_two_sided == pytest.approx(1.0)


def test_exposure_scaling():
    """Same events, exposure ratio 1:3, gives RR 3."""
    rr = rate_ratio(5, 25.0, 5, 75.0)
    assert rr.rate_ratio == pytest.approx(3.0)
    assert rr.ci_low < 3.0 < rr.ci_high


def test_zero_events_inside():
    """n_in = 0 gives RR 0 with lower bound 0."""
    rr = rate_ratio(0, 10.0, 20, 90.0)
    assert rr.rate_ratio == 0.0 and rr.ci_low == 0.0 and rr.ci_high > 0
    with pytest.raises(ValueError):
        rate_ratio(1, 0.0, 1, 1.0)


def test_indicator_rate_ratio_counts_grid():
    """Counts are read from the grid."""
    ind = np.zeros(100, dtype=int)
    ind[:20] = 1
    rr = indicator_rate_ratio([1, 2, 50, 60], ind)
    assert (rr.n_in, rr.t_in, rr.n_out, rr.t_out) == (2, 20.0, 2, 80.0)
    assert rr.rate_ratio == pytest.approx(4.0)


def _runs(n, seed):
    return (np.sin(np.arange(n) / 30.0 + seed) > 0.7).astype(int)


def test_shift_test_detects_events_inside_runs():
    """Events only inside indicator runs give the minimum p-value."""
    ind = _runs(5000, 0)
    rng = np.random.default_rng(0)
    events = rng.choice(np.flatnonzero(ind), size=40, replace=False)
    res = rate_ratio_shift_test(events, ind, 500, 999, np.random.default_rng(1))
    assert res.p_value == pytest.approx(1 / 1000)
    assert res.exact.rate_ratio == np.inf or res.exact.rate_ratio > 3


def test_shift_test_null_for_unrelated_clustered_events():
    """Clustered events unrelated to the indicator are not significant."""
    rng = np.random.default_rng(2)
    centres = rng.integers(0, 5000, size=8)
    events = np.clip((centres[:, None] + rng.integers(0, 15, (8, 10))).ravel(),
                     0, 4999)
    res = rate_ratio_shift_test(events, _runs(5000, 1.3), 500, 999,
                                np.random.default_rng(3), alternative="two-sided")
    assert res.p_value > 0.05
    assert res.null_q025 <= res.null_median <= res.null_q975
