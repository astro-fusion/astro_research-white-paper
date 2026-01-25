"""
Visualization API for `vedic_numerology`.

This module mostly re-exports functionality from `vedic_astrology_core.visualization`,
but keeps the import paths used by docs intact.
"""

from __future__ import annotations

from typing import Any, Optional, Union

import pandas as pd

from vedic_astrology_core.config.constants import Planet
from vedic_astrology_core.visualization.support_index import plot_temporal_support
from vedic_astrology_core.visualization.radar_charts import plot_planetary_strength_numerology
from vedic_astrology_core.visualization.temporal_comparison import (
    plot_all_planets_comparison,
    plot_correlation_analysis,
    plot_moon_movement_highlight,
    plot_numerology_vs_astrology,
)


def plot_numerology_comparison(
    data: Union[pd.DataFrame, str],
    planet: Planet,
    use_plotly: bool = True,
    save_path: Optional[str] = None,
) -> Any:
    return plot_numerology_vs_astrology(
        data=data, planet=planet, use_plotly=use_plotly, save_path=save_path
    )


def plot_dignity_analysis(*args: Any, **kwargs: Any) -> Any:  # pragma: no cover
    # Backwards-compatible name: this is provided by vedic_astrology_core via VedicAstrologyChart.
    from vedic_astrology_core.visualization.radar_charts import plot_dignity_radar

    return plot_dignity_radar(*args, **kwargs)


def create_support_index_chart(*args: Any, **kwargs: Any) -> Any:  # pragma: no cover
    # Compatibility shim for docs. If you need a stable API here, we can formalize it.
    return plot_temporal_support(*args, **kwargs)


__all__ = [
    "plot_temporal_support",
    "plot_numerology_comparison",
    "plot_all_planets_comparison",
    "plot_correlation_analysis",
    "plot_moon_movement_highlight",
    "plot_dignity_analysis",
    "create_support_index_chart",
]
