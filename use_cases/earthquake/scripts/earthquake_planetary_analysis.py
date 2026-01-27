"""
Earthquake-Planetary Correlation Analysis Framework

Data-driven approach to analyze if certain planetary combinations
(e.g., Mangal-Ketu conjunction) correlate with earthquake events.

Part of the multi-use-case validation system for planetary influence analysis.
"""

import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import os
import sys

# Ensure src is in path to import vedic_astrology_core
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../src')))

from vedic_astrology_core.astrology.ephemeris import EphemerisEngine


class EarthquakeAstrologicalAnalysis:
    """
    Analyze correlation between planetary positions/combinations and earthquake events.

    Use Cases:
    - Mangal-Ketu conjunction → Earthquakes?
    - Saturn in certain positions → Earthquakes?
    - Multiple planet conjunctions → Earthquakes?
    - Planetary transits → Seismic activity?
    """

    def __init__(self, earthquake_data_file: Optional[str] = None):
        """Initialize earthquake analysis framework."""
        self.earthquakes = self._load_earthquake_data(earthquake_data_file)
        self.planetary_data = None
        self.correlation_results = {}

        # Define planetary combinations to test
        self.COMBINATIONS_TO_TEST = {
            "mangal_ketu": {
                "planets": ["MARS", "KETU"],
                "type": "conjunction",
                "description": "Mars-Ketu conjunction (Mars + South Node)",
            },
            "mangal_saturn": {
                "planets": ["MARS", "SATURN"],
                "type": "conjunction",
                "description": "Mars-Saturn conjunction",
            },
            "rahu_ketu": {
                "planets": ["RAHU", "KETU"],
                "type": "opposition",
                "description": "Rahu-Ketu axis (always opposite)",
            },
            "saturn_outer": {
                "planets": ["SATURN", "RAHU", "KETU"],
                "type": "any_two",
                "description": "Saturn with any outer planet",
            },
            "mars_activation": {
                "planets": ["MARS"],
                "type": "strength_trigger",
                "description": "Mars in high strength positions",
            },
            "malefic_cluster": {
                "planets": ["MARS", "SATURN", "RAHU"],
                "type": "clustering",
                "description": "Cluster of malefic planets",
            },
        }

    def _load_earthquake_data(self, filename: Optional[str]) -> pd.DataFrame:
        """
        Load earthquake data from CSV, JSON.
        
        Expected format:
        date,time,latitude,longitude,magnitude,depth_km,location
        OR JSON list of objects.
        """
        if not filename or not os.path.exists(filename):
            raise FileNotFoundError(
                "CRITICAL: Real earthquake data is required for production reports. "
                "No mock data allowed. Please provide a valid 'usgs_real_data_phase7.json' "
                "or other valid dataset."
            )

        if filename.endswith('.json'):
            df = pd.read_json(filename)
            # Ensure datetime format matches analysis expectations
            if 'time' in df.columns:
                 # Fetcher saves 'time' as ISO string or timestamp
                # Use format='mixed' to handle both with and without microseconds
                df['datetime'] = pd.to_datetime(df['time'], format='mixed')
            elif 'date' in df.columns:
                df['datetime'] = pd.to_datetime(df['date'], format='mixed')
        else:
            df = pd.read_csv(filename)
            df['datetime'] = pd.to_datetime(df['date'] + ' ' + df['time'].astype(str))
            
        return df

    def generate_planetary_data(self, start_date: datetime, 
                               end_date: datetime, 
                               frequency: str = 'daily') -> pd.DataFrame:
        """
        Generate REAL planetary position/strength data using Swiss Ephemeris.
        
        Args:
            start_date: Start of analysis period
            end_date: End of analysis period
            frequency: 'daily', 'weekly', 'monthly'

        Returns:
            DataFrame with planetary positions
        """
        print(f"Generating planetary data from {start_date.date()} to {end_date.date()}...")
        
        # Initialize Ephemeris Engine
        try:
            ephemeris = EphemerisEngine()
        except ImportError as e:
            print(f"Error initializing EphemerisEngine: {e}")
            print("Please ensure pyswisseph is installed.")
            return pd.DataFrame()

        if frequency == 'daily':
            dates = pd.date_range(start_date, end_date, freq='D')
        elif frequency == 'weekly':
            dates = pd.date_range(start_date, end_date, freq='W')
        else:
            dates = pd.date_range(start_date, end_date, freq='MS')
        
        rows = []
        
        for date_val in dates:
            # Calculate at Noon to be consistent
            dt = datetime.combine(date_val.date(), datetime.min.time().replace(hour=12))
            
            # Get Julian Day
            jd = ephemeris.datetime_to_julian_day(dt)
            
            # Get all positions
            positions = ephemeris.get_all_planet_positions(jd)
            
            row = {'datetime': date_val}
            
            for planet, data in positions.items():
                # Store longitude (0-360)
                p_name = planet.upper()
                row[f'{p_name}_position'] = data['longitude']
                row[f'{p_name}_speed'] = data['longitude_speed']
                row[f'{p_name}_strength'] = 50.0 # Placeholder
            
            rows.append(row)
        
        self.planetary_data = pd.DataFrame(rows)
        return self.planetary_data

    def identify_planetary_conjunction(
        self, planet1: str, planet2: str, tolerance_deg: float = 8.0
    ) -> List[Tuple]:
        """
        Identify when two planets are in conjunction (close proximity).
        """
        if self.planetary_data is None:
            return []

        pos1 = self.planetary_data[f"{planet1}_position"].values
        pos2 = self.planetary_data[f"{planet2}_position"].values
        dates = self.planetary_data["datetime"].values

        conjunctions = []

        for i in range(len(pos1)):
            diff = abs(pos1[i] - pos2[i])
            if diff > 180:
                diff = 360 - diff

            if diff <= tolerance_deg:
                conjunctions.append((dates[i], diff))

        return conjunctions

    def analyze_conjunction_earthquake_correlation(
        self, planet1: str, planet2: str, window_days: int = 30
    ) -> Dict:
        """
        Analyze if earthquakes are more likely within N days of a conjunction.
        """
        conjunctions = self.identify_planetary_conjunction(planet1, planet2)
        if not conjunctions:
            return {"status": "no_conjunctions_found", "details": {}}

        conjunction_dates = [c[0] for c in conjunctions]
        earthquakes_near_conjunction = 0
        earthquakes_far_from_conjunction = 0
        total_earthquake_days = 0

        for eq_date in self.earthquakes["datetime"].values:
            near_conjunction = False
            for conj_date in conjunction_dates:
                conj_datetime = pd.Timestamp(conj_date)
                eq_datetime = pd.Timestamp(eq_date)
                days_diff = abs((eq_datetime - conj_datetime).days)

                if days_diff <= window_days:
                    earthquakes_near_conjunction += 1
                    near_conjunction = True
                    break

            if not near_conjunction:
                earthquakes_far_from_conjunction += 1

            total_earthquake_days += 1

        total_period_days = (
            self.earthquakes["datetime"].max() - self.earthquakes["datetime"].min()
        ).days

        expected_earthquakes_in_window = (
            len(self.earthquakes)
            * (len(conjunction_dates) * window_days * 2)
            / total_period_days
        )

        chi_square = (
            (earthquakes_near_conjunction - expected_earthquakes_in_window) ** 2
        ) / (expected_earthquakes_in_window + 1)

        return {
            "conjunction": f"{planet1}-{planet2}",
            "conjunctions_found": len(conjunctions),
            "conjunction_dates": [
                pd.Timestamp(c[0]).strftime("%Y-%m-%d") for c in conjunctions[:5]
            ],
            "earthquakes_near_conjunction": earthquakes_near_conjunction,
            "earthquakes_far_from_conjunction": earthquakes_far_from_conjunction,
            "expected_earthquakes": round(expected_earthquakes_in_window, 2),
            "ratio_near_vs_expected": round(
                earthquakes_near_conjunction / max(expected_earthquakes_in_window, 1), 2
            ),
            "chi_square_statistic": round(chi_square, 4),
            "window_days": window_days,
            "total_earthquakes": len(self.earthquakes),
            "analysis_period_days": total_period_days,
        }

    def analyze_planetary_strength_trigger(
        self, planet: str, strength_threshold: float = 75.0
    ) -> Dict:
        """
        Analyze if earthquakes are more likely when a planet is in high strength.
        """
        if self.planetary_data is None:
            return {"status": "no_planetary_data"}

        high_strength_mask = (
            self.planetary_data[f"{planet}_strength"] >= strength_threshold
        )
        high_strength_dates = self.planetary_data[high_strength_mask]["datetime"].values

        if len(high_strength_dates) == 0:
            return {"status": "no_high_strength_periods"}

        earthquakes_during_high_strength = 0
        earthquakes_during_low_strength = 0

        for eq_date in self.earthquakes["datetime"].values:
            eq_dt = pd.Timestamp(eq_date)
            closest_idx = (self.planetary_data["datetime"] - eq_dt).abs().argmin()
            is_high_strength = high_strength_mask.iloc[closest_idx]

            if is_high_strength:
                earthquakes_during_high_strength += 1
            else:
                earthquakes_during_low_strength += 1

        total_high_strength_days = high_strength_mask.sum()
        total_days = len(self.planetary_data)
        high_strength_fraction = total_high_strength_days / total_days

        expected_earthquakes_during_high = (
            len(self.earthquakes) * high_strength_fraction
        )

        return {
            "planet": planet,
            "strength_threshold": strength_threshold,
            "high_strength_periods_found": int(total_high_strength_days),
            "earthquakes_during_high_strength": earthquakes_during_high_strength,
            "earthquakes_during_low_strength": earthquakes_during_low_strength,
            "expected_earthquakes_during_high": round(
                expected_earthquakes_during_high, 2
            ),
            "ratio_observed_vs_expected": round(
                earthquakes_during_high_strength
                / max(expected_earthquakes_during_high, 1),
                2,
            ),
            "high_strength_fraction_of_year": round(high_strength_fraction, 4),
            "total_earthquakes": len(self.earthquakes),
            "total_analysis_days": total_days,
        }

    def run_all_correlations(self) -> Dict:
        """Run all defined correlation tests."""
        results = {
            "analysis_timestamp": datetime.now().isoformat(),
            "earthquake_count": len(self.earthquakes),
            "analysis_period": {
                "start": self.earthquakes["datetime"].min().isoformat(),
                "end": self.earthquakes["datetime"].max().isoformat(),
            },
            "conjunction_analysis": {},
            "strength_trigger_analysis": {},
        }

        for combo_name, combo_info in self.COMBINATIONS_TO_TEST.items():
            if combo_info["type"] == "conjunction" and len(combo_info["planets"]) == 2:
                planet1, planet2 = combo_info["planets"]
                result = self.analyze_conjunction_earthquake_correlation(
                    planet1, planet2
                )
                results["conjunction_analysis"][combo_name] = {
                    "description": combo_info["description"],
                    "result": result,
                }

        for combo_name, combo_info in self.COMBINATIONS_TO_TEST.items():
            if combo_info["type"] == "strength_trigger":
                planet = combo_info["planets"][0]
                result = self.analyze_planetary_strength_trigger(planet)
                results["strength_trigger_analysis"][combo_name] = {
                    "description": combo_info["description"],
                    "result": result,
                }

        self.correlation_results = results
        return results

    def export_results_json(self, output_file: str) -> None:
        """Export analysis results to JSON."""
        with open(output_file, "w") as f:
            json.dump(self.correlation_results, f, indent=2, default=str)
        print(f"Results exported to {output_file}")

    def generate_analysis_summary(self) -> str:
        """Generate human-readable summary of findings."""
        if not self.correlation_results:
            return "No correlation analysis results available"

        summary = []
        summary.append("=" * 80)
        summary.append("EARTHQUAKE-PLANETARY CORRELATION ANALYSIS SUMMARY")
        summary.append("=" * 80)
        summary.append("")
        summary.append(
            f"Analysis Period: {self.correlation_results['analysis_period']['start']}"
        )
        summary.append(
            f"                 to {self.correlation_results['analysis_period']['end']}"
        )
        summary.append(
            f"Total Earthquakes Analyzed: {self.correlation_results['earthquake_count']}"
        )
        summary.append("")

        summary.append("PLANETARY CONJUNCTION ANALYSIS")
        summary.append("-" * 80)

        for combo_name, combo_data in self.correlation_results[
            "conjunction_analysis"
        ].items():
            summary.append(f"\n{combo_data['description']}")
            result = combo_data["result"]

            if "status" in result:
                summary.append(f"  Status: {result['status']}")
            else:
                summary.append(f"  Conjunctions Found: {result['conjunctions_found']}")
                summary.append(
                    f"  Earthquakes near conjunction: {result['earthquakes_near_conjunction']}"
                )
                summary.append(f"  Expected (random): {result['expected_earthquakes']}")
                summary.append(
                    f"  Ratio (observed/expected): {result['ratio_near_vs_expected']}"
                )
                summary.append(f"  Chi-square: {result['chi_square_statistic']}")

                if result["chi_square_statistic"] > 3.841:  # p < 0.05
                    summary.append(f"  ⚠️  POTENTIALLY SIGNIFICANT CORRELATION")
                else:
                    summary.append(f"  → No statistically significant correlation")

        summary.append("\n\nPLANETARY STRENGTH TRIGGER ANALYSIS")
        summary.append("-" * 80)

        for combo_name, combo_data in self.correlation_results[
            "strength_trigger_analysis"
        ].items():
            summary.append(f"\n{combo_data['description']}")
            result = combo_data["result"]

            if "status" in result:
                summary.append(f"  Status: {result['status']}")
            else:
                summary.append(
                    f"  Earthquakes during high strength: {result['earthquakes_during_high_strength']}"
                )
                summary.append(
                    f"  Expected (random): {result['expected_earthquakes_during_high']}"
                )
                summary.append(
                    f"  Ratio (observed/expected): {result['ratio_observed_vs_expected']}"
                )

        summary.append("\n" + "=" * 80)
        return "\n".join(summary)

    def get_conjunction_intervals(self, planet1: str, planet2: str, 
                                threshold_deg: float = 13.0) -> List[Tuple[datetime, datetime]]:
        """
        Identify start and end dates of conjunction periods.
        """
        if self.planetary_data is None:
            return []
            
        p1_col = f'{planet1}_position'
        p2_col = f'{planet2}_position'
        
        if p1_col not in self.planetary_data.columns or p2_col not in self.planetary_data.columns:
            return []

        pos1 = self.planetary_data[p1_col].values
        pos2 = self.planetary_data[p2_col].values
        dates = self.planetary_data['datetime'].values
        
        in_conjunction = False
        start_date = None
        intervals = []
        
        for i, dt in enumerate(dates):
            diff = abs(pos1[i] - pos2[i])
            if diff > 180:
                diff = 360 - diff
            
            is_conjunct = diff <= threshold_deg
            
            if is_conjunct and not in_conjunction:
                in_conjunction = True
                start_date = dt
            elif not is_conjunct and in_conjunction:
                in_conjunction = False
                intervals.append((pd.Timestamp(start_date), pd.Timestamp(dates[i-1])))
                start_date = None
                
        if in_conjunction:
            intervals.append((pd.Timestamp(start_date), pd.Timestamp(dates[-1])))
            
        return intervals

    def plot_conjunction_analysis(self, planet1: str, planet2: str, 
                                threshold_deg: float = 13.0,
                                output_path: str = None) -> None:
        """
        Plot the angular separation between two planets and overlay earthquake events.
        """
        if self.planetary_data is None:
            print("No planetary data available. Run generate_planetary_data first.")
            return

        p1_col = f'{planet1}_position'
        p2_col = f'{planet2}_position'
        
        if p1_col not in self.planetary_data.columns or p2_col not in self.planetary_data.columns:
            print(f"Data for {planet1} or {planet2} not found.")
            return

        dates = self.planetary_data['datetime']
        pos1 = self.planetary_data[p1_col]
        pos2 = self.planetary_data[p2_col]
        
        diff = np.abs(pos1 - pos2)
        diff = np.where(diff > 180, 360 - diff, diff)
        
        plt.figure(figsize=(15, 8))
        
        plt.subplot(2, 1, 1)
        plt.plot(dates, diff, label=f'{planet1}-{planet2} Separation', color='blue', linewidth=1)
        plt.axhline(y=threshold_deg, color='red', linestyle='--', label=f'{threshold_deg}° Threshold')
        plt.fill_between(dates, 0, diff, where=(diff <= threshold_deg), 
                         color='red', alpha=0.2, label='Conjunction Period')
        
        plt.ylabel('Separation (Degrees)')
        plt.title(f'{planet1} - {planet2} Conjunction Analysis')
        plt.legend(loc='upper right')
        plt.grid(True, alpha=0.3)
        plt.ylim(0, 180)
        
        plt.subplot(2, 1, 2, sharex=plt.gca())
        start_date = dates.min()
        end_date = dates.max()
        eq_subset = self.earthquakes[
            (self.earthquakes['datetime'] >= start_date) & 
            (self.earthquakes['datetime'] <= end_date)
        ]
        
        if not eq_subset.empty:
            scatter = plt.scatter(eq_subset['datetime'], eq_subset['magnitude'], 
                        s=eq_subset['magnitude']**3 / 10,
                        c=eq_subset['magnitude'], cmap='viridis', 
                        alpha=0.7, label='Earthquakes')
            plt.colorbar(scatter, label='Magnitude')
        else:
            plt.text(0.5, 0.5, "No earthquake data in this period", 
                     ha='center', transform=plt.gca().transAxes)
            
        intervals = self.get_conjunction_intervals(planet1, planet2, threshold_deg)
        for start, end in intervals:
            plt.axvspan(start, end, color='red', alpha=0.1)
            
        plt.ylabel('Magnitude')
        plt.xlabel('Date')
        plt.title('Earthquake Events (Red Zones = Conjunction Periods)')
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        
        if output_path:
            plt.savefig(output_path, dpi=300)
            print(f"Graph saved to {output_path}")
        else:
            plt.show()
        plt.close()


def main():
    """Main analysis workflow."""
    print("=" * 80)
    print("EARTHQUAKE-PLANETARY CORRELATION ANALYSIS (SWISS EPHEMERIS)")
    print("Data-driven framework for multi-use-case validation")
    print("=" * 80)
    
    data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../data'))
    target_file = None
    
    if len(sys.argv) > 1:
        arg_path = sys.argv[1]
        if os.path.exists(arg_path):
            target_file = arg_path
        else:
            print(f"❌ Error: Provided file not found: {arg_path}")
            sys.exit(1)
            
    if not target_file:
        potential_files = [
            os.path.join(data_dir, "usgs_global_6plus_2020_2025.json"),
            os.path.join(data_dir, "usgs_india_5plus_2020_2025.json"),
            os.path.join(data_dir, "usgs_real_data_phase7.json")
        ]
        for p in potential_files:
            if os.path.exists(p):
                target_file = p
                break
    
    if target_file and os.path.exists(target_file):
        print(f"Loading real earthquake data from {target_file}...")
        analyzer = EarthquakeAstrologicalAnalysis(earthquake_data_file=target_file)
    else:
        print("❌ CRITICAL: No real earthquake data found.")
        print(f"Please run 'python3 use_cases/earthquake/scripts/earthquake_data_fetcher.py' first")
        print("to fetch real USGS data.")
        sys.exit(1)
    
    start_date = datetime(2020, 1, 1)
    end_date = datetime(2025, 12, 31)
    
    print("\n1. Generating planetary data (2020-2025)...")
    analyzer.generate_planetary_data(start_date, end_date, frequency='daily')
    
    print("\n2. Genering Conjunction Graphs...")
    output_dir = 'use_cases/earthquake/figures'
    os.makedirs(output_dir, exist_ok=True)
    
    print("   - Generating Mars-Ketu Analysis...")
    analyzer.plot_conjunction_analysis('MARS', 'KETU', threshold_deg=13.0, 
                                     output_path=f'{output_dir}/mars_ketu_conjunction.png')
    print("   - Generating Mars-Saturn Analysis...")
    analyzer.plot_conjunction_analysis('MARS', 'SATURN', threshold_deg=15.0, 
                                     output_path=f'{output_dir}/mars_saturn_conjunction.png')

    print("\n3. Running full correlation analyses statistics...")
    results = analyzer.run_all_correlations()
    
    print("4. Generating summary...")
    summary = analyzer.generate_analysis_summary()
    print(summary)
    
    output_file = 'use_cases/earthquake/data/earthquake_planetary_correlation_analysis.json'
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    analyzer.export_results_json(output_file)
    print(f"\n✅ Analysis complete. Results saved to {output_file}")


if __name__ == '__main__':
    main()
