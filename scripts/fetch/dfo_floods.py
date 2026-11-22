#!/usr/bin/env python3
"""Fetch the Dartmouth Flood Observatory global flood records and index them.

    python scripts/fetch/dfo_floods.py

Global Active Archive of Large Flood Events (DFO, University of Colorado
Boulder), Zenodo record 19288171, CC0. Stored byte for byte. "rows" is the number
of event rows; the dates are the first and last "Start Date" (m/d/yy, two-digit
years 84 to 99 read as 19xx, others as 20xx).
"""

import csv
import io
import sys
from datetime import datetime
from typing import Callable, Optional

from vedic_astrology_core.datasets import snapshots

URL = "https://zenodo.org/api/records/19288171/files/Global_Flood_Records.csv/content"
USER_AGENT = "astro-research-fetch/1.0"

def _default_opener(url: str) -> bytes:
    import urllib.request

    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=180) as response:
        if response.status != 200:
            raise SystemExit(f"{url}: HTTP {response.status}")
        return response.read()


def _iso(text: str) -> str:
    month, day, year = (int(p) for p in text.strip().split("/"))
    year += 1900 if year >= 84 else 2000
    return datetime(year, month, day).date().isoformat()


def describe(text: str):
    """(rows, date_min, date_max) from the 'Start Date' column."""
    reader = csv.DictReader(io.StringIO(text.lstrip("\N{ZERO WIDTH NO-BREAK SPACE}")))
    if not reader.fieldnames or "Start Date" not in reader.fieldnames:
        raise SystemExit("DFO file has no 'Start Date' column")
    dates = []
    for row in reader:
        try:
            dates.append(_iso(row["Start Date"]))
        except (ValueError, AttributeError):
            raise SystemExit(f"unexpected DFO date: {row.get('Start Date')!r}")
    if not dates:
        raise SystemExit("DFO file has no rows")
    return len(dates), min(dates), max(dates)


def run(opener: Optional[Callable[[str], bytes]] = None, url: str = URL, **paths):
    """Download, snapshot and index the archive; return the snapshot path."""
    content = (opener or _default_opener)(url)
    rows, date_min, date_max = describe(content.decode("utf-8"))
    return snapshots.write_snapshot(
        content,
        name="dfo_global_flood_records",
        ext="csv",
        source_id="dfo_floods",
        source_url=url,
        rows=rows,
        date_min=date_min,
        date_max=date_max,
        **paths,
    )

def main(argv=None) -> int:
    """Command-line entry point."""
    result = run()
    for path in result if isinstance(result, list) else [result]:
        print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
