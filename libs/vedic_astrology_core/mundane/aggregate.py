"""The aggregate pattern report and hierarchical testing (ADR-006 WP-55).

For each declared omnibus test (one partition, section 5.3.3) and each of
its cells, the report gives the columns of section 2.2: ``n_events``,
``n_active``, ``control_rate``, ``rate_ratio`` and ``ci``, ``p_matched``,
``p_shift``, ``q_family``, ``episodes``, ``stable_share``, ``placebo_rank``,
``mde`` and ``verdict``.

The statistics (plan ``statistics``):

* **Matched-set permutation (C1).** Each event and its control dates form one
  matched set. Under the null the event is exchangeable with its own controls
  and with nothing else, so one permutation picks which member plays the
  event (uniformly among that set's members). Labels never move between
  sets. Events of one cluster (closer than the C1 gap; their controls are
  aligned shifts of the whole cluster, see :mod:`.controls`) share one choice,
  which keeps their dependence; distinct clusters choose independently. The
  omnibus statistic is Pearson's chi-square of the 2 x k table (event or
  control by cell); its margins are fixed under this permutation. Every test
  uses the same permutation draws (one uniform number per cluster and
  permutation), so the Romano-Wolf step for the single best cell is computed
  from the same permutations.
* **Circular shift (C2).** The test's cell series on the daily calendar grid
  of the period is rotated by one offset shared by all tests per draw
  (``shared_offset``), keeping event clustering; statistic: chi-square of
  the events' cell counts against the grid duty.
* **Hierarchy.** The p-value of an omnibus test is ``p_matched`` (the plan's
  omnibus test); ``p_shift`` is reported beside it and never replaces it. Level 1:
  family p = smallest test p times the declared number of tests (Bonferroni),
  Benjamini-Yekutieli across the declared families. Level 2: BY over the
  declared tests of each passed family at ``alpha x passed / declared``.
  Level 3: BY over the declared cells of each passed test at the same level.
  **Denominators are always the declared counts**; a test that is
  untestable, descriptive only or missing keeps its place with p = 1
  (:class:`FamilyShrinkError` guards this).
* **Placebo rank (C3).** Rank of the real chart's omnibus statistic among the
  placebo charts' statistics (1 = most extreme; ties count against the real
  chart).

Below the event floor (30), when the plan's verdict ceiling is "descriptive
only", or when a method fails the status gate, a row is **descriptive only**:
no p-value, q-value or placebo rank is computed or printed.

Explore period only: the confirm period raises "not available until WP-63",
and every event time, control time and grid day must lie inside the explore
period (:class:`LeakageError`).

Two tables: the main table counts only events at which the test's
``needs_stable`` items are stable in the founding-time window; the second,
labelled table adds unstable events at their stated-time value. When they
disagree the main table wins.

The second half of the module turns a registry chart and events into
:class:`TestData` through the workbench predicates (one rule engine), and
simulates data for the engine calibration of section 5.3.9.
"""

from __future__ import annotations

import bisect
import csv
import json
import math
from collections import namedtuple
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple, Union

import numpy as np

from vedic_astrology_core.stats.multiplicity import benjamini_yekutieli
from vedic_astrology_core.stats.nulls import circular_shift_offsets
from vedic_astrology_core.stats.rates import rate_ratio

from .burden import Plan, PlanError, TestSpec, family_ids, mde_alpha, mde_exact, plan_tests
from .controls import ControlDraw, draw_season_matched, in_period, period_bounds

UTC = timezone.utc
REPORT_COLUMNS = ("n_events", "n_active", "control_rate", "rate_ratio", "ci", "p_matched",
                  "p_shift", "q_family", "episodes", "stable_share", "placebo_rank", "mde",
                  "verdict")
VERDICTS = ("effect found", "effect excluded", "inconclusive", "untestable", "descriptive only")
SECOND_TABLE_LABEL = ("SECOND TABLE: unstable events added at their stated-time value. "
                      "Where it disagrees with the main table, the main table wins.")
_MISSING = -1
_STATUS_RANK = {"unverified": 0, "page_cited": 1, "verified": 2}


class AggregateError(ValueError):
    """The report cannot be built as the plan says."""


class LeakageError(AggregateError):
    """Data from outside the report period reached the report."""


class FamilyShrinkError(AggregateError):
    """A family was given fewer tests (or cells) than declared."""


# ------------------------------------------------------------------ inputs
@dataclass
class TestData:
    """Everything the report needs for one declared test, already evaluated.

    Labels are cell values of the test's partition (``None`` when the
    factor cannot be evaluated at that moment). ``grid_labels`` holds one
    label per day from ``grid_start`` (the C2 calendar grid).
    ``placebo_labels`` holds, per placebo chart, the labels at the same events
    and control dates: ``(event_labels, control_labels)``.
    """

    test_id: str
    event_ids: List[str]
    event_times: List[datetime]
    event_labels: List[Any]
    event_stable: List[bool]
    control_times: List[List[datetime]]
    control_labels: List[List[Any]]
    grid_start: Optional[date] = None
    grid_labels: Optional[Sequence[Any]] = None
    placebo_labels: List[Tuple[List[Any], List[List[Any]]]] = field(default_factory=list)
    method_status: str = "unverified"
    gate_ok: bool = False
    gate_reason: str = "method status not checked"
    #: Cluster key per event (from the C1 draw); None means every event is its own cluster.
    event_clusters: Optional[List[str]] = None

    __test__ = False

    def cluster(self, i: int) -> str:
        return self.event_clusters[i] if self.event_clusters is not None else self.event_ids[i]

    def __post_init__(self) -> None:
        n = len(self.event_ids)
        lens = [len(self.event_times), len(self.event_labels), len(self.event_stable),
                len(self.control_times), len(self.control_labels)]
        if any(x != n for x in lens):
            raise AggregateError(f"{self.test_id}: event fields differ in length")
        for ts, ls in zip(self.control_times, self.control_labels):
            if len(ts) != len(ls):
                raise AggregateError(f"{self.test_id}: control times and labels differ")
        if any(not isinstance(s, bool) for s in self.event_stable):
            raise AggregateError(f"{self.test_id}: stability flags must be bools")
        if self.event_clusters is not None and len(self.event_clusters) != n:
            raise AggregateError(f"{self.test_id}: one cluster key per event is needed")


def _encode(spec: TestSpec, labels: Sequence[Any]) -> np.ndarray:
    index = {c: i for i, c in enumerate(spec.cells)}
    out = np.empty(len(labels), dtype=np.int64)
    for i, lab in enumerate(labels):
        if lab is None:
            out[i] = _MISSING
        elif lab in index:
            out[i] = index[lab]
        else:
            raise AggregateError(f"{spec.id}: label {lab!r} is not a cell of the partition")
    return out


def _f(x: Any) -> Optional[float]:
    if x is None:
        return None
    x = float(x)
    return x if math.isfinite(x) else None


# ------------------------------------------------------------- statistics
def _chi2_matched(counts: np.ndarray, totals: np.ndarray, n_sets: int, n_all: int) -> np.ndarray:
    """Pearson chi-square of the 2 x k table with fixed margins; ``counts`` is (..., k)."""
    keep = totals > 0
    n_ctrl = n_all - n_sets
    ee = n_sets * totals[keep] / n_all
    ec = n_ctrl * totals[keep] / n_all
    w = 1.0 / ee + 1.0 / ec
    d = counts[..., keep] - ee
    return (d * d * w).sum(axis=-1)


def _chi2_gof(counts: np.ndarray, duty: np.ndarray) -> np.ndarray:
    keep = duty > 0
    n = counts.sum(axis=-1, keepdims=True)
    e = n * duty[keep]
    with np.errstate(divide="ignore", invalid="ignore"):
        out = np.where(e > 0, (counts[..., keep] - e) ** 2 / np.where(e > 0, e, 1.0), 0.0)
    return out.sum(axis=-1)


def _p_greater(obs: float, null: np.ndarray) -> float:
    tol = 1e-9 * max(1.0, abs(obs))
    return float((np.sum(null >= obs - tol) + 1) / (len(null) + 1))


def _p_two_sided(obs: np.ndarray, null: np.ndarray) -> np.ndarray:
    centre = null.mean(axis=0)
    dev = np.abs(obs - centre)
    ext = np.abs(null - centre) >= dev - 1e-9
    return (ext.sum(axis=0) + 1) / (null.shape[0] + 1)


@dataclass
class _Matched:
    stat: float
    p: float
    cell_p: np.ndarray
    z_null: np.ndarray       # (P, k) standardised permutation counts
    z_obs: np.ndarray        # (k,)


def matched_permutation(event_lab: np.ndarray, control_labs: Sequence[np.ndarray], k: int,
                        u: np.ndarray) -> Optional[_Matched]:
    """Matched-set permutation test.

    ``u`` is (P, S) uniforms, one column per set. In permutation p, set s gives
    the event role to member ``floor(u[p, s] x size_s)`` of its own members
    (member 0 is the real event). Labels never leave their set. Sets of one
    cluster are given the same column of uniforms by the caller.
    Returns None when there are no control dates.
    """
    s = len(event_lab)
    sizes = np.array([1 + len(c) for c in control_labs], dtype=np.int64)
    n_all = int(sizes.sum())
    if s == 0 or n_all == s:
        return None
    m = int(sizes.max())
    mat = np.full((s, m), _MISSING, dtype=np.int64)
    mat[:, 0] = event_lab
    for i, c in enumerate(control_labs):
        mat[i, 1:1 + len(c)] = c
    members = mat[mat >= 0]
    totals = np.bincount(members, minlength=k).astype(float)
    obs = np.bincount(event_lab, minlength=k).astype(float)
    stat = float(_chi2_matched(obs, totals, s, n_all))
    n_perm = u.shape[0]
    j = np.minimum((u * sizes[None, :]).astype(np.int64), sizes[None, :] - 1)
    lab = mat.ravel()[np.arange(s)[None, :] * m + j]
    flat = (lab + k * np.arange(n_perm)[:, None]).ravel()
    counts = np.bincount(flat, minlength=n_perm * k).reshape(n_perm, k).astype(float)
    null = _chi2_matched(counts, totals, s, n_all)
    mu = counts.mean(axis=0)
    sd = counts.std(axis=0, ddof=1) if n_perm > 1 else np.zeros(k)
    sd = np.where(sd > 0, sd, np.inf)
    return _Matched(stat=stat, p=_p_greater(stat, null), cell_p=_p_two_sided(obs, counts),
                    z_null=np.abs(counts - mu) / sd, z_obs=np.abs(obs - mu) / sd)


@dataclass
class _Shift:
    stat: float
    p: float
    cell_p: np.ndarray


def shift_test(grid: np.ndarray, event_idx: np.ndarray, k: int, offsets: np.ndarray) -> Optional[_Shift]:
    """Circular-shift test of the events' cell counts against the grid duty."""
    if len(event_idx) == 0 or len(offsets) == 0:
        return None
    n = len(grid)
    valid = grid[grid >= 0]
    if valid.size == 0:
        return None
    duty = np.bincount(valid, minlength=k) / valid.size
    g = np.where(grid >= 0, grid, k)
    obs = np.bincount(g[event_idx], minlength=k + 1)[:k].astype(float)
    stat = float(_chi2_gof(obs, duty))
    lab = g[(event_idx[None, :] - offsets[:, None]) % n]
    d = len(offsets)
    flat = (lab + (k + 1) * np.arange(d)[:, None]).ravel()
    counts = np.bincount(flat, minlength=d * (k + 1)).reshape(d, k + 1)[:, :k].astype(float)
    null = _chi2_gof(counts, duty)
    return _Shift(stat=stat, p=_p_greater(stat, null), cell_p=_p_two_sided(obs, counts))


def episodes(grid: np.ndarray, k: int) -> np.ndarray:
    """Separate runs of each cell on the calendar grid (ADR-004 D-6)."""
    out = np.zeros(k, dtype=np.int64)
    if len(grid) == 0:
        return out
    starts = np.ones(len(grid), dtype=bool)
    starts[1:] = grid[1:] != grid[:-1]
    for c in range(k):
        out[c] = int(np.sum(starts & (grid == c)))
    return out


def by_q(p: Sequence[float], declared: int, what: str) -> np.ndarray:
    """BY q-values over exactly ``declared`` p-values; fewer raises."""
    if len(p) != int(declared):
        raise FamilyShrinkError(f"{what}: {len(p)} p-values for {declared} declared")
    return benjamini_yekutieli(np.asarray(p, dtype=float))


def hierarchical(p_tests: Mapping[str, Sequence[float]], declared: Mapping[str, int],
                 n_families_declared: int, alpha: float) -> Dict[str, Any]:
    """Levels 1 and 2 of the hierarchy. ``p_tests`` maps family id to its test p-values.

    Raises :class:`FamilyShrinkError` when a family or test is missing.
    """
    fams = list(p_tests)
    if len(fams) != int(n_families_declared):
        raise FamilyShrinkError(f"{len(fams)} families for {n_families_declared} declared")
    p_family = []
    for f in fams:
        m = int(declared[f])
        if len(p_tests[f]) != m:
            raise FamilyShrinkError(f"family {f}: {len(p_tests[f])} tests for {m} declared")
        p_family.append(min(1.0, min(p_tests[f]) * m))
    q1 = by_q(p_family, n_families_declared, "families")
    passed = [f for f, q in zip(fams, q1) if q < alpha]
    alpha2 = alpha * len(passed) / int(n_families_declared)
    q2 = {f: by_q(p_tests[f], declared[f], f"family {f}") for f in passed}
    return {"p_family": dict(zip(fams, p_family)), "q_level1": dict(zip(fams, q1.tolist())),
            "passed": passed, "alpha_level2": alpha2,
            "q_level2": {f: v.tolist() for f, v in q2.items()}}


# --------------------------------------------------------------- the report
@dataclass
class _Settings:
    alpha: float
    floor: int
    ceiling_descriptive: bool
    n_perm: int
    n_shift: int
    min_shift: int
    seed: int
    shift_seed: int
    mde_alpha: float
    min_episodes: int
    min_inside: float
    min_outside: float
    min_stable: float
    min_cells: int


def _settings(plan: Plan, n_perm: Optional[int], n_shift: Optional[int]) -> _Settings:
    st = plan["statistics"]
    c2 = plan["controls"]["C2_shifted_sky"]
    te = plan["testability"]
    if int(c2.get("grid_step_hours", 24)) != 24:
        raise PlanError("C2 grid_step_hours must be 24 (a daily grid)")
    if st.get("denominators") != "declared_counts":
        raise PlanError("statistics.denominators must be declared_counts")
    ceiling = str(plan["scope"].get("verdict_ceiling") or "").strip().lower()
    return _Settings(
        alpha=float(st["hierarchy"]["level_1"]["alpha"]),
        floor=int(plan["budgets"]["min_events_for_test"]),
        ceiling_descriptive=ceiling == "descriptive only",
        n_perm=int(n_perm if n_perm is not None else st["omnibus_permutations"]),
        n_shift=int(n_shift if n_shift is not None else c2["draws"]),
        min_shift=int(c2["min_shift_days"]),
        seed=int(st["omnibus_seed"]),
        shift_seed=int(c2["seed"]),
        mde_alpha=mde_alpha(plan),
        min_episodes=int(te["min_episodes"]),
        min_inside=float(te["min_expected_events_inside"]),
        min_outside=float(te["min_expected_events_outside"]),
        min_stable=float(te["min_stable_share"]),
        min_cells=2,
    )


def _check_period(td: TestData, bounds: Tuple[date, date]) -> None:
    for eid, t in zip(td.event_ids, td.event_times):
        if not in_period(t, bounds):
            raise LeakageError(f"{td.test_id}: event {eid} at {t.isoformat()} is outside the "
                               f"report period {bounds[0]} to {bounds[1]}")
    for eid, ts in zip(td.event_ids, td.control_times):
        for t in ts:
            if not in_period(t, bounds):
                raise LeakageError(f"{td.test_id}: a control date of {eid} ({t.isoformat()}) "
                                   "is outside the report period")
    if td.grid_labels is not None:
        if td.grid_start is None:
            raise AggregateError(f"{td.test_id}: grid_labels without grid_start")
        last = td.grid_start + timedelta(days=len(td.grid_labels) - 1)
        if td.grid_start < bounds[0] or last > bounds[1]:
            raise LeakageError(f"{td.test_id}: calendar grid {td.grid_start} to {last} leaves "
                               "the report period")


def _blank_row(spec: TestSpec, kind: str, cell: Any = None) -> Dict[str, Any]:
    row = {"factor_id": spec.id if kind == "omnibus" else spec.factor_id(cell),
           "test_id": spec.id, "family": spec.family, "kind": kind,
           "cell": None if kind == "omnibus" else cell,
           "predicate": spec.predicate, "methods": list(spec.methods)}
    for c in REPORT_COLUMNS:
        row[c] = None
    row.update({"testable": False, "flagged": False, "reason": "", "method_status": None,
                "family_size": None})
    return row


def _analyse(spec: TestSpec, td: Optional[TestData], s: _Settings, *, stable_only: bool,
             u_all: Optional[np.ndarray], set_index: Dict[str, int],
             offsets: Dict[int, np.ndarray]) -> Dict[str, Any]:
    """One test: its omnibus row, its cell rows and the material for the hierarchy."""
    k = len(spec.cells)
    omni = _blank_row(spec, "omnibus")
    cells = [_blank_row(spec, "cell", c) for c in spec.cells]
    res: Dict[str, Any] = {"omnibus": omni, "cells": cells, "p": 1.0, "cell_p": [1.0] * k,
                           "z_null": None, "z_obs": None}
    if td is None:
        for r in [omni] + cells:
            r["verdict"] = "untestable"
            r["reason"] = "no data supplied for this declared test; it keeps its place in the family"
        return res

    ev = _encode(spec, td.event_labels)
    ctrl = [_encode(spec, ls) for ls in td.control_labels]
    stable = np.array(td.event_stable, dtype=bool)
    share = float(stable.mean()) if len(stable) else 0.0
    include = (ev >= 0) & (stable if stable_only else np.ones(len(ev), dtype=bool))
    idx = np.flatnonzero(include)
    ev_in = ev[idx]
    ctrl_in = [ctrl[i][ctrl[i] >= 0] for i in idx]
    n = int(len(idx))
    n_ctrl = int(sum(len(c) for c in ctrl_in))
    n_active = np.bincount(ev_in, minlength=k) if n else np.zeros(k, dtype=np.int64)
    c_active = (np.bincount(np.concatenate(ctrl_in), minlength=k)
                if n_ctrl else np.zeros(k, dtype=np.int64))

    grid = _encode(spec, td.grid_labels) if td.grid_labels is not None else None
    eps = episodes(grid, k) if grid is not None else None
    if grid is not None and len(grid) and np.all(grid == grid[0]):
        from .burden import NatalFactorError
        raise NatalFactorError(f"{spec.id}: the factor never changes over the period; a purely "
                               "natal factor cannot enter a family")

    for r in [omni] + cells:
        r["n_events"] = n
        r["stable_share"] = round(share, 4)
        r["method_status"] = td.method_status
    omni["n_active"] = n
    omni["episodes"] = int(eps.sum()) if eps is not None else None

    cell_ok = []
    for c, r in enumerate(cells):
        cr = c_active[c] / n_ctrl if n_ctrl else None
        r["n_active"] = int(n_active[c])
        r["control_rate"] = _f(cr)
        r["episodes"] = int(eps[c]) if eps is not None else None
        if n and n_ctrl:
            rr = rate_ratio(int(n_active[c]), float(n), int(c_active[c]), float(n_ctrl))
            r["rate_ratio"] = _f(rr.rate_ratio)
            r["ci"] = [_f(rr.ci_low), _f(rr.ci_high)]
        if n and cr is not None and 0 < cr < 1:
            r["mde"] = _f(mde_exact(n, cr, s.mde_alpha))
        ok = (eps is not None and eps[c] >= s.min_episodes and cr is not None
              and n * cr >= s.min_inside and n * (1 - cr) >= s.min_outside)
        cell_ok.append(bool(ok))
    if n:
        omni["mde"] = _f(mde_exact(n, 1.0 / k, s.mde_alpha))

    # Testability: decided from the calendar, the controls and stability only.
    why = []
    if grid is None:
        why.append("no calendar grid")
    if share < s.min_stable:
        why.append(f"stable for {share:.0%} of events (< {s.min_stable:.0%}): founding time too coarse")
    if sum(cell_ok) < s.min_cells:
        why.append(f"{sum(cell_ok)} cell(s) pass the episode and expected-count rules (need {s.min_cells})")
    testable = not why
    omni["testable"] = testable
    for r, ok in zip(cells, cell_ok):
        r["testable"] = testable and ok

    gate = td.gate_ok
    descriptive = []
    if s.ceiling_descriptive:
        descriptive.append("plan verdict ceiling is 'descriptive only'")
    if n < s.floor:
        descriptive.append(f"{n} events, below the floor of {s.floor}")
    if not gate:
        descriptive.append(td.gate_reason or f"method status {td.method_status}")
    if descriptive:
        for r in [omni] + cells:
            r["verdict"] = "descriptive only"
            r["reason"] = "; ".join(descriptive + ([] if testable else ["untestable: " + "; ".join(why)]))
        return res
    if not testable:
        for r in [omni] + cells:
            r["verdict"] = "untestable"
            r["reason"] = "; ".join(why)
        return res

    # Tested: matched-set permutation, circular shift, placebo rank.
    cols = np.array([set_index[td.cluster(i)] for i in idx], dtype=np.int64)
    mt = matched_permutation(ev_in, ctrl_in, k, u_all[:, cols])
    sh = None
    if grid is not None:
        ev_idx = np.array([(td.event_times[i].astimezone(UTC).date() - td.grid_start).days
                           for i in idx], dtype=np.int64)
        sh = shift_test(grid, ev_idx, k, offsets[len(grid)])
    if mt is None or sh is None:
        for r in [omni] + cells:
            r["verdict"] = "untestable"
            r["reason"] = "no control dates" if mt is None else "circular shift not possible"
        omni["testable"] = False
        return res
    omni["p_matched"] = mt.p
    omni["p_shift"] = sh.p
    res["p"] = mt.p
    if td.placebo_labels:
        stats = []
        for pe, pc in td.placebo_labels:
            pev = _encode(spec, pe)[idx]
            pctrl = [_encode(spec, pc[i]) for i in idx]
            keep = pev >= 0
            pctrl = [c[c >= 0] for c, kp in zip(pctrl, keep) if kp]
            pev = pev[keep]
            if len(pev) == 0:
                continue
            members = np.concatenate([pev] + pctrl)
            tot = np.bincount(members, minlength=k).astype(float)
            stats.append(float(_chi2_matched(np.bincount(pev, minlength=k).astype(float), tot,
                                              len(pev), len(members))))
        if stats:
            omni["placebo_rank"] = 1 + int(sum(1 for x in stats if x >= mt.stat - 1e-12))
    for c, r in enumerate(cells):
        if r["testable"]:
            r["p_matched"] = float(mt.cell_p[c])
            r["p_shift"] = float(sh.cell_p[c])
            res["cell_p"][c] = float(mt.cell_p[c])
    tested = [c for c in range(k) if cells[c]["testable"]]
    res["z_null"] = mt.z_null[:, tested]
    res["z_obs"] = mt.z_obs[tested]
    res["tested_cells"] = tested
    for r in [omni] + cells:
        r["verdict"] = "inconclusive"
        r["reason"] = "explore period: a result can only be confirmed in the confirm run (WP-63)"
    for r in cells:
        if not r["testable"]:
            r["verdict"] = "untestable"
            r["reason"] = "cell fails the episode or expected-count rule; kept in the omnibus test only"
        elif r["ci"] and r["ci"][1] is not None and r["mde"] is not None and r["ci"][1] < r["mde"]:
            r["verdict"] = "effect excluded"
            r["reason"] = "upper end of the rate-ratio interval is below the test's mde"
    if all(cells[c]["verdict"] == "effect excluded" for c in tested):
        omni["verdict"] = "effect excluded"
        omni["reason"] = "every testable cell excludes an effect of the detectable size"
    return res


def _table(plan: Plan, specs: List[TestSpec], data: Mapping[str, TestData], s: _Settings,
           *, stable_only: bool, u_all, set_index, offsets) -> Dict[str, Any]:
    results = {sp.id: _analyse(sp, data.get(sp.id), s, stable_only=stable_only, u_all=u_all,
                               set_index=set_index, offsets=offsets) for sp in specs}
    fams = family_ids(plan)
    declared = dict(plan["declared_counts"]["by_family"])
    n_fam = int(plan["declared_counts"]["families"])
    by_family = {f: [sp for sp in specs if sp.family == f] for f in fams}
    for f in fams:
        if len(by_family[f]) != int(declared.get(f, -1)):
            raise FamilyShrinkError(f"family {f}: {len(by_family[f])} tests, {declared.get(f)} declared")
    h = hierarchical({f: [results[sp.id]["p"] for sp in by_family[f]] for f in fams},
                     declared, n_fam, s.alpha)
    any_tested = any(r["omnibus"]["p_matched"] is not None for r in results.values())
    for f in fams:
        for i, sp in enumerate(by_family[f]):
            res = results[sp.id]
            omni = res["omnibus"]
            omni["family_size"] = int(declared[f])
            for r in res["cells"]:
                r["family_size"] = len(sp.cells)
            if omni["p_matched"] is None:
                continue
            if f not in h["passed"]:
                omni["reason"] += "; family did not pass level 1"
                continue
            q2 = h["q_level2"][f][i]
            omni["q_family"] = q2
            omni["flagged"] = bool(q2 < h["alpha_level2"])
            if not omni["flagged"]:
                continue
            q3 = by_q(res["cell_p"], len(sp.cells), f"test {sp.id}")
            for c, r in enumerate(res["cells"]):
                if r["testable"]:
                    r["q_family"] = float(q3[c])
                    r["flagged"] = bool(q3[c] < h["alpha_level2"])
    families = [{"family": f, "declared_tests": int(declared[f]),
                 "p_family": h["p_family"][f] if any_tested else None,
                 "q_level1": h["q_level1"][f] if any_tested else None,
                 "passed": f in h["passed"]} for f in fams]
    best = None
    zs = [(sp.id, results[sp.id]) for sp in specs if results[sp.id].get("z_null") is not None
          and results[sp.id]["z_null"].shape[1] > 0]
    if zs:
        max_null = np.max(np.column_stack([r["z_null"].max(axis=1) for _, r in zs]), axis=1)
        tid, r = max(zs, key=lambda x: float(x[1]["z_obs"].max()))
        c = r["tested_cells"][int(np.argmax(r["z_obs"]))]
        sp = next(x for x in specs if x.id == tid)
        obs = float(r["z_obs"].max())
        best = {"factor_id": sp.factor_id(sp.cells[c]), "z": obs,
                "p_romano_wolf": float((np.sum(max_null >= obs - 1e-9) + 1) / (len(max_null) + 1))}
    tests = [results[sp.id]["omnibus"] for sp in specs]
    factors = [r for sp in specs for r in results[sp.id]["cells"]]
    return {"families": families, "alpha_level2": h["alpha_level2"] if any_tested else None,
            "tests": tests, "factors": factors, "best_factor": best,
            "any_flag": any(f["passed"] for f in families) if any_tested else False}


def build_report(plan: Plan, data: Mapping[str, TestData], *, period: str = "explore",
                 n_perm: Optional[int] = None, n_shift: Optional[int] = None,
                 provisional: bool = True, chart_id: Optional[str] = None,
                 second_table: bool = True) -> Dict[str, Any]:
    """The aggregate pattern report for one chart, explore period only."""
    bounds = period_bounds(plan, period)  # confirm raises "not available until WP-63"
    specs = plan_tests(plan)
    declared_ids = [sp.id for sp in specs]
    extra = sorted(set(data) - set(declared_ids))
    if extra:
        raise AggregateError(f"data for undeclared tests {extra}: only declared tests are reported")
    for td in data.values():
        _check_period(td, bounds)
    s = _settings(plan, n_perm, n_shift)

    all_ids = sorted({e for td in data.values() for e in td.event_ids})
    keys = sorted({td.cluster(i) for td in data.values() for i in range(len(td.event_ids))})
    set_index = {k: i for i, k in enumerate(keys)}
    rng = np.random.default_rng(s.seed)
    u_all = rng.random((s.n_perm, max(1, len(keys))))
    offsets: Dict[int, np.ndarray] = {}
    for td in data.values():
        if td.grid_labels is not None and len(td.grid_labels) not in offsets:
            n = len(td.grid_labels)
            if n - 2 * s.min_shift + 1 >= 1:
                offsets[n] = circular_shift_offsets(n, s.min_shift, s.n_shift,
                                                    np.random.default_rng([s.shift_seed, n]))
            else:
                offsets[n] = np.empty(0, dtype=np.int64)

    main = _table(plan, specs, data, s, stable_only=True, u_all=u_all, set_index=set_index,
                  offsets=offsets)
    n_total = len(all_ids)
    report: Dict[str, Any] = {
        "schema": "mundane-report/1",
        "plan_id": plan["id"],
        "plan_sha256": plan.sha256,
        "chart_id": chart_id,
        "period": period,
        "period_bounds": [bounds[0].isoformat(), bounds[1].isoformat()],
        "label": plan["periods"].get("label"),
        "provisional": bool(provisional),
        "n_events_total": n_total,
        "event_floor": s.floor,
        "descriptive_only": all(r["verdict"] == "descriptive only" for r in main["tests"]),
        "family_size_declared": dict(plan["declared_counts"]["by_family"]),
        "omnibus_tests_declared": len(specs),
        "settings": {"alpha": s.alpha, "n_perm": s.n_perm, "n_shift": s.n_shift,
                     "min_shift_days": s.min_shift, "mde_alpha": s.mde_alpha,
                     "hierarchy_p": "p_matched", "n_clusters": len(keys)},
        "columns": list(REPORT_COLUMNS),
        "main": main,
    }
    if second_table:
        sec = _table(plan, specs, data, s, stable_only=False, u_all=u_all, set_index=set_index,
                     offsets=offsets)
        sec["label"] = SECOND_TABLE_LABEL
        report["second"] = sec
        dis = []
        for a, b in zip(main["tests"], sec["tests"]):
            if (a["verdict"], a["flagged"]) != (b["verdict"], b["flagged"]):
                dis.append({"test_id": a["test_id"], "main": [a["verdict"], a["flagged"]],
                            "second": [b["verdict"], b["flagged"]], "wins": "main"})
        report["disagreements"] = dis
    report["headline"] = summary_lines(report)
    return _jsonable(report)


def summary_lines(report: Dict[str, Any]) -> List[str]:
    """Short text for the CLI. Under the floor it says "descriptive only" and prints no p-value."""
    m = report["main"]
    lines = [f"{report['plan_id']} ({report['period']}, {report.get('label')}): "
             f"{report['n_events_total']} events"]
    if report["descriptive_only"]:
        lines.append("descriptive only: no test statistic or p-value is reported")
        return lines
    for f in m["families"]:
        lines.append(f"{f['family']}: {'passed' if f['passed'] else 'not passed'} at level 1")
    return lines


def _jsonable(x: Any) -> Any:
    if isinstance(x, dict):
        return {k: _jsonable(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_jsonable(v) for v in x]
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (np.floating, float)):
        v = float(x)
        return v if math.isfinite(v) else None
    if isinstance(x, np.bool_):
        return bool(x)
    if isinstance(x, np.ndarray):
        return _jsonable(x.tolist())
    return x


FACTOR_TABLE_FIELDS = ["table", "kind", "factor_id", "test_id", "family", "cell"] + list(REPORT_COLUMNS) + [
    "testable", "flagged", "family_size", "method_status", "reason"]


def factor_rows(report: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Every row, winners and losers: omnibus rows and cell rows of both tables."""
    out = []
    for name in ("main", "second"):
        if name not in report:
            continue
        for r in report[name]["tests"] + report[name]["factors"]:
            row = {k: r.get(k) for k in FACTOR_TABLE_FIELDS if k != "table"}
            row["table"] = name
            if isinstance(row["ci"], list):
                row["ci"] = "" if row["ci"][0] is None and row["ci"][1] is None else \
                    f"[{row['ci'][0]}, {row['ci'][1]}]"
            out.append(row)
    return out


def write_report(report: Dict[str, Any], results_path: Union[str, Path],
                 factor_table_path: Union[str, Path]) -> Tuple[Path, Path]:
    rp, fp = Path(results_path), Path(factor_table_path)
    rp.parent.mkdir(parents=True, exist_ok=True)
    fp.parent.mkdir(parents=True, exist_ok=True)
    rp.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with fp.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FACTOR_TABLE_FIELDS, lineterminator="\n")
        w.writeheader()
        w.writerows(factor_rows(report))
    return rp, fp


# ======================================================= real charts (rules)
def method_gate(spec: TestSpec, plan: Plan, catalogue=None) -> Tuple[bool, str, str]:
    """(gate_ok, weakest status, reason) for an explore test (plan ``method_gate``)."""
    from .catalogue import load_catalogue

    cat = catalogue or load_catalogue()
    allowed = set(plan["method_gate"]["explore_test"])
    tiers = set(plan["method_gate"]["tiers_allowed_in_families"])
    statuses, problems = [], []
    for mid in spec.methods:
        m = cat.get(mid)  # an uncatalogued method raises
        st = m.citation_status(cat.root)
        statuses.append(st)
        if m.tier not in tiers:
            problems.append(f"{mid} is tier {m.tier}")
        if st not in allowed:
            problems.append(f"{mid} is {st}")
    weakest = min(statuses, key=lambda x: _STATUS_RANK[x]) if statuses else "unverified"
    reason = ("method status " + weakest + " (" + "; ".join(problems) + ")") if problems else ""
    return (not problems), weakest, reason


class _Evaluator:
    """Evaluates test cells through the workbench predicates for one natal chart."""

    def __init__(self, chart, specs: Sequence[TestSpec]):
        from vedic_astrology_core.dasha.vimshottari import compute_vimshottari_nested_periods
        from vedic_astrology_core.rules.context import Location, Sky
        from vedic_astrology_core.rules.predicates import PREDICATES

        from .charts import chart_moment

        self.chart = chart
        self.natal = Sky(chart_moment(chart), Location(chart.lat, chart.lon, "UTC"))
        self._periods = {}
        self._starts = {}
        for level in (1, 2, 3):
            ps = compute_vimshottari_nested_periods(self.natal.moment, self.natal.lon("Moon"),
                                                    depth=level)
            self._periods[level] = ps
            self._starts[level] = [p["start"] for p in ps]
        self._models: Dict[Tuple[str, Any], Any] = {}
        self._pred = PREDICATES
        for sp in specs:
            model = PREDICATES[sp.predicate].params
            if sp.collapse is not None:
                for raw in sp.priority:
                    self._models[(sp.id, raw)] = model.model_validate({**sp.params, sp.param_name: [raw]})
            else:
                for c in sp.cells:
                    self._models[(sp.id, c)] = model.model_validate(sp.cell_params(c))

    def chain(self, moment: datetime, level: int) -> Tuple[str, ...]:
        starts = self._starts[level]
        i = bisect.bisect_right(starts, moment) - 1
        if i >= 0:
            p = self._periods[level][i]
            if p["start"] <= moment < p["end"]:
                return tuple(p["lords"])
        from vedic_astrology_core.rules.context import MissingInputError

        raise MissingInputError("the moment is outside the 120-year Vimshottari cycle")

    def context(self, moment: datetime):
        from vedic_astrology_core.rules.context import EvalContext, Sky

        ev = self

        class _Ctx(EvalContext):
            def dasha_chain(self, level: int):  # noqa: D401 - same contract, cached lookup
                return ev.chain(self.sky.moment, level)

        return _Ctx(Sky(moment.astimezone(UTC)), self.natal)

    def label(self, ctx, spec: TestSpec) -> Any:
        func = self._pred[spec.predicate].func
        if spec.collapse is not None:
            for raw in spec.priority:
                if func(ctx, self._models[(spec.id, raw)]).held:
                    return next(c for c, v in spec.collapse.items() if raw in v)
            return None
        held = [c for c in spec.cells if func(ctx, self._models[(spec.id, c)]).held]
        if len(held) > 1:
            raise AggregateError(f"{spec.id}: cells {held} hold at once; not a partition")
        return held[0] if held else None

    def labels(self, moment: datetime, specs: Sequence[TestSpec]) -> Dict[str, Any]:
        ctx = self.context(moment)
        return {sp.id: self.label(ctx, sp) for sp in specs}


_STABILITY_KEYS = ("maha", "antar", "pratyantar", "d1_lagna", "d9_lagna", "moon_d1_sign",
                   "lord_d1_sign", "lord_d9_sign")


def stability_flags(chart, event, specs: Sequence[TestSpec], *, founding=None,
                    catalogue=None) -> Dict[str, bool]:
    """Per test: are all its ``needs_stable`` items stable for this chart and event?"""
    from .dasha import dasha_at_event
    from .stability import event_half_window, founding_table_stability

    founding = founding if founding is not None else founding_table_stability(
        chart, ("D1", "D9"), catalogue=catalogue)
    da = dasha_at_event(chart, event.time_utc, depth=3,
                        event_half_window_minutes=event_half_window(event), catalogue=catalogue)

    def ok(key: Tuple[str, str, str]) -> bool:
        st = founding.get(key)
        return bool(st is not None and st.stable)

    out = {}
    for sp in specs:
        flags = []
        for item in sp.needs_stable:
            if item not in _STABILITY_KEYS:
                raise AggregateError(f"{sp.id}: unknown needs_stable item {item!r}")
            if item in ("maha", "antar", "pratyantar"):
                lv = da.level({"maha": 1, "antar": 2, "pratyantar": 3}[item])
                flags.append(bool(lv.supported and lv.stable))
            elif item == "d1_lagna":
                flags.append(ok(("Lagna", "D1", "sign")))
            elif item == "d9_lagna":
                flags.append(ok(("Lagna", "D9", "sign")))
            elif item == "moon_d1_sign":
                flags.append(ok(("Moon", "D1", "sign")))
            else:
                level = int(sp.params.get("level", 1))
                lv = da.level(level)
                varga = "D1" if item == "lord_d1_sign" else "D9"
                flags.append(bool(lv.supported and lv.stable and lv.lord is not None
                                  and ok((lv.lord, varga, "sign"))))
        out[sp.id] = all(flags)
    return out


def collect_test_data(plan: Plan, chart, events: Sequence[Any], draw: ControlDraw, *,
                      catalogue=None, grid: bool = True, placebos: Sequence[Any] = (),
                      specs: Optional[Sequence[TestSpec]] = None) -> Dict[str, TestData]:
    """Evaluate every declared test for ``chart`` at the events, their controls and the grid.

    Events must be exhaustive and must all have a control draw. The grid is one
    evaluation per day at 00:00 UTC over the draw's period.
    """
    from .catalogue import load_catalogue
    from .stability import founding_table_stability

    cat = catalogue or load_catalogue()
    specs = list(specs or plan_tests(plan))
    for e in events:
        if not getattr(e, "exhaustive", False):
            raise AggregateError(f"{e.event_id}: not exhaustive; hand-picked events get case files only")
        if e.event_id not in draw.controls:
            raise AggregateError(f"{e.event_id}: no control draw")
    ev = _Evaluator(chart, specs)
    founding = founding_table_stability(chart, ("D1", "D9"), catalogue=cat)
    ev_labels = [ev.labels(e.time_utc, specs) for e in events]
    flags = [stability_flags(chart, e, specs, founding=founding, catalogue=cat) for e in events]
    ctrl_times = [list(draw.controls[e.event_id]) for e in events]
    ctrl_labels = [[ev.labels(t, specs) for t in ts] for ts in ctrl_times]
    grid_start = grid_vals = None
    if grid:
        start, end = draw.period
        days = (end - start).days + 1
        grid_start = start
        grid_vals = [ev.labels(datetime.combine(start + timedelta(days=i), time(0), UTC), specs)
                     for i in range(days)]
    pl = []
    for pc in placebos:
        pev = _Evaluator(pc, specs)
        pl.append(([pev.labels(e.time_utc, specs) for e in events],
                   [[pev.labels(t, specs) for t in ts] for ts in ctrl_times]))
    out = {}
    for sp in specs:
        ok, status, reason = method_gate(sp, plan, cat)
        out[sp.id] = TestData(
            test_id=sp.id,
            event_ids=[e.event_id for e in events],
            event_times=[e.time_utc for e in events],
            event_labels=[x[sp.id] for x in ev_labels],
            event_stable=[f[sp.id] for f in flags],
            control_times=ctrl_times,
            control_labels=[[x[sp.id] for x in row] for row in ctrl_labels],
            grid_start=grid_start,
            grid_labels=[g[sp.id] for g in grid_vals] if grid_vals is not None else None,
            placebo_labels=[([x[sp.id] for x in a], [[y[sp.id] for y in row] for row in b])
                            for a, b in pl],
            method_status=status, gate_ok=ok, gate_reason=reason,
            event_clusters=[draw.cluster_of.get(e.event_id, e.event_id) for e in events],
        )
    return out


# ============================================================ calibration
_SimEvent = namedtuple("_SimEvent", "event_id time_utc")
#: Mean run length in days of the simulated drivers (rough real values).
_SIM_RUN_DAYS = {"level2": 550.0, "level3": 60.0, "level1": 2500.0,
                 "Mars": 45.0, "Jupiter": 365.0, "Saturn": 900.0, "Rahu": 550.0,
                 "Sun": 30.0, "Moon": 2.3, "Mercury": 30.0, "Venus": 30.0, "Ketu": 550.0}


def _runs(rng: np.random.Generator, n_days: int, n_states: int, mean: float,
          reverse: bool = False) -> np.ndarray:
    """A cyclic state series with run lengths around ``mean`` days."""
    out = np.empty(n_days, dtype=np.int64)
    state = int(rng.integers(n_states))
    i = -int(rng.integers(0, max(1, int(mean))))
    while i < n_days:
        length = max(1, int(round(rng.gamma(4.0, mean / 4.0))))
        lo, hi = max(i, 0), min(i + length, n_days)
        if hi > lo:
            out[lo:hi] = state
        i += length
        state = (state + (-1 if reverse else 1)) % n_states
    return out


def simulate_test_data(plan: Plan, rng: np.random.Generator, *, n_events: int,
                       cluster_mean: float = 0.0, cluster_days: int = 20,
                       planted: Optional[Tuple[str, Any, float]] = None,
                       specs: Optional[Sequence[TestSpec]] = None) -> Dict[str, TestData]:
    """Synthetic explore-period data with the plan's tests, for engine calibration.

    Dasha-like tests share one lord series per level (runs of about 550 days
    for antar, 60 for pratyantar) mapped to cells by a random natal placement;
    transit tests get their own cyclic house series. Events are uniform days
    (no effect) or weighted by ``rr`` inside one planted cell
    (``planted = (test_id, cell, rr)``; cell None picks the cell that holds the
    most days). With ``cluster_mean > 0`` each
    parent event gets Poisson(cluster_mean) offspring within ``cluster_days``.
    Controls come from the real C1 draw. Methods are marked as passing the gate.
    """
    specs = list(specs or plan_tests(plan))
    start, end = period_bounds(plan, "explore")
    n_days = (end - start).days + 1
    lords = {lv: _runs(rng, n_days, 9, _SIM_RUN_DAYS[f"level{lv}"]) for lv in (1, 2, 3)}
    labels: Dict[str, np.ndarray] = {}
    for sp in specs:
        k = len(sp.cells)
        if sp.predicate.startswith("dasha_lord") or sp.predicate == "antardasha_lord_is":
            base = lords[int(sp.params.get("level", 1))]
            mapping = np.arange(9) if sp.predicate == "dasha_lord_is" else rng.integers(0, k, size=9)
            labels[sp.id] = mapping[base] % k
        else:
            planet = str(sp.params.get("planet", "Mars"))
            labels[sp.id] = _runs(rng, n_days, k, _SIM_RUN_DAYS.get(planet, 100.0),
                                  reverse=planet in ("Rahu", "Ketu"))
    # Events (day indices), kept away from the period edges by the C1 gap.
    gap = int(math.ceil(float(plan["controls"]["C1_season_matched"]["min_gap_days_from_any_event"])))
    weights = np.ones(n_days)
    weights[:gap] = 0
    weights[n_days - gap:] = 0
    if planted is not None:
        tid, cell, rr = planted
        sp = next(x for x in specs if x.id == tid)
        if cell is None:  # the cell that holds the most days
            ci = int(np.argmax(np.bincount(labels[tid], minlength=len(sp.cells))))
        else:
            ci = sp.cells.index(cell)
        weights = weights * np.where(labels[tid] == ci, float(rr), 1.0)
    weights = weights / weights.sum()
    days: List[int] = []
    while len(days) < n_events:
        d0 = int(rng.choice(n_days, p=weights))
        days.append(d0)
        if cluster_mean > 0:
            for _ in range(int(rng.poisson(cluster_mean))):
                d = d0 + int(rng.integers(1, cluster_days + 1))
                if d < n_days - gap and len(days) < n_events:
                    days.append(d)
    days.sort()
    events = []
    for i, d in enumerate(days):
        t = datetime.combine(start + timedelta(days=d), time(0), UTC) + timedelta(
            seconds=int(rng.integers(0, 86400)))
        events.append(_SimEvent(f"sim:{i:04d}", t))
    draw = draw_season_matched(events, plan, period="explore")
    out = {}
    for sp in specs:
        lab = labels[sp.id]
        cells = sp.cells

        def at(t: datetime) -> Any:
            return cells[int(lab[(t.astimezone(UTC).date() - start).days])]

        out[sp.id] = TestData(
            test_id=sp.id,
            event_ids=[e.event_id for e in events],
            event_times=[e.time_utc for e in events],
            event_labels=[at(e.time_utc) for e in events],
            event_stable=[True] * len(events),
            control_times=[draw.controls[e.event_id] for e in events],
            control_labels=[[at(t) for t in draw.controls[e.event_id]] for e in events],
            grid_start=start,
            grid_labels=[cells[int(x)] for x in lab],
            method_status="verified", gate_ok=True, gate_reason="",
            event_clusters=[draw.cluster_of[e.event_id] for e in events],
        )
    return out


__all__ = [
    "AggregateError", "FACTOR_TABLE_FIELDS", "FamilyShrinkError", "LeakageError",
    "REPORT_COLUMNS", "SECOND_TABLE_LABEL", "TestData", "VERDICTS", "build_report", "by_q",
    "collect_test_data", "episodes", "factor_rows", "hierarchical", "matched_permutation",
    "method_gate", "shift_test", "simulate_test_data", "stability_flags", "summary_lines",
    "write_report",
]
