"""src/celestial/divisional_charts.py.

Shodashavarga (Divisional Charts) Engine
========================================
Implements the 16 divisional charts (Vargas) of Vedic Astrology
as defined in the Bṛhat Parāśara Horāśāstra.

Mathematical model: papers/astrology/07_divisional_charts_shodashavarga (pending)
Symbol reference:   SYMBOLOGY.md §II.H
"""

from __future__ import annotations

import math
from typing import NamedTuple


class VargaResult(NamedTuple):
    """Result of a divisional chart calculation."""

    varga_name: str
    varga_number: int  # e.g., 9 for D-9
    sign_index: int  # 0-11
    sign_name: str
    degree_in_varga: float


# Vedic Signs Mapping
SIGNS: list[str] = [
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


def compute_varga(lambda_deg: float, d: int, name: str) -> VargaResult:
    """
    Provide generic algorithm for divisional charts starting sign counting.

    Signs follow the sequence of (Sign_Index * D) % 12 for the start sign.
    """
    total_longitude = lambda_deg % 360.0
    degree_in_sign = total_longitude % 30.0

    # Number of divisions in the sign
    # e.g., for D-9, each division is 30/9 = 3.333 degrees
    division_width = 30.0 / d

    # Sign of the divisional chart
    # Generalised Parasharic Rule: Total_Varga_Index % 12
    # For D-1, D-9, D-60 this holds for the 'sign counting' logic.
    varga_sign_index = int(math.floor(total_longitude / division_width)) % 12

    return VargaResult(
        varga_name=name,
        varga_number=d,
        sign_index=varga_sign_index,
        sign_name=SIGNS[varga_sign_index],
        degree_in_varga=(degree_in_sign % division_width) * d,
    )


def compute_navamsa(lambda_deg: float) -> VargaResult:
    """
    Compute Navamsa (D-9) — The most critical divisional chart.

    Formula: floor(λ * 9 / 30) % 12
    Equates to the 9th part of a sign.
    """
    return compute_varga(lambda_deg, 9, "Navamsa")


def compute_shastiamsa(lambda_deg: float) -> VargaResult:
    """
    Compute Shastiamsa (D-60) — Precision divisional chart.

    Formula: floor(λ * 60 / 30) % 12 = floor(λ * 2) % 12
    Used for granular differentiation.
    """
    return compute_varga(lambda_deg, 60, "Shastiamsa")


def compute_dashamsa(lambda_deg: float) -> VargaResult:
    """Compute Dashamsa (D-10) — Professional successes."""
    # Dashamsa rule: Odd signs start from the sign, even signs from the 9th.
    total_longitude = lambda_deg % 360.0
    sign_index = int(total_longitude // 30)
    degree_in_sign = total_longitude % 30.0

    part = int(degree_in_sign // 3.0)

    if sign_index % 2 == 0:  # Odd sign (Aries=0, Gemini=2) - wait index is 0-based
        # 0=Aries (Odd), 1=Taurus (Even) in Vedic (1-based)
        # So sign_index % 2 == 0 is Vedic 1, 3, 5 (Odd signs)
        varga_sign = (sign_index + part) % 12
    else:  # Even sign
        varga_sign = (sign_index + 8 + part) % 12  # Start from 9th sign (index+8)

    return VargaResult(
        "Dashamsa", 10, varga_sign, SIGNS[varga_sign], (degree_in_sign % 3.0) * 10
    )


if __name__ == "__main__":
    # Test cases:
    # 1. 0 deg Aries (0) -> Navamsa Aries (0)
    print(compute_navamsa(0.0))
    # 2. 10 deg Taurus (40 total) -> Navamsa Aries (40 * 3 / 10 = 12 % 12 = 0)
    print(compute_navamsa(40.0))
    # 3. 0.25 deg Aries -> D-60 Aries
    print(compute_shastiamsa(0.25))
    # 4. 0.75 deg Aries -> D-60 Taurus
    print(compute_shastiamsa(0.75))
