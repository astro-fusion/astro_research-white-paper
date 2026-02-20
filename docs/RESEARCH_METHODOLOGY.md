# 🔬 Research Methodology Guide

This guide explains how empirical research is structured in this project and provides step-by-step instructions for **adding a new research use case**.

---

## Core Principles

Every research track in this project must be:

| Principle           | Meaning                                                                           |
| ------------------- | --------------------------------------------------------------------------------- |
| **Falsifiable**     | The hypothesis must be testable and capable of being wrong                        |
| **Reproducible**    | All code, data, and steps must run from a clean checkout                          |
| **Transparent**     | Data sources, cleaning steps, and assumptions must be documented                  |
| **Honest**          | Null results and failures are reported, not suppressed                            |
| **Peer-reviewable** | Analysis is documented well enough that an independent researcher can critique it |

---

## Research Track Structure

Every use case lives under `research/use_cases/your_topic/` with this structure:

```
research/use_cases/your_topic/
├── README.md              ← Hypothesis, methodology, data sources, findings
├── data/
│   ├── raw/               ← Unmodified downloaded data (with download script!)
│   └── processed/         ← Cleaned/transformed data
├── analysis.qmd           ← Quarto notebook: reproducible analysis
├── tests/
│   └── test_analysis.py   ← Validates that key calculations are correct
└── reports/
    └── report.pdf         ← Generated report (tracked in .gitignore if large)
```

---

## Step-by-Step: Adding a New Research Track

### Step 1: Open a Discussion First

Before writing any code, [open a Research Request Issue](https://github.com/astro-fusion/astro_research-white-paper/issues/new?template=research_request.yml) to:

- State your hypothesis (must be falsifiable)
- Describe your data source (must be public or includable in the repo)
- Describe your statistical approach
- Invite feedback from maintainers and other contributors

### Step 2: Create the Directory Structure

```bash
# From project root
mkdir -p research/use_cases/your_topic/{data/raw,data/processed,tests,reports}
touch research/use_cases/your_topic/README.md
touch research/use_cases/your_topic/analysis.qmd
```

### Step 3: Write the README with Your Hypothesis

Your `README.md` must include:

````markdown
# 🔬 [Topic Name] Research Track

## Hypothesis

**H0 (Null Hypothesis)**: [State what you expect to find if no relationship exists]
**H1 (Alternative Hypothesis)**: [State the positive claim you are testing]

**Significance Level**: p < 0.05 (two-tailed)

---

## Data Sources

| Dataset        | Source | License   | Download                 |
| -------------- | ------ | --------- | ------------------------ |
| [Dataset name] | [URL]  | [License] | [Script or instructions] |

### Data Collection

```bash
# Download instructions or reference download script
python3 research/use_cases/your_topic/data/download.py
```
````

---

## Methodology

1. **Data Preprocessing**: [Steps to clean and prepare data]
2. **Astrological Mapping**: [How birth data maps to planetary positions]
3. **Statistical Test**: [Test name, why it was chosen, assumptions]
4. **Control Group**: [What the null distribution looks like / how it's generated]

---

## Results

[Fill in after analysis]

---

## Conclusion

[Accept or reject H0; discuss effect size; discuss limitations]

````

### Step 4: Write the Quarto Analysis Notebook

Your `analysis.qmd` should be structured like this:

```qmd
---
title: "[Topic] Empirical Analysis"
format: html
execute:
  echo: true
  warning: false
---

## Setup

```python
import pandas as pd
from libs.vedic_astrology_core import VedicChart
from libs.vedic_astrology_core.dignity import calculate_planetary_dignity
````

## Data Loading

```python
df = pd.read_csv("data/processed/dataset.csv")
df.head()
```

## Astrological Mapping

```python
# Map each subject to planetary positions
def map_to_planets(row):
    chart = VedicChart(row['birth_date'], row['birth_time'], row['lat'], row['lon'])
    return chart.get_dignity_scores()

df['dignity_scores'] = df.apply(map_to_planets, axis=1)
```

## Statistical Analysis

```python
from scipy import stats

# Your statistical test here
t_stat, p_value = stats.ttest_ind(group_a_scores, group_b_scores)
print(f"t={t_stat:.3f}, p={p_value:.4f}")
```

## Results

```python
# Visualize results
import matplotlib.pyplot as plt
# ...
```

````

### Step 5: Write Tests for Your Analysis

Every research track must have at least:

1. A test that **data loading works** on a small fixture dataset
2. A test that **the statistical calculation** returns sensible values
3. A test that **edge cases don't crash** the pipeline

```python
# research/use_cases/your_topic/tests/test_analysis.py
import pytest
import pandas as pd

def test_data_loading():
    """Dataset loads and has expected columns."""
    df = pd.read_csv("research/use_cases/your_topic/data/processed/dataset.csv")
    assert "birth_date" in df.columns
    assert len(df) > 0

def test_astrological_mapping():
    """Planetary mapping produces valid dignity scores."""
    from libs.vedic_astrology_core.dignity import calculate_planetary_dignity
    result = calculate_planetary_dignity("Mars", "Aries", 15.0)
    assert 0 <= result["score"] <= 100
````

### Step 6: Register the Use Case

Add an entry to `research/use_cases/README.md`:

```markdown
| [your_topic/](your_topic/) | Your Hypothesis Summary | 🔄 In Progress | Your Data Source |
```

And update the main `README.md` research table.

### Step 7: Submit a Pull Request

Open a PR referencing your Research Request issue. The PR should include:

- The complete directory structure
- Working `analysis.qmd` that renders without errors
- Tests passing
- README.md with clearly stated hypothesis and methodology

---

## Statistical Methods Reference

| Method                  | When to Use                                          | Python Implementation                               |
| ----------------------- | ---------------------------------------------------- | --------------------------------------------------- |
| **Pearson Correlation** | Linear relationship between two continuous variables | `scipy.stats.pearsonr()`                            |
| **Permutation Test**    | Non-parametric, no distribution assumptions          | `scipy.stats.permutation_test()`                    |
| **Granger Causality**   | Does X help predict Y over time?                     | `statsmodels.tsa.stattools.grangercausalitytests()` |
| **Monte Carlo**         | Empirical null distribution for complex statistics   | Custom implementation                               |
| **Mann-Whitney U**      | Comparing two groups without normality assumption    | `scipy.stats.mannwhitneyu()`                        |

---

## Citing Data Sources

Always include the full citation in your README:

```
USGS Earthquake Catalog. (2024). Retrieved from https://earthquake.usgs.gov/earthquakes/search/
Accessed: [date]. License: Public Domain (U.S. Government data).
```
