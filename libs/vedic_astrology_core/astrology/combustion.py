"""
Combustion (astangata / moudhya): a planet too close to the Sun.

Orbs are per planet, after Surya Siddhanta Ch. 9 (as tabulated in the
standard Jyotish references): Moon 12, Mars 17, Mercury 14 (12 when
retrograde), Jupiter 11, Venus 10 (8 when retrograde), Saturn 15 degrees of
longitude from the Sun. The Sun cannot be combust with itself, and Rahu and
Ketu (mathematical points) are never combust.
"""

from typing import Dict, Tuple

from ..config.constants import Planet

# (direct orb, retrograde orb) in degrees of longitude from the Sun.
COMBUSTION_ORBS: Dict[Planet, Tuple[float, float]] = {
    Planet.MOON: (12.0, 12.0),
    Planet.MARS: (17.0, 17.0),
    Planet.MERCURY: (14.0, 12.0),
    Planet.JUPITER: (11.0, 11.0),
    Planet.VENUS: (10.0, 8.0),
    Planet.SATURN: (15.0, 15.0),
}


def angular_separation(lon1: float, lon2: float) -> float:
    """Shortest angular distance between two longitudes, in [0, 180]."""
    diff = abs(lon1 - lon2) % 360.0
    return min(diff, 360.0 - diff)


def combustion_orb(planet: Planet, retrograde: bool = False) -> float:
    """Return the combustion orb for ``planet``; 0.0 if it cannot be combust."""
    if planet not in COMBUSTION_ORBS:
        return 0.0
    direct, retro = COMBUSTION_ORBS[planet]
    return retro if retrograde else direct


def is_combust(
    planet: Planet, longitude: float, sun_longitude: float, retrograde: bool = False
) -> bool:
    """Return True if ``planet`` lies within its combustion orb of the Sun."""
    if planet not in COMBUSTION_ORBS:
        return False
    return angular_separation(longitude, sun_longitude) <= combustion_orb(
        planet, retrograde
    )


__all__ = ["COMBUSTION_ORBS", "angular_separation", "combustion_orb", "is_combust"]
