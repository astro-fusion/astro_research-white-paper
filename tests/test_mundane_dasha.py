"""Dasha at the event with founding-time boundary intervals (ADR-006 WP-51)."""

from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from vedic_astrology_core.dasha.vimshottari import (
    VIMSHOTTARI_SEQUENCE,
    compute_vimshottari_nested_periods,
    get_vimshottari_chain_at,
    get_vimshottari_start_lord,
)
from vedic_astrology_core.mundane.dasha import (
    DashaWindowError,
    dasha_at_event,
    expected_boundary_shift_days,
    moon_longitude_at,
    moon_speed_at,
)
from vedic_astrology_core.mundane.registry import (
    ChartNotApplicable,
    RegistryError,
    load_charts,
)

UTC = timezone.utc
EVENTS = [
    datetime(1950, 3, 1, 12, tzinfo=UTC),
    datetime(1991, 10, 19, 21, 23, tzinfo=UTC),
    datetime(2005, 10, 8, 3, 50, 38, tzinfo=UTC),
    datetime(2015, 4, 25, 6, 11, 25, tzinfo=UTC),
    datetime(2060, 1, 1, tzinfo=UTC),
]


@pytest.fixture(scope="module")
def charts():
    return {c.chart_id: c for c in load_charts()}


@pytest.fixture(scope="module")
def india(charts):
    return charts["in-1947-midnight"]


def _at(chart, minutes):
    """The chart with its founding time moved by minutes (UTC zone, to keep it exact)."""
    t = chart.founding_instant() + timedelta(minutes=minutes)
    return replace(chart, date=t.date(), valid_from=t.date(), time=t.timetz().replace(tzinfo=None),
                   time_zone="UTC")


@pytest.mark.parametrize("event", EVENTS)
def test_lords_and_boundaries_match_vimshottari(india, event):
    r = dasha_at_event(india, event)
    birth = india.founding_instant()
    moon = moon_longitude_at(birth)
    assert r.founding_moment == birth and r.moon_longitude == pytest.approx(moon)
    nested3 = compute_vimshottari_nested_periods(birth, moon, depth=3, total_years=130)
    chain = get_vimshottari_chain_at(event, nested3)
    assert tuple(lv.lord for lv in r.levels) == chain
    for n in (1, 2, 3):
        nested = compute_vimshottari_nested_periods(birth, moon, depth=n, total_years=130)
        p = next(p for p in nested if p["start"] <= event < p["end"])
        lv = r.level(n)
        assert lv.lords == chain[:n] == p["lords"]
        assert (lv.start, lv.end) == (p["start"], p["end"])
        assert lv.start_interval[0] <= lv.start <= lv.start_interval[1]
        assert lv.end_interval[0] <= lv.end <= lv.end_interval[1]
        assert lv.supported


@pytest.mark.parametrize("minutes", [1, 5, 15, -10])
def test_boundary_shift_follows_section_3_2(india, minutes):
    event = datetime(1999, 6, 1, tzinfo=UTC)
    base = dasha_at_event(india, event, half_window=0)
    moved = dasha_at_event(_at(india, minutes), event, half_window=0)
    expected = expected_boundary_shift_days(
        minutes, moon_speed_at(india.founding_instant()), base.first_lord
    )
    # Compare the same boundary: the end of the stated-time maha, shifted.
    birth = india.founding_instant()
    nested = compute_vimshottari_nested_periods(birth, base.moon_longitude, depth=3)
    t2 = birth + timedelta(minutes=minutes)
    nested2 = compute_vimshottari_nested_periods(t2, moon_longitude_at(t2), depth=3)
    later = {}
    for p in nested2:
        later.setdefault(p["lords"], p)
    for a in nested[5:60]:
        b = later[a["lords"]]
        actual = (a["start"] - b["start"]).total_seconds() / 86400.0
        assert actual * minutes > 0  # a later founding time moves boundaries earlier
        assert abs(abs(actual) - expected) <= 0.01 * expected
    assert base.first_lord == moved.first_lord


def test_uncertainty_matches_formula(india):
    r = dasha_at_event(india, datetime(2001, 1, 26, 3, 16, tzinfo=UTC), half_window=15)
    expected = expected_boundary_shift_days(
        15, moon_speed_at(india.founding_instant()), r.first_lord
    )
    for lv in r.levels:
        assert lv.boundary_uncertainty_days == pytest.approx(expected, rel=0.01)
        width = (lv.start_interval[1] - lv.start_interval[0]).total_seconds() / 86400
        assert width == pytest.approx(2 * expected, rel=0.01)


def test_event_inside_boundary_interval_is_unstable(india):
    base = dasha_at_event(india, datetime(2010, 1, 1, tzinfo=UTC), half_window=2)
    p3 = base.level(3)
    unc = p3.boundary_uncertainty_days
    assert 0 < unc < 20
    # Just after the stated pratyantar end: inside its end interval.
    event = p3.end + timedelta(days=unc / 2)
    r = dasha_at_event(india, event, half_window=2)
    lv = r.level(3)
    assert lv.end_interval[0] <= event <= lv.end_interval[1] or \
        lv.start_interval[0] <= event <= lv.start_interval[1]
    assert not lv.stable and "boundary interval" in lv.reason
    # Lords at the window ends straddle the boundary.
    assert lv.lords_at_window_ends[0] != lv.lords_at_window_ends[1]
    # Exactly on the interval edge counts as inside (conservative).
    edge = r.level(3).start_interval[1]
    assert not dasha_at_event(india, edge, half_window=2).level(3).stable


def test_mid_period_is_stable_and_coarser_levels_independent(india):
    # 0.1 minute moves boundaries by about half a day; the shortest pratyantar is 5.5 days.
    base = dasha_at_event(india, datetime(2010, 1, 1, tzinfo=UTC), half_window=0.1)
    p3 = base.level(3)
    assert p3.boundary_uncertainty_days < 1
    mid = p3.start + (p3.end - p3.start) / 2
    r = dasha_at_event(india, mid, half_window=0.1)
    assert all(lv.stable and lv.reason == "" for lv in r.levels)


def test_event_window_widens_the_event(india):
    base = dasha_at_event(india, datetime(2010, 1, 1, tzinfo=UTC), half_window=0.1)
    p3 = base.level(3)
    event = p3.end_interval[1] + timedelta(hours=6)
    assert dasha_at_event(india, event, half_window=0.1).level(3).stable
    widened = dasha_at_event(india, event, half_window=0.1, event_half_window_minutes=720)
    assert not widened.level(3).stable


def test_coarser_unstable_forces_finer_unstable(india):
    base = dasha_at_event(india, datetime(2010, 1, 1, tzinfo=UTC), half_window=60)
    md_end = base.level(1).end
    r = dasha_at_event(india, md_end, half_window=60)
    assert [lv.stable for lv in r.levels] == [False, False, False]


def test_stable_mark_agrees_with_dense_scan(india):
    """A level marked stable never changes lords anywhere in the window."""
    hw = 15
    birth = india.founding_instant()
    grid = [birth + timedelta(minutes=m) for m in range(-hw, hw + 1)]
    trees = [compute_vimshottari_nested_periods(t, moon_longitude_at(t), depth=3) for t in grid]
    start = datetime(1960, 1, 1, tzinfo=UTC)
    for k in range(60):
        event = start + timedelta(days=37 * k + 0.3)
        r = dasha_at_event(india, event, half_window=hw)
        chains = {get_vimshottari_chain_at(event, tree) for tree in trees}
        for lv in r.levels:
            prefixes = {c[: lv.level] for c in chains}
            if lv.stable:
                assert prefixes == {lv.lords}, (event, lv.level)
            elif len(prefixes) == 1:
                # Unstable without a change on the grid only when a boundary is in reach.
                assert "boundary interval" in lv.reason or "coarser" in lv.reason


def test_window_across_ashwini_start_does_not_jump(india):
    """The Moon crossing 0 deg (Revati to Ashwini) inside the window slides, not jumps."""
    t = datetime(2000, 1, 1, tzinfo=UTC)
    prev = moon_longitude_at(t)
    while True:
        t2 = t + timedelta(hours=2)
        cur = moon_longitude_at(t2)
        if cur < prev:
            break
        t, prev = t2, cur
    lo, hi = t, t2
    while hi - lo > timedelta(seconds=1):
        m = lo + (hi - lo) / 2
        if moon_longitude_at(m) > 180:
            lo = m
        else:
            hi = m
    crossing = hi.replace(microsecond=0)
    chart = replace(india, chart_id="in-test-ashwini", date=crossing.date(),
                    valid_from=crossing.date(), time=crossing.time(), time_zone="UTC")
    r = dasha_at_event(chart, datetime(2030, 5, 5, tzinfo=UTC), half_window=2)
    ends = r.level(1).lords_at_window_ends
    assert {get_vimshottari_start_lord(moon_longitude_at(crossing - timedelta(minutes=2))),
            get_vimshottari_start_lord(moon_longitude_at(crossing + timedelta(minutes=2)))} \
        == {"Mercury", "Ketu"}
    assert ends[0] == ends[1]
    assert r.level(1).boundary_uncertainty_days < 10


def test_grade_d_supports_no_level(charts):
    nepal = charts["np-2008-republic"]
    assert nepal.grade == "D"
    r = dasha_at_event(nepal, datetime(2015, 4, 25, 6, 11, tzinfo=UTC))
    assert len(r.levels) == 3
    for lv in r.levels:
        assert not lv.supported and not lv.stable
        assert lv.lord is None and lv.start is None and lv.start_interval is None
        assert "grade D" in lv.reason


def test_naive_datetime_raises(india):
    with pytest.raises(ValueError):
        dasha_at_event(india, datetime(2015, 4, 25, 6, 11))
    with pytest.raises(ValueError):
        moon_longitude_at(datetime(2015, 4, 25))


def test_refusals(india):
    with pytest.raises(ChartNotApplicable):
        dasha_at_event(india, datetime(1940, 1, 1, tzinfo=UTC))
    with pytest.raises(DashaWindowError):
        dasha_at_event(india, india.founding_instant() + timedelta(minutes=30))
    disputed = replace(india, date_disputed=True)
    with pytest.raises(RegistryError):
        dasha_at_event(disputed, datetime(2015, 1, 1, tzinfo=UTC))
    with pytest.raises(ValueError):
        dasha_at_event(india, datetime(2015, 1, 1, tzinfo=UTC), depth=4)


def test_local_time_zone_and_lmt(india):
    """IST and LMT founding times are converted before the Moon is read."""
    r = dasha_at_event(india, datetime(2015, 1, 1, tzinfo=UTC))
    assert r.founding_moment == datetime(1947, 8, 14, 18, 30, tzinfo=UTC)
    lmt = replace(india, time_zone="LMT")
    r2 = dasha_at_event(lmt, datetime(2015, 1, 1, tzinfo=UTC))
    offset = timedelta(hours=india.lon / 15.0)
    assert r2.founding_moment == datetime(1947, 8, 15, tzinfo=UTC) - offset
    assert r2.moon_longitude == pytest.approx(moon_longitude_at(r2.founding_moment))


def test_to_dict_is_json_ready(india):
    import json

    d = dasha_at_event(india, datetime(2015, 4, 25, 6, 11, tzinfo=UTC)).to_dict()
    json.dumps(d)
    assert [lv["level"] for lv in d["levels"]] == [1, 2, 3]
    assert set(VIMSHOTTARI_SEQUENCE) >= {lv["lord"] for lv in d["levels"]}
