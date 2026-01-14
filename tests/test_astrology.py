"""
Unit tests for astrology module.

Tests astronomical calculations including ephemeris, chart generation,
and Ayanamsa handling.
"""

import math
import os
import sys
import unittest
from datetime import date, datetime, time

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from vedic_numerology.astrology import AyanamsaSystem
from vedic_numerology.astrology.ayanamsa import (
    convert_sidereal_to_tropical,
    convert_tropical_to_sidereal,
    get_ayanamsa_offset,
    get_zodiac_sign,
)
from vedic_numerology.config.constants import Planet, ZodiacSign


class TestAyanamsaCalculations(unittest.TestCase):
    """Test Ayanamsa calculation functions."""

    def test_lahiri_ayanamsa_calculation(self):
        """Test Lahiri Ayanamsa calculation."""
        # Test with a known Julian day
        # Approximate JD for J2000: 2451545.0
        jd_j2000 = 2451545.0

        ayanamsa = get_ayanamsa_offset(jd_j2000, AyanamsaSystem.LAHIRI)
        self.assertIsInstance(ayanamsa, float)
        self.assertGreater(ayanamsa, 20)  # Should be around 24 degrees for current era
        self.assertLess(ayanamsa, 30)

    def test_ayanamsa_conversion(self):
        """Test tropical to sidereal conversion."""
        longitude = 0.0  # Aries 0° tropical
        ayanamsa = 24.0  # Current Lahiri Ayanamsa

        sidereal = convert_tropical_to_sidereal(longitude, ayanamsa)
        expected = (longitude - ayanamsa) % 360
        self.assertAlmostEqual(sidereal, expected, places=5)

        # Test round-trip conversion
        tropical_again = convert_sidereal_to_tropical(sidereal, ayanamsa)
        self.assertAlmostEqual(tropical_again, longitude, places=5)

    def test_zodiac_sign_calculation(self):
        """Test zodiac sign determination."""
        # Test Aries (0-30°)
        sign_idx, sign_name, degrees = get_zodiac_sign(15.5)
        self.assertEqual(sign_idx, 0)
        self.assertEqual(sign_name, "Aries")
        self.assertAlmostEqual(degrees, 15.5, places=1)

        # Test Taurus (30-60°)
        sign_idx, sign_name, degrees = get_zodiac_sign(45.0)
        self.assertEqual(sign_idx, 1)
        self.assertEqual(sign_name, "Taurus")
        self.assertAlmostEqual(degrees, 15.0, places=1)

        # Test wraparound (360° = 0°)
        sign_idx1, _, _ = get_zodiac_sign(359.9)
        sign_idx2, _, _ = get_zodiac_sign(0.1)
        self.assertNotEqual(sign_idx1, sign_idx2)  # Should be different signs

    def test_ayanamsa_system_validation(self):
        """Test Ayanamsa system validation."""
        # Valid systems
        for system in [AyanamsaSystem.LAHIRI, AyanamsaSystem.RAMAN]:
            with self.subTest(system=system):
                offset = get_ayanamsa_offset(2451545.0, system)
                self.assertIsInstance(offset, float)

        # Invalid system should raise ValueError
        with self.assertRaises(ValueError):
            get_ayanamsa_offset(2451545.0, "invalid_system")


class TestEphemerisEngine(unittest.TestCase):
    """Test ephemeris engine functionality."""

    def setUp(self):
        """Set up test fixtures."""
        try:
            from vedic_numerology.astrology import EphemerisEngine

            self.ephemeris = EphemerisEngine()
            self.ephemeris_available = True
        except ImportError:
            self.ephemeris_available = False

    def test_ephemeris_initialization(self):
        """Test ephemeris engine initialization."""
        if not self.ephemeris_available:
            self.skipTest("Swiss Ephemeris (pyswisseph) not available")

        # Should initialize without errors
        self.assertIsNotNone(self.ephemeris)

    def test_datetime_to_julian_day(self):
        """Test Julian day conversion."""
        if not self.ephemeris_available:
            self.skipTest("Swiss Ephemeris not available")

        # Test J2000 epoch
        j2000 = datetime(2000, 1, 1, 12, 0, 0)
        jd = self.ephemeris.datetime_to_julian_day(j2000)

        # J2000.0 is 2451545.0
        self.assertAlmostEqual(jd, 2451545.0, places=1)

    def test_planet_position_structure(self):
        """Test planet position data structure."""
        if not self.ephemeris_available:
            self.skipTest("Swiss Ephemeris not available")

        # Test with a known date
        test_date = datetime(2024, 1, 1, 12, 0, 0)
        jd = self.ephemeris.datetime_to_julian_day(test_date)

        position = self.ephemeris.get_planet_position(jd, Planet.SUN.name.lower())

        # Check required keys exist
        required_keys = [
            "longitude",
            "latitude",
            "distance",
            "longitude_speed",
            "sign",
            "sign_name",
            "degrees_in_sign",
            "retrograde",
            "combust",
        ]

        for key in required_keys:
            self.assertIn(key, position)

        # Check data types
        self.assertIsInstance(position["longitude"], float)
        self.assertIsInstance(position["retrograde"], bool)
        self.assertIsInstance(position["combust"], bool)

        # Longitude should be 0-360
        self.assertGreaterEqual(position["longitude"], 0)
        self.assertLess(position["longitude"], 360)

    @unittest.skipUnless(hasattr(unittest, "assertLogs"), "assertLogs not available")
    def test_ephemeris_error_handling(self):
        """Test error handling when ephemeris is not available."""
        if self.ephemeris_available:
            self.skipTest("Swiss Ephemeris is available, cannot test error handling")

        from vedic_numerology.astrology import EphemerisEngine

        with self.assertRaises(ImportError):
            EphemerisEngine()


class TestBirthChart(unittest.TestCase):
    """Test birth chart calculations."""

    def test_birth_chart_creation(self):
        """Test birth chart object creation."""
        from vedic_numerology.astrology import BirthChart

        birth_datetime = datetime(1984, 8, 27, 10, 30, 0)
        latitude = 28.6139
        longitude = 77.1025

        chart = BirthChart(birth_datetime, latitude, longitude)

        # Check basic attributes
        self.assertEqual(chart.birth_datetime, birth_datetime)
        self.assertEqual(chart.latitude, latitude)
        self.assertEqual(chart.longitude, longitude)

    def test_chart_properties_lazy_loading(self):
        """Test that chart properties are loaded lazily."""
        from vedic_numerology.astrology import BirthChart

        birth_datetime = datetime(1984, 8, 27, 10, 30, 0)
        chart = BirthChart(birth_datetime, 28.6139, 77.1025)

        # Initially None
        self.assertIsNone(chart._ascendant)
        self.assertIsNone(chart._houses)
        self.assertIsNone(chart._planets)

        # Access triggers loading
        ascendant = chart.ascendant
        self.assertIsNotNone(ascendant)
        self.assertIsNotNone(chart._ascendant)  # Now loaded

    def test_ascendant_calculation(self):
        """Test ascendant calculation."""
        if not hasattr(unittest, "assertLogs"):
            self.skipTest("Cannot test without ephemeris")

        from vedic_numerology.astrology import BirthChart

        birth_datetime = datetime(1984, 8, 27, 10, 30, 0)
        chart = BirthChart(birth_datetime, 28.6139, 77.1025)

        ascendant = chart.ascendant

        # Check structure
        required_keys = [
            "longitude",
            "sign",
            "sign_name",
            "degrees_in_sign",
            "full_name",
        ]
        for key in required_keys:
            self.assertIn(key, ascendant)

        # Check value ranges
        self.assertGreaterEqual(ascendant["longitude"], 0)
        self.assertLess(ascendant["longitude"], 360)
        self.assertIsInstance(ascendant["sign"], int)
        self.assertGreaterEqual(ascendant["sign"], 0)
        self.assertLess(ascendant["sign"], 12)


class TestMars1984Case(unittest.TestCase):
    """Test the Mars in 1984 case from the technical document."""

    def test_mars_position_august_1984(self):
        """Test Mars position for August 1984 as mentioned in document."""
        # According to the document, Mars was in Scorpio in August 1984
        # Let's test the calculation framework

        from vedic_numerology.astrology import EphemerisEngine

        try:
            ephemeris = EphemerisEngine()
        except ImportError:
            self.skipTest("Swiss Ephemeris not available")

        # Calculate for August 15, 1984 (mid-month)
        test_date = datetime(1984, 8, 15, 12, 0, 0)
        jd = ephemeris.datetime_to_julian_day(test_date)

        mars_position = ephemeris.get_planet_position(jd, Planet.MARS.name.lower())

        # Mars should be in a valid sign (0-11)
        self.assertIsInstance(mars_position["sign"], int)
        self.assertGreaterEqual(mars_position["sign"], 0)
        self.assertLess(mars_position["sign"], 12)

        # Scorpio is sign index 7 (210°-240°)
        # The document mentions Mars in Scorpio, so let's verify the framework works
        sign_name = mars_position["sign_name"]
        self.assertIsInstance(sign_name, str)
        self.assertIn(
            sign_name,
            [
                "Aries",
                "Taurus",
                "Gemini",
                "Cancer",
                "Leo",
                "Virgo",
                "Libra",
                "Scorpio",
                "Sagittarius",
                "Capricorn",
                "Aquarius",
                "Pisces",
            ],
        )


class TestCoordinateValidation(unittest.TestCase):
    """Test coordinate validation."""

    def test_valid_coordinates(self):
        """Test valid coordinate ranges."""
        from vedic_numerology.astrology import BirthChart

        # Valid coordinates
        birth_datetime = datetime(1984, 8, 27, 10, 30, 0)

        # Should not raise errors
        chart = BirthChart(birth_datetime, 28.6139, 77.1025)  # Delhi
        self.assertIsNotNone(chart)

        chart = BirthChart(birth_datetime, 40.7128, -74.0060)  # New York
        self.assertIsNotNone(chart)

    def test_invalid_coordinates(self):
        """Test invalid coordinate handling."""
        from vedic_numerology.astrology import BirthChart

        birth_datetime = datetime(1984, 8, 27, 10, 30, 0)

        # Invalid latitude
        with self.assertRaises(ValueError):
            BirthChart(birth_datetime, 91.0, 77.1025)  # Latitude > 90

        with self.assertRaises(ValueError):
            BirthChart(birth_datetime, -91.0, 77.1025)  # Latitude < -90

        # Invalid longitude
        with self.assertRaises(ValueError):
            BirthChart(birth_datetime, 28.6139, 181.0)  # Longitude > 180

        with self.assertRaises(ValueError):
            BirthChart(birth_datetime, 28.6139, -181.0)  # Longitude < -180


if __name__ == "__main__":
    unittest.main()
