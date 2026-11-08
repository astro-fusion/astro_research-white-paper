"""Bayesian summaries of an event-rate ratio under sceptical and enthusiastic priors.

The parameter is ``theta = log RR``. The likelihood is the Poisson likelihood
of the two counts conditioned on their total, which removes the baseline
rate: ``n_in ~ Binomial(n, p)`` with ``p = RR t_in / (RR t_in + t_out)``.
The posterior is computed on a fine grid (no conjugacy needed), and the
Bayes factor against ``RR = 1`` is the Savage-Dickey density ratio
``BF01 = posterior(0) / prior(0)`` (Dickey 1971; Wagenmakers et al. 2010),
valid because ``RR = 1`` is a point inside a continuous prior.

Registered priors (ADR-003): sceptical ``theta ~ N(0, 0.1^2)`` (a 95% prior
range of about RR 0.82 to 1.22, the size of effect tidal triggering shows)
and enthusiastic ``theta ~ N(0, 0.5^2)`` (RR 0.38 to 2.7).
"""

from dataclasses import asdict, dataclass
from typing import Dict, Optional

import numpy as np
from scipy import stats as sps
from scipy.special import expit

PRIORS: Dict[str, float] = {"sceptical": 0.1, "enthusiastic": 0.5}
"""Prior standard deviation of log RR, by name."""


@dataclass
class PosteriorRR:
    """Posterior summary of log RR on one prior."""

    prior_sd: float
    post_mean: float
    post_sd: float
    rr_median: float
    rr_cri_low: float
    rr_cri_high: float
    p_rr_gt_1: float
    bf10: float
    bf01: float


def posterior_log_rr(
    n_in: int,
    t_in: float,
    n_out: int,
    t_out: float,
    prior_sd: float,
    cri_level: float = 0.95,
    grid: Optional[np.ndarray] = None,
) -> PosteriorRR:
    """Return the grid posterior of log RR under a ``N(0, prior_sd^2)`` prior.

    Raises:
        ValueError: If an exposure or the prior sd is not positive.
    """
    if t_in <= 0 or t_out <= 0:
        raise ValueError("both exposures must be positive")
    if prior_sd <= 0:
        raise ValueError("prior_sd must be positive")
    if grid is None:
        half = max(8.0 * prior_sd, 1.0)
        grid = np.linspace(-half, half, 40001)
    theta = np.asarray(grid, dtype=float)
    p = expit(theta + np.log(t_in / t_out))
    loglik = int(n_in) * np.log(p) + int(n_out) * np.log1p(-p)
    logprior = sps.norm.logpdf(theta, 0.0, prior_sd)
    logpost = loglik + logprior
    logpost -= logpost.max()
    dens = np.exp(logpost)
    dens /= np.trapezoid(dens, theta)
    steps = 0.5 * (dens[1:] + dens[:-1]) * np.diff(theta)
    cdf = np.concatenate([[0.0], np.cumsum(steps)])
    cdf /= cdf[-1]
    mean = float(np.trapezoid(theta * dens, theta))
    sd = float(np.sqrt(np.trapezoid((theta - mean) ** 2 * dens, theta)))
    a = (1.0 - cri_level) / 2.0
    lo, med, hi = np.interp([a, 0.5, 1.0 - a], cdf, theta)
    post0 = float(np.interp(0.0, theta, dens))
    prior0 = float(sps.norm.pdf(0.0, 0.0, prior_sd))
    bf01 = post0 / prior0
    return PosteriorRR(
        prior_sd=float(prior_sd),
        post_mean=mean,
        post_sd=sd,
        rr_median=float(np.exp(med)),
        rr_cri_low=float(np.exp(lo)),
        rr_cri_high=float(np.exp(hi)),
        p_rr_gt_1=float(1.0 - np.interp(0.0, theta, cdf)),
        bf10=float(1.0 / bf01) if bf01 > 0 else float("inf"),
        bf01=float(bf01),
    )


def summarise(
    n_in: int,
    t_in: float,
    n_out: int,
    t_out: float,
    priors: Optional[Dict[str, float]] = None,
) -> Dict[str, Dict[str, float]]:
    """Return :func:`posterior_log_rr` as dicts, one per named prior."""
    priors = PRIORS if priors is None else priors
    return {
        name: asdict(posterior_log_rr(n_in, t_in, n_out, t_out, sd))
        for name, sd in priors.items()
    }
