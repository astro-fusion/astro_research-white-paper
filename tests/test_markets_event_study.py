"""markets.event_study: predictive windows, bootstrap bands, rate ratios."""

import numpy as np
import pandas as pd
import pytest

from vedic_astrology_core.markets import event_study as es

FIX = "tests/fixtures/markets/yahoo_gold_GCF_2015_2020.csv"


def test_forward_window_starts_at_the_event_bar():
    """Check forward window starts at the event bar."""
    prices = pd.DataFrame({"close": np.exp(np.arange(10.0) * 0.01)})
    out = es.event_study(prices, [2, 5], horizons=(1, 3), n_boot=50,
                         rng=np.random.default_rng(0))
    assert out["mean"].tolist() == pytest.approx([0.01, 0.03])
    assert out["n_events"].tolist() == [2, 2]


def test_events_without_full_window_are_dropped_from_that_horizon():
    """Check events without full window are dropped from that horizon."""
    prices = pd.DataFrame({"close": np.exp(np.arange(10.0))})
    out = es.event_study(prices, [1, 8], horizons=(1, 5), n_boot=20,
                         rng=np.random.default_rng(0))
    assert out["n_events"].tolist() == [2, 1]


def test_bands_are_reproducible_and_bracket_random_dates():
    """Check bands are reproducible and bracket random dates."""
    prices = pd.read_csv(FIX)
    bars = np.arange(30, 1400, 37)
    a = es.event_study(prices, bars, rng=np.random.default_rng(42), n_boot=300)
    b = es.event_study(prices, bars, rng=np.random.default_rng(42), n_boot=300)
    pd.testing.assert_frame_equal(a, b)
    assert (a["null_lo"] < a["null_hi"]).all()
    assert ((a["p_value"] > 0) & (a["p_value"] <= 1)).all()
    with pytest.raises(TypeError):
        es.event_study(prices, bars)


def test_event_profile_is_zero_at_offset_zero():
    """Check event profile is zero at offset zero."""
    prices = pd.read_csv(FIX)
    prof = es.event_profile(prices, [100, 500, 900], pre=5, post=10)
    assert prof.loc[prof["offset"] == 0, "mean_cum_return"].item() == 0.0
    assert prof["n_events"].iloc[0] == 3 and len(prof) == 16


def test_rate_during_vs_outside_counts_bars():
    """Check rate during vs outside counts bars."""
    ind = np.array([True] * 10 + [False] * 30)
    flags = np.zeros(40, dtype=bool)
    flags[[1, 2, 15, 30]] = True
    out = es.rate_during_vs_outside(flags, ind)
    counts = (out["n_in"], out["bars_in"], out["n_out"], out["bars_out"])
    assert counts == (2, 10, 2, 30)
    assert out["rate_ratio"] == pytest.approx((2 / 10) / (2 / 30))
    shifted = es.rate_during_vs_outside(flags, ind, rng=np.random.default_rng(1),
                                        min_shift=10, n_draws=200)
    assert 0 < shifted["p_shift"] <= 1
