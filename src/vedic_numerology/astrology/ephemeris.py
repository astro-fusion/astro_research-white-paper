"""
Swiss Ephemeris Engine

Provides a high-level interface to the Swiss Ephemeris (pyswisseph) for
calculating planetary positions, retrograde status, and combustion.

This module handles the low-level astronomical calculations required
for Vedic astrology, including sidereal zodiac conversions.
"""

from typing import Dict, List, Optional, Tuple, Union
from datetime import datetime
from enum import Enum
import math

try:
    import swisseph as swe
    SWISSEPH_AVAILABLE = True
except ImportError:
    SWISSEPH_AVAILABLE = False
    swe = None

from .ayanamsa import AyanamsaSystem, get_ayanamsa_offset, convert_tropical_to_sidereal, get_pyswisseph_ayanamsa_constant
from ..config.constants import PLANETS


class EphemerisEngine:
    """
    Swiss Ephemeris calculation engine for Vedic astrology.

    Provides methods for calculating planetary positions, checking retrograde
    and combustion status, and handling sidereal zodiac conversions.
    """

    def __init__(self, ayanamsa_system: AyanamsaSystem = AyanamsaSystem.LAHIRI):
        """
        Initialize the ephemeris engine.

        Args:
            ayanamsa_system: Ayanamsa system to use for sidereal calculations
        """
        self.ayanamsa_system = ayanamsa_system
        self.sidereal_mode_set = False

        if SWISSEPH_AVAILABLE:
            self._initialize_swisseph()
        else:
            raise ImportError(
                "pyswisseph is not available. Install with: pip install pyswisseph>=2.08.00-1\n"
                "For Google Colab: pip install pyswisseph"
            )

    def _initialize_swisseph(self):
        """Initialize Swiss Ephemeris with proper settings."""
        # Set ephemeris path if needed (usually not required in modern installations)
        try:
            swe.set_ephe_path()
        except:
            pass  # Default path usually works

        # Set sidereal mode
        pyswisseph_constant = get_pyswisseph_ayanamsa_constant(self.ayanamsa_system)
        if pyswisseph_constant is not None:
            swe.set_sid_mode(pyswisseph_constant, 0.0, 0.0)
            self.sidereal_mode_set = True
        else:
            # Fallback to manual Ayanamsa calculation
            self.sidereal_mode_set = False

    def datetime_to_julian_day(self, dt: datetime) -> float:
        """
        Convert datetime to Julian Day Number.

        Args:
            dt: Datetime object

        Returns:
            Julian Day Number as float
        """
        # Convert to UTC if timezone-aware
        if dt.tzinfo is not None:
            dt = dt.utctimetuple()
            year, month, day = dt.tm_year, dt.tm_mon, dt.tm_mday
            hour = dt.tm_hour + dt.tm_min / 60.0 + dt.tm_sec / 3600.0
        else:
            year, month, day = dt.year, dt.month, dt.day
            hour = dt.hour + dt.minute / 60.0 + dt.second / 3600.0

        # Calculate Julian Day
        if month <= 2:
            year -= 1
            month += 12

        a = math.floor(year / 100)
        b = 2 - a + math.floor(a / 4)

        jd = (math.floor(365.25 * (year + 4716)) +
              math.floor(30.6001 * (month + 1)) +
              day + b - 1524 + hour / 24.0)

        return jd

    def get_planet_position(self, julian_day: float, planet: Union[int, str]) -> Dict:
        """
        Calculate planetary position for a given time.

        Args:
            julian_day: Julian day number
            planet: Planet identifier (int constant or string name)

        Returns:
            Dictionary with position data:
            - 'longitude': Celestial longitude in degrees (0-360)
            - 'latitude': Celestial latitude in degrees
            - 'distance': Distance from Earth in AU
            - 'longitude_speed': Daily speed in longitude (degrees/day)
            - 'sign': Zodiac sign index (0-11)
            - 'sign_name': Zodiac sign name
            - 'degrees_in_sign': Degrees within sign (0-30)
            - 'retrograde': Boolean indicating retrograde motion
            - 'combust': Boolean indicating combustion (close to Sun)

        Raises:
            ValueError: If planet identifier is invalid
        """
        # Convert planet name to constant if needed
        if isinstance(planet, str):
            planet = self._planet_name_to_constant(planet)

        # Calculate position using Swiss Ephemeris
        # swe.calc_ut returns: (longitude, latitude, distance, speed_longitude, speed_latitude, speed_distance)
        result = swe.calc_ut(julian_day, planet)

        longitude, latitude, distance = result[0], result[1], result[2]
        speed_longitude = result[3]

        # Handle sidereal conversion if not using built-in sidereal mode
        if not self.sidereal_mode_set:
            ayanamsa = get_ayanamsa_offset(julian_day, self.ayanamsa_system)
            longitude = convert_tropical_to_sidereal(longitude, ayanamsa)

        # Normalize longitude to 0-360
        longitude = longitude % 360

        # Get zodiac sign information
        from .ayanamsa import get_zodiac_sign
        sign_index, sign_name, degrees_in_sign = get_zodiac_sign(longitude)

        # Check retrograde status
        retrograde = speed_longitude < 0

        # Check combustion (within 8 degrees of Sun)
        sun_result = swe.calc_ut(julian_day, swe.SUN)
        sun_longitude = sun_result[0]
        if not self.sidereal_mode_set:
            sun_longitude = convert_tropical_to_sidereal(sun_longitude, ayanamsa)

        # Calculate angular separation, accounting for 360-degree wraparound
        angle_diff = abs(longitude - sun_longitude)
        angle_diff = min(angle_diff, 360 - angle_diff)
        combust = angle_diff <= 8.0  # 8-degree orb for combustion

        return {
            'longitude': longitude,
            'latitude': latitude,
            'distance': distance,
            'longitude_speed': speed_longitude,
            'sign': sign_index,
            'sign_name': sign_name,
            'degrees_in_sign': degrees_in_sign,
            'retrograde': retrograde,
            'combust': combust
        }

    def get_node_positions(self, julian_day: float) -> Tuple[Dict, Dict]:
        """
        Calculate positions of Rahu (North Node) and Ketu (South Node).

        Args:
            julian_day: Julian day number

        Returns:
            Tuple of (rahu_position, ketu_position) dictionaries
        """
        # Calculate Rahu (North Node)
        rahu_data = self.get_planet_position(julian_day, swe.TRUE_NODE)

        # Ketu is always 180 degrees opposite to Rahu
        ketu_longitude = (rahu_data['longitude'] + 180) % 360

        # Create Ketu position data (copy Rahu and modify)
        ketu_data = rahu_data.copy()
        ketu_data['longitude'] = ketu_longitude

        # Recalculate sign information for Ketu
        from .ayanamsa import get_zodiac_sign
        ketu_sign_index, ketu_sign_name, ketu_degrees_in_sign = get_zodiac_sign(ketu_longitude)
        ketu_data['sign'] = ketu_sign_index
        ketu_data['sign_name'] = ketu_sign_name
        ketu_data['degrees_in_sign'] = ketu_degrees_in_sign

        return rahu_data, ketu_data

    def is_retrograde(self, julian_day: float, planet: Union[int, str]) -> bool:
        """
        Check if a planet is retrograde at a given time.

        Args:
            julian_day: Julian day number
            planet: Planet identifier

        Returns:
            True if planet is retrograde
        """
        position_data = self.get_planet_position(julian_day, planet)
        return position_data['retrograde']

    def is_combust(self, julian_day: float, planet: Union[int, str]) -> bool:
        """
        Check if a planet is combust (close to the Sun) at a given time.

        Args:
            julian_day: Julian day number
            planet: Planet identifier

        Returns:
            True if planet is combust
        """
        position_data = self.get_planet_position(julian_day, planet)
        return position_data['combust']

    def get_all_planet_positions(self, julian_day: float) -> Dict[str, Dict]:
        """
        Calculate positions for all traditional planets.

        Args:
            julian_day: Julian day number

        Returns:
            Dictionary mapping planet names to position data
        """
        planets = {
            'Sun': swe.SUN,
            'Moon': swe.MOON,
            'Mars': swe.MARS,
            'Mercury': swe.MERCURY,
            'Jupiter': swe.JUPITER,
            'Venus': swe.VENUS,
            'Saturn': swe.SATURN,
            'Rahu': swe.TRUE_NODE,  # Will be handled specially
            'Ketu': 'KETU'  # Special marker for Ketu calculation
        }

        positions = {}

        for planet_name, planet_const in planets.items():
            if planet_name == 'Ketu':
                # Handle Ketu specially
                rahu_data, ketu_data = self.get_node_positions(julian_day)
                positions['Ketu'] = ketu_data
            elif planet_name == 'Rahu':
                rahu_data, ketu_data = self.get_node_positions(julian_day)
                positions['Rahu'] = rahu_data
            else:
                positions[planet_name] = self.get_planet_position(julian_day, planet_const)

        return positions

    def _planet_name_to_constant(self, planet_name: str) -> int:
        """
        Convert planet name to Swiss Ephemeris constant.

        Args:
            planet_name: Planet name (case-insensitive)

        Returns:
            Swiss Ephemeris planet constant

        Raises:
            ValueError: If planet name is not recognized
        """
        name_to_const = {
            'sun': swe.SUN,
            'moon': swe.MOON,
            'mars': swe.MARS,
            'mercury': swe.MERCURY,
            'jupiter': swe.JUPITER,
            'venus': swe.VENUS,
            'saturn': swe.SATURN,
            'rahu': swe.TRUE_NODE,
            'ketu': swe.TRUE_NODE,  # Ketu handled separately
            'north_node': swe.TRUE_NODE,
            'south_node': swe.TRUE_NODE,
            'true_node': swe.TRUE_NODE,
            'mean_node': swe.MEAN_NODE,
        }

        planet_lower = planet_name.lower()
        if planet_lower not in name_to_const:
            valid_names = list(name_to_const.keys())
            raise ValueError(f"Unknown planet '{planet_name}'. Valid names: {valid_names}")

        return name_to_const[planet_lower]

    def get_ephemeris_info(self) -> Dict:
        """
        Get information about the current ephemeris configuration.

        Returns:
            Dictionary with ephemeris configuration info
        """
        return {
            'swisseph_available': SWISSEPH_AVAILABLE,
            'sidereal_mode_set': self.sidereal_mode_set,
            'ayanamsa_system': self.ayanamsa_system.value,
            'version': swe.version if SWISSEPH_AVAILABLE else None
        }