#!/usr/bin/env python3
"""Fetch the NOAA ocean indices used as monsoon controls and index them.

    python scripts/fetch/noaa_enso.py

ONI (NOAA CPC via PSL), Nino 3.4 SST (PSL) and the Indian Ocean Dipole Mode Index
(DMI, HadISST1; Saji et al. 1999; freely available for research with citation, so
the register says hash only). The ONI and Nino 3.4 files are US Government
products and may be committed. Each file is a table of rows "YEAR m1 ... m12"
with a header and footer; missing months are sentinels with absolute value 99 or
more. "rows" counts valid monthly values and the dates are "YYYY-MM".
"""

import sys
from typing import Callable, Optional

from vedic_astrology_core.datasets import snapshots

USER_AGENT = "astro-research-fetch/1.0"
FILES = (
    ("noaa_oni", "noaa_enso", "https://psl.noaa.gov/data/correlation/oni.data"),
    ("noaa_nino34", "noaa_enso", "https://psl.noaa.gov/data/correlation/nina34.data"),
    (
        "noaa_dmi_hadley",
        "noaa_dmi",
        "https://psl.noaa.gov/data/timeseries/month/data/dmi.had.long.data",
    ),
)

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


def run(opener: Optional[Callable[[str], bytes]] = None, files=FILES, **paths):
    """Download, snapshot and index each file; return the snapshot paths."""
    opener = opener or _default_opener
    out = []
    for name, source_id, url in files:
        content = opener(url)
        rows, first, last = describe(content.decode("utf-8", errors="replace"))
        out.append(
            snapshots.write_snapshot(
                content,
                name=name,
                ext="data",
                source_id=source_id,
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
