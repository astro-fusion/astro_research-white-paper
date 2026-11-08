"""Summary figures for a market study: effect forest plot and event study.

Both read the result tables only (no computation, no random numbers) and are
saved through :func:`..stats.plots.save_figure`, which adds the provenance
footer.
"""

from typing import Dict

import numpy as np
import pandas as pd
from matplotlib.figure import Figure

from ..stats.plots import save_figure

INK = "#222222"
MUTED = "#6b6b6b"
EXPLORE = "#0072B2"
CONFIRM = "#D55E00"
TITLES = {
    "ret": "Daily log return (bp)",
    "absret": "Absolute return (bp)",
    "extreme": "Extreme-move rate (pp)",
}


def effects_figure(tests: pd.DataFrame, provenance: Dict, path: str) -> Figure:
    """Draw active-minus-inactive effects with 95% CIs, explore vs confirm."""
    inds = list(dict.fromkeys(tests["indicator"]))
    fig = Figure(figsize=(10, 0.32 * len(inds) + 1.6))
    axes = fig.subplots(1, 3, sharey=True)
    y = np.arange(len(inds))
    for ax, target in zip(axes, TITLES):
        for period, colour, dy in (("explore", EXPLORE, -0.15),
                                   ("confirm", CONFIRM, 0.15)):
            sub = tests[(tests["target"] == target) & (tests["period"] == period)
                        & tests["testable"]].set_index("indicator").reindex(inds)
            err = np.vstack([sub["effect"] - sub["ci_low"],
                             sub["ci_high"] - sub["effect"]])
            sig = sub["significant"].fillna(False).astype(bool).to_numpy()
            ax.errorbar(sub["effect"], y + dy, xerr=err, fmt="none",
                        ecolor=colour, elinewidth=1.0, alpha=0.8)
            ax.scatter(sub["effect"][~sig], (y + dy)[~sig], s=14,
                       facecolor="white", edgecolor=colour, zorder=3,
                       label=f"{period}: not significant")
            ax.scatter(sub["effect"][sig], (y + dy)[sig], s=18, color=colour,
                       zorder=3, label=f"{period}: BY q < 0.05")
        ax.axvline(0.0, color=INK, linewidth=0.7)
        ax.set_title(TITLES[target], fontsize=9, loc="left", color=INK)
        ax.tick_params(labelsize=7.5, colors=MUTED)
    axes[0].set_yticks(y)
    axes[0].set_yticklabels([i.replace("_", " ") for i in inds])
    axes[0].invert_yaxis()
    handles, labels = axes[0].get_legend_handles_labels()
    height = fig.get_figheight()
    fig.suptitle("Indicator active minus inactive (state on bar t-1, outcome on "
                 "bar t), 95% block-bootstrap CI", fontsize=9,
                 y=1 - 0.12 / height, x=0.01, ha="left")
    fig.legend(handles, labels, loc="upper left", ncol=4, fontsize=7.5,
               frameon=False, bbox_to_anchor=(0.17, 1 - 0.32 / height))
    fig.subplots_adjust(top=1 - 0.95 / height, wspace=0.08, left=0.17)
    save_figure(fig, path, provenance, note="EXPLORATORY and CONFIRMATORY periods")
    return fig


def event_figure(ev: pd.DataFrame, provenance: Dict, path: str) -> Figure:
    """Mean forward return after stations against the bootstrap null band."""
    horizons = sorted(ev["horizon"].unique())
    bodies = list(dict.fromkeys(ev["body"]))
    fig = Figure(figsize=(10, 3.2))
    axes = fig.subplots(1, len(horizons), sharey=False)
    x = np.arange(len(bodies))
    for ax, h in zip(np.atleast_1d(axes), horizons):
        sub = ev[ev["horizon"] == h].set_index("body").reindex(bodies)
        ax.vlines(x, sub["null_lo"], sub["null_hi"], color=MUTED, linewidth=6,
                  alpha=0.35, label="95% null band")
        ax.scatter(x, sub["mean"], color=EXPLORE, s=22, zorder=3,
                   label="mean after station")
        ax.axhline(0.0, color=INK, linewidth=0.6)
        ax.set_xticks(x)
        ax.set_xticklabels([f"{b.title()}\nN={n}" for b, n in
                            zip(bodies, sub["n_events"])], fontsize=7)
        ax.set_title(f"{h}-day forward log return (bp)", fontsize=9, loc="left")
        ax.tick_params(labelsize=7.5, colors=MUTED)
    np.atleast_1d(axes)[0].legend(fontsize=7, frameon=False, loc="upper left")
    fig.subplots_adjust(bottom=0.25, wspace=0.3)
    save_figure(fig, path, provenance, note="retrograde stations, full sample")
    return fig
