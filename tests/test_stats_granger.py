"""Tests for the exogenous-regressor ADL Granger test."""

import numpy as np
import pandas as pd
import pytest

from vedic_astrology_core.stats.granger import (
    exog_granger,
    garch_available,
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
