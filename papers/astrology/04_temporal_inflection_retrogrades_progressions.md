# ⏱️ White Paper 04: Temporal Inflection Points — Retrogradation and Progressions

## Derivative Calculus for Non-Linear Temporal Astrological Dynamics

> **Symbol reference**: [SYMBOLOGY.md §II.D, II.B](../../SYMBOLOGY.md)
> **Code**: [`src/celestial/retrograde_detector.py`](../../src/celestial/retrograde_detector.py)

---

## Abstract

The most computationally complex temporal phenomena in computational astrology arise not from position calculation but from the detection of **inflection points**—moments where the direction or rate of a celestial body's apparent motion undergoes a qualitative change. Retrograde stations, direct stations, and the temporal compression of predictive systems (Secondary Progressions, Solar Arc Directions) all require calculus-based treatment of the longitudinal velocity function $d\lambda_{\rm ecl}/dt$. This white paper provides the exact numerical differentiation strategies, temporal scanning algorithms, and progression formula derivations required for exhaustive, precise implementation.

---

## 1. Retrogradation: Longitudinal Velocity Analysis

### 1.1 Physical Mechanism

Retrograde motion is an apparent effect arising from the differential angular velocities of Earth and another planet. As an outer planet's orbital speed falls behind Earth's in its synodic cycle, the planet appears to reverse direction relative to the fixed background stars.

From a geocentric computational perspective, retrograde is simply the condition:

$$\frac{d\lambda_{\rm ecl}}{dt} < 0$$

Direct motion is $\frac{d\lambda_{\rm ecl}}{dt} > 0$. The stationary points (station retrograde $t_R$ and station direct $t_D$) satisfy:

$$\frac{d\lambda_{\rm ecl}}{dt}\bigg|_{t=t_R} = 0 \quad \text{(transition: direct → retrograde)}$$
$$\frac{d\lambda_{\rm ecl}}{dt}\bigg|_{t=t_D} = 0 \quad \text{(transition: retrograde → direct)}$$

### 1.2 Numerical Differentiation

A centred finite difference with step $\Delta = 1.5$ days provides robust velocity estimates:

$$\frac{d\lambda_{\rm ecl}}{dt}\bigg|_t \approx \frac{\lambda_{\rm ecl}(t + \Delta) - \lambda_{\rm ecl}(t - \Delta)}{2\Delta}$$

The 3-day window size is chosen to suppress ephemeris floating-point noise while remaining smaller than the shortest retrograde station duration (~3 days for Mercury at closest approach).

**Sign convention**: The daily angular increment for a direct planet is always positive ( $d\lambda_{\rm ecl}/dt > 0$ ); for a retrograde planet it is negative. Note that longitude wraps modulo 360°, so the difference must be short-arc corrected:

```python
def short_arc_diff(lambda_a: float, lambda_b: float) -> float:
    """Return signed short-arc difference lambda_a - lambda_b."""
    diff = lambda_a - lambda_b
    if diff > 180.0:
        diff -= 360.0
    elif diff < -180.0:
        diff += 360.0
    return diff
```

### 1.3 Station Detection Algorithm

```python
# src/celestial/retrograde_detector.py
import numpy as np
import swisseph as swe
from dataclasses import dataclass

@dataclass
class Station:
    body_id:    int
    jd_tt:      float         # Julian Day of station
    station_type: str         # "retrograde" or "direct"
    lambda_ecl: float         # Ecliptic longitude at station

def scan_retrograde_stations(
    body_id: int,
    jd_start: float,
    jd_end: float,
    step_days: float = 1.0,
    delta_days: float = 1.5,
) -> list[Station]:
    """
    Scan for all retrograde/direct station points of `body_id`
    in the time range [jd_start, jd_end].
    """
    jd_range = np.arange(jd_start, jd_end, step_days)

    lons = np.array([
        swe.calc_ut(jd, body_id, swe.FLG_SWIEPH)[0][0]
        for jd in jd_range
    ])

    # Centred finite difference velocity (deg/day)
    velocities = np.gradient(lons, step_days)  # handles boundary with forward/backward diff

    # Find sign changes in velocity
    stations: list[Station] = []
    for i in range(1, len(velocities) - 1):
        v_prev, v_curr = velocities[i-1], velocities[i]
        if v_prev > 0 and v_curr <= 0:
            stations.append(Station(body_id, jd_range[i], "retrograde", lons[i]))
        elif v_prev <= 0 and v_curr > 0:
            stations.append(Station(body_id, jd_range[i], "direct", lons[i]))

    return stations
```

---

## 2. Secondary Progressions

Secondary Progressions (SP) apply a strict **temporal metaphor**: one solar day after birth equals one tropical year of life.

### 2.1 Formula

For a natal epoch $t_0$ (in Julian Days), the **progressed chart** for age $\Delta t$ years uses planetary positions at:

$$t_{\rm prog} = t_0 + \Delta t \text{ days}$$

That is, the progressed chart for age 35 years uses the planetary positions 35 days after birth.

The progressed longitude of body $k$ at age $\Delta t$ is:

$$\lambda_{\rm prog,k}(\Delta t) = \lambda_{\rm ecl,k}(t_0 + \Delta t)$$

All subsequent natal-to-progressed aspect analysis uses $\mathbf{A}$ between $\boldsymbol{\lambda}_{\rm natal}$ and $\boldsymbol{\lambda}_{\rm prog}$.

### 2.2 Progressed Lunation Cycle

A particularly important SP event is the **Progressed New Moon** (SP Moon conjunct SP Sun, $a_{\rm Moon,Sun} \leq \Delta\theta$). The Progressed Moon moves ~1°/month in real time (≈ 13°/year in natal time), completing a full progressed lunation cycle in ~27.32 progressed years (~29.5 days in real time).

---

## 3. Solar Arc Directions

Solar Arc Directions advance **all planets by the same arc** equal to the Sun's daily motion (~1° per day ≡ ~1° per year of life).

$$\lambda_{\rm SAD,k}(\Delta t) = \lambda_{\rm ecl,k}(t_0) + SA_\sigma \cdot \Delta t$$

where $SA_\sigma = \lambda_{\rm ecl,\odot}(t_0 + \Delta t) - \lambda_{\rm ecl,\odot}(t_0)$ is the solar arc.

The key difference from SP:

- **SP**: each planet moves at its own rate (Moon advances fastest, outer planets nearly stationary)
- **SAD**: all planets move at the solar rate simultaneously; structure of natal chart is preserved, shifted uniformly

---

## 4. Out-of-Station Refinement (Bisection)

Once a station is detected at day-resolution, a **bisection refinement** achieves sub-minute accuracy:

```python
def refine_station_jd(
    body_id: int,
    jd_bracket_low: float,
    jd_bracket_high: float,
    tolerance_days: float = 1e-6,   # ≈ 0.1 seconds
) -> float:
    """Binary search for the zero-crossing of dλ/dt."""
    def velocity_at(jd: float) -> float:
        delta = 0.05   # 1.2-hour offset for finite diff
        l_plus, _ = swe.calc_ut(jd + delta, body_id, swe.FLG_SWIEPH)
        l_minus, _ = swe.calc_ut(jd - delta, body_id, swe.FLG_SWIEPH)
        return short_arc_diff(l_plus[0], l_minus[0]) / (2 * delta)

    lo, hi = jd_bracket_low, jd_bracket_high
    while (hi - lo) > tolerance_days:
        mid = (lo + hi) / 2
        if velocity_at(lo) * velocity_at(mid) < 0:
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2
```

---

_Cross-reference: [SYMBOLOGY.md §II.D–II.B](../../SYMBOLOGY.md). Station dates are stored in `data/ephemeris/` as Parquet files, indexed by body ID and JD._
