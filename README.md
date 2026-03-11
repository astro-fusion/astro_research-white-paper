# 🪐 Vedic Astrology Research Platform

> **A high-precision computational framework for empirical research into Vedic Astrology, Numerology, and celestial-terrestrial correlations.**

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/astro-fusion/astro_research-white-paper/blob/main/research/notebooks/01_numerology_calculations.ipynb)
[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/downloads/)
[![Quarto](https://img.shields.io/badge/Quarto-1.3%2B-purple.svg)](https://quarto.org/)
[![CI/CD](https://github.com/astro-fusion/astro_research-white-paper/actions/workflows/ci.yml/badge.svg)](https://github.com/astro-fusion/astro_research-white-paper/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)
[![GitHub Discussions](https://img.shields.io/github/discussions/astro-fusion/astro_research-white-paper)](https://github.com/astro-fusion/astro_research-white-paper/discussions)
[![GitHub Issues](https://img.shields.io/github/issues/astro-fusion/astro_research-white-paper)](https://github.com/astro-fusion/astro_research-white-paper/issues)

---

## 🌐 Live Research & Downloads

| Resource                | Link                                                                                                            |
| ----------------------- | --------------------------------------------------------------------------------------------------------------- |
| 🌐 **Research Website** | [astro-fusion.github.io/astro_research-white-paper](https://astro-fusion.github.io/astro_research-white-paper/) |
| 📖 **GitHub Wiki**      | [Project Wiki](https://github.com/astro-fusion/astro_research-white-paper/wiki)                                 |
| 💬 **Discussions**      | [GitHub Discussions](https://github.com/astro-fusion/astro_research-white-paper/discussions)                    |

### 📄 Research Papers (PDF)

| Paper                                                                                               | Description                                                             |
| --------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------- |
| [Master Research Report](research_papers/VEDIC_SYSTEMS_EMPIRICAL_ANALYSIS.pdf)                      | Consolidated 30+ page paper covering all research tracks                |
| [Numerology-Astrology Correlation](research_papers/NUMEROLOGY_ASTROLOGY_TEMPORAL_DISCONTINUITY.pdf) | Temporal discontinuity analysis between discrete and continuous systems |
| [Earthquake Prediction Analysis](research_papers/EARTHQUAKE_PREDICTION_INDIA_NEPAL_ANALYSIS.pdf)    | India-Nepal seismic pattern investigation                               |
| [Gold Market Correlation](research_papers/GOLD_MARKET_PLANETARY_CORRELATION_ANALYSIS.pdf)           | XAU/USD price prediction analysis                                       |

---

## 📖 What Is This Project?

This repository is an **open multi-domain research platform** that:

1. **Curates empirically rigorous astro-fusion plasma physics white papers** — covering thermal Helium line ratio spectroscopy, pellet ablation dynamics, relativistic κ-distributions, charge-exchange particle analysers, and wireless power transmission.
2. **Applies classical Vedic astrological principles** to empirical, reproducible data science using Swiss Ephemeris (sub-arcsecond precision), statistical validation, Granger Causality, and Monte Carlo permutations.
3. **Bridges both domains** — treating planetary geometry and high-temperature plasma diagnostics as multi-variable time-series amenable to unified ML analysis.

> **We invite plasma physicists, astronomers, data scientists, astrologers, and skeptics alike to explore, challenge, and contribute.**

---

## 🏗️ Architecture Overview

```
astro_research-white-paper/
│
├── 📐 SYMBOLOGY.md            ← Centralized math symbol dictionary (λ collision resolved)
│
├── 📚 papers/                 ← Static white papers (LaTeX math, Markdown)
│   ├── physics/               ← Plasma physics: spectroscopy, pellet ablation, κ-distributions
│   └── astrology/             ← Celestial mechanics, house systems, aspects, retrogrades
│
├── 🗄️ data/                   ← Scientific datasets (HDF5 / Parquet, never raw CSV)
│   ├── empirical/             ← Charge-exchange analyzer & spectroscopy raw data
│   ├── ephemeris/             ← Swiss Ephemeris + JPL Horizons planetary positions
│   └── simulations/           ← Pellet ablation ODE outputs, κ Monte Carlo results
│
├── ⚙️ src/                    ← Pure-computation engine libraries
│   ├── diagnostics/           ← Plasma: line ratio CR model, pellet ODE, κ simulator
│   └── celestial/             ← Astrology: ephemeris, house systems, aspects, dignity
│
├── 📚 research/               ← Research use cases, notebooks, Quarto reports
│   ├── use_cases/             ← numerology / earthquake / gold_market / remedy_conflict
│   ├── scripts/               ← Pipeline scripts → artifacts & reports
│   └── reports/               ← Generated Quarto manuscripts (PDF/HTML)
│
├── 🔧 libs/                   ← Vedic astrology + numerology core Python library
│   ├── vedic_astrology_core/  ← Swiss Ephemeris integration (pyswisseph)
│   └── vedic_numerology/      ← Lo Shu, Mulanka, Bhagyanka, Chaldean calculators
│
├── 🖥️ application/            ← Web interface and REST API (Flask, stateless)
├── ⚙️ ops/                    ← DevOps: config YAML, Makefile, Docker, Conda env
├── 📖 docs/                   ← Full documentation catalogue
└── 🧪 tests/                  ← Comprehensive pytest suite
```

For a deeper view of the system design, see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md). Detailed research methodologies are documented in [docs/RESEARCH_METHODOLOGY.md](docs/RESEARCH_METHODOLOGY.md).

---

## 📐 Mathematical Symbol Reference

> **Critical for cross-domain readability**: the symbol $\lambda$ means **wavelength** in plasma physics but **ecliptic longitude** in astrological computation. All symbols are resolved in:

➜ **[SYMBOLOGY.md](SYMBOLOGY.md)** — the single authoritative dictionary for all variables across physics and astrology domains.

---

## 🚀 Quick Start

```bash
git clone https://github.com/astro-fusion/astro_research-white-paper.git
cd astro_research-white-paper

make install     # 1. Setup environment & install dependencies
make build       # 2. Generate all data artifacts & research PDFs
```

---

## 🏗️ Core Workflows

### 📄 1. PDF Generation

Research papers are generated using **Quarto**:

- **Generate Everything**: `make pdfs`
- **Output Directory**: Root `pdfs/` folder

### 📊 2. Data & Artifact Generation

```bash
make artifacts                    # Generate all charts and statistical tables
python src/celestial/ephemeris_engine.py --help   # Ephemeris generation
python src/diagnostics/line_ratio_spectroscopy.py --help  # He line ratio lookup
```

### 🖥️ 3. Web Interface

```bash
source .venv/bin/activate
python application/web/web.py
# → Open http://localhost:5000
```

### 🧪 4. Testing & Quality

```bash
make test          # Run all tests
make quality-gate  # Lint + Type Check + Test
```

---

## 🔬 Research Use Cases

| Use Case                     | Status         | Description                                          | Key Files                                                     |
| ---------------------------- | -------------- | ---------------------------------------------------- | ------------------------------------------------------------- |
| **Numerology-Astrology**     | ✅ Active      | Lo Shu / Vedic digit mapping vs. planetary positions | [Explore Track 1](research/use_cases/numerology/)             |
| **Earthquake Prediction**    | 🔄 In Progress | Seismic pattern investigation (India-Nepal)          | [Explore Track 2](research/use_cases/earthquake/)             |
| **Gold Market Correlation**  | 🔄 In Progress | XAU/USD vs. planetary cycles                         | [Explore Track 3](research/use_cases/gold_market/)            |
| **Remedy Conflict Analysis** | 🔄 In Progress | Side-effect and collision analysis for remedies      | [Explore Track 4](research/use_cases/remedy_conflict_matrix/) |

> **Want to propose a new research track?** [Open a Research Request Issue →](https://github.com/astro-fusion/astro_research-white-paper/issues/new?template=research_request.yml)

---

## 🗺️ Four-Phase Strategic Roadmap

```
Phase I   (Current)  — Empirical plasma physics baseline + open-science docs ✅
           → SYMBOLOGY.md, papers/physics/ (5 papers), data/ structure, validation docs

Phase II  (v0.2)     — Dynamic CI/CD + Physics computation engines
           → src/diagnostics/ engines, automated TDD tests, unified API layer

Phase III (v0.3)     — Astrological logic engine (all cases)
           → src/celestial/ engines, papers/astrology/ (6 papers), exhaustive house/aspect/dignity logic

Phase IV  (v1.0)     — Multi-domain ML synthesis
           → PCA, clustering, neural networks across plasma + astrology time-series
           → Peer review submission, PyPI package, stable API
```

| Phase | Component                                                    | Status        |
| ----- | ------------------------------------------------------------ | ------------- |
| I     | White papers: physics (5)                                    | ✅ Complete   |
| I     | SYMBOLOGY.md                                                 | ✅ Complete   |
| I     | docs: VALIDATION, DATA_PROVENANCE, COMPUTATIONAL_ENVIRONMENT | ✅ Complete   |
| I     | data/ directory structure + READMEs                          | ✅ Complete   |
| II    | src/diagnostics/ Python engines                              | ✅ Scaffolded |
| III   | papers/astrology/ (6 papers)                                 | ✅ Complete   |
| III   | src/celestial/ Python engines                                | ✅ Scaffolded |
| II–IV | CI/CD, API, ML pipeline                                      | 🔄 Planned    |

---

## 📚 White Papers Index

### Physics (`papers/physics/`)

| #   | Paper                                                                                     | Topic                              |
| --- | ----------------------------------------------------------------------------------------- | ---------------------------------- |
| 01  | [He Line Ratio Spectroscopy](papers/physics/01_line_ratio_spectroscopy_thermal_helium.md) | CR model, $R_{\rm line}(T_e, n_e)$ |
| 02  | [Pellet Ablation Dynamics](papers/physics/02_pellet_ablation_dynamics_elm_mitigation.md)  | ELM mitigation ODE                 |
| 03  | [Relativistic κ-Distributions](papers/physics/03_relativistic_kappa_distributions.md)     | Monte Carlo RNG                    |
| 04  | [Charge-Exchange Analyzers](papers/physics/04_charge_exchange_particle_analyzers.md)      | $T_i$ from NPA                     |
| 05  | [Wireless Power Transmission](papers/physics/05_wireless_power_transmission.md)           | WPT + SPS                          |

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

- **Swiss Ephemeris** (Astro.com) — sub-arcsecond planetary precision
- **NASA JPL Horizons** — authoritative Solar System ephemeris
- **Quarto** — reproducible scientific publishing
- **IRCC-AFP**, **CFQS (NIFS/SWJTU)** — astro-fusion plasma physics collaboration
- The open-source Python scientific ecosystem: NumPy, SciPy, Pandas, pyswisseph, Matplotlib, statsmodels

---

_Built with 🪐 by the [AstroFusion](https://github.com/astro-fusion) team and open-source contributors._
