"""Combination Registry.

Loads combinations from YAML catalogs and provides a central registry.
"""

import yaml
from typing import Dict, List, Optional
from pathlib import Path

from .rules import CombinationRule, create_rule_from_config


class CombinationRegistry:
    """Central registry mapping names to CombinationRules."""

    def __init__(self):
        """Initialize the registry and load catalogs."""
        self._rules: Dict[str, CombinationRule] = {}
        self._load_catalogs()

    def _load_catalogs(self):
        """Dynamically load all YAML files in the catalog/ directory."""
        current_dir = Path(__file__).parent
        catalog_dir = current_dir / "catalog"

        if not catalog_dir.exists():
            return

        for file_path in catalog_dir.glob("*.yaml"):
            with open(file_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)

                if not data:
                    continue

                for entry in data:
                    rule = create_rule_from_config(entry)
                    self._rules[rule.name] = rule

    def get_rule(self, name: str) -> Optional[CombinationRule]:
        """Retrieve a loaded rule by exact name."""
        return self._rules.get(name)

    def get_all_rules(self) -> List[CombinationRule]:
        """Retrieve all loaded rules."""
        return list(self._rules.values())

    def get_rules_by_usecase(self, use_case: str) -> List[CombinationRule]:
        """Retrieve rules filtered by their tagged use case (e.g., 'seismic')."""
        use_case = use_case.lower()
        return [r for r in self._rules.values() if r.use_case.lower() == use_case]


# Singleton instance for easy access
_registry_instance = None


def get_registry() -> CombinationRegistry:
    """Get or initialize the global registry instance."""
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = CombinationRegistry()
    return _registry_instance
