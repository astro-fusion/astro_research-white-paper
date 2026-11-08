#!/usr/bin/env python3
"""Fetch the pre-registered USGS catalogue and write a hashed snapshot.

Usage::

    python studies/earthquake/scripts/fetch_catalogue.py            # USGS FDSN
    python studies/earthquake/scripts/fetch_catalogue.py --offline  # tracked JSON

The query covers the bounding box of the region polygon in
``studies/earthquake/hypothesis.yaml``; events are then kept only if they lie
inside the polygon and above the depth limit. The result goes to
``data/snapshots/usgs_<sha12>.csv`` with ``usgs_<sha12>.csv.manifest.json``
beside it. ``--offline`` (or an unreachable service) uses the tracked
``studies/earthquake/data/india_nepal_data.json`` instead and says so.

The module also holds the catalogue helpers the pipeline uses: the polygon,
Mw homogenisation and the magnitude of completeness.
"""

import argparse
import hashlib
import io
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Dict, Optional, Tuple

import numpy as np
import pandas as pd
import yaml

REPO = Path(__file__).resolve().parents[3]
for p in (REPO, REPO / "libs"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from studies._paths import SNAPSHOT_ROOT, study_dir  # noqa: E402
from vedic_astrology_core.stats.manifest import write_manifest  # noqa: E402

STUDY = study_dir("earthquake")
HYPOTHESIS = STUDY / "hypothesis.yaml"
OFFLINE_JSON = STUDY / "data" / "india_nepal_data.json"
COLUMNS = ["time", "latitude", "longitude", "depth", "mag", "magType", "id"]
MW_TYPES = {"mww", "mwc", "mwb", "mwr", "mw", "mwp"}


def load_hypothesis(path: Path = HYPOTHESIS) -> Dict:
    """Return the pre-registration as a dict."""
    return yaml.safe_load(Path(path).read_text())


# --------------------------------------------------------------- region
def region_polygon(region: Dict) -> np.ndarray:
    """Return the closed (lon, lat) polygon built from the MFT trace offsets."""
    trace = np.asarray(region["mft_trace_lon_lat"], dtype=float)
    south = trace.copy()
    south[:, 1] -= float(region["south_offset_deg"])
    north = trace[::-1].copy()
    north[:, 1] += float(region["north_offset_deg"])
    poly = np.vstack([south, north, south[:1]])
    return poly


def in_polygon(lon, lat, polygon: np.ndarray) -> np.ndarray:
    """Return a boolean mask of points inside the polygon."""
    from matplotlib.path import Path as MplPath

    pts = np.column_stack([np.asarray(lon, float), np.asarray(lat, float)])
    return MplPath(polygon).contains_points(pts)


def bounding_box(polygon: np.ndarray, pad: float = 0.1) -> Tuple[float, ...]:
    """Return ``(min_lat, max_lat, min_lon, max_lon)`` padded by ``pad``."""
    return (
        float(polygon[:, 1].min() - pad),
        float(polygon[:, 1].max() + pad),
        float(polygon[:, 0].min() - pad),
        float(polygon[:, 0].max() + pad),
    )


# ------------------------------------------------------------ magnitude
def homogenise_mw(df: pd.DataFrame, rules: Dict) -> pd.DataFrame:
    """Add ``mw`` and ``mw_rule`` columns following the registered rules.

    Moment magnitudes are kept; mb and Ms are converted with Scordilis
    (2006); anything else is kept as reported with rule ``"as_reported"``.
    """
    out = df.copy()
    mtype = out["magType"].fillna("").str.lower()
    mag = out["mag"].astype(float)
    mw = mag.copy()
    rule = pd.Series("as_reported", index=out.index)
    is_mw = mtype.isin(MW_TYPES)
    rule[is_mw] = "moment"
    is_mb = mtype.str.startswith("mb") & ~mtype.str.startswith("mb_lg")
    r = rules["mb"]
    mw[is_mb] = r["slope"] * mag[is_mb] + r["intercept"]
    rule[is_mb] = "scordilis_mb"
    is_ms = mtype.str.startswith("ms")
    lo, hi = rules["ms_low"], rules["ms_high"]
    ms_hi = is_ms & (mag >= hi["valid"][0])
    ms_lo = is_ms & ~ms_hi
    mw[ms_lo] = lo["slope"] * mag[ms_lo] + lo["intercept"]
    mw[ms_hi] = hi["slope"] * mag[ms_hi] + hi["intercept"]
    rule[is_ms] = "scordilis_ms"
    out["mw"] = mw
    out["mw_rule"] = rule
    return out


def mc_maxc(mags, bin_width: float = 0.1, correction: float = 0.2) -> float:
    """Return Mc by maximum curvature plus ``correction``.

    The maximum-curvature estimate is the magnitude bin with the most events
    in the non-cumulative frequency-magnitude distribution.
    """
    m = np.asarray(mags, dtype=float)
    m = m[np.isfinite(m)]
    if len(m) == 0:
        raise ValueError("no magnitudes")
    bins = np.round(np.floor(m / bin_width + 1e-9) * bin_width, 6)
    values, counts = np.unique(bins, return_counts=True)
    return float(np.round(values[np.argmax(counts)] + correction, 6))


def completeness(df: pd.DataFrame, cfg: Dict, min_events: int = 50) -> Dict:
    """Return per-decade Mc and the registered analysis threshold (in Mw).

    Mc is estimated by maximum curvature + 0.2 on native mb in every decade
    with at least ``min_events`` mb events; the largest value is converted to
    Mw with the registered mb rule. Maximum curvature on the converted Mw is
    reported too (``mc_mw_scale_per_decade``) for comparison.
    """
    bw = float(cfg["bin_width"])
    rule = cfg["rules"]["mb"]
    years = pd.to_datetime(df["time"], utc=True).dt.year
    decades = (years // 10) * 10
    is_mb = df["magType"].fillna("").str.lower().eq("mb")
    mb_scale, mw_scale = {}, {}
    for dec in sorted(decades.unique()):
        sel = decades == dec
        if (sel & is_mb).sum() >= min_events:
            mb_scale[int(dec)] = mc_maxc(df.loc[sel & is_mb, "mag"], bw)
        if sel.sum() >= min_events:
            mw_scale[int(dec)] = mc_maxc(df.loc[sel, "mw"], bw)
    if not mb_scale:
        raise ValueError("no decade has enough mb events to estimate Mc")
    worst_mb = max(mb_scale.values())
    threshold = rule["slope"] * worst_mb + rule["intercept"]
    return {
        "mc_mb_per_decade": mb_scale,
        "mc_mb_max": worst_mb,
        "mc_mw_scale_per_decade": mw_scale,
        "threshold": max(4.0, threshold),
    }


# ---------------------------------------------------------------- fetch
def fetch_usgs(cat: Dict, bbox: Tuple[float, ...], timeout: int = 120) -> str:
    """Return the FDSN CSV text for the registered query and bounding box."""
    min_lat, max_lat, min_lon, max_lon = bbox
    params = {
        "format": "csv",
        "starttime": cat["start"],
        "endtime": cat["end"],
        "minlatitude": f"{min_lat:.2f}",
        "maxlatitude": f"{max_lat:.2f}",
        "minlongitude": f"{min_lon:.2f}",
        "maxlongitude": f"{max_lon:.2f}",
        "minmagnitude": cat["query_min_magnitude"],
        "eventtype": cat["event_type"],
        "orderby": "time-asc",
        "limit": 20000,
    }
    url = cat["url"] + "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=timeout) as resp:  # noqa: S310
        return resp.read().decode("utf-8")


def load_offline(path: Path = OFFLINE_JSON) -> pd.DataFrame:
    """Return the tracked India-Nepal JSON in the FDSN column schema."""
    rows = json.loads(Path(path).read_text())
    df = pd.DataFrame(rows)
    out = pd.DataFrame(
        {
            "time": pd.to_datetime(df["time"], utc=True, format="ISO8601").dt.strftime(
                "%Y-%m-%dT%H:%M:%S.%fZ"
            ),
            "latitude": df["latitude"],
            "longitude": df["longitude"],
            "depth": df["depth_km"],
            "mag": df["magnitude_raw"].fillna(df["magnitude"]),
            "magType": df["magnitude_type"],
            "id": df["usgs_url"].str.rsplit("/", n=1).str[-1],
        }
    )
    return out


def filter_region(df: pd.DataFrame, hyp: Dict) -> pd.DataFrame:
    """Keep earthquakes inside the polygon and above the depth limit."""
    poly = region_polygon(hyp["region"])
    keep = in_polygon(df["longitude"], df["latitude"], poly)
    keep &= df["depth"].astype(float) <= float(hyp["catalogue"]["max_depth_km"])
    if "type" in df.columns:
        keep &= df["type"].fillna("earthquake") == "earthquake"
    out = df.loc[keep].copy()
    out["time"] = pd.to_datetime(out["time"], utc=True, format="ISO8601")
    return out.sort_values("time").reset_index(drop=True)


def snapshot(
    offline: bool = False,
    hyp: Optional[Dict] = None,
    out_dir: Path = SNAPSHOT_ROOT,
) -> Tuple[Path, str]:
    """Fetch (or load offline), filter to the region and write the snapshot.

    Returns:
        ``(path, source)`` where source is "usgs_fdsn" or "offline_json".
    """
    hyp = hyp or load_hypothesis()
    source = "usgs_fdsn"
    if not offline:
        try:
            text = fetch_usgs(
                hyp["catalogue"], bounding_box(region_polygon(hyp["region"]))
            )
            raw = pd.read_csv(io.StringIO(text))
        except (urllib.error.URLError, OSError, TimeoutError) as exc:
            print(f"USGS service unreachable ({exc}); using offline JSON")
            offline = True
    if offline:
        source = "offline_json"
        raw = load_offline()
    df = filter_region(raw, hyp)
    df["time"] = df["time"].dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    payload = df.to_csv(index=False).encode("utf-8")
    digest = hashlib.sha256(payload).hexdigest()[:12]
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    prefix = "usgs" if source == "usgs_fdsn" else "offline"
    path = out_dir / f"{prefix}_{digest}.csv"
    path.write_bytes(payload)
    times = pd.to_datetime(df["time"], utc=True)
    write_manifest(
        path,
        inputs=[
            {
                "path": path,
                "row_count": int(len(df)),
                "date_range": [str(times.min()), str(times.max())],
            }
        ],
        repo_root=REPO,
        extra={
            "source": source,
            "query": hyp["catalogue"],
            "rows_before_polygon": int(len(raw)),
            "hypothesis_id": hyp["id"],
        },
    )
    return path, source


def main(argv=None) -> int:
    """Command-line entry point."""
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument(
        "--offline", action="store_true", help="use the tracked india_nepal_data.json"
    )
    args = ap.parse_args(argv)
    path, source = snapshot(offline=args.offline)
    print(f"source: {source}")
    print(f"snapshot: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
