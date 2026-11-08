#!/usr/bin/env python3
"""Check that the pipeline's required input files exist; print SHA-256 and rows.

Paths come from ``studies._paths`` so this matches what the scripts read.
Exit status 1 when any required file is missing.
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


def main() -> int:
    """Report each required file; return 1 if any is missing."""
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
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
