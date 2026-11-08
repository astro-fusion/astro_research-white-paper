# Market fixtures

Real data, small, for offline tests and the offline fallback of the market
pipelines. Not inputs for any reported result unless a study's `results.json`
says `provisional: true`.

| File | Source | Rows | Notes |
|---|---|---|---|
| `fred_DEXUSUK_2019-12-20_2020-01-10.csv` | FRED `fredgraph.csv?id=DEXUSUK`, unmodified | 16 | Exercises the FRED parser (blank = missing day). The LBMA gold and silver ids were withdrawn from FRED in 2022. |
| `yahoo_gold_GCF_2015_2020.csv` | Yahoo Finance `GC=F` via `markets.fetch.yahoo`, 2015-01-02 to 2020-12-31 | 1480 | COMEX front-month continuous futures, not spot; zero-volume rows dropped. |
| `yahoo_silver_SIF_2015_2020.csv` | Yahoo Finance `SI=F` via `markets.fetch.yahoo`, same span | 1377 | As above, for silver. |
