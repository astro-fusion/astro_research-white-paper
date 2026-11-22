#!/usr/bin/env python3
"""Fetch the IITM monthly rainfall archives (India) and index them.

    python scripts/fetch/iitm_rainfall.py

Three plain-text files from the Indian Institute of Tropical Meteorology: all-India
and macro-regions (1871-2016), 30 subdivisions (1871-2016) and the longest
instrumental all-India series (1813-2006). Stored byte for byte. The licence is
unclear (audit 2026-11-22), so the register says hash only: publish the hash and
this script, not the files. A data row starts with a four-digit year followed by
numbers; "rows" counts those lines and the dates are the first and last year.
"""

import re
import sys
from typing import Callable, Optional

from vedic_astrology_core.datasets import snapshots

BASE = "https://www.tropmet.res.in/data/data-archival/"
USER_AGENT = "astro-research-fetch/1.0"
FILES = (
    ("iitm_all_india_macro", BASE + "rain/iitm-regionrf.txt"),
    ("iitm_subdivisions", BASE + "rain/iitm-subdivrf.txt"),
    ("iitm_longest_instrumental", BASE + "rain-series/8-all_ind.txt"),
)
_ROW = re.compile(r"^\s*(\d{4})(\s+-?\d+(\.\d+)?){12,}\s*$")

def _default_opener(url: str) -> bytes:
    import urllib.request

    import ssl
    import subprocess
    import urllib.error

    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        response = urllib.request.urlopen(request, timeout=180)
    except urllib.error.URLError as error:
        if not isinstance(error.reason, ssl.SSLCertVerificationError):
            raise
        # tropmet.res.in serves an incomplete certificate chain that Python's
        # trust store cannot complete. Verification stays on: fall back to
        # curl, which fetches the missing intermediate certificate itself.
        done = subprocess.run(
            ["curl", "-sS", "-L", "-f", "-m", "180", "-A", USER_AGENT, url],
            capture_output=True,
        )
        if done.returncode != 0:
            raise SystemExit(f"{url}: curl failed: {done.stderr.decode()[:200]}")
        return done.stdout
    with response:
        if response.status != 200:
            raise SystemExit(f"{url}: HTTP {response.status}")
        return response.read()


def describe(text: str):
    """(rows, first year, last year) over lines that are a year plus 12 or more numbers."""
    years = [m.group(1) for m in map(_ROW.match, text.splitlines()) if m]
    if not years:
        raise SystemExit("IITM file has no data rows")
    return len(years), min(years), max(years)


def run(opener: Optional[Callable[[str], bytes]] = None, files=FILES, **paths):
    """Download, snapshot and index each file; return the snapshot paths."""
    opener = opener or _default_opener
    out = []
    for name, url in files:
        content = opener(url)
        rows, first, last = describe(content.decode("latin-1"))
        out.append(
            snapshots.write_snapshot(
                content,
                name=name,
                ext="txt",
                source_id="iitm_rainfall",
                source_url=url,
                rows=rows,
                date_min=first,
                date_max=last,
                **paths,
            )
        )
    return out

def main(argv=None) -> int:
    """Command-line entry point."""
    result = run()
    for path in result if isinstance(result, list) else [result]:
        print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
