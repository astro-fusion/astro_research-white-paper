"""Combinator Rules for Astrological Conditions.

This module provides logical combinators to group atomic astrological conditions
into complex, multi-factor rules.
"""

from typing import Dict, List, Any
from .conditions import AstroCondition, create_condition


class CombinationRule:
    """A named astrological combination composed of multiple conditions."""

    def __init__(
        self,
        name: str,
        conditions: List[AstroCondition],
        logic: str = "ALL_OF",
        description: str = "",
        source: str = "",
        use_case: str = "",
    ):
        """Initialize with name, conditions, and logical operator."""
        self.name = name
        self.conditions = conditions
        self.logic = logic.upper()
        self.description = description
        self.source = source
        self.use_case = use_case

    def evaluate(self, positions: Dict[str, Dict]) -> Dict[str, Any]:
        """
        Evaluate the entire rule by combining its child conditions.

        Returns:
            Dict containing overall is_active, strength score, and breakdown.
        """
        if not self.conditions:
            return {
                "is_active": False,
                "score": 0.0,
                "details": "No conditions defined.",
            }

        evaluations = [cond.evaluate(positions) for cond in self.conditions]

        is_active = False
        score = 0.0

        if self.logic == "ALL_OF":
            # AND logic: Active only if ALL conditions are active
            is_active = all(ev["is_active"] for ev in evaluations)
            if evaluations:
                # Score is average of all active conditions, or 0 if not active
                score = (
                    sum(ev["score"] for ev in evaluations) / len(evaluations)
                    if is_active
                    else 0.0
                )
        elif self.logic == "ANY_OF":
            # OR logic: Active if AT LEAST ONE condition is active
            active_evs = [ev for ev in evaluations if ev["is_active"]]
            is_active = len(active_evs) > 0
            if active_evs:
                score = max(ev["score"] for ev in active_evs)  # Take highest score
        else:
            raise ValueError(f"Unknown logic operator: {self.logic}")

        return {
            "name": self.name,
            "is_active": is_active,
            "score": score,
            "condition_count": len(self.conditions),
            "breakdown": evaluations,
        }


def create_rule_from_config(config: Dict[str, Any]) -> CombinationRule:
    """Create a CombinationRule from a dictionary config (YAML)."""
    name = config.get("name", "Unnamed Combination")
    desc = config.get("description", "")
    source = config.get("source", "")
    use_case = config.get("use_case", "")

    cond_config = config.get("conditions", {})
    logic = cond_config.get("logic", "ALL_OF")
    items = cond_config.get("items", [])

    conditions = [create_condition(item) for item in items]

    return CombinationRule(
        name=name,
        conditions=conditions,
        logic=logic,
        description=desc,
        source=source,
        use_case=use_case,
    )
