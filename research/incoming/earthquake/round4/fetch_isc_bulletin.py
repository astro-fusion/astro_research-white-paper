#!/usr/bin/env python3
"""
fetch_isc_bulletin.py

Downloads International Seismological Centre (ISC) Reviewed Bulletin extracts
for the Himalayan bounding box (72-98E, 25-37N) using the ISC FDSN Event Web Service API.
Prints HTTP status, byte size, SHA-256 checksum, and row count.
Saves files directly to /tmp.
"""

import urllib.request
import hashlib
import os

URLS = {
    "isc_bulletin_m55_1976_2026.txt": (
        "http://www.isc.ac.uk/fdsnws/event/1/query?"
        "minlatitude=25&maxlatitude=37&minlongitude=72&maxlongitude=98"
        "&minmagnitude=5.5&starttime=1976-01-01&endtime=2026-01-01&format=text"
    ),
    "isc_bulletin_m40_1976_h1.txt": (
        "http://www.isc.ac.uk/fdsnws/event/1/query?"
        "minlatitude=25&maxlatitude=37&minlongitude=72&maxlongitude=98"
        "&minmagnitude=4.0&starttime=1976-01-01&endtime=1976-07-01&format=text"
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
    data_rows = [l for l in lines if not l.startswith("#")]
    
    print(f"  Status: {status}")
    print(f"  Saved to: {dest_path}")
    print(f"  Size: {len(data):,} bytes")
    print(f"  SHA-256: {sha256}")
    print(f"  Data rows: {len(data_rows)}")
    print()

if __name__ == "__main__":
    for fname, url in URLS.items():
        fetch_file(fname, url)
