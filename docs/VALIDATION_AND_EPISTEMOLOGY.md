# 🔬 Validation and Epistemology

> **Purpose**: Document all mathematical model assumptions, random number generation
> seeds, and numerical boundary conditions used across the astrology,
> numerology and correlation white papers. This file is a mandatory prerequisite for reproducibility.

---

## 1. Scope and Intent

Scientific papers in this repository make claims that rest on computational models.
Those models contain:

1. **Explicit assumptions** — mathematical approximations or astrological conventions
   accepted as axioms.
2. **Configurable parameters** — boundary conditions or seed values that must be
   fixed for exact reproduction.
3. **Known limitations** — conditions under which a model breaks down.

All three categories are codified here.

---

## 2. Astrological/Celestial Mechanics Models

### 2.1 Ephemeris Engine

| Parameter         | Value                                              | Justification                                           |
| ----------------- | -------------------------------------------------- | ------------------------------------------------------- |
| Ephemeris library | Swiss Ephemeris (pyswisseph)                       | Sub-arcsecond precision; IAU SOFA compliant             |
| Ayanamsa          | Lahiri (Chitrapaksha)                              | Official Indian standard; most used in Jyotish research |
| Coordinate frame  | Geocentric ecliptic of date                        | Standard for natal chart computation                    |
| Delta-T model     | `pyswisseph` internal (Morrison & Stephenson 2004) | Valid from −2000 to +3000 CE                            |
| Valid date range  | 2000 BCE – 3000 CE                                 | Beyond this, use historical approximations only         |

### 2.2 House System Singularity Thresholds

The Placidus and Koch house systems break down at geographic latitudes approaching
the polar circles. The following thresholds are **hard-coded** in
`libs/vedic_astrology_core/astrology/chart.py`
(`resolve_house_system_for_latitude`):

```python
PLACIDUS_HIGH_DISTORTION_LAT = 60.0   # degrees N/S: warning, cusps compressed
POLAR_SINGULARITY_LAT        = 66.5   # degrees N/S: quadrant systems fall back
DEFAULT_HOUSE_SYSTEM         = "W"    # whole sign: the default and the fallback
```

### 2.3 Retrograde Detection Tolerance

The instantaneous velocity `dλ_ecl/dt` near a stationary point is numerically
near-zero and susceptible to floating-point noise. A **3-day centred finite
difference** is used as the default detection window:

$$\frac{d\lambda_{\rm ecl}}{dt}\bigg|_t \approx \frac{\lambda_{\rm ecl}(t+\Delta) - \lambda_{\rm ecl}(t-\Delta)}{2\,\Delta}, \quad \Delta = 1.5\,\text{days}$$

---

## 3. Numerical Precision Standards

| Domain                | Standard                                              | Notes                                       |
| --------------------- | ----------------------------------------------------- | ------------------------------------------- |
| Planetary positions   | 64-bit IEEE 754 double                                | Never use 32-bit float for longitude        |
| Aspect orbs           | Rounded to 4 decimal places (°)                       | Prevents false positive aspect detections   |

---

## 4. Known Model Limitations

| Model                  | Limitation                                              | Mitigation                                       |
| ---------------------- | ------------------------------------------------------- | ------------------------------------------------ |
| Swiss Ephemeris        | Limited accuracy before 2000 BCE                        | Document as "historical approximation"           |
| Placidus houses        | Singularity above polar circles                         | Automatic whole-sign fallback                    |
| Secondary progessions  | 1 day = 1 year approximation                            | Introduce sidereal year correction for precision |

---

_Update this document whenever model parameters or seeds change. Include the change in
`CHANGELOG.md` with the semantic version that introduced the modification._
