#!/usr/bin/env python3
"""Fetch IMD Operational Long Range Seasonal Forecasts page."""
import urllib.request, hashlib, os, sys, ssl

url = 'https://www.imdpune.gov.in/cmpg/lrf/Forecast_Performance.html'
dest_dir = sys.argv[1] if len(sys.argv) > 1 else '/tmp'
os.makedirs(dest_dir, exist_ok=True)

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
headers = {'User-Agent': 'Mozilla/5.0'}

print(f'Fetching IMD forecast performance from {url}...')
req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req, timeout=30, context=ctx) as resp:
    content = resp.read()

dest = os.path.join(dest_dir, 'Forecast_Performance.html')
with open(dest, 'wb') as f:
    f.write(content)

sha = hashlib.sha256(content).hexdigest()
print(f'Saved to {dest} ({len(content)} bytes), SHA256: {sha}')
