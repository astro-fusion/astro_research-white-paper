"""
Test Suite for Vedic Numerology-Astrology Integration System

Includes unit tests, integration tests, and reference case validations.
"""

import numpy as np

# Test configuration and fixtures
import pytest


# Set up test environment
def pytest_configure(config):
    """Configure pytest for the test suite."""
    # Set random seed for reproducible tests
    np.random.seed(42)

    # Add markers
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line(
        "markers", "reference: marks tests that validate against reference cases"
    )
