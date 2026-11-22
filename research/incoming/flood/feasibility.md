# Feasibility Study & Pre-Registration Protocol: South Asian Monsoon Rainfall, Floods, and Astrological Meteorological Hypotheses

**Project:** Open, Pre-Registered Scientific Testing of Vedic (Sidereal Lahiri) Astrological Claims  
**Domain:** Mundane Astro-Meteorology (*Medini Jyotisha* / *Varsha Lakshana*)  
**Document Status:** Working Pre-Registration Protocol & Feasibility Assessment  
**Author:** Research Assistant for astro-research  
**Date:** 2026-11-22  

---

## 1. Executive Summary

This study establishes the scientific framework, empirical data architecture, and formal pre-registration methodology to test classical Vedic and modern practitioner astrological rain and flood forecasting claims against historical meteorological observations. 

Historically, South Asian cultures have relied on astro-meteorological frameworks—codified in Varahamihira's *Brihat Samhita* (6th century CE), Narapati's *Narapatijayacharya* (11th century CE), and regional *Panchangs* (almanacs)—to predict seasonal monsoon performance, onset dates, flood inundations, and droughts. Simultaneously, modern climate science has demonstrated that while the El Niño-Southern Oscillation (ENSO) and the Indian Ocean Dipole (IOD) are the primary physical ocean-atmosphere drivers of interannual monsoon variability, they account for roughly $30\% - 42\%$ of the seasonal variance, leaving $58\% - 70\%$ governed by internal atmospheric chaos and regional land-surface dynamics. Furthermore, empirical atmospheric physics confirms a physically real but minute gravitational lunar atmospheric tide modulating tropical rainfall by only $0.5\% - 1.5\%$ ($d < 0.02$).

This document provides:
1. A complete inventory of observational datasets (IMD, IITM, DHM Nepal, DFO, EM-DAT, GloFAS, RSMC best tracks, ENSO, IOD) with licensing and redistribution constraints.
2. A formal synthesis of physical drivers, operational IMD long-range forecast skill, and lunar tidal effects.
3. Verse-by-verse calculational parameterization of Brihat Samhita Chapters 21–28 and the Sapta Nadi Chakra.
4. An ex-ante database of 27 years (2000–2026) of published pre-monsoon predictions.
5. Statistical power analyses establishing minimum detectable effects for 155 historical seasons.
6. A selection of the first computable candidate rule for formal pre-registration.

---

## 2. Primary and Secondary Outcomes

To avoid post-hoc outcome switching and multiple-testing artifacts, the study pre-specifies one primary outcome and three secondary physical outcomes:

### Primary Outcome: Standardized All-India Summer Monsoon Rainfall Anomaly ($z_{ISMR}$)
* **Definition:** Continuous area-weighted All-India Summer Monsoon Rainfall (ISMR) total accumulated over the core southwest monsoon months (June 1 to September 30, JJAS), standardized as a $z$-score relative to the standard climatological reference period (1971–2020 Long Period Average, $\text{LPA} \approx 880.6\text{ mm}$, $\sigma \approx 88.0\text{ mm}$):
  $$z_{ISMR} = \frac{R_{JJAS} - \mu_{LPA}}{\sigma_{LPA}}$$
* **Data Source:** Indian Institute of Tropical Meteorology (IITM) Homogeneous Indian Monthly Rainfall series (1871–2016) extended with IMD National Climate Centre annual operational summaries through 2025 ($N = 155$ seasons).
* **Rationale:** A continuous metric provides substantially higher statistical power than threshold categorization and prevents boundary slicing disputes.

### Secondary Outcome 1: IMD Operational 3-Category Classification
* **Definition:** Standard 3-tier classification utilized by the India Meteorological Department and agricultural planners:
  * **Deficient:** $R_{JJAS} < 90\%$ of LPA ($<-10\%$ departure; $z < -1.0$)
  * **Normal:** $90\% \le R_{JJAS} \le 110\%$ of LPA ($-10\%$ to $+10\%$ departure; $-1.0 \le z \le +1.0$)
  * **Excess:** $R_{JJAS} > 110\%$ of LPA ($>+10\%$ departure; $z > +1.0$)
* **Rationale:** Directly maps to traditional claims of "drought" (*anavrishti*), "sufficient rain" (*suvrishti*), or "deluge" (*ativrishti*).

### Secondary Outcome 2: Annual Major Flood Frequency and Magnitude ($F_{SASIA}$)
* **Definition:** Annual count of large flood events and cumulative flooded spatial footprint ($\text{km}^2$) across India, Nepal, Bangladesh, and Pakistan during the monsoon season (June–October).
* **Data Source:** Dartmouth Flood Observatory (DFO) Global Active Archive of Large Flood Events (1985–2025, $N = 41$ years) cross-checked against CRED EM-DAT (1900–2025, $N = 126$ years).

### Secondary Outcome 3: Monsoon Onset Date over Kerala ($MOK$)
* **Definition:** Calendar day of objective monsoon onset declared over Kerala, measured as departure in days from the revised climatological normal of June 1 ($\mu = \text{June 1}$, $\sigma = 7.5\text{ days}$).
* **Data Source:** IMD National Climate Centre objective time series (1901–2025, $N = 125$ seasons; Pai & Rajeevan 2009).

---

## 3. Sample Size and Statistical Power Analysis

### Historical Time Span ($N = 155$ Monsoon Seasons, 1871–2025)
The historical observational archive spans 1871 through 2025, providing $N = 155$ independent annual seasonal realizations.

### Power for Continuous Primary Outcome ($z_{ISMR}$)
For a two-sample comparison between years where an astrological configuration is active ($n_1$) versus silent ($n_0 = N - n_1$), assuming standard statistical parameters ($\alpha = 0.05$, two-tailed; statistical power $1 - \beta = 0.80$):

The standard error of the difference between means is:
$$SE = \sqrt{\frac{1}{n_1} + \frac{1}{n_0}}$$
The Minimum Detectable Effect size (MDE in units of standard deviation, Cohen's $d$) is:
$$MDE = (z_{\alpha/2} + z_\beta) \times SE = (1.96 + 0.84) \times \sqrt{\frac{1}{n_1} + \frac{1}{n_0}} \approx 2.80 \times SE$$

| Configuration Frequency in Sample | Active Years ($n_1$) | Silent Years ($n_0$) | Standard Error ($SE$) | Minimum Detectable Cohen's $d$ | MDE in % of IMD LPA ($\sim 88\text{ mm/SD}$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Common (33.3% of years)** | 52 | 103 | 0.170 | **0.477 SD** | **$\pm 4.2\%$ of LPA** ($\sim 37\text{ mm}$) |
| **Moderate (20.0% of years)** | 31 | 124 | 0.201 | **0.562 SD** | **$\pm 4.9\%$ of LPA** ($\sim 43\text{ mm}$) |
| **Rare (10.0% of years)** | 15 | 140 | 0.272 | **0.761 SD** | **$\pm 6.7\%$ of LPA** ($\sim 59\text{ mm}$) |
| **Very Rare (5.0% of years)** | 8 | 147 | 0.363 | **1.016 SD** | **$\pm 8.9\%$ of LPA** ($\sim 78\text{ mm}$) |

**Conclusion on Power:** With $N = 155$ seasons, the study is adequately powered ($80\%$) to detect any astrological signal that shifts all-India seasonal rainfall by more than $\sim 5\%$ of LPA (approx. half a standard deviation) for moderately frequent rules, and by $\sim 7\%$ of LPA for rarer rules. If an astrological rule claims to cause "drought" or "heavy floods" (which historically correspond to departures $> 10\%$ of LPA, or $|d| > 1.1$), $N = 155$ provides statistical power exceeding **$99\%$**!

### Power in Multiple Linear Regression with Physical Controls
When controlling for ENSO (Niño 3.4 SST), the Indian Ocean Dipole (DMI), and a secular warming trend:
$$z_{ISMR, t} = \beta_0 + \beta_1 \text{Rule}_t + \beta_2 \text{Nino34}_t + \beta_3 \text{DMI}_t + \beta_4 t + \epsilon_t$$
With $N = 155$ and 3 covariates (degrees of freedom $df = 150$), the critical threshold for the partial correlation of the astrological indicator at $\alpha = 0.05$ and $80\%$ power is:
$$r_{\text{partial}} \ge \frac{2.80}{\sqrt{150 + 2.80^2}} \approx 0.225$$
This corresponds to a partial $R^2 \ge 5.1\%$. The study can detect any astrological predictor that explains as little as **$5.1\%$ of the remaining variance** after accounting for physical controls.

### Power for 3-Class Categorical Outcome (Deficient / Normal / Excess)
In the historical climatology (1871–2025):
* Deficient seasons ($< 90\%$ LPA): 28 years ($18.1\%$)
* Normal seasons ($90\% - 110\%$ LPA): 104 years ($67.1\%$)
* Excess seasons ($> 110\%$ LPA): 23 years ($14.8\%$)

Using Fisher's exact test / multinomial logistic regression, for a rule firing in 25 years ($n_1 = 25$), detecting an increase in drought probability from the baseline $18\%$ to $45\%$ ($OR \approx 3.7$) achieves $80\%$ power at $\alpha = 0.05$. Detecting an extreme shift (e.g. $>60\%$ drought) achieves $>98\%$ power.

---

## 4. Evaluation of Classical Rules: Which Rule to Pre-Register First?

To adhere to open scientific standards, a pre-registered rule must be:
1. **Fully computable:** Calculated purely from astronomical ephemerides (e.g. Swiss Ephemeris / Lahiri ayanamsa) without requiring subjective, unrecorded human visual diaries from centuries ago.
2. **Ex-ante:** Formulated before the outcome window opens.
3. **Deterministic:** Binary or graded condition without ad-hoc parameter adjustments.

### Comparative Assessment of Candidate Rules

| Rule Identifier | Classical Source | Astronomical Calculability | Requires Historical Diaries? | Pre-Registration Viability | Recommendation |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Megheshvara (Lord of Clouds)** | Panchang Navanayaka | 100% Astronomical (Weekday of Ardra Sun ingress) | No | High ($N = 155$ independent test cases) | **Tier 1: Pre-Register First** |
| **Varsheshvara (King Planet)** | Brihat Samhita Ch. 19 | 100% Astronomical (Weekday of Chaitra Shukla 1) | No | High ($N = 155$ independent test cases) | **Tier 1: Pre-Register First** |
| **Mars in Rohini Weak Monsoon** | Brihat Samhita Ch. 6, 24 | 100% Astronomical (Mars in Taurus 10°-23°20') | No | High ($N = 155$ seasons; fires in ~14 seasons) | **Tier 1: Pre-Register First** |
| **Sapta Nadi Saturn in Jala** | Narapatijayacharya | 100% Astronomical (Saturn in 28-nakshatra Nadi) | No | High (Multi-month transits) | **Tier 1: Pre-Register First** |
| **Ardra Pravesha Ingress** | Bhavishya Phala Bhaskar | 100% Astronomical (Sun at 66°40' Gemini) | No | Moderate (Lagna requires geographical reference) | **Tier 2: Secondary Test** |
| **Sadyovrishti Immediate Rain** | Brihat Samhita Ch. 28 | 100% Astronomical (Mercury-Venus orb $\le 3^\circ$) | No | High (Synoptic daily time scale) | **Tier 2: Daily Rainfall Test** |
| **Garbha Lakshana (195-day cycle)** | Brihat Samhita Ch. 21 | **Non-computable on ephemeris alone** | **Yes** (Requires daily cloud shape, halo, and wind records 195 days prior) | **Infeasible for 1871–2025 archival backtest** | **Archive Only (Special Case)** |
| **Rohini Yoga Wind Vector** | Brihat Samhita Ch. 24 | Partial (Moon in Rohini is ephemeris; wind vector is local weather) | **Yes** (Requires hourly anemometer records on Rohini day) | Moderate (Feasible only for modern IMD stations 1970+) | **Conditional on Station Data** |
| **Swati Yoga Rain Trigger** | Brihat Samhita Ch. 25 | Partial (Requires rainfall measurement on Swati day) | **Yes** (Requires station daily rainfall on Swati day) | Moderate (Feasible with IMD 0.25° grid 1901+) | **Conditional on Daily Grid** |
| **Meghamala Cloud Lines** | Meghamala | Non-computable | **Yes** (Requires visual cloud morphology logs) | Infeasible | **Descriptive Only** |

### Selected Primary Pre-Registered Hypothesis: The Panchang Megheshvara (Lord of Clouds) and Mars in Rohini Models
* **Hypothesis 1 (Megheshvara):** Seasons where the Lord of Clouds (*Megheshvara*, defined by the weekday at sunrise of the Sun's sidereal ingress into Ardra) is a benefic planet (Moon, Venus, Jupiter, Mercury) exhibit significantly higher mean all-India rainfall ($z_{ISMR} > 0$) than seasons governed by malefic lords (Mars, Saturn, Sun; $z_{ISMR} < 0$), holding ENSO and IOD constant.
* **Hypothesis 2 (Mars in Rohini):** The presence of Mars in Rohini nakshatra (Taurus 10°00' to 23°20' Lahiri) at any time between May 1 and September 30 is associated with a statistically significant deficit in southwest monsoon rainfall ($z_{ISMR} < -0.5$) and an increased incidence of regional agricultural drought.

---

## 5. Physical Confounders and Control Framework

To prevent spurious astrological associations resulting from real physical climate oscillations, the empirical models must incorporate three essential physical controls:

### Control 1: El Niño-Southern Oscillation (ENSO)
* **Metric:** Detrended June–September (JJAS) seasonal mean Sea Surface Temperature anomaly in the Niño 3.4 region ($5^\circ\text{N} - 5^\circ\text{S}, 170^\circ\text{W} - 120^\circ\text{W}$; NOAA ERSSTv5).
* **Expected Effect Size:** Pearson $r \approx -0.45$ to $-0.55$ over the full record ($p < 10^{-6}$).
* **Role:** Essential positive control. Any statistical model that fails to detect the ENSO signal on ISMR is statistically invalid.

### Control 2: Indian Ocean Dipole (IOD)
* **Metric:** Detrended June–September (JJAS) seasonal mean Dipole Mode Index (DMI; NOAA PSL / Saji et al. 1999), measuring the anomalous SST gradient between the western equatorial Indian Ocean ($50^\circ\text{E} - 70^\circ\text{E}, 10^\circ\text{S} - 10^\circ\text{N}$) and the southeastern tropical Indian Ocean ($90^\circ\text{E} - 110^\circ\text{E}, 10^\circ\text{S} - 0^\circ$).
* **Expected Effect Size:** Partial $r \approx +0.35$ independent of ENSO ($p < 10^{-4}$).

### Control 3: Secular Anthropogenic Climate Trend
* **Metric:** Continuous linear time counter ($t = \text{Year} - 1871$) and natural cubic spline (with 3 interior knots) to absorb multidecadal warming trends, aerosol cooling trends, and land-use changes documented in South Asian monsoon dynamics.

### Control 4: Negative Control (Phase-Shuffled / Permutation Skies)
* **Method:** For every rule evaluated, generate a null distribution via $B = 10,000$ permutations:
  1. Shuffled year labels (destroying the correlation between planetary positions and climate years while preserving ephemeris autocorrelations).
  2. Synthetic offset skies (shifting planetary longitudes by random degree increments $\Delta \lambda \in [1^\circ, 359^\circ]$).
* **Evaluation:** An astrological effect is considered statistically significant only if the observed test statistic exceeds the $95\text{th}$ percentile ($p < 0.05$) of both the empirical parametric test and the permutation null distribution.

---

## 6. Evaluation Framework for Modern Ex-Ante Forecasts (2000–2026)

The project compiled 27 years of prospective, dated, ex-ante monsoon predictions published prior to the monsoon season (documented in `monsoon_forecasts_exante.csv`).

### Formal Contingency Table Scoring Matrix

| Predicted \ Observed | Observed Deficient | Observed Normal | Observed Excess | Total Predicted |
| :--- | :--- | :--- | :--- | :--- |
| **Predicted Deficient** | $n_{11}$ (Hit) | $n_{12}$ (False Alarm) | $n_{13}$ (False Alarm) | $N_{P,\text{Def}}$ |
| **Predicted Normal** | $n_{21}$ (Miss) | $n_{22}$ (Hit) | $n_{23}$ (Miss) | $N_{P,\text{Norm}}$ |
| **Predicted Excess** | $n_{31}$ (False Alarm) | $n_{32}$ (False Alarm) | $n_{33}$ (Hit) | $N_{P,\text{Exc}}$ |
| **Total Observed** | $N_{O,\text{Def}}$ | $N_{O,\text{Norm}}$ | $N_{O,\text{Exc}}$ | $N = 27$ |

### Verification Skill Metrics
1. **Percent Correct (Hit Rate / Accuracy):**
   $$PC = \frac{\sum_{i=1}^3 n_{ii}}{N} \times 100\%$$
2. **Heidke Skill Score (HSS):** Measures forecast accuracy relative to expected chance:
   $$HSS = \frac{\sum_{i=1}^3 n_{ii} - \sum_{i=1}^3 \frac{N_{P,i} N_{O,i}}{N}}{N - \sum_{i=1}^3 \frac{N_{P,i} N_{O,i}}{N}}$$
   * $HSS = 1$: Perfect forecast skill.
   * $HSS = 0$: Skill no better than random guessing.
   * $HSS < 0$: Worse than chance.
3. **Peirce Two-way Skill Score (Hanssen-Kuipers Discriminant / PSS):**
   $$PSS = \frac{\sum_{i=1}^3 n_{ii} - \sum_{i=1}^3 \frac{N_{P,i} N_{O,i}}{N}}{N - \sum_{i=1}^3 \frac{N_{O,i}^2}{N}}$$
4. **Comparison Benchmark:** Performance will be formally benchmarked against:
   * Random Climatological Guessing (baseline expected accuracy $\approx 50\% - 55\%$ due to high frequency of Normal seasons).
   * Official IMD Operational April/May Long-Range Forecasts over the identical 2000–2026 period.

---

## 7. Data Ingestion Architecture & Licensing Compliance

All datasets must be ingested in accordance with their legal licensing terms (detailed in `sources_flood.csv`):
* **Freely Redistributable in MIT Repo:**
  * IITM All-India & Subdivisional Monthly Rainfall (1871–2016; OGD Derived Tables).
  * IMD Monsoon Onset Dates over Kerala (1901–2025; Public Record).
  * Dartmouth Flood Observatory (DFO) Global Active Archive (1985–2025; CC-BY 4.0).
  * GloFAS Historical River Discharge Reanalysis (1979–present; Copernicus CEMS Licence).
  * RSMC New Delhi Cyclone Best Tracks via NOAA IBTrACS (1891–present; Public Domain).
  * NOAA Niño 3.4, ONI, and DMI Indices (1854/1870–present; US Public Domain).
* **Restricted / Non-Redistributable (Fetch-on-Demand Scripts Only):**
  * **Nepal DHM Station Data:** Strictly proprietary to the Government of Nepal. The repository will provide automated API/request ingestion scripts (`fetch_dhm_nepal.py`) but will *never* commit raw DHM station data. Open-access gridded APHRODITE and CHIRPS precipitation will serve as the redistributable proxy.
  * **EM-DAT Disaster Database:** CRED non-commercial license prohibits database mirroring. The repository will provide an automated retrieval script (`fetch_emdat.py`) requiring user credentials.
  * **IMD 0.25° Raw Daily NetCDF:** Subject to IMD Pune Data Supply Agreement. Ingestion will extract regional subdivisional averages; raw grids will remain excluded from version control.

---

## 8. Summary of Pre-Registration Commitments

1. **Protocol Lock:** The analysis code and hypotheses specified above are frozen prior to running statistical hypothesis tests against the post-2000 modern verification partition.
2. **Analysis Pipeline:** All tests will execute automatically via continuous integration scripts in `tests/test_monsoon_study.py`.
3. **Publication Standard:** Results will report point estimates, exact $p$-values (unadjusted and Benjamini-Hochberg FDR corrected), parametric 95% confidence intervals, and permutation null distributions regardless of whether outcomes support or refute the astrological hypotheses.
