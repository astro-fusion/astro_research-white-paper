"""Golden tests: sidereal ascendant and house cusps against pyswisseph."""

import pytest

from tests.golden import ARCMIN, CHART_IDS, CHARTS, angle_diff, birth
from vedic_astrology_core.astrology.chart import calculate_chart


@pytest.mark.parametrize("chart", CHARTS, ids=CHART_IDS)
def test_ascendant_and_cusps(chart):
    """Sidereal ascendant within 1 arcminute; whole-sign by default."""
    bc = calculate_chart(birth(chart), chart["latitude"], chart["longitude"])
    assert bc.house_system == "W"
    assert angle_diff(bc.ascendant["longitude"], chart["ascendant"]) < ARCMIN
    for house, cusp in zip(bc.houses, chart["cusps_whole_sign"]):
        assert angle_diff(house["longitude"], cusp) < ARCMIN
    if chart["cusps_placidus"] is not None:
        bc_p = calculate_chart(
            birth(chart),
            chart["latitude"],
            chart["longitude"],
            house_system="placidus",
        )
        assert bc_p.house_system == "P"
        assert angle_diff(bc_p.ascendant["longitude"], chart["ascendant"]) < ARCMIN
        for house, cusp in zip(bc_p.houses, chart["cusps_placidus"]):
            assert angle_diff(house["longitude"], cusp) < ARCMIN
