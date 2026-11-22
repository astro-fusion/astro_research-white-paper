"""markets.placebo: placebo skies, rank logic and ayanamsa sensitivity."""

import numpy as np
import pandas as pd
import pytest

from vedic_astrology_core.astrology.ephemeris import EphemerisEngine
from vedic_astrology_core.markets import features, placebo

ENGINE = EphemerisEngine()
INDEX = pd.date_range("2000-01-01 12:00", periods=40, freq="7D", tz="UTC")
SPECS = [
    {"id": "sat_aries", "kind": "in_sign", "body": "Saturn", "signs": ["Aries"]},
    {"id": "moon_retro", "kind": "retrograde", "body": "Mars"},
]


@pytest.fixture(scope="module")
def frame():
    """Lahiri frame for Sun, Moon, Mars, Saturn over 40 weeks."""
    return features.indicator_frame(INDEX, ["Sun", "Moon", "Mars", "Saturn"], ENGINE, 0)


def test_rank_of_real_mid_ranks_ties():
    """A-01: rank is 1 + larger placebos + half the ties; p never zero."""
    out = placebo.rank_of_real(5.0, [1, 2, 5, 7])
    assert out["rank"] == 2.5 and out["p_value"] == pytest.approx(2.5 / 5)
    assert out["n_greater"] == 1 and out["n_tied"] == 1
    assert placebo.rank_of_real(5.0, [1, 2, 5, 7], ties="against")["rank"] == 3
    assert placebo.rank_of_real(9.0, [1, 2])["rank"] == 1
    # all placebos equal to the real sky: not p = 1 any more
    assert placebo.rank_of_real(3.0, [3.0] * 19)["p_value"] == pytest.approx(10.5 / 20)
    r = placebo.rank_of_real(3.0, [3.0] * 19, ties="random", rng=np.random.default_rng(0))
    assert 1 <= r["rank"] <= 20
    with pytest.raises(ValueError):
        placebo.rank_of_real(1.0, [])
    with pytest.raises(ValueError):
        placebo.rank_of_real(1.0, [1.0], ties="random")


def test_offsets_respect_the_400_day_floor_and_are_distinct():
    """Offsets are distinct, at least 400 days in size, both signs."""
    rng = np.random.default_rng(1)
    offs = placebo.shift_offsets(200, rng)
    assert len(set(offs)) == 200 and np.abs(offs).min() >= 400
    assert (offs < 0).any() and (offs > 0).any()
    with pytest.raises(ValueError):
        placebo.shift_offsets(5, rng, min_days=399)
    with pytest.raises(ValueError):
        placebo.shifted_sky_frame(INDEX, 399, lambda i: None)


def test_shifted_sky_is_the_sky_of_the_other_date(frame):
    """The shifted frame carries the original index but the other date's sky."""
    seen = {}

    def builder(inst):
        seen["inst"] = inst
        return features.indicator_frame(inst, ["Saturn"], ENGINE)

    out = placebo.shifted_sky_frame(INDEX[:3], 400, builder)
    assert (seen["inst"] - INDEX[:3] == pd.Timedelta(days=400)).all()
    assert out.index.equals(INDEX[:3])


def test_rezodiac_zero_is_identity_and_tropical_moves_signs(frame):
    """Zero shift keeps labels; the tropical shift moves longitudes by ~24 deg."""
    same = placebo.rezodiac(frame, 0.0, lagna_sign=0)
    pd.testing.assert_frame_equal(same, frame)
    trop = placebo.rezodiac(frame, 24.0, lagna_sign=0)
    gap = (trop["SUN_lon"] - frame["SUN_lon"]) % 360
    assert np.allclose(gap, 24.0)
    assert (trop["SUN_sign"] != frame["SUN_sign"]).any()
    assert trop["MARS_retro"].equals(frame["MARS_retro"])


def test_scramble_is_a_permutation_of_labels(frame):
    """Scrambling keeps label counts' structure: equal signs stay equal."""
    out = placebo.scramble_signs(frame, np.random.default_rng(3), lagna_sign=0)
    pairs = set(zip(frame["SUN_sign"], out["SUN_sign"]))
    assert len({a for a, _ in pairs}) == len(pairs)  # one-to-one
    assert len({b for _, b in pairs}) == len(pairs)


def test_placebo_skies_ranks_a_planted_signal():
    """A statistic that reads the real sky ranks first; placebos cannot."""
    bodies = ["Sun", "Moon", "Mars", "Saturn"]
    idx = pd.date_range("2000-01-01 12:00", periods=30, freq="30D", tz="UTC")
    base = features.indicator_frame(idx, bodies, ENGINE, 0)
    real_ind = features.build_indicators(
        base, [{"id": "r", "kind": "in_sign", "body": "Saturn", "signs": ["Aries"]}]
    )["r"].to_numpy()
    outcome = real_ind.astype(float)

    def stat(ind):
        return {c: abs(float(np.corrcoef(ind[c].to_numpy(float), outcome)[0, 1]))
                if ind[c].any() and not ind[c].all() else 0.0 for c in ind.columns}

    specs = [{"id": "r", "kind": "in_sign", "body": "Saturn", "signs": ["Aries"]}]
    res = placebo.placebo_skies(
        idx, bodies, specs, stat, n_placebo=8, seed=5, engine=ENGINE,
        lagna_sign=0, base_frame=base, max_offset_days=1500,
    )
    assert res["real_max"] == pytest.approx(1.0)
    assert res["kinds"]["shift"]["rank"] == 1
    assert res["kinds"]["shift"]["n_placebo"] == 8
    assert min(abs(o) for o in res["kinds"]["shift"]["offsets_days"]) >= 400
    assert res["kinds"]["scramble"]["n_placebo"] == 8
    assert res["kinds"]["tropical"]["deterministic"] is True
    with pytest.raises(ValueError):
        placebo.placebo_skies(idx, bodies, specs, stat, kinds=["nope"], engine=ENGINE)


def test_ayanamsa_sensitivity_counts_changed_bars(frame):
    """Lahiri against itself changes nothing; KP and Raman move some bars."""
    # Pick a body-sign boundary sample: Moon sign changes every ~2.3 days.
    from vedic_astrology_core.astrology.ayanamsa import SIGN_NAMES_LIST

    specs = [
        {"id": f"moon_{s}", "kind": "in_sign", "body": "Moon", "signs": [s]}
        for s in SIGN_NAMES_LIST
    ]
    out = placebo.ayanamsa_sensitivity(frame, specs, engine=ENGINE, lagna_sign=0)
    assert out["n_bars"] == len(INDEX)
    assert out["variants"]["lahiri"]["any_changed"] == 0
    for name in ("raman", "krishnamurti", "true_chitrapaksha"):
        v = out["variants"][name]
        assert 0 <= v["any_changed"] <= len(INDEX)
        assert len(v["bars_changed"]) == 12
    # Raman differs from Lahiri by ~1.4 deg: over 40 bars some Moon bars flip.
    assert out["variants"]["raman"]["any_changed"] > 0
    # True Chitrapaksha is within ~arcminutes of Lahiri: far fewer flips.
    assert (
        out["variants"]["true_chitrapaksha"]["any_changed"]
        <= out["variants"]["raman"]["any_changed"]
    )


def test_ayanamsa_sensitivity_flags_rules_and_tolerates_vanishing_indicator(frame):
    """Rule columns are listed as not rebuilt; a vanished indicator counts zero."""
    f = frame.copy()
    f["rule:x"] = False
    f.loc[f.index[0], "rule:x"] = True
    specs = [{"id": "x", "kind": "rule", "rule": "x"}]
    out = placebo.ayanamsa_sensitivity(f, specs, engine=ENGINE)
    assert out["rules_not_rebuilt"] == ["x"]
    assert out["variants"]["raman"]["any_changed"] == 0


def test_discrete_principles_can_pass_the_placebo_check():
    """A-01: retrograde and tithi indicators with a real effect rank first
    among the shifted skies; the scramble and tropical placebos, which do not
    move them, are "not applicable" instead of failing them with p = 1."""
    bodies = ["Sun", "Moon", "Mercury"]
    idx = pd.date_range("2001-01-01 12:00", periods=160, freq="5D", tz="UTC")
    base = features.indicator_frame(idx, bodies, ENGINE, 0)
    specs = [
        {"id": "merc_retro", "kind": "retrograde", "body": "Mercury"},
        {"id": "waxing", "kind": "tithi", "tithis": list(range(1, 16))},
    ]
    real = features.build_indicators(base, specs)
    rng = np.random.default_rng(4)
    # Outcome with a true effect of both indicators plus noise.
    outcome = 1.5 * real["merc_retro"].to_numpy(float) + 1.0 * real["waxing"].to_numpy(float)
    outcome = outcome + rng.normal(0, 0.5, len(idx))

    def stat(ind):
        return {c: abs(float(np.corrcoef(ind[c].to_numpy(float), outcome)[0, 1]))
                if ind[c].any() and not ind[c].all() else 0.0 for c in ind.columns}

    res = placebo.placebo_skies(idx, bodies, specs, stat, n_placebo=39, seed=1, engine=ENGINE,
                                lagna_sign=0, base_frame=base, max_offset_days=4000)
    shift = res["kinds"]["shift"]["per_indicator"]
    assert shift["merc_retro"]["applicable"] and shift["merc_retro"]["rank"] == 1
    assert shift["merc_retro"]["p_value"] <= 0.05
    # A shift close to a whole number of synodic months re-creates the tithi
    # sky (module docstring), so a few shifted skies match the real one.
    assert shift["waxing"]["applicable"] and shift["waxing"]["p_value"] < 0.1
    for kind in ("scramble", "tropical"):
        per = res["kinds"][kind]["per_indicator"]
        for i in ("merc_retro", "waxing"):
            assert per[i]["applicable"] is False and per[i]["p_value"] is None
        assert res["kinds"][kind]["applicable"] is False


def test_rezodiac_moves_the_lagna_with_the_planets():
    """m6: houses never count tropical planets from a sidereal lagna."""
    frame = pd.DataFrame({"SUN_lon": [355.0], "SUN_sign": ["Pisces"], "SUN_house": [1]},
                         index=pd.DatetimeIndex(["2000-01-01"], tz="UTC"))
    trop = placebo.rezodiac(frame, 24.0, lagna_sign=11)  # degree of the lagna unknown
    assert trop["SUN_sign"].iloc[0] == "Aries" and trop["SUN_house"].iloc[0] == 1
    moved = placebo.rezodiac(frame, 24.0, lagna_sign=11, lagna_lon=345.0)
    assert moved["SUN_house"].iloc[0] == 1  # lagna 345 + 24 = 9 deg Aries
    late = placebo.rezodiac(frame, 24.0, lagna_sign=11, lagna_lon=330.5)
    assert late["SUN_house"].iloc[0] == 2  # lagna 354.5 deg stays in Pisces
