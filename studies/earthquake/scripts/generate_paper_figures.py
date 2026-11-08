"""
Generate all figures for the Earthquake Research Paper (Track 2).

Outputs:
- figures/mars_saturn_strength.png
- figures/mars_ketu_separation.png
- figures/malefic_cluster_vs_earthquakes.png

The former "predicted vs actual" and "Monte Carlo" figures were drawn from
random numbers and have been withdrawn (see CORRECTIONS.md, 2026-11-08).
"""

import importlib
import os
import sys
from datetime import datetime

import matplotlib.pyplot as plt
import pandas as pd

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
)  # repo root
_paths = importlib.import_module("studies._paths")

EphemerisEngine = importlib.import_module(
    "vedic_astrology_core.astrology.ephemeris"
).EphemerisEngine
Planet = importlib.import_module("vedic_astrology_core.config.constants").Planet
GlobalShadbalaScorer = importlib.import_module(
    "vedic_astrology_core.dignity.global_scorer"
).GlobalShadbalaScorer

# Configuration
START_DATE = datetime(2020, 1, 1)
END_DATE = datetime(2025, 1, 1)
OUTPUT_DIR = str(_paths.figures_dir("earthquake"))
DATA_PATH = str(_paths.study_data_dir("earthquake") / "usgs_real_data_phase7.json")


def ensure_dir(d):
    """Create directory d if it does not exist."""
    if not os.path.exists(d):
        os.makedirs(d)


def load_earthquake_data():
    """Load the USGS earthquake catalog as a DataFrame."""
    if not os.path.exists(DATA_PATH):
        print(f"Warning: {DATA_PATH} not found. Returning empty DF.")
        return pd.DataFrame()

    # Check if JSON
    try:
        df = pd.read_json(DATA_PATH)
        if "time" in df.columns:
            df["datetime"] = pd.to_datetime(df["time"], format="mixed")
        elif "date" in df.columns:
            df["datetime"] = pd.to_datetime(df["date"], format="mixed")
        return df
    except Exception as e:
        print(f"Error loading earthquake data: {e}")
        return pd.DataFrame()


def generate_planetary_data():
    """Compute daily planetary strength data."""
    """Generate daily planetary data for the period."""
    print("Generating planetary data...")
    ee = EphemerisEngine()
    gs = GlobalShadbalaScorer(ephemeris=ee)

    dates = pd.date_range(START_DATE, END_DATE, freq="D")
    rows = []

    for d in dates:
        dt = datetime.combine(d.date(), datetime.min.time().replace(hour=12))
        jd = ee.datetime_to_julian_day(dt)
        scores = gs.calculate_global_power(jd)

        # Positions
        mars_pos = ee.get_planet_position(jd, Planet.MARS.value)["longitude"]
        ketu_pos = ee.get_planet_position(jd, Planet.KETU.value)["longitude"]
        saturn_pos = ee.get_planet_position(jd, Planet.SATURN.value)["longitude"]

        rows.append(
            {
                "date": d,
                "strength_MARS": scores.get("Mars", 0),
                "strength_SATURN": scores.get("Saturn", 0),
                "strength_RAHU": scores.get("Rahu", 0),
                "strength_SUN": scores.get("Sun", 0),
                "pos_MARS": mars_pos,
                "pos_KETU": ketu_pos,
                "pos_SATURN": saturn_pos,
            }
        )

    return pd.DataFrame(rows)


def plot_mars_saturn_strength(df, eq_df):
    """Plot Mars and Saturn strength against earthquakes."""
    print("Generating Figure 1: Mars & Saturn Strength...")
    plt.figure(figsize=(12, 6))
    plt.plot(
        df["date"], df["strength_MARS"], label="Mars Strength", color="red", alpha=0.8
    )
    plt.plot(
        df["date"],
        df["strength_SATURN"],
        label="Saturn Strength",
        color="blue",
        alpha=0.8,
    )

    # Overlay major earthquakes as vertical lines or scatter
    if not eq_df.empty:
        major_eq = eq_df[eq_df["magnitude"] >= 7.0]
        if not major_eq.empty:
            # Filter to plot range
            major_eq = major_eq[
                (major_eq["datetime"] >= START_DATE)
                & (major_eq["datetime"] <= END_DATE)
            ]
            plt.scatter(
                major_eq["datetime"],
                [150] * len(major_eq),
                color="black",
                marker="x",
                s=50,
                label="M7+ Quakes",
                zorder=5,
            )

    plt.title("Planetary Strength Variation (Mars & Saturn) 2020-2025")
    plt.ylabel("Shadbala Score")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.savefig(os.path.join(OUTPUT_DIR, "mars_saturn_strength.png"))
    plt.close()


def plot_mars_ketu_separation(df):
    """Plot Mars-Ketu angular separation."""
    print("Generating Figure 2: Mars-Ketu Separation...")

    # Calculate difference
    df["mars_ketu_diff"] = abs(df["pos_MARS"] - df["pos_KETU"])
    df["mars_ketu_diff"] = df["mars_ketu_diff"].apply(
        lambda x: 360 - x if x > 180 else x
    )

    plt.figure(figsize=(12, 5))
    plt.plot(df["date"], df["mars_ketu_diff"], label="Separation Angle", color="purple")

    # Highlight danger zone (< 15 deg)
    threshold = 15
    plt.axhline(threshold, color="red", linestyle="--", label="Danger Threshold (15°)")
    plt.fill_between(
        df["date"],
        0,
        df["mars_ketu_diff"],
        where=(df["mars_ketu_diff"] <= threshold),
        color="red",
        alpha=0.3,
        label="Angarak Yoga Period",
    )

    plt.title("Mars-Ketu Angular Separation (Angarak Yoga Windows)")
    plt.ylabel("Degrees")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.savefig(os.path.join(OUTPUT_DIR, "mars_ketu_separation.png"))
    plt.close()


def plot_malefic_cluster(df, eq_df):
    """Plot malefic cluster strength against earthquakes."""
    print("Generating Figure 3: Malefic Cluster Index vs Quakes...")

    # Create Index
    df["malefic_index"] = (
        df["strength_MARS"]
        + df["strength_SATURN"]
        + df["strength_RAHU"]
        + df["strength_SUN"]
    )

    # Aggregate quakes by month
    if not eq_df.empty:
        eq_df["month"] = eq_df["datetime"].dt.to_period("M")
        monthly_eq = eq_df.groupby("month").size()

        # Align timelines
        df["month"] = df["date"].dt.to_period("M")
        monthly_index = df.groupby("month")["malefic_index"].mean()

        common_idx = monthly_eq.index.intersection(monthly_index.index)

        fig, ax1 = plt.subplots(figsize=(12, 6))

        ax1.set_xlabel("Date")
        ax1.set_ylabel("Malefic Stress Index", color="tab:red")
        ax1.plot(
            common_idx.to_timestamp(),
            monthly_index[common_idx],
            color="tab:red",
            label="Cosmic Stress Index",
        )
        ax1.tick_params(axis="y", labelcolor="tab:red")

        ax2 = ax1.twinx()
        ax2.set_ylabel("Diff Earthquake Count (Monthly)", color="tab:blue")
        ax2.bar(
            common_idx.to_timestamp(),
            monthly_eq[common_idx],
            width=20,
            alpha=0.3,
            color="tab:blue",
            label="Earthquake Count",
        )
        ax2.tick_params(axis="y", labelcolor="tab:blue")

        plt.title("Cosmic Stress Index vs Global Seismicity (Monthly)")
        fig.tight_layout()
        plt.savefig(os.path.join(OUTPUT_DIR, "malefic_cluster_vs_earthquakes.png"))
        plt.close()
    else:
        print("Skipping Malefic Cluster plot (no EQ data)")


def main():
    """Generate all paper figures."""
    ensure_dir(OUTPUT_DIR)

    # Load Data
    eq_df = load_earthquake_data()
    df_astro = generate_planetary_data()

    # Generate Plots
    plot_mars_saturn_strength(df_astro, eq_df)
    plot_mars_ketu_separation(df_astro)
    plot_malefic_cluster(df_astro, eq_df)

    print("All figures generated successfully.")


if __name__ == "__main__":
    main()
