"""
Vedic Planetary Number Mapping

Implements the Vedic numerology system where numbers 1-9 are mapped to planets.
Unlike Western systems, Vedic numerology assigns 4 to Rahu and 7 to Ketu.

This mapping is critical for the numerology-astrology integration as it determines
which planetary positions are evaluated for support/contradiction analysis.
"""

from typing import Dict

from ..config.constants import PLANET_NAMES, Planet

# Vedic Number-to-Planet Mapping
# This is the core mapping that differentiates Vedic from Western numerology
NUMBER_TO_PLANET: Dict[int, Planet] = {
    1: Planet.SUN,  # Authority, Ego, Soul, Vitality
    2: Planet.MOON,  # Mind, Emotions, Nurturing
    3: Planet.JUPITER,  # Wisdom, Expansion, Optimism
    4: Planet.RAHU,  # Illusion, Materialism, Innovation (NOT Uranus in Vedic)
    5: Planet.MERCURY,  # Intellect, Communication, Logic
    6: Planet.VENUS,  # Luxury, Art, Desire, Relationship
    7: Planet.KETU,  # Detachment, Moksha, Intuition (NOT Neptune in Vedic)
    8: Planet.SATURN,  # Discipline, Delay, Structure
    9: Planet.MARS,  # Energy, Aggression, Action
}

# Reverse mapping for lookups
PLANET_TO_NUMBER: Dict[Planet, int] = {
    planet: number for number, planet in NUMBER_TO_PLANET.items()
}

# Vedic qualities associated with each number
NUMBER_QUALITIES: Dict[int, str] = {
    1: "Authority, Ego, Soul, Vitality",
    2: "Mind, Emotions, Nurturing",
    3: "Wisdom, Expansion, Optimism",
    4: "Illusion, Materialism, Innovation",
    5: "Intellect, Communication, Logic",
    6: "Luxury, Art, Desire, Relationship",
    7: "Detachment, Moksha, Intuition",
    8: "Discipline, Delay, Structure",
    9: "Energy, Aggression, Action",
}


def get_planet_from_number(number: int) -> Planet:
    """
    Get the planet associated with a numerological number.

    Args:
        number: Numerological number (1-9)

    Returns:
        Planet enum value

    Raises:
        ValueError: If number is not in valid range (1-9)
    """
    if not isinstance(number, int) or number < 1 or number > 9:
        raise ValueError(f"Number must be an integer between 1 and 9, got {number}")

    return NUMBER_TO_PLANET[number]


def get_number_from_planet(planet: Planet) -> int:
    """
    Get the numerological number associated with a planet.

    Args:
        planet: Planet enum value

    Returns:
        Numerological number (1-9)
    """
    return PLANET_TO_NUMBER[planet]


def get_planet_name(planet: Planet) -> str:
    """
    Get the display name for a planet.

    Args:
        planet: Planet enum value

    Returns:
        Human-readable planet name
    """
    return PLANET_NAMES[planet]


def get_number_qualities(number: int) -> str:
    """
    Get the Vedic qualities associated with a numerological number.

    Args:
        number: Numerological number (1-9)

    Returns:
        String describing the qualities

    Raises:
        ValueError: If number is not in valid range (1-9)
    """
    if not isinstance(number, int) or number < 1 or number > 9:
        raise ValueError(f"Number must be an integer between 1 and 9, got {number}")

    return NUMBER_QUALITIES[number]


def validate_vedic_mapping() -> bool:
    """
    Validate that the Vedic mapping is correctly implemented.

    This function checks that:
    - Numbers 4 and 7 map to Rahu and Ketu (not Uranus/Neptune)
    - All planets are properly mapped
    - No duplicate mappings exist

    Returns:
        True if validation passes, raises AssertionError otherwise
    """
    # Check Vedic-specific mappings
    assert (
        NUMBER_TO_PLANET[4] == Planet.RAHU
    ), "Number 4 must map to Rahu in Vedic system"
    assert (
        NUMBER_TO_PLANET[7] == Planet.KETU
    ), "Number 7 must map to Ketu in Vedic system"

    # Check that all numbers 1-9 are mapped
    for i in range(1, 10):
        assert i in NUMBER_TO_PLANET, f"Number {i} must be mapped"

    # Check that all planets are used exactly once
    planets_used = set(NUMBER_TO_PLANET.values())
    expected_planets = {
        Planet.SUN,
        Planet.MOON,
        Planet.MARS,
        Planet.MERCURY,
        Planet.JUPITER,
        Planet.VENUS,
        Planet.SATURN,
        Planet.RAHU,
        Planet.KETU,
    }

    assert (
        planets_used == expected_planets
    ), f"Planet mapping mismatch: {planets_used} vs {expected_planets}"

    return True


# Run validation on module import
validate_vedic_mapping()
