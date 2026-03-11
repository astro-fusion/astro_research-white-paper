# 💥 White Paper 02: Pellet Ablation Dynamics and ELM Mitigation

## Numerical Simulation of Cryogenic Pellet Injection in Stellarator and Tokamak Plasmas

> **Symbol reference**: [SYMBOLOGY.md §I.C](../../SYMBOLOGY.md)
> **Model parameters**: [docs/VALIDATION_AND_EPISTEMOLOGY.md §2.3](../../docs/VALIDATION_AND_EPISTEMOLOGY.md)
> **Code**: [`src/diagnostics/pellet_ablation.py`](../../src/diagnostics/pellet_ablation.py)

---

## Abstract

Pellet injection represents one of the most efficacious experimentally proven methods for plasma refueling and active control in both tokamak and stellarator confinement geometries. Beyond simple fuelling, pellets are deployed as a primary tool for mitigating the destructive energy releases associated with Edge Localized Modes (ELMs). This white paper documents the governing differential equations for the ablation of cryogenic deuterium pellets—including the critical shielding cloud correction—along with the numerical integration strategy and boundary conditions employed in the repository's canonical CFQS pellet simulation dataset.

---

## 1. ELM Mitigation Background

Edge Localized Modes (ELMs) are periodic, violent magnetohydrodynamic (MHD) instabilities that develop at the plasma edge (the H-mode pedestal). Each ELM event releases an energy burst $\Phi_{\rm ELM}$ that deposits transiently onto the plasma-facing components (PFCs). For ITER- and DEMO-class devices, unmitigated ELMs would erode the divertor tungsten armor within thousands of shots.

High-frequency pellet injection (trigger rate $f_{\rm trigger} \gg f_{\rm natural ELM}$) forces small, controlled ELM releases, reducing peak $\Phi_{\rm ELM}$ to tolerable levels.

---

## 2. Governing Equations: Ablation Rate

### 2.1 Neutral Gas Shielding Model

As a solid cryogenic pellet of radius $r_p$ traverses the hot background plasma, surface material ablates, forming a neutral gas cloud that partially shields the pellet from the incoming heat flux. The ablation rate is governed by the **NBI (Neutral Gas and Plasma Shielding) model**:

$$\frac{dr_p}{dt} = -\frac{\dot{m}_{\rm abl}}{4\pi r_p^2\, \rho_{\rm pellet}}$$

where $\dot{m}_{\rm abl}$ (kg s⁻¹) is the ablation mass rate, determined by the shielded heat flux:

$$\dot{m}_{\rm abl} = \frac{Q_{\rm eff}(n_e, T_e, r_p, S_c)}{\mathcal{L}_{\rm sub}}$$

with $Q_{\rm eff}$ the effective heat flux reaching the pellet surface (modified by the shielding factor $S_c$) and $\mathcal{L}_{\rm sub}$ the latent heat of sublimation.

### 2.2 Shielding Factor

The shielding factor $S_c$ accounts for the attenuation of electron energy flux by the ablation cloud:

$$S_c = \exp\!\left(-\frac{n_{\rm cl}\, r_{\rm cl}}{\lambda_{\rm mfp}}\right)$$

where $n_{\rm cl}$ is the cloud number density, $r_{\rm cl}$ is the cloud radius, and $\lambda_{\rm mfp}$ is the electron mean free path in the cloud.

The shielded heat flux reaching the pellet becomes:

$$Q_{\rm eff} = Q_0\, S_c = \frac{1}{2}\, n_e\, v_{th,e}\, k_B T_e\, S_c$$

### 2.3 Combined ODE System

The full state vector is $\mathbf{y} = [r_p,\; N_p]^T$ where $N_p$ is the remaining particle count:

$$\frac{dr_p}{dt} = -\frac{3}{4}\, \frac{\dot{m}_{\rm abl}}{4\pi r_p^2\, \rho_{\rm pellet}}$$

$$\frac{dN_p}{dt} = -\frac{4\pi r_p^2\, \dot{m}_{\rm abl}}{m_D}$$

Initial conditions (CFQS canonical):

- $r_p(0) = 1\,{\rm mm}$, $N_p(0) = 2.0 \times 10^{21}\,{\rm particles}$
- Background: $n_e = 5 \times 10^{19}\,{\rm m}^{-3}$, $T_e = 3\,{\rm keV}$

---

## 3. Numerical Integration Strategy

**Method**: Adaptive Runge-Kutta 45 (Dormand-Prince), via `scipy.integrate.solve_ivp`.

```python
from scipy.integrate import solve_ivp
import numpy as np

def ablation_ode(t: float, y: np.ndarray, n_e: float, T_e_eV: float) -> np.ndarray:
    """
    ODE right-hand side for pellet ablation.
    y = [r_p (m), N_p (particles)]
    """
    r_p, N_p = y
    if r_p <= 0 or N_p <= 0:
        return [0.0, 0.0]

    # Thermal velocity of electrons
    v_th_e = np.sqrt(2.0 * T_e_eV * 1.602e-19 / 9.109e-31)

    # Unshielded heat flux
    Q0 = 0.5 * n_e * v_th_e * T_e_eV * 1.602e-19

    # Simplified shielding factor (full model in src/diagnostics/pellet_ablation.py)
    S_c = np.exp(-n_e * r_p * 1e-20)

    Q_eff = Q0 * S_c
    L_sub = 2.27e5   # J/kg sublimation latent heat for D2
    m_D   = 3.344e-27  # kg, deuterium atom mass
    rho_pellet = 200.0  # kg/m^3, solid D2 density

    m_dot = Q_eff * 4 * np.pi * r_p**2 / L_sub

    dr_dt  = -m_dot / (4 * np.pi * r_p**2 * rho_pellet)
    dNp_dt = -m_dot / m_D

    return [dr_dt, dNp_dt]
```

**Integration settings** (see also [docs/VALIDATION_AND_EPISTEMOLOGY.md §2.3](../../docs/VALIDATION_AND_EPISTEMOLOGY.md)):

```python
sol = solve_ivp(
    ablation_ode,
    t_span=[0.0, 1e-3],   # 1 ms total traverse
    y0=[1e-3, 2e21],
    args=(5e19, 3000.0),   # n_e, T_e_eV
    method='RK45',
    rtol=1e-8,
    atol=1e-10,
)
```

---

## 4. Output Dataset Specification

Simulation outputs are stored as `data/simulations/pellet_ablation_cfqs_v1.parquet`:

| Column              | Unit   | Description                 |
| ------------------- | ------ | --------------------------- |
| `t_s`               | s      | Time from injection         |
| `r_p_m`             | m      | Pellet radius               |
| `N_p_particles`     | —      | Remaining particles         |
| `S_c`               | —      | Shielding factor            |
| `Q_eff_Wm2`         | W m⁻²  | Shielded heat flux          |
| `ablation_rate_kgs` | kg s⁻¹ | Instantaneous ablation rate |

---

## 5. Physical Interpretation

The pellet traverses from the low-field side (LFS) toward the plasma core. Peak ablation occurs at the point of maximum background electron density along the trajectory. The cloud density $n_{\rm cl}$ at peak ablation determines the achievable particle deposition profile—a critical design parameter for fuelling efficiency.

At $N_p \approx 2 \times 10^{21}$ particles (canonical CFQS size), simulations show peak deposition occurring at approximately $r/a \approx 0.7$–$0.85$ (normalised plasma radius), demonstrating effective core penetration for density peaking.

---

_All symbols from SYMBOLOGY.md §I.C are used throughout. Run `make pellet-test` to verify outputs._
