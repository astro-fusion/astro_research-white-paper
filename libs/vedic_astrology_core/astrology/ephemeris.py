"""
Swiss Ephemeris Engine.

High-level interface to the Swiss Ephemeris (pyswisseph) for sidereal
planetary positions, retrograde status and combustion.

Conventions (all recorded on the engine so they can go into a run manifest):

* Every ``calc_ut`` call uses ``FLG_SWIEPH | FLG_SPEED | FLG_SIDEREAL``:
  apparent geocentric sidereal longitudes with velocities.
* The ayanamsa comes only from ``swe.get_ayanamsa_ut``.
* ``node_model`` ("mean" or "true", default "mean") selects the lunar node
  used for Rahu; Ketu is always Rahu + 180 degrees, computed in
  :meth:`EphemerisEngine.get_node_positions` and nowhere else.
* ``ephemeris_model`` is "swieph" when the Swiss Ephemeris ``.se1`` files
  were found and "moshier" when Swiss Ephemeris fell back to its analytic
  Moshier theory. It is read once, from a Sun calculation at engine
  creation, and does not change for the engine's lifetime (node calls
  always report ``swieph`` and must not overwrite it). The ``retflag`` of
  the latest calculation stays available as ``last_retflag``.
* Retrograde motion is read from the ``FLG_SPEED`` longitude velocity.
"""

import math
import os
from datetime import datetime
from typing import Dict, Optional, Tuple, Union

import swisseph as swe

from ..config.constants import Planet, PlanetDict, to_planet
from ..utils.datetime_utils import julian_day as calculate_jd
from .ayanamsa import (
    AyanamsaSystem,
    get_zodiac_sign,
    resolve_ayanamsa_system,
    set_sidereal_mode,
)
from .combustion import is_combust

SWISSEPH_AVAILABLE = True

SIDEREAL_FLAGS = swe.FLG_SWIEPH | swe.FLG_SPEED | swe.FLG_SIDEREAL
NODE_MODELS = ("mean", "true")

# Swiss Ephemeris body numbers for the seven visible grahas.
SWE_BODIES: Dict[Planet, int] = {
    Planet.SUN: swe.SUN,
    Planet.MOON: swe.MOON,
    Planet.MARS: swe.MARS,
    Planet.MERCURY: swe.MERCURY,
    Planet.JUPITER: swe.JUPITER,
    Planet.VENUS: swe.VENUS,
    Planet.SATURN: swe.SATURN,
}
PLANET_ORDER = [
    Planet.SUN,
    Planet.MOON,
    Planet.MARS,
    Planet.MERCURY,
    Planet.JUPITER,
    Planet.VENUS,
    Planet.SATURN,
    Planet.RAHU,
    Planet.KETU,
]


def ephemeris_model_from_retflag(retflag: int) -> str:
    """Return "swieph", "moshier" or "jpl" from a ``calc_ut`` return flag."""
    if retflag & swe.FLG_SWIEPH:
        return "swieph"
    if retflag & swe.FLG_JPLEPH:
        return "jpl"
    return "moshier"


def resolve_node_model(node_model: str) -> str:
    """Validate a node model name ("mean" or "true")."""
    model = str(node_model).lower()
    if model not in NODE_MODELS:
        raise ValueError(f"node_model must be one of {NODE_MODELS}, got {node_model!r}")
    return model


class EphemerisEngine:
    """
    Swiss Ephemeris calculation engine for Vedic astrology.

    Attributes:
        ayanamsa_system: The sidereal zodiac in use (default Lahiri).
        node_model: "mean" or "true" lunar node for Rahu (Ketu = Rahu + 180).
        ephemeris_model: "swieph" or "moshier", fixed at creation from a Sun
            calculation (read-only).
        last_retflag: ``retflag`` of the most recent calculation, for
            diagnostics.
    """

    def __init__(
        self,
        ayanamsa_system: Union[AyanamsaSystem, str] = AyanamsaSystem.LAHIRI,
        node_model: str = "mean",
        ephe_path: Optional[str] = None,
    ):
        """
        Initialize the ephemeris engine.

        Args:
            ayanamsa_system: Ayanamsa system to use for sidereal calculations
            node_model: "mean" (default) or "true" lunar node for Rahu/Ketu
            ephe_path: Directory with Swiss Ephemeris ``.se1`` files. Defaults
                to the ``SE_EPHE_PATH`` environment variable; without files
                Swiss Ephemeris uses the Moshier analytic ephemeris.
        """
        self.ayanamsa_system = resolve_ayanamsa_system(ayanamsa_system)
        self.node_model = resolve_node_model(node_model)
        self.ephe_path = ephe_path or os.environ.get("SE_EPHE_PATH")
        if self.ephe_path:
            swe.set_ephe_path(self.ephe_path)
        self.sidereal_mode_set = True
        self.last_retflag: Optional[int] = None
        # Probe a planet once; the model is immutable for the engine's life.
        _, retflag = self._calc(2451545.0, swe.SUN)
        self._ephemeris_model = ephemeris_model_from_retflag(retflag)

    @property
    def ephemeris_model(self) -> str:
        """Return "swieph", "moshier" or "jpl", read once from the Sun."""
        return self._ephemeris_model

    # ------------------------------------------------------------------ core
    def _calc(self, julian_day: float, body: int, flags: int = SIDEREAL_FLAGS):
        set_sidereal_mode(self.ayanamsa_system)
        xx, retflag = swe.calc_ut(julian_day, body, flags)
        self.last_retflag = retflag
        return xx, retflag

    @property
    def node_body(self) -> int:
        """Swiss Ephemeris body used for Rahu under the current node model."""
        return swe.MEAN_NODE if self.node_model == "mean" else swe.TRUE_NODE

    def datetime_to_julian_day(self, dt: datetime) -> float:
        """
        Convert a timezone-aware datetime to a Julian day (UT).

        Raises:
            ValueError: If ``dt`` is naive.
        """
        return calculate_jd(dt)

    def get_ayanamsa(self, julian_day: float) -> float:
        """Return the ayanamsa in degrees from ``swe.get_ayanamsa_ut``."""
        set_sidereal_mode(self.ayanamsa_system)
        return float(swe.get_ayanamsa_ut(julian_day))

    def get_ayanamsa_offset(self, julian_day: float) -> float:
        """Alias of :meth:`get_ayanamsa`."""
        return self.get_ayanamsa(julian_day)

    def get_heliocentric_position(
        self, julian_day: float, planet: Union[Planet, int, str]
    ) -> Dict:
        """
        Calculate the heliocentric (tropical) position of a planet.

        Used for the physical-coupling hypothesis; heliocentric positions are
        not used for any Vedic quantity.
        """
        body = SWE_BODIES[self._resolve_planet(planet)]
        flags = swe.FLG_SWIEPH | swe.FLG_HELCTR | swe.FLG_SPEED
        xx, _ = self._calc(julian_day, body, flags)
        longitude, latitude, distance = xx[0], xx[1], xx[2]
        return {
            "longitude": longitude % 360,
            "latitude": latitude,
            "distance": distance,
            "longitude_speed": xx[3],
            "x_vector": distance
            * math.cos(math.radians(longitude))
            * math.cos(math.radians(latitude)),
            "y_vector": distance
            * math.sin(math.radians(longitude))
            * math.cos(math.radians(latitude)),
            "z_vector": distance * math.sin(math.radians(latitude)),
        }

    # ------------------------------------------------------------- positions
    def _resolve_planet(self, planet: Union[Planet, int, str]) -> Planet:
        if isinstance(planet, Planet):
            return planet
        if isinstance(planet, str):
            try:
                return to_planet(planet)
            except KeyError:
                raise ValueError(
                    f"Unknown planet '{planet}'. Valid names: "
                    f"{[p.name.lower() for p in Planet]}"
                ) from None
        if isinstance(planet, int):
            for p in Planet:
                if p.value == planet:
                    return p
            if planet in (swe.MEAN_NODE, swe.TRUE_NODE):
                return Planet.RAHU
        raise ValueError(f"Unknown planet identifier {planet!r}")

    @staticmethod
    def _position_record(xx, sun_longitude: Optional[float], planet: Planet):
        longitude = xx[0] % 360.0
        sign_index, sign_name, degrees_in_sign = get_zodiac_sign(longitude)
        retrograde = xx[3] < 0
        combust = (
            False
            if sun_longitude is None
            else is_combust(planet, longitude, sun_longitude, retrograde)
        )
        return {
            "longitude": longitude,
            "latitude": xx[1],
            "distance": xx[2],
            "longitude_speed": xx[3],
            "sign": sign_index,
            "sign_name": sign_name,
            "degrees_in_sign": degrees_in_sign,
            "retrograde": retrograde,
            "combust": combust,
            "sun_longitude": sun_longitude,
        }

    def get_planet_position(
        self, julian_day: float, planet: Union[Planet, int, str]
    ) -> Dict:
        """
        Calculate the sidereal position of one graha.

        Args:
            julian_day: Julian day number (UT)
            planet: Planet enum, name ("sun", "Ketu", ...) or Swiss Ephemeris
                body number (MEAN_NODE/TRUE_NODE resolve to Rahu under the
                engine's node model)

        Returns:
            Dictionary with longitude, latitude, distance, longitude_speed,
            sign, sign_name, degrees_in_sign, retrograde, combust and
            sun_longitude.

        Raises:
            ValueError: If planet identifier is invalid
        """
        p = self._resolve_planet(planet)
        if p in (Planet.RAHU, Planet.KETU):
            rahu, ketu = self.get_node_positions(julian_day)
            return rahu if p == Planet.RAHU else ketu
        sun_xx, _ = self._calc(julian_day, swe.SUN)
        xx = sun_xx if p == Planet.SUN else self._calc(julian_day, SWE_BODIES[p])[0]
        return self._position_record(xx, sun_xx[0] % 360.0, p)

    def get_node_positions(
        self, julian_day: float, node_type: Optional[str] = None
    ) -> Tuple[Dict, Dict]:
        """
        Calculate Rahu (north node) and Ketu (south node).

        This is the single place where Ketu is derived: Ketu = Rahu + 180.

        Args:
            julian_day: Julian day number (UT)
            node_type: Must equal the engine's ``node_model`` if given; the
                node model is an engine setting, not a per-call choice.

        Returns:
            Tuple of (rahu_position, ketu_position) dictionaries
        """
        if node_type is not None and resolve_node_model(node_type) != self.node_model:
            raise ValueError(
                f"node_type {node_type!r} differs from the engine node_model "
                f"{self.node_model!r}; create an engine with that node_model"
            )
        xx, _ = self._calc(julian_day, self.node_body)
        rahu = self._position_record(xx, None, Planet.RAHU)
        ketu_xx = ((xx[0] + 180.0) % 360.0, -xx[1], xx[2], xx[3], -xx[4], xx[5])
        ketu = self._position_record(ketu_xx, None, Planet.KETU)
        return rahu, ketu

    def is_retrograde(self, julian_day: float, planet: Union[Planet, int, str]) -> bool:
        """Return True if the planet's longitude velocity is negative."""
        return bool(self.get_planet_position(julian_day, planet)["retrograde"])

    def is_combust(self, julian_day: float, planet: Union[Planet, int, str]) -> bool:
        """Return True if the planet is within its combustion orb of the Sun."""
        return bool(self.get_planet_position(julian_day, planet)["combust"])

    def get_all_planet_positions(
        self, julian_day: float, node_type: Optional[str] = None
    ) -> PlanetDict:
        """
        Calculate positions for all nine grahas.

        Returns:
            :class:`PlanetDict` keyed by :class:`Planet` (name lookups such as
            ``positions["SUN"]`` are also accepted).
        """
        positions = PlanetDict()
        sun_xx, _ = self._calc(julian_day, swe.SUN)
        sun_lon = sun_xx[0] % 360.0
        for p in PLANET_ORDER[:7]:
            xx = sun_xx if p == Planet.SUN else self._calc(julian_day, SWE_BODIES[p])[0]
            positions[p] = self._position_record(xx, sun_lon, p)
        rahu, ketu = self.get_node_positions(julian_day, node_type)
        positions[Planet.RAHU] = rahu
        positions[Planet.KETU] = ketu
        return positions

    def _planet_name_to_constant(self, planet_name: str) -> int:
        """Return the Swiss Ephemeris body for a planet name (Rahu per node model).

        Ketu has no Swiss Ephemeris body and raises ValueError; use
        :meth:`get_node_positions`.
        """
        p = self._resolve_planet(planet_name)
        if p == Planet.KETU:
            raise ValueError("Ketu has no Swiss Ephemeris body; it is Rahu + 180")
        if p == Planet.RAHU:
            return self.node_body
        return SWE_BODIES[p]

    def get_ephemeris_info(self) -> Dict:
        """Return the engine configuration for a run manifest."""
        return {
            "swisseph_available": True,
            "sidereal_mode_set": True,
            "ayanamsa_system": self.ayanamsa_system.value,
            "node_model": self.node_model,
            "ephemeris_model": self.ephemeris_model,
            "flags": "FLG_SWIEPH|FLG_SPEED|FLG_SIDEREAL",
            "version": swe.version,
        }
