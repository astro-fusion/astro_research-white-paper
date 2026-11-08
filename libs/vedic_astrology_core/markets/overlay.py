"""Price-versus-indicator overlay: one tidy frame, one standard figure.

:func:`overlay_frame` is the artifact both the paper figure and the website's
interactive explorer read, so nothing on the site exists that the paper
cannot cite. :func:`overlay_plot` draws the standard static figure:

- top panel: log-scale price, shaded indicator windows, event markers
- bottom panel: forward log return over ``horizon`` bars from each bar
- footer (via :func:`..stats.plots.save_figure`): data hash, commit, seed,
  study status (EXPLORATORY or CONFIRMATORY) and source

Plain house style, two colour-blind-safe hues (Okabe-Ito blue and vermilion),
no random numbers.
"""

from typing import Dict, Iterable, Optional, Sequence, Union

import numpy as np
import pandas as pd
from matplotlib.figure import Figure
from matplotlib.ticker import NullFormatter, ScalarFormatter

from ..stats.plots import save_figure
from .align import intervals, on_calendar

INK = "#222222"
MUTED = "#6b6b6b"
WINDOW = "#0072B2"
EVENT = "#D55E00"
GRID = "#e3e3e3"


def forward_log_return(close: Sequence[float], horizon: int) -> np.ndarray:
    """``log C[t+h] - log C[t]`` per bar; NaN where ``t+h`` is past the end."""
    logc = np.log(np.asarray(close, dtype=float))
    out = np.full(len(logc), np.nan)
    if horizon < len(logc):
        out[: len(logc) - horizon] = logc[horizon:] - logc[: len(logc) - horizon]
    return out


def overlay_frame(
    aligned: pd.DataFrame,
    indicators: Union[pd.DataFrame, None] = None,
    horizons: Iterable[int] = (5, 21, 63),
) -> pd.DataFrame:
    """Tidy frame for papers and the site: one row per trading bar.

    Columns: ``date``, ``close``, ``log_return``, ``fwd_<h>`` for each horizon,
    then one 0/1 column per indicator and per ``rule:*`` column of
    ``aligned``.
    """
    trading = aligned[aligned.get("is_trading", True) == True]  # noqa: E712
    out = pd.DataFrame(
        {
            "date": pd.to_datetime(trading["date"]).dt.strftime("%Y-%m-%d").values,
            "close": trading["close"].to_numpy(dtype=float),
        }
    )
    out["log_return"] = np.concatenate([[np.nan], np.diff(np.log(out["close"]))])
    for h in horizons:
        out[f"fwd_{h}"] = forward_log_return(out["close"], h)
    if indicators is not None:
        for col in indicators.columns:
            out[col] = np.asarray(indicators[col], dtype=bool).astype(int)
    for col in [c for c in aligned.columns if str(c).startswith("rule:")]:
        out[col] = trading[col].astype(bool).astype(int).to_numpy()
    return out


def overlay_plot(
    prices: pd.DataFrame,
    events_or_indicator: Union[pd.Series, np.ndarray, Iterable],
    title: str,
    horizon: int = 21,
    provenance: Optional[Dict] = None,
    status: str = "EXPLORATORY",
    label: str = "indicator active",
    path: Optional[str] = None,
):
    """Draw the standard overlay figure and return the matplotlib Figure.

    Args:
        prices: tidy price frame (``date``, ``close``), trading bars only.
        events_or_indicator: a boolean array/Series aligned to ``prices``
            (shaded windows) or an iterable of event dates (markers, mapped
            to the next bar).
        title: figure title (plain text).
        horizon: forward-return horizon in bars for the lower panel.
        provenance: ``data_sha256``, ``commit``, ``seed`` (required to save)
            and optionally ``source``.
        status: ``EXPLORATORY`` or ``CONFIRMATORY``; stamped in the footer.
        path: if given, save there with the provenance footer.
    """
    dates = pd.DatetimeIndex(pd.to_datetime(prices["date"]))
    close = prices["close"].to_numpy(dtype=float)
    fwd = forward_log_return(close, horizon)
    values = events_or_indicator
    is_mask = isinstance(values, (pd.Series, np.ndarray)) and (
        np.asarray(values).dtype == bool and len(values) == len(close)
    )

    fig = Figure(figsize=(9, 5.6))
    ax_price, ax_fwd = fig.subplots(
        2,
        1,
        sharex=True,
        gridspec_kw={"height_ratios": [2.2, 1], "hspace": 0.08},
    )
    for ax in (ax_price, ax_fwd):
        ax.grid(True, color=GRID, linewidth=0.6)
        ax.set_axisbelow(True)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        ax.tick_params(colors=MUTED, labelsize=8)

    ax_price.plot(dates, close, color=INK, linewidth=1.0)
    ax_price.set_yscale("log")
    ax_price.set_ylabel("Price (log scale)", color=MUTED, fontsize=9)
    ax_fwd.plot(dates, fwd, color=MUTED, linewidth=0.6)
    ax_fwd.axhline(0.0, color=INK, linewidth=0.6)
    ax_fwd.set_ylabel(f"Forward {horizon}-day\nlog return", color=MUTED, fontsize=9)

    n_marked = 0
    if is_mask:
        spans = intervals(np.asarray(values, dtype=bool), dates)
        for start, end in spans:
            for ax in (ax_price, ax_fwd):
                ax.axvspan(start, end, color=WINDOW, alpha=0.18, linewidth=0)
        n_marked = len(spans)
        legend = f"{label} ({n_marked} windows, {int(np.sum(values))} bars)"
        ax_price.fill_between([], [], color=WINDOW, alpha=0.18, label=legend)
    else:
        bars = on_calendar(list(values), dates, policy="next_bar")
        n_marked = len(bars)
        ax_price.scatter(
            dates[bars],
            close[bars],
            marker="v",
            s=28,
            color=EVENT,
            edgecolor="white",
            linewidth=0.6,
            zorder=3,
            label=f"{label} (N = {n_marked})",
        )
        ax_fwd.scatter(dates[bars], fwd[bars], s=10, color=EVENT, zorder=3)
    ax_price.legend(loc="upper left", frameon=False, fontsize=8)
    ax_price.set_title(title, loc="left", fontsize=11, color=INK)
    ax_price.yaxis.set_major_formatter(ScalarFormatter())
    ax_price.yaxis.set_minor_formatter(NullFormatter())
    ax_price.set_xlim(dates[0], dates[-1])
    span = f"{dates[0]:%Y-%m-%d} to {dates[-1]:%Y-%m-%d} (full sample)"
    if path is not None:
        note = f"{status} | {span}"
        if provenance and provenance.get("source"):
            note += f" | {provenance['source']}"
        save_figure(fig, path, provenance, note=note)
    return fig
