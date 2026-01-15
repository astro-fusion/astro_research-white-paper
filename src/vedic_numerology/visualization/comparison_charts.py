"""
Comparison Charts

Creates visualizations comparing Mulanka (Birth Number) and Bhagyanka (Destiny Number)
planetary dignity scores and relationships.
"""

from typing import Any, Dict, Optional

import matplotlib.pyplot as plt
import numpy as np

try:
    import seaborn as sns

    SEABORN_AVAILABLE = True
except ImportError:
    SEABORN_AVAILABLE = False

try:
    import plotly.graph_objects as go

    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
    go = Any  # type: ignore

from ..config.constants import Planet

# Color scheme for Mulanka vs Bhagyanka
COMPARISON_COLORS = {
    "mulanka": "#1f77b4",  # Blue
    "bhagyanka": "#ff7f0e",  # Orange
    "neutral": "#7f7f7f",  # Gray
}


def plot_mulanka_vs_bhagyanka(
    mulanka_score: float,
    bhagyanka_score: float,
    mulanka_planet: Optional[Planet] = None,
    bhagyanka_planet: Optional[Planet] = None,
    use_plotly: bool = True,
) -> Any:
    """
    Create a bar chart comparing Mulanka and Bhagyanka dignity scores.

    Args:
        mulanka_score: Dignity score for Mulanka planet (0-100)
        bhagyanka_score: Dignity score for Bhagyanka planet (0-100)
        mulanka_planet: Mulanka planet (optional, for labels)
        bhagyanka_planet: Bhagyanka planet (optional, for labels)
        use_plotly: Whether to use Plotly (interactive) or Matplotlib

    Returns:
        Plot object (Plotly figure or Matplotlib axes)
    """
    if use_plotly and PLOTLY_AVAILABLE:
        return _plot_comparison_plotly(
            mulanka_score, bhagyanka_score, mulanka_planet, bhagyanka_planet
        )
    else:
        return _plot_comparison_matplotlib(
            mulanka_score, bhagyanka_score, mulanka_planet, bhagyanka_planet
        )


def plot_natal_strength_comparison(
    chart: Any,
    mulanka_planet: Planet,
    bhagyanka_planet: Planet,
    use_plotly: bool = True,
) -> Any:
    """
    Create a detailed comparison of natal strength factors.

    Args:
        chart: BirthChart object with planetary data
        mulanka_planet: Mulanka ruling planet
        bhagyanka_planet: Bhagyanka ruling planet
        use_plotly: Whether to use Plotly (interactive) or Matplotlib

    Returns:
        Plot object (Plotly figure or Matplotlib axes)
    """
    # Extract planetary data
    mulanka_data = chart.planets.get(mulanka_planet.name, {})
    bhagyanka_data = chart.planets.get(bhagyanka_planet.name, {})

    if not mulanka_data or not bhagyanka_data:
        raise ValueError("Planetary data not found in chart")

    # Calculate various strength factors
    factors = _calculate_strength_factors(
        mulanka_data, bhagyanka_data, mulanka_planet, bhagyanka_planet
    )

    if use_plotly and PLOTLY_AVAILABLE:
        return _plot_strength_factors_plotly(factors, mulanka_planet, bhagyanka_planet)
    else:
        return _plot_strength_factors_matplotlib(
            factors, mulanka_planet, bhagyanka_planet
        )


def _plot_comparison_plotly(
    mulanka_score: float,
    bhagyanka_score: float,
    mulanka_planet: Optional[Planet],
    bhagyanka_planet: Optional[Planet],
) -> Any:
    """
    Create Plotly bar chart for Mulanka vs Bhagyanka comparison.

    Args:
        mulanka_score: Mulanka dignity score
        bhagyanka_score: Bhagyanka dignity score
        mulanka_planet: Mulanka planet
        bhagyanka_planet: Bhagyanka planet

    Returns:
        Plotly figure
    """
    # Prepare data
    categories = ["Mulanka", "Bhagyanka"]
    scores = [mulanka_score, bhagyanka_score]
    colors = [COMPARISON_COLORS["mulanka"], COMPARISON_COLORS["bhagyanka"]]

    # Create planet labels
    planet_labels = []
    if mulanka_planet:
        planet_labels.append(f"Mulanka ({mulanka_planet.name})")
    else:
        planet_labels.append("Mulanka")

    if bhagyanka_planet:
        planet_labels.append(f"Bhagyanka ({bhagyanka_planet.name})")
    else:
        planet_labels.append("Bhagyanka")

    # Create figure
    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=categories,
            y=scores,
            marker_color=colors,
            text=[f"{s:.1f}" for s in scores],
            textposition="auto",
            hovertemplate="<b>%{x}</b><br>"
            + "Planet: %{text}<br>"
            + "Score: %{y:.1f}/100<br>"
            + "<extra></extra>",
        )
    )

    # Add reference lines
    fig.add_hline(
        y=75,
        line_dash="dash",
        line_color="green",
        annotation_text="Strong Support",
        annotation_position="top right",
    )
    fig.add_hline(
        y=50,
        line_dash="dot",
        line_color="orange",
        annotation_text="Neutral",
        annotation_position="bottom right",
    )
    fig.add_hline(
        y=25,
        line_dash="dash",
        line_color="red",
        annotation_text="Weak Support",
        annotation_position="bottom right",
    )

    # Update layout
    title = "Numerological Planet Comparison"
    if mulanka_planet and bhagyanka_planet:
        title += f": {mulanka_planet.name} vs {bhagyanka_planet.name}"

    fig.update_layout(
        title=title,
        xaxis_title="Numerological Number",
        yaxis_title="Dignity Score (0-100)",
        yaxis_range=[0, 105],
        showlegend=False,
    )

    return fig


def _plot_comparison_matplotlib(
    mulanka_score: float,
    bhagyanka_score: float,
    mulanka_planet: Optional[Planet],
    bhagyanka_planet: Optional[Planet],
) -> plt.Axes:
    """
    Create Matplotlib bar chart for Mulanka vs Bhagyanka comparison.

    Args:
        mulanka_score: Mulanka dignity score
        bhagyanka_score: Bhagyanka dignity score
        mulanka_planet: Mulanka planet
        bhagyanka_planet: Bhagyanka planet

    Returns:
        Matplotlib axes
    """
    if SEABORN_AVAILABLE:
        sns.set_style("whitegrid")

    fig, ax = plt.subplots(figsize=(8, 6))

    # Data
    categories = ["Mulanka", "Bhagyanka"]
    scores = [mulanka_score, bhagyanka_score]
    colors = [COMPARISON_COLORS["mulanka"], COMPARISON_COLORS["bhagyanka"]]

    # Create bars
    bars = ax.bar(categories, scores, color=colors, alpha=0.7, width=0.6)

    # Add value labels on bars
    for bar, score in zip(bars, scores):
        height = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width() / 2.0,
            height + 1,
            f"{score:.1f}",
            ha="center",
            va="bottom",
            fontweight="bold",
        )

    # Add reference lines
    ax.axhline(
        y=75, color="green", linestyle="--", alpha=0.7, label="Strong Support (75+)"
    )
    ax.axhline(y=50, color="orange", linestyle=":", alpha=0.7, label="Neutral (50)")
    ax.axhline(y=25, color="red", linestyle="--", alpha=0.7, label="Weak Support (25-)")

    # Labels and title
    title = "Numerological Planet Comparison"
    if mulanka_planet and bhagyanka_planet:
        title += f": {mulanka_planet.name} vs {bhagyanka_planet.name}"

    ax.set_title(title, fontsize=14, fontweight="bold")
    ax.set_ylabel("Dignity Score (0-100)")
    ax.set_ylim(0, 105)

    # Add planet names as subtitle if available
    if mulanka_planet or bhagyanka_planet:
        planet_text = []
        if mulanka_planet:
            planet_text.append(f"Mulanka: {mulanka_planet.name}")
        if bhagyanka_planet:
            planet_text.append(f"Bhagyanka: {bhagyanka_planet.name}")
        ax.set_xlabel(", ".join(planet_text))

    ax.legend()
    plt.tight_layout()

    return ax


def _calculate_strength_factors(
    mulanka_data: Dict,
    bhagyanka_data: Dict,
    mulanka_planet: Planet,
    bhagyanka_planet: Planet,
) -> Dict[str, Dict]:
    """
    Calculate various strength factors for comparison.

    Args:
        mulanka_data: Planetary data for Mulanka planet
        bhagyanka_data: Planetary data for Bhagyanka planet
        mulanka_planet: Mulanka planet
        bhagyanka_planet: Bhagyanka planet

    Returns:
        Dictionary with strength factors for both planets
    """
    factors = {
        "Position": {
            "mulanka": 0,
            "bhagyanka": 0,
            "description": "Essential dignity (exaltation, etc.)",
        },
        "Direction": {
            "mulanka": 0,
            "bhagyanka": 0,
            "description": "Directional strength ( Kendra positions)",
        },
        "Temporal": {
            "mulanka": 0,
            "bhagyanka": 0,
            "description": "Time-based strength (day/night)",
        },
        "Motion": {
            "mulanka": 0,
            "bhagyanka": 0,
            "description": "Motion strength (retrograde bonus)",
        },
        "Combustion": {
            "mulanka": 0,
            "bhagyanka": 0,
            "description": "Combustion penalty (inverse)",
        },
    }

    # Position strength (simplified - would use full dignity calculation)
    # For now, use sign-based scoring
    mulanka_sign = mulanka_data.get("sign", 0)
    bhagyanka_sign = bhagyanka_data.get("sign", 0)

    # Rough position strength based on sign dignity
    factors["Position"]["mulanka"] = _estimate_position_strength(
        mulanka_planet, mulanka_sign
    )
    factors["Position"]["bhagyanka"] = _estimate_position_strength(
        bhagyanka_planet, bhagyanka_sign
    )

    # Directional strength (simplified)
    # Planets in angular houses (1,4,7,10) get higher scores
    mulanka_house = mulanka_data.get("house", 1)
    bhagyanka_house = bhagyanka_data.get("house", 1)

    angular_houses = [1, 4, 7, 10]
    factors["Direction"]["mulanka"] = 80 if mulanka_house in angular_houses else 40
    factors["Direction"]["bhagyanka"] = 80 if bhagyanka_house in angular_houses else 40

    # Temporal strength (simplified)
    # Sun, Jupiter, Venus strong during day; Moon, Mars, Saturn strong at night
    day_planets = [Planet.SUN, Planet.JUPITER, Planet.VENUS]
    night_planets = [Planet.MOON, Planet.MARS, Planet.SATURN]

    # Assume daytime for this example (would need actual time calculation)
    is_daytime = True  # This would be calculated from birth time

    if is_daytime:
        factors["Temporal"]["mulanka"] = 80 if mulanka_planet in day_planets else 40
        factors["Temporal"]["bhagyanka"] = 80 if bhagyanka_planet in day_planets else 40
    else:
        factors["Temporal"]["mulanka"] = 80 if mulanka_planet in night_planets else 40
        factors["Temporal"]["bhagyanka"] = (
            80 if bhagyanka_planet in night_planets else 40
        )

    # Motion strength
    mulanka_retrograde = mulanka_data.get("retrograde", False)
    bhagyanka_retrograde = bhagyanka_data.get("retrograde", False)

    factors["Motion"]["mulanka"] = 80 if mulanka_retrograde else 50
    factors["Motion"]["bhagyanka"] = 80 if bhagyanka_retrograde else 50

    # Combustion (inverse - lower combustion = higher score)
    mulanka_combust = mulanka_data.get("combust", False)
    bhagyanka_combust = bhagyanka_data.get("combust", False)

    factors["Combustion"]["mulanka"] = 20 if mulanka_combust else 80
    factors["Combustion"]["bhagyanka"] = 20 if bhagyanka_combust else 80

    return factors


def _estimate_position_strength(planet: Planet, sign: int) -> float:
    """
    Estimate positional strength based on planet and sign.

    Args:
        planet: Planet
        sign: Zodiac sign index

    Returns:
        Strength score (0-100)
    """
    from ..dignity.exaltation_matrix import (
        is_in_exaltation,
        is_in_moolatrikona,
        is_in_own_sign,
    )

    # Check dignity hierarchy
    longitude = sign * 30 + 15  # Midpoint of sign

    if is_in_exaltation(longitude, planet):
        return 100
    elif is_in_moolatrikona(longitude, planet):
        return 85
    elif is_in_own_sign(longitude, planet):
        return 75
    else:
        # Neutral/friend/enemy sign
        return 50


def _plot_strength_factors_plotly(
    factors: Dict[str, Dict], mulanka_planet: Planet, bhagyanka_planet: Planet
) -> Any:
    """
    Create Plotly radar chart for strength factors comparison.

    Args:
        factors: Strength factors data
        mulanka_planet: Mulanka planet
        bhagyanka_planet: Bhagyanka planet

    Returns:
        Plotly figure
    """
    # Prepare data for radar chart
    categories = list(factors.keys())
    mulanka_values = [factors[cat]["mulanka"] for cat in categories]
    bhagyanka_values = [factors[cat]["bhagyanka"] for cat in categories]

    # Close the radar chart
    mulanka_values.append(mulanka_values[0])
    bhagyanka_values.append(bhagyanka_values[0])
    categories_closed = categories + [categories[0]]

    # Create figure
    fig = go.Figure()

    fig.add_trace(
        go.Scatterpolar(
            r=mulanka_values,
            theta=categories_closed,
            fill="toself",
            name=f"Mulanka ({mulanka_planet.name})",
            line_color=COMPARISON_COLORS["mulanka"],
        )
    )

    fig.add_trace(
        go.Scatterpolar(
            r=bhagyanka_values,
            theta=categories_closed,
            fill="toself",
            name=f"Bhagyanka ({bhagyanka_planet.name})",
            line_color=COMPARISON_COLORS["bhagyanka"],
        )
    )

    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
        title=f"Strength Factors: {mulanka_planet.name} vs {bhagyanka_planet.name}",
        showlegend=True,
    )

    return fig


def _plot_strength_factors_matplotlib(
    factors: Dict[str, Dict], mulanka_planet: Planet, bhagyanka_planet: Planet
) -> plt.Axes:
    """
    Create Matplotlib radar chart for strength factors comparison.

    Args:
        factors: Strength factors data
        mulanka_planet: Mulanka planet
        bhagyanka_planet: Bhagyanka planet

    Returns:
        Matplotlib axes
    """
    # Prepare data
    categories = list(factors.keys())
    mulanka_values = [factors[cat]["mulanka"] for cat in categories]
    bhagyanka_values = [factors[cat]["bhagyanka"] for cat in categories]

    # Number of variables
    num_vars = len(categories)

    # Compute angle for each axis
    angles = [n / float(num_vars) * 2 * np.pi for n in range(num_vars)]
    angles += angles[:1]  # Close the plot

    # Values for closing the plot
    mulanka_values += mulanka_values[:1]
    bhagyanka_values += bhagyanka_values[:1]

    # Create figure
    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(projection="polar"))

    # Plot data
    ax.plot(
        angles,
        mulanka_values,
        "o-",
        linewidth=2,
        label=f"Mulanka ({mulanka_planet.name})",
        color=COMPARISON_COLORS["mulanka"],
    )
    ax.fill(angles, mulanka_values, alpha=0.25, color=COMPARISON_COLORS["mulanka"])

    ax.plot(
        angles,
        bhagyanka_values,
        "o-",
        linewidth=2,
        label=f"Bhagyanka ({bhagyanka_planet.name})",
        color=COMPARISON_COLORS["bhagyanka"],
    )
    ax.fill(angles, bhagyanka_values, alpha=0.25, color=COMPARISON_COLORS["bhagyanka"])

    # Fix axis to go in the right order and start at 12 o'clock
    ax.set_thetamin(0)
    ax.set_thetamax(360)

    # Set category labels
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(categories)

    # Set radial limits
    ax.set_ylim(0, 100)
    ax.set_yticks([20, 40, 60, 80, 100])
    ax.set_yticklabels(["20", "40", "60", "80", "100"])

    # Title and legend
    ax.set_title(
        f"Strength Factors: {mulanka_planet.name} vs {bhagyanka_planet.name}",
        size=14,
        fontweight="bold",
        pad=20,
    )
    ax.legend(loc="upper right", bbox_to_anchor=(1.2, 1.0))

    plt.tight_layout()

    return ax
