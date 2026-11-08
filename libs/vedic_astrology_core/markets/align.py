"""Align market bars with astrological indicators on one calendar.

This is the one place that maps dates and timestamps onto bars; the
statistics, the event study and the figures all go through it.

Windows and denominators are counted in **bars** (trading days) when
``calendar="trading"``. The gold study once built windows in calendar days
and divided by a trading-day total, which inflated every expected overlap
(review item S1-11); :func:`window_mask` works on bar positions only.

Astro state is sampled at a stated local time (``sample_time`` in ``tz``,
e.g. the LBMA PM fix at 15:00 Europe/London or COMEX settlement at 13:30
America/New_York), not at 12:00 UTC. Sampling at or before the bar close is
what keeps look-ahead out.
"""

from typing import Callable, Iterable, List, Optional, Tuple, Union

import numpy as np
import pandas as pd

IndicatorSource = Union[pd.DataFrame, Callable[[pd.DatetimeIndex], pd.DataFrame]]
POLICIES = ("next_bar", "previous_bar", "drop_non_trading")


def trading_calendar(prices: pd.DataFrame) -> pd.DatetimeIndex:
    """Sorted unique trading dates of a tidy price frame."""
    dates = pd.to_datetime(prices["date"]).dt.normalize()
    return pd.DatetimeIndex(sorted(dates.unique()), name="date")


def sample_instants(
    dates: Iterable, sample_time: str = "12:00", tz: str = "UTC"
) -> pd.DatetimeIndex:
    """UTC instants of ``sample_time`` local time in ``tz`` on each date.

    DST is handled by localising each wall-clock time in ``tz``.
    """
    hours, minutes = (int(x) for x in sample_time.split(":"))
    local = pd.DatetimeIndex(pd.to_datetime(list(dates))).normalize() + pd.Timedelta(
        hours=hours, minutes=minutes
    )
    return local.tz_localize(tz).tz_convert("UTC")


def _utc_dates(index: pd.Index) -> pd.DatetimeIndex:
    idx = pd.DatetimeIndex(index)
    if idx.tz is not None:
        idx = idx.tz_convert("UTC").tz_localize(None)
    return idx.normalize()


def align(
    prices: pd.DataFrame,
    indicator_frame: IndicatorSource,
    freq: str = "D",
    calendar: str = "trading",
    sample_time: Optional[str] = None,
    tz: str = "UTC",
) -> pd.DataFrame:
    """Join prices and indicators into one tidy frame, one row per bar.

    Args:
        prices: tidy price frame (see :mod:`.fetch`).
        indicator_frame: a DataFrame indexed by date or timestamp (tz-aware
            timestamps are joined on their UTC date), or a callable that takes
            the UTC sample instants and returns a frame indexed by them.
        freq: only ``"D"`` (daily bars) is supported.
        calendar: ``"trading"`` keeps price dates only; ``"calendar"`` keeps
            every day, forward-fills ``close`` and adds ``is_trading``.
        sample_time: local ``HH:MM`` at which a callable source is sampled.
        tz: time zone of ``sample_time``.

    Returns:
        DataFrame with ``date``, ``bar`` (position on the trading calendar),
        ``close``, ``is_trading`` and the indicator columns. Every trading
        bar must have indicator values; a gap raises ``ValueError``.
    """
    if freq != "D":
        raise ValueError(f"freq {freq!r} not supported; only daily bars ('D')")
    if calendar not in ("trading", "calendar"):
        raise ValueError(f"calendar must be 'trading' or 'calendar', not {calendar!r}")
    bars = trading_calendar(prices)
    close = prices.assign(date=pd.to_datetime(prices["date"]).dt.normalize())
    close = close.set_index("date")["close"]
    if calendar == "trading":
        dates = bars
    else:
        dates = pd.date_range(bars[0], bars[-1], freq="D", name="date")
    frame = pd.DataFrame(index=dates)
    frame["is_trading"] = frame.index.isin(bars)
    frame["close"] = close.reindex(dates).ffill()
    frame["bar"] = np.searchsorted(bars.values, dates.values, side="right") - 1

    if callable(indicator_frame):
        instants = sample_instants(dates, sample_time or "12:00", tz)
        ind = indicator_frame(instants)
        ind = ind.copy()
        ind.index = dates
    else:
        ind = indicator_frame.copy()
        if "date" in ind.columns:
            ind = ind.set_index("date")
        ind.index = _utc_dates(ind.index)
        if ind.index.duplicated().any():
            raise ValueError("indicator frame has more than one row per UTC date")
    ind = ind.reindex(dates)
    gaps = ind.isna().all(axis=1) & frame["is_trading"]
    if len(ind.columns) and gaps.any():
        first = ind.index[gaps.values][0].date()
        raise ValueError(f"{int(gaps.sum())} trading bars lack indicators ({first})")
    out = frame.join(ind)
    out.index.name = "date"
    return out.reset_index()


def on_calendar(
    event_times: Iterable,
    calendar: pd.DatetimeIndex,
    policy: str = "next_bar",
    tz: str = "UTC",
) -> np.ndarray:
    """Map event timestamps to bar positions on ``calendar``.

    Tz-aware events are converted to ``tz`` (the market's zone) and take that
    local date. Policies: ``next_bar`` (first bar on or after the date),
    ``previous_bar`` (last bar on or before), ``drop_non_trading`` (only events
    whose date is a bar). Events off either end of the calendar are dropped.
    """
    if policy not in POLICIES:
        raise ValueError(f"policy must be one of {POLICIES}")
    idx = pd.DatetimeIndex(pd.to_datetime(list(event_times)))
    if len(idx) == 0:
        return np.array([], dtype=int)
    if idx.tz is not None:
        idx = idx.tz_convert(tz).tz_localize(None)
    days = idx.normalize().values
    cal = pd.DatetimeIndex(calendar).values
    if policy == "next_bar":
        pos = np.searchsorted(cal, days, side="left")
        keep = pos < len(cal)
    elif policy == "previous_bar":
        pos = np.searchsorted(cal, days, side="right") - 1
        keep = pos >= 0
    else:
        pos = np.searchsorted(cal, days, side="left")
        keep = (pos < len(cal)) & (cal[np.minimum(pos, len(cal) - 1)] == days)
    return np.unique(pos[keep]).astype(int)


def window_mask(
    bars: Iterable[int], n_bars: int, before: int = 0, after: int = 0
) -> np.ndarray:
    """Boolean mask of bars within ``[b - before, b + after]`` of any event.

    Offsets count bars (trading days), never calendar days.
    """
    mask = np.zeros(n_bars, dtype=bool)
    for b in bars:
        lo, hi = max(0, int(b) - before), min(n_bars - 1, int(b) + after)
        if lo <= hi:
            mask[lo : hi + 1] = True
    return mask


def run_starts(mask: Iterable[bool]) -> np.ndarray:
    """Positions where a boolean series turns from False to True."""
    m = np.asarray(list(mask), dtype=bool)
    prev = np.concatenate([[False], m[:-1]])
    starts = np.flatnonzero(m & ~prev)
    if len(m) and m[0]:
        starts = starts[1:]  # already active at the start: not an onset we saw
    return starts


def intervals(mask: Iterable[bool], dates: Iterable) -> List[Tuple]:
    """``(first_date, last_date)`` of each run of True values."""
    m = np.asarray(list(mask), dtype=bool)
    d = list(pd.to_datetime(list(dates)))
    out = []
    start = None
    for i, value in enumerate(m):
        if value and start is None:
            start = i
        if start is not None and (not value or i == len(m) - 1):
            end = i if value else i - 1
            out.append((d[start], d[end]))
            start = None
    return out
