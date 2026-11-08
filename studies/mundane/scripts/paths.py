"""Paths for the mundane study (kept local: ``studies._paths`` has no entry yet)."""

import sys
from pathlib import Path

STUDY_DIR: Path = Path(__file__).resolve().parents[1]
REPO_ROOT: Path = STUDY_DIR.parents[1]
DATA_DIR: Path = STUDY_DIR / "data"
SNAPSHOT_DIR: Path = DATA_DIR / "snapshots"
ARTIFACTS_DIR: Path = STUDY_DIR / "artifacts"
COUNTRIES_FILE: Path = DATA_DIR / "countries.yaml"
EVENTS_FILE: Path = DATA_DIR / "events.jsonl"


def ensure_import_paths() -> None:
    """Make ``libs/`` and the repo root importable when run as a script."""
    for extra in (REPO_ROOT, REPO_ROOT / "libs"):
        if str(extra) not in sys.path:
            sys.path.insert(0, str(extra))
