"""Tests for Bayesian rate-ratio summaries (grid posterior, Savage-Dickey)."""

import numpy as np
import pytest
from scipy import stats as sps

from vedic_astrology_core.stats.bayes import PRIORS, posterior_log_rr, summarise


def test_no_events_returns_the_prior():
    """With no events the posterior is the prior and the Bayes factor is 1."""
    post = posterior_log_rr(0, 10.0, 0, 90.0, prior_sd=0.5)
    assert post.post_mean == pytest.approx(0.0, abs=1e-6)
    assert post.post_sd == pytest.approx(0.5, rel=1e-3)
    assert post.bf10 == pytest.approx(1.0, rel=1e-3)
    assert post.p_rr_gt_1 == pytest.approx(0.5, abs=1e-3)


def test_matches_normal_normal_conjugate_for_large_counts():
    """Large counts: likelihood ~ normal, so the closed form applies."""
    n_in, n_out, t_in, t_out = 2600, 7400, 0.25, 0.75
    m = np.log((n_in / t_in) / (n_out / t_out))
    s2 = 1.0 / n_in + 1.0 / n_out
    tau = 0.1
    v = 1.0 / (1.0 / tau**2 + 1.0 / s2)
    mean = v * m / s2
    post = posterior_log_rr(n_in, t_in, n_out, t_out, prior_sd=tau)
    assert post.post_mean == pytest.approx(mean, abs=2e-3)
    assert post.post_sd == pytest.approx(np.sqrt(v), rel=0.02)
    bf01 = sps.norm.pdf(0, mean, np.sqrt(v)) / sps.norm.pdf(0, 0, tau)
    assert post.bf10 == pytest.approx(1.0 / bf01, rel=0.05)


def test_strong_effect_gives_large_bayes_factor_and_sceptical_shrinks():
    """RR = 3 on 200 events: BF10 large; sceptical prior shrinks harder."""
    sk = posterior_log_rr(75, 0.2, 125, 0.8, prior_sd=0.1)
    en = posterior_log_rr(75, 0.2, 125, 0.8, prior_sd=0.5)
    assert en.bf10 > 100
    assert 0 < sk.post_mean < en.post_mean < np.log(2.4) + 0.05
    assert en.p_rr_gt_1 > 0.999
    assert en.rr_cri_low > 1.0


def test_summarise_reports_both_registered_priors():
    """The summary returns one entry per prior with RR-scale summaries."""
    out = summarise(10, 0.1, 90, 0.9)
    assert set(out) == set(PRIORS)
    assert PRIORS["sceptical"] == 0.1 and PRIORS["enthusiastic"] == 0.5
    for v in out.values():
        assert v["rr_cri_low"] <= v["rr_median"] <= v["rr_cri_high"]
        assert v["bf10"] > 0


def test_rejects_bad_input():
    """Check rejects bad input."""
    with pytest.raises(ValueError):
        posterior_log_rr(1, 0.0, 1, 1.0, prior_sd=0.1)
    with pytest.raises(ValueError):
        posterior_log_rr(1, 1.0, 1, 1.0, prior_sd=0.0)
