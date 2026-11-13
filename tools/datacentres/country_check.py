#!/usr/bin/env python3
"""Audit: page-stated country vs country at the record's coordinates (OSM Nominatim reverse, cached, 1 req/s).
Writes data/datacentres/v2/country-check.json. Mismatches are flagged for review, never auto-corrected."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from pipeline import Fetcher
from to_import import ISO
ROOT = Path(__file__).resolve().parents[2]
f = Fetcher(sys.argv[1]); out = []
for c in json.loads((ROOT / 'data/datacentres/candidates.json').read_text(encoding='utf-8'))['records']:
    co = c['coordinates']; iso = ISO.get(c.get('country'))
    if co.get('lat') is None or not iso: continue
    st, body, _ = f.get(f"https://nominatim.openstreetmap.org/reverse?format=json&zoom=3&lat={co['lat']}&lon={co['lng']}")
    try: cc = (json.loads(body).get('address', {}).get('country_code') or '').upper()
    except Exception: cc = ''
    if cc and cc != iso:
        out.append({'id': c['id'], 'page_country': c['country'], 'page_iso': iso, 'coordinate_country': cc, 'coordinate_class': co['class'], 'address': c.get('address')})
(ROOT / 'data/datacentres/v2/country-check.json').write_text(json.dumps({'checked_at': '2026-11-13', 'mismatches': out}, ensure_ascii=False, indent=1), encoding='utf-8')
print(json.dumps({'mismatches': len(out), 'sample': out[:8]}, ensure_ascii=False, indent=1))
