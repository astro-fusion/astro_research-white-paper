#!/usr/bin/env python3
"""Fetch Dartmouth Flood Observatory Global Flood Records from Zenodo archive."""
import urllib.request, hashlib, os, sys

url = 'https://zenodo.org/api/records/19288171/files/Global_Flood_Records.csv/content'
dest_dir = sys.argv[1] if len(sys.argv) > 1 else '/tmp'
os.makedirs(dest_dir, exist_ok=True)
headers = {'User-Agent': 'curl/7.88.1'}

print(f'Fetching Global_Flood_Records.csv from {url}...')
req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req, timeout=60) as resp:
    content = resp.read()

dest = os.path.join(dest_dir, 'Global_Flood_Records.csv')
with open(dest, 'wb') as f:
    f.write(content)

sha = hashlib.sha256(content).hexdigest()
print(f'Saved to {dest} ({len(content)} bytes), SHA256: {sha}')
