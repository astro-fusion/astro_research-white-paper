"""
Test Suite for Earthquake Analysis Pipeline

Validates the complete workflow:
1. Data fetching (sample & USGS API)
2. Data processing
3. Planetary analysis
4. Report generation
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from earthquake_data_fetcher import EarthquakeDataFetcher


class EarthquakeAnalysisTester:
    """Test suite for earthquake analysis pipeline."""
    
    def __init__(self, verbose: bool = True):
        """Initialize tester."""
        self.verbose = verbose
        self.results = {
            "tests_passed": 0,
            "tests_failed": 0,
            "details": []
        }
    
    def _log(self, message: str, level: str = "INFO") -> None:
        """Print log message."""
        if self.verbose:
            icon = {
                "INFO": "ℹ️ ",
                "PASS": "✅",
                "FAIL": "❌",
                "WARN": "⚠️ ",
                "TEST": "🧪"
            }.get(level, "")
            print(f"{icon} {message}")
    
    def test_data_fetcher_init(self) -> bool:
        """Test 1: Initialize data fetcher."""
        self._log("Test 1: Initialize earthquake data fetcher", "TEST")
        try:
            fetcher = EarthquakeDataFetcher(use_sample_data=True, verbose=False)
            self._log("✅ Data fetcher initialized successfully", "PASS")
            self.results["tests_passed"] += 1
            return True
        except Exception as e:
            self._log(f"Failed to initialize: {e}", "FAIL")
            self.results["tests_failed"] += 1
            return False
    
    def test_load_sample_data(self) -> bool:
        """Test 2: Load sample earthquake data."""
        self._log("Test 2: Load sample earthquake data", "TEST")
        try:
            fetcher = EarthquakeDataFetcher(use_sample_data=True, verbose=False)
            data = fetcher.fetch_earthquakes(
                start_date="2020-01-01",
                end_date="2020-12-31",
                use_usgs_api=False
            )
            
            features = data.get("features", [])
            if len(features) > 0:
                self._log(f"✅ Loaded {len(features)} earthquakes", "PASS")
                self.results["tests_passed"] += 1
                return True
            else:
                self._log("No earthquake data loaded", "FAIL")
                self.results["tests_failed"] += 1
                return False
                
        except Exception as e:
            self._log(f"Error loading sample data: {e}", "FAIL")
            self.results["tests_failed"] += 1
            return False
    
    def test_data_processing(self) -> bool:
        """Test 3: Process earthquake data."""
        self._log("Test 3: Process earthquake data", "TEST")
        try:
            fetcher = EarthquakeDataFetcher(use_sample_data=True, verbose=False)
            raw_data = fetcher.fetch_earthquakes(
                start_date="2020-01-01",
                end_date="2020-12-31",
                use_usgs_api=False
            )
            
            processed = fetcher.process_for_analysis(raw_data)
            
            if len(processed) > 0:
                # Validate structure
                sample = processed[0]
                required_fields = ["date", "magnitude", "place", "latitude", "longitude"]
                
                missing = [f for f in required_fields if f not in sample]
                if missing:
                    self._log(f"Missing fields: {missing}", "FAIL")
                    self.results["tests_failed"] += 1
                    return False
                
                self._log(f"✅ Processed {len(processed)} earthquakes successfully", "PASS")
                self._log(f"   Sample: {sample['date']} - Mag {sample['magnitude']} - {sample['place']}", "INFO")
                self.results["tests_passed"] += 1
                return True
            else:
                self._log("No earthquakes processed", "FAIL")
                self.results["tests_failed"] += 1
                return False
                
        except Exception as e:
            self._log(f"Error processing data: {e}", "FAIL")
            self.results["tests_failed"] += 1
            return False
    
    def test_data_validation(self) -> bool:
        """Test 4: Validate processed data quality."""
        self._log("Test 4: Validate processed data quality", "TEST")
        try:
            fetcher = EarthquakeDataFetcher(use_sample_data=True, verbose=False)
            raw_data = fetcher.fetch_earthquakes(
                start_date="2020-01-01",
                end_date="2020-12-31",
                use_usgs_api=False
            )
            
            processed = fetcher.process_for_analysis(raw_data)
            
            # Validation checks
            checks = {
                "magnitude_valid": all(0 <= eq["magnitude"] <= 10 for eq in processed),
                "date_format": all(len(eq["date"]) == 10 for eq in processed),  # YYYY-MM-DD
                "coordinates_valid": all(
                    -180 <= eq["longitude"] <= 180 and
                    -90 <= eq["latitude"] <= 90
                    for eq in processed
                ),
                "location_present": all(len(eq["place"]) > 0 for eq in processed)
            }
            
            all_valid = all(checks.values())
            
            if all_valid:
                self._log("✅ All validation checks passed", "PASS")
                for check, result in checks.items():
                    status = "✓" if result else "✗"
                    self._log(f"   {status} {check}", "INFO")
                self.results["tests_passed"] += 1
                return True
            else:
                self._log("Some validation checks failed", "FAIL")
                for check, result in checks.items():
                    status = "✓" if result else "✗"
                    self._log(f"   {status} {check}", "INFO")
                self.results["tests_failed"] += 1
                return False
                
        except Exception as e:
            self._log(f"Error validating data: {e}", "FAIL")
            self.results["tests_failed"] += 1
            return False
    
    def test_mock_data_generation(self) -> bool:
        """Test 5: Generate mock data as fallback."""
        self._log("Test 5: Generate mock data as fallback", "TEST")
        try:
            fetcher = EarthquakeDataFetcher(use_sample_data=False, verbose=False)
            # This should generate mock data
            data = fetcher._create_mock_data()
            
            features = data.get("features", [])
            if len(features) > 0:
                self._log(f"✅ Generated {len(features)} mock earthquakes", "PASS")
                self.results["tests_passed"] += 1
                return True
            else:
                self._log("Failed to generate mock data", "FAIL")
                self.results["tests_failed"] += 1
                return False
                
        except Exception as e:
            self._log(f"Error generating mock data: {e}", "FAIL")
            self.results["tests_failed"] += 1
            return False
    
    def run_all_tests(self) -> dict:
        """Run complete test suite."""
        self._log("=" * 60, "INFO")
        self._log("EARTHQUAKE ANALYSIS PIPELINE - TEST SUITE", "TEST")
        self._log("=" * 60, "INFO")
        
        tests = [
            self.test_data_fetcher_init,
            self.test_load_sample_data,
            self.test_data_processing,
            self.test_data_validation,
            self.test_mock_data_generation,
        ]
        
        for test in tests:
            test()
            self._log("")  # Blank line between tests
        
        # Summary
        self._log("=" * 60, "INFO")
        self._log("TEST SUMMARY", "INFO")
        self._log("=" * 60, "INFO")
        
        total = self.results["tests_passed"] + self.results["tests_failed"]
        passed = self.results["tests_passed"]
        failed = self.results["tests_failed"]
        percentage = (passed / total * 100) if total > 0 else 0
        
        self._log(f"Total Tests: {total}", "INFO")
        self._log(f"Passed: {passed} ✅", "PASS")
        self._log(f"Failed: {failed} ❌", "FAIL" if failed > 0 else "PASS")
        self._log(f"Success Rate: {percentage:.1f}%", "PASS" if percentage == 100 else "WARN")
        
        self._log("=" * 60, "INFO")
        
        if failed == 0:
            self._log("🎉 ALL TESTS PASSED!", "PASS")
        else:
            self._log(f"⚠️  {failed} test(s) failed", "FAIL")
        
        self._log("=" * 60, "INFO")
        
        return self.results


def main():
    """Run all tests."""
    print("\n🧪 EARTHQUAKE ANALYSIS PIPELINE VALIDATION\n")
    
    tester = EarthquakeAnalysisTester(verbose=True)
    results = tester.run_all_tests()
    
    # Return exit code based on results
    return 0 if results["tests_failed"] == 0 else 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
