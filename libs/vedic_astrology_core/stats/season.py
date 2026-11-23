"""Season-matched controls and baselines (ADR-008 section 6, work package WP-87).

Closes F-01 (season) and, with WP-93 and WP-95, F-02 (physical proxies) of the
strategy audit of 2026-11-22. Everything that builds a design here reads the
**calendar and the grid dates only**, never an outcome, so the gate can run
it before any outcome exists.

Section 6.1, item by item:

1. **Measure.** :func:`season_r2` is the share of the calendar's variance
   explained by the first three yearly harmonics of day-of-year. At
   :data:`SEASON_LINKED_R2` (0.05) or above the calendar is season-linked.
   The number is printed on the card.
2. **Controls.** :func:`control_design` routes a season-linked calendar to
   :func:`season_design`; any other calendar gets the neighbour blocks of
   :func:`.blocks.build_blocks`. A season window of an episode is the same
   day-of-year span in the nearest earlier year and the nearest later year
   (searched up to :data:`MAX_YEARS_AWAY` years away) on which at least
   :data:`MIN_INACTIVE_SHARE` (90%) of the bars are usable controls (inactive,
   outside every episode, carrying an outcome, not reserved by another
   episode). A span serves one episode only. Where a side exists on the grid
   and no such span is found, the block is dropped
   (:data:`DROP_NO_SEASON_WINDOW`). Following Amendment A1 the block is
   equal-size: each active bar gets exactly one control bar, the bar of the
   same day of year in the earlier or the later year (alternating, so both
   years cover the whole span). An active bar with no usable counterpart in
   either year drops the block (:data:`DROP_UNBALANCED`). A calendar left with
   too little evidence this way is Untestable with :data:`SEASON_REASON`.
3. **Placebos and shift cells** of a season-linked calendar use whole-year
   shifts, k = 1 to 100 in both directions (:func:`whole_year_shifts`,
   :func:`shifted_instants`); other calendars keep the random offsets.
4. **Outcome.** :func:`leave_year_out_anomaly`: a seasonal outcome minus the
   day-of-year (or month) mean computed **without the year being tested**;
   for a yearly series, minus the mean (or running mean) of the other years
   (also D-06).
5. **R4.** :func:`baseline_r2` is the R-squared of the calendar regressed on
   all of the domain's baselines together; R4 fails at
   :data:`R4_MAX_BASELINE_R2` (0.5) or above (:func:`r4_passes`).
6. **Slow physical cycles.** :func:`nodal_baseline` (18.6-year node cycle) and
   :func:`solar_cycle_baseline` (smoothed sunspot number); monsoon, flood and
   earthquake plans add both (:func:`physical_baselines`,
   :data:`PHYSICAL_BASELINE_DOMAINS`). :func:`remove_baselines` gives the
   outcome "with baselines" for the primary row of the card (section 7.3).
   Exclusion on that outcome must remove the effect in the shape the
   regression leaves it (second strategy audit N-02):
   :func:`baseline_effect_shape`, or :func:`effect_shape` for baselines and
   detrending together. A flat removal over-removes whenever the calendar
   correlates with a baseline and gives false "excluded".

Amendment A2 (single-day and edge episodes): :func:`control_design` and
:func:`season_design` take the plan seed as `side_seed`, which allows
one-sided equal-size blocks (single-bar season windows alternate between the
earlier and the later year). One-sided controls are sensitive to trend, so
daily and hourly outcomes (:func:`detrend_required`) are detrended first by
:func:`centred_detrend`, a centred running mean over a window the plan
declares; :func:`detrended_effect_shape` gives the shape a steady effect
takes after it (for exclusion by effect removal).

Deviation from the ADR text, conservative (recorded in the WP-87 report): the
nodal term is entered as the first :data:`NODAL_HARMONICS` (6) harmonics of
the 18.6-year cycle, not the first harmonic alone. A node-in-one-sign
calendar is a box of one twelfth of the cycle; against one sine and cosine its
R-squared is about 0.18, so R4 could never fail for it and Z6 could not pass.
Six harmonics give about 0.74 to 0.82 for every sign on the 1871 to 2016
yearly grid.

Nothing here starts a thread (G-13); every function is deterministic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd

from . import blocks as _blocks
from .episodes import episodes

#: Item 1: a calendar with season_r2 at or above this is season-linked.
SEASON_LINKED_R2 = 0.05
#: Item 1: number of yearly harmonics of day-of-year in season_r2.
SEASON_HARMONICS = 3
#: Item 2: share of a candidate span's bars that must be usable controls.
MIN_INACTIVE_SHARE = 0.9
#: Item 2: years searched on each side, nearest first.
MAX_YEARS_AWAY = 3
#: Item 2: largest distance (days) between a bar's same-day-of-year date and
#: the grid bar that stands for it (business-day grids have no weekend bars).
MAX_MATCH_DAYS = 3
#: Item 3 and section 5: whole-year shifts, k = 1 to this in both directions.
MAX_YEAR_SHIFT = 100
#: Item 5: R4 fails at this baseline_r2 or above.
R4_MAX_BASELINE_R2 = 0.5
#: Item 6: lunar nodal period in years and harmonics entered (see the module
#: docstring for why six).
NODAL_PERIOD_YEARS = 18.6
NODAL_HARMONICS = 6
#: Item 6: smoothing window of the sunspot number (13-month running mean,
#: half weight at both ends, as for the international smoothed number).
SOLAR_SMOOTHING_WINDOW = 13
#: Item 6: plans that must add the nodal and solar-cycle baselines.
PHYSICAL_BASELINE_DOMAINS = ("monsoon", "flood", "earthquake")

#: Amendment A2: grids with a median bar spacing at or below this many days
#: (daily, business-daily, hourly) are detrended before the block test.
DETREND_MAX_SPACING_DAYS = 1.0

#: The card's reason when the season cannot be held fixed.
SEASON_REASON = "cannot be separated from the season"
#: Season-specific drop reasons (the block design then sees an empty window
#: and counts the block as `no_control` as well).
DROP_NO_SEASON_WINDOW = "no_season_window"
DROP_UNBALANCED = "unbalanced"
SEASON_DROP_REASONS = (DROP_NO_SEASON_WINDOW, DROP_UNBALANCED)

_DAYS_PER_YEAR = 365.25
_NS_PER_DAY = 86_400 * 10**9


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------


def _mask(values, name: str, n: Optional[int] = None) -> np.ndarray:
    v = values.to_numpy() if isinstance(values, pd.Series) else np.asarray(values)
    if v.ndim != 1:
        raise ValueError(f"{name} must be one-dimensional")
    if v.dtype.kind == "f" and np.isnan(v).any():
        raise ValueError(f"{name} contains NaN")
    if v.dtype.kind not in "biuf" or (v.dtype.kind != "b" and not np.isin(v, (0, 1)).all()):
        raise ValueError(f"{name} must be boolean or 0/1")
    if n is not None and len(v) != n:
        raise ValueError(f"{name} must have length {n}, got {len(v)}")
    return v.astype(bool)


def _dates(dates, calendar=None, n: Optional[int] = None) -> pd.DatetimeIndex:
    if dates is None and isinstance(calendar, pd.Series) and isinstance(calendar.index, pd.DatetimeIndex):
        dates = calendar.index
    if dates is None:
        raise ValueError("grid dates are required (a DatetimeIndex, one per bar)")
    idx = pd.DatetimeIndex(dates)
    if idx.tz is not None:
        idx = idx.tz_convert("UTC").tz_localize(None)
    idx = idx.as_unit("ns")  # asi8 below is in nanoseconds whatever the input unit
    if n is not None and len(idx) != n:
        raise ValueError(f"dates must have one entry per bar ({n}), got {len(idx)}")
    if len(idx) > 1 and not (np.diff(idx.asi8) > 0).all():
        raise ValueError("dates must be strictly increasing")
    return idx


def _r2(y: np.ndarray, X: np.ndarray) -> float:
    """R-squared of y on [1, X] by least squares; 0 for a constant y."""
    y = np.asarray(y, dtype=float)
    sst = float(np.sum((y - y.mean()) ** 2))
    if sst == 0.0:
        return 0.0
    A = np.column_stack([np.ones(len(y)), X]) if X.size else np.ones((len(y), 1))
    coef, *_ = np.linalg.lstsq(A, y, rcond=None)
    res = y - A @ coef
    return float(min(1.0, max(0.0, 1.0 - float(np.sum(res * res)) / sst)))


def _harmonics(phase: np.ndarray, k_max: int, prefix: str) -> pd.DataFrame:
    cols = {}
    for k in range(1, int(k_max) + 1):
        cols[f"{prefix}_sin_{k}"] = np.sin(2.0 * np.pi * k * phase)
        cols[f"{prefix}_cos_{k}"] = np.cos(2.0 * np.pi * k * phase)
    return pd.DataFrame(cols)


def decimal_years(dates) -> np.ndarray:
    """Time in years (year plus elapsed fraction); plain integers are years."""
    arr = np.asarray(dates)
    if arr.dtype.kind in "iu":
        return arr.astype(float)
    idx = _dates(dates)
    elapsed = (idx.day_of_year.to_numpy(float) - 1.0
               + (idx.asi8 - idx.normalize().asi8) / _NS_PER_DAY)
    length = np.where(idx.is_leap_year, 366.0, 365.0)
    return idx.year.to_numpy(float) + elapsed / length


# --------------------------------------------------------------------------
# Item 1: season measure
# --------------------------------------------------------------------------


def season_harmonics(dates, k_max: int = SEASON_HARMONICS) -> pd.DataFrame:
    """Sine and cosine of the first `k_max` yearly harmonics of day-of-year."""
    idx = _dates(dates)
    return _harmonics(idx.day_of_year.to_numpy(float) / _DAYS_PER_YEAR, k_max, "season")


def season_r2(calendar, dates=None) -> float:
    """Share of the calendar's variance explained by three yearly harmonics (item 1).

    0 for a constant calendar and for a grid with one bar per year (the
    harmonics are then constant).
    """
    c = _mask(calendar, "calendar")
    idx = _dates(dates, calendar, len(c))
    return _r2(c.astype(float), season_harmonics(idx).to_numpy())


def is_season_linked(r2: float) -> bool:
    """Item 1: season-linked at :data:`SEASON_LINKED_R2` or above."""
    return bool(r2 >= SEASON_LINKED_R2)


# --------------------------------------------------------------------------
# Item 2: same-season windows
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class SeasonWindow:
    """Season choice of one episode: year offsets used (None: none used)."""

    episode: int
    left_years: Optional[int]
    right_years: Optional[int]
    left_exists: bool
    right_exists: bool
    reason: Optional[str]


@dataclass(frozen=True, eq=False)
class SeasonDesign:
    """Control design of one calendar, chosen from the calendar alone.

    `blocks` is the :class:`.blocks.BlockDesign` the primary test reads
    (neighbour blocks, or same-season windows when `season_linked`).
    """

    blocks: _blocks.BlockDesign
    season_r2: float
    season_linked: bool
    windows: Tuple[SeasonWindow, ...] = field(default=())

    @property
    def control_kind(self) -> str:
        return "season_windows" if self.blocks.kind == "windows" else "neighbours"

    @property
    def placebo_shift(self) -> str:
        """Item 3: `"whole_year"` for season-linked calendars, else `"random_offset"`."""
        return placebo_shift_kind(self.season_linked)

    @property
    def season_drop_counts(self) -> Dict[str, int]:
        out = {r: 0 for r in SEASON_DROP_REASONS}
        for w in self.windows:
            if w.reason is not None:
                out[w.reason] += 1
        return out

    @property
    def untestable_reason(self) -> Optional[str]:
        """:data:`SEASON_REASON` when the season windows leave too little evidence.

        Set for a season-linked calendar whose used blocks fall below gate G4
        (`K_eff < MIN_K_EFF`) while at least one block was dropped for want
        of a same-season window. Other shortfalls are the gate's to name.
        """
        if not self.season_linked:
            return None
        if self.blocks.k_eff >= _blocks.MIN_K_EFF:
            return None
        if sum(self.season_drop_counts.values()) == 0:
            return None
        return SEASON_REASON

    def summary(self) -> Dict:
        """What the card and the gate print (numbers from the calendar only)."""
        return {
            "season_r2": self.season_r2,
            "season_linked": self.season_linked,
            "control_kind": self.control_kind,
            "placebo_shift": self.placebo_shift,
            "n_episodes": self.blocks.n_episodes,
            "n_used": self.blocks.n_used,
            "drop_counts": self.blocks.drop_counts,
            "season_drop_counts": self.season_drop_counts,
            "k_eff": self.blocks.k_eff,
            "untestable_reason": self.untestable_reason,
            "design_id": self.blocks.design_id,
        }


def _shift_ns(dates: pd.DatetimeIndex, bars, years: int) -> np.ndarray:
    """Same month and day `years` away (Feb 29 goes to Feb 28), as int64 ns."""
    moved = pd.DatetimeIndex(dates[np.atleast_1d(bars)]) + pd.DateOffset(years=int(years))
    return moved.as_unit("ns").asi8


def _span(dates: pd.DatetimeIndex, ns: np.ndarray, start: int, end: int,
          years: int) -> Optional[Tuple[int, int]]:
    """Bars of the episode span moved by `years`; None if it leaves the grid."""
    a, b = _shift_ns(dates, [start, end], years)
    if a < ns[0] or b > ns[-1]:
        return None
    lo = int(np.searchsorted(ns, a, side="left"))
    hi = int(np.searchsorted(ns, b, side="right")) - 1
    if hi < lo:
        return None
    return lo, hi


def _counterparts(ns: np.ndarray, targets: np.ndarray, lo: int, hi: int) -> np.ndarray:
    """Nearest grid bar inside lo..hi for each target instant; -1 if too far."""
    j = np.searchsorted(ns, targets)
    out = np.full(len(targets), -1, dtype=np.int64)
    best_gap = np.full(len(targets), np.iinfo(np.int64).max)
    for cand in (j - 1, j):
        ok = (cand >= lo) & (cand <= hi)
        c = np.clip(cand, 0, len(ns) - 1)
        gap = np.abs(ns[c] - targets)
        better = ok & (gap < best_gap)
        out[better] = c[better]
        best_gap[better] = gap[better]
    out[best_gap > MAX_MATCH_DAYS * _NS_PER_DAY] = -1
    return out


def season_design(
    calendar,
    dates=None,
    *,
    merge_gap: Union[int, str, pd.Timedelta],
    available=None,
    r2: Optional[float] = None,
    side_seed: Optional[Union[int, str]] = None,
) -> SeasonDesign:
    """Same-season control windows for every episode (item 2, Amendments A1 and A2).

    Reads the calendar, the grid dates and `available` only (see the module
    docstring for the rule). Episodes are served in time order; a span
    chosen for one episode is reserved and never serves another. Returns the
    design whether or not the calendar is season-linked;
    :func:`control_design` chooses between this and the neighbour blocks.

    With `side_seed` (the plan seed, Amendment A2) a block may take its
    equal-size control from ONE year: (a) when no same-season window is found
    on the other side, the side with a window is used for every active bar
    (forced); (b) a single-bar episode with a window on both sides takes its
    one control bar from one year, the side alternating in calendar order
    over such episodes, the first side fixed by :func:`.blocks.start_side`.
    Only the spans that give a control bar are reserved. Without
    `side_seed` the A1 rule holds (a missing window on an existing side
    drops the block; a single bar always takes the earlier year first, and
    the block design then drops it as one-sided).
    """
    active = _mask(calendar, "calendar")
    n = len(active)
    idx = _dates(dates, calendar, n)
    ns = idx.asi8
    avail = np.ones(n, dtype=bool) if available is None else _mask(available, "available", n)
    eps = episodes(active, merge_gap)
    in_span = np.zeros(n, dtype=bool)
    for ep in eps:
        in_span[ep.start : ep.end + 1] = True
    free = ~active & ~in_span & avail
    reserved = np.zeros(n, dtype=bool)
    turn = None if side_seed is None else _blocks.start_side(side_seed)

    entries: List[Tuple] = []
    windows: List[SeasonWindow] = []
    for k, ep in enumerate(eps):
        span = np.arange(ep.start, ep.end + 1)
        on = span[active[span] & avail[span]]
        usable = free & ~reserved

        def search(sign: int):
            exists = _span(idx, ns, ep.start, ep.end, sign) is not None
            for y in range(1, MAX_YEARS_AWAY + 1):
                sp = _span(idx, ns, ep.start, ep.end, sign * y)
                if sp is None:
                    continue
                lo, hi = sp
                if usable[lo : hi + 1].mean() >= MIN_INACTIVE_SHARE:
                    return exists, sign * y, sp
            return exists, None, None

        l_exists, l_years, l_sp = search(-1)
        r_exists, r_years, r_sp = search(+1)
        reason = None
        if len(on) == 0:
            reason = None  # the block design drops it as no_active
        elif l_years is None and r_years is None:
            reason = DROP_NO_SEASON_WINDOW
        elif turn is None and ((l_exists and l_years is None) or (r_exists and r_years is None)):
            reason = DROP_NO_SEASON_WINDOW  # A1: an existing side needs its window
        left: List[int] = []
        right: List[int] = []
        if reason is None and len(on):
            sides = [(s, y, sp) for s, y, sp in (("L", l_years, l_sp), ("R", r_years, r_sp))
                     if y is not None]
            if turn is not None and len(on) == 1 and len(sides) == 2:
                # A2 (b): alternate the year of single-bar blocks in calendar order.
                first = "L" if turn == _blocks.SIDE_LEFT else "R"
                sides = sorted(sides, key=lambda e: e[0] != first)
                turn = _blocks.SIDE_RIGHT if turn == _blocks.SIDE_LEFT else _blocks.SIDE_LEFT
            match = {s: _counterparts(ns, _shift_ns(idx, on, y), sp[0], sp[1])
                     for s, y, sp in sides}
            taken = set()
            for i in range(len(on)):
                order = sides if i % 2 == 0 else sides[::-1]
                got = False
                for s, _, _ in order:
                    c = int(match[s][i])
                    if c >= 0 and usable[c] and c not in taken:
                        taken.add(c)
                        (left if s == "L" else right).append(c)
                        got = True
                        break
                if not got:
                    reason = DROP_UNBALANCED
                    break
        if reason is None:
            for sp, got_side in ((l_sp, left), (r_sp, right)):
                if sp is not None and len(on) and (turn is None or len(got_side)):
                    reserved[sp[0] : sp[1] + 1] = True
            entries.append((np.asarray(left, dtype=np.int64), np.asarray(right, dtype=np.int64),
                            bool(l_exists), bool(r_exists)))
            windows.append(SeasonWindow(k, l_years, r_years, bool(l_exists), bool(r_exists), None))
        else:
            empty = np.zeros(0, dtype=np.int64)
            entries.append((empty, empty, bool(l_exists), bool(r_exists)))
            windows.append(SeasonWindow(k, None, None, bool(l_exists), bool(r_exists), reason))

    design = _blocks.design_from_windows(active, entries, merge_gap=merge_gap, available=available,
                                         side_seed=side_seed)
    if r2 is None:
        r2 = season_r2(active, idx)
    return SeasonDesign(design, float(r2), is_season_linked(r2), tuple(windows))


def control_design(
    calendar,
    dates=None,
    *,
    merge_gap: Union[int, str, pd.Timedelta],
    guard_bars: int = 0,
    available=None,
    side_seed: Optional[Union[int, str]] = None,
) -> SeasonDesign:
    """The control design the primary test uses (items 1 and 2).

    Measures :func:`season_r2`; a season-linked calendar gets
    :func:`season_design`, any other the neighbour blocks of
    :func:`.blocks.build_blocks` (with the plan's `guard_bars`).
    `side_seed` is the plan seed: given, Amendment A2 (one-sided
    equal-size blocks) applies to both kinds; the gate and the pipeline
    always pass it. Reads no outcome.
    """
    c = _mask(calendar, "calendar")
    idx = _dates(dates, calendar, len(c))
    r2 = season_r2(c, idx)
    if is_season_linked(r2):
        return season_design(c, idx, merge_gap=merge_gap, available=available, r2=r2,
                             side_seed=side_seed)
    design = _blocks.build_blocks(c, merge_gap=merge_gap, guard_bars=guard_bars, available=available,
                                  side_seed=side_seed)
    return SeasonDesign(design, r2, False, ())


# --------------------------------------------------------------------------
# Item 3: whole-year shifts
# --------------------------------------------------------------------------


def placebo_shift_kind(season_linked: bool) -> str:
    """`"whole_year"` for a season-linked calendar, else `"random_offset"`."""
    return "whole_year" if season_linked else "random_offset"


def whole_year_shifts(k_max: int = MAX_YEAR_SHIFT) -> List[int]:
    """Shifts in whole years: -k_max..-1 and 1..k_max (200 skies by default)."""
    k = int(k_max)
    if k < 1:
        raise ValueError("k_max must be at least 1")
    return list(range(-k, 0)) + list(range(1, k + 1))


def shifted_instants(dates, years: int) -> pd.DatetimeIndex:
    """Grid instants moved by whole years, at which a placebo sky is computed.

    The month and day stay, so the Sun and the season stay in place
    (Feb 29 goes to Feb 28 in a common year).
    """
    if int(years) == 0:
        raise ValueError("a shift of 0 years is the real sky, not a placebo")
    return pd.DatetimeIndex(pd.DatetimeIndex(dates) + pd.DateOffset(years=int(years)))


# --------------------------------------------------------------------------
# Item 4: leave-year-out anomalies
# --------------------------------------------------------------------------


def leave_year_out_anomaly(values, dates=None, *, by: str = "doy",
                           window: Optional[int] = None) -> np.ndarray:
    """Outcome minus a seasonal (or yearly) mean that leaves out the tested year.

    `by="doy"`: mean of the same month and day in the other years;
    `by="month"`: mean of the same month in the other years (every bar of
    those years); `by="year"`: one value per year (`dates` may be plain
    years), mean of the other years, or of the other years within
    `window // 2` years when `window` is given (a running mean without the
    year itself, D-06). Missing values (NaN) stay missing and enter no mean;
    a bar with no other year to compare with is NaN.
    """
    y = np.asarray(values, dtype=float)
    if y.ndim != 1:
        raise ValueError("values must be one-dimensional")
    ok = np.isfinite(y)
    out = np.full(len(y), np.nan)
    if by == "year":
        raw = np.asarray(np.arange(len(y)) if dates is None else dates)
        yrs = raw.astype(int) if raw.dtype.kind in "iu" else _dates(raw).year.to_numpy()
        if len(yrs) != len(y):
            raise ValueError("one year per value")
        if window is not None and int(window) < 1:
            raise ValueError("window must be a positive number of years")
        for i in np.flatnonzero(ok):
            m = ok & (yrs != yrs[i])
            if window is not None:
                m &= np.abs(yrs - yrs[i]) <= int(window) // 2
            if m.any():
                out[i] = y[i] - y[m].mean()
        return out
    if by not in ("doy", "month"):
        raise ValueError('by must be "doy", "month" or "year"')
    idx = _dates(dates, None, len(y))
    key = idx.month.to_numpy() * 100 + (idx.day.to_numpy() if by == "doy" else 0)
    year = idx.year.to_numpy()
    df = pd.DataFrame({"y": y[ok], "key": key[ok], "year": year[ok]})
    tot = df.groupby("key")["y"].agg(["sum", "count"])
    own = df.groupby(["key", "year"])["y"].agg(["sum", "count"])
    t = tot.reindex(key[ok])
    o = own.reindex(pd.MultiIndex.from_arrays([key[ok], year[ok]]))
    s = t["sum"].to_numpy() - o["sum"].to_numpy()
    c = t["count"].to_numpy() - o["count"].to_numpy()
    base = np.full(len(s), np.nan)
    np.divide(s, c, out=base, where=c > 0)
    out[ok] = y[ok] - base
    return out


# --------------------------------------------------------------------------
# Amendment A2: detrending baseline for daily and hourly outcomes
# --------------------------------------------------------------------------


def detrend_required(dates) -> bool:
    """True for a daily or finer grid (median bar spacing at most one day).

    Amendment A2: one-sided controls are sensitive to trend, so a daily or
    hourly outcome is detrended (:func:`centred_detrend`) before the block
    test. Business-day grids count as daily. Reads the grid only.
    """
    arr = np.asarray(dates)
    if arr.dtype.kind in "iu" or len(arr) < 2:
        return False  # plain years, or no spacing to measure
    idx = _dates(dates)
    return bool(np.median(np.diff(idx.asi8)) <= DETREND_MAX_SPACING_DAYS * _NS_PER_DAY)


def _check_window(window) -> int:
    if isinstance(window, bool) or not isinstance(window, (int, np.integer)):
        raise ValueError("the detrending window must be an odd whole number of bars (from the plan)")
    w = int(window)
    if w < 3 or w % 2 == 0:
        raise ValueError("the detrending window must be an odd number of bars, at least 3")
    return w


def centred_detrend(values, window: int, *, segments=None) -> np.ndarray:
    """Values minus a centred running mean over `window` bars, past and future alike.

    The window is declared in the plan (odd, at least 3). Each bar's
    baseline is the mean of the finite values within `h` bars on either
    side, with `h = window // 2` cut back symmetrically near the ends of
    the grid (`h_i = min(h, i, n - 1 - i)`), so the baseline never looks
    further one way than the other and a linear trend is removed exactly at
    every bar (the first and last bars are 0). Missing values (NaN) stay
    missing and enter no mean. Linear in the values, so the same operator
    applied to the active-bar indicator gives the shape a steady effect
    takes after detrending (:func:`detrended_effect_shape`).

    `segments` (N-22, optional): one label per bar, for example 0 on the
    explore bars and 1 on the confirm bars. Every maximal run of equal labels
    is detrended on its own, with the window cut back symmetrically at the
    run's edges, so no baseline mixes bars of two periods and the explore
    numbers are the same whether or not the confirm period is open.
    """
    w = _check_window(window)
    y = np.asarray(values, dtype=float)
    if y.ndim != 1:
        raise ValueError("values must be one-dimensional")
    if segments is not None:
        lab = np.asarray(segments).ravel()
        if len(lab) != len(y):
            raise ValueError(f"segments must have one label per bar ({len(y)}), got {len(lab)}")
        out = np.full(len(y), np.nan)
        cuts = np.flatnonzero(lab[1:] != lab[:-1]) + 1
        for lo, hi in zip(np.r_[0, cuts], np.r_[cuts, len(y)]):
            out[lo:hi] = centred_detrend(y[lo:hi], w)
        return out
    n = len(y)
    ok = np.isfinite(y)
    out = np.full(n, np.nan)
    if n == 0 or not ok.any():
        return out
    i = np.arange(n)
    h = np.minimum(np.minimum(w // 2, i), n - 1 - i)
    cs = np.concatenate(([0.0], np.cumsum(np.where(ok, y, 0.0))))
    cn = np.concatenate(([0], np.cumsum(ok)))
    lo, hi = i - h, i + h + 1
    s, c = cs[hi] - cs[lo], cn[hi] - cn[lo]
    out[ok] = y[ok] - s[ok] / c[ok]  # c >= 1 on a finite bar (the bar itself)
    return out


def detrended_effect_shape(calendar, window: int, finite=None, *, segments=None) -> np.ndarray:
    """What a steady effect of size 1 on every active bar becomes after :func:`centred_detrend`.

    `finite` marks the bars that carry an outcome (NaN elsewhere, as the
    outcome). Exclusion by effect removal (core/stats/exclusion.py,
    `effect_shape`) removes `r` times this shape, so the removed effect
    is the one the detrended data carry. Reads the calendar only.
    """
    return centred_detrend(_indicator(calendar, finite), window, segments=segments)


def _indicator(calendar, finite=None) -> np.ndarray:
    c = _mask(calendar, "calendar")
    ind = c.astype(float)
    if finite is not None:
        ind = np.where(_mask(finite, "finite", len(c)), ind, np.nan)
    return ind


# --------------------------------------------------------------------------
# Items 5 and 6: baselines and R4
# --------------------------------------------------------------------------


def _baseline_matrix(baselines, n: int) -> np.ndarray:
    if isinstance(baselines, pd.DataFrame):
        X = baselines.to_numpy(dtype=float)
    elif isinstance(baselines, dict):
        cols = [np.asarray(v, dtype=float) for v in baselines.values()]
        X = np.column_stack(cols) if cols else np.zeros((n, 0))
    else:
        X = np.asarray(baselines, dtype=float)
        if X.ndim == 1:
            X = X[:, None]
    if X.ndim != 2 or X.shape[0] != n:
        raise ValueError(f"baselines need {n} rows, got shape {X.shape}")
    if not np.isfinite(X).all():
        raise ValueError("baselines must be finite on every bar")
    return X


def baseline_r2(calendar, baselines) -> float:
    """R-squared of the calendar on all of the domain's baselines together (item 5)."""
    c = _mask(calendar, "calendar")
    return _r2(c.astype(float), _baseline_matrix(baselines, len(c)))


def r4_passes(baseline_r2_value: float) -> bool:
    """R4 passes below :data:`R4_MAX_BASELINE_R2` and fails at or above it."""
    v = float(baseline_r2_value)
    if not np.isfinite(v):
        raise ValueError("baseline_r2 must be finite")
    return v < R4_MAX_BASELINE_R2


def nodal_baseline(dates, harmonics: int = NODAL_HARMONICS,
                   period_years: float = NODAL_PERIOD_YEARS) -> pd.DataFrame:
    """Sine and cosine terms of the 18.6-year node cycle (item 6).

    `dates` are grid dates or plain years. Six harmonics by default (module
    docstring).
    """
    if int(harmonics) < 1:
        raise ValueError("harmonics must be at least 1")
    return _harmonics(decimal_years(dates) / float(period_years), harmonics, "nodal")


def solar_cycle_baseline(sunspots, window: int = SOLAR_SMOOTHING_WINDOW) -> np.ndarray:
    """Smoothed sunspot number: centred running mean, half weight at both ends.

    `sunspots` is the series on the outcome's grid, from the plan's pinned
    snapshot. Where the window passes the end of the record the weights of
    the bars present are renormalised.
    """
    s = np.asarray(sunspots, dtype=float)
    if s.ndim != 1 or not np.isfinite(s).all():
        raise ValueError("sunspots must be a finite one-dimensional series")
    w = int(window)
    if w < 1 or w % 2 == 0:
        raise ValueError("window must be a positive odd number")
    if w == 1:
        return s.copy()
    kern = np.ones(w)
    kern[0] = kern[-1] = 0.5  # offsets -w//2 .. +w//2, half weight at both ends
    num = np.convolve(s, kern, mode="same")
    den = np.convolve(np.ones(len(s)), kern, mode="same")
    return num / den


def requires_physical_baselines(domain: str) -> bool:
    """Item 6: monsoon, flood and earthquake plans add the nodal and solar terms."""
    return str(domain) in PHYSICAL_BASELINE_DOMAINS


def physical_baselines(dates, sunspots=None) -> pd.DataFrame:
    """Nodal terms plus the smoothed sunspot number when given (item 6)."""
    out = nodal_baseline(dates)
    if sunspots is not None:
        sm = solar_cycle_baseline(sunspots)
        if len(sm) != len(out):
            raise ValueError("sunspots must have one value per bar")
        out["solar_cycle"] = sm
    return out


def remove_baselines(outcome, baselines) -> np.ndarray:
    """Outcome with the baselines regressed out (the card's "with baselines" row).

    Ordinary least squares of the outcome on [1, baselines] over the bars
    with a finite outcome; returns the residual plus the outcome's mean (NaN
    stays NaN). For continuous and log-ratio outcomes; counts and flags are
    not residualised (R4 and the plan's strata carry their baselines).
    """
    y = np.asarray(outcome, dtype=float)
    if y.ndim != 1:
        raise ValueError("outcome must be one-dimensional")
    X = _baseline_matrix(baselines, len(y))
    ok = np.isfinite(y)
    out = np.full(len(y), np.nan)
    if not ok.any():
        return out
    A = np.column_stack([np.ones(len(y)), X])
    coef, *_ = np.linalg.lstsq(A[ok], y[ok], rcond=None)
    out[ok] = y[ok] - A[ok] @ coef + y[ok].mean()
    return out


def baseline_effect_shape(calendar, baselines, finite=None) -> np.ndarray:
    """What a steady effect of size 1 on every active bar becomes after :func:`remove_baselines` (N-02).

    :func:`remove_baselines` is linear in the outcome, so a steady effect
    `r` on the active bars shows in the "with baselines" outcome as `r`
    times this shape: the active-bar indicator with the same baselines
    regressed out over the same bars (`finite`, the bars that carry an
    outcome). When the calendar correlates with a baseline the regression
    absorbs part of a real effect; removing a flat `r` then over-removes and
    exclusion and X95 are anti-conservative (second strategy audit N-02:
    13.5%, 33% and 46% false "excluded" at baseline R-squared 0.14, 0.29
    and 0.39). Removing `r` times this shape is the same as removing the
    effect from the outcome **before** fitting the baselines and refitting
    (tested). Reads the calendar and the baselines only, never an outcome.
    """
    return remove_baselines(_indicator(calendar, finite), baselines)


def effect_shape(calendar, *, baselines=None, detrend_window: Optional[int] = None, finite=None,
                 segments=None) -> Optional[np.ndarray]:
    """The effect shape exclusion must remove, after every linear step the outcome went through.

    The pipeline's order: baselines regressed out (:func:`remove_baselines`,
    continuous and log-ratio outcomes with declared baselines), then the
    centred detrend (Amendment A2, daily and finer grids). Pass the
    `baselines` the outcome was residualised on (None if it was not) and the
    `detrend_window` (and `segments`) it was detrended with (None if it was
    not). Returns None when neither step applies: removal is then the flat
    shift on the active bars. The shape goes to
    core/stats/exclusion.py `effect_shape`. Calendar and baselines only.
    """
    if baselines is None and detrend_window is None:
        return None
    h = _indicator(calendar, finite)
    if baselines is not None:
        h = remove_baselines(h, baselines)
    if detrend_window is not None:
        h = centred_detrend(h, detrend_window, segments=segments)
    return h
