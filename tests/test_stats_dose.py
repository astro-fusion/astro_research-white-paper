"""Tests for dose-response trend tests across strength bins."""

import numpy as np
import pytest

from vedic_astrology_core.stats.dose import cochran_armitage, dose_response


def test_cochran_armitage_equals_n_r_squared():
    """CA z^2 equals N r^2, r the Pearson correlation of score and outcome."""
    rng = np.random.default_rng(0)
    score = rng.integers(0, 5, 400)
    y = (rng.random(400) < 0.1 + 0.05 * score).astype(int)
    z, p = cochran_armitage(score, y)
    r = np.corrcoef(score, y)[0, 1]
    assert z**2 == pytest.approx(len(y) * r**2, rel=1e-9)
    assert 0 < p < 1


def test_binary_trend_detected_and_flat_not():
    """Check binary trend detected and flat not."""
    rng = np.random.default_rng(1)
    s = rng.random(5000)
    y_trend = (rng.random(5000) < 0.02 + 0.1 * s).astype(int)
    y_flat = (rng.random(5000) < 0.05).astype(int)
    up = dose_response(s, y_trend)
    flat = dose_response(s, y_flat)
    assert up.method == "cochran_armitage" and up.p_value < 1e-6
    assert up.statistic > 0
    assert flat.p_value > 0.001
    assert len(up.table) == 5
    assert up.table["n"].sum() == 5000


def test_continuous_uses_spearman():
    """Check continuous uses spearman."""
    rng = np.random.default_rng(2)
    s = rng.random(500)
    y = s + rng.normal(0, 0.5, 500)
    res = dose_response(s, y, n_bins=4)
    assert res.method == "spearman" and res.p_value < 1e-3 and res.statistic > 0
    assert len(res.table) == 4


def test_ties_and_bad_input():
    """Check ties and bad input."""
    s = np.r_[np.zeros(80), np.ones(20)]
    y = np.r_[np.zeros(80), np.ones(20)].astype(int)
    res = dose_response(s, y, n_bins=5)
    assert len(res.table) == 2 and res.p_value < 1e-6
    with pytest.raises(ValueError):
        dose_response([1, 2], [1], n_bins=2)
