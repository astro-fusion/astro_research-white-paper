"""Fetch script for US Economic Policy Uncertainty Index (EPU).

Downloads US monthly EPU index compiled by Scott R. Baker, Nicholas Bloom, and Steven J. Davis.
Source: https://www.policyuncertainty.com/media/US_Policy_Uncertainty_Data.csv
"""

import hashlib
import os
import urllib.request

URL = "https://www.policyuncertainty.com/media/US_Policy_Uncertainty_Data.csv"
TARGET_FILE = "/tmp/epu_us.csv"

def fetch():
    headers = {"User-Agent": "Mozilla/5.0"}
    req = urllib.request.Request(URL, headers=headers)
    print(f"Fetching US EPU data from: {URL}")
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = resp.read()
    with open(TARGET_FILE, "wb") as f:
        f.write(data)
    sha256 = hashlib.sha256(data).hexdigest()
    rows = len(data.decode("utf-8", errors="ignore").splitlines()) - 1
    print(f"Downloaded EPU: {len(data)} bytes, {rows} rows to {TARGET_FILE}")
    print(f"SHA-256: {sha256}")
    return TARGET_FILE, sha256

if __name__ == "__main__":
    fetch()
