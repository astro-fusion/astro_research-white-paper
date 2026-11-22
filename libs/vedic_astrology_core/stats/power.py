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

ADR-004 WP-08 (review M6) adds:

* :func:`family_alpha`: the level a single test must reach to survive the
  family correction. For a Benjamini-Yekutieli family of ``m`` tests this is
  the rank-1 threshold ``alpha / (m H_m)``; power quoted at the unadjusted
  0.05 overstates what a corrected study can find (review 2.6 a).
* ``overdispersion`` in :func:`power_at_rate_ratio`,
  :func:`minimum_detectable_rate_ratio` and :func:`power_table`: event
  counts inside and outside the indicator are negative binomial with
  variance ``phi * mean`` (``phi = 1`` is Poisson). Aftershock residue and
  swarms make real counts over-dispersed; the circular-shift null keeps that
  clustering, so the simulated null uses the same ``phi``.
* :func:`power_episode_effect` and :func:`minimum_detectable_episode_effect`:
  power and minimum detectable effect for a slow indicator whose unit of
  evidence is the episode (ADR-004 D-6), with ``n_episodes`` as ``n``
  (never the bar count) and the per-episode difference's standard deviation.
  A test whose attainable minimum p (``2**-K`` for the exact sign-flip test)
  is not below ``alpha`` has power 0 and an infinite minimum detectable
  effect, whatever the effect.
"""

import math
from typing import Dict, Iterable, Optional

import numpy as np
import pandas as pd
from scipy import stats as sps

from .episodes import ALTERNATIVES, by_rank1_threshold, sign_flip_p_min
from .nulls import _check_rng

FAMILY_METHODS = ("by", "bh", "bonferroni", "none")


def family_alpha(family_size: int, alpha: float = 0.05, method: str = "by") -> float:
    """Return the per-test level that survives the family correction at rank 1.

    The most significant test of a family is declared only if its p-value is
    below this level, so power and minimum detectable effects for a
    confirmatory family are computed at it, not at ``alpha``.

    * ``"by"``: ``alpha / (m H_m)`` (Benjamini-Yekutieli, the project default;
      same value as :func:`.episodes.by_rank1_threshold`).
    * ``"bh"`` and ``"bonferroni"``: ``alpha / m``.
    * ``"none"``: ``alpha`` (single pre-registered test).
    """
    if method not in FAMILY_METHODS:
        raise ValueError(f"method must be one of {FAMILY_METHODS}, got {method!r}")
    if method == "by":
        return by_rank1_threshold(family_size, alpha)
    m = int(family_size)
    if m < 1:
        raise ValueError("family_size must be at least 1")
    if not 0 < alpha < 1:
        raise ValueError("alpha must lie in (0, 1)")
    return float(alpha) if method == "none" else float(alpha) / m


def _check_overdispersion(overdispersion):
    if overdispersion is None:
        return 1.0
    phi = float(overdispersion)
    if not np.isfinite(phi) or phi < 1.0:
        raise ValueError("overdispersion (variance / mean) must be finite and >= 1")
    return phi


def _simulate(n_events, duty_cycle, n_sim, rng, phi=1.0):
    if phi == 1.0:
        n_tot = rng.poisson(n_events, size=n_sim)
        p0 = np.full(n_sim, float(duty_cycle))
        u_null = rng.random(n_sim)
        u_alt = rng.random(n_sim)
        return n_tot, p0, u_null, u_alt
    # Negative binomial: four uniforms per study (inside and outside counts,
    # null and alternative), drawn once and reused at every RR (common random
    # numbers, so the power curve is monotone in RR).
    return (float(n_events), float(phi), rng.random((n_sim, 2)), rng.random((n_sim, 2)))


def _nb_counts(mean, phi, u):
    """Negative binomial counts with the given means and variance phi * mean."""
    mean = np.asarray(mean, dtype=float)
    out = np.zeros(np.broadcast(mean, u).shape)
    pos = np.broadcast_to(mean, out.shape) > 0
    m = np.broadcast_to(mean, out.shape)[pos]
    size = m / (phi - 1.0)
    out[pos] = sps.nbinom.ppf(u[pos], size, 1.0 / phi)
    return out


def _power_nb(log_rr, d, n_events, phi, u_null, u_alt, alpha, two_sided):
    """Rejection rate at RR with over-dispersed inside and outside counts.

    The inside and outside counts are independent negative binomials with
    means ``n p`` and ``n (1 - p)`` (``p = d`` under the null, ``p1`` under
    RR) and variance ``phi`` times the mean. The test compares the inside
    share with the ``1 - alpha`` quantile of its simulated null.
    """
    rr = np.exp(log_rr)
    p1 = rr * d / (rr * d + 1.0 - d)
    a = alpha / 2.0 if two_sided else alpha
    null = _nb_counts(np.array([n_events * d, n_events * (1 - d)]), phi, u_null)
    alt = _nb_counts(np.array([n_events * p1, n_events * (1 - p1)]), phi, u_alt)
    tot_null = null.sum(axis=1)
    tot_alt = alt.sum(axis=1)
    frac_null = np.where(tot_null > 0, null[:, 0] / np.maximum(tot_null, 1), 0.0)
    crit = np.quantile(frac_null, 1.0 - a, method="higher")
    frac_alt = np.where(tot_alt > 0, alt[:, 0] / np.maximum(tot_alt, 1), 0.0)
    return float(np.mean((frac_alt > crit) & (tot_alt > 0)))


def _power_any(log_rr, d, sims, alpha, two_sided):
    if isinstance(sims[0], float):
        return _power_nb(
            log_rr, d, sims[0], sims[1], sims[2], sims[3], alpha, two_sided
        )
    return _power(log_rr, d, sims[0], sims[1], sims[2], sims[3], alpha, two_sided)


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
    overdispersion: Optional[float] = None,
) -> float:
    """Return the simulated power of the circular-shift test at ``rate_ratio``.

    ``alpha`` is the per-test level; for a confirmatory family pass
    :func:`family_alpha`. ``overdispersion`` is the variance-to-mean ratio of
    the event counts (None or 1 for Poisson).
    """
    _check_rng(rng)
    d = float(duty_cycle)
    phi = _check_overdispersion(overdispersion)
    sims = _simulate(n_events, d, n_sim, rng, phi)
    return _power_any(np.log(rate_ratio), d, sims, alpha, two_sided)


def minimum_detectable_rate_ratio(
    n_events: float,
    duty_cycle: float,
    alpha: float,
    power: float,
    rng: np.random.Generator,
    n_sim: int = 4000,
    two_sided: bool = False,
    max_rr: float = 1000.0,
    overdispersion: Optional[float] = None,
) -> float:
    """Return the smallest RR > 1 detected with probability ``power``.

    Args:
        n_events: Expected number of events in the tested period.
        duty_cycle: Share of time the indicator is active.
        alpha: Per-test level (one-sided unless ``two_sided``). For a
            confirmatory family pass :func:`family_alpha` (the rank-1 BY
            threshold), not the unadjusted 0.05.
        power: Target power, e.g. 0.8.
        rng: ``np.random.default_rng(seed)``.
        n_sim: Simulated studies per evaluation.
        max_rr: Upper search bound; returned as ``inf`` if not reached.
        overdispersion: Variance-to-mean ratio ``phi >= 1`` of the inside and
            outside event counts (negative binomial). None or 1 is Poisson.
            Estimate it from the declustered catalogue (for example the
            Pearson dispersion of counts per episode-length window), and fix
            it in the plan.
    """
    _check_rng(rng)
    if not 0 < duty_cycle < 1:
        raise ValueError("duty_cycle must lie in (0, 1)")
    d = float(duty_cycle)
    phi = _check_overdispersion(overdispersion)
    sims = _simulate(n_events, d, n_sim, rng, phi)
    lo, hi = 0.0, np.log(max_rr)
    if _power_any(hi, d, sims, alpha, two_sided) < power:
        return float("inf")
    for _ in range(40):
        mid = 0.5 * (lo + hi)
        if _power_any(mid, d, sims, alpha, two_sided) >= power:
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
    family_size: Optional[int] = None,
    family_method: str = "by",
    overdispersion: Optional[float] = None,
) -> pd.DataFrame:
    """Return the minimum detectable RR for each registered indicator.

    Each spec needs ``id``, ``n_events`` and ``duty_cycle``; ``direction``
    ``"two-sided"`` halves alpha per tail. Optional ``label`` is copied, and an
    optional per-spec ``overdispersion`` overrides the table-wide value.

    With ``family_size`` the table is computed at :func:`family_alpha`
    (``family_method``, default the rank-1 BY threshold) instead of
    ``alpha``; the column ``alpha`` holds the level actually used and
    ``alpha_family`` the family's nominal level.
    """
    level = (
        float(alpha)
        if family_size is None
        else family_alpha(family_size, alpha, family_method)
    )
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
                n,
                d,
                level,
                power,
                rng,
                n_sim=n_sim,
                two_sided=two,
                overdispersion=spec.get("overdispersion", overdispersion),
            )
        rows.append(row)
    out = pd.DataFrame(rows)
    out["alpha"] = level
    out["alpha_family"] = float(alpha)
    out["family_size"] = family_size
    out["power"] = power
    return out


# --------------------------------------------------------------------------
# Episodes as n (slow indicators, ADR-004 D-6)
# --------------------------------------------------------------------------


def _check_episode_args(n_episodes, sd, alpha, alternative):
    k = int(n_episodes)
    if k != n_episodes or k < 1:
        raise ValueError("n_episodes must be a positive integer")
    if not (np.isfinite(sd) and sd > 0):
        raise ValueError("sd must be positive and finite")
    if not 0 < alpha < 1:
        raise ValueError("alpha must lie in (0, 1)")
    if alternative not in ALTERNATIVES:
        raise ValueError(f"alternative must be one of {ALTERNATIVES}")
    return k


def _episode_power_t(effect, sd, k, alpha, alternative):
    """Noncentral-t power of the one-sample test of the episode mean."""
    if k < 2:
        return 0.0
    df = k - 1
    nc = float(effect) / float(sd) * math.sqrt(k)
    if alternative == "two-sided":
        t = sps.t.ppf(1.0 - alpha / 2.0, df)
        return float(sps.nct.sf(t, df, nc) + sps.nct.cdf(-t, df, nc))
    t = sps.t.ppf(1.0 - alpha, df)
    if alternative == "less":
        nc = -nc
    return float(sps.nct.sf(t, df, nc))


def power_episode_effect(
    effect: float,
    sd: float,
    n_episodes: int,
    alpha: float,
    alternative: str = "greater",
    method: str = "t",
    rng: Optional[np.random.Generator] = None,
    n_sim: int = 2000,
    n_draws: int = 9999,
) -> float:
    """Return the power to detect a mean per-episode difference ``effect``.

    The test is the episode-level sign-flip test of
    :func:`.episodes.sign_flip_test`, with ``n = n_episodes`` and ``sd`` the
    standard deviation of one episode's difference (active mean minus
    neighbouring mean), not of one bar.

    If the attainable minimum p of the sign-flip test is not strictly below
    ``alpha`` (for example 8 episodes against a rank-1 BY threshold of
    0.0003) the power is exactly 0.

    Args:
        effect: True mean difference, in the outcome's unit, signed so that
            positive is the claimed direction for ``"greater"``.
        sd: Between-episode standard deviation of the differences.
        n_episodes: Number of episodes K.
        alpha: Per-test level; pass :func:`family_alpha` for a family.
        alternative: ``"greater"``, ``"less"`` or ``"two-sided"``.
        method: ``"t"`` (noncentral t, normal differences; fast) or
            ``"sign_flip"`` (simulate normal differences and run the exact
            sign-flip test; needs ``rng``).
        n_draws: Random sign patterns when K exceeds the enumeration limit.
    """
    k = _check_episode_args(n_episodes, sd, alpha, alternative)
    if not sign_flip_p_min(k, alternative, n_draws) < alpha:
        return 0.0
    if method == "t":
        return _episode_power_t(effect, sd, k, alpha, alternative)
    if method != "sign_flip":
        raise ValueError("method must be 't' or 'sign_flip'")
    if rng is None:
        raise ValueError("method 'sign_flip' needs rng")
    _check_rng(rng)
    from .episodes import sign_flip_test

    hits = 0
    for _ in range(int(n_sim)):
        d = float(effect) + float(sd) * rng.standard_normal(k)
        res = sign_flip_test(d, alternative=alternative, rng=rng, n_draws=n_draws)
        hits += res.p_value < alpha
    return hits / int(n_sim)


def minimum_detectable_episode_effect(
    sd: float,
    n_episodes: int,
    alpha: float,
    power: float = 0.8,
    alternative: str = "greater",
    n_draws: int = 9999,
) -> float:
    """Return the smallest mean per-episode difference found with ``power``.

    Uses the noncentral-t power of :func:`power_episode_effect` with
    ``n = n_episodes``. Returns ``inf`` when the sign-flip test cannot reach
    ``alpha`` with this many episodes, or with a single episode. The answer is
    in the outcome's unit (the same unit as ``sd``); divide by ``sd`` for
    standard-deviation units. For ``"less"`` the magnitude is returned.
    """
    k = _check_episode_args(n_episodes, sd, alpha, alternative)
    if not 0 < power < 1:
        raise ValueError("power must lie in (0, 1)")
    if k < 2 or not sign_flip_p_min(k, alternative, n_draws) < alpha:
        return float("inf")
    alt = "greater" if alternative == "less" else alternative

    def gap(es):
        return _episode_power_t(es * sd, sd, k, alpha, alt) - power

    hi = 1.0
    while gap(hi) < 0:
        hi *= 2.0
        if hi > 1e6:
            return float("inf")
    from scipy.optimize import brentq

    return float(brentq(gap, 0.0, hi, xtol=1e-10) * sd)
