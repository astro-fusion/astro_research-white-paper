"""Tests for Gardner-Knopoff and nearest-neighbour declustering."""

import sys

import numpy as np
import pandas as pd
import pytest

from studies._paths import study_dir

sys.path.insert(0, str(study_dir("earthquake") / "scripts"))

import decluster as dc  # noqa: E402


def _catalogue(rows, unit="us"):
    df = pd.DataFrame(rows, columns=["time", "latitude", "longitude", "mw"])
    df["time"] = pd.to_datetime(df["time"], utc=True).astype(f"datetime64[{unit}, UTC]")
    return df


def test_haversine_known_distance():
    """One degree of latitude is about 111.2 km."""
    assert dc.haversine_km(0.0, 0.0, 1.0, 0.0) == pytest.approx(111.19, abs=0.05)


def test_gk_windows_known_values():
    """Window formulas at M 5 and M 7."""
    d, t = dc.gk_windows([5.0, 7.0])
    assert d[0] == pytest.approx(10 ** (0.1238 * 5 + 0.983))
    assert t[0] == pytest.approx(10 ** (0.5409 * 5 - 0.547))
    assert t[1] == pytest.approx(10 ** (0.032 * 7 + 2.7389))


@pytest.mark.parametrize("unit", ["ns", "us", "s"])
def test_gk_removes_aftershocks_and_foreshocks_only(unit):
    """Nearby smaller events within the window go; distant or late ones stay.

    Run with several datetime units: a units bug once made every event a
    few days apart.
    """
    cat = _catalogue(
        [
            ("2000-01-01", 28.0, 85.0, 6.0),  # mainshock
            ("2000-01-05", 28.1, 85.1, 5.0),  # aftershock, 15 km, 4 days
            ("1999-12-30", 28.05, 85.0, 4.8),  # foreshock
            ("2000-01-05", 31.0, 79.0, 5.0),  # far away
            ("2003-01-01", 28.0, 85.0, 5.0),  # years later
        ],
        unit,
    )
    keep = dc.gardner_knopoff(cat)
    assert keep.tolist() == [True, False, False, True, True]


def test_nearest_neighbour_separates_clusters_from_background():
    """Tight clusters are flagged; widely spaced background is kept."""
    rng = np.random.default_rng(0)
    rows = []
    for k in range(60):  # background: random times over 30 years, random places
        t = pd.Timestamp("1990-01-01", tz="UTC") + pd.Timedelta(
            days=float(rng.uniform(0, 30 * 365))
        )
        rows.append((t, rng.uniform(27, 31), rng.uniform(78, 92), 5.3))
    for k in range(8):  # clusters: 6 aftershocks within hours and 5 km
        t0 = pd.Timestamp("1990-01-01", tz="UTC") + pd.Timedelta(days=1000 * k + 7)
        lat, lon = rng.uniform(27, 31), rng.uniform(78, 92)
        rows.append((t0, lat, lon, 6.0))
        for _ in range(6):
            rows.append(
                (
                    t0 + pd.Timedelta(hours=float(rng.uniform(1, 48))),
                    lat + rng.normal(0, 0.03),
                    lon + rng.normal(0, 0.03),
                    5.2,
                )
            )
    cat = _catalogue(rows).sort_values("time").reset_index(drop=True)
    keep, fit = dc.nearest_neighbour(cat)
    is_after = cat["mw"].eq(5.2).to_numpy()
    assert fit["separated"]
    assert (~keep.to_numpy()[is_after]).mean() > 0.9
    assert keep.to_numpy()[~is_after].mean() > 0.85


def test_gmm_falls_back_when_unimodal():
    """A single Gaussian does not separate; the fallback threshold is used."""
    fit = dc.gmm_threshold(np.random.default_rng(1).normal(size=2000))
    assert not fit["separated"] and fit["threshold"] == -5.0
