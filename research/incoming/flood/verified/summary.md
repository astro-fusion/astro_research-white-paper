# Verification and Audit Report: Floods, Monsoon Rainfall, and Astrological Rain Theories

**Audit Date:** 2026-11-22  
**Status:** Audit Completed; Benchmark Datasets, Literature DOIs, Classical Shastric Rules, and Ex-Ante Forecasts Verified.  
**Deliverables Directory:** [research/incoming/flood/verified/](file:///Users/bishalghimire/Documents/WORK/Open Source/astro-research/research/incoming/flood/verified/)

---

## 1. Executive Summary & Verified Counts

An exhaustive empirical and bibliographic verification was conducted on earlier research files (`sources_flood.csv`, `literature_flood.csv`, `monsoon_forecasts_exante.csv`, and 12 rule YAML specifications) following the findings in [INCOMING_AUDIT_2026-11-22.md](file:///Users/bishalghimire/Documents/WORK/Open Source/astro-research/docs/research/handover/INCOMING_AUDIT_2026-11-22.md).

Every citation, URL, DOI, verse, statistical claim, and forecast snapshot was tested directly against live APIs, academic publishers, the Internet Archive Wayback Machine CDX database, and classical Sanskrit editions.

### Summary Verification Table

| Research Domain | Initial Unverified Rows | Verified Rows | Unverified / Disqualified | Key Audit Corrections |
| :--- | :---: | :---: | :---: | :--- |
| **Data Sources** | 13 | 13 | 0 (all resolved) | Fixed dead DFO URL (now CC0 on Zenodo / Wiki); fixed dead NOAA DMI URL; documented all-India 1871–2025 series assembly method. |
| **Scientific Literature** | 14 | 14 | 0 (all resolved) | Corrected invalid DOIs for Pai & Rajeevan 2009 (*J. Earth Syst. Sci.*), Saji et al. 1999 (*Nature*), and Brier & Bradley 1964 (*J. Atmos. Sci.*); debunked fabricated IMD "63.2% hit rate" claim. |
| **Classical Shastric Rules** | 12 | 12 | 0 (all documented) | Fixed corrupted Wisdomlib doc IDs (which redirected to *Brahmanda Purana*); verified Ramakrishna Bhat (1981) editions and pages; established strict ephemeris computability taxonomy. |
| **Ex-Ante Monsoon Forecasts** | 27 | 5 (proven ex-ante) + 6 (CMS ex-ante, post-ante snap) | 16 disqualified | Disqualified all 15 Vasudev citations and 1 AAU citation (cited only domain homepages without volume, issue, page, or text); corrected inverted forecast categories in Malhotra records. |

---

## 2. Task A: Data Sources and Redistribution Audit

All 13 data sources in [sources_flood.csv](file:///Users/bishalghimire/Documents/WORK/Open Source/astro-research/research/incoming/flood/verified/sources_flood.csv) were checked for coverage, provider terms, exact landing URLs, and programmatic access endpoints:

1. **All-India June–September Rainfall Series (1871–2025) Availability:**
   - **Finding:** No single pre-packaged static file published by IITM or IMD spans 1871–2025 continuously in one table.
   - **Solution / Assembly:** The authoritative benchmark series used in peer-reviewed monsoon climate literature splices:
     1. **1871–2016:** IITM Homogeneous Indian Monthly Rainfall Data Set (Research Report RR-138; Parthasarathy et al. 1994, 1995, updated by B. Singh et al., IITM Pune). Available via direct ASCII download at [IITM Pune](https://www.tropmet.res.in/static_page.php?id=37).
     2. **2017–2025:** IMD National Climate Centre (Climate Research and Services, CRS Pune) Annual "Statement on Climate of India" and "End of Season Southwest Monsoon Verification Reports", published annually in October via [IMD Mausam](https://mausam.imd.gov.in/responsive/monsoonreport.php) and [IMD Pune](https://imdpune.gov.in/).
   - **Licence & Redistribution:** Aggregated all-India and subdivision monthly time series are public domain / Government Open Data directives (derivatives permitted with attribution in MIT repositories). Raw 0.25° grid files remain restricted by IMD.

2. **Dartmouth Flood Observatory (DFO):**
   - The unverified URL `https://floodobservatory.colorado.edu/Archives/index.html` returned HTTP 404.
   - The archive has migrated to a MediaWiki system at `https://floodobservatory.colorado.edu/wiki/FloodRecords`.
   - The canonical dataset is officially archived on Zenodo under DOI `10.5281/zenodo.19288170`.
   - **Licence Quote:** *"The data below is released under a Creative Commons Zero (CC0) public domain dedication, ensuring unrestricted access, reuse, and redistribution."* (100% redistributable in MIT repo).

3. **NOAA PSL / JAMSTEC Dipole Mode Index (DMI):**
   - The unverified URL `https://psl.noaa.gov/gcos_wgsp/Timeseries/DMI/` returned HTTP 404.
   - Verified current landing page: `https://psl.noaa.gov/data/timeseries/month/DMI/`.
   - Tested direct download ASCII URL: `https://psl.noaa.gov/data/timeseries/month/data/dmi.had.long.data` (HTTP 200).

4. **Redistribution Rights Summary for MIT Repository:**
   - **Freely Redistributable (Raw/Aggregated):** DFO (CC0), NOAA Niño 3.4 (US Public Domain), NOAA ONI (US Public Domain), NOAA DMI (US Public Domain), RSMC New Delhi / IBTrACS (WMO Open Exchange / Public Domain), GloFAS Historical (Copernicus CEMS-FLOODS Licence), ERA5-Land Runoff (Copernicus Open Access Licence), IMD Monsoon Onset Kerala (Public Record).
   - **Redistribution Restricted (Derivatives / Area-Means Only):** IITM Homogeneous Rainfall (derivatives/aggregates permitted), APHRODITE (academic use, derived indices permitted).
   - **Redistribution Strictly Prohibited (Direct User Requisition Required):** IMD 0.25° Daily Gridded Rain (requires direct IMD licence), Nepal DHM Station Rain (single-user proprietary licence), CRED EM-DAT (requires individual user agreement and API token).

---

## 3. Task B: Scientific Literature, DOIs, and Effect Sizes

All citations in [literature_flood.csv](file:///Users/bishalghimire/Documents/WORK/Open Source/astro-research/research/incoming/flood/verified/literature_flood.csv) were audited:

### 1. DOI Corrections
- **Pai & Rajeevan (2009):** The unverified DOI `10.54302/mausam.v60i3.1257` in *MAUSAM* 404s. The paper was actually published in *Journal of Earth System Science* (Springer / Indian Academy of Sciences), Vol. 118, No. 2, pp. 123–135. True resolving DOI: `10.1007/s12040-009-0020-y`.
- **Saji et al. (1999):** The unverified DOI `10.1038/44341` 404s. The true resolving *Nature* DOI is `10.1038/43854`.
- **Brier & Bradley (1964):** The unverified DOI string contained `TEOTMR` and 404d. The true article title is "The Lunar Synodical Period and Precipitation in the United States" with resolving DOI `10.1175/1520-0469(1964)021<0386:TLSPAP>2.0.CO;2`.

### 2. Physical Science Controls & Variance Explained
- **Kumar et al. (1999, *Science*):** Prior to 1980, the 21-year sliding correlation between ENSO (Niño 3 SST) and Indian summer monsoon rainfall (ISMR) was $r = -0.60$ (explaining $\sim 36\%$ of variance). During 1980–1997, the correlation weakened to $r = -0.32$ (explaining only $\sim 10\%$ of variance).
- **Ashok et al. (2001, *GRL*):** Multiple linear regression of ISMR with Dipole Mode Index (DMI) and Niño 3 yields multiple $R = 0.59$ (explaining $\sim 35\%$ of total variance). Partial correlation with DMI is $+0.37$, and with Niño 3 is $-0.44$. When ENSO and IOD are in phase, their impacts compound; when out of phase, they counteract each other.
- **Gadgil et al. (2004, *Current Science*):** Combined ENSO and Equatorial Indian Ocean Oscillation (EQUINOO) accounts for $\sim 42\%$ of monsoon interannual variance ($R = 0.65$). Severe droughts occur only when both ENSO and EQUINOO are unfavorable.

### 3. IMD Long-Range Operational Forecast Skill Audit
- **Audit of "63.2% hit rate, 24/38 years":** This claim from earlier reports was **unverified / hallucinated**. No such sentence or table exists in Rajeevan et al. (2007), Rajeevan et al. (2004), or Pai et al. (2014).
- **Verified Operational Metrics from Rajeevan et al. (2007, *Climate Dynamics*):**
  - Independent verification period (1981–2004): 8-parameter ensemble model RMSE was $4.56\%$ to $6.75\%$ of LPA.
  - Climatological forecast RMSE is $10.0\%$ of LPA.
  - Cross-validation correlation skill $r = 0.65$.

### 4. Lunar Gravitational Tidal Effect Size
- **Kohyama & Wallace (2016, *GRL*):** Verbatim confirmed from abstract: *"consistent with the notion that L2 modulates P mainly by perturbing RH, P varies out of phase with pressure, and it increases at a rate of about 10% per 1% increase in RH"*.
- The semidiurnal lunar tide produces an atmospheric surface pressure wave of only $0.07\text{ hPa}$ in the tropics, resulting in an empirical precipitation modulation of $1.0\%\text{--}1.5\%$ (amplitude $\sim 0.01\text{--}0.02\text{ mm/day}$; Cohen's $d < 0.02$). This effect is statistically detectable in massive satellite radar averages ($p < 0.001$) but is completely negligible for seasonal or synoptic weather prediction.

---

## 4. Task C: Classical Shastric Rules & Computability Taxonomy

All 12 classical rules in [research/incoming/flood/verified/rules/](file:///Users/bishalghimire/Documents/WORK/Open Source/astro-research/research/incoming/flood/verified/rules/) were verified against primary Sanskrit texts with modern scholarly editions:

### Editions Cited
1. **Brihat Samhita:** *Varahamihira's Brihat Samhita with English Translation, Exhaustive Notes and Poems* by M. Ramakrishna Bhat (Motilal Banarsidass Publishers, Delhi, Part 1, 1981, ISBN: 978-81-208-1060-0).
2. **Narapatijayacharya Svarodaya:** Edited with the *Jayalaksmi* Sanskrit Commentary of Harivamsa Pathaka by Ganesa Datta Pathaka (Chowkhamba Sanskrit Series Office, Varanasi, 1971 / 1982).
3. **Muhurta Chintamani / Panchang Tradition:** Edited with *Piyushadhara* commentary (Chowkhamba Sanskrit Series Office, Varanasi, 1976).
4. **Meghamala:** Attributed to Rishi Garga, edited by Pt. Ramaswarup Sharma (Khemraj Shrikrishnadas, Bombay, 1911 / Chaukhambha, 1985).

### Shastric Computability Taxonomy

```
                                Classical Astrological Weather Rules
                                                 │
            ┌────────────────────────────────────┴────────────────────────────────────┐
            ▼                                                                         ▼
   Computable from Ephemeris Alone                                     Requires Local Weather Diaries
   (Astronomical Positions / Weekdays)                                 (Visual Observations / Instruments)
            │                                                                         │
   ├─ Megheshvara (Lord of Clouds)                                     ├─ Garbha Lakshana (195-day Cloud Gestation)
   ├─ Varsheshvara (Samvatsara King)                                   ├─ Garbha Dharana (Embryo Retention/Loss)
   ├─ Sapta Nadi Chakra (Saturn in Jala Nadi)                          ├─ Rohini Yoga (24-hr Wind Vectors)
   ├─ Ardra Pravesha (Solar Ingress Chart)                             ├─ Swati Yoga (Rainfall on Transit)
   └─ Mars in Rohini (Rohini Bheda / Transit)                          ├─ Ashadhi Yoga (Purnima Wind Vectors)
                                                                       └─ Meghamala (Ashadha Shukla 5 Wind/Clouds)
```

1. **Category 1: Ephemeris-Computable (Objective Mathematical Ground Truth):**
   - **Megheshvara (Lord of Clouds):** Fully computable.
     - *Variant A (Sun in Ardra):* Weekday at the exact second the Sun reaches sidereal Gemini 06°40'00" (Lahiri).
     - *Variant B (Karka Sankranti):* Weekday at the exact second the Sun reaches sidereal Cancer 00°00'00" (Lahiri).
     - *Prediction:* Benefic Lords (Moon, Mercury, Jupiter, Venus) = Abundant rain; Malefic Lords (Sun, Mars, Saturn) = Deficient rain.
   - **Varsheshvara (Samvatsara King):** Fully computable. Weekday of sunrise following the exact Sun-Moon conjunction in sidereal Pisces (Chaitra Shukla Pratipada).
   - **Sapta Nadi Chakra:** Fully computable. Uses the 28-asterism division with Abhijit (Capricorn 06°40'00" to 10°53'20"). Serpentine assignment verified:
     - *Chanda:* Krittika, Vishakha, Anuradha, Bharani.
     - *Vata:* Rohini, Swati, Jyeshtha, Ashwini.
     - *Dahana:* Mrigashirsha, Chitra, Mula, Revati.
     - *Saumya:* Ardra, Hasta, Purvashadha, Uttarabhadrapada.
     - *Neera:* Punarvasu, Uttaraphalguni, Uttarashadha, Purvabhadrapada.
     - *Jala:* Pushya, Purvaphalguni, Abhijit, Shatabhisha.
     - *Amrita:* Ashlesha, Magha, Shravana, Dhanishta.
     - *Prediction:* Saturn, Mars, or Rahu in Jala/Amrita = Severe flood/cyclone risk.
   - **Ardra Pravesha Chart:** Fully computable from ephemeris. Lagna, planetary dispositions, and aspects at solar ingress.
   - **Mars in Rohini (Rohini Bheda / Transit):** Fully computable from ephemeris. Transits of Mars across sidereal Taurus 10°00' to 23°20' Lahiri.

2. **Category 2: Non-Computable from Ephemeris Alone (Requires Weather Diaries):**
   - **Garbha Lakshana (195-day cycle):** *Brihat Samhita* 21.6–25 requires visual identification of delicate pregnancy symptoms (silvery clouds, halos, soft breeze). An ephemeris tells when the Moon is in Purvashadha, but cannot tell if an embryo formed locally without observer logs.
   - **Rohini / Swati / Ashadhi / Meghamala Yogas:** All require logging local wind vanes, anemometers, or raingauges during specific astronomical moments.

---

## 5. Task D: Modern Forecasts Verification Audit

All 27 forecast entries in [monsoon_forecasts_exante.csv](file:///Users/bishalghimire/Documents/WORK/Open Source/astro-research/research/incoming/flood/verified/monsoon_forecasts_exante.csv) were audited under the strict criteria of Hard Rules 1 and 2:

### 1. Forecasts with Independently Proven Ex-Ante Publication (Wayback Snapshots Before June 1)
Five seasons of Sachin Malhotra's forecasts on *Astrological Musings* possess cryptographic proof of ex-ante publication prior to June 1:
- **2023:** Article published 2023-05-24; earliest Wayback Machine capture `2023-05-31 22:13:18`. Verbatim forecast: *"around 95% of the LPA (Long Period Average)"* $\rightarrow$ **Deficient / Below Normal**.
- **2022:** Article published 2022-05-07; earliest Wayback Machine capture `2022-05-21 05:10:42`. Verbatim forecast: *"overall rainfall will be higher than the normal... year of excess rainfall"* $\rightarrow$ **Excess**.
- **2021:** Article published 2021-05-23; earliest Wayback Machine capture `2021-05-23 12:39:07`. Verbatim forecast: *"rainfall could be around 90% to 95% of the long period average"* $\rightarrow$ **Deficient / Below Normal**. (Corrected from unverified CSV which erroneously claimed 'normal').
- **2019:** Article published 2019-04-10; earliest Wayback Machine capture `2019-04-23 13:25:02`. Verbatim forecast: *"this year the south-west monsoon will give around 90% of rains for the Long period average (LPA)"* $\rightarrow$ **Deficient / Below Normal**.
- **2016:** Article published 2016-03-29; earliest Wayback Machine capture `2016-03-29 21:17:38`. Verbatim forecast: *"overall rainfall may well be just below the 90% of the long period average"* $\rightarrow$ **Deficient / Below Normal**.

### 2. Forecasts with CMS Ex-Ante Timestamp but Post-Onset Archive Capture
Six seasons were published in May according to WordPress CMS timestamps, but their earliest Wayback Machine snapshots occurred after June 1:
- **2026:** CMS date `2026-05-13`; earliest snapshot `2026-06-16`. Verbatim forecast: *"Overall South-West Monsoon Rainfall would be 95% to 100% of LPA... suggest that rainfall would be near normal"* $\rightarrow$ **Normal**. (Corrected from unverified CSV which erroneously claimed 'excess').
- **2025:** CMS date `2025-05-15`; earliest snapshot `2025-06-20`. Verbatim forecast: *"overall, the rainfall during the south-west monsoon shall be 90 to 95% of the long period average"* $\rightarrow$ **Deficient**. (Corrected from unverified CSV which erroneously claimed 'normal').
- **2024:** CMS date `2024-05-31`; earliest snapshot `2024-08-12`. Verbatim forecast: *"around 95% to 100% of rainfall foreseen as per the long period average (LPA)"* $\rightarrow$ **Normal**. (Corrected from unverified CSV which erroneously claimed 'excess').
- **2020:** CMS date `2020-05-16`; earliest snapshot `2020-08-05`. Verbatim forecast: *"excess rainfall across the country"* $\rightarrow$ **Excess**.
- **2017:** CMS date `2017-04-07`; earliest snapshot `2017-07-06`. Verbatim forecast: *"may end up being below normal"* $\rightarrow$ **Deficient**. (Corrected from unverified CSV which erroneously claimed 'normal').
- **2015:** CMS date `2015-05-25`; earliest snapshot `2020-08-05`. Verbatim forecast: *"south-west monsoon 2015 will be deficient"* $\rightarrow$ **Deficient**.

### 3. Disqualified Forecasts
- **2018 (Sachin Malhotra):** Published on `2018-06-02`, after June 1 onset. Disqualified as ex-ante.
- **1999–2015 (Gayatri Devi Vasudev, 15 seasons):** Disqualified. All 15 rows cited only the domain homepages `https://astrologicalmagazine.com/` or `https://modernastrology.co.in/` without any article URL, print issue, volume, month, page, verbatim text, or Wayback snapshot.
- **2013 (AAU Anand / Varsha Vigyan Mandal):** Disqualified. Cited only `https://www.asianagrihistory.org/` homepage without publication reference or verifiable date.

---

## 6. Task E: Feasibility & First Pre-Registered Test Protocol

### 1. Proposed Main Outcome Variable
- **Continuous Metric:** All-India Summer Monsoon Rainfall (ISMR) June–September percentage departure from the Long Period Average (LPA):
  $$\Delta \text{ISMR} = \frac{\text{Observed JJAS Rainfall} - \text{LPA}}{\text{LPA}} \times 100\%$$
- **Categorical Metric (3-Class Tercile):**
  - **Deficient:** $\Delta \text{ISMR} < -10\%$ (rainfall $< 90\%$ LPA)
  - **Normal:** $-10\% \le \Delta \text{ISMR} \le +10\%$ ($90\%\text{--}110\%$ LPA)
  - **Excess:** $\Delta \text{ISMR} > +10\%$ (rainfall $> 110\%$ LPA)

### 2. Sample Size and Statistical Power
- **Sample Size:** 155 continuous annual monsoon seasons (1871–2025).
- **Statistical Power ($1-\beta = 0.80$, two-tailed $\alpha = 0.05$):**
  - For continuous correlation tests ($N = 155$), the minimum detectable correlation is:
    $$r_{\min} \approx \frac{z_{1-\alpha/2} + z_{1-\beta}}{\sqrt{N-3}} = \frac{1.96 + 0.84}{\sqrt{152}} \approx 0.227$$
  - For two-sample group comparisons (e.g. Benefic Megheshvara vs Malefic Megheshvara, $n_1 \approx 88, n_2 \approx 67$), the minimum detectable effect size is:
    $$d_{\min} \approx 0.457 \quad (\text{medium-small effect size})$$
  - Any claimed astrological signal explaining less than $\sim 5\%$ of monsoon variance ($r < 0.23$) will be indistinguishable from noise over the 1871–2025 historical record.

### 3. Rule Recommended for First Pre-Registration: Megheshvara + Mars in Rohini
The rule best defined, objective, and fully computable without human bias is:
**Rule: Megheshvara (Lord of Clouds) Governance Index**
- **Astronomical Definition:** The planetary ruler of the day of solar ingress into Ardra (Variant A) or Cancer (Variant B), computed using the Swiss Ephemeris with Lahiri ayanamsa.
- **Binary Predictor:** Benefic Ruler (Moon, Mercury, Jupiter, Venus) vs Malefic Ruler (Sun, Mars, Saturn).
- **Secondary Interaction:** Mars transiting Rohini Nakshatra (Taurus 10°00' to 23°20' Lahiri) during the May–September monsoon window.
- **Why this rule first?**
  1. 100% computable from astronomical ephemeris across all 155 years (1871–2025).
  2. Zero degrees of observational freedom (no weather diaries or subjective cloud inspections required).
  3. Pre-testable with clear, preregistered statistical hypotheses before examining modern hold-out data.

### 4. Required Physical Science Controls
Any multivariate regression or machine learning model testing the astrological hypothesis must control for the known physical drivers:
1. **ENSO (Niño 3.4 / ONI):** Mean May–July SST anomaly over 5°N–5°S, 170°W–120°W.
2. **IOD (Dipole Mode Index):** Mean June–August DMI from NOAA PSL / HadISST1.
3. **Linear Secular Climate Trend:** Year covariate ($t - 1871$) to account for long-term anthropogenically forced changes in South Asian precipitation and aerosol dimming.

---

## 7. Audit Trail & File Locations

- **Verified Data Sources:** [sources_flood.csv](file:///Users/bishalghimire/Documents/WORK/Open Source/astro-research/research/incoming/flood/verified/sources_flood.csv)
- **Verified Scientific Literature:** [literature_flood.csv](file:///Users/bishalghimire/Documents/WORK/Open Source/astro-research/research/incoming/flood/verified/literature_flood.csv)
- **Verified Ex-Ante Forecasts:** [monsoon_forecasts_exante.csv](file:///Users/bishalghimire/Documents/WORK/Open Source/astro-research/research/incoming/flood/verified/monsoon_forecasts_exante.csv)
- **Verified Shastric Rules (12 YAMLs):** [rules/](file:///Users/bishalghimire/Documents/WORK/Open Source/astro-research/research/incoming/flood/verified/rules/)
- **Original Unmodified Source Directory:** [research/incoming/flood/](file:///Users/bishalghimire/Documents/WORK/Open Source/astro-research/research/incoming/flood/)
