"""Golden tests: nakshatra/pada and the sixteen vargas against PyJHora."""

import pytest

from tests.golden import CHART_IDS, CHARTS, FIXTURE, point
from vedic_astrology_core.astrology.chart import get_nakshatra
from vedic_astrology_core.astrology.divisional import VARGA_FACTORS, varga_sign


@pytest.mark.parametrize("chart", CHARTS, ids=CHART_IDS)
def test_nakshatra_and_pada(chart):
    """Nakshatra (0-based) and pada match PyJHora for every point."""
    for key, expected in chart["nakshatra_pada"].items():
        lon = point(chart, key)
        nak = get_nakshatra(lon)
        assert (nak["index"], nak["pada"]) == (
            expected["nakshatra"],
            expected["pada"],
        ), key


@pytest.mark.parametrize("chart", CHARTS, ids=CHART_IDS)
def test_vargas_of_chart_points(chart):
    """All sixteen vargas match PyJHora's Parashari mapping exactly."""
    for varga, signs in chart["vargas"].items():
        factor = int(varga[1:])
        for key, expected in signs.items():
            lon = point(chart, key)
            assert varga_sign(lon, factor) == expected, (varga, key)


@pytest.mark.parametrize("varga", sorted(FIXTURE["varga_mid_points"]))
def test_varga_mid_points(varga):
    """Every part of every sign, sampled at its midpoint."""
    factor = int(varga[1:])
    assert factor in VARGA_FACTORS
    for lon, expected in FIXTURE["varga_mid_points"][varga]:
        assert varga_sign(lon, factor) == expected, lon
