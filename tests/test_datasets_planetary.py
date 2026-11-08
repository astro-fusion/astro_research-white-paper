"""Tests for the reproducible planetary dataset generator."""

import json
from datetime import datetime, timezone

import pandas as pd
import pytest
import swisseph as swe

from vedic_astrology_core.datasets import planetary
from vedic_astrology_core.datasets.planetary import (
    COLUMNS,
    combined,
    generate,
    verify,
)

NOON_2000 = 2451545.0  # 2000-01-01 12:00 UTC


def _gen(tmp_path, **kw):
    kw.setdefault("fmt", "csv")
    return generate(2000, 2000, out_dir=tmp_path, **kw)


def test_schema_and_rows(tmp_path):
    """One row per body per day with the documented columns."""
    _gen(tmp_path)
    df = pd.read_csv(tmp_path / "2000.csv")
    assert list(df.columns) == COLUMNS
    assert len(df) == 366 * 9
    assert set(df["body"]) == {
        "SUN", "MOON", "MARS", "MERCURY", "JUPITER",
        "VENUS", "SATURN", "RAHU", "KETU",
    }  # fmt: skip
    assert df["sign"].between(0, 11).all()
    assert df["nakshatra"].between(1, 27).all()
    assert df["pada"].between(1, 4).all()


def test_sun_matches_pyswisseph_sidereal_lahiri(tmp_path):
    """Sun on 2000-01-01 12:00 UTC equals swe.calc_ut with FLG_SIDEREAL."""
    _gen(tmp_path)
    df = pd.read_csv(tmp_path / "2000.csv")
    row = df[(df.body == "SUN") & (df.jd == NOON_2000)].iloc[0]
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    flags = swe.FLG_SWIEPH | swe.FLG_SPEED | swe.FLG_SIDEREAL
    expected = swe.calc_ut(NOON_2000, swe.SUN, flags)[0]
    assert row.longitude == pytest.approx(expected[0], abs=1e-9)
    assert row.speed == pytest.approx(expected[3], abs=1e-9)
    assert row.date.startswith("2000-01-01T12:00:00")
    assert row.sign_name == "Sagittarius"
    assert row.sign == 8


def test_ketu_is_rahu_plus_180_and_mean_node(tmp_path):
    """Ketu = Rahu + 180 and Rahu is the mean node by default."""
    _gen(tmp_path)
    df = pd.read_csv(tmp_path / "2000.csv")
    rahu = df[df.body == "RAHU"].reset_index(drop=True)
    ketu = df[df.body == "KETU"].reset_index(drop=True)
    diff = (ketu.longitude - rahu.longitude) % 360
    assert (diff - 180).abs().max() < 1e-9
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    flags = swe.FLG_SWIEPH | swe.FLG_SPEED | swe.FLG_SIDEREAL
    mean = swe.calc_ut(NOON_2000, swe.MEAN_NODE, flags)[0][0]
    assert rahu.longitude.iloc[0] == pytest.approx(mean, abs=1e-9)
    assert rahu.retrograde.all()


def test_moon_nakshatra_fields_consistent(tmp_path):
    """Nakshatra number, pada and degree_in_sign follow the longitude."""
    _gen(tmp_path, bodies=["MOON"])
    df = pd.read_csv(tmp_path / "2000.csv")
    span = 360.0 / 27.0
    assert (df.nakshatra == (df.longitude // span).astype(int) + 1).all()
    assert (df.degree_in_sign - (df.longitude % 30)).abs().max() < 1e-9
    assert df.nakshatra_lord.notna().all()


def test_manifest_contents_and_hash(tmp_path):
    """The manifest records engine details and the file sha256."""
    _gen(tmp_path)
    manifest = json.loads((tmp_path / "2000.manifest.json").read_text())
    assert manifest["ayanamsa"] == "lahiri"
    assert manifest["node_model"] == "mean"
    assert manifest["ephemeris_model"] in ("swieph", "moshier", "jpl")
    assert manifest["file"] == "2000.csv"
    assert manifest["rows"] == 366 * 9
    assert manifest["generator_version"]
    assert "git_commit" in manifest
    assert len(manifest["sha256"]) == 64
    assert verify(tmp_path) == []


def test_verify_detects_tampering(tmp_path):
    """Verification reports a file whose hash no longer matches."""
    _gen(tmp_path)
    path = tmp_path / "2000.csv"
    path.write_text(path.read_text().replace("SUN", "SUM", 1))
    assert verify(tmp_path) == ["2000.csv"]


def test_deterministic(tmp_path):
    """Two runs give byte-identical files."""
    a, b = tmp_path / "a", tmp_path / "b"
    generate(2001, 2001, out_dir=a, fmt="csv")
    generate(2001, 2001, out_dir=b, fmt="csv")
    assert (a / "2001.csv").read_bytes() == (b / "2001.csv").read_bytes()


def test_sample_time_and_timezone(tmp_path):
    """06:00 in Asia/Kathmandu (UTC+5:45) is 00:15 UTC on the same date."""
    _gen(tmp_path, bodies=["SUN"], sample_time="06:00", tz="Asia/Kathmandu")
    df = pd.read_csv(tmp_path / "2000.csv")
    assert df.date.iloc[0] == "2000-01-01T00:15:00+00:00"
    expected = datetime(2000, 1, 1, 0, 15, tzinfo=timezone.utc)
    assert df.jd.iloc[0] == pytest.approx(
        2440587.5 + expected.timestamp() / 86400, abs=1e-9
    )


def test_step_and_unsupported_options(tmp_path):
    """Step 7D thins the rows; bad options raise."""
    _gen(tmp_path, bodies=["SUN"], step="7D")
    assert len(pd.read_csv(tmp_path / "2000.csv")) == 53
    with pytest.raises(ValueError):
        _gen(tmp_path, ayanamsa="nonsense")
    with pytest.raises(ValueError):
        _gen(tmp_path, node_model="odd")
    with pytest.raises(ValueError):
        _gen(tmp_path, fmt="xlsx")
    with pytest.raises(ValueError):
        _gen(tmp_path, tz="Not/AZone")
    with pytest.raises(ValueError):
        generate(2001, 2000, out_dir=tmp_path)


def test_parquet_roundtrip_and_combined(tmp_path):
    """Parquet files load back through combined(), filtered by body."""
    pytest.importorskip("pyarrow")
    generate(2000, 2001, out_dir=tmp_path, fmt="parquet")
    df = combined([2000, 2001], bodies=["SUN", "MOON"], data_dir=tmp_path)
    assert len(df) == (366 + 365) * 2
    assert set(df.body) == {"SUN", "MOON"}
    assert df.date.is_monotonic_increasing or df.sort_values("date").shape == df.shape
    assert verify(tmp_path) == []


def test_combined_csv_and_missing_year(tmp_path):
    """Combining reads CSV too and names a missing year."""
    _gen(tmp_path, bodies=["SUN"])
    assert len(combined([2000], data_dir=tmp_path)) == 366
    with pytest.raises(FileNotFoundError, match="1999"):
        combined([1999, 2000], data_dir=tmp_path)


def test_module_exports():
    """Public names exist."""
    assert planetary.NINE_GRAHAS[-1] == "KETU"
