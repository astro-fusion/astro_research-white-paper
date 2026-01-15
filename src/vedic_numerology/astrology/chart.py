"""
Birth Chart Calculations

Handles complete birth chart generation including ascendant calculation,
house cusps, planetary positions, and chart analysis for Vedic astrology.
"""

from datetime import datetime
from typing import Dict, List, Optional, Tuple

try:
    import swisseph as swe

    SWISSEPH_AVAILABLE = True
except ImportError:
    SWISSEPH_AVAILABLE = False
    swe = None

from .ayanamsa import (
    AyanamsaSystem,
    convert_tropical_to_sidereal,
    get_ayanamsa_offset,
    get_zodiac_sign,
)
from .ephemeris import EphemerisEngine


class BirthChart:
    """
    Complete birth chart for Vedic astrology analysis.

    Contains planetary positions, ascendant, house cusps, and metadata
    required for dignity scoring and numerology-astrology correlation.
    """

    def __init__(
        self,
        birth_datetime: datetime,
        latitude: float,
        longitude: float,
        ayanamsa_system: AyanamsaSystem = AyanamsaSystem.LAHIRI,
    ):
        """
        Initialize birth chart.

        Args:
            birth_datetime: Birth date and time
            latitude: Birth latitude in decimal degrees
            longitude: Birth longitude in decimal degrees
            ayanamsa_system: Ayanamsa system to use
        """
        self.birth_datetime = birth_datetime
        self.latitude = latitude
        self.longitude = longitude
        self.ayanamsa_system = ayanamsa_system

        # Validate coordinates
        if not (-90 <= self.latitude <= 90):
            raise ValueError(
                f"Latitude must be between -90 and 90, got {self.latitude}"
            )
        if not (-180 <= self.longitude <= 180):
            raise ValueError(
                f"Longitude must be between -180 and 180, got {self.longitude}"
            )

        # Initialize ephemeris engine
        self.ephemeris = EphemerisEngine(ayanamsa_system)

        # Calculate Julian Day
        self.julian_day = self.ephemeris.datetime_to_julian_day(birth_datetime)

        # Chart data (calculated on demand)
        self._ascendant: Optional[Dict] = None
        self._houses: Optional[List[Dict]] = None
        self._planets: Optional[Dict[str, Dict]] = None
        self._ayanamsa: Optional[float] = None

    @property
    def ascendant(self) -> Dict:
        """Get ascendant (Lagna) information."""
        if self._ascendant is None:
            self._ascendant = self._calculate_ascendant()
        return self._ascendant

    @property
    def houses(self) -> List[Dict]:
        """Get house cusp information."""
        if self._houses is None:
            self._houses = self._calculate_houses()
        return self._houses

    @property
    def planets(self) -> Dict[str, Dict]:
        """Get all planetary positions."""
        if self._planets is None:
            self._planets = self.ephemeris.get_all_planet_positions(self.julian_day)
        return self._planets

    @property
    def ayanamsa(self) -> float:
        """Get Ayanamsa value for this chart."""
        if self._ayanamsa is None:
            self._ayanamsa = get_ayanamsa_offset(self.julian_day, self.ayanamsa_system)
        return self._ayanamsa

    def _calculate_ascendant(self) -> Dict:
        """
        Calculate the ascendant (Lagna) for the birth chart.

        The ascendant is the degree of the zodiac rising on the eastern horizon
        at the time of birth.

        Returns:
            Dictionary with ascendant information
        """
        # Calculate ascendant using Swiss Ephemeris
        # swe.houses_ex() returns house cusps, but we can also get ascendant directly
        cusps, ascmc = swe.houses_ex(
            self.julian_day, self.latitude, self.longitude, b"P"
        )  # Placidus

        ascendant_longitude = ascmc[0]  # Ascendant is first element

        # Convert to sidereal if needed
        if not self.ephemeris.sidereal_mode_set:
            ascendant_longitude = convert_tropical_to_sidereal(
                ascendant_longitude, self.ayanamsa
            )

        # Normalize to 0-360
        ascendant_longitude = ascendant_longitude % 360

        # Get sign information
        sign_index, sign_name, degrees_in_sign = get_zodiac_sign(ascendant_longitude)

        return {
            "longitude": ascendant_longitude,
            "sign": sign_index,
            "sign_name": sign_name,
            "degrees_in_sign": degrees_in_sign,
            "full_name": f"{sign_name} {degrees_in_sign:.2f}°",
        }

    def _calculate_houses(self) -> List[Dict]:
        """
        Calculate house cusps for the birth chart.

        Uses Placidus house system as standard for Vedic astrology.

        Returns:
            List of 12 dictionaries with house information
        """
        # Calculate houses using Swiss Ephemeris
        cusps, ascmc = swe.houses_ex(
            self.julian_day, self.latitude, self.longitude, b"P"
        )  # Placidus

        houses = []

        for i in range(12):
            house_longitude = cusps[i]

            # Convert to sidereal if needed
            if not self.ephemeris.sidereal_mode_set:
                house_longitude = convert_tropical_to_sidereal(
                    house_longitude, self.ayanamsa
                )

            # Normalize to 0-360
            house_longitude = house_longitude % 360

            # Get sign information
            sign_index, sign_name, degrees_in_sign = get_zodiac_sign(house_longitude)

            houses.append(
                {
                    "house_number": i + 1,
                    "longitude": house_longitude,
                    "sign": sign_index,
                    "sign_name": sign_name,
                    "degrees_in_sign": degrees_in_sign,
                    "full_name": f"{sign_name} {degrees_in_sign:.2f}°",
                }
            )

        return houses

    def get_planet_in_house(self, planet_name: str) -> Optional[int]:
        """
        Determine which house a planet is in.

        Args:
            planet_name: Name of the planet

        Returns:
            House number (1-12), or None if planet not found
        """
        if planet_name not in self.planets:
            return None

        planet_longitude = self.planets[planet_name]["longitude"]
        ascendant_longitude = self.ascendant["longitude"]

        # Calculate house by finding angular distance from ascendant
        # Each house spans 30 degrees
        angle_from_asc = (planet_longitude - ascendant_longitude) % 360
        house_number = int(angle_from_asc / 30) + 1

        return house_number

    def get_planets_in_sign(self, sign_index: int) -> List[str]:
        """
        Get all planets in a specific zodiac sign.

        Args:
            sign_index: Zodiac sign index (0-11)

        Returns:
            List of planet names in that sign
        """
        planets_in_sign = []

        for planet_name, planet_data in self.planets.items():
            if planet_data["sign"] == sign_index:
                planets_in_sign.append(planet_name)

        return planets_in_sign

    def get_chart_summary(self) -> Dict:
        """
        Generate a summary of the birth chart.

        Returns:
            Dictionary with chart summary information
        """
        return {
            "birth_datetime": self.birth_datetime.isoformat(),
            "latitude": self.latitude,
            "longitude": self.longitude,
            "ayanamsa_system": self.ayanamsa_system.value,
            "ayanamsa_value": self.ayanamsa,
            "julian_day": self.julian_day,
            "ascendant": self.ascendant,
            "planets": self.planets,
            "houses": [
                {
                    "house": h["house_number"],
                    "sign": h["sign_name"],
                    "longitude": h["longitude"],
                }
                for h in self.houses
            ],
        }


def calculate_chart(
    birth_datetime: datetime,
    latitude: float,
    longitude: float,
    ayanamsa_system: AyanamsaSystem = AyanamsaSystem.LAHIRI,
) -> BirthChart:
    """
    Convenience function to calculate a complete birth chart.

    Args:
        birth_datetime: Birth date and time
        latitude: Birth latitude in decimal degrees
        longitude: Birth longitude in decimal degrees
        ayanamsa_system: Ayanamsa system to use

    Returns:
        BirthChart object with complete chart data
    """
    return BirthChart(birth_datetime, latitude, longitude, ayanamsa_system)


def get_ascendant(
    birth_datetime: datetime,
    latitude: float,
    longitude: float,
    ayanamsa_system: AyanamsaSystem = AyanamsaSystem.LAHIRI,
) -> Dict:
    """
    Calculate ascendant for a given birth data.

    Args:
        birth_datetime: Birth date and time
        latitude: Birth latitude
        longitude: Birth longitude
        ayanamsa_system: Ayanamsa system to use

    Returns:
        Dictionary with ascendant information
    """
    chart = calculate_chart(birth_datetime, latitude, longitude, ayanamsa_system)
    return chart.ascendant


def get_house_system(
    birth_datetime: datetime,
    latitude: float,
    longitude: float,
    ayanamsa_system: AyanamsaSystem = AyanamsaSystem.LAHIRI,
) -> List[Dict]:
    """
    Calculate house cusps for a given birth data.

    Args:
        birth_datetime: Birth date and time
        latitude: Birth latitude
        longitude: Birth longitude
        ayanamsa_system: Ayanamsa system to use

    Returns:
        List of house cusp dictionaries
    """
    chart = calculate_chart(birth_datetime, latitude, longitude, ayanamsa_system)
    return chart.houses


def get_planet_in_sign(longitude: float) -> Tuple[int, str, float]:
    """
    Get zodiac sign information for a given celestial longitude.

    Args:
        longitude: Celestial longitude in degrees (0-360)

    Returns:
        Tuple of (sign_index, sign_name, degrees_in_sign)
    """
    return get_zodiac_sign(longitude)
