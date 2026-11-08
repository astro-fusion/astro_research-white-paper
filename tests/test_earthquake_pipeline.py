"""Unit tests for the earthquake pipeline's family and split logic."""

import sys

import numpy as np
import pandas as pd

from studies._paths import study_dir

sys.path.insert(0, str(study_dir("earthquake") / "scripts"))

import fetch_catalogue as fc  # noqa: E402
import indicators as ind  # noqa: E402
import pipeline  # noqa: E402

HYP = fc.load_hypothesis()


def test_hypothesis_is_complete():
    """The pre-registration fixes every parameter the pipeline reads."""
    assert len(HYP["indicators"]) == 13
    assert HYP["test"]["n_draws"] == 10000 and HYP["test"]["seed"] == 42
    assert HYP["test"]["correction"] == "benjamini_yekutieli"
    assert HYP["split"]["explore"][1] < HYP["split"]["confirm"][0]
    ids = [i["id"] for i in HYP["indicators"]]
    assert len(set(ids)) == len(ids)


def test_period_slices_do_not_overlap():
    """Exploration ends where confirmation starts."""
    grid = ind.time_grid("2009-12-01", "2011-03-01", 1)
    sl = pipeline.period_slices(HYP, grid)
    assert grid[sl["explore"].stop - 1] < pd.Timestamp("2011-01-01", tz="UTC")
    assert grid[sl["confirm"].start] == pd.Timestamp("2011-01-01", tz="UTC")


def _tests_frame(p_explore, rr_explore, p_confirm):
    rows = []
    for period, ps, rrs in (("explore", p_explore, rr_explore),
                            ("confirm", p_confirm, rr_explore)):
        for k, (p, rr) in enumerate(zip(ps, rrs)):
            for cat in ("gk", "nn", "raw"):
                rows.append({"catalogue": cat, "period": period,
                             "indicator": f"i{k}", "direction": "greater",
                             "rate_ratio": rr, "p_value": p, "skipped": ""})
    return pd.DataFrame(rows)


def test_only_significant_pairs_in_direction_are_carried():
    """BY across gk+nn; a low p with RR < 1 is not carried."""
    tests = _tests_frame([1e-5, 1e-5, 0.5], [2.0, 0.5, 1.1], [1e-4, 0.5, 0.5])
    t = pipeline.family_tables(HYP, tests)
    fam = t["family"].set_index(["catalogue", "indicator"])
    assert (fam["family_size"] == 6).all()
    assert fam.loc[("gk", "i0"), "carried"]
    assert not fam.loc[("gk", "i1"), "carried"]
    assert not fam.loc[("gk", "i2"), "carried"]
    conf = t["confirmation"].set_index(["catalogue", "indicator"])
    assert conf.loc[("gk", "i0"), "confirmed"]
    assert not conf.loc[("gk", "i1"), "confirmed"]
    assert np.isnan(conf.loc[("gk", "i2"), "q_value"])
    assert set(t["raw"]["catalogue"]) == {"raw"}
