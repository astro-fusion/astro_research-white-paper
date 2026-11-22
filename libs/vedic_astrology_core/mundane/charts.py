"""Founding chart table for the retrospective mundane engine (ADR-006 WP-50).

For one registry chart and a list of vargas, return the lagna and the nine
grahas with their sign in each varga, the house counted from that varga's
lagna (whole sign) and the dignity.

Rules kept here:

* Signs come from ``astrology.divisional.varga_sign`` only.
* A varga is computed only if its method entry (``varga.d<N>``) is in the
  catalogue and has an implementation. D5, D6 and D8 have none, so asking for
  them raises ``MethodNotCited`` ("not cited").
* A date-only chart has no lagna and no houses: the grahas are placed at local
  noon of the founding date and only their signs are given.
* D2 (Parashara hora) has two signs, so it returns the hora lord (Sun or Moon)
  and no houses and no dignity.
* A grade X chart (disputed date) is refused.

The stability check (WP-51) can pass ``moment`` to evaluate the same chart at
another instant inside the founding-time window.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, time, timedelta, timezone
from typing import Any, Dict, List, Optional, Sequence
from zoneinfo import ZoneInfo

from ..astrology.divisional import varga_sign
from ..config.constants import Planet
from ..rules.context import Location, Sky
from ..rules.predicates.placement import dignities_of
from ..rules.vocabulary import SIGN_NAMES, to_planet_enum
from .catalogue import Catalogue, CatalogueError, load_catalogue
from .registry import Chart, RegistryError, chart_grade

GRAHAS = ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu")
LAGNA = "Lagna"
DEFAULT_VARGAS = ("D1", "D9")
#: Fixed settings of the table (ADR-006 section 6.4); recorded in the output.
SETTINGS = {"ayanamsa": "lahiri", "node": "mean", "houses": "whole_sign"}
#: Hora lord by D2 sign index: Leo is the Sun's hora, Cancer the Moon's.
_HORA_LORD = {4: "Sun", 3: "Moon"}


@dataclass(frozen=True)
class VargaPlacement:
    """One point in one varga."""

    varga: str
    sign: int
    sign_name: str
    house: Optional[int]
    dignity: Optional[List[str]]
    hora_lord: Optional[str] = None


@dataclass(frozen=True)
class PointRow:
    """The lagna or one graha: sidereal longitude and its varga placements."""

    point: str
    longitude: float
    retrograde: Optional[bool]
    vargas: Dict[str, VargaPlacement]


@dataclass(frozen=True)
class FoundingTable:
    """Result of :func:`founding_table`."""

    chart_id: str
    grade: str
    moment_utc: datetime
    time_known: bool
    has_lagna: bool
    vargas: List[str]
    points: List[PointRow]
    settings: Dict[str, str] = field(default_factory=lambda: dict(SETTINGS))
    catalogue_sha256: str = ""

    def row(self, point: str) -> PointRow:
        for r in self.points:
            if r.point == point:
                return r
        raise KeyError(point)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["moment_utc"] = self.moment_utc.isoformat()
        return d


def varga_factor(varga: str) -> int:
    """``'D9'`` to 9; anything else is refused."""
    m = re.fullmatch(r"D([1-9][0-9]?)", str(varga))
    if not m:
        raise CatalogueError(f"bad varga name {varga!r}; expected 'D1', 'D9', ...")
    return int(m.group(1))


def _tzinfo(chart: Chart):
    if chart.time_zone == "LMT":
        return timezone(timedelta(hours=chart.lon / 15.0))
    return ZoneInfo(chart.time_zone)


def chart_moment(chart: Chart) -> datetime:
    """The instant used for the table: the founding time, or local noon if date-only."""
    founded = chart.founding_instant()
    if founded is not None:
        return founded
    noon = datetime.combine(chart.date, time(12, 0)).replace(tzinfo=_tzinfo(chart))
    return noon.astimezone(timezone.utc)


def _dignity(planet: str, sign: int, in_d1: bool, longitude: float) -> List[str]:
    """Dignity of a graha in a sign. Outside D1 only the sign is known, so
    moolatrikona (a degree range of the rashi) is not asserted."""
    lon = longitude if in_d1 else sign * 30.0 + 15.0
    found = dignities_of(to_planet_enum(planet), lon, "taurus")
    if not in_d1:
        found.discard("moolatrikona")
    return sorted(found)


def founding_table(
    chart: Chart,
    vargas: Sequence[str] = DEFAULT_VARGAS,
    *,
    moment: Optional[datetime] = None,
    catalogue: Optional[Catalogue] = None,
) -> FoundingTable:
    """Lagna and nine grahas of ``chart`` in each of ``vargas``.

    Raises ``MethodNotCited`` for a varga with no implementation (D5, D6, D8),
    ``CatalogueError`` for an unknown one, ``RegistryError`` for a grade X
    chart and ``ValueError`` for a naive ``moment``.
    """
    if chart_grade(chart) == "X":
        raise RegistryError(f"{chart.chart_id}: grade X (date disputed) is excluded")
    cat = catalogue or load_catalogue()
    names = list(dict.fromkeys(vargas))
    factors = {}
    for name in names:
        n = varga_factor(name)
        method = cat.get(f"varga.d{n}")
        method.resolve()  # raises MethodNotCited when there is no implementation
        factors[name] = n

    if moment is not None and (moment.tzinfo is None or moment.utcoffset() is None):
        raise ValueError("moment: naive datetime; timezone-aware required")
    when = (moment or chart_moment(chart)).astimezone(timezone.utc)
    time_known = chart.time is not None
    sky = Sky(when, Location(chart.lat, chart.lon, "UTC"))

    lons: List = []
    if time_known:
        lons.append((LAGNA, sky.ascendant, None))
    for g in GRAHAS:
        lons.append((g, float(sky.lon(g)), bool(sky.record(g).get("retrograde", False))))

    lagna_sign: Dict[str, int] = {}
    if time_known:
        for name, n in factors.items():
            lagna_sign[name] = varga_sign(sky.ascendant, n)

    rows: List[PointRow] = []
    for point, lon, retro in lons:
        placements: Dict[str, VargaPlacement] = {}
        for name, n in factors.items():
            sign = varga_sign(lon, n)
            if n == 2:
                placements[name] = VargaPlacement(
                    name, sign, SIGN_NAMES[sign], None, None, _HORA_LORD[sign]
                )
                continue
            house = (sign - lagna_sign[name]) % 12 + 1 if time_known else None
            dignity = None if point == LAGNA else _dignity(point, sign, n == 1, lon)
            placements[name] = VargaPlacement(name, sign, SIGN_NAMES[sign], house, dignity)
        rows.append(PointRow(point, lon, retro, placements))

    return FoundingTable(
        chart_id=chart.chart_id,
        grade=chart_grade(chart),
        moment_utc=when,
        time_known=time_known,
        has_lagna=time_known,
        vargas=names,
        points=rows,
        catalogue_sha256=cat.hash(),
    )
