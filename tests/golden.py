"""Shared loader and helpers for the golden-chart tests.

The fixture ``tests/fixtures/golden_charts.json`` is produced by
``tests/fixtures/generate_golden_charts.py`` from pyswisseph (positions,
ascendant, ayanamsa) and PyJHora, a Python port of JHora 8 (dasha, vargas,
nakshatra/pada). See its ``provenance`` block for versions.

Tolerances: longitudes and ascendant 1 arcminute, dasha boundaries 1 day,
varga signs exact.
"""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "golden_charts.json").read_text()
)
CHARTS = FIXTURE["charts"]
CHART_IDS = [c["id"] for c in CHARTS]
ARCMIN = 1.0 / 60.0
PLANETS = ["SUN", "MOON", "MARS", "MERCURY", "JUPITER", "VENUS", "SATURN"]


def angle_diff(a, b):
    """Shortest angular distance between two longitudes in degrees."""
    d = abs(a - b) % 360.0
    return min(d, 360.0 - d)


def jd_to_datetime(jd):
    """UTC datetime of a Julian day (UT)."""
    return datetime(1970, 1, 1, tzinfo=timezone.utc) + timedelta(days=jd - 2440587.5)


def birth(chart):
    """Timezone-aware birth instant of a fixture chart."""
    return datetime.fromisoformat(chart["utc"])


def point(chart, key):
    """Return a fixture longitude; RAHU and KETU use the mean node."""
    if key == "ASC":
        return chart["ascendant"]
    if key in ("RAHU", "KETU"):
        return chart["bodies"][f"{key}_MEAN"]["longitude"]
    return chart["bodies"][key]["longitude"]
