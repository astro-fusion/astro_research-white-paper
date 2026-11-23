"""astro-validity cli (ADR-007 section 8, WP-74). SimulatedDomain only; no real outcome is read."""

from __future__ import annotations

import dataclasses
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
import yaml

from vedic_astrology_core.domains.base import DomainAdapter
from vedic_astrology_core.domains.simulated import SimulatedDomain, simulated_grades, simulated_registers
from vedic_astrology_core.rules.schema import Rule
from vedic_astrology_core.validity import changelog as CL
from vedic_astrology_core.validity import cli
from vedic_astrology_core.validity import pipeline as P
from vedic_astrology_core.validity import sealbundle as SB
from vedic_astrology_core.validity.family import FamilyLock

ROOT = Path(__file__).resolve().parents[1]
MANDALA = ROOT / "rules/mundane/practitioner/bs32_agni_mandala_earthquake.yaml"
START, YEARS = 1700, 300
VINTAGE = {"id": "sim_v1", "confirm_period": {"start": "1880-01-01", "end": "1999-12-31"}, "seen": False}
SEAL_SHA = "ab" * 32


def active(dates):
    return np.asarray([(d.year % 6) < 2 for d in dates])


def planted(seed: int) -> SimulatedDomain:
    """SimulatedDomain with a planted effect on the years the calendar is active."""
    dom = SimulatedDomain(seed=seed, n_years=YEARS, start_year=START)
    act = active(dom.grid()).astype(float)
    dom._values = np.random.default_rng(seed + 7919).normal(size=YEARS) + 1.5 * act
    dom.sha256 = hashlib.sha256(dom._values.tobytes()).hexdigest()
    index, licences = simulated_registers(dom.sha256)
    DomainAdapter.__init__(dom, index, licences, simulated_grades(dom.sha256))
    return dom


def _rule() -> Rule:
    doc = yaml.safe_load(MANDALA.read_text())
    doc["source"]["published"] = "1600"
    doc["expected_effect"]["fixed_by"] = "project"
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


RULE = _rule()


class FakeSeal:
    def __init__(self, provisional):
        self.provisional = provisional

    def __enter__(self):
        return self

    def finish(self, engine=None):
        return {"provisional": self.provisional, "commit": "c0ffee", "dirty": False,
                "problems": [], "files_read": [], "threads_started": 0}

    def __exit__(self, *exc):
        return False


class FakeSealedRun(FakeSeal):
    """Stands in for stats/seal.py SealedRun (the tmp tree is no git checkout)."""

    calls = []

    def __init__(self, repo_root=None, *, provisional=False, **kw):
        super().__init__(provisional)
        FakeSealedRun.calls.append(provisional)


def registered_plan(domain="simulated"):
    """A plan that passes validity/plan.py with status registered (the seal gate, N-05)."""
    return {
        "domain": domain, "status": "registered", "seed": 20261122,
        "split": {"explore": {"start": "1700-01-01", "end": "1879-12-31"},
                  "confirm": {"start": "1880-01-01", "end": "1999-12-31"}},
        "vintages": [{"id": "sim_v1", "snapshot": "sim", "grain": "yearly", "seen": False,
                      "confirm_period": {"start": "1880-01-01", "end": "1999-12-31"}}],
        "snapshots": [{"id": "sim", "file": "data/sim.csv", "sha256": "ab" * 32}],
        "outcomes": [{"id": "value", "type": "continuous", "estimand": "pooled_difference",
                      "effect_model": "additive", "side": "two_sided", "sesoi": None, "guard_bars": 0,
                      "grid_x": [0.1, 0.5, 1.0]}],
        "windows": {"year": "the year"}, "merge_gap": 0, "guard_bars": 0, "day_convention": "year",
        "r_measures": {r: {"measure": "m", "threshold": 0.05} for r in ("R1", "R2", "R3", "R4")},
        "placebo_sets": ["time_shift"], "baselines": [{"id": "trend"}],
        "alpha_spending": {"first": 0.04, "ratio": 0.2, "max_variants": 3},
        "owner_signoffs": {k: "2026-11-23" for k in ("H16", "H19", "H20", "L2", "Support")},
    }


def write_plan(layout, plan):
    layout.domains_dir.mkdir(parents=True, exist_ok=True)
    (layout.domains_dir / f"{plan['domain']}.yaml").write_text(yaml.safe_dump(plan))


class SimBindings(cli.Bindings):
    def __init__(self, layout, *, seed=11, confirm=True, orb=15):
        super().__init__(layout)
        self.dom = planted(seed)
        self.confirm, self.orb, self.version = confirm, orb, 1
        self.tokens = []

    def domains(self):
        return ["simulated"]

    def adapter(self, domain):
        return self.dom

    def run_spec(self, domain):
        return P.DomainRun(
            domain="simulated", plan_seed=20261122, plan_sha256="cd" * 32, vintage=VINTAGE,
            baselines=lambda d: np.asarray([(x.year - 1850) / 100.0 for x in d]),
            plan={"domain": "simulated", "outcomes": [{"id": "value"}], "vintages": [VINTAGE]})

    def tests(self, domain):
        return [P.TestDefinition(
            rule_id="sim.four", version=self.version, outcome="value", calendar=active, side="greater",
            outcome_type="continuous", x_grid=np.round(np.linspace(0.05, 4.0, 40), 4).tolist(),
            name="Simulated principle", level=2, rule=RULE, sesoi=0.8, noise_sd=1.0, source_published="1600",
            n_draws=499, power_reps=20)]

    def rule_states(self, domain):
        return {"sim.four": CL.rule_state(self.version, {"id": "sim.four", "params": {"orb": {"value": self.orb}}})}

    def engine_id(self):
        return "test-engine"

    def sealer(self):
        return FakeSeal

    def today(self):
        return "2026-12-03"

    def handle(self, domain):
        if not self.confirm:
            return None
        token = f"cli-{id(self)}"
        h = SB.ConfirmHandle(
            domain="simulated", batch=1, bundle_sha256=SEAL_SHA, bundle_path="seals/sim.json",
            ots_path="seals/sim.json.ots", block_height=1, vintage_id="sim_v1",
            period=("1880-01-01", "1999-12-31"), test_ids=tuple(t.test_id for t in self.tests(domain)),
            ledger_commit="c0ffee", token=token)
        SB._ISSUED[token] = h
        self.tokens.append(token)
        return h

    def seal_sources(self, domain):
        return object()  # the fake seal_domain ignores it

    def catalogue_rows(self):
        return [{"id": "sim.four", "status": "active"}]


@pytest.fixture
def env(tmp_path, monkeypatch):
    b = SimBindings(cli.Layout(tmp_path))
    write_plan(b.layout, registered_plan())
    FakeSealedRun.calls = []
    monkeypatch.setattr(P, "SealedRun", FakeSealedRun)  # the confirm path always uses it (N-11)

    def fake_seal(repo_root, src, **kw):
        lock = FamilyLock(b.layout.lock("simulated"), "simulated")
        lock.close_batch(vintage=VINTAGE, seal_bundle_sha256=SEAL_SHA)
        return {"bundle": "x", "bundle_sha256": SEAL_SHA, "commit": "c0ffee" * 6, "ots": "x", "batch": 1}

    monkeypatch.setattr(cli, "seal_domain", fake_seal)
    yield b
    for t in b.tokens:
        SB._ISSUED.pop(t, None)


def run(b, *argv):
    return cli.main(list(argv), bindings=b)


def sealed(b):
    assert run(b, "register") == 0
    assert run(b, "seal") == 0


def test_register_reads_no_outcome_and_is_idempotent(env, capsys):
    assert run(env, "register") == 0
    assert "registered sim.four@1/primary/value" in capsys.readouterr().out
    assert env.dom.outcome_reads == 0
    assert run(env, "register") == 0
    assert "already registered" in capsys.readouterr().out
    assert len(FamilyLock(env.layout.lock("simulated"), "simulated").test_ids()) == 1


def test_register_refuses_an_unregistrable_rule(env, monkeypatch, capsys):
    monkeypatch.setattr(cli, "registration_problems", lambda r, d=(): ["reading: not stated"])
    assert run(env, "register") == 1
    assert "refused" in capsys.readouterr().out
    assert not env.layout.lock("simulated").exists()


def test_gate_reads_no_outcome(env, capsys):
    run(env, "register")
    assert run(env, "gate") == 0
    out = capsys.readouterr().out
    assert "simulated sim.four@1/primary/value:" in out
    assert env.dom.outcome_reads == 0


def test_run_is_provisional_and_does_not_take_a_published_directory(env):
    run(env, "register")
    assert run(env, "run") == 0
    prov = [p for p in env.layout.runs.iterdir()]
    assert len(prov) == 1 and prov[0].name.endswith(".provisional")
    res = json.loads((prov[0] / "simulated" / "results.json").read_text())
    assert res["provisional"] is True and (prov[0] / "state.json").is_file()


def test_all_refuses_provisional_results_and_records_nothing(env, capsys):
    sealed(env)
    env.confirm = False
    assert run(env, "all") == 1
    assert "provisional" in capsys.readouterr().out
    assert not env.layout.changelog.exists()


def test_all_records_reports_and_is_idempotent(env, capsys):
    sealed(env)
    assert run(env, "all") == 0
    out = capsys.readouterr().out
    assert "changelog entry 1" in out
    entries = CL.read_entries(env.layout.changelog)
    assert len(entries) == 1
    e = entries[0]
    assert e["previous_run_id"] is None and [t["cause"] for t in e["tests"]] == ["new_principle"]
    pages = env.layout.reports / e["run_id"] / "simulated"
    assert (pages / "summary.md").is_file() and (pages / "report_manifest.json").is_file()
    assert "sim.four" in (env.layout.site / "changelog.qmd").read_text()
    # unchanged inputs: nothing runs, nothing is appended
    before = env.layout.changelog.read_bytes()
    assert run(env, "all") == 0
    assert "unchanged" in capsys.readouterr().out
    assert env.layout.changelog.read_bytes() == before
    # the lock now holds the batch results
    lock = FamilyLock(env.layout.lock("simulated"), "simulated")
    assert lock.entries[-1]["kind"] == "batch_results"


def test_changed_data_after_confirm_stops_the_run(env, capsys):
    sealed(env)
    assert run(env, "all") == 0
    before = env.layout.changelog.read_bytes()
    other = SimBindings(env.layout, seed=12)
    other.today = lambda: "2026-12-04"
    assert run(other, "all") == 1
    assert "closed batch" in capsys.readouterr().err
    assert env.layout.changelog.read_bytes() == before


def test_diff_of_two_runs(env, capsys):
    sealed(env)
    assert run(env, "all") == 0
    rid = CL.read_entries(env.layout.changelog)[0]["run_id"]
    capsys.readouterr()
    assert run(env, "run") == 0  # closed batch: the stored records are reused
    prov = next(p.name for p in env.layout.runs.iterdir() if p.name.endswith(".provisional"))
    capsys.readouterr()
    assert run(env, "diff", rid, prov) == 0
    assert json.loads(capsys.readouterr().out)["summary"]["unchanged"] == 1
    rp = env.layout.runs / prov / "simulated" / "results.json"
    doc = json.loads(rp.read_text())
    doc["records"][0]["verdict"]["code"] = "Z"  # a verdict change with no input change
    rp.write_text(json.dumps(doc))
    assert run(env, "diff", rid, prov) == 1
    assert json.loads(capsys.readouterr().out)["unexplained"]
    env.orb = 8  # an edited parameter shows in inputs_changed
    assert run(env, "run") == 0
    prov2 = sorted(p.name for p in env.layout.runs.iterdir() if p.name.endswith(".provisional"))
    new = [p for p in prov2 if p != prov][0]
    capsys.readouterr()
    assert run(env, "diff", rid, new) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["inputs_changed"]["rules"][0]["fields"] == [{"path": "params.orb.value", "from": 15, "to": 8}]


def test_report_command_rebuilds_pages(env, capsys):
    sealed(env)
    run(env, "all")
    rid = CL.read_entries(env.layout.changelog)[0]["run_id"]
    summary = env.layout.reports / rid / "simulated" / "summary.md"
    summary.unlink()
    assert run(env, "report", "--run", rid) == 0
    assert summary.is_file()


def test_catalogue_writes_the_rows(env):
    assert run(env, "catalogue") == 0
    data = json.loads((env.layout.site / "catalogue.json").read_text())
    assert data["principles"] == [{"id": "sim.four", "status": "active"}]


def test_confirm_and_seal_go_through_sealbundle(env, monkeypatch):
    run(env, "register")
    seen = {}

    def fake_issue(root, bundle, **kw):
        seen["bundle"] = str(bundle)
        return env.handle("simulated")

    monkeypatch.setattr(cli, "issue_confirm_handle", fake_issue)
    assert run(env, "seal") == 0
    assert run(env, "confirm", "--bundle", "seals/sim.json") == 0
    assert seen["bundle"] == "seals/sim.json"
    rid_dir = next(p for p in env.layout.runs.iterdir() if not p.name.endswith(".provisional"))
    assert json.loads((rid_dir / "simulated" / "results.json").read_text())["provisional"] is False


def test_default_bindings_exit_2_with_a_message(tmp_path, capsys):
    assert cli.main(["--root", str(tmp_path), "register", "gold"]) == 2
    assert "no bindings" in capsys.readouterr().err


def test_module_is_runnable():
    out = subprocess.run([sys.executable, "-m", "vedic_astrology_core.validity.cli", "--help"],
                         capture_output=True, text=True)
    assert out.returncode == 0 and "register" in out.stdout and "confirm" in out.stdout


# ------------------------------------------------ strategy audit 2 (N-05, N-11, N-13, A-08)
def test_register_checks_the_rule_with_the_disputes_lists(env, monkeypatch, tmp_path, capsys):
    d = tmp_path / "rules" / "financial" / "practitioner"
    d.mkdir(parents=True)
    (d / "DISPUTES.md").write_text(f"- `{RULE.id}` is read both ways\n")
    seen = {}

    def spy(rule, disputes=()):
        seen["disputes"] = list(disputes)
        return []

    monkeypatch.setattr(cli, "registration_problems", spy)
    assert run(env, "register") == 0
    assert RULE.id in seen["disputes"]


def test_register_refuses_a_test_without_its_rule_file(env, capsys):
    orig = env.tests

    def no_rule(domain):
        return [dataclasses.replace(t, rule=None) for t in orig(domain)]

    env.tests = no_rule
    assert run(env, "register") == 1
    assert "no rule file" in capsys.readouterr().out
    assert not env.layout.lock("simulated").exists()


def test_confirm_runs_in_sealedrun_whatever_the_bindings_say(env):
    used = []

    class Lenient(FakeSeal):
        def __init__(self, provisional):
            used.append(provisional)
            super().__init__(provisional)

    env.sealer = lambda: Lenient
    sealed(env)
    assert run(env, "all") == 0
    assert False not in used  # the bindings' sealer never ran a confirm
    assert False in FakeSealedRun.calls  # stats/seal.py SealedRun did


@pytest.mark.parametrize("change", ["draft", "invalid", "missing"])
def test_seal_refuses_a_plan_that_is_not_valid_and_registered(env, capsys, change):
    plan = registered_plan()
    path = env.layout.domains_dir / "simulated.yaml"
    if change == "draft":
        plan["status"] = "draft"
        write_plan(env.layout, plan)
    elif change == "invalid":
        plan["outcomes"][0]["sesoi"] = {"kind": "project", "value": 0.8}
        write_plan(env.layout, plan)
    else:
        path.unlink()
    assert run(env, "register") == 0
    assert run(env, "seal") == 1
    assert "refused to seal simulated" in capsys.readouterr().out
    assert not FamilyLock(env.layout.lock("simulated"), "simulated").closed_batches()


def test_report_refuses_results_that_differ_from_the_lock(env, capsys):
    sealed(env)
    assert run(env, "all") == 0
    rid = CL.read_entries(env.layout.changelog)[0]["run_id"]
    rp = env.layout.runs / rid / "simulated" / "results.json"
    doc = json.loads(rp.read_text())
    doc["records"][0]["level"] = 4  # an edited record (N-13 probe)
    rp.write_text(json.dumps(doc))
    capsys.readouterr()
    assert run(env, "report", "--run", rid) == 1
    out = capsys.readouterr().out
    assert "changed after it was recorded" in out and "failed" in out


def test_report_refuses_provisional_results(env, capsys):
    run(env, "register")
    assert run(env, "run") == 0
    prov = next(p.name for p in env.layout.runs.iterdir() if p.name.endswith(".provisional"))
    assert run(env, "report", "--run", prov) == 1
    assert "provisional results are never published" in capsys.readouterr().out


def _preview(env):
    assert run(env, "preview") == 0
    return json.loads((env.layout.preview / "simulated" / "results.json").read_text())


def test_preview_is_explore_only_with_no_verdict_and_no_lock(env):
    doc = _preview(env)
    assert doc["schema"] == cli.PREVIEW_SCHEMA and doc["provisional"] is True and doc["verdicts"] is None
    assert doc["period"] == {"explore": ["1700-01-01", "1879-12-31"], "confirm_rows_read": False}
    rec = doc["records"][0]
    assert "verdict" not in rec and rec["explore"]["blocks_used"] > 0
    assert rec["explore"]["p_descriptive_uncorrected"] is not None
    assert doc["headline"]["tests"] == 1 and doc["headline"]["with_explore_numbers"] == 1
    assert not env.layout.lock("simulated").exists()  # a throwaway lock only
    assert not env.layout.runs.exists()


def test_preview_does_not_depend_on_confirm_rows(env):
    first = _preview(env)
    dom = env.dom
    years = np.asarray([d.year for d in dom.grid()])
    dom._values = np.where(years >= 1880, dom._values + 100.0, dom._values)  # confirm rows only
    second = _preview(env)
    assert first["records"] == second["records"]


def test_preview_keeps_the_gate_when_outcomes_are_refused(env):
    class FirewallError(RuntimeError):
        pass

    class Walled:
        def __init__(self, inner):
            self.inner, self.domain = inner, inner.domain

        def __getattr__(self, name):
            return getattr(self.inner, name)

        def outcomes(self, gate=None, *, gate_path=None):
            raise FirewallError("plan is a draft")

    inner = env.dom
    env.adapter = lambda d: Walled(inner)
    doc = _preview(env)
    assert doc["outcomes_refused"].startswith("FirewallError")
    rec = doc["records"][0]
    assert rec["explore"] is None and "can_support" in rec["gate"]


def test_preview_can_leave_rules_out_and_says_so(env):
    assert run(env, "preview", "--skip-rule", "^sim\\.") == 0
    doc = json.loads((env.layout.preview / "simulated" / "results.json").read_text())
    assert doc["records"] == [] and doc["left_out"]["test_ids"] == ["sim.four@1/primary/value"]
