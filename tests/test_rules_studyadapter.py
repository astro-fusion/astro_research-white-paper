"""The study adapter: explore/confirm split, events, and the holdout wall."""

import inspect
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import pytest

from vedic_astrology_core.rules import RuleRegistry, evaluate
from vedic_astrology_core.rules.grid import GridEvaluator, apply_window
from vedic_astrology_core.rules.schema import Window
from vedic_astrology_core.rules.studyadapter import (
    StudyAdapter,
    direction_of,
    split_periods,
)

REGISTRY = RuleRegistry.load()


@pytest.fixture(scope="module")
def quake():
    """Return the earthquake study (data from the committed snapshot)."""
    return StudyAdapter("earthquake")


def test_split_from_the_earthquake_layout():
    """split: explore [a, b], confirm [c, d]; ends inclusive in the file."""
    hyp = {
        "split": {
            "explore": ["1976-01-01", "2010-12-31"],
            "confirm": ["2011-01-01", "2026-10-31"],
        }
    }
    explore, confirm = split_periods(hyp)
    assert explore.end == pd.Timestamp("2011-01-01", tz="UTC")
    assert confirm.start == pd.Timestamp("2011-01-01", tz="UTC")
    assert explore.label() == ["1976-01-01", "2010-12-31"]


def test_split_from_the_market_layout():
    """periods: explore_end, confirm_start, with data start and end."""
    hyp = {
        "data": {"start": "1968-04-01", "end": "2026-10-30"},
        "periods": {"explore_end": "2015-12-31", "confirm_start": "2016-01-01"},
    }
    explore, confirm = split_periods(hyp)
    assert explore.start == pd.Timestamp("1968-04-01", tz="UTC")
    assert confirm.label() == ["2016-01-01", "2026-10-30"]


def test_overlapping_split_is_rejected():
    """A confirm period that starts inside explore is a registration error."""
    hyp = {
        "split": {
            "explore": ["2000-01-01", "2010-12-31"],
            "confirm": ["2010-06-01", "2020-01-01"],
        }
    }
    with pytest.raises(ValueError, match="overlaps"):
        split_periods(hyp)


def test_explore_and_confirm_partition_the_events(quake):
    """Explore events end before the confirm period; both are non-empty."""
    explore, confirm = quake.explore_period(), quake.confirm_period()
    grid = quake.explore_grid()
    assert grid[0] >= explore.start and grid[-1] < confirm.start
    ev = quake.explore_events()
    assert len(ev) > 50 and ev.max() < len(grid)
    cgrid = quake.confirm_grid()
    assert cgrid[0] >= confirm.start
    assert len(quake.confirm_events()) > 20


def _timestamps(value):
    if isinstance(value, pd.DatetimeIndex):
        return list(value)
    if isinstance(value, pd.Timestamp):
        return [value]
    return []


def test_no_function_without_confirm_in_its_name_returns_confirm_data(quake):
    """Every public non-confirm accessor stays inside the explore period."""
    rule = REGISTRY.get("seismic.mangal_ketu_primary")
    cutoff = quake.confirm_period().start
    n_explore = len(quake.explore_grid())
    checked = []
    for name, member in inspect.getmembers(quake):
        if name.startswith("_") or "confirm" in name or not callable(member):
            continue
        params = inspect.signature(member).parameters
        if not params:
            out = member()
        elif list(params) == ["rule"]:
            out = member(rule)
        else:
            continue
        if callable(out):
            out = out(rule)
        for ts in _timestamps(out):
            assert ts < cutoff, name
        if hasattr(out, "end"):
            assert out.end <= cutoff, name
        if isinstance(out, np.ndarray) and out.dtype != np.int64:
            assert len(out) == n_explore, name
        if isinstance(out, np.ndarray) and out.dtype == np.int64 and len(out):
            assert out.max() < n_explore, name
        checked.append(name)
    assert {
        "explore_period",
        "explore_grid",
        "explore_events",
        "explore_indicator",
        "explore_strength",
        "explore_evaluator",
    } <= set(checked)


def test_grid_indicator_matches_the_engine(quake):
    """The cached grid evaluation agrees with astro-rules explain."""
    rule = REGISTRY.get("seismic.mangal_ketu_primary")
    ind = quake.explore_indicator(rule)
    grid = quake.explore_grid()
    for i in (0, 4000, 9000, len(grid) - 1):
        moment = (grid[i] + pd.Timedelta(hours=12)).to_pydatetime()
        assert evaluate(rule, moment).fired == ind[i]


def test_bound_params_change_the_indicator(quake):
    """A wider orb opens the indicator on more days."""
    rule = REGISTRY.get("seismic.mangal_ketu_primary")
    narrow = quake.explore_indicator(rule.bind({"orb": 3})).mean()
    wide = quake.explore_indicator(rule.bind({"orb": 19})).mean()
    assert 0 < narrow < wide < 0.2


def test_window_opens_the_steps_after_a_firing():
    """after: 2 days opens the firing day and the two days after it."""
    days = pd.date_range("2000-01-01", periods=10, freq="D", tz="UTC")
    fired = np.zeros(10, dtype=bool)
    fired[3] = True
    out = apply_window(fired, days, Window(unit="days", after=2))
    assert np.flatnonzero(out).tolist() == [3, 4, 5]
    out = apply_window(fired, days, Window(unit="days", before=1, after=0))
    assert np.flatnonzero(out).tolist() == [2, 3]
    assert apply_window(fired, days, None).tolist() == fired.tolist()


def test_strength_is_zero_when_silent_and_graded_when_firing():
    """A binary rule gives 0/1; strength terms give values in (0, 1]."""
    moments = pd.date_range("2001-05-10", periods=12, freq="D", tz="UTC")
    ev = GridEvaluator(moments)
    rule = REGISTRY.get("seismic.mangal_ketu_primary")
    binary = ev.strength(rule)
    assert set(np.unique(binary)) <= {0.0, 1.0}
    graded = rule.model_validate(
        dict(
            rule._template,
            strength={
                "combine": "product",
                "terms": [
                    {"orb_closeness": {"planets": ["Mars", "Ketu"], "orb": "$orb"}}
                ],
            },
        )
    )
    values = ev.strength(graded)
    fired = ev.fired(graded)
    assert np.all(values[~fired] == 0)
    assert np.all((values[fired] > 0) & (values[fired] <= 1))


def test_direction_comes_from_the_expected_effect():
    """Map increase to greater, decrease to less, anything else two-sided."""
    assert direction_of(REGISTRY.get("seismic.mangal_ketu_primary")) == "greater"
    assert direction_of(REGISTRY.get("general.gaja_kesari.moon_kendra")) == "two-sided"


def test_market_study_uses_extreme_move_bars():
    """Gold: bars, extreme moves, the indicator on the previous bar."""
    gold = StudyAdapter("gold")
    grid = gold.explore_grid()
    if len(grid) < 100:
        pytest.skip(
            "gold price data is not available in this checkout (data/ is not committed)"
        )
    assert grid[-1] < gold.confirm_period().start
    ev = gold.explore_events()
    assert 0.02 < len(ev) / len(grid) < 0.15  # about 5 % of bars by construction
    assert gold.min_shift == 400


def test_unknown_study_is_named():
    """A typo lists the known studies."""
    with pytest.raises(KeyError, match="earthquake"):
        StudyAdapter("earthquakes")


def test_family_member_reads_the_hypothesis():
    """The gold family names migrated catalogue rules by their old names."""
    gold = StudyAdapter("gold")
    assert gold.family_member(REGISTRY.get("financial.venus_own_sign")) == (
        "venus_own_sign"
    )
    assert (
        gold.family_member(REGISTRY.get("financial.venus_retrograde_reversal")) is None
    )


def test_datetime_inputs_are_aware():
    """Grid moments are UTC-aware datetimes."""
    moments = pd.date_range("2001-05-10", periods=2, freq="D", tz="UTC")
    ev = GridEvaluator(moments)
    assert ev.contexts[0].sky.moment.tzinfo is not None
    assert ev.contexts[0].sky.moment == datetime(2001, 5, 10, tzinfo=timezone.utc)
