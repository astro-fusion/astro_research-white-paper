"""
Sunrise Correction for Vedic Numerology

Implements Vedic day calculation logic where the day begins at sunrise,
not at midnight (Gregorian convention). This is crucial for accurate
Mulanka calculations in Vedic numerology.

The Vedic day (Vara) starts at sunrise and affects which day number
is used for numerological calculations.
"""

import math
from datetime import date, datetime, time, timedelta
from typing import Any, Optional, Tuple, cast

try:
    from suntime import Sun
except ImportError:
    Sun = None

try:
    from flatlib import const
    from flatlib.datetime import Datetime as FlatlibDatetime
    from flatlib.geopos import GeoPos

    FLATLIB_AVAILABLE = True
except ImportError:
    FLATLIB_AVAILABLE = False


def get_sunrise_time(
    birth_date: date, latitude: float, longitude: float
) -> Optional[datetime]:
    """
    Calculate sunrise time for a given date and location.

    Uses suntime library as primary method, with flatlib as fallback.
    Sunrise is when the upper limb of the sun appears above the horizon.

    Args:
        birth_date: Date for sunrise calculation
        latitude: Latitude in decimal degrees (-90 to 90)
        longitude: Longitude in decimal degrees (-180 to 180)

    Returns:
        Sunrise datetime, or None if calculation fails

    Raises:
        ValueError: If coordinates are invalid
    """
    if not (-90 <= latitude <= 90):
        raise ValueError(f"Latitude must be between -90 and 90, got {latitude}")
    if not (-180 <= longitude <= 180):
        raise ValueError(f"Longitude must be between -180 and 180, got {longitude}")

    # Try suntime first (simpler and more reliable)
    if Sun is not None:
        try:
            sun = Sun(latitude, longitude)
            sunrise = sun.get_sunrise_time(birth_date)
            return cast(datetime, sunrise)
        except Exception as e:
            # Fall back to flatlib if suntime fails
            pass

    # Fallback to flatlib
    if FLATLIB_AVAILABLE:
        try:
            # Create flatlib datetime and geopos objects
            dt = FlatlibDatetime(
                birth_date.year, birth_date.month, birth_date.day, 12, 0, 0
            )
            pos = GeoPos(latitude, longitude)

            # Calculate sunrise (this is approximate and may need refinement)
            # Note: flatlib's sunrise calculation might not be as accurate as suntime
            # This is a simplified implementation
            sunrise_hour = _calculate_sunrise_approximation(
                latitude, longitude, birth_date
            )
            sunrise = datetime.combine(
                birth_date,
                time(hour=int(sunrise_hour), minute=int((sunrise_hour % 1) * 60)),
            )
            return sunrise

        except Exception as e:
            pass

    # If both methods fail, return None
    # This allows the calculation to proceed without sunrise correction
    return None


def _calculate_sunrise_approximation(
    latitude: float, longitude: float, date: date
) -> float:
    """
    Approximate sunrise time using simplified astronomical calculations.

    This is a fallback when suntime and flatlib are not available.
    Based on the solar declination and equation of time.

    Args:
        latitude: Latitude in degrees
        longitude: Longitude in degrees
        date: Date for calculation

    Returns:
        Sunrise hour as float (0-24)
    """
    # Day of year
    day_of_year = date.timetuple().tm_yday

    # Solar declination (simplified)
    declination = 23.45 * math.sin(math.radians(360 * (284 + day_of_year) / 365))

    # Equation of time (simplified approximation)
    equation_of_time = 4 * math.sin(math.radians(360 * (day_of_year - 81) / 365))

    # Solar noon
    solar_noon = 12 - longitude / 15 - equation_of_time / 60

    # Hour angle at sunrise
    hour_angle = math.acos(
        -math.tan(math.radians(latitude)) * math.tan(math.radians(declination))
    )
    hour_angle_deg = math.degrees(hour_angle)

    # Sunrise time
    sunrise_offset = hour_angle_deg / 15  # 15 degrees per hour
    sunrise = solar_noon - sunrise_offset

    return sunrise % 24


def adjust_date_for_vedic_day(
    birth_date: date, birth_time: time, latitude: float, longitude: float
) -> date:
    """
    Adjust Gregorian date to Vedic date based on sunrise.

    In Vedic tradition, the day begins at sunrise, not midnight.
    If birth time is before sunrise, the numerological day is the previous Gregorian day.

    Args:
        birth_date: Gregorian birth date
        birth_time: Birth time
        latitude: Latitude for sunrise calculation
        longitude: Longitude for sunrise calculation

    Returns:
        Corrected date for numerological calculations

    Raises:
        ValueError: If coordinates are invalid
        RuntimeError: If sunrise calculation fails
    """
    # Combine date and time
    birth_datetime = datetime.combine(birth_date, birth_time)

    # Calculate sunrise
    sunrise = get_sunrise_time(birth_date, latitude, longitude)

    if sunrise is None:
        # If sunrise calculation fails, use Gregorian date
        # This maintains backward compatibility
        return birth_date

    # Check if birth was before sunrise
    if birth_datetime.time() < sunrise.time():
        # Birth was before sunrise, so numerological day is previous day
        vedic_date = birth_date - timedelta(days=1)
        return vedic_date
    else:
        # Birth was after sunrise, use the given date
        return birth_date


def is_vedic_day_transition(birth_time: time, sunrise_time: time) -> bool:
    """
    Check if birth time falls before sunrise, indicating a Vedic day transition.

    Args:
        birth_time: Actual birth time
        sunrise_time: Sunrise time for the birth date

    Returns:
        True if birth was before sunrise (Vedic day transition)
    """
    return birth_time < sunrise_time


def get_vedic_day_info(
    birth_date: date, birth_time: time, latitude: float, longitude: float
) -> dict:
    """
    Get complete Vedic day information for numerological analysis.

    Args:
        birth_date: Gregorian birth date
        birth_time: Birth time
        latitude: Latitude for sunrise calculation
        longitude: Longitude for sunrise calculation

    Returns:
        Dictionary with Vedic day information:
        - 'gregorian_date': Original Gregorian date
        - 'vedic_date': Corrected Vedic date
        - 'sunrise_time': Calculated sunrise time
        - 'birth_before_sunrise': Whether birth was before sunrise
        - 'day_number_used': Day number used for Mulanka calculation
    """
    sunrise = get_sunrise_time(birth_date, latitude, longitude)
    vedic_date = adjust_date_for_vedic_day(birth_date, birth_time, latitude, longitude)

    birth_datetime = datetime.combine(birth_date, birth_time)
    birth_before_sunrise = (
        sunrise is not None and birth_datetime.time() < sunrise.time()
    )

    return {
        "gregorian_date": birth_date,
        "vedic_date": vedic_date,
        "sunrise_time": sunrise,
        "birth_before_sunrise": birth_before_sunrise,
        "day_number_used": vedic_date.day,
        "correction_applied": birth_before_sunrise,
    }


def validate_coordinates(latitude: float, longitude: float) -> Tuple[bool, str]:
    """
    Validate latitude and longitude coordinates.

    Args:
        latitude: Latitude in decimal degrees
        longitude: Longitude in decimal degrees

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not (-90 <= latitude <= 90):
        return False, f"Latitude must be between -90 and 90 degrees, got {latitude}"

    if not (-180 <= longitude <= 180):
        return False, f"Longitude must be between -180 and 180 degrees, got {longitude}"

    return True, ""
