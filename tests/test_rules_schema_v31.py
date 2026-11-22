"""Schema 3.1 (ADR-008 WP-91): register checks; old files still load."""

import hashlib
import json
import sys
import textwrap

import pytest
from pydantic import ValidationError

from vedic_astrology_core.rules.schema import (
    Rule,
    function_hash,
    is_registrable,
    json_schema,
    parse_disputes,
    registration_problems,
)

from tests.test_rules_schema_v3 import base


def good(**over):
    """A registrable rule."""
    rule = base(
        id="test.v31.good",
        source={"text": "Folk", "published": "1990"},
        expected_effect={"direction": "increase", "fixed_by": "text"},
        reading={"kind": "forward_trigger"},
        operationalisation=[
            {"choice": "day_convention", "value": "sunrise", "fixed_by": "text"},
            {"choice": "place", "value": "Kathmandu", "fixed_by": "practitioner"},
            {
                "choice": "horizon",
                "value": "monthly",
                "fixed_by": "project",
                "alternatives": ["weekly"],
            },
        ],
        tests=[
            {
                "domain": "gold",
                "outcome": "abs_return",
                "direction": "increase",
                "quote": "gold rises",
            }
        ],
    )
    rule.update(over)
    return rule


def problems(data, disputes=()):
    return registration_problems(Rule.model_validate(data), disputes)


def test_complete_rule_is_registrable():
    assert is_registrable(Rule.model_validate(good()))


def test_old_rule_loads_and_lists_missing_fields():
    rule = Rule.model_validate(base())
    out = registration_problems(rule)
    assert not is_registrable(rule)
    text = "\n".join(out)
    for word in ("tests", "reading", "day_convention", "place", "horizon",
                 "source.published", "expected_effect.direction"):
        assert word in text


@pytest.mark.parametrize("name", ["day_convention", "place", "horizon"])
def test_missing_required_choice(name):
    data = good()
    data["operationalisation"] = [
        c for c in data["operationalisation"] if c["choice"] != name
    ]
    assert any(f"operationalisation.{name}" in p for p in problems(data))


def test_choice_without_fixed_by_is_a_load_error():
    data = good()
    del data["operationalisation"][0]["fixed_by"]
    with pytest.raises(ValidationError):
        Rule.model_validate(data)


def test_project_choice_needs_alternatives():
    data = good()
    data["operationalisation"][2]["alternatives"] = []
    assert any("no alternatives" in p for p in problems(data))


def test_source_published_required():
    assert any("source.published" in p for p in problems(good(source={"text": "Folk"})))


def test_direction_needs_fixed_by():
    data = good(expected_effect={"direction": "increase"})
    assert any("expected_effect.fixed_by" in p for p in problems(data))


def test_bphs_needs_page():
    src = {"text": "Brihat Parashara Hora Shastra", "chapter": "1", "published": "1000"}
    assert any("source.page" in p for p in problems(good(source=src)))
    assert is_registrable(Rule.model_validate(good(source={**src, "page": "12"})))


def test_test_entry_needs_quote_or_extension():
    data = good()
    del data["tests"][0]["quote"]
    assert any("quote or project_extension" in p for p in problems(data))
    data["tests"][0]["project_extension"] = True
    assert not problems(data)
    data["tests"][0]["quote"] = "x"
    assert any("not both" in p for p in problems(data))


def test_disputed_rule_cannot_be_directional():
    out = problems(good(), disputes=["test.v31.good"])
    assert any("must be 'either'" in p for p in out)
    assert any("cannot be directional" in p for p in out)
    either = good(expected_effect={"direction": "either", "fixed_by": "project"})
    either["tests"][0]["direction"] = "either"
    assert not problems(either, disputes=["test.v31.good"])


def test_parse_disputes_reads_rule_ids():
    text = "# Disputes\n- `general.gaja_kesari.moon_kendra`: schools differ\n- see a.b\n"
    assert parse_disputes(text) == ["a.b", "general.gaja_kesari.moon_kendra"]


def test_use_pin_shorthand_and_register_check():
    from vedic_astrology_core.rules.schema import UseTarget

    assert UseTarget.model_validate({"id": "a.b", "version": 2}).version == 2
    with pytest.raises(ValidationError):
        Rule.model_validate(good(conditions={"use": "no.such@x"}))


def test_known_channel_is_optional_and_stored():
    assert Rule.model_validate(good(known_channel="tide")).known_channel == "tide"


def test_synthesis_hash_is_checked(tmp_path, monkeypatch):
    (tmp_path / "synth_mod.py").write_text("def score(x):\n    return x\n")
    monkeypatch.syspath_prepend(str(tmp_path))
    sys.modules.pop("synth_mod", None)
    digest = function_hash("synth_mod:score")
    assert digest == hashlib.sha256(b"def score(x):\n    return x\n").hexdigest()
    ok = good(synthesis={"function": "synth_mod:score", "sha256": digest})
    assert not problems(ok)
    bad = good(synthesis={"function": "synth_mod:score", "sha256": "0" * 64})
    assert any("new version" in p for p in problems(bad))
    gone = good(synthesis={"function": "synth_mod:nope", "sha256": digest})
    assert any("cannot be read" in p for p in problems(gone))


def test_schema_json_has_v31_fields():
    props = json_schema()["properties"]
    assert "known_channel" in props and "synthesis" in props
