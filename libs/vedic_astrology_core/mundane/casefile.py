"""Case file builder (ADR-006 section 2.1 and 6.4, WP-54).

One event, one candidate chart, everything the catalogue can compute, as one
JSON document (``casefile/1``, schema in ``studies/mundane/casefile.schema.json``).
HTML and PDF are rendered from the JSON by :mod:`.render` and add nothing.

The nine sections of section 2.1 are the top-level keys ``event`` plus
``chart`` (1 header), ``natal`` (2), ``dasha`` (3), ``transits`` (4),
``event_sky`` (5), ``annual`` (6), ``factors`` (7), ``claims`` (8) and
``provenance`` (9). Every section except the header and provenance is an
object with ``computable`` and ``reason``: a section that cannot be computed
says why. The ``sections`` index lists all nine.

Nothing here is a test: no p-value, no aggregate. Unverified and extended
methods carry their true status wherever they appear.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from datetime import date, datetime, time
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence

from ..rules.context import Location, Sky
from ..rules.predicates.timing import houses_ruled
from ..rules.vocabulary import SIGN_NAMES
from ..stats.manifest import file_sha256
from . import dasha as dasha_mod
from . import stability as stab
from .catalogue import Catalogue, CatalogueError, load_catalogue, repo_root
from .charts import DEFAULT_VARGAS, GRAHAS, LAGNA, SETTINGS, FoundingTable, chart_moment, founding_table
from .eventsky import event_sky
from .factors import PLAN_PATH, fired_factors, load_plan
from .registry import (
    CHARTS_FILE,
    EVENTS_FILE,
    Chart,
    Event,
    RegistryError,
    chart_applies,
    chart_grade,
    half_window_minutes,
    registry_hashes,
)
from .transits import transit_table

SCHEMA_ID = "casefile/1"
SCHEMA_PATH = repo_root() / "studies" / "mundane" / "casefile.schema.json"
DASHA_YEAR = "julian"
#: Combustion orbs in degrees from the Sun (direct, retrograde). A convention
#: recorded in the output: from memory of the BPHS tradition, no page cited.
COMBUST_ORBS = {
    "Moon": (12.0, 12.0), "Mars": (17.0, 17.0), "Mercury": (14.0, 12.0),
    "Jupiter": (11.0, 11.0), "Venus": (10.0, 8.0), "Saturn": (15.0, 15.0),
}
COMBUST_NOTE = "orbs from memory of the BPHS tradition (unverified, no page cited)"
SECTIONS = (
    (1, "header", "Header"),
    (2, "natal", "Founding chart"),
    (3, "dasha", "Dasha at the event"),
    (4, "transits", "Transits at the event"),
    (5, "event_sky", "Event-time sky chart"),
    (6, "annual", "Annual context"),
    (7, "factors", "Factors that fire"),
    (8, "claims", "Practitioner explanations"),
    (9, "provenance", "Provenance"),
)
CLAIMS_REASON = "claims registry not built (ADR-005); no row can name this event"
ANNUAL_REASON = "Phase 2 (ADR-006 WP-59): the Mesha sankranti chart of the capital is not built"


# ------------------------------------------------------------------ helpers
def _plain(value: Any) -> Any:
    """Make a value JSON-plain: datetimes to ISO, tuples to lists, sets sorted."""
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, (date, time)):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {str(k): _plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    if isinstance(value, (set, frozenset)):
        return sorted((_plain(v) for v in value), key=str)
    if isinstance(value, float):
        return round(value, 6)
    return value


def _git_commit() -> Optional[str]:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=repo_root(), capture_output=True, text=True, timeout=10
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout.strip() or None if out.returncode == 0 else None


def _section(computable: bool, reason: Optional[str], **content: Any) -> Dict[str, Any]:
    if computable and reason:
        raise ValueError("a computable section has no reason")
    if not computable and not reason:
        raise ValueError("a section that cannot be computed must say why")
    return {"computable": computable, "reason": reason, **content}


def event_title(event: Event) -> str:
    """Plain title built from the record (the registry holds no free-text title)."""
    sev = event.severity or {}
    mag = f" {sev['scale']} {sev['value']}" if sev.get("scale") and sev.get("value") is not None else ""
    return f"{event.event_type.replace('_', ' ').capitalize()}{mag} ({event.event_id})"


# ----------------------------------------------------------------- section 1
def _header(event: Event, chart: Chart) -> Dict[str, Any]:
    ev = {
        "event_id": event.event_id,
        "title": event_title(event),
        "event_type": event.event_type,
        "subtype": event.subtype,
        "country_iso": event.country_iso,
        "time_utc": event.time_utc.isoformat(),
        "time_precision": event.time_precision,
        "lat": event.lat,
        "lon": event.lon,
        "location_precision_km": event.location_precision_km,
        "severity": dict(event.severity),
        "cluster_id": event.cluster_id,
        "catalogue": {"name": event.catalogue.get("name"), "snapshot_sha256": event.catalogue.get("snapshot_sha256")},
        "exhaustive": event.exhaustive,
        "source_url": event.source_url,
        "archive_url": event.archive_url,
        "reviewed_by": event.reviewed_by,
        "reviewed_at": event.reviewed_at,
    }
    src = (chart.time_evidence or {}).get("source") or {}
    ch = {
        "chart_id": chart.chart_id,
        "country_iso": chart.country_iso,
        "event": chart.event,
        "grade": chart_grade(chart),
        "half_window_minutes": half_window_minutes(chart),
        "founding_date": chart.date.isoformat(),
        "founding_time": chart.time.isoformat() if chart.time else None,
        "time_zone": chart.time_zone,
        "place": chart.place,
        "lat": chart.lat,
        "lon": chart.lon,
        "time_evidence_kind": chart.time_evidence.get("kind"),
        "stated_precision_minutes": chart.time_evidence.get("stated_precision_minutes"),
        "source_title": src.get("title"),
        "source_url": src.get("url"),
        "source_archive_url": src.get("archive_url"),
        "checked_by": chart.time_evidence.get("checked_by"),
        "rectified": bool(chart.time_evidence.get("rectified")),
        "valid_from": chart.valid_from.isoformat(),
        "claimed_confidence": chart.claimed_confidence,
    }
    return {"event": ev, "chart": ch}


# ----------------------------------------------------------------- section 2
def _combust(sky: Sky, planet: str) -> Optional[bool]:
    if planet not in COMBUST_ORBS:
        return None
    sep = abs(sky.lon(planet) - sky.lon("Sun")) % 360.0
    sep = min(sep, 360.0 - sep)
    direct, retro = COMBUST_ORBS[planet]
    return sep <= (retro if sky.record(planet).get("retrograde") else direct)


def _point_cells(chart: Chart, has_lagna: bool) -> Callable[[datetime], Dict[Any, Any]]:
    place = Location(chart.lat, chart.lon, "UTC")

    def cells(t: datetime) -> Dict[Any, Any]:
        sky = Sky(t, place, "mean")
        out: Dict[Any, Any] = {}
        points = ([LAGNA] if has_lagna else []) + list(GRAHAS)
        for p in points:
            nk = sky.nakshatra(p)
            out[(p, "nakshatra")] = f"{nk['name']} {nk['pada']}"
            if p != LAGNA:
                out[(p, "retrograde")] = bool(sky.record(p).get("retrograde"))
                c = _combust(sky, p)
                if c is not None:
                    out[(p, "combust")] = c
        return out

    return cells


def _alts(stabilities: Mapping, point: str, varga: str, fields: Sequence[str]) -> List[Dict[str, Any]]:
    out = []
    for f in fields:
        s = stabilities.get((point, varga, f))
        if s is not None and not s.stable:
            out += [{"field": f, "value": _plain(v.value), "share": round(v.share, 4)} for v in s.values]
    return out


def _natal(chart: Chart, vargas: Sequence[str], cat: Catalogue) -> Dict[str, Any]:
    try:
        table: FoundingTable = founding_table(chart, vargas, catalogue=cat)
        cell_stab = stab.founding_table_stability(chart, vargas, catalogue=cat)
    except (CatalogueError, RegistryError) as exc:
        return _section(False, f"{type(exc).__name__}: {exc}", points=[])
    hw = half_window_minutes(chart)
    extra = stab.check_many(
        _point_cells(chart, table.has_lagna), chart_moment(chart), float(hw), stab.founding_grid_minutes(chart)
    )
    rows = []
    for r in table.points:
        pfields = {k: extra[(r.point, k)] for k in ("nakshatra", "retrograde", "combust") if (r.point, k) in extra}
        vg = {}
        for name, p in r.vargas.items():
            fields = [f for f in ("sign", "house", "dignity", "hora_lord") if (r.point, name, f) in cell_stab]
            alts = _alts(cell_stab, r.point, name, fields)
            vg[name] = {
                "sign": p.sign_name, "house": p.house, "dignity": p.dignity, "hora_lord": p.hora_lord,
                "stable": not alts, "alternatives": alts,
            }
        unstable_point = [k for k, s in pfields.items() if not s.stable]
        stated = {k: s.stated_value for k, s in pfields.items()}
        rows.append({
            "point": r.point,
            "longitude": round(r.longitude, 4),
            "degree_in_sign": round(r.longitude % 30.0, 4),
            "nakshatra": stated["nakshatra"].rsplit(" ", 1)[0],
            "pada": int(stated["nakshatra"].rsplit(" ", 1)[1]),
            "retrograde": stated.get("retrograde"),
            "combust": stated.get("combust"),
            "point_stable": not unstable_point,
            "point_alternatives": [
                {"field": k, "value": _plain(v.value), "share": round(v.share, 4)}
                for k in unstable_point for v in pfields[k].values
            ],
            "vargas": vg,
        })
    return _section(
        True, None,
        moment_utc=table.moment_utc.isoformat(),
        time_known=table.time_known,
        has_lagna=table.has_lagna,
        note=None if table.has_lagna else "date-only chart: planets at local noon, no lagna and no houses",
        vargas=list(table.vargas),
        window={"half_window_minutes": hw, "grid_minutes": stab.founding_grid_minutes(chart)},
        combust_convention=COMBUST_NOTE,
        points=rows,
    )


# ----------------------------------------------------------------- section 3
def _lord_state(lord: str, natal: Dict[str, Any]) -> Dict[str, Any]:
    if not natal.get("computable"):
        return {"computable": False, "reason": natal.get("reason")}
    row = next((p for p in natal["points"] if p["point"] == lord), None)
    lagna = next((p for p in natal["points"] if p["point"] == LAGNA), None)
    out: Dict[str, Any] = {"computable": True, "reason": None}
    for v in ("D1", "D9"):
        if row is None or v not in row["vargas"]:
            out[v] = None
            continue
        cell = row["vargas"][v]
        ruled = None
        if lagna is not None and v in lagna["vargas"]:
            ruled = houses_ruled(lord, SIGN_NAMES.index(lagna["vargas"][v]["sign"]))
        out[v] = {
            "sign": cell["sign"], "house": cell["house"], "dignity": cell["dignity"],
            "houses_ruled": ruled, "stable": cell["stable"],
        }
    return out


def _dasha(chart: Chart, event: Event, natal: Dict[str, Any], cat: Catalogue) -> Dict[str, Any]:
    try:
        half = stab.event_half_window(event)
        res = dasha_mod.dasha_at_event(chart, event.time_utc, event_half_window_minutes=half, catalogue=cat)
    except RegistryError as exc:  # includes DashaWindowError (event inside the founding window)
        return _section(False, str(exc), levels=[])
    levels = []
    for lv in res.levels:
        d = lv.to_dict()
        d["lord_state"] = _lord_state(lv.lord, natal) if lv.lord else {"computable": False, "reason": lv.reason}
        levels.append(d)
    unsupported = all(not lv.supported for lv in res.levels)
    return _section(
        True, None,
        method="dasha.vimshottari",
        all_levels_unsupported=unsupported,
        note=dasha_mod.UNSUPPORTED_REASON if unsupported else None,
        first_lord=res.first_lord,
        dasha_year_days=res.dasha_year_days,
        half_window_minutes=res.half_window_minutes,
        event_half_window_minutes=res.event_half_window_minutes,
        levels=levels,
    )


# ----------------------------------------------------------------- section 4
def _transits(event: Event, chart: Chart, cat: Catalogue) -> Dict[str, Any]:
    tt = transit_table(event, chart, catalogue=cat)
    if not tt.get("computable"):
        return _section(False, tt.get("reason") or "not computable", positions=[], readings={"core": {}, "extended": {}})
    core = tt["readings"]["core"]
    lag = {r["graha"]: r for r in core["transit.from_lagna"]["rows"]}
    moon = {r["graha"]: r for r in core["transit.gochara_moon"]["rows"]}
    known = bool(tt.get("natal_time_known"))
    positions = []
    for p in tt["positions"]:
        g = p["graha"]
        positions.append({
            **p,
            "house_from_lagna": lag[g]["house"] if known else None,
            "house_from_lagna_stable": lag[g]["stable"] if known else None,
            "house_from_moon": moon[g]["house"],
            "house_from_moon_stable": moon[g]["stable"],
        })
    return _section(
        True, None,
        note=None if known else "natal time unknown: no house from the lagna",
        event_window_half_minutes=tt["event_window_half_minutes"],
        natal_window_half_minutes=tt["natal_window_half_minutes"],
        positions=positions,
        readings=tt["readings"],
    )


# ----------------------------------------------------------------- section 5
def _event_sky(event: Event, cat: Catalogue) -> Dict[str, Any]:
    if event.lat is None or event.lon is None:
        return _section(False, "the event has no place; the event-time sky chart needs a place and a time to the hour or better")
    if event.time_precision not in ("minute", "hour"):
        return _section(
            False,
            f"time precision is {event.time_precision!r}; the event-time sky chart needs a time to the hour or better",
        )
    sky = event_sky(event, catalogue=cat)
    if not sky.get("computable"):
        return _section(False, sky.get("reason") or "not computable")
    body = {k: v for k, v in sky.items() if k not in ("computable", "reason")}
    return _section(True, None, **body)


# ----------------------------------------------------------------- section 7, 8, 9
def _factors(event: Event, chart: Chart, cat: Catalogue, plan: Dict[str, Any], base_rates) -> Dict[str, Any]:
    res = fired_factors(event, chart, catalogue=cat, plan=plan, base_rates=base_rates)
    if not res["computable"]:
        return _section(False, res["reason"], rows=[], not_evaluated=res["not_evaluated"], plan_id=res["plan_id"],
                        tests_declared=res["tests_declared"])
    return _section(
        True, None,
        plan_id=res["plan_id"],
        tests_declared=res["tests_declared"],
        base_rate_note="share of calendar dates on which the same factor is true for this chart; no event data is used",
        rows=res["rows"],
        not_evaluated=res["not_evaluated"],
    )


def _claims(event: Event, claims: Optional[Sequence[Mapping[str, Any]]]) -> Dict[str, Any]:
    if claims is None:
        return _section(False, CLAIMS_REASON, rows=[])
    rows = [dict(c) for c in claims if event.event_id in (c.get("event_ids") or [])]
    return _section(True, None, rows=rows)


def _provenance(
    cat: Catalogue, commit: Optional[str], charts_path: Path, events_path: Path, plan_path: Path
) -> Dict[str, Any]:
    h = registry_hashes(charts_path, events_path)
    return {
        **h,
        "catalogue_sha256": cat.hash(),
        "plan_sha256": file_sha256(plan_path),
        "ayanamsa": SETTINGS["ayanamsa"],
        "node": SETTINGS["node"],
        "houses": SETTINGS["houses"],
        "dasha_year": DASHA_YEAR,
        "commit": commit,
    }


# --------------------------------------------------------------------- build
def build_casefile(
    event: Event,
    chart: Chart,
    *,
    vargas: Sequence[str] = DEFAULT_VARGAS,
    catalogue: Optional[Catalogue] = None,
    plan_path: Path = PLAN_PATH,
    base_rates: Optional[Mapping[str, Optional[float]]] = None,
    claims: Optional[Sequence[Mapping[str, Any]]] = None,
    commit: Optional[str] = None,
    charts_path: Path = CHARTS_FILE,
    events_path: Path = EVENTS_FILE,
) -> Dict[str, Any]:
    """The case file of one event against one chart, as a JSON-plain dict.

    Raises ``ChartNotApplicable`` for an event before the chart's ``valid_from``
    and ``RegistryError`` for a grade X chart. Every other failure becomes a
    section that is not computable, with the reason.
    """
    if chart_grade(chart) == "X":
        raise RegistryError(f"{chart.chart_id}: grade X (date disputed) is excluded")
    chart_applies(chart, event.time_utc)
    cat = catalogue or load_catalogue()
    plan = load_plan(plan_path)
    head = _header(event, chart)
    natal = _natal(chart, vargas, cat)
    case: Dict[str, Any] = {
        "schema": SCHEMA_ID,
        **head,
        "settings": {**SETTINGS, "dasha_year": DASHA_YEAR},
        "natal": natal,
        "dasha": _dasha(chart, event, natal, cat),
        "transits": _transits(event, chart, cat),
        "event_sky": _event_sky(event, cat),
        "annual": _section(False, ANNUAL_REASON),
        "factors": _factors(event, chart, cat, plan, base_rates),
        "claims": _claims(event, claims),
        "provenance": _provenance(cat, commit if commit is not None else _git_commit(), Path(charts_path), Path(events_path), Path(plan_path)),
    }
    case["sections"] = [
        {
            "number": n, "key": key, "title": title,
            "computable": True if key in ("header", "provenance") else bool(case[key]["computable"]),
            "reason": None if key in ("header", "provenance") else case[key]["reason"],
        }
        for n, key, title in SECTIONS
    ]
    return _plain(case)


def casefile_name(event_id: str, chart_id: str) -> str:
    """File stem ``<event_id>__<chart_id>`` with path-unsafe characters replaced."""
    return re.sub(r"[^A-Za-z0-9._-]", "_", event_id) + "__" + re.sub(r"[^A-Za-z0-9._-]", "_", chart_id)


def dumps(case: Mapping[str, Any]) -> str:
    """Canonical JSON text (stable key order as built, two-space indent, trailing newline)."""
    return json.dumps(case, indent=2, ensure_ascii=False) + "\n"


def write_casefile(case: Mapping[str, Any], out_dir: Path) -> Path:
    """Write ``<event_id>__<chart_id>.json`` into ``out_dir`` and return its path."""
    path = Path(out_dir) / (casefile_name(case["event"]["event_id"], case["chart"]["chart_id"]) + ".json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dumps(case), encoding="utf-8")
    return path


# ---------------------------------------------------------------- validation
class SchemaError(ValueError):
    """A document does not match the case-file schema."""


_TYPES = {
    "object": dict, "array": list, "string": str, "boolean": bool, "null": type(None),
}


def _is_type(value: Any, name: str) -> bool:
    if name == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if name == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    return isinstance(value, _TYPES[name])


def _check(value: Any, schema: Mapping[str, Any], root: Mapping[str, Any], where: str, errors: List[str]) -> None:
    if "$ref" in schema:
        node: Any = root
        for part in schema["$ref"].lstrip("#/").split("/"):
            node = node[part]
        return _check(value, node, root, where, errors)
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{where}: {value!r} not in {schema['enum']}")
    if "const" in schema and value != schema["const"]:
        errors.append(f"{where}: expected {schema['const']!r}")
    if "type" in schema:
        names = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
        if not any(_is_type(value, n) for n in names):
            errors.append(f"{where}: expected {'|'.join(names)}, got {type(value).__name__}")
            return
    if isinstance(value, dict):
        for k in schema.get("required", []):
            if k not in value:
                errors.append(f"{where}: missing key {k!r}")
        props = schema.get("properties", {})
        for k, v in value.items():
            if k in props:
                _check(v, props[k], root, f"{where}.{k}", errors)
            elif schema.get("additionalProperties") is False:
                errors.append(f"{where}: unknown key {k!r}")
            elif isinstance(schema.get("additionalProperties"), dict):
                _check(v, schema["additionalProperties"], root, f"{where}.{k}", errors)
        for cond in schema.get("allOf", []):
            _check(value, cond, root, where, errors)
    if isinstance(value, list) and "items" in schema:
        if len(value) < schema.get("minItems", 0):
            errors.append(f"{where}: fewer than {schema['minItems']} items")
        for i, v in enumerate(value):
            _check(v, schema["items"], root, f"{where}[{i}]", errors)
    if "if" in schema:
        probe: List[str] = []
        _check(value, schema["if"], root, where, probe)
        branch = schema.get("then") if not probe else schema.get("else")
        if branch:
            _check(value, branch, root, where, errors)


def load_schema(path: Path = SCHEMA_PATH) -> Dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def validate_casefile(case: Mapping[str, Any], schema: Optional[Mapping[str, Any]] = None) -> List[str]:
    """Problems of ``case`` against the schema (empty list when valid).

    A small validator for the schema subset used (type, enum, const, required,
    properties, additionalProperties, items, minItems, ``$ref`` into ``$defs``,
    if/then/else); ``jsonschema`` is not a dependency of the repository.
    """
    sch = schema or load_schema()
    errors: List[str] = []
    _check(case, sch, sch, "$", errors)
    return errors


def assert_valid(case: Mapping[str, Any]) -> None:
    errors = validate_casefile(case)
    if errors:
        raise SchemaError("; ".join(errors[:5]))


__all__ = [
    "SCHEMA_ID", "SCHEMA_PATH", "SECTIONS", "SchemaError", "assert_valid", "build_casefile",
    "casefile_name", "dumps", "event_title", "load_schema", "validate_casefile", "write_casefile",
]
