# Mundane

**Question.** Do recorded national events (earthquakes, floods, war starts,
changes of government) cluster around the planetary configurations that
mundane astrologers name, when those configurations are read against a
country's founding chart? The comparison is made openly, with the data, rules
and code public, and the results are reported as found.

**Status.** Seeded. Data and the feature pipeline exist; no hypothesis test has
been run, and none will be until [hypothesis.yaml](hypothesis.yaml) leaves
`draft` and countries have sourced founding times.

## The limit that shapes the study

All 113 founding times in the source data were placeholders (midnight or noon),
so every country has `time_known: false` and no lagna or houses. Only
sign-level features are testable: where a transiting planet is relative to the
signs of the natal planets, eclipses, Sun ingresses and stations near the event
date. Natal planets are computed at local noon and every feature row carries
the `time_known` flag. See [data/README.md](data/README.md).

## Contents

- `data/countries.yaml`: 113 countries, founding date, `time: null`, empty `candidate_charts` list.
- `data/events.jsonl`: 825 events (no descriptions), each with `event_type_reviewed: false`; `data/event_types.md` lists counts and known misclassifications.
- `hypothesis.yaml`: pre-registration template (draft).
- `scripts/validate_data.py`, `scripts/fetch_catalogues.py` (USGS works; DFO needs `--url` or `--local`; EM-DAT is a licence-explaining stub), `scripts/features.py`, `scripts/pipeline.py`.
- `sources/README.md`: open research questions for practitioners' methods and the folder convention for results.
- `artifacts/` (gitignored): `features.csv` or `features.parquet`, `summary.json`.

## First slice (ADR-006): India, Himalayan earthquakes, Mw 6 and above

**Descriptive only.** The slice has 3 declustered (Gardner-Knopoff) Himalayan
mainshocks in India in the explore period (1976 to 2010); two more (2011,
2021) lie in the closed confirm period and get case files only. The floor for
any p-value is 30 events, so the report prints no test statistic. Chart grades
used: primary `in-1947-midnight` is grade C (half-window 60 minutes); the
secondary India charts `in-1947-kn-rao`, `in-1947-noon`, `in-1950-republic`
are also grade C; the case-file-only Nepal chart `np-2008-republic` (Gorkha
2015) is grade D. At grade C the lagna-based and pratyantar factors are
unstable and are reported as such.

```bash
python -m vedic_astrology_core.mundane.cli validate
python -m vedic_astrology_core.mundane.cli burden
python -m vedic_astrology_core.mundane.cli casefile usgs:usp0004y1r --chart all --format json,html
python studies/mundane/scripts/run_slice.py     # about 10 minutes; writes studies/mundane/artifacts/
```

The console command `astro-mundane` is the same CLI; ADR-004 WP-18 adds the
entry point to `pyproject.toml`. `report --period confirm` exits with "not
available until WP-63".

Outputs of the slice (under `artifacts/`, which is gitignored except
`results.json`, `manifest.json`, `tbl_*.csv` and `fig_*.png`): `results.json`
(provisional while the tree is dirty), `factor_table.csv`, `burden.json`,
`controls_<plan_sha12>.csv` with manifest, `cases/<event>__<chart>.json|html`,
`secondary/<chart>_results.json`.

## How to run (seeded data pipeline)

```bash
pip install -e ".[dev]"   # once; no PYTHONPATH needed
python studies/mundane/scripts/validate_data.py
python studies/mundane/scripts/pipeline.py --seed 42 --limit 50   # drop --limit for all events
python studies/mundane/scripts/fetch_catalogues.py usgs           # snapshot into data/snapshots/
pytest tests/test_mundane_*.py
```

## What an astrologer can contribute

1. **A sourced founding time** for a country, with a citation, in
   `candidate_charts` of `data/countries.yaml` (competing charts are welcome;
   each is tested separately and all are reported).
2. **A corrected event type**: edit the row in `data/events.jsonl` and set
   `event_type_reviewed: true`.
3. **A new rule**: follow
   [CONTRIBUTING_ASTROLOGERS.md](../../CONTRIBUTING_ASTROLOGERS.md).

## Licence and provenance

Dates, coordinates and titles come from the AstroFusion mundane dataset (export
2026-11-08), CC BY 4.0; event titles and URLs point to Wikipedia and Wikidata
(facts, CC0). The event descriptions in the source are Wikipedia text under
CC BY-SA and were left out on purpose.

## Power

Not computed yet. The minimum detectable rate ratio
(`vedic_astrology_core.stats.power.minimum_detectable_rate_ratio`) needs the
number of events per country and the time fraction of each indicator, and
the indicators that matter here (houses and lagna of a founding chart) need
founding times. Until countries have sourced founding times, the only
testable features are sign-level transits, and a power table for those would
describe a study nobody has registered. The table will be added when
`hypothesis.yaml` leaves `draft`.
