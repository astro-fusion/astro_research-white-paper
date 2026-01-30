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
* **Preprocessing:** Detailed accounts of transformations. "Data was log-differenced to achieve stationarity, confirmed via the Augmented Dickey-Fuller test (![][image1])."  
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

* ![][image2] **(Null):** There is no statistical causal relationship between planetary positions (geocentric longitude, declination, or aspect) and the log-returns of Gold (XAUUSD). The inclusion of planetary variables in a Vector Autoregression (VAR) model does not reduce the Akaike Information Criterion (AIC) compared to a univariate autoregressive model.  
* ![][image3] **(Alternative):** Planetary positions provide unique information that significantly reduces the forecast error of Gold prices, exhibiting Granger Causality with a p-value ![][image4] (after Bonferroni correction).

### **3.2 Data Acquisition and Preprocessing Protocol**

A rigorous methodology section begins with the data. The report must detail the "ETL" (Extract, Transform, Load) process.

#### **3.2.1 The Target Variable: Gold (XAUUSD)**

Gold prices are a non-stationary financial time series. Raw prices cannot be used for correlation analysis because they contain trends (inflation, long-term growth) that yield spurious correlations.19

* **Step 1: Ingestion.** Download daily close prices from a reliable vendor (e.g., Yahoo Finance via yfinance, or Bloomberg).  
* **Step 2: Transformation.** Convert to Log Returns to approximate continuous compounding and stabilize variance:  
  ![][image5]  
* **Step 3: Stationarity Test.** Apply the **Augmented Dickey-Fuller (ADF)** test.  
  * *Report Requirement:* The report must include a table showing the ADF statistic and p-value.  
  * *Critical Threshold:* The p-value must be ![][image6] to reject the presence of a unit root. If raw prices are used (![][image7]), the results are statistically invalid.21

#### **3.2.2 The Exogenous Variable: Planetary Ephemerides**

Astrological data is complex because planets move in continuous cycles, but their "aspects" (geometric angles like 90° or 180°) are discontinuous events.

* **Continuous Data:** Geocentric Longitude (![][image8]). This is cyclical. Linear regression fails here because ![][image9] is numerically far from ![][image10], despite being spatially adjacent.  
  * *Methodological Fix:* The report must describe the use of Trigonometric Encoding: ![][image11], ![][image12].  
* **Discrete Data:** Retrograde periods (binary 0/1) or Aspects (Conjunctions, Squares).  
* **Alignment:** Financial markets close on weekends; planets do not. The planetary data must be re-indexed to match market trading days. The report must explicitly state how this was handled (e.g., "Non-trading days were dropped from the planetary dataset to align with the XAUUSD index").22

### **3.3 Statistical Methodology: The Engine of Validation**

#### **3.3.1 Cycle Detection: The Lomb-Scargle Periodogram**

Since financial data often has gaps (holidays/weekends) and planetary data is continuous, the standard Fourier Transform (FFT) is strictly mathematically inappropriate (it introduces spectral leakage). The **Lomb-Scargle Periodogram** is the gold standard in astrophysics for detecting periodicity in unevenly spaced data.10

* **Application:** The report must show the periodogram of Gold Log-Returns.  
* **Test Logic:** If astrology is true, we should see significant power spikes at known planetary frequencies (e.g., the 29.5-day lunar synodic cycle, the 88-day Mercury cycle).  
* **Significance Testing:** We must calculate the False Alarm Probability (FAP). A spike is only real if the FAP ![][image13]. If the periodogram of gold prices looks like white noise (flat) or only shows weekly/yearly seasonality, the cyclic hypothesis is rejected.24

#### **3.3.2 Granger Causality: Testing Predictive Power**

Granger Causality is the econometric standard for testing whether one time series is useful in forecasting another.26 It does not test "true" causality but tests *predictive precedence*.

* **Model Specification:** Vector Autoregression (VAR).  
  ![][image14]  
* **Test:** We perform an F-test on the coefficients ![][image15].  
* **Null Hypothesis:** ![][image16]. (Planetary lags do not improve the prediction of Gold).  
* **The Bonferroni Correction:** Astrology involves many variables (10 planets, 5 major aspects). If we test 50 combinations, we might find a "significant" result by chance. The report must describe the use of the Bonferroni correction: dividing the p-value threshold (0.05) by the number of hypotheses tested (![][image17]).29  
  ![][image18]  
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
* **Implementation:** If you check Mars, Venus, and Jupiter against Gold, Silver, and SP500, you have performed ![][image19] tests. Your p-value threshold for significance is no longer 0.05, but ![][image20]. The report must state this clearly.

## ---

**2\. Advanced Statistical Implementation Details**

### **2.1 The Vector Autoregression (VAR) Model**

To test if Planets cause Gold prices, we use VAR. This treats every variable as a function of the past values of every other variable.

![][image21]

* **Granger Causality Test:** We check if ![][image22]. If ![][image23] is significantly different from zero, it means past planetary values help predict current Gold values.  
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

[image1]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAEYAAAAYCAYAAABHqosDAAAChUlEQVR4Xu2XS+hNURjFP28G5FWKKCZGRiIZScIAyYCBTBiQmYEBMTJRZvhnwICZIiGFmCFS5BWiFAMjeT8jrHX33v7fXefs+zhyU/f8anXPt9a++5y7z95nn2tWU1NT05/sht5Dn6FNkrXjCPQLegHNkIy8hfZA06Hh0ALoVlOL/5SH0CVXP4CuuboVP6GlruYALXd18lTbmlr0mEVqlDDOwoUq9MarKXAW6HdXlHisd0DHoM2S9ZQL0GtokgYl3LHiDyH0uERawTacbQp9LpvED3fcktnQIRu8I3Oh09C8Py26ZwT0GHoGjZKsFWlqKznfw/yymhb8/a7+7o6zDIHuQYstdPAcWhMzdnA0HnfKBOgVdN1C392SG4Cc72F+Vk0L/nlXf4MGoHfQ8ZgvdHmDE9BQaKWFBrNctjd6nTAT+gqd0qBLcgOQ8xP8DczLzk//qau52y1z9XwLbSY6z3bFzxtWPPHJEk/hsuNOcFCDiuQGIOd7mPMRoNC/oqbANhywAgwelXjtLoZbI9vs1KAiuXPmfA/zi2pa8A+7ms8/Jds/zXUl3kvxcqSZc0CDLvlg5RdYduMUtsntSum3bYj19sG4QenApLvuWR+90eK3g2+anywswyqsteK1EHocfI/OUg6Kfjc9PxIbYz3NeYTeE/EaOwgDvgyR9CDjRVZlrIXZdlWDDuC5t7h6X/Q8b6K31Xl8eOrN5AzU133t61yJ1yCN1v14/BGa2tSiOsOg2xb6HylZjjEWruMmdNfCbqdb/xwL70jKEgvfPWNh8HjTlckW2nC75ucXK/bfgCGXzr/mb2Zgz1llmWnU7/AveFqrUyTra7gmuSuttsw6q6mpqanIb6jHtgj7606WAAAAAElFTkSuQmCC>

[image2]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAABKElEQVR4XmNgGAWDDcwD4k9A/B8Jv4TKMQLxKzS5d0DsBZUnCcAMwAb2M0Dk+NAliAUgl4IMOIcuAQX4LCcKZDNADPBDl4ACkNxPdEFSACjMcbnQlgEi14QuQQqABYE/EHszQCLRE4pPQuU44arJACADbgJxMRoug8rh8h1RABb+uJIervAvAeI7QHwfXQIdvGbA7UIrBohcM5q4ExDPRuL/QmJjAHxBsJsBIseFJg7ykTISH5d+BmYGiCSp6R8kxovGN0Xiw0E/A0QyDF2CAZJq8FmAnKpA/AgkPsNyIP4MxO+B+C0QfwDiv1A5biD+AhUDyYHU/GCAJGEYABnIg8YHxRfVAMhA9DhAjyeKQB0DJI/AALZgpBiAMuYcIP4NxDJocqNggAEAx65V0Ig6zrsAAAAASUVORK5CYII=>

[image3]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAABA0lEQVR4Xu2TPQ4BURDHR1RIHEg4AOKjcgUJpcQBOIAbaB1CodZs7wiIbxIKYSYzu2F4u283m1DsL/k383vePGMAJPwbY8wR83jJUlwKs1Jui6mID4V7wTdmwC6vhS30UrrA0ULwa25FF/iCuhYCuZsuhoFmbnphCdgNtAiDO4IGpgr8I5Ylc3EZ73QE6IIFpqfSF2f6dla48zetnt/8O2D+nMcazC8sALuhqhcxbXGBDfxGMAV2WS2EwAZp4ENR9z+wwQj4UEsL4K2xaUBb98EEc8LsMBvMHnMXl8OcpUaOzlyBV1hDDWq6GCfUwPTvjwVq0NTFOKD1PQCPkHJ51wm/5gm0QlCAMfrSTQAAAABJRU5ErkJggg==>

[image4]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACEAAAAYCAYAAAB0kZQKAAABGUlEQVR4Xu2SPWoCURSFb34MBoJNIEV0ARY2abOAILgBN5BOV5EmTcAmRBRbe1OkcgUSiIWkCoiFhY0g/kCIEM/lPZ3xBCczxli9Dz50zhm8M74r4nA4dkeOg31SgV8wzcU+aMIRvOAiJCewBB/hJXWBHMN32IOn1EXhA3ZgzF5/wzuvlnvf9xUJOICv8JC6qMxgl7K8mAdRijDl6yQJp/DZH/6BBzHD+EWObJ6xn2voss1hmYst0QE/hlg0r8MbLpYs/5EGFxHRQW0OLdrpov/KGezDFjygLgw6qMqhRbsCh0HoGb6JWbA4dUG8wE/KsnAs5iFqYn77eu2OEOgRDeE5Fxt4Em83JmKWUbmymR771txy4HA4/osFjA0z3gU33qgAAAAASUVORK5CYII=>

[image5]: <data:image/png;base64,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>

[image6]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADcAAAAXCAYAAACvd9dwAAACEklEQVR4Xu2WPUhXURjG31IhJSMpE4lyi2gKskVcFLeGwEEHRxGEIMLBCAoCR5saRPJjcAunGlzUKVpSUCN0VLEGF6Eijb70fTznyHuf///cvBdc5P7gQd7fe7z3HO895ypSUFBwmnim+abZ1fRS739Ma/Y1q5oa6oFfmkeaBk21pkOzYQecJJjUrKk/ad6bOkaVuEVd93WFrxuPRjjgOG2JETm4x6IMF8TdjIG7yJJ4p/lM7oWUXg/1c824pjvZys4rzW/NTW6UYVlKJwPgMJk0MGaEXIv3Fq5zMaf5qrnCjRTCa8LEfCC8gk/JN3nfaVzadVKpFLdnNsVt1qzEFhHzgdvi+gPk671/bBxq7Okvmhlf43CJgr2yrVnUnKVeFmKLiPlAu7j+Q/J13o8Zh7rJ1IPelXBV80Pzlhs5iS0i5gM3xPVxxFsuez9EnsGYeZY4JP5oRrmRk9giYj5wRlz/Cflr3vcYh08Gk3r98ATfcCMj36X8TeDWWBIYEzstw7duwtd3j0Y44HCip3Je3Eb9IO6vmZUuiS/ujqnPaR6YGvzTfCTH+2lK81eSc6sVNwafrGOBo3lJsy5uIlnAjfpNPeydJbxGt4xr9c6C+qWpcdjtmRpgjvx7xwav6o7mEjci4BOCm+Hpr2h+SulbcF+zQA6EJ/Va3P+Qk8n2Ic3ixuB0x8+tZDsffSwKCgoKTj0HYEeOFm5ZcRkAAAAASUVORK5CYII=>

[image7]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAEYAAAAYCAYAAABHqosDAAACjklEQVR4Xu2XTcgNURzG/0RYkCSKWLCwspKPLCUskCQWsmFBdhYWxMpG7JQsvAskKRJSElbykVK+FSKSrHznOzzPPed4//eZOffOvd6F3PnV053/85w5M3Nm5py5ZjU1NTW9yXboPfQJWidZO/qgX9BzaLJk5C20A5oEDYHmQDeaWvyj3IfOu/oudNnVrfgJLXA1B2iRq5On2tTUYgDQg/4toyycqEJvtJoCnwLdd3GJx3oLdBBaL9mAMRb6AB3RoEtuWvFCCD2+Iq1gGz5tCn2+Nokfbrsl06B91n9HZkAnoZl/WrRnJPQKugINkqwT0qOt5HwP8wtqWvD3uPq7287Ci7gNzbPQwTNoeczYwYG4XRVOZpwTnkIjJKtCbgByvof5aTUt+Gdd/RXaC72DjsZ8rssbHIMGQ0ssNJjisp3R65aLFg4+ToMW5AYg5yd4DcxPaGDBf+RqrnYLXT3LQpsxzrNt8feaFQ98vMTrhsMW7tJUDUrIDUDO9zDnFKDQv6SmwDYcsAIMHpR47U6mCrss9DNbgxJyx8z5Hubn1LTg73f1ULedyPZPc1WJ91K8TjgEfbMwuVeFK1zZCZbdOIVtcqtSurY1sd7cHzcoHRh+EKm5OnrDxa8CV4bXFpbyTllpxXMh9LhaerZKzUHRfdP8kVgb64nOI/QeimdXY8CPIZImMp5kVbga3YMeQ8Mk6xQee4Ord0fP8yZ6G53HyVNvJp9A/dzXvs6UeA3SaN2J2x+hCU0t8nBJfmHtJ7dOYJ88j+vQLeiLFb+NpkNPxCPzLex7ysLg8aYrfJLZhismfz9bsf8GDPnqdMMKNf4XllrmMep1+Bc8vavjJetp+E5yVVpmmfespqampkt+A1N8tfIYM+h8AAAAAElFTkSuQmCC>

[image8]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAE4AAAAXCAYAAAClK3kiAAACFklEQVR4Xu2XvUtcQRTFr9+KYKGkUgRTGEUQFUlQRAuRdEIksZGQJtgJ1pomqSQhRWxTWFiolZ2KjViJSf4Cm10IBIkYCPgRYvy4x7mjd68B2WXWt+D84LDvnJl53Dv7Hu89okgkErkfVLPWWeesr6yizOFLf8haZv00Y3fFA1aKXI07rObM4QymWaeip2YMBOm3ntwJqsTXiS++mkH0Sx2DXePzTSdrQ/nX5GqcUJnnhPVZjitYZ6zK6+Fw/WJnl0z2jfVH+Rl1DOz8fINadLMAHtLss/aU/0RuzmOVBesXJx412ZTkHl0M+G18vlmkm5tkN65JfKPKQLvxQfrtJ7egz+SvJK8VX0ruH/nIOvCTEqSXXH3vVbYlGShnDakxT7B+J8kt6DL5C8mfmLwQwG2H2jZN7q/ABdYAq008bldPsH7fkVtgL+dnko+ZPGk+sObJ1YarROM37q3KHkrWID5Yv+PkFnSY/LnkgybPhu4slC1l5OpLq8xvnAXZDzkO1q+/53tM/lJyPLpzZTgL5YLfqEfGW3QerF+852DBbU+ZpMErxBeT/SNX4xvx2+IteuOC9osFsyZbkbwQ8C+oth6ftYpvEW9BNmd8kH7/t9vwIyZLEtSD9zRPjWQplYEj1pry+PSyvQXtF49wfNfhFyfBY7uQKGEdk6stLb+reoLiO7nxv+Q+t/SnlKfQ+41EIpFI5J5wAe/NuZ8edv2DAAAAAElFTkSuQmCC>

[image9]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACUAAAAXCAYAAACMLIalAAABtElEQVR4Xu2VyStGYRTGT4ZYKENJwt6KWNvZyEphowwLxZ8gZW1jY9xQNlbWKHvESomUSKaFMpXEwnSee973+849vb5BKYv7q6d7z3POPXd4h0uUkPB3NLPuWV+sXVZFPB3xxOpnVbLKWT2sx1iFUMs6JOm1ZHKgjPXB2mTtm1yKUdaMildIGrYqD8Czqo9VEI04v8DFw6zPdDriwMQbJo7wN8jFm2QtsNpNDuBBUDNtfHizKu5Q5+DWxBHXFH6AkJeJXpKaPuPbXtvqPBQHGSdp0mn8bA+1TFLTZXwMn762mvXMmmNdKP9H0DA0BAD+CeuItcN6ZxWp/KCryfal8mKKtUqyMkJzBo1LVIwJam+GWC8a79m6vKkjabJmE4ZGkroJ5Y05z7POejPerwm9XaGJ/Wo7Nn4La49kAldRuFdWMFyLxvON2lx86uLSVIVsgvC2lBcCNVfWzEQ3hd/Ee/7rXLJe0ukI7Deo0RMbsd7li51Xo7ycwEV6Ajc5T++0DawzFQPMlVfj4bpzFT+QDGXeYNyxl0B3JI3nYxXCAEnuxh1Dm94QSQ4vgGPo35eQkPAv+QbEwID383S7KAAAAABJRU5ErkJggg==>

[image10]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABEAAAAYCAYAAAAcYhYyAAAAr0lEQVR4XmNgGAXEAmZ0ASgQAeJ0IOZBl4ABkMYaIP4PxFlociBQAcT6ULYTEAcjyYHBDSBeB8R+DLgN2YHGB+nBCXAZshGNfwmNjwJwGdLJAAkTEFAC4hQkOQyAyxAQ0ATiDiCWQ5dAB/gMIRqADMlBFyQVgAzJRRckFYAMyUMXJBWADClAFyQVgAwpRBckBYDSAciQHnQJYsBqIH4NxE+A+DGUfgnEv5AVjYKhCADQ5yB76Gq9BQAAAABJRU5ErkJggg==>

[image11]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAG4AAAAYCAYAAAAbIMgnAAADz0lEQVR4Xu2YWahNURjHP2MiU1FEIWOhSEroUoQSD6TECxGJB0MRL8aUofCgRLjCg6GURxnOA1ci3szpyjxmnqfvf7+17v7Od9c+955zb+fctv2rf3ev/7f3umevYa9vLaKUlJSUJNKV1dSatTDAGinFpT3rsTUV7VjlrB7Gv8YabLwgs1nfWX+VXqv4DxO7p2JJoxPJO5bZQAGgnjiOsyrc9R9WzyhUBZ5tY7xYJpA88MT4qACVtzZ+EtlF0gbnbCBP7rOWW9OxgKQ9PXtZr1QZoC8+Gy8nflZZ739ikDUKIFebIdZFlXc7zwKvmzXjOEbywEZXxnWzKJxSB9ARn6zpwBJkO+l6wANY6y5aM44mFM26L6wO2eFE0JZkgD5grWQdcX4Lks/YdtYG54E5rM2sk648kLWPtczfYEDbbbKmA7E9AS/UcTMp7Mfyk+SBMTaQALqzvqpyR4oaBx2KDkH5fPUd0gm+cStJ7vMD/GN0WzXw+1qTmUES05OhufNeKE+TV8ddIXkAI7LUHM6hQyTp9AHWfpJG71P1VDwnSBIHzXtTth0HkNbDb6U8zLhQw8JDh1jeksQySvgcwtvibzKE6g+CDGcVRSOsUB5ao5EwkeS9sP3BOo4ZZwl1XKXzNYsCHgh5INSmpwKexg6WIIsp+t77JAWdWAjrrdGI2EZRI0I3s8PBjsMstQ08P+CBkAfgnw54v4ynQRyf5ljGs66qsk5SSsnWPIXEIRc4zfDgKAobYbzjWOWHOg6HDrYt5gU8AC+UicNfospY6+DprYElVH81/VnPrUnRiUlcxTiywUJ/ljXLeZNYl0gyMX8P1pWjJLMX69EHFysFF1gjjIf3XKPKoY6rdL4m14zrbU0Sf5oqY22tbaMfqp9asg6SBHFtWUESe2oDDl9pP9Ytd436prBuuPJt9xf3+sNWJD3D3HWxyVB2Vgnw2zqbsv76AJxs2EZEZ8PDNkIDb63xAJInLEFgLsmAycV0qvk/6S7rHesNSc/b4xVkQPARxzXS3tVZd8ixDSrOGP8bZe/4MTLPqHKNH1NEMqzhlH02O87FsFygg5BBYrD6NkEbwHtEkrbjPrQHjgbhPaPs9ysnadsQPrO0MzpEBeuyNRsKvAT2fUhsPLZj8IKj3TVGp40nDZztNsQ7hmZzvUGlQ9x1OUWbynUkn4QyVwb6JXaydlC0BiYVzNiF1syDUVT7p7QgkIxgr4Y0ebLy0YGYYUuV91JdYz3Ec1OVl0Tq+2X5TeFNfEoR6MW6Y806gExzqDVTigu2WtgT58NIa6SkpJSCf37fE53u5dzQAAAAAElFTkSuQmCC>

[image12]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAHAAAAAYCAYAAAAiR3l8AAADr0lEQVR4Xu2YWahOURTHlyEzUWYKRZIyZijDTYkSyVCSFy+KPBDJ8IIo5YkUMl1TSXnwICGFkJDMKVM3RR7MIjPrf/dezjrrO9PX/fou3z2/+nfP+q9z9j3f3mfvs/YhysnJyWlIzLJGCkOskVN/HGGNtaZiBGsbq6nxf5s4lnmsr+QuEL1S+W8m90jlcpKZwjpjTcU71nxWYyocsD6st8ZLZBK5Rp4bvzXrF6uV8XPSsYOiecw6rWKcu0zF4BNrmvESkVlmvZziWcO6ZU3PKCrsV8SXjdfP+5k5Su6CDT7GcZMgnVME6LvR1vQgdzvC+2A8AD/z6teIgln4mdU+nK4YBrOusWpYO8OpWtAPm8m9TjaZnLCO9Yy1nzWMNVsnKX7mjCSX62Z8eFeMB+DjXjLzndxFVTZRIdwg9xsxSADvd93ZY3zc0scdfDzo7xkubqtiFBuLVIziJW4A75PL6ZWtu/d0GwKKIBSZmblKrrGnNlFm0EGHYnSQdYBVzdrH2sPa7S5LBBU3fltH5X0hVywIyM9RMUDH6gGxgzOUwp2/ngrPEeD/ZJ1XQtUPv42cpMAKEddWAbtYK8ldkPmi/4i034XlMiovr5a5PpZ2jrPGyUkKPFxR7QD41RFe3PkyHqksZh32x1LM4OJKIqmjAFaduDx82dN19rGWnj0YoKh2OpHz8c7UwNthPGEFRbcVYiLruop1MVNfNCf38i5GaaT9JsyoqDzuBf5eFQvoO+SwKRdWec+CPbX1k5ZbgIFNylN/1ktrUvAFpqtNeHqTK3vxqUi/f7aS28+8p/AnJOxpsNajfMb/rA/WkvtN9rMVOhGgMkR+uMqBqd5v4WP7hWQGhTvZxhrrI64ynuYUuR1BAc0omOo4tiwnl3thE+QGRp64JRT8gwesCf4Y6JuV4wUUv1yUAxQteDgFVIN42ISz5CpTDe79mInxQAqYcRdVDOxACagoB/jjO6xzKhcF2tlizYfkBuA1uZvXVRh4433kcfyRtVrl0WgvFQNZ3zV2AKGofVe5OUHB/VwwOTCdgjwqxsnhdO0gy3ILoWawwLczGbSj4LqlJhcFzsNWpqTYgQLbye2xBHyFkPNkzzPTewN9XMmcpMJPY8XSk6L7us7YRjGj8Z64q7wfrB7+GOfLe6fG/20I2H4qFrxr8dCXHKz/WFovUbD1AFhWbvqc/gyHNfwe6wmrr/IrnY0UvbxmoQtFF5c5ZQbFjf4Ml5W6zt6cErLQGimMt0ZOTs6/wh/WKgzc33cD/AAAAABJRU5ErkJggg==>

[image13]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADcAAAAXCAYAAACvd9dwAAAB1ElEQVR4Xu2WSyhFURSGl1ceSeRREmaSkTKTkamBMjAxlFJKMiDFyJCRgYTMZcSUGSYoj8RQQlFSyCOEtey9te9vb/dsj8ntfPUP1rd2d991z77nHKKYmJhUYoRzw7nndEIvGQucN84BJw96yAWK/0a+1LJV73PWrdpHFqmhqnSdoevyzxWKHe1N/oQWFA4KyL2huEKUwCrnFNw4uT9PWCJ/LzLTnGdOLTYcmF8VETeLEpA1k+AatXfxq+FWONecMmx8g++o+LzBHMFh8NXat4EXgofLJPWfOebkQi8KviF83lBPqt8PvlT7QfBC5OHkvyJ3ni1OOvRC8A3h84ZmUv1e8EXaz4AXkg5XwbkjtfAv8A3h84YaUv0+8CXaj4IXkg4nN4kXzhQ2fohvCJ83pJHqD4Gv1L4DvJB0OIO5govYCOSW3BuKO0QJyBrf3RKfdULk4Qz5nDPOBqlfM5R2cm8orsGqczg9Vi28cvbADZD784Tg4Qxya97mHJH6IiHIht1WPaadjdSSOss1aWcj9QQ4wxqpfjY2QpCjesUpxoYHeYTIpnL1dzmP9PUUtHI2wQnmSs1znjhzie0PHjjnpN5mTkidtEsKf4dNoAtFTExMTMrzDhXXhKxF9knlAAAAAElFTkSuQmCC>

[image14]: <data:image/png;base64,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>

[image15]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAsAAAAYCAYAAAAs7gcTAAAAf0lEQVR4XmNgGAX0BtJAvAyIc9ElgMAWmXMMiP8j4TfIkkBwA8bIA+K3QMwK5UsyQDTIQvkLgZgNygZLoAMHID4AZYMMIghAhmQBsQi6BDYAcz9R4D0Q16AL4gJP0AXwAaKdwATEr9AFcYE6IO5GF8QF3gExH7ogLvAbXWAQAQAYqBfQoq3vPwAAAABJRU5ErkJggg==>

[image16]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAIsAAAAYCAYAAADK6w4SAAACq0lEQVR4Xu2ZS6hNURjHP8+ESDGQPEYGMpAyIEqS8kxKBiYyEUUyIBF5lTChmHhdFCEyMVfKwMDAQEZGTORZlEce3/+ubx1r//c++9xzu9Z29f3qX2v9117nfHvt76y91joijuM4juM4jjP4uK36pXqmGk1tjtPLCAlJMs3qw6w+uXWF4xgPVS/JOyUhYRynAJLiHHkLzC8xRXVdtZ0blEVs/AOsV92QP9Nmyhw2nFriK2c/+dPNX5eaj8yMepM2Ks+p3jRprNDypG2fhJt0+g5+XBjHXeRPMn9PNHao3kpY4AAsaHDBVKtfUY20cn+41kZXJXz2ZdUl1QXVeetTxw/V0aR+QIpT5c+k3C0bpBxnGm+PhHgvSoj3dG+v/GCcOL4ojGmPhDFFnLh2ZW+v9iyRMIbIhZQJ5reeSzrQkcWqB1ZGIqVsU60gLxczpPoBYSbENm+Zar55o1QfJNzfMfOcamZKGKed5E80/wj5JXAREgMdwELVFvObSpZ2zFYdkmLiP0nK31U3k7pTZIiEsdtLPt4u8DeSXwIXVc063SbLiS7VX16oDid1xDnWyhiEqnthlko5njqlr8Oc4D45ljqtDt1qwfi02w11PGt5L+XVMeg2WXJRlwz3VV/ZzMhBNiTsOnktOE81l7xcYK33lLzdUj+uLfiAJoLOnRZMTfCJjQTEPIbNTNyT8P23Ei/uPvhBVHm5wDKDvxv1M+RVwh0j8PsyreUEZ0TH2TQ+qsazmRHsKF6pxpH/WLWKvLOmpogzCdZ33yTsqDoyVPWaTQMftobNhrmrmsWmhGl1uJXxB5nzF8DZxUk2DSTLWjYbpmoWxOnuZtUm1VbVl0KrM2C8k/K0iZUxpnScu0Cfi82NUpUs8f0fdafY7AwUOJcYTOCI33Ecx3Gc/5ffntqsxvZoUYMAAAAASUVORK5CYII=>

[image17]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABIAAAAYCAYAAAD3Va0xAAAA3UlEQVR4XmNgGAWkgnlA/BmI/0PxAhRZCPjLgJAHYWdUaVSArBAb2AfEKuiC6IARiLcD8XoGiEFBqNJggMsCFJAPxCZQNi5X/UEXwAbeIrE/MEAM4kMSUwPiTiQ+ToDsAlA4gPg3kcSWATEPEh8rAIXPZjQxdO9h8yoGQA4fZDGQ5m4o/xeSHE7wDl0ACmCu0gbiFjQ5rACXs3czQOTuATEnmhwGYAHiveiCUMDEgBlWWAEzEL8B4pPoEkjgGxB/RxdEBquA+CMDJP2A0g0oL2ED+kCcjS44CkYBEAAABi803bhnVOIAAAAASUVORK5CYII=>

[image18]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAmwAAABECAYAAAA89WlXAAAFr0lEQVR4Xu3dXahmVRkH8KU12kWWhmY2leJQ6RSKqQgOWk6OIqiRkR8JjV4o4lgYqWhRTN50EUGkFxKF+I2IRsooQshcCKaiiOPEDEXhyCiWgmgYZlbrca8173qX7/loBs97Duf3gz97rWft9+y5m4f9mRIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAsDwd2hfm6cC+UOzVFwAA2D1/yNmac1rOCzmbx1Zntj7nnZyv5/w3Z8P4cjql1COxX2zfHNsDAIA5/SYNzVQrGquru1rvsDTs14r5/s18banVaNYAAHbDpObsplKfzc6cf3S1+M1zzfzknJ80cwAA/k8r09BkndHVryj12cT6413tlVKv1iQNGwDAHrkoDQ3W8V39/FL/bFdvxfqmrrat1KsT09CwfS3niZzbmjUAAObhujQ0WEd39W+Uen/mrRXrv+1qW0q9OqHMv1Dmx+T8cbQMAMBcfpAmN2znlPp5Xb01qWF7ttSr/XJWNfMQ6+u6GgAAM6iN2bFd/dxS7xu5Vqw/0NXi7FnbsE0S66/3RQAAJts3DQ1UNGiteuZtNrHeX958q9SrGPd/J+ZvdzUAAGYRDdQvu9qDpV59KL33pbiTzqb1Z91ifk8zr7VfdTUAAGYx6WxazONyaTuPrG5qHyu1aObCJ8p8xa49UnomDa/2qA5J7z0WAADzcFcavnYQ22iorhxffve1HE92tXBqGvb/XdkePr78rnom7l9lCwAAAAAAAAAAAAAAAAAsBwfk3JuGj5QDALDIvJFGL12N10b8u1l7tBkDALDAjkqT3+kVtcfScNbth93aYvCXvjAPd6fhxbXTUl+IO80AAEvQTP+R1/pr/cIiMenfPJf4zT59EQBgsYsm5om+mEYN22X9QrZ3ztq+mH0r59PN/MSyjbN4Hy7jD+R8vozXlXkVf3d9V6v1i8s4/v63c7bnfGbXHoP4fNNBXS1cmLNX2r0mDwBg6qKJ+U5fTDOfeYsPlX8353s5d5ZaXDKt42tyfpFzSs4NOW+Xev1bN+ZsyXk95+NNfVsaPskUYr2qxwtxjLhEuzXngjKu4lNPH8n5ZlM/IY2a0b/n/LOM5+PPOW/NM4+X3wAAvC+iYerv6/pUqfcNWzRJ0fiES3I+mnNkGt8vzobF/OGcv+WcVOrRjH2yjGM9PmK+X86Xcn6U86eyFseu96e1xwtxvND/u+KybZx1C6829Xa/O3I2NnMAgCUjLltGY3NMGhqqF3N+noZLj1GPhxF2lH1jXs+CVbH/T5v5VTkvlXHfWFV9Pebxu7h02tf744VJv/9KGl1qDXEJtd2vNokAAEtW3E/21a62IufkZt43SrEetdVN7c2cNWXc7x8+l4ZXiLRiv0kPA/S/j+OdnUaXTDeXbb9f2JhzczOv+1ze1Bazp3KeKYlx7+mcR3I2le2Px5cBgOXq+znXlfFDabgH7cw0XP4Mv865voxD3H/WuyUN97m11ufcVMZfzPl9GbfHizOBcbwNOT/L+XLOqrK2PQ2/Cy+X7Qdzni/jnWlo2OK+uqWkXl6OnNWtRYMb9/LFPYJHdGsAwDIXT1v2jc++afRE6FxW9oUiGpBj+2KafLz+nXHh4DT+hGqI3x5XxvH3+6dPF7sr0+iS9X+6tXB/Gt3XBwDAFNQHKOIScjRt9dUo1aRLwQAALKDakMU9gjGOS6Ct+soUAACmIJ6YjXv4qr+moWmrLwu+NOf00TIAAAvtvjR+z118xSEatvpeuvrqFAAApmTS/Wn1idE6BgBgiuLTXb347FY0arfnPNqtAQCwgOJzXdf2xaKeZVvbLwAAsHDipcSTvvwQbk0uhwIATF00ZPEJr5lo2AAApuSKNNy7Fi/Mje1j48u77OgLAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAHvofzjyRtCdB7aFAAAAAElFTkSuQmCC>

[image19]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAE8AAAAXCAYAAABK6RIcAAACMUlEQVR4Xu2Xz0tVQRTHD4YIhT+SIETduRONWrtrFy4CadNGF4IuW4qof4C4sahFWRoJRluzVdugdgpuXESgLVz4Ay1/V3q+nRnf3OP9+fDNxvnAl/fme+5wzj137rx5RIFAIHA1ucPaZJ2yvrIaomFvfCap4RerV8V808RaJqlnSsXOGWQ9dcazJBPuOZ4PjljXzPdakhpWS2GvDJDkrzLjfta/UrgELoKyvEoyRpJv1PF812BBw5B3UvnwnimPfpqAS97CH2tDUU2yirLoIMnX7Xh5a7hsHpHk1feWq55hkose6EAMt1k72jTcYB1rswCoAXufb6ZJcj9UPl7b1OZhQtySTaOF9Vt5aNyJ8vJST/JA9nXAE71UxsqbYH1g/WXdV7EsWll75jsa98eJFQF73kvWAeuFiiXxLkVvWTOsN6zXrFestv+z0kGT3B9R6yU2z9JMctFHHcjANrDcxmlyFVshhiiae4F1qLxEyim8keRVxaq5DOZJapjTAU/cZX1jfSG5t9ie4DXFcnaxF3YpPwnbOHCLiu9Xi6xd5Y2Q1JC1d44XVLtMKwxqWXONHmPqjlrPHlrTuEkXbxANtHtgHmy+645nD+vvHc8XyLvtjHHkgofTRQSYNc6403ifHC+JOpK9IA40UP8KJ4EnilXhEvdQfYG8P5zxFskrfAG8cjjDQBskE59HrkjmiTYUOCCjiXlYIsm9Yj7Xo2Gv9JHU8N18Jv63DQQCgUAgUCnOAOHZm2Ed1aUkAAAAAElFTkSuQmCC>

[image20]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAIUAAAAXCAYAAAAldIx0AAAEqUlEQVR4Xu2aSagdRRSGj+JIFEEJTtGIuFFwnghJFFFE0IWKw0Ik4EIkG0VFQV1Eg2CCC4m4cQpOOKE4oOKIw0LBeUTj8GIkJoqoKM7j+d6pSk6frrq3zUvue/j6g59766/T3dXVfatO1XsiPT09Pf8XDo1Gz/RmC9W90ewZDTNUT6n+Ub2q2qxZPZBjVB+KHXtXqIODVc+oDlFtrtpbdZ3qIR9U4T7VVsGj/KLY9WjzVOAc1RrVn6prQt0wbha7l1WqPUNdZlgfw5uq+WL9M0t1her7RoTI76oLVDurtlUdp1rpAzK7i12MINgplXmAw7hQ9bcrnyd2rIcL43l93YioE8/Fi4W3QyofnsqTyf2qL135TtW3rjwI+u54V+ZeTnBl6NLHjKixj3kBIjEG8cK1+EnaQ/Rrql+DV4KT7lvw/K/laNVjYr+Iq1TbubpBMKIsDh7nfrvgvRu8UcL1eSjRiw83wr0R5zmp4HXpY/hIdYNqiWq3UJfhuEViz+LMZlUTAs8I3mXJH8TJUo75TZr+PNWVrtyVT0J5pth5bwz+68mfDJgGS9fGi+2PEPNBNMX8PdL3rn0ML4RyiXhMkaPEAnlwngXJ3zH4nuekfJExafpzZcNeij9CObeJB+GptWMUMESXro1X8j3Uk2tF8Jel77V7i30MG+2lIOkgkLnac3ryjwy+hySmdJH3penPEUuO8O5W/SyWKA7iVGkPb7PFzhFHis+TTy40amoPv+Z7qH8kmmL+E+l71z6GN8QSXaZqcraxZvU4HPO0arXq8VQm6WzAHE/FAcE/JflnBd9Tu3HmfO/zwvHgPNS/FDwPw2MJjnun4CGSzkHcUdHtqttUy1W3is23N6VjhlHrg5qfIYmn/sFYIeZ/7L6XzhP7GGIOSH1cfeDNduVLktfg3GQeFPzTkn9s8D1k3K0TKu9J2feslcExLM9K0B6Oy8vUS8WSTLwuq6WNTe2h1XwP9aVlOX7+wUykj+8Ri2G7YRDEPOuNnFMwxHvOTj7L1Rq1+e5TKfue58ViWkOXWP6xXzQdHMP+BEPo/qrPZPj1NhUM16Vrd30pnoymmJ9Hqon08SKxGD8Nb+m+Z1pt3ToZG7L6uFzKMTEzbl1UbMmLt03wIcYOg3i/jq+x9D+qC8zPpfZ2aRMxtdVHfpAT6eNrk8c+EdySynGaxYtJ/biZs91MTkI8JJ/xl01MXKHgPRrKbPB4alk70wKJUo3SzVMmB5oMdpF2ewDvouDxQ/PwQsRjjyh4XfuYHU3PK8nPkDv9Jc3d6u3FYmLyXhwVKLMCyHCi0gMhNxhz5dxJfph6S2xZmtlVLGaB8zIPyPqd1RIcx+olw4jTdfdwU8GIwPydOVHa/fRd8hY6jweN50fLH8X2XTxd+vh6sZ3PTN7hXO48cq5fXBk4b2zrOlgq8hbxSRBL1QhJ0cXRVL5RfSXrRxd2IiP5V5FHiDykRaoNTBwoFvNF+hy2tB0V3NcKsQSRdsVd25z7RPKfAB4We3Feblavo0sf57of0uf5zepxDhOr41y5H6c0e6mujmbP9KaUdPVMc0p/1euZxvB/AD6x7emRfaLR09MzRfgX5h2Og7eDLtgAAAAASUVORK5CYII=>

[image21]: <data:image/png;base64,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l7lcRjsFffYBMeyE9LDusKzj2OEH1/kYoMM3vF/FNP1IAjtNQCd9/Ke+blFWG1WPSTlhg1g8dtknNl6AutQOULfLeDw81BXQGd1+X7gr0U4Hw30lbHhOWWx+OOuHJAd3OWrPkLnjQ2y5taq6mLqELZc2+3kZr8fNDdCkzZbJOWGDsriG7Sn8WgXWFd4TbkaKaTJNIspAWcKGSyD4zw2NHeWGolw4NsYI/iPHOLijTD9y4lRx/atwxg3PfAp9MHCge4sfZ3cf0zAudt67yHj/oQfEHYywbMcX5U+qDjAdPH4B89R9huz0rRwStnPE9WfZtygPjlc/Cuu06jEmKR6g8F0hvoG4m1fC87gWFeWh0WjLoM5emkOsqv9OV5g+tsPNxXWwx/C2Up4wx76D2HJrsXVTpSxhO0vmttmyM65N2iw+77TaLNaLbbPPFDcd9FVDvyy9fdrpN5V7wobt6iJxiSrOmsXGszE7bNXVE1EmyhK2trDjD3eMajhQIckI1i3KpmoYiZW+JBPgshh26BYuEYZLZRbOtOjLBoAdX11fmNQTNsA6OkjiCcHTi/IDGzRSPUAB+lEt8q/xXYTne2m2c3yA6fbxbDQNj8DArwMEseVDIhK6Amhly61VrZuYsoStrSHb7GY26OH71mf0INZmESsrWu4JG2A7wiVrfek/sNsT9nfXmJhVNS8iysi0ErZUXVyU1/vX79UVSg4JWxmczcCZjyVFOVlG/YGslA9QdbB9LinKgUU5d7zq0enag/bQcDlwibg7SMN3gP5YVcuttV0300rYUtWkzZZZCAlbjN2ewmVnnJHDP3FV3QLazouIErXQEzZ0yr1Fxp8rZeWcsOE9upTJ7QAV4MxM7DMeJe7SHR7jgkupsUuoQ4ktn41Vff6qupiFnrA1abMxuCR7r7htAtvGy8erx+TWHuy2hOfXAZ59d6WMHl4c03ZeRJSohZ6wNZFzwtZUbgeoWdJ23Sz0hG0Is9QehpwXEfWICRsTtiH0+dly13bdMGHrbpbaw5DzIqIeIWH7bVGOUGUW6M+Ly2upJGx6uXTH77bQp0VPK4UD1LQ+W+52krnfTRtI2PT7Uaha6u1h6/HqTrpuX0RERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERERDR7/g/WUIo+/AcvAQAAAABJRU5ErkJggg==>

[image22]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADwAAAAYCAYAAACmwZ5SAAABlElEQVR4Xu2XzytEURTHT6EUKxtW9srG0lpJ2drZyEZSLGRho6zIyoIV+a2Uf0BZ2hGxxYpig1KUJJxv79xx3rl3jCmemdf91Lfe+dx73+s08+6dIYpEIpHKY5Bzy3njzJqx3LHLuVH1FudB1bnjg1MbcD3G5YJ5SpqzwF1aCWo4k5wxO1AlvFLxhj0/Q8kC0CDX3qQKJ9gYBXy/iHrljsX9JZtFssFZ56xyVjjLnCVZ8x1eY4LnUWAbt+7JONDBObSSuaJkzY4dyBCvMSHl+6QYKgwnwOF91kxxFslv+FldX3CuVZ0lOHdLNrynC6FVXJ3xYJr8hjHXbfudUv+EuTJTin0KPxvu3RULIjQ4rJ3b1gMUblgzQf79sqKFws+GG3cFdmQ9qVtq5+wN0PCRcRrMb7MyQ/BJ6n2kl/weqEskMiIOC1E3uUkCGsYOHuKM027lP4Aj9ZxzQEkPjenh8kDDJ1Yya5xmuS58ffIAGj41bpgzyhmgZLd/SY1WMTh+8M/jjvNIXz/S3evgci8+EolEfpVPdcJ7KgDFB+YAAAAASUVORK5CYII=>

[image23]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABkAAAAYCAYAAAAPtVbGAAABCElEQVR4Xu2SMQtBURTHT6GUzWKzK4vRrOQD2Cw2STHIYFEmX4DdQPkIPgMRs43BglKUDDjnvfN65533Fs8bDO9X/zr3d+69p967ACEhId8SwXQxLd0IigHmyXWC67fd/p0KmBfGhVuxCwy67OjhbsoROcxCS2QP5pmZbhBlMJs15cnR/5H0MCNwD7mLeoc5iLXBHNyfJc0upjzRB/cQ2lviOs9rB0MPORFuKhvgPUTSAfd9xkuSsshry+kDNGSpnIT2Z7QkCmBf3GD34nXS2sTQEHp5XmwxWS39QEPWWiJjTIrrtvC+oCEb5eqYJqYK5it9OLpfQk/1gjlhrpgoe+tTWzmzD/lTPh3PQM8nXnZZAAAAAElFTkSuQmCC>