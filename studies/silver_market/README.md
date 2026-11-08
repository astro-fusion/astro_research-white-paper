# Silver market

**Question.** On days when a pre-registered sidereal (Lahiri) planetary
condition holds, is the next trading day's silver return, absolute return or
probability of an extreme move different from other days?

This study exists to show that the market pipeline has nothing gold-specific:
`scripts/pipeline.py` is a configuration of `vedic_astrology_core.markets.study`
and only `hypothesis.yaml` differs from the gold study (series, karakas Moon and
Venus, full and new Moon).

**Status.** New 2026-11-08. Outcome of the pre-registered run (seed 42):
**null**. None of the 42 explore-period tests passed the Benjamini-Yekutieli
correction, so nothing was carried to the confirm period. The paper states the
numbers.

## Contents

- `hypothesis.yaml`: the pre-registration.
- `scripts/pipeline.py`: the shared pipeline, configured.
- `paper/manuscript.qmd`: Results and Discussion generated from
  `artifacts/results.json`.
- `artifacts/`: `results.json`, `manifest.json`, tables, figures and
  `overlay_frame.csv`.

## How to run

```bash
pip install -e ".[dev,fetch]"
python studies/silver_market/scripts/pipeline.py --seed 42
quarto render studies/silver_market/paper/manuscript.qmd --to html
```

## Data

The LBMA silver price (`SLVPRUSD`) is no longer served by FRED, so the run uses
COMEX front-month continuous futures (Yahoo `SI=F`), labelled as futures.
Zero-volume rows are dropped. The snapshot is
`data/snapshots/silver_market_<sha256[:12]>.csv` (gitignored); its hash is in
`artifacts/results.json` and `artifacts/manifest.json`.
