"""Time-split evaluation with a frozen out-of-sample period, and Hansen's SPA.

* :func:`time_split` divides a time index into an exploration period and a
  frozen confirmation period, with an optional purge gap before the
  confirmation start (at least the longest window used).
* :func:`walk_forward_splits` yields expanding-window train/test splits.
* :func:`spa_test` is Hansen's (2005) test for superior predictive ability:
  does *any* of ``K`` models beat a benchmark once the search over ``K`` is
  accounted for? It uses the stationary bootstrap and reports the
  consistent, lower and upper p-values. ``(n_ge + 1) / (B + 1)`` is used
  instead of Hansen's ``n_ge / B`` so a p-value is never zero.
"""

from dataclasses import dataclass
from typing import Iterator, Optional, Tuple

import numpy as np
import pandas as pd

from .nulls import stationary_bootstrap_indices


def time_split(
    index, confirm_start, purge: Optional[pd.Timedelta] = None
) -> Tuple[np.ndarray, np.ndarray]:
    """Return boolean masks ``(explore, confirm)`` for a datetime index.

    Rows in ``[confirm_start - purge, confirm_start)`` belong to neither.
    """
    idx = pd.DatetimeIndex(index)
    start = pd.Timestamp(confirm_start)
    if idx.tz is not None and start.tz is None:
        start = start.tz_localize(idx.tz)
    confirm = np.asarray(idx >= start)
    gap_start = start - (purge if purge is not None else pd.Timedelta(0))
    explore = np.asarray(idx < gap_start)
    if not explore.any() or not confirm.any():
        raise ValueError("both periods must contain observations")
    return explore, confirm


def walk_forward_splits(
    n: int, initial: int, step: int, purge: int = 0
) -> Iterator[Tuple[np.ndarray, np.ndarray]]:
    """Yield expanding-window ``(train_idx, test_idx)`` pairs.

    Train is ``[0, end - purge)``, test is ``[end, end + step)`` for
    ``end = initial, initial + step, ...``.
    """
    if initial <= purge or step < 1:
        raise ValueError("need initial > purge and step >= 1")
    end = initial
    while end < n:
        yield np.arange(0, end - purge), np.arange(end, min(end + step, n))
        end += step


@dataclass
class SPAResult:
    """Outcome of :func:`spa_test`."""

    statistic: float
    p_consistent: float
    p_lower: float
    p_upper: float
    best_model: int
    mean_loss_diff: np.ndarray
    n_boot: int


def spa_test(
    benchmark_loss,
    model_losses,
    rng: np.random.Generator,
    n_boot: int = 2000,
    mean_block: float = 10.0,
) -> SPAResult:
    """Run Hansen's SPA test of ``K`` models against a benchmark.

    Args:
        benchmark_loss: Shape ``(n,)`` loss of the benchmark per period.
        model_losses: Shape ``(n, K)`` losses of the candidate models.
        rng: ``np.random.default_rng(seed)``.
        n_boot: Stationary-bootstrap resamples.
        mean_block: Mean block length of the bootstrap.

    Returns:
        :class:`SPAResult`. Small ``p_consistent`` means some model beats the
        benchmark after accounting for the search over models.
    """
    b = np.asarray(benchmark_loss, dtype=float)
    m = np.asarray(model_losses, dtype=float)
    if m.ndim == 1:
        m = m[:, None]
    if m.shape[0] != len(b):
        raise ValueError("loss arrays must have the same length")
    n = len(b)
    d = b[:, None] - m  # positive: model has lower loss
    d_bar = d.mean(axis=0)

    boot_means = np.empty((n_boot, d.shape[1]))
    for i in range(n_boot):
        idx = stationary_bootstrap_indices(n, mean_block, rng)
        boot_means[i] = d[idx].mean(axis=0)
    omega = np.sqrt(n) * boot_means.std(axis=0, ddof=1)
    omega = np.where(omega > 0, omega, np.inf)

    t_obs = max(0.0, float(np.max(np.sqrt(n) * d_bar / omega)))
    threshold = -np.sqrt(2.0 * np.log(np.log(n))) if n > 15 else -np.inf
    mu = {
        "consistent": np.where(np.sqrt(n) * d_bar / omega >= threshold, d_bar, 0.0),
        "lower": np.maximum(d_bar, 0.0),
        "upper": d_bar,
    }
    centred = boot_means - d_bar  # bootstrap fluctuation around the sample mean
    p = {}
    for key, mu_k in mu.items():
        t_star = np.max(np.sqrt(n) * (centred + d_bar - mu_k) / omega, axis=1)
        t_star = np.maximum(t_star, 0.0)
        p[key] = float((np.sum(t_star >= t_obs) + 1) / (n_boot + 1))
    return SPAResult(
        statistic=t_obs,
        p_consistent=p["consistent"],
        p_lower=p["lower"],
        p_upper=p["upper"],
        best_model=int(np.argmax(d_bar)),
        mean_loss_diff=d_bar,
        n_boot=int(n_boot),
    )
