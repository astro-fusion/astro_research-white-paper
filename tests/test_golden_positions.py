"""Golden tests: sidereal positions, ayanamsa and nodes against pyswisseph."""

import pytest

from tests.golden import ARCMIN, CHART_IDS, CHARTS, FIXTURE, PLANETS, angle_diff
from vedic_astrology_core.astrology.ephemeris import EphemerisEngine
from vedic_astrology_core.config.constants import Planet

ENGINE_MEAN = EphemerisEngine(node_model="mean")
ENGINE_TRUE = EphemerisEngine(node_model="true")


def test_fixture_provenance_and_coverage():
    """The fixture declares its oracles and covers the required spread."""
    prov = FIXTURE["provenance"]
    assert prov["ayanamsa"].startswith("Lahiri")
    assert prov["oracles"]["positions_ascendant_ayanamsa"]["name"] == "pyswisseph"
    assert prov["oracles"]["dasha_vargas_nakshatra_combustion"]["name"] == "PyJHora"
    assert len(CHARTS) >= 20
    years = [int(c["utc"][:4]) for c in CHARTS]
    assert min(years) <= 1900 and max(years) >= 2050
    assert any(abs(c["latitude"]) > 66.5 for c in CHARTS)


@pytest.mark.parametrize("chart", CHARTS, ids=CHART_IDS)
def test_ayanamsa(chart):
    """The golden (mean) Lahiri ayanamsa equals swe.get_ayanamsa_ut.

    The engine's get_ayanamsa is the true value the positions use; see
    tests/test_ephemeris_ayanamsa.py.
    """
    assert ENGINE_MEAN.ayanamsa_mean(chart["jd_ut"]) == pytest.approx(
        chart["ayanamsa"], abs=ARCMIN / 60.0
    )


@pytest.mark.parametrize("chart", CHARTS, ids=CHART_IDS)
def test_sidereal_longitudes(chart):
    """Sun to Saturn and both node models within 1 arcminute."""
    positions = ENGINE_MEAN.get_all_planet_positions(chart["jd_ut"])
    for name in PLANETS:
        expected = chart["bodies"][name]
        got = positions[Planet[name]]
        assert angle_diff(got["longitude"], expected["longitude"]) < ARCMIN, name
        assert got["retrograde"] == (expected["speed"] < 0), name
    for name in ("RAHU", "KETU"):
        got = positions[Planet[name]]["longitude"]
        assert angle_diff(got, chart["bodies"][f"{name}_MEAN"]["longitude"]) < ARCMIN
    true_pos = ENGINE_TRUE.get_all_planet_positions(chart["jd_ut"])
    for name in ("RAHU", "KETU"):
        got = true_pos[Planet[name]]["longitude"]
        assert angle_diff(got, chart["bodies"][f"{name}_TRUE"]["longitude"]) < ARCMIN


@pytest.mark.parametrize("chart", CHARTS, ids=CHART_IDS)
def test_ketu_is_rahu_plus_180(chart):
    """Ketu is exactly opposite Rahu for both node models, on every path."""
    for engine in (ENGINE_MEAN, ENGINE_TRUE):
        positions = engine.get_all_planet_positions(chart["jd_ut"])
        rahu = positions[Planet.RAHU]["longitude"]
        ketu = positions[Planet.KETU]["longitude"]
        assert (ketu - rahu) % 360.0 == pytest.approx(180.0, abs=1e-9)
        single = engine.get_planet_position(chart["jd_ut"], Planet.KETU)
        assert single["longitude"] == pytest.approx(ketu, abs=1e-9)
        by_name = engine.get_planet_position(chart["jd_ut"], "ketu")
        assert by_name["longitude"] == pytest.approx(ketu, abs=1e-9)


def test_j2000_sun_is_sidereal():
    """Probe from the review: sidereal Sun at J2000 is about 256.52 deg."""
    sun = ENGINE_MEAN.get_planet_position(2451545.0, Planet.SUN)["longitude"]
    assert sun == pytest.approx(256.516, abs=0.01)
    assert ENGINE_MEAN.ephemeris_model in ("swieph", "moshier")
    assert ENGINE_MEAN.node_model == "mean"
