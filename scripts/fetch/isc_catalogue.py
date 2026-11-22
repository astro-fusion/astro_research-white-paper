#!/usr/bin/env python3
"""Fetch the ISC Reviewed Bulletin Himalayan-box extract (M 5.5 and over, 1976-2025) and index it.

    python scripts/fetch/isc_catalogue.py

Same box and period as usgs_catalogue.py, from the ISC FDSN event service in
pipe-delimited text. The ISC filter matches a magnitude from any agency, so a
comparison with USGS must fix one magnitude type first (audit 2026-11-22). The
register says hash only until the ISC terms are read. Stored byte for byte.
The "rows" count excludes the header and the trailing '#' agency list.
"""

import sys
from typing import Callable, Optional

from vedic_astrology_core.datasets import snapshots

URL = (
    "https://www.isc.ac.uk/fdsnws/event/1/query?minlatitude=25&maxlatitude=37"
    "&minlongitude=72&maxlongitude=98&minmagnitude=5.5"
    "&starttime=1976-01-01&endtime=2026-01-01&format=text"
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
    """(rows, date_min, date_max) from the pipe-delimited 'Time' column."""
    lines = text.splitlines()
    if not lines or not lines[0].startswith("#EventID|Time|"):
        raise SystemExit("ISC file lacks the expected header")
    dates = []
    for line in lines[1:]:
        if not line.strip() or line.startswith("#"):
            continue
        parts = line.split("|")
        if len(parts) < 11:
            raise SystemExit(f"unexpected ISC line: {line[:60]!r}")
        dates.append(parts[1][:10])
    if not dates:
        raise SystemExit("ISC file has no events")
    return len(dates), min(dates), max(dates)


def run(opener: Optional[Callable[[str], bytes]] = None, url: str = URL, **paths):
    """Download, snapshot and index the extract; return the snapshot path."""
    content = (opener or _default_opener)(url)
    rows, date_min, date_max = describe(content.decode("utf-8"))
    return snapshots.write_snapshot(
        content,
        name="isc_bulletin_himalaya_m55",
        ext="txt",
        source_id="isc_bulletin",
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
