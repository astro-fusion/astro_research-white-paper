"""Granger-style test of astrological series as exogenous regressors.

Planetary series are deterministic, so they are never endogenous variables
in a VAR. The test is an autoregressive distributed-lag (ADL) regression of
the outcome on its own lags and on lagged astro regressors, with Newey-West
HAC standard errors, and a Wald test that every astro coefficient is zero:

    y_t = c + sum_i a_i y_{t-i} + sum_k sum_{l in lags} b_{k,l} x_{k,t-l} + e_t

Rules enforced here:

* The lag set is fixed a priori by the caller (no AIC search on the data).
* The outcome passes :func:`.stationarity.stationarity_gate` first; if it is
  still non-stationary after one transform the test is refused.
* ``target="garch_abs"`` replaces the returns by the absolute GARCH(1,1)
  standardised returns computed past-only (:func:`.volatility.past_only_volatility`:
  parameters fitted on data to ``t - 1``, refitted on a fixed schedule,
  burn-in bars dropped), never by a full-sample fit. It needs the optional
  ``arch`` package (``pip install arch``); without it a ``RuntimeError``
  says so and the caller must report the omission instead of silently
  switching target.
* One multiplicity family across all planets and targets is the caller's job
  (:func:`.multiplicity.family`).
"""

from typing import Dict, Optional, Sequence

import numpy as np
import pandas as pd

from . import volatility
from .stationarity import stationarity_gate

TARGETS = ("returns", "garch_abs")


def garch_available() -> bool:
    """Return True if the optional ``arch`` package can be imported."""
    return volatility.garch_available()


def garch_standardised_abs(
    returns: pd.Series, min_train: int = 500, refit_every: int = 21
) -> pd.Series:
    """Return past-only ``|z_t|`` from a constant-mean GARCH(1,1).

    The value at bar ``t`` uses parameters fitted on bars before ``t``
    (see :func:`.volatility.past_only_volatility`); the first ``min_train``
    bars are dropped. Raises ``RuntimeError`` without ``arch``.
    """
    if not garch_available():
        raise RuntimeError(
            "target='garch_abs' needs the optional 'arch' package; "
            "install it or report that the volatility target was omitted"
        )
    return volatility.standardised_abs(
        returns, method="garch", min_train=min_train, refit_every=refit_every
    )


def newey_west_lags(n: int) -> int:
    """Return the Newey-West (1994) rule ``floor(4 (n/100)^(2/9))``."""
    return int(np.floor(4.0 * (n / 100.0) ** (2.0 / 9.0)))


def exog_granger(
    y: pd.Series,
    x: pd.DataFrame,
    lags: Sequence[int] = (1, 2, 3, 4, 5),
    y_lags: Optional[int] = None,
    target: str = "returns",
    hac_maxlags: Optional[int] = None,
    alpha: float = 0.05,
    garch_min_train: int = 500,
    garch_refit_every: int = 21,
) -> Dict:
    """Run the exogenous-regressor ADL Wald test with HAC errors.

    Args:
        y: Outcome series (prices or returns) with an index shared by ``x``.
        x: Astro regressors (columns), aligned to ``y``'s index.
        lags: A-priori lags of every astro regressor (positive integers).
        y_lags: Autoregressive lags of the outcome (default ``max(lags)``).
        target: "returns" (the gated series) or "garch_abs".
        hac_maxlags: Newey-West truncation (default :func:`newey_west_lags`).
        alpha: Level for the stationarity gate.
        garch_min_train: Burn-in bars of the past-only GARCH standardisation
            (target "garch_abs" only); these bars are dropped.
        garch_refit_every: Refit schedule of that standardisation, in bars.

    Returns:
        Dict with the gate verdict and transform, the Wald statistic, degrees
        of freedom, p-value, ``n`` and the HAC truncation. ``p_value`` is
        ``None`` when the gate refused the test.
    """
    import statsmodels.api as sm

    if target not in TARGETS:
        raise ValueError(f"target must be one of {TARGETS}")
    lags = sorted(int(v) for v in lags)
    if not lags or lags[0] < 1:
        raise ValueError("lags must be positive integers fixed a priori")
    y_lags = max(lags) if y_lags is None else int(y_lags)

    gate = stationarity_gate(y, alpha=alpha)
    out = {
        "verdict": gate.verdict,
        "transform": gate.transform,
        "target": target,
        "lags": lags,
        "y_lags": y_lags,
        "p_value": None,
    }
    if not gate.stationary:
        out["reason"] = "outcome non-stationary after one transform"
        return out
    series = gate.series
    if target == "garch_abs":
        series = garch_standardised_abs(
            series, min_train=garch_min_train, refit_every=garch_refit_every
        )

    x = pd.DataFrame(x)
    cols = {"y": series}
    for i in range(1, y_lags + 1):
        cols[f"y_lag{i}"] = series.shift(i)
    exog_names = []
    for c in x.columns:
        xs = x[c].reindex(series.index)
        for lag in lags:
            name = f"{c}_lag{lag}"
            cols[name] = xs.shift(lag)
            exog_names.append(name)
    frame = pd.DataFrame(cols).dropna()
    n = len(frame)
    if n < 10 * (len(exog_names) + y_lags + 1):
        raise ValueError("too few observations for the requested lag set")
    maxlags = newey_west_lags(n) if hac_maxlags is None else int(hac_maxlags)
    design = sm.add_constant(frame.drop(columns="y"))
    fit = sm.OLS(frame["y"], design).fit(cov_type="HAC", cov_kwds={"maxlags": maxlags})
    restriction = np.zeros((len(exog_names), design.shape[1]))
    for row, name in enumerate(exog_names):
        restriction[row, list(design.columns).index(name)] = 1.0
    wald = fit.wald_test(restriction, use_f=True, scalar=True)
    out.update(
        {
            "n": int(n),
            "hac_maxlags": maxlags,
            "f_stat": float(wald.statistic),
            "df_num": int(wald.df_num),
            "df_denom": float(wald.df_denom),
            "p_value": float(wald.pvalue),
            "exog_coefficients": {k: float(fit.params[k]) for k in exog_names},
        }
    )
    return out
