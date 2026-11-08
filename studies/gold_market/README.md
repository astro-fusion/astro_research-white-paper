# Gold market

**Question.** Do classical planetary configurations (Vedic and Western catalogue
entries) coincide with changes in XAU/USD returns more often than a
time-randomised baseline would predict?

**Status.** The statistical results in both manuscripts are withdrawn pending
re-analysis on verified data (see [CORRECTIONS.md](../../CORRECTIONS.md), items
b and c). The pipeline now refuses to run without its real input.

## Contents

- `paper/GOLD_MARKET_PLANETARY_CORRELATION_ANALYSIS.qmd` with `paper/sections/`: principles catalogue, algorithms, frequency and alignment graphs.
- `paper/manuscript.qmd`: the econometric manuscript (stationarity, Lomb-Scargle, Granger, Molchan, permutation tests); artifacts come from `scripts/generate_artifacts.py`.
- `scripts/`: `fetch_gold_data.py`, `generate_gold_astro_catalog.py`, `generate_gold_astro_features.py`, `compute_gold_astro_metrics.py`.

## How to run

```bash
pip install -e ".[dev]"
python studies/gold_market/scripts/fetch_gold_data.py          # writes studies/gold_market/data/gold_prices.csv
python studies/gold_market/scripts/generate_gold_astro_catalog.py
python studies/gold_market/scripts/generate_gold_astro_features.py
python studies/gold_market/scripts/compute_gold_astro_metrics.py
python scripts/generate_artifacts.py                            # reads data/processed/aligned_planetary_data.csv
quarto render studies/gold_market/paper/manuscript.qmd --to pdf
```

## Data

`data/` is gitignored. `gold_prices.csv` is fetched from Yahoo Finance (`XAUUSD=X`, falling back to `GC=F`)
by `fetch_gold_data.py`; the catalogue, feature and metric CSVs are generated.
`scripts/generate_artifacts.py` reads `data/processed/aligned_planetary_data.csv`
from the root data folder (see [data/README.md](../../data/README.md)).
