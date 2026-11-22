"""Past-only volatility standardisation and a GARCH-X variance-equation test.

Two tools for volatility outcomes (ADR-004 WP-05, review item M1):

* :func:`past_only_volatility` standardises returns with a conditional
  volatility whose parameters were fitted on data up to ``t - 1`` only. The
  model is refitted on a fixed schedule (every ``refit_every`` bars after a
  first ``min_train`` bars, expanding window), and between refits the
  variance recursion is run forward with the last fitted parameters, so the
  volatility at bar ``t`` uses returns up to ``t - 1`` only and ``z_t`` adds
  just ``r_t`` in the numerator. Changing data after ``t`` cannot change any
  value up to ``t``. Bars before ``min_train`` are ``NaN``.

  ``method="garch"`` fits a constant-mean GARCH(1,1) with the optional
  ``arch`` package (``pip install arch``). Without it a ``RuntimeError`` is
  raised; there is no silent fallback to another model. ``method="ewma"``
  (RiskMetrics, fixed ``lambda``, nothing fitted) is a separate, explicit
  choice that needs no optional package.

* :func:`garch_x_test` puts an indicator into the variance equation,

      h_t = exp(a + gamma x_t + d'z_t) + alpha e_{t-1}^2 + beta h_{t-1},
      e_t = r_t - mu,

  where ``z_t`` are optional controls (macro or calendar terms known before
  bar ``t``) present in both models. The statistic is the likelihood ratio
  of this model against the same model with ``gamma = 0``. Its p-value comes
  from the circular-shift null (:func:`.nulls.circular_shift_offsets`): the
  indicator is rotated by every admissible offset (or by distinct random
  offsets), the unrestricted model is refitted for each, and
  ``p = (1 + #{LR_shift >= LR}) / (1 + n_shifts)``. The chi-square
  reference distribution is never used, because the indicator's long runs
  and volatility regimes make it anti-conservative. The intercept enters as
  ``exp(...)`` so the variance stays positive for any ``gamma`` and any sign
  of the indicator; ``gamma`` is the log ratio of the variance intercept
  with and without the indicator. The likelihood is Gaussian (quasi-ML) and
  needs only numpy and scipy, because ``arch`` has no exogenous terms in the
  variance equation. The fit is a full-sample fit on purpose: it is an
  inference model, not an outcome transform.
"""

from typing import Dict, Optional, Tuple

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.signal import lfilter

from .nulls import _check_rng, circular_shift_offsets, shift_null_info

METHODS = ("garch", "ewma")
_MAX_PERSISTENCE = 0.9999
_LOG_2PI = float(np.log(2.0 * np.pi))


def garch_available() -> bool:
    """Return True if the optional ``arch`` package can be imported."""
    try:
        import arch  # noqa: F401
    except ImportError:
        return False
    return True


def _require_arch() -> None:
    if not garch_available():
        raise RuntimeError(
            "method='garch' needs the optional 'arch' package (pip install arch); "
            "install it or report that the volatility-standardised outcome was omitted"
        )


def _fit_garch11(train: np.ndarray) -> Tuple[float, float, float, float]:
    """Fit a constant-mean GARCH(1,1) and return (mu, omega, alpha, beta).

    ``train`` is already on the fitting scale (percent returns). Only the
    data passed in are used, so the caller decides what is "past".
    """
    _require_arch()
    from arch import arch_model

    res = arch_model(train, mean="Constant", vol="GARCH", p=1, q=1, rescale=False).fit(
        disp="off", show_warning=False
    )
    p = res.params
    return float(p["mu"]), float(p["omega"]), float(p["alpha[1]"]), float(p["beta[1]"])


def _garch_filter(e: np.ndarray, omega: float, alpha: float, beta: float, h0: float) -> np.ndarray:
    """Return h_t = omega + alpha e_{t-1}^2 + beta h_{t-1}, with h_0 = h0."""
    h = np.empty(len(e))
    h[0] = h0
    if len(e) > 1:
        u = omega + alpha * e[:-1] ** 2
        h[1:] = lfilter([1.0], [1.0, -beta], u, zi=[beta * h0])[0]
    return h


def past_only_volatility(
    returns: pd.Series,
    method: str = "garch",
    min_train: int = 500,
    refit_every: int = 21,
    ewma_lambda: float = 0.94,
) -> pd.DataFrame:
    """Return past-only conditional mean, volatility and standardised returns.

    Args:
        returns: Return series (any index); ``NaN`` values are dropped first.
        method: "garch" (needs ``arch``) or "ewma".
        min_train: Bars used before the first value is produced (and by the
            first GARCH fit). Rows at positions ``< min_train`` are ``NaN``.
        refit_every: Fixed refit schedule: the parameters used for bars
            ``[k, k + refit_every)`` were fitted on bars ``[0, k)``, with
            ``k = min_train + j * refit_every``.
        ewma_lambda: Decay of the EWMA variance (method "ewma" only).

    Returns:
        DataFrame on the returns' index with columns ``mu``, ``sigma``
        (same units as ``returns``), ``z = (r - mu) / sigma`` and
        ``fit_end`` (first bar position *not* used by the fit behind the row;
        -1 in the burn-in).

    Raises:
        RuntimeError: method "garch" without the ``arch`` package.
        ValueError: bad arguments or too few observations.
    """
    if method not in METHODS:
        raise ValueError(f"method must be one of {METHODS}")
    min_train, refit_every = int(min_train), int(refit_every)
    if min_train < 2 or refit_every < 1:
        raise ValueError("min_train must be >= 2 and refit_every >= 1")
    if method == "garch":
        _require_arch()
    elif not 0.0 < float(ewma_lambda) < 1.0:
        raise ValueError("ewma_lambda must lie in (0, 1)")
    r = pd.Series(returns).dropna().astype(float)
    n = len(r)
    if n <= min_train:
        raise ValueError(f"need more than min_train={min_train} observations, got {n}")
    x = r.to_numpy()
    mu = np.full(n, np.nan)
    sigma = np.full(n, np.nan)
    fit_end = np.full(n, -1, dtype=np.int64)

    if method == "ewma":
        # h at min_train is seeded from bars [0, min_train); each later h_t
        # adds r_{t-1}, so nothing at or after t enters sigma_t.
        lam = float(ewma_lambda)
        h = np.empty(n)
        h[min_train] = float(np.mean(x[:min_train] ** 2))
        if n > min_train + 1:
            u = (1.0 - lam) * x[min_train:-1] ** 2
            h[min_train + 1 :] = lfilter([1.0], [1.0, -lam], u, zi=[lam * h[min_train]])[0]
        mu[min_train:] = 0.0
        sigma[min_train:] = np.sqrt(h[min_train:])
        fit_end[min_train:] = np.arange(min_train, n)
    else:
        scaled = 100.0 * x
        for k in range(min_train, n, refit_every):
            stop = min(k + refit_every, n)
            train = scaled[:k]
            m, omega, alpha, beta = _fit_garch11(train)
            h0 = float(np.mean((train - m) ** 2))
            # h_t for t < stop uses e up to t - 1; the fit used bars < k <= t.
            h = _garch_filter(scaled[:stop] - m, omega, alpha, beta, h0)
            mu[k:stop] = m / 100.0
            sigma[k:stop] = np.sqrt(h[k:stop]) / 100.0
            fit_end[k:stop] = k
    out = pd.DataFrame({"mu": mu, "sigma": sigma}, index=r.index)
    out["z"] = (r - out["mu"]) / out["sigma"]
    out["fit_end"] = fit_end
    return out


def standardised_abs(returns: pd.Series, **kwargs) -> pd.Series:
    """Return ``|z_t|`` from :func:`past_only_volatility`, burn-in dropped."""
    return past_only_volatility(returns, **kwargs)["z"].abs().dropna()


# --------------------------------------------------------------------------
# GARCH-X
# --------------------------------------------------------------------------


def _unpack(theta: np.ndarray, n_x: int, n_z: int):
    mu, a, pers, share = theta[:4]
    alpha, beta = pers * share, pers * (1.0 - share)
    gamma = theta[4 : 4 + n_x]
    delta = theta[4 + n_x : 4 + n_x + n_z]
    return mu, a, alpha, beta, gamma, delta


def _nll(theta: np.ndarray, r: np.ndarray, X: np.ndarray, Z: np.ndarray, h0: float) -> float:
    mu, a, alpha, beta, gamma, delta = _unpack(theta, X.shape[1], Z.shape[1])
    log_omega = a + X @ gamma + Z @ delta
    if np.any(log_omega > 50.0):
        return 1e300
    omega = np.exp(log_omega)
    e = r - mu
    h = np.empty(len(r))
    h[0] = h0
    u = omega[1:] + alpha * e[:-1] ** 2
    h[1:] = lfilter([1.0], [1.0, -beta], u, zi=[beta * h0])[0]
    if not np.all(np.isfinite(h)) or np.any(h <= 0.0):
        return 1e300
    return 0.5 * float(np.sum(_LOG_2PI + np.log(h) + e**2 / h))


def _fit(r, X, Z, h0, start, free_x: bool):
    n_x, n_z = X.shape[1], Z.shape[1]
    bounds = [(None, None), (-30.0, 30.0), (0.0, _MAX_PERSISTENCE), (0.0, 1.0)]
    bounds += [(-20.0, 20.0) if free_x else (0.0, 0.0)] * n_x
    bounds += [(-20.0, 20.0)] * n_z
    res = minimize(_nll, start, args=(r, X, Z, h0), method="L-BFGS-B", bounds=bounds)
    return res.x, float(res.fun)


def _restricted_start(r: np.ndarray, n_x: int, n_z: int) -> np.ndarray:
    var = float(np.var(r))
    pers, share = 0.95, 0.05 / 0.95
    a = float(np.log(var * (1.0 - pers)))
    return np.concatenate([[float(np.mean(r)), a, pers, share], np.zeros(n_x + n_z)])


def garch_x_test(
    returns,
    indicator,
    controls=None,
    min_shift: int = 400,
    n_shifts: int = 199,
    rng: Optional[np.random.Generator] = None,
) -> Dict:
    """Likelihood-ratio test of an indicator in the GARCH(1,1) variance equation.

    Args:
        returns: Return series (1-D, finite) on a regular bar grid.
        indicator: Array or DataFrame aligned to ``returns`` (one column per
            indicator term), known before each bar (an astrological calendar
            is). All columns are rotated together under the null.
        controls: Optional array or DataFrame of terms present in both the
            null and alternative models and never rotated.
        min_shift: Smallest circular shift, in bars (at least the longest
            period of the indicator).
        n_shifts: Number of shifts; every admissible shift is used (an exact
            test) when there are no more than this.
        rng: ``np.random.default_rng(seed)`` (required even when exact).

    Returns:
        Dict with ``lr``, ``p_value`` (shift null), ``gamma`` (per indicator
        column), restricted and unrestricted log-likelihoods and parameters,
        ``n``, the null description from :func:`.nulls.shift_null_info` and
        ``null_lr`` (sorted).
    """
    rng = _check_rng(rng)
    r = np.asarray(returns, dtype=float).ravel()
    X = np.asarray(indicator, dtype=float)
    X = X.reshape(len(X), -1) if X.ndim == 1 else X
    Z = np.zeros((len(r), 0)) if controls is None else np.asarray(controls, dtype=float)
    Z = Z.reshape(len(Z), -1) if Z.ndim == 1 else Z
    if len(X) != len(r) or len(Z) != len(r):
        raise ValueError("indicator and controls must be aligned to returns")
    if not (np.all(np.isfinite(r)) and np.all(np.isfinite(X)) and np.all(np.isfinite(Z))):
        raise ValueError("returns, indicator and controls must be finite")
    if np.all(np.ptp(X, axis=0) == 0.0):
        raise ValueError("indicator is constant; nothing to test")
    n, n_x, n_z = len(r), X.shape[1], Z.shape[1]
    if n < 50 * (4 + n_x + n_z):
        raise ValueError("too few observations for a GARCH-X fit")

    scale = float(np.std(r))
    if scale <= 0.0:
        raise ValueError("returns have zero variance")
    rs = r / scale
    h0 = float(np.var(rs))

    theta0, nll0 = _fit(rs, X, Z, h0, _restricted_start(rs, n_x, n_z), free_x=False)
    theta0, nll0 = _fit(rs, X, Z, h0, theta0, free_x=False)

    def unrestricted(xm: np.ndarray) -> Tuple[np.ndarray, float]:
        # Starts at the restricted optimum (gamma = 0), so it can only improve.
        theta, nll = _fit(rs, xm, Z, h0, theta0, free_x=True)
        if nll > nll0:
            return theta0, nll0
        return theta, nll

    theta1, nll1 = unrestricted(X)
    lr = 2.0 * (nll0 - nll1)

    offsets = circular_shift_offsets(n, min_shift, n_shifts, rng)
    null_lr = np.empty(len(offsets))
    for i, off in enumerate(offsets):
        _, nll_b = unrestricted(np.roll(X, int(off), axis=0))
        null_lr[i] = 2.0 * (nll0 - nll_b)
    tol = 1e-8 * max(1.0, lr)
    n_extreme = int(np.sum(null_lr >= lr - tol))
    p_value = (n_extreme + 1) / (len(offsets) + 1) if len(offsets) else None

    def params(theta):
        mu, a, alpha, beta, gamma, delta = _unpack(theta, n_x, n_z)
        return {
            "mu": float(mu) * scale,
            "omega": float(np.exp(a)) * scale**2,
            "alpha": float(alpha),
            "beta": float(beta),
            "gamma": [float(g) for g in gamma],
            "delta": [float(d) for d in delta],
        }

    p1 = params(theta1)
    if isinstance(indicator, pd.DataFrame):
        gamma = dict(zip(map(str, indicator.columns), p1["gamma"]))
    else:
        gamma = p1["gamma"][0] if n_x == 1 else p1["gamma"]
    rescale = -n * float(np.log(scale))
    return {
        "lr": float(lr),
        "p_value": None if p_value is None else float(p_value),
        "n_extreme": n_extreme,
        "gamma": gamma,
        "n": int(n),
        "loglik_restricted": float(-nll0 + rescale),
        "loglik_unrestricted": float(-nll1 + rescale),
        "params_restricted": params(theta0),
        "params_unrestricted": p1,
        "null": "circular_shift",
        **shift_null_info(n, min_shift, n_shifts),
        "null_lr": np.sort(null_lr).tolist(),
    }
