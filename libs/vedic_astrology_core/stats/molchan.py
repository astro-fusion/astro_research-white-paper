"""Molchan error diagrams on the time axis, with binomial confidence bounds.

For an alarm function (a score on a regular time grid), declaring alarm when
``score >= threshold`` gives

* ``tau``: the fraction of **time** under alarm (grid steps, not event days);
* ``nu``: the fraction of events that fall outside the alarm (misses).

A time-random forecaster lies on ``nu = 1 - tau``. For ``N`` events and
alarm fraction ``tau`` the hit count of a random forecaster is
``Binomial(N, tau)``; :func:`binomial_bound` gives the miss rate a forecaster
must beat to reject randomness at level ``alpha`` (Zechar and Jordan 2008).

The area skill score is ``1 - integral(nu d tau)`` over ``tau`` in [0, 1];
it is 0.5 for the time-random reference. Every curve is sorted by ``tau``
ascending before integration, and nothing here interpolates on a decreasing
axis (the earlier ``np.interp`` on a reversed ``xp`` returned garbage).
"""

from typing import Optional

import numpy as np
import pandas as pd
from scipy import stats as sps

_trapezoid = getattr(np, "trapezoid", None) or getattr(np, "trapz")


def molchan_point(indicator, event_bins) -> tuple:
    """Return ``(tau, nu)`` for a binary alarm on the grid."""
    alarm = np.asarray(indicator).astype(bool)
    ev = np.asarray(event_bins, dtype=np.int64)
    if len(ev) == 0:
        raise ValueError("need at least one event")
    tau = float(alarm.mean())
    nu = float(1.0 - alarm[ev].mean())
    return tau, nu


def molchan_trajectory(score, event_bins, thresholds=None) -> pd.DataFrame:
    """Return the Molchan trajectory of a score, sorted by ``tau`` ascending.

    Args:
        score: Alarm function on the time grid (higher means more alarm).
        event_bins: Grid indices of the events.
        thresholds: Alarm thresholds; default every distinct score value.

    Returns:
        DataFrame with ``threshold``, ``tau``, ``nu``, including the
        end points ``(0, 1)`` and ``(1, 0)``.
    """
    s = np.asarray(score, dtype=float)
    ev = np.asarray(event_bins, dtype=np.int64)
    if len(ev) == 0:
        raise ValueError("need at least one event")
    if thresholds is None:
        thresholds = np.unique(s)
    rows = [{"threshold": np.inf, "tau": 0.0, "nu": 1.0}]
    ev_scores = s[ev]
    for th in np.asarray(thresholds, dtype=float):
        rows.append({
            "threshold": float(th),
            "tau": float(np.mean(s >= th)),
            "nu": float(1.0 - np.mean(ev_scores >= th)),
        })
    rows.append({"threshold": -np.inf, "tau": 1.0, "nu": 0.0})
    df = pd.DataFrame(rows).sort_values(["tau", "nu"], ascending=[True, False])
    return df.reset_index(drop=True)


def area_skill_score(tau, nu) -> float:
    """Return ``1 - integral(nu d tau)`` with ``tau`` sorted ascending.

    The curve is completed with ``(0, 1)`` and ``(1, 0)`` if missing.
    """
    t = np.asarray(tau, dtype=float)
    v = np.asarray(nu, dtype=float)
    order = np.lexsort((-v, t))
    t, v = t[order], v[order]
    if t[0] > 0 or v[0] < 1:
        t, v = np.r_[0.0, t], np.r_[1.0, v]
    if t[-1] < 1 or v[-1] > 0:
        t, v = np.r_[t, 1.0], np.r_[v, 0.0]
    return float(1.0 - _trapezoid(v, t))


def binomial_bound(n_events: int, tau, alpha: float = 0.05) -> np.ndarray:
    """Return the critical miss rate for ``N`` events at alarm fraction ``tau``.

    The critical hit count ``h`` is the smallest ``h`` with
    ``P(Binomial(N, tau) >= h) <= alpha``; the bound is ``1 - h / N``.
    A forecaster with ``nu <= bound`` beats the time-random reference at
    level ``alpha`` (one-sided).
    """
    t = np.atleast_1d(np.asarray(tau, dtype=float))
    n = int(n_events)
    if n < 1:
        raise ValueError("n_events must be at least 1")
    h = np.arange(n + 2)
    out = np.empty_like(t)
    for i, ti in enumerate(t):
        tail = sps.binom.sf(h - 1, n, ti)
        ok = np.flatnonzero(tail <= alpha)
        hc = h[ok[0]] if len(ok) else n + 1
        out[i] = 1.0 - hc / n
    return out


def molchan_p_value(n_events: int, tau: float, nu: float) -> float:
    """Return ``P(hits >= observed)`` for a time-random alarm of fraction tau."""
    hits = int(round((1.0 - nu) * n_events))
    return float(sps.binom.sf(hits - 1, int(n_events), float(tau)))


def time_random_reference(
    score,
    n_events: int,
    rng: np.random.Generator,
    n_sims: int = 1000,
    observed_ass: Optional[float] = None,
) -> dict:
    """Simulate area skill scores of events placed uniformly in time.

    This is the time-random reference model for the given alarm function
    (ties in the score are handled exactly as for the real events).

    Returns:
        Dict with the reference mean, 2.5 and 97.5 percentiles and, when
        ``observed_ass`` is given, the one-sided p-value
        ``(n_ge + 1) / (n_sims + 1)``.
    """
    s = np.asarray(score, dtype=float)
    # tau needed to catch an event at score v is the fraction of time >= v.
    sorted_s = np.sort(s)
    n = len(s)
    asses = np.empty(n_sims)
    for i in range(n_sims):
        ev_scores = s[rng.integers(0, n, size=int(n_events))]
        tau_hi = 1.0 - np.searchsorted(sorted_s, ev_scores, side="left") / n
        tau_lo = 1.0 - np.searchsorted(sorted_s, ev_scores, side="right") / n
        asses[i] = 1.0 - np.mean((tau_hi + tau_lo) / 2.0)
    out = {
        "mean": float(asses.mean()),
        "q025": float(np.percentile(asses, 2.5)),
        "q975": float(np.percentile(asses, 97.5)),
        "n_sims": int(n_sims),
    }
    if observed_ass is not None:
        out["p_value"] = float((np.sum(asses >= observed_ass) + 1) / (n_sims + 1))
    return out
