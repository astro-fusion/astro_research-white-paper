# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

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
