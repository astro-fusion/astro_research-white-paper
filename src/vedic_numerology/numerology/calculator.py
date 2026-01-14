"""
Numerology Calculator

Implements Vedic numerological calculations including:
- Mulanka (Birth Number/Psychic Number) with sunrise correction
- Bhagyanka (Destiny Number/Life Path Number)
- Core reduction algorithms

The calculator handles the mathematical operations that form the foundation
of numerological analysis in the Vedic tradition.
"""

import math
from datetime import date, datetime, time
from typing import Optional, Tuple, Union

from .planet_mapping import Planet, get_planet_from_number


def reduce_to_single_digit(number: Union[int, str]) -> int:
    """
    Reduce a number to a single digit using recursive summation.

    This is the core algorithm used in numerology for reducing compound numbers
    to their fundamental vibration (1-9).

    Args:
        number: Number to reduce (int or string representation)

    Returns:
        Single digit between 1-9

    Raises:
        ValueError: If input cannot be converted to a valid number
        TypeError: If input is not int or str
    """
    if isinstance(number, str):
        try:
            number = int(number)
        except ValueError:
            raise ValueError(f"Cannot convert '{number}' to integer")

    if not isinstance(number, int):
        raise TypeError(f"Number must be int or str, got {type(number)}")

    if number < 0:
        raise ValueError(f"Number must be non-negative, got {number}")

    # Handle zero case (though zero shouldn't occur in numerology)
    if number == 0:
        return 9  # Master numbers reduce to 9

    # Reduce to single digit
    while number > 9:
        # Sum the digits
        number = sum(int(digit) for digit in str(number))

    return number


def calculate_mulanka(
    birth_date: date,
    birth_time: Optional[time] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
) -> Tuple[int, Planet]:
    """
    Calculate the Mulanka (Birth Number/Psychic Number).

    The Mulanka represents the core personality and immediate reactions.
    It is calculated from the day of birth, with Vedic sunrise correction if coordinates provided.

    Args:
        birth_date: Date of birth
        birth_time: Time of birth (optional, for sunrise correction)
        latitude: Latitude for sunrise calculation (optional)
        longitude: Longitude for sunrise calculation (optional)

    Returns:
        Tuple of (mulanka_number, planet) where number is 1-9 and planet is the ruling Planet

    Raises:
        ValueError: If date is invalid or coordinates are incomplete
    """
    if not isinstance(birth_date, date):
        raise TypeError("birth_date must be a date object")

    # Apply sunrise correction if all parameters provided
    day_number = birth_date.day

    if birth_time is not None and latitude is not None and longitude is not None:
        # Import here to avoid circular imports
        from .sunrise_correction import adjust_date_for_vedic_day

        corrected_date = adjust_date_for_vedic_day(
            birth_date, birth_time, latitude, longitude
        )
        day_number = corrected_date.day

    # Calculate Mulanka by reducing day number
    mulanka = reduce_to_single_digit(day_number)

    # Get associated planet
    planet = get_planet_from_number(mulanka)

    return mulanka, planet


def calculate_bhagyanka(birth_date: date) -> Tuple[int, Planet]:
    """
    Calculate the Bhagyanka (Destiny Number/Life Path Number).

    The Bhagyanka represents the life path, karmic trajectory, and external circumstances.
    It is calculated by summing all components of the birth date and reducing to a single digit.

    Args:
        birth_date: Complete date of birth

    Returns:
        Tuple of (bhagyanka_number, planet) where number is 1-9 and planet is the ruling Planet

    Raises:
        TypeError: If birth_date is not a date object
    """
    if not isinstance(birth_date, date):
        raise TypeError("birth_date must be a date object")

    # Extract date components
    day = birth_date.day
    month = birth_date.month
    year = birth_date.year

    # Sum all components: Day + Month + Year
    total = day + month + year

    # Reduce to single digit
    bhagyanka = reduce_to_single_digit(total)

    # Get associated planet
    planet = get_planet_from_number(bhagyanka)

    return bhagyanka, planet


def calculate_complete_numerology(
    birth_date: date,
    birth_time: Optional[time] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
) -> dict:
    """
    Calculate complete numerological profile including Mulanka and Bhagyanka.

    This is a convenience function that provides both numbers and their planets
    along with additional metadata.

    Args:
        birth_date: Date of birth
        birth_time: Time of birth (optional, for sunrise correction)
        latitude: Latitude for sunrise calculation (optional)
        longitude: Longitude for sunrise calculation (optional)

    Returns:
        Dictionary containing numerological analysis with keys:
        - 'mulanka': {'number': int, 'planet': Planet, 'corrected': bool}
        - 'bhagyanka': {'number': int, 'planet': Planet}
        - 'sunrise_corrected': bool
    """
    sunrise_corrected = (
        birth_time is not None and latitude is not None and longitude is not None
    )

    # Calculate Mulanka
    mulanka_num, mulanka_planet = calculate_mulanka(
        birth_date, birth_time, latitude, longitude
    )

    # Calculate Bhagyanka
    bhagyanka_num, bhagyanka_planet = calculate_bhagyanka(birth_date)

    return {
        "mulanka": {
            "number": mulanka_num,
            "planet": mulanka_planet,
            "corrected": sunrise_corrected,
        },
        "bhagyanka": {"number": bhagyanka_num, "planet": bhagyanka_planet},
        "sunrise_corrected": sunrise_corrected,
    }


def get_numerology_relationship(mulanka_num: int, bhagyanka_num: int) -> str:
    """
    Analyze the relationship between Mulanka and Bhagyanka numbers.

    This provides insights into how the personality (Mulanka) interacts with
    the life path (Bhagyanka).

    Args:
        mulanka_num: Mulanka number (1-9)
        bhagyanka_num: Bhagyanka number (1-9)

    Returns:
        String describing the relationship

    Raises:
        ValueError: If numbers are not in valid range
    """
    if not (1 <= mulanka_num <= 9):
        raise ValueError(f"Mulanka must be 1-9, got {mulanka_num}")
    if not (1 <= bhagyanka_num <= 9):
        raise ValueError(f"Bhagyanka must be 1-9, got {bhagyanka_num}")

    if mulanka_num == bhagyanka_num:
        return "Harmonic Unity: Personality and destiny are aligned - strong potential for self-actualization"

    # Check for complementary numbers (summing to 10)
    if mulanka_num + bhagyanka_num == 10:
        return "Complementary Balance: Personality and destiny complement each other perfectly"

    # Get planets for deeper analysis
    mulanka_planet = get_planet_from_number(mulanka_num)
    bhagyanka_planet = get_planet_from_number(bhagyanka_num)

    # This would be enhanced with planetary friendship analysis
    # For now, provide basic analysis
    diff = abs(mulanka_num - bhagyanka_num)

    if diff <= 2:
        return "Close Harmony: Personality and destiny work closely together"
    elif diff >= 6:
        return "Dynamic Tension: Personality and destiny present significant challenges"
    else:
        return "Balanced Growth: Personality and destiny offer opportunities for development"
