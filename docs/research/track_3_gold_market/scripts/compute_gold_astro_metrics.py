#!/usr/bin/env python3
"""Compute activation metrics for astrology principles vs gold return spikes."""
from datetime import timedelta
from pathlib import Path
import pandas as pd
import numpy as np
from scipy.stats import chi2

base = Path(__file__).resolve().parents[1]
data_dir = base / "data"

catalog_path = data_dir / "gold_astro_catalog.csv"
features_path = data_dir / "gold_astro_features.csv"
prices_path = data_dir / "gold_prices.csv"

for p in [catalog_path, features_path, prices_path]:
    if not p.exists():
        raise SystemExit(f"Missing {p}. Run generation scripts first.")

catalog = pd.read_csv(catalog_path)
feat = pd.read_csv(features_path)
feat["date"] = pd.to_datetime(feat["date"], errors="coerce")

prices = pd.read_csv(prices_path)
prices["date"] = pd.to_datetime(prices["date"], errors="coerce")
prices = prices.dropna(subset=["date"]).sort_values("date")
prices["close"] = pd.to_numeric(prices["close"], errors="coerce")
prices["log_returns"] = np.log(prices["close"]) - np.log(prices["close"].shift(1))
prices = prices.dropna(subset=["log_returns"])

# Define event days: top 5% absolute returns
thr = prices["log_returns"].abs().quantile(0.95)
price_events = set(prices.loc[prices["log_returns"].abs() >= thr, "date"].dt.date)

WINDOWS = [0,1,3,7,14,30]
window_sets = {}
for w in WINDOWS:
    days = set()
    for d in price_events:
        for delta in range(-w, w+1):
            days.add(d + timedelta(days=delta))
    window_sets[w] = days

window_sizes = {w: len(dayset) for w, dayset in window_sets.items()}

def chi_square_p(a, b, c, d):
    obs = np.array([a, b, c, d], dtype=float)
    if obs.sum() == 0:
        return 1.0
    row1 = a + b
    row2 = c + d
    col1 = a + c
    col2 = b + d
    expected = np.array([
        row1 * col1 / obs.sum(),
        row1 * col2 / obs.sum(),
        row2 * col1 / obs.sum(),
        row2 * col2 / obs.sum(),
    ])
    if np.any(expected == 0):
        return 1.0
    chi2_stat = ((obs - expected) ** 2 / expected).sum()
    return float(chi2.sf(chi2_stat, df=1))

# helpers

def ang_diff(a, b):
    diff = np.abs(a - b) % 360.0
    return np.minimum(diff, 360.0 - diff)

# Precompute arrays
feat_days = feat["date"].dt.date.values
total_days = len(feat_days)

# Precompute for phases
moon = feat["Moon_lon"].values
sun = feat["Sun_lon"].values
rahu = feat.get("Rahu_lon", pd.Series([np.nan]*len(feat))).values
ketu = feat.get("Ketu_lon", pd.Series([np.nan]*len(feat))).values

delta = (moon - sun) % 360.0
new_moon = (delta >= 345) | (delta <= 15)
full_moon = (delta >= 165) & (delta <= 195)
first_quarter = (delta >= 75) & (delta <= 105)
last_quarter = (delta >= 255) & (delta <= 285)

node_dist = np.minimum(ang_diff(moon, rahu), ang_diff(moon, ketu))
solar_eclipse = new_moon & (node_dist <= 12)
lunar_eclipse = full_moon & (node_dist <= 12)

results = []

for _, row in catalog.iterrows():
    cat = row["category"]
    active = None

    if cat in ["major_aspect", "minor_aspect", "vedic_malefic_aspect"]:
        p1 = row["p1"]; p2 = row["p2"]
        if f"{p1}_lon" not in feat.columns or f"{p2}_lon" not in feat.columns:
            active = np.zeros(len(feat), dtype=bool)
        else:
            target = row["aspect_deg"]; orb = row["orb"]
            diff = ang_diff(feat[f"{p1}_lon"].values, feat[f"{p2}_lon"].values)
            active = np.abs(diff - target) <= orb

    elif cat == "retrograde":
        p1 = row["p1"]
        col = f"{p1}_retrograde"
        active = feat[col].values.astype(bool) if col in feat.columns else np.zeros(len(feat), dtype=bool)

    elif cat == "combustion":
        p1 = row["p1"]
        col = f"{p1}_combust"
        active = feat[col].values.astype(bool) if col in feat.columns else np.zeros(len(feat), dtype=bool)

    elif cat == "ingress":
        p1 = row["p1"]
        col = f"{p1}_sign"
        active = feat[col].values == row["sign"] if col in feat.columns else np.zeros(len(feat), dtype=bool)

    elif cat == "lunar_phase":
        if row.get("phase") == "new":
            active = new_moon
        elif row.get("phase") == "full":
            active = full_moon
        elif row.get("phase") == "first_quarter":
            active = first_quarter
        else:
            active = last_quarter

    elif cat == "eclipse":
        if row.get("eclipse_type") == "solar":
            active = solar_eclipse
        else:
            active = lunar_eclipse

    elif cat == "nakshatra_lord":
        active = feat["nakshatra_lord"].values == row["lord"]

    elif cat == "dasha":
        col = "global_vimshottari_lord"
        active = feat[col].values == row["lord"] if col in feat.columns else np.zeros(len(feat), dtype=bool)

    elif cat == "compound":
        active = np.zeros(len(feat), dtype=bool)

    if active is None:
        continue

    total_active = int(active.sum())

    overlaps = {}
    pvals = {}
    for w, dayset in window_sets.items():
        overlap = int(sum(1 for i, d in enumerate(feat_days) if active[i] and d in dayset))
        overlaps[f"overlap_w{w}"] = overlap
        a = overlap
        b = total_active - a
        c = window_sizes[w] - a
        d = total_days - (a + b + c)
        pvals[f"pval_w{w}"] = chi_square_p(a, b, c, d)
        if w == 3:
            expected = (total_active * window_sizes[w]) / total_days if total_days else 0
            var = 0
            if total_days > 1:
                var = (total_active * window_sizes[w] * (total_days - total_active) * (total_days - window_sizes[w])) / (
                    total_days**2 * (total_days - 1)
                )
            z = (a - expected) / np.sqrt(var) if var > 0 else 0.0
            overlaps["expected_overlap_w3"] = expected
            overlaps["zscore_w3"] = z

    results.append({
        "combo_id": row["combo_id"],
        "category": cat,
        "total_active_days": total_active,
        **overlaps,
        **pvals,
    })

metrics = pd.DataFrame(results)

if "pval_w3" in metrics.columns:
    p = metrics["pval_w3"].fillna(1.0).values
    m = len(p)
    metrics["pval_w3_bonferroni"] = np.minimum(p * m, 1.0)
    order = np.argsort(p)
    q = np.empty_like(p)
    prev = 1.0
    for rank, idx in enumerate(order[::-1], start=1):
        qval = min(prev, p[idx] * m / (m - rank + 1))
        q[idx] = qval
        prev = qval
    metrics["pval_w3_fdr"] = q

out_path = data_dir / "gold_astro_metrics.csv"
metrics.to_csv(out_path, index=False)
print(f"Wrote {out_path} with {len(results)} rows")
