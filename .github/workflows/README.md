# ⚙️ GitHub Actions CI/CD Workflows

This directory contains all CI/CD workflow definitions. Each workflow automates a specific part of the development and research pipeline.

---

## Workflow Summary

| Workflow                 | File                       | Trigger            | Purpose                                        |
| ------------------------ | -------------------------- | ------------------ | ---------------------------------------------- |
| **CI**                   | `ci.yml`                   | Push, PR           | Lint + type-check + tests on all branches      |
| **Build & Deploy**       | `build-deploy.yml`         | Push to `main`     | Full build, render, and deploy to GitHub Pages |
| **Publish Research**     | `publish-research.yml`     | Push to `main`     | Render Quarto manuscripts and publish          |
| **Data Analysis**        | `data-analysis.yml`        | Scheduled (weekly) | Automated data refresh and re-analysis         |
| **Scientific Reporting** | `scientific-reporting.yml` | Manual dispatch    | Generate PDF scientific manuscripts            |

---

## Detailed Descriptions

### `ci.yml` — Continuous Integration

**Triggers**: Every push and pull request to any branch.

**Steps**:

1. Checkout code
2. Set up Python (matrix: 3.8, 3.10, 3.12)
3. Install dependencies
4. Run `flake8` linting
5. Run `mypy` type checking
6. Run `pytest` test suite with coverage

**Purpose**: Ensures every code change passes quality checks before merging.

---

### `build-deploy.yml` — Build & Deploy

**Triggers**: Push to `main` branch only.

**Steps**:

1. Full quality gate (same as CI)
2. Generate all research artifacts (`research/scripts/generate_artifacts.py`)
3. Render all Quarto reports
4. Deploy the rendered site to GitHub Pages

**Purpose**: Keeps the research website always up-to-date with the latest findings.

---

### `publish-research.yml` — Research Publication

**Triggers**: Push to `main` branch; also supports manual dispatch.

**Steps**:

1. Install Quarto, LaTeX (for PDF), and Python dependencies
2. Render manuscripts in all formats (HTML, PDF, DOCX)
3. Upload artifacts and publish to GitHub Pages

**Purpose**: Automates the production of peer-quality manuscripts.

---

### `data-analysis.yml` — Scheduled Analysis

**Triggers**: Weekly schedule (Monday 00:00 UTC); manual dispatch.

**Steps**:

1. Fetch latest data from external sources (USGS, Yahoo Finance, etc.)
2. Run analysis pipeline
3. Commit updated results to `data/processed/`
4. Open an automated PR if results changed significantly

**Purpose**: Keeps research data fresh without manual intervention.

---

### `scientific-reporting.yml` — Scientific Report Generation

**Triggers**: Manual dispatch only (`workflow_dispatch`).

**Steps**:

1. Generate scientific assets (figures, tables, statistics)
2. Render to Nature/IEEE manuscript templates
3. Upload as GitHub release artifacts

**Purpose**: On-demand generation of camera-ready scientific manuscripts.

---

## Adding a New Workflow

1. Create a new `.yml` file in this directory
2. Follow the [GitHub Actions syntax](https://docs.github.com/en/actions/writing-workflows/workflow-syntax-for-github-actions)
3. Test it using [act](https://github.com/nektos/act) locally before pushing:
   ```bash
   act push -j your-job-name
   ```
4. Document it in this README

---

## Secrets Used

| Secret Name    | Used In       | Description                                       |
| -------------- | ------------- | ------------------------------------------------- |
| `GITHUB_TOKEN` | All workflows | Auto-provided by GitHub for checkout and releases |

> **Note**: This project intentionally uses no external service secrets. All computation is local to the CI runner.
