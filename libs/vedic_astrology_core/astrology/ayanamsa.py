"""
Ayanamsa (precession offset) for Vedic astrology.

The ayanamsa converts tropical longitudes to sidereal (nirayana) longitudes.
The only source of ayanamsa values in this library is the Swiss Ephemeris,
``swe.get_ayanamsa_ut`` with the sidereal mode selected below. There is no
hand-written fallback formula: an earlier fallback used the obliquity of the
ecliptic (23.437 deg) as the "Lahiri J2000 base", which is 0.42 deg wrong
(Lahiri at J2000 is about 23.857 deg), and gave other systems fixed values
with no precession at all. pyswisseph is therefore a hard dependency.

The Lahiri (Chitra Paksha) ayanamsa is the standard of the Indian
Astronomical Ephemeris (Calendar Reform Committee, 1955).
"""

from enum import Enum
from typing import Dict, Union

import swisseph as swe


class AyanamsaSystem(Enum):
    """Available Ayanamsa systems for Vedic astrology."""

    LAHIRI = "lahiri"  # Chitra Paksha - Indian national standard
    RAMAN = "raman"  # B.V. Raman
    KRISHNAMURTI = "krishnamurti"  # K.S. Krishnamurti (KP)
    YUKTESHWAR = "yukteshwar"  # Sri Yukteshwar
    FAGAN = "fagan"  # Fagan-Bradley (Western sidereal)
    DELUCE = "deluce"  # De Luce
    DJWHAL_KHUL = "djwhal_khul"  # Djwhal Khul


# Swiss Ephemeris sidereal-mode constants for each system.
PYSWISSEPH_AYANAMSA_MAP: Dict[AyanamsaSystem, int] = {
    AyanamsaSystem.LAHIRI: swe.SIDM_LAHIRI,
    AyanamsaSystem.RAMAN: swe.SIDM_RAMAN,
    AyanamsaSystem.KRISHNAMURTI: swe.SIDM_KRISHNAMURTI,
    AyanamsaSystem.YUKTESHWAR: swe.SIDM_YUKTESHWAR,
    AyanamsaSystem.FAGAN: swe.SIDM_FAGAN_BRADLEY,
    AyanamsaSystem.DELUCE: swe.SIDM_DELUCE,
    AyanamsaSystem.DJWHAL_KHUL: swe.SIDM_DJWHAL_KHUL,
}

SYSTEM_DESCRIPTIONS: Dict[AyanamsaSystem, str] = {
    AyanamsaSystem.LAHIRI: (
        "Lahiri (Chitra Paksha) - Indian Astronomical Ephemeris standard"
    ),
    AyanamsaSystem.RAMAN: "Raman Ayanamsa - after B.V. Raman",
    AyanamsaSystem.KRISHNAMURTI: (
        "Krishnamurti Ayanamsa - K.S. Krishnamurti Paddhati (KP)"
    ),
    AyanamsaSystem.YUKTESHWAR: "Yukteshwar Ayanamsa - after Sri Yukteshwar",
    AyanamsaSystem.FAGAN: "Fagan-Bradley Ayanamsa - Western sidereal astrology",
    AyanamsaSystem.DELUCE: "De Luce Ayanamsa",
    AyanamsaSystem.DJWHAL_KHUL: "Djwhal Khul Ayanamsa",
}


def resolve_ayanamsa_system(system: Union[str, AyanamsaSystem]) -> AyanamsaSystem:
    """Return the AyanamsaSystem for an enum member or a case-insensitive name.

    Raises:
        ValueError: If the name is not a known system.
    """
    if isinstance(system, AyanamsaSystem):
        return system
    try:
        return AyanamsaSystem(str(system).lower())
    except ValueError:
        valid_systems = [s.value for s in AyanamsaSystem]
        raise ValueError(
            f"Unknown Ayanamsa system '{system}'. Valid systems: {valid_systems}"
        ) from None


def set_sidereal_mode(system: Union[str, AyanamsaSystem]) -> int:
    """Select the Swiss Ephemeris sidereal mode for ``system``.

    Swiss Ephemeris keeps the sidereal mode as global state, so every
    calculation in this library calls this immediately before computing.

    Returns:
        The ``swe.SIDM_*`` constant that was set.
    """
    sid_mode = PYSWISSEPH_AYANAMSA_MAP[resolve_ayanamsa_system(system)]
    swe.set_sid_mode(sid_mode, 0.0, 0.0)
    return sid_mode


def get_ayanamsa_offset(
    julian_day: float, system: Union[str, AyanamsaSystem] = AyanamsaSystem.LAHIRI
) -> float:
    """
    Return the mean ayanamsa in degrees from ``swe.get_ayanamsa_ut``.

    This is the mean value (no nutation). Sidereal positions from
    :class:`~.ephemeris.EphemerisEngine` subtract the true value; use
    :func:`ayanamsa_true` (or ``EphemerisEngine.get_ayanamsa``) to convert
    between them.

    Args:
        julian_day: Julian day number (UT)
        system: Ayanamsa system to use (default: Lahiri)

    Raises:
        ValueError: If system is not recognized
    """
    set_sidereal_mode(system)
    return float(swe.get_ayanamsa_ut(julian_day))


def ayanamsa_mean(
    julian_day: float, system: Union[str, AyanamsaSystem] = AyanamsaSystem.LAHIRI
) -> float:
    """Return the mean ayanamsa (no nutation), ``swe.get_ayanamsa_ut``."""
    set_sidereal_mode(system)
    return float(swe.get_ayanamsa_ut(julian_day))


def ayanamsa_true(
    julian_day: float, system: Union[str, AyanamsaSystem] = AyanamsaSystem.LAHIRI
) -> float:
    """Return the true ayanamsa: the mean value plus the nutation in longitude.

    This is the value Swiss Ephemeris subtracts from the apparent tropical
    longitude of date when ``FLG_SIDEREAL`` is set, so sidereal longitude
    plus the true ayanamsa is the apparent tropical longitude exactly
    (``swe.get_ayanamsa_ex_ut`` without ``FLG_NONUT``). The two differ by
    the nutation in longitude, at most about 17.2 arcseconds (-13.9 at
    J2000).
    """
    set_sidereal_mode(system)
    _flag, value = swe.get_ayanamsa_ex_ut(julian_day, swe.FLG_SWIEPH)
    return float(value)


def convert_tropical_to_sidereal(longitude: float, ayanamsa: float) -> float:
    """Convert a tropical longitude to sidereal, normalised to [0, 360)."""
    return (longitude - ayanamsa) % 360.0


def convert_sidereal_to_tropical(longitude: float, ayanamsa: float) -> float:
    """Convert a sidereal longitude to tropical, normalised to [0, 360)."""
    return (longitude + ayanamsa) % 360.0


SIGN_NAMES_LIST = [
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


def get_zodiac_sign(longitude: float) -> tuple:
    """
    Get the zodiac sign and degree within sign for a given longitude.

    Returns:
        Tuple of (sign_index 0-11, sign_name, degrees_in_sign)
    """
    longitude = longitude % 360
    sign_index = int(longitude // 30) % 12
    return sign_index, SIGN_NAMES_LIST[sign_index], longitude - sign_index * 30


def get_ayanamsa_info(
    julian_day: float, system: Union[str, AyanamsaSystem] = AyanamsaSystem.LAHIRI
) -> dict:
    """
    Get the ayanamsa value and a description of the system.

    Returns:
        Dictionary with 'system', 'ayanamsa' (degrees) and 'description'.
    """
    resolved = resolve_ayanamsa_system(system)
    return {
        "system": resolved.value,
        "ayanamsa": get_ayanamsa_offset(julian_day, resolved),
        "description": SYSTEM_DESCRIPTIONS[resolved],
    }


def get_pyswisseph_ayanamsa_constant(system: AyanamsaSystem) -> int:
    """Return the ``swe.SIDM_*`` constant for an Ayanamsa system."""
    return PYSWISSEPH_AYANAMSA_MAP[resolve_ayanamsa_system(system)]


__all__ = [
    "AyanamsaSystem",
    "PYSWISSEPH_AYANAMSA_MAP",
    "resolve_ayanamsa_system",
    "set_sidereal_mode",
    "get_ayanamsa_offset",
    "ayanamsa_mean",
    "ayanamsa_true",
    "convert_tropical_to_sidereal",
    "convert_sidereal_to_tropical",
    "get_zodiac_sign",
    "get_ayanamsa_info",
    "get_pyswisseph_ayanamsa_constant",
]
