"""
Statistical Validation Suite.

This script implements rigorous statistical tests to validate (or invalidate)
the findings of the regression models.

Tests Implemented:
1. Schuster's Test for Periodicity:
   - Treats the 9-day Numerology Cycle as a phase circle (0 to 2*pi).
   - Calculates the vector sum of earthquake occurrences on this circle.
   - Large resultant vector R implies events are NOT random relative to the cycle.
   - Reference: Schuster (1897).

2. Monte Carlo Shuffle Test (The "Look-Elsewhere" Defense):
   - Randomly shuffles the earthquake time series 1000 times.
   - Re-runs the Negative Binomial Regression for each shuffle.
   - Compares the "Real" AIC improvement against the distribution of "Random" AIC improvements.
   - If Real Delta-AIC is not in the top 5% (p < 0.05) of random shuffles, the result is noise.
"""

import pandas as pd
import numpy as np
import statsmodels.api as sm
import statsmodels.formula.api as smf
import matplotlib.pyplot as plt
import json
import os
import sys
from tqdm import tqdm

def run_validation(matrix_path: str = "regression_matrix.csv", n_shuffles: int = 1000):
    """
    Run validation tests on the regression matrix.
    
    Args:
        matrix_path: Path to daily CSV.
        n_shuffles: Number of Monte Carlo iterations.
    """
    if not os.path.exists(matrix_path):
        print(f"Matrix file {matrix_path} not found.")
        return

    df = pd.read_csv(matrix_path)
    print(f"Loaded {len(df)} days of data for validation.")
    
    # Pre-calculate seasonality features
    df['date'] = pd.to_datetime(df['date'])
    df['doy'] = df['date'].dt.dayofyear
    df['year_index'] = df['date'].dt.year - df['date'].dt.year.min()
    df['sin_doy'] = np.sin(2 * np.pi * df['doy'] / 365.25)
    df['cos_doy'] = np.cos(2 * np.pi * df['doy'] / 365.25)
    
    # ---------------------------------------------------------
    # 1. Schuster's Test for Periodicity (9-Day Cycle)
    # ---------------------------------------------------------
    print("\n" + "="*40)
    print("TEST 1: SCHUSTER'S TEST (9-Day Cycle)")
    print("="*40)
    
    # Filter for days with earthquakes (magnitude >= 5.0)
    # Weighted by event count? Or just events? 
    # Standard Schuster uses discrete events. We will expand the counts.
    events_phases = []
    for _, row in df.iterrows():
        count = int(row['eq_count_m5'])
        udn = row['udn']
        # Phase: Day 1 = 0, Day 9 = 2*pi * 8/9 (start at 0)
        # Actually mapping 1->0, 2->1/9... 9->8/9
        # Angle theta = 2 * pi * (udn - 1) / 9
        theta = 2 * np.pi * (udn - 1) / 9.0
        events_phases.extend([theta] * count)
        
    N = len(events_phases)
    print(f"Analyzing {N} discrete seismic events.")
    
    if N > 0:
        C_sum = sum(np.cos(theta) for theta in events_phases)
        S_sum = sum(np.sin(theta) for theta in events_phases)
        R_squared = C_sum**2 + S_sum**2
        R = np.sqrt(R_squared)
        
        # Schuster's Probability (p-value under null hypothesis of randomness)
        # P = exp(-R^2 / N)
        p_schuster = np.exp(-R_squared / N)
        
        print(f"Resultant Vector R: {R:.2f}")
        print(f"Schuster's p-value: {p_schuster:.5e}")
        
        if p_schuster < 0.05:
            print(">> SIGNIFICANT periodicity detected in 9-day cycle!")
        else:
            print(">> No significant periodicity detected (Null Hypothesis holds).")
    else:
        p_schuster = 1.0
        print("No events to analyze.")

    # ---------------------------------------------------------
    # 2. Monte Carlo Shuffle Test (AIC Significance)
    # ---------------------------------------------------------
    print("\n" + "="*40)
    print(f"TEST 2: MONTE CARLO SHUFFLE ({n_shuffles} iterations)")
    print("="*40)
    
    # Real Model Delta AIC
    baseline_formula = "eq_count_m5 ~ year_index + sin_doy + cos_doy"
    research_formula = (
        "eq_count_m5 ~ year_index + sin_doy + cos_doy + "
        "C(udn) + mars_score + saturn_score"
    )
    
    try:
        real_baseline = smf.glm(formula=baseline_formula, data=df, family=sm.families.Poisson()).fit()
        real_research = smf.glm(formula=research_formula, data=df, family=sm.families.NegativeBinomial(alpha=1.0)).fit()
        real_delta_aic = real_baseline.aic - real_research.aic
        print(f"Real Delta AIC: {real_delta_aic:.4f}")
    except Exception as e:
        print(f"Validation failed: Could not train real models ({e})")
        return

    random_deltas = []
    
    # Shuffle Loop
    # We shuffle the TARGET variable (earthquake counts) relative to the PREDICTORS (Planets/Numbers)
    # This preserves the auto-correlation of planets but breaks the link to earthquakes.
    target_series = df['eq_count_m5'].values.copy()
    
    for i in tqdm(range(n_shuffles)):
        np.random.shuffle(target_series)
        df['shuffled_count'] = target_series
        
        try:
            # Re-train
            # Note: Baseline must also be re-trained on shuffled data because Year/Seasonality correlation changes
            # Wait, Year/Seasonality are predictors. If we shuffle count, we break Year trend too.
            # That's fair for Null Hypothesis: "Earthquakes are random time-independent processes" (mostly).
            # But technically we want to preserve seasonality in the null? 
            # Standard MC usually just breaks the link we care about.
            
            base_shuf = smf.glm(
                formula="shuffled_count ~ year_index + sin_doy + cos_doy",
                data=df,
                family=sm.families.Poisson()
            ).fit(disp=0) # Suppress convergence warnings
            
            res_shuf = smf.glm(
                formula="shuffled_count ~ year_index + sin_doy + cos_doy + C(udn) + mars_score + saturn_score",
                data=df,
                family=sm.families.NegativeBinomial(alpha=1.0)
            ).fit(disp=0)
            
            delta = base_shuf.aic - res_shuf.aic
            random_deltas.append(delta)
            
        except:
            continue
            
    random_deltas = np.array(random_deltas)
    
    # Calculate P-value
    # P = (Number of Random Deltas >= Real Delta) / Total Shuffles
    n_better = np.sum(random_deltas >= real_delta_aic)
    p_monte_carlo = (n_better + 1) / (len(random_deltas) + 1) # Add 1 for the real observation
    
    print(f"\nMonte Carlo p-value: {p_monte_carlo:.5f}")
    print(f"Checking if Real Delta ({real_delta_aic:.2f}) > 95% of Random noise")
    
    percentile_95 = np.percentile(random_deltas, 95)
    print(f"95th Percentile of Random Noise: {percentile_95:.2f}")
    
    result = "FAIL"
    if real_delta_aic > percentile_95:
        result = "PASS"
        print(">> VALIDATION SUCCESS: The signal is statistically distinguishable from noise.")
    else:
        print(">> VALIDATION FAIL: The signal is indistinguishable from random chance.")

    # Save Report
    report = {
        "schuster_p_value": p_schuster,
        "monte_carlo_p_value": p_monte_carlo,
        "real_delta_aic": real_delta_aic,
        "p95_random_delta": percentile_95,
        "validation_result": result
    }
    
    with open("validation_report.json", "w") as f:
        json.dump(report, f, indent=2)
        
    print("\nSaved validation_report.json")
    
    # Optional: Plot Histogram
    try:
        plt.figure(figsize=(10, 6))
        plt.hist(random_deltas, bins=30, alpha=0.7, color='gray', label='Random Shuffles')
        plt.axvline(real_delta_aic, color='red', linestyle='dashed', linewidth=2, label='Real Data')
        plt.title(f"Monte Carlo Validation (N={n_shuffles})")
        plt.xlabel("Delta AIC (Baseline - Research)")
        plt.ylabel("Frequency")
        plt.legend()
        plt.savefig("monte_carlo_distribution.png")
        print("Saved monte_carlo_distribution.png")
    except:
        pass

if __name__ == "__main__":
    run_validation()
