"""Indian festival days computed in-house from the repo's sidereal sky.

The Gemini festival file (research/incoming/.../indian_festivals_1990_2027.csv)
is rejected: it is wrong in adhika-masa years. These functions replace it.

Calendar rules (all stated, none hidden):

* Lunar months are **amanta** (new moon to new moon), sidereal Lahiri, Swiss
  Ephemeris. A month is named after the sidereal sign the Sun occupies at its
  opening new moon (Pisces = Chaitra, Aries = Vaishakha, ... Aquarius =
  Phalguna). A month whose closing new moon finds the Sun in the same sign
  (no sankranti inside it) is **adhika**; the following month, with the same
  name, is the *nija* month. Festivals fall in nija months only.
  (A kshaya month, two sankrantis in one month, would skip a name; it is not
  special-cased.)
* Place: New Delhi (28.6139 N, 77.2090 E), civil dates in IST (UTC+5:30).
  Sunrise and sunset are the upper limb with standard refraction.
* A festival names a tithi and a day-part. The civil date chosen is the one on
  which the tithi overlaps that day-part the longest (ties go to the earlier
  date): purvahna = sunrise to local mid-day, aparahna = the fourth fifth of
  the day, pradosha = sunset to 2h24m after, udaya = the tithi in force at
  sunrise.

  - Akshaya Tritiya: Vaishakha shukla 3, purvahna.
  - Dhanteras: Ashvina krishna 13 (Kartika krishna 13 in purnimanta naming),
    pradosha; when Trayodashi covers at least 30 minutes of the pradosha of
    two dates (2015, 2016) the later date is taken. The 30-minute threshold
    is empirical: it reproduces the Delhi dates recalled for 2015-2025
    (2022: Trayodashi ends 18 minutes into the second pradosha, so the first
    date stands). Treat Dhanteras as the least settled of the four.
  - Diwali (Lakshmi Puja): Ashvina amavasya (tithi 30), pradosha. In 2024
    amavasya covers sunset on both 31 October and 1 November; 31 October
    holds the whole pradosha window and is chosen, as in most published
    Delhi panchangs (some publish 1 November).
  - Mahalaya (Sarva Pitru) Amavasya: Bhadrapada amavasya, aparahna (the
    shraddha time). Pitru
    Paksha is the krishna paksha of Bhadrapada: every civil date whose
    sunrise tithi is 16-30 of that month.
* Adhik Maas: the adhika month, as the civil dates whose sunrise falls between
  its opening and closing new moon (first date = first sunrise after the new
  moon, which is how panchangs publish it).
* Pushya days: sunrise Moon in the sidereal nakshatra Pushya (93d20m-106d40m).
  guru_pushya and ravi_pushya add Thursday and Sunday.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from functools import lru_cache
from typing import Dict, List, Optional, Tuple

import pandas as pd
import swisseph as swe

from ..astrology.ephemeris import EphemerisEngine
from ..config.constants import Planet

IST = timezone(timedelta(hours=5, minutes=30))
DELHI = (77.2090, 28.6139)  # (lon east, lat north)
TITHI_DEG = 12.0
MONTH_NAMES = (
    "Chaitra", "Vaishakha", "Jyeshtha", "Ashadha", "Shravana", "Bhadrapada",
    "Ashvina", "Kartika", "Margashirsha", "Pausha", "Magha", "Phalguna",
)  # fmt: skip
PUSHYA_RANGE = (93.0 + 20.0 / 60.0, 106.0 + 40.0 / 60.0)
PRADOSHA_HOURS = 2.4
LATE_MIN_HOURS = 0.5  # empirical: fits the recalled Delhi dates of 2015-2025, see docstring

# name -> (month number 1-12, tithi 1-30, day-part)
FESTIVALS: Dict[str, Tuple[int, int, str]] = {
    "akshaya_tritiya": (2, 3, "purvahna"),
    "dhanteras": (7, 28, "pradosha_late"),
    "diwali": (7, 30, "pradosha"),
    "mahalaya_amavasya": (6, 30, "aparahna"),
}

_ENGINE: Optional[EphemerisEngine] = None


def _engine() -> EphemerisEngine:
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = EphemerisEngine()
    return _ENGINE


def _jd_of(d: date, hour_ist: float = 0.0) -> float:
    """Julian day (UT) of local IST midnight of ``d`` plus ``hour_ist`` hours."""
    dt = datetime(d.year, d.month, d.day, tzinfo=IST) + timedelta(hours=hour_ist)
    dt = dt.astimezone(timezone.utc)
    return swe.julday(
        dt.year, dt.month, dt.day, dt.hour + dt.minute / 60 + dt.second / 3600
    )


def _date_of(jd: float) -> date:
    y, m, d, h = swe.revjul(jd)
    dt = datetime(y, m, d, tzinfo=timezone.utc) + timedelta(hours=h)
    return dt.astimezone(IST).date()


def _lons(jd: float) -> Tuple[float, float]:
    eng = _engine()
    sun = eng.get_planet_position(jd, Planet.SUN)["longitude"]
    moon = eng.get_planet_position(jd, Planet.MOON)["longitude"]
    return sun, moon


def elongation(jd: float) -> float:
    """Moon minus Sun sidereal longitude in [0, 360)."""
    sun, moon = _lons(jd)
    return (moon - sun) % 360.0


def tithi_at(jd: float) -> int:
    """Tithi 1-30 in force at ``jd``."""
    return int(elongation(jd) // TITHI_DEG) + 1


def _next_crossing(jd0: float, target: float, max_days: float = 32.0) -> float:
    """First jd after ``jd0`` where the elongation reaches ``target`` degrees (mod 360)."""
    target %= 360.0
    step = 0.25

    def gap(jd):  # signed distance in [-180, 180); the elongation grows
        return (elongation(jd) - target + 180.0) % 360.0 - 180.0

    jd = jd0
    prev = gap(jd)
    end = jd0 + max_days
    while jd < end:
        nxt = jd + step
        g = gap(nxt)
        if prev < 0.0 <= g:
            lo, hi = jd, nxt
            for _ in range(45):
                mid = 0.5 * (lo + hi)
                if gap(mid) >= 0.0:
                    hi = mid
                else:
                    lo = mid
            return hi
        jd, prev = nxt, g
    raise RuntimeError("elongation crossing not found")


@lru_cache(maxsize=None)
def _new_moons(year: int) -> Tuple[float, ...]:
    """New-moon instants (jd UT) from 1 Dec of year-1 to 1 Feb of year+1."""
    out = []
    jd = _next_crossing(_jd_of(date(year - 1, 12, 1)), 0.0)
    end = _jd_of(date(year + 1, 2, 1))
    while jd < end:
        out.append(jd)
        jd = _next_crossing(jd + 20.0, 0.0)
    return tuple(out)


def lunar_months(year: int) -> List[Dict]:
    """Amanta lunar months touching ``year``.

    Each dict: ``number`` (1 = Chaitra), ``name``, ``adhika``, ``start_jd``,
    ``end_jd``, ``start_date``, ``end_date`` (IST civil dates of the new moons).
    """
    return list(_lunar_months(int(year)))


@lru_cache(maxsize=None)
def _lunar_months(year: int) -> Tuple[Dict, ...]:
    nms = _new_moons(year)
    signs = [int(_lons(jd)[0] // 30.0) for jd in nms]
    months = []
    for i in range(len(nms) - 1):
        number = (signs[i] + 2) % 12 or 12
        months.append(
            {
                "number": number,
                "name": MONTH_NAMES[number - 1],
                "adhika": signs[i] == signs[i + 1],
                "start_jd": nms[i],
                "end_jd": nms[i + 1],
                "start_date": _date_of(nms[i]),
                "end_date": _date_of(nms[i + 1]),
            }
        )
    return tuple(months)


def _sun_events(d: date, place=DELHI) -> Tuple[float, float]:
    """(sunrise_jd, sunset_jd) of local civil date ``d``."""
    lon, lat = place
    geo = (lon, lat, 0.0)
    rise = swe.rise_trans(_jd_of(d), swe.SUN, swe.CALC_RISE, geo, 1013.25, 15.0)[1][0]
    sett = swe.rise_trans(rise, swe.SUN, swe.CALC_SET, geo, 1013.25, 15.0)[1][0]
    return rise, sett


def _window(d: date, part: str, place=DELHI) -> Tuple[float, float]:
    rise, sett = _sun_events(d, place)
    length = sett - rise
    if part == "udaya":
        return rise, rise + 1.0 / 1440.0
    if part == "purvahna":
        return rise, rise + 0.5 * length
    if part == "aparahna":
        return rise + 0.6 * length, rise + 0.8 * length
    if part in ("pradosha", "pradosha_late"):
        return sett, sett + PRADOSHA_HOURS / 24.0
    raise ValueError(f"unknown day-part {part!r}")


def tithi_interval(month: Dict, tithi: int) -> Tuple[float, float]:
    """(start_jd, end_jd) of absolute tithi 1-30 within an amanta month."""
    if not 1 <= tithi <= 30:
        raise ValueError("tithi must be 1-30")
    start = (
        month["start_jd"]
        if tithi == 1
        else _next_crossing(month["start_jd"], (tithi - 1) * TITHI_DEG)
    )
    end = month["end_jd"] if tithi == 30 else _next_crossing(start, tithi * TITHI_DEG)
    return start, end


def civil_date_for_tithi(
    start_jd: float, end_jd: float, part: str, place=DELHI
) -> date:
    """Civil date on which the tithi overlaps ``part`` longest (ties: earlier)."""
    d = _date_of(start_jd) - timedelta(days=1)
    d1 = _date_of(end_jd) + timedelta(days=1)
    best, best_ov = None, 0.0
    late = part.endswith("_late")
    while d <= d1:
        w0, w1 = _window(d, part, place)
        ov = min(end_jd, w1) - max(start_jd, w0)
        if late:  # latest date with at least LATE_MIN_HOURS of overlap
            if ov > LATE_MIN_HOURS / 24.0:
                best, best_ov = d, ov
        elif ov > best_ov + 1e-9:
            best, best_ov = d, ov
        d += timedelta(days=1)
    if best is None:  # kshaya tithi: never in force in the day-part
        best = _date_of(0.5 * (start_jd + end_jd))
    return best


def festival_dates(year: int, name: str, place=DELHI) -> List[date]:
    """Civil dates (IST) of festival ``name`` falling in calendar ``year``."""
    if name not in FESTIVALS:
        raise ValueError(f"unknown festival {name!r}; known: {sorted(FESTIVALS)}")
    number, tithi, part = FESTIVALS[name]
    out = []
    for m in lunar_months(year):
        if m["number"] != number or m["adhika"]:
            continue
        s, e = tithi_interval(m, tithi)
        d = civil_date_for_tithi(s, e, part, place)
        if d.year == year:
            out.append(d)
    return out


def pitru_paksha(year: int, place=DELHI) -> Optional[Tuple[date, date]]:
    """(first, last) civil dates whose sunrise tithi is in Bhadrapada krishna paksha."""
    for m in lunar_months(year):
        if m["number"] != 6 or m["adhika"]:
            continue
        s16, _ = tithi_interval(m, 16)
        days = []
        d = _date_of(s16) - timedelta(days=1)
        while d <= m["end_date"] + timedelta(days=1):
            rise = _sun_events(d, place)[0]
            if s16 <= rise < m["end_jd"]:
                days.append(d)
            d += timedelta(days=1)
        if days and days[0].year == year:
            return days[0], days[-1]
    return None


def adhik_maas(year: int, place=DELHI) -> List[Dict]:
    """Adhika months that start in ``year``: name, start and end civil dates."""
    out = []
    for m in lunar_months(year):
        if not m["adhika"]:
            continue
        days = []
        d = m["start_date"]
        while d <= m["end_date"] + timedelta(days=1):
            if m["start_jd"] <= _sun_events(d, place)[0] < m["end_jd"]:
                days.append(d)
            d += timedelta(days=1)
        if days and days[0].year == year:
            out.append({"name": m["name"], "start": days[0], "end": days[-1]})
    return out


def pushya_dates(start: date, end: date, place=DELHI) -> List[date]:
    """Dates in [start, end] whose sunrise Moon is in sidereal Pushya."""
    out = []
    d = start
    while d <= end:
        moon = _lons(_sun_events(d, place)[0])[1]
        if PUSHYA_RANGE[0] <= moon < PUSHYA_RANGE[1]:
            out.append(d)
        d += timedelta(days=1)
    return out


def festival_flags(index, place=DELHI) -> pd.DataFrame:
    """Boolean daily columns for a DatetimeIndex (dates are civil dates).

    Columns: akshaya_tritiya, dhanteras, diwali, mahalaya_amavasya,
    pitru_paksha, adhik_maas, pushya, guru_pushya, ravi_pushya.
    """
    idx = pd.DatetimeIndex(index)
    naive = idx.tz_localize(None) if idx.tz is not None else idx
    days = naive.normalize()
    years = sorted(set(days.year))
    point: Dict[str, set] = {k: set() for k in FESTIVALS}
    pitru, adhik = set(), set()
    for y in range(years[0], years[-1] + 1):
        for k in FESTIVALS:
            point[k].update(pd.Timestamp(d) for d in festival_dates(y, k, place))
        span = pitru_paksha(y, place)
        if span:
            pitru.update(pd.date_range(span[0], span[1]))
        for a in adhik_maas(y):
            adhik.update(pd.date_range(a["start"], a["end"]))
    pushya = {
        pd.Timestamp(d)
        for d in pushya_dates(days.min().date(), days.max().date(), place)
    }
    out = pd.DataFrame(index=idx)
    for k in FESTIVALS:
        out[k] = [v in point[k] for v in days]
    out["pitru_paksha"] = [v in pitru for v in days]
    out["adhik_maas"] = [v in adhik for v in days]
    out["pushya"] = [v in pushya for v in days]
    wd = days.day_of_week.to_numpy()
    out["guru_pushya"] = out["pushya"].to_numpy() & (wd == 3)
    out["ravi_pushya"] = out["pushya"].to_numpy() & (wd == 6)
    return out
