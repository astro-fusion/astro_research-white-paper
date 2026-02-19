# 🪐 Vedic Astrology Research Platform

A high-precision computational framework for empirical research into Vedic Astrology, Numerology, and celestial-terrestrial correlations.

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/astro-fusion/astro_research-white-paper/blob/main/notebooks/01_numerology_calculations.ipynb)
[![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Quarto](https://img.shields.io/badge/Quarto-1.3+-purple.svg)](https://quarto.org/)
[![CI/CD](https://github.com/astro-fusion/astro_research-white-paper/actions/workflows/ci.yml/badge.svg)](https://github.com/astro-fusion/astro_research-white-paper/actions)

## 📥 Downloads

[![Download PDF](https://img.shields.io/badge/PDF-Open-blue?logo=adobe-acrobat-reader)](pdfs/NUMEROLOGY_ASTROLOGY_TEMPORAL_DISCONTINUITY.pdf)
[![Download DOCX](https://img.shields.io/badge/DOCX-Open-blue?logo=microsoft-word)](assets/releases/vedic-numerology-research-manuscript.docx)
[![Download HTML](https://img.shields.io/badge/HTML-Open-blue?logo=html5)](assets/releases/vedic-numerology-research-manuscript.html)

### 📖 Read the Research

**🌐 [Visit Research Website](https://astro-fusion.github.io/astro_research-white-paper/)**

Access our comprehensively referenced, peer-ready research manuscripts:

#### 🔬 Complete Research Collection (Direct PDF View)

| Research Paper                                                                               | Format | Description                                                             |
| -------------------------------------------------------------------------------------------- | ------ | ----------------------------------------------------------------------- |
| **[Master Research Report](pdfs/VEDIC_SYSTEMS_EMPIRICAL_ANALYSIS.pdf)**                      | PDF    | Consolidated 30+ page paper covering all research tracks                |
| **[Numerology-Astrology Correlation](pdfs/NUMEROLOGY_ASTROLOGY_TEMPORAL_DISCONTINUITY.pdf)** | PDF    | Temporal discontinuity analysis between discrete and continuous systems |
| **[Earthquake Prediction Analysis](pdfs/EARTHQUAKE_PREDICTION_INDIA_NEPAL_ANALYSIS.pdf)**    | PDF    | India-Nepal seismic pattern investigation                               |
| **[Gold Market Correlation](pdfs/GOLD_MARKET_PLANETARY_CORRELATION_ANALYSIS.pdf)**           | PDF    | XAU/USD price prediction analysis                                       |

#### 📄 Journal Styles (Generated via CI/CD)

- **[Nature-Style Manuscript](pdfs/manuscript_nature.pdf)**: Rigorous falsification of planetary predictors
- **IEEE-Style Manuscript** (Coming Soon): Technical evaluation in IEEE format

> **Note**: This repository contains multiple research use cases. Visit the [Reports Section](assets/reports/) for generated PDF reports or browse the [Source Code](src/) for implementation details.

---

## 📚 Documentation & Resources

- **[GitHub Wiki](https://github.com/astro-fusion/astro_research-white-paper/wiki)**: Comprehensive project knowledge base (Advanced Guides & Wiki Pages).
- **[Research Website](https://astro-fusion.github.io/astro_research-white-paper/)**: Access interactive reports and latest findings.
- **[Architecture Overview](docs/README.md)**: Explore the system design and documentation index.

## 📁 Repository Organization

This project is modularly organized to separate data, logic, and presentation:

| Directory          | Purpose                                     | Documentation                   |
| ------------------ | ------------------------------------------- | ------------------------------- |
| **`research/`**    | Research use cases, data, and reports.      | [README](research/README.md)    |
| **`application/`** | Web interface and API.                      | [README](application/README.md) |
| **`libs/`**        | Core astrological engines and shared logic. | [README](libs/README.md)        |
| **`ops/`**         | DevOps and configuration files.             |                                 |
| **`docs/`**        | Project documentation.                      | [README](docs/README.md)        |

## 🚀 Quick Start

### Local Installation

```bash
git clone https://github.com/astro-fusion/astro_research-white-paper.git
cd astro_research-white-paper
pip install -r ops/requirements.txt
python application/web/web.py  # Start the research interface
```

### 🔬 Running Analysis

```bash
python3 research/scripts/generate_artifacts.py  # Run the research pipeline
quarto render research/reports/comprehensive_thesis/COMPREHENSIVE_RESEARCH_THESIS.qmd  # Generate report
```

### 🧪 Testing

```bash
python3 tests/run_all_tests.py
```

---

_For detailed usage examples and technical specifications, please refer to the folder-specific READMEs listed above._
