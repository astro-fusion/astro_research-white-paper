# Gold market

**Question.** On days when a pre-registered sidereal (Lahiri) planetary
condition holds, is the next trading day's gold return, absolute return or
probability of an extreme move different from other days?

**Status.** Rebuilt 2026-11-08 on `vedic_astrology_core.markets` after the
earlier results were withdrawn (see [CORRECTIONS.md](../../CORRECTIONS.md)).
Outcome of the pre-registered run (seed 42): **null**. One of 42 explore-period
tests (Jupiter in Capricorn, absolute return) passed the Benjamini-Yekutieli
correction and did not replicate in the frozen 2016-2026 period; Hansen's SPA
finds no rule that beats being flat. The paper states the numbers.

## Contents

- `hypothesis.yaml`: the pre-registration (sources, 14 indicators, outcomes,
  null, correction, explore and confirm periods, SPA, event study, Granger).
- `scripts/pipeline.py`: a configuration of the shared pipeline
  `vedic_astrology_core.markets.study`; it holds no gold-specific logic.
- `paper/manuscript.qmd`: the paper; its Results and Discussion are generated
  from `artifacts/results.json`.
- `artifacts/`: committed outputs the paper reads: `results.json`,
  `manifest.json`, `tbl_*.csv` and `fig_*.png`. The pipeline also writes
  `overlay_frame.csv` (one row per trading day with every indicator, for the
  website explorer); it holds the price series and is not committed.

## How to run

```bash
pip install -e ".[dev,fetch]"
python studies/gold_market/scripts/pipeline.py --seed 42      # about 40 s
quarto render studies/gold_market/paper/manuscript.qmd --to html
```

`--offline` uses the fixture `tests/fixtures/markets/yahoo_gold_GCF_2015_2020.csv`
and marks every result `provisional: true`.

## Data

Sources are tried in the order of `hypothesis.yaml`. The LBMA PM fix
(`GOLDPMGBD228NLBM`) is no longer served by FRED (HTTP 404 since 2022), so the
run uses COMEX front-month continuous futures (Yahoo `GC=F`), which are labelled
as futures, never spot. Zero-volume rows (stale quotes) are dropped. The raw
download is written to `data/snapshots/gold_market_<sha256[:12]>.csv`
(gitignored); its SHA-256, row count and date range are in
`artifacts/results.json` and `artifacts/manifest.json`.
