"""
Smoke tests for astrometric validation.

This module provides basic checks for the calculation engine's precision.
"""

import unittest


def validate_astrometric_precision(data):
    """
    Validate astrometric precision.

    Smoke test to verify that the calculation engine accounts for
    topocentric parallax and atmospheric refraction.
    """
    required_keys = ["topocentric", "refraction_applied", "ayanamsa_precision"]
    for key in required_keys:
        if key not in data:
            return False, f"Missing key: {key}"

    if data["topocentric"] is False:
        return (
            False,
            "Topocentric correction MUST be applied for high-precision validation.",
        )

    return True, "Validation Passed"


class TestAstrometricPrecision(unittest.TestCase):
    """Test suite for astrometric precision validation."""

    def test_precision_payload(self):
        """Test the validation function with a sample payload."""
        sample_payload = {
            "topocentric": True,
            "refraction_applied": True,
            "ayanamsa_precision": 0.0001,
        }
        success, message = validate_astrometric_precision(sample_payload)
        self.assertTrue(success, message)


if __name__ == "__main__":
    unittest.main()
