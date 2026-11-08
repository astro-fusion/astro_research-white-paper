"""Positive and negative controls as first-class study inputs.

A null result is only worth something if the method can find a real effect
of the size in question. A study therefore reports, beside its indicators:

* a **positive control**: a time-varying driver with a documented, small,
  real effect, tested exactly like an indicator. For earthquakes this is
  tidal phase. Large earthquakes are more likely when tidal stress is high
  (Ide, Yabe and Tanaka 2016, *Nature Geoscience* 9, 834-837), and shallow
  thrust earthquakes correlate with the phase of the solid-Earth tide
  (Cochran, Vidale and Tanaka 2004, *Science* 306, 1164-1166). Two phase
  proxies are built from the sky alone: the semidiurnal phase (the Moon's
  local hour angle within ``semidiurnal_half_width_deg`` of upper or lower
  culmination) and the fortnightly spring-neap phase (Moon-Sun elongation
  within ``spring_half_width_deg`` of new or full Moon). These are proxies
  for the tide-generating potential, not resolved fault-plane stresses, so
  they can only be weaker than the published stress-based analyses. For
  floods the positive control is the monsoon season flag.
* a **negative control**: every registered indicator evaluated on a sky
  rotated by a fixed, pre-declared offset (:func:`shifted_sky`). Its test
  results should look like the null: about ``alpha`` of them nominally
  significant and none after correction.

A study states "the method detected the positive control at RR x" or "did not
detect it"; the second makes its other nulls uninformative about effects of
that size.
"""

from typing import Dict, Iterable

import numpy as np
import pandas as pd

REFERENCES: Dict[str, str] = {
    "ide2016": (
        "Ide, S., Yabe, S. and Tanaka, Y. (2016). Earthquake potential "
        "revealed by tidal influence on earthquake size-frequency statistics. "
        "Nature Geoscience 9, 834-837."
    ),
    "cochran2004": (
        "Cochran, E. S., Vidale, J. E. and Tanaka, S. (2004). Earth tides can "
        "trigger shallow thrust fault earthquakes. Science 306, 1164-1166."
    ),
}


def lunar_elongation(moon_lon, sun_lon) -> np.ndarray:
    """Return the Moon-Sun elongation in [0, 360) degrees (0 = new Moon)."""
    moon = np.asarray(moon_lon, dtype=float)
    return (moon - np.asarray(sun_lon, dtype=float)) % 360.0


def moon_hour_angle(jd_ut, lon_east_deg: float) -> np.ndarray:
    """Return the Moon's local hour angle in [0, 360) degrees.

    ``HA = LAST - RA``, with apparent sidereal time from ``swe.sidtime`` and
    the Moon's geocentric apparent right ascension from Swiss Ephemeris
    (tropical, equatorial). 0 is upper culmination, 180 lower culmination.
    """
    import swisseph as swe

    jds = np.atleast_1d(np.asarray(jd_ut, dtype=float))
    out = np.empty(len(jds))
    flags = swe.FLG_SWIEPH | swe.FLG_EQUATORIAL
    for i, jd in enumerate(jds):
        ra = swe.calc_ut(float(jd), swe.MOON, flags)[0][0]
        last = swe.sidtime(float(jd)) * 15.0 + lon_east_deg
        out[i] = (last - ra) % 360.0
    return out


def _near(angle, centres: Iterable[float], half_width: float) -> np.ndarray:
    a = np.asarray(angle, dtype=float) % 360.0
    hit = np.zeros(a.shape, dtype=bool)
    for c in centres:
        d = np.abs((a - c + 180.0) % 360.0 - 180.0)
        hit |= d <= half_width
    return hit


def tidal_phase_indicators(
    hour_angle,
    elongation,
    semidiurnal_half_width_deg: float = 45.0,
    spring_half_width_deg: float = 45.0,
) -> Dict[str, np.ndarray]:
    """Return the high-tidal-stress phase indicators.

    Keys: ``tide_semidiurnal_peak`` (hour angle near 0 or 180),
    ``tide_spring`` (elongation near 0 or 180) and ``tide_spring_and_peak``
    (both). With the default half widths each single indicator is active half
    of the time and the combined one a quarter.
    """
    peak = _near(hour_angle, (0.0, 180.0), semidiurnal_half_width_deg)
    spring = _near(elongation, (0.0, 180.0), spring_half_width_deg)
    return {
        "tide_semidiurnal_peak": peak,
        "tide_spring": spring,
        "tide_spring_and_peak": peak & spring,
    }


def shifted_sky(frame: pd.DataFrame, offset_steps: int) -> pd.DataFrame:
    """Return ``frame`` with every column rotated by the same fixed offset.

    The index (the time grid and therefore the events) stays put; the sky
    moves. Used as the negative control: no configuration on a rotated sky
    can carry a real astrological signal.

    Raises:
        ValueError: If the offset is zero modulo the length.
    """
    n = len(frame)
    k = int(offset_steps) % max(n, 1)
    if k == 0:
        raise ValueError("offset must be non-zero modulo the series length")
    out = pd.DataFrame(
        {c: np.roll(frame[c].to_numpy(), k) for c in frame.columns}, index=frame.index
    )
    out.attrs = dict(frame.attrs)
    return out


def monsoon_flag(index, months=(6, 7, 8, 9)) -> np.ndarray:
    """Return True for dates in the South Asian monsoon months (June-September)."""
    idx = pd.DatetimeIndex(index)
    return np.isin(idx.month, list(months))
