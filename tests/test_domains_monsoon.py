"""WP-79: monsoon adapter and monsoon principles (simulated rainfall first)."""

import json
import tempfile
from pathlib import Path

import numpy as np
import pytest
import yaml

from studies._paths import REPO_ROOT
from vedic_astrology_core.domains.base import GateHashError, write_gate
from vedic_astrology_core.domains.monsoon import (
    FirewallError,
    MonsoonDomain,
    PlanError,
    VariantError,
    YearCalendar,
    load_plan,
    load_principles,
    parse_iitm_regions,
    parse_psl_monthly,
    season_differences,
    season_test,
    simulate_rainfall,
    sun_nakshatra_ingress,
    vara_lord,
    jd_to_datetime,
)
from vedic_astrology_core.rules import run_reference_cases
from vedic_astrology_core.rules.levels import level
from vedic_astrology_core.stats.episodes import by_rank1_threshold

GATE = write_gate(Path(tempfile.mkdtemp()) / "gate.json", {"test": "monsoon"})
PLAN = REPO_ROOT / "studies" / "monsoon" / "plan.yaml"
RULES = REPO_ROOT / "rules" / "monsoon"
MEGH = "monsoon.meghesha_malefic_deficit"
VARSH = "monsoon.varsheshvara_malefic_deficit"
MARS = "monsoon.mars_in_rohini_deficit"
YEARS = np.arange(1871, 2017)


def registers():
    index = json.loads((REPO_ROOT / "data" / "snapshot_index.json").read_text())
    lic = yaml.safe_load((REPO_ROOT / "data" / "registry" / "licences.yaml").read_text())
    return index, lic.get("sources", lic)


@pytest.fixture(scope="module")
def real():
    """Adapter on the committed draft plan; no simulated rainfall."""
    return MonsoonDomain(*registers())


@pytest.fixture(scope="module")
def sim():
    rain = simulate_rainfall(YEARS, seed=7, regions=("all_india", "peninsular_india"))
    return MonsoonDomain(*registers(), simulated=rain)


# ------------------------------------------------------------------ plan
def test_plan_is_a_marked_draft_with_adr_proposals():
    plan = load_plan(PLAN)
    assert plan["status"] == "draft"
    assert "DRAFT" in PLAN.read_text().splitlines()[1]
    assert plan["periods"]["explore"] == [1871, 1960]
    assert plan["periods"]["confirm"] == [1961, 2016]
    assert plan["sesoi"] == {"jjas_anomaly_pct": 5.0, "drought_risk_ratio": 2.0}
    assert plan["budget_m"] == 40
    assert plan["unit_of_evidence"] == "season"


def test_plan_loader_is_strict(tmp_path):
    data = yaml.safe_load(PLAN.read_text())
    data["surprise"] = 1
    p = tmp_path / "plan.yaml"
    p.write_text(yaml.safe_dump(data))
    with pytest.raises(PlanError, match="unknown"):
        load_plan(p)
    data.pop("surprise")
    data["unit_of_evidence"] = "month"
    p.write_text(yaml.safe_dump(data))
    with pytest.raises(PlanError, match="season"):
        load_plan(p)


def test_grid_and_periods_come_from_the_plan(real):
    g = real.grid()
    assert g[0] == 1871 and g[-1] == 2016 and len(g) == 146
    per = real.periods()
    assert per.explore[1].year == 1960 and per.confirm[0].year == 1961
    ctx = real.calendar_context()
    assert ctx["unit"] == "season"
    assert ctx["explore"].sum() == 90 and ctx["confirm"].sum() == 56


def test_dataset_is_grade_b_with_licence_and_splice(real):
    ds = real.dataset()
    assert ds.grade == "B"
    assert ds.sha256.startswith("76380a8e9ee3")
    assert "licence not yet read" in ds.limitations
    assert any("splice" in x for x in ds.limitations)
    assert ds.spec.n_units == 146


# ------------------------------------------------------------ principles
def test_principles_load_at_their_honest_level():
    prs = load_principles(RULES)
    assert set(prs) == {MEGH, VARSH, MARS}
    for pr in prs.values():
        assert pr.rule.tier == "experimental"
        assert level(pr.rule).level == 0  # no quotation or maintainer check yet (H11)
        assert pr.outcomes()


def test_monsoon_rule_files_stay_out_of_the_catalogue_until_wp65():
    from vedic_astrology_core.rules.loader import discover

    assert not [p for p in discover([REPO_ROOT / "rules"]) if p.parent.name == "monsoon"]


def test_mars_reference_cases_pass():
    rule = load_principles(RULES)[MARS].rule
    assert all(r.passed for r in run_reference_cases(rule))


def test_varsheshvara_matches_published_kings(real):
    ref = real.principles()[VARSH].spec["reference_years"]
    cal = real.calendar(VARSH, years=sorted(ref))
    assert [d["lord"] for d in cal.detail] == [ref[y] for y in sorted(ref)]
    assert list(cal.active) == [ref[y] in ("Sun", "Mars", "Saturn") for y in sorted(ref)]


def test_meghesha_is_read_at_the_ardra_ingress(real):
    cal = real.calendar(MEGH, years=[2022, 2023, 2024])
    for d in cal.detail:
        when = d["instant_utc"]
        assert when[5:7] == "06" and 19 <= int(when[8:10]) <= 24
    # 2024: the ingress is 00:06 IST on Saturday 22 June, before sunrise, so the
    # vara is still Friday (Venus); the civil-date cell says Saturday.
    assert cal.detail[-1]["lord"] == "Venus"
    civil = real.calendar(MEGH, {"vara": "civil"}, years=[2024])
    assert civil.detail[0]["lord"] == "Saturn" and civil.active[0]


def test_ayanamsa_cell_moves_the_instant():
    lahiri = sun_nakshatra_ingress(2000, "Ardra", "lahiri")
    raman = sun_nakshatra_ingress(2000, "Ardra", "raman")
    assert 0.5 < lahiri - raman < 2.0  # Raman's ayanamsa is ~1.4 deg smaller


def test_vara_conventions():
    place = {"lat": 23.1765, "lon": 75.7885, "tz_offset_hours": 5.5}
    jd = 2460483.275  # 2024-06-21 18:36 UTC, before sunrise in Ujjain
    assert jd_to_datetime(jd).hour == 18
    assert vara_lord(jd, "sunrise", place)[0] == "Venus"
    assert vara_lord(jd, "udaya", place)[0] == "Saturn"
    assert vara_lord(jd, "civil", place)[0] == "Saturn"


def test_undeclared_cells_are_refused(real):
    with pytest.raises(VariantError):
        real.calendar(MEGH, {"ayanamsa": "fagan"}, years=[2000])
    with pytest.raises(VariantError):
        real.calendar(MARS, {"window": "whole_year"}, years=[2000])
    assert {"vara": "civil"} in real.declared_cells(MEGH)


def test_mars_in_rohini_uses_the_rule_window(real):
    cal = real.calendar(MARS, years=[2018, 2019])
    assert list(cal.active) == [False, True]
    assert cal.detail[1]["window"] == ["2019-03-01", "2019-09-30"]
    assert cal.detail[1]["first_day"].startswith("2019-04")
    only = real.calendar(MARS, {"window": "season_only"}, years=[2019])
    assert not only.active[0]  # Mars left Rohini in April 2019


# --------------------------------------------------------------- firewall
def test_outcomes_and_controls_need_a_gate_hash(sim):
    with pytest.raises(GateHashError):
        sim.outcomes()
    with pytest.raises(GateHashError):
        sim.controls("nope")


def test_draft_plan_refuses_real_rainfall(real):
    status = real.firewall_status()
    assert not status["open"] and len(status["reasons"]) == 4
    with pytest.raises(FirewallError, match="registered"):
        real.outcomes(GATE)
    with pytest.raises(FirewallError):
        real.controls(GATE)
    assert real.outcome_reads == 0


def _registered_copy(tmp_path, *, calibration=True, lock=True, passed=True):
    data = yaml.safe_load(PLAN.read_text())
    data["status"] = "registered"
    data["firewall"] = {"calibration_record": str(tmp_path / "cal.json"),
                        "family_lock": str(tmp_path / "family.lock")}
    plan = tmp_path / "plan.yaml"
    plan.write_text(yaml.safe_dump(data))
    from vedic_astrology_core.stats.manifest import file_sha256

    sha = file_sha256(plan)
    if calibration:
        (tmp_path / "cal.json").write_text(json.dumps(
            {"domain": "monsoon", "rainfall": "simulated", "passed": passed, "plan_sha256": sha}))
    if lock:
        (tmp_path / "family.lock").write_text("locked\n")
    return plan, sha


def test_firewall_opens_only_when_all_three_conditions_hold(tmp_path):
    idx, lic = registers()
    plan, sha = _registered_copy(tmp_path)
    assert MonsoonDomain(idx, lic, plan_path=plan, registered_plan_sha256=sha).firewall_status()["open"]
    assert not MonsoonDomain(idx, lic, plan_path=plan).firewall_status()["open"]
    assert not MonsoonDomain(idx, lic, plan_path=plan,
                             registered_plan_sha256="0" * 64).firewall_status()["open"]
    for kw, tag in (({"calibration": False}, "(b)"), ({"passed": False}, "(b)"),
                    ({"lock": False}, "(c)")):
        sub = tmp_path / tag.strip("()") / str(len(kw))
        sub.mkdir(parents=True, exist_ok=True)
        p2, s2 = _registered_copy(sub, **kw)
        st = MonsoonDomain(idx, lic, plan_path=p2, registered_plan_sha256=s2).firewall_status()
        assert not st["open"] and any(r.startswith(tag) for r in st["reasons"])


# ------------------------------------------------------- simulated outcomes
def test_simulated_outcomes_are_seasons_in_percent_of_lpa(sim):
    oc = sim.outcomes(GATE)
    assert oc["source"] == "simulated" and oc["unit"] == "season"
    anom = oc["series"]["all_india_jjas_anomaly_pct"]
    assert len(anom) == 146
    base = (oc["years"] >= 1951) & (oc["years"] <= 2000)
    assert abs(anom[base].mean()) < 1e-9
    drought = oc["series"]["all_india_drought"]
    assert set(np.unique(drought)) <= {0.0, 1.0}
    assert np.array_equal(drought == 1.0, anom < -10.0)
    assert "peninsular_india_jun_mm" in oc["series"]


def test_simulated_controls(sim):
    c = sim.controls(GATE)
    assert len(c["epoch_31y"]) == 146 and np.isnan(c["last_year_anomaly"][0])
    assert c["positive"][0]["id"] == "control.el_nino"
    if "oni_jas" in c:
        assert not c["el_nino_available"][YEARS < 1950].any()
        assert c["el_nino_available"][YEARS == 1997].all() and c["el_nino"].active[YEARS == 1997].all()
    else:
        assert "oni_jas" in c["missing"]


# -------------------------------------------------- the unit of evidence
def test_consecutive_active_seasons_are_one_episode():
    years = np.arange(1900, 1940)
    active = np.zeros(40, bool)
    active[[5, 6, 7, 20, 30]] = True
    vals = np.zeros(40)
    vals[[5, 6, 7]] = -9.0
    sd = season_differences(years, active, vals, half_window=15, min_inactive=5)
    assert sd.episodes == [(1905, 1907), (1920, 1920), (1930, 1930)]
    assert sd.n_active_seasons == 5
    assert np.allclose(sd.differences, [-9.0, 0.0, 0.0])


def test_baseline_stays_inside_the_period_and_thin_baselines_drop():
    years = np.arange(1950, 1971)
    active = np.zeros(21, bool)
    active[11] = True  # 1961, first confirm year
    vals = np.where(years <= 1960, 100.0, 0.0)
    vals[11] = 1.0
    sd = season_differences(years, active, vals, period=(1961, 1970), min_inactive=5)
    assert np.allclose(sd.differences, [1.0])  # explore years never enter the baseline
    sd = season_differences(years, active, vals, period=(1961, 1964), min_inactive=5)
    assert sd.n_dropped == 1 and len(sd.differences) == 0


def _iid_calendar(rng, p=3 / 7):
    return rng.random(len(YEARS)) < p


def _mars_like_calendar(rng):
    phase = rng.random()
    return ((YEARS / 1.88 + phase) % 1.0) < 0.42


@pytest.mark.parametrize("make", [_iid_calendar, _mars_like_calendar])
def test_null_calibration_on_simulated_rainfall(make):
    """No effect, slow epochs and AR(1) rain: one-sided rejections near 5 %."""
    rng = np.random.default_rng(11)
    reps, hits = 300, 0
    for r in range(reps):
        active = make(rng)
        rain = simulate_rainfall(YEARS, seed=1000 + r, epoch_amplitude_pct=6.0, phi=0.3)
        anom = rain["all_india"]["JJAS"].to_numpy() / 8.5 - 100.0
        res = season_test(YEARS, active, anom, direction="decrease", n_draws=499,
                          rng=np.random.default_rng(r))
        hits += res["p"] <= 0.05
    assert hits / reps <= 0.085


def test_planted_effect_is_found_with_the_right_sign():
    rng = np.random.default_rng(3)
    active = _iid_calendar(rng)
    rain = simulate_rainfall(YEARS, seed=5, effect_pct=-8.0, active=active)
    anom = rain["all_india"]["JJAS"].to_numpy() / 8.5 - 100.0
    res = season_test(YEARS, active, anom, direction="decrease", n_draws=1999)
    assert res["p"] < 0.01 and res["effect"] > 4.0
    assert res["ci95"][0] > 0 and res["x95"] >= res["effect"]
    wrong = season_test(YEARS, active, anom, direction="increase", n_draws=1999)
    assert wrong["p"] > 0.9


def test_adapter_season_effect_on_simulated_rain(sim):
    cal = sim.calendar(MEGH)
    assert len(cal.active) == 146 and 0.2 < cal.duty_cycle < 0.65
    res = sim.season_effect(cal, "all_india_jjas_anomaly_pct", GATE, which="confirm", n_draws=999)
    assert res["unit"] == "season" and res["period"] == [1961, 2016]
    assert res["n_episodes"] + res["n_dropped_episodes"] == len(cal.episodes((1961, 2016)))
    assert res["direction"] == "decrease" and 0.0 <= res["p"] <= 1.0
    dr = sim.season_effect(cal, "all_india_drought", GATE, n_draws=999)
    assert "risk_ratio" in dr["risk"]
    # gate G5 input: the smallest attainable p over confirm-period episodes
    assert sim.attainable_p(cal, "confirm") < by_rank1_threshold(sim.plan["budget_m"])


def test_shifted_calendar_is_a_negative_control(sim):
    cal = YearCalendar("x", YEARS, _iid_calendar(np.random.default_rng(0)))
    sh = cal.shifted(7)
    assert sh.active.sum() == cal.active.sum() and np.array_equal(np.roll(cal.active, 7), sh.active)


# ---------------------------------------------------------------- parsers
IITM_TEXT = """146  ALL-INDIA  RAINFALL    (1871-2016)          30 SUBDIVISIONS AREA 2880324 SQ.KM.
YEAR    JAN   FEB   MAR   APR   MAY   JUN   JUL   AUG   SEP   OCT   NOV   DEC    JF   MAM  JJAS   OND   ANN
1871    196   107   145   339   636  2080  2778  1794  1836   368   324    67   303  1120  8487   758 10670
1872     76    75    73   240   438  1892  2913  2452  1879   785   276   191   151   751  9136  1252 11289
MEAN    107   124   152   264   527  1630  2725  2422  1703   775   308   117   232   944  8481  1201 10859
146 PENINSULAR INDIA RAINFALL  (1871-2016)        6 SUBDIVISIONS AREA  442908 SQ.KM.
YEAR    JAN   FEB   MAR   APR   MAY   JUN   JUL   AUG   SEP   OCT   NOV   DEC    JF   MAM  JJAS   OND   ANN
1871    100   100   100   100   100  1000  1000  1000  1000   100   100   100   200   300  4000   300  4800
"""


def test_parse_iitm_regions():
    f = parse_iitm_regions(IITM_TEXT)
    assert set(f) == {"all_india", "peninsular_india"}
    assert f["all_india"].loc[1871, "JJAS"] == pytest.approx(848.7)
    assert list(f["all_india"].index) == [1871, 1872]
    assert f["peninsular_india"].loc[1871, "JUN"] == pytest.approx(100.0)


def test_parse_psl_monthly():
    text = (" 1950 1951\n1950 -1.32 -1.20 -1.12 -1.08 -1.10 -0.90 -0.62 -0.57 -0.56 -0.62 -0.66 -0.79\n"
            "1951 0.1 0.2 0.3 0.4 0.5 0.6 0.7 0.8 0.9 1.0 -99.99 -99.99\n  -99.99\n ONI\n")
    df = parse_psl_monthly(text)
    assert list(df.index) == [1950, 1951]
    assert df.loc[1950, "JAN"] == -1.32 and np.isnan(df.loc[1951, "DEC"])


def test_rule_file_with_wrong_domain_is_refused(tmp_path):
    src = (RULES / "_mars_in_rohini_deficit.yaml").read_text()
    (tmp_path / "x.yaml").write_text(src.replace("domain: monsoon", "domain: mundane"))
    with pytest.raises(PlanError):
        load_principles(tmp_path)


def test_leave_year_out_anomaly_sees_a_planted_spike():
    """D-06: the tested year no longer pulls its own baseline toward itself."""
    from vedic_astrology_core.domains.monsoon import (
        leave_year_out_anomaly_pct,
        leave_year_out_running_mean,
    )

    years = np.arange(1951, 2001)
    v = np.full(50, 100.0)
    v[10] = 200.0  # spike
    loo = leave_year_out_anomaly_pct(v, years, (1951, 2000))
    assert loo[10] == pytest.approx(100.0)  # baseline of the other 49 years is 100
    old = 100.0 * (v[10] - v.mean()) / v.mean()
    assert old < loo[10]  # the old mean understates it
    assert loo[0] == pytest.approx(-2.0)  # others' mean is 102.04: the spike counts for the others
    outside = leave_year_out_anomaly_pct([200.0], [2010], (1951, 2000))
    assert np.isnan(outside[0])  # no base years, no anomaly
    rm = leave_year_out_running_mean(v, 3)
    assert rm[10] == pytest.approx(100.0)  # excludes the spike itself
    assert rm[11] == pytest.approx((200.0 + 5 * 100.0) / 6)  # but a neighbour sees it


def test_long_nino34_control_is_loaded_when_pinned(tmp_path):
    import hashlib

    rows = ["          1870        1880"] + [
        f" {y}" + "".join(f" {26.0 + (y % 3):7.2f}" for _ in range(12)) for y in range(1870, 1881)
    ]
    f = tmp_path / "n34.data"
    f.write_text("\n".join(rows) + "\n")
    sha = hashlib.sha256(f.read_bytes()).hexdigest()
    import yaml

    plan = yaml.safe_load(PLAN.read_text())
    plan["controls"]["enso"]["nino34_long"] = {"file": str(f), "sha256": sha}
    p2 = tmp_path / "plan.yaml"
    p2.write_text(yaml.safe_dump(plan))
    dom = MonsoonDomain(*registers(), plan_path=p2, simulated=simulate_rainfall(YEARS, seed=1))
    out = dom._controls()
    assert out["nino34_long_covers"] == (1871, 1880)  # 1870 is outside the plan's grid
    assert "nino34_long" not in out["pending"]
