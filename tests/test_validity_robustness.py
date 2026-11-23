"""ADR-008 WP-94: the robustness contract of section 5 (A-01, F-07) and section 7.3.

R2 per test on its own statistic T; a placebo kind applies only when it
changes at least 1% of the active bars; tropical is a rival system (sensitivity
grid only); 200 time-shift skies, whole years for season-linked calendars;
pass at (1 + strictly larger) / (n + 1) <= 0.05. R3 counts distinct calendars
(at least 5% of active bars changed). R1 with baselines, R4 by baseline_r2.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from vedic_astrology_core.stats import blocks as B
from vedic_astrology_core.stats import season as Z
from vedic_astrology_core.validity import family as fam
from vedic_astrology_core.validity import robustness as R
from vedic_astrology_core.validity.calibration import clopper_pearson_upper

N = 6000
DAYS = np.arange(N, dtype=float)


def phase_calendar(period, width, offset=0.0, phase0=0.13):
    """Active when the phase of a cycle of length period (days) is below width (a share)."""
    return ((DAYS + offset) / period + phase0) % 1.0 < width


def nakshatra(offset=0.0):
    # Two days a sidereal month on a daily grid: under Amendment A1 a one-bar
    # episode cannot reach equal size on both sides and is dropped.
    return phase_calendar(27.321661, 2.0 / 27.0, offset)


def tithi(offset=0.0):
    return phase_calendar(29.530589, 1.0 / 15.0, offset, phase0=0.41)


def orb_conjunction(offset=0.0):
    # Two bodies with a synodic period of about 400 days, within a 15-degree orb.
    p = ((DAYS + offset) / 398.9 + 0.2) % 1.0
    return (p < 15 / 360) | (p > 1 - 15 / 360)


def stat(calendar, y):
    design = B.build_blocks(calendar, merge_gap=1)
    return B.block_differences(design, y, outcome_type="continuous").statistic


def placebos_for(make, y, rng, scramble_unchanged=True):
    real_cal = make()
    out = []
    plan = R.time_shift_plan(False, rng)
    assert plan["kind"] == "random_offset" and len(plan["shifts"]) == 200
    for off in plan["shifts"]:
        c = make(float(off))
        out.append(R.Placebo("time_shift", stat(c, y), R.changed_share(real_cal, c), label=str(off)))
    if scramble_unchanged:
        # Scrambling sign labels leaves a nakshatra, tithi or degree-orb calendar unchanged.
        t_real = stat(real_cal, y)
        out.extend(R.Placebo("scramble", t_real, R.changed_share(real_cal, real_cal)) for _ in range(20))
    return out


@pytest.mark.parametrize("make", [nakshatra, tithi, orb_conjunction], ids=["nakshatra", "tithi", "orb"])
def test_label_free_calendars_with_a_strong_effect_pass_r2(make):
    rng = np.random.default_rng(5)
    cal = make()
    y = rng.normal(size=N)
    y[cal] += 1.0
    t = stat(cal, y)
    res = R.r2_placebo(t, placebos_for(make, y, fam.stream_rng(1, make.__name__, "placebo")), "greater")
    assert res.passes, res
    assert res.not_applicable_kinds == ("scramble",)
    assert res.applicable_kinds == ("time_shift",)
    assert res.n_placebo == 200


def test_ties_are_mid_rank_unless_the_sky_is_identical():
    # N-06 (ii): a different calendar tied with the real statistic counts one half.
    res = R.r2_placebo(0.7, [R.Placebo("time_shift", 0.7, 0.5)] * 200, "greater")
    assert res.n_tied == 200 and res.n_larger == 0 and not res.passes
    assert res.p_value == pytest.approx(101 / 201)
    # The audit's probe: 150 tied and 50 lower gave p = 0.005 under "ties never count".
    probe = R.r2_placebo(1.0, [R.Placebo("time_shift", 1.0, 0.3)] * 150 + [R.Placebo("time_shift", 0.0, 0.3)] * 50,
                         "greater")
    assert probe.p_value == pytest.approx(76 / 201) and not probe.passes
    # A sky identical to the real calendar (changed share 0) is not counted as a tie.
    same = [R.Placebo("time_shift", 1.0, 0.0)] * 5 + [R.Placebo("time_shift", 0.0, 0.3)] * 195
    assert R.r2_placebo(1.0, same, "greater").p_value == pytest.approx(1 / 201)
    # Cluster weighting uses the same half count.
    cl = [R.Placebo("time_shift", 1.0, 0.3, cluster=0), R.Placebo("time_shift", 0.0, 0.3, cluster=0)]
    cl += [R.Placebo("time_shift", 0.0, 0.3, cluster=1 + i) for i in range(19)]
    assert R.r2_placebo(1.0, cl, "greater", n_distinct=20).p_value == pytest.approx(1.25 / 21)


def test_r2_null_rate_with_tied_discrete_statistics_10000_runs():
    """N-06 (ii): a discrete statistic (many ties) under no effect passes R2 in at most 5%."""
    rng = np.random.default_rng(2611)
    n_runs = 10_000
    sims = rng.poisson(0.3, size=(n_runs, 201)).astype(float)
    passes = 0
    for row in sims:
        pls = [R.Placebo("time_shift", float(v), 0.5) for v in row[1:]]
        passes += R.r2_placebo(float(row[0]), pls, "greater").passes
    assert clopper_pearson_upper(passes, n_runs) <= 0.06, passes


def test_r2_boundaries():
    def run(k, n, side="greater", real=1.0):
        larger = 2.0 if side != "less" else -2.0
        smaller = 0.0
        pls = [R.Placebo("time_shift", larger, 0.3)] * k + [R.Placebo("time_shift", smaller, 0.3)] * (n - k)
        if side == "less":
            real = -1.0
        return R.r2_placebo(real, pls, side)

    assert run(9, 199).p_value == pytest.approx(0.05) and run(9, 199).passes  # equal to 0.05 passes
    assert not run(10, 199).passes
    assert run(9, 200).passes and not run(10, 200).passes
    assert run(9, 199, "less").passes and not run(10, 199, "less").passes
    two = R.r2_placebo(1.0, [R.Placebo("time_shift", -2.0, 0.3)] * 10 + [R.Placebo("time_shift", 0.1, 0.3)] * 189,
                       "two-sided")
    assert two.n_larger == 10 and not two.passes


def test_kind_applicability_and_rival_systems():
    res = R.r2_placebo(1.0, [R.Placebo("scramble", 1.0, 0.009)] * 50 + [R.Placebo("time_shift", 0.0, 0.5)] * 199,
                       "greater")
    assert res.not_applicable_kinds == ("scramble",) and res.n_placebo == 199 and res.passes
    only_na = R.r2_placebo(1.0, [R.Placebo("scramble", 1.0, 0.0)] * 50, "greater")
    assert only_na.status == "not_computable" and not only_na.passes
    with pytest.raises(R.RobustnessError):
        R.r2_placebo(1.0, [R.Placebo("tropical", 0.0, 0.5)], "greater")
    with pytest.raises(R.RobustnessError):
        R.r2_placebo(1.0, [R.Placebo("time_shift", 0.0, 0.5)], "up")


def test_r2_null_rate_10000_runs():
    rng = np.random.default_rng(2026)
    passes = 0
    n_runs = 10_000
    sims = rng.standard_normal((n_runs, 201))
    for row in sims:
        pls = [R.Placebo("time_shift", float(v), 0.5) for v in row[1:]]
        passes += R.r2_placebo(float(row[0]), pls, "greater").passes
    assert clopper_pearson_upper(passes, n_runs) <= 0.06, passes


def test_adding_a_second_test_leaves_r2_of_the_first_byte_identical():
    rng = np.random.default_rng(3)
    y = rng.normal(size=N)
    y[nakshatra()] += 1.0
    first = R.r2_placebo(stat(nakshatra(), y), placebos_for(nakshatra, y, fam.stream_rng(1, "A", "placebo")),
                         "greater")
    # A second test (tithi) is evaluated in between; A's stream and statistic are its own.
    R.r2_placebo(stat(tithi(), y), placebos_for(tithi, y, fam.stream_rng(1, "B", "placebo")), "greater")
    again = R.r2_placebo(stat(nakshatra(), y), placebos_for(nakshatra, y, fam.stream_rng(1, "A", "placebo")),
                         "greater")
    assert R.robustness(r2=first).to_bytes() == R.robustness(r2=again).to_bytes()


def test_time_shift_plan():
    yearly = R.time_shift_plan(True)
    assert yearly["kind"] == "whole_year" and len(yearly["shifts"]) == 200
    assert sorted(yearly["shifts"]) == list(range(-100, 0)) + list(range(1, 101))
    a = R.time_shift_plan(False, fam.stream_rng(9, "t", "placebo"))
    b = R.time_shift_plan(False, fam.stream_rng(9, "t", "placebo"))
    assert a == b and len(set(a["shifts"])) == 200
    assert all(400 <= abs(s) <= 3650 for s in a["shifts"])
    with pytest.raises(R.RobustnessError):
        R.time_shift_plan(False)
    with pytest.raises(R.RobustnessError):
        R.time_shift_plan(True, n=50)


def test_yearly_grids_get_whole_year_skies():
    """N-07: day offsets of at most 3,650 days give a yearly grid only about 20 skies."""
    years = pd.date_range("1871-06-01", periods=146, freq="YS-JUN")
    assert R.is_yearly_grid(years) and R.is_yearly_grid(np.arange(1871, 2017))
    assert not R.is_yearly_grid(pd.date_range("2000-01-01", periods=100, freq="D"))
    plan = R.time_shift_plan(False, fam.stream_rng(9, "t", "placebo"), dates=years)
    assert plan["kind"] == "whole_year" and len(set(plan["shifts"])) == 200
    daily = R.time_shift_plan(False, fam.stream_rng(9, "t", "placebo"),
                              dates=pd.date_range("2000-01-01", periods=100, freq="D"))
    assert daily["kind"] == "random_offset"
    # Before: random offsets on a yearly grid move it by 1 to 10 whole years at most.
    old = R.time_shift_plan(False, fam.stream_rng(9, "t", "placebo"))
    assert len({round(s / 365.25) for s in old["shifts"]}) <= 20


def test_changed_share():
    a = np.array([1, 1, 0, 0, 1, 0, 0, 0], dtype=bool)
    assert R.changed_share(a, a) == 0.0
    b = a.copy()
    b[2] = True
    assert R.changed_share(a, b) == pytest.approx(1 / 3)
    assert R.changed_share(np.zeros(4, bool), np.zeros(4, bool)) == 0.0


def test_r3_counts_distinct_calendars_only():
    near = [R.Cell(f"ayanamsa_{i}", -1.0, 0.01) for i in range(4)]  # near-copies of the primary
    distinct = [R.Cell("orb_min", 0.5, 0.2), R.Cell("orb_max", 0.4, 0.3), R.Cell("node_true", 0.3, 0.06),
                R.Cell("decluster_b", 0.2, 0.05), R.Cell("window_max", -0.1, 0.4)]
    res = R.r3_sensitivity(0.6, near + distinct, "greater")
    assert res.n_distinct == 5 and res.n_same_sign == 4 and res.same_sign_share == pytest.approx(0.8)
    assert res.passes  # 80% exactly passes
    assert set(res.near_copies) == {c.name for c in near}
    worse = R.r3_sensitivity(0.6, distinct + [R.Cell("second_dataset", -0.2, 1.0)], "greater")
    assert not worse.passes
    none = R.r3_sensitivity(0.6, near, "greater")
    assert none.status == R.R3_NOT_RUN and none.passes and "not run" in none.reason
    # N-18: an empty grid is "not run" too, and the record says so.
    empty = R.r3_sensitivity(0.6, [], "greater")
    assert empty.status == R.R3_NOT_RUN and "no declared sensitivity cell" in empty.to_dict()["reason"]
    two = R.r3_sensitivity(-0.6, [R.Cell("a", -0.2, 0.5), R.Cell("b", -0.1, 0.5)], "two-sided")
    assert two.passes and two.n_same_sign == 2


def test_r1_and_r4():
    assert R.r1_baselines(0.3, 0.05, "greater").passes
    assert not R.r1_baselines(0.3, 0.051, "greater").passes
    assert not R.r1_baselines(-0.3, 0.001, "greater").passes
    assert R.r1_baselines(-0.3, 0.001, "less").passes
    assert R.r4_separability(0.49).passes and not R.r4_separability(0.5).passes
    rob = R.robustness(r1=R.r1_baselines(0.3, 0.01, "greater"), r4=R.r4_separability(0.1))
    assert rob.failed() == ("R2", "R3") and not rob.all_pass


def test_festival_channel_with_and_without_baselines():
    """Section 7.3: returns with a festival-day effect only, tithi calendar.

    Without baselines the tithi calendar reaches the threshold in more than
    half of the runs; with the festival baseline (the primary test) at most 5%
    (upper bound 0.06). The card carries both rows.
    """
    a_test = 0.002
    cal = tithi()
    design = B.build_blocks(cal, merge_gap=1)
    starts = [b.active[0] for b in design.used_blocks]
    festival = np.zeros(N, dtype=bool)
    festival[starts[::6]] = True  # two festivals a year, each on a day of this tithi
    rng = np.random.default_rng(73)
    n_runs = 200
    hit_without = hit_with = 0
    for i in range(n_runs):
        y = rng.normal(size=N)
        y[festival] += 5.0
        sf_rng = fam.stream_rng(1, f"festival{i}", "signflip")
        raw = B.primary_test(design, y, alternative="greater", outcome_type="continuous", rng=sf_rng, n_draws=1999)
        adj = Z.remove_baselines(y, {"festival": festival.astype(float)})
        prim = B.primary_test(design, adj, alternative="greater", outcome_type="continuous", rng=sf_rng,
                              n_draws=1999)
        hit_without += raw.p_value <= a_test
        hit_with += prim.p_value <= a_test
    assert hit_without / n_runs > 0.5
    assert clopper_pearson_upper(hit_with, n_runs) <= 0.06, hit_with
    rows = R.baseline_rows({"estimate": 0.1}, {"estimate": 0.4}, channel="festival buying")
    assert rows["primary"] == "with_baselines" and rows["tested_claim"] == "beyond_channel"
    assert set(rows) >= {"with_baselines", "without_baselines"}


# ----------------------------------------- CALIBRATION-FIX (WP-98 W1 and Z3)
def test_placebo_overlap_is_the_carried_share_of_a_steady_effect():
    real = np.tile(np.r_[np.ones(8, bool), np.zeros(8, bool)], 20)
    same = B.build_blocks(real, merge_gap=0, side_seed=1)
    anti = np.roll(real, 8)
    quarter = np.roll(real, 4)
    assert R.placebo_overlap(same, real) == pytest.approx(1.0)
    assert R.placebo_overlap(B.build_blocks(anti, merge_gap=0, side_seed=1), real) == pytest.approx(-1.0, abs=0.06)
    assert abs(R.placebo_overlap(B.build_blocks(quarter, merge_gap=0, side_seed=1), real)) < R.MAX_PLACEBO_OVERLAP


def test_distinct_clusters_merge_near_copies():
    base = np.zeros(400, bool)
    base[::2] = True  # 200 active bars
    near = base.copy()
    near[0] = False  # one bar of 200 changed: 0.5%, below 1%: a near copy
    far = np.roll(base, 1)
    assert R.distinct_clusters([base, near, far, base, far], int(base.sum())) == [0, 0, 1, 0, 1]
    assert R.count_distinct([base, near, far], int(base.sum())) == 2


def test_insufficient_placebos_sentence_names_the_minimum():
    from vedic_astrology_core.validity import sentences as S
    key = "flag.signal_not_robust.insufficient_placebos"
    assert f"fewer than {R.MIN_DISTINCT_PLACEBOS} distinct placebo calendars" in S.TEMPLATES[key]
    assert S.render(key) == S.TEMPLATES[key]


def test_r2_needs_distinct_placebo_calendars_and_counts_each_once():
    sk = [R.Placebo("time_shift", -1.0, 0.5, cluster=i) for i in range(R.MIN_DISTINCT_PLACEBOS)]
    ok = R.r2_placebo(1.0, sk, "greater", n_distinct=R.MIN_DISTINCT_PLACEBOS)
    assert ok.passes and ok.p_value == pytest.approx(1 / (R.MIN_DISTINCT_PLACEBOS + 1))
    few = R.r2_placebo(1.0, sk[:-1], "greater", n_distinct=R.MIN_DISTINCT_PLACEBOS - 1, n_rejected_overlap=7)
    assert not few.passes and few.status == R.R2_INSUFFICIENT and "distinct" in few.reason
    assert few.to_dict()["n_rejected_overlap"] == 7 and few.to_dict()["min_distinct"] == R.MIN_DISTINCT_PLACEBOS
    # 180 copies of one calendar below the real sky cannot outvote 20 distinct calendars above it.
    dup = [R.Placebo("time_shift", -1.0, 0.5, cluster=0) for _ in range(180)]
    dup += [R.Placebo("time_shift", 2.0, 0.5, cluster=1 + i) for i in range(20)]
    unweighted = R.r2_placebo(1.0, dup, "greater")
    weighted = R.r2_placebo(1.0, dup, "greater", n_distinct=21)
    assert unweighted.p_value == pytest.approx(21 / 201) and weighted.p_value == pytest.approx(21 / 22)
    assert weighted.n_larger == 20 and not weighted.passes


def test_r2_needs_a_real_statistic_in_the_claimed_direction():
    zeros = [R.Placebo("time_shift", 0.0, 0.5, cluster=i) for i in range(30)]
    r = R.r2_placebo(0.0, zeros, "greater", n_distinct=30)
    assert not r.passes and r.n_larger == 0 and r.n_tied == 30 and "direction" in r.reason
    assert not R.r2_placebo(0.0, zeros, "two-sided", n_distinct=30).passes
    assert R.r2_placebo(-0.5, [R.Placebo("time_shift", 0.0, 0.5, cluster=i) for i in range(30)], "less",
                        n_distinct=30).passes


def test_more_offsets_are_fresh_and_in_range():
    rng = np.random.default_rng(5)
    plan = R.time_shift_plan(False, rng)
    extra = R.more_offsets(rng, plan["shifts"], 300)
    assert len(extra) == 300 and not set(extra) & set(plan["shifts"]) and len(set(extra)) == 300
    assert all(R.MIN_OFFSET_DAYS <= abs(s) <= R.MAX_OFFSET_DAYS for s in extra)
