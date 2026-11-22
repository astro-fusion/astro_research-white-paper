"""Tests for the generic permutation test."""

import numpy as np
import pytest

from vedic_astrology_core.stats.nulls import circular_shift_offsets, shift_null_info
from vedic_astrology_core.stats.permutation import (
    empirical_p_value,
    permutation_test,
)
from vedic_astrology_core.stats.rates import rate_ratio_shift_test


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


# ---------------------------------------------------------------- exact null
def _runs(n, mean_run, rng):
    """0/1 series of alternating runs with geometric lengths (mean mean_run)."""
    out = np.empty(n, dtype=int)
    state, i = int(rng.integers(2)), 0
    while i < n:
        length = int(rng.geometric(1.0 / mean_run))
        out[i : i + length] = state
        state, i = 1 - state, i + length
    return out


def _ar_garch(n, rng, phi=0.3, omega=0.05, a=0.1, b=0.85):
    """AR(1) mean with GARCH(1,1) errors: autocorrelated, volatility clusters."""
    y = np.zeros(n)
    h, e_prev = omega / (1 - a - b), 0.0
    for t in range(1, n):
        h = omega + a * e_prev**2 + b * h
        e_prev = np.sqrt(h) * rng.standard_normal()
        y[t] = phi * y[t - 1] + e_prev
    return y


def _diff(x, y):
    on = x.astype(bool)
    return float(y[on].mean() - y[~on].mean())


def test_exact_enumeration_matches_brute_force():
    """Fewer admissible shifts than n_perm: every shift once, p by hand."""
    rng = np.random.default_rng(3)
    n, min_shift = 40, 6
    x = _runs(n, 5, rng)
    y = rng.normal(size=n) + 0.8 * x
    shifts = range(min_shift, n - min_shift + 1)
    brute = np.array([_diff(np.roll(x, k), y) for k in shifts])
    for alt in ("greater", "less", "two-sided"):
        runs = [
            permutation_test(
                _diff,
                x,
                y,
                rng=np.random.default_rng(seed),
                n_perm=10000,
                alternative=alt,
                min_shift=min_shift,
                n_boot=0,
            )
            for seed in (0, 1)
        ]
        res = runs[0]
        np.testing.assert_allclose(res.null_stats, brute)
        assert res.p_value == pytest.approx(empirical_p_value(_diff(x, y), brute, alt))
        assert runs[1].p_value == res.p_value  # deterministic: rng is unused
        assert res.exact_enumeration and res.n_admissible == len(brute)
        assert res.n_perm == len(brute) == n - 2 * min_shift + 1
        assert res.p_min == pytest.approx(1 / (len(brute) + 1))


def test_sampled_shifts_never_repeat():
    """More admissible shifts than n_perm: distinct shifts, none out of range."""
    n, min_shift, n_perm = 1000, 100, 500
    x = np.arange(n)

    def offset(xs, _y):
        return float((n - xs[0]) % n)  # np.roll(arange, k)[0] == n - k

    res = permutation_test(
        offset,
        x,
        np.zeros(n),
        rng=np.random.default_rng(9),
        n_perm=n_perm,
        min_shift=min_shift,
        n_boot=0,
    )
    k = res.null_stats.astype(int)
    assert len(np.unique(k)) == len(k) == n_perm
    assert k.min() >= min_shift and k.max() <= n - min_shift
    assert not res.exact_enumeration and res.n_admissible == n - 2 * min_shift + 1
    assert res.p_min == pytest.approx(1 / (n_perm + 1))
    off = circular_shift_offsets(n, min_shift, n_perm, np.random.default_rng(9))
    assert len(np.unique(off)) == n_perm
    full = circular_shift_offsets(n, min_shift, 10_000, np.random.default_rng(9))
    np.testing.assert_array_equal(full, np.arange(min_shift, n - min_shift + 1))


def test_minimum_p_is_attained_and_reported():
    """A planted effect beyond every shift gets exactly p_min = 1/(M+1)."""
    rng = np.random.default_rng(0)
    n, min_shift = 600, 150
    x = (np.sin(np.arange(n) / 20.0) > 0.6).astype(int)
    y = rng.normal(size=n) * 0.1 + 5.0 * x
    res = permutation_test(
        _diff, x, y, rng=rng, n_perm=10000, min_shift=min_shift, n_boot=0
    )
    m = n - 2 * min_shift + 1
    assert res.exact_enumeration
    assert res.p_min == pytest.approx(1 / (m + 1))
    assert res.p_value == pytest.approx(res.p_min)
    # The gold explore case of the 2026-11-22 review: 2,663 shifts, p >= 1/2664.
    info = shift_null_info(3462, 400, 10000)
    assert info == {
        "n_admissible": 2663,
        "n_shifts": 2663,
        "exact_enumeration": True,
        "p_min": pytest.approx(1 / 2664),
    }
    assert not shift_null_info(3462, 400, 999)["exact_enumeration"]


def test_rate_ratio_shift_test_reports_exact_null():
    """The event-rate shift test uses and records the same exact null."""
    rng = np.random.default_rng(2)
    n, min_shift = 500, 100
    ind = _runs(n, 25, rng).astype(bool)
    events = np.sort(rng.choice(n, 40, replace=False))
    res = rate_ratio_shift_test(events, ind, min_shift, 10000, rng, "greater")
    m = n - 2 * min_shift + 1
    counts = [ind[(events - k) % n].sum() for k in range(min_shift, n - min_shift + 1)]
    assert res.p_value == pytest.approx(
        empirical_p_value(res.exact.n_in, np.array(counts), "greater")
    )
    assert res.exact_enumeration and res.n_draws == m == res.n_admissible
    assert res.p_min == pytest.approx(1 / (m + 1))
    small = rate_ratio_shift_test(events, ind, min_shift, 99, rng, "greater")
    assert not small.exact_enumeration and small.n_draws == 99
    assert small.p_min == pytest.approx(0.01)


@pytest.mark.parametrize(
    "n, min_shift, n_perm, alternative",
    [(400, 40, 10000, "two-sided"), (600, 60, 199, "greater")],
)
def test_size_under_the_null_on_ar_garch(n, min_shift, n_perm, alternative):
    """Indicator independent of an AR-GARCH outcome: rejections at most alpha.

    The first case enumerates all 321 shifts exactly (two-sided, as the market
    studies test); the second samples 199 of 481 shifts without replacement
    (one-sided, as the event studies test). The bound allows two binomial
    standard errors of Monte Carlo noise.

    Runs average 6 steps, so the indicator has many runs. With few long runs
    (say 13 runs of 30 steps in 400) the size of the min_shift-restricted
    test rises to about 0.08 at alpha 0.05 even for i.i.d. outcomes, because
    excluding the shifts near zero breaks the rotation group; the full group
    of shifts keeps it near 0.05.
    """
    alpha, reps = 0.05, 300
    rng = np.random.default_rng(20261122)
    rejections = done = 0
    for _ in range(reps):
        y = _ar_garch(n, rng)
        x = _runs(n, 6, rng)
        if x.sum() < 20 or (1 - x).sum() < 20:
            continue
        res = permutation_test(
            _diff,
            x,
            y,
            rng=rng,
            n_perm=n_perm,
            alternative=alternative,
            min_shift=min_shift,
            n_boot=0,
        )
        assert res.exact_enumeration == (n_perm >= n - 2 * min_shift + 1)
        rejections += res.p_value <= alpha
        done += 1
    assert done > 0.95 * reps
    bound = alpha + 2 * np.sqrt(alpha * (1 - alpha) / done)
    assert rejections / done <= bound
