"""The year test and yearly exclusion (ADR-008 Amendment A3, H-8 and H-9; WP-101).

A vintage with ``grain: yearly`` uses this test for every test and every
outcome type; every other grain uses the block test of :mod:`.blocks`. The
grain is a property of the data, so nobody chooses a method (A3.1 Routing).

Design (A3.1 items 1 to 3), calendar and ENSO only, never an outcome:

1. **Units.** The years of the tested period with a finite outcome (the
   caller passes that as a mask, ``finite``). Every year is used at most once.
2. **Strata.** ENSO phase x epoch. Phase from the June to September mean
   Nino 3.4 anomaly: cold at or below -0.5 C, warm at or above +0.5 C,
   neutral otherwise (:data:`ENSO_THRESHOLD`). Epoch: the two halves of the
   tested period by year count, an odd middle year in the earlier half.
   Collapse rule, counts only: a phase with fewer than 2 active or fewer than
   2 inactive years in either half loses its epoch split; a phase that still
   has fewer than 2 of either is dropped with reason ``no_stratum_control``
   (its years are counted and printed). No IOD stratum.
3. **Gate (G4 for yearly grids).** Used active years >= 8, used inactive
   years >= 8 and K_eff >= 8, K_eff = (sum w)^2 / sum w^2 over the runs of
   active years (w = used years in the run; runs merged across gaps of at
   most ``merge_gap`` years). Reasons ``too_few_years``, ``too_few_episodes``.

Outcome (item 4): continuous outcomes are the leave-year-out anomaly, then
the plan's baselines regressed out (core/stats/season.py remove_baselines,
the N-02 baseline-aware method). Yes/no outcomes are used as 0/1.

Statistic (item 5): ``T = sum_s n1_s (mean_active_s - mean_inactive_s) / sum_s n1_s``
over used strata. T is the estimate, the tested number and the X and SESOI
scale. Yes/no outcomes also get the pooled (active-standardised) risk ratio,
and every record carries the unstratified, no-baseline difference (the
"without known channels" row, section 7.3).

Null (item 6): prewhitened permutation, worst case over the envelope
:data:`ENVELOPE` = {-0.3, ..., +0.3}. u = outcome minus its stratum mean; for
each rho the innovations e_t = u_t - rho u_(t-1) (the first year of an
unbroken stretch: sqrt(1 - rho^2) u_t), over all finite years including
those of dropped strata; B permutations of the innovations rebuild u* by the
same recursion; T* is computed on the fixed calendar and strata, after the
same baseline regression the outcome went through (the null re-runs the
linear chain, as A3.2 item 1 asks of exclusion). p_rho = (1 + #{T* at least
as extreme}) / (B + 1); **p = max over rho**. B = min(200,000, max(19,999,
ceil(50 / a_test))), from the test's own ``yearperm`` stream (section 3.5).

Implementation details fixed here (not choices per test):

* T* is linear in the permuted innovations, ``T* = v_rho . e[pi]`` with
  ``v_rho = L_rho' M w`` (L_rho the AR(1) rebuild, M the baseline residual
  maker, w the stratum weights), so one permutation costs one dot product per
  rho. The same permutations serve every rho and both sides.
* The innovations are centred before permuting, so T* has mean zero.
* Permutations are drawn in fixed chunks of :data:`CHUNK` rows, so a run that
  stops early (``stop_level``, simulation only) has drawn exactly the same
  permutations as the full run and reaches the same decision at that level.

Safety check (item 7): rho_hat = lag-1 autocorrelation of u; if
``|rho_hat| > 0.3 + 1.645 / sqrt(N)`` the record carries
``dependence_outside_envelope`` (S, C and E impossible; WP-102 applies it).

Exclusion (A3.2): an effect of size r is removed from the active years on the
raw scale, in the claimed direction, before the anomaly, the baselines and
the strata; the whole chain is re-run (it is linear, so removal at r is
``T(r) = T - r T_h`` and ``T*(r) = T* - r T*_h`` with h the active indicator put
through the chain, on the same permutations). Yes/no: each "yes" in the arm
the claim calls higher is kept with probability 1/r, 199 nested thinnings,
p = twice the median over thinnings of the largest p over the envelope.
X95 = smallest grid r with p_ex <= 0.05 at r and every larger grid value,
refined by bisection towards the previous grid point (upper end reported).
X-strict likewise at a_test. Two-sided claims: both directions excluded,
each at the level in use; the printed X is the larger limit.
Minimum information (item 5): continuous, the gate above; yes/no, the
expected "yes" years in the smaller arm (base rate x arm size) >= 5 for X95
and >= ceil(log2(1 / a_test)) for X-strict, else ``unbounded``.
Item 6: the "Not addressed" line uses K = number of active runs.
With no SESOI the limits are still printed (A3.4 item 5); only the exclusion
p and verdict E need one.

Past data only; nothing here forecasts. Nothing starts a thread.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple, Union

import numpy as np

from . import exclusion as _ex

#: A3.1 item 6: the fixed envelope of AR(1) members. Changed only by amendment.
ENVELOPE: Tuple[float, ...] = (-0.3, -0.2, -0.1, 0.0, 0.1, 0.2, 0.3)
ENVELOPE_EDGE = 0.3
#: A3.1 item 7: one-way safety check, |rho_hat| > ENVELOPE_EDGE + SAFETY_Z / sqrt(N).
SAFETY_Z = 1.645
#: A3.1 item 2: ENSO phase threshold (degrees C on the JJAS mean anomaly).
ENSO_THRESHOLD = 0.5
ENSO_MONTHS = ("JUN", "JUL", "AUG", "SEP")
PHASE_COLD, PHASE_NEUTRAL, PHASE_WARM = "cold", "neutral", "warm"
#: Phase label when the plan has no ENSO series (one phase; strata are epochs only).
PHASE_NONE = "all"
#: Collapse rule: years per arm a stratum needs.
MIN_STRATUM_ARM = 2
#: Gate G4 for yearly grids.
MIN_YEARS = 8
MIN_K_EFF = 8.0
#: B = min(B_CAP, max(B_FLOOR, ceil(B_PER_ALPHA / a_test))).
B_FLOOR = 19_999
B_CAP = 200_000
B_PER_ALPHA = 50
#: Calibration cells at the 5% level may use this B (A3.3).
B_CALIBRATION = 1_999
#: Section 3.5 purpose of the permutation stream.
PERM_PURPOSE = "yearperm"
#: Permutations drawn per chunk (fixed: early stopping must see the same draws).
CHUNK = 256
#: Thinning repetitions for yes/no exclusion (section 2.2).
N_THIN = _ex.N_THIN
X95_ALPHA = _ex.X95_ALPHA
BISECT_STEPS = 40

OUTCOME_TYPES = ("continuous", "flags")
SIDES = ("greater", "less", "two-sided")

REASON_TOO_FEW_YEARS = "too_few_years"
REASON_TOO_FEW_EPISODES = "too_few_episodes"
DROP_NO_STRATUM_CONTROL = "no_stratum_control"
DROP_NO_ENSO = "no_enso_value"
FLAG_OUTSIDE_ENVELOPE = "dependence_outside_envelope"
REASON_NO_BASE_RATE = "no_base_rate"
REASON_TOO_FEW_YES = "too_few_expected_yes"
REASON_NOT_TESTABLE = "year_gate_failed"

#: The validity sentence every yearly card prints (A3.1).
VALIDITY_SENTENCE = (
    "Valid if the year-to-year dependence of the outcome, after ENSO and trend, "
    "is no stronger than lag-1 correlation 0.3 in either direction."
)


# --------------------------------------------------------------------------
# Constants of one test
# --------------------------------------------------------------------------


def production_b(a_test: Optional[float]) -> int:
    """B of A3.1 item 6; ``a_test=None`` gives the floor."""
    if a_test is None:
        return B_FLOOR
    a = float(a_test)
    if not 0.0 < a < 1.0:
        raise ValueError("a_test must lie in (0, 1)")
    return int(min(B_CAP, max(B_FLOOR, math.ceil(B_PER_ALPHA / a))))


def smallest_p(n_perm: int) -> float:
    """Smallest attainable p, ``1 / (B + 1)`` (G5)."""
    return 1.0 / (int(n_perm) + 1.0)


def year_perm_seed(plan_seed: Union[int, str], test_id: str) -> int:
    """Seed of the test's ``yearperm`` stream: first 8 bytes of SHA-256(plan seed|test id|yearperm)."""
    if isinstance(plan_seed, bool) or not isinstance(plan_seed, (int, str)) or plan_seed == "":
        raise ValueError("plan seed must be an integer or a non-empty string")
    if not isinstance(test_id, str) or not test_id:
        raise ValueError("test id must be a non-empty string")
    digest = hashlib.sha256(f"{plan_seed}|{test_id}|{PERM_PURPOSE}".encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big")


def safety_limit(n_years: int) -> float:
    """|rho_hat| above this flags ``dependence_outside_envelope`` (item 7)."""
    return ENVELOPE_EDGE + SAFETY_Z / math.sqrt(max(int(n_years), 1))


# --------------------------------------------------------------------------
# ENSO phase and epochs (calendar side only)
# --------------------------------------------------------------------------


def jjas_anomaly(monthly, base_period: Tuple[int, int]):
    """June to September mean of a monthly table (index: year; columns JUN..SEP), minus its base-period mean.

    ``base_period`` is the plan's ``enso.phase_base_period`` as (first year, last
    year), inclusive. A year with a missing month is NaN.
    """
    import pandas as pd

    df = monthly if isinstance(monthly, pd.DataFrame) else pd.DataFrame(monthly)
    s = df[list(ENSO_MONTHS)].astype(float).mean(axis=1, skipna=False)
    lo, hi = int(base_period[0]), int(base_period[1])
    if hi < lo:
        raise ValueError("base period ends before it starts")
    base = s[(s.index >= lo) & (s.index <= hi)].dropna()
    if len(base) < hi - lo + 1:
        raise ValueError(f"the ENSO series does not cover the base period {lo}-{hi}")
    return s - base.mean()


def enso_phase(anomaly) -> np.ndarray:
    """Phase per year from the JJAS anomaly; '' where the anomaly is missing."""
    z = np.asarray(anomaly, dtype=float)
    out = np.full(len(z), PHASE_NEUTRAL, dtype=object)
    out[z >= ENSO_THRESHOLD] = PHASE_WARM
    out[z <= -ENSO_THRESHOLD] = PHASE_COLD
    out[~np.isfinite(z)] = ""
    return out


def epochs(n_years: int) -> np.ndarray:
    """0 for the earlier half of the period, 1 for the later (odd middle year earlier)."""
    n = int(n_years)
    return (np.arange(n) >= (n + 1) // 2).astype(int)


# --------------------------------------------------------------------------
# Design
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Stratum:
    label: str
    phase: str
    epoch: Optional[int]  # None when the phase lost its epoch split
    n_active: int
    n_inactive: int

    def to_dict(self) -> Dict:
        return {"label": self.label, "phase": self.phase, "epoch": self.epoch,
                "n_active": self.n_active, "n_inactive": self.n_inactive}


@dataclass
class YearDesign:
    """The design of one yearly test; built from the calendar, the ENSO phase and the finite mask only."""

    years: np.ndarray
    active: np.ndarray
    finite: np.ndarray
    phase: np.ndarray
    epoch: np.ndarray
    stratum: np.ndarray  # index into strata, -1 when the year is not used
    group: np.ndarray  # centring group of every finite year (-1: not finite)
    strata: Tuple[Stratum, ...]
    dropped: Tuple[Dict, ...]
    runs: Tuple[Tuple[int, int, int], ...]  # (first year, last year, used active years)
    n_active: int
    n_inactive: int
    k_eff: float
    reason: Optional[str]
    merge_gap: int

    @property
    def testable(self) -> bool:
        return self.reason is None

    @property
    def used(self) -> np.ndarray:
        return self.stratum >= 0

    @property
    def n_runs(self) -> int:
        return len(self.runs)

    @property
    def n_groups(self) -> int:
        g = self.group[self.group >= 0]
        return int(len(np.unique(g)))

    def weights(self) -> np.ndarray:
        """w with T = w . outcome: 1/N1 on used active years, -(n1_s/n0_s)/N1 on used inactive years."""
        w = np.zeros(len(self.years))
        n1 = float(self.n_active)
        if n1 <= 0:
            return w
        for k, s in enumerate(self.strata):
            m = self.stratum == k
            w[m & self.active] = 1.0 / n1
            if s.n_inactive:
                w[m & ~self.active] = -(s.n_active / s.n_inactive) / n1
        return w

    def to_dict(self) -> Dict:
        return {
            "method": "year_test",
            "years": [int(self.years[0]), int(self.years[-1])] if len(self.years) else None,
            "n_years_finite": int(self.finite.sum()),
            "n_active_used": int(self.n_active),
            "n_inactive_used": int(self.n_inactive),
            "k_eff": float(self.k_eff),
            "n_runs": self.n_runs,
            "merge_gap": int(self.merge_gap),
            "strata": [s.to_dict() for s in self.strata],
            "dropped": [dict(d) for d in self.dropped],
            "gate": "pass" if self.testable else self.reason,
        }


def _as_bool(x, name: str, n: Optional[int] = None) -> np.ndarray:
    a = np.asarray(x)
    if a.ndim != 1:
        raise ValueError(f"{name} must be one-dimensional")
    if n is not None and len(a) != n:
        raise ValueError(f"{name} must have one value per year ({n}), got {len(a)}")
    if a.dtype != bool:
        af = a.astype(float)
        if not np.isin(af, (0.0, 1.0)).all():
            raise ValueError(f"{name} must be 0/1")
        a = af.astype(bool)
    return a


def _runs(mask: np.ndarray, merge_gap: int) -> List[Tuple[int, int]]:
    m = mask.astype(np.int8)
    d = np.diff(np.concatenate([[0], m, [0]]))
    runs = list(zip(np.flatnonzero(d == 1).tolist(), np.flatnonzero(d == -1).tolist()))
    merged: List[List[int]] = []
    for s, e in runs:
        if merged and s - merged[-1][1] <= int(merge_gap):
            merged[-1][1] = e
        else:
            merged.append([s, e])
    return [(s, e) for s, e in merged]


def year_design(active, years, *, enso=None, finite=None, merge_gap: int = 0) -> YearDesign:
    """Strata, drops and gate of A3.1 items 1 to 3 (reads no outcome).

    Args:
        active: 0/1 per year of the tested period, as the adapter defines it.
        years: the years of the tested period, increasing and consecutive.
        enso: JJAS Nino 3.4 anomaly per year (degrees C, see :func:`jjas_anomaly`),
            or None (one phase; strata are the epochs only).
        finite: True where the year has a finite outcome (default: every year).
        merge_gap: the plan's merge gap in years (0: runs are never merged).
    """
    yrs = np.asarray(years)
    if yrs.ndim != 1 or len(yrs) == 0:
        raise ValueError("years must be a non-empty one-dimensional array")
    yrs = yrs.astype(int)
    if (np.diff(yrs) != 1).any():
        raise ValueError("years must be consecutive and increasing (mark missing outcomes with finite)")
    n = len(yrs)
    act = _as_bool(active, "active", n)
    fin = np.ones(n, bool) if finite is None else _as_bool(finite, "finite", n)
    if int(merge_gap) < 0:
        raise ValueError("merge_gap must be >= 0")
    phase = np.full(n, PHASE_NONE, dtype=object) if enso is None else enso_phase(enso)
    if len(phase) != n:
        raise ValueError("enso must have one value per year")
    ep = epochs(n)
    stratum = np.full(n, -1, dtype=int)
    group = np.full(n, -1, dtype=int)
    strata: List[Stratum] = []
    dropped: List[Dict] = []
    gcount = 0
    unit = fin & (phase != "")
    no_enso = fin & (phase == "")
    if no_enso.any():
        dropped.append({"phase": "", "reason": DROP_NO_ENSO, "n_active": int((no_enso & act).sum()),
                        "n_inactive": int((no_enso & ~act).sum()), "years": [int(y) for y in yrs[no_enso]]})
        group[no_enso] = gcount
        gcount += 1
    order = [PHASE_COLD, PHASE_NEUTRAL, PHASE_WARM, PHASE_NONE]
    for ph in order:
        pm = unit & (phase == ph)
        if not pm.any():
            continue
        counts = [(int((pm & (ep == h) & act).sum()), int((pm & (ep == h) & ~act).sum())) for h in (0, 1)]
        split = all(a >= MIN_STRATUM_ARM and c >= MIN_STRATUM_ARM for a, c in counts)
        if split:
            for h in (0, 1):
                m = pm & (ep == h)
                stratum[m] = len(strata)
                group[m] = gcount
                gcount += 1
                strata.append(Stratum(f"{ph}:{h}", ph, h, counts[h][0], counts[h][1]))
            continue
        na, nc = int((pm & act).sum()), int((pm & ~act).sum())
        group[pm] = gcount
        gcount += 1
        if na >= MIN_STRATUM_ARM and nc >= MIN_STRATUM_ARM:
            stratum[pm] = len(strata)
            strata.append(Stratum(ph, ph, None, na, nc))
        else:
            dropped.append({"phase": ph, "reason": DROP_NO_STRATUM_CONTROL, "n_active": na, "n_inactive": nc,
                            "years": [int(y) for y in yrs[pm]]})
    used = stratum >= 0
    n1, n0 = int((used & act).sum()), int((used & ~act).sum())
    runs = []
    for s, e in _runs(act & fin, merge_gap):
        w = int((used[s:e] & act[s:e]).sum())
        if w:
            runs.append((int(yrs[s]), int(yrs[e - 1]), w))
    ws = np.array([r[2] for r in runs], dtype=float)
    k_eff = float(ws.sum() ** 2 / (ws ** 2).sum()) if len(ws) else 0.0
    if n1 < MIN_YEARS or n0 < MIN_YEARS:
        reason = REASON_TOO_FEW_YEARS
    elif k_eff < MIN_K_EFF:
        reason = REASON_TOO_FEW_EPISODES
    else:
        reason = None
    return YearDesign(years=yrs, active=act, finite=fin, phase=phase, epoch=ep, stratum=stratum, group=group,
                      strata=tuple(strata), dropped=tuple(dropped), runs=tuple(runs), n_active=n1,
                      n_inactive=n0, k_eff=k_eff, reason=reason, merge_gap=int(merge_gap))


# --------------------------------------------------------------------------
# Outcome chain (item 4) and statistic (item 5)
# --------------------------------------------------------------------------


def _baseline_matrix(baselines, n: int) -> Optional[np.ndarray]:
    if baselines is None:
        return None
    from .season import _baseline_matrix as bm

    X = bm(baselines, n)
    return X if X.shape[1] else None


def leave_year_out(values, finite: np.ndarray) -> np.ndarray:
    """y_t minus the mean of the other finite years (season.leave_year_out_anomaly, by year, vectorised)."""
    y = np.asarray(values, dtype=float)
    out = np.full(len(y), np.nan)
    k = int(finite.sum())
    if k < 2:
        return out
    s = y[finite].sum()
    out[finite] = y[finite] - (s - y[finite]) / (k - 1)
    return out


def _residualise(y: np.ndarray, X: Optional[np.ndarray], finite: np.ndarray) -> np.ndarray:
    if X is None:
        return y
    out = np.full(len(y), np.nan)
    A = np.column_stack([np.ones(int(finite.sum())), X[finite]])
    coef, *_ = np.linalg.lstsq(A, y[finite], rcond=None)
    out[finite] = y[finite] - A @ coef + y[finite].mean()
    return out


def prepare_outcome(values, design: YearDesign, *, outcome_type: str, baselines=None) -> np.ndarray:
    """The tested outcome: leave-year-out anomaly then baselines removed (continuous); 0/1 (flags).

    Linear in the raw outcome for continuous outcomes (what effect removal relies on).
    """
    _check_type(outcome_type)
    y = np.asarray(values, dtype=float)
    if len(y) != len(design.years):
        raise ValueError("one outcome value per year")
    fin = design.finite
    if not np.isfinite(y[fin]).all():
        raise ValueError("the outcome must be finite on every year marked finite")
    if outcome_type == "flags":
        if not np.isin(y[fin], (0.0, 1.0)).all():
            raise ValueError("flags must be 0/1")
        out = np.full(len(y), np.nan)
        out[fin] = y[fin]
        return out
    X = _baseline_matrix(baselines, len(y))
    return _residualise(leave_year_out(y, fin), X, fin)


def statistic(design: YearDesign, outcome) -> float:
    """T of item 5 on a prepared outcome."""
    y = np.asarray(outcome, dtype=float)
    w = design.weights()
    u = design.used
    return float(np.dot(w[u], y[u]))


def pooled_risk_ratio(design: YearDesign, flags) -> float:
    """Active-standardised risk ratio: sum n1_s p1_s / sum n1_s p0_s (the card's number for yes/no)."""
    y = np.asarray(flags, dtype=float)
    num = den = 0.0
    for k, s in enumerate(design.strata):
        m = design.stratum == k
        num += s.n_active * y[m & design.active].mean()
        den += s.n_active * y[m & ~design.active].mean()
    if den == 0.0:
        return float("inf") if num > 0 else float("nan")
    return float(num / den)


def unstratified_difference(values, active, finite=None, *, outcome_type: str = "continuous") -> float:
    """The "without known channels" row: active mean minus inactive mean, no strata, no baselines.

    Continuous outcomes on the leave-year-out anomaly; flags on 0/1.
    """
    y = np.asarray(values, dtype=float)
    a = _as_bool(active, "active", len(y))
    fin = np.isfinite(y) if finite is None else (_as_bool(finite, "finite", len(y)) & np.isfinite(y))
    if outcome_type == "continuous":
        y = leave_year_out(y, fin)
    if not (fin & a).any() or not (fin & ~a).any():
        return float("nan")
    return float(y[fin & a].mean() - y[fin & ~a].mean())


def minimal_detectable_effect(design: YearDesign, sd: float, a: float, power: float = 0.8) -> float:
    """Shift detectable with ``power`` at one-sided level ``a`` if years were independent.

    ``(z_{1-a} + z_power) * sd * sqrt(sum w^2)``; the gate prints it; the envelope
    costs power on top of it (Y12 reports by how much).
    """
    from scipy.stats import norm

    w = design.weights()
    return float((norm.ppf(1.0 - float(a)) + norm.ppf(float(power))) * float(sd) * math.sqrt(float(np.dot(w, w))))


def _check_type(outcome_type) -> str:
    if outcome_type not in OUTCOME_TYPES:
        raise ValueError(f"outcome_type must be one of {OUTCOME_TYPES} for the year test")
    return outcome_type


def _check_side(side) -> str:
    if side not in SIDES:
        raise ValueError(f"side must be one of {SIDES}")
    return side


# --------------------------------------------------------------------------
# The null: prewhitened permutation over the envelope (item 6)
# --------------------------------------------------------------------------


class YearNull:
    """Permutation statistics of one design for one or more prepared columns.

    ``columns`` (n years x m) are prepared outcomes (or effect shapes put
    through the same chain). For every rho in the envelope and every
    permutation b, ``stats[r, b, j]`` is T* of column j. Columns share the
    permutations, which makes effect removal linear in r.
    """

    def __init__(self, design: YearDesign, columns, *, baselines=None, envelope: Sequence[float] = ENVELOPE):
        cols = np.asarray(columns, dtype=float)
        if cols.ndim == 1:
            cols = cols[:, None]
        n = len(design.years)
        if cols.shape[0] != n:
            raise ValueError("columns need one row per year")
        fin = design.finite
        self.design = design
        self.envelope = tuple(float(r) for r in envelope)
        if any(abs(r) >= 1 for r in self.envelope):
            raise ValueError("envelope members must lie in (-1, 1)")
        idx = np.flatnonzero(fin)
        self.nf = len(idx)
        c = cols[idx]
        if not np.isfinite(c).all():
            raise ValueError("columns must be finite on finite years")
        g = design.group[idx]
        # u: column minus the mean of its centring group (both arms together).
        u = c.copy()
        for gv in np.unique(g):
            m = g == gv
            u[m] -= u[m].mean(axis=0)
        self.u = u
        self.observed = design.weights()[idx] @ c  # (m,)
        starts = np.ones(self.nf, bool)
        starts[1:] = np.diff(design.years[idx]) != 1
        self.starts = starts
        X = _baseline_matrix(baselines, n)
        w = design.weights()[idx]
        if X is not None:
            A = np.column_stack([np.ones(self.nf), X[idx]])
            coef, *_ = np.linalg.lstsq(A, w, rcond=None)
            w = w - A @ coef  # M w (the constant part of M meets a zero-sum w)
        R = len(self.envelope)
        self.E = np.empty((R, self.nf, u.shape[1]))
        self.V = np.empty((R, self.nf))
        for k, rho in enumerate(self.envelope):
            e = self._innovations(u, rho)
            e = e - e.mean(axis=0)
            self.E[k] = e
            self.V[k] = self._rebuild_t(w, rho)

    def _innovations(self, u: np.ndarray, rho: float) -> np.ndarray:
        e = u.copy()
        e[1:] -= rho * u[:-1]
        s = self.starts
        e[s] = math.sqrt(1.0 - rho * rho) * u[s]
        return e

    def _rebuild_t(self, v: np.ndarray, rho: float) -> np.ndarray:
        """L' v for the rebuild u*_start = e_start / sqrt(1 - rho^2), u*_t = rho u*_(t-1) + e_t."""
        out = np.empty(self.nf)
        acc = 0.0
        for t in range(self.nf - 1, -1, -1):
            acc = v[t] + (rho * acc if (t + 1 < self.nf and not self.starts[t + 1]) else 0.0)
            out[t] = acc
        out[self.starts] /= math.sqrt(1.0 - rho * rho)
        return out

    def rho_hat(self, column: int = 0) -> float:
        u = self.u[:, column]
        den = float(np.dot(u, u))
        if den == 0.0:
            return 0.0
        pair = ~self.starts[1:]
        return float(np.dot(u[1:][pair], u[:-1][pair]) / den)

    def draw(self, n_perm: int, rng: np.random.Generator, *, stop=None) -> np.ndarray:
        """T* for ``n_perm`` permutations: array (rho, b, column).

        ``stop``: optional callable(stats_so_far) -> bool, checked after each
        chunk; the draw ends early when it returns True (simulation only).
        """
        R, n, m = self.E.shape
        base = np.broadcast_to(np.arange(n), (CHUNK, n))
        parts = []
        done = 0
        while done < n_perm:
            size = min(CHUNK, n_perm - done)
            P = rng.permuted(base, axis=1)[:size]
            VP = self.V[:, P]  # R x size x n
            parts.append(np.matmul(VP, self.E))  # R x size x m
            done += size
            if stop is not None and stop(np.concatenate(parts, axis=1)):
                break
        return np.concatenate(parts, axis=1) if parts else np.zeros((R, 0, m))


def _tol(t: float, stats: np.ndarray) -> float:
    return 1e-9 * (abs(t) + float(np.abs(stats).max(initial=0.0)) + 1e-12)


def _counts(stats: np.ndarray, t, side: str) -> np.ndarray:
    """#{T* at least as extreme as t} per rho; stats (R x B), t scalar or (R x B)-broadcastable."""
    tol = _tol(float(np.max(np.abs(t))), stats)
    if side == "greater":
        return np.sum(stats >= t - tol, axis=-1)
    return np.sum(stats <= t + tol, axis=-1)


def _p(count, b: int) -> np.ndarray:
    return (1.0 + np.asarray(count, dtype=float)) / (b + 1.0)


# --------------------------------------------------------------------------
# The test
# --------------------------------------------------------------------------


@dataclass
class YearTestResult:
    """One year test. p values are the largest over the envelope."""

    outcome_type: str
    side: str
    design: YearDesign
    estimate: Optional[float]
    p: Dict[str, Optional[float]]
    p_by_rho: Dict[str, Dict[float, float]]
    n_perm: int
    n_drawn: int
    rho_hat: Optional[float]
    flags: Tuple[str, ...]
    risk_ratio: Optional[float]
    unstratified: Optional[float]
    seed: Optional[int]

    @property
    def testable(self) -> bool:
        return self.design.testable

    @property
    def complete(self) -> bool:
        """False when a simulation stopped early (p then a lower bound above stop_level)."""
        return self.n_drawn >= self.n_perm

    @property
    def p_value(self) -> Optional[float]:
        """p on the registered side."""
        return self.p.get(self.side)

    @property
    def outside_envelope(self) -> bool:
        return FLAG_OUTSIDE_ENVELOPE in self.flags

    def to_dict(self) -> Dict:
        return {
            "method": "year_test",
            "outcome_type": self.outcome_type,
            "side": self.side,
            "design": self.design.to_dict(),
            "estimate": self.estimate,
            "statistic": "stratified_difference",
            "p": dict(self.p),
            "p_by_rho": {s: {f"{r:+.1f}": v for r, v in d.items()} for s, d in self.p_by_rho.items()},
            "envelope": list(ENVELOPE),
            "n_perm": int(self.n_perm),
            "smallest_p": smallest_p(self.n_perm),
            "rho_hat": self.rho_hat,
            "safety_limit": safety_limit(int(self.design.finite.sum())),
            "flags": list(self.flags),
            "risk_ratio": self.risk_ratio,
            "without_known_channels": self.unstratified,
            "validity": VALIDITY_SENTENCE,
            "seed_purpose": PERM_PURPOSE,
        }


def _finite_mask(y: np.ndarray, finite) -> np.ndarray:
    fin = np.isfinite(y)
    if finite is not None:
        fin &= _as_bool(finite, "finite", len(y))
    return fin


def _rng(seed, rng) -> Tuple[np.random.Generator, Optional[int]]:
    if rng is not None:
        return rng, None
    if seed is None:
        raise ValueError("the year test needs its yearperm seed (year_perm_seed) or an rng")
    return np.random.default_rng(int(seed)), int(seed)


def year_test(
    values,
    active,
    years,
    *,
    outcome_type: str = "continuous",
    side: str = "two-sided",
    enso=None,
    baselines=None,
    finite=None,
    merge_gap: int = 0,
    a_test: Optional[float] = None,
    n_perm: Optional[int] = None,
    seed: Optional[int] = None,
    rng: Optional[np.random.Generator] = None,
    stop_level: Optional[float] = None,
    stop_sides: Sequence[str] = ("greater", "less"),
) -> YearTestResult:
    """The year test of A3.1 for one (calendar, outcome).

    ``side`` is the registered side (A3.5); both one-sided p values and the
    two-sided p (twice the smaller one-sided p, per rho, then the largest over
    the envelope) are always reported. ``n_perm`` defaults to
    :func:`production_b`(a_test). ``stop_level`` (simulation only) stops drawing once
    the p of every side in ``stop_sides`` is certainly above it; the decision
    "p <= stop_level" on those sides is then the same as with all B
    permutations (same chunks, same draws). p values above it are then lower
    bounds (``complete`` is False).
    """
    _check_type(outcome_type)
    side = _check_side(side)
    y = np.asarray(values, dtype=float)
    fin = _finite_mask(y, finite)
    design = year_design(active, years, enso=enso, finite=fin, merge_gap=merge_gap)
    B = production_b(a_test) if n_perm is None else int(n_perm)
    if B < 1:
        raise ValueError("n_perm must be at least 1")
    unstrat = unstratified_difference(y, design.active, fin, outcome_type=outcome_type)
    if not design.testable:
        return YearTestResult(outcome_type, side, design, None, {"greater": None, "less": None, "two-sided": None},
                              {}, B, 0, None, (), None, unstrat, seed)
    prepared = prepare_outcome(y, design, outcome_type=outcome_type, baselines=baselines)
    t = statistic(design, prepared)
    null = YearNull(design, prepared, baselines=baselines)
    gen, used_seed = _rng(seed, rng)
    stop = None
    if stop_level is not None:
        lim = float(stop_level) * (B + 1.0) - 1.0
        lim2 = 0.5 * float(stop_level) * (B + 1.0) - 1.0
        for sd in stop_sides:
            _check_side(sd)

        def stop(st):
            s = st[:, :, 0]
            cg, cl = _counts(s, t, "greater"), _counts(s, t, "less")
            dec = {"greater": bool((cg > lim).any()), "less": bool((cl > lim).any()),
                   "two-sided": bool(((cg > lim2) & (cl > lim2)).any())}
            return all(dec[sd] for sd in stop_sides)

    stats = null.draw(B, gen, stop=stop)[:, :, 0]
    nd = stats.shape[1]
    pg = _p(_counts(stats, t, "greater"), B)
    pl = _p(_counts(stats, t, "less"), B)
    p2 = np.minimum(1.0, 2.0 * np.minimum(pg, pl))
    env = null.envelope
    p = {"greater": float(pg.max()), "less": float(pl.max()), "two-sided": float(p2.max())}
    by = {"greater": dict(zip(env, map(float, pg))), "less": dict(zip(env, map(float, pl))),
          "two-sided": dict(zip(env, map(float, p2)))}
    rh = null.rho_hat()
    flags = (FLAG_OUTSIDE_ENVELOPE,) if abs(rh) > safety_limit(null.nf) else ()
    rr = pooled_risk_ratio(design, prepared) if outcome_type == "flags" else None
    return YearTestResult(outcome_type, side, design, t, p, by, B, nd, rh, flags, rr, unstrat, used_seed)


# --------------------------------------------------------------------------
# Exclusion and X95 on yearly grids (A3.2)
# --------------------------------------------------------------------------


def _claim_dirs(side: str) -> List[str]:
    return ["greater", "less"] if side == "two-sided" else [side]


class YearRemoval:
    """Effect removal for one yearly test, at any r, on one fixed set of permutations.

    Continuous: column 0 is the prepared outcome, column 1 the active
    indicator through the same chain (h). Removing a shift r in the claim
    direction "greater" is ``y - r a`` (tested "less"); in "less", ``y + r a``
    (tested "greater"). Flags: one extra column per "yes" year of each arm a
    claim may thin; thinning k at ratio r removes year j when its uniform
    ``U[k, j] >= 1 / r`` (nested in r).
    """

    def __init__(self, values, design: YearDesign, *, outcome_type: str, side: str, baselines=None,
                 n_perm: int, rng: np.random.Generator, thinning_rng: Optional[np.random.Generator] = None,
                 n_thin: int = N_THIN, stop_level: Optional[float] = None, stop_r: Optional[float] = None):
        self.design = design
        self.outcome_type = _check_type(outcome_type)
        self.side = _check_side(side)
        self.n_perm = int(n_perm)
        y = np.asarray(values, dtype=float)
        prepared = prepare_outcome(y, design, outcome_type=outcome_type, baselines=baselines)
        cols = [prepared]
        self.thin = outcome_type == "flags"
        self.thin_cols: Dict[str, np.ndarray] = {}
        self.U: Dict[str, np.ndarray] = {}
        fin = design.finite
        if not self.thin:
            a = np.where(fin, design.active.astype(float), np.nan)
            cols.append(prepare_outcome(np.where(fin, a, 0.0), design, outcome_type="continuous", baselines=baselines))
            cols[-1][~fin] = np.nan
        else:
            if thinning_rng is None:
                raise ValueError("yes/no exclusion needs the test's thinning stream")
            self.n_thin = int(n_thin)
            for d in _claim_dirs(self.side):
                arm = design.active if d == "greater" else ~design.active
                yes = np.flatnonzero(fin & design.used & arm & (np.nan_to_num(y) == 1.0))
                first = len(cols)
                for j in yes:
                    e = np.zeros(len(y))
                    e[j] = 1.0
                    cols.append(e)
                self.thin_cols[d] = np.arange(first, len(cols))
                # one uniform per thinned year and repetition, in year order
                self.U[d] = thinning_rng.random((self.n_thin, len(yes)))
        C = np.column_stack(cols)
        C[~fin] = 0.0
        self.null = YearNull(design, C, baselines=baselines if not self.thin else None)
        self.T = self.null.observed
        stop = None
        if stop_level is not None and stop_r is not None:
            lim = float(stop_level) * (self.n_perm + 1.0) - 1.0

            lim2 = 0.5 * float(stop_level) * (self.n_perm + 1.0) - 1.0

            running: Dict[str, np.ndarray] = {}
            seen = [0]

            def stop(st):
                # p_ex = max over claim directions, so one decided direction decides.
                # Counts are added chunk by chunk (only the new permutations are read).
                new = st[:, seen[0]:, :]
                seen[0] = st.shape[1]
                for d in _claim_dirs(self.side):
                    running[d] = running.get(d, 0) + self._counts_at(stop_r, d, new)
                    c = running[d]  # rho x thinnings
                    if not self.thin:
                        if (c > lim).any():
                            return True
                    elif int((c > lim2).any(axis=0).sum()) >= (c.shape[1] + 1) // 2:
                        return True  # twice the median is certainly above stop_level
                return False
        self.S = self.null.draw(self.n_perm, rng, stop=stop)
        self.n_drawn = self.S.shape[1]

    # counts per (rho[, thinning]) at claim-scale r in claim direction d
    def _coefs(self, r: float, d: str) -> np.ndarray:
        if not self.thin:
            return np.array([r if d == "greater" else -r])
        return (self.U[d] >= 1.0 / r).astype(float)  # n_thin x m_d

    def _counts_at(self, r: float, d: str, S: Optional[np.ndarray] = None) -> np.ndarray:
        test_side = "less" if d == "greater" else "greater"
        S = self.S if S is None else S
        T = self.T
        if not self.thin:
            c = self._coefs(r, d)[0]
            t = T[0] - c * T[1]
            s = S[:, :, 0] - c * S[:, :, 1]
            return _counts(s, t, test_side)[:, None]  # R x 1
        cols = self.thin_cols[d]
        C = self._coefs(r, d)  # K x m
        t = T[0] - C @ T[cols]  # K
        out = np.empty((S.shape[0], C.shape[0]), dtype=np.int64)
        for k0 in range(0, S.shape[1], 20_000):
            blk = S[:, k0:k0 + 20_000, :]
            s = blk[:, :, 0][:, :, None] - blk[:, :, cols] @ C.T  # R x b x K
            tol = _tol(float(np.max(np.abs(t))), s)
            if test_side == "greater":
                c = np.sum(s >= t[None, None, :] - tol, axis=1)
            else:
                c = np.sum(s <= t[None, None, :] + tol, axis=1)
            out = c if k0 == 0 else out + c
        return out

    def shifted(self, delta: float) -> "YearRemoval":
        """The same removal for the outcome ``y + delta * active`` (continuous; same permutations).

        The chain is linear, so this is exact; simulations use it to plant
        several effects on one draw.
        """
        if self.thin:
            raise ValueError("shifted() is for continuous outcomes")
        import copy

        out = copy.copy(self)
        out.S = self.S.copy()
        out.S[:, :, 0] += float(delta) * self.S[:, :, 1]
        out.T = self.T.copy()
        out.T[0] += float(delta) * self.T[1]
        return out

    def p_direction(self, r: float, d: str) -> float:
        """Exclusion p for H0 "effect in direction d is at least r" (claim scale)."""
        p = _p(self._counts_at(float(r), d), self.n_perm)  # R x K
        pk = p.max(axis=0)
        if not self.thin:
            return float(pk[0])
        return float(min(1.0, 2.0 * np.median(pk)))

    def p_exclusion(self, r: float) -> float:
        return max(self.p_direction(r, d) for d in _claim_dirs(self.side))


def _limit_search(pfun, grid: np.ndarray, a: float, steps: int = BISECT_STEPS):
    """A3.2 item 3: smallest grid r with p <= a there and at every larger grid value, bisected downwards.

    Returns (value, at_grid_floor, p_on_grid, monotone).
    """
    ps = [pfun(float(x)) for x in grid]
    ok = [p <= a for p in ps]
    i = len(grid)
    while i > 0 and ok[i - 1]:
        i -= 1
    monotone = all(ps[j + 1] <= ps[j] + 1e-15 for j in range(len(ps) - 1))
    if i == len(grid):
        return None, False, ps, monotone
    if i == 0:
        return float(grid[0]), True, ps, monotone
    lo, hi = float(grid[i - 1]), float(grid[i])
    for _ in range(int(steps)):
        mid = 0.5 * (lo + hi)
        if mid <= lo or mid >= hi:
            break
        if pfun(mid) <= a:
            hi = mid
        else:
            lo = mid
    return hi, False, ps, monotone


@dataclass
class YearExclusionResult:
    """Exclusion p at the SESOI, X95 and X-strict of one yearly test (A3.2)."""

    outcome_type: str
    side: str
    sesoi: Optional[float]
    p_exclusion: Optional[float]
    x95: _ex.LimitRecord
    x_strict: Optional[_ex.LimitRecord]
    a_test: Optional[float]
    grid: Tuple[float, ...]
    k_runs: int
    k_eff: float
    expected_yes: Optional[float]
    n_perm: int
    n_thin: int
    p_on_grid: Dict[str, List[float]] = field(default_factory=dict)
    monotone: bool = True
    design: Optional[YearDesign] = field(default=None, repr=False)

    def can_limit(self, a: float) -> bool:
        if self.design is None or not self.design.testable:
            return False
        if self.outcome_type == "flags":
            return self.expected_yes is not None and self.expected_yes >= _ex.min_informative(a)
        return True

    def excluded(self, a: float) -> bool:
        """A steady effect of at least the SESOI is rejected at ``a`` (needed for E)."""
        return self.p_exclusion is not None and self.p_exclusion <= float(a) and self.can_limit(a)

    def card_lines(self) -> List[str]:
        return _ex.card_lines(self.x95, max(self.k_runs, 1))

    def to_dict(self) -> Dict:
        return {
            "method": "year_exclusion_by_effect_removal",
            "outcome_type": self.outcome_type,
            "effect_model": _ex.EFFECT_MODELS[self.outcome_type],
            "scale": _ex.SCALES[self.outcome_type],
            "side": self.side,
            "sesoi": self.sesoi,
            "p_exclusion": self.p_exclusion,
            "x95": self.x95.to_dict(),
            "x_strict": None if self.x_strict is None else self.x_strict.to_dict(),
            "a_test": self.a_test,
            "grid": list(self.grid),
            "k_runs": self.k_runs,
            "k_eff": self.k_eff,
            "expected_yes_smaller_arm": self.expected_yes,
            "n_perm": self.n_perm,
            "n_thin": self.n_thin,
            "aggregation": "twice_median" if self.n_thin > 1 else "single",
            "envelope_aggregation": "max_over_envelope",
            "p_on_grid": {k: list(v) for k, v in self.p_on_grid.items()},
            "monotone_on_grid": self.monotone,
            "not_addressed_share": _ex.not_addressed_share(self.k_runs) if self.k_runs else None,
            "validity": VALIDITY_SENTENCE,
        }


def expected_yes(design: YearDesign, base_rate: float) -> float:
    """A3.2 item 5: expected "yes" years in the smaller arm after thinning at the SESOI."""
    p = float(base_rate)
    if not 0.0 < p < 1.0:
        raise ValueError("base_rate must lie in (0, 1)")
    return float(min(design.n_active, design.n_inactive) * p)


def year_exclusion(
    values,
    active,
    years,
    *,
    outcome_type: str,
    side: str,
    sesoi: Optional[float],
    grid,
    a_test: Optional[float] = None,
    enso=None,
    baselines=None,
    finite=None,
    merge_gap: int = 0,
    base_rate: Optional[float] = None,
    n_perm: Optional[int] = None,
    seed: Optional[int] = None,
    rng: Optional[np.random.Generator] = None,
    thinning_rng: Optional[np.random.Generator] = None,
    n_thin: int = N_THIN,
    steps: int = BISECT_STEPS,
    limits: bool = True,
    stop_level: Optional[float] = None,
) -> YearExclusionResult:
    """Exclusion p at the SESOI, X95 and X-strict of A3.2 for one yearly test.

    ``sesoi`` and ``grid`` are on the claim scale (positive shift; risk ratio
    above 1). ``base_rate`` (flags) is the plan's, from a named publication.
    ``limits=False`` skips X95 and X-strict (simulation of the exclusion p only);
    ``stop_level`` (simulation only, with ``limits=False``) stops drawing once the
    exclusion p at the SESOI is certainly above it.
    """
    _check_type(outcome_type)
    side = _check_side(side)
    g = _ex._check_grid(grid, "flags" if outcome_type == "flags" else "continuous")
    y = np.asarray(values, dtype=float)
    fin = _finite_mask(y, finite)
    design = year_design(active, years, enso=enso, finite=fin, merge_gap=merge_gap)
    B = production_b(a_test) if n_perm is None else int(n_perm)
    levels = [X95_ALPHA] + ([float(a_test)] if a_test is not None else [])
    scale = _ex.SCALES[outcome_type]
    ey = None
    if outcome_type == "flags" and base_rate is not None:
        ey = expected_yes(design, base_rate)

    def info_for(a: float) -> Tuple[int, int, Optional[str]]:
        if not design.testable:
            return min(design.n_active, design.n_inactive), MIN_YEARS, REASON_NOT_TESTABLE
        if outcome_type == "flags":
            need = _ex.min_informative(a)
            if ey is None:
                return 0, need, REASON_NO_BASE_RATE
            return int(math.floor(ey + 1e-12)), need, (None if ey >= need else REASON_TOO_FEW_YES)
        return min(design.n_active, design.n_inactive), MIN_YEARS, None

    def unbounded(a, reason, info, need):
        return _ex.LimitRecord(alpha=float(a), value=None, unbounded=True, reason=reason, scale=scale,
                               informative=int(info), required_informative=int(need), k_eff=float(design.k_eff))

    s = None if sesoi is None else _ex._check_magnitude(sesoi, "flags" if outcome_type == "flags" else "continuous")
    blocked = {a: info_for(a) for a in levels}
    if all(r[2] is not None for r in blocked.values()) and (s is None or blocked[X95_ALPHA][2] is not None):
        recs = [unbounded(a, *[blocked[a][2], blocked[a][0], blocked[a][1]]) for a in levels]
        return YearExclusionResult(outcome_type, side, s, None, recs[0], recs[1] if len(recs) > 1 else None,
                                   None if a_test is None else float(a_test), tuple(map(float, g)),
                                   design.n_runs, design.k_eff, ey, B, n_thin if outcome_type == "flags" else 1,
                                   design=design)
    gen, _ = _rng(seed, rng)
    er = YearRemoval(y, design, outcome_type=outcome_type, side=side, baselines=baselines, n_perm=B, rng=gen,
                     thinning_rng=thinning_rng, n_thin=n_thin,
                     stop_level=None if limits else stop_level, stop_r=s)
    # p at the SESOI only where the minimum-information rule allows an E at X95 level
    p_ex = er.p_exclusion(s) if (s is not None and blocked[X95_ALPHA][2] is None) else None
    recs = []
    p_grid: Dict[str, List[float]] = {}
    mono = True
    for a in levels:
        info, need, reason = blocked[a]
        if reason is not None or not limits:
            recs.append(unbounded(a, reason or "not_computed", info, need))
            continue
        vals, floors, unb = [], [], False
        for d in _claim_dirs(side):
            v, fl, ps, m = _limit_search(lambda r, d=d: er.p_direction(r, d), g, a, steps)
            p_grid.setdefault(d, ps)
            mono = mono and m
            if v is None:
                unb = True
            vals.append(v)
            floors.append(fl)
        if unb:
            recs.append(unbounded(a, _ex.REASON_NOT_REACHED, info, need))
        else:
            recs.append(_ex.LimitRecord(alpha=float(a), value=float(max(vals)), unbounded=False, reason=None,
                                        scale=scale, informative=int(info), required_informative=int(need),
                                        k_eff=float(design.k_eff), at_grid_floor=all(floors)))
    return YearExclusionResult(outcome_type, side, s, p_ex, recs[0], recs[1] if len(recs) > 1 else None,
                               None if a_test is None else float(a_test), tuple(map(float, g)), design.n_runs,
                               design.k_eff, ey, B, er.n_thin if er.thin else 1, p_grid, mono, design)
