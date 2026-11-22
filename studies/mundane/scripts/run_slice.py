#!/usr/bin/env python3
"""Run the first mundane slice end to end (ADR-006 WP-56).

India, Himalayan earthquakes of Mw 6 and above, D1 + D9 + Vimshottari. Writes
case files, controls, burden.json, results.json and factor_table.csv under
studies/mundane/artifacts/. The slice is descriptive only.

    python studies/mundane/scripts/run_slice.py [--out DIR] [--formats json,html]
"""

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
for _p in (REPO, REPO / "libs"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from vedic_astrology_core.mundane import cli  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--plan", default=str(cli.bur.PLAN_FILE))
    ap.add_argument("--out", default=str(cli.ARTIFACTS))
    ap.add_argument("--formats", default="json,html")
    a = ap.parse_args(argv)
    try:
        s = cli.run_slice(Path(a.plan), Path(a.out), formats=tuple(f for f in a.formats.split(",") if f))
    except (cli.CliError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(f"events in the counts: {s['n_events_counts']}  case-file events: {s['n_events_case_files']}")
    print(f"primary chart: {s['primary_chart']}  secondary: {s['secondary_charts']}")
    print(f"verdict: {s['verdict']}  provisional: {s['tree_dirty']}")
    print(json.dumps(s["outputs"], indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
