#!/usr/bin/env python3
"""
fetch_usgs_comcat.py

Downloads USGS Comprehensive Earthquake Catalog (ComCat) extracts for the Himalayan
bounding box (72-98E, 25-37N) using the USGS FDSN Event Web Service API.
Prints HTTP status, byte size, SHA-256 checksum, and row count.
Saves files directly to /tmp.
"""

import urllib.request
import hashlib
import os

URLS = {
    "usgs_comcat_m55_1976_2026.csv": (
        "https://earthquake.usgs.gov/fdsnws/event/1/query?"
        "format=csv&minlatitude=25&maxlatitude=37&minlongitude=72&maxlongitude=98"
        "&minmagnitude=5.5&starttime=1976-01-01T00:00:00&endtime=2026-01-01T00:00:00"
    ),
    "usgs_comcat_m40_1976_2026.csv": (
        "https://earthquake.usgs.gov/fdsnws/event/1/query?"
        "format=csv&minlatitude=25&maxlatitude=37&minlongitude=72&maxlongitude=98"
        "&minmagnitude=4.0&maxdepth=70&starttime=1976-01-01T00:00:00&endtime=2026-01-01T00:00:00"
    ),
    "usgs_iscgem_centennial_1900_1975.csv": (
        "https://earthquake.usgs.gov/fdsnws/event/1/query?"
        "format=csv&minlatitude=25&maxlatitude=37&minlongitude=72&maxlongitude=98"
        "&minmagnitude=5.5&starttime=1900-01-01T00:00:00&endtime=1975-12-31T23:59:59"
    )
}

def fetch_file(filename, url, timeout=60):
    dest_path = os.path.join("/tmp", filename)
    print(f"Fetching {filename}...")
    print(f"  URL: {url}")
    
    req = urllib.request.Request(url, headers={"User-Agent": "AstroResearch/1.0 (Earthquake-Verification)"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        status = resp.status
        data = resp.read()
    
    with open(dest_path, "wb") as f:
        f.write(data)
    
    sha256 = hashlib.sha256(data).hexdigest()
    lines = [l for l in data.decode("utf-8", errors="ignore").splitlines() if l.strip()]
    row_count = len(lines) - 1 if len(lines) > 0 else 0  # subtract header
    
    print(f"  Status: {status}")
    print(f"  Saved to: {dest_path}")
    print(f"  Size: {len(data):,} bytes")
    print(f"  SHA-256: {sha256}")
    print(f"  Data rows: {row_count}")
    print()

if __name__ == "__main__":
    for fname, url in URLS.items():
        fetch_file(fname, url)
