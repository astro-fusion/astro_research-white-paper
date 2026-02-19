"""
Datetime Utilities

Provides functions for date/time parsing, timezone conversion, and
Julian Day calculation.
"""

import math
from datetime import datetime
from typing import Optional, Union

import pytz
from dateutil import parser as date_parser


def parse_datetime(
    date_input: Union[str, datetime],
    time_input: Optional[str] = "00:00",
    timezone_str: str = "UTC",
) -> datetime:
    """
    Parse date and time strings into a timezone-aware datetime object.

    Args:
        date_input: Date string (e.g., "1984-08-27") or datetime object
        time_input: Time string (e.g., "10:30")
        timezone_str: Timezone string (e.g., "Asia/Kolkata")

    Returns:
        Timezone-aware datetime object
    """
    if isinstance(date_input, datetime):
        dt = date_input
    else:
        # Combine date and time
        dt_str = f"{date_input} {time_input}"
        try:
            dt = date_parser.parse(dt_str)
        except (ValueError, TypeError):
            # Fallback to simple ISO parsing or just date
            dt = date_parser.parse(str(date_input))

    # Handle timezone
    tz = pytz.timezone(timezone_str)
    if dt.tzinfo is None:
        dt = tz.localize(dt)
    else:
        dt = dt.astimezone(tz)

    return dt


def convert_timezone(dt: datetime, target_tz_str: str) -> datetime:
    """
    Convert a datetime object to a target timezone.

    Args:
        dt: Datetime object
        target_tz_str: Target timezone string

    Returns:
        Datetime object in target timezone
    """
    target_tz = pytz.timezone(target_tz_str)
    if dt.tzinfo is None:
        # Assume UTC if naive, or raise error?
        # Assuming UTC is safer than local for ambiguity
        dt = pytz.UTC.localize(dt)

    return dt.astimezone(target_tz)


def julian_day(dt: datetime) -> float:
    """
    Calculate Julian Day Number from a datetime object.

    This implementation matches the standard astronomical algorithm.

    Args:
        dt: Datetime object

    Returns:
        Julian Day Number as float
    """
    # Convert to UTC if timezone-aware
    if dt.tzinfo is not None:
        utc_tm = dt.astimezone(pytz.UTC).timetuple()
        year, month, day = utc_tm.tm_year, utc_tm.tm_mon, utc_tm.tm_mday
        # Add fractional day from time
        # Note: timetuple doesn't include microseconds, need to get them from dt
        utc_dt = dt.astimezone(pytz.UTC)
        hour = (
            utc_dt.hour
            + utc_dt.minute / 60.0
            + (utc_dt.second + utc_dt.microsecond / 1e6) / 3600.0
        )
    else:
        year, month, day = dt.year, dt.month, dt.day
        hour = dt.hour + dt.minute / 60.0 + (dt.second + dt.microsecond / 1e6) / 3600.0

    # Calculate Julian Day
    if month <= 2:
        year -= 1
        month += 12

    a = math.floor(year / 100)
    b = 2 - a + math.floor(a / 4)

    jd = (
        math.floor(365.25 * (year + 4716))
        + math.floor(30.6001 * (month + 1))
        + day
        + b
        - 1524.5
        + hour / 24.0
    )

    return jd
