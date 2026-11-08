"""Tests for the ADF/KPSS stationarity gate."""

import numpy as np
import pandas as pd
import pytest

from vedic_astrology_core.stats.stationarity import (
    apply_transform,
    stationarity_gate,
)


def _rng(seed=0):
    return np.random.default_rng(seed)


def test_white_noise_passes_without_transform():
    """White noise is stationary as it is."""
    y = pd.Series(_rng(1).normal(size=800))
    res = stationarity_gate(y)
    assert res.verdict == "stationary"
    assert res.transform == "none"
    assert len(res.series) == 800


def test_random_walk_with_negatives_is_differenced():
    """A random walk crossing zero gets a plain first difference."""
    y = pd.Series(np.cumsum(_rng(2).normal(size=800)) - 5.0)
    assert (y < 0).any()
    res = stationarity_gate(y)
    assert res.transform == "diff"
    assert res.stationary
    assert res.tests["none"]["adf_p"] > 0.05


def test_positive_price_walk_gets_log_diff():
    """A strictly positive geometric walk gets log returns."""
    y = pd.Series(100.0 * np.exp(np.cumsum(_rng(3).normal(0, 0.01, size=800))))
    res = stationarity_gate(y)
    assert res.transform == "log-diff"
    assert res.stationary
    np.testing.assert_allclose(res.series.to_numpy(), np.diff(np.log(y.to_numpy())))


def test_integrated_of_order_two_is_refused():
    """One difference of an I(2) series is still non-stationary."""
    y = pd.Series(np.cumsum(np.cumsum(_rng(4).normal(size=800))) - 1e4)
    res = stationarity_gate(y)
    assert res.verdict == "nonstationary"


def test_transform_errors():
    """Bad transforms and log of non-positive data raise."""
    with pytest.raises(ValueError):
        apply_transform(pd.Series([1.0, -1.0, 2.0]), "log-diff")
    with pytest.raises(ValueError):
        apply_transform(pd.Series([1.0, 2.0]), "boxcox")
    with pytest.raises(ValueError):
        stationarity_gate(pd.Series(np.ones(50)))
