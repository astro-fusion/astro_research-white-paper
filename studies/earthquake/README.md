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

## Controls, classifier and Bayes (amendment 2, 2026-11-08)

Added after the first run, outside the registered family (see the
`controls` and `secondary` blocks and the second amendment in
`hypothesis.yaml`; code in `scripts/robustness.py`):

- **Positive control, tidal phase** (Ide, Yabe and Tanaka 2016; Cochran,
  Vidale and Tanaka 2004): **not detected.** Best result: semidiurnal peak,
  nearest-neighbour, RR 1.06 (0.80-1.40), p = 0.35; all six tests q = 1. The
  smallest rate ratio the test could detect for the tidal indicators is
  1.40 to 1.50 on 1976-2026, larger than published tidal effects, so the study's nulls
  are uninformative about effects of tidal size.
- **Negative control** (registered indicators on a sky rotated by 3,001
  days): 0 of 26 nominal p < 0.05, 0 after BY.
- **Rule-free classifier** (ridge logistic, 83 daily sky features, 127 event
  days in 1976-2010): forward-chaining AUC 0.517 against a shifted-sky median
  of 0.490 (5-95% 0.458-0.524), p = 0.11; frozen 2011-2026 AUC 0.520 against
  0.481 (0.434-0.534), p = 0.13.
- **Bayes** (log RR priors N(0, 0.1^2) and N(0, 0.5^2), Savage-Dickey BF10):
  under the enthusiastic prior, 2 of 26 exploration tests have BF10 > 3
  (Varuna mandala, 3.6 and 3.7) and none BF10 < 1/3; under the sceptical
  prior every BF10 lies between 1/3 and 3. The catalogue cannot decide.

## Power

Minimum detectable rate ratio at 80% power, alpha = 0.05 (two-sided tests
use alpha / 2 per tail), simulated with Poisson event counts under the
circular-shift null (`vedic_astrology_core.stats.power`) at each test's
event count and time fraction. Residual clustering widens the real null, so
these are lower bounds. Generated into `artifacts/tbl_power.csv` and the
paper by `pipeline.py`.

| Indicator | Time active | GK explore | NN explore | GK 1976-2026 | NN 1976-2026 |
|---|---|---|---|---|---|
| Mars-Saturn conjunction | 5.0% | 2.25 | 2.19 | 2.04 | 1.95 |
| Mars-Ketu conjunction | 4.1% | 2.53 | 2.42 | 2.14 | 2.04 |
| Eclipse within 7 days | 13.8% | 1.76 | 1.72 | 1.64 | 1.58 |
| Sun sign ingress (sankranti) within 2 days | 13.3% | 1.78 | 1.73 | 1.64 | 1.57 |
| Mars station within 3 days | 1.5% | 3.50 | 3.34 | 2.96 | 2.80 |
| Mercury station within 3 days | 10.4% | 1.88 | 1.80 | 1.70 | 1.64 |
| Venus station within 3 days | 2.1% | 3.07 | 2.95 | 2.59 | 2.55 |
| Jupiter station within 3 days | 3.0% | 2.72 | 2.59 | 2.36 | 2.27 |
| Saturn station within 3 days | 3.2% | 2.68 | 2.54 | 2.28 | 2.20 |
| Moon in a Vayu-mandala nakshatra | 26.0% | 1.70 | 1.69 | 1.56 | 1.51 |
| Moon in an Agni-mandala nakshatra | 26.0% | 1.69 | 1.67 | 1.56 | 1.52 |
| Moon in an Indra-mandala nakshatra | 22.2% | 1.75 | 1.67 | 1.59 | 1.55 |
| Moon in a Varuna-mandala nakshatra | 25.9% | 1.71 | 1.67 | 1.55 | 1.52 |
| Semidiurnal tidal peak (Moon within 3 h of culmination) | 50.0% | 1.57 | 1.52 | 1.43 | 1.40 |
| Spring tide (within 45 deg of new or full Moon) | 49.4% | 1.56 | 1.52 | 1.45 | 1.42 |
| Spring tide and semidiurnal peak | 24.7% | 1.62 | 1.57 | 1.50 | 1.45 |

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
- `scripts/robustness.py`: controls, classifier, Bayes and power (amendment 2).
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
