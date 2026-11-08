# 🔬 research/ — Research Use Cases & Pipeline

The `research/` directory contains all **empirical research tracks**, raw datasets, analysis notebooks, and generated reports. This is the "lab notebook" of the project.

---

## 📁 Directory Structure

```
research/
├── use_cases/                   ← Individual research tracks
│   ├── numerology/              ← Numerology-Astrology integration study
│   ├── earthquake/              ← India-Nepal seismic pattern analysis
│   ├── gold_market/             ← XAU/USD vs. planetary cycle correlations
│   └── assets/                  ← Shared research assets
│
├── scripts/                     ← Pipeline orchestration scripts
│   ├── generate_artifacts.py    ← Main pipeline entry point
│   ├── generate_track1_scientific_assets.py
│   ├── generate_track2_scientific_assets.py
│   ├── pipeline.py              ← Pipeline utilities
│   └── generate/                ← Modular generation scripts
│
├── reports/                     ← Quarto manuscripts & published reports
├── data/                        ← Raw and processed datasets
├── notebooks/                   ← Jupyter notebooks for exploration
└── REPORT_STANDARDS_AND_GUIDELINES.md  ← Standards for research reports
```

---

## 🔬 Active Research Tracks

| Track                                  | Focus                                                          | Status         | Data Source                            |
| -------------------------------------- | -------------------------------------------------------------- | -------------- | -------------------------------------- |
| [numerology/](use_cases/numerology/)   | Numerology-Astrology digit mapping; athlete/event correlations | ✅ Active      | Wikipedia birth data, custom databases |
| [earthquake/](use_cases/earthquake/)   | Classical Jyotish vs. seismic events (India-Nepal)             | 🔄 In Progress | USGS Earthquake Catalog                |
| [gold_market/](use_cases/gold_market/) | Planetary cycles vs. XAU/USD price movements                   | 🔄 In Progress | Yahoo Finance / World Gold Council     |

---

## 🚀 Running the Research Pipeline

### Full Pipeline (Generate All Artifacts & Reports)

```bash
# From project root
python3 research/scripts/generate_artifacts.py

# Or via Makefile
make build
```

### Generate a Specific Report

```bash
# Render the comprehensive thesis to HTML
quarto render research/reports/comprehensive_thesis/COMPREHENSIVE_RESEARCH_THESIS.qmd --to html

# Render to PDF (requires LaTeX)
quarto render research/reports/comprehensive_thesis/COMPREHENSIVE_RESEARCH_THESIS.qmd --to pdf

# Render all formats
quarto render
```

### Running Individual Use Cases

```bash
# Numerology analysis
quarto render research/use_cases/numerology/numerology_planet_timeline.qmd

# Batch report generation
bash research/scripts/build_all_reports.sh
```

---

## 📐 Research Methodology

All research tracks follow the same empirical framework:

1. **Hypothesis** — State a specific, falsifiable claim
2. **Data Collection** — Document sources, download scripts, and preprocessing
3. **Analysis** — Run statistical tests (correlation, permutation, Granger causality)
4. **Falsification** — Actively attempt to disprove the hypothesis
5. **Reporting** — Generate reproducible Quarto report

See [docs/RESEARCH_METHODOLOGY.md](../docs/RESEARCH_METHODOLOGY.md) for the full guide.

---

## ➕ Adding a New Research Track

```bash
# Create the new use case directory
mkdir -p research/use_cases/your_topic/{data,tests,reports}

# Start from the README template
cp research/use_cases/numerology/README.md research/use_cases/your_topic/README.md
# → Edit the hypothesis, methodology, and data sources
```

**Always open a [Research Request Issue](https://github.com/astro-fusion/astro_research-white-paper/issues/new?template=research_request.yml) first** to discuss your proposal before investing significant work.

---

## 📊 Report Standards

All generated reports must comply with [`REPORT_STANDARDS_AND_GUIDELINES.md`](REPORT_STANDARDS_AND_GUIDELINES.md):

- Academic tone with proper citations
- Reproducible — all code must run from a clean checkout
- Include a null hypothesis and falsification section
- Statistical significance clearly stated (p-values, effect sizes, confidence intervals)
