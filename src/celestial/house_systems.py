"""src/celestial/house_systems.py.

Astrological House System Router with Polar Singularity Handling
================================================================
See: papers/astrology/02_house_systems_and_polar_singularities.md
     SYMBOLOGY.md §II.E
"""

from __future__ import annotations

from enum import Enum

import numpy as np

PLACIDUS_HIGH_DISTORTION_LAT = 60.0  # degrees N/S
PLACIDUS_SINGULARITY_LAT = 66.5  # degrees N/S


class HouseSystem(Enum):
    """Supported house systems."""

    PLACIDUS = b"P"
    KOCH = b"K"
    REGIOMONTANUS = b"R"
    CAMPANUS = b"C"
    TOPOCENTRIC = b"T"
    PORPHYRY = b"O"
    EQUAL = b"E"
    WHOLE_SIGN = b"W"


def resolve_house_system(
    geographic_lat: float,
    requested_system: HouseSystem = HouseSystem.PLACIDUS,
    fallback_system: HouseSystem = HouseSystem.WHOLE_SIGN,
) -> tuple[HouseSystem, str | None]:
    """
    Return the appropriate house system for the given geographic latitude.

    Parameters
    ----------
    geographic_lat : float
        Observer's geographic latitude in degrees (−90 to +90).
    requested_system : HouseSystem
        Preferred house system.
    fallback_system : HouseSystem
        System to use when singularity is detected.

    Returns
    -------
    (resolved_system, warning_message | None)
    """
    abs_lat = abs(geographic_lat)

    if abs_lat >= PLACIDUS_SINGULARITY_LAT:
        warning = (
            f"Geographic latitude {geographic_lat:.2f}° exceeds polar singularity "
            f"threshold ({PLACIDUS_SINGULARITY_LAT}°). "
            f"Falling back to {fallback_system.name}."
        )
        return fallback_system, warning

    if abs_lat >= PLACIDUS_HIGH_DISTORTION_LAT and requested_system in (
        HouseSystem.PLACIDUS,
        HouseSystem.KOCH,
    ):
        warning = (
            f"Geographic latitude {geographic_lat:.2f}° is in the high-distortion "
            f"zone ({PLACIDUS_HIGH_DISTORTION_LAT}°–{PLACIDUS_SINGULARITY_LAT}°). "
            f"House cusps may be severely compressed."
        )
        return requested_system, warning

    return requested_system, None


def compute_diurnal_semi_arc(
    declination_deg: float,
    geographic_lat_deg: float,
) -> float | None:
    """
    Compute the Diurnal Semi-Arc (DSA) for an ecliptic point.

    DSA(λ, φ) = 90° + arcsin(tan(δ)·tan(φ))

    Returns None if the ecliptic point is circumpolar (no rising/setting).
    See: papers/astrology/02 §1.1
    """
    tan_product = np.tan(np.radians(declination_deg)) * np.tan(
        np.radians(geographic_lat_deg)
    )
    if abs(tan_product) > 1.0:
        return None  # Circumpolar — singularity
    return 90.0 + np.degrees(np.arcsin(tan_product))


def compute_house_cusps(
    jd_tt: float,
    geographic_lat: float,
    geographic_lon: float,
    system: HouseSystem = HouseSystem.PLACIDUS,
) -> tuple[list[float], float, float]:
    """
    Compute 12 house cusps, ASC, and MC for the given chart params.

    Returns
    -------
    (cusps_12, asc_deg, mc_deg)
    cusps_12 : list of 12 ecliptic longitudes (tropical), houses 1–12
    asc_deg  : Ascendant ecliptic longitude
    mc_deg   : Midheaven ecliptic longitude
    """
    try:
        import swisseph as swe
    except ImportError as exc:
        raise ImportError("pyswisseph required: pip install pyswisseph") from exc

    resolved_system, warning = resolve_house_system(geographic_lat, system)
    if warning:
        import logging

        logging.getLogger(__name__).warning(warning)

    cusps_raw, ascmc = swe.houses(
        jd_tt, geographic_lat, geographic_lon, resolved_system.value
    )
    cusps_12 = list(cusps_raw[:12])
    asc_deg = float(ascmc[0])
    mc_deg = float(ascmc[1])

    return cusps_12, asc_deg, mc_deg
