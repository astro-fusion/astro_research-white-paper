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

This repository is an **open research platform** that applies classical Vedic astrological principles to empirical, reproducible data science. It bridges:

- **Traditional Jyotish**: Vedic planetary dignities, Dasha systems, Nakshatra analysis
- **Modern Computational Methods**: Swiss Ephemeris (arcsecond precision), statistical validation, Granger Causality, Monte Carlo permutations
- **Open Science**: Every hypothesis, dataset, notebook, and finding is versioned and reproducible

> **We invite astronomers, data scientists, astrologers, researchers, and skeptics alike to explore, challenge, and contribute.**

---

## 🏗️ Architecture Overview

```
astro_research-white-paper/
│
├── 📚 research/               ← Research use cases, data, notebooks, reports
│   ├── use_cases/             ← Individual tracks (numerology, earthquake, gold, remedy)
│   ├── scripts/               ← Pipeline scripts to generate artifacts & reports
│   └── reports/               ← Generated Quarto manuscripts (PDF/HTML)
│
├── 🔧 libs/                   ← Core computation engines (Python library)
│   ├── vedic_astrology_core/  ← Swiss Ephemeris integration
│   └── vedic_numerology/      ← Numerology calculators
│
├── 🖥️ application/            ← Web interface and REST API
│   ├── web/                   ← Flask web app
│   └── api/                   ← REST API (Python + JS client)
│
├── ⚙️ ops/                    ← DevOps, configuration, deployment
│   ├── config/                ← YAML configuration files
│   └── Makefile               ← Build automation
│
├── 📖 docs/                   ← Project documentation, guides, research docs
│   ├── api/                   ← API references and endpoint docs
│   └── research/              ← Deep dives: math models, architecture, ethics
│
└── 🧪 tests/                  ← Comprehensive test suite
```

For a deeper view of the system design, see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md). Detailed research methodologies are documented in [docs/RESEARCH_METHODOLOGY.md](docs/RESEARCH_METHODOLOGY.md).

---

## 🚀 Quick Start

## 🚀 Quick Start (Get Result ASAP)

To get everything running—from dependencies to research PDFs—run these three commands:

```bash
git clone https://github.com/astro-fusion/astro_research-white-paper.git
cd astro_research-white-paper

make install     # 1. Setup environment & install dependencies
make build       # 2. Generate all data artifacts & research PDFs
```

---

## 🏗️ Core Workflows

### 📄 1. PDF Generation

Research papers are generated using **Quarto**. You can generate individual tracks or build the entire library:

- **Generate Everything**: `make pdfs`
- **Output Directory**: All generated PDFs are moved to the root `pdfs/` folder.

### 📊 2. Data & Artifact Generation

Before rendering PDFs, the Python research pipeline must generate the underlying charts and statistical tables:

- **Generate All Artifacts**: `make artifacts`
- **Manual Run**: `python3 research/scripts/generate_artifacts.py` (requires venv)

### 🖥️ 3. Web Interface

To explore the research interactively via the web app:

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

## 🤝 Contributing

We warmly welcome contributions of all kinds — from fixing a typo to proposing a new research methodology.

### Good First Issues

Look for issues tagged [`good-first-issue`](https://github.com/astro-fusion/astro_research-white-paper/issues?q=label%3A%22good+first+issue%22) to get started.

### Quick Contribution Steps

```bash
# 1. Fork the repo and clone your fork
git clone https://github.com/YOUR_USERNAME/astro_research-white-paper.git

# 2. Create a feature branch
git checkout -b feature/your-feature-name

# 3. Make changes, then run quality checks
make quality-gate

# 4. Push and open a Pull Request
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

| Document                                                     | Purpose                                   |
| ------------------------------------------------------------ | ----------------------------------------- |
| [CONTRIBUTING.md](CONTRIBUTING.md)                           | How to contribute code, data, or research |
| [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)                     | Community standards                       |
| [SECURITY.md](SECURITY.md)                                   | Security policy and reporting             |
| [CHANGELOG.md](CHANGELOG.md)                                 | Version history                           |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)                 | System design and component overview      |
| [docs/EDGE_CASES.md](docs/EDGE_CASES.md)                     | Known edge cases & how to add new ones    |
| [docs/DEVELOPMENT_SETUP.md](docs/DEVELOPMENT_SETUP.md)       | Detailed environment setup                |
| [docs/RESEARCH_METHODOLOGY.md](docs/RESEARCH_METHODOLOGY.md) | How to add new research use cases         |
| [tests/TESTING_GUIDE.md](tests/TESTING_GUIDE.md)             | Testing guide and conventions             |

---

## 🗺️ Roadmap

```
v0.1 (Current)  ── Library foundation, 3 research tracks, CI/CD ✅
v0.2            ── Pytest coverage >80%, API documentation, Docker support
v0.3            ── New research track (Weather/Agriculture), plugin system
v1.0            ── Peer review submission, PyPI package, stable API
```

See [GitHub Milestones](https://github.com/astro-fusion/astro_research-white-paper/milestones) for detailed planning.

---

## 📜 License

This project is licensed under the **MIT License** — see [LICENSE](LICENSE) for details.

The research content (manuscripts, datasets, findings) is licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).

---

## 🙏 Acknowledgments

- **Swiss Ephemeris** by Astro.com — for planetary calculation precision
- **Quarto** — for reproducible scientific publishing
- The open-source Python scientific ecosystem: NumPy, Pandas, Matplotlib, statsmodels

---

_Built with 🪐 by the [AstroFusion](https://github.com/astro-fusion) team and open-source contributors._
