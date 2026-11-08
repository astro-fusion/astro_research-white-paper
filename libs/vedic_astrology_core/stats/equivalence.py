"""Equivalence tests and agreement statistics.

A non-significant correlation or association test does not show that two
series are unrelated; it only fails to show that they are related. To claim
"no meaningful relation" a study fixes an equivalence margin in its
pre-registration and runs two one-sided tests (TOST, Schuirmann 1987): the
estimate is shown to lie above the lower bound *and* below the upper bound.

* :func:`tost` runs TOST on any estimate with a standard error (z, or t with
  ``df``), e.g. a Fisher-z correlation or a kappa.
* :func:`cohen_kappa_ci` gives Cohen's kappa for two categorical series with
  the Fleiss-Cohen-Everitt (1969) asymptotic standard error, or with a
  stationary block bootstrap when consecutive observations are dependent.
"""

from dataclasses import dataclass
from typing import Hashable, Optional, Sequence

import numpy as np
from scipy import stats as sps

from .nulls import _check_rng, stationary_bootstrap_indices


@dataclass
class TostResult:
    """Two one-sided tests of ``low < theta < high``."""

    estimate: float
    se: float
    low: float
    high: float
    p_lower: float
    p_upper: float
    p_value: float
    equivalent: bool
    ci_low: float
    ci_high: float
    alpha: float
    df: Optional[float]


def tost(
    estimate: float,
    se: float,
    low: float,
    high: float,
    alpha: float = 0.05,
    df: Optional[float] = None,
) -> TostResult:
    """Return the TOST equivalence test of ``estimate`` against ``(low, high)``.

    ``p_lower`` tests H0: theta <= low and ``p_upper`` tests H0:
    theta >= high; equivalence is shown when the larger of the two is below
    ``alpha``. This is the same decision as the ``1 - 2 alpha`` confidence
    interval (``ci_low``, ``ci_high``) lying inside the margin.

    Raises:
        ValueError: If ``se`` is not positive or ``low >= high``.
    """
    if not se > 0:
        raise ValueError("se must be positive")
    if not low < high:
        raise ValueError("low must be below high")
    dist = sps.norm if df is None else sps.t(df)
    p_lower = float(dist.sf((estimate - low) / se))
    p_upper = float(dist.cdf((estimate - high) / se))
    p_value = max(p_lower, p_upper)
    q = float(dist.ppf(1.0 - alpha))
    return TostResult(
        estimate=float(estimate),
        se=float(se),
        low=float(low),
        high=float(high),
        p_lower=p_lower,
        p_upper=p_upper,
        p_value=p_value,
        equivalent=bool(p_value < alpha),
        ci_low=float(estimate - q * se),
        ci_high=float(estimate + q * se),
        alpha=float(alpha),
        df=None if df is None else float(df),
    )


@dataclass
class KappaResult:
    """Cohen's kappa with a confidence interval."""

    kappa: float
    observed_agreement: float
    expected_agreement: float
    n: int
    se: float
    ci_low: float
    ci_high: float
    ci_level: float
    method: str
    n_boot: int
    mean_block: Optional[float]


def _kappa_parts(table: np.ndarray):
    n = table.sum()
    p = table / n
    rows, cols = p.sum(axis=1), p.sum(axis=0)
    po = float(np.trace(p))
    pe = float(rows @ cols)
    return p, rows, cols, po, pe


def _kappa(table: np.ndarray) -> float:
    _, _, _, po, pe = _kappa_parts(table)
    return (po - pe) / (1.0 - pe) if pe < 1 else float("nan")


def _kappa_se(table: np.ndarray) -> float:
    """Fleiss, Cohen and Everitt (1969) large-sample SE of kappa."""
    n = table.sum()
    p, rows, cols, po, pe = _kappa_parts(table)
    diag = np.diag(p)
    a = float(np.sum(diag * ((1 - pe) - (rows + cols) * (1 - po)) ** 2))
    off = p.copy()
    np.fill_diagonal(off, 0.0)
    b = float((1 - po) ** 2 * np.sum(off * (cols[:, None] + rows[None, :]) ** 2))
    c = (po * pe - 2 * pe + po) ** 2
    var = (a + b - c) / (n * (1 - pe) ** 4)
    return float(np.sqrt(max(var, 0.0)))


def _codes(a, b, labels):
    a, b = list(a), list(b)
    if len(a) != len(b):
        raise ValueError("the two ratings must have the same length")
    if labels is None:
        labels = sorted(set(a) | set(b), key=repr)
    index = {k: i for i, k in enumerate(labels)}
    try:
        return (
            np.array([index[x] for x in a]),
            np.array([index[x] for x in b]),
            len(labels),
        )
    except KeyError as exc:
        raise ValueError(f"rating {exc.args[0]!r} is not in labels") from None


def _table(ca: np.ndarray, cb: np.ndarray, k: int) -> np.ndarray:
    return np.bincount(ca * k + cb, minlength=k * k).reshape(k, k).astype(float)


def cohen_kappa_ci(
    a: Sequence[Hashable],
    b: Sequence[Hashable],
    labels: Optional[Sequence[Hashable]] = None,
    ci_level: float = 0.95,
    n_boot: int = 0,
    mean_block: Optional[float] = None,
    rng: Optional[np.random.Generator] = None,
) -> KappaResult:
    """Return Cohen's kappa of two paired categorical series with a CI.

    With ``n_boot == 0`` the interval is ``kappa +- z * se`` with the
    Fleiss-Cohen-Everitt asymptotic SE, which assumes independent pairs.
    With ``n_boot > 0`` the pairs are resampled by a stationary block
    bootstrap (mean block length ``mean_block``) and the SE is the bootstrap
    standard deviation and the interval the percentile interval; use it for
    time series, where consecutive pairs are dependent.

    Raises:
        ValueError: On unequal lengths, a rating outside ``labels``, or a
            bootstrap without ``mean_block`` and an explicit ``rng``.
    """
    ca, cb, k = _codes(a, b, labels)
    table = _table(ca, cb, k)
    kappa = _kappa(table)
    _, _, _, po, pe = _kappa_parts(table)
    n = len(ca)
    if n_boot <= 0:
        se = _kappa_se(table)
        z = float(sps.norm.ppf(0.5 + ci_level / 2))
        return KappaResult(
            kappa,
            po,
            pe,
            n,
            se,
            kappa - z * se,
            kappa + z * se,
            ci_level,
            "analytic",
            0,
            None,
        )
    if mean_block is None or rng is None:
        raise ValueError("a bootstrap needs mean_block and rng")
    _check_rng(rng)
    draws = np.empty(n_boot)
    for i in range(n_boot):
        idx = stationary_bootstrap_indices(n, mean_block, rng)
        draws[i] = _kappa(_table(ca[idx], cb[idx], k))
    tail = (1 - ci_level) / 2
    lo, hi = np.nanquantile(draws, [tail, 1 - tail])
    return KappaResult(
        kappa,
        po,
        pe,
        n,
        float(np.nanstd(draws, ddof=1)),
        float(lo),
        float(hi),
        ci_level,
        "block_bootstrap",
        int(n_boot),
        float(mean_block),
    )
