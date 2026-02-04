#!/usr/bin/env python3
"""Generate daily planetary features aligned to gold trading days."""
from datetime import datetime
from pathlib import Path
import sys
import pandas as pd
import numpy as np

repo_root = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(repo_root / "src"))

from vedic_astrology_core.astrology.ephemeris import EphemerisEngine
from vedic_astrology_core.astrology.chart import calculate_chart, get_nakshatra
from vedic_astrology_core.config.reference_charts import get_reference_chart
from vedic_astrology_core.dasha.vimshottari import compute_vimshottari_periods

# Paths
base = Path(__file__).resolve().parents[1]
data_dir = base / "data"
gold_path = data_dir / "gold_prices.csv"

if not gold_path.exists():
    raise SystemExit("Missing gold_prices.csv. Run fetch_gold_data.py first.")

# Load trading days
prices = pd.read_csv(gold_path)
prices["date"] = pd.to_datetime(prices["date"], errors="coerce")
prices = prices.dropna(subset=["date"]).sort_values("date")

engine = EphemerisEngine()
rows = []

# Global baseline dasha reference (Phase-1)
ref_chart = get_reference_chart("global_baseline_2000")
ref_birth_chart = calculate_chart(ref_chart.datetime, ref_chart.latitude, ref_chart.longitude)
ref_moon_long = ref_birth_chart.planets["Moon"]["longitude"]
ref_periods = compute_vimshottari_periods(ref_chart.datetime, ref_moon_long, total_years=120)

def get_dasha_lord(periods, target_dt, tzinfo):
    if target_dt.tzinfo is None:
        target_dt = target_dt.replace(tzinfo=tzinfo)
    for period in periods:
        if period.start <= target_dt < period.end:
            return period.lord
    return periods[-1].lord

for d in prices["date"].dt.date:
    dt = datetime(d.year, d.month, d.day, 12, 0, 0)
    chart = calculate_chart(dt, 0.0, 0.0)  # geocentric reference
    jd = engine.datetime_to_julian_day(dt)

    row = {"date": d.isoformat()}
    # Use EphemerisEngine for extended planets
    planet_names = [
        "Sun","Moon","Mars","Mercury","Jupiter","Venus","Saturn","Uranus","Neptune","Pluto","Rahu","Ketu"
    ]
    for pname in planet_names:
        try:
            pdata = engine.get_planet_position(jd, pname)
        except Exception:
            continue
        row[f"{pname}_lon"] = pdata.get("longitude")
        row[f"{pname}_retrograde"] = int(pdata.get("retrograde", False))
        row[f"{pname}_combust"] = int(pdata.get("combust", False))
        row[f"{pname}_sign"] = pdata.get("sign_name")

    # Panchanga-like lunar data
    moon_long = chart.planets["Moon"]["longitude"]
    sun_long = chart.planets["Sun"]["longitude"]
    delta = (moon_long - sun_long) % 360.0
    row["tithi"] = int(delta // 12.0) + 1
    row["nakshatra"] = get_nakshatra(moon_long).get("name")
    row["nakshatra_lord"] = get_nakshatra(moon_long).get("lord")
    row["global_vimshottari_lord"] = get_dasha_lord(ref_periods, dt, ref_chart.datetime.tzinfo)

    rows.append(row)

out_path = data_dir / "gold_astro_features.csv"
pd.DataFrame(rows).to_csv(out_path, index=False)
print(f"Wrote {out_path} with {len(rows)} rows")
