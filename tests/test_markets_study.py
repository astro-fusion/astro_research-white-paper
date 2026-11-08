"""markets.study: the shared, hypothesis-driven pipeline, run offline."""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

from vedic_astrology_core.markets import fetch, study

REPO = Path(__file__).resolve().parent.parent
GOLD = REPO / "studies" / "gold_market" / "hypothesis.yaml"


def _small_hypothesis(tmp_path):
    cfg = yaml.safe_load(GOLD.read_text())
    cfg["tests"].update(n_perm=99, n_boot_ci=50, min_shift_bars=150)
    cfg["periods"].update(explore_end="2017-12-31", confirm_start="2018-01-01")
    cfg["spa"]["n_boot"] = 99
    cfg["event_study"].update(n_boot=50, bodies=["MERCURY", "JUPITER"])
    cfg["granger"].update(bodies=["JUPITER"], targets=["returns"])
    cfg["indicators"] = cfg["indicators"][:4] + cfg["indicators"][-1:]
    path = tmp_path / "hypothesis.yaml"
    path.write_text(yaml.safe_dump(cfg))
    return path


def test_extreme_flag_uses_only_the_past():
    """Check the extreme-move threshold never sees the bar it judges."""
    close = np.exp(np.cumsum(np.r_[0.0, np.tile([0.01, -0.01], 20)]))
    base = study.targets(close, window=10, quantile=0.9)
    bumped = close.copy()
    bumped[30:] *= 1.5  # a jump at bar 30 changes nothing before it
    after = study.targets(bumped, window=10, quantile=0.9)
    pd.testing.assert_frame_equal(base.iloc[:30], after.iloc[:30])
    assert after["extreme"].iloc[30] == 1.0
    assert base["extreme"].iloc[:11].isna().all()


def test_acquire_falls_back_to_fixture_and_marks_provisional(monkeypatch):
    """Check unreachable sources lead to the fixture and provisional=True."""

    def down(*args, **kwargs):
        raise fetch.FetchError("offline")

    monkeypatch.setattr(fetch, "fred", down)
    monkeypatch.setattr(fetch, "yahoo", down)
    prices, record = study.acquire(study.load_hypothesis(GOLD), REPO)
    assert record["provisional"] is True and len(prices) == 1480
    assert [t["series_id"] for t in record["sources_tried"]] == [
        "GOLDPMGBD228NLBM",
        "GC=F",
    ]
    assert record["sha256"] == fetch.sha256_bytes(
        (REPO / "tests/fixtures/markets/yahoo_gold_GCF_2015_2020.csv").read_bytes()
    )


def test_load_hypothesis_rejects_duplicates(tmp_path):
    """Check a hypothesis file with a repeated indicator id is refused."""
    cfg = yaml.safe_load(GOLD.read_text())
    cfg["indicators"].append(cfg["indicators"][0])
    path = tmp_path / "h.yaml"
    path.write_text(yaml.safe_dump(cfg))
    with pytest.raises(ValueError, match="duplicate"):
        study.load_hypothesis(path)


@pytest.mark.slow
def test_offline_run_is_complete_and_reproducible(tmp_path):
    """Check an offline run writes every artifact and is seed-reproducible."""
    hyp = _small_hypothesis(tmp_path)
    a = study.run_study(hyp, tmp_path / "a", REPO, seed=7, offline=True)
    study.run_study(hyp, tmp_path / "b", REPO, seed=7, offline=True)
    assert a["provisional"] is True and a["data"]["adapter"] == "fixture"
    for name in (
        "results.json",
        "manifest.json",
        "tbl_indicator_tests.csv",
        "overlay_frame.csv",
        "fig_overlay.png",
        "fig_effects.png",
        "fig_event_study.png",
        "fig_stations.png",
    ):
        assert (tmp_path / "a" / name).exists(), name
    ta = pd.read_csv(tmp_path / "a" / "tbl_indicator_tests.csv")
    tb = pd.read_csv(tmp_path / "b" / "tbl_indicator_tests.csv")
    pd.testing.assert_frame_equal(ta, tb)
    assert a["family"]["size_explore"] == 5 * 3
    tested = ta[ta["testable"]]
    assert ((tested["p_value"] > 0) & (tested["p_value"] <= 1)).all()
    assert (tested["q_value"] >= tested["p_value"]).all()
    manifest = json.loads((tmp_path / "a" / "manifest.json").read_text())
    assert manifest["seed"] == 7 and manifest["provisional"] is True
    assert manifest["inputs"][0]["sha256"] == a["data"]["sha256"]
    frame = pd.read_csv(tmp_path / "a" / "overlay_frame.csv")
    assert {"date", "close", "log_return", "jupiter_retrograde"} <= set(frame.columns)
