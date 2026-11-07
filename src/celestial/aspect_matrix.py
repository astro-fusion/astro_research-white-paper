"""src/celestial/aspect_matrix.py.

Aspect Geometry Engine — Graph-Theory Adjacency Matrix
========================================================
See: papers/astrology/03_aspect_geometry_graph_theory.md
     papers/astrology/05_declination_out_of_bounds.md
     SYMBOLOGY.md §II.C, §II.G
"""

from __future__ import annotations

from typing import NamedTuple

import numpy as np

# ── Aspect catalogue ─────────────────────────────────────────────────────────
# {name: (canonical_angle_deg, default_orb_deg)}
ASPECT_CATALOGUE: dict[str, tuple[float, float]] = {
    "conjunction": (0.0, 8.0),
    "semi_sextile": (30.0, 2.0),
    "semi_square": (45.0, 2.0),
    "sextile": (60.0, 6.0),
    "square": (90.0, 8.0),
    "trine": (120.0, 8.0),
    "sesquiquadrate": (135.0, 2.0),
    "quincunx": (150.0, 3.0),
    "opposition": (180.0, 8.0),
}


class AspectHit(NamedTuple):
    """Single detected aspect between two bodies."""

    body_i: int
    body_j: int
    aspect_name: str
    orb_deg: float  # signed: negative = applying, positive = separating


def compute_aspect_matrix(longitudes_deg: np.ndarray) -> np.ndarray:
    """
    Compute the (n × n) minimum-arc aspect matrix.

    Parameters
    ----------
    longitudes_deg : np.ndarray, shape (n,)
        Ecliptic longitudes λ_ecl [0, 360).

    Returns
    -------
    A : np.ndarray, shape (n, n)
        A[i,j] = min arc in degrees; diagonal = 0; symmetric.
    """
    diff = np.abs(longitudes_deg[:, None] - longitudes_deg[None, :])
    return np.minimum(diff, 360.0 - diff)


def detect_aspects(
    longitudes_deg: np.ndarray,
    body_names: list[str],
    orb_override: dict[str, float] | None = None,
) -> list[AspectHit]:
    """Detect all active aspects in the current planetary configuration."""
    A = compute_aspect_matrix(longitudes_deg)
    hits: list[AspectHit] = []

    for aspect_name, (theta, default_orb) in ASPECT_CATALOGUE.items():
        orb = (orb_override or {}).get(aspect_name, default_orb)
        mask = np.abs(A - theta) <= orb
        np.fill_diagonal(mask, False)
        i_arr, j_arr = np.where(np.triu(mask, k=1))
        for i, j in zip(i_arr.tolist(), j_arr.tolist()):
            hits.append(
                AspectHit(
                    body_i=int(i),
                    body_j=int(j),
                    aspect_name=aspect_name,
                    orb_deg=float(A[i, j] - theta),
                )
            )

    return hits


def detect_out_of_bounds(
    declinations_deg: np.ndarray,
    obliquity_deg: float | np.ndarray = 23.4393,
) -> np.ndarray:
    """
    Return boolean mask: True where |δ_decl| > ε (Out-of-Bounds).

    See: papers/astrology/05_declination_out_of_bounds.md §2.4
    """
    return np.abs(declinations_deg) > obliquity_deg


def compute_parallel_matrix(
    declinations_deg: np.ndarray,
    par_orb: float = 1.0,
    cpar_orb: float = 1.0,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Compute parallel and contra-parallel declination aspect matrices.

    Returns
    -------
    (parallel_mask, contra_parallel_mask) : tuple[np.ndarray, np.ndarray]
        Both shape (n, n) boolean; diagonal False.
    """
    d = declinations_deg
    diff_matrix = np.abs(d[:, None] - d[None, :])

    # Compute parallel: |δi - δj| <= orb
    parallel_mask = diff_matrix <= par_orb
    np.fill_diagonal(parallel_mask, False)

    sum_matrix = np.abs(d[:, None] + d[None, :])
    cpar_mask = sum_matrix <= cpar_orb
    np.fill_diagonal(cpar_mask, False)

    return parallel_mask, cpar_mask
