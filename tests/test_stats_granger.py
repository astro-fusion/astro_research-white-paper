"""Tests for the exogenous-regressor ADL Granger test."""

import sys

import numpy as np
import pandas as pd
import pytest

from vedic_astrology_core.stats.granger import (
    exog_granger,
    garch_available,
    garch_standardised_abs,
    newey_west_lags,
)


def _frame(effect, seed):
    rng = np.random.default_rng(seed)
    n = 1500
    idx = pd.date_range("2000-01-01", periods=n, freq="D")
    x = np.sin(2 * np.pi * np.arange(n) / 29.5) + 0.3 * rng.normal(size=n)
    y = 0.1 * rng.normal(size=n)
    y[1:] += effect * x[:-1]
    return pd.Series(y, idx), pd.DataFrame({"moon": x}, idx)


def test_lagged_exogenous_effect_is_detected():
    """y_t depends on x_{t-1}: tiny p-value."""
    y, x = _frame(0.2, 0)
    res = exog_granger(y, x, lags=(1, 2))
    assert res["transform"] == "none"
    assert res["p_value"] < 1e-6
    assert res["exog_coefficients"]["moon_lag1"] == pytest.approx(0.2, abs=0.03)


def test_no_effect_is_not_rejected():
    """Independent y gives a non-small p-value."""
    y, x = _frame(0.0, 1)
    res = exog_granger(y, x, lags=(1, 2))
    assert res["p_value"] > 0.05


def test_gate_refuses_integrated_of_order_two():
    """An I(2) outcome is refused, not tested."""
    y, x = _frame(0.0, 2)
    y2 = pd.Series(np.cumsum(np.cumsum(y.to_numpy())) - 1e3, y.index)
    res = exog_granger(y2, x, lags=(1,))
    assert res["p_value"] is None and res["verdict"] == "nonstationary"


def test_lag_set_must_be_a_priori_positive():
    """Lag 0 or an empty set is an error; NW rule matches the formula."""
    y, x = _frame(0.0, 3)
    with pytest.raises(ValueError):
        exog_granger(y, x, lags=(0, 1))
    assert newey_west_lags(100) == 4


@pytest.mark.skipif(not garch_available(), reason="optional arch not installed")
def test_garch_target_runs():
    """The GARCH-standardised absolute-return target fits."""
    y, x = _frame(0.0, 4)
    res = exog_granger(y, x, lags=(1,), target="garch_abs")
    assert 0.0 <= res["p_value"] <= 1.0


@pytest.fixture
def fake_arch(monkeypatch):
    """Stand-in for the arch fit so the past-only schedule runs without arch."""
    from vedic_astrology_core.stats import volatility

    def fit(train):
        return float(np.mean(train)), 0.05 * float(np.var(train)), 0.08, 0.87

    monkeypatch.setattr(volatility, "garch_available", lambda: True)
    monkeypatch.setattr(volatility, "_fit_garch11", fit)


def test_garch_abs_target_is_past_only(fake_arch):
    """The garch_abs target drops the burn-in and ignores data after t."""
    y, _ = _frame(0.0, 5)
    z = garch_standardised_abs(y, min_train=500, refit_every=21)
    assert len(z) == len(y) - 500 and z.index[0] == y.index[500]
    y2 = y.copy()
    y2.iloc[901:] *= 3.0
    z2 = garch_standardised_abs(y2, min_train=500, refit_every=21)
    pd.testing.assert_series_equal(z.loc[: y.index[900]], z2.loc[: y.index[900]])


def test_garch_abs_target_in_exog_granger_uses_burn_in(fake_arch):
    """exog_granger on garch_abs loses the burn-in bars and still tests."""
    y, x = _frame(0.0, 6)
    full = exog_granger(y, x, lags=(1,), target="returns")
    res = exog_granger(y, x, lags=(1,), target="garch_abs", garch_min_train=400)
    assert res["n"] == full["n"] - 400
    assert 0.0 <= res["p_value"] <= 1.0


def test_garch_abs_without_arch_raises(monkeypatch):
    """No arch: the garch_abs target raises instead of switching target."""
    monkeypatch.setitem(sys.modules, "arch", None)
    assert garch_available() is False
    y, x = _frame(0.0, 7)
    with pytest.raises(RuntimeError, match="arch"):
        exog_granger(y, x, lags=(1,), target="garch_abs")
