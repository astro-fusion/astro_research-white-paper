"""Tests for shared reference charts."""

from vedic_astrology_core.config.reference_charts import (
    get_reference_chart,
    get_reference_charts,
)


def test_reference_chart_keys():
    charts = get_reference_charts()
    assert "india_independence" in charts
    assert "nepal_constitution_2015" in charts
    assert "global_baseline_2000" in charts


def test_reference_chart_metadata():
    india = get_reference_chart("india_independence")
    nepal = get_reference_chart("nepal_constitution_2015")
    global_chart = get_reference_chart("global_baseline_2000")

    assert india.timezone == "Asia/Kolkata"
    assert nepal.timezone == "Asia/Kathmandu"
    assert global_chart.timezone == "UTC"
    assert india.latitude != nepal.latitude
