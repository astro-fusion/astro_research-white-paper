#!/usr/bin/env python3
"""Combination atlas: evaluate every declared candidate against one study.

Usage::

    python studies/combinations/scripts/pipeline.py --seed 42 [--study earthquake]

Steps, all fixed by ``grammar.yaml``:

1. Expand the grammar (``enumerate.py``) into candidates with ids.
2. Build the hourly sky (sign, nakshatra lord, moment lagna, dasha lords) on
   the study's grid, and its event series (earthquake: Gardner-Knopoff
   mainshocks of the earthquake study).
3. Exploration period: two-sided circular-shift rate test for every testable
   candidate, 2,000 shared offsets; Benjamini-Yekutieli across the family;
   single-step Romano-Wolf (max-|z|) adjusted p for the best candidate.
4. Confirmation period: only BY survivors, BY across them, same direction.
5. Hansen SPA on the confirmation period for the 20 best explore candidates.
6. Write ``artifacts/atlas.csv`` (every candidate), ``results.json`` and
   ``manifest.json``.
"""

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Dict

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
STUDY = HERE.parent
REPO = HERE.parents[2]
EQ_SCRIPTS = REPO / "studies" / "earthquake" / "scripts"
for p in (HERE, REPO, REPO / "libs"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))
if str(EQ_SCRIPTS) not in sys.path:
    sys.path.append(str(EQ_SCRIPTS))

import atlas  # noqa: E402
import enumerate as grammar_enum  # noqa: E402

from vedic_astrology_core.stats.manifest import (  # noqa: E402
    file_sha256,
    git_commit,
    write_manifest,
)
from vedic_astrology_core.stats.multiplicity import adjust  # noqa: E402
from vedic_astrology_core.stats.walk_forward import spa_test  # noqa: E402

ARTIFACTS = STUDY / "artifacts"
N_SPA = 20


def _load_earthquake_pipeline():
    """Import the earthquake pipeline under a name that does not clash."""
    spec = importlib.util.spec_from_file_location(
        "earthquake_pipeline", EQ_SCRIPTS / "pipeline.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def earthquake_inputs(study: Dict) -> Dict:
    """Grid, ephemeris, events and split of the earthquake study."""
    import decluster
    import fetch_catalogue as fc
    import indicators as ind

    from vedic_astrology_core.astrology.ephemeris import EphemerisEngine

    eqp = _load_earthquake_pipeline()
    hyp = fc.load_hypothesis()
    cat, info = eqp.load_catalogue(None, False)
    cat = cat[
        (cat["time"] >= pd.Timestamp(hyp["catalogue"]["start"]))
        & (cat["time"] < pd.Timestamp(hyp["catalogue"]["end"]))
    ]
    cat = cat.reset_index(drop=True)
    gk = decluster.gardner_knopoff(cat).to_numpy()
    engine = EphemerisEngine(node_model=hyp["ephemeris"]["node_model"])
    grid = ind.time_grid(
        hyp["catalogue"]["start"],
        hyp["catalogue"]["end"],
        hyp["time_grid"]["step_hours"],
    )
    eph = ind.ephemeris_frame(grid, engine)
    bins = np.sort(ind.event_bins(cat.loc[gk, "time"], grid))
    loc = study["reference_location"]
    lagna = atlas.lagna_signs(eph["jd"].to_numpy(), loc["lat"], loc["lon"])
    dasha = atlas.dasha_lords(grid, study["reference_chart"], engine)
    return {
        "grid": grid,
        "eph": eph,
        "events": bins,
        "slices": eqp.period_slices(hyp, grid),
        "sky": atlas.sky_state(eph, lagna, dasha),
        "catalogue": {k: v for k, v in info.items() if k != "all_mw"},
        "engine": engine.get_ephemeris_info(),
        "hyp_path": fc.HYPOTHESIS,
    }


def _period_events(events, sl):
    ev = events[(events >= sl.start) & (events < sl.stop)]
    return ev - sl.start


def spa_check(cands, sky, grammar, events, slices, top, seed) -> Dict:
    """Frozen exploration rates of the top candidates scored on confirmation."""
    from scipy.stats import poisson

    ex, co = slices["explore"], slices["confirm"]
    counts = np.bincount(events, minlength=sky["n"])
    per_day = 24
    n_days = (co.stop - co.start) // per_day
    stop = co.start + n_days * per_day
    daily = counts[co.start : stop].reshape(n_days, per_day).sum(axis=1)
    base = counts[ex].sum() / (ex.stop - ex.start)
    losses = []
    for cid in top:
        m = atlas.candidate_mask(cands[cid], sky, grammar)
        a_ex = m[ex]
        r_in = counts[ex][a_ex].sum() / max(a_ex.sum(), 1)
        r_out = counts[ex][~a_ex].sum() / max((~a_ex).sum(), 1)
        a_co = m[co.start : stop].reshape(n_days, per_day)
        mu = (a_co * r_in + (~a_co) * r_out).sum(axis=1)
        losses.append(-poisson.logpmf(daily, np.maximum(mu, 1e-12)))
    res = spa_test(
        -poisson.logpmf(daily, np.full(n_days, base * per_day)),
        np.column_stack(losses),
        np.random.default_rng([seed, 99]),
        n_boot=2000,
        mean_block=30.0,
    )
    return {
        "candidates": list(top),
        "n_days": int(n_days),
        "p_consistent": res.p_consistent,
        "p_lower": res.p_lower,
        "p_upper": res.p_upper,
        "best": top[res.best_model],
        "best_log_score_gain_per_day": float(res.mean_loss_diff[res.best_model]),
    }


def run(seed: int, study_id: str = "earthquake") -> Dict:
    """Evaluate the whole atlas for one study and write the artifacts."""
    grammar = grammar_enum.load_grammar()
    study = next(s for s in grammar["studies"] if s["id"] == study_id)
    if study_id != "earthquake":
        raise SystemExit(f"study {study_id!r} is declared but not implemented yet")
    t = grammar["test"]
    cands = {c["id"]: c for c in grammar_enum.expand(grammar, study_id)}
    data = earthquake_inputs(study)
    sky, slices, events = data["sky"], data["slices"], data["events"]
    min_shift = int(t["min_shift_days"]) * 24
    alpha = float(t["alpha"])
    cache: Dict = {}

    ex = slices["explore"]
    ev_ex = _period_events(events, ex)
    n_ex = ex.stop - ex.start
    masks = (
        (cid, atlas.candidate_mask(c, sky, grammar, cache)[ex])
        for cid, c in cands.items()
    )
    res = atlas.shift_family(
        masks,
        ev_ex,
        n_ex,
        min_shift,
        int(t["n_draws"]),
        np.random.default_rng([seed, 1]),
        float(t["min_expected"]),
    )
    res = res.rename(columns={c: f"explore_{c}" for c in res.columns if c != "id"})
    testable = res["explore_testable"].to_numpy(dtype=bool)
    res["explore_q_value"] = np.nan
    res.loc[testable, "explore_q_value"] = adjust(
        res.loc[testable, "explore_p_value"].to_numpy(), "by"
    )
    surv = testable & (res["explore_q_value"].fillna(1.0).to_numpy() < alpha)

    co = slices["confirm"]
    ev_co = _period_events(events, co)
    for col in (
        "confirm_rate_ratio",
        "confirm_ci_low",
        "confirm_ci_high",
        "confirm_p_value",
        "confirm_q_value",
    ):
        res[col] = np.nan
    res["confirmed"] = False
    if surv.any():
        ids = res.loc[surv, "id"].tolist()
        cmasks = (
            (cid, atlas.candidate_mask(cands[cid], sky, grammar, cache)[co])
            for cid in ids
        )
        cres = atlas.shift_family(
            cmasks,
            ev_co,
            co.stop - co.start,
            min_shift,
            int(t["n_draws"]),
            np.random.default_rng([seed, 2]),
            0.0,
        ).set_index("id")
        q = adjust(cres["p_value"].to_numpy(), "by")
        for (cid, r), qi in zip(cres.iterrows(), q):
            sel = res["id"] == cid
            res.loc[sel, "confirm_rate_ratio"] = r["rate_ratio"]
            res.loc[sel, "confirm_ci_low"] = r["ci_low"]
            res.loc[sel, "confirm_ci_high"] = r["ci_high"]
            res.loc[sel, "confirm_p_value"] = r["p_value"]
            res.loc[sel, "confirm_q_value"] = qi
            same = np.sign(np.log(r["rate_ratio"])) == np.sign(
                np.log(res.loc[sel, "explore_rate_ratio"].iloc[0])
            )
            res.loc[sel, "confirmed"] = bool(qi < alpha and same)

    status = np.where(
        ~testable,
        "untestable",
        np.where(
            ~surv,
            "not significant in explore",
            np.where(res["confirmed"], "confirmed", "survived explore, not confirmed"),
        ),
    )
    res["status"] = status
    meta = pd.DataFrame(
        [
            {k: c[k] for k in ("id", "template", "depth", "key", "definition")}
            for c in cands.values()
        ]
    )
    atlas_df = meta.merge(res, on="id", how="left")
    atlas_df.insert(0, "study", study_id)

    top = atlas_df[testable].sort_values("explore_p_value")["id"].head(N_SPA).tolist()
    spa = spa_check(cands, sky, grammar, events, slices, top, seed)
    best = atlas_df[testable].sort_values("explore_p_value").iloc[0]

    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    atlas_df.to_csv(ARTIFACTS / "atlas.csv", index=False, float_format="%.6g")
    by_t = (
        atlas_df.groupby("template")
        .agg(
            candidates=("id", "size"),
            testable=("explore_testable", "sum"),
            nominal=("explore_p_value", lambda p: int((p < alpha).sum())),
        )
        .reset_index()
    )
    git = git_commit(REPO)
    results = {
        "grammar_id": grammar["id"],
        "grammar_sha256": file_sha256(grammar_enum.GRAMMAR),
        "study": study_id,
        "seed": seed,
        "n_draws": int(t["n_draws"]),
        "git": git,
        "ephemeris": data["engine"],
        "catalogue": data["catalogue"],
        "events": {"explore": int(len(ev_ex)), "confirm": int(len(ev_co))},
        "counts": {
            "candidates": int(len(atlas_df)),
            "testable": int(testable.sum()),
            "explore_nominal_p_lt_alpha": int((res["explore_p_value"] < alpha).sum()),
            "expected_nominal_by_chance": float(alpha * testable.sum()),
            "survived_by": int(surv.sum()),
            "confirmed": int(res["confirmed"].sum()),
        },
        "by_template": json.loads(by_t.to_json(orient="records")),
        "best_explore": {
            "id": best["id"],
            "definition": best["definition"],
            "rate_ratio": float(best["explore_rate_ratio"]),
            "ci_low": float(best["explore_ci_low"]),
            "ci_high": float(best["explore_ci_high"]),
            "p_value": float(best["explore_p_value"]),
            "q_value": float(best["explore_q_value"]),
            "p_romano_wolf": float(best["explore_p_rw"]),
        },
        "spa": spa,
    }
    (ARTIFACTS / "results.json").write_text(json.dumps(results, indent=1, default=str))
    write_manifest(
        ARTIFACTS,
        inputs=[
            {"path": REPO / data["catalogue"]["snapshot"]},
            {"path": grammar_enum.GRAMMAR},
            {"path": data["hyp_path"]},
        ],
        seed=seed,
        engine=data["engine"],
        repo_root=REPO,
        extra={
            "n_draws": int(t["n_draws"]),
            "artifacts": ["atlas.csv", "results.json"],
        },
    )
    return results


def main(argv=None) -> int:
    """Command-line entry point."""
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--study", default="earthquake")
    args = ap.parse_args(argv)
    seed = (
        args.seed
        if args.seed is not None
        else int(grammar_enum.load_grammar()["test"]["seed"])
    )
    r = run(seed, args.study)
    c = r["counts"]
    print(
        f"{c['candidates']} candidates, {c['testable']} testable, "
        f"{c['explore_nominal_p_lt_alpha']} with explore p < 0.05 "
        f"({c['expected_nominal_by_chance']:.0f} expected by chance), "
        f"{c['survived_by']} survived BY, {c['confirmed']} confirmed"
    )
    b = r["best_explore"]
    print(
        f"best: {b['definition']} RR {b['rate_ratio']:.2f} p {b['p_value']:.4f} "
        f"Romano-Wolf p {b['p_romano_wolf']:.3f}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
