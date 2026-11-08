"""The engine reports the same (true) ayanamsa its sidereal positions use."""

import pytest
import swisseph as swe

from vedic_astrology_core.astrology.ayanamsa import ayanamsa_mean, ayanamsa_true
from vedic_astrology_core.astrology.ephemeris import EphemerisEngine

ARCSEC = 1.0 / 3600.0
J2000 = 2451545.0
JD_2024 = 2460310.5  # 2024-01-01 00:00 UT


@pytest.fixture(scope="module")
def engine():
    """Return one Lahiri engine for the module."""
    return EphemerisEngine()


def nutation_in_longitude(jd):
    """Return the nutation in longitude in degrees (Swiss Ephemeris ECL_NUT)."""
    return swe.calc_ut(jd, swe.ECL_NUT)[0][2]


@pytest.mark.parametrize("jd", [J2000, JD_2024, 2433282.5, 2469807.5])
def test_get_ayanamsa_is_the_true_value(engine, jd):
    """get_ayanamsa equals ayanamsa_true and differs from the mean by nutation."""
    assert engine.get_ayanamsa(jd) == engine.ayanamsa_true(jd)
    diff = engine.ayanamsa_true(jd) - engine.ayanamsa_mean(jd)
    assert diff == pytest.approx(nutation_in_longitude(jd), abs=1e-6 * ARCSEC)
    assert abs(diff) < 17.5 * ARCSEC


@pytest.mark.parametrize("body", ["SUN", "MOON", "MARS", "JUPITER", "SATURN"])
@pytest.mark.parametrize("jd", [J2000, JD_2024])
def test_sidereal_plus_ayanamsa_is_the_apparent_tropical_longitude(engine, jd, body):
    """The sidereal path and get_ayanamsa agree to a micro-arcsecond."""
    sidereal = engine.get_planet_position(jd, body)["longitude"]
    tropical = swe.calc_ut(jd, getattr(swe, body), swe.FLG_SWIEPH)[0][0]
    gap = ((sidereal + engine.get_ayanamsa(jd)) - tropical + 180) % 360 - 180
    assert abs(gap) < 1e-6 * ARCSEC


def test_reported_difference_at_j2000(engine):
    """At J2000 the mean is 23.857092, the true 23.853222: -13.93 arcseconds."""
    assert engine.ayanamsa_mean(J2000) == pytest.approx(23.857092, abs=1e-6)
    assert engine.ayanamsa_true(J2000) == pytest.approx(23.853222, abs=1e-6)
    diff = (engine.ayanamsa_true(J2000) - engine.ayanamsa_mean(J2000)) * 3600
    assert diff == pytest.approx(-13.93, abs=0.01)


def test_module_functions_match_the_engine(engine):
    """ayanamsa_mean / ayanamsa_true agree with the engine methods."""
    assert ayanamsa_mean(JD_2024) == engine.ayanamsa_mean(JD_2024)
    assert ayanamsa_true(JD_2024) == engine.ayanamsa_true(JD_2024)
    assert ayanamsa_mean(JD_2024) == swe.get_ayanamsa_ut(JD_2024)


def test_manifest_records_the_kind(engine):
    """The run manifest says which ayanamsa the positions use."""
    assert engine.get_ephemeris_info()["ayanamsa_kind"].startswith("true")
