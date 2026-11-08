"""The shared market-study pipeline, driven entirely by ``hypothesis.yaml``.

A study script is a configuration of :func:`run_study`; nothing here knows
which metal it is looking at. Steps, in order, all fixed by the hypothesis
file before the run:

1. Data: try each source in ``data.sources``; the first that answers is
   snapshotted (SHA-256) and used. If none answers, the offline fixture is
   used and every result is marked ``provisional``.
2. Features: engine state sampled at the source's stated local time on each
   trading bar; indicators built from the declared specs and registry rules.
3. Targets: daily log return, absolute return, and an extreme-move flag
   (absolute return above the rolling, past-only quantile).
4. Tests: indicator state on bar ``t-1`` against the target on bar ``t``;
   difference in means, circular-shift null of the indicator, BY across the
   family; explore and confirm periods; SPA over the long/short rule set in
   the confirm period; event study around retrograde stations; exogenous
   Granger (ADL + HAC) on sin/cos of longitudes; stationarity gate.
5. Artifacts: tables (CSV), figures (PNG), ``overlay_frame.csv``,
   ``results.json`` and ``manifest.json`` in the artifacts directory.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import yaml

from ..astrology.ephemeris import EphemerisEngine
from ..stats import granger, multiplicity, permutation, stationarity, walk_forward
from ..stats.manifest import build_manifest, git_commit
from . import align, event_study, features, fetch, overlay
from .study_figures import effects_figure, event_figure

logger = logging.getLogger(__name__)

TARGETS = ("ret", "absret", "extreme")
TARGET_UNITS = {"ret": "bp/day", "absret": "bp/day", "extreme": "pp"}
TARGET_SCALE = {"ret": 1e4, "absret": 1e4, "extreme": 100.0}
REQUIRED = ("study", "data", "indicators", "tests", "periods")


def load_hypothesis(path) -> Dict:
    """Read and minimally validate a hypothesis file."""
    cfg = yaml.safe_load(Path(path).read_text())
    missing = [k for k in REQUIRED if k not in cfg]
    if missing:
        raise ValueError(f"{path}: missing sections {missing}")
    ids = [s["id"] for s in cfg["indicators"]]
    if len(ids) != len(set(ids)):
        raise ValueError(f"{path}: duplicate indicator ids")
    return cfg


# ---------------------------------------------------------------- data
def acquire(cfg: Dict, repo_root: Path, offline: bool = False) -> Tuple:
    """Return ``(prices, record)`` from the first source that answers."""
    data = cfg["data"]
    tried = []
    if not offline:
        for src in data["sources"]:
            try:
                prices = _fetch_source(src, data)
            except Exception as exc:  # any failure: record it and move on
                tried.append({"series_id": src["series_id"], "error": str(exc)[:200]})
                logger.warning("source %s unavailable: %s", src["series_id"], exc)
                continue
            path = fetch.snapshot(prices, cfg["study"])
            record = _record(prices, src, path, provisional=False)
            record["sources_tried"] = tried
            return prices, record
    fixture = repo_root / data["fixture"]["path"]
    prices = fetch.read_tidy_csv(fixture)
    prices.attrs["source_url"] = f"fixture:{data['fixture']['path']}"
    src = dict(data["fixture"], adapter="fixture")
    record = _record(prices, src, fixture, provisional=True)
    record["sources_tried"] = tried or [{"series_id": "*", "error": "offline"}]
    return prices, record


def _fetch_source(src: Dict, data: Dict) -> pd.DataFrame:
    start, end = data.get("start"), data.get("end")
    if src["adapter"] == "fred":
        return fetch.fred(src["series_id"], start=start, end=end)
    if src["adapter"] == "yahoo":
        df = fetch.yahoo(src["series_id"], start=start or "1990-01-01")
        return fetch.clip(df, None, end)
    raise ValueError(f"unknown adapter {src['adapter']!r}")


def _record(prices: pd.DataFrame, src: Dict, path: Path, provisional: bool) -> Dict:
    digest = fetch.sha256_bytes(Path(path).read_bytes())
    rec = fetch.snapshot_manifest(prices, digest)
    rec.update(
        {
            "label": src["label"],
            "adapter": src["adapter"],
            "sample_time": src["sample_time"],
            "tz": src["tz"],
            "snapshot": Path(path).name,
            "provisional": provisional,
        }
    )
    return rec


# ------------------------------------------------------------ features
def build_frame(prices: pd.DataFrame, cfg: Dict, record: Dict, engine) -> Tuple:
    """Aligned bars, indicator matrix and the raw feature frame."""
    bodies = sorted(
        {s["body"].upper() for s in cfg["indicators"] if "body" in s}
        | {b.upper() for b in cfg.get("granger", {}).get("bodies", [])}
        | {b.upper() for b in cfg.get("event_study", {}).get("bodies", [])}
        | {"SUN", "MOON"}
    )
    use_case = cfg.get("rules_use_case")

    def source(instants):
        return features.indicator_frame(
            instants, bodies, engine, rules_use_case=use_case
        )

    aligned = align.align(
        prices, source, sample_time=record["sample_time"], tz=record["tz"]
    )
    specs, skipped = [], []
    for spec in cfg["indicators"]:
        if spec["kind"] == "rule" and f"rule:{spec['rule']}" not in aligned.columns:
            skipped.append(spec["id"])
            continue
        specs.append(spec)
    if skipped:
        logger.warning("registry rules not evaluated, dropped: %s", skipped)
    indicators = features.build_indicators(aligned, specs)
    return aligned, indicators, skipped


def targets(close: np.ndarray, window: int, quantile: float) -> pd.DataFrame:
    """Daily log return, |return| and past-only extreme-move flag per bar."""
    r = np.concatenate([[np.nan], np.diff(np.log(close))])
    a = np.abs(r)
    past = pd.Series(a).shift(1).rolling(window, min_periods=window).quantile(quantile)
    extreme = np.where(past.notna(), (a > past.to_numpy()).astype(float), np.nan)
    return pd.DataFrame({"ret": r, "absret": a, "extreme": extreme})


# --------------------------------------------------------------- tests
def _diff_means(x, y) -> float:
    x = np.asarray(x, dtype=bool)
    return float(np.mean(y[x]) - np.mean(y[~x]))


def indicator_tests(
    indicators: pd.DataFrame,
    tgt: pd.DataFrame,
    periods: Dict[str, np.ndarray],
    tcfg: Dict,
    rng: np.random.Generator,
) -> pd.DataFrame:
    """One permutation test per (indicator, target, period)."""
    rows = []
    min_bars = int(tcfg["min_active_bars"])
    for period, mask in periods.items():
        for target in TARGETS:
            y_all = tgt[target].to_numpy()
            for ind in indicators.columns:
                # State known on bar t-1 against the outcome on bar t.
                x_all = np.concatenate([[False], indicators[ind].to_numpy()[:-1]])
                keep = mask & ~np.isnan(y_all)
                keep[0] = False
                x, y = x_all[keep], y_all[keep]
                row = {
                    "indicator": ind,
                    "target": target,
                    "period": period,
                    "n": int(len(y)),
                    "n_active": int(x.sum()),
                }
                reason = None
                if len(y) < 2 * int(tcfg["min_shift_bars"]) + 1:
                    reason = "period shorter than twice the minimum shift"
                elif x.sum() < min_bars or (~x).sum() < min_bars:
                    reason = f"fewer than {min_bars} active or inactive bars"
                if reason:
                    rows.append(
                        {**row, "testable": False, "p_value": np.nan, "reason": reason}
                    )
                    continue
                res = permutation.permutation_test(
                    _diff_means,
                    x,
                    y,
                    rng=rng,
                    null="circular_shift",
                    n_perm=int(tcfg["n_perm"]),
                    alternative="two-sided",
                    min_shift=int(tcfg["min_shift_bars"]),
                    mean_block=float(tcfg["mean_block_bars"]),
                    n_boot=int(tcfg["n_boot_ci"]),
                )
                s = TARGET_SCALE[target]
                rows.append(
                    {
                        **row,
                        "testable": True,
                        "mean_active": float(np.mean(y[x])) * s,
                        "mean_inactive": float(np.mean(y[~x])) * s,
                        "effect": res.observed * s,
                        "ci_low": res.ci_low * s,
                        "ci_high": res.ci_high * s,
                        "effect_z": res.effect_z,
                        "p_value": res.p_value,
                        "unit": TARGET_UNITS[target],
                    }
                )
    return pd.DataFrame(rows)


def correct(tests: pd.DataFrame, method: str, alpha: float) -> pd.DataFrame:
    """BY (or other) correction within each period across indicators x targets."""
    parts = []
    for period, grp in tests.groupby("period", sort=False):
        ok = grp[grp["testable"]].rename(columns={"indicator": "rule"})
        fam = multiplicity.family(
            ok, method=method, alpha=alpha, keys=("rule", "target")
        )
        fam = fam.rename(columns={"rule": "indicator"})
        rest = grp[~grp["testable"]].assign(q_value=np.nan, significant=False)
        parts.append(pd.concat([fam, rest], ignore_index=True))
    return pd.concat(parts, ignore_index=True)


def confirm(tests: pd.DataFrame, method: str, alpha: float) -> pd.DataFrame:
    """Carry explore-significant tests to the confirm period and re-correct."""
    ex = tests[(tests["period"] == "explore") & tests["significant"]]
    co = tests[(tests["period"] == "confirm") & tests["testable"]]
    merged = ex.merge(co, on=["indicator", "target"], suffixes=("_explore", ""))
    if merged.empty:
        return merged
    merged["q_confirm"] = multiplicity.adjust(merged["p_value"].to_numpy(), method)
    same_sign = np.sign(merged["effect"]) == np.sign(merged["effect_explore"])
    merged["confirmed"] = same_sign & (merged["q_confirm"] < alpha)
    return merged


def spa(indicators, tgt, explore, confirm_mask, explore_tests, rng, cfg) -> Dict:
    """Hansen SPA in the confirm period over long/short indicator rules.

    Direction per indicator is the sign of its explore-period return effect;
    the benchmark is being flat. Loss is minus the rule's daily return.
    """
    r = np.nan_to_num(tgt["ret"].to_numpy())
    eff = explore_tests[(explore_tests["target"] == "ret") & explore_tests["testable"]]
    eff = eff.set_index("indicator")["effect"]
    cols = [c for c in indicators.columns if c in eff.index]
    if not cols:
        return {
            "n_rules": 0,
            "p_consistent": None,
            "skipped": "no testable explore-period return effects",
        }
    lagged = np.vstack(
        [np.concatenate([[0.0], indicators[c].to_numpy()[:-1]]) for c in cols]
    ).T
    pos = lagged * np.sign(eff[cols].to_numpy())[None, :]
    keep = confirm_mask.copy()
    keep[0] = False
    losses = -(pos[keep] * r[keep, None])
    res = walk_forward.spa_test(
        np.zeros(keep.sum()),
        losses,
        rng=rng,
        n_boot=int(cfg["n_boot"]),
        mean_block=float(cfg["mean_block_bars"]),
    )
    best = cols[res.best_model]
    return {
        "n_rules": len(cols),
        "statistic": res.statistic,
        "p_consistent": res.p_consistent,
        "p_lower": res.p_lower,
        "p_upper": res.p_upper,
        "best_rule": best,
        "best_mean_return_bp": float(res.mean_loss_diff[res.best_model] * 1e4),
        "n_boot": res.n_boot,
    }


def station_events(aligned: pd.DataFrame, bodies) -> Dict[str, np.ndarray]:
    """Bars on which each body is first seen retrograde (station retrograde)."""
    return {
        b.upper(): align.run_starts(aligned[f"{b.upper()}_retro"].to_numpy())
        for b in bodies
    }


def run_event_study(aligned, events, ecfg, rng, method, alpha) -> pd.DataFrame:
    """Event study per body and horizon, one BY family across all of them."""
    frames = []
    for body, bars in events.items():
        out = event_study.event_study(
            aligned,
            bars,
            tuple(ecfg["horizons"]),
            rng=rng,
            n_boot=int(ecfg["n_boot"]),
            mean_block=float(ecfg["mean_block_bars"]),
        )
        frames.append(out.assign(body=body))
    res = pd.concat(frames, ignore_index=True)
    for c in ("mean", "null_mean", "null_lo", "null_hi", "unconditional"):
        res[c] = res[c] * 1e4
    res["q_value"] = multiplicity.adjust(res["p_value"].to_numpy(), method)
    res["significant"] = res["q_value"] < alpha
    return res


def run_granger(aligned, gcfg, method, alpha) -> List[Dict]:
    """Exogenous ADL Wald tests on sin/cos of sidereal longitude, per body."""
    idx = pd.DatetimeIndex(aligned["date"])
    close = pd.Series(aligned["close"].to_numpy(), index=idx)
    rows = []
    for target in gcfg["targets"]:
        if target == "garch_abs" and not granger.garch_available():
            rows.append(
                {
                    "body": "*",
                    "target": target,
                    "p_value": None,
                    "reason": "arch not installed; target omitted",
                }
            )
            continue
        for body in gcfg["bodies"]:
            lon = np.radians(aligned[f"{body.upper()}_lon"].to_numpy())
            x = pd.DataFrame({"sin": np.sin(lon), "cos": np.cos(lon)}, index=idx)
            res = granger.exog_granger(
                close,
                x,
                lags=tuple(gcfg["lags"]),
                y_lags=int(gcfg["y_lags"]),
                target=target,
            )
            rows.append(
                {
                    "body": body.upper(),
                    "target": target,
                    "f_stat": res.get("f_stat"),
                    "p_value": res.get("p_value"),
                    "n": res.get("n"),
                    "transform": res["transform"],
                }
            )
    ps = [r["p_value"] for r in rows if r["p_value"] is not None]
    qs = iter(multiplicity.adjust(ps, method)) if ps else iter([])
    for r in rows:
        if r["p_value"] is not None:
            r["q_value"] = float(next(qs))
            r["significant"] = r["q_value"] < alpha
    return rows


def stationarity_table(close: np.ndarray, tgt: pd.DataFrame) -> List[Dict]:
    """ADF and KPSS on log price, returns and absolute returns."""
    out = []
    series = {"log_price": np.log(close), "ret": tgt["ret"], "absret": tgt["absret"]}
    for name, values in series.items():
        t = stationarity.adf_kpss(pd.Series(values).dropna())
        out.append({"series": name, **t, "stationary": stationarity.is_stationary(t)})
    return out


# ----------------------------------------------------------- pipeline
def run_study(
    hypothesis_path, out_dir, repo_root, seed: int = 42, offline: bool = False
) -> Dict:
    """Run the whole pre-registered pipeline and write every artifact."""
    cfg = load_hypothesis(hypothesis_path)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)
    engine = EphemerisEngine(node_model=cfg.get("node_model", "mean"))
    tcfg, alpha, method = (
        cfg["tests"],
        float(cfg["tests"]["alpha"]),
        cfg["tests"]["correction"],
    )

    prices, record = acquire(cfg, Path(repo_root), offline)
    aligned, indicators, skipped = build_frame(prices, cfg, record, engine)
    close = aligned["close"].to_numpy(dtype=float)
    tgt = targets(
        close, int(tcfg["extreme_window_bars"]), float(tcfg["extreme_quantile"])
    )
    dates = pd.DatetimeIndex(aligned["date"])
    confirm_start = cfg["periods"]["confirm_start"]
    explore, confirm_mask = walk_forward.time_split(dates, confirm_start)
    periods = {
        "full": np.ones(len(dates), bool),
        "explore": explore,
        "confirm": confirm_mask,
    }

    tests = correct(indicator_tests(indicators, tgt, periods, tcfg, rng), method, alpha)
    confirmed = confirm(tests, method, alpha)
    explore_tests = tests[tests["period"] == "explore"]
    spa_res = spa(
        indicators, tgt, explore, confirm_mask, explore_tests, rng, cfg["spa"]
    )
    events = station_events(aligned, cfg["event_study"]["bodies"])
    ev = run_event_study(aligned, events, cfg["event_study"], rng, method, alpha)
    gr = run_granger(aligned, cfg["granger"], method, alpha)
    stat_rows = stationarity_table(close, tgt)

    commit = git_commit(repo_root)
    prov = {
        "data_sha256": record["sha256"],
        "commit": commit["commit"],
        "seed": seed,
        "source": record["label"] + (" (PROVISIONAL)" if record["provisional"] else ""),
    }
    _write_tables(out, tests, confirmed, ev, aligned, indicators)
    _write_figures(out, aligned, indicators, tests, ev, events, cfg, prov)

    results = _results(
        cfg,
        seed,
        record,
        tests,
        confirmed,
        spa_res,
        ev,
        gr,
        stat_rows,
        indicators,
        skipped,
        aligned,
        commit,
    )
    (out / "results.json").write_text(json.dumps(results, indent=2, default=_json))
    manifest = build_manifest(
        inputs=[
            {
                "path": (
                    str(Path(repo_root) / "data" / "snapshots" / record["snapshot"])
                    if not record["provisional"]
                    else str(Path(repo_root) / cfg["data"]["fixture"]["path"])
                ),
                "row_count": record["rows"],
                "date_range": [record["date_min"], record["date_max"]],
            }
        ],
        seed=seed,
        engine=engine,
        repo_root=repo_root,
        extra={
            "study": cfg["study"],
            "hypothesis_sha256": fetch.sha256_bytes(Path(hypothesis_path).read_bytes()),
            "provisional": record["provisional"],
            "artifacts": sorted(p.name for p in out.iterdir() if p.is_file()),
        },
    )
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2, default=str))
    return results


def _write_tables(out, tests, confirmed, ev, aligned, indicators) -> None:
    tests.to_csv(out / "tbl_indicator_tests.csv", index=False, float_format="%.6g")
    confirmed.to_csv(out / "tbl_confirmation.csv", index=False, float_format="%.6g")
    ev.to_csv(out / "tbl_event_study.csv", index=False, float_format="%.6g")
    frame = overlay.overlay_frame(aligned, indicators)
    frame.to_csv(out / "overlay_frame.csv", index=False, float_format="%.6g")


def _write_figures(out, aligned, indicators, tests, ev, events, cfg, prov) -> None:
    show = cfg["figures"]["overlay_indicator"]
    overlay.overlay_plot(
        aligned,
        indicators[show].to_numpy(),
        f"{cfg['title_short']}: price and {show.replace('_', ' ')}",
        provenance=prov,
        status="EXPLORATORY",
        label=show.replace("_", " "),
        path=str(out / "fig_overlay.png"),
    )
    body = cfg["figures"]["station_body"].upper()
    dates = pd.DatetimeIndex(aligned["date"])
    overlay.overlay_plot(
        aligned,
        list(dates[events[body]]),
        f"{cfg['title_short']}: price and {body.title()} " "retrograde stations",
        provenance=prov,
        label=f"{body.title()} station retrograde",
        path=str(out / "fig_stations.png"),
    )
    effects_figure(tests, prov, str(out / "fig_effects.png"))
    event_figure(ev, prov, str(out / "fig_event_study.png"))


def _json(value):
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return None if np.isnan(value) else float(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.isoformat()
    return str(value)


def _records(df: pd.DataFrame) -> List[Dict]:
    return json.loads(df.to_json(orient="records", double_precision=6))


def _results(
    cfg,
    seed,
    record,
    tests,
    confirmed,
    spa_res,
    ev,
    gr,
    stat_rows,
    indicators,
    skipped,
    aligned,
    commit,
) -> Dict:
    ex = tests[(tests["period"] == "explore") & tests["testable"]]
    n_conf = int(confirmed["confirmed"].sum()) if len(confirmed) else 0
    n_sig = int(ex["significant"].sum())
    if len(ex) == 0:
        verdict = "not_testable"
    elif n_conf:
        verdict = "positive" if n_conf == n_sig else "mixed"
    else:
        verdict = "null" if n_sig == 0 else "not_replicated"
    full = tests[tests["period"] == "full"]
    return {
        "study": cfg["study"],
        "title": cfg.get("title"),
        "provisional": bool(record["provisional"]),
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "seed": seed,
        "git": commit,
        "data": record,
        "bars": int(len(aligned)),
        "periods": {
            "explore": [
                str(aligned["date"].iloc[0].date()),
                cfg["periods"]["explore_end"],
            ],
            "confirm": [
                cfg["periods"]["confirm_start"],
                str(aligned["date"].iloc[-1].date()),
            ],
        },
        "family": {
            "method": cfg["tests"]["correction"],
            "alpha": cfg["tests"]["alpha"],
            "size_explore": int(len(ex)),
            "indicators": list(indicators.columns),
            "indicators_not_evaluated": skipped,
            "targets": list(TARGETS),
            "units": TARGET_UNITS,
        },
        "headline": {
            "verdict": verdict,
            "n_tests_explore": int(len(ex)),
            "n_significant_explore": n_sig,
            "n_confirmed": n_conf,
            "n_significant_full": int(full["significant"].sum()),
            "spa_p": spa_res["p_consistent"],
            "n_event_tests": int(len(ev)),
            "n_event_significant": int(ev["significant"].sum()),
        },
        "indicator_activity": {c: float(indicators[c].mean()) for c in indicators},
        "tests": _records(tests),
        "confirmation": _records(confirmed) if len(confirmed) else [],
        "spa": spa_res,
        "event_study": _records(ev),
        "granger": gr,
        "stationarity": stat_rows,
    }


def main(hypothesis_path, out_dir, repo_root, argv=None) -> int:
    """Command line used by each study's ``scripts/pipeline.py``."""
    import argparse

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--offline",
        action="store_true",
        help="use the fixture; results are marked provisional",
    )
    parser.add_argument("--out", default=str(out_dir))
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    res = run_study(hypothesis_path, args.out, repo_root, args.seed, args.offline)
    h = res["headline"]
    print(
        f"{res['study']}: verdict={h['verdict']} explore tests={h['n_tests_explore']}"
        f" significant={h['n_significant_explore']} confirmed={h['n_confirmed']}"
        f" provisional={res['provisional']} -> {args.out}"
    )
    return 0
