"""
Generate High-Resolution Planetary Strength Curves.

This script generates a time-series of "Global Planetary Power" (Shadbala-lite)
at 2-hour intervals. This resolution captures fast-moving components like the Moon
and provides a smooth "Variation Curve" for correlation with seismic events.

Output:
    assets/data/planetary_strength_curves_2h.csv
"""

import sys
import os
import pandas as pd
from datetime import datetime, timedelta

# Ensure src is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../src')))

from vedic_astrology_core.time_series import compute_astrology_strength_series
from vedic_astrology_core.config.constants import Planet

def generate_curves(year: int = 2023):
    """
    Generate 2-hour resolution curves for a full year.
    """
    print(f"Generating 2-hour strength curves for {year}...")
    
    start_date = f"{year}-01-01"
    end_date = f"{year}-12-31"
    
    # We use step_hours=2.0 as requested
    df = compute_astrology_strength_series(
        start_date=start_date,
        end_date=end_date,
        step_hours=2.0
    )
    
    # Ensure asset directory exists
    output_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../assets/data'))
    os.makedirs(output_dir, exist_ok=True)
    
    output_path = os.path.join(output_dir, f"planetary_strength_curves_{year}_2h.csv")
    df.to_csv(output_path, index=False)
    
    print(f"✅ Generated {len(df)} data points (2-hr intervals).")
    print(f"✅ Saved to: {output_path}")
    
    # Basic Stats
    print("\nVariation Statistics:")
    print(df.describe())

if __name__ == "__main__":
    generate_curves(2023)  # Generate for the dataset year
