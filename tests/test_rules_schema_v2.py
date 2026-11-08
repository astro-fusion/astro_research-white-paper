"""Schema v2: params with ranges, strength, tuning_log, validation, review."""

import copy
import json

import pytest
from pydantic import ValidationError

from vedic_astrology_core.rules import default_rules_dir, load_rules
from vedic_astrology_core.rules.loader import range_problems
from vedic_astrology_core.rules.schema import Rule, json_schema


def v2(**overrides):
    """Return a minimal v2 rule with one tunable orb."""
    rule = {
        "id": "test.v2",
        "version": 2,
        "name": "V2",
        "domain": "seismic",
        "claim": "c",
        "source": {"text": "Folk"},
        "author": "@me",
        "tier": "experimental",
        "params": {"orb": {"value": 8, "min": 2, "max": 12, "step": 1, "unit": "deg"}},
        "conditions": {
            "conjunct_within": {"planets": ["Mars", "Saturn"], "orb": "$orb"}
        },
        "reference_cases": [
            {"moment": "2000-01-01T12:00:00Z", "expect": "fires", "note": "R"}
        ],
    }
    rule.update(overrides)
    return rule


def test_param_reference_is_bound_to_its_value():
    """$orb in a condition becomes params.orb.value."""
    rule = Rule.model_validate(v2())
    assert rule.conditions.params.orb == 8
    assert rule.param_values == {"orb": 8}
    assert rule.validation.status == "unvalidated"


def test_bind_returns_a_rule_with_new_values():
    """Rebinding re-validates with the new value; the original is unchanged."""
    rule = Rule.model_validate(v2())
    tuned = rule.bind({"orb": 3})
    assert tuned.conditions.params.orb == 3 and tuned.params["orb"].value == 3
    assert rule.conditions.params.orb == 8
    with pytest.raises(ValueError, match="no parameter 'window'"):
        rule.bind({"window": 3})
    with pytest.raises(ValidationError, match="outside its range"):
        rule.bind({"orb": 20})


def test_unknown_param_reference_is_rejected():
    """Every $name must be declared."""
    data = v2()
    data["conditions"]["conjunct_within"]["orb"] = "$orbit"
    with pytest.raises(ValidationError, match=r"unknown parameter '\$orbit'"):
        Rule.model_validate(data)


def test_unused_param_is_rejected():
    """A declared parameter nobody references cannot be tuned meaningfully."""
    data = v2(conditions={"retrograde": {"planet": "Mars"}})
    with pytest.raises(ValidationError, match="never referenced"):
        Rule.model_validate(data)


@pytest.mark.parametrize(
    "spec, match",
    [
        ({"value": 15, "min": 2, "max": 12, "step": 1, "unit": "deg"}, "outside"),
        ({"value": 8, "min": 12, "max": 2, "step": 1, "unit": "deg"}, "above max"),
        ({"value": 8, "min": 2, "max": 12, "step": 0, "unit": "deg"}, "greater than"),
        ({"value": 8, "min": 2, "max": 12, "step": 1, "unit": "furlong"}, "unit"),
        ({"value": 8, "min": 2, "max": 12, "step": 1, "unit": "deg", "x": 1}, "Extra"),
    ],
)
def test_param_ranges_are_strict(spec, match):
    """Value inside [min, max], positive step, known unit, no extra keys."""
    with pytest.raises(ValidationError, match=match):
        Rule.model_validate(v2(params={"orb": spec}))


def test_param_grid():
    """The grid runs from min to max in steps."""
    rule = Rule.model_validate(v2())
    assert rule.params["orb"].grid() == [float(x) for x in range(2, 13)]


def test_range_ends_must_give_a_valid_rule():
    """An orb range reaching past the predicate's own limit is a problem."""
    spec = {"value": 8, "min": 2, "max": 40, "step": 1, "unit": "deg"}
    rule = Rule.model_validate(v2(params={"orb": spec}))
    problems = range_problems(rule, "x.yaml")
    assert len(problems) == 1
    assert problems[0].field == "params.orb.max"
    assert "orb = 40" in problems[0].message


def test_window_and_strength_take_param_references():
    """$name works in window and strength too."""
    data = v2(
        params={
            "orb": {"value": 8, "min": 2, "max": 12, "step": 1, "unit": "deg"},
            "window_after": {
                "value": 7,
                "min": 0,
                "max": 30,
                "step": 1,
                "unit": "days",
            },
        },
        window={"unit": "days", "after": "$window_after"},
        strength={
            "combine": "mean",
            "terms": [
                {"orb_closeness": {"planets": ["Mars", "Saturn"], "orb": "$orb"}},
                {"dignity_weight": {"planet": "Mars"}},
            ],
        },
    )
    rule = Rule.model_validate(data)
    assert rule.window.after == 7
    assert rule.strength.terms[0].orb_closeness.orb == 8
    assert rule.bind({"orb": 4}).strength.terms[0].orb_closeness.orb == 4


@pytest.mark.parametrize(
    "terms, match",
    [
        (
            [{"closeness": {"planets": ["Mars", "Saturn"], "orb": 3}}],
            "unknown strength",
        ),
        ([{"dignity_weight": {"planet": "Rahu"}}], "Sun to Saturn"),
        ([{"dasha_weight": {"lord": "Mars", "levels": [4]}}], "levels are 1, 2 or 3"),
        ([], "at least 1"),
    ],
)
def test_strength_terms_are_checked(terms, match):
    """Only the four strength terms, with valid arguments."""
    with pytest.raises(ValidationError, match=match):
        Rule.model_validate(v2(strength={"combine": "min", "terms": terms}))


def test_validation_stamp_needs_its_evidence():
    """A confirm stamp needs the version, study, result and time."""
    with pytest.raises(ValidationError, match="needs version, study, confirm, at"):
        Rule.model_validate(v2(validation={"status": "confirmed"}))
    stamp = {
        "status": "not_confirmed",
        "version": 2,
        "study": "earthquake",
        "confirm": {"rate_ratio": 0.9, "ci": [0.5, 1.4], "p": 0.7},
        "at": "2026-11-08T10:00:00Z",
        "commit": "abc",
    }
    assert Rule.model_validate(v2(validation=stamp)).validation.confirm.p == 0.7


def test_tuning_log_and_review_entries():
    """Both lists are strict about their keys and verdicts."""
    entry = {
        "at": "2026-11-08T10:00:00Z",
        "by": "@me",
        "study": "earthquake",
        "version": 2,
        "grid": {"orb": {"min": 2, "max": 12, "step": 1}},
        "chosen": {"orb": 6},
        "explore": {"rate_ratio": 1.3, "ci": [0.9, 1.9], "p": 0.08, "n_cells": 11},
    }
    review = {
        "by": "@a",
        "at": "2026-11-08T10:00:00Z",
        "verdict": "faithful",
        "note": "ok",
    }
    rule = Rule.model_validate(v2(tuning_log=[entry], review=[review]))
    assert rule.tuning_log[0].chosen == {"orb": 6}
    bad = dict(review, verdict="maybe")
    with pytest.raises(ValidationError):
        Rule.model_validate(v2(review=[bad]))
    with pytest.raises(ValidationError, match="Extra"):
        Rule.model_validate(v2(tuning_log=[dict(entry, best=True)]))


def test_json_schema_accepts_param_references():
    """Editors see "$orb" as valid in a number field, but not in Param itself."""
    schema = json_schema()
    text = json.dumps(schema)
    assert r"^\\$([a-z][a-z0-9_]*)$" in text
    param = schema["$defs"]["Param"]["properties"]["value"]
    assert param.get("type") == "number"
    assert set(schema["properties"]) >= {
        "params",
        "strength",
        "tuning_log",
        "validation",
        "review",
    }


def test_every_committed_rule_is_version_2_and_unvalidated_or_stamped():
    """The migration left no v1 rule behind."""
    loaded, problems = load_rules([default_rules_dir()])
    assert not problems
    for item in loaded:
        assert item.rule.version >= 2, item.rule.id
        assert item.rule.validation.status in (
            "unvalidated",
            "confirmed",
            "not_confirmed",
        )


def test_committed_orbs_became_params():
    """A rule that had an orb now tunes it; the condition reads the param."""
    loaded, _ = load_rules([default_rules_dir() / "seismic"])
    rule = next(i.rule for i in loaded if i.rule.id == "seismic.shrapit_yoga")
    orb = rule.params["orb"]
    assert orb.min < orb.value < orb.max
    assert rule.conditions is not None
    assert "$orb" in str(rule._template["conditions"])
    tuned = next(i.rule for i in loaded if i.rule.id == "seismic.mangal_ketu_primary")
    assert tuned.params["orb"].value == tuned.tuning_log[-1].chosen["orb"]
    assert tuned.conditions.params.orb == tuned.params["orb"].value


def test_deepcopy_keeps_the_template():
    """A copied rule can still be rebound."""
    rule = copy.deepcopy(Rule.model_validate(v2()))
    assert rule.bind({"orb": 5}).conditions.params.orb == 5
