"""`astro-validity`: register, gate, run, preview, seal, confirm, report, diff, catalogue, all.

ADR-007 section 8 as amended by ADR-008 section 13 (WP-74). Every command goes
through the core modules; none computes a statistic of its own:

* register  validity/family.py   (slots, lock; rules/schema.py registration_problems)
* gate      validity/gate.py     (through the pipeline's own prepare and gate steps)
* run       validity/pipeline.py (explore rows only, provisional)
* preview   validity/pipeline.py on the explore period only, every test the
            plan and the rule files give (registrable or not, labelled), in a
            throwaway lock: descriptive numbers, no verdict, never a confirm
            row; writes studies/validity/preview/<plan>/results.json
* seal      validity/sealbundle.py seal_domain
* confirm   validity/sealbundle.py issue_confirm_handle, then pipeline.run_domain
* report    validity/report.py   (reads results JSON only)
* all       run every domain whose inputs changed, append the changelog, report

No command reads an outcome before the gate files are written (the pipeline
enforces it) and none registers anything except `register`.

Run it as `python -m vedic_astrology_core.validity.cli`. The console script
`astro-validity` is planned (WP-18 owns pyproject.toml).

The cli needs *bindings*: how a domain's adapter, plan and tests are built
from the plan files and the rule files. The default, PlanBindings, builds
them with core/validity/bindings.py from studies/validity/domains/*.yaml and
the rule files (strategy audit 2 N-05): no verdict input is typed. Another
factory may be passed with `--bindings package.module:factory` (tests use
SimulatedDomain this way), but it cannot change what makes a confirm
trustworthy: the confirm path always runs inside stats/seal.py SealedRun
(N-11), `register` always checks the rule with the DISPUTES.md lists (A-08),
`seal` refuses a plan that fails validity/plan.py or is not registered
(N-05), and `report` refuses results that differ from the family lock (N-13).

Past data only. No forecast, no network.
"""

from __future__ import annotations

import argparse
import dataclasses
import datetime as _dt
import importlib
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from .. import __version__ as _ENGINE_VERSION
from ..rules.schema import registration_problems
from . import bindings as _bd
from . import changelog as _cl
from . import pipeline as _pl
from . import plan as _plan
from . import report as _rp
from .family import FamilyError, FamilyLock, calendar_hash
from .sealbundle import ConfirmHandle, SealSources, issue_confirm_handle, seal_domain

__all__ = ["Layout", "Bindings", "BindingsError", "FileBindings", "PlanBindings", "PreviewError",
           "PREVIEW_SCHEMA", "main", "current_state", "plan_problems", "run_preview"]

PREVIEW_SCHEMA = "validity-preview/1"

DEFAULT_ROOT = Path(__file__).resolve().parents[3]


class BindingsError(RuntimeError):
    """The cli has no way to build this from the committed files (exit code 2)."""


@dataclass(frozen=True)
class Layout:
    """Where everything lives, under one repository root."""

    root: Path = DEFAULT_ROOT

    @property
    def validity(self) -> Path:
        return self.root / "studies" / "validity"

    @property
    def domains_dir(self) -> Path:
        return self.validity / "domains"

    @property
    def runs(self) -> Path:
        return self.validity / "runs"

    @property
    def changelog(self) -> Path:
        return self.validity / "changelog.jsonl"

    @property
    def reports(self) -> Path:
        return self.root / "reports" / "validity"

    @property
    def site(self) -> Path:
        return self.root / "site" / "validity"

    def lock(self, domain: str) -> Path:
        return self.validity / "locks" / f"{domain}.lock.jsonl"

    @property
    def preview(self) -> Path:
        return self.validity / "preview"


class Bindings:
    """What the cli needs from the project. Override what a project has; the rest raises."""

    def __init__(self, layout: Layout):
        self.layout = layout

    @staticmethod
    def _missing(what: str) -> BindingsError:
        return BindingsError(
            f"no bindings for {what}: these bindings do not build it; "
            "use the default PlanBindings or pass --bindings package.module:factory")

    def domains(self) -> List[str]:
        d = self.layout.domains_dir
        return sorted(p.stem for p in d.glob("*.yaml")) if d.is_dir() else []

    def disputes(self) -> List[str]:
        """Rule ids named in the repository's DISPUTES.md files (A-08); never typed."""
        return _bd.disputed_rule_ids(self.layout.root)

    def preview_name(self, domain: str) -> str:
        """The folder of the domain's preview (the plan file's name)."""
        return domain

    def preview_tests(self, domain: str) -> List[_pl.TestDefinition]:
        """Every test the preview shows; the default is the registered set."""
        return self.tests(domain)

    def preview_info(self, domain: str) -> Dict[str, Any]:
        """Registrability per test id and the excluded list (for the preview file)."""
        return {"tests": {}, "excluded": [], "notes": {}}

    def adapter(self, domain: str) -> Any:
        raise self._missing(f"the {domain} adapter")

    def run_spec(self, domain: str) -> _pl.DomainRun:
        raise self._missing(f"the {domain} plan")

    def tests(self, domain: str) -> List[_pl.TestDefinition]:
        raise self._missing(f"the {domain} tests")

    def rule_states(self, domain: str) -> Dict[str, Dict[str, Any]]:
        raise self._missing(f"the {domain} rule files")

    def engine_id(self) -> str:
        return f"vedic_astrology_core {_ENGINE_VERSION}"

    def handle(self, domain: str) -> Optional[ConfirmHandle]:
        """A confirm handle for `all`; None means a provisional run (which cannot be published)."""
        return None

    def sealer(self) -> Any:
        return None

    def seal_sources(self, domain: str) -> SealSources:
        raise self._missing(f"the {domain} seal sources")

    def catalogue_rows(self) -> List[Dict[str, Any]]:
        raise self._missing("the principle catalogue")

    def today(self) -> str:
        return _dt.datetime.now(_dt.timezone.utc).date().isoformat()


class PlanBindings(Bindings):
    """The default: every domain from its plan file and the rule files (core/validity/bindings.py)."""

    def __init__(self, layout: Layout):
        super().__init__(layout)
        self._plans: Optional[Dict[str, Path]] = None
        self._bound: Dict[str, _bd.DomainBinding] = {}
        self._rules: Optional[Dict[str, _bd.RuleFile]] = None

    def _plan_paths(self) -> Dict[str, Path]:
        if self._plans is None:
            import yaml

            out: Dict[str, Path] = {}
            for p in _bd.plan_files(self.layout.root):
                doc = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
                d = doc.get("domain") if isinstance(doc, Mapping) else None
                if isinstance(d, str):
                    out[d] = p
            self._plans = out
        return self._plans

    def domains(self) -> List[str]:
        return sorted(self._plan_paths())

    def binding(self, domain: str) -> _bd.DomainBinding:
        if domain not in self._bound:
            path = self._plan_paths().get(domain)
            if path is None:
                raise BindingsError(f"no bindings for {domain}: no plan in {self.layout.domains_dir} names it")
            if self._rules is None:
                self._rules = _bd.load_rule_files(self.layout.root)
            try:
                self._bound[domain] = _bd.bind(path, root=self.layout.root, rule_files=self._rules,
                                               disputes=self.disputes(), n_domains=len(self._plan_paths()))
            except _plan.PlanError as exc:
                raise BindingsError(f"no bindings for {domain}: {exc}") from exc
        return self._bound[domain]

    def adapter(self, domain: str) -> Any:
        return self.binding(domain).adapter

    def run_spec(self, domain: str) -> _pl.DomainRun:
        return self.binding(domain).run

    def tests(self, domain: str) -> List[_pl.TestDefinition]:
        return self.binding(domain).registrable_tests()

    def preview_tests(self, domain: str) -> List[_pl.TestDefinition]:
        return self.binding(domain).all_tests()

    def preview_name(self, domain: str) -> str:
        return self.binding(domain).plan_path.stem

    def preview_info(self, domain: str) -> Dict[str, Any]:
        bd = self.binding(domain)
        return {"tests": {b.test_id: b.as_dict() for b in bd.tests},
                "excluded": [e.as_dict() for e in bd.excluded], "notes": dict(bd.notes),
                "plan": {"path": str(bd.plan_path.relative_to(self.layout.root))
                         if bd.plan_path.is_relative_to(self.layout.root) else str(bd.plan_path),
                         "status": bd.plan.get("status"), "sha256": bd.plan_sha256}}

    def rule_states(self, domain: str) -> Dict[str, Dict[str, Any]]:
        bd = self.binding(domain)
        out = {}
        for rid in bd.rule_ids():
            rule = bd.rule_files[rid].rule
            doc = getattr(rule, "_template", None) or rule.model_dump(mode="json", by_alias=True, exclude_none=True)
            out[rid] = _cl.rule_state(int(rule.version), json.loads(json.dumps(doc, default=str)))
        return out

    def catalogue_rows(self) -> List[Dict[str, Any]]:
        rows = []
        for d in self.domains():
            bd = self.binding(d)
            for b in bd.tests:
                rows.append({"domain": d, **b.as_dict()})
            for e in bd.excluded:
                rows.append({"domain": d, **e.as_dict(), "registrable": False})
        return rows


#: Kept for callers of the old name.
FileBindings = PlanBindings


def plan_problems(layout: Layout, domain: str) -> List[str]:
    """Why the domain's plan cannot be sealed: validity/plan.py problems, or not registered (N-05).

    The plan is the committed file in studies/validity/domains/ whose
    ``domain`` key names the domain; bindings cannot supply another.
    """
    import yaml

    found = []
    for p in _bd.plan_files(layout.root):
        doc = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        if isinstance(doc, Mapping) and doc.get("domain") == domain:
            found.append(p)
    if len(found) != 1:
        return [f"{len(found)} plan files in {layout.domains_dir} name domain {domain!r}; exactly one is needed"]
    try:
        plan = _bd.load_domain_plan(found[0], layout.root)
    except _plan.PlanError as exc:
        return list(exc.errors)
    if plan.get("status") != "registered":
        return [f"plan {found[0].name} has status {plan.get('status')!r}; only a registered plan is sealed"]
    return []


# ------------------------------------------------------------------ helpers
def _say(*parts: Any) -> None:
    print(*parts)


def _dates(adapter: Any) -> pd.DatetimeIndex:
    return pd.DatetimeIndex([pd.Timestamp(d) for d in adapter.grid()])


def _lock(b: Bindings, domain: str) -> FamilyLock:
    return FamilyLock(b.layout.lock(domain), domain)


def _results_of(run_dir: Path) -> Dict[str, Dict[str, Any]]:
    out = {}
    for p in sorted(run_dir.glob("*/results.json")):
        out[p.parent.name] = json.loads(p.read_text(encoding="utf-8"))
    return out


def _records(results: Mapping[str, Mapping[str, Any]]) -> List[Dict[str, Any]]:
    return [r for dom in sorted(results) for r in results[dom].get("records", [])]


def current_state(b: Bindings, domains: Sequence[str]) -> Dict[str, Any]:
    """The input state of the record: rule files, datasets, plans, budget, engine."""
    rules: Dict[str, Any] = {}
    datasets: Dict[str, str] = {}
    plans: Dict[str, str] = {}
    budget: Dict[str, Any] = {}
    by_domain: Dict[str, List[str]] = {}
    for d in domains:
        rs = b.rule_states(d)
        rules.update(rs)
        by_domain[d] = sorted(rs)
        datasets[d] = b.adapter(d).dataset().sha256
        plans[d] = b.run_spec(d).plan_sha256
        lock = _lock(b, d)
        budget[d] = {str(n): {"n_b": c["n_b"], "alpha_b": c["alpha_b"]}
                     for n in lock.closed_batches() for c in [lock.batch_close_entry(n)]}
    state = _cl.input_state(rules=rules, datasets=datasets, plans=plans, engine=b.engine_id(), budget=budget)
    state["domain_rules"] = by_domain
    return state


def _slice(state: Mapping[str, Any], domain: str) -> Dict[str, Any]:
    ids = (state.get("domain_rules") or {}).get(domain, [])
    return {"rules": {i: (state.get("rules") or {}).get(i) for i in ids},
            "dataset": (state.get("datasets") or {}).get(domain),
            "plan": (state.get("plans") or {}).get(domain),
            "budget": (state.get("budget") or {}).get(domain),
            "engine": state.get("engine")}


def _write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def _domains(b: Bindings, args: argparse.Namespace) -> List[str]:
    return list(args.domains) if getattr(args, "domains", None) else b.domains()


def _run_domain(b: Bindings, domain: str, out_dir: Path, *, handle: Optional[ConfirmHandle],
                provisional: bool, previous: Optional[Path]) -> Dict[str, Any]:
    # N-11: bindings may supply a sealer for provisional runs only; a confirm
    # always runs inside stats/seal.py SealedRun (clean tree, environment, reads).
    sealer = b.sealer() if handle is None else None
    results = _pl.run_domain(
        b.adapter(domain), b.run_spec(domain), b.tests(domain), _lock(b, domain), out_dir,
        handle=handle, provisional=provisional, repo_root=b.layout.root, sealer=sealer,
        previous=previous if previous is not None and previous.is_file() else None)
    if handle is not None and results.get("provisional") is False:
        _pl.record_batch_results(_lock(b, domain), results)
    return results


def _last_run_dir(b: Bindings) -> Optional[Path]:
    entries = _cl.read_entries(b.layout.changelog)
    return b.layout.runs / entries[-1]["run_id"] if entries else None


# ------------------------------------------------------------------ preview
class PreviewError(RuntimeError):
    """The preview would have produced something it must not (a verdict, a confirm row)."""


def _gate_only(adapter: Any, run: _pl.DomainRun, tests: Sequence[_pl.TestDefinition],
               lock: FamilyLock) -> Dict[str, Dict[str, Any]]:
    """Outcome-free gate of every test (used when the outcomes are refused)."""
    dates = _dates(adapter)
    confirm = _pl._mask_between(dates, adapter.periods().confirm)
    grade = adapter.dataset().grade
    out = {}
    for p in _pl._prepare(tests, dates, lock, run):
        g = _pl._gate(p, dates, confirm, grade, run)
        out[p.test.test_id] = _pl._clean(g.to_dict())
    return out


def _gate_summary(g: Mapping[str, Any]) -> Dict[str, Any]:
    keep = ("untestable", "untestable_reason", "can_support", "can_limit", "all_blocks_dropped")
    out = {k: g.get(k) for k in keep if k in g}
    for part in ("explore", "confirm", "full"):
        sub = g.get(part)
        if isinstance(sub, Mapping):
            out[f"{part}_blocks"] = sub.get("n_used")
    return out


def _robustness_summary(rob: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(rob, Mapping):
        return None
    out = {}
    for k in ("R1", "R2", "R3", "R4"):
        v = rob.get(k)
        if isinstance(v, Mapping):
            out[k] = {"passed": v.get("passed"), "status": v.get("status")}
    return out


def _preview_record(rec: Mapping[str, Any], info: Mapping[str, Any]) -> Dict[str, Any]:
    v = rec.get("verdict") or {}
    if v.get("code") in ("S", "C", "E"):
        raise PreviewError(f"{rec.get('test_id')}: a provisional run produced verdict {v.get('code')}")
    if rec.get("confirm_open"):
        raise PreviewError(f"{rec.get('test_id')}: the confirm period was open in a preview")
    eff = rec.get("effect") or {}
    exp = eff.get("explore") or {}
    p = (rec.get("p") or {}).get("descriptive") or {}
    bound = rec.get("bound") or {}
    return {
        "test_id": rec["test_id"],
        "rule_id": (rec.get("principle") or {}).get("id"),
        "variant": (rec.get("variant") or {}).get("id"),
        "name": rec.get("name"),
        "level": rec.get("level"),
        "registrable": info.get("registrable"),
        "registration_problems": info.get("registration_problems", []),
        "outcome": info.get("outcome"),
        "outcome_type": info.get("outcome_type"),
        "side": info.get("side"),
        "gate": _gate_summary(rec.get("gate") or {}),
        "explore": {
            "scale": exp.get("scale"),
            "statistic": exp.get("statistic"),
            "estimate": exp.get("estimate"),
            "blocks_used": exp.get("n_used"),
            "p_descriptive_uncorrected": p.get("explore"),
        },
        "x95_explore_per_test": bound.get("x95"),
        "x_strict_explore": bound.get("x_strict"),
        "estimate_with_without_baselines": rec.get("estimate"),
        "robustness": _robustness_summary(rec.get("robustness")),
        "calendar": rec.get("calendar"),
        "dataset": rec.get("dataset"),
        "limitations": rec.get("limitations"),
    }


def _headline(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    ex = [r for r in rows if (r.get("explore") or {}).get("p_descriptive_uncorrected") is not None]
    ps = [float(r["explore"]["p_descriptive_uncorrected"]) for r in ex]
    return {
        "tests": len(rows),
        "registrable": sum(1 for r in rows if r.get("registrable")),
        "below_entry_level": sum(1 for r in rows if r.get("below_entry_level")),
        "gate_untestable": sum(1 for r in rows if (r.get("gate") or {}).get("untestable")),
        "with_explore_numbers": len(ex),
        "explore_p_at_or_below_0_05_uncorrected": sum(1 for x in ps if x <= 0.05),
        "expected_at_or_below_0_05_if_no_effect": round(0.05 * len(ps), 2),
        "smallest_explore_p_uncorrected": min(ps) if ps else None,
        "note": ("descriptive, explore period only, no multiplicity correction and no verdict; "
                 "about 5% of tests reach p <= 0.05 with no effect at all"),
    }


def run_preview(adapter: Any, run: _pl.DomainRun, tests: Sequence[_pl.TestDefinition], *,
                repo_root: Optional[Path] = None, sealer: Any = None,
                info: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    """Every test on the EXPLORE period only; descriptive numbers, no verdict.

    The tests are registered in a throwaway family lock (deleted after the
    run), so the preview touches no real lock, batch or alpha. The outcomes
    are read through sealbundle.guarded() without a handle (explore rows
    only); a run that came back with a confirm row or an S, C or E stops
    with PreviewError. If the adapter refuses its outcomes (the monsoon
    firewall of ADR-007 4.3) the preview keeps the outcome-free gate only
    and says why.
    """
    import tempfile

    from .gate import FAMILY_MIN_LEVEL

    info = dict(info or {})
    tinfo = info.get("tests") or {}
    refused: Optional[str] = None
    # Below the entry level (L2) the gate makes every test Untestable, which is
    # right for a verdict. A preview gives no verdict, so it computes the
    # descriptive numbers of every test and prints each test's real level.
    real_level = {t.test_id: int(t.level) for t in tests}
    tests = [dataclasses.replace(t, level=max(int(t.level), FAMILY_MIN_LEVEL)) for t in tests]
    with tempfile.TemporaryDirectory(prefix="validity-preview-") as tmp:
        lock = FamilyLock(Path(tmp) / "preview.lock.jsonl", run.domain)
        dates = _dates(adapter)
        kept, lock_refused = [], []
        for t in tests:
            cal = np.asarray(_pl._evaluate(t.calendar, dates, t.test_id), dtype=bool)
            try:
                lock.register(rule_id=t.rule_id, version=t.version, outcome=t.outcome,
                              calendar_hash=calendar_hash(cal), variant=t.variant,
                              use_parents=list(t.use_parents), outcome_type=t.outcome_type)
            except FamilyError as exc:  # e.g. the same calendar and outcome as an earlier test
                lock_refused.append({"test_id": t.test_id, "reason": f"{type(exc).__name__}: {exc}"})
                continue
            kept.append(t)
        tests = kept
        try:
            res = _pl.run_domain(adapter, run, tests, lock, Path(tmp) / "run", handle=None, provisional=True,
                                 repo_root=repo_root, sealer=sealer, write=False)
        except Exception as exc:  # noqa: BLE001 - only an outcome refusal is turned into a gate-only preview
            if type(exc).__name__ != "FirewallError":
                raise
            refused = f"{type(exc).__name__}: {exc}"
            res = None
        if res is not None:
            if res.get("provisional") is not True or res.get("confirm") is not None:
                raise PreviewError("the preview run was not provisional")
            rows = [_preview_record(r, tinfo.get(r["test_id"], {})) for r in res.get("records", [])]
            for r in rows:
                r["level"] = real_level[r["test_id"]]
                r["below_entry_level"] = r["level"] < FAMILY_MIN_LEVEL
        else:
            gates = _gate_only(adapter, run, tests, lock)
            rows = []
            for t in tests:
                ti = tinfo.get(t.test_id, {})
                rows.append({"test_id": t.test_id, "rule_id": t.rule_id, "variant": t.variant, "name": t.name,
                             "level": real_level[t.test_id],
                             "below_entry_level": real_level[t.test_id] < FAMILY_MIN_LEVEL,
                             "registrable": ti.get("registrable"),
                             "registration_problems": ti.get("registration_problems", []),
                             "outcome": t.outcome, "outcome_type": t.outcome_type, "side": t.side,
                             "gate": _gate_summary(gates[t.test_id]), "explore": None,
                             "outcomes_refused": refused})
    per = adapter.periods()
    return _pl._clean({
        "schema": PREVIEW_SCHEMA,
        "domain": run.domain,
        "provisional": True,
        "verdicts": None,
        "period": {"explore": [str(per.explore[0]), str(per.explore[1])], "confirm_rows_read": False},
        "statement": ("Preview on the explore period only. Provisional, descriptive numbers; no Supported, "
                      "Contradicted or Excluded verdict can come from it, and no confirm row was read. "
                      "Tests below the entry level (L2) and unregistrable tests are computed and labelled."),
        "plan": info.get("plan") or {"sha256": run.plan_sha256},
        "vintage": dict(run.vintage),
        "sampling_frame": dict(run.sampling_frame),
        "outcomes_refused": refused,
        "notes": info.get("notes") or {},
        "excluded": info.get("excluded") or [],
        "refused_by_lock": lock_refused,
        "headline": _headline(rows),
        "records": sorted(rows, key=lambda r: r["test_id"]),
    })


def _select(tests: Sequence[_pl.TestDefinition], only: Sequence[str], skip: Sequence[str]
            ) -> Tuple[List[_pl.TestDefinition], List[str]]:
    """Tests whose rule id matches --rule (all when none) and no --skip-rule; the left-out ids."""
    import re

    keep, left = [], []
    for t in tests:
        ok = (not only or any(re.search(p, t.rule_id) for p in only)) and not any(re.search(p, t.rule_id)
                                                                              for p in skip)
        (keep if ok else left).append(t)
    for t in left:  # their calendars leave the shared sky evaluation
        for fn in (t.calendar, *t.sensitivity.values()):
            if hasattr(fn, "active"):
                fn.active = False
    return keep, [t.test_id for t in left]


def cmd_preview(b: Bindings, args: argparse.Namespace) -> int:
    """Explore-only preview of every principle of each domain (registrable or not); no verdict."""
    only, skip = list(getattr(args, "rule", None) or []), list(getattr(args, "skip_rule", None) or [])
    for d in _domains(b, args):
        tests, left = _select(b.preview_tests(d), only, skip)
        doc = run_preview(b.adapter(d), b.run_spec(d), tests, repo_root=b.layout.root,
                          sealer=b.sealer(), info=b.preview_info(d))
        if left:
            doc["left_out"] = {"rule": only, "skip_rule": skip, "test_ids": left,
                               "note": "left out of this preview on request; not run, no number"}
        path = b.layout.preview / b.preview_name(d) / "results.json"
        _write_json(path, doc)
        h = doc["headline"]
        _say(f"preview {d}: {h['tests']} tests ({h['registrable']} registrable), "
             f"{h['with_explore_numbers']} with explore numbers, "
             f"{h['explore_p_at_or_below_0_05_uncorrected']} at p <= 0.05 uncorrected -> {path}")
    return 0


# ----------------------------------------------------------------- commands
def cmd_register(b: Bindings, args: argparse.Namespace) -> int:
    """Register every test of a domain into the open batch. Reads no outcome."""
    code = 0
    for domain in _domains(b, args):
        adapter = b.adapter(domain)
        dates = _dates(adapter)
        lock = _lock(b, domain)
        known = set(lock.test_ids())
        disputes = b.disputes()
        for t in b.tests(domain):
            if t.rule is None:  # A-08: no test registers without its rule file
                _say(f"refused {t.test_id}: no rule file; registration checks the rule")
                code = 1
                continue
            problems = registration_problems(t.rule, disputes)
            if problems:
                _say(f"refused {t.test_id}: " + "; ".join(problems))
                code = 1
                continue
            cal = np.asarray(_pl._evaluate(t.calendar, dates, t.test_id), dtype=bool)
            h = calendar_hash(cal)
            if t.test_id in known:
                if lock.test_record(t.test_id)["calendar_hash"] != h:
                    _say(f"refused {t.test_id}: the calendar differs from the registered one")
                    code = 1
                else:
                    _say(f"already registered {t.test_id}")
                continue
            e = lock.register(rule_id=t.rule_id, version=t.version, outcome=t.outcome, calendar_hash=h,
                              variant=t.variant, use_parents=list(t.use_parents), outcome_type=t.outcome_type)
            _say(f"registered {t.test_id} batch {e['batch']} slot {e['seq']}")
    return code


def cmd_gate(b: Bindings, args: argparse.Namespace) -> int:
    """Whether the data can test each principle at all. Still no outcome read."""
    rows = []
    for domain in _domains(b, args):
        adapter = b.adapter(domain)
        dates = _dates(adapter)
        run = b.run_spec(domain)
        per = adapter.periods()
        confirm = _pl._mask_between(dates, per.confirm)
        tests = [t for t in b.tests(domain) if not args.test or t.test_id == args.test]
        prepared = _pl._prepare(tests, dates, _lock(b, domain), run)
        grade = adapter.dataset().grade
        for p in prepared:
            g = _pl._gate(p, dates, confirm, grade, run)
            rows.append({"domain": domain, "test_id": p.test.test_id, "untestable": bool(g.untestable),
                         "reason": g.untestable_reason, "can_support": g.can_support, "can_limit": g.can_limit})
    for r in rows:
        _say(f"{r['domain']} {r['test_id']}: " +
             (f"untestable ({r['reason']})" if r["untestable"] else
              f"can_support={r['can_support']} can_limit={r['can_limit']}"))
    return 0


def cmd_run(b: Bindings, args: argparse.Namespace) -> int:
    """Explore rows only; the results are provisional and cannot be published."""
    doms = _domains(b, args)
    state = current_state(b, b.domains())
    rid = _cl.run_id_for(b.today(), state)
    run_dir = b.layout.runs / f"{rid}.provisional"  # never a published run's directory
    last = _last_run_dir(b)
    for d in doms:
        _run_domain(b, d, run_dir / d, handle=None, provisional=True,
                    previous=(last / d / "results.json") if last else None)
        _say(f"ran {d} provisional -> {run_dir / d / 'results.json'}")
    _write_json(run_dir / "state.json", state)
    return 0


def cmd_seal(b: Bindings, args: argparse.Namespace) -> int:
    for d in _domains(b, args):
        problems = plan_problems(b.layout, d)  # N-05: the plan validator is on the seal path
        if problems:
            _say(f"refused to seal {d}: " + "; ".join(problems))
            return 1
        out = seal_domain(b.layout.root, b.seal_sources(d), remote=args.remote, branch=args.branch)
        _say(f"sealed {d}: batch {out['batch']} bundle {out['bundle_sha256'][:12]} commit {out['commit'][:12]}")
    return 0


def cmd_confirm(b: Bindings, args: argparse.Namespace) -> int:
    """Open the confirm period once (all checks of the seal bundle), then run with the handle."""
    state = current_state(b, b.domains())
    rid = _cl.run_id_for(b.today(), state)
    run_dir = b.layout.runs / rid
    last = _last_run_dir(b)
    for d in _domains(b, args):
        handle = issue_confirm_handle(b.layout.root, args.bundle, remote=args.remote, branch=args.branch)
        _run_domain(b, d, run_dir / d, handle=handle, provisional=False,
                    previous=(last / d / "results.json") if last else None)
        _say(f"confirmed {d} -> {run_dir / d / 'results.json'}")
    _write_json(run_dir / "state.json", state)
    return 0


def results_problems(b: Bindings, domain: str, results: Mapping[str, Any]) -> List[str]:
    """Why a results file may not be published (N-13): provisional, or not what the lock recorded.

    Every record must belong to a closed batch of the domain's family lock,
    and each batch's records must be byte for byte the results the lock
    hashed at the confirm. A page built from an edited results file is
    refused before it is written.
    """
    if results.get("provisional") is not False:
        return [f"{domain}: provisional results are never published"]
    lock = _lock(b, domain)
    out: List[str] = []
    batches = sorted({r.get("batch") for r in results.get("records", [])}, key=lambda x: (x is None, x))
    for n in batches:
        if n is None or n not in lock.closed_batches():
            out.append(f"{domain}: records of batch {n} are not in a closed batch of the lock")
            continue
        try:
            lock.verify_batch_results(n, _pl.batch_results_bytes(results, n))
        except FamilyError as exc:
            out.append(f"{domain}: {exc}")
    return out


def _report_run(b: Bindings, run_id: str, domains: Sequence[str]) -> List[str]:
    run_dir = b.layout.runs / run_id
    problems: List[str] = []
    for d in domains:
        rp = run_dir / d / "results.json"
        bad = results_problems(b, d, json.loads(rp.read_text(encoding="utf-8")))
        if bad:
            problems += bad
            continue
        out = b.layout.reports / run_id / d
        _rp.write_report(rp, out, b.layout.changelog if b.layout.changelog.exists() else None)
        problems += _rp.check_report(rp, out, changelog=b.layout.changelog if b.layout.changelog.exists() else None)
    b.layout.site.mkdir(parents=True, exist_ok=True)
    (b.layout.site / "changelog.qmd").write_text(
        _cl.render_qmd(_cl.read_entries(b.layout.changelog)), encoding="utf-8")
    return problems


def cmd_report(b: Bindings, args: argparse.Namespace) -> int:
    """Rebuild the pages of a run from its results JSON; the report gate must pass."""
    rid = args.run or (_cl.read_entries(b.layout.changelog) or [{}])[-1].get("run_id")
    if not rid:
        _say("error: no run to report; give --run or run `all` first")
        return 1
    doms = [d for d in (args.domains or sorted(p.name for p in (b.layout.runs / rid).iterdir() if p.is_dir()))]
    problems = _report_run(b, rid, doms)
    for p in problems:
        _say(f"gate: {p}")
    _say(f"report {rid}: " + ("failed" if problems else "built, gate passed"))
    return 1 if problems else 0


def cmd_diff(b: Bindings, args: argparse.Namespace) -> int:
    """The changelog comparison of any two runs (not recorded)."""
    da, db = b.layout.runs / args.run_a, b.layout.runs / args.run_b
    for p in (da, db):
        if not (p / "state.json").is_file():
            _say(f"error: {p} has no state.json")
            return 1
    sa = json.loads((da / "state.json").read_text(encoding="utf-8"))
    sb = json.loads((db / "state.json").read_text(encoding="utf-8"))
    entry = _cl.build_entry(args.run_b, args.run_a, _records(_results_of(da)), _records(_results_of(db)),
                            sa, sb, strict=False)
    entry.pop("state", None)
    _say(json.dumps(entry, indent=2, sort_keys=True, default=str))
    return 1 if entry.get("unexplained") else 0


def cmd_catalogue(b: Bindings, args: argparse.Namespace) -> int:
    rows = b.catalogue_rows()
    _write_json(b.layout.site / "catalogue.json", {"schema": "validity-catalogue/1", "principles": rows})
    _say(f"catalogue: {len(rows)} principles -> {b.layout.site / 'catalogue.json'}")
    return 0


def cmd_all(b: Bindings, args: argparse.Namespace) -> int:
    """Run every domain whose inputs changed, append the changelog, rebuild every report.

    Idempotent: with the inputs of the last entry it does nothing. It
    registers nothing. Provisional results are never published, and an
    unexplained change stops it before anything is recorded.
    """
    doms = b.domains()
    state = current_state(b, doms)
    entries = _cl.read_entries(b.layout.changelog)
    last = entries[-1] if entries else None
    if last is not None and last["state"] == state:
        _say(f"unchanged: inputs equal those of run {last['run_id']}; nothing to do")
        return 0
    rid = _cl.run_id_for(b.today(), state)
    run_dir = b.layout.runs / rid
    last_dir = b.layout.runs / last["run_id"] if last else None
    old_results = _results_of(last_dir) if last_dir and last_dir.is_dir() else {}
    results: Dict[str, Dict[str, Any]] = {}
    for d in doms:
        prev = last_dir / d / "results.json" if last_dir else None
        same = (last is not None and d in old_results
                and _slice(last["state"], d) == _slice(state, d))
        if same:
            (run_dir / d).mkdir(parents=True, exist_ok=True)
            (run_dir / d / "results.json").write_bytes((prev).read_bytes())
            results[d] = old_results[d]
            _say(f"{d}: inputs unchanged, results reused")
            continue
        handle = b.handle(d)
        results[d] = _run_domain(b, d, run_dir / d, handle=handle, provisional=handle is None, previous=prev)
        _say(f"{d}: ran ({'confirm' if handle else 'provisional'})")
    if any(r.get("provisional") is not False for r in results.values()):
        _say("error: provisional results cannot be published; nothing was recorded "
             "(seal and confirm each domain first)")
        return 1
    entry = _cl.build_entry(rid, last["run_id"] if last else None, _records(old_results), _records(results),
                            last["state"] if last else None, state)
    _write_json(run_dir / "state.json", state)
    row = _cl.append_entry(b.layout.changelog, entry)
    _say(f"changelog entry {row['seq']}: {len(entry['tests'])} test lines, "
         f"{entry['summary']['verdict_changes']} verdict changes")
    problems = _report_run(b, rid, doms)
    for p in problems:
        _say(f"gate: {p}")
    return 1 if problems else 0


# --------------------------------------------------------------------- main
def _parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="astro-validity", description=__doc__.split("\n")[0])
    ap.add_argument("--root", type=Path, default=None, help="repository root")
    ap.add_argument("--bindings", default=None, help="package.module:factory(layout) -> Bindings")
    sub = ap.add_subparsers(dest="command", required=True)

    def add(name: str, fn: Any, help_: str, domains: bool = True) -> argparse.ArgumentParser:
        p = sub.add_parser(name, help=help_)
        p.set_defaults(fn=fn)
        if domains:
            p.add_argument("domains", nargs="*", help="domains (default: all)")
        return p

    add("register", cmd_register, "register the tests of a domain (reads no outcome)")
    g = add("gate", cmd_gate, "can the data test each principle at all (reads no outcome)")
    g.add_argument("--test", default=None)
    add("run", cmd_run, "provisional run on explore rows only")
    pv = add("preview", cmd_preview, "explore-only preview of every principle: descriptive numbers, no verdict")
    pv.add_argument("--rule", action="append", default=[], help="only rules whose id matches (regex)")
    pv.add_argument("--skip-rule", action="append", default=[], help="leave out rules whose id matches (regex)")
    s = add("seal", cmd_seal, "write the seal bundle, close the batch, commit, push, timestamp")
    s.add_argument("--remote", default="origin")
    s.add_argument("--branch", default="main")
    c = add("confirm", cmd_confirm, "open the confirm period once and run with the handle")
    c.add_argument("--bundle", required=True)
    c.add_argument("--remote", default="origin")
    c.add_argument("--branch", default="main")
    r = add("report", cmd_report, "rebuild the pages of a run from its results JSON")
    r.add_argument("--run", default=None)
    d = add("diff", cmd_diff, "compare any two runs", domains=False)
    d.add_argument("run_a")
    d.add_argument("run_b")
    add("catalogue", cmd_catalogue, "write the principle catalogue", domains=False)
    add("all", cmd_all, "run what changed, append the changelog, rebuild every report", domains=False)
    return ap


def _load_bindings(spec: Optional[str], layout: Layout) -> Bindings:
    if not spec:
        return FileBindings(layout)
    mod, _, fn = spec.partition(":")
    if not mod or not fn:
        raise BindingsError("--bindings must look like package.module:factory")
    return getattr(importlib.import_module(mod), fn)(layout)


def main(argv: Optional[Sequence[str]] = None, bindings: Optional[Bindings] = None) -> int:
    args = _parser().parse_args(argv)
    try:
        b = bindings or _load_bindings(args.bindings, Layout(args.root or DEFAULT_ROOT))
        return int(args.fn(b, args))
    except BindingsError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # a stopped run is an exit code, not a traceback
        print(f"error: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
