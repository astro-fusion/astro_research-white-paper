#!/usr/bin/env python3
"""Fetch IMD Forecasting Manual IV-18.1 containing Kerala Monsoon Onset historical records."""
import urllib.request, hashlib, os, sys, ssl

url = 'https://imdpune.gov.in/Reports/Forecasting_Mannuals/IMD_IV-18.1.pdf'
dest_dir = sys.argv[1] if len(sys.argv) > 1 else '/tmp'
os.makedirs(dest_dir, exist_ok=True)

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
headers = {'User-Agent': 'Mozilla/5.0'}

print(f'Fetching IMD Forecasting Manual IV-18.1 from {url}...')
req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req, timeout=60, context=ctx) as resp:
    content = resp.read()

dest = os.path.join(dest_dir, 'IMD_IV-18.1.pdf')
with open(dest, 'wb') as f:
    f.write(content)

sha = hashlib.sha256(content).hexdigest()
print(f'Saved to {dest} ({len(content)} bytes), SHA256: {sha}')
