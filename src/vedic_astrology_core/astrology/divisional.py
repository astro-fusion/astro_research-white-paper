"""
Divisional Chart Calculations (Vargas)

Handles calculation of divisional charts used in Vedic astrology to refine
planetary strength and specific life areas.
"""

from typing import Dict, Tuple

from ..config.constants import SIGNS


def get_navamsa_sign(longitude: float) -> Tuple[int, str]:
    """
    Calculate the Navamsa (D9) sign for a given longitude.

    The Navamsa divides each sign (30°) into 9 parts of 3°20' each.
    The mapping depends on the element of the Rasi (D1) sign:
    - Fire Signs (Aries, Leo, Sag): Start from Aries
    - Earth Signs (Taurus, Virgo, Cap): Start from Capricorn
    - Air Signs (Gemini, Libra, Aqua): Start from Libra
    - Water Signs (Cancer, Scorpio, Pisces): Start from Cancer

    Args:
        longitude: Celestial longitude in degrees (0-360)

    Returns:
        Tuple of (sign_index, sign_name) for the Navamsa position
    """
    # Normalize longitude
    lon = longitude % 360

    # Determine Rasi (D1) sign index (0-11)
    d1_sign_index = int(lon / 30)

    # Determine which "pada" (ninth) of the sign the planet is in (0-8)
    degrees_in_sign = lon % 30
    pada_index = int(degrees_in_sign / (30 / 9))

    # Determine starting sign based on Element of D1 sign
    # Fire: 0 (Aries), 4 (Leo), 8 (Sag) -> Starts at 0 (Aries)
    # Earth: 1 (Taurus), 5 (Virgo), 9 (Cap) -> Starts at 9 (Capricorn)
    # Air: 2 (Gemini), 6 (Libra), 10 (Aqua) -> Starts at 6 (Libra)
    # Water: 3 (Cancer), 7 (Scorpio), 11 (Pisces) -> Starts at 3 (Cancer)

    remainder = d1_sign_index % 4
    if remainder == 0:  # Fire
        start_index = 0
    elif remainder == 1:  # Earth
        start_index = 9
    elif remainder == 2:  # Air
        start_index = 6
    else:  # Water
        start_index = 3

    # Calculate Navamsa sign index
    d9_sign_index = (start_index + pada_index) % 12

    return d9_sign_index, SIGNS[d9_sign_index]


def calculate_d9(longitude: float) -> Dict:
    """
    Calculate full D9 (Navamsa) details.

    Args:
        longitude: Celestial longitude in degrees (0-360)

    Returns:
        Dictionary containing D9 sign index, name, and Vargottama status check helper.
    """
    d9_index, d9_name = get_navamsa_sign(longitude)
    d1_index = int((longitude % 360) / 30)

    return {
        "index": d9_index,
        "sign_name": d9_name,
        "is_vargottama": d9_index == d1_index,
    }
