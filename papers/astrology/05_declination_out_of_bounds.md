# 🌐 White Paper 05: Declination Analysis and Out-of-Bounds Logic

## Multi-Dimensional Celestial Geometry Beyond Ecliptic Longitude

> **Symbol reference**: [SYMBOLOGY.md §II.G](../../SYMBOLOGY.md)
> **Code**: [`src/celestial/aspect_matrix.py`](../../src/celestial/aspect_matrix.py) (parallel / contra-parallel detection)

---

## Abstract

Standard computational astrology operates primarily on the one-dimensional ecliptic longitude plane. This restriction neglects a critical second dimension of celestial geometry: **equatorial declination** ($\delta_{\rm decl}$). This white paper establishes the mathematical framework for three advanced declination-based analytical modules: (1) detection of **Out-of-Bounds** (OOB) celestial bodies whose declination exceeds the obliquity envelope, (2) computation of **parallel** (same-sign) and **contra-parallel** (opposite-sign) declination aspects, and (3) integration of declination data into the full multi-dimensional aspect adjacency matrix.

---

## 1. Declination in the Celestial Coordinate Frame

### 1.1 Definition

Declination $\delta_{\rm decl}$ is the angular distance of a celestial body north (+) or south (−) of the celestial equator, measured in the equatorial coordinate system. It is obtained from the ecliptic coordinates $(\lambda_{\rm ecl}, \beta)$ via the transformation (fully derived in Paper 01):

$$\sin(\delta_{\rm decl}) = \sin(\beta)\cos(\varepsilon) + \cos(\beta)\sin(\varepsilon)\sin(\lambda_{\rm ecl})$$

### 1.2 The Obliquity Envelope

The obliquity of the ecliptic $\varepsilon \approx 23.44°$ defines the **maximum possible declination** for any ecliptic-plane body ($\beta = 0$):

$$|\delta_{\rm decl}|_{\rm max} = \varepsilon \approx 23.44°$$

- The Sun's declination oscillates between $-\varepsilon$ and $+\varepsilon$ over the tropical year.
- The Moon has an orbital inclination of ~5.1° to the ecliptic, so its maximum declination can reach $23.44° + 5.1° = 28.5°$.
- True planets have varying orbital inclinations (see table below).

---

## 2. Out-of-Bounds (OOB) Detection

### 2.1 Definition

A celestial body is classified **Out-of-Bounds** when its absolute declination exceeds the current obliquity threshold:

$$|\delta_{\rm decl}| > \varepsilon(t)$$

where $\varepsilon(t)$ is the time-varying obliquity (secularly decreasing; see Paper 01 §2.2).

### 2.2 Physical Significance

OOB bodies are beyond the Sun's annual declination range. In the geocentric observer's sky, an OOB body rises and sets at extremes not achieved by the Sun at any time of year. Astrological traditions treat this as a state of exaggerated, unconstrained expression of the body's significations.

### 2.3 Planetary OOB Ranges

| Body    | Max Ecliptic Latitude β | Max Possible | δ_decl           |     | OOB Frequency |
| ------- | ----------------------- | ------------ | ---------------- | --- | ------------- |
| Sun     | 0° (by definition)      | ~23.44°      | Never            |
| Moon    | ±5.1°                   | ~28.5°       | ~24% of the time |
| Mercury | ±7.0°                   | ~27.8°       | Frequently       |
| Venus   | ±3.4°                   | ~26.4°       | Occasionally     |
| Mars    | ±1.9°                   | ~25.2°       | Rarely           |
| Jupiter | ±1.3°                   | ~24.6°       | Very rarely      |
| Saturn  | ±2.5°                   | ~25.6°       | Rarely           |

### 2.4 Implementation

```python
# src/celestial/aspect_matrix.py — OOB detection extension

import numpy as np

def detect_out_of_bounds(
    declinations_deg: np.ndarray,   # shape (n_bodies,) or (T, n_bodies)
    obliquity_deg: float | np.ndarray = 23.4393,
) -> np.ndarray:
    """
    Boolean mask: True where |δ_decl| > ε (Out-of-Bounds condition).

    Parameters
    ----------
    declinations_deg : np.ndarray
        Declination values in degrees. Can be 1-D (single epoch) or
        2-D (T × n_bodies for time-series).
    obliquity_deg : float or np.ndarray
        Obliquity threshold. Pass an array of shape (T,) for time-varying ε.

    Returns
    -------
    oob_mask : np.ndarray (bool)
        Same shape as input; True = OOB.
    """
    return np.abs(declinations_deg) > obliquity_deg
```

---

## 3. Parallel and Contra-Parallel Aspects

### 3.1 Definitions

**Parallel declination**: Two bodies share approximately equal declinations on the same hemisphere:

$${\rm PAR}(i,j): \quad |\delta_{{\rm decl},i} - \delta_{{\rm decl},j}| \leq \Delta\theta_{\rm par}$$

**Contra-parallel declination**: Two bodies are at equal declinations on opposite hemispheres:

$${\rm CPAR}(i,j): \quad |\delta_{{\rm decl},i} + \delta_{{\rm decl},j}| \leq \Delta\theta_{\rm cpar}$$

Default orb for both: $\Delta\theta = 1.0°$ (much tighter than longitudinal aspect orbs because declination changes slowly).

### 3.2 Astronomical Interpretation

- Parallel is considered analogous in effect to a **conjunction**
- Contra-parallel is considered analogous in effect to an **opposition**

These are often **invisible** in standard longitude-based chart analysis — their inclusion is a major competitive advantage of this repository's analytical engine.

### 3.3 Full 2-D Aspect Matrix Extension

The complete extended aspect matrix combines longitude-based arcs (from Paper 03) with declination-based parallels:

```python
def compute_parallel_matrix(
    declinations_deg: np.ndarray,   # shape (n_bodies,)
    par_orb: float = 1.0,
    cpar_orb: float = 1.0,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Returns (parallel_mask, contra_parallel_mask), both shape (n, n) boolean.
    """
    n = len(declinations_deg)
    decl_diff = decl = declinations_deg

    # Parallel: |δi - δj| <= orb
    diff_matrix = np.abs(decl[:, None] - decl[None, :])
    parallel_mask = diff_matrix <= par_orb
    np.fill_diagonal(parallel_mask, False)

    # Contra-parallel: |δi + δj| <= orb (same magnitude, opposite sign)
    sum_matrix = np.abs(decl[:, None] + decl[None, :])
    cpar_mask = sum_matrix <= cpar_orb
    np.fill_diagonal(cpar_mask, False)

    return parallel_mask, cpar_mask
```

---

## 4. Validation Test Cases

| Scenario                        | δ_Sun   | δ_Moon  | Expected Result |
| ------------------------------- | ------- | ------- | --------------- | ---- | ------- |
| Summer solstice (Sun at max +ε) | +23.44° | +23.44° | PAR = True (`   | 0.0° | ` ≤ 1°) |
| Moon OOB north                  | —       | +28.1°  | OOB = True      |
| Sun–Moon contra-parallel        | +20.0°  | -20.0°  | CPAR = True (`  | 0.0° | ` ≤ 1°) |
| Moon at equator crossing        | —       | 0.0°    | OOB = False     |

---

_Symbol cross-reference: [SYMBOLOGY.md §II.G](../../SYMBOLOGY.md). OOB data stored in ephemeris Parquet files under column `is_oob` (bool)._
