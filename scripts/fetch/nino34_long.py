#!/usr/bin/env python3
"""Fetch the long Nino 3.4 sea-surface-temperature series (1870 on) and index it.

    python scripts/fetch/nino34_long.py

ADR-008 section 6.1 item 7 and WP-95: the monsoon plan uses ONE ENSO series
that covers the explore and the confirm years. The series is the NOAA PSL
Nino 3.4 SST table built from HadISST (monthly, 1870 on; first line "start end",
then rows "YEAR m1 ... m12"). URL checked once on 2026-11-22 (HTTP 200).

The bytes are stored exactly as received (no decoding, no re-encoding), with a
generic client name and no personal details in the request. The source must
be in `data/registry/licences.yaml` first (task H4: the owner reads the terms);
until then this script stops without writing anything. If the terms forbid
use, the monsoon analysis period is cut to the years the pinned series covers
(plan validator, WP-93).
"""

import sys
from typing import Callable, Optional

from vedic_astrology_core.datasets import snapshots

USER_AGENT = "astro-research-fetch/1.0"
URL = "https://psl.noaa.gov/data/timeseries/month/data/nino34.long.data"
NAME = "noaa_nino34_long"
SOURCE_ID = "noaa_nino34_long"


def _default_opener(url: str) -> bytes:
    import urllib.request

    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=180) as response:
        if response.status != 200:
            raise SystemExit(f"{url}: HTTP {response.status}")
        return response.read()


def describe(text: str):
    """(valid monthly values, first YYYY-MM, last YYYY-MM) of a PSL year-by-month table."""
    months = []
    for line in text.splitlines():
        parts = line.split()
        if len(parts) != 13 or not (parts[0].isdigit() and len(parts[0]) == 4):
            continue
        try:
            values = [float(p) for p in parts[1:]]
        except ValueError:
            continue
        for number, value in enumerate(values, start=1):
            if abs(value) < 99:
                months.append(f"{parts[0]}-{number:02d}")
    if not months:
        raise SystemExit("PSL file has no monthly values")
    return len(months), min(months), max(months)


def run(opener: Optional[Callable[[str], bytes]] = None, url: str = URL, **paths):
    """Download, snapshot and index the series; return the snapshot path."""
    opener = opener or _default_opener
    content = opener(url)
    rows, first, last = describe(content.decode("utf-8", errors="replace"))
    if first[:4] > "1871":
        raise SystemExit(f"series starts {first}; the monsoon plan needs 1871 or earlier")
    return snapshots.write_snapshot(
        content,
        name=NAME,
        ext="data",
        source_id=SOURCE_ID,
        source_url=url,
        rows=rows,
        date_min=first,
        date_max=last,
        **paths,
    )


def main(argv=None) -> int:
    """Command-line entry point."""
    try:
        print(run())
    except snapshots.SnapshotError as exc:
        print(f"not written: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
