"""Aggregate pattern report, hierarchy and engine calibration (ADR-006 WP-55)."""

import copy
import json
import math
from dataclasses import replace
from datetime import datetime, timezone

import numpy as np
import pytest

from vedic_astrology_core.mundane import aggregate as ag
from vedic_astrology_core.mundane import burden as bd
from vedic_astrology_core.mundane import controls as ct
from vedic_astrology_core.mundane.registry import load_charts, load_events

UTC = timezone.utc


@pytest.fixture(scope="module")
def plan():
    return bd.load_plan()


@pytest.fixture(scope="module")
def open_plan(plan):
    """The plan with its slice ceiling lifted, so the statistics can be exercised."""
    data = copy.deepcopy(plan.data)
    data["scope"]["verdict_ceiling"] = "none"
    return bd.plan_from_dict(data, plan.sha256)


@pytest.fixture(scope="module")
def sim(open_plan):
    return ag.simulate_test_data(open_plan, np.random.default_rng(7), n_events=60, cluster_mean=0.5)


# --------------------------------------------------- matched-set permutation
def test_matched_permutation_keeps_labels_inside_sets():
    # Every member of a set shares one label: no within-set exchange can change
    # anything, so the null is degenerate and p is 1. A pooled permutation
    # (labels moved between sets) would call this highly significant.
    rng = np.random.default_rng(1)
    k, s = 3, 40
    ev = np.array([i % k for i in range(s)])
    ctrl = [np.full(5, ev[i]) for i in range(s)]
    ev_skew = np.zeros(s, dtype=int)
    ctrl_skew = [np.full(5, i % k) for i in range(s)]
    u = rng.random((999, s))
    same = ag.matched_permutation(ev, ctrl, k, u)
    assert same.p == 1.0
    skew = ag.matched_permutation(ev_skew, ctrl_skew, k, u)
    assert skew.p == pytest.approx(1 / 1000)


def test_matched_permutation_null_is_uniform():
    rng = np.random.default_rng(3)
    ps = []
    for _ in range(300):
        s = 30
        ev = rng.integers(0, 4, s)
        ctrl = [rng.integers(0, 4, 10) for _ in range(s)]
        ps.append(ag.matched_permutation(ev, ctrl, 4, rng.random((199, s))).p)
    ps = np.array(ps)
    assert 0.02 < np.mean(ps <= 0.05) < 0.09
    assert abs(np.mean(ps) - 0.5) < 0.06


def test_cluster_shares_one_permutation_choice(open_plan, sim):
    td = next(iter(sim.values()))
    keys = {td.cluster(i) for i in range(len(td.event_ids))}
    assert len(keys) < len(td.event_ids)   # the simulation made clusters
    r = ag.build_report(open_plan, sim, n_perm=199, n_shift=199, second_table=False)
    assert r["settings"]["n_clusters"] == len(keys)


# ----------------------------------------------------------- family size
def test_hierarchy_refuses_a_shrunken_family():
    with pytest.raises(ag.FamilyShrinkError):
        ag.hierarchical({"F1": [0.01], "F2": [0.5, 0.5]}, {"F1": 2, "F2": 2}, 2, 0.05)
    with pytest.raises(ag.FamilyShrinkError):
        ag.hierarchical({"F1": [0.01, 0.2]}, {"F1": 2, "F2": 2}, 2, 0.05)
    with pytest.raises(ag.FamilyShrinkError):
        ag.by_q([0.01, 0.02], 3, "x")
    h = ag.hierarchical({"F1": [0.001, 1.0], "F2": [1.0, 1.0]}, {"F1": 2, "F2": 2}, 2, 0.05)
    assert h["p_family"]["F1"] == pytest.approx(0.002)   # Bonferroni over the declared 2


def test_missing_test_keeps_its_place(open_plan, sim):
    data = dict(sim)
    data.pop("dasha.identity.pratyantar")
    r = ag.build_report(open_plan, data, n_perm=199, n_shift=199, second_table=False)
    rows = {t["test_id"]: t for t in r["main"]["tests"]}
    assert len(rows) == 18
    gone = rows["dasha.identity.pratyantar"]
    assert gone["verdict"] == "untestable" and "keeps its place" in gone["reason"]
    assert gone["family_size"] == 2
    fam = {f["family"]: f for f in r["main"]["families"]}
    assert fam["F1_dasha_lord_identity"]["declared_tests"] == 2
    assert len(r["main"]["factors"]) == 182


def test_undeclared_test_is_refused(open_plan, sim):
    data = dict(sim)
    data["dasha.identity.maha"] = replace(sim["dasha.identity.antar"], test_id="dasha.identity.maha")
    with pytest.raises(ag.AggregateError, match="undeclared"):
        ag.build_report(open_plan, data, n_perm=99, n_shift=99)


# ------------------------------------------------------------- the report
def test_report_has_every_column(open_plan, sim):
    r = ag.build_report(open_plan, sim, n_perm=499, n_shift=499)
    for table in ("main", "second"):
        for row in r[table]["tests"] + r[table]["factors"]:
            for col in ("n_events", "n_active", "control_rate", "rate_ratio", "ci", "p_matched",
                        "p_shift", "q_family", "episodes", "stable_share", "placebo_rank", "mde",
                        "verdict"):
                assert col in row
            assert row["verdict"] in ag.VERDICTS
    assert r["second"]["label"].startswith("SECOND TABLE")
    tested = [t for t in r["main"]["tests"] if t["p_matched"] is not None]
    assert tested and all(t["p_shift"] is not None for t in tested)
    assert all(t["verdict"] != "effect found" for t in r["main"]["tests"])   # explore only
    json.dumps(r, allow_nan=False)
    again = ag.build_report(open_plan, sim, n_perm=499, n_shift=499)
    assert json.dumps(again, sort_keys=True) == json.dumps(r, sort_keys=True)


def test_under_30_events_is_descriptive_only(open_plan):
    data = ag.simulate_test_data(open_plan, np.random.default_rng(11), n_events=20)
    r = ag.build_report(open_plan, data, n_perm=199, n_shift=199)
    assert r["descriptive_only"]
    assert any("descriptive only" in line for line in r["headline"])
    for table in ("main", "second"):
        for row in r[table]["tests"] + r[table]["factors"]:
            assert row["verdict"] == "descriptive only"
            assert row["p_matched"] is None and row["p_shift"] is None
            assert row["q_family"] is None and row["placebo_rank"] is None
    assert r["main"]["best_factor"] is None
    assert all(f["p_family"] is None for f in r["main"]["families"])


def test_slice_plan_ceiling_prints_no_p_value(plan, sim):
    r = ag.build_report(plan, sim, n_perm=99, n_shift=99)
    assert r["descriptive_only"]
    assert all(t["p_matched"] is None for t in r["main"]["tests"])


def test_method_gate_makes_rows_descriptive(open_plan, sim):
    data = {k: replace(v, gate_ok=False, gate_reason="method status unverified") for k, v in sim.items()}
    r = ag.build_report(open_plan, data, n_perm=99, n_shift=99)
    assert all(t["verdict"] == "descriptive only" for t in r["main"]["tests"])
    assert "unverified" in r["main"]["tests"][0]["reason"]


def test_unstable_events_only_in_second_table(open_plan, sim):
    tid = "transit.mars.from_lagna.d1"
    td = sim[tid]
    flags = [i % 4 != 0 for i in range(len(td.event_ids))]
    data = dict(sim)
    data[tid] = replace(td, event_stable=flags)
    r = ag.build_report(open_plan, data, n_perm=199, n_shift=199)
    main = next(t for t in r["main"]["tests"] if t["test_id"] == tid)
    second = next(t for t in r["second"]["tests"] if t["test_id"] == tid)
    assert main["n_events"] == sum(flags)
    assert second["n_events"] == len(flags)
    assert main["stable_share"] == pytest.approx(sum(flags) / len(flags), abs=1e-4)
    assert "disagreements" in r


def test_confirm_period_and_leakage_are_refused(open_plan, sim):
    with pytest.raises(ct.ConfirmNotAvailable, match="WP-63"):
        ag.build_report(open_plan, sim, period="confirm")
    tid = "dasha.identity.antar"
    td = sim[tid]
    late = datetime(2012, 5, 1, tzinfo=UTC)
    bad_event = replace(td, event_times=[late] + td.event_times[1:])
    with pytest.raises(ag.LeakageError, match="outside"):
        ag.build_report(open_plan, {**sim, tid: bad_event})
    ctrl = [list(c) for c in td.control_times]
    ctrl[0][0] = late
    with pytest.raises(ag.LeakageError):
        ag.build_report(open_plan, {**sim, tid: replace(td, control_times=ctrl)})
    long_grid = list(td.grid_labels) + [td.grid_labels[-1]] * 40
    with pytest.raises(ag.LeakageError, match="grid"):
        ag.build_report(open_plan, {**sim, tid: replace(td, grid_labels=long_grid)})


def test_constant_factor_is_rejected_as_natal(open_plan, sim):
    tid = "transit.saturn.from_moon.d1"
    td = sim[tid]
    const = replace(td, grid_labels=[1] * len(td.grid_labels),
                    event_labels=[1] * len(td.event_labels),
                    control_labels=[[1] * len(c) for c in td.control_labels])
    with pytest.raises(bd.NatalFactorError):
        ag.build_report(open_plan, {**sim, tid: const}, n_perm=99, n_shift=99)


def test_placebo_rank(open_plan):
    data = ag.simulate_test_data(open_plan, np.random.default_rng(5), n_events=80,
                                 planted=("dasha.dignity.pratyantar.d1", None, 4.0))
    tid = "dasha.dignity.pratyantar.d1"
    td = data[tid]
    rng = np.random.default_rng(9)
    cells = list(next(t for t in bd.plan_tests(open_plan) if t.id == tid).cells)
    placebos = []
    for _ in range(19):
        perm = dict(zip(cells, rng.permutation(cells)))
        shuffled = [cells[int(i)] for i in rng.integers(0, len(cells), len(td.event_labels))]
        placebos.append((shuffled, [[perm[x] for x in row] for row in td.control_labels]))
    r = ag.build_report(open_plan, {**data, tid: replace(td, placebo_labels=placebos)},
                        n_perm=999, n_shift=999, second_table=False)
    row = next(t for t in r["main"]["tests"] if t["test_id"] == tid)
    assert row["placebo_rank"] is not None and 1 <= row["placebo_rank"] <= 20
    assert row["placebo_rank"] <= 3


def test_write_report(open_plan, sim, tmp_path):
    r = ag.build_report(open_plan, sim, n_perm=199, n_shift=199)
    rp, fp = ag.write_report(r, tmp_path / "results.json", tmp_path / "factor_table.csv")
    lines = fp.read_text().strip().splitlines()
    assert len(lines) == 1 + 2 * (18 + 182)       # every row, both tables
    assert json.loads(rp.read_text())["plan_sha256"] == open_plan.sha256


# ------------------------------------------------------------ calibration
def test_calibration_no_effect_flags_at_most_5_percent(open_plan):
    cal = open_plan["calibration"]
    n = int(cal["null_datasets"])
    flags = 0
    for i in range(n):
        rng = np.random.default_rng([int(cal["seed"]), i])
        data = ag.simulate_test_data(open_plan, rng, n_events=40, cluster_mean=1.0)
        r = ag.build_report(open_plan, data, n_perm=9999, n_shift=999, second_table=False)
        flags += bool(r["main"]["any_flag"])
    bound = 0.05 + 3 * math.sqrt(0.05 * 0.95 / n)
    assert flags / n <= bound, (flags, n)


def test_calibration_planted_rate_ratio_3_on_100_events(open_plan):
    cal = open_plan["calibration"]["planted"]
    tid = "dasha.dignity.pratyantar.d1"
    reps, found, duties = 40, 0, []
    for i in range(reps):
        rng = np.random.default_rng([20261122, 1000 + i])
        data = ag.simulate_test_data(open_plan, rng, n_events=int(cal["events"]),
                                     planted=(tid, None, float(cal["rate_ratio"])))
        grid = data[tid].grid_labels
        duties.append(max(grid.count(c) for c in set(grid)) / len(grid))
        r = ag.build_report(open_plan, data, n_perm=9999, n_shift=999, second_table=False)
        row = next(t for t in r["main"]["tests"] if t["test_id"] == tid)
        found += bool(row["flagged"])
    assert min(duties) >= 0.15           # a cell the plan's MDE table says is detectable
    assert found / reps >= float(cal["min_detection_rate"]), (found, reps)


# ------------------------------------------------------- real chart (rules)
def test_real_chart_descriptive_slice(plan):
    events = load_events()
    sel = ct.select_events(events, plan)
    draw = ct.draw_season_matched(sel, plan, exclusion=ct.exclusion_events(events, plan))
    india = {c.chart_id: c for c in load_charts()}["in-1947-midnight"]
    specs = bd.plan_tests(plan)
    data = ag.collect_test_data(plan, india, sel, draw, grid=False,
                                placebos=ct.date_shift_placebos(india, plan, n=2))
    assert set(data) == {s.id for s in specs}
    for sp in specs:
        td = data[sp.id]
        assert all(lab in sp.cells for lab in td.event_labels)
        assert all(lab in sp.cells for row in td.control_labels for lab in row)
        assert td.gate_ok is False and td.method_status == "unverified"
        assert len(td.placebo_labels) == 2
    # Grade C (60 minutes): the D1 lagna is not stable, so lagna-based tests drop out.
    assert not any(data["transit.saturn.from_lagna.d1"].event_stable)
    assert all(data["transit.saturn.from_moon.d1"].event_stable)
    r = ag.build_report(plan, data, chart_id=india.chart_id)
    assert r["descriptive_only"]
    assert all(t["p_matched"] is None for t in r["main"]["tests"])
    nonhand = replace(sel[0], exhaustive=False)
    with pytest.raises(ag.AggregateError, match="exhaustive"):
        ag.collect_test_data(plan, india, [nonhand], draw, grid=False)
