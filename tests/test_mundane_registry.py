"""Tests for the mundane chart and event registries (ADR-006 WP-49)."""

import copy
import json
from datetime import datetime, timezone

import pytest
import yaml

from studies._paths import REPO_ROOT
from studies.mundane.scripts import build_registry as br
from vedic_astrology_core.mundane import registry as reg

COUNTRIES = REPO_ROOT / "studies" / "mundane" / "data" / "countries.yaml"


def _chart(**over):
    base = {
        "chart_id": "xx-test",
        "country_iso": "XX",
        "event": "Test",
        "founding": {
            "date": "1947-08-15",
            "time": "00:00:00",
            "time_zone": "Asia/Kolkata",
            "place": "New Delhi",
            "lat": 28.6139,
            "lon": 77.209,
        },
        "time_evidence": {
            "kind": "primary_record",
            "stated_precision_minutes": 1,
            "source": {
                "title": "Gazette",
                "url": "https://example.org/g",
                "archive_url": "https://web.archive.org/x",
                "accessed": "2026-01-01",
                "quote": "q",
            },
            "checked_by": "maintainer",
            "checked_at": "2026-01-02",
            "rectified": False,
            "rectification_published": None,
        },
        "half_window_minutes": None,
        "used_by": [],
        "claimed_confidence": "documented",
        "valid_from": "1947-08-15",
        "notes": "",
    }
    base["chart_id"] = "in-test"
    base["country_iso"] = "IN"
    for k, v in over.items():
        if k in base["time_evidence"] and k not in base:
            base["time_evidence"][k] = v
        elif k in base["founding"] and k not in base:
            base["founding"][k] = v
        else:
            base[k] = v
    return reg.parse_chart(base)


def test_grade_a():
    """Checked primary record with an archive capture, to the minute."""
    c = _chart()
    assert c.grade == "A"
    assert c.half_window == 2.0


def test_grade_b():
    """Checked press source, 15 minutes."""
    c = _chart(kind="press", stated_precision_minutes=10)
    assert c.grade == "B"
    assert c.half_window == 15.0


def test_grade_c_hour_known():
    """Time known to the hour."""
    c = _chart(
        kind="secondary", stated_precision_minutes=60, checked_by=None, checked_at=None
    )
    assert c.grade == "C"
    assert c.half_window == 60.0


def test_grade_d_date_only():
    """Date only."""
    c = _chart(time=None, kind="none", stated_precision_minutes=None,
               checked_by=None, checked_at=None)
    assert c.grade == "D"
    assert c.half_window == 720.0


def test_grade_r_rectified():
    """Rectified charts are grade R; the half-window follows the author."""
    c = _chart(kind="rectified", rectified=True, stated_precision_minutes=5)
    assert c.grade == "R"
    assert c.half_window == 5.0


def test_grade_x_disputed_date():
    """A disputed date is grade X with no window."""
    c = _chart(date_disputed=True)
    assert c.grade == "X"
    assert c.half_window is None


def test_unchecked_source_never_above_c():
    """Even a primary record to the minute grades C if nobody opened it."""
    c = _chart(checked_by=None, checked_at=None)
    assert c.grade == "C"
    c2 = _chart(kind="press", stated_precision_minutes=1, checked_by=None, checked_at=None)
    assert c2.grade == "C"


def test_primary_without_archive_is_b_not_a():
    """Grade A needs the archive URL."""
    c = _chart(source={"title": "t", "url": "u", "archive_url": None,
                       "accessed": None, "quote": None})
    assert c.grade == "B"


def test_half_window_override():
    """An explicit half-window wins over the grade default."""
    assert _chart(half_window_minutes=7).half_window == 7.0


def test_grade_cannot_be_typed():
    """A typed grade is a schema error."""
    with pytest.raises(reg.RegistryError, match="computed"):
        _chart(grade="A")


def test_unknown_key_rejected():
    """Unknown keys fail."""
    with pytest.raises(reg.RegistryError, match="unknown"):
        _chart(colour="red")


def test_date_only_needs_none_kind():
    """A date-only chart cannot claim a time source kind."""
    with pytest.raises(reg.RegistryError):
        _chart(time=None, kind="secondary")


def test_chart_refused_before_valid_from():
    """An event before valid_from is refused; naive datetimes raise."""
    c = _chart()
    with pytest.raises(reg.ChartNotApplicable):
        reg.chart_applies(c, datetime(1947, 8, 14, 12, tzinfo=timezone.utc))
    assert reg.chart_applies(c, datetime(1947, 8, 16, tzinfo=timezone.utc))
    with pytest.raises(ValueError, match="naive"):
        reg.chart_applies(c, datetime(1947, 8, 16))


def test_chart_refused_before_founding_moment_same_day():
    """The founding moment, not just the date, bounds applicability."""
    c = _chart(time="12:00:00", valid_from="1947-08-15")
    with pytest.raises(reg.ChartNotApplicable):
        reg.chart_applies(c, datetime(1947, 8, 15, 3, 0, tzinfo=timezone.utc))


def test_valid_from_after_founding_date_enforced():
    """valid_from may not precede the founding date."""
    with pytest.raises(reg.RegistryError, match="valid_from"):
        _chart(valid_from="1947-08-14")


def test_rectified_excluded_before_publication():
    """A rectified chart is aggregate-eligible only after an archived publication."""
    src = {"title": "t", "url": "u", "archive_url": "https://web.archive.org/y",
           "accessed": None, "quote": None}
    c = _chart(kind="rectified", rectified=True, rectification_published="2000-01-01",
               source=src, stated_precision_minutes=5)
    before = datetime(1999, 6, 1, tzinfo=timezone.utc)
    after = datetime(2001, 6, 1, tzinfo=timezone.utc)
    assert not reg.aggregate_eligible(c, before)
    assert reg.aggregate_eligible(c, after)
    # no archive proof: never eligible
    c2 = _chart(kind="rectified", rectified=True, rectification_published="2000-01-01",
                source=dict(src, archive_url=None), stated_precision_minutes=5)
    assert not reg.aggregate_eligible(c2, after)
    # no publication date: never eligible
    c3 = _chart(kind="rectified", rectified=True, stated_precision_minutes=5, source=src)
    assert not reg.aggregate_eligible(c3, after)


def test_grade_x_never_aggregate():
    """Grade X is excluded."""
    c = _chart(date_disputed=True)
    assert not reg.aggregate_eligible(c, datetime(2000, 1, 1, tzinfo=timezone.utc))


def test_lmt_converted_from_longitude():
    """LMT uses longitude / 15 hours."""
    c = _chart(time="12:00:00", time_zone="LMT", lon=-75.15, lat=39.9489)
    inst = c.founding_instant()
    assert inst == datetime(1947, 8, 15, 12, 0, tzinfo=timezone.utc) + __import__(
        "datetime"
    ).timedelta(hours=75.15 / 15)


def test_zone_conversion_and_date_only():
    """IANA zone converts; date-only has no instant."""
    c = _chart()
    assert c.founding_instant() == datetime(1947, 8, 14, 18, 30, tzinfo=timezone.utc)
    d = _chart(time=None, kind="none", stated_precision_minutes=None,
               checked_by=None, checked_at=None)
    assert d.founding_instant() is None


def test_unknown_zone_rejected():
    """Unknown zone names fail."""
    with pytest.raises(reg.RegistryError, match="time zone"):
        _chart(time_zone="Mars/Olympus")


# ------------------------------------------------------------ seeded files
def test_seeded_charts_load_and_grade():
    """Seeded charts load; India midnight is C, Nepal date-only charts are D, none above C."""
    charts = {c.chart_id: c for c in reg.load_charts()}
    assert set(charts) == set(br.CHART_IDS.values())
    assert charts["in-1947-midnight"].grade == "C"
    assert charts["in-1947-midnight"].half_window == 60.0
    assert charts["np-2008-republic"].grade == "D"
    assert charts["np-2015-constitution"].grade == "D"
    # Owner's Maitreya chart file: unchecked secondary evidence, so C at most; +05:45 zone.
    owner = charts["np-2008-republic-owner"]
    assert owner.grade == "C"
    assert owner.founding_instant() == datetime(2008, 5, 28, 17, 41, 26, tzinfo=timezone.utc)
    assert all(c.grade in ("C", "D") for c in charts.values())


def test_seeded_events_load():
    """Events load, are Mw >= 6, exhaustive, unreviewed, with flags."""
    events = reg.load_events()
    assert 12 <= len(events) <= 30
    assert all(e.severity["value"] >= 6.0 for e in events)
    assert all(e.exhaustive and e.reviewed_by is None for e in events)
    assert all({"raw", "mainshock_gk", "mainshock_nn"} <= set(e.flags) for e in events)
    assert sum(e.flags["mainshock_gk"] for e in events) == 12
    assert len(reg.aggregate_events(events)) == len(events)
    for e in events:
        if not e.flags["mainshock_gk"]:
            assert e.cluster_id is None or e.cluster_id.startswith("usgs:")


def test_event_rules():
    """Strict event schema and the exhaustive rule."""
    raw = json.loads((REPO_ROOT / "data/registry/mundane/events.jsonl").read_text().splitlines()[0])
    bad = copy.deepcopy(raw)
    bad["extra"] = 1
    with pytest.raises(reg.RegistryError, match="unknown"):
        reg.parse_event(bad)
    bad = copy.deepcopy(raw)
    bad["event_type"] = "comet"
    with pytest.raises(reg.RegistryError):
        reg.parse_event(bad)
    bad = copy.deepcopy(raw)
    bad["time_utc"] = "2000-01-01T00:00:00"
    with pytest.raises(reg.RegistryError, match="time zone"):
        reg.parse_event(bad)
    bad = copy.deepcopy(raw)
    bad["catalogue"]["inclusion_rule"] = None
    with pytest.raises(reg.RegistryError, match="exhaustive"):
        reg.parse_event(bad)
    bad = copy.deepcopy(raw)
    bad["exhaustive"] = False
    assert reg.aggregate_events([reg.parse_event(bad)]) == []


# ------------------------------------------------------------- seed script
def test_seed_script_is_deterministic_and_writes_hashes(tmp_path):
    """Two runs give byte-identical files; the manifest hashes match; inputs untouched."""
    before = reg.file_sha256(COUNTRIES)
    snap = br._latest_usgs_snapshot()
    m1 = br.write_registries(snap, tmp_path / "a")
    m2 = br.write_registries(snap, tmp_path / "b")
    assert m1 == m2
    for name in ("charts.yaml", "events.jsonl", "MANIFEST.json"):
        assert (tmp_path / "a" / name).read_bytes() == (tmp_path / "b" / name).read_bytes()
    assert m1["outputs"]["charts_sha256"] == reg.file_sha256(tmp_path / "a" / "charts.yaml")
    # and they equal the committed registries
    committed = reg.registry_hashes()
    assert committed["charts_sha256"] == m1["outputs"]["charts_sha256"]
    assert committed["events_sha256"] == m1["outputs"]["events_sha256"]
    assert reg.file_sha256(COUNTRIES) == before


def test_countries_yaml_still_stamped():
    """The seed copies from countries.yaml; it must remain 113 untouched rows."""
    rows = yaml.safe_load(COUNTRIES.read_text())["countries"]
    assert len(rows) == 113


@pytest.mark.parametrize("day, clock, kind", [
    ("2021-03-14", "02:30:00", "DST gap"),      # spring forward: 02:30 does not exist
    ("2021-11-07", "01:30:00", "DST overlap"),  # fall back: 01:30 happens twice
])
def test_founding_time_in_dst_gap_or_overlap_is_refused(day, clock, kind):
    """m10: a wall-clock time the zone skips or repeats is not resolved silently."""
    c = _chart(date=day, time=clock, time_zone="America/New_York", lat=40.7, lon=-74.0,
               valid_from=day)
    with pytest.raises(reg.RegistryError, match=kind):
        reg.founding_instant_utc(c)


def test_founding_time_outside_dst_change_converts():
    c = _chart(date="2021-03-14", time="03:30:00", time_zone="America/New_York",
               lat=40.7, lon=-74.0, valid_from="2021-03-14")
    assert reg.founding_instant_utc(c) == datetime(2021, 3, 14, 7, 30, tzinfo=timezone.utc)


def test_committed_charts_have_unambiguous_times():
    for c in reg.load_charts():
        reg.founding_instant_utc(c)
