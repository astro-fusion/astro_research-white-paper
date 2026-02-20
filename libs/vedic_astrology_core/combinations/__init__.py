"""Modular Astrological Combinations Engine.

This package provides a declarative rule engine for evaluating Vedic astrological
combinations (Yogas) across time series data. It supports complex composition of
atomic conditions (conjunctions, aspects, sign placements, etc.).
"""

from .conditions import AstroCondition, create_condition
from .rules import CombinationRule, create_rule_from_config
from .evaluator import CombinationEvaluator
from .registry import CombinationRegistry, get_registry

__all__ = [
    "AstroCondition",
    "create_condition",
    "CombinationRule",
    "create_rule_from_config",
    "CombinationEvaluator",
    "CombinationRegistry",
    "get_registry",
]
