"""Fetch script for SPDR Gold Shares (GLD) Historical Holdings Archive.

Downloads the official historical holdings spreadsheet directly from State Street Global Advisors API.
Endpoint: https://api.spdrgoldshares.com/api/v1/historical-archive?product=gld&exchange=NYSE&lang=en
Contains daily NAV, closing price, ounces, and metric tonnes from fund inception (2004-11-18) to present.
"""

import hashlib
import os
import urllib.request

URL = "https://api.spdrgoldshares.com/api/v1/historical-archive?product=gld&exchange=NYSE&lang=en"
TARGET_FILE = "/tmp/gld_historical_archive.xlsx"

def fetch():
    headers = {"User-Agent": "Mozilla/5.0"}
    req = urllib.request.Request(URL, headers=headers)
    print(f"Fetching GLD Historical Archive from: {URL}")
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = resp.read()
    with open(TARGET_FILE, "wb") as f:
        f.write(data)
    sha256 = hashlib.sha256(data).hexdigest()
    print(f"Downloaded GLD Archive: {len(data)} bytes to {TARGET_FILE}")
    print(f"SHA-256: {sha256}")
    return TARGET_FILE, sha256

if __name__ == "__main__":
    fetch()
