"""Tests for past-only volatility standardisation and the GARCH-X test."""

import sys

import numpy as np
import pandas as pd
import pytest

from vedic_astrology_core.stats import volatility as vol
from vedic_astrology_core.stats.nulls import n_admissible_shifts


def _returns(n=1200, seed=0):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2001-01-01", periods=n, freq="D")
    return pd.Series(0.01 * rng.standard_t(5, size=n), idx)


def _fake_fitter(calls):
    """Deterministic stand-in for the arch fit; depends on every bar it sees."""

    def fit(train):
        calls.append(len(train))
        var = float(np.var(train))
        return float(np.mean(train)), 0.05 * var, 0.08, 0.87

    return fit


@pytest.fixture
def fake_arch(monkeypatch):
    calls = []
    monkeypatch.setattr(vol, "garch_available", lambda: True)
    monkeypatch.setattr(vol, "_fit_garch11", _fake_fitter(calls))
    return calls


def _perturb_after(r, t, seed=99):
    r2 = r.copy()
    rng = np.random.default_rng(seed)
    r2.iloc[t + 1 :] = 0.05 * rng.normal(size=len(r) - t - 1)
    return r2


@pytest.mark.parametrize("t", [500, 523, 700, 1100])
def test_garch_schedule_is_past_only(fake_arch, t):
    """Changing data after t leaves every value up to t unchanged."""
    r = _returns()
    a = vol.past_only_volatility(r, method="garch", min_train=500, refit_every=21)
    b = vol.past_only_volatility(_perturb_after(r, t), method="garch", min_train=500, refit_every=21)
    pd.testing.assert_frame_equal(a.iloc[: t + 1], b.iloc[: t + 1])
    assert not np.allclose(a["sigma"].iloc[t + 2 :], b["sigma"].iloc[t + 2 :])


def test_garch_refits_on_fixed_schedule_with_data_to_t_minus_1(fake_arch):
    """Each fit sees exactly bars [0, k), k = min_train + j * refit_every."""
    r = _returns(n=1000)
    out = vol.past_only_volatility(r, method="garch", min_train=500, refit_every=50)
    assert fake_arch == list(range(500, 1000, 50))
    assert out["sigma"].iloc[:500].isna().all() and out["fit_end"].iloc[:500].eq(-1).all()
    pos = np.arange(1000)
    fe = out["fit_end"].to_numpy()
    assert np.all(fe[500:] <= pos[500:])
    assert np.all(fe[500:] == 500 + 50 * ((pos[500:] - 500) // 50))
    assert out["z"].iloc[500:].notna().all()


def test_ewma_is_past_only_and_needs_no_arch(monkeypatch):
    """EWMA sigma_t uses returns up to t - 1; z_t changes only with r_t."""
    monkeypatch.setattr(vol, "garch_available", lambda: False)
    r = _returns()
    t = 800
    a = vol.past_only_volatility(r, method="ewma", min_train=250)
    b = vol.past_only_volatility(_perturb_after(r, t), method="ewma", min_train=250)
    pd.testing.assert_frame_equal(a.iloc[: t + 1], b.iloc[: t + 1])
    # sigma at t + 1 depends on r_t only through the past, so changing r_{t+1}
    # alone leaves sigma_{t+1} unchanged.
    c = r.copy()
    c.iloc[t + 1] += 0.5
    d = vol.past_only_volatility(c, method="ewma", min_train=250)
    assert d["sigma"].iloc[t + 1] == a["sigma"].iloc[t + 1]
    assert d["z"].iloc[t + 1] != a["z"].iloc[t + 1]
    lam = 0.94
    h = a["sigma"].to_numpy() ** 2
    assert h[t + 1] == pytest.approx(lam * h[t] + (1 - lam) * r.iloc[t] ** 2)


def test_missing_arch_raises_without_fallback(monkeypatch):
    """With arch unimportable, method='garch' raises; no other model is used."""
    monkeypatch.setitem(sys.modules, "arch", None)
    assert vol.garch_available() is False
    with pytest.raises(RuntimeError, match="arch"):
        vol.past_only_volatility(_returns(), method="garch")
    with pytest.raises(RuntimeError, match="arch"):
        vol.standardised_abs(_returns())


def test_bad_arguments():
    r = _returns(n=300)
    with pytest.raises(ValueError):
        vol.past_only_volatility(r, method="har")
    with pytest.raises(ValueError):
        vol.past_only_volatility(r, method="ewma", min_train=500)
    with pytest.raises(ValueError):
        vol.past_only_volatility(r, method="ewma", min_train=100, ewma_lambda=1.0)


@pytest.mark.skipif(not vol.garch_available(), reason="optional arch not installed")
def test_real_garch_fit_is_past_only():
    """With arch installed, the real fit is also invariant to the future."""
    r = _returns(n=700)
    a = vol.past_only_volatility(r, min_train=500, refit_every=50)
    b = vol.past_only_volatility(_perturb_after(r, 560), min_train=500, refit_every=50)
    pd.testing.assert_frame_equal(a.iloc[:561], b.iloc[:561])
    assert a["z"].iloc[500:].abs().mean() == pytest.approx(0.8, abs=0.25)


# --------------------------------------------------------------------------
# GARCH-X
# --------------------------------------------------------------------------


def _blocks(n, seed, mean_run=60):
    rng = np.random.default_rng(seed)
    x = np.zeros(n)
    i, state = 0, 0
    while i < n:
        run = int(rng.integers(mean_run // 2, 3 * mean_run // 2))
        x[i : i + run] = state
        state = 1 - state
        i += run
    return x


def _garch_x_sim(n, x, log_ratio, seed):
    rng = np.random.default_rng(seed)
    omega = 0.05 * np.exp(log_ratio * x)
    alpha, beta = 0.08, 0.87
    r = np.empty(n)
    h = 1.0
    e_prev = 0.0
    for t in range(n):
        h = omega[t] + alpha * e_prev**2 + beta * h
        r[t] = np.sqrt(h) * rng.normal()
        e_prev = r[t]
    return 0.01 * r


def test_garch_x_detects_variance_effect():
    """A strong indicator effect in the variance equation sits at the p floor."""
    n = 1500
    x = _blocks(n, 1)
    r = _garch_x_sim(n, x, np.log(4.0), 2)
    res = vol.garch_x_test(r, x, min_shift=100, n_shifts=19, rng=np.random.default_rng(3))
    assert res["lr"] > 20.0
    assert res["p_value"] == pytest.approx(1 / 20)
    assert res["p_min"] == pytest.approx(1 / 20)
    assert res["gamma"] == pytest.approx(np.log(4.0), abs=0.6)
    assert res["loglik_unrestricted"] >= res["loglik_restricted"]


def test_garch_x_null_and_p_value_definition():
    """No effect: p is not small and equals (n_extreme + 1) / (n_shifts + 1)."""
    n = 1500
    x = _blocks(n, 4)
    r = _garch_x_sim(n, x, 0.0, 5)
    res = vol.garch_x_test(r, x, min_shift=100, n_shifts=19, rng=np.random.default_rng(6))
    assert res["p_value"] > 0.1
    assert res["lr"] >= 0.0 and min(res["null_lr"]) >= 0.0
    n_ext = sum(v >= res["lr"] - 1e-8 * max(1.0, res["lr"]) for v in res["null_lr"])
    assert res["n_extreme"] == n_ext
    assert res["p_value"] == pytest.approx((n_ext + 1) / 20)
    assert res["null"] == "circular_shift" and res["n_shifts"] == 19


def test_garch_x_exact_enumeration_and_controls():
    """Few admissible shifts are all used; controls enter both models."""
    n = 1000
    x = pd.DataFrame({"jupiter_cap": _blocks(n, 7, mean_run=40)})
    ctrl = pd.DataFrame({"monday": (np.arange(n) % 5 == 0).astype(float)})
    r = _garch_x_sim(n, x["jupiter_cap"].to_numpy(), 0.0, 8)
    min_shift = 490
    m = n_admissible_shifts(n, min_shift)
    res = vol.garch_x_test(
        r, x, controls=ctrl, min_shift=min_shift, n_shifts=100, rng=np.random.default_rng(9)
    )
    assert res["exact_enumeration"] and res["n_shifts"] == m == 21
    assert set(res["gamma"]) == {"jupiter_cap"}
    assert len(res["params_restricted"]["delta"]) == 1
    again = vol.garch_x_test(
        r, x, controls=ctrl, min_shift=min_shift, n_shifts=100, rng=np.random.default_rng(1)
    )
    assert again["p_value"] == res["p_value"]


def test_garch_x_input_checks():
    r = _returns(n=600).to_numpy()
    with pytest.raises(ValueError):
        vol.garch_x_test(r, np.ones(600), rng=np.random.default_rng(0))
    with pytest.raises(ValueError):
        vol.garch_x_test(r, np.ones(500), rng=np.random.default_rng(0))
    with pytest.raises(TypeError):
        vol.garch_x_test(r, _blocks(600, 0), min_shift=100, rng=None)
