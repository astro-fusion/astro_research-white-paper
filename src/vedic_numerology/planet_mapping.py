"""
Vedic number-to-planet mapping (1-9) used by numerology.
"""

from __future__ import annotations

from typing import Dict

from vedic_astrology_core.config.constants import PLANET_NAMES, Planet

NUMBER_TO_PLANET: Dict[int, Planet] = {
    1: Planet.SUN,
    2: Planet.MOON,
    3: Planet.JUPITER,
    4: Planet.RAHU,
    5: Planet.MERCURY,
    6: Planet.VENUS,
    7: Planet.KETU,
    8: Planet.SATURN,
    9: Planet.MARS,
}

PLANET_TO_NUMBER: Dict[Planet, int] = {
    planet: number for number, planet in NUMBER_TO_PLANET.items()
}


def get_planet_from_number(number: int) -> Planet:
    if not isinstance(number, int) or number < 1 or number > 9:
        raise ValueError(f"Number must be an integer between 1 and 9, got {number}")
    return NUMBER_TO_PLANET[number]


def get_number_from_planet(planet: Planet) -> int:
    return PLANET_TO_NUMBER[planet]


def get_planet_name(planet: Planet) -> str:
    return PLANET_NAMES[planet]
