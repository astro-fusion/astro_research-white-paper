"""Generate scientific assets for Track 1: Numerology vs Astrology.

Only the numerology step function (Phase 1) is computed from real rules. No
Shadbala series is computed here: the former "Astrology Shadbala (Mars)"
curves were a sine wave plus random noise and were withdrawn on 2026-11-08
(see CORRECTIONS.md). Pass ``--simulation`` to draw those curves as
watermarked illustrations with a ``SIMULATED_`` filename prefix.
"""

import argparse
import os
import sys
from datetime import datetime, timedelta

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from studies._paths import figures_dir  # noqa: E402

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


def compute_numerology_strength(start_date: datetime, end_date: datetime):
    """Return the daily Mars numerology strength step function."""
    num_rows = []
    current_day = start_date.date()
    while current_day <= end_date.date():
        # Mulanka = (Day Sum - 1) % 9 + 1
        day_sum = sum(int(d) for d in str(current_day.day))
        mulanka = (day_sum - 1) % 9 + 1

        # Strength mapping: Mulanka 9 (Mars) = 100, friends (1, 3, 5) = 75,
        # otherwise 40.
        mars_num_strength = (
            100 if mulanka == 9 else (75 if mulanka in [1, 3, 5] else 40)
        )
        num_rows.append(
            {
                "date": current_day,
                "mulanka": mulanka,
                "Mars_Num_Strength": mars_num_strength,
            }
        )
        current_day += timedelta(days=1)
    return pd.DataFrame(num_rows)


def simulate_mars_strength(start_date: datetime, end_date: datetime):
    """Return a SIMULATED hourly Mars strength series (sine plus noise).

    This is not Shadbala and not derived from any ephemeris.
    """
    rows = []
    current = start_date
    while current <= end_date:
        t_hour = (current - start_date).total_seconds() / 3600
        mars_strength = (
            50 + 40 * np.sin(t_hour / (24 * 60) * 2 * np.pi) + np.random.normal(0, 2)
        )
        rows.append({"time": current, "Mars": np.clip(mars_strength, 0, 100)})
        current += timedelta(hours=1)
    return pd.DataFrame(rows)


def plot_simulated_astrology_figures(df_num, start_date, end_date, output_dir):
    """Draw watermarked SIMULATED astrology curves (illustration only)."""
    df_astro = simulate_mars_strength(start_date, end_date)

    fig = plt.figure(figsize=(10, 5))
    plt.plot(
        df_astro["time"],
        df_astro["Mars"],
        color="blue",
        linewidth=2,
        label="Simulated Mars curve (sine + noise)",
    )
    plt.title("SIMULATED illustration: continuous oscillation\nJan 2024", fontsize=14)
    plt.ylabel("Simulated score (0-100)")
    plt.grid(True, alpha=0.3)
    plt.ylim(0, 110)
    plt.legend()
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter("%d-%b"))
    _watermark_simulated(fig)
    plt.savefig(f"{output_dir}/SIMULATED_phase2_astrology_curve.png", dpi=300)
    plt.close()

    fig = plt.figure(figsize=(10, 6))
    plt.plot(
        df_astro["time"],
        df_astro["Mars"],
        color="blue",
        alpha=0.6,
        linewidth=2,
        label="Simulated Mars curve (sine + noise)",
    )
    plt.step(
        df_num["date"],
        df_num["Mars_Num_Strength"],
        where="post",
        color="orange",
        linewidth=2,
        label="Numerology (Dig. Root)",
    )
    plt.title(
        "SIMULATED illustration: continuous vs. discrete systems (Mars)", fontsize=14
    )
    plt.ylabel("Score")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter("%d-%b"))
    _watermark_simulated(fig)
    plt.savefig(f"{output_dir}/SIMULATED_phase3_comparison_overlay.png", dpi=300)
    plt.close()
    print(f"Generated 2 SIMULATED illustration figures in {output_dir}")


def generate_scientific_assets(
    output_dir: str = str(figures_dir("numerology_vs_astrology")),
    simulation: bool = False,
):
    """Generate Track 1 figures for January 2024.

    Always: the numerology variation step function (Phase 1).
    With ``simulation=True`` only: watermarked SIMULATED astrology curves.
    """
    os.makedirs(output_dir, exist_ok=True)

    start_date = datetime(2024, 1, 1)
    end_date = datetime(2024, 2, 1)  # 31 Days
    print(f"Generating data for period: {start_date.date()} to {end_date.date()}")

    df_num = compute_numerology_strength(start_date, end_date)

    plt.figure(figsize=(10, 5))
    plt.step(
        df_num["date"],
        df_num["Mars_Num_Strength"],
        where="post",
        color="orange",
        linewidth=2,
        label="Numerology Strength (Mars)",
    )
    plt.title(
        "Phase 1: Numerology Variation (Discrete Step Function)\nJan 2024", fontsize=14
    )
    plt.ylabel("Strength Score (0-100)")
    plt.grid(True, alpha=0.3)
    plt.ylim(0, 110)
    plt.legend()
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter("%d-%b"))
    plt.savefig(f"{output_dir}/phase1_numerology_step.png", dpi=300)
    plt.close()
    print(f"Generated numerology figure in {output_dir}")

    if simulation:
        plot_simulated_astrology_figures(df_num, start_date, end_date, output_dir)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--simulation",
        action="store_true",
        help="Also draw SIMULATED illustration figures (watermarked, not data).",
    )
    args = parser.parse_args()
    generate_scientific_assets(simulation=args.simulation)
