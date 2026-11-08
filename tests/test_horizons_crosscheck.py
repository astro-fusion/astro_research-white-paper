"""Cross-check the engine's longitudes against JPL Horizons (DE441).

The engine returns sidereal longitudes. Swiss Ephemeris forms them by
subtracting the true ayanamsa (with nutation in longitude) from the apparent
tropical longitude of date, so adding that same ayanamsa back gives the
apparent geocentric ecliptic longitude of date that Horizons quantity 31
reports.

Tolerances:

- ``moshier`` (no ``.se1`` files installed): 10 arcseconds. The Moshier
  analytic ephemeris in Swiss Ephemeris reproduces JPL DE404/DE431 to about
  0.1 arcsecond for the Sun and planets and a few arcseconds for the Moon
  over 1800-2200 (Swiss Ephemeris documentation, section 2.1.3); the
  remaining difference between IAU76/80 (Horizons) and IAU2006/2000B (Swiss
  Ephemeris) precession-nutation is a few milliarcseconds.
- ``swieph`` (``.se1`` files compressing DE431): 1 arcsecond.

Offline against ``tests/fixtures/horizons/`` unless ``HORIZONS_LIVE=1``.
"""

import os

import pytest
import swisseph as swe

from tests import horizons
from vedic_astrology_core.astrology.ayanamsa import set_sidereal_mode
from vedic_astrology_core.astrology.ephemeris import SIDEREAL_FLAGS, EphemerisEngine

TOLERANCE_ARCSEC = {"moshier": 10.0, "swieph": 1.0}
LIVE = os.environ.get("HORIZONS_LIVE") == "1"


@pytest.fixture(scope="module")
def engine():
    """One engine for the module."""
    return EphemerisEngine()


@pytest.fixture(scope="module", params=sorted(horizons.BODIES))
def reference(request):
    """Fixture document for one body (fetched live with HORIZONS_LIVE=1)."""
    if LIVE:
        return horizons.fetch(request.param)
    return horizons.load(request.param)


def tropical_longitude(engine, jd, body):
    """Engine sidereal longitude plus the true ayanamsa Swiss Ephemeris used."""
    sidereal = engine.get_planet_position(jd, body)["longitude"]
    set_sidereal_mode(engine.ayanamsa_system)
    _, true_ayanamsa = swe.get_ayanamsa_ex_ut(jd, SIDEREAL_FLAGS & ~swe.FLG_SIDEREAL)
    return (sidereal + true_ayanamsa) % 360.0


def deviation_arcsec(a, b):
    """Shortest angular distance in arcseconds."""
    d = abs(a - b) % 360.0
    return min(d, 360.0 - d) * 3600.0


def test_fixture_header_records_the_request(reference):
    """Every fixture says what was asked, of what, and when."""
    header = reference["header"]
    assert header["params"]["QUANTITIES"] == "'31'"
    assert header["params"]["CENTER"] == "'500@399'"
    assert header["params"]["TIME_TYPE"] == "'UT'"
    assert header["fetched_at"]
    assert "DE441" in reference["raw_result"]
    assert [r["jd_ut"] for r in reference["rows"]] == pytest.approx(
        horizons.INSTANTS_JD
    )


def test_longitude_matches_horizons(engine, reference):
    """Apparent ecliptic longitude of date within the model's tolerance."""
    body = reference["header"]["body"]
    tolerance = TOLERANCE_ARCSEC[engine.ephemeris_model]
    deviations = [
        deviation_arcsec(
            tropical_longitude(engine, row["jd_ut"], body), row["ecl_lon_deg"]
        )
        for row in reference["rows"]
    ]
    worst = max(deviations)
    print(f"{body}: max {worst:.3f} arcsec ({engine.ephemeris_model})")
    assert worst <= tolerance, (body, engine.ephemeris_model, deviations)


def test_sidereal_differs_from_tropical_by_the_ayanamsa(engine):
    """Guard against comparing tropical to tropical: Lahiri ~23.86 at J2000."""
    jd = 2451545.0
    sidereal = engine.get_planet_position(jd, "SUN")["longitude"]
    assert tropical_longitude(engine, jd, "SUN") - sidereal == pytest.approx(
        23.853, abs=0.01
    )
