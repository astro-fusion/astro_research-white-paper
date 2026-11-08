"""Tests for the same-family NB2 count-model comparison."""

import os
import sys

import numpy as np
import pandas as pd

from studies._paths import study_dir

sys.path.insert(0, str(study_dir("earthquake") / "scripts"))

from count_models import compare_nb_models, monthly_design  # noqa: E402


def _frame(effect, seed, months=240):
    rng = np.random.default_rng(seed)
    x = rng.uniform(0, 1, size=months)
    mu = np.exp(0.5 + effect * x)
    alpha = 0.3
    y = rng.negative_binomial(1 / alpha, 1 / (1 + alpha * mu))
    periods = pd.period_range("2000-01", periods=months, freq="M")
    return pd.DataFrame({"count": y, "trend": np.linspace(-1, 1, months),
                         "x": x, "year": [p.year for p in periods]},
                        index=periods)


def test_effect_detected_by_lr_and_cv():
    """A real covariate gives a small LR p-value and a positive CV gain."""
    res = compare_nb_models(_frame(1.5, 0), ["x"])
    assert res["lr_p_value"] < 1e-4
    assert res["loyo_cv_gain"] > 0
    assert res["baseline"]["alpha"] > 0 and res["research"]["alpha"] > 0


def test_no_effect_not_rejected():
    """Noise covariate: LR p-value is not small."""
    res = compare_nb_models(_frame(0.0, 1), ["x"])
    assert res["lr_p_value"] > 0.05


def test_monthly_design_and_no_files_written(tmp_path):
    """Monthly design counts events; nothing is written to the cwd."""
    old = os.getcwd()
    os.chdir(tmp_path)
    try:
        grid = pd.date_range("2000-01-01", "2000-03-01", freq="h", tz="UTC",
                             inclusive="left")
        ind = pd.DataFrame({"a": np.arange(len(grid)) % 2 == 0}, index=grid)
        times = ["2000-01-05T00:00:00Z", "2000-02-10T00:00:00Z",
                 "2000-02-11T00:00:00Z"]
        frame = monthly_design(times, ind, ["a"])
        assert frame["count"].tolist() == [1, 2]
        assert np.allclose(frame["a"], 0.5)
        assert list(tmp_path.iterdir()) == []
    finally:
        os.chdir(old)
