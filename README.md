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

| Paper                                                                                    | Description                                                             |
| ---------------------------------------------------------------------------------------- | ----------------------------------------------------------------------- |
| [Master Research Report](pdfs/VEDIC_SYSTEMS_EMPIRICAL_ANALYSIS.pdf)                      | Consolidated 30+ page paper covering all research tracks                |
| [Numerology-Astrology Correlation](pdfs/NUMEROLOGY_ASTROLOGY_TEMPORAL_DISCONTINUITY.pdf) | Temporal discontinuity analysis between discrete and continuous systems |
| [Earthquake Prediction Analysis](pdfs/EARTHQUAKE_PREDICTION_INDIA_NEPAL_ANALYSIS.pdf)    | India-Nepal seismic pattern investigation                               |
| [Gold Market Correlation](pdfs/GOLD_MARKET_PLANETARY_CORRELATION_ANALYSIS.pdf)           | XAU/USD price prediction analysis                                       |

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
│   ├── use_cases/             ← Individual research tracks (numerology, earthquake, gold)
│   ├── scripts/               ← Pipeline scripts to generate artifacts & reports
│   ├── data/                  ← Raw and processed datasets
│   └── reports/               ← Generated Quarto manuscripts (PDF/HTML)
│
├── 🔧 libs/                   ← Core computation engines (importable Python library)
│   ├── vedic_astrology_core/  ← Swiss Ephemeris integration, chart calculations
│   ├── vedic_numerology/      ← Lo Shu, Chaldean, Vedic numerology calculators
│   └── visuals/               ← Chart and visualization generators
│
├── 🖥️ application/            ← Web interface and REST API
│   ├── web/                   ← Flask web app for interactive research
│   └── api/                   ← REST API (Python + JS client)
│
├── ⚙️ ops/                    ← DevOps, configuration, deployment
│   ├── config/                ← YAML configuration files
│   ├── requirements*.txt      ← Dependency sets (base, API, Colab)
│   └── Makefile               ← Build and workflow automation
│
├── 🧪 tests/                  ← Comprehensive test suite
├── 📖 docs/                   ← Project documentation, guides, API reference
└── .github/                   ← CI/CD workflows, issue templates, PR templates
```

For a deeper view, see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

---

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- [Quarto](https://quarto.org/docs/get-started/) (for report generation)
- `git`

### 1. Clone & Install

```bash
git clone https://github.com/astro-fusion/astro_research-white-paper.git
cd astro_research-white-paper

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate   # On Windows: .venv\Scripts\activate

# Install base dependencies
pip install -r ops/requirements.txt

# (Optional) Install the library in editable mode with dev tools
pip install -e ".[dev]"
```

### 2. Run the Research Pipeline

```bash
# Generate all research artifacts (charts, data files)
python3 research/scripts/generate_artifacts.py

# Render a specific report to HTML
quarto render research/reports/comprehensive_thesis/COMPREHENSIVE_RESEARCH_THESIS.qmd --to html

# Or use the Makefile
make build
```

### 3. Start the Web Interface

```bash
python application/web/web.py
# → Open http://localhost:5000
```

### 4. Run Tests

```bash
pytest tests/ -v

# With coverage
pytest tests/ --cov=libs --cov-report=html
open htmlcov/index.html
```

### 5. One-Command Setup (Make)

```bash
make help        # See all available targets
make install     # Install all dependencies
make test        # Run test suite
make quality-gate # Lint + type check + test
```

---

## 🔬 Research Use Cases

| Use Case                    | Status         | Description                                          | Key Files                                                            |
| --------------------------- | -------------- | ---------------------------------------------------- | -------------------------------------------------------------------- |
| **Numerology-Astrology**    | ✅ Active      | Lo Shu / Vedic digit mapping vs. planetary positions | [`research/use_cases/numerology/`](research/use_cases/numerology/)   |
| **Earthquake Prediction**   | 🔄 In Progress | Seismic pattern investigation (India-Nepal)          | [`research/use_cases/earthquake/`](research/use_cases/earthquake/)   |
| **Gold Market Correlation** | 🔄 In Progress | XAU/USD vs. planetary cycles                         | [`research/use_cases/gold_market/`](research/use_cases/gold_market/) |

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
