"""Event-time sky chart (ADR-006 section 2.1 section 5, WP-53).

The sky at the instant and place of an event: lagna at the epicentre, Moon
nakshatra and its Brihat Samhita ch. 32 mandala (``sky.bs32_mandala``),
tithi, weekday lord, the nearest eclipse on each side (``sky.eclipse``) and
the samvatsara (``sky.samvatsara``).

Three rules from the ADR are enforced here.

1. The lagna is computed only when the event has a place and a time to the
   hour or better. Otherwise the section says why it is missing.
2. Fast factors (lagna, Moon nakshatra, mandala, tithi, weekday lord) are
   evaluated across the event's own time window (the event's time precision,
   ADR-006 section 3.4) and marked unstable when they take more than one value.
3. **No aggregate count of an event-sky factor over events outside the
   Himalayan polygon** until the ADR-004 D2 test has a confirm record
   (``count_event_sky_factor``). The global catalogue stays untouched.

Every method used must have a catalogue entry; its citation status is copied
into the output so a reader sees the true status.
"""

import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence

import yaml

from vedic_astrology_core.astrology import mundane as bs
from vedic_astrology_core.mundane.catalogue import Catalogue, load_catalogue, repo_root
from vedic_astrology_core.mundane.registry import Event
from vedic_astrology_core.rules.context import Location, Sky, sunrise_before
from vedic_astrology_core.rules.eclipses import eclipses_between
from vedic_astrology_core.utils.datetime_utils import require_aware, julian_day_to_datetime

#: Half-window of the event's own time, minutes, by time precision
#: (studies/mundane/hypothesis.yaml: events.event_time_window; month is excluded).
EVENT_HALF_WINDOW_MINUTES = {"minute": 1.0, "hour": 30.0, "day": 720.0}
#: Precisions at which a lagna is meaningful.
LAGNA_PRECISIONS = ("minute", "hour")
#: Sampling step inside a window, minutes.
SAMPLE_STEP_MINUTES = 5.0
MAX_SAMPLES = 300

#: Python weekday() (Monday = 0) to lord of the vara.
WEEKDAY_LORDS = ["Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Sun"]

D2_CONFIRM_RECORD = repo_root() / "data" / "registry" / "mundane" / "d2_confirm_record.json"
EARTHQUAKE_HYPOTHESIS = repo_root() / "studies" / "earthquake" / "hypothesis.yaml"

SKY_METHODS = ("sky.bs32_mandala", "sky.eclipse", "sky.samvatsara")


class EventSkyError(ValueError):
    """An event-sky computation is not allowed or not possible."""


class EventSkyGuardError(EventSkyError):
    """An aggregate count of an event-sky factor is blocked (ADR-004 D2)."""


# ------------------------------------------------------------ helpers
def window_instants(
    moment: datetime, half_minutes: float, step_minutes: float = SAMPLE_STEP_MINUTES
) -> List[datetime]:
    """Evenly spaced instants from moment-half to moment+half, ends included."""
    require_aware(moment, "moment")
    if half_minutes <= 0:
        return [moment]
    n = min(MAX_SAMPLES, max(2, math.ceil(2 * half_minutes / step_minutes)))
    start = moment - timedelta(minutes=half_minutes)
    width = 2 * half_minutes / n
    return [start + timedelta(minutes=width * i) for i in range(n + 1)]


def distinct(values: Iterable[Any]) -> List[Any]:
    """Distinct values in first-seen order."""
    out: List[Any] = []
    for v in values:
        if v not in out:
            out.append(v)
    return out


def method_info(catalogue: Catalogue, method_id: str) -> Dict[str, Any]:
    """Catalogue status of a method; an unknown id raises."""
    m = catalogue.get(method_id)
    return {
        "id": m.id,
        "tier": m.tier,
        "tradition": m.tradition,
        "citation_status": m.citation_status(catalogue.root),
        "level": m.level(catalogue.root),
    }


def _marked(value: Any, values: List[Any]) -> Dict[str, Any]:
    return {"value": value, "values_across_window": values, "stable": len(values) == 1}


def _tithi(jd: float) -> int:
    return int(bs.elongation(jd) // 12.0) + 1


def tithi_name(tithi: int) -> str:
    """Name a tithi 1-30: "Shukla 5", "Purnima", "Krishna 3", "Amavasya"."""
    if tithi == 15:
        return "Purnima"
    if tithi == 30:
        return "Amavasya"
    return f"Shukla {tithi}" if tithi < 15 else f"Krishna {tithi - 15}"


def vara(moment: datetime, place: Optional[Location]) -> Dict[str, Any]:
    """Weekday and its lord. With a place the day runs sunrise to sunrise."""
    convention = "utc_civil_day"
    local = moment
    if place is not None:
        sr = sunrise_before(moment, place)
        shift = timedelta(hours=place.lon / 15.0)
        if sr is not None:
            local, convention = sr + shift, "sunrise_to_sunrise"
        else:
            local, convention = moment + shift, "local_mean_civil_day"
    wd = local.weekday()
    return {"weekday": wd, "lord": WEEKDAY_LORDS[wd], "convention": convention}


# ------------------------------------------------------------ polygon guard
def himalayan_polygon(path: Path = EARTHQUAKE_HYPOTHESIS) -> List[tuple]:
    """Closed (lon, lat) polygon of the registered Himalayan arc."""
    region = yaml.safe_load(Path(path).read_text(encoding="utf-8"))["region"]
    trace = [(float(a), float(b)) for a, b in region["mft_trace_lon_lat"]]
    south = [(x, y - float(region["south_offset_deg"])) for x, y in trace]
    north = [(x, y + float(region["north_offset_deg"])) for x, y in reversed(trace)]
    return south + north + [south[0]]


def in_himalayan_polygon(lat: Optional[float], lon: Optional[float]) -> bool:
    """Whether a point lies inside the registered polygon (False if unknown)."""
    if lat is None or lon is None:
        return False
    poly = himalayan_polygon()
    inside = False
    for (x1, y1), (x2, y2) in zip(poly, poly[1:]):
        if (y1 > lat) != (y2 > lat) and lon < (x2 - x1) * (lat - y1) / (y2 - y1) + x1:
            inside = not inside
    return inside


def d2_confirm_recorded(path: Path = D2_CONFIRM_RECORD) -> bool:
    """True only when the ADR-004 D2 test has a confirm record on disk.

    The record is a JSON file with a non-empty ``confirm_run_id``. No such file
    exists today, so the guard stays closed.
    """
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    return bool(isinstance(data, dict) and str(data.get("confirm_run_id", "")).strip())


def count_event_sky_factor(
    events: Sequence[Event],
    factor: Callable[[Dict[str, Any]], bool],
    *,
    method_id: str = "sky.bs32_mandala",
    catalogue: Optional[Catalogue] = None,
    d2_confirmed: Optional[bool] = None,
) -> int:
    """Count events whose event-sky satisfies ``factor`` (an aggregate count).

    Raises :class:`EventSkyGuardError` if any event lies outside the Himalayan
    polygon (or has no place) while the D2 confirm record is missing. The check
    runs before any chart is computed.
    """
    cat = catalogue or load_catalogue()
    if cat.get(method_id).family != "sky":
        raise EventSkyError(f"{method_id!r} is not an event-sky method")
    confirmed = d2_confirm_recorded() if d2_confirmed is None else d2_confirmed
    if not confirmed:
        outside = [e.event_id for e in events if not in_himalayan_polygon(e.lat, e.lon)]
        if outside:
            raise EventSkyGuardError(
                f"{len(outside)} event(s) lie outside the Himalayan polygon "
                f"(first: {outside[0]}); no event-sky factor may be counted over them "
                "until the ADR-004 D2 test has its confirm record"
            )
    return sum(1 for e in events if factor(event_sky(e, catalogue=cat)))


# ------------------------------------------------------------ the sky
def _nearest_eclipses(jd: float) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for span in (200.0, 420.0):
        found = eclipses_between(jd - span, jd + span, "any")
        before = [e for e in found if e.jd <= jd]
        after = [e for e in found if e.jd > jd]
        if before and after:
            break
    for key, e in (("before", before[-1] if before else None), ("after", after[0] if after else None)):
        out[key] = None if e is None else {
            "kind": e.kind,
            "subtype": e.subtype,
            "moment_utc": e.moment.isoformat(),
            "days_from_event": round(e.jd - jd, 4),
            "sidereal_longitude": round(e.longitude, 4),
        }
    return out


def event_sky(
    event: Event, *, catalogue: Optional[Catalogue] = None, d2_confirmed: Optional[bool] = None
) -> Dict[str, Any]:
    """The event-time sky chart of one event (case-file section 5)."""
    cat = catalogue or load_catalogue()
    methods = {mid: method_info(cat, mid) for mid in SKY_METHODS}
    moment = require_aware(event.time_utc, "event time")
    base: Dict[str, Any] = {
        "event_id": event.event_id,
        "moment_utc": moment.astimezone(timezone.utc).isoformat(),
        "time_precision": event.time_precision,
        "methods": methods,
    }
    half = EVENT_HALF_WINDOW_MINUTES.get(event.time_precision)
    if half is None:
        base.update(computable=False, reason=f"time precision {event.time_precision!r} is excluded (no event-time window)")
        return base

    has_place = event.lat is not None and event.lon is not None
    place = Location(float(event.lat), float(event.lon), "UTC") if has_place else None
    instants = window_instants(moment, half)
    skies = [Sky(t, place) for t in instants]
    nominal = Sky(moment, place)

    # lagna
    if event.time_precision not in LAGNA_PRECISIONS:
        lagna: Dict[str, Any] = {"computed": False, "reason": f"time precision is {event.time_precision}; a lagna needs hour or better"}
    elif place is None:
        lagna = {"computed": False, "reason": "the event has no place"}
    else:
        signs = distinct(s.sign("Lagna") for s in skies)
        lagna = {"computed": True, "longitude": round(nominal.lon("Lagna"), 4),
                 **_marked(nominal.sign("Lagna"), signs)}

    # Moon nakshatra and mandala
    naks = distinct(s.nakshatra("Moon")["name"] for s in skies)
    nk = nominal.nakshatra("Moon")
    mandalas = distinct(bs.mandala_of(n) for n in naks)
    tithis = distinct(_tithi(s.jd) for s in skies)
    t0 = _tithi(nominal.jd)
    varas = distinct(vara(t, place)["lord"] for t in instants)
    v0 = vara(moment, place)
    jd = nominal.jd
    sv_name, sv_index, sv_start = bs.samvatsara(jd)

    base.update(
        computable=True,
        window_half_minutes=half,
        place=None if place is None else {"lat": place.lat, "lon": place.lon},
        lagna=lagna,
        moon_nakshatra={"longitude": round(nominal.lon("Moon"), 4), "pada": nk["pada"],
                        **_marked(nk["name"], naks)},
        mandala={"method": "sky.bs32_mandala",
                 **_marked(bs.mandala_of(nk["name"]), mandalas)},
        tithi={"name": tithi_name(t0), **_marked(t0, tithis)},
        weekday_lord={"weekday": v0["weekday"], "convention": v0["convention"], **_marked(v0["lord"], varas)},
        eclipses=_nearest_eclipses(jd),
        samvatsara={"name": sv_name, "index": sv_index, "starts_utc": sv_start.isoformat(),
                    "convention": "Chaitra Shukla Pratipada, Prabhava = 1987 (a parameter, ADR-006 section 4.3)"},
        aggregate_guard="aggregate counts over events outside the Himalayan polygon raise until the ADR-004 D2 confirm record exists",
    )
    return base


__all__ = [
    "EventSkyError", "EventSkyGuardError", "EVENT_HALF_WINDOW_MINUTES", "count_event_sky_factor",
    "d2_confirm_recorded", "event_sky", "himalayan_polygon", "in_himalayan_polygon",
    "tithi_name", "vara", "window_instants",
]
