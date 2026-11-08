"""Tests for the astrological indicator grid (known 2020 configurations)."""

import sys

import numpy as np
import pandas as pd
import pytest

from studies._paths import study_dir

sys.path.insert(0, str(study_dir("earthquake") / "scripts"))

import fetch_catalogue as fc  # noqa: E402
import indicators as ind  # noqa: E402

from vedic_astrology_core.astrology.ephemeris import EphemerisEngine  # noqa: E402

HYP = fc.load_hypothesis()


def test_window_mask_and_sign_changes():
    """Window edges are inclusive and clipped; sign changes are located."""
    m = ind.window_mask(10, [0, 6], 1)
    assert m.tolist() == [1, 1, 0, 0, 0, 1, 1, 1, 0, 0]
    assert ind.sign_change_bins([1.0, 0.5, -0.2, -0.1, 0.3]).tolist() == [2, 4]
    assert ind.separation(359.0, 2.0) == pytest.approx(3.0)


def test_event_bins_and_grid_bounds():
    """Events map to the hour that contains them; outside raises."""
    grid = ind.time_grid("2020-01-01", "2020-01-02", 1)
    assert len(grid) == 24 and str(grid.tz) == "UTC"
    bins = ind.event_bins(["2020-01-01T00:59:59Z", "2020-01-01T13:00:00Z"], grid)
    assert bins.tolist() == [0, 13]
    with pytest.raises(ValueError):
        ind.event_bins(["2020-01-02T00:00:01Z"], grid)


@pytest.fixture(scope="module")
def spring_2020():
    """Build indicators for 2020-02-01 .. 2020-07-01 on an hourly grid."""
    grid = ind.time_grid("2020-02-01", "2020-07-01", 1)
    eph = ind.ephemeris_frame(grid, EphemerisEngine())
    return ind.build_indicators(HYP, eph)


def _at(frame, ts):
    return frame.loc[pd.Timestamp(ts, tz="UTC")]


def test_known_configurations_2020(spring_2020):
    """Mars-Saturn conjunction 31 Mar, Mercury station 17 Feb, eclipse 21 Jun."""
    f = spring_2020
    assert _at(f, "2020-03-31 12:00")["mars_saturn_conj"]
    assert not _at(f, "2020-06-01 12:00")["mars_saturn_conj"]
    assert _at(f, "2020-02-17 00:00")["station_mercury"]
    assert not _at(f, "2020-03-25 00:00")["station_mercury"]
    assert _at(f, "2020-06-21 06:00")["eclipse_window"]
    assert _at(f, "2020-06-28 00:00")["eclipse_window"]
    assert not _at(f, "2020-05-01 00:00")["eclipse_window"]
    # Sun enters sidereal Aries around 13-14 April.
    assert _at(f, "2020-04-13 12:00")["sun_ingress"]
    assert f.attrs["n_solar_eclipses"] >= 1


def test_mandalas_partition_the_moon(spring_2020):
    """Every hour has the Moon in exactly one mandala; Abhijit is not used."""
    cols = [c for c in spring_2020 if c.startswith("moon_mandala_")]
    total = spring_2020[cols].sum(axis=1)
    assert (total == 1).all()
    fractions = spring_2020[cols].mean()
    assert np.isclose(fractions.sum(), 1.0)
