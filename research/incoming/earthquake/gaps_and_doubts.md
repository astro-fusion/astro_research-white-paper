# Gaps, Doubts, and Methodological Limitations

This document records the data gaps, ambiguities, and critical doubts identified during the compilation of earthquake catalogues, seismological literature, and astrological claims for the Himalayan and global seismic testing project.

---

## 1. Catalogue Incompatibilities & Magnitude Homogenisation

1. **Heterogeneous Magnitudes in ComCat and National Bulletins:**
   - ComCat reports mixed magnitudes ($m_b$, $M_s$, $M_L$, $M_w$). As shown in the study review, conversion via Scordilis (2006) equations creates an uneven Mw grid with artificial binning artefacts (empty and doubled bins for slope 0.85 on 0.1-unit $m_b$).
   - National networks (Nepal DMG/NEMRC and India NCS) predominantly compute local magnitude $M_L$. Converting $M_L$ to $M_w$ in the Himalayan crust is non-linear and suffers from magnitude saturation above $M_L \approx 6.0$.
   - **Resolution for Next Phase:** Migrate to the **ISC-GEM v10.0** catalogue for all events above $M_w 5.5$ (1904–2021+), which provides direct, uniformly inverted or calibrated moment magnitudes with documented standard errors ($\sigma_{Mw}$).

2. **Completeness Threshold ($M_c$) Spatiotemporal Non-Stationarity:**
   - The Himalayan collision zone has extreme topography and historic sparsity of seismic stations prior to 1995. Maximum-curvature estimation of $M_c$ shows that before 1990, the completeness threshold along the Himalayan arc was $M_c \approx 5.2–5.5$, dropping to $M_c \approx 4.0–4.5$ only after the deployment of the digital Nepal network (1994) and modern Indian broadband stations (1998–2005).
   - Any long-term statistical study spanning 1976–2026 must enforce an epoch-dependent or conservative uniform threshold ($M_w \ge 5.2$) to prevent artificial rate changes driven by network densification.

---

## 2. Aftershock Removal: Failure of Gardner-Knopoff in the Himalayas

1. **The 2015 Mw 7.3 Kodari Misclassification:**
   - The Gardner-Knopoff (1974) window method defines circular epicentral spatial windows. The 2015 Gorkha ($M_w 7.8$) rupture was a unilateral eastward unzipping of the Main Himalayan Thrust over ~140 km.
   - The 2015-05-12 $M_w 7.3$ Kodari aftershock nucleated at the eastern edge of the rupture. Because the Gardner-Knopoff distance window was evaluated from the initial hypocenter ($84.73^\circ\text{E}$), the Kodari shock ($86.07^\circ\text{E}$, $\sim 140\text{ km}$ away) fell just outside the classical radial cutoff and was falsely retained as an independent mainshock.
   - **Resolution:** Window declustering is mathematically obsolete for complex thrust faulting. The project must implement **stochastic declustering via space-time ETAS** (Zhuang, Ogata & Vere-Jones 2002) or the **nearest-neighbor proximity metric** (Zaliapin & Ben-Zion 2013) using fault-parallel anisotropic kernels.

---

## 3. Physical Baselines vs Positive Controls

1. **Tidal Triggering Scale Mismatch:**
   - Solid Earth body tides create shear stresses of order $\sim 1\text{–}3\text{ kPa}$, whereas tectonic stress drops during earthquakes are $1\text{–}10\text{ MPa}$ ($1,000\text{–}10,000\text{ kPa}$).
   - As documented by Cochran et al. (2004) and Ide et al. (2016), measurable tidal triggering occurs predominantly on shallow subduction thrust and normal faults subjected to **ocean tidal loading** ($\ge 10\text{–}20\text{ kPa}$).
   - The Himalayan arc is an intracontinental collision zone situated hundreds of kilometers inland from ocean loading. Solid Earth body tides alone produce negligible stress perturbations relative to tectonic loading rates, meaning the study's tidal positive control has negligible theoretical power to detect an effect in an inland continental thrust sequence.

2. **Planetary Gravitational Forces:**
   - The maximum gravitational tidal force exerted by any planet on Earth (Jupiter at closest perihelic opposition) is $\approx 10^{-5}$ times smaller than the lunar gravitational tide, and planetary stresses in the Earth's crust are $< 10^{-5}\text{ Pa}$.
   - No known physical mechanism (gravitational, electromagnetic, or solar wind perturbation) can induce crustal failure at planetary distances.

---

## 4. Textual Ambiguities in Classical Jyotish Literature

1. **Brihat Samhita Chapter 32 Mandala Classification:**
   - In verse 32.20 (Varuna mandala), certain Sanskrit recensions (e.g. printed editions consulted by Chidambaram Iyer 1884) mistakenly print *Uttarāṣāḍha* twice and omit *Uttarā Bhādrapadā*. However, Bhattotpala's commentary and scholarly recensions (M. Ramakrishna Bhat 1981) resolve this: each of the 28 nakshatras (including Abhijit) belongs to exactly one mandala. Abhijit belongs to the Indra mandala, and Uttara Bhadrapada belongs to the Varuna mandala.
   - When dropping Abhijit to map onto the standard 27-nakshatra equal division ($13^\circ 20'$ each), Indra mandala is left with 6 nakshatras ($80^\circ$ of arc), while Vayu, Agni, and Varuna mandalas retain 7 nakshatras ($93^\circ 20'$ of arc). This creates an unequal baseline exposure probability ($\approx 0.222$ vs $0.259$) that must be normalized in Poisson rate tests.

2. **Lead Time and Causality Direction in Samhita Texts:**
   - Modern astrologers cite Brihat Samhita Ch. 32 as an *ex-ante* triggering mechanism (e.g., "Moon in Varuna causes earthquakes").
   - However, the actual Sanskrit text of Varahamihira uses the mandala classification to diagnose the *portents and aftermath* (effects on kings, crops, rainfall, and diseases over the subsequent 6 months) *given* that an earthquake has already occurred! Applying the mandalas as a prospective causal alarm inverts the classical hermeneutic structure of *nimitta* (omen observation).

---

## 5. Ex-Ante Astrological Forecasts vs Scientific Verification

1. **The Specificity Deficit:**
   - Out of all documented modern predictions, almost all "successful" claims suffer from extreme parameter vagueness:
     * Wide spatial targets (e.g. "Asia", "Middle East", "Northern India", "China").
     * Broad temporal alarm windows (e.g., 30 to 180 days).
     * Missing or non-falsifiable magnitudes (e.g., "destructive earthquake" or "natural calamity").
   - Under standard Molchan error diagram analysis, an alarm window covering 30% to 50% of the year across active tectonic regions (where background seismicity produces multiple $M \ge 6$ events annually) inevitably captures events by sheer Poisson chance.
   - In accordance with CSEP standards, an astrological prediction can only be validated if the spatial polygon, magnitude lower bound, and tight temporal window are pre-registered with a fixed, unalterable hash before origin time.
