"""Solar and lunar eclipses from the Swiss Ephemeris.

``swe.sol_eclipse_when_glob`` and ``swe.lun_eclipse_when`` give the time of
greatest eclipse; the sidereal longitude of the Sun (solar) or the Moon
(lunar) at that instant places the eclipse in a sign and nakshatra.

Speed (performance only, results unchanged). A rule evaluated on an hourly
grid asks for the eclipses of a new window at every step, and every window
ran its own Swiss Ephemeris search (about 3 ms per kind), so an eclipse rule
on the 1976-2010 hourly earthquake grid took about an hour per sky and its
placebo skies days. ``eclipses_between`` now reads a catalogue built once per
ten-year block by the same chained search as ``_search`` (next eclipse after
t, then after its peak plus one day). The search is deterministic per
lunation, so the catalogue holds the very floats a direct search returns.
The one start-dependent case is an eclipse peaking within about 1e-4 day of
the window's start (the ephemeris skips it): a window that starts within
``_EDGE`` days of a catalogued peak, and any catalogue failure, falls back to
the direct search. tests/test_rules_eclipse_catalogue.py checks equality with
the direct search on thousands of windows, edge starts included.
"""

import math
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from typing import List, Optional, Tuple

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


#: Catalogue block length (days) and origin (J2000). Block i owns the peaks in
#: (anchor_i + 1, anchor_i+1 + 1]; its chain starts at anchor_i, so every peak
#: it owns lies more than a day after the chain's start.
_BLOCK_DAYS = 3652.5
_BLOCK_EPOCH = 2451545.0
#: A window starting this close (days) to a catalogued peak is searched directly.
_EDGE = 0.01


def _next_peak(t: float, kind: str) -> Tuple[int, float]:
    """(flag, peak) of the next eclipse after t: the call ``_search`` makes."""
    if kind == "solar":
        flag, tret = swe.sol_eclipse_when_glob(t, swe.FLG_SWIEPH, 0, False)
    else:
        flag, tret = swe.lun_eclipse_when(t, swe.FLG_SWIEPH, 0, False)
    return flag, tret[0]


@lru_cache(maxsize=None)
def _block(index: int, kind: str) -> Tuple[Tuple[float, int], ...]:
    """(peak, flag) of the eclipses one block owns, from the chained search of ``_search``."""
    anchor = _BLOCK_EPOCH + index * _BLOCK_DAYS
    lo, hi = anchor + 1.0, anchor + _BLOCK_DAYS + 1.0
    out = []
    t = anchor
    while True:
        flag, peak = _next_peak(t, kind)
        if peak <= 0:
            raise ValueError("eclipse search returned no peak")
        if peak > hi:
            break
        if peak > lo:
            out.append((peak, flag))
        t = peak + 1.0
    return tuple(out)


def _catalogue(jd_start: float, jd_end: float, kind: str) -> Optional[Tuple[Eclipse, ...]]:
    """``_search(jd_start, jd_end, kind)`` read from the catalogue; None where only the direct search is exact."""
    if not jd_start < jd_end:
        return None
    first = math.floor((jd_start - 1.0 - _BLOCK_EPOCH) / _BLOCK_DAYS)
    last = math.floor((jd_end - _BLOCK_EPOCH) / _BLOCK_DAYS)
    peaks = []
    for i in range(first, last + 1):
        for peak, flag in _block(i, kind):
            if abs(peak - jd_start) <= _EDGE:
                return None  # the ephemeris may skip a peak at the very start
            if jd_start < peak <= jd_end:
                peaks.append((peak, flag))
    if not peaks:
        return ()
    engine = get_engine()
    body = "SUN" if kind == "solar" else "MOON"
    return tuple(Eclipse(kind, _subtype(flag), peak, engine.get_planet_position(peak, body)["longitude"])
                 for peak, flag in peaks)


def _eclipses(jd_start: float, jd_end: float, kind: str) -> Tuple[Eclipse, ...]:
    try:
        got = _catalogue(jd_start, jd_end, kind)
    except Exception:  # noqa: BLE001 - any catalogue failure: the direct search decides
        got = None
    return _search(jd_start, jd_end, kind) if got is None else got


def eclipses_between(
    jd_start: float, jd_end: float, kind: str = "any"
) -> List[Eclipse]:
    """Eclipses whose greatest phase lies in [jd_start, jd_end], in time order.

    Args:
        kind: "solar", "lunar" or "any".

    Equal to the direct chained search ``_search`` (see the module note).
    """
    kinds = ("solar", "lunar") if kind == "any" else (kind,)
    out: List[Eclipse] = []
    for k in kinds:
        out.extend(_eclipses(round(jd_start, 6), round(jd_end, 6), k))
    return sorted(out, key=lambda e: e.jd)


__all__ = ["Eclipse", "eclipses_between"]
