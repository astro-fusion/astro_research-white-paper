"""Fetch script for CFTC Commitments of Traders (COT) Disaggregated Reports.

Downloads historical weekly positioning for Gold (CMX contract code 088691)
and Silver (CMX contract code 084691) via the public Socrata Open Data API.
Public domain data compiled by the Commodity Futures Trading Commission.
"""

import hashlib
import os
import urllib.request

CONTRACTS = {
    "gold": "088691",
    "silver": "084691"
}

BASE_URL = "https://publicreporting.cftc.gov/resource/jun7-fc8e.csv"

def fetch():
    headers = {"User-Agent": "Mozilla/5.0"}
    for commodity, code in CONTRACTS.items():
        url = f"{BASE_URL}?cftc_contract_market_code={code}&$limit=10000&$order=report_date_as_yyyy_mm_dd"
        target = f"/tmp/cftc_cot_{commodity}_disagg.csv"
        print(f"Fetching CFTC COT {commodity} (code {code}) from: {url}")
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
        with open(target, "wb") as f:
            f.write(data)
        sha256 = hashlib.sha256(data).hexdigest()
        rows = len(data.decode("utf-8", errors="ignore").splitlines()) - 1
        print(f"Downloaded {commodity}: {len(data)} bytes, {rows} rows to {target}")
        print(f"SHA-256: {sha256}")

if __name__ == "__main__":
    fetch()
