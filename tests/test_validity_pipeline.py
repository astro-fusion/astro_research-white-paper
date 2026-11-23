"""ADR-007 WP-69 (amended by ADR-008): the validity pipeline end to end on the SimulatedDomain.

No real outcome is read. The domain is a subclass of the toy SimulatedDomain
whose planted effect sits on the calendar the test evaluates (two active
years in every six, so every episode gets equal-size neighbour blocks).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from datetime import date

import numpy as np
import pandas as pd
import pytest
import yaml
from scipy import stats as _st

from vedic_astrology_core.domains.base import DomainAdapter, Periods
from vedic_astrology_core.domains.simulated import SimulatedDomain, simulated_grades, simulated_registers
from vedic_astrology_core.rules.schema import Rule
from vedic_astrology_core.validity import pipeline as P
from vedic_astrology_core.validity import report as RP
from vedic_astrology_core.validity import sealbundle as SB
from vedic_astrology_core.validity.family import FamilyLock, calendar_hash

ROOT = Path(__file__).resolve().parents[1]
MANDALA = ROOT / "rules/mundane/practitioner/bs32_agni_mandala_earthquake.yaml"
START, YEARS = 1700, 300
VINTAGE = {"id": "sim_v1", "confirm_period": {"start": "1880-01-01", "end": "1999-12-31"}, "seen": False}
SEED = 20261122


def active_years(dates) -> np.ndarray:
    years = np.asarray([d.year for d in dates])
    return (years % 6) < 2


class PlantedDomain(SimulatedDomain):
    """SimulatedDomain with its effect planted on active_years() and a read spy."""

    def __init__(self, *, seed: int, effect: float, run_dir: Path, trend: float = 0.0):
        super().__init__(seed=seed, n_years=YEARS, start_year=START, effect=0.0)
        rng = np.random.default_rng(seed + 7919)
        self._active = active_years(self.grid()).astype(float)
        t = np.arange(YEARS) / YEARS
        self._values = rng.normal(size=YEARS) + effect * self._active + trend * t
        self.sha256 = hashlib.sha256(self._values.tobytes()).hexdigest()
        index, licences = simulated_registers(self.sha256)
        DomainAdapter.__init__(self, index, licences, simulated_grades(self.sha256))
        self.run_dir = Path(run_dir)
        self.seen_at_read = []

    def _outcomes(self):
        gates = sorted(p.name for p in (self.run_dir / "gates").glob("*.json"))
        self.seen_at_read.append({"gate_json": (self.run_dir / "gate.json").is_file(), "gates": gates})
        return super()._outcomes()


def rule() -> Rule:
    doc = yaml.safe_load(MANDALA.read_text())
    doc.update(
        reading={"kind": "concurrent"},
        operationalisation=[
            {"choice": "day_convention", "value": "utc_day", "fixed_by": "project", "alternatives": ["local_day"]},
            {"choice": "place", "value": "Greenwich", "fixed_by": "project", "alternatives": ["Delhi"]},
            {"choice": "horizon", "value": 0, "fixed_by": "text"},
        ],
        tests=[{"domain": "simulated", "outcome": "value", "direction": "either", "project_extension": True}],
    )
    return Rule.model_validate(doc)


RULE = rule()


def definition(version: int = 1, calendar=active_years, **over) -> P.TestDefinition:
    kw = dict(
        rule_id="sim.two_in_six", version=version, outcome="value", calendar=calendar, side="greater",
        outcome_type="continuous", x_grid=np.round(np.linspace(0.05, 4.0, 80), 4).tolist(),
        name="Simulated principle", level=2, rule=RULE, sesoi=0.8, noise_sd=1.0,
        source_published="1600", n_draws=1999, power_reps=50,
        sensitivity={"two_in_twelve": lambda d: np.asarray([x.year % 12 < 2 for x in d])},
    )
    kw.update(over)
    return P.TestDefinition(**kw)


def run_spec(**over) -> P.DomainRun:
    kw = dict(domain="simulated", plan_seed=SEED, plan_sha256="cd" * 32, vintage=VINTAGE,
              baselines=lambda d: np.asarray([(x.year - 1850) / 100.0 for x in d]),
              plan={"domain": "simulated", "outcomes": [{"id": "value"}], "vintages": [VINTAGE]})
    kw.update(over)
    return P.DomainRun(**kw)


class FakeSeal:
    """Stands in for SealedRun on a clean, committed tree (the working tree here is not)."""

    calls = []

    def __init__(self, provisional: bool):
        self.provisional = provisional
        FakeSeal.calls.append(provisional)

    def __enter__(self):
        return self

    def finish(self, engine=None):
        return {"provisional": self.provisional, "commit": "c0ffee", "dirty": False,
                "problems": [], "files_read": [], "threads_started": 0}

    def __exit__(self, *exc):
        return False


def make_lock(tmp_path: Path, tests, close: bool = True) -> FamilyLock:
    lock = FamilyLock(tmp_path / "lock.jsonl", "simulated")
    import pandas as pd
    dates = pd.DatetimeIndex([pd.Timestamp(START + i, 1, 1) for i in range(YEARS)])
    for t in tests:
        lock.register(rule_id=t.rule_id, version=t.version, outcome=t.outcome,
                      calendar_hash=calendar_hash(np.asarray(t.calendar(dates), dtype=bool)))
    if close:
        lock.close_batch(vintage=VINTAGE, seal_bundle_sha256="ab" * 32)
    return lock


def handle_for(tests, token: str = "test-handle") -> SB.ConfirmHandle:
    """A handle registered as issued (the issuing checks are tested in test_confirm_bypass.py)."""
    h = SB.ConfirmHandle(domain="simulated", batch=1, bundle_sha256="ab" * 32, bundle_path="seals/sim.json",
                         ots_path="seals/sim.json.ots", block_height=1, vintage_id="sim_v1",
                         period=("1880-01-01", "1999-12-31"), test_ids=tuple(t.test_id for t in tests),
                         ledger_commit="c0ffee", token=token)
    SB._ISSUED[token] = h
    return h


def confirm_run(tmp_path: Path, effect: float, seed: int = 1, tests=None, **kw):
    tests = tests or [definition()]
    lock = make_lock(tmp_path, tests)
    dom = PlantedDomain(seed=seed, effect=effect, run_dir=tmp_path / "run")
    h = handle_for(tests, token=f"tok-{seed}-{effect}-{tmp_path.name}")
    try:
        res = P.run_domain(dom, run_spec(), tests, lock, tmp_path / "run", handle=h, provisional=False,
                           sealer=FakeSeal, **kw)
    finally:
        SB._ISSUED.pop(h.token, None)
    return res, dom, lock


# ------------------------------------------------------------------ order
def test_no_outcome_is_read_before_the_gate_is_written(tmp_path):
    res, dom, _ = confirm_run(tmp_path, effect=1.5)
    assert dom.outcome_reads == 1
    assert dom.seen_at_read == [{"gate_json": True, "gates": [P.record_id_for(definition().test_id) + ".json"]}]
    gate = tmp_path / "run" / "gate.json"
    assert hashlib.sha256(gate.read_bytes()).hexdigest() == res["gate"]["sha256"]
    rec = res["records"][0]
    gfile = tmp_path / "run" / rec["gate"]["file"]
    assert hashlib.sha256(gfile.read_bytes()).hexdigest() == rec["gate"]["file_sha256"]


def test_outcomes_refuse_without_the_written_gate(tmp_path):
    dom = PlantedDomain(seed=1, effect=0.0, run_dir=tmp_path)
    with pytest.raises(Exception):
        dom.outcomes("0" * 64, gate_path=tmp_path / "gate.json")
    assert dom.outcome_reads == 0


def test_untestable_test_reads_no_outcome(tmp_path):
    sparse = lambda d: np.asarray([x.year % 60 < 2 for x in d])  # noqa: E731 - five episodes in 300 years
    t = definition(calendar=sparse)
    res, dom, _ = confirm_run(tmp_path, effect=0.0, tests=[t])
    assert res["records"][0]["verdict"]["code"] == "U"
    assert dom.outcome_reads == 0
    assert res["records"][0]["effect"] is None


def test_rule_that_fails_to_evaluate_stops_the_run(tmp_path):
    def broken(d):
        raise KeyError("Moon")

    good = definition()
    lock = make_lock(tmp_path, [good])
    dom = PlantedDomain(seed=1, effect=0.0, run_dir=tmp_path / "run")
    with pytest.raises(P.PipelineError, match="failed to evaluate"):
        P.run_domain(dom, run_spec(), [good, definition(version=2, calendar=broken)], lock,
                     tmp_path / "run", sealer=FakeSeal)
    assert dom.outcome_reads == 0
    assert not (tmp_path / "run" / "gate.json").exists()


def test_changed_calendar_or_unregistered_test_stops_the_run(tmp_path):
    lock = make_lock(tmp_path, [definition()], close=False)
    dom = PlantedDomain(seed=1, effect=0.0, run_dir=tmp_path / "run")
    moved = definition(calendar=lambda d: np.asarray([x.year % 6 in (1, 2) for x in d]))
    with pytest.raises(P.PipelineError, match="calendar changed"):
        P.run_domain(dom, run_spec(), [moved], lock, tmp_path / "run", sealer=FakeSeal)
    with pytest.raises(P.PipelineError, match="not registered"):
        P.run_domain(dom, run_spec(), [definition(version=2)], lock, tmp_path / "run", sealer=FakeSeal)
    assert dom.outcome_reads == 0


def test_version_bump_takes_a_new_registration(tmp_path):
    v1 = definition()
    lock = make_lock(tmp_path, [v1])  # batch 1 closed
    v2 = definition(version=2, calendar=lambda d: np.asarray([x.year % 6 in (2, 3) for x in d]))
    import pandas as pd
    dates = pd.DatetimeIndex([pd.Timestamp(START + i, 1, 1) for i in range(YEARS)])
    e = lock.register(rule_id=v2.rule_id, version=2, outcome="value",
                      calendar_hash=calendar_hash(v2.calendar(dates)))
    assert e["batch"] == 2 and v2.test_id != v1.test_id
    assert lock.test_record(v1.test_id)["batch"] == 1
    dom = PlantedDomain(seed=3, effect=0.0, run_dir=tmp_path / "run")
    res = P.run_domain(dom, run_spec(), [v1, v2], lock, tmp_path / "run", sealer=FakeSeal)
    by = {r["test_id"]: r for r in res["records"]}
    assert by[v2.test_id]["eligibility"]["row"] == "after_close_same_vintage"
    assert "registered_after_unblinding" in by[v2.test_id]["verdict"]["flags"]
    assert by[v2.test_id]["verdict"]["code"] in ("N", "U")


# ------------------------------------------------------------ holdout
def test_provisional_run_reads_explore_rows_only_and_gives_no_s(tmp_path):
    t = definition()
    lock = make_lock(tmp_path, [t])
    dom = PlantedDomain(seed=1, effect=1.5, run_dir=tmp_path / "run")
    res = P.run_domain(dom, run_spec(), [t], lock, tmp_path / "run", provisional=True, sealer=FakeSeal)
    rec = res["records"][0]
    assert res["provisional"] is True and rec["confirm_open"] is False
    assert rec["p"]["support_confirm"] is None and rec["p"]["exclusion_full"] is None
    assert rec["effect"]["confirm"] is None
    assert rec["verdict"]["code"] == "N"
    assert rec["p"]["descriptive"]["explore"] < 0.01  # the effect shows in the explore rows
    with pytest.raises(P.PipelineError, match="provisional run never takes"):
        P.run_domain(dom, run_spec(), [t], lock, tmp_path / "r2", handle=handle_for([t], "x"),
                     provisional=True, sealer=FakeSeal)
    SB._ISSUED.pop("x", None)


def test_handle_not_issued_is_refused(tmp_path):
    t = definition()
    lock = make_lock(tmp_path, [t])
    dom = PlantedDomain(seed=1, effect=0.0, run_dir=tmp_path / "run")
    fake = SB.ConfirmHandle(domain="simulated", batch=1, bundle_sha256="ab" * 32, bundle_path="b", ots_path="o",
                            block_height=1, vintage_id="sim_v1", period=("1880-01-01", "1999-12-31"),
                            test_ids=(t.test_id,), ledger_commit="c", token="never-issued")
    with pytest.raises(P.PipelineError, match="not issued"):
        P.run_domain(dom, run_spec(), [t], lock, tmp_path / "run", handle=fake, provisional=False, sealer=FakeSeal)
    assert dom.outcome_reads == 0


def test_default_sealer_is_sealedrun_and_stamps(tmp_path, monkeypatch):
    t = definition()
    lock = make_lock(tmp_path, [t])
    made = []

    class Spy(FakeSeal):
        def __init__(self, repo_root=None, *, provisional=False):
            made.append((repo_root, provisional))
            super().__init__(provisional)

    monkeypatch.setattr(P, "SealedRun", Spy)
    dom = PlantedDomain(seed=1, effect=0.0, run_dir=tmp_path / "run")
    res = P.run_domain(dom, run_spec(), [t], lock, tmp_path / "run", repo_root=tmp_path)
    assert made == [(tmp_path, True)]
    assert res["git"] == {"commit": "c0ffee", "dirty": False}
    assert res["seal"]["threads_started"] == 0


# ------------------------------------------------------------- numbers
def test_planted_effect_is_found(tmp_path):
    """Found (p), but not Supported: a year-keyed toy calendar has too few distinct placebo skies.

    Day offsets of 400 to 3650 days move a calendar keyed by the year by 1 to
    10 years, and a 2-in-6 calendar repeats every 6 years: after the overlap
    rule only a handful of distinct placebo calendars remain, fewer than
    MIN_DISTINCT_PLACEBOS, so R2 is "insufficient_placebos" and cannot clear
    an S (CALIBRATION-FIX, conservative). test_scattered_daily_calendar_reaches_s
    shows S end to end on a calendar with enough distinct skies.
    """
    res, _, _ = confirm_run(tmp_path, effect=1.5, seed=11)
    rec = res["records"][0]
    assert rec["verdict"]["code"] == "N", rec["verdict"]
    assert "signal_not_robust" in rec["verdict"]["flags"]
    assert rec["p"]["support_confirm"] <= rec["threshold"]["a_test"] == 0.04
    assert rec["robustness"]["passed"] == {"R1": True, "R2": False, "R3": True, "R4": True}
    r2 = rec["robustness"]["R2"]
    assert r2["status"] == "insufficient_placebos" and r2["n_distinct"] < r2["min_distinct"] == 19
    assert "distinct placebo calendars" in r2["reason"]
    assert r2["n_placebo"] + r2["n_rejected_overlap"] + rec["robustness"]["placebo_skipped_no_blocks"] \
        == r2["n_candidates"]
    assert 1.0 < rec["effect"]["confirm"]["estimate"] < 2.0
    assert res["provisional"] is False and res["confirm"]["seal_bundle_sha256"] == "ab" * 32
    assert [r["kind"] for r in rec["limitations"]][:2] == ["citation_level", "tradition"]


def test_null_data_gives_no_s_beyond_the_bound(tmp_path):
    n = 24
    codes = []
    for seed in range(100, 100 + n):
        res, _, _ = confirm_run(tmp_path / str(seed), effect=0.0, seed=seed)
        rec = res["records"][0]
        codes.append(rec["verdict"]["code"])
        x95 = rec["bound"]["x95"]
        assert x95["unbounded"] or x95["value"] >= 0.05  # the plan's grid floor
    # One test per batch: a false S (or C) has chance at most a_test = 0.04 per run.
    bound = _st.binom.ppf(0.999, n, 0.04)
    assert codes.count("S") <= bound and codes.count("C") <= bound, codes
    assert codes.count("E") >= 1  # the bound is informative: steady effects at the SESOI are ruled out


def test_reproduction_of_unchanged_inputs(tmp_path):
    res, _, lock = confirm_run(tmp_path / "a", effect=1.0, seed=5)
    prev = tmp_path / "a" / "run" / "results.json"
    again, _, _ = confirm_run(tmp_path / "b", effect=1.0, seed=5, previous=prev)
    assert json.dumps(again["records"], sort_keys=True) == json.dumps(res["records"], sort_keys=True)
    tampered = json.loads(prev.read_text())
    tampered["records"][0]["effect"]["confirm"]["estimate"] += 1e-9
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps(tampered))
    with pytest.raises(P.ReproductionError):
        confirm_run(tmp_path / "c", effect=1.0, seed=5, previous=bad)


def test_closed_batch_with_recorded_results_is_not_recomputed(tmp_path):
    t = definition()
    lock = make_lock(tmp_path, [t])
    dom = PlantedDomain(seed=5, effect=1.0, run_dir=tmp_path / "run")
    h = handle_for([t], "rec")
    res = P.run_domain(dom, run_spec(), [t], lock, tmp_path / "run", handle=h, provisional=False, sealer=FakeSeal)
    P.record_batch_results(lock, res)
    prev = tmp_path / "run" / "results.json"
    dom2 = PlantedDomain(seed=5, effect=1.0, run_dir=tmp_path / "run2")
    again = P.run_domain(dom2, run_spec(), [t], lock, tmp_path / "run2", handle=h, provisional=False,
                         sealer=FakeSeal, previous=prev)
    SB._ISSUED.pop("rec", None)
    assert dom2.outcome_reads == 0
    assert again["records"] == res["records"]
    tampered = json.loads(prev.read_text())
    tampered["records"][0]["name"] = "Simulated principle edited"
    prev.write_text(json.dumps(tampered))
    with pytest.raises(P.ReproductionError):
        P.run_domain(dom2, run_spec(), [t], lock, tmp_path / "run3", sealer=FakeSeal, previous=prev)


def test_adding_a_test_changes_no_number_of_another(tmp_path):
    a = definition()
    b = definition(rule_id="sim.other", calendar=lambda d: np.asarray([x.year % 6 in (3, 4) for x in d]))
    one, _, _ = confirm_run(tmp_path / "one", effect=1.0, seed=9, tests=[a])
    two, _, _ = confirm_run(tmp_path / "two", effect=1.0, seed=9, tests=[a, b])
    ra = one["records"][0]
    rb = next(r for r in two["records"] if r["test_id"] == a.test_id)
    # a_test differs (n_b = 1 against 2); the statistics and placebo ranks do not.
    for key in ("effect", "robustness"):
        assert ra[key] == rb[key]


def test_robustness_cells_come_only_from_the_definition(tmp_path):
    res, _, _ = confirm_run(tmp_path, effect=1.5, seed=11)
    r3 = res["records"][0]["robustness"]["R3"]
    assert r3["n_cells"] == 1 and set(r3["distinct"]) | set(r3["near_copies"]) == {"two_in_twelve"}


def test_undeclared_placebo_kind_stops_the_run(tmp_path):
    t = definition(placebo_kinds=("time_shift", "scramble"))
    with pytest.raises(P.PipelineError, match="scramble"):
        confirm_run(tmp_path, effect=0.0, tests=[t])


# ------------------------------------------------------------- report
def test_report_gate_passes_on_the_output(tmp_path):
    a = definition()
    u = definition(rule_id="sim.sparse", calendar=lambda d: np.asarray([x.year % 60 < 2 for x in d]))
    res, _, _ = confirm_run(tmp_path, effect=1.5, seed=11, tests=[a, u])
    assert res["schema"] == RP.REPORT_SCHEMA
    rp = tmp_path / "run" / "results.json"
    out = tmp_path / "pages"
    manifest = RP.write_report(rp, out)
    assert RP.check_report(rp, out) == []
    assert len([k for k in manifest["pages"] if k.startswith("card/")]) == 2
    codes = sorted(r["verdict"]["code"] for r in res["records"])
    assert codes == ["N", "U"]  # N: too few distinct placebo skies on the toy yearly grid (R2)

# ------------------------------------------- outcome gaps (WP-69 open issue)
GAP_YEARS = (1903, 1904, 1951, 1952, 1953, 1990)


class GappyDomain(PlantedDomain):
    """PlantedDomain whose source has no value in GAP_YEARS (known from its inventory)."""

    def __init__(self, **kw):
        super().__init__(**kw)
        years = np.arange(START, START + YEARS)
        self._values[np.isin(years, GAP_YEARS)] = np.nan


def gap_years(dates) -> np.ndarray:
    return np.isin(np.asarray([d.year for d in dates]), GAP_YEARS)


def test_outcome_gaps_go_to_the_gate_as_the_missing_bar_mask(tmp_path):
    t = definition()
    lock = make_lock(tmp_path, [t])
    dom = GappyDomain(seed=11, effect=1.5, run_dir=tmp_path / "run")
    h = handle_for([t], "gaps")
    try:
        res = P.run_domain(dom, run_spec(missing_bars={"value": gap_years}), [t], lock, tmp_path / "run",
                           handle=h, provisional=False, sealer=FakeSeal)
    finally:
        SB._ISSUED.pop("gaps", None)
    rec = res["records"][0]
    assert dom.outcome_reads == 1 and rec["p"]["support_confirm"] <= rec["threshold"]["a_test"]
    assert rec["verdict"]["code"] == "N"  # R2: too few distinct placebo skies on the toy yearly grid
    # The gate saw the mask: its whole-period design is the one the test used (S-15).
    assert rec["gate"]["full"]["design_id"] == rec["effect"]["full"]["design_id"]
    assert rec["gate"]["confirm"]["design_id"] == rec["effect"]["confirm"]["design_id"]
    plain, _, _ = confirm_run(tmp_path / "plain", effect=1.5, seed=11)
    assert plain["records"][0]["gate"]["full"]["design_id"] != rec["gate"]["full"]["design_id"]
    assert plain["records"][0]["input_sha256"] != rec["input_sha256"]


def test_undeclared_outcome_gap_stops_the_run(tmp_path):
    t = definition()
    lock = make_lock(tmp_path, [t])
    dom = GappyDomain(seed=11, effect=0.0, run_dir=tmp_path / "run")
    h = handle_for([t], "undeclared")
    try:
        with pytest.raises(P.PipelineError, match="missing_bars does not declare"):
            P.run_domain(dom, run_spec(), [t], lock, tmp_path / "run", handle=h, provisional=False,
                         sealer=FakeSeal)
        # A declared gap that carries values is refused too.
        dom2 = PlantedDomain(seed=11, effect=0.0, run_dir=tmp_path / "run2")
        with pytest.raises(P.PipelineError, match="declared-missing"):
            P.run_domain(dom2, run_spec(missing_bars={"value": gap_years}), [t], lock, tmp_path / "run2",
                         handle=h, provisional=False, sealer=FakeSeal)
    finally:
        SB._ISSUED.pop("undeclared", None)


def test_provisional_run_with_gaps(tmp_path):
    t = definition()
    lock = make_lock(tmp_path, [t])
    dom = GappyDomain(seed=11, effect=1.5, run_dir=tmp_path / "run")
    res = P.run_domain(dom, run_spec(missing_bars={"value": gap_years}), [t], lock, tmp_path / "run",
                       provisional=True, sealer=FakeSeal)
    rec = res["records"][0]
    assert rec["p"]["descriptive"]["explore"] < 0.01 and rec["p"]["support_confirm"] is None


# ------------------------------------- daily grid: A2 blocks and detrending
DAILY_START, DAILY_DAYS = "1990-01-01", 3000
VINTAGE_D = {"id": "sim_d1", "confirm_period": {"start": "1995-01-01", "end": "1998-12-31"}, "seen": False}


def every_tenth_day(d) -> np.ndarray:
    """Single-day episodes, one in ten days (new-moon-like; A1 drops them all)."""
    days = (pd.DatetimeIndex(d) - pd.Timestamp(DAILY_START)).days
    return np.asarray(days % 10 == 3)


def scattered_days(d) -> np.ndarray:
    """Single days where frac(day * golden ratio) < 0.1: aperiodic, so day shifts give distinct skies."""
    days = (pd.DatetimeIndex(d) - pd.Timestamp(DAILY_START)).days.to_numpy(dtype=float)
    return np.asarray(np.mod(days * 0.6180339887498949, 1.0) < 0.1)


class DailyDomain(SimulatedDomain):
    """Daily toy series with a strong drift (slope and random walk), effect on every_tenth_day()."""

    def __init__(self, *, seed: int, effect: float, slope: float = 0.02, step: float = 0.05,
                 calendar=None):
        super().__init__(seed=seed, n_years=10, start_year=1990, effect=0.0)
        rng = np.random.default_rng(seed + 104729)
        self._dates = pd.date_range(DAILY_START, periods=DAILY_DAYS, freq="D")
        t = np.arange(DAILY_DAYS, dtype=float)
        act = (calendar or every_tenth_day)(self._dates).astype(float)
        self._values = (rng.normal(size=DAILY_DAYS) + slope * t + np.cumsum(rng.normal(0, step, DAILY_DAYS))
                        + effect * act)
        self.sha256 = hashlib.sha256(self._values.tobytes()).hexdigest()
        index, licences = simulated_registers(self.sha256)
        DomainAdapter.__init__(self, index, licences, simulated_grades(self.sha256))

    def grid(self):
        return [x.date() for x in self._dates]

    def periods(self):
        return Periods(explore=(date(1990, 1, 1), date(1994, 12, 31)),
                       confirm=(date(1995, 1, 1), self._dates[-1].date()))


def daily_definition(**over) -> P.TestDefinition:
    kw = dict(calendar=every_tenth_day, merge_gap=0, sensitivity={
        "days_3_4": lambda d: np.asarray((pd.DatetimeIndex(d) - pd.Timestamp(DAILY_START)).days % 10 < 5)
        & np.asarray((pd.DatetimeIndex(d) - pd.Timestamp(DAILY_START)).days % 10 > 2)},
        rule_id="sim.tenth_day")
    kw.update(over)
    return definition(**kw)


def daily_run(tmp_path: Path, effect: float, seed: int = 1, calendar=None, **spec):
    t = daily_definition() if calendar is None else daily_definition(calendar=calendar, sensitivity={})
    lock = FamilyLock(tmp_path / "lock.jsonl", "simulated")
    dom = DailyDomain(seed=seed, effect=effect, calendar=calendar)
    dates = pd.DatetimeIndex(pd.to_datetime(list(dom.grid())))
    lock.register(rule_id=t.rule_id, version=t.version, outcome=t.outcome,
                  calendar_hash=calendar_hash(t.calendar(dates)))
    lock.close_batch(vintage=VINTAGE_D, seal_bundle_sha256="ab" * 32)
    h = SB.ConfirmHandle(domain="simulated", batch=1, bundle_sha256="ab" * 32, bundle_path="seals/sim.json",
                         ots_path="seals/sim.json.ots", block_height=1, vintage_id="sim_d1",
                         period=("1995-01-01", "1998-12-31"), test_ids=(t.test_id,),
                         ledger_commit="c0ffee", token=f"daily-{tmp_path.name}-{seed}")
    SB._ISSUED[h.token] = h
    kw = dict(vintage=VINTAGE_D, plan={"domain": "simulated", "outcomes": [{"id": "value"}],
                                       "vintages": [VINTAGE_D]})
    kw.update(spec)
    try:
        res = P.run_domain(dom, run_spec(**kw), [t], lock, tmp_path / "run", handle=h, provisional=False,
                           sealer=FakeSeal)
    finally:
        SB._ISSUED.pop(h.token, None)
    return res, dom


def test_daily_outcome_without_a_detrend_window_stops_before_any_read(tmp_path, monkeypatch):
    def no_read(self):
        raise AssertionError("an outcome was read")

    monkeypatch.setattr(DailyDomain, "_outcomes", no_read)
    with pytest.raises(P.PipelineError, match="detrend_window"):
        daily_run(tmp_path, effect=0.0)
    # The gate is written (calendar only), but no outcome was read.
    assert (tmp_path / "run" / "gates").is_dir()


def test_daily_drift_is_detrended_and_single_day_blocks_are_used(tmp_path):
    res, dom = daily_run(tmp_path / "null", effect=0.0, seed=3, detrend_window=31)
    rec = res["records"][0]
    assert dom.outcome_reads == 1
    g = rec["gate"]["full"]
    assert g["n_used"] == g["n_episodes"] == 300  # A2: every single-day episode keeps a block
    assert rec["gate"]["full"]["design_id"] == rec["effect"]["full"]["design_id"]
    assert rec["verdict"]["code"] != "S"
    # Raw drift is 60 noise SD over the record; detrended, the estimate is noise-sized.
    assert abs(rec["effect"]["full"]["statistic"]) < 0.25
    assert abs(rec["estimate"]["without_baselines"]) < 0.25
    found, _ = daily_run(tmp_path / "planted", effect=1.0, seed=3, detrend_window=31)
    frec = found["records"][0]
    # Every tenth day repeats every 10 days: about 10 distinct placebo skies, R2 insufficient.
    assert frec["verdict"]["code"] == "N", frec["verdict"]
    assert frec["robustness"]["R2"]["status"] == "insufficient_placebos"
    assert frec["p"]["support_confirm"] <= frec["threshold"]["a_test"]
    assert 0.7 < frec["effect"]["confirm"]["estimate"] < 1.3
    assert frec["input_sha256"] != rec["input_sha256"]


def test_scattered_daily_calendar_reaches_s(tmp_path):
    """End to end S: an aperiodic single-day calendar has enough distinct placebo skies (R2)."""
    res, _ = daily_run(tmp_path, effect=1.0, seed=3, calendar=scattered_days, detrend_window=31)
    rec = res["records"][0]
    r2 = rec["robustness"]["R2"]
    assert r2["status"] == "pass" and r2["n_distinct"] >= r2["min_distinct"], r2
    assert r2["n_placebo"] == 200  # rejected skies were replaced from the placebo stream
    assert rec["verdict"]["code"] == "S", rec["verdict"]
    assert 0.7 < rec["effect"]["confirm"]["estimate"] < 1.3
