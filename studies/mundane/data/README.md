# Mundane study data

Two tracked files, both seeded from the AstroFusion mundane dataset (export
date 2026-11-08). Dates, coordinates and titles are released under
CC BY 4.0, attribution "AstroFusion mundane dataset". Event descriptions were
deliberately left out: in the source they are Wikipedia text (CC BY-SA), so each
row keeps only the facts and a link back to the Wikipedia page.

## `countries.yaml` (113 countries)

| Field | Meaning |
|---|---|
| `iso`, `slug`, `name` | ISO 3166-1 alpha-2 code, URL slug, English name |
| `capital_lat`, `capital_lon`, `timezone` | Capital coordinates (east positive) and IANA zone |
| `founding.date` | Founding or independence date, `YYYY-MM-DD`, proleptic Gregorian |
| `founding.time` | Always `null` today. A sourced time goes here (`HH:MM:SS`, local) |
| `founding.time_known` | `false` until a time with a citation exists |
| `founding.rationale` | One sentence on why this date is used |
| `candidate_charts` | Empty list. Competing charts (other dates or times) with a source and a confidence label go here |

The source file held only `00:00:00` or `12:00:00` placeholders, never a
sourced time, so every `time` was set to `null` instead of carrying a fake
value. Two duplicated rows (Singapore, Uzbekistan) were collapsed.

## The limitation

With no sourced birth time there is no lagna and no houses. Only features that
do not depend on them can be tested: the sign a planet transits relative to the
signs of natal planets, eclipses, Sun ingresses and stations near the event.
Natal planet signs are computed at local noon (the Moon can move about 6
degrees either way, so Moon-based features carry a `time_known=false` flag on
every row). A sourced time unlocks house-based rules for that country.

## `events.jsonl` (825 rows)

One JSON object per line: `id`, `title`, `date`, `event_type`,
`event_type_reviewed` (always `false` for now), `country_iso`, `region`, `lat`,
`lon`, `source_url`, `metadata.qid`, `metadata.wikipediaUrl`.

- `country_iso` is the crawl group the event was filed under, not necessarily
  where it happened. A few events appear under two countries with the same `id`.
- 30 rows are hand-curated and have no URL or QID.
- `event_type` is the source's label and is known to be wrong in places; see
  [event_types.md](event_types.md) and fix it by editing that row.

## Validation

```bash
python studies/mundane/scripts/validate_data.py
```
