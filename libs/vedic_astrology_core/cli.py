#!/usr/bin/env python3
"""
Command Line Interface for Vedic Astrology Core Library

Provides a simple CLI for basic astrological calculations.
"""

import argparse
import sys
from typing import Optional

from . import create_birth_chart


def create_birth_chart_command(args: argparse.Namespace) -> None:
    """Create and display a birth chart."""
    try:
        chart = create_birth_chart(
            birth_date=args.date,
            birth_time=args.time,
            latitude=args.lat,
            longitude=args.lon,
        )

        print("🪐 Vedic Astrology Birth Chart Analysis")
        print("=" * 50)

        # Display basic chart information
        print(f"Birth Date: {chart.birth_date}")
        if chart.birth_time:
            print(f"Birth Time: {chart.birth_time}")
        print(f"Location: {chart.latitude:.4f}°N, {chart.longitude:.4f}°E")
        print(f"Ascendant: {chart.chart.ascendant['sign_name']}")
        print(f"Planets: {len(chart.chart.planets)}")
        print()

        # Display planetary positions
        print("PLANETARY POSITIONS:")
        for planet_name, planet_data in chart.chart.planets.items():
            dignity_score = chart.score_dignity(planet_name)
            print(
                f"  {planet_name}: {planet_data['sign_name']} {planet_data['degrees_in_sign']:.1f}°"
            )
            print(f"    Dignity Score: {dignity_score['score']:.1f}/100")

        print("\n✅ Birth chart generated successfully!")

    except Exception as e:
        print(f"❌ Error creating birth chart: {e}", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Vedic Astrology Core Library CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create a birth chart
  vedic-numerology --date 1984-08-27 --time 10:30 --lat 28.6139 --lon 77.1025
        """,
    )

    parser.add_argument(
        "--date",
        required=True,
        help="Birth date in YYYY-MM-DD format",
    )

    parser.add_argument(
        "--time",
        help="Birth time in HH:MM:SS format (optional)",
    )

    parser.add_argument(
        "--lat",
        type=float,
        default=28.6139,
        help="Birth latitude in decimal degrees (default: Delhi)",
    )

    parser.add_argument(
        "--lon",
        type=float,
        default=77.1025,
        help="Birth longitude in decimal degrees (default: Delhi)",
    )

    args = parser.parse_args()

    # Execute the command
    create_birth_chart_command(args)


if __name__ == "__main__":
    main()
