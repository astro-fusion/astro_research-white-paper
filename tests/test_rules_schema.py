"""Rule file schema: fields, tiers, sources, the condition tree, JSON Schema."""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from vedic_astrology_core.rules.schema import Rule, json_schema

REPO = Path(__file__).parent.parent


def base(**overrides):
    """Return a minimal valid experimental rule as a dict."""
    rule = {
        "id": "test.minimal",
        "name": "Minimal",
        "domain": "general",
        "claim": "c",
        "source": {"text": "Folk"},
        "author": "@me",
        "tier": "experimental",
        "conditions": {"retrograde": {"planet": "Saturn"}},
        "reference_cases": [
            {"moment": "2000-01-01T12:00:00Z", "expect": "fires", "note": "R"}
        ],
    }
    rule.update(overrides)
    return rule


def test_minimal_rule_validates():
    """The smallest experimental rule is accepted."""
    rule = Rule.model_validate(base())
    assert rule.status == "active" and rule.version == 1


def test_unknown_top_level_key_is_rejected():
    """extra="forbid": a misspelt field is an error, not ignored."""
    with pytest.raises(ValidationError, match="Extra inputs"):
        Rule.model_validate(base(reference_case=[]))


@pytest.mark.parametrize("bad_id", ["Gaja", "gaja", "gaja kesari.x", "a..b"])
def test_id_must_be_lowercase_dotted(bad_id):
    """Ids are lowercase and contain at least one dot."""
    with pytest.raises(ValidationError):
        Rule.model_validate(base(id=bad_id))


def test_classical_needs_text_and_chapter():
    """A source without a chapter forces tier experimental."""
    cases = [
        {"moment": "2000-01-01T12:00:00Z", "expect": "fires", "note": "a"},
        {"moment": "2001-09-11T12:00:00Z", "expect": "silent", "note": "b"},
    ]
    with pytest.raises(ValidationError, match="tier 'classical' needs a source"):
        Rule.model_validate(base(tier="classical", reference_cases=cases))
    ok = Rule.model_validate(
        base(
            tier="classical",
            source={"text": "BPHS", "chapter": 36, "verse": 3},
            reference_cases=cases,
        )
    )
    assert ok.source.chapter == "36"


def test_classical_needs_a_firing_and_a_silent_case():
    """Classical rules carry both kinds of reference case."""
    with pytest.raises(ValidationError, match="expect: silent"):
        Rule.model_validate(
            base(tier="classical", source={"text": "BPHS", "chapter": "36"})
        )


def test_experimental_needs_one_reference_case():
    """At least one reference case unless the rule waits for predicates."""
    with pytest.raises(ValidationError, match="at least one reference case"):
        Rule.model_validate(base(reference_cases=[]))


def test_null_conditions_only_when_needs_predicates():
    """conditions: null is allowed only with status needs_predicates."""
    with pytest.raises(ValidationError, match="needs_predicates"):
        Rule.model_validate(base(conditions=None))
    rule = Rule.model_validate(
        base(conditions=None, status="needs_predicates", reference_cases=[])
    )
    assert rule.conditions is None


def test_source_kinds():
    """text, app_registry+id, or url; nothing else."""
    Rule.model_validate(base(source={"app_registry": "x.yaml", "id": "R-1"}))
    Rule.model_validate(base(source={"url": "https://example.org"}))
    with pytest.raises(ValidationError, match="source needs"):
        Rule.model_validate(base(source={"verse": "3"}))


def test_moment_needs_a_timezone():
    """Naive reference moments are rejected."""
    cases = [{"moment": "2000-01-01T12:00:00", "expect": "fires", "note": "n"}]
    with pytest.raises(ValidationError):
        Rule.model_validate(base(reference_cases=cases))


def test_unknown_time_zone_is_rejected():
    """Places carry IANA zone names."""
    case = {
        "moment": "2000-01-01T12:00:00Z",
        "place": {"lat": 0, "lon": 0, "tz": "Mars/Olympus"},
        "expect": "fires",
        "note": "n",
    }
    with pytest.raises(ValidationError, match="unknown time zone"):
        Rule.model_validate(base(reference_cases=[case]))


def test_boolean_tree_nests_arbitrarily():
    """Nest all / any / not / at_least; shorthand leaves expand."""
    cond = {
        "all": [
            {"planet": "Guru", "in_kendra_from": "Chandra"},
            {"not": {"any": [{"planet": "Jupiter", "combust": True}]}},
            {
                "at_least": {
                    "n": 1,
                    "of": [
                        {"in_sign": {"planet": "Sun", "signs": "Leo"}},
                        {"planet": "Mars", "not": "retrograde"},
                    ],
                }
            },
        ]
    }
    rule = Rule.model_validate(base(conditions=cond))
    leaf = rule.conditions.all[0]
    assert leaf.predicate == "in_kendra_from"
    assert leaf.params.planet == "Jupiter" and leaf.params.from_ == "Moon"


def test_at_least_n_cannot_exceed_the_list():
    """at_least with n larger than its list is an error."""
    cond = {"at_least": {"n": 3, "of": [{"retrograde": {"planet": "Mars"}}]}}
    with pytest.raises(ValidationError, match="only 1 conditions"):
        Rule.model_validate(base(conditions=cond))


def test_illegal_graha_drishti_is_rejected():
    """Mars casts only the 4th, 7th and 8th aspects."""
    cond = {"graha_drishti": {"planet": "Mars", "target": "Moon", "aspects": [10]}}
    with pytest.raises(ValidationError, match="Mars casts only"):
        Rule.model_validate(base(conditions=cond))


def test_unsupported_varga_is_rejected():
    """Only the sixteen Shodasavargas are allowed."""
    cond = {"varga_sign": {"planet": "Moon", "varga": 8, "signs": ["Leo"]}}
    with pytest.raises(ValidationError, match="D8 is not a supported varga"):
        Rule.model_validate(base(conditions=cond))


def test_json_schema_matches_the_committed_file():
    """rules/schema.json is the exported schema (regenerate if this fails)."""
    committed = json.loads((REPO / "rules" / "schema.json").read_text())
    assert committed == json.loads(json.dumps(json_schema(), sort_keys=True))
    assert committed["additionalProperties"] is False
    assert "in_kendra_from" in json.dumps(committed)
