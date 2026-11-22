"""ADR-008 WP-98: whole-pipeline calibration and the calibration certificate.

Every case of ADR-008 sections 1.3, 2.4, 3.6, 4.4 (power), 5, 6.3, 7.3 and 8
runs here through the REAL pipeline: ``core/validity/pipeline.py``
``run_domain`` on a simulated domain adapter, with a confirm handle, a closed
family lock, the gate, the block test, exclusion, robustness R1 to R4 and the
verdict function. Nothing statistical is re-implemented: a replication is one
``run_domain`` call and every rate is read from its result records. Only the
cases that document an OLD loophole (B5, X8, Z4) call the old functions, by
definition, through the runners of the stats test files.

Outcome generators (tests/simulators.py, WP-84): Gaussian, Student-t(3),
lognormal, exponential, 98%-zero bars, GARCH, volatility regimes, AR(1),
drift (A2), rare Poisson events (0.1, 0.5 and 2 per active window),
Neyman-Scott clustered events with a doubling background, clustered GARCH
flags, drought-year flags, yearly rainfall with an ENSO driver and an epoch
wave, seasonal daily outcomes and events, a nodal wave, a festival-only effect
and monthly averages of a daily random walk. Calendars: periodic (short and
long gaps, 12 and 18 confirm episodes), balance-edge calendars with 8, 12 and
20 blocks, real Mercury retrograde, Venus combust, Moon-nakshatra group, tithi
group, eclipse window, Sun in Ashwini and Sun in Aries on the 1968 to 1998
daily grid, a new-moon-like single-day calendar (A2), and real Rahu, Jupiter
and Saturn in-sign calendars on yearly grids.

How it runs (``make calibrate``)::

    python -m tests.test_validity_calibration run [--full] [--workers N]
        [--work DIR] [--only SID,...] [--full-cells SID,...] [--write]

Replications are split into job files; worker PROCESSES (no thread, G-13)
claim them by an atomic rename, so an interrupted run resumes where it
stopped. ``--write`` aggregates every finished job, adds the property cases
and writes ``studies/validity/calibration/certificate.json`` through
``core/validity/calibration.py``, tied to the git blob hashes of
``core/stats``, ``core/validity``, ``core/domains``, ``tests/simulators.py``
and to the environment lock hash.

A cell that ran fewer replications than ADR-008 asks (10,000 per-test, 2,000
families, 1,000 power) is written with its true count, the fast mark
(observed rate at or below 0.085, ADR-008 1.3) and a note. check_certificate()
refuses such a cell, so ``begin_confirm`` refuses the outcome types that need
it until the full run is done. A failed cell is written as failed; no
threshold is relaxed here.

Speed without changing a number: the gate and every block design depend on the
calendar only (they are built before any outcome is read), so a worker
memoises ``pipeline.run_gate`` and ``pipeline._design`` per calendar;
``test_cached_pipeline_is_byte_identical`` proves the records equal those of
the uncached pipeline byte for byte. The plan seed is fixed per scenario, as
it is fixed per real domain; outcomes vary per replication.

pytest runs the fast checks; set ASTRO_CALIBRATE_FULL=1 for the checks that
need the full certificate. Past data only; nothing here forecasts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import tempfile
import threading
import time
import traceback
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
import pytest
import yaml
from scipy.stats import beta as _beta

from tests import simulators as sim
from vedic_astrology_core.domains.base import DatasetSpec, DomainAdapter, Periods
from vedic_astrology_core.domains.simulated import simulated_grades, simulated_registers
from vedic_astrology_core.rules.schema import Rule
from vedic_astrology_core.stats import blocks as B
from vedic_astrology_core.stats import exclusion as X
from vedic_astrology_core.stats import season as S
from vedic_astrology_core.validity import calibration as cal
from vedic_astrology_core.validity import family as F
from vedic_astrology_core.validity import gate as G
from vedic_astrology_core.validity import pipeline as P
from vedic_astrology_core.validity import sealbundle as SB

ROOT = Path(__file__).resolve().parents[1]
FULL = os.environ.get("ASTRO_CALIBRATE_FULL") == "1"
BASE_SEED = 20261122
FAST_REPS = 400
FAST_RATE = 0.085  # ADR-008 1.3 fast mark: observed rate over 400 replications
ALPHA = 0.05
DETREND_WINDOW = 31  # bars; the plan value of the A2 runs (daily grids)
CERTIFICATE = ROOT / cal.DEFAULT_CERTIFICATE_PATH
MANDALA = ROOT / "rules/mundane/practitioner/bs32_agni_mandala_earthquake.yaml"
DOMAIN = "simulated"
SEAL_HASH = "ab" * 32
PLAN_HASH = "cd" * 32

MONTHLY_START = "1850-01-01"
YEARLY_BAR_START = 1700
DAILY_GRID = sim.DAILY_GRID  # 1968-01-01 .. 1998-12-31
DAILY_PAD = ("1955-01-01", "2011-12-31")  # day-offset placebos reach 3,650 days
YEARLY_GRID = sim.YEARLY_GRID  # 1871 .. 2016
YEARLY_PAD = (1580, 2120)  # whole-year placebos reach 100 years
#: Z6 runs on a longer yearly grid: on 1871-2016 every Rahu-in-sign calendar has fewer
#: than 8 episodes and is Untestable, which would pass Z6 without testing it.
Z6_GRID = (1700, 2016)
NEW_MOON_PERIOD = 29.530589
DAILY_DRAWS = 9_999

#: Continuous SESOI in noise standard deviations; ratio SESOI as in ADR-008 X3.
SESOI_SHIFT = 0.5
SESOI_RATIO = 2.0
X_GRID_SHIFT = tuple(np.round(np.linspace(0.02, 4.0, 200), 4).tolist())
X_GRID_RATIO = tuple(np.round(np.linspace(1.02, 12.0, 300), 4).tolist())
#: Festival-day effect (7.3), noise standard deviations.
FESTIVAL_EFFECT = 0.8
FESTIVAL_MONTHS = (3, 10, 11)


# ===================================================================== rule
@lru_cache(maxsize=1)
def calibration_rule() -> Rule:
    """A registered rule for the limitations box (the record needs one; no number reads it)."""
    doc = yaml.safe_load(MANDALA.read_text(encoding="utf-8"))
    doc.update(
        reading={"kind": "concurrent"},
        operationalisation=[
            {"choice": "day_convention", "value": "utc_day", "fixed_by": "project", "alternatives": ["local_day"]},
            {"choice": "place", "value": "Greenwich", "fixed_by": "project", "alternatives": ["Delhi"]},
            {"choice": "horizon", "value": 0, "fixed_by": "text"},
        ],
        tests=[{"domain": DOMAIN, "outcome": "value", "direction": "either", "project_extension": True}],
    )
    return Rule.model_validate(doc)


class NoSeal:
    """Stands in for SealedRun: calibration runs on a working tree, not a sealed commit.

    The seal stamp (environment, files read) enters no number the certificate
    measures; the pipeline still opens and finishes it once per run.
    """

    def __init__(self, provisional: bool):
        self.provisional = provisional

    def __enter__(self):
        return self

    def finish(self, engine=None):
        return {"provisional": self.provisional, "commit": "calibration", "dirty": False,
                "problems": [], "files_read": [], "threads_started": 0}

    def __exit__(self, *exc):
        return False


# ================================================================ calendars
def _memo_calendar(fn: Callable[[pd.DatetimeIndex], np.ndarray]) -> Callable[[Any], np.ndarray]:
    """Cache a calendar function per instant vector (placebo skies repeat every replication)."""
    cache: Dict[bytes, np.ndarray] = {}

    def wrapped(instants):
        idx = pd.DatetimeIndex(instants)
        key = hashlib.sha1(np.asarray(idx.asi8).tobytes()).digest()
        hit = cache.get(key)
        if hit is None:
            hit = np.asarray(fn(idx), dtype=bool)
            cache[key] = hit
        return hit.copy()

    return wrapped


def monthly_dates(n: int) -> pd.DatetimeIndex:
    return pd.date_range(MONTHLY_START, periods=int(n), freq="MS")


def yearly_bar_dates(n: int) -> pd.DatetimeIndex:
    return pd.DatetimeIndex([pd.Timestamp(YEARLY_BAR_START + i, 6, 1) for i in range(int(n))])


def bar_calendar(mask: np.ndarray, dates: pd.DatetimeIndex, unit: str) -> Callable:
    """A calendar given bar by bar on a monthly or yearly grid; off-grid instants are inactive."""
    m = np.asarray(mask, dtype=bool)
    y0, m0 = int(dates[0].year), int(dates[0].month)

    def fn(idx: pd.DatetimeIndex) -> np.ndarray:
        if unit == "month":
            i = (np.asarray(idx.year) - y0) * 12 + (np.asarray(idx.month) - m0)
        else:
            i = np.asarray(idx.year) - y0
        out = np.zeros(len(idx), dtype=bool)
        ok = (i >= 0) & (i < len(m))
        out[ok] = m[i[ok]]
        return out

    return _memo_calendar(fn)


def new_moon_like(days: np.ndarray, start: int = 3) -> np.ndarray:
    """Single-day episodes every 29.53 days (A2), defined for any day number."""
    d = np.asarray(days, dtype=float)
    k = np.round((d - start) / NEW_MOON_PERIOD)
    return np.round(start + k * NEW_MOON_PERIOD) == d


@lru_cache(maxsize=1)
def daily_frame() -> pd.DataFrame:
    """Real daily calendars over the padded range, plus the new-moon-like calendar."""
    f = sim.daily_calendars(*DAILY_PAD)
    days = (f.index - pd.Timestamp(DAILY_GRID[0])).days.to_numpy()
    f["new_moon_like"] = new_moon_like(days)
    return f


@lru_cache(maxsize=1)
def orb_frame() -> pd.Series:
    """Mercury within 5 degrees of Venus (an orb conjunction, section 5 proof test)."""
    from vedic_astrology_core.markets.align import sample_instants
    from vedic_astrology_core.markets.features import indicator_frame

    dates = pd.date_range(*DAILY_PAD, freq="D")
    f = indicator_frame(sample_instants(dates, "12:00", "UTC"), ["MERCURY", "VENUS"])
    sep = np.abs((f["MERCURY_lon"].to_numpy(float) - f["VENUS_lon"].to_numpy(float) + 180.0) % 360.0 - 180.0)
    return pd.Series(sep <= 5.0, index=dates)


def daily_calendar(name: str) -> Callable:
    """Look-up of a real daily calendar at any instant inside the padded range."""
    if name == "mercury_venus_orb":
        s = orb_frame()
        col, origin = s.to_numpy(dtype=bool), s.index[0]
    else:
        f = daily_frame()
        col, origin = f[name].to_numpy(dtype=bool), f.index[0]

    def fn(idx: pd.DatetimeIndex) -> np.ndarray:
        i = np.asarray((idx.normalize() - origin).days)
        if (i < 0).any() or (i >= len(col)).any():
            raise ValueError(f"{name}: instant outside the padded daily range {DAILY_PAD}")
        return col[i]

    return _memo_calendar(fn)


@lru_cache(maxsize=1)
def yearly_frame() -> pd.DataFrame:
    return sim.yearly_calendars(*YEARLY_PAD)


#: Real yearly calendars with more episodes than one sign gives (Z3 on 1871-2016).
COMPOSITE_YEARLY = {"jupiter_in_water": ("jupiter", ("cancer", "scorpio", "pisces")),
                    "saturn_in_fire": ("saturn", ("aries", "leo", "sagittarius")),
                    "rahu_in_dual": ("rahu", ("gemini", "virgo", "sagittarius", "pisces"))}


def yearly_calendar(name: str) -> Callable:
    """Look-up of a real yearly calendar (1 June, noon UTC) by year; "every_k": year % k == 0."""
    if name.startswith("every_"):
        k = int(name.split("_")[1])
        return _memo_calendar(lambda idx: np.asarray(idx.year) % k == 0)
    f = yearly_frame()
    if name in COMPOSITE_YEARLY:
        body, signs = COMPOSITE_YEARLY[name]
        col = np.any([f[f"{body}_in_{s}"].to_numpy(dtype=bool) for s in signs], axis=0)
    else:
        col = f[name].to_numpy(dtype=bool)
    y0 = int(f.index[0])

    def fn(idx: pd.DatetimeIndex) -> np.ndarray:
        i = np.asarray(idx.year) - y0
        if (i < 0).any() or (i >= len(col)).any():
            raise ValueError(f"{name}: year outside the padded yearly range {YEARLY_PAD}")
        return col[i]

    return _memo_calendar(fn)


def daily_dates() -> pd.DatetimeIndex:
    return pd.date_range(DAILY_GRID[0], DAILY_GRID[1], freq="D")


def yearly_dates(first: int = YEARLY_GRID[0], last: int = YEARLY_GRID[1]) -> pd.DatetimeIndex:
    return pd.DatetimeIndex([pd.Timestamp(int(y), 6, 1) for y in range(int(first), int(last) + 1)])


def explore_cut(mask: np.ndarray, n_explore: int) -> int:
    """Index of the first confirm bar: the midpoint of the gap after episode n_explore.

    The confirm blocks keep their own half-gap (ADR-008 1.1 item 2).
    """
    runs = sim.episode_runs(mask)
    if n_explore < 1 or n_explore >= len(runs):
        raise ValueError("need at least one explore and one confirm episode")
    return int((runs[n_explore - 1][1] + runs[n_explore][0]) // 2)


# ================================================================ scenarios
@dataclass(frozen=True)
class Output:
    """One certificate cell fed by a scenario: case id, cell name, metric, test index.

    Metrics: "rej" (confirm-period primary p at or below 0.05), "S", "C", "E",
    "excluded" (exclusion p at or below 0.05 with the minimum-information
    rule met), "r2" (R2 passes), "r4" (R4 passes), "below:<v>" (X95 bounded
    and below v), "any_S" and "any_C" (any test of the family).
    """

    case_id: str
    cell: str
    metric: str
    test: int = 0


@dataclass(frozen=True)
class Scenario:
    """One simulated domain run through `run_domain`, replicated.

    grid: "monthly" or "yearbars" (bar calendars), "daily" (1968-1998),
        "yearly" (1871-2016), "yearly_long" (1771-2016) or "yearly_z6" (1700-2016).
    calendars: one test per key; an effect is planted on the first one. Keys:
        "per:a/g/k[/n_explore]" periodic, k episodes after the cut;
        "bal:b/k/na" balance calendar with k episodes; "cyc:a/p/off" active
        when (bar - off) mod p < a; "daily:<name>"; "yearly:<name>".
    gen: outcome generator (see `generate`); effect: planted shift
        (continuous) or ratio (log_ratio, events, flags); "mde" plants twice
        the gate's minimal detectable effect (W1).
    """

    sid: str
    grid: str
    calendars: Tuple[str, ...]
    gen: str
    outcome_type: str
    outputs: Tuple[Output, ...]
    effect: Any = None
    sesoi: Optional[float] = None
    baselines: str = "trend"
    base_rate: Optional[float] = None
    noise_sd: Optional[float] = 1.0
    guard_bars: int = 0
    uneven: bool = False
    missing_every: int = 0
    explore_share: float = 0.4
    n_bars: int = 0
    kind: str = "domain"  # domain | clone
    n_draws: int = 0  # Monte Carlo sign flips; 0: the pipeline default (99,999)
    replications: int = 10_000
    chunk: int = 50

    @property
    def x_grid(self) -> Tuple[float, ...]:
        return X_GRID_SHIFT if self.outcome_type == "continuous" else X_GRID_RATIO


def _grid_dates(sc: Scenario, n: int) -> pd.DatetimeIndex:
    if sc.grid == "monthly":
        return monthly_dates(n)
    if sc.grid == "yearbars":
        return yearly_bar_dates(n)
    if sc.grid == "daily":
        return daily_dates()
    if sc.grid == "yearly":
        return yearly_dates()
    if sc.grid == "yearly_long":
        return yearly_dates(1771, YEARLY_GRID[1])
    if sc.grid == "yearly_z6":
        return yearly_dates(*Z6_GRID)
    raise ValueError(f"unknown grid {sc.grid!r}")


def _bar_mask(key: str, n_bars: int) -> Tuple[np.ndarray, Optional[int]]:
    """Mask of a bar-calendar key and its explore cut (None: cut by share)."""
    kind, spec = key.split(":", 1)
    parts = spec.split("/")
    if kind == "per":
        a, g, k = (int(x) for x in parts[:3])
        nexp = int(parts[3]) if len(parts) > 3 else 2
        m = sim.periodic_calendar(a, g, k + nexp)
        return m, explore_cut(m, nexp)
    if kind == "bal":
        b, k, na = float(parts[0]), int(parts[1]), int(parts[2])
        m = sim.balance_calendar(b, k, na)
        return m, explore_cut(m, 2)
    if kind == "cyc":
        a, p, off = (int(x) for x in parts)
        i = np.arange(int(n_bars))
        return ((i >= off) & ((i - off) % p < a)), None
    raise ValueError(f"not a bar calendar: {key!r}")


def layout(sc: Scenario) -> Tuple[pd.DatetimeIndex, List[Callable], List[np.ndarray], Optional[int], int]:
    """Grid dates, calendar functions, calendars on the grid, explore cut (None: by share), bars."""
    if sc.grid in ("monthly", "yearbars"):
        first, cut = _bar_mask(sc.calendars[0], sc.n_bars)
        n = sc.n_bars or len(first)
        masks = [first] + [_bar_mask(k, n)[0] for k in sc.calendars[1:]]
        if any(len(m) != n for m in masks):
            raise ValueError(f"{sc.sid}: bar calendars must share the grid length")
        dates = _grid_dates(sc, n)
        unit = "month" if sc.grid == "monthly" else "year"
        fns = [bar_calendar(m, dates, unit) for m in masks]
    else:
        dates = _grid_dates(sc, 0)
        n, cut = len(dates), None
        fns = []
        for key in sc.calendars:
            kind, name = key.split(":", 1)
            fns.append(daily_calendar(name) if kind == "daily" else yearly_calendar(name))
    masks = [np.asarray(fn(dates), dtype=bool) for fn in fns]
    return dates, fns, masks, cut, n


class Ctx:
    """Everything outcome-free about a scenario, built once per worker process."""

    def __init__(self, sc: Scenario, run_root: Path, *, plan_seed: Optional[int] = None,
                 outcomes: Optional[Sequence[str]] = None):
        self.sc = sc
        self.plan_seed = int(cal.derive_seed(BASE_SEED, sc.sid, "plan") if plan_seed is None else plan_seed)
        self.dates, self.fns, self.masks, cut, n = layout(sc)
        self.outcome_names = list(outcomes) if outcomes is not None else ["value"] * len(self.fns)
        self.n = n
        self.cal0 = self.masks[0]
        self.cut = int(cut if cut is not None else round(sc.explore_share * n))
        self.missing = np.zeros(n, dtype=bool)
        if sc.missing_every:
            self.missing[np.arange(sc.missing_every // 2, n, sc.missing_every)] = True
        d = self.dates
        self.periods = Periods(explore=(d[0].date(), d[self.cut - 1].date()), confirm=(d[self.cut].date(), d[-1].date()))
        self.vintage = {"id": f"calib_{sc.sid}", "seen": False,
                        "confirm_period": {"start": d[self.cut].date().isoformat(), "end": d[-1].date().isoformat()}}
        self.tests = [self._definition(j, fn) for j, fn in enumerate(self.fns)]
        self.lock = F.FamilyLock(None, DOMAIN)
        for t, m in zip(self.tests, self.masks):
            self.lock.register(rule_id=t.rule_id, version=1, outcome=t.outcome, calendar_hash=F.calendar_hash(m))
        self.lock.close_batch(vintage=self.vintage, seal_bundle_sha256=SEAL_HASH)
        self.token = f"calibration-{sc.sid}-{os.getpid()}-{id(self)}"
        self.handle = SB.ConfirmHandle(
            domain=DOMAIN, batch=1, bundle_sha256=SEAL_HASH, bundle_path="seals/calibration.json",
            ots_path="seals/calibration.json.ots", block_height=1, vintage_id=self.vintage["id"],
            period=(self.vintage["confirm_period"]["start"], self.vintage["confirm_period"]["end"]),
            test_ids=tuple(t.test_id for t in self.tests), ledger_commit="calibration", token=self.token)
        SB._ISSUED[self.token] = self.handle
        self.run_dir = Path(run_root) / re.sub(r"[^A-Za-z0-9_.-]+", "_", sc.sid)
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.festival = None
        if sc.baselines == "trend+festival" or sc.gen == "festival":
            self.festival = (self.cal0 & np.isin(d.month, FESTIVAL_MONTHS)).astype(float)
        self.rahu_lon = None
        if sc.gen == "nodal":
            self.rahu_lon = yearly_frame().loc[d.year, "rahu_longitude"].to_numpy(dtype=float)
        self.effect = sc.effect
        if sc.effect == "mde":
            self.mde = minimal_detectable_effect(self)
            self.effect = (2.0 * self.mde if sc.outcome_type == "continuous" else 1.0 + 2.0 * (self.mde - 1.0))
            if sc.outcome_type == "flags":
                self.effect = min(self.effect, 0.95 / float(sc.base_rate))

    def _definition(self, j: int, fn: Callable) -> P.TestDefinition:
        sc = self.sc
        return P.TestDefinition(
            rule_id=f"calibration.t{j:02d}", version=1, outcome=self.outcome_names[j], calendar=fn, side="greater",
            outcome_type=sc.outcome_type, x_grid=list(sc.x_grid), name=f"Calibration test {j}", level=2,
            rule=calibration_rule(), sesoi=sc.sesoi, base_rate=sc.base_rate,
            noise_sd=sc.noise_sd if sc.outcome_type in ("continuous", "log_ratio") else None,
            source_published="1600", merge_gap=0, guard_bars=sc.guard_bars,
            n_draws=sc.n_draws or B.DEFAULT_DRAWS)

    def baselines(self, extra: Dict[str, np.ndarray]) -> Callable:
        """The plan's baselines on the grid (outcome-free; extra holds per-replication drivers)."""
        cols = [(self.dates.year.to_numpy(float) + self.dates.day_of_year.to_numpy(float) / 366.0 - 1900.0) / 100.0]
        kinds = self.sc.baselines.split("+")
        if "festival" in kinds:
            cols.append(self.festival)
        if "nodal" in kinds:
            nb = S.nodal_baseline(self.dates.year.to_numpy())
            cols.extend(np.asarray(nb, dtype=float).T)
        if "enso" in kinds:
            cols.append(np.asarray(extra["enso"], dtype=float))
        mat = np.column_stack(cols)
        n = self.n

        def fn(d):
            if len(d) != n:
                raise ValueError("baselines are given on the grid only")
            return mat

        return fn

    def run_spec(self, extra: Dict[str, np.ndarray]) -> P.DomainRun:
        missing = {"value": (lambda d: self.missing.copy())} if self.missing.any() else {}
        return P.DomainRun(
            domain=DOMAIN, plan_seed=self.plan_seed, plan_sha256=PLAN_HASH, vintage=self.vintage,
            baselines=self.baselines(extra),
            plan={"domain": DOMAIN, "outcomes": [{"id": "value"}], "vintages": [self.vintage]},
            detrend_window=DETREND_WINDOW if S.detrend_required(self.dates) else None,
            missing_bars=missing)

    def close(self) -> None:
        SB._ISSUED.pop(self.token, None)


def minimal_detectable_effect(ctx: Ctx) -> float:
    """Smallest effect with gate power P(S) >= 0.8 on the confirm blocks (bisection, W1)."""
    sc = ctx.sc
    conf = np.zeros(ctx.n, dtype=bool)
    conf[ctx.cut:] = True
    design = S.control_design(ctx.cal0, ctx.dates, merge_gap=0, guard_bars=sc.guard_bars,
                              available=conf, side_seed=ctx.plan_seed).blocks
    a_test = F.a_test_for(F.alpha_for_batch(1), len(ctx.tests))

    def power(e: float) -> float:
        spec = G.GateSpec(test_id=ctx.tests[0].test_id, side="greater", outcome_type=sc.outcome_type,
                          a_test=a_test, merge_gap=0, guard_bars=sc.guard_bars, sesoi=float(e),
                          base_rate=sc.base_rate, noise_sd=sc.noise_sd, level=2, plan_seed=ctx.plan_seed,
                          power_reps=400)
        return float(G.power_at_sesoi(design, spec) or 0.0)

    ratio = sc.outcome_type != "continuous"
    lo, hi = (1.0001, 60.0) if ratio else (1e-4, 20.0)
    if sc.outcome_type == "flags":
        hi = 0.99 / float(sc.base_rate)
    if power(hi) < G.POWER_TARGET:
        raise ValueError(f"{sc.sid}: no detectable effect below {hi}")
    for _ in range(30):
        mid = math.sqrt(lo * hi) if ratio else 0.5 * (lo + hi)
        if power(mid) >= G.POWER_TARGET:
            hi = mid
        else:
            lo = mid
    return float(hi)


# ================================================================ generators
def _drift(n: int, rng: np.random.Generator) -> np.ndarray:
    t = np.arange(n, dtype=float)
    return rng.standard_normal(n) + 0.02 * t + np.cumsum(rng.normal(0.0, 0.05, n))


_CONT = {
    **{k: (lambda k: lambda n, rng: sim.continuous_bars(k, n, rng))(k) for k in sim.CONTINUOUS_KINDS},
    "garch": lambda n, rng: sim.garch11_normal(n, rng, **sim.B3_GARCH),
    "regimes": lambda n, rng: sim.regime_bars(n, rng),
    "ar1_0.1": lambda n, rng: sim.ar1(n, rng, 0.1),
    "ar1_0.3": lambda n, rng: sim.ar1(n, rng, 0.3),
    "drift": _drift,
}


def _shift(ctx: Ctx, rng: np.random.Generator):
    e = ctx.effect
    if e is None or e == 0:
        return None
    if ctx.sc.uneven:
        return sim.uneven_multiplier(ctx.cal0, e, rng, scale="shift")
    return float(e)


def _multiplier(ctx: Ctx, rng: np.random.Generator):
    e = ctx.effect
    if e is None or e == 1.0:
        return None
    if ctx.sc.uneven:
        return sim.uneven_multiplier(ctx.cal0, e, rng, scale="ratio")
    return sim.effect_multiplier(ctx.cal0, e)


def generate(ctx: Ctx, rng: np.random.Generator) -> Tuple[np.ndarray, Dict[str, np.ndarray]]:
    """One outcome series on the grid (effect planted in the bars) and per-replication drivers."""
    sc, n, c = ctx.sc, ctx.n, ctx.cal0
    head, *args = sc.gen.split(":")
    extra: Dict[str, np.ndarray] = {}
    if head in _CONT:
        y = _CONT[head](n, rng)
        if sc.outcome_type == "log_ratio":
            pos = np.abs(y) + 1e-3
            if ctx.effect not in (None, 1.0):
                pos = sim.plant_ratio(pos, c, ctx.effect)
            return np.log(pos), extra
        s = _shift(ctx, rng)
        return (y if s is None else sim.plant_shift(y, c, s)), extra
    if head == "poisson":  # poisson:<mean per active window>:<window>
        ev = sim.poisson_events(c, float(args[0]), int(args[1]), rng, _multiplier(ctx, rng))
        return ev.astype(float), extra
    if head == "ns":  # Neyman-Scott parents (the declustered mainshocks)
        out = sim.neyman_scott(n, rng, float(args[0]), multiplier=_multiplier(ctx, rng))
        return out["parents"].astype(float), extra
    if head == "season_ns":  # Z2: all events, rate x8 in four months, clustered
        m = sim.season_multiplier(ctx.dates)
        out = sim.neyman_scott(n, rng, float(args[0]), multiplier=m)
        return out["counts"].astype(float), extra
    if head == "garch_flags":
        f = sim.garch_flags(n, rng)
        if ctx.effect not in (None, 1.0):
            f = sim.plant_risk_ratio(f, c, ctx.effect, rng, sim.GARCH_FLAG_RATE)
        return f.astype(float), extra
    if head == "drought":
        f = sim.drought_flags(sim.yearly_rainfall(ctx.dates.year.to_numpy(), rng)["anomaly"])
        if ctx.effect not in (None, 1.0):
            f = sim.plant_risk_ratio(f, c, ctx.effect, rng, sim.DROUGHT_FLAG_RATE)
        return f.astype(float), extra
    if head == "rain":  # Z3: leave-year-out anomaly (D-06), ENSO as a baseline
        g = sim.yearly_rainfall(ctx.dates.year.to_numpy(), rng)
        extra["enso"] = g["enso"]
        a = S.leave_year_out_anomaly(g["anomaly"], ctx.dates.year.to_numpy(), by="year")
        s = _shift(ctx, rng)
        return (a if s is None else sim.plant_shift(a, c, s)), extra
    if head == "rain_drought":
        g = sim.yearly_rainfall(ctx.dates.year.to_numpy(), rng)
        extra["enso"] = g["enso"]
        return g["drought"].astype(float), extra
    if head == "seasonal":  # Z1: anomaly from a day-of-year mean without the tested year
        y = S.leave_year_out_anomaly(sim.seasonal_daily(ctx.dates, rng), ctx.dates, by="doy")
        return y, extra
    if head == "nodal":
        return sim.nodal_wave(ctx.rahu_lon, rng), extra
    if head == "festival":  # 7.3: the effect sits on festival days only
        return rng.standard_normal(n) + FESTIVAL_EFFECT * ctx.festival, extra
    if head == "monthly_avg":  # D-01: monthly averages of a daily random walk
        r = sim.monthly_average_returns(n // 12 + 2, rng).to_numpy()[:n]
        return r / (sim.DAILY_VOL * math.sqrt(261.0 / 12.0)), extra
    raise ValueError(f"unknown generator {sc.gen!r}")


class CalibDomain(DomainAdapter):
    """A simulated domain adapter on any grid; outcomes only through `outcomes()`."""

    domain = DOMAIN

    def __init__(self, ctx: Ctx, outcomes: Dict[str, np.ndarray], periods: Optional[Periods] = None):
        self._ctx = ctx
        self._out = {k: np.asarray(v, dtype=float) for k, v in outcomes.items()}
        self._periods = periods or ctx.periods
        h = hashlib.sha256()
        for k in sorted(self._out):
            h.update(k.encode())
            h.update(self._out[k].tobytes())
        self.sha256 = h.hexdigest()
        self.outcome_reads = 0
        index, licences = simulated_registers(self.sha256)
        super().__init__(index, licences, simulated_grades(self.sha256))

    def dataset_spec(self) -> DatasetSpec:
        d = self._ctx.dates
        return DatasetSpec(id="calibration", sha256=self.sha256, source_id="simulated",
                           span=(d[0].date().isoformat(), d[-1].date().isoformat()), n_units=len(d))

    def grid(self):
        return list(self._ctx.dates)

    def calendar_context(self):
        return {}

    def periods(self) -> Periods:
        return self._periods

    def _outcomes(self):
        self.outcome_reads += 1
        return {k: v.copy() for k, v in self._out.items()}

    def _controls(self):
        return {}


# ============================================================ outcome-free cache
_ORIGINAL = {"run_gate": P.run_gate, "_design": P._design}
_CACHE: Dict[str, Dict[Any, Any]] = {"gate": {}, "design": {}}


def _hb(a) -> bytes:
    arr = np.ascontiguousarray(np.asarray(a))
    return hashlib.sha1(arr.tobytes() + str(arr.dtype).encode() + str(arr.shape).encode()).digest()


def _cached_run_gate(calendar, dates, confirm, spec, *, available=None):
    key = (_hb(calendar), _hb(pd.DatetimeIndex(dates).asi8), _hb(confirm), repr(spec),
           None if available is None else _hb(available))
    hit = _CACHE["gate"].get(key)
    if hit is None:
        hit = _ORIGINAL["run_gate"](calendar, dates, confirm, spec, available=available)
        _CACHE["gate"][key] = hit
    return hit


def _cached_design(cal_, dates, t, available, plan_seed):
    key = (_hb(cal_), _hb(pd.DatetimeIndex(dates).asi8), repr(t.merge_gap), int(t.guard_bars),
           None if available is None else _hb(available), str(plan_seed))
    hit = _CACHE["design"].get(key)
    if hit is None:
        hit = _ORIGINAL["_design"](cal_, dates, t, available, plan_seed)
        _CACHE["design"][key] = hit
    return hit


def install_cache() -> None:
    """Memoise the outcome-free gate and block designs of the pipeline (same objects, same bytes)."""
    P.run_gate = _cached_run_gate
    P._design = _cached_design


def remove_cache() -> None:
    P.run_gate = _ORIGINAL["run_gate"]
    P._design = _ORIGINAL["_design"]
    clear_cache()


def clear_cache() -> None:
    for v in _CACHE.values():
        v.clear()


# ================================================================ replications
def outcome_rng(sid: str, i: int) -> np.random.Generator:
    return np.random.default_rng([cal.case_seed(BASE_SEED, sid, "", "outcome"), int(i)])


def run_once(ctx: Ctx, i: int) -> Tuple[Dict[str, Any], CalibDomain]:
    """Replication i of a scenario: one full `run_domain` with the confirm handle."""
    rng = outcome_rng(ctx.sc.sid, i)
    y, extra = generate(ctx, rng)
    y = np.asarray(y, dtype=float).copy()
    if ctx.missing.any():
        y[ctx.missing] = np.nan
    dom = CalibDomain(ctx, {"value": y})
    res = P.run_domain(dom, ctx.run_spec(extra), ctx.tests, ctx.lock, ctx.run_dir, handle=ctx.handle,
                       provisional=False, sealer=NoSeal, write=False)
    return res, dom


def summarise(rec: Dict[str, Any]) -> Dict[str, Any]:
    """The numbers one record gives the certificate."""
    v = rec["verdict"]
    p = rec.get("p") or {}
    b = rec.get("bound") or {}
    rob = rec.get("robustness") or {}
    g = rec["gate"]
    p_sup, p_ex = p.get("support_confirm"), p.get("exclusion_full")
    info, keff = b.get("informative_at_sesoi"), b.get("k_eff")
    excluded = bool(p_ex is not None and p_ex <= ALPHA and info is not None and keff is not None
                    and X.can_limit(keff, info, ALPHA))
    x95 = b.get("x95") or {}
    r2 = rob.get("R2") or {}
    eff = rec.get("effect") or {}
    b6 = True  # ADR-008 B6: the test reads the gate's blocks, side and count (S-15)
    for per in ("confirm", "full"):
        e, gg = eff.get(per), g.get(per)
        if e is not None:
            b6 &= (e["design_id"] == gg["design_id"] and e["n_used"] == gg["n_used"]
                   and e["alternative"] == gg["alternative"] == g["side"])
    pw = g.get("p_support_at_sesoi")
    w4 = v["code"] == "U" or not (pw is None or pw < G.POWER_TARGET) or "support_underpowered" in v["flags"]
    return {
        "code": v["code"], "rej": bool(p_sup is not None and p_sup <= ALPHA),
        "excluded": excluded, "x95": None if x95.get("unbounded", True) else x95.get("value"),
        "r2": bool(r2.get("passes")), "r2_tied": int(r2.get("n_tied") or 0),
        "r4": bool((rob.get("passed") or {}).get("R4")), "untestable": bool(g["untestable"]),
        "can_support": bool(g["can_support"]), "b6": bool(b6), "w4": bool(w4),
    }


def metric_value(metric: str, rows: List[Dict[str, Any]], test: int) -> bool:
    if metric == "any_S":
        return any(r["code"] == "S" for r in rows)
    if metric == "any_C":
        return any(r["code"] == "C" for r in rows)
    r = rows[test]
    if metric in ("S", "C", "E", "N", "U"):
        return r["code"] == metric
    if metric.startswith("below:"):
        return r["x95"] is not None and r["x95"] < float(metric.split(":", 1)[1])
    return bool(r[metric])


def run_domain_chunk(sc: Scenario, a: int, b: int, ctx: Ctx) -> Dict[str, Any]:
    counts: Dict[str, int] = {f"{o.case_id}|{o.cell}": 0 for o in sc.outputs}
    aux = {"b6_bad": 0, "w4_bad": 0, "untestable_first": 0, "r2_tied_reps": 0, "reps": 0}
    for i in range(a, b):
        res, _ = run_once(ctx, i)
        by_id = {r["test_id"]: r for r in res["records"]}
        rows = [summarise(by_id[t.test_id]) for t in ctx.tests]
        for o in sc.outputs:
            counts[f"{o.case_id}|{o.cell}"] += int(metric_value(o.metric, rows, o.test))
        aux["b6_bad"] += sum(not r["b6"] for r in rows)
        aux["w4_bad"] += sum(not r["w4"] for r in rows)
        aux["untestable_first"] += int(rows[0]["untestable"])
        aux["r2_tied_reps"] += int(rows[0]["r2_tied"] > 0)
        aux["reps"] += 1
    extra = {}
    if getattr(ctx, "effect", None) is not None and sc.effect == "mde":
        extra = {"mde": ctx.mde, "planted": ctx.effect}
    return {"counts": counts, "aux": aux, "extra": extra}


# ------------------------------------------------------------------ F3 and F4
CLONE_CALENDARS = tuple(
    f"yearly:{b}_in_{s.lower()}" for b in ("rahu", "jupiter", "saturn") for s in sim.SIGNS
) + tuple(f"yearly:every_{k}" for k in range(3, 10))
CLONE_V1 = {"id": "clone_v1", "seen": False, "confirm_period": {"start": "1901-01-01", "end": "1958-12-31"}}
CLONE_V2 = {"id": "clone_v2", "seen": False, "confirm_period": {"start": "1959-01-01", "end": "2016-12-31"}}


def _handle(ctx: Ctx, batch: int, vintage: Dict[str, Any], test_ids: Sequence[str], token: str) -> SB.ConfirmHandle:
    h = SB.ConfirmHandle(domain=DOMAIN, batch=batch, bundle_sha256=SEAL_HASH, bundle_path="seals/clone.json",
                         ots_path="seals/clone.json.ots", block_height=1, vintage_id=vintage["id"],
                         period=(vintage["confirm_period"]["start"], vintage["confirm_period"]["end"]),
                         test_ids=tuple(test_ids), ledger_commit="calibration", token=token)
    SB._ISSUED[token] = h
    return h


def clone_family(ctx: Ctx, i: int) -> Dict[str, int]:
    """One family of the S-04 clone attack (F3, F4) on real calendars, through the pipeline.

    43 null tests close batch 1 on vintage v1 (confirm 1901-1958; later years
    not yet observed, declared missing). After the confirm the adversary
    registers 17 copies of the test with the smallest support p: 5 renamed
    copies (same calendar), 6 variants of the same rule and 6 use: children.
    The accepted copies are run on the old vintage (no handle exists for
    them: a provisional run) and, for F4, confirmed on a fresh vintage v2
    (confirm 1959-2016) after batch 2 closes on it.
    """
    sc = ctx.sc
    rng = outcome_rng(sc.sid, i)
    y = rng.standard_normal(ctx.n)
    years = ctx.dates.year.to_numpy()
    lock = F.FamilyLock(None, DOMAIN)
    for t, m in zip(ctx.tests, ctx.masks):
        lock.register(rule_id=t.rule_id, version=1, outcome="value", calendar_hash=F.calendar_hash(m))
    lock.close_batch(vintage=CLONE_V1, seal_bundle_sha256=SEAL_HASH)
    d = ctx.dates
    per1 = Periods(explore=(d[0].date(), pd.Timestamp("1900-12-31").date()),
                   confirm=(pd.Timestamp("1901-01-01").date(), pd.Timestamp("1958-12-31").date()))
    y1 = np.where(years <= 1958, y, np.nan)
    later = years > 1958
    run1 = P.DomainRun(domain=DOMAIN, plan_seed=ctx.plan_seed, plan_sha256=PLAN_HASH, vintage=CLONE_V1,
                       baselines=ctx.baselines({}), plan={"domain": DOMAIN, "outcomes": [{"id": "value"}],
                                                          "vintages": [CLONE_V1, CLONE_V2]},
                       missing_bars={"value": lambda dd: later.copy()})
    tok = f"clone-{os.getpid()}-{i}"
    h1 = _handle(ctx, 1, CLONE_V1, [t.test_id for t in ctx.tests], tok + "-1")
    try:
        res1 = P.run_domain(CalibDomain(ctx, {"value": y1}, per1), run1, ctx.tests, lock, ctx.run_dir,
                            handle=h1, provisional=False, sealer=NoSeal, write=False)
    finally:
        SB._ISSUED.pop(h1.token, None)
    recs = {r["test_id"]: r for r in res1["records"]}
    false_s1 = any(r["verdict"]["code"] == "S" for r in recs.values())
    psup = [(recs[t.test_id]["p"]["support_confirm"] if recs[t.test_id].get("p") else None, j)
            for j, t in enumerate(ctx.tests)]
    psup = [(p, j) for p, j in psup if p is not None]
    w = min(psup)[1] if psup else 0
    win, wfn, wmask = ctx.tests[w], ctx.fns[w], ctx.masks[w]
    whash = F.calendar_hash(wmask)
    clones: List[P.TestDefinition] = []
    refused = 0

    def attempt(rule_id: str, variant: str, fn: Callable, use_parents=()):
        nonlocal refused
        m = np.asarray(fn(d), dtype=bool)
        try:
            lock.register(rule_id=rule_id, version=1, outcome="value", variant=variant,
                          calendar_hash=F.calendar_hash(m), use_parents=use_parents)
        except F.FamilyError:
            refused += 1
            return
        clones.append(replace(win, rule_id=rule_id, variant=variant, calendar=fn,
                              use_parents=tuple(use_parents)))

    for k in range(5):  # renamed files, same calendar
        attempt(f"calibration.renamed{k}", F.PRIMARY, wfn)
    for k in range(6):  # candidate variants of the winning rule (orb widened by k years)
        fn = _memo_calendar((lambda kk: lambda idx: wfn(idx) | wfn(idx + pd.DateOffset(years=kk + 1)))(k))
        attempt(win.rule_id, f"orb{k}", fn)
    for k in range(6):  # use: children of the winner
        fn = _memo_calendar((lambda kk: lambda idx: wfn(idx) & (np.asarray(idx.year) % (kk + 7) != 0))(k))
        attempt(f"calibration.child{k}", F.PRIMARY, fn, [(win.rule_id, 1, whash)])
    copies_s_old = 0
    if clones:  # on the old vintage: no handle can include them, so the run is provisional
        res2 = P.run_domain(CalibDomain(ctx, {"value": y1}, per1), run1, clones, lock, ctx.run_dir,
                            handle=None, provisional=True, sealer=NoSeal, write=False)
        copies_s_old = sum(r["verdict"]["code"] == "S" for r in res2["records"])
    false_s2 = False
    if clones and sc.gen == "clone_fresh":
        lock.close_batch(vintage=CLONE_V2, seal_bundle_sha256=SEAL_HASH)
        per2 = Periods(explore=(d[0].date(), pd.Timestamp("1958-12-31").date()),
                       confirm=(pd.Timestamp("1959-01-01").date(), d[-1].date()))
        run2 = replace(run1, vintage=CLONE_V2, missing_bars={})
        h2 = _handle(ctx, 2, CLONE_V2, [t.test_id for t in clones], tok + "-2")
        try:
            res3 = P.run_domain(CalibDomain(ctx, {"value": y}, per2), run2, clones, lock, ctx.run_dir,
                                handle=h2, provisional=False, sealer=NoSeal, write=False)
        finally:
            SB._ISSUED.pop(h2.token, None)
        false_s2 = any(r["verdict"]["code"] == "S" for r in res3["records"])
    return {"any_false_s": int(false_s1 or copies_s_old > 0 or false_s2), "copies_s_old": int(copies_s_old > 0),
            "accepted": len(clones), "refused": refused}


def run_clone_chunk(sc: Scenario, a: int, b: int, ctx: Ctx) -> Dict[str, Any]:
    counts = {f"{o.case_id}|{o.cell}": 0 for o in sc.outputs}
    aux = {"reps": 0, "accepted": 0, "refused": 0}
    for i in range(a, b):
        r = clone_family(ctx, i)
        for o in sc.outputs:
            counts[f"{o.case_id}|{o.cell}"] += r[o.metric]
        aux["reps"] += 1
        aux["accepted"] += r["accepted"]
        aux["refused"] += r["refused"]
    return {"counts": counts, "aux": aux, "extra": {}}


# ================================================================== registry
def _o(case: str, cell: str, metric: str, test: int = 0) -> Output:
    return Output(case, cell, metric, test)


_NOISE_SD = {"normal": 1.0, "t3": math.sqrt(3.0), "lognormal": math.sqrt((math.e - 1.0) * math.e),
             "exponential": 1.0, "zero_inflated": 0.2, "garch": 1.0, "regimes": 1.6, "ar1_0.1": 1.0,
             "ar1_0.3": 1.0, "drift": 1.0}
B3_GENS = ("garch", "regimes", "ar1_0.1", "ar1_0.3")
DAILY_REAL_B3 = ("mercury_retrograde", "moon_nakshatra_group", "tithi_group", "eclipse_window")
DAILY_EVENT = ("new_moon_like", "tithi_group", "eclipse_window")
Z_DAILY = ("mercury_retrograde", "venus_combust", "moon_nakshatra_group", "tithi_group",
           "sun_nakshatra", "sun_sign", "eclipse_window")
Z_YEARLY = ("rahu_in_aries", "rahu_in_libra", "jupiter_in_cancer", "saturn_in_aries",
            "saturn_in_libra", "saturn_in_capricorn", "jupiter_in_water", "saturn_in_fire", "rahu_in_dual")
#: Under Amendment A1 a gap shorter than the active run gives no equal-size block, so 5/5,
#: 20/5 and 60/10 are Untestable. 5/6 and 20/21 are the shortest testable gaps: their
#: control bars touch the episode, the riskiest testable case.
SHAPES = tuple(sim.PERIODIC_SHAPES) + ((5, 6), (20, 21))
FAMILY_CALENDARS = ("cyc:5/15/1", "cyc:3/10/5", "cyc:8/20/2", "cyc:10/30/7", "cyc:6/24/11",
                    "cyc:4/16/3", "cyc:12/36/0", "cyc:2/12/6")
BLOCK_COUNTS = sim.BLOCK_COUNTS  # 8, 12, 20


@lru_cache(maxsize=1)
def scenarios() -> Dict[str, Scenario]:
    """Every scenario of the certificate, by id (fixed order)."""
    out: List[Scenario] = []

    def add(**kw):
        out.append(Scenario(**kw))

    # ---- 1.3 B1, B2, B3 on periodic calendars (bars), R2 under no effect alongside
    for (a, g) in SHAPES:
        for k in sim.PERIODIC_EPISODES:
            for gen in ("normal",) + sim.SKEWED_KINDS + B3_GENS:
                case = "B1" if gen == "normal" else ("B2" if gen in sim.SKEWED_KINDS else "B3")
                cell = f"{gen} {a}/{g} K={k}"
                add(sid=f"{case}.{gen}.{a}-{g}.K{k}", grid="monthly", calendars=(f"per:{a}/{g}/{k}",), gen=gen,
                    outcome_type="continuous", noise_sd=_NOISE_SD[gen],
                    outputs=(_o(case, cell, "rej"), _o("R2N", f"{case} {cell}", "r2")))
    add(sid="B1.normal.20-20.K18.gaps", grid="monthly", calendars=("per:20/20/18",), gen="normal",
        outcome_type="continuous", missing_every=23,
        outputs=(_o("B1", "normal 20/20 K=18, declared outcome gaps every 23rd bar", "rej"),
                 _o("R2N", "B1 normal 20/20 K=18 with gaps", "r2")))
    # ---- 1.3 B3 on the real daily calendars; A2 daily-event calendars for B1, B2; drift (A2 D1)
    for name in DAILY_REAL_B3:
        for gen in B3_GENS:
            add(sid=f"B3.{gen}.daily.{name}", grid="daily", calendars=(f"daily:{name}",), gen=gen,
                outcome_type="continuous", noise_sd=_NOISE_SD[gen], chunk=10,
                outputs=(_o("B3", f"{gen} daily {name}", "rej"), _o("R2N", f"B3 {gen} daily {name}", "r2")))
    for name in DAILY_EVENT:
        for gen in ("normal",) + sim.SKEWED_KINDS:
            case = "B1" if gen == "normal" else "B2"
            add(sid=f"{case}.{gen}.daily.{name}", grid="daily", calendars=(f"daily:{name}",), gen=gen,
                outcome_type="continuous", noise_sd=_NOISE_SD[gen], chunk=10,
                outputs=(_o(case, f"{gen} daily-event (A2) {name}", "rej"),
                         _o("R2N", f"{case} {gen} daily {name}", "r2")))
        add(sid=f"B3.drift.daily.{name}", grid="daily", calendars=(f"daily:{name}",), gen="drift",
            outcome_type="continuous", chunk=10,
            outputs=(_o("B3", f"A2 drift (D1 of the amendment), detrended, {name}", "rej"),
                     _o("R2N", f"B3 drift daily {name}", "r2")))
    # ---- rare-event and discrete outcomes under no effect (B2 rows for events and flags)
    for m in sim.RARE_EVENT_MEANS:
        add(sid=f"B2.poisson{m}.8-8.K12", grid="monthly", calendars=("per:8/8/12",), gen=f"poisson:{m}:8",
            outcome_type="events", base_rate=m / 8.0,
            outputs=(_o("B2", f"events Poisson {m} per window 8/8 K=12", "rej"),
                     _o("R2N", f"events Poisson {m} per window 8/8 K=12", "r2")))
    add(sid="B2.ns.20-20.K12", grid="monthly", calendars=("per:20/20/12",), gen="ns:0.05",
        outcome_type="events", base_rate=0.075,
        outputs=(_o("B2", "events Neyman-Scott mainshocks 20/20 K=12", "rej"),
                 _o("R2N", "events Neyman-Scott mainshocks 20/20 K=12", "r2")))
    add(sid="B2.garchflags.40-40.K12", grid="monthly", calendars=("per:40/40/12",), gen="garch_flags",
        outcome_type="flags", base_rate=sim.GARCH_FLAG_RATE,
        outputs=(_o("B2", "flags clustered GARCH 5% 40/40 K=12", "rej"),
                 _o("R2N", "flags clustered GARCH 5% 40/40 K=12", "r2")))
    add(sid="B2.drought.2-2.K14", grid="yearbars", calendars=("per:2/2/14",), gen="drought",
        outcome_type="flags", base_rate=sim.DROUGHT_FLAG_RATE,
        outputs=(_o("B2", "flags drought years 15% 2/2 K=14", "rej"),
                 _o("R2N", "flags drought years 15% 2/2 K=14", "r2")))
    # ---- 2.4 X1, X2: constant shift equal to the SESOI
    for case, kinds in (("X1", ("normal", "t3")), ("X2", ("lognormal", "exponential"))):
        for kind in kinds:
            for k in BLOCK_COUNTS:
                add(sid=f"{case}.{kind}.K{k}", grid="monthly", calendars=(f"bal:1.0/{k}/8",), gen=kind,
                    outcome_type="continuous", effect=SESOI_SHIFT, sesoi=SESOI_SHIFT, noise_sd=_NOISE_SD[kind],
                    outputs=(_o(case, f"{kind} shift K={k}", "excluded"),))
            if kind in ("normal", "t3", "lognormal"):
                add(sid=f"{case}.{kind}.logratio.K12", grid="monthly", calendars=("bal:1.0/12/8",), gen=kind,
                    outcome_type="log_ratio", effect=1.5, sesoi=1.5, noise_sd=1.2,
                    outputs=(_o(case, f"{kind} log ratio K=12", "excluded"),))
        for name in ("new_moon_like", "eclipse_window"):
            kind = kinds[0]
            add(sid=f"{case}.{kind}.daily.{name}", grid="daily", calendars=(f"daily:{name}",), gen=kind,
                outcome_type="continuous", effect=SESOI_SHIFT, sesoi=SESOI_SHIFT, noise_sd=_NOISE_SD[kind],
                chunk=10, outputs=(_o(case, f"{kind} daily-event (A2, detrended) {name}", "excluded"),))
    # ---- X3 rare Poisson events, X4 clustered events, X5 clustered flags
    for m in sim.RARE_EVENT_MEANS:
        for r in (2.0, 1.5):
            for k in BLOCK_COUNTS:
                add(sid=f"X3.poisson{m}.rr{r}.K{k}", grid="monthly", calendars=(f"bal:1.0/{k}/8",),
                    gen=f"poisson:{m}:8", outcome_type="events", effect=r, sesoi=r, base_rate=m / 8.0,
                    outputs=(_o("X3", f"Poisson {m} per window, rate ratio {r}, K={k}", "excluded"),))
    for r in (2.0, 1.5):
        for k in BLOCK_COUNTS:
            add(sid=f"X4.ns.rr{r}.K{k}", grid="monthly", calendars=(f"bal:1.0/{k}/20",), gen="ns:0.05",
                outcome_type="events", effect=r, sesoi=r, base_rate=0.075,
                outputs=(_o("X4", f"Neyman-Scott mainshocks, doubling background, rate ratio {r}, K={k}",
                            "excluded"),))
    for k in BLOCK_COUNTS:
        add(sid=f"X5.garchflags.K{k}", grid="monthly", calendars=(f"bal:1.0/{k}/40",), gen="garch_flags",
            outcome_type="flags", effect=2.0, sesoi=2.0, base_rate=sim.GARCH_FLAG_RATE,
            outputs=(_o("X5", f"clustered GARCH flags 5%, risk ratio 2, K={k}", "excluded"),))
        add(sid=f"X5.drought.K{k}", grid="yearbars", calendars=(f"bal:1.0/{k}/2",), gen="drought",
            outcome_type="flags", effect=2.0, sesoi=2.0, base_rate=sim.DROUGHT_FLAG_RATE,
            outputs=(_o("X5", f"drought-year flags 15%, risk ratio 2, K={k}", "excluded"),))
    # ---- X6 coverage, X7 balance edge, X9 uneven effect (recorded)
    for e in (0.0, 0.25, 0.5, 1.0):
        add(sid=f"X6.normal.e{e}", grid="monthly", calendars=("bal:1.0/12/8",), gen="normal",
            outcome_type="continuous", effect=e, sesoi=SESOI_SHIFT,
            outputs=(_o("X6", f"normal shift, true effect {e}, K=12", f"below:{e}"),))
    for e in (1.0, math.sqrt(2.0), 2.0, 4.0):
        add(sid=f"X6.poisson.e{e:.4f}", grid="monthly", calendars=("bal:1.0/12/8",), gen="poisson:2.0:8",
            outcome_type="events", effect=e, sesoi=SESOI_RATIO, base_rate=0.25,
            outputs=(_o("X6", f"Poisson 2 per window, true rate ratio {e:.4f}, K=12", f"below:{e}"),))
    for bal in sim.BALANCES:
        add(sid=f"X7.lognormal.b{bal}", grid="monthly", calendars=(f"bal:{bal}/12/8",), gen="lognormal",
            outcome_type="continuous", effect=SESOI_SHIFT, sesoi=SESOI_SHIFT, noise_sd=_NOISE_SD["lognormal"],
            outputs=(_o("X7", f"lognormal, balance {bal}, K=12", "excluded"),))
        add(sid=f"X7.poisson.b{bal}", grid="monthly", calendars=(f"bal:{bal}/12/8",), gen="poisson:0.5:8",
            outcome_type="events", effect=SESOI_RATIO, sesoi=SESOI_RATIO, base_rate=0.0625,
            outputs=(_o("X7", f"Poisson 0.5 per window, balance {bal}, K=12", "excluded"),))
    add(sid="X9.lognormal", grid="monthly", calendars=("bal:1.0/12/8",), gen="lognormal", uneven=True,
        outcome_type="continuous", effect=SESOI_SHIFT, sesoi=SESOI_SHIFT, noise_sd=_NOISE_SD["lognormal"],
        outputs=(_o("X9", "lognormal, whole effect in 20% of episodes, K=12", "excluded"),))
    add(sid="X9.poisson", grid="monthly", calendars=("bal:1.0/12/8",), gen="poisson:2.0:8", uneven=True,
        outcome_type="events", effect=SESOI_RATIO, sesoi=SESOI_RATIO, base_rate=0.25,
        outputs=(_o("X9", "Poisson 2 per window, whole effect in 20% of episodes, K=12", "excluded"),))
    # ---- 6.3 season
    for name in Z_DAILY:
        add(sid=f"Z1.{name}", grid="daily", calendars=(f"daily:{name}",), gen="seasonal",
            outcome_type="continuous", chunk=10,
            outputs=(_o("Z1", f"{name} S", "S"), _o("Z1", f"{name} R2 passes", "r2")))
        add(sid=f"Z2.{name}", grid="daily", calendars=(f"daily:{name}",), gen="season_ns:0.05",
            outcome_type="events", base_rate=1.0, chunk=10,
            outputs=(_o("Z2", f"{name} S", "S"), _o("Z2", f"{name} R2 passes", "r2")))
    rsd = sim.rainfall_sd()
    for name in Z_YEARLY:
        add(sid=f"Z3.rain.{name}", grid="yearly", calendars=(f"yearly:{name}",), gen="rain",
            outcome_type="continuous", baselines="trend+enso", noise_sd=rsd,
            outputs=(_o("Z3", f"{name} rainfall S", "S"), _o("Z3", f"{name} rainfall R2 passes", "r2")))
        add(sid=f"Z3.drought.{name}", grid="yearly", calendars=(f"yearly:{name}",), gen="rain_drought",
            outcome_type="flags", baselines="trend+enso", base_rate=sim.DROUGHT_FLAG_RATE,
            outputs=(_o("Z3", f"{name} drought S", "S"), _o("Z3", f"{name} drought R2 passes", "r2")))
        add(sid=f"Z3.rainx.{name}", grid="yearly", calendars=(f"yearly:{name}",), gen="rain",
            outcome_type="continuous", baselines="trend+enso", noise_sd=rsd,
            effect=round(0.5 * rsd, 4), sesoi=round(0.5 * rsd, 4),
            outputs=(_o("Z3", f"{name} rainfall false exclusion at SESOI", "excluded"),))
    for s in sim.SIGNS:
        name = f"rahu_in_{s.lower()}"
        add(sid=f"Z6.{name}", grid="yearly_z6", calendars=(f"yearly:{name}",), gen="nodal",
            outcome_type="continuous", baselines="trend+nodal",
            outputs=(_o("Z6", f"{name} S with the nodal baseline", "S"),
                     _o("Z6", f"{name} R4 passes (must not)", "r4")))
    # ---- 7.3 festival-only effect on the tithi calendar
    add(sid="K1.tithi_group", grid="daily", calendars=("daily:tithi_group",), gen="festival",
        outcome_type="continuous", baselines="trend+festival", chunk=10,
        outputs=(_o("K1", "tithi group, festival-day effect only, with the festival baseline", "S"),))
    add(sid="K2.tithi_group", grid="daily", calendars=("daily:tithi_group",), gen="festival",
        outcome_type="continuous", baselines="trend", chunk=10,
        outputs=(_o("K2", "tithi group, festival-day effect only, without the festival baseline", "S"),))
    # ---- 8 D1: monthly averages with one guard month
    for k in BLOCK_COUNTS:
        add(sid=f"D1.monthly_avg.K{k}", grid="monthly", calendars=(f"per:2/8/{k}",), gen="monthly_avg",
            outcome_type="continuous", guard_bars=1,
            outputs=(_o("D1", f"monthly averages, guard 1, 2/8 K={k}", "rej"),
                     _o("R2N", f"D1 monthly averages 2/8 K={k}", "r2")))
    # ---- 4.4 W1 power at twice the gate's minimal detectable effect; W2 limit-only never S
    add(sid="W1.normal", grid="monthly", calendars=("per:20/20/18",), gen="normal", outcome_type="continuous",
        effect="mde", replications=1_000, outputs=(_o("W1", "continuous normal 20/20 K=18", "S"),))
    add(sid="W1.poisson", grid="monthly", calendars=("per:8/8/18",), gen="poisson:2.0:8", outcome_type="events",
        effect="mde", base_rate=0.25, replications=1_000,
        outputs=(_o("W1", "events Poisson 2 per window 8/8 K=18", "S"),))
    add(sid="W1.garchflags", grid="monthly", calendars=("per:40/40/18",), gen="garch_flags",
        outcome_type="flags", effect="mde", base_rate=sim.GARCH_FLAG_RATE, replications=1_000,
        outputs=(_o("W1", "flags clustered GARCH 5% 40/40 K=18", "S"),))
    add(sid="W2.normal", grid="monthly", calendars=("per:20/20/5/12",), gen="normal", outcome_type="continuous",
        effect=2.0, sesoi=SESOI_SHIFT, replications=1_000,
        outputs=(_o("W2", "continuous, 12 explore and 5 confirm episodes, effect 4 SESOI", "S"),))
    add(sid="W2.poisson", grid="monthly", calendars=("per:8/8/5/12",), gen="poisson:2.0:8", outcome_type="events",
        effect=4.0, sesoi=SESOI_RATIO, base_rate=0.25, replications=1_000,
        outputs=(_o("W2", "events, 12 explore and 5 confirm episodes, rate ratio 4", "S"),))
    # ---- 3.6 F8 null families through the pipeline, one per outcome type
    for label, gen, otype, br in (("continuous normal", "normal", "continuous", None),
                                  ("continuous lognormal", "lognormal", "continuous", None),
                                  ("events Poisson", "poisson:0.5:8", "events", 0.0625),
                                  ("flags clustered GARCH", "garch_flags", "flags", sim.GARCH_FLAG_RATE)):
        add(sid=f"F8.{gen.split(':')[0]}.{otype}", grid="monthly", calendars=FAMILY_CALENDARS, gen=gen,
            outcome_type=otype, base_rate=br, n_bars=480, replications=2_000, chunk=20,
            noise_sd=_NOISE_SD.get(gen, 1.0),
            outputs=(_o("F8S", f"{label}, family of {len(FAMILY_CALENDARS)}", "any_S"),
                     _o("F8C", f"{label}, family of {len(FAMILY_CALENDARS)}", "any_C")))
    # ---- 3.6 F3, F4 clone attack on real calendars through the pipeline
    add(sid="F3.clone", grid="yearly_long", calendars=CLONE_CALENDARS, gen="clone_same", kind="clone",
        outcome_type="continuous", replications=2_000, chunk=10,
        outputs=(_o("F3", "families with any false S (43 real calendars, copies on the same vintage)", "any_false_s"),
                 _o("F3", "families with a false S among the copies on the old vintage (must be 0)", "copies_s_old")))
    add(sid="F4.clone", grid="yearly_long", calendars=CLONE_CALENDARS, gen="clone_fresh", kind="clone",
        outcome_type="continuous", replications=2_000, chunk=10,
        outputs=(_o("F4", "families with any false S over both batches (fresh vintage for batch 2)",
                    "any_false_s"),))
    # Daily grids carry hundreds of blocks: Monte Carlo sign flips with 9,999 draws (a plan
    # input; the Monte Carlo p-value is valid for any number of draws).
    out = [replace(s, n_draws=DAILY_DRAWS) if s.grid == "daily" else s for s in out]
    sids = [s.sid for s in out]
    if len(sids) != len(set(sids)):
        raise ValueError("duplicate scenario ids")
    for s in out:
        for o in s.outputs:
            cal.get_case(o.case_id)
    return {s.sid: s for s in out}


#: Cases that never run a scenario: properties and the old-method documentation runs.
PROPERTY_CASES = ("B4", "B6", "X10", "F1", "F2", "F5", "F6", "F7", "W4", "R2P", "Z5")
OLD_METHOD_JOBS = ("old.B5", "old.X8", "old.Z4")


# ================================================================ old methods
def run_old(job: str) -> List[Dict[str, Any]]:
    """B5, X8, Z4: the old functions, kept failing on purpose (they document the loopholes)."""
    if job == "old.B5":
        from tests import test_stats_blocks as tb

        reps = cal.get_case("B5").replications
        return [r.to_dict() for r in tb.run_b5(reps)]
    if job == "old.X8":
        from tests import test_stats_exclusion as tx

        reps = cal.get_case("X8").replications
        out = []
        for kind in ("exponential", "rare", "lognormal"):  # the three skewed rows of appendix A.1
            rate = tx.run_x8(kind, reps=reps, seed=int(cal.case_seed(BASE_SEED, "X8", kind)) % (2**32))
            out.append(cal.evaluate("X8", f"old episode_equivalence, {kind}", int(round(rate * reps)), reps).to_dict())
        return out
    if job == "old.Z4":
        from tests import test_stats_season as tz

        reps = cal.get_case("Z4").replications
        rows = tz.run_z4(reps)
        best = max(rows, key=lambda r: r[2])  # "for at least one Sun-linked calendar"
        note = "; ".join(f"{c}: {h}/{n}" for _, c, h, n, _ in rows)
        r = cal.evaluate("Z4", f"old neighbour design, highest Sun-linked cell: {best[1]}", best[2], best[3])
        return [replace(r, note=f"all cells: {note}").to_dict()]
    raise ValueError(f"unknown old-method job {job!r}")


# ============================================================ property cases
def _prop(case: str, cell: str, ok: bool, note: str = "") -> cal.CaseResult:
    return cal.property_result(case, cell, bool(ok), note)


def prop_b4() -> cal.CaseResult:
    """No bar in two blocks; control bars are inactive, available, and never more than the inactive bars."""
    bad, seen, n_checked = [], set(), 0
    for sc in scenarios().values():
        dates, _, masks, cut, n = layout(sc)
        cut = int(cut if cut is not None else round(sc.explore_share * n))
        seed = int(cal.derive_seed(BASE_SEED, sc.sid, "plan"))
        for key, m in zip(sc.calendars, masks):
            conf = np.zeros(n, dtype=bool)
            conf[cut:] = True
            for avail in (None, conf):
                k = (sc.grid, n, key, sc.guard_bars, avail is None, seed)
                if k in seen:
                    continue
                seen.add(k)
                d = S.control_design(m, dates, merge_gap=0, guard_bars=sc.guard_bars, available=avail,
                                     side_seed=seed).blocks
                used: set = set()
                n_control = 0
                for b in d.used_blocks:
                    bars = set(np.asarray(b.active).tolist()) | set(np.asarray(b.control).tolist())
                    ctrl = np.asarray(b.control, dtype=int)
                    if bars & used or m[ctrl].any() or (avail is not None and not avail[ctrl].all()):
                        bad.append(f"{sc.sid}:{key}")
                    used |= bars
                    n_control += len(ctrl)
                inactive = int((~m).sum() if avail is None else (~m & avail).sum())
                if n_control > inactive:
                    bad.append(f"{sc.sid}:{key} control count")
                n_checked += 1
    return _prop("B4", "every scenario calendar, whole and confirm period", not bad,
                 f"{n_checked} designs checked; problems: {bad[:5]}")


def prop_x10() -> cal.CaseResult:
    """Exclusion p never increases as r grows (shift, thinned events, detrended daily shift)."""
    bad = []
    for sid in ("X1.normal.K12", "X3.poisson2.0.rr2.0.K12", "X5.garchflags.K12", "X1.normal.daily.new_moon_like"):
        sc = scenarios()[sid]
        ctx = Ctx(sc, Path(tempfile.mkdtemp(prefix="x10-")))
        try:
            design = S.control_design(ctx.cal0, ctx.dates, merge_gap=0, guard_bars=sc.guard_bars,
                                      side_seed=ctx.plan_seed).blocks
            daily = S.detrend_required(ctx.dates)
            shape = S.detrended_effect_shape(ctx.cal0, DETREND_WINDOW) if daily else None
            grid = np.asarray(sc.x_grid)[:: max(1, len(sc.x_grid) // 40)]
            for i in range(5):
                y, _ = generate(ctx, outcome_rng(sid, i))
                if daily:
                    y = S.centred_detrend(y, DETREND_WINDOW)
                thin = np.random.default_rng(i) if sc.outcome_type in X.THINNED_TYPES else None
                er = X.EffectRemoval(design, y, outcome_type=sc.outcome_type, thinning_rng=thin,
                                     signflip_seed=i + 1, n_draws=999, effect_shape=shape)
                ps = [er.exclusion_p(float(r), "greater") for r in grid]
                if any(b > a + 1e-12 for a, b in zip(ps, ps[1:])):
                    bad.append(f"{sid} rep {i}")
        finally:
            ctx.close()
    return _prop("X10", "exclusion p over the plan grid", not bad, f"non-monotone: {bad}")


def _family_ctx(n_tests: int, sid: str, *, plan_seed: int, outcomes=None) -> Ctx:
    sc = replace(scenarios()["F8.normal.continuous"], sid=sid, calendars=FAMILY_CALENDARS[:n_tests])
    return Ctx(sc, Path(tempfile.mkdtemp(prefix="fam-")), plan_seed=plan_seed, outcomes=outcomes)


def prop_f1() -> cal.CaseResult:
    """Another test's p-value moved to almost 0 leaves this test's record byte-identical."""
    seed = int(cal.derive_seed(BASE_SEED, "F1"))
    ctx = _family_ctx(2, "F1", plan_seed=seed, outcomes=["value", "other"])
    try:
        rng = outcome_rng("F1", 0)
        y = rng.standard_normal(ctx.n)
        other = rng.standard_normal(ctx.n)
        recs = []
        for o in (other, other + 3.0 * ctx.masks[1]):
            dom = CalibDomain(ctx, {"value": y, "other": o})
            res = P.run_domain(dom, ctx.run_spec({}), ctx.tests, ctx.lock, ctx.run_dir, handle=ctx.handle,
                               provisional=False, sealer=NoSeal, write=False)
            recs.append({r["test_id"]: r for r in res["records"]})
        a, b = ctx.tests[0].test_id, ctx.tests[1].test_id
        p0, p1 = recs[0][b]["p"]["support_confirm"], recs[1][b]["p"]["support_confirm"]
        moved = p1 <= recs[1][b]["threshold"]["a_test"] < p0
        # The dataset hash (and the input hash built on it) changes with the data by design.
        strip = lambda r: {k: v for k, v in r.items() if k not in ("dataset", "input_sha256")}  # noqa: E731
        same = F.canonical_bytes(strip(recs[0][a])) == F.canonical_bytes(strip(recs[1][a]))
    finally:
        ctx.close()
    return _prop("F1", "two tests, two outcomes; the other test's p moved below a_test", moved and same,
                 f"other p {p0:.4g} -> {p1:.4g}; record identical apart from the dataset hash: {same}")


def prop_f2() -> cal.CaseResult:
    """Close batch 1, run, register 5 more tests, run again: batch 1 byte-identical, the 5 flagged."""
    sc = scenarios()["B1.normal.20-20.K18"]
    ctx = Ctx(sc, Path(tempfile.mkdtemp(prefix="f2-")))
    try:
        res1, _ = run_once(ctx, 0)
        P.record_batch_results(ctx.lock, res1)
        prev = ctx.run_dir / "results_f2.json"
        prev.write_text(json.dumps(res1, sort_keys=True), encoding="utf-8")
        new = []
        for s in range(1, 6):
            m = np.roll(ctx.cal0, s)
            fn = bar_calendar(m, ctx.dates, "month")
            t = replace(ctx.tests[0], rule_id=f"calibration.late{s}", calendar=fn)
            ctx.lock.register(rule_id=t.rule_id, version=1, outcome="value", calendar_hash=F.calendar_hash(m))
            new.append(t)
        y, extra = generate(ctx, outcome_rng(sc.sid, 0))
        res2 = P.run_domain(CalibDomain(ctx, {"value": y}), ctx.run_spec(extra), ctx.tests + new, ctx.lock,
                            ctx.run_dir, handle=None, provisional=True, sealer=NoSeal, previous=prev, write=False)
        by = {r["test_id"]: r for r in res2["records"]}
        t0 = ctx.tests[0].test_id
        same = F.canonical_bytes(by[t0]) == F.canonical_bytes(res1["records"][0])
        flagged = all("registered_after_unblinding" in by[t.test_id]["verdict"]["flags"]
                      and ctx.lock.test_record(t.test_id)["batch"] == 2 for t in new)
    finally:
        ctx.close()
    return _prop("F2", "one test closed and run, five registered after", same and flagged,
                 f"batch-1 record identical: {same}; five in batch 2 flagged: {flagged}")


def prop_f5() -> cal.CaseResult:
    table = F.alpha_table(50)
    ok = sum(table) <= 0.05 + 1e-15
    for b, ab in enumerate(table, start=1):
        for n_b in (1, 2, 3, 7, 20, 43, 60):
            ok &= F.a_test_for(ab, n_b) == ab / n_b
    return _prop("F5", "50 batches", ok, f"sum of alpha_b = {sum(table)!r}")


def prop_f6() -> cal.CaseResult:
    """Tests A, B and then A, B, C: every number of A and B identical (E4)."""
    seed = int(cal.derive_seed(BASE_SEED, "F6"))
    keep = ("effect", "robustness")
    outs = []
    for k in (2, 3):
        ctx = _family_ctx(k, f"F6.{k}", plan_seed=seed)
        try:
            y = outcome_rng("F6", 0).standard_normal(ctx.n)
            res = P.run_domain(CalibDomain(ctx, {"value": y}), ctx.run_spec({}), ctx.tests, ctx.lock,
                               ctx.run_dir, handle=ctx.handle, provisional=False, sealer=NoSeal, write=False)
            outs.append({r["test_id"]: r for r in res["records"]})
        finally:
            ctx.close()
    ok = True
    for tid in outs[0]:
        a, b = outs[0][tid], outs[1][tid]
        ok &= all(F.canonical_bytes(a[k]) == F.canonical_bytes(b[k]) for k in keep)
        ok &= F.canonical_bytes(a["p"]["descriptive"]) == F.canonical_bytes(b["p"]["descriptive"])
        ok &= F.canonical_bytes(a["bound"]["x95"]) == F.canonical_bytes(b["bound"]["x95"])
    return _prop("F6", "tests A, B against A, B, C through the pipeline", ok,
                 "effect, robustness, p (descriptive) and X95 compared byte for byte")


def prop_f7() -> cal.CaseResult:
    """Every row of the ADR-008 3.2 eligibility table gives the exact allowed verdicts and flag."""
    v1 = {"id": "v1", "seen": False, "confirm_period": {"start": "2000-01-01", "end": "2010-12-31"}}
    v2 = {"id": "v2", "seen": False, "confirm_period": {"start": "2011-01-01", "end": "2020-12-31"}}
    vs = {"id": "vs", "seen": True, "confirm_period": {"start": "2000-01-01", "end": "2010-12-31"}}
    h = [hashlib.sha256(bytes([i])).hexdigest() for i in range(4)]
    lock = F.FamilyLock(None, "f7")
    a = lock.register(rule_id="f7.a", version=1, outcome="y", calendar_hash=h[0])["test_id"]
    lock.close_batch(vintage=v1, seal_bundle_sha256=SEAL_HASH)
    late = lock.register(rule_id="f7.late", version=1, outcome="y", calendar_hash=h[1])["test_id"]
    rows = []
    e = lock.eligibility(a, v1)
    rows.append(("before close, unseen", (e.allow_s, e.allow_c, e.allow_e), (True, True, True), e.flags, ()))
    e = lock.eligibility(late, v1)
    rows.append(("after close, same vintage", (e.allow_s, e.allow_c, e.allow_e), (False, False, False),
                 e.flags, ("registered_after_unblinding",)))
    lock.close_batch(vintage=v2, seal_bundle_sha256=SEAL_HASH)
    e = lock.eligibility(late, v2)
    rows.append(("later batch, fresh vintage", (e.allow_s, e.allow_c, e.allow_e), (True, True, True), e.flags, ()))
    seen = F.FamilyLock(None, "f7s")
    old = seen.register(rule_id="f7.old", version=1, outcome="y", calendar_hash=h[2])["test_id"]
    newer = seen.register(rule_id="f7.new", version=1, outcome="y", calendar_hash=h[3])["test_id"]
    seen.close_batch(vintage=vs, seal_bundle_sha256=SEAL_HASH)
    e = seen.eligibility(old, vs, first_look_calendars=[h[2]])
    rows.append(("before close, seen, hash older than first look", (e.allow_s, e.allow_c, e.allow_e),
                 (False, False, True), e.flags, ("seen_data",)))
    e = seen.eligibility(newer, vs, first_look_calendars=[h[2]])
    rows.append(("before close, seen, newer hash", (e.allow_s, e.allow_c, e.allow_e), (False, False, False),
                 e.flags, ()))
    bad = [r[0] for r in rows if r[1] != r[2] or tuple(r[3]) != r[4]]
    return _prop("F7", "every row of the 3.2 table", not bad, f"rows not matching: {bad}")


def prop_r2p(reps: int = 3) -> cal.CaseResult:
    """Nakshatra-only, tithi-only and orb calendars with a strong effect pass R2; R2 is per test."""
    bad, notes = [], []
    for name in ("moon_nakshatra_group", "tithi_group", "mercury_venus_orb"):
        sc = Scenario(sid=f"R2P.{name}", grid="daily", calendars=(f"daily:{name}",), gen="normal",
                      outcome_type="continuous", effect=1.0, outputs=())
        ctx = Ctx(sc, Path(tempfile.mkdtemp(prefix="r2p-")))
        try:
            passes = []
            for i in range(reps):
                res, _ = run_once(ctx, i)
                passes.append(bool(res["records"][0]["robustness"]["R2"]["passes"]))
            notes.append(f"{name}: R2 passed {sum(passes)}/{reps}")
            if not all(passes):
                bad.append(name)
        finally:
            ctx.close()
    # A second test leaves the first test's R2 byte-identical.
    seed = int(cal.derive_seed(BASE_SEED, "R2P", "pair"))
    r2 = []
    for cals in (("daily:moon_nakshatra_group",), ("daily:moon_nakshatra_group", "daily:mercury_venus_orb")):
        sc = Scenario(sid="R2P.pair", grid="daily", calendars=cals, gen="normal", outcome_type="continuous",
                      effect=1.0, outputs=())
        ctx = Ctx(sc, Path(tempfile.mkdtemp(prefix="r2p-")), plan_seed=seed)
        try:
            res, _ = run_once(ctx, 0)
            first = next(r for r in res["records"] if r["test_id"] == ctx.tests[0].test_id)
            r2.append(F.canonical_bytes(first["robustness"]["R2"]))
        finally:
            ctx.close()
    if r2[0] != r2[1]:
        bad.append("second test changed the first test's R2")
    return _prop("R2P", "strong effect on nakshatra, tithi and orb calendars; R2 per test", not bad,
                 "; ".join(notes) + (f"; failed: {bad}" if bad else ""))


def prop_z5() -> cal.CaseResult:
    """Sun in sign: Untestable for the season, and no outcome is read."""
    sc = scenarios()["Z1.sun_sign"]
    ctx = Ctx(sc, Path(tempfile.mkdtemp(prefix="z5-")))
    try:
        y, extra = generate(ctx, outcome_rng(sc.sid, 0))
        dom = CalibDomain(ctx, {"value": y})
        res = P.run_domain(dom, ctx.run_spec(extra), ctx.tests, ctx.lock, ctx.run_dir, handle=ctx.handle,
                           provisional=False, sealer=NoSeal, write=False)
        rec = res["records"][0]
        ok = rec["verdict"]["code"] == "U" and rec["gate"]["untestable_reason"] == "season" and dom.outcome_reads == 0
        note = f"verdict {rec['verdict']['code']}, reason {rec['gate']['untestable_reason']}, reads {dom.outcome_reads}"
    finally:
        ctx.close()
    return _prop("Z5", "Sun in Aries, daily 1968-1998", ok, note)


def d1_artefact() -> cal.CaseResult:
    """D-01 proof: monthly averages carry lag-1 autocorrelation between 0.15 and 0.35."""
    rng = np.random.default_rng(cal.case_seed(BASE_SEED, "D1", "artefact"))
    ac = float(np.mean([sim.lag1_autocorrelation(sim.monthly_average_returns(30, rng)) for _ in range(200)]))
    ok = 0.15 <= ac <= 0.35
    return cal.CaseResult("D1", "artefact present: mean lag-1 autocorrelation of 30-year monthly averages",
                          None, None, ac, None, ok, cal.PROPERTY, None, "must lie in [0.15, 0.35]")


def property_results(aux_total: Dict[str, int], domain_reps: int) -> List[cal.CaseResult]:
    out = [prop_b4(), prop_x10(), prop_f1(), prop_f2(), prop_f5(), prop_f6(), prop_f7(), prop_r2p(),
           prop_z5(), d1_artefact()]
    out.append(_prop("B6", "every replication of every scenario", domain_reps > 0 and aux_total.get("b6_bad", 1) == 0,
                     f"{aux_total.get('b6_bad')} records out of {domain_reps} runs with blocks unlike the gate's"))
    out.append(_prop("W4", "every replication of every scenario", domain_reps > 0 and aux_total.get("w4_bad", 1) == 0,
                     f"{aux_total.get('w4_bad')} records with P(S | SESOI) < 0.8 and no support_underpowered"))
    return out


# ============================================================== orchestration
DEFAULT_WORK = Path(tempfile.gettempdir()) / "astro-calibration"
_THREAD_ENV = {"OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1", "MKL_NUM_THREADS": "1",
               "VECLIB_MAXIMUM_THREADS": "1", "NUMEXPR_NUM_THREADS": "1"}


def _dirs(work: Path) -> Dict[str, Path]:
    d = {k: Path(work) / k for k in ("jobs", "claimed", "done", "logs", "runs")}
    for p in d.values():
        p.mkdir(parents=True, exist_ok=True)
    return d


def _job_name(prio: int, sid: str, a: int, b: int) -> str:
    return f"{prio}__{sid}__{a:06d}_{b:06d}.json"


def plan_jobs(work: Path, targets: Dict[str, int]) -> int:
    """Write a job file for every chunk not yet done, queued or claimed; return the number written."""
    d = _dirs(work)
    present = {p.name.split(".json")[0] + ".json" for k in ("jobs", "claimed", "done") for p in d[k].iterdir()}
    written = 0
    for sid, reps in targets.items():
        if sid.startswith("old."):
            names = [(_job_name(0, sid, 0, 1), {"sid": sid, "a": 0, "b": 1})]
        else:
            sc = scenarios()[sid]
            prio = 0 if sc.grid == "daily" or sc.kind == "clone" else 1
            names = [(_job_name(prio, sid, a, min(a + sc.chunk, reps)), {"sid": sid, "a": a, "b": min(a + sc.chunk, reps)})
                     for a in range(0, reps, sc.chunk)]
        for name, job in names:
            if name in present:
                continue
            (d["jobs"] / name).write_text(json.dumps(job), encoding="utf-8")
            written += 1
    return written


def worker(work: Path) -> None:
    """Claim job files until none is left (atomic rename); one process, no thread."""
    d = _dirs(work)
    install_cache()
    ctxs: Dict[str, Ctx] = {}
    run_root = d["runs"] / str(os.getpid())
    while True:
        names = sorted(p.name for p in d["jobs"].iterdir() if p.name.endswith(".json"))
        if not names:
            break
        mine = [n for n in names if n.split("__")[1] in ctxs]
        pick = (mine or names)[0]
        claimed = d["claimed"] / f"{pick}.{os.getpid()}"
        try:
            os.rename(d["jobs"] / pick, claimed)
        except FileNotFoundError:
            continue
        job = json.loads(claimed.read_text(encoding="utf-8"))
        t0 = time.time()
        try:
            if job["sid"].startswith("old."):
                res: Dict[str, Any] = {"results": run_old(job["sid"])}
            else:
                sc = scenarios()[job["sid"]]
                if sc.sid not in ctxs:
                    for c in ctxs.values():
                        c.close()
                    ctxs.clear()
                    clear_cache()
                    ctxs[sc.sid] = Ctx(sc, run_root)
                runner = run_clone_chunk if sc.kind == "clone" else run_domain_chunk
                res = runner(sc, job["a"], job["b"], ctxs[sc.sid])
        except Exception:  # noqa: BLE001 - the error goes into the done file and fails the cell
            res = {"error": traceback.format_exc()}
        res.update(job)
        res["seconds"] = round(time.time() - t0, 3)
        res["pid"] = os.getpid()
        tmp = d["done"] / f"{pick}.tmp"
        tmp.write_text(json.dumps(res, sort_keys=True), encoding="utf-8")
        os.replace(tmp, d["done"] / pick)
        claimed.unlink(missing_ok=True)


def run_workers(work: Path, n_workers: int, poll: float = 20.0) -> None:
    """Start worker processes and wait for them; report progress (no thread is started)."""
    d = _dirs(work)
    for p in d["claimed"].iterdir():  # chunks of a previous, interrupted run go back to the queue
        os.replace(p, d["jobs"] / p.name.rsplit(".", 1)[0])
    env = {**os.environ, **_THREAD_ENV, "PYTHONPATH": str(ROOT) + os.pathsep + os.environ.get("PYTHONPATH", "")}
    procs = []
    for k in range(int(n_workers)):
        log = open(d["logs"] / f"worker_{k}.log", "a", encoding="utf-8")  # noqa: SIM115 - closed below
        procs.append((subprocess.Popen([sys.executable, "-m", "tests.test_validity_calibration", "worker",
                                        "--work", str(work)], cwd=str(ROOT), env=env, stdout=log,
                                       stderr=subprocess.STDOUT), log))
    t0 = time.time()
    while any(p.poll() is None for p, _ in procs):
        time.sleep(poll)
        n_jobs = sum(1 for _ in d["jobs"].iterdir())
        n_done = sum(1 for p in d["done"].iterdir() if p.name.endswith(".json"))
        print(f"[{(time.time() - t0) / 60:6.1f} min] done {n_done}, queued {n_jobs}", flush=True)
    for p, log in procs:
        log.close()
        if p.returncode:
            print(f"worker exited with {p.returncode}; see {d['logs']}", flush=True)


def aggregate(work: Path) -> Tuple[List[cal.CaseResult], Dict[str, Any]]:
    """Sum the finished chunks per scenario and turn counts into case results."""
    d = _dirs(work)
    per: Dict[str, Dict[str, Any]] = {}
    old: List[cal.CaseResult] = []
    errors: Dict[str, str] = {}
    for p in sorted(d["done"].iterdir()):
        if not p.name.endswith(".json"):
            continue
        r = json.loads(p.read_text(encoding="utf-8"))
        sid = r["sid"]
        if "error" in r:
            errors[sid] = r["error"]
            continue
        if sid.startswith("old."):
            old.extend(cal.CaseResult(**x) for x in r["results"])
            continue
        if sid not in scenarios():
            continue
        acc = per.setdefault(sid, {"counts": {}, "aux": {}, "extra": {}, "seconds": 0.0, "reps": 0, "ranges": []})
        for k, v in r["counts"].items():
            acc["counts"][k] = acc["counts"].get(k, 0) + int(v)
        for k, v in r["aux"].items():
            acc["aux"][k] = acc["aux"].get(k, 0) + int(v)
        acc["extra"].update(r.get("extra") or {})
        acc["seconds"] += float(r["seconds"])
        acc["reps"] += int(r["b"]) - int(r["a"])
        acc["ranges"].append((int(r["a"]), int(r["b"])))
    results: List[cal.CaseResult] = list(old)
    aux_total: Dict[str, int] = {}
    domain_reps = 0
    for sid, sc in scenarios().items():
        acc = per.get(sid)
        if acc is None:
            continue
        reps = acc["reps"]
        if sc.kind == "domain":
            domain_reps += reps
            for k in ("b6_bad", "w4_bad"):
                aux_total[k] = aux_total.get(k, 0) + acc["aux"].get(k, 0)
        note = f"scenario {sid}"
        if acc["aux"].get("untestable_first"):
            note += f"; first test Untestable in {acc['aux']['untestable_first']} of {reps} runs"
        if acc["aux"].get("r2_tied_reps"):
            note += f"; R2 had tied placebo statistics in {acc['aux']['r2_tied_reps']} runs"
        if acc["extra"]:
            note += "; " + ", ".join(f"{k} {v:.4g}" for k, v in sorted(acc["extra"].items()))
        if sid in errors:
            note += "; ERROR in a chunk"
        for o in sc.outputs:
            results.append(make_result(o, acc["counts"].get(f"{o.case_id}|{o.cell}", 0), reps, note,
                                       failed=sid in errors))
    for sid in errors:
        if sid.startswith("old."):
            results.append(cal.CaseResult(sid.split(".", 1)[1], "old-method run", None, None, None, None, False,
                                          cal.get_case(sid.split(".", 1)[1]).rule, None, "ERROR"))
    summary = {"per": per, "errors": errors, "aux_total": aux_total, "domain_reps": domain_reps}
    return results, summary


def make_result(o: Output, count: int, reps: int, note: str = "", failed: bool = False) -> cal.CaseResult:
    """A cell's result: the case's own mark at full size; the fast mark (noted) below it."""
    spec = cal.get_case(o.case_id)
    if o.metric == "copies_s_old":  # ADR-008 F3: zero S among the copies, in every family
        rate = count / reps if reps else float("nan")
        return cal.CaseResult(o.case_id, o.cell, reps, count, rate, cal.clopper_pearson_upper(count, reps),
                              count == 0 and not failed, cal.ZERO, None, note)
    if reps >= int(spec.replications or 0):
        r = cal.evaluate(o.case_id, o.cell, count, reps)
        return replace(r, passed=r.passed and not failed, note=note)
    rate = count / reps
    ub = cal.clopper_pearson_upper(count, reps)
    if spec.rule == cal.UPPER_BOUND_AT_MOST:
        thr = spec.fast_threshold if spec.fast_threshold is not None else FAST_RATE
        ok = rate <= thr
        # Conclusive already: the lower 95% bound lies above the full-size mark, so no
        # number of further replications can pass the cell.
        lower = float(_beta.ppf(0.05, count, reps - count + 1)) if count else 0.0
        if lower > float(spec.threshold):
            ok = False
            note = f"fails conclusively: lower 95% bound {lower:.4f} above {spec.threshold}; " + note
    elif spec.rule == cal.RATE_ABOVE:
        thr, ok = spec.threshold, rate > spec.threshold
    elif spec.rule == cal.RATE_AT_LEAST:
        thr, ok = spec.threshold, rate >= spec.threshold
    elif spec.rule == cal.ZERO:
        thr, ok = None, count == 0
    else:
        thr, ok = None, True
    note = f"FAST SUBSET: {reps} of {spec.replications} replications, fast mark; " + note
    return cal.CaseResult(o.case_id, o.cell, reps, count, rate, ub, bool(ok and not failed), spec.rule, thr, note)


def write_certificate(work: Path, path: Path = CERTIFICATE, with_properties: bool = True) -> Dict[str, Any]:
    results, summary = aggregate(work)
    if with_properties:
        install_cache()
        try:
            results += property_results(summary["aux_total"], summary["domain_reps"])
        finally:
            remove_cache()
    cert = cal.write_certificate(path, results, ROOT, BASE_SEED,
                                 created_utc=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
    rows = [r.to_dict() for r in results]
    (Path(work) / "summary.json").write_text(json.dumps({"rows": rows, "errors": summary["errors"],
                                                         "seconds": {k: v["seconds"] for k, v in summary["per"].items()},
                                                         "reps": {k: v["reps"] for k, v in summary["per"].items()}},
                                                        indent=1, sort_keys=True, default=str), encoding="utf-8")
    return cert


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m tests.test_validity_calibration",
                                 description="ADR-008 WP-98 whole-pipeline calibration")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="plan, run and (with --write) certify")
    r.add_argument("--work", type=Path, default=DEFAULT_WORK)
    r.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 2))
    r.add_argument("--full", action="store_true", default=FULL, help="every cell at ADR-008 size")
    r.add_argument("--only", default="", help="comma-separated scenario ids (prefixes allowed)")
    r.add_argument("--full-cells", default="", help="comma-separated scenario ids run at full size")
    r.add_argument("--fast-reps", type=int, default=FAST_REPS)
    r.add_argument("--write", action="store_true", help="write the certificate after the run")
    r.add_argument("--no-run", action="store_true", help="only aggregate and write")
    w = sub.add_parser("worker")
    w.add_argument("--work", type=Path, default=DEFAULT_WORK)
    sub.add_parser("list", help="list scenario ids")
    a = ap.parse_args(argv)
    if a.cmd == "worker":
        worker(a.work)
        return 0
    if a.cmd == "list":
        for sid, sc in scenarios().items():
            print(sid, sc.grid, sc.replications)
        return 0
    only = [x for x in a.only.split(",") if x]
    full_cells = [x for x in a.full_cells.split(",") if x]
    pick = lambda sid, pats: any(sid == p or sid.startswith(p) for p in pats)  # noqa: E731
    targets: Dict[str, int] = {}
    for sid, sc in scenarios().items():
        if only and not pick(sid, only):
            continue
        full = a.full or pick(sid, full_cells)
        targets[sid] = sc.replications if full else min(a.fast_reps, sc.replications)
    if not only:
        targets.update({j: 1 for j in OLD_METHOD_JOBS})
    if not a.no_run:
        n = plan_jobs(a.work, targets)
        print(f"{n} new job files; {a.workers} workers; work dir {a.work}", flush=True)
        run_workers(a.work, a.workers)
    if a.write:
        cert = write_certificate(a.work)
        failed = [(r["case_id"], r["cell"]) for r in cert["cases"] if not r["passed"]]
        print(f"certificate written: {CERTIFICATE} ({len(cert['cases'])} cells, {len(failed)} failed)")
        for f in failed:
            print("  FAILED", *f)
    return 0


# ===================================================================== pytest
def _small(sid: str, reps: int) -> Tuple[Dict[str, int], int]:
    sc = scenarios()[sid]
    ctx = Ctx(sc, Path(tempfile.mkdtemp(prefix="wp98-")))
    try:
        out = run_domain_chunk(sc, 0, reps, ctx)
    finally:
        ctx.close()
    return out["counts"], reps


def test_registry_covers_every_case():
    covered = {o.case_id for sc in scenarios().values() for o in sc.outputs}
    covered |= set(PROPERTY_CASES) | {j.split(".", 1)[1] for j in OLD_METHOD_JOBS} | {"D1"}
    assert set(cal.CASES) <= covered, sorted(set(cal.CASES) - covered)
    kinds = {(sc.outcome_type, sc.gen.split(":")[0]) for sc in scenarios().values()}
    for need in (("continuous", "normal"), ("continuous", "lognormal"), ("events", "poisson"),
                 ("events", "ns"), ("events", "season_ns"), ("flags", "garch_flags"), ("flags", "drought"),
                 ("continuous", "rain"), ("continuous", "seasonal"), ("continuous", "drift")):
        assert need in kinds, need


def test_cached_pipeline_is_byte_identical(tmp_path):
    for sid in ("B1.normal.5-5.K12", "X3.poisson0.5.rr2.0.K12", "X1.normal.daily.new_moon_like"):
        sc = scenarios()[sid]
        out = []
        for cached in (False, True):
            (install_cache if cached else remove_cache)()
            ctx = Ctx(sc, tmp_path / f"{sid}-{cached}")
            try:
                out.append([F.canonical_bytes(run_once(ctx, i)[0]["records"]) for i in range(2)])
            finally:
                ctx.close()
        remove_cache()
        assert out[0] == out[1], sid


def test_pipeline_starts_no_thread(tmp_path):
    before = {t.ident for t in threading.enumerate()}
    ctx = Ctx(scenarios()["X5.garchflags.K8"], tmp_path)
    try:
        run_once(ctx, 0)
    finally:
        ctx.close()
    assert {t.ident for t in threading.enumerate()} == before


def test_fast_subset_through_the_pipeline():
    """A few dozen replications of B1, B2 (98% zeros), X1 and X3 through run_domain (smoke + loose size)."""
    from scipy.stats import binom

    install_cache()
    try:
        for sid, reps in (("B1.normal.5-5.K18", 60), ("B2.zero_inflated.20-20.K12", 60),
                          ("X1.normal.K12", 60), ("X3.poisson2.0.rr2.0.K12", 40)):
            counts, n = _small(sid, reps)
            limit = binom.ppf(0.999, n, ALPHA)
            for key, c in counts.items():
                if key.startswith("R2N|") or key.startswith(("B", "X")):
                    assert c <= limit, (sid, key, c, n)
    finally:
        remove_cache()


def test_property_cases_hold():
    install_cache()
    try:
        for fn in (prop_x10, prop_f1, prop_f2, prop_f5, prop_f6, prop_f7, prop_z5, d1_artefact):
            r = fn()
            assert r.passed, r
    finally:
        remove_cache()


def test_certificate_is_intact_and_lists_every_case():
    cert = cal.load_certificate(CERTIFICATE)  # body hash checked
    have = {r["case_id"] for r in cert["cases"]}
    assert set(cal.CASES) <= have, sorted(set(cal.CASES) - have)
    assert cert["certified_paths"] == list(cal.CERTIFIED_PATHS)
    assert cert["env_lock_path"] == cal.ENV_LOCK_PATH and cert["seed"] == BASE_SEED


def test_begin_confirm_refuses_without_a_valid_certificate(tmp_path):
    with pytest.raises(cal.CertificateError, match="no calibration certificate"):
        cal.check_certificate(tmp_path / "absent.json", ROOT)
    repo = tmp_path / "repo"
    for rel in cal.CERTIFIED_PATHS + (cal.ENV_LOCK_PATH,):
        src = ROOT / rel
        dst = repo / rel
        if src.is_dir():
            import shutil

            shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(src.read_bytes())
    path = repo / cal.DEFAULT_CERTIFICATE_PATH
    cal.write_certificate(path, [cal.property_result("B4", "x", True)], repo, BASE_SEED)
    cal.check_certificate(path, repo)  # code and lock unchanged: holds
    with pytest.raises(cal.CertificateError, match="missing"):
        cal.check_certificate(path, repo, outcome_type="continuous")
    f = repo / "libs/vedic_astrology_core/stats/blocks.py"
    f.write_bytes(f.read_bytes() + b"\n# changed after calibration\n")
    with pytest.raises(cal.CertificateError, match="certified code changed"):
        cal.check_certificate(path, repo)


@pytest.mark.skipif(not FULL, reason="needs the full certificate (make calibrate)")
@pytest.mark.parametrize("outcome_type", cal.OUTCOME_TYPES)
def test_full_certificate_is_green(outcome_type):
    cal.check_certificate(CERTIFICATE, ROOT, outcome_type)


if __name__ == "__main__":
    sys.exit(main())
