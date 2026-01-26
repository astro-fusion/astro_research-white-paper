"""
Vedic Astrology Constants

This module defines all the fundamental constants used throughout the
Vedic Numerology-Astrology integration system, including planet definitions,
zodiac signs, and other astrological constants.
"""

from enum import Enum
from typing import Dict, List


# Planet Constants (matching Swiss Ephemeris)
class Planet(Enum):
    """Vedic planets with their Swiss Ephemeris constants."""

    SUN = 0  # Surya
    MOON = 1  # Chandra
    MARS = 4  # Mangal
    MERCURY = 2  # Budha
    JUPITER = 5  # Guru
    VENUS = 3  # Shukra
    SATURN = 6  # Shani
    RAHU = 10  # North Node
    KETU = 11  # South Node (calculated)


# Zodiac Signs
class ZodiacSign(Enum):
    """12 Zodiac signs with their starting longitudes."""

    ARIES = 0  # 0° - 30°
    TAURUS = 30  # 30° - 60°
    GEMINI = 60  # 60° - 90°
    CANCER = 90  # 90° - 120°
    LEO = 120  # 120° - 150°
    VIRGO = 150  # 150° - 180°
    LIBRA = 180  # 180° - 210°
    SCORPIO = 210  # 210° - 240°
    SAGITTARIUS = 240  # 240° - 270°
    CAPRICORN = 270  # 270° - 300°
    AQUARIUS = 300  # 300° - 330°
    PISCES = 330  # 330° - 360°


# Planet Names and Symbols
PLANETS = Planet  # Alias for backward compatibility
SIGNS = ZodiacSign  # Alias for backward compatibility

PLANET_NAMES: Dict[Planet, str] = {
    Planet.SUN: "Sun (Surya)",
    Planet.MOON: "Moon (Chandra)",
    Planet.MARS: "Mars (Mangal)",
    Planet.MERCURY: "Mercury (Budha)",
    Planet.JUPITER: "Jupiter (Guru)",
    Planet.VENUS: "Venus (Shukra)",
    Planet.SATURN: "Saturn (Shani)",
    Planet.RAHU: "Rahu (North Node)",
    Planet.KETU: "Ketu (South Node)",
}

PLANET_SYMBOLS: Dict[Planet, str] = {
    Planet.SUN: "☉",
    Planet.MOON: "☽",
    Planet.MARS: "♂",
    Planet.MERCURY: "☿",
    Planet.JUPITER: "♃",
    Planet.VENUS: "♀",
    Planet.SATURN: "♄",
    Planet.RAHU: "☊",
    Planet.KETU: "☋",
}

# Planet Rulerships (Signs owned by planets)
PLANET_RULERSHIPS: Dict[Planet, List[ZodiacSign]] = {
    Planet.SUN: [ZodiacSign.LEO],
    Planet.MOON: [ZodiacSign.CANCER],
    Planet.MARS: [ZodiacSign.ARIES, ZodiacSign.SCORPIO],
    Planet.MERCURY: [ZodiacSign.GEMINI, ZodiacSign.VIRGO],
    Planet.JUPITER: [ZodiacSign.SAGITTARIUS, ZodiacSign.PISCES],
    Planet.VENUS: [ZodiacSign.TAURUS, ZodiacSign.LIBRA],
    Planet.SATURN: [ZodiacSign.CAPRICORN, ZodiacSign.AQUARIUS],
    # Rahu and Ketu don't traditionally rule signs
}

# Sign Names
SIGN_NAMES: Dict[ZodiacSign, str] = {
    ZodiacSign.ARIES: "Aries",
    ZodiacSign.TAURUS: "Taurus",
    ZodiacSign.GEMINI: "Gemini",
    ZodiacSign.CANCER: "Cancer",
    ZodiacSign.LEO: "Leo",
    ZodiacSign.VIRGO: "Virgo",
    ZodiacSign.LIBRA: "Libra",
    ZodiacSign.SCORPIO: "Scorpio",
    ZodiacSign.SAGITTARIUS: "Sagittarius",
    ZodiacSign.CAPRICORN: "Capricorn",
    ZodiacSign.AQUARIUS: "Aquarius",
    ZodiacSign.PISCES: "Pisces",
}

SIGN_SYMBOLS: Dict[ZodiacSign, str] = {
    ZodiacSign.ARIES: "♈",
    ZodiacSign.TAURUS: "♉",
    ZodiacSign.GEMINI: "♊",
    ZodiacSign.CANCER: "♋",
    ZodiacSign.LEO: "♌",
    ZodiacSign.VIRGO: "♍",
    ZodiacSign.LIBRA: "♎",
    ZodiacSign.SCORPIO: "♏",
    ZodiacSign.SAGITTARIUS: "♐",
    ZodiacSign.CAPRICORN: "♑",
    ZodiacSign.AQUARIUS: "♒",
    ZodiacSign.PISCES: "♓",
}

# House Names
HOUSE_NAMES: Dict[int, str] = {
    1: "Ascendant (Lagna)",
    2: "Wealth (Dhana)",
    3: "Siblings (Sahaja)",
    4: "Home (Bandhu)",
    5: "Children (Putra)",
    6: "Enemies (Ari)",
    7: "Spouse (Kalatra)",
    8: "Longevity (Ayur)",
    9: "Fortune (Bhagya)",
    10: "Career (Karma)",
    11: "Gains (Labha)",
    12: "Spirituality (Vyaya)",
}

# Planet Properties
PLANET_GENDERS: Dict[Planet, str] = {
    Planet.SUN: "Male",
    Planet.MOON: "Female",
    Planet.MARS: "Male",
    Planet.MERCURY: "Neutral",
    Planet.JUPITER: "Male",
    Planet.VENUS: "Female",
    Planet.SATURN: "Neutral",
    Planet.RAHU: "Neutral",
    Planet.KETU: "Neutral",
}

PLANET_ELEMENTS: Dict[Planet, str] = {
    Planet.SUN: "Fire",
    Planet.MOON: "Water",
    Planet.MARS: "Fire",
    Planet.MERCURY: "Earth",
    Planet.JUPITER: "Ether",
    Planet.VENUS: "Water",
    Planet.SATURN: "Air",
    Planet.RAHU: "Air",
    Planet.KETU: "Ether",
}

PLANET_NATURES: Dict[Planet, str] = {
    Planet.SUN: "Hot, Dry",
    Planet.MOON: "Cold, Moist",
    Planet.MARS: "Hot, Dry",
    Planet.MERCURY: "Neutral",
    Planet.JUPITER: "Hot, Moist",
    Planet.VENUS: "Cold, Dry",
    Planet.SATURN: "Cold, Dry",
    Planet.RAHU: "Cold, Dry",
    Planet.KETU: "Hot, Moist",
}

# Dignity Status Descriptions
DIGNITY_DESCRIPTIONS: Dict[str, str] = {
    "exaltation": "Exalted - Maximum strength and positive expression",
    "moolatrikona": "Moolatrikona - Root power, highly favorable",
    "own_sign": "Own Sign - Comfortable, strong influence",
    "friend": "Friend's Sign - Supportive environment",
    "neutral": "Neutral Sign - Balanced, neither helping nor hindering",
    "enemy": "Enemy's Sign - Challenging environment",
    "debilitation": "Debilitated - Weakened, negative expression",
}

# Support Level Categories
SUPPORT_LEVELS: Dict[str, Dict] = {
    "excellent": {
        "range": (75, 100),
        "color": "#28a745",
        "description": "Excellent planetary support",
    },
    "good": {
        "range": (50, 75),
        "color": "#17a2b8",
        "description": "Good planetary support",
    },
    "neutral": {
        "range": (40, 50),
        "color": "#ffc107",
        "description": "Neutral planetary influence",
    },
    "weak": {
        "range": (25, 40),
        "color": "#fd7e14",
        "description": "Weak planetary support",
    },
    "poor": {
        "range": (0, 25),
        "color": "#dc3545",
        "description": "Poor planetary support or contradiction",
    },
}

# Ayanamsa Systems
AYANAMSA_SYSTEMS: Dict[str, str] = {
    "lahiri": "Lahiri (Chitra Paksha) - Standard Vedic",
    "raman": "Krishnamurti Ayanamsa",
    "yukteshwar": "Yukteshwar Ayanamsa",
    "fagan": "Fagan-Bradley Ayanamsa",
    "deluce": "De Luce Ayanamsa",
    "djwhal_khul": "Djwhal Khul Ayanamsa",
}

# House Systems
HOUSE_SYSTEMS: Dict[str, str] = {
    "placidus": "Placidus - Most common in Vedic astrology",
    "koch": "Koch - Alternative Western system",
    "equal": "Equal House - Simple equal division",
    "whole_sign": "Whole Sign - Traditional Vedic approach",
}


# Utility Functions
def get_planet_from_longitude(longitude: float) -> Planet:
    """
    Get planet from longitude (for transit calculations).

    Args:
        longitude: Celestial longitude in degrees

    Returns:
        Planet enum (simplified - would need full ephemeris for accuracy)
    """
    # This is a placeholder - actual implementation would require ephemeris
    # For now, return Sun as default
    return Planet.SUN


def get_sign_from_longitude(longitude: float) -> ZodiacSign:
    """
    Get zodiac sign from longitude.

    Args:
        longitude: Celestial longitude in degrees (0-360)

    Returns:
        ZodiacSign enum
    """
    normalized_long = longitude % 360
    sign_index = int(normalized_long / 30)
    return list(ZodiacSign)[sign_index]


def get_degrees_in_sign(longitude: float) -> float:
    """
    Get degrees within the sign from longitude.

    Args:
        longitude: Celestial longitude in degrees

    Returns:
        Degrees within the sign (0-29.999...)
    """
    return longitude % 30


def longitude_to_sign_position(longitude: float) -> Dict:
    """
    Convert longitude to sign and position information.

    Args:
        longitude: Celestial longitude in degrees

    Returns:
        Dictionary with sign, degrees, and formatted string
    """
    sign = get_sign_from_longitude(longitude)
    degrees = get_degrees_in_sign(longitude)

    return {
        "sign": sign,
        "sign_name": SIGN_NAMES[sign],
        "sign_symbol": SIGN_SYMBOLS[sign],
        "degrees": degrees,
        "formatted": f"{SIGN_NAMES[sign]} {degrees:.2f}°",
    }


def get_support_level(score: float) -> Dict:
    """
    Get support level information from dignity score.

    Args:
        score: Dignity score (0-100)

    Returns:
        Dictionary with level info
    """
    for level, info in SUPPORT_LEVELS.items():
        min_score, max_score = info["range"]
        if min_score <= score < max_score or (
            level == "excellent" and score >= max_score
        ):
            return {
                "level": level,
                "description": info["description"],
                "color": info["color"],
                "range": info["range"],
            }

    # Default to poor
    return SUPPORT_LEVELS["poor"]


# Export all constants for easy importing
__all__ = [
    "Planet",
    "PLANETS",
    "ZodiacSign",
    "SIGNS",
    "PLANET_NAMES",
    "PLANET_SYMBOLS",
    "PLANET_RULERSHIPS",
    "SIGN_NAMES",
    "SIGN_SYMBOLS",
    "HOUSE_NAMES",
    "PLANET_GENDERS",
    "PLANET_ELEMENTS",
    "PLANET_NATURES",
    "DIGNITY_DESCRIPTIONS",
    "SUPPORT_LEVELS",
    "AYANAMSA_SYSTEMS",
    "HOUSE_SYSTEMS",
    "get_planet_from_longitude",
    "get_sign_from_longitude",
    "get_degrees_in_sign",
    "longitude_to_sign_position",
    "get_support_level",
    "NAKSHATRAS",
]

# Nakshatra Constants
NAKSHATRAS: Dict[int, Dict] = {
    0: {"name": "Ashwini", "lord": Planet.KETU, "deity": "Ashwini Kumaras (Health)"},
    1: {"name": "Bharani", "lord": Planet.VENUS, "deity": "Yama (Death)"},
    2: {"name": "Krittika", "lord": Planet.SUN, "deity": "Agni (Fire)"},
    3: {"name": "Rohini", "lord": Planet.MOON, "deity": "Brahma (Creation)"},
    4: {"name": "Mrigashira", "lord": Planet.MARS, "deity": "Soma (Moon)"},
    5: {"name": "Ardra", "lord": Planet.RAHU, "deity": "Rudra (Storm)"},
    6: {"name": "Punarvasu", "lord": Planet.JUPITER, "deity": "Aditi (Boundless)"},
    7: {"name": "Pushya", "lord": Planet.SATURN, "deity": "Brihaspati (Wisdom)"},
    8: {"name": "Ashlesha", "lord": Planet.MERCURY, "deity": "Nagas (Serpents)"},
    9: {"name": "Magha", "lord": Planet.KETU, "deity": "Pitris (Ancestors)"},
    10: {"name": "Purva Phalguni", "lord": Planet.VENUS, "deity": "Bhaga (Prosperity)"},
    11: {"name": "Uttara Phalguni", "lord": Planet.SUN, "deity": "Aryaman (Patronage)"},
    12: {"name": "Hasta", "lord": Planet.MOON, "deity": "Savitr (Sun)"},
    13: {"name": "Chitra", "lord": Planet.MARS, "deity": "Vishvakarma (Architect)"},
    14: {"name": "Swati", "lord": Planet.RAHU, "deity": "Vayu (Wind)"},
    15: {"name": "Vishakha", "lord": Planet.JUPITER, "deity": "Indra-Agni"},
    16: {"name": "Anuradha", "lord": Planet.SATURN, "deity": "Mitra (Friendship)"},
    17: {"name": "Jyeshtha", "lord": Planet.MERCURY, "deity": "Indra (Chief)"},
    18: {"name": "Mula", "lord": Planet.KETU, "deity": "Nirriti (Destruction)"},
    19: {"name": "Purva Ashadha", "lord": Planet.VENUS, "deity": "Apah (Water)"},
    20: {
        "name": "Uttara Ashadha",
        "lord": Planet.SUN,
        "deity": "Vishvedevas (Universal)",
    },
    21: {"name": "Shravana", "lord": Planet.MOON, "deity": "Vishnu (Preserver)"},
    22: {"name": "Dhanishta", "lord": Planet.MARS, "deity": "Ashta Vasus"},
    23: {"name": "Shatabhisha", "lord": Planet.RAHU, "deity": "Varuna (Cosmic Order)"},
    24: {"name": "Purva Bhadrapada", "lord": Planet.JUPITER, "deity": "Aja Ekapada"},
    25: {"name": "Uttara Bhadrapada", "lord": Planet.SATURN, "deity": "Ahir Budhnya"},
    26: {"name": "Revati", "lord": Planet.MERCURY, "deity": "Pushan (Nourisher)"},
}
