"""Rule loader, registry, friendly errors and explain trees."""

from datetime import datetime
from pathlib import Path

import pytest

from vedic_astrology_core.rules import (
    MissingInputError,
    RuleLoadError,
    RuleNotEvaluable,
    RuleRegistry,
    evaluate,
    explain,
    load_rules,
)
from vedic_astrology_core.rules.loader import load_file

FIXTURES = Path(__file__).parent / "fixtures" / "rules"


def test_friendly_errors_name_file_line_and_field():
    """Typos produce one message each, with a suggestion and a line number."""
    rule, problems = load_file(FIXTURES / "invalid" / "typos.yaml")
    assert rule is None
    text = "\n".join(str(p) for p in problems)
    assert (
        "typos.yaml:10: conditions.all[0].conjunct_within.orb_degs: unknown "
        "field 'orb_degs'. Did you mean 'orb'?" in text
    )
    assert (
        "typos.yaml:11: conditions.all[1]: unknown predicate 'house_frm'. "
        "Did you mean 'in_house_from'?" in text
    )
    assert (
        "typos.yaml:12: conditions.all[2].in_sign.planet: unknown planet or "
        "Lagna 'Jupitor'. Did you mean 'Jupiter'?" in text
    )
    assert "typos.yaml:13" in text and "Mars casts only" in text
    assert "the moment needs a time zone" in text


def test_semantic_check_wants_a_place_for_the_lagna():
    """A rule using in_house needs places on its reference cases."""
    _rules, problems = load_rules([FIXTURES / "invalid" / "missing_place.yaml"])
    assert any("add a place" in str(p) for p in problems)


def test_duplicate_ids_are_rejected():
    """Two files with the same id: the second is reported."""
    loaded, problems = load_rules([FIXTURES / "duplicate"])
    assert len(loaded) == 1
    assert any("duplicate id 'test.saturn_tenth'" in str(p) for p in problems)
    with pytest.raises(RuleLoadError):
        RuleRegistry.load([FIXTURES / "duplicate"])


def test_registry_indexes_by_domain_and_tier():
    """The registry answers get, by_domain, by_tier and filter."""
    registry = RuleRegistry.load([FIXTURES / "valid"])
    assert len(registry) == 3
    assert registry.get("test.gaja_kesari").tier == "classical"
    assert [r.id for r in registry.by_domain["mundane"]] == ["test.waiting"]
    assert {r.id for r in registry.by_tier["experimental"]} == {
        "test.saturn_tenth",
        "test.waiting",
    }
    assert [r.id for r in registry.filter(status="needs_predicates")] == [
        "test.waiting"
    ]
    with pytest.raises(KeyError, match="Did you mean 'test.gaja_kesari'"):
        registry.get("test.gaja_kesri")


def test_explain_tree_in_plain_words():
    """Evaluate returns fired + a tree whose leaves carry evidence."""
    registry = RuleRegistry.load([FIXTURES / "valid"])
    rule = registry.get("test.gaja_kesari")
    result = evaluate(rule, datetime.fromisoformat("1990-05-15T04:45:00+00:00"))
    assert result.fired is True
    tree = result.tree
    assert tree.condition == "all of" and tree.evidence == "2 of 2 held"
    kendra = tree.children[0]
    assert kendra.condition == "in_kendra_from(planet=Jupiter, from=Moon)"
    assert kendra.evidence == (
        "Jupiter is in Gemini 15.8 deg, 7th from Moon in Sagittarius, "
        "which is a kendra (1, 4, 7, 10)"
    )
    assert tree.children[1].condition == "not"
    text = result.render()
    assert text.splitlines()[0] == "test.gaja_kesari FIRES"
    assert "[HOLDS] in_kendra_from" in text


def test_explain_shows_why_a_rule_is_silent():
    """The failing branch is marked FAILS with its reason."""
    rule = RuleRegistry.load([FIXTURES / "valid"]).get("test.gaja_kesari")
    tree = explain(rule, datetime.fromisoformat("2024-05-16T12:00:00+00:00"))
    assert tree.held is False
    combust = tree.children[1].children[0]
    assert combust.held is True
    assert "1.7 deg from the Sun" in combust.evidence
    assert "[FAILS] not" in tree.render()


def test_place_is_used_for_lagna_rules():
    """in_house needs the place given to evaluate()."""
    rule = RuleRegistry.load([FIXTURES / "valid"]).get("test.saturn_tenth")
    when = datetime.fromisoformat("2000-01-01T12:00:00+00:00")
    place = {"lat": 51.4769, "lon": 0.0, "tz": "UTC"}
    assert evaluate(rule, when, place).fired is True
    with pytest.raises(MissingInputError, match="needs a place"):
        evaluate(rule, when)


def test_needs_predicates_rule_cannot_be_evaluated():
    """A rule without conditions raises RuleNotEvaluable."""
    rule = RuleRegistry.load([FIXTURES / "valid"]).get("test.waiting")
    with pytest.raises(RuleNotEvaluable):
        evaluate(rule, datetime.fromisoformat("2000-01-01T12:00:00+00:00"))
