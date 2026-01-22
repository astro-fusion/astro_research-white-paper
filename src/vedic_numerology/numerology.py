"""
Numerology primitives (Mulanka/Bhagyanka) used by the integration layer.

This is a small, self-contained implementation derived from the existing
`use_cases/numerology` code, but packaged under `src/` so imports work in
library contexts (tests, docs, API, Streamlit) without fiddling with sys.path.
"""

from __future__ import annotations

from datetime import date, time
from typing import Optional, Tuple, Union

from vedic_astrology_core.config.constants import Planet

from .planet_mapping import get_planet_from_number
from .sunrise_correction import adjust_date_for_vedic_day


def reduce_to_single_digit(number: Union[int, str]) -> int:
    if isinstance(number, str):
        number = int(number)
    if not isinstance(number, int):
        raise TypeError(f"number must be int or str, got {type(number)}")
    if number < 0:
        raise ValueError(f"number must be non-negative, got {number}")
    if number == 0:
        return 9
    while number > 9:
        number = sum(int(d) for d in str(number))
    return number


def calculate_mulanka(
    birth_date: date,
    birth_time: Optional[time] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
) -> Tuple[int, Planet]:
    if not isinstance(birth_date, date):
        raise TypeError("birth_date must be a date object")

    day_number = birth_date.day
    if birth_time is not None and latitude is not None and longitude is not None:
        corrected_date = adjust_date_for_vedic_day(
            birth_date, birth_time, latitude, longitude
        )
        day_number = corrected_date.day

    mulanka = reduce_to_single_digit(day_number)
    planet = get_planet_from_number(mulanka)
    return mulanka, planet


def calculate_bhagyanka(birth_date: date) -> Tuple[int, Planet]:
    if not isinstance(birth_date, date):
        raise TypeError("birth_date must be a date object")

    total = birth_date.day + birth_date.month + birth_date.year
    bhagyanka = reduce_to_single_digit(total)
    planet = get_planet_from_number(bhagyanka)
    return bhagyanka, planet


def calculate_complete_numerology(
    birth_date: date,
    birth_time: Optional[time] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
) -> dict:
    sunrise_corrected = (
        birth_time is not None and latitude is not None and longitude is not None
    )
    mulanka_num, mulanka_planet = calculate_mulanka(
        birth_date, birth_time, latitude, longitude
    )
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
