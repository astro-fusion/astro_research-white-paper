"""ADR-008 WP-100 and WP-101: generators, cases and the year test of the yearly-grid proof (A3.3).

Committed before the year test (core/stats/yearly.py, WP-101). Two jobs:

1. Prove each generator in tests/simulators.py against its stated moments, so
   a pass of the year test cannot come from a generator that is too kind.
2. Fix the case list (YEARLY_CASES) and the runner (run_null_case) that
   WP-101 and the certificate call. Any test with the signature
   test(y, active, years, driver, rng) -> {"greater": p, "less": p}
   (one-sided p-values for each side) can be run through a case. The cases
   fail against stubs: a test that always rejects, and the naive designs A3.3
   Y10 keeps on record. A trivially valid stub (uniform p) passes.

WP-101 adds the year test itself (core/stats/yearly.py): cases Y12 and YX1
to YX6, the runners the certificate uses for them (run_exclusion_case,
run_coverage_case, run_power_case, run_family_case), the Y9 design
properties, and the fast subset (400 replications of Y1, Y4 and YX1, pass at
or below 0.085). Full-size runs are made by the certificate, not here.

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

from vedic_astrology_core.stats import exclusion as EX  # noqa: E402
from vedic_astrology_core.stats import yearly as Y  # noqa: E402

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
                    gen, active = draw_cell(gname, cname, n, yrs, rng, fixed)
                    p = test(gen["y"], active, yrs, gen.get("driver"), rng)
                    for side in hits:
                        hits[side] += int(p[side] <= level + 1e-12)
                for side, k in hits.items():
                    out.append({"case": case_id, "generator": gname, "calendar": cname, "n": n, "side": side,
                                "hits": k, "reps": reps, "rate": k / reps, "bound": clopper_upper(k, reps)})
    return out


def draw_cell(gname: str, cname: str, n: int, yrs, rng, fixed=None):
    """One draw of a cell: the generator's dict and the 0/1 calendar.

    Y7 draws whose sample R2 cannot reach the target within its tolerance
    (rare at 34 years and R2 0.39) are redrawn from the same stream.
    """
    for _ in range(50):
        try:
            gen = S.YEARLY_GENERATORS[gname](yrs, rng)
            break
        except ValueError:
            if not gname.startswith("Y7:"):
                raise
    else:  # pragma: no cover
        raise ValueError(f"{gname}: no draw reached its target")
    if cname == "loaded":
        return gen, gen["active"]
    return gen, (fixed if fixed is not None else S.yearly_case_calendar(cname, n, rng))


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
    assert list(YEARLY_CASES) == [f"Y{i}" for i in range(1, 13)] + [f"YX{i}" for i in range(1, 7)]
    for cid, spec in YEARLY_CASES.items():
        for g in spec["generators"]:
            assert g in S.YEARLY_GENERATORS, (cid, g)
        for c in spec["calendars"]:
            assert c == "loaded" or c in ALL_CALENDARS, (cid, c)
        assert set(spec["lengths"]) <= set(S.YEARLY_LENGTHS)
    assert YEARLY_CASES["Y1"]["reps"] == FULL_REPS and YEARLY_CASES["Y1"]["pass"] == FULL_PASS
    assert YEARLY_CASES["Y12"]["reps"] == 1000 and YEARLY_CASES["YX6"]["reps"] == 2000
    assert not YEARLY_CASES["YX5"]["gate"] and YEARLY_CASES["YX1"]["pass"] == FULL_PASS
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


# ===================================================================
# WP-101: the year test (core/stats/yearly.py) and cases Y12, YX1 to YX6
# ===================================================================
#: Simulation SESOI (A3.3 YX1): 0.5 and 1 standard deviation of 10 points.
SIM_SESOI = (5.0, 10.0)
#: YX2: planted risk ratios (also the simulation SESOI on the ratio scale) and base rate.
SIM_RR = (1.5, 2.0)
SIM_BASE_RATE = S.YEARLY_DROUGHT_RATE
#: Grids of X in the simulations: each SESOI and a value on each side of it (A3.2 item 7).
SIM_GRID = (1.25, 2.5, 5.0, 7.5, 10.0, 15.0, 20.0, 30.0)
SIM_GRID_RR = (1.1, 1.2247, 1.4142, 1.5, 2.0, 2.25, 3.0, 4.0, 5.0)
#: Monsoon family threshold: 0.04 over the 7 monsoon tests (A3.0).
MONSOON_A_TEST = 0.04 / 7
#: The 7 monsoon tests (calendar, outcome) of the preview (studies/validity/preview/monsoon).
MONSOON_TESTS = (
    ("mars_in_rohini", "all_india"), ("mars_in_rohini", "peninsular"), ("mars_in_rohini", "peninsular_drought"),
    ("ardra_weekday_malefic", "all_india"), ("ardra_weekday_malefic", "all_india_drought"),
    ("varsheshvara_malefic", "all_india"), ("varsheshvara_malefic", "all_india_drought"),
)
SIM_STEPS = 12  # bisection steps in simulations (bracket / 4096)

YEARLY_CONTINUOUS = tuple(
    g for c in ("Y1", "Y2", "Y3", "Y4", "Y5", "Y6", "Y7") for g in YEARLY_CASES[c]["generators"] if g != "Y2:flag"
)

YEARLY_CASES.update({
    "Y12": _case("Power: constant effect of twice the gate's minimal detectable effect, a_test 0.04/7",
                 ["Y1"], reps=1000, level=MONSOON_A_TEST, passmark=0.80, kind="power",
                 note="S in at least 80% of runs (W1) on every cell the gate calls supportable; also reported: "
                      "rejection rate on the Bernoulli calendar with the envelope and at rho 0 only"),
    "YX1": _case("False exclusion: steady effect planted at the SESOI (0.5 and 1 sd), Y1 to Y7 generators",
                 YEARLY_CONTINUOUS, kind="exclusion"),
    "YX2": _case("Yes/no: drought flag at 15%, risk ratio 1.5 and 2.0 planted", ["Y2:flag"], kind="exclusion",
                 note="an excluded where A3.2 item 5 says unbounded counts as a failure"),
    "YX3": _case("Coverage: true effect 0, half, one and two times the SESOI; share with X95 below it",
                 YEARLY_CONTINUOUS + ("Y2:flag",), kind="coverage"),
    "YX4": _case("Monotone: p_ex never increases over the grid (property; violations listed)", [],
                 kind="property", reps=1),
    "YX5": _case("Uneven effect: whole effect in 20% of active runs (reported, no pass mark)",
                 ["Y1", "Y2:lognormal", "Y2:exponential"], gate=False, kind="reported"),
    "YX6": _case("Families of the 7 monsoon tests on their real calendars (34 confirm years)", [],
                 calendars=("mars_in_rohini", "ardra_weekday_malefic", "varsheshvara_malefic"), lengths=(34,),
                 reps=2000, kind="family", note="any S and any false E at the SESOI: bound at or below 0.06"),
})


# -------------------------------------------------------- the test as a case
def _inputs(y, driver):
    flags = np.asarray(y).dtype.kind in "iub"
    ot = "flags" if flags else "continuous"
    bl = None if (driver is None or flags) else np.asarray(driver, float)[:, None]
    return ot, {"enso": driver, "baselines": bl}


def year_case_test(n_perm: int = Y.B_CALIBRATION, level: float = 0.05):
    """The year test in the shape run_null_case wants; untestable designs return p = 1.

    The driver the case lets the test see is both the ENSO stratifier and the
    ENSO baseline. Counts of untestable designs are kept on the function.
    """
    def test(y, active, years, driver, rng):
        ot, kw = _inputs(y, driver)
        r = Y.year_test(y, active, years, outcome_type=ot, n_perm=n_perm, rng=rng, stop_level=level, **kw)
        test.calls += 1
        if not r.testable:
            test.untestable += 1
            return {"greater": 1.0, "less": 1.0}
        test.outside += int(r.outside_envelope)
        return {"greater": r.p["greater"], "less": r.p["less"]}

    test.calls = test.untestable = test.outside = 0
    return test


def _cells(spec, generators=None, calendars=None, lengths=None):
    for g in generators or spec["generators"]:
        cals = ("loaded",) if g.startswith("Y7:") else tuple(c for c in (calendars or spec["calendars"]) if c != "loaded")
        for c in cals:
            for n in lengths or spec["lengths"]:
                if g == "Y5:e" and n > 69:
                    continue
                yield g, c, n


def _cell_rng(seed, n, g, c, extra=0):
    return np.random.default_rng([seed, n, sum(map(ord, g)), sum(map(ord, c)), int(extra)])


def _fixed(c, n):
    return None if (c == "loaded" or c.startswith("bernoulli")) else S.yearly_case_calendar(c, n)


def x95_below(pfun, grid, a: float, theta: float, steps: int = SIM_STEPS) -> bool:
    """Is X95 (A3.2 item 3) below theta? Walks the grid down from the top, bisects only when needed."""
    g = [float(x) for x in grid]
    k = len(g) - 1
    while k >= 0 and pfun(g[k]) <= a:
        if g[k] < theta:
            return True  # X95 <= g[k] < theta
        k -= 1
    if k == len(g) - 1 or g[k] >= theta:
        return False  # unbounded, or X95 > g[k] >= theta
    lo, hi = g[k], g[k + 1]
    for _ in range(int(steps)):
        mid = 0.5 * (lo + hi)
        if pfun(mid) <= a:
            hi = mid
        else:
            lo = mid
    return hi < theta


def _uneven(active, rng, share: float = 0.2) -> np.ndarray:
    """Per-year effect of mean 1 over the active years, all of it in 20% of the active runs (YX5)."""
    a = np.asarray(active, bool)
    runs = S.episode_runs(a)
    k = max(1, int(round(share * len(runs))))
    pick = rng.choice(len(runs), size=k, replace=False)
    h = np.zeros(len(a))
    for i in pick:
        s, e = runs[i]
        h[s:e] = 1.0
    return h * a.sum() / h.sum()


def run_exclusion_case(case_id: str, *, reps: Optional[int] = None, seed: int = 20261202, generators=None,
                       calendars=None, lengths=None, magnitudes=None, n_perm: int = Y.B_CALIBRATION,
                       level: float = 0.05, uneven: bool = False) -> List[dict]:
    """False "excluded" at r = SESOI with a steady effect of the SESOI planted (YX1, YX2; YX5 with uneven).

    Both claim directions on each draw: "greater" with +SESOI (risk ratio on
    the active years), "less" with -SESOI (risk ratio on the inactive years).
    """
    spec = YEARLY_CASES[case_id]
    reps = int(spec["reps"] if reps is None else reps)
    out = []
    for g, c, n in _cells(spec, generators, calendars, lengths):
        flags = g == "Y2:flag"
        mags = magnitudes or (SIM_RR if flags else SIM_SESOI)
        yrs = case_years(n)
        fixed = _fixed(c, n)
        for m in mags:
            rng = _cell_rng(seed, n, g, c, m * 100)
            hits = {"greater": 0, "less": 0}
            bad = {"greater": 0, "less": 0}
            untestable = unbounded = 0
            for _ in range(reps):
                gen, active = draw_cell(g, c, n, yrs, rng, fixed)
                ot, kw = _inputs(gen["y"], gen.get("driver"))
                h = _uneven(active, rng) if uneven else np.asarray(active, float)
                for d, sign in (("greater", 1.0), ("less", -1.0)):
                    if flags:
                        arm = np.asarray(active, bool) if d == "greater" else ~np.asarray(active, bool)
                        yy = S.plant_risk_ratio(gen["y"], arm, m, rng, SIM_BASE_RATE)
                        r = Y.year_exclusion(yy, active, yrs, outcome_type="flags", side=d, sesoi=m, grid=SIM_GRID_RR,
                                             base_rate=SIM_BASE_RATE, n_perm=n_perm, rng=rng, thinning_rng=rng,
                                             limits=False, stop_level=level, **kw)
                    else:
                        yy = np.asarray(gen["y"], float) + sign * m * h
                        r = Y.year_exclusion(yy, active, yrs, outcome_type="continuous", side=d, sesoi=m, grid=SIM_GRID,
                                             n_perm=n_perm, rng=rng, limits=False, stop_level=level, **kw)
                    if d == "greater":
                        untestable += int(not r.design.testable)
                        unbounded += int(r.p_exclusion is None)
                    hits[d] += int(r.excluded(level))
                    bad[d] += int(r.p_exclusion is not None and r.p_exclusion <= level and not r.can_limit(level))
            for d in hits:
                k = hits[d] + bad[d]
                out.append({"case": case_id, "generator": g, "calendar": c, "n": n, "magnitude": m, "side": d,
                            "hits": k, "reps": reps, "rate": k / reps, "bound": clopper_upper(k, reps),
                            "untestable": untestable, "unbounded": unbounded})
    return out


def run_coverage_case(case_id: str = "YX3", *, reps: Optional[int] = None, seed: int = 20261203, generators=None,
                      calendars=None, lengths=None, n_perm: int = Y.B_CALIBRATION, level: float = 0.05) -> List[dict]:
    """YX3 (with YX1 and YX4 read off the same draws): X95 below the true effect, by true effect.

    Continuous: one set of permutations per draw serves every planted effect
    (YearRemoval.shifted, exact by linearity); true effects 0, 2.5, 5, 10 and
    20 points (0, half, one and two times the SESOI 5 and 10). Yes/no: risk
    ratios 1, sqrt(s), s, s^2 for s = 1.5 and 2.0, one removal per planted
    ratio. A true effect of 0 (ratio 1) cannot be undercut by a positive X95;
    it is counted, not computed. Also returns, per cell, the share of draws
    whose exclusion p was not monotone over the grid (YX4).
    """
    spec = YEARLY_CASES[case_id]
    reps = int(spec["reps"] if reps is None else reps)
    out = []
    for g, c, n in _cells(spec, generators, calendars, lengths):
        flags = g == "Y2:flag"
        yrs = case_years(n)
        fixed = _fixed(c, n)
        rng = _cell_rng(seed, n, g, c)
        thetas = sorted({1.0} | {s ** e for s in SIM_RR for e in (0.5, 1.0, 2.0)}) if flags else (0.0, 2.5, 5.0, 10.0, 20.0)
        fails = {(t, d): 0 for t in thetas for d in ("greater", "less")}
        yx1 = {(m, d): 0 for m in (SIM_RR if flags else SIM_SESOI) for d in ("greater", "less")}
        nonmono = computed = untestable = 0
        for _ in range(reps):
            gen, active = draw_cell(g, c, n, yrs, rng, fixed)
            ot, kw = _inputs(gen["y"], gen.get("driver"))
            act = np.asarray(active, bool)
            design = Y.year_design(act, yrs, enso=kw["enso"], merge_gap=0)
            if not design.testable:
                untestable += 1
                continue
            if flags:
                if Y.expected_yes(design, SIM_BASE_RATE) < EX.min_informative(level):
                    continue  # unbounded: no X95, no failure possible
                for t in thetas:
                    if t == 1.0:
                        continue
                    for d in ("greater", "less"):
                        arm = act if d == "greater" else ~act
                        yy = S.plant_risk_ratio(gen["y"], arm, t, rng, SIM_BASE_RATE)
                        er = Y.YearRemoval(yy, Y.year_design(act, yrs, enso=kw["enso"]), outcome_type="flags",
                                           side=d, n_perm=n_perm, rng=rng, thinning_rng=rng)
                        computed += 1
                        f = x95_below(lambda r: er.p_direction(r, d), SIM_GRID_RR, level, t)
                        fails[(t, d)] += int(f)
                        if t in SIM_RR:
                            yx1[(t, d)] += int(er.p_direction(t, d) <= level)
                continue
            er = Y.YearRemoval(gen["y"], design, outcome_type="continuous", side="two-sided", n_perm=n_perm,
                               rng=rng, **({"baselines": kw["baselines"]}))
            computed += 1
            ps0 = [er.p_direction(r, "greater") for r in SIM_GRID]
            nonmono += int(any(ps0[j + 1] > ps0[j] + 1e-15 for j in range(len(ps0) - 1)))
            for t in thetas:
                if t == 0.0:
                    continue
                for d, sign in (("greater", 1.0), ("less", -1.0)):
                    sh = er.shifted(sign * t)
                    fails[(t, d)] += int(x95_below(lambda r: sh.p_direction(r, d), SIM_GRID, level, t))
                    if t in SIM_SESOI:
                        yx1[(t, d)] += int(sh.p_direction(t, d) <= level)
        for (t, d), k in fails.items():
            out.append({"case": case_id, "generator": g, "calendar": c, "n": n, "true_effect": t, "side": d,
                        "hits": k, "reps": reps, "rate": k / reps, "bound": clopper_upper(k, reps),
                        "untestable": untestable, "computed": computed, "nonmonotone": nonmono})
        for (m, d), k in yx1.items():
            out.append({"case": "YX1@YX3", "generator": g, "calendar": c, "n": n, "magnitude": m, "side": d,
                        "hits": k, "reps": reps, "rate": k / reps, "bound": clopper_upper(k, reps)})
    return out


def run_power_case(*, reps: Optional[int] = None, seed: int = 20261204, calendars=None, lengths=None,
                   a_test: float = MONSOON_A_TEST) -> List[dict]:
    """Y12: S (one-sided greater, p <= a_test at production B) with twice the gate's minimal detectable effect.

    Cells the gate calls Untestable are listed with power None. On the
    Bernoulli calendar the rate at rho 0 alone is also given (the cost of the
    envelope), and both rates again at one minimal detectable effect, where
    the cost shows; those cells draw every permutation.
    """
    spec = YEARLY_CASES["Y12"]
    reps = int(spec["reps"] if reps is None else reps)
    B = Y.production_b(a_test)
    out = []
    for c in calendars or ALL_CALENDARS:
        for n in lengths or S.YEARLY_LENGTHS:
            yrs = case_years(n)
            fixed = _fixed(c, n)
            rng = _cell_rng(seed, n, "Y12", c)
            hits = hits0 = tested = one = one0 = 0
            effects = []
            for _ in range(reps):
                act = fixed if fixed is not None else S.yearly_case_calendar(c, n, rng)
                design = Y.year_design(act, yrs)
                if not design.testable:
                    continue
                eff = 2.0 * Y.minimal_detectable_effect(design, S.YEARLY_SD, a_test)
                effects.append(eff)
                y = S.yearly_normal(yrs, rng)["y"] + eff * np.asarray(act, float)
                bern = c.startswith("bernoulli")
                r = Y.year_test(y, act, yrs, side="greater", n_perm=B, rng=rng,
                                stop_level=None if bern else a_test, stop_sides=("greater",))
                tested += 1
                hits += int(r.p["greater"] <= a_test)
                if bern:
                    hits0 += int(r.p_by_rho["greater"][0.0] <= a_test)
                    # the cost of the envelope at one minimal detectable effect (reported)
                    y1 = S.yearly_normal(yrs, rng)["y"] + 0.5 * eff * np.asarray(act, float)
                    r1 = Y.year_test(y1, act, yrs, side="greater", n_perm=B, rng=rng)
                    one += int(r1.p["greater"] <= a_test)
                    one0 += int(r1.p_by_rho["greater"][0.0] <= a_test)
            out.append({"case": "Y12", "calendar": c, "n": n, "tested": tested, "reps": reps,
                        "power": hits / tested if tested else None,
                        "power_rho0": (hits0 / tested if tested else None) if c.startswith("bernoulli") else None,
                        "effect_mean": float(np.mean(effects)) if effects else None,
                        "power_1mde": (one / tested if tested else None) if c.startswith("bernoulli") else None,
                        "power_1mde_rho0": (one0 / tested if tested else None) if c.startswith("bernoulli") else None})
    return out


def _monsoon_outcomes(yrs, rng):
    """Two rainfall series sharing one ENSO driver (Z3 form) and their drought flags (anomaly below -10)."""
    ai = S.yearly_rainfall(yrs, rng)
    z = ai["enso"]
    wave = S.RAIN_EPOCH_AMPLITUDE * np.sin(2.0 * np.pi * yrs / S.RAIN_EPOCH_PERIOD + rng.uniform(0, 2 * np.pi))
    pi = S.RAIN_ENSO_WEIGHT * z + wave + rng.standard_normal(len(yrs)) * S.RAIN_NOISE_SD
    return {"all_india": ai["anomaly"], "peninsular": pi,
            "all_india_drought": (ai["anomaly"] < S.DROUGHT_THRESHOLD).astype(np.int8),
            "peninsular_drought": (pi < S.DROUGHT_THRESHOLD).astype(np.int8)}, z


def run_family_case(*, reps: Optional[int] = None, seed: int = 20261205, a_test: float = MONSOON_A_TEST,
                    sesoi: float = 5.0, sesoi_rr: float = 2.0, n: int = 34) -> dict:
    """YX6: null families of the 7 monsoon tests (two-sided, as A3.5 makes them today) on the real calendars.

    Any S: two-sided p <= a_test without the dependence flag, on outcomes with
    no effect. Any false E: with an effect of the SESOI planted in every test
    (-SESOI on the anomaly, risk ratio sesoi_rr on the drought flag), both
    directions excluded at a_test where the minimum-information rule allows.
    """
    reps = int(YEARLY_CASES["YX6"]["reps"] if reps is None else reps)
    yrs = case_years(n)
    cals = {c: S.yearly_case_calendar(c, n) for c, _ in MONSOON_TESTS}
    rng = np.random.default_rng([seed, n])
    B = Y.production_b(a_test)
    any_s = any_e = 0
    s_by_test = [0] * len(MONSOON_TESTS)
    for _ in range(reps):
        outs, z = _monsoon_outcomes(yrs, rng)
        fam_s = fam_e = False
        for i, (c, o) in enumerate(MONSOON_TESTS):
            act = cals[c]
            y = outs[o]
            ot, kw = _inputs(y, z)
            r = Y.year_test(y, act, yrs, outcome_type=ot, side="two-sided", n_perm=B, rng=rng,
                            stop_level=a_test, stop_sides=("two-sided",), **kw)
            if r.testable and r.p["two-sided"] <= a_test and not r.outside_envelope:
                fam_s = True
                s_by_test[i] += 1
            if ot == "flags":
                yy = S.plant_risk_ratio(y, act, sesoi_rr, rng, SIM_BASE_RATE)
                e = Y.year_exclusion(yy, act, yrs, outcome_type="flags", side="two-sided", sesoi=sesoi_rr,
                                     grid=SIM_GRID_RR, a_test=a_test, base_rate=SIM_BASE_RATE, n_perm=B, rng=rng,
                                     thinning_rng=rng, limits=False, stop_level=a_test, **kw)
            else:
                yy = np.asarray(y, float) - sesoi * np.asarray(act, float)
                e = Y.year_exclusion(yy, act, yrs, outcome_type="continuous", side="two-sided", sesoi=sesoi,
                                     grid=SIM_GRID, a_test=a_test, n_perm=B, rng=rng, limits=False,
                                     stop_level=a_test, **kw)
            fam_e = fam_e or e.excluded(a_test)
        any_s += int(fam_s)
        any_e += int(fam_e)
    return {"case": "YX6", "reps": reps, "n": n, "a_test": a_test, "B": B,
            "any_S": any_s, "any_S_rate": any_s / reps, "any_S_bound": clopper_upper(any_s, reps),
            "any_false_E": any_e, "any_false_E_rate": any_e / reps, "any_false_E_bound": clopper_upper(any_e, reps),
            "S_by_test": dict(zip(["/".join(t) for t in MONSOON_TESTS], s_by_test))}


# ------------------------------------------------------- unit: the design
def _years(n, start=1983):
    return np.arange(start, start + n)


def test_epochs_put_an_odd_middle_year_in_the_earlier_half():
    assert Y.epochs(5).tolist() == [0, 0, 0, 1, 1] and Y.epochs(4).tolist() == [0, 0, 1, 1]


def test_enso_phase_threshold_is_half_a_degree():
    ph = Y.enso_phase([-0.6, -0.5, -0.49, 0.0, 0.49, 0.5, np.nan])
    assert ph.tolist() == ["cold", "cold", "neutral", "neutral", "neutral", "warm", ""]


def test_jjas_anomaly_uses_the_base_period():
    import pandas as pd

    df = pd.DataFrame({m: [26.0, 27.0, 28.0] for m in Y.ENSO_MONTHS}, index=[1990, 1991, 1992])
    a = Y.jjas_anomaly(df, (1991, 1992))
    assert a.tolist() == pytest.approx([-1.5, -0.5, 0.5])
    with pytest.raises(ValueError, match="base period"):
        Y.jjas_anomaly(df, (1980, 1992))


def test_design_strata_collapse_and_drop():
    n = 40
    act = S.synthetic_calendar("alternation", n)
    enso = np.zeros(n)
    enso[[0, 1, 2, 3]] = 1.0  # warm: 2 active and 2 inactive, all in the first half -> loses the split
    enso[[30]] = -1.0  # cold: one year -> dropped
    d = Y.year_design(act, _years(n), enso=enso)
    labels = {s.label: s for s in d.strata}
    assert set(labels) == {"neutral:0", "neutral:1", "warm"}
    assert labels["warm"].epoch is None and labels["warm"].n_active == 2 and labels["warm"].n_inactive == 2
    assert [x["phase"] for x in d.dropped] == ["cold"] and d.dropped[0]["reason"] == Y.DROP_NO_STRATUM_CONTROL
    assert d.stratum[30] == -1 and d.group[30] >= 0  # dropped years stay in the recursion
    assert (np.bincount(d.stratum[d.stratum >= 0]) > 0).all()
    assert d.n_active + d.n_inactive == n - 1  # every year used at most once


def test_design_without_enso_uses_epochs_only():
    d = Y.year_design(S.synthetic_calendar("alternation", 34), _years(34))
    assert [s.label for s in d.strata] == ["all:0", "all:1"] and d.testable


def test_gate_reasons():
    few = np.zeros(34, bool)
    few[::5] = True  # 7 active years
    assert Y.year_design(few, _years(34)).reason == Y.REASON_TOO_FEW_YEARS
    long_run = np.zeros(34, bool)
    long_run[5:20] = True  # one long stretch: K_eff 1
    d = Y.year_design(long_run, _years(34))
    assert d.reason == Y.REASON_TOO_FEW_EPISODES and d.k_eff == pytest.approx(1.0)
    alt = S.synthetic_calendar("alternation", 34)
    assert Y.year_design(alt, _years(34)).k_eff == pytest.approx(17.0)
    assert Y.year_design(alt, _years(34), merge_gap=1).k_eff == pytest.approx(1.0)  # merged into one run


def test_weights_give_the_stratified_difference():
    rng = np.random.default_rng(0)
    n = 69
    act = S.yearly_case_calendar("mars_in_rohini", n)
    enso = rng.standard_normal(n)
    d = Y.year_design(act, _years(n, 1948), enso=enso)
    y = rng.standard_normal(n)
    num = sum(s.n_active * (y[(d.stratum == k) & act].mean() - y[(d.stratum == k) & ~act].mean())
              for k, s in enumerate(d.strata))
    assert Y.statistic(d, y) == pytest.approx(num / d.n_active)
    w = d.weights()
    for k in range(len(d.strata)):
        assert w[d.stratum == k].sum() == pytest.approx(0.0, abs=1e-12)
    assert Y.statistic(d, y + 5.0 * (d.stratum + 1)) == pytest.approx(Y.statistic(d, y))  # stratum shifts cancel


def test_production_b_and_smallest_p():
    assert Y.production_b(None) == 19_999 and Y.production_b(0.04 / 7) == 19_999
    assert Y.production_b(0.001) == 50_000 and Y.production_b(1e-5) == 200_000
    assert Y.smallest_p(19_999) == pytest.approx(5e-5)


def test_seed_follows_section_3_5():
    import hashlib

    want = int.from_bytes(hashlib.sha256(b"20261125|monsoon.x@1/primary/o|yearperm").digest()[:8], "big")
    assert Y.year_perm_seed(20261125, "monsoon.x@1/primary/o") == want


# -------------------------------------------------------- unit: the null
def _brute_stats(design, y_prep, baselines, rho, perms):
    """T* by brute force: centre, prewhiten, permute, rebuild, re-run the baseline step, statistic."""
    fin = design.finite
    idx = np.flatnonzero(fin)
    u = y_prep[idx].copy()
    g = design.group[idx]
    for gv in np.unique(g):
        u[g == gv] -= u[g == gv].mean()
    starts = np.ones(len(idx), bool)
    starts[1:] = np.diff(design.years[idx]) != 1
    e = u.copy()
    e[1:] -= rho * u[:-1]
    e[starts] = math.sqrt(1 - rho * rho) * u[starts]
    e -= e.mean()
    out = []
    for P in perms:
        es = e[np.argsort(P)]
        us = np.empty_like(es)
        for t in range(len(es)):
            us[t] = es[t] / math.sqrt(1 - rho * rho) if starts[t] else rho * us[t - 1] + es[t]
        full = np.zeros(len(design.years))
        full[idx] = us
        if baselines is not None:
            full = Y._residualise(full, np.asarray(baselines, float).reshape(len(full), -1), fin)
        out.append(Y.statistic(design, full))
    return np.array(out)


@pytest.mark.parametrize("with_baseline", [False, True])
def test_null_statistics_match_brute_force(with_baseline):
    rng = np.random.default_rng(3)
    n = 34
    yrs = _years(n)
    act = S.yearly_case_calendar("mars_in_rohini", n)
    z = rng.standard_normal(n)
    y = rng.standard_normal(n) * 10 + 4 * z
    y[7] = np.nan  # a break: two stretches
    fin = np.isfinite(y)
    d = Y.year_design(act, yrs, enso=z, finite=fin)
    bl = z[:, None] if with_baseline else None
    prep = Y.prepare_outcome(y, d, outcome_type="continuous", baselines=bl)
    null = Y.YearNull(d, prep, baselines=bl)
    st = null.draw(40, np.random.default_rng(11))
    base = np.broadcast_to(np.arange(null.nf), (Y.CHUNK, null.nf))
    perms = np.random.default_rng(11).permuted(base, axis=1)[:40]
    for k, rho in enumerate(Y.ENVELOPE):
        assert st[k, :, 0] == pytest.approx(_brute_stats(d, prep, bl, rho, perms), abs=1e-9)
    assert null.observed[0] == pytest.approx(Y.statistic(d, prep))


def test_leave_year_out_matches_season_module():
    from vedic_astrology_core.stats.season import leave_year_out_anomaly

    rng = np.random.default_rng(1)
    y = rng.standard_normal(30)
    assert Y.leave_year_out(y, np.ones(30, bool)) == pytest.approx(leave_year_out_anomaly(y, np.arange(30), by="year"))


def test_p_is_the_largest_over_the_envelope_and_early_stop_keeps_the_decision():
    rng = np.random.default_rng(5)
    n = 69
    yrs = case_years(n)
    act = S.yearly_case_calendar("mars_in_rohini", n)
    for i in range(30):
        y = rng.standard_normal(n) * 10 + (6.0 if i % 3 == 0 else 0.0) * act
        full = Y.year_test(y, act, yrs, n_perm=1999, seed=i)
        fast = Y.year_test(y, act, yrs, n_perm=1999, seed=i, stop_level=0.05)
        for s in ("greater", "less"):
            assert full.p[s] == max(full.p_by_rho[s].values())
            assert (full.p[s] <= 0.05) == (fast.p[s] <= 0.05)
            assert fast.p[s] <= full.p[s] + 1e-12
        assert full.p["two-sided"] == pytest.approx(max(min(1.0, 2 * min(full.p_by_rho["greater"][r], full.p_by_rho["less"][r])) for r in Y.ENVELOPE))
        assert full.complete and full.p["greater"] >= Y.smallest_p(1999)


def test_safety_flag_fires_outside_the_envelope():
    rng = np.random.default_rng(2)
    n = 146
    act = S.synthetic_calendar("alternation", n)
    y = S.yearly_ar1(case_years(n), rng, 0.85)["y"]
    r = Y.year_test(y, act, case_years(n), n_perm=199, seed=1)
    assert r.rho_hat > Y.safety_limit(n) and r.outside_envelope
    r2 = Y.year_test(rng.standard_normal(n), act, case_years(n), n_perm=199, seed=1)
    assert not r2.outside_envelope


def test_flags_outcome_and_risk_ratio():
    rng = np.random.default_rng(4)
    n = 69
    act = S.yearly_case_calendar("mars_in_rohini", n)
    f = (rng.random(n) < 0.3).astype(np.int8)
    r = Y.year_test(f, act, case_years(n), outcome_type="flags", n_perm=199, seed=3)
    assert r.testable and r.risk_ratio is not None and r.estimate == pytest.approx(Y.statistic(r.design, f.astype(float)))
    with pytest.raises(ValueError, match="0/1"):
        Y.year_test(f * 2.0, act, case_years(n), outcome_type="flags", n_perm=19, seed=3)


def test_untestable_record_has_no_p():
    act = np.zeros(34, bool)
    act[3:6] = True
    r = Y.year_test(np.random.default_rng(0).standard_normal(34), act, _years(34), n_perm=99, seed=1)
    assert not r.testable and r.p["two-sided"] is None and r.to_dict()["design"]["gate"] == Y.REASON_TOO_FEW_YEARS


# ------------------------------------------------------------ Y9 design
def test_y9_design_reads_no_outcome_and_ignores_shuffles():
    n = 69
    yrs = case_years(n)
    act = S.yearly_case_calendar("ardra_weekday_malefic", n)
    rng = np.random.default_rng(9)
    z = rng.standard_normal(n)
    import inspect

    assert "values" not in inspect.signature(Y.year_design).parameters  # the design has no outcome argument
    y = rng.standard_normal(n)
    a = Y.year_test(y, act, yrs, enso=z, n_perm=99, seed=1).design.to_dict()
    b = Y.year_test(rng.permutation(y), act, yrs, enso=z, n_perm=99, seed=1).design.to_dict()
    assert a == b
    d = Y.year_design(act, yrs, enso=z)
    for k in range(len(d.strata)):
        assert ((d.stratum == k) & d.finite).sum() == d.strata[k].n_active + d.strata[k].n_inactive
    assert len(np.flatnonzero(d.stratum >= 0)) == len(set(np.flatnonzero(d.stratum >= 0)))


def test_y9_test_a_unchanged_when_test_b_is_added():
    import json

    n = 34
    yrs = case_years(n)
    rng = np.random.default_rng(1)
    y = rng.standard_normal(n)
    sa = Y.year_perm_seed(20261125, "a")
    a1 = json.dumps(Y.year_test(y, S.yearly_case_calendar("mars_in_rohini", n), yrs, n_perm=999, seed=sa).to_dict(), sort_keys=True)
    Y.year_test(y, S.yearly_case_calendar("varsheshvara_malefic", n), yrs, n_perm=999, seed=Y.year_perm_seed(20261125, "b"))
    a2 = json.dumps(Y.year_test(y, S.yearly_case_calendar("mars_in_rohini", n), yrs, n_perm=999, seed=sa).to_dict(), sort_keys=True)
    assert a1 == a2


# ---------------------------------------------------- unit: exclusion
def test_removal_equals_the_test_on_the_adjusted_outcome():
    rng = np.random.default_rng(6)
    n = 69
    yrs = case_years(n)
    act = S.yearly_case_calendar("mars_in_rohini", n)
    z = rng.standard_normal(n)
    y = rng.standard_normal(n) * 10 + 4 * z
    d = Y.year_design(act, yrs, enso=z)
    er = Y.YearRemoval(y, d, outcome_type="continuous", side="two-sided", baselines=z[:, None], n_perm=499,
                       rng=np.random.default_rng(8))
    for r in (2.0, 5.0):
        direct = Y.year_test(y - r * act, act, yrs, enso=z, baselines=z[:, None], n_perm=499, rng=np.random.default_rng(8))
        assert er.p_direction(r, "greater") == pytest.approx(direct.p["less"])
        direct = Y.year_test(y + r * act, act, yrs, enso=z, baselines=z[:, None], n_perm=499, rng=np.random.default_rng(8))
        assert er.p_direction(r, "less") == pytest.approx(direct.p["greater"])
    sh = er.shifted(3.0)
    assert sh.p_direction(5.0, "greater") == pytest.approx(er.p_direction(2.0, "greater"))


def test_yearly_exclusion_limits_two_sided_and_no_sesoi():
    rng = np.random.default_rng(7)
    n = 146
    yrs = case_years(n)
    act = S.yearly_case_calendar("mars_in_rohini", n)
    y = rng.standard_normal(n) * 10
    kw = dict(outcome_type="continuous", grid=SIM_GRID, a_test=0.01, n_perm=999, seed=4)
    g = Y.year_exclusion(y, act, yrs, side="greater", sesoi=10.0, **kw)
    l = Y.year_exclusion(y, act, yrs, side="less", sesoi=10.0, **kw)
    t = Y.year_exclusion(y, act, yrs, side="two-sided", sesoi=10.0, **kw)
    assert not g.x95.unbounded and not l.x95.unbounded and not t.x95.unbounded
    assert t.x95.value == pytest.approx(max(g.x95.value, l.x95.value))
    assert t.p_exclusion == pytest.approx(max(g.p_exclusion, l.p_exclusion))
    assert t.x_strict.value >= t.x95.value
    none = Y.year_exclusion(y, act, yrs, side="two-sided", sesoi=None, **kw)  # A3.4 item 5: limits without a SESOI
    assert none.p_exclusion is None and none.x95.value == pytest.approx(t.x95.value) and not none.excluded(0.05)
    via = EX.yearly_exclusion(y, act, yrs, side="two-sided", sesoi=10.0, **kw)
    assert via.to_dict() == t.to_dict() and EX.method_for_grain("yearly") == EX.METHOD_YEARLY
    assert EX.method_for_grain("daily") == EX.METHOD_BLOCKS
    assert t.card_lines()[1].startswith("Not addressed") and t.k_runs == t.design.n_runs


def test_yes_no_exclusion_minimum_information():
    rng = np.random.default_rng(8)
    act34 = S.yearly_case_calendar("mars_in_rohini", 34)
    f = (rng.random(34) < 0.15).astype(np.int8)
    r = Y.year_exclusion(f, act34, case_years(34), outcome_type="flags", side="greater", sesoi=2.0, grid=SIM_GRID_RR,
                         a_test=0.0057, base_rate=0.15, n_perm=199, seed=1, thinning_rng=np.random.default_rng(1))
    assert r.x95.unbounded and r.x95.reason == Y.REASON_TOO_FEW_YES and r.p_exclusion is None and not r.excluded(0.05)
    r = Y.year_exclusion(f, act34, case_years(34), outcome_type="flags", side="greater", sesoi=2.0, grid=SIM_GRID_RR,
                         n_perm=199, seed=1, thinning_rng=np.random.default_rng(1))
    assert r.x95.reason == Y.REASON_NO_BASE_RATE
    act = S.yearly_case_calendar("mars_in_rohini", 146)
    f = (rng.random(146) < 0.15).astype(np.int8)
    r = Y.year_exclusion(f, act, case_years(146), outcome_type="flags", side="two-sided", sesoi=2.0, grid=SIM_GRID_RR,
                         a_test=0.0057, base_rate=0.15, n_perm=199, seed=1, thinning_rng=np.random.default_rng(1))
    assert r.expected_yes >= 8 and r.n_thin == Y.N_THIN and r.p_exclusion is not None
    assert r.to_dict()["aggregation"] == "twice_median"


def test_yx4_exclusion_p_monotone_on_draws():
    """YX4 as a property: list any draw where p_ex rises with r (the item 3 definition still protects X95)."""
    rng = np.random.default_rng(10)
    violations = []
    for i in range(40):
        n = (34, 69, 146)[i % 3]
        act = S.yearly_case_calendar(("mars_in_rohini", "alternation", "ardra_weekday_malefic")[i % 3], n)
        y = rng.standard_normal(n) * 10
        r = Y.year_exclusion(y, act, case_years(n), outcome_type="continuous", side="two-sided", sesoi=5.0,
                             grid=SIM_GRID, n_perm=499, seed=i)
        if not r.monotone:
            violations.append(i)
    assert violations == []


def test_x95_below_agrees_with_the_search():
    rng = np.random.default_rng(12)
    act = S.yearly_case_calendar("mars_in_rohini", 69)
    y = rng.standard_normal(69) * 10
    d = Y.year_design(act, case_years(69))
    er = Y.YearRemoval(y, d, outcome_type="continuous", side="greater", n_perm=999, rng=np.random.default_rng(1))
    v, *_ = Y._limit_search(lambda r: er.p_direction(r, "greater"), np.array(SIM_GRID), 0.05, SIM_STEPS)
    for t in (1.0, 2.5, 5.0, 7.0, 10.0, 20.0, 40.0):
        assert x95_below(lambda r: er.p_direction(r, "greater"), SIM_GRID, 0.05, t) == (v is not None and v < t)


# ------------------------------------------------ fast subset (every PR)
def test_fast_subset_y1_y4():
    """A3.3 fast subset: 400 replications, cases Y1 and Y4, pass at or below 0.085."""
    test = year_case_test()
    cells = run_null_case("Y1", test, reps=FAST_REPS, seed=31, lengths=(34, 69))
    cells += run_null_case("Y4", test, reps=FAST_REPS, seed=32, calendars=("alternation", "mars_in_rohini"))
    assert not failing_cells(cells, FAST_PASS), failing_cells(cells, FAST_PASS)


def test_fast_subset_yx1():
    """A3.3 fast subset: YX1, 400 replications, pass at or below 0.085."""
    cells = run_exclusion_case("YX1", reps=FAST_REPS, seed=33, generators=("Y1", "Y4:ar2", "Y5:a"),
                               calendars=("mars_in_rohini", "alternation"), lengths=(34, 69), magnitudes=(5.0,))
    assert len(cells) == 3 * 2 * 2 * 2
    assert not failing_cells(cells, FAST_PASS), failing_cells(cells, FAST_PASS)


def test_harness_catches_a_broken_year_test():
    """The fast subset fails against a test that forgets the envelope and the strata (free permutation)."""
    cells = run_null_case("Y4", stub_naive_free_permutation, reps=FAST_REPS, seed=34, generators=["Y4:ar2"],
                          calendars=["alternation"], lengths=[69])
    assert failing_cells(cells, FAST_PASS)
