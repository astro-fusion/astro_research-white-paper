"""src/diagnostics/statistics.py.

Statistical Validation Layer — Significance and Effect Sizes
===========================================================
Provides utilities for academic-grade verification of experimental data
and astrological correlations.
"""

from __future__ import annotations

import numpy as np
from scipy import stats


def calculate_p_value(group_a: np.ndarray, group_b: np.ndarray) -> float:
    """Calculate the p-value using a two-sample t-test."""
    t_stat, p_val = stats.ttest_ind(group_a, group_b, equal_var=False)
    return float(p_val)


def calculate_cohens_d(group_a: np.ndarray, group_b: np.ndarray) -> float:
    """
    Calculate Cohen's d effect size.

    d = (mean1 - mean2) / pooled_standard_deviation
    """
    m1, m2 = np.mean(group_a), np.mean(group_b)
    s1, s2 = np.var(group_a, ddof=1), np.var(group_b, ddof=1)
    n1, n2 = len(group_a), len(group_b)

    pooled_std = np.sqrt(((n1 - 1) * s1 + (n2 - 1) * s2) / (n1 + n2 - 2))
    return float((m1 - m2) / pooled_std)


def validate_correlation(predicted: np.ndarray, actual: np.ndarray) -> dict[str, float]:
    """Perform a standardized statistical validation of prediction accuracy."""
    pearson_r, p_val = stats.pearsonr(predicted, actual)

    return {
        "pearson_r": float(pearson_r),
        "p_value": float(p_val),
        "is_significant": float(p_val < 0.05),
    }
