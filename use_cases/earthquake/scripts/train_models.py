"""
Train Statistical Models.

This script implements the core hypothesis testing engine for the Research Pipeline.
It trains two types of Generalized Linear Models (GLM):

1. Baseline Model (Null Hypothesis):
   - Assumes earthquakes follow a Poisson process with Seasonality + Trend.
   - Formula: count ~ Year + sin(2π*day/365) + cos(2π*day/365)

2. Research Model (Negative Binomial):
   - Tests if Astrology/Numerology adds predictive power.
   - Handles Overdispersion (Clustering/Aftershocks) better than Poisson.
   - Formula: count ~ Baseline + C(universal_day_number) + global_shadbala_scores...

Output: Summary of regression coefficients and AIC/BIC comparison.
"""

import pandas as pd
import numpy as np
import statsmodels.api as sm
import statsmodels.formula.api as smf
import sys
import os
import json
from pathlib import Path


def train_models(matrix_path: str = "regression_matrix.csv", target_mag: float = 5.0):
    """
    Train GLMs on the regression matrix.

    Args:
        matrix_path: Path to daily CSV.
        target_mag: Minimum magnitude threshold used for counts (meta-data only here).
    """
    if not os.path.exists(matrix_path):
        print(f"Matrix file {matrix_path} not found.")
        return

    df = pd.read_csv(matrix_path)
    # Ensure date is datetime
    df["date"] = pd.to_datetime(df["date"])

    # Feature Engineering for Baseline
    # Add Day of Year (DOY) for seasonality
    df["doy"] = df["date"].dt.dayofyear
    df["year_index"] = df["date"].dt.year - df["date"].dt.year.min()

    # Harmonic Seasonality (Annual Cycle)
    df["sin_doy"] = np.sin(2 * np.pi * df["doy"] / 365.25)
    df["cos_doy"] = np.cos(2 * np.pi * df["doy"] / 365.25)

    print(f"Training models on {len(df)} days. Target: eq_count_m5")

    # --- 1. Baseline Model (Poisson) ---
    # Hypothesis: Random process + Seasonal Weather/Tidal stress + Catalog improvement trend
    baseline_formula = "eq_count_m5 ~ year_index + sin_doy + cos_doy"

    try:
        baseline_model = smf.glm(
            formula=baseline_formula, data=df, family=sm.families.Poisson()
        ).fit()

        print("\n" + "=" * 40)
        print("BASELINE MODEL (Poisson)")
        print("=" * 40)
        print(baseline_model.summary().tables[0])  # Print summary header
        print(f"AIC: {baseline_model.aic:.2f}")
    except Exception as e:
        print(f"Baseline training failed: {e}")
        return

    # --- 2. Research Model (Negative Binomial) ---
    # Hypothesis: Astro/Numerology adds signal.
    # We use Negative Binomial to handle overdispersion (Variance > Mean),
    # which is typical for earthquake clusters.

    # Predictors:
    # - C(udn): Categorical Universal Day Number (is Day 8 differnet from Day 1?)
    # - Mars Score: Global Strength of Mars (Energy/Violence archetype)
    # - Saturn Score: Global Strength of Saturn (Structure/Tectonic archetype)
    # - Retrograde status is baked into the scores.

    research_formula = (
        "eq_count_m5 ~ year_index + sin_doy + cos_doy + "
        "C(udn) + mars_score + saturn_score + sun_score + moon_score"
    )

    try:
        # Note: statsmodels NegativeBinomial family defaults to alpha=1 (geometric).
        # ideally we estimate alpha, but fixed alpha is often sufficient for comparison.
        research_model = smf.glm(
            formula=research_formula,
            data=df,
            family=sm.families.NegativeBinomial(alpha=1.0),
        ).fit()

        print("\n" + "=" * 40)
        print("RESEARCH MODEL (Negative Binomial)")
        print("=" * 40)
        # Print coefficients for our variables of interest
        print(research_model.summary())
        print(f"AIC: {research_model.aic:.2f}")

    except Exception as e:
        print(f"Research model training failed: {e}")
        return

    # --- 3. Comparison ---
    print("\n" + "=" * 40)
    print("MODEL COMPARISON")
    print("=" * 40)
    delta_aic = baseline_model.aic - research_model.aic
    print(f"Baseline AIC: {baseline_model.aic:.2f}")
    print(f"Research AIC: {research_model.aic:.2f}")
    print(f"Delta AIC:    {delta_aic:.2f}")

    if delta_aic > 2:
        print("Result: Research Model is statistically superior.")
    elif delta_aic < -2:
        print("Result: Baseline Model is superior (Research adds noise).")
    else:
        print("Result: Models are statistically indistinguishable.")

    # Save Results
    results = {
        "baseline_aic": baseline_model.aic,
        "research_aic": research_model.aic,
        "delta_aic": delta_aic,
        "significant_features": [],
    }

    # Check p-values < 0.05
    pvals = research_model.pvalues
    for feature, p in pvals.items():
        if p < 0.05:
            results["significant_features"].append(
                {
                    "feature": feature,
                    "p_value": p,
                    "coefficient": research_model.params[feature],
                }
            )

    with open("model_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print("\nSaved full results to model_results.json")


if __name__ == "__main__":
    train_models()
