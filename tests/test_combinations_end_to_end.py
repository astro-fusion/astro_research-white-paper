"""End-to-end: every catalog rule evaluated on a fixed date.

Positions are keyed by the canonical ``Planet`` enum. Expected activations
are recomputed independently from the golden fixture (pyswisseph oracle) for
the J2000 chart, so this checks values, not just that nothing raises.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from vedic_astrology_core.astrology.ephemeris import EphemerisEngine
from vedic_astrology_core.combinations.evaluator import CombinationEvaluator
from vedic_astrology_core.combinations.registry import CombinationRegistry
from vedic_astrology_core.config.constants import Planet, PlanetDict

FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "golden_charts.json").read_text()
)
J2000 = next(c for c in FIXTURE["charts"] if c["id"] == "grw_j2000")
WHEN = datetime(2000, 1, 1, 12, tzinfo=timezone.utc)


def _lon(name):
    key = {"RAHU": "RAHU_MEAN", "KETU": "KETU_MEAN"}.get(name, name)
    return J2000["bodies"][key]["longitude"]


def _speed(name):
    key = {"RAHU": "RAHU_MEAN", "KETU": "KETU_MEAN"}.get(name, name)
    return J2000["bodies"][key]["speed"]


def _sep(a, b):
    d = abs(a - b) % 360.0
    return min(d, 360.0 - d)


def _expected(item):
    kind = item["type"].upper()
    if kind == "CONJUNCTION":
        p1, p2 = item["planet1"].upper(), item["planet2"].upper()
        return _sep(_lon(p1), _lon(p2)) <= float(item["orb_deg"])
    if kind == "ASPECT":
        src, dst = item["aspect_planet"].upper(), item["target_planet"].upper()
        point = (_lon(src) + (int(item["house_aspect"]) - 1) * 30.0) % 360.0
        return _sep(point, _lon(dst)) <= float(item.get("orb_deg", 15.0))
    if kind == "SIGNELEMENT":
        elements = {"FIRE": 0, "EARTH": 1, "AIR": 2, "WATER": 3}
        sign = int(_lon(item["planet"].upper()) // 30)
        return sign % 4 == elements[item["element"].upper()]
    if kind == "INSIGN":
        names = [
            "aries",
            "taurus",
            "gemini",
            "cancer",
            "leo",
            "virgo",
            "libra",
            "scorpio",
            "sagittarius",
            "capricorn",
            "aquarius",
            "pisces",
        ]
        sign = int(_lon(item["planet"].upper()) // 30)
        return names[sign] in [s.lower() for s in item["signs"]]
    if kind == "RETROGRADE":
        return _speed(item["planet"].upper()) < 0
    if kind == "STATIONARY":
        return abs(_speed(item["planet"].upper())) <= float(
            item.get("speed_threshold", 0.05)
        )
    raise AssertionError(kind)


def _catalog_entries():
    import yaml

    catalog = (
        Path(__file__).parent.parent
        / "libs"
        / "vedic_astrology_core"
        / "combinations"
        / "catalog"
    )
    entries = []
    for path in sorted(catalog.glob("*.yaml")):
        entries += yaml.safe_load(path.read_text()) or []
    return entries


def test_positions_use_canonical_planet_keys():
    """get_all_planet_positions is keyed by Planet."""
    positions = EphemerisEngine().get_all_planet_positions(2451545.0)
    assert isinstance(positions, PlanetDict)
    assert list(positions) == [
        Planet.SUN,
        Planet.MOON,
        Planet.MARS,
        Planet.MERCURY,
        Planet.JUPITER,
        Planet.VENUS,
        Planet.SATURN,
        Planet.RAHU,
        Planet.KETU,
    ]


def test_every_catalog_rule_evaluates_to_the_oracle_value():
    """All catalog rules run (no KeyError) and agree with the fixture."""
    registry = CombinationRegistry()
    rules = registry.get_all_rules()
    entries = {e["name"]: e for e in _catalog_entries()}
    assert len(rules) == len(entries) >= 12
    results = CombinationEvaluator(EphemerisEngine(), rules).evaluate_date(WHEN)
    assert set(results) == set(entries)
    for name, entry in entries.items():
        items = entry["conditions"]["items"]
        flags = [_expected(i) for i in items]
        logic = entry["conditions"].get("logic", "ALL_OF").upper()
        expected = all(flags) if logic == "ALL_OF" else any(flags)
        assert results[name]["is_active"] is expected, name
        assert 0.0 <= results[name]["score"] <= 1.0
