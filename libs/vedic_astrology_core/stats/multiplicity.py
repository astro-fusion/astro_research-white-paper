"""Multiple-comparison corrections applied to one family of tests.

A family is every (rule, target) pair a study tests, including every
parameter sweep and window. Correct once across the whole family, never per
planet or per table.

* ``"bh"``: Benjamini-Hochberg (1995) false discovery rate, valid under
  independence or positive regression dependence.
* ``"by"``: Benjamini-Yekutieli (2001), valid under any dependence; the BH
  q-values times the harmonic number ``sum(1/i)``.
* ``"bonferroni"``: family-wise error rate, ``min(1, m * p)``.
"""

from typing import Sequence

import numpy as np
import pandas as pd

METHODS = ("bh", "by", "bonferroni")


def bonferroni(p_values) -> np.ndarray:
    """Return Bonferroni-adjusted p-values ``min(1, m p)``."""
    p = _as_p(p_values)
    return np.minimum(1.0, p * len(p))


def benjamini_hochberg(p_values) -> np.ndarray:
    """Return Benjamini-Hochberg q-values (step-up, monotone, capped at 1)."""
    return _step_up(_as_p(p_values), 1.0)


def benjamini_yekutieli(p_values) -> np.ndarray:
    """Return Benjamini-Yekutieli q-values (BH times ``sum_{i<=m} 1/i``)."""
    p = _as_p(p_values)
    c_m = float(np.sum(1.0 / np.arange(1, len(p) + 1))) if len(p) else 1.0
    return _step_up(p, c_m)


def adjust(p_values, method: str = "by") -> np.ndarray:
    """Adjust p-values with ``"bh"``, ``"by"`` or ``"bonferroni"``."""
    if method == "bh":
        return benjamini_hochberg(p_values)
    if method == "by":
        return benjamini_yekutieli(p_values)
    if method == "bonferroni":
        return bonferroni(p_values)
    raise ValueError(f"method must be one of {METHODS}, got {method!r}")


def family(
    results: pd.DataFrame,
    method: str = "by",
    p_col: str = "p_value",
    keys: Sequence[str] = ("rule", "target"),
    alpha: float = 0.05,
) -> pd.DataFrame:
    """Apply one correction across every (rule, target) pair in ``results``.

    Args:
        results: One row per test with the key columns and ``p_col``.
        method: Correction method, see :data:`METHODS`.
        p_col: Column of raw p-values.
        keys: Columns that identify a test; duplicates are an error because
            each test must enter the family exactly once.
        alpha: Level for the ``significant`` column.

    Returns:
        A copy with ``q_value``, ``significant``, ``correction`` and
        ``family_size`` columns.
    """
    keys = list(keys)
    missing = [k for k in keys + [p_col] if k not in results.columns]
    if missing:
        raise KeyError(f"results lacks columns {missing}")
    if results.duplicated(subset=keys).any():
        raise ValueError(f"duplicate tests for keys {keys}")
    out = results.copy()
    out["q_value"] = adjust(out[p_col].to_numpy(dtype=float), method)
    out["significant"] = out["q_value"] < alpha
    out["correction"] = method
    out["family_size"] = len(out)
    return out


def _as_p(p_values) -> np.ndarray:
    p = np.asarray(p_values, dtype=float).ravel()
    if np.any(np.isnan(p)):
        raise ValueError("p-values contain NaN")
    if np.any((p < 0) | (p > 1)):
        raise ValueError("p-values must lie in [0, 1]")
    return p


def _step_up(p: np.ndarray, c_m: float) -> np.ndarray:
    m = len(p)
    if m == 0:
        return p.copy()
    order = np.argsort(p)
    ranked = p[order] * m * c_m / np.arange(1, m + 1)
    ranked = np.minimum.accumulate(ranked[::-1])[::-1]
    q = np.empty(m)
    q[order] = np.minimum(1.0, ranked)
    return q
