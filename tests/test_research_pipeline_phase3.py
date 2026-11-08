"""Test suite for research pipeline phase 3."""

import os
import sys
import tempfile
import unittest

import numpy as np
import pandas as pd

from studies._paths import study_dir  # noqa: E402

EARTHQUAKE_SCRIPTS = str(study_dir("earthquake") / "scripts")
if EARTHQUAKE_SCRIPTS not in sys.path:
    sys.path.append(EARTHQUAKE_SCRIPTS)


class TestResearchPipelinePhase3(unittest.TestCase):
    """Tests for Phase 3 pipeline."""

    def setUp(self):
        """Initialize fixtures."""
        # Run in a temp dir so generated outputs never land in the repo.
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self._old_cwd = os.getcwd()
        self.addCleanup(os.chdir, self._old_cwd)
        os.chdir(self._tmp.name)

        # Create a dummy regression matrix for testing
        self.test_matrix_path = "test_regression_matrix.csv"

        # Random data
        dates = pd.date_range(start="2023-01-01", periods=100)
        data = {
            "date": dates,
            "udn": np.random.randint(1, 10, 100),
            "year": [2023] * 100,
            "eq_count_m5": np.random.poisson(lam=1.0, size=100),  # Poisson dist
            "mars_score": np.random.uniform(0, 100, 100),
            "saturn_score": np.random.uniform(0, 100, 100),
            "sun_score": np.random.uniform(0, 100, 100),
            "moon_score": np.random.uniform(0, 100, 100),
        }
        df = pd.DataFrame(data)
        df.to_csv(self.test_matrix_path, index=False)

    def tearDown(self):
        """Clean up fixtures."""
        if os.path.exists(self.test_matrix_path):
            os.remove(self.test_matrix_path)

    def test_model_training_execution(self):
        """Test that train_models.train_models runs on valid data."""
        import train_models  # noqa: E402

        # Capture stdout to check for success messages
        # We just want to ensure it calls fit() and produces output
        try:
            train_models.train_models(self.test_matrix_path)
        except Exception as e:
            self.fail(f"train_models failed with exception: {e}")

        # Check if output JSON was created
        self.assertTrue(os.path.exists("model_results.json"))
        if os.path.exists("model_results.json"):
            os.remove("model_results.json")


if __name__ == "__main__":
    unittest.main()
