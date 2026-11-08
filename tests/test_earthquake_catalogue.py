"""Tests for the earthquake catalogue helpers (region, Mw, completeness)."""

import sys

import numpy as np
import pandas as pd
import pytest

from studies._paths import study_dir

sys.path.insert(0, str(study_dir("earthquake") / "scripts"))

import fetch_catalogue as fc  # noqa: E402

HYP = fc.load_hypothesis()


def test_polygon_contains_known_himalayan_events_only():
    """Gorkha 2015 and Sikkim 2011 are inside; Lhasa and Delhi are outside."""
    poly = fc.region_polygon(HYP["region"])
    assert np.allclose(poly[0], poly[-1])
    lon = [84.73, 88.16, 91.1, 77.2]
    lat = [28.23, 27.73, 29.65, 28.6]
    assert fc.in_polygon(lon, lat, poly).tolist() == [True, True, False, False]


def test_homogenise_known_conversions():
    """Scordilis (2006) mb and Ms relations; moment magnitudes unchanged."""
    df = pd.DataFrame(
        {"mag": [5.0, 5.0, 6.5, 7.8, 4.5], "magType": ["mb", "ms", "ms", "mww", "ml"]}
    )
    out = fc.homogenise_mw(df, HYP["magnitude"]["rules"])
    np.testing.assert_allclose(
        out["mw"], [0.85 * 5 + 1.03, 0.67 * 5 + 2.07, 0.99 * 6.5 + 0.08, 7.8, 4.5]
    )
    assert out["mw_rule"].tolist() == [
        "scordilis_mb",
        "scordilis_ms",
        "scordilis_ms",
        "moment",
        "as_reported",
    ]


def test_maximum_curvature_known_answer():
    """The modal 0.1 bin plus 0.2."""
    mags = [4.1] * 3 + [4.3] * 10 + [4.4] * 7 + [5.0] * 2
    assert fc.mc_maxc(mags) == pytest.approx(4.5)
    with pytest.raises(ValueError):
        fc.mc_maxc([np.nan])


def test_completeness_uses_worst_decade_on_mb():
    """The worst decade's mb Mc, converted to Mw, is the threshold."""
    times = ["1985-06-01T00:00:00Z"] * 60 + ["1995-06-01T00:00:00Z"] * 60
    mags = [4.6] * 40 + [4.9] * 20 + [4.3] * 40 + [4.8] * 20
    df = pd.DataFrame({"time": times, "mag": mags, "magType": "mb"})
    df = fc.homogenise_mw(df, HYP["magnitude"]["rules"])
    comp = fc.completeness(df, HYP["magnitude"])
    assert comp["mc_mb_per_decade"] == {1980: 4.8, 1990: 4.5}
    assert comp["threshold"] == pytest.approx(0.85 * 4.8 + 1.03)


def test_offline_json_maps_to_fdsn_schema():
    """The tracked JSON loads with the FDSN columns and filters to the arc."""
    df = fc.load_offline()
    assert set(fc.COLUMNS) <= set(df.columns)
    assert len(df) == 370
    kept = fc.filter_region(df, HYP)
    assert 0 < len(kept) < len(df)
    assert kept["time"].is_monotonic_increasing
