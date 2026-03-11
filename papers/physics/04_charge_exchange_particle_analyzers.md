# 🌡️ White Paper 04: Charge-Exchange Particle Analyzers and Ion Temperature Diagnostics

> **Symbol reference**: [SYMBOLOGY.md §I.A](../../SYMBOLOGY.md)
> **Data**: [`data/empirical/cxa_energy_spectra_v1`](../../data/empirical/)

---

## Abstract

Charge-exchange recombination spectroscopy (CXRS) and neutral particle analysis (NPA) via charge-exchange particle analyzers provide the primary experimental access to **ion temperature** ($T_i$) distributions in the hot core of a fusion plasma — a region that is otherwise inaccessible to conventional Langmuir probe diagnostics. This white paper documents the physical operating principles, channel calibration methodology, and data interface specifications for the charge-exchange particle analyzer arrays integrated into the astro-fusion research pipeline.

---

## 1. Operating Principle

### 1.1 Charge-Exchange Reaction

A fast neutral atom beam is injected into the plasma. When a fast beam neutral atom collides with a fully stripped plasma ion, a single electron is transferred:

$$\text{D}^0_{\rm beam} + X^{Z+}_{\rm plasma} \rightarrow \text{D}^+_{\rm beam} + X^{(Z-1)+*}$$

The heavier plasma ion $X^{(Z-1)+*}$ is now in an excited state and emits a characteristic spectral line upon relaxation. For deuterium plasmas, the primary diagnostic reaction is:

$$\text{D}^0_{\rm beam} + \text{D}^+ \rightarrow \text{D}^+_{\rm beam} + \text{D}^0 + h\nu$$

The resulting fast neutral $\text{D}^0$ escapes the magnetic field and is detected by the **neutral particle analyzer (NPA)**.

### 1.2 Energy Spectrum → Ion Temperature

Because the emitted (or escaped) neutral inherits the velocity of the parent plasma ion, the energy spectrum of detected neutrals is directly proportional to the ion velocity distribution. For a Maxwellian plasma:

$$\frac{dJ}{dE} \propto \sqrt{E}\exp\!\left(-\frac{E}{k_B T_i}\right)$$

where $dJ/dE$ is the detected neutral flux per unit energy, $E$ is the kinetic energy of the detected particles, and $T_i$ is the ion temperature. A semi-log plot of $\ln(dJ/dE)$ vs. $E$ is therefore linear with slope $-1/k_B T_i$.

---

## 2. Analyzer Architecture

### 2.1 Energy Channels

The charge-exchange particle analyzer operates across 32 discrete energy channels covering the range:

| Channel | Energy Range          | Resolution | Primary Ion Diagnostic                    |
| ------- | --------------------- | ---------- | ----------------------------------------- |
| 1–8     | $1$–$10\,{\rm keV}$   | $\pm 5\%$  | Thermal bulk; $T_i$ edge                  |
| 9–20    | $10$–$100\,{\rm keV}$ | $\pm 3\%$  | Core $T_i$; suprathermal ions             |
| 21–32   | $0.1$–$1\,{\rm MeV}$  | $\pm 2\%$  | Alpha particle (fusion product) detection |

### 2.2 Geometric Factor and Sensitivity

Each channel has a geometric factor $G_k$ (m² sr) calibrated pre-experiment. The detected flux:

$$J_k = G_k \cdot \Phi_k(T_i, n_i, n_{\rm He^0}_{\rm beam})$$

where $\Phi_k$ is the model prediction for channel $k$ given plasma parameters.

---

## 3. Data Format Specification

Raw analyzer time series are stored in `data/empirical/cxa_energy_spectra_v1.parquet`:

| Column           | Type    | Unit               | Description                    |
| ---------------- | ------- | ------------------ | ------------------------------ |
| `shot_id`        | int64   | —                  | Plasma discharge identifier    |
| `t_ms`           | float64 | ms                 | Shot-relative timestamp        |
| `channel_id`     | int8    | 1–32               | Energy channel index           |
| `energy_keV`     | float64 | keV                | Channel central energy         |
| `flux_counts_ms` | float64 | counts ms⁻¹        | Raw detector count rate        |
| `flux_norm`      | float64 | m⁻² sr⁻¹ s⁻¹ keV⁻¹ | Calibrated differential flux   |
| `T_i_eV`         | float64 | eV                 | Inferred ion temperature (fit) |
| `T_i_err_eV`     | float64 | eV                 | 1σ uncertainty on $T_i$        |

### 3.1 $T_i$ Extraction Script

```python
# src/diagnostics/electron_density_solver.py — T_i fitting routine
import numpy as np
from scipy.optimize import curve_fit

def fit_ion_temperature(
    energies_keV: np.ndarray,
    flux_norm: np.ndarray,
    flux_err: np.ndarray,
) -> tuple[float, float]:
    """
    Fit ion temperature from the energy-resolved neutral flux.
    Uses log-linear fit on ln(dJ/dE) vs E (Maxwellian assumption).

    Returns: (T_i_eV, T_i_sigma_eV)
    """
    energies_eV = energies_keV * 1000.0

    log_flux = np.log(flux_norm)
    log_flux_err = flux_err / flux_norm   # Propagated uncertainty in log space

    def linear_model(E: np.ndarray, neg_inv_T: float, const: float) -> np.ndarray:
        return neg_inv_T * E + const

    popt, pcov = curve_fit(
        linear_model,
        energies_eV,
        log_flux,
        sigma=log_flux_err,
        absolute_sigma=True,
    )
    neg_inv_T, _ = popt
    T_i_eV = -1.0 / neg_inv_T
    T_i_sigma = np.sqrt(pcov[0, 0]) / neg_inv_T**2   # Error propagation

    return T_i_eV, T_i_sigma
```

---

## 4. Cross-Reference with κ-Distribution Results

When the measured $dJ/dE$ spectrum deviates from a log-linear slope (indicating a non-Maxwellian ion distribution), the κ-distribution fit from **Paper 03** is applied:

$$\frac{dJ}{dE} \propto E^{1/2} \left(1 + \frac{E}{\kappa\, k_B T_i}\right)^{-(\kappa+2)}$$

The kappa index $\kappa$ is extracted as a second fit parameter, providing a direct observational measure of the suprathermal ion fraction generated by reconnection events (see
[papers/physics/03](03_relativistic_kappa_distributions.md)).

---

_Data format conforms to [docs/DATA_PROVENANCE.md §2.1](../../docs/DATA_PROVENANCE.md). Symbols from [SYMBOLOGY.md §I.A](../../SYMBOLOGY.md)._
