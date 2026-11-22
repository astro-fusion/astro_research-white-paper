"""Fetch script for Deutsche Bundesbank Precious Metals Time Series.

Series BBEX3.D.XAU.DEM.EA.AC.C01:
Frankfurt Stock Exchange daily fixing for 1 kg fine gold (999.9/1000) in DEM (1968-06-18 to 1998-12-30).
Retrieved via the Bundesbank SDMX REST API.
"""

import hashlib
import os
import urllib.request

SERIES_ID = "BBEX3.D.XAU.DEM.EA.AC.C01"
URL = "https://api.statistiken.bundesbank.de/rest/data/BBEX3/D.XAU.DEM.EA.AC.C01?format=csv"
TARGET_FILE = f"/tmp/bundesbank_{SERIES_ID.replace('.', '_')}.csv"

def fetch():
    headers = {"User-Agent": "Mozilla/5.0"}
    req = urllib.request.Request(URL, headers=headers)
    print(f"Fetching Bundesbank series {SERIES_ID} from: {URL}")
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = resp.read()
    
    with open(TARGET_FILE, "wb") as f:
        f.write(data)
    
    sha256 = hashlib.sha256(data).hexdigest()
    lines = len(data.decode("utf-8", errors="ignore").splitlines())
    print(f"Downloaded: {len(data)} bytes, {lines} lines to {TARGET_FILE}")
    print(f"SHA-256: {sha256}")
    return TARGET_FILE, sha256

if __name__ == "__main__":
    fetch()
