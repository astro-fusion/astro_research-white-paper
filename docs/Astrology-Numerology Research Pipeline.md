# **Feasibility Study and Strategic Roadmap: Statistical Validation of Astrological and Numerological Precursors in Global Seismic Activity**

## **1\. Executive Summary**

The intersection of geophysical phenomena and celestial pattern recognition represents one of the most contentious yet potentially data-rich frontiers in exploratory data science. The "Astro-Fusion" initiative, as reviewed through its repository structure and stated goals, aims to bridge the epistemological gap between deterministic ancient systems—specifically Vedic astrology and Pythagorean numerology—and the stochastic, non-linear nature of earthquake occurrences. This report serves as a comprehensive feasibility study, execution roadmap, and theoretical validation framework designed to transform the project from a conceptual exploration into a rigorous scientific endeavor capable of withstanding peer review.

The core objective investigated herein is the development of a regression model capable of "hindcasting" (predicting past events) by correlating seismic catalogs with numerological cycles and planetary configurations. While mainstream seismology relies on physical models such as the Elastic Rebound Theory and statistical baselines like the Epidemic Type Aftershock Sequence (ETAS), this research proposes a novel investigation: treating the time-series of celestial coordinates and numerological integers as exogenous regressors in a Generalized Linear Model (GLM).

Our analysis confirms that while a standard linear regression is mathematically inappropriate due to the discrete, overdispersed nature of earthquake counts, a **Negative Binomial Regression** framework offers a viable pathway for testing the hypothesis. However, the project faces significant methodological hurdles, most notably the "Look-Elsewhere Effect," where the high dimensionality of astrological variables increases the probability of false positives. To mitigate this, the roadmap prioritizes the implementation of rigorous statistical controls, including **Schuster’s Test for Periodicity** and **Monte Carlo significance testing**.

This document outlines a 16-week execution pipeline, detailing the necessary data engineering (migrating from skyfield to swisseph for Vedic precision), feature engineering (quantifying "Shadbala" and "Universal Day Numbers"), and model validation steps. It concludes that while the predictive power of such a model remains a hypothesis to be tested, the construction of a high-fidelity "Astro-Seismic" dataset constitutes a valuable contribution to the field of anomaly detection and time-series analysis.

## ---

> **PROJECT STATUS UPDATE (Jan 2026):** Phases 1, 2, 3, and 4 are **COMPLETE**. The pipeline has moved from feasibility study to active implementation and validation.

**2\. Theoretical Framework and Scientific Context**

To publish a paper that will be taken seriously by the scientific community, the project must be grounded in established theories, even if the hypothesis is unconventional. The "Astro-Fusion" project operates at the boundary of two distinct domains: the physical science of seismology and the symbolic logic of astrology/numerology. Bridging these requires a precise translation of symbolic concepts into quantifiable mathematical features.

### **2.1. The Seismological Baseline: Defining the Null Hypothesis**

Earthquake prediction—specifying the time, location, and magnitude of a future event with high precision—is widely regarded as impossible in current geophysical science.1 The Earth's crust is a complex, non-linear system where stress accumulation is slow (tectonic plate motion) but release is chaotic and sensitive to initial conditions. Consequently, the current state-of-the-art is "forecasting" rather than "prediction"—estimating the probability of an event within a window of years, not days.2

Any new model proposed by the Astro-Fusion project must outperform the standard null hypothesis in seismology. To demonstrate value, the numerological regression model must provide **Information Gain** over these established baselines:

1. **Poisson Process Assumption:** The simplest baseline assumes that earthquakes occur randomly in time at a constant average rate (![][image1]). In this model, the probability of ![][image2] events occurring in a time interval is given by the Poisson distribution. If the numerology model simply predicts "earthquakes happen," it fails. It must predict deviations from this random rate.3  
2. **Gutenberg-Richter Law:** This empirical relationship describes the frequency-magnitude distribution: ![][image3], where ![][image4] is the number of events with magnitude ![][image5]. The ![][image6]\-value is typically around 1.0. A successful predictive model must account for this; predicting a Magnitude 4.0 event is trivial (they happen daily), whereas predicting a Magnitude 7.0 is significant.4  
3. **Omori’s Law and ETAS:** After a large earthquake (mainshock), aftershocks occur at a rate that decays hyperbolically with time (![][image7]). The **Epidemic Type Aftershock Sequence (ETAS)** model formalizes this, treating every earthquake as a potential trigger for future earthquakes.5 This is the most critical baseline: if a "numerologically significant day" follows a major earthquake, the high seismicity observed is likely due to physical aftershocks (Omori's Law) rather than the numerology. The project must use **declustering algorithms** to remove these dependent events to isolate the "mainshock" triggers that might theoretically be influenced by external factors.5

### **2.2. The Astrological and Numerological Variables: Feature Definition**

The project proposes using "static tools and analytical analysis" of astro-based models. In a machine learning context, these systems function as **Feature Generators**. We must formalize the vaguely defined concepts of "Universal Day" and "Planetary Strength" into rigid, reproducible vectors.

#### **2.2.1. Numerological Features (Temporal Cyclicity)**

Numerology, specifically the Pythagorean system referenced in the project scope, posits that time follows a base-9 cycle.

* **Universal Day Number (UDN):** This is the primary independent variable for the requested regression. It represents the numerological vibration of the global day.  
  * *Calculation:* ![][image8].  
  * *Example:* March 14, 1997 ![][image9].  
  * *Scientific Interpretation:* This effectively bins time into a 9-day recurring cycle. The hypothesis is that earthquake probability ![][image10] is non-uniform across bins ![][image11].7  
* **Master Numbers:** Occurrences of 11, 22, and 33 are often treated as distinct, high-energy markers in numerology.9 In a regression model, these should not be reduced to 2, 4, or 6 but treated as categorical dummy variables to test for specific "high-energy" correlations.

#### **2.2.2. Astrological Features (Planetary Mechanics)**

The project references "Astro-Fusion," implying a synthesis of Vedic (Sidereal) and Western concepts.

* **Heliocentric Acceleration:** Recent exploratory studies have suggested correlations between the acceleration of outer planets (Jupiter, Uranus) and seismic cycles.10 Unlike geocentric positions (which include retrograde motion illusions), heliocentric acceleration represents physical forces (gravitational changes), making it a more plausible candidate for physical coupling mechanisms like tidal triggering.11  
* **Shadbala (Vedic Strength):** This is a composite index used in Vedic astrology to measure the "strength" of a planet. It consists of six components (Sthana, Dig, Kala, Chesta, Naisargika, Drik).12  
  * *Data Engineering Challenge:* Many components of Shadbala (like *Dig Bala* or Directional Strength) depend on the local time and the Ascendant (Lagna). Since the project aims to predict *global* earthquakes, these local-dependent variables introduce noise. The analysis should focus on **Chesta Bala** (Motion Strength) and **Sthana Bala** (Positional Strength), which are globally consistent.13

### **2.3. The Epistemological Gap and Statistical Pitfalls**

The primary reason such studies fail peer review is not necessarily the subject matter, but the lack of rigorous statistical controls. The project must aggressively defend against the **Look-Elsewhere Effect (LEE)**.14

* *Definition:* If a researcher looks for correlations in Life Path 1, then Life Path 2, then Life Path 3... up to Life Path 9, and also checks conjunctions, oppositions, and squares, they have effectively performed dozens of independent hypothesis tests. Finding one "statistically significant" result (e.g., p \< 0.05) is expected by pure chance when ![][image12].  
* *Implication for Research:* The regression model must define the hypothesis *ex-ante* (before looking at the data). If the hypothesis is "Universal Day 8 correlates with earthquakes," the model is tested only on Day 8\. If the hypothesis is "Any day might correlate," the significance threshold (alpha) must be corrected using the **Bonferroni correction** (e.g., ![][image13]) to penalize the multiple attempts.17

## ---

**3\. Investigating the Regression Model: A Mathematical Feasibility Study**

The user specifically requested: *"Investigate if there is a regression model that can predict past events from numerology... as a first case to earthquakes."* This section provides the theoretical derivation and feasibility assessment of such a model.

### **3.1. Why Linear Regression (OLS) Fails**

The first instinct in data science is to apply Ordinary Least Squares (OLS) regression: ![][image14]. However, for earthquake prediction, OLS is fundamentally flawed and scientifically invalid for three reasons:

1. **Discrete Integer Outcomes:** The target variable (![][image15]) is the *count* of earthquakes per day (0, 1, 2...). OLS assumes a continuous variable (e.g., 1.5 earthquakes), which is physically impossible.  
2. **Rare Events (Zero-Inflation):** For large earthquakes (![][image16]), most days will have a count of 0\. OLS handles sparse data poorly, often predicting negative counts.  
3. **Heteroscedasticity:** The variance of earthquake counts is not constant; it increases with the mean. Days with high seismic activity (swarms) have much higher variance than quiet days.

### **3.2. The Proposed Solution: Generalized Linear Models (GLM)**

The mathematically appropriate tool for this investigation is a **Generalized Linear Model (GLM)**, specifically using the **Negative Binomial** distribution.

#### **3.2.1. Model Derivation**

We assume the number of earthquakes ![][image17] on day ![][image18] follows a Negative Binomial distribution, which is superior to the Poisson distribution because it accounts for **Overdispersion** (where Variance \> Mean). Earthquake catalogs are notoriously overdispersed due to clustering (aftershocks).3

The regression equation is defined as:

![][image19]  
Where:

* ![][image17]: The count of independent (declustered) earthquakes on day ![][image18].  
* ![][image20]: The intercept, representing the baseline seismic rate.  
* ![][image21]: The vector of Numerological and Astrological predictors.  
* ![][image22]: An offset term accounting for the observation window (usually 1.0 for daily data, but adjustable if data is missing).

#### **3.2.2. Numerological Predictors (![][image23])**

To test the numerology hypothesis, we encode the "Universal Day Number" (UDN) not as a continuous integer (where 9 \> 1), but as a **Categorical Variable**.

* We create dummy variables ![][image24].  
* ![][image25] if UDN is 1, else 0\.  
* The regression will output coefficients ![][image26].  
* *Interpretation:* If ![][image27], it implies that on Universal Day 8, the earthquake rate is ![][image28] times higher (22% increase) compared to the reference day.

### **3.3. Feasibility Assessment: Can it Predict Past Events?**

* **Descriptive Validity:** Yes. It is computationally straightforward to fit this model to the USGS catalog (1900–2023). The model *will* output coefficients. If the p-value for a specific coefficient (e.g., Master Number 22\) is extremely low (\< 0.001), it suggests a correlation exists in the historical dataset.  
* **Predictive Validity:** To claim "prediction," the model must hold up on unseen data.  
  * *Hindcasting Test:* Train the GLM on data from 1900–2000. Use the derived coefficients to predict the expected number of earthquakes for each day in 2001–2023. Compare these predictions to the actual counts using the **Root Mean Square Error (RMSE)** or **Log-Likelihood**.  
* **Constraint:** Numerology is strictly cyclic (1 follows 9). A simple regression might capture the periodicity of the *calendar* (e.g., weekly or monthly anthropogenic noise) rather than a mystical connection. The model must control for **Seasonality** (Day of Year) to prove the signal is truly numerological.

## ---

**4\. Comprehensive Project Pipeline and Task List**

This section details the specific technical tasks required to build the "Astro-Fusion" research engine, organized into a phased execution plan.

### **Phase 1: Data Infrastructure & Engineering (Weeks 1-4)**

**Objective:** Construct a "Gold Standard" dataset. Analysis is only as good as the data, and earthquake catalogs are prone to incompleteness and magnitude errors.

* **Task 1.1: Build the Earthquake Catalog Ingestor**  
  * *Tooling:* Use Python libcomcat (USGS official library) or requests for the USGS API.19  
  * *Parameters:*  
    * starttime: 1900-01-01  
    * minmagnitude: 4.5 (Ensures global completeness in the modern satellite era).  
    * format: CSV or GeoJSON.  
  * *Critical Fix:* **Magnitude Homogenization**. The USGS catalog contains different magnitude types (![][image29], ![][image30], ![][image31], ![][image32]). ![][image29] (Richter) saturates at large magnitudes. You must convert all magnitudes to **Moment Magnitude (![][image32])** using empirical conversion formulas (e.g., Scordilis, 2006\) to ensure consistent energy estimates.19  
  * *Output:* earthquake\_master\_catalog.parquet (Parquet format is recommended for performance).  
* **Task 1.2: Implement Declustering Algorithm**  
  * *Context:* Numerology/Astrology hypotheses typically concern the *triggering* of events. Aftershocks are triggered by the mainshock, not the stars. Including them inflates noise.  
  * *Action:* Implement the **Gardner-Knopoff** or **Reasenberg** declustering algorithm.  
  * *Logic:* For every event of magnitude ![][image33], remove all subsequent events within time ![][image34] and distance ![][image35].20  
  * *Output:* declustered\_catalog.parquet (containing only independent mainshocks).  
* **Task 1.3: Build the High-Precision Ephemeris Engine**  
  * *Tooling:* Migrate from skyfield or ephem to **Swiss Ephemeris (swisseph)** via the pyswisseph wrapper. swisseph is the industry standard for astrological precision and supports the complex Ayanamsa (precession) calculations required for Vedic astrology.13  
  * *Calculations (Daily at 00:00 UTC):*  
    * **Geocentric Longitudes:** Sun, Moon, Mars, Mercury, Jupiter, Venus, Saturn, Rahu, Ketu.  
    * **Heliocentric Coordinates:** For the "Planetary Influences" study.10  
    * **Retrograde Status:** Calculate velocity; if ![][image36], flag as Retrograde.  
    * **Ayanamsa:** Use swe.set\_sid\_mode(swe.SIDM\_LAHIRI) for Vedic compatibility.  
* **Task 1.4: Develop the Numerology Feature Generator**  
  * *Action:* Write a robust Python class NumerologyEngine.  
  * *Features:*  
    * **Universal Day Number (UDN):** sum\_digits(day \+ month \+ year).  
    * **Life Path Logic:** Implement the "reduce down" logic versus "Master Number" logic (keeping 11, 22, 33 intact).9  
    * **Universal Year:** To test long-term cyclical trends (e.g., "Universal Year 7 is seismic").

### **Phase 2: Feature Engineering & Exploratory Analysis (Weeks 5-8)**

**Objective:** Transform raw data into the Regression Matrix (![][image23] and ![][image15]).

* **Task 2.1: The "Shadbala" Computation Module**  
  * *Gap Analysis:* The project requires "Shadbala" (Six-Fold Strength). However, full Shadbala requires precise local time and latitude (for Ascendant/Dig Bala), which is impossible for a *global* daily aggregate.  
  * *Solution:* Implement a **"Global Planetary Power"** index using only the location-independent components of Shadbala:  
    * **Chesta Bala (Motion Strength):** Is the planet retrograde? (High strength). Is it slow? (Low strength).  
    * **Sthana Bala (Positional Strength):** Is the planet in its exaltation sign (Ucha) or debilitation sign (Neecha)?  
    * **Yuddha Bala (Planetary War):** Are two planets within 1 degree?.12  
  * *Output:* Daily strength scores (0-100) for each planet.  
* **Task 2.2: The Timezone Resolution Strategy**  
  * *Issue:* "Universal Day" is defined by UTC. However, an earthquake in Japan (UTC+9) might occur on "Day 4" locally but "Day 3" UTC.  
  * *Strategy:* Create two datasets to test the hypothesis robustly:  
    1. **UTC Hypothesis:** All events binned by UTC date. (Tests for global synchronization).  
    2. **Local Hypothesis:** Each earthquake is assigned the "Numerology of the Local Date" based on its longitude. (Tests for local resonance).  
* **Task 2.3: Superposed Epoch Analysis (SEA)**  
  * *Action:* Identify the 100 largest earthquakes in the catalog (![][image37]).  
  * *Analysis:* "Stack" the timelines of these 100 events such that Day 0 is the earthquake day.  
  * *Test:* Plot the mean Universal Day Number (or Life Path) for days ![][image38] to ![][image39].  
  * *Check:* Is there a statistically significant spike at ![][image40]?.20

### **Phase 3: Model Development & Regression Analysis (Weeks 9-12)**

**Objective:** Run the statistical models and quantify predictive power.

* **Task 3.1: Baseline Model Creation (The Control)**  
  * *Model:* Poisson Regression using only *trend* (year) and *seasonality* (day of year).  
  * *Purpose:* Establish the error bar (AIC/BIC). If the Numerology model doesn't beat this, the hypothesis fails.  
* **Task 3.2: Train the Negative Binomial GLM**  
  * *Library:* statsmodels (Python).  
  * *Code Logic:*  
    Python  
    import statsmodels.formula.api as smf  
    \# Formula: Earthquake Count depends on Universal Day (Categorical)  
    model \= smf.glm("count \~ C(universal\_day\_number) \+ sun\_longitude",  
                    data=training\_df,  
                    family=sm.families.NegativeBinomial())  
    results \= model.fit()  
    print(results.summary())

  * *Hypothesis Test:* Look at the **Wald Chi-Square** statistic for the C(universal\_day\_number) coefficients. Are they significantly different from zero?  
* **Task 3.3: Sensitivity Analysis**  
  * *Action:* Run the regression with different Magnitude Thresholds (![][image41]).  
  * *Logic:* If a correlation is real, it should persist (or get stronger) as magnitude increases. If it disappears at ![][image42], it is likely noise or a catalog artifact.23

### **Phase 4: Validation & Paper Writing (Weeks 13-16) [COMPLETE]**

**Objective:** rigorous defense of the findings for publication. (Validation Implemented per `validate_results.py`)

* **Task 4.1: Schuster’s Test for Periodicity**  
  * *Context:* This is the standard geophysical test for tidal triggering.  
  * *Action:* Adapt Schuster's Test for numerology. Treat the 9-day cycle as a phase angle ![][image43]. Calculate the vector sum of earthquake occurrences on this phase circle.  
  * *Significance:* Calculate the p-value (![][image44]) where ![][image45] is the resultant vector length.23  
* **Task 4.2: Monte Carlo Randomization (The "Shuffle" Test)**  
  * *Procedure:*  
    1. Keep the Astro/Numerology time series fixed.  
    2. Shuffle the Earthquake counts randomly in time (destroying the link to dates but keeping the count distribution).  
    3. Re-run the Regression 1,000 times.  
    4. Calculate the distribution of Pseudo\-![][image46].  
  * *Criterion:* If the "real" model's performance is not in the top 95th percentile (p \< 0.05) of the shuffled models, the result is null.25  
* **Task 4.3: Draft the Research Paper**  
  * *Structure:* Abstract, Introduction (Seismology vs. Numerology Context), Methodology (Data Cleaning, GLM Specification), Results (Coefficients, SEA Plots), Discussion (Physical vs. Statistical Interpretation), Conclusion.

## ---

**5\. Milestone-Based Organized Todos**

The following table provides a structured schedule to correlate the combination of astrology and pattern recognition.

| Milestone | Deliverable | Key Tasks | Deadline |
| :---- | :---- | :---- | :---- |
| **M1: Data Core** | master\_dataset.parquet | 1\. USGS Scraper implementation (libcomcat) 2\. Magnitude Standardization (![][image32]) 3\. Declustering (Gardner-Knopoff) | Week 4 |
| **M2: Feature Engine** | regression\_matrix.csv | 1\. Swiss Ephemeris (swisseph) Integration 2\. "Global Shadbala" Algorithm 3\. Universal Day/Master Number Logic | Week 8 |
| **M3: EDA & SEA** | preliminary\_report.pdf | 1\. Superposed Epoch Analysis (Top 100 Quakes) 2\. Chi-Square Goodness of Fit (Day 1-9) 3\. Correlation Heatmaps | Week 9 |
| **M4: Modeling** | model\_results.json | 1\. Poisson vs. NegBin Model Training 2\. Coefficient Analysis (Wald Tests) 3\. AIC/BIC Comparison against Baseline | Week 12 |
| **M5: Validation** | validation\_suite.py | 1\. Schuster’s Test for Periodicity 2\. Monte Carlo Shuffle Test (1000 iter) 3\. Walk-Forward Hindcasting | Week 14 |
| **M6: Publication** | research\_paper.md | 1\. Abstract & Introduction 2\. Methodology Section (Detailed) 3\. Results Visualization (Matplotlib) | Week 16 |

## ---

**6\. Issues to Fix & Future Project Pipeline**

### **6.1. Current Issues to Fix in "Astro-Fusion"**

Based on the research snippets and the standard pitfalls of this domain, the following issues must be addressed immediately:

1. **The "Universal Day" Fallacy (Timezone Ambiguity):**  
   * *Issue:* Numerology relies on "Calendar Dates." But an earthquake at 11:59 PM UTC on the 1st is 1 minute away from the 2nd. Using strict UTC dates assumes the "vibration" changes globally at midnight London time, which is scientifically arbitrary.  
   * *Fix:* Implement **Fuzzy Windowing** or test the **Local Date Hypothesis** (assigning the date based on the earthquake's epicenter longitude). This is a crucial distinction for a scientific paper.  
2. **Data Leakage in Training:**  
   * *Issue:* Calculating "average seismic rates" across the whole century and then using that to predict 1950 events is data leakage (using future knowledge).  
   * *Fix:* Use **Strict Walk-Forward Validation**. Train on year ![][image47], predict ![][image48]. Expand the window. This simulates real-world prediction.  
3. **Ignoring Magnitude Completeness (![][image49]):**  
   * *Issue:* The earthquake catalog is incomplete for small quakes (![][image50]) before 1970\. Including them introduces bias (it looks like earthquakes are increasing, but we are just detecting more).  
   * *Fix:* Use **Time-Dependent Magnitude Thresholds**:  
     * 1900-1950: Use only ![][image51].  
     * 1950-1990: Use only ![][image52].  
     * 1990-Present: Use ![][image53].26

### **6.2. Future Project Pipeline**

Once the Regression Model is established (regardless of whether the result is positive or negative), the pipeline should evolve toward advanced pattern recognition:

* **Machine Learning (Non-Linear Models):** Move beyond regression. Use **Random Forests** or **Gradient Boosting (XGBoost)** to capture non-linear interactions (e.g., "Earthquake risk is high ONLY when Universal Day is 5 AND Mars is Retrograde"). These models can handle the complex "Shadbala" features better than linear regression.27  
* **Deep Learning (LSTM/Transformers):** Implement Long Short-Term Memory (LSTM) networks to analyze the *sequence* of daily numbers and planetary positions. LSTMs are state-of-the-art for time-series forecasting.28  
* **Real-Time Monitoring API:** Deploy the model as a microservice (using FastAPI).  
  * *Function:* Ingest live USGS feeds.  
  * *Process:* Calculate the "Astro-Seismic Probability" for the next 24 hours.  
  * *Output:* If Probability \> Threshold (e.g., 95th percentile), log a prediction.  
  * *Validation:* Publish these predictions to an immutable ledger (Blockchain or simple Git timestamp) to build a prospective track record, which is the only way to silence skeptics.30

## ---

**7\. Robust Plan for Delivery & Scientific Publication**

To deliver this as a "Scientific Research Paper" rather than a metaphysical blog post, the format must be academic, objective, and rigorously transparent about limitations.

### **7.1. Target Journals & Tone**

* *Potential Venues:* *Journal of Scientific Exploration*, *Big Data & Society*, or *Pattern Recognition Letters* (if focusing on the algorithmic aspect).  
* *Tone:* The paper must **not** claim "Numerology works." It must claim "We performed a statistical audit of numerological features using Generalized Linear Models." The "discovery" is the statistical result (even if negative), not the belief system.

### **7.2. Paper Structure**

1. **Abstract:** A neutral summary of the hypothesis, methodology (GLM/Negative Binomial), and results.  
2. **Introduction:**  
   * Review of the "Prediction Gap" in seismology.  
   * Introduction of "Astro-Fusion" variables as candidate features for Exploratory Data Analysis (EDA).  
3. **Data & Methodology:**  
   * Detailed description of the USGS catalog cleaning (![][image32] conversion, Declustering).  
   * Mathematical specification of the Negative Binomial Regression.  
   * Definition of the Null Hypothesis (![][image54]: ![][image55]).  
4. **Results:**  
   * **Table 1:** Regression Coefficients with Standard Errors and P-values.  
   * **Figure 1:** Time series of Predicted Rate vs. Actual Rate.  
   * **Figure 2:** The "Look-Elsewhere" Analysis (Monte Carlo P-value distribution).  
5. **Discussion:**  
   * Interpretation of any significant coefficients.  
   * Discussion of potential confounders (e.g., Solar Cycle, Tidal Stress).  
   * **Critical self-assessment:** Did we find a signal, or just noise?  
6. **Conclusion:** Final synthesis.

### **7.3. The Regression Conclusion**

Regarding the specific request to "investigate if there is a regression model":

* **Conclusion:** Yes, the **Negative Binomial Generalized Linear Model** is the correct regression framework.  
* **Implementation:** It can be implemented using the statsmodels Python library.  
* **Expectation:** Scientific literature suggests the linear effect size will be small or non-existent. However, the *investigation itself* is valid research. The construction of the pipeline—merging high-precision orbital mechanics with rigorous seismic catalogs—provides a robust platform for testing *any* cyclical hypothesis, making it a valuable contribution to the field of anomaly detection.

**Immediate Next Step:** Clone the libcomcat repository and download the 1970-2024 catalog (![][image56]). This is your training data. Implement the "Universal Day" calculation and run the preliminary correlation matrix. This simple step will immediately reveal the viability of the linear hypothesis.

#### **Works cited**

1. Chasing the Dream of Earthquake Prediction | Discover Magazine, accessed January 26, 2026, [https://www.discovermagazine.com/chasing-the-dream-of-earthquake-prediction-45331](https://www.discovermagazine.com/chasing-the-dream-of-earthquake-prediction-45331)  
2. The pursuit of reliable earthquake forecasting \- Physics Today, accessed January 26, 2026, [https://physicstoday.aip.org/features/the-pursuit-of-reliable-earthquake-forecasting](https://physicstoday.aip.org/features/the-pursuit-of-reliable-earthquake-forecasting)  
3. The Statistical Analysis of the Earthquake Hazard for Turkey by Generalized Linear Models \- DergiPark, accessed January 26, 2026, [https://dergipark.org.tr/en/download/article-file/380313](https://dergipark.org.tr/en/download/article-file/380313)  
4. Estimating the Probability of Earthquake Occurrence and Return Period Using Generalized Linear Models \- SciRP.org, accessed January 26, 2026, [https://www.scirp.org/journal/paperinformation?paperid=95013](https://www.scirp.org/journal/paperinformation?paperid=95013)  
5. Application of the EEPAS earthquake forecasting model to Italy \- Unibo, accessed January 26, 2026, [https://cris.unibo.it/retrieve/handle/11585/930755/8e484803-7927-413e-84ba-1fd2e8409edc/ggad123.pdf](https://cris.unibo.it/retrieve/handle/11585/930755/8e484803-7927-413e-84ba-1fd2e8409edc/ggad123.pdf)  
6. Standard Errors of Parameter Estimates in the ETAS Model | Request PDF \- ResearchGate, accessed January 26, 2026, [https://www.researchgate.net/publication/241235001\_Standard\_Errors\_of\_Parameter\_Estimates\_in\_the\_ETAS\_Model](https://www.researchgate.net/publication/241235001_Standard_Errors_of_Parameter_Estimates_in_the_ETAS_Model)  
7. Python Program to Compute Life Path Number \- GeeksforGeeks, accessed January 26, 2026, [https://www.geeksforgeeks.org/python/python-program-to-compute-life-path-number/](https://www.geeksforgeeks.org/python/python-program-to-compute-life-path-number/)  
8. How to Choose Your Wedding Date Using Numerology \- The Knot, accessed January 26, 2026, [https://www.theknot.com/content/wedding-date-numerology](https://www.theknot.com/content/wedding-date-numerology)  
9. If you have these three numbers on your birthday, a special fate awaits you \- Telegrafi, accessed January 26, 2026, [https://telegrafi.com/en/if-you-have-these-three-numbers-on-your-birthday%2C-a-special-luck-awaits-you/](https://telegrafi.com/en/if-you-have-these-three-numbers-on-your-birthday%2C-a-special-luck-awaits-you/)  
10. (PDF) Planets Influences on Earthquakes \- ResearchGate, accessed January 26, 2026, [https://www.researchgate.net/publication/383822840\_Planets\_Influences\_on\_Earthquakes](https://www.researchgate.net/publication/383822840_Planets_Influences_on_Earthquakes)  
11. Evidence for tidal triggering of earthquakes as revealed \- from statistical analysis of global data, accessed January 26, 2026, [https://basin.earth.ncu.edu.tw/download/courses/seminar\_MSc/2011/1006-2\_03.pdf](https://basin.earth.ncu.edu.tw/download/courses/seminar_MSc/2011/1006-2_03.pdf)  
12. jyotishyamitra \- PyPI, accessed January 26, 2026, [https://pypi.org/project/jyotishyamitra/](https://pypi.org/project/jyotishyamitra/)  
13. VedAstro \- PyPI, accessed January 26, 2026, [https://pypi.org/project/VedAstro/](https://pypi.org/project/VedAstro/)  
14. ICRR annual report (2017), accessed January 26, 2026, [https://www.icrr.u-tokyo.ac.jp/prwps/wp-content/uploads/2019/07/icrr-annual-report-2017.pdf](https://www.icrr.u-tokyo.ac.jp/prwps/wp-content/uploads/2019/07/icrr-annual-report-2017.pdf)  
15. Statistical Inference as Severe Testing, accessed January 26, 2026, [https://phil-stat-wars.com/wp-content/uploads/2022/09/sist-uncorrected-proofs\_title-itinerary-preface\_ex1-6red.pdf](https://phil-stat-wars.com/wp-content/uploads/2022/09/sist-uncorrected-proofs_title-itinerary-preface_ex1-6red.pdf)  
16. Nature is Full of Surprises – Of Particular Significance \- Matt Strassler, accessed January 26, 2026, [https://profmattstrassler.com/2011/08/28/nature-is-full-of-surprises/](https://profmattstrassler.com/2011/08/28/nature-is-full-of-surprises/)  
17. the annals \- APPLIED STATISTICS, accessed January 26, 2026, [https://www.imstat.org/publications/aoas/aoas\_12\_3/aoas\_12\_3.pdf](https://www.imstat.org/publications/aoas/aoas_12_3/aoas_12_3.pdf)  
18. Modeling the Number of Ignitions Following an Earthquake: Developing Prediction Limits for Overdispersed Count Data \- Department of Energy, accessed January 26, 2026, [https://www.energy.gov/sites/prod/files/LA-UR-11-01857%20Modeling%20the%20Number%20of%20Ignitions%20Following%20an%20Earthquake\_1.pdf](https://www.energy.gov/sites/prod/files/LA-UR-11-01857%20Modeling%20the%20Number%20of%20Ignitions%20Following%20an%20Earthquake_1.pdf)  
19. ghsc / Engineering Seismology and Impacts / libcomcat-python · GitLab \- USGS.gov, accessed January 26, 2026, [https://code.usgs.gov/ghsc/esi/libcomcat-python](https://code.usgs.gov/ghsc/esi/libcomcat-python)  
20. The possible statistical relation of Pc1 pulsations to Earthquake occurrence at low latitudes \- ANGEO, accessed January 26, 2026, [https://angeo.copernicus.org/articles/26/2825/2008/angeo-26-2825-2008.pdf](https://angeo.copernicus.org/articles/26/2825/2008/angeo-26-2825-2008.pdf)  
21. swisseph@groups.io | Topics, accessed January 26, 2026, [https://groups.io/g/swisseph/topics?page=10\&after=1684345358738441422](https://groups.io/g/swisseph/topics?page=10&after=1684345358738441422)  
22. Statistical Global Investigation of Pre-Earthquake Anomalous Geomagnetic Diurnal Variation Using Superposed Epoch Analysis \- ResearchGate, accessed January 26, 2026, [https://www.researchgate.net/publication/353260961\_Statistical\_Global\_Investigation\_of\_Pre-Earthquake\_Anomalous\_Geomagnetic\_Diurnal\_Variation\_Using\_Superposed\_Epoch\_Analysis](https://www.researchgate.net/publication/353260961_Statistical_Global_Investigation_of_Pre-Earthquake_Anomalous_Geomagnetic_Diurnal_Variation_Using_Superposed_Epoch_Analysis)  
23. Results of Schuster's Test for Various Ranges of Earthquake Magnitude \- ResearchGate, accessed January 26, 2026, [https://www.researchgate.net/figure/Results-of-Schusters-Test-for-Various-Ranges-of-Earthquake-Magnitude\_tbl3\_240487973](https://www.researchgate.net/figure/Results-of-Schusters-Test-for-Various-Ranges-of-Earthquake-Magnitude_tbl3_240487973)  
24. Tidal Triggering of Earthquakes: Response to Fault Compliance?, accessed January 26, 2026, [https://www.ism.ac.jp/\~ogata/Statsei4/abstr/Cochran.pdf](https://www.ism.ac.jp/~ogata/Statsei4/abstr/Cochran.pdf)  
25. Search for Continuous and Transient Neutrino Emission Associated with IceCube's Highest- energy Tracks \- UC Irvine, accessed January 26, 2026, [https://escholarship.org/content/qt12q424wz/qt12q424wz.pdf](https://escholarship.org/content/qt12q424wz/qt12q424wz.pdf)  
26. Machine learning and earthquake forecasting—next steps \- PMC \- PubMed Central, accessed January 26, 2026, [https://pmc.ncbi.nlm.nih.gov/articles/PMC8346575/](https://pmc.ncbi.nlm.nih.gov/articles/PMC8346575/)  
27. Machine Learning Modelling and Feature Engineering in Seismology Experiment \- MDPI, accessed January 26, 2026, [https://www.mdpi.com/1424-8220/20/15/4228](https://www.mdpi.com/1424-8220/20/15/4228)  
28. Jackson School Researchers Employ AI to Predict Earthquakes in China \- Texas Global, accessed January 26, 2026, [https://global.utexas.edu/news/jackson-school-researchers-employ-ai-predict-earthquakes-china](https://global.utexas.edu/news/jackson-school-researchers-employ-ai-predict-earthquakes-china)  
29. SeismoQuakeGNN: a hybrid framework for spatio-temporal earthquake prediction with transformer-enhanced models \- PubMed Central, accessed January 26, 2026, [https://pmc.ncbi.nlm.nih.gov/articles/PMC12706585/](https://pmc.ncbi.nlm.nih.gov/articles/PMC12706585/)  
30. this guy is right again at predicting these earth quakes: https://twitter.com/ss... | Hacker News, accessed January 26, 2026, [https://news.ycombinator.com/item?id=39913356](https://news.ycombinator.com/item?id=39913356)

[image1]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAsAAAAZCAYAAADnstS2AAAAhUlEQVR4XmNgGPrgPxA/AGIWNHGcAKQBhIkCExggijnQJXABkOKN6IK4AElOyWCAKFZGl8AFQIpvoQtiA+IMJDjlOhDfZYAoxhvmD4B4JRAzM0AUL0ORRQIvGVDdidMpH4D4O5pYIQNEsRSy4GeoIDYAEr8E48hABUBuxAb2MOA2aBQQBwC0ciJVn07c0AAAAABJRU5ErkJggg==>

[image2]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAsAAAAXCAYAAADduLXGAAAAoElEQVR4XmNgGJSAEYhV0QWxgadA/B+KiQJXGEhQDFJ4DV0QFwApjkAXxAaiGDCd0ATE/mhiYHCTAaGYC4jvAzEfEH+Dq0ACIIW3gVgQiDdCxX5CxTEASHAnEM9El0AHMxgQJsyGslUQ0qgAPTJA7INQdj6SOBiAJKeh8VuQ2HDACRUQRRL7CMQbgLgHiA2RxMHAE10ACDyAmANdcBTAAACQdCSKrBERiwAAAABJRU5ErkJggg==>

[image3]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAJUAAAAYCAYAAADzjL9JAAAEcUlEQVR4Xu2ZaahNURTHl3kIRYYM8ZIhEjIUJSJjGT4rKfMH5IshFEVJiOILEaEUMpQp8UUZk+SL6YOXmcxD5rD/d+/17jrr7vPOfXrn3vfc/avV3Wutfc7eZ5991l57X6JAIBAIBEqartoQ+O/oZKSFNqbBGyN/nNQWZht5T9l+P4i6M3yjrB+yLOouKc5TdhxGKJ+klZG3FB23ylhA2Xo/jNyWzs7OUdtIevhVRmZoY4kyi+LHSYPJcZKS658gWwe/ObSl5BvURD4aWUS271uVD7zWhhLmMeX/jlFvsfuN46GRsWTr9FW+DAh7ld2gJtKP7IODuGjls5UqGIsL2hjDEyODyF7TTvnAACeXqZIxbknxTiwfT43sJRvRfPQ2sovscgPWk73f4Ioa1c9RI/Vc+RzZ9kZl3RmuKb2YzDSyxUgd7SgQGJ+RZN/nQSONo+4KxpPNWQGumSp8DKIUiPuYM/gmVUNnQyPMVyPbhA7Kjdx35aFkr+lp5IqRA1wpBWR/6zr9l7DNNTJO6MWiB9m+dXH6b6fPq6iRPpjQaBNtIzAg+kDvICs58N4Y1EGwkBwTZfgPCT2Cb1L9NHJH2eqTrdfe6aOdLtEvNy2w+5N8Idt2I6c/F7582B8j+8hG6T1GdpMd5J3umiQQDdCnOcI2ydk4yhaCcvK/Jz2GQNZDWe6smxlZ6MoINvBjlfKiJ1UTp08RNgb2e6483+kS6NpW3ch8StrQ7nWnp92HfEBk1/3ARNU2H8hp8pUk0J6MQGzz9QOpDqPr4JiGuUr+6yvQk2q608cIGyMbQn6AMr4+BvpGoafBcfJ/6dw39Oui8hUD9EVHTNg+K5uPyVWQJNCmTGPYdkvZUEcuy3wWCJYaaSp8esLloCdVf6f7znj0zVDGcoftPcqbhU9zShvI5j34OnAIy0tXEnEPs5KsDyFbJ+1JbKiiJDGEbF907gTbcmVLE87pJNhA+d4vR3kG+RNfq/Nj2A8rWwRO3OTOBLrvUAv2FUK/K8pxbCK7lOqHw18GMm/T/jiwrMSBe+R7nzRpTbn96OZs+Hi6U+5LTYMGlNsPnFn58l5dj0/Mccou4bywj7JH6EW2EgaCQViFrbmw4VxCv1DUwQnsJSNnjOygmMMwyu30DbInvQz8ZUL3gWsQ1eJIXOsLCPoxzZU5aee+Rf7SSBm0yUvXBKfrI4W1zi7BLh42zA8JcmpdN8J3I8/Izt4XFH1h+AMSp9I8GGuEj5F+KUk7C9ZlPoa2lwhdgq8GSyzqvCO7O/WBoxAdqosFNjyICHhOXvqx1EPHkUeh4I0XROdRbYx8IjuuH8j+hzdQ+HEGyLwiWweRC+8XiXtlH/g/gQ6s1kbKhtyOyu6bVPhymJdGtgs9UIJgUuCsygd8+gzDN6kmCh2zXuZrgRIEiRomhlyyysiGx5vCxuhJ9YiiORVOfKu6awv8pyAvwqEe1t915D9DAnpSDTdyWujaHwjEcpZsco2kHlFMJtlHyO4akfgNE/ZAIBAIBFLiL6YgUBQhCHozAAAAAElFTkSuQmCC>

[image4]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABIAAAAYCAYAAAD3Va0xAAAA3UlEQVR4XmNgGAWkgnlA/BmI/0PxAhRZCPjLgJAHYWdUaVSArBAb2AfEKuiC6IARiLcD8XoGiEFBqNJggMsCFJAPxCZQNi5X/UEXwAbeIrE/MEAM4kMSUwPiTiQ+ToDsAlA4gPg3kcSWATEPEh8rAIXPZjQxdO9h8yoGQA4fZDGQ5m4o/xeSHE7wDl0ACmCu0gbiFjQ5rACXs3czQOTuATEnmhwGYAHiveiCUMDEgBlWWAEzEL8B4pPoEkjgGxB/RxdEBquA+CMDJP2A0g0oL2ED+kCcjS44CkYBEAAABi803bhnVOIAAAAASUVORK5CYII=>

[image5]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACkAAAAYCAYAAABnRtT+AAABgElEQVR4Xu2VyytFURTGvzJRUpSUjCVS8ihKmXmUMpIyN5BS/gFlZOIPYMrAQFKMjA3IRJkoA0keGSGPPAZYq7VPd93ldPY+7qF0z6++9jrrW/ucde7dex8gJ6f8uCF9KiVRhULdB+lKmwPOmNbJDBknLUOeUWs8zSsCXqYPUrBojRI5dCPfe0wbihlSNaRm03ixNJHeSGvW+CHRL8PjkjYU3NggpKbNeInUke5Iu9ZIyaUbuYETbTgu3LgHz1+dRCXpjHRMqjCejyHSpIvj1lsnqcPFcX4q6kn3pB1reNhX8QO+N3GuYvbW1XUwzaR30oo1AtFNbZnrbRUPQ7xWlfPSD5m0YI2UXKt4FoUma0hTyjtQnpcJSHEWZ+YIihtph9w7Oj00QeuRzykuGrVGCRzZBOQZp5DNaPMbJlfEPGSXZUkX5MENJs+5VZPj3c/5bpP/VZ5It04vkA0TodfoHOkRchZz7TPkm/1/aYQs8hD1ujl/Dn/+egLV4ubk5JQtX+INXygCzGNgAAAAAElFTkSuQmCC>

[image6]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAgAAAAZCAYAAAAMhW+1AAAAhElEQVR4XmNgGDzgBBD/AuL/QGyGJgcH/QwQBTjBYwYCCkCSh9AFkQFIgSO6IAwkM0AUNALxcygbxbSHUEELJDEQPwCZcxQhBxe7gsxpR8jBxV6AGJJQDg+SJCNUbCKIkwblIINSqJgqiGMH5SADEP8RugAMdKDxwUARKgjC29HkRgIAAFc5JozAqrYVAAAAAElFTkSuQmCC>

[image7]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABkAAAAYCAYAAAAPtVbGAAAA1klEQVR4XmNgGAXDFUQC8Ukg1gXic0B8G4i1UVQggW9AfApdkAiwG4jjgPgOkth/JDYKAEkUIPGZgPg7HlyKUMpwC4jdkfhYLdFngEiADCYHIBuaB8RvkPgMNkDsxQDxMkihL5RPKkC2BMMXRUBcApV4C+WDMCkgCojPAPFTBkgw8qNKIwDIklx0QSLBXQYifA9KeiBLGNEliAAmDBC9hugS6GANA5ZwpDYAWfAOXZDaAGQJKPJh4AgSm2oAZIkKlP0TWYKaoIcBYtEPIGZBkxsFo2CkAwBqRjFaaViXhgAAAABJRU5ErkJggg==>

[image8]: <data:image/png;base64,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>

[image9]: <data:image/png;base64,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>

[image10]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAC4AAAAYCAYAAACFms+HAAACAklEQVR4Xu2WyytFURTGVzExUyZmZoYUE2TCAInymMjEY0KKkYEYKclEkQyRidfEzEDKQPIYSClSkr/AW8hzrfbZ177f3efsc697krq/+ursb39rn333OXfdS5Th/9OKRoq0oBEly6xKNFNEDmAeTT+mWHesL0/PrGvw1mLpeOpZm2h6VNBPvUsNXo1wyGo3xk70IkgBKd+2QVseuafgnMzlWrzQSHgPTQ/bhxpmHYNnw1Zr8ooGc8WaQdNGG6nFa3GCySH7zWVcBh6SRSp3BP6ccf1hXGvk1cH7WTkl/+A6qbkm8P3yJoOkco3gXxrXfh0pzPrWExWqSPnT4MuX0pZH9Bdcuo6ok/XO6jAyfkhdOZqI3vgt64b14o1PWHlGTjNK4Tau1x0n1b22vXEYJNeFpol+v7txIoBFcm8gm1RmH3ysK4SxRnITaJqcU+JiLhbIXTNEKlMHvpy6ZpaVb4xNpHYSTRP9OJNBbyqIR3JnguZlbgBNEwlcoOmgmYJvKrgO5IDVi6aB1Mqvr5URUoEenAhB0Kbk8cs89m+hmFQTCKoXrPPyq/RAqoPI/5In1mdcwo0sXApeCeuN1Fr6xE2JL+1QutaKV2Ojhnw2ng42WLtopokzVj+a6SSqU4lq3RhjrFU0f8kWJbbQSNhhFaGZItWsJTSjJKitJUMfGhn+km83DJkFnhtomQAAAABJRU5ErkJggg==>

[image11]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACQAAAAXCAYAAABj7u2bAAABMElEQVR4Xu2Vv0oDQRCHR1KktRACNnkCX8HCyiZFCiuDYBeNkQgWIeADBNIlZdDSwiaNlfgOVinTxEaiiEUM2CQz7Ny5+9tLt3fVfvDjmG+HveH+EkUi4bnlXKAMyANnzfnk7MJayiPnj0yj5NJdDsIOmb0bWpe1rqYdW8hroBWZvW1GGc4jr4GSq29TUydXaytFDnSorgneociBztUNwTtIQwtlAL7IH2iq7hm8gzS0UQagRGbvY633OK/q7pKmLKThGmVAxpwfzhXnjMz5jpwOQBo6KHOiT/5t9JCGG5TKCacCbp9TByf0oL4n/+RSv4FzkPsqTQNcoP8vbdam6L7V2W/ri7qEU6gdnjgLzjtnrscPMr8TmwmZf51NV73NAWcGTpABlpxfMs9RJBIpnA0zFE9+2TSX9wAAAABJRU5ErkJggg==>

[image12]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAFsAAAAYCAYAAACV+oFbAAADKElEQVR4Xu2YS6iNURTHl0chQh5lQnlEMqDIwEgxUESRyAwjSZKBTAwkXSlMjIibkEdRDAw88igyIG+RvAbe5P1+rf9Z63PWXmfv75576Hac+/3q39nrv8/33b3X9+2917lEBQUFBQX/K9tY71i/VM1Br/CDyv3QpLC7IRnEuk8y36usnkFvmQWsx6zvrCbXl8QmM8YJ1jBvNiizWOdMfI8kLzOMB/azHpl4J+uViaN0YB1hHSS56cywu0TqITQimOvsiOdzgLhzxJvivIClrHHajt0UYJnUM11Y470ZoZ83IsRy8Fy9kRpv0tgD7443LS9N+zXJBXaPGs5aZ+J64y7JmJ/q542wOwDnU0ssYs113hcK8/JVY0/sQQXYTuzLiG8Zbzerh4nrieWsCc6bSjKHJc5fxVrmvGrxSfRxRsovgf36sPP8BcmL6wC8YSlOU3kuEKqKWthMcv0I4/kcZaT8Ena/th4uWK9x3oT+hu7eqAG8LC2B/bxW+pLkwp8HqaSm/BKpUiW7aBRrjesDODD7eLOVJAfVSgZSebwvWP3D7oD33sgBDxL3xP09mH9s/LnJTnUcJenD4dPN9YHUddWCmvWyN2sA1QVq3a4aTyNJhK2TMzqyDnkzB8zRrr6FrKHazvLjgffTmwA14nFvKhhY7Ck9M77tw1LFKtlO4eEKnrB2sC5pbK+398BJ/4l1jDXP+Hm89YYyn+Tep1gTWWs1rmbbAZ+psoa+btoDqDI3AB4O7YBOJEvuvO8wfCSZvGcDa6OJkST7h8+a9l7WEG3b76QGClBq3rQdOWzxhmMlSd2LX3fV8pAqXwj/YgC8wXtMnFVBAftYb0jqa9TV+N9HjNGsxd4k+b7dr/HmYinj9Mebb/dMTBIDwI8CS8WgSAYP/6Tz2xqf4FSyAYqH26wzJP3/vET2fxRxtpd5sGxRMl2kcsKns678+UbIZNY3ij/kdgf2sSzZ1/QTb/VYbYOsZMR2ckDbg1mrtY0VMEfbK/QT9xyj7WZWb223e1A++R8IH0iWv/2p3IvkuxdYW42f/ftyl/FwID4g2V+x9xUUFBQUFLQpvwG1oecLbXrSOgAAAABJRU5ErkJggg==>

[image13]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAHwAAAAXCAYAAADJLSsnAAAEm0lEQVR4Xu2ZW6hWRRTHV/ekKDBFu0v0ouStMJEuhy5EUA8ZZYHUAcEQX4wMgupBjUChhy70YkEvRffoHmpE5UOB3dUwMw8VdCO6WdG91p81c741/29mf8P54nj42D9YnG/+s2b23mv2nlkzR6SlpaVlf3MGCy2Dy8Fqj7LY0j9HqG1W+1dtm9oBaXUj56ntEmv7ENWB+Wovq52udqDaKWp3qj3tnQo8pnYoaSi/LnY93PNEYJnal2p/qa2nul7cL/Ysn6mdRHWRXjEG76qdIxafE9RuVfsh8QgcL9bRpFA+JpQxOL24Qe0fV14h1tZzYdC8fZN4lOG+8NJAOzqUF4Ty/uRxtS9c+UG171y5CcTuIlfGs1zsyqAmxpgJOcZ/JB6OX6R72nxL7TfScqDjmRnNv+VDai+Ivcnr1I50dU1gJriNNPT9fkbbTtp4gusj4KzxwDF4Nh64SzNaTYzBR2r3qm1QO47qEtB4CWk3B72JyyTv87uk+tlqa125lj1UnirW70bS3w56LUgCp7A4RrA05a4Nje+fgc+HLIrpJ4bftTEGr1E5y7liDTEonuGgTybd84p0XxSMSKqfJWMb8D+pHO8JQfaU7oPBOgg/THXoG7+HEo8OWAtrQF+5a0PL6R7UI7dhoN8dfpeejWMMqgb8erGGWBs9VwZ9IekeJAR8UbBTUn2RWKIB7WG1X8WSriYuV7uKtJPF+uAv/NOgI/do4kcWlL1i6y0vM7nnylEa2JLuQf2zLIrpL4XftTEG74gljVg+kSONpNUG1lQ0nEP64qAvJd1TeiissV7Hy4RB8aB+K2keTFk50O6DjAZDAlcC2W9M9JjTpNNHtOmJR5lSDEp6BAkx6p/iCjH9Y/c71w/HGHDOhfquLP26UDGP9CuCfgHpHmSmfFGwQ/K65ytp9sEWJQfuB+3iVu0msYQNWs2u4v+mNCAl3YP63NYUevwY+onxI2I+2HKPEtdwTLuea4KOLVuJ0vryieR1z6tiPtNIB1jvZ7HoQBvsvzGtzRablntdL/KMdAbjLqrzHKJ2EIsZMIXmrl074JtYFNPvC7/7ifEaMZ9kaTwsiGPJ0m+RvA9nkLmHx7YP2uGkA/btBfz9PrXEz2rLw28M5nNibeeOenR4noUCWyR/vzX3BJ9Slh4HqZ8Y3xE0nIMkQIxZYeTFoHuQyPEXCR/O5KEhmL6MwwlPKbvFVI2ko0TuwVBGztEE+sUeN8e3Yn1cq3a12tdi02ENWOv5fgC01aThI/JgsLntmRmtNsY4afO8GfQucl8zysiUIzhqzQUba/GIK8cAYEqMvCe2NYscK+Yz7LTIk9I58cuBdsjyI5gpak61jmKBmKH2hFh/56dVPcGX7F+QS6Q7Tt8HbaXTMIjQ/Cy3T+xcwVMT43vETuQi8eTtAaclYLv0d/gLR2zXGCQYN7Io9oXgq4izAk7ImPg2xy+7a5oJcKAYTL/w+Tz87bW9Gy/wXLvFki3cF2/zYq7BxGNn5BZ4Kd5Iq0epiXGs+yn8XZVWTzxmqN3OYsvgkktgWgaY4n93WgYPnF37JLFlwDmVhZaWlj75D5x1dlZxd78DAAAAAElFTkSuQmCC>

[image14]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAGUAAAAYCAYAAADjwDPQAAACr0lEQVR4Xu2Zy+tNURTHv97PIgOPgQEpZYCBiYmbSDEwkpSpGRMZSMmvMJISBoTII2VKyUSZSfIHoBiR8n4/w/pad//u3ss5v3tefmff7E99a5+19t5n7cfZj3uBRCKRSLTENtEx0ULrGGQui76Ifnm6H+QAxng+6kPoboU5oieiyaJxoo+i7UEOYKvoK8LYX3j+b8b30PNFwS1oYHuN3XFSdM0aW+Sxee5A489iHdTHQfSZJvopmmrs0TALvRljWSW6Z40t8tIahP3Ijt2R1Tb7XIUm6hiRrMA5WO+NrW1uWgM07lPW6HEFmudA95lpLnt1sf3VOBegLznq2f75S0syJJouGitaKZrZtfXbD/x98RO0XBM01T/LRRugcQaMR/i1cL1tYjY1CQ8lhLG5WKkZwzny+Q7N27GOGtQdlAfQthwS7TS+YVwjX4vmG19Rloou5ohf43nROdFZ0RnRaS1WiM/WAD1lFemcO9B8j6yjBkXemwdPhoViOQJ90WbriIApon3WCF3K+nUO95vdCFeCMswWrcgQ67I2aokWy+UEtOwE6ApF/bV0OZ6jWtCjATfpSdYorMfIMfP+cqmbdhs+B6gMi0QbM8S6rI1arcVycZPjhqc1QQ6PqjPJZwF0jSyjIvBzz+I68mNeK7rrPfsbfhNUrYfl8toT4AK+ah2RkNcBtGfNssWiZ9aI3k1+rnVUIC+mfrAcDx59OQzN3LGOCOCtmzfyHcbOk8txY5sIPUiwLUxbdkF9T62jAlUHhZOIZblPOjZ56T+noXeiV9Db8lvE8fuWz0HowPDHRzaGui2a52eCHjHfoNcO/ibmwzbSTj/TvBjvCXKUo+qgkGWiH9A6eKrcErrjh0tOjNQZlIHHXRpjI7bL9ajBdXfIGhPtwv9O/tsZmUgkEgPCb8jvulRxXn2CAAAAAElFTkSuQmCC>

[image15]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAXCAYAAAAC9s/ZAAAAmElEQVR4XmNgGAUgsAyIfwDxfyR8E0UFAwMjkhwIf0GVhoADDBDJGjRxGJgBxJvRBZGBEAPCBnRgB8Rn0QWxAWwGgAz+jCaGEyxigBgwEUkM3UC8gIUB1RX/gJgZIU0cgBnwHohl0eSIAv0MEAPC0CWIBdgCkiQA0vwBXZBYoM8AMaAEXYIQiAHiIwwI54NccABZwSgY1gAAzGwoiimZM7IAAAAASUVORK5CYII=>

[image16]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAEcAAAAYCAYAAACoaOA9AAACb0lEQVR4Xu2XS6hNURjHP0WSRxEyUArlmQFFyh0ZeM+IgYwwk4GRge7EQOIO3boz0lUUBjJipCRlIkZInlHej7wf379v7c53/mctZz9Ox2T96t/e6///9r5r77se+4hkMpnM/2NQ9Un1J+hWe9zBI2nV4roD7XFfwN8eUe1R7VTtCNqu2uDqUhxXfVe9Vq2hLErxwFCKZapDYjUrKOsnvq+sIVcX473qsGt/UR1x7ShPpTWCUjxRXZd/1zDr2egBz1QrVQtV81VzVYtUH31RhLXS2fdpEa+NjardqkuSLjwfjt1GFzNdrNOjHNRktWoLm1KuT5hKsTp4mJ5RboQj1o/YxZNU+8I58nMuK8tk1QuxkTeGsqZcVi1nMwL6/oNNMf82mwXFC8E6gvPZLgNfw3GdWL7YZVUZq7qjeqiaQFkdMKU+sJkAfY/VwsfaEwVzuACFu1x7v2piOMcIi42sulwVWyBnclCBX6p5bCZA39+wKeZHnwujYa9ro+ika/splLxJQ06rvkn5hyyYIdX6g9p3bIr5v9kExXpTgELsSuC5D8Sys+T1gqNi917FQReww1Z9OfgnMPDvsQn45sXoGFAtdf6m4C9xXlNOie0gCzgoSdWRnKqHN8wmeEntVxJ/k/hyjt24DlfE5j62+SagP2/ZdAxS+4R0PgN2Tnjj2Hwg9nPAc0Y6bwBSb70s2KXuqu6rxlNWh1li/XnMQeCiWM7LADw/+m8K7WDHxBYm/LbAB9pPl21WbXPtz9KqxU3wnXDQ5d3Ado214RoHPQAPeoHNwFSxXXgK+XPErsNOiRfrd+q+s5WNTCaTyWQyTfgLeCCnyEdekkgAAAAASUVORK5CYII=>

[image17]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABEAAAAYCAYAAAAcYhYyAAAA0UlEQVR4Xu2TOw7CMBBEB4FEC/RcBW7BaaiokRAVtFBwAChocwEOwBkQRHwKGj5rOVY2QxybPk8aKZqxdjcbB6gpYyN6ij5Kx8IJoKEyo0cxzklgD4zJdyxFOzaZHvJOzEB0YNNHWRFT/E5eJWvYInPlcdEgLRSneYuaeRyPK5KK+pRFM4MtMuJA0WaDOSG8h1Be+oU0XdhdeXE3c8tBhmtQ2WgKGw45ULxgp/lhJbqJLqKz6Ar//+GdIJYOAvuIYSJaZM97HfyDudHmtRPya4gvfYY3lgsWnYcAAAAASUVORK5CYII=>

[image18]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAcAAAAYCAYAAAA20uedAAAAcklEQVR4XmNgGOTgGxCfQheEgf9AXIAuCAL6DBBJJmRBGyD2AuLdUElfKB8MioC4BCrxFsoHYRQAksxFFwQBXQaIJCO6BAisYYBIYgUgiXfogjAAkgQ5CgaOILHBkipQ9k9kCRDoYYAo+AHELGhywwEAAMS4F/hUVNxNAAAAAElFTkSuQmCC>

[image19]: <data:image/png;base64,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>

[image20]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABMAAAAYCAYAAAAYl8YPAAABGElEQVR4XmNgGPGAF4inAHExugSpYBUQd0PZKkD8H0mOJFABxDZoYiDDatDEiAK30QUYIIY1oQsSAtOAmBtdkAFiGCO6ICEACxtRILaHsv8gsUkCB4FYkgFiKAiDDPqCooJI4MSA3QUgQ+vRBQmBQ+gCUHAAiL8h8UuA+A4Q30cSwwC40tI/IP4MZYNcPxtJ7hcSGwWcRBeAApAlU6Hsn0CsjCaHAVwYIE5HBwUMqBpAbFA2Q+abIvHB4AgQ/2VATUugyAAplkISA/E50fgRSHy4IAg8gLJBuBMuiwAgcR40vhUSHwxwxSQ6AGlGDzMuJD44vByRBfCAOiAuQ+JjRMBhdAEC4CYQzwHi30AsgybH4IsuMArwAgDvkTrHqxDJxAAAAABJRU5ErkJggg==>

[image21]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACEAAAAYCAYAAAB0kZQKAAABV0lEQVR4Xu2WTytEURjGHymFmhSKnZ35FjaylL2PYGkhWfoKTLKxYMNWPoNEbEUpiZQ/kSgUnnfec9xz3ty5YxrH5v7q15zzPrc559773jsDlJQ0Zpq+0s/A2yB/M9lpkLWdCegil6beSz9oj6n/Gf5sbS0pm9BFF91cxp1ZnIYOZFfjhfbFcTreoZsYs0FK9qCbOLNBKlbpHH5uUEsNxcf8mhm64ca+QWVDeQyg+U0c0ClbtIzT/WAeNmgey3TFFnNo9D11Rum1LSJ7Uw7ZwCHZMO2mu/Q8jutsITsZsRrHQBddg4YytsxCsysbOCTrh75pF+hNHH8zSY9sUTihD/SOPtLnOMa9q0su4yc6H+SD0E2sB7U8DtFEP7TCEvTpqKD4fhflLSM/aL5X/CLb7lOaWnKPz+XWt5Xw7HbocTAX5DZK0woX0EdUrlpSRmzhP7D/SUpy+QLCrley1mCs+wAAAABJRU5ErkJggg==>

[image22]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAHQAAAAXCAYAAADa+mvTAAAEz0lEQVR4Xu2YV6glRRCGy4hrwICrCCIoGB8MiChiwJzj6oPhQVRQQX1QDKgPK2LArIjhxRUEEyiiYERBRPBBdxUTKnLNERMGFGN9dtU5NXV65pzr3ntl3fmgON1/9fRMn5qprhmRnp6e5Y8js9Cz1GyfhXFsloV/ydtq62exZ0b4Kws1vpYycKLBY7hS7ZLQXyzDucdZz3g2Vfs2izU2kaX/U1eU9jm+kOJbLTuUtaT4tsuOnio/qR2WxcwG0h6MSXlK7aYsGh7QVbLDOFPtrCz2VNlcJojVejLBoDFw/MpZNDyg0U/7CGvzdD8QfD3d8F+unsXIutIM6FZqZ6vdora7aceq3aO2rQ8KUFB13RC1gO4ozf32KPvdT21XtZ3tF7aRMp5z72Qa13OR2l3Wpwq8Ru0G69fYRe01KdnkgOQD1vG42htqp6u9aDpFHv3rpDn/SWqXqd0XtOPVLlW71/rnSRmXuUptSso1Txf+y6uzGMkB3VPtEdNOU3vedH/c+TMjTD5JQAkQxqLpx4A656o9LcXvBcBB1sceNO18tR9N+1OG+8odpvnN4Hyu9mjoP6P2SegfqvZW6HMT+ZoI9CLrvzoYIXK5aXHtFwftDyk3Ie2Tze/1itcM51h/OnBD/prFSA6oky/WNTbmyHOmt+EB5a4k+KRX+rWAOi/LcM4N1d4LPucYKWNWSvoPpjv3p76DdoW1v5LhU+XkY+jHgMJHpkd4ktG4bnhSbQVro/sD4qA9lLQubpfRczboCuiiipbHfmDWRi3l7i/NgJJSMxzDH53P5xwudd9eUvRTrU97ydA94HcZHs8rF22yAmlyVR8UwJ8D+qHpEdJo1mC+FJ2sR7DduAF5miflAqnPP6AroLdWtDx2Su39pEVqAeUPI20634S2w8bPcQuT7hwio9cCnAfd73raLwzdA76T5vE8Sb4+7OHgAzT24Mh0AsoNhs669022Txg3Dm642vwDugKaX0V8sZEnpOxjbYx7bYE8J1CAUKTg4xozbQGlkEO/3vq0axkkroVXN4f3ZZ5ofOsEnX7cZ+FT0yNtAd1Siu6Zo4s1sxC4TerzD+CxZ4DneQeNSjdreTKCnrWIB7SWxoDKNaccCrDXrf2l1OdvCyhFA7p/yGDPr41D+z6084cPtFhc0X839F3Lc19b0Rz0N7OovBPaa0v3A8ID9HMWI1tLOVH+BotGQZG1fLFbVLQI+xJ+LjRzoRQfT6JznGnxBqj9mR7QWDBtZFp8r/XUfULQvNJ2aE+FvmsRUjSVtbOH2m8yOu7uiuZwDD6qaofCDN0hM+XMGOH4G7PoUP6SNqjWKO35tkuVRhvtYykLYUOnQHGNdoST8IEgMp1vuafYMeylzP+ZlA/9QJrz6+F3oeke0DWkrMPnOtD8Ea6NVxUf81jT/Y+2g/1iPCFkiYxnG4x3U/Zm7+8mJeD+f7KGX8phDciIrNOPYx2OaxhrrYGvtgXNKKRF3svmEu5yFvd/o2tNG0u3f8aYJ3N0osACmftzzjYUYV37J9vX0VmcLZ5VOyOLswTp7hUpAb1TRr9eLatQmd+cRYNU3ZaGZw32mK6Se6Y4WEoFyvdZ9q69m+5lFqp9Akchx9oi/1k2OjELPRPDN+mXZPRjSqyCe5YX/gYbxIKc+Mpd1wAAAABJRU5ErkJggg==>

[image23]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABIAAAAXCAYAAAAGAx/kAAAAp0lEQVR4XmNgGAWkgmgg/gnE/5HwGyT5X2hyt5HksAI3BojCp2ji3ED8D4i50MTxApit6GIkg5UMEI3NUD6IzYyQJh4wMiBc9Q2IBVClSQO/GSAG2aNLkApOMkAMuocuQQqYBcTlDNgDnWjwF4hZoWxnBohBdxDSxIHPQCyKJkayq54AsQm6IAMiKdSgSyCDFgbUpP8SVZphLZIcCJ8D4kIUFaNgpAMAXYMxGjJZzX0AAAAASUVORK5CYII=>

[image24]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAHEAAAAYCAYAAADNhRJCAAAC80lEQVR4Xu2ZS6hOURTHF8nzEvIo6mYiCRkZmF2JmDFTJgqJAUokDC4DysBIKBMDAzPMpBSGJpIiKcQAeb/fj/VvnfPddf93n3OP853z+U7tX6369n/ts/Y5a++zH+cTiUQikUgkEuKo2ju1P4l9UXtN2t1W7eq5rvZRBtr6pPZK7b3TrrRqN4+O5jcNGOKbZPuqAvG/s6iME/N9ZkfD6Eh+EQRvRYgeMX8/6VUxWyz+IXYkLBHz95HeJGrP7zqxIMvY4cgbSe1ySiw23ros4L/JYkPoSH7vyPAB2m4khyKxi9TpVjqS3yIBitQpC+J+ZdExXazOY3Y0hCK5K1InF1x8lUXHSrE6le2iHDPFYveT7jksVuckOxpC7flN5+s+0j33xerMIP2Y2njS/pV0PRzLDkdolOKthHaO9G6jbH5PqL1RO++0TO7J0AQx8P9y5c1q6xO93U4MdZBnhJj/mdNwlkxBAp64crdRJr8X1XYkv+dJgQ3dcElMF+WR7JDqOjFvPcT5kO8P5VXJ76VJuVspk1+Up1I5F1TIOr8cFPMvZEdCXiduFNuQ5DFHLEbW+RAjEv4p7HDslvBD7lEbxaJjltpaFpV9LCj7WVBWqy1gMUCZ/ELzuQs9XwvcHCqsIH2N2GehH6QzuHYCi8piMV9u48olCQ+ETWLTywvSQ+D6+aRtT/QPpHtC94c1CNo2p+1MtOdOS6d4vp4pm9+3MrCG9kpGO1g0kaT0RmA/xT7/4NveWbXRrdrZ4LqJLCbckOxOuC2D2/8tg9vHhqkIt2ToKE55KBYzi71qF0hbpPaANACNBwpmiUekpVSRX3TwAbUjktGJVYHgk1h05CWxXc6IHU/ALqd7an14sYHaCWp9DgSfzKIDO8c62Co2ZW5Q2yLhjdEYtdMsVkxdyX0pNkjBcbHTQOVg8ce8jcbwt1EoiU/F1o468NMUDPfA+C17HVxWm8ZiRSxXuya2Icra9HUELMj/E/wzUCdzWYhEIpFI4/gLI3EETchUf60AAAAASUVORK5CYII=>

[image25]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADsAAAAYCAYAAABEHYUrAAABVElEQVR4Xu2WPUoEQRSECwMF/zDyFB7CDTQ2FAzFS2iiqYGhiYvizwk8gYgHMFLEUAUFFY1U3EXr8WbW3ofNdPtD7w79QQVbrxq6hpneBjKZTD+zTj1TH4VeqEfjnXfSvc2dNXyUxb7jDf5Zak7xtffgPUrw2JoFo9D5qvF7iUMElp2HBht24BD15BIQXPYM1cHalA0pEpJJSVTZI2s6zEIzvzmVx6h9j/aoXWqH2qaa1JYuCyaobPm9Thvf5RKamTT+BjVsvFQElb1AdUjmbef3ErVQ+H1VtupbLA+vATtAXNkh6AUmRjEEl/X9v65B51N2UBBT9r+pLLsCDcwYfw56XXw3vkXWjlgzESfQ/cgb1MUm9BssX2FRC3otlLvxATXYSfuRdXLKpkT2e0tdU1fUDXVPLbqhv0DKjluzrkjZCWvWjWXqCfq6PFCv3eNMJpP5GZ8cQnDtQB5w7gAAAABJRU5ErkJggg==>

[image26]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADYAAAAYCAYAAACx4w6bAAACMklEQVR4Xu2WPWsVQRiFX4mgUVQsYtDaUsHKQsVEDRYJihY2qQVBLAQFRZQLNibYiaYw5A9YiVXAwqhpQvIPFImFnSKSKIH4dY4zc3f33Jlkr95dRe4Dhzv3vLM7887sfJh16fLPsw26D13RwF/gGjQGbddAuzyC7vryXuhHLlYnh6F5X95irh8HsnB7XIeOiMcX3hSvanZCT8RrQCvileaVGuYSu61mxcS+khfQVzXLMAFtVdNcIxvUrJA90C01zfVjVM0yhFHqgwZ8mSMUynXxzP9uMtf2Zugp9LhZo02eQ7vNJUgxqeVCjXoIAxz6EfRbHLf4zPCFDTUrJsxYnknog5pl4MKMMQN9Ee8iNCxep+AAH1UTDFpx1k5Cq9A7aGPObyE11d+hJV/mMXDBXN2qEnuphmfcsj4eNJdQINX3X8yp4eFDDyJeVYmlOvneshjX/b1cjP6O3P8mQ9BrNcFlize0VmLnoH7xuH2fFY/cUMPi7XFXpL/L/9fB5v/oMTALfbPiWTVg7gF2SqE/oqa55xnTzsW8j97jeg1wgPmJ5a9N3PJZ73zOu2Nu7QcYj96MQqOLvkzxm07B+Ck1PTxrrorHa5qeQfuhN+JxgMm0Zf3gtaq3WSNjAXpo7i7JehyUFlI7Ygq+6LSaHUBntSzR55jpMTXXgS86o2YH4AWhDJcsS4YXitj+kNxeYxyCPpk7KKnPxfAfccLiF4QYPdBbaMoSSZHUWqmbfWp06fIf8BOH/nyOftc1UwAAAABJRU5ErkJggg==>

[image27]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAEUAAAAYCAYAAACsnTAAAAACNklEQVR4Xu2Xz0tVQRTHT4sWJoWbgtz1w6WLiHaBKa0EaVX9ASKoqyIQiUJo1Q+X1iZJzECwfQS6sB8udJVgtVDETYtyIalEC63O981cnfu9c95Twfcer/uBL8x8z5wZztzh3rkiOTk5h8Bx1ZDqDgf+VyZUT3z7vOpvEKsm7qvWVb9UnRQrxjHVgri6llRn0+Es/arL5CH5HnmV5otqMuijyJmgb3FG9T3oT4mrbzDwMiyyIS7pAZsV5ITETy+8BjYJjLkd8WLzFXimqmdTXMIRNivIJ4kXAW+YTSK2Aa+910N+gWTwSVWLb28F7WohVhiw/JBrkj0p0+LyOsgv8E51WnYnx4ZspkZUB1bxll8KM69N4icCgwfY3Cdjhl6qRlUjqhfijv5zn1MMqwjLL8Z1cTk3OQDes+GZFvfJS8DR+6FaVR0N/HJiFW/5FnhPYnwXBxKsyf6oNny7Vdy9JcHKOWys4i3fAmNRk8ksGx4kPvVtHG28qMLYXni8T5UCDym2NryvbBrg9DcF/XNCF8Cr4m52zC1JL447APqfVb2q9iBWTm6IvSkXybtLfbCsOkUeHjy+ujt8VG1L+i7SIm6RxsADfd6HLlGsnGD97qCP3xLeqDXv4QEmvPVeTCkSY8W3oUc70V0eqi749rhEJiojdeLWn1PNq35L9oLZLO5UhPBGmJtifXkYTnwl2f+kmgDvk6Jv4ICf1H9D/ZrhAxslwC13RPVNdSUdqh2i9/2cnJycA/APzHqgZDh+cgQAAAAASUVORK5CYII=>

[image28]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAFgAAAAYCAYAAAB+zTpYAAAC+klEQVR4Xu2YS8hNURTHl3dRJK+ZPJJEJmbIa+KdkQwoIqJICgNhKAMlSpkYKAbIa+JR3sWMCZKS8ipERN7C+t99trPO/559Hjff/T61f/XvnrXWPrt91tl77X2uSKTLMFv1QvVW1Ydilt2q3+La9adYJAAS9cDYSGAeO1Q9k+uxEm4XIW6rVhkbiRthbM9j1U9jo90CY0cCIFELjY3lv8XYIXDfIHZ2AvNUx9hZAibUJ3HPcIFinr6qe+LaPFKNyoargw7mGvuV6qCx8ziqusPONrJV9VHc2KHj2XAhWLHLk+sekvZh956R4vLguSSuzR7jqwwvdczgbcZmJqhusLMTqZPg7qofquHG109cH9+ND/YmY3sfVJunkq3Bv1SzjG0ZoDps7GnmuoxuqinJbxF1y06dBM+R/ESxj21wIvGtI3+G+arTqunGhySdM7bt+IlqcnKNxNxXrRD3QvaLmxFVuCqu39fJL1ZJKNFY+nWok2BwSFwJsHBCF0nzDL4mro3dr/6yXVxwZmLjPLsvDctJ1XnVe9VU47+uGpdcf5B0IDygIiapNpBvvLj795If5/Gz5CujboIZbGbo4xkHiOAz++Ta2YZleMvYHQmOdyEwm+wLe5cNVwL3Yfm2ymcJJM6wWFybJRwACGBpg16qNYmvXYRKgcV/wLQCngUrsBU2irsfp4kQGD/arOYAQM31A9ilWiv1N5F/AZYhdm+M5ZtqYjac4Qo7SkCfp9hZAZQubOhloH9fWpvYKe2drSGQ1GHJNR4MG1mo5r1hRwl4vjPsLGGw6gv58saD8jHG2KMle+JqbFihBC9jRwcR+lLCkQ1je6iaIe7rEfZA06YKuCe0MaJ2+hfrQTnIq/WcJ+wdQ8l3QDWEfI0bV5IPNRk7djs4wg4CZeuuuGVeVAvz6C3u+W5yQNLayYnzPpYtF5gUHM/rqwFOD18lbXA5G/4vWS+ulOAvVizt56qX0rzsUTo2G3upNCfM66Jpx7HCBEcikUgkEolEuhR/APy7zZapyN4YAAAAAElFTkSuQmCC>

[image29]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAB0AAAAYCAYAAAAGXva8AAABYUlEQVR4Xu2Vu0oEQRBFy1g/wdBIxUQz0cBEfGCkqZGYiYGRweIPGBhqaCSoGBkLJiKCXyAG4gMFBfEBgqLea3czNTXd6+4w0bIHLtNVt6f6UcusSJtWZw16g368zvN2gSvJ5vK9lbzdHKEQlWIAqombM2i8UtxIduIU19CJ1J/TMJPQAnQo6YIH/vnfbTTMqX+yP7GCXdCSH9PfU15pwkLsE8fdyiMf/jkuzu9VXmlu1ZhF51W8DHX6MW8kdhNNw90vqphFt1WsrzLVzx5oS5y3D23k7SKhnwG+yF8pudOGOG/X5AJjEt9QFDsxnGYE6lf5KZ/vUznNEXRmkykeTPworviFyfNLZTeooTdhk5YO6FLcZ02zI/HiqX4G6nl/rEPP0BP0Cn0pbxqaU/G7ZHNfoE9oVflkVOKLztpElRxL8Y9i08SVw1POqHgYuldxpXAhtib0m/oW14IhNa9NC/ILUDJePOXLu4oAAAAASUVORK5CYII=>

[image30]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABoAAAAYCAYAAADkgu3FAAABPUlEQVR4XmNgGAVDDdQD8Rcg/g/FZ1GlMcBDBoRakL5iVGnCAKYZhHEBPSCuZYCoMUaTIxo8YUD4DBd4DMTHGPCrwQu8gDgFiLcw4DZkHZQm5Gu84ASUBoU3NkN4gDgXygbJr0aSIwnADAeFO4gtgyQHAj+gtDsDRF4LSY4k8BSJDTIoDomfD8TcUDbI59h8TBQAuTINiQ8yaCESHzmYqBI/MAAyCJS6QOAZsgQDRG4VmhjRAN2FMFfbArEOkrg3VFwbSYwk8BKN/4YBYuBtNHFQiYHuKBjwBOJbDJC8yIkmx8AIxHcZIEUKMljOgN1AfPEDE18KxOHIEj1A/AGI3wLxZyD+gyTnA8ShSPyvDAi1n4D4NxBXIsmDAMwRyImK6gAWVEkMuH1MFYBsOE0t2ssAySI3GLAkhFEwuAEAGqtV1gn3p38AAAAASUVORK5CYII=>

[image31]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAABHElEQVR4XmNgGAWjYBTAgAEQzwRibiifF4hrgbgIiBlhioCgDIgXALE0khhBwArEh4HYD4j/A3EzA8QQEKiHimkB8U0gZgZiKaiYDFQNQXAQSicwQDQ2IqTAPgGJPUISAwGQWAmaGE4ACgoQALkQpBEZJGERA/kCJKaNJJYJFQtDEsMAIAXH0MRALke3AORDdDEQwCaGAkAKPLCIwYIQWewtmhgI4LUgggG7ApCYPRYxFyj7O5T2BeI3QHweiD8BMRtUHA4uM2BagC38bZDEqoFYBco+zQBJcSCgzABJlSjgDxBPRhObA8Tv0MRAABQ8IEsCkcSQHRIDxL+Q+FQByBbcBuKpSHyqAGQL0IOVKsAOiC8A8VV0iVEw8AAAv84/tdxc9TMAAAAASUVORK5CYII=>

[image32]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAB4AAAAYCAYAAADtaU2/AAABXklEQVR4XmNgGAUjDdQD8Rcg/g/FZ1GlMcBDBoRakL5iVGnSAcwwEMYF9IC4lgGixhhNjmzwhAHhc1zgMRAfY8CvhiTgBcQpQLyFAbeh66A0oVAhCZyA0qD4wmYoDxDnQtkg+dVIchQBmGWgeAOxZZDkQOAHlHZngMhrIclRBJ4isUEGxyHx84GYG8oGhQy2ECELgHyRhsQHGbwQiY8crDSJXxgAGQxKvSDwDFmCASK3Ck2MbIDuA5ivbIFYB0ncGyqujSRGEXiJxn/DALHgNpo4qERDdyQIXAPiT0j8biCWBWIhBuzqGRiB+C4DpAhEBssZsGvAFr/hUPovEHNA2chq0NUz9ADxByB+C8SfgfgPkpwPEIci8b8yINSCfPYbiCuR5EEAl2WwbEgTAMp6R6FskKMvIskVILGpDkC+nwNlTwLiTVB2FZSmKQAlSJCvLRgg0XIGiA1RVIyCEQEAWGlcw5rGXa8AAAAASUVORK5CYII=>

[image33]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABUAAAAYCAYAAAAVibZIAAABCUlEQVR4XmNgGAW0BvVA/AWI/0PxWVRpDPCQAaEWpK8YVRoVwBSCMC6gB8S1DBA1xmhyWMETBoSLcYHHQHyMAb8aOPAC4hQg3sKAW8M6KE3IN3BwAkqDwgebBh4gzoWyQfKrkeRwAphBoHACsWWQ5EDgB5R2Z4DIayHJ4QRPkdggTXFI/Hwg5oayQT7C5hMMALI9DYkP0rQQiY/sVZLDEwZAmkCxDALPkCUYIHKr0MSwAnSbYa6xBWIdJHFvqLg2khhO8BKN/4YBovk2mjgop6E7AAMwAvFdBki2QwbLGbBrJhiePUD8AYjfAvFnIP6DJOcDxKFI/K8MCLWfgPg3EFciyY+CUUALAABbjUmZS+msywAAAABJRU5ErkJggg==>

[image34]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADIAAAAYCAYAAAC4CK7hAAACXElEQVR4Xu2Wz0sXQRjG3yy0QiVC0K4R6jX9C7wU1KH0IIEegkDRIIMCL0Kn7AcoeBY6hZfqlFp5CL0reMtOaZcwqNAo+4X5Ps0svT47+90RdiHCDzzszPO+++7szu7Miuzzf3ORjQI5w0ZZvFY1sFkg1aoNNpmnqt97EHNHNcKm56y4AVQ63/JY/uZtqR6ZWKdqyfRT4KTugMcXbQ14VQEvBHI++2MWR1W3xOXcoFgCYo1sguPiZsSSDG6ZfPCW+nOqCfJCoN60P2bxXTUqLucAxRKuiJupFDOSPum6uGIXyMd7Ok4e8g6Rx9SpHqpuSvaNXFPVqn5Idk5CMD7EhvJJwsnHZPe0npRwHnNXdUrVLi7/xO7wH574I+LvbSAAcs6xGQKJMQO8L3F5P00b+b2mD5LXFTOC+KCJhcCsvWCTOSiu2CIHAixI3I3YHLQfmH6b6rRvY+Zi6q2o1thkhsUVO8+BACiWVxBPecr0UXvV9N+YNmYu5kaeSURe3hJpwSBW2STwlFtMH7WT+rPGB/DXyQuBBSp3jPZCeTxXbbNJ/KJ+spBg2e8zfr33rxovi1eqj2xasLyiWMz3AbB/5N00x5OdG3uGZcz7vBWE+CZu/8pkUlyxy+Rn0SzpgVrw6vCA+8Wdc5h8zGylWhbkpX5Qu1RfxU35By98JzEbE0AO/gQsuMimuFo44iOu8bEm1T3fBrgW/sWQiyNuHK9sJWLGtWewed1ms0Quqd6xWQRHpKQnlAGuhVkthZeqATZLoEM1z2bRYP3H5lcW+A6/sFkW/A9VJD1s7PMvswMYGKad874oPgAAAABJRU5ErkJggg==>

[image35]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADUAAAAYCAYAAABa1LWYAAACZElEQVR4Xu2Wu2sVQRjFj08EFbURJJWIKKKImio2WiQGbARF8gcIsRHEVoIKVvZqShErEUF7QSQoggRsFDEpRA1Wxic+o34ns5P73bMzuyn2XgjmB4edPd/Z2dnX7ACL/N9sMi1Vs0G2q9Fp1pneqNkwT0y71MxxyfTR9LfQN9N78Z7PpdMwk+MdWv1U5chqtHJ/TG/by7M+M/Om6qQ/kK9NmM6oKRw3jSL0sUFqnu+oHseA6auaVbCjB2oWrEGonxef5AbgGS+2zB7zBccp01qEzG2peVjvUTPFEEL4oBYcqTt42fRFvBTxOG6v+oKDF8InwcxOqXn4bY2pmeIZygNWUhfF/YvipYiTCPMvfKHgdbF9iPI5lPgAakkNWElluL9VPOWQ6UTRTvWx17SnaKfqKeaTmQ3dV9MRXwudBektF0955NqfUB7QK9dm7abbz6F9lIiP84D4npcImY3i13aO9swd2b/r2oMItR3Oy8HcKjU9fMfrBsf6jJqoP45MufZptI5Zbzrpao9drQ7mOFNmYaCqsziJpJZA9Jep6TiM9oHvRjiG3yH/fZ66cXhqcwzk/k8XEOq5KZa1LWo6nqqBcMwkyq8P/Vvi5ai8qLMIgX7xjyAsk36Jr/DYc2oW7EOoc6HroXddPM6O9HvFT3EUmYu6gvCNxEdO/UZ4Jbj2u2FaOZfOc830QU2EHzLXjxT74wQR8d/YiOmzaRohyyUQ13xV8F/mZ9TGiQvQbsLzrVCzaXjnh9XsEPtNP9XsBLxr3Xpa/GTqfvaNsRnpNV2T3ENrOdU1tpmWqNkgfWosshD5B8WVq6y3vkg5AAAAAElFTkSuQmCC>

[image36]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAC4AAAAYCAYAAACFms+HAAABc0lEQVR4Xu2UvS8FQRTFj9BIaBWIKJSEXuI1NBQSvShUmtephOyfQBAN0akUGgmiUhEKEiUt0ahofIR7352Vcd68j13xKOaXnMzcc3Zm79s3u0AkEvkr+kRnog/RMWX/lgKs4ZQhqhtOPxsV0CbnyHsRnZL368zAmpnlIEAH7FodfY6cX8aCaJq8baqzksBuNk5+NZYQblB7KfNf3ajBiJvr09E6cXUWNkXvsLOZlT0EGhTWQf6WqM3NNSh4md488epa7IueRd0cZOAE4cZXYH5Xaiy6cdkFPhvwLqxAk+hCdC9qpywPOyjvQ1mD+S0cqHlH3gPVIXSjW9G1qJmyPFQ643oyQn7JnCTvkupq6JM/h/349OjlYRjWS11flZ6AWRR1klcv+oI9If967WWKPN3vkbwSevGgm7eKbrwsL6uiN9EABzU4hK1L0X9T++v1vC8mYKHqgLKfMg/bd4yDKlzBvlC7sLWj3+PGkqXxSCQSaSCfj9dRVRFfyJUAAAAASUVORK5CYII=>

[image37]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAEcAAAAYCAYAAACoaOA9AAACb0lEQVR4Xu2XS8hNURiGPyWSSylk8GeAcjegyECZuY8QAxkhExkYGeifGEguQ/UbkSgKAxkxEpmYkYTkGuV+KXfe9//W/s+3v7P2/vc++3RM1lNv+6z3/fY6a++z9lr7iCQSicT/ox/6Av0Nup2P23girVqetzcf9wR+9wC0A9oKbQnaDK02dTGeQuugsdBkaBf0I1cRIbtgqoiF0H7RmsUu6yV2rF5HTV0MX0+NylVEeC6tGVTEM+imlNd4VnmjC7yAlkCzoZnQdGgO9NkWFZDdwGPQApdFWQNthy5L8YVfCMfsbldlkuigz/igQ5ZB670p1cdUtW6IW+HI9SN28jhod/jM/LzJqjIeeiU680a4rClXoEXeLCB2faVkJ3Ad4ec+k5Fv4bhSNJ9rsrqMhO5Aj6ExLusEPlKfvFkCx/8BugHdhz7m43b4DGfw5G2mvUd0ZSecYbXvfAnXRAc3xQc1+A3N8GYJfvzvIt4QnA07TZuFJ03bPkLMCjtqwGnou9S7SMKtuOl4uJWzj+U+INl6k8FC7krkpQ1Es3PO6waHRPte6oNh4A7b9OasEO3juPMH8Z1ns4N3cr7x1wZ/nvGackr0BWyWDypSdyb/kfZ6vhDSO+D8QV679hvR4gfO55uz77hTroo+69zmm8DxvPemod+1WW/XV3Iw+NOsye30kejfActZid+Eur+Sh7vUXeghNNplnTBVdDz8OxDjkmhul4ENwbew5p41DotuZ29FX9B+mYzTbJNpf5VWLbfMn9A+kw8Ht2uuDdd90AV4YRe9GZgoOksmOP+I6Hl8Yng8kY97y0ZvJBKJRCKRaMI/voihheGIzbIAAAAASUVORK5CYII=>

[image38]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACAAAAAYCAYAAACbU/80AAABEElEQVR4XmNgGAWjYJCBb0B8Cl2QnuA/EBegC9IL6DNAHMCELkFrYAPEXkC8mwHiAF8on26gCIhLGCCWv4XyQZjuAOSAXHRBegFdBogDGNElSAQ+QNyFLsgAyVnXgbgJXQIG1jBAHEAuEGKARNtJBkwHfAFiZii7BoizkOTgAGT5O3RBMsBBBkwHIHsM5BCsHgUJghIiDBxBYpMC0B2gyoBpITofDECCKlD2T2QJEgHIAd1IfGsGTAvR+WDQwwCR+AHELEjioELpOx5cilAKBiAH9CLxpRkwLUTnUxWAHNCHJoZsIchzNHfABDQxZAvDgHgeEp+q4BMDpCR9A8SfkcRB0fiPAeKwR0jio2AUgAEAp0VASHkmCKkAAAAASUVORK5CYII=>

[image39]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACAAAAAYCAYAAACbU/80AAABIklEQVR4Xu2VPU5CURCFD8IKbG2hNCwAV0CgZREmJsRYUlniT9iAFNQmtkYrExrYgL21UKjxp/BnhrmYyblEeSbcSPK+5CT3nCnmXHgPgJycf8azaMxhSj5FbQ5TUYUV2ODBqtkR1UXXsALN4JOxLzqALZ8Er0qOFtjjMBXbsAIFHmSkIepyCHuzbkWHPJhzDivwGwMOApuwr22EuMCTqBjOHdGum32jy6ccLuCSA+IGcQF/MS2y8KIa6oM4Z+jOnisOCC5QQbyQ/QwNy+H85gfEMgWOnK8hXsh+xjFs8CoqufxM9OL0Tl7l0QInzm8hXsg+E8t8AqeU+YV6uZUX6FHmF7ZEfecz81OBB9gv6b3o0eX63/IBK3bn8j9xwUHO2vMFtPFHFiJT2WAAAAAASUVORK5CYII=>

[image40]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACoAAAAYCAYAAACMcW/9AAABHklEQVR4Xu2UMUtCYRSGX8X+gJNztDSEf8DFNRH8GS1BSFtbU4j/IIxC3NqElsCpqS0ocAm3KLBoEl3Uc7pH+O7xXMPl1PA98MI9z/FyX+V+ApFIZBuqlCFlQempXYoJ5VFLJ5qUeTAfISlswosTLZ3gZ+8b7kI5lGWR1wsHGrB/vRkCX6EcUu5F1mX2ZAC76AiB53fjVMSnzBxPvmEXfYHhWRxrmcElpZuRG8o15YrSkc/Wfu7Khp+9Voh4gvIHInKhdOQNdtFnKH+rhTNZ7+grlOfhKxS/cE5pbRE+oJs4g100deoZHvhArXgIrr3gDkXD9bXYk2v+Fn/BO5K/oxUlJL12Aoe2yCmlEC6cGVM+KHdI+uym15FIJPLvWAJ2olFPnrcp/QAAAABJRU5ErkJggg==>

[image41]: <data:image/png;base64,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>

[image42]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAEcAAAAYCAYAAACoaOA9AAAClElEQVR4Xu2XTahNURTHlyLJR5H0BuoNDHxmYqDEyMDzyAQzGclMBkYGeoqBRAaKkUQvQmEgI0YKvZeJSELyTSGf+f5Y/9be3XX+d5/7zr3ndd9k/+rfOeu/9tl3nXP32XsfkUwmkxk7BlRfVP+CbhXTTTyRRltct6OY7irLVJ/EajlEuVYcVP1UvVMtp1ySeMNQGYtVu8TaLKFct7mheuPie6qdLi7jo2qvi7+p9rk4yXNpjKAynqmuS+s2TB8bo8AeKdYwM8SXnZdipTTXPiPhFehXbVFdkvKG58NxpNHFoPDPqlOcqAF+/xh58yhOgVcpVTu8TWxGboYj5o/UxVNU28I58udcripTVa/FRt44yrXDKrEa1od4ncuNBK77xaaYf5vNSHwgmEdwPtvlwPdwjIUtcLl2Ga+6o3qsmkS5KpyRxj+9WzVd7HV/5dqUgeswgTPwMfckeeHO0XCzi7erJodzjLDUyOqUq2IT5CxOtOC+WA3vyYd3mDwmdR2An7wvjIatLkajEy72r1BpJzUZVP1QzeFEgmGxGnzNoEptyH9gU8z/yyaI800EDTFMwUufEMudJW802C/W91JOJDgu1pYfZNWHgz+Bgf+ATcAdxh9ZoVrk/DXBX+i8upwUW0HmcqIFq8XqmE9+1YeTagPvKJvAb6TAW0k/SeycUx13whWxdx/LfCegDl564fGrMUDxEWm+B6yc8Caw+Ujsc8BzWpo7AGVPvSpYpe6qHqomUq5dMOL+uBhbDdTW47yLweNpAJ4f/UNCK9gBsYkJ3xbYoP12ubWqjS7+Ko226AT7hCrb9AiWa+y+r3GiJhfEbhTzIo5+CgBY4rEKTyO/V6w9VsqnUlypu84GNjKZTCaTydThPwAetWMakloBAAAAAElFTkSuQmCC>

[image43]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAoAAAAXCAYAAAAyet74AAAAn0lEQVR4XmNgGHQgDYgL0AWRAQcQ/wdicSC2AeKfqNIIAFJkhcZnR+KDwRYg/o0mBlLoiiwgDBUMRBaEihUhC2yDCiIDFaiYO7IgSOAvEDNB+YxAPA0qDgcsUIF7QHwACYPEUBQmQQXkkQWhYteRBZZCBZHBIixiDNlYBEF8kE0oAGQlssI+IP6GxEcBX4E4BIiroGy8wBmIRdEFRzYAABkLJxqYpSHRAAAAAElFTkSuQmCC>

[image44]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAFsAAAAaCAYAAADYMiBQAAAClUlEQVR4Xu2YS6hNURjHPxRKeQxucosBeUwMdFOUcvOccJMBA4NbjCgGDCQGpG6iyCvyPFwjDEgphrc8RvIYkJJXmQl5lsT/31qbb39777Od7L117l6/+rfW91/7rH3Wt9deZ60jEhgHzYUOQLtMW6BgmOD1vv5TNwTKYwT0wpqGI9YIxJkIHRc3a1megV5BT/RF4LWJLXOgISoeBh0V1++A8pdAH6C30Frl14bZklwiGF/w9Ru+XOfLNJg8y0hooST7PmziWnEVumU8JmgHdNDXI2Wx2Rpgpy/5uS3K/6HqtYPJWKzi3dA9FecR/YBavvlyo8Qf1AlVrx1MxEXoiq9PiTfn8tEantOqzn6nQmOhCcpve55DX5tIM0vis467jmbLRRr6rYjgej1JxTeh99B+5dWOa9BtFc+X1pJ9zBoeLkWaoeL6zV2vp4vrlK8A6RL3yvFX/H8yBton7uAx3LT9LUzAUhVzOYmSvUf5Wdy3hue7NcBncdvBTLh3fAgtEPclXkIrfRs7bPh6lXCWfIGui0sy97StzEbCLRn74HrLstf7o8X1tV3cLG8Gj/J2/WUc9Wtn8Uyow3gxLokb3HJxX2KyauOTzxtkf4bOQ+egs+IOEqegk/4zefCeD1K8qtGHlULgXpPcleSALqd4ZcMHpe85DXoG9SmvKhrWKAoO8HGKV3Wyo3segrZB3bHW6pgh8eN5oXCAq1O8N8az7G1RefCeWfvaQQH/PLEzeI33uJ+sEt7zkTXBKGu0K3fEDXKZj6M946rfV1THJkk++HnQO+O1LRzcU3EzivVPUGfsimrZKn/WbiaZyR40cFBcNgIl0yPJ1zZQEvzzhMneAI03bYGCWSRuN7JCStxXBgKBQOCf+QX3uJrlUxPlAQAAAABJRU5ErkJggg==>

[image45]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAA8AAAAYCAYAAAAlBadpAAAAy0lEQVR4Xu2SMQ8BURCER6XSqiVahd8gWr3/4g8olCqVH6KlUGkQnUonR0hEEGaz7708e+/UivuSSS4zs5fbzQElI+pMvZ1u1JF6RF7Dl4vwRcsM6jdtECOFuTVJB5qtbeDpQwtdG5AJNJsaP7BB+pOFonUCqUKbelJ74+eQQbnwklpRd+dV41IKv68cJmbr/J/skC4NoX7dBjGpfYUr1K/YIEYKC2ui+KWBAbTQswHyw+F5TF2oDHrlE/XyoaMFHThA//fad1zy53wAhPQ9J2j9tisAAAAASUVORK5CYII=>

[image46]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABcAAAAYCAYAAAARfGZ1AAABHUlEQVR4Xu2Ur0+CURSGX5PJqtWN5GagWp3BQifSHMXCSPwDBKLJROSPsEIwSQDHKEw3mhMGDpw6eM/Ovdv9DhcFv0Lg2Z7tfu85O/fb/X4AO84LXdCGLaTlI1j36WtwnRq542u3vnDXa6nRMbRJnNE3+hVkp77ZUMYfwz1+kOUBmmdsAZqf2TCGNDZtSC6htY7J2/TcZFHy0AFXtkDuobV6kMn6xK1LQR6li/iRCPa4ivSWFugNnQe1KHaAkKXfdGBy3+uVh/8rvumRPtFPlx2GTf/Bn7c8uJBnl6eih/iQKjQ/toVtiJ23MIXmB7awDTKgZUOs33RjKtABOVvA6vCNN7qjE/oOfUtG9CfRoV+fDBxC/zdHyfKePTvNElGWUSRuS2OLAAAAAElFTkSuQmCC>

[image47]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAEkAAAAYCAYAAAC2odCOAAACsElEQVR4Xu2Xy8tOURTGl2sZmAgDyvcpkUQyMaAoTMwoRv4Al4hIopRSJAZyG0lJDAgzEQMG7hOminLLJddILmE99lrfWed593nf4gwM9q9WZ69n7dvZe5+131ekUCgU/m82qa1iMbBZ7ZvaL7V5FHMmqd2SVOcyxSL7JPX1Rm0uxdrkpdp3SfOBDa6HZVeIwT7Ww4lTUr04bHU9PMAntbvBf6u2J/gAC4c+nJnkOx/Udgb/i9ru4LcN5nFN0lwuUszJzTNL0yIdks5OxmQ0+HwSsQE3g79AOtuNymhtck5tqFQHgRmkdofFJpoWqalzaFusPNZ8PCOXTHf81DLQVrDYEj6ebza/40q1xaQ1kusAdFukF1bebj5zTOo6ysgRDPT7LLbE+1DOvctz8rvyN4vk+vlQjvCninIuOUJHbmqbGWobg/9I0lgTgpabdyOovIZFZYd0drTcNNc9MTL7JenjzUcZSZ+JfbXJWbUhwff89zpo10O5J2i8lkUDtxsWwsHVivrIMeCk+cxBSToSJ0A5Hn8H+k8WWyA3p7ghuGgWhVhP0HAdiwHkHVzfB8xHfV+4ppx0VOo6yl+D70B/wGIL5D7tZZLGO6H2imI9QcP1LDYwQlL9KebPMb/X7RZ3MQLtCIv/yCypbl/G55GbS1fQYAOLSp+k2Oyg5RI1/KWk4TONOeiwdLbD7xRow4I2Tm1J8J2tLCjbWDAuqA1n0TguacyrHOjGaEmN9nJAqlMy3fyR5k8cqJHAr9kfwfeX7w8agDYt+Lel87PI7fI70+INjJMPDTkyMtl0PJtAfD6LOU5LyvRP1Z7YEwN6QnY8UT+zZ38tWnFP7bPaGUn1FtbDf+iTFLui9lhSnww+E5zWCDbpIWkA2tTgY3xcDvhfiMW/EWIRjF0oFAqFQqHA/Aakl9cwax6VYwAAAABJRU5ErkJggg==>

[image48]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADMAAAAYCAYAAABXysXfAAABUElEQVR4Xu2Wv0oEMRCHxz+NIHKNbyA2Fja+gb2Fr3GFL2EjvoNYWdhYWFwh2gkKWosgFgpWKoqgIIr+5pLF2TFxZ7PuapEPPtj8ZpPLHBdyRJlMpgkb8Al+eDdLVcc7fdXZxXK5E3rkPtuE3GyIAzijw5aZhldUvbcSI3AAd8hNWC6Xh5gWinCogwTMzazABf8cm/Smgxoc6SCB2L6+cSeeH8hNmhLZLFwT47qc6CABczPyJT4XPD4X2RacFOO6nOogAVMzfF52VaYnVi5SQWfNyPMiM5647sevovYTE+TW0p4FskIrpmbudeApJs/BVVWLwXfBUsCLQFZoxdRM7IU9crVLct94Ezr5mY3DfR16RsmwgJHWmxmDt/BYFwTP8EWHCbTazDZ8JHe/8L3C/71CzMO+DhNo0gzv7wZee/mZsz+jSTP/Dj5/mUwm87t8AgpDYpY+w9xXAAAAAElFTkSuQmCC>

[image49]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABoAAAAYCAYAAADkgu3FAAABQUlEQVR4XmNgGAVDDdQD8Rcg/g/FZ1GlMcBDBoRakL5iVGnCAKYZhHEBPSCuZYCoMUaTIxo8YUD4DBd4DMTHGPCrwQu8gDgFiLcw4DZkHZQm5Gu84ASUBoU3NkN4gDgXygbJr0aSIwnADAeFO4gtgyQHAj+gtDsDRF4LSY4k8BSJDTIoDomfD8TcUDbI59h8TBQAuTINiQ8yaCESHzmYqBI/MAAyCJS6QOAZsgQDRG4VmhjRAN2FMFfbArEOkrg3VFwbSYwk8BKN/4YBYuBtNHFQiYHuKBhIBeJrQHwQiE3Q5BgYgfguA6RIQQbLGbAbiCt+NgFxD5T9HohbkOTAEh+A+C0QfwbiP0hyPkAcisT/yoBQ+wmIfwNxJZI8NsupDkAlCl0sYgfiX0h8JiCei8SnKgDFyWkGSKGMnB9HwRAAACmfVPtbWDhmAAAAAElFTkSuQmCC>

[image50]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAEcAAAAYCAYAAACoaOA9AAACfklEQVR4Xu2XS8hNURiGP7kNXMpl5pYpMlGSKKUoTBlhIDGSJANK/4CBASN+xkaEZGBgYiakGBiJKNdSyDXX8L6tvfq//e61ztnnnL+fwXrqbe/1ft/eZ+291/rWOmaFQqHw7xiCPkN/Kt2thxs8tZFcXre/Hh4T3kNHoHnQBGiFde+35wT0A3oLrZJYkvjAVI6l0GELOcskNpb4vkbtq2Xk+QAdde2v0DHXTvLCRkZQjufQTeucMwhr1MjA3z8InYV2S6wTa63Z95kJr8YGaCd01fKJl6tjt9HVD9egd9AsDWT4pUZLOJVSfae3Vc3I7erI+pG6eCq0pzpn/KKL9ctE6AH0BJossW78VKMl7HvqWvr31YzEF8I6wvO5Lka+Vcf1FuKLXKxXZkBvoFvQOIm15Ts0bKF+nLfQp5W1jDTM+6imBZ+1J8lLd87E7a69F5pSnXOEpUZWGxZaeMlxeg4CH5AfKrLcQr9YPzrBHE5fhX7yufgju1ybSSx0ET+FsjfpAEfjb+iUBkaZ3KjwMIfbAIU++9gg1psIE7kqkVc+YCF2QbxurLNw3SENDADrldLmwzHOKanQf6Qm0RvGH1kNLXH+xspf7LxeiCPopAZ6ZJuFfhwQv+3LSeXQO6MmeS1tFsvUm+QONHXjXpkPfYEuaaAlOyz0Y4749B6KNyTt09Z8Bi4K9GqjkeZjC38HPOeseQOSe+v9Ms3CtL2hgRZoP1L7syuVp2WAnh/9d0xq1XELhYn/LT5ZfVO1Cdrs2vzKMZc34T6Bu9PRYjx0z8JXnySxHLMtPCSXch65DOu2gFsGrsLTxV9g4Zrr0DOrr9T/NVvUKBQKhUKhoPwFrLiv/v57M6AAAAAASUVORK5CYII=>

[image51]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAEcAAAAYCAYAAACoaOA9AAACl0lEQVR4Xu2XS8hNURTHlxLJoxQy+DIx8DYxUEqZ+TwywUxGkokMjAz0KQaSx8DA4EsiEQoDGTGSR8mMJCRvCnmWN+t/1z7fXed/9znOuefrmuxf/Tt3r//a56597j577yuSSCQS/48B1WfVn6BbebuDx9LORb+tebunLFJ9FKvlAHlFPFGtVI1VTVZtUn3PZUTIBgwVMV+1XSxnAXm95rrqtWvfVW1z7SL8ODONymVEeCbtGVTEU9U1Kc9h+jkwDOyUfA2TQvuiixWBvP1iM20eeVGWqzaoLkjxwM+G679mF4PCP6lOsNEAfP9his2kdhF1am9xI1yxfsQ6j1NtDp/hn3FeVcarXonNvBHk1WGpWA2rQ3uV86oQG18pWQesI/jc5zzwNVyzwmY7ry4jVbdVj1RjyKvCKbEa1ql2qCaKve4vXU4Z6PtedVV1T/Uhb3fy3H1G5/WuvUVsZQeYYbWffAmXxYqbwkYJGBBqeEdxxA5SLAbXj/twbAjMho2ujcSjru1fIXiFN2rAcdU31XQ2ItwUq8HXDLqtDVs5+i1mA2TrTQYSMU3BC2+IeacpNhzsEbv3QjYiHBHL5QfZ7cNZItbvEMVb8A2zL8GTnOviK0J8jos15ZjYAWwGGyUsE6tjFsWrPJzf0pmDAyFiuyjewh+kwBux5PsUx8mZb9wtl8TedWzz3YA6sCBzDIP3DFAbOX59BbtDfJoPYjt9KPZ3wHNS4g+hyi9TBnapO6oHqtHk1QUz7pdr46iB2qa62PkQ88sAtn/EPcjB6XqIvWLb2VuxA9pP52GarXXtL9LOxf+YH1LtmJ6B7Rqn7ytsNOSc2MCwLuLqlwCALR6zZALF94nl443BdTBv95Y1HEgkEolEItGEv0aGryB78aepAAAAAElFTkSuQmCC>

[image52]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAEcAAAAYCAYAAACoaOA9AAACgUlEQVR4Xu2XS6hNURjH/8ojeRRh4jExUF4ThZQyI8wwZCBhIkkGBroDBhLX6HYHRiREycCQkcjEjOSV7vWIQp55hu9/vr2cb39n7332uvt2TNav/u2z//9v7bP2PmuvtQ6QSCQS/48+0WfRn0x38nEHQ2jXst3+fNwT3osOi+aKxopWonu/A8OijaJJopmi3aIfuYoCwg1TZSwVHYLWLHNZL7F9DdqXqyjHt6PG5yoKeI72CCrjmegWqms867wxCvD7D4pOi3a5rBts2y86KVriskLWi3aIrqL8xi9nx/C06zJD9El0zgcN+OWNCGL63uJ2duT8UdR4smhP9pn5JZPVZYroFXTkjXFZLD+9EUHR/VUSGnAe4ec5JiPfsuNaaL7QZLFwAr0reiqa6LK6fBcNiD6ILkD7tCpXUQ5rOaHfFD2AXqOSF+YzG28z53uhMzvhCIt+8hVch3Zulg+68BH6QwWWQ/s13Xhl+P6/K/D+wS/Zac5ZyIkuYF8hZqUXasBZ6GiY74MI2C8+tFi4lLPtah+QMN8EWMhViby0ATS76LzR4Bj02it8UMI4b2DkP9waaLtB57fwFwxfwie52PgbMn+R8ZpyBroBW+CDCrZC+3HA+XUezm901nBDSO+I81u8dudvoMWPnM8dqL/wSLkGfde5zMeyHdqP2c6n99B5fe6cNXZ+JUczf541uZw+gf4dsJxH8UOo88tUwVXqnuixaILLYvH9KNqfXck8Ow1synwLa+5b4zh0OXsL3aDZTRWH2RZz/gXtWk543GNwd1oXLtfcfd/wQQM44nhTXOl4/IrOvdM06CiZ6vwT0DZ8Y3g8lY97y2ZvJBKJRCKRaMJfnI2ppegxX6IAAAAASUVORK5CYII=>

[image53]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAEcAAAAYCAYAAACoaOA9AAACZUlEQVR4Xu2WP2hUQRDGJyIJJkYIaCqxSSFoTCPBQgLpDFErtbUSsQkpUglKGgsJ/gGbFKkUUUggWFjGShQbKxUNUURjxIiKRgU1Ep0vs+vNm9t3l7178Zr9wcfbnW/33d4wb3eJEolEonGMsr6x/jg9zNplvKLSWMwbydoN4QrrkQ3m8Jp1iNXG2sY6xfqVGRHA/2Eojx7WWZIxe43XKFpJ1rPW5Oj/6dWcGRHgDZUqKI951n2qPMYyYAMFs0LxybnEuszaY7wgg6wTrNuU/8en3bNadVm2sr6yblijAC6weik+OVE8cE/sH6HJm1lDrg1/SnlrpZ31jqTymoxXCy2sZ669rsnxE7CPoL1deeCHex4g8XcpL5aNrMesl6xNxothWbVjk/OZdY81y/qStctZUG1MPq76wyQ7O0CFRWe+AndIFtdpjSqcYfWrfmxyNJ8CsX+gGk6qPgZeVX39CcHLfVEdXGf9ZHVZI8AGkuuEJiY5FhzlmN9nDeD3Gw8G4lQCb7VB4k2aWBGMkbx7nzUCfLcBqi85/STzx018FVsJvjqQyW4VP+jiu1WsXq6RXMB2WqMCdwPCupA0tPeXhpbhj30NLoSInTPxVRZN/wPJ4DkTx83ZvrhWZki+dRzzRZBXOaOmj3F6fwXnXXyHDuI4fUHl3+9NCifBV1St4JR6wnpOcgwXCdaFS6zmlovrbeCIi2sw5qkO4PKE4+wjyQXtt/JQZsdUH+Xqxy6RHKGnlV8NHNdYOEq+aLA27IvYI/Eb71mHnddBUiVbXN9zkSQh+GLwnMja/5ejNpBIJBKJRKIe/gIuhan/ifVHGQAAAABJRU5ErkJggg==>

[image54]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAYAAADgdz34AAABKElEQVR4XmNgGAWDDcwD4k9A/B8Jv4TKMQLxKzS5d0DsBZUnCcAMwAb2M0Dk+NAliAUgl4IMOIcuAQX4LCcKZDNADPBDl4ACkNxPdEFSACjMcbnQlgEi14QuQQqABYE/EHszQCLRE4pPQuU44arJACADbgJxMRoug8rh8h1RABb+uJIervAvAeI7QHwfXQIdvGbA7UIrBohcM5q4ExDPRuL/QmJjAHxBsJsBIseFJg7ykTISH5d+BmYGiCSp6R8kxovGN0Xiw0E/A0QyDF2CAZJq8FmAnKpA/AgkPsNyIP4MxO+B+C0QfwDiv1A5biD+AhUDyYHU/GCAJGEYABnIg8YHxRfVAMhA9DhAjyeKQB0DJI/AALZgpBiAMuYcIP4NxDJocqNggAEAx65V0Ig6zrsAAAAASUVORK5CYII=>

[image55]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAHcAAAAYCAYAAADAm2IFAAADuklEQVR4Xu2ZWchOWxjHn0PITJIhnShyS4YifIgMcaUjilyQIS6EIpEMF4YLKVxw+HDiSBxJGSIzIRkyhzKeZDgyHMd08P/3rPW9z7vevT/ceN/N+tW/bz3Ps/a7917r2Wv6RCKRSCSSEepCy6GpYSCSbbZAS1y5NfTJxCKlxWzoBfQaGh3ECpgBdQt87NxZgS9SfK5A+4x9CTpu7AJuhA7Rzp0XOiNFpZ4kj6j0NQidZCVUO3SKXvBL6IwUlfOS3rm/h07iKzeGylz5gylHSgf2VVrnJvnlMNRMchXYsa/yakRKhbROTPT3luQvlBXnhM7IN8Ft5R8p2gCth8qhtaJD6mq9rFISO1FS/EdCh+OQ6DI7q8wXfVmOSD8SiZ0oKf4Ch+Mj9DJ0Zoy0d8syiZ0oKf5TocPBiitCZ4bgkFjwst+ZGtDib9SX4AeX9F70XbWOPtBN63BMlvwfWAo9ghpCD6C90FYT54b6GlTN2b9C2115LHQG6gidhf4U3YSz8bms/wfq4Op6OFXwHs+czbqbReeqXdBuqIqLkXPQJtHRprrzLYTWVNRQxkOXoTvQxCD2RPQeYyR34sN3/r+ihsh0qL2xi8FQSe/cvHY8Jvrwdi9bJlqxufFNEH1xNorH34ANXwu6CPV0vv3QcFf+C5oEvXM24bUjXLmLaGLYGDOe9BP97fuiz+jvyb+NTNnTBnrjyu+hFibGxJhrbHudLbOT+0PTEmJJjVoM+BxMVA+PjAuezTtuuzK1qCKaD2P+y0w6JamsEfi1dzW2jW+U3BEnk4AxJsd/oo3s4cvwi7UsEz1687ST3G+Hz5BkM2FmQrcCv6dOYIe/USxqij7LaeiCaEIXHDalrZSTsC+2E5pi7FbQW2OHjWDtXtBdY9sYh1x+YUn8DXUOfLx2sLH3iCZL2Ckcyjhke5ikPs7D92EmZq/jVoWrbtIDemhiJQ3nWzb018D/ENlDDd8AnJPIEOigKw90/rbOJrbBeGAyypXtUDsSGieaOB7Oby1dOUwYwrmc9/b4Ovwa10muY7hW4MGM5x40wJX5PH6E2CG6LvBwqilz5ZOi01MmOBo6KmEB9JuxD4guTCwc2tgAnUTn8W3OzyTigszDudDC1R8XVp5D0AnRxZTdo/pECnksuqDjM3mYNM8l/z9aXImyU/8VTVYLhzeKc/8g468qOuRdl+TkKlnscPYzU9+Uww7k3E+4uGRSRDIEh9mnrszjwHIT6wutEl2tc762W69IRmgCdQ+djqaiW71IpDT4DEBT+i68pUecAAAAAElFTkSuQmCC>

[image56]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAEcAAAAYCAYAAACoaOA9AAACgUlEQVR4Xu2XTegOURTGH8WKFCnlI6UsfCSlkFjIQvlYWigsJCxIkmSh/4KFBUusZUGUKBsLW0nZWJKFz1LIZ74/ztOZ23vmvPfO3P9M+Yv7q6eZ+5xz73tn5s6Z+wKFQqEwdoyIPoh+VbpbDw/xCINc9jtYD/8R3oiOiWaLxotWoH3ellOir6JXolUuFiVcMJVisegoNGepi6XYB83f5AM9sHMNOlDLSPNWdNy0P4lOmHaUpxisoBRPRLfQnJNiC7TfXh/oAMc5Ijon2u1iTazF8NynRrwa60U7RdeRTrxSHdtWVxtroP1bn1YD372RCV+l2NzpbfVm4HZ1ZP2IdZ4EfT0I45dNrCvzRd9E530gA/brAuce60v/njcD4YawjvB8lomRz9VxHTS+wMT6Ml30TnTDBxr4IjoNrR8XoXNaWcuIwzz+loc+a0+UZ+acidtNe79oYnXOFRZbWX1ZBH1Vcl81XiAfVGAZdF6sH00w57U3oX70uvgju0ybSSx0AfsKJQfpSCiQ/Cz3JbUqLMzhNsBD/6c3Sag3ASbyq0Se2wA0dsl5XdgGHWuPD2QywRvIe3CM85X00H/gTeIHDD+yGrrcAxsqf6HxRsth6BgbfWAUhBt7yPm5NyeWQ++sN8kL136J+J3kDjQ2cA7ckf4QLfGBDuyAzmOm8+ndd96Ia5/B8DWMq7zaaqT5EPp3wHIBwwOQ1F1v45pohjd74ucR259drTxfBujZ1X8HrladhBYm/rd4j/qmikt+s2l/xCCXg3CfwN3pWDINepH8lPPIzzAftmUK9Cs82flzoH1uih6j/qUu/E3wzyqLeY7mVX3+G+aKlmfKF9lCoVD4p/kNYNa15I0F5H0AAAAASUVORK5CYII=>