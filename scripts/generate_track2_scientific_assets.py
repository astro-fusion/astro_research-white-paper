"""Generate Track 2 (earthquake) figures from real catalogue data."""

import json
import os
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# cartopy removed to avoid dependency issues

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # repo root
from studies._paths import figures_dir, study_data_dir, study_dir  # noqa: E402

sys.path.insert(0, str(study_dir("earthquake") / "scripts"))

try:
    from earthquake_data_fetcher import EarthquakeDataFetcher
except ImportError:
    print("Error importing EarthquakeDataFetcher")


def generate_track2_assets(
    output_dir: str = str(figures_dir("earthquake")),
    simulation: bool = False,
):
    """
    Generate Scientific Assets for Track 2 (Earthquake Prediction):.

    1. Phase 1: Data Collection & Introspection (Map/Timeline of India-Nepal)
    2. With ``simulation=True`` only: SIMULATED illustrations of a stress
       index (sine plus noise). No real planetary stress index is computed
       here; the former "Planetary Stress Index (Model)" figures were
       withdrawn on 2026-11-08 (see CORRECTIONS.md).
    """
    os.makedirs(output_dir, exist_ok=True)

    # ==========================================
    # 1. Fetch Real Data (India-Nepal Focus)
    # ==========================================
    fetcher = EarthquakeDataFetcher(verbose=True)

    # India-Nepal Approximate Bounding Box
    # Lat: 20N to 35N
    # Lon: 75E to 90E
    # Period: 2015-2024 (Last 9 Years)
    # Mag: > 4.5 (To capture more events in this smaller region)

    print("Fetching India-Nepal Real Data...")
    try:
        raw_data = fetcher.fetch_earthquakes(
            start_date="2015-01-01",
            end_date="2024-01-01",
            min_magnitude=4.5,
            latitude_range=(20, 35),
            longitude_range=(75, 90),
            use_usgs_api=True,
        )
        data = fetcher.process_for_analysis(raw_data)

        # Save for report reference
        with open(study_data_dir("earthquake") / "india_nepal_data.json", "w") as f:
            json.dump(data, f, indent=2, default=str)

    except Exception as e:
        print(f"Fetch failed: {e}. No figures generated.")
        return

    df = pd.DataFrame(data)
    df["date"] = pd.to_datetime(df["date"])
    print(f"✅ Fetched {len(df)} events for India-Nepal region.")

    # ==========================================
    # 2. Phase 1 Asset: Seismic Intensity Map
    # ==========================================
    # Plotting magnitude vs time
    plt.figure(figsize=(10, 6))

    # Bubble chart: X=Time, Y=Magnitude, Size=Magnitude^2
    plt.scatter(
        df["date"],
        df["magnitude"],
        s=(df["magnitude"] ** 4) / 10,  # Size exaggerated for visual
        c=df["magnitude"],
        cmap="Reds",
        alpha=0.7,
        edgecolors="k",
    )

    plt.colorbar(label="Magnitude (Mw)")
    plt.title(
        "Phase 1: Seismic Activity in India-Nepal Region (2015-2024)\n"
        f"N={len(df)} Events (Mag > 4.5)",
        fontsize=14,
    )
    plt.ylabel("Magnitude")
    plt.grid(True, alpha=0.3)
    plt.savefig(f"{output_dir}/phase1_seismic_timeline.png", dpi=300)
    plt.close()

    print(f"Generated real-data figure in {output_dir}")

    if simulation:
        plot_simulated_stress_figures(df, output_dir)


SIMULATION_WATERMARK = "SIMULATED, NOT DATA"


def _watermark_simulated(fig):
    """Draw a large diagonal SIMULATED watermark across a figure."""
    fig.text(
        0.5,
        0.5,
        SIMULATION_WATERMARK,
        fontsize=40,
        color="red",
        alpha=0.25,
        ha="center",
        va="center",
        rotation=30,
    )


def plot_simulated_stress_figures(df: pd.DataFrame, output_dir: str):
    """Draw illustrative figures from a SIMULATED stress index (not data).

    The "Planetary Stress Index" here is a sine wave plus noise and the
    per-quake stress values are uniform random numbers. These are teaching
    illustrations only; they must never be presented as results. Outputs
    carry a SIMULATED_ filename prefix and a watermark (see CORRECTIONS.md).
    """
    import random

    dates = pd.date_range("2015-01-01", "2024-01-01", freq="W")
    stress_index = (
        50
        + 30 * np.sin(np.arange(len(dates)) / 20)
        + np.random.normal(0, 5, len(dates))
    )

    fig = plt.figure(figsize=(12, 6))
    plt.plot(
        dates,
        stress_index,
        color="purple",
        alpha=0.5,
        label="Simulated stress index (sine + noise)",
    )
    for _, row in df.iterrows():
        if row["magnitude"] >= 5.5:
            plt.axvline(row["date"], color="red", linestyle="--", alpha=0.6)
    plt.title("SIMULATED illustration: stress index vs. major quakes", fontsize=14)
    plt.ylabel("Simulated index")
    plt.legend()
    _watermark_simulated(fig)
    plt.savefig(f"{output_dir}/SIMULATED_phase2_astro_pattern_map.png", dpi=300)
    plt.close()

    quake_stress = [50 + random.uniform(-20, 20) for _ in range(len(df))]
    fig = plt.figure(figsize=(8, 8))
    plt.scatter(quake_stress, df["magnitude"], color="blue", alpha=0.6)
    plt.axhline(y=df["magnitude"].mean(), color="k", linestyle=":", label="Mean Mag")
    plt.axvline(x=50, color="k", linestyle=":", label="Mean Stress")
    plt.title("SIMULATED illustration: random index vs. magnitude", fontsize=14)
    plt.xlabel("Simulated index (uniform random)")
    plt.ylabel("Earthquake Magnitude")
    plt.grid(True, alpha=0.3)
    _watermark_simulated(fig)
    plt.savefig(f"{output_dir}/SIMULATED_phase3_validation_scatter.png", dpi=300)
    plt.close()
    print(f"Generated 2 SIMULATED illustration figures in {output_dir}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--simulation",
        action="store_true",
        help="Also draw SIMULATED illustration figures (watermarked, not data).",
    )
    args = parser.parse_args()
    generate_track2_assets(simulation=args.simulation)
