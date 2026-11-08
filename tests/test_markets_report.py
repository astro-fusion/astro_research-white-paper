"""markets.report: paper text follows results.json, whatever the outcome."""

import copy
import json
from pathlib import Path

import pytest

from vedic_astrology_core.markets import report

REPO = Path(__file__).resolve().parent.parent
RESULTS = REPO / "studies" / "gold_market" / "artifacts" / "results.json"
pytestmark = pytest.mark.skipif(not RESULTS.exists(), reason="pipeline not run")


@pytest.fixture
def res():
    """Load the committed gold results."""
    return json.loads(RESULTS.read_text())


def test_verdict_sentence_follows_outcome(res):
    """Check each verdict produces its own wording."""
    for verdict, word in (("null", "**null**"), ("not_replicated", "not replicated"),
                          ("positive", "**positive**"), ("mixed", "**mixed**")):
        r = copy.deepcopy(res)
        r["headline"]["verdict"] = verdict
        assert word in report.verdict_sentence(r)


def test_tables_are_markdown_with_numbers_from_results(res):
    """Check tables carry the result values and pipe syntax."""
    table = report.tests_table(res, "explore", top=3)
    lines = table.splitlines()
    assert len(lines) == 5 and lines[1].startswith("|---")
    best = min((t for t in res["tests"] if t["period"] == "explore" and t["testable"]),
               key=lambda t: t["p_value"])
    assert best["indicator"].replace("_", " ") in lines[2]
    assert report.headline_table(res).count("\n") == 7
    assert res["data"]["sha256"][:16] in report.data_paragraph(res)


def test_provisional_banner_only_when_provisional(res):
    """Check the warning appears only for fixture runs."""
    r = copy.deepcopy(res)
    r["provisional"] = False
    assert report.provisional_banner(r) == ""
    r["provisional"] = True
    assert "PROVISIONAL" in report.provisional_banner(r)
    assert "PROVISIONAL" in report.discussion(r)


def test_indicator_table_lists_the_family():
    """Check the pre-registered family is printed in full."""
    table = report.indicator_table(REPO / "studies/gold_market/hypothesis.yaml")
    assert table.count("\n") == 15 and "Shukra-Guru-Wealth" in table
