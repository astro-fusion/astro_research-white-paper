"""Tests for the simulated minimum detectable rate ratio."""

import numpy as np
import pandas as pd
import pytest
from scipy import stats as sps

from vedic_astrology_core.stats.power import (
    minimum_detectable_difference,
    minimum_detectable_rate_ratio,
    power_at_rate_ratio,
    power_table,
)


def _analytic_mdrr(n, d, alpha, power):
    """Return the normal-approximation MDRR of the one-sided binomial test."""
    za, zb = sps.norm.ppf(1 - alpha), sps.norm.ppf(power)
    p0 = d
    p1 = p0 + (za * np.sqrt(p0 * (1 - p0)) + zb * np.sqrt(p0 * (1 - p0))) / np.sqrt(n)
    return (p1 / (1 - p1)) * (1 - d) / d


def test_known_answer_against_normal_approximation():
    """1000 events, duty 0.5: simulation agrees with the binomial normal approx."""
    mdrr = minimum_detectable_rate_ratio(
        1000, 0.5, 0.05, 0.8, np.random.default_rng(1), n_sim=4000
    )
    assert mdrr == pytest.approx(_analytic_mdrr(1000, 0.5, 0.05, 0.8), rel=0.03)


def test_more_events_detect_smaller_effects():
    """MDRR shrinks as the event count grows and grows as duty falls."""
    rng = np.random.default_rng
    a = minimum_detectable_rate_ratio(100, 0.2, 0.05, 0.8, rng(2), n_sim=2000)
    b = minimum_detectable_rate_ratio(1000, 0.2, 0.05, 0.8, rng(2), n_sim=2000)
    c = minimum_detectable_rate_ratio(1000, 0.02, 0.05, 0.8, rng(2), n_sim=2000)
    assert a > b > 1.0
    assert c > b


def test_power_at_null_is_alpha():
    """At RR = 1 the rejection rate is at most alpha (up to MC error)."""
    pw = power_at_rate_ratio(1.0, 200, 0.3, 0.05, np.random.default_rng(3), 4000)
    assert pw <= 0.05 + 3 * np.sqrt(0.05 * 0.95 / 4000)


def test_two_sided_needs_a_larger_effect():
    """Two-sided tests spend alpha/2 per tail, so the MDRR is larger."""
    rng = np.random.default_rng
    one = minimum_detectable_rate_ratio(300, 0.2, 0.05, 0.8, rng(4), n_sim=2000)
    two = minimum_detectable_rate_ratio(
        300, 0.2, 0.05, 0.8, rng(4), n_sim=2000, two_sided=True
    )
    assert two > one > 1.0


def test_minimum_detectable_difference_from_ci():
    """MDE = (z_{1-a/2} + z_power) * SE, SE from a 95% CI."""
    mde = minimum_detectable_difference(-1.96, 1.96, alpha=0.05, power=0.8)
    assert mde == pytest.approx(1.959964 + 0.841621, rel=1e-4)


def test_power_table_one_row_per_indicator():
    """Check power table one row per indicator."""
    specs = [
        {"id": "a", "n_events": 150, "duty_cycle": 0.1, "direction": "greater"},
        {"id": "b", "n_events": 150, "duty_cycle": 0.5, "direction": "two-sided"},
    ]
    tab = power_table(specs, np.random.default_rng(5), n_sim=1000)
    assert isinstance(tab, pd.DataFrame)
    assert list(tab["id"]) == ["a", "b"]
    assert (tab["mdrr"] > 1).all()
    assert tab.loc[0, "expected_in"] == pytest.approx(15.0)


# --------------------------------------------------------------------------
# WP-08: family alpha, over-dispersion, episodes as n
# --------------------------------------------------------------------------

from vedic_astrology_core.stats.episodes import by_rank1_threshold  # noqa: E402
from vedic_astrology_core.stats.power import (  # noqa: E402
    family_alpha,
    minimum_detectable_episode_effect,
    power_episode_effect,
)


def test_family_alpha_is_the_rank1_by_threshold():
    """BY rank 1 is alpha / (m H_m); Bonferroni and BH rank 1 are alpha / m."""
    assert family_alpha(42) == pytest.approx(by_rank1_threshold(42, 0.05))
    h = sum(1 / i for i in range(1, 27))
    assert family_alpha(26) == pytest.approx(0.05 / (26 * h))
    assert family_alpha(10, method="bonferroni") == pytest.approx(0.005)
    assert family_alpha(10, method="bh") == pytest.approx(0.005)
    assert family_alpha(10, method="none") == pytest.approx(0.05)
    with pytest.raises(ValueError):
        family_alpha(10, method="holm")
    with pytest.raises(ValueError):
        family_alpha(0)


def test_power_table_at_family_alpha_needs_larger_effects():
    """A table at the family's rank-1 BY level reports larger MDRRs."""
    specs = [{"id": "a", "n_events": 150, "duty_cycle": 0.2}]
    plain = power_table(specs, np.random.default_rng(6), n_sim=2000)
    fam = power_table(specs, np.random.default_rng(6), n_sim=2000, family_size=26)
    assert fam.loc[0, "alpha"] == pytest.approx(family_alpha(26))
    assert fam.loc[0, "alpha_family"] == pytest.approx(0.05)
    assert fam.loc[0, "family_size"] == 26
    assert fam.loc[0, "mdrr"] > plain.loc[0, "mdrr"]


def test_overdispersion_none_keeps_the_poisson_answer():
    """Without over-dispersion the result is unchanged (same seed, same value)."""
    a = minimum_detectable_rate_ratio(
        200, 0.2, 0.05, 0.8, np.random.default_rng(8), 2000
    )
    b = minimum_detectable_rate_ratio(
        200, 0.2, 0.05, 0.8, np.random.default_rng(8), 2000, overdispersion=None
    )
    assert a == b


def test_overdispersion_near_one_agrees_with_poisson():
    """Phi just above 1 gives (nearly) the Poisson MDRR."""
    a = minimum_detectable_rate_ratio(
        300, 0.2, 0.05, 0.8, np.random.default_rng(9), 4000
    )
    b = minimum_detectable_rate_ratio(
        300, 0.2, 0.05, 0.8, np.random.default_rng(9), 4000, overdispersion=1.0001
    )
    assert b == pytest.approx(a, rel=0.03)


def test_overdispersed_counts_need_larger_effects():
    """Negative binomial counts (phi = 3) raise the MDRR."""
    rng = np.random.default_rng
    pois = minimum_detectable_rate_ratio(200, 0.2, 0.05, 0.8, rng(10), n_sim=2000)
    nb = minimum_detectable_rate_ratio(
        200, 0.2, 0.05, 0.8, rng(10), n_sim=2000, overdispersion=3.0
    )
    assert nb > pois * 1.1


def test_overdispersed_power_at_null_is_alpha():
    """With phi = 3 the simulated null still rejects at most alpha at RR = 1."""
    pw = power_at_rate_ratio(
        1.0, 200, 0.3, 0.05, np.random.default_rng(11), 4000, overdispersion=3.0
    )
    assert pw <= 0.05 + 3 * np.sqrt(0.05 * 0.95 / 4000)


def test_overdispersion_below_one_raises():
    """Under-dispersion is not a negative binomial; it is refused."""
    with pytest.raises(ValueError):
        minimum_detectable_rate_ratio(
            100, 0.2, 0.05, 0.8, np.random.default_rng(1), 100, overdispersion=0.5
        )


def test_episode_mde_matches_statsmodels_one_sample_t():
    """The episode MDE in SD units equals the one-sample t solve_power answer."""
    from statsmodels.stats.power import TTestPower

    for k, alpha, alt, sm_alt in [
        (12, 0.01, "greater", "larger"),
        (30, 0.05, "two-sided", "two-sided"),
    ]:
        mde = minimum_detectable_episode_effect(2.0, k, alpha, 0.8, alt)
        es = TTestPower().solve_power(
            nobs=k, alpha=alpha, power=0.8, alternative=sm_alt
        )
        assert mde / 2.0 == pytest.approx(es, rel=1e-4)


def test_episode_mde_is_infinite_when_p_is_not_attainable():
    """Eight episodes cannot reach a rank-1 BY threshold of a family of 42."""
    alpha = family_alpha(42)
    assert 2.0**-8 > alpha
    assert minimum_detectable_episode_effect(1.0, 8, alpha) == float("inf")
    assert power_episode_effect(100.0, 1.0, 8, alpha) == 0.0
    assert np.isfinite(minimum_detectable_episode_effect(1.0, 12, alpha))
    assert minimum_detectable_episode_effect(1.0, 1, 0.05) == float("inf")


def test_episodes_not_bars_are_the_n():
    """More episodes detect smaller effects; the MDE scales like 1 / sqrt(K)."""
    small = minimum_detectable_episode_effect(1.0, 10, 0.05)
    large = minimum_detectable_episode_effect(1.0, 40, 0.05)
    assert large < small
    assert large == pytest.approx(small * np.sqrt(10 / 40), rel=0.15)


def test_sign_flip_power_agrees_with_t_power():
    """The simulated exact sign-flip test has power close to the t approximation."""
    t = power_episode_effect(0.8, 1.0, 12, 0.05)
    sf = power_episode_effect(
        0.8, 1.0, 12, 0.05, method="sign_flip", rng=np.random.default_rng(12), n_sim=400
    )
    assert sf == pytest.approx(t, abs=0.1)


def test_episode_power_rejects_bad_input():
    """Non-integer episodes, non-positive SD and unknown methods raise."""
    with pytest.raises(ValueError):
        power_episode_effect(1.0, 1.0, 2.5, 0.05)
    with pytest.raises(ValueError):
        power_episode_effect(1.0, 0.0, 10, 0.05)
    with pytest.raises(ValueError):
        power_episode_effect(1.0, 1.0, 10, 0.05, method="z")
    with pytest.raises(ValueError):
        power_episode_effect(1.0, 1.0, 10, 0.05, method="sign_flip")
