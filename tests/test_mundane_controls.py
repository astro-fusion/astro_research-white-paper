"""C1 control dates and C3 placebo charts (ADR-006 WP-55)."""

from collections import namedtuple
from datetime import date, datetime, timedelta, timezone

import pytest

from vedic_astrology_core.mundane import burden as bd
from vedic_astrology_core.mundane import controls as ct
from vedic_astrology_core.mundane.registry import load_charts, load_events

UTC = timezone.utc
Ev = namedtuple("Ev", "event_id time_utc")


@pytest.fixture(scope="module")
def plan():
    return bd.load_plan()


@pytest.fixture(scope="module")
def events():
    return load_events()


@pytest.fixture(scope="module")
def india():
    return {c.chart_id: c for c in load_charts()}["in-1947-midnight"]


def _doy_dist(a: date, b: date) -> int:
    out = []
    for y in (a.year - 1, a.year, a.year + 1):
        try:
            out.append(abs((a - b.replace(year=y)).days))
        except ValueError:
            out.append(abs((a - date(y, 2, 28)).days))
    return min(out)


def test_select_events_explore_exhaustive_india(plan, events):
    sel = ct.select_events(events, plan, "explore")
    assert sel, "the registry has India mainshocks in the explore period"
    for e in sel:
        assert e.exhaustive and e.event_type == "earthquake"
        assert "IN" in ([e.country_iso] if isinstance(e.country_iso, str) else e.country_iso)
        assert date(1976, 1, 1) <= e.time_utc.date() <= date(2010, 12, 31)
        assert e.flags.get("mainshock_gk")


def test_c1_rules_hold_exactly(plan, events):
    sel = ct.select_events(events, plan)
    excl = ct.exclusion_events(events, plan)
    draw = ct.draw_season_matched(sel, plan, exclusion=excl)
    lo, hi = draw.period
    ex_times = [e.time_utc for e in excl]
    for e in sel:
        cs = draw.controls[e.event_id]
        assert len(cs) == 20 and draw.shortfall[e.event_id] == 0
        assert len(set(cs)) == 20                                   # no replacement
        for c in cs:
            assert c.year != e.time_utc.year                         # other years only
            assert _doy_dist(c.date(), e.time_utc.date()) <= 15       # season matched
            assert c.timetz() == e.time_utc.astimezone(UTC).timetz()  # same UTC time of day
            assert lo <= c.date() <= hi                               # same period
            assert min(abs((c - t).total_seconds()) for t in ex_times) >= 30 * 86400
            assert (c - datetime.combine(lo, datetime.min.time(), UTC)).days >= 30
            assert (datetime.combine(hi + timedelta(days=1), datetime.min.time(), UTC) - c).days >= 30


def test_c1_reproducible_from_seed_and_plan_hash(plan, events):
    sel = ct.select_events(events, plan)
    a = ct.draw_season_matched(sel, plan)
    b = ct.draw_season_matched(sel, plan)
    assert a.controls == b.controls
    other = bd.Plan(data=plan.data, sha256="f" * 64)
    c = ct.draw_season_matched(sel, other)
    assert c.controls != a.controls
    # One generator per cluster: an event whose admissible set is unchanged keeps its draw.
    d = ct.draw_season_matched(sel[1:], plan)
    for e in sel[1:]:
        if d.available[e.event_id] == a.available[e.event_id]:
            assert d.controls[e.event_id] == a.controls[e.event_id]


def test_confirm_events_cannot_shape_the_explore_draw(plan, events):
    sel = ct.select_events(events, plan)
    confirm_like = [Ev("usgs:fake-confirm", datetime(2011, 1, 10, 3, tzinfo=UTC)),
                    Ev("usgs:fake-confirm2", datetime(2015, 4, 25, 6, 11, tzinfo=UTC))]
    a = ct.draw_season_matched(sel, plan)
    b = ct.draw_season_matched(list(sel) + confirm_like, plan,
                               exclusion=list(sel) + confirm_like)
    assert a.controls == b.controls
    assert "usgs:fake-confirm" not in b.controls
    with pytest.raises(ct.ConfirmNotAvailable, match="WP-63"):
        ct.draw_season_matched(sel, plan, period="confirm")


def test_shortfall_recorded(plan, tmp_path):
    ev = [Ev("sim:a", datetime(1990, 6, 1, 12, tzinfo=UTC))]
    spec = ct.C1Spec(day_of_year_tolerance_days=5)
    draw = ct.draw_season_matched(ev, plan, spec=spec, bounds=(date(1989, 1, 1), date(1990, 12, 31)))
    assert 0 < len(draw.controls["sim:a"]) < 20
    assert draw.shortfall["sim:a"] == 20 - len(draw.controls["sim:a"])
    path = ct.write_controls(draw, plan, tmp_path)
    assert path.name == f"controls_{plan.sha12}.csv"
    man = path.with_suffix(".manifest.json").read_text()
    assert '"sim:a"' in man and '"shortfall"' in man


def test_clustered_events_move_together(plan):
    t0 = datetime(1995, 3, 10, 4, 30, tzinfo=UTC)
    ev = [Ev("sim:a", t0), Ev("sim:b", t0 + timedelta(days=9, hours=3))]
    draw = ct.draw_season_matched(ev, plan)
    assert draw.cluster_of["sim:a"] == draw.cluster_of["sim:b"] == "sim:a"
    for ca, cb in zip(draw.controls["sim:a"], draw.controls["sim:b"]):
        assert cb - ca == ev[1].time_utc - ev[0].time_utc
    far = [Ev("sim:a", t0), Ev("sim:c", t0 + timedelta(days=200))]
    d2 = ct.draw_season_matched(far, plan)
    assert d2.cluster_of["sim:c"] == "sim:c"


def test_leap_day_and_naive_times(plan):
    draw = ct.draw_season_matched([Ev("sim:leap", datetime(1996, 2, 29, 8, tzinfo=UTC))], plan)
    assert len(draw.controls["sim:leap"]) == 20
    with pytest.raises(ValueError, match="naive"):
        ct.draw_season_matched([Ev("sim:n", datetime(1996, 3, 1, 8))], plan)


def test_date_shift_placebos(plan, india):
    pl = ct.date_shift_placebos(india, plan)
    assert len(pl) == 99
    shifts = [ct.placebo_shift_days(p, india) for p in pl]
    assert len(set(shifts)) == 99
    assert all(30 <= abs(s) <= 3650 for s in shifts)
    assert any(s < 0 for s in shifts) and any(s > 0 for s in shifts)
    for p in pl:
        assert p.date < date(1976, 1, 1)
        assert (p.time, p.lat, p.lon, p.time_zone) == (india.time, india.lat, india.lon, india.time_zone)
        assert p.grade == india.grade
        assert (p.valid_from - p.date) == (india.valid_from - india.date)
    assert [p.date for p in ct.date_shift_placebos(india, plan)] == [p.date for p in pl]
    assert len({p.chart_id for p in pl}) == 99


def test_primary_chart_and_other_country(plan):
    charts = load_charts()
    assert ct.primary_chart(charts, "IN", plan).chart_id == plan["charts"]["expected_primary"]["chart_id"]
    india = ct.primary_chart(charts, "IN", plan)
    assert ct.other_country_placebos(charts, india, plan) == []      # disabled in the plan
    assert all(c.country_iso != "IN" for c in ct.other_country_placebos(charts, india, enabled=True))
