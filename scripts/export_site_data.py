"""Export the small, derived, redistributable data the website explorers read.

Writes ``site/data/*.json``. Every file is ``{"_meta": {...}, ...}`` where
``_meta`` holds the SHA-256 of each input, the SHA-256 of the exported rows,
the commit, the seed, the generation time, the source and its licence.

Nothing here republishes a price or a return from Yahoo Finance: the market
files carry indicator flags, an extreme-move flag, the sign of the daily move
and forward-return *quintile classes* only. The price panel uses the World
Bank Commodity Price Data (the "Pink Sheet", CC BY 4.0), fetched once and
snapshotted with its hash under ``data/snapshots/``.

Usage::

    PYTHONPATH=libs:src:. python scripts/export_site_data.py --seed 42
    python scripts/export_site_data.py --only rules,markets --offline
"""

import argparse
import hashlib
import importlib.util
import json
import math
import re
import subprocess
import sys
import urllib.request
import zipfile
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from xml.etree import ElementTree as ET

import numpy as np
import pandas as pd
import pytz
import yaml

REPO = Path(__file__).resolve().parents[1]
for _p in (REPO, REPO / "libs", REPO / "src"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from studies._paths import SNAPSHOT_ROOT  # noqa: E402
from vedic_astrology_core.astrology.ephemeris import EphemerisEngine  # noqa: E402
from vedic_astrology_core.config.constants import Planet  # noqa: E402

OUT = REPO / "site" / "data"
GRAHAS = [
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
PINK_SHEET_PAGE = "https://www.worldbank.org/en/research/commodity-markets"
PINK_SHEET_URL = (
    "https://thedocs.worldbank.org/en/doc/"
    "74e8be41ceb20fa0da750cda2f6b9e4e-0050012026/related/"
    "CMO-Historical-Data-Monthly.xlsx"
)
ATLAS_URL = "https://cdn.jsdelivr.net/npm/world-atlas@2.0.2/countries-110m.json"
LICENCES = {
    "yahoo_derived": (
        "Derived classes and flags only (no prices or returns); "
        "the underlying Yahoo Finance series is not redistributed"
    ),
    "worldbank": "CC BY 4.0, World Bank Commodity Price Data (The Pink Sheet)",
    "usgs": "Public domain (US Government), USGS ComCat",
    "engine": "Computed with the Swiss Ephemeris (pyswisseph); AGPL / Swiss "
    "Ephemeris licence",
    "mundane": "CC BY 4.0 (AstroFusion mundane dataset export 2026-11-08)",
    "repo": "Repository licence (rules and results of this project)",
}


# ------------------------------------------------------------------ helpers
def sha256_file(path: Path) -> str:
    """Return the SHA-256 hex digest of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def git_commit() -> str:
    """Return the current commit hash, or 'unknown' outside git."""
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=REPO,
            capture_output=True,
            text=True,
            check=True,
        )
        return out.stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def rel(path: Path) -> str:
    """Return ``path`` relative to the repository root when inside it."""
    path = Path(path).resolve()
    return str(path.relative_to(REPO)) if path.is_relative_to(REPO) else str(path)


def clean(value: Any) -> Any:
    """JSON-safe: NaN and inf become None, numpy scalars become Python."""
    if isinstance(value, dict):
        return {str(k): clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean(v) for v in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        f = float(value)
        return None if math.isnan(f) or math.isinf(f) else round(f, 6)
    if isinstance(value, np.bool_):
        return bool(value)
    return value


class Writer:
    """Writes one JSON file per dataset with a ``_meta`` block."""

    def __init__(self, out: Path, seed: int):
        """Prepare the output folder and the shared provenance fields."""
        self.out = out
        self.seed = seed
        self.commit = git_commit()
        self.now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        self.written: List[Path] = []
        out.mkdir(parents=True, exist_ok=True)

    def write(
        self,
        name: str,
        payload: Dict[str, Any],
        inputs: Dict[str, Any],
        source: str,
        licence: str,
        note: str = "",
    ) -> Path:
        """Write ``name`` with its ``_meta`` block and return its path."""
        payload = clean(payload)
        body = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        meta = {
            "file": name,
            "data_sha256": hashlib.sha256(body.encode()).hexdigest(),
            "inputs": inputs,
            "commit": self.commit,
            "seed": self.seed,
            "generated_at": self.now,
            "source": source,
            "licence": licence,
            "script": "scripts/export_site_data.py",
        }
        if note:
            meta["note"] = note
        path = self.out / name
        text = json.dumps({"_meta": meta, **payload}, separators=(",", ":"))
        path.write_text(text + "\n", encoding="utf-8")
        self.written.append(path)
        print(f"  {name}: {path.stat().st_size / 1024:.1f} KiB")
        return path


def load_module(name: str, path: Path):
    """Import a study script by file path under a unique module name."""
    folder = str(path.parent)
    if folder not in sys.path:
        sys.path.insert(0, folder)
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def fetch_snapshot(url: str, stem: str, suffix: str, offline: bool) -> Path:
    """Return the newest snapshot ``stem_*.suffix``; fetch one if missing."""
    SNAPSHOT_ROOT.mkdir(parents=True, exist_ok=True)
    found = sorted(
        p
        for p in SNAPSHOT_ROOT.glob(f"{stem}_*{suffix}")
        if not p.name.endswith(".manifest.json")
    )
    if found:
        return found[-1]
    if offline:
        raise SystemExit(
            f"no {stem} snapshot under {rel(SNAPSHOT_ROOT)}; "
            "run once without --offline"
        )
    req = urllib.request.Request(url, headers={"User-Agent": "astro-research"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = resp.read()
    digest = hashlib.sha256(data).hexdigest()
    path = SNAPSHOT_ROOT / f"{stem}_{digest[:12]}{suffix}"
    path.write_bytes(data)
    manifest = {
        "url": url,
        "sha256": digest,
        "bytes": len(data),
        "fetched_utc": datetime.now(timezone.utc).isoformat(),
    }
    path.with_name(path.name + ".manifest.json").write_text(
        json.dumps(manifest, indent=1)
    )
    return path


def hypothesis(study: str) -> Dict[str, Any]:
    """Return a study's parsed pre-registration."""
    return yaml.safe_load(
        (REPO / "studies" / study / "hypothesis.yaml").read_text(encoding="utf-8")
    )


def results(study: str) -> Dict[str, Any]:
    """Return a study's parsed ``artifacts/results.json``."""
    return json.loads(
        (REPO / "studies" / study / "artifacts" / "results.json").read_text(
            encoding="utf-8"
        )
    )


# --------------------------------------------------------- market defs
SIGN_WORD = {
    "retrograde": "is retrograde (longitude decreasing)",
    "combust": "is combust (within its combustion orb of the Sun)",
}


def market_definitions(study: str) -> List[Dict[str, str]]:
    """Return a plain-word definition of each registered market indicator."""
    out = []
    for spec in hypothesis(study)["indicators"]:
        kind = spec["kind"]
        body = str(spec.get("body", "")).title()
        if kind in SIGN_WORD:
            text = f"{body} {SIGN_WORD[kind]}"
        elif kind == "in_sign":
            text = f"{body} in sidereal {', '.join(spec['signs'])} (Lahiri)"
        elif kind == "tithi":
            names = {15: "Purnima (full Moon)", 30: "Amavasya (new Moon)"}
            text = "Tithi " + ", ".join(names.get(t, str(t)) for t in spec["tithis"])
        else:
            text = f"Registry rule {spec['rule']} holds"
        label = spec["id"].replace("_", " ").capitalize()
        out.append(
            {
                "id": spec["id"],
                "label": label,
                "definition": text + "; state on the previous trading bar",
            }
        )
    return out


# ------------------------------------------------------------ markets
def export_markets(w: Writer) -> None:
    """Write the gold and silver daily flag and class files."""
    for study, metal in (("gold_market", "gold"), ("silver_market", "silver")):
        frame_path = REPO / "studies" / study / "artifacts" / "overlay_frame.csv"
        if not frame_path.exists():
            raise SystemExit(
                f"{rel(frame_path)} missing: run the {study} "
                "pipeline first (it is not committed)"
            )
        df = pd.read_csv(frame_path, parse_dates=["date"])
        hyp = hypothesis(study)
        defs = market_definitions(study)
        ids = [d["id"] for d in defs]
        r = df["log_return"]
        window = int(hyp["tests"]["extreme_window_bars"])
        q = float(hyp["tests"]["extreme_quantile"])
        thresh = r.abs().rolling(window).quantile(q).shift(1)
        extreme = (r.abs() > thresh).astype(int).where(thresh.notna(), 0)
        cols: Dict[str, Any] = {
            "date": df["date"].dt.strftime("%Y-%m-%d").tolist(),
            "sign": np.sign(r.fillna(0)).astype(int).tolist(),
            "extreme": extreme.astype(int).tolist(),
        }
        for h in (5, 21, 63):
            fwd = df[f"fwd_{h}"]
            cls = pd.qcut(fwd, 5, labels=False) + 1
            cols[f"fwd{h}_q"] = [None if pd.isna(v) else int(v) for v in cls]
        for i in ids:
            cols[i] = df[i].fillna(0).astype(int).tolist()
        res = results(study)
        w.write(
            f"market_{metal}.json",
            {
                "metal": metal,
                "indicators": defs,
                "columns": cols,
                "fields": {
                    "sign": "sign of the day's move: 1 up, -1 down, 0 flat",
                    "extreme": (
                        f"1 if the absolute move exceeds the past-only "
                        f"{int(q * 100)}th percentile of the previous "
                        f"{window} bars"
                    ),
                    "fwdH_q": (
                        "forward H-bar move as a quintile class over the "
                        "whole sample: 1 lowest fifth, 5 highest"
                    ),
                },
            },
            inputs={
                "overlay_frame": {
                    "path": rel(frame_path),
                    "underlying_sha256": res["data"]["sha256"],
                    "series": res["data"]["label"],
                }
            },
            source=res["data"]["label"],
            licence=LICENCES["yahoo_derived"],
        )


# --------------------------------------------------------- pink sheet
_NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def read_xlsx_sheet(path: Path, sheet_name: str) -> List[List[Any]]:
    """Minimal XLSX reader (stdlib only): return rows of cell strings."""
    z = zipfile.ZipFile(path)
    rid = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
    wb = ET.fromstring(z.read("xl/workbook.xml"))
    rels = {
        r.get("Id"): r.get("Target")
        for r in ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
    }
    target = None
    for s in wb.find("m:sheets", _NS):
        if s.get("name") == sheet_name:
            target = rels[s.get(rid)]
    if target is None:
        raise ValueError(f"sheet {sheet_name!r} not in {path.name}")
    shared = [
        "".join(t.text or "" for t in si.iter(f"{{{_NS['m']}}}t"))
        for si in ET.fromstring(z.read("xl/sharedStrings.xml"))
    ]
    sheet = ET.fromstring(z.read("xl/" + target.lstrip("/").replace("xl/", "")))
    rows = []
    for row in sheet.find("m:sheetData", _NS):
        cells = {}
        for c in row:
            v = c.find("m:v", _NS)
            if v is None:
                continue
            col = re.match(r"[A-Z]+", c.get("r")).group(0)
            cells[col] = shared[int(v.text)] if c.get("t") == "s" else v.text
        rows.append(cells)
    return rows


def export_pink_sheet(w: Writer, offline: bool) -> None:
    """Write the World Bank monthly gold and silver series."""
    path = fetch_snapshot(PINK_SHEET_URL, "worldbank_pinksheet", ".xlsx", offline)
    rows = read_xlsx_sheet(path, "Monthly Prices")
    header = next(r for r in rows if "Gold" in r.values())
    col = {v.strip(): k for k, v in header.items()}
    updated = next(
        (v for r in rows[:6] for v in r.values() if str(v).startswith("Updated")), ""
    )
    out = {"month": [], "gold": [], "silver": []}
    for r in rows:
        m = re.fullmatch(r"(\d{4})M(\d{2})", str(r.get("A", "")))
        if not m:
            continue
        vals = []
        for name in ("Gold", "Silver"):
            try:
                vals.append(float(r.get(col[name], "")))
            except ValueError:
                vals.append(None)
        out["month"].append(f"{m.group(1)}-{m.group(2)}")
        out["gold"].append(vals[0])
        out["silver"].append(vals[1])
    w.write(
        "pinksheet_monthly.json",
        {
            "columns": out,
            "units": "nominal USD per troy ounce, monthly average",
            "updated": updated,
        },
        inputs={
            "pink_sheet": {
                "path": rel(path),
                "sha256": sha256_file(path),
                "url": PINK_SHEET_URL,
                "landing_page": PINK_SHEET_PAGE,
            }
        },
        source="World Bank Commodity Price Data (The Pink Sheet), monthly",
        licence=LICENCES["worldbank"],
        note="Cite: World Bank, Commodity Price Data (The Pink Sheet).",
    )


# ---------------------------------------------------------- earthquake
def intervals(mask: np.ndarray, grid: pd.DatetimeIndex) -> List[List[str]]:
    """Return runs of True in ``mask`` as [start, end) ISO strings on ``grid``."""
    m = np.asarray(mask, dtype=bool)
    edges = np.flatnonzero(np.diff(np.r_[0, m.astype(int), 0]))
    step = grid[1] - grid[0]
    out = []
    for a, b in zip(edges[::2], edges[1::2]):
        end = grid[b - 1] + step
        out.append([grid[a].strftime("%Y-%m-%dT%H:%M"), end.strftime("%Y-%m-%dT%H:%M")])
    return out


def export_earthquake(w: Writer) -> None:
    """Write the declustered catalogue and indicator windows."""
    here = REPO / "studies" / "earthquake" / "scripts"
    pipe = load_module("eq_pipeline", here / "pipeline.py")
    hyp = pipe.fc.load_hypothesis()
    snap = pipe.latest_snapshot(hyp)
    if snap is None:
        raise SystemExit(
            "no USGS snapshot for this pre-registration: run "
            "studies/earthquake/scripts/pipeline.py first"
        )
    cat, info = pipe.load_catalogue(snap)
    expected = results("earthquake")["catalogue"]["sha256"]
    if info["sha256"] != expected:
        print(
            f"  warning: catalogue {info['sha256'][:12]} differs from the one "
            f"in results.json ({expected[:12]})"
        )
    cat = cat[
        (cat["time"] >= pd.Timestamp(hyp["catalogue"]["start"]))
        & (cat["time"] < pd.Timestamp(hyp["catalogue"]["end"]))
    ]
    cat = cat.reset_index(drop=True)
    gk = pipe.decluster.gardner_knopoff(cat).to_numpy()
    nn, _ = pipe.decluster.nearest_neighbour(cat)
    engine = EphemerisEngine(node_model=hyp["ephemeris"]["node_model"])
    grid = pipe.ind.time_grid(
        hyp["catalogue"]["start"],
        hyp["catalogue"]["end"],
        hyp["time_grid"]["step_hours"],
    )
    eph = pipe.ind.ephemeris_frame(grid, engine)
    frame = pipe.ind.build_indicators(hyp, eph)
    bins = pipe.ind.event_bins(cat["time"], grid)
    ids = [s["id"] for s in hyp["indicators"]]
    events = {
        "time": cat["time"].dt.strftime("%Y-%m-%dT%H:%M").tolist(),
        "lat": cat["latitude"].round(3).tolist(),
        "lon": cat["longitude"].round(3).tolist(),
        "mw": cat["mw"].round(2).tolist(),
        "gk": gk.astype(int).tolist(),
        "nn": nn.to_numpy().astype(int).tolist(),
    }
    for i in ids:
        events[i] = frame[i].to_numpy()[bins].astype(int).tolist()
    windows = {
        i: intervals(frame[i].to_numpy(), grid)
        for i in ids
        if not i.startswith("moon_mandala")
    }
    defs = [
        {
            "id": s["id"],
            "label": s["label"],
            "definition": s.get("definition")
            or (
                f"within {s['window_days']} days of a {s['planet'].title()} " "station"
                if "planet" in s
                else "Moon in one of: " + ", ".join(s.get("nakshatras", []))
            ),
            "direction": s["direction"],
        }
        for s in hyp["indicators"]
    ]
    w.write(
        "earthquake.json",
        {
            "events": events,
            "indicators": defs,
            "windows": windows,
            "catalogues": {
                "raw": "Undeclustered",
                "gk": "Gardner-Knopoff",
                "nn": "Nearest-neighbour (Zaliapin)",
            },
            "threshold_mw": info["completeness"]["threshold"],
            "note": (
                "Moon-mandala windows change about daily and are not "
                "exported as intervals; each event carries its state."
            ),
        },
        inputs={
            "usgs_snapshot": {"path": info["snapshot"], "sha256": info["sha256"]},
            "hypothesis": {
                "path": "studies/earthquake/hypothesis.yaml",
                "sha256": sha256_file(pipe.fc.HYPOTHESIS),
            },
        },
        source="USGS ComCat via the FDSN event service; Himalayan-arc polygon",
        licence=LICENCES["usgs"] + "; indicator windows: " + LICENCES["engine"],
    )


# ------------------------------------------------------------ ephemeris
def export_ephemeris(w: Writer) -> None:
    """Write monthly sidereal longitudes of the nine grahas."""
    engine = EphemerisEngine(node_model="mean")
    months = pd.date_range("1976-01-01", "2026-12-01", freq="MS", tz="UTC")
    cols: Dict[str, List[Any]] = {"month": [m.strftime("%Y-%m") for m in months]}
    for g in GRAHAS:
        cols[g] = []
        cols[g + "_r"] = []
    for m in months:
        pos = engine.get_all_planet_positions(
            engine.datetime_to_julian_day(m.to_pydatetime())
        )
        for g in GRAHAS:
            rec = pos[Planet[g]]
            cols[g].append(round(rec["longitude"], 3))
            cols[g + "_r"].append(int(bool(rec["retrograde"])))
    w.write(
        "ephemeris_monthly.json",
        {
            "columns": cols,
            "sampled_at": "00:00 UTC on the 1st of each month",
            "ayanamsa": "lahiri",
            "node_model": "mean",
            "note": (
                "Monthly samples alias the Moon (about 13 degrees a day); "
                "its curve here is not its path."
            ),
        },
        inputs={"engine": engine.get_ephemeris_info()},
        source="Swiss Ephemeris via vedic_astrology_core EphemerisEngine",
        licence=LICENCES["engine"],
    )


# --------------------------------------------------------------- results
def _market_rows(study: str) -> List[Dict[str, Any]]:
    res = results(study)
    defs = {d["id"]: d for d in market_definitions(study)}
    out = []
    for t in res["tests"]:
        if not t.get("testable", True):
            continue
        out.append(
            {
                "study": study,
                "indicator": t["indicator"],
                "label": defs[t["indicator"]]["label"],
                "definition": defs[t["indicator"]]["definition"],
                "group": t["target"],
                "period": t["period"],
                "measure": "difference in means",
                "unit": t["unit"],
                "effect": t["effect"],
                "lo": t["ci_low"],
                "hi": t["ci_high"],
                "z": t.get("effect_z"),
                "p": t["p_value"],
                "q": t.get("q_value"),
                "significant": bool(t.get("significant")),
                "null": 0.0,
                "n_active": t["n_active"],
            }
        )
    return out


def _quake_rows() -> List[Dict[str, Any]]:
    res = results("earthquake")
    defs = {s["id"]: s for s in hypothesis("earthquake")["indicators"]}
    full = pd.read_csv(REPO / "studies/earthquake/artifacts/rate_tests_all.csv")
    full = full[(full["period"] == "full") & full["catalogue"].isin(["gk", "nn"])]
    rows = (
        res["family"]
        + res["confirmation"]
        + res["raw_descriptive"]
        + json.loads(full.to_json(orient="records"))
    )
    out = []
    for t in rows:
        if t.get("skipped"):
            continue
        rr = t["rate_ratio"]
        spec = defs[t["indicator"]]
        q = t.get("q_value", t.get("q_value_descriptive"))
        out.append(
            {
                "study": "earthquake",
                "indicator": t["indicator"],
                "label": t["label"],
                "definition": spec.get("definition") or t["label"],
                "group": t["catalogue"],
                "period": t["period"],
                "measure": "rate ratio",
                "unit": "x",
                "effect": rr,
                "lo": t["ci_low"],
                "hi": t["ci_high"],
                "z": math.log2(rr) if rr and rr > 0 else None,
                "p": t["p_value"],
                "q": q,
                "significant": bool(t.get("significant") or t.get("confirmed")),
                "null": 1.0,
                "n_active": t["n_in"],
            }
        )
    return out


def _numerology_rows() -> List[Dict[str, Any]]:
    res = results("numerology_vs_astrology")
    out = []
    for p in res["H2_planets"]:
        out.append(
            {
                "study": "numerology_vs_astrology",
                "indicator": p["id"].lower(),
                "label": p["planet"],
                "definition": (
                    "correlation between 'numerology planet rules the day' "
                    "and the planet's dignity score; TOST margin +-0.10"
                ),
                "group": "H2",
                "period": "full",
                "measure": "Pearson r (90% CI)",
                "unit": "r",
                "effect": p["r"],
                "lo": p["r_ci90_low"],
                "hi": p["r_ci90_high"],
                "z": p["r"],
                "p": p["p_tost"],
                "q": None,
                "significant": bool(p["equivalent"]),
                "null": 0.0,
                "n_active": p["n"],
            }
        )
    k = res["H1_kappa"]
    out.append(
        {
            "study": "numerology_vs_astrology",
            "indicator": "kappa",
            "label": "Cohen's kappa, numerology planet vs Moon's nakshatra lord",
            "definition": "agreement beyond chance; TOST margin +-0.05",
            "group": "H1",
            "period": "full",
            "measure": "kappa (90% CI)",
            "unit": "k",
            "effect": k["kappa"],
            "lo": k["ci90_tost"][0],
            "hi": k["ci90_tost"][1],
            "z": k["kappa"],
            "p": k["p_tost"],
            "q": None,
            "significant": bool(k["equivalent"]),
            "null": 0.0,
            "n_active": k["n"],
        }
    )
    return out


def study_status() -> List[Dict[str, Any]]:
    """Return one factual status card per study, without verdicts."""
    g, s = results("gold_market"), results("silver_market")
    e, n = results("earthquake"), results("numerology_vs_astrology")
    mundane = json.loads((REPO / "studies/mundane/artifacts/summary.json").read_text())

    def market(name, r, link):
        """Market."""
        h = r["headline"]
        return {
            "study": name,
            "status": "Pre-registered; run " + r["generated_utc"][:10],
            "link": link,
            "headline": (
                f"{h['n_significant_explore']} of {h['n_tests_explore']} "
                f"exploration tests pass the BY correction; "
                f"{h['n_confirmed']} confirmed in 2016-2026"
            ),
            "commit": r["git"]["commit"][:12],
        }

    h = e["headline"]
    k = n["H1_kappa"]
    return [
        market("Gold market", g, "../studies/gold_market/paper/manuscript.html"),
        market("Silver market", s, "../studies/silver_market/paper/manuscript.html"),
        {
            "study": "Earthquake (Himalayan arc)",
            "status": f"Pre-registered; run with seed {e['seed']}",
            "link": (
                "../studies/earthquake/paper/"
                "EARTHQUAKE_PREDICTION_INDIA_NEPAL_ANALYSIS.html"
            ),
            "headline": (
                f"{h['n_significant_explore']} of {h['family_size']} rate tests "
                f"pass the BY correction in 1976-2010; {h['n_confirmed']} "
                "confirmed in 2011-2026"
            ),
            "commit": e["git"]["commit"][:12],
        },
        {
            "study": "Numerology and astrology",
            "status": "Pre-registered; run " + n["generated_utc"][:10],
            "link": (
                "../studies/numerology_vs_astrology/paper/"
                "NUMEROLOGY_ASTROLOGY_TEMPORAL_DISCONTINUITY.html"
            ),
            "headline": (
                f"Cohen's kappa {k['kappa']:.3f}, 90% CI "
                f"{k['ci90_tost'][0]:.3f} to {k['ci90_tost'][1]:.3f}, inside "
                f"the registered +-{k['margin_kappa']} equivalence margin"
            ),
            "commit": n["git"]["commit"][:12],
        },
        {
            "study": "Mundane",
            "status": "Seeded; awaiting sourced founding times",
            "link": "mundane.html",
            "headline": (
                f"{mundane['countries']} countries, "
                f"{mundane['feature_rows']} sign-level feature rows; "
                "no test run yet"
            ),
            "commit": "",
        },
    ]


def export_results(w: Writer) -> None:
    """Write every registered test and the home-page status strip."""
    rows = (
        _market_rows("gold_market")
        + _market_rows("silver_market")
        + _quake_rows()
        + _numerology_rows()
    )
    inputs = {
        s: {
            "path": f"studies/{s}/artifacts/results.json",
            "sha256": sha256_file(REPO / f"studies/{s}/artifacts/results.json"),
        }
        for s in (
            "gold_market",
            "silver_market",
            "earthquake",
            "numerology_vs_astrology",
        )
    }
    w.write(
        "results.json",
        {
            "effects": rows,
            "status": study_status(),
            "groups": {
                "ret": "daily return (bp/day)",
                "absret": "absolute return (bp/day)",
                "extreme": "extreme-move probability (pp)",
                "raw": "undeclustered catalogue",
                "gk": "Gardner-Knopoff",
                "nn": "nearest-neighbour",
                "H1": "agreement",
                "H2": "per-planet correlation",
            },
            "alpha": 0.05,
        },
        inputs=inputs,
        source="Study artifacts (results.json) of this repository",
        licence=LICENCES["repo"],
    )


# ------------------------------------------------------------- mundane
CONF_RANK = {"documented": 3, "conventional": 2, "disputed": 1}


def chart_moment(c: Dict[str, Any]) -> Optional[datetime]:
    """UTC moment of a candidate chart, or None without a stated time."""
    if not c.get("time"):
        return None
    naive = datetime.fromisoformat(f"{c['date']}T{c['time']}")
    tz = c.get("time_zone") or "UTC"
    if tz == "LMT":
        return (naive - timedelta(hours=float(c["lon"]) / 15.0)).replace(
            tzinfo=timezone.utc
        )
    return pytz.timezone(tz).localize(naive).astimezone(timezone.utc)


def dasha_for(moment: datetime, engine: EphemerisEngine) -> Dict[str, Any]:
    """Return Vimshottari mahadashas and antardashas for a moment."""
    from vedic_astrology_core.dasha.vimshottari import (
        compute_vimshottari_nested_periods,
    )

    jd = engine.datetime_to_julian_day(moment)
    moon = engine.get_all_planet_positions(jd)[Planet.MOON]["longitude"]
    leaves = compute_vimshottari_nested_periods(moment, moon, depth=2)
    out: List[Dict[str, Any]] = []
    for leaf in leaves:
        md, ad = leaf["lords"]
        if not out or out[-1]["lord"] != md:
            out.append(
                {"lord": md, "start": leaf["start"].date().isoformat(), "sub": []}
            )
        out[-1]["end"] = leaf["end"].date().isoformat()
        out[-1]["sub"].append(
            {
                "lord": ad,
                "start": leaf["start"].date().isoformat(),
                "end": leaf["end"].date().isoformat(),
            }
        )
    return {"moon_longitude": round(moon, 4), "mahadashas": out}


def _count_true(series: pd.Series) -> int:
    """Count True values in a column read from CSV (bools or strings)."""
    return int(series.astype(str).str.lower().eq("true").sum())


def export_mundane(w: Writer, offline: bool) -> None:
    """Write countries, candidate charts, events and dasha files."""
    data = REPO / "studies" / "mundane" / "data"
    countries = yaml.safe_load((data / "countries.yaml").read_text())["countries"]
    events = [
        json.loads(line)
        for line in (data / "events.jsonl").read_text().splitlines()
        if line.strip()
    ]
    atlas = fetch_snapshot(ATLAS_URL, "world_atlas_110m", ".json", offline)
    geoms = json.loads(atlas.read_text())["objects"]["countries"]["geometries"]
    by_name = {g["properties"]["name"]: g.get("id") for g in geoms}
    alias = {
        "United States": "United States of America",
        "Czech Republic": "Czechia",
        "East Timor": "Timor-Leste",
    }
    ev_counts: Dict[str, Counter] = defaultdict(Counter)
    for e in events:
        ev_counts[e.get("country_iso")][e.get("event_type") or "Unknown"] += 1
    engine = EphemerisEngine(node_model="mean")
    rows, dashas = [], {}
    for c in countries:
        cands = []
        for i, k in enumerate(c.get("candidate_charts") or []):
            moment = chart_moment(k)
            key = f"{c['iso']}-{i}"
            conventional = k.get("confidence") == "conventional"
            if moment is not None:
                dashas[key] = {
                    "country": c["name"],
                    "event": k.get("event"),
                    "moment_utc": moment.isoformat(),
                    "conventional_time": conventional,
                    **dasha_for(moment, engine),
                }
            src = k.get("source") or {}
            cands.append(
                {
                    "key": key,
                    "event": k.get("event"),
                    "date": str(k.get("date")),
                    "time": k.get("time"),
                    "time_zone": k.get("time_zone"),
                    "place": k.get("place"),
                    "confidence": k.get("confidence"),
                    "conventional_time": conventional,
                    "used_by": k.get("used_by") or [],
                    "source_url": src.get("url"),
                    "source_title": src.get("title"),
                    "source_checked": bool(src.get("checked")),
                    "has_dasha": moment is not None,
                }
            )
        best = max((CONF_RANK.get(k["confidence"], 0) for k in cands), default=0)
        f = c.get("founding") or {}
        rows.append(
            {
                "iso": c["iso"],
                "name": c["name"],
                "atlas_id": by_name.get(alias.get(c["name"], c["name"])),
                "lat": c.get("capital_lat"),
                "lon": c.get("capital_lon"),
                "founding_date": str(f.get("date")),
                "time_known": bool(f.get("time_known")),
                "n_candidates": len(cands),
                "n_timed": sum(k["has_dasha"] for k in cands),
                "best_confidence": {v: k for k, v in CONF_RANK.items()}.get(
                    best, "none"
                ),
                "candidates": cands,
                "events": dict(ev_counts.get(c["iso"], {})),
            }
        )
    feats = pd.read_csv(REPO / "studies/mundane/artifacts/features.csv")
    tn = feats[feats["family"] == "transit_natal"]
    sign_summary = (
        tn.groupby(["event_type", "transit_planet"])
        .agg(
            rows=("family", "size"),
            conjunct=("conjunct_sign", _count_true),
            opposition=("opposition_sign", _count_true),
            aspect=("aspect_whole_sign", _count_true),
        )
        .reset_index()
    )
    summary = json.loads((REPO / "studies/mundane/artifacts/summary.json").read_text())
    ins = {
        "countries": {
            "path": "studies/mundane/data/countries.yaml",
            "sha256": sha256_file(data / "countries.yaml"),
        },
        "events": {
            "path": "studies/mundane/data/events.jsonl",
            "sha256": sha256_file(data / "events.jsonl"),
        },
        "atlas": {"url": ATLAS_URL, "sha256": sha256_file(atlas)},
    }
    all_types = Counter(e.get("event_type") or "Unknown" for e in events)
    w.write(
        "mundane_countries.json",
        {
            "countries": rows,
            "event_types": dict(all_types),
            "atlas_url": ATLAS_URL,
            "summary": summary,
            "sign_features": json.loads(sign_summary.to_json(orient="records")),
        },
        inputs=ins,
        source="studies/mundane (countries.yaml, events.jsonl, "
        "artifacts/features.csv)",
        licence=LICENCES["mundane"],
    )
    w.write(
        "mundane_dasha.json",
        {
            "charts": dashas,
            "system": "Vimshottari, Julian year, Lahiri, mean node",
            "note": (
                "Computed only for candidate charts that state a time. A "
                "conventional time (midnight, noon) gives a conventional "
                "dasha, flagged as such."
            ),
        },
        inputs={"countries": ins["countries"]},
        source="Computed from studies/mundane/data/countries.yaml",
        licence=LICENCES["mundane"] + "; " + LICENCES["engine"],
    )


# --------------------------------------------------------------- rules
def _humanise(name: str) -> str:
    return name.replace("_", " ").capitalize()


def plain_words(cond: Any) -> Dict[str, Any]:
    """Render a condition tree in plain words without evaluating it."""
    from vedic_astrology_core.rules.predicates import PREDICATES
    from vedic_astrology_core.rules.schema import AllOf, AnyOf, AtLeast, Leaf, NotOf

    if isinstance(cond, AllOf):
        return {
            "text": "All of these hold",
            "children": [plain_words(c) for c in cond.all],
        }
    if isinstance(cond, AnyOf):
        return {
            "text": "Any one of these holds",
            "children": [plain_words(c) for c in cond.any],
        }
    if isinstance(cond, NotOf):
        return {"text": "This does not hold", "children": [plain_words(cond.not_)]}
    if isinstance(cond, AtLeast):
        body = cond.at_least
        return {
            "text": f"At least {body.n} of these hold",
            "children": [plain_words(c) for c in body.of],
        }
    if isinstance(cond, Leaf):
        spec = PREDICATES[cond.predicate]
        doc = spec.doc.splitlines()[0] if spec.doc else ""
        doc = re.sub(r"^Check that (the )?", "", doc).replace("``", "")
        label = cond.params.label().replace("=", ": ").replace(", ", "; ")
        return {
            "text": f"{_humanise(cond.predicate)}: {label}",
            "gloss": doc[:1].upper() + doc[1:],
            "children": [],
        }
    return {"text": str(cond), "children": []}


def source_type(rule, path: Path) -> str:
    """Classify a rule's source: practitioner, classical text, registry, other."""
    parts = set(path.parts)
    notes = rule.notes or {}
    if "practitioner" in parts or "practitioner" in notes:
        return "practitioner"
    if rule.source.cited:
        return "classical text"
    if rule.source.app_registry:
        return "application registry"
    return "other"


def export_rules(w: Writer) -> None:
    """Write every rule with plain-word conditions and case outcomes."""
    from vedic_astrology_core.rules.engine import run_reference_cases
    from vedic_astrology_core.rules.loader import default_rules_dir, load_rules

    loaded, problems = load_rules([default_rules_dir()])
    rows = []
    for item in sorted(loaded, key=lambda x: x.rule.id):
        rule, path = item.rule, Path(item.path)
        cases = []
        results_ = (
            [] if rule.status == "needs_predicates" else run_reference_cases(rule)
        )
        for i, case in enumerate(rule.reference_cases):
            res = results_[i] if i < len(results_) else None
            outcome = (
                "not run"
                if res is None
                else ("error" if res.error else ("pass" if res.passed else "fail"))
            )
            cases.append(
                {
                    "moment": case.moment.isoformat(),
                    "expect": case.expect,
                    "note": case.note,
                    "verified_with": case.verified_with,
                    "outcome": outcome,
                }
            )
        n_pass = sum(c["outcome"] == "pass" for c in cases)
        notes = rule.notes or {}
        original = notes.get("original_condition")
        rows.append(
            {
                "id": rule.id,
                "name": rule.name,
                "domain": rule.domain,
                "tier": rule.tier,
                "status": rule.status,
                "claim": rule.claim,
                "author": rule.author,
                "source": rule.source.short(),
                "source_url": rule.source.url,
                "source_note": rule.source.note,
                "source_type": source_type(rule, path),
                "path": rel(path),
                "conditions": plain_words(rule.conditions) if rule.conditions else None,
                "original_condition": (
                    original
                    if isinstance(original, list)
                    else ([original] if original else [])
                ),
                "missing_predicates": notes.get("missing_predicates") or [],
                "window": (
                    rule.window.model_dump(exclude_none=True) if rule.window else None
                ),
                "expected_effect": (
                    rule.expected_effect.model_dump(exclude_none=True)
                    if rule.expected_effect
                    else None
                ),
                "cases": cases,
                "reference": (
                    "not run"
                    if not cases or rule.status == "needs_predicates"
                    else f"{n_pass}/{len(cases)} pass"
                ),
            }
        )
    files = sorted(Path(default_rules_dir()).rglob("*.yaml"))
    digest = hashlib.sha256(
        b"".join(sha256_file(p).encode() for p in files)
    ).hexdigest()
    w.write(
        "rules.json",
        {"rules": rows, "problems": [str(p) for p in problems]},
        inputs={
            "rules": {
                "path": "rules/",
                "files": len(files),
                "sha256_of_file_hashes": digest,
            }
        },
        source="rules/**/*.yaml via vedic_astrology_core.rules.loader",
        licence=LICENCES["repo"],
        note="Reference cases are run with the engine; conditions are rendered, "
        "not evaluated.",
    )


# ------------------------------------------------------------ numerology
NAKSHATRAS = [
    "Ashvini",
    "Bharani",
    "Krittika",
    "Rohini",
    "Mrigashira",
    "Ardra",
    "Punarvasu",
    "Pushya",
    "Ashlesha",
    "Magha",
    "Purva Phalguni",
    "Uttara Phalguni",
    "Hasta",
    "Chitra",
    "Swati",
    "Vishakha",
    "Anuradha",
    "Jyeshtha",
    "Mula",
    "Purva Ashadha",
    "Uttara Ashadha",
    "Shravana",
    "Dhanishtha",
    "Shatabhisha",
    "Purva Bhadrapada",
    "Uttara Bhadrapada",
    "Revati",
]


def export_numerology(w: Writer) -> None:
    """Write the daily numerology label and Moon longitude series."""
    here = REPO / "studies" / "numerology_vs_astrology" / "scripts"
    pipe = load_module("num_pipeline", here / "pipeline.py")
    hyp = pipe.load_hypothesis()
    frame = pipe.build_frame(hyp)
    engine = EphemerisEngine(node_model=hyp["node_model"])
    hh, mm = (int(x) for x in hyp["sample_time"].split(":"))
    moon = []
    for d in pd.to_datetime(frame["date"]):
        moment = datetime(d.year, d.month, d.day, hh, mm, tzinfo=timezone.utc)
        jd = engine.datetime_to_julian_day(moment)
        moon.append(
            round(engine.get_all_planet_positions(jd)[Planet.MOON]["longitude"], 3)
        )
    cols = {
        "date": pd.to_datetime(frame["date"]).dt.strftime("%Y-%m-%d").tolist(),
        "number": frame["numerology_mulanka_number"].astype(int).tolist(),
        "num_planet": frame["numerology_active_planet"].tolist(),
        "nak_lord": frame["astrology_moon_nakshatra_lord"].tolist(),
        "moon": moon,
        "nakshatra": [NAKSHATRAS[int(m // (360 / 27)) % 27] for m in moon],
    }
    res = results("numerology_vs_astrology")
    w.write(
        "numerology_daily.json",
        {
            "columns": cols,
            "summary": res["description"],
            "kappa": res["H1_kappa"],
            "sample_time": f"{hyp['sample_time']} {hyp['tz']}",
        },
        inputs={
            "hypothesis": {
                "path": "studies/numerology_vs_astrology/hypothesis.yaml",
                "sha256": res["hypothesis_sha256"],
            },
            "engine": engine.get_ephemeris_info(),
        },
        source="Regenerated with the study's pipeline.build_frame",
        licence=LICENCES["engine"],
    )


# ------------------------------------------------------------------ main
STEPS = (
    "results",
    "markets",
    "pinksheet",
    "earthquake",
    "ephemeris",
    "mundane",
    "rules",
    "numerology",
)


def main(argv=None) -> int:
    """Run the selected export steps."""
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument(
        "--offline",
        action="store_true",
        help="use existing snapshots only; never fetch",
    )
    ap.add_argument(
        "--only",
        default=",".join(STEPS),
        help="comma-separated subset of: " + ", ".join(STEPS),
    )
    args = ap.parse_args(argv)
    np.random.seed(args.seed)
    w = Writer(args.out, args.seed)
    steps = [s.strip() for s in args.only.split(",") if s.strip()]
    for s in steps:
        if s not in STEPS:
            ap.error(f"unknown step {s!r}")
    print(f"exporting to {rel(args.out)} (commit {w.commit[:12]}, seed {args.seed})")
    table = {
        "results": lambda: export_results(w),
        "markets": lambda: export_markets(w),
        "pinksheet": lambda: export_pink_sheet(w, args.offline),
        "earthquake": lambda: export_earthquake(w),
        "ephemeris": lambda: export_ephemeris(w),
        "mundane": lambda: export_mundane(w, args.offline),
        "rules": lambda: export_rules(w),
        "numerology": lambda: export_numerology(w),
    }
    for s in steps:
        table[s]()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
