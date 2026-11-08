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

## How to run

```bash
export PYTHONPATH=libs:src:.
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
