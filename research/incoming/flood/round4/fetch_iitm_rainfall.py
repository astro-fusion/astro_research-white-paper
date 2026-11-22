#!/usr/bin/env python3
"""Fetch IITM homogeneous monthly rainfall datasets (All-India, Macro-regions, Subdivisions, Longest series)."""
import urllib.request, hashlib, os, sys

URLS = {
    'iitm-regionrf.txt': 'https://www.tropmet.res.in/data/data-archival/rain/iitm-regionrf.txt',
    'iitm-subdivrf.txt': 'https://www.tropmet.res.in/data/data-archival/rain/iitm-subdivrf.txt',
    '8-all_ind.txt': 'https://www.tropmet.res.in/data/data-archival/rain-series/8-all_ind.txt'
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
