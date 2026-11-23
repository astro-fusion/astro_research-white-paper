"""Robustness checks R1 to R4: the contract of ADR-008 section 5 (A-01, F-07).

Work package WP-94. Re-specifies the robustness part of ADR-007 WP-69 (5.3).
Every check here is computed **per test**, on that test's own statistic T
(the primary block statistic of core/stats/blocks.py). Nothing is a maximum
over indicators, so adding a second test leaves the first test's R2
byte-identical.

R1 Baselines (ADR-007 5.3, 7.3)
    The primary test is the one **with** the domain's baselines. R1 passes when
    the with-baselines statistic lies in the claimed direction (two-sided: is
    not zero) and its p-value is at or below 0.05. The card shows both rows,
    with and without the socially mediated baselines (A-09):
    baseline_rows().

R2 Placebo skies (section 5)
    * Per test, on T only.
    * A placebo kind applies only if it changes at least 1% of the test's
      active bars (changed share = bars whose state differs between the real
      and the placebo calendar, over the real calendar's active bars).
      Otherwise the kind is "not applicable", never "failed".
    * The tropical zodiac is a rival system: it is refused here and belongs to
      the sensitivity grid.
    * Time-shift placebos: 200 skies. Season-linked calendars use whole-year
      shifts k = 1 to 100 in both directions; others random day offsets of at
      least 400 days (time_shift_plan()).
    * R2 passes when (1 + number of applicable placebos with a strictly larger
      statistic + half the number of tied ones) / (n + 1) <= 0.05, "larger"
      in the claimed direction (|T| for two-sided). Mid-rank ties (second
      strategy audit N-06 ii): a placebo sky that is a different calendar and
      ties the real statistic counts one half; only a sky identical to the
      real calendar (changed share 0) does not count. The old rule ("ties
      never count") let a real sky tied with 150 of 200 skies pass at
      p = 0.005, and event and flag statistics tie often.
    * CALIBRATION-FIX (WP-98 W1, Z3), two outcome-free rules on the skies:
      (a) Overlap. A shifted sky is a valid placebo only if it carries less
          than MAX_PLACEBO_OVERLAP (0.5) of a steady effect on the real
          active bars: placebo_overlap() is the placebo's own statistic T
          computed on the real calendar's 0/1 indicator, i.e. the share of
          real active bars among the placebo's active bars minus that share
          among its control bars, and its absolute value must be below 0.5.
          A periodic calendar shifted by about a whole period otherwise
          re-tests the real calendar (W1: 39 of 200 skies shared over half
          the active bars and carried the planted effect), and an anti-phase
          sky (negative overlap) is anti-correlated with the real statistic
          and makes a null real sky look extreme. Why 0.5: a valid placebo's
          mean under a steady effect e is below e/2, so at the W1 effect
          (twice the gate's minimal detectable effect) the real sky leads
          every valid placebo by more than the minimal detectable effect
          itself. A smaller bound is not safer: it removes the real sky's
          near neighbours, which share its luckiest bars, and so breaks the
          exchangeability the rank needs (measured, 10,000 null runs, 98%-
          zero bars 5/50 K=12: R2 passed in 5.61% at 0.25, failing the 0.06
          bound, and in 5.26% at 0.5; W1 power was 0.89 to 0.97 at 0.25 and
          0.91 to 0.97 at 0.5). A rejected sky is replaced by a fresh day offset
          from the same stream (up to MAX_PLACEBO_CANDIDATES draws); whole-
          year skies are a fixed set and are not replaced. The rejected
          count is recorded.
      (b) Distinct calendars. Valid skies are grouped greedily, in draw
          order, into distinct calendars: a sky is a new calendar when it
          differs from every earlier one in at least 1% of the real active
          bars (MIN_PLACEBO_CHANGE: the change that makes a sky differ from
          the real one at all, applied between skies; a periodic calendar
          shifted by whole periods differs only at the grid edges and
          collapses into one calendar). With m distinct
          calendars the rank of the real sky is resolved only to 1/(m + 1):
          near-copies of one calendar must not count as many placebos (Z3:
          about 20 distinct yearly offsets, each drawn about ten times,
          passed R2 in 9% to 11.5% of null runs). So each distinct calendar
          counts once: p = (1 + sum over distinct calendars of the share of
          its skies with a strictly larger statistic) / (m + 1). The smallest
          attainable p is then 1/(m + 1), which reaches the pass mark 0.05
          only for m >= 19 = MIN_DISTINCT_PLACEBOS. Fewer gives status
          "insufficient_placebos": R2 does not pass, so the test cannot be
          Supported (the conservative reading), and the record says why.
    * CALIBRATION-FIX: R2 does not pass when the real statistic is not in the
      claimed direction (0 or the wrong sign; two-sided: 0). Ties never count
      against the real sky, so a real T of exactly 0 (all blocks constant on
      a 98%-zero outcome) tied with most skies and passed R2 in about 4% of
      null runs (WP-98 R2N, B2 zero_inflated).
    * With no applicable placebo at all R2 is "not computable" and does not
      pass (the conservative reading: a check that could not run cannot
      clear a Supported).

R3 Sensitivity grid (section 5, F-07)
    Counts **distinct calendars**: a cell counts only if it changes at least
    5% of the active bars against the primary. R3 passes when the statistic has
    the claimed sign (two-sided: the primary's sign) in at least 80% of the
    distinct cells. With no distinct cell (including an empty grid) R3 has
    status "not_run" (second strategy audit N-18: it was "not_applicable",
    which read as a check that ran and found nothing wrong). It still does not
    block the verdict, because the grid offered no different calendar to
    show the effect fragile; the record carries the reason so the card can
    say the check was not run.

R4 Separability (section 6.1 item 5)
    baseline_r2 of the calendar on all the domain's baselines; fails at 0.5 or
    above (core/stats/season.py r4_passes()).

No outcome is read here; callers pass statistics. No thread, no network.
"""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

import numpy as np

from ..stats import blocks as _blocks
from ..stats import season as _season

__all__ = [
    "PLACEBO_KINDS",
    "RIVAL_SYSTEMS",
    "N_TIME_SHIFT",
    "MIN_PLACEBO_CHANGE",
    "MIN_DISTINCT_CHANGE",
    "R1_LEVEL",
    "R2_LEVEL",
    "R3_SAME_SIGN_SHARE",
    "MIN_OFFSET_DAYS",
    "MAX_OFFSET_DAYS",
    "MAX_PLACEBO_OVERLAP",
    "MIN_DISTINCT_PLACEBOS",
    "MAX_PLACEBO_CANDIDATES",
    "R2_INSUFFICIENT",
    "R3_NOT_RUN",
    "YEARLY_GRID_MIN_SPACING_DAYS",
    "is_yearly_grid",
    "RobustnessError",
    "Placebo",
    "R2Result",
    "Cell",
    "R3Result",
    "CheckResult",
    "RobustnessResult",
    "changed_share",
    "time_shift_plan",
    "more_offsets",
    "placebo_overlap",
    "count_distinct",
    "distinct_clusters",
    "r1_baselines",
    "baseline_rows",
    "r2_placebo",
    "r3_sensitivity",
    "r4_separability",
    "robustness",
]

#: Placebo kinds R2 accepts. "time_shift" covers whole-year and day-offset skies.
PLACEBO_KINDS: Tuple[str, ...] = ("time_shift", "scramble")
#: Rival systems: never a placebo, only a sensitivity cell (section 5).
RIVAL_SYSTEMS: Tuple[str, ...] = ("tropical",)
#: Number of time-shift skies (section 5).
N_TIME_SHIFT = 200
#: A placebo kind applies when it changes at least this share of active bars.
MIN_PLACEBO_CHANGE = 0.01
#: A sensitivity cell is a distinct calendar at or above this share (F-07).
MIN_DISTINCT_CHANGE = 0.05
#: R1: the with-baselines p must be at or below this.
R1_LEVEL = 0.05
#: R2 pass mark on (1 + larger) / (n + 1).
R2_LEVEL = 0.05
#: R3: share of distinct cells with the claimed sign.
R3_SAME_SIGN_SHARE = 0.8
#: Day offsets of time-shift placebos for calendars that are not season-linked.
MIN_OFFSET_DAYS = 400
MAX_OFFSET_DAYS = 3650
#: CALIBRATION-FIX (a): a sky is a valid placebo only if |placebo_overlap| is below this
#: (it carries less than half of a steady effect on the real active bars).
MAX_PLACEBO_OVERLAP = 0.5
#: CALIBRATION-FIX (b): distinct valid placebo calendars R2 needs: 1/(m+1) <= R2_LEVEL.
MIN_DISTINCT_PLACEBOS = 19
#: Day offsets tried at most per test (the first N_TIME_SHIFT plus replacements).
MAX_PLACEBO_CANDIDATES = 10 * N_TIME_SHIFT
#: R2 status when fewer than MIN_DISTINCT_PLACEBOS distinct calendars exist.
R2_INSUFFICIENT = "insufficient_placebos"
#: R3 status when no declared cell is a distinct calendar (N-18).
R3_NOT_RUN = "not_run"
#: N-07: a grid whose median bar spacing is at least this many days is yearly;
#: its time-shift skies are whole years (k = 1 to 100 both ways), because day
#: offsets of at most MAX_OFFSET_DAYS give only about 20 distinct yearly skies.
YEARLY_GRID_MIN_SPACING_DAYS = 360.0

_SIDES = ("greater", "less", "two-sided")


class RobustnessError(ValueError):
    """A placebo or cell outside the contract (for example a tropical placebo)."""


def _side(side: str) -> str:
    if side not in _SIDES:
        raise RobustnessError(f"side must be one of {_SIDES} (there is no default side)")
    return side


def _finite(x: Any, what: str) -> float:
    v = float(x)
    if not math.isfinite(v):
        raise RobustnessError(f"{what} must be finite, got {x!r}")
    return v


def _tol(x: float) -> float:
    return 1e-12 * max(1.0, abs(x))


# --------------------------------------------------------------- calendars
def changed_share(primary, other) -> float:
    """Bars whose state differs between two calendars, over the primary's active bars.

    0 when nothing changed. A primary with no active bar gives inf when
    anything changed (any change is total) and 0 otherwise.
    """
    a = np.asarray(primary, dtype=bool).ravel()
    b = np.asarray(other, dtype=bool).ravel()
    if a.shape != b.shape:
        raise RobustnessError("calendars must have the same number of bars")
    diff = int(np.sum(a != b))
    n = int(a.sum())
    if n == 0:
        return math.inf if diff else 0.0
    return diff / n


def is_yearly_grid(dates) -> bool:
    """True for a grid with one bar a year or fewer (median spacing >= 360 days; plain years)."""
    arr = np.asarray(dates)
    if arr.dtype.kind in "iu":
        return True  # plain years
    if len(arr) < 2:
        return False
    ns = np.asarray(arr, dtype="datetime64[ns]").astype(np.int64)
    return bool(np.median(np.diff(ns)) >= YEARLY_GRID_MIN_SPACING_DAYS * 86_400 * 10**9)


def time_shift_plan(season_linked: bool, rng: Optional[np.random.Generator] = None,
                    n: int = N_TIME_SHIFT, *, dates=None) -> Dict[str, Any]:
    """The time-shift placebo skies of one test (section 5, section 6.1 item 3).

    Season-linked: whole-year shifts -100..-1 and 1..100 (exactly 200, no
    randomness), so the Sun and the season stay in place. Otherwise n distinct
    day offsets with 400 <= |offset| <= 3650 from rng (the test's own
    "placebo" stream, ADR-008 3.5).

    N-07: with the grid `dates` given, a yearly grid (:func:`is_yearly_grid`)
    also gets the 200 whole-year shifts. Day offsets capped at 3,650 days
    move a yearly grid by at most ten years, about 20 distinct skies, so R2
    could never pass for slow calendars (Saturn in fire: 18, Rahu in dual
    signs: 15) while the gate said "can support".
    """
    if season_linked or (dates is not None and is_yearly_grid(dates)):
        if n != N_TIME_SHIFT:
            raise RobustnessError("season-linked calendars and yearly grids use the 200 whole-year shifts")
        return {"kind": "whole_year", "unit": "years", "shifts": _season.whole_year_shifts()}
    if not isinstance(rng, np.random.Generator):
        raise RobustnessError("day-offset placebos need the test's own placebo stream (rng)")
    if int(n) < 1:
        raise RobustnessError("n must be at least 1")
    pool = np.concatenate([np.arange(MIN_OFFSET_DAYS, MAX_OFFSET_DAYS + 1),
                           -np.arange(MIN_OFFSET_DAYS, MAX_OFFSET_DAYS + 1)])
    shifts = rng.choice(pool, size=int(n), replace=False)
    return {"kind": "random_offset", "unit": "days", "shifts": [int(s) for s in shifts]}


def _offset_pool() -> np.ndarray:
    return np.concatenate([np.arange(MIN_OFFSET_DAYS, MAX_OFFSET_DAYS + 1),
                           -np.arange(MIN_OFFSET_DAYS, MAX_OFFSET_DAYS + 1)])


def more_offsets(rng: np.random.Generator, used: Iterable[int], n: int) -> List[int]:
    """Up to n fresh day offsets not in ``used``, from the same placebo stream (replacements)."""
    if not isinstance(rng, np.random.Generator):
        raise RobustnessError("replacement offsets need the test's own placebo stream (rng)")
    pool = _offset_pool()
    pool = pool[~np.isin(pool, np.asarray(sorted(set(int(u) for u in used)), dtype=np.int64))]
    k = min(int(n), len(pool))
    if k < 1:
        return []
    return [int(s) for s in rng.choice(pool, size=k, replace=False)]


def placebo_overlap(placebo_design, real_calendar) -> float:
    """Share of a steady effect on the real active bars that a placebo's statistic carries.

    The placebo's own block statistic T computed on the real calendar's 0/1
    indicator: (real active share of its active bars) minus (real active
    share of its control bars), weighted as T is. 1 for the real calendar
    itself, about 0 for an unrelated sky, negative for an anti-phase sky.
    Outcome-free (calendar only). NaN when the placebo has no used block.
    """
    a = np.asarray(real_calendar, dtype=bool).ravel().astype(float)
    if placebo_design.n_used == 0:
        return float("nan")
    return float(_blocks.block_differences(placebo_design, a, outcome_type="continuous").statistic)


def distinct_clusters(masks: Iterable[Any], n_real_active: int) -> List[int]:
    """Distinct-calendar id of every placebo mask, greedily in order (CALIBRATION-FIX b).

    A mask opens a new distinct calendar when it differs from every earlier
    representative in at least MIN_PLACEBO_CHANGE (1%) of the real calendar's
    active bars; otherwise it joins the first representative it is that close
    to. Ids are 0, 1, ... in order of first appearance.
    """
    reps: List[np.ndarray] = []
    exact: Dict[bytes, int] = {}
    ids: List[int] = []
    denom = max(int(n_real_active), 1)
    for m in masks:
        m = np.asarray(m, dtype=bool).ravel()
        key = np.packbits(m).tobytes() + str(len(m)).encode()
        if key in exact:
            ids.append(exact[key])
            continue
        cid = next((j for j, r in enumerate(reps)
                    if np.count_nonzero(m != r) / denom < MIN_PLACEBO_CHANGE), None)
        if cid is None:
            cid = len(reps)
            reps.append(m)
        exact[key] = cid
        ids.append(cid)
    return ids


def count_distinct(masks: Iterable[Any], n_real_active: int) -> int:
    """Number of distinct calendars among placebo masks (see distinct_clusters)."""
    ids = distinct_clusters(masks, n_real_active)
    return (max(ids) + 1) if ids else 0


# ---------------------------------------------------------------------- R1
@dataclass(frozen=True)
class CheckResult:
    """One of R1 and R4: passes, status and the numbers behind it."""

    check: str
    passes: bool
    status: str  # "pass", "fail", "not_applicable" or "not_computable"
    detail: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {"check": self.check, "passes": self.passes, "status": self.status, "detail": dict(self.detail)}


def _in_direction(t: float, side: str) -> bool:
    if side == "greater":
        return t > 0
    if side == "less":
        return t < 0
    return t != 0


def r1_baselines(statistic_with: float, p_with: float, side: str) -> CheckResult:
    """R1: with the domain's baselines the statistic keeps the claimed sign and p <= 0.05."""
    side = _side(side)
    t = _finite(statistic_with, "statistic")
    p = _finite(p_with, "p-value")
    if not 0.0 <= p <= 1.0:
        raise RobustnessError("p-value outside [0, 1]")
    ok = _in_direction(t, side) and p <= R1_LEVEL
    return CheckResult("R1", ok, "pass" if ok else "fail",
                       {"statistic_with_baselines": t, "p_with_baselines": p, "side": side})


def baseline_rows(with_baselines: Mapping[str, Any], without_baselines: Mapping[str, Any],
                  channel: Optional[str] = None) -> Dict[str, Any]:
    """The two card rows of section 7.3: with (primary) and without the social baselines."""
    return {
        "primary": "with_baselines",
        "tested_claim": "beyond_channel" if channel else "with_baselines",
        "channel": channel,
        "with_baselines": dict(with_baselines),
        "without_baselines": dict(without_baselines),
    }


# ---------------------------------------------------------------------- R2
@dataclass(frozen=True)
class Placebo:
    """One placebo sky of one test: its kind, T on it and how much it changed the calendar."""

    kind: str
    statistic: float
    changed_share: float
    label: str = ""
    #: CALIBRATION-FIX: id of the distinct calendar this sky belongs to (distinct_clusters).
    cluster: Optional[int] = None


@dataclass(frozen=True)
class R2Result:
    passes: bool
    status: str
    p_value: Optional[float]
    n_placebo: int
    n_larger: int
    n_tied: int
    applicable_kinds: Tuple[str, ...]
    not_applicable_kinds: Tuple[str, ...]
    real_statistic: float
    side: str
    #: CALIBRATION-FIX: distinct valid calendars (None: not given by the caller).
    n_distinct: Optional[int] = None
    #: Skies rejected because |placebo_overlap| >= MAX_PLACEBO_OVERLAP.
    n_rejected_overlap: int = 0
    #: Shifts tried in all (valid, rejected and without a used block).
    n_candidates: Optional[int] = None
    #: Plain words for a status other than pass or fail.
    reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["check"] = "R2"
        d["min_distinct"] = MIN_DISTINCT_PLACEBOS
        d["max_overlap"] = MAX_PLACEBO_OVERLAP
        d["applicable_kinds"] = list(self.applicable_kinds)
        d["not_applicable_kinds"] = list(self.not_applicable_kinds)
        return d


def r2_placebo(real_statistic: float, placebos: Iterable[Placebo], side: str, *,
               n_distinct: Optional[int] = None, n_rejected_overlap: int = 0,
               n_candidates: Optional[int] = None) -> R2Result:
    """R2 for one test on its own statistic T (section 5).

    A kind applies when its skies change, on average, at least 1% of the
    active bars; otherwise it is "not applicable" and none of its skies is
    counted. Every sky of an applicable kind counts (a sky equal to the real
    one is a tie and ties never count against the real sky). Then
    p = (1 + #strictly larger) / (n + 1) and R2 passes at p <= 0.05.

    ``placebos`` must already be the valid skies (overlap rule (a), applied by
    the caller before any outcome is read). ``n_distinct`` is their number of
    distinct calendars (count_distinct); below MIN_DISTINCT_PLACEBOS the
    status is "insufficient_placebos" and R2 does not pass, whatever p is.
    When every sky carries its ``cluster`` id, each distinct calendar counts
    once: p = (1 + sum_c larger_c / size_c) / (m + 1) with m distinct
    calendars, and ``n_larger`` reports the unweighted count. The pipeline
    always passes both; None (direct callers, unit tests) skips the rule and
    the weighting.
    """
    side = _side(side)
    real = _finite(real_statistic, "real statistic")
    by_kind: Dict[str, List[Placebo]] = {}
    for pl in placebos:
        if pl.kind in RIVAL_SYSTEMS:
            raise RobustnessError(f"{pl.kind!r} is a rival system: it goes to the sensitivity grid, not R2")
        if pl.kind not in PLACEBO_KINDS:
            raise RobustnessError(f"unknown placebo kind {pl.kind!r}; expected one of {PLACEBO_KINDS}")
        _finite(pl.statistic, "placebo statistic")
        if not float(pl.changed_share) >= 0.0:
            raise RobustnessError("changed_share must be non-negative")
        by_kind.setdefault(pl.kind, []).append(pl)
    used: List[float] = []
    shares: List[float] = []
    clusters: List[Optional[int]] = []
    applicable, not_applicable = [], []
    for kind in sorted(by_kind):
        skies = by_kind[kind]
        if float(np.mean([float(p.changed_share) for p in skies])) >= MIN_PLACEBO_CHANGE:
            applicable.append(kind)
            used.extend(float(p.statistic) for p in skies)
            shares.extend(float(p.changed_share) for p in skies)
            clusters.extend((kind, p.cluster) if p.cluster is not None else None for p in skies)
        else:
            not_applicable.append(kind)
    n = len(used)
    extra = {"n_distinct": None if n_distinct is None else int(n_distinct),
             "n_rejected_overlap": int(n_rejected_overlap),
             "n_candidates": None if n_candidates is None else int(n_candidates)}
    if n == 0:
        return R2Result(False, "not_computable", None, 0, 0, 0, tuple(applicable), tuple(not_applicable),
                        real, side, reason="no valid placebo sky", **extra)
    arr = np.asarray(used, dtype=float)
    eps = _tol(real)
    if side == "greater":
        larger = arr > real + eps
    elif side == "less":
        larger = arr < real - eps
    else:
        larger = np.abs(arr) > abs(real) + eps
    if side == "two-sided":
        tied = np.abs(np.abs(arr) - abs(real)) <= eps
    else:
        tied = np.abs(arr - real) <= eps
    k = int(larger.sum())
    # N-06 (ii): mid-rank ties. A sky that ties the real statistic but is a
    # different calendar counts one half (it is as extreme as the real sky);
    # only a sky identical to the real one (changed share 0) does not count.
    score = larger.astype(float) + 0.5 * (tied & ~larger & (np.asarray(shares) > 0.0))
    p = (1.0 + float(score.sum())) / (n + 1)
    if n_distinct is not None and all(c is not None for c in clusters):
        groups: Dict[Any, List[int]] = {}
        for i, c in enumerate(clusters):
            groups.setdefault(c, []).append(i)
        m = len(groups)
        p = (1.0 + sum(float(score[ix].mean()) for ix in groups.values())) / (m + 1)
    if n_distinct is not None and int(n_distinct) < MIN_DISTINCT_PLACEBOS:
        why = (f"only {int(n_distinct)} distinct placebo calendars (at least {MIN_DISTINCT_PLACEBOS} "
               "are needed); the placebo check cannot clear a Supported")
        return R2Result(False, R2_INSUFFICIENT, p, n, k, int(tied.sum()), tuple(applicable),
                        tuple(not_applicable), real, side, reason=why, **extra)
    if not _in_direction(real, side):
        # CALIBRATION-FIX: a real statistic of exactly 0 (every block constant, as
        # for a 98%-zero outcome) tied with most skies and "passed", because ties
        # never count against the real sky. A sky that shows no effect in the
        # claimed direction cannot stand out from the placebos.
        return R2Result(False, "fail", p, n, k, int(tied.sum()), tuple(applicable), tuple(not_applicable),
                        real, side, reason="the real statistic is not in the claimed direction", **extra)
    ok = p <= R2_LEVEL + 1e-15
    return R2Result(ok, "pass" if ok else "fail", p, n, k, int(tied.sum()), tuple(applicable),
                    tuple(not_applicable), real, side, **extra)


# ---------------------------------------------------------------------- R3
@dataclass(frozen=True)
class Cell:
    """One declared sensitivity cell: its name, T on it and its changed share."""

    name: str
    statistic: float
    changed_share: float


@dataclass(frozen=True)
class R3Result:
    passes: bool
    status: str
    n_cells: int
    n_distinct: int
    n_same_sign: int
    same_sign_share: Optional[float]
    distinct: Tuple[str, ...]
    near_copies: Tuple[str, ...]
    #: Plain words for status "not_run".
    reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["check"] = "R3"
        d["distinct"] = list(self.distinct)
        d["near_copies"] = list(self.near_copies)
        return d


def r3_sensitivity(primary_statistic: float, cells: Iterable[Cell], side: str) -> R3Result:
    """R3 over distinct calendars only (a cell changing >= 5% of active bars)."""
    side = _side(side)
    t0 = _finite(primary_statistic, "primary statistic")
    cells = list(cells)
    distinct = [c for c in cells if float(c.changed_share) >= MIN_DISTINCT_CHANGE]
    copies = [c for c in cells if float(c.changed_share) < MIN_DISTINCT_CHANGE]
    if not distinct:
        why = ("no declared sensitivity cell" if not cells else
               f"none of the {len(cells)} declared cells changes at least {MIN_DISTINCT_CHANGE:.0%} "
               "of the active bars")
        return R3Result(True, R3_NOT_RUN, len(cells), 0, 0, None, (),
                        tuple(c.name for c in copies), reason=why + "; the sensitivity check was not run")
    if side == "two-sided":
        ref = 1.0 if t0 > 0 else (-1.0 if t0 < 0 else 0.0)
        same = [c for c in distinct if ref != 0.0 and np.sign(_finite(c.statistic, "cell")) == ref]
    else:
        same = [c for c in distinct if _in_direction(_finite(c.statistic, "cell"), side)]
    share = len(same) / len(distinct)
    ok = share >= R3_SAME_SIGN_SHARE - 1e-15
    return R3Result(ok, "pass" if ok else "fail", len(cells), len(distinct), len(same), share,
                    tuple(c.name for c in distinct), tuple(c.name for c in copies))


# ---------------------------------------------------------------------- R4
def r4_separability(baseline_r2_value: float) -> CheckResult:
    """R4: baseline_r2 below 0.5 passes (section 6.1 item 5)."""
    v = _finite(baseline_r2_value, "baseline_r2")
    ok = _season.r4_passes(v)
    return CheckResult("R4", ok, "pass" if ok else "fail",
                       {"baseline_r2": v, "max": _season.R4_MAX_BASELINE_R2})


# ---------------------------------------------------------------- together
@dataclass(frozen=True)
class RobustnessResult:
    """R1 to R4 of one test. A missing check counts as not passed."""

    r1: Optional[CheckResult]
    r2: Optional[R2Result]
    r3: Optional[R3Result]
    r4: Optional[CheckResult]

    def passed(self) -> Dict[str, bool]:
        return {
            "R1": bool(self.r1 is not None and self.r1.passes),
            "R2": bool(self.r2 is not None and self.r2.passes),
            "R3": bool(self.r3 is not None and self.r3.passes),
            "R4": bool(self.r4 is not None and self.r4.passes),
        }

    def failed(self) -> Tuple[str, ...]:
        return tuple(k for k, v in self.passed().items() if not v)

    @property
    def all_pass(self) -> bool:
        return not self.failed()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "R1": None if self.r1 is None else self.r1.to_dict(),
            "R2": None if self.r2 is None else self.r2.to_dict(),
            "R3": None if self.r3 is None else self.r3.to_dict(),
            "R4": None if self.r4 is None else self.r4.to_dict(),
            "passed": self.passed(),
        }

    def to_bytes(self) -> bytes:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"), default=float).encode()


def robustness(*, r1: Optional[CheckResult] = None, r2: Optional[R2Result] = None,
               r3: Optional[R3Result] = None, r4: Optional[CheckResult] = None) -> RobustnessResult:
    """Bundle the four checks of one test."""
    return RobustnessResult(r1, r2, r3, r4)
