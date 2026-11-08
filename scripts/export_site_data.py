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

    python scripts/export_site_data.py --seed 42   # after pip install -e .
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
for _p in (REPO, REPO / "libs"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from studies._paths import SNAPSHOT_ROOT  # noqa: E402
from vedic_astrology_core.astrology.ephemeris import EphemerisEngine  # noqa: E402
from vedic_astrology_core.config.constants import Planet  # noqa: E402
from vedic_astrology_core.rules.vocabulary import NAKSHATRA_NAMES  # noqa: E402

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


def quake_catalogue():
    """Return (pipeline, hypothesis, catalogue, info, gk, nn) as the study does."""
    here = REPO / "studies" / "earthquake" / "scripts"
    pipe = sys.modules.get("eq_pipeline") or load_module(
        "eq_pipeline", here / "pipeline.py"
    )
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
    return pipe, hyp, cat, info, gk, nn


def export_earthquake(w: Writer) -> None:
    """Write the declustered catalogue and indicator windows."""
    pipe, hyp, cat, info, gk, nn = quake_catalogue()
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


def _plain(value: Any) -> Any:
    """Return a pydantic model, list or scalar as plain JSON data."""
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json", by_alias=True, exclude_none=True)
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _plain(v) for k, v in value.items()}
    if isinstance(value, (datetime, pd.Timestamp)):
        return value.isoformat()
    return value


def validation_state(validation: Any, tuning_log: List[Any]) -> str:
    """Return confirmed, not_confirmed, tuned or unvalidated."""
    status = (validation or {}).get("status") if isinstance(validation, dict) else None
    if status in ("confirmed", "not_confirmed"):
        return status
    return "tuned" if tuning_log else "unvalidated"


def rule_v2(rule) -> Dict[str, Any]:
    """Return schema v2 fields (ADR-003) and the browser-evaluable tree.

    Fields the rule model does not have yet are exported empty, so the site
    works before and after the schema lands.
    """
    tuning_log = _plain(getattr(rule, "tuning_log", None) or [])
    validation = _plain(getattr(rule, "validation", None))
    window_days = None
    if rule.window is not None:
        k = WINDOW_DAYS[rule.window.unit]
        window_days = {
            "before": round((rule.window.before or 0) * k, 3),
            "after": round((rule.window.after or 0) * k, 3),
        }
    return {
        "version": int(getattr(rule, "version", 1) or 1),
        "params": _plain(getattr(rule, "params", None)),
        "strength": _plain(getattr(rule, "strength", None)),
        "tuning_log": tuning_log,
        "validation": validation,
        "review": _plain(getattr(rule, "review", None) or []),
        "validation_state": validation_state(validation, tuning_log),
        "machine": machine_tree(rule.conditions),
        **param_links(rule),
        "client_evaluable": client_evaluable(rule),
        "window_days": window_days,
    }


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
                **rule_v2(rule),
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
        {
            "rules": rows,
            "problems": [str(p) for p in problems],
            "validation_counts": {
                k: sum(r["validation_state"] == k for r in rows)
                for k in ("confirmed", "not_confirmed", "tuned", "unvalidated")
            },
        },
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


# ------------------------------------------------------------ workbench
# ADR-003: the workbench tunes on the EXPLORE period only. Confirm-period
# rows are never exported; ``assert_explore_only`` hard-fails the export if
# one slips through.
WORKBENCH_STUDIES = {
    "earthquake": "earthquake",
    "gold": "gold_market",
    "silver": "silver_market",
}
# Predicates the browser evaluates on the daily arrays (whole-sign houses,
# no Lagna: the daily rows carry no place).
CLIENT_PREDICATES = {
    "conjunct_within",
    "separation_within",
    "in_sign",
    "in_house_from",
    "in_kendra_from",
    "in_trikona_from",
    "retrograde",
    "moon_phase",
    "in_nakshatra",
    "dasha_lord_is",
}
WINDOW_DAYS = {"hours": 1 / 24, "days": 1.0, "weeks": 7.0, "months": 30.436875}
WINDOW_DAYS["years"] = 365.25


def split_of(hyp: Dict[str, Any]) -> Dict[str, Optional[pd.Timestamp]]:
    """Return the explore start and confirm start of a study's split.

    Reads ``split: {explore: [a, b], confirm: [c, d]}`` (earthquake),
    ``periods: {explore_end, confirm_start}`` (markets) or the ADR-003 form
    ``confirm: {start: ...}``.

    Raises:
        SystemExit: If the hypothesis file states no confirm start.
    """
    if "split" in hyp:
        sp = hyp["split"]
        return {
            "explore_start": pd.Timestamp(sp["explore"][0]),
            "confirm_start": pd.Timestamp(sp["confirm"][0]),
        }
    if isinstance(hyp.get("confirm"), dict) and "start" in hyp["confirm"]:
        start = (hyp.get("explore") or {}).get("start")
        return {
            "explore_start": pd.Timestamp(start) if start else None,
            "confirm_start": pd.Timestamp(hyp["confirm"]["start"]),
        }
    if "periods" in hyp and "confirm_start" in hyp["periods"]:
        return {
            "explore_start": None,
            "confirm_start": pd.Timestamp(hyp["periods"]["confirm_start"]),
        }
    raise SystemExit("hypothesis.yaml states no confirm start: refusing to export")


def assert_explore_only(dates: List[str], confirm_start: pd.Timestamp) -> None:
    """Hard-fail if any exported date is on or after the confirm start."""
    cut = confirm_start.strftime("%Y-%m-%d")
    bad = [d for d in dates if d >= cut]
    if bad:
        raise SystemExit(
            f"workbench export would leak {len(bad)} confirm-period rows "
            f"(first {bad[0]}, confirm starts {cut}); refusing to write"
        )


def sky_row(engine: EphemerisEngine, moment: datetime) -> List[Any]:
    """Nine longitudes (0.01 deg), retrograde bitmask, tithi, nakshatra index."""
    pos = engine.get_all_planet_positions(engine.datetime_to_julian_day(moment))
    lons = [pos[Planet[g]]["longitude"] for g in GRAHAS]
    mask = 0
    for i, g in enumerate(GRAHAS):
        if pos[Planet[g]]["longitude_speed"] < 0:
            mask |= 1 << i
    tithi = int(((lons[1] - lons[0]) % 360.0) // 12) + 1
    nak = int(lons[1] // (360.0 / 27)) % 27
    return [round(x, 2) for x in lons] + [mask, tithi, nak]


def _walk(cond: Any):
    """Yield (predicate, params) for every leaf of a condition tree."""
    from vedic_astrology_core.rules.engine import iter_leaves

    for leaf in iter_leaves(cond):
        yield leaf.predicate, leaf.params.model_dump(by_alias=True, exclude_none=True)


def machine_tree(cond: Any) -> Optional[Dict[str, Any]]:
    """Return the condition tree as plain JSON for the browser evaluator."""
    from vedic_astrology_core.rules.schema import AllOf, AnyOf, AtLeast, Leaf, NotOf

    if cond is None:
        return None
    if isinstance(cond, AllOf):
        return {"op": "all", "of": [machine_tree(c) for c in cond.all]}
    if isinstance(cond, AnyOf):
        return {"op": "any", "of": [machine_tree(c) for c in cond.any]}
    if isinstance(cond, NotOf):
        return {"op": "not", "of": [machine_tree(cond.not_)]}
    if isinstance(cond, AtLeast):
        body = cond.at_least
        return {"op": "at_least", "n": body.n, "of": [machine_tree(c) for c in body.of]}
    if isinstance(cond, Leaf):
        params = cond.params.model_dump(by_alias=True, exclude_none=True)
        return {"pred": cond.predicate, "params": params}
    return {"pred": "unknown", "params": {}}


def _mark(base: Any, other: Any, name: str, out: Any) -> None:
    """Write ``$name`` into ``out`` wherever ``base`` and ``other`` leaves differ."""
    if base.get("pred"):
        for key, value in base["params"].items():
            if other["params"].get(key) != value:
                out["params"][key] = f"${name}"
        return
    for b, o, t in zip(base["of"], other["of"], out["of"]):
        _mark(b, o, name, t)


def param_links(rule) -> Dict[str, Any]:
    """Return the condition tree with ``$param`` slots and what each param drives.

    Rules bind ``$name`` to numbers at load time, so each param is moved to
    another legal value and the leaves (or window ends) that change are the
    ones it drives. Window params carry their unit in days.
    """
    params = getattr(rule, "params", None) or {}
    base = machine_tree(rule.conditions)
    template = json.loads(json.dumps(base)) if base else None
    links: Dict[str, Any] = {}
    for name, spec in params.items():
        alt = spec.max if spec.value != spec.max else spec.min
        if alt == spec.value:
            continue
        try:
            other = rule.bind({name: alt})
        except ValueError:
            continue
        targets = []
        if base is not None:
            alt_tree = machine_tree(other.conditions)
            before = json.dumps(template)
            _mark(base, alt_tree, name, template)
            if json.dumps(template) != before:
                targets.append("conditions")
        if rule.window is not None and other.window is not None:
            k = WINDOW_DAYS[rule.window.unit]
            for end in ("before", "after"):
                if getattr(rule.window, end) != getattr(other.window, end):
                    targets.append(f"window_{end}")
                    links.setdefault(name, {})["days_per_unit"] = k
        links.setdefault(name, {})["targets"] = targets
    return {"machine_template": template, "param_links": links}


def client_evaluable(rule) -> bool:
    """Return True when the browser can evaluate every leaf (no place needed)."""
    if rule.conditions is None or rule.status == "needs_predicates":
        return False
    for pred, params in _walk(rule.conditions):
        if pred not in CLIENT_PREDICATES:
            return False
        if "Lagna" in (params.get("planet"), params.get("from")):
            return False
        if pred == "dasha_lord_is" and (rule.natal is None or params["level"] > 2):
            return False
    return True


def dasha_runs(natal, moments: List[datetime]) -> List[List[int]]:
    """Return ``[row, lord1, lord2]`` at each row where the dasha changes."""
    from vedic_astrology_core.dasha.vimshottari import (
        compute_vimshottari_nested_periods,
    )
    from vedic_astrology_core.rules.context import Sky

    sky = Sky(natal.moment, None, "mean")
    leaves = compute_vimshottari_nested_periods(natal.moment, sky.lon("Moon"), depth=2)
    names = [g.title() for g in GRAHAS]
    runs: List[List[int]] = []
    j = 0
    for i, m in enumerate(moments):
        while j < len(leaves) and leaves[j]["end"] <= m:
            j += 1
        if j >= len(leaves) or leaves[j]["start"] > m:
            lords = [-1, -1]
        else:
            lords = [names.index(x) for x in leaves[j]["lords"]]
        if not runs or runs[-1][1:] != lords:
            runs.append([i] + lords)
    return runs


def _natal_charts() -> Dict[str, Any]:
    """Natal charts of client-evaluable dasha rules, keyed by rule id."""
    from vedic_astrology_core.rules.loader import default_rules_dir, load_rules

    loaded, _ = load_rules([default_rules_dir()])
    out = {}
    for item in loaded:
        rule = item.rule
        uses = any(p == "dasha_lord_is" for p, _ in _walk(rule.conditions))
        if rule.natal is not None and uses and client_evaluable(rule):
            out[rule.id] = rule.natal
    return out


def _workbench_quake() -> Dict[str, Any]:
    """Daily explore rows of the earthquake study with event counts."""
    pipe, hyp, cat, info, gk, nn = quake_catalogue()
    split = split_of(hyp)
    days = pd.date_range(
        split["explore_start"], split["confirm_start"], freq="D", inclusive="left"
    )
    day = cat["time"].dt.tz_convert("UTC").dt.strftime("%Y-%m-%d")
    counts = {
        "raw": Counter(day),
        "gk": Counter(day[gk.astype(bool)]),
        "nn": Counter(day[nn.to_numpy().astype(bool)]),
    }
    engine = EphemerisEngine(node_model=hyp["ephemeris"]["node_model"])
    moments = [datetime(d.year, d.month, d.day, 12, tzinfo=timezone.utc) for d in days]
    rows = []
    for d, m in zip(days, moments):
        key = d.strftime("%Y-%m-%d")
        rows.append(
            [key]
            + sky_row(engine, m)
            + [counts[c].get(key, 0) for c in ("raw", "gk", "nn")]
        )
    return {
        "hyp": hyp,
        "split": split,
        "moments": moments,
        "rows": rows,
        "events": ["ev_raw", "ev_gk", "ev_nn"],
        "event_labels": {
            "ev_raw": "Undeclustered events that day",
            "ev_gk": "Gardner-Knopoff mainshocks that day",
            "ev_nn": "Nearest-neighbour (Zaliapin) mainshocks that day",
        },
        "unit": "day",
        "sampled_at": "12:00 UTC each calendar day",
        "min_shift": int(hyp["test"]["min_shift_days"]),
        "alternative_default": "greater",
        "inputs": {
            "usgs_snapshot": {"path": info["snapshot"], "sha256": info["sha256"]},
            "hypothesis": {
                "path": "studies/earthquake/hypothesis.yaml",
                "sha256": sha256_file(pipe.fc.HYPOTHESIS),
            },
        },
        "source": "USGS ComCat (Himalayan-arc polygon), explore period only",
        "licence": LICENCES["usgs"] + "; sky: " + LICENCES["engine"],
    }


def _workbench_market(study: str) -> Dict[str, Any]:
    """Explore trading bars of a market study: sky on bar t-1, extreme on bar t."""
    hyp = hypothesis(study)
    split = split_of(hyp)
    frame_path = REPO / "studies" / study / "artifacts" / "overlay_frame.csv"
    if not frame_path.exists():
        raise SystemExit(f"{rel(frame_path)} missing: run the {study} pipeline")
    df = pd.read_csv(frame_path, parse_dates=["date"])
    res = results(study)
    r = df["log_return"]
    window = int(hyp["tests"]["extreme_window_bars"])
    thresh = r.abs().rolling(window).quantile(float(hyp["tests"]["extreme_quantile"]))
    thresh = thresh.shift(1)
    extreme = ((r.abs() > thresh) & thresh.notna()).astype(int).to_numpy()
    tz = pytz.timezone(res["data"]["tz"])
    hh, mm = (int(x) for x in res["data"]["sample_time"].split(":"))
    engine = EphemerisEngine(node_model=hyp.get("node_model", "mean"))
    dates = df["date"].dt.strftime("%Y-%m-%d").tolist()
    keep = [
        i
        for i in range(1, len(df))
        if df["date"][i] < split["confirm_start"]
        and (split["explore_start"] is None or df["date"][i] >= split["explore_start"])
    ]
    moments, rows = [], []
    for i in keep:
        prev = df["date"][i - 1]
        local = tz.localize(datetime(prev.year, prev.month, prev.day, hh, mm))
        m = local.astimezone(timezone.utc)
        moments.append(m)
        rows.append([dates[i]] + sky_row(engine, m) + [int(extreme[i])])
    return {
        "hyp": hyp,
        "split": {
            "explore_start": pd.Timestamp(dates[keep[0]]),
            "confirm_start": split["confirm_start"],
        },
        "moments": moments,
        "rows": rows,
        "events": ["extreme"],
        "event_labels": {
            "extreme": (
                f"1 if the bar's absolute move exceeds the past-only "
                f"{hyp['tests']['extreme_quantile']:.0%} quantile of the previous "
                f"{window} bars"
            )
        },
        "unit": "trading bar",
        "sampled_at": (
            f"sky at {res['data']['sample_time']} {res['data']['tz']} on the "
            "previous trading bar (the study's lag)"
        ),
        "min_shift": int(hyp["tests"]["min_shift_bars"]),
        "alternative_default": "two-sided",
        "inputs": {
            "overlay_frame": {
                "path": rel(frame_path),
                "underlying_sha256": res["data"]["sha256"],
                "series": res["data"]["label"],
            },
            "hypothesis": {
                "path": f"studies/{study}/hypothesis.yaml",
                "sha256": sha256_file(REPO / "studies" / study / "hypothesis.yaml"),
            },
        },
        "source": res["data"]["label"] + ", explore period only; flags only",
        "licence": LICENCES["yahoo_derived"] + "; sky: " + LICENCES["engine"],
    }


def export_workbench(w: Writer) -> None:
    """Write ``workbench_<study>.json``: explore-period daily arrays only."""
    natals = _natal_charts()
    for key, study in WORKBENCH_STUDIES.items():
        d = _workbench_quake() if key == "earthquake" else _workbench_market(study)
        dates = [r[0] for r in d["rows"]]
        assert_explore_only(dates, d["split"]["confirm_start"])
        dasha = {
            rid: {
                "label": natal.label or natal.moment.isoformat(),
                "runs": dasha_runs(natal, d["moments"]),
            }
            for rid, natal in natals.items()
        }
        fields = (
            ["date"]
            + [g.title() for g in GRAHAS]
            + ["retro_mask", "tithi", "nakshatra"]
            + d["events"]
        )
        w.write(
            f"workbench_{key}.json",
            {
                "study": study,
                "fields": fields,
                "rows": d["rows"],
                "planets": [g.title() for g in GRAHAS],
                "nakshatras": NAKSHATRA_NAMES,
                "events": d["events"],
                "event_labels": d["event_labels"],
                "dasha": dasha,
                "explore": {
                    "start": dates[0],
                    "end": dates[-1],
                    "confirm_start": d["split"]["confirm_start"].strftime("%Y-%m-%d"),
                },
                "unit": d["unit"],
                "sampled_at": d["sampled_at"],
                "min_shift": d["min_shift"],
                "alternative_default": d["alternative_default"],
                "notes": {
                    "longitudes": "sidereal (Lahiri), mean node, degrees, 0.01 deg",
                    "retro_mask": "bit i set when planet i (fields order) has "
                    "negative longitude speed",
                    "tithi": "1-30 from the Moon-Sun elongation in 12 deg steps",
                    "nakshatra": "0-26, Ashwini = 0",
                    "dasha": "per natal chart of a dasha rule: [row, mahadasha "
                    "lord, antardasha lord] where the period changes "
                    "(planet index, -1 outside the cycle)",
                },
            },
            inputs=d["inputs"],
            source=d["source"],
            licence=d["licence"],
            note="Explore period only (ADR-003); confirm-period rows are not "
            "exported and the export fails if one would be.",
        )


# --------------------------------------------------------- combination atlas
ATLAS_CSV = REPO / "studies" / "combinations" / "artifacts" / "atlas.csv"
ATLAS_RESULTS = REPO / "studies" / "combinations" / "artifacts" / "results.json"
ATLAS_FIXTURE = REPO / "tests" / "site" / "fixtures" / "atlas_fixture.csv"
ATLAS_ALIASES = {
    "id": ["id", "candidate", "candidate_id"],
    "label": ["definition", "label", "description", "name"],
    "planets": ["planets", "planet", "bodies"],
    "structure": ["structure", "kind", "family"],
    "template": ["template"],
    "depth": ["depth", "n_terms"],
    "effect": ["explore_rate_ratio", "rate_ratio", "effect", "rr"],
    "ci_low": ["explore_ci_low", "ci_low", "lo"],
    "ci_high": ["explore_ci_high", "ci_high", "hi"],
    "p": ["explore_p_value", "p_explore", "explore_p", "p_value", "p"],
    "p_rw": ["explore_p_rw", "p_rw"],
    "q": ["explore_q_value", "q_explore", "explore_q", "q_value", "q"],
    "n_in": ["explore_n_in", "n_in", "events_in"],
    "confirm_effect": ["confirm_rate_ratio"],
    "confirm_p": ["confirm_p_value"],
    "confirmed": ["confirmed"],
    "status": ["status", "verdict", "outcome"],
}
ATLAS_PLANETS = "SUN|MOON|MARS|MERCURY|JUPITER|VENUS|SATURN|RAHU|KETU"
ATLAS_KINDS = (
    ("@sign=", "sign"),
    ("@house_from_lagna=", "house from lagna"),
    ("@house_from_moon=", "house from Moon"),
    ("@nakshatra_group=", "nakshatra group"),
    ("~conj~", "conjunction"),
    (">aspect>", "aspect"),
    ("dasha1=", "mahadasha lord"),
    ("dasha2=", "antardasha lord"),
)
SURVIVOR_WORDS = ("survivor", "survived", "carried", "confirmed", "significant")


def atlas_key_parts(key: str) -> Dict[str, Any]:
    """Return the planets and structure named by an atlas key."""
    planets = sorted({p.title() for p in re.findall(rf"\b({ATLAS_PLANETS})\b", key)})
    kinds = [label for token, label in ATLAS_KINDS if token in key]
    return {"planets": planets, "structure": " + ".join(kinds) or "other"}


def _num(v: Any, digits: int = 4) -> Any:
    """Round a float to ``digits`` significant figures; NaN becomes None."""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if math.isnan(f) or math.isinf(f):
        return None
    return float(f"{f:.{digits}g}")


def by_threshold(pvals: np.ndarray, alpha: float = 0.05) -> float:
    """Return the largest p that passes Benjamini-Yekutieli at ``alpha`` (or 0)."""
    p = np.sort(pvals[np.isfinite(pvals)])
    m = len(p)
    if m == 0:
        return 0.0
    c_m = float(np.sum(1.0 / np.arange(1, m + 1)))
    ok = p <= np.arange(1, m + 1) * alpha / (m * c_m)
    return float(p[np.flatnonzero(ok)[-1]]) if ok.any() else 0.0


def export_atlas(w: Writer) -> None:
    """Write ``atlas.json`` from the combination atlas (or a marked fixture)."""
    real = ATLAS_CSV.exists()
    path = ATLAS_CSV if real else ATLAS_FIXTURE
    df = pd.read_csv(path)
    cols: Dict[str, List[Any]] = {}
    for name, aliases in ATLAS_ALIASES.items():
        hit = next((a for a in aliases if a in df.columns), None)
        cols[name] = df[hit].tolist() if hit else [None] * len(df)
    if "key" in df.columns:
        parts = [atlas_key_parts(str(k)) for k in df["key"]]
        cols["planets"] = [x["planets"] for x in parts]
        cols["structure"] = [x["structure"] for x in parts]
    else:
        cols["planets"] = [
            [x for x in re.split(r"[;,|+ ]+", str(v)) if x and x != "nan"]
            for v in cols["planets"]
        ]
    for k in ("effect", "ci_low", "ci_high", "p", "p_rw", "q", "confirm_effect"):
        cols[k] = [_num(v) for v in cols[k]]
    cols["confirm_p"] = [_num(v) for v in cols["confirm_p"]]
    cols["confirmed"] = [str(v).lower() == "true" for v in cols["confirmed"]]
    pvals = np.array([np.nan if v is None else float(v) for v in cols["p"]])
    tested = int(np.isfinite(pvals).sum())
    alpha, threshold, method = 0.05, None, "Benjamini-Yekutieli across the family"
    summary = None
    if real and ATLAS_RESULTS.exists():
        meta = json.loads(ATLAS_RESULTS.read_text(encoding="utf-8"))
        alpha = float(meta.get("alpha", alpha))
        summary = meta.get("counts")
        for k in ("corrected_threshold", "threshold_p", "p_threshold"):
            if k in meta:
                threshold, method = float(meta[k]), meta.get("correction", k)
    if threshold is None:
        threshold = by_threshold(pvals, alpha)
    c_m = float(np.sum(1.0 / np.arange(1, tested + 1))) if tested else 1.0
    first_bar = alpha / (tested * c_m) if tested else 0.0
    status = [str(s).lower() if s is not None else "" for s in cols["status"]]
    cols["status"] = [s if s and s != "nan" else "tested" for s in status]
    has_status = any(s != "tested" for s in cols["status"])
    cols["survivor"] = [
        (
            (s.startswith(SURVIVOR_WORDS) or c)
            if has_status
            else bool(threshold > 0 and float(p) <= threshold)
        )
        for s, c, p in zip(cols["status"], cols["confirmed"], pvals)
    ]
    # Categorical columns as indices into lookup lists; flags as 0/1 (size).
    lookups = {}
    for k in ("structure", "status", "template"):
        values = sorted({str(v) for v in cols[k]})
        lookups[k] = values
        cols[k] = [values.index(str(v)) for v in cols[k]]
    for k in ("confirmed", "survivor"):
        cols[k] = [int(bool(v)) for v in cols[k]]
    inputs = {"atlas": {"path": rel(path), "sha256": sha256_file(path)}}
    if real and ATLAS_RESULTS.exists():
        inputs["results"] = {
            "path": rel(ATLAS_RESULTS),
            "sha256": sha256_file(ATLAS_RESULTS),
        }
    w.write(
        "atlas.json",
        {
            "columns": cols,
            "lookups": lookups,
            "fixture": not real,
            "threshold": threshold,
            "threshold_line": threshold if threshold > 0 else first_bar,
            "threshold_note": (
                "largest p passing the correction"
                if threshold > 0
                else "no candidate passes; the line is the bar the smallest p "
                "would have to clear"
            ),
            "alpha": alpha,
            "correction": method,
            "n": len(df),
            "n_tested": tested,
            "summary": summary,
        },
        inputs=inputs,
        source=(
            "studies/combinations/artifacts/atlas.csv"
            if real
            else "FIXTURE tests/site/fixtures/atlas_fixture.csv (illustrative, "
            "not results): the combination atlas has not been run yet"
        ),
        licence=LICENCES["repo"],
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
    "workbench",
    "atlas",
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
        "workbench": lambda: export_workbench(w),
        "atlas": lambda: export_atlas(w),
    }
    for s in steps:
        table[s]()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
