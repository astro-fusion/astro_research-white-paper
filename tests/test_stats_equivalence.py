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
    r1 = cohen_kappa_ci(a, b, n_boot=500, mean_block=20, rng=np.random.default_rng(42))
    r2 = cohen_kappa_ci(a, b, n_boot=500, mean_block=20, rng=np.random.default_rng(42))
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


# --------------------------------------------------------------------------
# WP-08: SESOI decisions, episode-clustered TOST and the upper limit X
# --------------------------------------------------------------------------

from vedic_astrology_core.stats.episodes import wild_cluster_interval  # noqa: E402
from vedic_astrology_core.stats.equivalence import (  # noqa: E402
    DECISIONS,
    effect_equivalence,
    episode_equivalence,
    strict_level,
    upper_limit,
    upper_limit_episodes,
)


def test_episode_equivalence_false_exclusion_rate_at_the_sesoi():
    """With the true effect equal to the SESOI, "excluded" occurs at most alpha.

    This is the headline risk of WP-08: a wrong SE gives a false exclusion.
    """
    rng = np.random.default_rng(2026)
    sesoi, alpha, n_sim = 0.5, 0.05, 400
    hits = 0
    for _ in range(n_sim):
        d = sesoi + rng.normal(0.0, 1.0, 12)
        hits += episode_equivalence(d, sesoi, alpha=alpha).excluded
    assert hits / n_sim <= alpha + 3 * np.sqrt(alpha * (1 - alpha) / n_sim)


def test_episode_equivalence_false_support_rate_at_zero():
    """With no effect, "found" occurs at most alpha."""
    rng = np.random.default_rng(7)
    n_sim, alpha = 400, 0.05
    hits = 0
    for _ in range(n_sim):
        hits += episode_equivalence(rng.normal(0, 1, 10), 1.0, alpha=alpha).found
    assert hits / n_sim <= alpha + 3 * np.sqrt(alpha * (1 - alpha) / n_sim)


def test_episode_clustering_prevents_false_exclusion_from_bar_counts():
    """Many bars per episode do not shrink the episode-level test.

    The bars inside an episode share one regime, so their naive SE is tiny;
    the episode route only sees K = 9 differences and stays inconclusive.
    """
    rng = np.random.default_rng(3)
    sesoi = 1.0
    episode_effects = sesoi + rng.normal(0, 2.0, 9)
    bars = np.concatenate([e + rng.normal(0, 0.1, 500) for e in episode_effects])
    naive_se = bars.std(ddof=1) / np.sqrt(len(bars))
    ours = episode_equivalence(episode_effects, sesoi)
    assert ours.decision == "inconclusive"
    assert ours.x_upper > sesoi
    # the naive bar-level SE is two orders of magnitude smaller
    assert naive_se < 0.05 * ours.x_upper


def test_exclusion_agrees_with_the_wild_cluster_interval():
    """Excluded at alpha iff the 1 - 2 alpha interval's upper bound is below SESOI."""
    rng = np.random.default_rng(11)
    for _ in range(40):
        d = rng.normal(rng.uniform(-0.5, 1.0), 1.0, 10)
        sesoi = rng.uniform(0.3, 2.0)
        res = episode_equivalence(d, sesoi, alpha=0.05)
        ci = wild_cluster_interval(d, level=0.90)
        assert res.excluded == (ci.ci_high < sesoi)
        assert res.x_upper == pytest.approx(ci.ci_high)


def test_found_and_excluded_gives_found_below_sesoi():
    """A precise small effect is found and is below the SESOI."""
    rng = np.random.default_rng(5)
    d = 0.3 + rng.normal(0, 0.05, 15)
    res = episode_equivalence(d, 1.0)
    assert res.found and res.excluded
    assert res.decision == "found"
    assert res.below_sesoi


def test_clear_effect_is_found_not_excluded():
    """A large effect above the SESOI is found and not excluded."""
    d = 2.0 + np.random.default_rng(6).normal(0, 0.3, 12)
    res = episode_equivalence(d, 0.5)
    assert res.decision == "found"
    assert not res.excluded and not res.below_sesoi


def test_too_few_episodes_is_inconclusive_with_infinite_bound():
    """Four episodes: p cannot go below 1/16, so nothing is found or excluded."""
    res = episode_equivalence([0.0, 0.01, -0.01, 0.02], 5.0, alpha=0.05)
    assert res.decision == "inconclusive"
    assert not res.exclusion_attainable
    assert res.p_min == pytest.approx(1 / 16)
    assert res.x_upper == float("inf")
    assert res.notes


def test_direction_less_mirrors_greater():
    """A "less" claim on d equals a "greater" claim on -d."""
    d = np.random.default_rng(8).normal(-0.2, 1.0, 11)
    a = episode_equivalence(d, 0.8, direction="less")
    b = episode_equivalence(-d, 0.8, direction="greater")
    assert (a.decision, a.p_support, a.p_equivalence) == (
        b.decision,
        b.p_support,
        b.p_equivalence,
    )
    assert a.x_upper == pytest.approx(b.x_upper)
    assert a.estimate == pytest.approx(-d.mean())


def test_either_direction_is_tost_on_both_margins():
    """For "either" the equivalence p is the larger of the two one-sided tests."""
    d = np.random.default_rng(9).normal(0.1, 0.5, 12)
    res = episode_equivalence(d, 1.0, direction="either")
    assert res.p_equivalence == max(res.p_equivalence_lower, res.p_equivalence_upper)
    ci = wild_cluster_interval(d, level=0.90)
    assert res.x_upper == pytest.approx(max(abs(ci.ci_low), abs(ci.ci_high)))


def test_decision_words_are_fixed():
    """Only found, excluded and inconclusive are returned; never "null"."""
    assert DECISIONS == ("found", "excluded", "inconclusive")
    rng = np.random.default_rng(10)
    for _ in range(20):
        res = episode_equivalence(rng.normal(0, 1, 9), 0.7)
        assert res.decision in DECISIONS


def test_effect_equivalence_matches_tost_closed_form():
    """The SE route equals tost() for "either" and one-sided z for directions."""
    r = effect_equivalence(
        0.05, 0.1, 0.3, se_method="episode_cluster", direction="either"
    )
    t = tost(0.05, 0.1, -0.3, 0.3)
    assert r.p_equivalence == pytest.approx(t.p_value)
    assert r.decision == ("excluded" if t.equivalent else "inconclusive")
    g = effect_equivalence(0.05, 0.1, 0.3, se_method="block_bootstrap")
    assert g.p_equivalence == pytest.approx(sps.norm.cdf((0.05 - 0.3) / 0.1))
    assert g.p_support == pytest.approx(sps.norm.sf(0.5))
    assert g.x_upper == pytest.approx(0.05 + sps.norm.ppf(0.95) * 0.1)
    lo = effect_equivalence(-0.05, 0.1, 0.3, se_method="exact", direction="less")
    assert lo.p_equivalence == pytest.approx(g.p_equivalence)
    assert lo.estimate == pytest.approx(0.05)


def test_effect_equivalence_requires_an_se_method():
    """The caller must say where the SE comes from; unknown sources raise."""
    with pytest.raises(TypeError):
        effect_equivalence(0.0, 0.1, 0.3)  # type: ignore[call-arg]
    with pytest.raises(ValueError):
        effect_equivalence(0.0, 0.1, 0.3, se_method="bars")
    r = effect_equivalence(0.0, 0.1, 0.3, se_method="analytic_independent")
    assert r.notes


@pytest.mark.parametrize(
    "kwargs",
    [
        {"sesoi": 0.0},
        {"sesoi": -1.0},
        {"direction": "up"},
        {"alpha": 0.6},
        {"x_level": 0.4},
    ],
)
def test_equivalence_rejects_bad_input(kwargs):
    """A non-positive SESOI, an unknown direction or a bad level raises."""
    args = {"sesoi": 0.5, "direction": "greater", "alpha": 0.05, "x_level": 0.95}
    args.update(kwargs)
    sesoi = args.pop("sesoi")
    with pytest.raises(ValueError):
        episode_equivalence(np.arange(10.0), sesoi, **args)


def test_upper_limit_closed_form_and_strict_level():
    """X95 is est + z_0.95 SE; X-strict uses level 1 - 0.05 / M."""
    assert upper_limit(0.2, 0.1) == pytest.approx(0.2 + 1.6448536 * 0.1)
    assert upper_limit(0.2, 0.1, direction="less") == pytest.approx(
        -0.2 + 1.6448536 * 0.1
    )
    assert upper_limit(-0.2, 0.1, direction="either") == pytest.approx(
        0.2 + 1.6448536 * 0.1
    )
    assert upper_limit(0.0, 0.1, df=5) == pytest.approx(sps.t.ppf(0.95, 5) * 0.1)
    assert strict_level(40) == pytest.approx(0.99875)
    lvl = strict_level(40)
    assert upper_limit(0.2, 0.1, level=lvl) > upper_limit(0.2, 0.1)


def test_x_strict_needs_more_episodes_than_x95():
    """With 8 episodes X95 is finite but X-strict at M = 40 is unbounded."""
    d = np.random.default_rng(13).normal(0, 1, 8)
    assert np.isfinite(upper_limit_episodes(d, 0.95))
    assert upper_limit_episodes(d, strict_level(40)) == float("inf")
