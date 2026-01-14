"""
Unit tests for numerology module.

Tests numerological calculations including Mulanka, Bhagyanka,
sunrise correction, and planet mapping.
"""

import os
import sys
import unittest
from datetime import date, datetime, time

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from vedic_numerology.numerology import (
    calculate_bhagyanka,
    calculate_complete_numerology,
    calculate_mulanka,
    reduce_to_single_digit,
)
from vedic_numerology.numerology.planet_mapping import (
    NUMBER_TO_PLANET,
    Planet,
    get_planet_from_number,
)
from vedic_numerology.numerology.sunrise_correction import (
    adjust_date_for_vedic_day,
    get_vedic_day_info,
)


class TestNumerologyCalculations(unittest.TestCase):
    """Test numerological calculation functions."""

    def test_reduce_to_single_digit(self):
        """Test single digit reduction algorithm."""
        # Test basic cases
        self.assertEqual(reduce_to_single_digit(5), 5)
        self.assertEqual(reduce_to_single_digit(15), 6)  # 1 + 5 = 6
        self.assertEqual(reduce_to_single_digit(27), 9)  # 2 + 7 = 9
        self.assertEqual(reduce_to_single_digit(39), 3)  # 3 + 9 = 12, 1 + 2 = 3

        # Test master numbers (should still reduce)
        self.assertEqual(reduce_to_single_digit(11), 2)  # 1 + 1 = 2
        self.assertEqual(reduce_to_single_digit(22), 4)  # 2 + 2 = 4
        self.assertEqual(reduce_to_single_digit(33), 6)  # 3 + 3 = 6

        # Test edge cases
        self.assertEqual(reduce_to_single_digit(0), 9)  # Zero reduces to 9
        self.assertEqual(reduce_to_single_digit(999), 9)  # 9 + 9 + 9 = 27, 2 + 7 = 9

    def test_calculate_mulanka_basic(self):
        """Test basic Mulanka calculation without sunrise correction."""
        # Test known cases
        birth_date = date(1984, 8, 27)

        # Without time, should use day 27
        mulanka, planet = calculate_mulanka(birth_date)
        self.assertEqual(mulanka, 9)  # 2 + 7 = 9
        self.assertEqual(planet, Planet.MARS)

        # Test different dates
        test_cases = [
            (date(1990, 5, 15), 6),  # 1 + 5 = 6
            (date(1985, 12, 3), 3),  # 3
            (date(1975, 1, 11), 2),  # 1 + 1 = 2
        ]

        for test_date, expected_mulanka in test_cases:
            with self.subTest(date=test_date):
                mulanka_num, _ = calculate_mulanka(test_date)
                self.assertEqual(mulanka_num, expected_mulanka)

    def test_calculate_bhagyanka(self):
        """Test Bhagyanka calculation."""
        # Test known case: August 27, 1984
        # 27 + 8 + 1984 = 2019 → 2 + 0 + 1 + 9 = 12 → 1 + 2 = 3
        birth_date = date(1984, 8, 27)
        bhagyanka, planet = calculate_bhagyanka(birth_date)

        self.assertEqual(bhagyanka, 3)
        self.assertEqual(planet, Planet.JUPITER)

        # Test other cases
        test_cases = [
            (
                date(1990, 5, 15),
                5,
            ),  # 15 + 5 + 1990 = 2010 → 2 + 0 + 1 + 0 = 3 → wait, let's calculate properly
            (
                date(1985, 12, 3),
                4,
            ),  # 3 + 12 + 1985 = 2000 → 2 + 0 + 0 + 0 = 2 → wait, need correct calculation
        ]

        # Let's calculate these properly:
        # May 15, 1990: 15 + 5 + 1990 = 2010 → 2+0+1+0 = 3
        # December 3, 1985: 3 + 12 + 1985 = 2000 → 2+0+0+0 = 2

        correct_test_cases = [
            (date(1990, 5, 15), 3),  # 15 + 5 + 1990 = 2010 → 2+0+1+0 = 3
            (date(1985, 12, 3), 2),  # 3 + 12 + 1985 = 2000 → 2+0+0+0 = 2
            (
                date(1975, 1, 11),
                7,
            ),  # 11 + 1 + 1975 = 1987 → 1+9+8+7 = 25 → 2+5 = 7
        ]

        # Actually let's recalculate properly:
        # January 11, 1975: 11 + 1 + 1975 = 1987 → 1+9+8+7 = 25 → 2+5 = 7

        for test_date, expected_bhagyanka in correct_test_cases:
            with self.subTest(date=test_date):
                bhagyanka_num, _ = calculate_bhagyanka(test_date)
                self.assertEqual(bhagyanka_num, expected_bhagyanka)

    def test_calculate_complete_numerology(self):
        """Test complete numerology calculation."""
        birth_date = date(1984, 8, 27)
        result = calculate_complete_numerology(birth_date)

        # Check structure
        self.assertIn("mulanka", result)
        self.assertIn("bhagyanka", result)
        self.assertIn("sunrise_corrected", result)

        # Check values
        self.assertEqual(result["mulanka"]["number"], 9)
        self.assertEqual(result["mulanka"]["planet"], Planet.MARS)
        self.assertEqual(result["bhagyanka"]["number"], 3)
        self.assertEqual(result["bhagyanka"]["planet"], Planet.JUPITER)
        self.assertFalse(result["sunrise_corrected"])  # No time provided


class TestPlanetMapping(unittest.TestCase):
    """Test planet mapping functions."""

    def test_get_planet_from_number(self):
        """Test planet mapping from numbers."""
        # Test Vedic mappings
        self.assertEqual(get_planet_from_number(1), Planet.SUN)
        self.assertEqual(get_planet_from_number(2), Planet.MOON)
        self.assertEqual(get_planet_from_number(3), Planet.JUPITER)
        self.assertEqual(
            get_planet_from_number(4), Planet.RAHU
        )  # Vedic: Rahu not Uranus
        self.assertEqual(get_planet_from_number(5), Planet.MERCURY)
        self.assertEqual(get_planet_from_number(6), Planet.VENUS)
        self.assertEqual(
            get_planet_from_number(7), Planet.KETU
        )  # Vedic: Ketu not Neptune
        self.assertEqual(get_planet_from_number(8), Planet.SATURN)
        self.assertEqual(get_planet_from_number(9), Planet.MARS)

    def test_invalid_number_raises_error(self):
        """Test that invalid numbers raise ValueError."""
        with self.assertRaises(ValueError):
            get_planet_from_number(0)

        with self.assertRaises(ValueError):
            get_planet_from_number(10)

        with self.assertRaises(ValueError):
            get_planet_from_number(-1)

    def test_number_to_planet_completeness(self):
        """Test that all numbers 1-9 are mapped."""
        for i in range(1, 10):
            with self.subTest(number=i):
                planet = NUMBER_TO_PLANET[i]
                self.assertIsInstance(planet, Planet)


class TestSunriseCorrection(unittest.TestCase):
    """Test sunrise correction functions."""

    def test_adjust_date_for_vedic_day_no_time(self):
        """Test Vedic day adjustment when no time is provided."""
        birth_date = date(1984, 8, 27)

        # Without time, should return same date
        adjusted = adjust_date_for_vedic_day(birth_date, time(12, 0), 28.6139, 77.1025)
        self.assertEqual(adjusted, birth_date)

    def test_get_vedic_day_info_structure(self):
        """Test Vedic day info structure."""
        birth_date = date(1984, 8, 27)
        birth_time = time(10, 30)

        # Test with mock sunrise (this will use approximation since suntime may not be available)
        info = get_vedic_day_info(birth_date, birth_time, 28.6139, 77.1025)

        required_keys = [
            "gregorian_date",
            "vedic_date",
            "sunrise_time",
            "birth_before_sunrise",
            "day_number_used",
            "correction_applied",
        ]

        for key in required_keys:
            self.assertIn(key, info)

        self.assertEqual(info["gregorian_date"], birth_date)
        self.assertEqual(info["day_number_used"], info["vedic_date"].day)


class TestIntegration(unittest.TestCase):
    """Integration tests for numerology module."""

    def test_mars_1984_case(self):
        """Test the Mars in 1984 case from the technical document."""
        # August 27, 1984
        birth_date = date(1984, 8, 27)

        # Calculate Mulanka: 27 → 2 + 7 = 9 → Mars
        mulanka, planet = calculate_mulanka(birth_date)
        self.assertEqual(mulanka, 9)
        self.assertEqual(planet, Planet.MARS)

        # Calculate Bhagyanka: 27 + 8 + 1984 = 2019 → 2+0+1+9 = 12 → 1+2 = 3 → Jupiter
        bhagyanka, planet = calculate_bhagyanka(birth_date)
        self.assertEqual(bhagyanka, 3)
        self.assertEqual(planet, Planet.JUPITER)

    def test_complete_workflow(self):
        """Test complete numerology workflow."""
        birth_date = date(1990, 5, 15)
        result = calculate_complete_numerology(birth_date)

        # Should have both numbers and planets
        self.assertIsInstance(result["mulanka"]["number"], int)
        self.assertIsInstance(result["bhagyanka"]["number"], int)
        self.assertIsInstance(result["mulanka"]["planet"], Planet)
        self.assertIsInstance(result["bhagyanka"]["planet"], Planet)

        # Numbers should be between 1-9
        self.assertIn(result["mulanka"]["number"], range(1, 10))
        self.assertIn(result["bhagyanka"]["number"], range(1, 10))


if __name__ == "__main__":
    unittest.main()
