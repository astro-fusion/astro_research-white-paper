"""Power: the smallest rate ratio a study could have detected.

:func:`minimum_detectable_rate_ratio` answers "with ``n_events`` events and
an indicator active for ``duty_cycle`` of the time, what rate ratio would the
circular-shift test detect with probability ``power`` at level ``alpha``?"
by simulation:

1. Events are a Poisson process: the total count is ``Poisson(n_events)``.
2. Under the circular-shift null each event of a Poisson process lands
   inside the shifted indicator with probability ``d`` (the duty cycle),
   whatever the indicator's run structure, because the events are uniform
   in time; the null in-count given the total is therefore exactly
   ``Binomial(n, d)`` and is drawn directly. Real catalogues keep some
   clustering after declustering, which widens the null, so the answer is a
   lower bound on what the study can detect.
3. Under RR the inside probability is ``RR d / (RR d + 1 - d)``.
4. The critical in-count is the ``1 - alpha`` quantile of the null count
   (conditional on the total, as the study's test is), and the minimum
   detectable RR is found by bisection on log RR with common random numbers,
   so the power curve is monotone.

The answer is optimistic for clustered catalogues.

:func:`minimum_detectable_difference` gives the analogue for a difference in
means from a reported confidence interval: ``(z_{1-alpha/2} + z_power) SE``.
"""

from typing import Dict, Iterable

import numpy as np
import pandas as pd
from scipy import stats as sps

from .nulls import _check_rng


def _simulate(n_events, duty_cycle, n_sim, rng):
    n_tot = rng.poisson(n_events, size=n_sim)
    p0 = np.full(n_sim, float(duty_cycle))
    u_null = rng.random(n_sim)
    u_alt = rng.random(n_sim)
    return n_tot, p0, u_null, u_alt


def _power(log_rr, d, n_tot, p0, u_null, u_alt, alpha, two_sided):
    """Rejection rate of the conditional test at RR = exp(log_rr)."""
    rr = np.exp(log_rr)
    p1 = rr * d / (rr * d + 1.0 - d)
    k_alt = sps.binom.ppf(u_alt, n_tot, p1)
    a = alpha / 2.0 if two_sided else alpha
    # Critical value from the null mixture over shifts: the (1 - a) quantile of
    # the in-count when each simulation draws its own shifted duty.
    k_null = sps.binom.ppf(u_null, n_tot, p0)
    frac_null = np.where(n_tot > 0, k_null / np.maximum(n_tot, 1), 0.0)
    crit = np.quantile(frac_null, 1.0 - a, method="higher")
    frac_alt = np.where(n_tot > 0, k_alt / np.maximum(n_tot, 1), 0.0)
    return float(np.mean((frac_alt > crit) & (n_tot > 0)))


def power_at_rate_ratio(
    rate_ratio: float,
    n_events: float,
    duty_cycle: float,
    alpha: float,
    rng: np.random.Generator,
    n_sim: int = 4000,
    two_sided: bool = False,
) -> float:
    """Return the simulated power of the circular-shift test at ``rate_ratio``."""
    _check_rng(rng)
    d = float(duty_cycle)
    sims = _simulate(n_events, d, n_sim, rng)
    return _power(
        np.log(rate_ratio), d, sims[0], sims[1], sims[2], sims[3], alpha, two_sided
    )


def minimum_detectable_rate_ratio(
    n_events: float,
    duty_cycle: float,
    alpha: float,
    power: float,
    rng: np.random.Generator,
    n_sim: int = 4000,
    two_sided: bool = False,
    max_rr: float = 1000.0,
) -> float:
    """Return the smallest RR > 1 detected with probability ``power``.

    Args:
        n_events: Expected number of events in the tested period.
        duty_cycle: Share of time the indicator is active.
        alpha: Test level (one-sided unless ``two_sided``).
        power: Target power, e.g. 0.8.
        rng: ``np.random.default_rng(seed)``.
        n_sim: Simulated studies per evaluation.
        max_rr: Upper search bound; returned as ``inf`` if not reached.
    """
    _check_rng(rng)
    if not 0 < duty_cycle < 1:
        raise ValueError("duty_cycle must lie in (0, 1)")
    d = float(duty_cycle)
    sims = _simulate(n_events, d, n_sim, rng)
    lo, hi = 0.0, np.log(max_rr)
    if _power(hi, d, sims[0], sims[1], sims[2], sims[3], alpha, two_sided) < power:
        return float("inf")
    for _ in range(40):
        mid = 0.5 * (lo + hi)
        if (
            _power(mid, d, sims[0], sims[1], sims[2], sims[3], alpha, two_sided)
            >= power
        ):
            hi = mid
        else:
            lo = mid
    return float(np.exp(hi))


def minimum_detectable_difference(
    ci_low: float,
    ci_high: float,
    alpha: float = 0.05,
    power: float = 0.8,
    ci_level: float = 0.95,
) -> float:
    """Return ``(z_{1-alpha/2} + z_power) SE`` with SE read from a CI."""
    se = (ci_high - ci_low) / (2.0 * sps.norm.ppf(0.5 + ci_level / 2.0))
    return float((sps.norm.ppf(1 - alpha / 2.0) + sps.norm.ppf(power)) * se)


def power_table(
    specs: Iterable[Dict],
    rng: np.random.Generator,
    alpha: float = 0.05,
    power: float = 0.8,
    n_sim: int = 4000,
) -> pd.DataFrame:
    """Return the minimum detectable RR for each registered indicator.

    Each spec needs ``id``, ``n_events`` and ``duty_cycle``; ``direction``
    ``"two-sided"`` halves alpha per tail. Optional ``label`` is copied.
    """
    rows = []
    for spec in specs:
        two = spec.get("direction", "greater") == "two-sided"
        d = float(spec["duty_cycle"])
        n = float(spec["n_events"])
        row = {
            "id": spec["id"],
            "label": spec.get("label", spec["id"]),
            "n_events": n,
            "duty_cycle": d,
            "expected_in": n * d,
            "direction": spec.get("direction", "greater"),
        }
        if n <= 0 or not 0 < d < 1:
            row["mdrr"] = float("nan")
        else:
            row["mdrr"] = minimum_detectable_rate_ratio(
                n, d, alpha, power, rng, n_sim=n_sim, two_sided=two
            )
        rows.append(row)
    out = pd.DataFrame(rows)
    out["alpha"] = alpha
    out["power"] = power
    return out
