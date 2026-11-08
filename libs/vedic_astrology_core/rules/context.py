"""Evaluation context: everything a predicate may look at.

A context holds the sky at one moment (sidereal positions from the corrected
:class:`EphemerisEngine`), optionally a place (needed for the Lagna and for
sunrise), and optionally a natal chart (a person's or a nation's) for dasha
and transit-to-natal predicates. Every quantity is computed lazily and
cached, so a rule only pays for what it uses.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

import pytz
import swisseph as swe

from ..astrology.chart import compute_sidereal_houses, get_nakshatra
from ..astrology.ephemeris import EphemerisEngine
from ..config.constants import Planet, PlanetDict
from ..dasha.vimshottari import compute_vimshottari_nested_periods
from ..utils.datetime_utils import require_aware
from .vocabulary import LAGNA, SIGN_NAMES, to_planet_enum


class MissingInputError(ValueError):
    """A predicate needs a place or a natal chart the caller did not give."""


@dataclass(frozen=True)
class Location:
    """A place on Earth: latitude, longitude (east positive), IANA time zone."""

    lat: float
    lon: float
    tz: str = "UTC"


_ENGINES: Dict[str, EphemerisEngine] = {}


def get_engine(node_model: str = "mean") -> EphemerisEngine:
    """Return a shared Lahiri engine for a node model ("mean" or "true")."""
    if node_model not in _ENGINES:
        _ENGINES[node_model] = EphemerisEngine(node_model=node_model)
    return _ENGINES[node_model]


def fmt_lon(longitude: float) -> str:
    """Format a sidereal longitude as "Cancer 5.2 deg"."""
    lon = longitude % 360.0
    return f"{SIGN_NAMES[int(lon // 30)]} {lon % 30:.1f} deg"


@dataclass
class Sky:
    """The sidereal sky at one instant, seen from an optional place."""

    moment: datetime
    place: Optional[Location] = None
    node_model: str = "mean"
    _positions: Optional[PlanetDict] = field(default=None, repr=False)
    _ascendant: Optional[float] = field(default=None, repr=False)

    def __post_init__(self) -> None:
        """Reject naive datetimes."""
        require_aware(self.moment, "moment")

    @classmethod
    def from_positions(cls, positions: Dict, moment: Optional[datetime] = None):
        """Build a sky from precomputed positions (no moment-based predicates)."""
        sky = cls.__new__(cls)
        sky.moment = moment  # type: ignore[assignment]
        sky.place = None
        sky.node_model = "mean"
        sky._positions = PlanetDict(positions)
        sky._ascendant = None
        return sky

    @property
    def engine(self) -> EphemerisEngine:
        """The ephemeris engine for this sky's node model."""
        return get_engine(self.node_model)

    @property
    def jd(self) -> float:
        """Julian day (UT) of the moment."""
        if self.moment is None:
            raise MissingInputError("this predicate needs a moment, not positions")
        return self.engine.datetime_to_julian_day(self.moment)

    @property
    def positions(self) -> PlanetDict:
        """Sidereal positions of the nine grahas, keyed by Planet."""
        if self._positions is None:
            self._positions = self.engine.get_all_planet_positions(self.jd)
        return self._positions

    @property
    def ascendant(self) -> float:
        """Sidereal ascendant longitude; needs a place."""
        if self._ascendant is None:
            if self.place is None:
                raise MissingInputError("the Lagna needs a place: give lat, lon and tz")
            _cusps, asc, _mc, _code = compute_sidereal_houses(
                self.jd, self.place.lat, self.place.lon, "W"
            )
            self._ascendant = asc
        return self._ascendant

    def record(self, planet: str) -> Dict:
        """Position record of a planet (longitude, speed, retrograde, ...)."""
        return self.positions[to_planet_enum(planet)]

    def lon(self, point: str) -> float:
        """Sidereal longitude of a planet or of the Lagna."""
        if point == LAGNA:
            return self.ascendant
        return float(self.record(point)["longitude"])

    def sign(self, point: str) -> int:
        """Sign index (Aries = 0) of a planet or the Lagna."""
        return int(self.lon(point) % 360.0 // 30)

    def speed(self, planet: str) -> float:
        """Longitude speed in degrees per day."""
        return float(self.record(planet)["longitude_speed"])

    def nakshatra(self, point: str) -> Dict:
        """Nakshatra record (index, name, lord, pada) of a point."""
        return get_nakshatra(self.lon(point))

    def describe(self, point: str) -> str:
        """Plain words: "Jupiter is in Cancer 5.2 deg"."""
        name = "the Lagna" if point == LAGNA else point
        return f"{name} is in {fmt_lon(self.lon(point))}"

    def local_time(self) -> datetime:
        """Return the moment in the place's time zone (or its own offset)."""
        if self.place is not None:
            return self.moment.astimezone(pytz.timezone(self.place.tz))
        return self.moment


@dataclass
class EvalContext:
    """What a predicate sees: the sky now, and optionally a natal chart."""

    sky: Sky
    natal: Optional[Sky] = None
    _dasha: Dict[int, list] = field(default_factory=dict, repr=False)

    @classmethod
    def at(
        cls,
        moment: datetime,
        place: Optional[Location] = None,
        natal: Optional[Tuple[datetime, Optional[Location]]] = None,
        node_model: str = "mean",
    ) -> "EvalContext":
        """Build a context for ``moment`` at ``place`` with an optional natal."""
        natal_sky = None
        if natal is not None:
            natal_sky = Sky(natal[0], natal[1], node_model)
        return cls(Sky(moment, place, node_model), natal_sky)

    def require_natal(self) -> Sky:
        """Return the natal sky or raise :class:`MissingInputError`."""
        if self.natal is None:
            raise MissingInputError(
                "this predicate needs a natal chart (a person's or a nation's): "
                "give natal moment and place"
            )
        return self.natal

    def dasha_chain(self, level: int) -> Tuple[str, ...]:
        """Vimshottari lords (mahadasha, antardasha, ...) running now."""
        natal = self.require_natal()
        if level not in self._dasha:
            self._dasha[level] = compute_vimshottari_nested_periods(
                natal.moment, natal.lon("Moon"), depth=level
            )
        for period in self._dasha[level]:
            if period["start"] <= self.sky.moment < period["end"]:
                return period["lords"]
        raise MissingInputError(
            "the moment is outside the 120-year Vimshottari cycle of the natal chart"
        )


def sunrise_before(moment: datetime, place: Location) -> Optional[datetime]:
    """Return the most recent local sunrise at or before ``moment``.

    Uses ``swe.rise_trans`` (upper limb, standard refraction), the convention
    of most pancangas. Returns None where the Sun does not rise (polar day or
    night).
    """
    jd = get_engine().datetime_to_julian_day(moment)
    start = jd - 1.5
    last = None
    for _ in range(4):
        res, tret = swe.rise_trans(
            start, swe.SUN, swe.CALC_RISE, (place.lon, place.lat, 0.0)
        )
        if res != 0 or tret[0] > jd:
            break
        last = tret[0]
        start = tret[0] + 0.01
    if last is None:
        return None
    epoch = datetime(1970, 1, 1, tzinfo=pytz.utc)
    return epoch + timedelta(days=last - 2440587.5)


__all__ = [
    "EvalContext",
    "Location",
    "MissingInputError",
    "Planet",
    "Sky",
    "fmt_lon",
    "get_engine",
    "sunrise_before",
]
