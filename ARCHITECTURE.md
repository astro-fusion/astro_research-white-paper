# 🏗️ Astro-Research Project Architecture

**Version**: 2.0 (Reorganized)  
**Last Updated**: January 2026  
**Purpose**: Comprehensive guide to project structure, organization, and development workflow

---

## 📋 Table of Contents
1. [Directory Structure](#directory-structure)
2. [Folder Descriptions](#folder-descriptions)
3. [Core Modules](#core-modules)
4. [Development Workflow](#development-workflow)
5. [Adding New Features](#adding-new-features)
6. [File Organization Guidelines](#file-organization-guidelines)

---

## 📁 Directory Structure

```
astro-research/
│
├── 📖 docs/                              # All project documentation
│   ├── guides/                           # User guides & setup instructions
│   │   ├── QUICK_START_RESEARCH.md      # Getting started guide
│   │   ├── REAL_TIME_VISUALIZATION_GUIDE.md
│   │   ├── RESEARCH_REPORT_GUIDE.md
│   │   └── API_DEPLOYMENT.md            # Deployment instructions
│   │
│   ├── research/                         # Research findings & analysis
│   │   ├── RESEARCH_COMPLETION_SUMMARY.md
│   │   ├── RESEARCH_DATA_REFERENCE.md
│   │   ├── RESEARCH_PAPER_TEMPLATE.md
│   │   └── PLANETARY_STRENGTH_VISUALIZATION.md
│   │
│   ├── framework/                        # Architecture & framework docs
│   │   ├── MULTI_USE_CASE_FRAMEWORK.md  # Scalable framework design
│   │   ├── EARTHQUAKE_DATA_INTEGRATION.md
│   │   ├── PROJECT_UPDATE_SUMMARY.md
│   │   └── QUICK_REFERENCE_CARD.md
│   │
│   ├── architecture/                     # System design documentation
│   │   └── (detailed design specifications)
│   │
│   ├── INDEX.md                          # Documentation index
│   └── CONTRIBUTING.md                   # Contribution guidelines
│
├── 🔨 scripts/                           # Executable scripts & automation
│   ├── build/                            # Build automation scripts
│   │   ├── build.sh                      # Standard build
│   │   └── build-all.sh                  # Complete build pipeline
│   │
│   ├── generate/                         # Data & asset generation
│   │   ├── create_planetary_strength_graph.py
│   │   ├── generate-assets.py
│   │   └── generate_research_report.py
│   │
│   └── utilities/                        # Utility scripts (future)
│
├── 🌐 src/                               # Source code (application logic)
│   ├── api/                              # REST API implementation
│   │   ├── api.py                        # Flask/FastAPI endpoints
│   │   └── api-client.js                 # JavaScript client
│   │
│   ├── web/                              # Web application
│   │   ├── app.py                        # Main web application
│   │   └── web.py                        # Web utilities
│   │
│   └── utils/                            # Shared utilities (future)
│       └── (helper functions, constants)
│
├── 📓 notebooks/                         # Jupyter & Colab notebooks
│   ├── analysis/                         # Data analysis notebooks
│   ├── exploration/                      # Exploratory notebooks
│   └── test.qmd                          # Quarto test document
│
├── 🔬 use_cases/                         # Use case implementations
│   ├── numerology/                       # ✅ COMPLETE
│   │   ├── scripts/                      # Analysis scripts
│   │   ├── data/                         # Numerology data
│   │   └── manuscripts/                  # Research documents
│   │
│   ├── earthquake/                       # 🔄 IN PROGRESS
│   │   ├── scripts/
│   │   │   └── earthquake_planetary_analysis.py
│   │   ├── data/                         # Earthquake data
│   │   └── manuscripts/                  # QUARTO documents
│   │
│   ├── weather/                          # ⏳ PLANNED
│   ├── economics/                        # ⏳ PLANNED
│   └── health/                           # ⏳ PLANNED
│
├── 🧪 tests/                             # Test suite
│   ├── unit/                             # Unit tests
│   ├── integration/                      # Integration tests
│   └── fixtures/                         # Test data & fixtures
│
├── ⚙️ config/                            # Configuration files
│   ├── _quarto.yml                       # Quarto rendering config
│   ├── railway.json                      # Railway deployment config
│   ├── render.yaml                       # Render deployment config
│   └── requirements/                     # Python dependencies
│       ├── requirements.txt              # Base dependencies
│       ├── requirements-api.txt          # API dependencies
│       ├── requirements-app.txt          # Web app dependencies
│       └── requirements-colab.txt        # Colab dependencies
│
├── 📊 assets/                            # Generated outputs
│   ├── reports/                          # Generated PDF reports
│   │   ├── vedic_correlation_research_report.pdf
│   │   ├── planet_individual_variations.pdf
│   │   └── planet_variations_detailed.pdf
│   │
│   ├── visualizations/                   # HTML visualizations
│   │   ├── daily_numerology_changes.html
│   │   ├── planetary_strength_dashboard.html
│   │   ├── planetary_strength_timeline.html
│   │   ├── numerology_vs_astrology_comparison.html
│   │   └── interactive-components.html
│   │
│   ├── data/                             # Analysis results
│   │   └── research_results.json
│   │
│   └── releases/                         # Release artifacts
│
├── 📚 manuscript/                        # Manuscript materials
│   ├── simple_manuscript-preview.html
│   ├── simple_manuscript.embed.ipynb
│   └── simple_manuscript.out.ipynb
│
├── 🗂️ Other Existing Folders
│   ├── _book/                            # Quarto book output
│   ├── _manuscript/                      # Manuscript build files
│   ├── _site/                            # Static site build
│   ├── htmlcov/                          # Code coverage reports
│   ├── .venv/                            # Python virtual environment
│   ├── .github/                          # GitHub workflows & CI/CD
│   ├── .git/                             # Git repository
│   └── styles/                           # CSS/styling assets
│
└── 📄 Root Level (ESSENTIAL ONLY)
    ├── README.md                         # Main project entry point
    ├── LICENSE                           # MIT License
    ├── Makefile                          # Build targets
    ├── pyproject.toml                    # Python project metadata
    ├── ARCHITECTURE.md                   # This file
    ├── PROJECT_STRUCTURE.md              # Structure documentation
    ├── COMPLETION_SUMMARY.txt            # Project completion tracking
    ├── _quarto.yml                       # Quarto config (main)
    ├── .gitignore                        # Git ignore rules
    └── .env (optional)                   # Environment variables
```

---

## 📝 Folder Descriptions

### **docs/** - Documentation Hub
**Purpose**: Centralized documentation for the entire project  
**Organization**:
- `guides/` - User-facing guides (setup, deployment, usage)
- `research/` - Research findings and analysis documentation
- `framework/` - Architecture & framework specifications
- `architecture/` - Detailed system design documents

**When to use**: 
- Creating user guides → `docs/guides/`
- Writing research findings → `docs/research/`
- Documenting framework changes → `docs/framework/`

---

### **scripts/** - Automation & Utilities
**Purpose**: Executable scripts for building, generating, and maintaining the project  
**Organization**:
- `build/` - Build automation (CI/CD preparation)
- `generate/` - Data & asset generation scripts
- `utilities/` - Helper scripts and utilities

**When to use**:
- Build tasks → `scripts/build/`
- Generating reports/visualizations → `scripts/generate/`
- Maintenance tasks → `scripts/utilities/`

**Examples**:
```bash
# Run build pipeline
bash scripts/build/build-all.sh

# Generate research report
python scripts/generate/generate_research_report.py

# Generate assets
python scripts/generate/generate-assets.py
```

---

### **src/** - Source Code
**Purpose**: Application logic and core modules  
**Organization**:
- `api/` - REST API implementation
- `web/` - Web application code
- `utils/` - Shared utilities (future)

**When to use**:
- Building API endpoints → `src/api/`
- Web application logic → `src/web/`
- Shared functions → `src/utils/`

---

### **use_cases/** - Domain-Specific Analysis
**Purpose**: Independent implementations of different research hypotheses  
**Current Status**:
- ✅ `numerology/` - Numerology-Astrology correlation (COMPLETE)
- 🔄 `earthquake/` - Earthquake-Planetary correlation (FRAMEWORK READY)
- ⏳ `weather/` - Weather/Climate patterns (PLANNED)
- ⏳ `economics/` - Economic cycles (PLANNED)
- ⏳ `health/` - Health/Epidemics (PLANNED)

**Each use case contains**:
- `scripts/` - Analysis scripts
- `data/` - Raw and processed data
- `manuscripts/` - QUARTO documents for reports

**Framework**: All use cases inherit from base architecture (code reuse)

---

### **assets/** - Generated Outputs
**Purpose**: Non-source files generated by scripts and builds  
**Organization**:
- `reports/` - Generated PDF reports
- `visualizations/` - Interactive HTML dashboards
- `data/` - Analysis results (JSON, CSV)
- `releases/` - Distribution artifacts

**Never commit to git**: These are regenerated by build scripts

---

### **config/** - Configuration Files
**Purpose**: Application and deployment configuration  
**Contents**:
- Deployment configs (Railway, Render)
- Quarto rendering configuration
- Python dependency specifications
- Environment-specific settings

**Usage**: Centralized config location for all environments

---

### **notebooks/** - Interactive Analysis
**Purpose**: Jupyter notebooks and Colab notebooks for exploration  
**Organization**:
- `analysis/` - Formal analysis notebooks
- `exploration/` - Exploratory/scratch notebooks
- Individual `.qmd` files for Quarto documents

**When to use**:
- Data exploration → `exploration/`
- Formal analysis → `analysis/`
- Long-form research → `.qmd` files

---

## 🔄 Core Modules

### **Vedic Astrology System**
- **Location**: `use_cases/numerology/scripts/` & `use_cases/earthquake/scripts/`
- **Purpose**: Calculate planetary positions and strengths
- **Key Classes**: `PlanetaryCalculations`, `VedicAstrologyEngine`
- **Data Format**: JSON with daily planetary values (0-100 strength scale)

### **Numerology System**
- **Location**: `use_cases/numerology/`
- **Purpose**: Calculate numerological values from birth dates
- **Key Formula**: Digit sum reduction (day/month/year) → 1-9 values
- **Integration**: Mapped to 9 Navagraha planets

### **Analysis Framework**
- **Location**: `use_cases/earthquake/scripts/earthquake_planetary_analysis.py`
- **Purpose**: Correlation analysis between events and planetary positions
- **Methods**: Chi-square testing, conjunction analysis, strength activation testing
- **Extensible**: Base class architecture for new use cases

---

## 🚀 Development Workflow

### **1. Setting Up Development Environment**
```bash
# Clone repository
git clone <repo-url> astro-research
cd astro-research

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Install dependencies
pip install -r config/requirements/requirements.txt

# Optional: Install development dependencies
pip install -r config/requirements/requirements-colab.txt  # For notebook work
pip install -r config/requirements/requirements-api.txt    # For API work
```

### **2. Running Existing Analysis**
```bash
# Numerology-Astrology correlation (COMPLETE)
python use_cases/numerology/scripts/numerology_astrology_correlation.py

# Earthquake analysis (READY)
python use_cases/earthquake/scripts/earthquake_planetary_analysis.py

# Generate reports
python scripts/generate/generate_research_report.py
```

### **3. Building & Deployment**
```bash
# Standard build
bash scripts/build/build.sh

# Full build pipeline
bash scripts/build/build-all.sh

# Generate all assets
python scripts/generate/generate-assets.py
```

### **4. Creating Documentation**
```bash
# Use Quarto to render markdown to PDF
quarto render docs/guides/QUICK_START_RESEARCH.md --to pdf

# Or render entire documentation
quarto render docs/ --to html
```

---

## ✨ Adding New Features

### **Adding a New Use Case**

**Step 1**: Create folder structure
```bash
mkdir -p use_cases/YOUR_USE_CASE/{scripts,data,manuscripts}
```

**Step 2**: Implement analysis script (inherit from base framework)
```python
# use_cases/YOUR_USE_CASE/scripts/analysis.py
from use_cases.earthquake.scripts.earthquake_planetary_analysis import EarthquakeAstrologicalAnalysis

class YourUseCase(EarthquakeAstrologicalAnalysis):
    """Inherit framework, customize for your event type"""
    
    def __init__(self, event_data_file):
        super().__init__(event_data_file)
        # Your customization
```

**Step 3**: Add to documentation
```bash
# Document in docs/framework/
echo "## YOUR_USE_CASE Analysis" >> docs/framework/USE_CASES_STATUS.md
```

**Step 4**: Create QUARTO manuscript
```bash
# use_cases/YOUR_USE_CASE/manuscripts/analysis.qmd
touch use_cases/YOUR_USE_CASE/manuscripts/analysis.qmd
```

---

### **Adding a New Documentation File**

**Rule**: Categorize by content type:
- User guide → `docs/guides/`
- Research finding → `docs/research/`
- Framework doc → `docs/framework/`
- System design → `docs/architecture/`

**Example**:
```bash
# Add new deployment guide
touch docs/guides/AZURE_DEPLOYMENT.md
```

---

### **Adding a New Script**

**Rule**: Organize by function:
- Build script → `scripts/build/`
- Data generation → `scripts/generate/`
- Utility/maintenance → `scripts/utilities/`

**Example**:
```bash
# Add data processing utility
touch scripts/utilities/process_earthquake_data.py
```

---

## 📏 File Organization Guidelines

### **DO's** ✅
- ✅ Keep root folder clean (only essential files)
- ✅ Organize by content type (docs/, scripts/, src/, etc.)
- ✅ Use descriptive file names
- ✅ Document file locations in README or ARCHITECTURE.md
- ✅ Move generated files to `assets/`
- ✅ Keep config files in `config/`
- ✅ Use the framework base class for new use cases

### **DON'Ts** ❌
- ❌ Don't add markdown files to root (use docs/)
- ❌ Don't put scripts in root (use scripts/)
- ❌ Don't commit generated assets (use .gitignore)
- ❌ Don't mix documentation with code
- ❌ Don't create random folders (follow structure)
- ❌ Don't duplicate configuration files

---

## 📊 Project Statistics

| Metric | Value |
|--------|-------|
| **Documentation Files** | 15 markdown files in docs/ |
| **Scripts** | 5 executable scripts in scripts/ |
| **Use Cases** | 5 planned (1 complete, 1 framework ready) |
| **Source Code Modules** | 2 (api/, web/) |
| **Generated Assets** | 14 files (PDFs, HTML, JSON) |
| **Tests** | Unit & integration test structure |

---

## 🔍 Quick Reference

### **Finding Things**
| What | Where |
|-----|-------|
| How do I get started? | `docs/guides/QUICK_START_RESEARCH.md` |
| API documentation | `docs/guides/API_DEPLOYMENT.md` |
| Research findings | `docs/research/` |
| Build/deploy scripts | `scripts/build/` |
| Data generation | `scripts/generate/` |
| Analysis engine | `use_cases/earthquake/scripts/` |
| Generated reports | `assets/reports/` |
| Data visualizations | `assets/visualizations/` |

---

## 🎯 Next Steps

1. **For Development**: Start in `src/` for new features
2. **For Documentation**: Add files to appropriate `docs/` subfolder
3. **For Analysis**: Create new use case in `use_cases/`
4. **For Automation**: Add scripts to `scripts/`
5. **For Outputs**: Generated files → `assets/`

---

## 📞 Support

For questions about project structure, refer to:
- **Architecture Questions**: This file (ARCHITECTURE.md)
- **Structure Overview**: [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md)
- **Getting Started**: [docs/guides/](docs/guides/)
- **Framework Design**: [docs/framework/MULTI_USE_CASE_FRAMEWORK.md](docs/framework/MULTI_USE_CASE_FRAMEWORK.md)

---

**Last Updated**: January 2026  
**Maintained By**: Development Team  
**Status**: ✅ Active (Clean Architecture v2.0)
