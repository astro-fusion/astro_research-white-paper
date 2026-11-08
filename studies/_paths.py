"""Single source of truth for repository paths used by studies and scripts.

Every study script, top-level script and test resolves data, artifact and
study locations through this module instead of hard-coding relative paths.

Run scripts from anywhere; ``REPO_ROOT`` is derived from this file's location.
Environment overrides exist for CI and temporary test directories.
"""

import os
from pathlib import Path

REPO_ROOT: Path = Path(__file__).resolve().parent.parent
"""Repository root (the directory that contains ``studies/``)."""

STUDIES_ROOT: Path = REPO_ROOT / "studies"

DATA_ROOT: Path = Path(os.environ.get("ASTRO_DATA_ROOT", REPO_ROOT / "data"))
"""Single data root: ``data/raw``, ``data/processed``, ``data/snapshots``."""

RAW_ROOT: Path = DATA_ROOT / "raw"
PROCESSED_ROOT: Path = DATA_ROOT / "processed"
SNAPSHOT_ROOT: Path = DATA_ROOT / "snapshots"
"""Hashed, documented snapshots of external datasets (see data/README.md)."""

STUDIES = (
    "gold_market",
    "silver_market",
    "earthquake",
    "numerology_vs_astrology",
    "remedy_conflict_matrix",
    "mundane",
    "combinations",
)


def study_dir(name: str) -> Path:
    """Return ``studies/<name>``; raise ``KeyError`` for an unknown study."""
    if name not in STUDIES:
        raise KeyError(f"Unknown study {name!r}; expected one of {STUDIES}")
    return STUDIES_ROOT / name


def study_data_dir(name: str) -> Path:
    """Return ``studies/<name>/data`` (small inputs and generated tables)."""
    return study_dir(name) / "data"


def figures_dir(name: str) -> Path:
    """Return ``studies/<name>/figures`` (committed, paper-referenced figures)."""
    return study_dir(name) / "figures"


def tables_dir(name: str) -> Path:
    """Return ``studies/<name>/tables``."""
    return study_dir(name) / "tables"


def artifacts_dir(name: str, create: bool = True) -> Path:
    """Return ``studies/<name>/artifacts`` (gitignored generated output).

    ``ASTRO_ARTIFACTS_DIR`` overrides the location (used by tests).
    """
    override = os.environ.get("ASTRO_ARTIFACTS_DIR")
    path = Path(override) if override else study_dir(name) / "artifacts"
    if create:
        path.mkdir(parents=True, exist_ok=True)
    return path
