# 🔨 Scripts & Utilities

CLI wrappers and build utilities for managing the research pipeline and development environment.

## Principal Scripts

- **`web.py`**: Launches the interactive research timeline interface (Flask).
- **`scripts/generate_artifacts.py`**: Primary orchestrator for the analysis pipeline.
- **`pytest tests/`**: the test suite (no `PYTHONPATH`; install the package first).
- **`studies/gold_market/scripts/pipeline.py`**, **`studies/silver_market/scripts/pipeline.py`**: pre-registered market studies (fetch, snapshot, test, figures) on `vedic_astrology_core.markets`.

## Usage

Most scripts are either triggered via the `Makefile` or run directly using `python3`.

```bash
# Example: Run full validation
make validate
```
