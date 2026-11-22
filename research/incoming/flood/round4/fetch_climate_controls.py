#!/usr/bin/env python3
"""Fetch monthly climate control indices: NOAA ONI, Niño 3.4, and Dipole Mode Index (DMI)."""
import urllib.request, hashlib, os, sys

URLS = {
    'oni.data': 'https://psl.noaa.gov/data/correlation/oni.data',
    'nina34.data': 'https://psl.noaa.gov/data/correlation/nina34.data',
    'dmi.had.long.data': 'https://psl.noaa.gov/data/timeseries/month/data/dmi.had.long.data'
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
