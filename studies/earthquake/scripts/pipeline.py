#!/usr/bin/env python3
"""Earthquake study pipeline: every table, figure and number in the paper.

Usage::

    python studies/earthquake/scripts/pipeline.py --seed 42 [--offline]
        [--snapshot data/snapshots/usgs_<sha12>.csv] [--n-draws 10000]

Reads ``studies/earthquake/hypothesis.yaml`` (the pre-registration), the
catalogue snapshot (fetched with ``fetch_catalogue.py`` if none exists) and
the ephemeris engine, and writes into ``studies/earthquake/artifacts/``:
CSV tables, PNG figures with provenance footers, ``results.json`` (read by
the paper) and ``manifest.json``.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Optional, Tuple

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
for p in (HERE, REPO, REPO / "libs"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import decluster  # noqa: E402
import fetch_catalogue as fc  # noqa: E402
import indicators as ind  # noqa: E402
from count_models import compare_nb_models, monthly_design  # noqa: E402
from studies._paths import SNAPSHOT_ROOT, artifacts_dir  # noqa: E402
from vedic_astrology_core.astrology.ephemeris import EphemerisEngine  # noqa: E402
from vedic_astrology_core.stats.manifest import (  # noqa: E402
    file_sha256,
    git_commit,
    write_manifest,
)
from vedic_astrology_core.stats.molchan import (  # noqa: E402
    area_skill_score,
    binomial_bound,
    molchan_p_value,
    molchan_point,
    molchan_trajectory,
    time_random_reference,
)
from vedic_astrology_core.stats.multiplicity import adjust, family  # noqa: E402
from vedic_astrology_core.stats.rates import rate_ratio_shift_test  # noqa: E402
from vedic_astrology_core.stats.walk_forward import spa_test  # noqa: E402

CATALOGUES = {"raw": "Undeclustered", "gk": "Gardner-Knopoff",
              "nn": "Nearest-neighbour"}
PERIODS = ("explore", "confirm", "full")
MIN_EVENTS = 5


# ------------------------------------------------------------ catalogue
def latest_snapshot(hyp: Dict) -> Optional[Path]:
    """Return the newest USGS snapshot made for this pre-registration."""
    best = None
    for path in sorted(SNAPSHOT_ROOT.glob("usgs_*.csv")):
        man = path.with_name(path.name + ".manifest.json")
        if not man.exists():
            continue
        meta = json.loads(man.read_text())
        if meta.get("hypothesis_id") == hyp["id"] and meta.get("query") == (
                hyp["catalogue"]):
            if best is None or meta["created_utc"] > best[0]:
                best = (meta["created_utc"], path)
    return best[1] if best else None


def load_catalogue(
    snapshot: Optional[Path] = None, offline: bool = False
) -> Tuple[pd.DataFrame, Dict]:
    """Return the analysed catalogue (Mw >= threshold) and its description."""
    hyp = fc.load_hypothesis()
    if snapshot is None and offline:
        snapshot, source = fc.snapshot(offline=True, hyp=hyp)
    elif snapshot is None:
        snapshot = latest_snapshot(hyp)
        source = "usgs_fdsn"
        if snapshot is None:
            snapshot, source = fc.snapshot(hyp=hyp)
    else:
        source = "offline_json" if Path(snapshot).name.startswith(
            "offline_") else "usgs_fdsn"
    snapshot = Path(snapshot)
    raw = pd.read_csv(snapshot)
    raw["time"] = pd.to_datetime(raw["time"], utc=True, format="ISO8601")
    cat = fc.homogenise_mw(raw, hyp["magnitude"]["rules"])
    comp = fc.completeness(cat, hyp["magnitude"])
    analysed = cat[cat["mw"] >= comp["threshold"] - 1e-6].reset_index(drop=True)
    info = {
        "source": source,
        "snapshot": str(snapshot.relative_to(REPO)) if snapshot.is_relative_to(
            REPO) else str(snapshot),
        "sha256": file_sha256(snapshot),
        "n_polygon": int(len(raw)),
        "mag_types": {str(k): int(v) for k, v in
                      raw["magType"].fillna("unknown").value_counts().items()},
        "mw_rules": {str(k): int(v) for k, v in
                     cat["mw_rule"].value_counts().items()},
        "completeness": comp,
        "n_analysed": int(len(analysed)),
        "first_event": str(raw["time"].min()),
        "last_event": str(raw["time"].max()),
        "all_mw": cat["mw"].to_numpy(),
    }
    return analysed, info


# -------------------------------------------------------------- testing
def period_slices(hyp: Dict, grid: pd.DatetimeIndex) -> Dict[str, slice]:
    """Return grid slices of the exploration, confirmation and full periods."""
    split = hyp["split"]
    c0 = pd.Timestamp(split["confirm"][0], tz="UTC")
    e1 = pd.Timestamp(split["explore"][1], tz="UTC") + pd.Timedelta(days=1)
    e1 = e1 - pd.Timedelta(days=int(split.get("purge_days", 0)))
    return {
        "explore": slice(0, int(grid.searchsorted(e1))),
        "confirm": slice(int(grid.searchsorted(c0)), len(grid)),
        "full": slice(0, len(grid)),
    }


def run_tests(hyp, grid, frame, bins_by_cat, seed, n_draws) -> pd.DataFrame:
    """Run the circular-shift rate test for every catalogue/period/indicator."""
    min_shift = int(hyp["test"]["min_shift_days"]) * int(round(
        pd.Timedelta(days=1) / (grid[1] - grid[0])))
    slices = period_slices(hyp, grid)
    rows = []
    for ci, (cat, bins) in enumerate(bins_by_cat.items()):
        for pi, period in enumerate(PERIODS):
            sl = slices[period]
            ev = bins[(bins >= sl.start) & (bins < sl.stop)] - sl.start
            for ii, spec in enumerate(hyp["indicators"]):
                alt = spec["direction"]
                row = {"catalogue": cat, "period": period,
                       "indicator": spec["id"], "label": spec["label"],
                       "direction": alt, "n_events": int(len(ev))}
                series = frame[spec["id"]].to_numpy()[sl]
                if len(ev) < MIN_EVENTS or series.all() or not series.any():
                    row["skipped"] = "too few events or degenerate indicator"
                    rows.append(row)
                    continue
                rng = np.random.default_rng([seed, ci, pi, ii])
                res = rate_ratio_shift_test(ev, series, min_shift, n_draws, rng,
                                            alternative=alt)
                ex = res.exact
                row.update({
                    "n_in": ex.n_in, "t_in_days": ex.t_in / 24.0,
                    "n_out": ex.n_out, "t_out_days": ex.t_out / 24.0,
                    "time_fraction": ex.t_in / (ex.t_in + ex.t_out),
                    "rate_ratio": ex.rate_ratio, "ci_low": ex.ci_low,
                    "ci_high": ex.ci_high, "p_value": res.p_value,
                    "p_poisson": ex.p_greater if alt == "greater" else (
                        ex.p_two_sided),
                    "null_median": res.null_median, "null_q025": res.null_q025,
                    "null_q975": res.null_q975, "skipped": "",
                })
                rows.append(row)
    return pd.DataFrame(rows)


def in_direction(rr: float, direction: str) -> bool:
    """Return True when the rate ratio lies in the registered direction."""
    if direction == "greater":
        return rr > 1
    if direction == "less":
        return rr < 1
    return True


def family_tables(hyp, tests: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    """Return the exploration family, confirmation and raw descriptive tables."""
    alpha = float(hyp["test"]["alpha"])
    method = {"benjamini_yekutieli": "by", "benjamini_hochberg": "bh",
              "bonferroni": "bonferroni"}[hyp["test"]["correction"]]
    ok = tests["skipped"].fillna("") == ""
    ex = tests[ok & (tests["period"] == "explore")
               & tests["catalogue"].isin(["gk", "nn"])]
    fam = family(ex.rename(columns={"indicator": "rule", "catalogue": "target"}),
                 method=method, alpha=alpha)
    fam = fam.rename(columns={"rule": "indicator", "target": "catalogue"})
    fam["carried"] = fam["significant"].to_numpy() & np.array([
        in_direction(r, d) for r, d in zip(fam["rate_ratio"], fam["direction"])],
        dtype=bool)

    conf = tests[ok & (tests["period"] == "confirm")
                 & tests["catalogue"].isin(["gk", "nn"])].copy()
    conf = conf.merge(fam[["catalogue", "indicator", "carried"]],
                      on=["catalogue", "indicator"], how="left")
    conf["carried"] = conf["carried"].fillna(False).astype(bool)
    conf["q_value"] = np.nan
    conf["confirmed"] = False
    if conf["carried"].any():
        sub = conf["carried"]
        conf.loc[sub, "q_value"] = adjust(conf.loc[sub, "p_value"], method)
        conf.loc[sub, "confirmed"] = (
            conf.loc[sub, "q_value"].to_numpy() < alpha) & np.array([
                in_direction(r, d) for r, d in
                zip(conf.loc[sub, "rate_ratio"], conf.loc[sub, "direction"])],
                dtype=bool)

    raw = tests[ok & (tests["catalogue"] == "raw")].copy()
    raw["q_value_descriptive"] = np.nan
    for period in PERIODS:
        sel = raw["period"] == period
        if sel.any():
            raw.loc[sel, "q_value_descriptive"] = adjust(raw.loc[sel, "p_value"],
                                                         method)
    return {"family": fam, "confirmation": conf, "raw": raw}


def spa_check(hyp, grid, frame, bins, seed) -> Dict:
    """Frozen exploration rates as daily forecasts, scored on confirmation."""
    from scipy.stats import poisson

    slices = period_slices(hyp, grid)
    ex, co = slices["explore"], slices["confirm"]
    per_day = int(round(pd.Timedelta(days=1) / (grid[1] - grid[0])))
    counts = np.bincount(bins, minlength=len(grid))
    ids = [s["id"] for s in hyp["indicators"]]
    n_ex = counts[ex].sum()
    base_rate = n_ex / (ex.stop - ex.start)
    n_days = (co.stop - co.start) // per_day
    stop = co.start + n_days * per_day
    daily = counts[co.start:stop].reshape(n_days, per_day).sum(axis=1)
    bench_mu = np.full(n_days, base_rate * per_day)
    losses = []
    for iid in ids:
        a = frame[iid].to_numpy()
        a_ex = a[ex]
        r_in = counts[ex][a_ex].sum() / max(a_ex.sum(), 1)
        r_out = counts[ex][~a_ex].sum() / max((~a_ex).sum(), 1)
        a_co = a[co.start:stop].reshape(n_days, per_day)
        mu = (a_co * r_in + (~a_co) * r_out).sum(axis=1)
        losses.append(-poisson.logpmf(daily, np.maximum(mu, 1e-12)))
    res = spa_test(-poisson.logpmf(daily, bench_mu), np.column_stack(losses),
                   np.random.default_rng([seed, 99]), n_boot=2000,
                   mean_block=30.0)
    return {
        "catalogue": "gk",
        "n_days": int(n_days),
        "statistic": res.statistic,
        "p_consistent": res.p_consistent,
        "p_lower": res.p_lower,
        "p_upper": res.p_upper,
        "best_indicator": ids[res.best_model],
        "mean_log_loss_gain_per_day": {
            k: float(v) for k, v in zip(ids, res.mean_loss_diff)},
    }


def molchan_summary(hyp, frame, bins, seed, tag) -> Dict:
    """Return Molchan points, the combined trajectory and its reference test."""
    greater = [s["id"] for s in hyp["indicators"] if s["direction"] == "greater"]
    n = len(bins)
    points = []
    for spec in hyp["indicators"]:
        tau, nu = molchan_point(frame[spec["id"]].to_numpy(), bins)
        points.append({"indicator": spec["id"], "tau": tau, "nu": nu,
                       "bound_nu": float(binomial_bound(n, tau)[0]),
                       "p_value": molchan_p_value(n, tau, nu)})
    score = frame[greater].to_numpy().sum(axis=1).astype(float)
    traj = molchan_trajectory(score, bins)
    ass = area_skill_score(traj["tau"], traj["nu"])
    ref = time_random_reference(score, n, np.random.default_rng([seed, 7, tag]),
                                n_sims=2000, observed_ass=ass)
    return {"n_events": int(n), "points": points,
            "combined": {"tau": traj["tau"].tolist(), "nu": traj["nu"].tolist(),
                         "area_skill_score": ass, "reference": ref}}


# -------------------------------------------------------------- figures
def make_figures(art, hyp, cat, info, masks, tests, fam, molchan, prov):
    """Write the paper figures with provenance footers."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    from vedic_astrology_core.stats.plots import HOUSE_STYLE, PALETTE, save_figure

    out = {}
    poly = fc.region_polygon(hyp["region"])
    with matplotlib.rc_context(HOUSE_STYLE):
        fig, ax = plt.subplots(figsize=(7.0, 3.6))
        ax.plot(poly[:, 0], poly[:, 1], color="0.2", lw=1.0, label="Region")
        ax.scatter(cat["longitude"], cat["latitude"], s=4, color="0.7",
                   label="All events (Mw >= Mc)")
        gk = cat[masks["gk"]]
        ax.scatter(gk["longitude"], gk["latitude"], s=6, color=PALETTE[0],
                   label="Gardner-Knopoff mainshocks")
        ax.set_xlabel("Longitude (deg E)")
        ax.set_ylabel("Latitude (deg N)")
        ax.set_aspect("equal")
        ax.legend(loc="upper right", fontsize=7)
        out["region"] = save_figure(fig, art / "fig_region.png", prov)
        plt.close(fig)

        mw = info["all_mw"]
        bw = float(hyp["magnitude"]["bin_width"])
        bins = np.round(np.arange(np.floor(mw.min() * 10) / 10, mw.max() + bw, bw), 2)
        hist, edges = np.histogram(mw, bins=bins)
        cum = hist[::-1].cumsum()[::-1]
        fig, ax = plt.subplots(figsize=(6.0, 3.4))
        ax.semilogy(edges[:-1], np.maximum(hist, 0.8), "o", ms=3,
                    color=PALETTE[0], label="Non-cumulative")
        ax.semilogy(edges[:-1], cum, "s", ms=3, color=PALETTE[1],
                    label="Cumulative")
        thr = info["completeness"]["threshold"]
        ax.axvline(thr, color="0.3", ls="--", lw=1)
        ax.text(thr + 0.05, cum.max() / 2, f"Mc used = {thr:.1f}", fontsize=8)
        ax.set_xlabel("Mw (homogenised)")
        ax.set_ylabel("Number of events")
        ax.legend()
        out["mc"] = save_figure(fig, art / "fig_mc.png", prov)
        plt.close(fig)

        fig, ax = plt.subplots(figsize=(6.5, 3.4))
        t = cat["time"].dt.tz_localize(None)
        for key, colour in (("raw", "0.55"), ("gk", PALETTE[0]),
                            ("nn", PALETTE[1])):
            m = masks[key]
            ax.step(t[m], np.arange(1, m.sum() + 1), where="post", color=colour,
                    label=f"{CATALOGUES[key]} (n = {int(m.sum())})")
        ax.set_xlabel("Year")
        ax.set_ylabel("Cumulative events")
        ax.legend(loc="upper left")
        out["declustering"] = save_figure(fig, art / "fig_declustering.png", prov)
        plt.close(fig)

        fig, ax = plt.subplots(figsize=(7.0, 4.6))
        labels = [s["label"] for s in hyp["indicators"]]
        ypos = np.arange(len(labels))
        for k, (key, colour, off) in enumerate((("gk", PALETTE[0], -0.15),
                                                ("nn", PALETTE[1], 0.15))):
            sub = fam[fam["catalogue"] == key].set_index("indicator")
            sub = sub.reindex([s["id"] for s in hyp["indicators"]])
            ax.errorbar(sub["rate_ratio"], ypos + off,
                        xerr=[sub["rate_ratio"] - sub["ci_low"],
                              sub["ci_high"] - sub["rate_ratio"]],
                        fmt="o", ms=3, color=colour, capsize=2, lw=1,
                        label=CATALOGUES[key])
        ax.axvline(1.0, color="0.3", lw=1)
        ax.set_xscale("log")
        ax.set_yticks(ypos)
        ax.set_yticklabels(labels, fontsize=7)
        ax.invert_yaxis()
        ax.set_xlabel("Rate ratio, exploration period (95% exact Poisson CI)")
        ax.legend(loc="upper left", bbox_to_anchor=(1.0, 1.0))
        out["rate_ratios"] = save_figure(fig, art / "fig_rate_ratios.png", prov)
        plt.close(fig)

        fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.6), sharey=True)
        for ax, key in zip(axes, ("gk", "nn")):
            mol = molchan[key]
            grid_tau = np.linspace(0.0, 1.0, 201)
            ax.plot(grid_tau, 1 - grid_tau, color="0.4", lw=1,
                    label="Time-random")
            ax.plot(grid_tau, binomial_bound(mol["n_events"], grid_tau), ":",
                    color="0.2", lw=1, label="95% bound")
            ax.plot(mol["combined"]["tau"], mol["combined"]["nu"], "-",
                    marker=".", ms=4, color=PALETTE[0], label="Combined score")
            taus = [p["tau"] for p in mol["points"]]
            nus = [p["nu"] for p in mol["points"]]
            ax.plot(taus, nus, "o", ms=3, color=PALETTE[1], label="Indicators")
            ax.set_title(f"{CATALOGUES[key]} (N = {mol['n_events']})")
            ax.set_xlabel("Fraction of time under alarm (tau)")
            ax.set_xlim(0, 1)
            ax.set_ylim(0, 1)
        axes[0].set_ylabel("Miss rate (nu)")
        axes[0].legend(loc="lower left", fontsize=7)
        out["molchan"] = save_figure(fig, art / "fig_molchan.png", prov)
        plt.close(fig)
    return {k: v.name for k, v in out.items()}


# ----------------------------------------------------------------- main
def _records(df: pd.DataFrame):
    return json.loads(df.to_json(orient="records", double_precision=10))


def run(seed: int, snapshot: Optional[Path], offline: bool,
        n_draws: Optional[int]) -> Dict:
    """Run the whole study and return the results dictionary."""
    hyp = fc.load_hypothesis()
    n_draws = int(n_draws or hyp["test"]["n_draws"])
    art = artifacts_dir("earthquake")
    cat, info = load_catalogue(snapshot, offline)
    cat = cat[(cat["time"] >= pd.Timestamp(hyp["catalogue"]["start"]))
              & (cat["time"] < pd.Timestamp(hyp["catalogue"]["end"]))]
    cat = cat.reset_index(drop=True)

    gk = decluster.gardner_knopoff(cat).to_numpy()
    nn_mask, nn_fit = decluster.nearest_neighbour(cat)
    masks = {"raw": np.ones(len(cat), dtype=bool), "gk": gk,
             "nn": nn_mask.to_numpy()}

    engine = EphemerisEngine(node_model=hyp["ephemeris"]["node_model"])
    grid = ind.time_grid(hyp["catalogue"]["start"], hyp["catalogue"]["end"],
                         hyp["time_grid"]["step_hours"])
    eph = ind.ephemeris_frame(grid, engine)
    frame = ind.build_indicators(hyp, eph)
    all_bins = ind.event_bins(cat["time"], grid)
    bins_by_cat = {k: np.sort(all_bins[m]) for k, m in masks.items()}

    tests = run_tests(hyp, grid, frame, bins_by_cat, seed, n_draws)
    tables = family_tables(hyp, tests)
    spa = spa_check(hyp, grid, frame, bins_by_cat["gk"], seed)
    molchan = {k: molchan_summary(hyp, frame, bins_by_cat[k], seed, t)
               for t, k in enumerate(("gk", "nn"))}
    greater = [s["id"] for s in hyp["indicators"] if s["direction"] == "greater"]
    counts = compare_nb_models(
        monthly_design(cat.loc[masks["gk"], "time"], frame, greater), greater)

    git = git_commit(REPO)
    prov = {"data_sha256": info["sha256"], "commit": git["commit"], "seed": seed}
    figures = make_figures(art, hyp, cat, info, masks, tests, tables["family"],
                           molchan, prov)

    summary_rows = []
    for key in ("raw", "gk", "nn"):
        sub = cat[masks[key]]
        summary_rows.append({
            "catalogue": key, "label": CATALOGUES[key], "n_events": int(len(sub)),
            "n_explore": int((sub["time"] < pd.Timestamp(
                hyp["split"]["confirm"][0], tz="UTC")).sum()),
            "n_confirm": int((sub["time"] >= pd.Timestamp(
                hyp["split"]["confirm"][0], tz="UTC")).sum()),
            "max_mw": float(sub["mw"].max()), "median_mw": float(sub["mw"].median()),
        })
    summary = pd.DataFrame(summary_rows)
    summary.to_csv(art / "catalogue_summary.csv", index=False)
    tests.to_csv(art / "rate_tests_all.csv", index=False)
    tables["family"].to_csv(art / "family_explore.csv", index=False)
    tables["confirmation"].to_csv(art / "confirmation.csv", index=False)
    tables["raw"].to_csv(art / "raw_descriptive.csv", index=False)

    fam = tables["family"]
    conf = tables["confirmation"]
    results = {
        "hypothesis_id": hyp["id"],
        "hypothesis_sha256": file_sha256(fc.HYPOTHESIS),
        "seed": seed,
        "n_draws": n_draws,
        "git": git,
        "ephemeris": engine.get_ephemeris_info(),
        "catalogue": {k: v for k, v in info.items() if k != "all_mw"},
        "declustering": {
            "summary": _records(summary),
            "nn_threshold_log10_eta": nn_fit["threshold"],
            "nn_mixture": {k: nn_fit[k] for k in ("means", "sds", "weights",
                                                  "separated")},
        },
        "grid": {"start": str(grid[0]), "end": str(grid[-1]),
                 "step_hours": hyp["time_grid"]["step_hours"],
                 "n_steps": int(len(grid))},
        "eclipses": {"solar": frame.attrs["n_solar_eclipses"],
                     "lunar": frame.attrs["n_lunar_eclipses"]},
        "indicator_time_fraction": {c: float(frame[c].mean()) for c in frame},
        "family": _records(fam),
        "confirmation": _records(conf),
        "raw_descriptive": _records(tables["raw"]),
        "spa": spa,
        "molchan": molchan,
        "count_model": counts,
        "figures": figures,
        "headline": {
            "family_size": int(len(fam)),
            "n_significant_explore": int(fam["significant"].sum()),
            "n_carried": int(fam["carried"].sum()),
            "n_confirmed": int(conf["confirmed"].sum()),
            "correction": hyp["test"]["correction"],
            "alpha": float(hyp["test"]["alpha"]),
        },
    }
    (art / "results.json").write_text(json.dumps(results, indent=1, default=str))
    write_manifest(
        art,
        inputs=[{"path": REPO / info["snapshot"], "row_count": info["n_polygon"],
                 "date_range": [info["first_event"], info["last_event"]]},
                {"path": fc.HYPOTHESIS}],
        seed=seed, engine=engine, repo_root=REPO,
        extra={"catalogue_source": info["source"], "n_draws": n_draws,
               "artifacts": sorted(p.name for p in art.iterdir()
                                   if p.name != "manifest.json")},
    )
    return results


def main(argv=None) -> int:
    """Command-line entry point."""
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--seed", type=int, default=None,
                    help="RNG seed (default: hypothesis.yaml test.seed)")
    ap.add_argument("--snapshot", type=Path, default=None)
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--n-draws", type=int, default=None)
    args = ap.parse_args(argv)
    seed = args.seed if args.seed is not None else int(
        fc.load_hypothesis()["test"]["seed"])
    res = run(seed, args.snapshot, args.offline, args.n_draws)
    h = res["headline"]
    print(f"source {res['catalogue']['source']}, snapshot "
          f"{res['catalogue']['snapshot']}")
    for row in res["declustering"]["summary"]:
        print(f"  {row['label']}: {row['n_events']} events")
    print(f"family {h['family_size']} tests, {h['n_significant_explore']} "
          f"significant in exploration, {h['n_carried']} carried, "
          f"{h['n_confirmed']} confirmed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
