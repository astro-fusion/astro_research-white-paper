
import unittest
import sys
import os
import pandas as pd
import numpy as np
from unittest.mock import MagicMock, patch

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../use_cases/earthquake/scripts')))

class TestResearchPipelinePhase3(unittest.TestCase):
    
    def setUp(self):
        # Create a dummy regression matrix for testing
        self.test_matrix_path = "test_regression_matrix.csv"
        
        # Random data
        dates = pd.date_range(start="2023-01-01", periods=100)
        data = {
            "date": dates,
            "udn": np.random.randint(1, 10, 100),
            "year": [2023]*100,
            "eq_count_m5": np.random.poisson(lam=1.0, size=100), # Poisson dist
            "mars_score": np.random.uniform(0, 100, 100),
            "saturn_score": np.random.uniform(0, 100, 100),
            "sun_score": np.random.uniform(0, 100, 100),
            "moon_score": np.random.uniform(0, 100, 100)
        }
        df = pd.DataFrame(data)
        df.to_csv(self.test_matrix_path, index=False)
        
    def tearDown(self):
        if os.path.exists(self.test_matrix_path):
            os.remove(self.test_matrix_path)
            
    def test_model_training_execution(self):
        """Test that train_models runs without crashing on valid data."""
        import train_models
        
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
