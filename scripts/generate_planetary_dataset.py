#!/usr/bin/env python
"""Generate or verify the daily sidereal planetary dataset.

Examples:
    python scripts/generate_planetary_dataset.py --years 1600-2100
    python scripts/generate_planetary_dataset.py --check --out data/datasets/planetary
"""

import argparse
import sys
import time
from pathlib import Path
from typing import List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "libs"))

from vedic_astrology_core.datasets.planetary import (  # noqa: E402
    generate,
    verify,
)


def parse_years(text: str) -> Tuple[int, int]:
    """Parse "1600-2100" or "2000" into an inclusive (start, end) pair."""
    first, _, last = text.partition("-")
    return int(first), int(last or first)


def main(argv: Optional[List[str]] = None) -> int:
    """Run the CLI; return the process exit code."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--years", default="1600-2100", help="e.g. 1600-2100")
    parser.add_argument("--out", default="data/datasets/planetary")
    parser.add_argument("--fmt", choices=("parquet", "csv"), default="parquet")
    parser.add_argument("--step", default="1D")
    parser.add_argument("--sample-time", default="12:00")
    parser.add_argument("--tz", default="UTC")
    parser.add_argument("--node-model", choices=("mean", "true"), default="mean")
    parser.add_argument("--ayanamsa", default="lahiri")
    parser.add_argument(
        "--check", action="store_true", help="verify hashes of an existing output"
    )
    args = parser.parse_args(argv)
    if args.check:
        bad = verify(args.out)
        for name in bad:
            print(f"MISMATCH {name}")
        print("OK" if not bad else f"{len(bad)} file(s) failed")
        return 1 if bad else 0
    start, end = parse_years(args.years)
    began = time.perf_counter()
    manifests = generate(
        start,
        end,
        step=args.step,
        sample_time=args.sample_time,
        tz=args.tz,
        node_model=args.node_model,
        ayanamsa=args.ayanamsa,
        out_dir=args.out,
        fmt=args.fmt,
    )
    seconds = time.perf_counter() - began
    rows = sum(m["rows"] for m in manifests)
    print(
        f"{len(manifests)} years, {rows:,} rows in {seconds:.1f}s "
        f"({rows / seconds:,.0f} rows/s) -> {args.out}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
