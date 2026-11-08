"""Tests for the rule-free classifier (time-ordered CV, shifted-sky null)."""

import numpy as np
import pytest

from vedic_astrology_core.stats.classify import (
    auc,
    fit_ridge_logistic,
    forward_chaining_auc,
    shifted_sky_auc_test,
)


def test_auc_known_answer():
    """Check auc known answer."""
    assert auc([0, 0, 1, 1], [0.1, 0.4, 0.35, 0.8]) == pytest.approx(0.75)
    assert auc([0, 1], [0.2, 0.2]) == pytest.approx(0.5)


def test_ridge_logistic_recovers_sign():
    """Check ridge logistic recovers sign."""
    rng = np.random.default_rng(0)
    x = rng.normal(size=(2000, 3))
    y = (rng.random(2000) < 1 / (1 + np.exp(-(2 * x[:, 0] - 1)))).astype(int)
    model = fit_ridge_logistic(x, y, l2=1.0)
    assert model.coef[0] > 1.0 and abs(model.coef[1]) < 0.3


def _periodic(n, rng):
    """Build the periodic fixture."""
    t = np.arange(n)
    x = np.column_stack([np.sin(2 * np.pi * t / 29.5), np.cos(2 * np.pi * t / 29.5)])
    noise = rng.normal(size=(n, 4))
    return np.column_stack([x, noise])


def test_informative_sky_beats_shifted_sky():
    """Check informative sky beats shifted sky."""
    rng = np.random.default_rng(1)
    n = 6000
    x = _periodic(n, rng)
    y = (rng.random(n) < 0.02 * np.exp(1.5 * x[:, 0])).astype(int)
    res = shifted_sky_auc_test(
        x, y, min_shift=400, n_draws=40, rng=np.random.default_rng(2), n_folds=4
    )
    assert res.auc > 0.65
    assert res.p_value <= 2 / 41
    assert res.null_q50 < res.auc


def test_noise_sky_is_not_significant():
    """Check noise sky is not significant."""
    rng = np.random.default_rng(3)
    n = 4000
    x = _periodic(n, rng)
    y = (rng.random(n) < 0.03).astype(int)
    res = shifted_sky_auc_test(
        x, y, min_shift=300, n_draws=40, rng=np.random.default_rng(4), n_folds=4
    )
    assert 0.35 < res.auc < 0.65
    assert res.p_value > 0.05


def test_forward_chaining_never_trains_on_the_future():
    """Check forward chaining never trains on the future."""
    seen = []
    x = np.arange(100, dtype=float)[:, None]
    y = (np.arange(100) % 7 == 0).astype(int)
    forward_chaining_auc(x, y, n_folds=4, on_split=lambda tr, te: seen.append((tr, te)))
    assert len(seen) == 4
    for tr, te in seen:
        assert tr.max() < te.min()
