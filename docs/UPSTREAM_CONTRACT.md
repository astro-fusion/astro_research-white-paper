# Upstream data contract

Some datasets in this repository are exported from a private upstream dataset
maintained by the project owner. The upstream is not part of this repository and
is not required to reproduce anything here.

This file describes the shape of the exported bundle in `studies/mundane/data/`,
the stamp that fingerprints it, and what this repository promises back. Decision
record: [ADR-002](adr/ADR-002-research-bridge.md).

## For AI agents

Do not add anything here, or anywhere in this repository, that describes the
upstream's internals. The upstream is not needed to reproduce anything: every
input is committed and hash-checked. If a bundle file must change, edit it and
re-stamp (see below).

## Bundle schema (bundle_version 1)

"Required" means the key is present in every row. Nullable fields hold an
explicit `null` rather than being omitted. Dates are `YYYY-MM-DD`, proleptic
Gregorian. Longitudes are east positive.

### `countries.yaml` (top-level key `countries`, 113 rows)

| Field | Type | Required | Notes |
|---|---|---|---|
| `iso` | string | yes | ISO 3166-1 alpha-2 |
| `slug` | string | yes | URL slug |
| `name` | string | yes | English name |
| `capital_lat` | float | yes | |
| `capital_lon` | float | yes | |
| `timezone` | string | yes | IANA zone |
| `founding` | mapping | yes | |
| `founding.date` | string | yes | founding or independence date |
| `founding.time` | string or null | yes | `HH:MM:SS` local; `null` in every row today |
| `founding.time_known` | bool | yes | `false` until a sourced time exists |
| `founding.rationale` | string | yes | one sentence |
| `candidate_charts` | list | yes | empty for most countries (65 entries across 29 countries) |

Each `candidate_charts` entry:

| Field | Type | Required | Notes |
|---|---|---|---|
| `event` | string | yes | |
| `date` | string | yes | |
| `time` | string or null | yes | |
| `time_zone` | string | yes | e.g. `LMT` |
| `place` | string | yes | |
| `lat` | float | yes | |
| `lon` | float | yes | |
| `used_by` | list of string | yes | |
| `source` | mapping | yes | |
| `source.url` | string | yes | |
| `source.title` | string | yes | |
| `source.checked` | bool | yes | |
| `confidence` | string | yes | label such as `disputed` |
| `notes` | string | yes | |

### `events.jsonl` (one JSON object per line, 825 rows)

| Field | Type | Required | Notes |
|---|---|---|---|
| `id` | string | yes | e.g. `wd:Q190517`; may repeat across countries |
| `title` | string | yes | |
| `date` | string | yes | |
| `event_type` | string | yes | source label, not reviewed |
| `event_type_reviewed` | bool | yes | `false` for now |
| `country_iso` | string or null | yes | |
| `region` | string or null | yes | |
| `lat` | number or null | yes | |
| `lon` | number or null | yes | |
| `source_url` | string or null | yes | |
| `metadata` | mapping | yes | |
| `metadata.qid` | string or null | yes | |
| `metadata.wikipediaUrl` | string or null | yes | |

Free-text descriptions are deliberately not part of the bundle.

### `eclipses.csv`

Not part of bundle version 1. No such file is committed; the stamp records
`eclipses: 0`. When it is added, this section gets its column list and the stamp
gets a hash for it.

## The stamp: `studies/mundane/data/UPSTREAM.yaml`

| Key | Meaning |
|---|---|
| `bundle_version` | integer, bumped when the schema above changes |
| `exported_at` | export date, `YYYY-MM-DD` |
| `row_counts` | `countries`, `events`, `eclipses` |
| `sha256` | hex digest per committed bundle file |
| `exporter_commit` | opaque upstream commit hash, or `null` |
| `licence` | `CC-BY-4.0` |
| `attribution` | `AstroFusion mundane dataset` |

`tests/test_upstream_stamp.py` fails if a hash or row count no longer matches,
and names the stale file. After a deliberate edit, recompute with
`shasum -a 256 countries.yaml events.jsonl` (run in the data folder) and update
`UPSTREAM.yaml` together with the row counts.

## Licence

The bundle is released under CC BY 4.0. Attribution: "AstroFusion mundane
dataset". Event rows carry facts and a link to the Wikipedia page, not its text.

## What this repository promises back

Rules in `rules/**` and candidate charts are the canonical open versions. The
upstream may consume them at a pinned commit of this repository.
