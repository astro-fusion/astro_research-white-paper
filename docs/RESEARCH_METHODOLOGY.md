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

Every use case lives under `studies/your_topic/` with this structure:

```
studies/your_topic/
├── README.md              ← Question, status, how to run, data sources
├── paper/                 ← The .qmd manuscript, sections/, references (no rendered output)
├── scripts/               ← Pipeline scripts; resolve paths via studies/_paths.py
├── data/                  ← Fetched or generated inputs (gitignored; documented in README)
├── figures/               ← Committed only if produced by scripts/ and referenced by paper/
├── tables/                ← Small committed result tables
├── notebooks/             ← Optional exploration notebooks
└── artifacts/             ← Generated output (gitignored)
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
mkdir -p studies/your_topic/{paper/sections,scripts,data,figures,tables,artifacts}
touch studies/your_topic/README.md studies/your_topic/paper/your_topic.qmd
touch studies/your_topic/data/.gitkeep studies/your_topic/artifacts/.gitkeep
# then add "your_topic" to STUDIES in studies/_paths.py
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
python3 studies/your_topic/data/download.py
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
from vedic_astrology_core import VedicChart
from vedic_astrology_core.dignity import calculate_planetary_dignity
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
# studies/your_topic/tests/test_analysis.py
import pytest
import pandas as pd

def test_data_loading():
    """Dataset loads and has expected columns."""
    df = pd.read_csv("studies/your_topic/data/processed/dataset.csv")
    assert "birth_date" in df.columns
    assert len(df) > 0

def test_astrological_mapping():
    """Planetary mapping produces valid dignity scores."""
    from vedic_astrology_core.dignity import calculate_planetary_dignity
    result = calculate_planetary_dignity("Mars", "Aries", 15.0)
    assert 0 <= result["score"] <= 100
````

### Step 6: Register the Use Case

Add the study to `STUDIES` in `studies/_paths.py` and an entry to the studies table:

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

Use `vedic_astrology_core.stats` (`libs/vedic_astrology_core/stats/`); do not
write study-local versions of these tests. The rigor contract in
`docs/adr/ADR-001-flagship-research-repo.md` is enforced through it.

| Need | Module and function | Notes |
| --- | --- | --- |
| Is the outcome stationary? | `stationarity.stationarity_gate` | ADF + KPSS; returns the verdict and the transform applied (none, diff, log-diff) |
| Null that keeps autocorrelation | `nulls.circular_shift_null`, `nulls.stationary_block_bootstrap`, `nulls.phase_randomization` | never shuffle days i.i.d.; pass `rng=np.random.default_rng(seed)` |
| Permutation test of any statistic | `permutation.permutation_test` | p = (n_extreme + 1) / (n + 1); returns effect size and a bootstrap CI |
| Multiple comparisons | `multiplicity.family(results, method="by")` | one correction across every (rule, target) pair; `"bh"`, `"by"`, `"bonferroni"` |
| Event rate during an indicator | `rates.rate_ratio`, `rates.rate_ratio_shift_test` | exact Poisson CI; circular-shift p-value |
| Alarm-based forecasts | `molchan.molchan_trajectory`, `binomial_bound`, `area_skill_score`, `time_random_reference` | tau is a fraction of time; never interpolate on a decreasing axis |
| Granger-type question | `granger.exog_granger` | astro series exogenous, ADL with Newey-West HAC, a priori lags, stationarity gate enforced; `target="garch_abs"` needs the optional `arch` package |
| Out-of-sample evaluation | `walk_forward.time_split`, `walk_forward_splits`, `spa_test` | frozen confirmation period; Hansen SPA for best-rule claims |
| Periodicities | `spectral.lomb_scargle_at_periods` | only at periods fixed in advance |
| Provenance | `manifest.write_manifest`, `plots.save_figure` | data SHA-256, commit, seed, ephemeris model, ayanamsa and node model; figure footer |

Every study also needs a `hypothesis.yaml` written before the pipeline runs
(see `studies/earthquake/hypothesis.yaml`): data and period, indicators,
windows, direction, null, number of draws and seed, correction, alpha and the
exploration/confirmation split. Changes after the first run go into its
`amendments` list with a date and a reason. One `scripts/pipeline.py` per
study writes every table, figure, `results.json` and `manifest.json` into
`studies/<name>/artifacts/`, and the paper reads `results.json` instead of
typing numbers.

---

## Citing Data Sources

Always include the full citation in your README:

```
USGS Earthquake Catalog. (2024). Retrieved from https://earthquake.usgs.gov/earthquakes/search/
Accessed: [date]. License: Public Domain (U.S. Government data).
```

---

## Beyond a single test: what a result is worth

The tools below (ADR-003) do not change how a registered family is tested.
They answer the questions a reader asks next: does the result depend on one
analytic choice, could the study have found an effect at all, does the method
find a real effect when one exists, and is anything in the sky predictive
when no rule is named?

### Specification curves

A rate ratio that holds for an 8-degree orb but not 6 or 10, or for one
declustering method but not the other, reflects one path through many
defensible choices. `stats.speccurve.specification_curve(estimator, grid,
rng, n=...)` runs the estimator on every cell of a declared grid of choices
(orb, window, catalogue, declustering, ayanamsa, node model, house system)
and returns the curve sorted by estimate, each cell's interval, and the share
of cells whose interval excludes the null. `stats.plots.specification_curve_figure`
draws the curve above a matrix of the choices behind each cell (Simonsohn,
Simmons and Nelson 2020, *Nature Human Behaviour* 4, 1208-1214; Steegen,
Tuerlinckx, Gelman and Vanpaemel 2016, *Perspectives on Psychological
Science* 11, 702-712).

The cells share data, so their p-values are not independent and the share of
"significant" cells means nothing on its own. The joint test rotates the
outcome once per draw by a random circular shift and recomputes the whole
curve with that shift; the p-value of the median estimate (and of the share)
is its rank among those draws. The grid is declared before the run, like the
family, and goes into `hypothesis.yaml` or the rule's `params` ranges.

### Power

A null result from a small catalogue excludes only large effects.
`stats.power.minimum_detectable_rate_ratio(n_events, duty_cycle, alpha,
power, rng, n_sim)` simulates studies with a Poisson number of events and the
circular-shift null (for Poisson events the shifted in-count is exactly
binomial whatever the indicator's run structure) and finds by bisection the
smallest rate ratio the test detects with the target power; `power_table`
does this for every registered indicator, and
`minimum_detectable_difference` gives the analogue for a difference in means
from a reported interval (Cohen 1988, *Statistical Power Analysis for the
Behavioral Sciences*; Gelman and Carlin 2014, *Perspectives on Psychological
Science* 9, 641-651).

Every study README and paper prints its power table. The numbers are lower
bounds on what the study could miss, because declustered catalogues keep
some clustering and market returns have volatility clusters, both of which
widen the null. A reader should compare a claimed effect with the table: a
practitioner's "Mars-Saturn raises quake risk by 20%" is untestable with a
study whose minimum detectable rate ratio is 2.

### Positive and negative controls

`stats.controls` makes controls first-class study inputs. A positive control
is a time-varying driver with a documented, small, real effect, tested
exactly like an indicator: for earthquakes the semidiurnal and spring-neap
tidal phase, built from the Moon's hour angle and the Moon-Sun elongation
(Ide, Yabe and Tanaka 2016, *Nature Geoscience* 9, 834-837; Cochran, Vidale
and Tanaka 2004, *Science* 306, 1164-1166); for floods the monsoon season. A
negative control is every registered indicator on a sky rotated by a fixed,
pre-declared offset (`shifted_sky`), which cannot carry a real signal
(Lipsitch, Tchetgen Tchetgen and Cohen 2010, *Epidemiology* 21, 383-388).

The paper then states one of two things. "The method detected the positive
control at RR x" means its nulls for the astrological indicators exclude
effects of about that size. "The method did not detect it" means those nulls
are uninformative about effects of the size a real geophysical driver has,
and the study can speak only to larger effects. The negative control should
give about alpha nominal results and none after correction; anything else
points to a broken null.

### The rule-free classifier

Rules name configurations; a classifier asks whether *any* function of the
sky predicts event days. `stats.classify.shifted_sky_auc_test` fits an
L2-penalised logistic model (scikit-learn when installed, otherwise the same
likelihood with L-BFGS) from sky features (sine and cosine of the
longitudes, speeds, tithi and nakshatra one-hot) to a 0/1 event series and
scores it with forward-chaining cross-validation, so no fold trains on its
own future (Bergmeir and Benitez 2012, *Information Sciences* 191, 192-213).
The penalty is fixed in advance; tuning it on test folds would leak.

The null is the same model refitted on the sky circularly shifted against the
events, which keeps every periodicity and autocorrelation of both and breaks
only their alignment. A seasonal or decadal pattern in the catalogue raises
the shifted-sky AUCs as much as the real one, so only alignment-specific
skill shows up as a small p. The report gives the AUC, the 5th, 50th and
95th percentiles of the shifted-sky AUCs and p, plus one frozen
train-on-explore, score-on-confirm AUC (Hanley and McNeil 1982, *Radiology*
143, 29-36).

### Bayesian summaries

A p-value above 0.05 does not distinguish "no effect" from "too little data".
`stats.bayes.posterior_log_rr` computes the posterior of log RR on a fine
grid, with the Poisson likelihood conditioned on the total count (which
removes the baseline rate), under a sceptical prior N(0, 0.1^2) (95% prior
mass between RR 0.82 and 1.22) and an enthusiastic prior N(0, 0.5^2) (RR 0.38
to 2.7); `summarise` reports both (Spiegelhalter, Freedman and Parmar 1994,
*JRSS A* 157, 357-416, for the sceptical and enthusiastic prior pair).

The Bayes factor against RR = 1 is the Savage-Dickey density ratio,
posterior over prior density at log RR = 0 (Dickey 1971, *Annals of
Mathematical Statistics* 42, 204-223; Wagenmakers et al. 2010, *Cognitive
Psychology* 60, 158-189). BF10 > 3 is moderate evidence for an effect, BF10 <
1/3 moderate evidence for none, and anything in between says the data cannot
decide. The prior widths are registered, not chosen per result.

### The combination atlas

Classical texts combine conditions (a planet in a sign, aspecting another,
during a dasha), and searching such combinations is the garden of forking
paths at scale (Gelman and Loken 2014, *American Scientist* 102, 460). The
atlas (`studies/combinations/`) declares the grammar in advance
(`grammar.yaml`), expands it deterministically into thousands of candidates
with ids (`scripts/enumerate.py`), and tests every testable candidate on the
exploration period against the circular-shift null with shared offsets,
corrects across the whole family with Benjamini-Yekutieli (Benjamini and
Yekutieli 2001, *Annals of Statistics* 29, 1165-1188) and gives the best
candidate a single-step Romano-Wolf max-|z| adjusted p (Romano and Wolf 2005,
*Econometrica* 73, 1237-1282).

Only survivors are tested once on the frozen confirmation period, and the
frozen exploration rates of the twenty best candidates are scored out of
sample with Hansen's SPA test (Hansen 2005, *Journal of Business and Economic
Statistics* 23, 365-380). Every candidate is published in
`artifacts/atlas.csv`, winners and losers, with its plain-words definition,
so a reader sees the full denominator. With thousands of candidates, dozens
of nominal p < 0.05 are expected by chance; the atlas's honest headline is
the number that survive correction and confirmation.
