"""Comparison terms an astrological effect must beat (review item 7).

Calendar, festival, lunar-phase and macro terms for a daily outcome, plus
:func:`incremental_test`, which asks whether an indicator explains anything
once those terms are removed from both the outcome and the indicator.

Everything here is known in advance (calendar, festivals, the Moon's phase) or
joined with a stated lag (:func:`macro_join`), so no term uses data from after
bar t. Past data only; nothing here forecasts.
"""

from __future__ import annotations

from typing import Dict, Optional

import numpy as np
import pandas as pd

from ..stats.nulls import circular_shift_offsets
from ..stats.permutation import empirical_p_value
from . import festivals as fest

# Local mid-day in IST, 06:30 UTC: the instant the lunar phase of a date is read.
LUNAR_READ_HOUR_UTC = 6.5


def calendar_terms(index, holidays: Optional[pd.DatetimeIndex] = None) -> pd.DataFrame:
    """Month, weekday, turn-of-month and holiday terms for a daily index.

    Columns (all 0/1): ``month_02`` .. ``month_12`` (January is the reference),
    ``wd_1`` .. ``wd_4`` (Tuesday to Friday; Monday is the reference),
    ``turn_of_month`` (last trading day of a month and the first three of the
    next, by position in ``index``), ``holiday_eve`` and ``holiday_after`` (the
    bar just before or after a holiday that is not itself a bar).
    ``holidays`` default to the US federal calendar over the index span.
    """
    idx = pd.DatetimeIndex(index)
    naive = idx.tz_localize(None) if idx.tz is not None else idx
    days = naive.normalize()
    out = pd.DataFrame(index=idx)
    for m in range(2, 13):
        out[f"month_{m:02d}"] = (days.month == m).astype(int)
    for w in range(1, 5):
        out[f"wd_{w}"] = (days.day_of_week == w).astype(int)
    ym = pd.Series(days.year * 12 + days.month, index=idx)
    pos_in_month = ym.groupby(ym.to_numpy()).cumcount().to_numpy()
    pos_from_end = (
        ym.groupby(ym.to_numpy()).cumcount(ascending=False).to_numpy()
    )
    out["turn_of_month"] = ((pos_in_month < 3) | (pos_from_end < 1)).astype(int)
    if holidays is None:
        from pandas.tseries.holiday import USFederalHolidayCalendar

        holidays = USFederalHolidayCalendar().holidays(
            start=days.min() - pd.Timedelta(days=7),
            end=days.max() + pd.Timedelta(days=7),
        )
    hol = pd.DatetimeIndex(holidays).normalize()
    bars = set(days)
    hol = [h for h in hol if h not in bars]
    eve, after = np.zeros(len(days), int), np.zeros(len(days), int)
    for h in hol:
        prev = np.searchsorted(days.values, h.to_datetime64()) - 1
        nxt = prev + 1
        if 0 <= prev < len(days):
            eve[prev] = 1
        if 0 <= nxt < len(days):
            after[nxt] = 1
    out["holiday_eve"], out["holiday_after"] = eve, after
    return out


def lunar_phase_terms(index) -> pd.DataFrame:
    """Lunar-phase terms read at 06:30 UTC (mid-day IST) of each date.

    Columns: ``moon_sin``, ``moon_cos`` (Moon-Sun elongation, sidereal, so the
    same as the tropical one), ``tithi`` (1-30), ``new_moon_day`` (tithi 30 or
    1), ``full_moon_day`` (tithi 14 to 15).
    """
    idx = pd.DatetimeIndex(index)
    naive = idx.tz_localize(None) if idx.tz is not None else idx
    days = naive.normalize()
    elong = np.empty(len(days))
    cache: Dict[pd.Timestamp, float] = {}
    for i, d in enumerate(days):
        if d not in cache:
            jd = d.to_julian_date() + LUNAR_READ_HOUR_UTC / 24.0  # 00:00 UTC + hour
            cache[d] = fest.elongation(jd)
        elong[i] = cache[d]
    tithi = (elong // fest.TITHI_DEG).astype(int) + 1
    rad = np.deg2rad(elong)
    out = pd.DataFrame(index=idx)
    out["moon_sin"], out["moon_cos"] = np.sin(rad), np.cos(rad)
    out["tithi"] = tithi
    out["new_moon_day"] = np.isin(tithi, (30, 1)).astype(int)
    out["full_moon_day"] = np.isin(tithi, (14, 15)).astype(int)
    return out


def macro_join(
    index, macro: pd.Series, release_lag_days: int = 0, name: Optional[str] = None
) -> pd.Series:
    """Align a macro series to bars using only values known at t-1.

    A value observed on date ``s`` is taken to be public from the end of date
    ``s + release_lag_days`` (use the series' real publication lag; 0 for a
    market close). Bar ``t`` gets the latest value public on or before ``t-1``
    calendar day, so a same-day print is never used. Bars before the first
    known value are NaN. No value is ever filled backwards.
    """
    idx = pd.DatetimeIndex(index)
    s = macro.dropna().sort_index()
    s_idx = pd.DatetimeIndex(s.index)
    if s_idx.tz is not None:
        s_idx = s_idx.tz_localize(None)
    known = pd.DataFrame(
        {"known": s_idx.normalize() + pd.Timedelta(days=int(release_lag_days)), "v": s.to_numpy()}
    ).sort_values("known")
    naive = idx.tz_localize(None) if idx.tz is not None else idx
    bars = pd.DataFrame({"cut": naive.normalize() - pd.Timedelta(days=1)})
    bars["order"] = np.arange(len(bars))
    merged = pd.merge_asof(
        bars.sort_values("cut"), known, left_on="cut", right_on="known",
        direction="backward",
    ).sort_values("order")
    return pd.Series(merged["v"].to_numpy(), index=idx, name=name or macro.name)


def build_baselines(
    index,
    macro: Optional[Dict[str, pd.Series]] = None,
    release_lag_days: Optional[Dict[str, int]] = None,
    festivals: bool = True,
    lunar: bool = True,
) -> pd.DataFrame:
    """Stack calendar, festival, lunar-phase and macro (t-1) terms for ``index``."""
    idx = pd.DatetimeIndex(index)
    parts = [calendar_terms(idx)]
    if festivals:
        ff = fest.festival_flags(idx).astype(int)
        parts.append(ff.loc[:, ff.sum() > 0])
    if lunar:
        parts.append(lunar_phase_terms(idx).drop(columns=["tithi"]))
    for key, series in (macro or {}).items():
        lag = (release_lag_days or {}).get(key, 0)
        parts.append(macro_join(idx, series, lag, name=f"macro_{key}").to_frame())
    return pd.concat(parts, axis=1)


def _residualise(y: np.ndarray, X: np.ndarray) -> np.ndarray:
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    return y - X @ beta


def incremental_test(
    outcome,
    indicator,
    baselines: pd.DataFrame,
    min_shift: int,
    n_draws: int,
    rng: np.random.Generator,
    alternative: str = "two-sided",
) -> Dict:
    """Does ``indicator`` explain ``outcome`` beyond the baselines?

    Both the outcome and the indicator are regressed on the baselines (OLS with
    an intercept) and replaced by their residuals. The statistic is the
    correlation of the two residual series; its null rotates the residual
    indicator circularly by at least ``min_shift`` bars (every admissible
    offset when there are no more than ``n_draws``), which keeps the runs of
    the indicator and the clustering of the outcome. p is
    ``(n_extreme + 1) / (n_shifts + 1)``.

    Rows with a NaN baseline or outcome (for example a macro term before its
    first value) are dropped before anything is fitted; a NaN indicator raises.

    Returns:
        ``r_raw`` (outcome vs indicator), ``r_incremental‵ (after removal), ``p``,
        ``n``, ``n_dropped``, ``n_baseline_terms`` (columns kept after dropping
        constant ones), ``n_shifts``, ``alternative``.
    """
    y = np.asarray(outcome, dtype=float)
    x = np.asarray(indicator, dtype=float)
    if len(y) != len(x) or len(y) != len(baselines):
        raise ValueError("outcome, indicator and baselines must have the same length")
    if np.isnan(x).any():
        raise ValueError("indicator contains NaN")
    B = baselines.to_numpy(dtype=float)
    keep = ~np.isnan(y) & ~np.isnan(B).any(axis=1)
    y, x, B = y[keep], x[keep], B[:, B[keep].std(axis=0) > 0][keep]
    n = len(y)
    X = np.column_stack([np.ones(n), B])
    ry, rx = _residualise(y, X), _residualise(x, X)

    def corr(a, b):
        den = np.sqrt((a * a).sum() * (b * b).sum())
        return float((a * b).sum() / den) if den > 0 else 0.0

    def raw_corr():
        return corr(y - y.mean(), x - x.mean())

    obs = corr(ry, rx)
    offsets = circular_shift_offsets(n, int(min_shift), int(n_draws), rng)
    null = np.array([corr(ry, np.roll(rx, int(k))) for k in offsets])
    return {
        "r_raw": raw_corr(),
        "r_incremental": obs,
        "p": empirical_p_value(obs, null, alternative),
        "n": int(n),
        "n_dropped": int((~keep).sum()),
        "n_baseline_terms": int(B.shape[1]),
        "n_shifts": int(len(offsets)),
        "alternative": alternative,
    }
