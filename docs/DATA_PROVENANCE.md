# Data Provenance and Reproducibility Governance

This document governs how empirical data and ephemeris files are sourced,
versioned, hashed and licensed. It describes only files and scripts that exist
in the repository.

## 1. Governing principles

1. **Source traceability.** Every dataset names its source URL and licence in
   `data/snapshot_index.json` and `data/registry/licences.yaml`.
2. **Immutability.** A snapshot is named by the first 12 hex digits of its
   SHA-256 (`<name>_<sha12>.<ext>`); new data make a new file, never an overwrite.
3. **Checksum verification.** `python scripts/check_data.py` (`make check-data`)
   recomputes the hash of every indexed file that is present and fails on a
   mismatch or on a file in `data/snapshots/` that the index does not list.
4. **Hash plus fetch script when unsure.** A file whose licence does not allow
   redistribution stays out of git; its hash and fetch script are published.

## 2. Snapshot index and licence register

- `data/snapshot_index.json`: file, SHA-256, rows, date range, source id,
  source URL, licence, `committable`, `committed`, `fetched_at`.
- `data/registry/licences.yaml`: per source, the terms URL, licence, decision
  (`commit` or `hash_only`), `verified` and `date_read`. The decisions follow
  PAPER_ROADMAP section 4.5 and have not yet been read and confirmed by a person.
- Code: `libs/vedic_astrology_core/datasets/snapshots.py`.

## 3. Datasets in the index

| Source id | Content | Fetched by | Decision |
|---|---|---|---|
| `yahoo_finance` | Gold `GC=F` and silver `SI=F`, COMEX front-month continuous futures, daily | `libs/vedic_astrology_core/markets/fetch.py` | hash only |
| `worldbank_pinksheet` | World Bank Pink Sheet, monthly | `scripts/fetch/worldbank_pinksheet.py` | commit |
| `usgs_comcat` | USGS ComCat earthquakes | `studies/earthquake/scripts/fetch_catalogue.py` | commit |
| `tracked_offline_fallback` | Tracked earthquake fallback, 2015-2023 | `studies/earthquake/data/india_nepal_data.json` | commit |
| `world_atlas` | Country outlines for site maps | `scripts/export_site_data.py` | commit |
| `cftc_cot`, `gfz_kp`, `fred_us_gov`, `fred_cboe` | Fetch scripts exist; no snapshot indexed yet | `scripts/fetch/` | see register |

**The gold source.** The gold and silver series now in the index are Yahoo
Finance continuous front-month COMEX futures (`GC=F`, `SI=F`). They are futures,
not spot, and they are not LBMA prices. FRED withdrew the LBMA series in 2022,
so `fred.py` refuses them. A verified LBMA route is planned (ADR-004 WP-12).
Yahoo data are not redistributed; the index holds their hashes.

## 4. Ephemeris

Planetary positions are computed with `pyswisseph` (Swiss Ephemeris, AGPL or
Swiss Ephemeris licence). The Moshier analytic ephemeris is used unless Swiss
Ephemeris `.se1` files are installed; each result records the
`ephemeris_model` actually used. Ephemeris files are not redistributed.

## 5. Reproduce a result

1. Install the package: `pip install -e .` (add the `fetch` extra for Yahoo).
2. Fetch the sources a study names, with the scripts above.
3. Run `python scripts/check_data.py --snapshots-only`; compare your hashes with
   the index. A hash-only source gives your copy a different hash if the vendor
   has revised its history; record the new hash instead of editing the index.

## 7. Planetary dataset 1600-2100 (2026-11-08)

**What it is.** `libs/vedic_astrology_core/datasets/planetary.py` writes daily
positions of the nine grahas, 1600-2100, 12:00 UTC, one Parquet file per year
under `data/datasets/planetary/` (not committed). Engine: pyswisseph,
`FLG_SWIEPH | FLG_SPEED | FLG_SIDEREAL`, Lahiri, mean node, Ketu = Rahu + 180,
whole-sign. Columns: `date`, `jd`, `body`, `longitude`, `latitude`, `speed`,
`retrograde`, `sign`, `sign_name`, `degree_in_sign`, `nakshatra`,
`nakshatra_name`, `pada`, `nakshatra_lord`. Each `<year>.manifest.json` holds the
engine `ephemeris_model`, ayanamsa, node model, generator version, git commit
and the file SHA-256.

**Regenerate and verify.**

    python scripts/generate_planetary_dataset.py --years 1600-2100
    python scripts/generate_planetary_dataset.py --check

**Where it lives.** Release assets of tag `dataset-v*` on
`astro-fusion/astro_research-white-paper` (workflow
`.github/workflows/dataset-release.yml`), zipped per century with
`DATASET_README.md`. Licence CC BY 4.0. Hashes are reproducible only with the
same Swiss Ephemeris build and `ephemeris_model`.

**The old repository.** `astro-fusion/Astrology_Planetary_Data` is archived.
Its CSVs (`planetary_positions_simplified`, `planetary_positions_complete`,
`house_lordships_complete`) contain house occupancy per day or hour for an
unsourced ascendant, not longitudes. The claimed sidereal basis could not be
confirmed: for 2000-01-01 the sign pattern of the first row fits a sidereal
Lahiri chart, but over all 366 days of 2000 neither a tropical nor a Lahiri
sidereal calculation (mean or true node, any 3-hourly sample time) explains
more than 56 days (15%) with a single ascendant, so the tables are not
reproducible. `house_lordships` depended on the same unsourced ascendant and is
not reproduced. The old raw CSV URLs stay online for existing notebooks, but
nothing here should cite them.
