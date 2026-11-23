"""Season-matched controls and baselines (ADR-008 WP-87, section 6).

Covers section 6.1 items 1 to 6 and the fast subset of the proof cases of
section 6.3 (Z1 to Z6). The full-size cases (10,000 replications per cell)
run in the certificate suite (WP-98) through the `run_z*` functions below;
set `ASTRO_CALIBRATE_FULL=1` to run them here. The Z cases have no fast mark
in the case registry, so the fast subset here uses the section 1.3 fast mark
(observed rate at or below 0.085 over 400 replications).
"""

import inspect
import os

import numpy as np
import pandas as pd
import pytest

from tests import simulators as sim
from vedic_astrology_core.stats import blocks as B
from vedic_astrology_core.stats import season as S
from vedic_astrology_core.validity import calibration as cal

FULL = os.environ.get("ASTRO_CALIBRATE_FULL") == "1"
BASE_SEED = 20261122
FAST_REPS = 400
FAST_RATE = 0.085
ALPHA = 0.05
N_DRAWS = 999
DAILY = ("mercury_retrograde", "venus_combust", "moon_nakshatra_group", "tithi_group",
         "sun_nakshatra", "sun_sign", "eclipse_window")
SUN_LINKED = ("sun_sign", "sun_nakshatra")
YEARLY = ("rahu_in_aries", "rahu_in_libra", "jupiter_in_cancer", "saturn_in_aries",
          "saturn_in_libra", "saturn_in_capricorn")


@pytest.fixture(scope="module")
def daily():
    return sim.daily_calendars()


@pytest.fixture(scope="module")
def yearly():
    return sim.yearly_calendars()


def _yearly_dates(years):
    return pd.DatetimeIndex([pd.Timestamp(int(y), 6, 1) for y in years])


def _box(dates, spans):
    """Calendar active on the given (start, end) date pairs, inclusive."""
    c = np.zeros(len(dates), dtype=bool)
    for a, b in spans:
        c |= (dates >= pd.Timestamp(a)) & (dates <= pd.Timestamp(b))
    return c


# ---------------------------------------------------------------- item 1
def test_season_r2_measure_and_threshold(daily):
    dates = daily.index
    assert S.season_r2(np.zeros(len(dates), dtype=bool), dates) == 0.0
    r_sign = S.season_r2(daily["sun_sign"].to_numpy(), dates)
    r_nak = S.season_r2(daily["sun_nakshatra"].to_numpy(), dates)
    r_merc = S.season_r2(daily["mercury_retrograde"].to_numpy(), dates)
    assert r_sign > 0.4 and r_nak > 0.15
    assert r_merc < 0.01
    assert S.is_season_linked(r_nak) and not S.is_season_linked(r_merc)
    assert S.is_season_linked(S.SEASON_LINKED_R2)  # the threshold is inclusive
    # A pure yearly sine calendar is fully explained.
    doy = dates.day_of_year.to_numpy(float)
    assert S.season_r2(np.sin(2 * np.pi * doy / 365.25) > 0, dates) > 0.75
    # One bar per year: the harmonics are (all but) constant, nothing is explained
    # (leap years move June 1 by one day of year).
    yrs = np.arange(1900, 1950)
    assert S.season_r2(yrs % 3 == 0, _yearly_dates(yrs)) < 0.01
    # Microsecond-unit dates give the same design as nanosecond ones.
    d_us = pd.DatetimeIndex(dates).as_unit("us")
    c = daily["sun_nakshatra"].to_numpy()
    assert (S.control_design(c, d_us, merge_gap=0).blocks.design_id
            == S.control_design(c, dates, merge_gap=0).blocks.design_id)
    with pytest.raises(ValueError, match="dates"):
        S.season_r2(np.zeros(10, dtype=bool))


def test_series_index_supplies_dates(daily):
    s = daily["sun_sign"]
    assert S.season_r2(s) == S.season_r2(s.to_numpy(), s.index)


# ---------------------------------------------------------------- item 2
def test_neighbour_blocks_for_calendars_not_season_linked(daily):
    c = daily["mercury_retrograde"].to_numpy()
    d = S.control_design(c, daily.index, merge_gap=0)
    assert not d.season_linked and d.control_kind == "neighbours"
    assert d.blocks.design_id == B.build_blocks(c, merge_gap=0).design_id
    assert d.untestable_reason is None and d.placebo_shift == "random_offset"


def test_same_season_windows_equal_size_same_day_of_year():
    dates = pd.date_range("2000-01-01", "2009-12-31", freq="D")
    c = _box(dates, [("2004-03-01", "2004-03-10")])
    d = S.season_design(c, dates, merge_gap=0)
    (b,) = d.blocks.blocks
    (w,) = d.windows
    assert b.used and w.left_years == -1 and w.right_years == 1
    assert b.n_control == b.n_active == 10  # Amendment A1: equal size
    assert len(b.control_left) == len(b.control_right) == 5
    assert set(dates[b.control_left].year) == {2003}
    assert set(dates[b.control_right].year) == {2005}
    md = lambda ix: set(zip(dates[ix].month, dates[ix].day))
    assert md(b.control) == md(b.active)  # each control bar has an active twin


def test_ninety_percent_rule_and_reserved_spans():
    dates = pd.date_range("2000-01-01", "2009-12-31", freq="D")
    # Episode A (2003-03-02..03) is served first and reserves its spans in
    # 2002 and 2005; episode B (2004-03-01..10) then finds 2003 and 2002 at
    # 80% usable and goes to 2001, and 2005 at 80% and goes to 2006.
    c = _box(dates, [("2003-03-02", "2003-03-03"), ("2004-03-01", "2004-03-10")])
    d = S.season_design(c, dates, merge_gap=0)
    wa, wb = d.windows
    assert (wa.left_years, wa.right_years) == (-1, 2)
    assert (wb.left_years, wb.right_years) == (-3, 2)
    assert all(b.used for b in d.blocks.blocks)
    ba, bb = d.blocks.blocks
    assert not set(ba.control.tolist()) & set(bb.control.tolist())


def test_no_window_drops_block_and_edge_uses_one_side():
    dates = pd.date_range("2000-01-01", "2009-12-31", freq="D")
    # Active on the same days every year: no same-season span is free.
    c = _box(dates, [(f"{y}-04-14", f"{y}-05-13") for y in range(2000, 2010)])
    d = S.season_design(c, dates, merge_gap=0)
    assert d.blocks.n_used == 0
    assert d.season_drop_counts[S.DROP_NO_SEASON_WINDOW] == 10
    assert d.blocks.drop_counts[B.DROP_NO_CONTROL] == 10
    # First year of the grid: no earlier year exists, the later one serves alone.
    c2 = _box(dates, [("2000-06-01", "2000-06-08")])
    (b,) = S.season_design(c2, dates, merge_gap=0).blocks.blocks
    assert b.used and not b.left_exists and len(b.control_right) == 8


def test_unmatched_active_bar_drops_block_as_unbalanced():
    dates = pd.date_range("2000-01-01", "2009-12-31", freq="D")
    c = _box(dates, [("2004-03-01", "2004-03-20")])
    avail = np.ones(len(dates), dtype=bool)
    # 2003-03-05 and 2005-03-05 carry no outcome (spans stay 95% usable), so
    # the active bar 2004-03-05 has no twin in either year.
    avail[dates.get_indexer(pd.DatetimeIndex(["2003-03-05", "2005-03-05"]))] = False
    d = S.season_design(c, dates, merge_gap=0, available=avail)
    assert d.windows[0].reason == S.DROP_UNBALANCED and d.blocks.n_used == 0


def test_business_day_grid_matches_within_three_days():
    dates = pd.bdate_range("2000-01-03", "2009-12-31")
    c = _box(dates, [("2004-03-01", "2004-03-12")])
    d = S.season_design(c, dates, merge_gap=0)
    (b,) = d.blocks.blocks
    assert b.used and b.n_control == b.n_active
    gaps = [min(abs((dates[x] - (dates[a] + pd.DateOffset(years=s))).days)
                for a in b.active for s in (-1, 1)) for x in b.control]
    assert max(gaps) <= S.MAX_MATCH_DAYS


def test_random_season_designs_are_disjoint_and_equal_size():
    rng = np.random.default_rng(cal.case_seed(BASE_SEED, "season-property"))
    dates = pd.date_range("1990-01-01", "2005-12-31", freq="D")
    for _ in range(25):
        c = np.zeros(len(dates), dtype=bool)
        for y in range(1990, 2006):
            if rng.random() < 0.6:
                s = int(rng.integers(0, 330))
                c[(dates.year == y) & (dates.day_of_year >= s)
                  & (dates.day_of_year < s + int(rng.integers(1, 30)))] = True
        d = S.season_design(c, dates, merge_gap=int(rng.integers(0, 3)))  # raises if shared
        owner = {}
        for b in d.blocks.used_blocks:
            assert b.n_control == b.n_active
            for x in np.concatenate([b.active, b.control]).tolist():
                assert x not in owner
                owner[x] = b.number
            assert not c[b.control].any()


def test_sun_sign_is_season_linked_and_untestable(daily):
    d = S.control_design(daily["sun_sign"].to_numpy(), daily.index, merge_gap=0)
    assert d.season_linked and d.control_kind == "season_windows"
    assert d.blocks.n_used == 0
    assert d.untestable_reason == S.SEASON_REASON
    s = d.summary()
    assert s["season_r2"] == d.season_r2 and s["untestable_reason"] == S.SEASON_REASON


# ---------------------------------------------------------------- item 3
def test_whole_year_shifts_keep_the_season():
    ks = S.whole_year_shifts()
    assert len(ks) == 200 and 0 not in ks and min(ks) == -100 and max(ks) == 100
    dates = pd.DatetimeIndex(["2000-02-29", "2001-04-14", "1999-12-31"])
    moved = S.shifted_instants(dates, 3)
    assert list(moved.strftime("%Y-%m-%d")) == ["2003-02-28", "2004-04-14", "2002-12-31"]
    with pytest.raises(ValueError):
        S.shifted_instants(dates, 0)
    assert S.placebo_shift_kind(True) == "whole_year"
    assert S.placebo_shift_kind(False) == "random_offset"


# ---------------------------------------------------------------- item 4
def test_leave_year_out_spike_and_centred_mean():
    years = np.arange(1901, 1951)
    y = np.full(len(years), 100.0)
    y[years == 1930] += 25.0
    a = S.leave_year_out_anomaly(y, years, by="year")
    assert a[years == 1930][0] == pytest.approx(25.0)
    old = y - y.mean()  # centred mean with the tested year inside
    assert old[years == 1930][0] < 25.0
    # Running mean without the year itself.
    w = S.leave_year_out_anomaly(y, years, by="year", window=11)
    assert w[years == 1930][0] == pytest.approx(25.0)
    assert w[years == 1931][0] == pytest.approx(-2.5)  # 1930 is one of its 10 neighbours


def test_leave_year_out_day_of_year_and_month():
    dates = pd.date_range("1990-01-01", "1999-12-31", freq="D")
    season = np.sin(2 * np.pi * (dates.month.to_numpy() * 31 + dates.day.to_numpy()) / 372.0)
    y = season.copy()
    y[dates.year == 1995] += 2.0
    a = S.leave_year_out_anomaly(y, dates, by="doy")
    inside = (dates.year == 1995) & ~((dates.month == 2) & (dates.day == 29))
    assert np.allclose(a[inside], 2.0)
    m = S.leave_year_out_anomaly(np.where(dates.month == 7, 5.0, 1.0), dates, by="month")
    assert np.allclose(m, 0.0)
    y2 = y.copy()
    y2[10] = np.nan
    a2 = S.leave_year_out_anomaly(y2, dates, by="doy")
    assert np.isnan(a2[10]) and np.isfinite(a2[11])
    with pytest.raises(ValueError):
        S.leave_year_out_anomaly(y, dates, by="week")


# ---------------------------------------------------------------- item 5
def test_baseline_r2_and_r4():
    rng = np.random.default_rng(3)
    n = 500
    x = rng.normal(size=n)
    c = x > 0.5
    assert S.baseline_r2(c, {"x": x}) > 0.4
    assert S.baseline_r2(c, pd.DataFrame({"x": (x > 0.5).astype(float)})) == pytest.approx(1.0)
    assert S.baseline_r2(c, rng.normal(size=(n, 2))) < 0.05
    assert S.r4_passes(0.4999) and not S.r4_passes(0.5) and not S.r4_passes(0.9)
    with pytest.raises(ValueError):
        S.baseline_r2(c, np.ones(n - 1))


# ---------------------------------------------------------------- item 6
def test_nodal_baseline_tracks_the_node(yearly):
    years = yearly.index.to_numpy()
    nb = S.nodal_baseline(years)
    assert nb.shape == (len(years), 2 * S.NODAL_HARMONICS)
    lon = np.radians(yearly["rahu_longitude"].to_numpy())
    X = np.column_stack([np.ones(len(years)), nb.to_numpy()])
    for target in (np.cos(lon), np.sin(lon)):
        coef, *_ = np.linalg.lstsq(X, target, rcond=None)
        res = target - X @ coef
        assert 1 - res.var() / target.var() > 0.999
    daily_t = S.decimal_years(pd.DatetimeIndex(["2000-01-01", "2000-07-02"]))
    assert daily_t[0] == 2000.0 and 2000.49 < daily_t[1] < 2000.51


def test_solar_cycle_smoothing():
    s = np.full(40, 7.0)
    assert np.allclose(S.solar_cycle_baseline(s), 7.0)
    x = np.zeros(40)
    x[20] = 24.0
    sm = S.solar_cycle_baseline(x)
    assert sm[20] == pytest.approx(2.0)  # weight 1/12 in the middle
    assert sm[14] == pytest.approx(1.0) and sm[26] == pytest.approx(1.0)  # half weight at +-6
    assert sm[13] == 0.0 and sm[27] == 0.0
    with pytest.raises(ValueError):
        S.solar_cycle_baseline(x, window=12)


def test_physical_baseline_domains():
    for dom in ("monsoon", "flood", "earthquake"):
        assert S.requires_physical_baselines(dom)
    assert not S.requires_physical_baselines("gold")
    years = np.arange(1950, 2000)
    pb = S.physical_baselines(years, sunspots=np.linspace(0, 100, len(years)))
    assert "solar_cycle" in pb.columns and pb.shape[1] == 2 * S.NODAL_HARMONICS + 1
    with pytest.raises(ValueError):
        S.physical_baselines(years, sunspots=np.ones(3))


def test_remove_baselines():
    rng = np.random.default_rng(4)
    b = rng.normal(size=300)
    noise = rng.normal(size=300)
    y = 3.0 * b + noise + 10.0
    y[5] = np.nan
    r = S.remove_baselines(y, {"b": b})
    assert np.isnan(r[5])
    assert abs(np.corrcoef(r[np.isfinite(r)], b[np.isfinite(r)])[0, 1]) < 1e-8
    assert np.nanmean(r) == pytest.approx(np.nanmean(y))


# ---------------------------------------------------------------- Z5 and spy
def test_z5_sun_in_sign_untestable_without_reading_an_outcome(daily, monkeypatch):
    for fn in (S.control_design, S.season_design):
        assert "outcome" not in inspect.signature(fn).parameters
    reads = []
    real = B._outcome_values

    def spy(*a, **k):
        reads.append(1)
        return real(*a, **k)

    monkeypatch.setattr(B, "_outcome_values", spy)
    d = S.control_design(daily["sun_sign"].to_numpy(), daily.index, merge_gap=0)
    d.summary()
    d.blocks.gate_summary("greater")
    assert reads == []
    assert d.untestable_reason == S.SEASON_REASON and d.blocks.n_used == 0
    cal.property_result("Z5", "sun_sign daily 1968-1998", True)


# ---------------------------------------------------------------- Z runners
def _rejections(design, draw, reps, seed, outcome_type="continuous", alternative="greater",
                transform=None):
    """Rejections at one-sided 5% of the primary test, no calendar effect planted."""
    if design.n_used == 0:
        return 0  # Untestable: never supports
    rng = np.random.default_rng(seed)
    hits = 0
    for _ in range(int(reps)):
        y = draw(rng)
        if transform is not None:
            y = transform(y)
        r = B.primary_test(design, y, alternative=alternative, outcome_type=outcome_type,
                           rng=rng, n_draws=N_DRAWS)
        hits += r.p_value <= ALPHA
    return hits


def _result(case, cell, hits, reps, fast):
    if fast:
        return (case, cell, hits, reps, hits / reps <= FAST_RATE)
    r = cal.evaluate(case, cell, hits, reps)
    return (case, cell, hits, reps, r.passed)


def run_z1(reps, fast=False, names=DAILY, sides=("greater", "less")):
    frame = sim.daily_calendars()
    dates = frame.index
    # As the pipeline does for a daily outcome: anomaly, then the A2 detrending.
    loo = lambda y: S.centred_detrend(S.leave_year_out_anomaly(y, dates, by="doy"), DETREND_WINDOW)
    out = []
    for name in names:
        d = S.control_design(frame[name].to_numpy(), dates, merge_gap=0, side_seed=BASE_SEED).blocks
        for side in sides:
            cell = f"{name} {side}"
            hits = _rejections(d, lambda rng: sim.seasonal_daily(dates, rng), reps,
                               cal.case_seed(BASE_SEED, "Z1", cell), alternative=side,
                               transform=loo)
            out.append(_result("Z1", cell, hits, reps, fast))
    return out


def run_z2(reps, fast=False, names=DAILY, parent_rate=0.05):
    frame = sim.daily_calendars()
    dates = frame.index
    mult = sim.season_multiplier(dates)
    draw = lambda rng: sim.neyman_scott(len(dates), rng, parent_rate, multiplier=mult)["counts"].astype(float)
    out = []
    for name in names:
        d = S.control_design(frame[name].to_numpy(), dates, merge_gap=0, side_seed=BASE_SEED).blocks
        hits = _rejections(d, draw, reps, cal.case_seed(BASE_SEED, "Z2", name), outcome_type="events")
        out.append(_result("Z2", name, hits, reps, fast))
    return out


def run_z3(reps, fast=False, names=YEARLY):
    frame = sim.yearly_calendars()
    years = frame.index.to_numpy()
    dates = _yearly_dates(years)
    out = []
    for name in names:
        d = S.control_design(frame[name].to_numpy(), dates, merge_gap=0, side_seed=BASE_SEED).blocks
        for otype in ("continuous", "flags"):
            cell = f"{name} {otype}"
            seed = cal.case_seed(BASE_SEED, "Z3", cell)
            if otype == "continuous":
                # Leave-year-out anomaly, then the ENSO baseline removed.
                def draw(rng):
                    g = sim.yearly_rainfall(years, rng)
                    a = S.leave_year_out_anomaly(g["anomaly"], years, by="year")
                    return S.remove_baselines(a, {"enso": g["enso"]})
            else:
                def draw(rng):
                    return sim.yearly_rainfall(years, rng)["drought"].astype(float)
            hits = _rejections(d, draw, reps, seed, outcome_type=otype)
            out.append(_result("Z3", cell, hits, reps, fast))
    return out


def run_z4(reps, names=SUN_LINKED, sides=("greater", "less")):
    """Old design: neighbour controls, raw seasonal outcome (documents F-01)."""
    frame = sim.daily_calendars()
    dates = frame.index
    out = []
    for name in names:
        d = B.build_blocks(frame[name].to_numpy(), merge_gap=0)
        for side in sides:
            cell = f"{name} {side}"
            hits = _rejections(d, lambda rng: sim.seasonal_daily(dates, rng), reps,
                               cal.case_seed(BASE_SEED, "Z4", cell), alternative=side)
            out.append(_result("Z4", cell, hits, reps, False))
    return out


def run_z6(reps, fast=False, signs=sim.SIGNS):
    frame = sim.yearly_calendars()
    years = frame.index.to_numpy()
    dates = _yearly_dates(years)
    nb = S.nodal_baseline(years)
    lon = frame["rahu_longitude"].to_numpy()
    out, r4 = [], {}
    for s in signs:
        name = f"rahu_in_{s.lower()}"
        c = frame[name].to_numpy()
        r4[name] = S.r4_passes(S.baseline_r2(c, nb))
        d = S.control_design(c, dates, merge_gap=0, side_seed=BASE_SEED).blocks
        hits = _rejections(d, lambda rng: sim.nodal_wave(lon, rng), reps,
                           cal.case_seed(BASE_SEED, "Z6", name),
                           transform=lambda y: S.remove_baselines(y, nb))
        out.append(_result("Z6", name, hits, reps, fast))
    return out, r4


def _assert_all(results):
    failed = [r for r in results if not r[4]]
    assert not failed, failed


def test_z1_fast():
    _assert_all(run_z1(FAST_REPS, fast=True, sides=("greater",)))


def test_z2_fast():
    _assert_all(run_z2(FAST_REPS, fast=True))


def test_z3_fast():
    _assert_all(run_z3(FAST_REPS, fast=True))


def test_z4_old_design_fails():
    res = run_z4(FAST_REPS)
    assert any(r[4] for r in res), res  # rate above 0.20 for a Sun-linked calendar


def test_z6_fast_nodal_proxy():
    res, r4 = run_z6(FAST_REPS, fast=True)
    _assert_all(res)
    assert not any(r4.values()), r4  # R4 fails for every Rahu-in-sign calendar


@pytest.mark.skipif(not FULL, reason="full calibration runs in the certificate suite")
def test_full_z_cases():
    z6, r4 = run_z6(10_000)
    _assert_all(run_z1(10_000) + run_z2(10_000) + run_z3(10_000) + z6)
    assert any(r[4] for r in run_z4(10_000))
    assert not any(r4.values())

# ------------------------------------------------- Amendment A2 in season.py
def test_single_bar_season_windows_alternate_sides_with_the_plan_seed():
    dates = pd.date_range("2000-01-01", "2009-12-31", freq="D")
    days = [f"2004-{m:02d}-15" for m in range(1, 13)]
    c = _box(dates, [(d, d) for d in days])  # twelve single-day episodes, one a month
    a1 = S.season_design(c, dates, merge_gap=0)
    assert a1.blocks.n_used == 0  # A1: a single bar cannot be split over two years
    a2 = S.season_design(c, dates, merge_gap=0, side_seed=BASE_SEED)
    assert a2.blocks.n_used == 12 and a2.blocks.n_one_sided == 12
    sides = ["left" if len(b.control_left) else "right" for b in a2.blocks.blocks]
    first = B.start_side(BASE_SEED)
    other = B.SIDE_RIGHT if first == B.SIDE_LEFT else B.SIDE_LEFT
    assert sides == [first, other] * 6  # alternating in calendar order from the seed
    for b in a2.blocks.blocks:  # the twin is the same day in the year before or after
        (x,) = b.control.tolist()
        (a,) = b.active.tolist()
        assert (dates[x].month, dates[x].day) == (dates[a].month, dates[a].day)
        assert abs(dates[x].year - dates[a].year) == 1
    # Another seed may start on the other side; the side never depends on an outcome.
    seed2 = next(s for s in range(100) if B.start_side(s) != first)
    a3 = S.season_design(c, dates, merge_gap=0, side_seed=seed2)
    assert ["left" if len(b.control_left) else "right" for b in a3.blocks.blocks] == [other, first] * 6


def test_missing_season_window_on_one_side_gives_a_one_sided_block_with_a2():
    dates = pd.date_range("2000-01-01", "2009-12-31", freq="D")
    # Episode in 2004; the same days are active in 2001 to 2003, so no earlier
    # window lies within three years, while 2005 is free.
    c = _box(dates, [(f"{y}-03-01", f"{y}-03-10") for y in (2001, 2002, 2003, 2004)])
    a1 = S.season_design(c, dates, merge_gap=0)
    a2 = S.season_design(c, dates, merge_gap=0, side_seed=BASE_SEED)
    b1, b2 = a1.blocks.blocks[3], a2.blocks.blocks[3]
    assert not b1.used and a1.windows[3].reason == S.DROP_NO_SEASON_WINDOW
    assert b2.used and b2.side_rule == B.SIDE_FORCED and len(b2.control_left) == 0
    # Earlier episodes reserved 2005 and 2006 first; the nearest free later year serves.
    assert set(dates[b2.control_right].year) == {2007} and b2.n_control == b2.n_active


def test_control_design_passes_the_side_seed(daily):
    dates = daily.index
    c = np.zeros(len(dates), dtype=bool)
    c[10::30] = True  # single-day episodes, not season-linked
    plain = S.control_design(c, dates, merge_gap=0)
    a2 = S.control_design(c, dates, merge_gap=0, side_seed=BASE_SEED)
    assert not a2.season_linked and plain.blocks.n_used == 0
    assert a2.blocks.n_used == a2.blocks.n_episodes and a2.blocks.side_seed == BASE_SEED


# --------------------------------------------------- A2 detrending baseline
def test_centred_detrend_is_symmetric_and_removes_a_linear_trend():
    n = 200
    t = np.arange(n, dtype=float)
    out = S.centred_detrend(3.0 + 0.7 * t, 31)
    assert np.allclose(out, 0.0)  # exact at every bar, the ends included
    # Past and future weigh alike: a spike moves the baseline of the bars
    # 15 before and 15 after it by the same amount.
    y = np.zeros(n)
    y[100] = 31.0
    d = S.centred_detrend(y, 31)
    assert d[85] == d[115] == -1.0 and d[84] == d[116] == 0.0 and d[100] == 30.0
    # Near the ends the half-window is cut back on both sides.
    assert S.centred_detrend(np.r_[5.0, np.zeros(n - 1)], 31)[0] == 0.0
    # NaN stays NaN and enters no mean.
    y = np.random.default_rng(1).normal(size=n)
    y[50] = np.nan
    d = S.centred_detrend(y, 11)
    assert np.isnan(d[50]) and np.isfinite(np.delete(d, 50)).all()
    assert d[45] == pytest.approx(y[45] - np.nanmean(y[40:51]))
    for bad in (2, 4, 1, 3.0, True):
        with pytest.raises(ValueError):
            S.centred_detrend(y, bad)


def test_detrend_required_for_daily_and_hourly_grids_only():
    assert S.detrend_required(pd.date_range("2000-01-01", periods=50, freq="D"))
    assert S.detrend_required(pd.bdate_range("2000-01-03", periods=50))
    assert S.detrend_required(pd.date_range("2000-01-01", periods=50, freq="h"))
    assert not S.detrend_required(pd.date_range("2000-01-01", periods=50, freq="MS"))
    assert not S.detrend_required(_yearly_dates(range(1900, 1950)))
    assert not S.detrend_required(np.arange(1900, 1950))


def test_detrended_effect_shape_is_the_detrended_indicator():
    c = np.zeros(120, dtype=bool)
    c[40:47] = True
    fin = np.ones(120, dtype=bool)
    fin[60] = False
    h = S.detrended_effect_shape(c, 31, fin)
    ind = np.where(fin, c.astype(float), np.nan)
    assert np.allclose(h, S.centred_detrend(ind, 31), equal_nan=True)
    y = np.random.default_rng(2).normal(size=120)
    y[~fin] = np.nan
    # Linearity: detrending (y + r * indicator) = detrended y + r * shape.
    assert np.allclose(S.centred_detrend(np.where(c, y + 0.8, y), 31),
                       S.centred_detrend(y, 31) + 0.8 * h, equal_nan=True)


# D1 (Amendment A2): drift. Slope and random-walk step in noise standard
# deviations, as in tests/test_stats_blocks.py; window declared by the plan.
DRIFT_SLOPE = 0.02
DRIFT_STEP = 0.05
DETREND_WINDOW = 31


def _drift(n, rng):
    t = np.arange(n, dtype=float)
    return rng.standard_normal(n) + DRIFT_SLOPE * t + np.cumsum(rng.normal(0, DRIFT_STEP, n))


def _new_moon_like(n, period=29.530589, start=3):
    c = np.zeros(n, dtype=bool)
    c[np.round(np.arange(start, n, period)).astype(int)] = True
    return c


def run_d1(reps, fast=False, detrend=True, sides=("greater", "less")):
    """D1: no effect, drifting outcome, A2 blocks; detrended by the centred running mean."""
    frame = sim.daily_calendars()
    dates = frame.index
    n = len(dates)
    cals = {"eclipse_window": frame["eclipse_window"].to_numpy(), "new_moon_like": _new_moon_like(n)}
    tf = (lambda y: S.centred_detrend(y, DETREND_WINDOW)) if detrend else None
    out = []
    for name, c in cals.items():
        d = S.control_design(c, dates, merge_gap=0, side_seed=BASE_SEED).blocks
        assert d.n_used >= B.MIN_K_EFF
        for side in sides:
            cell = f"A2 drift {'detrended' if detrend else 'raw'} {name} {side}"
            hits = _rejections(d, lambda rng: _drift(n, rng), reps, cal.case_seed(BASE_SEED, "B3", cell),
                               alternative=side, transform=tf)
            out.append(_result("B3", cell, hits, reps, fast))
    return out


def test_d1_drift_holds_size_after_detrending_fast():
    _assert_all(run_d1(FAST_REPS, fast=True))


@pytest.mark.skipif(not FULL, reason="full calibration runs in the certificate suite")
def test_full_d1_drift():
    _assert_all(run_d1(10_000))



# ------------------------------------------------- second strategy audit (2026-11-23)
def test_detrend_segments_keep_explore_numbers_fixed():
    """N-22: detrended per period, the explore bars do not depend on the confirm bars."""
    rng = np.random.default_rng(22)
    y = rng.normal(size=400) + np.linspace(0.0, 3.0, 400)
    seg = np.r_[np.zeros(250, int), np.ones(150, int)]
    a = S.centred_detrend(y, 31, segments=seg)
    y2 = y.copy()
    y2[250:] += 50.0  # whatever the confirm period holds
    b = S.centred_detrend(y2, 31, segments=seg)
    assert np.array_equal(a[:250], b[:250])
    assert np.allclose(a[:250], S.centred_detrend(y[:250], 31))
    assert np.allclose(a[250:], S.centred_detrend(y[250:], 31))
    # Without segments the centred mean crosses the split (the finding).
    assert not np.allclose(S.centred_detrend(y, 31)[:250], S.centred_detrend(y2, 31)[:250])
    with pytest.raises(ValueError, match="one label per bar"):
        S.centred_detrend(y, 31, segments=seg[:-1])
    cal_ = np.zeros(400, bool)
    cal_[::20] = True
    assert np.allclose(S.detrended_effect_shape(cal_, 31, segments=seg),
                       S.centred_detrend(cal_.astype(float), 31, segments=seg))


def test_baseline_effect_shape_is_the_indicator_through_remove_baselines():
    """N-02: calendar and baselines only; NaN where the outcome is missing."""
    c = np.zeros(300, bool)
    c[::10] = True
    base = np.random.default_rng(1).normal(size=300) + 2.0 * c
    fin = np.ones(300, bool)
    fin[5] = False
    h = S.baseline_effect_shape(c, base, fin)
    assert np.isnan(h[5]) and np.isfinite(np.delete(h, 5)).all()
    assert np.allclose(h, S.remove_baselines(np.where(fin, c.astype(float), np.nan), base), equal_nan=True)
    # The regression absorbs part of the indicator: the active-minus-control gap shrinks below 1.
    gap = np.nanmean(h[c]) - np.nanmean(h[~c])
    assert 0.0 < gap < 1.0
