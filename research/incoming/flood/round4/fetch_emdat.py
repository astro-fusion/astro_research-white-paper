#!/usr/bin/env python3
"""Fetch EM-DAT South Asia flood disasters using CRED REST API (requires EMDAT_API_KEY)."""
import urllib.request, json, os, sys

api_key = os.environ.get('EMDAT_API_KEY')
if not api_key:
    print('NOTE: EM-DAT requires a free user API key from https://public.emdat.be/')
    print('Export your key: export EMDAT_API_KEY="your_key_here"')
    sys.exit(0)

headers = {'Authorization': f'Bearer {api_key}', 'User-Agent': 'Mozilla/5.0'}
url = 'https://api.emdat.be/v1/disasters?disaster_type=Flood&country_iso=IND,NPL,BGD,PAK'

try:
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode())
    out = os.path.join(sys.argv[1] if len(sys.argv) > 1 else '/tmp', 'emdat_south_asia_floods.json')
    with open(out, 'w') as f:
        json.dump(data, f, indent=2)
    print(f'Saved {len(data.get("data", []))} disaster records to {out}')
except Exception as e:
    print('EM-DAT API request failed:', e)
