"""
Temporal Support Index Visualization

Creates time series graphs showing how numerological planetary support
changes over time (transits). Shows the relationship between static
numerology and dynamic astrological positions.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np

try:
    import seaborn as sns

    SEABORN_AVAILABLE = True
except ImportError:
    SEABORN_AVAILABLE = False

try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

from ..config.constants import Planet

# Default color zones for support levels
SUPPORT_COLORS = {
    "excellent": "#28a745",  # Green - >75
    "good": "#17a2b8",  # Blue - 50-75
    "neutral": "#ffc107",  # Yellow - 40-50
    "weak": "#fd7e14",  # Orange - 25-40
    "poor": "#dc3545",  # Red - <25
}


def plot_temporal_support(
    planet: Planet,
    start_date: datetime,
    end_date: datetime,
    latitude: float = 28.6139,
    longitude: float = 77.2090,
    baseline_score: Optional[float] = None,
    use_plotly: bool = True,
) -> Any:
    """
    Create a temporal support index graph showing planetary dignity over time.

    Args:
        planet: Planet to track (e.g., Planet.MARS for Mulanka 9)
        start_date: Start date for analysis
        end_date: End date for analysis
        latitude: Observer latitude (default: Delhi)
        longitude: Observer longitude (default: Delhi)
        baseline_score: Natal dignity score to show as reference line
        use_plotly: Whether to use Plotly (interactive) or Matplotlib

    Returns:
        Plot object (Plotly figure or Matplotlib axes)
    """
    # Generate time series data
    dates, scores = _calculate_temporal_scores(
        planet, start_date, end_date, latitude, longitude
    )

    if use_plotly and PLOTLY_AVAILABLE:
        return _plot_temporal_support_plotly(planet, dates, scores, baseline_score)
    else:
        return _plot_temporal_support_matplotlib(planet, dates, scores, baseline_score)


def _calculate_temporal_scores(
    planet: Planet,
    start_date: datetime,
    end_date: datetime,
    latitude: float,
    longitude: float,
) -> Tuple[List[datetime], List[float]]:
    """
    Calculate planetary dignity scores over a time period.

    Args:
        planet: Planet to analyze
        start_date: Analysis start date
        end_date: Analysis end date
        latitude: Observer latitude
        longitude: Observer longitude

    Returns:
        Tuple of (dates, scores) lists
    """
    from ..astrology import EphemerisEngine
    from ..dignity import DignityScorer

    # Initialize engines
    ephemeris = EphemerisEngine()
    scorer = DignityScorer()

    dates = []
    scores = []

    # Calculate daily scores (could be optimized for longer periods)
    current_date = start_date
    while current_date <= end_date:
        try:
            # Get planetary position for this date
            julian_day = ephemeris.datetime_to_julian_day(current_date)
            planet_data = ephemeris.get_planet_position(julian_day, planet.name.lower())

            # Calculate dignity score
            score = scorer.calculate_full_score(
                planet,
                planet_data["sign"],
                planet_data["longitude"],
                planet_data=planet_data,
            )

            dates.append(current_date)
            scores.append(score)

        except Exception as e:
            # Skip problematic dates
            pass

        current_date += timedelta(days=1)

    return dates, scores


def _plot_temporal_support_plotly(
    planet: Planet,
    dates: List[datetime],
    scores: List[float],
    baseline_score: Optional[float],
) -> go.Figure:
    """
    Create interactive Plotly temporal support graph.

    Args:
        planet: Planet being analyzed
        dates: List of dates
        scores: List of dignity scores
        baseline_score: Natal score for reference

    Returns:
        Plotly figure
    """
    # Create color zones based on scores
    colors = []
    for score in scores:
        if score > 75:
            colors.append(SUPPORT_COLORS["excellent"])
        elif score > 50:
            colors.append(SUPPORT_COLORS["good"])
        elif score > 40:
            colors.append(SUPPORT_COLORS["neutral"])
        elif score > 25:
            colors.append(SUPPORT_COLORS["weak"])
        else:
            colors.append(SUPPORT_COLORS["poor"])

    # Create figure
    fig = go.Figure()

    # Add main line
    fig.add_trace(
        go.Scatter(
            x=dates,
            y=scores,
            mode="lines+markers",
            name=f"{planet.name} Dignity",
            line=dict(color="black", width=2),
            marker=dict(color=colors, size=6),
            hovertemplate="<b>Date:</b> %{x}<br>"
            + f"<b>{planet.name} Score:</b> %{{y:.1f}}<br>"
            + "<extra></extra>",
        )
    )

    # Add baseline if provided
    if baseline_score is not None:
        fig.add_trace(
            go.Scatter(
                x=[dates[0], dates[-1]],
                y=[baseline_score, baseline_score],
                mode="lines",
                name="Natal Score",
                line=dict(color="red", width=2, dash="dash"),
                hovertemplate=f"<b>Natal Score:</b> {baseline_score:.1f}<extra></extra>",
            )
        )

    # Add support zones
    _add_support_zones_plotly(fig, dates)

    # Update layout
    fig.update_layout(
        title=f"Numerological Support: {planet.name} Dignity Over Time",
        xaxis_title="Date",
        yaxis_title="Dignity Score (0-100)",
        yaxis_range=[0, 105],
        showlegend=True,
        hovermode="x unified",
    )

    # Format x-axis dates
    fig.update_xaxes(tickformat="%Y-%m-%d", tickangle=45)

    return fig


def _plot_temporal_support_matplotlib(
    planet: Planet,
    dates: List[datetime],
    scores: List[float],
    baseline_score: Optional[float],
) -> plt.Axes:
    """
    Create Matplotlib temporal support graph.

    Args:
        planet: Planet being analyzed
        dates: List of dates
        scores: List of dignity scores
        baseline_score: Natal score for reference

    Returns:
        Matplotlib axes object
    """
    if SEABORN_AVAILABLE:
        sns.set_style("whitegrid")

    fig, ax = plt.subplots(figsize=(12, 6))

    # Add support zones
    _add_support_zones_matplotlib(ax, dates)

    # Plot main line
    ax.plot(
        dates,
        scores,
        "k-",
        linewidth=2,
        marker="o",
        markersize=4,
        markerfacecolor="white",
        markeredgewidth=1,
        label=f"{planet.name} Dignity",
    )

    # Add baseline if provided
    if baseline_score is not None:
        ax.axhline(
            y=baseline_score,
            color="red",
            linestyle="--",
            linewidth=2,
            label=f"Natal Score ({baseline_score:.1f})",
        )

    # Format axes
    ax.set_title(
        f"Numerological Support: {planet.name} Dignity Over Time",
        fontsize=14,
        fontweight="bold",
    )
    ax.set_xlabel("Date")
    ax.set_ylabel("Dignity Score (0-100)")
    ax.set_ylim(0, 105)
    ax.legend()

    # Format x-axis dates
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)

    plt.tight_layout()
    return ax


def _add_support_zones_plotly(fig: go.Figure, dates: List[datetime]) -> None:
    """Add colored support zones to Plotly figure."""
    date_range = [dates[0], dates[-1]]

    # Excellent zone (>75)
    fig.add_trace(
        go.Scatter(
            x=date_range + date_range[::-1],
            y=[75, 75, 105, 105],
            fill="toself",
            fillcolor=SUPPORT_COLORS["excellent"],
            opacity=0.1,
            line=dict(width=0),
            name="Excellent Support",
            showlegend=True,
        )
    )

    # Good zone (50-75)
    fig.add_trace(
        go.Scatter(
            x=date_range + date_range[::-1],
            y=[50, 50, 75, 75],
            fill="toself",
            fillcolor=SUPPORT_COLORS["good"],
            opacity=0.1,
            line=dict(width=0),
            name="Good Support",
            showlegend=True,
        )
    )

    # Neutral zone (40-50)
    fig.add_trace(
        go.Scatter(
            x=date_range + date_range[::-1],
            y=[40, 40, 50, 50],
            fill="toself",
            fillcolor=SUPPORT_COLORS["neutral"],
            opacity=0.15,
            line=dict(width=0),
            name="Neutral",
            showlegend=True,
        )
    )

    # Weak zone (25-40)
    fig.add_trace(
        go.Scatter(
            x=date_range + date_range[::-1],
            y=[25, 25, 40, 40],
            fill="toself",
            fillcolor=SUPPORT_COLORS["weak"],
            opacity=0.15,
            line=dict(width=0),
            name="Weak Support",
            showlegend=True,
        )
    )

    # Poor zone (<25)
    fig.add_trace(
        go.Scatter(
            x=date_range + date_range[::-1],
            y=[0, 0, 25, 25],
            fill="toself",
            fillcolor=SUPPORT_COLORS["poor"],
            opacity=0.15,
            line=dict(width=0),
            name="Poor Support",
            showlegend=True,
        )
    )


def _add_support_zones_matplotlib(ax: plt.Axes, dates: List[datetime]) -> None:
    """Add colored support zones to Matplotlib axes."""
    date_nums = mdates.date2num(dates)
    date_range = [date_nums[0], date_nums[-1]]

    # Excellent zone (>75)
    ax.fill_between(
        date_range,
        75,
        105,
        color=SUPPORT_COLORS["excellent"],
        alpha=0.1,
        label="Excellent",
    )

    # Good zone (50-75)
    ax.fill_between(
        date_range, 50, 75, color=SUPPORT_COLORS["good"], alpha=0.1, label="Good"
    )

    # Neutral zone (40-50)
    ax.fill_between(
        date_range, 40, 50, color=SUPPORT_COLORS["neutral"], alpha=0.15, label="Neutral"
    )

    # Weak zone (25-40)
    ax.fill_between(
        date_range, 25, 40, color=SUPPORT_COLORS["weak"], alpha=0.15, label="Weak"
    )

    # Poor zone (<25)
    ax.fill_between(
        date_range, 0, 25, color=SUPPORT_COLORS["poor"], alpha=0.15, label="Poor"
    )


def analyze_support_periods(
    dates: List[datetime], scores: List[float]
) -> Dict[str, Any]:
    """
    Analyze support periods from temporal data.

    Args:
        dates: List of dates
        scores: List of dignity scores

    Returns:
        Dictionary with period analysis
    """
    if not scores:
        return {"error": "No data to analyze"}

    # Calculate statistics
    avg_score = np.mean(scores)
    max_score = np.max(scores)
    min_score = np.min(scores)

    # Find best and worst periods
    best_idx = np.argmax(scores)
    worst_idx = np.argmin(scores)

    # Count days in each support level
    excellent_days = sum(1 for s in scores if s > 75)
    good_days = sum(1 for s in scores if 50 < s <= 75)
    neutral_days = sum(1 for s in scores if 40 <= s <= 50)
    weak_days = sum(1 for s in scores if 25 <= s < 40)
    poor_days = sum(1 for s in scores if s <= 25)

    total_days = len(scores)

    return {
        "statistics": {
            "average_score": avg_score,
            "max_score": max_score,
            "min_score": min_score,
            "best_date": dates[best_idx],
            "worst_date": dates[worst_idx],
        },
        "period_distribution": {
            "excellent": {
                "days": excellent_days,
                "percentage": excellent_days / total_days * 100,
            },
            "good": {"days": good_days, "percentage": good_days / total_days * 100},
            "neutral": {
                "days": neutral_days,
                "percentage": neutral_days / total_days * 100,
            },
            "weak": {"days": weak_days, "percentage": weak_days / total_days * 100},
            "poor": {"days": poor_days, "percentage": poor_days / total_days * 100},
        },
    }
