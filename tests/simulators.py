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


# =====================================================================
# ADR-008 WP-84: generators for the block, exclusion, season and data-rule
# cases (sections 1.3, 2.4, 6.3 and 8). Every random function takes a
# numpy Generator; parameters are module constants so the certificate
# (which hashes this file) pins them. Effects are planted in the BARS
# (outcome per bar, or the bar's event rate), never in block differences.
# =====================================================================

#: Section 1.3: periodic calendars (active bars, gap bars) and episode counts.
PERIODIC_SHAPES = ((5, 5), (20, 5), (5, 50), (20, 20), (60, 10))
PERIODIC_EPISODES = (12, 18)
#: Section 2.4: numbers of used blocks.
BLOCK_COUNTS = (8, 12, 20)
#: Section 2.4 X7: block balance values.
BALANCES = (0.5, 0.75, 1.0)
#: Section 1.3 B2 / 2.4 X1, X2: bar distributions.
CONTINUOUS_KINDS = ("normal", "t3", "lognormal", "exponential", "zero_inflated")
SKEWED_KINDS = ("lognormal", "exponential", "zero_inflated")
ZERO_INFLATED_P0 = 0.98
#: Section 1.3 B3: GARCH(1,1) and AR(1).
B3_GARCH = {"alpha": 0.08, "beta": 0.90}
AR1_PHIS = (0.1, 0.3)
#: Section 2.4 X3: mean Poisson events per active window.
RARE_EVENT_MEANS = (0.1, 0.5, 2.0)
#: Section 2.4 X4: Neyman-Scott clustering.
NS_OFFSPRING_MEAN = 3.0
NS_DELAY_MEAN = 10.0  # bars
NS_TREND = 2.0  # background rate at the end of the record over the start
#: Section 2.4 X5: base rates of yes/no flags.
GARCH_FLAG_RATE = 0.05
DROUGHT_FLAG_RATE = 0.15
#: Section 6.3 Z1/Z2: season.
SEASON_AMPLITUDE = 1.0  # in noise standard deviations
SEASON_PULSE = 1.0  # added in the pulse months, in noise standard deviations
SEASON_PULSE_MONTHS = (6, 7, 8, 9)
SEASON_EVENT_FACTOR = 8.0
#: Section 6.3 Z3: yearly rainfall anomaly (percentage points).
#: The ADR fixes the noise SD, the ENSO weight and the 31-year period; the
#: ENSO AR(1) coefficient and the epoch amplitude are not given and are set
#: here (and pinned by the certificate's hash of this file).
RAIN_NOISE_SD = 10.0
RAIN_ENSO_WEIGHT = 4.0
RAIN_ENSO_PHI = 0.3
RAIN_EPOCH_PERIOD = 31.0
RAIN_EPOCH_AMPLITUDE = 4.0
DROUGHT_THRESHOLD = -10.0
#: Section 6.3 Z6: lunar nodal period in years.
NODAL_PERIOD_YEARS = 18.6
#: Section 6.3 grids.
DAILY_GRID = ("1968-01-01", "1998-12-31")
YEARLY_GRID = (1871, 2016)
#: Section 6.3 real calendars: Moon in the fixed (dhruva) nakshatras; rikta tithis.
MOON_NAKSHATRA_GROUP = ("Rohini", "Uttara Phalguni", "Uttara Ashadha", "Uttara Bhadrapada")
TITHI_GROUP = (4, 9, 14, 19, 24, 29)
SUN_NAKSHATRA = "Ashwini"
SUN_SIGN = "Aries"
ECLIPSE_HALF_WINDOW = 3  # days either side of greatest eclipse
SIGNS = (
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
)


def _mask(active) -> np.ndarray:
    return np.asarray(active, dtype=bool)


def _same_length(y, active) -> Tuple[np.ndarray, np.ndarray]:
    y = np.asarray(y)
    a = _mask(active)
    if y.ndim != 1 or a.ndim != 1 or len(y) != len(a):
        raise ValueError(
            "effects are planted in bars: the outcome and the calendar must be "
            f"1-D arrays of the same length (got {y.shape} and {a.shape})"
        )
    return y, a


def episode_runs(mask) -> list:
    """List of ``(start, stop)`` index pairs of the maximal True runs."""
    m = _mask(mask).astype(np.int8)
    d = np.diff(np.concatenate([[0], m, [0]]))
    return list(zip(np.flatnonzero(d == 1).tolist(), np.flatnonzero(d == -1).tolist()))


# --------------------------------------------------------- calendars (1.3)
def periodic_calendar(
    n_active: int, n_gap: int, n_episodes: int, lead: int = None, trail: int = None
) -> np.ndarray:
    """Boolean calendar: ``lead`` off, then ``n_episodes`` x (on ``n_active``, off ``n_gap``).

    The last gap is replaced by ``trail``. ``lead`` and ``trail`` default to
    ``n_gap // 2``, so the edge episodes get the same control room as the
    inner ones under the half-gap rule of ADR-008 section 1.1.
    """
    if n_active < 1 or n_gap < 0 or n_episodes < 1:
        raise ValueError("need n_active >= 1, n_gap >= 0, n_episodes >= 1")
    lead = n_gap // 2 if lead is None else int(lead)
    trail = n_gap // 2 if trail is None else int(trail)
    unit = [True] * int(n_active) + [False] * int(n_gap)
    body = unit * int(n_episodes)
    body = body[: len(body) - int(n_gap)]
    return np.asarray([False] * lead + body + [False] * trail, dtype=bool)


def balance_calendar(balance: float, n_episodes: int, n_active: int = 8) -> np.ndarray:
    """Periodic calendar whose blocks have exactly ``balance`` = control / active (X7).

    Each side gets ``balance * n_active / 2`` control bars: the gap is twice
    that (even, so no middle bar is dropped) and each edge gets one half-gap.
    """
    per_side = balance * n_active / 2.0
    if per_side != int(per_side) or per_side < 1:
        raise ValueError(f"balance {balance} with {n_active} active bars gives no whole control count")
    if per_side > math.ceil(n_active / 2):
        raise ValueError("balance above 1 exceeds the ceil(n_active / 2) cap per side")
    gap = 2 * int(per_side)
    return periodic_calendar(n_active, gap, n_episodes, lead=gap // 2, trail=gap // 2)


# ------------------------------------------------------ bar outcomes (1.3, 2.4)
def continuous_bars(kind: str, n: int, rng: np.random.Generator) -> np.ndarray:
    """i.i.d. bars: normal, t3 (Student-t, 3 df), lognormal(0, 1), exponential(1), zero_inflated.

    ``zero_inflated``: 0 with probability 0.98, else Exponential(1). Values are
    not centred: block differences do not depend on a constant.
    """
    n = int(n)
    if kind == "normal":
        return rng.standard_normal(n)
    if kind == "t3":
        return rng.standard_t(3, size=n)
    if kind == "lognormal":
        return rng.lognormal(0.0, 1.0, size=n)
    if kind == "exponential":
        return rng.exponential(1.0, size=n)
    if kind == "zero_inflated":
        keep = rng.random(n) >= ZERO_INFLATED_P0
        return np.where(keep, rng.exponential(1.0, size=n), 0.0)
    raise ValueError(f"unknown bar kind {kind!r}; expected one of {CONTINUOUS_KINDS}")


def garch11_normal(n: int, rng: np.random.Generator, alpha: float = 0.08, beta: float = 0.90) -> np.ndarray:
    """Unit-variance GARCH(1,1) with Gaussian innovations (B3)."""
    if alpha + beta >= 1.0:
        raise ValueError("alpha + beta must be below 1 for a finite variance")
    omega = 1.0 - alpha - beta  # unconditional variance 1
    burn = 500
    z = rng.standard_normal(int(n) + burn).tolist()
    out = [0.0] * len(z)
    s2, e2 = 1.0, 1.0
    for t, zt in enumerate(z):
        s2 = omega + alpha * e2 + beta * s2
        et = math.sqrt(s2) * zt
        out[t] = et
        e2 = et * et
    return np.asarray(out[burn:])


def ar1(n: int, rng: np.random.Generator, phi: float, sd: float = 1.0) -> np.ndarray:
    """Stationary AR(1) with marginal standard deviation ``sd`` (B3, Z3)."""
    if not -1.0 < phi < 1.0:
        raise ValueError("phi must lie in (-1, 1)")
    eps = (rng.standard_normal(int(n)) * sd * math.sqrt(1.0 - phi * phi)).tolist()
    out = [0.0] * int(n)
    x = float(rng.standard_normal()) * sd
    for t, e in enumerate(eps):
        if t:
            x = phi * x + e
        out[t] = x
    return np.asarray(out)


def regime_bars(n: int, rng: np.random.Generator) -> np.ndarray:
    """Gaussian bars scaled by the two-state volatility regime chain (B3)."""
    scale, _ = regime_scale(n, rng)
    return rng.standard_normal(int(n)) * scale


# ------------------------------------------------------------ events (2.4)
def effect_multiplier(active, r: float) -> np.ndarray:
    """Per-bar rate multiplier: ``r`` on active bars, 1 elsewhere."""
    return np.where(_mask(active), float(r), 1.0)


def uneven_multiplier(
    active, r: float, rng: np.random.Generator, share: float = 0.2, scale: str = "ratio"
) -> np.ndarray:
    """X9: the whole effect in ``share`` of the episodes, bar-mean effect equal to ``r``.

    ``scale="ratio"`` returns a rate multiplier whose mean over active bars
    is ``r``; ``scale="shift"`` returns an additive shift whose mean over
    active bars is ``r``. At least one episode is chosen.
    """
    a = _mask(active)
    runs = episode_runs(a)
    if not runs:
        raise ValueError("calendar has no active bar")
    m = max(1, int(round(share * len(runs))))
    pick = rng.choice(len(runs), size=m, replace=False)
    sel = np.zeros(len(a), dtype=bool)
    for i in pick.tolist():
        s, e = runs[i]
        sel[s:e] = True
    factor = a.sum() / sel.sum()
    if scale == "ratio":
        return np.where(sel, 1.0 + (float(r) - 1.0) * factor, 1.0)
    if scale == "shift":
        return np.where(sel, float(r) * factor, 0.0)
    raise ValueError("scale must be 'ratio' or 'shift'")


def poisson_events(
    active, mean_per_window: float, window: int, rng: np.random.Generator, multiplier=None
) -> np.ndarray:
    """Event counts per bar: Poisson with ``mean_per_window / window`` events per bar (X3).

    ``window`` is the active-episode length, so an active window holds
    ``mean_per_window`` events on average under no effect. ``multiplier``
    (per bar, see :func:`effect_multiplier`) plants a rate ratio in the bars.
    """
    a = _mask(active)
    lam = np.full(len(a), float(mean_per_window) / float(window))
    if multiplier is not None:
        lam = lam * _same_length(multiplier, a)[0]
    return rng.poisson(lam)


def neyman_scott(
    n: int,
    rng: np.random.Generator,
    parent_rate: float,
    multiplier=None,
    trend: float = NS_TREND,
    offspring_mean: float = NS_OFFSPRING_MEAN,
    delay_mean: float = NS_DELAY_MEAN,
) -> Dict[str, np.ndarray]:
    """Clustered events (X4, Z2): Poisson parents with geometric offspring.

    Parent intensity per bar rises linearly from ``parent_rate`` to
    ``trend * parent_rate`` over the record (completeness change), times
    ``multiplier`` per bar (a planted rate ratio on parents, or a season).
    Each parent has a geometric number of offspring (support 0, 1, ...; mean
    ``offspring_mean``), each delayed by an Exponential(``delay_mean``) number
    of bars (floored). Offspring past the record are lost.

    Returns ``{"counts", "parents", "event_bar", "event_parent", "event_cluster"}``:
    all events per bar, parent events per bar (an ideal declustering), and
    one row per event (bar, is-parent flag, cluster id) for the pipeline's
    own declustering.
    """
    n = int(n)
    lam = float(parent_rate) * (1.0 + (float(trend) - 1.0) * np.arange(n) / max(n - 1, 1))
    if multiplier is not None:
        lam = lam * _same_length(multiplier, np.zeros(n, dtype=bool))[0]
    parents = rng.poisson(lam)
    p_bar = np.repeat(np.arange(n), parents)
    n_par = len(p_bar)
    n_off = rng.geometric(1.0 / (1.0 + float(offspring_mean)), size=n_par) - 1
    o_parent = np.repeat(np.arange(n_par), n_off)
    o_bar = p_bar[o_parent] + np.floor(rng.exponential(float(delay_mean), size=len(o_parent))).astype(int)
    keep = o_bar < n
    o_bar, o_parent = o_bar[keep], o_parent[keep]
    bars = np.concatenate([p_bar, o_bar]).astype(int)
    is_parent = np.concatenate([np.ones(n_par, dtype=bool), np.zeros(len(o_bar), dtype=bool)])
    cluster = np.concatenate([np.arange(n_par), o_parent]).astype(int)
    order = np.lexsort((~is_parent, bars))
    return {
        "counts": np.bincount(bars, minlength=n),
        "parents": parents,
        "event_bar": bars[order],
        "event_parent": is_parent[order],
        "event_cluster": cluster[order],
    }


def index_of_dispersion(counts, window: int) -> float:
    """Variance over mean of event counts in consecutive windows of ``window`` bars."""
    c = np.asarray(counts, dtype=float)
    k = len(c) // int(window)
    w = c[: k * int(window)].reshape(k, int(window)).sum(axis=1)
    return float(w.var(ddof=1) / w.mean())


# ------------------------------------------------------------- flags (2.4)
def garch_flags(n: int, rng: np.random.Generator, rate: float = GARCH_FLAG_RATE) -> np.ndarray:
    """Yes/no bars that cluster: |GARCH(1,1)| above its own (1 - rate) quantile (X5)."""
    e = np.abs(garch11_normal(n, rng, **B3_GARCH))
    k = int(round(rate * len(e)))
    thr = np.partition(e, len(e) - k - 1)[len(e) - k - 1]
    return (e > thr).astype(np.int8)


def plant_risk_ratio(flags, active, r: float, rng: np.random.Generator, base_rate: float) -> np.ndarray:
    """Plant a risk ratio ``r`` on the active bars of a yes/no series.

    ``r >= 1``: each active "no" turns "yes" with probability
    ``(r - 1) p / (1 - p)`` (``p = base_rate``), so P(yes) becomes ``r p``.
    ``r < 1``: each active "yes" is kept with probability ``r``.
    """
    f, a = _same_length(flags, active)
    f = f.astype(np.int8).copy()
    u = rng.random(len(f))
    if r >= 1.0:
        q = (float(r) - 1.0) * base_rate / (1.0 - base_rate)
        if q > 1.0:
            raise ValueError("r * base_rate must stay below 1")
        f[a & (f == 0) & (u < q)] = 1
    else:
        f[a & (f == 1) & (u >= r)] = 0
    return f


# ------------------------------------------------- planting in bars (2.4, 4.4)
def plant_shift(y, active, r) -> np.ndarray:
    """Add ``r`` (scalar or per-bar array) to every active bar; other bars unchanged."""
    y, a = _same_length(y, active)
    out = y.astype(float).copy()
    out[a] = out[a] + (np.asarray(r, dtype=float)[a] if np.ndim(r) else float(r))
    return out


def plant_ratio(y, active, r) -> np.ndarray:
    """Multiply every active bar by ``r`` (a shift of ``log r`` on the log scale)."""
    y, a = _same_length(y, active)
    if np.any(np.asarray(r) <= 0):
        raise ValueError("a ratio must be positive")
    out = y.astype(float).copy()
    out[a] = out[a] * (np.asarray(r, dtype=float)[a] if np.ndim(r) else float(r))
    return out


# ------------------------------------------------------------ season (6.3)
def seasonal_daily(
    dates,
    rng: np.random.Generator,
    amplitude: float = SEASON_AMPLITUDE,
    pulse: float = SEASON_PULSE,
    pulse_months=SEASON_PULSE_MONTHS,
    noise_sd: float = 1.0,
) -> np.ndarray:
    """Z1: yearly sine of ``amplitude`` noise SDs plus a four-month pulse plus noise."""
    idx = pd.DatetimeIndex(dates)
    doy = idx.day_of_year.to_numpy(dtype=float)
    season = amplitude * noise_sd * np.sin(2.0 * np.pi * doy / 365.25)
    season = season + pulse * noise_sd * np.isin(idx.month, pulse_months)
    return season + rng.standard_normal(len(idx)) * noise_sd


def season_multiplier(dates, months=SEASON_PULSE_MONTHS, factor: float = SEASON_EVENT_FACTOR) -> np.ndarray:
    """Z2: event-rate multiplier ``factor`` in ``months``, 1 elsewhere."""
    return np.where(np.isin(pd.DatetimeIndex(dates).month, months), float(factor), 1.0)


def harmonic_amplitude(dates, y) -> float:
    """Amplitude of the first yearly harmonic, fitted by least squares."""
    doy = pd.DatetimeIndex(dates).day_of_year.to_numpy(dtype=float)
    w = 2.0 * np.pi * doy / 365.25
    X = np.column_stack([np.ones(len(w)), np.sin(w), np.cos(w)])
    coef, *_ = np.linalg.lstsq(X, np.asarray(y, dtype=float), rcond=None)
    return float(np.hypot(coef[1], coef[2]))


def yearly_rainfall(
    years,
    rng: np.random.Generator,
    noise_sd: float = RAIN_NOISE_SD,
    enso_weight: float = RAIN_ENSO_WEIGHT,
    enso_phi: float = RAIN_ENSO_PHI,
    epoch_period: float = RAIN_EPOCH_PERIOD,
    epoch_amplitude: float = RAIN_EPOCH_AMPLITUDE,
    spike_year: int = None,
    spike: float = 0.0,
) -> Dict[str, np.ndarray]:
    """Z3: yearly rainfall anomaly in percentage points.

    ``anomaly = enso_weight * enso + epoch wave + Normal(0, noise_sd)``, with
    ``enso`` a unit-SD AR(1) driver and a sine of period ``epoch_period``
    years (random phase). ``spike_year`` adds ``spike`` to one year (D-06).
    Returns ``{"anomaly", "enso", "drought"}``; drought is anomaly below -10.
    """
    yrs = np.asarray(years, dtype=int)
    enso = ar1(len(yrs), rng, enso_phi)
    phase = rng.uniform(0.0, 2.0 * np.pi)
    epoch = epoch_amplitude * np.sin(2.0 * np.pi * yrs / epoch_period + phase)
    anomaly = enso_weight * enso + epoch + rng.standard_normal(len(yrs)) * noise_sd
    if spike_year is not None:
        anomaly = anomaly + np.where(yrs == int(spike_year), float(spike), 0.0)
    return {"anomaly": anomaly, "enso": enso, "drought": (anomaly < DROUGHT_THRESHOLD).astype(np.int8)}


def rainfall_sd(
    noise_sd: float = RAIN_NOISE_SD,
    enso_weight: float = RAIN_ENSO_WEIGHT,
    epoch_amplitude: float = RAIN_EPOCH_AMPLITUDE,
) -> float:
    """Marginal SD of :func:`yearly_rainfall` anomalies (sine variance A^2 / 2)."""
    return math.sqrt(noise_sd**2 + enso_weight**2 + epoch_amplitude**2 / 2.0)


def drought_flags(anomaly, rate: float = DROUGHT_FLAG_RATE) -> np.ndarray:
    """X5: drought-year flags with base rate ``rate`` (threshold from the generator's SD)."""
    from scipy.stats import norm

    thr = norm.ppf(rate) * rainfall_sd()
    return (np.asarray(anomaly, dtype=float) < thr).astype(np.int8)


def nodal_wave(rahu_longitude, rng: np.random.Generator, amplitude: float = 1.0, noise_sd: float = 1.0) -> np.ndarray:
    """Z6: outcome driven by the 18.6-year node cycle: ``amplitude * cos(node longitude)`` + noise."""
    lon = np.radians(np.asarray(rahu_longitude, dtype=float))
    return amplitude * np.cos(lon) + rng.standard_normal(len(lon)) * noise_sd


# -------------------------------------------------------- data rules (8)
def monthly_average_returns(n_years: int, rng: np.random.Generator, start: str = "1970-01-01") -> pd.Series:
    """D-01: daily Gaussian random walk in log price, averaged by month, then log returns.

    Averaging makes neighbouring monthly returns correlated (lag-1
    autocorrelation near 0.25, Working 1960); that artefact is the point.
    """
    days = pd.bdate_range(start, periods=int(n_years) * 261)
    logp = np.cumsum(rng.standard_normal(len(days)) * DAILY_VOL)
    monthly = pd.Series(np.exp(logp), index=days).resample("MS").mean()
    return np.log(monthly).diff().dropna()


def lag1_autocorrelation(x) -> float:
    """Sample lag-1 autocorrelation."""
    x = np.asarray(x, dtype=float)
    x = x - x.mean()
    return float(np.dot(x[:-1], x[1:]) / np.dot(x, x))


def holiday_mismatch(dates, rng: np.random.Generator, n_a: int = 10, n_b: int = 10) -> Tuple[pd.Series, pd.Series]:
    """D-02: two price series on the same days with different, random missing days.

    Returns ``(a, b)`` price Series; each drops its own ``n_a`` or ``n_b`` inner
    days (a few may coincide), so a return in one series can span a day the
    other series lacks.
    """
    idx = pd.DatetimeIndex(dates)
    inner = np.arange(1, len(idx) - 1)
    out = []
    for k in (n_a, n_b):
        drop = rng.choice(inner, size=int(k), replace=False)
        px = np.exp(np.cumsum(rng.standard_normal(len(idx)) * DAILY_VOL))
        keep = np.ones(len(idx), dtype=bool)
        keep[drop] = False
        out.append(pd.Series(px[keep], index=idx[keep]))
    return out[0], out[1]


# ---------------------------------------------- real calendars (1.3, 6.3)
@lru_cache(maxsize=4)
def _daily_frame(start: str, end: str) -> pd.DataFrame:
    import swisseph as swe

    from vedic_astrology_core.markets.align import sample_instants
    from vedic_astrology_core.markets.features import indicator_frame
    from vedic_astrology_core.rules.eclipses import eclipses_between
    from vedic_astrology_core.utils.datetime_utils import julian_day_to_datetime

    dates = pd.date_range(start, end, freq="D")
    f = indicator_frame(sample_instants(dates, "12:00", "UTC"), ["SUN", "MOON", "MERCURY", "VENUS"])
    cols = {
        "mercury_retrograde": f["MERCURY_retro"].to_numpy(dtype=bool),
        "venus_combust": f["VENUS_combust"].to_numpy(dtype=bool),
        "moon_nakshatra_group": f["MOON_nakshatra"].isin(MOON_NAKSHATRA_GROUP).to_numpy(),
        "tithi_group": f["tithi"].isin(TITHI_GROUP).to_numpy(),
        "sun_nakshatra": (f["SUN_nakshatra"] == SUN_NAKSHATRA).to_numpy(),
        "sun_sign": (f["SUN_sign"] == SUN_SIGN).to_numpy(),
    }
    t0, t1 = dates[0], dates[-1]
    jd0 = swe.julday(t0.year, t0.month, t0.day, 0.0) - ECLIPSE_HALF_WINDOW - 1
    jd1 = swe.julday(t1.year, t1.month, t1.day, 24.0) + ECLIPSE_HALF_WINDOW + 1
    ecl = np.zeros(len(dates), dtype=bool)
    day0 = dates[0].normalize()
    for e in eclipses_between(jd0, jd1):
        d = pd.Timestamp(julian_day_to_datetime(e.jd))
        if d.tzinfo is not None:
            d = d.tz_convert("UTC").tz_localize(None)
        i = (d.normalize() - day0).days
        lo, hi = max(i - ECLIPSE_HALF_WINDOW, 0), min(i + ECLIPSE_HALF_WINDOW + 1, len(dates))
        if lo < hi:
            ecl[lo:hi] = True
    cols["eclipse_window"] = ecl
    return pd.DataFrame(cols, index=dates)


def daily_calendars(start: str = DAILY_GRID[0], end: str = DAILY_GRID[1]) -> pd.DataFrame:
    """Real calendars on the daily grid (noon UTC, sidereal Lahiri, mean node).

    Columns: ``mercury_retrograde``, ``venus_combust``, ``moon_nakshatra_group``
    (Moon in a fixed nakshatra), ``tithi_group`` (rikta tithis),
    ``sun_nakshatra`` (Sun in Ashwini), ``sun_sign`` (Sun in Aries),
    ``eclipse_window`` (3 days either side of any solar or lunar eclipse).
    Cached; a copy is returned.
    """
    return _daily_frame(str(start), str(end)).copy()


@lru_cache(maxsize=4)
def _yearly_frame(start: int, end: int, month: int, day: int) -> pd.DataFrame:
    from vedic_astrology_core.markets.align import sample_instants
    from vedic_astrology_core.markets.features import indicator_frame

    years = np.arange(int(start), int(end) + 1)
    dates = pd.DatetimeIndex([pd.Timestamp(int(y), month, day) for y in years])
    f = indicator_frame(sample_instants(dates, "12:00", "UTC"), ["RAHU", "JUPITER", "SATURN"])
    cols = {"rahu_longitude": f["RAHU_lon"].to_numpy(dtype=float)}
    for body in ("RAHU", "JUPITER", "SATURN"):
        for s in SIGNS:
            cols[f"{body.lower()}_in_{s.lower()}"] = (f[f"{body}_sign"] == s).to_numpy()
    return pd.DataFrame(cols, index=pd.Index(years, name="year"))


def yearly_calendars(start: int = YEARLY_GRID[0], end: int = YEARLY_GRID[1], month: int = 6, day: int = 1) -> pd.DataFrame:
    """Real calendars on the yearly grid, sampled at noon UTC on ``month``/``day``.

    Columns ``<body>_in_<sign>`` for Rahu, Jupiter and Saturn, plus
    ``rahu_longitude`` (degrees, sidereal) for :func:`nodal_wave`.
    """
    return _yearly_frame(int(start), int(end), int(month), int(day)).copy()



# ====================================================================
# Yearly-grid simulators (ADR-008 amendment A3.3, WP-100): cases Y1 to Y11.
# Every generator takes (years, rng) and returns a dict with the outcome
# "y" (one value per year, standard deviation 10 points unless stated), the
# ENSO-like "driver" the test is allowed to see (or None), and, where a case
# plants its own calendar, "active". None of them knows what the test does
# with it. Pass marks live in tests/test_stats_yearly.py.
# ====================================================================
YEARLY_SD = 10.0
YEARLY_LENGTHS = (34, 69, 146)
YEARLY_DROUGHT_RATE = 0.15
#: Y4: spectral peak (years) and lag-1 correlation of the AR(2) outcome; the
#: alternating component's size and yearly phase-flip probability.
BIENNIAL_PERIOD = 2.3
BIENNIAL_RHO1 = -0.25
ALTERNATING_AMPLITUDE = 3.0
ALTERNATING_FLIP = 0.15
#: Y5: proxy correlation, asymmetric responses (warm, cold), the warm/cold
#: threshold in driver standard deviations, quasi-cycle period (years).
ENSO_PROXY_CORR = 0.7
ENSO_WARM_EFFECT = -8.0
ENSO_COLD_EFFECT = 3.0
ENSO_PHASE_SD = 0.5
ENSO_QUASI_PERIOD = 4.0
ENSO_QUASI_DAMPING = 0.8
#: Y6: linear trend over the record, wave amplitude (31-year period) and
#: step size at two thirds of the record, all in outcome standard deviations.
TREND_SPAN = 1.0
WAVE_AMPLITUDE = 0.5
WAVE_PERIOD = 31.0
STEP_SIZE = 0.5
STEP_AT = 2.0 / 3.0
#: Y7: R2 of the calendar on the driver (the N-02 values).
LOADED_R2 = (0.14, 0.29, 0.39)
#: Y11: long-memory parameter.
LONG_MEMORY_D = 0.2
#: Real monsoon calendars (ADR-008 A3.3): the rules of rules/monsoon.
YEARLY_RULE_CALENDARS = ("mars_in_rohini", "ardra_weekday_malefic", "varsheshvara_malefic")
YEARLY_SYNTHETIC_CALENDARS = ("alternation", "bernoulli_0.4", "three_on_four_off")
#: Sign calendars of A3.3: Saturn, Jupiter and Rahu in one sign (the sign is fixed here).
YEARLY_SIGN_CALENDARS = ("saturn_in_capricorn", "jupiter_in_sagittarius", "rahu_in_aries")
MALEFIC_LORDS = ("Sun", "Mars", "Saturn")
UJJAIN = {"lat": 23.1765, "lon": 75.7885, "tz_offset_hours": 5.5}
MARS_WINDOW = ((3, 1), (9, 30))  # window_after = 3 months before 1 June
MARS_STEP_DAYS = 2
NINO34_SNAPSHOT = "data/snapshots/noaa_nino34_8ba6cd0536ad.data"


def yearly_normal(years, rng: np.random.Generator, sd: float = YEARLY_SD) -> Dict[str, object]:
    """Y1: independent Normal(0, sd)."""
    return {"y": rng.standard_normal(len(years)) * sd, "driver": None}


def yearly_mirrored_lognormal(years, rng: np.random.Generator, sd: float = YEARLY_SD) -> Dict[str, object]:
    """Y2: minus a Lognormal(0, 1), centred and scaled to sd (long dry tail, skew about -6.2)."""
    m, v = math.exp(0.5), (math.e - 1.0) * math.e
    x = rng.lognormal(0.0, 1.0, len(years))
    return {"y": -(x - m) / math.sqrt(v) * sd, "driver": None}


def yearly_mirrored_exponential(years, rng: np.random.Generator, sd: float = YEARLY_SD) -> Dict[str, object]:
    """Y2: minus an Exponential(1), centred and scaled to sd (skew -2)."""
    return {"y": -(rng.exponential(1.0, len(years)) - 1.0) * sd, "driver": None}


def drought_threshold(rate: float = YEARLY_DROUGHT_RATE, sd: float = YEARLY_SD) -> float:
    """The rate point of Normal(0, sd): Y2's drought flag is y below it."""
    from scipy.stats import norm

    return float(norm.ppf(rate)) * float(sd)


def yearly_drought_flag(years, rng: np.random.Generator, rate: float = YEARLY_DROUGHT_RATE) -> Dict[str, object]:
    """Y2, YX2: yes/no drought flag, the Y1 value below its rate point ("y" holds the flags)."""
    z = yearly_normal(years, rng)["y"]
    return {"y": (z < drought_threshold(rate)).astype(np.int8), "driver": None, "latent": z}


def yearly_ar1(years, rng: np.random.Generator, phi: float, sd: float = YEARLY_SD) -> Dict[str, object]:
    """Y3, Y11: stationary AR(1), lag-1 correlation phi, marginal sd."""
    return {"y": ar1(len(years), rng, phi, sd), "driver": None}


def ar2_coefficients(period: float, rho1: float) -> Tuple[float, float]:
    """AR(2) (phi1, phi2) with lag-1 correlation rho1 and spectral peak at period years.

    rho1 = phi1 / (1 - phi2) and cos(w) = phi1 (phi2 - 1) / (4 phi2) with
    w = 2 pi / period. With a = -phi2 this is rho1 a^2 + (2 rho1 - 4 cos w) a + rho1 = 0;
    the root inside the stationary region is taken.
    """
    c = math.cos(2.0 * math.pi / period)
    A, B, C = rho1, 2.0 * rho1 - 4.0 * c, rho1
    disc = B * B - 4.0 * A * C
    if disc < 0:
        raise ValueError("no AR(2) has that peak and lag-1 correlation")
    roots = [(-B + s * math.sqrt(disc)) / (2.0 * A) for s in (1.0, -1.0)]
    for a in sorted(roots, key=abs):
        phi2 = -a
        phi1 = rho1 * (1.0 - phi2)
        if a > 0 and -1.0 < phi2 < 1.0 and phi1 + phi2 < 1.0 and phi2 - phi1 < 1.0:
            return phi1, phi2
    raise ValueError("no stationary AR(2) has that peak and lag-1 correlation")


def ar2_variance_ratio(phi1: float, phi2: float) -> float:
    """Marginal variance of a stationary AR(2) over its innovation variance."""
    return (1.0 - phi2) / ((1.0 + phi2) * ((1.0 - phi2) ** 2 - phi1 * phi1))


def ar2_series(n: int, rng: np.random.Generator, phi1: float, phi2: float, sd: float = 1.0, burn: int = 300) -> np.ndarray:
    """Stationary AR(2) scaled to marginal standard deviation sd."""
    scale = float(sd) / math.sqrt(ar2_variance_ratio(phi1, phi2))
    e = (rng.standard_normal(int(n) + burn) * scale).tolist()
    x = [0.0, 0.0]
    for t in range(len(e)):
        x.append(phi1 * x[-1] + phi2 * x[-2] + e[t])
    return np.asarray(x[2 + burn :])


def yearly_biennial_ar2(years, rng: np.random.Generator, sd: float = YEARLY_SD) -> Dict[str, object]:
    """Y4 (first): AR(2) with spectral peak at 2.3 years and lag-1 correlation -0.25."""
    phi1, phi2 = ar2_coefficients(BIENNIAL_PERIOD, BIENNIAL_RHO1)
    return {"y": ar2_series(len(years), rng, phi1, phi2, sd), "driver": None}


def alternating_component(n: int, rng: np.random.Generator, amplitude: float = ALTERNATING_AMPLITUDE, flip: float = ALTERNATING_FLIP) -> np.ndarray:
    """Plus or minus amplitude alternating each year; with probability flip a year repeats the last sign (phase flip)."""
    s = np.empty(int(n))
    cur = 1.0 if rng.random() < 0.5 else -1.0
    u = rng.random(int(n))
    for t in range(int(n)):
        if t:
            cur = cur if u[t] < flip else -cur
        s[t] = cur
    return amplitude * s


def yearly_alternating(years, rng: np.random.Generator, sd: float = YEARLY_SD) -> Dict[str, object]:
    """Y4 (second): Normal(0, sd) plus an alternating +-3 whose phase flips with probability 0.15 a year."""
    n = len(years)
    return {"y": rng.standard_normal(n) * sd + alternating_component(n, rng), "driver": None}


def enso_quasi_cycle(n: int, rng: np.random.Generator, period: float = ENSO_QUASI_PERIOD, damping: float = ENSO_QUASI_DAMPING) -> np.ndarray:
    """Unit-variance AR(2) driver with a peak near period years (Y5d)."""
    w = 2.0 * math.pi / period
    return ar2_series(n, rng, 2.0 * damping * math.cos(w), -damping * damping, 1.0)


@lru_cache(maxsize=1)
def _nino34_jjas() -> pd.Series:
    from pathlib import Path

    from vedic_astrology_core.domains.monsoon import parse_psl_monthly

    root = Path(__file__).resolve().parents[1]
    df = parse_psl_monthly((root / NINO34_SNAPSHOT).read_text())
    s = df[["JUN", "JUL", "AUG", "SEP"]].mean(axis=1, skipna=False).dropna()
    return (s - s.mean()) / s.std()


def real_enso_driver(years) -> np.ndarray:
    """Y5e: the pinned Nino 3.4 June-September mean anomaly (unit SD over the series), for years."""
    s = _nino34_jjas()
    yrs = np.asarray(years, dtype=int)
    if yrs.min() < s.index.min() or yrs.max() > s.index.max():
        raise ValueError(f"the pinned Nino 3.4 series covers {s.index.min()} to {s.index.max()}")
    return s.reindex(yrs).to_numpy(dtype=float)


def yearly_enso(years, rng: np.random.Generator, variant: str = "a", sd: float = YEARLY_SD) -> Dict[str, object]:
    """Y5: Z3-style rainfall, 4 * driver plus Normal(0, sd) noise, variants a to e.

    a: the test sees the driver. b: it sees a proxy with correlation 0.7 to it.
    c: asymmetric, warm years (driver at or above +0.5) -8, cold years (at or below -0.5) +3.
    d: the driver has a 4-year quasi-cycle. e: the driver is the real Nino 3.4 series.
    """
    n = len(years)
    noise = rng.standard_normal(n) * sd
    if variant == "e":
        z = real_enso_driver(years)
    elif variant == "d":
        z = enso_quasi_cycle(n, rng)
    else:
        z = ar1(n, rng, RAIN_ENSO_PHI)
    if variant == "c":
        y = noise + np.where(z >= ENSO_PHASE_SD, ENSO_WARM_EFFECT, 0.0) + np.where(z <= -ENSO_PHASE_SD, ENSO_COLD_EFFECT, 0.0)
    else:
        y = RAIN_ENSO_WEIGHT * z + noise
    seen = z
    if variant == "b":
        seen = ENSO_PROXY_CORR * z + math.sqrt(1.0 - ENSO_PROXY_CORR**2) * rng.standard_normal(n)
    return {"y": y, "driver": seen, "true_driver": z}


def yearly_trend_epoch(years, rng: np.random.Generator, variant: str = "trend", sd: float = YEARLY_SD) -> Dict[str, object]:
    """Y6: Normal(0, sd) plus a trend (rise of 1 sd over the record), a wave (31 years, 0.5 sd) or a step (0.5 sd at two thirds)."""
    n = len(years)
    t = np.arange(n, dtype=float)
    y = rng.standard_normal(n) * sd
    if variant == "trend":
        y = y + TREND_SPAN * sd * (t / max(n - 1, 1) - 0.5)
    elif variant == "wave":
        y = y + WAVE_AMPLITUDE * sd * np.sin(2.0 * math.pi * t / WAVE_PERIOD + rng.uniform(0.0, 2.0 * math.pi))
    elif variant == "step":
        y = y + STEP_SIZE * sd * (t >= int(round(STEP_AT * n))).astype(float)
    else:
        raise ValueError("variant must be trend, wave or step")
    return {"y": y, "driver": None}


def arfima_noise(n: int, rng: np.random.Generator, d: float, sd: float = YEARLY_SD, n_lags: int = 1000) -> np.ndarray:
    """Y11: fractionally integrated ARFIMA(0, d, 0) noise with marginal sd (lag-1 correlation d / (1 - d))."""
    if not -0.5 < d < 0.5:
        raise ValueError("d must lie in (-0.5, 0.5)")
    k = np.arange(1, n_lags)
    psi = np.concatenate([[1.0], np.cumprod((k - 1 + d) / k)])
    eps = rng.standard_normal(int(n) + n_lags)
    x = np.convolve(eps, psi, mode="full")[n_lags : n_lags + int(n)]
    var = math.gamma(1.0 - 2.0 * d) / math.gamma(1.0 - d) ** 2  # exact marginal variance
    return x / math.sqrt(var) * sd


def yearly_long_memory(years, rng: np.random.Generator, d: float = LONG_MEMORY_D, sd: float = YEARLY_SD) -> Dict[str, object]:
    """Y11: long memory (fractional d = 0.2)."""
    return {"y": arfima_noise(len(years), rng, d, sd), "driver": None}


# ---------------------------------------------------------------- calendars
def synthetic_calendar(kind: str, n: int, rng: np.random.Generator = None) -> np.ndarray:
    """Synthetic yearly calendars: strict alternation (active first), bernoulli_0.4, three_on_four_off."""
    t = np.arange(int(n))
    if kind == "alternation":
        return t % 2 == 0
    if kind == "three_on_four_off":
        return (t % 7) < 3
    if kind.startswith("bernoulli_"):
        if rng is None:
            raise ValueError("a Bernoulli calendar needs rng")
        return rng.random(int(n)) < float(kind.split("_", 1)[1])
    raise ValueError(f"unknown synthetic calendar {kind!r}")


def calendar_r2(active, driver) -> float:
    """R2 of the 0/1 calendar regressed on the driver (baseline_r2 of one baseline)."""
    a = np.asarray(active, dtype=float)
    z = np.asarray(driver, dtype=float)
    if a.std() == 0 or z.std() == 0:
        return 0.0
    return float(np.corrcoef(a, z)[0, 1] ** 2)


def driver_loaded_calendar(driver, r2: float, rng: np.random.Generator, duty: float = 0.4, tol: float = 0.01) -> np.ndarray:
    """Y7: a calendar with a duty share of active years whose R2 on the driver is r2 (within tol).

    Active = the top duty share of w * driver + (1 - w) * noise; w is found by
    bisection for the drawn noise, so the sample R2 (what R4 reads) hits the
    target, not only its expectation.
    """
    z = np.asarray(driver, dtype=float)
    z = (z - z.mean()) / z.std()
    noise = rng.standard_normal(len(z))
    k = max(1, int(round(duty * len(z))))

    def make(w):
        score = w * z + (1.0 - w) * noise
        out = np.zeros(len(z), dtype=bool)
        out[np.argsort(-score, kind="stable")[:k]] = True
        return out

    # Start from the bisection answer, then swap one active and one inactive
    # year at a time, keeping a swap that moves the sample R2 closer to the
    # target (the R2 of a 0/1 calendar on a short record is granular).
    lo, hi = 0.0, 1.0
    best = make(0.5)
    for _ in range(30):
        mid = (lo + hi) / 2.0
        best = make(mid)
        lo, hi = (mid, hi) if calendar_r2(best, z) < r2 else (lo, mid)
    cur = best.copy()
    err = abs(calendar_r2(cur, z) - r2)
    for _ in range(20_000):
        if err <= tol / 4.0:
            break
        i = rng.choice(np.flatnonzero(cur))
        j = rng.choice(np.flatnonzero(~cur))
        cur[i], cur[j] = False, True
        e = abs(calendar_r2(cur, z) - r2)
        if e < err:
            err = e
        else:
            cur[i], cur[j] = True, False
    if err > tol:
        raise ValueError(f"cannot reach R2 {r2} with {len(z)} years (got {calendar_r2(cur, z):.3f})")
    return cur


def yearly_driver_loaded(years, rng: np.random.Generator, r2: float, duty: float = 0.4) -> Dict[str, object]:
    """Y7: the Y5(a) outcome with a calendar loaded on the driver at R2 r2."""
    out = yearly_enso(years, rng, "a")
    out["active"] = driver_loaded_calendar(out["driver"], r2, rng, duty)
    return out


@lru_cache(maxsize=2)
def _rule_frame(start: int, end: int) -> pd.DataFrame:
    from vedic_astrology_core.domains import monsoon as M
    from vedic_astrology_core.markets.align import sample_instants
    from vedic_astrology_core.markets.features import indicator_frame

    years = np.arange(int(start), int(end) + 1)
    days = []
    for y in years:
        days.extend(pd.date_range(pd.Timestamp(int(y), *MARS_WINDOW[0]), pd.Timestamp(int(y), *MARS_WINDOW[1]), freq=f"{MARS_STEP_DAYS}D"))
    f = indicator_frame(sample_instants(pd.DatetimeIndex(days), "00:00", "UTC"), ["MARS"])
    in_rohini = (f["MARS_nakshatra"] == "Rohini").to_numpy()
    yr = np.asarray([d.year for d in days])
    mars = np.array([bool(in_rohini[yr == y].any()) for y in years])
    ardra, varsh = [], []
    for y in years:
        jd = M.sun_nakshatra_ingress(int(y), "Ardra", "lahiri")
        ardra.append(M.vara_lord(jd, "sunrise", UJJAIN)[0] in MALEFIC_LORDS)
        jd = M.chaitra_shukla_pratipada(int(y))
        varsh.append(M.vara_lord(jd, "sunrise", UJJAIN)[0] in MALEFIC_LORDS)
    return pd.DataFrame(
        {"mars_in_rohini": mars, "ardra_weekday_malefic": ardra, "varsheshvara_malefic": varsh},
        index=pd.Index(years, name="year"),
    )


def yearly_rule_calendars(start: int = YEARLY_GRID[0], end: int = YEARLY_GRID[1]) -> pd.DataFrame:
    """Real monsoon-rule calendars, one yes/no per year.

    mars_in_rohini: Mars in Rohini on any 2-day sample from 1 March to 30
    September (00:00 UTC, Lahiri). ardra_weekday_malefic and
    varsheshvara_malefic: the weekday lord (sunrise at Ujjain) at the Sun's
    Ardra ingress, and at Chaitra Shukla Pratipada, is Sun, Mars or Saturn.
    Cached; a copy is returned.
    """
    return _rule_frame(int(start), int(end)).copy()


def yearly_case_calendar(name: str, n: int, rng: np.random.Generator = None) -> np.ndarray:
    """The calendar name over the last n years of the grid (34: 1983-2016, 69: 1948-2016, 146: 1871-2016).

    Real calendars come from the ephemeris (yearly_calendars for the sign
    calendars, yearly_rule_calendars for the rules); synthetic ones from
    synthetic_calendar.
    """
    n = int(n)
    if YEARLY_GRID[1] - n + 1 < YEARLY_GRID[0]:
        raise ValueError("the record cannot be longer than the yearly grid")
    if name in YEARLY_RULE_CALENDARS:
        return yearly_rule_calendars()[name].to_numpy(dtype=bool)[-n:]
    if name in YEARLY_SYNTHETIC_CALENDARS:
        return synthetic_calendar(name, n, rng)
    return yearly_calendars()[name].to_numpy(dtype=bool)[-n:]


# --------------------------------------------- naive designs (Y10, kept on record)
def gap_midpoint_usable_blocks(active) -> int:
    """Y10(a): blocks the old gap-midpoint block rule can use on a yearly grid.

    Each active run takes inactive years from the gap on each side; a gap
    between two runs is split at its midpoint and an odd middle year goes to
    neither; a gap at the record's edge goes whole to the one run beside it. A
    run is usable when it gets at least as many control years as it has active
    years (equal-size blocks).
    """
    a = np.asarray(active, dtype=bool)
    runs = episode_runs(a)
    n = len(a)
    usable = 0
    for i, (s, e) in enumerate(runs):
        length = e - s
        left_gap = s - (runs[i - 1][1] if i else 0)
        right_gap = (runs[i + 1][0] if i + 1 < len(runs) else n) - e
        left = left_gap // 2 if i else left_gap
        right = right_gap // 2 if i + 1 < len(runs) else right_gap
        usable += int(left + right >= length)
    return usable


def naive_free_permutation_p(y, active, rng: np.random.Generator, n_perm: int = 199, alternative: str = "greater") -> float:
    """Y10(b, c): free permutation of the calendar over the years, no strata, no dependence allowance.

    Statistic: mean outcome of active years minus the rest. Returns the
    one-sided p (1 + #{T* at least as extreme}) / (n_perm + 1).
    """
    y = np.asarray(y, dtype=float)
    a = np.asarray(active, dtype=bool)
    k, n = int(a.sum()), len(y)
    t = y[a].mean() - y[~a].mean()
    idx = np.argsort(rng.random((int(n_perm), n)), axis=1)[:, :k]
    sums = y[idx].sum(axis=1)
    ts = sums / k - (y.sum() - sums) / (n - k)
    hit = (ts >= t - 1e-12) if alternative == "greater" else (ts <= t + 1e-12)
    return float((1 + hit.sum()) / (n_perm + 1))


class OutcomeSpy:
    """Y9: stands in for the outcome of a design function and records every read.

    Any indexing, iteration, arithmetic or numpy conversion raises
    AssertionError, so a design that peeks at the outcome fails loudly.
    """

    def __init__(self, n: int):
        self.n = int(n)
        self.reads = 0

    def _peek(self, *a, **k):
        self.reads += 1
        raise AssertionError("the design read the outcome")

    __getitem__ = __iter__ = __array__ = __add__ = __radd__ = __sub__ = __mul__ = __rmul__ = __float__ = _peek

    def __len__(self):
        return self.n


#: Generators of cases Y1 to Y7 and Y11 by name: (years, rng) -> dict.
YEARLY_GENERATORS = {
    "Y1": lambda yrs, rng: yearly_normal(yrs, rng),
    "Y2:lognormal": lambda yrs, rng: yearly_mirrored_lognormal(yrs, rng),
    "Y2:exponential": lambda yrs, rng: yearly_mirrored_exponential(yrs, rng),
    "Y2:flag": lambda yrs, rng: yearly_drought_flag(yrs, rng),
    **{f"Y3:{p:+.2f}": (lambda yrs, rng, p=p: yearly_ar1(yrs, rng, p)) for p in (-0.3, -0.15, 0.15, 0.3)},
    "Y4:ar2": lambda yrs, rng: yearly_biennial_ar2(yrs, rng),
    "Y4:alternating": lambda yrs, rng: yearly_alternating(yrs, rng),
    **{f"Y5:{v}": (lambda yrs, rng, v=v: yearly_enso(yrs, rng, v)) for v in "abcde"},
    **{f"Y6:{v}": (lambda yrs, rng, v=v: yearly_trend_epoch(yrs, rng, v)) for v in ("trend", "wave", "step")},
    **{f"Y7:{r:.2f}": (lambda yrs, rng, r=r: yearly_driver_loaded(yrs, rng, r)) for r in LOADED_R2},
    "Y11:ar1+0.5": lambda yrs, rng: yearly_ar1(yrs, rng, 0.5),
    "Y11:ar1-0.5": lambda yrs, rng: yearly_ar1(yrs, rng, -0.5),
    "Y11:long_memory": lambda yrs, rng: yearly_long_memory(yrs, rng),
}
