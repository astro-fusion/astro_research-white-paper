# Vedic Numerology-Astrology Integration System

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/astro-fusion/numerology-white-paper/blob/main/notebooks/01_numerology_calculations.ipynb)

A comprehensive Python package for integrating Vedic Numerology (Anka Jyotish) with Vedic Astrology (Parashari Jyotish) using Swiss Ephemeris calculations. This system provides quantitative analysis of how planetary positions support or contradict numerological potentials.

## 🌟 Features

- **Vedic Numerology**: Mulanka (Birth Number) and Bhagyanka (Destiny Number) calculations with sunrise correction
- **Sidereal Astrology**: High-precision planetary positions using Swiss Ephemeris and Lahiri Ayanamsa
- **Dignity Scoring**: 0-100 quantitative planetary strength analysis with classical Vedic parameters
- **Temporal Analysis**: Visualize how numerological support changes over time
- **Interactive Visualizations**: Charts and graphs for research and analysis
- **Google Colab Ready**: Cloud-based execution with no local setup required

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

## 🚀 Installation

### Option 1: Google Colab (Recommended for Beginners)

1. Click the Colab badge above or go to [Google Colab](https://colab.research.google.com/)
2. Upload and run the tutorial notebooks:
   ```bash
   # In Colab cell:
   !pip install git+https://github.com/astro-fusion/numerology-white-paper.git
   ```

### Option 2: Local Installation

#### Prerequisites
- Python 3.8+
- pip package manager

#### Install Core Package
```bash
# Clone the repository
git clone https://github.com/astro-fusion/numerology-white-paper.git
cd vedic-numerology-astrology

# Install with pip
pip install -e .
```

#### Install with All Dependencies (Recommended)
```bash
# Install core dependencies
pip install -r requirements.txt

# Or install with all optional dependencies
pip install -e ".[all]"
```

#### Install Google Colab Dependencies (for local Colab-like experience)
```bash
pip install -r requirements-colab.txt
```

## 💡 Quick Start

### Basic Numerology Analysis

```python
from vedic_numerology import analyze_birth_chart

# Analyze birth data
analysis = analyze_birth_chart("1984-08-27", "10:30", 28.6139, 77.1025)

# Get numerology results
mulanka = analysis.calculate_mulanka()      # Returns: 9 (Mars)
bhagyanka = analysis.calculate_bhagyanka()  # Returns: 3 (Jupiter)

# Generate complete report
report = analysis.generate_report()
print(report)
```

### Advanced Astrology Integration

```python
from vedic_numerology import VedicNumerologyAstrology

# Create detailed analysis
vna = VedicNumerologyAstrology(
    birth_date="1984-08-27",
    birth_time="10:30",
    latitude=28.6139,    # Delhi
    longitude=77.1025,   # Delhi
    ayanamsa_system="lahiri"
)

# Get planetary support analysis
support_analysis = vna.analyze_support_contradiction()
print(f"Mulanka Support: {support_analysis['mulanka']['support_level']}")
print(f"Bhagyanka Support: {support_analysis['bhagyanka']['support_level']}")
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
   !pip install git+https://github.com/astro-fusion/numerology-white-paper.git
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

## 💻 Local Development

### Development Setup

```bash
# Clone repository
git clone https://github.com/astro-fusion/numerology-white-paper.git
cd vedic-numerology-astrology

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\\Scripts\\activate

# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest

# Run specific test
pytest tests/test_numerology.py::TestNumerologyCalculations::test_calculate_mulanka_basic
```

### Running Jupyter Notebooks Locally

```bash
# Install Jupyter
pip install jupyter notebook

# Start Jupyter server
jupyter notebook

# Open notebooks/01_numerology_calculations.ipynb
```

### Code Quality

```bash
# Format code
black src/ tests/

# Sort imports
isort src/ tests/

# Type checking
mypy src/

# Run full test suite
pytest --cov=vedic_numerology --cov-report=html
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

## 📁 Project Structure

```
numerology-white-paper/
├── src/vedic_numerology/          # Main package
│   ├── numerology/                 # Numerology calculations
│   ├── astrology/                  # Astronomical calculations
│   ├── dignity/                    # Planetary dignity scoring
│   ├── visualization/              # Charts and graphs
│   ├── utils/                      # Utilities
│   └── config/                     # Configuration
├── notebooks/                      # Jupyter notebooks
├── tests/                          # Test suite
├── docs/                           # Documentation
├── config/                         # Configuration files
├── manuscript.qmd                  # Quarto manuscript
├── pyproject.toml                  # Modern Python packaging
├── requirements.txt                # Dependencies
└── README.md                       # This file
```

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

- **Issues**: [GitHub Issues](https://github.com/astro-fusion/numerology-white-paper/issues)
- **Discussions**: [GitHub Discussions](https://github.com/astro-fusion/numerology-white-paper/discussions)
- **Documentation**: [Read the Docs](https://numerology-white-paper.readthedocs.io/)

---

**Note**: This system is designed for research and educational purposes. Always consult qualified astrologers for personal astrological advice.