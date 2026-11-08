"""
Exaltation and Debilitation Matrices.

Contains the classical Vedic astrology exaltation and debilitation positions
for all planets, along with Moolatrikona ranges and sign rulership data.
"""

from enum import Enum
from typing import Dict, List, Optional, Tuple

from ..config.constants import Planet


# Zodiac signs
class ZodiacSign(Enum):
    """Docstring."""

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
# Deep-exaltation degrees: BPHS 3.49-50 (Santhanam 1984), "The deepest
# exaltation degrees are respectively 10, 3, 28, 15, 5, 27 and 20" in Aries,
# Taurus, Capricorn, Virgo, Cancer, Pisces and Libra. Deep fall is the same
# degree in the seventh sign.
EXALTATION_TABLE: Dict[Planet, Tuple[int, float]] = {
    Planet.SUN: (ZodiacSign.ARIES.value, 10.0),  # Aries 10°, BPHS 3.49-50
    Planet.MOON: (ZodiacSign.TAURUS.value, 3.0),  # Taurus 3°, BPHS 3.49-50
    Planet.MARS: (ZodiacSign.CAPRICORN.value, 28.0),  # Capricorn 28°, BPHS 3.49-50
    Planet.MERCURY: (ZodiacSign.VIRGO.value, 15.0),  # Virgo 15°, BPHS 3.49-50
    Planet.JUPITER: (ZodiacSign.CANCER.value, 5.0),  # Cancer 5°, BPHS 3.49-50
    Planet.VENUS: (ZodiacSign.PISCES.value, 27.0),  # Pisces 27°, BPHS 3.49-50
    Planet.SATURN: (ZodiacSign.LIBRA.value, 20.0),  # Libra 20°, BPHS 3.49-50
    # Rahu and Ketu: Special handling (Taurus/Scorpio convention)
    Planet.RAHU: (ZodiacSign.TAURUS.value, 0.0),  # Taurus (variable)
    Planet.KETU: (ZodiacSign.SCORPIO.value, 0.0),  # Scorpio (variable)
}

DEBILITATION_TABLE: Dict[Planet, Tuple[int, float]] = {
    Planet.SUN: (ZodiacSign.LIBRA.value, 10.0),  # Libra 10°, BPHS 3.49-50
    Planet.MOON: (ZodiacSign.SCORPIO.value, 3.0),  # Scorpio 3°, BPHS 3.49-50
    Planet.MARS: (ZodiacSign.CANCER.value, 28.0),  # Cancer 28°, BPHS 3.49-50
    Planet.MERCURY: (ZodiacSign.PISCES.value, 15.0),  # Pisces 15°, BPHS 3.49-50
    Planet.JUPITER: (ZodiacSign.CAPRICORN.value, 5.0),  # Capricorn 5°, BPHS 3.49-50
    Planet.VENUS: (ZodiacSign.VIRGO.value, 27.0),  # Virgo 27°, BPHS 3.49-50
    Planet.SATURN: (ZodiacSign.ARIES.value, 20.0),  # Aries 20°, BPHS 3.49-50
    # Rahu and Ketu: Opposite signs to exaltation
    Planet.RAHU: (ZodiacSign.SCORPIO.value, 0.0),  # Scorpio (variable)
    Planet.KETU: (ZodiacSign.TAURUS.value, 0.0),  # Taurus (variable)
}

# Moolatrikona ranges: (start_sign, start_degrees, end_sign, end_degrees),
# half-open [start, end): "the first 20 degrees" ends before 20.
# Source: BPHS 3.51-54 (Santhanam 1984). Corrected 2026-11-09, see
# CORRECTIONS.md (Mars was 0-18, Jupiter 0-13, Venus 0-10, Moon 4-30,
# Mercury 16-20, and the end degree was included).
MOOLATRIKONA_TABLE: Dict[Planet, Tuple[int, float, int, float]] = {
    # Leo 0-20°: "In Leo, the first 20 degrees are the Sun's Moola-Trikona",
    # BPHS 3.51-54 (Santhanam 1984)
    Planet.SUN: (ZodiacSign.LEO.value, 0.0, ZodiacSign.LEO.value, 20.0),
    # Taurus 3-30°: "After the first 3 degrees of exaltation portion in
    # Taurus", BPHS 3.51-54 (Santhanam 1984)
    Planet.MOON: (ZodiacSign.TAURUS.value, 3.0, ZodiacSign.TAURUS.value, 30.0),
    # Aries 0-12°: "Mars has the first 12 degrees in Aries", BPHS 3.51-54
    # (Santhanam 1984)
    Planet.MARS: (ZodiacSign.ARIES.value, 0.0, ZodiacSign.ARIES.value, 12.0),
    # Virgo 15-20°: "the first 15 degrees are exaltation zone, the next 5
    # degrees Moola-Trikona", BPHS 3.51-54 (Santhanam 1984)
    Planet.MERCURY: (ZodiacSign.VIRGO.value, 15.0, ZodiacSign.VIRGO.value, 20.0),
    # Sagittarius 0-10°: "The first one third of Sagittarius", BPHS 3.51-54
    # (Santhanam 1984)
    Planet.JUPITER: (
        ZodiacSign.SAGITTARIUS.value,
        0.0,
        ZodiacSign.SAGITTARIUS.value,
        10.0,
    ),
    # Libra 0-15°: "Venus divides Libra into two halves keeping the first as
    # Moola-Trikona", BPHS 3.51-54 (Santhanam 1984)
    Planet.VENUS: (ZodiacSign.LIBRA.value, 0.0, ZodiacSign.LIBRA.value, 15.0),
    # Aquarius 0-20°: "Saturn's arrangements are same in Aquarius as the Sun
    # has in Leo", BPHS 3.51-54 (Santhanam 1984)
    Planet.SATURN: (ZodiacSign.AQUARIUS.value, 0.0, ZodiacSign.AQUARIUS.value, 20.0),
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
        Tuple of (start_sign, start_deg, end_sign, end_deg, start_sign_name,
        end_sign_name) or None if planet has no Moolatrikona
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


RAHU_EXALTATION_TRADITIONS = ("taurus", "gemini")
DEFAULT_RAHU_EXALTED_IN = "taurus"


def _validate_tradition(rahu_exalted_in: str) -> str:
    tradition = str(rahu_exalted_in).lower()
    if tradition not in RAHU_EXALTATION_TRADITIONS:
        raise ValueError(
            f"rahu_exalted_in must be one of {RAHU_EXALTATION_TRADITIONS}, "
            f"got {rahu_exalted_in!r}"
        )
    return tradition


def exaltation_sign_index(
    planet: Planet, rahu_exalted_in: str = DEFAULT_RAHU_EXALTED_IN
) -> Optional[int]:
    """Return the exaltation (uccha) sign of a planet, or None.

    The nodes have no exaltation in BPHS proper; two traditions exist and
    the choice is an explicit parameter: ``"taurus"`` (Rahu exalted in
    Taurus, Ketu in Scorpio) or ``"gemini"`` (Rahu in Gemini, Ketu in
    Sagittarius).
    """
    if planet in (Planet.RAHU, Planet.KETU):
        tradition = _validate_tradition(rahu_exalted_in)
        rahu = (
            ZodiacSign.TAURUS.value
            if tradition == "taurus"
            else (ZodiacSign.GEMINI.value)
        )
        return rahu if planet == Planet.RAHU else (rahu + 6) % 12
    if planet not in EXALTATION_TABLE:
        return None
    return EXALTATION_TABLE[planet][0]


def debilitation_sign_index(
    planet: Planet, rahu_exalted_in: str = DEFAULT_RAHU_EXALTED_IN
) -> Optional[int]:
    """Return the debilitation (neecha) sign: the 7th from exaltation."""
    exalt = exaltation_sign_index(planet, rahu_exalted_in)
    return None if exalt is None else (exalt + 6) % 12


def is_in_exaltation(
    longitude: float, planet: Planet, rahu_exalted_in: str = DEFAULT_RAHU_EXALTED_IN
) -> bool:
    """
    Return True if the planet is in its exaltation sign (whole sign).

    Classical uccha is the whole sign; the deep-exaltation degree
    (paramoccha) only grades the strength, see :func:`uccha_bala`.
    """
    exalt = exaltation_sign_index(planet, rahu_exalted_in)
    return exalt is not None and int((longitude % 360) // 30) == exalt


def is_in_debilitation(
    longitude: float, planet: Planet, rahu_exalted_in: str = DEFAULT_RAHU_EXALTED_IN
) -> bool:
    """Return True if the planet is in its debilitation sign (whole sign)."""
    debil = debilitation_sign_index(planet, rahu_exalted_in)
    return debil is not None and int((longitude % 360) // 30) == debil


def uccha_bala(planet: Planet, longitude: float) -> float:
    """
    Uccha bala (exaltation strength) in virupas, 0 to 60 (BPHS Ch. 27).

    It is the arc from the planet's deep-debilitation point, folded to at
    most 180 degrees, divided by 3: 60 at the paramoccha degree, 0 at the
    deepest debilitation. Defined for the Sun to Saturn only.

    Raises:
        ValueError: For Rahu and Ketu.
    """
    if planet not in DEBILITATION_TABLE or planet in (Planet.RAHU, Planet.KETU):
        raise ValueError(f"Uccha bala is not defined for {planet.name}")
    sign, deg = DEBILITATION_TABLE[planet]
    arc = abs((longitude % 360.0) - (sign * 30.0 + deg)) % 360.0
    if arc > 180.0:
        arc = 360.0 - arc
    return arc / 3.0


def is_in_moolatrikona(longitude: float, planet: Planet) -> bool:
    """
    Check if a planet is in its Moolatrikona range (BPHS 3.51-54).

    The range is half-open: the end degree belongs to the next part of the
    sign (own sign, or the next sign for the Moon's Taurus 3-30).

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

    # Half-open [start, end): BPHS 3.51-54 counts "the first 20 degrees".
    # Handle wraparound case (if range crosses 0° Aries)
    if start_longitude <= end_longitude:
        return start_longitude <= longitude < end_longitude
    else:
        # Range wraps around 360°/0°
        return longitude >= start_longitude or longitude < end_longitude


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


def get_dignity_type(
    longitude: float, planet: Planet, rahu_exalted_in: str = DEFAULT_RAHU_EXALTED_IN
) -> str:
    """
    Return the dignity of a planet at a longitude.

    Exaltation and debilitation are by whole sign. Where BPHS places a
    moolatrikona range inside the exaltation sign (the Moon in Taurus,
    Mercury in Virgo), that range is reported as Moolatrikona.
    """
    if is_in_moolatrikona(longitude, planet):
        return "Moolatrikona"
    if is_in_exaltation(longitude, planet, rahu_exalted_in):
        return "Exalted"
    if is_in_debilitation(longitude, planet, rahu_exalted_in):
        return "Debilitated"
    if is_in_own_sign(longitude, planet):
        return "Own Sign"
    return "Neutral"
