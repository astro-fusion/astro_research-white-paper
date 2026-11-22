#!/usr/bin/env python3
"""Fetch the GFZ Potsdam Kp/ap/Ap index file and index it.

    python scripts/fetch/gfz_kp.py

CC BY 4.0; cite Matzka et al. (2021), Space Weather 19, e2020SW002641. The
text file is stored byte for byte; comment lines start with '#'.
"""

import sys
from typing import Callable, Optional

from vedic_astrology_core.datasets import snapshots

URL = "https://kp.gfz-potsdam.de/app/files/Kp_ap_Ap_SN_F107_since_1932.txt"


def _default_opener(url: str) -> bytes:
    import requests

    response = requests.get(url, timeout=120)
    if response.status_code != 200:
        raise SystemExit(f"{url}: HTTP {response.status_code}")
    return response.content


def describe(text: str):
    """(rows, date_min, date_max) from the ``YYYY MM DD ...`` data lines."""
    dates = []
    for line in text.splitlines():
        parts = line.split()
        if not parts or parts[0].startswith("#"):
            continue
        if len(parts) < 3 or not all(p.isdigit() for p in parts[:3]):
            raise SystemExit(f"unexpected Kp line: {line[:60]!r}")
        dates.append(f"{int(parts[0]):04d}-{int(parts[1]):02d}-{int(parts[2]):02d}")
    if not dates:
        raise SystemExit("Kp file has no data lines")
    return len(dates), min(dates), max(dates)


def run(opener: Optional[Callable[[str], bytes]] = None, url: str = URL, **paths):
    """Download, snapshot and index the Kp file; return the snapshot path."""
    content = (opener or _default_opener)(url)
    rows, date_min, date_max = describe(content.decode("utf-8"))
    return snapshots.write_snapshot(
        content,
        name="gfz_kp",
        ext="txt",
        source_id="gfz_kp",
        source_url=url,
        rows=rows,
        date_min=date_min,
        date_max=date_max,
        **paths,
    )


def main(argv=None) -> int:
    """Command-line entry point."""
    print(run())
    return 0


if __name__ == "__main__":
    sys.exit(main())
