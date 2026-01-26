"""
Superposed Epoch Analysis (SEA).

Statistical validation tool for the Research Pipeline.
"Stacks" the timelines of the largest earthquakes to detect common precursors.
"""

import pandas as pd
import matplotlib.pyplot as plt
import sys
import os
from pathlib import Path

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent.parent / "src"))

def perform_sea_analysis(matrix_path: str = "regression_matrix.csv", output_dir: str = "sea_plots"):
    """
    Perform Superposed Epoch Analysis.
    
    Args:
        matrix_path: Path to daily regression matrix CSV
        output_dir: Directory to save plots
    """
    if not os.path.exists(matrix_path):
        print(f"Matrix file {matrix_path} not found. Run build_regression_matrix.py first.")
        return

    df = pd.read_csv(matrix_path)
    df['date'] = pd.to_datetime(df['date'])
    
    # 1. Identify Key Events (Epochs)
    # Filter for significant earthquakes in the matrix
    # Note: Mock data might be sparse, so we take top 10 events for safety
    threshold_mag = 5.0
    epochs = df[df['max_magnitude'] >= threshold_mag].sort_values('max_magnitude', ascending=False).head(100)
    
    print(f"Found {len(epochs)} epoch events (Mag >= {threshold_mag})")
    
    if len(epochs) == 0:
        print("No events found for SEA.")
        return
        
    # 2. Define Window
    window_days = 10
    window_range = range(-window_days, window_days + 1)
    
    # 3. Stack Data
    # We want valid indices (ensure window doesn't go out of bounds)
    stacked_udn = {d: [] for d in window_range}
    stacked_mars = {d: [] for d in window_range}
    
    for _, event in epochs.iterrows():
        event_date = event['date']
        
        # Get slice
        for delta in window_range:
            target_date = event_date + pd.Timedelta(days=delta)
            
            # Find row in full df
            row = df[df['date'] == target_date]
            
            if not row.empty:
                val = row.iloc[0]
                stacked_udn[delta].append(val['udn'])
                stacked_mars[delta].append(val['mars_score'])
                
    # 4. Aggregate
    sea_results = []
    for delta in window_range:
        udn_vals = stacked_udn[delta]
        mars_vals = stacked_mars[delta]
        
        if udn_vals:
            sea_results.append({
                "delta": delta,
                "mean_udn": sum(udn_vals) / len(udn_vals),
                "mean_mars": sum(mars_vals) / len(mars_vals),
                "count": len(udn_vals)
            })
            
    sea_df = pd.DataFrame(sea_results)
    
    # 5. Visualize
    os.makedirs(output_dir, exist_ok=True)
    
    # Plot UDN
    plt.figure(figsize=(10, 6))
    plt.plot(sea_df['delta'], sea_df['mean_udn'], marker='o', label='Mean UDN')
    plt.axvline(0, color='r', linestyle='--', label='Earthquake Day')
    plt.title(f"Superposed Epoch Analysis: UDN (N={len(epochs)})")
    plt.xlabel("Days from Event")
    plt.ylabel("Mean Universal Day Number")
    plt.legend()
    plt.grid(True)
    plt.savefig(f"{output_dir}/sea_udn.png")
    print(f"✅ Saved SEA plot to {output_dir}/sea_udn.png")
    
    # Plot Mars
    plt.figure(figsize=(10, 6))
    plt.plot(sea_df['delta'], sea_df['mean_mars'], marker='s', color='orange', label='Mean Mars Score')
    plt.axvline(0, color='r', linestyle='--', label='Earthquake Day')
    plt.title(f"Superposed Epoch Analysis: Mars Strength (N={len(epochs)})")
    plt.xlabel("Days from Event")
    plt.ylabel("Global Shadbala Score")
    plt.legend()
    plt.grid(True)
    plt.savefig(f"{output_dir}/sea_mars.png")
    print(f"✅ Saved SEA plot to {output_dir}/sea_mars.png")

if __name__ == "__main__":
    perform_sea_analysis()
