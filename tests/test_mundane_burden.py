"""Burden count, plan checks and the MDE table (ADR-006 WP-55)."""

import copy
from dataclasses import replace

import pytest

from vedic_astrology_core.mundane import burden as bd
from vedic_astrology_core.rules.predicates import PREDICATES


@pytest.fixture(scope="module")
def plan():
    return bd.load_plan()


def _plan(plan, edit):
    data = copy.deepcopy(plan.data)
    edit(data)
    return data


def test_plan_counts_match_declared(plan):
    counts = bd.check_declared(plan)
    assert counts["families"] == 4
    assert counts["omnibus_tests"] == 18
    assert counts["cells_total"] == 182
    assert counts["by_family"] == {"F1_dasha_lord_identity": 2, "F2_dasha_lord_natal_house": 4,
                                   "F3_dasha_lord_dignity": 4, "F4_transit_house_d1": 8}
    assert bd.check_budget(plan)["within_budget"]


def test_search_space_reproduces_section_5_1():
    s = bd.search_space()
    b = s["blocks"]
    assert b["A_dasha_lord_identity"] == 27
    assert b["B_dasha_lord_house_from_lagna"] == b["C_dasha_lord_house_from_moon"] == 324
    assert b["D_dasha_lord_rules_house"] == 324
    assert b["E_dasha_lord_dignity"] == 135
    assert b["F_transit_house_from_lagna"] == b["G_transit_house_from_moon"] == 972
    assert b["H_transit_conjunct_or_aspect_natal"] == 1458
    assert b["I_transit_read_in_own_varga"] == 27216
    assert s["dasha_factors"] == 1134 and s["transit_factors"] == 30618
    assert abs(s["single_factors"] - 32000) / 32000 < 0.01          # "about 32,000"
    assert abs(s["pairs_dasha_by_transit"] - 35e6) / 35e6 < 0.01     # "about 35 million"
    assert s["multiplier"] == 84
    assert s["always_true_BCFG"] == 216
    assert abs(s["chance_significant_at_0_05"] - 1600) / 1600 < 0.01
    # "about 2,800" true statements at any moment (block J excluded here).
    assert abs(s["true_at_any_moment"]["total_excluding_J"] - 2800) / 2800 < 0.10


def test_mde_table_reproduces_section_5_4(plan):
    t = bd.mde_table(plan)
    for key in ("duty_0.10", "duty_0.25"):
        for got, want in zip(t["rows"][key], plan["mde"][key]):
            assert got[0] == want[0]
            for g, w in zip(got[1:], want[1:]):
                # The plan's table is printed to one decimal; one cell (100 events,
                # duty 0.25, Bonferroni 1.6e-6) reads 3.2 where the exact value is 3.09.
                assert abs(g - float(w)) <= max(0.06, 0.04 * float(w)), (key, got, want)
    assert t["check"]["computed"] == pytest.approx(1.63, abs=0.005)
    assert bd.by_rank1_alpha(24) == pytest.approx(5.5e-4, rel=0.01)
    assert bd.by_rank1_alpha(60) == pytest.approx(1.8e-4, rel=0.03)


def test_burden_report_and_file(plan, tmp_path):
    r = bd.burden_report(plan)
    assert r["plan_counts"]["omnibus_tests"] == 18
    assert r["event_floor"] == 30
    path = bd.write_burden(r, tmp_path / "burden.json")
    assert path.read_text().startswith("{")


def test_declared_counts_must_match(plan):
    data = _plan(plan, lambda d: d["declared_counts"].update(omnibus_tests=17))
    with pytest.raises(bd.PlanError, match="declared counts"):
        bd.check_declared(bd.plan_from_dict(data))
    data = _plan(plan, lambda d: d["families"][3]["tests"].pop())  # a test removed silently
    with pytest.raises(bd.PlanError, match="declared counts"):
        bd.check_declared(bd.plan_from_dict(data))


def test_over_budget_fails(plan):
    data = _plan(plan, lambda d: d["budgets"].update(max_omnibus_tests_first_slice=10))
    with pytest.raises(bd.BudgetExceeded):
        bd.burden_report(bd.plan_from_dict(data))
    with pytest.raises(bd.BudgetExceeded):
        bd.check_budget(plan, programme_used=190)


def test_plan_schema_is_strict(plan):
    with pytest.raises(bd.PlanError, match="unknown key"):
        bd.plan_from_dict(_plan(plan, lambda d: d.update(extra=1)))
    with pytest.raises(bd.PlanError, match="missing key"):
        bd.plan_from_dict(_plan(plan, lambda d: d.pop("budgets")))
    with pytest.raises(bd.PlanError, match="schema"):
        bd.plan_from_dict(_plan(plan, lambda d: d.update(schema="mundane-plan/0")))
    with pytest.raises(bd.PlanError, match="unknown key"):
        bd.plan_from_dict(_plan(plan, lambda d: d["families"][0]["tests"][0].update(alpha=1)))


def test_purely_natal_factor_is_rejected(plan, monkeypatch):
    fake = replace(PREDICATES["dasha_lord_is"], name="natal_graha_in_house")
    monkeypatch.setitem(PREDICATES, "natal_graha_in_house", fake)

    def edit(d):
        d["families"][0]["tests"][0]["predicate"] = "natal_graha_in_house"

    with pytest.raises(bd.NatalFactorError, match="purely natal"):
        bd.plan_from_dict(_plan(plan, edit))


def test_tests_are_partitions(plan):
    tests = bd.plan_tests(plan)
    assert len(tests) == 18
    ids = [t.id for t in tests]
    assert len(set(ids)) == 18
    antar = tests[0]
    assert antar.cell_params("Saturn") == {"level": 2, "lords": ["Saturn"]}
    d9 = next(t for t in tests if t.id == "dasha.dignity.antar.d9")
    assert "moolatrikona" not in d9.collapse["own"]          # undefined outside D1
    d1 = next(t for t in tests if t.id == "dasha.dignity.antar.d1")
    assert d1.collapse["own"] == ("moolatrikona", "own")
    with pytest.raises(bd.PlanError, match="two or more"):
        bd.plan_from_dict(_plan(plan, lambda d: d["families"][0]["tests"][0].update(cells=["Sun"])))
