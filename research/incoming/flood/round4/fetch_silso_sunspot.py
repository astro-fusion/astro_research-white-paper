#!/usr/bin/env python3
"""Fetch WDC-SILSO monthly total sunspot number (1749 to present)."""
import urllib.request, hashlib, os, sys

URLS = {
    'SN_m_tot_V2.0.txt': 'https://www.sidc.be/SILSO/DATA/SN_m_tot_V2.0.txt',
    'SN_m_tot_V2.0.csv': 'https://www.sidc.be/SILSO/DATA/SN_m_tot_V2.0.csv'
}

dest_dir = sys.argv[1] if len(sys.argv) > 1 else '/tmp'
os.makedirs(dest_dir, exist_ok=True)
headers = {'User-Agent': 'Mozilla/5.0'}

for fname, url in URLS.items():
    print(f'Fetching {fname} from {url}...')
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        content = resp.read()
    dest = os.path.join(dest_dir, fname)
    with open(dest, 'wb') as f:
        f.write(content)
    sha = hashlib.sha256(content).hexdigest()
    print(f'  Saved to {dest} ({len(content)} bytes), SHA256: {sha}')
