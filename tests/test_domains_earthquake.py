"""WP-77: earthquake adapter."""

import numpy as np
import pytest

from vedic_astrology_core.domains.base import GateHashError
from vedic_astrology_core.domains.earthquake import EarthquakeDomain
from studies._paths import REPO_ROOT

import json

import yaml

GATE = "cd" * 32


@pytest.fixture(scope="module")
def adapter():
    index = json.loads((REPO_ROOT / "data" / "snapshot_index.json").read_text())
    lic = yaml.safe_load((REPO_ROOT / "data" / "registry" / "licences.yaml").read_text())
    lic = lic.get("sources", lic)
    return EarthquakeDomain(index, lic)


@pytest.fixture(scope="module")
def outcomes(adapter):
    return adapter.outcomes(GATE)


def test_outcomes_and_controls_need_gate(adapter):
    with pytest.raises(GateHashError):
        adapter.outcomes()
    with pytest.raises(GateHashError):
        adapter.controls("nope")


def test_grid_is_hourly_utc_from_plan(adapter):
    g = adapter.grid()
    assert str(g.tz) == "UTC"
    assert (g[1] - g[0]).total_seconds() == 3600
    assert str(g[0]) == "1976-01-01 00:00:00+00:00"
    assert str(g[-1]) == "2026-10-31 23:00:00+00:00"
    ctx = adapter.calendar_context()
    assert len(ctx["monsoon_season"]) == len(g)


def test_periods_pseudo_oos(adapter):
    p = adapter.periods()
    assert p.pseudo_out_of_sample
    assert p.explore[1].year == 2010 and p.confirm[0].year == 2011


def test_dataset_grade_b_with_isc_open_item(adapter):
    ds = adapter.dataset()
    assert ds.grade == "B"
    assert any("ISC" in x for x in ds.limitations)
    assert ds.sha256.startswith("d3d3d6ec8405")


def test_mainshock_counts_match_ledger(outcomes):
    c = outcomes["mainshock_counts"]
    assert c["gk"]["all"] == 186 and c["gk"]["explore"] == 128 and c["gk"]["confirm"] == 58
    assert c["nn"]["all"] == 214 and c["nn"]["explore"] == 144 and c["nn"]["confirm"] == 70
    assert c["raw"]["all"] == 297
    assert len(outcomes["event_bins"]) == 186
    assert outcomes["declustering"] == "gk"


def test_declustering_method_is_a_declared_cell(adapter):
    cells = adapter.declared_cells()["declustering"]
    assert cells["primary"] == "gk" and set(cells["sensitivity"]) == {"nn", "raw"}
    with pytest.raises(ValueError):
        EarthquakeDomain({}, {}, declustering="magic")


def test_controls_declared_as_principles(adapter):
    c = adapter.controls(GATE)
    ids = [x["id"] for x in c["positive"]]
    assert ids == [
        "control.tide_semidiurnal_peak",
        "control.tide_spring",
        "control.tide_spring_and_peak",
    ]
    offs = [x["offset_days"] for x in c["negative"]]
    assert 3001 in offs and len(offs) >= 5 and min(offs) >= 767


def test_shifted_sky_rotates(adapter):
    import pandas as pd

    f = pd.DataFrame({"a": np.arange(10)})
    out = adapter.shifted_sky(f, 3)
    assert sorted(out["a"]) == list(range(10)) and out["a"].tolist() != list(range(10))
