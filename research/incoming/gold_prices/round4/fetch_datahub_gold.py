"""Fetch script for Datahub.io core/gold-prices.

Downloads monthly.csv and annual.csv from datahub.io.
Provides monthly gold prices from 1833 to present (ODC-PDDL Public Domain).
"""

import hashlib
import os
import urllib.request

URLS = {
    "monthly": "https://datahub.io/core/gold-prices/r/monthly.csv",
    "annual": "https://datahub.io/core/gold-prices/r/annual.csv"
}

def fetch():
    headers = {"User-Agent": "Mozilla/5.0"}
    for name, url in URLS.items():
        req = urllib.request.Request(url, headers=headers)
        print(f"Fetching Datahub {name} from: {url}")
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
        target = f"/tmp/datahub_gold_{name}.csv"
        with open(target, "wb") as f:
            f.write(data)
        sha256 = hashlib.sha256(data).hexdigest()
        lines = len(data.decode("utf-8", errors="ignore").splitlines()) - 1
        print(f"Downloaded {name}: {len(data)} bytes, {lines} rows to {target}")
        print(f"SHA-256: {sha256}")

if __name__ == "__main__":
    fetch()
