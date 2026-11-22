"""The stability check of ADR-006 section 3.4 (WP-51)."""

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from vedic_astrology_core.astrology.divisional import varga_sign
from vedic_astrology_core.mundane.registry import RegistryError, load_charts, load_events
from vedic_astrology_core.mundane.stability import (
    check,
    check_event,
    check_founding,
    event_half_window,
    founding_grid_minutes,
    founding_table_stability,
    stable_share,
    testable_by_stability,
    window_grid,
)
from vedic_astrology_core.rules.context import Location, Sky

UTC = timezone.utc
T0 = datetime(2000, 1, 1, 12, tzinfo=UTC)


@pytest.fixture(scope="module")
def charts():
    return {c.chart_id: c for c in load_charts()}


@pytest.fixture(scope="module")
def india(charts):
    return charts["in-1947-midnight"]


def _d9_lagna(chart, t):
    return varga_sign(Sky(t, Location(chart.lat, chart.lon, "UTC")).ascendant, 9)


def _next_d9_change(chart, start):
    a = start
    first = _d9_lagna(chart, a)
    b = a
    while _d9_lagna(chart, b) == first:
        b += timedelta(minutes=1)
    while b - a > timedelta(milliseconds=200):
        m = a + (b - a) / 2
        if _d9_lagna(chart, m) == first:
            a = m
        else:
            b = m
    return b


def _at_local(chart, instant):
    local = instant.astimezone(ZoneInfo(chart.time_zone)).replace(microsecond=0)
    return replace(chart, date=local.date(), valid_from=local.date(),
                   time=local.time().replace(tzinfo=None), half_window_minutes=2.0)


# ----------------------------------------------------------------- grid
def test_grid_has_ends_centre_and_small_steps():
    g = window_grid(T0, 2.5, 1.0)
    assert g[0] == T0 - timedelta(minutes=2.5) and g[-1] == T0 + timedelta(minutes=2.5)
    assert T0 in g
    assert all(b - a <= timedelta(minutes=1) for a, b in zip(g, g[1:]))
    assert window_grid(T0, 0) == [T0]
    with pytest.raises(ValueError):
        window_grid(datetime(2000, 1, 1), 2)


# ------------------------------------------------- the D9 lagna acceptance
def test_lagna_30_seconds_from_d9_boundary_is_caught(india):
    crossing = _next_d9_change(india, india.founding_instant())
    chart = _at_local(india, crossing - timedelta(seconds=30))
    assert chart.half_window == 2.0
    cells = founding_table_stability(chart, ["D1", "D9"])
    d9 = cells[("Lagna", "D9", "sign")]
    assert not d9.stable
    assert len(d9.values) == 2 and d9.alternatives
    assert abs((d9.change_points[0] - crossing).total_seconds()) <= 2
    shares = {v.value: v.share for v in d9.values}
    assert shares[d9.stated_value] == pytest.approx(150 / 240, abs=0.02)
    assert sum(shares.values()) == pytest.approx(1.0)
    # Every D9 house moves with the lagna; D1 lagna is far from its edge.
    assert not cells[("Sun", "D9", "house")].stable
    assert cells[("Lagna", "D1", "sign")].stable
    assert cells[("Saturn", "D1", "sign")].stable


def test_lagna_30_seconds_inside_but_window_shorter_is_stable(india):
    crossing = _next_d9_change(india, india.founding_instant())
    chart = _at_local(india, crossing - timedelta(seconds=30))
    s = check_founding(chart, lambda t: _d9_lagna(chart, t), half_window=0.25)
    assert s.stable and s.values[0].share == 1.0


# ----------------------------------------------------- generic behaviour
def test_value_held_for_one_minute_off_grid_is_caught():
    blip_start = T0 + timedelta(minutes=10, seconds=17)

    def f(t):
        return blip_start <= t < blip_start + timedelta(minutes=1)

    s = check(f, T0, 60, 1.0)
    assert not s.stable and s.stated_value is False
    shares = {v.value: v.share for v in s.values}
    assert shares[True] == pytest.approx(60 / 7200, abs=1 / 7200)
    assert len(s.change_points) == 2


def test_change_point_is_refined():
    edge = T0 + timedelta(minutes=7, seconds=33)
    s = check(lambda t: "after" if t >= edge else "before", T0, 15, 1.0)
    assert not s.stable
    assert abs((s.change_points[0] - edge).total_seconds()) <= 1
    assert [v.value for v in s.values] == ["before", "after"]
    assert s.values[0].share == pytest.approx((15 * 60 + 453) / 1800, abs=1 / 1800)


def test_constant_factor_is_stable_and_lists_freeze():
    s = check(lambda t: ["own", "friend"], T0, 30, 1.0)
    assert s.stable and s.stated_value == ("own", "friend") and s.alternatives == []


def test_window_edge_counts():
    """A change exactly at the window end is inside the window."""
    end = T0 + timedelta(minutes=5)
    s = check(lambda t: t >= end, T0, 5, 1.0)
    assert not s.stable


def test_naive_center_raises():
    with pytest.raises(ValueError):
        check(lambda t: 1, datetime(2000, 1, 1), 2)


# ------------------------------------------------------- chart behaviour
def test_grade_c_india_table(india):
    assert india.grade == "C" and founding_grid_minutes(india) == 1.0
    cells = founding_table_stability(india, ["D1", "D9"])
    assert not cells[("Lagna", "D1", "sign")].stable   # 60-minute window, section 3.3
    assert not cells[("Lagna", "D9", "sign")].stable
    assert cells[("Saturn", "D1", "sign")].stable
    assert cells[("Lagna", "D1", "sign")].stated_value == "Taurus"


def test_grade_d_uses_ten_minute_grid_and_has_no_lagna(charts):
    nepal = charts["np-2008-republic"]
    assert founding_grid_minutes(nepal) == 10.0
    cells = founding_table_stability(nepal, ["D1", "D9"])
    assert not any(k[0] == "Lagna" for k in cells)
    assert not any(k[2] == "house" for k in cells)
    assert not cells[("Moon", "D9", "sign")].stable   # 24-hour window
    s = cells[("Saturn", "D1", "sign")]
    assert s.stable and s.window[1] - s.window[0] == timedelta(hours=24)
    with pytest.raises(ValueError):
        founding_table_stability(nepal, ["D1"], step_minutes=30)


def test_lmt_chart_window_is_centred_on_local_mean_time(india):
    lmt = replace(india, time_zone="LMT")
    s = check_founding(lmt, lambda t: 0)
    centre = s.window[0] + (s.window[1] - s.window[0]) / 2
    assert centre == datetime(1947, 8, 15, tzinfo=UTC) - timedelta(hours=india.lon / 15)


def test_grade_x_refused(india):
    with pytest.raises(RegistryError):
        check_founding(replace(india, date_disputed=True), lambda t: 0)


# ------------------------------------------------------------ event side
def test_event_window():
    ev = load_events()[0]
    assert event_half_window(ev) == 1.0
    edge = ev.time_utc + timedelta(seconds=40)
    s = check_event(ev, lambda t: t >= edge)
    assert not s.stable
    with pytest.raises(RegistryError):
        event_half_window(replace(ev, time_precision="month"))
    assert event_half_window(replace(ev, time_precision="day")) == 720.0


# ------------------------------------------------------------- aggregate
def test_stable_share_and_threshold():
    assert stable_share([True] * 8 + [False] * 2) == 0.8
    assert testable_by_stability([True] * 8 + [False] * 2)
    assert not testable_by_stability([True] * 7 + [False] * 3)
    assert not testable_by_stability([])
    with pytest.raises(TypeError):
        stable_share([True, None])
