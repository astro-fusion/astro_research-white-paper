"""Schema v3 (ADR-007 WP-65): reading, operationalisation, tests, variants, use."""

import sys
import textwrap
from datetime import datetime, timezone

import pytest
import yaml
from pydantic import ValidationError

from vedic_astrology_core.rules import default_rules_dir, evaluate, load_rules
from vedic_astrology_core.rules.engine import rule_inputs
from vedic_astrology_core.rules.predicates import (
    MODULES,
    PREDICATES,
    compose,
    load_modules,
)
from vedic_astrology_core.rules.schema import Rule, UseOf, json_schema

JAN_2000 = datetime(2000, 1, 1, 12, tzinfo=timezone.utc)  # Sun in Sagittarius
JUL_2000 = datetime(2000, 7, 1, 12, tzinfo=timezone.utc)  # Sun in Gemini


def base(**overrides):
    """A minimal valid rule."""
    rule = {
        "id": "test.v3.base",
        "name": "Base",
        "domain": "seismic",
        "claim": "c",
        "source": {"text": "Folk"},
        "author": "@me",
        "tier": "experimental",
        "conditions": {"in_sign": {"planet": "Sun", "signs": ["Sagittarius"]}},
        "reference_cases": [{"moment": "2000-01-01T12:00:00Z", "expect": "fires", "note": "R"}],
    }
    rule.update(overrides)
    return rule


def full_v3(**overrides):
    """The section 3.2 example, on a rule with an orb parameter."""
    rule = base(
        params={"orb": {"value": 8, "min": 2, "max": 12, "step": 1, "unit": "deg"}},
        conditions={"conjunct_within": {"planets": ["Mars", "Ketu"], "orb": "$orb"}},
        reading={
            "kind": "forward_trigger",
            "text_says": "post_event_classification",
            "note": "The text reads the mandala after an earthquake.",
        },
        operationalisation=[
            {"choice": "orb", "value": "8 deg", "fixed_by": "project", "note": "No orb in the verse."},
            {"choice": "node", "value": "mean", "fixed_by": "project"},
        ],
        tests=[
            {"domain": "earthquake", "outcome": "mainshock_rate", "direction": "increase"},
            {"domain": "gold", "outcome": "abs_return", "direction": "increase"},
        ],
        variants=[
            {
                "id": "orb_10",
                "role": "candidate",
                "params": {"orb": 10},
                "reason": "A named practitioner uses 10 degrees.",
                "source": {"text": "...", "url": "https://example.org", "archive_url": "https://archive.org/x"},
            },
            {"id": "true_node", "role": "sensitivity", "conventions": {"node_model": "true"}},
        ],
    )
    rule.update(overrides)
    return rule


def write_rule(folder, data):
    """Write one rule file named after its id."""
    path = folder / (data["id"].replace(".", "_") + ".yaml")
    path.write_text(yaml.safe_dump(data, sort_keys=False))
    return path


@pytest.fixture(autouse=True)
def fresh_cache():
    """Each test resolves parents from scratch."""
    compose.clear_cache()
    yield
    compose.clear_cache()


# ------------------------------------------------------------------ v3 blocks
def test_every_existing_rule_file_loads_unchanged():
    """Schema v3 is additive: the committed rules/ validates as before."""
    loaded, problems = load_rules([default_rules_dir()])
    assert not problems, "\n".join(str(p) for p in problems)
    # The 121 pre-v3 files are unchanged; study ports (ADR-007 WP-71) are new
    # v3 files that carry tests blocks by design.
    old = [r for r in loaded if ".study." not in r.rule.id]
    assert len(old) == 121
    assert all(not r.rule.tests and not r.rule.variants for r in old)


def test_the_four_blocks_validate_as_in_section_3_2():
    """reading, operationalisation, tests and variants load and read back."""
    rule = Rule.model_validate(full_v3())
    assert rule.reading.kind == "forward_trigger"
    assert rule.reading.text_says == "post_event_classification"
    assert [c.fixed_by for c in rule.operationalisation] == ["project", "project"]
    assert [(t.domain, t.outcome) for t in rule.tests] == [
        ("earthquake", "mainshock_rate"),
        ("gold", "abs_return"),
    ]
    assert rule.variant("orb_10").params == {"orb": 10}
    assert rule.variant("true_node").conventions.node_model == "true"
    with pytest.raises(KeyError, match="no variant 'orb_11'"):
        rule.variant("orb_11")
    # the blocks survive rebinding a parameter
    assert rule.bind({"orb": 9}).tests == rule.tests


@pytest.mark.parametrize(
    "change, message",
    [
        (lambda r: r.pop("reading"), "needs reading and operationalisation"),
        (lambda r: r.update(operationalisation=[]), "needs reading and operationalisation"),
        (lambda r: r["reading"].pop("note"), "say why in note"),
        (lambda r: r["reading"].update(kind="prophecy"), "kind"),
        (lambda r: r["operationalisation"][0].update(fixed_by="me"), "fixed_by"),
        (lambda r: r["operationalisation"].append(dict(r["operationalisation"][0])), "orb twice"),
        (lambda r: r["tests"].append(dict(r["tests"][0])), "listed twice"),
        (lambda r: r["tests"][0].update(direction="up"), "direction"),
        (lambda r: r["tests"][0].update(domain="Gold Price"), "domain"),
        (lambda r: r["variants"][0].pop("reason"), "needs a reason"),
        (lambda r: r["variants"][0].update(params={"window": 3}), "'window' is not declared"),
        (lambda r: r["variants"][0].update(params={"orb": 20}), "outside its range"),
        (lambda r: r["variants"][1].update(conventions={}), "changes nothing"),
        (lambda r: r["variants"][1].update(conventions={"house_system": "P"}), "house_system"),
        (lambda r: r["variants"][1].update(id="primary"), "reserved"),
        (lambda r: r["variants"][1].update(id="orb_10"), "used twice"),
        (lambda r: r["tests"][0].update(slot=3), "slot"),
    ],
)
def test_bad_v3_blocks_are_rejected(change, message):
    """Each rule of section 3.2 is enforced with a message that names it."""
    data = full_v3()
    change(data)
    with pytest.raises(ValidationError, match=message):
        Rule.model_validate(data)


def test_v3_blocks_are_in_the_json_schema():
    """rules/schema.json lists the new blocks and the use leaf."""
    schema = json_schema()
    for key in ("reading", "operationalisation", "tests", "variants"):
        assert key in schema["properties"], key
    use = schema["$defs"]["UseOf"]
    assert list(use["properties"]) == ["use"]
    assert use["properties"]["use"]["anyOf"][0]["type"] == "string"


# ------------------------------------------------------------------ use leaf
def parent(**overrides):
    """A parent with a bound orb: Sun within $orb of Mercury, Sun in Sagittarius."""
    rule = base(
        id="test.v3.parent",
        version=2,
        params={"orb": {"value": 8, "min": 2, "max": 12, "step": 1, "unit": "deg"}},
        conditions={
            "all": [
                {"in_sign": {"planet": "Sun", "signs": ["Sagittarius"]}},
                {"conjunct_within": {"planets": ["Sun", "Mercury"], "orb": "$orb"}},
            ]
        },
    )
    rule.update(overrides)
    return rule


def child(use="test.v3.parent", **overrides):
    """A combination: the parent plus the Moon anywhere (always true)."""
    rule = base(
        id="test.v3.child",
        conditions={
            "all": [
                {"use": use},
                {"in_sign": {"planet": "Moon", "signs": [
                    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra",
                    "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]}},
            ]
        },
    )
    rule.update(overrides)
    return rule


def test_use_resolves_to_the_parents_bound_primary_conditions(tmp_path):
    """The leaf expands to the parent's conditions with $orb bound to 8."""
    write_rule(tmp_path, parent())
    with compose.use_rules(tmp_path):
        rule = Rule.model_validate(child())
        par = Rule.model_validate(parent())
    leaf = rule.conditions.all[0]
    assert isinstance(leaf, UseOf)
    assert leaf.resolved.id == "test.v3.parent" and leaf.resolved.version == 2
    assert leaf.resolved.conditions["all"][1]["conjunct_within"]["orb"] == 8
    assert leaf.all[0] == par.conditions
    for moment in (JAN_2000, JUL_2000):
        assert evaluate(rule, moment).fired == evaluate(par, moment).fired
    assert evaluate(rule, JAN_2000).fired is evaluate(par, JAN_2000).fired


def test_use_carries_the_parents_inputs(tmp_path):
    """A parent that needs a place makes the child need one too."""
    write_rule(
        tmp_path,
        base(
            id="test.v3.lagna",
            conditions={"in_sign": {"planet": "Lagna", "signs": ["Aries"]}},
            reference_cases=[{
                "moment": "2000-01-01T12:00:00Z", "expect": "silent", "note": "R",
                "place": {"lat": 27.7, "lon": 85.3, "tz": "Asia/Kathmandu"}}],
        ),
    )
    with compose.use_rules(tmp_path):
        rule = Rule.model_validate(base(conditions={"use": "test.v3.lagna"}))
    assert "place" in rule_inputs(rule)


def test_use_refuses_a_missing_id(tmp_path):
    """A missing parent is a validation error with a suggestion."""
    write_rule(tmp_path, parent())
    with compose.use_rules(tmp_path), pytest.raises(
        ValidationError, match="no rule 'test.v3.parnet'.*Did you mean 'test.v3.parent'"
    ):
        Rule.model_validate(child(use="test.v3.parnet"))


def test_use_refuses_a_cycle(tmp_path):
    """a -> b -> a, and a rule using itself, are errors."""
    a = base(id="test.v3.a", conditions={"use": "test.v3.b"})
    b = base(id="test.v3.b", conditions={"all": [{"use": "test.v3.a"}]})
    write_rule(tmp_path, a)
    write_rule(tmp_path, b)
    with compose.use_rules(tmp_path):
        with pytest.raises(ValidationError, match="use cycle: test.v3.a -> test.v3.b -> test.v3.a"):
            Rule.model_validate(a)
        with pytest.raises(ValidationError, match="use cycle: test.v3.self -> test.v3.self"):
            Rule.model_validate(base(id="test.v3.self", conditions={"use": "test.v3.self"}))
    assert compose.find_cycles(compose.raw_rules([tmp_path])) == [
        ["test.v3.a", "test.v3.b", "test.v3.a"]
    ]


def test_cycle_is_found_even_after_the_parent_was_cached(tmp_path):
    """Caching never hides a cycle introduced later."""
    write_rule(tmp_path, parent())
    with compose.use_rules(tmp_path):
        Rule.model_validate(child())  # caches test.v3.parent
        looped = parent(conditions={"all": [{"use": "test.v3.child"}]}, params={})
        write_rule(tmp_path, looped)
        write_rule(tmp_path, child())
        with pytest.raises(ValidationError, match="use cycle"):
            Rule.model_validate(child())


def test_use_refuses_a_parent_without_conditions(tmp_path):
    """A needs_predicates parent cannot be used."""
    write_rule(tmp_path, base(id="test.v3.todo", conditions=None, status="needs_predicates"))
    with compose.use_rules(tmp_path), pytest.raises(ValidationError, match="has no conditions"):
        Rule.model_validate(child(use="test.v3.todo"))


def test_version_pin_refuses_a_changed_parent(tmp_path):
    """use: {id, version} holds only while the parent stays at that version."""
    write_rule(tmp_path, parent())
    with compose.use_rules(tmp_path):
        Rule.model_validate(child(use={"id": "test.v3.parent", "version": 2}))
        write_rule(tmp_path, parent(version=3))
        with pytest.raises(ValidationError, match="pinned to version 2 .* version 3"):
            Rule.model_validate(child(use={"id": "test.v3.parent", "version": 2}))


def test_a_silently_changed_parent_changes_the_fingerprint(tmp_path):
    """Editing the parent's orb without a version bump is seen, not hidden."""
    write_rule(tmp_path, parent())
    with compose.use_rules(tmp_path):
        before = Rule.model_validate(child())
        changed = parent()
        changed["params"]["orb"]["value"] = 5
        write_rule(tmp_path, changed)  # same version 2
        after = Rule.model_validate(child())
    fp_a, fp_b = before.use_fingerprint(), after.use_fingerprint()
    assert [u["version"] for u in fp_a["uses"]] == [u["version"] for u in fp_b["uses"]] == [2]
    assert fp_a["sha256"] != fp_b["sha256"]
    assert after.conditions.all[0].resolved.conditions["all"][1]["conjunct_within"]["orb"] == 5


def test_fingerprint_lists_every_ancestor(tmp_path):
    """grandchild -> child -> parent: both ancestors appear, nearest first."""
    write_rule(tmp_path, parent())
    write_rule(tmp_path, child())
    with compose.use_rules(tmp_path):
        rule = Rule.model_validate(base(id="test.v3.grand", conditions={"use": "test.v3.child"}))
    assert [u["id"] for u in rule.use_fingerprint()["uses"]] == ["test.v3.child", "test.v3.parent"]
    assert [r.id for r in rule.uses] == ["test.v3.child"]


def test_use_round_trips_and_rebinds(tmp_path):
    """A dump keeps the leaf (not the expansion); bind re-resolves it."""
    write_rule(tmp_path, parent())
    data = child(params={"w": {"value": 1, "min": 0, "max": 3, "step": 1, "unit": "days"}},
                 window={"unit": "days", "after": "$w"})
    with compose.use_rules(tmp_path):
        rule = Rule.model_validate(data)
        dumped = rule.model_dump(by_alias=True, exclude_none=True)
        assert dumped["conditions"]["all"][0] == {"use": {"id": "test.v3.parent"}}
        dumped.pop("params")  # a dump holds bound values, not $w
        again = Rule.model_validate(dumped)
        rebound = rule.bind({"w": 2})
    assert again.conditions == rule.conditions
    assert rebound.window.after == 2 and isinstance(rebound.conditions.all[0], UseOf)


def test_use_takes_no_other_keys(tmp_path):
    """The expansion cannot be written by hand."""
    write_rule(tmp_path, parent())
    with compose.use_rules(tmp_path), pytest.raises(ValidationError):
        Rule.model_validate(base(conditions={"use": "test.v3.parent", "all": [{"in_sign": {"planet": "Sun", "signs": ["Leo"]}}]}))
    with compose.use_rules(tmp_path), pytest.raises(ValidationError, match="use"):
        Rule.model_validate(base(conditions={"use": {"id": "test.v3.parent", "pin": 2}}))


def test_use_in_a_rule_directory_loads_through_the_loader(tmp_path):
    """The loader validates a use leaf like any other condition."""
    write_rule(tmp_path, parent())
    write_rule(tmp_path, child())
    with compose.use_rules(tmp_path):
        loaded, problems = load_rules([tmp_path])
    assert not problems, "\n".join(str(p) for p in problems)
    assert {r.rule.id for r in loaded} == {"test.v3.parent", "test.v3.child"}


# ------------------------------------------------------- predicate discovery
def test_every_module_in_the_predicate_folder_is_imported():
    """Discovery covers the folder; the core modules keep their order."""
    from pathlib import Path

    import vedic_astrology_core.rules.predicates as pkg

    folder = Path(pkg.__file__).parent
    on_disk = {p.stem for p in folder.glob("*.py") if not p.stem.startswith("_")}
    assert set(MODULES) == on_disk
    assert MODULES[:6] == ["placement", "relations", "timing", "mundane", "samhita", "bhava"]
    assert "use" not in PREDICATES  # use is a reference, not a predicate


def _drop_in(tmp_path, name, body):
    pkg = tmp_path / "dropin_preds"
    pkg.mkdir(exist_ok=True)
    (pkg / "__init__.py").write_text("")
    (pkg / f"{name}.py").write_text(textwrap.dedent(body))
    return pkg


PREDICATE_MODULE = '''
from vedic_astrology_core.rules.predicates import Outcome, Params, predicate


class NoParams(Params):
    pass


@predicate("{name}", NoParams, category="test", example={{"{name}": {{}}}})
def always(ctx, params):
    """Always holds (test)."""
    return Outcome(True, "always")
'''


@pytest.fixture
def scratch_package(tmp_path, monkeypatch):
    """A throwaway package on sys.path; registered test predicates are removed."""
    monkeypatch.syspath_prepend(str(tmp_path))
    before = set(PREDICATES)
    yield tmp_path
    for name in set(PREDICATES) - before:
        PREDICATES.pop(name)
    for mod in [m for m in sys.modules if m.startswith("dropin_preds")]:
        sys.modules.pop(mod)


def test_a_dropped_in_module_is_registered_with_no_other_edit(scratch_package):
    """load_modules imports a new file and its predicate appears."""
    pkg = _drop_in(scratch_package, "zz_new", PREDICATE_MODULE.format(name="wp65_dropin"))
    names = load_modules(pkg, "dropin_preds")
    assert names == ["zz_new"]
    assert PREDICATES["wp65_dropin"].category == "test"


def test_a_duplicate_predicate_name_fails(scratch_package):
    """A module registering an existing name raises and names both modules."""
    pkg = _drop_in(scratch_package, "dup", PREDICATE_MODULE.format(name="in_sign"))
    with pytest.raises(ValueError, match="'in_sign' registered twice.*placement.*dropin_preds.dup"):
        load_modules(pkg, "dropin_preds")
