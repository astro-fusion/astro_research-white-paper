"""Astrological Combination Evaluator.

Time-series engine to evaluate rules against the ephemeris over a date range.
"""

from typing import Dict, List
from datetime import datetime, timedelta
import pandas as pd

from .rules import CombinationRule
from ..astrology.ephemeris import EphemerisEngine


class CombinationEvaluator:
    """Time-series engine for evaluating astrological combinations."""

    def __init__(self, ephemeris: EphemerisEngine, rules: List[CombinationRule]):
        """Initialize with ephemeris engine and a list of rules."""
        self.ephemeris = ephemeris
        self.rules = rules

    def evaluate_date(self, dt: datetime) -> Dict[str, Dict]:
        """Evaluate all registered combinations for a specific datetime."""
        # Calculate julian day and get all required planetary positions
        jd = self.ephemeris.datetime_to_julian_day(dt)
        positions = self.ephemeris.get_all_planet_positions(jd)

        results = {}
        for rule in self.rules:
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

            # Flatten into a row mapping
            row = {"date": current}
            for rule_name, ev in day_res.items():
                row[f"{rule_name}_active"] = 1 if ev["is_active"] else 0
                row[f"{rule_name}_score"] = ev["score"]

            rows.append(row)
            current += timedelta(days=step_days)

        return pd.DataFrame(rows)
