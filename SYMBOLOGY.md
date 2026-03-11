# 📐 SYMBOLOGY.md — Centralized Mathematical Symbol Dictionary

> **Authoritative reference for all mathematical variables and symbols** used across
> the astro-fusion/astro_research-white-paper repository. Every white paper,
> source-code comment, and dataset schema MUST use the notation defined here.
>
> **Domain tags** — each symbol is marked with one or more domain tags:
> `[PH]` = Plasma Physics / Astro-fusion | `[AS]` = Astrological / Celestial Mechanics | `[ST]` = General Statistics / Signal Processing

---

## ⚠️ Symbol Collision Resolution

Several symbols carry conflicting meanings across disciplines represented in this
repository. The following table defines the **canonical, context-exclusive** usage
that resolves those collisions:

| Symbol | Physics Meaning `[PH]`      | Astrological Meaning `[AS]` | **Resolution**                                              |
| ------ | --------------------------- | --------------------------- | ----------------------------------------------------------- |
| `λ`    | Wavelength (optics, nm / Å) | Ecliptic longitude (°)      | Use `λ_wave` for wavelength; `λ_ecl` for ecliptic longitude |
| `ω`    | Angular frequency (rad s⁻¹) | Argument of perihelion (°)  | Use `ω_freq` vs `ω_peri`                                    |
| `ρ`    | Mass density (kg m⁻³)       | —                           | `ρ` reserved exclusively for plasma/particle density        |
| `T`    | Temperature (K or eV)       | —                           | `T_e` = electron temperature; `T_i` = ion temperature       |
| `n`    | Number density (m⁻³)        | —                           | `n_e` = electron number density                             |
| `R`    | Line intensity ratio        | Right Ascension             | Use `R_line` for line ratios; `α` for Right Ascension       |

---

## I. Plasma Physics & Astro-Fusion Symbols `[PH]`

### I.A — Particle & Plasma Parameters

| Symbol | LaTeX      | Unit        | Definition                                                                                       |
| ------ | ---------- | ----------- | ------------------------------------------------------------------------------------------------ |
| `n_e`  | `n_e`      | m⁻³         | Electron number density                                                                          |
| `T_e`  | `T_e`      | eV or K     | Electron temperature                                                                             |
| `T_i`  | `T_i`      | eV or K     | Ion temperature                                                                                  |
| `κ`    | `\kappa`   | —           | Kappa index; spectral index of suprathermal tail distribution. κ → ∞ recovers Maxwell-Boltzmann. |
| `f_κ`  | `f_\kappa` | m⁻³ (m/s)⁻³ | Relativistic Kappa velocity distribution function                                                |
| `v_th` | `v_{th}`   | m s⁻¹       | Thermal velocity `v_th = sqrt(2 k_B T / m)`                                                      |
| `m_e`  | `m_e`      | kg          | Electron rest mass                                                                               |
| `m_i`  | `m_i`      | kg          | Ion rest mass                                                                                    |
| `k_B`  | `k_B`      | J K⁻¹       | Boltzmann constant                                                                               |
| `c`    | `c`        | m s⁻¹       | Speed of light in vacuum                                                                         |
| `e`    | `e`        | C           | Elementary charge                                                                                |

### I.B — Spectroscopic Line Diagnostics

| Symbol    | LaTeX                | Unit       | Definition                                                                       |
| --------- | -------------------- | ---------- | -------------------------------------------------------------------------------- |
| `I_{ij}`  | `I_{ij}`             | W m⁻² sr⁻¹ | Intensity of spectral line from upper level `i` → lower level `j`                |
| `A_{ij}`  | `A_{ij}`             | s⁻¹        | Einstein A-coefficient (spontaneous emission probability) for transition `i → j` |
| `ΔE_{ij}` | `\Delta E_{ij}`      | J or eV    | Energy of the transition photon `i → j`                                          |
| `N_i`     | `N_i`                | m⁻³        | Population density of excited state `i`                                          |
| `λ_wave`  | `\lambda_{\rm wave}` | nm         | Wavelength of emitted photon (optical spectroscopy)                              |
| `R_line`  | `R_{\rm line}`       | —          | Dimensionless ratio of two spectral line intensities                             |
| `Q_{ij}`  | `Q_{ij}`             | m³ s⁻¹     | Collisional rate coefficient for transition `i → j`                              |

**Helium Line Ratio Formula:**

$$R_{\rm line}(T_e, n_e) = \frac{I_{\rm singlet}}{I_{\rm triplet}} = \frac{\lambda_{\rm wave,\,triplet}\,A_{\rm singlet}\,N_{\rm singlet}(T_e, n_e)}{\lambda_{\rm wave,\,singlet}\,A_{\rm triplet}\,N_{\rm triplet}(T_e, n_e)}$$

### I.C — Pellet Ablation & ELM Mitigation

| Symbol  | LaTeX               | Unit      | Definition                                                             |
| ------- | ------------------- | --------- | ---------------------------------------------------------------------- |
| `N_p`   | `N_p`               | particles | Total number of particles in the injected pellet                       |
| `ṁ_abl` | `\dot{m}_{\rm abl}` | kg s⁻¹    | Ablation rate of the solid cryogenic pellet                            |
| `n_cl`  | `n_{\rm cl}`        | m⁻³       | Number density of the pellet ablation cloud                            |
| `T_cl`  | `T_{\rm cl}`        | eV        | Temperature of the ablation cloud                                      |
| `v_p`   | `v_p`               | m s⁻¹     | Pellet injection velocity                                              |
| `r_p`   | `r_p`               | m         | Pellet radius                                                          |
| `S_c`   | `S_c`               | —         | Shielding factor (ratio of cloud density to background plasma density) |
| `Φ_ELM` | `\Phi_{\rm ELM}`    | J         | Energy released per ELM event                                          |

### I.D — Magnetic Reconnection

| Symbol  | LaTeX              | Unit  | Definition                                  |
| ------- | ------------------ | ----- | ------------------------------------------- |
| `B`     | `\mathbf{B}`       | T     | Magnetic field vector                       |
| `E`     | `\mathbf{E}`       | V m⁻¹ | Electric field vector                       |
| `η`     | `\eta`             | Ω·m   | Plasma resistivity                          |
| `v_A`   | `v_A`              | m s⁻¹ | Alfvén velocity                             |
| `δ_rec` | `\delta_{\rm rec}` | m     | Thickness of the reconnection current sheet |
| `W_rec` | `W_{\rm rec}`      | J     | Energy released per reconnection event      |
| `W_kin` | `W_{\rm kin}`      | J     | Kinetic energy component from reconnection  |
| `W_th`  | `W_{\rm th}`       | J     | Thermal energy component from reconnection  |

---

## II. Celestial Mechanics & Astrological Symbols `[AS]`

### II.A — Coordinate Systems

| Symbol   | LaTeX               | Unit        | Definition                                                      |
| -------- | ------------------- | ----------- | --------------------------------------------------------------- |
| `λ_ecl`  | `\lambda_{\rm ecl}` | ° (degrees) | Ecliptic longitude (0°–360°, measured from vernal equinox)      |
| `β`      | `\beta`             | °           | Celestial latitude (ecliptic frame; −90° to +90°)               |
| `α`      | `\alpha`            | ° or h:m:s  | Right Ascension (equatorial frame)                              |
| `δ_decl` | `\delta_{\rm decl}` | °           | Declination (equatorial frame; −90° to +90°)                    |
| `ε`      | `\varepsilon`       | °           | Obliquity of the ecliptic (~23.44°, secular variation included) |
| `r`      | `r`                 | AU          | Geocentric radial distance of celestial body                    |
| `φ_geo`  | `\varphi_{\rm geo}` | °           | Geographic latitude of observer                                 |
| `Λ_geo`  | `\Lambda_{\rm geo}` | °           | Geographic longitude of observer                                |

**Coordinate Transformation (Ecliptic → Equatorial):**

$$\sin(\delta_{\rm decl}) = \sin(\beta)\cos(\varepsilon) + \cos(\beta)\sin(\varepsilon)\sin(\lambda_{\rm ecl})$$

$$\cos(\alpha)\cos(\delta_{\rm decl}) = \cos(\beta)\cos(\lambda_{\rm ecl})$$

$$\sin(\alpha)\cos(\delta_{\rm decl}) = -\sin(\beta)\sin(\varepsilon) + \cos(\beta)\cos(\varepsilon)\sin(\lambda_{\rm ecl})$$

### II.B — Temporal Variables

| Symbol | LaTeX       | Unit             | Definition                                                            |
| ------ | ----------- | ---------------- | --------------------------------------------------------------------- |
| `t`    | `t`         | Julian Days (JD) | Continuous temporal coordinate (Barycentric Dynamical Time preferred) |
| `t_0`  | `t_0`       | JD               | Reference epoch (e.g., J2000.0 = JD 2451545.0)                        |
| `Δt`   | `\Delta t`  | days or years    | Time interval                                                         |
| `P`    | `P`         | days             | Orbital period of a celestial body                                    |
| `SA_σ` | `SA_\sigma` | °                | Solar Arc Direction: angular advancement per year ≈ 1°                |
| `SP_τ` | `SP_\tau`   | days → years     | Secondary Progression temporal compression ratio (1 day ≡ 1 year)     |

### II.C — Aspect Geometry

| Symbol   | LaTeX              | Unit | Definition                                                                   |
| -------- | ------------------ | ---- | ---------------------------------------------------------------------------- |
| `a_{ij}` | `a_{ij}`           | °    | Minimum angular separation (arc) between body `i` and body `j`               |
| `Δθ`     | `\Delta\theta`     | °    | Orb tolerance for aspect application/separation                              |
| `A`      | `\mathbf{A}`       | —    | Aspect adjacency matrix: element `a_{ij}` = minimum angular distance         |
| `G`      | `G=(V,E)`          | —    | Aspect network graph; V = planetary bodies; E = weighted angular separations |
| `θ_asp`  | `\theta_{\rm asp}` | °    | Canonical aspect angle (e.g., 60°, 90°, 120°, 180°)                          |

**Aspect Matrix Element:**

$$a_{ij} = \min\!\bigl(|\lambda_{\rm ecl,i} - \lambda_{\rm ecl,j}|,\; 360° - |\lambda_{\rm ecl,i} - \lambda_{\rm ecl,j}|\bigr)$$

### II.D — Retrogradation

| Symbol  | LaTeX                           | Unit  | Definition                                                                  |
| ------- | ------------------------------- | ----- | --------------------------------------------------------------------------- |
| `dλ/dt` | `\frac{d\lambda_{\rm ecl}}{dt}` | °/day | Instantaneous longitudinal velocity of a body                               |
| `t_R`   | `t_R`                           | JD    | Moment of station retrograde: `dλ/dt` transitions from positive to negative |
| `t_D`   | `t_D`                           | JD    | Moment of station direct: `dλ/dt` transitions from negative to positive     |

The body is defined **retrograde** when `dλ_ecl/dt < 0` and **direct** when `dλ_ecl/dt > 0`. At `t_R` and `t_D`, the velocity passes through zero (stationary point).

### II.E — House Systems

| Symbol   | LaTeX                | Unit | Definition                                                                |
| -------- | -------------------- | ---- | ------------------------------------------------------------------------- |
| `RAMC`   | `{\rm RAMC}`         | °    | Right Ascension of the Midheaven (MC)                                     |
| `ASC`    | `{\rm ASC}`          | °    | Ecliptic longitude of the Ascendant                                       |
| `MC`     | `{\rm MC}`           | °    | Ecliptic longitude of the Midheaven (Medium Coeli)                        |
| `DSA_k`  | `{\rm DSA}_k`        | °    | Diurnal Semi-Arc for house cusp `k` (Placidus/Koch)                       |
| `NSA_k`  | `{\rm NSA}_k`        | °    | Nocturnal Semi-Arc for house cusp `k`                                     |
| `φ_crit` | `\varphi_{\rm crit}` | °    | Critical polar latitude (~66.5°) beyond which temporal house systems fail |

### II.F — Dignity Scoring

| Symbol        | LaTeX                     | Unit              | Definition                                                        |
| ------------- | ------------------------- | ----------------- | ----------------------------------------------------------------- |
| `D(p, λ_ecl)` | `D(p, \lambda_{\rm ecl})` | integer [−4, +10] | Essential dignity score for planet `p` at longitude `λ_ecl`       |
| `w_r`         | `w_r`                     | integer           | Dignity weight for domicile/rulership (+5)                        |
| `w_ex`        | `w_{\rm ex}`              | integer           | Dignity weight for exaltation (+4); exact degree exaltation (+10) |
| `w_det`       | `w_{\rm det}`             | integer           | Dignity weight for detriment (−4)                                 |
| `w_fall`      | `w_{\rm fall}`            | integer           | Dignity weight for fall (−3)                                      |

### II.G — Out-of-Bounds Declination

| Symbol      | LaTeX              | Unit | Definition                                                                    |
| ----------- | ------------------ | ---- | ----------------------------------------------------------------------------- | ------ | ---- |
| `δ_OOB`     | `\delta_{\rm OOB}` | °    | Declination magnitude threshold for "Out-of-Bounds" classification: `         | δ_decl | > ε` |
| `PAR(i,j)`  | `{\rm PAR}(i,j)`   | —    | Boolean: parallel declination aspect between bodies `i` and `j` (`δ_i ≈ δ_j`) |
| `CPAR(i,j)` | `{\rm CPAR}(i,j)`  | —    | Boolean: contra-parallel declination (`δ_i ≈ −δ_j`)                           |

---

## III. General Statistics & Signal Processing `[ST]`

| Symbol | LaTeX        | Unit   | Definition                             |
| ------ | ------------ | ------ | -------------------------------------- |
| `μ`    | `\mu`        | varies | Population mean                        |
| `σ`    | `\sigma`     | varies | Population standard deviation          |
| `p`    | `p`          | [0,1]  | p-value (statistical significance)     |
| `r_s`  | `r_s`        | [−1,1] | Spearman rank correlation coefficient  |
| `H_0`  | `H_0`        | —      | Null hypothesis                        |
| `H_1`  | `H_1`        | —      | Alternative hypothesis                 |
| `PCA`  | `{\rm PCA}`  | —      | Principal Component Analysis           |
| `PC_k` | `{\rm PC}_k` | —      | `k`-th principal component             |
| `ξ_k`  | `\xi_k`      | —      | `k`-th eigenvalue in PCA decomposition |

---

## IV. Cross-Domain Abbreviation Glossary

| Abbreviation | Full Term                                                                   | Domain               |
| ------------ | --------------------------------------------------------------------------- | -------------------- |
| ELM          | Edge Localized Mode                                                         | `[PH]`               |
| CFQS         | Chinese First Quasi-axisymmetric Stellarator                                | `[PH]`               |
| TDD          | Test-Driven Development                                                     | Software Engineering |
| CI/CD        | Continuous Integration / Continuous Deployment                              | Software Engineering |
| HDF5         | Hierarchical Data Format v5                                                 | Data Science         |
| JPL          | Jet Propulsion Laboratory                                                   | `[AS]`               |
| WPT          | Wireless Power Transmission                                                 | `[PH]`               |
| SPS          | Space Solar Power System                                                    | `[PH]`               |
| IRCC-AFP     | International Research Collaboration Center for Astro-fusion Plasma Physics | `[PH]`               |
| DOE          | US Department of Energy                                                     | Institutional        |
| OOB          | Out-of-Bounds (declination)                                                 | `[AS]`               |
| SPF          | Secondary Progression Formula                                               | `[AS]`               |
| SAD          | Solar Arc Direction                                                         | `[AS]`               |

---

_This document is the single source of truth for mathematical notation in this repository.
All pull requests that introduce new symbols must update this file as part of the submission._
