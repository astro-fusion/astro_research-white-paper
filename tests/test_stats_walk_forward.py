"""Tests for time splits, walk-forward splits and Hansen's SPA test."""

import numpy as np
import pandas as pd
import pytest

from vedic_astrology_core.stats.walk_forward import (
    spa_test,
    time_split,
    walk_forward_splits,
)


def test_time_split_with_purge():
    """Purged days belong to neither period."""
    idx = pd.date_range("2000-01-01", periods=100, freq="D")
    ex, conf = time_split(idx, "2000-03-01", purge=pd.Timedelta(days=10))
    assert conf.sum() == 100 - 60  # 2000 is a leap year
    assert ex.sum() == 60 - 10
    assert not (ex & conf).any()
    with pytest.raises(ValueError):
        time_split(idx, "2001-01-01")


def test_walk_forward_splits_expand_and_never_overlap():
    """Each test block follows its train block after the purge."""
    splits = list(walk_forward_splits(100, 40, 20, purge=5))
    assert len(splits) == 3
    for train, test in splits:
        assert train.max() + 5 < test.min()
    assert splits[-1][1].max() == 99


def test_spa_detects_superior_model():
    """One model with much lower loss gives a small consistent p-value."""
    rng = np.random.default_rng(0)
    bench = rng.normal(1.0, 0.2, size=800)
    models = np.column_stack([bench + rng.normal(0, 0.2, 800) for _ in range(5)])
    models[:, 2] -= 0.3
    res = spa_test(bench, models, np.random.default_rng(1), n_boot=499)
    assert res.best_model == 2
    assert res.p_consistent < 0.01
    assert res.p_lower <= res.p_consistent <= res.p_upper


def test_spa_null_when_no_model_is_better():
    """Models no better than the benchmark give a large p-value."""
    rng = np.random.default_rng(2)
    bench = rng.normal(1.0, 0.2, size=800)
    models = np.column_stack([bench + rng.normal(0.05, 0.2, 800)
                              for _ in range(10)])
    res = spa_test(bench, models, np.random.default_rng(3), n_boot=499)
    assert res.p_consistent > 0.2
