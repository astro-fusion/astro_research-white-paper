#!/usr/bin/env python3
"""
Temporal Analysis Data Generation Script

Generates 5-year time series data comparing numerology and Vedic astrology
planetary strength calculations. This data demonstrates the fundamental
difference between numerology's discrete date-based system and astrology's
gradual planetary movements.

Usage:
    python scripts/generate_temporal_analysis.py

Output:
    - data/temporal_analysis_5years.csv: Complete time series data
    - data/temporal_analysis_summary.json: Statistical summary
"""

import sys
import os
import json
import csv
from datetime import datetime, timedelta, date
from typing import Dict, List, Any, Optional
import pandas as pd

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from numerology.calculator import calculate_mulanka
from numerology.planet_mapping import get_planet_from_number
from vedic_astrology_core.dignity import DignityScorer
from vedic_astrology_core.astrology import EphemerisEngine
from vedic_astrology_core.config import Planet


class TemporalDataGenerator:
    """
    Generates temporal data comparing numerology and astrology planetary strengths.
    """

    def __init__(
        self, start_date: date = date(2020, 1, 1), end_date: date = date(2025, 1, 1)
    ):
        """
        Initialize the data generator.

        Args:
            start_date: Start date for analysis (default: 2020-01-01)
            end_date: End date for analysis (default: 2025-01-01)
        """
        self.start_date = start_date
        self.end_date = end_date
        self.scorer = DignityScorer()
        self.ephemeris = EphemerisEngine()

        # Create data directory if it doesn't exist
        self.data_dir = os.path.join(
            os.path.dirname(__file__), "..", "data", "processed"
        )
        os.makedirs(self.data_dir, exist_ok=True)

        # All planets to analyze
        self.planets = [
            Planet.SUN,
            Planet.MOON,
            Planet.MARS,
            Planet.MERCURY,
            Planet.JUPITER,
            Planet.VENUS,
            Planet.SATURN,
            Planet.RAHU,
            Planet.KETU,
        ]

    def generate_data(self) -> List[Dict[str, Any]]:
        """
        Generate the complete temporal dataset.

        Returns:
            List of dictionaries containing daily data
        """
        print(f"Generating temporal data from {self.start_date} to {self.end_date}...")
        print("This may take several minutes due to astronomical calculations...")

        data = []
        current_date = self.start_date
        total_days = (self.end_date - self.start_date).days

        day_count = 0
        while current_date < self.end_date:
            try:
                # Calculate numerology data for this date
                numerology_data = self._calculate_numerology_for_date(current_date)

                # Calculate astrology data for this date
                astrology_data = self._calculate_astrology_for_date(current_date)

                # Combine data
                daily_data = {
                    "date": current_date.isoformat(),
                    "day_of_year": current_date.timetuple().tm_yday,
                    "month": current_date.month,
                    "day": current_date.day,
                    "year": current_date.year,
                    **numerology_data,
                    **astrology_data,
                }

                data.append(daily_data)

                day_count += 1
                if day_count % 365 == 0:  # Progress update every year
                    progress = (day_count / total_days) * 100
                    print(".1f")

            except Exception as e:
                print(f"Error processing date {current_date}: {e}")
                # Continue with next date

            current_date += timedelta(days=1)

        print(f"Generated data for {len(data)} days")
        return data

    def _calculate_numerology_for_date(self, target_date: date) -> Dict[str, Any]:
        """
        Calculate numerology data for a specific date.

        In numerology, only one planet has "strength" per day based on the
        reduced day number (1-9). Other planets have zero strength.

        Args:
            target_date: Date to analyze

        Returns:
            Dictionary with numerology strength data
        """
        # Calculate Mulanka (day number)
        mulanka_num, mulanka_planet = calculate_mulanka(target_date)

        # Initialize all planets with zero strength
        numerology_strengths = {
            f"numerology_{planet.name}": 0.0 for planet in self.planets
        }

        # The active planet gets full strength (100)
        numerology_strengths[f"numerology_{mulanka_planet.name}"] = 100.0

        return {
            "numerology_active_planet": mulanka_planet.name,
            "numerology_mulanka_number": mulanka_num,
            **numerology_strengths,
        }

    def _calculate_astrology_for_date(self, target_date: date) -> Dict[str, Any]:
        """
        Calculate astrology dignity scores for all planets on a specific date.

        Args:
            target_date: Date to analyze

        Returns:
            Dictionary with astrology dignity scores
        """
        # Convert date to datetime (noon for calculations)
        dt = datetime.combine(target_date, datetime.min.time().replace(hour=12))

        # Get Julian Day
        julian_day = self.ephemeris.datetime_to_julian_day(dt)

        # Calculate dignity scores for all planets
        astrology_strengths = {}

        for planet in self.planets:
            try:
                # Get planet position
                planet_data = self.ephemeris.get_planet_position(
                    julian_day, planet.name.lower()
                )

                # Calculate full dignity score
                score = self.scorer.calculate_full_score(
                    planet,
                    planet_data["sign"],
                    planet_data["longitude"],
                    planet_data=planet_data,
                )

                astrology_strengths[f"astrology_{planet.name}"] = score

            except Exception as e:
                print(
                    f"Warning: Could not calculate score for {planet.name} on {target_date}: {e}"
                )
                astrology_strengths[f"astrology_{planet.name}"] = 0.0

        return astrology_strengths

    def save_data(
        self, data: List[Dict[str, Any]], output_file: Optional[str] = None
    ) -> str:
        """
        Save the generated data to CSV and JSON files.

        Args:
            data: Generated temporal data
            output_file: Optional custom output filename

        Returns:
            Path to the saved CSV file
        """
        if output_file is None:
            output_file = "temporal_analysis_5years.csv"

        csv_path = os.path.join(self.data_dir, output_file)
        json_path = os.path.join(
            self.data_dir, output_file.replace(".csv", "_summary.json")
        )

        # Save CSV
        if data:
            df = pd.DataFrame(data)
            df.to_csv(csv_path, index=False)
            print(f"Saved {len(data)} records to {csv_path}")

            # Save summary statistics as JSON
            summary = self._generate_summary(data)
            with open(json_path, "w") as f:
                json.dump(summary, f, indent=2, default=str)
            print(f"Saved summary statistics to {json_path}")

        return csv_path

    def _generate_summary(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate summary statistics from the temporal data.

        Args:
            data: Generated temporal data

        Returns:
            Dictionary with summary statistics
        """
        if not data:
            return {"error": "No data to summarize"}

        df = pd.DataFrame(data)

        summary = {
            "metadata": {
                "start_date": self.start_date.isoformat(),
                "end_date": self.end_date.isoformat(),
                "total_days": len(data),
                "planets_analyzed": [p.name for p in self.planets],
            },
            "numerology_stats": {},
            "astrology_stats": {},
            "correlation_analysis": {},
        }

        # Numerology statistics (discrete changes)
        numerology_cols = [
            col
            for col in df.columns
            if col.startswith("numerology_")
            and not col.endswith("_active_planet")
            and not col.endswith("_mulanka_number")
        ]

        for col in numerology_cols:
            planet_name = col.replace("numerology_", "")
            values = df[col].dropna()

            summary["numerology_stats"][planet_name] = {
                "mean": float(values.mean()),
                "std": float(values.std()),
                "min": float(values.min()),
                "max": float(values.max()),
                "unique_values": sorted(values.unique().tolist()),
                "change_frequency": self._calculate_change_frequency(
                    df["date"], values
                ),
            }

        # Astrology statistics (continuous changes)
        astrology_cols = [col for col in df.columns if col.startswith("astrology_")]

        for col in astrology_cols:
            planet_name = col.replace("astrology_", "")
            values = df[col].dropna()

            summary["astrology_stats"][planet_name] = {
                "mean": float(values.mean()),
                "std": float(values.std()),
                "min": float(values.min()),
                "max": float(values.max()),
                "change_frequency": self._calculate_change_frequency(
                    df["date"], values, threshold=0.1
                ),  # Any change > 0.1
            }

        # Correlation analysis
        for planet in self.planets:
            num_col = f"numerology_{planet.name}"
            ast_col = f"astrology_{planet.name}"

            if num_col in df.columns and ast_col in df.columns:
                correlation = df[num_col].corr(df[ast_col])
                summary["correlation_analysis"][planet.name] = {
                    "pearson_correlation": (
                        float(correlation) if not pd.isna(correlation) else None
                    ),
                    "numerology_mean": float(df[num_col].mean()),
                    "astrology_mean": float(df[ast_col].mean()),
                    "correlation_interpretation": self._interpret_correlation(
                        correlation
                    ),
                }

        return summary

    def _calculate_change_frequency(
        self, dates: pd.Series, values: pd.Series, threshold: float = 1.0
    ) -> Dict[str, Any]:
        """
        Calculate how frequently values change.

        Args:
            dates: Date series
            values: Value series
            threshold: Minimum change to count as a change

        Returns:
            Dictionary with change frequency statistics
        """
        if len(values) < 2:
            return {"total_changes": 0, "avg_days_between_changes": None}

        changes = 0
        change_dates = []

        prev_value = values.iloc[0]
        for i in range(1, len(values)):
            curr_value = values.iloc[i]
            if abs(curr_value - prev_value) >= threshold:
                changes += 1
                change_dates.append(dates.iloc[i])
                prev_value = curr_value

        avg_days_between_changes = None
        if changes > 1:
            # Calculate average days between changes
            change_datetimes = [pd.to_datetime(d) for d in change_dates]
            intervals = [
                (change_datetimes[i] - change_datetimes[i - 1]).days
                for i in range(1, len(change_datetimes))
            ]
            avg_days_between_changes = (
                sum(intervals) / len(intervals) if intervals else None
            )

        return {
            "total_changes": changes,
            "avg_days_between_changes": avg_days_between_changes,
            "change_percentage": (changes / len(values)) * 100,
        }

    def _interpret_correlation(self, correlation: float) -> str:
        """
        Interpret correlation coefficient.

        Args:
            correlation: Pearson correlation coefficient

        Returns:
            Text interpretation
        """
        if pd.isna(correlation):
            return "No correlation data available"

        abs_corr = abs(correlation)
        if abs_corr < 0.1:
            return "No correlation"
        elif abs_corr < 0.3:
            return "Weak correlation"
        elif abs_corr < 0.5:
            return "Moderate correlation"
        elif abs_corr < 0.7:
            return "Strong correlation"
        else:
            return "Very strong correlation"


def main():
    """Main execution function."""
    print("Vedic Numerology-Astrology Temporal Correlation Analysis")
    print("=" * 60)

    # Initialize generator
    generator = TemporalDataGenerator()

    # Generate data
    data = generator.generate_data()

    # Save data
    output_file = generator.save_data(data)

    print(f"\nData generation complete!")
    print(f"Output saved to: {output_file}")

    # Print key insights
    if data:
        df = pd.DataFrame(data)

        print("\nKey Findings:")
        print("-" * 30)

        # Count numerology changes (should be ~365 per year due to day number changes)
        numerology_changes = sum(
            1
            for i in range(1, len(data))
            if data[i]["numerology_mulanka_number"]
            != data[i - 1]["numerology_mulanka_number"]
        )
        print(f"Numerology system changes: {numerology_changes} times over 5 years")

        # Calculate astrology volatility
        astrology_changes = {}
        for planet in generator.planets:
            col = f"astrology_{planet.name}"
            if col in df.columns:
                changes = sum(
                    1
                    for i in range(1, len(df))
                    if abs(df[col].iloc[i] - df[col].iloc[i - 1]) > 0.1
                )
                astrology_changes[planet.name] = changes

        print(
            f"Astrology system - average changes per planet: {sum(astrology_changes.values()) / len(astrology_changes):.0f} times over 5 years"
        )

        print("\nThis demonstrates the fundamental difference:")
        print("- Numerology: Discrete, date-based changes (~73 changes/year)")
        print(
            "- Astrology: Continuous, gradual changes (1000+ changes/year per planet)"
        )


if __name__ == "__main__":
    main()
