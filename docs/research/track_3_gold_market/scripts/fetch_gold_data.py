#!/usr/bin/env python3
"""Fetch XAU/USD gold prices and store locally for offline report rendering."""
from datetime import datetime
from pathlib import Path
import pandas as pd

try:
    import yfinance as yf
except ImportError as exc:
    raise SystemExit("Missing dependency: yfinance. Install with: pip install yfinance") from exc

START = "2000-01-01"
END = datetime.utcnow().strftime("%Y-%m-%d")
SYMBOLS = [
    "XAUUSD=X",  # Yahoo spot XAU/USD (preferred)
    "GC=F",      # COMEX Gold Futures (fallback)
]

out_dir = Path(__file__).resolve().parents[1] / "data"
out_dir.mkdir(parents=True, exist_ok=True)
out_path = out_dir / "gold_prices.csv"

# Download daily data with fallback symbols
series = None
symbol_used = None
for sym in SYMBOLS:
    df = yf.download(sym, start=START, end=END, interval="1d", auto_adjust=False, progress=False)
    if df is not None and not df.empty:
        series = df
        symbol_used = sym
        break

if series is None or series.empty:
    raise SystemExit("No data returned from Yahoo Finance. Check symbols or connection.")

series = series.reset_index()
# Normalize column names (handle MultiIndex from yfinance)
if isinstance(series.columns, pd.MultiIndex):
    series.columns = [str(c[0]).lower().replace(" ", "_") for c in series.columns]
else:
    series.columns = [
        (c[0] if isinstance(c, tuple) else c).lower().replace(" ", "_")
        for c in series.columns
    ]

# Keep essential columns
keep = ["date", "open", "high", "low", "close", "adj_close", "volume"]
series = series[[c for c in keep if c in series.columns]]
series.to_csv(out_path, index=False)

meta_path = out_dir / "gold_prices_meta.json"
meta_path.write_text(
    f'{{"symbol":"{symbol_used}","start":"{START}","end":"{END}","source":"Yahoo Finance"}}'
)

print(f"Wrote {out_path} with {len(series)} rows (through {END}) using {symbol_used}")
