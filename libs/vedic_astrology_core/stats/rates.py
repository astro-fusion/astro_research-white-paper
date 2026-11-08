"""Event-rate ratio during versus outside an indicator.

Exposure is time on a regular grid; events are grid indices. The rate ratio
is ``(n_in / t_in) / (n_out / t_out)``.

* :func:`rate_ratio` gives the exact conditional (binomial) confidence
  interval and p-value: given ``n = n_in + n_out`` events, ``n_in`` is
  binomial with ``p = RR t_in / (RR t_in + t_out)`` (Clopper-Pearson).
  It assumes a Poisson process, so it is anti-conservative for clustered
  events; use it for the interval, not for the test.
* :func:`rate_ratio_shift_test` tests the same ratio against a
  circular-shift null of the indicator, which keeps event clustering and the
  indicator's run structure.
"""

from dataclasses import dataclass

import numpy as np
from scipy import stats as sps

from .nulls import circular_shift_offsets
from .permutation import empirical_p_value


@dataclass
class RateRatio:
    """Rate ratio with an exact Poisson confidence interval."""

    n_in: int
    t_in: float
    n_out: int
    t_out: float
    rate_ratio: float
    ci_low: float
    ci_high: float
    p_greater: float
    p_two_sided: float


@dataclass
class ShiftTest:
    """Rate ratio tested against a circular-shift null."""

    exact: RateRatio
    p_value: float
    null_median: float
    null_q025: float
    null_q975: float
    n_draws: int
    min_shift: int
    alternative: str


def rate_ratio(
    n_in: int, t_in: float, n_out: int, t_out: float, ci_level: float = 0.95
) -> RateRatio:
    """Return the rate ratio with exact conditional binomial CI and p-values.

    Raises:
        ValueError: If an exposure is not positive.
    """
    if t_in <= 0 or t_out <= 0:
        raise ValueError("both exposures must be positive")
    n_in, n_out = int(n_in), int(n_out)
    n = n_in + n_out
    odds_scale = t_out / t_in
    rr = (n_in / t_in) / (n_out / t_out) if n_out > 0 else float("inf")
    if n == 0:
        return RateRatio(n_in, t_in, n_out, t_out, float("nan"), 0.0,
                         float("inf"), 1.0, 1.0)
    a = 1.0 - ci_level
    p_lo = sps.beta.ppf(a / 2, n_in, n - n_in + 1) if n_in > 0 else 0.0
    p_hi = sps.beta.ppf(1 - a / 2, n_in + 1, n - n_in) if n_in < n else 1.0
    lo = p_lo / (1 - p_lo) * odds_scale
    hi = p_hi / (1 - p_hi) * odds_scale if p_hi < 1 else float("inf")
    p0 = t_in / (t_in + t_out)
    p_greater = float(sps.binom.sf(n_in - 1, n, p0))
    p_two = float(sps.binomtest(n_in, n, p0, alternative="two-sided").pvalue)
    return RateRatio(n_in, float(t_in), n_out, float(t_out), float(rr),
                     float(lo), float(hi), p_greater, p_two)


def indicator_rate_ratio(event_bins, indicator, ci_level: float = 0.95) -> RateRatio:
    """Return :func:`rate_ratio` for events (grid indices) and a 0/1 grid."""
    ind = np.asarray(indicator).astype(bool)
    ev = np.asarray(event_bins, dtype=np.int64)
    n_in = int(ind[ev].sum())
    t_in = float(ind.sum())
    return rate_ratio(n_in, t_in, len(ev) - n_in, float(len(ind)) - t_in, ci_level)


def rate_ratio_shift_test(
    event_bins,
    indicator,
    min_shift: int,
    n_draws: int,
    rng: np.random.Generator,
    alternative: str = "greater",
    ci_level: float = 0.95,
) -> ShiftTest:
    """Test the rate ratio against circular shifts of the indicator.

    Exposure is invariant under rotation, so the null distribution of the
    rate ratio is that of the in-indicator event count. Each draw rotates the
    indicator by an offset in ``[min_shift, n - min_shift]``, exactly as
    :func:`.nulls.circular_shift_null` does.
    """
    ind = np.asarray(indicator).astype(bool)
    ev = np.asarray(event_bins, dtype=np.int64)
    n = len(ind)
    exact = indicator_rate_ratio(ev, ind, ci_level)
    offsets = circular_shift_offsets(n, min_shift, n_draws, rng)
    counts = np.empty(len(offsets), dtype=np.int64)
    chunk = max(1, 2_000_000 // max(1, len(ev)))
    for start in range(0, len(offsets), chunk):
        off = offsets[start:start + chunk, None]
        counts[start:start + chunk] = ind[(ev[None, :] - off) % n].sum(axis=1)
    t_in, t_out = exact.t_in, exact.t_out
    n_ev = len(ev)
    with np.errstate(divide="ignore", invalid="ignore"):
        null_rr = (counts / t_in) / ((n_ev - counts) / t_out)
    p = empirical_p_value(exact.n_in, counts, alternative)
    q = np.nanpercentile(null_rr[np.isfinite(null_rr)], [2.5, 50, 97.5])
    return ShiftTest(exact, p, float(q[1]), float(q[0]), float(q[2]),
                     int(n_draws), int(min_shift), alternative)
