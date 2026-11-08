"""Declarative rule engine for testing Vedic astrological principles.

Rules are YAML files under ``rules/``. This package validates them
(:mod:`.schema`) and evaluates their predicates (:mod:`.predicates`) against
the corrected sidereal engine, explaining every result in plain words.
"""

from .context import EvalContext, Location, MissingInputError, Sky
from .predicates import PREDICATES, Outcome, check
from .schema import ChartSpec, Place, ReferenceCase, Rule, json_schema

__all__ = [
    "PREDICATES",
    "ChartSpec",
    "EvalContext",
    "Location",
    "MissingInputError",
    "Outcome",
    "Place",
    "ReferenceCase",
    "Rule",
    "Sky",
    "check",
    "json_schema",
]
