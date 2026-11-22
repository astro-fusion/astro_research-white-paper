"""Fetch script for LBMA daily chart JSON endpoints (prices.lbma.org.uk).

Note: The public endpoint provides a trailing 22-trading-day window (~1 month).
Historical series (>1 month) require MyLBMA portal login and commercial licensing from ICE Benchmark Administration (IBA).
Requires 'Referer: https://www.lbma.org.uk/' and 'Origin: https://www.lbma.org.uk' headers.
"""

import hashlib
import json
import os
import subprocess

ENDPOINTS = {
    "gold_pm": "https://prices.lbma.org.uk/json/limited/gold_pm.json",
    "gold_am": "https://prices.lbma.org.uk/json/limited/gold_am.json",
    "silver": "https://prices.lbma.org.uk/json/limited/silver.json",
    "today": "https://prices.lbma.org.uk/json/today.json"
}

def fetch():
    for name, url in ENDPOINTS.items():
        target = f"/tmp/lbma_{name}.json"
        cmd = [
            "curl", "-s",
            "-H", "Referer: https://www.lbma.org.uk/",
            "-H", "Origin: https://www.lbma.org.uk",
            "-A", "Mozilla/5.0",
            url,
            "-o", target
        ]
        print(f"Fetching LBMA {name} from: {url}")
        subprocess.run(cmd, check=True)
        with open(target, "rb") as f:
            data = f.read()
        sha256 = hashlib.sha256(data).hexdigest()
        try:
            parsed = json.loads(data)
            rows = len(parsed) if isinstance(parsed, list) else len(parsed.keys())
        except Exception:
            rows = 0
        print(f"Downloaded {name}: {len(data)} bytes, {rows} entries to {target}")
        print(f"SHA-256: {sha256}")

if __name__ == "__main__":
    fetch()
