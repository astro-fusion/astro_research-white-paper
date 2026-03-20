"""
Birth Chart Calculations.

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
    get_zodiac_sign,
)
from .ephemeris import EphemerisEngine
from ..config.constants import NAKSHATRAS

# Internal bridge to src/celestial if available for advanced house systems
try:
    from src.celestial.house_systems import CelestialHouseSystem, compute_house_cusps

    HAS_CELESTIAL_ENGINES = True
except ImportError:
    HAS_CELESTIAL_ENGINES = False


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
        house_system: str = "P",  # Default: Placidus
        node_type: str = "mean",  # Default: Mean Node
    ):
        """
        Initialize birth chart.

        Args:
            birth_datetime: Birth date and time
            latitude: Birth latitude in decimal degrees
            longitude: Birth longitude in decimal degrees
            ayanamsa_system: Ayanamsa system to use
            house_system: Swiss Ephemeris house system code (e.g., 'P', 'K', 'O', 'W')
            node_type: 'mean' or 'true' node
        """
        self.birth_datetime = birth_datetime
        self.latitude = latitude
        self.longitude = longitude
        self.ayanamsa_system = ayanamsa_system
        self.house_system_code = (
            house_system.encode() if isinstance(house_system, str) else house_system
        )
        self.node_type = node_type

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
        """Retrieve Lagna (Ascendant) information."""
        if self._ascendant is None:
            self._ascendant = self._calculate_ascendant()
        return self._ascendant

    @property
    def houses(self) -> List[Dict]:
        """Return house cusp information."""
        if self._houses is None:
            self._houses = self._calculate_houses()
        return self._houses

    @property
    def planets(self) -> Dict[str, Dict]:
        """Return all planetary positions."""
        if self._planets is None:
            self._planets = self.ephemeris.get_all_planet_positions(
                self.julian_day, node_type=self.node_type
            )
        return self._planets

    @property
    def ayanamsa(self) -> float:
        """Get Ayanamsa value for this chart."""
        if self._ayanamsa is None:
            self._ayanamsa = self.ephemeris.get_ayanamsa_offset(self.julian_day)
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

        Standard: Placidus (P) or Whole Sign (W). Handles polar regions via src bridge.

        Returns:
            List of 12 dictionaries with house information
        """
        if HAS_CELESTIAL_ENGINES:
            # Map single-letter code to HouseSystem enum if possible
            try:
                # This is a bit hacky but works for the bridge
                enum_map = {
                    b"P": CelestialHouseSystem.PLACIDUS,
                    b"W": CelestialHouseSystem.WHOLE_SIGN,
                }
                sys_enum = enum_map.get(
                    self.house_system_code, CelestialHouseSystem.PORPHYRY
                )
                cusps, ascmc_0, mc_0 = compute_house_cusps(
                    self.julian_day, self.latitude, self.longitude, sys_enum
                )
            except Exception:
                # Fallback to direct swisseph if bridge fails
                cusps, ascmc = swe.houses_ex(
                    self.julian_day,
                    self.latitude,
                    self.longitude,
                    self.house_system_code,
                )
        else:
            cusps, ascmc = swe.houses_ex(
                self.julian_day, self.latitude, self.longitude, self.house_system_code
            )

        houses = []
        for i in range(12):
            house_longitude = cusps[i]
            if not self.ephemeris.sidereal_mode_set:
                house_longitude = convert_tropical_to_sidereal(
                    house_longitude, self.ayanamsa
                )
            house_longitude = house_longitude % 360
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
        planet_name = planet_name.upper()
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

    def get_planet_nakshatra(self, planet_name: str) -> Optional[Dict]:
        """
        Get Nakshatra information for a specific planet.

        Args:
            planet_name: Name of the planet

        Returns:
            Dictionary with Nakshatra info or None if planet not found
        """
        planet_name = planet_name.upper()
        if planet_name not in self.planets:
            return None

        longitude = self.planets[planet_name]["longitude"]
        return get_nakshatra(longitude)

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
    house_system: str = "P",
    node_type: str = "mean",
) -> BirthChart:
    """
    Calculate a complete birth chart.

    Args:
        birth_datetime: Birth date and time
        latitude: Birth latitude in decimal degrees
        longitude: Birth longitude in decimal degrees
        ayanamsa_system: Ayanamsa system to use

    Returns:
        BirthChart object with complete chart data
    """
    return BirthChart(
        birth_datetime,
        latitude,
        longitude,
        ayanamsa_system,
        house_system=house_system,
        node_type=node_type,
    )


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


def get_nakshatra(longitude: float) -> Dict:
    """
    Get Nakshatra (lunar mansion) information for a given longitude.

    Args:
        longitude: Celestial longitude in degrees (0-360)

    Returns:
        Dictionary with Nakshatra name, lord, deity, and pada (quarter)
    """
    normalized_long = longitude % 360

    # Each Nakshatra spans 13°20' (13.3333... degrees)
    nakshatra_span = 360 / 27
    nakshatra_index = int(normalized_long / nakshatra_span)

    # Calculate angular distance into the Nakshatra
    degrees_in_nakshatra = normalized_long % nakshatra_span

    # Each Pada (quarter) spans 3°20' (3.3333... degrees)
    # 4 Padas per Nakshatra
    pada = int(degrees_in_nakshatra / (nakshatra_span / 4)) + 1

    data = NAKSHATRAS[nakshatra_index]

    return {
        "index": nakshatra_index,
        "name": data["name"],
        "lord": data["lord"],
        "deity": data["deity"],
        "pada": pada,
        "degrees_in_nakshatra": degrees_in_nakshatra,
    }
