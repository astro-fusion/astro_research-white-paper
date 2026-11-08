"""markets.overlay: tidy frame for paper and site, standard figure."""

import numpy as np
import pandas as pd
import pytest

from vedic_astrology_core.markets import overlay

FIX = "tests/fixtures/markets/yahoo_gold_GCF_2015_2020.csv"
PROV = {"data_sha256": "4aa16ff6166f" + "0" * 52, "commit": "abc1234", "seed": 42}


def _prices():
    return pd.read_csv(FIX, parse_dates=["date"])


def test_forward_log_return():
    """Check forward log return."""
    out = overlay.forward_log_return(np.exp([0.0, 1.0, 3.0]), 1)
    assert out[:2].tolist() == [1.0, 2.0] and np.isnan(out[2])


def test_overlay_frame_columns_and_types():
    """Check overlay frame columns and types."""
    prices = _prices()
    aligned = prices.assign(is_trading=True, **{"rule:X": [True, False] * 740})
    ind = pd.DataFrame({"jup_retro": np.arange(len(prices)) % 3 == 0})
    frame = overlay.overlay_frame(aligned, ind, horizons=(5,))
    assert list(frame.columns) == ["date", "close", "log_return", "fwd_5",
                                   "jup_retro", "rule:X"]
    assert frame["date"].iloc[0] == "2015-01-02"
    assert set(frame["jup_retro"].unique()) == {0, 1}
    assert frame["fwd_5"].isna().sum() == 5


@pytest.mark.parametrize("kind", ["mask", "events"])
def test_overlay_plot_writes_png_with_footer(tmp_path, kind):
    """Check overlay plot writes png with footer."""
    prices = _prices()
    if kind == "mask":
        target = (np.arange(len(prices)) // 100) % 2 == 0
    else:
        target = ["2016-06-24", "2020-03-09"]
    path = tmp_path / f"{kind}.png"
    fig = overlay.overlay_plot(prices, target, "Gold and a test indicator",
                               provenance=PROV, path=str(path))
    assert path.exists() and path.stat().st_size > 10_000
    texts = " ".join(t.get_text() for t in fig.texts)
    assert "4aa16ff6166f" in texts and "seed 42" in texts and "EXPLORATORY" in texts
    legend = fig.axes[0].get_legend().get_texts()[0].get_text()
    assert ("8 windows" in legend) if kind == "mask" else ("N = 2" in legend)
