#!/usr/bin/env python3
"""Information and asset fetcher for Global Flood Database (Tellman et al. 2021)."""
import urllib.request, hashlib, os, sys, ssl

# Global Flood Database metadata asset / repository descriptor
url = 'https://global-flood-database.cloudtostreet.ai/'
dest_dir = sys.argv[1] if len(sys.argv) > 1 else '/tmp'
os.makedirs(dest_dir, exist_ok=True)

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
headers = {'User-Agent': 'Mozilla/5.0'}

print(f'Fetching GFD portal metadata from {url}...')
req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req, timeout=30, context=ctx) as resp:
    content = resp.read()

dest = os.path.join(dest_dir, 'gfd_portal_index.html')
with open(dest, 'wb') as f:
    f.write(content)

sha = hashlib.sha256(content).hexdigest()
print(f'Saved to {dest} ({len(content)} bytes), SHA256: {sha}')
print('Note: Full spatial inundation rasters (CC BY 4.0) are hosted on Google Earth Engine: ee.ImageCollection("GLOBAL_FLOOD_DB/MODIS_EVENTS/V1")')
