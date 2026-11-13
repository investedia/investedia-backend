#!/usr/bin/env python3
"""Validate operator-published map pins against the operator-published address.

An operator pin is strong evidence but may mark the building, a campus entrance or just the street address.
For every record with an operator pin we geocode the published address (OpenStreetMap Nominatim, 1 req/s, cached)
and compare:
  - geocoder hit is a building/address-level object AND pin within 150 m  -> 'exact'  (pin agrees with the building/address)
  - pin within 1,000 m of the address                                     -> 'approximate' (campus-level; building not confirmed)
  - farther, or the address cannot be geocoded                            -> 'needs_review' (kept, never shown as exact)
Records geocoded from an address only stay 'approximate'. Nothing is upgraded to exact without both sources agreeing.

Usage: python tools/datacentres/validate_pins.py --cache DIR
"""
import argparse, json, math, sys, urllib.parse
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from pipeline import Fetcher, OUT, tiers  # reuse the polite cached fetcher and tier rules

BUILDING_LEVEL = {'building', 'house', 'office', 'industrial', 'commercial', 'yes'}

def dist_m(a, b, c, d):
    r = 6371000; p1, p2 = math.radians(a), math.radians(c); dp = p2 - p1; dl = math.radians(d - b)
    return 2 * r * math.asin(math.sqrt(math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2))

def lookup(f, r):
    q = r['address'] if (r.get('country') or '') in r['address'] else f"{r['address']}, {r.get('country') or ''}"
    parts = [x.strip() for x in q.split(',') if x.strip()]
    for qq in dict.fromkeys([q, ', '.join(parts[:2] + parts[-2:]), ', '.join(parts[:1] + parts[-2:])]):
        st, body, _ = f.get('https://nominatim.openstreetmap.org/search?format=json&limit=1&addressdetails=0&q=' + urllib.parse.quote(qq))
        try:
            hits = json.loads(body) if st == 200 else []
        except Exception:
            hits = []
        if hits: return hits[0], qq
    return None, None

def main(cache):
    path = OUT / 'candidates.json'; data = json.loads(path.read_text(encoding='utf-8')); f = Fetcher(cache)
    stats = {}
    for r in data['records']:
        c = r['coordinates']
        if not (c.get('source') or '').startswith('operator') or c.get('lat') is None:
            continue
        if not r.get('address'):
            c.update(validation='no published address to compare', **{'class': 'needs_review'})
        else:
            hit, q = lookup(f, r)
            if not hit:
                c.update(validation='published address could not be geocoded', **{'class': 'needs_review'})
            else:
                d = dist_m(c['lat'], c['lng'], float(hit['lat']), float(hit['lon']))
                level = hit.get('type') in BUILDING_LEVEL or hit.get('class') in ('building', 'place') and int(hit.get('place_rank', 0)) >= 28
                cls = 'exact' if (d <= 150 and level) else 'approximate' if d <= 1000 else 'needs_review'
                c.update({'class': cls, 'validation': f"operator pin vs geocoded published address: {round(d)} m ({hit.get('class')}/{hit.get('type')}, OpenStreetMap Nominatim, ODbL)",
                          'pin_address_distance_m': round(d)})
        stats[c['class']] = stats.get(c['class'], 0) + 1
    for r in data['records']: r['evidence'] = tiers(r)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding='utf-8')
    v = OUT / 'verified.json'
    if v.exists():
        vd = json.loads(v.read_text(encoding='utf-8')); ids = {r['id']: r for r in data['records']}
        vd['records'] = [ids.get(r['id'], r) for r in vd['records']]; v.write_text(json.dumps(vd, ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps({'operator_pins_checked': sum(stats.values()), 'result': stats}, indent=1))

if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--cache', required=True); main(ap.parse_args().cache)
