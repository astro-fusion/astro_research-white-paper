"""Transit table of an event against a candidate natal chart (WP-53, ADR-006 4.3).

One block per catalogued transit reading. Core readings (``transit.gochara_moon``,
``transit.from_lagna``, ``transit.conjunct_natal``) are in ``readings["core"]``;
extended readings (``transit.over_varga``, ``transit.in_varga``) are kept in a
separate block, ``readings["extended"]``, and never enter the aggregate report.

Two windows are sampled. The event's own time window (fast transiting grahas,
chiefly the Moon) and the natal chart's founding-time window (natal Moon sign,
lagna, varga lagna). A value that takes more than one value across either window
is listed with every value and marked ``stable: false``. A date-only natal
chart uses local noon with the grade D half-window.
"""

from datetime import datetime, time, timedelta, timezone
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

from vedic_astrology_core.astrology.divisional import varga_sign
from vedic_astrology_core.mundane.catalogue import Catalogue, load_catalogue
from vedic_astrology_core.mundane.eventsky import (
    EVENT_HALF_WINDOW_MINUTES,
    distinct,
    method_info,
    window_instants,
)
from vedic_astrology_core.mundane.registry import Chart, Event
from vedic_astrology_core.rules.context import Location, Sky
from vedic_astrology_core.rules.vocabulary import PLANET_NAMES, SIGN_NAMES
from vedic_astrology_core.utils.datetime_utils import require_aware

CORE_READINGS = ("transit.gochara_moon", "transit.from_lagna", "transit.conjunct_natal")
EXTENDED_READINGS = ("transit.over_varga", "transit.in_varga")
#: Orb of ``transit.conjunct_natal`` in degrees (the example value of the predicate).
DEFAULT_ORB = 3.0
#: Cap on samples per window when two windows are crossed pairwise.
CROSS_SAMPLES = 25


def _thin(items: List[Any], n: int = CROSS_SAMPLES) -> List[Any]:
    if len(items) <= n:
        return items
    idx = sorted({round(i * (len(items) - 1) / (n - 1)) for i in range(n)})
    return [items[i] for i in idx]


def natal_moment(chart: Chart) -> datetime:
    """Founding instant (UTC); local noon for a date-only chart."""
    inst = chart.founding_instant()
    if inst is not None:
        return inst
    tz = (timezone(timedelta(hours=chart.lon / 15.0)) if chart.time_zone == "LMT"
          else ZoneInfo(chart.time_zone))
    return datetime.combine(chart.date, time(12, 0)).replace(tzinfo=tz).astimezone(timezone.utc)


def _house(sign: int, base: int) -> int:
    return (sign - base) % 12 + 1


def _event_skies(event: Event) -> Optional[List[Sky]]:
    half = EVENT_HALF_WINDOW_MINUTES.get(event.time_precision)
    if half is None:
        return None
    return [Sky(t) for t in window_instants(require_aware(event.time_utc, "event time"), half)]


def _natal_skies(chart: Chart, half: float):
    place = Location(chart.lat, chart.lon, chart.time_zone if chart.time_zone != "LMT" else "UTC")
    return [Sky(t, place) for t in window_instants(natal_moment(chart), half)]


def _position_rows(nominal: Sky, skies: List[Sky]) -> List[Dict[str, Any]]:
    rows = []
    for g in PLANET_NAMES:
        rec = nominal.record(g)
        signs = distinct(s.sign(g) for s in skies)
        rows.append({
            "graha": g,
            "longitude": round(nominal.lon(g), 4),
            "sign": SIGN_NAMES[nominal.sign(g)],
            "nakshatra": nominal.nakshatra(g)["name"],
            "speed": round(float(rec["longitude_speed"]), 5),
            "retrograde": bool(rec["retrograde"]),
            "signs_across_window": [SIGN_NAMES[i] for i in signs],
            "stable": len(signs) == 1,
        })
    return rows


def _house_rows(ev_skies, nominal, natal_values: List[int], natal_nominal: int,
                transit_sign) -> List[Dict[str, Any]]:
    """House of each transit sign from a natal base sign, over both windows."""
    rows = []
    for g in PLANET_NAMES:
        t_signs = distinct(transit_sign(s, g) for s in ev_skies)
        houses = sorted({_house(t, b) for t in t_signs for b in natal_values})
        rows.append({
            "graha": g,
            "house": _house(transit_sign(nominal, g), natal_nominal),
            "houses_across_windows": houses,
            "stable": len(houses) == 1,
            "fast": len(t_signs) > 1,
        })
    return rows


def transit_table(
    event: Event, chart: Chart, *, catalogue: Optional[Catalogue] = None, orb: float = DEFAULT_ORB
) -> Dict[str, Any]:
    """Transit table of ``event`` against the natal chart ``chart`` (case-file section 4)."""
    cat = catalogue or load_catalogue()
    out: Dict[str, Any] = {
        "event_id": event.event_id,
        "chart_id": chart.chart_id,
        "chart_grade": chart.grade,
        "moment_utc": event.time_utc.astimezone(timezone.utc).isoformat(),
        "readings": {"core": {}, "extended": {}},
    }
    ev_skies = _event_skies(event)
    if ev_skies is None:
        out.update(computable=False, reason=f"event time precision {event.time_precision!r} is excluded")
        return out
    nat_half = chart.half_window
    if nat_half is None:
        out.update(computable=False, reason=f"chart grade {chart.grade} has no founding-time window")
        return out

    nominal = Sky(require_aware(event.time_utc, "event time"))
    nat_skies = _natal_skies(chart, nat_half)
    nat_nominal = Sky(natal_moment(chart), nat_skies[0].place)
    out.update(
        computable=True,
        event_window_half_minutes=EVENT_HALF_WINDOW_MINUTES[event.time_precision],
        natal_window_half_minutes=nat_half,
        natal_time_known=chart.time is not None,
        positions=_position_rows(nominal, ev_skies),
    )
    info = {mid: method_info(cat, mid) for mid in CORE_READINGS + EXTENDED_READINGS}
    core, ext = out["readings"]["core"], out["readings"]["extended"]
    sign_of = lambda s, g: s.sign(g)

    moon_signs = distinct(n.sign("Moon") for n in nat_skies)
    core["transit.gochara_moon"] = {
        "method": info["transit.gochara_moon"],
        "natal_moon_sign_values": [SIGN_NAMES[i] for i in moon_signs],
        "rows": _house_rows(ev_skies, nominal, moon_signs, nat_nominal.sign("Moon"), sign_of),
    }
    lag_signs = distinct(n.sign("Lagna") for n in nat_skies)
    core["transit.from_lagna"] = {
        "method": info["transit.from_lagna"],
        "natal_lagna_sign_values": [SIGN_NAMES[i] for i in lag_signs],
        "rows": _house_rows(ev_skies, nominal, lag_signs, nat_nominal.sign("Lagna"), sign_of),
    }

    points = list(PLANET_NAMES) + ["Lagna"]
    ev_thin, nat_thin = _thin(ev_skies), _thin(nat_skies)

    def sep(a: float, b: float) -> float:
        d = abs(a - b) % 360.0
        return min(d, 360.0 - d)

    conj = []
    for g in PLANET_NAMES:
        for p in points:
            held = {sep(e.lon(g), n.lon(p)) <= orb for e in ev_thin for n in nat_thin}
            nominal_held = sep(nominal.lon(g), nat_nominal.lon(p)) <= orb
            if nominal_held or True in held:
                conj.append({
                    "graha": g, "natal_point": p, "orb": orb,
                    "separation": round(sep(nominal.lon(g), nat_nominal.lon(p)), 3),
                    "held_at_nominal": nominal_held,
                    "stable": len(held) == 1,
                })
    core["transit.conjunct_natal"] = {"method": info["transit.conjunct_natal"], "orb": orb, "rows": conj}

    # extended readings: natal D9 lagna (fast, sampled every few minutes)
    d9 = distinct(varga_sign(n.lon("Lagna"), 9) for n in nat_skies)
    d9_nom = varga_sign(nat_nominal.lon("Lagna"), 9)
    note = None if chart.time is not None else "natal time unknown: the D9 lagna takes every value"
    ext["transit.over_varga"] = {
        "method": info["transit.over_varga"],
        "varga": 9, "natal_d9_lagna_values": [SIGN_NAMES[i] for i in d9], "note": note,
        "rows": _house_rows(ev_skies, nominal, d9, d9_nom, sign_of),
    }
    ext["transit.in_varga"] = {
        "method": info["transit.in_varga"],
        "varga": 9, "natal_d9_lagna_values": [SIGN_NAMES[i] for i in d9], "note": note,
        "rows": _house_rows(ev_skies, nominal, d9, d9_nom, lambda s, g: varga_sign(s.lon(g), 9)),
    }
    return out


__all__ = ["CORE_READINGS", "EXTENDED_READINGS", "natal_moment", "transit_table"]
