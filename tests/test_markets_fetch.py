"""markets.fetch: tidy adapters, futures labelling, hashed snapshots."""

import json
from pathlib import Path

import pandas as pd
import pytest

from vedic_astrology_core.markets import fetch

FIX = Path(__file__).parent / "fixtures" / "markets"
FRED_CSV = (FIX / "fred_DEXUSUK_2019-12-20_2020-01-10.csv").read_text()


def test_fred_parses_blank_as_missing_and_is_tidy():
    """Check fred parses blank as missing and is tidy."""
    df = fetch.fred("DEXUSUK", opener=lambda url: FRED_CSV)
    assert list(df.columns[:5]) == fetch.TIDY_COLUMNS
    assert len(df) == 14  # 16 rows, Christmas and New Year blank
    assert df["date"].iloc[0] == pd.Timestamp("2019-12-20")
    assert df["close"].iloc[0] == pytest.approx(1.3036)
    assert not df["is_futures"].any()
    assert df.attrs["source_url"].endswith("id=DEXUSUK")


def test_fred_clip_and_dot_missing():
    """Check fred clip and dot missing."""
    text = "observation_date,X\n2020-01-01,.\n2020-01-02,5\n2020-01-03,6\n"
    df = fetch.fred("X", start="2020-01-03", opener=lambda url: text)
    assert df["close"].tolist() == [6.0]


def test_fred_html_or_wrong_columns_raise():
    """Check fred html or wrong columns raise."""
    with pytest.raises(fetch.FetchError):
        fetch.fred("GOLDPMGBD228NLBM", opener=lambda url: "<!DOCTYPE html>")
    with pytest.raises(fetch.FetchError):
        fetch.parse_fred_csv("observation_date,OTHER\n2020-01-01,1\n", "X")


def _fake_yahoo(ticker, start, end):
    idx = pd.DatetimeIndex(["2020-01-02", "2020-01-03", "2020-01-06"], name="Date")
    return pd.DataFrame(
        {"Close": [1520.0, 1550.0, 1570.0], "Volume": [10, 0, 5]}, index=idx
    )


def test_yahoo_futures_flagged_and_zero_volume_dropped():
    """Check yahoo futures flagged and zero volume dropped."""
    df = fetch.yahoo("GC=F", downloader=_fake_yahoo)
    assert df["is_futures"].all()
    assert len(df) == 2 and df.attrs["dropped_zero_volume"] == 1
    assert "not spot" in df.attrs["description"]


def test_yahoo_futures_can_never_be_spot():
    """Check yahoo futures can never be spot."""
    with pytest.raises(ValueError, match="futures"):
        fetch.yahoo("GC=F", is_futures=False, downloader=_fake_yahoo)


def test_tidy_rejects_duplicates_and_nonpositive():
    """Check tidy rejects duplicates and nonpositive."""
    base = {"source": "x", "series_id": "y", "is_futures": False}
    with pytest.raises(ValueError, match="duplicate"):
        fetch.tidy(pd.DataFrame({"date": ["2020-01-01"] * 2, "close": [1, 2], **base}))
    with pytest.raises(ValueError, match="non-positive"):
        fetch.tidy(pd.DataFrame({"date": ["2020-01-01"], "close": [0.0], **base}))


def test_snapshot_roundtrip_hash_and_manifest(tmp_path):
    """Check snapshot roundtrip hash and manifest."""
    df = fetch.read_tidy_csv(FIX / "yahoo_gold_GCF_2015_2020.csv")
    path = fetch.snapshot(
        df,
        "gold",
        root=tmp_path,
        source_url="u",
        fetched_at="2026-11-08T00:00:00+00:00",
    )
    digest = fetch.sha256_bytes(path.read_bytes())
    assert path.name == f"gold_{digest[:12]}.csv"
    manifest = json.loads(path.with_suffix(".manifest.json").read_text())
    assert manifest["sha256"] == digest
    assert manifest["rows"] == len(df) == 1480
    assert (manifest["date_min"], manifest["date_max"]) == ("2015-01-02", "2020-12-31")
    assert manifest["is_futures"] is True and manifest["source_url"] == "u"
    again, sha = fetch.load_snapshot(path)
    assert sha == digest and len(again) == len(df)
    # Same data, same file name: snapshots are content-addressed.
    assert fetch.snapshot(again, "gold", root=tmp_path) == path


def test_load_snapshot_detects_tampering(tmp_path):
    """Check load snapshot detects tampering."""
    df = fetch.read_tidy_csv(FIX / "yahoo_silver_SIF_2015_2020.csv")
    path = fetch.snapshot(df, "silver", root=tmp_path)
    path.write_text(path.read_text().replace("2015-01-02", "2015-01-01", 1))
    with pytest.raises(ValueError, match="hash"):
        fetch.load_snapshot(path)
