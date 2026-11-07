# 🌌 White Paper 01: Celestial Mechanics and High-Precision Ephemeris Integration

## Foundational Coordinate Transforms for Computational Astrology

> **Repository path**: `papers/astrology/01_celestial_mechanics_and_ephemeris.md`
> **Symbol reference**: [SYMBOLOGY.md](../../SYMBOLOGY.md) — Section II.A–II.B
> **Code implementation**: [`src/celestial/ephemeris_engine.py`](../../src/celestial/ephemeris_engine.py)

---

## Abstract

The mathematical foundation of any rigorous computational astrological analysis is the precise localisation of celestial bodies in three-dimensional space relative to a specific terrestrial observer at an exact moment in Universal Time. This white paper documents the coordinate system transformations required to translate heliocentric equatorial positions (as delivered by the Swiss Ephemeris / JPL Horizons data pipeline) into the geocentric ecliptic frame that forms the standard basis of astrological computation. All equations are rendered with explicit symbol definitions conforming to [SYMBOLOGY.md §II](../../SYMBOLOGY.md) to prevent collision with the plasma physics symbol space.

---

## 1. Coordinate System Hierarchy

Astrological computation requires a chain of coordinate transformations:

```
Heliocentric Equatorial (JPL)
         │
         ▼   Parallax correction + Earth radius vector
Geocentric Equatorial (α, δ_decl)
         │
         ▼   Obliquity rotation ε
Geocentric Ecliptic (λ_ecl, β)
         │
         ▼   Ayanamsa subtraction (for Vedic / sidereal systems)
Sidereal Ecliptic (λ_sid = λ_ecl − ψ_ayanamsa)
```

---

## 2. Primary Coordinate Transformations

### 2.1 Ecliptic → Equatorial Transformation

Let:

- $\lambda_{\rm ecl}$ = ecliptic longitude of the celestial body (°)
- $\beta$ = celestial latitude in the ecliptic frame (°)
- $\varepsilon$ = obliquity of the ecliptic (currently $\approx 23.4393°$, secularly decreasing)

The equatorial coordinates (right ascension $\alpha$, declination $\delta_{\rm decl}$) are computed by:

$$\boxed{\sin(\delta_{\rm decl}) = \sin(\beta)\cos(\varepsilon) + \cos(\beta)\sin(\varepsilon)\sin(\lambda_{\rm ecl})}$$

$$\boxed{\cos(\alpha)\cos(\delta_{\rm decl}) = \cos(\beta)\cos(\lambda_{\rm ecl})}$$

$$\boxed{\sin(\alpha)\cos(\delta_{\rm decl}) = -\sin(\beta)\sin(\varepsilon) + \cos(\beta)\cos(\varepsilon)\sin(\lambda_{\rm ecl})}$$

The right ascension $\alpha$ is resolved to the correct quadrant using the two-argument arctangent `atan2(sin_α, cos_α)`.

### 2.2 Obliquity of the Ecliptic

The mean obliquity $\varepsilon$ varies secularly due to gravitational perturbations. The IAU 2006 series (valid to 2025 at sub-arcsecond precision, with higher-order terms for longer spans):

$$\varepsilon = 23°\,26'\,21.448'' - 4680.93''\,T - 1.55''\,T^2 + 1999.25''\,T^3 - \ldots$$

where $T = ({\rm JD} - 2451545.0) / 36525$ is the Julian century from J2000.0.

The `pyswisseph` library computes the IAU-series obliquity internally; the above is provided for documentation and independent verification.

### 2.3 Ayanamsa (Tropical → Sidereal Conversion)

For Vedic / sidereal astrological analysis, the tropical ecliptic longitude is converted to the sidereal frame:

$$\lambda_{\rm sid} = \lambda_{\rm ecl} - \psi_{\rm ayanamsa}(t)$$

where $\psi_{\rm ayanamsa}(t)$ is the accumulated ayanamsa at epoch $t$. For the Lahiri (Chitrapaksha) ayanamsa:

$$\psi_{\rm Lahiri}(t) \approx \psi_0 + 50.3''\,T_{\rm Julian\,year}$$

with $\psi_0 \approx 0°$ at ~285 CE.

---

## 3. Temporal Framework

### 3.1 Julian Day Number

All internal time computations use **Julian Days (JD)**, a continuous count of solar days since epoch −4712-01-01 12:00 UT.

Reference values:

- J2000.0 = JD 2451545.0 (2000 January 1, 12:00 TT)
- Unix epoch = JD 2440587.5 (1970 January 1, 00:00 UTC)

### 3.2 Timescale Conversion

| Timescale                  | Abbreviation | Usage                                        |
| -------------------------- | ------------ | -------------------------------------------- |
| Universal Time             | UT1          | Observer wall-clock time                     |
| Coordinated Universal Time | UTC          | Civil time; differs from UT1 by leap seconds |
| Terrestrial Time           | TT           | Planetary ephemeris integration              |
| Barycentric Dynamical Time | TDB          | Solar System barycentric integration         |

Swiss Ephemeris inputs are in **TT** (or equivalently ET/TDT). The library internally applies $\Delta T = TT - UT1$ corrections.

---

## 4. Planetary Body Catalogue

Bodies computed and stored in `data/ephemeris/jpl_horizons_planets_2000_2100.parquet`:

| ID  | Body                       | Symbol | Notes                                                      |
| --- | -------------------------- | ------ | ---------------------------------------------------------- |
| 0   | Sun                        | ☉      | Geometric centre (not mass centre for high-precision work) |
| 1   | Moon                       | ☽      | Geocentric; requires separate high-precision lunar theory  |
| 2   | Mercury                    | ☿      |                                                            |
| 3   | Venus                      | ♀      |                                                            |
| 4   | Mars                       | ♂      |                                                            |
| 5   | Jupiter                    | ♃      |                                                            |
| 6   | Saturn                     | ♄      |                                                            |
| 7   | Uranus                     | ♅      |                                                            |
| 8   | Neptune                    | ♆      |                                                            |
| 9   | Pluto                      | ♇      | Dwarf planet; included for astrological completeness       |
| 10  | Mean lunar ascending node  | ☊      | Rahu (Vedic)                                               |
| 11  | Mean lunar descending node | ☋      | Ketu (Vedic)                                               |

---

## 5. Precision Standards and Validation

| Parameter                 | Precision Target      | Method                               |
| ------------------------- | --------------------- | ------------------------------------ |
| Planet ecliptic longitude | Sub-arcsecond (< 1'') | Swiss Ephemeris, pyswisseph          |
| Lunar longitude           | Sub-arcsecond         | Swiss Ephemeris ELP 2000/82          |
| Ayanamsa                  | 0.001°                | SEFLG_SIDEREAL + SE_SIDM_LAHIRI flag |
| Obliquity                 | 0.0001°               | IAU 2006 series                      |
| ΔT                        | < 1 second            | Built-in Morrison & Stephenson model |

---

## 6. Implementation Reference

```python
# src/celestial/ephemeris_engine.py  (simplified excerpt)
import swisseph as swe
import numpy as np
from dataclasses import dataclass

@dataclass
class CelestialPosition:
    body_id: int
    jd_tt:   float          # Julian Day in Terrestrial Time
    lambda_ecl: float       # Ecliptic longitude (tropical), degrees
    beta:       float       # Celestial latitude, degrees
    r:          float       # Geocentric distance, AU
    lambda_sid: float       # Sidereal (Lahiri) ecliptic longitude, degrees
    delta_decl: float       # Declination, degrees
    alpha_ra:   float       # Right Ascension, degrees

def compute_position(body_id: int, jd_tt: float) -> CelestialPosition:
    """Compute geocentric ecliptic and equatorial position via Swiss Ephemeris."""
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    flags = swe.FLG_SWIEPH | swe.FLG_SPEED
    result, _ = swe.calc_ut(jd_tt, body_id, flags | swe.FLG_SIDEREAL)
    tropical_result, _ = swe.calc_ut(jd_tt, body_id, flags)

    return CelestialPosition(
        body_id=body_id,
        jd_tt=jd_tt,
        lambda_ecl=tropical_result[0],
        beta=tropical_result[1],
        r=tropical_result[2],
        lambda_sid=result[0],
        delta_decl=0.0,   # Computed via transformation equations above
        alpha_ra=0.0,
    )
```

---

_Symbol cross-reference: All symbols conform to [SYMBOLOGY.md §II.A–II.B](../../SYMBOLOGY.md). The symbol $\lambda$ in this paper **exclusively** refers to `λ_ecl` (ecliptic longitude); never to optical wavelength._
