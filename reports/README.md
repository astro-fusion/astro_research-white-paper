# 📖 Reports & Artifacts

This directory handles the presentation layer of the research, transforming data and analysis into publication-ready manuscripts and visualizations.

## 🔬 Scientific Reporting Pipeline

The platform includes a fully automated pipeline for generating international-level scientific reports.

### 1. Automated Artifact Generation

Running `python3 src/generate_artifacts.py` produces:

- **`artifacts/tbl_stationarity.csv`**: Unit root test results.
- **`artifacts/stats_granger.json`**: p-values for causal inference.
- **`artifacts/fig_permutation_dist.pdf`**: Monte Carlo distribution visualization.

### 2. Dynamic Narrative Rendering

Using Quarto to inject statistics from `artifacts/` into dynamic manuscripts.

- **Nature Style**: `quarto render reports/manuscript.qmd --profile=nature_like`
- **IEEE Style**: `quarto render reports/manuscript.qmd --profile=ieee_like`

## Styles & Formatting

- **`styles/`**: Contains journal-specific CSL files (Nature, IEEE, etc.).
- **`references.bib`**: Central bibliography for research citations.
