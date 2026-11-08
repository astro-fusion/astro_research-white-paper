"""Astrological Combination Evaluator.

Time-series engine to evaluate rules against the ephemeris over a date
range. Rules come from the ``rules/`` registry (see :mod:`.registry`); the
old :class:`~.rules.CombinationRule` objects are still accepted for one
release.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Sequence, Union

import pandas as pd

from ..astrology.ephemeris import EphemerisEngine
from ..rules.context import EvalContext, Sky
from .registry import RegistryRule, get_registry
from .rules import CombinationRule

AnyRule = Union[RegistryRule, CombinationRule]


class CombinationEvaluator:
    """Time-series engine for evaluating astrological combinations."""

    def __init__(
        self,
        ephemeris: Optional[EphemerisEngine] = None,
        rules: Optional[Sequence[AnyRule]] = None,
    ):
        """Initialize with an ephemeris engine and rules (default: all of rules/)."""
        self.ephemeris = ephemeris or EphemerisEngine()
        self.rules: List[AnyRule] = (
            list(rules) if rules is not None else get_registry().get_all_rules()
        )

    def evaluate_date(self, dt: datetime) -> Dict[str, Dict]:
        """Evaluate all rules for one timezone-aware datetime."""
        jd = self.ephemeris.datetime_to_julian_day(dt)
        positions = self.ephemeris.get_all_planet_positions(jd)
        sky = Sky(dt, None, self.ephemeris.node_model)
        sky._positions = positions
        ctx = EvalContext(sky)

        results = {}
        for rule in self.rules:
            if isinstance(rule, RegistryRule):
                results[rule.name] = rule._result(ctx)
            else:
                results[rule.name] = rule.evaluate(positions)
        return results

    def evaluate_timeseries(
        self, start_date: datetime, end_date: datetime, step_days: float = 1.0
    ) -> pd.DataFrame:
        """Evaluate rules over a date range and return a time-series DataFrame."""
        rows = []
        current = start_date

        while current <= end_date:
            day_res = self.evaluate_date(current)

            row = {"date": current}
            for rule_name, ev in day_res.items():
                row[f"{rule_name}_active"] = 1 if ev["is_active"] else 0
                row[f"{rule_name}_score"] = ev["score"]

            rows.append(row)
            current += timedelta(days=step_days)

        return pd.DataFrame(rows)
