"""Balanced disjoint blocks and the primary block sign-flip test (ADR-008 WP-85).

Covers section 1.1 items 1 to 10 and the fast subset of the proof cases of
section 1.3 (B1 to B6), with Amendment A1 (equal-size blocks) and Amendment
A2 (one-sided equal-size blocks for single-bar and edge episodes, side fixed
by the plan seed in calendar order). The full-size cases (10,000
replications per cell) run in the certificate suite (WP-98) through the
``run_b*`` and ``run_a2`` functions below; set ``ASTRO_CALIBRATE_FULL=1`` to
run them here.
"""

import functools
import inspect
import itertools
import math
import os

import numpy as np
import pandas as pd
import pytest

from tests import simulators as sim
from vedic_astrology_core.stats import blocks as B
from vedic_astrology_core.stats.episodes import episode_differences, episodes, sign_flip_test
from vedic_astrology_core.validity import calibration as cal

FULL = os.environ.get("ASTRO_CALIBRATE_FULL") == "1"
BASE_SEED = 20261122
FAST_REPS = 400
ALPHA = 0.05


def _cal(s: str) -> np.ndarray:
    return np.array([c == "1" for c in s], dtype=bool)


# ---------------------------------------------------------------- item 2
def test_gap_cut_at_midpoint_odd_middle_dropped():
    #            0123456789012345
    c = _cal("0011000111000010")
    d = B.build_blocks(c, merge_gap=0)
    b0, b1, b2 = d.blocks
    assert b0.active.tolist() == [2, 3]
    assert b0.control_left.tolist() == [1]  # cap ceil(2/2) = 1, nearest first
    assert b0.control_right.tolist() == [4]  # gap 4..6 (odd): 5 dropped
    assert b1.control_left.tolist() == [6]
    assert b1.control_right.tolist() == [10, 11]  # gap 10..13: left half 10, 11
    assert b2.control_left.tolist() == [13]  # right half 12, 13; cap 1 -> nearest
    assert b2.control_right.tolist() == [15]
    # A1: one active bar with a neighbour on each side cannot be equal-size
    # without leaving a side empty.
    assert [b.reason for b in d.blocks] == [None, None, B.DROP_UNBALANCED]
    assert b0.n_control == b0.n_active and b1.n_control == b1.n_active
    used = set(itertools.chain.from_iterable(
        b.active.tolist() + b.control.tolist() for b in d.blocks))
    assert 5 not in used and 12 not in used


def test_cap_takes_nearest_bars():
    c = np.zeros(60, dtype=bool)
    c[20:26] = True  # 6 active -> cap 3 per side
    d = B.build_blocks(c, merge_gap=0)
    (b,) = d.blocks
    assert b.control_left.tolist() == [19, 18, 17]
    assert b.control_right.tolist() == [26, 27, 28]
    assert b.balance == 1.0


def test_merged_episode_inner_gap_is_never_control():
    c = _cal("000011001100000")
    d = B.build_blocks(c, merge_gap=2)
    (b,) = d.blocks
    assert b.active.tolist() == [4, 5, 8, 9]
    assert not set(b.control.tolist()) & {6, 7}
    assert b.control_left.tolist() == [3, 2]
    assert b.control_right.tolist() == [10, 11]


# ---------------------------------------------------------------- item 3
def test_guard_bars_skip_next_bars():
    c = np.zeros(40, dtype=bool)
    c[10:14] = True
    d = B.build_blocks(c, merge_gap=0, guard_bars=1)
    (b,) = d.blocks
    assert b.control_left.tolist() == [8, 7]
    assert b.control_right.tolist() == [15, 16]
    with pytest.raises(ValueError):
        B.build_blocks(c, merge_gap=0, guard_bars=-1)


def test_guard_bars_stay_inside_own_half():
    # gap of 6 between episodes: each half is 3 bars; with guard 1 each takes 2.
    c = _cal("00001111000000111100000")
    d = B.build_blocks(c, merge_gap=0, guard_bars=1)
    b0, b1 = d.blocks
    assert b0.control_right.tolist() == [9, 10]
    assert b1.control_left.tolist() == [12, 11]


# ---------------------------------------------------------------- item 4
def test_unbalanced_is_dropped_and_counted():
    c = sim.periodic_calendar(20, 5, 12)  # 2 control bars a side vs 20 active
    d = B.build_blocks(c, merge_gap=0)
    assert d.n_used == 0 and d.n_dropped == 12
    assert d.drop_counts[B.DROP_UNBALANCED] == 12
    assert B.DROP_LOW_BALANCE == B.DROP_UNBALANCED == "unbalanced"
    r = B.primary_test(d, np.zeros(len(c)), alternative="greater", outcome_type="continuous")
    assert r.n_used == 0 and r.p_value == 1.0 and math.isnan(r.estimate)


def test_one_sided_block_dropped_only_when_other_side_exists():
    # Gap of 1 bar between episodes: odd middle dropped, no control on that side.
    c = _cal("0011010000")
    d = B.build_blocks(c, merge_gap=0)
    assert [b.reason for b in d.blocks] == [B.DROP_ONE_SIDED, B.DROP_ONE_SIDED]
    # Episode at bar 0: no left side exists, so the right side alone is fine.
    c2 = _cal("1000000")
    (b,) = B.build_blocks(c2, merge_gap=0).blocks
    assert b.used and not b.left_exists and b.control_right.tolist() == [1]
    # ... but the ceil(n_active / 2) cap leaves it short of equal size (A1).
    (b,) = B.build_blocks(_cal("1100000"), merge_gap=0).blocks
    assert b.reason == B.DROP_UNBALANCED and b.control_right.tolist() == [2]


def test_equal_size_floor_amendment_a1():
    assert B.MIN_BALANCE == 1.0
    d = B.build_blocks(sim.balance_calendar(1.0, 10, n_active=8), merge_gap=0)
    assert d.n_used == 10
    assert all(b.balance == 1.0 for b in d.blocks)
    for balance in (0.5, 0.75):
        d = B.build_blocks(sim.balance_calendar(balance, 10, n_active=8), merge_gap=0)
        assert d.n_used == 0 and d.drop_counts[B.DROP_UNBALANCED] == 10


def test_odd_active_trims_farthest_control_bar():
    c = np.zeros(40, dtype=bool)
    c[10:15] = True  # 5 active -> cap 3 a side, 6 offered, trimmed to 5
    (b,) = B.build_blocks(c, merge_gap=0).blocks
    assert b.used and b.n_active == b.n_control == 5
    assert b.control_left.tolist() == [9, 8, 7]  # tie in distance: right is trimmed
    assert b.control_right.tolist() == [15, 16]
    assert b.active.tolist() == list(range(10, 15))  # active bars never trimmed
    # A gap on the left makes its third bar farther than the right's third bar.
    avail = np.ones(40, dtype=bool)
    avail[8] = False
    (b,) = B.build_blocks(c, merge_gap=0, available=avail).blocks
    assert b.control_left.tolist() == [9, 7]
    assert b.control_right.tolist() == [15, 16, 17]


def test_periodic_shapes_testable_only_with_room_for_equal_size():
    used = {}
    for (a, g), k in itertools.product(sim.PERIODIC_SHAPES, sim.PERIODIC_EPISODES):
        d = B.build_blocks(sim.periodic_calendar(a, g, k), merge_gap=0)
        used[(a, g, k)] = d.n_used
        assert d.n_used in (0, k)
        assert all(b.n_control == b.n_active for b in d.used_blocks)
    # Half-gap 2 vs 5 active, 2 vs 20, 5 vs 60: Untestable (A1 consequence).
    assert {key for key, n in used.items() if n == 0} == {
        (5, 5, 12), (5, 5, 18), (20, 5, 12), (20, 5, 18), (60, 10, 12), (60, 10, 18)}


def test_available_mask_skips_bars_and_counts_alike():
    c = np.zeros(30, dtype=bool)
    c[10:14] = True
    avail = np.ones(30, dtype=bool)
    avail[9] = False
    avail[12] = False
    (b,) = B.build_blocks(c, merge_gap=0, available=avail).blocks
    assert b.active.tolist() == [10, 11, 13]
    # Offered [8, 7] and [14, 15]; equal size trims bar 7 (3 bars away, 15 is 2).
    assert b.control_left.tolist() == [8]
    assert b.control_right.tolist() == [14, 15]
    y = np.arange(30, dtype=float)
    y[[9, 12]] = np.nan
    d = B.build_blocks(c, merge_gap=0, available=avail)
    B.primary_test(d, y, alternative="greater", outcome_type="continuous")
    # Without the mask the NaN bars are used: refused, never silently dropped (S-15).
    with pytest.raises(ValueError, match="available"):
        B.primary_test(B.build_blocks(c, merge_gap=0), y, alternative="greater",
                       outcome_type="continuous")


# ---------------------------------------------------------------- B4
def _random_calendar(rng, n):
    out = np.zeros(n, dtype=bool)
    i = int(rng.integers(0, 5))
    while i < n:
        on = int(rng.geometric(rng.uniform(0.05, 0.8)))
        out[i : i + on] = True
        i += on + int(rng.geometric(rng.uniform(0.05, 0.8)))
    return out


def test_b4_no_bar_in_two_blocks_property():
    rng = np.random.default_rng(cal.case_seed(BASE_SEED, "B4"))
    for _ in range(400):
        n = int(rng.integers(5, 400))
        c = _random_calendar(rng, n)
        if not c.any():
            continue
        avail = rng.random(n) > 0.05 if rng.random() < 0.5 else None
        mg = int(rng.integers(0, 4))
        guard = int(rng.integers(0, 3))
        d = B.build_blocks(c, merge_gap=mg, guard_bars=guard, available=avail)
        eps = episodes(c, mg)
        in_span = np.zeros(n, dtype=bool)
        for e in eps:
            in_span[e.start : e.end + 1] = True
        seen = np.zeros(n, dtype=np.int64)
        for k, b in enumerate(d.blocks):
            ctrl = b.control
            seen[b.active] += 1
            seen[ctrl] += 1
            assert not c[ctrl].any() and not in_span[ctrl].any()
            assert len(b.control_left) <= math.ceil(b.n_active / 2)
            assert len(b.control_right) <= math.ceil(b.n_active / 2)
            # Control bars lie in the episode's own half of each gap.
            ep = eps[k]
            if k > 0 and len(b.control_left):
                assert b.control_left.min() > (eps[k - 1].end + ep.start) / 2
            if k < len(eps) - 1 and len(b.control_right):
                assert b.control_right.max() < (ep.end + eps[k + 1].start) / 2
            if b.used:
                assert b.n_control == b.n_active  # A1: equal size
        assert seen.max() <= 1
        n_inactive = int((~c).sum())
        assert sum(b.n_control for b in d.blocks) <= n_inactive


def test_windows_design_refuses_shared_or_active_controls():
    c = _cal("000011000000110000")
    eps = episodes(c, 0)
    ok = B.design_from_windows(c, [([2, 3], [6, 7]), ([10, 11], [14, 15])], merge_gap=0)
    assert ok.n_used == 2 and ok.kind == "windows"
    # A1: 4 offered bars against 2 active, trimmed farthest first to 1 + 1.
    assert [(b.control_left.tolist(), b.control_right.tolist()) for b in ok.blocks] == [
        ([3], [6]), ([11], [14])]
    short = B.design_from_windows(c, [([3], []), ([10, 11], [14, 15])], merge_gap=0)
    assert short.blocks[0].reason == B.DROP_ONE_SIDED
    short = B.design_from_windows(c, [([3], [], True, False), ([10, 11], [14, 15])],
                                  merge_gap=0)
    assert short.blocks[0].reason == B.DROP_UNBALANCED  # 1 control bar vs 2 active
    with pytest.raises(ValueError, match="disjoint"):
        B.design_from_windows(c, [([2, 3], [6, 7]), ([7, 8], [14, 15])], merge_gap=0)
    with pytest.raises(ValueError, match="active"):
        B.design_from_windows(c, [([2, 4], [6, 7]), ([10, 11], [14, 15])], merge_gap=0)
    dropped = B.design_from_windows(c, [([2, 3], []), ([10, 11], [14, 15], True, False)], merge_gap=0)
    assert [b.reason for b in dropped.blocks] == [B.DROP_ONE_SIDED, None]
    assert len(eps) == 2


# ---------------------------------------------------------------- item 6
def test_year_unit_each_inactive_year_used_once():
    years = np.arange(1871, 2017)
    rng = np.random.default_rng(3)
    c = pd.Series(rng.random(len(years)) < 0.3, index=years)
    d = B.build_blocks(c, merge_gap=0)
    used = np.concatenate([np.concatenate((b.active, b.control)) for b in d.blocks])
    assert len(used) == len(np.unique(used))
    y = rng.normal(size=len(years))
    r = B.primary_test(d, pd.Series(y, index=years), alternative="less", outcome_type="continuous")
    assert r.n_used == d.n_used


# ---------------------------------------------------------------- items 7-9
def test_statistic_is_pooled_difference_and_weights():
    c = _cal("000111100000110000001111110000")
    d = B.build_blocks(c, merge_gap=0)
    rng = np.random.default_rng(5)
    y = rng.normal(size=len(c))
    r = B.primary_test(d, y, alternative="two-sided", outcome_type="continuous")
    w = np.array([b.n_active for b in d.used_blocks], dtype=float)
    dk = np.array([y[b.active].mean() - y[b.control].mean() for b in d.used_blocks])
    assert r.statistic == float(np.sum(w * dk) / np.sum(w))
    assert r.estimate == r.statistic  # card number is T (S-06)
    act = np.concatenate([b.active for b in d.used_blocks])
    ctrl_w = sum(b.n_active * y[b.control].mean() for b in d.used_blocks) / w.sum()
    assert r.statistic == pytest.approx(y[act].mean() - ctrl_w, abs=1e-12)
    assert r.k_eff == pytest.approx(w.sum() ** 2 / np.sum(w**2))
    assert d.k_eff == r.k_eff


def test_k_eff_one_long_episode_cannot_hide_short_ones():
    w = np.array([500.0] + [1.0] * 7)
    k_eff = w.sum() ** 2 / np.sum(w * w)
    assert k_eff < 1.1
    c = np.zeros(2000, dtype=bool)
    c[300:500] = True  # 200 active bars, equal size: 100 control bars a side
    for s in range(701, 2000, 150):
        c[s : s + 2] = True  # nine 2-bar episodes, 1 control bar a side
    d = B.build_blocks(c, merge_gap=0)
    assert d.blocks[0].used and d.n_used == 10
    assert d.blocks[0].n_control == 200
    assert d.k_eff < 1.2 < B.MIN_K_EFF


@pytest.mark.parametrize("otype", ["events", "flags"])
def test_ratio_estimate_and_same_p_as_t(otype):
    rng = np.random.default_rng(11)
    c = sim.periodic_calendar(6, 8, 10)
    if otype == "events":
        y = rng.poisson(0.4, size=len(c)).astype(float)
    else:
        y = (rng.random(len(c)) < 0.2).astype(float)
    d = B.build_blocks(c, merge_gap=0)
    r = B.primary_test(d, y, alternative="greater", outcome_type=otype)
    act = sum(y[b.active].sum() for b in d.used_blocks)
    ctl = sum(b.n_active * y[b.control].mean() for b in d.used_blocks)
    assert r.estimate == pytest.approx(act / ctl)
    assert r.estimate_scale == ("rate_ratio" if otype == "events" else "risk_ratio")
    # p of the ratio by brute force equals the p of T.
    ea = np.array([y[b.active].sum() for b in d.used_blocks])
    na = np.array([b.n_active for b in d.used_blocks], dtype=float)
    ec = np.array([b.n_active * y[b.control].mean() for b in d.used_blocks])
    obs = ea.sum() / ec.sum()
    hits = 0
    for signs in itertools.product([0, 1], repeat=len(ea)):
        s = np.array(signs, dtype=bool)
        num = np.where(s, ec, ea).sum()
        den = np.where(s, ea, ec).sum()
        hits += num / den >= obs - 1e-12
    assert r.p_value == pytest.approx(hits / 2 ** len(ea))
    assert np.allclose(na, r.weights)


def test_outcome_type_checks():
    c = sim.periodic_calendar(4, 6, 4)
    d = B.build_blocks(c, merge_gap=0)
    with pytest.raises(ValueError):
        B.primary_test(d, -np.ones(len(c)), alternative="greater", outcome_type="events")
    with pytest.raises(ValueError):
        B.primary_test(d, np.full(len(c), 2.0), alternative="greater", outcome_type="flags")
    with pytest.raises(ValueError):
        B.primary_test(d, np.zeros(len(c)), alternative="greater", outcome_type="bp")


# ---------------------------------------------------------------- item 10
def test_no_default_side():
    params = inspect.signature(B.primary_test).parameters
    assert params["alternative"].default is inspect.Parameter.empty
    assert inspect.signature(B.weighted_sign_flip).parameters["alternative"].default is inspect.Parameter.empty
    c = sim.periodic_calendar(4, 6, 4)
    d = B.build_blocks(c, merge_gap=0)
    with pytest.raises(TypeError):
        B.primary_test(d, np.zeros(len(c)), outcome_type="continuous")
    with pytest.raises(ValueError):
        B.primary_test(d, np.zeros(len(c)), alternative="either", outcome_type="continuous")
    with pytest.raises(ValueError):
        d.gate_summary(None)
    assert B.alternative_for("increase") == "greater"
    assert B.alternative_for("up") == "greater"
    assert B.alternative_for("decrease") == "less"
    assert B.alternative_for("down") == "less"
    assert B.alternative_for("either") == "two-sided"
    with pytest.raises(ValueError):
        B.alternative_for(None)


@pytest.mark.parametrize("alternative", B.ALTERNATIVES)
def test_exact_enumeration_matches_brute_force(alternative):
    rng = np.random.default_rng(7)
    d = rng.exponential(size=9) - 0.8
    w = rng.integers(1, 6, size=9).astype(float)
    sf = B.weighted_sign_flip(d, w, alternative=alternative)
    obs = np.sum(w * d) / w.sum()
    stats = np.array([np.sum(np.array(s) * w * d) / w.sum()
                      for s in itertools.product([-1, 1], repeat=9)])
    if alternative == "greater":
        p = np.mean(stats >= obs - 1e-12)
    elif alternative == "less":
        p = np.mean(stats <= obs + 1e-12)
    else:
        p = np.mean(np.abs(stats) >= abs(obs) - 1e-12)
    assert sf.exact_enumeration and sf.p_value == pytest.approx(p)
    assert sf.p_min == (2 if alternative == "two-sided" else 1) / 2**9


def test_equal_weights_match_old_unweighted_sign_flip():
    rng = np.random.default_rng(8)
    d = rng.normal(size=11)
    old = sign_flip_test(d, alternative="greater")
    new = B.weighted_sign_flip(d, np.ones(11), alternative="greater")
    assert new.p_value == pytest.approx(old.p_value)


def test_monte_carlo_above_twenty_blocks_needs_rng_and_has_floor():
    d = np.ones(25)
    with pytest.raises(ValueError, match="rng"):
        B.weighted_sign_flip(d, np.ones(25), alternative="greater")
    sf = B.weighted_sign_flip(d, np.ones(25), alternative="greater",
                              rng=np.random.default_rng(1), n_draws=999)
    assert not sf.exact_enumeration
    assert sf.p_value == pytest.approx(1 / 1000)  # only the observed pattern
    assert sf.p_min == 1 / 1000
    a = B.weighted_sign_flip(np.arange(25) - 12.0, np.ones(25), alternative="two-sided",
                             rng=np.random.default_rng(2), n_draws=500)
    b = B.weighted_sign_flip(np.arange(25) - 12.0, np.ones(25), alternative="two-sided",
                             rng=np.random.default_rng(2), n_draws=500)
    assert a.p_value == b.p_value


# ---------------------------------------------------------------- B6 and spy
def test_b6_gate_and_test_report_same_side_and_blocks():
    # Hand-built: a low-balance block, two one-sided blocks, three good ones.
    c = _cal("0001100000" "1111111111" "00" "11" "0" "11" "000000" "11000000110000001100")
    d = B.build_blocks(c, merge_gap=0)
    assert d.drop_counts[B.DROP_LOW_BALANCE] == 1
    assert d.drop_counts[B.DROP_ONE_SIDED] == 2
    assert d.n_used == 4
    y = np.random.default_rng(9).normal(size=len(c))
    for alt in B.ALTERNATIVES:
        gate = d.gate_summary(alt)
        r = B.primary_test(d, y, alternative=alt, outcome_type="continuous")
        assert r.gate_summary() == gate
        assert r.alternative == alt
        assert r.n_used + r.n_dropped == r.n_episodes == len(episodes(c, 0))
        assert sum(gate["drop_counts"].values()) == gate["n_dropped"]
    cal.property_result("B6", "hand-built", True)


def test_spy_blocks_are_built_without_reading_an_outcome(monkeypatch):
    assert "outcome" not in inspect.signature(B.build_blocks).parameters
    reads = []
    real = B._outcome_values

    def spy(*a, **k):
        reads.append(1)
        return real(*a, **k)

    monkeypatch.setattr(B, "_outcome_values", spy)
    c = sim.periodic_calendar(5, 5, 12)
    d = B.build_blocks(c, merge_gap=0)
    d.gate_summary("greater")
    d.table()
    assert reads == []
    before = d.design_id
    B.primary_test(d, np.zeros(len(c)), alternative="greater", outcome_type="continuous")
    assert reads == [1]
    assert d.design_id == before  # the test does not rebuild or alter the design


# ---------------------------------------------------------------- Amendment A2
PLAN_SEED = BASE_SEED


def test_a2_off_without_seed_keeps_a1_design():
    c = _cal("0011000111000010")
    a1 = B.build_blocks(c, merge_gap=0)
    again = B.build_blocks(c, merge_gap=0, side_seed=None)
    assert a1.design_id == again.design_id and a1.side_seed is None
    assert a1.n_one_sided == 0
    a2 = B.build_blocks(c, merge_gap=0, side_seed=PLAN_SEED)
    assert a2.design_id != a1.design_id
    # The single bar at 14 is testable under A2, from one side only.
    b2 = a2.blocks[2]
    assert b2.used and b2.n_control == 1 and b2.side_rule == B.SIDE_ALTERNATED
    # Two-bar blocks with room on both sides are unchanged.
    for k in (0, 1):
        assert a2.blocks[k].control.tolist() == a1.blocks[k].control.tolist()
        assert a2.blocks[k].one_sided is None


def test_a2_start_side_is_fixed_by_the_seed_alone():
    sides = {B.start_side(s) for s in range(64)}
    assert sides == {B.SIDE_LEFT, B.SIDE_RIGHT}
    assert B.start_side(PLAN_SEED) == B.start_side(PLAN_SEED)
    assert B.start_side("plan-7") == B.start_side("plan-7")
    for bad in (None, True, 1.5):
        with pytest.raises(ValueError):
            B.start_side(bad)
    with pytest.raises(ValueError):
        B.build_blocks(_cal("0010100"), merge_gap=0, side_seed=2.0)


def _seed_starting(side):
    return next(s for s in range(100) if B.start_side(s) == side)


@pytest.mark.parametrize("first", [B.SIDE_LEFT, B.SIDE_RIGHT])
def test_a2_single_bars_alternate_in_calendar_order(first):
    c = sim.periodic_calendar(1, 4, 9)  # lead 2, single bars, half-gap 2
    d = B.build_blocks(c, merge_gap=0, side_seed=_seed_starting(first))
    assert d.n_used == 9 and d.n_one_sided == 9
    want = [first if k % 2 == 0 else B._other(first) for k in range(9)]
    assert [b.one_sided for b in d.blocks] == want
    for b in d.blocks:
        assert b.side_rule == B.SIDE_ALTERNATED and b.n_control == b.n_active == 1
        a = int(b.active[0])
        # The nearest bar of the chosen side, never a bar past the half-gap.
        assert b.control.tolist() == ([a - 1] if b.one_sided == B.SIDE_LEFT else [a + 1])
    assert d.table()["one_sided"].tolist() == want


def test_a2_forced_side_when_the_other_is_unavailable():
    # Gap of 1 bar between episodes: odd middle dropped, that side is empty.
    c = _cal("0011010000")
    d = B.build_blocks(c, merge_gap=0, side_seed=_seed_starting(B.SIDE_RIGHT))
    b0, b1 = d.blocks
    assert b0.used and b0.one_sided == B.SIDE_LEFT and b0.side_rule == B.SIDE_FORCED
    assert b0.control_left.tolist() == [1, 0] and len(b0.control_right) == 0
    # Forced blocks do not use up the alternation; b1 is forced anyway.
    assert b1.used and b1.one_sided == B.SIDE_RIGHT and b1.control_right.tolist() == [6]
    # Edge episode: no left side; the right side gives all n_active bars.
    (b,) = B.build_blocks(_cal("1100000"), merge_gap=0, side_seed=1).blocks
    assert b.used and b.one_sided == B.SIDE_RIGHT and b.control_right.tolist() == [2, 3]
    (b,) = B.build_blocks(_cal("0000111"), merge_gap=0, side_seed=1).blocks
    assert b.used and b.one_sided == B.SIDE_LEFT and b.control_left.tolist() == [3, 2, 1]
    # Too few bars on the one side: unbalanced, not a smaller block.
    (b,) = B.build_blocks(_cal("11110"), merge_gap=0, side_seed=1).blocks
    assert b.reason == B.DROP_UNBALANCED
    # Guard bars and unavailable bars make a side unavailable too.
    c = _cal("0000011" "0" "11" "000000")
    d = B.build_blocks(c, merge_gap=0, guard_bars=1, side_seed=1)
    assert d.blocks[0].control_left.tolist() == [3, 2]
    assert d.blocks[1].control_right.tolist() == [11, 12]
    avail = np.ones(12, dtype=bool)
    avail[[4, 3, 2, 1, 0]] = False
    (b,) = B.build_blocks(_cal("000001100000"), merge_gap=0, available=avail,
                          side_seed=1).blocks
    assert b.one_sided == B.SIDE_RIGHT and b.control_right.tolist() == [7, 8]


def test_a2_forced_blocks_do_not_shift_the_alternation():
    # single, forced-right (no room on its left), single, single
    c = _cal("00100" "1" "0" "1" "000" "1" "000" "1" "00")
    d = B.build_blocks(c, merge_gap=0, side_seed=_seed_starting(B.SIDE_LEFT))
    rules = [(b.one_sided, b.side_rule) for b in d.blocks]
    assert rules[0] == (B.SIDE_LEFT, B.SIDE_ALTERNATED)
    assert rules[1][1] == B.SIDE_FORCED and rules[2][1] == B.SIDE_FORCED
    assert rules[3] == (B.SIDE_RIGHT, B.SIDE_ALTERNATED)
    assert rules[4] == (B.SIDE_LEFT, B.SIDE_ALTERNATED)


def test_a2_longer_runs_with_both_sides_stay_two_sided():
    # 5 active bars, half-gaps of 2 on both sides: A1 drops it, A2 does too
    # (one side is taken only for a single bar or an unavailable side).
    c = sim.periodic_calendar(5, 5, 12)
    d = B.build_blocks(c, merge_gap=0, side_seed=PLAN_SEED)
    assert d.n_used == 0 and d.drop_counts[B.DROP_UNBALANCED] == 12
    c = sim.periodic_calendar(6, 8, 6)
    a1, a2 = (B.build_blocks(c, merge_gap=0, side_seed=s) for s in (None, PLAN_SEED))
    assert [b.control.tolist() for b in a1.blocks] == [b.control.tolist() for b in a2.blocks]
    assert a2.n_one_sided == 0


def test_a2_windows_design_takes_one_side_too():
    c = _cal("000010000000100000")
    wins = [([3], [5]), ([11], [13])]
    assert B.design_from_windows(c, wins, merge_gap=0).n_used == 0  # A1
    d = B.design_from_windows(c, wins, merge_gap=0, side_seed=_seed_starting(B.SIDE_RIGHT))
    assert [b.control.tolist() for b in d.blocks] == [[5], [11]]
    assert [b.one_sided for b in d.blocks] == [B.SIDE_RIGHT, B.SIDE_LEFT]
    d = B.design_from_windows(c, [([3], []), ([], [13])], merge_gap=0, side_seed=1)
    assert [b.side_rule for b in d.blocks] == [B.SIDE_FORCED, B.SIDE_FORCED]
    with pytest.raises(ValueError, match="disjoint"):
        B.design_from_windows(c, [([3], [5]), ([5], [13])], merge_gap=0, side_seed=1)


def test_a2_b4_no_bar_in_two_blocks_property():
    rng = np.random.default_rng(cal.case_seed(BASE_SEED, "B4", "A2"))
    for _ in range(400):
        n = int(rng.integers(5, 400))
        c = _random_calendar(rng, n)
        if not c.any():
            continue
        avail = rng.random(n) > 0.05 if rng.random() < 0.5 else None
        mg = int(rng.integers(0, 4))
        guard = int(rng.integers(0, 3))
        d = B.build_blocks(c, merge_gap=mg, guard_bars=guard, available=avail,
                           side_seed=int(rng.integers(0, 1000)))
        eps = episodes(c, mg)
        in_span = np.zeros(n, dtype=bool)
        for e in eps:
            in_span[e.start : e.end + 1] = True
        seen = np.zeros(n, dtype=np.int64)
        for k, b in enumerate(d.blocks):
            ctrl = b.control
            seen[b.active] += 1
            seen[ctrl] += 1
            assert not c[ctrl].any() and not in_span[ctrl].any()
            if guard and len(ctrl):
                assert np.abs(ctrl[:, None] - np.array([eps[k].start, eps[k].end])).min() > guard
            ep = eps[k]
            if k > 0 and len(b.control_left):
                assert b.control_left.min() > (eps[k - 1].end + ep.start) / 2
            if k < len(eps) - 1 and len(b.control_right):
                assert b.control_right.max() < (ep.end + eps[k + 1].start) / 2
            if b.used:
                assert b.n_control == b.n_active
                if b.one_sided is None:
                    cap = math.ceil(b.n_active / 2)
                    assert len(b.control_left) <= cap and len(b.control_right) <= cap
                else:
                    assert (len(b.control_left) == 0) != (len(b.control_right) == 0)
                    if b.side_rule == B.SIDE_ALTERNATED:
                        assert b.n_active == 1
            # A2 never drops a block as one_sided.
            assert b.reason != B.DROP_ONE_SIDED
        assert seen.max() <= 1
        assert sum(b.n_control for b in d.blocks) <= int((~c).sum())
    cal.property_result("B4", "A2 random calendars", True)


def test_a2_b6_and_spy_side_is_chosen_without_an_outcome(monkeypatch):
    reads = []
    real = B._outcome_values
    monkeypatch.setattr(B, "_outcome_values", lambda *a, **k: (reads.append(1), real(*a, **k))[1])
    c = _cal("0010001000100" "0111100000" "100")
    d = B.build_blocks(c, merge_gap=0, side_seed=PLAN_SEED)
    gate = d.gate_summary("less")
    assert reads == [] and d.n_one_sided >= 4
    y = np.random.default_rng(1).normal(size=len(c))
    r = B.primary_test(d, y, alternative="less", outcome_type="continuous")
    assert r.gate_summary() == gate and reads == [1]


# ---------------------------------------------------------------- B1 to B3, B5 runners
def _rejections(calendar, draw, reps, seed, alternative="greater", n_draws=999,
                side_seed=None, transform=None):
    """Rejections at one-sided 5% of the primary test, no effect planted.

    ``side_seed`` switches on Amendment A2; ``transform`` is applied to each
    simulated outcome before the test (the detrending baseline of A2).
    """
    rng = np.random.default_rng(seed)
    d = B.build_blocks(calendar, merge_gap=0, side_seed=side_seed)
    if d.n_used == 0:
        return 0, d  # Untestable: never rejects
    hits = 0
    for _ in range(int(reps)):
        y = draw(len(calendar), rng)
        if transform is not None:
            y = transform(y)
        r = B.primary_test(d, y, alternative=alternative, outcome_type="continuous",
                           rng=rng, n_draws=n_draws)
        hits += r.p_value <= ALPHA
    return hits, d


def _bars(kind):
    return lambda n, rng: sim.continuous_bars(kind, n, rng)


def _b3_generators():
    return {
        "garch": lambda n, rng: sim.garch11_normal(n, rng, **sim.B3_GARCH),
        "regimes": lambda n, rng: sim.regime_bars(n, rng),
        "ar1_0.1": lambda n, rng: sim.ar1(n, rng, 0.1),
        "ar1_0.3": lambda n, rng: sim.ar1(n, rng, 0.3),
    }


def run_b1(reps, fast=False, shapes=sim.PERIODIC_SHAPES, counts=sim.PERIODIC_EPISODES, only=None):
    out = []
    for (a, g), k in itertools.product(shapes, counts):
        cell = f"{a}/{g} K={k}"
        if only is not None and cell not in only:
            continue
        hits, _ = _rejections(sim.periodic_calendar(a, g, k), _bars("normal"), reps,
                              cal.case_seed(BASE_SEED, "B1", cell))
        out.append(cal.evaluate("B1", cell, hits, reps, fast=fast))
    return out


def run_b2(reps, fast=False, shapes=sim.PERIODIC_SHAPES, counts=sim.PERIODIC_EPISODES,
           kinds=sim.SKEWED_KINDS, only=None):
    out = []
    for (a, g), k, kind in itertools.product(shapes, counts, kinds):
        cell = f"{kind} {a}/{g} K={k}"
        if only is not None and cell not in only:
            continue
        hits, _ = _rejections(sim.periodic_calendar(a, g, k), _bars(kind), reps,
                              cal.case_seed(BASE_SEED, "B2", cell))
        out.append(cal.evaluate("B2", cell, hits, reps, fast=fast))
    return out


def run_b3(reps, fast=False, shapes=sim.PERIODIC_SHAPES, counts=sim.PERIODIC_EPISODES,
           real=("mercury_retrograde", "moon_nakshatra_group", "tithi_group", "eclipse_window"),
           generators=None, only=None):
    gens = _b3_generators() if generators is None else generators
    out = []
    cals = [(f"{a}/{g} K={k}", sim.periodic_calendar(a, g, k))
            for (a, g), k in itertools.product(shapes, counts)]
    if real:
        frame = sim.daily_calendars()
        cals += [(name, frame[name].to_numpy()) for name in real]
    for (cname, c), (gname, gen) in itertools.product(cals, gens.items()):
        cell = f"{gname} {cname}"
        if only is not None and cell not in only:
            continue
        hits, _ = _rejections(c, gen, reps, cal.case_seed(BASE_SEED, "B3", cell))
        out.append(cal.evaluate("B3", cell, hits, reps, fast=fast))
    return out


def run_b5(reps, shapes=((5, 5), (20, 5)), k=12):
    """Old episode_differences with shared neighbour windows (appendix A.2)."""
    out = []
    for a, g in shapes:
        cell = f"{a}/{g} K={k}"
        c = sim.periodic_calendar(a, g, k)
        rng = np.random.default_rng(cal.case_seed(BASE_SEED, "B5", cell))
        hits = 0
        for _ in range(int(reps)):
            y = rng.standard_normal(len(c))
            dd = episode_differences(c, y, merge_gap=0)["difference"]
            hits += sign_flip_test(dd, alternative="greater").p_value <= ALPHA
        out.append(cal.evaluate("B5", cell, hits, reps))
    return out


# ---------------------------------------------------------------- A2 runners
#: Daily-event calendars of A2: tithi numbers at noon UTC (30 = new moon).
A2_TITHIS = {"new_moon": 30, "tithi_11": 11, "full_moon": 15}
A2_REAL = ("new_moon", "tithi_11", "full_moon", "tithi_group", "eclipse_window")
#: Drift (A2): slope per bar and random-walk step, in noise standard deviations.
DRIFT_SLOPE = 0.02
DRIFT_STEP = 0.05
DETREND_WINDOW = 31


@functools.lru_cache(maxsize=1)
def _tithi_frame():
    from vedic_astrology_core.markets.align import sample_instants
    from vedic_astrology_core.markets.features import indicator_frame

    dates = pd.date_range(*sim.DAILY_GRID, freq="D")
    f = indicator_frame(sample_instants(dates, "12:00", "UTC"), ["SUN", "MOON"])
    return dates, f["tithi"].to_numpy()


def a2_daily_calendar(name):
    """Daily-event calendar on the 1968-1998 noon grid (committed ephemeris only)."""
    if name in A2_TITHIS:
        _, tithi = _tithi_frame()
        return tithi == A2_TITHIS[name]
    return sim.daily_calendars()[name].to_numpy()


def a2_synthetic_calendars(counts=sim.PERIODIC_EPISODES):
    """Single-bar and edge shapes that A1 drops and A2 keeps."""
    out = {}
    for k in counts:
        out[f"1/4 K={k}"] = sim.periodic_calendar(1, 4, k)  # alternated single bars
        out[f"1/29 K={k}"] = sim.periodic_calendar(1, 29, k)  # new-moon-like
        # 3-bar runs with alternating gaps of 1 and 8: every block forced one-sided.
        body = []
        for i in range(k):
            body += [True] * 3 + [False] * (1 if i % 2 == 0 else 8)
        out[f"forced 3/1,8 K={k}"] = np.asarray([False] * 4 + body[:-1] + [False] * 4)
        # Edge episodes on the grid's edges: one-sided at both ends.
        out[f"edge 5/10 K={k}"] = sim.periodic_calendar(5, 10, k, lead=0, trail=0)
    return out


def _drift(n, rng):
    t = np.arange(n, dtype=float)
    return rng.standard_normal(n) + DRIFT_SLOPE * t + np.cumsum(rng.normal(0, DRIFT_STEP, n))


def detrend(y, window=DETREND_WINDOW):
    """Detrending baseline of the A2 drift case: minus a centred running mean."""
    s = pd.Series(np.asarray(y, dtype=float))
    return (s - s.rolling(int(window), center=True, min_periods=1).mean()).to_numpy()


def a2_generators():
    """(case, generator name) -> (draw, transform) for B1, B2, B3 and drift."""
    gens = {("B1", "normal"): (_bars("normal"), None)}
    for kind in sim.SKEWED_KINDS:
        gens[("B2", kind)] = (_bars(kind), None)
    for name, g in _b3_generators().items():
        gens[("B3", name)] = (g, None)
    # Drift case of A2 (D1 in the amendment; filed under B3 because the
    # certificate's D1 id is the monthly-average guard case of section 8).
    gens[("B3", "drift_detrended")] = (_drift, detrend)
    return gens


def a2_cells(real=A2_REAL, synthetic=True, counts=sim.PERIODIC_EPISODES):
    """Every (case, generator, calendar) cell of the A2 full-size run."""
    cals = [(name, functools.partial(a2_daily_calendar, name)) for name in real]
    if synthetic:
        cals += [(name, (lambda c: (lambda: c))(c))
                 for name, c in a2_synthetic_calendars(counts).items()]
    return [(case, gname, cname, make) for (case, gname), (cname, make)
            in itertools.product(a2_generators(), cals)]


def run_a2_cell(case, gname, cname, make, reps, fast=False, side_seed=PLAN_SEED):
    draw, transform = a2_generators()[(case, gname)]
    cell = f"A2 {gname} {cname}"
    hits, d = _rejections(make(), draw, reps, cal.case_seed(BASE_SEED, case, cell),
                          side_seed=side_seed, transform=transform)
    return cal.evaluate(case, cell, hits, reps, fast=fast), d


def run_a2(reps, fast=False, **kw):
    return [run_a2_cell(*cell, reps, fast=fast)[0] for cell in a2_cells(**kw)]


def test_a2_daily_event_calendars_are_testable():
    for name in A2_REAL:
        c = a2_daily_calendar(name)
        a1 = B.build_blocks(c, merge_gap=0)
        a2 = B.build_blocks(c, merge_gap=0, side_seed=PLAN_SEED)
        assert a2.n_used >= a1.n_used and a2.k_eff >= B.MIN_K_EFF, name
        if name in A2_TITHIS:  # single-day runs: A1 drops most, A2 keeps them
            assert a2.n_used > a1.n_used and a2.n_one_sided > 0, name


def test_a2_fast():
    keep = {("B1", "normal"), ("B2", "lognormal"), ("B3", "garch"), ("B3", "drift_detrended")}
    cells = [cell for cell in a2_cells(real=("new_moon",), counts=(12,))
             if cell[:2] in keep and (cell[2] == "new_moon" or cell[2].startswith(("1/4", "forced")))]
    assert len(cells) == 12
    _assert_fast(lambda reps, only=None: [run_a2_cell(*cell, reps, fast=True)[0] for cell in cells
                                          if only is None or f"A2 {cell[1]} {cell[2]}" in only])


def _assert_all(results):
    failed = [(r.cell, r.count, r.replications) for r in results if not r.passed]
    assert not failed, failed


#: REVIEW_1 fix 2: a fast cell is judged on its upper Clopper-Pearson bound
#: (fast mark 0.085: at 400 replications, 24 rejections or fewer). A cell that
#: misses it is inconclusive and is decided on more replications of the same
#: seeded stream (the first 400 included), still on the bound and the same mark.
ESCALATED_REPS = 2_000


def _assert_fast(run):
    """``run(reps, only=None)`` gives fast results; inconclusive cells are re-run at ESCALATED_REPS."""
    first = run(FAST_REPS)
    bad = {r.cell for r in first if not r.passed}
    results = [r for r in first if r.passed]
    if bad:
        again = run(ESCALATED_REPS, only=bad)
        assert {r.cell for r in again} == bad
        results += again
    _assert_all(results)


def test_b1_fast():
    _assert_fast(lambda reps, only=None: run_b1(reps, fast=True, shapes=((5, 50), (20, 20), (20, 5)),
                                                counts=(12,), only=only))


def test_b2_fast():
    _assert_fast(lambda reps, only=None: run_b2(reps, fast=True, shapes=((20, 20), (5, 50)), counts=(12,),
                                                kinds=("lognormal", "zero_inflated"), only=only))


def test_b3_fast():
    gens = _b3_generators()
    _assert_fast(lambda reps, only=None: run_b3(reps, fast=True, shapes=((20, 20),), counts=(12,),
                                                real=("mercury_retrograde",),
                                                generators={"garch": gens["garch"], "ar1_0.3": gens["ar1_0.3"]},
                                                only=only))


def test_review1_daily_moon_cells_hold_size():
    """REVIEW_1 fix 3: B3 AR(1) 0.3 and GARCH on the daily Moon-nakshatra and tithi calendars (A2 blocks).

    The certificate's fast cells read 31/400 and 29/400 (Moon) and 26/400
    (tithi; checked at full size outside pytest, too slow here). Re-run at 10,000 replications through the same pipeline path and
    seeds (REVIEW_1 R1-SIZE report): 506/10,000 for AR(1) 0.3 on the Moon
    calendar, so the fast rates were sampling noise of the first 400 seeds.
    The design explains why: single-day blocks 5 to 9 days apart, so block
    differences are nearly uncorrelated under AR(1) 0.3 (lag-1 correlation of
    consecutive block differences about 0.003), and exactly sign-symmetric
    under symmetric GARCH (negating a block's innovations leaves every
    variance unchanged). This keeps the cells in the fast suite on the bound.
    """
    gens = a2_generators()
    cells = [(case, g, name, functools.partial(a2_daily_calendar, name))
             for (case, g) in (("B3", "ar1_0.3"), ("B3", "garch"))
             for name in ("moon_nakshatra_group",)]
    assert all((c[0], c[1]) in gens for c in cells)
    _assert_fast(lambda reps, only=None: [run_a2_cell(*cell, reps, fast=True)[0] for cell in cells
                                          if only is None or f"A2 {cell[1]} {cell[2]}" in only])


def test_b5_old_design_still_fails():
    # Documents the S-02 loophole: shared neighbour windows inflate the size.
    _assert_all(run_b5(2000))


def test_20_over_5_is_untestable_not_rejected():
    hits, d = _rejections(sim.periodic_calendar(20, 5, 12), _bars("normal"), 10, 1)
    assert hits == 0 and d.n_used == 0


@pytest.mark.skipif(not FULL, reason="full calibration runs in the certificate suite")
def test_full_b2_equal_size():
    # Amendment A1: B2 must pass at full size before any certificate is issued.
    _assert_all(run_b2(10_000))


@pytest.mark.skipif(not FULL, reason="full calibration runs in the certificate suite")
def test_full_a2_daily_events():
    # Amendment A2: B1, B2, B3 and the drift case at full size for daily-event
    # calendars and the single-bar and edge shapes, one-sided blocks on.
    _assert_all(run_a2(10_000))


@pytest.mark.skipif(not FULL, reason="full calibration runs in the certificate suite")
def test_full_b_cases():
    results = (run_b1(10_000) + run_b2(10_000) + run_b3(10_000) + run_b5(10_000))
    _assert_all(results)


# ------------------------------------------------- CALIBRATION-FIX (WP-98 B2)
def test_constant_raw_block_has_zero_difference():
    c = _cal("0001110000001110000001110000")  # odd runs: 2 + 1 control bars, a time offset
    d = B.build_blocks(c, merge_gap=0, side_seed=1)
    assert d.n_used == 3
    raw = np.zeros(len(c))
    raw[13] = 2.0  # an active bar of block 1; blocks 0 and 2 are all zero
    resid = raw - 0.01 * np.arange(len(c))  # a fitted trend leaves a residue everywhere
    plain = B.block_differences(d, resid, outcome_type="continuous")
    assert (np.abs(plain.d) > 0).all()  # the residue alone looks like signal
    fixed = B.block_differences(d, resid, outcome_type="continuous", raw=raw)
    assert fixed.constant.tolist() == [True, False, True]
    assert fixed.d[0] == 0.0 and fixed.d[2] == 0.0 and fixed.d[1] == plain.d[1]
    r = B.primary_test(d, resid, alternative="greater", outcome_type="continuous", raw=raw)
    assert r.statistic == fixed.statistic and r.p_value == 0.5  # one informative block of three
    with pytest.raises(ValueError, match="raw"):
        B.block_differences(d, resid, outcome_type="continuous", raw=raw[:-1])


@pytest.mark.parametrize("first", [B.SIDE_LEFT, B.SIDE_RIGHT])
def test_odd_blocks_alternate_the_extra_control_bar(first):
    c = sim.periodic_calendar(5, 6, 6)  # 5 active bars, 3 + 3 offered: one trim by a distance tie
    seed = _seed_starting(first)
    d = B.build_blocks(c, merge_gap=0, side_seed=seed)
    inner = [b for b in d.used_blocks if b.left_exists and b.right_exists and b.one_sided is None]
    sides = [(len(b.control_left), len(b.control_right)) for b in inner]
    assert all(b.n_control == b.n_active == 5 for b in inner)
    assert set(sides) == {(3, 2), (2, 3)}
    assert all(sides[k] != sides[k + 1] for k in range(len(sides) - 1))  # alternate in calendar order
    a1 = B.build_blocks(c, merge_gap=0)  # A1 rule unchanged without the plan seed: right always trimmed
    assert {(len(b.control_left), len(b.control_right)) for b in a1.used_blocks
            if b.left_exists and b.right_exists} == {(3, 2)}
