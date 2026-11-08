"""House style for paper figures, with a provenance footer on every figure.

Plain, greyscale-safe matplotlib. Every saved figure carries a footer with
the data hash, git commit and seed so a reader can trace it to a run.
"""

from pathlib import Path
from typing import Any, Dict, Optional, Union

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
