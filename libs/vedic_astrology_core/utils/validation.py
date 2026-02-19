"""
Validation Utilities

Provides functions for validating inputs such as birth data, coordinates,
and date ranges.
"""

from datetime import datetime
from typing import Optional

from .datetime_utils import parse_datetime


def validate_birth_data(
    date_str: str,
    time_str: str,
    lat: float,
    lon: float,
    timezone_str: Optional[str] = None,
) -> bool:
    """
    Validate birth data inputs.

    Args:
        date_str: Birth date string
        time_str: Birth time string
        lat: Latitude
        lon: Longitude
        timezone_str: Timezone string (optional)

    Returns:
        True if valid, raises ValueError otherwise.
    """
    # Validate date and time format by attempting to parse
    try:
        parse_datetime(date_str, time_str, timezone_str or "UTC")
    except Exception as e:
        raise ValueError(f"Invalid date/time format: {e}")

    # Validate coordinates
    validate_coordinates(lat, lon)

    return True


def validate_coordinates(lat: float, lon: float) -> bool:
    """
    Validate geographic coordinates.

    Args:
        lat: Latitude (-90 to 90)
        lon: Longitude (-180 to 180)

    Returns:
        True if valid, raises ValueError otherwise.
    """
    if not (-90 <= lat <= 90):
        raise ValueError(f"Latitude must be between -90 and 90, got {lat}")

    if not (-180 <= lon <= 180):
        raise ValueError(f"Longitude must be between -180 and 180, got {lon}")

    return True


def validate_date_range(
    dt: datetime, min_year: int = 1000, max_year: int = 3000
) -> bool:
    """
    Validate that a date is within a supported range.

    Args:
        dt: Datetime object
        min_year: Minimum supported year
        max_year: Maximum supported year

    Returns:
        True if valid, raises ValueError otherwise.
    """
    if not (min_year <= dt.year <= max_year):
        raise ValueError(
            f"Date year {dt.year} is out of supported range ({min_year}-{max_year})"
        )

    return True
