"""Candidate national charts in countries.yaml: shape, dates, sources, confidence."""

import re
from datetime import date
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).parent.parent
ROWS = yaml.safe_load((REPO / "studies/mundane/data/countries.yaml").read_text())[
    "countries"
]
CANDIDATES = [
    (c["iso"], i, cc) for c in ROWS for i, cc in enumerate(c["candidate_charts"])
]
FIELDS = {
    "event", "date", "time", "time_zone", "place", "lat", "lon",
    "used_by", "source", "confidence", "notes",
}
CONFIDENCE = {"documented", "conventional", "disputed"}


def test_candidates_exist_and_founding_is_untouched():
    """Candidates were added without promoting any of them to the founding block."""
    assert len(CANDIDATES) >= 50
    assert len({iso for iso, _, _ in CANDIDATES}) >= 25
    assert all(c["founding"]["time"] is None for c in ROWS)
    assert not any(c["founding"]["time_known"] for c in ROWS)


@pytest.mark.parametrize(
    "iso,i,cand", CANDIDATES, ids=[f"{iso}-{i}" for iso, i, _ in CANDIDATES]
)
def test_candidate_schema(iso, i, cand):
    """Every field present; date parses; time is HH:MM:SS or null; coordinates sane."""
    assert set(cand) == FIELDS
    assert cand["event"]
    date.fromisoformat(str(cand["date"]))
    assert cand["time"] is None or re.fullmatch(r"\d{2}:\d{2}:\d{2}", cand["time"])
    assert cand["time_zone"]
    assert -90 <= cand["lat"] <= 90 and -180 <= cand["lon"] <= 180
    assert isinstance(cand["used_by"], list) and cand["used_by"]


@pytest.mark.parametrize(
    "iso,i,cand", CANDIDATES, ids=[f"{iso}-{i}" for iso, i, _ in CANDIDATES]
)
def test_candidate_has_source_and_confidence(iso, i, cand):
    """A URL source with a checked flag, and one of the three confidence labels."""
    src = cand["source"]
    assert src["url"].startswith(("http://", "https://"))
    assert isinstance(src["checked"], bool)
    assert cand["confidence"] in CONFIDENCE
    if cand["confidence"] == "documented":
        assert cand["time"] is not None, "a documented candidate states a time"


def test_summary_table_matches_the_data():
    """countries_candidates_summary.md has one row per country with candidates."""
    text = (REPO / "studies/mundane/data/countries_candidates_summary.md").read_text()
    for c in ROWS:
        if c["candidate_charts"]:
            name = re.escape(c["name"])
            row = re.search(rf"\| {name} \| {c['iso']} \| (\d+) \|", text)
            assert row and int(row.group(1)) == len(c["candidate_charts"]), c["iso"]
