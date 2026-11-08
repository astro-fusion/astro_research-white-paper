"""
Planetary Friendship Matrices.

Implements Naisargika Maitri (Natural Friendship) and Tatkalika Maitri
(Temporary Friendship) systems used in Vedic astrology for determining
planetary relationships.
"""

from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from ..config.constants import Planet, PlanetDict

if TYPE_CHECKING:
    from ..astrology.chart import BirthChart


class FriendshipType(Enum):
    """Types of planetary friendship."""

    NATURAL_FRIEND = "Natural Friend"
    NATURAL_ENEMY = "Natural Enemy"
    NATURAL_NEUTRAL = "Natural Neutral"
    TEMPORARY_FRIEND = "Temporary Friend"
    TEMPORARY_ENEMY = "Temporary Enemy"
    ADHI_MITRA = "Adhi Mitra"
    MITRA = "Mitra"
    SAMA = "Sama"
    SHATRU = "Shatru"
    ADHI_SHATRU = "Adhi Shatru"


# Naisargika Maitri (natural friendship), BPHS Ch. 3. Natural friendship is
# not symmetric (e.g. the Moon has no enemies, yet Mercury counts the Moon as
# an enemy). Rows are the planet, columns how it regards the other planet.
NAISARGIKA_MAITRI: Dict[Planet, Dict[Planet, FriendshipType]] = {
    # Sun: friends Moon Mars Jupiter; neutral Mercury; enemies Venus Saturn
    Planet.SUN: {
        Planet.SUN: FriendshipType.NATURAL_NEUTRAL,
        Planet.MOON: FriendshipType.NATURAL_FRIEND,
        Planet.MARS: FriendshipType.NATURAL_FRIEND,
        Planet.MERCURY: FriendshipType.NATURAL_NEUTRAL,
        Planet.JUPITER: FriendshipType.NATURAL_FRIEND,
        Planet.VENUS: FriendshipType.NATURAL_ENEMY,
        Planet.SATURN: FriendshipType.NATURAL_ENEMY,
        Planet.RAHU: FriendshipType.NATURAL_ENEMY,
        Planet.KETU: FriendshipType.NATURAL_ENEMY,
    },
    # Moon: friends Sun Mercury; neutral Mars Jupiter Venus Saturn; enemies -
    Planet.MOON: {
        Planet.SUN: FriendshipType.NATURAL_FRIEND,
        Planet.MOON: FriendshipType.NATURAL_NEUTRAL,
        Planet.MARS: FriendshipType.NATURAL_NEUTRAL,
        Planet.MERCURY: FriendshipType.NATURAL_FRIEND,
        Planet.JUPITER: FriendshipType.NATURAL_NEUTRAL,
        Planet.VENUS: FriendshipType.NATURAL_NEUTRAL,
        Planet.SATURN: FriendshipType.NATURAL_NEUTRAL,
        Planet.RAHU: FriendshipType.NATURAL_ENEMY,
        Planet.KETU: FriendshipType.NATURAL_ENEMY,
    },
    # Mars: friends Sun Moon Jupiter; neutral Venus Saturn; enemies Mercury
    Planet.MARS: {
        Planet.SUN: FriendshipType.NATURAL_FRIEND,
        Planet.MOON: FriendshipType.NATURAL_FRIEND,
        Planet.MARS: FriendshipType.NATURAL_NEUTRAL,
        Planet.MERCURY: FriendshipType.NATURAL_ENEMY,
        Planet.JUPITER: FriendshipType.NATURAL_FRIEND,
        Planet.VENUS: FriendshipType.NATURAL_NEUTRAL,
        Planet.SATURN: FriendshipType.NATURAL_NEUTRAL,
        Planet.RAHU: FriendshipType.NATURAL_FRIEND,
        Planet.KETU: FriendshipType.NATURAL_FRIEND,
    },
    # Mercury: friends Sun Venus; neutral Mars Jupiter Saturn; enemies Moon
    Planet.MERCURY: {
        Planet.SUN: FriendshipType.NATURAL_FRIEND,
        Planet.MOON: FriendshipType.NATURAL_ENEMY,
        Planet.MARS: FriendshipType.NATURAL_NEUTRAL,
        Planet.MERCURY: FriendshipType.NATURAL_NEUTRAL,
        Planet.JUPITER: FriendshipType.NATURAL_NEUTRAL,
        Planet.VENUS: FriendshipType.NATURAL_FRIEND,
        Planet.SATURN: FriendshipType.NATURAL_NEUTRAL,
        Planet.RAHU: FriendshipType.NATURAL_ENEMY,
        Planet.KETU: FriendshipType.NATURAL_ENEMY,
    },
    # Jupiter: friends Sun Moon Mars; neutral Saturn; enemies Mercury Venus
    Planet.JUPITER: {
        Planet.SUN: FriendshipType.NATURAL_FRIEND,
        Planet.MOON: FriendshipType.NATURAL_FRIEND,
        Planet.MARS: FriendshipType.NATURAL_FRIEND,
        Planet.MERCURY: FriendshipType.NATURAL_ENEMY,
        Planet.JUPITER: FriendshipType.NATURAL_NEUTRAL,
        Planet.VENUS: FriendshipType.NATURAL_ENEMY,
        Planet.SATURN: FriendshipType.NATURAL_NEUTRAL,
        Planet.RAHU: FriendshipType.NATURAL_ENEMY,
        Planet.KETU: FriendshipType.NATURAL_ENEMY,
    },
    # Venus: friends Mercury Saturn; neutral Mars Jupiter; enemies Sun Moon
    Planet.VENUS: {
        Planet.SUN: FriendshipType.NATURAL_ENEMY,
        Planet.MOON: FriendshipType.NATURAL_ENEMY,
        Planet.MARS: FriendshipType.NATURAL_NEUTRAL,
        Planet.MERCURY: FriendshipType.NATURAL_FRIEND,
        Planet.JUPITER: FriendshipType.NATURAL_NEUTRAL,
        Planet.VENUS: FriendshipType.NATURAL_NEUTRAL,
        Planet.SATURN: FriendshipType.NATURAL_FRIEND,
        Planet.RAHU: FriendshipType.NATURAL_FRIEND,
        Planet.KETU: FriendshipType.NATURAL_FRIEND,
    },
    # Saturn: friends Mercury Venus; neutral Jupiter; enemies Sun Moon Mars
    Planet.SATURN: {
        Planet.SUN: FriendshipType.NATURAL_ENEMY,
        Planet.MOON: FriendshipType.NATURAL_ENEMY,
        Planet.MARS: FriendshipType.NATURAL_ENEMY,
        Planet.MERCURY: FriendshipType.NATURAL_FRIEND,
        Planet.JUPITER: FriendshipType.NATURAL_NEUTRAL,
        Planet.VENUS: FriendshipType.NATURAL_FRIEND,
        Planet.SATURN: FriendshipType.NATURAL_NEUTRAL,
        Planet.RAHU: FriendshipType.NATURAL_FRIEND,
        Planet.KETU: FriendshipType.NATURAL_FRIEND,
    },
    # Rahu follows Saturn (and is hostile to Ketu)
    Planet.RAHU: {
        Planet.SUN: FriendshipType.NATURAL_ENEMY,
        Planet.MOON: FriendshipType.NATURAL_ENEMY,
        Planet.MARS: FriendshipType.NATURAL_ENEMY,
        Planet.MERCURY: FriendshipType.NATURAL_FRIEND,
        Planet.JUPITER: FriendshipType.NATURAL_NEUTRAL,
        Planet.VENUS: FriendshipType.NATURAL_FRIEND,
        Planet.SATURN: FriendshipType.NATURAL_FRIEND,
        Planet.RAHU: FriendshipType.NATURAL_NEUTRAL,
        Planet.KETU: FriendshipType.NATURAL_ENEMY,
    },
    # Ketu follows Mars (and is hostile to Rahu)
    Planet.KETU: {
        Planet.SUN: FriendshipType.NATURAL_FRIEND,
        Planet.MOON: FriendshipType.NATURAL_FRIEND,
        Planet.MARS: FriendshipType.NATURAL_FRIEND,
        Planet.MERCURY: FriendshipType.NATURAL_ENEMY,
        Planet.JUPITER: FriendshipType.NATURAL_FRIEND,
        Planet.VENUS: FriendshipType.NATURAL_NEUTRAL,
        Planet.SATURN: FriendshipType.NATURAL_NEUTRAL,
        Planet.RAHU: FriendshipType.NATURAL_ENEMY,
        Planet.KETU: FriendshipType.NATURAL_NEUTRAL,
    },
}


def get_natural_friendship(planet1: Planet, planet2: Planet) -> FriendshipType:
    """
    Get the natural friendship between two planets.

    Args:
        planet1: First planet
        planet2: Second planet

    Returns:
        FriendshipType enum value
    """
    if planet1 not in NAISARGIKA_MAITRI or planet2 not in NAISARGIKA_MAITRI[planet1]:
        # Default to neutral if relationship not defined
        return FriendshipType.NATURAL_NEUTRAL

    return NAISARGIKA_MAITRI[planet1][planet2]


def calculate_tatkalika_maitri(
    chart: "BirthChart", planet1: Planet, planet2: Planet
) -> FriendshipType:
    """
    Calculate temporary friendship between two planets based on chart positions.

    In Vedic astrology, planets become temporary friends or enemies based on their
    positions relative to each other in houses.

    Args:
        chart: BirthChart object with planetary positions
        planet1: First planet
        planet2: Second planet

    Returns:
        FriendshipType (temporary relationship)
    """
    # Get planet positions
    if not hasattr(chart, "planets"):
        return FriendshipType.NATURAL_NEUTRAL
    planets = PlanetDict(chart.planets)
    if planet1 not in planets or planet2 not in planets:
        return FriendshipType.NATURAL_NEUTRAL

    planet1_pos = planets[planet1]
    planet2_pos = planets[planet2]

    # Calculate house positions relative to each other
    # Planets in 2, 3, 4, 10, 11, 12 houses from each other are temporary friends
    house_diff = (planet2_pos["sign"] - planet1_pos["sign"]) % 12

    friendly_houses = {
        1,
        2,
        3,
        9,
        10,
        11,
    }  # 2, 3, 4, 10, 11, 12 from planet1 (0-indexed)

    if house_diff in friendly_houses:
        return FriendshipType.TEMPORARY_FRIEND
    else:
        return FriendshipType.TEMPORARY_ENEMY


def get_combined_friendship(
    natural: FriendshipType, temporary: FriendshipType
) -> FriendshipType:
    """
    Combine natural and temporary friendship into five-fold friendship.

    Standard Vedic combination rules:
    - Friend + Friend = Great Friend
    - Friend + Neutral = Friend
    - Enemy + Friend = Neutral
    - Neutral + Friend = Friend
    - Neutral + Enemy = Enemy
    - Enemy + Enemy = Great Enemy
    """
    # Friend + Friend = Great Friend
    if natural == FriendshipType.NATURAL_FRIEND:
        if temporary == FriendshipType.TEMPORARY_FRIEND:
            return FriendshipType.ADHI_MITRA
        else:
            return FriendshipType.SAMA

    # Enemy + Friend = Neutral / Enemy + Enemy = Great Enemy
    elif natural == FriendshipType.NATURAL_ENEMY:
        if temporary == FriendshipType.TEMPORARY_FRIEND:
            return FriendshipType.SAMA
        else:
            return FriendshipType.ADHI_SHATRU

    # Neutral + Friend = Friend / Neutral + Enemy = Enemy
    else:
        if temporary == FriendshipType.TEMPORARY_FRIEND:
            return FriendshipType.MITRA
        else:
            return FriendshipType.SHATRU


def calculate_panchadha_maitri(chart: "BirthChart", planet: Planet) -> Dict[str, Any]:
    """
    Calculate Panchadha Maitri (five-fold friendship) for a planet.

    Combines Naisargika (Natural) and Tatkalika (Temporary) friendships
    into the definitive five-fold relationship for all other planets.

    Args:
        chart: BirthChart object
        planet: Planet to analyze

    Returns:
        Dictionary mapping each planet to its five-fold relationship type.
    """
    relationships = {}

    planets = [
        Planet.SUN,
        Planet.MOON,
        Planet.MARS,
        Planet.MERCURY,
        Planet.JUPITER,
        Planet.VENUS,
        Planet.SATURN,
        Planet.RAHU,
        Planet.KETU,
    ]

    for other_planet in planets:
        if other_planet == planet:
            continue

        natural_rel = get_natural_friendship(planet, other_planet)
        temp_rel = calculate_tatkalika_maitri(chart, planet, other_planet)
        combined = get_combined_friendship(natural_rel, temp_rel)

        relationships[other_planet.name] = {
            "natural": natural_rel.value,
            "temporary": temp_rel.value,
            "combined": combined.value,
        }

    return relationships


def are_planets_friends(
    planet1: Planet, planet2: Planet, chart: Optional["BirthChart"] = None
) -> bool:
    """
    Determine if two planets are friends (natural or temporary).

    Args:
        planet1: First planet
        planet2: Second planet
        chart: BirthChart object (optional, for temporary friendship)

    Returns:
        True if planets are friends
    """
    # Check natural friendship first
    natural_rel = get_natural_friendship(planet1, planet2)
    if natural_rel == FriendshipType.NATURAL_FRIEND:
        return True
    elif natural_rel == FriendshipType.NATURAL_ENEMY:
        return False

    # If chart provided, check temporary friendship
    if chart is not None:
        temp_rel = calculate_tatkalika_maitri(chart, planet1, planet2)
        if temp_rel == FriendshipType.TEMPORARY_FRIEND:
            return True

    # Default to neutral (not friends)
    return False


def get_friendship_description(
    planet1: Planet, planet2: Planet, chart: Optional["BirthChart"] = None
) -> str:
    """
    Get a descriptive string of the friendship between two planets.

    Args:
        planet1: First planet
        planet2: Second planet
        chart: BirthChart object (optional)

    Returns:
        Descriptive string of relationship
    """
    natural_rel = get_natural_friendship(planet1, planet2)

    description = f"{planet1.name} and {planet2.name} are {natural_rel.value}"

    if chart is not None:
        temp_rel = calculate_tatkalika_maitri(chart, planet1, planet2)
        description += f" and {temp_rel.value.lower()} in this chart"

    return description


def get_planet_friends(
    planet: Planet, chart: Optional["BirthChart"] = None
) -> List[Planet]:
    """
    Get list of planets that are friends with the given planet.

    Args:
        planet: Planet to check friendships for
        chart: BirthChart object (optional, for temporary friendships)

    Returns:
        List of friendly planets
    """
    friends = []

    planets = [
        Planet.SUN,
        Planet.MOON,
        Planet.MARS,
        Planet.MERCURY,
        Planet.JUPITER,
        Planet.VENUS,
        Planet.SATURN,
        Planet.RAHU,
        Planet.KETU,
    ]

    for other_planet in planets:
        if other_planet != planet and are_planets_friends(planet, other_planet, chart):
            friends.append(other_planet)

    return friends
