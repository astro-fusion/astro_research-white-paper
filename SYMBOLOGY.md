# 📐 SYMBOLOGY.md — Centralized Mathematical Symbol Dictionary

> **Authoritative reference for all mathematical variables and symbols** used across
> the astro_research-white-paper repository. Every white paper,
> source-code comment, and dataset schema MUST use the notation defined here.
>
> **Domain tags** — each symbol is marked with one or more domain tags:
> `[AS]` = Astrological / Celestial Mechanics | `[ST]` = General Statistics / Signal Processing

---

## Notation Conventions

Symbols are kept context-exclusive so that astrological and statistical notation never collide:

| Symbol | Astrological Meaning `[AS]` | Convention                                                   |
| ------ | --------------------------- | ------------------------------------------------------------ |
| `λ`    | Ecliptic longitude (°)      | Always written `λ_ecl`                                       |
| `α`    | Right Ascension             | Equatorial frame only                                        |
| `ω`    | Argument of perihelion (°)  | Written `ω_peri`                                             |

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
| TDD          | Test-Driven Development                                                     | Software Engineering |
| CI/CD        | Continuous Integration / Continuous Deployment                              | Software Engineering |
| HDF5         | Hierarchical Data Format v5                                                 | Data Science         |
| JPL          | Jet Propulsion Laboratory                                                   | `[AS]`               |
| DOE          | US Department of Energy                                                     | Institutional        |
| OOB          | Out-of-Bounds (declination)                                                 | `[AS]`               |
| SPF          | Secondary Progression Formula                                               | `[AS]`               |
| SAD          | Solar Arc Direction                                                         | `[AS]`               |

---

_This document is the single source of truth for mathematical notation in this repository.
All pull requests that introduce new symbols must update this file as part of the submission._
