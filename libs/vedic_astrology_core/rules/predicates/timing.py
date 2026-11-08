"""Time predicates: Vimshottari dasha, tithi and Moon phase, weekday lord."""

from datetime import datetime
from typing import List, Literal, Optional

import pytz
from pydantic import Field, field_validator, model_validator

from ..context import EvalContext, sunrise_before
from . import Outcome, Params, PlanetList, predicate

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


__all__ = ["WEEKDAY_LORDS", "tithi_words", "vara"]
