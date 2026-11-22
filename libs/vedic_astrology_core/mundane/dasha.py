"""Vimshottari dasha at an event, with founding-time boundary intervals (ADR-006 WP-51).

For one registry chart and one event instant this returns the maha, antar and
pratyantar lords (levels 1 to 3), each with its start and end at the stated
founding time, the interval each boundary can occupy inside the chart's
founding-time window, and a stability mark.

How the window is handled (ADR-006 sections 3.2 and 3.4):

* The Vimshottari timeline is a function of the Moon's longitude at the
  founding moment. Moving the founding time moves the Moon, and that slides the
  *whole* timeline by one amount (it is continuous even when the Moon crosses a
  nakshatra edge). The slide is monotonic in the founding time, so evaluating
  both ends of the window is exact.
* A level is **stable** only when (a) the running lords to that level are the
  same at the stated time and at both window ends, and (b) neither boundary
  interval of the running period contains the event (edges count as inside).
  Both tests must pass; if they ever disagree the level is unstable. A level
  below an unstable level is unstable too.
* The event's own time uncertainty (optional ``event_half_window_minutes``)
  widens the event to an interval; any overlap with a boundary interval is
  unstable.
* Grade D (date only) supports no dasha level: every level is returned with
  ``supported=False``, ``stable=False`` and no lord. Grade X is refused.

All datetimes must be timezone-aware; a naive one raises ``ValueError``.

``boundary_uncertainty_days`` is the larger distance, in days, that a boundary
moves between the stated time and either window end (a "plus or minus" figure,
as in the table of section 3.2).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from ..dasha.vimshottari import (
    DEFAULT_DASHA_YEAR,
    VIMSHOTTARI_SEQUENCE,
    VIMSHOTTARI_YEARS,
    VimshottariPeriodDict,
    YearLike,
    compute_vimshottari_nested_periods,
    elapsed_fraction,
    get_vimshottari_start_lord,
    year_length_days,
)
from ..rules.context import Sky
from ..utils.datetime_utils import require_aware
from .catalogue import Catalogue, load_catalogue
from .charts import chart_moment
from .registry import Chart, RegistryError, chart_applies, chart_grade, half_window_minutes

METHOD_ID = "dasha.vimshottari"
MAX_DEPTH = 3
LEVEL_NAMES = {1: "maha", 2: "antar", 3: "pratyantar"}
#: Degrees in one nakshatra (13 deg 20').
NAKSHATRA_SPAN = 360.0 / 27.0
UNSUPPORTED_REASON = "date-only chart (grade D): no dasha level is supported (ADR-006 3.2)"


class DashaWindowError(RegistryError):
    """The dasha cannot be read for this chart and event (event inside the window)."""


@dataclass(frozen=True)
class DashaLevel:
    """One dasha level running at the event."""

    level: int
    name: str
    lord: Optional[str]
    lords: Optional[Tuple[str, ...]]
    start: Optional[datetime]
    end: Optional[datetime]
    #: (earliest, latest) instant the start boundary can take inside the window.
    start_interval: Optional[Tuple[datetime, datetime]]
    end_interval: Optional[Tuple[datetime, datetime]]
    boundary_uncertainty_days: Optional[float]
    stable: bool
    supported: bool
    #: Lords to this level at the early and the late end of the founding window.
    lords_at_window_ends: Optional[Tuple[Tuple[str, ...], Tuple[str, ...]]] = None
    reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        for k in ("start", "end"):
            d[k] = d[k].isoformat() if d[k] else None
        for k in ("start_interval", "end_interval"):
            d[k] = [x.isoformat() for x in d[k]] if d[k] else None
        return d


@dataclass(frozen=True)
class DashaAtEvent:
    """Result of :func:`dasha_at_event`."""

    chart_id: str
    grade: str
    event_time: datetime
    founding_moment: datetime
    half_window_minutes: float
    event_half_window_minutes: float
    dasha_year_days: float
    moon_longitude: float
    first_lord: str
    levels: List[DashaLevel] = field(default_factory=list)

    def level(self, n: int) -> DashaLevel:
        return self.levels[n - 1]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chart_id": self.chart_id,
            "grade": self.grade,
            "event_time": self.event_time.isoformat(),
            "founding_moment": self.founding_moment.isoformat(),
            "half_window_minutes": self.half_window_minutes,
            "event_half_window_minutes": self.event_half_window_minutes,
            "dasha_year_days": self.dasha_year_days,
            "moon_longitude": self.moon_longitude,
            "first_lord": self.first_lord,
            "levels": [lv.to_dict() for lv in self.levels],
        }


# ------------------------------------------------------------------ helpers
def _aware(dt: datetime, name: str) -> datetime:
    require_aware(dt, name)  # NaiveDatetimeError is a ValueError
    return dt.astimezone(timezone.utc)


def moon_longitude_at(moment: datetime) -> float:
    """Sidereal longitude of the Moon at ``moment`` (project ayanamsa)."""
    return float(Sky(_aware(moment, "moment")).lon("Moon"))


def moon_speed_at(moment: datetime) -> float:
    """The Moon's speed in degrees per day at ``moment``."""
    return float(Sky(_aware(moment, "moment")).record("Moon")["longitude_speed"])


def expected_boundary_shift_days(
    minutes: float,
    moon_speed_deg_per_day: float,
    first_lord: str,
    year: YearLike = DEFAULT_DASHA_YEAR,
) -> float:
    """Section 3.2: ``(time error x Moon speed / 13 deg 20') x years of the first lord``.

    Returns the size of the shift in days (positive). Moving the founding time
    later moves every boundary *earlier* by this amount, less the time error
    itself (one minute against days, so negligible).
    """
    moon_moved = minutes / 1440.0 * moon_speed_deg_per_day
    return abs(moon_moved / NAKSHATRA_SPAN * VIMSHOTTARI_YEARS[first_lord] * year_length_days(year))


def _nested(birth: datetime, moon: float, depth: int, until: datetime, year: YearLike):
    span_years = (until - birth).total_seconds() / 86400.0 / year_length_days(year) + 1.0
    return compute_vimshottari_nested_periods(
        birth, moon, depth=depth, total_years=max(120.0, span_years), year=year
    )


def _running(nested: List[VimshottariPeriodDict], t: datetime) -> VimshottariPeriodDict:
    """The period containing ``t``; never falls back to a neighbour."""
    for p in nested:
        if p["start"] <= t < p["end"]:
            return p
    raise DashaWindowError(f"no dasha period contains {t.isoformat()}")


def _chains(birth: datetime, moon: float, t: datetime, year: YearLike, depth: int):
    """Running period at each level 1..depth for founding moment ``birth``."""
    return [_running(_nested(birth, moon, d, t, year), t) for d in range(1, depth + 1)]


def _timeline_origin(birth: datetime, moon: float, year: YearLike) -> datetime:
    """Start of the Ketu mahadasha of the 120-year cycle holding the first period.

    Only differences of this instant are used: they measure how far the whole
    timeline slides between two founding moments.
    """
    lord = get_vimshottari_start_lord(moon)
    idx = VIMSHOTTARI_SEQUENCE.index(lord)
    before = sum(VIMSHOTTARI_YEARS[VIMSHOTTARI_SEQUENCE[i]] for i in range(idx))
    elapsed = elapsed_fraction(moon) * VIMSHOTTARI_YEARS[lord]
    return birth - timedelta(days=(before + elapsed) * year_length_days(year))


def _offset(t0: datetime, moon0: float, t: datetime, year: YearLike) -> timedelta:
    """How far every boundary moves when the founding moment is ``t`` instead of ``t0``."""
    d = _timeline_origin(t, moon_longitude_at(t), year) - _timeline_origin(t0, moon0, year)
    cycle = timedelta(days=120 * year_length_days(year))
    # Crossing Ashwini 0 deg restarts the cycle count; bring the slide back near zero.
    while d > cycle / 2:
        d -= cycle
    while d < -cycle / 2:
        d += cycle
    return d


def _span(*points: datetime) -> Tuple[datetime, datetime]:
    return (min(points), max(points))


def _overlaps(iv: Tuple[datetime, datetime], lo: datetime, hi: datetime) -> bool:
    """Closed-interval overlap: touching an edge counts (conservative)."""
    return iv[0] <= hi and lo <= iv[1]


# --------------------------------------------------------------------- main
def dasha_at_event(
    chart: Chart,
    event_time: datetime,
    *,
    depth: int = MAX_DEPTH,
    year: YearLike = DEFAULT_DASHA_YEAR,
    half_window: Optional[float] = None,
    event_half_window_minutes: float = 0.0,
    catalogue: Optional[Catalogue] = None,
) -> DashaAtEvent:
    """Vimshottari lords running at ``event_time`` for ``chart``, levels 1..``depth``.

    ``half_window`` overrides the chart's founding half-window in minutes
    (default: from the registry and the grade). Raises ``ValueError`` for a
    naive datetime, ``RegistryError`` for grade X, ``ChartNotApplicable`` for an
    event before the chart, ``DashaWindowError`` for an event inside the
    founding window, ``CatalogueError`` if the method is not catalogued.
    """
    if not 1 <= depth <= MAX_DEPTH:
        raise ValueError(f"depth must be 1 to {MAX_DEPTH}")
    if event_half_window_minutes < 0:
        raise ValueError("event_half_window_minutes must be >= 0")
    event = _aware(event_time, "event_time")
    grade = chart_grade(chart)
    if grade == "X":
        raise RegistryError(f"{chart.chart_id}: grade X (date disputed) is excluded")
    cat = catalogue or load_catalogue()
    cat.get(METHOD_ID).resolve()  # refuses an uncatalogued or uncomputable method
    chart_applies(chart, event)

    hw = half_window if half_window is not None else half_window_minutes(chart)
    if hw is None or hw < 0:
        raise RegistryError(f"{chart.chart_id}: no founding-time window")
    t0 = chart_moment(chart)
    moon0 = moon_longitude_at(t0)
    common = dict(
        chart_id=chart.chart_id,
        grade=grade,
        event_time=event,
        founding_moment=t0,
        half_window_minutes=float(hw),
        event_half_window_minutes=float(event_half_window_minutes),
        dasha_year_days=year_length_days(year),
        moon_longitude=moon0,
        first_lord=get_vimshottari_start_lord(moon0),
    )

    if grade == "D" or chart.time is None:
        levels = [
            DashaLevel(
                level=n, name=LEVEL_NAMES[n], lord=None, lords=None, start=None, end=None,
                start_interval=None, end_interval=None, boundary_uncertainty_days=None,
                stable=False, supported=False, reason=UNSUPPORTED_REASON,
            )
            for n in range(1, depth + 1)
        ]
        return DashaAtEvent(levels=levels, **common)

    t_lo = t0 - timedelta(minutes=hw)
    t_hi = t0 + timedelta(minutes=hw)
    if event <= t_hi:
        raise DashaWindowError(
            f"{chart.chart_id}: event {event.isoformat()} falls inside the founding-time window"
        )
    e_lo = event - timedelta(minutes=event_half_window_minutes)
    e_hi = event + timedelta(minutes=event_half_window_minutes)

    mid = _chains(t0, moon0, event, year, depth)
    early = _chains(t_lo, moon_longitude_at(t_lo), event, year, depth)
    late = _chains(t_hi, moon_longitude_at(t_hi), event, year, depth)
    off_early = _offset(t0, moon0, t_lo, year)
    off_late = _offset(t0, moon0, t_hi, year)
    unc = max(abs(off_early.total_seconds()), abs(off_late.total_seconds())) / 86400.0

    levels: List[DashaLevel] = []
    coarser_stable = True
    for n in range(1, depth + 1):
        p = mid[n - 1]
        s_iv = _span(p["start"], p["start"] + off_early, p["start"] + off_late)
        e_iv = _span(p["end"], p["end"] + off_early, p["end"] + off_late)
        same = early[n - 1]["lords"] == p["lords"] == late[n - 1]["lords"]
        edge_hit = _overlaps(s_iv, e_lo, e_hi) or _overlaps(e_iv, e_lo, e_hi)
        reasons = []
        if not same:
            reasons.append("running lords differ across the founding-time window")
        if edge_hit:
            reasons.append("a boundary interval contains the event")
        if not coarser_stable:
            reasons.append("a coarser level is unstable")
        stable = not reasons
        coarser_stable = stable
        levels.append(
            DashaLevel(
                level=n,
                name=LEVEL_NAMES[n],
                lord=p["lords"][-1],
                lords=tuple(p["lords"]),
                start=p["start"],
                end=p["end"],
                start_interval=s_iv,
                end_interval=e_iv,
                boundary_uncertainty_days=unc,
                stable=stable,
                supported=True,
                lords_at_window_ends=(tuple(early[n - 1]["lords"]), tuple(late[n - 1]["lords"])),
                reason="; ".join(reasons),
            )
        )
    return DashaAtEvent(levels=levels, **common)


__all__ = [
    "DashaAtEvent",
    "DashaLevel",
    "DashaWindowError",
    "LEVEL_NAMES",
    "dasha_at_event",
    "expected_boundary_shift_days",
    "moon_longitude_at",
    "moon_speed_at",
]
