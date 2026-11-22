"""Time predicates: Vimshottari dasha, tithi and Moon phase, weekday lord."""

from datetime import datetime
from typing import List, Literal, Optional, Set

import pytz
from pydantic import Field, field_validator, model_validator

from ...config.constants import Planet
from ...dignity.exaltation_matrix import (
    OWN_SIGNS_TABLE,
    is_in_debilitation,
    is_in_exaltation,
)
from ...dignity.friendship_matrix import NAISARGIKA_MAITRI, FriendshipType
from ..context import EvalContext, check_varga, sunrise_before
from ..vocabulary import LAGNA, SIGN_NAMES, ordinal, to_planet_enum
from . import HouseList, Outcome, Params, PlanetList, PointName, predicate
from .placement import SIGN_LORDS, dignities_of

LEVEL_NAMES = {1: "mahadasha", 2: "antardasha", 3: "pratyantardasha"}
VISIBLE = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]
# Python weekday() (Monday = 0) -> lord of the vara.
WEEKDAY_LORDS = ["Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Sun"]
WEEKDAY_NAMES = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]


class DashaLordIs(Params):
    """Parameters of ``dasha_lord_is``."""

    lords: PlanetList
    level: int = Field(default=1, ge=1, le=3)


@predicate(
    "dasha_lord_is",
    DashaLordIs,
    needs=("natal",),
    shorthand="lords",
    category="time",
    example={"dasha_lord_is": {"level": 1, "lords": ["Saturn"]}},
)
def dasha_lord_is(ctx: EvalContext, p: DashaLordIs) -> Outcome:
    """Check that the natal chart's running Vimshottari lord at ``level`` is listed.

    Vimshottari (BPHS Ch. 46): the Moon's nakshatra at birth fixes the first
    mahadasha and its elapsed fraction; level 1 is the mahadasha, 2 the
    antardasha (bhukti), 3 the pratyantardasha. Dasha years are Julian years
    of 365.25 days.
    """
    chain = ctx.dasha_chain(p.level)
    lord = chain[p.level - 1]
    held = lord in p.lords
    return Outcome(
        held,
        f"the running Vimshottari period is {'-'.join(chain)}; its "
        f"{LEVEL_NAMES[p.level]} lord is {lord}"
        f"{'' if held else ', not ' + ' or '.join(p.lords)}",
    )


class LordsOnly(Params):
    """Parameters of ``antardasha_lord_is``."""

    lords: PlanetList


@predicate(
    "antardasha_lord_is",
    LordsOnly,
    needs=("natal",),
    shorthand="lords",
    category="time",
    example={"antardasha_lord_is": {"lords": ["Rahu"]}},
)
def antardasha_lord_is(ctx: EvalContext, p: LordsOnly) -> Outcome:
    """Check that the running Vimshottari antardasha (bhukti) lord is listed.

    Same as ``dasha_lord_is`` with ``level: 2``.
    """
    return dasha_lord_is(ctx, DashaLordIs(lords=p.lords, level=2))


Phase = Literal["waxing", "waning", "new", "full"]


class MoonPhase(Params):
    """Parameters of ``moon_phase``."""

    phase: Optional[Phase] = None
    tithis: Optional[List[int]] = None

    @field_validator("tithis", mode="before")
    @classmethod
    def _tithis(cls, value):
        if value is None:
            return value
        value = value if isinstance(value, list) else [value]
        for t in value:
            if not isinstance(t, int) or not 1 <= t <= 30:
                raise ValueError("tithis are numbers 1-30 (1-15 Shukla, 16-30 Krishna)")
        return value

    @model_validator(mode="after")
    def _one(self):
        if self.phase is None and not self.tithis:
            raise ValueError("give a phase (waxing, waning, new, full) or tithis")
        return self


def tithi_words(tithi: int) -> str:
    """Name a tithi: "Shukla 5", "Purnima", "Krishna 3", "Amavasya"."""
    if tithi == 15:
        return "Purnima (full Moon)"
    if tithi == 30:
        return "Amavasya (new Moon)"
    return f"Shukla {tithi}" if tithi < 15 else f"Krishna {tithi - 15}"


@predicate(
    "moon_phase",
    MoonPhase,
    category="time",
    example={"moon_phase": {"phase": "full"}},
)
def moon_phase(ctx: EvalContext, p: MoonPhase) -> Outcome:
    """Check that the Moon's phase (paksha) or tithi matches.

    The tithi is the Moon's elongation from the Sun in 12-degree steps:
    tithis 1-15 are the bright half (Shukla paksha, waxing), 16-30 the dark
    half (Krishna paksha, waning). ``full`` is tithi 15 (Purnima), ``new``
    is tithi 30 (Amavasya). When both ``phase`` and ``tithis`` are given,
    both must hold.
    """
    elong = (ctx.sky.lon("Moon") - ctx.sky.lon("Sun")) % 360.0
    tithi = int(elong // 12) + 1
    phase_now = "waxing" if tithi <= 15 else "waning"
    checks = []
    if p.phase is not None:
        wanted = {"new": tithi == 30, "full": tithi == 15}
        checks.append(wanted.get(p.phase, phase_now == p.phase))
    if p.tithis:
        checks.append(tithi in p.tithis)
    held = all(checks)
    return Outcome(
        held,
        f"the Moon is {elong:.1f} deg ahead of the Sun: tithi {tithi} "
        f"({tithi_words(tithi)}), {phase_now}",
    )


class WeekdayLordIs(Params):
    """Parameters of ``weekday_lord_is``."""

    lords: PlanetList

    @field_validator("lords")
    @classmethod
    def _visible(cls, value):
        bad = [v for v in value if v not in VISIBLE]
        if bad:
            raise ValueError(f"{', '.join(bad)} rules no weekday")
        return value


def vara(ctx: EvalContext) -> tuple:
    """Return (weekday index, explanation) of the Vedic day at the moment."""
    sky = ctx.sky
    if sky.place is None:
        local = sky.moment
        return local.weekday(), (
            f"civil {WEEKDAY_NAMES[local.weekday()]} at UTC offset "
            f"{local.strftime('%z')} (no place, so midnight is the day boundary)"
        )
    tz = pytz.timezone(sky.place.tz)
    rise = sunrise_before(sky.moment, sky.place)
    if rise is None:
        local = sky.moment.astimezone(tz)
        return local.weekday(), (
            f"civil {WEEKDAY_NAMES[local.weekday()]} (the Sun does not rise "
            "here today)"
        )
    local_rise: datetime = rise.astimezone(tz)
    day = local_rise.weekday()
    return day, (
        f"{WEEKDAY_NAMES[day]}, the vara that began at sunrise "
        f"{local_rise.strftime('%Y-%m-%d %H:%M %Z')}"
    )


@predicate(
    "weekday_lord_is",
    WeekdayLordIs,
    shorthand="lords",
    category="time",
    example={"weekday_lord_is": {"lords": ["Saturn"]}},
)
def weekday_lord_is(ctx: EvalContext, p: WeekdayLordIs) -> Outcome:
    """Check that the lord of the weekday (vara) is listed.

    The Vedic day runs from sunrise to sunrise, so 02:00 on a Friday is
    still Thursday (Jupiter). With a place the local sunrise is computed;
    without one the civil date in the moment's own UTC offset is used.
    Lords: Sunday Sun, Monday Moon, Tuesday Mars, Wednesday Mercury,
    Thursday Jupiter, Friday Venus, Saturday Saturn.
    """
    day, words = vara(ctx)
    lord = WEEKDAY_LORDS[day]
    held = lord in p.lords
    return Outcome(
        held,
        f"the day is {words}, ruled by {lord}"
        f"{'' if held else ', not ' + ' or '.join(p.lords)}",
    )


# ------------------------------------------------ the running dasha lord
def _varga_words(varga: int) -> str:
    return "natal chart" if varga == 1 else f"natal D{varga}"


def _origin_words(origin: str) -> str:
    return "Lagna" if origin == LAGNA else origin


class DashaLordState(Params):
    """Shared fields: dasha level, natal varga and the counting origin."""

    level: int = Field(default=1, ge=1, le=3)
    varga: int = 1
    from_: PointName = Field(default=LAGNA, alias="from")
    natal_fields = ("from_",)

    @field_validator("varga", mode="before")
    @classmethod
    def _varga(cls, value):
        return check_varga(value, houses=True)

    @field_validator("from_")
    @classmethod
    def _origin(cls, value):
        if value not in (LAGNA, "Moon"):
            raise ValueError("count houses from the Lagna or the Moon")
        return value


def running_lord(ctx: EvalContext, level: int) -> tuple:
    """Return (chain, lord) of the natal chart's running Vimshottari period."""
    chain = ctx.dasha_chain(level)
    return chain, chain[level - 1]


def _period_words(chain, level: int, lord: str) -> str:
    return (
        f"the running Vimshottari period is {'-'.join(chain)}; its "
        f"{LEVEL_NAMES[level]} lord {lord}"
    )


class DashaLordInHouse(DashaLordState):
    """Parameters of ``dasha_lord_in_house``."""

    houses: HouseList


@predicate(
    "dasha_lord_in_house",
    DashaLordInHouse,
    needs=("natal",),
    category="time",
    example={
        "dasha_lord_in_house": {"level": 1, "varga": 1, "from": "Lagna", "houses": [8]}
    },
)
def dasha_lord_in_house(ctx: EvalContext, p: DashaLordInHouse) -> Outcome:
    """Check that the running dasha lord occupies one of the listed natal houses.

    Catalogue id: ``dasha.lord_state`` (jataka_applied, unverified). The
    Vimshottari lord at ``level`` (1 mahadasha, 2 antardasha, 3
    pratyantardasha) is placed in the natal D-``varga`` chart, and its house
    is counted by whole sign from the natal Lagna (default) or the natal
    Moon in the same varga. The dasha-result chapters of BPHS read the
    lord's natal house; applying them to a nation's chart is modern
    practice. D2 has no houses and raises, as does any varga the engine
    does not compute (D5, D6, D8).
    """
    chain, lord = running_lord(ctx, p.level)
    house = ctx.natal_house_of(lord, p.from_, p.varga)
    sign = SIGN_NAMES[ctx.natal_varga_sign(lord, p.varga)]
    origin = SIGN_NAMES[ctx.natal_varga_sign(p.from_, p.varga)]
    held = house in p.houses
    return Outcome(
        held,
        f"{_period_words(chain, p.level, lord)} is in {sign} in the "
        f"{_varga_words(p.varga)}, the {ordinal(house)} from the "
        f"{_origin_words(p.from_)} in {origin}"
        f"{'' if held else ', not ' + ', '.join(ordinal(h) for h in p.houses)}",
    )


class DashaLordRulesHouse(DashaLordState):
    """Parameters of ``dasha_lord_rules_house``."""

    houses: HouseList


def houses_ruled(lord: str, origin_sign: int) -> List[int]:
    """Whole-sign houses (1-12) from ``origin_sign`` whose sign ``lord`` rules.

    Parashari sign lords; Rahu and Ketu rule no sign and so no house.
    """
    return [h for h in range(1, 13) if SIGN_LORDS[(origin_sign + h - 1) % 12] == lord]


@predicate(
    "dasha_lord_rules_house",
    DashaLordRulesHouse,
    needs=("natal",),
    category="time",
    example={
        "dasha_lord_rules_house": {"level": 2, "varga": 9, "from": "Moon", "houses": [8]}
    },
)
def dasha_lord_rules_house(ctx: EvalContext, p: DashaLordRulesHouse) -> Outcome:
    """Check that the running dasha lord rules one of the listed natal houses.

    Catalogue id: ``dasha.lord_state`` (jataka_applied, unverified). The
    Vimshottari lord at ``level`` is the lord of a house when it rules that
    house's sign; houses are whole signs counted from the natal Lagna
    (default) or the natal Moon in the natal D-``varga`` chart. Sign lords
    are the Parashari rulers: Rahu and Ketu rule no house here, so a node
    period never holds. D2 has no houses and raises, as does any varga the
    engine does not compute.
    """
    chain, lord = running_lord(ctx, p.level)
    origin_sign = ctx.natal_varga_sign(p.from_, p.varga)
    ruled = houses_ruled(lord, origin_sign)
    held = bool(set(ruled) & set(p.houses))
    if ruled:
        rules = "rules the " + " and ".join(ordinal(h) for h in ruled)
    else:
        rules = "rules no house (the nodes own no sign)"
    return Outcome(
        held,
        f"{_period_words(chain, p.level, lord)} {rules} from the "
        f"{_origin_words(p.from_)} in {SIGN_NAMES[origin_sign]} in the "
        f"{_varga_words(p.varga)}"
        f"{'' if held else ', not ' + ', '.join(ordinal(h) for h in p.houses)}",
    )


DashaDignity = Literal[
    "own", "exaltation", "debilitation", "moolatrikona", "friend", "enemy", "neutral"
]


class DashaLordDignity(Params):
    """Parameters of ``dasha_lord_dignity``."""

    dignities: List[DashaDignity] = Field(min_length=1)
    level: int = Field(default=1, ge=1, le=3)
    varga: int = 1
    rahu_exalted_in: Literal["taurus", "gemini"] = "taurus"

    @field_validator("dignities", mode="before")
    @classmethod
    def _listify(cls, value):
        return value if isinstance(value, list) else [value]

    @field_validator("varga", mode="before")
    @classmethod
    def _varga(cls, value):
        factor = check_varga(value)
        if factor == 2:
            raise ValueError(
                "D2 (hora) gives only the Sun's or the Moon's hora; read it "
                "with varga_sign, not as a dignity"
            )
        return factor

    @model_validator(mode="after")
    def _moolatrikona(self):
        if self.varga != 1 and "moolatrikona" in self.dignities:
            raise ValueError(
                "moolatrikona is a degree range of the rashi; it has no "
                f"meaning for a D{self.varga} sign"
            )
        return self


def sign_dignities(planet: Planet, sign: int, rahu_exalted_in: str) -> Set[str]:
    """Dignities of ``planet`` in a varga ``sign`` (whole sign only).

    Exaltation, debilitation and own sign by sign; friend, enemy or neutral
    (natural relation to the sign lord) only when none of those applies.
    Moolatrikona is a degree range of the rashi and is not assessed.
    """
    lon = sign * 30.0
    found = set()
    if is_in_exaltation(lon, planet, rahu_exalted_in):
        found.add("exaltation")
    if is_in_debilitation(lon, planet, rahu_exalted_in):
        found.add("debilitation")
    if sign in OWN_SIGNS_TABLE.get(planet, []):
        found.add("own")
    if not found:
        relation = NAISARGIKA_MAITRI[planet][to_planet_enum(SIGN_LORDS[sign])]
        found.add(
            {
                FriendshipType.NATURAL_FRIEND: "friend",
                FriendshipType.NATURAL_ENEMY: "enemy",
            }.get(relation, "neutral")
        )
    return found


@predicate(
    "dasha_lord_dignity",
    DashaLordDignity,
    needs=("natal",),
    category="time",
    example={
        "dasha_lord_dignity": {
            "level": 1,
            "varga": 9,
            "dignities": ["debilitation", "enemy"],
        }
    },
)
def dasha_lord_dignity(ctx: EvalContext, p: DashaLordDignity) -> Outcome:
    """Check that the running dasha lord has one of the listed natal dignities.

    Catalogue id: ``dasha.lord_state`` (jataka_applied, unverified). The
    Vimshottari lord at ``level`` is read in the natal D-``varga`` chart.
    In D1 the dignities are those of ``dignity_in`` (BPHS Ch. 3: whole-sign
    exaltation and debilitation, moolatrikona by degree range, own sign,
    else the natural relation to the sign lord). In a varga the sign alone
    is used, so moolatrikona cannot be asked for there. Dignity does not
    depend on a counting origin, so there is no ``from``. D2 raises, as
    does any varga the engine does not compute.
    """
    chain, lord = running_lord(ctx, p.level)
    planet = to_planet_enum(lord)
    natal = ctx.require_natal()
    if p.varga == 1:
        found = dignities_of(planet, natal.lon(lord), p.rahu_exalted_in)
    else:
        found = sign_dignities(
            planet, ctx.natal_varga_sign(lord, p.varga), p.rahu_exalted_in
        )
    sign = SIGN_NAMES[ctx.natal_varga_sign(lord, p.varga)]
    held = bool(found & set(p.dignities))
    return Outcome(
        held,
        f"{_period_words(chain, p.level, lord)} is in {sign} in the "
        f"{_varga_words(p.varga)}: {' and '.join(sorted(found))}"
        f"{'' if held else ', not ' + ' or '.join(p.dignities)}",
    )


__all__ = [
    "WEEKDAY_LORDS",
    "houses_ruled",
    "running_lord",
    "sign_dignities",
    "tithi_words",
    "vara",
]
