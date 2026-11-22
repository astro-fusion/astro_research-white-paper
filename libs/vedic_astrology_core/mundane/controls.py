"""Control dates (C1) and placebo charts (C3) for the mundane report (ADR-006 WP-55).

C1, season-matched dates (section 1.3; plan ``controls.C1_season_matched``):
for each event, dates in **other years** of the same period, within
``day_of_year_tolerance_days`` of the event's calendar day, at the event's UTC
time of day, at least ``min_gap_days_from_any_event`` from every event of the
same type and country (mainshock or not). ``per_event`` dates are drawn
without replacement; when fewer are available, all are used and the
shortfall is recorded.

Reproducibility: the draw for one cluster depends only on the plan seed, the
plan's SHA-256, the id of the cluster's first event (one generator per
cluster) and its admissible dates, so another event changes it only by
changing which dates are admissible.

Clustered events: events closer than the C1 gap are chained into one cluster
and moved as a block (control ``j`` of each member is the same calendar shift),
so the matched-set permutation can keep their dependence. Each member's
controls still satisfy every C1 rule.

Period guard (no leakage across the explore and confirm split): a draw is
made for one period at a time. Only events inside that period are drawn for
and only they exclude dates, and a control date may not lie within the gap of
either period edge. A control can therefore never sit next to an event of the
other period, and the explore draw is the same whether or not confirm-period
events are passed in.

C3, placebo charts: the real chart with its founding date moved by a random
whole number of days (time of day, place and zone kept), and optionally the
primary charts of other countries.

C2 (circular shift of the sky) needs a calendar grid of factor values and
lives in :mod:`vedic_astrology_core.mundane.aggregate`.
"""

from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import dataclass, field, replace
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple, Union

import numpy as np

from .burden import Plan
from .registry import Chart, chart_grade

UTC = timezone.utc
PERIODS = ("explore", "confirm")


class ControlError(ValueError):
    """A control draw or placebo chart cannot be made as the plan says."""


class ConfirmNotAvailable(ControlError):
    """The confirm period is closed until WP-63."""


# ---------------------------------------------------------------- periods
def _d(value: Any) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def period_bounds(plan: Plan, period: str = "explore", *, allow_confirm: bool = False) -> Tuple[date, date]:
    """First and last day (inclusive) of a period. Confirm needs ``allow_confirm``."""
    if period not in PERIODS:
        raise ControlError(f"period must be one of {PERIODS}, got {period!r}")
    if period == "confirm" and not (allow_confirm and plan["periods"].get("confirm_enabled")):
        raise ConfirmNotAvailable("report --period confirm: not available until WP-63")
    p = plan["periods"][period]
    return _d(p["start"]), _d(p["end"])


def _aware(t: datetime, what: str) -> datetime:
    if not isinstance(t, datetime) or t.tzinfo is None or t.utcoffset() is None:
        raise ValueError(f"{what}: naive datetime; timezone-aware required")
    return t.astimezone(UTC)


def in_period(t: datetime, bounds: Tuple[date, date]) -> bool:
    return bounds[0] <= _aware(t, "time").date() <= bounds[1]


def _countries(event: Any) -> List[str]:
    iso = getattr(event, "country_iso", None)
    if iso is None:
        return []
    return list(iso) if isinstance(iso, (list, tuple)) else [iso]


def select_events(events: Iterable[Any], plan: Plan, period: str = "explore", *,
                  mainshocks_only: bool = True) -> List[Any]:
    """Events that enter the counts of one period, in time order.

    Exhaustive events only (hand-picked events get case files, never counts),
    of the plan's type and country, magnitude at or above the floor, a time
    precision that is not excluded, inside the period, and (by default)
    Gardner-Knopoff mainshocks only.
    """
    bounds = period_bounds(plan, period)
    d = plan["events"]["definition"]
    excluded = {k for k, v in (plan["events"]["event_time_window"] or {}).items() if v == "excluded"}
    mag = (d.get("magnitude") or {}).get("min")
    out = []
    for e in events:
        if not e.exhaustive or e.event_type != d["event_type"]:
            continue
        if d.get("country_iso") and d["country_iso"] not in _countries(e):
            continue
        if e.time_precision in excluded:
            continue
        if mag is not None and float(e.severity.get("value") or 0) < float(mag):
            continue
        if mainshocks_only and not e.flags.get("mainshock_gk", False):
            continue
        if not in_period(e.time_utc, bounds):
            continue
        out.append(e)
    return sorted(out, key=lambda e: (e.time_utc, e.event_id))


def exclusion_events(events: Iterable[Any], plan: Plan, period: str = "explore") -> List[Any]:
    """Every event of the plan's type and country inside the period (mainshock or not)."""
    bounds = period_bounds(plan, period)
    d = plan["events"]["definition"]
    return [e for e in events
            if e.event_type == d["event_type"]
            and (not d.get("country_iso") or d["country_iso"] in _countries(e))
            and in_period(e.time_utc, bounds)]


# ---------------------------------------------------------------- C1 draw
@dataclass(frozen=True)
class C1Spec:
    """The C1 settings of the plan."""

    per_event: int = 20
    day_of_year_tolerance_days: int = 15
    min_gap_days: float = 30.0
    seed: int = 20261122
    other_years_only: bool = True

    @classmethod
    def from_plan(cls, plan: Plan) -> "C1Spec":
        c = plan["controls"]["C1_season_matched"]
        if not c.get("enabled", True):
            raise ControlError("C1 is disabled in the plan")
        if not c.get("other_years_only", True) or c.get("replacement", False):
            raise ControlError("C1 must draw from other years without replacement")
        if c.get("time_of_day") != "same_utc_time_as_event":
            raise ControlError("C1 time_of_day must be same_utc_time_as_event")
        return cls(per_event=int(c["per_event"]),
                   day_of_year_tolerance_days=int(c["day_of_year_tolerance_days"]),
                   min_gap_days=float(c["min_gap_days_from_any_event"]),
                   seed=int(c["seed"]))


@dataclass
class ControlDraw:
    """Control instants per event id, with the shortfall and the inputs that fix them.

    ``cluster_of`` maps each event to its cluster (the id of the cluster's first
    event). Control ``j`` of every member of one cluster is the same calendar
    shift of the whole cluster, so the lists of one cluster are aligned.
    """

    controls: Dict[str, List[datetime]]
    shortfall: Dict[str, int]
    available: Dict[str, int]
    event_times: Dict[str, datetime]
    period: Tuple[date, date]
    plan_sha256: str
    spec: C1Spec
    cluster_of: Dict[str, str] = field(default_factory=dict)

    def rows(self) -> List[Dict[str, Any]]:
        out = []
        for eid in sorted(self.controls, key=lambda k: (self.event_times[k], k)):
            for i, t in enumerate(self.controls[eid]):
                out.append({"event_id": eid, "cluster": self.cluster_of.get(eid, eid),
                            "control_index": i,
                            "event_time_utc": self.event_times[eid].isoformat(),
                            "control_time_utc": t.isoformat()})
        return out

    def all_times(self) -> List[datetime]:
        return [t for ts in self.controls.values() for t in ts]


def _anchor(event_day: date, year: int) -> date:
    """The event's calendar day in another year (29 February becomes the 28th)."""
    try:
        return event_day.replace(year=year)
    except ValueError:
        return date(year, 2, 28)


def _doy_distance(day: date, event_day: date) -> int:
    """Days between ``day`` and the event's calendar day in the nearest year."""
    return min(abs((day - _anchor(event_day, y)).days) for y in (day.year - 1, day.year, day.year + 1))


def _cluster_rng(seed: int, plan_sha256: str, key: str) -> np.random.Generator:
    eh = int(hashlib.sha256(key.encode("utf-8")).hexdigest()[:16], 16)
    ph = int(plan_sha256[:16], 16) if plan_sha256 else 0
    return np.random.default_rng([int(seed), ph, eh])


def clusters(times: Sequence[datetime], window_days: float) -> List[List[int]]:
    """Indices of time-sorted events chained into clusters: gaps under ``window_days`` join."""
    order = sorted(range(len(times)), key=lambda i: times[i])
    out: List[List[int]] = []
    last = None
    for i in order:
        if last is not None and (times[i] - times[last]).total_seconds() < window_days * 86400:
            out[-1].append(i)
        else:
            out.append([i])
        last = i
    return out


def season_matched_shifts(member_times: Sequence[datetime], period: Tuple[date, date],
                          exclusion_times: Sequence[datetime], spec: C1Spec) -> List[timedelta]:
    """Every admissible whole-day shift of a cluster, in increasing order.

    A shift moves every member to another year, to within the day-of-year
    tolerance of its own calendar day, keeping its UTC time of day; every moved
    member must lie in the period, at least the gap from both period edges and
    from every event. For a single event this is exactly the C1 candidate set.
    """
    ts = sorted(_aware(t, "event_time") for t in member_times)
    first = ts[0]
    start, end = period
    gap = timedelta(days=spec.min_gap_days)
    lo = (datetime.combine(start, time(0, 0), UTC) + gap).timestamp()
    hi = (datetime.combine(end + timedelta(days=1), time(0, 0), UTC) - gap).timestamp()
    ex = np.array(sorted(_aware(x, "exclusion time").timestamp() for x in exclusion_times),
                  dtype=float)
    gap_s = gap.total_seconds()
    tol = spec.day_of_year_tolerance_days
    days = sorted({(_anchor(first.date(), year) - first.date()).days + off
                   for year in range(start.year - 1, end.year + 2)
                   for off in range(-tol, tol + 1)} - {0})
    d = np.array(days, dtype=np.int64)
    ok = np.ones(len(d), dtype=bool)
    for m, t in enumerate(ts):
        s = t.timestamp() + d * 86400.0
        ok &= (s >= lo) & (s <= hi)
        if ex.size:
            i = np.searchsorted(ex, s)
            left = np.abs(s - ex[np.clip(i - 1, 0, ex.size - 1)])
            right = np.abs(s - ex[np.clip(i, 0, ex.size - 1)])
            ok &= np.minimum(left, right) >= gap_s
        shifted = np.datetime64(t.date(), "D") + d
        ok &= (shifted >= np.datetime64(start, "D")) & (shifted <= np.datetime64(end, "D"))
        if spec.other_years_only:
            ok &= shifted.astype("datetime64[Y]").astype(np.int64) + 1970 != t.year
        if m > 0:  # the first member is placed by construction; later ones can drift a leap day
            for j in np.flatnonzero(ok):
                if _doy_distance(t.date() + timedelta(days=int(d[j])), t.date()) > tol:
                    ok[j] = False
    return [timedelta(days=int(x)) for x in d[ok]]


def season_matched_candidates(event_time: datetime, period: Tuple[date, date],
                              exclusion_times: Sequence[datetime], spec: C1Spec) -> List[datetime]:
    """Every admissible control instant for one event, in time order."""
    t = _aware(event_time, "event_time")
    return [t + d for d in season_matched_shifts([t], period, exclusion_times, spec)]


def draw_season_matched(events: Sequence[Any], plan: Plan, *, period: str = "explore",
                        exclusion: Optional[Sequence[Any]] = None,
                        spec: Optional[C1Spec] = None,
                        bounds: Optional[Tuple[date, date]] = None,
                        cluster_window_days: Optional[float] = None) -> ControlDraw:
    """Draw C1 control dates for ``events`` (objects with ``event_id`` and ``time_utc``).

    ``exclusion`` lists the events no control may come near (default:
    ``events``). Events or exclusion events outside the period are dropped
    before anything is drawn, so nothing from another period can shape the
    draw. Events closer than ``cluster_window_days`` (default: the C1 gap)
    are chained into one cluster and moved together, so control ``j`` of each
    member is the same shift of the cluster; the matched-set permutation then
    keeps the members' dependence (one choice per cluster). A cluster of one
    event is the plain C1 draw.
    """
    spec = spec or C1Spec.from_plan(plan)
    b = bounds or period_bounds(plan, period)
    window = spec.min_gap_days if cluster_window_days is None else float(cluster_window_days)
    inside = [e for e in events if in_period(e.time_utc, b)]
    excl = [e for e in (exclusion if exclusion is not None else events) if in_period(e.time_utc, b)]
    ex_times = [e.time_utc for e in excl] + [e.time_utc for e in inside]
    ids = [e.event_id for e in inside]
    if len(ids) != len(set(ids)):
        raise ControlError("duplicate event ids in the control draw")
    times = {e.event_id: _aware(e.time_utc, "time_utc") for e in inside}
    controls, shortfall, available, cluster_of = {}, {}, {}, {}
    for members in clusters([times[e.event_id] for e in inside], window):
        mem = sorted((inside[i] for i in members), key=lambda e: (times[e.event_id], e.event_id))
        key = mem[0].event_id
        shifts = season_matched_shifts([times[e.event_id] for e in mem], b, ex_times, spec)
        rng = _cluster_rng(spec.seed, plan.sha256, key)
        k = min(spec.per_event, len(shifts))
        pick = sorted(rng.choice(len(shifts), size=k, replace=False).tolist()) if k else []
        for e in mem:
            controls[e.event_id] = [times[e.event_id] + shifts[i] for i in pick]
            shortfall[e.event_id] = spec.per_event - k
            available[e.event_id] = len(shifts)
            cluster_of[e.event_id] = key
    return ControlDraw(controls, shortfall, available, times, b, plan.sha256, spec, cluster_of)


def controls_path(plan: Plan, directory: Union[str, Path]) -> Path:
    return Path(directory) / f"controls_{plan.sha12}.csv"


def write_controls(draw: ControlDraw, plan: Plan, directory: Union[str, Path]) -> Path:
    """Write ``controls_<plan_sha12>.csv`` and its manifest (shortfall recorded per event)."""
    path = controls_path(plan, directory)
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = draw.rows()
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["event_id", "cluster", "control_index",
                                           "event_time_utc", "control_time_utc"],
                           lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    manifest = {
        "schema": "mundane-controls/1",
        "plan_id": plan["id"],
        "plan_sha256": plan.sha256,
        "seed": draw.spec.seed,
        "period": [draw.period[0].isoformat(), draw.period[1].isoformat()],
        "spec": {"per_event": draw.spec.per_event,
                 "day_of_year_tolerance_days": draw.spec.day_of_year_tolerance_days,
                 "min_gap_days": draw.spec.min_gap_days},
        "n_events": len(draw.controls),
        "n_controls": len(rows),
        "shortfall": {k: v for k, v in sorted(draw.shortfall.items()) if v},
        "available": dict(sorted(draw.available.items())),
        "csv_sha256": digest,
    }
    path.with_suffix(".manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


# ------------------------------------------------------------ C3 placebos
_GRADE_ORDER = {"A": 0, "B": 1, "C": 2, "D": 3, "R": 4, "X": 5}


def date_shift_placebos(chart: Chart, plan: Optional[Plan] = None, *, n: Optional[int] = None,
                        min_abs: Optional[int] = None, max_abs: Optional[int] = None,
                        must_precede: Optional[date] = None,
                        seed: Optional[int] = None) -> List[Chart]:
    """C3: the chart with its founding date moved by ``n`` distinct random day counts.

    Shifts are uniform whole numbers with ``min_abs <= |shift| <= max_abs``, either
    sign. Time of day, place and zone are kept. A shift that puts the founding
    date on or after ``must_precede`` is redrawn, so every placebo covers the
    whole event period. Ids are ``<chart_id>-placebo-NN``.
    """
    cfg: Dict[str, Any] = {}
    if plan is not None:
        c3 = plan["controls"]["C3_placebo_chart"]
        if not c3.get("enabled", True):
            raise ControlError("C3 is disabled in the plan")
        cfg = c3["date_shift"]
    n = int(n if n is not None else cfg.get("n", 99))
    sd = cfg.get("shift_days", {})
    min_abs = int(min_abs if min_abs is not None else sd.get("min_abs", 30))
    max_abs = int(max_abs if max_abs is not None else sd.get("max_abs", 3650))
    seed = int(seed if seed is not None else cfg.get("seed", 20261122))
    if must_precede is None and cfg.get("founding_must_precede"):
        must_precede = _d(cfg["founding_must_precede"])
    if not 0 < min_abs <= max_abs:
        raise ControlError("need 0 < min_abs <= max_abs")
    keep = set(cfg.get("keep", ["time_of_day", "place", "time_zone"]))
    if keep - {"time_of_day", "place", "time_zone"}:
        raise ControlError(f"unknown keep entries {sorted(keep)}")
    allowed = [s for s in range(min_abs, max_abs + 1)]
    allowed = [-s for s in reversed(allowed)] + allowed
    if must_precede is not None:
        allowed = [s for s in allowed if chart.date + timedelta(days=s) < must_precede]
    if len(allowed) < n:
        raise ControlError(f"only {len(allowed)} admissible shifts for {n} placebos")
    ch = int(hashlib.sha256(chart.chart_id.encode("utf-8")).hexdigest()[:16], 16)
    rng = np.random.default_rng([seed, ch])
    picks = rng.choice(len(allowed), size=n, replace=False)
    out = []
    for i, j in enumerate(picks):
        s = timedelta(days=int(allowed[int(j)]))
        out.append(replace(chart, chart_id=f"{chart.chart_id}-placebo-{i + 1:02d}",
                           date=chart.date + s, valid_from=chart.valid_from + s,
                           notes=f"C3 placebo: founding date shifted {allowed[int(j)]:+d} days"))
    return out


def placebo_shift_days(placebo: Chart, real: Chart) -> int:
    return (placebo.date - real.date).days


def _named_users(chart: Chart) -> int:
    vague = ("most ", "many ", "some ", "various", "practitioners", "astrologers")
    return sum(1 for u in chart.used_by if u and not any(v in u.lower() for v in vague))


def primary_chart(charts: Sequence[Chart], country_iso: str, plan: Optional[Plan] = None,
                  *, eligible_grades: Sequence[str] = ("A", "B", "C", "D"),
                  valid_by: Optional[date] = None) -> Optional[Chart]:
    """The plan's primary-chart rule: grade, named users, earliest founding, chart id."""
    if plan is not None:
        rule = plan["charts"]["primary_rule"]
        eligible_grades = rule.get("eligible_grades", eligible_grades)
        if rule.get("requires_valid_from_on_or_before"):
            valid_by = _d(rule["requires_valid_from_on_or_before"])
    pool = [c for c in charts if c.country_iso == country_iso and chart_grade(c) in eligible_grades
            and (valid_by is None or c.valid_from <= valid_by)]
    if not pool:
        return None

    def key(c: Chart):
        t = c.founding_instant()
        return (_GRADE_ORDER[chart_grade(c)], -_named_users(c),
                t.timestamp() if t else datetime.combine(c.date, time(12), UTC).timestamp(),
                c.chart_id)

    return sorted(pool, key=key)[0]


def other_country_placebos(charts: Sequence[Chart], real: Chart, plan: Optional[Plan] = None,
                           *, enabled: Optional[bool] = None) -> List[Chart]:
    """C3 other-country placebos: each other country's primary chart of the same or better grade.

    Returns an empty list while the plan keeps this placebo disabled.
    """
    if enabled is None:
        enabled = bool(plan["controls"]["C3_placebo_chart"]["other_country"]["enabled"]) if plan else True
    if not enabled:
        return []
    real_rank = _GRADE_ORDER[chart_grade(real)]
    out = []
    for iso in sorted({c.country_iso for c in charts} - {real.country_iso}):
        p = primary_chart(charts, iso, plan)
        if p is not None and _GRADE_ORDER[chart_grade(p)] <= real_rank:
            out.append(p)
    return out


__all__ = [
    "C1Spec", "ConfirmNotAvailable", "ControlDraw", "ControlError", "controls_path",
    "date_shift_placebos", "draw_season_matched", "exclusion_events", "in_period",
    "other_country_placebos", "period_bounds", "placebo_shift_days", "primary_chart",
    "clusters", "season_matched_candidates", "season_matched_shifts", "select_events",
    "write_controls",
]
