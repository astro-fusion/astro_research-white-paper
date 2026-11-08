# Earthquake

**Question.** Does the rate of earthquakes in the Himalayan arc (74-96 E,
India, Nepal, Bhutan and the adjacent arc) differ while specific classical
configurations hold: Mars-Saturn and Mars-Ketu conjunctions, eclipse windows,
solar ingresses (sankranti), planetary stations, and the Moon's nakshatra
mandala (Brihat Samhita ch. 32)?

**Status.** Rebuilt on the rigor contract (ADR-001) and pre-registered in
[`hypothesis.yaml`](hypothesis.yaml). First run (USGS ComCat 1976-2026,
Mw >= 5.2, 297 events, 186 Gardner-Knopoff and 214 nearest-neighbour
mainshocks): none of the 26 exploration tests passed the Benjamini-Yekutieli
correction, so nothing was carried to the 2011-2026 confirmation period. The
paper reports every rate ratio with its interval. The previous version of the
study is withdrawn (see "What changed" below and
[CORRECTIONS.md](../../CORRECTIONS.md)).

## How to run

```bash
pip install -e ".[dev]"     # numpy, pandas, scipy, statsmodels, pyswisseph, PyYAML
python studies/earthquake/scripts/fetch_catalogue.py            # USGS snapshot (or --offline)
python studies/earthquake/scripts/decluster.py                  # counts before/after declustering
python studies/earthquake/scripts/pipeline.py --seed 42         # every table, figure, results.json
quarto render studies/earthquake/paper/EARTHQUAKE_PREDICTION_INDIA_NEPAL_ANALYSIS.qmd --to html
```

`pipeline.py` fetches the catalogue itself if no snapshot exists. It takes
about a minute: an hourly ephemeris grid for 1976-2026 and 10,000 circular
shifts per test. `--offline` uses the tracked
`data/india_nepal_data.json` (2015-2023, M4.5+ only), which is too short for
the 1976-2010 exploration period; the run records which source it used.

## Layout

- `hypothesis.yaml`: the pre-registration (region polygon, Mw rules, Mc rule,
  declustering, the 13 indicators, null, correction, split) and its
  amendments.
- `scripts/fetch_catalogue.py`: USGS FDSN query, polygon filter, Mw
  homogenisation, completeness; writes `data/snapshots/usgs_<sha12>.csv` and
  its manifest (gitignored; the hash is in every artifact manifest).
- `scripts/decluster.py`: Gardner-Knopoff and nearest-neighbour declustering.
- `scripts/indicators.py`: the hourly indicator grid from the sidereal engine.
- `scripts/count_models.py`: same-family NB2 count models, LR test and
  leave-one-year-out CV.
- `scripts/pipeline.py`: the whole study; writes into `artifacts/`.
- `artifacts/`: generated output. The files the paper reads are committed
  (`results.json`, `manifest.json`, the CSV tables and `fig_*.png`); the rest
  is gitignored.
- `paper/EARTHQUAKE_PREDICTION_INDIA_NEPAL_ANALYSIS.qmd`: the paper. Results
  and Discussion are generated from `artifacts/results.json` when it renders.
- `paper/rigor_audit.qmd`, `paper/sections/`, `paper/drafts/`, `figures/` and
  the remaining scripts (`earthquake_data_fetcher.py`,
  `generate_daily_astro_features.py`, `generate_combination_catalog.py`,
  `compute_combination_metrics.py`, `build_regression_matrix.py`,
  `earthquake_planetary_analysis.py`, `sea_analysis.py`,
  `generate_paper_figures.py`): the withdrawn analysis, kept for audit. They
  are not part of the current results.

## What changed from the withdrawn version

| Withdrawn | Now |
|---|---|
| Bounding box 21.8-35 N, 75.6-89.9 E (includes Tibet and Bangladesh); one track ran on the global M6+ file | Himalayan-arc polygon from the MFT trace (Bilham 2019), depth <= 70 km |
| Mixed magnitude types, no completeness estimate | Mw homogenisation (Scordilis 2006), Mc by maximum curvature per decade |
| No declustering (28% of events in the Gorkha sequence) | Gardner-Knopoff and nearest-neighbour, both reported |
| i.i.d. 2x2 chi-square per day, BH over 1,422 tests | rate ratios against a 10,000-draw circular-shift null, BY over a fixed 26-test family |
| No out-of-sample period | 1976-2010 exploration, 2011-2026 frozen confirmation, Hansen SPA |
| Molchan AUC from `np.interp` on a decreasing axis, no bounds | Molchan on the time axis with binomial bounds and a time-random reference |
| Poisson baseline vs NB with alpha = 1 by AIC; in-sample "predicted vs actual" | NB2 with estimated alpha in both models, LR test, leave-one-year-out CV |
| Figures drawn from simulated data; tropical positions; DE440 claim | figures only from `pipeline.py`, with provenance footers; sidereal positions; the ephemeris actually used is read from the run |
