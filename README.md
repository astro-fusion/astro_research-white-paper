# Vedic Astrology Core Library

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/astro-fusion/astro_research-white-paper/blob/main/notebooks/01_numerology_calculations.ipynb)
[![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Quarto](https://img.shields.io/badge/Quarto-1.3+-purple.svg)](https://quarto.org/)
[![CI/CD](https://github.com/astro-fusion/astro_research-white-paper/actions/workflows/ci.yml/badge.svg)](https://github.com/astro-fusion/astro_research-white-paper/actions)

## 📥 Downloads

[![Download PDF](https://img.shields.io/github/downloads/astro-fusion/astro_research-white-paper/total.svg?label=PDF%20Downloads&logo=adobe-acrobat-reader)](https://github.com/astro-fusion/astro_research-white-paper/releases/latest/download/vedic-numerology-research-manuscript.pdf)
[![Download DOCX](https://img.shields.io/github/downloads/astro-fusion/astro_research-white-paper/total.svg?label=DOCX%20Downloads&logo=microsoft-word)](https://github.com/astro-fusion/astro_research-white-paper/releases/latest/download/vedic-numerology-research-manuscript.docx)
[![Download HTML](https://img.shields.io/github/downloads/astro-fusion/astro_research-white-paper/total.svg?label=HTML%20Downloads&logo=html5)](https://github.com/astro-fusion/astro_research-white-paper/releases/latest/download/vedic-numerology-research-manuscript.html)

### 📖 Read the Research

**🌐 [View Online](https://astro-fusion.github.io/astro_research-white-paper/)** | **[📄 Download PDF](https://github.com/astro-fusion/astro_research-white-paper/releases/latest/download/vedic-numerology-research-manuscript.pdf)** | **[📝 Download DOCX](https://github.com/astro-fusion/astro_research-white-paper/releases/latest/download/vedic-numerology-research-manuscript.docx)**

A comprehensive Python library for Vedic Astrology (Parashari Jyotish) calculations using high-precision Swiss Ephemeris. This core library provides the foundation for astrological analysis and can be extended by use cases like numerology correlations, earthquake studies, and other research applications.

## 🌟 Key Features

### 🪐 **Core Vedic Astrology Engine**
- **Swiss Ephemeris Backend**: Astronomical precision with 0.1 arcsecond accuracy
- **Lahiri Ayanamsa**: Traditional Chitra Paksha ayanamsa system
- **Complete Birth Charts**: All planets, lunar nodes, houses, and key points

### 📊 **Dignity & Strength Analysis**
- **Classical Dignity Scoring**: Moolatrikona, own sign, exaltation analysis
- **Quantitative Strength Metrics**: 0-100 planetary power calculations
- **Aspect Analysis**: Planetary relationships and influence patterns

### 📈 **Temporal Dynamics**
- **Transit Analysis**: Current planetary influences on natal positions
- **Dasha Period Calculations**: Major and sub-period influence mapping
- **Time Series Analysis**: How planetary strengths evolve over time

### 🎨 **Advanced Visualizations**
- **Interactive Charts**: Plotly-powered dynamic visualizations
- **Publication-Ready Graphics**: High-DPI static plots for research papers
- **Birth Chart Diagrams**: Traditional and modern chart representations

### 🔧 **Extensible Architecture**
- **Use Case Framework**: Easy to add new research applications
- **Modular Design**: Core astrology separate from specific analyses
- **API-First**: REST API and Python library interfaces

### ☁️ **Multi-Platform Support**
- **Google Colab Ready**: Zero-setup cloud execution
- **Local Development**: Full local environment support
- **Container Ready**: Docker and Podman compatibility

## 📋 Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Usage Examples](#usage-examples)
- [Google Colab Setup](#google-colab-setup)
- [Local Development](#local-development)
- [PDF Report Generation](#pdf-report-generation)
- [Project Structure](#project-structure)
- [API Documentation](#api-documentation)
- [Testing](#testing)
- [Contributing](#contributing)
- [License](#license)

## 🚀 Quick Start

### ⚡ 5-Minute Setup (Google Colab)

The fastest way to get started - no installation required!

1. **Click the Colab Badge** above or visit [Google Colab](https://colab.research.google.com/)
2. **Run the Installation**:
   ```python
   !pip install git+https://github.com/astro-fusion/astro_research-white-paper.git
   ```
3. **Execute Your First Analysis**:
   ```python
   from vedic_astrology_core import create_birth_chart

# Create a birth chart
chart = create_birth_chart("1984-08-27", "10:30", 28.6139, 77.1025)
print(f"Ascendant: {chart.chart.ascendant.sign_name}")

# For numerology analysis, see the numerology use case
   ```

### 🖥️ Local Development Setup

#### Prerequisites
- **Python 3.8+** - Core runtime
- **Git** - Version control
- **Quarto** (optional) - For building documentation

#### One-Command Setup
```bash
# Clone and setup in one command
git clone https://github.com/astro-fusion/astro_research-white-paper.git
cd astro_research-white-paper
make setup-dev
```

#### Manual Installation Steps

**1. Clone Repository**
```bash
git clone https://github.com/astro-fusion/astro_research-white-paper.git
cd astro_research-white-paper
```

**2. Install Python Dependencies**
```bash
# Core dependencies only
pip install -r requirements.txt

# Full development setup (recommended)
pip install -e ".[dev]"

# Include Colab features
pip install -r requirements-colab.txt
```

**3. Install Swiss Ephemeris** (Required for astrology calculations)
```bash
# Ubuntu/Debian
sudo apt-get update && sudo apt-get install -y libswisseph-dev

# macOS with Homebrew
brew install swisseph

# Or install Python wrapper
pip install pyswisseph>=2.08.00
```

**4. Verify Installation**
```bash
# Run quick test
python -c "from vedic_numerology import analyze_birth_chart; print('✅ Installation successful!')"

# Run test suite
make test
```

### 🐳 Docker Setup (Advanced)

For isolated development environments:

```bash
# Build container
docker build -t vedic-numerology .

# Run interactive session
docker run -it --rm vedic-numerology

# Mount local files
docker run -it --rm -v $(pwd):/app vedic-numerology
```

## 💡 Usage Examples

### 🪐 Basic Astrology Analysis

Get started with fundamental astrological calculations:

```python
from vedic_astrology_core import create_birth_chart

# Create a birth chart
chart = create_birth_chart("1984-08-27", "10:30", 28.6139, 77.1025)

# Basic chart information
print(f"Ascendant: {chart.chart.ascendant.sign_name}")
print(f"Moon sign: {chart.chart.planets['MOON'].sign.name}")

# Planetary dignity analysis
mars_dignity = chart.score_dignity('MARS')
print(f"Mars dignity score: {mars_dignity['score']:.1f}/100")

# Generate chart report
report = chart.generate_chart_report()
print(report)
```

### 🔢 Numerology Use Case

For numerology analysis, see the dedicated use case:

```python
# In the numerology use case environment
from numerology import calculate_complete_numerology

# Calculate numerology
numerology = calculate_complete_numerology("1984-08-27", "10:30", 28.6139, 77.1025)
print(f"Mulanka: {numerology['mulanka']['number']}")
print(f"Bhagyanka: {numerology['bhagyanka']['number']}")
```

### 📊 Advanced Data Analysis Workflows

#### Temporal Trend Analysis
```python
from vedic_numerology import VedicNumerologyAstrology
from datetime import datetime

# Analyze how numerological support changes over time
vna = VedicNumerologyAstrology("1984-08-27", "10:30", 28.6139, 77.1025)

# Generate time series data
fig = vna.plot_temporal_support(
    start_date="2024-01-01",
    end_date="2024-12-31",
    use_plotly=True
)
fig.show()
```

#### Comparative Studies
```python
# Compare multiple birth charts
subjects = [
    {"name": "Person A", "date": "1984-08-27", "time": "10:30", "lat": 28.6139, "lon": 77.1025},
    {"name": "Person B", "date": "1990-05-15", "time": "14:20", "lat": 40.7128, "lon": -74.0060},
]

results = []
for subject in subjects:
    vna = VedicNumerologyAstrology(
        birth_date=subject["date"],
        birth_time=subject["time"],
        latitude=subject["lat"],
        longitude=subject["lon"]
    )

    analysis = vna.analyze_support_contradiction()
    results.append({
        "name": subject["name"],
        "mulanka_support": analysis['mulanka']['support_level'],
        "bhagyanka_support": analysis['bhagyanka']['support_level']
    })

# Create comparison visualization
import plotly.express as px
df = pd.DataFrame(results)
fig = px.bar(df, x='name', y=['mulanka_support', 'bhagyanka_support'],
             title="Comparative Numerological Support Analysis")
fig.show()
```

### 🪐 Advanced Astrology Integration

Combine numerology with full astrological analysis:

```python
from vedic_numerology import VedicNumerologyAstrology

# Create detailed analysis object
vna = VedicNumerologyAstrology(
    birth_date="1984-08-27",
    birth_time="10:30",
    latitude=28.6139,    # Delhi latitude
    longitude=77.1025,   # Delhi longitude
    ayanamsa_system="lahiri"
)

# Get planetary support analysis
support_analysis = vna.analyze_support_contradiction()

print("🎯 Numerological Support Analysis:")
print(f"  Mulanka ({support_analysis['mulanka']['planet']}): {support_analysis['mulanka']['support_level']}")
print(f"  Bhagyanka ({support_analysis['bhagyanka']['planet']}): {support_analysis['bhagyanka']['support_level']}")
print(f"  Overall Harmony: {support_analysis['overall']['harmony_level']}")

# Access detailed planetary data
chart = vna.chart
mars_dignity = vna.score_dignity('MARS')
print(f"Mars dignity score: {mars_dignity['score']:.1f}/100 ({mars_dignity['dignity_type']})")
```

## 📊 Usage Examples

### 1. Complete Birth Chart Analysis

```python
from vedic_numerology import VedicNumerologyAstrology
from datetime import date

# Initialize with birth data
vna = VedicNumerologyAstrology(
    birth_date=date(1984, 8, 27),
    birth_time="10:30:00",
    latitude=28.6139,   # Delhi latitude
    longitude=77.1025,  # Delhi longitude
)

# Calculate numerology
print("=== NUMEROLOGY ===")
mulanka = vna.calculate_mulanka()
bhagyanka = vna.calculate_bhagyanka()
print(f"Mulanka: {mulanka['number']} ({mulanka['planet'].name})")
print(f"Bhagyanka: {bhagyanka['number']} ({bhagyanka['planet'].name})")

# Analyze planetary support
print("\\n=== PLANETARY SUPPORT ===")
support = vna.analyze_support_contradiction()
print(f"Mulanka ({support['mulanka']['planet']}): {support['mulanka']['support_level']}")
print(f"Bhagyanka ({support['bhagyanka']['planet']}): {support['bhagyanka']['support_level']}")

# Generate visualizations
print("\\n=== VISUALIZATIONS ===")
# Time series of planetary support
vna.plot_temporal_support("2024-01-01", "2024-12-31")

# Comparison chart
vna.plot_numerology_comparison()

# Complete report
print("\\n=== COMPLETE REPORT ===")
report = vna.generate_report()
print(report)
```

### 2. Research Analysis with Custom Parameters

```python
# Advanced configuration
from vedic_numerology.config import Config

# Load custom configuration
config = Config()
config.set('ayanamsa_system', 'raman')  # Use Raman Ayanamsa
config.set('visualization.default_library', 'plotly')  # Use interactive plots

# Analysis with custom settings
vna = VedicNumerologyAstrology(
    birth_date="1990-05-15",
    birth_time="14:20",
    latitude=40.7128,   # New York
    longitude=-74.0060,
    ayanamsa_system="raman"
)

# Research-focused analysis
chart = vna.chart  # Access full birth chart
mars_dignity = vna.score_dignity('MARS')
print(f"Mars dignity score: {mars_dignity['score']}/100")
print(f"Dignity type: {mars_dignity['dignity_type']}")
```

## 🥼 Google Colab Setup

### Running Notebooks in Google Colab

1. **Open Google Colab**: Go to [colab.research.google.com](https://colab.research.google.com)

2. **Install the Package**:
   ```python
   # Run this in the first Colab cell
   !pip install git+https://github.com/astro-fusion/astro_research-white-paper.git
   ```

3. **Run Tutorial Notebooks**:
   - [01_numerology_calculations.ipynb](notebooks/01_numerology_calculations.ipynb) - Basic numerology
   - [02_astrology_calculations.ipynb](notebooks/02_astrology_calculations.ipynb) - Astrology integration
   - [03_dignity_scoring.ipynb](notebooks/03_dignity_scoring.ipynb) - Dignity analysis
   - [04_visualization_demo.ipynb](notebooks/04_visualization_demo.ipynb) - Charts and graphs
   - [05_complete_analysis.ipynb](notebooks/05_complete_analysis.ipynb) - Full workflow

4. **Share Your Analysis**:
   - Click "Share" button in Colab
   - Generate shareable link
   - Others can run your analysis instantly

### Sharing Colab Notebooks

To share your analysis:

1. **Save to GitHub**:
   ```bash
   # Upload notebooks to your GitHub repository
   git add notebooks/
   git commit -m "Add analysis notebooks"
   git push origin main
   ```

2. **Direct Colab Links**:
   ```
   https://colab.research.google.com/github/YOUR_USERNAME/YOUR_REPO/blob/main/notebooks/01_numerology_calculations.ipynb
   ```

3. **Embed in Documentation**:
   ```markdown
   [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](YOUR_COLAB_LINK)
   ```

## 🚀 Deployment & Publishing

### Multi-Format Publishing Strategy

Your research platform supports **three deployment channels** for maximum reach:

#### 1. 📖 **Static Research Site** (GitHub Pages)
- **Purpose**: Primary research dissemination
- **Content**: Manuscripts, documentation, interactive components
- **Access**: `https://astro-fusion.github.io/astro_research-white-paper/`

#### 2. 🎮 **Interactive Web App** (Streamlit Cloud)
- **Purpose**: Real-time exploration and analysis
- **Features**: Live calculators, dynamic visualizations, data export
- **Access**: `https://share.streamlit.io/astro-fusion/numerology-app/main/app.py`

#### 3. 📚 **Academic Publications**
- **PDF**: Traditional research paper format
- **HTML**: Web-optimized with cross-references
- **DOCX**: Collaborative editing format

### Automated Deployment

#### GitHub Actions Workflows

**Deploy Static Site:**
```yaml
# .github/workflows/deploy-platform.yml
# Deploys to GitHub Pages automatically on main branch push
```

**Manual Deployment Options:**
```bash
# Deploy everything
gh workflow run deploy-platform.yml -f deploy_target=both

# Deploy only static content
gh workflow run deploy-platform.yml -f deploy_target=static-only

# Deploy only interactive app
gh workflow run deploy-platform.yml -f deploy_target=app-only
```

#### Local Deployment Testing

**Test Static Site Locally:**
```bash
# Build all content
make build-all

# Serve locally
cd _site && python -m http.server 8000
# Visit: http://localhost:8000
```

**Test Streamlit App Locally:**
```bash
# Install Streamlit
pip install streamlit

# Run the app
streamlit run app.py

# Access at: http://localhost:8501
```

## 🛠️ Development & Building

### Build System Overview

This project uses a comprehensive build system inspired by modern documentation projects:

- **📦 Build Scripts**: Automated building for multiple formats
- **🔍 Quality Gates**: Automated code quality and testing
- **📋 Make Targets**: Simplified development workflow
- **🔄 CI/CD**: Automated testing and deployment

### Quick Development Setup

```bash
# One-command setup
make setup-dev

# Or manually:
git clone https://github.com/astro-fusion/astro_research-white-paper.git
cd astro_research-white-paper
pip install -r requirements.txt
pip install -e ".[dev]"
```

### Build Commands

#### Using Make (Recommended)
```bash
# Show all available commands
make help

# Quick build (HTML + PDF)
make build

# Build specific formats
make build-html    # HTML only
make build-pdf     # PDF only
make build-docx    # Word document

# Quality checks
make test         # Run tests
make lint         # Code quality
make format       # Auto-format code
make quality-gate # Full quality check

# Development
make clean        # Clean build artifacts
make docs         # Build API documentation
```

#### Using Build Scripts
```bash
# Simple single-format build
./build.sh html

# Comprehensive build with all checks
./build-all.sh

# Build including notebook execution
./build-all.sh --notebooks

# Check system requirements
./build.sh check
```

### Development Workflow

#### 1. **Local Development**
```bash
# Start with fresh environment
make setup-dev

# Work on code with auto-reload
# Edit files in src/vedic_numerology/

# Run tests continuously
pytest-watch tests/

# Preview manuscript changes
quarto preview manuscript.qmd
```

#### 2. **Code Quality**
```bash
# Auto-format code
make format

# Run quality checks
make quality-gate

# Check specific files
black --check src/vedic_numerology/calculator.py
mypy src/vedic_numerology/calculator.py
```

#### 3. **Testing Strategy**
```bash
# Unit tests
pytest tests/test_numerology.py -v

# Integration tests
pytest tests/test_integration.py -v

# With coverage
pytest --cov=vedic_numerology --cov-report=html

# Open coverage report
open htmlcov/index.html
```

#### 4. **Documentation**
```bash
# Build API docs
make docs

# Serve docs locally
make serve-docs

# Preview manuscript
quarto preview manuscript.qmd
```

### Advanced Development

#### Running Notebooks
```bash
# Execute all notebooks
make build-notebooks

# Start Jupyter server
jupyter notebook

# Open specific notebook
# notebooks/01_numerology_calculations.ipynb
```

#### Performance Profiling
```bash
# Profile specific function
python -c "
import cProfile
from vedic_numerology import analyze_birth_chart
cProfile.run('analyze_birth_chart(\"1984-08-27\", \"10:30\", 28.6139, 77.1025)')
"
```

#### Debugging
```bash
# Debug specific test
pytest tests/test_numerology.py::TestNumerologyCalculations::test_calculate_mulanka -s -v

# Enable debug logging
PYTHONPATH=src python -c "
import logging
logging.basicConfig(level=logging.DEBUG)
# Your debug code here
"
```

### Build Artifacts

After successful builds, artifacts are available in:

```
_book/
├── html/           # Web version with interactivity
├── pdf/            # Print-ready PDF
├── docx/           # Microsoft Word format
└── epub/           # E-reader format

htmlcov/            # Test coverage reports
docs/_build/        # API documentation
build-report-*.md   # Build logs and reports
```

### Troubleshooting

#### Build Issues
```bash
# Check Quarto installation
quarto check

# Validate YAML configuration
python -c "import yaml; yaml.safe_load(open('_quarto.yml'))"

# Test Python imports
python -c "from vedic_numerology import analyze_birth_chart"
```

#### PDF Build Problems
```bash
# Install/update TinyTeX
quarto install tinytex

# Check LaTeX packages
tlmgr install geometry fontspec

# Debug PDF build
quarto render manuscript.qmd --to pdf --log-level debug
```

#### Test Failures
```bash
# Run with detailed output
pytest -v --tb=long

# Debug specific failure
pytest tests/test_numerology.py -k "mulanka" -s

# Check dependencies
pip check
```

## 🌐 Interactive Research Platform

Your project now supports **multiple deployment formats** for maximum accessibility and engagement:

### 📊 **1. Static Research Publications**
- **PDF Downloads**: Traditional academic paper format for citations and printing
- **HTML Manuscripts**: Web-optimized versions with cross-references and navigation
- **DOCX Format**: Microsoft Word compatible for collaborative editing

### 🎮 **2. Interactive Web Experience**
- **Embedded Interactive Components**: Live calculators and visualizations in the manuscript
- **Streamlit Web App**: Full-featured application with real-time controls
- **Dynamic Visualizations**: Plotly-powered charts that respond to user input

### 🔧 **3. Developer Resources**
- **API Documentation**: Complete Sphinx-generated documentation
- **Jupyter Notebooks**: Executable computational narratives
- **Google Colab Integration**: Zero-setup cloud execution

## 📄 Research Content Formats

### Academic Publications
```bash
# Generate all formats
make build

# Individual formats
make build-pdf     # Research paper PDF
make build-html    # Web manuscript
make build-docx    # Word document
```

### Interactive Experience
```bash
# Run local Streamlit app
streamlit run app.py

# Access interactive components
# Visit: manuscript.html#interactive-controls
```

### Developer Documentation
```bash
# Build API docs
make docs

# View at: docs/_build/html/index.html
```

## 📄 PDF Report Generation

### Using Quarto (Recommended)

The project includes Quarto integration for generating scientific PDF reports.

#### Prerequisites
```bash
# Install Quarto
# Download from: https://quarto.org/docs/get-started/

# Or using Homebrew (macOS):
brew install quarto

# Or using conda:
conda install -c conda-forge quarto
```

#### Generate PDF Report

1. **Update Manuscript**:
   ```bash
   # Edit manuscript.qmd with your analysis
   # Include code chunks and visualizations
   ```

2. **Render PDF**:
   ```bash
   # Generate PDF from manuscript
   quarto render manuscript.qmd --to pdf

   # Or render all formats
   quarto render
   ```

3. **Include Dynamic Results**:
   ```qmd
   # manuscript.qmd

   ```{python}
   from vedic_numerology import analyze_birth_chart

   analysis = analyze_birth_chart("1984-08-27")
   results = analysis.analyze_support_contradiction()
   ```

   The analysis shows that Mulanka support is `{python} results['mulanka']['support_level']`
   and Bhagyanka support is `{python} results['bhagyanka']['support_level']`.
   ```

#### Embed Visualizations in PDF

```qmd
# manuscript.qmd

```{python}
#| label: fig-mulanka-support
#| fig-cap: "Mulanka planetary support over time"

from vedic_numerology import VedicNumerologyAstrology

vna = VedicNumerologyAstrology("1984-08-27", "10:30", 28.6139, 77.1025)
vna.plot_temporal_support("2024-01-01", "2024-06-01")
```
```

### Using Python Directly

```python
from vedic_numerology import VedicNumerologyAstrology
import matplotlib.pyplot as plt

# Generate analysis
vna = VedicNumerologyAstrology("1984-08-27", "10:30", 28.6139, 77.1025)

# Create visualizations
fig1 = vna.plot_temporal_support(use_plotly=False)
plt.savefig('temporal_support.pdf')

fig2 = vna.plot_numerology_comparison(use_plotly=False)
plt.savefig('comparison.pdf')

# Generate text report
report = vna.generate_report()
with open('analysis_report.txt', 'w') as f:
    f.write(report)
```

## 📊 Generated Reports and PDFs

### Automated Workflow Artifacts

This repository includes automated workflows that generate research manuscripts and analysis reports. The following artifacts are available as GitHub Actions outputs:

#### 📋 Research Manuscript PDF
- **File**: `manuscript.pdf`
- **Workflow**: [Research PDF Generation](https://github.com/astro-fusion/astro_research-white-paper/actions/workflows/research-pdf.yml)
- **Contents**: Complete research paper with integrated analysis results
- **Download**: Available as workflow artifact `research-manuscript-pdf`

#### 📈 Analysis Reports
- **File**: `research_results.json`
- **Workflow**: [Research PDF Generation](https://github.com/astro-fusion/astro_research-white-paper/actions/workflows/research-pdf.yml)
- **Contents**: Raw analysis data and computational results
- **Download**: Available as workflow artifact `research-data-reports`

#### 📊 Research Summary
- **File**: `RESEARCH_SUMMARY.md`
- **Workflow**: [Publish Research](https://github.com/astro-fusion/astro_research-white-paper/actions/workflows/publish-research.yml)
- **Contents**: Executive summary of research findings and methodology
- **Download**: Available as workflow artifact `research-release-artifacts`

#### 📉 Data Analysis Results
- **File**: `analysis_results/` (directory)
- **Workflow**: [Data Analysis](https://github.com/astro-fusion/astro_research-white-paper/actions/workflows/data-analysis.yml)
- **Contents**: Statistical analysis and research data processing results
- **Download**: Available as workflow artifact `data-analysis-results-{run_number}`

### Accessing Generated Files

#### From GitHub Actions
1. Go to the [Actions tab](https://github.com/astro-fusion/astro_research-white-paper/actions)
2. Click on the latest successful workflow run
3. Scroll down to the "Artifacts" section
4. Download the desired artifact files

#### From Latest Release
- Visit the [Releases page](https://github.com/astro-fusion/astro_research-white-paper/releases)
- Download the latest release assets which include compiled PDFs and reports

#### Automated Generation
Workflows automatically generate these files on:
- Push to `main` branch (research PDFs)
- Manual workflow dispatch (custom analysis)
- Release creation (comprehensive research packages)

## 📁 Project Structure

```
vedic-astrology-core/
├── src/vedic_astrology_core/       # Core astrology library
│   ├── astrology/                  # Swiss Ephemeris integration
│   ├── dignity/                    # Planetary dignity scoring
│   ├── visualization/              # Generic visualization utilities
│   ├── utils/                      # Core utilities
│   └── config/                     # Configuration
├── use_cases/                      # Research use cases
│   ├── numerology/                 # Numerology correlation studies
│   │   ├── src/numerology/         # Numerology calculations
│   │   ├── manuscripts/            # Research manuscripts
│   │   ├── notebooks/              # Analysis notebooks
│   │   ├── scripts/                # Analysis scripts
│   │   ├── data/                   # Research data
│   │   └── figures/                # Generated figures
│   └── earthquake/                 # Future: Earthquake studies
├── api.py                          # REST API server
├── app.py                          # Streamlit web application
├── tests/                          # Test suite
├── docs/                           # API documentation
├── _quarto.yml                     # Shared Quarto configuration
├── styles/                         # Shared styling
├── pyproject.toml                  # Python package configuration
├── requirements*.txt               # Dependencies
└── README.md                       # This file
```

### 🏗️ **Architecture Overview**

- **Core Library** (`src/vedic_astrology_core/`): Domain-agnostic astrology calculations
- **Use Cases** (`use_cases/`): Specific research applications that extend the core
- **API/Web** (`api.py`, `app.py`): Interfaces for accessing functionality
- **Documentation** (`docs/`, manuscripts): Research papers and API docs

## 🔧 Adding New Use Cases

The project is designed to easily accommodate new research applications. To add a new use case:

1. **Create Use Case Structure**:
   ```bash
   mkdir -p use_cases/your_use_case/{src,manuscripts,notebooks,scripts,data,figures}
   ```

2. **Implement Use Case Logic**:
   - Add your calculations in `use_cases/your_use_case/src/`
   - Import from `vedic_astrology_core` for astrology functionality
   - Follow the same structure as the numerology use case

3. **Create Research Manuscripts**:
   - Add Quarto manuscripts in `use_cases/your_use_case/manuscripts/`
   - Copy and customize `_quarto.yml` for your specific needs

4. **Build and Test**:
   ```bash
   ./build.sh your_use_case    # Build specific use case
   ./build-all.sh              # Build all use cases
   ```

### 📚 **Example Use Cases**
- **Numerology**: Planetary correlations with numerological numbers
- **Earthquake Studies**: Astrological patterns in seismic activity
- **Financial Markets**: Planetary influences on market trends
- **Weather Patterns**: Astronomical correlations with climate

## 📚 API Documentation

### Core Classes

- **`VedicNumerologyAstrology`**: Main analysis class
- **`EphemerisEngine`**: Swiss Ephemeris wrapper
- **`DignityScorer`**: Planetary dignity calculation
- **`BirthChart`**: Complete birth chart object

### Key Methods

- `calculate_mulanka()`: Birth number calculation
- `calculate_bhagyanka()`: Destiny number calculation
- `analyze_support_contradiction()`: Support analysis
- `plot_temporal_support()`: Time series visualization
- `generate_report()`: Complete analysis report

### Configuration

```python
from vedic_numerology.config import Config

config = Config()
config.set('ayanamsa_system', 'lahiri')
config.set('visualization.default_library', 'plotly')
```

## 🧪 Testing

### Run Test Suite

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=vedic_numerology --cov-report=html

# Run specific tests
pytest tests/test_numerology.py
pytest tests/test_integration.py::TestMars1984Case
```

### Test Categories

- **Unit Tests**: Individual function testing
- **Integration Tests**: End-to-end workflow testing
- **Reference Tests**: Validation against known cases (Mars 1984)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes and add tests
4. Run the test suite: `pytest`
5. Commit your changes: `git commit -am 'Add feature'`
6. Push to the branch: `git push origin feature-name`
7. Submit a pull request

### Development Guidelines

- Follow PEP 8 style guidelines
- Add tests for new functionality
- Update documentation for API changes
- Use type hints for new functions
- Maintain backward compatibility

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Swiss Ephemeris by Astrodienst for astronomical calculations
- Vedic astrology tradition for the theoretical foundation
- Open source community for the libraries and tools

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/astro-fusion/astro_research-white-paper/issues)
- **Discussions**: [GitHub Discussions](https://github.com/astro-fusion/astro_research-white-paper/discussions)
- **Documentation**: [Read the Docs](https://astro_research-white-paper.readthedocs.io/)

---

**Note**: This system is designed for research and educational purposes. Always consult qualified astrologers for personal astrological advice.

---

## 🔌 REST API Access

### Deployed API Endpoints

The Vedic Numerology-Astrology API is available through multiple deployment options:

#### 🚀 **FastAPI on Render** (Recommended)
```bash
# Deployed at: https://your-app-name.onrender.com
curl https://your-app-name.onrender.com/api/v1/health

# Interactive API docs
# Visit: https://your-app-name.onrender.com/docs
```

#### ⚡ **GitHub Actions Webhook API** (Free)
```bash
# Trigger calculation via GitHub Actions
curl -X POST \
  -H "Authorization: token YOUR_GITHUB_TOKEN" \
  https://api.github.com/repos/astro-fusion/astro_research-white-paper/dispatches \
  -d '{"event_type": "calculate-numerology", "client_payload": {"birth_date": "1984-08-27"}}'
```

> **⚠️ Security Note**: Use fine-grained personal access tokens with minimum required scopes. See [API_DEPLOYMENT.md](API_DEPLOYMENT.md) for detailed security guidelines.

#### 🎮 **Streamlit Web App**
```bash
# Interactive web application
# Visit: https://share.streamlit.io/astro-fusion/numerology-app/main/app.py
```

### API Usage Examples

#### Calculate Complete Analysis
```python
import requests

response = requests.post("https://vedic-numerology-api.onrender.com/api/v1/analysis", json={
    "birth_date": "1984-08-27",
    "birth_time": "10:30",
    "latitude": 28.6139,
    "longitude": 77.1025
})

result = response.json()
print(f"Mulanka: {result['numerology']['mulanka']['number']}")
```

#### JavaScript Integration
```html
<script src="api-client.js"></script>
<script>
const vedicAPI = new VedicNumerologyAPI();

const result = await vedicAPI.completeAnalysis({
    birth_date: "1984-08-27",
    birth_time: "10:30",
    latitude: 28.6139,
    longitude: 77.1025
});

console.log("Results:", result);
</script>
```

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/analysis` | Complete numerology + astrology analysis |
| `POST` | `/api/v1/numerology` | Numerology calculations only |
| `POST` | `/api/v1/astrology` | Astrology calculations only |
| `GET` | `/api/v1/health` | API health check |
| `GET` | `/docs` | Interactive API documentation |

### Self-Hosting

For self-hosting the API:

```bash
# Install API dependencies
pip install -r requirements-api.txt

# Start FastAPI server
uvicorn api:app --reload

# API available at: http://localhost:8000
# Documentation at: http://localhost:8000/docs
```

📖 **Full API Documentation**: See [`API_DEPLOYMENT.md`](API_DEPLOYMENT.md) for deployment guides and advanced usage.