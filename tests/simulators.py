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
