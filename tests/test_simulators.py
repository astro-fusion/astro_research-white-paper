"""Each generator has the property ADR-008 states for it, and the certificate holds.

ADR-008 WP-84 (sections 1.3, 2.4, 4.4, 6.3 and 8). The generators in
``tests/simulators.py`` certify the block, exclusion and season methods, so
each one is checked here against its own stated property: skewness above 1
for the skewed bars, index of dispersion above 2 for clustered events before
declustering, lag-1 autocorrelation 0.15 to 0.35 for monthly averages, the
season amplitude, the mean events per window. Effects are planted in bars,
never in block differences. The certificate round-trips and fails on a
changed blob hash.
"""

import json
import shutil
import subprocess

import numpy as np
import pandas as pd
import pytest
from scipy.stats import kurtosis, skew

from tests import simulators as S
from vedic_astrology_core.validity import calibration as C

SEED = 20261122


def rng(*parts):
    return np.random.default_rng(C.derive_seed(SEED, *parts))


# ------------------------------------------------------------- calendars
@pytest.mark.parametrize("n_active,n_gap", S.PERIODIC_SHAPES)
@pytest.mark.parametrize("k", S.PERIODIC_EPISODES)
def test_periodic_calendar_shape(n_active, n_gap, k):
    cal = S.periodic_calendar(n_active, n_gap, k)
    runs = S.episode_runs(cal)
    assert len(runs) == k
    assert all(e - s == n_active for s, e in runs)
    gaps = [runs[i + 1][0] - runs[i][1] for i in range(k - 1)]
    assert gaps == [n_gap] * (k - 1)
    assert runs[0][0] == n_gap // 2 and len(cal) - runs[-1][1] == n_gap // 2


@pytest.mark.parametrize("balance", S.BALANCES)
@pytest.mark.parametrize("k", S.BLOCK_COUNTS)
def test_balance_calendar_gives_the_stated_balance(balance, k):
    n_active = 8
    cal = S.balance_calendar(balance, k, n_active)
    runs = S.episode_runs(cal)
    assert len(runs) == k
    # half-gap per side, odd middle dropped, cap ceil(n_active / 2) per side
    gap = runs[1][0] - runs[0][1]
    per_side = min(gap // 2, -(-n_active // 2))
    assert 2 * per_side / n_active == balance
    assert runs[0][0] == gap // 2 and len(cal) - runs[-1][1] == gap // 2


def test_balance_calendar_refuses_impossible_balance():
    with pytest.raises(ValueError):
        S.balance_calendar(0.3, 8, 8)
    with pytest.raises(ValueError):
        S.balance_calendar(1.5, 8, 8)


# ---------------------------------------------------------- bar outcomes
@pytest.mark.parametrize("kind", S.SKEWED_KINDS)
def test_skewed_bars_have_skewness_above_one(kind):
    x = S.continuous_bars(kind, 50_000, rng("skew", kind))
    assert skew(x) > 1.0


def test_zero_inflated_bars_are_mostly_zero():
    x = S.continuous_bars("zero_inflated", 100_000, rng("zi"))
    assert abs(np.mean(x == 0) - S.ZERO_INFLATED_P0) < 0.003


def test_t3_bars_are_heavy_tailed_and_normal_is_not():
    t3 = S.continuous_bars("t3", 50_000, rng("t3"))
    nrm = S.continuous_bars("normal", 50_000, rng("normal"))
    assert kurtosis(t3) > 3.0
    assert abs(kurtosis(nrm)) < 0.2
    assert abs(skew(nrm)) < 0.1


def test_unknown_bar_kind_raises():
    with pytest.raises(ValueError):
        S.continuous_bars("cauchy", 10, rng("x"))


def test_garch_normal_has_volatility_clustering():
    e = S.garch11_normal(20_000, rng("garch"), **S.B3_GARCH)
    assert abs(np.var(e) - 1.0) < 0.15
    assert abs(S.lag1_autocorrelation(e)) < 0.05
    assert S.lag1_autocorrelation(e**2) > 0.05


@pytest.mark.parametrize("phi", S.AR1_PHIS)
def test_ar1_has_its_coefficient(phi):
    x = S.ar1(40_000, rng("ar1", phi), phi)
    assert abs(S.lag1_autocorrelation(x) - phi) < 0.02
    assert abs(np.std(x) - 1.0) < 0.03


def test_regime_bars_switch_volatility():
    x = S.regime_bars(50_000, rng("regime"))
    assert S.lag1_autocorrelation(x**2) > 0.05


# ---------------------------------------------------------------- events
@pytest.mark.parametrize("mean", S.RARE_EVENT_MEANS)
def test_poisson_events_mean_per_window(mean):
    window, k = 10, 4000
    cal = S.periodic_calendar(window, window, k)
    counts = S.poisson_events(cal, mean, window, rng("poisson", mean))
    per_window = np.array([counts[s:e].sum() for s, e in S.episode_runs(cal)])
    se = np.sqrt(mean / k)
    assert abs(per_window.mean() - mean) < 4 * se


def test_poisson_rate_ratio_is_planted_in_active_bars():
    window, k, r = 10, 4000, 2.0
    cal = S.periodic_calendar(window, window, k)
    counts = S.poisson_events(cal, 1.0, window, rng("poisson-rr"), S.effect_multiplier(cal, r))
    ratio = counts[cal].sum() / counts[~cal][: cal.sum()].sum()
    assert abs(ratio - r) < 0.1


def test_neyman_scott_is_overdispersed_before_declustering():
    out = S.neyman_scott(200_000, rng("ns"), parent_rate=0.01)
    assert S.index_of_dispersion(out["counts"], 30) > 2.0
    # the parents alone (an ideal declustering) are close to Poisson
    assert S.index_of_dispersion(out["parents"], 30) < 1.3


def test_neyman_scott_offspring_mean_and_trend():
    n = 400_000
    out = S.neyman_scott(n, rng("ns2"), parent_rate=0.01)
    n_par = out["parents"].sum()
    n_off = len(out["event_bar"]) - n_par
    assert abs(n_off / n_par - S.NS_OFFSPRING_MEAN) < 0.15  # few lost at the end
    q = n // 10
    early, late = out["parents"][:q].sum(), out["parents"][-q:].sum()
    # linear rise from 1 to 2: deciles average 1.05 and 1.95
    assert abs(late / early - 1.95 / 1.05) < 0.15


def test_neyman_scott_event_table_is_consistent():
    out = S.neyman_scott(20_000, rng("ns3"), parent_rate=0.02)
    assert np.array_equal(np.bincount(out["event_bar"], minlength=20_000), out["counts"])
    assert np.array_equal(
        np.bincount(out["event_bar"][out["event_parent"]], minlength=20_000), out["parents"]
    )
    assert np.all(np.diff(out["event_bar"]) >= 0)
    # each offspring is at or after its parent
    parent_bar = dict(zip(out["event_cluster"][out["event_parent"]], out["event_bar"][out["event_parent"]]))
    kids = ~out["event_parent"]
    assert all(b >= parent_bar[c] for b, c in zip(out["event_bar"][kids], out["event_cluster"][kids]))


def test_neyman_scott_rate_ratio_on_parents():
    cal = S.periodic_calendar(50, 50, 2000)
    out = S.neyman_scott(len(cal), rng("ns-rr"), 0.1, S.effect_multiplier(cal, 2.0), trend=1.0)
    ratio = out["parents"][cal].sum() / out["parents"][~cal].sum()
    assert abs(ratio * (~cal).sum() / cal.sum() - 2.0) < 0.15  # about 4 standard errors


# ----------------------------------------------------------------- flags
def test_garch_flags_base_rate_and_clustering():
    f = S.garch_flags(40_000, rng("gflags"))
    assert abs(f.mean() - S.GARCH_FLAG_RATE) < 0.001
    assert S.index_of_dispersion(f, 50) > 1.2
    assert S.lag1_autocorrelation(f) > 0.02


def test_plant_risk_ratio_up_and_down():
    p, n = 0.05, 400_000
    cal = S.periodic_calendar(10, 10, n // 20)
    flags = (rng("flags-base").random(len(cal)) < p).astype(np.int8)
    up = S.plant_risk_ratio(flags, cal, 2.0, rng("rr-up"), p)
    down = S.plant_risk_ratio(flags, cal, 0.5, rng("rr-down"), p)
    assert np.array_equal(up[~cal], flags[~cal]) and np.array_equal(down[~cal], flags[~cal])
    assert abs(up[cal].mean() / flags[~cal].mean() - 2.0) < 0.08
    assert abs(down[cal].mean() / flags[~cal].mean() - 0.5) < 0.04


# --------------------------------------------------------- planting in bars
def test_plant_shift_changes_only_active_bars_by_r():
    cal = S.periodic_calendar(5, 7, 10)
    y = S.continuous_bars("lognormal", len(cal), rng("plant"))
    out = S.plant_shift(y, cal, 0.3)
    assert np.allclose(out[cal] - y[cal], 0.3)
    assert np.array_equal(out[~cal], y[~cal])
    assert np.array_equal(y, S.continuous_bars("lognormal", len(cal), rng("plant")))  # input untouched


def test_plant_ratio_is_a_log_shift():
    cal = S.periodic_calendar(5, 7, 10)
    y = S.continuous_bars("exponential", len(cal), rng("ratio")) + 0.1
    out = S.plant_ratio(y, cal, 1.5)
    assert np.allclose(np.log(out[cal]) - np.log(y[cal]), np.log(1.5))
    assert np.array_equal(out[~cal], y[~cal])
    with pytest.raises(ValueError):
        S.plant_ratio(y, cal, 0.0)


def test_effects_are_planted_in_bars_not_block_differences():
    """A vector of one value per block (or any length other than the bars) is refused."""
    cal = S.periodic_calendar(5, 5, 12)
    per_block = np.zeros(12)
    for fn in (S.plant_shift, S.plant_ratio):
        with pytest.raises(ValueError, match="planted in bars"):
            fn(per_block + 1.0, cal, 1.5)
    with pytest.raises(ValueError, match="planted in bars"):
        S.plant_risk_ratio(per_block.astype(int), cal, 2.0, rng("x"), 0.05)
    with pytest.raises(ValueError, match="planted in bars"):
        S.poisson_events(cal, 0.5, 5, rng("x"), multiplier=np.ones(12))


@pytest.mark.parametrize("scale", ["ratio", "shift"])
def test_uneven_effect_sits_in_a_fifth_of_episodes_with_mean_r(scale):
    cal = S.periodic_calendar(6, 6, 20)
    r = 2.0
    m = S.uneven_multiplier(cal, r, rng("uneven", scale), share=0.2, scale=scale)
    neutral = 1.0 if scale == "ratio" else 0.0
    assert np.all(m[~cal] == neutral)
    assert abs(m[cal].mean() - r) < 1e-12
    hit = [s for s, e in S.episode_runs(cal) if m[s] != neutral]
    assert len(hit) == 4


# ---------------------------------------------------------------- season
def test_seasonal_daily_amplitude_and_pulse():
    dates = pd.date_range(*S.DAILY_GRID, freq="D")
    y = S.seasonal_daily(dates, rng("season"))
    pulse = np.isin(dates.month, S.SEASON_PULSE_MONTHS)
    detrended = y - S.SEASON_PULSE * pulse
    assert abs(S.harmonic_amplitude(dates, detrended) - S.SEASON_AMPLITUDE) < 0.05
    sine = S.SEASON_AMPLITUDE * np.sin(2 * np.pi * dates.day_of_year.to_numpy() / 365.25)
    assert abs(np.mean((y - sine)[pulse]) - np.mean((y - sine)[~pulse]) - S.SEASON_PULSE) < 0.06


def test_seasonal_events_rate_factor():
    dates = pd.date_range(*S.DAILY_GRID, freq="D")
    mult = S.season_multiplier(dates)
    out = S.neyman_scott(len(dates), rng("season-ev"), 0.02, mult, trend=1.0)
    pulse = mult > 1
    ratio = out["parents"][pulse].mean() / out["parents"][~pulse].mean()
    assert abs(ratio - S.SEASON_EVENT_FACTOR) < 0.8
    assert S.index_of_dispersion(out["counts"], 30) > 2.0


def test_yearly_rainfall_components():
    years = np.arange(1871, 1871 + 20_000)
    out = S.yearly_rainfall(years, rng("rain"))
    a = out["anomaly"]
    assert abs(np.std(a) - S.rainfall_sd()) < 0.2
    assert abs(np.corrcoef(a, out["enso"])[0, 1] - S.RAIN_ENSO_WEIGHT / S.rainfall_sd()) < 0.03
    assert abs(S.lag1_autocorrelation(out["enso"]) - S.RAIN_ENSO_PHI) < 0.03
    assert np.array_equal(out["drought"], (a < S.DROUGHT_THRESHOLD).astype(np.int8))


def test_drought_flags_base_rate():
    years = np.arange(1871, 1871 + 40_000)
    a = S.yearly_rainfall(years, rng("drought"))["anomaly"]
    # the epoch wave makes the marginal slightly non-normal; the rate is close
    assert abs(S.drought_flags(a).mean() - S.DROUGHT_FLAG_RATE) < 0.01


def test_rainfall_spike_year():
    years = np.arange(1901, 1950)
    base = S.yearly_rainfall(years, rng("spike"))["anomaly"]
    spiked = S.yearly_rainfall(years, rng("spike"), spike_year=1920, spike=-30.0)["anomaly"]
    diff = spiked - base
    assert diff[years == 1920][0] == -30.0 and np.all(diff[years != 1920] == 0)


def test_nodal_wave_follows_the_node():
    lon = np.linspace(0, 360 * 50, 20_000) % 360
    y = S.nodal_wave(lon, rng("nodal"))
    assert np.corrcoef(y, np.cos(np.radians(lon)))[0, 1] > 0.5


# ----------------------------------------------------------- data rules
def test_monthly_average_returns_lag1_artefact():
    r1 = [S.lag1_autocorrelation(S.monthly_average_returns(30, rng("monthly", i))) for i in range(40)]
    assert 0.15 <= np.mean(r1) <= 0.35
    one = S.monthly_average_returns(30, rng("monthly", "single"))
    assert 350 <= len(one) <= 360
    assert 0.15 <= S.lag1_autocorrelation(one) <= 0.35


def test_holiday_mismatch_series_differ():
    dates = pd.bdate_range("2000-01-03", periods=500)
    a, b = S.holiday_mismatch(dates, rng("hol"), 12, 9)
    assert len(a) == 488 and len(b) == 491
    assert set(dates) - set(a.index) != set(dates) - set(b.index)
    assert a.index[0] == dates[0] and a.index[-1] == dates[-1]


# --------------------------------------------------------- real calendars
@pytest.fixture(scope="module")
def daily():
    return S.daily_calendars()


def test_daily_calendars_cover_the_grid(daily):
    assert daily.index[0] == pd.Timestamp(S.DAILY_GRID[0])
    assert daily.index[-1] == pd.Timestamp(S.DAILY_GRID[1])
    assert len(daily) == 11_323
    assert all(daily[c].dtype == bool for c in daily)


@pytest.mark.parametrize(
    "col,share,episodes",
    [
        ("mercury_retrograde", (0.17, 0.22), (90, 105)),  # about 3 a year, 3 weeks each
        ("venus_combust", (0.10, 0.20), (35, 45)),
        ("moon_nakshatra_group", (4 / 27 - 0.01, 4 / 27 + 0.01), (1500, 1750)),
        ("tithi_group", (0.19, 0.21), (2000, 2400)),
        ("sun_nakshatra", (0.035, 0.040), (31, 31)),
        ("sun_sign", (0.080, 0.088), (31, 31)),
        ("eclipse_window", (0.08, 0.09), (130, 150)),
    ],
)
def test_daily_calendar_shares_and_episodes(daily, col, share, episodes):
    assert share[0] <= daily[col].mean() <= share[1]
    assert episodes[0] <= S.n_episodes(daily[col]) <= episodes[1]


def test_eclipse_windows_are_seven_days(daily):
    runs = S.episode_runs(daily["eclipse_window"].to_numpy())
    lengths = {e - s for s, e in runs[1:-1]}
    assert lengths <= {7, 14}  # 14 only if two eclipses fall within a week, which is rare
    assert 7 in lengths


def test_yearly_calendars_node_cycle():
    y = S.yearly_calendars()
    assert y.index[0] == S.YEARLY_GRID[0] and y.index[-1] == S.YEARLY_GRID[1]
    in_sign = y[[f"rahu_in_{s.lower()}" for s in S.SIGNS]].sum(axis=1)
    assert np.all(in_sign == 1)
    for s in S.SIGNS:
        assert 5 <= S.n_episodes(y[f"rahu_in_{s.lower()}"]) <= 9  # 146 years / 18.6
    # the node moves backwards: longitude falls by about 19.3 degrees a year
    step = (np.diff(y["rahu_longitude"]) + 180) % 360 - 180
    assert np.all(np.abs(step + 360 / S.NODAL_PERIOD_YEARS) < 2.0)


# ------------------------------------------------------------ determinism
def test_same_seed_same_series():
    a = S.neyman_scott(5000, np.random.default_rng(7), 0.05)
    b = S.neyman_scott(5000, np.random.default_rng(7), 0.05)
    assert all(np.array_equal(a[k], b[k]) for k in a)
    assert np.array_equal(S.garch_flags(3000, np.random.default_rng(3)), S.garch_flags(3000, np.random.default_rng(3)))


def test_derive_seed_is_stable_and_separates_parts():
    assert C.derive_seed(1, "B1", "x") == C.derive_seed(1, "B1", "x")
    assert C.derive_seed(1, "B1", "x") != C.derive_seed(1, "B1", "y")
    assert C.derive_seed("a|b") == C.derive_seed("a", "b")  # documented: parts joined with "|"
    assert 0 <= C.derive_seed(SEED) < 2**64
    assert C.case_seed(SEED, "X3", "K=8") != C.case_seed(SEED, "X3", "K=12")


# =============================================================== calibration
def test_clopper_pearson_known_values():
    assert C.clopper_pearson_upper(0, 10) == pytest.approx(1 - 0.05 ** (1 / 10))
    assert C.clopper_pearson_upper(10, 10) == 1.0
    assert C.clopper_pearson_upper(500, 10_000) < 0.06
    with pytest.raises(ValueError):
        C.clopper_pearson_upper(11, 10)


def test_max_passing_count_matches_the_adr():
    k = C.max_passing_count(10_000, 0.06)
    assert 555 <= k <= 565  # ADR-008 1.3: "about 562 rejections or fewer"
    assert C.clopper_pearson_upper(k, 10_000) <= 0.06 < C.clopper_pearson_upper(k + 1, 10_000)
    assert C.max_passing_count(10, 0.06) == -1


def test_registry_holds_every_adr_case():
    ids = set(C.CASES)
    expected = (
        {f"B{i}" for i in range(1, 7)}
        | {f"X{i}" for i in range(1, 11)}
        | {f"F{i}" for i in range(1, 8)} | {"F8S", "F8C"}
        | {f"Z{i}" for i in range(1, 7)}
        | {"W1", "W2", "W4", "R2N", "R2P", "K1", "K2", "D1"}
    )
    assert expected <= ids
    assert C.get_case("B1").replications == 10_000 and C.get_case("F3").replications == 2_000
    assert C.get_case("W1").replications == 1_000
    assert C.get_case("X9").rule == C.RECORD
    with pytest.raises(ValueError):
        C.register(C.CaseSpec("B1", "1.3", "dup", C.PROPERTY))
    with pytest.raises(KeyError):
        C.get_case("nope")


def test_required_cases_per_outcome_type():
    ev = {c.case_id for c in C.required_cases("events")}
    assert {"X3", "X4", "B1", "Z2"} <= ev and "X5" not in ev and "X9" not in ev
    fl = {c.case_id for c in C.required_cases("flags")}
    assert "X5" in fl and "X3" not in fl
    with pytest.raises(ValueError):
        C.required_cases("prices")


def test_evaluate_rules():
    assert C.evaluate("B1", "5/5", 560, 10_000).passed
    assert not C.evaluate("B1", "5/5", 600, 10_000).passed
    assert C.evaluate("B5", "5/5", 800, 10_000).passed  # the old loophole must show
    assert not C.evaluate("B5", "5/5", 500, 10_000).passed
    assert C.evaluate("W1", "gold", 800, 1_000).passed and not C.evaluate("W1", "gold", 799, 1_000).passed
    assert C.evaluate("W2", "silver", 0, 1_000).passed and not C.evaluate("W2", "silver", 1, 1_000).passed
    assert C.evaluate("X9", "lognormal", 4000, 10_000).passed  # recorded only
    fast = C.evaluate("B1", "5/5", 34, 400, fast=True)
    assert fast.passed and fast.threshold == 0.085
    assert not C.evaluate("B1", "5/5", 35, 400, fast=True).passed
    with pytest.raises(ValueError):
        C.evaluate("B4", "all", 0, 1)
    assert C.property_result("B4", "all", True).passed
    with pytest.raises(ValueError):
        C.property_result("B1", "all", True)


def test_git_blob_hash_matches_git():
    assert C.git_blob_sha1(b"hello\n") == "ce013625030ba8dba906f756967f9e9ca394464a"
    if shutil.which("git"):
        out = subprocess.run(
            ["git", "hash-object", "--stdin", "--no-filters"], input=b"abc\x00\n", capture_output=True, check=True
        )
        assert C.git_blob_sha1(b"abc\x00\n") == out.stdout.decode().strip()


# ------------------------------------------------------------ certificate
@pytest.fixture()
def repo(tmp_path):
    for rel, text in {
        "libs/vedic_astrology_core/stats/blocks.py": "X = 1\n",
        "libs/vedic_astrology_core/stats/sub/deep.py": "Y = 2\n",
        "libs/vedic_astrology_core/validity/calibration.py": "Z = 3\n",
        "libs/vedic_astrology_core/domains/base.py": "W = 4\n",
        "tests/simulators.py": "SEED = 5\n",
        "ops/requirements.lock.txt": "numpy==2.0\n",
        "libs/vedic_astrology_core/other/ignored.py": "not certified\n",
    }.items():
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
    (tmp_path / "libs/vedic_astrology_core/stats/__pycache__").mkdir()
    (tmp_path / "libs/vedic_astrology_core/stats/__pycache__/blocks.cpython-312.pyc").write_bytes(b"x")
    return tmp_path


def all_passing_results():
    out = []
    for spec in C.CASES.values():
        if spec.rule == C.PROPERTY:
            out.append(C.property_result(spec.case_id, "all", True))
        elif spec.rule == C.RATE_ABOVE:
            out.append(C.evaluate(spec.case_id, "all", spec.replications, spec.replications))
        elif spec.rule == C.RATE_AT_LEAST:
            out.append(C.evaluate(spec.case_id, "all", spec.replications, spec.replications))
        else:
            out.append(C.evaluate(spec.case_id, "all", 0, spec.replications))
    return out


def test_certificate_round_trip(repo):
    path = repo / C.DEFAULT_CERTIFICATE_PATH
    cert = C.write_certificate(path, all_passing_results(), repo, seed=SEED, created_utc="2026-11-22T00:00:00Z")
    loaded = C.check_certificate(path, repo)
    assert loaded == cert == json.loads(path.read_text())
    for t in C.OUTCOME_TYPES:
        C.check_certificate(path, repo, outcome_type=t)
    assert set(cert["code_hashes"]) == {
        "libs/vedic_astrology_core/stats/blocks.py",
        "libs/vedic_astrology_core/stats/sub/deep.py",
        "libs/vedic_astrology_core/validity/calibration.py",
        "libs/vedic_astrology_core/domains/base.py",
        "tests/simulators.py",
    }
    assert cert["code_hashes"]["tests/simulators.py"] == C.git_blob_sha1(b"SEED = 5\n")
    assert all(cert["case_passed"].values())
    # deterministic: the same inputs give the same bytes
    first = path.read_bytes()
    C.write_certificate(path, all_passing_results()[::-1], repo, seed=SEED, created_utc="2026-11-22T00:00:00Z")
    assert path.read_bytes() == first


def test_certificate_fails_on_a_changed_blob_hash(repo):
    path = repo / "cert.json"
    C.write_certificate(path, all_passing_results(), repo, seed=SEED)
    (repo / "libs/vedic_astrology_core/stats/blocks.py").write_text("X = 2\n")
    with pytest.raises(C.CertificateError, match="stats/blocks.py"):
        C.check_certificate(path, repo)


@pytest.mark.parametrize(
    "change",
    ["add", "remove", "simulators", "lock", "uncertified", "pycache"],
)
def test_certificate_detects_code_and_environment_changes(repo, change):
    path = repo / "cert.json"
    C.write_certificate(path, all_passing_results(), repo, seed=SEED)
    if change == "add":
        (repo / "libs/vedic_astrology_core/validity/verdict.py").write_text("")
    elif change == "remove":
        (repo / "libs/vedic_astrology_core/stats/sub/deep.py").unlink()
    elif change == "simulators":
        (repo / "tests/simulators.py").write_text("SEED = 6\n")
    elif change == "lock":
        (repo / "ops/requirements.lock.txt").write_text("numpy==2.1\n")
    elif change == "uncertified":
        (repo / "libs/vedic_astrology_core/other/ignored.py").write_text("changed\n")
    elif change == "pycache":
        (repo / "libs/vedic_astrology_core/stats/__pycache__/blocks.cpython-312.pyc").write_bytes(b"y")
    if change in ("uncertified", "pycache"):
        C.check_certificate(path, repo)  # outside the certified set: still valid
    else:
        with pytest.raises(C.CertificateError):
            C.check_certificate(path, repo)


def test_certificate_missing_or_edited(repo):
    with pytest.raises(C.CertificateError, match="no calibration certificate"):
        C.check_certificate(repo / "absent.json", repo)
    path = repo / "cert.json"
    C.write_certificate(path, all_passing_results(), repo, seed=SEED)
    cert = json.loads(path.read_text())
    cert["cases"][0]["passed"] = not cert["cases"][0]["passed"]
    path.write_text(json.dumps(cert))
    with pytest.raises(C.CertificateError, match="body_sha256"):
        C.check_certificate(path, repo)
    path.write_text("{not json")
    with pytest.raises(C.CertificateError):
        C.check_certificate(path, repo)


def test_certificate_failed_case_blocks_only_its_outcome_types(repo):
    results = [r for r in all_passing_results() if r.case_id != "X3"]
    results.append(C.evaluate("X3", "mean=0.1,K=8", 700, 10_000))  # fails
    path = repo / "cert.json"
    C.write_certificate(path, results, repo, seed=SEED)
    with pytest.raises(C.CertificateError, match="X3"):
        C.check_certificate(path, repo, outcome_type="events")
    C.check_certificate(path, repo, outcome_type="continuous")
    C.check_certificate(path, repo)  # no type: code and lock only


def test_certificate_refuses_missing_case_and_fast_subset(repo):
    path = repo / "cert.json"
    results = [r for r in all_passing_results() if r.case_id != "B2"]
    C.write_certificate(path, results, repo, seed=SEED)
    with pytest.raises(C.CertificateError, match="B2 missing"):
        C.check_certificate(path, repo, outcome_type="flags")
    results.append(C.evaluate("B2", "lognormal", 10, 400, fast=True))
    C.write_certificate(path, results, repo, seed=SEED)
    with pytest.raises(C.CertificateError, match="replications"):
        C.check_certificate(path, repo, outcome_type="flags")


def test_certificate_refuses_unknown_case(repo):
    bad = C.CaseResult("Q9", "x", 1, 0, 0.0, 0.9, True, C.UPPER_BOUND_AT_MOST, 0.06)
    with pytest.raises(KeyError):
        C.build_certificate([bad], repo, seed=SEED)


def test_real_repository_hashes_include_the_simulators():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    hashes = C.code_hashes(root)
    assert "tests/simulators.py" in hashes
    assert "libs/vedic_astrology_core/validity/calibration.py" in hashes
    assert not any("__pycache__" in k for k in hashes)
