"""Relations between planets: conjunction, aspect, combustion, motion."""

from typing import Dict, List, Optional, Set

from pydantic import Field, field_validator, model_validator

from ...astrology.combustion import angular_separation, combustion_orb
from ..context import EvalContext
from ..vocabulary import SIGN_NAMES, ordinal, to_planet_enum
from . import Outcome, Params, PlanetName, PointName, house_from, point_label
from . import predicate

# Whole-sign aspects (graha drishti) each planet casts, counted from its own
# sign. Every planet aspects the 7th; Mars also the 4th and 8th, Jupiter the
# 5th and 9th, Saturn the 3rd and 10th. The nodes are given the 7th only.
GRAHA_DRISHTI: Dict[str, Set[int]] = {
    "Sun": {7},
    "Moon": {7},
    "Mercury": {7},
    "Venus": {7},
    "Mars": {4, 7, 8},
    "Jupiter": {5, 7, 9},
    "Saturn": {3, 7, 10},
    "Rahu": {7},
    "Ketu": {7},
}


class PlanetOnly(Params):
    """Parameters of predicates about one planet."""

    planet: PlanetName


@predicate(
    "combust",
    PlanetOnly,
    category="relation",
    example={"combust": {"planet": "Mercury"}},
)
def combust(ctx: EvalContext, p: PlanetOnly) -> Outcome:
    """Check that the planet is within its combustion (asta) orb of the Sun.

    Orbs after Surya Siddhanta Ch. 9: Moon 12, Mars 17, Mercury 14 (12 when
    retrograde), Jupiter 11, Venus 10 (8 when retrograde), Saturn 15 degrees
    of longitude. The Sun, Rahu and Ketu are never combust.
    """
    planet = to_planet_enum(p.planet)
    record = ctx.sky.record(p.planet)
    retro = bool(record["longitude_speed"] < 0)
    orb = combustion_orb(planet, retro)
    if orb == 0.0:
        return Outcome(False, f"{p.planet} cannot be combust")
    sep = angular_separation(ctx.sky.lon(p.planet), ctx.sky.lon("Sun"))
    held = sep <= orb
    return Outcome(
        held,
        f"{p.planet} is {sep:.1f} deg from the Sun; its combustion orb is "
        f"{orb:g} deg{' (retrograde)' if retro else ''}",
    )


@predicate(
    "retrograde",
    PlanetOnly,
    category="relation",
    example={"retrograde": {"planet": "Saturn"}},
)
def retrograde(ctx: EvalContext, p: PlanetOnly) -> Outcome:
    """Check that the planet moves backwards (vakri): longitude decreasing.

    Read from the Swiss Ephemeris longitude speed. The mean nodes are always
    retrograde; the Sun and Moon never are.
    """
    speed = ctx.sky.speed(p.planet)
    held = speed < 0
    return Outcome(
        held,
        f"{p.planet} moves {speed:+.3f} deg/day, so it is "
        f"{'retrograde' if held else 'direct'}",
    )


class PlanetPair(Params):
    """Two planets and an orb."""

    planets: List[PlanetName] = Field(min_length=2, max_length=2)
    orb: float = Field(gt=0, le=30)


@predicate(
    "conjunct_within",
    PlanetPair,
    category="relation",
    example={"conjunct_within": {"planets": ["Mars", "Ketu"], "orb": 13}},
)
def conjunct_within(ctx: EvalContext, p: PlanetPair) -> Outcome:
    """Check that the two planets are within ``orb`` degrees of longitude (yuti).

    The orb is measured in degrees, so the pair may straddle a sign
    boundary. For a whole-sign conjunction (same rashi) use
    ``in_house_from`` with ``houses: [1]``.
    """
    a, b = p.planets
    sep = angular_separation(ctx.sky.lon(a), ctx.sky.lon(b))
    held = sep <= p.orb
    return Outcome(
        held,
        f"{ctx.sky.describe(a)} and {ctx.sky.describe(b)}: {sep:.1f} deg apart, "
        f"{'within' if held else 'outside'} the {p.orb:g} deg orb",
    )


class Separation(Params):
    """Two planets, a target angle and an orb."""

    planets: List[PlanetName] = Field(min_length=2, max_length=2)
    angle: float = Field(ge=0, le=180)
    orb: float = Field(gt=0, le=30)


@predicate(
    "separation_within",
    Separation,
    category="relation",
    example={
        "separation_within": {"planets": ["Jupiter", "Saturn"], "angle": 180, "orb": 10}
    },
)
def separation_within(ctx: EvalContext, p: Separation) -> Outcome:
    """Check that the shortest arc between two planets is within ``orb`` of ``angle``.

    A degree-based relation (180 = opposition, 90 = square), used by the
    mundane texts; it is not graha drishti, which is whole-sign.
    """
    a, b = p.planets
    sep = angular_separation(ctx.sky.lon(a), ctx.sky.lon(b))
    held = abs(sep - p.angle) <= p.orb
    return Outcome(
        held,
        f"{ctx.sky.describe(a)} and {ctx.sky.describe(b)}: {sep:.1f} deg apart, "
        f"{abs(sep - p.angle):.1f} deg from {p.angle:g} "
        f"({'within' if held else 'outside'} the {p.orb:g} deg orb)",
    )


class Drishti(Params):
    """Parameters of ``graha_drishti``."""

    planet: PlanetName
    target: PointName
    aspects: Optional[List[int]] = None

    @field_validator("aspects", mode="before")
    @classmethod
    def _listify(cls, value):
        return value if value is None or isinstance(value, list) else [value]

    @model_validator(mode="after")
    def _legal(self):
        legal = GRAHA_DRISHTI[self.planet]
        if self.aspects is not None:
            bad = [a for a in self.aspects if a not in legal]
            if bad or not self.aspects:
                raise ValueError(
                    f"{self.planet} casts only the "
                    + ", ".join(ordinal(a) for a in sorted(legal))
                    + f" aspect(s); {', '.join(ordinal(a) for a in bad)} is not one"
                )
        return self


@predicate(
    "graha_drishti",
    Drishti,
    category="relation",
    example={"graha_drishti": {"planet": "Mars", "target": "Ketu", "aspects": [8]}},
)
def graha_drishti(ctx: EvalContext, p: Drishti) -> Outcome:
    """Check that the planet casts a whole-sign graha drishti on the target.

    Parashari aspects are counted by sign from the aspecting planet: every
    planet aspects the 7th sign from itself; Mars also the 4th and 8th,
    Jupiter the 5th and 9th, Saturn the 3rd and 10th (BPHS, Graha Drishti).
    Rahu and Ketu are given the 7th only. A planet in the same sign as the
    target is conjunct, not aspecting. ``aspects`` restricts the test to
    some of the planet's legal aspects (Mars may only list 4, 7 and 8).
    """
    house = house_from(ctx.sky.sign(p.planet), ctx.sky.sign(p.target))
    allowed = set(p.aspects or GRAHA_DRISHTI[p.planet])
    held = house in allowed
    target_sign = SIGN_NAMES[ctx.sky.sign(p.target)]
    return Outcome(
        held,
        f"{ctx.sky.describe(p.planet)}; {point_label(p.target)} in {target_sign} "
        f"is the {ordinal(house)} sign from it, "
        f"{'which is' if held else 'not'} one of its aspects "
        f"({', '.join(ordinal(a) for a in sorted(allowed))})",
    )


class SpeedBelow(Params):
    """Parameters of ``planet_speed_below``."""

    planet: PlanetName
    speed: float = Field(gt=0)
    absolute: bool = True


@predicate(
    "planet_speed_below",
    SpeedBelow,
    category="relation",
    example={"planet_speed_below": {"planet": "Saturn", "speed": 0.05}},
)
def planet_speed_below(ctx: EvalContext, p: SpeedBelow) -> Outcome:
    """Check that the planet moves slower than ``speed`` degrees per day.

    With ``absolute: true`` (default) the magnitude of the speed is compared,
    which detects a planet near its station (sthambhana / vikala). With
    ``absolute: false`` the signed speed is compared, so any retrograde
    planet is "below" a positive threshold.
    """
    speed = ctx.sky.speed(p.planet)
    value = abs(speed) if p.absolute else speed
    held = value < p.speed
    return Outcome(
        held,
        f"{p.planet} moves {speed:+.4f} deg/day; "
        f"{'|speed|' if p.absolute else 'speed'} is "
        f"{'below' if held else 'not below'} {p.speed:g}",
    )


__all__ = ["GRAHA_DRISHTI"]
