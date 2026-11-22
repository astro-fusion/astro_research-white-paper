#!/usr/bin/env python3
"""Fetch IMD 0.25 x 0.25 degree daily gridded rainfall binary file for a specified year."""
import urllib.request, urllib.parse, hashlib, os, sys

year = int(sys.argv[1]) if len(sys.argv) > 1 else 2020
dest_dir = sys.argv[2] if len(sys.argv) > 2 else '/tmp'
os.makedirs(dest_dir, exist_ok=True)

url = 'https://imdpune.gov.in/cmpg/Griddata/rainfall.php'
payload = urllib.parse.urlencode({'rain': year}).encode('utf-8')
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
    'Referer': 'https://imdpune.gov.in/cmpg/Griddata/Rainfall_25_NetCDF.html',
    'Content-Type': 'application/x-www-form-urlencoded'
}

print(f'Downloading IMD 0.25 gridded rainfall for year {year}...')
req = urllib.request.Request(url, data=payload, headers=headers)
with urllib.request.urlopen(req, timeout=60) as resp:
    content = resp.read()

dest = os.path.join(dest_dir, f'rain_{year}.grd')
with open(dest, 'wb') as f:
    f.write(content)

sha = hashlib.sha256(content).hexdigest()
days = 366 if (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)) else 365
expected = 129 * 135 * 4 * days
print(f'Saved {dest} ({len(content)} bytes), SHA256: {sha}')
print(f'Expected size: {expected} bytes. Valid: {len(content) == expected}')
