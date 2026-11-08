"""The committed rules/ directory: validates, and every reference case passes."""

from collections import Counter

import pytest

from vedic_astrology_core.rules import (
    RuleRegistry,
    default_rules_dir,
    load_rules,
    run_reference_cases,
)

LOADED, PROBLEMS = load_rules([default_rules_dir()])
RULES = sorted((item.rule for item in LOADED), key=lambda r: r.id)


def test_rules_directory_validates():
    """astro-rules validate is clean."""
    assert not PROBLEMS, "\n".join(str(p) for p in PROBLEMS)


def test_rule_counts():
    """Catalog (12), general yogas (3), mundane drafts (67), practitioner rules (39)."""
    registry = RuleRegistry(LOADED)
    assert len(registry.by_domain["financial"]) == 25  # 4 migrated + 21 practitioner
    assert len(registry.by_domain["seismic"]) == 8
    assert len(registry.by_domain["general"]) == 3
    assert len(registry.by_domain["mundane"]) == 85  # 67 drafts + 18 practitioner


def test_mundane_rules_are_experimental_and_keep_their_original_text():
    """Mundane drafts stay experimental; needs_predicates rules keep the text."""
    for rule in RULES:
        if rule.domain != "mundane":
            continue
        assert rule.tier == "experimental", rule.id
        assert rule.notes and "mapping_status" in rule.notes, rule.id
        if rule.status == "needs_predicates":
            assert rule.conditions is None
            assert rule.notes.get("needs_predicates"), rule.id
            assert rule.notes.get("original_condition") or rule.notes.get(
                "draft_conditions"
            ), rule.id


def test_status_counts():
    """44 mundane rules are testable (11 practitioner); 41 wait for predicates.

    17 of the 64 rules that waited were encoded on 2026-11-08 when the
    mundane predicates were added (15 drafts, 2 practitioner rules).
    """
    counts = Counter((r.domain, r.status) for r in RULES)
    assert counts[("mundane", "active")] == 44
    assert counts[("mundane", "needs_predicates")] == 41
    assert sum(r.status == "needs_predicates" for r in RULES) == 47


@pytest.mark.parametrize(
    "rule", [r for r in RULES if r.status == "active"], ids=lambda r: r.id
)
def test_reference_cases_pass(rule):
    """Every reference case of every active rule passes."""
    for result in run_reference_cases(rule):
        detail = result.error or (result.tree.render() if result.tree else "")
        assert result.passed, f"case {result.index}: {detail}"


def test_gaja_kesari_counts_kendras_by_sign():
    """The S3-3 regression case is present and fires."""
    rule = RuleRegistry(LOADED).get("general.gaja_kesari.moon_kendra")
    notes = [c.note for c in rule.reference_cases]
    assert any("S3-3" in n for n in notes)
