"""Episode-level inference for slow indicators (ADR-004 D-6, WP-04).

A slow indicator (Jupiter in a sign, a retrograde) is active for long runs of
consecutive bars. Bars inside one run share one market regime, so the run,
not the bar, is the unit of evidence (review items M1 and M2). This module:

* :func:`episodes` turns a boolean calendar into episodes: maximal runs of
  active bars, with runs separated by at most ``merge_gap`` inactive bars
  (or calendar time) merged into one episode. A planet that leaves a sign
  during a retrograde loop and re-enters it is therefore one episode.
* :func:`testable` applies the D-6 rule from the calendar alone, before any
  outcome is read: at least ``min_episodes`` episodes **and** an attainable
  minimum p below the rank-1 Benjamini-Yekutieli threshold
  ``alpha / (m * H_m)`` of the family. An indicator that fails is
  "untestable with this sample" and stays outside the family.
* :func:`episode_differences` reduces bar-level outcomes to one number per
  episode: the mean outcome on the episode's active bars minus the mean on
  its neighbouring inactive windows (``window`` bars before and after).
* :func:`sign_flip_test` tests the mean of those differences against the
  null that each is symmetric about zero. With 20 or fewer episodes all
  ``2**K`` sign patterns are enumerated (exact p); above that a seeded
  Monte Carlo sample is used with ``p = (k + 1) / (B + 1)``. Ties count as
  extreme.
* :func:`wild_cluster_interval` gives an interval for the mean difference
  from the wild cluster bootstrap by episode, with Rademacher weights and the
  null imposed (restricted), inverted over the null value. For the mean of
  cluster-level scores this inversion has a closed form: the bounds are
  order statistics of the subset means of the differences (Hartigan 1969),
  and coverage is at least the nominal level whenever the differences are
  symmetric about the true mean, however few the episodes. With too few
  episodes for the requested level the interval is unbounded, which is the
  honest answer; it never falls back to a normal approximation. Unrestricted
  wild bootstraps and cluster-robust t intervals are anti-conservative with
  a handful of clusters and are deliberately not offered.

Every function is deterministic given its inputs (and ``rng`` for the Monte
Carlo branches).
"""

from dataclasses import dataclass, field
from typing import List, Optional, Union

import numpy as np
import pandas as pd

from .nulls import shift_null_info

ALTERNATIVES = ("greater", "less", "two-sided")
TESTS = ("shift", "sign_flip")
MAX_ENUMERATED = 20
UNTESTABLE = "untestable with this sample"
_CHUNK = 1 << 16


@dataclass(frozen=True)
class Episode:
    """One episode: bars ``start`` to ``end`` inclusive (positions).

    ``n_active`` counts active bars; a merged episode also spans the
    inactive bars of the gaps it closed (``n_bars - n_active`` of them).
    ``start_label`` and ``end_label`` are index labels when the input
    was a Series, else the positions.
    """

    start: int
    end: int
    n_active: int
    n_runs: int
    start_label: object = None
    end_label: object = None

    @property
    def n_bars(self) -> int:
        """Bars spanned, active or not."""
        return self.end - self.start + 1


@dataclass
class Testability:
    """Outcome of :func:`testable`."""

    testable: bool
    label: str
    n_episodes: int
    min_episodes: int
    p_min: float
    by_rank1_threshold: float
    family_size: int
    alpha: float
    test: str
    reasons: List[str] = field(default_factory=list)


@dataclass
class SignFlipResult:
    """Outcome of :func:`sign_flip_test`."""

    statistic: float
    p_value: float
    p_min: float
    n_episodes: int
    n_null: int
    exact_enumeration: bool
    alternative: str
    differences: np.ndarray = field(repr=False, default=None)


@dataclass
class ClusterInterval:
    """Outcome of :func:`wild_cluster_interval`."""

    estimate: float
    ci_low: float
    ci_high: float
    level: float
    n_episodes: int
    n_patterns: int
    exact_enumeration: bool
    bounded: bool


# --------------------------------------------------------------------------
# Episodes
# --------------------------------------------------------------------------


def _as_indicator(indicator) -> np.ndarray:
    values = (
        indicator.to_numpy()
        if isinstance(indicator, pd.Series)
        else np.asarray(indicator)
    )
    if values.ndim != 1:
        raise ValueError("indicator must be one-dimensional")
    if values.dtype.kind == "f" and np.isnan(values).any():
        raise ValueError("indicator contains NaN; fill or drop it first")
    if values.dtype.kind not in "biuf":
        raise ValueError(f"indicator must be boolean or 0/1, got dtype {values.dtype}")
    if values.dtype.kind != "b" and not np.isin(values, (0, 1)).all():
        raise ValueError("indicator must contain only 0/1 or booleans")
    return values.astype(bool)


def _runs(active: np.ndarray) -> List[tuple]:
    """Maximal runs of True as (start, end) inclusive positions."""
    if not active.any():
        return []
    padded = np.concatenate(([False], active, [False])).astype(np.int8)
    edges = np.diff(padded)
    starts = np.flatnonzero(edges == 1)
    ends = np.flatnonzero(edges == -1) - 1
    return list(zip(starts.tolist(), ends.tolist()))


def episodes(indicator, merge_gap: Union[int, str, pd.Timedelta] = 0) -> List[Episode]:
    """Return the episodes of a boolean indicator calendar.

    Args:
        indicator: Boolean (or 0/1) sequence or Series, one value per bar.
        merge_gap: Runs separated by a gap no longer than this are merged.
            An integer counts inactive bars between the runs (0 merges
            nothing). A ``pd.Timedelta`` or a string such as ``"120D"``
            needs a Series with a DatetimeIndex and compares the time from
            the last active bar of one run to the first active bar of the
            next. The value belongs to the plan, never to the data.

    Returns:
        Episodes in time order.
    """
    active = _as_indicator(indicator)
    index = indicator.index if isinstance(indicator, pd.Series) else None
    timed = isinstance(merge_gap, (str, pd.Timedelta, np.timedelta64)) or hasattr(
        merge_gap, "total_seconds"
    )
    if timed:
        gap_td = pd.Timedelta(merge_gap)
        if gap_td < pd.Timedelta(0):
            raise ValueError("merge_gap must not be negative")
        if not isinstance(index, pd.DatetimeIndex):
            raise ValueError(
                "a time-based merge_gap needs a Series with a DatetimeIndex"
            )
        if not index.is_monotonic_increasing:
            raise ValueError("the DatetimeIndex must be increasing")
    else:
        if isinstance(merge_gap, bool) or int(merge_gap) != merge_gap:
            raise ValueError(
                "merge_gap must be an integer number of bars or a time span"
            )
        merge_gap = int(merge_gap)
        if merge_gap < 0:
            raise ValueError("merge_gap must not be negative")

    merged: List[list] = []
    for start, end in _runs(active):
        if merged:
            prev = merged[-1]
            if timed:
                close = index[start] - index[prev[1]] <= gap_td
            else:
                close = start - prev[1] - 1 <= merge_gap
            if close:
                prev[1] = end
                prev[2] += end - start + 1
                prev[3] += 1
                continue
        merged.append([start, end, end - start + 1, 1])

    out = []
    for start, end, n_active, n_runs in merged:
        out.append(
            Episode(
                start=int(start),
                end=int(end),
                n_active=int(n_active),
                n_runs=int(n_runs),
                start_label=index[start] if index is not None else int(start),
                end_label=index[end] if index is not None else int(end),
            )
        )
    return out


def episode_labels(
    indicator, merge_gap: Union[int, str, pd.Timedelta] = 0
) -> np.ndarray:
    """Episode number (0, 1, ...) of each active bar; -1 for inactive bars.

    Inactive bars inside a merged gap are -1 too: they belong to the
    episode's span but carry no indicator exposure.
    """
    active = _as_indicator(indicator)
    labels = np.full(len(active), -1, dtype=np.int64)
    for k, ep in enumerate(episodes(indicator, merge_gap)):
        span = np.arange(ep.start, ep.end + 1)
        labels[span[active[span]]] = k
    return labels


def episode_table(
    indicator, merge_gap: Union[int, str, pd.Timedelta] = 0
) -> pd.DataFrame:
    """Episodes as a DataFrame (one row each), for results and figures."""
    rows = [
        {
            "episode": k,
            "start": ep.start_label,
            "end": ep.end_label,
            "n_bars": ep.n_bars,
            "n_active": ep.n_active,
            "n_runs": ep.n_runs,
        }
        for k, ep in enumerate(episodes(indicator, merge_gap))
    ]
    return pd.DataFrame(
        rows, columns=["episode", "start", "end", "n_bars", "n_active", "n_runs"]
    )


# --------------------------------------------------------------------------
# Testability (D-6)
# --------------------------------------------------------------------------


def by_rank1_threshold(family_size: int, alpha: float = 0.05) -> float:
    """Smallest Benjamini-Yekutieli rejection threshold ``alpha / (m H_m)``.

    A p-value must be strictly below it to give a q-value below ``alpha``
    (as :func:`.multiplicity.family` marks significance).
    """
    m = int(family_size)
    if m < 1:
        raise ValueError("family_size must be at least 1")
    if not 0 < alpha < 1:
        raise ValueError("alpha must lie in (0, 1)")
    h_m = float(np.sum(1.0 / np.arange(1, m + 1)))
    return float(alpha / (m * h_m))


def sign_flip_p_min(
    n_episodes: int, alternative: str = "two-sided", n_draws: Optional[int] = None
) -> float:
    """Smallest p-value :func:`sign_flip_test` can return for K episodes."""
    k = int(n_episodes)
    if alternative not in ALTERNATIVES:
        raise ValueError(f"alternative must be one of {ALTERNATIVES}")
    if k < 1:
        return 1.0
    if k <= MAX_ENUMERATED:
        hits = 2 if alternative == "two-sided" else 1
        return float(hits / 2.0**k)
    if n_draws is None:
        raise ValueError(f"more than {MAX_ENUMERATED} episodes needs n_draws")
    return float(1.0 / (int(n_draws) + 1))


def testable(
    indicator,
    *,
    merge_gap: Union[int, str, pd.Timedelta],
    family_size: int,
    alpha: float = 0.05,
    min_episodes: int = 8,
    test: str = "shift",
    min_shift: Optional[int] = None,
    n_draws: int = 10000,
    alternative: str = "two-sided",
) -> Testability:
    """Decide from the calendar alone whether an indicator may be tested.

    D-6: testable only with at least ``min_episodes`` episodes **and** an
    attainable minimum p strictly below the rank-1 BY threshold of the
    family. No outcome enters this function.

    Args:
        indicator: Boolean calendar for the period (one value per bar).
        merge_gap: The plan's merge gap (see :func:`episodes`).
        family_size: Number of hypotheses in the confirmatory family.
        alpha: Family false discovery rate.
        min_episodes: Minimum number of episodes (the plan's value; 8).
        test: ``"shift"`` (the exact circular-shift test of WP-A; needs
            ``min_shift`` and uses ``n_draws`` as its upper bound on
            shifts) or ``"sign_flip"`` (:func:`sign_flip_test`).
        alternative: For the sign-flip floor (two-sided doubles it).
    """
    if test not in TESTS:
        raise ValueError(f"test must be one of {TESTS}")
    active = _as_indicator(indicator)
    eps = episodes(indicator, merge_gap)
    threshold = by_rank1_threshold(family_size, alpha)
    if test == "shift":
        if min_shift is None:
            raise ValueError("the shift test needs min_shift")
        p_min = float(shift_null_info(len(active), min_shift, n_draws)["p_min"])
    else:
        p_min = sign_flip_p_min(len(eps), alternative, n_draws)
    reasons = []
    if len(eps) < min_episodes:
        reasons.append(f"{len(eps)} episode(s), fewer than {min_episodes}")
    if not p_min < threshold:
        reasons.append(
            f"attainable minimum p {p_min:.3g} is not below the rank-1 BY "
            f"threshold {threshold:.3g} (family of {int(family_size)}, alpha {alpha})"
        )
    ok = not reasons
    return Testability(
        testable=ok,
        label="testable" if ok else UNTESTABLE,
        n_episodes=len(eps),
        min_episodes=int(min_episodes),
        p_min=p_min,
        by_rank1_threshold=threshold,
        family_size=int(family_size),
        alpha=float(alpha),
        test=test,
        reasons=reasons,
    )


# --------------------------------------------------------------------------
# Per-episode differences
# --------------------------------------------------------------------------


def episode_differences(
    indicator,
    outcome,
    *,
    merge_gap: Union[int, str, pd.Timedelta],
    window: Optional[int] = None,
    min_neighbours: int = 1,
) -> pd.DataFrame:
    """Per-episode difference: active mean minus neighbouring inactive mean.

    The neighbouring windows are the ``window`` bars immediately before the
    episode's first bar and after its last bar, keeping only bars that are
    inactive and outside every episode span (so the inactive gap inside a
    merged episode, and bars of other episodes, are never neighbours).
    Missing (NaN) outcomes are skipped.

    Args:
        indicator: Boolean calendar.
        outcome: Outcome per bar, same length.
        merge_gap: See :func:`episodes`.
        window: Bars on each side; default is the episode's own span.
        min_neighbours: An episode with fewer usable neighbouring bars, or no
            usable active bar, gets ``difference`` NaN and ``used`` False.

    Returns:
        One row per episode with ``active_mean``, ``neighbour_mean``,
        ``difference``, ``n_active_used``, ``n_neighbours``, ``used``.
    """
    active = _as_indicator(indicator)
    y = (
        outcome.to_numpy(dtype=float)
        if isinstance(outcome, pd.Series)
        else np.asarray(outcome, dtype=float)
    )
    if y.shape != active.shape:
        raise ValueError("indicator and outcome must have the same length")
    if window is not None and int(window) < 1:
        raise ValueError("window must be at least 1")
    eps = episodes(indicator, merge_gap)
    in_span = np.zeros(len(active), dtype=bool)
    for ep in eps:
        in_span[ep.start : ep.end + 1] = True
    eligible = ~active & ~in_span & np.isfinite(y)
    n = len(active)
    rows = []
    for k, ep in enumerate(eps):
        w = int(window) if window is not None else ep.n_bars
        span = np.arange(ep.start, ep.end + 1)
        on = span[active[span] & np.isfinite(y[span])]
        before = np.arange(max(0, ep.start - w), ep.start)
        after = np.arange(ep.end + 1, min(n, ep.end + 1 + w))
        nb = np.concatenate((before, after))
        nb = nb[eligible[nb]]
        used = len(on) > 0 and len(nb) >= max(1, int(min_neighbours))
        a_mean = float(y[on].mean()) if len(on) else float("nan")
        n_mean = float(y[nb].mean()) if len(nb) else float("nan")
        rows.append(
            {
                "episode": k,
                "start": ep.start_label,
                "end": ep.end_label,
                "active_mean": a_mean,
                "neighbour_mean": n_mean,
                "difference": a_mean - n_mean if used else float("nan"),
                "n_active_used": int(len(on)),
                "n_neighbours": int(len(nb)),
                "used": bool(used),
            }
        )
    return pd.DataFrame(
        rows,
        columns=[
            "episode",
            "start",
            "end",
            "active_mean",
            "neighbour_mean",
            "difference",
            "n_active_used",
            "n_neighbours",
            "used",
        ],
    )


# --------------------------------------------------------------------------
# Sign patterns
# --------------------------------------------------------------------------


def _as_differences(differences) -> np.ndarray:
    d = np.asarray(differences, dtype=float).ravel()
    d = d[np.isfinite(d)]
    if len(d) == 0:
        raise ValueError("no finite per-episode differences")
    return d


def _pattern_chunks(k: int, rng: Optional[np.random.Generator], n_draws: Optional[int]):
    """Yield (n, k) arrays of +1/-1 sign patterns.

    Enumerated (every pattern once, identity included) when ``k`` is at
    most :data:`MAX_ENUMERATED`; otherwise ``n_draws`` random patterns.
    """
    if k <= MAX_ENUMERATED:
        total = 1 << k
        bits = np.arange(k, dtype=np.int64)
        for lo in range(0, total, _CHUNK):
            codes = np.arange(lo, min(total, lo + _CHUNK), dtype=np.int64)
            flips = (codes[:, None] >> bits) & 1
            yield 1.0 - 2.0 * flips
    else:
        if rng is None or n_draws is None:
            raise ValueError(
                f"more than {MAX_ENUMERATED} episodes needs rng and n_draws"
            )
        remaining = int(n_draws)
        while remaining > 0:
            size = min(_CHUNK, remaining)
            yield rng.choice(np.array([-1.0, 1.0]), size=(size, k))
            remaining -= size


def sign_flip_test(
    differences,
    *,
    alternative: str = "two-sided",
    rng: Optional[np.random.Generator] = None,
    n_draws: int = 99999,
) -> SignFlipResult:
    """Sign-flip test of the mean per-episode difference.

    Null: each difference is symmetric about zero, independently across
    episodes. Exact by enumeration of all ``2**K`` patterns when
    ``K <= 20`` (``rng`` unused); otherwise ``n_draws`` random patterns
    and ``p = (k + 1) / (n_draws + 1)``. Two-sided extremeness is
    ``|mean|`` (the null is centred at zero). Ties count as extreme.

    Args:
        differences: Per-episode differences (NaN entries are dropped), e.g.
            the ``difference`` column of :func:`episode_differences`.
    """
    if alternative not in ALTERNATIVES:
        raise ValueError(f"alternative must be one of {ALTERNATIVES}")
    d = _as_differences(differences)
    k = len(d)
    observed = float(d.mean())
    tol = 1e-12 * (float(np.abs(d).sum()) + 1.0)
    count = 0
    seen = 0
    for signs in _pattern_chunks(k, rng, n_draws):
        stats = signs @ d / k
        if alternative == "greater":
            count += int(np.sum(stats >= observed - tol))
        elif alternative == "less":
            count += int(np.sum(stats <= observed + tol))
        else:
            count += int(np.sum(np.abs(stats) >= abs(observed) - tol))
        seen += len(stats)
    exact = k <= MAX_ENUMERATED
    p = count / seen if exact else (count + 1) / (seen + 1)
    return SignFlipResult(
        statistic=observed,
        p_value=float(min(1.0, p)),
        p_min=sign_flip_p_min(k, alternative, n_draws),
        n_episodes=k,
        n_null=int(seen),
        exact_enumeration=exact,
        alternative=alternative,
        differences=d,
    )


def wild_cluster_interval(
    differences,
    *,
    level: float = 0.95,
    rng: Optional[np.random.Generator] = None,
    n_draws: int = 99999,
) -> ClusterInterval:
    """Equal-tailed interval for the mean difference, clustered by episode.

    Restricted wild cluster bootstrap with Rademacher weights, inverted over
    the null value ``mu0``: ``mu0`` is inside the interval unless the
    one-sided test of ``mean(d - mu0) = 0`` rejects at ``(1 - level) / 2``.
    Flipping the set ``F`` of episodes raises the bootstrap statistic above
    the observed one exactly when ``mean(d[F]) <= mu0``, so the bounds are
    order statistics of the subset means: the ``j``-th smallest and
    ``j``-th largest with ``j = floor(a * N)``, ``a = (1 - level) / 2``,
    ``N`` the number of patterns (``2**K`` enumerated, or
    ``n_draws + 1`` with the identity counted). If ``j`` is 0 the bound is
    infinite (too few episodes for this level).
    """
    if not 0 < level < 1:
        raise ValueError("level must lie in (0, 1)")
    d = _as_differences(differences)
    k = len(d)
    total = float(d.sum())
    means = []
    n_identity = 0
    for signs in _pattern_chunks(k, rng, n_draws):
        n_flip = np.sum(signs < 0, axis=1)
        keep = n_flip > 0
        n_identity += int(np.sum(~keep))
        if not keep.any():
            continue
        flipped_sum = (total - signs[keep] @ d) / 2.0
        means.append(flipped_sum / n_flip[keep])
    subset_means = np.sort(np.concatenate(means)) if means else np.empty(0)
    exact = k <= MAX_ENUMERATED
    if exact:
        n_patterns = 1 << k
        lows = highs = subset_means
    else:
        # The observed pattern is counted once (the "+ 1"); a drawn identity
        # pattern is always extreme, so it widens both tails.
        n_patterns = int(n_draws) + 1
        extra = n_identity
        lows = np.concatenate((np.full(extra, -np.inf), subset_means))
        highs = np.concatenate((subset_means, np.full(extra, np.inf)))
    j = int(np.floor((1.0 - level) / 2.0 * n_patterns + 1e-9))
    if 1 <= j <= len(lows):
        low = float(lows[j - 1])
        high = float(highs[len(highs) - j])
        bounded = bool(np.isfinite(low) and np.isfinite(high))
    else:
        low, high, bounded = float("-inf"), float("inf"), False
    return ClusterInterval(
        estimate=float(d.mean()),
        ci_low=low,
        ci_high=high,
        level=float(level),
        n_episodes=k,
        n_patterns=n_patterns,
        exact_enumeration=exact,
        bounded=bounded,
    )
