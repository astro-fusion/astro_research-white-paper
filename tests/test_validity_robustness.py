"""ADR-008 WP-94: the robustness contract of section 5 (A-01, F-07) and section 7.3.

R2 per test on its own statistic T; a placebo kind applies only when it
changes at least 1% of the active bars; tropical is a rival system (sensitivity
grid only); 200 time-shift skies, whole years for season-linked calendars;
pass at (1 + strictly larger) / (n + 1) <= 0.05. R3 counts distinct calendars
(at least 5% of active bars changed). R1 with baselines, R4 by baseline_r2.
"""

from __future__ import annotations

import numpy as np
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


def test_old_tie_rule_would_have_failed_and_new_one_does_not():
    # Every placebo equals the real statistic: ties never count against the real sky.
    res = R.r2_placebo(0.7, [R.Placebo("time_shift", 0.7, 0.5)] * 200, "greater")
    assert res.n_tied == 200 and res.n_larger == 0 and res.passes


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
    assert none.status == "not_applicable" and none.passes
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
