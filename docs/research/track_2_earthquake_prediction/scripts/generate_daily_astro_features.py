#!/usr/bin/env python3
"""
Generate daily astrology base features for mundane analysis.
"""
from datetime import datetime, timedelta
from pathlib import Path
import sys
import pandas as pd

repo_root = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(repo_root / "src"))

from vedic_astrology_core.astrology.chart import calculate_chart, get_nakshatra
from vedic_astrology_core.astrology.ephemeris import EphemerisEngine
from vedic_astrology_core.config.constants import Planet
from vedic_astrology_core.config.reference_charts import get_reference_chart
from vedic_astrology_core.dasha.vimshottari import (
    compute_vimshottari_periods,
    compute_vimshottari_nested_periods,
    get_vimshottari_chain_at,
)
from vedic_astrology_core.time_series import TimeSeriesConfig, compute_astrology_strength_series

# Config
START = datetime(2015, 1, 1, 12, 0, 0)
END = datetime(2024, 1, 1, 12, 0, 0)
LAT = 28.6
LON = 77.1

# Output path
out_dir = Path(__file__).resolve().parents[1] / "data"
out_dir.mkdir(parents=True, exist_ok=True)
base_out = out_dir / "daily_astro_base.csv"

# Helper: tithi, karana, yoga
TITHI_DEG = 12.0
YOGA_DEG = 13.333333333333334

KARANA_NAMES = [
    "Bava", "Balava", "Kaulava", "Taitila", "Gara", "Vanija", "Vishti",
    "Shakuni", "Chatushpada", "Naga", "Kimstughna",
]

# Daily iteration
rows = []
cur = START
engine = EphemerisEngine()

# Reference charts for Phase-2 mundane dasha overlay (India + Nepal)
india_chart = get_reference_chart("india_independence")
nepal_chart = get_reference_chart("nepal_constitution_2015")

india_birth = calculate_chart(india_chart.datetime, india_chart.latitude, india_chart.longitude)
nepal_birth = calculate_chart(nepal_chart.datetime, nepal_chart.latitude, nepal_chart.longitude)

india_moon_long = india_birth.planets["Moon"]["longitude"]
nepal_moon_long = nepal_birth.planets["Moon"]["longitude"]

india_periods = compute_vimshottari_periods(india_chart.datetime, india_moon_long, total_years=120)
nepal_periods = compute_vimshottari_periods(nepal_chart.datetime, nepal_moon_long, total_years=120)

india_nested = compute_vimshottari_nested_periods(india_chart.datetime, india_moon_long, depth=2, total_years=120)
nepal_nested = compute_vimshottari_nested_periods(nepal_chart.datetime, nepal_moon_long, depth=2, total_years=120)

def get_dasha_lord(periods, target_dt, tzinfo):
    if target_dt.tzinfo is None:
        target_dt = target_dt.replace(tzinfo=tzinfo)
    for period in periods:
        if period.start <= target_dt < period.end:
            return period.lord
    return periods[-1].lord

def get_dasha_chain(nested_periods, target_dt, tzinfo):
    if target_dt.tzinfo is None:
        target_dt = target_dt.replace(tzinfo=tzinfo)
    return get_vimshottari_chain_at(target_dt, nested_periods)

while cur <= END:
    chart = calculate_chart(cur, LAT, LON)
    jd = engine.datetime_to_julian_day(cur)

    # Planetary positions
    planet_data = {}
    for pname, pdata in chart.planets.items():
        planet_data[pname] = {
            "longitude": pdata.get("longitude"),
            "retrograde": bool(pdata.get("retrograde", False)),
            "combust": bool(pdata.get("combust", False)),
            "sign_name": pdata.get("sign_name"),
        }

    sun_long = planet_data["Sun"]["longitude"]
    moon_long = planet_data["Moon"]["longitude"]

    # Panchanga elements
    delta = (moon_long - sun_long) % 360.0
    tithi = int(delta // TITHI_DEG) + 1
    karana_index = int(delta // 6.0) + 1  # 1..60
    yoga = int(((sun_long + moon_long) % 360.0) // YOGA_DEG) + 1

    nak = get_nakshatra(moon_long)

    # House placement
    house_map = {p: chart.get_planet_in_house(p) for p in chart.planets.keys()}

    row = {
        "date": cur.date().isoformat(),
        "datetime": cur.isoformat(),
        "tithi": tithi,
        "karana_index": karana_index,
        "karana_name": KARANA_NAMES[(karana_index - 1) % len(KARANA_NAMES)],
        "yoga": yoga,
        "nakshatra": nak.get("name"),
        "nakshatra_index": nak.get("index"),
        "nakshatra_lord": nak.get("lord"),
        "india_vimshottari_lord": get_dasha_lord(india_periods, cur, india_chart.datetime.tzinfo),
        "nepal_vimshottari_lord": get_dasha_lord(nepal_periods, cur, nepal_chart.datetime.tzinfo),
    }

    india_chain = get_dasha_chain(india_nested, cur, india_chart.datetime.tzinfo)
    nepal_chain = get_dasha_chain(nepal_nested, cur, nepal_chart.datetime.tzinfo)
    row["india_vimshottari_sublord"] = india_chain[1] if len(india_chain) > 1 else india_chain[0]
    row["nepal_vimshottari_sublord"] = nepal_chain[1] if len(nepal_chain) > 1 else nepal_chain[0]

    for pname, pdata in planet_data.items():
        row[f"{pname}_lon"] = pdata["longitude"]
        row[f"{pname}_retrograde"] = int(pdata["retrograde"])
        row[f"{pname}_combust"] = int(pdata["combust"])
        row[f"{pname}_sign"] = pdata["sign_name"]
        row[f"{pname}_house"] = house_map.get(pname)

    rows.append(row)
    cur += timedelta(days=1)

# Shadbala (global power)
strength_df = compute_astrology_strength_series(
    START.date(), END.date(), config=TimeSeriesConfig(latitude=LAT, longitude=LON)
)

base_df = pd.DataFrame(rows)
base_df = base_df.merge(strength_df, left_on="date", right_on="date", how="left")
base_df.to_csv(base_out, index=False)
print(f"Wrote {base_out} with {len(base_df)} rows")

# Export deeper dasha periods (up to pratyantar) for offline analysis
def export_nested_periods(periods, path):
    out = []
    for p in periods:
        out.append(
            {
                "level": p["level"],
                "lords": "-".join(p["lords"]),
                "start": p["start"].isoformat(),
                "end": p["end"].isoformat(),
                "years": p["years"],
            }
        )
    pd.DataFrame(out).to_csv(path, index=False)

india_nested_depth3 = compute_vimshottari_nested_periods(india_chart.datetime, india_moon_long, depth=3, total_years=120)
nepal_nested_depth3 = compute_vimshottari_nested_periods(nepal_chart.datetime, nepal_moon_long, depth=3, total_years=120)

export_nested_periods(india_nested_depth3, out_dir / "india_dasha_periods.csv")
export_nested_periods(nepal_nested_depth3, out_dir / "nepal_dasha_periods.csv")
