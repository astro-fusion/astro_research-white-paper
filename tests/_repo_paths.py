"""Locate research scripts across the repository restructure.

The earthquake scripts moved from ``research/use_cases/earthquake/scripts`` to
``studies/earthquake/scripts`` and ``generate_artifacts.py`` from
``research/scripts`` to ``scripts``. Tests try the new location first and
fall back to the old one, so they work on either side of the move.
"""

import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def repo_path(*candidates: str) -> str:
    """Return the first existing repo-relative path (or the first candidate)."""
    for candidate in candidates:
        path = os.path.join(REPO_ROOT, candidate)
        if os.path.exists(path):
            return path
    return os.path.join(REPO_ROOT, candidates[0])


EARTHQUAKE_SCRIPTS = repo_path(
    "studies/earthquake/scripts", "research/use_cases/earthquake/scripts"
)
GENERATE_ARTIFACTS_SCRIPT = repo_path(
    "scripts/generate_artifacts.py", "research/scripts/generate_artifacts.py"
)
MANUSCRIPT_QMD = repo_path(
    "studies/gold_market/paper/manuscript.qmd", "research/reports/manuscript.qmd"
)


def add_earthquake_scripts_to_path() -> str:
    """Put the earthquake scripts directory on ``sys.path`` and return it."""
    if EARTHQUAKE_SCRIPTS not in sys.path:
        sys.path.append(EARTHQUAKE_SCRIPTS)
    return EARTHQUAKE_SCRIPTS
