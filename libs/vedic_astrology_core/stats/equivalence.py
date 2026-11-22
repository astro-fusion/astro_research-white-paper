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

ADR-004 D-6 / WP-08 and ADR-007 section 5 add a three-way decision against
the plan's smallest effect size of interest (SESOI) and the upper limit X:

* :func:`episode_equivalence` is the primary route for slow indicators. The
  unit is the episode; every p-value is the exact (or seeded Monte Carlo)
  sign-flip test of :func:`.episodes.sign_flip_test` on shifted per-episode
  differences, which is the same restricted wild cluster bootstrap that
  :func:`.episodes.wild_cluster_interval` inverts. No bar-level standard
  error enters, so serial correlation inside an episode cannot shrink the
  interval and manufacture a false "effect excluded".
* :func:`effect_equivalence` is the same decision from an estimate and a
  standard error the caller vouches for (an episode-clustered or block
  bootstrap SE, or an exact interval converted to one). It refuses a naive
  i.i.d. bar-level SE by requiring ``se_method``.
* :func:`upper_limit` and :func:`upper_limit_episodes` give X: the one-sided
  upper confidence limit of the effect in the claimed direction at a given
  level (X95 at 0.95; X-strict at ``1 - alpha / M``, see :func:`strict_level`).
  "Effects above X are ruled out by this dataset."

Effects are signed so that positive is the claimed direction. A claim with
direction ``"either"`` is about the size ``|theta|``: support is two-sided,
exclusion is TOST on ``(-SESOI, SESOI)``, and X bounds ``|theta|``. For a
directional claim exclusion is the single one-sided test of H0
``theta >= SESOI`` (an effect in the opposite direction is not the claimed
effect, and the "contradicted" verdict tests it separately).

Decisions: ``"found"`` (support p below alpha), ``"excluded"`` (equivalence
p below alpha), otherwise ``"inconclusive"``. When both hold the decision is
``"found"`` with ``below_sesoi`` set: a real but small effect. The word
"null" is never returned. Both p-values are returned raw so that a caller
can apply the same family correction to support and to exclusion
(ADR-007 F-7); ``alpha`` here is the per-test level the caller passes (the
rank-1 BY threshold of :func:`.power.family_alpha` gives a conservative
stand-alone decision).
"""

from dataclasses import dataclass, field
from typing import Hashable, List, Optional, Sequence

import numpy as np
from scipy import stats as sps

from .episodes import sign_flip_p_min, sign_flip_test, wild_cluster_interval
from .nulls import _check_rng, stationary_bootstrap_indices

DIRECTIONS = ("greater", "less", "either")
DECISIONS = ("found", "excluded", "inconclusive")
SE_METHODS = ("episode_cluster", "block_bootstrap", "exact", "analytic_independent")


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


# --------------------------------------------------------------------------
# SESOI decisions and the upper limit X (ADR-004 D-6, ADR-007 section 5)
# --------------------------------------------------------------------------


@dataclass
class EquivalenceDecision:
    """Found, excluded or inconclusive against the SESOI, with the bound X.

    ``estimate`` is signed so that positive is the claimed direction (for
    ``"either"`` it is the raw estimate; X bounds its absolute value).
    ``p_support`` tests H0 ``theta <= 0`` (two-sided H0 ``theta = 0`` for
    ``"either"``); ``p_equivalence`` tests H0 "the effect is at least the
    SESOI". ``x_upper`` is the upper limit at ``x_level``; it can be
    negative for a directional claim when the data point the other way, and
    is ``inf`` when there are too few episodes for the level.
    """

    decision: str
    estimate: float
    sesoi: float
    direction: str
    alpha: float
    p_support: float
    p_equivalence: float
    p_equivalence_lower: Optional[float]
    p_equivalence_upper: float
    found: bool
    excluded: bool
    below_sesoi: bool
    x_upper: float
    x_level: float
    method: str
    n_episodes: Optional[int] = None
    p_min: Optional[float] = None
    exclusion_attainable: bool = True
    notes: List[str] = field(default_factory=list)


def strict_level(budget: int, alpha: float = 0.05) -> float:
    """Return the level of X-strict, ``1 - alpha / M`` (ADR-007 section 5.2)."""
    m = int(budget)
    if m < 1:
        raise ValueError("budget must be at least 1")
    if not 0 < alpha < 1:
        raise ValueError("alpha must lie in (0, 1)")
    return 1.0 - float(alpha) / m


def _check_common(sesoi, direction, alpha, level=None):
    if direction not in DIRECTIONS:
        raise ValueError(f"direction must be one of {DIRECTIONS}, got {direction!r}")
    if not (np.isfinite(sesoi) and sesoi > 0):
        raise ValueError("sesoi must be positive and finite (signed effects)")
    if not 0 < alpha < 0.5:
        raise ValueError("alpha must lie in (0, 0.5)")
    if level is not None and not 0.5 < level < 1:
        raise ValueError("level must lie in (0.5, 1)")


def _signed(values, direction):
    return -values if direction == "less" else values


def _decide(found, excluded):
    if found:
        return "found"
    return "excluded" if excluded else "inconclusive"


def upper_limit(
    estimate: float,
    se: float,
    level: float = 0.95,
    direction: str = "greater",
    df: Optional[float] = None,
) -> float:
    """Return X: the one-sided upper confidence limit of the claimed effect.

    For ``"greater"`` it is ``estimate + q_level * se``; for ``"less"`` the
    estimate is negated first (so X is in the claimed direction); for
    ``"either"`` it is ``max(|L|, |U|)`` of the equal-tailed ``2 level - 1``
    interval, the smallest margin TOST would exclude at ``1 - level``.
    """
    if not se > 0:
        raise ValueError("se must be positive")
    if direction not in DIRECTIONS:
        raise ValueError(f"direction must be one of {DIRECTIONS}")
    if not 0.5 < level < 1:
        raise ValueError("level must lie in (0.5, 1)")
    dist = sps.norm if df is None else sps.t(df)
    q = float(dist.ppf(level))
    if direction == "either":
        return float(max(abs(estimate - q * se), abs(estimate + q * se)))
    est = float(_signed(np.float64(estimate), direction))
    return float(est + q * se)


def upper_limit_episodes(
    differences,
    level: float = 0.95,
    direction: str = "greater",
    rng: Optional[np.random.Generator] = None,
    n_draws: int = 99999,
) -> float:
    """Return X from per-episode differences (wild cluster interval).

    The upper bound of the equal-tailed :func:`.episodes.wild_cluster_interval`
    at level ``2 level - 1``, which is the one-sided limit at ``level``. With
    too few episodes for the level the answer is ``inf``: nothing is ruled
    out. For ``"either"`` it bounds ``|theta|``.
    """
    if direction not in DIRECTIONS:
        raise ValueError(f"direction must be one of {DIRECTIONS}")
    if not 0.5 < level < 1:
        raise ValueError("level must lie in (0.5, 1)")
    d = _signed(np.asarray(differences, dtype=float), direction)
    ci = wild_cluster_interval(d, level=2.0 * level - 1.0, rng=rng, n_draws=n_draws)
    if direction == "either":
        return float(max(abs(ci.ci_low), abs(ci.ci_high)))
    return float(ci.ci_high)


def effect_equivalence(
    estimate: float,
    se: float,
    sesoi: float,
    *,
    se_method: str,
    direction: str = "greater",
    alpha: float = 0.05,
    df: Optional[float] = None,
    x_level: float = 0.95,
) -> EquivalenceDecision:
    """Three-way decision from an estimate and a dependence-aware SE.

    Args:
        estimate: Effect on its own scale (for a rate ratio pass the log rate
            ratio and the log SESOI). Sign as observed; ``direction`` says
            which sign the claim predicts.
        se: Standard error of ``estimate``.
        sesoi: Smallest effect size of interest, positive, same scale.
        se_method: Where the SE comes from, one of :data:`SE_METHODS`.
            ``"analytic_independent"`` is accepted only for data that really
            are independent (one observation per episode or year); with it a
            note is recorded. A bar-level SE for an autocorrelated series
            understates the uncertainty and produces false exclusions: use
            :func:`episode_equivalence` instead.
        alpha: Per-test level for both one-sided tests.
        df: Student-t degrees of freedom (e.g. episodes - 1); None is normal.
        x_level: Level of the reported upper limit X (0.95 gives X95).
    """
    _check_common(sesoi, direction, alpha, x_level)
    if se_method not in SE_METHODS:
        raise ValueError(f"se_method must be one of {SE_METHODS}, got {se_method!r}")
    if not (np.isfinite(se) and se > 0):
        raise ValueError("se must be positive and finite")
    dist = sps.norm if df is None else sps.t(df)
    notes = []
    if se_method == "analytic_independent":
        notes.append("SE assumes independent observations")
    if direction == "either":
        p_support = float(2.0 * dist.sf(abs(estimate) / se))
        p_low = float(dist.sf((estimate + sesoi) / se))
        p_up = float(dist.cdf((estimate - sesoi) / se))
        p_eq = max(p_low, p_up)
        est = float(estimate)
    else:
        est = float(_signed(np.float64(estimate), direction))
        p_support = float(dist.sf(est / se))
        p_low = None
        p_up = float(dist.cdf((est - sesoi) / se))
        p_eq = p_up
    found = p_support < alpha
    excluded = p_eq < alpha
    return EquivalenceDecision(
        decision=_decide(found, excluded),
        estimate=est,
        sesoi=float(sesoi),
        direction=direction,
        alpha=float(alpha),
        p_support=min(1.0, p_support),
        p_equivalence=float(p_eq),
        p_equivalence_lower=p_low,
        p_equivalence_upper=p_up,
        found=bool(found),
        excluded=bool(excluded),
        below_sesoi=bool(found and excluded),
        x_upper=upper_limit(estimate, se, x_level, direction, df),
        x_level=float(x_level),
        method=f"se:{se_method}",
        notes=notes,
    )


def episode_equivalence(
    differences,
    sesoi: float,
    *,
    direction: str = "greater",
    alpha: float = 0.05,
    x_level: float = 0.95,
    rng: Optional[np.random.Generator] = None,
    n_draws: int = 99999,
) -> EquivalenceDecision:
    """Three-way decision from per-episode differences (episode-clustered).

    Every p-value is a sign-flip test on the differences, shifted by the
    hypothesised value: support tests ``mean(d) = 0``; exclusion tests
    ``mean(d - SESOI) = 0`` against "less" (and, for ``"either"``,
    ``mean(d + SESOI) = 0`` against "greater", the larger p deciding). This is
    the test that :func:`.episodes.wild_cluster_interval` inverts, so
    "excluded" at ``alpha`` agrees with the ``1 - 2 alpha`` interval lying
    below the SESOI. With 20 or fewer episodes the tests are exact by
    enumeration; above that pass ``rng``.

    If the attainable minimum p (``2**-K``) is not below ``alpha``, nothing
    can be excluded or found; the decision is "inconclusive" and
    ``exclusion_attainable`` is False.

    Args:
        differences: One value per episode (NaN dropped), e.g. the
            ``difference`` column of :func:`.episodes.episode_differences`,
            on the outcome's own scale, as observed (not yet signed).
        sesoi: Positive SESOI in the same unit.
        direction: ``"greater"``, ``"less"`` or ``"either"``.
        alpha: Per-test level.
        x_level: Level of the upper limit X.
    """
    _check_common(sesoi, direction, alpha, x_level)
    raw = np.asarray(differences, dtype=float).ravel()
    raw = raw[np.isfinite(raw)]
    if len(raw) == 0:
        raise ValueError("no finite per-episode differences")
    k = len(raw)
    d = _signed(raw, direction)
    kw = {"rng": rng, "n_draws": n_draws}
    if direction == "either":
        p_support = sign_flip_test(d, alternative="two-sided", **kw).p_value
        p_low = sign_flip_test(d + sesoi, alternative="greater", **kw).p_value
        p_up = sign_flip_test(d - sesoi, alternative="less", **kw).p_value
        p_eq = max(p_low, p_up)
        p_min = sign_flip_p_min(k, "greater", n_draws)
        p_min_support = sign_flip_p_min(k, "two-sided", n_draws)
    else:
        p_support = sign_flip_test(d, alternative="greater", **kw).p_value
        p_low = None
        p_up = sign_flip_test(d - sesoi, alternative="less", **kw).p_value
        p_eq = p_up
        p_min = p_min_support = sign_flip_p_min(k, "greater", n_draws)
    attainable = p_min < alpha
    notes = []
    if not attainable:
        notes.append(
            f"{k} episode(s): attainable minimum p {p_min:.3g} is not below "
            f"alpha {alpha:.3g}; the effect can be neither found nor excluded"
        )
    found = bool(p_support < alpha and p_min_support < alpha)
    excluded = bool(p_eq < alpha and attainable)
    x = upper_limit_episodes(raw, x_level, direction, rng=rng, n_draws=n_draws)
    return EquivalenceDecision(
        decision=_decide(found, excluded),
        estimate=float(d.mean()),
        sesoi=float(sesoi),
        direction=direction,
        alpha=float(alpha),
        p_support=float(p_support),
        p_equivalence=float(p_eq),
        p_equivalence_lower=None if p_low is None else float(p_low),
        p_equivalence_upper=float(p_up),
        found=found,
        excluded=excluded,
        below_sesoi=bool(found and excluded),
        x_upper=x,
        x_level=float(x_level),
        method="episode_sign_flip",
        n_episodes=int(k),
        p_min=float(p_min),
        exclusion_attainable=bool(attainable),
        notes=notes,
    )
