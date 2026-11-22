"""The validity pipeline: one domain run from calendars to result records (ADR-007 WP-69).

ADR-007 section 5 as amended by ADR-008 (sections 1 to 5, 9). Robustness R1 to
R4 come from core/validity/robustness.py (WP-94); this module wires every step
in one fixed order and adds no statistic of its own:

1.  Calendar of every test on the domain grid (outcome-free). A rule that
    fails to evaluate stops the run (PipelineError).
1a. Calendars checked against the family lock (registered, same calendar
    hash, pinned use: parents); eligibility and a_test from the lock.
2.  Gate per test (validity/gate.py); every gate file and the domain
    ``gate.json`` are written and hashed (domains/base.py write_gate).
2b. Outcomes read, once, through sealbundle.guarded() with the domain gate
    record: explore rows only without a confirm handle.
3.  Block designs and the primary block sign-flip test (stats/blocks.py,
    stats/season.py) on the explore, confirm and whole period. The confirm
    and whole-period designs must equal the gate's (S-15).
4.  Exclusion by effect removal (stats/exclusion.py): p_ex, X95 and X-strict
    at the test's a_test.
5.  Robustness R1 to R4 (validity/robustness.py): baselines, placebo skies,
    declared sensitivity cells, separability.
6.  Verdict, a pure function (validity/verdict.py).
7.  Limitations box (validity/limitations.py).
8.  Result records: the keys of schema validity-report-input/1
    (validity/report.py) plus the numbers, stamped through stats/seal.py
    SealedRun and stamp_results().

Holdout rules the code enforces:

* No outcome is read before every gate file and the domain ``gate.json`` are
  written; the adapter's ``outcomes()`` is called with that record.
* Outcomes are read only through sealbundle.guarded(). Without a valid
  confirm handle the adapter returns explore rows only, the run is stamped
  provisional, and p_sup, p_opp and p_ex stay None, so no S, C or E can
  come from it (the explore numbers are kept as descriptive). A provisional
  run never takes a handle.
* With a handle, every non-control test must be in the handle's batch and
  on its vintage. The handle is issued only after the keyed confirm ledger
  entries are committed (one confirm per lineage version, WP-89); a version
  bump is a new test id and so a new registration (WP-88).
* Robustness cells come only from the test definition, which the caller
  builds from the plan and the rule's ``variants``; no other cell exists.

Unchanged inputs: each record carries ``input_sha256`` (calendar hash, gate
file hash, dataset hash, plan hash, vintage, eligibility, a_test, test
definition). With ``previous`` (an earlier results file) a test of a closed
batch whose results the lock recorded is not recomputed: the stored batch
bytes are verified against the lock and the stored record is reused (ADR-008
3.4). Any other test with an unchanged input hash is recomputed and must
reproduce its stored record byte for byte, or the run stops
(ReproductionError).

Random streams: every draw of a test comes from family.stream_rng(plan seed,
test id, purpose) (ADR-008 3.5), so adding a test changes no other number.

Past data only. Nothing here forecasts. No thread, no network.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple, Union

import numpy as np
import pandas as pd

from ..domains.base import GateRecord, write_gate
from ..stats import blocks as _blocks
from ..stats import exclusion as _exclusion
from ..stats import season as _season
from ..stats.seal import SealedRun, stamp_results
from . import robustness as _rob
from .family import (
    PRIMARY,
    FamilyError,
    FamilyLock,
    a_test_for,
    alpha_for_batch,
    calendar_hash,
    canonical_bytes,
    make_test_id,
    stream_rng,
    stream_seed,
)
from .gate import GateResult, GateSpec, run_gate
from .limitations import build_limitations
from .report import REPORT_SCHEMA
from .sealbundle import ConfirmHandle, guarded, handle_is_valid
from .verdict import VerdictInput, verdict

__all__ = [
    "PIPELINE_SCHEMA",
    "RECORD_SCHEMA",
    "DOMAIN_GATE_SCHEMA",
    "PipelineError",
    "ReproductionError",
    "TestDefinition",
    "DomainRun",
    "run_domain",
    "batch_results_bytes",
    "record_batch_results",
    "record_id_for",
]

PIPELINE_SCHEMA = "validity-pipeline/1"
RECORD_SCHEMA = "validity-result/2"
DOMAIN_GATE_SCHEMA = "validity-domain-gate/1"
PathLike = Union[str, Path]
#: Grid instants in, one active flag per instant out. Reads no outcome.
CalendarFn = Callable[[pd.DatetimeIndex], Any]
#: Grid instants in, one row of baseline columns per instant out. Reads no outcome.
BaselinesFn = Callable[[pd.DatetimeIndex], Any]


class PipelineError(RuntimeError):
    """The run stopped: a rule failed to evaluate, a lock mismatch, a missing plan input."""


class ReproductionError(PipelineError):
    """A test with unchanged inputs did not reproduce its stored record exactly."""


# ------------------------------------------------------------------ inputs
@dataclass(frozen=True)
class TestDefinition:
    """One registered test as the plan and the rule file fix it (no outcome).

    ``calendar`` evaluates the principle at the given instants; the pipeline
    also calls it at time-shifted instants for the placebo skies (R2).
    ``sensitivity`` maps each declared cell (plan grid and the rule's
    ``variants``) to its calendar function; nothing else becomes a cell.
    ``x_grid`` is the plan's grid for X, on the claim scale. ``rule`` is the
    registered rule (core/rules/schema.py Rule) for the limitations box.
    """

    __test__ = False  # not a pytest class

    rule_id: str
    version: int
    outcome: str
    calendar: CalendarFn
    side: str
    outcome_type: str
    x_grid: Sequence[float]
    name: str
    level: int
    rule: Any = None
    variant: str = PRIMARY
    merge_gap: Any = 0
    guard_bars: int = 0
    sesoi: Optional[float] = None
    base_rate: Optional[float] = None
    noise_sd: Optional[float] = None
    encoded: bool = True
    source_published: Any = None
    direction_disputed: bool = False
    known_channel: Optional[str] = None
    reading_differs: bool = False
    source_name: Optional[str] = None
    project_extension: bool = False
    tuned: bool = False
    use_parents: Sequence[Mapping[str, Any]] = ()
    sensitivity: Mapping[str, CalendarFn] = field(default_factory=dict)
    placebo_kinds: Tuple[str, ...] = ("time_shift",)
    entry: str = "project"
    market: str = "simulated series"
    currency: str = "XXX"
    justified: bool = False
    n_draws: int = _blocks.DEFAULT_DRAWS
    n_thin: int = _exclusion.N_THIN
    power_reps: int = 200
    national_chart_ok: Optional[bool] = None

    @property
    def test_id(self) -> str:
        return make_test_id(self.rule_id, self.version, self.variant, self.outcome)

    def identity(self) -> Dict[str, Any]:
        """Every plan-fixed input of the test (part of the input hash)."""
        return {
            "test_id": self.test_id, "side": self.side, "outcome_type": self.outcome_type,
            "x_grid": [float(x) for x in self.x_grid], "level": int(self.level),
            "merge_gap": str(self.merge_gap), "guard_bars": int(self.guard_bars),
            "sesoi": self.sesoi, "base_rate": self.base_rate, "noise_sd": self.noise_sd,
            "encoded": self.encoded,
            "source_published": None if self.source_published is None else str(self.source_published),
            "direction_disputed": self.direction_disputed, "known_channel": self.known_channel,
            "reading_differs": self.reading_differs, "source_name": self.source_name,
            "project_extension": self.project_extension, "tuned": self.tuned,
            "sensitivity": sorted(self.sensitivity), "placebo_kinds": list(self.placebo_kinds),
            "n_draws": int(self.n_draws), "n_thin": int(self.n_thin), "power_reps": int(self.power_reps),
            "national_chart_ok": self.national_chart_ok, "name": self.name, "entry": self.entry,
            "market": self.market, "currency": self.currency, "justified": self.justified,
        }


@dataclass(frozen=True)
class DomainRun:
    """The domain plan's fixed inputs for one run.

    ``vintage`` is the plan vintage (id, confirm_period, seen, never_opened).
    ``baselines`` gives the domain's baselines on the grid (outcome-free); with
    none, R1 and R4 are not computable and do not pass (conservative: every
    sealed plan declares its baselines, ADR-008 S-12). ``plan`` is the plan
    mapping the limitations box reads (domain, outcomes, vintages).
    """

    domain: str
    plan_seed: Union[int, str]
    plan_sha256: str
    vintage: Mapping[str, Any]
    baselines: Optional[BaselinesFn] = None
    plan: Optional[Mapping[str, Any]] = None
    disputes: Sequence[str] = ()
    first_look_calendars: Sequence[str] = ()
    pseudo_out_of_sample: bool = False
    control_not_detected: bool = False
    domains_in_run_set: int = 1
    sampling_frame: Mapping[str, int] = field(
        default_factory=lambda: {"not_encodable": 0, "not_sourced": 0, "untestable": 0})


# ----------------------------------------------------------------- helpers
_SAFE = re.compile(r"[^a-z0-9]+")


def record_id_for(test_id: str) -> str:
    """A page id (lower-case, digits, underscore, at most 80 characters) unique per test id."""
    stem = _SAFE.sub("_", test_id.lower()).strip("_")[:60] or "test"
    return f"{stem}_{hashlib.sha256(test_id.encode('utf-8')).hexdigest()[:10]}"


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _clean(x: Any) -> Any:
    """JSON-safe copy: numpy scalars to Python, NaN and inf to None, tuples to lists."""
    if isinstance(x, Mapping):
        return {str(k): _clean(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_clean(v) for v in x]
    if isinstance(x, np.ndarray):
        return [_clean(v) for v in x.tolist()]
    if isinstance(x, (bool, np.bool_)):
        return bool(x)
    if isinstance(x, np.integer):
        return int(x)
    if isinstance(x, (float, np.floating)):
        v = float(x)
        return v if math.isfinite(v) else None
    return x


def _dates(grid: Sequence[Any]) -> pd.DatetimeIndex:
    return pd.DatetimeIndex(pd.to_datetime(list(grid)))


def _mask_between(dates: pd.DatetimeIndex, period: Tuple[Any, Any]) -> np.ndarray:
    a, b = pd.Timestamp(period[0]), pd.Timestamp(period[1])
    day = dates.normalize()
    return np.asarray((day >= a) & (day <= b), dtype=bool)


def _evaluate(fn: CalendarFn, instants: pd.DatetimeIndex, what: str) -> np.ndarray:
    """Evaluate a calendar function; any failure or a wrong shape stops the run."""
    try:
        raw = fn(instants)
    except Exception as exc:  # noqa: BLE001 - every failure stops the run
        raise PipelineError(
            f"{what}: the rule failed to evaluate ({type(exc).__name__}: {exc}); run stopped") from exc
    arr = np.asarray(raw)
    if arr.shape != (len(instants),):
        raise PipelineError(f"{what}: calendar has shape {arr.shape}, expected ({len(instants)},); run stopped")
    if arr.dtype.kind not in "bui" and not (arr.dtype.kind == "f" and np.isin(arr, (0.0, 1.0)).all()):
        raise PipelineError(f"{what}: calendar is not boolean; run stopped")
    return arr.astype(bool)


def _opposite(side: str) -> Optional[str]:
    return {"greater": "less", "less": "greater"}.get(side)


def _finite(x: Optional[float]) -> bool:
    return x is not None and math.isfinite(float(x))


def _same_sign(explore_t: Optional[float], side: str, confirm_t: Optional[float]) -> Optional[bool]:
    """The explore effect lies in the claimed direction (two-sided: the confirm sign)."""
    if not _finite(explore_t):
        return None
    if side == "greater":
        return explore_t > 0
    if side == "less":
        return explore_t < 0
    if not _finite(confirm_t) or confirm_t == 0 or explore_t == 0:
        return None
    return (explore_t > 0) == (confirm_t > 0)


def _magnitude(res: Optional[_blocks.BlockTestResult], side: str, outcome_type: str) -> Optional[float]:
    """The confirm estimate on the SESOI's scale, larger = further in the claimed direction."""
    if res is None or res.n_used == 0:
        return None
    if outcome_type in ("events", "flags"):
        r = res.estimate
        if not _finite(r) or r <= 0:
            return None
        return {"greater": r, "less": 1.0 / r}.get(side, max(r, 1.0 / r))
    t = res.statistic
    if not _finite(t):
        return None
    if outcome_type == "log_ratio":
        return math.exp({"greater": t, "less": -t}.get(side, abs(t)))
    return {"greater": t, "less": -t}.get(side, abs(t))


def _summary(res: Optional[_blocks.BlockTestResult]) -> Optional[Dict[str, Any]]:
    if res is None:
        return None
    used = res.n_used > 0
    return _clean({
        "statistic": res.statistic if used else None,
        "estimate": res.estimate if used else None,
        "scale": res.estimate_scale,
        "p": res.p_value,
        "alternative": res.alternative,
        "n_used": res.n_used,
        "n_dropped": res.n_dropped,
        "drop_counts": dict(res.drop_counts),
        "k_eff": res.k_eff,
        "design_id": res.design_id,
    })


def batch_results_bytes(results: Mapping[str, Any], batch: int) -> bytes:
    """Canonical bytes of the records of one batch (what the lock hashes, ADR-008 3.4)."""
    recs = sorted((r for r in results.get("records", []) if r.get("batch") == batch),
                  key=lambda r: r["test_id"])
    return canonical_bytes({"batch": batch, "records": recs})


def record_batch_results(lock: FamilyLock, results: Mapping[str, Any]) -> List[Dict[str, Any]]:
    """Hash every closed batch's records of a confirm run into the lock (once each)."""
    if results.get("provisional") is not False:
        raise PipelineError("only a non-provisional confirm run is recorded in the lock")
    out = []
    batches = sorted({r.get("batch") for r in results.get("records", []) if r.get("batch") is not None})
    for b in batches:
        if b in lock.closed_batches():
            out.append(lock.record_batch_results(b, batch_results_bytes(results, b)))
    return out


# --------------------------------------------------------------- per test
@dataclass
class _Prepared:
    test: TestDefinition
    calendar: np.ndarray
    cal_hash: str
    a_test: float = 0.0
    eligibility: Any = None
    gate: Optional[GateResult] = None
    gate_record: Optional[GateRecord] = None
    input_sha256: Optional[str] = None


def _a_test_open(lock: FamilyLock, test_id: str) -> float:
    """a_test before close: alpha_b / n_b of the open batch as it stands (gate.py GateSpec)."""
    rec = lock.test_record(test_id)
    if rec["a_test"] is not None:
        return float(rec["a_test"])
    if rec["control"]:
        return float(alpha_for_batch(1))
    b = rec["batch"]
    return a_test_for(alpha_for_batch(b), max(len(lock.batch_tests(b)), 1))


def _design(cal: np.ndarray, dates: pd.DatetimeIndex, t: TestDefinition, available=None) -> _season.SeasonDesign:
    """The control design the gate uses (core/stats/season.py control_design)."""
    return _season.control_design(cal, dates, merge_gap=t.merge_gap, guard_bars=t.guard_bars,
                                  available=available)


def _primary(design: _blocks.BlockDesign, y: np.ndarray, t: TestDefinition, side: str,
             plan_seed: Union[int, str]) -> _blocks.BlockTestResult:
    # A fresh generator on the test's own sign-flip stream for every call (3.5).
    return _blocks.primary_test(design, y, alternative=side, outcome_type=t.outcome_type,
                                rng=stream_rng(plan_seed, t.test_id, "signflip"), n_draws=t.n_draws)


def _statistic(design: _blocks.BlockDesign, y: np.ndarray, outcome_type: str) -> Optional[float]:
    if design.n_used == 0:
        return None
    v = float(_blocks.block_differences(design, y, outcome_type=outcome_type).statistic)
    return v if math.isfinite(v) else None


def _shifted(dates: pd.DatetimeIndex, kind: str, shift: int) -> pd.DatetimeIndex:
    if kind == "whole_year":
        return _season.shifted_instants(dates, int(shift))
    return dates + pd.Timedelta(days=int(shift))


def _robustness(p: _Prepared, dates: pd.DatetimeIndex, y_with: np.ndarray, avail: Optional[np.ndarray],
                full_res: _blocks.BlockTestResult, B: Optional[np.ndarray], season_linked: bool,
                run: DomainRun) -> Tuple[_rob.RobustnessResult, Dict[str, Any]]:
    """R1 to R4 of one test on its own statistic T over the available period."""
    t = p.test
    side = t.side
    t0 = full_res.statistic if full_res.n_used else float("nan")
    has_t = _finite(t0)
    # R1: the primary outcome already has the baselines removed (ADR-008 7.3).
    if B is None:
        r1 = _rob.CheckResult("R1", False, "not_computable", {"reason": "the plan declares no baselines"})
    elif not has_t:
        r1 = _rob.CheckResult("R1", False, "not_computable", {"reason": "no used block"})
    else:
        r1 = _rob.r1_baselines(t0, full_res.p_value, side)
    # R2: placebo skies, per test, on T only (section 5).
    placebos: List[_rob.Placebo] = []
    skipped = 0
    for kind in t.placebo_kinds:
        if kind != "time_shift":
            raise PipelineError(f"{t.test_id}: placebo kind {kind!r} is declared but the pipeline "
                                "implements only time_shift skies; run stopped")
        plan = _rob.time_shift_plan(season_linked, stream_rng(run.plan_seed, t.test_id, "placebo"))
        for s in plan["shifts"]:
            pc = _evaluate(t.calendar, _shifted(dates, plan["kind"], s), f"{t.test_id} placebo {s}")
            stat = _statistic(_design(pc, dates, t, avail).blocks, y_with, t.outcome_type)
            if stat is None:
                skipped += 1  # a sky with no used block has no statistic; it is not counted
                continue
            placebos.append(_rob.Placebo("time_shift", stat, _rob.changed_share(p.calendar, pc),
                                         f"{plan['kind']}:{s}"))
    r2 = _rob.r2_placebo(t0, placebos, side) if has_t else None
    # R3: declared sensitivity cells only.
    cells = []
    for name in sorted(t.sensitivity):
        cc = _evaluate(t.sensitivity[name], dates, f"{t.test_id} cell {name}")
        stat = _statistic(_design(cc, dates, t, avail).blocks, y_with, t.outcome_type)
        if stat is not None:
            cells.append(_rob.Cell(name, stat, _rob.changed_share(p.calendar, cc)))
    r3 = _rob.r3_sensitivity(t0, cells, side) if has_t else None
    # R4: separability from the domain's baselines.
    if B is None:
        r4 = _rob.CheckResult("R4", False, "not_computable", {"reason": "the plan declares no baselines"})
    else:
        r4 = _rob.r4_separability(_season.baseline_r2(p.calendar, B))
    return _rob.robustness(r1=r1, r2=r2, r3=r3, r4=r4), {"placebo_skipped_no_blocks": skipped}


def _prepare(tests: Sequence[TestDefinition], dates: pd.DatetimeIndex, lock: FamilyLock,
             run: DomainRun) -> List[_Prepared]:
    ids = [t.test_id for t in tests]
    if len(set(ids)) != len(ids):
        raise PipelineError("duplicate test ids in one run")
    prepared = []
    for t in tests:  # step 1: every calendar before anything else
        cal = _evaluate(t.calendar, dates, t.test_id)
        prepared.append(_Prepared(t, cal, calendar_hash(cal)))
    try:  # step 1a
        lock.check_against_rules([{"test_id": p.test.test_id, "calendar_hash": p.cal_hash,
                                   "use_parents": list(p.test.use_parents)} for p in prepared])
    except FamilyError as exc:
        raise PipelineError(str(exc)) from exc
    for p in prepared:
        p.eligibility = lock.eligibility(p.test.test_id, run.vintage,
                                         first_look_calendars=run.first_look_calendars)
        a = p.eligibility.a_test
        p.a_test = float(a) if a is not None else _a_test_open(lock, p.test.test_id)
    return prepared


def _gate(p: _Prepared, dates: pd.DatetimeIndex, confirm: np.ndarray, grade: str, run: DomainRun) -> GateResult:
    t = p.test
    spec = GateSpec(test_id=t.test_id, side=t.side, outcome_type=t.outcome_type, a_test=p.a_test,
                    merge_gap=t.merge_gap, guard_bars=t.guard_bars, sesoi=t.sesoi, base_rate=t.base_rate,
                    noise_sd=t.noise_sd, level=int(t.level), encoded=bool(t.encoded), data_grade=grade,
                    national_chart_ok=t.national_chart_ok, plan_seed=run.plan_seed, power_reps=t.power_reps)
    return run_gate(p.calendar, dates, confirm, spec)


def _input_hash(p: _Prepared, dataset_sha: str, run: DomainRun) -> str:
    return _sha(canonical_bytes({
        "schema": RECORD_SCHEMA, "test": p.test.identity(), "calendar_hash": p.cal_hash,
        "gate_sha256": p.gate_record.sha256 if p.gate_record else None, "dataset_sha256": dataset_sha,
        "plan_sha256": run.plan_sha256, "plan_seed": str(run.plan_seed), "a_test": p.a_test,
        "eligibility": _clean(p.eligibility.as_dict()), "vintage": _clean(dict(run.vintage)),
    }))


def _compute(p: _Prepared, dates: pd.DatetimeIndex, y_raw: np.ndarray, B: Optional[np.ndarray],
             explore: np.ndarray, confirm: np.ndarray, confirm_open: bool, run: DomainRun) -> Dict[str, Any]:
    """Steps 3 to 6 of one test; no outcome statistic for an Untestable test."""
    t, g = p.test, p.gate
    side = t.side
    seed = run.plan_seed
    numbers: Dict[str, Any] = {"effect": None, "p": None, "bound": None, "robustness": None, "estimate": None}
    vin: Dict[str, Any] = {}
    rob_passed: Dict[str, bool] = {}
    if not g.untestable:
        finite = np.isfinite(y_raw)
        y_with = y_raw
        if t.outcome_type in ("continuous", "log_ratio") and B is not None:
            y_with = _season.remove_baselines(y_raw, B)
        y_with = np.where(finite, y_with, np.nan)
        avail_full = None if bool(finite.all()) else finite
        sd_exp = _design(p.calendar, dates, t, explore & finite)
        res_exp = _primary(sd_exp.blocks, y_with, t, side, seed)
        res_conf = None
        if confirm_open:
            sd_conf = _design(p.calendar, dates, t, confirm & finite)
            sd_full = _design(p.calendar, dates, t, avail_full)
            if (sd_conf.blocks.design_id != g.confirm["design_id"]
                    or sd_full.blocks.design_id != g.full["design_id"]):
                raise PipelineError(f"{t.test_id}: the test's blocks differ from the gate's "
                                    "(outcome bars missing?); run stopped (S-15)")
            res_conf = _primary(sd_conf.blocks, y_with, t, side, seed)
        else:
            sd_full = sd_exp  # explore rows only: descriptive numbers on the explore period
        res_full = _primary(sd_full.blocks, y_with, t, side, seed)
        opp = _opposite(side)
        res_opp = _primary(sd_full.blocks, y_with, t, opp, seed) if opp and res_full.n_used else None
        stat_without = _statistic(sd_full.blocks, np.where(finite, y_raw, np.nan), t.outcome_type)
        ex = _exclusion.exclusion(
            sd_full.blocks, y_with, outcome_type=t.outcome_type, side=side, sesoi=t.sesoi, grid=t.x_grid,
            a_test=p.a_test, thinning_rng=stream_rng(seed, t.test_id, "thinning"),
            signflip_seed=stream_seed(seed, t.test_id, "signflip"), n_thin=t.n_thin, n_draws=t.n_draws)
        rob, extra = _robustness(p, dates, y_with, avail_full, res_full, B, sd_full.season_linked, run)
        rob_passed = rob.passed()
        vin = dict(
            p_sup=res_conf.p_value if res_conf is not None and res_conf.n_used else None,
            p_opp=res_opp.p_value if confirm_open and res_opp is not None else None,
            p_ex=ex.p_exclusion if confirm_open else None,
            explore_same_sign=_same_sign(res_exp.statistic if res_exp.n_used else None, side,
                                         res_conf.statistic if res_conf is not None and res_conf.n_used else None),
            informative_at_sesoi=ex.informative_at_sesoi,
            k_eff=ex.k_eff,
            estimate_magnitude=_magnitude(res_conf, side, t.outcome_type),
            x95=ex.x95, x_strict=ex.x_strict, n_blocks=ex.n_used,
        )
        numbers = {
            "effect": {"scale": res_full.estimate_scale, "explore": _summary(res_exp),
                       "confirm": _summary(res_conf), "full": _summary(res_full),
                       "full_is_explore_only": not confirm_open},
            "p": _clean({
                "support_confirm": vin["p_sup"], "opposite_full": vin["p_opp"], "exclusion_full": vin["p_ex"],
                "descriptive": {"explore": res_exp.p_value, "available_period": res_full.p_value,
                                "opposite_available_period": None if res_opp is None else res_opp.p_value,
                                "exclusion_available_period": ex.p_exclusion},
            }),
            "bound": _clean(ex.to_dict()),
            "robustness": _clean({**rob.to_dict(), **extra}),
            "estimate": None,
        }
        if _finite(t0 := (res_full.statistic if res_full.n_used else None)) and stat_without is not None:
            numbers["estimate"] = {"with_baselines": float(t0), "without_baselines": float(stat_without)}
    per = run.vintage.get("confirm_period") if isinstance(run.vintage, Mapping) else None
    v = verdict(VerdictInput(
        level=int(t.level), eligibility=p.eligibility, side=side,
        can_support=g.can_support, can_limit=g.can_limit, all_blocks_dropped=g.all_blocks_dropped,
        untestable_reason=g.untestable_reason, direction_disputed=t.direction_disputed,
        robustness=rob_passed, source_published=t.source_published,
        confirm_start=per.get("start") if isinstance(per, Mapping) else None,
        sesoi=t.sesoi, support_underpowered=g.support_underpowered,
        p_support_at_sesoi=g.p_support_at_sesoi, known_channel=t.known_channel,
        reading_differs=t.reading_differs, source_name=t.source_name,
        project_extension=t.project_extension, tuned=t.tuned,
        pseudo_out_of_sample=run.pseudo_out_of_sample, control_not_detected=run.control_not_detected,
        **vin,
    ))
    return {"numbers": numbers, "verdict": v}


def _limitations(p: _Prepared, ds: Any, run: DomainRun, r4: Any) -> List[Dict[str, str]]:
    t, g = p.test, p.gate
    if t.rule is None:
        raise PipelineError(f"{t.test_id}: no rule; the limitations box is built from the rule file (ADR-007 6)")
    cal = {"duty_cycle": float(p.calendar.mean()), "episodes_confirm": int(g.confirm.get("n_used", 0))}
    rows = build_limitations(t.rule, plan=run.plan, dataset=ds.as_record(), calendar=cal,
                             gate=g.to_dict(), r4=r4, disputes=run.disputes)
    return [r.to_dict() for r in rows]


def _record(p: _Prepared, out: Dict[str, Any], ds: Any, run: DomainRun, confirm_open: bool,
            lock: FamilyLock) -> Dict[str, Any]:
    t, g = p.test, p.gate
    n = out["numbers"]
    r4 = (n["robustness"] or {}).get("R4")
    lrec = lock.test_record(t.test_id)
    rec: Dict[str, Any] = {
        # keys of schema validity-report-input/1 (validity/report.py)
        "id": record_id_for(t.test_id),
        "name": t.name,
        "domain": run.domain,
        "level": int(t.level),
        "entry": t.entry,
        "outcome": {"market": t.market, "currency": t.currency},
        "justified": bool(t.justified),
        "verdict": out["verdict"].to_dict(),
        # the numbers (ADR-007 5.6 as amended by ADR-008)
        "schema": RECORD_SCHEMA,
        "test_id": t.test_id,
        "batch": lrec["batch"],
        "principle": {"id": t.rule_id, "version": t.version, "lineage_id": lrec["lineage_id"],
                      "use_parents": lrec["use_parents"]},
        "variant": {"id": t.variant},
        "dataset": ds.as_record(),
        "calendar": {"sha256": p.cal_hash, "duty_cycle": float(p.calendar.mean()), "n_bars": int(len(p.calendar))},
        "gate": {**g.to_dict(), "file": f"gates/{p.gate_record.path.name}", "file_sha256": p.gate_record.sha256},
        "eligibility": p.eligibility.as_dict(),
        "threshold": {k: lrec[k] for k in ("vintage_id", "n_b", "alpha_b", "a_test", "seal_bundle_sha256",
                                           "lock_position")},
        "a_test_used": p.a_test,
        "confirm_open": bool(confirm_open),
        "effect": n["effect"],
        "p": n["p"],
        "bound": n["bound"],
        "robustness": n["robustness"],
        "limitations": _limitations(p, ds, run, r4),
        "examined": {"primary": 1, "sensitivity": len(t.sensitivity), "placebo_kinds": list(t.placebo_kinds)},
        "input_sha256": p.input_sha256,
    }
    if n["estimate"] is not None:
        rec["estimate"] = n["estimate"]
    return _clean(rec)


def _load_previous(previous: Optional[PathLike]) -> Tuple[Optional[Dict[str, Any]], Dict[str, Dict[str, Any]]]:
    if previous is None:
        return None, {}
    data = json.loads(Path(previous).read_text(encoding="utf-8"))
    return data, {r["test_id"]: r for r in data.get("records", []) if "test_id" in r}


def _reusable_batches(lock: FamilyLock, prev: Optional[Dict[str, Any]]) -> set:
    """Closed batches whose results the lock recorded; the stored bytes must match (3.4)."""
    ok: set = set()
    if prev is None:
        return ok
    for b in lock.closed_batches():
        try:
            lock.verify_batch_results(b, batch_results_bytes(prev, b))
        except FamilyError as exc:
            if "no recorded results" in str(exc):
                continue
            raise ReproductionError(f"batch {b}: stored results differ from the lock: {exc}") from exc
        ok.add(b)
    return ok


def run_domain(
    adapter: Any,
    run: DomainRun,
    tests: Sequence[TestDefinition],
    lock: FamilyLock,
    run_dir: PathLike,
    *,
    handle: Optional[ConfirmHandle] = None,
    provisional: bool = True,
    repo_root: Optional[PathLike] = None,
    sealer: Optional[Callable[[bool], Any]] = None,
    previous: Optional[PathLike] = None,
    write: bool = True,
) -> Dict[str, Any]:
    """Run every test of one domain through the pipeline; return (and write) the results.

    Args:
        adapter: A domain adapter (core/domains/base.py), read only through
            sealbundle.guarded() with ``handle``.
        run: The domain plan's fixed inputs.
        tests: The registered tests; the lock must hold each with the same
            calendar hash and use: parents.
        lock: The domain's family lock.
        run_dir: Where ``gates/``, ``gate.json`` and ``results.json`` go.
        handle: From sealbundle.issue_confirm_handle(); None means explore
            rows only and a provisional result.
        provisional: True for a provisional run (never with a handle).
        repo_root: The repository the SealedRun checks.
        sealer: ``sealer(provisional)`` returns a SealedRun-like context manager
            with ``finish()``; default stats.seal.SealedRun(repo_root, ...).
        previous: An earlier results file of the domain (reuse and the
            reproduction check).
        write: Write ``results.json`` into run_dir.
    """
    if not isinstance(provisional, bool):
        raise TypeError("provisional must be a bool")
    if getattr(adapter, "domain", None) != run.domain:
        raise PipelineError(f"adapter domain {getattr(adapter, 'domain', None)!r} is not {run.domain!r}")
    if handle is not None:
        if provisional:
            raise PipelineError("a provisional run never takes a confirm handle")
        if not handle_is_valid(handle, run.domain):
            raise PipelineError("the confirm handle was not issued for this domain")
        if handle.vintage_id != run.vintage.get("id"):
            raise PipelineError(f"the handle is for vintage {handle.vintage_id}, the run for {run.vintage.get('id')}")
    out_dir = Path(run_dir)
    make = sealer or (lambda prov: SealedRun(repo_root, provisional=prov))
    prev, prev_records = _load_previous(previous)

    with make(provisional) as sealed:
        g_adapter = guarded(adapter, handle)
        confirm_open = g_adapter.confirm_open
        ds = g_adapter.dataset()
        dates = _dates(g_adapter.grid())
        per = g_adapter.periods()
        explore = _mask_between(dates, per.explore)
        confirm = _mask_between(dates, per.confirm)

        prepared = _prepare(tests, dates, lock, run)
        if handle is not None:
            outside = [p.test.test_id for p in prepared
                       if p.eligibility.row != "control" and p.test.test_id not in handle.test_ids]
            if outside:
                raise PipelineError(f"tests outside the handle's batch: {outside}")
        B = None
        if run.baselines is not None:  # outcome-free
            B = np.asarray(run.baselines(dates), dtype=float)
            if B.ndim == 1:
                B = B[:, None]
            if B.shape[0] != len(dates) or not np.isfinite(B).all():
                raise PipelineError("baselines must be finite, one row per grid bar")

        gate_index: Dict[str, Any] = {}
        for p in prepared:  # step 2
            p.gate = _gate(p, dates, confirm, ds.grade, run)
            rel = f"gates/{record_id_for(p.test.test_id)}.json"
            p.gate_record = write_gate(out_dir / rel, p.gate.to_dict())
            gate_index[p.test.test_id] = {"path": rel, "sha256": p.gate_record.sha256,
                                          "gate_hash": p.gate.gate_hash}
        domain_gate = write_gate(out_dir / "gate.json", _clean({
            "schema": DOMAIN_GATE_SCHEMA, "domain": run.domain, "plan_sha256": run.plan_sha256,
            "dataset_sha256": ds.sha256, "vintage": dict(run.vintage), "tests": gate_index}))
        for p in prepared:
            p.input_sha256 = _input_hash(p, ds.sha256, run)

        reuse = _reusable_batches(lock, prev)
        todo = [p for p in prepared
                if not (lock.test_record(p.test.test_id)["batch"] in reuse and p.test.test_id in prev_records)]
        y_by_outcome: Dict[str, np.ndarray] = {}
        if any(not p.gate.untestable for p in todo):
            raw = g_adapter.outcomes(domain_gate)  # step 2b: only now, after every gate file
            for p in todo:
                name = p.test.outcome
                if name in y_by_outcome or p.gate.untestable:
                    continue
                if not isinstance(raw, Mapping) or name not in raw:
                    raise PipelineError(f"the adapter returned no outcome {name!r}")
                v = np.asarray(raw[name], dtype=float).ravel()
                if len(v) > len(dates):
                    raise PipelineError(f"outcome {name!r} is longer than the grid")
                y = np.full(len(dates), np.nan)
                y[:len(v)] = v
                if not confirm_open:
                    y[~explore] = np.nan
                y_by_outcome[name] = y

        records = []
        for p in prepared:  # steps 3 to 8
            tid = p.test.test_id
            if p not in todo:
                old = prev_records[tid]
                if old.get("input_sha256") != p.input_sha256:
                    raise ReproductionError(f"{tid}: inputs changed for a closed batch whose results are recorded")
                records.append(old)
                continue
            y = y_by_outcome.get(p.test.outcome, np.full(len(dates), np.nan))
            rec = _record(p, _compute(p, dates, y, B, explore, confirm, confirm_open, run), ds, run,
                          confirm_open, lock)
            old = prev_records.get(tid)
            if old is not None and old.get("input_sha256") == p.input_sha256 \
                    and canonical_bytes(old) != canonical_bytes(rec):
                raise ReproductionError(f"{tid}: unchanged inputs did not reproduce the stored record; run stopped")
            records.append(rec)
        records.sort(key=lambda r: r["test_id"])
        stamp = sealed.finish()

    results: Dict[str, Any] = {
        "schema": REPORT_SCHEMA,
        "pipeline": PIPELINE_SCHEMA,
        "provisional": bool(provisional or not confirm_open),
        "plan": {"sha256": run.plan_sha256},
        "data": {"sha256": ds.sha256},
        "domain": run.domain,
        "vintage": dict(run.vintage),
        "gate": {"path": "gate.json", "sha256": domain_gate.sha256},
        "confirm": handle.footer() if confirm_open else None,
        "family": {"domains": int(run.domains_in_run_set)},
        "sampling_frame": {k: int(run.sampling_frame.get(k, 0)) for k in ("not_encodable", "not_sourced", "untestable")},
        "records": records,
    }
    results = _clean(stamp_results(results, stamp))
    if write:
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "results.json").write_text(json.dumps(results, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return results
