"""Bindings from plan and rule files to a run (strategy audit 2 N-05; ADR-008 sections 3, 7, 8).

No outcome is read here: plans are validated, rules expanded and tests built
from the files; calendars are not evaluated except where a test says so.
Snapshot files are not committed (hash only), so the gold binding is skipped
where the Bundesbank snapshot is absent.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

from vedic_astrology_core.rules import levels as L
from vedic_astrology_core.rules.schema import Rule, registration_problems
from vedic_astrology_core.validity import bindings as B
from vedic_astrology_core.validity import plan as PL
from vedic_astrology_core.validity import variants as VR

ROOT = Path(__file__).resolve().parents[1]
PLANS = ROOT / "studies" / "validity" / "domains"
GOLD_SNAPSHOT = ROOT / "data" / "snapshots" / "bundesbank_gold_dem_87c15f38332d.csv"


@pytest.fixture(scope="module")
def rules():
    return B.load_rule_files(ROOT)


@pytest.fixture(scope="module")
def eq(rules):
    return B.bind(PLANS / "earthquake.yaml", root=ROOT, rule_files=rules, check_detrend=False)


@pytest.fixture(scope="module")
def monsoon(rules):
    return B.bind(PLANS / "monsoon.yaml", root=ROOT, rule_files=rules, check_detrend=False)


# ------------------------------------------------------------------ plans
@pytest.mark.parametrize("name", ["earthquake", "metals", "monsoon"])
def test_domain_plans_are_valid_drafts_awaiting_only_the_owner(name):
    plan = yaml.safe_load((PLANS / f"{name}.yaml").read_text())
    sesoi = PL.load_sesoi_sources(ROOT / "studies/validity/sesoi_sources.yaml")
    index = json.loads((ROOT / "data/snapshot_index.json").read_text())
    assert plan["status"] == "draft"
    assert PL.validate_plan(plan, sesoi_sources=sesoi, snapshot_index=index) == []
    plan["status"] = "registered"
    errs = PL.validate_plan(plan, sesoi_sources=sesoi, snapshot_index=index)
    assert errs and all(e.startswith("owner_signoffs.") for e in errs)
    assert all(v is None for v in plan["owner_signoffs"].values())


def test_bind_refuses_a_plan_that_fails_the_validator(tmp_path, rules):
    plan = yaml.safe_load((PLANS / "earthquake.yaml").read_text())
    plan["outcomes"][0]["sesoi"] = {"kind": "project", "value": 2.0}  # a SESOI chosen by the project (S-13)
    p = tmp_path / "earthquake.yaml"
    p.write_text(yaml.safe_dump(plan))
    with pytest.raises(PL.PlanError, match="sesoi"):
        B.bind(p, root=ROOT, rule_files=rules, check_detrend=False)


# ------------------------------------------------------------ rule files
def test_the_41_study_rules_are_registrable(rules):
    study = {k: v for k, v in rules.items() if ".study." in k}
    assert len(study) == 41
    assert {k: registration_problems(v.rule) for k, v in study.items() if registration_problems(v.rule)} == {}
    for rf in study.values():  # published is the study plan's registered date or the text's, never blank
        assert rf.rule.source.published in ("2026-11-08", "550")


def test_monsoon_rules_registrable_where_the_source_date_is_known(rules):
    probs = {k: registration_problems(v.rule) for k, v in rules.items() if k.startswith("monsoon.")}
    assert probs["monsoon.mars_in_rohini_deficit"] == []
    assert probs["monsoon.varsheshvara_malefic_deficit"] == []
    # no publication date is known for the AstroFusion registry entry: it stays unregistrable
    assert probs["monsoon.meghesha_malefic_deficit"] == ["source.published: missing"]


def test_mandala_rules_declare_project_extension_once():
    for f in sorted((ROOT / "rules/seismic/study").glob("moon_mandala_*.yaml")):
        text = f.read_text()
        assert text.count("project_extension:") == 1, f.name


# ------------------------------------------------------------- variants
def _rule_with_variants(rules, n_candidates: int, tropical: bool = False) -> Rule:
    """The Mars-in-Rohini rule (params window_before 0..3, window_after 0..6) with declared variants."""
    doc = copy.deepcopy(rules["monsoon.mars_in_rohini_deficit"].rule._template)
    doc["domain"] = "mundane"  # the schema's domain enum has no monsoon yet (as the monsoon loader does)
    doc["variants"] = [{"id": f"after_{i}", "role": "candidate", "params": {"window_after": i}, "reason": "declared"}
                       for i in range(n_candidates)]
    doc["variants"].append({"id": "true_node", "role": "sensitivity", "conventions": {"node_model": "true"}})
    if tropical:
        doc["variants"].append({"id": "tropical", "role": "sensitivity", "conventions": {"zodiac": "tropical"}})
    return Rule.model_validate(doc)


def test_expand_gives_primary_candidates_and_cells(rules):
    rule = _rule_with_variants(rules, 2)
    exps = VR.expand(rule, "monsoon")
    first = "peninsular_india_jjas_anomaly_pct"
    assert [(e.variant, e.test.outcome) for e in exps][:3] == [
        ("primary", first), ("after_0", first), ("after_1", first)]
    assert len(exps) == 9  # three outcomes x (primary + two candidates)
    prim = exps[0]
    assert set(prim.sensitivity) == {"true_node"} and prim.sensitivity["true_node"].node_model == "true"
    assert exps[1].rule.params["window_after"].value == 0 and exps[1].role == "candidate"
    assert not exps[1].sensitivity and prim.side == "less"


def test_more_than_three_candidates_go_to_the_sensitivity_grid(rules):
    exps = VR.expand(_rule_with_variants(rules, 5), "monsoon", outcomes=["all_india_jjas_anomaly_pct"])
    assert [e.variant for e in exps] == ["primary", "after_0", "after_1", "after_2"]
    assert exps[0].demoted == ("after_3", "after_4")
    assert {"after_3", "after_4", "true_node"} == set(exps[0].sensitivity)


def test_a_variant_out_of_range_is_refused(rules):
    doc = copy.deepcopy(rules["monsoon.mars_in_rohini_deficit"].rule._template)
    doc["domain"] = "mundane"
    rule = Rule.model_validate(doc)
    bad = rule.variants  # none declared; bind one by hand outside its range
    with pytest.raises(VR.VariantError):
        VR.bound_rule(rule, type("V", (), {"params": {"window_after": 99}, "conventions": None, "id": "x"})())
    assert bad == []


def test_a_cell_the_evaluator_cannot_compute_is_listed_not_dropped(rules):
    exps = VR.expand(_rule_with_variants(rules, 0, tropical=True), "monsoon",
                     outcomes=["all_india_jjas_anomaly_pct"])
    assert any("tropical" in p for p in exps[0].not_computable)


# ------------------------------------------------------- built test inputs
def test_every_verdict_input_comes_from_the_files(eq, rules):
    assert eq.domain == "earthquake" and eq.run.plan_sha256 == PL.plan_hash(eq.plan)
    assert eq.run.vintage["seen"] is True and eq.run.vintage["id"] == eq.plan["active_vintage"]
    by_id = {b.definition.rule_id: b for b in eq.tests}
    b = by_id["seismic.study.moon_mandala_agni"]
    t, rule = b.definition, rules["seismic.study.moon_mandala_agni"].rule
    assert t.level == L.level(rule).level
    assert t.source_published == rule.source.published == "550"
    assert t.sesoi is None  # the plan's SESOI is null: E impossible (7.2 rule 3)
    assert t.reading_differs is True and t.project_extension is True
    assert t.outcome_type == "events" and t.base_rate == eq.plan["outcomes"][0]["base_rate"]
    assert t.side == "two-sided"
    assert by_id["seismic.study.mars_ketu_conj"].definition.side == "greater"
    assert t.x_grid == [float(x) for x in eq.plan["outcomes"][0]["grid_x"]]
    assert b.registrable and b.problems == ()


def test_rules_without_conditions_are_counted_not_encodable(eq):
    ne = {e.rule_id for e in eq.excluded if e.category == "not_encodable"}
    assert ne == {f"seismic.study.station_{p}" for p in ("jupiter", "mars", "mercury", "saturn", "venus")}
    assert eq.run.sampling_frame["not_encodable"] == 5


def test_a_declared_baseline_without_data_leaves_no_baselines(eq):
    # REVIEW_1 fix 4: the solar term is now built from the pinned SILSO snapshot; only a clone
    # without that hash-only file still gets no baselines (R1 and R4 then cannot pass, conservative).
    silso = ROOT / "data" / "snapshots" / "silso_sn_monthly_1cf8a1f6f28f.csv"
    if silso.is_file():
        assert "baselines_missing" not in eq.notes and eq.run.baselines is not None
    else:
        assert eq.notes["baselines_missing"] == ["solar_cycle"]
        assert eq.run.baselines is None


def test_disputed_rules_get_the_flag_from_disputes_md(tmp_path, rules):
    rid = "seismic.study.mars_ketu_conj"  # directional (increase)
    b = B.bind(PLANS / "earthquake.yaml", root=ROOT, rule_files=rules, disputes=[rid], check_detrend=False)
    t = next(x for x in b.tests if x.definition.rule_id == rid)
    assert t.definition.direction_disputed is True
    assert t.definition.test_id in {x.test_id for x in b.tests if not x.registrable}  # directional and disputed
    assert B.disputed_rule_ids(tmp_path) == []
    named = B.disputed_rule_ids(ROOT)  # DISPUTES.md names files; they are read as rule ids (A-08)
    for f in ("rules/financial/practitioner/vyapar_ratna_inverse_dignity_gold.yaml",
              "rules/financial/practitioner/tempora_jupiter_cancer_gold_peak.yaml"):
        assert yaml.safe_load((ROOT / f).read_text())["id"] in named


def test_unregistrable_rules_are_built_but_not_registered(monsoon):
    meg = [b for b in monsoon.tests if b.definition.rule_id == "monsoon.meghesha_malefic_deficit"]
    assert meg and all(not b.registrable for b in meg)
    assert all(t.rule_id != "monsoon.meghesha_malefic_deficit" for t in monsoon.registrable_tests())
    assert monsoon.run.sampling_frame["not_sourced"] == 1


def test_monsoon_grid_is_one_date_per_season_and_calendars_are_yearly(monsoon):
    g = pd.DatetimeIndex(monsoon.adapter.grid())
    assert g[0] == pd.Timestamp("1948-07-01") and g[-1] == pd.Timestamp("2016-07-01")
    t = next(b.definition for b in monsoon.tests if b.definition.rule_id == "monsoon.varsheshvara_malefic_deficit")
    cal = np.asarray(t.calendar(g[:5]))
    assert cal.dtype == bool and cal.shape == (5,)
    # a date shifted inside the same year reads the same season
    assert (np.asarray(t.calendar(g[:5] + pd.Timedelta(days=30))) == cal).all()


def test_monthly_data_needs_a_month_horizon():
    assert B.horizon_allows_monthly("the June to September season of the same year")
    assert not B.horizon_allows_monthly("the next bar of the outcome series")


@pytest.mark.skipif(not GOLD_SNAPSHOT.is_file(), reason="Bundesbank snapshot not on disk (hash-only data)")
def test_gold_binding_declares_long_gaps_and_burn_in_missing(rules):
    b = B.bind(PLANS / "metals.yaml", root=ROOT, rule_files=rules, check_detrend=False)
    assert b.domain == "gold" and b.notes["long_gap_bars"] > 0
    g = pd.DatetimeIndex(b.adapter.grid())
    m = b.run.missing_bars["gold_dem_frankfurt_extreme_move"](g)
    assert m[:500].all() and m.sum() >= 500
    lr = b.run.missing_bars["gold_dem_frankfurt_log_return"](g)
    assert lr.sum() == b.notes["long_gap_bars"]  # N-20: long-gap returns are declared, not merged
    t = next(x.definition for x in b.tests if x.definition.outcome.endswith("abs_return"))
    assert t.outcome_type == "log_ratio" and t.market == "frankfurt" and t.currency == "dem"
    silver = {e.rule_id for e in b.excluded if e.outcome.startswith("silver.")}
    assert len(silver) == 14 and b.run.sampling_frame["untestable"] == 14


# ------------------------------------------------------------- adapters
def test_bound_adapter_checks_the_gate_and_the_pinned_bytes_before_any_row(tmp_path):
    from vedic_astrology_core.domains.base import GateHashError, write_gate

    class Inner:
        reads = 0

        def outcomes(self, gate=None, *, gate_path=None):
            Inner.reads += 1
            return {"x": [1.0, 2.0]}

    grid = pd.DatetimeIndex(["2000-01-01", "2000-01-02"])

    def bad_pin():
        raise B.BindingError("bytes do not hash to the plan's pinned SHA-256")

    ad = B.BoundAdapter(Inner(), "d", {"x": lambda raw: raw["x"]}, grid=grid, verify=bad_pin)
    with pytest.raises(GateHashError):
        ad.outcomes("ab" * 32)
    gate = write_gate(tmp_path / "gate.json", {"tests": {}})
    with pytest.raises(B.BindingError, match="pinned"):
        ad.outcomes(gate)
    assert Inner.reads == 0
    ok = B.BoundAdapter(Inner(), "d", {"x": lambda raw: raw["x"]}, grid=grid,
                        missing={"x": np.array([True, False])})
    assert np.isnan(ok.outcomes(gate)["x"][0]) and ok.outcomes(gate)["x"][1] == 2.0


def test_rules_of_one_domain_share_their_sky(rules):
    group = B.SkyGroup()
    a = B.SkyCalendar(rules["seismic.study.mars_ketu_conj"].rule, B._utc, group=group)
    b = B.SkyCalendar(rules["seismic.study.mars_saturn_conj"].rule, B._utc, group=group)
    hours = pd.date_range("2001-01-01", periods=48, freq="h", tz="UTC")
    a(hours)
    assert len(b._cache) == len(a._cache) == 48  # one sky for both
    shifted = hours + pd.Timedelta(days=400)
    assert (np.asarray(b(hours)) == np.asarray(b(hours))).all() and len(b(shifted)) == 48
    # an index in microseconds reads the same instants (no unit confusion)
    assert (a(hours.as_unit("us")) == a(hours)).all()


def test_earthquake_outcome_is_the_mainshock_count_per_hourly_bar(eq):
    fn = eq.adapter._fns["mainshock_rate"]
    n = len(eq.adapter.grid())
    y = fn({"event_bins_by_method": {"gk": np.array([0, 0, 5]), "nn": np.array([1])}})
    assert y.shape == (n,) and y[0] == 2 and y[5] == 1 and y.sum() == 3
    assert pd.DatetimeIndex(eq.adapter.grid()).tz is None  # naive UTC: the pipeline's period masks compare
