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

## Power

How large an effect could the explore period (the one the family is tested
on) have found? For each indicator and outcome the minimum detectable
difference at 80% power and two-sided alpha = 0.05 is
`(z_0.975 + z_0.8) x SE = 2.80 SE`, with the standard error read from the
95% interval the pipeline reports
(`vedic_astrology_core.stats.power.minimum_detectable_difference`). It is a
difference in next-day mean between active and inactive days. The base rate
of an extreme move is 5% (95th percentile), so a detectable +4 pp is close
to doubling it; the mean absolute daily move in the explore period is about 88 bp for
gold, so the detectable differences are 15 to 50 percent of a typical day.
Effects smaller than these are not excluded by the null result.

| Indicator | Active bars | Return (bp/day) | Absolute return (bp/day) | Extreme move (pp) |
|---|---|---|---|---|
| `mercury_retrograde` | 675 | 14.9 | 12.6 | 3.1 |
| `venus_retrograde` | 253 | 17.9 | 22.5 | 4.8 |
| `mars_retrograde` | 326 | 19.6 | 14.5 | 3.6 |
| `jupiter_retrograde` | 1016 | 12.6 | 16.2 | 3.8 |
| `saturn_retrograde` | 1279 | 11.2 | 16.3 | 3.0 |
| `venus_combust` | 500 | 17.1 | 18.3 | 5.2 |
| `jupiter_combust` | 263 | 23.3 | 23.1 | 5.7 |
| `sun_exalted` | 277 | 25.4 | 18.4 | 4.3 |
| `sun_debilitated` | 295 | 20.8 | 21.6 | 5.8 |
| `sun_own_sign` | 285 | 19.9 | 20.9 | 6.4 |
| `jupiter_exalted` | 465 | 14.0 | 16.7 | 3.9 |
| `jupiter_debilitated` | 198 | 30.2 | 45.0 | 3.1 |
| `venus_jupiter_conjunction` | 220 | 20.9 | 17.7 | 3.6 |
| `venus_own_sign` | 697 | 13.9 | 12.8 | 3.6 |

