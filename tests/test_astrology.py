"""
Unit tests for the astrology module.

Values are asserted against the golden fixture
(``tests/fixtures/golden_charts.json``: pyswisseph with FLG_SIDEREAL and
Lahiri, PyJHora), not just shapes.
"""

import json
import unittest
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import swisseph as swe

from vedic_astrology_core.astrology import AyanamsaSystem, BirthChart, EphemerisEngine
from vedic_astrology_core.astrology.ayanamsa import (
    convert_sidereal_to_tropical,
    convert_tropical_to_sidereal,
    get_ayanamsa_offset,
    get_zodiac_sign,
)
from vedic_astrology_core.config.constants import Planet
from vedic_astrology_core.utils.datetime_utils import NaiveDatetimeError

FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "golden_charts.json").read_text()
)
CHARTS = {c["id"]: c for c in FIXTURE["charts"]}
J2000 = CHARTS["grw_j2000"]  # 2000-01-01 12:00 UTC, JD 2451545.0
DELHI_1984 = CHARTS["del_1984"]  # 1984-08-27 10:30 IST, Delhi
ARCSEC = 1.0 / 3600.0
ARCMIN = 1.0 / 60.0


class TestAyanamsaCalculations(unittest.TestCase):
    """Ayanamsa comes from swe.get_ayanamsa_ut only."""

    def test_lahiri_ayanamsa_at_j2000(self):
        """Lahiri at J2000 is 23.857 deg (not the 23.437 obliquity)."""
        ayanamsa = get_ayanamsa_offset(2451545.0, AyanamsaSystem.LAHIRI)
        self.assertAlmostEqual(ayanamsa, J2000["ayanamsa"], delta=ARCSEC)
        self.assertAlmostEqual(ayanamsa, 23.857, places=3)

    def test_lahiri_ayanamsa_precesses(self):
        """The value at 1984 matches the oracle and is smaller than at 2000."""
        ayanamsa = get_ayanamsa_offset(DELHI_1984["jd_ut"])
        self.assertAlmostEqual(ayanamsa, DELHI_1984["ayanamsa"], delta=ARCSEC)
        self.assertLess(ayanamsa, J2000["ayanamsa"])

    def test_raman_uses_sidm_raman(self):
        """Raman maps to SIDM_RAMAN, distinct from Krishnamurti."""
        swe.set_sid_mode(swe.SIDM_RAMAN, 0.0, 0.0)
        expected = swe.get_ayanamsa_ut(2451545.0)
        raman = get_ayanamsa_offset(2451545.0, AyanamsaSystem.RAMAN)
        kp = get_ayanamsa_offset(2451545.0, AyanamsaSystem.KRISHNAMURTI)
        self.assertAlmostEqual(raman, expected, delta=1e-9)
        self.assertNotAlmostEqual(raman, kp, places=3)

    def test_invalid_system(self):
        """Unknown systems raise ValueError."""
        with self.assertRaises(ValueError):
            get_ayanamsa_offset(2451545.0, "invalid_system")

    def test_ayanamsa_conversion_round_trip(self):
        """Tropical to sidereal and back."""
        sidereal = convert_tropical_to_sidereal(0.0, 24.0)
        self.assertAlmostEqual(sidereal, 336.0, places=9)
        self.assertAlmostEqual(convert_sidereal_to_tropical(sidereal, 24.0), 0.0)

    def test_zodiac_sign_calculation(self):
        """Sign index, name and degrees within sign."""
        self.assertEqual(get_zodiac_sign(15.5), (0, "Aries", 15.5))
        idx, name, deg = get_zodiac_sign(45.0)
        self.assertEqual((idx, name), (1, "Taurus"))
        self.assertAlmostEqual(deg, 15.0)
        self.assertEqual(get_zodiac_sign(359.9)[0], 11)
        self.assertEqual(get_zodiac_sign(360.1)[0], 0)


class TestEphemerisEngine(unittest.TestCase):
    """Sidereal positions against the pyswisseph oracle."""

    def setUp(self):
        """Create a default (Lahiri, mean node) engine."""
        self.ephemeris = EphemerisEngine()

    def test_engine_records_conventions(self):
        """Node model and ephemeris model are recorded on the engine."""
        info = self.ephemeris.get_ephemeris_info()
        self.assertEqual(info["node_model"], "mean")
        self.assertIn(info["ephemeris_model"], ("swieph", "moshier"))
        self.assertEqual(info["ayanamsa_system"], "lahiri")
        with self.assertRaises(ValueError):
            EphemerisEngine(node_model="osculating")

    def test_datetime_to_julian_day(self):
        """Aware datetimes convert exactly; naive ones are rejected."""
        j2000 = datetime(2000, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        self.assertEqual(self.ephemeris.datetime_to_julian_day(j2000), 2451545.0)
        with self.assertRaises(NaiveDatetimeError):
            self.ephemeris.datetime_to_julian_day(datetime(2000, 1, 1, 12))
        ktm = datetime(1990, 5, 15, 10, 30, tzinfo=ZoneInfo("Asia/Kathmandu"))
        utc = datetime(1990, 5, 15, 4, 45, tzinfo=timezone.utc)
        self.assertAlmostEqual(
            self.ephemeris.datetime_to_julian_day(ktm),
            self.ephemeris.datetime_to_julian_day(utc),
            places=9,
        )

    def test_sun_at_j2000_is_sidereal(self):
        """J2000 Sun is 256.516 deg (sidereal Sagittarius), not 280.37."""
        sun = self.ephemeris.get_planet_position(2451545.0, Planet.SUN)
        self.assertAlmostEqual(
            sun["longitude"], J2000["bodies"]["SUN"]["longitude"], delta=ARCMIN
        )
        self.assertEqual(sun["sign_name"], "Sagittarius")
        self.assertFalse(sun["retrograde"])
        self.assertFalse(sun["combust"])

    def test_planet_position_values(self):
        """Every graha at J2000 within 1 arcminute; retrograde from speed."""
        for name in ("MOON", "MARS", "MERCURY", "JUPITER", "VENUS", "SATURN"):
            with self.subTest(planet=name):
                pos = self.ephemeris.get_planet_position(2451545.0, name.lower())
                expected = J2000["bodies"][name]
                self.assertAlmostEqual(
                    pos["longitude"], expected["longitude"], delta=ARCMIN
                )
                self.assertAlmostEqual(
                    pos["longitude_speed"], expected["speed"], delta=1e-3
                )
                self.assertEqual(pos["retrograde"], expected["speed"] < 0)
                self.assertEqual(pos["sign"], int(expected["longitude"] // 30))

    def test_ketu_id_is_not_true_node(self):
        """Planet.KETU no longer collides with swe.TRUE_NODE."""
        self.assertNotEqual(Planet.KETU.value, swe.TRUE_NODE)
        ketu = self.ephemeris.get_planet_position(2451545.0, Planet.KETU.value)
        self.assertAlmostEqual(
            ketu["longitude"], J2000["bodies"]["KETU_MEAN"]["longitude"], delta=ARCMIN
        )


class TestBirthChart(unittest.TestCase):
    """Birth chart against the Delhi 1984 golden chart."""

    def setUp(self):
        """Delhi, 1984-08-27 10:30 IST."""
        self.birth = datetime(1984, 8, 27, 10, 30, tzinfo=ZoneInfo("Asia/Kolkata"))
        self.lat, self.lon = DELHI_1984["latitude"], DELHI_1984["longitude"]

    def test_naive_datetime_rejected(self):
        """A naive birth time is ambiguous and raises."""
        with self.assertRaises(NaiveDatetimeError):
            BirthChart(datetime(1984, 8, 27, 10, 30), self.lat, self.lon)

    def test_chart_values(self):
        """Ascendant, ayanamsa and planets match the oracle."""
        chart = BirthChart(self.birth, self.lat, self.lon)
        self.assertIsNone(chart._ascendant)  # lazy
        self.assertAlmostEqual(chart.julian_day, DELHI_1984["jd_ut"], places=6)
        self.assertAlmostEqual(
            chart.ascendant["longitude"], DELHI_1984["ascendant"], delta=ARCMIN
        )
        self.assertEqual(chart.ascendant["sign_name"], "Libra")
        # The fixture stores the mean ayanamsa; the chart reports the true one
        # (mean + nutation in longitude), which its sidereal positions use.
        self.assertAlmostEqual(
            chart.ephemeris.ayanamsa_mean(chart.julian_day),
            DELHI_1984["ayanamsa"],
            delta=ARCSEC,
        )
        self.assertAlmostEqual(
            chart.ayanamsa, chart.ephemeris.ayanamsa_true(chart.julian_day), delta=1e-9
        )
        mars = chart.planets[Planet.MARS]
        self.assertAlmostEqual(
            mars["longitude"], DELHI_1984["bodies"]["MARS"]["longitude"], delta=ARCMIN
        )
        self.assertEqual(mars["sign_name"], "Scorpio")

    def test_whole_sign_houses_by_default(self):
        """Whole-sign houses: house = sign distance from the ascendant sign."""
        chart = BirthChart(self.birth, self.lat, self.lon)
        self.assertEqual(chart.house_system, "W")
        asc_sign = chart.ascendant["sign"]
        self.assertEqual([h["sign"] for h in chart.houses][0], asc_sign)
        # Mars in Scorpio, ascendant Libra: 2nd house.
        self.assertEqual(chart.get_planet_in_house(Planet.MARS), 2)
        self.assertEqual(chart.planets[Planet.MARS]["house"], 2)

    def test_house_system_parameter_is_honoured(self):
        """Placidus cusps and placement come from the same system."""
        chart = BirthChart(self.birth, self.lat, self.lon, house_system="placidus")
        self.assertEqual(chart.house_system, "P")
        for house, cusp in zip(chart.houses, DELHI_1984["cusps_placidus"]):
            self.assertAlmostEqual(house["longitude"], cusp, delta=ARCMIN)
        mars = chart.planets[Planet.MARS]["longitude"]
        house = chart.get_planet_in_house(Planet.MARS)
        start = chart.houses[house - 1]["longitude"]
        end = chart.houses[house % 12]["longitude"]
        self.assertLess((mars - start) % 360, (end - start) % 360)

    def test_polar_latitude_falls_back_to_whole_sign(self):
        """Placidus is undefined above 66.5 deg; whole sign is used instead."""
        polar = CHARTS["polar_2010"]
        birth = datetime.fromisoformat(polar["utc"])
        with self.assertWarns(RuntimeWarning):
            chart = BirthChart(
                birth, polar["latitude"], polar["longitude"], house_system="P"
            )
            asc = chart.ascendant["longitude"]
        self.assertEqual(chart.requested_house_system, "P")
        self.assertEqual(chart.house_system, "W")
        self.assertAlmostEqual(asc, polar["ascendant"], delta=ARCMIN)

    def test_unknown_house_system(self):
        """Unknown systems raise ValueError."""
        with self.assertRaises(ValueError):
            BirthChart(self.birth, self.lat, self.lon, house_system="nonsense")


class TestCoordinateValidation(unittest.TestCase):
    """Coordinate validation."""

    def test_invalid_coordinates(self):
        """Out-of-range latitude/longitude raise ValueError."""
        birth = datetime(1984, 8, 27, 10, 30, tzinfo=ZoneInfo("Asia/Kolkata"))
        for lat, lon in ((91.0, 77.1), (-91.0, 77.1), (28.6, 181.0), (28.6, -181.0)):
            with self.subTest(lat=lat, lon=lon):
                with self.assertRaises(ValueError):
                    BirthChart(birth, lat, lon)


if __name__ == "__main__":
    unittest.main()
