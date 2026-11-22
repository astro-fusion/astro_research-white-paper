"""Balanced disjoint blocks and the primary block sign-flip test.

ADR-008 section 1 (H-1), work package WP-85. Closes S-02, S-06 (with WP-86),
S-08 and S-15 of the strategy audit of 2026-11-22.

Design (section 1.1). :func:`build_blocks` reads the **calendar only**, never
an outcome, so the gate can run it before any outcome exists:

1. Episodes come from :func:`.episodes.episodes` with the plan's
   ``merge_gap``.
2. Each inactive gap between two episodes is cut at its midpoint. The left
   half belongs to the episode on its left, the right half to the episode on
   its right; an odd middle bar is dropped. Inactive bars before the first
   episode belong to it, those after the last episode to the last one. Each
   episode takes at most ``ceil(n_active / 2)`` control bars on each side,
   the ones nearest to it. So no bar is ever in two blocks.
3. ``guard_bars`` (plan, per dataset: 1 for monthly averages, else 0) bars
   next to the episode are skipped on each side before control bars are
   taken.
4. ``balance = n_control / n_active``. A block with balance below
   :data:`MIN_BALANCE` (0.5), with no control bar, or with control bars on
   one side only when the other side exists, is **dropped**. Drops are
   counted by reason; the gate and the test read the same counts (S-15).
5. Season-linked calendars use same-season windows from other years instead
   of neighbours. ``core/stats/season.py`` (WP-87) finds those windows; it
   hands them to :func:`design_from_windows`, which applies the same
   disjointness and balance rules.
6. The year unit (monsoon) is the same rule on a yearly grid: pass a
   calendar with one bar per year; each inactive year is used once.

Statistic (items 7 and 8). For used block k, ``d_k`` is the mean outcome on
its active bars minus the mean on its control bars (events and flags: counts
per bar, i.e. per unit exposure). With ``w_k`` = active bars used,
``T = sum(w_k d_k) / sum(w_k)``: all active bars against all matched control
bars, the control side reweighted to the active exposure. T is the estimate
on the card, the statistic the p-value tests, the scale X95 bounds (WP-86)
and the scale of the SESOI. For events and flags the card shows the pooled
rate (risk) ratio "active events / control events at equal exposure",
``sum_k E_A,k / sum_k (n_A,k E_C,k / n_C,k)``. Under every sign pattern the
sum of numerator and denominator is unchanged, so the ratio is a strictly
increasing function of T and the sign-flip p-value of T is the p-value of
the ratio as well (one test, one number).

Effective episodes (item 9): ``K_eff = (sum w)^2 / sum(w^2)``; gate G4 is
``K_eff >= MIN_K_EFF`` (8).

Primary test (item 10): sign-flip of the block differences with weights,
exact enumeration of all ``2**K`` patterns up to ``K = 20``, seeded Monte
Carlo above with ``p = (k + 1) / (B + 1)`` (the floor of ``nulls.py``).
Ties count as extreme. The side is required: there is no default
(:func:`alternative_for` maps the rule's claimed direction). The
circular-shift test is a sensitivity cell elsewhere and never enters here.

Nothing here starts a thread (G-13). Every function is deterministic given
its inputs and, for the Monte Carlo branch, ``rng``.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple, Union

import numpy as np
import pandas as pd

from .episodes import Episode, episodes

#: Block balance floor (section 1.1 item 4). Changed only by amending ADR-008.
MIN_BALANCE = 0.5
#: Gate G4 (section 1.1 item 9).
MIN_K_EFF = 8.0
#: Largest number of used blocks enumerated exactly (2**20 patterns).
MAX_ENUMERATED = 20
#: Default Monte Carlo draws above MAX_ENUMERATED blocks.
DEFAULT_DRAWS = 99_999
ALTERNATIVES = ("greater", "less", "two-sided")
#: Outcome types (as in ``core/validity/calibration.py``).
OUTCOME_TYPES = ("continuous", "log_ratio", "events", "flags")

#: Claimed direction (rule schema) to test side.
_DIRECTION_TO_SIDE = {
    "up": "greater",
    "increase": "greater",
    "down": "less",
    "decrease": "less",
    "either": "two-sided",
}

#: Drop reasons, in the order they are checked.
DROP_NO_ACTIVE = "no_active"
DROP_NO_CONTROL = "no_control"
DROP_ONE_SIDED = "one_sided"
DROP_LOW_BALANCE = "low_balance"
DROP_REASONS = (DROP_NO_ACTIVE, DROP_NO_CONTROL, DROP_ONE_SIDED, DROP_LOW_BALANCE)

_CHUNK = 1 << 16


# --------------------------------------------------------------------------
# Side
# --------------------------------------------------------------------------


def alternative_for(direction: str) -> str:
    """Test side for a rule's claimed direction (S-15: no default side).

    ``up``/``increase`` give ``"greater"``, ``down``/``decrease`` give
    ``"less"``, ``either`` gives ``"two-sided"``. Anything else raises.
    """
    try:
        return _DIRECTION_TO_SIDE[str(direction)]
    except KeyError:
        raise ValueError(
            f"unknown claimed direction {direction!r}; expected one of "
            f"{sorted(_DIRECTION_TO_SIDE)}"
        ) from None


def _check_alternative(alternative) -> str:
    if alternative not in ALTERNATIVES:
        raise ValueError(
            f"alternative must be one of {ALTERNATIVES} (there is no default side; "
            "use alternative_for(direction))"
        )
    return alternative


# --------------------------------------------------------------------------
# Design (calendar only)
# --------------------------------------------------------------------------


@dataclass(frozen=True, eq=False)
class Block:
    """One episode with its own control bars (positions on the grid).

    ``active`` are the episode's active bars that carry an outcome;
    ``control_left`` and ``control_right`` its control bars, nearest first.
    ``used`` is False when the block is dropped; ``reason`` then names why.
    """

    number: int
    episode: Episode
    active: np.ndarray
    control_left: np.ndarray
    control_right: np.ndarray
    left_exists: bool
    right_exists: bool
    used: bool
    reason: Optional[str]

    @property
    def control(self) -> np.ndarray:
        """Control bars of both sides in time order."""
        return np.concatenate((self.control_left[::-1], self.control_right))

    @property
    def n_active(self) -> int:
        return int(len(self.active))

    @property
    def n_control(self) -> int:
        return int(len(self.control_left) + len(self.control_right))

    @property
    def balance(self) -> float:
        return self.n_control / self.n_active if self.n_active else 0.0

    def to_dict(self) -> Dict:
        return {
            "block": self.number,
            "start": self.episode.start,
            "end": self.episode.end,
            "n_active": self.n_active,
            "n_control_left": int(len(self.control_left)),
            "n_control_right": int(len(self.control_right)),
            "n_control": self.n_control,
            "balance": self.balance,
            "used": self.used,
            "reason": self.reason,
        }


@dataclass(frozen=True, eq=False)
class BlockDesign:
    """Every block of one calendar, used or dropped; built before any outcome."""

    n_bars: int
    blocks: Tuple[Block, ...]
    merge_gap: object
    guard_bars: int
    kind: str  # "neighbours" or "windows"
    calendar_sha256: str
    available_sha256: Optional[str]

    @property
    def used_blocks(self) -> Tuple[Block, ...]:
        return tuple(b for b in self.blocks if b.used)

    @property
    def n_episodes(self) -> int:
        return len(self.blocks)

    @property
    def n_used(self) -> int:
        return len(self.used_blocks)

    @property
    def n_dropped(self) -> int:
        return self.n_episodes - self.n_used

    @property
    def drop_counts(self) -> Dict[str, int]:
        out = {r: 0 for r in DROP_REASONS}
        for b in self.blocks:
            if not b.used:
                out[b.reason] += 1
        return out

    @property
    def weights(self) -> np.ndarray:
        """``w_k`` = active bars used, per used block."""
        return np.asarray([b.n_active for b in self.used_blocks], dtype=float)

    @property
    def k_eff(self) -> float:
        """``(sum w)^2 / sum(w^2)``; 0 when no block is used."""
        w = self.weights
        if len(w) == 0:
            return 0.0
        return float(w.sum() ** 2 / np.sum(w * w))

    @property
    def design_id(self) -> str:
        """SHA-256 of the calendar, the parameters and every block's bars."""
        h = hashlib.sha256()
        head = {
            "n_bars": self.n_bars,
            "merge_gap": str(self.merge_gap),
            "guard_bars": self.guard_bars,
            "kind": self.kind,
            "calendar": self.calendar_sha256,
            "available": self.available_sha256,
            "min_balance": MIN_BALANCE,
        }
        h.update(json.dumps(head, sort_keys=True).encode("utf-8"))
        for b in self.blocks:
            h.update(f"|{b.number}:{int(b.used)}:{b.reason}|".encode("utf-8"))
            for arr in (b.active, b.control_left, b.control_right):
                h.update(np.asarray(arr, dtype="<i8").tobytes())
                h.update(b"/")
        return h.hexdigest()

    def p_min(self, alternative: str, n_draws: int = DEFAULT_DRAWS) -> float:
        """Smallest p-value the primary test can return on this design."""
        return sign_flip_p_min(self.n_used, _check_alternative(alternative), n_draws)

    def table(self) -> pd.DataFrame:
        """One row per block, used or dropped, for the gate report."""
        cols = ["block", "start", "end", "n_active", "n_control_left",
                "n_control_right", "n_control", "balance", "used", "reason"]
        return pd.DataFrame([b.to_dict() for b in self.blocks], columns=cols)

    def gate_summary(self, alternative: str, n_draws: int = DEFAULT_DRAWS) -> Dict:
        """What the gate reports; :meth:`BlockTestResult.gate_summary` must equal it (B6)."""
        alternative = _check_alternative(alternative)
        return {
            "design_id": self.design_id,
            "alternative": alternative,
            "n_episodes": self.n_episodes,
            "n_used": self.n_used,
            "n_dropped": self.n_dropped,
            "drop_counts": self.drop_counts,
            "k_eff": self.k_eff,
            "p_min": self.p_min(alternative, n_draws),
        }


def _as_mask(values, name: str, n: Optional[int] = None) -> np.ndarray:
    v = values.to_numpy() if isinstance(values, pd.Series) else np.asarray(values)
    if v.ndim != 1:
        raise ValueError(f"{name} must be one-dimensional")
    if v.dtype.kind == "f" and np.isnan(v).any():
        raise ValueError(f"{name} contains NaN")
    if v.dtype.kind not in "biuf":
        raise ValueError(f"{name} must be boolean or 0/1, got dtype {v.dtype}")
    if v.dtype.kind != "b" and not np.isin(v, (0, 1)).all():
        raise ValueError(f"{name} must contain only 0/1 or booleans")
    if n is not None and len(v) != n:
        raise ValueError(f"{name} must have the calendar's length {n}, got {len(v)}")
    return v.astype(bool)


def _sha(mask: np.ndarray) -> str:
    return hashlib.sha256(
        str(len(mask)).encode("ascii") + b":" + np.packbits(mask.astype(np.uint8)).tobytes()
    ).hexdigest()


def _classify(n_active, left, right, left_exists, right_exists) -> Optional[str]:
    if n_active == 0:
        return DROP_NO_ACTIVE
    if len(left) + len(right) == 0:
        return DROP_NO_CONTROL
    if (left_exists and len(left) == 0) or (right_exists and len(right) == 0):
        return DROP_ONE_SIDED
    if (len(left) + len(right)) / n_active < MIN_BALANCE:
        return DROP_LOW_BALANCE
    return None


def build_blocks(
    calendar,
    *,
    merge_gap: Union[int, str, pd.Timedelta],
    guard_bars: int = 0,
    available=None,
) -> BlockDesign:
    """Build the balanced disjoint blocks of a calendar (section 1.1 items 1 to 4, 6).

    Reads the calendar only. No outcome is an argument, so the gate can call
    this before any outcome is loaded.

    Args:
        calendar: Boolean (or 0/1) array or Series, one value per bar (a
            yearly calendar for the year unit).
        merge_gap: The plan's merge gap (see :func:`.episodes.episodes`).
        guard_bars: Bars next to each episode skipped on each side (plan,
            per dataset; 1 for monthly-average prices, 0 otherwise).
        available: Optional boolean mask of bars that carry an outcome
            (known from the grid, not from outcome values). Unavailable
            active bars are not counted; unavailable control bars are passed
            over and the next nearest bar of the episode's own half is taken.

    Returns:
        A :class:`BlockDesign` with every episode's block, used or dropped.
    """
    active = _as_mask(calendar, "calendar")
    n = len(active)
    avail = np.ones(n, dtype=bool) if available is None else _as_mask(available, "available", n)
    if isinstance(guard_bars, bool) or int(guard_bars) != guard_bars or int(guard_bars) < 0:
        raise ValueError("guard_bars must be a non-negative integer")
    guard = int(guard_bars)
    eps = episodes(calendar, merge_gap)

    def take(region: np.ndarray, cap: int) -> np.ndarray:
        cand = region[guard:]
        cand = cand[avail[cand]]
        return cand[:cap].astype(np.int64)

    blocks: List[Block] = []
    for k, ep in enumerate(eps):
        span = np.arange(ep.start, ep.end + 1)
        on = span[active[span] & avail[span]]
        cap = math.ceil(len(on) / 2)
        # This episode's share of the gap on its left, nearest bar first.
        if k == 0:
            left_region = np.arange(ep.start - 1, -1, -1)
        else:
            half = (ep.start - eps[k - 1].end - 1) // 2
            left_region = np.arange(ep.start - 1, ep.start - 1 - half, -1)
        # Its share of the gap on its right, nearest bar first.
        if k == len(eps) - 1:
            right_region = np.arange(ep.end + 1, n)
        else:
            half = (eps[k + 1].start - ep.end - 1) // 2
            right_region = np.arange(ep.end + 1, ep.end + 1 + half)
        left_exists = ep.start > 0
        right_exists = ep.end < n - 1
        left, right = take(left_region, cap), take(right_region, cap)
        reason = _classify(len(on), left, right, left_exists, right_exists)
        blocks.append(
            Block(
                number=k,
                episode=ep,
                active=on.astype(np.int64),
                control_left=left,
                control_right=right,
                left_exists=bool(left_exists),
                right_exists=bool(right_exists),
                used=reason is None,
                reason=reason,
            )
        )
    design = BlockDesign(
        n_bars=n,
        blocks=tuple(blocks),
        merge_gap=merge_gap,
        guard_bars=guard,
        kind="neighbours",
        calendar_sha256=_sha(active),
        available_sha256=None if available is None else _sha(avail),
    )
    _check_disjoint(design, active)
    return design


def design_from_windows(
    calendar,
    windows: Sequence[Tuple],
    *,
    merge_gap: Union[int, str, pd.Timedelta],
    available=None,
) -> BlockDesign:
    """Blocks with control windows chosen elsewhere (season-linked calendars, item 5).

    ``windows`` has one entry per episode of ``episodes(calendar, merge_gap)``,
    in order: ``(control_left, control_right)`` or ``(control_left,
    control_right, left_exists, right_exists)``. ``core/stats/season.py``
    supplies same-season spans from other years; an empty side whose
    ``*_exists`` is True drops the block, as in :func:`build_blocks`. The
    ``ceil(n_active / 2)`` cap does not apply (a same-season span has the
    episode's own length); the balance floor does. Raises if a control bar is
    active, inside an episode span, unavailable, or shared by two blocks.
    """
    active = _as_mask(calendar, "calendar")
    n = len(active)
    avail = np.ones(n, dtype=bool) if available is None else _as_mask(available, "available", n)
    eps = episodes(calendar, merge_gap)
    if len(windows) != len(eps):
        raise ValueError(f"need one window entry per episode ({len(eps)}), got {len(windows)}")
    blocks: List[Block] = []
    for k, (ep, win) in enumerate(zip(eps, windows)):
        if len(win) == 2:
            left, right = win
            left_exists = right_exists = True
        elif len(win) == 4:
            left, right, left_exists, right_exists = win
        else:
            raise ValueError(
                "a window entry is (left, right) or (left, right, left_exists, right_exists)"
            )
        left = np.asarray(left, dtype=np.int64).ravel()
        right = np.asarray(right, dtype=np.int64).ravel()
        for side in (left, right):
            if len(side) and (side.min() < 0 or side.max() >= n):
                raise ValueError(f"block {k}: control bar outside the grid")
            if len(side) and not avail[side].all():
                raise ValueError(f"block {k}: control bar without an outcome")
        span = np.arange(ep.start, ep.end + 1)
        on = span[active[span] & avail[span]]
        reason = _classify(len(on), left, right, bool(left_exists), bool(right_exists))
        blocks.append(
            Block(k, ep, on.astype(np.int64), left, right, bool(left_exists),
                  bool(right_exists), reason is None, reason)
        )
    design = BlockDesign(
        n_bars=n,
        blocks=tuple(blocks),
        merge_gap=merge_gap,
        guard_bars=0,
        kind="windows",
        calendar_sha256=_sha(active),
        available_sha256=None if available is None else _sha(avail),
    )
    _check_disjoint(design, active)
    return design


def _check_disjoint(design: BlockDesign, active: np.ndarray) -> None:
    """No bar in two blocks; control bars inactive and outside every episode span."""
    in_span = np.zeros(design.n_bars, dtype=bool)
    for b in design.blocks:
        in_span[b.episode.start : b.episode.end + 1] = True
    owner = np.full(design.n_bars, -1, dtype=np.int64)
    for b in design.blocks:
        for arr, is_control in ((b.active, False), (b.control_left, True), (b.control_right, True)):
            if len(arr) == 0:
                continue
            if len(np.unique(arr)) != len(arr):
                raise ValueError(f"block {b.number}: a bar is listed twice")
            if is_control and (active[arr].any() or in_span[arr].any()):
                raise ValueError(f"block {b.number}: a control bar is active or inside an episode")
            taken = owner[arr]
            if (taken >= 0).any():
                raise ValueError(
                    f"bar {int(arr[taken >= 0][0])} is in blocks {int(taken[taken >= 0][0])} "
                    f"and {b.number}: blocks must be disjoint (S-02)"
                )
            owner[arr] = b.number


# --------------------------------------------------------------------------
# Outcome side
# --------------------------------------------------------------------------


def _outcome_values(outcome, n: int, outcome_type: str) -> np.ndarray:
    """The one place this module reads an outcome (the tests spy on it)."""
    y = (
        outcome.to_numpy(dtype=float)
        if isinstance(outcome, pd.Series)
        else np.asarray(outcome, dtype=float)
    )
    if y.ndim != 1 or len(y) != n:
        raise ValueError(f"outcome must be one-dimensional with {n} bars, got shape {y.shape}")
    if outcome_type in ("events", "flags"):
        fin = y[np.isfinite(y)]
        if (fin < 0).any():
            raise ValueError(f"{outcome_type} outcome must be non-negative counts")
        if outcome_type == "flags" and not np.isin(fin, (0.0, 1.0)).all():
            raise ValueError("flags outcome must be 0 or 1 per bar")
    return y


def _check_type(outcome_type) -> str:
    if outcome_type not in OUTCOME_TYPES:
        raise ValueError(f"outcome_type must be one of {OUTCOME_TYPES}")
    return outcome_type


@dataclass
class BlockDifferences:
    """Per used block: active and control means, ``d_k`` and ``w_k``."""

    active_mean: np.ndarray
    control_mean: np.ndarray
    active_sum: np.ndarray
    n_active: np.ndarray
    n_control: np.ndarray

    @property
    def d(self) -> np.ndarray:
        return self.active_mean - self.control_mean

    @property
    def w(self) -> np.ndarray:
        return self.n_active.astype(float)

    @property
    def statistic(self) -> float:
        """``T = sum(w d) / sum(w)`` (NaN with no used block)."""
        w = self.w
        return float(np.sum(w * self.d) / np.sum(w)) if len(w) else float("nan")

    @property
    def ratio(self) -> float:
        """Active events over control events at equal exposure (events, flags)."""
        num = float(np.sum(self.active_sum))
        den = float(np.sum(self.n_active * self.control_mean))
        if den == 0.0:
            return float("inf") if num > 0 else float("nan")
        return num / den


def block_differences(design: BlockDesign, outcome, *, outcome_type: str) -> BlockDifferences:
    """Means over each used block's active and control bars (items 7, 8).

    Raises if a bar the design uses has no finite outcome: such a bar must be
    marked unavailable when the blocks are built, so the gate and the test
    count the same blocks (S-15).
    """
    _check_type(outcome_type)
    y = _outcome_values(outcome, design.n_bars, outcome_type)
    a_mean, c_mean, a_sum, n_a, n_c = [], [], [], [], []
    for b in design.used_blocks:
        ya, yc = y[b.active], y[b.control]
        if not (np.isfinite(ya).all() and np.isfinite(yc).all()):
            raise ValueError(
                f"block {b.number} uses a bar with no finite outcome; pass "
                "available= to build_blocks so the gate sees the same blocks"
            )
        a_mean.append(ya.mean())
        c_mean.append(yc.mean())
        a_sum.append(ya.sum())
        n_a.append(len(ya))
        n_c.append(len(yc))
    return BlockDifferences(
        np.asarray(a_mean, dtype=float),
        np.asarray(c_mean, dtype=float),
        np.asarray(a_sum, dtype=float),
        np.asarray(n_a, dtype=np.int64),
        np.asarray(n_c, dtype=np.int64),
    )


# --------------------------------------------------------------------------
# Weighted sign-flip
# --------------------------------------------------------------------------


def sign_flip_p_min(n_blocks: int, alternative: str, n_draws: int = DEFAULT_DRAWS) -> float:
    """Smallest attainable p for ``n_blocks`` used blocks (1.0 with none)."""
    _check_alternative(alternative)
    k = int(n_blocks)
    if k < 1:
        return 1.0
    if k <= MAX_ENUMERATED:
        return float((2 if alternative == "two-sided" else 1) / 2.0**k)
    return float(1.0 / (int(n_draws) + 1))


@dataclass
class SignFlip:
    """Outcome of :func:`weighted_sign_flip`."""

    statistic: float
    p_value: float
    p_min: float
    n_blocks: int
    n_null: int
    exact_enumeration: bool
    alternative: str


def _count_extreme(stats: np.ndarray, observed: float, tol: float, alternative: str) -> int:
    if alternative == "greater":
        return int(np.sum(stats >= observed - tol))
    if alternative == "less":
        return int(np.sum(stats <= observed + tol))
    return int(np.sum(np.abs(stats) >= abs(observed) - tol))


def weighted_sign_flip(
    d,
    w,
    *,
    alternative: str,
    rng: Optional[np.random.Generator] = None,
    n_draws: int = DEFAULT_DRAWS,
) -> SignFlip:
    """Sign-flip test of ``T = sum(w d) / sum(w)`` (section 1.1 item 10).

    Each block's difference keeps its weight and gets a sign; under no
    effect, swapping active and control inside a block leaves the joint
    distribution unchanged, so every sign pattern is equally likely. Exact
    over all ``2**K`` patterns for ``K <= 20``; otherwise ``n_draws``
    patterns from ``rng`` and ``p = (count + 1) / (n_draws + 1)``. Ties
    count as extreme. Two-sided extremeness is ``|T|``. Also meant for
    ``exclusion.py`` (WP-86) on effect-removed data.
    """
    alternative = _check_alternative(alternative)
    d = np.asarray(d, dtype=float).ravel()
    w = np.asarray(w, dtype=float).ravel()
    if d.shape != w.shape:
        raise ValueError("d and w must have the same length")
    if not (np.isfinite(d).all() and np.isfinite(w).all()) or (w <= 0).any():
        raise ValueError("d must be finite and w positive")
    k = len(d)
    if k == 0:
        return SignFlip(float("nan"), 1.0, 1.0, 0, 0, True, alternative)
    wd = w * d
    observed = float(wd.sum())
    tol = 1e-12 * (float(np.abs(wd).sum()) + 1.0)
    exact = k <= MAX_ENUMERATED
    count = 0
    seen = 0
    if exact:
        total = 1 << k
        bits = np.arange(k, dtype=np.int64)
        for lo in range(0, total, _CHUNK):
            codes = np.arange(lo, min(total, lo + _CHUNK), dtype=np.int64)
            flips = ((codes[:, None] >> bits) & 1).astype(float)
            stats = observed - 2.0 * (flips @ wd)
            count += _count_extreme(stats, observed, tol, alternative)
            seen += len(stats)
        p = count / seen
    else:
        if not isinstance(rng, np.random.Generator):
            raise ValueError(
                f"more than {MAX_ENUMERATED} used blocks needs rng (the test's own "
                "'signflip' stream, ADR-008 3.5)"
            )
        remaining = int(n_draws)
        if remaining < 1:
            raise ValueError("n_draws must be at least 1")
        while remaining > 0:
            size = min(_CHUNK, remaining)
            signs = rng.choice(np.array([-1.0, 1.0]), size=(size, k))
            count += _count_extreme(signs @ wd, observed, tol, alternative)
            seen += size
            remaining -= size
        p = (count + 1) / (seen + 1)
    return SignFlip(
        statistic=observed / float(w.sum()),
        p_value=float(min(1.0, p)),
        p_min=sign_flip_p_min(k, alternative, n_draws),
        n_blocks=k,
        n_null=int(seen),
        exact_enumeration=exact,
        alternative=alternative,
    )


# --------------------------------------------------------------------------
# Primary test
# --------------------------------------------------------------------------


@dataclass
class BlockTestResult:
    """Outcome of :func:`primary_test`. ``statistic`` is T (section 1.1 item 8)."""

    statistic: float
    estimate: float
    estimate_scale: str
    p_value: float
    p_min: float
    alternative: str
    outcome_type: str
    n_episodes: int
    n_used: int
    n_dropped: int
    drop_counts: Dict[str, int]
    k_eff: float
    sum_w: float
    exact_enumeration: bool
    n_null: int
    design_id: str
    differences: np.ndarray = field(repr=False, default=None)
    weights: np.ndarray = field(repr=False, default=None)
    ratio: Optional[float] = None

    def gate_summary(self) -> Dict:
        """Same keys as :meth:`BlockDesign.gate_summary`; B6 asserts equality."""
        return {
            "design_id": self.design_id,
            "alternative": self.alternative,
            "n_episodes": self.n_episodes,
            "n_used": self.n_used,
            "n_dropped": self.n_dropped,
            "drop_counts": dict(self.drop_counts),
            "k_eff": self.k_eff,
            "p_min": self.p_min,
        }


_SCALES = {
    "continuous": "difference",
    "log_ratio": "log_ratio",
    "events": "rate_ratio",
    "flags": "risk_ratio",
}


def primary_test(
    design: BlockDesign,
    outcome,
    *,
    alternative: str,
    outcome_type: str,
    rng: Optional[np.random.Generator] = None,
    n_draws: int = DEFAULT_DRAWS,
) -> BlockTestResult:
    """The primary test of every outcome type: block sign-flip of T.

    Args:
        design: From :func:`build_blocks` or :func:`design_from_windows`
            (built before the outcome is read; the gate reads the same one).
        outcome: One value per bar. ``continuous``: the outcome; ``log_ratio``:
            already on the log scale with the plan's floor; ``events``: counts
            of the plan's counting unit per bar; ``flags``: 0/1 per bar.
        alternative: Required (no default side): ``"greater"`` (active above
            control), ``"less"`` or ``"two-sided"``; see :func:`alternative_for`.
        outcome_type: One of :data:`OUTCOME_TYPES`.
        rng: Needed above 20 used blocks (the test's ``signflip`` stream).
        n_draws: Monte Carlo draws above 20 used blocks.

    ``estimate`` is T for ``continuous`` and ``log_ratio`` (a difference on
    the outcome's scale), and the pooled ratio at equal exposure for
    ``events`` and ``flags`` (a strictly increasing function of T under every
    sign pattern, so the p-value is the same). With no used block the result
    has ``n_used == 0``, ``p_value == 1`` and a NaN estimate (verdict U).
    """
    alternative = _check_alternative(alternative)
    outcome_type = _check_type(outcome_type)
    diffs = block_differences(design, outcome, outcome_type=outcome_type)
    d, w = diffs.d, diffs.w
    sf = weighted_sign_flip(d, w, alternative=alternative, rng=rng, n_draws=n_draws)
    t_stat = diffs.statistic
    ratio = diffs.ratio if outcome_type in ("events", "flags") and len(d) else None
    estimate = ratio if outcome_type in ("events", "flags") else t_stat
    return BlockTestResult(
        statistic=t_stat,
        estimate=float("nan") if estimate is None else float(estimate),
        estimate_scale=_SCALES[outcome_type],
        p_value=sf.p_value,
        p_min=design.p_min(alternative, n_draws),
        alternative=alternative,
        outcome_type=outcome_type,
        n_episodes=design.n_episodes,
        n_used=design.n_used,
        n_dropped=design.n_dropped,
        drop_counts=design.drop_counts,
        k_eff=design.k_eff,
        sum_w=float(w.sum()),
        exact_enumeration=sf.exact_enumeration,
        n_null=sf.n_null,
        design_id=design.design_id,
        differences=d,
        weights=w,
        ratio=ratio,
    )
