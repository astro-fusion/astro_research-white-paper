# ADR-001: One flagship research repository

Status: accepted 2026-11-08; packages WP-0..WP-2, WP-4..WP-8 and WP-M delivered; WP-3 open (see Outcome). Owner: astro-fusion. Applies to `astro_research-white-paper`.

## Decision

1. `astro_research-white-paper` becomes the single public research project. `Astrology_Planetary_Data` is archived (not deleted, so its raw-URL Colab links keep working) and its only unique value, the 1600 to 2100 planetary dataset, is reproduced here by a generator script and published as a Release asset in Parquet. No CSV dumps are committed.
2. The repository serves four communities with one codebase and clearly separated entry points:
   - Astrologers: edit YAML rules under `rules/`, never Python. A validator and reference-chart tests tell them whether a rule is well-formed and whether it fires on the charts they expect.
   - Statisticians and skeptics: every study has a pre-registered hypothesis file, a stationarity gate, multiple-comparison correction, out-of-sample evaluation and a fixed seed. Claims in papers are generated from the same pipeline that produces the figures.
   - Astronomers: the ephemeris layer is validated against JPL Horizons and Swiss Ephemeris reference values in CI, with the ayanamsa and node model stated explicitly in every output.
   - Economists and market analysts: a generic overlay module aligns any price series (gold, silver, any ticker) with any astrological indicator and produces the same standard plots and tests.
3. Rendered output (HTML, PDF, TeX, `_book`, `site_libs`, `_freeze`) is never tracked. CI renders to GitHub Pages and Releases.
4. One Python package. The two competing engines (`libs/vedic_astrology_core/astrology` and the `celestial` package under `src/`) are consolidated after the review identifies which is correct per function.

## Target layout

```
astro_research-white-paper/
├── README.md                      scope, 3 quick starts (astrologer / scientist / developer)
├── CONTRIBUTING.md                developers
├── CONTRIBUTING_ASTROLOGERS.md    how to propose a rule without writing code
├── rules/                         YAML catalogs astrologers edit
│   ├── schema.json                JSON Schema for a rule file
│   ├── financial/                 e.g. gold_yogas.yaml, silver_yogas.yaml
│   ├── seismic/
│   └── general/                   classical yogas (BPHS, Phaladeepika, Saravali) with citations
├── vedic_research/                the single Python package (replaces libs/ and src/)
│   ├── ephemeris/                 positions, ayanamsa, nodes, houses, divisional charts
│   ├── dasha/
│   ├── dignity/
│   ├── rules/                     engine, loader, validator, explain()
│   ├── numerology/
│   ├── stats/                     stationarity, granger, permutation, bh_fdr, block_bootstrap, walk_forward, molchan
│   ├── markets/                   fetchers (gold, silver, generic ticker), alignment, overlay plots
│   ├── datasets/                  planetary dataset generator (1600 to 2100, Parquet)
│   └── viz/
├── studies/                       one folder per study (was research/use_cases)
│   ├── gold_market/               README, hypothesis.yaml, pipeline.py, paper.qmd, sections/
│   ├── silver_market/             new, built on markets/ to prove the overlay is generic
│   ├── earthquake/
│   └── numerology_vs_astrology/
├── papers/                        qmd/md sources only
├── notebooks/                     Colab-ready, incl. the two migrated from Astrology_Planetary_Data
├── tests/                         unit, reference charts, rule fixtures, stats property tests
├── scripts/                       CLI: generate-dataset, validate-rules, run-study, render
├── ops/                           Makefile, Docker, conda, CI config
└── docs/                          methodology, provenance, ADRs, no rendered output
```

## Astrologer contribution model

A rule is a YAML document with no code:

```yaml
id: gold.jupiter_kendra_from_moon
name: Jupiter in kendra from Moon (Gaja Kesari variant)
domain: financial
claim: Bullish for gold during the window
source: {text: BPHS, chapter: 36, verse: 12}
author: "@astrologer-handle"
conditions:
  all:
    - planet: Jupiter
      in_kendra_from: Moon
    - planet: Jupiter
      not: combust
    - planet: Jupiter
      dignity_in: [own, exaltation]
window: {unit: days, before: 0, after: 30}
expected_effect: {series: gold_usd, direction: up}
examples:
  fires_on:   ["2024-05-03T06:00:00Z"]
  silent_on:  ["2023-01-15T06:00:00Z"]
```

Mechanics:
- `scripts/validate-rules` checks the schema, resolves every predicate against the engine's vocabulary, and runs `examples` against the ephemeris. A rule with a failing example does not merge.
- `vedic_research.rules.explain(rule, moment)` prints, in plain words, which conditions held and which did not, so an astrologer can debug without Python.
- An issue template "Propose a rule" collects the same fields for people who will not open a pull request; a maintainer converts it.
- Every rule carries a classical citation. Rules without a source are accepted under `rules/experimental/` and are excluded from papers.
- The rule vocabulary (predicates such as `in_kendra_from`, `aspected_by`, `in_nakshatra`, `dasha_lord_is`, `retrograde`, `combust`, `dignity_in`, `in_sign`, `in_house_from`) is documented in `CONTRIBUTING_ASTROLOGERS.md` with one example each. New predicates are added in Python by developers with tests.

## Scientific rigor contract (applies to every study)

- `hypothesis.yaml` is written before the pipeline runs and states series, indicator, window, direction, test, alpha, and correction method.
- Stationarity gate (ADF and KPSS) before any Granger test; difference or detrend when it fails.
- Multiple comparisons corrected across all rules and planets with Benjamini-Hochberg; the paper reports q-values.
- Permutation and block-bootstrap nulls preserve autocorrelation (circular block or phase randomization).
- Walk-forward evaluation with a frozen out-of-sample period; no parameter chosen after seeing OOS.
- Molchan diagrams report alarm fraction against a time-random baseline with confidence bands.
- Every figure and number in a paper is produced by `pipeline.py` with a fixed seed and a recorded data hash.

## Market overlay module (`vedic_research.markets`)

- `fetch(series_id, start, end)` with adapters for gold and silver (LBMA or FRED), generic Yahoo ticker, and cached Parquet.
- `align(prices, indicator_frame, freq="D")` joins on UTC dates, forward-fills holidays, and returns a tidy frame.
- `overlay_plot(prices, events, rule_id)` produces a standard figure: price (log scale), event markers, shaded windows, and a lower panel with forward returns.
- `event_study(prices, events, horizons=[5, 21, 63])` returns average abnormal returns with bootstrap bands.
- The gold study is rewritten on top of this module; the silver study is added as the proof that nothing is gold-specific.

## Public website (GitHub Pages, no new framework)

The repo is already a Quarto website project deployed by GitHub Actions to `astro-fusion.github.io/astro_research-white-paper`. Quarto is the simplest honest choice for a research site: plain Markdown plus live figures, math, citations and downloadable PDFs, all static HTML on Pages at zero cost. What is wrong today is the content structure, not the tool. Target navigation:

| Page | Audience | Content, generated where possible |
|---|---|---|
| Home | layperson | the one-paragraph question, the "deterministic sky, random events" explainer (below), what we have found so far, what was withdrawn and why |
| How prediction can and cannot work | layperson, skeptic | the hazard-rate framing with one animated figure: smooth planetary curves above, spiky event series below, and the only testable overlap, a change in event *rate* during a configuration |
| Principles used | astrologer | table auto-generated from `rules/**.yaml`: rule id, plain-language condition, classical source and verse, which study uses it, whether it has passed reference-chart tests |
| Data | scientist | every dataset with source, licence, SHA-256, row count, date range, download link; the planetary dataset 1600 to 2100 as Parquet |
| Studies | all | one page per study: hypothesis as pre-registered, pipeline status, figures with provenance footers, effect sizes with CIs, and the honest result even when null |
| Mundane atlas | all | national charts with cited founding times, event catalogues (USGS earthquakes, Dartmouth Flood Observatory floods, later cyclones and droughts), transit-to-natal features, hazard-modulation tests per country |
| Contribute | astrologer, developer | propose a rule without code; add a predicate with code; verify in JHora checklist |
| Corrections | all | `CORRECTIONS.md` rendered as a page |

### Two render targets from one pipeline

| | Paper (PDF, static) | Website (HTML, interactive) |
|---|---|---|
| Purpose | journal-grade, citable, frozen | explore, filter, compare, enjoy |
| Figures | matplotlib via `vedic_research.viz.paper`, one house style, greyscale-safe, vector PDF | Observable JS (Plot, D3) and Plotly in Quarto `{ojs}` cells reading the same artifacts |
| Interaction | none | filters (country, date range, planet, rule, magnitude), chart-type toggles (line / bar / heatmap / polar wheel), hover provenance, linked brushing between the sky panel and the event panel |
| Data | artifacts frozen at render with hash in the footer | same artifacts as JSON/CSV/Parquet under `site/data/`, loaded client-side (Arquero for filtering, DuckDB-WASM only if a dataset exceeds a few MB) |
| Look | plain, professional | custom Quarto SCSS theme built from the `af-design` token CSS (dark-first, glass surfaces, planet colour scale), custom components: zodiac wheel, dasha timeline, transit-vs-natal overlay, hazard-rate gauge |
| Hosting | Release asset | GitHub Pages, static, no server |

Rules: every interactive explorer has a static twin in the paper produced from the same artifact file, so nothing on the site exists that the paper cannot cite. Chart colour and form follow the `dataviz` skill (one palette, accessible in light and dark). Custom components live in `site/components/*.ojs` and `site/assets/*.js`, tested with a Playwright smoke that loads each page and asserts the explorer renders with its default filter. Observable JS runs entirely in the browser, so the site stays a pure static Pages deploy.

Every figure, static or interactive, carries a footer with data hash, commit and seed. Nothing on the site is hand-drawn.

## Vision statement (what leads every page, and the order of the home page)

The project exists to **compare and contrast** real-world dates and data with Vedic astrological principles, openly and reproducibly, and to make that comparison easy for astrologers to extend. The home page opens with that, in this order:

1. The vision: an open, astrologer-extensible laboratory for testing classical principles against recorded events (earthquakes, floods, markets, national events).
2. How to read a comparison here: what a rule is, what a study is, what a result looks like, and that results are reported as found, positive, null or mixed.
3. The principles in use, with their classical sources, and the invitation to add more.
4. The studies and their current status.

Results are outcomes, not the mission. Whatever a corrected pipeline shows is published as the result of that study. No page opens with a verdict about what astrology can or cannot do.

### Working expectations (Methods page, not the home page)

The owner's current expectation, recorded as a hypothesis to be tested rather than a premise: planetary motion is smooth and deterministic in every ayanamsa and every divisional chart, while earthquakes, floods and prices are bursty and partly random, so if a relationship exists it is more likely to appear as a change in the *rate* or *conditions* of events during a configuration than as a point prediction. This is one expectation among others that astrologers may hold (for example, that specific transits to a national chart coincide with specific event types). The methods are chosen so that any of these can be tested on equal footing: event-rate ratios with confidence intervals, Molchan diagrams against a time-random baseline, declustered catalogues, multiplicity correction across every rule tested, and effect sizes reported whether or not they reach significance. The Methods page states the expectation, says whose it is, and lets the studies answer it.

## Mundane track (new, open counterpart to the proprietary AstroFusion mundane app)

- `studies/mundane/` with `countries/<iso>.yaml` (founding chart: date, time, place, source citation, confidence), event catalogues under `data/snapshots/` (USGS, Dartmouth Flood Observatory; EM-DAT only if its licence allows redistribution, otherwise fetch-on-demand with a hash), and a `pipeline.py` that computes transit-to-natal features from the rules registry and runs the hazard-modulation tests.
- The proprietary app stays private. This repo publishes the method, the open data, the rules, and reproducible results; it never imports from the app.
- Floods first after earthquakes: the DFO archive is open and well structured, and floods test the method on a seasonal process where the monsoon is the obvious confound that the null model must absorb.

## Work packages

| WP | Scope | Model | Depends on |
|---|---|---|---|
| WP-1 | Remove plasma track; fix broken Quarto include | Sonnet | none (running) |
| WP-0 | Read-only deep review (algorithms, stats, rules engine, quality) | Opus | none (running) |
| WP-2 | Untrack rendered output, add ignores, CI renders Pages and Releases; move `research/use_cases` to `studies/`, `use_cases/` legacy content merged or removed | Sonnet | WP-1 |
| WP-3 | Dataset generator and Parquet release; migrate the two notebooks and geocoding; archive banner on the old repo; `atlas/github` page update in the web app | Sonnet | WP-1 |
| WP-4 | Rules engine v2: schema, validator CLI, `explain()`, examples-as-tests, `CONTRIBUTING_ASTROLOGERS.md`, issue template, migrate existing YAML catalogs | Opus | WP-0 |
| WP-5 | `stats/` module with the rigor contract, applied to the gold and earthquake studies; hypothesis files; papers regenerated | Opus | WP-0 |
| WP-6 | `markets/` overlay module, gold study rewritten on it, silver study added | Opus | WP-5 |
| WP-7 | Package consolidation (`libs/` + `src/` into `vedic_research`), ephemeris validation against JPL Horizons in CI | Opus | WP-0, WP-2 |
| WP-8 | README rewrite with three quick starts; methodology docs refreshed | Sonnet | WP-4..7 |

Gates for every package: flake8 0, pytest green, no new tracked rendered output, no secrets, commit on `main` with explicit paths, push.

## Out of scope for now

Flask `application/` layer and the REST API. They stay untouched until the package consolidation is done; they are not on the reviewer-facing path.

## Outcome (2026-11-08)

Delivered on `main`, by package (commit ranges inclusive, oldest first):

| Package | Delivered | Commits |
|---|---|---|
| WP-1 | Plasma-physics track removed | `23cad93` |
| WP-0 | Deep review; its integrity findings fixed: simulated figures withdrawn and `CORRECTIONS.md`, sidereal positions and one node model, houses, Vimshottari dasha, BPHS vargas, dignity, rule keys; single dependency source and lockfile | `d69c651`..`ca8f9fb`, `f364283`, `6df9321`..`da5f39c` |
| WP-2 | Rendered output untracked; one copy of each study under `studies/`, `studies/_paths.py`, Quarto website from `site/`, ADR-001 | `20ffde4`, `6d87830`..`4740abb` |
| WP-M | Mundane study seeded: countries and events with validator, transit-to-natal features, pipeline and draft pre-registration, site page | `dbfb76f`..`c31ba43` |
| WP-4 | Rules engine v2: schema, predicates, loader, `explain()`, `astro-rules` CLI, migration of the catalog and 67 mundane drafts, `CONTRIBUTING_ASTROLOGERS.md` | `c362c7e`..`eed142d`, `4f55153`..`b272929`, `c7b1e46` |
| WP-5 | `vedic_astrology_core.stats` rigor-contract module; earthquake pre-registration, catalogue snapshot, declustering, one-command pipeline and paper from `results.json` | `085bc52`, `a078cb4`, `298512e`, `12cb679`, `51b2fa9`, `8dbfa59`, `a6b11d7`, `129e69a` |
| WP-6 | `vedic_astrology_core.markets` overlay and study pipeline; gold rebuilt and silver added on it, seed-42 results | `fa2f92f`, `2af434e`..`9332c25` |
| WP-7 | One engine: the `celestial` package under `src/` retired (its geometric aspects ported to `astrology/aspects.py`, everything else already had a corrected equivalent), `src/` removed; package installable without `PYTHONPATH` (`libs/` holds `vedic_astrology_core` and `vedic_numerology`, the LLM diagram tool moved to `tools/visuals`), `application/` on the installed package; JPL Horizons cross-check in CI; smoke-only tests, the `GlobalShadbalaScorer` alias and the invented Nepal constitution time removed; CI quality and earthquake jobs repaired | `3df4328`, `1397f74`..`fd9f46f` and this ADR update |
| WP-8 | Consolidation: immutable ephemeris model, pydantic and Python 3.9 in packaging, migration scripts kept, ignores for committed artifacts, mundane on `_paths`, caption and deploy home page, README with three quick starts and results, numerology re-analysis with TOST and Cohen's kappa | `9d77cea`..`f6016cf` and this ADR update |

Not delivered: WP-3 (dataset generator and Parquet release, notebook and
geocoding migration, archive banner on the old repository). It remains open.

WP-7 notes:

- Package name kept. The import root stays `vedic_astrology_core` rather
  than the `vedic_research` of the target layout: renaming it touches more
  than 100 files and every notebook and paper that imports it, and is a
  separate decision from collapsing the two engines.
- JPL Horizons cross-check (`tests/test_horizons_crosscheck.py`, fixtures
  fetched 2026-11-08 from DE441, quantity 31, geocentric apparent ecliptic
  longitude of date at six UT instants 1950-2040). Maximum deviation of the
  engine (Moshier, no `.se1` files) per body: Sun 0.10, Moon 1.94, Mars 0.12,
  Jupiter 0.31, Saturn 0.20 arcseconds; tolerance 10 arcseconds for Moshier
  and 1 for `swieph`.
- Behaviour changes: the Western essential-dignity scheme and the
  finite-difference retrograde detector of the retired engine were not
  ported (nothing used them; papers 04 and 06 now point at the speed flag and
  the Vedic scorer). The Nepal 2015 reference chart has no time
  (`datetime=None`, `time_known=False`). The Sphinx docs job no longer
  deploys to Pages, and the release job runs only on `v*` tags.

Current results (pre-registered runs, seed 42, from each study's
`artifacts/results.json`):

| Study | Outcome |
|---|---|
| Gold market | Null: 1 of 42 exploration tests significant after Benjamini-Yekutieli, not confirmed in 2016-2026; SPA p = 0.53 |
| Silver market | Null: 0 of 42 significant; SPA p = 0.90 |
| Earthquake (Himalayan arc) | Null: 0 of 26 significant, none confirmed; the Varuna-mandala indicator (highest rate ratio in both periods, not significant) is a candidate for a new pre-registration on independent data |
| Numerology vs astrology | Agreement equivalent to chance (kappa = -0.012 within +-0.05; 9 of 9 planets within +-0.10), as the paper derives analytically |
| Mundane | Pending: seeded, awaiting sourced founding times |
