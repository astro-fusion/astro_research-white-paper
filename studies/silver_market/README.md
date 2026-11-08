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
- `artifacts/`: `results.json`, `manifest.json`, tables and figures
  (`overlay_frame.csv` is regenerated, not committed: it holds the prices).

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

## Power

How large an effect could the explore period (the one the family is tested
on) have found? For each indicator and outcome the minimum detectable
difference at 80% power and two-sided alpha = 0.05 is
`(z_0.975 + z_0.8) x SE = 2.80 SE`, with the standard error read from the
95% interval the pipeline reports
(`vedic_astrology_core.stats.power.minimum_detectable_difference`). It is a
difference in next-day mean between active and inactive days. The base rate
of an extreme move is 5% (95th percentile), so a detectable +4 pp is close
to doubling it; the mean absolute daily move in the explore period is about 155 bp for
silver, so the detectable differences are 15 to 45 percent of a typical day.
Effects smaller than these are not excluded by the null result.

| Indicator | Active bars | Return (bp/day) | Absolute return (bp/day) | Extreme move (pp) |
|---|---|---|---|---|
| `mercury_retrograde` | 579 | 32.5 | 29.4 | 3.9 |
| `venus_retrograde` | 218 | 31.5 | 46.2 | 6.2 |
| `mars_retrograde` | 308 | 27.8 | 35.5 | 3.8 |
| `jupiter_retrograde` | 969 | 26.7 | 35.0 | 4.6 |
| `saturn_retrograde` | 1152 | 22.1 | 30.9 | 3.8 |
| `venus_combust` | 462 | 29.4 | 32.2 | 4.2 |
| `moon_exalted` | 281 | 38.0 | 24.2 | 4.1 |
| `moon_debilitated` | 256 | 36.5 | 26.0 | 4.6 |
| `venus_exalted` | 332 | 35.8 | 56.0 | 9.0 |
| `venus_debilitated` | 212 | 52.4 | 70.3 | 7.2 |
| `purnima` | 105 | 65.3 | 43.6 | 6.9 |
| `amavasya` | 114 | 69.7 | 46.7 | 7.2 |
| `venus_jupiter_conjunction` | 185 | 43.5 | 55.9 | 6.3 |
| `venus_own_sign` | 691 | 25.9 | 27.2 | 4.1 |

