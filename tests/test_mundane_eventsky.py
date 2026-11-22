"""Event-time sky chart (WP-53): known dates, window marking and the D2 guard."""

from dataclasses import replace
from datetime import datetime, timezone

import pytest

from vedic_astrology_core.mundane import eventsky as es
from vedic_astrology_core.mundane.catalogue import CatalogueError, load_catalogue
from vedic_astrology_core.mundane.registry import load_events


@pytest.fixture(scope="module")
def events():
    return load_events()


@pytest.fixture(scope="module")
def gorkha(events):
    return next(e for e in events if e.event_id == "usgs:us20002926")


def test_gorkha_sky_known_facts(gorkha):
    """25 April 2015 was a Saturday, Shukla 7, in samvatsara Manmatha."""
    sky = es.event_sky(gorkha)
    assert sky["computable"] and sky["lagna"]["computed"]
    assert sky["weekday_lord"]["value"] == "Saturn"
    assert sky["tithi"]["name"] == "Shukla 7"
    assert sky["samvatsara"]["name"] == "Manmatha"
    assert sky["mandala"]["value"] == "vayu"  # Punarvasu is in the Vayu circle
    assert sky["moon_nakshatra"]["value"] == "Punarvasu"
    assert sky["eclipses"]["before"]["kind"] == "lunar"
    assert sky["eclipses"]["before"]["days_from_event"] < 0 < sky["eclipses"]["after"]["days_from_event"]
    assert all(sky["methods"][m]["citation_status"] for m in es.SKY_METHODS)


def test_day_precision_has_no_lagna_and_marks_fast_factors(gorkha):
    ev = replace(gorkha, time_precision="day",
                 time_utc=datetime(2015, 4, 25, 0, 0, tzinfo=timezone.utc))
    sky = es.event_sky(ev)
    assert sky["lagna"]["computed"] is False and "hour" in sky["lagna"]["reason"]
    # a 24 hour window crosses a vara boundary (sunrise) and several tithi/Moon steps
    assert sky["weekday_lord"]["stable"] is False
    assert len(sky["weekday_lord"]["values_across_window"]) == 2


def test_no_place_no_lagna(gorkha):
    sky = es.event_sky(replace(gorkha, lat=None, lon=None))
    assert sky["lagna"]["computed"] is False and sky["weekday_lord"]["convention"] == "utc_civil_day"


def test_month_precision_not_computable(gorkha):
    sky = es.event_sky(replace(gorkha, time_precision="month"))
    assert sky["computable"] is False and "excluded" in sky["reason"]


def test_naive_datetime_refused(gorkha):
    with pytest.raises(ValueError):
        es.event_sky(replace(gorkha, time_utc=datetime(2015, 4, 25, 6, 11)))


def test_polygon():
    assert es.in_himalayan_polygon(28.23, 84.73)  # Gorkha
    assert not es.in_himalayan_polygon(35.0, 139.0)  # Japan
    assert not es.in_himalayan_polygon(None, None)


def test_aggregate_count_blocked_outside_polygon(gorkha):
    outside = replace(gorkha, event_id="usgs:outside", lat=35.0, lon=139.0)
    with pytest.raises(es.EventSkyGuardError):
        es.count_event_sky_factor([gorkha, outside], lambda s: True, d2_confirmed=False)
    # no place at all counts as outside
    with pytest.raises(es.EventSkyGuardError):
        es.count_event_sky_factor([replace(gorkha, lat=None, lon=None)], lambda s: True, d2_confirmed=False)


def test_aggregate_count_default_guard_is_closed():
    assert es.d2_confirm_recorded() is False or es.D2_CONFIRM_RECORD.exists()


def test_aggregate_count_inside_polygon_and_after_confirm(gorkha):
    assert es.count_event_sky_factor([gorkha], lambda s: s["mandala"]["value"] == "vayu", d2_confirmed=False) == 1
    outside = replace(gorkha, event_id="usgs:outside", lat=35.0, lon=139.0)
    assert es.count_event_sky_factor([gorkha, outside], lambda s: True, d2_confirmed=True) == 2


def test_confirm_record_file(tmp_path):
    p = tmp_path / "rec.json"
    assert es.d2_confirm_recorded(p) is False
    p.write_text('{"confirm_run_id": ""}')
    assert es.d2_confirm_recorded(p) is False
    p.write_text('{"confirm_run_id": "run-1"}')
    assert es.d2_confirm_recorded(p) is True


def test_non_sky_method_refused(gorkha):
    with pytest.raises(es.EventSkyError):
        es.count_event_sky_factor([gorkha], lambda s: True, method_id="transit.gochara_moon", d2_confirmed=True)
    with pytest.raises(CatalogueError):
        es.count_event_sky_factor([gorkha], lambda s: True, method_id="sky.nope", d2_confirmed=True)


def test_catalogue_gives_status(gorkha):
    cat = load_catalogue()
    assert es.method_info(cat, "sky.eclipse")["tier"] == "core"
