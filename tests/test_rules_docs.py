"""CONTRIBUTING_ASTROLOGERS.md stays true: its example runs, its table is complete."""

import re
from pathlib import Path

from vedic_astrology_core.rules import PREDICATES
from vedic_astrology_core.rules.cli import main

REPO = Path(__file__).parent.parent
DOC = (REPO / "CONTRIBUTING_ASTROLOGERS.md").read_text()
EXAMPLE = Path(__file__).parent / "fixtures" / "rules" / "docs_example"


def _body(text):
    """Drop the yaml-language-server line, whose relative path differs."""
    return "\n".join(text.strip().splitlines()[1:])


def test_worked_example_matches_the_tested_fixture():
    """The YAML in the guide is the fixture that the next test runs."""
    block = re.search(r"```yaml\n(.*?)```", DOC, re.S).group(1)
    fixture = (EXAMPLE / "jupiter_kendra_from_moon.yaml").read_text()
    assert _body(block) == _body(fixture)


def test_worked_example_passes(capsys):
    """astro-rules test on the example passes, as the guide shows."""
    assert main(["test", str(EXAMPLE)]) == 0
    assert "PASS financial.gold.jupiter_kendra_from_moon (2 cases)" in (
        capsys.readouterr().out
    )


def test_vocabulary_table_lists_every_predicate():
    """Each predicate has a row with an example."""
    for name in PREDICATES:
        assert f"| `{name}` |" in DOC, name


def test_issue_template_exists():
    """The guide points to a real issue template."""
    template = REPO / ".github" / "ISSUE_TEMPLATE" / "propose-rule.yml"
    assert "Propose a rule" in template.read_text()


def _table_rows():
    """Rows of the predicate table: (name, kind, example YAML)."""
    rows = []
    for line in DOC.splitlines():
        m = re.match(r"^\| `([a-z_]+)` \| (\w+) \| .* \| `(\{.*\})` \|$", line)
        if m:
            rows.append(m.groups())
    return rows


def test_predicate_table_has_no_stale_rows():
    """Every row names a registered predicate, once, with its category."""
    rows = _table_rows()
    names = [r[0] for r in rows]
    assert len(names) == len(set(names))
    assert set(names) == set(PREDICATES)
    for name, kind, _ in rows:
        assert PREDICATES[name].category == kind, name


def test_predicate_table_examples_validate():
    """Each example in the table is valid YAML for its predicate's parameters."""
    import yaml

    for name, _, example in _table_rows():
        parsed = yaml.safe_load(example)
        assert list(parsed) == [name], name
        PREDICATES[name].params.model_validate(parsed[name])


def test_workbench_chapter_names_real_commands():
    """The tune-and-validate chapter uses the CLI's own subcommands."""
    from vedic_astrology_core.rules.cli import build_parser

    chapter = DOC.split("## Tune and validate a rule", 1)[1].split("\n## ", 1)[0]
    used = set(re.findall(r"\$ astro-rules (\w+)", chapter))
    commands = set(build_parser()._subparsers._group_actions[0].choices)
    assert {"fit", "confirm", "dose", "review"} <= used
    assert used <= commands


def test_new_predicate_examples_in_the_chapter_validate():
    """The one-line examples of the new predicates are valid conditions."""
    import yaml

    from vedic_astrology_core.rules.schema import Rule

    chapter = DOC.split("## Tune and validate a rule", 1)[1].split("\n## ", 1)[0]
    block = chapter.split("### New predicates", 1)[1]
    examples = re.findall(r"^    (\{[a-z_]+: .*\})$", block, re.M)
    assert len(examples) >= 15
    base = {
        "id": "docs.example",
        "name": "n",
        "domain": "mundane",
        "claim": "c",
        "source": {"text": "docs"},
        "author": "docs",
        "tier": "experimental",
        "reference_cases": [
            {"moment": "2000-01-01T00:00:00Z", "expect": "fires", "note": "n"}
        ],
    }
    for text in examples:
        Rule.model_validate(dict(base, conditions=yaml.safe_load(text)))
