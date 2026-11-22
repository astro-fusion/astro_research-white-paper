"""Fetch script for World Bank Pink Sheet (Monthly Commodity Prices).

Downloads CMO-Historical-Data-Monthly.xlsx directly from the World Bank.
Extracts monthly historical series for Gold (UK London PM fix) and Silver (UK London fix).
"""

import hashlib
import os
import urllib.request

URL = "https://thedocs.worldbank.org/en/doc/5d903e848db1d1b83e0ec8f744e55570-0350012021/related/CMO-Historical-Data-Monthly.xlsx"
TARGET_FILE = "/tmp/CMO-Historical-Data-Monthly.xlsx"

def fetch():
    headers = {"User-Agent": "Mozilla/5.0"}
    req = urllib.request.Request(URL, headers=headers)
    print(f"Fetching World Bank Pink Sheet from: {URL}")
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = resp.read()
    
    with open(TARGET_FILE, "wb") as f:
        f.write(data)
    
    sha256 = hashlib.sha256(data).hexdigest()
    print(f"Downloaded: {len(data)} bytes to {TARGET_FILE}")
    print(f"SHA-256: {sha256}")
    return TARGET_FILE, sha256

if __name__ == "__main__":
    fetch()
