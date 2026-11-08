# 🏗️ System Architecture

This document describes the high-level architecture of the Vedic Astrology Research Platform, explaining how components relate to each other and the data flow through the system.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER-FACING LAYER                        │
│                                                                 │
│   🌐 Research Website          🖥️ Web App          📡 REST API  │
│   (GitHub Pages / Quarto)      (Flask)           (Python/Flask) │
│          │                         │                   │        │
└──────────┼─────────────────────────┼───────────────────┼────────┘
           │                         │                   │
           ▼                         ▼                   ▼
┌─────────────────────────────────────────────────────────────────┐
│        LIBRARY LAYER (libs/, installed with pip install -e .)   │
│                                                                 │
│   🪐 vedic_astrology_core      🔢 vedic_numerology              │
│   ┌───────────────────────┐   ┌───────────────────────┐        │
│   │ astrology/  ephemeris │   │ numerology.py         │        │
│   │   houses, vargas,     │   │ engine.py, analysis   │        │
│   │   aspects, combustion │   └───────────────────────┘        │
│   │ dasha/  dignity/      │                                     │
│   │ rules/  stats/        │   tools/visuals (not installed:     │
│   │ markets/ datasets/    │   LLM diagrams, `diagrams` extra)   │
│   └───────────────────────┘                                     │
│           │                                                     │
│           ▼                                                     │
│   🔭 Swiss Ephemeris (pyswisseph), sidereal Lahiri, Moshier     │
│   unless .se1 files; cross-checked against JPL Horizons in CI   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────────┐
│              RESEARCH PIPELINE (studies/, scripts/)              │
│                                                                 │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────┐  │
│  │ Data Ingest  │───▶│  Analysis    │───▶│  Report          │  │
│  │ data/        │    │  scripts/    │    │  Generation      │  │
│  │ USGS, Yahoo  │    │  pipeline.py │    │  Quarto .qmd     │  │
│  └──────────────┘    └──────────────┘    └──────────────────┘  │
│                                                                 │
│  studies/  gold_market/ ─ earthquake/ ─ numerology_vs_astrology/ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────────┐
│                         OUTPUTS                                 │
│   📄 PDF Reports     🌐 HTML Site     📊 Charts & CSVs          │
└─────────────────────────────────────────────────────────────────┘
```

---

## Component Descriptions

### 1. Library Layer (`libs/`)

The core computational engine. **This is the most stable component** — changes here affect everything.
There is one engine: the former second implementation under `src/` was
retired in WP-7 (see ADR-001) and `src/` no longer exists.

`pip install -e .` installs two import roots from `libs/` (setuptools
`package-dir`); nothing needs `PYTHONPATH`:

- **`vedic_astrology_core/`**: Wraps `pyswisseph` (built-in Moshier analytic ephemeris unless SE data files are installed). Sidereal (Lahiri by default) with one node model, whole-sign houses with a polar fallback, 16 BPHS vargas, Vimshottari dasha, Vedic dignity, geometric aspects, the YAML rules engine, `stats`, `markets` and the planetary `datasets` generator. Golden-tested against PyJHora and cross-checked against JPL Horizons.
- **`vedic_numerology/`**: Implements Vedic, Chaldean, and Lo Shu numerology systems.

`tools/visuals/` (the LLM diagram generator, `diagrams` extra) is outside the
package and runs as `python -m tools.visuals.manager`.

**No external I/O** — pure computation only. This enables easy testing and reproducibility.

### 2. Research Pipeline (`studies/`, `scripts/`)

Each study lives in `studies/<name>/` with its README, `paper/`, `scripts/`,
`data/` (gitignored), `figures/`, `tables/` and `artifacts/` (gitignored).
Cross-study scripts live in `scripts/`, cross-study papers in `papers/`, the
website pages in `site/`, and all data under the single `data/` root. Paths
are resolved through `studies/_paths.py`; see
[ADR-001](adr/ADR-001-flagship-research-repo.md).

Orchestrates the full research workflow:

```
Raw Data → Preprocessing → Astrological Mapping → Statistical Analysis → Report
```

The pipeline is **parameterized via YAML** (in `ops/config/`) so that research tracks can be independently configured without code changes.

### 3. Application Layer (`application/`)

Provides user-facing interfaces built **on top of** the library layer:

- **`web/`**: A Streamlit explorer (`app.py`) and a Flask timeline (`web.py`), extra `app`.
- **`api/`**: A FastAPI REST API (`api.py`) that exposes library functions as HTTP endpoints, extra `api`.

Both import the installed package; there are no `sys.path` entries.

Both are **stateless** — each request computes fresh results from the library. This simplifies deployment and eliminates database dependencies.

### 4. CI/CD (`.github/workflows/`)

| Workflow                   | Trigger            | Purpose                                        |
| -------------------------- | ------------------ | ---------------------------------------------- |
| `ci.yml`                   | Push / PR, `v*` tag | black, isort, flake8, mypy, bandit, pip-audit; tests incl. the JPL Horizons cross-check; Sphinx build; release only on a `v*` tag |
| `build-deploy.yml`         | Push to main       | Earthquake pipeline tests, Quarto site render, Playwright smoke, GitHub Pages deploy (the only Pages deployer) |
| `publish-research.yml`     | Release published  | Render and attach the research PDFs            |
| `data-analysis.yml`        | Scheduled (weekly) | Automated data refresh and re-analysis         |
| `scientific-reporting.yml` | Manual             | Generate PDF scientific manuscripts            |

---

## Data Flow: Birth Chart Calculation

```
User Input (birth_date, birth_time, lat, lon)
         │
         ▼
  VedicChart.__init__()
         │
         ├─▶ utils.parse_datetime()    ← Validate and parse input
         │
         ├─▶ utils.calculate_ayanamsa()  ← Lahiri ayanamsa for epoch
         │
         ├─▶ pyswisseph.calc_ut()       ← Swiss Ephemeris: ecliptic coords
         │
         ├─▶ astrology.assign_houses()  ← Whole-sign or Placidus houses
         │
         ├─▶ dignity.score_planets()    ← Classical dignity scoring
         │
         └─▶ VedicChart (object)        ← Complete chart ready for use
                    │
                    ├─▶ visuals.render_chart()    → PNG/SVG chart image
                    ├─▶ dasha.calculate_periods() → Dasha timeline
                    └─▶ combinations.detect_yogas() → Yoga list
```

---

## Design Decisions & Rationale

| Decision                             | Rationale                                                         |
| ------------------------------------ | ----------------------------------------------------------------- |
| **Lahiri Ayanamsa**                  | Official standard; most widely used in Jyotish research           |
| **Swiss Ephemeris**                  | Highest available precision; trusted by professional astronomers  |
| **No Database**                      | Reproducibility — all outputs are deterministic from input        |
| **Quarto for Reports**               | Reproducible science publishing; native Python/R support          |
| **YAML Config for Classical Rules**  | Non-programmers can correct classical rules without touching code |
| **Stateless Flask API**              | Simplifies horizontal scaling and testing                         |
| **Separate `libs/` and `studies/`**  | Library stays stable while research evolves rapidly               |

---

## Extension Points

To **add a new digniy rule**: Edit `ops/config/dignity_rules.yml`

To **add a new planet**: Add to `ops/config/planets.yml` and implement in `vedic_astrology_core/astrology/`

To **add a new numerology system**: Create a new module in `libs/vedic_numerology/` following `lo_shu.py` as a template

To **add a new research track**: See [docs/RESEARCH_METHODOLOGY.md](RESEARCH_METHODOLOGY.md)

To **add a new API endpoint**: Add route to `application/api/api.py` with a matching test under `tests/` (FastAPI `TestClient`)
