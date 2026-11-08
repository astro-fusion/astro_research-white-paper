"""Golden tests: combustion with per-planet Surya Siddhanta orbs."""

import pytest

from tests.golden import CHART_IDS, CHARTS
from vedic_astrology_core.astrology.ephemeris import EphemerisEngine
from vedic_astrology_core.config.constants import Planet

ENGINE_MEAN = EphemerisEngine(node_model="mean")


@pytest.mark.parametrize("chart", CHARTS, ids=CHART_IDS)
def test_combustion(chart):
    """Per-planet Surya Siddhanta orbs; the Sun and nodes are never combust."""
    positions = ENGINE_MEAN.get_all_planet_positions(chart["jd_ut"])
    combust = sorted(p.name for p, data in positions.items() if data["combust"])
    assert combust == sorted(chart["combust"]["expected"])
    for p in (Planet.SUN, Planet.RAHU, Planet.KETU):
        assert positions[p]["combust"] is False
