"""Strategy audit 2 diagnosis package (DIAG): gate reasons, tz-aware grids, earthquake pins.

Each test failed on the code before the DIAG change and passes after it.

* Gate: a calendar whose episodes exist but whose blocks lose their control
  time (alternate-year monsoon calendars) is "no_clean_control", not "too few
  episodes"; the abilities themselves do not change (no rule is loosened).
* Pipeline: a tz-aware grid no longer stops the run (naive period bounds were
  compared with tz-aware bars) and gives the same records as the naive grid.
* Earthquake adapter (N-21, D-03, D-05): an explicit snapshot file does not
  bypass the pin, the pinned file's bytes are checked on every read, and
  grade inputs cannot be passed to the constructor.
"""

from __future__ import annotations

import json
import shutil
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

from studies._paths import REPO_ROOT
from vedic_astrology_core.validity import pipeline as P
from vedic_astrology_core.validity.gate import GateSpec, run_gate

PINNED = "d3d3d6ec840599341782147b35579b69dae3919dd2668d762659270baef19972"


# ------------------------------------------------------------------ gate
def _years(n=69, start=1948):
    return pd.DatetimeIndex([pd.Timestamp(start + i, 7, 1) for i in range(n)])


def _spec(**kw):
    base = dict(test_id="t", side="less", outcome_type="continuous", a_test=0.04 / 7, merge_gap=0,
                level=2, sesoi=None, power_reps=10)
    base.update(kw)
    return GateSpec(**base)


#: monsoon.mars_in_rohini_deficit@1 on the 1948-2016 seasons (the preview's calendar).
ROHINI = ".A.A.A.A.A.AA.A.A.A.A.A.A.AA.A.A.A.A.A.A.AAAA.A.A.A.A.A.A.AA.A.A.A.A."


def test_alternate_year_calendar_is_no_clean_control_not_too_few_episodes():
    """31 episodes, but a one-year gap has no half for either neighbour (ADR-008 1.1 item 2)."""
    dates = _years()
    cal = np.array([c == "A" for c in ROHINI])
    confirm = dates.year >= 1983
    g = run_gate(cal, dates, confirm, _spec(plan_seed=20261125))
    assert g.full["n_episodes"] == 31 and g.full["n_used"] == 2
    assert g.full["drop_counts"]["no_control"] == 29
    assert g.untestable and g.untestable_reason == "no_clean_control"
    assert "no_clean_control" in g.limit_failed and "no_clean_control" in g.support_failed
    assert "too_few_episodes" not in g.limit_failed + g.support_failed
    assert not g.can_support and not g.can_limit  # the abilities are unchanged


def test_few_episodes_without_dropped_blocks_stay_too_few_episodes():
    dates = _years()
    cal = np.zeros(len(dates), dtype=bool)
    cal[[5, 20, 40, 60]] = True  # four clean episodes
    g = run_gate(cal, dates, dates.year >= 1983, _spec())
    assert g.full["drop_counts"].get("no_control", 0) == 0
    assert g.untestable_reason == "too_few_episodes"
    assert "too_few_episodes" in g.limit_failed


# ------------------------------------------------------------------ tz grid
def test_mask_between_accepts_a_tz_aware_grid():
    naive = pd.DatetimeIndex(pd.date_range("1999-12-30 22:00", periods=6, freq="h"))
    aware = naive.tz_localize("UTC")
    per = (date(1999, 12, 31), date(2000, 12, 31))
    np.testing.assert_array_equal(P._mask_between(aware, per), P._mask_between(naive, per))
    assert P._mask_between(aware, per).tolist() == [False, False, True, True, True, True]


def test_pipeline_runs_on_a_tz_aware_grid_with_the_naive_grid_numbers(tmp_path):
    from tests.test_validity_pipeline import (START, YEARS, FakeSeal, PlantedDomain, definition, make_lock,
                                              run_spec)

    class AwareDomain(PlantedDomain):
        def grid(self):
            return list(pd.DatetimeIndex([pd.Timestamp(START + i, 1, 1) for i in range(YEARS)]).tz_localize("UTC"))

    recs = {}
    for name, cls in (("naive", PlantedDomain), ("aware", AwareDomain)):
        d = tmp_path / name
        tests = [definition()]
        lock = make_lock(d, tests, close=False)
        dom = cls(seed=3, effect=1.0, run_dir=d / "run")
        res = P.run_domain(dom, run_spec(), tests, lock, d / "run", sealer=FakeSeal)
        recs[name] = res["records"][0]
    for key in ("p", "effect", "bound", "verdict"):
        assert recs["aware"][key] == recs["naive"][key], key
    assert recs["aware"]["gate"]["file_sha256"] == recs["naive"]["gate"]["file_sha256"]


# ------------------------------------------------------------------ earthquake pins
def _registers():
    index = json.loads((REPO_ROOT / "data" / "snapshot_index.json").read_text())
    lic = yaml.safe_load((REPO_ROOT / "data" / "registry" / "licences.yaml").read_text())
    return index, lic.get("sources", lic)


def _tampered(tmp_path: Path) -> Path:
    index, _ = _registers()
    src = REPO_ROOT / next(s["file"] for s in index["snapshots"] if s["sha256"] == PINNED)
    dst = tmp_path / "usgs_tampered.csv"
    shutil.copyfile(src, dst)
    with dst.open("a", encoding="utf-8") as f:
        f.write("\n")  # one byte more: same rows, other hash
    return dst


def test_explicit_snapshot_does_not_bypass_the_pin(tmp_path):
    from vedic_astrology_core.domains.earthquake import EarthquakeDomain, PinError

    index, lic = _registers()
    bad = _tampered(tmp_path)
    with pytest.raises(PinError):
        EarthquakeDomain(index, lic, snapshot=bad).snapshot_path()  # no pin at all
    with pytest.raises(PinError):
        EarthquakeDomain(index, lic, snapshot=bad, pinned_sha256=PINNED).catalogue()  # wrong bytes


def test_pinned_snapshot_bytes_are_checked_on_read(tmp_path):
    from vedic_astrology_core.domains.earthquake import EarthquakeDomain, PinError

    index, lic = _registers()
    bad = _tampered(tmp_path)
    swapped = {**index, "snapshots": [{**s, "file": str(bad)} if s["sha256"] == PINNED else s
                                      for s in index["snapshots"]]}
    adapter = EarthquakeDomain(swapped, lic, pinned_sha256=PINNED)
    with pytest.raises(PinError):
        adapter.catalogue()
    with pytest.raises(PinError):
        adapter.dataset()
    good = EarthquakeDomain(index, lic, pinned_sha256=PINNED)
    assert good.verified_snapshot()[1] == PINNED


def test_earthquake_constructor_takes_no_grade_rows():
    from vedic_astrology_core.domains.earthquake import EarthquakeDomain

    with pytest.raises(TypeError):
        EarthquakeDomain({}, {}, grades=[{"sha256": PINNED, "reproduced": True, "checked_by": "x",
                                          "date": "2026-11-23"}])
