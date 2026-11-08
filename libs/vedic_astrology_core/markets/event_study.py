"""Event studies around astrological events, on the trading calendar.

For an event mapped to bar ``b`` (first bar on or after the event date, see
:func:`.align.on_calendar`) the forward return over ``h`` bars is
``log C[b+h] - log C[b]``. It starts at the bar on which the event is first
observed (astro state is sampled at or before that bar's close), so it is a
strictly predictive window: nothing at or before ``b`` enters.

Null bands come from :func:`..stats.nulls.stationary_block_bootstrap` of the
daily log returns: each surrogate return series keeps volatility clustering,
is rebuilt into a price path, and the same event bars are read from it.
The bands answer "how large would the mean be at these dates if returns had
the same dependence but no link to the events".
"""

from typing import Dict, Iterable, Optional, Sequence

import numpy as np
import pandas as pd

from ..stats import nulls, rates
from ..stats.permutation import empirical_p_value


def _event_means(logc: np.ndarray, bars: np.ndarray, horizons: Sequence[int]):
    out = []
    for h in horizons:
        valid = bars[bars + h < len(logc)]
        mean = np.mean(logc[valid + h] - logc[valid]) if len(valid) else np.nan
        out.append(float(mean))
    return np.array(out)


def event_study(
    prices: pd.DataFrame,
    event_bars: Iterable[int],
    horizons: Sequence[int] = (5, 21, 63),
    rng: Optional[np.random.Generator] = None,
    n_boot: int = 2000,
    mean_block: float = 20.0,
    ci_level: float = 0.95,
) -> pd.DataFrame:
    """Mean forward log return after events, with block-bootstrap null bands.

    Args:
        prices: trading bars with ``close`` (one row per bar, in order).
        event_bars: bar positions of the events (from ``on_calendar``).
        horizons: forward horizons in bars.
        rng: ``np.random.default_rng(seed)`` (required).
        n_boot: number of stationary-bootstrap surrogates.
        mean_block: mean block length of the bootstrap, in bars.
        ci_level: width of the null band.

    Returns:
        One row per horizon: ``horizon``, ``n_events`` (events with a full
        window), ``mean``, ``null_mean``, ``null_lo``, ``null_hi``,
        ``p_value`` (two-sided, ``(k+1)/(B+1)``), ``unconditional`` (mean
        h-bar return over all bars).
    """
    if rng is None:
        raise TypeError("rng must be np.random.default_rng(seed)")
    close = prices["close"].to_numpy(dtype=float)
    logc = np.log(close)
    bars = np.asarray(sorted(set(int(b) for b in event_bars)), dtype=int)
    if len(bars) == 0:
        raise ValueError("no events")
    returns = np.diff(logc)
    observed = _event_means(logc, bars, horizons)
    boots = np.empty((n_boot, len(horizons)))
    for i in range(n_boot):
        r = nulls.stationary_block_bootstrap(returns, mean_block, rng)
        path = np.concatenate([[logc[0]], logc[0] + np.cumsum(r)])
        boots[i] = _event_means(path, bars, horizons)
    tail = (1.0 - ci_level) / 2.0 * 100.0
    rows = []
    for j, h in enumerate(horizons):
        n_ev = int(np.sum(bars + h < len(logc)))
        uncond = float(np.mean(logc[h:] - logc[:-h])) if h < len(logc) else np.nan
        lo, hi = np.nanpercentile(boots[:, j], [tail, 100.0 - tail])
        rows.append(
            {
                "horizon": int(h),
                "n_events": n_ev,
                "mean": observed[j],
                "null_mean": float(np.nanmean(boots[:, j])),
                "null_lo": float(lo),
                "null_hi": float(hi),
                "p_value": empirical_p_value(observed[j], boots[:, j], "two-sided"),
                "unconditional": uncond,
            }
        )
    return pd.DataFrame(rows)


def event_profile(
    prices: pd.DataFrame, event_bars: Iterable[int], pre: int = 10, post: int = 63
) -> pd.DataFrame:
    """Mean cumulative log return from bar ``b`` for offsets ``-pre..post``.

    Only events with the full window are used; ``n_events`` says how many.
    """
    logc = np.log(prices["close"].to_numpy(dtype=float))
    bars = np.asarray(sorted(set(int(b) for b in event_bars)), dtype=int)
    bars = bars[(bars - pre >= 0) & (bars + post < len(logc))]
    offsets = np.arange(-pre, post + 1)
    paths = logc[bars[:, None] + offsets[None, :]] - logc[bars][:, None]
    return pd.DataFrame(
        {
            "offset": offsets,
            "mean_cum_return": paths.mean(axis=0) if len(bars) else np.nan,
            "n_events": len(bars),
        }
    )


def rate_during_vs_outside(
    event_flags: Iterable[bool],
    indicator: Iterable[bool],
    rng: Optional[np.random.Generator] = None,
    min_shift: int = 400,
    n_draws: int = 10000,
    alternative: str = "two-sided",
) -> Dict:
    """Event rate on indicator-active bars versus inactive bars.

    For volatility events (e.g. extreme-move days). Exposure is counted in
    trading bars. With ``rng`` the ratio is also tested against circular
    shifts of the indicator (:func:`..stats.rates.rate_ratio_shift_test`).
    """
    flags = np.asarray(list(event_flags), dtype=bool)
    ind = np.asarray(list(indicator), dtype=bool)
    if len(flags) != len(ind):
        raise ValueError("event_flags and indicator must have the same length")
    event_bins = np.flatnonzero(flags)
    exact = rates.indicator_rate_ratio(event_bins, ind)
    out = {
        "n_in": exact.n_in,
        "bars_in": exact.t_in,
        "n_out": exact.n_out,
        "bars_out": exact.t_out,
        "rate_in": exact.n_in / exact.t_in if exact.t_in else np.nan,
        "rate_out": exact.n_out / exact.t_out if exact.t_out else np.nan,
        "rate_ratio": exact.rate_ratio,
        "ci_low": exact.ci_low,
        "ci_high": exact.ci_high,
        "p_exact": exact.p_two_sided,
    }
    if rng is not None:
        shift = rates.rate_ratio_shift_test(
            event_bins, ind, min_shift, n_draws, rng, alternative=alternative
        )
        out.update(
            {
                "p_shift": shift.p_value,
                "null_q025": shift.null_q025,
                "null_q975": shift.null_q975,
            }
        )
    return out
