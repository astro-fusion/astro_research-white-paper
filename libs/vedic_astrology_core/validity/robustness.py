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
      statistic) / (n + 1) <= 0.05, "larger" in the claimed direction (|T| for
      two-sided). Ties never count against the real sky.
    * With no applicable placebo at all R2 is "not computable" and does not
      pass (the conservative reading: a check that could not run cannot
      clear a Supported).

R3 Sensitivity grid (section 5, F-07)
    Counts **distinct calendars**: a cell counts only if it changes at least
    5% of the active bars against the primary. R3 passes when the statistic has
    the claimed sign (two-sided: the primary's sign) in at least 80% of the
    distinct cells. With no distinct cell R3 is "not applicable" and passes:
    the declared grid offered no different calendar, so it cannot show the
    effect to be fragile.

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
    "RobustnessError",
    "Placebo",
    "R2Result",
    "Cell",
    "R3Result",
    "CheckResult",
    "RobustnessResult",
    "changed_share",
    "time_shift_plan",
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


def time_shift_plan(season_linked: bool, rng: Optional[np.random.Generator] = None,
                    n: int = N_TIME_SHIFT) -> Dict[str, Any]:
    """The time-shift placebo skies of one test (section 5, section 6.1 item 3).

    Season-linked: whole-year shifts -100..-1 and 1..100 (exactly 200, no
    randomness), so the Sun and the season stay in place. Otherwise n distinct
    day offsets with 400 <= |offset| <= 3650 from rng (the test's own
    "placebo" stream, ADR-008 3.5).
    """
    if season_linked:
        if n != N_TIME_SHIFT:
            raise RobustnessError("season-linked calendars use the 200 whole-year shifts")
        return {"kind": "whole_year", "unit": "years", "shifts": _season.whole_year_shifts()}
    if not isinstance(rng, np.random.Generator):
        raise RobustnessError("day-offset placebos need the test's own placebo stream (rng)")
    if int(n) < 1:
        raise RobustnessError("n must be at least 1")
    pool = np.concatenate([np.arange(MIN_OFFSET_DAYS, MAX_OFFSET_DAYS + 1),
                           -np.arange(MIN_OFFSET_DAYS, MAX_OFFSET_DAYS + 1)])
    shifts = rng.choice(pool, size=int(n), replace=False)
    return {"kind": "random_offset", "unit": "days", "shifts": [int(s) for s in shifts]}


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

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["check"] = "R2"
        d["applicable_kinds"] = list(self.applicable_kinds)
        d["not_applicable_kinds"] = list(self.not_applicable_kinds)
        return d


def r2_placebo(real_statistic: float, placebos: Iterable[Placebo], side: str) -> R2Result:
    """R2 for one test on its own statistic T (section 5).

    A kind applies when its skies change, on average, at least 1% of the
    active bars; otherwise it is "not applicable" and none of its skies is
    counted. Every sky of an applicable kind counts (a sky equal to the real
    one is a tie and ties never count against the real sky). Then
    p = (1 + #strictly larger) / (n + 1) and R2 passes at p <= 0.05.
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
    applicable, not_applicable = [], []
    for kind in sorted(by_kind):
        skies = by_kind[kind]
        if float(np.mean([float(p.changed_share) for p in skies])) >= MIN_PLACEBO_CHANGE:
            applicable.append(kind)
            used.extend(float(p.statistic) for p in skies)
        else:
            not_applicable.append(kind)
    n = len(used)
    if n == 0:
        return R2Result(False, "not_computable", None, 0, 0, 0, tuple(applicable), tuple(not_applicable),
                        real, side)
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
    p = (1 + k) / (n + 1)
    ok = p <= R2_LEVEL + 1e-15
    return R2Result(ok, "pass" if ok else "fail", p, n, k, int(tied.sum()), tuple(applicable),
                    tuple(not_applicable), real, side)


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
        return R3Result(True, "not_applicable", len(cells), 0, 0, None, (),
                        tuple(c.name for c in copies))
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
