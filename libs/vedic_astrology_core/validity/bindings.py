"""Bindings: build a domain run from its plan and the rule files (strategy audit 2 N-05).

ADR-007 sections 3 to 5 and ADR-008 sections 3, 7 and 8 say what "the plan
fixes" and what "the register step refuses". This module is the one path that
makes those sentences true for a real run: every input of
``pipeline.DomainRun`` and of every ``pipeline.TestDefinition`` is read from

* the domain plan ``studies/validity/domains/<name>.yaml``, loaded through
  ``validity/plan.py validate_plan`` with the SESOI table and the snapshot
  index (a plan with any problem is refused, PlanError);
* the rule files (``rules/**`` and the monsoon principles), expanded into
  tests by ``validity/variants.py``;
* ``rules/schema.py registration_problems`` with the DISPUTES.md lists;
* ``rules/levels.py level`` for the level;
* the domain adapters (``domains/earthquake.py``, ``metals.py``,
  ``monsoon.py``) for the grid, the dataset and the outcomes.

Nothing a caller types reaches a verdict input: level, SESOI, x-grid, side,
source date, disputed flag, known channel, reading flag, project-extension
flag, market and currency, guard bars, base rate, detrending window, missing
bars, baselines, vintage, plan seed and plan hash all come from the files.

Outcome types. The plan's types are mapped once (N-05: nothing mapped them):
continuous -> continuous, absolute_return -> log_ratio (on the log scale with
the plan's floor), event -> events, binary -> flags.

What is refused, with a reason, before any outcome is read (outcome-free):

* a rule with no conditions and no yearly calendar (not encodable);
* a test whose outcome the plan does not declare, or declares untestable;
* a declared variant or cell the evaluator cannot compute;
* a test whose used block the plan's detrending window would absorb
  (it would stop the whole run; ADR-008 A2);
* on a monthly grid, a rule whose horizon is not a month or longer (D-01).

Every built test carries ``registrable`` and its registration problems.
``DomainBinding.registrable_tests()`` is what ``register``, ``gate``, ``run``
and ``confirm`` see; the explore-only preview may show the others,
labelled.

Past data only. No forecast, no network.
"""

from __future__ import annotations

import inspect
import json
import re
from dataclasses import dataclass, field, replace
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
import yaml

from ..domains.base import Periods, verify_gate
from ..rules import levels as _levels
from ..rules.schema import Rule, parse_disputes, registration_problems
from ..stats import season as _season
from . import pipeline as _pl
from . import plan as _plan
from . import variants as _var
from .family import MAX_VARIANTS, calendar_hash

__all__ = [
    "BindingError",
    "OUTCOME_TYPES",
    "SIDES",
    "RuleFile",
    "Excluded",
    "BoundTest",
    "DomainBinding",
    "BoundAdapter",
    "SkyCalendar",
    "SkyGroup",
    "load_rule_files",
    "disputed_rule_ids",
    "load_domain_plan",
    "plan_files",
    "bind",
    "sampling_frame",
    "horizon_allows_monthly",
]

REPO = Path(__file__).resolve().parents[3]
PLANS_DIR = Path("studies") / "validity" / "domains"
SESOI_SOURCES = Path("studies") / "validity" / "sesoi_sources.yaml"
SNAPSHOT_INDEX = Path("data") / "snapshot_index.json"
LICENCES = Path("data") / "registry" / "licences.yaml"

#: Plan outcome type -> pipeline outcome type (validity/plan.py OUTCOME_TYPES -> stats/blocks.py).
OUTCOME_TYPES: Dict[str, str] = {
    "continuous": "continuous",
    "absolute_return": "log_ratio",
    "event": "events",
    "binary": "flags",
}
#: Rule test direction -> pipeline side (there is no default side).
SIDES: Dict[str, str] = {"increase": "greater", "decrease": "less", "either": "two-sided"}
_PLAN_SIDES = {"greater": "greater", "less": "less", "two_sided": "two-sided"}
_SOURCE_SLOT = re.compile(r"[A-Z][A-Za-z0-9 .,'()\-]{0,79}")
_MONTH_WORDS = re.compile(r"\b(month|months|monthly|season|seasons|year|years|yearly|annual)\b", re.I)
_CHUNK = 4000


class BindingError(RuntimeError):
    """The plan or the rule files cannot be bound into a run."""


# ------------------------------------------------------------------ inputs
@dataclass(frozen=True)
class RuleFile:
    """A validated rule, its file, and the monsoon yearly calendar spec (if any)."""

    rule: Rule
    path: Path
    season_calendar: Optional[Mapping[str, Any]] = None

    @property
    def encodable(self) -> bool:
        return self.rule.conditions is not None or self.season_calendar is not None


def load_rule_files(root: Path = REPO) -> Dict[str, RuleFile]:
    """Every rule file under rules/ plus the monsoon principles (rules/monsoon/_*.yaml).

    Raises BindingError when any file fails validation (a run never skips a
    broken rule in silence).
    """
    from ..domains import monsoon as _monsoon
    from ..rules.loader import load_rules

    loaded, problems = load_rules([Path(root) / "rules"])
    if problems:
        raise BindingError("rule files do not validate: " + "; ".join(str(p) for p in problems[:5]))
    out = {lr.rule.id: RuleFile(lr.rule, Path(lr.path)) for lr in loaded}
    mdir = Path(root) / "rules" / "monsoon"
    if mdir.is_dir():
        for pid, pr in _monsoon.load_principles(mdir).items():
            if pid in out:
                raise BindingError(f"{pid}: defined twice (rules loader and monsoon principles)")
            out[pid] = RuleFile(pr.rule, Path(pr.path), dict(pr.spec))
    return out


def disputed_rule_ids(root: Path = REPO) -> List[str]:
    """Rule ids named in any rules/**/DISPUTES.md (A-08).

    A DISPUTES.md may name a rule by its id or by its file name
    (``vyapar_ratna_inverse_dignity_gold.yaml``); a file name is read as
    the id of that file in the same folder. Without this, the lists name
    files and no rule id ever matched (strategy audit 2, A-08).
    """
    ids: set = set()
    for p in sorted((Path(root) / "rules").rglob("DISPUTES.md")):
        for token in parse_disputes(p.read_text(encoding="utf-8")):
            if token.endswith((".yaml", ".yml")):
                f = p.parent / token
                if f.is_file():
                    doc = yaml.safe_load(f.read_text(encoding="utf-8"))
                    if isinstance(doc, Mapping) and isinstance(doc.get("id"), str):
                        ids.add(doc["id"])
                continue
            ids.add(token)
    return sorted(ids)


def plan_files(root: Path = REPO) -> List[Path]:
    """The committed domain plans, sorted by file name."""
    d = Path(root) / PLANS_DIR
    return sorted(d.glob("*.yaml")) if d.is_dir() else []


def load_domain_plan(path: Path, root: Path = REPO) -> Dict[str, Any]:
    """Load and validate a domain plan with the SESOI table and the snapshot index.

    Raises plan.PlanError with every problem. A draft passes the validator
    (only a registered plan needs the owner sign-offs); ``register`` and
    ``seal`` check the status themselves.
    """
    root = Path(root)
    sesoi = root / SESOI_SOURCES
    index = root / SNAPSHOT_INDEX
    return _plan.load_plan(path, sesoi_sources_path=sesoi if sesoi.is_file() else None,
                           snapshot_index_path=index if index.is_file() else None)


def _registers(root: Path) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    index = json.loads((root / SNAPSHOT_INDEX).read_text(encoding="utf-8"))
    lic = yaml.safe_load((root / LICENCES).read_text(encoding="utf-8")) or {}
    return index, dict(lic.get("sources") or {})


# ------------------------------------------------------------- calendars
class SkyGroup:
    """Rules of one domain that share their sky: positions are computed once per instant.

    When any member needs instants it has not seen, every member with the
    same node model is evaluated on them from one GridEvaluator (the
    expensive part is the sky, not the predicate), so the placebo skies of
    one test serve the others. Reads no outcome.
    """

    def __init__(self, chunk: int = _CHUNK) -> None:
        self.chunk = int(chunk)
        self.members: List["SkyCalendar"] = []

    def fill(self, keys: np.ndarray, node_model: str) -> None:
        from ..rules.grid import GridEvaluator

        peers = [m for m in self.members if m.rule.node_model == node_model and m.active]
        need = np.unique(np.asarray(keys, dtype=np.int64))
        need = need[[any(int(k) not in m._cache for m in peers) for k in need]] if len(need) else need
        for a in range(0, len(need), self.chunk):
            part = need[a:a + self.chunk]
            moments = pd.DatetimeIndex(pd.to_datetime(part, unit="ns", utc=True))
            ev = GridEvaluator(moments, node_model=node_model)
            for m in peers:
                fired = ev.fired(m.rule)
                m._cache.update(zip((int(k) for k in part), (bool(v) for v in fired)))


class SkyCalendar:
    """A rule evaluated at instants, cached per instant (placebo skies reuse it).

    ``instants_of(dates)`` maps the pipeline's grid instants (or shifted
    ones) to the UTC instants at which the rule is read: the same instant
    (a concurrent reading) or the previous bar's fixing instant (a forward
    trigger on a market). The rule's ``window`` widens the firing over the
    instants of each call. Reads no outcome.
    """

    def __init__(self, rule: Rule, instants_of: Callable[[pd.DatetimeIndex], pd.DatetimeIndex],
                 chunk: int = _CHUNK, group: Optional[SkyGroup] = None) -> None:
        if rule.conditions is None:
            raise BindingError(f"{rule.id}: no conditions; nothing to evaluate")
        self.rule = rule
        self.instants_of = instants_of
        self.group = group if group is not None else SkyGroup(chunk)
        self.group.members.append(self)
        #: False keeps a calendar out of its group's shared evaluation until it is asked for
        #: (a preview that leaves a rule out should not pay for its sky).
        self.active = True
        self._cache: Dict[int, bool] = {}

    def _fill(self, keys: np.ndarray) -> None:
        missing = np.asarray([k for k in np.unique(keys) if int(k) not in self._cache], dtype=np.int64)
        if len(missing):
            self.active = True  # a calendar that is asked for is always evaluated
            self.group.fill(missing, self.rule.node_model)

    def __call__(self, dates: pd.DatetimeIndex) -> np.ndarray:
        inst = pd.DatetimeIndex(self.instants_of(pd.DatetimeIndex(dates)))
        inst = (inst.tz_localize("UTC") if inst.tz is None else inst.tz_convert("UTC")).as_unit("ns")
        keys = inst.asi8  # nanoseconds since the epoch, whatever unit the caller's index had
        self._fill(keys)
        fired = np.fromiter((self._cache[int(k)] for k in keys), dtype=bool, count=len(keys))
        if self.rule.window is not None:
            from ..rules.grid import apply_window

            fired = apply_window(fired, inst, self.rule.window)
        return fired


def _utc(dates: pd.DatetimeIndex) -> pd.DatetimeIndex:
    d = pd.DatetimeIndex(dates)
    return d.tz_localize("UTC") if d.tz is None else d.tz_convert("UTC")


class _YearCalendar:
    """A monsoon principle's yearly calendar on a date grid (one bar per season)."""

    def __init__(self, adapter: Any, principle_id: str, variant: Optional[Mapping[str, str]] = None):
        self.adapter = adapter
        self.pid = principle_id
        self.variant = dict(variant or {})
        self._cache: Dict[int, bool] = {}

    def __call__(self, dates: pd.DatetimeIndex) -> np.ndarray:
        years = np.asarray(pd.DatetimeIndex(dates).year, dtype=int)
        need = sorted({int(y) for y in years} - set(self._cache))
        if need:
            cal = self.adapter.calendar(self.pid, self.variant or None, years=need)
            self._cache.update({int(y): bool(a) for y, a in zip(cal.years, cal.active)})
        return np.asarray([self._cache[int(y)] for y in years], dtype=bool)


# --------------------------------------------------------------- adapters
class BoundAdapter:
    """A domain adapter seen through the plan: plan outcome ids, declared missing bars.

    ``outcome_fns`` maps each plan outcome id to a function of the adapter's
    raw outcome mapping giving one value per grid bar. ``missing`` maps an
    outcome id to a boolean array on the grid (outcome-free: from dates,
    gaps and burn-in only); those bars are set to NaN here and declared to
    the pipeline through ``DomainRun.missing_bars``. ``grid`` and
    ``periods`` override the adapter's (the monsoon grid of years becomes
    a date grid). ``outcomes()`` verifies the written gate first.
    """

    def __init__(self, inner: Any, domain: str, outcome_fns: Mapping[str, Callable[[Mapping[str, Any]], Any]],
                 *, missing: Optional[Mapping[str, np.ndarray]] = None, grid: Optional[pd.DatetimeIndex] = None,
                 periods: Optional[Periods] = None, verify: Optional[Callable[[], None]] = None) -> None:
        self.inner = inner
        self._verify = verify
        self.domain = domain
        self._fns = dict(outcome_fns)
        self._missing = {k: np.asarray(v, dtype=bool) for k, v in (missing or {}).items()}
        self._grid = grid
        self._periods = periods
        self.outcome_reads = 0

    def dataset(self) -> Any:
        return self.inner.dataset()

    def grid(self) -> Any:
        return self._grid if self._grid is not None else self.inner.grid()

    def periods(self) -> Periods:
        return self._periods if self._periods is not None else self.inner.periods()

    def calendar_context(self) -> Mapping[str, Any]:
        return self.inner.calendar_context()

    def outcomes(self, gate: Any = None, *, gate_path: Any = None) -> Dict[str, np.ndarray]:
        verify_gate(gate, gate_path)
        if self._verify is not None:  # e.g. the pinned snapshot's bytes (N-21), before any row is read
            self._verify()
        raw = self.inner.outcomes(gate, gate_path=gate_path)
        self.outcome_reads += 1
        n = len(self.grid())
        out: Dict[str, np.ndarray] = {}
        for oid, fn in self._fns.items():
            v = np.asarray(fn(raw), dtype=float).ravel()
            if len(v) != n:
                raise BindingError(f"outcome {oid!r} has {len(v)} values for {n} grid bars")
            m = self._missing.get(oid)
            if m is not None:
                v = np.where(m, np.nan, v)
            out[oid] = v
        return out

    def controls(self, gate: Any = None, *, gate_path: Any = None) -> Any:
        return self.inner.controls(gate, gate_path=gate_path)


# ----------------------------------------------------------------- output
@dataclass(frozen=True)
class Excluded:
    """A (rule, outcome) the plan cannot run, and why (outcome-free)."""

    rule_id: str
    outcome: str
    category: str  # not_encodable | not_sourced | untestable
    reason: str
    variant: str = "primary"

    def as_dict(self) -> Dict[str, str]:
        return {"rule_id": self.rule_id, "outcome": self.outcome, "variant": self.variant,
                "category": self.category, "reason": self.reason}


@dataclass(frozen=True)
class BoundTest:
    """One test definition built from the files, with its registrability."""

    definition: _pl.TestDefinition
    registrable: bool
    problems: Tuple[str, ...]
    role: str
    level_missing: Mapping[int, Sequence[str]] = field(default_factory=dict)

    @property
    def test_id(self) -> str:
        return self.definition.test_id

    def as_dict(self) -> Dict[str, Any]:
        t = self.definition
        return {"test_id": t.test_id, "rule_id": t.rule_id, "variant": t.variant, "role": self.role,
                "outcome": t.outcome, "outcome_type": t.outcome_type, "side": t.side, "level": t.level,
                "registrable": self.registrable, "registration_problems": list(self.problems),
                "source_published": t.source_published, "direction_disputed": t.direction_disputed,
                "project_extension": t.project_extension, "sesoi": t.sesoi,
                "sensitivity_cells": sorted(t.sensitivity)}


@dataclass
class DomainBinding:
    """Everything one domain run needs, read from its plan and the rule files."""

    name: str
    plan_path: Path
    plan: Dict[str, Any]
    plan_sha256: str
    adapter: BoundAdapter
    run: _pl.DomainRun
    tests: List[BoundTest]
    excluded: List[Excluded]
    rule_files: Dict[str, RuleFile]
    notes: Dict[str, Any] = field(default_factory=dict)

    @property
    def domain(self) -> str:
        return self.run.domain

    def registrable_tests(self) -> List[_pl.TestDefinition]:
        return [b.definition for b in self.tests if b.registrable]

    def all_tests(self) -> List[_pl.TestDefinition]:
        return [b.definition for b in self.tests]

    def rule_ids(self) -> List[str]:
        return sorted({b.definition.rule_id for b in self.tests} | {e.rule_id for e in self.excluded})


# ---------------------------------------------------------------- helpers
def _sesoi(o: Mapping[str, Any]) -> Optional[float]:
    s = o.get("sesoi")
    if isinstance(s, Mapping) and s.get("kind") in ("source", "yardstick"):
        return float(s["value"])  # validate_plan has checked its source
    return None


def _entry(rf: RuleFile) -> str:
    src = rf.rule.source
    if src.cited:
        return "text"
    if src.url or "practitioner" in rf.path.parts:
        return "practitioner"
    return "project"


def _source_name(rule: Rule) -> Optional[str]:
    name = (rule.source.text or "").strip()
    return name if name and _SOURCE_SLOT.fullmatch(name) else None


def _reading_differs(rule: Rule) -> bool:
    r = rule.reading
    return bool(r is not None and r.text_says and r.text_says != r.kind)


def _horizon_text(rule: Rule) -> str:
    for c in rule.operationalisation:
        if c.choice == "horizon":
            return str(c.value)
    return ""


def horizon_allows_monthly(horizon: str) -> bool:
    """ADR-008 D-01: monthly data only for a horizon of a month, a season or a year."""
    return bool(_MONTH_WORDS.search(str(horizon or "")))


def _active_vintage(plan: Mapping[str, Any]) -> Dict[str, Any]:
    vs = [dict(v) for v in plan["vintages"]]
    want = plan.get("active_vintage")
    if want is None:
        if len(vs) != 1:
            raise BindingError("a plan with several vintages names its active_vintage")
        return vs[0]
    for v in vs:
        if v.get("id") == want:
            return v
    raise BindingError(f"active_vintage {want!r} is not a vintage of the plan")


def _snapshot(plan: Mapping[str, Any], snap_id: str) -> Dict[str, Any]:
    for s in plan["snapshots"]:
        if s.get("id") == snap_id:
            return dict(s)
    raise BindingError(f"vintage snapshot {snap_id!r} is not pinned in the plan")


def _date(v: Any) -> date:
    return pd.Timestamp(str(v)).date()


def _plan_periods(plan: Mapping[str, Any], pseudo: bool) -> Periods:
    sp = plan["split"]
    return Periods(explore=(_date(sp["explore"]["start"]), _date(sp["explore"]["end"])),
                   confirm=(_date(sp["confirm"]["start"]), _date(sp["confirm"]["end"])),
                   pseudo_out_of_sample=pseudo)


def _vintage_for_run(v: Mapping[str, Any]) -> Dict[str, Any]:
    per = v.get("confirm_period") or {}
    out = {k: v[k] for k in v if k not in ("confirm_period",)}
    out["confirm_period"] = {"start": str(per.get("start")), "end": str(per.get("end"))}
    out.setdefault("never_opened", False)
    return out


def _position_mask(grid: pd.DatetimeIndex, bars: np.ndarray) -> Callable[[pd.DatetimeIndex], np.ndarray]:
    """A missing-bars function: the declared mask, looked up by date on the grid."""
    lookup = pd.Series(np.asarray(bars, dtype=bool), index=pd.DatetimeIndex(grid))

    def fn(dates: pd.DatetimeIndex) -> np.ndarray:
        d = pd.DatetimeIndex(dates)
        got = lookup.reindex(d)
        if got.isna().any():
            raise BindingError("missing bars asked for instants outside the grid")
        return got.to_numpy(dtype=bool)

    return fn


# ------------------------------------------------------------ per domain
@dataclass
class _DomainParts:
    adapter: BoundAdapter
    calendar_for: Callable[[RuleFile, Optional[Rule], Optional[Mapping[str, str]]], Callable]
    cells_for: Callable[[RuleFile, "_var.Expansion"], Dict[str, Callable]]
    baselines: Optional[Callable[[pd.DatetimeIndex], Any]]
    missing: Dict[str, Callable[[pd.DatetimeIndex], np.ndarray]]
    detrend_window: Optional[int]
    monthly: bool
    notes: Dict[str, Any]


def _rule_cells(rf: RuleFile, exp: "_var.Expansion", make: Callable[[Rule], Callable]) -> Dict[str, Callable]:
    return {cid: make(r) for cid, r in exp.sensitivity.items()}


def _baseline_ids(plan: Mapping[str, Any]) -> List[str]:
    b = plan.get("baselines") or []
    return [x if isinstance(x, str) else x.get("id") for x in b] if isinstance(b, list) else list(b)


def _physical_baselines(ids: Sequence[str], notes: Dict[str, Any],
                        extra: Optional[Mapping[str, Callable[[pd.DatetimeIndex], np.ndarray]]] = None
                        ) -> Optional[Callable[[pd.DatetimeIndex], np.ndarray]]:
    """Nodal (and other computable) terms; None when a declared baseline has no data.

    Conservative (ADR-008 S-12): a plan that declares a baseline the run
    cannot compute gets no baselines at all, so R1 and R4 are not computable
    and do not pass; a partial set would pass as complete.
    """
    missing = []
    for b in ids:
        if b == "nodal_18_6y" or (extra and b in extra):
            continue
        missing.append(b)
    notes["baselines_declared"] = list(ids)
    if missing:
        notes["baselines_missing"] = missing
        return None

    def fn(dates: pd.DatetimeIndex) -> np.ndarray:
        cols = []
        for b in ids:
            if b == "nodal_18_6y":
                cols.append(np.asarray(_season.nodal_baseline(pd.DatetimeIndex(dates)), dtype=float))
            else:
                cols.append(np.asarray(extra[b](dates), dtype=float).reshape(len(dates), -1))
        return np.column_stack(cols)

    return fn


def _earthquake(plan: Mapping[str, Any], root: Path, vintage: Mapping[str, Any]) -> _DomainParts:
    from ..domains.earthquake import EarthquakeDomain

    index, lic = _registers(root)
    snap = _snapshot(plan, vintage["snapshot"])
    inner = EarthquakeDomain(index, lic, pinned_sha256=snap["sha256"])
    notes: Dict[str, Any] = {"limit_only": bool(plan.get("limit_only", False))}
    n_bars = len(inner.grid())
    fns = {}
    for o in plan["outcomes"]:  # the adapter gives each mainshock's bar; the outcome is the count per bar
        method = o.get("declustering", "gk")
        fns[o["id"]] = (lambda raw, m=method: np.bincount(np.asarray(raw["event_bins_by_method"][m], dtype=np.int64),
                                                          minlength=n_bars).astype(float))
    # Naive UTC on the pipeline's grid: its period masks compare with plain dates
    # (a tz-aware index cannot be compared with them); calendars read UTC again (_utc).
    grid = pd.DatetimeIndex(inner.grid()).tz_convert("UTC").tz_localize(None)

    def pinned_bytes() -> None:
        from ..stats.manifest import file_sha256

        path = inner.snapshot_path()
        if not Path(path).is_file() or file_sha256(path) != snap["sha256"]:
            raise BindingError(f"{path}: bytes do not hash to the plan's pinned SHA-256 (D-03, N-21)")

    adapter = BoundAdapter(inner, plan["domain"], fns, grid=grid, verify=pinned_bytes,
                           periods=_plan_periods(plan, inner.periods().pseudo_out_of_sample))

    group = SkyGroup()

    def calendar_for(rf: RuleFile, rule: Optional[Rule] = None, variant=None) -> Callable:
        return SkyCalendar(rule or rf.rule, _utc, group=group)

    def cells_for(rf: RuleFile, exp) -> Dict[str, Callable]:
        return _rule_cells(rf, exp, lambda r: SkyCalendar(r, _utc, group=group))

    return _DomainParts(adapter, calendar_for, cells_for, _physical_baselines(_baseline_ids(plan), notes), {},
                        plan.get("detrend_window"), False, notes)


def _gold(plan: Mapping[str, Any], root: Path, vintage: Mapping[str, Any]) -> _DomainParts:
    from ..domains import metals as _metals
    from ..markets import baselines as _mb

    index, lic = _registers(root)
    snap = _snapshot(plan, vintage["snapshot"])
    series = vintage.get("series") or plan.get("series")
    periods = _plan_periods(plan, _metals.SERIES[series].pseudo_out_of_sample)
    inner = _metals.MetalsDomain(index, lic, series=series, pinned_sha256=snap["sha256"], periods=periods,
                                 min_train=int(plan.get("min_train", _metals.MIN_TRAIN)),
                                 long_gap_days=int(plan.get("long_gap_days", _metals.LONG_GAP_DAYS)))
    if inner.domain != plan["domain"]:
        raise BindingError(f"series {series} is {inner.domain}, the plan is {plan['domain']}")
    spec = inner.spec
    grid = inner.grid()
    n = len(grid)
    monthly = spec.freq == "monthly"
    notes: Dict[str, Any] = {"series": series, "fixing": f"{spec.fixing_time} {spec.place.tz}"}
    gaps = inner.gap_days()
    long_gap = gaps > int(plan.get("long_gap_days", _metals.LONG_GAP_DAYS))
    burn = np.arange(n) < int(plan.get("min_train", _metals.MIN_TRAIN))
    notes["long_gap_bars"] = int(long_gap.sum())
    fns: Dict[str, Callable] = {}
    masks: Dict[str, np.ndarray] = {}
    for o in plan["outcomes"]:
        key = o.get("adapter_outcome") or o["id"]
        if o["type"] == "absolute_return":
            floor = float(o["floor"])
            fns[o["id"]] = (lambda raw, k=key, f=floor:
                            np.log(np.maximum(pd.Series(raw[k]).reindex(grid).to_numpy(float), f)))
        else:
            fns[o["id"]] = (lambda raw, k=key: pd.Series(raw[k]).reindex(grid).to_numpy(float))
        m = long_gap.copy()
        if key.endswith((".abs_return_std", ".extreme_move")):
            m |= burn
        masks[o["id"]] = m
    adapter = BoundAdapter(inner, plan["domain"], fns, missing=masks, grid=grid, periods=periods)
    raw_first = inner._raw_prices().index[0]  # the price date that opens the series (no value used)
    first_gap = grid[0] - raw_first

    def previous_fixing(dates: pd.DatetimeIndex) -> pd.DatetimeIndex:
        d = pd.DatetimeIndex(dates)
        d = d.tz_localize(None) if d.tz is not None else d
        prev = d[:-1].insert(0, d[0] - first_gap)
        return _metals.fixing_instants(prev.normalize(), spec)

    group = SkyGroup()

    def make(rule: Rule) -> Callable:
        return SkyCalendar(rule, previous_fixing, group=group)

    def calendar_for(rf: RuleFile, rule: Optional[Rule] = None, variant=None) -> Callable:
        return make(rule or rf.rule)

    def cells_for(rf: RuleFile, exp) -> Dict[str, Callable]:
        return _rule_cells(rf, exp, make)

    ids = _baseline_ids(plan)
    holidays = inner.holidays()
    extra = {"calendar_terms": lambda d: _mb.calendar_terms(pd.DatetimeIndex(d), holidays=holidays).to_numpy(float)}
    base = None
    if ids:
        unknown = [b for b in ids if b not in extra]
        notes["baselines_declared"] = list(ids)
        if unknown:
            notes["baselines_missing"] = unknown
        else:
            base = (lambda dates, _ids=tuple(ids):  # noqa: E731 - one closure over the declared ids
                    np.column_stack([extra[b](dates) for b in _ids]))
    return _DomainParts(adapter, calendar_for, cells_for, base,
                        {oid: _position_mask(grid, m) for oid, m in masks.items() if m.any()},
                        plan.get("detrend_window"), monthly, notes)


def _monsoon(plan: Mapping[str, Any], root: Path, vintage: Mapping[str, Any]) -> _DomainParts:
    from ..domains.monsoon import MonsoonDomain

    index, lic = _registers(root)
    adapter_plan = Path(root) / plan.get("adapter_plan", "studies/monsoon/plan.yaml")
    inner = MonsoonDomain(index, lic, plan_path=adapter_plan, rules_dir=Path(root) / "rules" / "monsoon",
                          repo=Path(root))
    periods = _plan_periods(plan, inner.periods().pseudo_out_of_sample)
    y0, y1 = periods.explore[0].year, periods.confirm[1].year
    years = np.arange(y0, y1 + 1)
    mm, dd = (int(x) for x in str(plan.get("season_date", "07-01")).split("-"))
    grid = pd.DatetimeIndex([pd.Timestamp(int(y), mm, dd) for y in years])
    notes: Dict[str, Any] = {"firewall": "real rainfall is read only through the adapter's ADR-007 4.3 firewall"}

    def series(raw: Mapping[str, Any], name: str) -> np.ndarray:
        s = pd.Series(raw["series"][name], index=np.asarray(raw["years"], dtype=int))
        return s.reindex(years).to_numpy(float)

    fns = {o["id"]: (lambda raw, k=o.get("adapter_outcome") or o["id"]: series(raw, k)) for o in plan["outcomes"]}
    adapter = BoundAdapter(inner, plan["domain"], fns, grid=grid, periods=periods)

    def calendar_for(rf: RuleFile, rule: Optional[Rule] = None, variant=None) -> Callable:
        return _YearCalendar(inner, rf.rule.id, variant)

    def cells_for(rf: RuleFile, exp) -> Dict[str, Callable]:
        spec = rf.season_calendar or {}
        return {f"{k}_{v}": _YearCalendar(inner, rf.rule.id, {k: v})
                for k, vals in (spec.get("variants") or {}).items() for v in vals}

    def enso(dates: pd.DatetimeIndex) -> np.ndarray:  # outcome-free covariate
        from ..domains.monsoon import parse_psl_monthly

        e = plan["enso"]
        snap = _snapshot(plan, e["series_id"])
        path = Path(root) / snap["file"]
        df = parse_psl_monthly(path.read_text(encoding="latin-1"))
        yrs = pd.DatetimeIndex(dates).year
        v = df.reindex(yrs)[["JUN", "JUL", "AUG", "SEP"]].mean(axis=1).to_numpy(float)
        if not np.isfinite(v).all():
            raise BindingError("the ENSO series does not cover every season of the grid")
        return v

    return _DomainParts(adapter, calendar_for, cells_for,
                        _physical_baselines(_baseline_ids(plan), notes, {"enso_nino34_jjas": enso}), {},
                        plan.get("detrend_window"), False, notes)


_DOMAIN_PARTS = {"earthquake": _earthquake, "gold": _gold, "monsoon": _monsoon}


# ------------------------------------------------------------------ bind
def _detrend_problem(cal_fn: Callable, dates: pd.DatetimeIndex, t: _pl.TestDefinition,
                     run: _pl.DomainRun, periods: Periods) -> Optional[str]:
    """The pipeline's own A2 check (pipeline._check_detrending), outcome-free, for one test.

    A test it would stop is refused here instead, so one long-episode rule
    does not stop every other test of the domain. Checked as for a run
    without a confirm handle, which also checks the explore design (the
    stricter case). None: passes, or no detrending applies.
    """
    if t.outcome_type not in ("continuous", "log_ratio") or not _season.detrend_required(dates):
        return None
    if run.detrend_window is None:
        return "a daily or hourly outcome needs the plan's detrend_window (ADR-008 A2)"
    cal = _pl._evaluate(cal_fn, dates, t.test_id)
    p = _pl._Prepared(t, cal, calendar_hash(cal))
    p.available = _pl._available(run, t.outcome, dates)
    p.detrend = True
    p.gate = SimpleNamespace(untestable=False)  # the check runs only for a testable gate
    explore = _pl._mask_between(dates, periods.explore)
    confirm = _pl._mask_between(dates, periods.confirm)
    params = inspect.signature(_pl._check_detrending).parameters
    try:
        if "explore" in params:
            _pl._check_detrending(p, dates, run, explore, confirm, False)
        else:
            _pl._check_detrending(p, dates, run)
    except _pl.PipelineError as exc:
        return str(exc).replace("; run stopped", "")
    return None


def bind(plan_path: Path, *, root: Path = REPO, rule_files: Optional[Dict[str, RuleFile]] = None,
         disputes: Optional[Sequence[str]] = None, n_domains: Optional[int] = None,
         check_detrend: bool = True) -> DomainBinding:
    """Build the run of one domain plan from the plan file and the rule files.

    Reads no outcome. Raises plan.PlanError for an invalid plan and
    BindingError when the plan names a domain with no adapter here.
    """
    root = Path(root)
    plan_path = Path(plan_path)
    plan = load_domain_plan(plan_path, root)
    domain = plan["domain"]
    if domain not in _DOMAIN_PARTS:
        raise BindingError(f"no adapter binding for domain {domain!r} (have {sorted(_DOMAIN_PARTS)})")
    rules = rule_files if rule_files is not None else load_rule_files(root)
    disp = list(disputes) if disputes is not None else disputed_rule_ids(root)
    vintage = _active_vintage(plan)
    parts = _DOMAIN_PARTS[domain](plan, root, vintage)
    dates = _pl._dates(parts.adapter.grid())
    outcomes = {o.get("rule_outcome") or o["id"]: o for o in plan["outcomes"]}
    untestable = {(u.get("domain"), u.get("outcome")): u.get("why", "declared untestable by the plan")
                  for u in plan.get("untestable_outcomes") or []}
    max_c = int((plan.get("alpha_spending") or {}).get("max_variants", MAX_VARIANTS))
    run = _pl.DomainRun(
        domain=domain, plan_seed=plan["seed"], plan_sha256=_plan.plan_hash(plan), vintage=_vintage_for_run(vintage),
        baselines=parts.baselines, plan=plan, disputes=tuple(disp),
        first_look_calendars=tuple(plan.get("first_look_calendars") or ()),
        pseudo_out_of_sample=bool(parts.adapter.periods().pseudo_out_of_sample),
        control_not_detected=False,
        domains_in_run_set=int(n_domains if n_domains is not None else max(len(plan_files(root)), 1)),
        detrend_window=None if parts.detrend_window is None else int(parts.detrend_window),
        missing_bars=dict(parts.missing),
    )
    tests: List[BoundTest] = []
    excluded: List[Excluded] = []
    cal_cache: Dict[Tuple[str, str], Callable] = {}
    cell_cache: Dict[Tuple[str, str], Dict[str, Callable]] = {}
    for rid in sorted(rules):
        rf = rules[rid]
        rule = rf.rule
        for spec in rule.tests:
            if (spec.domain, spec.outcome) in untestable:
                excluded.append(Excluded(rid, f"{spec.domain}.{spec.outcome}", "untestable",
                                         untestable[(spec.domain, spec.outcome)]))
        mine = [s for s in rule.tests if s.domain == domain]
        if not mine:
            continue
        if not rf.encodable:
            for s in mine:
                excluded.append(Excluded(rid, s.outcome, "not_encodable",
                                         f"no machine conditions (status {rule.status})"))
            continue
        problems = tuple(registration_problems(rule, disp))
        lvl = _levels.level(rule)
        try:
            exps = _var.expand(rule, domain, max_candidates=max_c)
        except _var.VariantError as exc:
            excluded.append(Excluded(rid, ",".join(s.outcome for s in mine), "untestable", str(exc)))
            continue
        for exp in exps:
            o = outcomes.get(exp.test.outcome)
            if o is None:
                excluded.append(Excluded(rid, exp.test.outcome, "untestable",
                                         "the plan declares no such outcome", exp.variant))
                continue
            if exp.not_computable and rf.season_calendar is None:
                excluded.append(Excluded(rid, o["id"], "untestable", "; ".join(exp.not_computable), exp.variant))
                continue
            if parts.monthly and not horizon_allows_monthly(_horizon_text(rule)):
                excluded.append(Excluded(rid, o["id"], "untestable",
                                         "monthly data needs a horizon of a month or longer (ADR-008 D-01)",
                                         exp.variant))
                continue
            plan_side = _PLAN_SIDES.get(str(o.get("side")))
            if plan_side not in (None, "two-sided") and plan_side != exp.side:
                excluded.append(Excluded(rid, o["id"], "untestable",
                                         f"the plan fixes side {plan_side}; the rule claims {exp.side}",
                                         exp.variant))
                continue
            key = (rid, exp.variant)  # one calendar per rule variant: its cache serves every outcome
            if key not in cal_cache:
                cal_cache[key] = parts.calendar_for(rf, exp.rule if exp.variant != "primary" else None)
                cell_cache[key] = parts.cells_for(rf, exp) if exp.role == "primary" else {}
            cal, cells = cal_cache[key], cell_cache[key]
            t = _pl.TestDefinition(
                rule_id=rid, version=int(rule.version), outcome=o["id"], calendar=cal, side=exp.side,
                outcome_type=OUTCOME_TYPES[o["type"]], x_grid=[float(x) for x in o["grid_x"]],
                name=rule.name, level=int(lvl.level), rule=exp.rule, variant=exp.variant,
                merge_gap=plan["merge_gap"], guard_bars=int(o.get("guard_bars", plan["guard_bars"])),
                sesoi=_sesoi(o), base_rate=o.get("base_rate"), noise_sd=o.get("noise_sd"),
                encoded=True, source_published=rule.source.published,
                direction_disputed=rid in set(disp), known_channel=rule.known_channel,
                reading_differs=_reading_differs(rule), source_name=_source_name(rule),
                project_extension=bool(exp.test.project_extension), tuned=bool(rule.tuning_log),
                use_parents=tuple(rule.use_fingerprint()["uses"]), sensitivity=cells,
                placebo_kinds=tuple(plan.get("placebo_sets") or ("time_shift",)), entry=_entry(rf),
                market=str(o.get("market") or "not a market"), currency=str(o.get("currency") or "none"),
                justified=bool(exp.test.quote),
            )
            if check_detrend:
                why = _detrend_problem(cal, dates, t, run, parts.adapter.periods())
                if why:
                    excluded.append(Excluded(rid, o["id"], "untestable", why, exp.variant))
                    continue
            tests.append(BoundTest(t, not problems, problems, exp.role, dict(lvl.missing)))
    out = DomainBinding(plan_path.stem, plan_path, plan, run.plan_sha256, parts.adapter, run, tests, excluded,
                        rules, dict(parts.notes))
    out.run = replace(run, sampling_frame=sampling_frame(out))
    return out


def sampling_frame(binding: DomainBinding) -> Dict[str, int]:
    """Distinct rules per reason they did not enter (ADR-008 7.1 frame table, O-02)."""
    tested = {b.definition.rule_id for b in binding.tests}
    out = {"not_encodable": set(), "not_sourced": set(), "untestable": set()}
    for e in binding.excluded:
        if e.rule_id not in tested:
            out[e.category if e.category in out else "untestable"].add(e.rule_id)
    for b in binding.tests:
        if not b.registrable and any(p.startswith("source.") for p in b.problems):
            out["not_sourced"].add(b.definition.rule_id)
    return {k: len(v) for k, v in out.items()}
