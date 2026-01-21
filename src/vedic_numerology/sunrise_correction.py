"""
Sunrise correction for Vedic day logic.

In Vedic tradition, the "day" begins at sunrise, not at midnight. For Mulanka,
this means births before local sunrise are treated as the previous day.
"""

from __future__ import annotations

import math
from datetime import date, datetime, time, timedelta
from typing import Optional, Tuple, cast

try:
    from suntime import Sun
except ImportError:  # pragma: no cover
    Sun = None

FLATLIB_AVAILABLE = False
try:  # pragma: no cover
    import flatlib  # noqa: F401

    FLATLIB_AVAILABLE = True
except ImportError:  # pragma: no cover
    pass


def get_sunrise_time(
    target_date: date, latitude: float, longitude: float
) -> Optional[datetime]:
    if not (-90 <= latitude <= 90):
        raise ValueError(f"Latitude must be between -90 and 90, got {latitude}")
    if not (-180 <= longitude <= 180):
        raise ValueError(f"Longitude must be between -180 and 180, got {longitude}")

    if Sun is not None:
        try:
            sun = Sun(latitude, longitude)
            sunrise = sun.get_sunrise_time(target_date)
            return cast(datetime, sunrise)
        except Exception:
            pass

    if FLATLIB_AVAILABLE:
        try:
            sunrise_hour = _calculate_sunrise_approximation(latitude, longitude, target_date)
            return datetime.combine(
                target_date,
                time(hour=int(sunrise_hour), minute=int((sunrise_hour % 1) * 60)),
            )
        except Exception:
            pass

    return None


def _calculate_sunrise_approximation(latitude: float, longitude: float, d: date) -> float:
    day_of_year = d.timetuple().tm_yday
    declination = 23.45 * math.sin(math.radians(360 * (284 + day_of_year) / 365))
    equation_of_time = 4 * math.sin(math.radians(360 * (day_of_year - 81) / 365))
    solar_noon = 12 - longitude / 15 - equation_of_time / 60

    hour_angle = math.acos(
        -math.tan(math.radians(latitude)) * math.tan(math.radians(declination))
    )
    hour_angle_deg = math.degrees(hour_angle)
    sunrise_offset = hour_angle_deg / 15
    sunrise = solar_noon - sunrise_offset
    return sunrise % 24


def adjust_date_for_vedic_day(
    birth_date: date, birth_time: time, latitude: float, longitude: float
) -> date:
    birth_dt = datetime.combine(birth_date, birth_time)
    sunrise = get_sunrise_time(birth_date, latitude, longitude)
    if sunrise is None:
        return birth_date

    if birth_dt.time() < sunrise.time():
        return birth_date - timedelta(days=1)
    return birth_date


def validate_coordinates(latitude: float, longitude: float) -> Tuple[bool, str]:
    if not (-90 <= latitude <= 90):
        return False, f"Latitude must be between -90 and 90 degrees, got {latitude}"
    if not (-180 <= longitude <= 180):
        return False, f"Longitude must be between -180 and 180 degrees, got {longitude}"
    return True, ""

