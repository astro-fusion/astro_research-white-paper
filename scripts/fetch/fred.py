#!/usr/bin/env python3
"""Fetch one FRED series, write a hashed snapshot and add the index entry.

    python scripts/fetch/fred.py DFII10
    python scripts/fetch/fred.py VIXCLS          # hash_only licence: not committable

The licence comes from ``data/registry/licences.yaml``. A series whose licence
is not known here needs an explicit ``--source-id``; the licence is never guessed.
FRED's LBMA gold and silver series were withdrawn in 2022 and are refused.
"""

import argparse
import sys
from typing import Callable, Optional

from vedic_astrology_core.datasets import snapshots
from vedic_astrology_core.markets import fetch

SERIES_SOURCE = {
    "DFII10": "fred_us_gov",
    "DTWEXBGS": "fred_us_gov",
    "VIXCLS": "fred_cboe",
    "GVZCLS": "fred_cboe",
}
WITHDRAWN = {"GOLDPMGBD228NLBM", "GOLDAMGBD228NLBM", "SLVPRUSD"}


def run(
    series_id: str,
    source_id: Optional[str] = None,
    opener: Optional[Callable[[str], str]] = None,
    **paths,
):
    """Fetch, snapshot and index ``series_id``; return the snapshot path."""
    if series_id in WITHDRAWN:
        raise SystemExit(f"{series_id}: withdrawn from FRED in 2022 (LBMA licensing)")
    source_id = source_id or SERIES_SOURCE.get(series_id)
    if source_id is None:
        raise SystemExit(f"{series_id}: unknown licence; pass --source-id")
    df = fetch.fred(series_id, opener=opener)
    return snapshots.write_snapshot(
        fetch.csv_bytes(df),
        name=f"fred_{series_id}",
        ext="csv",
        source_id=source_id,
        source_url=df.attrs["source_url"],
        rows=int(len(df)),
        date_min=df["date"].min().strftime("%Y-%m-%d"),
        date_max=df["date"].max().strftime("%Y-%m-%d"),
        extra={"series_id": series_id},
        **paths,
    )


def main(argv=None) -> int:
    """Command-line entry point."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("series_id")
    parser.add_argument("--source-id")
    args = parser.parse_args(argv)
    print(run(args.series_id, args.source_id))
    return 0


if __name__ == "__main__":
    sys.exit(main())
