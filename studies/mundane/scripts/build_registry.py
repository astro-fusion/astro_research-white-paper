#!/usr/bin/env python3
"""Seed the mundane registries (ADR-006 WP-49). Deterministic; copies committed files only.

Writes into `data/registry/mundane/`:

* `charts.yaml`: every candidate chart for India and Nepal from
  `studies/mundane/data/countries.yaml` (which is read, never modified), plus the charts
  taken from the owner's chart files in `studies/mundane/data/owner_charts.yaml`.
* `events.jsonl`: Himalayan earthquakes of Mw 6.0 and above from the hashed USGS snapshot,
  with raw and declustered (Gardner-Knopoff, nearest-neighbour) flags.
* `MANIFEST.json`: SHA-256 of the inputs and outputs. No timestamps, so a re-run is
  byte-identical.

Usage::

    python studies/mundane/scripts/build_registry.py [--snapshot PATH] [--out-dir DIR]
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import yaml

REPO = Path(__file__).resolve().parents[3]
for _p in (REPO, REPO / "libs", REPO / "studies" / "earthquake" / "scripts"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import decluster  # noqa: E402
import fetch_catalogue as fc  # noqa: E402

from vedic_astrology_core.mundane import registry as reg  # noqa: E402
from vedic_astrology_core.stats.manifest import file_sha256  # noqa: E402

COUNTRIES = REPO / "studies" / "mundane" / "data" / "countries.yaml"
OWNER_CHARTS = REPO / "studies" / "mundane" / "data" / "owner_charts.yaml"
SNAPSHOT_DIR = REPO / "data" / "snapshots"
OUT_DIR = REPO / "data" / "registry" / "mundane"
SEED_ISOS = ("IN", "NP")
MIN_MW = 6.0

#: Stable ids for the seeded candidates, keyed by the event text in countries.yaml.
CHART_IDS = {
    "Independence Act takes effect (midnight chart)": "in-1947-midnight",
    "Independence (K.N. Rao variant)": "in-1947-kn-rao",
    "Independence (noon chart)": "in-1947-noon",
    "Republic Day (constitution in force)": "in-1950-republic",
    "Abolition of the monarchy (republic declared)": "np-2008-republic",
    "Constitution of Nepal 2015 promulgated": "np-2015-constitution",
    "Republic declared (owner's Maitreya chart file)": "np-2008-republic-owner",
}
#: Place-text country names (USGS `place` is the nearest town, not the epicentre).
PLACE_COUNTRY = {
    "India": "IN",
    "Nepal": "NP",
    "Bhutan": "BT",
    "China": "CN",
    "Pakistan": "PK",
    "Myanmar": "MM",
    "Bangladesh": "BD",
    "Afghanistan": "AF",
}


def _kind_for(candidate: Dict[str, Any]) -> str:
    """Evidence kind for a seeded candidate. Nothing has been opened by a maintainer."""
    if candidate.get("time") in (None, ""):
        return "none"
    conf = candidate.get("confidence")
    return "secondary" if conf == "documented" else "convention"


def _clock(value: Any) -> Optional[str]:
    """Normalise a YAML time (str or sexagesimal int) to HH:MM:SS."""
    if value is None:
        return None
    if isinstance(value, int):  # YAML 1.1 sexagesimal: 00:01:00 -> 60
        return f"{value // 3600:02d}:{value % 3600 // 60:02d}:{value % 60:02d}"
    return str(value)


def build_charts(countries_path: Path = COUNTRIES) -> List[Dict[str, Any]]:
    """Return chart mappings (section 6.1) for the seed countries."""
    data = yaml.safe_load(countries_path.read_text(encoding="utf-8"))["countries"]
    out: List[Dict[str, Any]] = []
    for country in data:
        if country["iso"] not in SEED_ISOS:
            continue
        for cand in country["candidate_charts"]:
            cid = CHART_IDS.get(cand["event"])
            if cid is None:
                raise SystemExit(f"no chart_id assigned for {cand['event']!r}")
            clock = _clock(cand.get("time"))
            src = cand.get("source") or {}
            has_time = clock is not None
            out.append(
                {
                    "chart_id": cid,
                    "country_iso": country["iso"],
                    "event": cand["event"],
                    "founding": {
                        "date": str(cand["date"]),
                        "time": clock,
                        "time_zone": cand["time_zone"],
                        "place": cand["place"],
                        "lat": float(cand["lat"]),
                        "lon": float(cand["lon"]),
                    },
                    "time_evidence": {
                        "kind": _kind_for({**cand, "time": clock}),
                        # No source has been opened for the time: the coarsest claim
                        # that still allows grade C. H10 replaces this with evidence.
                        "stated_precision_minutes": 60 if has_time else None,
                        "source": {
                            "title": src.get("title"),
                            "url": src.get("url"),
                            "archive_url": None,
                            "accessed": None,
                            "quote": None,
                        },
                        "checked_by": None,
                        "checked_at": None,
                        "rectified": False,
                        "rectification_published": None,
                    },
                    "half_window_minutes": None,
                    "used_by": list(cand.get("used_by") or []),
                    "claimed_confidence": cand["confidence"],
                    "valid_from": str(cand["date"]),
                    "notes": " ".join(str(cand.get("notes") or "").split()),
                }
            )
    out.extend(build_owner_charts())
    return out


def build_owner_charts(path: Path = OWNER_CHARTS) -> List[Dict[str, Any]]:
    """Charts from the owner's chart files; the evidence kind is stated per chart, never checked."""
    if not path.exists():
        return []
    out: List[Dict[str, Any]] = []
    for cand in yaml.safe_load(path.read_text(encoding="utf-8"))["charts"]:
        cid = CHART_IDS.get(cand["event"])
        if cid is None or cid != cand["chart_id"]:
            raise SystemExit(f"no chart_id assigned for {cand['event']!r}")
        clock = _clock(cand.get("time"))
        out.append(
            {
                "chart_id": cid,
                "country_iso": cand["country_iso"],
                "event": cand["event"],
                "founding": {
                    "date": str(cand["date"]),
                    "time": clock,
                    "time_zone": cand["time_zone"],
                    "place": cand["place"],
                    "lat": float(cand["lat"]),
                    "lon": float(cand["lon"]),
                },
                "time_evidence": {
                    "kind": cand["evidence_kind"] if clock is not None else "none",
                    "stated_precision_minutes": cand.get("stated_precision_minutes"),
                    "source": {
                        "title": cand.get("source_title"),
                        "url": None,
                        "archive_url": None,
                        "accessed": None,
                        "quote": None,
                    },
                    "checked_by": None,
                    "checked_at": None,
                    "rectified": False,
                    "rectification_published": None,
                },
                "half_window_minutes": None,
                "used_by": list(cand.get("used_by") or []),
                "claimed_confidence": cand["confidence"],
                "valid_from": str(cand["date"]),
                "notes": " ".join(
                    f"Evidence origin: {cand.get('evidence_origin')}. {cand.get('notes') or ''}".split()
                ),
            }
        )
    return out


def _latest_usgs_snapshot(snapshot_dir: Path = SNAPSHOT_DIR) -> Path:
    files = sorted(snapshot_dir.glob("usgs_*.csv"))
    if not files:
        raise SystemExit(f"no usgs_*.csv snapshot in {snapshot_dir}")

    def created(p: Path) -> str:
        m = p.with_name(p.name + ".manifest.json")
        if not m.exists():
            m = p.with_suffix(".manifest.json")
        try:
            return json.loads(m.read_text())["created_utc"]
        except (OSError, KeyError, ValueError):
            return ""

    return max(files, key=lambda p: (created(p), p.name))


def _country_from_place(place: str) -> Optional[str]:
    m = re.search(r",\s*([^,]+)$", place or "")
    return PLACE_COUNTRY.get(m.group(1).strip()) if m else None


def build_events(snapshot: Path) -> List[Dict[str, Any]]:
    """Return event mappings (section 6.2): Himalayan Mw >= 6.0, raw and declustered flags."""
    hyp = fc.load_hypothesis()
    raw = pd.read_csv(snapshot)
    raw["time"] = pd.to_datetime(raw["time"], utc=True, format="ISO8601")
    cat = fc.homogenise_mw(raw, hyp["magnitude"]["rules"])
    comp = fc.completeness(cat, hyp["magnitude"])
    cat = cat[cat["mw"] >= comp["threshold"] - 1e-6].reset_index(drop=True)
    gk = decluster.gardner_knopoff(cat)
    nn, _fit = decluster.nearest_neighbour(cat)
    cat["gk"], cat["nn"] = gk.to_numpy(), nn.to_numpy()

    # Parent of each GK-removed event: the largest kept event whose window covers it.
    t = decluster.days_since_epoch(cat["time"])
    dist_w, time_w = decluster.gk_windows(cat["mw"].to_numpy(float))
    parents: Dict[int, Optional[str]] = {}
    for i in cat.index[~cat["gk"]]:
        best = None
        for j in cat.index[cat["gk"]]:
            if cat.at[j, "mw"] < cat.at[i, "mw"] or abs(t[j] - t[i]) > time_w[j]:
                continue
            d = float(
                decluster.haversine_km(
                    cat.at[j, "latitude"], cat.at[j, "longitude"],
                    cat.at[i, "latitude"], cat.at[i, "longitude"],
                )
            )
            if d <= dist_w[j] and (best is None or cat.at[j, "mw"] > cat.at[best, "mw"]):
                best = j
        parents[i] = f"usgs:{cat.at[best, 'id']}" if best is not None else None

    sha = file_sha256(snapshot)
    rule = (
        "USGS ComCat events inside the registered Himalayan-arc polygon, depth <= 70 km, "
        f"homogenised Mw >= {MIN_MW} (earthquake-himalaya-v2 hypothesis); inclusion "
        "does not depend on fame."
    )
    rows: List[Dict[str, Any]] = []
    big = cat[cat["mw"] >= MIN_MW - 1e-9].sort_values(["time", "id"])
    for _, r in big.iterrows():
        i = r.name
        rows.append(
            {
                "event_id": f"usgs:{r['id']}",
                "event_type": "earthquake",
                "subtype": None,
                "country_iso": _country_from_place(str(r["place"])),
                "time_utc": r["time"].strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
                "time_precision": "minute",
                "lat": round(float(r["latitude"]), 4),
                "lon": round(float(r["longitude"]), 4),
                "location_precision_km": None,
                "severity": {
                    "scale": "Mw",
                    "value": round(float(r["mw"]), 2),
                    "native_magnitude": float(r["mag"]),
                    "native_type": None if pd.isna(r["magType"]) else str(r["magType"]),
                },
                "cluster_id": None if r["gk"] else parents.get(i),
                "catalogue": {
                    "name": "USGS ComCat (Himalayan arc snapshot)",
                    "inclusion_rule": rule,
                    "snapshot_sha256": sha,
                },
                "exhaustive": True,
                "source_url": f"https://earthquake.usgs.gov/earthquakes/eventpage/{r['id']}",
                "archive_url": None,
                "reviewed_by": None,
                "reviewed_at": None,
                "flags": {
                    "raw": True,
                    "mainshock_gk": bool(r["gk"]),
                    "mainshock_nn": bool(r["nn"]),
                },
                "notes": (
                    "country_iso is read from the USGS place text (nearest town); "
                    "WP-60 replaces it with an epicentre lookup."
                ),
            }
        )
    return rows


def write_registries(snapshot: Path, out_dir: Path = OUT_DIR) -> Dict[str, Any]:
    """Write charts.yaml, events.jsonl and MANIFEST.json; return the manifest."""
    out_dir.mkdir(parents=True, exist_ok=True)
    charts = build_charts()
    events = build_events(snapshot)
    charts_file = out_dir / "charts.yaml"
    events_file = out_dir / "events.jsonl"
    header = (
        "# Country chart registry (ADR-006 section 6.1). Written by "
        "studies/mundane/scripts/build_registry.py.\n"
        "# The grade is computed by core/mundane/registry.py from time_evidence; it is not stored.\n"
    )
    charts_file.write_text(
        header + yaml.safe_dump(charts, sort_keys=False, allow_unicode=True, width=100),
        encoding="utf-8",
    )
    events_file.write_text(
        "".join(json.dumps(e, sort_keys=True, ensure_ascii=False) + "\n" for e in events),
        encoding="utf-8",
    )
    # Fail early if the contract is broken.
    reg.load_charts(charts_file)
    reg.load_events(events_file)
    manifest = {
        "inputs": {
            "countries_yaml_sha256": file_sha256(COUNTRIES),
            "owner_charts_yaml_sha256": file_sha256(OWNER_CHARTS),
            "usgs_snapshot": snapshot.name,
            "usgs_snapshot_sha256": file_sha256(snapshot),
        },
        "outputs": {
            "charts_sha256": file_sha256(charts_file),
            "events_sha256": file_sha256(events_file),
        },
        "counts": {
            "charts": len(charts),
            "events": len(events),
            "events_gk_mainshock": sum(e["flags"]["mainshock_gk"] for e in events),
            "events_nn_mainshock": sum(e["flags"]["mainshock_nn"] for e in events),
        },
    }
    (out_dir / "MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest


def main(argv=None) -> int:
    """Entry point."""
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--snapshot", type=Path, default=None)
    ap.add_argument("--out-dir", type=Path, default=OUT_DIR)
    args = ap.parse_args(argv)
    snap = args.snapshot or _latest_usgs_snapshot()
    manifest = write_registries(snap, args.out_dir)
    print(json.dumps(manifest["counts"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
