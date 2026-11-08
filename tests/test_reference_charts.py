"""Tests for shared reference charts."""

from datetime import date
from pathlib import Path

from vedic_astrology_core.config.reference_charts import (
    get_reference_chart,
    get_reference_charts,
)

REPO = Path(__file__).resolve().parents[1]


def test_reference_chart_keys():
    """Test that all expected reference chart keys are present."""
    charts = get_reference_charts()
    assert "india_independence" in charts
    assert "nepal_constitution_2015" in charts
    assert "global_baseline_2000" in charts


def test_reference_chart_metadata():
    """Test that reference chart metadata corresponds to expected values."""
    india = get_reference_chart("india_independence")
    nepal = get_reference_chart("nepal_constitution_2015")
    global_chart = get_reference_chart("global_baseline_2000")

    assert india.timezone == "Asia/Kolkata"
    assert nepal.timezone == "Asia/Kathmandu"
    assert global_chart.timezone == "UTC"
    assert india.latitude != nepal.latitude


def test_nepal_constitution_time_is_not_invented():
    """Promulgation date is sourced; the hour is not, so no datetime is given."""
    nepal = get_reference_chart("nepal_constitution_2015")
    assert nepal.date == date(2015, 9, 20)
    assert nepal.time_known is False
    assert nepal.datetime is None
    assert nepal.source == "chart_thehimalayantimes_126755"
    assert nepal.source in (REPO / "papers" / "sources.bib").read_text()


def test_charts_with_a_known_time_are_timezone_aware():
    """A chart either has an aware datetime on its date or no time at all."""
    for chart in get_reference_charts().values():
        if chart.time_known:
            assert chart.datetime is not None and chart.datetime.tzinfo is not None
            assert chart.datetime.date() == chart.date
        else:
            assert chart.datetime is None
