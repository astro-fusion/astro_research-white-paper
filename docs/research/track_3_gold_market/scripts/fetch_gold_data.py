#!/usr/bin/env python3
"""Fetch XAU/USD gold prices and store locally for offline report rendering."""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

import pandas as pd

try:
    import yfinance as yf
except ImportError as exc:
    raise SystemExit("Missing dependency: yfinance. Install with: pip install yfinance") from exc

START_YEAR = 2000
END = datetime.utcnow().strftime("%Y-%m-%d")
SYMBOLS = [
    "XAUUSD=X",  # Yahoo spot XAU/USD (preferred)
    "GC=F",      # COMEX Gold Futures (fallback)
]

out_dir = Path(__file__).resolve().parents[1] / "data"
out_dir.mkdir(parents=True, exist_ok=True)
out_path = out_dir / "gold_prices.csv"
yearly_dir = out_dir / "gold_prices_yearly"
yearly_dir.mkdir(parents=True, exist_ok=True)

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch and cache gold price data.")
    parser.add_argument("--start-year", type=int, default=START_YEAR)
    parser.add_argument("--end-year", type=int, default=datetime.utcnow().year)
    parser.add_argument(
        "--update",
        action="store_true",
        help="Refresh the current year if it already exists.",
    )
    parser.add_argument(
        "--update-all",
        action="store_true",
        help="Refresh all years even if cached.",
    )
    parser.add_argument(
        "--merge-only",
        action="store_true",
        help="Skip fetching and only merge existing yearly files.",
    )
    parser.add_argument(
        "--symbol",
        type=str,
        default="",
        help="Override the Yahoo Finance symbol (e.g., GC=F).",
    )
    return parser.parse_args()


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.reset_index()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [str(c[0]).lower().replace(" ", "_") for c in df.columns]
    else:
        df.columns = [
            (c[0] if isinstance(c, tuple) else c).lower().replace(" ", "_")
            for c in df.columns
        ]
    keep = ["date", "open", "high", "low", "close", "adj_close", "volume"]
    for col in keep:
        if col not in df.columns:
            df[col] = pd.NA
    return df[keep]


def select_symbol(preferred: str, start: str, end: str) -> str:
    candidates = [preferred] if preferred else []
    candidates += [sym for sym in SYMBOLS if sym not in candidates]
    for sym in candidates:
        try:
            df = yf.download(sym, start=start, end=end, interval="1d", auto_adjust=False, progress=False)
        except Exception:
            df = None
        if df is not None and not df.empty:
            return sym
    raise SystemExit("No data returned from Yahoo Finance. Check symbols or connection.")


def download_range(symbol: str, start: str, end: str) -> pd.DataFrame:
    df = yf.download(symbol, start=start, end=end, interval="1d", auto_adjust=False, progress=False)
    if df is None or df.empty:
        raise SystemExit(f"No data returned for symbol {symbol}.")
    return normalize_columns(df)


def load_yearly_files(start_year: int, end_year: int) -> list[Path]:
    files = []
    for year in range(start_year, end_year + 1):
        path = yearly_dir / f"gold_prices_{year}.csv"
        if path.exists():
            files.append(path)
    return files


def merge_yearly_files(files: list[Path]) -> pd.DataFrame:
    frames = []
    for path in sorted(files):
        df = pd.read_csv(path)
        frames.append(df)
    if not frames:
        raise SystemExit("No yearly files available to merge.")
    merged = pd.concat(frames, ignore_index=True)
    merged["date"] = pd.to_datetime(merged["date"], errors="coerce")
    merged = merged.dropna(subset=["date"]).sort_values("date")
    merged = merged.drop_duplicates(subset=["date"], keep="last")
    merged["date"] = merged["date"].dt.date.astype(str)
    return merged


def main() -> None:
    args = parse_args()
    start_year = args.start_year
    end_year = args.end_year

    symbol_used = None
    updated_years = []

    meta_path = out_dir / "gold_prices_meta.json"
    preferred_symbol = ""
    if args.symbol:
        preferred_symbol = args.symbol
    elif meta_path.exists():
        try:
            preferred_symbol = json.loads(meta_path.read_text()).get("symbol", "")
        except Exception:
            preferred_symbol = ""

    if not args.merge_only:
        # Pick a working symbol once to avoid repeated failures
        probe_start = f"{start_year}-01-01"
        probe_end = f"{start_year}-12-31"
        symbol_used = select_symbol(preferred_symbol, probe_start, probe_end)

    # If we already have a combined file but no yearly chunks, split locally
    existing_yearly = list(yearly_dir.glob("gold_prices_*.csv"))
    if not existing_yearly and out_path.exists() and not args.update and not args.update_all:
        df = pd.read_csv(out_path)
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.dropna(subset=["date"])
        for year, group in df.groupby(df["date"].dt.year):
            year_path = yearly_dir / f"gold_prices_{year}.csv"
            group = group.copy()
            group["date"] = group["date"].dt.date.astype(str)
            group.to_csv(year_path, index=False)
        updated_years = ["cache_split"]

    if not args.merge_only:
        for year in range(start_year, end_year + 1):
            path = yearly_dir / f"gold_prices_{year}.csv"
            is_current_year = year == end_year

            if path.exists() and not args.update_all:
                if args.update and is_current_year:
                    pass
                else:
                    continue

            start = f"{year}-01-01"
            end = END if is_current_year else f"{year + 1}-01-01"
            data = download_range(symbol_used, start, end)
            data.to_csv(path, index=False)
            updated_years.append(year)

    files = load_yearly_files(start_year, end_year)
    merged = merge_yearly_files(files)
    merged.to_csv(out_path, index=False)

    meta = {
        "symbol": symbol_used or preferred_symbol,
        "start_year": start_year,
        "end_year": end_year,
        "source": "Yahoo Finance",
        "updated_years": updated_years,
        "generated_at": datetime.utcnow().isoformat(),
        "yearly_dir": str(yearly_dir),
    }
    (out_dir / "gold_prices_meta.json").write_text(json.dumps(meta, indent=2))

    print(
        f"Wrote {out_path} with {len(merged)} rows (through {END}). "
        f"Updated years: {updated_years or 'none'}"
    )


if __name__ == "__main__":
    main()
