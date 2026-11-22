#!/usr/bin/env python3
"""Check that the pipeline's required input files exist; print SHA-256 and rows.

Paths come from ``studies._paths`` so this matches what the scripts read.
It also checks ``data/snapshot_index.json``: a listed snapshot whose bytes
differ from the indexed SHA-256, and a file in ``data/snapshots/`` that the
index does not list, both fail. `--snapshots-only` skips the required-file check.
Exit status 1 when any required file is missing or the index check fails.
"""

import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # repo root

from studies._paths import PROCESSED_ROOT, RAW_ROOT, REPO_ROOT  # noqa: E402

REQUIRED = (
    RAW_ROOT / "gold_prices.csv",
    PROCESSED_ROOT / "aligned_planetary_data.csv",
)


def describe(path: Path) -> str:
    """Return 'relative/path  sha256=...  rows=N' for a CSV file."""
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    with path.open("rb") as handle:
        rows = max(sum(1 for _ in handle) - 1, 0)
    return f"{path.relative_to(REPO_ROOT)}  sha256={digest}  rows={rows}"


def check_snapshots() -> int:
    """Verify the snapshot index against the files; return the problem count."""
    from vedic_astrology_core.datasets import snapshots

    problems = snapshots.verify_index(
        snapshots.INDEX_PATH, snapshots.SNAPSHOT_ROOT, REPO_ROOT
    )
    for problem in problems:
        print(f"SNAPSHOT: {problem}")
    if not problems:
        print("snapshot index ok")
    return len(problems)


def main(argv=None) -> int:
    """Report each required file and the snapshot index; 1 on any failure."""
    argv = sys.argv[1:] if argv is None else argv
    status = 0
    if "--snapshots-only" not in argv:
        print("Checking required input data...")
        missing = 0
        for path in REQUIRED:
            if path.is_file():
                print(describe(path))
            else:
                print(f"MISSING: {path.relative_to(REPO_ROOT)}")
                missing += 1
        if missing:
            print("check-data failed: required data files are missing")
            status = 1
    if check_snapshots():
        print("check-data failed: snapshot index does not match the files")
        status = 1
    return status


if __name__ == "__main__":
    sys.exit(main())
