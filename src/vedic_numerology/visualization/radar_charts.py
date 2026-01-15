"""
Radar Charts for Multi-Factor Analysis

Creates radar/spider charts to visualize multiple dignity factors
and provide comprehensive planetary strength analysis.
"""

from typing import Any, Dict, List, Optional, Tuple, cast

import matplotlib.pyplot as plt
import numpy as np

try:
    import plotly.graph_objects as go

    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
    go = Any  # type: ignore

from ..config.constants import Planet

# Default radar chart configuration
RADAR_CONFIG = {
    "figsize": (10, 8),
    "alpha": 0.3,
    "line_width": 2,
    "marker_size": 6,
    "title_fontsize": 14,
    "label_fontsize": 10,
}

# Color palette for multiple planets
RADAR_COLORS = [
    "#1f77b4",  # Blue
    "#ff7f0e",  # Orange
    "#2ca02c",  # Green
    "#d62728",  # Red
    "#9467bd",  # Purple
    "#8c564b",  # Brown
    "#e377c2",  # Pink
    "#7f7f7f",  # Gray
    "#bcbd22",  # Olive
]


def plot_dignity_radar(
    chart: Any,
    planet: Planet,
    factors: Optional[List[str]] = None,
    use_plotly: bool = True,
) -> Any:
    """
    Create a radar chart showing multiple dignity factors for a planet.

    Args:
        chart: BirthChart object with planetary data
        planet: Planet to analyze
        factors: List of factors to include (optional)
        use_plotly: Whether to use Plotly (interactive) or Matplotlib

    Returns:
        Plot object (Plotly figure or Matplotlib axes)
    """
    # Default factors if not specified
    if factors is None:
        factors = ["Position", "Direction", "Temporal", "Motion", "Combustion"]

    # Calculate factor values
    factor_values = _calculate_dignity_factors(chart, planet, factors)

    if use_plotly and PLOTLY_AVAILABLE:
        return _plot_radar_plotly(planet, factors, factor_values)
    else:
        return _plot_radar_matplotlib(planet, factors, factor_values)


def plot_multi_planet_radar(
    chart: Any,
    planets: List[Planet],
    factors: Optional[List[str]] = None,
    use_plotly: bool = True,
) -> Any:
    """
    Create a radar chart comparing multiple planets across dignity factors.

    Args:
        chart: BirthChart object with planetary data
        planets: List of planets to compare
        factors: List of factors to include (optional)
        use_plotly: Whether to use Plotly (interactive) or Matplotlib

    Returns:
        Plot object (Plotly figure or Matplotlib axes)
    """
    if factors is None:
        factors = ["Position", "Direction", "Temporal", "Motion"]

    # Calculate factors for all planets
    all_factors = {}
    for planet in planets:
        try:
            all_factors[planet] = _calculate_dignity_factors(chart, planet, factors)
        except KeyError:
            # Skip planets not in chart
            continue

    if use_plotly and PLOTLY_AVAILABLE:
        return _plot_multi_radar_plotly(planets, factors, all_factors)
    else:
        return _plot_multi_radar_matplotlib(planets, factors, all_factors)


def _calculate_dignity_factors(
    chart: Any, planet: Planet, factors: List[str]
) -> Dict[str, float]:
    """
    Calculate dignity factor values for a planet.

    Args:
        chart: BirthChart object
        planet: Planet to analyze
        factors: List of factors to calculate

    Returns:
        Dictionary mapping factor names to values (0-100)
    """
    planet_data = chart.planets.get(planet.name, {})

    if not planet_data:
        # Return zeros if planet data not available
        return {factor: 0.0 for factor in factors}

    factor_values = {}

    for factor in factors:
        if factor == "Position":
            # Essential dignity score
            factor_values[factor] = _calculate_position_factor(planet, planet_data)
        elif factor == "Direction":
            # Directional strength (house-based)
            factor_values[factor] = _calculate_directional_factor(planet_data)
        elif factor == "Temporal":
            # Day/night strength
            factor_values[factor] = _calculate_temporal_factor(planet, chart)
        elif factor == "Motion":
            # Retrograde bonus
            factor_values[factor] = _calculate_motion_factor(planet_data)
        elif factor == "Combustion":
            # Combustion penalty (inverse)
            factor_values[factor] = _calculate_combustion_factor(planet_data)
        elif factor == "Aspect":
            # Aspect strength (simplified)
            factor_values[factor] = _calculate_aspect_factor(planet, chart)
        elif factor == "Nakshatra":
            # Lunar mansion strength (simplified)
            factor_values[factor] = _calculate_nakshatra_factor(planet_data)
        else:
            # Unknown factor
            factor_values[factor] = 50.0  # Neutral value

    return factor_values


def _calculate_position_factor(planet: Planet, planet_data: Dict) -> float:
    """
    Calculate positional dignity factor.

    Args:
        planet: Planet
        planet_data: Planetary position data

    Returns:
        Position strength score (0-100)
    """
    from ..dignity.exaltation_matrix import (
        is_in_exaltation,
        is_in_moolatrikona,
        is_in_own_sign,
    )

    longitude = planet_data.get("longitude", 0)

    # Check dignity hierarchy
    if is_in_exaltation(longitude, planet):
        return 100.0
    elif is_in_moolatrikona(longitude, planet):
        return 85.0
    elif is_in_own_sign(longitude, planet):
        return 75.0
    else:
        # Friend/neutral/enemy sign - simplified scoring
        return 50.0


def _calculate_directional_factor(planet_data: Dict) -> float:
    """
    Calculate directional strength based on house position.

    Args:
        planet_data: Planetary position data

    Returns:
        Directional strength score (0-100)
    """
    # Angular houses (1, 4, 7, 10) are strongest
    # Succeedent houses (2, 5, 8, 11) are medium
    # Cadent houses (3, 6, 9, 12) are weakest

    house = planet_data.get("house", 1)

    if house in [1, 4, 7, 10]:  # Angular (Kendra)
        return 90.0
    elif house in [2, 5, 8, 11]:  # Succeedent (Panapara)
        return 70.0
    elif house in [3, 6, 9, 12]:  # Cadent (Apoklima)
        return 40.0
    else:
        return 50.0


def _calculate_temporal_factor(planet: Planet, chart: Any) -> float:
    """
    Calculate temporal (day/night) strength factor.

    Args:
        planet: Planet
        chart: BirthChart object

    Returns:
        Temporal strength score (0-100)
    """
    # Day planets: Sun, Jupiter, Venus
    # Night planets: Moon, Mars, Saturn
    # Mercury and nodes are neutral

    day_planets = {Planet.SUN, Planet.JUPITER, Planet.VENUS}
    night_planets = {Planet.MOON, Planet.MARS, Planet.SATURN}

    # Determine if birth was during day or night
    # This is a simplification - would need proper sunrise/sunset calculation
    birth_hour = chart.birth_datetime.hour

    # Assume sunrise at 6 AM, sunset at 6 PM for this example
    is_daytime = 6 <= birth_hour <= 18

    if planet in day_planets:
        return 80.0 if is_daytime else 40.0
    elif planet in night_planets:
        return 80.0 if not is_daytime else 40.0
    else:
        # Mercury, Rahu, Ketu - neutral
        return 60.0


def _calculate_motion_factor(planet_data: Dict) -> float:
    """
    Calculate motion-based strength (retrograde bonus).

    Args:
        planet_data: Planetary position data

    Returns:
        Motion strength score (0-100)
    """
    is_retrograde = planet_data.get("retrograde", False)
    speed = abs(planet_data.get("longitude_speed", 0))

    if is_retrograde:
        return 85.0  # Retrograde bonus
    elif speed > 1.0:
        return 70.0  # Fast moving
    elif speed < 0.5:
        return 40.0  # Slow moving
    else:
        return 60.0  # Normal speed


def _calculate_combustion_factor(planet_data: Dict) -> float:
    """
    Calculate combustion factor (inverse of combustion penalty).

    Args:
        planet_data: Planetary position data

    Returns:
        Combustion strength score (0-100, higher = less combust)
    """
    is_combust = planet_data.get("combust", False)

    if is_combust:
        return 20.0  # Combust = weak
    else:
        return 90.0  # Not combust = strong


def _calculate_aspect_factor(planet: Planet, chart: Any) -> float:
    """
    Calculate aspect-based strength (simplified).

    Args:
        planet: Planet
        chart: BirthChart object

    Returns:
        Aspect strength score (0-100)
    """
    # Simplified aspect calculation
    # In full Vedic astrology, this would check conjunctions, trines, squares, etc.
    return 65.0  # Neutral-positive for this example


def _calculate_nakshatra_factor(planet_data: Dict) -> float:
    """
    Calculate Nakshatra (lunar mansion) based strength.

    Args:
        planet_data: Planetary position data

    Returns:
        Nakshatra strength score (0-100)
    """
    # Simplified - would need full Nakshatra calculation
    longitude = planet_data.get("longitude", 0)
    nakshatra_index = int(longitude / (360 / 27))  # 27 Nakshatras

    # Some Nakshatras are considered more auspicious
    auspicious_nakshatras = [1, 3, 5, 7, 9, 11, 13, 16, 18, 21, 23, 26]  # Example

    if nakshatra_index in auspicious_nakshatras:
        return 75.0
    else:
        return 55.0


def _plot_radar_plotly(
    planet: Planet, factors: List[str], values: Dict[str, float]
) -> Any:
    """
    Create Plotly radar chart for single planet dignity factors.

    Args:
        planet: Planet being analyzed
        factors: List of factor names
        values: Dictionary of factor values

    Returns:
        Plotly figure
    """
    # Prepare data
    factor_values = [values.get(factor, 50) for factor in factors]
    factor_values.append(factor_values[0])  # Close the radar
    factors_closed = factors + [factors[0]]

    # Create figure
    fig = go.Figure()

    fig.add_trace(
        go.Scatterpolar(
            r=factor_values,
            theta=factors_closed,
            fill="toself",
            name=planet.name,
            line_color=RADAR_COLORS[0],
        )
    )

    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
        title=f"Dignity Factors for {planet.name}",
        showlegend=False,
    )

    return fig


def _plot_radar_matplotlib(
    planet: Planet, factors: List[str], values: Dict[str, float]
) -> plt.Axes:
    """
    Create Matplotlib radar chart for single planet dignity factors.

    Args:
        planet: Planet being analyzed
        factors: List of factor names
        values: Dictionary of factor values

    Returns:
        Matplotlib axes
    """
    # Prepare data
    factor_values = [values.get(factor, 50) for factor in factors]
    num_vars = len(factors)

    # Compute angle for each axis
    angles = [n / float(num_vars) * 2 * np.pi for n in range(num_vars)]
    angles += angles[:1]  # Close the plot

    # Values for closing the plot
    factor_values += factor_values[:1]

    # Create figure
    fig = plt.figure(figsize=cast(Tuple[float, float], RADAR_CONFIG["figsize"]))
    ax = fig.add_subplot(111, polar=True)

    # Plot data
    ax.plot(
        angles,
        factor_values,
        "o-",
        linewidth=RADAR_CONFIG["line_width"],
        label=planet.name,
        color=RADAR_COLORS[0],
        markersize=RADAR_CONFIG["marker_size"],
    )
    ax.fill(angles, factor_values, alpha=RADAR_CONFIG["alpha"], color=RADAR_COLORS[0])

    # Set labels
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(factors, fontsize=RADAR_CONFIG["label_fontsize"])

    # Set radial limits and labels
    ax.set_ylim(0, 100)
    ax.set_yticks([20, 40, 60, 80, 100])
    ax.set_yticklabels(["20", "40", "60", "80", "100"])

    # Title
    ax.set_title(
        f"Dignity Factors for {planet.name}",
        size=RADAR_CONFIG["title_fontsize"],
        fontweight="bold",
        pad=20,
    )

    plt.tight_layout()
    return ax


def _plot_multi_radar_plotly(
    planets: List[Planet],
    factors: List[str],
    all_values: Dict[Planet, Dict[str, float]],
) -> Any:
    """
    Create Plotly radar chart comparing multiple planets.

    Args:
        planets: List of planets to compare
        factors: List of factor names
        all_values: Dictionary mapping planets to their factor values

    Returns:
        Plotly figure
    """
    # Create figure
    fig = go.Figure()

    for i, planet in enumerate(planets):
        if planet not in all_values:
            continue

        values = all_values[planet]
        factor_values = [values.get(factor, 50) for factor in factors]
        factor_values.append(factor_values[0])  # Close the radar
        factors_closed = factors + [factors[0]]

        fig.add_trace(
            go.Scatterpolar(
                r=factor_values,
                theta=factors_closed,
                fill="toself",
                name=planet.name,
                line_color=RADAR_COLORS[i % len(RADAR_COLORS)],
            )
        )

    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
        title="Planetary Dignity Comparison",
        showlegend=True,
    )

    return fig


def _plot_multi_radar_matplotlib(
    planets: List[Planet],
    factors: List[str],
    all_values: Dict[Planet, Dict[str, float]],
) -> plt.Axes:
    """
    Create Matplotlib radar chart comparing multiple planets.

    Args:
        planets: List of planets to compare
        factors: List of factor names
        all_values: Dictionary mapping planets to their factor values

    Returns:
        Matplotlib axes
    """
    # Prepare data
    num_vars = len(factors)
    angles = [n / float(num_vars) * 2 * np.pi for n in range(num_vars)]
    angles += angles[:1]

    # Create figure
    fig = plt.figure(figsize=cast(Tuple[float, float], RADAR_CONFIG["figsize"]))
    ax = fig.add_subplot(111, polar=True)

    # Plot each planet
    for i, planet in enumerate(planets):
        if planet not in all_values:
            continue

        values = all_values[planet]
        factor_values = [values.get(factor, 50) for factor in factors]
        factor_values += factor_values[:1]  # Close the plot

        ax.plot(
            angles,
            factor_values,
            "o-",
            linewidth=RADAR_CONFIG["line_width"],
            label=planet.name,
            color=RADAR_COLORS[i % len(RADAR_COLORS)],
            markersize=RADAR_CONFIG["marker_size"],
        )
        ax.fill(
            angles,
            factor_values,
            alpha=RADAR_CONFIG["alpha"],
            color=RADAR_COLORS[i % len(RADAR_COLORS)],
        )

    # Set labels and formatting
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(factors, fontsize=RADAR_CONFIG["label_fontsize"])
    ax.set_ylim(0, 100)
    ax.set_yticks([20, 40, 60, 80, 100])
    ax.set_yticklabels(["20", "40", "60", "80", "100"])

    # Title and legend
    ax.set_title(
        "Planetary Dignity Comparison",
        size=RADAR_CONFIG["title_fontsize"],
        fontweight="bold",
        pad=20,
    )
    ax.legend(loc="upper right", bbox_to_anchor=(1.3, 1.0))

    plt.tight_layout()
    return ax
