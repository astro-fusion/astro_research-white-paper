"""Mundane predicates from the Samhita texts: clusters, eclipses, Kurma, mandalas."""

from functools import lru_cache
from typing import List, Literal, Optional

from pydantic import Field, field_validator

from ...astrology.combustion import angular_separation
from ...astrology.mundane import (
    DIRECTIONS,
    MANDALAS,
    eclipse_magnitude,
    geocentric_distance_au,
    kurma_division,
    mandala_of,
    samvatsara,
)
from ..context import EvalContext, fmt_lon
from ..eclipses import Eclipse, eclipses_between
from ..vocabulary import SIGN_NAMES
from . import (
    Outcome,
    Params,
    PlanetList,
    PlanetName,
    PointName,
    SignName,
    predicate,
)

VISIBLE = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]


def _listify(value):
    return value if value is None or isinstance(value, list) else [value]


# ------------------------------------------------------------- clusters
class SignCluster(Params):
    """Parameters of ``planets_in_one_sign_gte``."""

    count: int = Field(ge=2, le=9)
    bodies: PlanetList = Field(default_factory=lambda: list(VISIBLE))
    signs: Optional[List[SignName]] = None

    @field_validator("signs", mode="before")
    @classmethod
    def _lists(cls, value):
        return _listify(value)


@predicate(
    "planets_in_one_sign_gte",
    SignCluster,
    category="mundane",
    example={"planets_in_one_sign_gte": {"count": 5}},
)
def planets_in_one_sign_gte(ctx: EvalContext, p: SignCluster) -> Outcome:
    """Check that at least ``count`` of ``bodies`` occupy one sidereal sign.

    The graha-cluster (sankhya) yogas of Varahamihira, Brihat Jataka ch. 12
    (Nabhasa yogas: Gola when all seven occupy one sign, Yuga two, Shula
    three, ...), and the mundane "pancha graha" (five-planet) cluster.
    ``bodies`` defaults to the seven visible grahas; ``signs`` restricts
    the sign that holds the cluster.
    """
    by_sign: dict = {}
    for body in p.bodies:
        by_sign.setdefault(ctx.sky.sign(body), []).append(body)
    sign, members = max(by_sign.items(), key=lambda kv: len(kv[1]))
    allowed = p.signs is None or SIGN_NAMES[sign] in p.signs
    held = len(members) >= p.count and allowed
    where = "" if p.signs is None else f" (wanted in {', '.join(p.signs)})"
    return Outcome(
        held,
        f"largest cluster: {len(members)} in {SIGN_NAMES[sign]} "
        f"({', '.join(members)}); {p.count} needed{where}",
    )


# ------------------------------------------------------------- eclipses
@lru_cache(maxsize=4096)
def _magnitude(ecl: Eclipse) -> float:
    return eclipse_magnitude(ecl.kind, ecl.jd)


class EclipseWithin(Params):
    """Parameters of ``eclipse_within_days``."""

    kind: Literal["solar", "lunar", "any"] = "any"
    days_before: float = Field(default=0.0, ge=0, le=400)
    days_after: float = Field(default=0.0, ge=0, le=400)
    pair_within_days: Optional[float] = Field(default=None, gt=0, le=60)
    min_magnitude: Optional[float] = Field(default=None, gt=-1, le=2)
    penumbral: bool = True


def _pair(ecl: Eclipse, days: float) -> Optional[Eclipse]:
    other = "lunar" if ecl.kind == "solar" else "solar"
    found = eclipses_between(ecl.jd - days, ecl.jd + days, other)
    return found[0] if found else None


@predicate(
    "eclipse_within_days",
    EclipseWithin,
    category="mundane",
    example={
        "eclipse_within_days": {
            "kind": "any",
            "days_before": 30,
            "days_after": 30,
            "pair_within_days": 16,
        }
    },
)
def eclipse_within_days(ctx: EvalContext, p: EclipseWithin) -> Outcome:
    """Check that an eclipse falls between ``days_before`` and ``days_after``.

    Brihat Samhita ch. 5 (Rahu-charita) reads eclipses as omens for the
    months that follow. Options: ``pair_within_days`` asks for an eclipse
    of the other kind within that many days of the found one (the
    solar-lunar pair of one eclipse season, the "fortnight" multiplier of
    the mundane texts); ``min_magnitude`` asks for a magnitude at greatest
    eclipse at or above it (Swiss Ephemeris ``sol_eclipse_how`` /
    ``lun_eclipse_how``; umbral for a lunar eclipse, so a penumbral-only
    eclipse is below any positive threshold); ``penumbral: false`` drops
    penumbral-only lunar eclipses.
    """
    jd = ctx.sky.jd
    found = eclipses_between(jd - p.days_before, jd + p.days_after, p.kind)
    words = []
    held = False
    for ecl in found:
        if not p.penumbral and ecl.kind == "lunar" and ecl.subtype == "penumbral":
            continue
        ok = True
        text = f"{ecl.subtype} {ecl.kind} eclipse {ecl.moment:%Y-%m-%d}"
        if p.min_magnitude is not None or p.pair_within_days is None:
            mag = _magnitude(ecl)
            text += f" magnitude {mag:.2f}"
            if p.min_magnitude is not None and mag < p.min_magnitude:
                ok = False
        if p.pair_within_days is not None:
            other = _pair(ecl, p.pair_within_days)
            if other is None:
                ok = False
                text += f", no paired eclipse within {p.pair_within_days:g} days"
            else:
                gap = abs(other.jd - ecl.jd)
                text += f", paired with the {other.kind} of {other.moment:%Y-%m-%d}"
                text += f" ({gap:.1f} days)"
        held = held or ok
        words.append(text)
    window = f"{p.days_before:g} days before to {p.days_after:g} days after"
    if not words:
        return Outcome(False, f"no eclipse from {window} the moment")
    return Outcome(held, "; ".join(words) + f" ({window})")


class EclipseDegree(Params):
    """Parameters of ``eclipse_degree_transited_by``."""

    planets: PlanetList
    orb: float = Field(gt=0, le=15)
    angles: List[float] = Field(default_factory=lambda: [0.0], min_length=1)
    kind: Literal["solar", "lunar", "any"] = "any"
    lookback_days: float = Field(default=365.0, gt=0, le=1100)

    @field_validator("angles", mode="before")
    @classmethod
    def _angles(cls, value):
        value = _listify(value)
        if any(not 0 <= float(a) <= 180 for a in value):
            raise ValueError("angles are degrees from 0 (conjunction) to 180")
        return value


@predicate(
    "eclipse_degree_transited_by",
    EclipseDegree,
    category="mundane",
    example={
        "eclipse_degree_transited_by": {
            "planets": ["Mars", "Saturn"],
            "orb": 3,
            "angles": [0, 180],
            "lookback_days": 365,
        }
    },
)
def eclipse_degree_transited_by(ctx: EvalContext, p: EclipseDegree) -> Outcome:
    """Check that a planet now stands at ``angles`` from a recent eclipse degree.

    The eclipse degree is the sidereal longitude of the Sun (solar) or Moon
    (lunar) at greatest eclipse, for eclipses in the ``lookback_days``
    before the moment. Brihat Samhita ch. 5 (Rahu-charita) assigns an
    eclipse's effects to the region and sign it falls in; the transit of a
    malefic over the eclipse point as the trigger is the modern mundane
    reading (B.V. Raman, *Mundane Astrology*), encoded as a rule, not as
    classical doctrine. ``angles: [0, 180]`` counts conjunction and
    opposition, ``[90, 180]`` square and opposition.
    """
    jd = ctx.sky.jd
    found = eclipses_between(jd - p.lookback_days, jd, p.kind)
    if not found:
        return Outcome(False, f"no eclipse in the {p.lookback_days:g} days before")
    hits = []
    near: Optional[tuple] = None
    for ecl in found:
        for planet in p.planets:
            sep = angular_separation(ctx.sky.lon(planet), ecl.longitude)
            for angle in p.angles:
                off = abs(sep - angle)
                if near is None or off < near[0]:
                    near = (off, planet, angle, ecl)
                if off <= p.orb:
                    hits.append(
                        f"{planet} {off:.1f} deg from {angle:g} to the "
                        f"{ecl.kind} eclipse degree {fmt_lon(ecl.longitude)} "
                        f"of {ecl.moment:%Y-%m-%d}"
                    )
    if hits:
        return Outcome(True, "; ".join(hits))
    assert near is not None
    off, planet, angle, ecl = near
    return Outcome(
        False,
        f"closest: {planet} {off:.1f} deg from {angle:g} to the {ecl.kind} eclipse "
        f"degree {fmt_lon(ecl.longitude)} of {ecl.moment:%Y-%m-%d} "
        f"(orb {p.orb:g})",
    )


# ------------------------------------------------------- Kurma, mandalas
Direction = Literal[DIRECTIONS]  # type: ignore[valid-type]


class KurmaDirection(Params):
    """Parameters of ``kurma_direction``."""

    planet: PointName
    directions: List[Direction] = Field(min_length=1)  # type: ignore[valid-type]
    start: Literal["krittika", "ashwini"] = "krittika"

    @field_validator("directions", mode="before")
    @classmethod
    def _lists(cls, value):
        return _listify(value)


@predicate(
    "kurma_direction",
    KurmaDirection,
    category="mundane",
    example={
        "kurma_direction": {
            "planet": "Saturn",
            "directions": ["north", "north_east"],
            "start": "krittika",
        }
    },
)
def kurma_direction(ctx: EvalContext, p: KurmaDirection) -> Outcome:
    """Check that the point's nakshatra lies in a listed Kurma Chakra division.

    Brihat Samhita ch. 14 (Kurma-vibhaga), verse 1: the land is divided
    into nine parts, three asterisms each, "beginning from Krittika", from
    the centre (Krittika, Rohini, Mrigashira) round the east, south-east,
    south, south-west, west, north-west, north and north-east (verses
    2-31; Iyer tr. 1884); verses 32-33 give malefics in a division as
    misery to its rulers. ``start: ashwini`` uses the practitioner table
    that puts Ashwini, Bharani, Krittika in the north instead; the dispute
    is recorded in ``rules/mundane/practitioner/DISPUTES.md``.
    """
    nak = ctx.sky.nakshatra(p.planet)
    division = kurma_division(nak["index"], p.start)
    held = division in p.directions
    return Outcome(
        held,
        f"{ctx.sky.describe(p.planet)}, in {nak['name']}: the "
        f"{division.replace('_', '-')} division ({p.start} convention)"
        f"{'' if held else ', not ' + ' or '.join(p.directions)}",
    )


class MoonMandala(Params):
    """Parameters of ``moon_mandala``."""

    mandalas: List[Literal["vayu", "agni", "indra", "varuna"]] = Field(min_length=1)
    planet: PointName = "Moon"

    @field_validator("mandalas", mode="before")
    @classmethod
    def _lists(cls, value):
        return [str(v).lower() for v in _listify(value)]


@predicate(
    "moon_mandala",
    MoonMandala,
    shorthand="mandalas",
    category="mundane",
    example={"moon_mandala": {"mandalas": ["agni"]}},
)
def moon_mandala(ctx: EvalContext, p: MoonMandala) -> Outcome:
    """Check that the Moon's nakshatra belongs to a listed earthquake circle.

    Brihat Samhita ch. 32 (Bhukampa-lakshana), Iyer tr. 1884: Vayu (v. 8)
    Uttara Phalguni, Hasta, Chitra, Swati, Punarvasu, Mrigashira, Ashwini;
    Agni (v. 12) Pushya, Krittika, Vishakha, Bharani, Magha, Purva
    Bhadrapada, Purva Phalguni; Indra (v. 16) Abhijit, Shravana, Dhanishta,
    Rohini, Jyeshtha, Uttara Ashadha, Anuradha; Varuna (v. 20) Revati, Purva
    Ashadha, Ardra, Ashlesha, Mula, Uttara Bhadrapada, Shatabhisha. The
    printed Varuna list repeats Uttara Ashadha and omits Uttara Bhadrapada;
    every asterism belongs to one circle, so Uttara Bhadrapada is used
    (see ``astrology/mundane.py`` and DISPUTES.md). Abhijit is not one of
    the 27 equal nakshatras and is dropped.
    """
    nak = ctx.sky.nakshatra(p.planet)
    circle = mandala_of(nak["name"])
    held = circle in p.mandalas
    return Outcome(
        held,
        f"{ctx.sky.describe(p.planet)}, in {nak['name']}: the {circle.title()} "
        f"mandala{'' if held else ', not ' + ' or '.join(p.mandalas)}",
    )


# ------------------------------------------------------------- distance
class DistanceAU(Params):
    """Parameters of ``planet_distance_au_lte``."""

    planet: PlanetName
    au: float = Field(gt=0, le=12)

    @field_validator("planet")
    @classmethod
    def _visible(cls, value):
        if value not in VISIBLE:
            raise ValueError("the nodes have no distance; use a visible planet")
        return value


@predicate(
    "planet_distance_au_lte",
    DistanceAU,
    category="mundane",
    example={"planet_distance_au_lte": {"planet": "Mars", "au": 0.45}},
)
def planet_distance_au_lte(ctx: EvalContext, p: DistanceAU) -> Outcome:
    """Check that the planet's geocentric distance is at most ``au``.

    Brihat Samhita ch. 6 (Bhauma-chara) reads Mars by its appearance, a
    large, bright, red Mars portending strife; brightness and apparent size
    are set by distance, which this predicate measures directly (Swiss
    Ephemeris geocentric distance, astronomical units). Mars comes within
    about 0.37 au at a perihelic opposition (2003) and recedes to 2.7 au.
    """
    dist = geocentric_distance_au(ctx.sky.jd, p.planet)
    held = dist <= p.au
    return Outcome(
        held,
        f"{p.planet} is {dist:.3f} au from Earth "
        f"({'within' if held else 'beyond'} {p.au:g} au)",
    )


# ------------------------------------------------------------ samvatsara
class SamvatsaraIs(Params):
    """Parameters of ``samvatsara_is``."""

    names: List[str] = Field(min_length=1)
    convention: Literal["luni_solar"] = "luni_solar"

    @field_validator("names", mode="before")
    @classmethod
    def _known(cls, value):
        from ...astrology.mundane import SAMVATSARA_NAMES

        value = _listify(value)
        table = {n.lower(): n for n in SAMVATSARA_NAMES}
        out = []
        for name in value:
            if str(name).lower() not in table:
                raise ValueError(
                    f"unknown samvatsara '{name}'; the sixty are "
                    + ", ".join(SAMVATSARA_NAMES)
                )
            out.append(table[str(name).lower()])
        return out


@predicate(
    "samvatsara_is",
    SamvatsaraIs,
    shorthand="names",
    category="time",
    example={"samvatsara_is": {"names": ["Krodhi"]}},
)
def samvatsara_is(ctx: EvalContext, p: SamvatsaraIs) -> Outcome:
    """Check that the sixty-year samvatsara running at the moment is listed.

    The cycle of Brihat Samhita ch. 8 (Brihaspati-chara), Prabhava to
    Akshaya. Convention ``luni_solar`` (South and West India): the year
    begins at Chaitra Shukla Pratipada, the new Moon with the sidereal Sun
    in Pisces before Mesha sankranti (the first one if Chaitra is doubled),
    and the year that began in 1987 is Prabhava, so 2024-25 is Krodhi. The
    North Indian Barhaspatya reckoning by Jupiter's mean sign gives
    different names and is not implemented.
    """
    name, index, start = samvatsara(ctx.sky.jd)
    held = name in p.names
    return Outcome(
        held,
        f"the samvatsara is {name} (no. {index + 1} of 60, from "
        f"{start:%Y-%m-%d})" + ("" if held else ", not " + " or ".join(p.names)),
    )


MANDALA_NAMES = tuple(MANDALAS)

__all__ = ["MANDALA_NAMES", "VISIBLE"]
