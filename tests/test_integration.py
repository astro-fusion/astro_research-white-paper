"""
Integration tests for the complete Vedic Numerology-Astrology system.

Tests end-to-end workflows combining numerology, astrology, and dignity scoring.
"""

import os
import sys
import unittest
from datetime import date, datetime

import pandas as pd

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from vedic_numerology import VedicNumerologyAstrology, analyze_birth_chart  # noqa: E402
from vedic_numerology.config.constants import Planet  # noqa: E402


class TestCompleteWorkflow(unittest.TestCase):
    """Test complete analysis workflows."""

    def setUp(self):
        """Set up test fixtures."""
        # Use the Mars 1984 case as primary test case
        self.birth_date = date(1984, 8, 27)
        self.birth_time = datetime.strptime("10:30:00", "%H:%M:%S").time()
        self.latitude = 28.6139  # Delhi
        self.longitude = 77.1025  # Delhi

        # Create analysis object
        self.analysis = VedicNumerologyAstrology(
            self.birth_date, self.birth_time, self.latitude, self.longitude
        )

    def test_mars_1984_complete_analysis(self):
        """Test complete analysis for Mars 1984 case."""
        # Check numerology results
        mulanka_data = self.analysis.calculate_mulanka()
        self.assertEqual(mulanka_data["number"], 9)
        self.assertEqual(mulanka_data["planet"], Planet.MARS)

        bhagyanka_data = self.analysis.calculate_bhagyanka()
        self.assertEqual(bhagyanka_data["number"], 3)
        self.assertEqual(bhagyanka_data["planet"], Planet.JUPITER)

        # Check support analysis
        support_analysis = self.analysis.analyze_support_contradiction()

        # Should have analysis for both planets
        self.assertIn("mulanka", support_analysis)
        self.assertIn("bhagyanka", support_analysis)
        self.assertIn("overall", support_analysis)

        # Check structure
        mulanka_analysis = support_analysis["mulanka"]
        required_keys = ["planet", "score", "support_level", "dignity_type", "details"]
        for key in required_keys:
            self.assertIn(key, mulanka_analysis)

        # Scores should be numeric
        self.assertIsInstance(mulanka_analysis["score"], (int, float))
        self.assertIsInstance(support_analysis["bhagyanka"]["score"], (int, float))

    def test_report_generation(self):
        """Test complete report generation."""
        report = self.analysis.generate_report()

        # Check report structure
        self.assertIsInstance(report, str)
        self.assertIn("VEDIC NUMEROLOGY-ASTROLOGY ANALYSIS REPORT", report)
        self.assertIn("BIRTH DATA:", report)
        self.assertIn("NUMEROLOGY CALCULATIONS:", report)
        self.assertIn("PLANETARY SUPPORT ANALYSIS:", report)

        # Check specific values are included
        self.assertIn("Mulanka (Birth Number): 9", report)
        self.assertIn("Bhagyanka (Destiny Number): 3", report)
        self.assertIn("Mars", report)
        self.assertIn("Jupiter", report)

    def test_dignity_scoring_integration(self):
        """Test dignity scoring integration."""
        # Score both planets
        mars_score = self.analysis.score_dignity(Planet.MARS)
        jupiter_score = self.analysis.score_dignity(Planet.JUPITER)

        # Check score structure
        required_keys = [
            "score",
            "base_score",
            "dignity_type",
            "sign_lord",
            "friendship",
            "modifiers",
        ]
        for key in required_keys:
            self.assertIn(key, mars_score)
            self.assertIn(key, jupiter_score)

        # Scores should be reasonable (0-100)
        self.assertGreaterEqual(mars_score["score"], 0)
        self.assertLessEqual(mars_score["score"], 100)
        self.assertGreaterEqual(jupiter_score["score"], 0)
        self.assertLessEqual(jupiter_score["score"], 100)


class TestConvenienceFunctions(unittest.TestCase):
    """Test convenience functions for quick analysis."""

    def test_analyze_birth_chart_function(self):
        """Test the analyze_birth_chart convenience function."""
        birth_date = date(1984, 8, 27)
        analysis = analyze_birth_chart(birth_date)

        # Should return a VedicNumerologyAstrology object
        self.assertIsInstance(analysis, VedicNumerologyAstrology)

        # Should have basic functionality
        mulanka = analysis.calculate_mulanka()
        self.assertEqual(mulanka["number"], 9)
        self.assertEqual(mulanka["planet"], Planet.MARS)

    def test_different_birth_dates(self):
        """Test analysis with different birth dates."""
        test_cases = [
            (date(1990, 5, 15), "Expected numerology results"),
            (date(1975, 1, 11), "Another test case"),
            (date(2000, 12, 25), "Millennium baby"),
        ]

        for birth_date, description in test_cases:
            with self.subTest(birth_date=birth_date, description=description):
                analysis = analyze_birth_chart(birth_date)

                # Should complete analysis without errors
                mulanka = analysis.calculate_mulanka()
                bhagyanka = analysis.calculate_bhagyanka()
                support = analysis.analyze_support_contradiction()

                # Basic validation
                self.assertIsInstance(mulanka["number"], int)
                self.assertIsInstance(bhagyanka["number"], int)
                self.assertIn("mulanka", support)
                self.assertIn("bhagyanka", support)


class TestVisualizationIntegration(unittest.TestCase):
    """Test visualization integration (without actual plotting)."""

    def setUp(self):
        """Set up test fixtures."""
        self.analysis = analyze_birth_chart(date(1984, 8, 27))

    def test_comparison_chart_setup(self):
        """Test comparison chart setup (without actual plotting)."""
        # This tests that the setup works, but doesn't create actual plots
        # in unit test environment

        try:
            # Try to create comparison chart
            chart = self.analysis.plot_numerology_comparison(use_plotly=False)
            # If we get here without error, basic setup works
            self.assertIsNotNone(chart)
        except ImportError:
            # Matplotlib may not be available in test environment
            self.skipTest("Visualization libraries not available")

    def test_dignity_analysis_setup(self):
        """Test dignity analysis chart setup."""
        try:
            chart = self.analysis.plot_dignity_analysis(Planet.MARS, use_plotly=False)
            self.assertIsNotNone(chart)
        except ImportError:
            self.skipTest("Visualization libraries not available")


class TestErrorHandling(unittest.TestCase):
    """Test error handling in integrated workflows."""

    def test_invalid_birth_date(self):
        """Test handling of invalid birth dates."""
        with self.assertRaises((ValueError, TypeError)):
            VedicNumerologyAstrology("invalid-date")

    def test_invalid_coordinates(self):
        """Test handling of invalid coordinates."""
        birth_date = date(1984, 8, 27)

        # Invalid latitude
        with self.assertRaises(ValueError):
            VedicNumerologyAstrology(birth_date, latitude=91.0)

        # Invalid longitude
        with self.assertRaises(ValueError):
            VedicNumerologyAstrology(birth_date, longitude=181.0)

    def test_missing_ephemeris(self):
        """Test graceful handling when ephemeris is not available."""
        # This should work even without Swiss Ephemeris for basic numerology
        birth_date = date(1984, 8, 27)
        analysis = VedicNumerologyAstrology(birth_date)

        # Numerology should still work
        mulanka = analysis.calculate_mulanka()
        self.assertEqual(mulanka["number"], 9)

        # Astrology-dependent features may fail gracefully
        # (exact behavior depends on implementation)


class TestConfigurationIntegration(unittest.TestCase):
    """Test configuration integration."""

    def test_custom_ayanamsa_system(self):
        """Test using different Ayanamsa systems."""
        birth_date = date(1984, 8, 27)

        # Test with Raman Ayanamsa
        analysis = VedicNumerologyAstrology(birth_date, ayanamsa_system="raman")

        # Should initialize without errors
        self.assertIsNotNone(analysis)

        # Should use specified Ayanamsa
        self.assertEqual(analysis.ayanamsa_system, "raman")

    def test_invalid_ayanamsa_system(self):
        """Test handling of invalid Ayanamsa systems."""
        birth_date = date(1984, 8, 27)

        with self.assertRaises(ValueError):
            VedicNumerologyAstrology(birth_date, ayanamsa_system="invalid_system")


class TestPerformanceScenarios(unittest.TestCase):
    """Test performance-related scenarios."""

    def test_multiple_calculations(self):
        """Test multiple calculations don't interfere with each other."""
        birth_dates = [
            date(1984, 8, 27),
            date(1990, 5, 15),
            date(1975, 1, 11),
        ]

        results = []
        for birth_date in birth_dates:
            analysis = analyze_birth_chart(birth_date)
            mulanka = analysis.calculate_mulanka()
            results.append(mulanka["number"])

        # Should get consistent results
        self.assertEqual(results[0], 9)  # Mars case
        # Other results may vary but should be valid numbers
        for result in results:
            self.assertIsInstance(result, int)
            self.assertIn(result, range(1, 10))


class TestTimeSeriesIntegration(unittest.TestCase):
    """Test time series functionality integration."""

    def setUp(self):
        """Set up test fixtures."""
        from datetime import datetime

        from vedic_astrology_core.time_series import (
            compute_astrology_strength_series,
            compute_combined_series,
            compute_numerology_series,
        )

        self.compute_planet_strength = compute_astrology_strength_series
        self.compute_numerology = compute_numerology_series
        self.compute_combined = compute_combined_series

        # Test date range (small for speed)
        self.start_date = datetime(2024, 1, 1)
        self.end_date = datetime(2024, 1, 31)  # One month
        self.step_days = 7  # Weekly

    def test_planet_strength_series_basic(self):
        """Test basic planetary strength series generation."""
        df = self.compute_planet_strength(
            self.start_date, self.end_date, self.step_days
        )

        # Check it's a DataFrame
        self.assertIsInstance(df, pd.DataFrame)

        # Check required columns exist
        self.assertIn("date", df.columns)

        # Should have all planets
        expected_planets = [
            "SUN",
            "MOON",
            "MARS",
            "MERCURY",
            "JUPITER",
            "VENUS",
            "SATURN",
            "RAHU",
            "KETU",
        ]
        for planet in expected_planets:
            col_name = f"astrology_{planet}"
            self.assertIn(col_name, df.columns)

            # Values should be reasonable (0-100)
            values = df[col_name]
            for val in values:
                self.assertIsInstance(val, (int, float))
                self.assertGreaterEqual(val, 0)
                self.assertLessEqual(val, 100)

        # Should have at least one row
        self.assertGreater(len(df), 0)

    def test_numerology_series_basic(self):
        """Test basic numerology series generation."""
        df = self.compute_numerology(self.start_date, self.end_date, self.step_days)

        # Check it's a DataFrame
        self.assertIsInstance(df, pd.DataFrame)

        # Check required columns exist
        self.assertIn("date", df.columns)
        self.assertIn("numerology_active_planet", df.columns)
        self.assertIn("numerology_mulanka_number", df.columns)

        # Should have all planets
        expected_planets = [
            "SUN",
            "MOON",
            "MARS",
            "MERCURY",
            "JUPITER",
            "VENUS",
            "SATURN",
            "RAHU",
            "KETU",
        ]
        for planet in expected_planets:
            col_name = f"numerology_{planet}"
            self.assertIn(col_name, df.columns)

            # Numerology values should be either 0 or 100 (binary)
            values = df[col_name]
            for val in values:
                self.assertIsInstance(val, (int, float))
                self.assertIn(val, [0, 100])

        # Should have at least one row
        self.assertGreater(len(df), 0)

    def test_combined_series_basic(self):
        """Test basic combined series generation."""
        df = self.compute_combined(self.start_date, self.end_date, self.step_days)

        # Check it's a DataFrame
        self.assertIsInstance(df, pd.DataFrame)

        # Check required columns exist
        self.assertIn("date", df.columns)

        # Should have both numerology and astrology columns
        numerology_cols = [col for col in df.columns if col.startswith("numerology_")]
        astrology_cols = [col for col in df.columns if col.startswith("astrology_")]

        self.assertGreater(len(numerology_cols), 0)
        self.assertGreater(len(astrology_cols), 0)

        # Should have at least one row
        self.assertGreater(len(df), 0)

    def test_date_spacing(self):
        """Test that dates are properly spaced according to step_days."""
        step_days = 5
        df = self.compute_planet_strength(self.start_date, self.end_date, step_days)

        dates = pd.to_datetime(df["date"])
        self.assertGreater(len(dates), 1)

        # Check spacing between consecutive dates
        for i in range(1, len(dates)):
            from datetime import timedelta

            expected_diff = timedelta(days=step_days)
            actual_diff = dates.iloc[i] - dates.iloc[i - 1]
            self.assertEqual(
                actual_diff, expected_diff, f"Date spacing incorrect at index {i}"
            )

    def test_step_size_variations(self):
        """Test different step sizes work correctly."""
        step_sizes = [1, 3, 7, 14]

        for step in step_sizes:
            with self.subTest(step_days=step):
                df = self.compute_planet_strength(self.start_date, self.end_date, step)

                # Should have at least one data point
                self.assertGreater(len(df), 0)

                # If more than one point, check spacing
                if len(df) > 1:
                    from datetime import timedelta

                    dates = pd.to_datetime(df["date"])
                    diff = dates.iloc[1] - dates.iloc[0]
                    self.assertEqual(diff, timedelta(days=step))

    def test_edge_case_single_day(self):
        """Test edge case with single day range."""
        from datetime import timedelta

        single_date = self.start_date
        end_date = single_date + timedelta(days=1)

        df = self.compute_planet_strength(single_date, end_date, 1)

        # Should have two data points (start and end dates, 1 day apart with step=1)
        self.assertEqual(len(df), 2)
        self.assertEqual(pd.to_datetime(df["date"].iloc[0]).date(), single_date.date())
        self.assertEqual(pd.to_datetime(df["date"].iloc[1]).date(), end_date.date())

    def test_reverse_date_range_error(self):
        """Test that reverse date ranges raise appropriate errors."""
        from datetime import timedelta

        # End before start
        end_before_start = self.start_date - timedelta(days=1)

        with self.assertRaises((ValueError, AssertionError)):
            self.compute_planet_strength(self.start_date, end_before_start, 1)


if __name__ == "__main__":
    unittest.main()
