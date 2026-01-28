import os
import sys
import unittest
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd

# Add src to path
sys.path.append(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../use_cases/earthquake/scripts")
    )
)


class TestValidationScript(unittest.TestCase):

    def setUp(self):
        # Create a dummy regression matrix for testing
        self.test_matrix_path = "test_validation_matrix.csv"

        # Random data
        dates = pd.date_range(start="2023-01-01", periods=50)  # 50 days
        data = {
            "date": dates,
            "udn": np.random.randint(1, 10, 50),
            "year": [2023] * 50,
            "eq_count_m5": np.random.poisson(lam=1.0, size=50),
            "mars_score": np.random.uniform(0, 100, 50),
            "saturn_score": np.random.uniform(0, 100, 50),
        }
        df = pd.DataFrame(data)
        df.to_csv(self.test_matrix_path, index=False)

    def tearDown(self):
        if os.path.exists(self.test_matrix_path):
            os.remove(self.test_matrix_path)
        if os.path.exists("validation_report.json"):
            os.remove("validation_report.json")
        if os.path.exists("monte_carlo_distribution.png"):
            os.remove("monte_carlo_distribution.png")

    def test_validation_execution(self):
        """Test that run_validation runs with small N shuffles."""
        import validate_results

        # Use small number of shuffles for speed
        try:
            validate_results.run_validation(self.test_matrix_path, n_shuffles=10)
        except Exception as e:
            self.fail(f"run_validation failed with: {e}")

        # Check outputs
        self.assertTrue(os.path.exists("validation_report.json"))
        # Plot might not generate in headless env without display, but code catches exception
        # so mostly checking script finished.


if __name__ == "__main__":
    unittest.main()
