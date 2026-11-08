"""Tests for the mundane study's data files and validator."""

import json
import shutil
from pathlib import Path

import pytest
import yaml

from studies.mundane.scripts import validate_data as vd
from studies.mundane.scripts.validate_data import COUNTRIES_FILE, EVENTS_FILE


def test_tracked_data_is_valid():
    """Tracked data is valid."""
    assert vd.validate_countries() == []
    assert vd.validate_events() == []
    assert vd.main() == 0


def test_countries_are_unplaceholdered_and_unique():
    """Countries are unplaceholdered and unique."""
    rows = yaml.safe_load(COUNTRIES_FILE.read_text())["countries"]
    assert len(rows) == 113
    assert len({c["iso"] for c in rows}) == 113
    assert all(c["founding"]["time"] is None for c in rows)
    assert not any(c["founding"]["time_known"] for c in rows)
    assert all(isinstance(c["candidate_charts"], list) for c in rows)
    # Candidates never change the founding block; see test_countries_candidates.py.


def test_events_have_no_description_and_are_unreviewed():
    """Events have no description and are unreviewed."""
    rows = [json.loads(x) for x in EVENTS_FILE.read_text().splitlines()]
    assert len(rows) == 825
    assert all("description" not in r for r in rows)
    assert not any(r["event_type_reviewed"] for r in rows)
    assert {r["metadata"]["qid"] is None for r in rows} == {True, False}


@pytest.fixture
def tmp_countries(tmp_path):
    """Tmp countries."""
    path = tmp_path / "countries.yaml"
    shutil.copy(COUNTRIES_FILE, path)
    return path


def _first_country(path: Path, **founding) -> Path:
    data = yaml.safe_load(path.read_text())
    data["countries"][0]["founding"].update(founding)
    path.write_text(yaml.safe_dump(data))
    return path


def test_bad_country_date_and_time_known_mismatch(tmp_countries):
    """Bad country date and time known mismatch."""
    _first_country(tmp_countries, date="1776-02-30", time="12:00:00")
    problems = vd.validate_countries(tmp_countries)
    assert any("founding.date" in p for p in problems)
    assert any("time is set but time_known is false" in p for p in problems)


def test_bad_country_iso_and_coordinates(tmp_countries):
    """Bad country iso and coordinates."""
    data = yaml.safe_load(tmp_countries.read_text())
    data["countries"][0].update(iso="ZZ", capital_lat=91, timezone="Mars/Base")
    tmp_countries.write_text(yaml.safe_dump(data))
    problems = " ".join(vd.validate_countries(tmp_countries))
    assert "invalid ISO code 'ZZ'" in problems
    assert "outside -90..90" in problems
    assert "unknown timezone" in problems


def test_bad_events(tmp_path):
    """Bad events."""
    good = json.loads(EVENTS_FILE.read_text().splitlines()[0])
    bad = dict(good, id="x", date="2020-13-01", country_iso="QQ", lat=95, lon=0,
               description="Wikipedia text", event_type_reviewed="no")
    path = tmp_path / "events.jsonl"
    path.write_text(json.dumps(good) + "\n" + json.dumps(bad) + "\nnot json\n")
    problems = " ".join(vd.validate_events(path))
    for expected in ("is not a date", "invalid ISO code 'QQ'", "outside -90..90",
                     "description must not be present", "must be a boolean",
                     "invalid JSON"):
        assert expected in problems
