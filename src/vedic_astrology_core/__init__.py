"""
Vedic Astrology Core Library

A comprehensive Python package for Vedic Astrology (Parashari Jyotish)
calculations using Swiss Ephemeris. This is the core library providing
astrological functionality that can be extended by use cases like numerology.

This package provides:
- Sidereal planetary position calculations with Lahiri Ayanamsa
- Complete birth chart generation with all planets and houses
- Planetary dignity scoring (0-100 scale)
- Temporal analysis and transit calculations
- Visualization utilities for astrological data
- Google Colab integration
"""

import warnings
from datetime import date, datetime, time
from typing import Any, Dict, Optional, Tuple, Union

from .astrology import AyanamsaSystem, BirthChart, calculate_chart
from .config import PLANET_NAMES, Planet
from .dignity import DignityScorer
from .visualization import (
    plot_dignity_radar,
    plot_temporal_support,
)

__version__ = "0.1.0"
__author__ = "Norah Jones"
__description__ = "Vedic Astrology Core Library with Swiss Ephemeris Integration"


class VedicAstrologyChart:
    """
    Main class for Vedic Astrology chart analysis.

    This class provides a high-level API for astrological calculations including
    birth chart generation, planetary dignity scoring, and temporal analysis.
    Can be extended by use cases like numerology for specific applications.
    """

    def __init__(
        self,
        birth_date: Union[str, date],
        birth_time: Optional[Union[str, time]] = None,
        latitude: float = 28.6139,
        longitude: float = 77.1025,
        timezone: str = "Asia/Kolkata",
        ayanamsa_system: str = "LAHIRI",
    ):
        """
        Initialize the analysis with birth data.

        Args:
            birth_date: Birth date (YYYY-MM-DD string or date object)
            birth_time: Birth time (HH:MM:SS string or time object, optional)
            latitude: Birth latitude in decimal degrees (default: Delhi)
            longitude: Birth longitude in decimal degrees (default: Delhi)
            timezone: Timezone string (default: Asia/Kolkata)
            ayanamsa_system: Ayanamsa system for sidereal calculations
        """
        # Parse and validate birth data
        self.birth_date = self._parse_birth_date(birth_date)
        self.birth_time = self._parse_birth_time(birth_time) if birth_time else None
        self.latitude = latitude
        self.longitude = longitude
        self.timezone = timezone
        self.ayanamsa_system = ayanamsa_system

        # Validate Ayanamsa system
        if self.ayanamsa_system.upper() != "LAHIRI":
            try:
                AyanamsaSystem[self.ayanamsa_system.upper()]
            except KeyError:
                valid_systems = [s.name for s in AyanamsaSystem]
                msg = (
                    f"Unknown Ayanamsa system '{self.ayanamsa_system}'. "
                    f"Valid systems: {valid_systems}"
                )
                raise ValueError(msg)

        # Create datetime object for birth
        if self.birth_time:
            self.birth_datetime = datetime.combine(self.birth_date, self.birth_time)
        else:
            # Use noon if no time specified (common default)
            self.birth_datetime = datetime.combine(
                self.birth_date, datetime.strptime("12:00:00", "%H:%M:%S").time()
            )

        # Initialize components
        self._chart: Optional[BirthChart] = None
        self._dignity_scorer = DignityScorer()

        # Validate coordinates
        self._validate_coordinates()

    def _parse_birth_date(self, birth_date: Union[str, date]) -> date:
        """Parse birth date from string or date object."""
        if isinstance(birth_date, str):
            try:
                return datetime.strptime(birth_date, "%Y-%m-%d").date()
            except ValueError:
                raise ValueError(
                    f"Invalid birth date format: {birth_date}. Use YYYY-MM-DD"
                )
        elif isinstance(birth_date, date):
            return birth_date
        else:
            raise TypeError(
                f"birth_date must be string or date object, got {type(birth_date)}"
            )

    def _parse_birth_time(self, birth_time: Union[str, time]) -> time:
        """Parse birth time from string or time object."""
        if isinstance(birth_time, str):
            try:
                return datetime.strptime(birth_time, "%H:%M:%S").time()
            except ValueError:
                # Try without seconds
                try:
                    return datetime.strptime(birth_time, "%H:%M").time()
                except ValueError:
                    msg = (
                        f"Invalid birth time format: {birth_time}. "
                        "Use HH:MM or HH:MM:SS"
                    )
                    raise ValueError(msg)
        elif isinstance(birth_time, time):
            return birth_time
        else:
            raise TypeError(
                f"birth_time must be string or time object, got {type(birth_time)}"
            )

    def _validate_coordinates(self) -> None:
        """Validate latitude and longitude coordinates."""
        if not (-90 <= self.latitude <= 90):
            raise ValueError(
                f"Latitude must be between -90 and 90, got {self.latitude}"
            )
        if not (-180 <= self.longitude <= 180):
            raise ValueError(
                f"Longitude must be between -180 and 180, got {self.longitude}"
            )

    @property
    def chart(self) -> BirthChart:
        """Get birth chart with planetary positions."""
        if self._chart is None:
            ayanamsa = AyanamsaSystem.LAHIRI  # Default to Lahiri
            if self.ayanamsa_system.upper() != "LAHIRI":
                ayanamsa = AyanamsaSystem[self.ayanamsa_system.upper()]

            self._chart = calculate_chart(
                self.birth_datetime, self.latitude, self.longitude, ayanamsa
            )
        return self._chart

    def score_dignity(self, planet: Union[Planet, str]) -> Dict[str, Any]:
        """
        Score planetary dignity in the birth chart.

        Args:
            planet: Planet to score (Planet enum or string name)

        Returns:
            Dictionary with dignity scoring details
        """
        # Convert string to Planet enum if needed
        if isinstance(planet, str):
            planet = Planet[planet.upper()]

        return self._dignity_scorer.score_planet_in_chart(planet, self.chart)

    def plot_temporal_support(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        planet: Optional[Union[Planet, str]] = None,
        use_plotly: bool = True,
    ) -> Any:
        """
        Create temporal support visualization for a planet.

        Args:
            start_date: Start date for analysis (optional, defaults to current
                year start)
            end_date: End date for analysis (optional, defaults to current year end)
            planet: Planet to analyze
            use_plotly: Whether to use Plotly for interactive charts

        Returns:
            Plot object (Plotly figure or Matplotlib axes)
        """
        from datetime import date

        # Set defaults
        current_year = date.today().year
        if start_date is None:
            start_date = datetime(current_year, 1, 1)
        if end_date is None:
            end_date = datetime(current_year, 12, 31)

        # Get planet to analyze
        if isinstance(planet, str):
            planet = Planet[planet.upper()]

        # Get natal score for reference line
        natal_score = self.score_dignity(planet)["score"]

        return plot_temporal_support(
            planet,
            start_date,
            end_date,
            self.latitude,
            self.longitude,
            natal_score,
            use_plotly,
        )

    def plot_dignity_analysis(
        self, planet: Optional[Union[Planet, str]] = None, use_plotly: bool = True
    ) -> Any:
        """
        Create radar chart showing dignity factors for a planet.

        Args:
            planet: Planet to analyze
            use_plotly: Whether to use Plotly for interactive charts

        Returns:
            Plot object (Plotly figure or Matplotlib axes)
        """
        # Get planet to analyze
        if isinstance(planet, str):
            planet = Planet[planet.upper()]

        return plot_dignity_radar(self.chart, planet, use_plotly=use_plotly)

    def generate_chart_report(self) -> str:
        """
        Generate a comprehensive birth chart analysis report.

        Returns:
            Formatted string report with astrological analysis
        """
        chart = self.chart

        # Build report
        report_lines = []
        report_lines.append("=" * 70)
        report_lines.append("VEDIC ASTROLOGY BIRTH CHART ANALYSIS")
        report_lines.append("=" * 70)
        report_lines.append("")

        # Birth data
        report_lines.append("BIRTH DATA:")
        report_lines.append(f"  Date: {self.birth_date}")
        if self.birth_time:
            report_lines.append(f"  Time: {self.birth_time}")
        report_lines.append(
            f"  Location: {self.latitude:.4f}°N, {self.longitude:.4f}°E"
        )
        report_lines.append(f"  Ayanamsa: {chart.ayanamsa:.2f}° ({self.ayanamsa_system})")
        report_lines.append("")

        # Ascendant
        report_lines.append("ASCENDANT:")
        asc = chart.ascendant
        report_lines.append(f"  Sign: {asc.sign_name}")
        report_lines.append(f"  Degrees: {asc.degrees_in_sign:.2f}°")
        report_lines.append(f"  Longitude: {asc.longitude:.2f}°")
        report_lines.append("")

        # Planetary positions
        report_lines.append("PLANETARY POSITIONS:")
        for planet_name, planet_data in chart.planets.items():
            dignity_score = self.score_dignity(planet_name)
            report_lines.append(f"  {planet_name}:")
            report_lines.append(f"    Sign: {planet_data.sign.name}")
            report_lines.append(f"    Degrees: {planet_data.degrees_in_sign:.2f}°")
            report_lines.append(f"    Longitude: {planet_data.longitude:.2f}°")
            report_lines.append(f"    Dignity Score: {dignity_score['score']:.1f}/100 ({dignity_score['dignity_type']})")
            if hasattr(planet_data, 'retrograde') and planet_data.retrograde:
                report_lines.append("    Retrograde: Yes")
        report_lines.append("")

        # House cusps
        report_lines.append("HOUSE CUSPS:")
        for i, house_data in enumerate(chart.houses):
            report_lines.append(f"  House {i+1}: {house_data.sign_name} {house_data.degrees_in_sign:.2f}°")
        report_lines.append("")

        report_lines.append("=" * 70)

        return "\n".join(report_lines)

    def __repr__(self) -> str:
        """String representation of the analysis object."""
        return (
            f"VedicAstrologyChart("
            f"birth_date={self.birth_date}, "
            f"birth_time={self.birth_time}, "
            f"location=({self.latitude:.2f}, {self.longitude:.2f}))"
        )


# Convenience functions for quick analysis
def create_birth_chart(
    birth_date: Union[str, date],
    birth_time: Optional[Union[str, time]] = None,
    latitude: float = 28.6139,
    longitude: float = 77.1025,
) -> VedicAstrologyChart:
    """
    Create and return a VedicAstrologyChart analysis object.

    Args:
        birth_date: Birth date
        birth_time: Birth time (optional)
        latitude: Birth latitude
        longitude: Birth longitude

    Returns:
        Initialized VedicAstrologyChart object
    """
    return VedicAstrologyChart(birth_date, birth_time, latitude, longitude)
