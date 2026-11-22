"""Calendar, festival, lunar and macro baselines and incremental_test (ADR-004 WP-06)."""

import numpy as np
import pandas as pd
import pytest

from vedic_astrology_core.markets import baselines as b


@pytest.fixture(scope="module")
def days():
    return pd.bdate_range("2019-01-01", "2019-12-31")


def test_calendar_terms_shape_and_reference_levels(days):
    t = b.calendar_terms(days)
    assert "month_01" not in t and "month_02" in t and "wd_0" not in t
    assert t.loc["2019-03-12", "month_03"] == 1 and t.loc["2019-03-12", "wd_1"] == 1
    assert set(np.unique(t.to_numpy())) <= {0, 1}


def test_turn_of_month_is_last_day_and_first_three(days):
    t = b.calendar_terms(days)["turn_of_month"]
    assert t.loc["2019-01-31"] == 1 and t.loc["2019-02-01"] == 1
    assert t.loc["2019-02-05"] == 1 and t.loc["2019-02-06"] == 0
    assert t.loc["2019-02-27"] == 0


def test_holiday_eve_and_after_for_us_federal_holidays(days):
    # Thanksgiving 2019-11-28 and Christmas 2019-12-25 are not bars.
    bars = days.drop(pd.to_datetime(["2019-11-28", "2019-12-25"]))
    t = b.calendar_terms(bars)
    assert t.loc["2019-11-27", "holiday_eve"] == 1 and t.loc["2019-11-29", "holiday_after"] == 1
    assert t.loc["2019-12-24", "holiday_eve"] == 1 and t.loc["2019-12-26", "holiday_after"] == 1


def test_lunar_phase_terms_known_syzygies():
    idx = pd.to_datetime(["2020-11-15", "2020-11-30", "2020-11-21"])
    t = b.lunar_phase_terms(idx)
    assert t.loc["2020-11-15", "new_moon_day"] == 1  # new moon 2020-11-15 05:07 UTC
    assert t.loc["2020-11-30", "full_moon_day"] == 1  # full moon 2020-11-30 09:30 UTC
    assert t.loc["2020-11-21", "new_moon_day"] == 0 and t.loc["2020-11-21", "full_moon_day"] == 0
    assert np.allclose(t["moon_sin"] ** 2 + t["moon_cos"] ** 2, 1.0)


def test_macro_join_uses_only_values_known_at_t_minus_1():
    idx = pd.bdate_range("2020-01-01", "2020-01-10")
    macro = pd.Series([1.0, 2.0, 3.0], index=pd.to_datetime(["2020-01-02", "2020-01-06", "2020-01-08"]))
    j = b.macro_join(idx, macro)
    assert np.isnan(j.loc["2020-01-01"]) and np.isnan(j.loc["2020-01-02"])  # same-day print unused
    assert j.loc["2020-01-03"] == 1.0 and j.loc["2020-01-06"] == 1.0
    assert j.loc["2020-01-07"] == 2.0 and j.loc["2020-01-09"] == 3.0


def test_macro_join_release_lag_and_no_look_ahead():
    idx = pd.bdate_range("2020-01-01", "2020-01-31")
    macro = pd.Series([5.0, 7.0], index=pd.to_datetime(["2020-01-01", "2020-01-15"]))
    j = b.macro_join(idx, macro, release_lag_days=10)
    assert j.loc[:"2020-01-11"].isna().all() and j.loc["2020-01-13"] == 5.0
    assert j.loc["2020-01-24"] == 5.0 and j.loc["2020-01-27"] == 7.0
    # changing a future observation never changes earlier bars
    macro2 = macro.copy()
    macro2.iloc[1] = 99.0
    j2 = b.macro_join(idx, macro2, release_lag_days=10)
    assert j.loc[:"2020-01-24"].equals(j2.loc[:"2020-01-24"])


def test_build_baselines_has_all_families(days):
    macro = {"rate": pd.Series(np.arange(len(days), dtype=float), index=days)}
    t = b.build_baselines(days[:120], macro=macro)
    assert {"month_02", "wd_1", "turn_of_month", "moon_sin", "macro_rate"} <= set(t.columns)
    assert t.index.equals(days[:120])


def _simulate(n=1500, seed=3, effect=0.0):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2010-01-01", periods=n)
    base = b.calendar_terms(idx)
    cal = 0.6 * base["turn_of_month"].to_numpy() + 0.3 * base["wd_4"].to_numpy()
    # an indicator that is mostly the calendar term plus a slow astro-like cycle
    cyc = (np.sin(np.arange(n) * 2 * np.pi / 29.5) > 0.4).astype(float)
    ind = np.clip(base["turn_of_month"].to_numpy() + cyc, 0, 1)
    y = cal + effect * cyc + rng.normal(0, 1, n)
    return idx, base, y, ind, cyc


def test_incremental_test_removes_calendar_confound():
    idx, base, y, ind, _ = _simulate()
    res = b.incremental_test(y, ind, base, 60, 400, np.random.default_rng(1))
    assert res["r_raw"] > 0.1 > abs(res["r_incremental"]) * 1.0 or abs(res["r_incremental"]) < res["r_raw"]
    assert res["p"] > 0.01
    assert res["n_baseline_terms"] > 10 and res["n_shifts"] == 400


def test_incremental_test_detects_a_real_increment():
    idx, base, y, ind, cyc = _simulate(effect=0.8)
    res = b.incremental_test(y, cyc, base, 60, 400, np.random.default_rng(2))
    assert res["r_incremental"] > 0.15 and res["p"] < 0.05


def test_incremental_test_is_deterministic_and_validates_inputs():
    idx, base, y, ind, _ = _simulate(n=600)
    r1 = b.incremental_test(y, ind, base, 50, 200, np.random.default_rng(5))
    r2 = b.incremental_test(y, ind, base, 50, 200, np.random.default_rng(5))
    assert r1 == r2
    with pytest.raises(ValueError):
        b.incremental_test(y[:-1], ind, base, 50, 10, np.random.default_rng(0))
    bad = ind.copy()
    bad[3] = np.nan
    with pytest.raises(ValueError):
        b.incremental_test(y, bad, base, 50, 10, np.random.default_rng(0))


def test_incremental_test_drops_rows_with_missing_macro():
    idx, base, y, ind, _ = _simulate(n=600)
    base = base.copy()
    base["macro_x"] = np.r_[np.full(30, np.nan), np.arange(570, dtype=float)]
    res = b.incremental_test(y, ind, base, 50, 100, np.random.default_rng(0))
    assert res["n_dropped"] == 30 and res["n"] == 570
