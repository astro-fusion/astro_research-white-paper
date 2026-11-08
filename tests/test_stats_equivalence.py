"""Tests for TOST equivalence and Cohen's kappa with confidence intervals."""

import numpy as np
import pytest
from scipy import stats as sps

from vedic_astrology_core.stats.equivalence import cohen_kappa_ci, tost


def test_tost_inside_the_margin_is_equivalent():
    """An estimate of 0 with SE 0.1 is equivalent within +-0.2 (z = 2)."""
    r = tost(0.0, 0.1, -0.2, 0.2)
    assert r.p_lower == pytest.approx(sps.norm.sf(2.0))
    assert r.p_upper == pytest.approx(sps.norm.sf(2.0))
    assert r.p_value == pytest.approx(0.02275, abs=1e-5)
    assert r.equivalent
    assert r.ci_low == pytest.approx(-0.1 * sps.norm.ppf(0.95))
    assert r.ci_high == pytest.approx(0.1 * sps.norm.ppf(0.95))


def test_tost_near_a_bound_is_not_equivalent():
    """The larger one-sided p-value decides: 0.15 +- 0.1 against 0.2 fails."""
    r = tost(0.15, 0.1, -0.2, 0.2)
    assert r.p_upper == pytest.approx(sps.norm.cdf(-0.5))
    assert r.p_value == r.p_upper
    assert not r.equivalent


def test_tost_matches_statsmodels_ztost():
    """With the sample mean and its standard error TOST equals ztost."""
    from statsmodels.stats.weightstats import ztost

    x = np.random.default_rng(1).normal(0.05, 1.0, 400)
    se = x.std(ddof=1) / np.sqrt(len(x))
    ours = tost(x.mean(), se, -0.2, 0.2)
    p_sm, _, _ = ztost(x, -0.2, 0.2)
    assert ours.p_value == pytest.approx(p_sm, rel=1e-9)


def test_tost_t_distribution_with_df():
    """With df the one-sided tests use Student's t."""
    r = tost(0.0, 0.1, -0.2, 0.2, df=10)
    assert r.p_value == pytest.approx(sps.t.sf(2.0, 10))


@pytest.mark.parametrize("bad", [(0.0, 0.0, -1, 1), (0.0, 1.0, 1, -1)])
def test_tost_rejects_bad_input(bad):
    """A non-positive SE or an empty margin raises."""
    with pytest.raises(ValueError):
        tost(*bad)


def _table(a, b, labels):
    idx = {k: i for i, k in enumerate(labels)}
    t = np.zeros((len(labels), len(labels)))
    for x, y in zip(a, b):
        t[idx[x], idx[y]] += 1
    return t


def test_kappa_perfect_agreement_is_one():
    """Identical ratings give kappa 1."""
    a = list("abcabcabca")
    r = cohen_kappa_ci(a, a)
    assert r.kappa == pytest.approx(1.0)
    assert r.observed_agreement == pytest.approx(1.0)


def test_kappa_and_se_match_statsmodels():
    """Kappa and its asymptotic SE equal statsmodels' cohens_kappa."""
    from statsmodels.stats.inter_rater import cohens_kappa

    rng = np.random.default_rng(7)
    labels = list(range(9))
    a = rng.integers(0, 9, 3000)
    b = np.where(rng.random(3000) < 0.2, a, rng.integers(0, 9, 3000))
    r = cohen_kappa_ci(a, b, labels=labels)
    sm = cohens_kappa(_table(a, b, labels))
    assert r.kappa == pytest.approx(sm.kappa, rel=1e-12)
    assert r.se == pytest.approx(sm.std_kappa, rel=1e-9)
    z = sps.norm.ppf(0.975)
    assert r.ci_low == pytest.approx(r.kappa - z * r.se)
    assert r.ci_high == pytest.approx(r.kappa + z * r.se)
    assert r.method == "analytic"


def test_kappa_independent_raters_is_near_zero():
    """Independent ratings give kappa near 0 with 0 inside the CI."""
    rng = np.random.default_rng(3)
    a = rng.integers(0, 9, 5000)
    b = rng.integers(0, 9, 5000)
    r = cohen_kappa_ci(a, b)
    assert abs(r.kappa) < 0.02
    assert r.ci_low < 0.0 < r.ci_high
    assert r.expected_agreement == pytest.approx(1 / 9, abs=0.01)


def test_kappa_block_bootstrap_is_reproducible_and_wider_for_runs():
    """The block bootstrap is seeded and widens the CI for runs of labels."""
    rng = np.random.default_rng(11)
    a = np.repeat(rng.integers(0, 9, 300), 10)
    b = np.repeat(rng.integers(0, 9, 300), 10)
    r1 = cohen_kappa_ci(a, b, n_boot=500, mean_block=20,
                        rng=np.random.default_rng(42))
    r2 = cohen_kappa_ci(a, b, n_boot=500, mean_block=20,
                        rng=np.random.default_rng(42))
    assert r1.method == "block_bootstrap"
    assert (r1.ci_low, r1.ci_high) == (r2.ci_low, r2.ci_high)
    analytic = cohen_kappa_ci(a, b)
    assert r1.se > analytic.se


def test_kappa_bootstrap_needs_an_rng():
    """A bootstrap without an explicit generator raises."""
    with pytest.raises(ValueError):
        cohen_kappa_ci([1, 2], [1, 2], n_boot=10, mean_block=2)


def test_kappa_rejects_unequal_lengths():
    """The two ratings must pair up."""
    with pytest.raises(ValueError):
        cohen_kappa_ci([1, 2, 3], [1, 2])
