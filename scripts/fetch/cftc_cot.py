#!/usr/bin/env python3
"""Fetch CFTC Commitments of Traders (disaggregated, futures only) and index it.

    python scripts/fetch/cftc_cot.py --years 2010-2025

Keeps the rows whose market name contains one of the ``--market`` strings
(default: COMEX gold and silver). US Government work, public domain.
"""

import argparse
import io
import sys
import zipfile
from typing import Callable, Iterable, Optional

import pandas as pd

from vedic_astrology_core.datasets import snapshots

URL = "https://www.cftc.gov/files/dea/history/fut_disagg_txt_{year}.zip"
DEFAULT_MARKETS = ("GOLD - COMMODITY EXCHANGE INC.", "SILVER - COMMODITY EXCHANGE INC.")
NAME_COL = "Market_and_Exchange_Names"
DATE_COL = "Report_Date_as_YYYY-MM-DD"


def _default_opener(url: str) -> bytes:
    import requests

    response = requests.get(url, timeout=120)
    if response.status_code != 200:
        raise SystemExit(f"{url}: HTTP {response.status_code}")
    return response.content


def parse_year(content: bytes, markets: Iterable[str]) -> pd.DataFrame:
    """Rows of one yearly zip whose market name contains any of ``markets``."""
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        names = [n for n in archive.namelist() if not n.endswith("/")]
        if len(names) != 1:
            raise SystemExit(f"COT zip holds {len(names)} files, expected 1")
        frame = pd.read_csv(archive.open(names[0]), low_memory=False)
    frame.columns = [c.strip() for c in frame.columns]
    for column in (NAME_COL, DATE_COL):
        if column not in frame.columns:
            raise SystemExit(f"COT file lacks column {column}")
    wanted = tuple(m.upper() for m in markets)
    mask = frame[NAME_COL].astype(str).str.upper().apply(lambda s: any(w in s for w in wanted))
    return frame[mask]


def run(
    years: Iterable[int],
    markets: Iterable[str] = DEFAULT_MARKETS,
    opener: Optional[Callable[[str], bytes]] = None,
    **paths,
):
    """Download each year, filter, snapshot and index; return the path."""
    years = list(years)
    opener = opener or _default_opener
    frames = [parse_year(opener(URL.format(year=y)), markets) for y in years]
    frame = pd.concat(frames, ignore_index=True)
    if frame.empty:
        raise SystemExit("no COT rows matched the market filter")
    frame[DATE_COL] = pd.to_datetime(frame[DATE_COL]).dt.strftime("%Y-%m-%d")
    frame = frame.sort_values([NAME_COL, DATE_COL]).reset_index(drop=True)
    content = frame.to_csv(index=False, lineterminator="\n").encode()
    return snapshots.write_snapshot(
        content,
        name=f"cftc_cot_disagg_{years[0]}_{years[-1]}",
        ext="csv",
        source_id="cftc_cot",
        source_url=URL.format(year="<year>"),
        rows=int(len(frame)),
        date_min=str(frame[DATE_COL].min()),
        date_max=str(frame[DATE_COL].max()),
        extra={"markets": list(markets)},
        **paths,
    )


def main(argv=None) -> int:
    """Command-line entry point."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--years", required=True, help="e.g. 2010-2025 or 2024")
    parser.add_argument("--market", action="append")
    args = parser.parse_args(argv)
    first, _, last = args.years.partition("-")
    years = range(int(first), int(last or first) + 1)
    print(run(years, args.market or DEFAULT_MARKETS))
    return 0


if __name__ == "__main__":
    sys.exit(main())
