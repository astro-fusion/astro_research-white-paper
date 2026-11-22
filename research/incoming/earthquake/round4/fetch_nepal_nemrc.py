#!/usr/bin/env python3
"""
fetch_nepal_nemrc.py

Fetches the latest earthquake bulletin from Nepal's National Earthquake Monitoring
and Research Centre (NEMRC / Department of Mines and Geology).
Endpoint: https://seismonepal.gov.np/en/earthquakes?page=1

Note: The host's SSL certificate is periodically expired, requiring an unverified
SSL context and a standard browser User-Agent header to avoid HTTP 406.
Saves HTML to /tmp/nepal_nemrc_page1.html and prints checksums and parsed rows.
"""

import urllib.request
import ssl
import hashlib
import re
import os

URL = "https://seismonepal.gov.np/en/earthquakes?page=1"
DEST_PATH = "/tmp/nepal_nemrc_page1.html"

def fetch_nepal(timeout=30):
    print(f"Fetching Nepal NEMRC bulletin...")
    print(f"  URL: {URL}")
    
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    }
    
    req = urllib.request.Request(URL, headers=headers)
    with urllib.request.urlopen(req, context=ctx, timeout=timeout) as resp:
        status = resp.status
        data = resp.read()
    
    with open(DEST_PATH, "wb") as f:
        f.write(data)
    
    sha256 = hashlib.sha256(data).hexdigest()
    html_text = data.decode("utf-8", errors="ignore")
    
    # Parse table rows
    rows = re.findall(r'<tr[^>]*>(.*?)</tr>', html_text, re.DOTALL)
    data_rows = []
    for r in rows:
        cols = re.findall(r'<td[^>]*>(.*?)</td>', r, re.DOTALL)
        if cols:
            cleaned = [re.sub(r'<[^>]+>', '', c).strip() for c in cols]
            data_rows.append(cleaned)
            
    print(f"  Status: {status}")
    print(f"  Saved to: {DEST_PATH}")
    print(f"  Size: {len(data):,} bytes")
    print(f"  SHA-256: {sha256}")
    print(f"  Parsed earthquake table entries: {len(data_rows)}")
    if data_rows:
        print("  Sample row:", data_rows[0])
    print()

if __name__ == "__main__":
    fetch_nepal()
