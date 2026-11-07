# Astro-Fusion Research: Scientific Report Standards & Guidelines

**Document Purpose:** This is the authoritative reference that defines what every final PDF/Quarto report produced by this project MUST contain. It is the answer to the question: _"What does a complete, publication-quality Astro-Fusion research report look like?"_

**Version:** 1.0
**Status:** Mandatory — all `report.qmd` and `manuscript.qmd` files must conform.
**Applies To:** All use-case reports (`earthquake/`, `gold_market/`, `numerology/`) and the master manuscript.

---

## 0. The Core Problem This Document Solves

Our current reports (e.g., `research/use_cases/earthquake/report.qmd`) are ≈96 lines long. They contain:

- A brief abstract
- A description of the dataset
- One or two placeholder tables
- One or two figure references (which may not even be generated)
- A short conclusion

**What is missing:**

| Missing Element                                                      | Why It Matters                                                                  |
| :------------------------------------------------------------------- | :------------------------------------------------------------------------------ |
| Classical astrological combination definitions with source citations | Establishes the original hypothesis from canonical texts (Brihat Samhita, etc.) |
| Mathematical formulation of each combination                         | Makes the hypothesis falsifiable and reproducible                               |
| Time-variation graph of the combination vs. time                     | Shows _when_ the combination is active — the primary visual claim               |
| Overlay of real events on the combination graph                      | Visually tests whether events cluster during active combination windows         |
| Confusion matrix (TP, FP, FN, TN) per combination                    | Quantifies false positives and false negatives explicitly                       |
| Severity/magnitude stratification                                    | Tests if stronger combinations predict more severe events                       |
| Source traceability table                                            | Documents which ancient text, sutra number, or page references the combination  |
| Step-by-step validation narrative                                    | Walks reader through each stage: Hypothesis → Data → Computation → Result       |
| Interpretation of negative results                                   | Scientifically explains _why_ a null result is still a contribution             |

---

## 1. Report Architecture: Mandatory Section Structure

Every final report `.qmd` file MUST contain the following numbered sections in this order. Skipping a section requires a written justification in the report itself.

```
1.  Title Page / Front Matter
2.  Abstract
3.  1. Introduction & Motivation
4.  2. Background: The Astrological Hypothesis
    2.1  Classical Sources & Textual Evidence
    2.2  The Specific Combination(s) Under Study
    2.3  Mathematical Formulation
5.  3. Data & Methodology
    3.1  Astronomical Data (Swiss Ephemeris / DE440)
    3.2  Event Data (USGS, FRED, COMEX, etc.)
    3.3  Alignment Procedure
    3.4  Statistical Framework
6.  4. Combination Definition & Activation Windows
    4.1  Formal Definition of Each Combination
    4.2  Time-Series Graph: Combination Strength vs. Time
    4.3  Activation Window Table
7.  5. Results
    5.1  Temporal Correlation Analysis
    5.2  Event Overlay Graph (Combination + Events)
    5.3  Confusion Matrix & Classification Metrics
    5.4  False Positive Analysis
    5.5  False Negative Analysis
    5.6  Permutation / Monte Carlo Null Test
8.  6. Discussion
    6.1  Interpretation of Findings
    6.2  Potential Physical Mechanisms (if applicable)
    6.3  Confounders & Limitations
    6.4  Critical Self-Assessment
9.  7. Conclusion
10. References (with Classical + Modern sources)
11. Appendix A: Full Combination Catalog
12. Appendix B: Raw Data Summary Statistics
13. Appendix C: Code Reference
```

---

## 2. Section-by-Section Content Requirements

### 2.1 Title Page / Front Matter

The Quarto YAML front matter must include:

```yaml
title: "[Descriptive Title — include the specific phenomenon studied]"
subtitle: "[statistical method] — [dataset name & date range]"
date: last-modified
date-format: long
authors:
  - name: Astro-Fusion Research Team
    affiliation: Independent Computational Astrology Research Initiative
abstract: |
  [4-6 sentences: Problem → Hypothesis → Method → Key Result → Conclusion]
keywords:
  - [Classical astrology term]
  - [Statistical method used]
  - [Phenomenon studied]
  - [Validation technique]
format:
  pdf:
    documentclass: article
    papersize: a4
    number-sections: true
    toc: true
    toc-depth: 3
    fig-pos: "H"
    geometry:
      - top=25mm
      - left=25mm
      - right=25mm
      - bottom=25mm
    fontsize: 11pt
    csl: ../../reports/styles/nature.csl
bibliography: references.bib
```

### 2.2 Abstract (Required)

Must explicitly state:

1. The specific astrological combination(s) tested (by name — e.g., "Mangal-Ketu Yoga")
2. The event dataset (e.g., "USGS ComCat, M≥5.0, 1900-2023")
3. The primary statistical test (e.g., "Chi-square test with Monte Carlo null distribution")
4. The numerical result (e.g., "_p_ = 0.12, failing to reject H₀")
5. The conclusion regarding falsification

### 2.3 Section 1: Introduction & Motivation

**Minimum length:** ~400 words.

Must include:

- The "Prediction Gap" problem in the domain (seismology, finance, etc.)
- Why astrological/numerological variables are worth testing _as a signal processing question_
- A clear statement of what this study contributes to the open literature
- An overview paragraph for each subsequent section

### 2.4 Section 2: Background: The Astrological Hypothesis

This is the **most critical section that is currently missing from all reports**.

#### 2.4.1 Classical Sources & Textual Evidence

For each combination tested, you MUST provide a **Source Citation Table** in this format:

```markdown
| Combination             | Classical Source              | Text Reference       | Original Language Extract     | Interpretation                            |
| :---------------------- | :---------------------------- | :------------------- | :---------------------------- | :---------------------------------------- |
| Mars-Ketu Conjunction   | Brihat Samhita                | Chapter 17, Verse 14 | "Kujah Ketunā yutaḥ..."       | Mars + Ketu in same sign → seismic unrest |
| Mars-Saturn Conjunction | Phaladeepika                  | Chapter 3, Verse 21  | "Śanaiścaraś ca Kujayukte..." | Mars + Saturn conjunction → disasters     |
| Rahu-Ketu Axis          | Brihat Parashara Hora Shastra | Chapter 45           | "..."                         | Nodal axis activations                    |
```

**Required sources to cite (where applicable to the combination):**

- Varahamihira: _Brihat Samhita_ (Mundane astrology — world events, earthquakes, famine)
- Parasara: _Brihat Parashara Hora Shastra_ (Foundational Vedic rules)
- Mantreswara: _Phaladeepika_ (Planetary yogas and their effects)
- Kalyanarma: _Saravali_ (Planetary combinations)
- Ramanujacharya: _Bhavartha Ratnakara_ (House significations)
- _Jaimini Sutras_ (Special lagnas and karakas)
- Modern: Krishnamurti Paddhati (KP System) where star-lord combinations are used

For **numerological combinations**, cite:

- Cheiro: _Book of Numbers_ (Western numerology foundations)
- Harish Johari: _Numerology: With Tantra, Ayurveda, and Astrology_
- Sepharial: _The Kabala of Numbers_

#### 2.4.2 The Specific Combination(s) Under Study

For EACH combination, provide a dedicated sub-section with:

**a) Name and Definition**
State the formal name in both Sanskrit (transliterated) and English.

> **Example:**
> _Mangal-Ketu Yoga_ (Mars-South Node Conjunction) — A malefic planetary yoga formed when Mangal (Mars) and Ketu (South Lunar Node) occupy the same zodiacal sign or are within 13° of arc of each other in the geocentric ecliptic coordinate system.

**b) Traditional Claim**
State precisely what the classical text claims will happen.

> **Example:**
> Per Varahamihira's _Brihat Samhita_ (Ch. 17), when Mangal approaches Ketu, _"there is fear of destruction from earthquakes, volcanic activity, and war in the region indicated by the sign."_

**c) Operational Hypothesis**
Translate the traditional claim into a falsifiable scientific hypothesis.

> **Example:**
> **H₁:** _The frequency of M≥5.0 earthquakes is significantly higher during periods when Mars and Ketu are within 13° of arc than during non-conjunction periods (χ² test, α = 0.05)._
> **H₀ (Null):** _The frequency of M≥5.0 earthquakes during Mars-Ketu conjunction windows is equal to the baseline rate expected from Poisson chance._

#### 2.4.3 Mathematical Formulation

For every combination, express it mathematically. Examples:

**Conjunction Criterion:**

$$
\text{Mars-Ketu Conjunction Active if: } |\lambda_{\text{Mars}} - \lambda_{\text{Ketu}}| \leq \theta_{\text{tol}}
$$

Where:

- $\lambda_{\text{Mars}}$ = geocentric ecliptic longitude of Mars (degrees)
- $\lambda_{\text{Ketu}}$ = geocentric ecliptic longitude of Ketu (degrees)
- $\theta_{\text{tol}}$ = tolerance angle (default: 13° per classical _drishti_ rules)

**Circular distance to handle 0°/360° wraparound:**

$$
\Delta\lambda = \min\left(|\lambda_1 - \lambda_2|,\ 360° - |\lambda_1 - \lambda_2|\right)
$$

**Activation Window Definition:**

$$
W_k = \{t : \Delta\lambda(t) \leq \theta_{\text{tol}}\}
$$

**Shadbala Strength Score** (where used):

$$
S_p = \sum_{i=1}^{6} w_i \cdot s_{p,i}
$$

Where $s_{p,i}$ are the six Bala components (Sthana Bala, Dig Bala, Kala Bala, Chesta Bala, Naisargika Bala, Drik Bala) and $w_i$ are normalization weights.

---

### 2.5 Section 4: Combination Definition & Activation Windows

#### 4.1 Activation Window Table

For each combination, include a table of all activation windows in the study period:

```
| Window # | Start Date | End Date | Duration (days) | Peak Separation (°) | Events in Window |
|:---:|:---|:---|:---:|:---:|:---:|
| 1 | 2020-03-12 | 2020-04-09 | 28 | 2.4° | 17 |
| 2 | 2021-09-01 | 2021-09-22 | 21 | 5.1° | 12 |
...
| Total | — | — | Σ | — | Σ |
```

#### 4.2 Time-Series Graph: Combination Strength vs. Time (**MANDATORY GRAPH**)

This graph MUST appear in the report. It shows:

- **X-axis:** Date (full study period)
- **Y-axis (primary):** Separation angle between the two planets (degrees)
- **Shaded red bands:** All periods where separation ≤ θ_tol (active conjunction windows)
- **Horizontal dashed line:** The threshold angle θ_tol
- **Y-axis (secondary, optional):** Planet Shadbala strength score

> This is the graph that the code in `earthquake_planetary_analysis.py::plot_conjunction_analysis()` already generates — it MUST be embedded in the QMD report, not just saved to disk.

**Required figure caption format:**

> _Figure N: Mars-Ketu Angular Separation over the Study Period (2020–2025). The blue line shows the geocentric ecliptic separation between Mars and Ketu calculated using the Swiss Ephemeris (DE440). Red shaded bands indicate periods when separation ≤ 13°, classified as active Mangal-Ketu Yoga windows per classical Vedic criteria (Varahamihira, Brihat Samhita, Ch. 17). The dashed horizontal line marks the 13° classical threshold._

#### 4.3 Event Overlay Graph (**MANDATORY GRAPH**)

This is the second mandatory graph per combination. It shows:

- **X-axis:** Date
- **Y-axis:** Event magnitude or intensity
- **Points/Bars:** All real events during the period (color-coded by magnitude)
- **Red shaded bands:** Same active combination windows from 4.2
- **Purpose:** Visual evidence test — do events cluster in the red bands?

**Required figure caption format:**

> _Figure N: Real Earthquake Events (M≥5.0, USGS ComCat) with Mars-Ketu Yoga Active Windows Overlaid. Red shaded bands indicate Mars-Ketu conjunction periods (separation ≤ 13°). Visual inspection tests whether seismic events cluster preferentially within these windows. Statistical quantification is provided in Section 5.3._

---

### 2.6 Section 5: Results

#### 5.1 Temporal Correlation Analysis

Must include a **full regression coefficient table** for every predictor variable:

```
| Predictor | Coefficient β | Std. Error | z-score | p-value | Significant (α=0.05) |
|:---|:---:|:---:|:---:|:---:|:---:|
| Intercept | -0.90 | 0.39 | -2.31 | 0.021 | Yes |
| Year Trend | 0.011 | 0.062 | 0.18 | 0.860 | No |
| Mars-Ketu Active | +0.183 | 0.119 | 1.54 | 0.124 | No |
| Mars-Saturn Active | +0.071 | 0.092 | 0.77 | 0.440 | No |
...
```

#### 5.2 Confusion Matrix & Classification Metrics (**MANDATORY TABLE**)

This is the section most critically missing from current reports. For **each combination**, compute a binary classification against the threshold (e.g., "predicts an M≥6.0 event within 30 days"):

```
| | Predicted: EVENT | Predicted: NO EVENT |
|:---|:---:|:---:|
| **Actual: EVENT** | TP = ? | FN = ? |
| **Actual: NO EVENT** | FP = ? | TN = ? |
```

Then compute and report all of:

$$
\text{Precision} = \frac{TP}{TP + FP}
$$

$$
\text{Recall (Sensitivity)} = \frac{TP}{TP + FN}
$$

$$
\text{Specificity} = \frac{TN}{TN + FP}
$$

$$
\text{F1-Score} = \frac{2 \cdot \text{Precision} \cdot \text{Recall}}{\text{Precision} + \text{Recall}}
$$

$$
\text{Matthews Correlation Coefficient (MCC)} = \frac{TP \cdot TN - FP \cdot FN}{\sqrt{(TP+FP)(TP+FN)(TN+FP)(TN+FN)}}
$$

$$
\text{False Positive Rate (FPR)} = \frac{FP}{FP + TN}
$$

$$
\text{False Negative Rate (FNR)} = \frac{FN}{FN + TP}
$$

**Summary table (one row per combination):**

```
| Combination | TP | FP | FN | TN | Precision | Recall | FPR | FNR | F1 | MCC |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| Mars-Ketu | 14 | 22 | 8 | 118 | 0.39 | 0.64 | 0.16 | 0.36 | 0.48 | 0.28 |
| Mars-Saturn | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... |
```

#### 5.3 False Positive Analysis (Dedicated Sub-Section)

Must contain:

1. **Definition used:** What constitutes a False Positive in this study (e.g., "a Mars-Ketu conjunction window where NO M≥6.0 earthquake occurred within 30 days")
2. **Enumerated list of all false positives** (by window date)
3. **Discussion:** Were there mitigating factors? (e.g., solar cycle, region, secondary combination absent?)
4. **Rate as a fraction of total conjunction windows**

Example paragraph format:

> _Of the 18 Mars-Ketu conjunction windows identified in the study period, 12 (66.7%) were False Positives — active conjunction windows with no M≥6.0 earthquake in the subsequent 30-day window. These windows span [dates]. The high FPR (0.67) indicates that the Mars-Ketu conjunction alone is insufficient as a binary trigger for seismic activity. However, in 8 of the 12 false positive cases, the contemporaneous Saturn-Rahu angle exceeded 60°, suggesting that a secondary combination filter may improve precision._

#### 5.4 False Negative Analysis (Dedicated Sub-Section)

Must contain:

1. **Definition used:** What constitutes a False Negative (e.g., "a major M≥6.5 earthquake that occurred outside any active combination window")
2. **Enumerated list of major false negative events** (by date, magnitude, region)
3. **Discussion:** Were there other active combinations present? What does the miss imply?
4. **Rate as a fraction of total major events**

Example paragraph format:

> _Of the 22 M≥6.5 earthquakes in the study period, 8 (36.4%) occurred outside any active Mars-Ketu conjunction window — classified as False Negatives. The most significant was the 2023-02-06 Türkiye earthquake (M7.8), which occurred 45 days after the nearest conjunction window closed. Examination of secondary indicators reveals that Saturn was within 12° of Rahu at the time, suggesting that multi-planet combinations beyond the pairwise Mars-Ketu Yoga may be required to capture full seismic precursor variance._

#### 5.5 Permutation / Monte Carlo Null Test Graph (**MANDATORY GRAPH**)

The Monte Carlo Permutation test result MUST be shown as a graph:

- **X-axis:** Δ-AIC or Chi-square statistic (or equivalent metric)
- **Y-axis:** Frequency count across N=1000 permutations
- **Grey histogram:** Distribution of the test statistic under the null (random data)
- **Red vertical line:** The actual observed test statistic from real data
- **Caption:** Must state the p-value and whether H₀ is rejected

**Required figure caption format:**

> _Figure N: Monte Carlo Null Distribution (N=1,000) for Mars-Ketu Yoga vs. Earthquake Frequency. The grey histogram displays the distribution of Chi-square statistics obtained after randomly shuffling the earthquake date series 1,000 times (destroying any temporal relationship with the conjunction windows). The red vertical line marks the Chi-square statistic observed in the real, unshuffled data (χ² = 3.21). The observed value falls within the 95th percentile of the null distribution (p = 0.17), indicating that the correlation is statistically indistinguishable from random chance under this test._

---

### 2.7 Section 6: Discussion

#### 6.1 Interpretation of Findings

Must address ALL of:

- What the results say about the specific classical claim
- Whether rejection of H₀ was achieved or not, and the exact numerical justification
- What fraction of events was captured vs. missed
- The signal-to-noise ratio of the combination

#### 6.2 Potential Physical Mechanisms

Even in a falsification study, this section must address:

- What proposed physical mechanism (if any) underpins the classic claim (e.g., gravitational tidal stress, electromagnetic)
- Why the mechanism would or would not expect the measured signal size
- Reference to peer-reviewed geophysical/astronomical literature

#### 6.3 Confounders & Limitations

Must enumerate:

- **Catalog incompleteness** (historical earthquake magnitudes are not homogeneous)
- **Solar cycle overlap** (11-year solar maximum may alias with planetary periods)
- **Regional vs. global averaging** (Koorma Chakra assigns regions to planetary rulers — global datasets dilute regional signals)
- **Multiple hypothesis testing** (Bonferroni or FDR correction must be mentioned)
- **Confirmation bias in classical selection** (classical literature may survive because cited predictions that came true, not the false ones)

#### 6.4 Critical Self-Assessment

This section must be brutally honest. Example framework:

> _This study has three principal weaknesses. First, [X]. Second, [Y]. Third, [Z]. These limitations are acknowledged and represent the primary targets for Phase 2 research, in which regionalized hypotheses using the Koorma Chakra framework will be evaluated against localized seismic catalogs._

---

## 3. Graph Production Standards

Every graph that is generated by a Python script MUST be embedded in the corresponding `.qmd` report. The following are mandatory graphs per report:

|  #  | Graph Name                                                  | Script Responsible                                              | Mandatory Section |
| :-: | :---------------------------------------------------------- | :-------------------------------------------------------------- | :---------------- |
| G1  | Combination Strength vs. Time (angular separation or score) | `earthquake_planetary_analysis.py::plot_conjunction_analysis()` | Section 4.2       |
| G2  | Event Overlay on Combination Windows                        | same script                                                     | Section 4.3       |
| G3  | Monte Carlo Null Distribution                               | `validate_results.py` or `earthquake_rigor_analysis.py`         | Section 5.5       |
| G4  | Confusion Matrix Heatmap                                    | `validate_results.py`                                           | Section 5.3       |
| G5  | Predicted Rate vs. Actual Rate (time-series)                | `train_models.py`                                               | Section 5.1       |
| G6  | Lomb-Scargle Periodogram (if frequency analysis used)       | `sea_analysis.py`                                               | Section 5.1       |
| G7  | ROC Curve (for binary classification)                       | `validate_results.py`                                           | Section 5.3       |

### Graph Quality Requirements

- **Resolution:** Minimum 300 DPI for all figures
- **Format:** `.pdf` (vector) for LaTeX/Quarto renders; `.png` (raster, 300 DPI) as fallback
- **Figure size:** Width = 90% of text width unless otherwise noted
- **Font size:** Axis labels minimum 10pt; title minimum 12pt; legend minimum 9pt
- **Color scheme:** Colorblind-safe palette (e.g., Seaborn's `colorblind` or `viridis`)
- **Caption:** Every figure must have a `#| fig-cap` Quarto caption (see format above)
- **Label:** Every figure must have a `#| label: fig-[kebab-case-name]` for cross-referencing

---

## 4. Classical Source Citation Standards

### 4.1 In-Text Citation Format

For each classical combination claim, cite in the format:
`(Varahamihira, Brihat Samhita, Ch. 17, v. 14)`

In the bibliography `.bib` file, classical sources use this format:

```bibtex
@Book{varahamihira_brihat_samhita,
  author    = {Varahamihira},
  title     = {Brihat Samhita},
  translator = {M. Ramakrishna Bhat},
  publisher = {Motilal Banarsidass},
  year      = {1981},
  address   = {Delhi, India},
  note      = {Sanskrit original, approximately 6th century CE. Commentary on mundane astrology including geophysical phenomena.}
}

@Book{parasara_bphs,
  author    = {Parasara},
  title     = {Brihat Parashara Hora Shastra},
  translator = {Girish Chand Sharma},
  publisher = {Sagar Publications},
  year      = {1994},
  address   = {New Delhi, India},
  note      = {Foundational Vedic astrology text. Specific planetary combination (Yoga) rules.}
}
```

### 4.2 Source Traceability Matrix

Include as **Appendix A** a comprehensive table of every combination tested and its origin:

```
| Combination | Sanskrit Name | Planet 1 | Planet 2 | Source Text | Chapter | Verse | Claimed Effect |
|:---|:---|:---|:---|:---|:---:|:---:|:---|
| Mars-Ketu Conjunction | Mangal-Ketu Yoga | Mars | South Node (Ketu) | Brihat Samhita | 17 | 14 | Earthquakes, volcanic activity |
| Mars-Saturn Conjunction | Mangal-Shani Yoga | Mars | Saturn | Phaladeepika | 3 | 21 | Disasters, military conflict |
| Kuja Dosha | Manglik Dosha | Mars | — (house position) | Parashara BPHS | 81 | 42 | Marital strife (not earth events) |
```

---

## 5. Use-Case Specific Requirements

### 5.1 Earthquake Use Case

**Combinations that MUST be analyzed and documented:**

| Priority | Combination                            | Source                |       Threshold       |            Window             |
| :------: | :------------------------------------- | :-------------------- | :-------------------: | :---------------------------: |
|    1     | Mars-Ketu Conjunction                  | Brihat Samhita Ch. 17 |          13°          |           ±30 days            |
|    2     | Mars-Saturn Conjunction                | Phaladeepika Ch. 3    |          15°          |           ±30 days            |
|    3     | Malefic Cluster (Mars+Saturn+Rahu)     | Brihat Samhita Ch. 18 |   Any 2 within 20°    |           ±45 days            |
|    4     | Rahu-Ketu Axis Activation              | Jaimini Sutras        | — (always 180° apart) | Transit over earthquake zones |
|    5     | Saturn-Rahu Conjunction (Shrapit Yoga) | Various               |          15°          |           ±60 days            |

**Each of these 5 combinations MUST have:**

- Its own sub-section with classical citation
- Its own time-series separation graph
- Its own event overlay graph
- Its own confusion matrix row
- Its own FP/FN analysis paragraph

**Data source requirements:**

- USGS ComCat API (already implemented in `earthquake_data_fetcher.py`)
- Minimum period: 2000–2023 for statistical power
- Minimum magnitude threshold: M≥5.0 for counts; M≥6.5 for major event analysis
- Declustering required (Gardner-Knopoff algorithm)

### 5.2 Gold Market Use Case

**Combinations that MUST be analyzed:**

| Priority | Combination                       | Source / Concept      | Claimed Effect           |
| :------: | :-------------------------------- | :-------------------- | :----------------------- |
|    1     | Venus Retrograde                  | Classical             | Gold price reversal      |
|    2     | Jupiter-Venus Angle               | Jyotish — Guru-Shukra | Prosperity, gold bullish |
|    3     | Saturn Stationary/Retrograde      | Classical             | Market stagnation        |
|    4     | Mars Speed (direct to retrograde) | Brihat Samhita        | Commodity volatility     |
|    5     | Mercury Retrograde frequency      | Western astrology     | Market confusion         |
|    6     | Solar Ingress into Taurus         | Classical             | Gold season              |

**Each combination needs the same graph + analysis treatment as earthquake.**

### 5.3 Numerology Use Case

**Combinations to document:**

| Priority | Variable                           | Source                        | Claim                       |
| :------: | :--------------------------------- | :---------------------------- | :-------------------------- |
|    1     | Universal Day Number (UDN) 8       | Cheiro, Book of Numbers Ch. 8 | Extremity, destruction days |
|    2     | Universal Year Number              | Cheiro                        | Annual cycle quality        |
|    3     | Compound Number 17 (Star of Venus) | Cheiro, Ch. 17                | Financial luck              |
|    4     | Pythagorean Life Path interaction  | Pythagorean numerology        | Personal macro-cycles       |

---

## 6. Report Length Expectations

Based on publication standards for comparable empirical research papers, the minimum expected length for each complete report is:

| Section                                   | Minimum Word Count |
| :---------------------------------------- | :----------------: |
| Abstract                                  |     200 words      |
| Introduction                              |     500 words      |
| Background & Classical Sources            |     800 words      |
| Data & Methodology                        |     600 words      |
| Combination Definitions (per combination) |     300 words      |
| Results                                   |     700 words      |
| Discussion                                |     600 words      |
| Conclusion                                |     250 words      |
| **Total Minimum**                         |  **~3,950 words**  |

With graphs, tables, equations, and appendices, the final compiled PDF should be **12–20 pages** (A4, 11pt).

> The current earthquake `report.qmd` is approximately 600 words and 4 pages. This is **insufficient by a factor of ~4x to ~5x**.

---

## 7. Implementation Priority Plan

### Phase 1 (Immediate — Current Sprint)

1. **Earthquake report** — rewrite `research/use_cases/earthquake/report.qmd` to full standard format
   - Embed all 5 combination analyses
   - Embed G1, G2, G3, G4 graphs (already generated — just need embedding)
   - Add classical source citation table
   - Add confusion matrix table with FP/FN sub-sections

2. **Gold market report** — rewrite `research/use_cases/gold_market/GOLD_MARKET_PLANETARY_CORRELATION_ANALYSIS.qmd`
   - Add Venus Retrograde and Jupiter-Venus combination analysis sections
   - Embed Molchan diagram with proper caption
   - Add Monte Carlo null distribution graph

### Phase 2 (Next Sprint)

3. **Numerology report** — rewrite `research/use_cases/numerology/numerology_planet_timeline.qmd`
4. **Master manuscript** — update `research/reports/manuscript.qmd` to cite all use-case results

### Phase 3 (Publication Preparation)

5. Final cross-reference check: all figures referenced in text are embedded
6. Bibliography completeness: all classical sources have full `.bib` entries
7. Supplement: include link to code repository and data DOI
8. Blind peer review preparation: anonymize author affiliations

---

## 8. Quality Gate Checklist

Before any report is considered "done," the following checklist must be fully checked:

**Content:**

- [ ] Abstract states specific combination names, dataset, test used, numerical result
- [ ] Every tested combination has a classical source citation (text, chapter, verse)
- [ ] Every tested combination has a formal mathematical definition
- [ ] Every tested combination has a time-series separation graph (G1)
- [ ] Every tested combination has an event overlay graph (G2)
- [ ] Monte Carlo null distribution graph is embedded (G3)
- [ ] Confusion matrix table is present (TP/FP/FN/TN explicitly stated)
- [ ] False Positive analysis section written (with example FP windows enumerated)
- [ ] False Negative analysis section written (with example FN events enumerated)
- [ ] F1-Score, Precision, Recall, FPR, FNR are computed and reported
- [ ] MCC (Matthews Correlation Coefficient) is reported
- [ ] Discussion section includes confounders (solar cycle, regional averaging, catalog issues)
- [ ] Critical self-assessment section is present
- [ ] Conclusion restates numerical result and explicitly states H₀ accepted or rejected

**Technical:**

- [ ] All figures have `#| label: fig-*` and `#| fig-cap:` Quarto attributes
- [ ] All tables have `#| label: tbl-*` and `#| tbl-cap:` Quarto attributes
- [ ] References in text use `@key` format and appear in `references.bib`
- [ ] `references.bib` includes at least one classical Sanskrit source
- [ ] Quarto renders to PDF without errors (`quarto render report.qmd --to pdf`)
- [ ] All figures are generated before the render (or use `#| cache: true` appropriately)
- [ ] PDF is ≥12 pages (as output sanity check)

---

## 9. Example: What the Earthquake Report's Combination Section Should Look Like

The following is a minimal example of what **Section 2.4.2** for the Mars-Ketu combination should look like in the final `.qmd` file. Use this as a template for every other combination.

````markdown
## 2.4 The Specific Combinations Under Study

### 2.4.1 Combination 1: Mangal-Ketu Yoga (Mars–South Node Conjunction)

**Classical Source:**
Varahamihira, _Brihat Samhita_, Chapter 17 ("On Planetary Positions and National Events"),
Verse 14: _"Kujah Ketunā yutaḥ bhūmi-kampam karoti"_ — "Mars joined with Ketu causes trembling of the earth."
[Translation: M. Ramakrishna Bhat, Motilal Banarsidass, 1981]

**Interpretation:**
Classical Vedic mundane astrology treats Mars (_Mangal_) as the karaka (significator) of fire, violence, and explosive energy. Ketu (South Lunar Node) represents sudden, karmic disruptions. Their combination in the same sign or close degree proximity is considered a high-energy malefic yoga conducive to geophysical disturbances.

**Operational Hypothesis:**

- **H₁:** The rate of M≥5.0 earthquakes during periods when |λ_Mars − λ_Ketu| ≤ 13° is significantly higher than the baseline rate.
- **H₀:** The earthquake rate during Mars-Ketu conjunction windows does not differ from the Poisson baseline rate.
- **Significance level:** α = 0.05 (Bonferroni-corrected for 5 simultaneous combination tests: α_adj = 0.01)

**Mathematical Definition:**

$$
\text{Active if: } \min\left(|\lambda_M - \lambda_K|,\ 360° - |\lambda_M - \lambda_K|\right) \leq 13°
$$

**Tolerance Justification:**
13° is used as the classical _orb_ or _drishti_ tolerance. Per Parasara (_BPHS_, Ch. 24), conjunction effects begin when planets are within one sign (30°) and peak within 13°. We use 13° as the primary test threshold with sensitivity analysis at 8° and 20°.

```python
#| echo: false
#| label: fig-mars-ketu-separation
#| fig-cap: "Mars-Ketu Angular Separation (2000-2023). Red shaded bands indicate active conjunction windows (≤13°). Source: Swiss Ephemeris DE440."
#| fig-width: 10
#| fig-height: 5

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
# ... [embed the plot_conjunction_analysis output here]
```
````

---

_This document is the contract for all report authors and contributors. Any report submitted for Quarto rendering that does not meet these standards will be returned for revision before PDF generation is attempted._

_Last updated: 2026-02-20 | Maintainer: Astro-Fusion Research Team_
