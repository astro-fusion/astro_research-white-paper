"""Classical dignity rules.

Whole-sign uccha, uccha bala, combustion orbs, the node-exaltation tradition,
friendship consistency and the (non-Shadbala) strength index.
"""

import json
from pathlib import Path

import pytest

from vedic_astrology_core.astrology.combustion import COMBUSTION_ORBS, is_combust
from vedic_astrology_core.config.constants import Planet, PlanetDict
from vedic_astrology_core.dignity import DignityScorer
from vedic_astrology_core.dignity.exaltation_matrix import (
    debilitation_sign_index,
    exaltation_sign_index,
    get_dignity_type,
    is_in_debilitation,
    is_in_exaltation,
    uccha_bala,
)
from vedic_astrology_core.dignity.global_scorer import GlobalStrengthScorer

FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "golden_charts.json").read_text()
)


def test_exaltation_is_whole_sign_and_scores_agree():
    """Sun at Aries 25 is exalted (it scored 50 'friend' before)."""
    scorer = DignityScorer()
    for deg in (0.5, 10.0, 25.0, 29.9):
        assert scorer.calculate_base_score(Planet.SUN, 0, deg) == 100
        assert get_dignity_type(deg, Planet.SUN) == "Exalted"
    assert scorer.calculate_base_score(Planet.SUN, 6, 185.0) == 5
    assert is_in_debilitation(205.0, Planet.SUN)


def test_moolatrikona_inside_exaltation_sign():
    """Moon in Taurus 0-4 exalted, 4-30 moolatrikona; Mercury Virgo 16-20 MT."""
    assert get_dignity_type(31.0, Planet.MOON) == "Exalted"
    assert get_dignity_type(45.0, Planet.MOON) == "Moolatrikona"
    assert get_dignity_type(150 + 10.0, Planet.MERCURY) == "Exalted"
    assert get_dignity_type(150 + 18.0, Planet.MERCURY) == "Moolatrikona"


def test_uccha_bala_graded():
    """60 virupas at paramoccha, 0 at deepest debilitation, linear between."""
    assert uccha_bala(Planet.SUN, 10.0) == pytest.approx(60.0)
    assert uccha_bala(Planet.SUN, 190.0) == pytest.approx(0.0)
    assert uccha_bala(Planet.SUN, 100.0) == pytest.approx(30.0)
    assert uccha_bala(Planet.SATURN, 200.0) == pytest.approx(60.0)
    with pytest.raises(ValueError):
        uccha_bala(Planet.RAHU, 40.0)


def test_node_exaltation_tradition_parameter():
    """rahu_exalted_in selects Taurus/Scorpio or Gemini/Sagittarius."""
    assert exaltation_sign_index(Planet.RAHU) == 1
    assert exaltation_sign_index(Planet.KETU) == 7
    assert exaltation_sign_index(Planet.RAHU, "gemini") == 2
    assert exaltation_sign_index(Planet.KETU, "gemini") == 8
    assert debilitation_sign_index(Planet.RAHU, "gemini") == 8
    assert is_in_exaltation(65.0, Planet.RAHU, rahu_exalted_in="gemini")
    assert not is_in_exaltation(65.0, Planet.RAHU, rahu_exalted_in="taurus")
    assert DignityScorer("gemini").calculate_base_score(Planet.RAHU, 2, 65.0) == 100
    with pytest.raises(ValueError):
        DignityScorer(rahu_exalted_in="leo")


def test_combustion_orbs_per_planet():
    """Surya Siddhanta orbs; retrograde Mercury 12 and Venus 8."""
    assert COMBUSTION_ORBS[Planet.MOON] == (12.0, 12.0)
    assert COMBUSTION_ORBS[Planet.MARS] == (17.0, 17.0)
    assert COMBUSTION_ORBS[Planet.MERCURY] == (14.0, 12.0)
    assert COMBUSTION_ORBS[Planet.JUPITER] == (11.0, 11.0)
    assert COMBUSTION_ORBS[Planet.VENUS] == (10.0, 8.0)
    assert COMBUSTION_ORBS[Planet.SATURN] == (15.0, 15.0)
    assert is_combust(Planet.MERCURY, 113.0, 100.0)
    assert not is_combust(Planet.MERCURY, 113.0, 100.0, retrograde=True)
    assert is_combust(Planet.MARS, 356.0, 10.0)  # wraps through 0 Aries
    for never in (Planet.SUN, Planet.RAHU, Planet.KETU):
        assert not is_combust(never, 100.0, 100.0)


def test_friendship_description_matches_score():
    """The score and the reported friendship use the same rule."""
    scorer = DignityScorer()

    class Chart:
        planets = PlanetDict(
            {
                "SUN": {"longitude": 95.0, "sign": 3},
                "MOON": {"longitude": 125.0, "sign": 4},
            }
        )

    result = scorer.score_planet_in_chart(Planet.SUN, Chart())
    key = {
        "Adhi Mitra": "great_friend",
        "Mitra": "friend",
        "Sama": "neutral",
        "Shatru": "enemy",
        "Adhi Shatru": "great_enemy",
    }[result["friendship"]]
    assert result["base_score"] == scorer.DIGNITY_SCORES[key]

    class EmptyChart:
        planets = {}

    assert scorer._calculate_friendship_score(Planet.SUN, 3, EmptyChart()) == 50
    assert (
        scorer.friendship_with_sign_lord(Planet.SUN, Planet.MOON, EmptyChart()).value
        == "Natural Friend"
    )


class _StubEphemeris:
    def __init__(self, positions):
        self.positions = positions

    def get_all_planet_positions(self, jd):
        return self.positions


def _pos(lon, speed=1.0):
    return {
        "longitude": lon,
        "sign": int(lon // 30),
        "longitude_speed": speed,
        "retrograde": speed < 0,
    }


def test_strength_index_rules():
    """Nodes fixed at 50; graha yuddha only among Mars to Saturn."""
    import vedic_astrology_core.dignity.global_scorer as gs

    assert not hasattr(gs, "GlobalShadbalaScorer")  # removed alias: not Shadbala
    positions = {
        "SUN": _pos(100.0),
        "MOON": _pos(100.5, 13.0),
        "MARS": _pos(200.0),
        "SATURN": _pos(200.4),
        "RAHU": _pos(40.0, -0.05),
        "KETU": _pos(220.0, -0.05),
    }
    scores = GlobalStrengthScorer(_StubEphemeris(positions)).calculate_global_power(0.0)
    assert scores[Planet.RAHU] == 50.0 and scores[Planet.KETU] == 50.0
    base = DignityScorer()
    sun_base = base.calculate_base_score(Planet.SUN, 3, 100.0)
    assert scores[Planet.SUN] == pytest.approx(sun_base)  # no war with the Moon
    mars_base = base.calculate_base_score(Planet.MARS, 6, 200.0)
    assert scores[Planet.MARS] == pytest.approx(mars_base * 0.8)


def test_golden_combustion_differs_from_pyjhora_where_pyjhora_is_wrong():
    """Document the PyJHora combustion discrepancy (off-by-one orb index)."""
    diffs = [
        c["id"]
        for c in FIXTURE["charts"]
        if sorted(c["combust"]["expected"]) != sorted(c["combust"]["pyjhora"])
    ]
    assert diffs, "PyJHora 5.0 indexes its orb list with p-2 (Moon gets 15)"


def test_scoring_nodes_and_combust_planets_in_a_real_chart():
    """Nodes carry sun_longitude=None; scoring them must not crash."""
    from datetime import datetime, timezone

    from vedic_astrology_core.astrology.chart import calculate_chart

    chart = calculate_chart(datetime(2000, 1, 1, 12, tzinfo=timezone.utc), 51.4769, 0.0)
    scorer = DignityScorer()
    for planet in Planet:
        result = scorer.score_planet_in_chart(planet, chart)
        assert 0.0 <= result["score"] <= 100.0
    # J2000: Mercury is combust (golden fixture) and loses points.
    mercury = scorer.score_planet_in_chart(Planet.MERCURY, chart)
    assert chart.planets[Planet.MERCURY]["combust"] is True
    assert "Combustion" in mercury["modifiers"]
