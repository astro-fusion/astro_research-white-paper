"""Mundane tables and helpers: Kurma Chakra, earthquake mandalas, eclipses, years.

Every table here names its source. The rule engine's predicates
(:mod:`vedic_astrology_core.rules.predicates`) read these; nothing in this
module evaluates a rule.

* :data:`KURMA_DIVISIONS` and :func:`kurma_division`: Brihat Samhita ch. 14
  (Kurma-vibhaga). Verse 1 divides the land into nine parts with three
  asterisms each, "beginning from Krittika", from the centre (Madhyadesha)
  round the east, south-east, south, south-west, west, north-west, north
  and north-east (verses 2-31; N. Chidambaram Iyer tr., 1884, read on
  wisdomlib.org 2026-11-08). Practitioners dispute the start: the
  AstroRidhis table starts with Ashwini in the north (see
  ``rules/mundane/practitioner/DISPUTES.md``), so the start is a parameter.
* :data:`MANDALAS` and :func:`mandala_of`: Brihat Samhita ch. 32
  (Bhukampa-lakshana), verses 8 (Vayu), 12 (Agni), 16 (Indra) and 20
  (Varuna), Iyer tr. 1884. As printed there the four lists of seven hold
  Uttarashadha twice (Indra and Varuna) and omit Uttara Bhadrapada; each
  of the 27 asterisms belongs to exactly one circle, so the Varuna entry is
  read as Uttara Bhadrapada (the reading also registered in
  ``studies/earthquake/hypothesis.yaml``). Abhijit, the 28th, is in Indra
  and is not one of the 27 equal nakshatras, so it is dropped.
* :func:`eclipse_magnitude`: greatest-eclipse magnitude from the Swiss
  Ephemeris (``sol_eclipse_where`` then ``sol_eclipse_how`` for a solar
  eclipse, ``lun_eclipse_how`` umbral magnitude for a lunar one).
* :data:`SAMVATSARA_NAMES` and :func:`samvatsara`: the sixty-year cycle of
  Brihat Samhita ch. 8 (Brihaspati-chara) in the luni-solar (South Indian)
  convention: the year starts at Chaitra Shukla Pratipada (the new Moon
  with the sidereal Sun in Pisces before Mesha sankranti; the earlier one
  if Chaitra is doubled), and the year beginning in 1987 is Prabhava.
"""

from datetime import datetime
from functools import lru_cache
from typing import Dict, List, Tuple

import swisseph as swe

from ..config.constants import NAKSHATRAS
from ..utils.datetime_utils import julian_day_to_datetime
from .ayanamsa import set_sidereal_mode

NAKSHATRA_NAMES = [NAKSHATRAS[i]["name"] for i in range(27)]
DIRECTIONS = (
    "centre",
    "east",
    "south_east",
    "south",
    "south_west",
    "west",
    "north_west",
    "north",
    "north_east",
)
# Brihat Samhita 14 order of the divisions, starting from the centre.
KURMA_ORDER_BS = DIRECTIONS
# AstroRidhis order: Ashwini-Bharani-Krittika in the north, then clockwise
# (north-east next, as the practitioner page states); the last triple is
# not given on the page and is read as the centre.
KURMA_ORDER_ASHWINI = (
    "north",
    "north_east",
    "east",
    "south_east",
    "south",
    "south_west",
    "west",
    "north_west",
    "centre",
)
KURMA_CONVENTIONS = {
    "krittika": (2, KURMA_ORDER_BS),
    "ashwini": (0, KURMA_ORDER_ASHWINI),
}


def kurma_division(nakshatra_index: int, start: str = "krittika") -> str:
    """Return the Kurma Chakra division of a nakshatra (0 = Ashwini).

    ``start="krittika"`` is Brihat Samhita 14.1 (Krittika, Rohini,
    Mrigashira in the centre); ``start="ashwini"`` is the practitioner
    table that puts Ashwini, Bharani, Krittika in the north.
    """
    first, order = KURMA_CONVENTIONS[start]
    return order[((nakshatra_index - first) % 27) // 3]


def kurma_table(start: str = "krittika") -> Dict[str, List[str]]:
    """Return every division with its three nakshatras."""
    out: Dict[str, List[str]] = {d: [] for d in DIRECTIONS}
    for i, name in enumerate(NAKSHATRA_NAMES):
        out[kurma_division(i, start)].append(name)
    return out


MANDALAS: Dict[str, Tuple[str, ...]] = {
    "vayu": (
        "Uttara Phalguni",
        "Hasta",
        "Chitra",
        "Swati",
        "Punarvasu",
        "Mrigashira",
        "Ashwini",
    ),
    "agni": (
        "Pushya",
        "Krittika",
        "Vishakha",
        "Bharani",
        "Magha",
        "Purva Bhadrapada",
        "Purva Phalguni",
    ),
    "indra": (
        "Shravana",
        "Dhanishta",
        "Rohini",
        "Jyeshtha",
        "Uttara Ashadha",
        "Anuradha",
    ),
    "varuna": (
        "Revati",
        "Purva Ashadha",
        "Ardra",
        "Ashlesha",
        "Mula",
        "Uttara Bhadrapada",
        "Shatabhisha",
    ),
}


def mandala_of(nakshatra_name: str) -> str:
    """Return the Brihat Samhita 32 circle (vayu, agni, indra, varuna)."""
    for mandala, names in MANDALAS.items():
        if nakshatra_name in names:
            return mandala
    raise KeyError(nakshatra_name)


# ---------------------------------------------------------------- eclipses
def eclipse_magnitude(kind: str, jd: float) -> float:
    """Magnitude at greatest eclipse (fraction of the diameter covered).

    Solar: ``sol_eclipse_where`` finds the place of greatest eclipse and
    ``sol_eclipse_how`` gives its magnitude there (above 1 for a total).
    Lunar: the umbral magnitude from ``lun_eclipse_how`` (negative for a
    penumbral-only eclipse, in which case the penumbral magnitude minus 1 is
    returned so it sorts below every umbral eclipse).
    """
    if kind == "solar":
        _flag, geopos, _attr = swe.sol_eclipse_where(jd, swe.FLG_SWIEPH)
        _flag, attr = swe.sol_eclipse_how(jd, geopos[:3], swe.FLG_SWIEPH)
        return float(attr[0])
    _flag, attr = swe.lun_eclipse_how(jd, (0.0, 0.0, 0.0), swe.FLG_SWIEPH)
    umbral, penumbral = float(attr[0]), float(attr[1])
    return umbral if umbral > 0 else penumbral - 1.0


def magnitude_strength(magnitude: float) -> float:
    """Map a magnitude to a strength in [0, 1] (penumbral-only gives 0)."""
    return float(min(1.0, max(0.0, magnitude)))


# ------------------------------------------------------------------- years
SAMVATSARA_NAMES = (
    "Prabhava",
    "Vibhava",
    "Shukla",
    "Pramoda",
    "Prajapati",
    "Angirasa",
    "Shrimukha",
    "Bhava",
    "Yuva",
    "Dhatri",
    "Ishvara",
    "Bahudhanya",
    "Pramathi",
    "Vikrama",
    "Vrisha",
    "Chitrabhanu",
    "Svabhanu",
    "Tarana",
    "Parthiva",
    "Vyaya",
    "Sarvajit",
    "Sarvadhari",
    "Virodhi",
    "Vikriti",
    "Khara",
    "Nandana",
    "Vijaya",
    "Jaya",
    "Manmatha",
    "Durmukhi",
    "Hevilambi",
    "Vilambi",
    "Vikari",
    "Sharvari",
    "Plava",
    "Shubhakrit",
    "Shobhakrit",
    "Krodhi",
    "Vishvavasu",
    "Parabhava",
    "Plavanga",
    "Kilaka",
    "Saumya",
    "Sadharana",
    "Virodhikrit",
    "Paridhavi",
    "Pramadicha",
    "Ananda",
    "Rakshasa",
    "Nala",
    "Pingala",
    "Kalayukti",
    "Siddharthi",
    "Raudra",
    "Durmati",
    "Dundubhi",
    "Rudhirodgari",
    "Raktakshi",
    "Krodhana",
    "Akshaya",
)
PRABHAVA_YEAR = 1987
LUNAR_MONTHS = (
    "Chaitra",
    "Vaishakha",
    "Jyeshtha",
    "Ashadha",
    "Shravana",
    "Bhadrapada",
    "Ashvina",
    "Kartika",
    "Margashirsha",
    "Pausha",
    "Magha",
    "Phalguna",
)
SYNODIC_MONTH = 29.530588853


def _sidereal_lon(jd: float, body: int) -> float:
    set_sidereal_mode("lahiri")
    xx, _ = swe.calc_ut(jd, body, swe.FLG_SWIEPH | swe.FLG_SIDEREAL)
    return float(xx[0])


def elongation(jd: float) -> float:
    """Moon minus Sun in degrees, [0, 360)."""
    return (_sidereal_lon(jd, swe.MOON) - _sidereal_lon(jd, swe.SUN)) % 360.0


@lru_cache(maxsize=4096)
def new_moon_at_or_before(jd: float) -> float:
    """JD (UT) of the last Sun-Moon conjunction at or before ``jd``."""
    guess = jd - elongation(jd) / 360.0 * SYNODIC_MONTH
    lo, hi = guess - 2.0, guess + 2.0
    # elongation rises from ~350 to ~10 across the conjunction
    for _ in range(50):
        mid = (lo + hi) / 2.0
        if elongation(mid) > 180.0:
            lo = mid
        else:
            hi = mid
    return hi if hi <= jd + 1e-9 else new_moon_at_or_before(guess - 3.0)


def sun_sign_at(jd: float) -> int:
    """Sidereal sign of the Sun (Aries = 0)."""
    return int(_sidereal_lon(jd, swe.SUN) // 30)


def lunar_month(jd: float) -> Tuple[str, bool, float]:
    """Amanta lunar month at ``jd``: (name, adhika, start JD).

    The month runs new Moon to new Moon and is named by the sign the
    sidereal Sun occupies at its start: Sun in Pisces names Chaitra, in
    Aries Vaishakha, and so on (the Surya Siddhanta rule as used by the
    Indian Astronomical Ephemeris). Two months that start in the same sign
    make the first one adhika (intercalary).
    """
    start = new_moon_at_or_before(jd)
    sign = sun_sign_at(start)
    nxt = new_moon_at_or_before(start + SYNODIC_MONTH + 2.0)
    adhika = sun_sign_at(nxt) == sign
    return LUNAR_MONTHS[(sign + 1) % 12], adhika, start


def year_start(gregorian_year: int) -> float:
    """JD of Chaitra Shukla Pratipada (the luni-solar new year) in that year."""
    jd = swe.julday(gregorian_year, 4, 25, 0.0)
    start = new_moon_at_or_before(jd)
    while sun_sign_at(start) != 11:  # step back to a month that starts in Pisces
        start = new_moon_at_or_before(start - 1.0)
    prev = new_moon_at_or_before(start - 1.0)
    if sun_sign_at(prev) == 11:  # doubled Chaitra: the year starts at the adhika
        start = prev
    return start


def samvatsara(jd: float) -> Tuple[str, int, datetime]:
    """Return (name, index 0-59, start of that year) for the moment ``jd``."""
    year = julian_day_to_datetime(jd).year
    start = year_start(year)
    if jd < start:
        year -= 1
        start = year_start(year)
    index = (year - PRABHAVA_YEAR) % 60
    return SAMVATSARA_NAMES[index], index, julian_day_to_datetime(start)


# --------------------------------------------------------------- distance
SWE_BODY = {
    "Sun": swe.SUN,
    "Moon": swe.MOON,
    "Mars": swe.MARS,
    "Mercury": swe.MERCURY,
    "Jupiter": swe.JUPITER,
    "Venus": swe.VENUS,
    "Saturn": swe.SATURN,
}


def geocentric_distance_au(jd: float, planet: str) -> float:
    """Geocentric distance of a visible planet in astronomical units."""
    xx, _ = swe.calc_ut(jd, SWE_BODY[planet], swe.FLG_SWIEPH)
    return float(xx[2])


__all__ = [
    "DIRECTIONS",
    "KURMA_CONVENTIONS",
    "LUNAR_MONTHS",
    "MANDALAS",
    "SAMVATSARA_NAMES",
    "eclipse_magnitude",
    "elongation",
    "geocentric_distance_au",
    "kurma_division",
    "kurma_table",
    "lunar_month",
    "magnitude_strength",
    "mandala_of",
    "new_moon_at_or_before",
    "samvatsara",
    "sun_sign_at",
    "year_start",
]
