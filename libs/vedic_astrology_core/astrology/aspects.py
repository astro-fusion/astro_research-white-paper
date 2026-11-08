"""
Geometric aspects: minimum-arc matrix, orb aspects, declination parallels.

Ported from the retired ``aspect_matrix.py`` of the second engine (WP-7) for
papers/astrology/03 and 05. These are orb-based geometric aspects of the
Hellenistic and Western tradition, not graha drishti:

- Major aspects (conjunction, sextile, square, trine, opposition) are the
  Ptolemaic set (Ptolemy, Tetrabiblos I.13); the minor ones (semi-sextile,
  semi-square, sesquiquadrate, quincunx) follow Kepler (Harmonices Mundi IV).
- The Vedic whole-sign aspect (graha drishti, BPHS Ch. 26 "Graha Drishti
  Kathana": every graha aspects the 7th; Mars also the 4th and 8th, Jupiter
  the 5th and 9th, Saturn the 3rd and 10th) is the ``graha_drishti`` rule
  predicate in ``vedic_astrology_core.rules.predicates.relations``; use that
  for any Jyotish rule.
- Out-of-bounds compares declination with the obliquity of the ecliptic, the
  Sun's greatest declination (Surya Siddhanta II.28 gives 24 degrees; the
  modern mean value at J2000 is 23.4393 degrees, IAU 2006).

Longitudes may be tropical or sidereal: aspects depend only on differences,
so the ayanamsa cancels.
"""

from __future__ import annotations

from typing import Dict, List, NamedTuple, Optional, Sequence, Tuple, Union

import numpy as np

# Mean obliquity of the ecliptic at J2000.0 (IAU 2006 precession), degrees.
MEAN_OBLIQUITY_J2000 = 23.439279

# {name: (exact angle, default orb)} in degrees.
ASPECT_CATALOGUE: Dict[str, Tuple[float, float]] = {
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
    """One aspect between bodies ``body_i`` < ``body_j``.

    ``orb_deg`` is the arc minus the exact angle: negative when the arc is
    narrower than exact, positive when wider. Applying versus separating
    needs the speeds and is not decided here.
    """

    body_i: int
    body_j: int
    aspect_name: str
    orb_deg: float


def compute_aspect_matrix(longitudes_deg: np.ndarray) -> np.ndarray:
    """Return the symmetric (n, n) matrix of minimum arcs in [0, 180]."""
    lon = np.asarray(longitudes_deg, dtype=float) % 360.0
    diff = np.abs(lon[:, None] - lon[None, :])
    return np.minimum(diff, 360.0 - diff)


def detect_aspects(
    longitudes_deg: np.ndarray,
    body_names: Sequence[str],
    orb_override: Optional[Dict[str, float]] = None,
) -> List[AspectHit]:
    """List every catalogued aspect within orb, in catalogue order."""
    lon = np.asarray(longitudes_deg, dtype=float)
    if len(body_names) != lon.shape[0]:
        raise ValueError(f"{len(body_names)} body names for {lon.shape[0]} longitudes")
    arcs = compute_aspect_matrix(lon)
    overrides = orb_override or {}
    hits: List[AspectHit] = []
    for name, (angle, default_orb) in ASPECT_CATALOGUE.items():
        orb = overrides.get(name, default_orb)
        mask = np.triu(np.abs(arcs - angle) <= orb, k=1)
        for i, j in zip(*np.nonzero(mask)):
            hits.append(AspectHit(int(i), int(j), name, float(arcs[i, j] - angle)))
    return hits


def detect_out_of_bounds(
    declinations_deg: np.ndarray,
    obliquity_deg: Union[float, np.ndarray] = MEAN_OBLIQUITY_J2000,
) -> np.ndarray:
    """Return a boolean mask, True where |declination| exceeds the obliquity."""
    return np.abs(np.asarray(declinations_deg, dtype=float)) > obliquity_deg


def compute_parallel_matrix(
    declinations_deg: np.ndarray,
    par_orb: float = 1.0,
    cpar_orb: float = 1.0,
) -> Tuple[np.ndarray, np.ndarray]:
    """Return (parallel, contra-parallel) boolean (n, n) masks, diagonal False.

    Parallel: same declination within ``par_orb``. Contra-parallel: equal
    declination of opposite sign within ``cpar_orb``.
    """
    d = np.asarray(declinations_deg, dtype=float)
    parallel = np.abs(d[:, None] - d[None, :]) <= par_orb
    contra = np.abs(d[:, None] + d[None, :]) <= cpar_orb
    np.fill_diagonal(parallel, False)
    np.fill_diagonal(contra, False)
    return parallel, contra
