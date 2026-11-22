"""Calibration suite: each test keeps its stated false-alarm rate with no true effect.

ADR-004 WP-02 (review item 5; flaws M1, M3, M11). Outcomes come from
``tests/simulators.py`` (GARCH(1,1)-t, two-state volatility regimes, long-memory
log-volatility, drift) and indicators are real calendars from the ephemeris,
so a test that only works on kind data fails here.

Every rate is checked against ``nominal + 3 binomial standard errors`` for the
number of simulated runs. Each check runs twice: a seeded fast subset (the
whole fast subset takes under five minutes) and a full run marked ``slow``
(``pytest -m slow tests/test_stats_calibration.py``).

Two cases are pinned as strict expected failures, so they turn red the day
they start to pass and the mark must be removed on purpose:

* the raw-outcome shift test with a one-episode indicator under regime shifts
  (M1; this is why D-6 makes such indicators "untestable");
* SPA size under drift against a flat benchmark (M3; removed by WP-09).

A third pin was found by this suite (not named in ADR-004): the shift test
with a 400-bar minimum shift is anti-conservative for the Saturn and Jupiter
retrograde calendars (about ten episodes of 100 to 140 bars, recurring about
once a year), even when the outcome is i.i.d. Gaussian. Excluding offsets
below the minimum shift removes part of the rotation group, so the observed
alignment is no longer exchangeable with the offsets used. For the other
twelve indicators the excess is small (about 0.053 at nominal 0.05) and
inside the tolerance.
"""

import zlib

import numpy as np
import pandas as pd
import pytest

from tests import simulators as S
from vedic_astrology_core.stats import multiplicity, permutation

ALPHA = 0.05
MIN_SHIFT = 400  # bars; the gold and silver plans' minimum shift
MEAN_BLOCK = 20  # bars; the plans' bootstrap block length
FAMILY = 42  # 14 indicators x 3 targets, the gold family
SHORT = ("2000-01-03", "2009-12-31")  # 2,609 business days
LONG = ("2000-01-03", "2024-12-31")  # 6,522 business days
# Series are cut to their last N_SHORT or N_LONG bars (5-smooth lengths, so the
# FFT is fast) after the 300-bar warm-up of the standardised outcomes.
N_SHORT = 2304
N_LONG = 6144
TARGET_KINDS = ("z", "abs_z", "extreme_z")
YEARLY_RETROGRADES = ("saturn_retrograde", "jupiter_retrograde")
CALIBRATED = tuple(i for i in S.MANY_EPISODE_INDICATORS if i not in YEARLY_RETROGRADES)


def reps(fast: int, full: int):
    """Parametrise a check with a fast run and a slow full run."""
    return pytest.mark.parametrize(
        "n_runs",
        [
            pytest.param(fast, id="fast"),
            pytest.param(full, marks=pytest.mark.slow, id="full"),
        ],
    )


def seed(*parts) -> int:
    return zlib.crc32("|".join(map(str, parts)).encode())


def upper_bound(rate: float, n_runs: int) -> float:
    """Nominal rate plus three binomial standard errors."""
    return rate + 3.0 * np.sqrt(rate * (1.0 - rate) / n_runs)


def diff_means(x, y) -> float:
    """The plans' statistic: mean outcome when active minus when inactive."""
    x = np.asarray(x, dtype=bool)
    return float(np.mean(y[x]) - np.mean(y[~x]))


def lagged(mask) -> np.ndarray:
    """Indicator state on bar t-1 against the outcome on bar t."""
    m = np.asarray(mask, dtype=bool)
    return np.concatenate([[False], m[:-1]])


def outcomes(r, kind: str) -> np.ndarray:
    """Outcome series of one kind from simulated returns (NaN where undefined)."""
    if kind == "raw_abs":
        return np.abs(r)
    if kind == "ret":
        return np.asarray(r, dtype=float)
    z = S.ewma_standardise(r)
    if kind == "z":
        return z
    if kind == "abs_z":
        return np.abs(z)
    if kind == "extreme_z":
        return S.past_quantile_flag(np.abs(z))
    raise ValueError(kind)


def shift_test(x, y, n_boot: int, rng) -> permutation.PermutationResult:
    """The plans' test: two-sided circular shift, every admissible offset."""
    return permutation.permutation_test(
        diff_means,
        x,
        y,
        rng=rng,
        null="circular_shift",
        n_perm=10**6,  # above the admissible count, so enumeration is exact
        alternative="two-sided",
        min_shift=MIN_SHIFT,
        mean_block=MEAN_BLOCK,
        n_boot=n_boot,
    )


def fft_shift_pvalues(X: np.ndarray, Y: np.ndarray, min_shift: int) -> np.ndarray:
    """Exact two-sided shift-test p-values for every (indicator, outcome) pair.

    Same null and p-value as :func:`shift_test` (checked below), computed for
    every offset at once by circular cross-correlation. ``X`` is (n, K)
    binary, ``Y`` is (n, J); returns shape (K, J).
    """
    X = np.asarray(X, dtype=float)
    Y = np.asarray(Y, dtype=float)
    n = X.shape[0]
    k = X.sum(axis=0)
    fx = np.conj(np.fft.rfft(X, axis=0))[:, :, None]
    fy = np.fft.rfft(Y, axis=0)[:, None, :]
    c = np.fft.irfft(fx * fy, n=n, axis=0)  # c[s] = sum_t x[t - s] y[t]
    stats = (
        c * (1.0 / k + 1.0 / (n - k))[None, :, None]
        - Y.sum(axis=0)[None, None, :] / (n - k)[None, :, None]
    )
    obs, null = stats[0], stats[min_shift : n - min_shift + 1]
    centre = null.mean(axis=0)
    tol = 1e-9 * np.abs(null).max(axis=0)
    n_ext = (np.abs(null - centre) >= np.abs(obs - centre) - tol).sum(axis=0)
    return (n_ext + 1) / (null.shape[0] + 1)


def standardised_targets(r, n_keep: int) -> np.ndarray:
    """The last ``n_keep`` bars of the three standardised targets, shape (n_keep, 3)."""
    Y = np.column_stack([outcomes(r, k)[-n_keep:] for k in TARGET_KINDS])
    assert not np.isnan(Y).any()
    return Y


_SIZE_TABLES = {}


def size_table(calendar: pd.DataFrame, n_runs: int) -> pd.DataFrame:
    """Rejection rate at 0.05 of the exact shift test, per indicator and target.

    One simulated return series per run feeds every (indicator, target) pair,
    as in a study. Cached per run count.
    """
    if n_runs not in _SIZE_TABLES:
        names = list(S.MANY_EPISODE_INDICATORS)
        X = np.column_stack([lagged(calendar[c])[-N_SHORT:] for c in names])
        rng = np.random.default_rng(seed("size-table", n_runs))
        rejections = np.zeros((len(names), len(TARGET_KINDS)))
        for _ in range(n_runs):
            r = S.hard_returns(len(calendar), rng)["ret"]
            p = fft_shift_pvalues(X, standardised_targets(r, N_SHORT), MIN_SHIFT)
            rejections += p <= ALPHA
        _SIZE_TABLES[n_runs] = pd.DataFrame(
            rejections / n_runs, index=names, columns=list(TARGET_KINDS)
        )
    return _SIZE_TABLES[n_runs]


@pytest.fixture(scope="module")
def short_calendar() -> pd.DataFrame:
    return S.ephemeris_calendar(*SHORT)


@pytest.fixture(scope="module")
def long_calendar() -> pd.DataFrame:
    return S.ephemeris_calendar(*LONG)


# ----------------------------------------------------- the simulator is hard
def test_simulated_returns_are_not_kind():
    """Heavy tails, clustering, persistent regimes and slow-decaying memory."""
    rng = np.random.default_rng(seed("realism"))
    sim = S.hard_returns(6500, rng)
    r, a = sim["ret"], np.abs(sim["ret"])

    def acf(v, lag):
        v = v - v.mean()
        return float(np.dot(v[:-lag], v[lag:]) / np.dot(v, v))

    kurt = float(np.mean((r - r.mean()) ** 4) / np.var(r) ** 2)
    assert kurt > 5.0
    assert acf(a, 1) > 0.1
    assert acf(a, 100) > 0.04  # memory months out: regimes and long memory
    assert abs(acf(r, 1)) < 0.05  # returns themselves are not predictable
    switches = int(np.sum(sim["state"][1:] != sim["state"][:-1]))
    assert 3 <= switches <= 60  # a handful of long regimes, not noise
    assert 0.007 < r.std() < 0.014
    drifted = S.hard_returns(20000, np.random.default_rng(1), drift=4.8e-4)["ret"]
    assert abs(drifted.mean() - 4.8e-4) < 2.5e-4


def test_standardisation_is_past_only():
    rng = np.random.default_rng(seed("past-only"))
    r = S.hard_returns(1000, rng)["ret"]
    z = S.ewma_standardise(r)
    changed = r.copy()
    changed[600:] *= 5.0
    z2 = S.ewma_standardise(changed)
    np.testing.assert_array_equal(z[:600], z2[:600])
    assert z2[600] == pytest.approx(5.0 * z[600])  # bar t uses r_t over sigma_{t|t-1}
    assert np.isnan(z[:50]).all() and not np.isnan(z[50:]).any()
    flag = S.past_quantile_flag(np.abs(z))
    a2 = np.abs(z).copy()
    a2[700:] = 0.0
    np.testing.assert_array_equal(flag[:700], S.past_quantile_flag(a2)[:700])


def test_real_calendars_have_the_stated_episode_counts(short_calendar, long_calendar):
    for cal in (short_calendar, long_calendar):
        for name in S.MANY_EPISODE_INDICATORS:
            assert S.n_episodes(cal[name]) >= 8, name
    # One transit in the short window: the M1 case.
    assert S.n_episodes(short_calendar["jupiter_exalted"]) == 1
    assert S.n_episodes(np.array([0, 1, 1, 0, 1, 0, 0, 1], dtype=bool)) == 3


def test_fft_shift_pvalues_match_permutation_test(short_calendar):
    rng = np.random.default_rng(seed("fft"))
    r = S.hard_returns(len(short_calendar), rng)["ret"]
    Y = standardised_targets(r, N_SHORT)
    names = ["mercury_retrograde", "saturn_retrograde", "purnima"]
    X = np.column_stack([lagged(short_calendar[c])[-N_SHORT:] for c in names])
    fast = fft_shift_pvalues(X, Y, MIN_SHIFT)
    for i in range(len(names)):
        for j in range(len(TARGET_KINDS)):
            res = shift_test(X[:, i], Y[:, j], 0, rng)
            assert res.exact_enumeration
            assert abs(fast[i, j] - res.p_value) <= 2.0 / (res.n_perm + 1)


# -------------------------------------------------------------------- size
@reps(fast=1000, full=3000)
@pytest.mark.parametrize("indicator", CALIBRATED)
def test_exact_shift_test_holds_size_on_standardised_outcomes(
    short_calendar, indicator, n_runs
):
    """At least 8 episodes, past-only standardised outcomes: size <= 0.05 + 3 SE.

    The rate is pooled over the three targets (z, |z|, extreme |z|), which
    share each simulated series; the bound uses the single-target standard
    error, which is the larger one.
    """
    assert S.n_episodes(short_calendar[indicator]) >= 8
    rates = size_table(short_calendar, n_runs).loc[indicator]
    assert rates.mean() <= upper_bound(ALPHA, n_runs), rates.to_dict()


@pytest.mark.parametrize(
    "indicator,kind", [("mercury_retrograde", "abs_z"), ("sun_own_sign", "z")]
)
def test_permutation_test_itself_holds_size(short_calendar, indicator, kind):
    """The library call the studies make, not the FFT shortcut (fast run only).

    The large-sample size check is the FFT table above, whose p-values equal
    the library's (see test_fft_shift_pvalues_match_permutation_test).
    """
    n_runs = 300
    rng = np.random.default_rng(seed("size-lib", indicator, kind, n_runs))
    x = lagged(short_calendar[indicator])[-N_SHORT:]
    rejections = 0
    for _ in range(n_runs):
        y = outcomes(S.hard_returns(len(short_calendar), rng)["ret"], kind)[-N_SHORT:]
        res = shift_test(x, y, 0, rng)
        assert res.exact_enumeration
        rejections += res.p_value <= ALPHA
    assert rejections / n_runs <= upper_bound(ALPHA, n_runs)


@pytest.mark.xfail(
    strict=True,
    reason=(
        "found by WP-02: with min_shift 400 the circular-shift null omits part "
        "of the rotation group, and for yearly retrograde calendars (about 10 "
        "episodes of 100-140 bars) the test rejects about 6 (Jupiter) to 7.5 "
        "(Saturn) percent at nominal 5 even for i.i.d. outcomes; needs the "
        "episode-level test (WP-04) or a full-group rotation null"
    ),
)
@pytest.mark.parametrize("indicator", YEARLY_RETROGRADES)
def test_shift_test_size_with_yearly_retrograde_calendars(short_calendar, indicator):
    n_runs = 20000
    rng = np.random.default_rng(seed("yearly", indicator, n_runs))
    X = lagged(short_calendar[indicator])[-N_SHORT:, None]
    rejections = np.zeros(3)
    for _ in range(n_runs):
        Y = rng.standard_normal((N_SHORT, 3))  # the kindest outcome there is
        rejections += fft_shift_pvalues(X, Y, MIN_SHIFT)[0] <= ALPHA
    assert (rejections / n_runs).max() <= upper_bound(ALPHA, n_runs)


@pytest.mark.xfail(
    strict=True,
    reason=(
        "M1: a circular shift of a one-episode indicator against a raw "
        "volatility outcome tests 'is this year different', which regime "
        "shifts make true; D-6 reports such indicators as untestable"
    ),
)
def test_raw_outcome_shift_test_with_one_episode_under_regimes(short_calendar):
    n_runs = 200
    rng = np.random.default_rng(seed("m1", n_runs))
    x_all = lagged(short_calendar["jupiter_exalted"])
    rejections = 0
    for _ in range(n_runs):
        y = outcomes(S.hard_returns(len(x_all), rng)["ret"], "raw_abs")
        x, yy = x_all[1:], y[1:]
        rejections += shift_test(x, yy, 0, rng).p_value <= ALPHA
    assert rejections / n_runs <= upper_bound(ALPHA, n_runs)


# ---------------------------------------------------------------- coverage
@pytest.mark.parametrize(
    "indicator,kind,n_runs",
    [
        pytest.param("mercury_retrograde", "ret", 400, id="mercury-ret-fast"),
        pytest.param("saturn_retrograde", "ret", 400, id="saturn-ret-fast"),
        pytest.param(
            "mercury_retrograde",
            "ret",
            2000,
            marks=pytest.mark.slow,
            id="mercury-ret-full",
        ),
        pytest.param(
            "saturn_retrograde",
            "ret",
            2000,
            marks=pytest.mark.slow,
            id="saturn-ret-full",
        ),
        pytest.param(
            "sun_exalted", "ret", 2000, marks=pytest.mark.slow, id="sun-ret-full"
        ),
        pytest.param(
            "mercury_retrograde",
            "abs_z",
            2000,
            marks=pytest.mark.slow,
            id="mercury-absz-full",
        ),
    ],
)
def test_bootstrap_interval_covers_the_true_difference(
    short_calendar, indicator, kind, n_runs
):
    """The 95 percent block-bootstrap interval covers 0 in at least 92 percent of runs."""
    rng = np.random.default_rng(seed("coverage", indicator, kind, n_runs))
    x_all = lagged(short_calendar[indicator])
    covered = 0
    for _ in range(n_runs):
        y = outcomes(S.hard_returns(len(x_all), rng)["ret"], kind)
        keep = ~np.isnan(y)
        keep[0] = False
        res = permutation.permutation_test(
            diff_means,
            x_all[keep],
            y[keep],
            rng=rng,
            null="circular_shift",
            n_perm=1,  # the interval is what is checked here
            alternative="two-sided",
            min_shift=MIN_SHIFT,
            mean_block=MEAN_BLOCK,
            ci_level=0.95,
            n_boot=999,
        )
        # No effect: the true difference of means is 0 for an outcome whose
        # law does not depend on a fixed calendar.
        covered += res.ci_low <= 0.0 <= res.ci_high
    assert covered / n_runs >= 0.92


# ---------------------------------------------------------------------- BY
def _gaussian_fdr(n_runs: int, scenario: str, rng) -> tuple:
    """FDR of BY at 0.05 over ``n_runs`` families of 42 dependent tests."""
    m = FAMILY
    if scenario == "all_null_equicorrelated":
        n_alt, rho = 0, 0.6
        L = np.linalg.cholesky(np.full((m, m), rho) + (1 - rho) * np.eye(m))
        mix = lambda g: L @ g  # noqa: E731
        sided = "two"
    elif scenario == "mixed_positive_blocks":
        n_alt = 10
        blocks = np.kron(np.eye(7), np.full((6, 6), 0.8)) + 0.2 * np.eye(m)
        L = np.linalg.cholesky(blocks)
        mix = lambda g: L @ g  # noqa: E731
        sided = "two"
    elif scenario == "mixed_negative_pairs":
        # One-sided tests in negatively correlated pairs: the dependence
        # under which Benjamini-Hochberg is not guaranteed and BY is.
        n_alt = 10

        def mix(g):
            z = g.copy()
            z[1::2] = -0.8 * g[0::2] + 0.6 * g[1::2]
            return z

        sided = "one"
    else:
        raise ValueError(scenario)
    shift = np.zeros(m)
    shift[:n_alt] = 3.0
    from scipy.stats import norm

    fdp = np.empty(n_runs)
    for i in range(n_runs):
        z = mix(rng.standard_normal(m)) + shift
        p = 2 * norm.sf(np.abs(z)) if sided == "two" else norm.sf(z)
        rejected = multiplicity.adjust(p, "by") < ALPHA
        false = int(rejected[n_alt:].sum())
        fdp[i] = false / max(int(rejected.sum()), 1)
    return float(fdp.mean()), float(fdp.std(ddof=1) / np.sqrt(n_runs))


@reps(fast=20000, full=200000)
@pytest.mark.parametrize(
    "scenario",
    ["all_null_equicorrelated", "mixed_positive_blocks", "mixed_negative_pairs"],
)
def test_by_controls_fdr_for_a_family_of_42_under_dependence(scenario, n_runs):
    rng = np.random.default_rng(seed("by-gauss", scenario, n_runs))
    fdr, se = _gaussian_fdr(n_runs, scenario, rng)
    assert fdr <= ALPHA + 3.0 * se


@reps(fast=300, full=2000)
def test_by_on_shift_tests_of_the_gold_family(long_calendar, n_runs):
    """14 real calendars x 3 standardised targets, no effect: P(any BY discovery)."""
    names = list(S.MANY_EPISODE_INDICATORS)
    assert len(names) * 3 == FAMILY
    rng = np.random.default_rng(seed("by-shift", n_runs))
    X = np.column_stack([lagged(long_calendar[c])[-N_LONG:] for c in names])
    n = X.shape[0]
    # Not vacuous: the attainable minimum p is below BY's rank-1 threshold.
    harmonic = float(np.sum(1.0 / np.arange(1, FAMILY + 1)))
    assert 1.0 / (n - 2 * MIN_SHIFT + 2) < ALPHA / (FAMILY * harmonic)
    any_discovery = 0
    for _ in range(n_runs):
        r = S.hard_returns(len(long_calendar), rng)["ret"]
        p = fft_shift_pvalues(X, standardised_targets(r, N_LONG), MIN_SHIFT).ravel()
        any_discovery += bool((multiplicity.adjust(p, "by") < ALPHA).any())
    # With every hypothesis null, FDR equals the chance of any discovery.
    assert any_discovery / n_runs <= upper_bound(ALPHA, n_runs)


# --------------------------------------------------------------------- SPA
@pytest.mark.xfail(
    strict=True,
    reason=(
        "M3: against a flat benchmark any long rule earns drift times duty "
        "cycle, so SPA rejects with no information; fixed by WP-09"
    ),
)
def test_spa_size_under_drift(long_calendar):
    """The study's SPA (directions from explore, flat benchmark) under +4.8 bp/day drift."""
    from vedic_astrology_core.markets import study

    n_runs = 150
    rng = np.random.default_rng(seed("spa", n_runs))
    names = list(S.MANY_EPISODE_INDICATORS)
    indicators = long_calendar[names]
    explore = np.asarray(long_calendar.index < pd.Timestamp("2016-01-01"))
    confirm = ~explore
    rejections = 0
    for _ in range(n_runs):
        r = S.hard_returns(len(long_calendar), rng, drift=4.8e-4)["ret"]
        rows = [
            {
                "indicator": c,
                "target": "ret",
                "testable": True,
                "effect": diff_means(lagged(indicators[c])[explore], r[explore]),
            }
            for c in names
        ]
        res = study.spa(
            indicators,
            pd.DataFrame({"ret": r}),
            explore,
            confirm,
            pd.DataFrame(rows),
            rng,
            {"n_boot": 499, "mean_block_bars": MEAN_BLOCK},
        )
        rejections += res["p_consistent"] <= ALPHA
    assert rejections / n_runs <= upper_bound(ALPHA, n_runs)
