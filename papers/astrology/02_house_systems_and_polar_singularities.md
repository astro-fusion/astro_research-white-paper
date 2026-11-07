# 🌐 White Paper 02: Astrological House Systems and Polar Singularity Handling

## Topological Failure Modes and Algorithmic Fallback Architecture

> **Symbol reference**: [SYMBOLOGY.md §II.E](../../SYMBOLOGY.md)
> **Code**: [`src/celestial/house_systems.py`](../../src/celestial/house_systems.py)
> **Validation**: [docs/VALIDATION_AND_EPISTEMOLOGY.md §3.2](../../docs/VALIDATION_AND_EPISTEMOLOGY.md)

---

## Abstract

Quadrant-based astrological house systems—most prominently Placidus, Koch, Regiomontanus, and Campanus—divide the celestial sphere by trisecting the local diurnal and nocturnal semi-arcs of the degree of the ecliptic in question. At geographic latitudes approaching the polar circles ($|\varphi_{\rm geo}| \geq 66.5°$), certain degrees of the ecliptic become **circumpolar** and never rise or set, causing a mathematical singularity in the semi-arc equations. This white paper documents the exact topological failure mechanism, provides the full calculus of temporal semi-arcs, and specifies the programmatic routing matrix that eliminates runtime exceptions through deterministic, geographically-aware fallback.

---

## 1. Mathematical Foundations: The Placidus Semi-Arc System

The Placidus system divides each hemisphere into three unequal sectors by trisecting the Diurnal Semi-Arc (DSA) and Nocturnal Semi-Arc (NSA) of each ecliptic degree.

### 1.1 Diurnal Semi-Arc

The DSA for an ecliptic degree at longitude $\lambda_{\rm ecl}$ and latitude $\beta$ is defined as the arc (in units of right ascension, i.e., degrees of time) from rising to the meridian:

$${\rm DSA}(\lambda_{\rm ecl}, \varphi_{\rm geo}) = 90° + \arcsin\!\bigl(\tan(\delta_{\rm decl})\,\tan(\varphi_{\rm geo})\bigr)$$

where $\delta_{\rm decl}$ is the declination of the ecliptic point $\lambda_{\rm ecl}$ (computed via the coordinate transforms in Paper 01).

The NSA is the complement:

$${\rm NSA}(\lambda_{\rm ecl}, \varphi_{\rm geo}) = 180° - {\rm DSA}(\lambda_{\rm ecl}, \varphi_{\rm geo})$$

### 1.2 House Cusps via Semi-Arc Trisection

House cusps 11, 12 (above horizon) and 2, 3 (below horizon) are located by trisecting the appropriate semi-arc:

$${\rm House\ 11\ cusp:} \quad {\rm RAMC} + \frac{{\rm DSA}}{3}$$
$${\rm House\ 12\ cusp:} \quad {\rm RAMC} + \frac{2\,\cdot\,{\rm DSA}}{3}$$

The Ascendant (House 1 cusp) occurs at the intersection of the ecliptic with the local horizon.

### 1.3 The Polar Singularity

The formula for DSA contains the factor $\tan(\delta_{\rm decl})\,\tan(\varphi_{\rm geo})$.

**Singularity condition**: When:

$$\bigl|\tan(\delta_{\rm decl})\,\tan(\varphi_{\rm geo})\bigr| \geq 1$$

the argument of $\arcsin$ exceeds ±1, and the function is undefined. Geometrically, this occurs when the ecliptic degree never crosses the local horizon—it is **circumpolar**.

This condition is met when $|\varphi_{\rm geo}|$ approaches $90° - |\delta_{\rm decl}|$, which at maximum declination $|\delta_{\rm decl}| = \varepsilon \approx 23.44°$ means:

$$\varphi_{\rm crit} = 90° - 23.44° = 66.56°$$

Above this critical latitude, **some ecliptic degrees have no rising or setting point**, and the Placidus (and similarly Koch, Regiomontanus, Campanus) house systems cannot be computed for charts with Ascendants in those sign ranges.

---

## 2. Programmatic Routing Decision Matrix

To prevent runtime arithmetic exceptions (`ValueError: math domain error`) and ensure the system handles all terrestrial birth locations gracefully, the following routing logic is mandatory:

| Geographic Latitude $ | \varphi\_{\rm geo}                                                      | $                                           | Primary Algorithm                                                     | Fallback | Mathematical Justification |
| --------------------- | ----------------------------------------------------------------------- | ------------------------------------------- | --------------------------------------------------------------------- | -------- | -------------------------- |
| $< 60°$               | Placidus (or user-selected: Koch, Regiomontanus, Campanus, Topocentric) | None required                               | Semi-arc equations operate fully within defined domain                |
| $60° - 66.5°$         | Placidus with high-distortion warning                                   | Porphyry or Equal House (user-configurable) | Extreme compression of intercepted signs may produce degenerate cusps |
| $> 66.5°$             | **Algorithm fails — singularity detected**                              | Whole Sign or Equal House from MC           | Circumpolar ecliptic degrees make semi-arc trisection undefined       |

### 2.1 Implementation

```python
# src/celestial/house_systems.py
from enum import Enum
import numpy as np
import swisseph as swe

PLACIDUS_HIGH_DISTORTION_LAT = 60.0   # degrees
PLACIDUS_SINGULARITY_LAT     = 66.5   # degrees

class HouseSystem(Enum):
    PLACIDUS      = b'P'
    KOCH          = b'K'
    REGIOMONTANUS = b'R'
    CAMPANUS      = b'C'
    TOPOCENTRIC   = b'T'
    PORPHYRY      = b'O'
    EQUAL         = b'E'
    WHOLE_SIGN    = b'W'

def resolve_house_system(
    geographic_lat: float,
    requested_system: HouseSystem = HouseSystem.PLACIDUS,
    fallback_system: HouseSystem = HouseSystem.WHOLE_SIGN,
) -> tuple[HouseSystem, str | None]:
    """
    Return the appropriate house system given geographic latitude.
    Returns (resolved_system, warning_message | None).
    """
    abs_lat = abs(geographic_lat)

    if abs_lat >= PLACIDUS_SINGULARITY_LAT:
        warning = (
            f"Geographic latitude {geographic_lat:.2f}° exceeds polar singularity "
            f"threshold ({PLACIDUS_SINGULARITY_LAT}°). "
            f"Falling back to {fallback_system.name}."
        )
        return fallback_system, warning

    if abs_lat >= PLACIDUS_HIGH_DISTORTION_LAT and requested_system in (
        HouseSystem.PLACIDUS, HouseSystem.KOCH
    ):
        warning = (
            f"Geographic latitude {geographic_lat:.2f}° is in the high-distortion "
            f"zone ({PLACIDUS_HIGH_DISTORTION_LAT}°–{PLACIDUS_SINGULARITY_LAT}°). "
            f"House cusps may be severely compressed."
        )
        return requested_system, warning

    return requested_system, None
```

---

## 3. Major House System Comparison

| House System         | Division Principle                  | Polar Safe?      | Preferred Use Case                        |
| -------------------- | ----------------------------------- | ---------------- | ----------------------------------------- |
| Whole Sign           | Each zodiac sign = one house        | ✅ Yes           | Vedic Jyotish; high-latitude births       |
| Equal House from ASC | Equal 30° arcs from Ascendant       | ✅ Yes           | Simple, modern Western                    |
| Equal House from MC  | Equal 30° arcs from Midheaven       | ✅ Yes           | Polar fallback default in this repository |
| Porphyry             | Trisects the four quadrants equally | ✅ Yes           | Intermediate fallback                     |
| Placidus             | Temporal semi-arc trisection        | ❌ Fails > 66.5° | Most common in Western tropical astrology |
| Koch                 | Birth place / oblique ascension     | ❌ Fails > 66°   | Western alternative to Placidus           |
| Regiomontanus        | Equator trisection                  | ⚠️ Partial       | Medieval / horary astrology               |
| Campanus             | Prime vertical trisection           | ⚠️ Partial       | Cosmobiological research                  |
| Topocentric          | Observer-centric; approx. Placidus  | ❌ Fails > 66.5° | Vedic Western hybrid research             |

---

## 4. Intercepted Signs: High-Distortion Zone

Between $60°$ and $66.5°$, Placidus houses may produce **intercepted signs**: one or more zodiac signs that are contained entirely within a single house, with their opposite signs straddling two house cusps. This creates analytical asymmetries:

- Some houses will span more than 30° of ecliptic longitude
- The intercepted sign contains no house cusp
- Statistical analysis of house-based event distributions must correct for this distortion

**Correction**: Normalize house-event frequencies by the angular width of each house in ecliptic degrees before computing any statistical correlations.

---

_See also [docs/EDGE_CASES.md §6.1](../../docs/EDGE_CASES.md) for the implementation-level edge case documentation. Symbol cross-reference: [SYMBOLOGY.md §II.E](../../SYMBOLOGY.md)._
