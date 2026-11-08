"""End-to-end: the combinations API now reads the rules/ registry.

Positions are keyed by the canonical ``Planet`` enum. Expected activations
for the migrated catalog rules are worked out by hand from the golden
fixture (pyswisseph oracle) for the J2000 chart: Sun Sagittarius 16.5,
Mars Aquarius 4.1 (304.1), Jupiter Aries 1.4 (speed +0.041), Venus Scorpio
7.7 (217.7, speed +1.21), Saturn Aries 16.5 (speed -0.020), Rahu Cancer
11.2 (101.2), Ketu Capricorn 11.2 (281.2).
"""

from datetime import datetime, timezone
from pathlib import Path

from vedic_astrology_core.astrology.ephemeris import EphemerisEngine
from vedic_astrology_core.combinations import RegistryRule
from vedic_astrology_core.combinations.evaluator import CombinationEvaluator
from vedic_astrology_core.combinations.registry import CombinationRegistry
from vedic_astrology_core.config.constants import Planet, PlanetDict
from vedic_astrology_core.rules.engine import rule_inputs
from vedic_astrology_core.rules.loader import load_rules

RULES_DIR = Path(__file__).resolve().parents[1] / "rules"

WHEN = datetime(2000, 1, 1, 12, tzinfo=timezone.utc)

EXPECTED_J2000 = {
    "Venus-Retrograde-Reversal": False,  # Venus speed +1.21
    "Jupiter-Retrograde-Contraction": False,  # Jupiter speed +0.041
    "Shukra-Guru-Wealth": False,  # Venus 217.7 vs Jupiter 1.4: 143.7 deg
    "Venus-Own-Sign": False,  # Venus in Scorpio
    "Mangal-Ketu-Primary": False,  # Mars 304.1 vs Ketu 281.2: 22.9 > 13
    "Mangal-Ketu-Fire-Sign": False,
    "Mangal-Shani-Malefic": False,  # 304.1 vs 16.5: 72.4 > 15
    "Mangal-8th-Aspect-Ketu": False,  # Ketu Capricorn is 12th from Aquarius
    "Shani-10th-Aspect-Mars": False,  # 10th from Aries is Capricorn, Mars Aquarius
    "Shrapit-Yoga": False,  # Saturn 16.5 vs Rahu 101.2
    "Mars-Retrograde-Tension": False,  # Mars direct
    "Saturn-Stationary": True,  # |speed| 0.020 < 0.05
    "Budha-Aditya Yoga": True,  # Sun and Mercury both in Sagittarius
    "Gaja Kesari Yoga (Moon kendra form)": True,  # Jupiter Aries, 7th from Libra
}


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


def _moment_only_rules(domain):
    """Rule files under rules/<domain>/ (any depth) the registry can evaluate.

    The registry keeps rules that have conditions and need nothing beyond a
    moment, so the expected count follows the files on disk, including the
    practitioner rules added after the migration.
    """
    loaded, problems = load_rules([RULES_DIR / domain])
    assert not problems
    return [item.rule for item in loaded
            if item.rule.conditions is not None and not rule_inputs(item.rule)]


def test_registry_reads_the_migrated_rules():
    """The old names are kept; seismic and financial come from rules/."""
    registry = CombinationRegistry()
    seismic = {r.name for r in registry.get_rules_by_usecase("seismic")}
    assert len(seismic) == 8 and "Mangal-Ketu-Primary" in seismic
    financial = {r.name for r in registry.get_rules_by_usecase("financial")}
    migrated = {"Venus-Retrograde-Reversal", "Jupiter-Retrograde-Contraction",
                "Shukra-Guru-Wealth", "Venus-Own-Sign"}
    assert migrated <= financial
    assert len(financial) == len(_moment_only_rules("financial"))
    rule = registry.get_rule("Mangal-Ketu-Primary")
    assert isinstance(rule, RegistryRule)
    assert rule.id == "seismic.mangal_ketu_primary"
    assert registry.get_rule("seismic.mangal_ketu_primary") is rule


def test_every_rule_evaluates_to_the_hand_derived_value():
    """All moment-only rules run and agree with the fixture at J2000."""
    registry = CombinationRegistry()
    results = CombinationEvaluator(EphemerisEngine(), registry.get_all_rules())
    results = results.evaluate_date(WHEN)
    for name, expected in EXPECTED_J2000.items():
        assert results[name]["is_active"] is expected, name
        assert results[name]["score"] == (1.0 if expected else 0.0)
    for res in results.values():
        assert 0.0 <= res["score"] <= 1.0
        assert res["breakdown"]


def test_default_evaluator_loads_all_rules():
    """CombinationEvaluator() with no rules uses the registry."""
    evaluator = CombinationEvaluator()
    names = {r.name for r in evaluator.rules}
    assert set(EXPECTED_J2000) <= names


def test_positions_interface_still_works():
    """rule.evaluate(positions) gives the same answer as evaluate_date."""
    engine = EphemerisEngine()
    positions = engine.get_all_planet_positions(engine.datetime_to_julian_day(WHEN))
    rule = CombinationRegistry().get_rule("Saturn-Stationary")
    assert rule.evaluate(positions)["is_active"] is True


def test_timeseries_columns_keep_old_names():
    """The earthquake study's columns are <old name>_active / _score."""
    registry = CombinationRegistry()
    evaluator = CombinationEvaluator(
        EphemerisEngine(), registry.get_rules_by_usecase("seismic")
    )
    frame = evaluator.evaluate_timeseries(WHEN, WHEN, step_days=1.0)
    assert "Mangal-Ketu-Primary_active" in frame.columns
    assert int(frame["Saturn-Stationary_active"].iloc[0]) == 1
