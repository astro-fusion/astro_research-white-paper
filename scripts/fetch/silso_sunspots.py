#!/usr/bin/env python3
"""Fetch the SILSO monthly total sunspot number v2.0 and index it.

    python scripts/fetch/silso_sunspots.py

World Data Center SILSO, Royal Observatory of Belgium, Brussels. File
SN_m_tot_V2.0.csv: one row per month, semicolon separated, columns year;
month;decimal year;monthly mean total sunspot number;standard deviation;
number of observations;definitive marker (1 definitive, 0 provisional).
A value of -1 means missing. Description page:
https://www.sidc.be/SILSO/INFO/snmtotcsv.php

The solar-cycle baseline of the monsoon and earthquake plans reads this
series (core/stats/season.py solar_cycle_baseline). Stored byte for byte, with a
generic client name. The data policy on the SILSO pages (checked 2026-11-23)
is CC BY-NC 4.0, not CC BY; the register says hash only until the owner reads
the terms (task H4). The source must be in data/registry/licences.yaml first.
"""

import re
import sys
from typing import Callable, Optional

from vedic_astrology_core.datasets import snapshots

USER_AGENT = "astro-research-fetch/1.0"
URL = "https://www.sidc.be/SILSO/DATA/SN_m_tot_V2.0.csv"
NAME = "silso_sn_monthly"
SOURCE_ID = "silso_sunspots"
_ROW = re.compile(r"^\s*(\d{4});\s*(\d{1,2});[^;]*;\s*(-?\d+(?:\.\d+)?);[^;]*;[^;]*;\s*\d\s*$")


def _default_opener(url: str) -> bytes:
    import urllib.request

    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=180) as response:
        if response.status != 200:
            raise SystemExit(f"{url}: HTTP {response.status}")
        return response.read()


def describe(text: str):
    """(monthly rows, first YYYY-MM, last YYYY-MM) over the well-formed rows."""
    months = []
    for line in text.splitlines():
        match = _ROW.match(line)
        if match and 1 <= int(match.group(2)) <= 12:
            months.append(f"{match.group(1)}-{int(match.group(2)):02d}")
    if not months:
        raise SystemExit("SILSO file has no monthly rows")
    return len(months), min(months), max(months)


def run(opener: Optional[Callable[[str], bytes]] = None, url: str = URL, **paths):
    """Download, snapshot and index the series; return the snapshot path."""
    opener = opener or _default_opener
    content = opener(url)
    rows, first, last = describe(content.decode("utf-8", errors="replace"))
    if first > "1750-01":
        raise SystemExit(f"series starts {first}; the file should start in 1749")
    return snapshots.write_snapshot(
        content,
        name=NAME,
        ext="csv",
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
