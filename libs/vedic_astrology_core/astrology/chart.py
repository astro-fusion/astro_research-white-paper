"""
Birth Chart Calculations.

Sidereal ascendant, house cusps, planetary positions and nakshatras.

House systems: the ``house_system`` argument is honoured everywhere. The
default is whole sign (bhava = rashi), the Parashari practice. The ascendant,
the cusps and the house of each planet all come from the same system. Near
the poles quadrant systems (Placidus, Koch, ...) are undefined; above
66.5 deg latitude they fall back to whole sign with a warning (ported from
``src/celestial/house_systems.py``).
"""

import logging
import warnings
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Union

import swisseph as swe

from ..config.constants import NAKSHATRAS, Planet, PlanetDict, to_planet
from ..utils.datetime_utils import require_aware
from .ayanamsa import AyanamsaSystem, get_zodiac_sign, set_sidereal_mode
from .ephemeris import EphemerisEngine

logger = logging.getLogger(__name__)

PLACIDUS_HIGH_DISTORTION_LAT = 60.0  # degrees N/S
POLAR_SINGULARITY_LAT = 66.5  # degrees N/S

# Swiss Ephemeris house-system codes, by name or code.
HOUSE_SYSTEM_CODES: Dict[str, str] = {
    "whole_sign": "W",
    "w": "W",
    "equal": "E",
    "e": "E",
    "sripati": "S",
    "s": "S",
    "porphyry": "O",
    "o": "O",
    "placidus": "P",
    "p": "P",
    "koch": "K",
    "k": "K",
    "regiomontanus": "R",
    "r": "R",
    "campanus": "C",
    "c": "C",
    "topocentric": "T",
    "t": "T",
}
# Systems that are defined at every latitude.
LATITUDE_SAFE_SYSTEMS = {"W", "E"}
DEFAULT_HOUSE_SYSTEM = "W"


def resolve_house_system(house_system: Union[str, bytes]) -> str:
    """Return the one-letter Swiss Ephemeris code for a house-system name/code.

    Raises:
        ValueError: If the system is unknown.
    """
    if isinstance(house_system, bytes):
        house_system = house_system.decode()
    key = str(house_system).strip().lower()
    if key not in HOUSE_SYSTEM_CODES:
        raise ValueError(
            f"Unknown house system {house_system!r}. Valid: "
            f"{sorted(k for k in HOUSE_SYSTEM_CODES if len(k) > 1)}"
        )
    return HOUSE_SYSTEM_CODES[key]


def resolve_house_system_for_latitude(
    latitude: float, house_system: Union[str, bytes]
) -> Tuple[str, Optional[str]]:
    """Apply the polar-latitude fallback.

    Returns:
        (system code actually used, warning message or None)
    """
    code = resolve_house_system(house_system)
    abs_lat = abs(latitude)
    if abs_lat >= POLAR_SINGULARITY_LAT and code not in LATITUDE_SAFE_SYSTEMS:
        return DEFAULT_HOUSE_SYSTEM, (
            f"Latitude {latitude:.2f} deg exceeds the polar threshold "
            f"({POLAR_SINGULARITY_LAT} deg); house system {code!r} is undefined "
            "there. Falling back to whole sign."
        )
    if abs_lat >= PLACIDUS_HIGH_DISTORTION_LAT and code in ("P", "K"):
        return code, (
            f"Latitude {latitude:.2f} deg is in the high-distortion zone "
            f"({PLACIDUS_HIGH_DISTORTION_LAT}-{POLAR_SINGULARITY_LAT} deg); "
            "house cusps may be severely compressed."
        )
    return code, None


def compute_sidereal_houses(
    julian_day: float,
    latitude: float,
    longitude: float,
    house_system: Union[str, bytes] = DEFAULT_HOUSE_SYSTEM,
    ayanamsa_system: Union[str, AyanamsaSystem] = AyanamsaSystem.LAHIRI,
) -> Tuple[List[float], float, float, str]:
    """
    Sidereal cusps, ascendant and MC from ``swe.houses_ex(..., FLG_SIDEREAL)``.

    Returns:
        (12 cusp longitudes, ascendant, MC, system code used)
    """
    code, warning = resolve_house_system_for_latitude(latitude, house_system)
    if warning:
        logger.warning(warning)
        warnings.warn(warning, RuntimeWarning, stacklevel=2)
    set_sidereal_mode(ayanamsa_system)
    cusps, ascmc = swe.houses_ex(
        julian_day, latitude, longitude, code.encode(), swe.FLG_SIDEREAL
    )
    return (
        [c % 360.0 for c in cusps[:12]],
        ascmc[0] % 360.0,
        ascmc[1] % 360.0,
        code,
    )


class BirthChart:
    """
    Complete sidereal birth chart.

    Contains planetary positions, ascendant, house cusps, and metadata
    required for dignity scoring.
    """

    def __init__(
        self,
        birth_datetime: datetime,
        latitude: float,
        longitude: float,
        ayanamsa_system: AyanamsaSystem = AyanamsaSystem.LAHIRI,
        house_system: Union[str, bytes] = DEFAULT_HOUSE_SYSTEM,
        node_type: str = "mean",
    ):
        """
        Initialize birth chart.

        Args:
            birth_datetime: Timezone-aware birth date and time
            latitude: Birth latitude in decimal degrees
            longitude: Birth longitude in decimal degrees (east positive)
            ayanamsa_system: Ayanamsa system to use
            house_system: "whole_sign" (default), "sripati", "equal",
                "placidus", "koch", "porphyry", ... or a Swiss Ephemeris code
            node_type: "mean" (default) or "true" lunar node

        Raises:
            ValueError: On a naive datetime, bad coordinates or unknown system.
        """
        require_aware(birth_datetime, "birth_datetime")
        if not (-90 <= latitude <= 90):
            raise ValueError(f"Latitude must be between -90 and 90, got {latitude}")
        if not (-180 <= longitude <= 180):
            raise ValueError(f"Longitude must be between -180 and 180, got {longitude}")
        self.birth_datetime = birth_datetime
        self.latitude = latitude
        self.longitude = longitude
        self.ayanamsa_system = ayanamsa_system
        self.requested_house_system = resolve_house_system(house_system)
        self.house_system, self.house_system_warning = (
            resolve_house_system_for_latitude(latitude, house_system)
        )
        if self.house_system_warning:
            logger.warning(self.house_system_warning)
            warnings.warn(self.house_system_warning, RuntimeWarning, stacklevel=2)
        self.house_system_code = self.house_system.encode()
        self.node_type = node_type

        self.ephemeris = EphemerisEngine(ayanamsa_system, node_model=node_type)
        self.julian_day = self.ephemeris.datetime_to_julian_day(birth_datetime)

        self._ascendant: Optional[Dict] = None
        self._houses: Optional[List[Dict]] = None
        self._planets: Optional[PlanetDict] = None
        self._ayanamsa: Optional[float] = None
        self._cusps: Optional[List[float]] = None

    def _compute_houses(self) -> None:
        if self._cusps is not None:
            return
        cusps, asc, _mc, _code = compute_sidereal_houses(
            self.julian_day,
            self.latitude,
            self.longitude,
            self.house_system,
            self.ayanamsa_system,
        )
        self._cusps = cusps
        sign_index, sign_name, degrees_in_sign = get_zodiac_sign(asc)
        self._ascendant = {
            "longitude": asc,
            "sign": sign_index,
            "sign_name": sign_name,
            "degrees_in_sign": degrees_in_sign,
            "full_name": f"{sign_name} {degrees_in_sign:.2f}°",
        }

    @property
    def ascendant(self) -> Dict:
        """Sidereal Lagna (ascendant)."""
        self._compute_houses()
        assert self._ascendant is not None
        return self._ascendant

    @property
    def houses(self) -> List[Dict]:
        """Sidereal house cusps of the chart's house system."""
        if self._houses is None:
            self._compute_houses()
            assert self._cusps is not None
            houses = []
            for i, cusp in enumerate(self._cusps):
                sign_index, sign_name, degrees_in_sign = get_zodiac_sign(cusp)
                houses.append(
                    {
                        "house_number": i + 1,
                        "longitude": cusp,
                        "sign": sign_index,
                        "sign_name": sign_name,
                        "degrees_in_sign": degrees_in_sign,
                        "full_name": f"{sign_name} {degrees_in_sign:.2f}°",
                    }
                )
            self._houses = houses
        return self._houses

    @property
    def planets(self) -> PlanetDict:
        """All planetary positions, keyed by :class:`Planet`."""
        if self._planets is None:
            self._planets = self.ephemeris.get_all_planet_positions(self.julian_day)
            for planet, data in self._planets.items():
                data["house"] = self._house_of_longitude(data["longitude"])
        return self._planets

    @property
    def ayanamsa(self) -> float:
        """Ayanamsa value (degrees) at the birth instant."""
        if self._ayanamsa is None:
            self._ayanamsa = self.ephemeris.get_ayanamsa(self.julian_day)
        return self._ayanamsa

    def _house_of_longitude(self, lon: float) -> int:
        """House (1-12) containing ``lon`` under the chart's house system."""
        if self.house_system == "W":
            asc_sign = int(self.ascendant["longitude"] // 30)
            return (int(lon // 30) - asc_sign) % 12 + 1
        self._compute_houses()
        assert self._cusps is not None
        cusps = self._cusps
        for i in range(12):
            start, end = cusps[i], cusps[(i + 1) % 12]
            span = (end - start) % 360.0
            if (lon - start) % 360.0 < span:
                return i + 1
        return 12

    def get_planet_in_house(self, planet_name: Union[Planet, str]) -> Optional[int]:
        """
        Return the house (1-12) of a planet under the chart's house system.

        Returns None if the planet is unknown.
        """
        try:
            planet = to_planet(planet_name)
        except KeyError:
            return None
        return self._house_of_longitude(self.planets[planet]["longitude"])

    def get_planets_in_sign(self, sign_index: int) -> List[Planet]:
        """Return the planets placed in a zodiac sign (0-11)."""
        return [p for p, data in self.planets.items() if data["sign"] == sign_index]

    def get_planet_nakshatra(self, planet_name: Union[Planet, str]) -> Optional[Dict]:
        """Return nakshatra information for a planet, or None if unknown."""
        try:
            planet = to_planet(planet_name)
        except KeyError:
            return None
        return get_nakshatra(self.planets[planet]["longitude"])

    def get_chart_summary(self) -> Dict:
        """Return a JSON-friendly summary of the chart."""
        return {
            "birth_datetime": self.birth_datetime.isoformat(),
            "latitude": self.latitude,
            "longitude": self.longitude,
            "ayanamsa_system": self.ayanamsa_system.value,
            "ayanamsa_value": self.ayanamsa,
            "house_system": self.house_system,
            "node_model": self.ephemeris.node_model,
            "ephemeris_model": self.ephemeris.ephemeris_model,
            "julian_day": self.julian_day,
            "ascendant": self.ascendant,
            "planets": {p.name: data for p, data in self.planets.items()},
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
    house_system: Union[str, bytes] = DEFAULT_HOUSE_SYSTEM,
    node_type: str = "mean",
) -> BirthChart:
    """Calculate a complete sidereal birth chart (see :class:`BirthChart`)."""
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
    """Return the sidereal ascendant for the given birth data."""
    chart = calculate_chart(birth_datetime, latitude, longitude, ayanamsa_system)
    return chart.ascendant


def get_house_system(
    birth_datetime: datetime,
    latitude: float,
    longitude: float,
    ayanamsa_system: AyanamsaSystem = AyanamsaSystem.LAHIRI,
    house_system: Union[str, bytes] = DEFAULT_HOUSE_SYSTEM,
) -> List[Dict]:
    """Return the sidereal house cusps for the given birth data."""
    chart = calculate_chart(
        birth_datetime, latitude, longitude, ayanamsa_system, house_system
    )
    return chart.houses


def get_planet_in_sign(longitude: float) -> Tuple[int, str, float]:
    """Return (sign_index, sign_name, degrees_in_sign) for a longitude."""
    return get_zodiac_sign(longitude)


NAKSHATRA_SPAN = 360.0 / 27.0
PADA_SPAN = NAKSHATRA_SPAN / 4.0


def get_nakshatra(longitude: float) -> Dict:
    """
    Return the nakshatra (lunar mansion) of a sidereal longitude.

    Returns:
        Dictionary with index (0-26), name, lord, deity, pada (1-4) and
        degrees_in_nakshatra.
    """
    lon = longitude % 360.0
    index = int(lon // NAKSHATRA_SPAN) % 27
    degrees_in_nakshatra = lon - index * NAKSHATRA_SPAN
    pada = min(int(degrees_in_nakshatra // PADA_SPAN), 3) + 1
    data = NAKSHATRAS[index]
    return {
        "index": index,
        "name": data["name"],
        "lord": data["lord"],
        "deity": data["deity"],
        "pada": pada,
        "degrees_in_nakshatra": degrees_in_nakshatra,
    }
