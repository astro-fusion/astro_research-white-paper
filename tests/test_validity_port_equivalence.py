"""WP-71: study indicators ported to rule files give the same calendar.

For each indicator of the gold, silver and earthquake plans there is one rule
file under rules/financial/study or rules/seismic/study. The calendar the rule
engine produces on a grid must equal the old study calendar bit for bit, or
the difference is listed in KNOWN_DIFFS with its cause. No outcome is read:
the grids are plain time grids and the old calendars come from the sky alone.
"""

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

from vedic_astrology_core.rules import default_rules_dir, load_rules
from vedic_astrology_core.rules.grid import GridEvaluator

REPO = Path(__file__).resolve().parents[1]
LOADED, PROBLEMS = load_rules([default_rules_dir()])
BY_ID = {item.rule.id: item.rule for item in LOADED}

PLANS = {
    "gold": ("financial", REPO / "studies/gold_market/hypothesis.yaml"),
    "silver": ("financial", REPO / "studies/silver_market/hypothesis.yaml"),
    "earthquake": ("seismic", REPO / "studies/earthquake/hypothesis.yaml"),
}
#: Station windows need a predicate that does not exist yet (see the files).
NEEDS_PREDICATE = {f"station_{b}" for b in ("mars", "mercury", "venus", "jupiter", "saturn")}
#: indicator -> (largest allowed share of differing steps, cause). Empty: exact.
KNOWN_DIFFS = {
    "sun_ingress": (
        0.01,
        "the old study opens the window at the first grid step in the new sign, "
        "the rule at the exact ingress time, so each window edge differs by at "
        "most one step",
    ),
    "eclipse_window": (
        0.005,
        "the old study rounds an eclipse maximum to the nearest grid step before "
        "widening it, so its window may open or close one step earlier or later "
        "than the exact +/- 7 days of the rule (new is never wider than old by "
        "more than that); lunar penumbral-only eclipses are excluded by "
        "penumbral: false, as in the old Swiss Ephemeris search",
    ),
}


def _plan_ids(name):
    hyp = yaml.safe_load(PLANS[name][1].read_text())
    return hyp, [i["id"] for i in hyp["indicators"]]


def _rule_id(name, iid):
    domain = PLANS[name][0]
    return (
        f"financial.study.{name}_{iid}" if domain == "financial" else f"seismic.study.{iid}"
    )


def test_study_rule_files_load_clean():
    assert not [p for p in PROBLEMS if "/study/" in str(p)]


def test_one_rule_file_per_plan_indicator():
    total = 0
    for name in PLANS:
        _, ids = _plan_ids(name)
        for iid in ids:
            rule = BY_ID.get(_rule_id(name, iid))
            assert rule is not None, f"{name}.{iid} has no rule file"
            assert rule.notes["plan_indicator"] == iid
            total += 1
    assert total == 41


@pytest.mark.parametrize("name", sorted(PLANS))
def test_each_port_says_how_it_is_read_and_has_two_cases(name):
    _, ids = _plan_ids(name)
    for iid in ids:
        rule = BY_ID[_rule_id(name, iid)]
        assert rule.reading is not None and rule.operationalisation, rule.id
        assert rule.tests and all(t.domain == name for t in rule.tests), rule.id
        if iid in NEEDS_PREDICATE:
            assert rule.status == "needs_predicates" and rule.conditions is None
            continue
        assert rule.status == "active", rule.id
        assert {c.expect for c in rule.reference_cases} == {"fires", "silent"}, rule.id


def test_outcome_slots_per_domain():
    """Gold 14 x 3, silver 14 x 2, earthquake 13 x 1: 70 slots, inside the budgets."""
    slots = {"gold": 0, "silver": 0, "earthquake": 0}
    for rule in BY_ID.values():
        if ".study." in rule.id:
            for t in rule.tests:
                slots[t.domain] += 1
    assert slots == {"gold": 42, "silver": 28, "earthquake": 13}


def _compare(iid, old, new, where):
    old = np.asarray(old, dtype=bool)
    new = np.asarray(new, dtype=bool)
    assert old.shape == new.shape
    share = float(np.mean(old != new))
    allowed, cause = KNOWN_DIFFS.get(iid, (0.0, "exact"))
    if allowed:  # a listed difference may only move a window edge by one step
        edges = np.flatnonzero(old[1:] != old[:-1])
        for i in np.flatnonzero(old != new):
            assert np.abs(edges - i).min() <= 1, f"{where}.{iid}: step {i} is not at a window edge"
    assert share <= allowed, (
        f"{where}.{iid}: {share:.4%} of steps differ "
        f"({int((old != new).sum())} of {len(old)}); allowed {allowed:.4%} ({cause})"
    )


@pytest.fixture(scope="module")
def market_grid():
    from vedic_astrology_core.astrology.ephemeris import EphemerisEngine
    from vedic_astrology_core.markets import features

    instants = pd.date_range("1996-01-01 12:00", "2024-12-31 12:00", freq="6D", tz="UTC")
    bodies = ["SUN", "MOON", "MARS", "MERCURY", "VENUS", "JUPITER", "SATURN"]
    engine = EphemerisEngine()
    frame = features.indicator_frame(
        instants, bodies, engine, rules_use_case="financial"
    )
    return instants, frame, GridEvaluator(instants)


@pytest.mark.parametrize("name", ["gold", "silver"])
def test_market_calendars_equal_old_study(name, market_grid):
    from vedic_astrology_core.markets import features

    instants, frame, evaluator = market_grid
    hyp, _ = _plan_ids(name)
    for spec in hyp["indicators"]:
        iid = spec["id"]
        try:
            old = features.build_indicators(frame, [spec])[iid].to_numpy()
        except ValueError as err:  # never active on this grid
            assert "never active" in str(err)
            old = np.zeros(len(instants), dtype=bool)
        new = evaluator.indicator(BY_ID[_rule_id(name, iid)])
        _compare(iid, old, new, name)


def _load_old_indicators():
    scripts = REPO / "studies/earthquake/scripts"
    spec = importlib.util.spec_from_file_location(
        "eq_study_indicators", scripts / "indicators.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_earthquake_calendars_equal_old_study():
    from vedic_astrology_core.astrology.ephemeris import EphemerisEngine

    old = _load_old_indicators()
    hyp, _ = _plan_ids("earthquake")
    grid = old.time_grid("2001-01-01", "2004-01-01", step_hours=6)
    eph = old.ephemeris_frame(grid, EphemerisEngine())
    specs = [i for i in hyp["indicators"] if i["id"] not in NEEDS_PREDICATE]
    frame = old.build_indicators({**hyp, "indicators": specs}, eph)
    evaluator = GridEvaluator(grid)
    for spec in specs:
        iid = spec["id"]
        new = evaluator.indicator(BY_ID[_rule_id("earthquake", iid)])
        _compare(iid, frame[iid].to_numpy(), new, "earthquake")
