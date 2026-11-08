# Planetary positions 1600-2100 (sidereal, Lahiri)

Daily positions of the nine Vedic grahas, 1600-01-01 to 2100-12-31, one row per
body per day at 12:00 UTC. Version: `@TAG@` (repository commit `@COMMIT@`).

Replaces the archived repository `astro-fusion/Astrology_Planetary_Data`.
Regenerate it byte for byte (same Swiss Ephemeris build) with:

    pip install ".[dev,data]"
    python scripts/generate_planetary_dataset.py --years 1600-2100 \
        --out data/datasets/planetary --fmt parquet
    python scripts/generate_planetary_dataset.py --check --out data/datasets/planetary

## Files

| Asset | Content |
|---|---|
| `planetary_1600-1699.zip` ... `planetary_2000-2099.zip`, `planetary_2100.zip` | `<year>.parquet` plus `<year>.manifest.json` for each year |
| `manifests.zip` | Every manifest on its own |
| `SHA256SUMS` | sha256 of every asset |
| `DATASET_README.md` | This file |

## Schema (`<year>.parquet`)

| Column | Type | Meaning |
|---|---|---|
| `date` | string | Sample instant, ISO 8601, UTC |
| `jd` | float | Julian day (UT) |
| `body` | string | SUN, MOON, MARS, MERCURY, JUPITER, VENUS, SATURN, RAHU, KETU |
| `longitude` | float | Sidereal ecliptic longitude, degrees, 0 to 360 |
| `latitude` | float | Ecliptic latitude, degrees (Ketu is minus Rahu's) |
| `speed` | float | Longitude speed, degrees per day |
| `retrograde` | bool | `speed < 0` (the mean node is always retrograde) |
| `sign` | int | 0 (Aries) to 11 (Pisces), whole sign |
| `sign_name` | string | Sign name |
| `degree_in_sign` | float | Degrees into the sign, 0 to 30 |
| `nakshatra` | int | 1 (Ashwini) to 27 (Revati) |
| `nakshatra_name` | string | Nakshatra name |
| `pada` | int | 1 to 4 |
| `nakshatra_lord` | string | Vimshottari lord of the nakshatra |

Rows are ordered by date, then in the order above. 501 years, 1,646,883 rows.

## Engine

Swiss Ephemeris through `pyswisseph`, apparent geocentric positions with
`FLG_SWIEPH | FLG_SPEED | FLG_SIDEREAL`, Lahiri ayanamsa, mean lunar node,
Ketu = Rahu + 180 degrees. The manifest of each year records the ayanamsa,
node model, `ephemeris_model` ("swieph" with `.se1` files, "moshier" without;
the GitHub runner uses Moshier), Swiss Ephemeris version, generator version,
git commit and the sha256 of the data file. Moshier positions differ from the
file ephemeris by well under an arcsecond for the planets in this range, but
the sha256 is only reproducible with the same ephemeris model.

## Not included

`house_lordships_complete` of the old repository is not reproduced. It depended
on an ascendant that was never sourced. Use whole-sign signs here, or compute
charts for a stated place and time with `vedic_astrology_core`.

## Licence and citation

Creative Commons Attribution 4.0 International (CC BY 4.0). Swiss Ephemeris is
used under its own licence; this release contains computed values only, not the
ephemeris files.

> Ghimire, B. (2026). *Planetary positions 1600-2100, sidereal Lahiri*
> (dataset, version @TAG@). astro-fusion/astro_research-white-paper.
> https://github.com/astro-fusion/astro_research-white-paper
