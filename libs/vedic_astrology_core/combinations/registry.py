"""Combination registry, now a thin view over the ``rules/`` registry.

The YAML catalogs that used to live in ``combinations/catalog/`` were
migrated to ``rules/financial`` and ``rules/seismic`` (one file per rule,
validated by ``astro-rules``). This module keeps the old API working for
one release: :class:`CombinationRegistry` and :func:`get_registry` return
:class:`RegistryRule` objects with the old ``name``, ``use_case`` and
``evaluate(positions)`` interface, backed by :mod:`vedic_astrology_core.rules`.
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Union

from ..rules.context import EvalContext, Sky
from ..rules.engine import evaluate_context, iter_leaves, rule_inputs
from ..rules.loader import RuleRegistry
from ..rules.schema import Rule


class RegistryRule:
    """Adapter giving a ``rules/`` rule the old CombinationRule interface."""

    def __init__(self, rule: Rule):
        """Wrap a validated :class:`Rule`."""
        self.rule = rule
        self.id = rule.id
        self.name = rule.name
        self.use_case = rule.domain
        self.description = rule.claim
        self.source = rule.source.short()
        self.conditions = list(iter_leaves(rule.conditions))
        self.logic = "TREE"

    def _result(self, ctx: EvalContext) -> Dict[str, Any]:
        result = evaluate_context(self.rule, ctx)
        breakdown = []

        def walk(node):
            if not node.children:
                breakdown.append(
                    {
                        "is_active": node.held,
                        "score": 1.0 if node.held else 0.0,
                        "details": f"{node.condition}: {node.evidence}",
                    }
                )
            for child in node.children:
                walk(child)

        walk(result.tree)
        return {
            "name": self.name,
            "id": self.id,
            "is_active": result.fired,
            "score": 1.0 if result.fired else 0.0,
            "condition_count": len(self.conditions),
            "breakdown": breakdown,
            "explain": result.tree.render(),
        }

    def evaluate(self, positions: Dict) -> Dict[str, Any]:
        """Evaluate on precomputed positions (old interface).

        Only rules whose predicates read positions alone can be evaluated
        this way; time-window predicates (eclipses, ingress, weekday, dasha)
        need :meth:`evaluate_at`.
        """
        return self._result(EvalContext(Sky.from_positions(positions)))

    def evaluate_at(self, moment: datetime, place=None, natal=None) -> Dict[str, Any]:
        """Evaluate at a moment with the full engine."""
        from ..rules.engine import build_context

        return self._result(build_context(self.rule, moment, place, natal))

    def __repr__(self) -> str:
        """Show the id and the old name."""
        return f"RegistryRule({self.id!r}, name={self.name!r})"


class CombinationRegistry:
    """Central registry of evaluable rules from ``rules/``, keyed by name."""

    def __init__(self, paths: Optional[Sequence[Union[str, Path]]] = None):
        """Load ``rules/`` (or ``paths``); rules needing a place or natal are skipped.

        Rules with ``status: needs_predicates`` have no conditions and are
        skipped too; the full set is in :attr:`rule_registry`.
        """
        self.rule_registry = RuleRegistry.load(paths)
        self._rules: Dict[str, RegistryRule] = {}
        for rule in self.rule_registry:
            if rule.conditions is None or rule_inputs(rule):
                continue
            self._rules[rule.name] = RegistryRule(rule)

    def get_rule(self, name: str) -> Optional[RegistryRule]:
        """Retrieve a rule by its old name or its id."""
        if name in self._rules:
            return self._rules[name]
        return next((r for r in self._rules.values() if r.id == name), None)

    def get_all_rules(self) -> List[RegistryRule]:
        """All rules evaluable from a moment alone."""
        return list(self._rules.values())

    def get_rules_by_usecase(self, use_case: str) -> List[RegistryRule]:
        """Rules of one domain (financial, seismic, mundane, natal, general)."""
        use_case = use_case.lower()
        return [r for r in self._rules.values() if r.use_case == use_case]


_registry_instance: Optional[CombinationRegistry] = None


def get_registry() -> CombinationRegistry:
    """Get or initialize the global registry instance."""
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = CombinationRegistry()
    return _registry_instance
