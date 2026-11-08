"""Tests for atlas clause evaluation and the shared-offset family test."""

import importlib.util

import numpy as np
import pandas as pd

from studies._paths import STUDIES_ROOT

SCRIPTS = STUDIES_ROOT / "combinations" / "scripts"


def _load(name, file):
    """Build the load fixture."""
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / file)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


atlas = _load("atlas_core", "atlas.py")
enum = _load("atlas_enumerate_eval", "enumerate.py")
GRAMMAR = enum.load_grammar()


def _sky(lons, lagna=0, md="SATURN", ad="MARS"):
    """Build the sky fixture."""
    n = len(next(iter(lons.values())))
    eph = pd.DataFrame(
        {f"lon_{p}": np.full(n, 0.0) for p in atlas.PLANETS if p != "RAHU"}
    )
    for p, v in lons.items():
        eph[f"lon_{p}"] = v
    dasha = {
        1: np.full(n, atlas.PLANETS.index(md), dtype=np.int8),
        2: np.full(n, atlas.PLANETS.index(ad), dtype=np.int8),
    }
    return atlas.sky_state(eph, np.full(n, lagna), dasha)


def test_placements():
    """Check placements."""
    sky = _sky(
        {"MARS": np.array([5.0, 35.0, 215.0]), "MOON": np.array([0, 0, 200.0])}, lagna=1
    )
    m = atlas.clause_mask(
        {"kind": "placement", "planet": "MARS", "frame": "sign", "value": 1},
        sky,
        GRAMMAR,
    )
    assert m.tolist() == [False, True, False]
    h = atlas.clause_mask(
        {
            "kind": "placement",
            "planet": "MARS",
            "frame": "house_from_lagna",
            "value": 0,
        },
        sky,
        GRAMMAR,
    )
    assert h.tolist() == [False, True, False]
    hm = atlas.clause_mask(
        {"kind": "placement", "planet": "MARS", "frame": "house_from_moon", "value": 1},
        sky,
        GRAMMAR,
    )
    assert hm.tolist() == [False, True, True]
    # Rahu is Ketu + 180: Ketu at 0 puts Rahu in Libra.
    r = atlas.clause_mask(
        {"kind": "placement", "planet": "RAHU", "frame": "sign", "value": 6},
        sky,
        GRAMMAR,
    )
    assert r.all()
    # Ashvini (0 deg) is Ketu-ruled: group 0.
    k = atlas.clause_mask(
        {"kind": "placement", "planet": "SUN", "frame": "nakshatra_group", "value": 0},
        sky,
        GRAMMAR,
    )
    assert k.all()


def test_special_aspects_and_conjunction():
    # Mars in Aries; Saturn in Cancer (4th), Libra (7th), Scorpio (8th), Leo (5th).
    """Check special aspects and conjunction."""
    sky = _sky(
        {
            "MARS": np.full(4, 10.0),
            "SATURN": np.array([100.0, 190, 220, 130]),
            "JUPITER": np.full(4, 10.0),
        }
    )
    a = atlas.clause_mask(
        {"kind": "aspect", "from": "MARS", "to": "SATURN"}, sky, GRAMMAR
    )
    assert a.tolist() == [True, True, True, False]
    j = atlas.clause_mask(
        {"kind": "aspect", "from": "JUPITER", "to": "SATURN"}, sky, GRAMMAR
    )
    assert j.tolist() == [False, True, False, True]
    c = atlas.clause_mask(
        {"kind": "conjunction", "a": "MARS", "b": "JUPITER"}, sky, GRAMMAR
    )
    assert c.all()


def test_dasha_and_candidate_and():
    """Check dasha and candidate and."""
    sky = _sky({"MARS": np.array([5.0, 35.0])})
    cand = {
        "clauses": [
            {"kind": "placement", "planet": "MARS", "frame": "sign", "value": 0},
            {"kind": "dasha", "planet": "SATURN", "level": 1},
        ]
    }
    assert atlas.candidate_mask(cand, sky, GRAMMAR, cache={}).tolist() == [True, False]
    d2 = atlas.clause_mask(
        {"kind": "dasha", "planet": "MARS", "level": 2}, sky, GRAMMAR
    )
    assert d2.all()


def test_shift_family_finds_a_planted_candidate_and_controls_fwer():
    """Check shift family finds a planted candidate and controls fwer."""
    rng = np.random.default_rng(0)
    n = 40_000
    masks = []
    for k in range(30):
        m = np.zeros(n, dtype=bool)
        for s in range(rng.integers(0, 500), n, 1000 + 37 * k):
            m[s : s + 150] = True
        masks.append((f"c{k}", m))
    planted = masks[0][1]
    rate = np.where(planted, 0.02, 0.004)
    events = np.flatnonzero(rng.random(n) < rate)
    sparse = np.zeros(n, dtype=bool)
    sparse[:3] = True
    masks.append(("sparse", sparse))
    out = atlas.shift_family(
        masks, events, n, 2000, 499, np.random.default_rng(1), min_expected=3
    )
    top = out[out["testable"]].sort_values("p_value").iloc[0]
    assert top["id"] == "c0" and top["rate_ratio"] > 3
    assert top["p_rw"] <= 0.01
    assert not out.set_index("id").loc["sparse", "testable"]
    assert np.isnan(out.set_index("id").loc["sparse", "p_rw"])
    others = out[out["testable"] & (out["id"] != "c0")]
    assert (others["p_rw"] >= top["p_rw"]).all()
