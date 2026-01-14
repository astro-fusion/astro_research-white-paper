"""
Vedic Numerology-Astrology Integration System

A comprehensive Python package for integrating Vedic Numerology (Anka Jyotish)
with Vedic Astrology (Parashari Jyotish) using Swiss Ephemeris calculations.

This package provides:
- Mulanka (Birth Number) and Bhagyanka (Destiny Number) calculations
- Sidereal planetary position calculations with Lahiri Ayanamsa
- Planetary dignity scoring (0-100 scale)
- Temporal support visualization
- Google Colab integration
"""

import warnings
from datetime import date, datetime, time
from typing import Any, Dict, Optional, Tuple, Union

from .astrology import AyanamsaSystem, BirthChart, calculate_chart
from .config import PLANET_NAMES, Planet
from .dignity import DignityScorer
from .numerology import (
    calculate_bhagyanka,
    calculate_complete_numerology,
    calculate_mulanka,
)
from .visualization import (
    plot_dignity_radar,
    plot_mulanka_vs_bhagyanka,
    plot_temporal_support,
)

__version__ = "0.1.0"
__author__ = "Norah Jones"
__description__ = "Computational Integration of Vedic Numerology and Sidereal Mechanics"


class VedicNumerologyAstrology:
    """
    Main integration class for Vedic Numerology-Astrology analysis.

    This class provides a high-level API that combines numerological calculations
    with astrological analysis to determine how planetary positions support or
    contradict numerological potentials.
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
                raise ValueError(
                    f"Unknown Ayanamsa system '{self.ayanamsa_system}'. Valid systems: {valid_systems}"
                )

        # Create datetime object for birth
        if self.birth_time:
            self.birth_datetime = datetime.combine(self.birth_date, self.birth_time)
        else:
            # Use noon if no time specified (common default)
            self.birth_datetime = datetime.combine(
                self.birth_date, datetime.strptime("12:00:00", "%H:%M:%S").time()
            )

        # Initialize components
        self._numerology_data: Optional[Dict[str, Any]] = None
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
                    raise ValueError(
                        f"Invalid birth time format: {birth_time}. Use HH:MM or HH:MM:SS"
                    )
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
    def numerology_data(self) -> Dict[str, Any]:
        """Get numerology calculations (Mulanka and Bhagyanka)."""
        if self._numerology_data is None:
            self._numerology_data = calculate_complete_numerology(
                self.birth_date, self.birth_time, self.latitude, self.longitude
            )
        return self._numerology_data

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

    def calculate_mulanka(self) -> Dict[str, Any]:
        """
        Calculate Mulanka (Birth Number/Psychic Number).

        Returns:
            Dictionary with Mulanka data including number, planet, and correction status
        """
        return dict(self.numerology_data["mulanka"])

    def calculate_bhagyanka(self) -> Dict[str, Any]:
        """
        Calculate Bhagyanka (Destiny Number/Life Path Number).

        Returns:
            Dictionary with Bhagyanka data including number and planet
        """
        return dict(self.numerology_data["bhagyanka"])

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

    def get_numerology_planets(self) -> Tuple[Planet, Planet]:
        """
        Get the planets ruling Mulanka and Bhagyanka.

        Returns:
            Tuple of (mulanka_planet, bhagyanka_planet)
        """
        mulanka_data = self.calculate_mulanka()
        bhagyanka_data = self.calculate_bhagyanka()

        return mulanka_data["planet"], bhagyanka_data["planet"]

    def analyze_support_contradiction(self) -> Dict[str, Any]:
        """
        Analyze how planetary positions support or contradict numerology.

        Returns:
            Dictionary with support analysis for Mulanka and Bhagyanka
        """
        mulanka_planet, bhagyanka_planet = self.get_numerology_planets()

        mulanka_score = self.score_dignity(mulanka_planet)
        bhagyanka_score = self.score_dignity(bhagyanka_planet)

        # Determine support level
        def get_support_level(score: float) -> str:
            if score >= 75:
                return "Excellent Support"
            elif score >= 50:
                return "Good Support"
            elif score >= 25:
                return "Weak Support"
            else:
                return "Contradiction"

        analysis = {
            "mulanka": {
                "planet": mulanka_planet.name,
                "score": mulanka_score["score"],
                "support_level": get_support_level(mulanka_score["score"]),
                "dignity_type": mulanka_score["dignity_type"],
                "details": mulanka_score,
            },
            "bhagyanka": {
                "planet": bhagyanka_planet.name,
                "score": bhagyanka_score["score"],
                "support_level": get_support_level(bhagyanka_score["score"]),
                "dignity_type": bhagyanka_score["dignity_type"],
                "details": bhagyanka_score,
            },
            "overall": {
                "average_score": (mulanka_score["score"] + bhagyanka_score["score"])
                / 2,
                "harmony_level": self._calculate_harmony(
                    mulanka_score["score"], bhagyanka_score["score"]
                ),
            },
        }

        return analysis

    def _calculate_harmony(self, mulanka_score: float, bhagyanka_score: float) -> str:
        """Calculate overall harmony between Mulanka and Bhagyanka support."""
        avg_score = (mulanka_score + bhagyanka_score) / 2
        diff = abs(mulanka_score - bhagyanka_score)

        if avg_score >= 75 and diff <= 20:
            return "Excellent Harmony"
        elif avg_score >= 60 and diff <= 30:
            return "Good Harmony"
        elif avg_score >= 40:
            return "Moderate Harmony"
        else:
            return "Significant Tension"

    def plot_support_index(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        planet: Optional[Union[Planet, str]] = None,
        use_plotly: bool = True,
    ) -> Any:
        """
        Create temporal support visualization for numerology planet.

        Args:
            start_date: Start date for analysis (optional, defaults to current year start)
            end_date: End date for analysis (optional, defaults to current year end)
            planet: Planet to analyze (optional, defaults to Mulanka planet)
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
        if planet is None:
            mulanka_planet, _ = self.get_numerology_planets()
            planet = mulanka_planet
        elif isinstance(planet, str):
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

    def plot_numerology_comparison(self, use_plotly: bool = True) -> Any:
        """
        Create comparison chart of Mulanka vs Bhagyanka dignity scores.

        Args:
            use_plotly: Whether to use Plotly for interactive charts

        Returns:
            Plot object (Plotly figure or Matplotlib axes)
        """
        mulanka_data = self.calculate_mulanka()
        bhagyanka_data = self.calculate_bhagyanka()

        mulanka_score = self.score_dignity(mulanka_data["planet"])["score"]
        bhagyanka_score = self.score_dignity(bhagyanka_data["planet"])["score"]

        return plot_mulanka_vs_bhagyanka(
            mulanka_score,
            bhagyanka_score,
            mulanka_data["planet"],
            bhagyanka_data["planet"],
            use_plotly,
        )

    def plot_dignity_analysis(
        self, planet: Optional[Union[Planet, str]] = None, use_plotly: bool = True
    ) -> Any:
        """
        Create radar chart showing dignity factors for a planet.

        Args:
            planet: Planet to analyze (optional, defaults to Mulanka planet)
            use_plotly: Whether to use Plotly for interactive charts

        Returns:
            Plot object (Plotly figure or Matplotlib axes)
        """
        # Get planet to analyze
        if planet is None:
            mulanka_planet, _ = self.get_numerology_planets()
            planet = mulanka_planet
        elif isinstance(planet, str):
            planet = Planet[planet.upper()]

        return plot_dignity_radar(self.chart, planet, use_plotly=use_plotly)

    def generate_report(self) -> str:
        """
        Generate a comprehensive analysis report.

        Returns:
            Formatted string report with numerology and astrology analysis
        """
        # Gather all data
        numerology = self.numerology_data
        analysis = self.analyze_support_contradiction()

        # Build report
        report_lines = []
        report_lines.append("=" * 70)
        report_lines.append("VEDIC NUMEROLOGY-ASTROLOGY ANALYSIS REPORT")
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
        report_lines.append("")

        # Numerology results
        report_lines.append("NUMEROLOGY CALCULATIONS:")
        mulanka = numerology["mulanka"]
        bhagyanka = numerology["bhagyanka"]

        report_lines.append(
            f"  Mulanka (Birth Number): {mulanka['number']} - {PLANET_NAMES[mulanka['planet']]}"
        )
        report_lines.append(
            f"  Bhagyanka (Destiny Number): {bhagyanka['number']} - {PLANET_NAMES[bhagyanka['planet']]}"
        )

        if numerology["sunrise_corrected"]:
            report_lines.append(
                "  Note: Sunrise correction applied for Vedic day calculation"
            )
        report_lines.append("")

        # Support analysis
        report_lines.append("PLANETARY SUPPORT ANALYSIS:")
        report_lines.append(
            f"  Mulanka ({analysis['mulanka']['planet']}): {analysis['mulanka']['support_level']}"
        )
        report_lines.append(
            f"    Dignity Score: {analysis['mulanka']['score']:.1f}/100"
        )
        report_lines.append(f"    Dignity Type: {analysis['mulanka']['dignity_type']}")

        report_lines.append("")
        report_lines.append(
            f"  Bhagyanka ({analysis['bhagyanka']['planet']}): {analysis['bhagyanka']['support_level']}"
        )
        report_lines.append(
            f"    Dignity Score: {analysis['bhagyanka']['score']:.1f}/100"
        )
        report_lines.append(
            f"    Dignity Type: {analysis['bhagyanka']['dignity_type']}"
        )

        report_lines.append("")
        report_lines.append(
            f"  Overall Harmony: {analysis['overall']['harmony_level']}"
        )
        report_lines.append(
            f"  Average Score: {analysis['overall']['average_score']:.1f}"
        )

        report_lines.append("=" * 70)

        return "\n".join(report_lines)

    def __repr__(self) -> str:
        """String representation of the analysis object."""
        return (
            f"VedicNumerologyAstrology("
            f"birth_date={self.birth_date}, "
            f"birth_time={self.birth_time}, "
            f"location=({self.latitude:.2f}, {self.longitude:.2f}))"
        )


# Convenience functions for quick analysis
def analyze_birth_chart(
    birth_date: Union[str, date],
    birth_time: Optional[Union[str, time]] = None,
    latitude: float = 28.6139,
    longitude: float = 77.1025,
) -> VedicNumerologyAstrology:
    """
    Create and return a VedicNumerologyAstrology analysis object.

    Args:
        birth_date: Birth date
        birth_time: Birth time (optional)
        latitude: Birth latitude
        longitude: Birth longitude

    Returns:
        Initialized VedicNumerologyAstrology object
    """
    return VedicNumerologyAstrology(birth_date, birth_time, latitude, longitude)
