"""Evaluate a rule at every step of a time grid, fast enough for a parameter sweep.

Positions are computed once per grid step. Each distinct predicate leaf
(predicate plus its bound parameters) is evaluated once over the whole grid
and cached, so a sweep over an orb re-evaluates only the leaves that use
the orb. The boolean tree is then combined with numpy, and the rule's
``window`` widens each firing to the steps whose effect window contains it.
"""

import json
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

import numpy as np
import pandas as pd

from .context import EvalContext, Location, Sky, get_engine
from .engine import RuleNotEvaluable
from .predicates import PREDICATES
from .schema import AllOf, AnyOf, AtLeast, Leaf, NotOf, Rule, Window
from .strength import strength_value

UNIT_DAYS = {
    "hours": 1.0 / 24.0,
    "days": 1.0,
    "weeks": 7.0,
    "months": 30.436875,
    "years": 365.25,
}


def leaf_key(leaf: Leaf) -> str:
    """Identity of a leaf: its predicate and its parameters."""
    return leaf.predicate + json.dumps(
        leaf.params.model_dump(mode="json"), sort_keys=True
    )


class GridEvaluator:
    """Evaluate rules on fixed moments, seen from an optional place and natal."""

    def __init__(
        self,
        moments: pd.DatetimeIndex,
        place: Optional[Location] = None,
        natal: Optional[Tuple[datetime, Optional[Location]]] = None,
        node_model: str = "mean",
    ):
        """Compute the sky at each moment once."""
        self.moments = pd.DatetimeIndex(moments)
        self.node_model = node_model
        engine = get_engine(node_model)
        natal_sky = Sky(natal[0], natal[1], node_model) if natal else None
        shared_dasha: Dict[int, list] = {}
        self.contexts = []
        for ts in self.moments:
            moment = ts.to_pydatetime()
            sky = Sky(moment, place, node_model)
            sky._positions = engine.get_all_planet_positions(sky.jd)
            ctx = EvalContext(sky, natal_sky)
            ctx._dasha = shared_dasha
            self.contexts.append(ctx)
        self._leaves: Dict[str, np.ndarray] = {}

    def __len__(self) -> int:
        """Return the number of grid steps."""
        return len(self.contexts)

    def leaf(self, leaf: Leaf) -> np.ndarray:
        """Return the cached boolean series of one predicate leaf."""
        key = leaf_key(leaf)
        if key not in self._leaves:
            func = PREDICATES[leaf.predicate].func
            params = leaf.params
            self._leaves[key] = np.fromiter(
                (func(ctx, params).held for ctx in self.contexts),
                dtype=bool,
                count=len(self.contexts),
            )
        return self._leaves[key]

    def condition(self, cond: Any) -> np.ndarray:
        """Boolean series of a condition tree."""
        if isinstance(cond, AllOf):
            return np.logical_and.reduce([self.condition(c) for c in cond.all])
        if isinstance(cond, AnyOf):
            return np.logical_or.reduce([self.condition(c) for c in cond.any])
        if isinstance(cond, NotOf):
            return ~self.condition(cond.not_)
        if isinstance(cond, AtLeast):
            kids = [self.condition(c) for c in cond.at_least.of]
            return np.sum(kids, axis=0) >= cond.at_least.n
        if isinstance(cond, Leaf):
            return self.leaf(cond)
        raise TypeError(f"not a condition: {cond!r}")

    def fired(self, rule: Rule) -> np.ndarray:
        """Return where the rule's conditions hold (no window applied)."""
        if rule.conditions is None:
            raise RuleNotEvaluable(
                f"{rule.id} has no machine conditions yet (status: {rule.status})"
            )
        return np.asarray(self.condition(rule.conditions), dtype=bool)

    def indicator(self, rule: Rule) -> np.ndarray:
        """Return where the rule's effect window is open (conditions + window)."""
        return apply_window(self.fired(rule), self.moments, rule.window)

    def strength(self, rule: Rule) -> np.ndarray:
        """Graded strength while the rule fires, 0 elsewhere (1 if binary)."""
        fired = self.fired(rule)
        out = fired.astype(float)
        if rule.strength is not None:
            for i in np.flatnonzero(fired):
                out[i] = strength_value(rule.strength, self.contexts[i])[0]
        return out


def apply_window(
    fired: np.ndarray, moments: pd.DatetimeIndex, window: Optional[Window]
) -> np.ndarray:
    """Open step ``s`` when the rule fired in ``[s - after, s + before]``.

    ``after`` is how long after the configuration the effect is expected,
    ``before`` how long before it. With no window (or zero both ways) the
    indicator is the firing series itself.
    """
    fired = np.asarray(fired, dtype=bool)
    if window is None:
        return fired
    unit = UNIT_DAYS[window.unit]
    after = float(window.after or 0.0) * unit
    before = float(window.before or 0.0) * unit
    if after == 0 and before == 0:
        return fired
    t = (moments - moments[0]) / pd.Timedelta(days=1)
    t = np.asarray(t, dtype=float)
    csum = np.concatenate([[0], np.cumsum(fired)])
    lo = np.searchsorted(t, t - after, side="left")
    hi = np.searchsorted(t, t + before, side="right")
    return (csum[hi] - csum[lo]) > 0


__all__ = ["GridEvaluator", "UNIT_DAYS", "apply_window", "leaf_key"]
