"""Daily sidereal planetary positions, one file per year.

The dataset replaces the archived ``Astrology_Planetary_Data`` repository. It
is produced by the same engine as every study in this repository
(:class:`~vedic_astrology_core.astrology.ephemeris.EphemerisEngine`): apparent
geocentric positions from Swiss Ephemeris with ``FLG_SIDEREAL`` (Lahiri by
default), mean lunar node, Ketu = Rahu + 180 degrees, whole-sign signs.

Layout of ``out_dir``::

    <year>.parquet | <year>.csv       one row per body per sample instant
    <year>.manifest.json              engine details and sha256 of that file

``house_lordships`` from the old repository is not reproduced: it depended on
an unsourced ascendant.
"""

import hashlib
import json
import subprocess
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Union
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import numpy as np
import pandas as pd
import swisseph as swe

from ..astrology.ayanamsa import SIGN_NAMES_LIST, set_sidereal_mode
from ..astrology.ephemeris import SWE_BODIES, EphemerisEngine
from ..config.constants import NAKSHATRAS, Planet

GENERATOR_VERSION = "1.0.0"
NINE_GRAHAS = [
    "SUN",
    "MOON",
    "MARS",
    "MERCURY",
    "JUPITER",
    "VENUS",
    "SATURN",
    "RAHU",
    "KETU",
]
COLUMNS = [
    "date",
    "jd",
    "body",
    "longitude",
    "latitude",
    "speed",
    "retrograde",
    "sign",
    "sign_name",
    "degree_in_sign",
    "nakshatra",
    "nakshatra_name",
    "pada",
    "nakshatra_lord",
]
FORMATS = ("parquet", "csv")
NAKSHATRA_SPAN = 360.0 / 27.0
PADA_SPAN = NAKSHATRA_SPAN / 4.0
_FLAGS = swe.FLG_SWIEPH | swe.FLG_SPEED | swe.FLG_SIDEREAL
_MANIFEST_SUFFIX = ".manifest.json"

PathLike = Union[str, Path]


def _git_commit() -> Optional[str]:
    """Return the HEAD commit of the repository, or None outside git."""
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=Path(__file__).resolve().parent,
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout.strip() or None


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _parse_clock(sample_time: str) -> time:
    try:
        return time.fromisoformat(sample_time)
    except ValueError:
        raise ValueError(f"sample_time must be HH:MM, got {sample_time!r}") from None


def _instants(year: int, step: pd.Timedelta, clock: time, zone: ZoneInfo):
    """UTC datetimes of one local year, whole-day steps on the local clock."""
    whole_days = step % pd.Timedelta(days=1) == pd.Timedelta(0)
    if whole_days:
        day, delta = date(year, 1, 1), timedelta(days=step.days)
        while day.year == year:
            local = datetime.combine(day, clock, tzinfo=zone)
            yield local.astimezone(timezone.utc)
            day += delta
        return
    current = datetime.combine(date(year, 1, 1), clock, tzinfo=zone)
    current = current.astimezone(timezone.utc)
    delta = step.to_pytimedelta()
    while current.astimezone(zone).year == year:
        yield current
        current += delta


def _julian_days(instants: Sequence[datetime]) -> np.ndarray:
    return np.array(
        [
            swe.julday(
                t.year,
                t.month,
                t.day,
                t.hour + t.minute / 60.0 + t.second / 3600.0,
                swe.GREG_CAL,
            )
            for t in instants
        ]
    )


def _year_frame(
    year: int,
    step: pd.Timedelta,
    clock: time,
    zone: ZoneInfo,
    bodies: Sequence[str],
    engine: EphemerisEngine,
) -> pd.DataFrame:
    instants = list(_instants(year, step, clock, zone))
    jds = _julian_days(instants)
    iso = np.array([t.isoformat() for t in instants])
    set_sidereal_mode(engine.ayanamsa_system)
    node_body = engine.node_body
    frames = []
    for name in bodies:
        planet = Planet[name]
        body = node_body if planet in (Planet.RAHU, Planet.KETU) else SWE_BODIES[planet]
        raw = np.array([swe.calc_ut(float(jd), body, _FLAGS)[0] for jd in jds])
        lon, lat, speed = raw[:, 0] % 360.0, raw[:, 1], raw[:, 3]
        if planet == Planet.KETU:
            lon, lat = (lon + 180.0) % 360.0, -lat
        frames.append(_body_frame(planet, iso, jds, lon, lat, speed))
    out = pd.concat(frames, ignore_index=True)
    out["_order"] = np.tile(np.arange(len(jds)), len(frames))
    out["_body"] = out["body"].map({n: i for i, n in enumerate(bodies)})
    out = out.sort_values(["_order", "_body"], kind="stable")
    return out[COLUMNS].reset_index(drop=True)


def _body_frame(planet, iso, jds, lon, lat, speed) -> pd.DataFrame:
    sign = (lon // 30).astype(int) % 12
    nak = (lon // NAKSHATRA_SPAN).astype(int) % 27
    in_nak = lon - nak * NAKSHATRA_SPAN
    pada = np.minimum((in_nak // PADA_SPAN).astype(int), 3) + 1
    return pd.DataFrame(
        {
            "date": iso,
            "jd": jds,
            "body": planet.name,
            "longitude": lon,
            "latitude": lat,
            "speed": speed,
            "retrograde": speed < 0,
            "sign": sign,
            "sign_name": [SIGN_NAMES_LIST[i] for i in sign],
            "degree_in_sign": lon - sign * 30.0,
            "nakshatra": nak + 1,
            "nakshatra_name": [NAKSHATRAS[i]["name"] for i in nak],
            "pada": pada,
            "nakshatra_lord": [NAKSHATRAS[i]["lord"].name for i in nak],
        }
    )


def _write(frame: pd.DataFrame, path: Path, fmt: str) -> None:
    if fmt == "csv":
        frame.to_csv(path, index=False, lineterminator="\n")
        return
    try:
        import pyarrow  # noqa: F401
    except ImportError as exc:
        raise ImportError(
            "Parquet output needs pyarrow: pip install 'vedic-astrology-core[data]'"
        ) from exc
    frame.to_parquet(path, index=False, engine="pyarrow", compression="zstd")


def generate(
    start_year: int,
    end_year: int,
    step: str = "1D",
    sample_time: str = "12:00",
    tz: str = "UTC",
    bodies: Iterable[str] = NINE_GRAHAS,
    node_model: str = "mean",
    ayanamsa: str = "lahiri",
    out_dir: PathLike = "data/datasets/planetary",
    fmt: str = "parquet",
) -> List[Dict]:
    """Write one file and one manifest per year; return the manifests.

    Args:
        start_year, end_year: Inclusive range of (local) calendar years.
        step: pandas Timedelta string ("1D", "7D", "6h"). Whole-day steps keep
            the local ``sample_time`` across daylight-saving changes.
        sample_time: Local clock time "HH:MM" of each daily sample.
        tz: IANA zone of ``sample_time``; the ``date`` column is always UTC.
        bodies: Subset of :data:`NINE_GRAHAS`.
        node_model: "mean" or "true" lunar node (Ketu = Rahu + 180).
        ayanamsa: Sidereal system name (default "lahiri").
        out_dir: Output directory, created if missing.
        fmt: "parquet" or "csv".

    Raises:
        ValueError: On a bad option, an unknown body or a reversed range.
    """
    if fmt not in FORMATS:
        raise ValueError(f"fmt must be one of {FORMATS}, got {fmt!r}")
    if end_year < start_year:
        raise ValueError(f"end_year {end_year} is before start_year {start_year}")
    bodies = [str(b).upper() for b in bodies]
    unknown = [b for b in bodies if b not in NINE_GRAHAS]
    if unknown:
        raise ValueError(f"Unknown bodies {unknown}; choose from {NINE_GRAHAS}")
    try:
        zone = ZoneInfo(tz)
    except (ZoneInfoNotFoundError, ValueError, OSError):
        raise ValueError(f"Unknown time zone {tz!r}") from None
    step_delta = pd.Timedelta(step)
    if step_delta <= pd.Timedelta(0):
        raise ValueError(f"step must be positive, got {step!r}")
    clock = _parse_clock(sample_time)
    engine = EphemerisEngine(ayanamsa_system=ayanamsa, node_model=node_model)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    commit = _git_commit()
    manifests = []
    for year in range(start_year, end_year + 1):
        frame = _year_frame(year, step_delta, clock, zone, bodies, engine)
        path = out / f"{year}.{fmt}"
        _write(frame, path, fmt)
        manifest = {
            "file": path.name,
            "year": year,
            "rows": int(len(frame)),
            "sha256": _sha256(path),
            "columns": COLUMNS,
            "bodies": bodies,
            "step": step,
            "sample_time": sample_time,
            "tz": tz,
            "ayanamsa": engine.ayanamsa_system.value,
            "node_model": engine.node_model,
            "ketu": "rahu + 180 degrees",
            "zodiac": "sidereal, whole-sign",
            "ephemeris_model": engine.ephemeris_model,
            "swisseph_version": swe.version,
            "generator_version": GENERATOR_VERSION,
            "git_commit": commit,
        }
        (out / f"{year}{_MANIFEST_SUFFIX}").write_text(
            json.dumps(manifest, indent=2) + "\n"
        )
        manifests.append(manifest)
    return manifests


def verify(out_dir: PathLike) -> List[str]:
    """Return the data files whose sha256 differs from their manifest.

    A manifest whose data file is missing is reported too.
    """
    out = Path(out_dir)
    manifests = sorted(out.glob(f"*{_MANIFEST_SUFFIX}"))
    if not manifests:
        raise FileNotFoundError(f"No manifests in {out}")
    bad = []
    for mpath in manifests:
        manifest = json.loads(mpath.read_text())
        data = out / manifest["file"]
        if not data.exists() or _sha256(data) != manifest["sha256"]:
            bad.append(manifest["file"])
    return bad


def _read(path: Path) -> pd.DataFrame:
    return pd.read_parquet(path) if path.suffix == ".parquet" else pd.read_csv(path)


def combined(
    years: Iterable[int],
    bodies: Optional[Iterable[str]] = None,
    data_dir: PathLike = "data/datasets/planetary",
) -> pd.DataFrame:
    """Concatenate the yearly files into one frame, optionally per body.

    Raises:
        FileNotFoundError: Naming the first year with no file.
    """
    base = Path(data_dir)
    wanted = None if bodies is None else [str(b).upper() for b in bodies]
    parts = []
    for year in years:
        path = next(
            (base / f"{year}.{e}" for e in FORMATS if (base / f"{year}.{e}").exists()),
            None,
        )
        if path is None:
            raise FileNotFoundError(f"No dataset file for {year} in {base}")
        frame = _read(path)
        if wanted is not None:
            frame = frame[frame["body"].isin(wanted)]
        parts.append(frame)
    return pd.concat(parts, ignore_index=True)
