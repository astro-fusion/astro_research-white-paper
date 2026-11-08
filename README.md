# 🪐 Vedic Astrology Research Platform

> **A high-precision computational framework for empirical research into Vedic Astrology, Numerology, and celestial-terrestrial correlations.**

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/astro-fusion/astro_research-white-paper/blob/main/notebooks/01_numerology_calculations.ipynb)
[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/downloads/)
[![Quarto](https://img.shields.io/badge/Quarto-1.3%2B-purple.svg)](https://quarto.org/)
[![CI/CD](https://github.com/astro-fusion/astro_research-white-paper/actions/workflows/ci.yml/badge.svg)](https://github.com/astro-fusion/astro_research-white-paper/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)
[![GitHub Discussions](https://img.shields.io/github/discussions/astro-fusion/astro_research-white-paper)](https://github.com/astro-fusion/astro_research-white-paper/discussions)
[![GitHub Issues](https://img.shields.io/github/issues/astro-fusion/astro_research-white-paper)](https://github.com/astro-fusion/astro_research-white-paper/issues)

---

> **Corrections notice (2026-11-08).** Published results in this repository are withdrawn pending re-analysis. Some earthquake figures were generated from random numbers, the gold-market statistics were computed from a synthetic placeholder series, planetary positions were tropical rather than sidereal (and Ketu was computed as Rahu), and the DE440 ephemeris claim was incorrect. Details: [CORRECTIONS.md](CORRECTIONS.md).

---

## 🌐 Live Research & Downloads

| Resource                | Link                                                                                                            |
| ----------------------- | --------------------------------------------------------------------------------------------------------------- |
| 🌐 **Research Website** | [astro-fusion.github.io/astro_research-white-paper](https://astro-fusion.github.io/astro_research-white-paper/) |
| 📖 **GitHub Wiki**      | [Project Wiki](https://github.com/astro-fusion/astro_research-white-paper/wiki)                                 |
| 💬 **Discussions**      | [GitHub Discussions](https://github.com/astro-fusion/astro_research-white-paper/discussions)                    |

### Papers

The current papers are the Quarto pages on the website, rendered from
`studies/<name>/paper/`. The PDFs in [papers/pdf/](papers/pdf/README.md) predate
the corrections and are kept only for the record; that folder's README marks
each one pre-correction and superseded (the gold-market PDF is withdrawn).

---

## 📖 What Is This Project?

This repository is an **open multi-domain research platform** that:

1. **Applies classical Vedic astrological principles** to empirical, reproducible data science using the Swiss Ephemeris library with the built-in Moshier analytic ephemeris unless SE data files are installed, statistical validation, Granger Causality, and Monte Carlo permutations.
2. **Studies Vedic numerology** — Lo Shu, Mulanka, Bhagyanka and Chaldean systems as computable, testable models.
3. **Investigates celestial-terrestrial correlations** — treating planetary geometry and terrestrial phenomena (earthquakes, gold market) as time-series amenable to statistical and ML analysis.

> **We invite astronomers, data scientists, astrologers, and skeptics alike to explore, challenge, and contribute.**

---

## 🏗️ Architecture Overview

```
astro_research-white-paper/
├── studies/                   one folder per study (hypothesis.yaml, scripts/, paper/, data/, artifacts/)
│   ├── gold_market/
│   ├── silver_market/
│   ├── earthquake/
│   ├── mundane/
│   ├── numerology_vs_astrology/
│   ├── remedy_conflict_matrix/
│   └── _paths.py              the one place that knows repository paths
├── rules/                     astrological rules as YAML (financial/, seismic/, general/, mundane/), schema.json
├── libs/                      Python packages
│   ├── vedic_astrology_core/  engine, rules, stats, markets
│   ├── vedic_numerology/
│   └── visuals/
├── site/                      website pages: home, methods, principles, data, mundane, contribute, corrections
├── papers/                    cross-study papers; astrology/ white papers
│   └── pdf/                   pre-correction PDFs, kept for the record
├── data/                      single data root: raw/, processed/, snapshots/ (gitignored)
├── scripts/                   repository CLIs; migrations/ holds one-shot scripts
├── docs/                      methodology, provenance, architecture, adr/, archive/
├── tests/                     pytest suite
├── src/                       celestial engines (to be consolidated with libs/, ADR-001)
├── application/               web interface and REST API (out of scope for now)
├── templates/, styles/        Quarto paper template and LaTeX/CSL styles
└── ops/                       config, deploy files, requirements.lock.txt
```

Rendered output (HTML, PDF, TeX, `_book`, `site_libs`, `_freeze`) is never committed; CI renders the website to GitHub Pages. The layout is recorded in [docs/adr/ADR-001-flagship-research-repo.md](docs/adr/ADR-001-flagship-research-repo.md).

For a deeper view of the system design, see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md). Detailed research methodologies are documented in [docs/RESEARCH_METHODOLOGY.md](docs/RESEARCH_METHODOLOGY.md).

---

## 📐 Mathematical Symbol Reference

> **For readability**: symbols such as $\lambda_{\rm ecl}$ (ecliptic longitude) are defined once and used consistently. All symbols are defined in:

➜ **[SYMBOLOGY.md](SYMBOLOGY.md)** — the single authoritative dictionary for all variables across astrology and statistics.

---

## 🚀 Quick Start

```bash
git clone https://github.com/astro-fusion/astro_research-white-paper.git
cd astro_research-white-paper
python3 -m venv .venv && source .venv/bin/activate
```

**Astrologers: write and check a rule.** Rules are YAML files under `rules/`;
you do not need to write Python. The guide walks through one rule from idea to
passing test: [CONTRIBUTING_ASTROLOGERS.md](CONTRIBUTING_ASTROLOGERS.md).

```bash
pip install -e .
astro-rules list --domain seismic
astro-rules validate rules/seismic/my_rule.yaml
astro-rules test rules/seismic/my_rule.yaml
astro-rules explain <rule-id> 2014-07-20T11:45:00+05:45
```

**Scientists: read a pre-registration and re-run a study.** Each study states
its hypotheses, data, tests and correction in `studies/<name>/hypothesis.yaml`
before any data are analysed, and one command reproduces its `results.json`:

```bash
pip install -e ".[stats]"
python studies/earthquake/scripts/pipeline.py --seed 42
python studies/gold_market/scripts/pipeline.py --seed 42
quarto render --to html          # the website, papers read results.json; output in _site/
```

**Developers: install and test.**

```bash
pip install -e ".[dev]"
pytest tests/
flake8 libs/ scripts/ studies/ tests/
```

---

## 🔬 Studies and current results

Outcomes of the pre-registered runs (seed 42), read from each study's
`artifacts/results.json`. A null result means no tested configuration passed
the registered multiple-testing correction and replicated in the held-out
period; it says nothing beyond those configurations, data and periods.

| Study | Status | Outcome |
| --- | --- | --- |
| [Gold market](studies/gold_market/) | Run | Null. 1 of 42 exploration tests significant after Benjamini-Yekutieli, 0 confirmed in 2016-2026; Hansen SPA p = 0.53. |
| [Silver market](studies/silver_market/) | Run | Null. 0 of 42 exploration tests significant, 0 confirmed; Hansen SPA p = 0.90. |
| [Earthquake (Himalayan arc)](studies/earthquake/) | Run | Null. 0 of 26 exploration tests significant, 0 confirmed; SPA p = 0.08. The Moon in a Varuna-mandala nakshatra had the highest rate ratio in both periods but did not pass the correction; it is a candidate for a new pre-registration on independent data. |
| [Numerology vs astrology](studies/numerology_vs_astrology/) | Run | Equivalent to chance, as derived analytically: kappa between the numerology planet and the Moon's nakshatra lord = -0.012, within the registered +-0.05 (TOST); 9 of 9 planets' numerology-dignity correlations within +-0.10. |
| [Mundane](studies/mundane/) | Pending | Seeded; awaiting sourced founding times for the national charts. |
| [Remedy conflict matrix](studies/remedy_conflict_matrix/) | Descriptive | No hypothesis test. |

> **Want to propose a new research track?** [Open a Research Request Issue →](https://github.com/astro-fusion/astro_research-white-paper/issues/new?template=research_request.yml)

---

## 🗺️ Four-Phase Strategic Roadmap

```
Phase I   (Current)  — Open-science docs and astrological white papers ✅
           → SYMBOLOGY.md, papers/astrology/, data/ structure, validation docs

Phase II  (v0.2)     — Dynamic CI/CD
           → automated TDD tests, unified API layer

Phase III (v0.3)     — Astrological logic engine (all cases)
           → one engine in libs/vedic_astrology_core/, papers/astrology/ (6 papers), exhaustive house/aspect/dignity logic

Phase IV  (v1.0)     — Multi-domain ML synthesis
           → PCA, clustering, neural networks across astrology, numerology and terrestrial time-series
           → Peer review submission, PyPI package, stable API
```

| Phase | Component                                                    | Status        |
| ----- | ------------------------------------------------------------ | ------------- |
| I     | SYMBOLOGY.md                                                 | ✅ Complete   |
| I     | docs: VALIDATION, DATA_PROVENANCE, COMPUTATIONAL_ENVIRONMENT | ✅ Complete   |
| I     | data/ directory structure + READMEs                          | ✅ Complete   |
| III   | papers/astrology/ (6 papers)                                 | ✅ Complete   |
| III   | libs/vedic_astrology_core/ (single engine, golden-tested)    | ✅ Complete   |
| II–IV | CI/CD, API, ML pipeline                                      | 🔄 Planned    |

---

## 📚 White Papers Index

### Astrology (`papers/astrology/`)

| #   | Paper                                                                                               | Topic                    |
| --- | --------------------------------------------------------------------------------------------------- | ------------------------ |
| 01  | [Celestial Mechanics](papers/astrology/01_celestial_mechanics_and_ephemeris.md)                     | Coordinate transforms    |
| 02  | [House Systems & Polar Singularities](papers/astrology/02_house_systems_and_polar_singularities.md) | Fallback routing         |
| 03  | [Aspect Geometry & Graph Theory](papers/astrology/03_aspect_geometry_graph_theory.md)               | Adjacency matrix         |
| 04  | [Retrogrades & Progressions](papers/astrology/04_temporal_inflection_retrogrades_progressions.md)   | $d\lambda/dt$ calculus   |
| 05  | [Declination & Out-of-Bounds](papers/astrology/05_declination_out_of_bounds.md)                     | Parallel/contra-parallel |
| 06  | [Essential Dignity Scoring](papers/astrology/06_essential_dignity_scoring.md)                       | O(1) hash-map scoring    |

---

## 🤝 Contributing

We warmly welcome contributions of all kinds — from fixing a typo to proposing a new research methodology.

### Good First Issues

Look for issues tagged [`good-first-issue`](https://github.com/astro-fusion/astro_research-white-paper/issues?q=label%3A%22good+first+issue%22) to get started.

### Quick Contribution Steps

```bash
# 1. Fork and clone
git clone https://github.com/YOUR_USERNAME/astro_research-white-paper.git

# 2. Feature branch
git checkout -b feature/your-feature-name

# 3. Quality gate
make quality-gate

# 4. Push and PR
git push origin feature/your-feature-name
```

**Read the full guide:** [CONTRIBUTING.md](CONTRIBUTING.md)

### Areas Most Needing Contributions

- 🧪 **New test cases** — especially edge cases for planetary calculations
- 📊 **New research use cases** — propose and implement new empirical research tracks
- 🐛 **Bug reports** — precision issues, calculation discrepancies
- 📖 **Documentation** — tutorials, explainers, translations
- 🌐 **Translations** — translating research findings for non-English audiences

---

## 📁 Documentation Index

| Document                                                                   | Purpose                              |
| -------------------------------------------------------------------------- | ------------------------------------ |
| [SYMBOLOGY.md](SYMBOLOGY.md)                                               | Centralized math symbol dictionary   |
| [CONTRIBUTING.md](CONTRIBUTING.md)                                         | Contribution guide                   |
| [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)                                   | Community standards                  |
| [SECURITY.md](SECURITY.md)                                                 | Security policy                      |
| [CHANGELOG.md](CHANGELOG.md)                                               | Version history                      |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)                               | System design overview               |
| [docs/VALIDATION_AND_EPISTEMOLOGY.md](docs/VALIDATION_AND_EPISTEMOLOGY.md) | Model assumptions, RNG seeds, BC     |
| [docs/DATA_PROVENANCE.md](docs/DATA_PROVENANCE.md)                         | Dataset registry and reproducibility |
| [docs/COMPUTATIONAL_ENVIRONMENT.md](docs/COMPUTATIONAL_ENVIRONMENT.md)     | Hardware, Docker, Conda specs        |
| [docs/EDGE_CASES.md](docs/EDGE_CASES.md)                                   | Known edge cases & tests             |
| [docs/DEVELOPMENT_SETUP.md](docs/DEVELOPMENT_SETUP.md)                     | Environment setup                    |
| [docs/RESEARCH_METHODOLOGY.md](docs/RESEARCH_METHODOLOGY.md)               | How to add research tracks           |
| [tests/TESTING_GUIDE.md](tests/TESTING_GUIDE.md)                           | Testing conventions                  |

---

## 📜 License

**MIT License** for code — see [LICENSE](LICENSE).
Research content (manuscripts, datasets) licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).

---

## 🙏 Acknowledgments

- **Swiss Ephemeris** (Astro.com) — built-in Moshier analytic ephemeris unless SE data files are installed
- **NASA JPL Horizons** — authoritative Solar System ephemeris
- **Quarto** — reproducible scientific publishing
- The open-source Python scientific ecosystem: NumPy, SciPy, Pandas, pyswisseph, Matplotlib, statsmodels

---

_Built with 🪐 by the [AstroFusion](https://github.com/astro-fusion) team and open-source contributors._
