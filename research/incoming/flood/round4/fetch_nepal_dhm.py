#!/usr/bin/env python3
"""Fetch Nepal DHM Monsoon Onset and Withdrawal Information document."""
import urllib.request, hashlib, os, sys, ssl

url = 'https://dhm.gov.np/uploads/dhm/climateService/1777966598_255c8bb3c67df349af0e.pdf'
dest_dir = sys.argv[1] if len(sys.argv) > 1 else '/tmp'
os.makedirs(dest_dir, exist_ok=True)

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
headers = {'User-Agent': 'Mozilla/5.0'}

print(f'Fetching DHM Nepal monsoon document from {url}...')
req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req, timeout=30, context=ctx) as resp:
    content = resp.read()

dest = os.path.join(dest_dir, 'dhm_monsoon_onset_withdrawal.pdf')
with open(dest, 'wb') as f:
    f.write(content)

sha = hashlib.sha256(content).hexdigest()
print(f'Saved to {dest} ({len(content)} bytes), SHA256: {sha}')
