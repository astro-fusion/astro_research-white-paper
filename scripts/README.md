# 🔨 Scripts & Utilities

CLI wrappers and build utilities for managing the research pipeline and development environment.

## Principal Scripts

- **`web.py`**: Launches the interactive research timeline interface (Flask).
- **`src/generate_artifacts.py`**: Primary orchestrator for the analysis pipeline.
- **`tests/run_all_tests.py`**: Executes the comprehensive testing suite.
- **`scripts/fetch_gold_data.py`**: Utility for updating historical market data.

## Usage

Most scripts are either triggered via the `Makefile` or run directly using `python3`.

```bash
# Example: Run full validation
make validate
```
