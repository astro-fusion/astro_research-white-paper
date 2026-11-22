#!/usr/bin/env python3
"""Fetch the Bundesbank Frankfurt gold fixing (daily, DEM per kg) and index it.

    python scripts/fetch/bundesbank_gold.py

Series BBEX3 D.XAU.DEM.EA.AC.C01, 1968-06-18 to 1998-12-30. Reuse permitted with
the source named (Deutsche Bundesbank). The file is stored byte for byte. Days
without a fixing carry "." in the value column and are not counted as rows
(7,622 values). The URL is the corrected one: a doubled "BBEX3." prefix, as in
the incoming sources.csv, returns an error. Values are DEM: converting to USD
needs a DEM/USD series (WP-76).
"""

import re
import sys
from typing import Callable, Optional

from vedic_astrology_core.datasets import snapshots

URL = (
    "https://api.statistiken.bundesbank.de/rest/data/BBEX3/"
    "D.XAU.DEM.EA.AC.C01?format=csv"
)
USER_AGENT = "astro-research-fetch/1.0"
_ROW = re.compile(r"^(\d{4}-\d{2}-\d{2});([^;]*);")

def _default_opener(url: str) -> bytes:
    import urllib.request

    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=180) as response:
        if response.status != 200:
            raise SystemExit(f"{url}: HTTP {response.status}")
        return response.read()


def describe(text: str):
    """(rows, date_min, date_max) over days that carry a numeric fixing."""
    dates = []
    for line in text.lstrip("\N{ZERO WIDTH NO-BREAK SPACE}").splitlines():
        match = _ROW.match(line)
        if not match:
            continue
        value = match.group(2).strip()
        if not value or value == ".":
            continue
        try:
            float(value)
        except ValueError:
            raise SystemExit(f"unexpected Bundesbank value: {line[:60]!r}")
        dates.append(match.group(1))
    if not dates:
        raise SystemExit("Bundesbank file has no daily values")
    return len(dates), min(dates), max(dates)


def run(opener: Optional[Callable[[str], bytes]] = None, url: str = URL, **paths):
    """Download, snapshot and index the series; return the snapshot path."""
    content = (opener or _default_opener)(url)
    rows, date_min, date_max = describe(content.decode("utf-8"))
    return snapshots.write_snapshot(
        content,
        name="bundesbank_gold_dem",
        ext="csv",
        source_id="bundesbank_gold",
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
