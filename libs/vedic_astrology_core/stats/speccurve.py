"""Specification curves: one estimate per defensible analytic choice.

A result that holds for one orb, one window and one catalogue but not for
its neighbours is a forking path, not a finding (Simonsohn, Simmons and
Nelson 2020, *Nature Human Behaviour* 4, 1208-1214; Steegen et al. 2016).
:func:`specification_curve` runs an estimator over every cell of a declared
grid of choices (orb, window, catalogue, declustering method, ayanamsa, node
model, house system, ...) and returns the curve sorted by estimate, the
share of cells whose interval excludes the null, and a joint test of the
median estimate: per draw the *outcome* is rotated once by a random circular
shift and the whole curve is recomputed with that same shift, so the
dependence between cells is kept.

The estimator is called as ``estimator(spec, shift)`` where ``spec`` maps
each grid key to one value and ``shift`` is the circular offset applied to
the outcome (0 for the observed data). It returns a dict with at least
``estimate``, ``ci_low`` and ``ci_high``.
"""

import itertools
from dataclasses import dataclass
from typing import Callable, Dict, List

import numpy as np
import pandas as pd

from .nulls import _check_rng, circular_shift_offsets


@dataclass
class SpecCurve:
    """Sorted specification curve and its joint circular-shift test."""

    frame: pd.DataFrame
    share_excluding_null: float
    median_estimate: float
    p_median: float
    null_medians: np.ndarray
    null_share: np.ndarray
    p_share: float
    n_draws: int
    null_value: float


def _cells(grid: Dict[str, List]) -> List[Dict]:
    keys = list(grid)
    return [dict(zip(keys, vals)) for vals in itertools.product(*grid.values())]


def _median(values, log_scale: bool) -> float:
    v = np.asarray(values, dtype=float)
    v = v[np.isfinite(v) & ((v > 0) if log_scale else True)]
    if not len(v):
        return float("nan")
    return float(np.exp(np.median(np.log(v)))) if log_scale else float(np.median(v))


def specification_curve(
    estimator: Callable[[Dict, int], Dict],
    grid: Dict[str, List],
    rng: np.random.Generator,
    n: int,
    min_shift: int = 1,
    n_draws: int = 200,
    null_value: float = 1.0,
    alternative: str = "greater",
    log_scale: bool = True,
) -> SpecCurve:
    """Run ``estimator`` over every cell of ``grid`` and test the median.

    Args:
        estimator: ``estimator(spec, shift) -> {"estimate", "ci_low",
            "ci_high", ...}``; extra keys are kept as columns.
        grid: Choice name to list of values; the curve has one row per
            element of the Cartesian product.
        rng: ``np.random.default_rng(seed)``.
        n: Length of the outcome series (for drawing shifts).
        min_shift: Smallest circular shift of the outcome.
        n_draws: Joint null draws; each recomputes the whole curve.
        null_value: Estimate under no effect (1 for a rate ratio).
        alternative: ``"greater"``, ``"less"`` or ``"two-sided"`` for the
            median (two-sided compares distances from ``null_value``, on the
            log scale when ``log_scale``).
        log_scale: Summarise estimates on the log scale (ratios).

    Raises:
        ValueError: If the grid is empty.
    """
    _check_rng(rng)
    if not grid or any(len(v) == 0 for v in grid.values()):
        raise ValueError("grid must declare at least one value per choice")
    cells = _cells(grid)
    rows = []
    for spec in cells:
        out = dict(spec)
        out.update(estimator(spec, 0))
        rows.append(out)
    frame = pd.DataFrame(rows)
    excl = (frame["ci_low"] > null_value) | (frame["ci_high"] < null_value)
    frame["excludes_null"] = excl.to_numpy()
    frame = frame.sort_values("estimate", kind="mergesort").reset_index(drop=True)
    frame["rank"] = np.arange(1, len(frame) + 1)
    obs_med = _median(frame["estimate"], log_scale)
    obs_share = float(frame["excludes_null"].mean())

    offsets = circular_shift_offsets(n, min_shift, n_draws, rng) if n_draws else []
    null_med = np.empty(len(offsets))
    null_share = np.empty(len(offsets))
    for i, k in enumerate(offsets):
        res = [estimator(spec, int(k)) for spec in cells]
        null_med[i] = _median([r["estimate"] for r in res], log_scale)
        null_share[i] = np.mean(
            [(r["ci_low"] > null_value) or (r["ci_high"] < null_value) for r in res]
        )

    def tr(v):
        v = np.asarray(v, dtype=float)
        return np.log(v) - np.log(null_value) if log_scale else v - null_value

    ok = np.isfinite(null_med)
    if alternative == "greater":
        hits = tr(null_med[ok]) >= tr(obs_med)
    elif alternative == "less":
        hits = tr(null_med[ok]) <= tr(obs_med)
    else:
        hits = np.abs(tr(null_med[ok])) >= abs(tr(obs_med))
    p_med = float((1 + hits.sum()) / (ok.sum() + 1))
    p_share = float((1 + np.sum(null_share >= obs_share)) / (len(null_share) + 1))
    return SpecCurve(
        frame=frame,
        share_excluding_null=obs_share,
        median_estimate=obs_med,
        p_median=p_med,
        null_medians=null_med,
        null_share=null_share,
        p_share=p_share,
        n_draws=int(len(offsets)),
        null_value=float(null_value),
    )
