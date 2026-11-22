"""Simulated price-return series and real indicator calendars for calibration tests.

The calibration suite (``tests/test_stats_calibration.py``, ADR-004 WP-02) checks
that each test in :mod:`vedic_astrology_core.stats` keeps its stated
false-alarm rate when there is no true effect. A simulator that is too kind
(Gaussian, no volatility clustering, no regimes, no long memory) would certify
a broken test, so the series here carry every feature that broke the gold
study's tests (review items M1 and M3):

* :func:`garch11_t`: GARCH(1,1) with Student-t innovations (heavy tails,
  volatility clustering).
* :func:`regime_scale`: a two-state Markov chain of volatility regimes with
  mean durations of hundreds of bars (2008-, 2020-style episodes).
* :func:`long_memory_logvol`: a fractionally integrated (ARFIMA(0, d, 0))
  log-volatility factor, whose autocorrelation decays hyperbolically.
* :func:`hard_returns`: all three multiplied together, plus an optional drift
  (gold drifted about +4.8 bp/day in 2016-2026).

Outcomes are standardised with :func:`ewma_standardise`, which uses only data
up to bar t-1 for bar t. It is a stand-in until WP-05's past-only GARCH
standardisation exists.

Indicator calendars are not simulated: :func:`ephemeris_calendar` computes
real ones from the engine (sidereal Lahiri, mean node) on business days, so
episode counts and run lengths are those a study meets.

Every random function takes ``rng=np.random.default_rng(seed)``.
"""

import math
from functools import lru_cache
from typing import Dict, Tuple

import numpy as np
import pandas as pd

DAILY_VOL = 0.01  # unconditional daily volatility of the simulated returns


# ----------------------------------------------------------------- returns
def garch11_t(
    n: int,
    rng: np.random.Generator,
    omega: float = 0.02,
    alpha: float = 0.08,
    beta: float = 0.90,
    nu: float = 5.0,
    burn: int = 500,
) -> Tuple[np.ndarray, np.ndarray]:
    """Return ``(e, sigma)``: a unit-variance GARCH(1,1) series with t innovations.

    ``sigma2_t = omega + alpha e_{t-1}^2 + beta sigma2_{t-1}``, scaled so the
    unconditional variance is 1. Innovations are Student-t with ``nu`` degrees
    of freedom, rescaled to unit variance.
    """
    if alpha + beta >= 1.0:
        raise ValueError("alpha + beta must be below 1 for a finite variance")
    if nu <= 2.0:
        raise ValueError("nu must exceed 2 for a finite variance")
    total = int(n) + int(burn)
    z = rng.standard_t(nu, size=total) * np.sqrt((nu - 2.0) / nu)
    uncond = omega / (1.0 - alpha - beta)
    e = [0.0] * total
    s2 = [0.0] * total
    prev_s2, prev_e2 = uncond, uncond
    for t, zt in enumerate(z.tolist()):  # plain floats: the loop is the cost
        cur = omega + alpha * prev_e2 + beta * prev_s2
        et = math.sqrt(cur) * zt
        s2[t], e[t] = cur, et
        prev_s2, prev_e2 = cur, et * et
    scale = 1.0 / math.sqrt(uncond)
    return np.asarray(e[burn:]) * scale, np.sqrt(np.asarray(s2[burn:])) * scale


def regime_scale(
    n: int,
    rng: np.random.Generator,
    scales: Tuple[float, float] = (1.0, 2.5),
    mean_durations: Tuple[float, float] = (500.0, 250.0),
) -> Tuple[np.ndarray, np.ndarray]:
    """Return ``(scale, state)`` from a two-state Markov chain of volatility regimes.

    State 0 is calm and state 1 is turbulent; each lasts a geometric number of
    bars with the given mean. The chain starts from its stationary law.
    """
    p_leave = 1.0 / np.asarray(mean_durations, dtype=float)
    pi1 = p_leave[0] / (p_leave[0] + p_leave[1])
    leave = p_leave.tolist()
    s = int(rng.random() < pi1)
    states = [0] * int(n)
    for t, ut in enumerate(rng.random(int(n)).tolist()):
        states[t] = s
        if ut < leave[s]:
            s = 1 - s
    state = np.asarray(states, dtype=np.int8)
    return np.asarray(scales, dtype=float)[state], state


def long_memory_logvol(
    n: int,
    rng: np.random.Generator,
    d: float = 0.4,
    sd: float = 0.3,
    n_lags: int = 2000,
) -> np.ndarray:
    """Return a long-memory volatility factor ``exp(h_t)`` with ``E[exp(2h)] = 1``.

    ``h`` is ARFIMA(0, d, 0) noise (moving-average weights
    ``Gamma(k + d) / (Gamma(k + 1) Gamma(d))`` truncated at ``n_lags``), scaled
    to standard deviation ``sd``.
    """
    if not 0.0 < d < 0.5:
        raise ValueError("d must lie in (0, 0.5) for a stationary long-memory series")
    k = np.arange(1, n_lags)
    psi = np.concatenate([[1.0], np.cumprod((k - 1 + d) / k)])
    eps = rng.standard_normal(int(n) + n_lags)
    h = np.convolve(eps, psi, mode="full")[n_lags : n_lags + int(n)]
    h = (h - h.mean()) / h.std() * sd
    return np.exp(h - sd * sd)


def hard_returns(
    n: int,
    rng: np.random.Generator,
    drift: float = 0.0,
    vol: float = DAILY_VOL,
    regimes: bool = True,
    long_memory: bool = True,
) -> Dict[str, np.ndarray]:
    """Return daily log returns with GARCH-t, regimes, long memory and drift.

    Returns:
        ``{"ret", "sigma", "state"}``: the returns, their true conditional
        volatility and the regime state (all zero when ``regimes`` is off).
        The returns have mean ``drift`` and roughly ``vol`` daily volatility.
    """
    e, s = garch11_t(n, rng)
    factor = np.ones(int(n))
    state = np.zeros(int(n), dtype=np.int8)
    if regimes:
        scale, state = regime_scale(n, rng)
        pi1 = 250.0 / 750.0  # stationary share of the turbulent state
        factor = factor * scale / np.sqrt((1 - pi1) * 1.0 + pi1 * 2.5**2)
    if long_memory:
        factor = factor * long_memory_logvol(n, rng)
    return {
        "ret": drift + vol * factor * e,
        "sigma": vol * factor * s,
        "state": state,
    }


# --------------------------------------------------------- standardisation
def ewma_standardise(r, lam: float = 0.94, warmup: int = 50) -> np.ndarray:
    """Return ``r_t / sigma_{t|t-1}`` with a past-only EWMA (RiskMetrics) variance.

    ``sigma2_{t|t-1} = lam sigma2_{t-1|t-2} + (1 - lam) r_{t-1}^2``, started from
    the mean square of the first ``warmup`` bars. Those bars are NaN, so no
    value depends on data at or after its own bar.
    """
    r = np.asarray(r, dtype=float)
    out = np.full(len(r), np.nan)
    if len(r) <= warmup:
        return out
    s2 = float(np.mean(r[:warmup] ** 2))
    sig = [0.0] * len(r)
    for t, rt in enumerate(r[warmup:].tolist(), start=warmup):
        sig[t] = s2
        s2 = lam * s2 + (1.0 - lam) * rt * rt
    out[warmup:] = r[warmup:] / np.sqrt(np.asarray(sig[warmup:]))
    return out


def past_quantile_flag(a, window: int = 250, quantile: float = 0.95) -> np.ndarray:
    """1.0 where ``a_t`` exceeds the past-only rolling quantile, NaN before it exists."""
    a = pd.Series(np.asarray(a, dtype=float))
    past = a.shift(1).rolling(window, min_periods=window).quantile(quantile)
    return np.where(past.notna(), (a > past).astype(float), np.nan)


# --------------------------------------------------------------- calendars
def n_episodes(mask) -> int:
    """Number of maximal runs of True in ``mask``."""
    m = np.asarray(mask, dtype=bool)
    if not len(m):
        return 0
    return int(m[0]) + int(np.sum(m[1:] & ~m[:-1]))


_SIGN_INDICATORS = {
    "sun_exalted": ("SUN", "Aries"),
    "sun_debilitated": ("SUN", "Libra"),
    "sun_own_sign": ("SUN", "Leo"),
    "sun_in_capricorn": ("SUN", "Capricorn"),
    "jupiter_exalted": ("JUPITER", "Cancer"),
    "jupiter_debilitated": ("JUPITER", "Capricorn"),
}
_FLAG_INDICATORS = {
    "mercury_retrograde": "MERCURY_retro",
    "venus_retrograde": "VENUS_retro",
    "mars_retrograde": "MARS_retro",
    "jupiter_retrograde": "JUPITER_retro",
    "saturn_retrograde": "SATURN_retro",
    "mercury_combust": "MERCURY_combust",
    "venus_combust": "VENUS_combust",
    "jupiter_combust": "JUPITER_combust",
    "saturn_combust": "SATURN_combust",
    "moon_combust": "MOON_combust",
}

#: Indicators with at least 8 episodes on business days 2000-2009 and 2000-2024.
MANY_EPISODE_INDICATORS = (
    "mercury_retrograde",
    "mercury_combust",
    "venus_combust",
    "jupiter_retrograde",
    "jupiter_combust",
    "saturn_retrograde",
    "saturn_combust",
    "moon_combust",
    "sun_exalted",
    "sun_debilitated",
    "sun_own_sign",
    "sun_in_capricorn",
    "purnima",
    "amavasya",
)


@lru_cache(maxsize=8)
def _calendar(start: str, end: str, sample_time: str, tz: str) -> pd.DataFrame:
    from vedic_astrology_core.markets.align import sample_instants
    from vedic_astrology_core.markets.features import indicator_frame

    dates = pd.bdate_range(start, end)
    frame = indicator_frame(
        sample_instants(dates, sample_time, tz),
        ["SUN", "MOON", "MERCURY", "VENUS", "MARS", "JUPITER", "SATURN"],
    )
    cols = {
        name: frame[col].to_numpy(dtype=bool) for name, col in _FLAG_INDICATORS.items()
    }
    for name, (body, sign) in _SIGN_INDICATORS.items():
        cols[name] = (frame[f"{body}_sign"] == sign).to_numpy()
    cols["purnima"] = (frame["tithi"] == 15).to_numpy()
    cols["amavasya"] = (frame["tithi"] == 30).to_numpy()
    return pd.DataFrame(cols, index=dates)


def ephemeris_calendar(
    start: str = "2000-01-03",
    end: str = "2009-12-31",
    sample_time: str = "12:00",
    tz: str = "UTC",
) -> pd.DataFrame:
    """Real boolean indicator calendars on business days, from the ephemeris.

    Columns are indicator ids (see :data:`MANY_EPISODE_INDICATORS` and the
    slow ones such as ``jupiter_exalted``); the index is the business days in
    ``[start, end]``. Results are cached per argument set; a copy is returned.
    """
    return _calendar(str(start), str(end), str(sample_time), str(tz)).copy()
