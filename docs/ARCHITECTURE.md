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
│                        LIBRARY LAYER (libs/)                    │
│                                                                 │
│   🪐 vedic_astrology_core      🔢 vedic_numerology              │
│   ┌───────────────────────┐   ┌───────────────────────┐        │
│   │ astrology/            │   │ mulanka.py            │        │
│   │ dignity/              │   │ bhagyanka.py          │        │
│   │ dasha/                │   │ lo_shu.py             │        │
│   │ combinations/         │   │ chaldean.py           │        │
│   │ utils/                │   └───────────────────────┘        │
│   │ time_series.py        │                                     │
│   └───────────────────────┘   📊 visuals/                      │
│           │                   ┌───────────────────────┐        │
│           ▼                   │ birth_chart.py        │        │
│   🔭 Swiss Ephemeris          │ timeline_plot.py      │        │
│   (pyswisseph)                │ dignity_heatmap.py    │        │
│   Lahiri Ayanamsa             └───────────────────────┘        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────────┐
│                    RESEARCH PIPELINE (research/)                 │
│                                                                 │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────┐  │
│  │ Data Ingest  │───▶│  Analysis    │───▶│  Report          │  │
│  │ data/        │    │  scripts/    │    │  Generation      │  │
│  │ USGS, Yahoo  │    │  pipeline.py │    │  Quarto .qmd     │  │
│  └──────────────┘    └──────────────┘    └──────────────────┘  │
│                                                                 │
│  use_cases/  numerology/ ─ earthquake/ ─ gold_market/           │
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

- **`vedic_astrology_core/`**: Wraps `pyswisseph` for sub-arcsecond astronomical calculations. Uses the Lahiri Ayanamsa (sidereal coordinate system).
- **`vedic_numerology/`**: Implements Vedic, Chaldean, and Lo Shu numerology systems.
- **`visuals/`**: Generates publication-quality charts and diagrams.

**No external I/O** — pure computation only. This enables easy testing and reproducibility.

### 2. Research Pipeline (`research/`)

Orchestrates the full research workflow:

```
Raw Data → Preprocessing → Astrological Mapping → Statistical Analysis → Report
```

The pipeline is **parameterized via YAML** (in `ops/config/`) so that research tracks can be independently configured without code changes.

### 3. Application Layer (`application/`)

Provides user-facing interfaces built **on top of** the library layer:

- **`web/`**: A Flask web app for interactive, point-and-click chart generation and exploration.
- **`api/`**: A REST API that exposes library functions as HTTP endpoints.

Both are **stateless** — each request computes fresh results from the library. This simplifies deployment and eliminates database dependencies.

### 4. CI/CD (`.github/workflows/`)

| Workflow                   | Trigger            | Purpose                                        |
| -------------------------- | ------------------ | ---------------------------------------------- |
| `ci.yml`                   | Push / PR          | Lint, type-check, test all code                |
| `build-deploy.yml`         | Push to main       | Build and deploy the full platform             |
| `publish-research.yml`     | Push to main       | Render and push Quarto reports to GitHub Pages |
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
| **Separate `libs/` and `research/`** | Library stays stable while research evolves rapidly               |

---

## Extension Points

To **add a new digniy rule**: Edit `ops/config/dignity_rules.yml`

To **add a new planet**: Add to `ops/config/planets.yml` and implement in `vedic_astrology_core/astrology/`

To **add a new numerology system**: Create a new module in `libs/vedic_numerology/` following `lo_shu.py` as a template

To **add a new research track**: See [docs/RESEARCH_METHODOLOGY.md](RESEARCH_METHODOLOGY.md)

To **add a new API endpoint**: Add route to `application/api/api.py` with matching test in `tests/test_e2e_complete.py`
