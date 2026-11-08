# Earthquake

**Question.** Does the rate of M5+ earthquakes, globally and in the
India-Nepal region, change while specific classical configurations hold
(Mars-Ketu and Mars-Saturn conjunctions, malefic clusters, eclipses, dasha
periods of national charts)?

**Status.** The regression, Monte Carlo and predicted-versus-actual results are
withdrawn pending re-analysis (see [CORRECTIONS.md](../../CORRECTIONS.md), items
a and c).

## Contents

- `paper/EARTHQUAKE_PREDICTION_INDIA_NEPAL_ANALYSIS.qmd` with `paper/sections/`: the classical-combination catalogue study for India and Nepal.
- `paper/rigor_audit.qmd`: the negative-binomial GLM audit of the USGS catalogue.
- `paper/drafts/`: superseded drafts kept for their unique text (`rigor_audit_modular/`, `research_earthquake_prediction.md`); not rendered.
- `scripts/`: USGS fetcher, declustering, feature generation, regression matrix, models, validation, rigor and figure scripts.
- `tables/`: `regression_coefficients.csv`, `earthquake_rigor_report.md`.
- `figures/`: figures referenced by the papers.

## How to run

```bash
pip install -e ".[dev]"
python studies/earthquake/scripts/earthquake_data_fetcher.py           # USGS catalogue into studies/earthquake/data/
python studies/earthquake/scripts/generate_daily_astro_features.py
python studies/earthquake/scripts/generate_combination_catalog.py
python studies/earthquake/scripts/compute_combination_metrics.py
python studies/earthquake/scripts/build_regression_matrix.py
python studies/earthquake/scripts/earthquake_rigor_analysis.py
```

## Data

`data/` is gitignored except `india_nepal_data.json` (the India-Nepal event
extract the paper reads). USGS catalogue snapshots (`usgs_*.json`) are fetched
by `earthquake_data_fetcher.py`; generated CSVs (`daily_astro_base.csv`,
`combination_catalog.csv`, `combination_metrics.csv`, dasha periods) come from
the scripts above.
