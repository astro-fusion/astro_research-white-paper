"""
Artifact Generation Controller.

===============================

This script acts as the "Controller" in the MVC architecture.
It orchestrates the data flow:
1. Loads aligned data (Model)
2. Runs statistical tests (Model)
3. Generates tables and figures (View Components)
4. Saves them to 'studies/gold_market/artifacts/' for Quarto consumption.
"""

import json
import logging
import os
import sys

# import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO)
sys.path.insert(0, os.path.join(_REPO, "libs"))

from studies._paths import PROCESSED_ROOT, artifacts_dir  # noqa: E402
from vedic_astrology_core.stats.granger import exog_granger  # noqa: E402
from vedic_astrology_core.stats.molchan import molchan_trajectory  # noqa: E402
from vedic_astrology_core.stats.multiplicity import adjust  # noqa: E402
from vedic_astrology_core.stats.nulls import make_rng  # noqa: E402
from vedic_astrology_core.stats.permutation import permutation_test  # noqa: E402
from vedic_astrology_core.stats.spectral import lomb_scargle_grid  # noqa: E402
from vedic_astrology_core.stats.stationarity import (  # noqa: E402
    adf_kpss,
    is_stationary,
)

SEED = 42


def check_stationarity(series: pd.Series, name: str) -> dict:
    """Return one stationarity-table row (ADF and KPSS, alpha 0.05)."""
    tests = adf_kpss(series)
    return {
        "Variable": name,
        "ADF Statistic": round(tests["adf_stat"], 4),
        "ADF p-value": round(tests["adf_p"], 4),
        "KPSS Statistic": round(tests["kpss_stat"], 4),
        "KPSS p-value": round(tests["kpss_p"], 4),
        "Stationary": "Yes" if is_stationary(tests) else "No",
    }


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Paths
PROCESSED_DATA_PATH = os.environ.get("ASTRO_PROCESSED_DATA_PATH") or str(
    PROCESSED_ROOT / "aligned_planetary_data.csv"
)
ARTIFACTS_DIR = str(artifacts_dir("gold_market"))  # honours ASTRO_ARTIFACTS_DIR

# Ensure artifacts directory exists
if not os.path.exists(ARTIFACTS_DIR):
    os.makedirs(ARTIFACTS_DIR)


def generate_stationarity_table(df: pd.DataFrame):
    """Generate Unit Root Test Table."""
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
    """Generate Lomb-Scargle Periodogram Figure."""
    logger.info("Generating Periodogram...")

    series = df.set_index("Date")["Gold_Log_Ret"].dropna()
    grid = lomb_scargle_grid(series, min_period=2, max_period=365)
    periods, power, fap = grid["period_days"], grid["power"], grid["fap_level_01"]

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
    """Generate Granger Causality Statistics JSON."""
    logger.info("Generating Granger Stats...")

    # Target: Gold Log Returns
    df["Gold_Log_Ret"] = np.log(df["Close"]).diff()

    # Planets to test (Mars, Saturn, Jupiter)
    planets = ["Mars", "Saturn", "Jupiter"]
    results = {}

    returns = df.set_index("Date")["Gold_Log_Ret"].dropna()
    for planet in planets:
        # Predictors: Sine/Cosine components, treated as exogenous regressors.
        predictors = [f"{planet}_Sin", f"{planet}_Cos"]

        # Check if columns exist
        if not all(col in df.columns for col in predictors):
            logger.warning(f"Predictors for {planet} not found.")
            continue

        # ADL with HAC errors, lag 1 fixed a priori, stationarity gate.
        res = exog_granger(returns, df.set_index("Date")[predictors],
                           lags=(1,), y_lags=1)
        results[planet] = {
            "Target": "Gold_Log_Ret",
            "Predictors": ", ".join(predictors),
            "Lags": res["lags"],
            "Transform": res["transform"],
            "F-Statistic": res.get("f_stat"),
            "p-value": res["p_value"],
        }

    # One Benjamini-Yekutieli family across the planets tested.
    tested = [k for k, v in results.items() if v["p-value"] is not None]
    if tested:
        q = adjust([results[k]["p-value"] for k in tested], "by")
        for k, qv in zip(tested, q):
            results[k]["q-value"] = float(qv)
            results[k]["Significant"] = "Yes" if qv < 0.05 else "No"
    for v in results.values():
        v.setdefault("q-value", None)
        v.setdefault("Significant", "No")

    output_path = os.path.join(ARTIFACTS_DIR, "stats_granger.json")
    with open(output_path, "w") as f:
        json.dump(results, f, indent=4)
    logger.info(f"Saved {output_path}")


def generate_molchan_plot(df: pd.DataFrame):
    """Generate Molchan Diagram."""
    logger.info("Generating Molchan Plot...")

    # Define "Event": Large absolute return (> 2 std dev)
    df["Gold_Log_Ret"] = np.log(df["Close"]).diff()
    threshold = df["Gold_Log_Ret"].std() * 2
    actuals = (df["Gold_Log_Ret"].abs() > threshold).astype(int)

    # Define "Prediction": Mars Speed (Stationary proxy for retrograde)
    # Using absolute speed change as proxy for "activity"
    predictions = df["Mars_Speed"].abs()

    # Calculate trajectory (tau = fraction of time under alarm, sorted ascending)
    thresholds = np.linspace(predictions.min(), predictions.max(), 50)
    event_bins = np.flatnonzero(actuals.to_numpy())
    molchan_df = molchan_trajectory(predictions.fillna(predictions.min()),
                                    event_bins, thresholds)

    plt.figure(figsize=(6, 6))
    plt.plot(
        molchan_df["tau"],
        molchan_df["nu"],
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


def generate_planetary_variation_plots(df: pd.DataFrame):
    """Generate Planetary Variation Plot (Speed, Motion)."""
    logger.info("Generating Planetary Variation Plots...")

    # 1. Mars Speed / Retrograde
    plt.figure(figsize=(12, 5))
    plt.plot(
        df["Date"], df["Mars_Speed"], color="#d62728", label="Mars Speed", linewidth=1
    )
    plt.axhline(0, color="black", linestyle="--", linewidth=0.8)
    # Highlight Retrograde (Speed < 0)
    plt.fill_between(
        df["Date"],
        df["Mars_Speed"],
        0,
        where=(df["Mars_Speed"] < 0),
        color="red",
        alpha=0.1,
        label="Retrograde",
    )
    plt.ylabel("Daily Motion (deg)")
    plt.title("Mars Planetary Motion & Retrograde Cycles (2020-2023)")
    plt.legend()
    plt.grid(True, alpha=0.3)

    output_path = os.path.join(ARTIFACTS_DIR, "fig_mars_variation.pdf")
    plt.savefig(output_path, bbox_inches="tight")
    plt.close()
    logger.info(f"Saved {output_path}")

    # 2. Multi-Planet Cycles (first 2 years to avoid clutter)
    subset = df[df["Date"] < df["Date"].min() + pd.Timedelta(days=730)]
    plt.figure(figsize=(12, 5))
    plt.plot(subset["Date"], subset["Jupiter_Sin"], label="Jupiter Cycle", alpha=0.8)
    plt.plot(subset["Date"], subset["Saturn_Sin"], label="Saturn Cycle", alpha=0.8)
    plt.plot(
        subset["Date"],
        subset["Mars_Sin"],
        label="Mars Cycle",
        alpha=0.6,
        linestyle="--",
    )

    plt.title("Comparative Planetary Cycles (Normalized Sine Components)")
    plt.ylabel("Cyclic Phase")
    plt.legend(loc="upper right")
    plt.grid(True, alpha=0.3)

    output_path = os.path.join(ARTIFACTS_DIR, "fig_multi_planet_cycles.pdf")
    plt.savefig(output_path, bbox_inches="tight")
    plt.close()
    logger.info(f"Saved {output_path}")


def main():
    """Main execution flow."""  # noqa: D401
    logger.info("Loading processed data...")
    if not os.path.exists(PROCESSED_DATA_PATH):
        # Never fall back to synthetic data: a placeholder series written to the
        # real data path was previously mistaken for market data (see
        # CORRECTIONS.md, 2026-11-08).
        logger.error(
            f"Processed data file not found: {PROCESSED_DATA_PATH}. "
            "Provide verified aligned market and ephemeris data, or set "
            "ASTRO_PROCESSED_DATA_PATH to its location."
        )
        sys.exit(1)

    df = pd.read_csv(PROCESSED_DATA_PATH)
    df["Date"] = pd.to_datetime(df["Date"])

    # Generate all artifacts
    generate_stationarity_table(df)
    generate_periodogram_plot(df)
    generate_granger_stats(df)
    generate_molchan_plot(df)
    generate_monte_carlo_plot(df)
    generate_planetary_variation_plots(df)

    logger.info("Artifact generation complete.")


def generate_monte_carlo_plot(df: pd.DataFrame):
    """Generate Monte Carlo Permutation Distribution Plot."""
    logger.info("Generating Monte Carlo Plot...")

    # Target: Gold Log Returns
    df["Gold_Log_Ret"] = np.log(df["Close"]).diff()

    # Test correlation with Mars Speed (as a proxy for activity)
    # or use Mars_Sin/Cos for a regression R^2 test.
    # Let's use Mars Speed for simplicity in this visualization to match the Molchan logic.  # noqa: E501
    target_col = "Gold_Log_Ret"
    exog_cols = ["Mars_Speed"]

    # Circular-shift null of the planetary series (keeps both series'
    # autocorrelation); statistic: R-squared of the simple regression.
    clean = df[[target_col] + exog_cols].dropna()
    x = clean[exog_cols[0]].to_numpy()
    y = clean[target_col].to_numpy()

    def r_squared(a, b):
        return float(np.corrcoef(a, b)[0, 1] ** 2)

    res = permutation_test(r_squared, x, y, rng=make_rng(SEED),
                           null="circular_shift", n_perm=1000,
                           min_shift=max(1, len(x) // 5), n_boot=0)
    actual_score = res.observed
    permuted_scores = res.null_stats
    p_value = res.p_value

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
    plt.title("Circular-shift Permutation Test: Mars Speed vs Gold")
    plt.legend()
    plt.grid(True, alpha=0.3)

    output_path = os.path.join(ARTIFACTS_DIR, "fig_permutation_dist.pdf")
    plt.savefig(output_path, bbox_inches="tight")
    plt.close()
    logger.info(f"Saved {output_path}")


if __name__ == "__main__":
    main()
