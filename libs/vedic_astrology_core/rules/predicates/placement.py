"""Placement predicates: sign, house, nakshatra, dignity, varga, longitude."""

from typing import List, Literal, Optional, Set

from pydantic import Field, field_validator

from ...astrology.divisional import VARGA_FACTORS, varga_sign as _varga_sign
from ...config.constants import Planet
from ...dignity.exaltation_matrix import (
    OWN_SIGNS_TABLE,
    is_in_debilitation,
    is_in_exaltation,
    is_in_moolatrikona,
)
from ...dignity.friendship_matrix import NAISARGIKA_MAITRI, FriendshipType
from ..context import EvalContext, fmt_lon
from ..vocabulary import NAKSHATRA_NAMES, SIGN_NAMES, ordinal, to_planet_enum
from . import (
    HouseList,
    NakshatraList,
    Outcome,
    Params,
    PlanetList,
    PlanetName,
    PointName,
    SignList,
    house_from,
    point_label,
    predicate,
)

KENDRAS = [1, 4, 7, 10]
TRIKONAS = [1, 5, 9]

# Lord of each sign, Aries first (BPHS, chapter on the rashis).
SIGN_LORDS = [
    "Mars",
    "Venus",
    "Mercury",
    "Moon",
    "Sun",
    "Mercury",
    "Venus",
    "Mars",
    "Jupiter",
    "Saturn",
    "Saturn",
    "Jupiter",
]


class InSign(Params):
    """Parameters of ``in_sign``."""

    planet: PointName
    signs: SignList


@predicate(
    "in_sign",
    InSign,
    shorthand="signs",
    category="placement",
    example={"in_sign": {"planet": "Jupiter", "signs": ["Cancer"]}},
)
def in_sign(ctx: EvalContext, p: InSign) -> Outcome:
    """Check that the planet (or the Lagna) occupies one of the listed sidereal signs.

    Signs are the twelve 30-degree rashis of the sidereal (Lahiri) zodiac,
    Aries starting at 0 degrees.
    """
    sign = SIGN_NAMES[ctx.sky.sign(p.planet)]
    held = sign in p.signs
    verdict = "one of" if held else "not one of"
    return Outcome(
        held, f"{ctx.sky.describe(p.planet)}, {verdict} {', '.join(p.signs)}"
    )


class InHouse(Params):
    """Parameters of ``in_house``."""

    planet: PlanetName
    houses: HouseList


@predicate(
    "in_house",
    InHouse,
    needs=("place",),
    shorthand="houses",
    category="placement",
    example={"in_house": {"planet": "Saturn", "houses": [10]}},
)
def in_house(ctx: EvalContext, p: InHouse) -> Outcome:
    """Check that the planet is in one of the listed houses counted from the Lagna.

    Houses are whole signs (bhava = rashi, the Parashari default): the sign
    rising is the 1st house, the next sign the 2nd, and so on.
    """
    house = house_from(ctx.sky.sign("Lagna"), ctx.sky.sign(p.planet))
    held = house in p.houses
    return Outcome(
        held,
        f"{ctx.sky.describe(p.planet)}, the {ordinal(house)} house from the Lagna "
        f"in {SIGN_NAMES[ctx.sky.sign('Lagna')]}"
        f"{'' if held else ', not one of ' + _houses(p.houses)}",
    )


class InHouseFrom(Params):
    """Parameters of ``in_house_from``."""

    planet: PointName
    from_: PointName = Field(alias="from")
    houses: HouseList


def _houses(houses: List[int]) -> str:
    return ", ".join(ordinal(h) for h in houses)


def _relative(ctx: EvalContext, planet: str, origin: str, wanted: List[int], what: str):
    house = house_from(ctx.sky.sign(origin), ctx.sky.sign(planet))
    held = house in wanted
    origin_words = (
        f"{point_label(origin)} in {SIGN_NAMES[ctx.sky.sign(origin)]}"
        if planet != origin
        else point_label(origin)
    )
    tail = f"which is {'' if held else 'not '}{what}"
    return Outcome(
        held,
        f"{ctx.sky.describe(planet)}, {ordinal(house)} from {origin_words}, {tail}",
    )


@predicate(
    "in_house_from",
    InHouseFrom,
    category="placement",
    example={"in_house_from": {"planet": "Moon", "from": "Sun", "houses": [3]}},
)
def in_house_from(ctx: EvalContext, p: InHouseFrom) -> Outcome:
    """Check that the planet is in one of the listed houses counted from another point.

    Counting is by whole sign, inclusive: a planet in the same sign as the
    reference is in the 1st from it, the next sign is the 2nd, and so on
    (the Parashari practice of reckoning bhavas from the Lagna, the Moon
    (Chandra Lagna), the Sun (Surya Lagna) or any planet).
    """
    return _relative(
        ctx, p.planet, p.from_, p.houses, f"one of the {_houses(p.houses)}"
    )


class FromPoint(Params):
    """Parameters of ``in_kendra_from`` and ``in_trikona_from``."""

    planet: PointName
    from_: PointName = Field(alias="from")


@predicate(
    "in_kendra_from",
    FromPoint,
    shorthand="from",
    category="placement",
    example={"in_kendra_from": {"planet": "Jupiter", "from": "Moon"}},
)
def in_kendra_from(ctx: EvalContext, p: FromPoint) -> Outcome:
    """Check that the planet is in a kendra (1st, 4th, 7th or 10th) from the point.

    Kendras (angles) are counted by whole sign from the reference, so a
    planet at Aries 29 deg and one at Cancer 28 deg are 4th from each other
    even though they are only 89 degrees apart.
    """
    return _relative(ctx, p.planet, p.from_, KENDRAS, "a kendra (1, 4, 7, 10)")


@predicate(
    "in_trikona_from",
    FromPoint,
    shorthand="from",
    category="placement",
    example={"in_trikona_from": {"planet": "Venus", "from": "Lagna"}},
)
def in_trikona_from(ctx: EvalContext, p: FromPoint) -> Outcome:
    """Check that the planet is in a trikona (1st, 5th, 9th) from the point."""
    return _relative(ctx, p.planet, p.from_, TRIKONAS, "a trikona (1, 5, 9)")


class InNakshatra(Params):
    """Parameters of ``in_nakshatra``."""

    planet: PointName
    nakshatras: NakshatraList


@predicate(
    "in_nakshatra",
    InNakshatra,
    shorthand="nakshatras",
    category="placement",
    example={"in_nakshatra": {"planet": "Saturn", "nakshatras": ["Krittika"]}},
)
def in_nakshatra(ctx: EvalContext, p: InNakshatra) -> Outcome:
    """Check that the point lies in one of the listed nakshatras.

    The 27 nakshatras are equal arcs of 13 deg 20 min of the sidereal
    zodiac, Ashwini starting at 0 deg Aries.
    """
    nak = ctx.sky.nakshatra(p.planet)
    held = nak["name"] in p.nakshatras
    verdict = "one of" if held else "not one of"
    return Outcome(
        held,
        f"{ctx.sky.describe(p.planet)}, in {nak['name']} pada {nak['pada']}, "
        f"{verdict} {', '.join(p.nakshatras)}",
    )


class NakshatraLordIs(Params):
    """Parameters of ``nakshatra_lord_is``."""

    planet: PointName
    lords: PlanetList


@predicate(
    "nakshatra_lord_is",
    NakshatraLordIs,
    shorthand="lords",
    category="placement",
    example={"nakshatra_lord_is": {"planet": "Moon", "lords": ["Saturn"]}},
)
def nakshatra_lord_is(ctx: EvalContext, p: NakshatraLordIs) -> Outcome:
    """Check that the lord of the point's nakshatra is one of the listed planets.

    Nakshatra lords follow the Vimshottari order (Ketu, Venus, Sun, Moon,
    Mars, Rahu, Jupiter, Saturn, Mercury), repeated three times from Ashwini.
    """
    nak = ctx.sky.nakshatra(p.planet)
    lord = nak["lord"].name.title()
    held = lord in p.lords
    return Outcome(
        held,
        f"{ctx.sky.describe(p.planet)}, in {nak['name']}, ruled by {lord}"
        f"{'' if held else ', not ' + ' or '.join(p.lords)}",
    )


Dignity = Literal[
    "own", "exaltation", "debilitation", "moolatrikona", "friend", "enemy", "neutral"
]


class DignityIn(Params):
    """Parameters of ``dignity_in``."""

    planet: PlanetName
    dignities: List[Dignity] = Field(min_length=1)
    rahu_exalted_in: Literal["taurus", "gemini"] = "taurus"

    @field_validator("dignities", mode="before")
    @classmethod
    def _listify(cls, value):
        return value if isinstance(value, list) else [value]


def dignities_of(planet: Planet, longitude: float, rahu_exalted_in: str) -> Set[str]:
    """Every dignity that applies to ``planet`` at ``longitude``.

    Exaltation and debilitation are by whole sign; moolatrikona by its
    degree range; own sign by rulership. Friend, enemy and neutral (the
    natural relation, naisargika maitri, to the sign lord) apply only when
    none of the four above does.
    """
    found = set()
    if is_in_exaltation(longitude, planet, rahu_exalted_in):
        found.add("exaltation")
    if is_in_debilitation(longitude, planet, rahu_exalted_in):
        found.add("debilitation")
    if is_in_moolatrikona(longitude % 360.0, planet):
        found.add("moolatrikona")
    sign = int(longitude % 360.0 // 30)
    if sign in OWN_SIGNS_TABLE.get(planet, []):
        found.add("own")
    if not found:
        lord = to_planet_enum(SIGN_LORDS[sign])
        relation = NAISARGIKA_MAITRI[planet][lord]
        found.add(
            {
                FriendshipType.NATURAL_FRIEND: "friend",
                FriendshipType.NATURAL_ENEMY: "enemy",
            }.get(relation, "neutral")
        )
    return found


@predicate(
    "dignity_in",
    DignityIn,
    shorthand="dignities",
    category="placement",
    example={"dignity_in": {"planet": "Jupiter", "dignities": ["own", "exaltation"]}},
)
def dignity_in(ctx: EvalContext, p: DignityIn) -> Outcome:
    """Check that the planet's dignity (sthana) is one of the listed kinds.

    Exaltation (uccha) and debilitation (neecha) are the whole signs of BPHS
    Ch. 3; moolatrikona uses the BPHS degree ranges (Sun Leo 0-20, Moon
    Taurus 4-30, ...). A planet can hold several at once: Mercury at Virgo
    17 deg is exalted, in moolatrikona and in its own sign. Friend, enemy and
    neutral are the natural relation (naisargika maitri) of the planet to
    the lord of the sign it occupies, used only when the planet is in none
    of its own, moolatrikona, exaltation or debilitation signs. The nodes'
    exaltation follows ``rahu_exalted_in`` (Taurus by default).
    """
    planet = to_planet_enum(p.planet)
    lon = ctx.sky.lon(p.planet)
    found = dignities_of(planet, lon, p.rahu_exalted_in)
    held = bool(found & set(p.dignities))
    sign = SIGN_NAMES[int(lon // 30)]
    return Outcome(
        held,
        f"{p.planet} in {fmt_lon(lon)} is {' and '.join(sorted(found))} "
        f"(sign lord {SIGN_LORDS[int(lon // 30)]} of {sign})"
        f"{'' if held else ', not ' + ' or '.join(p.dignities)}",
    )


class VargaSign(Params):
    """Parameters of ``varga_sign``."""

    planet: PointName
    varga: int
    signs: SignList

    @field_validator("varga", mode="before")
    @classmethod
    def _factor(cls, value):
        if isinstance(value, str) and value.upper().startswith("D"):
            value = value[1:]
        factor = int(value)
        if factor not in VARGA_FACTORS:
            raise ValueError(
                f"D{factor} is not a supported varga; use one of "
                + ", ".join(f"D{f}" for f in VARGA_FACTORS)
            )
        return factor


@predicate(
    "varga_sign",
    VargaSign,
    category="placement",
    example={"varga_sign": {"planet": "Venus", "varga": 9, "signs": ["Pisces"]}},
)
def varga_sign(ctx: EvalContext, p: VargaSign) -> Outcome:
    """Check that the point is in one of the listed signs of the D-n chart.

    The sixteen Shodasavargas of BPHS Ch. 6 (D1, D2, D3, D4, D7, D9, D10,
    D12, D16, D20, D24, D27, D30, D40, D45, D60) with the traditional
    Parashari mappings (e.g. D9 navamsa from Aries, Capricorn, Libra or
    Cancer by element).
    """
    lon = ctx.sky.lon(p.planet)
    sign = SIGN_NAMES[_varga_sign(lon, p.varga)]
    held = sign in p.signs
    return Outcome(
        held,
        f"{ctx.sky.describe(p.planet)}, which is {sign} in D{p.varga}"
        f"{'' if held else ', not ' + ' or '.join(p.signs)}",
    )


class LongitudeBetween(Params):
    """Parameters of ``longitude_between``."""

    planet: PointName
    start: float = Field(ge=0, lt=360)
    end: float = Field(ge=0, le=360)
    note: Optional[str] = None


@predicate(
    "longitude_between",
    LongitudeBetween,
    category="placement",
    example={"longitude_between": {"planet": "Sun", "start": 141.5, "end": 144.5}},
)
def longitude_between(ctx: EvalContext, p: LongitudeBetween) -> Outcome:
    """Check that the point's sidereal longitude lies in [start, end) degrees.

    Longitudes run 0-360 from 0 deg Aries; a range with ``start`` greater
    than ``end`` wraps through 0 deg Aries (e.g. 350 to 10).
    """
    lon = ctx.sky.lon(p.planet) % 360.0
    span = (p.end - p.start) % 360.0 or 360.0
    held = (lon - p.start) % 360.0 < span
    return Outcome(
        held,
        f"{ctx.sky.describe(p.planet)} ({lon:.2f} deg), "
        f"{'inside' if held else 'outside'} {p.start:g}-{p.end:g} deg",
    )


__all__ = ["KENDRAS", "NAKSHATRA_NAMES", "SIGN_LORDS", "TRIKONAS", "dignities_of"]
