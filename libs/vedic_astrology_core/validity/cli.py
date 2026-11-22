"""`astro-validity`: register, gate, run, seal, confirm, report, diff, catalogue, all.

ADR-007 section 8 as amended by ADR-008 section 13 (WP-74). Every command goes
through the core modules; none computes a statistic of its own:

* register  validity/family.py   (slots, lock; rules/schema.py registration_problems)
* gate      validity/gate.py     (through the pipeline's own prepare and gate steps)
* run       validity/pipeline.py (explore rows only, provisional)
* seal      validity/sealbundle.py seal_domain
* confirm   validity/sealbundle.py issue_confirm_handle, then pipeline.run_domain
* report    validity/report.py   (reads results JSON only)
* all       run every domain whose inputs changed, append the changelog, report

No command reads an outcome before the gate files are written (the pipeline
enforces it) and none registers anything except `register`.

Run it as `python -m vedic_astrology_core.validity.cli`. The console script
`astro-validity` is planned (WP-18 owns pyproject.toml).

The cli needs *bindings*: how a domain's adapter, plan and tests are built
from the plan files and the rule files. The rule-to-test expansion
(core/validity/variants.py of ADR-007) is not built yet, so the default
bindings only list the domains and the plan hashes; pass
`--bindings package.module:factory` (a callable taking the Layout and
returning a Bindings) to use another. Tests use SimulatedDomain this way.

Past data only. No forecast, no network.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import importlib
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

import numpy as np
import pandas as pd

from .. import __version__ as _ENGINE_VERSION
from ..rules.schema import registration_problems
from . import changelog as _cl
from . import pipeline as _pl
from . import report as _rp
from .family import FamilyLock, calendar_hash
from .sealbundle import ConfirmHandle, SealSources, issue_confirm_handle, seal_domain

__all__ = ["Layout", "Bindings", "BindingsError", "FileBindings", "main", "current_state"]

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


class Bindings:
    """What the cli needs from the project. Override what a project has; the rest raises."""

    def __init__(self, layout: Layout):
        self.layout = layout

    @staticmethod
    def _missing(what: str) -> BindingsError:
        return BindingsError(
            f"no bindings for {what}: the rule-to-test expansion is not built yet; "
            "pass --bindings package.module:factory")

    def domains(self) -> List[str]:
        d = self.layout.domains_dir
        return sorted(p.stem for p in d.glob("*.yaml")) if d.is_dir() else []

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


class FileBindings(Bindings):
    """The default: domains from the plan files only."""


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
    results = _pl.run_domain(
        b.adapter(domain), b.run_spec(domain), b.tests(domain), _lock(b, domain), out_dir,
        handle=handle, provisional=provisional, repo_root=b.layout.root, sealer=b.sealer(),
        previous=previous if previous is not None and previous.is_file() else None)
    if handle is not None and results.get("provisional") is False:
        _pl.record_batch_results(_lock(b, domain), results)
    return results


def _last_run_dir(b: Bindings) -> Optional[Path]:
    entries = _cl.read_entries(b.layout.changelog)
    return b.layout.runs / entries[-1]["run_id"] if entries else None


# ----------------------------------------------------------------- commands
def cmd_register(b: Bindings, args: argparse.Namespace) -> int:
    """Register every test of a domain into the open batch. Reads no outcome."""
    code = 0
    for domain in _domains(b, args):
        adapter = b.adapter(domain)
        dates = _dates(adapter)
        lock = _lock(b, domain)
        known = set(lock.test_ids())
        for t in b.tests(domain):
            if t.rule is not None:
                problems = registration_problems(t.rule)
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
                              variant=t.variant, use_parents=list(t.use_parents))
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


def _report_run(b: Bindings, run_id: str, domains: Sequence[str]) -> List[str]:
    run_dir = b.layout.runs / run_id
    problems: List[str] = []
    for d in domains:
        rp = run_dir / d / "results.json"
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
