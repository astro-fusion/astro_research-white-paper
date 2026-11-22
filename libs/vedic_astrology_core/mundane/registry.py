"""Chart and event registries for the retrospective mundane engine (ADR-006 WP-49).

Two committed files are read here:

* `data/registry/mundane/charts.yaml` (ADR-006 section 6.1): candidate founding charts.
* `data/registry/mundane/events.jsonl` (section 6.2): the event registry.

The chart grade (A, B, C, D, R, X) is never stored. It is computed by
:func:`chart_grade` from the evidence fields, so a hand-typed grade is a schema error
(ADR-006 section 3.3, same rule as ADR-004 D-4).

Everything is strict: an unknown key, a missing required key or a bad value raises
:class:`RegistryError` naming the record and the field.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Union
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import yaml

from vedic_astrology_core.stats.manifest import file_sha256

REPO_ROOT = Path(__file__).resolve().parents[3]
REGISTRY_DIR = REPO_ROOT / "data" / "registry" / "mundane"
CHARTS_FILE = REGISTRY_DIR / "charts.yaml"
EVENTS_FILE = REGISTRY_DIR / "events.jsonl"

GRADES = ("A", "B", "C", "D", "R", "X")
#: Default half-window in minutes per grade (ADR-006 section 3.3). R and X have none.
GRADE_HALF_WINDOW_MINUTES = {"A": 2.0, "B": 15.0, "C": 60.0, "D": 720.0}
TIME_EVIDENCE_KINDS = (
    "primary_record",
    "press",
    "secondary",
    "convention",
    "rectified",
    "none",
)
CLAIMED_CONFIDENCE = ("documented", "conventional", "disputed")
EVENT_TYPES = (
    "earthquake",
    "flood",
    "war_start",
    "coup",
    "disaster",
    "market_move",
)
TIME_PRECISIONS = ("minute", "hour", "day", "month")


class RegistryError(ValueError):
    """A registry record breaks the contract."""


class ChartNotApplicable(RegistryError):
    """The chart cannot be used for this event (before the chart existed)."""


# --------------------------------------------------------------- helpers
def _check_keys(
    obj: Any, where: str, required: Sequence[str], optional: Sequence[str] = ()
) -> None:
    if not isinstance(obj, dict):
        raise RegistryError(f"{where}: expected a mapping, got {type(obj).__name__}")
    unknown = sorted(set(obj) - set(required) - set(optional))
    if unknown:
        raise RegistryError(f"{where}: unknown key(s) {unknown}")
    missing = [k for k in required if k not in obj]
    if missing:
        raise RegistryError(f"{where}: missing key(s) {missing}")


def _as_date(value: Any, where: str) -> date:
    if isinstance(value, datetime):
        raise RegistryError(f"{where}: expected a date, got a datetime")
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except ValueError as exc:
        raise RegistryError(f"{where}: bad date {value!r}") from exc


def _as_time(value: Any, where: str) -> Optional[time]:
    if value is None:
        return None
    if isinstance(value, time):
        return value
    if isinstance(value, int):  # YAML 1.1 reads 00:01:00 as a sexagesimal int
        raise RegistryError(f"{where}: time must be a quoted HH:MM:SS string")
    try:
        return time.fromisoformat(str(value))
    except ValueError as exc:
        raise RegistryError(f"{where}: bad time {value!r}") from exc


def _number(value: Any, where: str, lo: float, hi: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise RegistryError(f"{where}: expected a number, got {value!r}")
    if not lo <= float(value) <= hi:
        raise RegistryError(f"{where}: {value} outside [{lo}, {hi}]")
    return float(value)


def _tz(name: str, where: str):
    if name == "LMT":
        return "LMT"
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError, OSError) as exc:
        raise RegistryError(f"{where}: unknown time zone {name!r}") from exc


def _utc(value: datetime, where: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{where}: naive datetime; timezone-aware required")
    return value.astimezone(timezone.utc)


# ---------------------------------------------------------------- charts
@dataclass(frozen=True)
class Chart:
    """One validated founding chart candidate (section 6.1)."""

    chart_id: str
    country_iso: str
    event: str
    date: date
    time: Optional[time]
    time_zone: str
    place: str
    lat: float
    lon: float
    time_evidence: Dict[str, Any]
    half_window_minutes: Optional[float]
    used_by: List[str]
    claimed_confidence: str
    valid_from: date
    notes: str
    date_disputed: bool = False

    @property
    def grade(self) -> str:
        """Grade computed from the evidence fields."""
        return chart_grade(self)

    @property
    def half_window(self) -> Optional[float]:
        """Half-window in minutes (override, else from the grade); None when excluded."""
        return half_window_minutes(self)

    def founding_instant(self) -> Optional[datetime]:
        """Founding moment as an aware UTC datetime; None for a date-only chart."""
        return founding_instant_utc(self)


_SOURCE_KEYS = ("title", "url", "archive_url", "accessed", "quote")
_EVIDENCE_REQUIRED = (
    "kind",
    "stated_precision_minutes",
    "source",
    "checked_by",
    "checked_at",
    "rectified",
    "rectification_published",
)
_CHART_REQUIRED = (
    "chart_id",
    "country_iso",
    "event",
    "founding",
    "time_evidence",
    "half_window_minutes",
    "used_by",
    "claimed_confidence",
    "valid_from",
    "notes",
)
_FOUNDING_KEYS = ("date", "time", "time_zone", "place", "lat", "lon")


def parse_chart(raw: Dict[str, Any]) -> Chart:
    """Validate one chart mapping and return a :class:`Chart`."""
    where = f"chart {raw.get('chart_id', '?') if isinstance(raw, dict) else '?'}"
    if isinstance(raw, dict) and "grade" in raw:
        raise RegistryError(f"{where}: grade is computed, never typed")
    _check_keys(raw, where, _CHART_REQUIRED, ("date_disputed",))
    cid = raw["chart_id"]
    if not isinstance(cid, str) or not re.fullmatch(r"[a-z]{2}-[a-z0-9][a-z0-9-]*", cid):
        raise RegistryError(f"{where}: chart_id must look like 'in-1947-midnight'")
    iso = raw["country_iso"]
    if not isinstance(iso, str) or not re.fullmatch(r"[A-Z]{2}", iso):
        raise RegistryError(f"{where}: country_iso must be two capital letters")
    if iso.lower() != cid[:2]:
        raise RegistryError(f"{where}: chart_id prefix must match country_iso")
    f = raw["founding"]
    _check_keys(f, f"{where}.founding", _FOUNDING_KEYS)
    fdate = _as_date(f["date"], f"{where}.founding.date")
    ftime = _as_time(f["time"], f"{where}.founding.time")
    _tz(str(f["time_zone"]), f"{where}.founding.time_zone")
    lat = _number(f["lat"], f"{where}.founding.lat", -90, 90)
    lon = _number(f["lon"], f"{where}.founding.lon", -180, 180)

    ev = raw["time_evidence"]
    _check_keys(ev, f"{where}.time_evidence", _EVIDENCE_REQUIRED)
    if ev["kind"] not in TIME_EVIDENCE_KINDS:
        raise RegistryError(f"{where}.time_evidence.kind: {ev['kind']!r} not allowed")
    if ev["stated_precision_minutes"] is not None:
        _number(ev["stated_precision_minutes"], f"{where}.stated_precision_minutes", 0, 1e6)
    if not isinstance(ev["rectified"], bool):
        raise RegistryError(f"{where}.time_evidence.rectified must be a bool")
    if ev["rectified"]:
        # null is allowed: the chart is then never eligible for aggregate use.
        if ev["rectification_published"] is not None:
            _as_date(ev["rectification_published"], f"{where}.rectification_published")
    elif ev["rectification_published"] is not None:
        raise RegistryError(f"{where}: rectification_published set but rectified is false")
    src = ev["source"]
    if src is not None:
        _check_keys(src, f"{where}.time_evidence.source", (), _SOURCE_KEYS)
    if (ev["checked_by"] is None) != (ev["checked_at"] is None):
        raise RegistryError(f"{where}: checked_by and checked_at go together")
    if ev["checked_by"] is not None and not src:
        raise RegistryError(f"{where}: checked_by given but no source")
    if ftime is None and ev["kind"] not in ("none",):
        raise RegistryError(f"{where}: date-only chart must have time_evidence.kind 'none'")
    if ftime is not None and ev["kind"] == "none":
        raise RegistryError(f"{where}: a timed chart cannot have time_evidence.kind 'none'")

    hw = raw["half_window_minutes"]
    if hw is not None:
        hw = _number(hw, f"{where}.half_window_minutes", 0, 1440)
    if not isinstance(raw["used_by"], list):
        raise RegistryError(f"{where}.used_by must be a list")
    if raw["claimed_confidence"] not in CLAIMED_CONFIDENCE:
        raise RegistryError(f"{where}.claimed_confidence not in {CLAIMED_CONFIDENCE}")
    valid_from = _as_date(raw["valid_from"], f"{where}.valid_from")
    if valid_from < fdate:
        raise RegistryError(f"{where}: valid_from precedes the founding date")
    disputed = raw.get("date_disputed", False)
    if not isinstance(disputed, bool):
        raise RegistryError(f"{where}.date_disputed must be a bool")
    return Chart(
        chart_id=cid,
        country_iso=iso,
        event=str(raw["event"]),
        date=fdate,
        time=ftime,
        time_zone=str(f["time_zone"]),
        place=str(f["place"]),
        lat=lat,
        lon=lon,
        time_evidence=dict(ev),
        half_window_minutes=hw,
        used_by=[str(x) for x in raw["used_by"]],
        claimed_confidence=raw["claimed_confidence"],
        valid_from=valid_from,
        notes=str(raw["notes"] or ""),
        date_disputed=disputed,
    )


def load_charts(path: Union[str, Path] = CHARTS_FILE) -> List[Chart]:
    """Load and validate `charts.yaml` (a list of chart mappings)."""
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise RegistryError(f"{path}: top level must be a list of charts")
    charts = [parse_chart(c) for c in data]
    ids = [c.chart_id for c in charts]
    dup = sorted({i for i in ids if ids.count(i) > 1})
    if dup:
        raise RegistryError(f"{path}: duplicate chart_id {dup} (ids are never reused)")
    return charts


# ----------------------------------------------------------------- grade
def _checked(ev: Dict[str, Any]) -> bool:
    return bool(ev.get("checked_by")) and bool(ev.get("checked_at")) and bool(ev.get("source"))


def chart_grade(chart: Chart) -> str:
    """Return the grade (A, B, C, D, R, X) computed from the evidence.

    Order of the rules: X (date disputed), R (rectified), D (date only), then
    A, B, C by source kind, precision and whether a maintainer opened the source.
    An unchecked source never grades above C.
    """
    ev = chart.time_evidence
    if chart.date_disputed:
        return "X"
    if ev["rectified"] or ev["kind"] == "rectified":
        return "R"
    if chart.time is None or ev["kind"] == "none":
        return "D"
    prec = ev["stated_precision_minutes"]
    src = ev["source"] or {}
    checked = _checked(ev)
    kind = ev["kind"]
    if (
        kind == "primary_record"
        and checked
        and src.get("archive_url")
        and prec is not None
        and prec <= 1
    ):
        return "A"
    if (
        checked
        and kind in ("primary_record", "press", "secondary")
        and prec is not None
        and prec <= 15
    ):
        return "B"
    if prec is not None and prec <= 60:
        return "C"
    return "D"


def half_window_minutes(chart: Chart) -> Optional[float]:
    """Half-window of the founding time in minutes; None for grade X.

    An explicit `half_window_minutes` wins. Grade R without one uses the
    author's stated precision, else 60 minutes (conservative).
    """
    grade = chart_grade(chart)
    if grade == "X":
        return None
    if chart.half_window_minutes is not None:
        return chart.half_window_minutes
    if grade == "R":
        prec = chart.time_evidence["stated_precision_minutes"]
        return float(prec) if prec is not None else 60.0
    return GRADE_HALF_WINDOW_MINUTES[grade]


# ------------------------------------------------------------ time zones
def founding_instant_utc(chart: Chart) -> Optional[datetime]:
    """Return the founding moment in UTC; `LMT` uses local mean time from longitude."""
    if chart.time is None:
        return None
    naive = datetime.combine(chart.date, chart.time)
    if chart.time_zone == "LMT":
        tz = timezone(timedelta(hours=chart.lon / 15.0))
    else:
        tz = ZoneInfo(chart.time_zone)
    return naive.replace(tzinfo=tz).astimezone(timezone.utc)


def _valid_from_instant(chart: Chart) -> datetime:
    start = datetime.combine(chart.valid_from, time(0, 0))
    if chart.time_zone == "LMT":
        tz = timezone(timedelta(hours=chart.lon / 15.0))
    else:
        tz = ZoneInfo(chart.time_zone)
    return start.replace(tzinfo=tz).astimezone(timezone.utc)


def chart_applies(chart: Chart, event_time: datetime) -> bool:
    """True when the chart may be used for an event at `event_time` (aware datetime).

    Raises :class:`ChartNotApplicable` for an event before `valid_from` or before the
    founding moment. A naive datetime raises `ValueError`.
    """
    t = _utc(event_time, "event_time")
    if t < _valid_from_instant(chart):
        raise ChartNotApplicable(
            f"{chart.chart_id}: event {t.isoformat()} is before valid_from {chart.valid_from}"
        )
    founded = founding_instant_utc(chart)
    if founded is not None and t < founded:
        raise ChartNotApplicable(
            f"{chart.chart_id}: event {t.isoformat()} precedes the founding moment"
        )
    return True


def aggregate_eligible(chart: Chart, event_time: datetime) -> bool:
    """True when the chart may enter the aggregate report for this event.

    Grade X never does. A rectified chart (grade R) does only for events after
    its rectification was published, and only when that date is proved by an
    archive capture. Applicability (`chart_applies`) is required for all.
    """
    t = _utc(event_time, "event_time")
    chart_applies(chart, t)
    grade = chart_grade(chart)
    if grade == "X":
        return False
    if grade == "R":
        ev = chart.time_evidence
        published = ev["rectification_published"]
        archive = (ev["source"] or {}).get("archive_url")
        if published is None or not archive:
            return False
        pub = datetime.combine(_as_date(published, "rectification_published"), time(0, 0))
        return t > pub.replace(tzinfo=timezone.utc) + timedelta(days=1)
    return True


# ---------------------------------------------------------------- events
_EVENT_REQUIRED = (
    "event_id",
    "event_type",
    "subtype",
    "country_iso",
    "time_utc",
    "time_precision",
    "lat",
    "lon",
    "location_precision_km",
    "severity",
    "cluster_id",
    "catalogue",
    "exhaustive",
    "source_url",
    "archive_url",
    "reviewed_by",
    "reviewed_at",
)
_EVENT_OPTIONAL = ("flags", "notes")
_SEVERITY_KEYS = ("scale", "value", "deaths", "loss", "native_magnitude", "native_type")


@dataclass(frozen=True)
class Event:
    """One validated event record (section 6.2)."""

    event_id: str
    event_type: str
    subtype: Optional[str]
    country_iso: Optional[Union[str, List[str]]]
    time_utc: datetime
    time_precision: str
    lat: Optional[float]
    lon: Optional[float]
    location_precision_km: Optional[float]
    severity: Dict[str, Any]
    cluster_id: Optional[str]
    catalogue: Dict[str, Any]
    exhaustive: bool
    source_url: Optional[str]
    archive_url: Optional[str]
    reviewed_by: Optional[str]
    reviewed_at: Optional[str]
    flags: Dict[str, Any]

    @property
    def in_aggregate(self) -> bool:
        """Only `exhaustive` events enter the aggregate report."""
        return self.exhaustive


def parse_event(raw: Dict[str, Any]) -> Event:
    """Validate one event mapping."""
    where = f"event {raw.get('event_id', '?') if isinstance(raw, dict) else '?'}"
    _check_keys(raw, where, _EVENT_REQUIRED, _EVENT_OPTIONAL)
    if not re.fullmatch(r"[a-z]+:[^\s]+", str(raw["event_id"])):
        raise RegistryError(f"{where}: event_id must look like 'usgs:<id>'")
    if raw["event_type"] not in EVENT_TYPES:
        raise RegistryError(f"{where}.event_type not in {EVENT_TYPES}")
    if raw["time_precision"] not in TIME_PRECISIONS:
        raise RegistryError(f"{where}.time_precision not in {TIME_PRECISIONS}")
    try:
        t = datetime.fromisoformat(str(raw["time_utc"]).replace("Z", "+00:00"))
    except ValueError as exc:
        raise RegistryError(f"{where}: bad time_utc {raw['time_utc']!r}") from exc
    if t.tzinfo is None:
        raise RegistryError(f"{where}: time_utc must carry a time zone")
    t = t.astimezone(timezone.utc)
    iso = raw["country_iso"]
    isos = iso if isinstance(iso, list) else [iso]
    for c in isos:
        if c is not None and not re.fullmatch(r"[A-Z]{2}", str(c)):
            raise RegistryError(f"{where}: bad country_iso {c!r}")
    lat, lon = raw["lat"], raw["lon"]
    if lat is not None:
        lat = _number(lat, f"{where}.lat", -90, 90)
    if lon is not None:
        lon = _number(lon, f"{where}.lon", -180, 180)
    sev = raw["severity"]
    _check_keys(sev, f"{where}.severity", ("scale", "value"), _SEVERITY_KEYS[2:])
    cat = raw["catalogue"]
    _check_keys(cat, f"{where}.catalogue", ("name", "inclusion_rule", "snapshot_sha256"))
    if not isinstance(raw["exhaustive"], bool):
        raise RegistryError(f"{where}.exhaustive must be a bool")
    if raw["exhaustive"] and not (cat["inclusion_rule"] and cat["snapshot_sha256"]):
        raise RegistryError(
            f"{where}: exhaustive needs a stated inclusion_rule and a snapshot hash"
        )
    if (raw["reviewed_by"] is None) != (raw["reviewed_at"] is None):
        raise RegistryError(f"{where}: reviewed_by and reviewed_at go together")
    return Event(
        event_id=raw["event_id"],
        event_type=raw["event_type"],
        subtype=raw["subtype"],
        country_iso=iso,
        time_utc=t,
        time_precision=raw["time_precision"],
        lat=lat,
        lon=lon,
        location_precision_km=raw["location_precision_km"],
        severity=dict(sev),
        cluster_id=raw["cluster_id"],
        catalogue=dict(cat),
        exhaustive=raw["exhaustive"],
        source_url=raw["source_url"],
        archive_url=raw["archive_url"],
        reviewed_by=raw["reviewed_by"],
        reviewed_at=raw["reviewed_at"],
        flags=dict(raw.get("flags") or {}),
    )


def load_events(path: Union[str, Path] = EVENTS_FILE) -> List[Event]:
    """Load and validate `events.jsonl` (one JSON object per line)."""
    events: List[Event] = []
    for n, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            raw = json.loads(line)
        except json.JSONDecodeError as exc:
            raise RegistryError(f"{path}:{n}: invalid JSON") from exc
        events.append(parse_event(raw))
    ids = [e.event_id for e in events]
    dup = sorted({i for i in ids if ids.count(i) > 1})
    if dup:
        raise RegistryError(f"{path}: duplicate event_id {dup[:5]}")
    return events


def aggregate_events(events: Sequence[Event]) -> List[Event]:
    """Events allowed in the aggregate report (exhaustive only); the rest get case files."""
    return [e for e in events if e.in_aggregate]


# ---------------------------------------------------------------- hashes
def registry_hashes(
    charts_path: Union[str, Path] = CHARTS_FILE,
    events_path: Union[str, Path] = EVENTS_FILE,
) -> Dict[str, str]:
    """SHA-256 of the chart and event registries (for case-file provenance)."""
    return {
        "charts_sha256": file_sha256(charts_path),
        "events_sha256": file_sha256(events_path),
    }
