"""Exclusion by effect removal and the upper limit X (ADR-008 section 2, H-2).

Work package WP-86. Closes S-01 (exclusion and X95 invalid for skewed
outcomes), S-07 (binomial rate-ratio interval used for exclusion), the X part
of S-06 (one statistic) and G-11 (an explicit ``unbounded`` record).

Why (section 2.1). No method bounds the **mean** of an unknown skewed
distribution from 8 to 20 values. So the effect is not estimated and then
bounded; it is **removed**. To test H0 "the effect is at least r" under the
plan's effect model, an effect of size r is taken out of the active bars and
the block sign-flip test of :mod:`.blocks` (the primary test, same blocks,
same weights, same statistic T) is run for "no effect" in the other
direction. If the true effect is exactly r and steady, the adjusted data have
no effect, so the test is exact for the same reason the support test is
exact: swapping active and control inside a balanced block leaves the joint
distribution unchanged. Skew and rare events do not enter.

Effect models (printed on the card, :data:`EFFECT_MODELS`):

============  ==========================  ===================================
outcome type  effect model                removal of an effect of size r
============  ==========================  ===================================
continuous    constant shift              subtract r from every active bar
log_ratio     constant ratio (log scale)  subtract log r from every active bar
events        constant rate ratio         keep each active-side event with
                                          probability 1/r (thinning)
flags         constant risk ratio         keep each active-side "yes" with
                                          probability 1/r (thinning)
============  ==========================  ===================================

A claim in the "less" direction is the mirror image: an effect of size r
means a shift of -r (a ratio of 1/r), removed by adding r to the active bars
(by thinning the **control** side with probability 1/r), and the test runs
against "greater". A claim with side ``two-sided`` (``either``) is excluded
only when both one-sided removals reject (the larger p decides, TOST).

Details that make it one deterministic procedure (section 2.2):

* **Thinning is repeated** :data:`N_THIN` (199) times. Each event of the
  plan's counting unit on a used block gets one uniform number per
  repetition, drawn once from the test's own ``thinning`` stream (ADR-008
  3.5) in bar order. An event is kept when its number is below its keep
  probability, so the kept sets are nested as r grows. The reported p is
  twice the median of the 199 p-values, capped at 1 (quantile aggregation at
  one half, Meinshausen, Meier and Buehlmann 2009): valid under any
  dependence between the repetitions, conservative.
* **Unequal exposure** inside a block (active and control sides of different
  length) is first equalised by thinning the longer side's events with
  probability ``short / long``, using the same uniform numbers. The block
  difference is then ``(kept active - kept control) / min(n_A, n_C)``. Under
  ADR-008 Amendment A1 every block is equal-size and this step keeps every
  event, so ``d_k`` is the primary test's block difference.
* **X95** is the smallest r whose exclusion p is at or below 0.05, found on
  the plan's grid and refined by bisection between the last accepted and the
  first rejected grid point (the upper end of the final bracket is
  reported, which is conservative). **X-strict** is the same at the test's
  family threshold ``a_test``. The exclusion p never increases as r grows
  (X10), which is what makes the search well defined.
* **Two-sided intervals** are the pair of one-sided limits of this inversion
  (:meth:`EffectRemoval.interval`). The binomial rate-ratio interval of
  :mod:`.rates` is not used here or on any card (S-07).
* **Minimum-information rule.** I is the number of used blocks whose
  difference is not zero after removal at r = SESOI (the lower median over
  the thinning repetitions for events and flags). A limit at level a is
  printed only if ``K_eff >= 8`` and ``I >= ceil(log2(1 / a))`` (5 for X95,
  10 at 0.001). Otherwise the record is ``unbounded: true`` with no number
  (G-11), and verdict E is impossible.

Detrended outcomes (ADR-008 Amendment A2). Daily and hourly continuous and
log-ratio outcomes are detrended by a centred running mean before the block
test (core/stats/season.py centred_detrend). A steady effect r on the active
bars then shows in block k as ``r * c_k``, with ``c_k`` the block difference
of the detrended active-bar indicator (``effect_shape``,
:func:`shape_contrasts`); removal subtracts exactly that, so the exactness
argument above is unchanged. Events and flags are not detrended (thinning
needs whole counts); measured with A2 blocks on daily new-moon and eclipse
calendars, a doubling event rate holds size without it.

What stays outside the guarantee (section 2.3): the guarantee is for a
**steady** effect. :func:`card_lines` gives the two fixed sentences every card
with an X prints, with ``f = 1 - 0.05 ** (1 / K)`` (:func:`not_addressed_share`).

Deprecated (not imported by ``core/validity``, checked by a test):
:func:`.equivalence.episode_equivalence` and
:func:`.equivalence.upper_limit_episodes` (S-01: they assume symmetric
episode differences), listed in :data:`DEPRECATED`.

Nothing here starts a thread (G-13). Every function is deterministic given
its inputs, the thinning generator and the sign-flip seed.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

import numpy as np

from . import blocks as _blocks
from .blocks import BlockDesign

#: Thinning repetitions (section 2.2). Changed only by amending ADR-008.
N_THIN = 199
#: Level of X95.
X95_ALPHA = 0.05
#: Gate G4 floor for printing any limit (same as the blocks module).
MIN_K_EFF = _blocks.MIN_K_EFF
#: Bisection steps between two grid points.
BISECT_STEPS = 40

OUTCOME_TYPES = _blocks.OUTCOME_TYPES
SIDES = _blocks.ALTERNATIVES
THINNED_TYPES = ("events", "flags")
RATIO_TYPES = ("log_ratio", "events", "flags")

#: The effect model printed on the card, per outcome type (section 2.2).
EFFECT_MODELS: Dict[str, str] = {
    "continuous": "constant shift in the outcome's unit",
    "log_ratio": "constant ratio, tested on the log scale",
    "events": "constant rate ratio",
    "flags": "constant risk ratio",
}
#: Scale of r, of X and of the SESOI, per outcome type.
SCALES: Dict[str, str] = {
    "continuous": "difference",
    "log_ratio": "ratio",
    "events": "rate_ratio",
    "flags": "risk_ratio",
}

#: Functions withdrawn by ADR-008 S-01; ``core/validity`` must not import them.
DEPRECATED: Tuple[str, ...] = (
    "vedic_astrology_core.stats.equivalence.episode_equivalence",
    "vedic_astrology_core.stats.equivalence.upper_limit_episodes",
)

#: Reasons a limit is unbounded.
REASON_FEW_BLOCKS = "k_eff_below_8"
REASON_LOW_INFORMATION = "too_few_informative_blocks"
REASON_NOT_REACHED = "not_rejected_on_grid"
REASON_NO_SESOI = "no_sesoi"


# --------------------------------------------------------------------------
# Small rules
# --------------------------------------------------------------------------


def min_informative(a: float) -> int:
    """Informative blocks needed for a limit at level ``a``: ``ceil(log2(1 / a))``."""
    if not 0.0 < float(a) < 1.0:
        raise ValueError("a must lie in (0, 1)")
    v = math.log2(1.0 / float(a))
    r = round(v)
    return int(r) if abs(v - r) < 1e-12 else int(math.ceil(v))


def can_limit(k_eff: float, informative: int, a: float) -> bool:
    """Minimum-information rule of section 2.2."""
    return float(k_eff) >= MIN_K_EFF and int(informative) >= min_informative(a)


def not_addressed_share(k: int, a: float = X95_ALPHA) -> float:
    """``f = 1 - a ** (1 / K)``: share of episodes below which an effect is not addressed."""
    k = int(k)
    if k < 1:
        raise ValueError("K must be at least 1")
    return float(1.0 - float(a) ** (1.0 / k))


def _check_type(outcome_type) -> str:
    if outcome_type not in OUTCOME_TYPES:
        raise ValueError(f"outcome_type must be one of {OUTCOME_TYPES}")
    return outcome_type


def _check_side(side) -> str:
    if side not in SIDES:
        raise ValueError(
            f"side must be one of {SIDES} (the claimed direction; there is no "
            "default side, use blocks.alternative_for(direction))"
        )
    return side


def _check_magnitude(m: float, outcome_type: str) -> float:
    m = float(m)
    if not math.isfinite(m):
        raise ValueError("effect size must be finite")
    if outcome_type in RATIO_TYPES:
        if m <= 1.0:
            raise ValueError(f"{outcome_type}: an effect size is a ratio above 1, got {m}")
    elif m <= 0.0:
        raise ValueError(f"continuous: an effect size is positive, got {m}")
    return m


def _check_grid(grid, outcome_type: str) -> np.ndarray:
    g = np.asarray(grid, dtype=float).ravel()
    if len(g) == 0:
        raise ValueError("the plan's grid for X is empty")
    if not np.isfinite(g).all() or (np.diff(g) <= 0).any():
        raise ValueError("the grid must be finite and strictly increasing")
    _check_magnitude(g[0], outcome_type)
    return g


# --------------------------------------------------------------------------
# Sign-flip p for many rows at once (same test as blocks.weighted_sign_flip)
# --------------------------------------------------------------------------


def _subset_sums(x: np.ndarray) -> np.ndarray:
    """All 2**h subset sums of the columns of ``x`` (rows x 2**h)."""
    h = x.shape[1]
    codes = np.arange(1 << h, dtype=np.int64)
    bits = ((codes[:, None] >> np.arange(h, dtype=np.int64)) & 1).astype(float)
    return x @ bits.T


def sign_flip_p_rows(
    d,
    w,
    alternative: str,
    *,
    signflip_seed: Optional[int] = None,
    n_draws: int = _blocks.DEFAULT_DRAWS,
) -> np.ndarray:
    """One-sided sign-flip p-value of every row of ``d`` (rows x K), weights ``w``.

    The same test as :func:`.blocks.weighted_sign_flip` (ties count as
    extreme, same tolerance, same Monte Carlo draws for the same seed),
    computed for many rows at once. Exact for ``K <= 20`` by splitting the
    blocks into two halves and counting pattern pairs; above that ``n_draws``
    sign patterns from ``default_rng(signflip_seed)``, the **same** patterns
    for every row and every r, so the p-value is monotone in r.
    """
    if alternative not in ("less", "greater"):
        raise ValueError("exclusion uses one-sided tests only")
    d = np.atleast_2d(np.asarray(d, dtype=float))
    w = np.asarray(w, dtype=float).ravel()
    rows, k = d.shape
    if k != len(w):
        raise ValueError("d and w disagree on the number of blocks")
    if k == 0:
        return np.ones(rows)
    if not np.isfinite(d).all() or not np.isfinite(w).all() or (w <= 0).any():
        raise ValueError("d must be finite and w positive")
    wd = d * w
    tol = 1e-12 * (np.abs(wd).sum(axis=1) + 1.0)
    if k <= _blocks.MAX_ENUMERATED:
        # Flipping the set F gives T_F = O - 2 S_F with S_F = sum over F of wd.
        # "less": T_F <= O + tol  <=>  S_F >= -tol / 2.
        # "greater": T_F >= O - tol  <=>  S_F <= tol / 2.
        h = k // 2
        a_sums = _subset_sums(wd[:, :h])
        b_sums = np.sort(_subset_sums(wd[:, h:]), axis=1)
        nb = b_sums.shape[1]
        out = np.empty(rows)
        for i in range(rows):
            if alternative == "less":
                cut = -tol[i] / 2.0 - a_sums[i]
                cnt = nb - np.searchsorted(b_sums[i], cut, side="left")
            else:
                cut = tol[i] / 2.0 - a_sums[i]
                cnt = np.searchsorted(b_sums[i], cut, side="right")
            out[i] = float(cnt.sum()) / float(1 << k)
        return np.minimum(out, 1.0)
    if signflip_seed is None:
        raise ValueError(
            f"more than {_blocks.MAX_ENUMERATED} used blocks needs signflip_seed "
            "(the test's own 'signflip' stream, ADR-008 3.5)"
        )
    rng = np.random.default_rng(int(signflip_seed))
    remaining = int(n_draws)
    if remaining < 1:
        raise ValueError("n_draws must be at least 1")
    observed = wd.sum(axis=1)
    count = np.zeros(rows, dtype=np.int64)
    seen = 0
    while remaining > 0:
        size = min(_blocks._CHUNK, remaining)
        signs = rng.choice(np.array([-1.0, 1.0]), size=(size, k))
        stats = signs @ wd.T  # size x rows
        if alternative == "less":
            count += np.sum(stats <= (observed + tol)[None, :], axis=0)
        else:
            count += np.sum(stats >= (observed - tol)[None, :], axis=0)
        seen += size
        remaining -= size
    return np.minimum((count + 1.0) / (seen + 1.0), 1.0)


# --------------------------------------------------------------------------
# Effect removal
# --------------------------------------------------------------------------


def _raw_shift(r: float, outcome_type: str) -> float:
    if outcome_type == "log_ratio":
        if not r > 0:
            raise ValueError("a ratio must be positive")
        return math.log(r)
    return r


def shift_active(design: BlockDesign, outcome, r: float, *, outcome_type: str,
                 effect_shape=None) -> np.ndarray:
    """Outcome with an effect of raw size ``r`` removed from the active bars.

    ``continuous``: subtract ``r``; ``log_ratio``: subtract ``log r`` (r a
    ratio). Bars outside the used blocks are unchanged. Running
    :func:`.blocks.primary_test` on the result gives the exclusion p-value of
    :class:`EffectRemoval` (tested).

    With ``effect_shape`` (a detrended outcome, Amendment A2) the removed
    effect is ``r`` times the shape on every bar: what a steady effect on the
    active bars becomes after the detrending (core/stats/season.py
    detrended_effect_shape).
    """
    _check_type(outcome_type)
    if outcome_type in THINNED_TYPES:
        raise ValueError("events and flags are thinned, not shifted")
    y = np.array(outcome, dtype=float, copy=True)
    s = _raw_shift(float(r), outcome_type)
    if effect_shape is not None:
        h = _check_shape(effect_shape, design.n_bars)
        fin = np.isfinite(h)
        y[fin] = y[fin] - s * h[fin]
        return y
    for b in design.used_blocks:
        y[b.active] = y[b.active] - s
    return y


def _check_shape(effect_shape, n: int) -> np.ndarray:
    h = np.asarray(effect_shape, dtype=float).ravel()
    if len(h) != n:
        raise ValueError(f"effect_shape must have one value per bar ({n}), got {len(h)}")
    return h


def shape_contrasts(design: BlockDesign, effect_shape) -> np.ndarray:
    """Per used block: active mean minus control mean of the effect shape.

    1 for every block without detrending. A steady raw effect r shows in
    block k as ``r * c_k``; exclusion needs every ``c_k > 0`` (the detrending
    window must be long enough that an active run is not absorbed by its own
    baseline). Reads the calendar-derived shape only, so the pipeline checks
    it before any outcome is read.
    """
    h = _check_shape(effect_shape, design.n_bars)
    return _blocks.block_differences(design, h, outcome_type="continuous").d


class EffectRemoval:
    """The block data of one test, ready for effect removal at any r.

    Built once per test: the blocks (calendar only), the outcome, and for
    events and flags the thinning uniforms (one per event and repetition,
    drawn once in bar order from ``thinning_rng``). Every p-value at every r
    reuses them, which makes the kept sets nested and the p-value monotone.

    Args:
        design: From :func:`.blocks.build_blocks` or
            :func:`.blocks.design_from_windows`, the same design the primary
            test uses.
        outcome: One value per bar, as for :func:`.blocks.primary_test`
            (``events``: counts of the plan's counting unit; ``flags``: 0/1).
        outcome_type: One of :data:`OUTCOME_TYPES`.
        thinning_rng: Required for ``events`` and ``flags``: the test's
            ``thinning`` stream (``family.stream_rng(plan_seed, test_id,
            "thinning")``).
        signflip_seed: Required above 20 used blocks: the test's
            ``signflip`` seed (``family.stream_seed(..., "signflip")``).
        n_thin: Thinning repetitions (199; other values for tests only).
        n_draws: Monte Carlo sign patterns above 20 used blocks.
        effect_shape: ``continuous`` and ``log_ratio`` only: per bar, what a
            steady effect of size 1 on the active bars becomes after the
            outcome's detrending (Amendment A2; core/stats/season.py
            detrended_effect_shape). Removing an effect r then subtracts
            ``r * c_k`` from block k's difference (:func:`shape_contrasts`),
            so the removed effect is the one the detrended data carry. None:
            ``c_k = 1`` (no detrending). Every ``c_k`` must be positive.
        raw: Optional outcome before baselines and detrending, as for
            :func:`.blocks.primary_test`: a block whose raw values are all
            equal starts from ``d_k = 0`` (CALIBRATION-FIX).
    """

    def __init__(
        self,
        design: BlockDesign,
        outcome,
        *,
        outcome_type: str,
        thinning_rng: Optional[np.random.Generator] = None,
        signflip_seed: Optional[int] = None,
        n_thin: int = N_THIN,
        n_draws: int = _blocks.DEFAULT_DRAWS,
        effect_shape=None,
        raw=None,
    ):
        self.design = design
        self.outcome_type = _check_type(outcome_type)
        self.signflip_seed = signflip_seed
        self.n_draws = int(n_draws)
        # Validates the outcome exactly as the primary test does.
        diffs = _blocks.block_differences(design, outcome, outcome_type=outcome_type, raw=raw)
        self.w = diffs.w
        self.k = len(self.w)
        self.k_eff = float(design.k_eff)
        self.n_used = int(design.n_used)
        self.d0 = diffs.d
        self.thinned = outcome_type in THINNED_TYPES
        self.n_thin = 1
        self.c = np.ones(self.k)
        if effect_shape is not None:
            if self.thinned:
                raise ValueError("events and flags are not detrended; effect_shape is for shifts only")
            self.c = shape_contrasts(design, effect_shape)
            if self.k and not (np.isfinite(self.c).all() and (self.c > 0).all()):
                raise ValueError(
                    "the detrended effect shape is not positive in every used block: "
                    "the detrending window is too short for the active runs"
                )
        if not self.thinned:
            return
        if int(n_thin) < 1:
            raise ValueError("n_thin must be at least 1")
        self.n_thin = int(n_thin)
        if not isinstance(thinning_rng, np.random.Generator):
            raise ValueError(
                "events and flags need thinning_rng (the test's own 'thinning' "
                "stream, ADR-008 3.5)"
            )
        y = np.asarray(outcome, dtype=float)
        # Segments: (block, side) in block order, active side first.
        seg_bars: List[np.ndarray] = []
        n_a, n_c = [], []
        for b in design.used_blocks:
            for bars in (b.active, b.control):
                c = y[bars]
                if not np.all(c == np.round(c)):
                    raise ValueError(f"{outcome_type} outcome must be whole counts per bar")
                seg_bars.append(np.asarray(bars, dtype=np.int64))
            n_a.append(b.n_active)
            n_c.append(b.n_control)
        self.n_a = np.asarray(n_a, dtype=float)
        self.n_c = np.asarray(n_c, dtype=float)
        self.m = np.minimum(self.n_a, self.n_c)
        self.e_a = self.m / self.n_a
        self.e_c = self.m / self.n_c
        # Event order: bars ascending over the grid, a bar's events together.
        # The uniform numbers are drawn in that order, then grouped by segment.
        n_seg = len(seg_bars)
        all_bars = np.concatenate(seg_bars) if seg_bars else np.zeros(0, dtype=np.int64)
        seg_of_bar = np.repeat(np.arange(n_seg), [len(x) for x in seg_bars])
        order = np.argsort(all_bars, kind="stable")
        counts = y[all_bars[order]].astype(np.int64)
        seg_of_event = np.repeat(seg_of_bar[order], counts)
        self.n_events = int(counts.sum())
        u = thinning_rng.random((self.n_thin, self.n_events))
        by_seg = np.argsort(seg_of_event, kind="stable")
        self._u = u[:, by_seg]
        self._seg = seg_of_event[by_seg]
        self._bounds = np.concatenate(
            ([0], np.cumsum(np.bincount(self._seg, minlength=n_seg)))
        ).astype(np.int64)

    # ---------------------------------------------------------- block rows
    def kept_counts(self, rho: float) -> Tuple[np.ndarray, np.ndarray]:
        """Kept events per repetition and used block on each side at raw ratio ``rho``.

        Active events are kept with probability ``e_A * min(1, 1 / rho)``,
        control events with ``e_C * min(1, rho)`` (``e`` equalises exposure).
        """
        if not self.thinned:
            raise ValueError("kept_counts is for events and flags")
        rho = float(rho)
        if not rho > 0:
            raise ValueError("a ratio must be positive")
        if self.k == 0:
            z = np.zeros((self.n_thin, 0))
            return z, z
        q_seg = np.empty(2 * self.k)
        q_seg[0::2] = self.e_a * min(1.0, 1.0 / rho)
        q_seg[1::2] = self.e_c * min(1.0, rho)
        kept = self._u < q_seg[self._seg][None, :]
        cum = np.concatenate((np.zeros((self.n_thin, 1)), np.cumsum(kept, axis=1)), axis=1)
        per_seg = cum[:, self._bounds[1:]] - cum[:, self._bounds[:-1]]
        return per_seg[:, 0::2], per_seg[:, 1::2]

    def differences(self, r: float) -> np.ndarray:
        """Block differences after removing a raw effect ``r`` (one row per repetition).

        ``r`` is a shift for ``continuous`` and a ratio for the other types.
        """
        if not self.thinned:
            return (self.d0 - _raw_shift(float(r), self.outcome_type) * self.c)[None, :]
        ka, kc = self.kept_counts(r)
        return ka / self.m - kc / self.m

    def p_reps(self, r: float, alternative: str) -> np.ndarray:
        """Sign-flip p of every thinning repetition (one row for shifts)."""
        return sign_flip_p_rows(
            self.differences(r), self.w, alternative,
            signflip_seed=self.signflip_seed, n_draws=self.n_draws,
        )

    def p_value(self, r: float, alternative: str) -> float:
        """p after removing raw effect ``r``; twice the median over repetitions for thinning."""
        p = self.p_reps(r, alternative)
        if not self.thinned:
            return float(p[0])
        return float(min(1.0, 2.0 * np.median(p)))

    def informative(self, r: float) -> int:
        """Used blocks with a non-zero difference after removal at raw ``r``.

        For events and flags the lower median over the repetitions.
        """
        nz = np.count_nonzero(self.differences(r), axis=1)
        return int(np.sort(nz)[(len(nz) - 1) // 2])

    # ------------------------------------------------------- claim scale
    def hypotheses(self, magnitude: float, side: str) -> List[Tuple[float, str]]:
        """Raw effects to remove and the test side for a claim-scale ``magnitude``."""
        side = _check_side(side)
        m = _check_magnitude(magnitude, self.outcome_type)
        up = (m, "less")
        down = (-m if self.outcome_type == "continuous" else 1.0 / m, "greater")
        if side == "greater":
            return [up]
        if side == "less":
            return [down]
        return [up, down]

    def exclusion_p(self, magnitude: float, side: str) -> float:
        """p of H0 "the effect in the claimed direction is at least ``magnitude``".

        ``magnitude`` is on the claim scale (a positive shift, or a ratio above
        1). For ``two-sided`` the larger of the two one-sided p-values.
        """
        return max(self.p_value(r, alt) for r, alt in self.hypotheses(magnitude, side))

    def informative_at(self, magnitude: float, side: str) -> int:
        """I at ``magnitude`` (the smaller over both removals for ``two-sided``)."""
        return min(self.informative(r) for r, _ in self.hypotheses(magnitude, side))

    def search(self, a: float, grid, side: str, steps: int = BISECT_STEPS) -> Tuple[Optional[float], bool]:
        """Smallest magnitude on ``grid`` (refined by bisection) with exclusion p <= ``a``.

        Returns ``(value, at_grid_floor)``; ``(None, False)`` when no grid
        point is rejected.
        """
        side = _check_side(side)
        g = _check_grid(grid, self.outcome_type)
        return _smallest_rejected(lambda m: self.exclusion_p(m, side), g, a, steps)

    def interval(self, a: float, grid, steps: int = BISECT_STEPS) -> Tuple[float, float]:
        """Two-sided interval on the raw scale: the pair of one-sided limits, each at ``a``.

        ``grid`` is on the raw scale (shifts, or ratios), increasing. Upper:
        the smallest raw r rejected by the "less" test after removing r;
        lower: the largest raw r rejected by the "greater" test. A side that
        no grid point rejects is open (``inf`` above; ``-inf`` below, or 0 for
        a ratio).
        """
        g = np.asarray(grid, dtype=float).ravel()
        if len(g) == 0 or not np.isfinite(g).all() or (np.diff(g) <= 0).any():
            raise ValueError("the grid must be finite and strictly increasing")
        ratio = self.outcome_type in RATIO_TYPES
        if ratio and (g <= 0).any():
            raise ValueError("a ratio grid must be positive")
        hi, _ = _smallest_rejected(lambda r: self.p_value(r, "less"), g, a, steps)
        # Mirror the grid so that the search again walks towards larger p-drops.
        if ratio:
            lo, _ = _smallest_rejected(lambda s: self.p_value(1.0 / s, "greater"), 1.0 / g[::-1], a, steps)
            lower = 1.0 / lo if lo is not None else 0.0
        else:
            lo, _ = _smallest_rejected(lambda s: self.p_value(-s, "greater"), -g[::-1], a, steps)
            lower = -lo if lo is not None else float("-inf")
        upper = hi if hi is not None else float("inf")
        return float(lower), float(upper)


def _smallest_rejected(pfun: Callable[[float], float], grid: np.ndarray, a: float, steps: int):
    """Smallest x on the increasing grid with ``pfun(x) <= a`` (pfun non-increasing)."""
    a = float(a)
    prev = None
    for x in grid:
        if pfun(float(x)) <= a:
            if prev is None:
                return float(x), True
            lo, hi = float(prev), float(x)
            for _ in range(int(steps)):
                mid = 0.5 * (lo + hi)
                if mid <= lo or mid >= hi:
                    break
                if pfun(mid) <= a:
                    hi = mid
                else:
                    lo = mid
            return hi, False
        prev = x
    return None, False


# --------------------------------------------------------------------------
# Result records
# --------------------------------------------------------------------------


@dataclass
class LimitRecord:
    """One upper limit (X95 or X-strict) as it goes into the results file.

    ``unbounded`` is True when no number may be printed (G-11); ``value`` is
    then None and :meth:`to_dict` writes no ``value`` key at all.
    """

    alpha: float
    value: Optional[float]
    unbounded: bool
    reason: Optional[str]
    scale: str
    informative: int
    required_informative: int
    k_eff: float
    at_grid_floor: bool = False

    @property
    def level(self) -> float:
        return 1.0 - self.alpha

    def to_dict(self) -> Dict:
        out = {
            "level": self.level,
            "alpha": self.alpha,
            "unbounded": bool(self.unbounded),
            "scale": self.scale,
            "informative_blocks": int(self.informative),
            "required_informative_blocks": int(self.required_informative),
            "k_eff": float(self.k_eff),
        }
        if self.unbounded:
            out["reason"] = self.reason
        else:
            out["value"] = float(self.value)
            out["at_grid_floor"] = bool(self.at_grid_floor)
        return out


def card_lines(x: LimitRecord, k: int) -> List[str]:
    """The "Ruled out" and "Not addressed" sentences of section 2.3 (none when unbounded)."""
    if x.unbounded or x.value is None:
        return []
    f = not_addressed_share(int(k))
    return [
        f"Ruled out: a steady effect of {x.value:.3g} or more in every episode.",
        f"Not addressed: an effect that appears in fewer than {f:.0%} of the episodes.",
    ]


@dataclass
class ExclusionResult:
    """Outcome of :func:`exclusion` for one test."""

    outcome_type: str
    effect_model: str
    scale: str
    side: str
    sesoi: Optional[float]
    p_exclusion: Optional[float]
    informative_at_sesoi: Optional[int]
    k_eff: float
    n_used: int
    n_thin: int
    x95: LimitRecord
    x_strict: Optional[LimitRecord]
    a_test: Optional[float]
    grid: Tuple[float, ...]
    p_reps: Optional[np.ndarray] = field(default=None, repr=False)

    def can_limit(self, a: float) -> bool:
        """Minimum-information rule at level ``a`` (I measured at the SESOI)."""
        if self.informative_at_sesoi is None:
            return False
        return can_limit(self.k_eff, self.informative_at_sesoi, a)

    def excluded(self, a: float) -> bool:
        """A steady effect of at least the SESOI is rejected at ``a`` (needed for E)."""
        return (
            self.p_exclusion is not None
            and self.p_exclusion <= float(a)
            and self.can_limit(a)
        )

    def card_lines(self) -> List[str]:
        """The two fixed sentences a card prints with X95 (empty when unbounded)."""
        return card_lines(self.x95, self.n_used)

    def to_dict(self) -> Dict:
        return {
            "method": "exclusion_by_effect_removal",
            "outcome_type": self.outcome_type,
            "effect_model": self.effect_model,
            "scale": self.scale,
            "side": self.side,
            "sesoi": self.sesoi,
            "p_exclusion": self.p_exclusion,
            "informative_at_sesoi": self.informative_at_sesoi,
            "k_eff": self.k_eff,
            "n_used": self.n_used,
            "n_thin": self.n_thin,
            "aggregation": "twice_median" if self.n_thin > 1 else "single",
            "x95": self.x95.to_dict(),
            "x_strict": None if self.x_strict is None else self.x_strict.to_dict(),
            "a_test": self.a_test,
            "grid": list(self.grid),
            "not_addressed_share": not_addressed_share(self.n_used) if self.n_used else None,
        }


def _limit(er: EffectRemoval, a: float, grid, side: str, info: int, steps: int) -> LimitRecord:
    need = min_informative(a)
    base = dict(alpha=float(a), scale=SCALES[er.outcome_type], informative=int(info),
                required_informative=need, k_eff=er.k_eff)
    if er.k_eff < MIN_K_EFF:
        return LimitRecord(value=None, unbounded=True, reason=REASON_FEW_BLOCKS, **base)
    if info < need:
        return LimitRecord(value=None, unbounded=True, reason=REASON_LOW_INFORMATION, **base)
    value, floor = er.search(a, grid, side, steps)
    if value is None:
        return LimitRecord(value=None, unbounded=True, reason=REASON_NOT_REACHED, **base)
    return LimitRecord(value=float(value), unbounded=False, reason=None,
                       at_grid_floor=bool(floor), **base)


def exclusion(
    design: BlockDesign,
    outcome,
    *,
    outcome_type: str,
    side: str,
    sesoi: Optional[float],
    grid,
    a_test: Optional[float] = None,
    thinning_rng: Optional[np.random.Generator] = None,
    signflip_seed: Optional[int] = None,
    n_thin: int = N_THIN,
    n_draws: int = _blocks.DEFAULT_DRAWS,
    steps: int = BISECT_STEPS,
    effect_shape=None,
    raw=None,
) -> ExclusionResult:
    """Exclusion p at the SESOI, X95 and X-strict for one test (section 2.2).

    Args:
        design, outcome, outcome_type: As for :func:`.blocks.primary_test`.
        side: The claimed direction, required: ``"greater"``, ``"less"`` or
            ``"two-sided"`` (see :func:`.blocks.alternative_for`).
        sesoi: On the claim scale (positive shift, or ratio above 1), from
            the plan (ADR-008 7.2). None when the plan has no SESOI: then
            there is no exclusion p and no E, and every limit is
            ``unbounded`` with reason ``no_sesoi`` (the information rule is
            measured at the SESOI).
        grid: The plan's grid for X, on the claim scale, increasing.
        a_test: The test's family threshold (section 3); gives X-strict.
        thinning_rng, signflip_seed, n_thin, n_draws, effect_shape, raw: See
            :class:`EffectRemoval`.
    """
    side = _check_side(side)
    outcome_type = _check_type(outcome_type)
    g = _check_grid(grid, outcome_type)
    levels = [X95_ALPHA]
    if a_test is not None:
        if not 0.0 < float(a_test) < 1.0:
            raise ValueError("a_test must lie in (0, 1)")
        levels.append(float(a_test))
    er = EffectRemoval(design, outcome, outcome_type=outcome_type,
                       thinning_rng=thinning_rng, signflip_seed=signflip_seed,
                       n_thin=n_thin, n_draws=n_draws, effect_shape=effect_shape, raw=raw)
    p_excl = info = p_reps = None
    if sesoi is not None:
        s = _check_magnitude(sesoi, outcome_type)
        p_excl = er.exclusion_p(s, side)
        info = er.informative_at(s, side)
        if side != "two-sided":
            ((r, alt),) = er.hypotheses(s, side)
            p_reps = er.p_reps(r, alt)
    records = []
    for a in levels:
        if sesoi is None:
            records.append(LimitRecord(
                alpha=a, value=None, unbounded=True, reason=REASON_NO_SESOI,
                scale=SCALES[outcome_type], informative=0,
                required_informative=min_informative(a), k_eff=er.k_eff))
        else:
            records.append(_limit(er, a, g, side, info, steps))
    return ExclusionResult(
        outcome_type=outcome_type,
        effect_model=EFFECT_MODELS[outcome_type],
        scale=SCALES[outcome_type],
        side=side,
        sesoi=None if sesoi is None else float(sesoi),
        p_exclusion=p_excl,
        informative_at_sesoi=info,
        k_eff=er.k_eff,
        n_used=er.n_used,
        n_thin=er.n_thin,
        x95=records[0],
        x_strict=records[1] if a_test is not None else None,
        a_test=None if a_test is None else float(a_test),
        grid=tuple(float(x) for x in g),
        p_reps=p_reps,
    )


def expected_informative(
    design: BlockDesign,
    base_rate: float,
    magnitude: float,
    *,
    outcome_type: str,
    side: str,
) -> float:
    """Expected I at ``magnitude`` under no effect, from the plan's base rate (gate).

    ``base_rate`` is events per bar (Poisson) for ``events`` and P(yes) per
    bar for ``flags``. A block counts when at least one event survives
    thinning on either side; exact ties between the two sides are ignored, so
    the prediction can only be optimistic through ties. For ``continuous``
    and ``log_ratio`` every used block is informative.
    """
    _check_type(outcome_type)
    side = _check_side(side)
    m = _check_magnitude(magnitude, outcome_type)
    used = design.used_blocks
    if outcome_type not in THINNED_TYPES:
        return float(len(used))
    total = 0.0
    for b in used:
        na, nc = float(b.n_active), float(b.n_control)
        mm = min(na, nc)
        up = ((mm / na) / m, mm / nc)
        down = (mm / na, (mm / nc) / m)
        pairs = {"greater": [up], "less": [down], "two-sided": [up, down]}[side]
        probs = []
        for qa, qc in pairs:
            if outcome_type == "events":
                none = math.exp(-float(base_rate) * (na * qa + nc * qc))
            else:
                p = float(base_rate)
                none = (1.0 - p * qa) ** na * (1.0 - p * qc) ** nc
            probs.append(1.0 - none)
        total += min(probs)
    return float(total)
