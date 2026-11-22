"""Transit table (WP-53): readings per catalogue method, windows and extended block."""

from dataclasses import replace

import pytest

from vedic_astrology_core.mundane import transits as tr
from vedic_astrology_core.mundane.registry import load_charts, load_events
from vedic_astrology_core.rules.vocabulary import SIGN_NAMES


@pytest.fixture(scope="module")
def gorkha():
    return next(e for e in load_events() if e.event_id == "usgs:us20002926")


@pytest.fixture(scope="module")
def charts():
    return {c.chart_id: c for c in load_charts()}


def test_blocks_and_methods(gorkha, charts):
    t = tr.transit_table(gorkha, charts["in-1950-republic"])
    assert t["computable"]
    assert set(t["readings"]["core"]) == set(tr.CORE_READINGS)
    assert set(t["readings"]["extended"]) == set(tr.EXTENDED_READINGS)
    for block in t["readings"].values():
        for reading in block.values():
            assert reading["method"]["citation_status"] in ("unverified", "page_cited", "verified")
    assert {r["graha"] for r in t["positions"]} == {
        "Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"}
    for reading in t["readings"]["extended"].values():
        assert reading["method"]["tier"] == "extended"


def test_house_arithmetic(gorkha, charts):
    t = tr.transit_table(gorkha, charts["in-1950-republic"])
    moon = {r["graha"]: r for r in t["readings"]["core"]["transit.gochara_moon"]["rows"]}
    pos = {r["graha"]: r for r in t["positions"]}
    assert pos["Moon"]["sign"] == "Cancer"
    natal = SIGN_NAMES.index(
        t["readings"]["core"]["transit.gochara_moon"]["natal_moon_sign_values"][0])
    assert moon["Moon"]["house"] == (3 - natal) % 12 + 1
    for r in moon.values():
        assert 1 <= r["house"] <= 12
        assert r["house"] in r["houses_across_windows"]


def test_ketu_opposite_rahu(gorkha, charts):
    t = tr.transit_table(gorkha, charts["in-1950-republic"])
    pos = {r["graha"]: r["longitude"] for r in t["positions"]}
    assert abs(((pos["Rahu"] - pos["Ketu"]) % 360) - 180) < 1e-3


def test_date_only_chart_marks_unstable(gorkha, charts):
    t = tr.transit_table(gorkha, charts["np-2008-republic"])
    assert t["chart_grade"] == "D" and t["natal_time_known"] is False
    lagna = t["readings"]["core"]["transit.from_lagna"]
    assert len(lagna["natal_lagna_sign_values"]) > 1
    assert all(r["stable"] is False for r in lagna["rows"])
    ext = t["readings"]["extended"]["transit.over_varga"]
    assert ext["note"] and len(ext["natal_d9_lagna_values"]) > 1


def test_day_precision_event_marks_fast_transit(gorkha, charts):
    ev = replace(gorkha, time_precision="day")
    t = tr.transit_table(ev, charts["in-1950-republic"])
    moon = next(r for r in t["readings"]["core"]["transit.gochara_moon"]["rows"] if r["graha"] == "Moon")
    slow = next(r for r in t["readings"]["core"]["transit.gochara_moon"]["rows"] if r["graha"] == "Saturn")
    assert slow["fast"] is False
    pos = next(r for r in t["positions"] if r["graha"] == "Moon")
    assert (len(pos["signs_across_window"]) > 1) == moon["fast"]


def test_month_precision_and_excluded_chart(gorkha, charts):
    assert tr.transit_table(replace(gorkha, time_precision="month"), charts["in-1950-republic"])["computable"] is False
    x = replace(charts["in-1950-republic"], date_disputed=True)
    out = tr.transit_table(gorkha, x)
    assert out["computable"] is False and "grade X" in out["reason"]


def test_conjunct_rows_shape(gorkha, charts):
    t = tr.transit_table(gorkha, charts["in-1950-republic"], orb=40.0)
    rows = t["readings"]["core"]["transit.conjunct_natal"]["rows"]
    assert rows and all({"graha", "natal_point", "held_at_nominal", "stable"} <= set(r) for r in rows)
