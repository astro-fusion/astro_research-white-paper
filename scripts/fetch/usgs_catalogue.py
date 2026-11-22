#!/usr/bin/env python3
"""Fetch the USGS ComCat Himalayan-box extract (M 5.5 and over, 1976-2025) and index it.

    python scripts/fetch/usgs_catalogue.py

Box 25 to 37 N, 72 to 98 E, magnitude 5.5 and over, 1976-01-01 to 2026-01-01
(exclusive end), FDSN event service, CSV. US Government data, public domain.
Stored byte for byte. "rows" is the number of events.
"""

import csv
import io
import sys
from typing import Callable, Optional

from vedic_astrology_core.datasets import snapshots

URL = (
    "https://earthquake.usgs.gov/fdsnws/event/1/query?format=csv"
    "&minlatitude=25&maxlatitude=37&minlongitude=72&maxlongitude=98"
    "&minmagnitude=5.5&starttime=1976-01-01T00:00:00&endtime=2026-01-01T00:00:00"
)
USER_AGENT = "astro-research-fetch/1.0"

def _default_opener(url: str) -> bytes:
    import urllib.request

    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=180) as response:
        if response.status != 200:
            raise SystemExit(f"{url}: HTTP {response.status}")
        return response.read()


def describe(text: str):
    """(rows, date_min, date_max) from the 'time' column (ISO dates)."""
    reader = csv.DictReader(io.StringIO(text))
    names = reader.fieldnames or []
    if "time" not in names or "mag" not in names:
        raise SystemExit("USGS file lacks the 'time' and 'mag' columns")
    dates = [row["time"][:10] for row in reader]
    if not dates:
        raise SystemExit("USGS file has no events")
    return len(dates), min(dates), max(dates)


def run(opener: Optional[Callable[[str], bytes]] = None, url: str = URL, **paths):
    """Download, snapshot and index the extract; return the snapshot path."""
    content = (opener or _default_opener)(url)
    rows, date_min, date_max = describe(content.decode("utf-8"))
    return snapshots.write_snapshot(
        content,
        name="usgs_comcat_himalaya_m55",
        ext="csv",
        source_id="usgs_comcat",
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
