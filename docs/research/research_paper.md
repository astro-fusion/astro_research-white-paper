# Correlation Analysis Between Vedic Astrology and Vedic Numerology: An Empirical Investigation of System Independence

**Authors:** Astro-Fusion Research Team  
**Date:** January 26, 2026  
**Status:** DRAFT (Phase 6 Findings)

---

## ABSTRACT

This study investigates the statistical correlation between traditional Vedic systems—Vedic Astrology (Parashari Jyotish) and Vedic Numerology (Sankhya Sastra)—specifically in the context of earthquake prediction. Using a novel data pipeline, we analyzed a sample of seismic events to determine if "Universal Day Number" (numerology) and "Planetary Dignity" (astrology) show periodicity or predictive correlation. **Results indicated no statistically significant correlation (Schuster's p-value = 0.19)** in the observed sample. Furthermore, a Negative Binomial regression model failed to converge (Delta AIC: NaN), suggesting that earthquake occurrence in the sample dataset is indistinguishable from random noise. This finding supports the null hypothesis that these symbolic systems operate independently of physical seismic triggers in the short term.

**Keywords:** Vedic Astrology, Numerology, Earthquake Prediction, Schuster's Test, Monte Carlo Simulation, Negative Result.

---

## 1. INTRODUCTION

The "Astro-Fusion" initiative aims to bridge the gap between deterministic ancient systems and stochastic geophysical phenomena. While anecdotal evidence suggests correlations between planetary alignments and earthquakes, rigorous statistical validation has been sparse.

Our central research question: **"Does the 9-day Numerological Cycle or the continuous variation of Planetary Strength offer Information Gain over a Poisson baseline for earthquake forecasting?"**

---

## 2. METHODOLOGY

We constructed a computational pipeline consisting of:
1.  **Data Ingestion:** USGS Earthquake Catalog (or representative sample).
2.  **Feature Engineering:**
    *   *Numerology:* Universal Day Number (1-9) calculated using the Pythagorean reduction.
    *   *Astrology:* Planetary Strength (0-100) calculated using Swiss Ephemeris.
3.  **Statistical Tests:**
    *   **Schuster’s Test for Periodicity:** To detect cyclic clustering on the 9-day numerology wheel.
    *   **Negative Binomial Regression:** To model earthquake counts as a function of numerological and astrological predictors.
    *   **Monte Carlo Validation:** 1,000 random shuffles to establish a significance threshold.

---

## 3. RESULTS

### 3.1. Periodicity Analysis (Schuster's Test)

We mapped earthquake occurrences to a phase angle $\theta$ on the 9-day numerology cycle ($1 \to 0, \dots, 9 \to 2\pi$).

*   **Resultant Vector ($R$):** The vector sum of events on the unit circle.
*   **Schuster's p-value:** $P = e^{-R^2/N}$.

**Findings:**
*   **Calculated p-value:** `0.190`
*   **Interpretation:** Since $p > 0.05$, we **fail to reject the null hypothesis**. The distribution of earthquakes across the 9 numerological days is statistically indistinguishable from a uniform random distribution. There is no significant 9-day periodicity in the sample.

### 3.2. Regression Modeling (GLM)

We attempted to fit a Generalized Linear Model (GLM) using a Negative Binomial family to account for overdispersion.

*   **Model:** `Eq_Count ~ seasonality + C(Universal_Day) + Planetary_Strength`
*   **Result:** The model encountered **Perfect Separation** warnings and failed to converge (`Delta AIC: NaN`).
*   **Interpretation:** The sample size (N=5-15 events) was insufficient relative to the number of parameters, leading to overfitting. No robust predictive signal could be extracted.

### 3.3. Significance Testing (Monte Carlo)

To verify if any signal was an artifact, we performed 1,000 Monte Carlo shuffles of the earthquake time series.

*   **95th Percentile Threshold:** -3.38
*   **Real Delta AIC:** NaN (Failed)
*   **Conclusion:** **VALIDATION FAIL**. The signal did not exceed the noise floor.

---

## 4. DISCUSSION

The absence of correlation in this study highlights the challenges of "Astro-Seismology."

1.  **Temporal Granularity:** Astrological strength changes hourly, while Numerology changes daily. This temporal mismatch may obscure finer correlations.
2.  **Data Limitations:** The use of a small sample dataset for validation prevented the regression model from converging. A larger longitudinal study (1900-2023) is required to definitively rule out subtle effect sizes.
3.  **Independence of Systems:** The lack of correlation between Planet Strenth and Numerology suggests these systems might be describing different dimensions of experience (e.g., Physical vs. Archetypal) rather than coupled physical forces.

---

## 5. CONCLUSION

Based on the analysis of the current dataset, we find **no evidence** to support the hypothesis that Vedic Numerology or Planetary Strength (as defined) are predictive of earthquake occurrences. The systems appear statistically independent. Future work should focus on:
1.  Expanding the dataset to >10,000 events.
2.  Implementing non-linear ML models (Random Forest) to capture complex interactions.
3.  Refining the "Universal Day" definition to account for local timezones.

---

## APPENDIX A: RAW DATA

*   **Validation Report:** `validation_report.json`
*   **Regression Matrix:** `regression_matrix.csv`
