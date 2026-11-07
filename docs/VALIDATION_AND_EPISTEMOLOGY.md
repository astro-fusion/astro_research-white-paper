# 🔬 Validation and Epistemology

> **Purpose**: Document all mathematical model assumptions, random number generation
> seeds, and numerical simulation boundary conditions used across the astro-fusion
> white papers. This file is a mandatory prerequisite for reproducibility.

---

## 1. Scope and Intent

Scientific papers in this repository make claims that rest on computational models.
Those models contain:

1. **Explicit assumptions** — physics approximations or astrological conventions
   accepted as axioms.
2. **Configurable parameters** — boundary conditions or seed values that must be
   fixed for exact reproduction.
3. **Known limitations** — conditions under which a model breaks down.

All three categories are codified here.

---

## 2. Plasma Physics Models

### 2.1 Thermal Helium Line Ratio Spectroscopy

**Model**: Collisional-radiative (CR) model for neutral helium in a hydrogen plasma.

| Assumption                        | Value / Justification                                                      |
| --------------------------------- | -------------------------------------------------------------------------- |
| Plasma is optically thin          | Emission lines escape without re-absorption; valid for `n_e < 10²⁰ m⁻³`    |
| Steady-state level populations    | `dN_i/dt = 0`; valid when plasma confinement time >> collisional timescale |
| Maxwellian electron distribution  | Suprathermal tails ignored; use κ-distribution models for edge plasmas     |
| Metastable He I (2³S) equilibrium | Population treated as ground-state-like for density > `10¹⁷ m⁻³`           |

**Boundary Conditions**:

```yaml
# ops/config/spectroscopy_cr_model.yml
n_e_range_m3: [1.0e17, 1.0e21] # Valid electron density domain
T_e_range_eV: [1.0, 100.0] # Valid electron temperature domain
He_neutral_fraction: 0.01 # Assumed edge He seeding fraction
transitions:
  singlet_line_nm: 667.8 # He I 2¹P → 2¹S (singlet)
  triplet_line_nm: 706.5 # He I 2³S → 2³P (triplet)
```

### 2.2 Relativistic Kappa Distribution — RNG Seeds

All stochastic simulations for relativistic κ-distributions use a **fixed seed** for
reproducibility. The seed is recorded per dataset version:

| Dataset Version | Library                    | Seed Value | Notes                                      |
| --------------- | -------------------------- | ---------- | ------------------------------------------ |
| `kappa_v1.0`    | `numpy.random.default_rng` | `42`       | Baseline Monte Carlo particle trajectories |
| `kappa_v1.1`    | `numpy.random.default_rng` | `20231015` | Extended reconnection event simulation     |
| `kappa_v2.0`    | `numpy.random.default_rng` | `20240401` | Relativistic correction added              |

**Reproduction snippet**:

```python
import numpy as np

KAPPA_SEED = 42  # change per dataset version table above
rng = np.random.default_rng(seed=KAPPA_SEED)
# All subsequent random draws use `rng` — never call np.random directly
```

### 2.3 Pellet Ablation Numerical Simulation

**Model**: 1-D ablation ODE with shielding cloud correction.

| Parameter                 | Value                        | Reference                                  |
| ------------------------- | ---------------------------- | ------------------------------------------ |
| Pellet size (canonical)   | `N_p = 2.0 × 10²¹ particles` | CFQS design spec                           |
| Integration method        | Runge-Kutta 4 (RK4)          | `scipy.integrate.solve_ivp`, method='RK45' |
| Time step `Δt`            | `1.0 × 10⁻⁶` s               | Convergence verified                       |
| Background plasma density | `n_e = 5.0 × 10¹⁹ m⁻³`       | Reference CFQS operating point             |
| Pellet injection velocity | `v_p = 1000 m s⁻¹`           | Centrifuge launcher reference              |
| Shielding factor `S_c`    | Computed dynamically         | Cloud density / background density         |

**Boundary Conditions**:

```python
# Ablation ODE initial conditions (data/simulations/pellet_ablation_ic.json)
{
    "r_p_initial_m": 0.001,          # 1 mm pellet radius at injection point
    "v_p_ms": 1000.0,
    "n_background_m3": 5.0e19,
    "T_background_eV": 3000.0,
    "injection_angle_deg": 90.0      # perpendicular injection
}
```

---

## 3. Astrological/Celestial Mechanics Models

### 3.1 Ephemeris Engine

| Parameter         | Value                                              | Justification                                           |
| ----------------- | -------------------------------------------------- | ------------------------------------------------------- |
| Ephemeris library | Swiss Ephemeris (pyswisseph)                       | Sub-arcsecond precision; IAU SOFA compliant             |
| Ayanamsa          | Lahiri (Chitrapaksha)                              | Official Indian standard; most used in Jyotish research |
| Coordinate frame  | Geocentric ecliptic of date                        | Standard for natal chart computation                    |
| Delta-T model     | `pyswisseph` internal (Morrison & Stephenson 2004) | Valid from −2000 to +3000 CE                            |
| Valid date range  | 2000 BCE – 3000 CE                                 | Beyond this, use historical approximations only         |

### 3.2 House System Singularity Thresholds

The Placidus and Koch house systems break down at geographic latitudes approaching
the polar circles. The following thresholds are **hard-coded** in
`src/celestial/house_systems.py`:

```python
PLACIDUS_HIGH_DISTORTION_LAT = 60.0   # degrees N/S — smoothing applied above here
PLACIDUS_SINGULARITY_LAT     = 66.5   # degrees N/S — algorithm falls back automatically
FALLBACK_SYSTEM_DEFAULT      = "whole_sign"   # configurable via ops/config/house_config.yml
```

### 3.3 Retrograde Detection Tolerance

The instantaneous velocity `dλ_ecl/dt` near a stationary point is numerically
near-zero and susceptible to floating-point noise. A **3-day centred finite
difference** is used as the default detection window:

$$\frac{d\lambda_{\rm ecl}}{dt}\bigg|_t \approx \frac{\lambda_{\rm ecl}(t+\Delta) - \lambda_{\rm ecl}(t-\Delta)}{2\,\Delta}, \quad \Delta = 1.5\,\text{days}$$

---

## 4. Numerical Precision Standards

| Domain                | Standard                                              | Notes                                       |
| --------------------- | ----------------------------------------------------- | ------------------------------------------- |
| Planetary positions   | 64-bit IEEE 754 double                                | Never use 32-bit float for longitude        |
| Aspect orbs           | Rounded to 4 decimal places (°)                       | Prevents false positive aspect detections   |
| Line ratio `R_line`   | 6 significant figures                                 | Match original published diagnostic results |
| Pellet ablation ODE   | Relative tolerance `rtol=1e-8`, absolute `atol=1e-10` | Set in `scipy.integrate.solve_ivp`          |
| Monte Carlo particles | `N ≥ 10⁶` particles per run                           | Statistical convergence requirement         |

---

## 5. Known Model Limitations

| Model                  | Limitation                                              | Mitigation                                       |
| ---------------------- | ------------------------------------------------------- | ------------------------------------------------ |
| CR Helium spectroscopy | Assumes Maxwellian electrons; fails in non-thermal edge | Use κ-distribution corrected tables              |
| Pellet ablation ODE    | 1-D; ignores cross-field diffusion                      | 3-D MHD needed for high-resolution work          |
| Swiss Ephemeris        | Limited accuracy before 2000 BCE                        | Document as "historical approximation"           |
| Placidus houses        | Singularity above polar circles                         | Automatic whole-sign fallback                    |
| Secondary progessions  | 1 day = 1 year approximation                            | Introduce sidereal year correction for precision |

---

_Update this document whenever model parameters or seeds change. Include the change in
`CHANGELOG.md` with the semantic version that introduced the modification._
