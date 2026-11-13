#!/usr/bin/env python3
"""Independent site identification for the 40 development records via OpenStreetMap (Nominatim search, ODbL).
Accept a site only when an OSM object's own name contains the operator AND the facility code (e.g. 'Equinix FR8'),
inside the expected metro (<= 60 km from the city reference). Everything else stays 'not identified'.
Writes data/datacentres/release/v1/site-identification.json."""
import json, math, sys, time, urllib.parse
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from pipeline import Fetcher
ROOT = Path(__file__).resolve().parents[2]; EV = Path(sys.argv[1]); F = Fetcher(EV / 'cache', delay=1.2)
EQ = json.loads((ROOT / 'data/datacentres/release/v1/equinix-developments.json').read_text())['records']
NX = json.loads((ROOT / 'data/datacentres/v2/nextdc-filing-developments.json').read_text())['records']
def dist(a, b, c, d):
    R = 6371000; p1, p2 = math.radians(a), math.radians(c)
    return 2 * R * math.asin(math.sqrt(math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(d - b) / 2) ** 2))
out = {}
for r in EQ + NX:
    code = r['id'].split(':')[2]; op = 'Equinix' if ':eqix:' in r['id'] else 'NEXTDC'; city = r['city']
    loc = r['location']; found = None; tried = []
    for q in (f'{op} {code} {city}', f'{op} {code}', f'{code} {op} data centre' if op == 'NEXTDC' else f'{op} {code} data center'):
        st, body, _ = F.get('https://nominatim.openstreetmap.org/search?' + urllib.parse.urlencode({'format': 'json', 'limit': 8, 'namedetails': 1, 'extratags': 1, 'q': q}))
        try: hits = json.loads(body) if st == 200 else []
        except Exception: hits = []
        tried.append({'q': q, 'hits': len(hits)})
        for h in hits:
            names = ' '.join([h.get('name') or ''] + list((h.get('namedetails') or {}).values()) + [h.get('display_name', '').split(',')[0]])
            if code.upper() in names.upper().replace(' ', '') or f'{code.upper()}' in names.upper().split():
                if op.upper() in names.upper() or op.upper() in (h.get('extratags') or {}).get('operator', '').upper():
                    d = dist(float(h['lat']), float(h['lon']), loc['lat'], loc['lon']) if loc.get('lat') is not None else 0
                    if d <= 60000:
                        found = {'osm': f"{h['osm_type']}/{h['osm_id']}", 'name': h.get('name') or names.strip(), 'class': f"{h.get('class')}/{h.get('type')}",
                                 'lat': round(float(h['lat']), 6), 'lon': round(float(h['lon']), 6), 'km_from_city_ref': round(d / 1000, 1),
                                 'source': f"https://www.openstreetmap.org/{h['osm_type']}/{h['osm_id']}", 'licence': 'ODbL 1.0 (© OpenStreetMap contributors)'}
                        break
        if found: break
    out[r['id']] = {'name': r['name'], 'site': found, 'queries': tried}
    print(r['id'], '->', (found or {}).get('name'), (found or {}).get('class'), (found or {}).get('km_from_city_ref'), flush=True)
p = ROOT / 'data/datacentres/release/v1/site-identification.json'
p.write_text(json.dumps({'method': __doc__.strip(), 'checked_at': '2026-11-13', 'records': out}, ensure_ascii=False, indent=1), encoding='utf-8')
print('identified', sum(1 for v in out.values() if v['site']), 'of', len(out))
