"""Golden tests: three-level Vimshottari against PyJHora (virtual start)."""

import pytest

from tests.golden import CHART_IDS, CHARTS, FIXTURE, birth, jd_to_datetime
from vedic_astrology_core.dasha.vimshottari import compute_vimshottari_nested_periods


def _assert_dasha_matches(expected, birth, moon):
    """Compare every PyJHora start time with ours (1 day), per level.

    PyJHora lists the whole tree from the virtual start; periods that end
    before birth must be absent from ours, all others present.
    """
    starts = {}
    for depth in (1, 2, 3):
        for p in compute_vimshottari_nested_periods(
            birth, moon, depth=depth, total_years=120
        ):
            starts.setdefault(p["lords"], []).append(p["start"])
    compared = 0
    for key in ("level1", "level2", "level3_birth_md"):
        rows = expected[key]
        for i, (lords, start_jd) in enumerate(rows):
            start = jd_to_datetime(start_jd)
            ours = starts.get(tuple(lords), [])
            match = any(abs((s - start).total_seconds()) < 86400 for s in ours)
            end_jd = rows[i + 1][1] if i + 1 < len(rows) else None
            if end_jd is not None and jd_to_datetime(end_jd) <= birth:
                assert not match, f"{lords} ends before birth and must be dropped"
            else:
                assert match, (lords, start, ours)
                compared += 1
    assert compared >= 9


@pytest.mark.parametrize("chart", CHARTS, ids=CHART_IDS)
def test_vimshottari_chart(chart):
    """Three-level Vimshottari against PyJHora (virtual-start algorithm)."""
    moon = chart["bodies"]["MOON"]["longitude"]
    assert moon == pytest.approx(chart["dasha"]["moon_longitude_pyjhora"], abs=1e-6)
    _assert_dasha_matches(chart["dasha"], birth(chart), moon)


@pytest.mark.parametrize(
    "case",
    FIXTURE["dasha_random_moon"],
    ids=[f"moon{c['moon_longitude']:.3f}" for c in FIXTURE["dasha_random_moon"]],
)
def test_vimshottari_random_moon(case):
    """Random Moon longitudes, three levels, against PyJHora."""
    birth = jd_to_datetime(case["birth_jd_ut"])
    _assert_dasha_matches(case, birth, case["moon_longitude"])
