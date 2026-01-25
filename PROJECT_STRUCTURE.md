# 📁 Astro-Research Project Structure

## Current State Analysis
**Files currently in root (MESSY):**
- 15 Markdown files (.md)
- 2 Shell scripts (.sh)
- 6 Python files (.py)
- 1 Text file (.txt)
- 3 Config files (.json, .yml)
- Multiple requirements files
- Multiple HTML, PDF outputs scattered

---

## ✅ Proposed Clean Architecture

```
astro-research/
│
├── 📖 docs/                          # All project documentation
│   ├── guides/                       # User guides & setup instructions
│   │   ├── QUICK_START_RESEARCH.md
│   │   ├── REAL_TIME_VISUALIZATION_GUIDE.md
│   │   ├── RESEARCH_REPORT_GUIDE.md
│   │   └── API_DEPLOYMENT.md
│   │
│   ├── research/                     # Research findings & reports
│   │   ├── RESEARCH_COMPLETION_SUMMARY.md
│   │   ├── RESEARCH_DATA_REFERENCE.md
│   │   ├── RESEARCH_PAPER_TEMPLATE.md
│   │   └── PLANETARY_STRENGTH_VISUALIZATION.md
│   │
│   ├── framework/                    # Architecture & framework docs
│   │   ├── MULTI_USE_CASE_FRAMEWORK.md
│   │   ├── EARTHQUAKE_DATA_INTEGRATION.md
│   │   ├── PROJECT_UPDATE_SUMMARY.md
│   │   └── QUICK_REFERENCE_CARD.md
│   │
│   ├── architecture/                 # System design & patterns
│   │   └── ARCHITECTURE.md (NEW - comprehensive guide)
│   │
│   ├── INDEX.md                      # Main index/navigation
│   ├── CONTRIBUTING.md
│   └── README.md                     # Root README (stays, but updated)
│
├── 🔨 scripts/                       # All executable scripts
│   ├── build/                        # Build automation
│   │   ├── build.sh
│   │   └── build-all.sh
│   │
│   ├── generate/                     # Data generation scripts
│   │   ├── create_planetary_strength_graph.py
│   │   ├── generate-assets.py
│   │   └── generate_research_report.py
│   │
│   └── utilities/                    # Utility scripts
│       └── (future maintenance scripts)
│
├── 🌐 src/                           # Source code (EXISTING)
│   ├── api/
│   │   ├── api.py  (move from root)
│   │   └── api-client.js  (move from root)
│   │
│   ├── web/
│   │   ├── app.py  (move from root)
│   │   └── web.py  (move from root)
│   │
│   └── utils/
│
├── 📓 notebooks/                     # Jupyter/Colab notebooks (EXISTING)
│   ├── analysis/
│   ├── exploration/
│   └── test.qmd (organize or remove)
│
├── 🔬 use_cases/                     # Use case implementations (EXISTING)
│   ├── numerology/
│   ├── earthquake/
│   ├── weather/
│   └── economics/
│
├── 🧪 tests/                         # Test files (EXISTING)
│   ├── unit/
│   ├── integration/
│   └── fixtures/
│
├── ⚙️ config/                        # Configuration files (EXISTING)
│   ├── default_config.yaml
│   ├── _quarto.yml (copy here)
│   ├── railway.json (copy here)
│   ├── render.yaml (copy here)
│   └── requirements/                 # Requirements organized
│       ├── requirements.txt (base)
│       ├── requirements-api.txt
│       ├── requirements-app.txt
│       └── requirements-colab.txt
│
├── 📊 assets/                        # Generated outputs (EXISTING - enhanced)
│   ├── reports/                      # Generated PDFs
│   │   ├── vedic_correlation_research_report.pdf
│   │   ├── planet_individual_variations.pdf
│   │   └── planet_variations_detailed.pdf
│   │
│   ├── visualizations/               # HTML visualizations
│   │   ├── daily_numerology_changes.html
│   │   ├── interactive-components.html
│   │   ├── numerology_vs_astrology_comparison.html
│   │   ├── planetary_strength_dashboard.html
│   │   ├── planetary_strength_timeline.html
│   │   └── test-output.html
│   │
│   ├── data/
│   │   ├── research_results.json
│   │   └── (analysis outputs)
│   │
│   └── releases/
│
├── 📚 manuscript/                    # Manuscript files (EXISTING - may stay)
│   ├── simple_manuscript-preview.html
│   ├── simple_manuscript.embed.ipynb
│   └── simple_manuscript.out.ipynb
│
├── 📄 Root Level (CLEAN)             # Only essential files
│   ├── README.md                     # Main entry point
│   ├── LICENSE
│   ├── Makefile
│   ├── pyproject.toml
│   ├── .gitignore
│   ├── ARCHITECTURE.md               # NEW - System design guide
│   ├── COMPLETION_SUMMARY.txt        # Move to docs/
│   └── .env (if needed)
│
└── 📁 Temporary / Deprecated         # Archive old files
    └── (files no longer needed)
```

---

## 📋 File Movement Plan

### **Documentation (→ docs/)**
| File | Current Location | New Location | Category |
|------|-----------------|--------------|----------|
| QUICK_START_RESEARCH.md | root | docs/guides/ | User Guide |
| REAL_TIME_VISUALIZATION_GUIDE.md | root | docs/guides/ | User Guide |
| RESEARCH_REPORT_GUIDE.md | root | docs/guides/ | User Guide |
| API_DEPLOYMENT.md | root | docs/guides/ | User Guide |
| RESEARCH_COMPLETION_SUMMARY.md | root | docs/research/ | Research |
| RESEARCH_DATA_REFERENCE.md | root | docs/research/ | Research |
| RESEARCH_PAPER_TEMPLATE.md | root | docs/research/ | Research |
| PLANETARY_STRENGTH_VISUALIZATION.md | root | docs/research/ | Research |
| MULTI_USE_CASE_FRAMEWORK.md | root | docs/framework/ | Framework |
| EARTHQUAKE_DATA_INTEGRATION.md | root | docs/framework/ | Framework |
| PROJECT_UPDATE_SUMMARY.md | root | docs/framework/ | Framework |
| QUICK_REFERENCE_CARD.md | root | docs/framework/ | Framework |
| INDEX.md | root | docs/ | Index |
| CONTRIBUTING.md | root | docs/ | Governance |

### **Scripts (→ scripts/)**
| File | Current Location | New Location | Purpose |
|------|-----------------|--------------|---------|
| build.sh | root | scripts/build/ | Build automation |
| build-all.sh | root | scripts/build/ | Build automation |
| create_planetary_strength_graph.py | root | scripts/generate/ | Asset generation |
| generate-assets.py | root | scripts/generate/ | Asset generation |
| generate_research_report.py | root | scripts/generate/ | Report generation |

### **Source Code (→ src/)**
| File | Current Location | New Location | Module |
|------|-----------------|--------------|--------|
| api.py | root | src/api/api.py | API |
| api-client.js | root | src/api/api-client.js | API |
| app.py | root | src/web/app.py | Web App |
| web.py | root | src/web/web.py | Web App |

### **Assets (→ assets/)**
| File Type | Current Location | New Location | Category |
|-----------|-----------------|--------------|----------|
| *.pdf | root | assets/reports/ | Reports |
| *.html (viz) | root | assets/visualizations/ | Visualizations |
| *.json (data) | root | assets/data/ | Data |

### **Config (→ config/)**
| File | Current Location | New Location | Purpose |
|------|-----------------|--------------|---------|
| _quarto.yml | root | config/ | Quarto config |
| railway.json | root | config/ | Railway deploy |
| render.yaml | root | config/ | Render deploy |
| requirements-*.txt | root | config/requirements/ | Dependencies |
| requirements.txt | root | config/requirements/ | Base deps |

### **Keep in Root (ESSENTIAL ONLY)**
```
README.md              # Main entry point
LICENSE                # Project license
Makefile               # Build targets
pyproject.toml         # Python project metadata
.gitignore             # Git configuration
ARCHITECTURE.md        # System design (NEW)
```

---

## 🎯 Benefits of This Structure

✅ **Clarity**: Each type of content has designated location  
✅ **Scalability**: Easy to add new use cases, scripts, or documentation  
✅ **Maintainability**: Clear separation of concerns  
✅ **Navigation**: Developers can easily find what they need  
✅ **CI/CD**: Scripts folder facilitates automation  
✅ **Documentation**: docs/ becomes central reference  
✅ **Outputs**: assets/ keeps generated files organized  

---

## 🚀 Implementation Steps

1. **Create directory structure** (scripts, docs subdirs, etc.)
2. **Move documentation files** to docs/
3. **Move scripts** to scripts/
4. **Move source code** to src/
5. **Move assets** to assets/
6. **Copy config files** to config/
7. **Update import paths** in all Python files
8. **Create ARCHITECTURE.md** documenting the new structure
9. **Clean root folder** - verify only essential files remain
10. **Test all imports** to ensure everything still works

---

## 📝 Notes

- **README.md stays in root** - This is the project entry point
- **Python imports need updating** - If files are moved, imports must be updated
- **Build processes need updating** - Scripts paths will change
- **CI/CD configs may need updating** - Look in .github/ workflows
- **Backwards compatibility** - Old file locations can redirect if needed

---

## ⏭️ Next Phase: Implement This Structure
Ready to proceed with reorganization? This will ensure:
- Professional project layout
- Easier maintenance
- Better onboarding for contributors
- Scalable architecture for future use cases
