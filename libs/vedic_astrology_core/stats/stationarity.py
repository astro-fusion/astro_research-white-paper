"""Stationarity gate: ADF and KPSS before any regression on a series.

The gate tests the raw series. If it is not stationary it applies one
transform, ``log-diff`` for a strictly positive series and ``diff`` otherwise,
and tests again. The verdict says whether the returned series may be used.

Rule: stationary means ADF rejects a unit root (``adf_p < alpha``) **and**
KPSS does not reject level stationarity (``kpss_p >= alpha``).
"""

import warnings
from dataclasses import dataclass, field
from typing import Dict

import numpy as np
import pandas as pd

TRANSFORMS = ("none", "diff", "log-diff")


@dataclass
class StationarityResult:
    """Outcome of :func:`stationarity_gate`.

    Attributes:
        verdict: "stationary" or "nonstationary" for ``series``.
        transform: "none", "diff" or "log-diff", the transform applied.
        series: The (possibly transformed) series, NaNs dropped.
        tests: ADF and KPSS statistics and p-values per transform tried.
    """

    verdict: str
    transform: str
    series: pd.Series
    tests: Dict[str, Dict[str, float]] = field(default_factory=dict)

    @property
    def stationary(self) -> bool:
        """Return True when the verdict is "stationary"."""
        return self.verdict == "stationary"


def adf_kpss(series: pd.Series) -> Dict[str, float]:
    """Return ADF and KPSS statistics and p-values for one series.

    KPSS p-values are interpolated from a table bounded to [0.01, 0.1];
    statsmodels warns at the bounds (and about a future ADF return type);
    those warnings are silenced here.
    """
    from statsmodels.tsa.stattools import adfuller, kpss

    x = pd.Series(series).dropna().to_numpy(dtype=float)
    if len(x) < 20:
        raise ValueError("stationarity tests need at least 20 observations")
    if np.allclose(x, x[0]):
        raise ValueError("series is constant")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        adf_stat, adf_p = adfuller(x, autolag="AIC")[:2]
        kpss_stat, kpss_p = kpss(x, regression="c", nlags="auto")[:2]
    return {
        "adf_stat": float(adf_stat),
        "adf_p": float(adf_p),
        "kpss_stat": float(kpss_stat),
        "kpss_p": float(kpss_p),
    }


def apply_transform(series: pd.Series, transform: str) -> pd.Series:
    """Apply ``"none"``, ``"diff"`` or ``"log-diff"`` and drop NaNs."""
    s = pd.Series(series).astype(float)
    if transform == "none":
        out = s
    elif transform == "diff":
        out = s.diff()
    elif transform == "log-diff":
        if (s.dropna() <= 0).any():
            raise ValueError("log-diff needs a strictly positive series")
        out = np.log(s).diff()
    else:
        raise ValueError(f"transform must be one of {TRANSFORMS}, got {transform!r}")
    return out.dropna()


def is_stationary(tests: Dict[str, float], alpha: float = 0.05) -> bool:
    """Return True when ADF rejects and KPSS does not reject at ``alpha``."""
    return tests["adf_p"] < alpha and tests["kpss_p"] >= alpha


def stationarity_gate(series: pd.Series, alpha: float = 0.05) -> StationarityResult:
    """Test a series and difference it once if needed.

    Args:
        series: The outcome series (prices, returns, counts).
        alpha: Level for both ADF and KPSS.

    Returns:
        :class:`StationarityResult` with the verdict, the transform applied
        and the transformed series.
    """
    raw = pd.Series(series).dropna().astype(float)
    tests = {"none": adf_kpss(raw)}
    if is_stationary(tests["none"], alpha):
        return StationarityResult("stationary", "none", raw, tests)
    transform = "log-diff" if (raw > 0).all() else "diff"
    transformed = apply_transform(raw, transform)
    tests[transform] = adf_kpss(transformed)
    verdict = (
        "stationary" if is_stationary(tests[transform], alpha) else ("nonstationary")
    )
    return StationarityResult(verdict, transform, transformed, tests)
