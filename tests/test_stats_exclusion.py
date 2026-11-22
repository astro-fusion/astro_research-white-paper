"""Exclusion by effect removal and X (ADR-008 section 2, WP-86).

Covers section 2.2 and the fast subset of the proof cases of section 2.4
(X1 to X10). Effects are planted in the **bars**, then the full block and
exclusion code runs. The full-size cases (10,000 replications per cell, pass
mark: upper one-sided 95% Clopper-Pearson bound at or below 0.06) run in the
certificate suite (WP-98) through the ``run_x*`` functions below; set
``ASTRO_CALIBRATE_FULL=1`` to run them here. The fast subset uses 400
replications and the fast mark 0.085 of section 1.3.
"""

import ast
import inspect
import math
import os
from pathlib import Path

import numpy as np
import pytest

from tests import simulators as sim
from vedic_astrology_core.paperkit import results as paper
from vedic_astrology_core.stats import blocks as B
from vedic_astrology_core.stats import exclusion as X
from vedic_astrology_core.stats import rates
from vedic_astrology_core.stats.equivalence import episode_equivalence
from vedic_astrology_core.validity import calibration as cal

FULL = os.environ.get("ASTRO_CALIBRATE_FULL") == "1"
BASE_SEED = 20261122
REPS = 10_000 if FULL else 400
#: Shift cells are cheap: the fast subset runs more of them for a sharper bound.
REPS_SHIFT = 10_000 if FULL else 1_500
MARK = 0.06 if FULL else 0.085
ALPHA = 0.05
ROOT = Path(__file__).resolve().parents[1]


def _rng(case, cell, i, purpose="outcome"):
    return np.random.default_rng([cal.case_seed(BASE_SEED, case, cell, purpose), i])


def _design(k, n_active=8, balance=1.0):
    c = sim.balance_calendar(balance, k, n_active)
    return c, B.build_blocks(c, merge_gap=0)


def _excluded(design, y, outcome_type, sesoi, thin_rng=None, side="greater", a=ALPHA):
    er = X.EffectRemoval(design, y, outcome_type=outcome_type, thinning_rng=thin_rng)
    p = er.exclusion_p(sesoi, side)
    info = er.informative_at(sesoi, side)
    return p <= a and X.can_limit(er.k_eff, info, a)


def _assert_rate(hits, reps, mark=MARK):
    bound = cal.clopper_pearson_upper(hits, reps)
    assert bound <= mark, f"{hits}/{reps} false exclusions, upper bound {bound:.4f} > {mark}"


# ------------------------------------------------------------ case runners
def run_x_continuous(case, kind, k, sesoi, reps=REPS_SHIFT, outcome_type="continuous", balance=1.0):
    """X1, X2, X7: false "excluded" at a constant planted effect equal to the SESOI."""
    c, d = _design(k, balance=balance)
    hits = 0
    for i in range(reps):
        rng = _rng(case, f"{kind}/{k}/{balance}", i)
        bars = sim.continuous_bars(kind, len(c), rng)
        if outcome_type == "continuous":
            y = sim.plant_shift(bars, c, sesoi)
        else:  # log_ratio: positive bars times the ratio, then the log scale
            y = np.log(sim.plant_ratio(np.abs(bars) + 1e-3, c, sesoi))
        hits += _excluded(d, y, outcome_type, sesoi)
    return hits


def run_x3(mean, sesoi, k, reps=REPS, balance=1.0):
    """X3: rare Poisson events, rate ratio planted in the bars."""
    c, d = _design(k, balance=balance)
    mult = sim.effect_multiplier(c, sesoi)
    hits = 0
    for i in range(reps):
        rng = _rng("X3", f"{mean}/{sesoi}/{k}/{balance}", i)
        ev = sim.poisson_events(c, mean, 8, rng, mult)
        hits += _excluded(d, ev, "events", sesoi, _rng("X3", f"{mean}/{sesoi}/{k}", i, "thinning"))
    return hits


def run_x4(sesoi, k, reps=REPS):
    """X4: Neyman-Scott clusters with a doubling background; the rate ratio on parents.

    The counting unit is the declustered mainshock; the fast subset uses the
    generator's parents (an ideal declustering).
    """
    c, d = _design(k, n_active=20)
    mult = sim.effect_multiplier(c, sesoi)
    hits = 0
    for i in range(reps):
        rng = _rng("X4", f"{sesoi}/{k}", i)
        out = sim.neyman_scott(len(c), rng, parent_rate=0.05, multiplier=mult)
        hits += _excluded(d, out["parents"], "events", sesoi, _rng("X4", f"{sesoi}/{k}", i, "thinning"))
    return hits


def run_x5_garch(sesoi, k, reps=REPS):
    """X5: clustered GARCH flags at a 5% base rate, risk ratio planted."""
    c, d = _design(k, n_active=40)
    hits = 0
    for i in range(reps):
        rng = _rng("X5", f"garch/{sesoi}/{k}", i)
        f = sim.garch_flags(len(c), rng)
        f = sim.plant_risk_ratio(f, c, sesoi, rng, sim.GARCH_FLAG_RATE)
        hits += _excluded(d, f, "flags", sesoi, _rng("X5", f"garch/{sesoi}/{k}", i, "thinning"))
    return hits


def run_x5_drought(sesoi, k, reps=REPS):
    """X5: drought-year flags at 15% on the yearly generator, risk ratio planted."""
    c, d = _design(k, n_active=2)
    years = np.arange(1871, 1871 + len(c))
    hits = 0
    for i in range(reps):
        rng = _rng("X5", f"drought/{sesoi}/{k}", i)
        f = sim.drought_flags(sim.yearly_rainfall(years, rng)["anomaly"])
        f = sim.plant_risk_ratio(f, c, sesoi, rng, sim.DROUGHT_FLAG_RATE)
        hits += _excluded(d, f, "flags", sesoi, _rng("X5", f"drought/{sesoi}/{k}", i, "thinning"))
    return hits


def run_x6(kind, k, sesoi, true_effect, reps, grid, outcome_type="continuous"):
    """X6: share of runs whose X95 lies below the true effect."""
    c, d = _design(k)
    below = 0
    for i in range(reps):
        rng = _rng("X6", f"{kind}/{k}/{true_effect}", i)
        if outcome_type == "continuous":
            y = sim.plant_shift(sim.continuous_bars(kind, len(c), rng), c, true_effect)
            thin = None
        else:
            y = sim.poisson_events(c, 2.0, 8, rng, sim.effect_multiplier(c, true_effect))
            thin = _rng("X6", f"{kind}/{k}/{true_effect}", i, "thinning")
        res = X.exclusion(d, y, outcome_type=outcome_type, side="greater", sesoi=sesoi,
                          grid=grid, thinning_rng=thin, steps=12)
        if not res.x95.unbounded and res.x95.value < true_effect:
            below += 1
    return below


def run_x8(kind, n_episodes=10, reps=800, seed=1):
    """X8: the old ``episode_equivalence`` on the inputs of strategy-audit appendix A.1."""
    rng = np.random.default_rng(seed)
    hits = 0
    for _ in range(reps):
        if kind == "exponential":
            e = rng.exponential(1.0, n_episodes) - 1.0
        elif kind == "rare":
            e = rng.binomial(1, 0.1, n_episodes) / 0.1 - 1.0
        elif kind == "lognormal":
            e = rng.lognormal(0.0, 1.0, n_episodes) - math.exp(0.5)
        else:
            e = rng.normal(0.0, 1.0, n_episodes)
        hits += episode_equivalence(0.5 + e, sesoi=0.5, alpha=0.05).excluded
    return hits / reps


def run_x9(kind, k, sesoi, reps=REPS):
    """X9 (recorded, no pass mark): whole effect in 20% of the episodes, mean = SESOI."""
    c, d = _design(k)
    hits = 0
    for i in range(reps):
        rng = _rng("X9", f"{kind}/{k}", i)
        if kind == "events":
            mult = sim.uneven_multiplier(c, sesoi, rng, scale="ratio")
            y = sim.poisson_events(c, 2.0, 8, rng, mult)
            hits += _excluded(d, y, "events", sesoi, _rng("X9", f"{kind}/{k}", i, "thinning"))
        else:
            shift = sim.uneven_multiplier(c, sesoi, rng, scale="shift")
            y = sim.plant_shift(sim.continuous_bars(kind, len(c), rng), c, shift)
            hits += _excluded(d, y, "continuous", sesoi)
    return hits / reps


# ------------------------------------------------------- the same block test
def test_sign_flip_rows_equal_the_primary_test_exact():
    rng = np.random.default_rng(3)
    for k in (1, 2, 3, 7, 12, 15):
        for trial in range(6):
            if trial % 2:
                d = rng.integers(-2, 3, size=k).astype(float) / 4.0  # many ties
            else:
                d = rng.normal(size=k)
            w = rng.integers(1, 9, size=k).astype(float)
            for alt in ("less", "greater"):
                ours = X.sign_flip_p_rows(d[None, :], w, alt)[0]
                ref = B.weighted_sign_flip(d, w, alternative=alt).p_value
                assert ours == ref, (k, trial, alt, ours, ref)


def test_sign_flip_rows_equal_the_primary_test_monte_carlo():
    rng = np.random.default_rng(4)
    d, w = rng.normal(size=23), np.full(23, 3.0)
    for alt in ("less", "greater"):
        ours = X.sign_flip_p_rows(d, w, alt, signflip_seed=11, n_draws=3000)[0]
        ref = B.weighted_sign_flip(d, w, alternative=alt, rng=np.random.default_rng(11), n_draws=3000)
        assert ours == ref.p_value
    with pytest.raises(ValueError, match="signflip_seed"):
        X.sign_flip_p_rows(d, w, "less")


def test_shift_removal_is_the_primary_test_on_adjusted_bars():
    c, d = _design(12)
    rng = np.random.default_rng(5)
    y = rng.lognormal(size=len(c))
    er = X.EffectRemoval(d, y, outcome_type="continuous")
    for r in (-0.5, 0.0, 0.3, 1.1):
        adj = X.shift_active(d, y, r, outcome_type="continuous")
        ref = B.primary_test(d, adj, alternative="less", outcome_type="continuous").p_value
        assert er.p_value(r, "less") == pytest.approx(ref, abs=0.0, rel=1e-12)
    ly = np.log(y)
    er = X.EffectRemoval(d, ly, outcome_type="log_ratio")
    adj = X.shift_active(d, ly, 1.5, outcome_type="log_ratio")
    ref = B.primary_test(d, adj, alternative="less", outcome_type="log_ratio").p_value
    assert er.p_value(1.5, "less") == ref


def test_events_at_ratio_one_are_the_primary_test_on_the_rate_ratio_scale():
    """S-06: on equal-size blocks nothing is thinned at r = 1; each repetition is the primary p."""
    c, d = _design(12)
    rng = np.random.default_rng(6)
    ev = sim.poisson_events(c, 2.0, 8, rng)
    er = X.EffectRemoval(d, ev, outcome_type="events", thinning_rng=np.random.default_rng(1), n_thin=9)
    reps = er.p_reps(1.0, "less")
    ref = B.primary_test(d, ev, alternative="less", outcome_type="events").p_value
    assert np.all(reps == ref)
    assert er.p_value(1.0, "less") == min(1.0, 2 * ref)
    np.testing.assert_array_equal(er.differences(1.0)[0], B.block_differences(d, ev, outcome_type="events").d)


# ----------------------------------------------------------- thinning rules
def test_thinning_nested_and_keep_rate():
    c, d = _design(12, n_active=40)
    ev = np.random.default_rng(7).poisson(3.0, len(c))
    er = X.EffectRemoval(d, ev, outcome_type="events", thinning_rng=np.random.default_rng(2))
    prev_a, prev_c = er.kept_counts(1.0)
    assert np.all(prev_a == B.block_differences(d, ev, outcome_type="events").active_sum)
    for rho in (1.2, 1.5, 2.0, 3.0, 10.0):
        ka, kc = er.kept_counts(rho)
        assert np.all(ka <= prev_a) and np.all(kc == prev_c)  # nested, control untouched
        prev_a = ka
    ka, _ = er.kept_counts(2.0)
    total = er.kept_counts(1.0)[0].sum(axis=1)
    assert abs(ka.sum(axis=1).mean() / total.mean() - 0.5) < 0.02
    # The "less" claim thins the control side instead.
    _, kc = er.kept_counts(0.5)
    assert np.all(kc <= er.kept_counts(1.0)[1])


def test_thinning_draws_come_from_the_test_stream_only():
    c, d = _design(12)
    ev = sim.poisson_events(c, 2.0, 8, np.random.default_rng(8))
    a = X.EffectRemoval(d, ev, outcome_type="events", thinning_rng=np.random.default_rng(5))
    b = X.EffectRemoval(d, ev, outcome_type="events", thinning_rng=np.random.default_rng(5))
    assert a.exclusion_p(2.0, "greater") == b.exclusion_p(2.0, "greater")
    with pytest.raises(ValueError, match="thinning_rng"):
        X.EffectRemoval(d, ev, outcome_type="events")
    with pytest.raises(ValueError, match="whole counts"):
        X.EffectRemoval(d, ev + 0.5, outcome_type="events", thinning_rng=np.random.default_rng(1))


def test_reported_p_is_twice_the_median_capped():
    c, d = _design(12)
    ev = sim.poisson_events(c, 2.0, 8, np.random.default_rng(9))
    er = X.EffectRemoval(d, ev, outcome_type="events", thinning_rng=np.random.default_rng(3))
    reps = er.p_reps(2.0, "less")
    assert len(reps) == X.N_THIN == 199
    assert er.p_value(2.0, "less") == min(1.0, 2.0 * float(np.sort(reps)[99]))
    assert er.p_value(1e-6, "less") == 1.0  # capped


def test_unequal_blocks_are_equalised_by_thinning_the_longer_side():
    """Section 2.2: unequal exposure is equalised first (A1 makes it a no-op on built designs)."""
    n = 40
    act = np.zeros(n, dtype=bool)
    act[10:14] = True
    ep = B.build_blocks(act, merge_gap=0).blocks[0].episode
    assert (ep.start, ep.end) == (10, 13)
    blk = B.Block(0, ep, np.arange(10, 14), np.arange(9, 1, -1), np.arange(14, 22),
                  True, True, True, None)
    design = B.BlockDesign(n, (blk,), 0, 0, "neighbours", "x", None)
    y = np.ones(n)
    er = X.EffectRemoval(design, y, outcome_type="events", thinning_rng=np.random.default_rng(4), n_thin=2000)
    ka, kc = er.kept_counts(1.0)
    assert np.all(ka == 4)  # the short side keeps everything
    assert abs(kc.mean() - 4.0) < 0.15  # 16 control events kept at 4/16
    assert er.differences(1.0).shape == (2000, 1)


# --------------------------------------------------------- information rule
def test_minimum_information_thresholds():
    assert X.min_informative(0.05) == 5
    assert X.min_informative(0.001) == 10
    assert X.min_informative(0.0625) == 4
    assert X.can_limit(8.0, 5, 0.05) and not X.can_limit(7.99, 5, 0.05)
    assert not X.can_limit(12.0, 4, 0.05)
    assert X.can_limit(12.0, 10, 0.001) and not X.can_limit(12.0, 9, 0.001)


def test_too_few_blocks_is_unbounded_with_no_number():
    c, d = _design(6)
    y = np.random.default_rng(1).normal(size=len(c))
    res = X.exclusion(d, y, outcome_type="continuous", side="greater", sesoi=0.5, grid=[0.25, 0.5, 1, 2, 4, 8, 16])
    assert res.x95.unbounded and res.x95.reason == X.REASON_FEW_BLOCKS
    rec = res.to_dict()["x95"]
    assert rec["unbounded"] is True and "value" not in rec
    assert not res.excluded(0.05) and res.card_lines() == []


def test_rare_events_give_unbounded_for_lack_of_information():
    c, d = _design(12)
    ev = np.zeros(len(c))
    ev[np.flatnonzero(c)[:3]] = 1  # three events in all
    res = X.exclusion(d, ev, outcome_type="events", side="greater", sesoi=2.0,
                      grid=[1.5, 2, 4, 8, 16, 64], thinning_rng=np.random.default_rng(2))
    assert res.informative_at_sesoi <= 3
    assert res.x95.unbounded and res.x95.reason == X.REASON_LOW_INFORMATION
    assert not res.excluded(0.05)


def test_x_strict_needs_more_information_than_x95():
    c, d = _design(9)
    y = sim.plant_shift(np.random.default_rng(2).normal(size=len(c)), c, -3.0)
    res = X.exclusion(d, y, outcome_type="continuous", side="greater", sesoi=0.5,
                      grid=[0.1, 0.5, 1, 2, 4], a_test=0.001)
    assert not res.x95.unbounded
    assert res.x_strict.unbounded and res.x_strict.reason == X.REASON_LOW_INFORMATION
    assert res.x_strict.required_informative == 10


def test_not_rejected_on_grid_is_unbounded_and_no_sesoi_gives_no_limit():
    c, d = _design(12)
    y = sim.plant_shift(np.random.default_rng(3).normal(size=len(c)), c, 5.0)
    res = X.exclusion(d, y, outcome_type="continuous", side="greater", sesoi=0.5, grid=[0.25, 0.5, 1.0])
    assert res.x95.unbounded and res.x95.reason == X.REASON_NOT_REACHED
    res = X.exclusion(d, y, outcome_type="continuous", side="greater", sesoi=None, grid=[0.25, 0.5, 1.0])
    assert res.p_exclusion is None and res.x95.reason == X.REASON_NO_SESOI and not res.excluded(0.5)


# -------------------------------------------------------- X95 by inversion
def test_x95_is_the_smallest_rejected_effect():
    c, d = _design(12)
    y = sim.plant_shift(np.random.default_rng(4).lognormal(size=len(c)), c, 0.2)
    grid = [0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 4.0]
    res = X.exclusion(d, y, outcome_type="continuous", side="greater", sesoi=0.5, grid=grid)
    er = X.EffectRemoval(d, y, outcome_type="continuous")
    x = res.x95.value
    assert er.exclusion_p(x, "greater") <= 0.05
    assert er.exclusion_p(x * (1 - 1e-6), "greater") > 0.05
    lo, hi = er.interval(0.05, np.linspace(-3, 3, 61))
    assert lo < hi and hi == pytest.approx(x, rel=1e-6)
    assert res.card_lines()[0].startswith("Ruled out: a steady effect of ")
    assert "22%" in res.card_lines()[1]


def test_side_is_required_and_mirrors():
    c, d = _design(12)
    y = np.random.default_rng(5).normal(size=len(c))
    with pytest.raises(ValueError, match="no default side"):
        X.exclusion(d, y, outcome_type="continuous", side=None, sesoi=0.5, grid=[0.5, 1])
    er_up = X.EffectRemoval(d, y, outcome_type="continuous")
    er_dn = X.EffectRemoval(d, -y, outcome_type="continuous")
    for m in (0.2, 0.5, 1.0):
        assert er_up.exclusion_p(m, "greater") == er_dn.exclusion_p(m, "less")
        both = er_up.exclusion_p(m, "two-sided")
        assert both == max(er_up.exclusion_p(m, "greater"), er_up.exclusion_p(m, "less"))


def test_effect_size_scales_are_checked():
    c, d = _design(12)
    ev = sim.poisson_events(c, 2.0, 8, np.random.default_rng(1))
    with pytest.raises(ValueError, match="ratio above 1"):
        X.exclusion(d, ev, outcome_type="events", side="greater", sesoi=0.5, grid=[1.5, 2],
                    thinning_rng=np.random.default_rng(1))
    with pytest.raises(ValueError, match="strictly increasing"):
        X.exclusion(d, ev, outcome_type="events", side="greater", sesoi=2.0, grid=[2, 1.5],
                    thinning_rng=np.random.default_rng(1))


def test_not_addressed_share_values():
    assert round(X.not_addressed_share(8), 2) == 0.31
    assert round(X.not_addressed_share(12), 2) == 0.22
    assert round(X.not_addressed_share(20), 2) == 0.14


def test_expected_informative_for_the_gate():
    c, d = _design(12)
    assert X.expected_informative(d, 0.0, 2.0, outcome_type="events", side="greater") == 0.0
    assert X.expected_informative(d, 1.0, 2.0, outcome_type="events", side="greater") == pytest.approx(12, abs=1e-3)
    low = X.expected_informative(d, 0.1 / 8, 2.0, outcome_type="events", side="greater")
    assert low < X.min_informative(0.05)  # mean 0.1 per window: "can limit: no"
    assert X.expected_informative(d, 0.5, 1.5, outcome_type="continuous", side="greater") == 12


# ---------------------------------------------------------------- X10
@pytest.mark.parametrize("outcome_type", X.OUTCOME_TYPES)
@pytest.mark.parametrize("side", X.SIDES)
def test_x10_exclusion_p_never_increases_with_r(outcome_type, side):
    for k in (8, 12, 22):
        c, d = _design(k)
        rng = np.random.default_rng(k)
        if outcome_type == "continuous":
            y, grid = rng.lognormal(size=len(c)), np.linspace(0.01, 4, 50)
        elif outcome_type == "log_ratio":
            y, grid = np.log(rng.exponential(size=len(c))), np.linspace(1.01, 8, 50)
        elif outcome_type == "events":
            y, grid = rng.poisson(0.4, len(c)), np.linspace(1.01, 12, 50)
        else:
            y, grid = (rng.random(len(c)) < 0.2).astype(int), np.linspace(1.01, 12, 50)
        er = X.EffectRemoval(d, y, outcome_type=outcome_type, thinning_rng=np.random.default_rng(1),
                             signflip_seed=7, n_draws=2000)
        p = [er.exclusion_p(m, side) for m in grid]
        assert all(b <= a for a, b in zip(p, p[1:])), (k, p)


# -------------------------------------------------------------- X1 to X7
@pytest.mark.parametrize("kind", ["normal", "t3"])
@pytest.mark.parametrize("k", [8, 12] + ([20] if FULL else []))
def test_x1_gaussian_heavy_tails(kind, k):
    _assert_rate(run_x_continuous("X1", kind, k, 0.5), REPS_SHIFT)


@pytest.mark.parametrize("kind", ["lognormal", "exponential"])
@pytest.mark.parametrize("k", [8, 12] + ([20] if FULL else []))
def test_x2_right_skew(kind, k):
    _assert_rate(run_x_continuous("X2", kind, k, 0.5), REPS_SHIFT)


@pytest.mark.parametrize("kind", ["exponential", "lognormal"])
def test_x1_x2_log_ratio(kind):
    _assert_rate(run_x_continuous("X2", kind, 12, 1.5, outcome_type="log_ratio"), REPS_SHIFT)


X3_CELLS = (
    [(m, s, k) for m in sim.RARE_EVENT_MEANS for s in (2.0, 1.5) for k in sim.BLOCK_COUNTS]
    if FULL else [(0.1, 2.0, 12), (0.5, 2.0, 12), (2.0, 2.0, 12), (2.0, 1.5, 8)]
)


@pytest.mark.parametrize("mean,sesoi,k", X3_CELLS)
def test_x3_rare_events(mean, sesoi, k):
    _assert_rate(run_x3(mean, sesoi, k), REPS)


def test_x4_clustered_events():
    _assert_rate(run_x4(2.0, 12), REPS)


def test_x5_clustered_and_drought_flags():
    _assert_rate(run_x5_garch(2.0, 12), REPS)
    _assert_rate(run_x5_drought(2.0, 12), REPS)


@pytest.mark.parametrize("true_frac", [0.0, 0.5, 1.0, 2.0])
def test_x6_coverage(true_frac):
    reps = REPS if FULL else 200
    mark = MARK if FULL else 0.1
    below = run_x6("lognormal", 12, 0.5, 0.5 * true_frac, reps, [0.05, 0.25, 0.5, 1, 2, 4, 8])
    assert cal.clopper_pearson_upper(below, reps) <= mark
    if true_frac:
        reps_e = REPS if FULL else 60
        below = run_x6("events", 12, 2.0, 2.0 ** true_frac, reps_e, [1.1, 1.5, 2, 3, 4, 8, 16],
                       outcome_type="events")
        assert below <= max(3, cal.max_passing_count(reps_e, 0.06)) if FULL else below <= 3


@pytest.mark.parametrize("balance", sim.BALANCES)
def test_x7_balance_edge(balance):
    reps = REPS if FULL else 200
    mark = MARK if FULL else 0.1
    assert cal.clopper_pearson_upper(run_x_continuous("X7", "exponential", 12, 0.5, reps, balance=balance), reps) <= mark
    assert cal.clopper_pearson_upper(run_x3(2.0, 2.0, 12, reps, balance=balance), reps) <= mark


# ----------------------------------------------------------- X8 and X9
@pytest.mark.parametrize("kind", ["exponential", "rare", "lognormal"])
def test_x8_old_episode_equivalence_still_fails(kind):
    """Documents the loophole S-01: the old route falsely excludes on skewed rows."""
    assert run_x8(kind) > 0.10


def test_x9_uneven_effect_is_recorded_not_gated():
    assert cal.get_case("X9").rule == cal.RECORD
    rate = run_x9("lognormal", 12, 0.5, reps=100)
    assert 0.0 <= rate <= 1.0


# ---------------------------------------------- deprecation and imports
def _validity_imports():
    found = []
    for path in sorted((ROOT / "libs/vedic_astrology_core/validity").rglob("*.py")):
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                found += [(path.name, a.name) for a in node.names]
            elif isinstance(node, ast.Attribute):
                found.append((path.name, node.attr))
            elif isinstance(node, ast.Name):
                found.append((path.name, node.id))
    return found


def test_validity_does_not_use_the_deprecated_functions():
    names = {d.rsplit(".", 1)[1] for d in X.DEPRECATED}
    assert names == {"episode_equivalence", "upper_limit_episodes"}
    bad = [(f, n) for f, n in _validity_imports() if n in names]
    assert bad == [], f"core/validity uses deprecated exclusion functions: {bad}"


def test_rate_ratio_docstring_is_corrected():
    doc = inspect.getdoc(rates.rate_ratio) + inspect.getdoc(rates)
    assert "not used for any verdict" in doc
    assert "too narrow for clustered events" in doc
    assert "use it for the interval" not in doc


def test_exclusion_module_reads_no_binomial_interval():
    src = inspect.getsource(X)
    assert "rate_ratio(" not in src and "from .rates" not in src


# ------------------------------------------------------- paper kit (G-11)
def test_paperkit_accepts_unbounded_limits():
    c, d = _design(6)
    y = np.random.default_rng(1).normal(size=len(c))
    res = X.exclusion(d, y, outcome_type="continuous", side="greater", sesoi=0.5, grid=[0.5, 1.0])
    c2, d2 = _design(12)
    y2 = sim.plant_shift(np.random.default_rng(2).normal(size=len(c2)), c2, -2.0)
    res2 = X.exclusion(d2, y2, outcome_type="continuous", side="greater", sesoi=0.5, grid=[0.1, 0.5, 1.0])
    r = paper.Results({"tests": [{"x95": res.to_dict()["x95"]}, {"x95": res2.to_dict()["x95"]}]})
    assert r.is_unbounded("tests.0.x95") and not r.is_unbounded("tests.1.x95")
    assert r.limit("tests.0.x95") == "unbounded"
    assert r.limit("tests.0.x95", unbounded_text="no limit") == "no limit"
    assert r.limit("tests.1.x95", 3) == f"{res2.x95.value:.3f}"
    with pytest.raises(paper.UnboundedLimitError):
        r.get("tests.0.x95.value")
    with pytest.raises(paper.MissingKeyError):
        r.get("tests.1.x95.nothing")


def test_paperkit_refuses_a_number_on_an_unbounded_limit():
    assert paper.limit_problems({"unbounded": True, "value": 3.0})
    assert paper.limit_problems({"unbounded": False, "value": float("inf")})
    assert paper.limit_problems({"unbounded": False})
    assert paper.limit_problems({"value": 2.0})
    assert paper.limit_problems({"unbounded": True, "value": None}) == []
    r = paper.Results({"x": {"unbounded": True, "value": 3.0}, "y": {"unbounded": True, "value": None}})
    with pytest.raises(ValueError, match="carries a number"):
        r.limit("x")
    with pytest.raises(paper.UnboundedLimitError):
        r.get("y.value")
    with pytest.raises(paper.NullValueError):
        paper.format_number(float("inf"))
