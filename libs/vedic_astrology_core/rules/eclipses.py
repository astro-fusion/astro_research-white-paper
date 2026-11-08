"""Solar and lunar eclipses from the Swiss Ephemeris.

``swe.sol_eclipse_when_glob`` and ``swe.lun_eclipse_when`` give the time of
greatest eclipse; the sidereal longitude of the Sun (solar) or the Moon
(lunar) at that instant places the eclipse in a sign and nakshatra.
"""

from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from typing import List, Tuple

import swisseph as swe

from ..utils.datetime_utils import julian_day_to_datetime
from .context import get_engine

_KIND_NAMES = (
    (swe.ECL_TOTAL, "total"),
    (swe.ECL_ANNULAR, "annular"),
    (swe.ECL_PARTIAL, "partial"),
    (swe.ECL_PENUMBRAL, "penumbral"),
)


@dataclass(frozen=True)
class Eclipse:
    """One eclipse at its greatest phase."""

    kind: str  # "solar" or "lunar"
    subtype: str  # total, annular, partial, penumbral (hybrid = total)
    jd: float
    longitude: float  # sidereal: the Sun for solar, the Moon for lunar

    @property
    def moment(self) -> datetime:
        """UTC instant of greatest eclipse."""
        return julian_day_to_datetime(self.jd)


def _subtype(flag: int) -> str:
    for bit, name in _KIND_NAMES:
        if flag & bit:
            return name
    return "eclipse"


@lru_cache(maxsize=4096)
def _search(jd_start: float, jd_end: float, kind: str) -> Tuple[Eclipse, ...]:
    engine = get_engine()
    found: List[Eclipse] = []
    t = jd_start
    while t < jd_end:
        if kind == "solar":
            flag, tret = swe.sol_eclipse_when_glob(t, swe.FLG_SWIEPH, 0, False)
            body = "SUN"
        else:
            flag, tret = swe.lun_eclipse_when(t, swe.FLG_SWIEPH, 0, False)
            body = "MOON"
        peak = tret[0]
        if peak > jd_end or peak <= 0:
            break
        lon = engine.get_planet_position(peak, body)["longitude"]
        found.append(Eclipse(kind, _subtype(flag), peak, lon))
        t = peak + 1.0
    return tuple(found)


def eclipses_between(
    jd_start: float, jd_end: float, kind: str = "any"
) -> List[Eclipse]:
    """Eclipses whose greatest phase lies in [jd_start, jd_end], in time order.

    Args:
        kind: "solar", "lunar" or "any".
    """
    kinds = ("solar", "lunar") if kind == "any" else (kind,)
    out: List[Eclipse] = []
    for k in kinds:
        out.extend(_search(round(jd_start, 6), round(jd_end, 6), k))
    return sorted(out, key=lambda e: e.jd)


__all__ = ["Eclipse", "eclipses_between"]
