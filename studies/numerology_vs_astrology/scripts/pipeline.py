#!/usr/bin/env python3
"""Run the pre-registered numerology-versus-astrology re-analysis.

Usage:
    python studies/numerology_vs_astrology/scripts/pipeline.py --seed 42

Reads ``hypothesis.yaml``, builds the daily frame (numerology planet, the nine
dignity scores and the Moon's nakshatra lord, sampled at the registered clock
time and zone), runs the equivalence tests and writes
``artifacts/results.json`` with its ``manifest.json``.
"""

import argparse
import hashlib
import json
import sys
from datetime import date, datetime, time, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd
import yaml

REPO = Path(__file__).resolve().parents[3]
for _p in (REPO, REPO / "libs", Path(__file__).resolve().parent):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from correlation_analysis import CorrelationAnalyzer  # noqa: E402
from generate_temporal_analysis import TemporalDataGenerator  # noqa: E402

from studies._paths import artifacts_dir, study_data_dir, study_dir  # noqa: E402
from vedic_astrology_core.stats.manifest import (  # noqa: E402
    git_commit,
    write_manifest,
)

STUDY = "numerology_vs_astrology"
HYPOTHESIS = study_dir(STUDY) / "hypothesis.yaml"
SIDEREAL_MONTH_DAYS = 27.321661


def load_hypothesis(path: Path = HYPOTHESIS) -> Dict[str, Any]:
    """Return the parsed pre-registration."""
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def changes(series: pd.Series) -> int:
    """Return how often a label differs from the previous day's label."""
    s = series.astype(str).to_numpy()
    return int((s[1:] != s[:-1]).sum())


def build_frame(hyp: Dict[str, Any]) -> pd.DataFrame:
    """Generate the daily frame for the registered period, zone and time."""
    hh, mm = (int(x) for x in hyp["sample_time"].split(":"))
    gen = TemporalDataGenerator(
        start_date=date.fromisoformat(hyp["period"]["start"]),
        end_date=date.fromisoformat(hyp["period"]["end"]),
        sample_time=time(hh, mm),
        tz=hyp["tz"],
    )
    frame = pd.DataFrame(gen.generate_data())
    frame.attrs["engine"] = gen.ephemeris.get_ephemeris_info()
    return frame


def describe(frame: pd.DataFrame) -> Dict[str, Any]:
    """Return the label distributions and change counts used by the paper."""
    years = len(frame) / 365.25
    num = frame["numerology_active_planet"].value_counts(normalize=True)
    lord = frame["astrology_moon_nakshatra_lord"].value_counts(normalize=True)
    labels = sorted(set(num.index) | set(lord.index))
    chance = float(sum(num.get(k, 0.0) * lord.get(k, 0.0) for k in labels))
    return {
        "n_days": int(len(frame)),
        "numerology_share": {k: float(num.get(k, 0.0)) for k in labels},
        "nakshatra_lord_share": {k: float(lord.get(k, 0.0)) for k in labels},
        "chance_agreement_from_margins": chance,
        "numerology_changes_per_year": changes(frame["numerology_active_planet"])
        / years,
        "nakshatra_lord_changes_per_year": changes(
            frame["astrology_moon_nakshatra_lord"]
        )
        / years,
        "mean_nakshatra_days": SIDEREAL_MONTH_DAYS / 27.0,
    }


def run(
    seed: int,
    out_dir: Optional[Path] = None,
    frame: Optional[pd.DataFrame] = None,
    data_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """Run the study and return the results dictionary.

    ``frame`` and ``data_dir`` let tests pass a short frame and a temporary
    directory; by default the registered period is generated and written to
    the study's data directory.
    """
    hyp = load_hypothesis()
    if frame is None:
        frame = build_frame(hyp)
    data_dir = Path(data_dir) if data_dir else study_data_dir(STUDY)
    data_dir.mkdir(parents=True, exist_ok=True)
    csv = data_dir / "temporal_analysis_5years.csv"
    frame.to_csv(csv, index=False)
    sha = hashlib.sha256(csv.read_bytes()).hexdigest()

    analyzer = CorrelationAnalyzer(str(csv))
    analyzer.load_data()
    analyzer.analyze_correlations()
    margins = {h["id"]: float(h["margin"]) for h in hyp["hypotheses"]}
    unc = hyp["uncertainty"]
    tests = analyzer.perform_hypothesis_tests(
        margin_r=margins["H2"],
        margin_kappa=margins["H1"],
        alpha=float(hyp["alpha"]),
        n_boot=int(unc["n_boot"]),
        mean_block=float(unc["mean_block_days"]),
        rng=np.random.default_rng(seed),
    )
    planets = tests["H2_planets"]
    k = tests["H1_kappa"]
    n_equiv = sum(1 for p in planets if p.get("equivalent"))
    n_tested = sum(1 for p in planets if "r" in p)
    engine = frame.attrs.get("engine") or {}
    results = {
        "study": STUDY,
        "hypothesis_id": hyp["id"],
        "hypothesis_sha256": hashlib.sha256(HYPOTHESIS.read_bytes()).hexdigest(),
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "seed": seed,
        "git": git_commit(REPO),
        "ephemeris": engine,
        "sampling": {
            "time": hyp["sample_time"],
            "tz": hyp["tz"],
            "start": hyp["period"]["start"],
            "end_exclusive": hyp["period"]["end"],
        },
        "data": {"file": csv.name, "sha256": sha, "rows": int(len(frame))},
        "description": describe(frame),
        "H1_kappa": k,
        "H2_planets": planets,
        "headline": {
            "h1_equivalent": bool(k.get("equivalent", False)),
            "kappa": k.get("kappa"),
            "h2_n_equivalent": n_equiv,
            "h2_n_tested": n_tested,
            "alpha": float(hyp["alpha"]),
        },
    }
    art = Path(out_dir) if out_dir else artifacts_dir(STUDY)
    art.mkdir(parents=True, exist_ok=True)
    (art / "results.json").write_text(json.dumps(results, indent=1, default=str))
    write_manifest(
        art,
        inputs=[
            {
                "path": csv,
                "row_count": int(len(frame)),
                "date_range": [str(frame["date"].iloc[0]), str(frame["date"].iloc[-1])],
            },
            {"path": HYPOTHESIS},
        ],
        seed=seed,
        engine=engine or None,
        repo_root=REPO,
        extra={"artifacts": ["results.json"]},
    )
    return results


def main(argv=None) -> int:
    """Command-line entry point."""
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument(
        "--seed",
        type=int,
        default=None,
        help="RNG seed (default: hypothesis.yaml seed)",
    )
    args = ap.parse_args(argv)
    seed = args.seed if args.seed is not None else int(load_hypothesis()["seed"])
    res = run(seed)
    h = res["headline"]
    print(
        f"H1 kappa {h['kappa']:.4f}, equivalent within margin: " f"{h['h1_equivalent']}"
    )
    print(f"H2 planets equivalent: {h['h2_n_equivalent']}/{h['h2_n_tested']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
