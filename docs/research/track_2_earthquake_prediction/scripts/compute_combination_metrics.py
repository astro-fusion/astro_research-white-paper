#!/usr/bin/env python3
"""Compute activation frequency and earthquake overlap for all combinations."""
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
import numpy as np

# Paths
root = Path(__file__).resolve().parents[1]
data_dir = root / "data"
base_path = data_dir / "daily_astro_base.csv"
catalog_path = data_dir / "combination_catalog.csv"
quakes_path = root / "india_nepal_data.json"

if not base_path.exists():
    raise SystemExit(f"Missing base features: {base_path}. Run generate_daily_astro_features.py")
if not catalog_path.exists():
    raise SystemExit(f"Missing catalog: {catalog_path}. Run generate_combination_catalog.py")

base = pd.read_csv(base_path)
base["date"] = pd.to_datetime(base["date"], format="mixed", errors="coerce")

catalog = pd.read_csv(catalog_path)

# Earthquake dates
quakes = pd.read_json(quakes_path)
quakes["date"] = pd.to_datetime(quakes["date"], format="mixed", errors="coerce")

# Precompute quake windows
WINDOWS = [0, 1, 3, 7, 14, 30]
window_sets = {}
for w in WINDOWS:
    days = set()
    for d in quakes["date"].dt.date:
        for delta in range(-w, w + 1):
            days.add(d + timedelta(days=delta))
    window_sets[w] = days

# Helper: angular distance

def ang_diff(a, b):
    diff = np.abs(a - b) % 360.0
    return np.minimum(diff, 360.0 - diff)

# Precompute arrays
base_days = base["date"].dt.date.values

# Precompute syzygy and eclipse flags
moon = base["Moon_lon"].values
sun = base["Sun_lon"].values
rahu = base["Rahu_lon"].values
ketu = base["Ketu_lon"].values

# tithi-based syzygy
syzygy_new = base["tithi"].values == 30
syzygy_full = base["tithi"].values == 15

# eclipse proxy: syzygy + node proximity within 12 deg
node_dist = np.minimum(ang_diff(moon, rahu), ang_diff(moon, ketu))
solar_eclipse = syzygy_new & (node_dist <= 12)
lunar_eclipse = syzygy_full & (node_dist <= 12)

# Precompute malefic conjunction flag (orb <=3)
MALEFICS = ["Mars", "Saturn", "Rahu", "Ketu"]
malefic_pairs = []
for i, p1 in enumerate(MALEFICS):
    for p2 in MALEFICS[i+1:]:
        malefic_pairs.append((p1, p2))

malefic_conj = np.zeros(len(base), dtype=bool)
for p1, p2 in malefic_pairs:
    malefic_conj |= ang_diff(base[f"{p1}_lon"].values, base[f"{p2}_lon"].values) <= 3

# Evaluate combinations
results = []
for _, row in catalog.iterrows():
    cat = row["category"]
    active = None

    if cat in ["aspects", "malefic_aspects"]:
        p1 = row["p1"]; p2 = row["p2"]
        target = row["aspect_deg"]; orb = row["orb"]
        diff = ang_diff(base[f"{p1}_lon"].values, base[f"{p2}_lon"].values)
        active = np.abs(diff - target) <= orb

    elif cat == "graha_yuddha":
        p1 = row["p1"]; p2 = row["p2"]
        diff = ang_diff(base[f"{p1}_lon"].values, base[f"{p2}_lon"].values)
        active = diff <= row["orb"]

    elif cat == "combustion":
        p1 = row["p1"]
        active = base[f"{p1}_combust"].values.astype(bool)

    elif cat == "retrograde":
        p1 = row["p1"]
        active = base[f"{p1}_retrograde"].values.astype(bool)

    elif cat == "shadbala":
        p1 = row["p1"].upper()
        col = f"astrology_{p1}"
        if col in base.columns:
            vals = base[col].values
            if row["band"] == "low":
                active = vals <= 33
            elif row["band"] == "medium":
                active = (vals > 33) & (vals <= 66)
            else:
                active = vals > 66
        else:
            active = np.zeros(len(base), dtype=bool)

    elif cat == "house":
        p1 = row["p1"]
        active = base[f"{p1}_house"].values == row["house"]

    elif cat == "sign":
        p1 = row["p1"]
        active = base[f"{p1}_sign"].values == row["sign"]

    elif cat == "nakshatra":
        active = base["nakshatra_lord"].values == row["p1"]

    elif cat == "tithi":
        active = base["tithi"].values == row["tithi"]

    elif cat == "karana":
        active = base["karana_name"].values == row["karana"]

    elif cat == "yoga":
        active = base["yoga"].values == row["yoga"]

    elif cat == "syzygy":
        if row.get("phase") == "new":
            active = syzygy_new
        else:
            active = syzygy_full

    elif cat == "eclipse":
        if row.get("eclipse_type") == "solar":
            active = solar_eclipse
        else:
            active = lunar_eclipse

    elif cat == "compound":
        # malefic conjunction during eclipse window
        active = malefic_conj & (solar_eclipse | lunar_eclipse)

    if active is None:
        continue

    total_active = int(active.sum())

    # Window overlaps
    overlaps = {}
    for w, dayset in window_sets.items():
        overlap = int(sum(1 for i, d in enumerate(base_days) if active[i] and d in dayset))
        overlaps[f"overlap_w{w}"] = overlap

    results.append({
        "combo_id": row["combo_id"],
        "category": cat,
        "total_active_days": total_active,
        **overlaps,
    })

metrics = pd.DataFrame(results)
metrics_path = data_dir / "combination_metrics.csv"
metrics.to_csv(metrics_path, index=False)
print(f"Wrote {metrics_path} with {len(metrics)} rows")
