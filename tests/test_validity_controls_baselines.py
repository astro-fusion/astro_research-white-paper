"""REVIEW_1 R1-DATA: physical baselines, positive controls, explore/confirm detrend segments, Abhijit.

* fix 4: the solar-cycle baseline is built from the pinned SILSO series and
  enters the earthquake and monsoon runs (before: declared, missing, so no
  baselines at all and R1/R4 "not_computable");
* fix 3: every domain plan declares positive controls with a pass rule and
  a consequence; they are built as never-registrable control tests the
  preview runs; the evaluation drives DomainRun.control_not_detected;
* fix 5: no confirm row changes any explore-period detrended value;
* fix 6: the Indra mandala declares Abhijit and a sensitivity variant.

No outcome is read. Hash-only snapshots that are absent skip their test.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

from vedic_astrology_core.rules.grid import GridEvaluator
from vedic_astrology_core.rules.schema import Rule
from vedic_astrology_core.stats import season as S
from vedic_astrology_core.validity import bindings as B
from vedic_astrology_core.validity import pipeline as P
from vedic_astrology_core.validity import plan as PL
from vedic_astrology_core.validity import variants as VR

ROOT = Path(__file__).resolve().parents[1]
PLANS = ROOT / "studies" / "validity" / "domains"
SILSO = ROOT / "data" / "snapshots" / "silso_sn_monthly_1cf8a1f6f28f.csv"
USGS = ROOT / "data" / "snapshots" / "usgs_d3d3d6ec8405.csv"
needs_silso = pytest.mark.skipif(not SILSO.is_file(), reason="SILSO snapshot not on disk (hash-only data)")


def _plan(name):
    return yaml.safe_load((PLANS / f"{name}.yaml").read_text())


@pytest.fixture(scope="module")
def rules():
    return B.load_rule_files(ROOT)


# ------------------------------------------------------------ fix 4: solar
def test_silso_rows_read_the_fourth_field_and_minus_one_is_missing():
    text = "1749;01;1749.042;  96.7; -1.0;   -1;1\r\n1749;02;1749.123; -1; -1.0;   -1;1\r\n"
    s = B.parse_silso_monthly(text)
    assert s.iloc[0] == 96.7 and np.isnan(s.iloc[1])
    assert str(s.index[0]) == "1749-01"
    with pytest.raises(B.BindingError, match="missing months"):
        B.solar_cycle_monthly(s)


def test_solar_cycle_is_smoothed_on_months_not_on_grid_bars():
    idx = pd.period_range("1950-01", "1990-12", freq="M")
    raw = pd.Series(100 + 80 * np.sin(2 * np.pi * np.arange(len(idx)) / 132.0), index=idx)
    sm = B.solar_cycle_monthly(raw)
    assert np.allclose(sm.to_numpy(), S.solar_cycle_baseline(raw.to_numpy()))
    years = pd.DatetimeIndex([pd.Timestamp(y, 7, 1) for y in range(1960, 1981)])
    v = B._season_mean(sm, years)
    want = [sm[[pd.Period(f"{y}-{m:02d}", "M") for m in (6, 7, 8, 9)]].mean() for y in range(1960, 1981)]
    assert np.allclose(v, want)
    # a 13-bar smoothing on the yearly grid would flatten the 11-year cycle; on months it survives
    assert np.ptp(v) > 100


@needs_silso
@pytest.mark.skipif(not USGS.is_file(), reason="USGS snapshot not on disk")
def test_earthquake_run_gets_nodal_and_solar_baselines(rules):
    eq = B.bind(PLANS / "earthquake.yaml", root=ROOT, rule_files=rules, check_detrend=False)
    assert "baselines_missing" not in eq.notes  # before: ["solar_cycle"] and run.baselines None
    assert eq.run.baselines is not None
    dates = pd.DatetimeIndex(eq.adapter.grid())[:: 24 * 30]
    m = np.asarray(eq.run.baselines(dates))
    assert m.shape == (len(dates), 2 * S.NODAL_HARMONICS + 1) and np.isfinite(m).all()
    solar = m[:, -1]
    assert solar.min() >= 0 and np.ptp(solar) > 50  # cycles 21 to 25 swing by about 100 to 200
    assert "are not (pipeline _residualised)" in eq.notes["baselines_in_estimate"]


@needs_silso
def test_monsoon_run_gets_solar_and_enso_baselines(rules):
    mo = B.bind(PLANS / "monsoon.yaml", root=ROOT, rule_files=rules, check_detrend=False)
    assert "baselines_missing" not in mo.notes and mo.run.baselines is not None
    g = pd.DatetimeIndex(mo.adapter.grid())
    m = np.asarray(mo.run.baselines(g))
    assert m.shape == (len(g), 2 * S.NODAL_HARMONICS + 2) and np.isfinite(m).all()


def test_a_missing_solar_snapshot_still_leaves_no_baselines(tmp_path, rules):
    plan = _plan("earthquake")
    for s in plan["snapshots"]:
        if s["id"] == plan["sunspot"]["series_id"]:
            s["file"] = "data/snapshots/not_here.csv"
    notes = {}
    assert B._solar_cycle(plan, ROOT, notes) is None
    assert "solar_cycle" in notes["baselines_unavailable"]
    assert B._physical_baselines(["nodal_18_6y", "solar_cycle"], notes, {"solar_cycle": None}) is None
    assert notes["baselines_missing"] == ["solar_cycle"]


# ---------------------------------------------------- fix 3: positive controls
@pytest.mark.parametrize("name", ["earthquake", "metals", "monsoon"])
def test_every_plan_declares_controls_with_pass_rule_and_consequence(name):
    plan = _plan(name)
    pc = plan["positive_controls"]
    assert pc["alpha"] == 0.05 and "detected" in pc["pass_rule"] and "control_not_detected" in pc["if_failed"]
    outs = {o["id"]: o for o in plan["outcomes"]}
    for c in pc["controls"]:
        assert c["id"].startswith("control.") and c["outcome"] in outs and c["direction"] in B.SIDES
        assert c["kind"] in B._CONTROL_KINDS and c["source"]
        # a control the domain's baselines regress out would fail by construction: events and flags only
        assert outs[c["outcome"]]["type"] in ("event", "binary")


@pytest.mark.skipif(not USGS.is_file(), reason="USGS snapshot not on disk")
def test_controls_are_built_as_tests_but_never_registered(rules):
    eq = B.bind(PLANS / "earthquake.yaml", root=ROOT, rule_files=rules, check_detrend=False, control_status={})
    ctl = [b for b in eq.tests if b.role == "control"]
    assert [b.definition.rule_id for b in ctl] == ["control.monsoon_season", "control.spring_tide"]
    assert all(not b.registrable and b.problems == (B.CONTROL_PROBLEM,) for b in ctl)
    assert not {t.test_id for t in eq.control_tests()} & {t.test_id for t in eq.registrable_tests()}
    assert {t.test_id for t in eq.control_tests()} <= {t.test_id for t in eq.all_tests()}
    assert not any(r.startswith("control.") for r in eq.rule_ids())
    assert eq.run.control_not_detected is True  # no evaluation that passed: every card carries the flag
    st = {"detected": True, "plan_sha256": eq.run.plan_sha256}
    ok = B.bind(PLANS / "earthquake.yaml", root=ROOT, rule_files=rules, check_detrend=False, control_status=st)
    assert ok.run.control_not_detected is False


def test_control_calendars_are_the_declared_effects():
    plan = _plan("monsoon")
    d = pd.DatetimeIndex(["1999-12-31 10:00", "2000-01-03 10:00", "2000-06-15", "2000-10-01"])
    mon = B.ControlCalendar({"id": "control.x", "kind": "weekday", "days": ["monday"]}, plan, ROOT)
    assert mon(d).tolist() == [False, True, False, False]
    sea = B.ControlCalendar({"id": "control.x", "kind": "months", "months": [6, 7, 8, 9]}, plan, ROOT)
    assert sea(d).tolist() == [False, False, True, False]
    tide = B.ControlCalendar({"id": "control.x", "kind": "syzygy", "orb_deg": 12}, plan, ROOT)
    # new Moon 2000-01-06 18:14 UTC, first quarter 2000-01-14 13:34 UTC, full Moon 2000-01-21 04:40 UTC
    t = pd.DatetimeIndex(["2000-01-06 18:00", "2000-01-14 13:00", "2000-01-21 05:00", "2000-01-28 07:00"])
    assert tide(t).tolist() == [True, False, True, False]
    el = B.sun_moon_elongation(t)
    assert abs(((el[0] + 180) % 360) - 180) < 1.0 and abs(el[2] - 180) < 1.0


def test_el_nino_control_marks_known_el_nino_and_la_nina_seasons():
    plan = _plan("monsoon")
    c = next(x for x in plan["positive_controls"]["controls"] if x["id"] == "control.el_nino")
    cal = B.ControlCalendar(c, plan, ROOT)
    years = pd.DatetimeIndex([pd.Timestamp(y, 7, 1) for y in (1972, 1987, 1997, 1988, 1999, 2010)])
    assert cal(years).tolist() == [True, True, True, False, False, False]
    assert cal(pd.DatetimeIndex(["1800-07-01"])).tolist() == [False]  # outside the series: inactive


def _doc(rows):
    return {"records": rows}


def _row(cid, outcome, p, stat, untestable=False):
    return {"rule_id": cid, "outcome": outcome, "gate": {"untestable": untestable},
            "explore": None if p is None else {"p_descriptive_uncorrected": p, "statistic": stat, "estimate": 1.0}}


def test_pass_rule_and_gate_control_order():
    plan = _plan("earthquake")
    a, b = "control.monsoon_season", "control.spring_tide"
    st = B.evaluate_positive_controls(_doc([_row(a, "mainshock_rate", 0.01, -0.2),
                                            _row(b, "mainshock_rate", 0.5, 0.1)]), plan)
    assert st["gate_control"] == a and st["detected"] is True and st["control_not_detected"] is False
    st = B.evaluate_positive_controls(_doc([_row(a, "mainshock_rate", 0.01, 0.2)]), plan)  # wrong sign
    assert st["controls"][0]["status"] == "not_detected" and st["detected"] is False
    st = B.evaluate_positive_controls(_doc([_row(a, "mainshock_rate", None, None, untestable=True),
                                            _row(b, "mainshock_rate", 0.03, 0.1)]), plan)
    assert [c["status"] for c in st["controls"]] == ["untestable", "detected"] and st["gate_control"] == b
    st = B.evaluate_positive_controls(_doc([]), plan)
    assert st["gate_control"] is None and st["control_not_detected"] is True
    assert st["plan_sha256"] == PL.plan_hash(plan)


def test_a_stored_evaluation_of_another_plan_hash_is_ignored(tmp_path):
    plan = _plan("metals")
    pv = tmp_path / "studies" / "validity" / "preview" / "metals"
    pv.mkdir(parents=True)
    (pv / "results.json").write_text('{"records": [], "positive_controls": {"detected": true, "plan_sha256": "x"}}')
    assert B.stored_control_status(Path("metals.yaml"), plan, tmp_path) is None
    st = B.annotate_preview(pv / "results.json", plan)
    assert B.stored_control_status(Path("metals.yaml"), plan, tmp_path) == st


# ------------------------------------------- fix 5: explore/confirm segments
def test_no_confirm_row_reaches_an_explore_detrended_value():
    plan = _plan("metals")
    w = int(plan["detrend_window"])
    sp = plan["split"]
    dates = pd.bdate_range(sp["explore"]["start"], sp["confirm"]["end"])
    explore = P._mask_between(dates, (pd.Timestamp(sp["explore"]["start"]).date(),
                                      pd.Timestamp(sp["explore"]["end"]).date()))
    confirm = P._mask_between(dates, (pd.Timestamp(sp["confirm"]["start"]).date(),
                                      pd.Timestamp(sp["confirm"]["end"]).date()))
    seg = P._segments(explore, confirm)
    rng = np.random.default_rng(7)
    y = np.cumsum(rng.normal(0, 0.01, len(dates)))  # a trending series, as a price log
    y2 = y.copy()
    y2[confirm] = rng.normal(50, 30, int(confirm.sum()))  # every confirm row changed, wildly
    y3 = y.copy()
    y3[confirm] = np.nan  # the provisional run: confirm rows unread
    a = S.centred_detrend(y, w, segments=seg)
    for other in (y2, y3):
        b = S.centred_detrend(other, w, segments=seg)
        assert np.array_equal(a[explore], b[explore])  # bit for bit
    # the shape exclusion removes is built with the same segments
    cal = (np.arange(len(dates)) % 17) < 3
    sa = S.effect_shape(cal, detrend_window=w, segments=seg)
    assert np.array_equal(sa[explore], S.effect_shape(cal, detrend_window=w, segments=seg)[explore])
    # teeth: without the segments the last explore bars do see confirm rows
    u1, u2 = S.centred_detrend(y, w), S.centred_detrend(y2, w)
    last = np.flatnonzero(explore)[-1]
    assert u1[last] != u2[last]
    assert np.array_equal(u1[explore][: -w], u2[explore][: -w])  # only the last half-window is reached


# ---------------------------------------------------------- fix 6: Abhijit
def _indra(rules):
    return rules["seismic.study.moon_mandala_indra"].rule


def test_indra_declares_abhijit_and_a_sensitivity_variant(rules):
    r = _indra(rules)
    choice = {c.choice: c for c in r.operationalisation}["abhijit"]
    assert choice.fixed_by == "project" and choice.alternatives
    assert "276 deg 40 min" in choice.value
    v = {v.id: v for v in r.variants}["abhijit_28_equal"]
    assert v.role == "sensitivity"
    exp = VR.expand(r, "earthquake")
    assert [e.variant for e in exp] == ["primary"] and "abhijit_28_equal" in exp[0].sensitivity
    p = r.param_values  # Abhijit's classical span lies inside the Uttara Ashadha to Dhanishtha range
    assert p["uttarashadha_start"] <= 276 + 40 / 60 and 280 + 53 / 60 + 20 / 3600 <= p["dhanishta_end"]


def test_indra_primary_is_the_27_nakshatra_circle_and_the_variant_differs(rules):
    r = _indra(rules)
    old = Rule.model_validate({**r.model_dump(by_alias=True, exclude_none=True),
                               "conditions": {"moon_mandala": {"mandalas": ["indra"]}},
                               "params": {}, "variants": []})
    moments = pd.date_range("1990-01-01", "1993-12-31", freq="7h", tz="UTC")
    ev = GridEvaluator(moments)
    new, ref = ev.fired(r), ev.fired(old)
    assert new.any() and np.array_equal(new, ref)
    cell = ev.fired(VR.expand(r, "earthquake")[0].sensitivity["abhijit_28_equal"])
    changed = np.mean(cell != new)
    assert changed > 0.05 and abs(cell.mean() - 7 / 28) < 0.03 and abs(new.mean() - 6 / 27) < 0.03
