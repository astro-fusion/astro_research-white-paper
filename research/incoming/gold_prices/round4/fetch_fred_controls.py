"""Fetch script for FRED Macroeconomic and Financial Control Series.

Downloads 8 control series:
1. DFII10: 10-Year Treasury Inflation-Indexed Security (Constant Maturity)
2. DTWEXBGS: Nominal Broad U.S. Dollar Index
3. DGS10: 10-Year Treasury Constant Maturity Rate
4. CPIAUCSL: Consumer Price Index for All Urban Consumers
5. FEDFUNDS: Federal Funds Effective Rate
6. VIXCLS: CBOE Volatility Index (VIX)
7. SP500: S&P 500 Index (10-year rolling window)
8. DCOILBRENTEU: Crude Oil Prices (Brent - Europe)

Uses curl with cookie management to satisfy Akamai Bot Manager headers.
"""

import hashlib
import os
import subprocess

FRED_IDS = [
    "DFII10",
    "DTWEXBGS",
    "DGS10",
    "CPIAUCSL",
    "FEDFUNDS",
    "VIXCLS",
    "SP500",
    "DCOILBRENTEU"
]

COOKIE_JAR = "/tmp/fred_cookies.txt"

def fetch():
    for fid in FRED_IDS:
        url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={fid}"
        target = f"/tmp/fred_{fid}.csv"
        cmd = [
            "curl", "-s",
            "-b", COOKIE_JAR,
            "-c", COOKIE_JAR,
            url,
            "-o", target
        ]
        print(f"Fetching FRED series {fid} from: {url}")
        subprocess.run(cmd, check=True)
        with open(target, "rb") as f:
            data = f.read()
        sha256 = hashlib.sha256(data).hexdigest()
        rows = len(data.decode("utf-8", errors="ignore").splitlines()) - 1
        print(f"Downloaded {fid}: {len(data)} bytes, {rows} rows to {target}")
        print(f"SHA-256: {sha256}")

if __name__ == "__main__":
    fetch()
