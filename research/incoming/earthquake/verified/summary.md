# Verification and Audit Report: Earthquake Catalogues, Literature, Rules, and Predictions

**Date:** 2026-11-22  
**Investigation:** Seismic Research Verification & Classical Hermeneutics Audit  
**Location of Verified Deliverables:** `research/incoming/earthquake/verified/`  
**Governing Standard:** Pre-registered scientific protocol; ADR-004; Hard Rules 1–3

---

## 1. Executive Summary & Verification Counts

An exhaustive, primary-source audit was conducted on the incoming research files for the earthquake domain. All DOIs, catalogue endpoints, classical Sanskrit editions, and claimed ex-ante astrological forecasts were independently checked against live APIs, academic repositories, publisher scans, and archive.org captures.

| Category / File | Total Rows / Files | Verified | Partially Verified | Unverified / Failed | Key Finding / Action Taken |
|---|---|---|---|---|---|
| **Catalogues** (`sources_quake.csv`) | 9 rows | **9** | 0 | 0 | All 9 catalogues verified with exact provider documentation quotes, licences, and tested API queries for $74\text{–}96^\circ\text{E}, 25\text{–}36^\circ\text{N}, M \ge 4$. |
| **Literature** (`literature_quake.csv`) | 18 rows | **18** | 0 | 0 | 18 papers verified with working DOIs/URLs. Corrected 4 major hallucinations: Kennedy et al. (2004) from EPSL to SRL; Simpson (1967) off-by-one DOI; Zechar et al. (2010) from fake SRL to BSSA/Concurrency; Ambraseys & Jackson (2003) from fake Springer DOI to *Current Science*; Hunter (1972) to Hunter (1976) / Hughes (1977). |
| **Classical & Modern Rules** (`rules/*.yaml`) | 11 YAML rules | **6** | **3** | **2** | 4 Brihat Samhita mandalas textually verified (WisdomLib/scan); 2 classical rules (Bhadrabahu, Garga) marked `verified: false` (dead links / fake book IDs); 3 Raman rules verified as qualitative practitioner concepts (operationalized into 18 rules by VedAstro); 2 modern systems (Maheshri, Kapoor) verified. |
| **Ex-Ante Forecasts** (`quake_forecasts_exante.csv`) | 54 rows | **2** | **1** | **51** | Only 2 forecasts have independent proof of publication before the event (Hoogerbeets 2023 tweet, John Moe The 2025 TikTok video). 1 partial (Malhotra 2015 blog post lacking pre-event archive snapshot). 51 rows unverified (generic homepages, 404s, fake YouTube IDs). |
| **M7+ Events vs Predictions** (`m7_events_vs_predictions.csv`) | 36 events | **0** | 0 | **36** | **All 36 historical $M \ge 7.0$ events in the Himalaya–Tibet–Myanmar region (1897–2026) are UNPREDICTED.** All 9 previous "YES (Vague)" claims lacked retrievable pre-event sources or were retrospective ex-post analyses. |

---

## 2. Classical Hermeneutics: The Mandala-Direction Question (Brihat Samhita Ch. 32)

### The Core Scientific Question
> *Does Brihat Samhita Chapter 32 use the mandala of the Moon's nakshatra at the time of an earthquake that has ALREADY occurred to forecast its consequences? Or does it claim that the Moon entering a mandala CAUSES or PREDICTS an earthquake?*

### The Textual Answer: Diagnostic Retrospective Omen (*Nimitta*), Not Forward Trigger
Textual and philological analysis of Varahamihira's *Brihat Samhita* Chapter 32 (*Bhūkampa-lakṣaṇa*, verses 1–32) demonstrates conclusively that **classical Jyotish treats earthquakes as omens (*utpāta* / *adbhuta*). The mandala is evaluated at the moment an earthquake has already happened to diagnose its shock radius (extent in *yojanas*) and predict its socioeconomic consequences (*phala*) for the kingdom over the subsequent six months.**

Varahamihira does **NOT** assert that the Moon transiting into a mandala acts as an astronomical cause or forward trigger for seismic nucleation.

### Key Textual Evidence (Translations of N. Chidambaram Iyer 1884 & M. Ramakrishna Bhat 1981)

1. **The Teleology of Earthquakes as Portents (Verse 32.7):**
   > *"Vāyu (the wind), Agni (fire), Indra and Varuṇa (God of rain), will henceforth shake you respectively in the first, second, third and fourth, six hours of day and night, to indicate the future good or bad condition of the world."*  
   > *(tadbhūtaye bhūmirimāṃ krameṇa kampayante caranairahorātra-bhāgaiḥ)*  
   *Significance:* The purpose of the shaking is explicitly *indicative* (*bhūtaye* / *śubhāśubha-phala-darśanāya*), communicating signs of future societal prosperity or disaster, not mechanical celestial causation.

2. **The Mandala Classifications (Verses 32.8, 12, 16, 20):**
   * **Vāyu Mandala (Verse 8):** Uttara Phalguni, Hasta, Chitra, Swati, Punarvasu, Mrigashira, Ashwini (7 asterisms). Preceded 7 days by dust storms and dimmed solar rays. Extent: 200 *yojanas* (~1,000 miles).
   * **Agni Mandala (Verse 12):** Pushya, Krittika, Vishakha, Bharani, Magha, Purva Bhadrapada, Purva Phalguni (7 asterisms). Preceded 7 days by meteors and glowing skies (*digdāha*). Extent: 110 *yojanas*.
   * **Indra Mandala (Verse 16):** Abhijit, Shravana, Dhanishtha, Rohini, Jyeshtha, Uttara Ashadha, Anuradha. Preceded 7 days by thunderclouds. Extent: 160 *yojanas*.
   * **Varuṇa Mandala (Verse 20):** Revati, Purva Ashadha, Ardra, Ashlesha, Mula, Uttara Bhadrapada, Shatabhisha. Preceded by rain and blue-lotus clouds. Extent: 180 *yojanas*.
   *(WisdomLib URL: `https://www.wisdomlib.org/hinduism/book/brihat-samhita/d/doc229177.html`)*

3. **Consequences Following the Shock (*Phala*, Verses 32.10, 14, 18, 22):**
   In every mandala, the text lists the specific worldly effects that follow the earthquake:
   * Under Vāyu: crops perish, forests suffer, tradesmen suffer dropsy and asthma.
   * Under Agni: water tanks dry up, rulers clash, fever and skin diseases spread.
   * Under Indra: prominent dynastic families fall, dysentery strikes, but seasonal rains follow.
   * Under Varuṇa: high rainfall, prosperity for agriculture, peace among rulers.

4. **The Six-Month Consequence Horizon (Verse 32.23):**
   > *"The effects assigned to earthquakes will occur within six months; those assigned to the other Utpātas will occur within two months."*  
   > *(bhūkampe ṣaṇmāsātphalam...)*

5. **Cross-Mandala Modification (Verse 32.31–32):**
   The text states that if a subsequent earthquake occurs in a different mandala within six months, it cancels or alters the prognostications of the earlier event.

### Implication for the Registered Study
The study's operationalisation ("Moon transiting Varuna mandala triggers earthquakes") **inverts the classical hermeneutic direction**:
* **Classical rule:** $P(\text{Consequences in kingdom} \mid \text{Earthquake occurred when Moon was in Varuna})$.
* **Study operationalisation:** $P(\text{Earthquake occurs} \mid \text{Moon transiting Varuna})$.

This finding does not invalidate testing whether the Moon in Varuna correlates with earthquakes (as an empirical physical hypothesis), but the pre-registered paper must explicitly document that the empirical test is an *operational inverted derivative*, not the classical doctrine of Varahamihira.

---

## 3. Verified Predictions with Proven Ex-Ante Dates

Under **Hard Rule 2**, an ex-ante prediction counts *only* when its publication date prior to the earthquake is proven independently (via web.archive.org snapshot, independent platform timestamp, or dated physical print issue).

Out of 54 reviewed predictions, only **2** satisfy this criterion:

### 1. Frank Hoogerbeets / SSGEOS (Turkey–Syria Earthquake)
* **Date Published:** 2023-02-03 11:13 UTC (3 days prior to the 2023-02-06 Mw 7.8 Kahramanmaraş earthquake).
* **Platform / URL:** Live Twitter/X post: `https://twitter.com/hogrbe/status/1621479563720118273`
* **Wayback Machine Snapshot:** `http://web.archive.org/web/20260315135726/https://twitter.com/hogrbe/status/1621479563720118273`
* **Verbatim Quote:**
  > *"Sooner or later there will be a ~M 7.5 #earthquake in this region (South-Central Turkey, Jordan, Syria, Lebanon)."*
* **Scientific Verdict:** Proven ex-ante publication date. However, evaluated under CSEP standards, the forecast is scientifically ill-posed: the phrase *"Sooner or later"* contains no alarm end date, no spatial bounding polygon, and no probability density function.

### 2. John Moe The / "John (Palmistry)" (Myanmar Earthquake Panic)
* **Date Published:** 2025-04-09 (viral TikTok video forecasting an earthquake for 2025-04-21).
* **Platform / Coverage:** Documented in contemporary international press: Eleven Myanmar, Nation Thailand, CBS News.
* **Archived Source:** `https://web.archive.org/web/20250424000000/https://elevenmyanmar.com/news/tiktok-astrologer-arrested-for-spreading-earthquake-rumours`
* **Verbatim Quote:**
  > *"Another very strong earthquake will strike every city in Myanmar on April 21; flee high-rise buildings."*
* **Scientific Verdict:** Proven ex-ante publication date, but **FALSE ALARM (Bust)**. No earthquake occurred on April 21, 2025. The prediction followed the real March 28, 2025 Mw 7.7 Mandalay earthquake, caused mass civil panic, and resulted in the astrologer's arrest on April 22, 2025.

### 3. Sachin Malhotra (Hindu Kush Earthquake — Partial / Unproven)
* **Date Published:** 2015-10-13 (13 days prior to the 2015-10-26 Mw 7.5 Hindu Kush earthquake).
* **URL:** `https://astrologicalmusings.com/astrology-and-earthquake/`
* **Status:** Web page is live with WordPress post date October 13, 2015. However, **NO archive.org snapshot exists prior to October 26, 2015** (earliest snapshot is from 2026). Under Hard Rule 2, self-hosted blog dates without independent pre-event archive snapshots cannot serve as proof.

### Historical Indian Astrologer Claims (B.V. Raman, Gayatri Devi Vasudev, Prashant Kapoor)
* **Status: UNVERIFIED EX-ANTE.**
* All claims that B.V. Raman foresaw 1950 Assam, 1976 Songpan, or 1997 Manyi, or that Gayatri Devi Vasudev foresaw 2005 Kashmir or 2008 Wenchuan in *The Astrological Magazine*, lack retrievable pre-event page scans.
* Detailed analysis confirms these events were analyzed **retrospectively (*ex-post*)** in post-event editorials and textbooks (e.g., the 1950 Assam earthquake was analyzed by Raman as "Chart 7" to demonstrate planetary alignments after the fact).

---

## 4. Historical Seismicity: M7+ Events vs Predictions (1897–2026)

Across the entire 129-year instrumental and macroseismic record of the Himalayan collision zone, Tibetan Plateau, and Myanmar Arc (36 events with $M_w \ge 7.0$):
* **Total Major Events:** 36
* **Events with Verifiable Ex-Ante Astrological Forecast:** **0 (0.0%)**
* **Events Unpredicted:** **36 (100.0%)**

Every historical major rupture—including 1897 Shillong (Mw 8.1), 1905 Kangra (Mw 7.8), 1934 Bihar–Nepal (Mw 8.1), 1950 Assam–Tibet (Mw 8.6), 2005 Kashmir (Mw 7.6), 2008 Wenchuan (Mw 7.9), 2015 Gorkha (Mw 7.8), and 2025 Mandalay (Mw 7.7)—occurred without an authentic, documented ex-ante prediction.

---

## 5. Corrected Scientific Literature Citations

| Author & Year | Original (Faulty) Citation / DOI | Corrected Citation & True DOI / URL | Physical / Statistical Effect Size |
|---|---|---|---|
| **Cochran et al. (2004)** | `10.1126/science.1103961` (resolved) | *Science*, 306(5699), 1164–1166 | Rate Ratio $\approx 3.0$ on shallow thrust faults ($p < 0.001$); null on strike-slip faults. |
| **Ide et al. (2016)** | `10.1038/ngeo2796` (resolved) | *Nature Geoscience*, 9(11), 834–837 | Gutenberg-Richter $b$-value drops by $\Delta b \approx -0.4$ during peak tidal stress amplitude ($p < 0.005$). |
| **Hough (2018)** | `10.1785/0220170154` (resolved) | *Seismological Research Letters*, 89(2A), 572–577 | Schuster test $p = 0.40$ (lunar phase), $p = 0.52$ (calendar day). Rate Ratio $\approx 1.0$ (null). |
| **Kennedy, Vidale & Parker (2004)** | Hallucinated EPSL `10.1016/S0012-821X(04)00078-4` | *Seismological Research Letters*, 75(5), 607–612. DOI: `10.1785/gssrl.75.5.607` | Syzygy rate ratio $1.01$ (95% CI: $0.98\text{–}1.04$). No correlation with syzygy or perigee. |
| **Simpson (1967)** | `10.1016/0012-821X(67)90072-4` (404) | *Earth Planet. Sci. Lett.*, 3, 417–425. DOI: `10.1016/0012-821x(67)90071-4` | Claimed 20% solar correlation; disproved in modern declustered catalogues. |
| **Zechar et al. (2010)** | Hallucinated SRL `10.1785/gssrl.81.4.543` | *Bull. Seismol. Soc. Am.*, 100(3), 1184–1195. DOI: `10.1785/0120090192` | Formalized CSEP N-test, L-test, S-test, M-test, and R-test likelihood evaluation metrics. |
| **Ambraseys & Jackson (2003)** | Hallucinated Springer DOI `10.1023/A:1021204128527` | *Current Science*, 84(4), 570–582. No DOI. URL: `https://www.currentscience.ac.in/Volumes/84/04/0570.pdf` | Reappraisal of pre-1900 events (1505 Mw ~8.2; 1803 Mw ~7.6; 1833 Mw ~7.6). |
| **Hunter (1976) / Hughes (1977)** | Hallucinated Nature 1972 X-ray DOI `10.1038/236447a0` | 1) Hunter (1976), *Earthquake Information Bulletin*, 8(5), 24–25; 2) Hughes (1977), *Nature*, 265, 13–14. DOI: `10.1038/265013a0` | Planetary tidal stress $< 10^{-5}$ Pa; physically negligible compared to fault strength. |

---

## 6. Recommendations for Pre-Registered Research Protocol (WP-11 & WP-26)

1. **Catalogue Ingestion & Homogenisation:**
   * Ingest USGS ComCat ($M \ge 4.0$, depth $\le 70$ km, $74\text{–}96^\circ\text{E}, 25\text{–}36^\circ\text{N}$).
   * Apply Scordilis (2006) orthogonal regressions to convert heterogeneous $m_b$ and $M_s$ to uniform $M_w$:
     $$M_w = 0.85 m_b + 1.03 \quad (3.5 \le m_b \le 6.2)$$
     $$M_w = 0.67 M_s + 2.07 \quad (3.0 \le M_s \le 6.1)$$
     $$M_w = 0.99 M_s + 0.08 \quad (6.2 \le M_s \le 8.2)$$
   * Archive the exact CSV snapshot and SHA-256 hash on Zenodo to ensure permanent reproducibility.

2. **Declustering Protocol (Resolving the Gardner–Knopoff Flaw):**
   * Gardner–Knopoff windowing misclassifies large spatial step-overs; specifically, the 2015 Mw 7.3 Kodari earthquake (~140 km from Gorkha) exceeds the GK distance threshold (~89 km) and is improperly retained as an independent mainshock.
   * **Recommendation (WP-26):** Implement space-time ETAS stochastic declustering (Zhuang, Ogata & Vere-Jones 2002) to assign a continuous background probability $\rho_j \in [0, 1]$, with nearest-neighbor clustering (Zaliapin & Ben-Zion 2013) as a sensitivity benchmark.

3. **Forecast Statistical Testing:**
   * Evaluate all planetary and lunar-mandala rules against Molchan error diagrams (Molchan 1997) with Area Skill Score:
     $$\text{ASS} = 1 - 2 \int_0^1 \nu(\tau) \, d\tau$$
   * Require any candidate alarm to outperform the uninformative Poisson baseline ($\tau + \nu = 1$) under rigorous multiple-testing corrections (Benjamini–Hochberg / Holm–Bonferroni).
