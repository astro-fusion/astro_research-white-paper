import os
import sys
import unittest
from datetime import date, datetime
from unittest.mock import MagicMock, patch

import pandas as pd

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))
sys.path.append(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../use_cases/earthquake/scripts")
    )
)

from vedic_astrology_core.astrology.ephemeris import EphemerisEngine
from vedic_astrology_core.dignity.global_scorer import GlobalShadbalaScorer


class TestResearchPipelinePhase2(unittest.TestCase):

    def setUp(self):
        self.eph = EphemerisEngine()
        self.scorer = GlobalShadbalaScorer(self.eph)

    def test_global_scorer_structure(self):
        """Test that scorer returns expected structure."""
        jd = self.eph.datetime_to_julian_day(datetime.now())
        scores = self.scorer.calculate_global_power(jd)

        self.assertIn("Sun", scores)
        self.assertIn("Mars", scores)
        self.assertGreaterEqual(scores["Mars"], 0)
        self.assertLessEqual(
            scores["Mars"], 100
        )  # Should be normalized (though bonus might go over 100 on raw, but clamped)

    def test_chesta_bala_retrograde_boost(self):
        """Test that retrograde motion increases score."""
        # Mock specific position data to simulate retrograde
        with patch.object(self.eph, "get_all_planet_positions") as mock_get:
            mock_get.return_value = {
                "Mars": {
                    "longitude": 10,  # Aries
                    "sign": 0,  # Aries
                    "retrograde": True,  # Boost!
                    "longitude_speed": -0.5,
                }
            }

            scores = self.scorer.calculate_global_power(2459000.5)
            # Base score for Own Sign is 75. Retrograde boost *1.3 -> ~97.5.
            self.assertGreater(scores["Mars"], 80)

    def test_regression_matrix_script_imports(self):
        """Test that build_matrix script is importable and has function."""
        import build_regression_matrix

        self.assertTrue(hasattr(build_regression_matrix, "build_matrix"))


if __name__ == "__main__":
    unittest.main()
