"""The testability gate, second version (ADR-008 sections 1.1, 2.2, 3.3, 4.4; amends ADR-007 5.1).

Work package WP-94. Re-specifies the gate part of ADR-007 WP-68. The gate
reads the **calendar and the plan only**, never an outcome, so it runs and its
record is hashed before any outcome is loaded.

Two abilities, as in ADR-007 5.1:

* **Can support** (confirm period): G1 to G3 and G7; G4 as K_eff >= 8 on the
  confirm-period blocks (section 1.1 item 9); G5 as "the smallest attainable
  p of the block sign-flip test is at or below the test's fixed threshold
  a_test" (section 3.2 rule 4); G6 for events (at least 5 events expected on
  the active and on the control bars of the used blocks).
* **Can limit** (whole period): G1 to G3, G7; K_eff >= 8 on the whole-period
  blocks; a SESOI exists (section 7.2); the **predicted** number I of
  informative blocks at r = SESOI, from the plan's base rate, meets the
  minimum-information rule at 0.05 (section 2.2: "the gate predicts I from
  the plan's base rate and reports 'can limit: no' in advance"); G6 for
  events. Whether X-strict can be bounded (I >= ceil(log2(1 / a_test))) is
  reported as can_limit_strict.

The control blocks are the ones the primary test will read: neighbour blocks
or, for a season-linked calendar, same-season windows (core/stats/season.py
control_design()). The gate and the test therefore report the same side and
the same number of used blocks (S-15, B6).

The gate also computes **P(S given SESOI)**: the probability that the primary
test reaches a_test on the confirm blocks when a steady effect equal to the
SESOI is planted in the bars, under the plan's noise model (Normal with the
plan's noise_sd for continuous and log_ratio outcomes; Poisson at the plan's
base rate for events; Bernoulli for flags). Below 0.8 the test carries
support_underpowered (A-07, W4). When the plan gives no noise model or no
SESOI the probability is unknown and the flag is set (the conservative
choice: support is not shown to be reachable).

supportability_table() gives, per domain and before a batch closes, how
many tests can support, can only limit, or are untestable (S-09).

No outcome, no network, no thread.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple, Union

import numpy as np

from ..stats import blocks as _blocks
from ..stats import exclusion as _exclusion
from ..stats import season as _season

__all__ = [
    "GATE_SCHEMA",
    "MIN_K_EFF",
    "MIN_EXPECTED_EVENTS",
    "POWER_TARGET",
    "FAMILY_MIN_LEVEL",
    "GOOD_GRADES",
    "GateError",
    "GateSpec",
    "GateResult",
    "run_gate",
    "power_at_sesoi",
    "supportability_table",
]

GATE_SCHEMA = "validity-gate/2"
MIN_K_EFF = _blocks.MIN_K_EFF
#: ADR-007 G6: events expected on each side.
MIN_EXPECTED_EVENTS = 5.0
#: A-07: below this P(S given SESOI) the test is support_underpowered.
POWER_TARGET = 0.8
#: ADR-008 7.1: entry level L2 (same value as core/rules/levels.py).
FAMILY_MIN_LEVEL = 2
GOOD_GRADES = ("A", "B")
#: Power simulation replications by default.
POWER_REPS = 200
#: Above this many used blocks the power simulation uses Monte Carlo sign flips.
_EXACT_MAX = 12


class GateError(ValueError):
    """A gate input that the plan should have fixed (side, type, base rate)."""


@dataclass(frozen=True)
class GateSpec:
    """What the gate needs from the plan and the rule (no outcome).

    side: "greater", "less" or "two-sided" (from the claimed direction).
    a_test: the test's fixed threshold alpha_b / n_b (stored at batch close,
        or the value for the current n_b before close).
    base_rate: events per bar (events) or P(yes) per bar (flags).
    noise_sd: standard deviation of one bar (continuous, log_ratio), for
        P(S given SESOI) only.
    national_chart_ok: None unless the test is on a national chart (G7).
    """

    test_id: str
    side: str
    outcome_type: str
    a_test: float
    merge_gap: Any
    guard_bars: int = 0
    sesoi: Optional[float] = None
    base_rate: Optional[float] = None
    noise_sd: Optional[float] = None
    level: int = 0
    encoded: bool = True
    data_grade: str = "A"
    national_chart_ok: Optional[bool] = None
    plan_seed: Union[int, str] = 0
    power_reps: int = POWER_REPS

    def check(self) -> None:
        if self.side not in _blocks.ALTERNATIVES:
            raise GateError(f"side must be one of {_blocks.ALTERNATIVES} (there is no default side)")
        if self.outcome_type not in _blocks.OUTCOME_TYPES:
            raise GateError(f"outcome_type must be one of {_blocks.OUTCOME_TYPES}")
        if not 0.0 < float(self.a_test) < 1.0:
            raise GateError("a_test must lie in (0, 1)")
        if self.outcome_type in ("events", "flags"):
            if self.base_rate is None or not float(self.base_rate) > 0.0:
                raise GateError("events and flags need the plan's base rate (section 2.2)")
            if self.outcome_type == "flags" and not float(self.base_rate) < 1.0:
                raise GateError("a flag base rate must lie in (0, 1)")
        if self.sesoi is not None:
            s = float(self.sesoi)
            if self.outcome_type == "continuous" and not s > 0.0:
                raise GateError("a continuous SESOI is a positive shift")
            if self.outcome_type != "continuous" and not s > 1.0:
                raise GateError("a ratio SESOI is above 1")
        if self.noise_sd is not None and not float(self.noise_sd) > 0.0:
            raise GateError("noise_sd must be positive")


@dataclass(frozen=True)
class GateResult:
    """The gate record of one test; hashed into gate.json before outcomes."""

    test_id: str
    side: str
    outcome_type: str
    a_test: float
    can_support: bool
    can_limit: bool
    can_limit_strict: bool
    support_failed: Tuple[str, ...]
    limit_failed: Tuple[str, ...]
    untestable: bool
    untestable_reason: Optional[str]
    all_blocks_dropped: bool
    confirm: Dict[str, Any]
    full: Dict[str, Any]
    season: Dict[str, Any]
    predicted_informative: Optional[float]
    required_informative: int
    required_informative_strict: int
    expected_events: Optional[Dict[str, float]]
    p_support_at_sesoi: Optional[float]
    support_underpowered: bool
    blocks_needed_support: int

    @property
    def category(self) -> str:
        """support, limit_only or untestable (the supportability table's column)."""
        if self.can_support:
            return "support"
        if self.can_limit:
            return "limit_only"
        return "untestable"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema": GATE_SCHEMA,
            "test_id": self.test_id,
            "side": self.side,
            "outcome_type": self.outcome_type,
            "a_test": self.a_test,
            "can_support": self.can_support,
            "can_limit": self.can_limit,
            "can_limit_strict": self.can_limit_strict,
            "support_failed": list(self.support_failed),
            "limit_failed": list(self.limit_failed),
            "untestable": self.untestable,
            "untestable_reason": self.untestable_reason,
            "all_blocks_dropped": self.all_blocks_dropped,
            "category": self.category,
            "confirm": self.confirm,
            "full": self.full,
            "season": self.season,
            "predicted_informative": self.predicted_informative,
            "required_informative": self.required_informative,
            "required_informative_strict": self.required_informative_strict,
            "expected_events": self.expected_events,
            "p_support_at_sesoi": self.p_support_at_sesoi,
            "support_underpowered": self.support_underpowered,
            "blocks_needed_support": self.blocks_needed_support,
        }

    def to_bytes(self) -> bytes:
        """Canonical JSON (the bytes written to gate.json)."""
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"), default=_jsonable).encode()

    @property
    def gate_hash(self) -> str:
        return hashlib.sha256(self.to_bytes()).hexdigest()


def _jsonable(x: Any) -> Any:
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (np.floating,)):
        return float(x)
    if isinstance(x, np.ndarray):
        return x.tolist()
    return str(x)


def _blocks_needed(a_test: float, side: str) -> int:
    mult = 2.0 if side == "two-sided" else 1.0
    k = 0
    while mult * 2.0 ** (-k) > a_test:
        k += 1
    return k


def _expected_events(design: _blocks.BlockDesign, rate: float) -> Dict[str, float]:
    used = design.used_blocks
    return {
        "active": float(rate * sum(b.n_active for b in used)),
        "control": float(rate * sum(b.n_control for b in used)),
    }


def _power_seed(plan_seed: Union[int, str], test_id: str) -> int:
    digest = hashlib.sha256(f"{plan_seed}|{test_id}|gate_power".encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big")


def _sign_flip_p(d: np.ndarray, w: np.ndarray, side: str, a_test: float, rng: np.random.Generator) -> float:
    if len(d) <= _EXACT_MAX:
        return _blocks.weighted_sign_flip(d, w, alternative=side).p_value
    n_draws = int(min(200_000, max(1999, math.ceil(50.0 / a_test))))
    wd = w * d
    obs = float(wd.sum())
    tol = 1e-12 * (float(np.abs(wd).sum()) + 1.0)
    signs = rng.choice(np.array([-1.0, 1.0]), size=(n_draws, len(d)))
    stats = signs @ wd
    if side == "greater":
        c = int(np.sum(stats >= obs - tol))
    elif side == "less":
        c = int(np.sum(stats <= obs + tol))
    else:
        c = int(np.sum(np.abs(stats) >= abs(obs) - tol))
    return (c + 1) / (n_draws + 1)


def power_at_sesoi(design: _blocks.BlockDesign, spec: GateSpec,
                   rng: Optional[np.random.Generator] = None) -> Optional[float]:
    """P(primary p <= a_test) with a steady effect equal to the SESOI planted in the bars.

    None when the plan lacks the noise model or the SESOI. The effect is
    planted in the claimed direction (the upward one for two-sided).
    """
    spec.check()
    if spec.sesoi is None or design.n_used == 0:
        return None if spec.sesoi is None else 0.0
    t = spec.outcome_type
    if t in ("continuous", "log_ratio") and spec.noise_sd is None:
        return None
    if design.p_min(spec.side) > spec.a_test:
        return 0.0
    rng = rng if rng is not None else np.random.default_rng(_power_seed(spec.plan_seed, spec.test_id))
    n = design.n_bars
    act = np.zeros(n, dtype=bool)
    for b in design.used_blocks:
        act[b.active] = True
    down = spec.side == "less"
    s = float(spec.sesoi)
    hits = 0
    reps = int(spec.power_reps)
    if reps < 1:
        raise GateError("power_reps must be at least 1")
    for _ in range(reps):
        if t == "continuous":
            y = rng.normal(0.0, float(spec.noise_sd), n)
            y[act] += -s if down else s
        elif t == "log_ratio":
            y = rng.normal(0.0, float(spec.noise_sd), n)
            y[act] += -math.log(s) if down else math.log(s)
        elif t == "events":
            lam = np.full(n, float(spec.base_rate))
            lam[act] *= (1.0 / s) if down else s
            y = rng.poisson(lam).astype(float)
        else:
            p = np.full(n, float(spec.base_rate))
            p[act] = np.minimum(1.0, p[act] * ((1.0 / s) if down else s))
            y = (rng.random(n) < p).astype(float)
        diffs = _blocks.block_differences(design, y, outcome_type=t)
        if _sign_flip_p(diffs.d, diffs.w, spec.side, float(spec.a_test), rng) <= float(spec.a_test):
            hits += 1
    return hits / reps


def _block_summary(sd: _season.SeasonDesign, side: str) -> Dict[str, Any]:
    out = sd.blocks.gate_summary(side)
    out["drop_counts"] = dict(out["drop_counts"])
    out["season_drop_counts"] = dict(sd.season_drop_counts)
    out["control_kind"] = sd.control_kind
    return out


def run_gate(calendar, dates, confirm, spec: GateSpec) -> GateResult:
    """Run the gate of one test from its calendar, the grid dates and the plan.

    Args:
        calendar: Active bars (boolean, one per bar of the vintage's grid).
        dates: The grid's instants (for season_r2 and same-season windows).
        confirm: Boolean mask of the confirm-period bars (the plan's split).
        spec: The plan's fixed inputs for this test (GateSpec).
    """
    spec.check()
    cal = np.asarray(calendar, dtype=bool).ravel()
    conf = np.asarray(confirm, dtype=bool).ravel()
    if conf.shape != cal.shape:
        raise GateError("confirm mask and calendar must have the same length")
    side, t, a = spec.side, spec.outcome_type, float(spec.a_test)

    common: List[str] = []
    if not spec.encoded:
        common.append("not_encoded")
    if int(spec.level) < FAMILY_MIN_LEVEL:
        common.append("not_operationalised")
    if str(spec.data_grade) not in GOOD_GRADES:
        common.append("data_quality")
    if spec.national_chart_ok is False:
        common.append("chart_time")

    full_sd = _season.control_design(cal, dates, merge_gap=spec.merge_gap, guard_bars=spec.guard_bars)
    conf_sd = _season.control_design(cal, dates, merge_gap=spec.merge_gap, guard_bars=spec.guard_bars,
                                     available=conf)
    full_d, conf_d = full_sd.blocks, conf_sd.blocks

    # ---- can support (confirm period)
    sup = list(common)
    if conf_d.k_eff < MIN_K_EFF:
        sup.append("season" if conf_sd.untestable_reason else "too_few_episodes")
    if conf_d.p_min(side) > a:
        sup.append("p_not_attainable")
    ev_conf = _expected_events(conf_d, float(spec.base_rate)) if t == "events" else None
    if ev_conf is not None and min(ev_conf.values()) < MIN_EXPECTED_EVENTS:
        sup.append("too_few_events")

    # ---- can limit (whole period)
    lim = list(common)
    if full_d.k_eff < MIN_K_EFF:
        lim.append("season" if full_sd.untestable_reason else "too_few_episodes")
    need = _exclusion.min_informative(_exclusion.X95_ALPHA)
    need_strict = _exclusion.min_informative(a)
    info: Optional[float] = None
    if spec.sesoi is None:
        lim.append("no_sesoi")
    else:
        rate = 1.0 if t in ("continuous", "log_ratio") else float(spec.base_rate)
        info = _exclusion.expected_informative(full_d, rate, float(spec.sesoi), outcome_type=t, side=side)
        if math.floor(info + 1e-9) < need:
            lim.append("too_little_information")
    ev_full = _expected_events(full_d, float(spec.base_rate)) if t == "events" else None
    if ev_full is not None and min(ev_full.values()) < MIN_EXPECTED_EVENTS:
        lim.append("too_few_events")

    can_support, can_limit = not sup, not lim
    can_limit_strict = can_limit and info is not None and math.floor(info + 1e-9) >= need_strict
    all_dropped = full_d.n_used == 0
    untestable = (not can_support and not can_limit) or all_dropped
    reason: Optional[str] = None
    if untestable:
        if common:
            reason = common[0]
        elif all_dropped:
            reason = "season" if full_sd.season_linked else "no_clean_control"
        elif full_sd.untestable_reason:
            reason = "season"
        else:
            # The limit ability's first failure names the reason (the whole period is the wider one).
            reason = lim[0] if lim else sup[0]
        can_support = can_limit = can_limit_strict = False

    power = power_at_sesoi(conf_d, spec) if can_support else (0.0 if spec.sesoi is not None else None)
    underpowered = power is None or power < POWER_TARGET

    events = None
    if ev_full is not None:
        events = {"confirm_active": ev_conf["active"], "confirm_control": ev_conf["control"],
                  "full_active": ev_full["active"], "full_control": ev_full["control"]}
    return GateResult(
        test_id=spec.test_id,
        side=side,
        outcome_type=t,
        a_test=a,
        can_support=can_support,
        can_limit=can_limit,
        can_limit_strict=bool(can_limit_strict),
        support_failed=tuple(sup),
        limit_failed=tuple(lim),
        untestable=untestable,
        untestable_reason=reason,
        all_blocks_dropped=all_dropped,
        confirm=_block_summary(conf_sd, side),
        full=_block_summary(full_sd, side),
        season={"season_r2": full_sd.season_r2, "season_linked": full_sd.season_linked,
                "placebo_shift": full_sd.placebo_shift},
        predicted_informative=info,
        required_informative=need,
        required_informative_strict=need_strict,
        expected_events=events,
        p_support_at_sesoi=power,
        support_underpowered=underpowered,
        blocks_needed_support=_blocks_needed(a, side),
    )


def supportability_table(results: Iterable[GateResult]) -> Dict[str, Any]:
    """How many tests can support, can only limit or are untestable (S-09).

    Printed per domain before a batch closes, with a_test for the current n_b.
    Same keys as core/validity/family.py supportability_table(); here the
    categories come from the gate's two abilities, so the table and the gate
    can never disagree.
    """
    counts = {"support": 0, "limit_only": 0, "untestable": 0}
    rows = []
    a_values = set()
    for g in results:
        counts[g.category] += 1
        a_values.add(g.a_test)
        rows.append({"test_id": g.test_id, "category": g.category, "a_test": g.a_test,
                     "blocks_needed_support": g.blocks_needed_support,
                     "blocks_used_confirm": g.confirm["n_used"],
                     "informative_needed_limit": g.required_informative,
                     "predicted_informative": g.predicted_informative,
                     "p_support_at_sesoi": g.p_support_at_sesoi,
                     "reason": g.untestable_reason})
    a_test = a_values.pop() if len(a_values) == 1 else None
    return {"a_test": a_test, "counts": counts, "rows": rows}
