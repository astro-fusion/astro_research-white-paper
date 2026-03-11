r"""src/diagnostics/line_ratio_spectroscopy.py.

Helium Line Ratio Spectroscopy Engine
======================================
Provides the core computational logic for determining electron temperature (T_e)
and electron density (n_e) from He I emission line ratios.

Mathematical model: papers/physics/01_line_ratio_spectroscopy_thermal_helium.md
Symbol reference:   SYMBOLOGY.md §I.B
Data input:        data/empirical/
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def compute_line_ratio(n_e: float, T_e_eV: float) -> float:
    """
    Compute the dimensionless He I singlet/triplet line ratio R_line(T_e, n_e).

    Uses a simplified 5-level CR model.
    See: papers/physics/01 §2.3.
    """
    # R_line ≈ a * n_e^alpha * T_e^beta [simplified scaling for demonstrating logic]
    # In reality, this interpolates a massive CR-model grid.
    if T_e_eV <= 0:
        return 0.0
    return 1.45e-14 * (n_e**0.21) * (T_e_eV**1.12)


def generate_lookup_table(
    n_e_range: np.ndarray,
    T_e_range: np.ndarray,
) -> pd.DataFrame:
    """
    Generate a 2-D lookup table of R_line(n_e, T_e).

    Parameters
    ----------
    n_e_range : np.ndarray
        Range of electron densities [m^-3].
    T_e_range : np.ndarray
        Range of electron temperatures [eV].

    Returns
    -------
    pd.DataFrame (tidy format)
    """
    records = []
    for ne in n_e_range:
        for te in T_e_range:
            r = compute_line_ratio(ne, te)
            records.append({"n_e": ne, "T_e": te, "R_line": r})

    return pd.DataFrame(records)


def invert_line_ratio(
    R_measured: float,
    lookup_table: pd.DataFrame,
    n_e_guess: float = 1e19,
    T_e_guess: float = 10.0,
) -> tuple[float, float]:
    """
    Invert a measured R_line value to retrieve (n_e, T_e).

    Uses bilinear interpolation on the lookup table.
    """
    # Stub: simplified inversion searching for the closest grid point
    # In Phase II, this will be replaced by a proper SciPy interpolator.
    dist = np.abs(lookup_table["R_line"] - R_measured)
    idx = dist.idxmin()
    row = lookup_table.loc[idx]
    return float(row["n_e"]), float(row["T_e"])


def validate_engine_output() -> bool:
    """
    Verify the engine against reference Helium transition data.

    Gate for CI/CD pipeline (TDD).
    """
    # Reference case: n_e = 1e19, T_e = 50eV
    r_val = compute_line_ratio(1e19, 50.0)
    expected = 6.43  # hypothetical benchmark
    tolerance = 0.05
    is_valid = abs(r_val - expected) < (expected * tolerance)
    if not is_valid:
        logger.error("Validation failed: R=%.2f, Expected=%.2f", r_val, expected)
    return is_valid


def main() -> None:
    """Run He line ratio lookup generator CLI."""
    parser = argparse.ArgumentParser(description="He line ratio lookup generator")
    parser.add_argument(
        "--n_e_start", type=float, default=1e18, help="Start density [m^-3]"
    )
    parser.add_argument(
        "--n_e_end", type=float, default=1e20, help="End density [m^-3]"
    )
    parser.add_argument("--T_e_start", type=float, default=1.0, help="Start temp [eV]")
    parser.add_argument("--T_e_end", type=float, default=100.0, help="End temp [eV]")
    parser.add_argument("--steps", type=int, default=50, help="Grid resolution")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/simulations/he_line_ratio_lookup.parquet"),
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    ne_grid = np.logspace(np.log10(args.n_e_start), np.log10(args.n_e_end), args.steps)
    te_grid = np.linspace(args.T_e_start, args.T_e_end, args.steps)

    logger.info("Generating lookup table (%d x %d)...", args.steps, args.steps)
    df = generate_lookup_table(ne_grid, te_grid)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(args.output, index=False)
    logger.info("Lookup table saved → %s", args.output)


if __name__ == "__main__":
    main()
