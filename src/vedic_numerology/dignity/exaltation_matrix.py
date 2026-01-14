"""
Exaltation and Debilitation Matrices

Contains the classical Vedic astrology exaltation and debilitation positions
for all planets, along with Moolatrikona ranges and sign rulership data.
"""

from enum import Enum
from typing import Dict, List, Optional, Tuple

from ..config.constants import Planet


# Zodiac signs
class ZodiacSign(Enum):
    ARIES = 0
    TAURUS = 1
    GEMINI = 2
    CANCER = 3
    LEO = 4
    VIRGO = 5
    LIBRA = 6
    SCORPIO = 7
    SAGITTARIUS = 8
    CAPRICORN = 9
    AQUARIUS = 10
    PISCES = 11


# Exaltation and Debilitation data
# Format: (sign_index, degrees_in_sign)
EXALTATION_TABLE: Dict[Planet, Tuple[int, float]] = {
    Planet.SUN: (ZodiacSign.ARIES.value, 10.0),  # Aries 10°
    Planet.MOON: (ZodiacSign.TAURUS.value, 3.0),  # Taurus 3°
    Planet.MARS: (ZodiacSign.CAPRICORN.value, 28.0),  # Capricorn 28°
    Planet.MERCURY: (ZodiacSign.VIRGO.value, 15.0),  # Virgo 15°
    Planet.JUPITER: (ZodiacSign.CANCER.value, 5.0),  # Cancer 5°
    Planet.VENUS: (ZodiacSign.PISCES.value, 27.0),  # Pisces 27°
    Planet.SATURN: (ZodiacSign.LIBRA.value, 20.0),  # Libra 20°
    # Rahu and Ketu: Special handling (Taurus/Scorpio convention)
    Planet.RAHU: (ZodiacSign.TAURUS.value, 0.0),  # Taurus (variable)
    Planet.KETU: (ZodiacSign.SCORPIO.value, 0.0),  # Scorpio (variable)
}

DEBILITATION_TABLE: Dict[Planet, Tuple[int, float]] = {
    Planet.SUN: (ZodiacSign.LIBRA.value, 10.0),  # Libra 10°
    Planet.MOON: (ZodiacSign.SCORPIO.value, 3.0),  # Scorpio 3°
    Planet.MARS: (ZodiacSign.CANCER.value, 28.0),  # Cancer 28°
    Planet.MERCURY: (ZodiacSign.PISCES.value, 15.0),  # Pisces 15°
    Planet.JUPITER: (ZodiacSign.CAPRICORN.value, 5.0),  # Capricorn 5°
    Planet.VENUS: (ZodiacSign.VIRGO.value, 27.0),  # Virgo 27°
    Planet.SATURN: (ZodiacSign.ARIES.value, 20.0),  # Aries 20°
    # Rahu and Ketu: Opposite signs to exaltation
    Planet.RAHU: (ZodiacSign.SCORPIO.value, 0.0),  # Scorpio (variable)
    Planet.KETU: (ZodiacSign.TAURUS.value, 0.0),  # Taurus (variable)
}

# Moolatrikona ranges: (start_sign, start_degrees, end_sign, end_degrees)
MOOLATRIKONA_TABLE: Dict[Planet, Tuple[int, float, int, float]] = {
    Planet.SUN: (ZodiacSign.LEO.value, 0.0, ZodiacSign.LEO.value, 20.0),  # Leo 0-20°
    Planet.MOON: (
        ZodiacSign.TAURUS.value,
        4.0,
        ZodiacSign.TAURUS.value,
        30.0,
    ),  # Taurus 4-30°
    Planet.MARS: (
        ZodiacSign.ARIES.value,
        0.0,
        ZodiacSign.ARIES.value,
        18.0,
    ),  # Aries 0-18°
    Planet.MERCURY: (
        ZodiacSign.VIRGO.value,
        16.0,
        ZodiacSign.VIRGO.value,
        20.0,
    ),  # Virgo 16-20°
    Planet.JUPITER: (
        ZodiacSign.SAGITTARIUS.value,
        0.0,
        ZodiacSign.SAGITTARIUS.value,
        13.0,
    ),  # Sagittarius 0-13°
    Planet.VENUS: (
        ZodiacSign.LIBRA.value,
        0.0,
        ZodiacSign.LIBRA.value,
        10.0,
    ),  # Libra 0-10°
    Planet.SATURN: (
        ZodiacSign.AQUARIUS.value,
        0.0,
        ZodiacSign.AQUARIUS.value,
        20.0,
    ),  # Aquarius 0-20°
    # Rahu and Ketu do not have Moolatrikona
}

# Own signs (Swakshetra) - planets rule these signs
OWN_SIGNS_TABLE: Dict[Planet, List[int]] = {
    Planet.SUN: [ZodiacSign.LEO.value],  # Leo
    Planet.MOON: [ZodiacSign.CANCER.value],  # Cancer
    Planet.MARS: [ZodiacSign.ARIES.value, ZodiacSign.SCORPIO.value],  # Aries, Scorpio
    Planet.MERCURY: [ZodiacSign.GEMINI.value, ZodiacSign.VIRGO.value],  # Gemini, Virgo
    Planet.JUPITER: [
        ZodiacSign.SAGITTARIUS.value,
        ZodiacSign.PISCES.value,
    ],  # Sagittarius, Pisces
    Planet.VENUS: [ZodiacSign.TAURUS.value, ZodiacSign.LIBRA.value],  # Taurus, Libra
    Planet.SATURN: [
        ZodiacSign.CAPRICORN.value,
        ZodiacSign.AQUARIUS.value,
    ],  # Capricorn, Aquarius
    # Rahu and Ketu don't rule signs traditionally
}

# Sign names for display
SIGN_NAMES: Dict[int, str] = {
    0: "Aries",
    1: "Taurus",
    2: "Gemini",
    3: "Cancer",
    4: "Leo",
    5: "Virgo",
    6: "Libra",
    7: "Scorpio",
    8: "Sagittarius",
    9: "Capricorn",
    10: "Aquarius",
    11: "Pisces",
}


def get_exaltation_sign(planet: Planet) -> Tuple[int, float, str]:
    """
    Get exaltation sign and degree for a planet.

    Args:
        planet: Planet enum

    Returns:
        Tuple of (sign_index, degrees, sign_name)
    """
    if planet not in EXALTATION_TABLE:
        raise ValueError(f"No exaltation data for planet {planet}")

    sign_index, degrees = EXALTATION_TABLE[planet]
    sign_name = SIGN_NAMES[sign_index]

    return sign_index, degrees, sign_name


def get_debilitation_sign(planet: Planet) -> Tuple[int, float, str]:
    """
    Get debilitation sign and degree for a planet.

    Args:
        planet: Planet enum

    Returns:
        Tuple of (sign_index, degrees, sign_name)
    """
    if planet not in DEBILITATION_TABLE:
        raise ValueError(f"No debilitation data for planet {planet}")

    sign_index, degrees = DEBILITATION_TABLE[planet]
    sign_name = SIGN_NAMES[sign_index]

    return sign_index, degrees, sign_name


def get_moolatrikona_range(
    planet: Planet,
) -> Optional[Tuple[int, float, int, float, str, str]]:
    """
    Get Moolatrikona range for a planet.

    Args:
        planet: Planet enum

    Returns:
        Tuple of (start_sign, start_deg, end_sign, end_deg, start_sign_name, end_sign_name)
        or None if planet has no Moolatrikona
    """
    if planet not in MOOLATRIKONA_TABLE:
        return None

    start_sign, start_deg, end_sign, end_deg = MOOLATRIKONA_TABLE[planet]
    start_sign_name = SIGN_NAMES[start_sign]
    end_sign_name = SIGN_NAMES[end_sign]

    return start_sign, start_deg, end_sign, end_deg, start_sign_name, end_sign_name


def get_own_signs(planet: Planet) -> List[Tuple[int, str]]:
    """
    Get signs owned by a planet.

    Args:
        planet: Planet enum

    Returns:
        List of (sign_index, sign_name) tuples
    """
    if planet not in OWN_SIGNS_TABLE:
        return []

    return [(sign_idx, SIGN_NAMES[sign_idx]) for sign_idx in OWN_SIGNS_TABLE[planet]]


def is_in_exaltation(longitude: float, planet: Planet, tolerance: float = 2.0) -> bool:
    """
    Check if a planet is in its exaltation degree (within tolerance).

    Args:
        longitude: Planet's longitude in degrees
        planet: Planet enum
        tolerance: Degree tolerance for exaltation (default 2°)

    Returns:
        True if planet is exalted
    """
    if planet not in EXALTATION_TABLE:
        return False

    exalt_sign, exalt_deg = EXALTATION_TABLE[planet]

    # Calculate the exaltation longitude
    exalt_longitude = exalt_sign * 30 + exalt_deg

    # Check if planet is within tolerance
    diff = abs(longitude - exalt_longitude)
    diff = min(diff, 360 - diff)  # Handle wraparound

    return diff <= tolerance


def is_in_debilitation(
    longitude: float, planet: Planet, tolerance: float = 2.0
) -> bool:
    """
    Check if a planet is in its debilitation degree (within tolerance).

    Args:
        longitude: Planet's longitude in degrees
        planet: Planet enum
        tolerance: Degree tolerance for debilitation (default 2°)

    Returns:
        True if planet is debilitated
    """
    if planet not in DEBILITATION_TABLE:
        return False

    debilitation_sign, debilitation_deg = DEBILITATION_TABLE[planet]

    # Calculate the debilitation longitude
    debilitation_longitude = debilitation_sign * 30 + debilitation_deg

    # Check if planet is within tolerance
    diff = abs(longitude - debilitation_longitude)
    diff = min(diff, 360 - diff)  # Handle wraparound

    return diff <= tolerance


def is_in_moolatrikona(longitude: float, planet: Planet) -> bool:
    """
    Check if a planet is in its Moolatrikona range.

    Args:
        longitude: Planet's longitude in degrees
        planet: Planet enum

    Returns:
        True if planet is in Moolatrikona
    """
    moola_range = get_moolatrikona_range(planet)
    if moola_range is None:
        return False

    start_sign, start_deg, end_sign, end_deg, _, _ = moola_range

    # Convert to longitude ranges
    start_longitude = start_sign * 30 + start_deg
    end_longitude = end_sign * 30 + end_deg

    # Handle wraparound case (if range crosses 0° Aries)
    if start_longitude <= end_longitude:
        return start_longitude <= longitude <= end_longitude
    else:
        # Range wraps around 360°/0°
        return longitude >= start_longitude or longitude <= end_longitude


def is_in_own_sign(longitude: float, planet: Planet) -> bool:
    """
    Check if a planet is in one of its own signs.

    Args:
        longitude: Planet's longitude in degrees
        planet: Planet enum

    Returns:
        True if planet is in own sign
    """
    own_signs = get_own_signs(planet)
    if not own_signs:
        return False

    sign_index = int(longitude / 30) % 12

    return any(sign_index == sign_idx for sign_idx, _ in own_signs)


def get_dignity_type(longitude: float, planet: Planet) -> str:
    """
    Get the dignity type for a planet at a given longitude.

    Args:
        longitude: Planet's longitude in degrees
        planet: Planet enum

    Returns:
        String describing the dignity type
    """
    if is_in_exaltation(longitude, planet):
        return "Exalted"
    elif is_in_moolatrikona(longitude, planet):
        return "Moolatrikona"
    elif is_in_own_sign(longitude, planet):
        return "Own Sign"
    elif is_in_debilitation(longitude, planet):
        return "Debilitated"
    else:
        return "Neutral"
