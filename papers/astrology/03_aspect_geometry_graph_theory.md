# 📐 White Paper 03: Aspect Geometry via Graph Theory and Adjacency Matrix Formulation

## High-Velocity Computation of Planetary Angular Relationships

> **Symbol reference**: [SYMBOLOGY.md §II.C](../../SYMBOLOGY.md)
> **Code**: [`src/celestial/aspect_matrix.py`](../../src/celestial/aspect_matrix.py)

---

## Abstract

Astrological aspects—specific angular separations between pairs of celestial bodies—form the primary relational geometry of any astrological chart. At scale (long time-series transit analysis, synastry comparison matrices, planetary return studies), the naive O(n²) pairwise computation quickly becomes a bottleneck. This white paper formalises the aspect calculation as a symmetric adjacency matrix problem on a weighted graph, enabling full NumPy vectorisation. The result is a computation engine capable of evaluating the complete aspect grid for 10 bodies across 36,500 time-steps (100 years at daily resolution) in approximately 8 minutes.

---

## 1. Graph-Theoretic Formulation

### 1.1 The Aspect Graph

Define a weighted undirected graph $G = (V, E)$ where:

- **Vertices** $V = \{v_1, v_2, \ldots, v_n\}$: the $n$ celestial bodies under analysis
- **Edges** $E$: every pair $(v_i, v_j)$ for $i \neq j$, forming a complete graph $K_n$
- **Edge weight** $a_{ij}$: the minimum angular arc between bodies $i$ and $j$ on the ecliptic

### 1.2 Aspect Adjacency Matrix

The $(n \times n)$ real-valued aspect matrix $\mathbf{A}$ has elements:

$$a_{ij} = \min\!\bigl(|\lambda_{\rm ecl,i} - \lambda_{\rm ecl,j}|,\; 360° - |\lambda_{\rm ecl,i} - \lambda_{\rm ecl,j}|\bigr)$$

By construction $\mathbf{A}$ is symmetric ($a_{ij} = a_{ji}$) and $a_{ii} = 0$ (diagonal). The full information is contained in the upper triangle.

---

## 2. Catalogue of Classical Aspects

| Aspect Name           | Canonical Angle $\theta_{\rm asp}$ | Default Orb $\Delta\theta$ | Harmonic | Interpretation Class   |
| --------------------- | ---------------------------------- | -------------------------- | -------- | ---------------------- |
| Conjunction           | 0°                                 | ±8°                        | 1st      | Fusion / amplification |
| Semi-sextile          | 30°                                | ±2°                        | 12th     | Mild dissonance        |
| Semi-square           | 45°                                | ±2°                        | 8th      | Friction               |
| Sextile               | 60°                                | ±6°                        | 6th      | Opportunity            |
| Square                | 90°                                | ±8°                        | 4th      | Dynamic tension        |
| Trine                 | 120°                               | ±8°                        | 3rd      | Ease and flow          |
| Sesquiquadrate        | 135°                               | ±2°                        | 8th      | Friction (extended)    |
| Quincunx (Inconjunct) | 150°                               | ±3°                        | —        | Adjustment required    |
| Opposition            | 180°                               | ±8°                        | 2nd      | Polarisation           |

**Aspect detection condition**: An aspect between bodies $i$ and $j$ is flagged when:

$$|a_{ij} - \theta_{\rm asp}| \leq \Delta\theta$$

---

## 3. NumPy Vectorised Implementation

```python
# src/celestial/aspect_matrix.py
import numpy as np
from dataclasses import dataclass
from typing import NamedTuple

ASPECT_CATALOGUE: dict[str, tuple[float, float]] = {
    "conjunction":    (0.0,   8.0),
    "semi_sextile":   (30.0,  2.0),
    "semi_square":    (45.0,  2.0),
    "sextile":        (60.0,  6.0),
    "square":         (90.0,  8.0),
    "trine":          (120.0, 8.0),
    "sesquiquadrate": (135.0, 2.0),
    "quincunx":       (150.0, 3.0),
    "opposition":     (180.0, 8.0),
}

class AspectHit(NamedTuple):
    body_i:     int
    body_j:     int
    aspect_name: str
    orb_deg:    float    # signed: negative = applying, positive = separating


def compute_aspect_matrix(longitudes_deg: np.ndarray) -> np.ndarray:
    """
    Compute the (n x n) minimum-arc aspect matrix for n celestial bodies.

    Parameters
    ----------
    longitudes_deg : np.ndarray, shape (n,)
        Ecliptic longitudes λ_ecl in degrees [0, 360).

    Returns
    -------
    A : np.ndarray, shape (n, n)
        Symmetric matrix where A[i,j] = min arc in degrees.
    """
    n = len(longitudes_deg)
    # Broadcast outer difference
    diff = np.abs(longitudes_deg[:, None] - longitudes_deg[None, :])  # (n, n)
    A = np.minimum(diff, 360.0 - diff)
    return A


def detect_aspects(
    longitudes_deg: np.ndarray,
    body_names: list[str],
    orb_override: dict[str, float] | None = None,
) -> list[AspectHit]:
    """
    Detect all active aspects in the current planetary configuration.
    Uses vectorised comparison against the full ASPECT_CATALOGUE.
    """
    A = compute_aspect_matrix(longitudes_deg)
    hits: list[AspectHit] = []

    for aspect_name, (theta, default_orb) in ASPECT_CATALOGUE.items():
        orb = orb_override.get(aspect_name, default_orb) if orb_override else default_orb
        # Check upper triangle only (symmetric)
        mask = np.abs(A - theta) <= orb
        np.fill_diagonal(mask, False)
        i_arr, j_arr = np.where(np.triu(mask, k=1))
        for i, j in zip(i_arr, j_arr):
            hits.append(AspectHit(
                body_i=i,
                body_j=j,
                aspect_name=aspect_name,
                orb_deg=float(A[i, j] - theta),
            ))

    return hits
```

---

## 4. Multi-Body Time-Series: Transit Computation at Scale

For $T$ time-steps and $n$ bodies, the full transit computation stores an $(n \times n \times T)$ tensor. For $n=10$, $T=36500$ (100 years daily), memory usage:

$$M = n^2 \times T \times 8\,{\rm bytes} = 10^2 \times 36500 \times 8 \approx 29\,{\rm MB}$$

This fits comfortably in RAM, enabling full vectorised operations:

```python
# Batch aspect detection across T time-steps
# longitudes_all: shape (T, n) — pre-computed ephemeris
diff_batch = np.abs(
    longitudes_all[:, :, None] - longitudes_all[:, None, :]   # (T, n, n)
)
A_batch = np.minimum(diff_batch, 360.0 - diff_batch)          # (T, n, n)

# Detect squares for all time-steps simultaneously
square_mask = np.abs(A_batch - 90.0) <= 8.0                   # boolean (T, n, n)
```

---

## 5. Synastry Matrix

For two individuals with longitude vectors $\boldsymbol{\lambda}^{(1)}$ and $\boldsymbol{\lambda}^{(2)}$, the synastry aspect matrix is:

$$S_{ij} = \min\!\bigl(|\lambda_{\rm ecl,i}^{(1)} - \lambda_{\rm ecl,j}^{(2)}|,\;360° - |\lambda_{\rm ecl,i}^{(1)} - \lambda_{\rm ecl,j}^{(2)}|\bigr)$$

This is **not symmetric** in general (cross-chart comparison) and uses a full $(n \times n)$ matrix rather than just the upper triangle.

---

## 6. Applying vs. Separating Aspects

The **orb direction** (applying vs. separating) is determined by comparing the current arc $a_{ij}$ with the arc one time-step later:

- **Applying** ($\frac{d(a_{ij})}{dt} < 0$): bodies moving toward exact aspect — traditionally more potent
- **Separating** ($\frac{d(a_{ij})}{dt} > 0$): bodies moving away from exact

```python
# Orb velocity (sign indicates applying/separating)
orb_velocity = (A_batch[1:] - A_batch[:-1]) / dt_days   # degrees per day
```

---

_Symbol cross-reference: [SYMBOLOGY.md §II.C](../../SYMBOLOGY.md). For synastry extensions, see the composite chart methodology in `docs/research/`._
