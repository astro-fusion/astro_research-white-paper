"""House style for paper figures, with a provenance footer on every figure.

Plain, greyscale-safe matplotlib. Every saved figure carries a footer with
the data hash, git commit and seed so a reader can trace it to a run.
"""

from pathlib import Path
from typing import Any, Dict, Optional, Union

import numpy as np

HOUSE_STYLE: Dict[str, Any] = {
    "figure.dpi": 100,
    "savefig.dpi": 150,
    "font.size": 9,
    "axes.titlesize": 10,
    "axes.labelsize": 9,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.color": "0.88",
    "grid.linewidth": 0.6,
    "legend.frameon": False,
    "lines.linewidth": 1.2,
}
"""rcParams for ``matplotlib.rc_context(HOUSE_STYLE)`` around figure code."""
PALETTE = ("#1f4e79", "#c0504d", "#4f7f3a", "#7f6000", "#5a5a5a", "#7030a0")


def save_figure(
    fig,
    path: Union[str, Path],
    provenance: Dict[str, Any],
    note: Optional[str] = None,
) -> Path:
    """Apply the house style, add the provenance footer and save the figure.

    Args:
        fig: A matplotlib Figure.
        path: Output file (PNG recommended for the website).
        provenance: Needs ``data_sha256``, ``commit`` and ``seed``.
        note: Optional short text appended to the footer.

    Returns:
        The path written.
    """
    missing = [k for k in ("data_sha256", "commit", "seed") if k not in provenance]
    if missing:
        raise KeyError(f"provenance lacks {missing}")
    style = HOUSE_STYLE
    for ax in fig.axes:
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.grid(True, color=style["grid.color"], linewidth=style["grid.linewidth"])
        ax.set_axisbelow(True)
    sha = str(provenance["data_sha256"] or "unknown")[:12]
    commit = str(provenance["commit"] or "unknown")[:10]
    footer = f"data sha256 {sha} | commit {commit} | seed {provenance['seed']}"
    if note:
        footer += f" | {note}"
    fig.text(0.01, 0.005, footer, fontsize=6.5, color="0.35", ha="left", va="bottom")
    fig.subplots_adjust(bottom=max(fig.subplotpars.bottom, 0.14))
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(
        out,
        dpi=style["savefig.dpi"],
        bbox_inches="tight",
        pad_inches=0.08,
        metadata={"Software": None},
    )
    return out


def specification_curve_figure(curve, choices, null_value: float = 1.0,
                               ylabel: str = "Rate ratio", log_scale: bool = True):
    """Return a two-panel figure of a :class:`.speccurve.SpecCurve`.

    Top: estimates sorted by size with their intervals (filled where the
    interval excludes ``null_value``). Bottom: one row per value of each
    choice in ``choices``, marked under the cells that use it. Save it with
    :func:`save_figure`.
    """
    import matplotlib.pyplot as plt

    f = curve.frame
    rows = [(c, v) for c in choices for v in dict.fromkeys(f[c].tolist())]
    with plt.rc_context(HOUSE_STYLE):
        fig, (ax, bx) = plt.subplots(
            2, 1, figsize=(7.0, 2.6 + 0.16 * len(rows)), sharex=True,
            gridspec_kw={"height_ratios": [2.2, max(1.0, 0.16 * len(rows))]},
        )
        x = f["rank"].to_numpy()
        est = f["estimate"].to_numpy()
        ax.vlines(x, f["ci_low"], f["ci_high"], color="0.65", lw=0.8)
        excl = f["excludes_null"].to_numpy()
        ax.plot(x[~excl], est[~excl], "o", ms=3, mfc="white", color=PALETTE[0])
        ax.plot(x[excl], est[excl], "o", ms=3, color=PALETTE[1])
        ax.axhline(null_value, color="0.3", lw=0.8)
        if log_scale:
            ax.set_yscale("log")
        ax.set_ylabel(ylabel)
        ax.set_title(
            f"median {curve.median_estimate:.2f}, joint p = {curve.p_median:.3f}, "
            f"{100 * curve.share_excluding_null:.0f}% of cells exclude the null"
        )
        for j, (c, v) in enumerate(rows):
            used = (f[c] == v).to_numpy()
            bx.plot(x[used], np.full(used.sum(), j), "|", ms=6, color="0.2")
        bx.set_yticks(range(len(rows)))
        bx.set_yticklabels([f"{c} = {v}" for c, v in rows], fontsize=7)
        bx.invert_yaxis()
        bx.set_xlabel("Specification (sorted by estimate)")
    return fig
