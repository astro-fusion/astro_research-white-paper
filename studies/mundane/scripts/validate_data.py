"""Validate ``countries.yaml`` and ``events.jsonl`` against their schemas.

Exit code 0 when both files are valid, 1 otherwise. Problems are printed one
per line as ``file:location: message``.
"""

import json
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any, Dict, List
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))  # repo root
from studies._paths import study_data_dir  # noqa: E402

DATA_DIR: Path = study_data_dir("mundane")
COUNTRIES_FILE: Path = DATA_DIR / "countries.yaml"
EVENTS_FILE: Path = DATA_DIR / "events.jsonl"
SNAPSHOT_DIR: Path = DATA_DIR / "snapshots"

# ISO 3166-1 alpha-2 codes.
ISO_CODES = frozenset(
    """AD AE AF AG AI AL AM AO AQ AR AS AT AU AW AX AZ BA BB BD BE BF BG BH BI BJ
    BL BM BN BO BQ BR BS BT BV BW BY BZ CA CC CD CF CG CH CI CK CL CM CN CO CR CU
    CV CW CX CY CZ DE DJ DK DM DO DZ EC EE EG EH ER ES ET FI FJ FK FM FO FR GA GB
    GD GE GF GG GH GI GL GM GN GP GQ GR GS GT GU GW GY HK HM HN HR HT HU ID IE IL
    IM IN IO IQ IR IS IT JE JM JO JP KE KG KH KI KM KN KP KR KW KY KZ LA LB LC LI
    LK LR LS LT LU LV LY MA MC MD ME MF MG MH MK ML MM MN MO MP MQ MR MS MT MU MV
    MW MX MY MZ NA NC NE NF NG NI NL NO NP NR NU NZ OM PA PE PF PG PH PK PL PM PN
    PR PS PT PW PY QA RE RO RS RU RW SA SB SC SD SE SG SH SI SJ SK SL SM SN SO SR
    SS ST SV SX SY SZ TC TD TF TG TH TJ TK TL TM TN TO TR TT TV TW TZ UA UG UM US
    UY UZ VA VC VE VG VI VN VU WF WS YE YT ZA ZM ZW""".split()
)

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_TIME_RE = re.compile(r"^\d{2}:\d{2}(:\d{2})?$")


def _bad_date(value: Any) -> bool:
    if not isinstance(value, str) or not _DATE_RE.match(value):
        return True
    try:
        date.fromisoformat(value)
    except ValueError:
        return True
    return False


def _check_coord(obj: Dict[str, Any], lat_key: str, lon_key: str) -> List[str]:
    out = []
    lat, lon = obj.get(lat_key), obj.get(lon_key)
    if (lat is None) != (lon is None):
        out.append(f"{lat_key}/{lon_key}: only one of the pair is set")
    if lat is not None and not (isinstance(lat, (int, float)) and -90 <= lat <= 90):
        out.append(f"{lat_key}: {lat!r} outside -90..90")
    if lon is not None and not (isinstance(lon, (int, float)) and -180 <= lon <= 180):
        out.append(f"{lon_key}: {lon!r} outside -180..180")
    return out


def validate_countries(path: Path = COUNTRIES_FILE) -> List[str]:
    """Return a list of problems in the countries YAML (empty when valid)."""
    problems: List[str] = []
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    rows = (data or {}).get("countries")
    if not isinstance(rows, list) or not rows:
        return [f"{path.name}: top-level 'countries' list is missing or empty"]
    seen = set()
    for i, c in enumerate(rows):
        where = f"{path.name}:countries[{i}]"
        iso = c.get("iso")
        if iso not in ISO_CODES:
            problems.append(f"{where}: invalid ISO code {iso!r}")
        if iso in seen:
            problems.append(f"{where}: duplicate ISO code {iso!r}")
        seen.add(iso)
        for key in ("slug", "name", "timezone"):
            if not c.get(key):
                problems.append(f"{where}: missing {key}")
        try:
            ZoneInfo(c.get("timezone") or "")
        except (ZoneInfoNotFoundError, ValueError, OSError):
            problems.append(f"{where}: unknown timezone {c.get('timezone')!r}")
        problems += [
            f"{where}: {p}" for p in _check_coord(c, "capital_lat", "capital_lon")
        ]
        if c.get("capital_lat") is None:
            problems.append(f"{where}: capital coordinates are required")
        f = c.get("founding") or {}
        if _bad_date(f.get("date")):
            problems.append(f"{where}: founding.date {f.get('date')!r} is not a date")
        t = f.get("time")
        if t is not None and not _TIME_RE.match(str(t)):
            problems.append(f"{where}: founding.time {t!r} is not HH:MM[:SS]")
        known = f.get("time_known")
        if not isinstance(known, bool):
            problems.append(f"{where}: founding.time_known must be true or false")
        elif known and t is None:
            problems.append(f"{where}: time_known is true but time is null")
        elif not known and t is not None:
            problems.append(f"{where}: time is set but time_known is false")
        if not f.get("rationale"):
            problems.append(f"{where}: founding.rationale is missing")
        cands = c.get("candidate_charts")
        if not isinstance(cands, list):
            problems.append(f"{where}: candidate_charts must be a list")
        else:
            for j, cc in enumerate(cands):
                if _bad_date(cc.get("date")) or not cc.get("source"):
                    problems.append(
                        f"{where}.candidate_charts[{j}]: needs a date and a source"
                    )
    return problems


def validate_events(
    path: Path = EVENTS_FILE, countries_path: Path = COUNTRIES_FILE
) -> List[str]:
    """Return a list of problems in the events JSONL (empty when valid)."""
    problems: List[str] = []
    seen = set()
    for n, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        where = f"{path.name}:{n}"
        try:
            e = json.loads(line)
        except json.JSONDecodeError as exc:
            problems.append(f"{where}: invalid JSON ({exc.msg})")
            continue
        for key in ("id", "title", "event_type"):
            if not e.get(key):
                problems.append(f"{where}: missing {key}")
        if _bad_date(e.get("date")):
            problems.append(f"{where}: date {e.get('date')!r} is not a date")
        elif int(e["date"][:4]) < 1:
            problems.append(f"{where}: year before 0001")
        iso = e.get("country_iso")
        if iso is not None and iso not in ISO_CODES:
            problems.append(f"{where}: invalid ISO code {iso!r}")
        problems += [f"{where}: {p}" for p in _check_coord(e, "lat", "lon")]
        if not isinstance(e.get("event_type_reviewed"), bool):
            problems.append(f"{where}: event_type_reviewed must be a boolean")
        if "description" in e:
            problems.append(f"{where}: description must not be present (licence)")
        meta = e.get("metadata")
        if not isinstance(meta, dict) or "qid" not in meta:
            problems.append(f"{where}: metadata.qid is required (may be null)")
        key = (e.get("id"), iso)
        if key in seen:
            problems.append(f"{where}: duplicate (id, country_iso) {key}")
        seen.add(key)
    return problems


def main() -> int:
    """Validate both data files; return a process exit code."""
    problems = validate_countries() + validate_events()
    for p in problems:
        print(p)
    print(f"validate_data: {len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
