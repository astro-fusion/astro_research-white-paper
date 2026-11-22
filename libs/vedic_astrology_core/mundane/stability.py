"""The stability check of ADR-006 section 3.4 (WP-51).

A factor is evaluated at the stated founding time, at both ends of the
founding-time window and on a grid inside it whose spacing is at most one
minute (grade D: ten minutes; ``studies/mundane/hypothesis.yaml``
``stability.founding_grid_minutes``). The factor is **stable** only if every
evaluation gives the same value. Otherwise it is unstable, and the result lists
every value it takes with the share of the window it holds; change points
between grid samples are located by bisection to about one second.

Guarantee and limit: any value the factor holds for one grid step or longer is
seen. A value held for less than one step can be missed only if the factor
changes and changes back between two samples; lagna-based factors move one way
and cannot do that.

The same machinery serves the event side (a fast transit evaluated across the
event's own time window, section 3.4 last paragraph) through
:func:`check_event`.

Dasha stability is not computed here: the dasha shift is monotonic, so
:mod:`vedic_astrology_core.mundane.dasha` evaluates the two window ends exactly.

All datetimes must be timezone-aware; a naive one raises ``ValueError``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, Hashable, List, Mapping, Optional, Sequence, Tuple

from ..utils.datetime_utils import require_aware
from .catalogue import Catalogue, load_catalogue
from .charts import DEFAULT_VARGAS, FoundingTable, chart_moment, founding_table
from .registry import Chart, Event, RegistryError, chart_grade, half_window_minutes

#: Grid spacing in minutes per grade (hypothesis.yaml, stability.founding_grid_minutes).
FOUNDING_GRID_MINUTES = {"A": 1.0, "B": 1.0, "C": 1.0, "D": 10.0, "R": 1.0}
#: Event half-window in minutes by time precision (hypothesis.yaml,
#: events.event_time_window). "month" is excluded.
EVENT_HALF_WINDOW_MINUTES = {"minute": 1.0, "hour": 30.0, "day": 720.0}
#: A test needs the factor stable for at least this share of events (section 3.4 rule 5).
MIN_STABLE_SHARE = 0.80
#: Bisection stops when the bracket is this short.
REFINE_SECONDS = 1.0


@dataclass(frozen=True)
class ValueShare:
    """One value a factor takes inside the window and the share of the window it holds."""

    value: Any
    share: float


@dataclass(frozen=True)
class Stability:
    """Outcome of the check for one factor."""

    key: Hashable
    stable: bool
    stated_value: Any
    values: List[ValueShare]
    change_points: List[datetime] = field(default_factory=list)
    window: Tuple[datetime, datetime] = None  # type: ignore[assignment]
    step_minutes: float = 1.0
    n_samples: int = 0

    @property
    def alternatives(self) -> List[Any]:
        """Values other than the stated one (empty when stable)."""
        return [v.value for v in self.values if v.value != self.stated_value]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key if isinstance(self.key, (str, int)) else list(self.key),
            "stable": self.stable,
            "stated_value": self.stated_value,
            "values": [{"value": v.value, "share": v.share} for v in self.values],
            "change_points": [t.isoformat() for t in self.change_points],
            "window": [t.isoformat() for t in self.window] if self.window else None,
            "step_minutes": self.step_minutes,
            "n_samples": self.n_samples,
        }


# ------------------------------------------------------------------ helpers
def _aware(dt: datetime, name: str) -> datetime:
    require_aware(dt, name)  # NaiveDatetimeError is a ValueError
    return dt.astimezone(timezone.utc)


def _freeze(value: Any) -> Any:
    """Make a value comparable and hashable (lists to tuples, dicts to sorted tuples)."""
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(v) for v in value)
    if isinstance(value, set):
        return tuple(sorted(_freeze(v) for v in value))
    if isinstance(value, dict):
        return tuple(sorted((k, _freeze(v)) for k, v in value.items()))
    return value


def window_grid(
    center: datetime, half_window_minutes: float, step_minutes: float = 1.0
) -> List[datetime]:
    """Both window ends, the centre, and evenly spaced points no more than ``step`` apart."""
    c = _aware(center, "center")
    if half_window_minutes < 0:
        raise ValueError("half_window_minutes must be >= 0")
    if step_minutes <= 0:
        raise ValueError("step_minutes must be > 0")
    if half_window_minutes == 0:
        return [c]
    n = max(1, math.ceil(2.0 * half_window_minutes / step_minutes - 1e-9))
    lo = c - timedelta(minutes=half_window_minutes)
    width = timedelta(minutes=2.0 * half_window_minutes)
    pts = {lo + width * (i / n) for i in range(n + 1)}
    pts.add(c)
    return sorted(pts)


def check_many(
    evaluate: Callable[[datetime], Mapping[Hashable, Any]],
    center: datetime,
    half_window_minutes: float,
    step_minutes: float = 1.0,
    *,
    refine_seconds: float = REFINE_SECONDS,
) -> Dict[Hashable, Stability]:
    """Run the check on every factor that ``evaluate(moment)`` returns.

    ``evaluate`` maps a moment to {factor key: value}. Every key must be present
    at every moment (a factor that disappears raises).
    """
    c = _aware(center, "center")
    grid = window_grid(c, half_window_minutes, step_minutes)
    cache: Dict[datetime, Dict[Hashable, Any]] = {}

    def at(t: datetime) -> Dict[Hashable, Any]:
        if t not in cache:
            cache[t] = {k: _freeze(v) for k, v in dict(evaluate(t)).items()}
        return cache[t]

    samples = [at(t) for t in grid]
    keys = list(samples[0])
    for t, s in zip(grid, samples):
        if list(s) != keys and set(s) != set(keys):
            raise ValueError(f"factor keys change at {t.isoformat()}")
    stated = at(c)
    lo, hi = grid[0], grid[-1]
    total = (hi - lo).total_seconds()
    tol = timedelta(seconds=refine_seconds)

    out: Dict[Hashable, Stability] = {}
    for key in keys:
        vals = [s[key] for s in samples]
        if all(v == vals[0] for v in vals):
            out[key] = Stability(
                key=key, stable=True, stated_value=stated[key],
                values=[ValueShare(stated[key], 1.0)], change_points=[],
                window=(lo, hi), step_minutes=step_minutes, n_samples=len(grid),
            )
            continue
        # Segments: (start, value); change points refined by bisection.
        changes: List[Tuple[datetime, Any]] = []
        for i in range(1, len(grid)):
            if vals[i] == vals[i - 1]:
                continue
            a, b = grid[i - 1], grid[i]
            va = vals[i - 1]
            while b - a > tol:
                m = a + (b - a) / 2
                if at(m)[key] == va:
                    a = m
                else:
                    b = m
            changes.append((b, vals[i]))
        held: Dict[Any, float] = {}
        order: List[Any] = []
        seg_start, seg_val = lo, vals[0]
        for when, new_val in changes + [(hi, None)]:
            if seg_val not in held:
                held[seg_val] = 0.0
                order.append(seg_val)
            held[seg_val] += (when - seg_start).total_seconds()
            seg_start, seg_val = when, new_val
        shares = [ValueShare(v, held[v] / total if total else 0.0) for v in order]
        out[key] = Stability(
            key=key, stable=False, stated_value=stated[key], values=shares,
            change_points=[w for w, _ in changes], window=(lo, hi),
            step_minutes=step_minutes, n_samples=len(cache),
        )
    return out


def check(
    evaluate: Callable[[datetime], Any],
    center: datetime,
    half_window_minutes: float,
    step_minutes: float = 1.0,
    *,
    key: Hashable = "factor",
    refine_seconds: float = REFINE_SECONDS,
) -> Stability:
    """Run the check on one factor; ``evaluate(moment)`` returns its value."""
    return check_many(
        lambda t: {key: evaluate(t)}, center, half_window_minutes, step_minutes,
        refine_seconds=refine_seconds,
    )[key]


# ------------------------------------------------------------ founding side
def founding_grid_minutes(chart: Chart) -> float:
    """Grid spacing for a chart's grade (1 minute; grade D 10 minutes)."""
    grade = chart_grade(chart)
    if grade not in FOUNDING_GRID_MINUTES:
        raise RegistryError(f"{chart.chart_id}: grade {grade} has no founding-time window")
    return FOUNDING_GRID_MINUTES[grade]


def _founding_window(chart: Chart, half_window: Optional[float], step: Optional[float]):
    hw = half_window if half_window is not None else half_window_minutes(chart)
    if hw is None:
        raise RegistryError(f"{chart.chart_id}: grade X (date disputed) is excluded")
    st = step if step is not None else founding_grid_minutes(chart)
    if st > FOUNDING_GRID_MINUTES.get(chart_grade(chart), 1.0):
        raise ValueError(f"step {st} min is coarser than the grade allows")
    return chart_moment(chart), float(hw), float(st)


def check_founding(
    chart: Chart,
    evaluate: Callable[[datetime], Any],
    *,
    half_window: Optional[float] = None,
    step_minutes: Optional[float] = None,
    key: Hashable = "factor",
) -> Stability:
    """Check one factor of ``chart`` across its founding-time window.

    ``evaluate(moment)`` gets a founding moment (aware, UTC). The centre is the
    stated founding time, or local noon for a date-only chart.
    """
    c, hw, st = _founding_window(chart, half_window, step_minutes)
    return check(evaluate, c, hw, st, key=key)


def founding_table_stability(
    chart: Chart,
    vargas: Sequence[str] = DEFAULT_VARGAS,
    *,
    half_window: Optional[float] = None,
    step_minutes: Optional[float] = None,
    catalogue: Optional[Catalogue] = None,
) -> Dict[Tuple[str, str, str], Stability]:
    """Stability of every cell of the founding table.

    Keys are ``(point, varga, field)`` with field ``sign``, ``house``,
    ``dignity`` or ``hora_lord`` (only the fields the table fills). A date-only
    chart has no lagna and no houses, as in :func:`founding_table`.
    """
    cat = catalogue or load_catalogue()
    c, hw, st = _founding_window(chart, half_window, step_minutes)

    def cells(t: datetime) -> Dict[Tuple[str, str, str], Any]:
        table: FoundingTable = founding_table(chart, vargas, moment=t, catalogue=cat)
        out: Dict[Tuple[str, str, str], Any] = {}
        for row in table.points:
            for name, p in row.vargas.items():
                out[(row.point, name, "sign")] = p.sign_name
                if p.house is not None:
                    out[(row.point, name, "house")] = p.house
                if p.dignity is not None:
                    out[(row.point, name, "dignity")] = p.dignity
                if p.hora_lord is not None:
                    out[(row.point, name, "hora_lord")] = p.hora_lord
        return out

    return check_many(cells, c, hw, st)


# --------------------------------------------------------------- event side
def event_half_window(
    event: Event, minutes_by_precision: Optional[Mapping[str, float]] = None
) -> float:
    """The event's own half-window in minutes; month precision is excluded (raises)."""
    table = dict(minutes_by_precision or EVENT_HALF_WINDOW_MINUTES)
    if event.time_precision not in table:
        raise RegistryError(
            f"{event.event_id}: time precision {event.time_precision!r} is excluded"
        )
    return float(table[event.time_precision])


def check_event(
    event: Event,
    evaluate: Callable[[datetime], Any],
    *,
    step_minutes: float = 1.0,
    key: Hashable = "factor",
    minutes_by_precision: Optional[Mapping[str, float]] = None,
) -> Stability:
    """Check an event-time factor across the event's own time window."""
    hw = event_half_window(event, minutes_by_precision)
    return check(evaluate, _aware(event.time_utc, "time_utc"), hw, step_minutes, key=key)


# ---------------------------------------------------------------- aggregate
def stable_share(flags: Sequence[bool]) -> float:
    """Share of events at which a factor is stable; an empty list gives 0.0."""
    flags = list(flags)
    if any(not isinstance(f, bool) for f in flags):
        raise TypeError("stability flags must be bools (None is not 'stable')")
    return sum(flags) / len(flags) if flags else 0.0


def testable_by_stability(flags: Sequence[bool], min_share: float = MIN_STABLE_SHARE) -> bool:
    """Section 3.4 rule 5: a factor stable for under ``min_share`` of events is untestable."""
    return bool(flags) and stable_share(flags) >= min_share


__all__ = [
    "EVENT_HALF_WINDOW_MINUTES",
    "FOUNDING_GRID_MINUTES",
    "MIN_STABLE_SHARE",
    "Stability",
    "ValueShare",
    "check",
    "check_event",
    "check_founding",
    "check_many",
    "event_half_window",
    "founding_grid_minutes",
    "founding_table_stability",
    "stable_share",
    "testable_by_stability",
    "window_grid",
]
