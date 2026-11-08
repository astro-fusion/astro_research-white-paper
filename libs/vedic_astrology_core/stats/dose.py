"""Dose-response trend tests of an outcome across bins of a graded strength.

:func:`dose_response` cuts ``strength`` into ``n_bins`` quantile bins
(ties merge bins, so fewer may result), then

* for a 0/1 outcome runs the Cochran-Armitage test for trend (Cochran 1954;
  Armitage 1955) with scores 0, 1, ... for the bins, and
* for a continuous outcome runs Spearman's rank correlation between the bin
  score and the outcome.

Both p-values assume independent observations. For autocorrelated daily
series use them as descriptions, or wrap the statistic in a circular-shift
null (:mod:`.permutation`).
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats as sps


@dataclass
class DoseResult:
    """Trend test across strength bins."""

    method: str
    statistic: float
    p_value: float
    n_bins: int
    table: pd.DataFrame


def cochran_armitage(score, outcome):
    """Return ``(z, two-sided p)`` of the Cochran-Armitage trend test.

    ``score`` is the per-observation bin score and ``outcome`` is 0/1. The
    statistic is ``z = sum (s - s_bar) y / sqrt(p (1 - p) sum (s - s_bar)^2)``,
    so ``z^2 = N r^2`` with ``r`` the Pearson correlation of score and outcome.
    """
    s = np.asarray(score, dtype=float)
    y = np.asarray(outcome, dtype=float)
    p = y.mean()
    ss = np.sum((s - s.mean()) ** 2)
    if p in (0.0, 1.0) or ss == 0:
        return 0.0, 1.0
    z = float(np.sum((s - s.mean()) * y) / np.sqrt(p * (1 - p) * ss))
    return z, float(2 * sps.norm.sf(abs(z)))


def dose_response(strength, outcome, n_bins: int = 5) -> DoseResult:
    """Trend of ``outcome`` across quantile bins of ``strength``.

    Raises:
        ValueError: If the inputs differ in length or are too short.
    """
    s = np.asarray(strength, dtype=float)
    y = np.asarray(outcome, dtype=float)
    if s.shape != y.shape or s.ndim != 1:
        raise ValueError("strength and outcome must be 1-D and the same length")
    ok = np.isfinite(s) & np.isfinite(y)
    s, y = s[ok], y[ok]
    if len(s) < 3:
        raise ValueError("need at least three observations")
    codes = pd.qcut(pd.Series(s).rank(method="average"), n_bins, labels=False,
                    duplicates="drop")
    # Equal strengths share a rank, so ties never split across bins.
    score = pd.factorize(codes, sort=True)[0]
    binary = set(np.unique(y)).issubset({0.0, 1.0})
    df = pd.DataFrame({"bin": score, "strength": s, "y": y})
    table = (
        df.groupby("bin")
        .agg(n=("y", "size"), strength_min=("strength", "min"),
             strength_max=("strength", "max"), mean_outcome=("y", "mean"))
        .reset_index()
    )
    if binary:
        stat, p = cochran_armitage(score, y)
        method = "cochran_armitage"
    else:
        rho, p = sps.spearmanr(score, y)
        stat, method = float(rho), "spearman"
    return DoseResult(method, float(stat), float(p), int(len(table)), table)
