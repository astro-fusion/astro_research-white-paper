"""Fetch script for Geopolitical Risk Index (GPR).

Downloads daily and monthly GPR data compiled by Dario Caldara and Matteo Iacoviello.
Daily: https://www.matteoiacoviello.com/gpr_files/data_gpr_daily_recent.xls
Monthly: https://www.matteoiacoviello.com/gpr_files/data_gpr_export.xls
"""

import hashlib
import os
import urllib.request

URLS = {
    "daily": "https://www.matteoiacoviello.com/gpr_files/data_gpr_daily_recent.xls",
    "monthly": "https://www.matteoiacoviello.com/gpr_files/data_gpr_export.xls"
}

def fetch():
    headers = {"User-Agent": "Mozilla/5.0"}
    for freq, url in URLS.items():
        req = urllib.request.Request(url, headers=headers)
        target = f"/tmp/gpr_{freq}.xls"
        print(f"Fetching GPR {freq} from: {url}")
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
        with open(target, "wb") as f:
            f.write(data)
        sha256 = hashlib.sha256(data).hexdigest()
        print(f"Downloaded GPR {freq}: {len(data)} bytes to {target}")
        print(f"SHA-256: {sha256}")

if __name__ == "__main__":
    fetch()
