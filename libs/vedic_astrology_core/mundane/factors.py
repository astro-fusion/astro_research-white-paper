"""Factors that fire at an event, for the case file (ADR-006 section 2.1 section 7, WP-54).

The declared tests of the plan (``studies/mundane/hypothesis.yaml``, families
F1 to F4) are the catalogued factors. Each test is a partition: exactly one
cell is true at any instant. For one event and one chart this module finds the
cell that is true, takes the evidence sentence from the rule engine's own
predicate (it never writes its own), and adds:

* the method ids, the weakest citation status and level among them, and the
  tier (an ``extended`` method is labelled as such);
* stability: the factor is evaluated across the chart's founding-time window
  (``stability.check_founding``) and across the event's own time window
  (``stability.check_event``); for a dasha factor the dasha module's own
  boundary check (``dasha_at_event``) is added. Stable only if all agree;
* the base rate: the share of calendar dates (every ``BASE_RATE_STEP_DAYS``
  days at 12:00 UTC, from the plan's control period, from the chart's
  ``valid_from``) on which the same cell is true for the same chart. It needs
  no event data. It is the one-line answer to "is this striking?".

A test that cannot be evaluated (no founding time for a lagna count, grade D
for a dasha, a varga that is not computable) is listed in ``not_evaluated``
with the reason; it never silently disappears.

Nothing here counts anything over events: no aggregate, no p-value.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import yaml

from ..rules.context import EvalContext, Location, Sky
from ..rules.predicates import PREDICATES, Outcome
from . import dasha as dasha_mod
from . import stability as stab
from .catalogue import Catalogue, Method, load_catalogue, repo_root
from .charts import chart_moment
from .registry import Chart, Event, chart_applies, chart_grade

PLAN_PATH = repo_root() / "studies" / "mundane" / "hypothesis.yaml"
#: Calendar step of the base rate, days (sampled at 12:00 UTC).
BASE_RATE_STEP_DAYS = 7
#: Step of the event-side stability check by the event's half-window, minutes.
EVENT_STEP_MINUTES = ((1.0, 1.0), (30.0, 5.0), (1e9, 30.0))
#: Plan cell parameter to the predicate's list parameter.
_LIST_PARAM = {"lord": "lords", "house": "houses", "houses": "houses", "dignity": "dignities"}
_LAGNA_NEEDS = ("d1_lagna", "d9_lagna")
_STATUS_RANK = {"unverified": 0, "page_cited": 1, "verified": 2}
_TIER_RANK = {"core": 0, "extended": 1, "phase2": 2, "phase3": 3}
_LEVEL_OF = {"antar": 2, "pratyantar": 3, "maha": 1}


class FactorError(ValueError):
    """A plan test cannot be read or evaluated."""


class NotEvaluable(FactorError):
    """A test cannot be evaluated for this chart and event; the message says why."""


# ---------------------------------------------------------------- the plan
@dataclass(frozen=True)
class FactorTest:
    """One declared omnibus test (one partition) of the plan."""

    family_id: str
    test_id: str
    predicate: str
    params: Dict[str, Any]
    cell_param: str
    cells: Tuple[Any, ...]
    needs_stable: Tuple[str, ...]
    methods: Tuple[str, ...]
    collapse: Optional[Dict[str, Any]] = None


def load_plan(path: Path = PLAN_PATH) -> Dict[str, Any]:
    """Read the plan; only the keys this module uses are checked."""
    plan = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(plan, dict) or plan.get("schema") != "mundane-plan/1":
        raise FactorError(f"{path}: not a mundane-plan/1 file")
    return plan


def plan_tests(plan: Dict[str, Any]) -> List[FactorTest]:
    """Every test of every family, in file order."""
    out: List[FactorTest] = []
    for fam in plan["families"]:
        for t in fam["tests"]:
            out.append(
                FactorTest(
                    family_id=fam["id"],
                    test_id=t["id"],
                    predicate=t["predicate"],
                    params=dict(t.get("params") or {}),
                    cell_param=t["cell_param"],
                    cells=tuple(t["cells"]),
                    needs_stable=tuple(t.get("needs_stable") or ()),
                    methods=tuple(t["methods"]),
                    collapse=fam.get("collapse"),
                )
            )
    return out


def factor_id(test: FactorTest, cell: Any) -> str:
    """``<test_id>:<cell>`` as in the plan."""
    return f"{test.test_id}:{cell}"


# ----------------------------------------------------------- one test, one sky
class _Prepared:
    """Validated parameters of one test, built once and reused for every date."""

    def __init__(self, test: FactorTest):
        self.test = test
        self.spec = PREDICATES[test.predicate]
        self._params: Dict[Any, Any] = {}
        self._dignity_of_cell: Dict[str, List[str]] = {}
        if test.cell_param == "dignity":
            col = test.collapse or {}
            for cell in test.cells:
                self._dignity_of_cell[cell] = list(col.get(cell, []))
            self._priority = list(col.get("priority") or [])
            self._cell_of_dignity = {d: c for c, ds in self._dignity_of_cell.items() for d in ds}

    def _validated(self, key: Any, extra: Dict[str, Any]):
        if key not in self._params:
            self._params[key] = self.spec.params.model_validate({**self.test.params, **extra})
        return self._params[key]

    def outcome(self, ctx: EvalContext, cell: Any) -> Outcome:
        """The predicate's outcome for one plan cell (not for the collapsed dignity cell)."""
        name = _LIST_PARAM.get(self.test.cell_param, self.test.cell_param)
        p = self._validated(("cell", cell), {name: [cell]})
        return self.spec.func(ctx, p)

    def _dignity(self, ctx: EvalContext) -> Tuple[str, str]:
        varga = int(self.test.params.get("varga", 1))
        found: Dict[str, str] = {}
        for d in self._priority:
            if d == "moolatrikona" and varga != 1:
                continue  # a degree range of the rashi: no meaning for a varga sign
            p = self._validated(("dignity", d), {"dignities": [d]})
            o = self.spec.func(ctx, p)
            if o.held:
                found[d] = o.evidence
        for d in self._priority:  # priority order: first found decides the cell
            if d in found:
                return self._cell_of_dignity[d], found[d]
        raise NotEvaluable(f"{self.test.test_id}: no dignity found")

    def cell(self, ctx: EvalContext) -> Tuple[Any, str]:
        """The cell that is true and the rule engine's evidence sentence."""
        if self.test.cell_param == "dignity":
            return self._dignity(ctx)
        for c in self.test.cells:
            o = self.outcome(ctx, c)
            if o.held:
                return c, o.evidence
        raise NotEvaluable(f"{self.test.test_id}: no cell of the partition is true")

    def held(self, ctx: EvalContext, cell: Any) -> bool:
        if self.test.cell_param == "dignity":
            return self._dignity(ctx)[0] == cell
        return self.outcome(ctx, cell).held


def _natal_sky(chart: Chart, moment: datetime) -> Sky:
    return Sky(moment, Location(chart.lat, chart.lon, "UTC"), "mean")


def _ctx(chart: Chart, event_moment: datetime, natal_moment: datetime) -> EvalContext:
    return EvalContext(Sky(event_moment, None, "mean"), _natal_sky(chart, natal_moment))


def _precheck(test: FactorTest, chart: Chart) -> None:
    """Raise :class:`NotEvaluable` when the chart cannot support this test at all."""
    uses_dasha = test.predicate.startswith("dasha_")
    uses_lagna = any(n in _LAGNA_NEEDS for n in test.needs_stable)
    if chart.time is None:
        if uses_dasha:
            raise NotEvaluable(dasha_mod.UNSUPPORTED_REASON)
        if uses_lagna:
            raise NotEvaluable("founding time unknown (date-only chart): there is no lagna and no house from it")
    if chart_grade(chart) == "X":
        raise NotEvaluable("grade X chart (date disputed) is excluded")


# -------------------------------------------------------------- base rates
_RATE_CACHE: Dict[Tuple, Dict[str, Any]] = {}


def base_rate_dates(chart: Chart, plan: Dict[str, Any]) -> List[datetime]:
    """Calendar dates (12:00 UTC) of the base rate: the plan's control period, from valid_from."""
    span = plan["controls"]["C1_season_matched"]["draw_from"]
    start = max(date.fromisoformat(str(span["start"])), chart.valid_from)
    end = date.fromisoformat(str(span["end"]))
    out, d = [], start
    while d <= end:
        out.append(datetime.combine(d, time(12, 0), tzinfo=timezone.utc))
        d += timedelta(days=BASE_RATE_STEP_DAYS)
    return out


def base_rate(
    prepared: "_Prepared", cell: Any, chart: Chart, plan: Dict[str, Any]
) -> Dict[str, Any]:
    """Share of calendar dates on which ``cell`` of this test is true for ``chart``."""
    key = (chart.chart_id, prepared.test.test_id, str(cell), str(plan["id"]), plan["controls"]["C1_season_matched"]["draw_from"]["start"], BASE_RATE_STEP_DAYS)
    if key in _RATE_CACHE:
        return _RATE_CACHE[key]
    dates = base_rate_dates(chart, plan)
    if not dates:
        out = {"value": None, "reason": "the chart is not valid for any date of the control period"}
    else:
        natal = _natal_sky(chart, chart_moment(chart))
        shared: Dict[int, list] = {}
        n_true = 0
        for t in dates:
            ctx = EvalContext(Sky(t, None, "mean"), natal, shared)
            n_true += bool(prepared.held(ctx, cell))
        out = {
            "value": n_true / len(dates),
            "reason": None,
            "dates": len(dates),
            "true_dates": n_true,
            "step_days": BASE_RATE_STEP_DAYS,
            "start": dates[0].date().isoformat(),
            "end": dates[-1].date().isoformat(),
            "time_utc": "12:00",
        }
    _RATE_CACHE[key] = out
    return out


# --------------------------------------------------------------- the factors
def _event_step(half: float) -> float:
    for limit, step in EVENT_STEP_MINUTES:
        if half <= limit:
            return step
    return 30.0


def method_row(method: Method) -> Dict[str, Any]:
    return {
        "id": method.id,
        "tier": method.tier,
        "tradition": method.tradition,
        "citation_status": method.citation_status(),
        "level": f"L{method.level()}",
    }


def weakest(rows: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """Weakest citation status, level and tier over method rows."""
    status = min((r["citation_status"] for r in rows), key=lambda s: _STATUS_RANK[s])
    level = min((int(r["level"][1:]) for r in rows))
    tier = max((r["tier"] for r in rows), key=lambda t: _TIER_RANK[t])
    return {"citation_status": status, "level": f"L{level}", "tier": tier}


def _stability_of(
    test: FactorTest,
    prep: _Prepared,
    chart: Chart,
    event: Event,
    cell: Any,
    dasha_levels: Optional[Dict[int, Any]],
) -> Dict[str, Any]:
    ev_moment = event.time_utc.astimezone(timezone.utc)
    nat_moment = chart_moment(chart)
    detail: Dict[str, Any] = {}
    values: List[Any] = []

    def founding(t: datetime):
        return prep.cell(_ctx(chart, ev_moment, t))[0]

    f = stab.check_founding(chart, founding, key=test.test_id)
    detail["founding_window"] = f.stable
    values += [str(v) for v in f.alternatives]

    half = stab.event_half_window(event)
    e = stab.check_event(
        event, lambda t: prep.cell(_ctx(chart, t, nat_moment))[0],
        step_minutes=_event_step(half), key=test.test_id,
    )
    detail["event_window"] = e.stable
    values += [str(v) for v in e.alternatives]

    if test.predicate.startswith("dasha_") and dasha_levels is not None:
        lv = dasha_levels[int(test.params.get("level", 1))]
        detail["dasha_boundaries"] = bool(lv.supported and lv.stable)
        if lv.reason:
            detail["dasha_reason"] = lv.reason
    stable = all(detail.values())
    return {
        "stable": stable,
        "detail": detail,
        "alternatives": sorted(set(values) - {str(cell)}),
        "founding_values": [{"value": v.value, "share": round(v.share, 4)} for v in f.values],
        "event_values": [{"value": v.value, "share": round(v.share, 4)} for v in e.values],
    }


def fired_factors(
    event: Event,
    chart: Chart,
    *,
    catalogue: Optional[Catalogue] = None,
    plan: Optional[Dict[str, Any]] = None,
    base_rates: Optional[Dict[str, Optional[float]]] = None,
) -> Dict[str, Any]:
    """Factors true at ``event`` for ``chart`` and the tests that could not be evaluated.

    ``base_rates`` may supply ``{factor_id: rate}`` (for instance from the WP-55
    aggregate); a factor missing from it is computed from the calendar here.
    Raises the registry's errors for a chart that does not apply to the event.
    """
    cat = catalogue or load_catalogue()
    plan = plan or load_plan()
    chart_applies(chart, event.time_utc)
    ev = event.time_utc.astimezone(timezone.utc)
    out: Dict[str, Any] = {"computable": True, "reason": None, "rows": [], "not_evaluated": [],
                           "plan_id": plan["id"], "tests_declared": 0}
    tests = plan_tests(plan)
    out["tests_declared"] = len(tests)
    if event.time_precision not in stab.EVENT_HALF_WINDOW_MINUTES:
        out.update(computable=False, reason=f"event time precision {event.time_precision!r} is excluded")
        out["not_evaluated"] = [{"test_id": t.test_id, "reason": out["reason"]} for t in tests]
        return out

    dasha_levels: Optional[Dict[int, Any]] = None
    dasha_reason = None
    try:
        res = dasha_mod.dasha_at_event(
            chart, ev, event_half_window_minutes=stab.event_half_window(event), catalogue=cat
        )
        dasha_levels = {lv.level: lv for lv in res.levels}
    except dasha_mod.DashaWindowError as exc:
        dasha_reason = str(exc)

    ctx = _ctx(chart, ev, chart_moment(chart))
    for test in tests:
        try:
            _precheck(test, chart)
            if test.predicate.startswith("dasha_") and dasha_levels is None:
                raise NotEvaluable(dasha_reason or "dasha not available")
            prep = _Prepared(test)
            cell, evidence = prep.cell(ctx)
        except NotEvaluable as exc:
            out["not_evaluated"].append({"test_id": test.test_id, "reason": str(exc)})
            continue
        except Exception as exc:  # a varga that is not computable, a missing input
            out["not_evaluated"].append({"test_id": test.test_id, "reason": f"{type(exc).__name__}: {exc}"})
            continue

        methods = [method_row(cat.get(m)) for m in test.methods]
        fid = factor_id(test, cell)
        st = _stability_of(test, prep, chart, event, cell, dasha_levels)
        if base_rates is not None and fid in base_rates:
            br = {"value": base_rates[fid], "reason": None if base_rates[fid] is not None else "base rate from WP-55 aggregate"}
        else:
            br = base_rate(prep, cell, chart, plan)
        out["rows"].append(
            {
                "factor_id": fid,
                "family_id": test.family_id,
                "test_id": test.test_id,
                "cell": cell,
                "method": test.methods[0],
                "methods": methods,
                **weakest(methods),
                "fired": True,
                "stable": st["stable"],
                "stability": {k: st[k] for k in ("detail", "alternatives", "founding_values", "event_values")},
                "base_rate": br,
                "evidence": evidence,
            }
        )
    return out


__all__ = [
    "BASE_RATE_STEP_DAYS", "FactorError", "FactorTest", "NotEvaluable", "PLAN_PATH",
    "base_rate", "base_rate_dates", "factor_id", "fired_factors", "load_plan",
    "method_row", "plan_tests", "weakest",
]
