"""ADR-008 WP-100: generators and cases of the yearly-grid proof (A3.3, Y1 to Y11).

Committed before the year test (core/stats/yearly.py, WP-101). Two jobs:

1. Prove each generator in tests/simulators.py against its stated moments, so
   a pass of the year test cannot come from a generator that is too kind.
2. Fix the case list (YEARLY_CASES) and the runner (run_null_case) that
   WP-101 and the certificate call. Any test with the signature
   test(y, active, years, driver, rng) -> {"greater": p, "less": p}
   (one-sided p-values for each side) can be run through a case. The cases
   fail against stubs: a test that always rejects, and the naive designs A3.3
   Y10 keeps on record. A trivially valid stub (uniform p) passes.

Past data only; nothing here forecasts. Real calendars come from the ephemeris
and the pinned Nino 3.4 snapshot; no outcome is read.
"""

import math
import sys
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence

import numpy as np
import pytest
from scipy.stats import beta

sys.path.insert(0, str(Path(__file__).resolve().parent))
import simulators as S  # noqa: E402

FAST_REPS = 400
FAST_PASS = 0.085  # ADR-008 A3.3 fast subset: observed bound at or below
FULL_PASS = 0.06
TAIL_PASS = 0.0065
FULL_REPS = 10_000
LAST_YEAR = S.YEARLY_GRID[1]

REAL_CALENDARS = S.YEARLY_RULE_CALENDARS + S.YEARLY_SIGN_CALENDARS
ALL_CALENDARS = REAL_CALENDARS + S.YEARLY_SYNTHETIC_CALENDARS
Y8_CALENDARS = ("mars_in_rohini", "ardra_weekday_malefic")


def _case(title, generators, *, calendars=ALL_CALENDARS, lengths=S.YEARLY_LENGTHS, reps=FULL_REPS,
          level=0.05, passmark=FULL_PASS, gate=True, kind="null", note=""):
    return {
        "title": title, "generators": tuple(generators), "calendars": tuple(calendars),
        "lengths": tuple(lengths), "reps": reps, "level": level, "pass": passmark,
        "gate": gate, "kind": kind, "note": note,
    }


#: The cases of the yearly proof that need only generators (A3.3; Y12 and YX1 to
#: YX6 need the year test and come with WP-101). "null" cases: the one-sided
#: rejection rate at "level" of each side must have an upper Clopper-Pearson
#: bound (95%, one-sided) at or below "pass". "design" and "naive" cases are
#: properties checked below and by WP-101. "reported" cases store their rates;
#: they are not gates.
YEARLY_CASES: Dict[str, dict] = {
    "Y1": _case("Independent Normal", ["Y1"]),
    "Y2": _case("Skew: mirrored lognormal, mirrored exponential, drought flag at 15%",
                ["Y2:lognormal", "Y2:exponential", "Y2:flag"]),
    "Y3": _case("AR(1) inside the envelope (-0.3, -0.15, +0.15, +0.3)",
                [f"Y3:{p:+.2f}" for p in (-0.3, -0.15, 0.15, 0.3)]),
    "Y4": _case("Biennial tendency: AR(2) peak 2.3 years rho1 -0.25; alternating +-3 with phase flips",
                ["Y4:ar2", "Y4:alternating"], note="strict alternation and Mars calendars in particular"),
    "Y5": _case("ENSO-driven dependence, variants a to e", [f"Y5:{v}" for v in "abcde"],
                note="variant e (real driver) exists for N of 69 or less only (Nino 3.4 starts 1948)"),
    "Y6": _case("Trend, 31-year wave, level step", [f"Y6:{v}" for v in ("trend", "wave", "step")]),
    "Y7": _case("Calendar tied to ENSO, baseline_r2 0.14 / 0.29 / 0.39", [f"Y7:{r:.2f}" for r in S.LOADED_R2],
                calendars=("loaded",), note="pass applies to every value that passes R4"),
    "Y8": _case("Tail at the level verdicts use (0.005, production B)",
                ["Y1", "Y3:-0.30", "Y3:+0.30", "Y4:ar2", "Y4:alternating", "Y5:a"],
                calendars=Y8_CALENDARS, lengths=(34, 69), reps=40_000, level=0.005, passmark=TAIL_PASS),
    "Y9": _case("Design properties (each year in one stratum once; design reads no outcome; test A unchanged by test B)",
                [], kind="design", reps=1),
    "Y10": _case("Naive designs fail (documented): gap-midpoint at most 2 usable blocks; free permutation above 0.07",
                 ["Y4:ar2", "Y4:alternating", "Y7:0.39"], calendars=("alternation",), kind="naive"),
    "Y11": _case("Outside the envelope: AR(1) at +-0.5, long memory d = 0.2 (reported, not a gate)",
                 ["Y11:ar1+0.5", "Y11:ar1-0.5", "Y11:long_memory"], gate=False, kind="reported"),
}


# ------------------------------------------------------------------ runner
def clopper_upper(k: int, n: int, conf: float = 0.95) -> float:
    """Upper one-sided Clopper-Pearson bound of a rate with k hits in n."""
    return 1.0 if k >= n else float(beta.ppf(conf, k + 1, n - k))


def case_years(n: int) -> np.ndarray:
    return np.arange(LAST_YEAR - n + 1, LAST_YEAR + 1)


def run_null_case(case_id: str, test: Callable, *, reps: Optional[int] = None, seed: int = 20261201,
                  generators: Optional[Sequence[str]] = None, calendars: Optional[Sequence[str]] = None,
                  lengths: Optional[Sequence[int]] = None, level: Optional[float] = None) -> List[dict]:
    """Run the one-sided rejection rates of a case for a test; one dict per cell and side.

    Cells: generator x calendar x N. test gets the outcome, the 0/1 calendar,
    the years, the driver the case lets it see (or None) and an rng. The seed
    of a cell depends on the seed, N, generator and calendar names only.
    """
    spec = YEARLY_CASES[case_id]
    reps = int(spec["reps"] if reps is None else reps)
    level = spec["level"] if level is None else level
    out = []
    for gname in generators or spec["generators"]:
        for cname in calendars or spec["calendars"]:
            for n in lengths or spec["lengths"]:
                if gname == "Y5:e" and n > 69:
                    continue
                yrs = case_years(n)
                rng = np.random.default_rng([seed, n, sum(map(ord, gname)), sum(map(ord, cname))])
                fixed = None if (cname == "loaded" or cname.startswith("bernoulli")) else S.yearly_case_calendar(cname, n)
                hits = {"greater": 0, "less": 0}
                for _ in range(reps):
                    gen = S.YEARLY_GENERATORS[gname](yrs, rng)
                    if cname == "loaded":
                        active = gen["active"]
                    else:
                        active = fixed if fixed is not None else S.yearly_case_calendar(cname, n, rng)
                    p = test(gen["y"], active, yrs, gen.get("driver"), rng)
                    for side in hits:
                        hits[side] += int(p[side] <= level + 1e-12)
                for side, k in hits.items():
                    out.append({"case": case_id, "generator": gname, "calendar": cname, "n": n, "side": side,
                                "hits": k, "reps": reps, "rate": k / reps, "bound": clopper_upper(k, reps)})
    return out


def failing_cells(cells: List[dict], passmark: float) -> List[dict]:
    return [c for c in cells if c["bound"] > passmark]


# ------------------------------------------------------------------- stubs
def stub_always_reject(y, active, years, driver, rng):
    return {"greater": 0.0, "less": 0.0}


def stub_uniform(y, active, years, driver, rng):
    return {"greater": float(rng.random()), "less": float(rng.random())}


def stub_naive_free_permutation(y, active, years, driver, rng):
    return {"greater": S.naive_free_permutation_p(y, active, rng, 199, "greater"),
            "less": S.naive_free_permutation_p(y, active, rng, 199, "less")}


# ------------------------------------------------------- helpers for moments
def _draw(name: str, n: int, seed: int = 7) -> dict:
    return S.YEARLY_GENERATORS[name](np.arange(n), np.random.default_rng(seed))


def _acf(x, lag=1):
    x = np.asarray(x, float) - np.mean(x)
    return float(np.dot(x[:-lag], x[lag:]) / np.dot(x, x))


def _skew(x):
    x = np.asarray(x, float)
    return float(np.mean((x - x.mean()) ** 3) / x.std() ** 3)


BIG = 200_000


# ----------------------------------------------------- generators: moments
def test_y1_normal_moments():
    y = _draw("Y1", BIG)["y"]
    assert abs(y.mean()) < 0.1 and abs(y.std() - 10) < 0.1 and abs(_skew(y)) < 0.03 and abs(_acf(y)) < 0.01


def test_y2_skew_signs_and_scale():
    ln = _draw("Y2:lognormal", BIG)["y"]
    ex = _draw("Y2:exponential", BIG)["y"]
    assert abs(ex.mean()) < 0.15 and abs(ex.std() - 10) < 0.15 and abs(_skew(ex) + 2.0) < 0.1  # long dry tail
    assert abs(ln.mean()) < 0.3 and ln.std() > 5 and _skew(ln) < -3  # heavy lower tail (skew -6.2, noisy)
    assert np.quantile(ln, 0.001) < -30  # the tail points down


def test_y2_drought_flag_rate_and_link():
    g = S.YEARLY_GENERATORS["Y2:flag"](np.arange(BIG), np.random.default_rng(3))
    assert g["y"].dtype == np.int8 and abs(g["y"].mean() - 0.15) < 0.004
    assert np.array_equal(g["y"], (g["latent"] < S.drought_threshold()).astype(np.int8))
    assert abs(S.drought_threshold() - (-10.364)) < 0.01


@pytest.mark.parametrize("phi", [-0.3, -0.15, 0.15, 0.3, 0.5, -0.5])
def test_y3_y11_ar1_moments(phi):
    y = S.yearly_ar1(np.arange(BIG), np.random.default_rng(5), phi)["y"]
    assert abs(_acf(y) - phi) < 0.01 and abs(y.std() - 10) < 0.15 and abs(_acf(y, 2) - phi**2) < 0.01


def test_y4_ar2_has_stated_peak_and_lag1():
    phi1, phi2 = S.ar2_coefficients(S.BIENNIAL_PERIOD, S.BIENNIAL_RHO1)
    assert phi1 / (1 - phi2) == pytest.approx(S.BIENNIAL_RHO1)
    f = np.linspace(0.01, 0.5, 20_000)
    spec = 1.0 / np.abs(1 - phi1 * np.exp(-2j * np.pi * f) - phi2 * np.exp(-4j * np.pi * f)) ** 2
    assert 1.0 / f[np.argmax(spec)] == pytest.approx(S.BIENNIAL_PERIOD, abs=0.02)
    y = _draw("Y4:ar2", BIG)["y"]
    assert abs(_acf(y) - S.BIENNIAL_RHO1) < 0.01 and abs(y.std() - 10) < 0.15


def test_y4_alternating_component_moments():
    comp = S.alternating_component(BIG, np.random.default_rng(2))
    assert set(np.unique(comp)) == {-3.0, 3.0}
    flips = np.mean(comp[1:] == comp[:-1])
    assert abs(flips - S.ALTERNATING_FLIP) < 0.005  # a repeated sign is a phase flip
    assert abs(_acf(comp) - (-(1 - 2 * S.ALTERNATING_FLIP))) < 0.01
    y = _draw("Y4:alternating", BIG)["y"]
    assert abs(y.std() - math.sqrt(100 + 9)) < 0.15 and abs(_acf(y) - (-0.7 * 9 / 109)) < 0.01


def test_y5_enso_variants():
    n = BIG
    a = S.yearly_enso(np.arange(n), np.random.default_rng(1), "a")
    assert np.array_equal(a["driver"], a["true_driver"])
    assert abs(np.corrcoef(a["y"], a["driver"])[0, 1] - 4 / math.sqrt(116)) < 0.01  # 4 points per driver sd
    assert abs(a["y"].std() - math.sqrt(116)) < 0.2 and abs(a["driver"].std() - 1) < 0.01
    assert abs(_acf(a["driver"]) - S.RAIN_ENSO_PHI) < 0.01
    b = S.yearly_enso(np.arange(n), np.random.default_rng(1), "b")
    assert abs(np.corrcoef(b["driver"], b["true_driver"])[0, 1] - 0.7) < 0.01
    assert abs(np.corrcoef(b["y"], b["true_driver"])[0, 1] - 4 / math.sqrt(116)) < 0.01
    c = S.yearly_enso(np.arange(n), np.random.default_rng(1), "c")
    z = c["driver"]
    assert abs(c["y"][z >= 0.5].mean() + 8) < 0.2 and abs(c["y"][z <= -0.5].mean() - 3) < 0.2
    assert abs(c["y"][np.abs(z) < 0.5].mean()) < 0.2
    d = S.yearly_enso(np.arange(n), np.random.default_rng(1), "d")
    zd = d["driver"]
    assert abs(zd.std() - 1) < 0.02
    per = np.abs(np.fft.rfft(zd[:2**16] - zd.mean())) ** 2
    fr = np.fft.rfftfreq(2**16)
    assert 1.0 / fr[1:][np.argmax(per[1:])] == pytest.approx(S.ENSO_QUASI_PERIOD, abs=0.5)
    assert _acf(zd, 2) < -0.2  # quasi-cycle: negative at half the period


def test_y5e_real_driver_is_the_pinned_series():
    yrs = case_years(69)
    e = S.yearly_enso(yrs, np.random.default_rng(1), "e")
    assert np.array_equal(e["driver"], S.real_enso_driver(yrs)) and np.isfinite(e["driver"]).all()
    assert abs(e["driver"].mean()) < 0.3 and 0.5 < e["driver"].std() < 1.5
    assert e["driver"][yrs == 1997][0] > 1.0 and e["driver"][yrs == 1988][0] < -1.0  # 1997 El Nino, 1988 La Nina (JJAS)
    with pytest.raises(ValueError, match="covers"):
        S.real_enso_driver(case_years(146))


def test_y6_trend_wave_step():
    n = 20_000
    rng = np.random.default_rng(4)
    t = np.arange(n)
    tr = S.yearly_trend_epoch(t, rng, "trend")["y"]
    slope = np.polyfit(t, tr, 1)[0] * (n - 1)
    assert abs(slope - 10.0) < 0.5  # one standard deviation (10 points) over the record
    w = S.yearly_trend_epoch(np.arange(62_000), np.random.default_rng(0), "wave")["y"]
    tt = np.arange(len(w))
    X = np.column_stack([np.sin(2 * np.pi * tt / 31), np.cos(2 * np.pi * tt / 31), np.ones(len(w))])
    c = np.linalg.lstsq(X, w, rcond=None)[0]
    assert abs(math.hypot(c[0], c[1]) - 5.0) < 0.2  # 0.5 standard deviation
    st = S.yearly_trend_epoch(np.arange(30_000), np.random.default_rng(6), "step")["y"]
    cut = int(round(S.STEP_AT * 30_000))
    assert abs(st[cut:].mean() - st[:cut].mean() - 5.0) < 0.3
    with pytest.raises(ValueError):
        S.yearly_trend_epoch(np.arange(10), rng, "nope")


def test_y11_long_memory_moments():
    y = S.yearly_long_memory(np.arange(100_000), np.random.default_rng(8))["y"]
    d = S.LONG_MEMORY_D
    assert abs(y.std() - 10) < 0.3
    assert abs(_acf(y) - d / (1 - d)) < 0.02  # ARFIMA(0, d, 0): rho1 = d / (1 - d)
    assert abs(_acf(y, 2) - d * (1 + d) / ((1 - d) * (2 - d))) < 0.02


# ------------------------------------------------------------ calendars
def test_real_rule_calendars_match_the_adr_duty():
    f = S.yearly_rule_calendars()
    assert list(f.columns) == list(S.YEARLY_RULE_CALENDARS) and f.index[0] == 1871 and f.index[-1] == 2016
    last69 = f.loc[1948:]
    assert len(last69) == 69
    assert abs(last69["mars_in_rohini"].mean() - 0.54) < 0.02  # A3.0: active in 54% of the 69 seasons
    for c in ("ardra_weekday_malefic", "varsheshvara_malefic"):
        assert 0.3 < f[c].mean() < 0.6  # three malefic lords of seven: about 3/7
    assert np.array_equal(S.yearly_case_calendar("mars_in_rohini", 34), f["mars_in_rohini"].to_numpy()[-34:])


def test_sign_calendars_are_real_and_nonempty():
    for name in S.YEARLY_SIGN_CALENDARS:
        for n in S.YEARLY_LENGTHS:
            a = S.yearly_case_calendar(name, n)
            assert len(a) == n and a.dtype == bool and 0 < a.sum() < n


def test_synthetic_calendars():
    for n in S.YEARLY_LENGTHS:
        alt = S.yearly_case_calendar("alternation", n)
        assert np.all(alt[1:] != alt[:-1])
        t = S.yearly_case_calendar("three_on_four_off", n)
        assert abs(t.mean() - 3 / 7) < 0.03 and S.episode_runs(t)[0] == (0, 3)
    b = np.concatenate([S.synthetic_calendar("bernoulli_0.4", 1000, np.random.default_rng(s)) for s in range(40)])
    assert abs(b.mean() - 0.4) < 0.01
    with pytest.raises(ValueError):
        S.synthetic_calendar("bernoulli_0.4", 10)


@pytest.mark.parametrize("r2", S.LOADED_R2)
@pytest.mark.parametrize("n", S.YEARLY_LENGTHS)
def test_y7_driver_loaded_calendar_hits_target_r2(r2, n):
    for s in range(20):
        g = S.yearly_driver_loaded(np.arange(n), np.random.default_rng(s), r2)
        assert abs(S.calendar_r2(g["active"], g["driver"]) - r2) <= 0.01
        assert abs(g["active"].mean() - 0.4) < 0.02


# ----------------------------------------------------- Y10 naive designs
@pytest.mark.parametrize("n", S.YEARLY_LENGTHS)
def test_y10a_gap_midpoint_has_at_most_two_usable_blocks_on_alternation(n):
    assert S.gap_midpoint_usable_blocks(S.synthetic_calendar("alternation", n)) <= 2


def test_gap_midpoint_usable_blocks_on_spaced_calendars():
    a = np.zeros(30, bool)
    a[[5, 15, 25]] = True
    assert S.gap_midpoint_usable_blocks(a) == 3  # wide gaps: every single year finds a control
    long_run = np.zeros(30, bool)
    long_run[5:25] = True
    assert S.gap_midpoint_usable_blocks(long_run) == 0  # one long stretch: no equal-size control


def _rate(test, gname, cname, n, reps, seed):
    cells = run_null_case("Y10", test, reps=reps, seed=seed, generators=[gname], calendars=[cname], lengths=[n], level=0.05)
    return max(c["rate"] for c in cells)


def test_y10b_free_permutation_fails_on_biennial_with_alternation():
    assert _rate(stub_naive_free_permutation, "Y4:ar2", "alternation", 34, 2000, 11) > 0.07
    assert _rate(stub_naive_free_permutation, "Y4:ar2", "alternation", 69, 2000, 12) > 0.07


def test_y10c_free_permutation_fails_on_enso_loaded_calendar():
    cells = run_null_case("Y7", stub_naive_free_permutation, reps=1500, seed=13, generators=["Y7:0.39"], calendars=["loaded"], lengths=[69])
    assert max(c["rate"] for c in cells) > 0.07


# ------------------------------------------------------- the case runner
def test_runner_uniform_stub_passes_and_always_reject_fails():
    ok = run_null_case("Y1", stub_uniform, reps=FAST_REPS, seed=1, calendars=["mars_in_rohini", "alternation"], lengths=[34])
    assert len(ok) == 2 * 2 and not failing_cells(ok, FAST_PASS)
    bad = run_null_case("Y1", stub_always_reject, reps=50, seed=1, calendars=["mars_in_rohini"], lengths=[34])
    assert len(failing_cells(bad, FAST_PASS)) == len(bad) == 2


def test_runner_skips_real_driver_beyond_1948():
    cells = run_null_case("Y5", stub_uniform, reps=3, seed=2, calendars=["alternation"])
    gens = {(c["generator"], c["n"]) for c in cells}
    assert ("Y5:e", 146) not in gens and ("Y5:e", 69) in gens and ("Y5:a", 146) in gens
    assert all(c["hits"] <= c["reps"] and 0 <= c["bound"] <= 1 for c in cells)


def test_runner_tail_case_has_a_stricter_bound():
    spec = YEARLY_CASES["Y8"]
    assert spec["level"] == 0.005 and spec["reps"] == 40_000 and spec["pass"] == TAIL_PASS
    assert clopper_upper(233, 40_000) <= TAIL_PASS < clopper_upper(250, 40_000)  # about 233 rejections or fewer
    assert clopper_upper(10, 10) == 1.0


def test_case_list_matches_the_adr():
    assert list(YEARLY_CASES) == [f"Y{i}" for i in range(1, 12)]
    for cid, spec in YEARLY_CASES.items():
        for g in spec["generators"]:
            assert g in S.YEARLY_GENERATORS, (cid, g)
        for c in spec["calendars"]:
            assert c == "loaded" or c in ALL_CALENDARS, (cid, c)
        assert set(spec["lengths"]) <= set(S.YEARLY_LENGTHS)
    assert YEARLY_CASES["Y1"]["reps"] == FULL_REPS and YEARLY_CASES["Y1"]["pass"] == FULL_PASS
    assert not YEARLY_CASES["Y11"]["gate"] and all(YEARLY_CASES[c]["gate"] for c in ("Y1", "Y2", "Y3", "Y4", "Y5", "Y6", "Y7", "Y8"))


def test_outcome_spy_raises_on_any_read():
    spy = S.OutcomeSpy(5)
    assert len(spy) == 5
    for peek in (lambda: spy[0], lambda: list(spy), lambda: np.asarray(spy), lambda: spy + 1, lambda: 2 * spy, lambda: float(spy)):
        with pytest.raises(AssertionError, match="read the outcome"):
            peek()
    assert spy.reads == 6


def test_generators_are_reproducible_and_return_one_value_per_year():
    yrs = case_years(34)
    for name, gen in S.YEARLY_GENERATORS.items():
        a, b = gen(yrs, np.random.default_rng(9)), gen(yrs, np.random.default_rng(9))
        assert len(a["y"]) == 34 and np.array_equal(a["y"], b["y"]), name
        assert np.isfinite(np.asarray(a["y"], float)).all(), name
