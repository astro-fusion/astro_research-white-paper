"""
Temporal Comparison Visualization

Creates visualizations comparing numerology and Vedic astrology temporal patterns.
Demonstrates the fundamental difference between discrete numerological changes
and gradual astrological movements.
"""

from typing import Any, List, Optional, Union, cast

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

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
    go = Any  # type: ignore

from ..config.constants import PLANET_NAMES, Planet

# Color schemes for numerology vs astrology comparison
COMPARISON_COLORS = {
    "numerology": "#1f77b4",  # Blue - discrete/step-wise
    "astrology": "#ff7f0e",  # Orange - continuous/gradual
    "correlation": "#2ca02c",  # Green - correlation lines
    "moon_highlight": "#d62728",  # Red - moon movement emphasis
}

# Support level zones (same as support_index.py)
SUPPORT_COLORS = {
    "excellent": "#28a745",  # Green - >75
    "good": "#17a2b8",  # Blue - 50-75
    "neutral": "#ffc107",  # Yellow - 40-50
    "weak": "#fd7e14",  # Orange - 25-40
    "poor": "#dc3545",  # Red - <25
}


def plot_numerology_vs_astrology(
    data: Union[pd.DataFrame, str],
    planet: Planet,
    use_plotly: bool = True,
    save_path: Optional[str] = None,
) -> Any:
    """
    Create a comparison plot showing numerology vs astrology strength over time.

    This demonstrates the key difference: numerology changes in discrete steps
    when the date number changes, while astrology changes gradually.

    Args:
        data: DataFrame with temporal data or path to CSV file
        planet: Planet to analyze
        use_plotly: Whether to use Plotly (interactive) or Matplotlib
        save_path: Optional path to save the figure

    Returns:
        Plot object (Plotly figure or Matplotlib axes)
    """
    # Load data if path provided
    if isinstance(data, str):
        data = pd.read_csv(data)

    # Convert date column to datetime
    data["date"] = pd.to_datetime(data["date"])

    # Extract relevant columns
    num_col = f"numerology_{planet.name}"
    ast_col = f"astrology_{planet.name}"

    if num_col not in data.columns or ast_col not in data.columns:
        raise ValueError(f"Required columns not found: {num_col}, {ast_col}")

    # Filter to a reasonable time range (first 2 years for clarity)
    plot_data = data.head(730)  # ~2 years

    if use_plotly and PLOTLY_AVAILABLE:
        return _plot_comparison_plotly(plot_data, planet, num_col, ast_col, save_path)
    else:
        return _plot_comparison_matplotlib(
            plot_data, planet, num_col, ast_col, save_path
        )


def plot_all_planets_comparison(
    data: Union[pd.DataFrame, str],
    use_plotly: bool = True,
    save_path: Optional[str] = None,
) -> Any:
    """
    Create a comprehensive comparison showing all planets' numerology vs astrology.

    Args:
        data: DataFrame with temporal data or path to CSV file
        use_plotly: Whether to use Plotly (interactive) or Matplotlib
        save_path: Optional path to save the figure

    Returns:
        Plot object (Plotly figure or Matplotlib axes)
    """
    # Load data if path provided
    if isinstance(data, str):
        data = pd.read_csv(data)

    # Convert date column to datetime
    data["date"] = pd.to_datetime(data["date"])

    # Use first year for overview
    plot_data = data.head(365)

    if use_plotly and PLOTLY_AVAILABLE:
        return _plot_all_planets_plotly(plot_data, save_path)
    else:
        return _plot_all_planets_matplotlib(plot_data, save_path)


def plot_correlation_analysis(
    data: Union[pd.DataFrame, str],
    planets: Optional[List[Planet]] = None,
    use_plotly: bool = True,
    save_path: Optional[str] = None,
) -> Any:
    """
    Create correlation analysis plots showing the lack of relationship
    between numerology and astrology strength values.

    Args:
        data: DataFrame with temporal data or path to CSV file
        planets: List of planets to analyze (default: all)
        use_plotly: Whether to use Plotly (interactive) or Matplotlib
        save_path: Optional path to save the figure

    Returns:
        Plot object (Plotly figure or Matplotlib axes)
    """
    # Load data if path provided
    if isinstance(data, str):
        data = pd.read_csv(data)

    if planets is None:
        planets = [
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

    if use_plotly and PLOTLY_AVAILABLE:
        return _plot_correlation_plotly(data, planets, save_path)
    else:
        return _plot_correlation_matplotlib(data, planets, save_path)


def plot_moon_movement_highlight(
    data: Union[pd.DataFrame, str],
    use_plotly: bool = True,
    save_path: Optional[str] = None,
) -> Any:
    """
    Highlight the rapid moon movement in astrology vs numerology's date-based changes.

    The moon changes signs every ~2.5 days in astrology, while numerology
    only changes when the date number changes.

    Args:
        data: DataFrame with temporal data or path to CSV file
        use_plotly: Whether to use Plotly (interactive) or Matplotlib
        save_path: Optional path to save the figure

    Returns:
        Plot object (Plotly figure or Matplotlib axes)
    """
    # Load data if path provided
    if isinstance(data, str):
        data = pd.read_csv(data)

    # Convert date column to datetime
    data["date"] = pd.to_datetime(data["date"])

    # Focus on moon data and first 3 months for detail
    plot_data = data.head(90)  # ~3 months

    if use_plotly and PLOTLY_AVAILABLE:
        return _plot_moon_highlight_plotly(plot_data, save_path)
    else:
        return _plot_moon_highlight_matplotlib(plot_data, save_path)


def _plot_comparison_plotly(
    data: pd.DataFrame,
    planet: Planet,
    num_col: str,
    ast_col: str,
    save_path: Optional[str] = None,
) -> Any:
    """Create Plotly comparison plot for a single planet."""
    fig = go.Figure()

    # Add numerology line (step-wise)
    fig.add_trace(
        go.Scatter(
            x=data["date"],
            y=data[num_col],
            mode="lines",
            name=f"Numerology ({planet.name})",
            line=dict(color=COMPARISON_COLORS["numerology"], width=3),
            hovertemplate="<b>Date:</b> %{x}<br>"
            + f"<b>Numerology {planet.name}:</b> %{{y}}<br>"
            + "<extra></extra>",
        )
    )

    # Add astrology line (smooth)
    fig.add_trace(
        go.Scatter(
            x=data["date"],
            y=data[ast_col],
            mode="lines",
            name=f"Astrology ({planet.name})",
            line=dict(color=COMPARISON_COLORS["astrology"], width=2),
            hovertemplate="<b>Date:</b> %{x}<br>"
            + f"<b>Astrology {planet.name}:</b> %{{y:.1f}}<br>"
            + "<extra></extra>",
        )
    )

    # Add support zones
    _add_support_zones_plotly(fig, data["date"])

    # Update layout
    title = f"Numerology vs Astrology: {PLANET_NAMES[planet]} Strength Over Time"
    fig.update_layout(
        title=title,
        xaxis_title="Date",
        yaxis_title="Strength Score (0-100)",
        yaxis_range=[0, 105],
        showlegend=True,
        hovermode="x unified",
    )

    # Format x-axis
    fig.update_xaxes(tickformat="%Y-%m-%d", tickangle=45)

    if save_path:
        fig.write_html(save_path)

    return fig


def _plot_comparison_matplotlib(
    data: pd.DataFrame,
    planet: Planet,
    num_col: str,
    ast_col: str,
    save_path: Optional[str] = None,
) -> plt.Axes:
    """Create Matplotlib comparison plot for a single planet."""
    if SEABORN_AVAILABLE:
        sns.set_style("whitegrid")

    fig, ax = plt.subplots(figsize=(14, 8))

    # Add support zones background
    _add_support_zones_matplotlib(ax, data["date"])

    # Plot numerology (step-wise, thicker line)
    ax.plot(
        data["date"],
        data[num_col],
        "b-",
        linewidth=3,
        alpha=0.8,
        label=f"Numerology ({planet.name})",
        drawstyle="steps-post",
    )

    # Plot astrology (smooth, thinner line)
    ax.plot(
        data["date"],
        data[ast_col],
        "r-",
        linewidth=2,
        alpha=0.9,
        label=f"Astrology ({planet.name})",
    )

    # Formatting
    title = f"Numerology vs Astrology: {PLANET_NAMES[planet]} Strength Over Time"
    ax.set_title(title, fontsize=14, fontweight="bold")
    ax.set_xlabel("Date")
    ax.set_ylabel("Strength Score (0-100)")
    ax.set_ylim(0, 105)
    ax.legend(loc="upper right")
    ax.grid(True, alpha=0.3)

    # Format x-axis dates
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches="tight")

    return ax


def _plot_all_planets_plotly(
    data: pd.DataFrame, save_path: Optional[str] = None
) -> Any:
    """Create Plotly overview plot showing all planets."""
    planets = [
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

    # Create subplots - 3x3 grid for 9 planets
    fig = make_subplots(
        rows=3,
        cols=3,
        subplot_titles=[PLANET_NAMES[p] for p in planets],
        shared_xaxes=True,
        vertical_spacing=0.05,
    )

    for i, planet in enumerate(planets):
        row = (i // 3) + 1
        col = (i % 3) + 1

        num_col = f"numerology_{planet.name}"
        ast_col = f"astrology_{planet.name}"

        if num_col in data.columns and ast_col in data.columns:
            # Add numerology trace
            fig.add_trace(
                go.Scatter(
                    x=data["date"],
                    y=data[num_col],
                    mode="lines",
                    name=f"Num {planet.name}",
                    line=dict(color=COMPARISON_COLORS["numerology"], width=2),
                    showlegend=False,
                ),
                row=row,
                col=col,
            )

            # Add astrology trace
            fig.add_trace(
                go.Scatter(
                    x=data["date"],
                    y=data[ast_col],
                    mode="lines",
                    name=f"Ast {planet.name}",
                    line=dict(color=COMPARISON_COLORS["astrology"], width=1.5),
                    showlegend=False,
                ),
                row=row,
                col=col,
            )

    # Update layout
    fig.update_layout(
        title="Numerology vs Astrology: All Planets Comparison (1 Year)",
        height=900,
        showlegend=False,
    )

    # Update y-axes
    for i in range(1, 10):
        fig.update_yaxes(
            title_text="Strength",
            range=[0, 105],
            row=(i - 1) // 3 + 1,
            col=(i - 1) % 3 + 1,
        )

    if save_path:
        fig.write_html(save_path)

    return fig


def _plot_all_planets_matplotlib(
    data: pd.DataFrame, save_path: Optional[str] = None
) -> plt.Figure:
    """Create Matplotlib overview plot showing all planets."""
    planets = [
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

    fig, axes = plt.subplots(3, 3, figsize=(18, 12))
    axes = axes.flatten()

    for i, planet in enumerate(planets):
        ax = axes[i]
        num_col = f"numerology_{planet.name}"
        ast_col = f"astrology_{planet.name}"

        if num_col in data.columns and ast_col in data.columns:
            # Plot both lines
            ax.plot(
                data["date"],
                data[num_col],
                color=COMPARISON_COLORS["numerology"],
                linewidth=2,
                alpha=0.7,
                label="Numerology",
                drawstyle="steps-post",
            )
            ax.plot(
                data["date"],
                data[ast_col],
                color=COMPARISON_COLORS["astrology"],
                linewidth=1.5,
                alpha=0.8,
                label="Astrology",
            )

        ax.set_title(PLANET_NAMES[planet], fontsize=10)
        ax.set_ylim(0, 105)
        ax.grid(True, alpha=0.3)

        # Only show x-labels on bottom row
        if i >= 6:
            ax.set_xlabel("Date")
        else:
            ax.set_xticklabels([])

        # Only show y-labels on left column
        if i % 3 == 0:
            ax.set_ylabel("Strength")

    # Add legend to last plot
    axes[-1].legend(loc="upper right", fontsize=8)

    fig.suptitle(
        "Numerology vs Astrology: All Planets Comparison (1 Year)",
        fontsize=14,
        fontweight="bold",
    )
    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches="tight")

    return fig


def _plot_correlation_plotly(
    data: pd.DataFrame, planets: List[Planet], save_path: Optional[str] = None
) -> Any:
    """Create Plotly correlation analysis plot."""
    # Calculate correlations for each planet
    correlations = []
    for planet in planets:
        num_col = f"numerology_{planet.name}"
        ast_col = f"astrology_{planet.name}"

        if num_col in data.columns and ast_col in data.columns:
            corr = data[num_col].corr(data[ast_col])
            correlations.append(
                {
                    "planet": PLANET_NAMES[planet],
                    "correlation": corr,
                    "planet_enum": planet,
                }
            )

    # Sort by correlation strength
    correlations.sort(key=lambda x: abs(cast(float, x["correlation"])), reverse=True)

    # Create scatter plots for top correlations
    fig = make_subplots(
        rows=2,
        cols=2,
        subplot_titles=[
            f"{c['planet']} (r = {c['correlation']:.3f})" for c in correlations[:4]
        ],
        horizontal_spacing=0.1,
        vertical_spacing=0.1,
    )

    colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728"]

    for i, corr_data in enumerate(correlations[:4]):
        planet = cast(Planet, corr_data["planet_enum"])
        row = (i // 2) + 1
        col = (i % 2) + 1

        num_values = data[f"numerology_{planet.name}"]
        ast_values = data[f"astrology_{planet.name}"]

        fig.add_trace(
            go.Scatter(
                x=num_values,
                y=ast_values,
                mode="markers",
                name=corr_data["planet"],
                marker=dict(color=colors[i], size=4, opacity=0.6),
                showlegend=False,
            ),
            row=row,
            col=col,
        )

        # Add correlation line if meaningful
        if abs(cast(float, corr_data["correlation"])) > 0.1:
            # Simple linear fit
            coeffs = np.polyfit(num_values, ast_values, 1)
            line_x = np.linspace(num_values.min(), num_values.max(), 50)
            line_y = coeffs[0] * line_x + coeffs[1]

            fig.add_trace(
                go.Scatter(
                    x=line_x,
                    y=line_y,
                    mode="lines",
                    line=dict(color="red", width=2, dash="dash"),
                    showlegend=False,
                ),
                row=row,
                col=col,
            )

    fig.update_layout(
        title="Correlation Analysis: Numerology vs Astrology Strength",
        height=800,
        showlegend=False,
    )

    # Update axis labels
    for i in range(1, 5):
        fig.update_xaxes(
            title_text="Numerology Strength", row=(i - 1) // 2 + 1, col=(i - 1) % 2 + 1
        )
        fig.update_yaxes(
            title_text="Astrology Strength", row=(i - 1) // 2 + 1, col=(i - 1) % 2 + 1
        )

    if save_path:
        fig.write_html(save_path)

    return fig


def _plot_correlation_matplotlib(
    data: pd.DataFrame, planets: List[Planet], save_path: Optional[str] = None
) -> plt.Figure:
    """Create Matplotlib correlation analysis plot."""
    # Calculate correlations
    correlations = []
    for planet in planets:
        num_col = f"numerology_{planet.name}"
        ast_col = f"astrology_{planet.name}"

        if num_col in data.columns and ast_col in data.columns:
            corr = data[num_col].corr(data[ast_col])
            correlations.append((planet, corr))

    # Sort by correlation strength
    correlations.sort(key=lambda x: abs(x[1]), reverse=True)

    # Create 2x2 grid of scatter plots
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))

    for i, (planet, corr) in enumerate(correlations[:4]):
        ax = axes[i // 2, i % 2]

        num_values = data[f"numerology_{planet.name}"]
        ast_values = data[f"astrology_{planet.name}"]

        # Scatter plot
        ax.scatter(
            num_values,
            ast_values,
            alpha=0.6,
            s=20,
            color=COMPARISON_COLORS["correlation"],
        )

        # Add correlation line if significant
        if abs(corr) > 0.1:
            coeffs = np.polyfit(num_values, ast_values, 1)
            line_x = np.linspace(num_values.min(), num_values.max(), 50)
            line_y = coeffs[0] * line_x + coeffs[1]
            ax.plot(line_x, line_y, "r--", linewidth=2, alpha=0.8)

        ax.set_title(f"{PLANET_NAMES[planet]}\n(r = {corr:.3f})", fontsize=10)
        ax.set_xlabel("Numerology Strength")
        ax.set_ylabel("Astrology Strength")
        ax.grid(True, alpha=0.3)

    fig.suptitle(
        "Correlation Analysis: Numerology vs Astrology Strength",
        fontsize=14,
        fontweight="bold",
    )
    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches="tight")

    return fig


def _plot_moon_highlight_plotly(
    data: pd.DataFrame, save_path: Optional[str] = None
) -> Any:
    """Create Plotly moon movement highlight plot."""
    fig = go.Figure()

    # Moon astrology (rapid changes)
    fig.add_trace(
        go.Scatter(
            x=data["date"],
            y=data["astrology_MOON"],
            mode="lines",
            name="Astrology Moon",
            line=dict(color=COMPARISON_COLORS["moon_highlight"], width=3),
            hovertemplate="<b>Date:</b> %{x}<br>"
            + "<b>Astrology Moon:</b> %{y:.1f}<br>"
            + "<extra></extra>",
        )
    )

    # Moon numerology (discrete changes)
    moon_active_dates = data[data["numerology_active_planet"] == "MOON"]["date"]
    moon_strengths = data[data["numerology_active_planet"] == "MOON"]["numerology_MOON"]

    fig.add_trace(
        go.Scatter(
            x=moon_active_dates,
            y=moon_strengths,
            mode="markers+lines",
            name="Numerology Moon (Active Days)",
            line=dict(color=COMPARISON_COLORS["numerology"], width=4),
            marker=dict(size=8, color=COMPARISON_COLORS["numerology"]),
            hovertemplate="<b>Date:</b> %{x}<br>"
            + "<b>Numerology Moon:</b> %{y}<br>"
            + "<extra></extra>",
        )
    )

    # Highlight sign changes in astrology
    astrology_moon = data["astrology_MOON"]
    sign_changes = []
    for i in range(1, len(astrology_moon)):
        if (
            abs(astrology_moon.iloc[i] - astrology_moon.iloc[i - 1]) > 20
        ):  # Rough sign change indicator
            sign_changes.append(data["date"].iloc[i])

    # Add vertical lines for astrology sign changes
    for change_date in sign_changes[:10]:  # Limit for clarity
        fig.add_vline(x=change_date, line_dash="dot", line_color="red", opacity=0.7)

    fig.update_layout(
        title=(
            "Moon Movement: Astrology vs Numerology<br>"
            "<sub>Red dots: Astrology sign changes (~every 2.5 days) | "
            "Blue: Numerology active days</sub>"
        ),
        xaxis_title="Date (3 Months)",
        yaxis_title="Moon Strength (0-100)",
        yaxis_range=[0, 105],
        showlegend=True,
    )

    if save_path:
        fig.write_html(save_path)

    return fig


def _plot_moon_highlight_matplotlib(
    data: pd.DataFrame, save_path: Optional[str] = None
) -> plt.Axes:
    """Create Matplotlib moon movement highlight plot."""
    if SEABORN_AVAILABLE:
        sns.set_style("whitegrid")

    fig, ax = plt.subplots(figsize=(14, 8))

    # Moon astrology (rapid changes)
    ax.plot(
        data["date"],
        data["astrology_MOON"],
        "r-",
        linewidth=3,
        alpha=0.8,
        label="Astrology Moon (Continuous)",
        color=COMPARISON_COLORS["moon_highlight"],
    )

    # Moon numerology (discrete changes)
    moon_data = data[data["numerology_active_planet"] == "MOON"]
    ax.plot(
        moon_data["date"],
        moon_data["numerology_MOON"],
        "bo-",
        linewidth=4,
        markersize=8,
        alpha=0.9,
        label="Numerology Moon (Active Days)",
        color=COMPARISON_COLORS["numerology"],
    )

    # Highlight astrology sign changes
    astrology_moon = data["astrology_MOON"]
    for i in range(1, len(astrology_moon)):
        if abs(astrology_moon.iloc[i] - astrology_moon.iloc[i - 1]) > 20:
            ax.axvline(
                x=data["date"].iloc[i],
                color="red",
                linestyle="--",
                alpha=0.5,
                linewidth=1,
            )

    ax.set_title(
        "Moon Movement: Astrology vs Numerology\n"
        "Red lines: Astrology sign changes (~every 2.5 days) | "
        "Blue: Numerology active days",
        fontsize=14,
        fontweight="bold",
    )
    ax.set_xlabel("Date (3 Months)")
    ax.set_ylabel("Moon Strength (0-100)")
    ax.set_ylim(0, 105)
    ax.legend(loc="upper right")
    ax.grid(True, alpha=0.3)

    # Format x-axis
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
    ax.xaxis.set_major_locator(mdates.WeekdayLocator())
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches="tight")

    return ax


def _add_support_zones_plotly(fig: Any, dates: pd.Series) -> None:
    """Add colored support zones to Plotly figure."""
    date_range = [dates.min(), dates.max()]

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


def _add_support_zones_matplotlib(ax: plt.Axes, dates: pd.Series) -> None:
    """Add colored support zones to Matplotlib axes."""
    date_nums = mdates.date2num(dates)
    date_range = [date_nums.min(), date_nums.max()]

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
