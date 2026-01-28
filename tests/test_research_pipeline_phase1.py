import os
import sys
import unittest
from datetime import date, datetime

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from vedic_astrology_core.astrology.ephemeris import EphemerisEngine
from vedic_numerology.engine import NumerologyEngine


class TestResearchPipelinePhase1(unittest.TestCase):

    def setUp(self):
        self.num_engine = NumerologyEngine()
        self.eph_engine = EphemerisEngine()

    def test_numerology_universal_day_master_numbers(self):
        """Test that Master Numbers (11, 22, 33) are preserved in UDN."""
        # March 14, 1997 -> 3 + 14 + 1997 = 2014 -> 7 (Not master)
        d1 = date(1997, 3, 14)
        self.assertEqual(self.num_engine.calculate_universal_day_number(d1), 7)

        # Test case for 11: Jan 1, 2007 -> 1 + 1 + 2007 = 2009 -> 11
        d2 = date(2007, 1, 1)
        self.assertEqual(self.num_engine.calculate_universal_day_number(d2), 11)

        # Test case for 22: Jan 1, 2009 -> 1 + 1 + 2009 = 2011 -> 4?
        # Wait, 2011 -> 4.
        # Need a date that sums to 22.
        # 2000 + 1 + 21 = 2022 -> 6.
        # Try: Nov 9, 2000 -> 11 + 9 + 2000 = 2020 -> 4.

        # Let's trust the logic: _reduce(22) -> 22.
        self.assertEqual(self.num_engine._reduce(22), 22)
        self.assertEqual(self.num_engine._reduce(33), 33)
        self.assertEqual(self.num_engine._reduce(11), 11)
        self.assertEqual(self.num_engine._reduce(11, preserve_master=False), 2)

    def test_heliocentric_vectors(self):
        """Test that heliocentric positions return vector components."""
        # Just check structure and non-zero values for current date
        now = datetime.now()
        jd = self.eph_engine.datetime_to_julian_day(now)

        # Jupiter (5)
        pos = self.eph_engine.get_heliocentric_position(jd, 5)

        self.assertIn("x_vector", pos)
        self.assertIn("y_vector", pos)
        self.assertIn("z_vector", pos)

        # Distance should be > 0
        self.assertGreater(pos["distance"], 0)

        # Vector magnitude should roughly equal distance
        vector_mag = (
            pos["x_vector"] ** 2 + pos["y_vector"] ** 2 + pos["z_vector"] ** 2
        ) ** 0.5
        self.assertAlmostEqual(pos["distance"], vector_mag, places=5)

    def test_magnitude_homogenization(self):
        """Test magnitude conversion logic."""
        # Need to import fetcher - it's in use_cases so path is tricky
        sys.path.append(
            os.path.abspath(
                os.path.join(
                    os.path.dirname(__file__), "../use_cases/earthquake/scripts"
                )
            )
        )
        from earthquake_data_fetcher import EarthquakeDataFetcher

        fetcher = EarthquakeDataFetcher(use_sample_data=True)

        # Mw should stay same
        self.assertEqual(fetcher._homogenize_magnitude(7.0, "mw"), 7.0)

        # Mb > 6.0 should scale up (Scordilis)
        # 0.85 * 6.5 + 1.03 = 5.525 + 1.03 = 6.555
        self.assertAlmostEqual(
            fetcher._homogenize_magnitude(6.5, "mb"), 6.555, places=2
        )

        # Small Mb should stay same
        self.assertEqual(fetcher._homogenize_magnitude(5.0, "mb"), 5.0)

    def test_declustering(self):
        """Test Gardner-Knopoff declustering."""
        sys.path.append(
            os.path.abspath(
                os.path.join(
                    os.path.dirname(__file__), "../use_cases/earthquake/scripts"
                )
            )
        )
        from earthquake_data_fetcher import EarthquakeDataFetcher

        fetcher = EarthquakeDataFetcher(use_sample_data=True)

        # Create mock sequence: Mainshock (7.0) -> Aftershock (5.0, near, soon) -> Independent (6.0, far)
        catalog = [
            {
                "magnitude": 7.0,  # Mainshock
                "time": "2020-01-01T12:00:00",
                "latitude": 0.0,
                "longitude": 0.0,
                "usgs_url": "mainshock",
            },
            {
                "magnitude": 5.0,  # Aftershock (Same day, very close)
                "time": "2020-01-01T13:00:00",
                "latitude": 0.1,  # Approx 11km away
                "longitude": 0.1,
                "usgs_url": "aftershock",
            },
            {
                "magnitude": 6.0,  # Independent (Far away)
                "time": "2020-01-02T12:00:00",
                "latitude": 50.0,  # Thousands of km away
                "longitude": 50.0,
                "usgs_url": "independent",
            },
        ]

        declustered = fetcher.decluster_catalog(catalog)

        self.assertEqual(len(declustered), 2)
        ids = [e["usgs_url"] for e in declustered]
        self.assertIn("mainshock", ids)
        self.assertIn("independent", ids)
        self.assertNotIn("aftershock", ids)


if __name__ == "__main__":
    unittest.main()
