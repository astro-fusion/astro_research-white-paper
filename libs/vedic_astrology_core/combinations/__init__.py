"""Astrological combinations: compatibility layer over :mod:`..rules`.

Deprecated for new code: use :mod:`vedic_astrology_core.rules` (rule files
in ``rules/``, the ``astro-rules`` CLI, ``evaluate`` and ``explain``). This
package keeps ``CombinationRegistry``, ``get_registry`` and
``CombinationEvaluator`` working for one release; they now read the same
``rules/`` files, so there is a single rule source. The degree-based
condition classes in :mod:`.conditions` and :mod:`.rules` are legacy and
are no longer used by the registry.
"""

from .conditions import AstroCondition, create_condition
from .rules import CombinationRule, create_rule_from_config
from .evaluator import CombinationEvaluator
from .registry import CombinationRegistry, RegistryRule, get_registry

__all__ = [
    "AstroCondition",
    "create_condition",
    "CombinationRule",
    "create_rule_from_config",
    "CombinationEvaluator",
    "CombinationRegistry",
    "RegistryRule",
    "get_registry",
]
