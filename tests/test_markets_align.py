"""markets.align: one calendar, windows in bars, fixing-time sampling."""

from datetime import timezone

import numpy as np
import pandas as pd
import pytest

from vedic_astrology_core.markets import align

# Thu 2 Jan 2020 to Wed 8 Jan 2020: five trading days, a weekend between.
DATES = ["2020-01-02", "2020-01-03", "2020-01-06", "2020-01-07", "2020-01-08"]
PRICES = pd.DataFrame({"date": pd.to_datetime(DATES), "close": [1.0, 2, 3, 4, 5]})


def test_window_mask_counts_trading_days_not_calendar_days():
    """S1-11: a 3-day window after Friday spans Fri..Wed, four bars."""
    cal = align.trading_calendar(PRICES)
    bars = align.on_calendar(["2020-01-03"], cal)
    mask = align.window_mask(bars, len(cal), before=0, after=3)
    assert mask.tolist() == [False, True, True, True, True]
    assert mask.sum() == 4  # a calendar-day window would cover 2 bars only


def test_on_calendar_policies_for_weekend_event():
    """Check on calendar policies for weekend event."""
    cal = align.trading_calendar(PRICES)
    sat = ["2020-01-04"]
    assert align.on_calendar(sat, cal, "next_bar").tolist() == [2]
    assert align.on_calendar(sat, cal, "previous_bar").tolist() == [1]
    assert align.on_calendar(sat, cal, "drop_non_trading").tolist() == []
    assert align.on_calendar(["2021-01-01"], cal).tolist() == []


def test_on_calendar_converts_aware_events_to_market_date():
    """Check on calendar converts aware events to market date."""
    cal = align.trading_calendar(PRICES)
    # 03:00 UTC on 3 Jan is still 2 Jan in New York.
    event = pd.Timestamp("2020-01-03 03:00", tz="UTC")
    assert align.on_calendar([event], cal, tz="America/New_York").tolist() == [0]
    assert align.on_calendar([event], cal, tz="UTC").tolist() == [1]


def test_sample_instants_follow_local_fixing_time_across_dst():
    """Check sample instants follow local fixing time across dst."""
    inst = align.sample_instants(["2020-01-15", "2020-07-15"], "15:00", "Europe/London")
    assert [t.hour for t in inst] == [15, 14]  # GMT then BST
    assert inst.tz is not None and str(inst.tz) == "UTC"


def test_align_trading_calendar_with_callable_source():
    """Check align trading calendar with callable source."""
    seen = {}

    def source(instants):
        seen["instants"] = instants
        return pd.DataFrame({"x": np.arange(len(instants))}, index=instants)

    out = align.align(PRICES, source, sample_time="13:30", tz="America/New_York")
    assert len(out) == 5 and out["x"].tolist() == [0, 1, 2, 3, 4]
    assert out["bar"].tolist() == [0, 1, 2, 3, 4]
    assert seen["instants"][0] == pd.Timestamp("2020-01-02 18:30", tz=timezone.utc)


def test_align_calendar_mode_ffills_close_and_marks_trading():
    """Check align calendar mode ffills close and marks trading."""
    ind = pd.DataFrame({"x": range(7)}, index=pd.date_range("2020-01-02", periods=7))
    out = align.align(PRICES, ind, calendar="calendar")
    assert len(out) == 7
    assert out["is_trading"].tolist() == [True, True, False, False, True, True, True]
    assert out.loc[2, "close"] == 2.0 and out.loc[2, "bar"] == 1


def test_align_joins_aware_index_on_utc_date_and_refuses_gaps():
    """Check align joins aware index on utc date and refuses gaps."""
    idx = pd.date_range("2020-01-02 23:00", periods=7, freq="D", tz="UTC")
    ok = align.align(PRICES, pd.DataFrame({"x": range(7)}, index=idx))
    assert ok["x"].tolist() == [0, 1, 4, 5, 6]
    short = pd.DataFrame({"x": [1]}, index=pd.DatetimeIndex(["2020-01-02"]))
    with pytest.raises(ValueError, match="lack indicators"):
        align.align(PRICES, short)
    with pytest.raises(ValueError, match="freq"):
        align.align(PRICES, short, freq="W")


def test_run_starts_and_intervals():
    """Check run starts and intervals."""
    m = [True, True, False, True, False, True]
    # The run already on at bar 0 is not an onset.
    assert align.run_starts(m).tolist() == [3, 5]
    spans = align.intervals(m, pd.date_range("2020-01-01", periods=6))
    assert [(a.day, b.day) for a, b in spans] == [(1, 2), (4, 4), (6, 6)]
