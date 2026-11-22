"""Case file builder and renderers (ADR-006 WP-54)."""

import copy
import json
import re
import shutil
from dataclasses import replace
from datetime import datetime, timezone

import pytest

from vedic_astrology_core.mundane import casefile as cf
from vedic_astrology_core.mundane import factors as fx
from vedic_astrology_core.mundane import render as rd
from vedic_astrology_core.mundane.registry import ChartNotApplicable, load_charts, load_events
from vedic_astrology_core.rules.context import Sky

NINE = ("event", "natal", "dasha", "transits", "event_sky", "annual", "factors", "claims", "provenance")


@pytest.fixture(scope="module")
def charts():
    return {c.chart_id: c for c in load_charts()}


@pytest.fixture(scope="module")
def events():
    return {e.event_id: e for e in load_events()}


@pytest.fixture(scope="module")
def gorkha(events):
    return events["usgs:us20002926"]


@pytest.fixture(scope="module")
def india(gorkha, charts):
    return cf.build_casefile(gorkha, charts["in-1947-midnight"], commit="test")


@pytest.fixture(scope="module")
def nepal(gorkha, charts):
    return cf.build_casefile(gorkha, charts["np-2008-republic"], commit="test")


# ------------------------------------------------------------------ schema
def test_json_validates_and_has_nine_sections(india, nepal):
    for case in (india, nepal):
        assert cf.validate_casefile(case) == []
        assert case["schema"] == "casefile/1"
        assert [s["number"] for s in case["sections"]] == list(range(1, 10))
        for key in NINE:
            assert key in case
        # A section that cannot be computed says why.
        for s in case["sections"]:
            assert (s["reason"] is None) == s["computable"], s
    assert not india["annual"]["computable"] and "Phase 2" in india["annual"]["reason"]
    assert not india["claims"]["computable"] and "claims registry" in india["claims"]["reason"]


def test_json_round_trips_and_is_stable(india, tmp_path):
    path = cf.write_casefile(india, tmp_path)
    assert path.name == "usgs_us20002926__in-1947-midnight.json"
    assert json.loads(path.read_text(encoding="utf-8")) == india
    assert path.read_text(encoding="utf-8") == cf.dumps(india)


def test_validator_rejects_broken_documents(india):
    bad = copy.deepcopy(india)
    del bad["factors"]
    assert any("factors" in e for e in cf.validate_casefile(bad))
    bad = copy.deepcopy(india)
    bad["annual"]["reason"] = None  # not computable, no reason
    assert cf.validate_casefile(bad)
    bad = copy.deepcopy(india)
    bad["surprise"] = 1
    assert any("surprise" in e for e in cf.validate_casefile(bad))
    bad = copy.deepcopy(india)
    bad["factors"]["rows"][0]["citation_status"] = "trusted"
    assert cf.validate_casefile(bad)


# ----------------------------------------------------------- content
def test_header_and_founding_table(india):
    assert india["event"]["event_id"] == "usgs:us20002926"
    assert india["chart"]["grade"] == "C" and india["chart"]["half_window_minutes"] == 60
    nat = india["natal"]
    assert nat["has_lagna"] and nat["vargas"] == ["D1", "D9"]
    lagna = next(p for p in nat["points"] if p["point"] == "Lagna")
    assert lagna["vargas"]["D1"]["sign"] == "Taurus" and lagna["vargas"]["D1"]["house"] == 1
    # Every graha has D1 and D9 sign, house, dignity, nakshatra, pada, combust marker.
    sun = next(p for p in nat["points"] if p["point"] == "Sun")
    assert set(sun["vargas"]) == {"D1", "D9"} and sun["nakshatra"] and sun["pada"] in (1, 2, 3, 4)
    # A 60-minute window moves the D9 lagna: the cell is marked and lists its values.
    d9 = lagna["vargas"]["D9"]
    assert not d9["stable"] and d9["alternatives"]


def test_dasha_and_transit_sections(india):
    d = india["dasha"]
    assert d["computable"] and [lv["level"] for lv in d["levels"]] == [1, 2, 3]
    lv2 = d["levels"][1]
    assert lv2["lord"] == "Venus" and lv2["lord_state"]["D1"]["house"] in range(1, 13)
    assert lv2["lord_state"]["D1"]["houses_ruled"]
    t = india["transits"]
    assert t["computable"] and len(t["positions"]) == 9
    assert all(p["house_from_moon"] in range(1, 13) for p in t["positions"])
    assert set(t["readings"]["extended"]) == {"transit.over_varga", "transit.in_varga"}
    assert india["event_sky"]["computable"] and india["event_sky"]["weekday_lord"]["value"] == "Saturn"


def test_every_fired_factor_carries_its_fields(india):
    f = india["factors"]
    assert f["computable"] and f["tests_declared"] == 18
    assert len(f["rows"]) + len(f["not_evaluated"]) == 18
    assert f["rows"], "India grade C should fire the plan's factors"
    for r in f["rows"]:
        assert r["method"] in [m["id"] for m in r["methods"]]
        assert r["citation_status"] == "unverified" and r["level"] == "L0"
        assert isinstance(r["stable"], bool)
        assert r["evidence"]
        assert 0.0 <= r["base_rate"]["value"] <= 1.0 and r["base_rate"]["dates"] > 2000
    by_id = {r["factor_id"]: r for r in f["rows"]}
    assert by_id["dasha.identity.antar:Venus"]["evidence"].startswith("the running Vimshottari period is Sun-Venus")
    # Grade C: the lagna and the pratyantar move inside the window, so the main-table flag is false.
    assert not by_id["transit.saturn.from_lagna.d1:7"]["stable"]
    assert by_id["transit.saturn.from_moon.d1:5"]["stable"]


def test_base_rate_matches_an_independent_calendar_count(gorkha, charts):
    from vedic_astrology_core.dasha.vimshottari import compute_vimshottari_nested_periods

    chart = charts["in-1947-midnight"]
    plan = fx.load_plan()
    test = next(t for t in fx.plan_tests(plan) if t.test_id == "dasha.identity.antar")
    prep = fx._Prepared(test)
    got = fx.base_rate(prep, "Venus", chart, plan)
    natal = Sky(fx.chart_moment(chart), fx.Location(chart.lat, chart.lon, "UTC"))
    periods = compute_vimshottari_nested_periods(natal.moment, natal.lon("Moon"), depth=2)
    dates = fx.base_rate_dates(chart, plan)
    hits = sum(any(p["start"] <= d < p["end"] and p["lords"][1] == "Venus" for p in periods) for d in dates)
    assert got["dates"] == len(dates) and got["true_dates"] == hits


def test_grade_d_chart_says_why(nepal):
    assert nepal["chart"]["grade"] == "D"
    assert nepal["dasha"]["all_levels_unsupported"]
    ne = {n["test_id"]: n["reason"] for n in nepal["factors"]["not_evaluated"]}
    assert "grade D" in ne["dasha.house.antar.d1"]
    assert "no lagna" in ne["transit.saturn.from_lagna.d1"]
    assert {r["test_id"] for r in nepal["factors"]["rows"]} == {
        "transit.mars.from_moon.d1", "transit.jupiter.from_moon.d1",
        "transit.saturn.from_moon.d1", "transit.rahu.from_moon.d1",
    }
    lagna_rows = [p for p in nepal["natal"]["points"] if p["point"] == "Lagna"]
    assert lagna_rows == []
    assert all(p["house_from_lagna"] is None for p in nepal["transits"]["positions"])


def test_sections_that_cannot_be_computed_carry_reasons(gorkha, charts):
    ch = charts["np-2008-republic"]
    month = replace(gorkha, time_precision="month")
    case = cf.build_casefile(month, ch, commit="test")
    assert cf.validate_casefile(case) == []
    for key in ("dasha", "transits", "event_sky", "factors"):
        assert not case[key]["computable"] and "month" in case[key]["reason"], key
    noplace = replace(gorkha, lat=None, lon=None)
    case = cf.build_casefile(noplace, ch, commit="test")
    assert not case["event_sky"]["computable"] and "place" in case["event_sky"]["reason"]
    d5 = cf.build_casefile(gorkha, ch, vargas=("D1", "D5"), commit="test")
    assert not d5["natal"]["computable"] and "not cited" in d5["natal"]["reason"]
    assert cf.validate_casefile(d5) == []


def test_chart_is_refused_before_valid_from(gorkha, charts):
    early = replace(gorkha, time_utc=datetime(1940, 1, 1, tzinfo=timezone.utc))
    with pytest.raises(ChartNotApplicable):
        cf.build_casefile(early, charts["in-1947-midnight"], commit="test")


def test_supplied_base_rates_are_used_and_null_keeps_the_field(gorkha, charts):
    ch = charts["np-2008-republic"]
    case = cf.build_casefile(gorkha, ch, commit="test", base_rates={f"transit.saturn.from_moon.d1:{h}": None for h in range(1, 13)})
    row = next(r for r in case["factors"]["rows"] if r["test_id"] == "transit.saturn.from_moon.d1")
    assert row["base_rate"] == {"value": None, "reason": "base rate from WP-55 aggregate"}
    assert cf.validate_casefile(case) == []


def test_claims_are_filtered_to_the_event(gorkha, charts):
    claims = [
        {"claim_id": "c1", "event_ids": ["usgs:us20002926"], "timing_class": "after"},
        {"claim_id": "c2", "event_ids": ["usgs:other"], "timing_class": "before"},
    ]
    case = cf.build_casefile(gorkha, charts["np-2008-republic"], commit="test", claims=claims)
    assert case["claims"]["computable"] and [c["claim_id"] for c in case["claims"]["rows"]] == ["c1"]


def test_provenance_hashes(india):
    p = india["provenance"]
    for k in ("charts_sha256", "events_sha256", "catalogue_sha256", "plan_sha256"):
        assert re.fullmatch(r"[0-9a-f]{64}", p[k])
    assert p["commit"] == "test" and p["dasha_year"] == "julian"


# ------------------------------------------------------------- rendering
def test_html_is_self_contained_and_deterministic(india):
    h1, h2 = rd.render_html(india), rd.render_html(india)
    assert h1 == h2
    assert h1.startswith("<!DOCTYPE html>")
    for forbidden in ("<script", "<link", " src=", "@import", "url(", "<iframe"):
        assert forbidden not in h1, forbidden
    for n in range(1, 10):
        assert f'id="s{n}"' in h1
    assert "Not computable." in h1  # annual and claims


def test_html_labels_unverified_and_extended(india):
    h = rd.render_html(india)
    assert 'class="badge b-unverified"' in h
    assert "extended: not cited, never in a test" in h  # the extended transit readings
    case = copy.deepcopy(india)
    case["factors"]["rows"][0]["tier"] = "extended"
    assert "extended: not cited" in rd.render_html(case)
    assert "unstable" in h  # marked cells


def test_rendering_never_recomputes(india, monkeypatch):
    def boom(*a, **k):
        raise AssertionError("render computed a sky")

    monkeypatch.setattr(Sky, "__init__", boom)
    monkeypatch.setattr(cf, "founding_table", boom)
    monkeypatch.setattr(cf, "fired_factors", boom)
    assert rd.render_html(india)
    assert rd.render_markdown(india)


def test_html_file_matches_function(india, tmp_path):
    jpath = cf.write_casefile(india, tmp_path)
    hpath = rd.render_html_file(jpath)
    assert hpath.suffix == ".html"
    assert hpath.read_text(encoding="utf-8") == rd.render_html(india)
    first = hpath.read_bytes()
    assert rd.render_html_file(jpath).read_bytes() == first


def test_pdf_skipped_with_message_when_quarto_absent(india, tmp_path, monkeypatch):
    jpath = cf.write_casefile(india, tmp_path)
    monkeypatch.setattr(shutil, "which", lambda name: None)
    res = rd.render_pdf(jpath)
    assert res.skipped and res.path is None and "Quarto is not installed" in res.message
    assert not list(tmp_path.glob("*.pdf"))


@pytest.mark.skipif(shutil.which("quarto") is None, reason="Quarto not installed")
def test_pdf_from_json_with_quarto(nepal, tmp_path):
    jpath = cf.write_casefile(nepal, tmp_path)
    res = rd.render_pdf(jpath)
    assert not res.skipped, res.message
    assert res.path.read_bytes().startswith(b"%PDF")
