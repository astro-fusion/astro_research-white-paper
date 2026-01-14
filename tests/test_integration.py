"""
Integration tests for the complete Vedic Numerology-Astrology system.

Tests end-to-end workflows combining numerology, astrology, and dignity scoring.
"""

import os
import sys
import unittest
from datetime import date, datetime

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from vedic_numerology import VedicNumerologyAstrology, analyze_birth_chart
from vedic_numerology.config.constants import Planet


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


if __name__ == "__main__":
    unittest.main()
