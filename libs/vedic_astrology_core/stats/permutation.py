"""Permutation test of any statistic against an autocorrelation-preserving null.

The p-value is ``(n_extreme + 1) / (n_perm + 1)`` (Phipson and Smyth 2010),
so it is never zero and never below ``p_min = 1 / (n_perm + 1)``. The null is
one of:

* ``"circular_shift"``: rotate the indicator ``x`` (needs ``min_shift``). The
  admissible offsets are ``[min_shift, n - min_shift]``. When there are no
  more of them than ``n_perm``, every one is used once (exact enumeration;
  ``n_perm`` in the result is then the number of admissible offsets);
  otherwise ``n_perm`` distinct offsets are drawn without replacement.
* ``"block_bootstrap"``: stationary block bootstrap of the outcome ``y``
  (needs ``mean_block``).
* ``"phase"``: phase-randomise a continuous indicator ``x``.

The result carries the effect (observed minus null mean), the effect in null
standard deviations, a percentile confidence interval for the statistic
from a paired stationary block bootstrap of ``(x, y)``, and the null
statistics themselves (for plotting).
"""

from dataclasses import dataclass, field
from typing import Callable, Optional

import numpy as np

from .nulls import (
    circular_shift_offsets,
    n_admissible_shifts,
    phase_randomization,
    stationary_block_bootstrap,
    stationary_bootstrap_indices,
)

NULLS = ("circular_shift", "block_bootstrap", "phase")
ALTERNATIVES = ("greater", "less", "two-sided")


@dataclass
class PermutationResult:
    """Outcome of :func:`permutation_test`."""

    observed: float
    p_value: float
    effect: float
    effect_z: float
    ci_low: float
    ci_high: float
    null_mean: float
    null_sd: float
    n_perm: int
    null: str
    alternative: str
    null_stats: np.ndarray = field(default=None, repr=False)
    p_min: float = float("nan")
    exact_enumeration: bool = False
    n_admissible: Optional[int] = None


def empirical_p_value(
    observed: float, null_stats: np.ndarray, alternative: str = "greater"
) -> float:
    """Return ``(n_extreme + 1) / (n + 1)`` for the given alternative.

    Two-sided extremeness is distance from the null mean.
    """
    null_stats = np.asarray(null_stats, dtype=float)
    n = len(null_stats)
    if alternative == "greater":
        n_ext = np.sum(null_stats >= observed)
    elif alternative == "less":
        n_ext = np.sum(null_stats <= observed)
    elif alternative == "two-sided":
        centre = null_stats.mean()
        n_ext = np.sum(np.abs(null_stats - centre) >= abs(observed - centre))
    else:
        raise ValueError(f"alternative must be one of {ALTERNATIVES}")
    return float((n_ext + 1) / (n + 1))


def permutation_test(
    statistic: Callable[[np.ndarray, np.ndarray], float],
    x,
    y,
    *,
    rng: np.random.Generator,
    null: str = "circular_shift",
    n_perm: int = 10000,
    alternative: str = "greater",
    min_shift: Optional[int] = None,
    mean_block: Optional[float] = None,
    ci_level: float = 0.95,
    n_boot: int = 1000,
) -> PermutationResult:
    """Test ``statistic(x, y)`` against surrogates from :mod:`.nulls`.

    Args:
        statistic: Function of the indicator ``x`` and outcome ``y``.
        x: Indicator series (same length as ``y``).
        y: Outcome series.
        rng: ``np.random.default_rng(seed)``.
        null: One of :data:`NULLS`.
        n_perm: Number of null surrogates. For the circular-shift null it is
            an upper bound: when the admissible offsets are fewer, all of
            them are used (exact test) and the result records how many.
        alternative: "greater", "less" or "two-sided".
        min_shift: Minimum rotation for the circular-shift null.
        mean_block: Mean block length for the block bootstrap; also used for
            the confidence interval (default ``n ** (1/3)``).
        ci_level: Confidence level of the bootstrap interval.
        n_boot: Bootstrap resamples for the interval (0 disables it).
    """
    if null not in NULLS:
        raise ValueError(f"null must be one of {NULLS}, got {null!r}")
    if alternative not in ALTERNATIVES:
        raise ValueError(f"alternative must be one of {ALTERNATIVES}")
    x = np.asarray(x)
    y = np.asarray(y)
    if len(x) != len(y):
        raise ValueError("x and y must have the same length")
    n = len(x)
    if null == "circular_shift" and min_shift is None:
        raise ValueError("circular_shift null needs min_shift")
    block = float(mean_block) if mean_block else max(1.0, n ** (1.0 / 3.0))

    observed = float(statistic(x, y))
    n_admissible: Optional[int] = None
    if null == "circular_shift":
        offsets = circular_shift_offsets(n, min_shift, n_perm, rng)
        n_admissible = n_admissible_shifts(n, min_shift)
        null_stats = np.array(
            [statistic(np.roll(x, int(k)), y) for k in offsets], dtype=float
        )
    else:
        null_stats = np.empty(n_perm, dtype=float)
        for i in range(n_perm):
            if null == "block_bootstrap":
                surrogate = stationary_block_bootstrap(y, block, rng)
                null_stats[i] = statistic(x, surrogate)
            else:
                null_stats[i] = statistic(phase_randomization(x, rng), y)
    n_used = len(null_stats)

    null_mean = float(np.mean(null_stats))
    null_sd = float(np.std(null_stats, ddof=1)) if n_used > 1 else float("nan")
    effect = observed - null_mean
    effect_z = effect / null_sd if null_sd and null_sd > 0 else float("nan")

    ci_low = ci_high = float("nan")
    if n_boot:
        boots = np.empty(n_boot, dtype=float)
        for b in range(n_boot):
            idx = stationary_bootstrap_indices(n, block, rng)
            boots[b] = statistic(x[idx], y[idx])
        tail = (1.0 - ci_level) / 2.0 * 100.0
        bounds = np.nanpercentile(boots, [tail, 100 - tail])
        ci_low, ci_high = float(bounds[0]), float(bounds[1])

    return PermutationResult(
        observed=observed,
        p_value=empirical_p_value(observed, null_stats, alternative),
        effect=float(effect),
        effect_z=float(effect_z),
        ci_low=ci_low,
        ci_high=ci_high,
        null_mean=null_mean,
        null_sd=null_sd,
        n_perm=int(n_used),
        null=null,
        alternative=alternative,
        null_stats=null_stats,
        p_min=1.0 / (n_used + 1),
        exact_enumeration=n_admissible is not None and n_used == n_admissible,
        n_admissible=n_admissible,
    )
