"""Controls, rule-free classifier, Bayesian summaries and power for the study.

Secondary analyses added by the 2026-11-08 amendment of ``hypothesis.yaml``
(blocks ``controls`` and ``secondary``). None of them changes the registered
family or its verdict; they say what the verdict is worth:

* positive control: tidal phase (semidiurnal and spring-neap) tested exactly
  like an indicator;
* negative control: every registered indicator on a sky rotated by a fixed
  offset;
* classifier: out-of-sample AUC of a ridge logistic model from sky features
  to event days, against the same model on circularly shifted skies;
* Bayes: posterior rate ratio under sceptical and enthusiastic priors, with
  the Savage-Dickey Bayes factor, for every indicator;
* power: the minimum detectable rate ratio for every indicator.
"""

from typing import Callable, Dict

import numpy as np
import pandas as pd

from vedic_astrology_core.stats import bayes, classify, controls, power
from vedic_astrology_core.stats.multiplicity import adjust

LONGITUDE_BODIES = (
    "SUN",
    "MOON",
    "MARS",
    "MERCURY",
    "VENUS",
    "JUPITER",
    "SATURN",
    "KETU",
)


def _per_day(grid: pd.DatetimeIndex) -> int:
    return int(round(pd.Timedelta(days=1) / (grid[1] - grid[0])))


# ----------------------------------------------------------- positive control
def tidal_frame(eph: pd.DataFrame, cfg: Dict) -> pd.DataFrame:
    """Return the tidal-phase control indicators on the ephemeris grid."""
    pos = cfg["positive"]
    ha = controls.moon_hour_angle(eph["jd"].to_numpy(), float(pos["longitude_deg_e"]))
    el = controls.lunar_elongation(eph["lon_MOON"], eph["lon_SUN"])
    cols = controls.tidal_phase_indicators(
        ha,
        el,
        semidiurnal_half_width_deg=float(pos["semidiurnal_half_width_deg"]),
        spring_half_width_deg=float(pos["spring_half_width_deg"]),
    )
    return pd.DataFrame(cols, index=eph.index)


def positive_control(
    hyp, grid, eph, bins_by_cat, seed, n_draws, run_tests: Callable
) -> Dict:
    """Test the tidal indicators like indicators; decide detection."""
    cfg = hyp["controls"]
    tf = tidal_frame(eph, cfg)
    specs = cfg["positive"]["indicators"]
    sub = dict(hyp, indicators=specs)
    tests = run_tests(sub, grid, tf, bins_by_cat, seed + 1000, n_draws)
    tests = tests[tests["skipped"].fillna("") == ""].copy()
    period = cfg["positive"]["decision_period"]
    cats = cfg["positive"]["decision_catalogues"]
    dec = tests[(tests["period"] == period) & tests["catalogue"].isin(cats)].copy()
    dec["q_value"] = adjust(dec["p_value"].to_numpy(), "by")
    alpha = float(hyp["test"]["alpha"])
    dec["detected"] = (dec["q_value"] < alpha) & (dec["rate_ratio"] > 1)
    best = dec.sort_values("p_value").iloc[0]
    return {
        "references": controls.REFERENCES,
        "time_fraction": {c: float(tf[c].mean()) for c in tf},
        "tests": tests,
        "decision": dec,
        "detected": bool(dec["detected"].any()),
        "best": {
            k: best[k]
            for k in (
                "indicator",
                "catalogue",
                "rate_ratio",
                "ci_low",
                "ci_high",
                "p_value",
                "q_value",
                "n_events",
            )
        },
        "frame": tf,
    }


# ----------------------------------------------------------- negative control
def negative_control(
    hyp, grid, frame, bins_by_cat, seed, n_draws, run_tests: Callable
) -> Dict:
    """Every registered indicator on a sky rotated by a fixed offset."""
    cfg = hyp["controls"]["negative"]
    offset = int(cfg["offset_days"]) * _per_day(grid)
    shifted = controls.shifted_sky(frame, offset)
    cats = {k: v for k, v in bins_by_cat.items() if k in ("gk", "nn")}
    tests = run_tests(hyp, grid, shifted, cats, seed + 2000, n_draws)
    ex = tests[(tests["period"] == "explore") & (tests["skipped"].fillna("") == "")]
    ex = ex.copy()
    ex["q_value"] = adjust(ex["p_value"].to_numpy(), "by")
    alpha = float(hyp["test"]["alpha"])
    return {
        "offset_days": int(cfg["offset_days"]),
        "family_size": int(len(ex)),
        "n_nominal": int((ex["p_value"] < alpha).sum()),
        "expected_nominal": float(alpha * len(ex)),
        "n_significant": int((ex["q_value"] < alpha).sum()),
        "min_p": float(ex["p_value"].min()),
        "tests": ex,
    }


# ----------------------------------------------------------------- classifier
def daily_features(eph: pd.DataFrame, per_day: int, hour: int = 12) -> np.ndarray:
    """Sky features once a day (at ``hour`` UTC).

    Nine longitudes as sin and cos (Rahu = Ketu + 180, so its pair is the
    negative of Ketu's), eight speeds (Rahu's equals Ketu's), tithi one-hot
    (30) and Moon nakshatra one-hot (27).
    """
    rows = eph.iloc[hour::per_day]
    cols = []
    for b in LONGITUDE_BODIES:
        r = np.radians(rows[f"lon_{b}"].to_numpy())
        cols += [np.sin(r), np.cos(r)]
    r = np.radians(rows["lon_KETU"].to_numpy() + 180.0)
    cols += [np.sin(r), np.cos(r)]
    for b in LONGITUDE_BODIES:
        cols.append(rows[f"speed_{b}"].to_numpy())
    el = controls.lunar_elongation(rows["lon_MOON"], rows["lon_SUN"])
    tithi = np.floor(el / 12.0).astype(int) % 30
    nak = np.floor(rows["lon_MOON"].to_numpy() / (360.0 / 27.0)).astype(int) % 27
    x = np.column_stack(cols)
    return np.column_stack([x, np.eye(30)[tithi], np.eye(27)[nak]])


def event_days(bins: np.ndarray, per_day: int, n_days: int) -> np.ndarray:
    """0/1 per day: at least one event that day."""
    y = np.zeros(n_days, dtype=int)
    d = np.asarray(bins) // per_day
    y[d[d < n_days]] = 1
    return y


def classifier(hyp, grid, eph, bins, slices, seed) -> Dict:
    """Forward-chaining AUC on exploration and a frozen holdout AUC."""
    cfg = hyp["secondary"]["classifier"]
    per_day = _per_day(grid)
    x = daily_features(eph, per_day)
    n_days = len(x)
    y = event_days(bins, per_day, n_days)
    ex_days = slices["explore"].stop // per_day
    co_day0 = -(-slices["confirm"].start // per_day)
    min_shift = int(hyp["test"]["min_shift_days"])
    rng = np.random.default_rng([seed, 31])
    cv = classify.shifted_sky_auc_test(
        x[:ex_days],
        y[:ex_days],
        min_shift,
        int(cfg["n_draws"]),
        rng,
        n_folds=int(cfg["n_folds"]),
        l2=float(cfg["l2"]),
    )
    hold = classify.holdout_auc(
        x[:ex_days], y[:ex_days], x[co_day0:], y[co_day0:], float(cfg["l2"])
    )
    offsets = np.random.default_rng([seed, 32]).integers(
        min_shift, n_days - min_shift + 1, size=int(cfg["n_draws"])
    )
    null_hold = []
    for k in offsets:
        xs = np.roll(x, int(k), axis=0)
        null_hold.append(
            classify.holdout_auc(
                xs[:ex_days], y[:ex_days], xs[co_day0:], y[co_day0:], float(cfg["l2"])
            )
        )
    null_hold = np.asarray(null_hold)
    q = np.quantile(null_hold, [0.05, 0.5, 0.95])
    return {
        "catalogue": "gk",
        "n_features": int(x.shape[1]),
        "explore_days": int(ex_days),
        "explore_event_days": int(y[:ex_days].sum()),
        "confirm_days": int(n_days - co_day0),
        "confirm_event_days": int(y[co_day0:].sum()),
        "model": "L2 logistic, l2 = %g, standardised features" % cv.l2,
        "explore_cv": {
            "auc": cv.auc,
            "n_folds": cv.n_folds,
            "n_draws": cv.n_draws,
            "null_q05": cv.null_q05,
            "null_q50": cv.null_q50,
            "null_q95": cv.null_q95,
            "p_value": cv.p_value,
        },
        "holdout": {
            "auc": hold,
            "n_draws": int(len(null_hold)),
            "null_q05": float(q[0]),
            "null_q50": float(q[1]),
            "null_q95": float(q[2]),
            "p_value": float((1 + np.sum(null_hold >= hold)) / (len(null_hold) + 1)),
        },
    }


# ---------------------------------------------------------------- Bayes, power
def bayes_table(fam: pd.DataFrame, conf: pd.DataFrame) -> pd.DataFrame:
    """Posterior summaries for every exploration and confirmation test."""
    rows = []
    for period, df in (("explore", fam), ("confirm", conf)):
        for _, r in df.iterrows():
            s = bayes.summarise(
                int(r["n_in"]),
                float(r["t_in_days"]),
                int(r["n_out"]),
                float(r["t_out_days"]),
            )
            row = {
                "period": period,
                "catalogue": r["catalogue"],
                "indicator": r["indicator"],
                "label": r["label"],
                "rate_ratio": float(r["rate_ratio"]),
            }
            for prior, v in s.items():
                for k in (
                    "rr_median",
                    "rr_cri_low",
                    "rr_cri_high",
                    "p_rr_gt_1",
                    "bf10",
                ):
                    row[f"{prior}_{k}"] = v[k]
            rows.append(row)
    return pd.DataFrame(rows)


def power_rows(
    hyp, tests: pd.DataFrame, extra: pd.DataFrame, seed: int
) -> pd.DataFrame:
    """Minimum detectable RR per indicator, catalogue and period."""
    cfg = hyp["secondary"]["power"]
    df = pd.concat([tests, extra], ignore_index=True)
    df = df[(df["skipped"].fillna("") == "") & df["catalogue"].isin(["gk", "nn"])]
    specs, keys = [], []
    for _, r in df.iterrows():
        specs.append(
            {
                "id": r["indicator"],
                "label": r["label"],
                "n_events": r["n_events"],
                "duty_cycle": r["time_fraction"],
                "direction": r["direction"],
            }
        )
        keys.append((r["catalogue"], r["period"]))
    tab = power.power_table(
        specs,
        np.random.default_rng([seed, 41]),
        alpha=float(cfg["alpha"]),
        power=float(cfg["power"]),
        n_sim=int(cfg["n_sim"]),
    )
    tab.insert(0, "catalogue", [k[0] for k in keys])
    tab.insert(1, "period", [k[1] for k in keys])
    return tab


def records(df: pd.DataFrame):
    """JSON-safe records."""
    import json

    return json.loads(df.to_json(orient="records", double_precision=10))
