"""
Build Regression Matrix.

Generates the daily time-series dataset for the Astro-Numerology Research Pipeline.
Integrates:
- Earthquake Counts (Daily, Magnitude Thresholded)
- Numerology Features (UDN, Master Numbers)
- Astrology Features (Global Shadbala, Moon Phase)

Output: CSV file ready for statistical modeling.
"""

import pandas as pd
import numpy as np
import json
from datetime import date, timedelta, datetime
import sys
import os
from pathlib import Path

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent.parent / "src"))

from vedic_numerology.engine import NumerologyEngine
from vedic_astrology_core.dignity.global_scorer import GlobalShadbalaScorer
from vedic_astrology_core.astrology.ephemeris import EphemerisEngine
from earthquake_data_fetcher import EarthquakeDataFetcher


def build_matrix(
    start_year: int = 2020,
    end_year: int = 2023,
    output_path: str = "regression_matrix.csv",
):
    """
    Build the regression matrix.

    Args:
        start_year: Start year (inclusive)
        end_year: End year (inclusive)
        output_path: Path to save CSV
    """
    print(f"Building Regression Matrix ({start_year}-{end_year})...")

    # Initialize Engines
    num_engine = NumerologyEngine()
    eph_engine = EphemerisEngine()
    shadbala_scorer = GlobalShadbalaScorer(ephemeris=eph_engine)
    eq_fetcher = EarthquakeDataFetcher(
        use_sample_data=True, verbose=False
    )  # Use mock/sample for demo, real in prod

    # 1. Fetch Earthquakes (Prefer Real Data for Phase 7)
    start_date_str = f"{start_year}-01-01"
    end_date_str = f"{end_year}-12-31"

    # Check for Real Data File first
    real_data_path = (
        Path(__file__).parent.parent.parent / "data" / "usgs_real_data_phase7.json"
    )

    if real_data_path.exists():
        print(f"Loading REAL earthquake data from {real_data_path}")
        with open(real_data_path, "r") as f:
            # The file contains the processed list directly
            eq_list = json.load(f)
            # Ensure date range filter matches requested year
            # (The file might contain 2020-2023, but we might only want a subset if specified)
    else:
        print("⚠️ Real data not found. Falling back to mock/sample data.")
        eq_data_raw = eq_fetcher.fetch_earthquakes(start_date_str, end_date_str)
        eq_list = eq_fetcher.process_for_analysis(eq_data_raw)

    print(f"Loaded {len(eq_list)} earthquakes for processing.")

    # Convert to DataFrame
    eq_df = pd.DataFrame(eq_list)
    eq_df["date"] = pd.to_datetime(eq_df["date"]).dt.date

    # 2. Iterate Daily
    start_date = date(start_year, 1, 1)
    end_date = date(end_year, 12, 31)
    delta = end_date - start_date

    rows = []

    for i in range(delta.days + 1):
        current_date = start_date + timedelta(days=i)

        # --- Numerology Features ---
        udn = num_engine.calculate_universal_day_number(
            current_date, preserve_master=True
        )
        uyn = num_engine.calculate_universal_year_number(
            current_date.year, preserve_master=True
        )

        # --- Astrology Features ---
        # Calculate at 00:00 UTC
        dt = datetime(current_date.year, current_date.month, current_date.day)
        jd = eph_engine.datetime_to_julian_day(dt)

        scores = shadbala_scorer.calculate_global_power(jd)

        # --- Earthquake Target ---
        # Count events on this day with Mag >= 5.0
        daily_eqs = eq_df[eq_df["date"] == current_date]
        count_all = len(daily_eqs)
        count_m5 = len(daily_eqs[daily_eqs["magnitude"] >= 5.0])
        max_mag = daily_eqs["magnitude"].max() if count_all > 0 else 0

        row = {
            "date": current_date,
            "udn": udn,
            "uyn": uyn,
            "is_master_day": udn in [11, 22, 33],
            "eq_count_all": count_all,
            "eq_count_m5": count_m5,
            "max_magnitude": max_mag,
            "sun_score": scores.get("Sun", 0),
            "moon_score": scores.get("Moon", 0),
            "mars_score": scores.get("Mars", 0),
            "mercury_score": scores.get("Mercury", 0),
            "jupiter_score": scores.get("Jupiter", 0),
            "venus_score": scores.get("Venus", 0),
            "saturn_score": scores.get("Saturn", 0),
        }
        rows.append(row)

        if i % 100 == 0:
            print(f"Processed {current_date}")

    # 3. Save
    final_df = pd.DataFrame(rows)
    final_df.to_csv(output_path, index=False)
    print(f"✅ Saved regression matrix to {output_path}")
    print(final_df.head())


if __name__ == "__main__":
    build_matrix()
