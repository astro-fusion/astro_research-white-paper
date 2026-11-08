"""Declarative rule engine for testing Vedic astrological principles.

Rules are YAML files under ``rules/`` (see ``CONTRIBUTING_ASTROLOGERS.md``).
This package validates them (:mod:`.schema`), evaluates them against the
corrected sidereal engine (:mod:`.engine`), and explains every result in
plain words. The command line tool is ``astro-rules`` (:mod:`.cli`).
"""

from .context import EvalContext, Location, MissingInputError, Sky
from .engine import (
    CaseResult,
    Evaluation,
    ExplainNode,
    RuleNotEvaluable,
    evaluate,
    evaluate_context,
    explain,
    rule_inputs,
    run_reference_cases,
)
from .loader import (
    RuleLoadError,
    RuleProblem,
    RuleRegistry,
    default_rules_dir,
    load_rules,
)
from .predicates import PREDICATES, Outcome, check
from .schema import ChartSpec, Place, ReferenceCase, Rule, json_schema

__all__ = [
    "PREDICATES",
    "CaseResult",
    "ChartSpec",
    "EvalContext",
    "Evaluation",
    "ExplainNode",
    "Location",
    "MissingInputError",
    "Outcome",
    "Place",
    "ReferenceCase",
    "Rule",
    "RuleLoadError",
    "RuleNotEvaluable",
    "RuleProblem",
    "RuleRegistry",
    "Sky",
    "check",
    "default_rules_dir",
    "evaluate",
    "evaluate_context",
    "explain",
    "json_schema",
    "load_rules",
    "rule_inputs",
    "run_reference_cases",
]
