"""Tests for episode-level inference (ADR-004 WP-04, D-6)."""

from itertools import product

import numpy as np
import pandas as pd
import pytest

from vedic_astrology_core.stats.episodes import (
    UNTESTABLE,
    by_rank1_threshold,
    episode_differences,
    episode_labels,
    episode_table,
    episodes,
    sign_flip_p_min,
    sign_flip_test,
    testable,
    wild_cluster_interval,
)
from vedic_astrology_core.stats.multiplicity import benjamini_yekutieli


def _calendar(n, runs):
    x = np.zeros(n, dtype=bool)
    for a, b in runs:
        x[a : b + 1] = True
    return x


# ---------------------------------------------------------------- episodes


def test_runs_without_merge():
    x = _calendar(30, [(2, 4), (7, 7), (10, 12), (25, 29)])
    eps = episodes(x, 0)
    assert [(e.start, e.end) for e in eps] == [(2, 4), (7, 7), (10, 12), (25, 29)]
    assert [e.n_active for e in eps] == [3, 1, 3, 5]


def test_merge_gap_counts_inactive_bars():
    x = _calendar(30, [(2, 4), (7, 7), (10, 12), (25, 29)])
    # gaps are 2 (5..6), 2 (8..9) and 12 (13..24) inactive bars
    assert len(episodes(x, 1)) == 4
    eps = episodes(x, 2)
    assert [(e.start, e.end, e.n_active, e.n_runs) for e in eps] == [
        (2, 12, 7, 3),
        (25, 29, 5, 1),
    ]
    assert eps[0].n_bars == 11
    assert len(episodes(x, 12)) == 1


def test_episode_edges_and_empty():
    assert episodes(np.zeros(5, dtype=bool)) == []
    eps = episodes(np.ones(5, dtype=bool))
    assert [(e.start, e.end) for e in eps] == [(0, 4)]
    eps = episodes([1, 0, 0, 1], 0)
    assert [(e.start, e.end) for e in eps] == [(0, 0), (3, 3)]


def test_labels_and_table():
    idx = pd.date_range("2020-01-01", periods=12, freq="D")
    s = pd.Series(_calendar(12, [(1, 2), (4, 4), (9, 10)]), index=idx)
    labels = episode_labels(s, 1)
    assert labels.tolist() == [-1, 0, 0, -1, 0, -1, -1, -1, -1, 1, 1, -1]
    table = episode_table(s, 1)
    assert table["start"].tolist() == [idx[1], idx[9]]
    assert table["n_bars"].tolist() == [4, 2]
    assert table["n_active"].tolist() == [3, 2]


def test_time_based_merge_gap():
    idx = pd.bdate_range("2021-01-04", periods=40)
    s = pd.Series(_calendar(40, [(0, 4), (10, 14), (35, 39)]), index=idx)
    # run 1 ends Fri 8 Jan, run 2 starts Mon 18 Jan: 10 days apart
    assert len(episodes(s, "9D")) == 3
    assert len(episodes(s, "10D")) == 2
    assert len(episodes(s, pd.Timedelta(days=60))) == 1
    with pytest.raises(ValueError):
        episodes(s.to_numpy(), "10D")


@pytest.mark.parametrize("bad", [-1, 1.5, True])
def test_bad_merge_gap(bad):
    with pytest.raises(ValueError):
        episodes([True, False, True], bad)


def test_bad_indicator():
    with pytest.raises(ValueError):
        episodes([0.0, np.nan, 1.0])
    with pytest.raises(ValueError):
        episodes([0, 2, 1])


# ------------------------------------------------------------- testability


def test_by_rank1_threshold_matches_multiplicity():
    m = 14
    t = by_rank1_threshold(m, 0.05)
    p = np.full(m, 0.9)
    p[0] = t * 0.999
    assert benjamini_yekutieli(p)[0] < 0.05
    p[0] = t * 1.001
    assert benjamini_yekutieli(p)[0] > 0.05


def test_testable_requires_enough_episodes():
    n = 4000
    runs = [(100 + 400 * i, 140 + 400 * i) for i in range(8)]
    x = _calendar(n, runs)
    res = testable(x, merge_gap=5, family_size=14, min_shift=400)
    assert res.testable and res.label == "testable" and res.n_episodes == 8
    # 3201 admissible shifts -> p_min 1/3202 < 0.05/(14*H_14)
    assert res.p_min == pytest.approx(1 / 3202)
    few = testable(_calendar(n, runs[:7]), merge_gap=5, family_size=14, min_shift=400)
    assert not few.testable and few.label == UNTESTABLE
    assert "fewer than 8" in few.reasons[0]


def test_testable_requires_attainable_p():
    n = 1000
    runs = [(20 + 60 * i, 30 + 60 * i) for i in range(12)]
    x = _calendar(n, runs)
    # min_shift 400 leaves 201 shifts: p_min 1/202 is above the BY rank-1
    # threshold of a family of 42
    res = testable(x, merge_gap=0, family_size=42, min_shift=400)
    assert res.n_episodes == 12
    assert not res.testable
    assert any("not below the rank-1 BY" in r for r in res.reasons)
    assert testable(x, merge_gap=0, family_size=1, min_shift=400).testable


def test_testable_sign_flip_floor():
    assert sign_flip_p_min(8, "two-sided") == pytest.approx(2 / 256)
    assert sign_flip_p_min(8, "greater") == pytest.approx(1 / 256)
    assert sign_flip_p_min(25, "two-sided", 9999) == pytest.approx(1e-4)
    x = _calendar(2000, [(10 + 100 * i, 20 + 100 * i) for i in range(10)])
    # 2 / 1024 is below 0.05 / (1 * 1) but above the threshold for 14 tests
    assert testable(x, merge_gap=0, family_size=1, test="sign_flip").testable
    assert not testable(x, merge_gap=0, family_size=14, test="sign_flip").testable
    with pytest.raises(ValueError):
        testable(x, merge_gap=0, family_size=14)  # shift test without min_shift


def test_testable_reads_no_outcome():
    import inspect

    params = inspect.signature(testable).parameters
    assert not {"outcome", "y", "returns"} & set(params)


def _jupiter_capricorn_explore():
    """Jupiter in sidereal (Lahiri) Capricorn, gold explore period.

    Business days 2000-09-05 to 2015-12-31 sampled at 15:00 UTC, as the
    review recomputed it (two runs, 2008-12 to 2009-04 and 2009-07 to
    2009-12, one transit).
    """
    from vedic_astrology_core.markets.features import indicator_frame

    idx = pd.bdate_range("2000-09-05", "2015-12-31", tz="UTC") + pd.Timedelta(hours=15)
    frame = indicator_frame(idx, ["JUPITER"])
    return frame["JUPITER_sign"].eq("Capricorn")


def test_jupiter_in_capricorn_explore_is_one_episode_and_untestable():
    cal = _jupiter_capricorn_explore()
    runs = episodes(cal, 0)
    assert len(runs) == 2
    assert runs[0].start_label.year == 2008 and runs[1].end_label.year == 2009
    one = episodes(cal, 126)  # about half a year of bars merges the loop
    assert len(one) == 1
    assert len(episodes(cal, "180D")) == 1
    res = testable(cal, merge_gap=126, family_size=14, min_shift=400)
    assert res.n_episodes == 1
    assert not res.testable and res.label == UNTESTABLE


def test_jupiter_in_capricorn_review_calendar():
    # The review's dates on a business-day calendar, independent of the engine
    idx = pd.bdate_range("2000-09-05", "2015-12-31")
    on = ((idx >= "2008-12-09") & (idx < "2009-05-01")) | (
        (idx >= "2009-07-30") & (idx < "2009-12-21")
    )
    cal = pd.Series(on, index=idx)
    assert len(episodes(cal, 0)) == 2
    res = testable(cal, merge_gap="180D", family_size=14, min_shift=400)
    assert res.n_episodes == 1 and res.label == UNTESTABLE


# ----------------------------------------------------- episode differences


def test_episode_differences_windows():
    n = 40
    x = _calendar(n, [(10, 12), (14, 15), (30, 31)])
    y = np.zeros(n)
    y[10:16] = 5.0
    y[13] = 100.0  # inside the merged gap: neither active nor a neighbour
    y[7:10] = 1.0
    y[16:19] = 3.0
    table = episode_differences(x, y, merge_gap=1, window=3)
    assert len(table) == 2
    first = table.iloc[0]
    assert first["n_active_used"] == 5
    assert first["active_mean"] == pytest.approx(5.0)
    assert first["neighbour_mean"] == pytest.approx(2.0)
    assert first["difference"] == pytest.approx(3.0)
    second = table.iloc[1]
    # window 3 each side of 30..31: 27..29 and 32..34, all zero
    assert second["n_neighbours"] == 6 and second["difference"] == pytest.approx(0.0)


def test_episode_differences_exclude_other_episodes_and_nan():
    n = 20
    x = _calendar(n, [(5, 6), (9, 10)])
    y = np.arange(n, dtype=float)
    y[4] = np.nan
    table = episode_differences(x, y, merge_gap=0, window=3)
    first = table.iloc[0]
    # before: 2, 3 (4 is NaN); after: 7, 8 (9 is the next episode)
    assert first["n_neighbours"] == 4
    assert first["neighbour_mean"] == pytest.approx((2 + 3 + 7 + 8) / 4)
    unusable = episode_differences(x, y, merge_gap=0, window=3, min_neighbours=6)
    assert not unusable["used"].any() and unusable["difference"].isna().all()


def test_episode_differences_length_check():
    with pytest.raises(ValueError):
        episode_differences([True, False], [1.0], merge_gap=0)


# --------------------------------------------------------------- sign flip


def _brute_p(d, alternative):
    d = np.asarray(d, float)
    obs = d.mean()
    stats = np.array([np.dot(s, d) / len(d) for s in product([1, -1], repeat=len(d))])
    if alternative == "greater":
        return np.mean(stats >= obs - 1e-12)
    if alternative == "less":
        return np.mean(stats <= obs + 1e-12)
    return np.mean(np.abs(stats) >= abs(obs) - 1e-12)


@pytest.mark.parametrize("alternative", ["greater", "less", "two-sided"])
def test_sign_flip_matches_brute_force(alternative):
    rng = np.random.default_rng(1)
    d = rng.normal(0.4, 1.0, size=9)
    res = sign_flip_test(d, alternative=alternative)
    assert res.exact_enumeration and res.n_null == 2**9
    assert res.p_value == pytest.approx(_brute_p(d, alternative))
    assert res.p_value >= res.p_min


def test_sign_flip_floor_and_ties():
    d = np.ones(8)
    assert sign_flip_test(d, alternative="greater").p_value == pytest.approx(1 / 256)
    assert sign_flip_test(d).p_value == pytest.approx(2 / 256)
    assert sign_flip_test(np.zeros(5)).p_value == pytest.approx(1.0)


def test_sign_flip_drops_nan_and_monte_carlo():
    rng = np.random.default_rng(2)
    d = np.append(rng.normal(size=24), np.nan)
    res = sign_flip_test(d, rng=np.random.default_rng(3), n_draws=4999)
    assert res.n_episodes == 24 and not res.exact_enumeration
    assert res.n_null == 4999
    assert res.p_min == pytest.approx(1 / 5000)
    with pytest.raises(ValueError):
        sign_flip_test(rng.normal(size=24))  # Monte Carlo needs an rng


def test_sign_flip_size_under_skewed_episode_null():
    # Symmetric but heavy-tailed, unequal-variance episodes: size <= alpha
    rng = np.random.default_rng(4)
    rejections = 0
    reps = 400
    for _ in range(reps):
        scale = rng.uniform(0.2, 3.0, size=10)
        d = rng.standard_t(3, size=10) * scale
        rejections += sign_flip_test(d).p_value <= 0.05
    se = np.sqrt(0.05 * 0.95 / reps)
    assert rejections / reps <= 0.05 + 3 * se


def test_sign_flip_power():
    d = np.random.default_rng(5).normal(1.5, 1.0, size=12)
    assert sign_flip_test(d, alternative="greater").p_value < 0.01


# -------------------------------------------------- wild cluster interval


def _brute_interval(d, level):
    d = np.asarray(d, float)
    k = len(d)
    means = sorted(
        np.mean(d[list(s)])
        for r in range(1, k + 1)
        for s in __import__("itertools").combinations(range(k), r)
    )
    j = int(np.floor((1 - level) / 2 * 2**k + 1e-9))
    return means[j - 1], means[len(means) - j]


def test_interval_matches_subset_means_and_inversion():
    rng = np.random.default_rng(6)
    d = rng.normal(0.3, 1.0, size=8)
    ci = wild_cluster_interval(d, level=0.9)
    lo, hi = _brute_interval(d, 0.9)
    assert ci.bounded and ci.exact_enumeration
    assert (ci.ci_low, ci.ci_high) == pytest.approx((lo, hi))
    assert ci.ci_low <= d.mean() <= ci.ci_high
    # inversion: just inside a bound the one-sided test does not reject at 5%
    eps = 1e-9
    assert sign_flip_test(d - (ci.ci_low + eps), alternative="greater").p_value > 0.05
    assert sign_flip_test(d - (ci.ci_low - eps), alternative="greater").p_value <= 0.05
    assert sign_flip_test(d - (ci.ci_high - eps), alternative="less").p_value > 0.05
    assert sign_flip_test(d - (ci.ci_high + eps), alternative="less").p_value <= 0.05


def test_interval_unbounded_with_few_episodes():
    # 5 episodes: 2**5 = 32 patterns, 0.025 * 32 < 1
    ci = wild_cluster_interval([0.1, 0.5, -0.2, 0.3, 0.9], level=0.95)
    assert not ci.bounded
    assert ci.ci_low == -np.inf and ci.ci_high == np.inf
    ci = wild_cluster_interval([1.0], level=0.95)
    assert not ci.bounded


def test_interval_coverage_few_clusters():
    rng = np.random.default_rng(7)
    reps, k, mu = 300, 8, 0.7
    covered = 0
    for _ in range(reps):
        d = mu + rng.standard_t(3, size=k) * rng.uniform(0.3, 3.0, size=k)
        ci = wild_cluster_interval(d, level=0.95)
        covered += ci.ci_low <= mu <= ci.ci_high
    assert covered / reps >= 0.92


def test_interval_monte_carlo():
    d = np.random.default_rng(8).normal(0.2, 1.0, size=30)
    ci = wild_cluster_interval(d, rng=np.random.default_rng(9), n_draws=19999)
    assert ci.bounded and not ci.exact_enumeration and ci.n_patterns == 20000
    assert ci.ci_low < d.mean() < ci.ci_high
    with pytest.raises(ValueError):
        wild_cluster_interval(d)


def test_end_to_end_on_bar_level_series():
    rng = np.random.default_rng(10)
    n = 3000
    runs = [(50 + 300 * i, 110 + 300 * i) for i in range(10)]
    x = _calendar(n, runs)
    y = rng.normal(size=n) + 0.8 * x
    gate = testable(x, merge_gap=5, family_size=1, min_shift=400)
    assert gate.testable
    table = episode_differences(x, y, merge_gap=5, window=60)
    res = sign_flip_test(table["difference"], alternative="greater")
    assert res.n_episodes == 10 and res.p_value == pytest.approx(1 / 1024)
    ci = wild_cluster_interval(table["difference"], level=0.9)
    assert ci.ci_low > 0.3
