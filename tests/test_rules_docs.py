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
