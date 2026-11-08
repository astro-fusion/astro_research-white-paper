"""Tests for the generic permutation test."""

import numpy as np
import pytest

from vedic_astrology_core.stats.permutation import (
    empirical_p_value,
    permutation_test,
)


def _mean_in(x, y):
    return float(y[x.astype(bool)].mean())


def test_p_value_is_never_zero():
    """Observed beyond all 99 null draws gives exactly 1/100."""
    assert empirical_p_value(5.0, np.zeros(99), "greater") == pytest.approx(0.01)
    assert empirical_p_value(-5.0, np.zeros(99), "less") == pytest.approx(0.01)
    assert empirical_p_value(0.0, np.zeros(99), "greater") == pytest.approx(1.0)


def test_two_sided_counts_distance_from_null_mean():
    """Two-sided extremeness is |stat - null mean|."""
    null = np.array([-2.0, -1.0, 0.0, 1.0, 2.0])
    assert empirical_p_value(1.5, null, "two-sided") == pytest.approx(3 / 6)


def test_planted_effect_is_detected_by_every_null():
    """An outcome raised during indicator runs gives a small p-value."""
    rng = np.random.default_rng(0)
    x = (np.sin(np.arange(3000) / 40.0) > 0.6).astype(int)
    y = rng.normal(size=3000) + 1.0 * x
    for null, kw in (
        ("circular_shift", {"min_shift": 300}),
        ("block_bootstrap", {"mean_block": 20}),
        ("phase", {}),
    ):
        res = permutation_test(
            _mean_in,
            x,
            y,
            rng=np.random.default_rng(1),
            null=null,
            n_perm=199,
            n_boot=99,
            **kw,
        )
        assert res.p_value == pytest.approx(1 / 200), null
        assert res.effect > 0.5
        assert res.ci_low < res.observed < res.ci_high
        assert len(res.null_stats) == 199


def test_independent_series_is_not_significant():
    """No effect gives a large p-value and an effect near zero."""
    rng = np.random.default_rng(4)
    x = (np.sin(np.arange(3000) / 40.0) > 0.6).astype(int)
    y = rng.normal(size=3000)
    res = permutation_test(
        _mean_in,
        x,
        y,
        rng=np.random.default_rng(5),
        min_shift=300,
        n_perm=499,
        n_boot=0,
    )
    assert res.p_value > 0.05
    assert abs(res.effect_z) < 2.5
    assert np.isnan(res.ci_low)


def test_bad_arguments_raise():
    """Unknown null, missing min_shift and length mismatch are errors."""
    x, y = np.zeros(100), np.zeros(100)
    rng = np.random.default_rng(0)
    with pytest.raises(ValueError):
        permutation_test(_mean_in, x, y, rng=rng, null="shuffle")
    with pytest.raises(ValueError):
        permutation_test(_mean_in, x, y, rng=rng)
    with pytest.raises(ValueError):
        permutation_test(_mean_in, x, y[:50], rng=rng, min_shift=10)
