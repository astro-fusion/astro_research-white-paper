"""
Datetime Utilities.

Provides functions for date/time parsing, timezone conversion, and
Julian Day calculation.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Union

import pytz
import swisseph as swe
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


class NaiveDatetimeError(ValueError):
    """Raised when a naive datetime reaches an API that needs an instant."""


def require_aware(dt: datetime, name: str = "datetime") -> datetime:
    """Return ``dt`` unchanged if it is timezone-aware, else raise.

    A naive datetime is ambiguous (local time? UT?). Treating it as UT
    silently shifted Kathmandu charts by 5h45m, so public APIs reject it.

    Raises:
        NaiveDatetimeError: If ``dt`` has no tzinfo / utcoffset.
    """
    if not isinstance(dt, datetime):
        raise TypeError(f"{name} must be a datetime, got {type(dt).__name__}")
    if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
        raise NaiveDatetimeError(
            f"{name} {dt!r} is naive; attach a timezone (e.g. "
            "datetime(..., tzinfo=ZoneInfo('Asia/Kathmandu')) or timezone.utc)"
        )
    return dt


def convert_timezone(dt: datetime, target_tz_str: str) -> datetime:
    """
    Convert a timezone-aware datetime to a target timezone.

    Raises:
        NaiveDatetimeError: If ``dt`` is naive.
    """
    require_aware(dt)
    return dt.astimezone(pytz.timezone(target_tz_str))


def julian_day(dt: datetime) -> float:
    """
    Return the Julian day (UT) of a timezone-aware datetime.

    The instant is converted to UTC and passed to ``swe.julday`` (Gregorian
    calendar). UTC is used as UT; the difference (under 1 s) is far below
    every tolerance in this library.

    Raises:
        NaiveDatetimeError: If ``dt`` is naive.
    """
    require_aware(dt)
    utc = dt.astimezone(timezone.utc)
    hour = utc.hour + utc.minute / 60.0 + (utc.second + utc.microsecond / 1e6) / 3600.0
    return float(swe.julday(utc.year, utc.month, utc.day, hour, swe.GREG_CAL))


def julian_day_to_datetime(jd: float) -> datetime:
    """Return the UTC datetime of a Julian day (UT)."""
    return _JD_UNIX_EPOCH_DT + timedelta(days=jd - _JD_UNIX_EPOCH)


_JD_UNIX_EPOCH = 2440587.5
_JD_UNIX_EPOCH_DT = datetime(1970, 1, 1, tzinfo=timezone.utc)
