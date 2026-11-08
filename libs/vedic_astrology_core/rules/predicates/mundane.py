"""Mundane predicates: transits to a natal (national) chart, eclipses, ingress."""

from typing import List, Literal, Optional

from pydantic import Field, field_validator

from ...astrology.chart import get_nakshatra
from ...astrology.combustion import angular_separation
from ...utils.datetime_utils import julian_day_to_datetime
from ..context import EvalContext, fmt_lon
from ..eclipses import eclipses_between
from ..vocabulary import SIGN_NAMES, ordinal
from . import (
    HouseList,
    NakshatraName,
    Outcome,
    Params,
    PlanetName,
    PointName,
    SignName,
    house_from,
    point_label,
    predicate,
)


class TransitHouse(Params):
    """Parameters of ``transit_in_house_from_natal``."""

    planet: PlanetName
    from_: PointName = Field(default="Lagna", alias="from")
    houses: HouseList
    natal_fields = ("from_",)


@predicate(
    "transit_in_house_from_natal",
    TransitHouse,
    needs=("natal",),
    category="mundane",
    example={
        "transit_in_house_from_natal": {
            "planet": "Saturn",
            "from": "Moon",
            "houses": [8],
        }
    },
)
def transit_in_house_from_natal(ctx: EvalContext, p: TransitHouse) -> Outcome:
    """Check that the transiting planet is in one of the houses from a natal point.

    Gochara: the planet's sign now is counted by whole sign from the natal
    Lagna (default) or a natal planet (the natal Moon for classical
    gochara). The natal chart may be a person's or a nation's.
    """
    natal = ctx.require_natal()
    origin_sign = natal.sign(p.from_)
    house = house_from(origin_sign, ctx.sky.sign(p.planet))
    held = house in p.houses
    return Outcome(
        held,
        f"transiting {ctx.sky.describe(p.planet)}, the {ordinal(house)} from the "
        f"natal {point_label(p.from_).replace('the ', '')} in "
        f"{SIGN_NAMES[origin_sign]}"
        f"{'' if held else ', not ' + ', '.join(ordinal(h) for h in p.houses)}",
    )


class TransitConjunct(Params):
    """Parameters of ``transit_conjunct_natal``."""

    planet: PlanetName
    natal_point: PointName
    orb: float = Field(gt=0, le=30)
    natal_fields = ("natal_point",)


@predicate(
    "transit_conjunct_natal",
    TransitConjunct,
    needs=("natal",),
    category="mundane",
    example={
        "transit_conjunct_natal": {"planet": "Saturn", "natal_point": "Sun", "orb": 3}
    },
)
def transit_conjunct_natal(ctx: EvalContext, p: TransitConjunct) -> Outcome:
    """Check that the transiting planet is within ``orb`` degrees of a natal point."""
    natal = ctx.require_natal()
    natal_lon = natal.lon(p.natal_point)
    sep = angular_separation(ctx.sky.lon(p.planet), natal_lon)
    held = sep <= p.orb
    return Outcome(
        held,
        f"transiting {ctx.sky.describe(p.planet)} is {sep:.1f} deg from the natal "
        f"{point_label(p.natal_point).replace('the ', '')} at {fmt_lon(natal_lon)}"
        f" ({'within' if held else 'outside'} {p.orb:g} deg)",
    )


def _days(n: float) -> str:
    return f"{n:g} day" if n == 1 else f"{n:g} days"


def _window(before: float, after: float) -> str:
    return f"between {_days(before)} before and {_days(after)} after"


def _list(value):
    return value if value is None or isinstance(value, list) else [value]


class EclipseInSign(Params):
    """Parameters of ``eclipse_in_sign``."""

    kind: Literal["solar", "lunar", "any"] = "any"
    signs: Optional[List[SignName]] = None
    nakshatras: Optional[List[NakshatraName]] = None
    days_before: float = Field(default=1.0, ge=0, le=400)
    days_after: float = Field(default=1.0, ge=0, le=400)

    @field_validator("signs", "nakshatras", mode="before")
    @classmethod
    def _lists(cls, value):
        return _list(value)


@predicate(
    "eclipse_in_sign",
    EclipseInSign,
    category="mundane",
    example={
        "eclipse_in_sign": {
            "kind": "solar",
            "signs": ["Leo"],
            "days_before": 15,
            "days_after": 15,
        }
    },
)
def eclipse_in_sign(ctx: EvalContext, p: EclipseInSign) -> Outcome:
    """Check that an eclipse falls in the window and in one of the listed signs.

    The window is ``days_before`` to ``days_after`` around the moment. A
    solar eclipse is placed by the sidereal Sun, a lunar eclipse by the
    sidereal Moon, at greatest eclipse (Swiss Ephemeris
    ``sol_eclipse_when_glob`` / ``lun_eclipse_when``). Without ``signs`` or
    ``nakshatras`` any eclipse of that kind in the window counts.
    """
    jd = ctx.sky.jd
    found = eclipses_between(jd - p.days_before, jd + p.days_after, p.kind)
    matches = []
    for ecl in found:
        sign = SIGN_NAMES[int(ecl.longitude // 30)]
        nak = get_nakshatra(ecl.longitude)["name"]
        ok = (p.signs is None or sign in p.signs) and (
            p.nakshatras is None or nak in p.nakshatras
        )
        words = (
            f"{ecl.subtype} {ecl.kind} eclipse {ecl.moment:%Y-%m-%d %H:%M} UT in "
            f"{fmt_lon(ecl.longitude)} ({nak})"
        )
        matches.append((ok, words))
    window = _window(p.days_before, p.days_after)
    if not matches:
        kind = "" if p.kind == "any" else p.kind + " "
        return Outcome(False, f"no {kind}eclipse {window} the moment")
    held = any(ok for ok, _ in matches)
    where = []
    if p.signs:
        where.append("signs " + ", ".join(p.signs))
    if p.nakshatras:
        where.append("nakshatras " + ", ".join(p.nakshatras))
    wanted = f"; wanted {' or '.join(where)}" if where else ""
    return Outcome(held, f"{'; '.join(w for _, w in matches)} ({window}){wanted}")


class Ingress(Params):
    """Parameters of ``ingress``."""

    planet: PlanetName
    signs: Optional[List[SignName]] = None
    days_before: float = Field(default=1.0, ge=0, le=400)
    days_after: float = Field(default=1.0, ge=0, le=400)

    @field_validator("signs", mode="before")
    @classmethod
    def _lists(cls, value):
        return _list(value)


def _step_days(planet: str) -> float:
    return 0.1 if planet == "Moon" else 0.5


@predicate(
    "ingress",
    Ingress,
    category="mundane",
    example={"ingress": {"planet": "Sun", "signs": ["Aries"], "days_before": 1}},
)
def ingress(ctx: EvalContext, p: Ingress) -> Outcome:
    """Check that the planet enters a sign (sankranti for the Sun) within the window.

    The window runs from ``days_before`` before to ``days_after`` after the
    moment. A retrograde planet re-entering a sign also counts. Without
    ``signs`` an ingress into any sign counts. The crossing time is refined
    to about a minute.
    """
    engine = ctx.sky.engine
    jd0 = ctx.sky.jd - p.days_before
    jd1 = ctx.sky.jd + p.days_after
    body = p.planet.upper()

    def sign_at(jd: float) -> int:
        return int(engine.get_planet_position(jd, body)["longitude"] // 30)

    step = _step_days(p.planet)
    crossings = []
    t, s = jd0, sign_at(jd0)
    while t < jd1:
        t2 = min(t + step, jd1)
        s2 = sign_at(t2)
        if s2 != s:
            lo, hi = t, t2
            for _ in range(20):
                mid = (lo + hi) / 2
                if sign_at(mid) == s:
                    lo = mid
                else:
                    hi = mid
            crossings.append((hi, s2))
        t, s = t2, s2
    window = _window(p.days_before, p.days_after)
    if not crossings:
        return Outcome(
            False,
            f"{p.planet} stays in {SIGN_NAMES[s]} {window} the moment (no ingress)",
        )
    words = []
    held = False
    for jd, sign in crossings:
        name = SIGN_NAMES[sign]
        when = julian_day_to_datetime(jd)
        words.append(f"{p.planet} enters {name} at {when:%Y-%m-%d %H:%M} UT")
        held = held or p.signs is None or name in p.signs
    wanted = f"; wanted {', '.join(p.signs)}" if p.signs else ""
    return Outcome(held, f"{'; '.join(words)} ({window}){wanted}")


__all__ = ["eclipse_in_sign", "ingress"]
