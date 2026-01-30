"""
Artifact Generation Controller
===============================

This script acts as the "Controller" in the MVC architecture.
It orchestrates the data flow:
1. Loads aligned data (Model)
2. Runs statistical tests (Model)
3. Generates tables and figures (View Components)
4. Saves them to 'reports/artifacts/' for Quarto consumption.
"""

import json
import logging
import os
import sys

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "src"))

from models.statistics import (
    calculate_molchan_trajectory,
    check_stationarity,
    run_granger_causality,
    run_lomb_scargle,
    run_monte_carlo_permutation_test,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Paths
PROCESSED_DATA_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "data",
    "processed",
    "aligned_planetary_data.csv",
)
ARTIFACTS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "reports", "artifacts"
)

# Ensure artifacts directory exists
if not os.path.exists(ARTIFACTS_DIR):
    os.makedirs(ARTIFACTS_DIR)


def generate_stationarity_table(df: pd.DataFrame):
    """Generates Unit Root Test Table."""
    logger.info("Generating Stationarity Table...")

    variables = ["Close"]
    # Add planetary variables (Cyclic/Sin/Cos)
    variables.extend(
        [c for c in df.columns if "_Sin" in c or "_Cos" in c][:4]
    )  # Limit to a few for brevity

    results = []

    # Text Gold separately (Log Returns)
    df["Gold_Log_Ret"] = np.log(df["Close"]).diff()
    results.append(check_stationarity(df["Gold_Log_Ret"], "Gold Log Returns"))

    # Test Planetary Variables (should be stationary/bounded)
    for var in variables:
        if var == "Close":
            continue
        results.append(check_stationarity(df[var], var))

    results_df = pd.DataFrame(results)
    output_path = os.path.join(ARTIFACTS_DIR, "tbl_stationarity.csv")
    results_df.to_csv(output_path, index=False)
    logger.info(f"Saved {output_path}")


def generate_periodogram_plot(df: pd.DataFrame):
    """Generates Lomb-Scargle Periodogram Figure."""
    logger.info("Generating Periodogram...")

    series = df.set_index("Date")["Gold_Log_Ret"].dropna()
    periods, power, fap = run_lomb_scargle(series, min_period=2, max_period=365)

    plt.figure(figsize=(10, 6))
    plt.plot(periods, power, color="black", linewidth=1)

    # Plot significance threshold
    plt.axhline(fap, color="red", linestyle="--", label="1% Significance (FAP)")

    plt.xscale("log")
    plt.xlabel("Period (Days)")
    plt.ylabel("Spectral Power Density")
    plt.title("Lomb-Scargle Periodogram of Gold Log-Returns")
    plt.legend()
    plt.grid(True, which="both", ls="-", alpha=0.2)

    output_path = os.path.join(ARTIFACTS_DIR, "fig_periodogram.pdf")
    plt.savefig(output_path, bbox_inches="tight")
    plt.close()
    logger.info(f"Saved {output_path}")


def generate_granger_stats(df: pd.DataFrame):
    """Generates Granger Causality Statistics JSON."""
    logger.info("Generating Granger Stats...")

    # Target: Gold Log Returns
    df["Gold_Log_Ret"] = np.log(df["Close"]).diff()

    # Planets to test (Mars, Saturn, Jupiter)
    planets = ["Mars", "Saturn", "Jupiter"]
    results = {}

    for planet in planets:
        # Predictors: Sine/Cosine components (Holistic cycle)
        predictors = [f"{planet}_Sin", f"{planet}_Cos"]

        # Check if columns exist
        if not all(col in df.columns for col in predictors):
            logger.warning(f"Predictors for {planet} not found.")
            continue

        # Run Test (Bonferroni n = number of planets tested = 3)
        res = run_granger_causality(
            df, "Gold_Log_Ret", predictors, maxlag=5, bonferroni_n=len(planets)
        )
        results[planet] = res

    output_path = os.path.join(ARTIFACTS_DIR, "stats_granger.json")
    with open(output_path, "w") as f:
        json.dump(results, f, indent=4)
    logger.info(f"Saved {output_path}")


def generate_molchan_plot(df: pd.DataFrame):
    """Generates Molchan Diagram."""
    logger.info("Generating Molchan Plot...")

    # Define "Event": Large absolute return (> 2 std dev)
    df["Gold_Log_Ret"] = np.log(df["Close"]).diff()
    threshold = df["Gold_Log_Ret"].std() * 2
    actuals = (df["Gold_Log_Ret"].abs() > threshold).astype(int)

    # Define "Prediction": Mars Speed (Stationary proxy for retrograde)
    # Using absolute speed change as proxy for "activity"
    predictions = df["Mars_Speed"].abs()

    # Calculate Trajectory
    thresholds = np.linspace(predictions.min(), predictions.max(), 50)
    molchan_df = calculate_molchan_trajectory(predictions, actuals, thresholds)

    plt.figure(figsize=(6, 6))
    plt.plot(
        molchan_df["Tau"],
        molchan_df["Nu"],
        marker="o",
        markersize=3,
        label="Mars Speed Model",
    )

    # Random diagonal
    plt.plot([0, 1], [1, 0], "k--", label="Random Guessing")

    plt.xlabel("Fraction of Time Alarm declared (τ)")
    plt.ylabel("Miss Rate (ν)")
    plt.title("Molchan Diagram: Mars vs Gold Volatility")
    plt.legend()
    plt.grid(True)
    plt.xlim(0, 1)
    plt.ylim(0, 1)

    output_path = os.path.join(ARTIFACTS_DIR, "fig_molchan.pdf")
    plt.savefig(output_path, bbox_inches="tight")
    plt.close()
    logger.info(f"Saved {output_path}")


def main():
    """Main execution flow."""
    logger.info("Loading processed data...")
    if not os.path.exists(PROCESSED_DATA_PATH):
        logger.warning(
            f"Data file not found: {PROCESSED_DATA_PATH}. Generating MOCK data for smoke testing."
        )

        # Ensure directory exists
        os.makedirs(os.path.dirname(PROCESSED_DATA_PATH), exist_ok=True)

        # Generate Mock Data
        dates = pd.date_range(start="2020-01-01", periods=1000, freq="D")
        mock_df = pd.DataFrame({"Date": dates})

        # Mock Gold Price (Random Walk)
        np.random.seed(42)
        returns = np.random.normal(0, 0.01, len(dates))
        price = 1000 * np.exp(np.cumsum(returns))
        mock_df["Close"] = price

        # Mock Planetary Data (Sine waves + Noise to avoid singular matrix)
        t = np.arange(len(dates))
        for planet, period in [("Mars", 687), ("Saturn", 10759), ("Jupiter", 4333)]:
            noise = np.random.normal(0, 0.001, len(dates))
            # Speed roughly sin wave
            mock_df[f"{planet}_Speed"] = np.sin(2 * np.pi * t / period) + noise
            # Cycles
            mock_df[f"{planet}_Sin"] = np.sin(2 * np.pi * t / period) + noise
            mock_df[f"{planet}_Cos"] = np.cos(2 * np.pi * t / period) + noise

        mock_df.to_csv(PROCESSED_DATA_PATH, index=False)
        logger.info(f"Saved mock data to {PROCESSED_DATA_PATH}")

    df = pd.read_csv(PROCESSED_DATA_PATH)
    df["Date"] = pd.to_datetime(df["Date"])

    # Generate all artifacts
    generate_stationarity_table(df)
    generate_periodogram_plot(df)
    generate_granger_stats(df)
    generate_molchan_plot(df)
    generate_monte_carlo_plot(df)

    logger.info("Artifact generation complete.")


def generate_monte_carlo_plot(df: pd.DataFrame):
    """Generates Monte Carlo Permutation Distribution Plot."""
    logger.info("Generating Monte Carlo Plot...")

    # Target: Gold Log Returns
    df["Gold_Log_Ret"] = np.log(df["Close"]).diff()

    # Test correlation with Mars Speed (as a proxy for activity)
    # or use Mars_Sin/Cos for a regression R^2 test.
    # Let's use Mars Speed for simplicity in this visualization to match the Molchan logic.
    target_col = "Gold_Log_Ret"
    exog_cols = ["Mars_Speed"]

    # Run Test (N=1000 for speed, usually 10000 for publication)
    res = run_monte_carlo_permutation_test(
        df, target_col, exog_cols, n_permutations=1000
    )

    actual_score = res["actual_score"]
    permuted_scores = res["permuted_scores"]
    p_value = res["p_value"]

    plt.figure(figsize=(10, 6))

    # Plot Histogram of random scores
    plt.hist(
        permuted_scores,
        bins=50,
        color="lightgray",
        edgecolor="gray",
        alpha=0.7,
        label="Random Permutations",
    )

    # Plot Actual Score
    plt.axvline(
        actual_score,
        color="red",
        linestyle="-",
        linewidth=2,
        label=f"Actual (p={p_value:.3f})",
    )

    plt.xlabel("R-Squared Correlation")
    plt.ylabel("Frequency")
    plt.title("Monte Carlo Permutation Test: Mars Speed vs Gold")
    plt.legend()
    plt.grid(True, alpha=0.3)

    output_path = os.path.join(ARTIFACTS_DIR, "fig_permutation_dist.pdf")
    plt.savefig(output_path, bbox_inches="tight")
    plt.close()
    logger.info(f"Saved {output_path}")


if __name__ == "__main__":
    main()
