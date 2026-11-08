"""Tests for the earthquake study's controls and classifier inputs."""

import sys

import numpy as np
import pandas as pd

from studies._paths import study_dir

sys.path.insert(0, str(study_dir("earthquake") / "scripts"))

import fetch_catalogue as fc  # noqa: E402
import robustness as rb  # noqa: E402

HYP = fc.load_hypothesis()


def _eph(n_days):
    """Return a synthetic hourly ephemeris frame."""
    n = n_days * 24
    idx = pd.date_range("2000-01-01", periods=n, freq="h", tz="UTC")
    data = {"jd": 2451544.5 + np.arange(n) / 24}
    for k, b in enumerate(rb.LONGITUDE_BODIES):
        data[f"lon_{b}"] = (np.arange(n) * (0.5 + k) / 24) % 360
        data[f"speed_{b}"] = np.full(n, 0.5 + k)
    return pd.DataFrame(data, index=idx)


def test_controls_are_registered_as_an_amendment():
    """The controls block exists and an amendment records when it was added."""
    assert HYP["controls"]["negative"]["offset_days"] >= HYP["test"]["min_shift_days"]
    ids = [s["id"] for s in HYP["controls"]["positive"]["indicators"]]
    assert ids == ["tide_semidiurnal_peak", "tide_spring", "tide_spring_and_peak"]
    assert any("controls" in a["field"] for a in HYP["amendments"])
    assert len(HYP["indicators"]) == 13


def test_daily_features_shape():
    """Nine sin/cos pairs, eight speeds, 30 tithis and 27 nakshatras per day."""
    x = rb.daily_features(_eph(10), 24)
    assert x.shape == (10, 18 + 8 + 30 + 27)
    assert np.allclose(x[:, 18 + 8:18 + 8 + 30].sum(axis=1), 1)
    assert np.allclose(x[:, -27:].sum(axis=1), 1)


def test_event_days():
    """Several events on one day give one event day."""
    y = rb.event_days(np.array([0, 5, 30, 47, 49]), 24, 3)
    assert y.tolist() == [1, 1, 1]
    assert rb.event_days(np.array([50]), 24, 2).tolist() == [0, 0]
