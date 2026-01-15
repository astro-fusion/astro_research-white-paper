"""
Ayanamsa Calculations for Vedic Astrology

Handles the precession of the equinoxes (Ayanamsa) calculations required
for converting Tropical (Western) zodiac to Sidereal (Vedic) zodiac.

The Lahiri Ayanamsa (Chitra Paksha) is the standard for Vedic astrology
and Government of India astronomical calculations.
"""

from enum import Enum
from typing import Any, Dict, Optional, Union, cast


# Ayanamsa system constants
class AyanamsaSystem(Enum):
    """Available Ayanamsa systems for Vedic astrology."""

    LAHIRI = "lahiri"  # Chitra Paksha - Standard for Vedic astrology
    RAMAN = "raman"  # Krishnamurti Ayanamsa
    KRISHNAMURTI = "krishnamurti"  # Same as Raman
    YUKTESHWAR = "yukteshwar"  # Yukteshwar Ayanamsa
    FAGAN = "fagan"  # Fagan-Bradley Ayanamsa
    DELUCE = "deluce"  # De Luce Ayanamsa
    DJWHAL_KHUL = "djwhal_khul"  # Djwhal Khul Ayanamsa


# Ayanamsa values for different systems (in degrees)
# These are reference values that would need to be calculated precisely
AYANAMSA_OFFSETS: Dict[AyanamsaSystem, float] = {
    AyanamsaSystem.LAHIRI: 24.0,  # Current Lahiri Ayanamsa (approximate)
    AyanamsaSystem.RAMAN: 22.5,  # Krishnamurti Ayanamsa
    AyanamsaSystem.KRISHNAMURTI: 22.5,  # Same as Raman
    AyanamsaSystem.YUKTESHWAR: 22.0,  # Yukteshwar Ayanamsa
    AyanamsaSystem.FAGAN: 24.1,  # Fagan-Bradley Ayanamsa
    AyanamsaSystem.DELUCE: 25.2,  # De Luce Ayanamsa
    AyanamsaSystem.DJWHAL_KHUL: 23.8,  # Djwhal Khul Ayanamsa
}


def calculate_lahiri_ayanamsa(julian_day: float) -> float:
    """
    Calculate the precise Lahiri Ayanamsa for a given Julian Day.

    The Lahiri Ayanamsa is calculated using the formula:
    Ayanamsa = 23° 26' 13.5" + (current_year - 285) * 50.2388475" per year

    This is the standard Ayanamsa used by the Government of India and
    most Vedic astrologers.

    Args:
        julian_day: Julian day number

    Returns:
        Ayanamsa in degrees
    """
    # Convert Julian Day to Gregorian year
    # This is an approximation; precise calculation would use astronomical algorithms
    gregorian_year = 2000 + (julian_day - 2451545.0) / 365.25

    # Lahiri Ayanamsa formula (simplified)
    # Base value for J2000: 23° 26' 13.5" = 23.437083 degrees
    base_ayanamsa = 23.437083

    # Annual precession rate: 50.2388475 arcseconds per year
    # Convert to degrees: 50.2388475 / 3600 = 0.013955235 degrees per year
    annual_rate = 0.013955235

    # Calculate years since J2000
    years_since_2000 = gregorian_year - 2000

    # Calculate Ayanamsa
    ayanamsa = base_ayanamsa + (years_since_2000 * annual_rate)

    return ayanamsa


def get_ayanamsa_offset(
    julian_day: float, system: Union[str, AyanamsaSystem] = AyanamsaSystem.LAHIRI
) -> float:
    """
    Get the Ayanamsa offset for converting Tropical to Sidereal positions.

    Args:
        julian_day: Julian day number for the calculation
        system: Ayanamsa system to use (default: Lahiri)

    Returns:
        Ayanamsa offset in degrees

    Raises:
        ValueError: If system is not recognized
    """
    if isinstance(system, str):
        try:
            system = AyanamsaSystem(system.lower())
        except ValueError:
            valid_systems = [s.value for s in AyanamsaSystem]
            raise ValueError(
                f"Unknown Ayanamsa system '{system}'. Valid systems: {valid_systems}"
            )

    if system == AyanamsaSystem.LAHIRI:
        # Use precise calculation for Lahiri
        return calculate_lahiri_ayanamsa(julian_day)
    else:
        # Use pre-calculated offsets for other systems
        # Note: These are approximations and should be updated periodically
        return AYANAMSA_OFFSETS[system]


def convert_tropical_to_sidereal(longitude: float, ayanamsa: float) -> float:
    """
    Convert Tropical (Western) longitude to Sidereal (Vedic) longitude.

    Args:
        longitude: Tropical longitude in degrees (0-360)
        ayanamsa: Ayanamsa value in degrees

    Returns:
        Sidereal longitude in degrees (0-360)
    """
    sidereal_longitude = longitude - ayanamsa

    # Normalize to 0-360 range
    while sidereal_longitude < 0:
        sidereal_longitude += 360
    while sidereal_longitude >= 360:
        sidereal_longitude -= 360

    return sidereal_longitude


def convert_sidereal_to_tropical(longitude: float, ayanamsa: float) -> float:
    """
    Convert Sidereal (Vedic) longitude to Tropical (Western) longitude.

    Args:
        longitude: Sidereal longitude in degrees (0-360)
        ayanamsa: Ayanamsa value in degrees

    Returns:
        Tropical longitude in degrees (0-360)
    """
    tropical_longitude = longitude + ayanamsa

    # Normalize to 0-360 range
    while tropical_longitude < 0:
        tropical_longitude += 360
    while tropical_longitude >= 360:
        tropical_longitude -= 360

    return tropical_longitude


def get_zodiac_sign(longitude: float) -> tuple:
    """
    Get the zodiac sign and degree within sign for a given longitude.

    Args:
        longitude: Celestial longitude in degrees (0-360)

    Returns:
        Tuple of (sign_index, sign_name, degrees_in_sign)
        sign_index: 0-11 (Aries=0, Taurus=1, etc.)
        sign_name: String name of the sign
        degrees_in_sign: Degrees within the sign (0-29.999...)
    """
    # Normalize longitude to 0-360
    longitude = longitude % 360

    # Calculate sign index (0-11)
    sign_index = int(longitude / 30)

    # Calculate degrees within sign
    degrees_in_sign = longitude % 30

    # Sign names
    sign_names = [
        "Aries",
        "Taurus",
        "Gemini",
        "Cancer",
        "Leo",
        "Virgo",
        "Libra",
        "Scorpio",
        "Sagittarius",
        "Capricorn",
        "Aquarius",
        "Pisces",
    ]

    sign_name = sign_names[sign_index]

    return sign_index, sign_name, degrees_in_sign


def get_ayanamsa_info(
    julian_day: float, system: Union[str, AyanamsaSystem] = AyanamsaSystem.LAHIRI
) -> dict:
    """
    Get comprehensive Ayanamsa information for a given time.

    Args:
        julian_day: Julian day number
        system: Ayanamsa system to use

    Returns:
        Dictionary with Ayanamsa information:
        - 'system': Ayanamsa system used
        - 'ayanamsa': Ayanamsa value in degrees
        - 'description': Description of the system
    """
    if isinstance(system, str):
        try:
            system = AyanamsaSystem(system.lower())
        except ValueError:
            pass

    ayanamsa = get_ayanamsa_offset(julian_day, system)

    system_descriptions = {
        AyanamsaSystem.LAHIRI: (
            "Chitra Paksha - Standard Vedic astrology (Government of India)"
        ),
        AyanamsaSystem.RAMAN: "Krishnamurti Ayanamsa - Named after Sanjay Rath",
        AyanamsaSystem.KRISHNAMURTI: "Krishnamurti Ayanamsa - Same as Raman",
        AyanamsaSystem.YUKTESHWAR: (
            "Yukteshwar Ayanamsa - From Paramahansa Yogananda's guru"
        ),
        AyanamsaSystem.FAGAN: (
            "Fagan-Bradley Ayanamsa - Popular in some Western sidereal systems"
        ),
        AyanamsaSystem.DELUCE: "De Luce Ayanamsa - Alternative calculation method",
        AyanamsaSystem.DJWHAL_KHUL: "Djwhal Khul Ayanamsa - Esoteric tradition",
    }

    return {
        "system": system.value if isinstance(system, AyanamsaSystem) else system,
        "ayanamsa": ayanamsa,
        "description": system_descriptions.get(
            cast(Any, system), "Unknown Ayanamsa system"
        ),
    }


# Constants for pyswisseph integration
try:
    import swisseph as swe

    SWISSEPH_AVAILABLE = True

    # pyswisseph Ayanamsa constants
    PYSWISSEPH_AYANAMSA_MAP: Dict[AyanamsaSystem, int] = {
        AyanamsaSystem.LAHIRI: swe.SIDM_LAHIRI,
        AyanamsaSystem.RAMAN: swe.SIDM_KRISHNAMURTI,  # Close approximation
        AyanamsaSystem.KRISHNAMURTI: swe.SIDM_KRISHNAMURTI,
        AyanamsaSystem.YUKTESHWAR: swe.SIDM_YUKTESHWAR,
        AyanamsaSystem.FAGAN: swe.SIDM_FAGAN_BRADLEY,
        AyanamsaSystem.DELUCE: swe.SIDM_DELUCE,
        AyanamsaSystem.DJWHAL_KHUL: swe.SIDM_DJWHAL_KHUL,
    }

except ImportError:
    SWISSEPH_AVAILABLE = False
    PYSWISSEPH_AYANAMSA_MAP: Dict[AyanamsaSystem, int] = {}  # type: ignore[no-redef]


def get_pyswisseph_ayanamsa_constant(system: AyanamsaSystem) -> Optional[int]:
    """
    Get the pyswisseph constant for an Ayanamsa system.

    Args:
        system: Ayanamsa system

    Returns:
        pyswisseph constant, or None if not available
    """
    if not SWISSEPH_AVAILABLE:
        return None

    return PYSWISSEPH_AYANAMSA_MAP.get(system)


# Export for external use
__all__ = [
    "AyanamsaSystem",
    "AYANAMSA_OFFSETS",
    "get_ayanamsa_offset",
    "convert_tropical_to_sidereal",
    "convert_sidereal_to_tropical",
    "get_zodiac_sign",
    "get_ayanamsa_info",
    "get_pyswisseph_ayanamsa_constant",
]
