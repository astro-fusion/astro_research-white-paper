# **Architectural Standards for Automated Scientific Reporting: A Comprehensive Guide to Transitioning from Exploratory Data Science to International-Level Publication**

## **Executive Summary**

The transformation of a GitHub repository containing disparate data analysis scripts into a cohesive, submission-ready scientific manuscript is a rigorous intellectual and architectural process. The user’s dissatisfaction with the current state of their report—specifically within the context of data-driven research on controversial or complex topics like "Gold Price vs. Astrology"—reflects a common tension in modern data science: the gap between *finding* a result and *communicating* it with sufficient rigor to withstand peer review.

This document serves as an exhaustive structural analysis and operational manual for bridging that gap. It is designed to guide the researcher through the entire lifecycle of report generation, from the epistemological foundations of "Severe Testing" in statistics to the technical implementation of automated pipelines using Python, Quarto, and LaTeX. We utilize the specific use case of testing financial astrology against gold prices not merely as a curiosity, but as a stress test for the scientific method. If a reporting structure can rigorously, dispassionately, and reproducibly evaluate a pseudoscientific claim using high-level econometrics, it is sufficiently robust for any conventional domain in the physical or social sciences.

The following analysis draws upon the standards of premier journals such as *Nature Scientific Reports* and *IEEE Transactions*, integrating best practices in software engineering (Cookiecutter Data Science) with the philosophical demands of the IMRaD (Introduction, Methods, Results, Discussion) structure.

## ---

**Part I: The Epistemology of the Scientific Record**

### **1.1 The Crisis of the "Unhappy" Report**

The modern data scientist often resides in a "notebook" environment—typically Jupyter or RStudio—where code, visualization, and commentary are intermingled in a stream-of-consciousness format. While excellent for exploration, this format is catastrophic for reporting.1 The user’s expressed "unhappiness" with their current report structure is a symptom of a fundamental misalignment between the *process of discovery* (which is non-linear, messy, and iterative) and the *product of research* (which must be linear, logical, and conclusive).

A GitHub repository that simply dumps code and results fails to meet the "International Standard" because it places the cognitive burden on the reader to synthesize the findings. A professional report must curate the narrative. It must distinguish between *data* (raw numbers) and *evidence* (numbers interpreted within a theoretical framework). In the context of "Gold vs. Astrology," a repository that merely shows a correlation plot is scientifically worthless. A report that structures this plot within a framework of stationarity testing, Bonferroni corrections, and falsification criteria transforms that same image into scientific evidence.3

### **1.2 The Immutable Skeleton: IMRaD as a Cognitive Scaffold**

Regardless of the discipline—whether submitting to the narrative-driven *Nature* or the technical-heavy *IEEE*—the IMRaD structure (Introduction, Methods, Results, and Discussion) remains the global gold standard.1 This structure is not an arbitrary bureaucratic requirement; it is a cognitive scaffold that mirrors the scientific method itself.

#### **1.2.1 The Introduction: The Funnel of Context**

The introduction must act as a funnel, starting with the broadest context and narrowing rapidly to the specific research question. It is the "Hook" that justifies the reader's time.7

* **The Broad Context:** In our case study, this is the Efficient Market Hypothesis (EMH). The introduction must ground the "Astrology" question not in mysticism, but in the search for *exogenous predictors* in financial time series.
* **The Gap:** What is missing? "While macroeconomic indicators are well-studied, the statistical validity of alternative cyclic predictors, such as astronomical phenomena, lacks rigorous empirical testing despite persistent anecdotal prevalence."
* **The Specific Objective:** "This study applies high-dimensional spectral analysis and Granger causality tests to falsify the hypothesis that planetary orbital mechanics influence XAU/USD spot prices."

#### **1.2.2 The Methods: The Engine of Trust**

In data-driven research, the Methods section is the most critical component for reproducibility. It must provide a "recipe" so precise that an independent researcher could replicate the findings using only the raw data and the manuscript.8

* **Data Provenance:** Precise definitions of data sources (e.g., "Daily spot gold prices from COMEX, accessed via Yahoo Finance API, adjusted for splits and dividends").
* **Preprocessing:** Detailed accounts of transformations. "Data was log-differenced to achieve stationarity, confirmed via the Augmented Dickey-Fuller test ((image omitted))."
* **Algorithmic Transparency:** If using a Lomb-Scargle periodogram, the report must specify the implementation (e.g., astropy.timeseries.LombScargle), the frequency grid used, and the method for calculating False Alarm Probabilities (FAP).10

#### **1.2.3 The Results: Dispassionate Observation**

The Results section must be agnostic to the researcher's desires. It is a historical record of what the algorithms output.

* **Separation of Church and State:** The Results section reports *what happened*. The Discussion section interprets *what it means*. These must never be mixed in a standard IMRaD format (though *Nature* sometimes allows a combined "Results and Discussion").2
* **Visual Evidence:** In our case, this includes the Molchan Diagram for event prediction and the Periodogram for cycle detection. These visuals must be polished, annotated, and self-explanatory.

#### **1.2.4 The Discussion: Synthesis and Implications**

This is where the raw data is transmuted into knowledge.

* **Interpretation:** "The failure of Granger causality to reject the null hypothesis suggests that planetary positions do not contain information useful for forecasting gold returns."
* **Limitations:** Acknowledge the boundaries. "This study utilized daily closing prices; intraday volatility or high-frequency trading anomalies were not captured."
* **Implications:** "These findings reinforce the EMH and suggest that 'financial astrology' provides no alpha beyond random chance, serving as a cautionary tale for the use of high-dimensional alternative data without theoretical grounding".1

## ---

**Part II: Deep Structural Analysis of Journal Requirements**

To create a "standard, international-level" report, one must understand the subtle differences between target publications. The structure of the report must be polymorphic—capable of shifting emphasis depending on the target audience while maintaining the same core data.

### **2.1 The *Nature Scientific Reports* Archetype**

Journals in the *Nature* portfolio prioritize broad scientific interest, narrative flow, and the implication of the findings on the wider body of knowledge.2

| Component | Requirement for Nature Style | Implementation for "Gold vs. Astrology" |
| :---- | :---- | :---- |
| **Title** | Declarative and Impactful. | "Rigorous Statistical Falsification of Exogenous Planetary Predictors in Global Gold Markets." |
| **Abstract** | Unstructured, narrative summary (\~150 words). | Focus on the tension between pseudoscience and market efficiency. Highlight the method (Lomb-Scargle) and the definitive negative result. |
| **Introduction** | Broad, accessible to non-specialists. | Discuss the history of "magical thinking" in markets vs. the mathematical reality of stochastic processes. |
| **Results** | Prominent, visually rich. | High-resolution spectral density plots. Use "The data indicates..." rather than "We found...". |
| **Methods** | Often placed at the end or in "Supplementary Information." | Concise summary of the data pipeline. Detailed math goes to the appendix. |
| **Discussion** | Integrated with context. | Discuss the psychological allure of patterns (Apophenia) and how statistical rigor protects against it. |

### **2.2 The *IEEE Transactions* Archetype**

Journals like *IEEE Transactions on Knowledge and Data Engineering* or *IEEE Transactions on Computational Social Systems* prioritize technical novelty, algorithmic rigor, and engineering contributions.15

| Component | Requirement for IEEE Style | Implementation for "Gold vs. Astrology" |
| :---- | :---- | :---- |
| **Title** | Technical and Specific. | "A Hybrid Vector Autoregression and Spectral Analysis Framework for Testing Non-Stationary Financial Time Series against Exogenous Cyclic Signals." |
| **Abstract** | Structured (Background, Method, Result, Conclusion). | Explicitly mention the algorithms: "We employ a customized Lomb-Scargle implementation with bootstrapping for False Alarm Probability..." |
| **Introduction** | Technical gap analysis. | Focus on the difficulty of handling irregular time series (weekends/holidays) in financial data and the limitations of standard FFT. |
| **Methodology** | Central and expansive. | Equations for the Granger Causality test and the VAR model specification must be in the main text. |
| **Experiments** | "Experiments" rather than "Results." | Focus on the robustness of the pipeline. Performance metrics (RMSE, MAE) of the forecasting model.17 |
| **Conclusion** | Summary of technical contribution. | "We present a reusable pipeline for evaluating alternative data." |

### **2.3 Structural Diagnosis of the User's "Current State"**

Based on the user's "unhappiness," we can infer the current report likely suffers from the following deficits, which the new structure must correct:

1. **Lack of Theoretical Anchoring:** The current report likely jumps straight to charts without establishing *why* the analysis matters (EMH vs. Behavioral Finance).
2. **Weak Statistical Justification:** It likely presents correlations without proving stationarity (a fatal error in time series analysis).
3. **Visual Clutter:** It likely uses default Matplotlib charts rather than publication-quality, annotated figures.
4. **Reproducibility Failure:** The code is likely not separated from the text, making it hard for a reader to verify the logic without wading through Python syntax.

## ---

**Part III: The Case Study – Rigorous Methodology for "Gold Price vs. Astrology"**

To elevate a topic like "financial astrology" from a blog post to a research paper, one must apply the principles of **"Severe Testing"**.4 We do not ask "does it work?" (which invites confirmation bias). We ask "can we break it?" We set up a null hypothesis that the relationship is zero, and we only accept the alternative if the data forces us to.

This section outlines the **concrete structure** required for the methodology section of the report.

### **3.1 Hypothesis Formulation**

A scientific report must be driven by falsifiable hypotheses.

* (image omitted) **(Null):** There is no statistical causal relationship between planetary positions (geocentric longitude, declination, or aspect) and the log-returns of Gold (XAUUSD). The inclusion of planetary variables in a Vector Autoregression (VAR) model does not reduce the Akaike Information Criterion (AIC) compared to a univariate autoregressive model.
* (image omitted) **(Alternative):** Planetary positions provide unique information that significantly reduces the forecast error of Gold prices, exhibiting Granger Causality with a p-value (image omitted) (after Bonferroni correction).

### **3.2 Data Acquisition and Preprocessing Protocol**

A rigorous methodology section begins with the data. The report must detail the "ETL" (Extract, Transform, Load) process.

#### **3.2.1 The Target Variable: Gold (XAUUSD)**

Gold prices are a non-stationary financial time series. Raw prices cannot be used for correlation analysis because they contain trends (inflation, long-term growth) that yield spurious correlations.19

* **Step 1: Ingestion.** Download daily close prices from a reliable vendor (e.g., Yahoo Finance via yfinance, or Bloomberg).
* **Step 2: Transformation.** Convert to Log Returns to approximate continuous compounding and stabilize variance:
  (image omitted)
* **Step 3: Stationarity Test.** Apply the **Augmented Dickey-Fuller (ADF)** test.
  * *Report Requirement:* The report must include a table showing the ADF statistic and p-value.
  * *Critical Threshold:* The p-value must be (image omitted) to reject the presence of a unit root. If raw prices are used ((image omitted)), the results are statistically invalid.21

#### **3.2.2 The Exogenous Variable: Planetary Ephemerides**

Astrological data is complex because planets move in continuous cycles, but their "aspects" (geometric angles like 90° or 180°) are discontinuous events.

* **Continuous Data:** Geocentric Longitude ((image omitted)). This is cyclical. Linear regression fails here because (image omitted) is numerically far from (image omitted), despite being spatially adjacent.
  * *Methodological Fix:* The report must describe the use of Trigonometric Encoding: (image omitted), (image omitted).
* **Discrete Data:** Retrograde periods (binary 0/1) or Aspects (Conjunctions, Squares).
* **Alignment:** Financial markets close on weekends; planets do not. The planetary data must be re-indexed to match market trading days. The report must explicitly state how this was handled (e.g., "Non-trading days were dropped from the planetary dataset to align with the XAUUSD index").22

### **3.3 Statistical Methodology: The Engine of Validation**

#### **3.3.1 Cycle Detection: The Lomb-Scargle Periodogram**

Since financial data often has gaps (holidays/weekends) and planetary data is continuous, the standard Fourier Transform (FFT) is strictly mathematically inappropriate (it introduces spectral leakage). The **Lomb-Scargle Periodogram** is the gold standard in astrophysics for detecting periodicity in unevenly spaced data.10

* **Application:** The report must show the periodogram of Gold Log-Returns.
* **Test Logic:** If astrology is true, we should see significant power spikes at known planetary frequencies (e.g., the 29.5-day lunar synodic cycle, the 88-day Mercury cycle).
* **Significance Testing:** We must calculate the False Alarm Probability (FAP). A spike is only real if the FAP (image omitted). If the periodogram of gold prices looks like white noise (flat) or only shows weekly/yearly seasonality, the cyclic hypothesis is rejected.24

#### **3.3.2 Granger Causality: Testing Predictive Power**

Granger Causality is the econometric standard for testing whether one time series is useful in forecasting another.26 It does not test "true" causality but tests *predictive precedence*.

* **Model Specification:** Vector Autoregression (VAR).
  (image omitted)
* **Test:** We perform an F-test on the coefficients (image omitted).
* **Null Hypothesis:** (image omitted). (Planetary lags do not improve the prediction of Gold).
* **The Bonferroni Correction:** Astrology involves many variables (10 planets, 5 major aspects). If we test 50 combinations, we might find a "significant" result by chance. The report must describe the use of the Bonferroni correction: dividing the p-value threshold (0.05) by the number of hypotheses tested ((image omitted)).29
  (image omitted)
  *This is a hallmark of international-level rigor.*

#### **3.3.3 Validation: Molchan Diagrams & The Problem of "Event" Prediction**

Astrologers often claim to predict "crashes" or "reversals" rather than continuous prices. This is a binary classification problem.

* **Metric:** We use the **Molchan Diagram**, borrowed from earthquake prediction science.30
* **X-axis:** Fraction of time declared as an "alarm" (e.g., "Mars is retrograde, beware\!").
* **Y-axis:** Miss rate (how many crashes happened when no alarm was sounded).
* **Diagonal:** Random guessing.
* **Result:** If the curve stays on the diagonal, the astrological prediction is no better than a coin flip. This is a devastatingly effective visual for debunking pseudoscientific claims in a research paper.

## ---

**Part IV: The Automated Report Generation Architecture**

To achieve the "International-Level" process requested, we must abandon the manual creation of graphs and tables. We propose a pipeline using **Python** for analysis and **Quarto** for typesetting. This ensures that the report is a *living document*.

### **4.1 Directory Structure (Cookiecutter Data Science)**

Adopting a standard folder structure ensures reproducibility and allows other researchers to immediately understand the project layout.33

| Directory | Purpose | Content Description |
| :---- | :---- | :---- |
| data/raw/ | Immutable Data | Original CSVs from Yahoo/NASA. Never edit these manually. |
| data/processed/ | Clean Data | Stationarized gold prices, aligned planetary ephemerides. |
| notebooks/ | Sandbox | Jupyter notebooks for exploration (01\_EDA.ipynb). Not for the final report. |
| src/ | Production Code | Python scripts (.py) that perform the heavy lifting. |
| src/data/ | ETL Scripts | make\_dataset.py (Downloads and cleans data). |
| src/models/ | Analysis Scripts | granger\_test.py, lomb\_scargle.py. |
| reports/ | Final Output | The compilation target. |
| reports/manuscript.qmd | Source Text | The Quarto file containing the text and code bindings. |
| reports/figures/ | Artifacts | SVG/PDF plots generated by src scripts. |

### **4.2 The Automation Pipeline (Python)**

The code should be modular. We do not run analysis *in* the report file; we run analysis to *generate artifacts* (tables/figures) that the report file *consumes*.

**Module 1: fetch\_data.py**

Uses yfinance to get Gold data and skyfield or flatlib (Python astrology libraries) to calculate planetary positions.

**Module 2: statistics.py**

Contains the rigorous tests.

Python

\# Conceptual implementation of a robust stationarity check
from statsmodels.tsa.stattools import adfuller

def check\_stationarity(timeseries, name):
    result \= adfuller(timeseries)
    p\_value \= result
    is\_stationary \= p\_value \< 0.05
    return {
        "Variable": name,
        "ADF Statistic": round(result, 4),
        "p-value": round(p\_value, 4),
        "Stationary": "Yes" if is\_stationary else "No"
    }

*Insight:* By wrapping this in a function, we can loop through 100 different assets or planetary aspects and generate a summary table automatically.21

**Module 3: generate\_report\_artifacts.py**

This script runs the analysis and saves:

* table\_stationarity.csv
* plot\_periodogram.pdf
* results\_granger.json (containing p-values and F-stats)

### **4.3 The Manuscript Engine (Quarto)**

Quarto is the successor to RMarkdown and allows for "parametric" reporting.37 It can render to PDF (using LaTeX engines) for journals or HTML for the web.

**The .qmd File Structure:**

YAML

\---
title: "A Statistical Evaluation of Exogenous Cyclic Predictors in XAUUSD"
format:
  nature-pdf:
    keep-tex: true
  ieee-pdf:
    keep-tex: true
bibliography: references.bib
\---

\# Introduction
The search for predictive signals...

\# Methodology
\#\# Data Preprocessing
We utilized daily closing prices for Gold... Stationarity was tested using the ADF test (Table @tbl-stationarity).

\#| label: tbl-stationarity
\#| tbl-cap: "Augmented Dickey-Fuller Test Results"
import pandas as pd
from IPython.display import Markdown
df \= pd.read\_csv("../reports/table\_stationarity.csv")
Markdown(df.to\_markdown(index=False))

\# Results
\#\# Spectral Analysis
Figure @fig-lomb shows the Lomb-Scargle periodogram...

\#| label: fig-lomb
\#| fig-cap: "Lomb-Scargle Periodogram of Gold Log-Returns"
\#| out-width: 100%
\!("../reports/figures/plot\_periodogram.pdf")

\# Discussion
Our analysis shows no significant spectral power at planetary frequencies...

*Key Advantage:* If you update your data (e.g., add 2024 data), you simply re-run the pipeline. The tables update, the p-values in the text update, and the PDF is regenerated. This is "Reproducible Research".40

## ---

**Part V: Detailed Section-by-Section Guide (The "Walkthrough")**

This section provides the specific content requirements for the user's report, mapping the "Gold vs. Astrology" use case to the IMRaD structure.

### **5.1 The Abstract**

* **Must-Have:** One sentence on background (EMH vs. Anomalies). One sentence on the specific hypothesis (Astrology). One sentence on methods (Granger/Lomb-Scargle). One sentence on results (Reject/Fail to Reject). One sentence on implication (Market Efficiency).
* **Keywords:** Financial Time Series, Granger Causality, Spectral Analysis, Efficient Market Hypothesis, Pseudoscience Demarcation.15

### **5.2 The Introduction**

* **Avoid:** Don't start by explaining what astrology is. Start with *Financial Markets*.
* **The Pivot:** "While behavioral finance acknowledges the role of human psychology, 'financial astrology' posits a deterministic exogenous force..."
* **Literature Review:** Cite *scientific* papers on market anomalies (e.g., Lunar phases in stock returns) to show you have done your homework, then pivot to why they are usually statistically flawed (e.g., lack of Bonferroni correction).42

### **5.3 The Methodology (The "Meat")**

* **Subsection 3.1: Data.** Explicitly state the date range (e.g., Jan 1, 2000 – Jan 1, 2024). State the source of Gold data (e.g., COMEX Spot). State the source of Ephemerides (e.g., NASA JPL DE440).
* **Subsection 3.2: Statistical Framework.**
  * Explain *why* you used Lomb-Scargle (uneven sampling).
  * Explain *why* you used Log-Returns (stationarity).
  * Explain the "Windowing" strategy (Rolling Granger Causality) if you checked for time-varying relationships.44
* **Subsection 3.3: Robustness Checks.** Mention that you tested against "Randomized Planetary Data" (shuffling the planet positions) to create a baseline for chance.45 This is a "Monte Carlo Permutation Test" and is highly respected in data science journals.

### **5.4 The Results**

* **Table 1:** Descriptive Statistics (Mean, Std Dev, Skewness, Kurtosis of Gold returns).
* **Table 2:** Unit Root Tests (ADF & KPSS results confirming stationarity after differencing).
* **Figure 1:** Time series plot of Gold vs. a normalized planetary cycle (visual check).
* **Figure 2:** The Lomb-Scargle Periodogram. (Likely showing noise, or daily/weekly cycles, but no planetary cycles).
* **Figure 3:** The Molchan Diagram. (Likely hugging the diagonal line).
* **Text:** "The Granger Causality test yielded an F-statistic of 1.23 (p \= 0.28), failing to reject the null hypothesis."

### **5.5 The Discussion**

* **The "Rebuttal":** If you find no correlation, framing is key. Do not say "Astrology is fake." Say "The results indicate that planetary positions contain no information gain for the prediction of XAUUSD that is not already captured by autoregressive lags." This is professional, scientific language.1
* **The "File Drawer" Problem:** Acknowledge that many positive results in this field are likely due to publication bias or p-hacking, which your rigorous methodology (Bonferroni correction, Out-of-sample testing) avoided.48

## ---

**Part VI: Automated Text Generation (Advanced)**

The user asked for a "data-driven research paper hosted on GitHub." Modern pipelines can go a step further and *generate* parts of the text based on the data, though this must be done with caution.

### **6.1 Python Libraries for Natural Language Generation**

* **Jinja2:** A templating engine. You can write a "template" discussion:"The ADF test returned a p-value of {{ p\_value }}. This indicates the series is {{ 'stationary' if p\_value \< 0.05 else 'non-stationary' }}." This ensures that if your data changes, your text never lies.50
* **ReportLab:** For generating PDFs directly from Python code, though Quarto is superior for academic layouts.51
* **Large Language Models (LLMs):** You can feed your results\_granger.json into a local LLM (like Llama 3 via Ollama) with a prompt: "Write a technical paragraph interpreting these Granger Causality results in the style of an IEEE paper."
  * *Warning:* LLMs hallucinate. In a research paper, *you* must verify every claim. Using templates (Jinja2) for the statistical facts is safer than using LLMs.52

## ---

**Part VII: Conclusions and Roadmap**

To move from an "unhappy" report to a "standard, international-level" submission, follow this roadmap:

1. **Phase 1: Structure (Days 1-2).** Set up the cookiecutter directory. Create the manuscript.qmd file with the target journal's template (Nature or IEEE).
2. **Phase 2: Rigor (Days 3-5).** Write the Python scripts to fetch Gold/Astrology data and run the "Severe Tests" (ADF, Lomb-Scargle, Granger, Monte Carlo Permutations). Ensure the code is modular.
3. **Phase 3: Automation (Days 6-7).** Bind the Python outputs to the Quarto document. Ensure that running quarto render builds the full PDF with updated tables and figures.
4. **Phase 4: Narrative (Days 8-10).** Write the Intro and Discussion around the automated results. Focus on the "Null Hypothesis" framework.
5. **Phase 5: Review.** Check against the "Checklist for Statistical Rigor" (Bonferroni corrections, Stationarity checks).

By treating the "Astrology" hypothesis with the same aggressive mathematical skepticism used for "Earthquake Prediction" or "Algorithmic Trading," the resulting report will not only be structurally sound but will demonstrate a level of scientific maturity that appeals to top-tier editors. The subject matter may be fringe, but the methodology must be mainstream and impeccable.

# **A Guide to the Scientific Validation of Financial Astrology Models**

## **1\. Introduction to the Methodology**

The application of the methodology outlined above to the specific case of "Gold vs. Astrology" requires a dedicated exploration of the scientific context. While often dismissed without investigation, "Financial Astrology" claims that celestial cycles (exogenous variables) drive market cycles (endogenous variables). To publish a paper on this, one must not mock the subject, but rather treat it as a **Signal Processing** problem.

### **1.1 The Theoretical Basis: EMH vs. Exogenous Cycles**

The Efficient Market Hypothesis (EMH) states that asset prices reflect all available information. If planetary cycles (which are public, deterministic, and predictable for thousands of years) actually influenced prices, rational arbitrageurs would have exploited this signal until it disappeared.

* *Hypothesis:* If a signal persists, the EMH is incomplete, or the signal is risk-based.
* *Counter-Hypothesis (Null):* The signal is illusory (Apophenia).

### **1.2 The "File Drawer" Effect in Astrology**

Most "evidence" for astrology comes from "p-hacking"—checking thousands of planetary combinations until one matches a market crash by chance. A rigorous report must explicitly account for this.

* **Standard:** Use a "Look-Elsewhere Effect" correction.
* **Implementation:** If you check Mars, Venus, and Jupiter against Gold, Silver, and SP500, you have performed (image omitted) tests. Your p-value threshold for significance is no longer 0.05, but (image omitted). The report must state this clearly.

## ---

**2\. Advanced Statistical Implementation Details**

### **2.1 The Vector Autoregression (VAR) Model**

To test if Planets cause Gold prices, we use VAR. This treats every variable as a function of the past values of every other variable.

(image omitted)

* **Granger Causality Test:** We check if (image omitted). If (image omitted) is significantly different from zero, it means past planetary values help predict current Gold values.
* **Stationarity Requirement:** VAR requires stationary data. If Gold is a random walk (non-stationary), the VAR results are invalid. This is why the **ADF Test** in the Data Preprocessing section is non-negotiable.

### **2.2 Handling the "Weekend Effect"**

Planets move on weekends; markets do not.

* **Bad Approach:** Interpolating Gold prices for weekends (invents data).
* **Rigorous Approach:** Re-indexing planetary data to "Trading Days."
  Python
  \# Python Pseudocode for Alignment
  gold\_index \= gold\_data.index \# DatetimeIndex of trading days
  planet\_data \= planet\_data.reindex(gold\_index, method='ffill')

  This ensures that we only test the planetary position *as it was known* on the trading day.

## ---

**3\. Visualizing the Null Hypothesis**

A major failing of amateur reports is the "Chart of Truth"—a single line chart showing two lines moving together. A professional report uses **Diagnostic Charts**.

### **3.1 The Cross-Correlation Function (CCF)**

Instead of one chart, show the correlation at different *lags*.

* **X-axis:** Lag (Days). \-10 to \+10.
* **Y-axis:** Correlation Coefficient.
* **Significance Bounds:** Blue dashed lines showing the 95% confidence interval for zero correlation.
* **Interpretation:** If the correlation bars are within the blue lines, there is no relationship.

### **3.2 The Bootstrapped Distribution**

To prove a result isn't random, shuffle the planetary data 10,000 times and recalculate the correlation.

* **Histogram:** Show the distribution of 10,000 random correlations.
* **Vertical Line:** Show the "Actual" correlation.
* **p-value:** The percentage of random correlations that are higher than the actual. If this is 30% (p=0.30), the result is random noise.

## ---

**4\. Final Recommendations for the User**

1. **Do not use the word "Prove".** Science does not prove; it fails to reject. Use "Demonstrate," "Indicate," "Suggest," or "Falsify."
2. **Focus on the Code Architecture.** A clean src folder with documented functions is as important as the text. It allows the reviewer to trust the result.
3. **Automate the Boring Stuff.** Use the Python scripts to generate your descriptive statistics tables. Don't type numbers manually. This prevents transcription errors.
4. **Embrace the Null.** A paper that rigorously proves astrology *doesn't* work is a valid scientific contribution to the field of Financial Econometrics. It establishes the lower bound of market efficiency.

By following this exhaustive guide, the user can transform their "unhappy" GitHub repository into a beacon of rigorous, reproducible data science that stands up to the scrutiny of the international scientific community.

#### **Works cited**

1. Scientific Writing: IMRaD \- Utah Valley University, accessed January 30, 2026, [https://www.uvu.edu/writingcenter/docs/scientificwriting.pdf](https://www.uvu.edu/writingcenter/docs/scientificwriting.pdf)
2. Structuring a Science Report | Academic Skills Kit \- Newcastle University, accessed January 30, 2026, [https://www.ncl.ac.uk/academic-skills-kit/assessment/assignment-types/structuring-a-science-report/](https://www.ncl.ac.uk/academic-skills-kit/assessment/assignment-types/structuring-a-science-report/)
3. Beware of Pseudoscience \- Dr. Sam Goldstein, accessed January 30, 2026, [https://samgoldstein.com/resources/articles/forensic-updates/forensic-update-beware-of-pseudoscience.aspx](https://samgoldstein.com/resources/articles/forensic-updates/forensic-update-beware-of-pseudoscience.aspx)
4. Falsification, Pseudoscience, Induction (Tour II) \- Statistical Inference as Severe Testing, accessed January 30, 2026, [https://www.cambridge.org/core/books/statistical-inference-as-severe-testing/falsification-pseudoscience-induction/A844660AD587D7EEA66E17DF27C4542E](https://www.cambridge.org/core/books/statistical-inference-as-severe-testing/falsification-pseudoscience-induction/A844660AD587D7EEA66E17DF27C4542E)
5. accessed January 30, 2026, [https://www.thesify.ai/blog/how-to-structure-a-scientific-research-paper-imrad-format-guide\#:\~:text=IMRaD%20stands%20for%20Introduction%2C%20Methods,logical%20flow%20of%20a%20study.](https://www.thesify.ai/blog/how-to-structure-a-scientific-research-paper-imrad-format-guide#:~:text=IMRaD%20stands%20for%20Introduction%2C%20Methods,logical%20flow%20of%20a%20study.)
6. Structuring your manuscript | Publish your research \- Springer Nature, accessed January 30, 2026, [https://www.springernature.com/gp/authors/campaigns/writing-a-manuscript/structuring-your-manuscript](https://www.springernature.com/gp/authors/campaigns/writing-a-manuscript/structuring-your-manuscript)
7. The introduction, methods, results, and discussion (IMRAD) structure: a fifty-year survey, accessed January 30, 2026, [https://pmc.ncbi.nlm.nih.gov/articles/PMC442179/](https://pmc.ncbi.nlm.nih.gov/articles/PMC442179/)
8. How to Write the Methods Section of a Research Paper \- Dartmouth Cancer Center, accessed January 30, 2026, [https://cancer.dartmouth.edu/sites/default/files/2019-05/methods-section.pdf](https://cancer.dartmouth.edu/sites/default/files/2019-05/methods-section.pdf)
9. How To Write The Methodology Chapter (With Examples) \- Grad Coach, accessed January 30, 2026, [https://gradcoach.com/how-to-write-the-methodology-chapter/](https://gradcoach.com/how-to-write-the-methodology-chapter/)
10. flatironinstitute/nifty-ls: A fast Lomb-Scargle periodogram. It's nifty, and uses a NUFFT\! \- GitHub, accessed January 30, 2026, [https://github.com/flatironinstitute/nifty-ls](https://github.com/flatironinstitute/nifty-ls)
11. Lomb-Scargle Periodograms — Astropy v8.0.0.dev308+g9805d6bf2, accessed January 30, 2026, [https://docs.astropy.org/en/latest/timeseries/lombscargle.html](https://docs.astropy.org/en/latest/timeseries/lombscargle.html)
12. Structuring a Science Report: IMRaD, accessed January 30, 2026, [https://www.ncl.ac.uk/mediav8/academic-skills-kit/file-downloads/Structuring%20a%20Science%20Report%20IMRaD.pdf](https://www.ncl.ac.uk/mediav8/academic-skills-kit/file-downloads/Structuring%20a%20Science%20Report%20IMRaD.pdf)
13. A Statistical Study of Astrology | PDF | Horoscope \- Scribd, accessed January 30, 2026, [https://www.scribd.com/document/487204758/A-Statistical-Study-of-Astrology](https://www.scribd.com/document/487204758/A-Statistical-Study-of-Astrology)
14. Nature Journal Manuscript Formatting Guide \- Pubrica, accessed January 30, 2026, [https://pubrica.com/academy/manuscript-editing/nature-journal-manuscript-formatting-guide/](https://pubrica.com/academy/manuscript-editing/nature-journal-manuscript-formatting-guide/)
15. Structure Your Article \- IEEE Author Center Journals, accessed January 30, 2026, [https://journals.ieeeauthorcenter.ieee.org/create-your-ieee-journal-article/create-the-text-of-your-article/structure-your-article/](https://journals.ieeeauthorcenter.ieee.org/create-your-ieee-journal-article/create-the-text-of-your-article/structure-your-article/)
16. Prepare your submission \- IEEE Antennas and Propagation Society, accessed January 30, 2026, [https://ieeeaps.org/ieee-tap/for-authors/how-to-prepare-your-submission](https://ieeeaps.org/ieee-tap/for-authors/how-to-prepare-your-submission)
17. SeismoQuakeGNN: a hybrid framework for spatio-temporal earthquake prediction with transformer-enhanced models \- PubMed Central, accessed January 30, 2026, [https://pmc.ncbi.nlm.nih.gov/articles/PMC12706585/](https://pmc.ncbi.nlm.nih.gov/articles/PMC12706585/)
18. Deborah Mayo | Statistics & Severe Testing vs Pseudoscience | Philosophy of Data Science, accessed January 30, 2026, [https://www.youtube.com/watch?v=MVHoE9V\_X5g](https://www.youtube.com/watch?v=MVHoE9V_X5g)
19. Gold Price Time Series Analysis \- Medium, accessed January 30, 2026, [https://medium.com/@emilychaukang/gold-price-time-series-analysis-154af77f22f2](https://medium.com/@emilychaukang/gold-price-time-series-analysis-154af77f22f2)
20. Forecasting Asset Prices Using VAR and Granger Causality \- KidQuant, accessed January 30, 2026, [https://kidquant.com/project/forecasting-var-granger-causlity/](https://kidquant.com/project/forecasting-var-granger-causlity/)
21. Forecasting Asset Prices Using VAR and Granger Causality \- GitHub, accessed January 30, 2026, [https://github.com/KidQuant/Forecasting-VAR-Granger-Causality/blob/master/Forecasting-VAR-Granger-Causlity.ipynb](https://github.com/KidQuant/Forecasting-VAR-Granger-Causality/blob/master/Forecasting-VAR-Granger-Causlity.ipynb)
22. How do you identify cyclic patterns in time series data? \- Milvus, accessed January 30, 2026, [https://milvus.io/ai-quick-reference/how-do-you-identify-cyclic-patterns-in-time-series-data](https://milvus.io/ai-quick-reference/how-do-you-identify-cyclic-patterns-in-time-series-data)
23. A Framework for Gold Price Prediction Combining Classical and Intelligent Methods with Financial, Economic, and Sentiment Data Fusion \- MDPI, accessed January 30, 2026, [https://www.mdpi.com/2227-7072/13/2/102](https://www.mdpi.com/2227-7072/13/2/102)
24. N-dimensional Lomb Scargle Periodogram analysis of traveling ionospheric disturbances using ionosonde data \- Frontiers, accessed January 30, 2026, [https://www.frontiersin.org/journals/astronomy-and-space-sciences/articles/10.3389/fspas.2024.1519436/full](https://www.frontiersin.org/journals/astronomy-and-space-sciences/articles/10.3389/fspas.2024.1519436/full)
25. Lomb-Scargle Periodogram \- YouTube, accessed January 30, 2026, [https://www.youtube.com/watch?v=WUi5H5JSKtY](https://www.youtube.com/watch?v=WUi5H5JSKtY)
26. Granger Causality between Stock and Gold Returns – Evidence from Poland, Hungary and the Czech Republic | Mamcarz, accessed January 30, 2026, [https://journals.umcs.pl/h/article/view/12319](https://journals.umcs.pl/h/article/view/12319)
27. testing the causality between bitcoin price and the gold price in the global market prime by granger \- Ekonomika, accessed January 30, 2026, [https://www.ekonomika.org.rs/en/PDF/ekonomika/2020/clanci20-3/7.pdf](https://www.ekonomika.org.rs/en/PDF/ekonomika/2020/clanci20-3/7.pdf)
28. I need to know steps of Granger Causality test in statistics. can anyone explain or give a reference, book name, slides, etc.? | ResearchGate, accessed January 30, 2026, [https://www.researchgate.net/post/I\_need\_to\_know\_steps\_of\_Granger\_Causality\_test\_in\_statistics\_can\_anyone\_explain\_or\_give\_a\_reference\_book\_name\_slides\_etc](https://www.researchgate.net/post/I_need_to_know_steps_of_Granger_Causality_test_in_statistics_can_anyone_explain_or_give_a_reference_book_name_slides_etc)
29. Detecting periodic patterns in unevenly spaced gene expression time series using Lomb–Scargle periodograms \- Oxford Academic, accessed January 30, 2026, [https://academic.oup.com/bioinformatics/article/22/3/310/220284](https://academic.oup.com/bioinformatics/article/22/3/310/220284)
30. Assessing Earthquake Forecast Performance Based on b Value in Yunnan Province, China, accessed January 30, 2026, [https://www.mdpi.com/1099-4300/23/6/730](https://www.mdpi.com/1099-4300/23/6/730)
31. Evaluating earthquake predictions and earthquake forecasts: a guide for students and new researchers \- CORSSA, accessed January 30, 2026, [http://www.corssa.org/export/sites/corssa/.galleries/articles-pdf/zechar.pdf\_2063069299.pdf](http://www.corssa.org/export/sites/corssa/.galleries/articles-pdf/zechar.pdf_2063069299.pdf)
32. Earthquake Forecasting Based on b Value and Background Seismicity Rate in Yunnan Province, China \- PMC \- PubMed Central, accessed January 30, 2026, [https://pmc.ncbi.nlm.nih.gov/articles/PMC11854019/](https://pmc.ncbi.nlm.nih.gov/articles/PMC11854019/)
33. Structuring your Project — Cookiecutter Data Science \- VC Edition v0.0.1, accessed January 30, 2026, [https://cookiecutter-data-science-vc.readthedocs.io/en/latest/getting\_started/INSTALL.html](https://cookiecutter-data-science-vc.readthedocs.io/en/latest/getting_started/INSTALL.html)
34. Cookiecutter Data Science, accessed January 30, 2026, [https://cookiecutter-data-science.drivendata.org/](https://cookiecutter-data-science.drivendata.org/)
35. Cookiecutter Data Science V2 \- DrivenData Labs, accessed January 30, 2026, [https://drivendata.co/blog/ccds-v2](https://drivendata.co/blog/ccds-v2)
36. Empirical Analysis and Forecasting of Gold Prices: Based on VAR Model \- ResearchGate, accessed January 30, 2026, [https://www.researchgate.net/publication/399222242\_Empirical\_Analysis\_and\_Forecasting\_of\_Gold\_Prices\_Based\_on\_VAR\_Model](https://www.researchgate.net/publication/399222242_Empirical_Analysis_and_Forecasting_of_Gold_Prices_Based_on_VAR_Model)
37. Quarto at Work: Streamline Reports and Share Insights \- Posit, accessed January 30, 2026, [https://posit.co/blog/quarto-at-work/](https://posit.co/blog/quarto-at-work/)
38. Quarto, accessed January 30, 2026, [https://quarto.org/](https://quarto.org/)
39. Generate 100s of custom reports in minutes with Python & Quarto\! (Parameterized report automation) \- YouTube, accessed January 30, 2026, [https://www.youtube.com/watch?v=\_kjs\_u3Ctt4](https://www.youtube.com/watch?v=_kjs_u3Ctt4)
40. Structuring data analysis projects in the Open Science era with Kerblam\! \- F1000Research, accessed January 30, 2026, [https://f1000research.com/articles/14-88/pdf](https://f1000research.com/articles/14-88/pdf)
41. Writing an Abstract for Your Research Paper, accessed January 30, 2026, [https://writing.wisc.edu/handbook/assignments/writing-an-abstract-for-your-research-paper/](https://writing.wisc.edu/handbook/assignments/writing-an-abstract-for-your-research-paper/)
42. Financial Analysis Method Based On Astrology, Fibonacci, And Astronacci To Find A Date Of Direction Inversion Base Information Technology \- Jci And Future Gold Prices \- ResearchGate, accessed January 30, 2026, [https://www.researchgate.net/publication/350796719\_Financial\_Analysis\_Method\_Based\_On\_Astrology\_Fibonacci\_And\_Astronacci\_To\_Find\_A\_Date\_Of\_Direction\_Inversion\_Base\_Information\_Technology\_-\_Jci\_And\_Future\_Gold\_Prices](https://www.researchgate.net/publication/350796719_Financial_Analysis_Method_Based_On_Astrology_Fibonacci_And_Astronacci_To_Find_A_Date_Of_Direction_Inversion_Base_Information_Technology_-_Jci_And_Future_Gold_Prices)
43. Financial Astrology: A Study on the Correlation Between Celestial Cycles and Financial Markets \- Oreate AI Blog, accessed January 30, 2026, [https://www.oreateai.com/blog/financial-astrology-a-study-on-the-correlation-between-celestial-cycles-and-financial-markets/80b8947367972652939aa9b6f454709f](https://www.oreateai.com/blog/financial-astrology-a-study-on-the-correlation-between-celestial-cycles-and-financial-markets/80b8947367972652939aa9b6f454709f)
44. Gold and inflation: Expected inflation effect or carrying cost effect? \- ScholarWorks @ UTRGV, accessed January 30, 2026, [https://scholarworks.utrgv.edu/ibe\_fac/25/](https://scholarworks.utrgv.edu/ibe_fac/25/)
45. Robustness Tests and Checks for Algorithmic Trading Strategies | Complete Guide, accessed January 30, 2026, [https://www.buildalpha.com/robustness-testing-guide/](https://www.buildalpha.com/robustness-testing-guide/)
46. How do you analyze the statistical significance of your trading strategy? : r/quant \- Reddit, accessed January 30, 2026, [https://www.reddit.com/r/quant/comments/18r0sdh/how\_do\_you\_analyze\_the\_statistical\_significance/](https://www.reddit.com/r/quant/comments/18r0sdh/how_do_you_analyze_the_statistical_significance/)
47. Granger-Causality test result interpretation \- Cross Validated, accessed January 30, 2026, [https://stats.stackexchange.com/questions/615838/granger-causality-test-result-interpretation](https://stats.stackexchange.com/questions/615838/granger-causality-test-result-interpretation)
48. Introduction to Special Section on Pseudoscience in Psychiatry \- PMC \- NIH, accessed January 30, 2026, [https://pmc.ncbi.nlm.nih.gov/articles/PMC4679160/](https://pmc.ncbi.nlm.nih.gov/articles/PMC4679160/)
49. The earth is flat (p \> 0.05): significance thresholds and the crisis of unreplicable research, accessed January 30, 2026, [https://pmc.ncbi.nlm.nih.gov/articles/PMC5502092/](https://pmc.ncbi.nlm.nih.gov/articles/PMC5502092/)
50. Python reporting tools to generate interactive and beautiful reports \- Reddit, accessed January 30, 2026, [https://www.reddit.com/r/Python/comments/x8t8fw/python\_reporting\_tools\_to\_generate\_interactive/](https://www.reddit.com/r/Python/comments/x8t8fw/python_reporting_tools_to_generate_interactive/)
51. 5 Python Libraries for Reporting and Factsheets \- Xlwings, accessed January 30, 2026, [https://www.xlwings.org/blog/reporting-with-python](https://www.xlwings.org/blog/reporting-with-python)
52. Hypothesis Generation via LLM-Automated Language Bias for ILP \- arXiv, accessed January 30, 2026, [https://arxiv.org/html/2505.21486v2](https://arxiv.org/html/2505.21486v2)
53. Self-driven Biological Discovery through Automated Hypothesis Generation and Experimental Validation | bioRxiv, accessed January 30, 2026, [https://www.biorxiv.org/content/10.1101/2025.06.24.661378v1.full-text](https://www.biorxiv.org/content/10.1101/2025.06.24.661378v1.full-text)
