"""House lords, malefics, elements, the lunar calendar and long cycles."""

from datetime import datetime
from typing import List, Literal, Optional, Set

from pydantic import AwareDatetime, Field, field_validator, model_validator

from ...astrology.combustion import angular_separation
from ...astrology.mundane import LUNAR_MONTHS, lunar_month
from ..context import EvalContext, Sky
from ..vocabulary import LAGNA, SIGN_NAMES, ordinal
from . import (
    HouseList,
    NakshatraList,
    Outcome,
    Params,
    PlanetList,
    PlanetName,
    PointName,
    house_from,
    point_label,
    predicate,
)
from .placement import SIGN_LORDS
from .relations import GRAHA_DRISHTI

NATURAL_MALEFICS = ["Sun", "Mars", "Saturn", "Rahu", "Ketu"]
ELEMENT_SIGNS = {
    "fire": ("Aries", "Leo", "Sagittarius"),
    "earth": ("Taurus", "Virgo", "Capricorn"),
    "air": ("Gemini", "Libra", "Aquarius"),
    "water": ("Cancer", "Scorpio", "Pisces"),
}
JULIAN_YEAR_DAYS = 365.25


def _listify(value):
    return value if value is None or isinstance(value, list) else [value]


# ------------------------------------------------------------ calendar
def _tithi(sky: Sky) -> int:
    elong = (sky.lon("Moon") - sky.lon("Sun")) % 360.0
    return int(elong // 12) + 1


def _month_names(value):
    value = _listify(value)
    if value is None:
        return value
    table = {m.lower(): m for m in LUNAR_MONTHS}
    table.update({"asvina": "Ashvina", "ashwin": "Ashvina", "shravan": "Shravana"})
    out = []
    for name in value:
        key = str(name).lower()
        if key not in table:
            raise ValueError(
                f"unknown lunar month '{name}'; use one of " + ", ".join(LUNAR_MONTHS)
            )
        out.append(table[key])
    return out


class MonthPaksha(Params):
    """Parameters of ``month_paksha``."""

    months: List[str] = Field(min_length=1)
    paksha: Optional[Literal["shukla", "krishna"]] = None
    adhika: Optional[bool] = None

    @field_validator("months", mode="before")
    @classmethod
    def _months(cls, value):
        return _month_names(value)


@predicate(
    "month_paksha",
    MonthPaksha,
    category="time",
    example={"month_paksha": {"months": ["Ashadha"], "paksha": "shukla"}},
)
def month_paksha(ctx: EvalContext, p: MonthPaksha) -> Outcome:
    """Check the amanta lunar month (and optionally its paksha) at the moment.

    The month runs new Moon to new Moon and takes its name from the
    sidereal sign of the Sun at its start (Sun in Pisces: Chaitra, Aries:
    Vaishakha, ... Aquarius: Phalguna), the Surya Siddhanta rule (ch. 14,
    Manadhyaya) as used by Indian pancangas; a month starting in the same
    sign as the next is adhika. Shukla paksha is tithis 1-15, Krishna 16-30.
    ``adhika: false`` excludes the intercalary month, ``true`` asks for it.
    """
    name, adhika, _start = lunar_month(ctx.sky.jd)
    tithi = _tithi(ctx.sky)
    paksha = "shukla" if tithi <= 15 else "krishna"
    held = name in p.months
    if p.paksha is not None:
        held = held and paksha == p.paksha
    if p.adhika is not None:
        held = held and adhika == p.adhika
    label = f"{'adhika ' if adhika else ''}{name}, {paksha} paksha (tithi {tithi})"
    want = " or ".join(p.months) + (f" {p.paksha}" if p.paksha else "")
    return Outcome(
        held, f"the lunar month is {label}" + ("" if held else f", not {want}")
    )


class NakshatraOnTithi(Params):
    """Parameters of ``nakshatra_on_tithi``."""

    nakshatras: NakshatraList
    tithis: List[int] = Field(min_length=1)
    months: Optional[List[str]] = None

    @field_validator("tithis", mode="before")
    @classmethod
    def _tithis(cls, value):
        value = _listify(value)
        for t in value:
            if not isinstance(t, int) or not 1 <= t <= 30:
                raise ValueError("tithis are numbers 1-30 (1-15 Shukla, 16-30 Krishna)")
        return value

    @field_validator("months", mode="before")
    @classmethod
    def _months(cls, value):
        return _month_names(value)


@predicate(
    "nakshatra_on_tithi",
    NakshatraOnTithi,
    category="time",
    example={
        "nakshatra_on_tithi": {
            "nakshatras": ["Rohini"],
            "tithis": [19],
            "months": ["Ashadha"],
        }
    },
)
def nakshatra_on_tithi(ctx: EvalContext, p: NakshatraOnTithi) -> Outcome:
    """Check that the Moon is in a listed nakshatra on a listed tithi (and month).

    Brihat Samhita ch. 26 (Ashadhi-yoga) and ch. 24 (Rohini-yoga) read the
    season from the Moon's asterism on fixed days of Ashadha: a nakshatra
    falling on a given tithi of a given lunar month. Tithi 1-15 is the
    bright half, 16-30 the dark half; months as in ``month_paksha``.
    """
    nak = ctx.sky.nakshatra("Moon")["name"]
    tithi = _tithi(ctx.sky)
    held = nak in p.nakshatras and tithi in p.tithis
    words = f"the Moon is in {nak} on tithi {tithi}"
    if p.months is not None:
        name, adhika, _ = lunar_month(ctx.sky.jd)
        held = held and name in p.months
        words += f" of {'adhika ' if adhika else ''}{name}"
    return Outcome(
        held,
        words
        + (
            ""
            if held
            else f"; wanted {', '.join(p.nakshatras)} on tithi "
            + ", ".join(str(t) for t in p.tithis)
        ),
    )


# -------------------------------------------------------- house lordship
class ChartChoice(Params):
    """Shared fields: whose chart, and counted from which point."""

    from_: PointName = Field(default=LAGNA, alias="from")
    chart: Literal["now", "natal"] = "now"

    def inputs(self) -> Set[str]:
        """Lagna-based counting needs a place (now) or a natal place."""
        needed: Set[str] = {"natal"} if self.chart == "natal" else set()
        if self.from_ == LAGNA:
            needed.add("natal_place" if self.chart == "natal" else "place")
        return needed

    def sky(self, ctx: EvalContext) -> Sky:
        """Return the sky the houses are read in."""
        return ctx.require_natal() if self.chart == "natal" else ctx.sky


def lord_of(sky: Sky, origin: str, house: int) -> str:
    """Lord of the ``house``-th sign from ``origin`` (whole sign)."""
    return SIGN_LORDS[(sky.sign(origin) + house - 1) % 12]


def _where(p: ChartChoice) -> str:
    whose = "natal " if p.chart == "natal" else ""
    return f"from the {whose}{point_label(p.from_).replace('the ', '')}"


class LordOfHouseIn(Params):
    """Parameters of ``lord_of_house_in``."""

    house: int = Field(ge=1, le=12)
    houses: HouseList
    from_: PointName = Field(default=LAGNA, alias="from")
    chart: Literal["now", "natal"] = "now"

    inputs = ChartChoice.inputs
    sky = ChartChoice.sky


@predicate(
    "lord_of_house_in",
    LordOfHouseIn,
    category="placement",
    example={"lord_of_house_in": {"house": 4, "houses": [12], "chart": "natal"}},
)
def lord_of_house_in(ctx: EvalContext, p: LordOfHouseIn) -> Outcome:
    """Check that the lord of house ``house`` sits in one of ``houses``.

    BPHS ch. 24 (Bhavesha-phala): the effects of the lord of each house
    placed in each house. Houses are whole signs counted from the Lagna
    (default) or another point, in the chart now or the natal chart; sign
    lords are the Parashari rulers (no node lordship).
    """
    sky = p.sky(ctx)
    lord = lord_of(sky, p.from_, p.house)
    where = house_from(sky.sign(p.from_), sky.sign(lord))
    held = where in p.houses
    return Outcome(
        held,
        f"the {ordinal(p.house)} lord {_where(p)} is {lord}, in the "
        f"{ordinal(where)} ({SIGN_NAMES[sky.sign(lord)]})"
        + ("" if held else ", not " + ", ".join(ordinal(h) for h in p.houses)),
    )


class MaleficInHouse(Params):
    """Parameters of ``malefic_in_house``."""

    houses: HouseList
    malefics: PlanetList = Field(default_factory=lambda: list(NATURAL_MALEFICS))
    count_gte: int = Field(default=1, ge=1, le=9)
    from_: PointName = Field(default=LAGNA, alias="from")
    chart: Literal["now", "natal"] = "now"

    inputs = ChartChoice.inputs
    sky = ChartChoice.sky


@predicate(
    "malefic_in_house",
    MaleficInHouse,
    category="placement",
    example={"malefic_in_house": {"houses": [6], "count_gte": 1}},
)
def malefic_in_house(ctx: EvalContext, p: MaleficInHouse) -> Outcome:
    """Check that at least ``count_gte`` malefics occupy the listed houses.

    Natural malefics after BPHS ch. 3 (Graha-guna-svarupa): the Sun, Mars,
    Saturn, Rahu and Ketu (the waning Moon and an afflicted Mercury are
    left out; list them in ``malefics`` to include them).
    """
    sky = p.sky(ctx)
    origin = sky.sign(p.from_)
    inside = [m for m in p.malefics if house_from(origin, sky.sign(m)) in p.houses]
    held = len(inside) >= p.count_gte
    houses = ", ".join(ordinal(h) for h in p.houses)
    return Outcome(
        held,
        f"malefics in the {houses} {_where(p)}: "
        f"{', '.join(inside) if inside else 'none'} ({p.count_gte} needed)",
    )


class LordsConjoined(Params):
    """Parameters of ``lords_conjoined``."""

    houses: List[int] = Field(min_length=2, max_length=4)
    in_houses: Optional[List[int]] = None
    from_: PointName = Field(default=LAGNA, alias="from")
    chart: Literal["now", "natal"] = "now"

    inputs = ChartChoice.inputs
    sky = ChartChoice.sky

    @field_validator("houses", "in_houses", mode="before")
    @classmethod
    def _range(cls, value):
        value = _listify(value)
        if value is not None and any(not 1 <= int(h) <= 12 for h in value):
            raise ValueError("houses are 1-12")
        return value


@predicate(
    "lords_conjoined",
    LordsConjoined,
    category="placement",
    example={"lords_conjoined": {"houses": [6, 1]}},
)
def lords_conjoined(ctx: EvalContext, p: LordsConjoined) -> Outcome:
    """Check that the lords of the listed houses occupy one sign (yuti).

    BPHS ch. 41 (Raja-yogas) counts the association (sambandha) of house
    lords by conjunction, mutual aspect or exchange; this predicate tests
    conjunction in one sign. When two houses share a lord (Mars rules
    Aries and Scorpio) the lord is conjoined with itself. ``in_houses``
    also asks that sign to be one of those houses.
    """
    sky = p.sky(ctx)
    origin = sky.sign(p.from_)
    lords = [lord_of(sky, p.from_, h) for h in p.houses]
    signs = {sky.sign(lord) for lord in lords}
    held = len(signs) == 1
    where = house_from(origin, next(iter(signs))) if held else None
    if held and p.in_houses is not None:
        held = where in p.in_houses
    placed = "; ".join(
        f"{ordinal(h)} lord {lord} in {SIGN_NAMES[sky.sign(lord)]}"
        for h, lord in zip(p.houses, lords)
    )
    tail = ""
    if where is not None:
        tail = f", together in the {ordinal(where)}"
    if p.in_houses is not None:
        tail += " (wanted " + ", ".join(ordinal(h) for h in p.in_houses) + ")"
    return Outcome(held, f"{placed} {_where(p)}{tail}")


# -------------------------------------------------------------- elements
class AfflictedElement(Params):
    """Parameters of ``afflicted_element``."""

    element: Literal["fire", "earth", "air", "water"]
    malefics: PlanetList = Field(default_factory=lambda: list(NATURAL_MALEFICS))
    count_gte: int = Field(default=1, ge=1, le=9)


@predicate(
    "afflicted_element",
    AfflictedElement,
    category="mundane",
    example={"afflicted_element": {"element": "fire", "count_gte": 2}},
)
def afflicted_element(ctx: EvalContext, p: AfflictedElement) -> Outcome:
    """Check that malefics occupy signs of one element.

    The four elements (tattvas) of the signs after BPHS ch. 4
    (Rashi-svarupa): fire Aries, Leo, Sagittarius; earth Taurus, Virgo,
    Capricorn; air Gemini, Libra, Aquarius; water Cancer, Scorpio, Pisces.
    The element is "afflicted" when at least ``count_gte`` natural malefics
    (BPHS ch. 3) occupy its signs, the occupation reading of affliction.
    """
    signs = ELEMENT_SIGNS[p.element]
    inside = [m for m in p.malefics if SIGN_NAMES[ctx.sky.sign(m)] in signs]
    held = len(inside) >= p.count_gte
    listed = ", ".join(f"{m} in {SIGN_NAMES[ctx.sky.sign(m)]}" for m in inside)
    return Outcome(
        held,
        f"malefics in {p.element} signs ({', '.join(signs)}): "
        f"{listed or 'none'} ({p.count_gte} needed)",
    )


# ---------------------------------------------------------------- cycles
class CycleResonance(Params):
    """Parameters of ``cycle_resonance``."""

    reference: AwareDatetime
    period_years: float = Field(gt=0, le=1000)
    tolerance_years: float = Field(ge=0, le=50)
    anchor: Optional[str] = None

    @model_validator(mode="after")
    def _tolerance(self):
        if self.tolerance_years * 2 >= self.period_years:
            raise ValueError("tolerance_years must be less than half the period")
        return self


@predicate(
    "cycle_resonance",
    CycleResonance,
    category="time",
    example={
        "cycle_resonance": {
            "reference": "2020-12-21T18:20:00Z",
            "period_years": 60,
            "tolerance_years": 3,
            "anchor": "Jupiter-Saturn conjunction",
        }
    },
)
def cycle_resonance(ctx: EvalContext, p: CycleResonance) -> Outcome:
    """Check that the moment is within ``tolerance_years`` of a cycle return.

    Years since ``reference`` (Julian years of 365.25 days, either side)
    are taken modulo ``period_years``; the rule holds when that phase is
    within the tolerance of 0 or of a full period. Brihat Samhita ch. 8
    (Brihaspati-chara) sets the sixty-year cycle of Jupiter, which is also
    three Jupiter-Saturn conjunction periods of about 19.86 years; the
    reference is usually a dated conjunction or a historical anchor.
    """
    moment: datetime = ctx.sky.moment
    years = (moment - p.reference).total_seconds() / 86400.0 / JULIAN_YEAR_DAYS
    phase = years % p.period_years
    distance = min(phase, p.period_years - phase)
    held = distance <= p.tolerance_years
    name = p.anchor or f"{p.reference:%Y-%m-%d}"
    return Outcome(
        held,
        f"{years:.1f} years from {name}: {distance:.1f} years from a "
        f"{p.period_years:g}-year return "
        f"({'within' if held else 'outside'} {p.tolerance_years:g})",
    )


# ----------------------------------------------------------- relations
class ConjOrAspect(Params):
    """Parameters of ``conjunction_or_mutual_aspect``."""

    planet: PlanetName
    others: PlanetList
    orb: Optional[float] = Field(default=None, gt=0, le=30)


def _aspects(sky: Sky, a: str, b: str) -> bool:
    return house_from(sky.sign(a), sky.sign(b)) in GRAHA_DRISHTI[a]


@predicate(
    "conjunction_or_mutual_aspect",
    ConjOrAspect,
    category="relation",
    example={
        "conjunction_or_mutual_aspect": {
            "planet": "Mars",
            "others": ["Saturn", "Jupiter"],
        }
    },
)
def conjunction_or_mutual_aspect(ctx: EvalContext, p: ConjOrAspect) -> Outcome:
    """Check that the planet is conjunct, or in mutual aspect with, any of ``others``.

    Sambandha after BPHS ch. 41 and the graha drishti of ch. 26: two
    planets are related when they share a sign (or, with ``orb``, are
    within ``orb`` degrees) or when each casts a whole-sign aspect on the
    other (every planet the 7th; Mars also 4th and 8th, Jupiter 5th and
    9th, Saturn 3rd and 10th; the nodes the 7th only).
    """
    sky = ctx.sky
    hits = []
    for other in p.others:
        if other == p.planet:
            continue
        if p.orb is not None:
            sep = angular_separation(sky.lon(p.planet), sky.lon(other))
            conj = sep <= p.orb
            how = f"{sep:.1f} deg apart"
        else:
            conj = sky.sign(p.planet) == sky.sign(other)
            how = f"both in {SIGN_NAMES[sky.sign(other)]}"
        if conj:
            hits.append(f"{p.planet} conjunct {other} ({how})")
        elif _aspects(sky, p.planet, other) and _aspects(sky, other, p.planet):
            hits.append(
                f"{p.planet} in {SIGN_NAMES[sky.sign(p.planet)]} and {other} in "
                f"{SIGN_NAMES[sky.sign(other)]} aspect each other"
            )
    if hits:
        return Outcome(True, "; ".join(hits))
    return Outcome(
        False,
        f"{sky.describe(p.planet)}; no conjunction or mutual aspect with "
        + ", ".join(f"{o} in {SIGN_NAMES[sky.sign(o)]}" for o in p.others),
    )


__all__ = ["ELEMENT_SIGNS", "NATURAL_MALEFICS", "lord_of"]
