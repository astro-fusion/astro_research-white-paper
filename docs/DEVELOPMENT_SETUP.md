# 🛠️ Development Setup Guide

Complete guide for setting up a local development environment. Follow all steps in order to get a fully working, linted, and test-ready environment.

---

## Prerequisites

| Tool       | Version | Install                                            |
| ---------- | ------- | -------------------------------------------------- |
| **Python** | 3.8+    | [python.org](https://www.python.org/downloads/)    |
| **Git**    | 2.0+    | [git-scm.com](https://git-scm.com/)                |
| **Quarto** | 1.3+    | [quarto.org](https://quarto.org/docs/get-started/) |
| **Make**   | Any     | Usually pre-installed on macOS/Linux               |

---

## Step 1: Fork & Clone

```bash
# 1a. Fork on GitHub (click the Fork button on the repo page)

# 1b. Clone YOUR fork
git clone https://github.com/YOUR_USERNAME/astro_research-white-paper.git
cd astro_research-white-paper

# 1c. Add the upstream remote (to sync with the main repo later)
git remote add upstream https://github.com/astro-fusion/astro_research-white-paper.git

# Verify
git remote -v
# origin    https://github.com/YOUR_USERNAME/astro_research-white-paper.git (fetch)
# upstream  https://github.com/astro-fusion/astro_research-white-paper.git (fetch)
```

---

## Step 2: Python Virtual Environment

```bash
# Create virtual environment
python3 -m venv .venv

# Activate it
source .venv/bin/activate        # macOS/Linux
.venv\Scripts\activate           # Windows

# Verify Python path
which python  # Should show .venv path
python --version  # Should be 3.8+
```

---

## Step 3: Install Dependencies

```bash
# Install base runtime dependencies
pip install -r ops/requirements.txt

# Install the library in editable mode + dev tools
pip install -e ".[dev]"

# Optional: Swiss Ephemeris (required for actual chart calculations)
pip install -e ".[ephemeris]"

# Optional: Colab/Jupyter extras
pip install -r ops/requirements-colab.txt
```

---

## Step 4: Install Pre-commit Hooks

Pre-commit hooks automatically run linters and formatters on every `git commit`, catching issues before they hit CI.

```bash
pip install pre-commit
pre-commit install

# Test it works (runs on all files — may take a minute)
pre-commit run --all-files
```

---

## Step 5: Install Quarto

Quarto is needed to render research reports.

```bash
# macOS (via Homebrew)
brew install --cask quarto

# Or download the installer directly from:
# https://quarto.org/docs/get-started/

# Verify installation
quarto --version  # Should be 1.3+
```

---

## Step 6: Verify Everything Works

```bash
# Run the full test suite
pytest tests/ -v

# Run quick smoke test (fast, no integration tests)
pytest tests/ -m "not slow and not integration" -v

# Run the quality gate (lint + type-check + tests)
make quality-gate

# Try rendering a report (optional but recommended)
quarto render research/reports/comprehensive_thesis/COMPREHENSIVE_RESEARCH_THESIS.qmd --to html
```

---

## Step 7: Start the Web App (Optional)

```bash
python application/web/web.py
# → Open http://localhost:5000
```

---

## Common Setup Issues & Fixes

### `pyswisseph` install fails on macOS

```bash
# Install Xcode command line tools first
xcode-select --install
# Then retry
pip install pyswisseph
```

### `pyswisseph` not found but tests still pass

Most tests mock the ephemeris. You only need `pyswisseph` for real chart calculations. Install with:

```bash
pip install -e ".[ephemeris]"
```

### Quarto not found in PATH

```bash
# macOS: add to PATH in ~/.zshrc or ~/.bashrc
export PATH="$PATH:/Applications/quarto/bin"
```

### `pre-commit` fails on first run

```bash
# Re-install hooks
pre-commit uninstall
pre-commit install
pre-commit run --all-files
```

### Pytest can't import `libs`

```bash
# Make sure you installed the package in editable mode
pip install -e ".[dev]"

# Or set PYTHONPATH
export PYTHONPATH="$PYTHONPATH:$(pwd)"
```

---

## Development Workflow (Day-to-Day)

```bash
# 1. Sync with upstream before starting new work
git fetch upstream
git checkout main
git rebase upstream/main

# 2. Create a feature branch
git checkout -b feat/your-feature

# 3. Write code

# 4. Run tests continuously
pytest tests/ -k "your_feature_keyword" -v --tb=short

# 5. Before committing, run full quality gate
make quality-gate

# 6. Commit (pre-commit hooks run automatically)
git add .
git commit -m "feat(libs): your change description"

# 7. Push and open PR
git push origin feat/your-feature
```

---

## IDE Setup

### VS Code (Recommended)

Install these extensions:

- `ms-python.python` — Python language support
- `ms-python.black-formatter` — Black formatting
- `quarto.quarto` — Quarto preview

Recommended `.vscode/settings.json`:

```json
{
  "editor.formatOnSave": true,
  "python.formatting.provider": "black",
  "python.linting.flake8Enabled": true,
  "python.linting.enabled": true,
  "python.testing.pytestEnabled": true,
  "python.testing.pytestArgs": ["tests/"]
}
```

### PyCharm

1. Set **Project Interpreter** to `.venv/bin/python`
2. Enable **Black** as the formatter (Settings → Tools → Black)
3. Set **Test framework** to `pytest` (Settings → Python Integrated Tools)
