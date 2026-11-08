# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Changed (repository reorganization, ADR-001 WP-2)

- One layout: every study lives once in `studies/<name>/` (`gold_market`, `earthquake`, `numerology_vs_astrology`, `remedy_conflict_matrix`) with `README.md`, `paper/`, `scripts/`, `data/` (gitignored), `figures/`, `tables/`, `artifacts/` (gitignored). The duplicate copies under `research/use_cases/`, `docs/research/track_N_*` and root `use_cases/` were merged and removed.
- `studies/_paths.py` is the single paths module (`REPO_ROOT`, `DATA_ROOT`, `SNAPSHOT_ROOT`, `study_dir`, `artifacts_dir`, ...); scripts and tests use it, and no `sys.path` entry points at `research/` or `src/` any more. `make check-data` runs `scripts/check_data.py`.
- `research/scripts` -> `scripts/`, `research/notebooks` -> `notebooks/`, cross-study papers -> `papers/`, released PDFs -> `papers/pdf/` (one copy each), the gold manuscript -> `studies/gold_market/paper/manuscript.qmd`.
- Website: `_quarto.yml` renders `site/` (home, methods, principles, data, mundane, contribute, corrections), `studies/*/paper/` and `papers/`; the home page follows the ADR-001 vision statement.
- Project-tracking notes and status reports moved to `docs/archive/`; ADR-001 added under `docs/adr/`.
- Docs (`README.md`, `docs/INDEX.md`, `docs/ARCHITECTURE.md`, `docs/DEVELOPMENT_SETUP.md`, `ops/README.md`) describe the new layout and install with `pip install -e ".[dev]"`.

### Removed

- Rendered output is no longer tracked: `_book/`, `site_libs/`, `*-preview.html`, Quarto/pandoc `.tex` renders, release HTML/DOCX, `tex_artifacts/`, generated test reports. `.gitignore` covers them.
- `research/use_cases/numerology/src/numerology`, a copy of `libs/vedic_numerology`; scripts import `vedic_numerology.numerology`.

- Removed: plasma-physics track (papers/physics, src/diagnostics); the project scope is Vedic astrology, numerology and celestial-terrestrial correlation research.

### Added

- Full open-source documentation suite: root-level `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`
- GitHub Issue Templates: Bug Report, Feature Request, Research Request
- GitHub Pull Request Template
- Subfolder `README.md` files for all major directories (`libs/`, `research/`, `application/`, `ops/`, `tests/`)
- `docs/ARCHITECTURE.md` — high-level system design overview
- `docs/EDGE_CASES.md` — catalog of known edge cases for planetary calculations
- `docs/RESEARCH_METHODOLOGY.md` — guide for adding new research use cases
- `docs/DEVELOPMENT_SETUP.md` — detailed local environment setup guide
- `.github/workflows/README.md` — CI/CD workflow documentation

### Changed (build hygiene and reproducibility)

- `pyproject.toml` is now the single dependency source. `pyswisseph>=2.10,<3` and `scipy` are core dependencies; new extras `fetch` (yfinance), `diagrams` (google-generativeai, paperbanana), `docs` (Quarto/Jupyter, Sphinx), `dev` (pytest, pytest-cov, flake8, flake8-docstrings, black, isort, mypy), `api`, `app`; upper bounds added.
- `ops/requirements*.txt` are thin wrappers (`-e .[dev]` etc.); the drifted copies in `ops/config/requirements/` were removed. Exact pins: `ops/requirements.lock.txt` (generated with `uv pip compile`).
- `make install` uses `pip install -e ".[dev]"`; `make build` depends on the new `make check-data` (prints SHA-256 and row counts of required inputs) and no longer runs `generate_artifacts.py` twice.
- CI: flake8 now runs the full `.flake8` config instead of `--select=E9,F63,F7,F82`; every workflow installs from `pyproject.toml` extras; pip cache keys hash `pyproject.toml`.
- `get_config_paths()` looks for `ops/config/default_config.yaml` (was the nonexistent `config/default_config.yaml`) and honours the `ASTRO_CONFIG` environment variable.
- `.gitignore`: `_book/`, `_site/`, `site_libs/`, `*-preview.html`, `htmlcov/`, `coverage.xml`, `.mypy_cache/`, and Quarto `keep-tex` outputs under `research/` and `docs/research/`.

### Fixed

- CI: unquoted `pip install pyswisseph>=2.08.00 ...` (shell redirect created a file named `=2.08.00` and left pyswisseph unpinned) in five workflows.
- CI no longer fetches live data (removed `earthquake_data_fetcher.py` step; yfinance no longer installed in CI).

### Removed

- Stale untracked `src/vedic_astrology_core/` (bytecode only).
- Duplicate `ops/config/render.yaml` and `ops/config/railway.json` (identical to the copies in `ops/`).

---

## [0.1.0] — 2026-02-20

### Added

- **Core Library** (`libs/`):
  - Vedic Astrology Core Engine with Swiss Ephemeris (Lahiri Ayanamsa)
  - Planetary dignity scoring system (all classical dignities)
  - Vimshottari Dasha calculations with sub-period support
  - Transit analysis engine
  - Time series analysis for planetary strengths
  - Visualization generators (birth charts, timeline plots)
- **Research Use Cases** (`research/use_cases/`):
  - Numerology-Astrology integration study (Lo Shu, Vedic mapping, athlete correlations)
  - Earthquake prediction analysis (India-Nepal seismic patterns)
  - Gold market planetary correlation (XAU/USD vs planetary cycles)
- **Research Scripts** (`research/scripts/`):
  - `generate_artifacts.py` — full pipeline orchestration
  - `generate_track1_scientific_assets.py`, `generate_track2_scientific_assets.py`
  - Shell scripts for batch PDF/report generation
- **Application Layer** (`application/`):
  - Flask web application for interactive research exploration
  - REST API for programmatic access
  - JavaScript API client library
- **DevOps** (`ops/`):
  - `Makefile` with `build`, `test`, `lint`, `format`, `quality-gate` targets
  - Requirements files: base, API, Colab
  - Railway and Render deployment configurations
- **CI/CD** (`.github/workflows/`):
  - `ci.yml` — Python lint, type-check, and test on push/PR
  - `build-deploy.yml` — Full build and deployment pipeline
  - `publish-research.yml` — Automated Quarto manuscript publication
  - `data-analysis.yml` — Scheduled data analysis runs
  - `scientific-reporting.yml` — Scientific report generation
- **Tests** (`tests/`):
  - Comprehensive unit test suite for all library modules
  - Integration tests for the full research pipeline
  - E2E tests with Playwright for the web interface
  - Multiplatform validation tests
- **Pre-commit hooks** (`.pre-commit-config.yaml`):
  - Black, isort, flake8, yamllint, trailing-whitespace checks
- **Documentation** (`docs/`):
  - Project documentation index (`docs/INDEX.md`)
  - API reference documentation
  - Research framework guides
  - Quarto-based research website configuration

### Infrastructure

- `pyproject.toml` configured for `vedic-astrology-core` package
- MIT License for code; CC BY 4.0 for research content
- `.gitignore` configured for Python, Quarto, macOS, and large binary files

---

## Legend

| Symbol         | Meaning                           |
| -------------- | --------------------------------- |
| **Added**      | New features                      |
| **Changed**    | Changes to existing functionality |
| **Deprecated** | Soon-to-be-removed features       |
| **Removed**    | Removed features                  |
| **Fixed**      | Bug fixes                         |
| **Security**   | Security vulnerability fixes      |

[Unreleased]: https://github.com/astro-fusion/astro_research-white-paper/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/astro-fusion/astro_research-white-paper/releases/tag/v0.1.0
