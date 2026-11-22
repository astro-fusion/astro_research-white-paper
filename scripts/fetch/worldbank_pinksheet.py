#!/usr/bin/env python3
"""Fetch the World Bank Pink Sheet (monthly) workbook and index it.

    python scripts/fetch/worldbank_pinksheet.py

CC BY 4.0: attribute the World Bank. Rows and date range are filled in only
when pandas can read the workbook (openpyxl installed); otherwise they are null.
"""

import io
import sys
from typing import Callable, Optional

from vedic_astrology_core.datasets import snapshots

URL = (
    "https://thedocs.worldbank.org/en/doc/"
    "74e8be41ceb20fa0da750cda2f6b9e4e-0050012026/related/"
    "CMO-Historical-Data-Monthly.xlsx"
)


def _default_opener(url: str) -> bytes:
    import requests

    response = requests.get(url, timeout=120)
    if response.status_code != 200:
        raise SystemExit(f"{url}: HTTP {response.status_code}")
    return response.content


def _describe(content: bytes):
    """(rows, date_min, date_max) of the 'Monthly Prices' sheet, else Nones."""
    try:
        import pandas as pd

        sheet = pd.read_excel(
            io.BytesIO(content), sheet_name="Monthly Prices", header=None, skiprows=4
        )
        months = sheet.iloc[:, 0].astype(str).str.extract(r"^(\d{4})M(\d{2})$").dropna()
        if months.empty:
            return None, None, None
        dates = sorted(f"{y}-{m}" for y, m in months.itertuples(index=False))
        return len(dates), dates[0], dates[-1]
    except Exception:  # missing openpyxl or a changed layout: record nulls
        return None, None, None


def run(opener: Optional[Callable[[str], bytes]] = None, url: str = URL, **paths):
    """Download, snapshot and index the workbook; return the snapshot path."""
    content = (opener or _default_opener)(url)
    if content[:2] != b"PK":
        raise SystemExit("Pink Sheet download is not an xlsx (zip) file")
    rows, date_min, date_max = _describe(content)
    return snapshots.write_snapshot(
        content,
        name="worldbank_pinksheet",
        ext="xlsx",
        source_id="worldbank_pinksheet",
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
